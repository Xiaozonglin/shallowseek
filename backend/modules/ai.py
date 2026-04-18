import os
import re
import logging
from typing import Optional, Tuple, List, Any

import torch
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import util

from transformers import (
    Qwen3VLForConditionalGeneration,
    AutoProcessor,
    TextIteratorStreamer,
)
from qwen_vl_utils import process_vision_info


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class AIEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.use_cuda = self.device == "cuda"

        # Qwen3-VL 官方示例更接近 torch_dtype="auto" 的用法
        # 这里保留一个显式 dtype 字段，方便调试和打印
        if self.use_cuda:
            major_cc = torch.cuda.get_device_capability()[0]
            self.dtype = torch.bfloat16 if major_cc >= 8 else torch.float16
        else:
            self.dtype = torch.float32

        logger.info(f"初始化 AI 引擎... device={self.device}, dtype={self.dtype}")

        self.embeddings = None
        self.processor = None
        self.llm = None
        self.retriever = None

        self.load_models()
        self.init_retriever()

    def load_models(self):
        """加载 Embedding 与 Qwen3-VL 模型"""
        logger.info("正在加载 BGE Embedding 模型 (用于 RAG)...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-zh-v1.5",
            model_kwargs={"device": self.device},
            encode_kwargs={"normalize_embeddings": True},
        )

        model_name = os.getenv("QWEN_VL_MODEL", "Qwen/Qwen3-VL-2B-Instruct")
        logger.info(f"正在加载多模态模型: {model_name}")

        # Qwen3-VL 推荐配合 AutoProcessor 使用
        self.processor = AutoProcessor.from_pretrained(
            model_name,
            trust_remote_code=True,
        )

        # Qwen3-VL 对应的正确模型类
        load_kwargs = {
            "torch_dtype": "auto",
            "trust_remote_code": True,
        }

        if self.use_cuda:
            load_kwargs["device_map"] = "auto"
        else:
            load_kwargs["device_map"] = None

        self.llm = Qwen3VLForConditionalGeneration.from_pretrained(
            model_name,
            **load_kwargs,
        )

        if not self.use_cuda:
            self.llm = self.llm.to(self.device)

        self.llm.eval()
        logger.info("Qwen3-VL 加载完成")

    def init_retriever(self):
        """加载本地 FAISS 索引"""
        faiss_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../faiss_index",
        )

        if os.path.exists(faiss_path):
            try:
                vector_db = FAISS.load_local(
                    faiss_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True,
                )
                self.retriever = vector_db.as_retriever(search_kwargs={"k": 3})
                logger.info("本地 FAISS 索引加载完成")
            except Exception as e:
                logger.exception("FAISS 索引加载失败")
                self.retriever = None
        else:
            logger.warning("未找到 FAISS 索引，文档检索功能暂时关闭")
            self.retriever = None

    def safe_math(self, query: str) -> str:
        """非常保守的四则运算辅助"""
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
            result = eval(expr_str, {"__builtins__": None}, {})
            return f"\n【系统工具计算结果】: {expr_str} = {result}\n"
        except Exception:
            return ""

    def _build_inputs_from_messages(self, messages: list):
        """
        将 Qwen message 格式转换成模型输入。
        对 Qwen3-VL:
        - qwen_vl_utils 负责视觉预处理
        - 需要 image_patch_size=16
        - 若 qwen_vl_utils 已缩放，则 processor 传 do_resize=False
        """
        text_prompt = self.processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        image_inputs, video_inputs, video_kwargs = process_vision_info(
            messages,
            image_patch_size=16,
            return_video_kwargs=True,
            return_video_metadata=True,
        )

        inputs = self.processor(
            text=[text_prompt],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
            do_resize=False,
            **video_kwargs,
        )

        return inputs.to(self.device)

    def build_chat_inputs(self, query: str, image_base64: Optional[str] = None):
        """
        供主 Flask 路由使用：
        构建一个标准 user message，并返回 processor 后的模型输入
        """
        if image_base64:
            img_url = (
                image_base64
                if image_base64.startswith("data:image")
                else f"data:image/jpeg;base64,{image_base64}"
            )
            user_content = [
                {"type": "image", "image": img_url},
                {"type": "text", "text": query or "请详细分析这张图片。"},
            ]
        else:
            user_content = [
                {"type": "text", "text": query or "请回答我的问题。"},
            ]

        messages = [{"role": "user", "content": user_content}]
        return self._build_inputs_from_messages(messages)

    def analyze_image_standalone(self, image_base64: str) -> str:
        """纯图片解析接口"""
        try:
            img_url = (
                image_base64
                if image_base64.startswith("data:image")
                else f"data:image/jpeg;base64,{image_base64}"
            )

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": img_url},
                        {
                            "type": "text",
                            "text": "请提取图片中的所有文字、数字和公式，并对图片内容进行详细总结。",
                        },
                    ],
                }
            ]

            inputs = self._build_inputs_from_messages(messages)

            with torch.inference_mode():
                generated_ids = self.llm.generate(
                    **inputs,
                    max_new_tokens=512,
                    do_sample=False,
                )

            generated_ids_trimmed = [
                out_ids[len(in_ids):]
                for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]

            output_text = self.processor.batch_decode(
                generated_ids_trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )

            return output_text[0].strip() if output_text else "未能解析图片内容。"

        except Exception as e:
            logger.exception("Qwen-VL 图像解析异常")
            return f"图像解析失败：{str(e)}"

    def stream_generate_from_messages(
        self,
        messages: list,
        max_new_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> Tuple[TextIteratorStreamer, dict]:
        """
        为 SSE/流式输出准备 streamer 和 generation kwargs
        你在 Flask 里可以直接拿去起线程 generate
        """
        inputs = self._build_inputs_from_messages(messages)

        streamer = TextIteratorStreamer(
            self.processor.tokenizer,
            skip_prompt=True,
            timeout=60,
        )

        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=True if temperature > 0 else False,
        )

        return streamer, generation_kwargs

    def retrieve_context(self, query: str) -> str:
        """从本地知识库取回上下文"""
        if not query or not self.retriever:
            return ""

        try:
            docs = self.retriever.invoke(query)
            unique_docs = []
            seen = set()

            for d in docs:
                content = getattr(d, "page_content", "") or ""
                content = content.strip()
                if content and content not in seen:
                    seen.add(content)
                    unique_docs.append(content)

            if not unique_docs:
                return ""

            return "\n【本地参考资料】:\n" + "\n---\n".join(unique_docs)
        except Exception:
            logger.exception("RAG 检索失败")
            return ""

    def semantic_similarity(self, text1: str, text2: str) -> float:
        """供外部需要时做简易相似度比较"""
        try:
            vec1 = self.embeddings.embed_query(text1)
            vec2 = self.embeddings.embed_query(text2)
            return float(util.cos_sim(vec1, vec2).item())
        except Exception:
            return 0.0