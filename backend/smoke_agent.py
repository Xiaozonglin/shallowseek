"""深度模式（Agent）冒烟测试：验证工具循环、事件流与卡片生成。

用法（需要本地 .env 配置 DEEPSEEK_API_KEY）::

    cd backend
    python smoke_agent.py
    python smoke_agent.py --question "动态规划解题步骤是什么？"

不需要启动 Flask、不需要前端；会真实调用 DeepSeek API。
"""

from __future__ import annotations

import argparse
import json
import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(description="深度模式 Agent 冒烟测试")
    parser.add_argument(
        "--question",
        default="二分查找的时间复杂度怎么推导？请给出解题步骤。",
        help="测试问题",
    )
    args = parser.parse_args()

    try:
        from modules.agent import AgentRuntime
        from modules.ai import AIEngine

        ai = AIEngine()
        runtime = AgentRuntime(ai)
    except Exception as exc:
        print(f"[失败] 初始化失败: {exc}")
        return 1

    print(f"[模型] {ai.model} | thinking={ai.thinking} | 检索索引: {ai.retriever is not None}")
    print(f"[问题] {args.question}")
    print("[流式回答] ", end="", flush=True)

    card_count = 0
    tool_count = 0
    sources = []
    duration_ms = 0

    try:
        for event in runtime.run(args.question, ui_enabled=True):
            event_type = event.get("type")
            if event_type == "answer_delta":
                print(event.get("text", ""), end="", flush=True)
            elif event_type == "answer_reset":
                print("\n[重置旁白]", end="", flush=True)
            elif event_type == "tool_call":
                tool_count += 1
                print(f"\n[工具] {event.get('name')} {event.get('arguments', '')[:120]}")
            elif event_type == "tool_result":
                print(f"[工具结果] {'成功' if event.get('ok') else '失败'}：{event.get('summary', '')}")
            elif event_type == "ui":
                ui = event.get("ui") or {}
                card_count = len(ui.get("cards") or [])
                print(f"\n[卡片] {json.dumps(ui, ensure_ascii=False)[:400]}")
            elif event_type == "complete":
                sources = event.get("sources") or []
                duration_ms = event.get("durationMs") or 0
            elif event_type == "error":
                print(f"\n[失败] {event.get('message')}")
                return 1
    except Exception as exc:
        print(f"\n[失败] {exc}")
        return 1

    print(f"\n\n[完成] 工具调用 {tool_count} 次 | 卡片 {card_count} 张 | 引用 {len(sources)} 条 | 耗时 {duration_ms} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
