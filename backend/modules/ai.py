import os, re

import torch
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyMuPDFLoader, UnstructuredImageLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import SentenceTransformer, util

# ==================== Qwen-VL 核心依赖 ====================
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor, TextIteratorStreamer, AutoModelForVision2Seq
from qwen_vl_utils import process_vision_info

class AIEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.bfloat16 if self.device == "cuda" and torch.cuda.get_device_capability()[0] >= 8 else torch.float32
        print(f"初始化 AI 引擎... 设备: {self.device}, 精度: {self.dtype}")
        
        self.load_models()
        self.init_retriever()

    def load_models(self):
        """加载统一的 Qwen2-VL 模型与向量 Embedding"""
        print("正在加载 BGE Embedding 模型 (用于 RAG)...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-zh-v1.5", 
            model_kwargs={'device': self.device},
            encode_kwargs={'normalize_embeddings': True}
        )

        print("正在加载 Qwen/Qwen3-VL-2B-Instruct 原生多模态大模型...")
        # 此处以 2B 版本为例，若服务器显存充足（如 16GB+），可替换为 "Qwen/Qwen2-VL-7B-Instruct"
        print("正在加载 Qwen/Qwen3-VL-2B-Instruct...")
        model_name = "Qwen/Qwen3-VL-2B-Instruct" 
    
        # 1. 确保 Processor 也是最新
        self.processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
    
        # 2. 这里的类名请确保与 transformers 库一致，或者使用 AutoModel
    
        self.llm = AutoModelForVision2Seq.from_pretrained(
            model_name,
            torch_dtype=self.dtype,
            device_map="auto" if self.device == "cuda" else None,
            trust_remote_code=True  # ！！！这行非常关键，能解决维度不匹配问题
        )
        print("Qwen3-VL 加载完成！")

    def init_retriever(self):
        faiss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../faiss_index")
        if os.path.exists(faiss_path):
            vector_db = FAISS.load_local(faiss_path, self.embeddings, allow_dangerous_deserialization=True)
            self.retriever = vector_db.as_retriever(search_kwargs={"k": 3})
            print("本地 FAISS 索引加载完成")
        else:
            print("未找到 FAISS 索引，文档检索功能暂时关闭。")
            self.retriever = None

    def safe_math(self, query):
        math_keywords = ['计算', '等于', '求解', '+', '-', '*', '/']
        if any(keyword in query for keyword in math_keywords):
            expr_str = re.sub(r'[^\d\+\-\*\/\(\)\.]', '', query.replace('计算', '').replace('等于', ''))
            if expr_str:
                try:
                    result = eval(expr_str, {"__builtins__": None}, {})
                    return f"\n【系统工具计算结果】: {expr_str} = {result}\n"
                except:
                    pass
        return ""

    def analyze_image_standalone(self, image_base64):
        """为单图片上传接口提供的独立解析方法"""
        try:
            img_url = f"data:image/jpeg;base64,{image_base64}" if not image_base64.startswith("data:image") else image_base64
            messages = [
                {"role": "user", "content": [
                    {"type": "image", "image": img_url},
                    {"type": "text", "text": "请提取图片中的所有文字、数字和公式，并对图片内容进行详细总结。"}
                ]}
            ]
            
            text_prompt = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs, _ = process_vision_info(messages)
            
            inputs = self.processor(
                text=[text_prompt],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt"
            ).to(self.device)
            
            with torch.inference_mode():
                generated_ids = self.llm.generate(**inputs, max_new_tokens=512)
                generated_ids_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
                output_text = self.processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)
                
            return output_text[0]
        except Exception as e:
            print(f"[Qwen-VL 解析异常]: {e}")
            return "图像解析失败，请确保图片格式正确且未损坏。"