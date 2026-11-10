"""Agent 工具层：知识库检索、读取原文、四则运算、提交卡片。

工具是纯 Python 函数，通过 OpenAI function-calling 协议暴露给模型；
本轮引用注册表（CitationRegistry）保证「引用编号只来自本轮检索」。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from . import ui_cards

logger = logging.getLogger(__name__)

MAX_READ_CHARS = 4000
MAX_RETRIEVE_LIMIT = 8

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "docs"))


class CitationRegistry:
    """本轮问答的引用注册表：编号 -> 资料元数据，编号按首次检索顺序递增。"""

    def __init__(self) -> None:
        self._sources: List[Dict[str, Any]] = []
        self._seen: Dict[str, int] = {}

    def add(self, *, title: str, source: Optional[str], document_id: str, text: str, path: str = "") -> int:
        dedupe_key = f"{document_id}::{text[:200]}"
        existing = self._seen.get(dedupe_key)
        if existing is not None:
            return existing
        citation = len(self._sources) + 1
        self._sources.append(
            {
                "citation": citation,
                "title": title[:240] or document_id,
                "source": source,
                "documentId": document_id,
                "path": path,
                "text": text,
            }
        )
        self._seen[dedupe_key] = citation
        return citation

    def get(self, citation: int) -> Optional[Dict[str, Any]]:
        if 1 <= citation <= len(self._sources):
            return self._sources[citation - 1]
        return None

    def sources(self) -> List[Dict[str, Any]]:
        return [
            {
                "citation": item["citation"],
                "title": item["title"],
                "source": item["source"],
                "documentId": item["documentId"],
            }
            for item in self._sources
        ]


class AgentTools:
    """一次问答对应的工具集合；每次请求创建新实例，保证引用注册表隔离。"""

    def __init__(self, engine: Any, ui_enabled: bool = True, docs_dir: Optional[str] = None) -> None:
        self.engine = engine
        self.ui_enabled = ui_enabled
        self.docs_dir = os.path.abspath(docs_dir or DOCS_DIR)
        self.registry = CitationRegistry()
        self.pending_ui: Optional[ui_cards.UIEnvelope] = None
        self._title_cache: Dict[str, str] = {}

    # ========================== 工具 schema ==========================
    def schemas(self) -> List[Dict[str, Any]]:
        schemas: List[Dict[str, Any]] = [
            {
                "type": "function",
                "function": {
                    "name": "retrieve_knowledge",
                    "description": "检索本地算法知识库，返回带引用编号的资料片段。回答课程/算法问题前先调用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "中文检索关键词，例如“二分查找 边界”"},
                            "limit": {"type": "integer", "minimum": 1, "maximum": MAX_RETRIEVE_LIMIT},
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_source",
                    "description": "读取某条引用对应的资料原文片段，用于核对细节。",
                    "parameters": {
                        "type": "object",
                        "properties": {"citation": {"type": "integer", "minimum": 1}},
                        "required": ["citation"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "safe_math",
                    "description": "计算四则运算表达式，避免口算错误。",
                    "parameters": {
                        "type": "object",
                        "properties": {"expression": {"type": "string", "description": "例如 (23*17+5)/2"}},
                        "required": ["expression"],
                        "additionalProperties": False,
                    },
                },
            },
        ]

        if self.ui_enabled:
            envelope_schema = ui_cards.UIEnvelope.model_json_schema()
            definitions = envelope_schema.pop("$defs", {})
            parameters: Dict[str, Any] = {
                "type": "object",
                "properties": {"ui": envelope_schema},
                "required": ["ui"],
                "additionalProperties": False,
            }
            if definitions:
                parameters["$defs"] = definitions
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": "present_ui",
                        "description": "提交最终回答要展示的交互卡片（最多 3 张）。只提交引用编号/章节 id 与纯文本。",
                        "parameters": parameters,
                    },
                }
            )
        return schemas

    # ========================== 工具执行 ==========================
    def execute(self, name: str, arguments: Any) -> Dict[str, Any]:
        handlers = {
            "retrieve_knowledge": self._retrieve,
            "read_source": self._read_source,
            "safe_math": self._safe_math,
            "present_ui": self._present_ui,
        }
        handler = handlers.get(name)
        if handler is None:
            return {"error": f"未知工具：{name}"}
        if not isinstance(arguments, dict):
            return {"error": "工具参数必须是 JSON 对象"}
        try:
            return handler(arguments)
        except Exception as exc:  # 工具异常不应中断整轮回答
            logger.exception("工具执行失败: %s", name)
            return {"error": f"工具执行失败：{exc}"}

    def _retrieve(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = str(arguments.get("query") or "").strip()
        if not query:
            return {"error": "query 不能为空"}
        try:
            limit = int(arguments.get("limit") or 4)
        except (TypeError, ValueError):
            limit = 4
        limit = min(max(limit, 1), MAX_RETRIEVE_LIMIT)

        retriever = getattr(self.engine, "retriever", None)
        if retriever is None:
            return {"found": 0, "message": "知识库索引未就绪，请基于已有信息作答或说明缺少资料"}

        hits = retriever.search(query, k=limit)
        if not hits:
            return {"found": 0, "message": "未检索到相关资料，请如实说明"}

        results = []
        for hit in hits:
            document_id = str(hit.get("source") or "")
            text = str(hit.get("text") or "")
            title = self._title_for(document_id, text)
            citation = self.registry.add(
                title=title,
                source=None,
                document_id=document_id,
                text=text,
                path=document_id,
            )
            results.append(
                {
                    "citation": citation,
                    "title": title,
                    "snippet": text[:300],
                }
            )
        return {
            "found": len(results),
            "results": results,
            "note": "引用编号只能使用这里返回的编号；需要原文细节可调用 read_source。",
        }

    def _read_source(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            citation = int(arguments.get("citation") or 0)
        except (TypeError, ValueError):
            return {"error": "citation 必须是整数"}
        source = self.registry.get(citation)
        if source is None:
            return {"error": "引用编号不存在，请先调用 retrieve_knowledge"}

        text = source.get("text") or ""
        path = source.get("path") or ""
        file_text = self._read_doc_file(path)
        if file_text:
            text = file_text
        truncated = len(text) > MAX_READ_CHARS
        return {
            "citation": citation,
            "title": source["title"],
            "text": text[:MAX_READ_CHARS],
            "truncated": truncated,
        }

    def _safe_math(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        expression = str(arguments.get("expression") or "").strip()
        if not expression:
            return {"error": "expression 不能为空"}
        calculator = getattr(self.engine, "safe_math", None)
        if calculator is None:
            return {"error": "计算工具不可用"}
        result = calculator(expression)
        if not result:
            return {"error": "表达式无法计算"}
        return {"expression": expression, "result": result.strip()}

    def _present_ui(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not self.ui_enabled:
            return {"accepted": False, "errors": ["ui_disabled"]}
        envelope, errors = ui_cards.validate_ui(arguments.get("ui"), self.registry.sources())
        if envelope is not None:
            self.pending_ui = envelope
        return {
            "accepted": envelope is not None,
            "errors": errors,
            "hint": "继续输出独立可读的完整文字回答。",
        }

    # ========================== 辅助 ==========================
    def _title_for(self, document_id: str, text: str) -> str:
        if document_id in self._title_cache:
            return self._title_cache[document_id]
        title = ""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                break
        if not title:
            base = os.path.basename(document_id)
            title = base[:-3] if base.endswith(".md") else base or document_id
        self._title_cache[document_id] = title
        return title

    def _read_doc_file(self, relative_path: str) -> str:
        if not relative_path:
            return ""
        try:
            candidate = os.path.abspath(os.path.join(self.docs_dir, relative_path))
            if not candidate.startswith(self.docs_dir + os.sep):
                return ""
            if not os.path.isfile(candidate):
                return ""
            with open(candidate, "r", encoding="utf-8", errors="ignore") as handle:
                return handle.read()
        except OSError:
            return ""

    def serialize_pending_ui(self) -> Optional[Dict[str, Any]]:
        if self.pending_ui is None:
            return None
        return self.pending_ui.model_dump()
