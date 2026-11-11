"""回答效果：回答模板 × 交流方式。

- 模板决定「回答的框架」（先辨析概念、先自测、还是从已知引出未知）；
- 交流方式决定「这一轮说多少、是否引导学生回答」。
两者互相独立，可组合使用；由前端在提问前选择，随请求发送并落库。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

DEFAULT_TEMPLATE = "free"
DEFAULT_STYLE = "long_form"

TEMPLATES: Dict[str, Dict[str, str]] = {
    "free": {
        "label": "自由回答",
        "description": "不套用固定框架，按问题类型直接作答（事实查询直接回答）",
        "instructions": "",
    },
    "learn_new": {
        "label": "学习新知",
        "description": "先辨析概念边界，再用最小例子和变式题检验理解",
        "instructions": (
            "回答框架（学习新知）：\n"
            "1. 先用一句话给出定义/结论，再指出最容易混淆的邻近概念（1-2 组对比：相同点、不同点、适用边界）；\n"
            "2. 用一个最小例子说明，再给 1 个变式题（由浅入深、覆盖常见误区），让学生先自己判断；\n"
            "3. 最后给一句自测提示（例如「能解释 X 与 Y 的区别，说明已掌握」）。\n"
            "重点在概念辨析与变式考察，不要只堆一大段文字解析。"
        ),
    },
    "review_old": {
        "label": "复习旧知",
        "description": "先自测回忆，再补易错点和记忆锚点",
        "instructions": (
            "回答框架（复习旧知）：\n"
            "1. 先用 1 个回忆/自测小问题开场（只问一个，等学生回答）；\n"
            "2. 再给最易错点与记忆锚点（不超过 3 条，每条一句话）；\n"
            "3. 给间隔复习建议（今天 / 3 天后 / 一周后分别复习什么），尽量精简。"
        ),
    },
    "explore_new": {
        "label": "探索未知",
        "description": "从已学知识引出未知问题，给延伸方向与资料线索",
        "instructions": (
            "回答框架（探索未知）：\n"
            "1. 用学生已知的概念作为锚点，指出它解释不了什么，从缺口里引出本轮的未知问题；\n"
            "2. 给一个粗线条的直觉/类比，并提出一个需要继续探索的关键问题；\n"
            "3. 提供 1-2 条继续阅读的资料线索（优先用本轮检索到的章节卡/来源卡），鼓励学生提出下一个问题。"
        ),
    },
}

STYLES: Dict[str, Dict[str, str]] = {
    "short_round": {
        "label": "逐轮短对话",
        "description": "每轮只推进一小步，用问题引导学生自己往下走",
        "instructions": (
            "交流方式（逐轮短对话）：\n"
            "- 本轮回答控制在 200 字以内（最多 4-5 句），只推进一个知识点或一个步骤；\n"
            "- 结尾必须向学生提出 1 个具体的小问题，等学生回答后再继续；\n"
            "- 不要一次给出所有结论；卡片最多 1 张，优先用对话引导。"
        ),
    },
    "long_form": {
        "label": "长对话",
        "description": "一次给出尽量完整的知识结构，便于系统学习",
        "instructions": (
            "交流方式（长对话）：\n"
            "- 尽量完整、结构化地回答（可用小标题或列表），覆盖定义、原理、例子与易错点；\n"
            "- 允许较长输出，卡片最多 3 张；结尾给 1 个可选的进一步追问方向。"
        ),
    },
}


def normalize_template(value: Optional[str]) -> str:
    template = (value or "").strip()
    return template if template in TEMPLATES else DEFAULT_TEMPLATE


def normalize_style(value: Optional[str]) -> str:
    style = (value or "").strip()
    return style if style in STYLES else DEFAULT_STYLE


def is_valid_template(value: Optional[str]) -> bool:
    return (value or "").strip() in TEMPLATES


def is_valid_style(value: Optional[str]) -> bool:
    return (value or "").strip() in STYLES


FREE_TEMPLATE_GUIDE = (
    "回答模板：自由回答（不强制套用固定框架）。\n"
    "- 先判断问题类型：事实、规则、流程、数据查询类问题直接给出准确结论与依据，"
    "不要硬加例子、变式题、自测提示或教学步骤；不知道就明确说不知道，并说明缺少哪项资料。\n"
    "- 只有概念学习/解题类问题，才需要使用概念辨析、例子或练习。"
)


def template_instructions(template: Optional[str]) -> str:
    template_id = normalize_template(template)
    if template_id == "free":
        return FREE_TEMPLATE_GUIDE
    return TEMPLATES[template_id]["instructions"]


def style_instructions(style: Optional[str]) -> str:
    return STYLES[normalize_style(style)]["instructions"]


def mode_instructions(template: Optional[str], style: Optional[str]) -> str:
    """深度模式：模板可选（默认自由回答）+ 交流方式。"""
    return (
        "【本轮回答效果】\n"
        f"{template_instructions(template)}\n\n"
        f"{style_instructions(style)}"
    )


def fast_mode_instructions(style: Optional[str] = None) -> str:
    """快答模式：不套用任何模板，只保留交流方式（默认直接回答）。"""
    return (
        "【本轮回答效果】\n"
        "快速回答：不套用回答模板，直接、准确地回答用户问题；"
        "事实/规则类问题不要附加例子、变式题或教学步骤。\n\n"
        f"{style_instructions(style)}"
    )


def mode_labels(template: Optional[str], style: Optional[str]) -> Tuple[str, str]:
    return (
        TEMPLATES[normalize_template(template)]["label"],
        STYLES[normalize_style(style)]["label"],
    )


def template_options() -> List[Dict[str, Any]]:
    return [
        {"id": template_id, "label": spec["label"], "description": spec["description"]}
        for template_id, spec in TEMPLATES.items()
    ]


def style_options() -> List[Dict[str, Any]]:
    return [
        {"id": style_id, "label": spec["label"], "description": spec["description"]}
        for style_id, spec in STYLES.items()
    ]


def metadata() -> Dict[str, Any]:
    return {
        "defaultTemplate": DEFAULT_TEMPLATE,
        "defaultStyle": DEFAULT_STYLE,
        "templates": template_options(),
        "styles": style_options(),
    }
