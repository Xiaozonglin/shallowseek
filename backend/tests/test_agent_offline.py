"""Agent 运行时离线测试：用假 OpenAI 客户端与假检索器，不调用真实 API。"""

import json
import unittest
from types import SimpleNamespace

from modules.agent import AgentRuntime
from modules.agent_tools import AgentTools


def text_chunk(text):
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=text, tool_calls=None))]
    )


def call_chunk(index, call_id=None, name=None, arguments=None):
    function = SimpleNamespace(name=name, arguments=arguments)
    tool_call = SimpleNamespace(index=index, id=call_id, function=function)
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=None, tool_calls=[tool_call]))]
    )


class FakeRetriever:
    def search(self, query, k=4):
        if not query:
            return []
        return [
            {
                "text": "# 二分查找\n二分查找要求数组有序，每次比较中点后舍弃一半区间。",
                "source": "algo-wiki/chapter_searching/binary_search.md",
                "score": 30.0,
            }
        ]


class FakeCompletions:
    def __init__(self, scripts):
        self.scripts = list(scripts)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        script = self.scripts.pop(0) if self.scripts else [text_chunk("默认回答")]
        if isinstance(script, Exception):
            raise script
        return iter(script)


class FakeEngine:
    model = "fake-model"

    def __init__(self, scripts):
        self.retriever = FakeRetriever()
        self.client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions(scripts)))

    def extra_body(self):
        return {}

    def safe_math(self, query):
        return "\n【系统工具计算结果】: 1+1 = 2\n" if "1+1" in query else ""

    def friendly_error(self, exc):
        return f"AI 服务调用失败：{exc}"


class AgentRuntimeTest(unittest.TestCase):
    def test_tool_loop_and_cards(self):
        ui_payload = {
            "ui": {
                "version": 1,
                "cards": [
                    {"type": "source_list", "citations": [1]},
                    {"type": "related_chapters", "chapterIds": ["searching"]},
                ],
            }
        }
        scripts = [
            # 第 1 轮：旁白 + 检索工具
            [text_chunk("我先查一下资料。"), call_chunk(0, "call_1", "retrieve_knowledge", json.dumps({"query": "二分查找", "limit": 2}))],
            # 第 2 轮：提交卡片
            [call_chunk(0, "call_2", "present_ui", json.dumps(ui_payload, ensure_ascii=False))],
            # 第 3 轮：最终文字回答
            [text_chunk("二分查找要求数组有序，每次比较中点后舍弃一半区间。")],
        ]
        engine = FakeEngine(scripts)
        runtime = AgentRuntime(engine, max_rounds=4, timeout_seconds=30)
        tools = AgentTools(engine, ui_enabled=True)

        events = list(runtime.run("什么是二分查找？", ui_enabled=True, tools=tools))
        types = [event["type"] for event in events]

        self.assertIn("tool_call", types)
        self.assertIn("tool_result", types)
        self.assertIn("answer_reset", types)
        self.assertIn("ui", types)
        self.assertIn("complete", types)

        ui_event = next(event for event in events if event["type"] == "ui")
        self.assertEqual("source_list", ui_event["ui"]["cards"][0]["type"])

        complete = next(event for event in events if event["type"] == "complete")
        self.assertEqual("deep", complete["mode"])
        self.assertIn("二分查找", complete["answer"])
        self.assertEqual(1, len(complete["sources"]))
        self.assertEqual(1, complete["sources"][0]["citation"])
        self.assertEqual(2, len(complete["trace"]))

    def test_invalid_card_is_dropped_but_answer_kept(self):
        bad_ui = {"ui": {"version": 1, "cards": [{"type": "source_list", "citations": [99]}]}}
        scripts = [
            [call_chunk(0, "call_1", "retrieve_knowledge", json.dumps({"query": "二分查找"}))],
            [call_chunk(0, "call_2", "present_ui", json.dumps(bad_ui))],
            [text_chunk("这是基于资料的回答。")],
        ]
        engine = FakeEngine(scripts)
        runtime = AgentRuntime(engine, max_rounds=4, timeout_seconds=30)
        events = list(runtime.run("题目", ui_enabled=True))

        types = [event["type"] for event in events]
        self.assertNotIn("ui", types)
        complete = next(event for event in events if event["type"] == "complete")
        self.assertEqual("这是基于资料的回答。", complete["answer"])

    def test_max_rounds_fallback(self):
        scripts = [
            [call_chunk(0, "call_1", "retrieve_knowledge", json.dumps({"query": "二分查找"}))],
            [call_chunk(0, "call_2", "retrieve_knowledge", json.dumps({"query": "哈希表"}))],
        ]
        engine = FakeEngine(scripts)
        runtime = AgentRuntime(engine, max_rounds=2, timeout_seconds=30)
        events = list(runtime.run("问题", ui_enabled=False))
        complete = next(event for event in events if event["type"] == "complete")
        self.assertTrue(complete["answer"])
        self.assertIn("抱歉", complete["answer"])

    def test_model_error_emits_error_event(self):
        engine = FakeEngine([RuntimeError("boom")])
        runtime = AgentRuntime(engine, max_rounds=2, timeout_seconds=30)
        events = list(runtime.run("问题", ui_enabled=False))
        self.assertEqual("error", events[-1]["type"])
        self.assertIn("AI 服务调用失败", events[-1]["message"])

    def test_no_ui_when_disabled(self):
        scripts = [[text_chunk("直接回答。")]]
        engine = FakeEngine(scripts)
        runtime = AgentRuntime(engine, max_rounds=2, timeout_seconds=30)
        events = list(runtime.run("问题", ui_enabled=False))
        types = [event["type"] for event in events]
        self.assertNotIn("ui", types)
        # 未启用卡片时，不应向模型暴露 present_ui 工具
        engine2 = FakeEngine([[text_chunk("回答")]])
        list(AgentRuntime(engine2, max_rounds=1).run("问题", ui_enabled=False))
        tool_names = {tool["function"]["name"] for tool in engine2.client.chat.completions.calls[0].get("tools", [])}
        self.assertNotIn("present_ui", tool_names)


if __name__ == "__main__":
    unittest.main()
