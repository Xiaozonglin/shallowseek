"""智能 UI 卡片协议与校验。

设计借鉴 xdu-zhixing 的 `agent_harness/ui.py`（只参考协议与校验思路，未复制其实现）：
模型只提交引用号 / 章节 ID 与纯文本；标题与来源由本轮检索注册表、章节目录注入，
非法卡片被丢弃但文字回答保留。

卡片类型（学习场景）：
- source_list：参考资料卡，列出本轮实际检索到的资料引用号；
- guide：解题步骤卡，每步带引用号；
- related_chapters：相关章节卡，模型只给 chapter id。
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Annotated, Any, Dict, List, Literal, Optional, Set, Tuple, Union
from urllib.parse import urlsplit

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    ValidationError,
)

UI_VERSION = 1

_CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chapter_catalog.json")


def _no_markup(value: str) -> str:
    if "<" in value or ">" in value:
        raise ValueError("display text must not contain markup")
    return value


Title = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=240),
    AfterValidator(_no_markup),
]
Detail = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
    AfterValidator(_no_markup),
]
Identifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    AfterValidator(_no_markup),
]
Citations = Annotated[
    List[Annotated[int, Field(strict=True, ge=1)]],
    Field(min_length=1, max_length=8),
]
ChapterIds = Annotated[List[Identifier], Field(min_length=1, max_length=8)]


class _UIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceList(_UIModel):
    type: Literal["source_list"]
    citations: Citations


class GuideStep(_UIModel):
    title: Title
    detail: Detail
    citations: Citations


class Guide(_UIModel):
    type: Literal["guide"]
    title: Title
    steps: List[GuideStep] = Field(min_length=1, max_length=8)


class RelatedChapters(_UIModel):
    type: Literal["related_chapters"]
    chapterIds: ChapterIds


UICard = Annotated[Union[SourceList, Guide, RelatedChapters], Field(discriminator="type")]
_card_adapter = TypeAdapter(UICard)


class UIEnvelope(_UIModel):
    version: Literal[1]
    cards: List[UICard] = Field(min_length=1, max_length=3)


@lru_cache(maxsize=1)
def chapter_catalog() -> Dict[str, Dict[str, str]]:
    try:
        with open(_CATALOG_PATH, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): {"title": str(value.get("title", key)), "path": str(value.get("path", ""))}
        for key, value in raw.items()
        if isinstance(value, dict)
    }


def chapter_ids() -> Set[str]:
    return set(chapter_catalog())


def chapter_titles() -> Dict[str, str]:
    return {key: value["title"] for key, value in chapter_catalog().items()}


def safe_source_url(value: Optional[str]) -> bool:
    """只允许 http(s) 链接；本地资料没有对外链接时返回 True。"""
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    try:
        url = urlsplit(value)
    except ValueError:
        return False
    return url.scheme in ("http", "https") and bool(url.hostname) and not url.username and not url.password


def card_citations(card: UICard) -> Set[int]:
    if isinstance(card, SourceList):
        return set(card.citations)
    if isinstance(card, Guide):
        return {int(number) for step in card.steps for number in step.citations}
    return set()


def validate_ui(
    value: Any,
    sources: List[Dict[str, Any]],
    allowed_chapters: Optional[Set[str]] = None,
) -> Tuple[Optional[UIEnvelope], List[str]]:
    """校验模型提交的卡片描述，返回 (合法卡片信封或 None, 错误原因列表)。"""
    if value is None:
        return None, []
    if (
        not isinstance(value, dict)
        or set(value) != {"version", "cards"}
        or type(value.get("version")) is not int
        or value["version"] != UI_VERSION
        or not isinstance(value.get("cards"), list)
        or not 1 <= len(value["cards"]) <= 3
    ):
        return None, ["invalid_envelope"]

    source_map = {int(source["citation"]): source for source in sources if "citation" in source}
    allowed_chapters = chapter_ids() if allowed_chapters is None else allowed_chapters

    cards: List[UICard] = []
    errors: List[str] = []

    for index, raw in enumerate(value["cards"]):
        try:
            card = _card_adapter.validate_python(raw)
        except ValidationError:
            errors.append(f"card_{index}:invalid_schema")
            continue

        references = card_citations(card)
        invalid_reference = False
        for citation in references:
            source = source_map.get(citation)
            if source is None or not safe_source_url(source.get("source")):
                invalid_reference = True
                break
        if invalid_reference:
            errors.append(f"card_{index}:invalid_source")
            continue

        if isinstance(card, RelatedChapters) and any(
            chapter_id not in allowed_chapters for chapter_id in card.chapterIds
        ):
            errors.append(f"card_{index}:unknown_chapter")
            continue

        cards.append(card)

    if not cards:
        return None, errors
    return UIEnvelope(version=UI_VERSION, cards=cards), errors
