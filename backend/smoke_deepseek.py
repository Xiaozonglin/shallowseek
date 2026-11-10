"""P0 冒烟测试：验证 DEEPSEEK_API_KEY、模型名与流式输出。

用法（在 backend 目录下）::

    python smoke_deepseek.py

不需要启动 Flask、不需要前端、不需要本地模型权重。
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    try:
        from modules.ai import AIEngine

        ai = AIEngine()
    except Exception as exc:  # Key 未配置 / 依赖未安装
        print(f"[失败] 初始化 AI 引擎失败: {exc}")
        return 1

    print(f"[1/2] 模型: {ai.model} | base_url: {ai.base_url} | thinking: {ai.thinking}")

    print("[2/2] 流式回答测试（约 2~10 秒）...")
    try:
        tokens = []
        for token in ai.stream_answer("你是一个简洁的助手。", "用一句话解释什么是二分查找。", max_tokens=256):
            tokens.append(token)
            print(token, end="", flush=True)
    except Exception as exc:
        print(f"\n[失败] {ai.friendly_error(exc)}")
        return 1

    answer = "".join(tokens).strip()
    print(f"\n[回答] {answer}")
    if not answer:
        print("[失败] 流式输出为空")
        return 1

    print("[通过] DeepSeek API 流式链路正常")
    return 0


if __name__ == "__main__":
    sys.exit(main())
