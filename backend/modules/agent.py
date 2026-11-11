"""进程内 Agent 运行时：DeepSeek function-calling 工具循环。

设计借鉴 xdu-zhixing 的 Agent 执行流程（只参考思路与事件协议，未复制其实现）：
- 最多 N 轮模型请求，整体有超时；
- 模型可调用工具（检索 / 读原文 / 计算 / 提交卡片），每轮流式输出文本；
- 工具调用之间的旁白用 answer_reset 清空，最终一段文字才是答案；
- 结束时产出 complete（含引用来源、工具轨迹、耗时），卡片另行以 ui 事件下发。

对外只暴露 `AgentRuntime.run()`，产出事件 dict，由 main.py 转成 SSE。
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Iterable, Iterator, List, Optional

from . import agent_prompts, ui_cards
from .agent_tools import AgentTools

logger = logging.getLogger(__name__)

DEFAULT_MAX_ROUNDS = 6
DEFAULT_TIMEOUT_SECONDS = 50
DEFAULT_MAX_OUTPUT_TOKENS = 2048


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


class AgentRuntime:
    """一次问答的 Agent 执行器；引擎需提供 client / model / extra_body() / safe_math()。"""

    def __init__(
        self,
        engine: Any,
        max_rounds: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
    ) -> None:
        self.engine = engine
        self.max_rounds = max(1, max_rounds if max_rounds is not None else _env_int("AGENT_MAX_ROUNDS", DEFAULT_MAX_ROUNDS))
        self.timeout_seconds = max(
            5.0,
            timeout_seconds if timeout_seconds is not None
            else _env_float("AGENT_TIMEOUT_SECONDS", float(DEFAULT_TIMEOUT_SECONDS)),
        )
        self.max_output_tokens = max(
            256,
            max_output_tokens if max_output_tokens is not None
            else _env_int("AGENT_MAX_OUTPUT_TOKENS", DEFAULT_MAX_OUTPUT_TOKENS),
        )

    # ========================== 对外入口 ==========================
    def run(
        self,
        question: str,
        history_text: str = "",
        ui_enabled: bool = True,
        tools: Optional[AgentTools] = None,
        authoritative_context: str = "",
    ) -> Iterator[Dict[str, Any]]:
        started = time.monotonic()
        tools = tools or AgentTools(self.engine, ui_enabled=ui_enabled)
        trace: List[Dict[str, Any]] = []
        tools_schema = tools.schemas()
        messages = self._initial_messages(question, history_text, ui_enabled, authoritative_context)

        final_text = ""
        timed_out = False

        yield {"type": "status", "stage": "thinking", "message": "正在检索和思考…"}

        for round_index in range(self.max_rounds):
            if time.monotonic() - started > self.timeout_seconds:
                timed_out = True
                break

            round_text = ""
            pending_calls: Dict[int, Dict[str, Any]] = {}
            try:
                stream = self._create_stream(messages, tools_schema)
                for chunk in stream:
                    if time.monotonic() - started > self.timeout_seconds:
                        timed_out = True
                        break
                    delta = self._delta_of(chunk)
                    if delta is None:
                        continue
                    content = getattr(delta, "content", None)
                    if content:
                        round_text += content
                        yield {"type": "answer_delta", "text": content}
                    tool_calls = getattr(delta, "tool_calls", None)
                    if tool_calls:
                        self._accumulate_tool_calls(pending_calls, tool_calls)
            except Exception as exc:
                logger.exception("Agent 模型调用失败")
                yield {
                    "type": "error",
                    "code": "ai_error",
                    "message": self._friendly_error(exc),
                }
                return

            if timed_out:
                final_text = round_text.strip()
                break

            if pending_calls:
                # 工具调用之间的旁白不是最终答案，清空已下发的临时文本
                if round_text.strip():
                    yield {"type": "answer_reset"}
                messages.append(self._assistant_tool_message(round_text, pending_calls))
                for call in [pending_calls[index] for index in sorted(pending_calls)]:
                    name = call["name"]
                    arguments = self._parse_arguments(call["arguments"])
                    yield {
                        "type": "tool_call",
                        "name": name,
                        "arguments": self._short_json(arguments),
                    }
                    tool_started = time.monotonic()
                    result = tools.execute(name, arguments)
                    ok = "error" not in result
                    trace.append(
                        {
                            "name": name,
                            "ok": ok,
                            "arguments": self._short_json(arguments, limit=120),
                            "ms": int((time.monotonic() - tool_started) * 1000),
                        }
                    )
                    yield {
                        "type": "tool_result",
                        "name": name,
                        "ok": ok,
                        "summary": self._tool_summary(name, result),
                    }
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call["id"],
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
                yield {"type": "status", "stage": "tool", "message": "资料已就绪，正在整理答案…"}
                continue

            if round_text.strip():
                final_text = round_text.strip()
                break

        if not final_text:
            if timed_out:
                final_text = "这次回答超时了，请重试或把问题描述得更具体一些。"
            else:
                final_text = agent_prompts.FALLBACK_ANSWER
            yield {"type": "answer_delta", "text": final_text}

        duration_ms = int((time.monotonic() - started) * 1000)
        pending_ui = tools.serialize_pending_ui()
        if pending_ui is not None and ui_enabled:
            yield {"type": "ui", "ui": pending_ui}

        yield {
            "type": "complete",
            "answer": final_text,
            "sources": tools.registry.sources(),
            "trace": trace,
            "durationMs": duration_ms,
            "mode": "deep",
        }

    # ========================== 内部辅助 ==========================
    def _initial_messages(
        self,
        question: str,
        history_text: str,
        ui_enabled: bool,
        authoritative_context: str = "",
    ) -> List[Dict[str, Any]]:
        user_content = question
        if history_text:
            user_content = f"{question}\n\n【最近的问答记录，仅供参考】\n{history_text}"
        return [
            {
                "role": "system",
                "content": agent_prompts.deep_system_prompt(
                    ui_enabled=ui_enabled,
                    authoritative_context=authoritative_context,
                ),
            },
            {"role": "user", "content": user_content},
        ]

    def _create_stream(self, messages: List[Dict[str, Any]], tools_schema: List[Dict[str, Any]]):
        kwargs: Dict[str, Any] = {
            "model": self.engine.model,
            "messages": messages,
            "stream": True,
            "temperature": 0.3,
            "max_tokens": self.max_output_tokens,
        }
        if tools_schema:
            kwargs["tools"] = tools_schema
            kwargs["tool_choice"] = "auto"
        extra_body = self.engine.extra_body() if callable(getattr(self.engine, "extra_body", None)) else {}
        if extra_body:
            kwargs["extra_body"] = extra_body
        return self.engine.client.chat.completions.create(**kwargs)

    @staticmethod
    def _delta_of(chunk: Any) -> Any:
        choices = getattr(chunk, "choices", None)
        if not choices:
            return None
        return getattr(choices[0], "delta", None)

    @staticmethod
    def _accumulate_tool_calls(pending: Dict[int, Dict[str, Any]], tool_calls: Iterable[Any]) -> None:
        for raw in tool_calls:
            index = getattr(raw, "index", 0) or 0
            entry = pending.setdefault(index, {"id": "", "name": "", "arguments": ""})
            call_id = getattr(raw, "id", None)
            if call_id:
                entry["id"] = call_id
            function = getattr(raw, "function", None)
            if function is not None:
                name = getattr(function, "name", None)
                if name:
                    entry["name"] = name
                arguments = getattr(function, "arguments", None)
                if arguments:
                    entry["arguments"] += arguments

    @staticmethod
    def _assistant_tool_message(round_text: str, pending_calls: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        calls = []
        for index in sorted(pending_calls):
            entry = pending_calls[index]
            calls.append(
                {
                    "id": entry["id"] or f"call_{index}",
                    "type": "function",
                    "function": {
                        "name": entry["name"],
                        "arguments": entry["arguments"] or "{}",
                    },
                }
            )
        return {
            "role": "assistant",
            "content": round_text or None,
            "tool_calls": calls,
        }

    @staticmethod
    def _parse_arguments(raw: str) -> Dict[str, Any]:
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _short_json(value: Any, limit: int = 200) -> str:
        try:
            text = json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            text = str(value)
        return text[:limit]

    @staticmethod
    def _tool_summary(name: str, result: Dict[str, Any]) -> str:
        if "error" in result:
            return f"{name} 失败：{result['error']}"
        if name == "retrieve_knowledge":
            return f"检索到 {result.get('found', 0)} 条资料"
        if name == "read_source":
            text = str(result.get("text") or "")
            return f"读取 {result.get('citation')} 号资料（{len(text)} 字）"
        if name == "safe_math":
            return f"计算结果：{result.get('result', '')}"
        if name == "present_ui":
            accepted = result.get("accepted")
            return "卡片已提交" if accepted else f"卡片被拒绝：{';'.join(result.get('errors') or [])}"
        return "完成"

    def _friendly_error(self, exc: Exception) -> str:
        friendly = getattr(self.engine, "friendly_error", None)
        if callable(friendly):
            return friendly(exc)
        return f"AI 服务调用失败：{exc}"


def available_chapter_payload() -> List[Dict[str, str]]:
    """给前端/调试用的章节目录（id + 标题）。"""
    return [{"id": chapter_id, "title": title} for chapter_id, title in ui_cards.chapter_titles().items()]
