"""DeepSeek API 版 AI 引擎（不加载任何本地模型）。

与旧实现的接口保持一致，`main.py` 只需要把「本地 generate / FAISS / embedding」
调用替换为这里的方法即可：

- ``stream_answer``：SSE 流式回答（文本 / 图片）
- ``generate_text``：非流式生成（学情分析等）
- ``analyze_image_standalone``：纯图片解析（``/api/upload/image``）
- ``retrieve_context``：知识库词法检索上下文
- ``text_similarity``：权威答案匹配 / 留言去重
- ``safe_math``：保守的四则运算工具（纯 Python，保留原实现）
- ``friendly_error``：把 API / 网络异常转成可直接展示给用户的中文提示
"""

from __future__ import annotations

import logging
import os
import re
from typing import Generator, List, Optional

from openai import OpenAI

from . import retrieval

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "你是专业的学习助手。请根据提供的资料、上下文或图片准确回答用户问题。"
    "如果用户上传了图片，请精确识别其中的文字、公式或逻辑结构并进行解答。"
)
DEFAULT_VISION_PROMPT = "请提取图片中的所有文字、数字和公式，并对图片内容进行详细总结。"

_IMAGE_DATA_URL_PREFIX = "data:image/"


class AIEngine:
    """DeepSeek API 封装。初始化时校验 Key、加载词法索引，不触发任何模型下载。"""

    def __init__(self) -> None:
        self.api_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
        self.thinking = (os.getenv("DEEPSEEK_THINKING", "disabled") or "disabled").strip().lower()
        self.timeout = float(os.getenv("DEEPSEEK_TIMEOUT", "60"))
        self.default_max_tokens = int(os.getenv("DEEPSEEK_MAX_TOKENS", "1024"))

        if not self.api_key:
            raise RuntimeError(
                "未配置 DEEPSEEK_API_KEY。请复制仓库根的 .env.example 为 .env 并填入 Key，"
                "例如：DEEPSEEK_API_KEY=sk-xxxx（也可通过环境变量提供）。"
            )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=2,
        )
        self.retriever = self._load_retriever()

        logger.info(
            "DeepSeek API 就绪: base_url=%s, model=%s, thinking=%s",
            self.base_url,
            self.model,
            self.thinking,
        )

    # ========================== 初始化辅助 ==========================
    def _load_retriever(self) -> Optional[retrieval.LexicalRetriever]:
        path = os.getenv("BM25_INDEX_PATH") or retrieval.default_index_path()
        try:
            return retrieval.LexicalRetriever.load(path)
        except Exception:  # 索引损坏不应阻止服务启动
            logger.exception("BM25 索引加载异常: %s", path)
            return None

    def _extra_body(self) -> dict:
        """DeepSeek 的思考模式开关不是 OpenAI SDK 标准字段，需要走 extra_body。"""
        if self.thinking in {"enabled", "disabled"}:
            return {"extra_body": {"thinking": {"type": self.thinking}}}
        return {}

    def _messages(self, system_prompt: str, user_text: str, image_data_url: Optional[str] = None) -> List[dict]:
        if image_data_url:
            user_content: object = [
                {"type": "image_url", "image_url": {"url": image_data_url, "detail": "auto"}},
                {"type": "text", "text": user_text or "请详细分析这张图片。"},
            ]
        else:
            user_content = user_text or ""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    # ========================== 对外能力 ==========================
    def stream_answer(
        self,
        system_prompt: str,
        user_text: str,
        image_data_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> Generator[str, None, None]:
        """流式回答：逐段 yield 文本增量（main.py 直接转成 SSE）。"""
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=self._messages(system_prompt, user_text, image_data_url),
            stream=True,
            temperature=0.7,
            max_tokens=max_tokens or self.default_max_tokens,
            **self._extra_body(),
        )

        try:
            for chunk in stream:
                choices = getattr(chunk, "choices", None)
                if not choices:
                    continue
                delta = choices[0].delta
                token = getattr(delta, "content", None)
                if token:
                    yield token
        finally:
            close = getattr(stream, "close", None)
            if callable(close):
                close()

    def generate_text(self, system_prompt: str, user_prompt: str, max_tokens: int = 520) -> str:
        """非流式生成：学情分析、班级总结等场景使用。"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._messages(system_prompt, user_prompt),
            temperature=0.7,
            max_tokens=max_tokens,
            **self._extra_body(),
        )
        if not response.choices:
            return ""
        content = response.choices[0].message.content
        return (content or "").strip()

    def analyze_image_standalone(self, image_b64: str) -> str:
        """纯图片解析：交给 deepseek-flash 的视觉能力完成。"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": self.to_data_url(image_b64), "detail": "auto"}},
                            {"type": "text", "text": DEFAULT_VISION_PROMPT},
                        ],
                    },
                ],
                temperature=0.3,
                max_tokens=768,
                **self._extra_body(),
            )
            if not response.choices:
                return "未能解析图片内容。"
            return (response.choices[0].message.content or "").strip() or "未能解析图片内容。"
        except Exception as exc:  # 图片解析失败返回可读文案，不抛出 500
            logger.exception("图片解析失败")
            return f"图像解析失败：{self.friendly_error(exc)}"

    def retrieve_context(self, query: str) -> str:
        """从本地知识库检索上下文（BM25）。索引缺失时静默返回空字符串。"""
        if not query or not self.retriever:
            return ""
        try:
            results = self.retriever.search(query, k=retrieval.DEFAULT_K)
            return retrieval.format_context(results)
        except Exception:
            logger.exception("词法检索失败")
            return ""

    @staticmethod
    def text_similarity(text_a: str, text_b: str) -> float:
        """短文本相似度（0~1），替代原 BGE embedding 余弦。"""
        return retrieval.text_similarity(text_a, text_b)

    @staticmethod
    def to_data_url(image_b64: str) -> str:
        """把前端传来的裸 base64（或完整 data URL）规整成 data URL。"""
        if not image_b64:
            return ""
        value = str(image_b64).strip()
        if value.startswith(_IMAGE_DATA_URL_PREFIX):
            return value
        return f"data:image/jpeg;base64,{value}"

    # ========================== 原样保留的工具方法 ==========================
    def safe_math(self, query: str) -> str:
        """非常保守的四则运算辅助。"""
        if not query:
            return ""

        math_keywords = ["计算", "等于", "求解", "+", "-", "*", "/"]
        if not any(keyword in query for keyword in math_keywords):
            return ""

        expr_str = re.sub(
            r"[^\d\+\-\*\/\(\)\.]",
            "",
            query.replace("计算", "").replace("等于", ""),
        )

        if not expr_str:
            return ""

        try:
            result = eval(expr_str, {"__builtins__": None}, {})  # noqa: S307 - 输入已白名单过滤
            return f"\n【系统工具计算结果】: {expr_str} = {result}\n"
        except Exception:
            return ""

    @staticmethod
    def friendly_error(exc: Exception) -> str:
        """把 API / 网络异常转成用户可读提示。"""
        status = getattr(exc, "status_code", None)
        if status == 401:
            return "AI 服务认证失败：请检查 DEEPSEEK_API_KEY 是否正确。"
        if status == 402:
            return "AI 服务余额不足，请前往 DeepSeek 开放平台充值后重试。"
        if status == 429:
            return "AI 服务请求过于频繁，请稍等几秒再试。"
        if status in (400, 422):
            return "AI 服务请求参数有误，请检查输入内容后重试。"
        if status and int(status) >= 500:
            return "AI 服务暂时不可用，请稍后重试。"

        name = type(exc).__name__
        if "Timeout" in name:
            return "AI 服务响应超时，请稍后重试。"
        if "Connection" in name:
            return "无法连接 AI 服务，请检查网络后重试。"
        return f"AI 回答失败：{exc}"
