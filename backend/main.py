import os
import json
import re
import torch
import threading
import requests
import sympy
import base64
import io
import cv2
import numpy as np
from PIL import Image
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
from datetime import timedelta
from functools import wraps

if torch.cuda.is_available():
    os.environ["CUDA_MODULE_LOADING"] = "LAZY"
    # 针对旧款显卡的显存优化
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
else:
    # CPU 环境下限制线程数，防止 Flask 阻塞
    torch.set_num_threads(os.cpu_count() // 2 if os.cpu_count() else 4)

import flask
from flask import Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message as MailMessage

from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyMuPDFLoader, UnstructuredImageLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer, AutoProcessor, AutoModelForMultimodalLM
from sentence_transformers import SentenceTransformer, util

# ========================== 基础配置 ==========================
load_dotenv()
app = flask.Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_default_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session Cookie 配置（关键：解决登出问题）
app.config['SESSION_COOKIE_SECURE'] = False  # 开发环境设为False，生产环境应为True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # 允许跨站请求携带cookie
app.config['REMEMBER_COOKIE_SECURE'] = False
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'

# 安全头部配置
app.config['SESSION_COOKIE_NAME'] = 'session_id'

# 速率限制配置
from collections import defaultdict
from time import time

RATE_LIMIT_STORE = defaultdict(list)

# 密码强度要求
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPER = True
PASSWORD_REQUIRE_LOWER = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = False

# 邮件配置
app.config['MAIL_SERVER'] = os.getenv('EMAIL_HOST')
app.config['MAIL_PORT'] = int(os.getenv('EMAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('EMAIL_USE_TLS', 'True').lower() in ['true', '1']
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('EMAIL_FROM')

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ========================== 安全工具函数 ==========================

def is_strong_password(password):
    """检查密码强度"""
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"密码长度至少需要 {PASSWORD_MIN_LENGTH} 位"
    
    if PASSWORD_REQUIRE_UPPER and not re.search(r'[A-Z]', password):
        return False, "密码需要包含至少一个大写字母"
    
    if PASSWORD_REQUIRE_LOWER and not re.search(r'[a-z]', password):
        return False, "密码需要包含至少一个小写字母"
    
    if PASSWORD_REQUIRE_DIGIT and not re.search(r'\d', password):
        return False, "密码需要包含至少一个数字"
    
    if PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "密码需要包含至少一个特殊字符"
    
    return True, "密码强度符合要求"

def sanitize_input(text, max_length=1000):
    """清理用户输入，防止XSS和注入攻击"""
    if not text:
        return text
    
    # 截断过长文本
    text = str(text)[:max_length]
    
    # 移除潜在危险字符（基础XSS防护）
    # 注意：这只是基础防护，完整方案应结合前端转义和CSP
    text = text.replace('<script', '&lt;script')
    text = text.replace('javascript:', '')
    text = text.replace('onerror=', '')
    text = text.replace('onload=', '')
    
    return text.strip()

def check_rate_limit(ip_address, limit=10, window=60):
    """检查速率限制"""
    current_time = time()
    
    # 清理过期记录
    RATE_LIMIT_STORE[ip_address] = [
        t for t in RATE_LIMIT_STORE[ip_address] if current_time - t < window
    ]
    
    # 检查是否超过限制
    if len(RATE_LIMIT_STORE[ip_address]) >= limit:
        return False
    
    # 记录本次请求
    RATE_LIMIT_STORE[ip_address].append(current_time)
    return True

def rate_limit(limit=10, window=60):
    """速率限制装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip_address = flask.request.remote_addr
            if not check_rate_limit(ip_address, limit, window):
                return flask.jsonify({
                    "error": "请求过于频繁，请稍后再试"
                }), 429
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ========================== 数据库模型 ==========================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(10), nullable=False) # 'student' or 'teacher'
    learning_summary = db.Column(db.String(1000), nullable=True) # AI生成的学习情况分析
    summary_updated_at = db.Column(db.DateTime, nullable=True) # 分析更新时间

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(1000), nullable=False)
    answer = db.Column(db.String(2000), nullable=True) # AI回答
    
    # --- 权威答案相关字段 ---
    authoritative_answer = db.Column(db.String(2000), nullable=True) # 老师提供的权威答案
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # 提供权威答案的老师
    
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(1000), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='unread')
    
    reply_content = db.Column(db.String(2000), nullable=True)
    reply_timestamp = db.Column(db.DateTime, nullable=True)
    replier_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

with app.app_context():
    db.create_all()

# ========================== AI 模型运行环境检测 ==========================

def get_optimal_hardware_config():
    if torch.cuda.is_available():
        device = "cuda"
        # 检查显卡是否支持 bfloat16 (RTX 30/40/50系列支持，比 float16 更稳定)
        if torch.cuda.get_device_capability()[0] >= 8:
            dtype = torch.bfloat16
            print(f"检测到现代 GPU: {torch.cuda.get_device_name(0)}，启用 bfloat16")
        else:
            dtype = torch.float16
            print(f"检测到旧款 GPU: {torch.cuda.get_device_name(0)}，启用 float16")
    else:
        device = "cpu"
        dtype = torch.float32 # CPU 通常不支持半精度运算，强行开启可能报错或变慢
        print("未检测到 GPU，将切换至 CPU 模式（注意：推理速度将大幅下降）")
    
    return device, dtype

DEVICE, DTYPE = get_optimal_hardware_config()

# ========================== AI 模型初始化 ==========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "model_weights"))
EMBED_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "rag-embedding"))
VLM_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "vlm_weights"))

os.makedirs(MODEL_PATH, exist_ok=True)
os.makedirs(EMBED_PATH, exist_ok=True)
os.makedirs(VLM_PATH, exist_ok=True)

def is_locally_available(path):
    return os.path.exists(os.path.join(path, "config.json"))

print("正在初始化 RTX 5060 加速引擎...")

# 1. 加载 LLM
if not is_locally_available(MODEL_PATH):
    print("第一次运行：正在从镜像站拉取 Qwen 模型...")
    t_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", trust_remote_code=True)
    t_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", torch_dtype=DTYPE, device_map="auto" if DEVICE == "cuda" else None, trust_remote_code=True)
    t_tokenizer.save_pretrained(MODEL_PATH)
    t_model.save_pretrained(MODEL_PATH)

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, torch_dtype=DTYPE, device_map="auto" if DEVICE == "cuda" else None, local_files_only=True, trust_remote_code=True, low_cpu_mem_usage=True,)

if DEVICE == "cpu":
    model = model.to("cpu")

# 2. 加载 Embedding
if not is_locally_available(EMBED_PATH):
    print("第一次运行：正在拉取 BGE 向量模型...")
    e_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    e_model.save(EMBED_PATH)

embedding = HuggingFaceEmbeddings(
    model_name=EMBED_PATH, 
    model_kwargs={'device': DEVICE},
    encode_kwargs={'normalize_embeddings': True}
)

# 3. 加载多模态视觉语言模型 (VLM)
print("正在初始化多模态视觉模型...")
try:
    if not is_locally_available(VLM_PATH):
        print("第一次运行：正在拉取多模态模型...")
        try:
            # 尝试使用BLIP模型 - 更小更快
            from transformers import BlipProcessor, BlipForConditionalGeneration
            
            print("尝试下载BLIP模型...")
            vlm_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            vlm_model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base",
                torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
                device_map="auto" if DEVICE == "cuda" else None
            )
            vlm_processor.save_pretrained(VLM_PATH)
            vlm_model.save_pretrained(VLM_PATH)
            print("BLIP 多模态模型下载成功")
        except Exception as e:
            print(f"⚠️ BLIP 模型下载失败: {e}")
            print("⚠️ 尝试使用更小的模型...")
            try:
                # 尝试使用更小的ViT-GPT2模型
                from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer
                
                print("尝试下载ViT-GPT2模型...")
                vlm_processor = ViTImageProcessor.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
                vlm_model = VisionEncoderDecoderModel.from_pretrained(
                    "nlpconnect/vit-gpt2-image-captioning",
                    torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
                    device_map="auto" if DEVICE == "cuda" else None
                )
                vlm_processor.save_pretrained(VLM_PATH)
                vlm_model.save_pretrained(VLM_PATH)
                print("ViT-GPT2 多模态模型下载成功")
            except Exception as e2:
                print(f"⚠️ 所有多模态模型下载失败: {e2}")
                print("⚠️ 将使用纯文本模式，多模态功能不可用")
                vlm_processor = None
                vlm_model = None
                vlm_available = False
    else:
        # 检查保存的模型类型
        config_path = os.path.join(VLM_PATH, "config.json")
        if os.path.exists(config_path):
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            model_type = config.get("_name_or_path", "") or config.get("model_type", "")
            
            if "blip" in model_type.lower():
                from transformers import BlipProcessor, BlipForConditionalGeneration
                vlm_processor = BlipProcessor.from_pretrained(VLM_PATH, local_files_only=True)
                vlm_model = BlipForConditionalGeneration.from_pretrained(
                    VLM_PATH,
                    torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
                    device_map="auto" if DEVICE == "cuda" else None,
                    local_files_only=True
                )
            elif "vision-encoder-decoder" in model_type.lower():
                from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer
                vlm_processor = ViTImageProcessor.from_pretrained(VLM_PATH, local_files_only=True)
                vlm_model = VisionEncoderDecoderModel.from_pretrained(
                    VLM_PATH,
                    torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
                    device_map="auto" if DEVICE == "cuda" else None,
                    local_files_only=True
                )
            else:
                # 尝试通用加载
                try:
                    vlm_processor = AutoProcessor.from_pretrained(VLM_PATH, local_files_only=True, trust_remote_code=True)
                    vlm_model = AutoModelForMultimodalLM.from_pretrained(
                        VLM_PATH,
                        torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
                        device_map="auto" if DEVICE == "cuda" else None,
                        local_files_only=True,
                        trust_remote_code=True
                    )
                except:
                    print("⚠️ 无法识别模型类型，将使用纯文本模式")
                    vlm_processor = None
                    vlm_model = None
        else:
            print("⚠️ 配置文件不存在，将使用纯文本模式")
            vlm_processor = None
            vlm_model = None
    
    # 检查变量是否已定义
    if 'vlm_processor' in locals() and vlm_processor is not None and 'vlm_model' in locals() and vlm_model is not None:
        if DEVICE == "cpu":
            vlm_model = vlm_model.to("cpu")
        
        print("多模态视觉模型加载成功")
        vlm_available = True
    else:
        print("⚠️ 多模态模型未加载，将使用纯文本模式")
        vlm_available = False
except Exception as e:
    print(f"⚠️ 多模态视觉模型加载失败: {e}")
    print("⚠️ 将使用纯文本模式，多模态功能不可用")
    vlm_processor = None
    vlm_model = None
    vlm_available = False

# 3. 向量库初始化
def init_vector_db():
    faiss_path = os.path.join(BASE_DIR, "faiss_index")
    if os.path.exists(faiss_path):
        vstore = FAISS.load_local(faiss_path, embedding, allow_dangerous_deserialization=True)
    else:
        docs_dir = os.path.join(BASE_DIR, "..", "docs")
        if not os.path.exists(docs_dir): os.makedirs(docs_dir)
        
        # 同时支持 .md, .pdf, .jpg, .png
        loaders = {
            ".md": DirectoryLoader(docs_dir, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'}),
            ".pdf": DirectoryLoader(docs_dir, glob="**/*.pdf", loader_cls=PyMuPDFLoader),
            ".jpg": DirectoryLoader(docs_dir, glob="**/*.jpg", loader_cls=UnstructuredImageLoader),
        }
        
        docs = []
        for loader in loaders.values():
            docs.extend(loader.load())
            
        if not docs: return None
        
        # 3. 分块与入库
        splits = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150).split_documents(docs)
        vstore = FAISS.from_documents(splits, embedding)
        vstore.save_local(faiss_path)
    return vstore.as_retriever(search_kwargs={"k": 3})

retriever = init_vector_db()

# ========================== 核心业务工具库 ==========================

def get_history(user_id):
    records = Question.query.filter_by(student_id=user_id).order_by(Question.timestamp.desc()).limit(3).all()
    records.reverse()
    return "\n".join([f"问：{r.content}\n答：{r.answer}" for r in records])

def find_authoritative_knowledge(query):
    """查找权威知识（老师提供的答案）"""
    try:
        # 在问题库中搜索相似问题
        questions = Question.query.filter(Question.authoritative_answer.isnot(None)).all()
        
        if not questions:
            return ""
        
        # 使用嵌入向量计算相似度
        query_vec = embedding.embed_query(query)
        best_match = None
        best_similarity = 0.7  # 相似度阈值
        
        for q in questions:
            if q.content:
                q_vec = embedding.embed_query(q.content)
                similarity = util.cos_sim(query_vec, q_vec).item()
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = q
        
        if best_match:
            teacher = db.session.get(User, best_match.teacher_id)
            teacher_name = teacher.username if teacher else "老师"
            return f"\n【权威参考】来自{teacher_name}的解答：\n{best_match.authoritative_answer}\n"
        
        return ""
    except Exception as e:
        print(f"查找权威知识错误: {e}")
        return ""

def check_and_run_tools(query):
    """检查并运行工具（数学计算、网页抓取等）"""
    try:
        # 检查是否需要数学计算
        math_keywords = ['计算', '等于', '求解', '解方程', '积分', '微分', '求导', 'sin', 'cos', 'tan', 'log', 'ln']
        if any(keyword in query.lower() for keyword in math_keywords):
            try:
                # 尝试使用sympy进行符号计算
                expr = sympy.sympify(query.replace('计算', '').replace('等于', '=').strip())
                result = sympy.N(expr)
                return f"\n【数学计算】{query} = {result}\n"
            except:
                pass
        
        # 检查是否需要网页抓取
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, query)
        if urls:
            try:
                response = requests.get(urls[0], timeout=5)
                soup = BeautifulSoup(response.text, 'html.parser')
                # 提取主要文本内容
                text = soup.get_text()[:500]  # 限制长度
                return f"\n【网页内容摘要】{text}...\n"
            except:
                pass
        
        return ""
    except Exception as e:
        print(f"工具运行错误: {e}")
        return ""

# ========================== 多模态图像处理工具 ==========================

def process_image_base64(image_base64):
    """处理base64编码的图像"""
    try:
        # 移除data:image/...;base64,前缀
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        # 解码base64
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        
        # 转换为RGB格式
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        return image
    except Exception as e:
        print(f"图像处理错误: {e}")
        return None

def extract_text_from_image(image):
    """从图像中提取文字（使用VLM模型）"""
    if not vlm_available:
        return "多模态模型未加载，无法提取图像文字"
    
    try:
        # 检查模型类型并相应处理
        model_type = type(vlm_model).__name__
        
        if "Blip" in model_type:
            # BLIP模型处理
            inputs = vlm_processor(image, return_tensors="pt").to(vlm_model.device)
            out = vlm_model.generate(**inputs, max_new_tokens=100)
            caption = vlm_processor.decode(out[0], skip_special_tokens=True)
            return f"图像描述：{caption}"
        elif "VisionEncoderDecoder" in model_type:
            # ViT-GPT2模型处理
            pixel_values = vlm_processor(images=image, return_tensors="pt").pixel_values.to(vlm_model.device)
            generated_ids = vlm_model.generate(pixel_values, max_length=50)
            generated_text = vlm_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return f"图像描述：{generated_text}"
        else:
            # 通用处理（尝试原始方法）
            prompt = "请详细描述这张图片的内容，包括其中的文字、图表、公式等所有可见信息。"
            inputs = vlm_processor(images=image, text=prompt, return_tensors="pt").to(vlm_model.device)
            generated_ids = vlm_model.generate(**inputs, max_new_tokens=512)
            generated_text = vlm_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return generated_text
            
    except Exception as e:
        print(f"图像文字提取错误: {e}")
        return f"图像处理失败: {str(e)}"

def analyze_image_with_question(image, question):
    """使用VLM模型分析图像并回答问题"""
    if not vlm_available:
        return "多模态模型未加载，无法分析图像"
    
    try:
        # 检查模型类型并相应处理
        model_type = type(vlm_model).__name__
        
        if "Blip" in model_type:
            # BLIP模型处理 - 使用条件生成
            inputs = vlm_processor(image, text=question, return_tensors="pt").to(vlm_model.device)
            out = vlm_model.generate(**inputs, max_new_tokens=100)
            caption = vlm_processor.decode(out[0], skip_special_tokens=True)
            return f"关于'{question}'的回答：{caption}"
        elif "VisionEncoderDecoder" in model_type:
            # ViT-GPT2模型主要用于图像描述，不支持问答
            pixel_values = vlm_processor(images=image, return_tensors="pt").pixel_values.to(vlm_model.device)
            generated_ids = vlm_model.generate(pixel_values, max_length=50)
            generated_text = vlm_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return f"图像描述：{generated_text}\n\n关于问题'{question}'：该模型主要用于图像描述，无法直接回答问题。"
        else:
            # 通用处理
            prompt = f"请根据图片内容回答以下问题：{question}\n请详细分析图片中的相关信息。"
            inputs = vlm_processor(images=image, text=prompt, return_tensors="pt").to(vlm_model.device)
            generated_ids = vlm_model.generate(**inputs, max_new_tokens=1024)
            generated_text = vlm_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return generated_text
            
    except Exception as e:
        print(f"图像分析错误: {e}")
        return f"图像分析失败: {str(e)}"

def generate_search_queries(query, history):
    """
    让 AI 根据当前问题和历史记录，生成最适合搜索的 1-3 个关键词
    """
    prompt = f"""<|im_start|>system
你是一个搜索优化专家。请根据用户的提问和对话历史，提取出最适合在知识库中搜索的关键词。
要求：
1. 除去语气词，保留核心学术/技术名词。
2. 如果问题涉及比较，请拆分为多个关键词。
3. 直接输出关键词，用逗号分隔，不要有任何解释。
<|im_end|>
<|im_start|>user
【历史记录】：{history}
【当前问题】：{query}
生成搜索词：<|im_end|>
<|im_start|>assistant
"""
    inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
    outputs = model.generate(**inputs, max_new_tokens=50, temperature=0.1)
    refined_queries = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()

    # 将生成的字符串拆分为列表，例如 "微积分, 牛顿莱布尼茨公式" -> ["微积分", "牛顿莱布尼茨公式"]
    query_list = [q.strip() for q in refined_queries.split(',')]
    return query_list

# ========================== 多模态图像问答接口 ==========================
@app.route("/api/multimodal/qa", methods=["POST"])
@login_required
@rate_limit(limit=10, window=60)
def multimodal_qa():
    """多模态问答接口，支持图像+文本"""
    data = flask.request.json
    query = data.get('question')
    image_base64 = data.get('image')
    
    if not query and not image_base64:
        return flask.jsonify({"error": "问题或图像不能为空"}), 400
    
    query = sanitize_input(query, max_length=1000) if query else ""
    
    def generate():
        try:
            image_analysis = ""
            
            # 如果有图像，先处理图像
            if image_base64:
                image = process_image_base64(image_base64)
                if image:
                    if query:
                        # 图像+问题：视觉问答
                        image_analysis = analyze_image_with_question(image, query)
                    else:
                        # 只有图像：图像描述
                        image_analysis = extract_text_from_image(image)
            
            # 构建最终回答
            if image_analysis and not image_analysis.startswith("多模态模型未加载"):
                # 使用VLM模型的回答
                full_answer = image_analysis
            else:
                # 回退到纯文本问答
                if query:
                    history = get_history(current_user.id)
                    
                    # 生成搜索查询
                    search_keywords = generate_search_queries(query, history)
                    
                    # 检索相关文档
                    retrieved_context = ""
                    if retriever:
                        context_list = []
                        for kw in search_keywords:
                            docs = retriever.invoke(kw)
                            context_list.extend([d.page_content for d in docs])
                        
                        if context_list:
                            retrieved_context = "\n【本地文件参考】:\n" + "\n---\n".join(list(set(context_list)))
                    
                    # 权威知识检索
                    auth_context = find_authoritative_knowledge(query)
                    if auth_context:
                        retrieved_context += auth_context
                    
                    # 工具调用
                    tool_result = check_and_run_tools(query)
                    if tool_result:
                        retrieved_context += tool_result
                    
                    # 生成最终回答
                    system_prompt = "你是学习助手。请根据以下检索到的资料和对话历史回答用户。"
                    full_prompt = (
                        f"<|im_start|>system\n{system_prompt}\n\n"
                        f"【检索到的资料】:\n{retrieved_context if retrieved_context else '无需外部资料'}\n\n"
                        f"【对话历史记录】:\n{history}<|im_end|>\n"
                        f"<|im_start|>user\n{query}<|im_end|>\n"
                        f"<|im_start|>assistant\n"
                    )
                    
                    inputs = tokenizer(full_prompt, return_tensors="pt").to(DEVICE)
                    outputs = model.generate(**inputs, max_new_tokens=1024, temperature=0.7, do_sample=True)
                    full_answer = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
                else:
                    full_answer = "请提供问题或图像进行分析"
            
            # 流式输出
            for char in full_answer:
                yield f"data: {json.dumps({'token': char})}\n\n"
                import time
                time.sleep(0.01)  # 控制流式输出速度
            
            # 保存到数据库
            with app.app_context():
                new_record = Question(
                    content=f"[多模态] {query[:50]}..." if query else "[图像分析]",
                    answer=full_answer.strip(),
                    student_id=current_user.id
                )
                db.session.add(new_record)
                db.session.commit()
                
        except Exception as e:
            print(f"多模态问答错误: {e}")
            yield f"data: {json.dumps({'token': '处理失败，请重试。'})}\n\n"
    
    response = Response(stream_with_context(generate()), mimetype='text/event-stream')
    response.headers.update({'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'})
    return response

# ========================== 图像上传接口 ==========================
@app.route("/api/upload/image", methods=["POST"])
@login_required
@rate_limit(limit=5, window=60)
def upload_image():
    """上传图像并返回分析结果"""
    try:
        if 'image' not in flask.request.files:
            return flask.jsonify({"error": "没有上传文件"}), 400
        
        file = flask.request.files['image']
        
        # 检查文件类型
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return flask.jsonify({"error": "不支持的文件类型"}), 400
        
        # 读取图像
        image_data = file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # 转换为base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # 分析图像
        analysis = ""
        if vlm_available:
            analysis = extract_text_from_image(image)
        
        return flask.jsonify({
            "success": True,
            "image_base64": f"data:image/png;base64,{img_str}",
            "analysis": analysis,
            "message": "图像上传成功"
        }), 200
        
    except Exception as e:
        print(f"图像上传错误: {e}")
        return flask.jsonify({"error": f"图像处理失败: {str(e)}"}), 500

# ========================== AI 问答接口 ==========================
@app.route("/api/qa", methods=["POST"])
@login_required
@rate_limit(limit=10, window=60)
def qa():
    data = flask.request.json
    query = data.get('question')
    if not query: return flask.jsonify({"error": "问题不能为空"}), 400
    
    query = sanitize_input(query, max_length=1000)
    history = get_history(current_user.id)

    # ========================== 阶段 1：主动决策 ==========================
    # 告诉模型它有哪些“技能”，让它决定用哪个
    decision_system_prompt = (
        "你是一个学习助手决策中心。根据用户问题，选择最合适的工具。可用工具：\n"
        "- [SEARCH_AUTH]: 用户询问课程规定、老师讲过的重点或权威定义时使用。\n"
        "- [SEARCH_DOCS]: 用户询问具体课本知识、PDF文档内容或详细技术细节时使用。\n"
        "- [USE_TOOL]: 用户需要数学计算(calculate)或查询网页(fetch_url)时使用。\n"
        "- [DIRECT_REPLY]: 简单的寒暄、日常对话或无需参考资料的问题。\n"
        "请直接输出工具标签，不要解释。"
    )
    
    decision_prompt = (
        f"<|im_start|>system\n{decision_system_prompt}<|im_end|>\n"
        f"<|im_start|>user\n问题: {query}\n最近对话记录: {history}\n决策结果:<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    # 快速推理获取决策（非流式）
    d_inputs = tokenizer(decision_prompt, return_tensors="pt").to(DEVICE)
    d_outputs = model.generate(**d_inputs, max_new_tokens=20, temperature=0.1)
    decision = tokenizer.decode(d_outputs[0][d_inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()

    # ========================== 阶段 2：执行检索 ==========================
    retrieved_context = ""
    
    if "[SEARCH_AUTH]" in decision:
        retrieved_context += find_authoritative_knowledge(query)
    
    if "[SEARCH_DOCS]" in decision:
        if retriever:
            search_keywords = generate_search_queries(query, history)
            print(f"AI 决定的搜索关键词: {search_keywords}")

            context_list = []
            for kw in search_keywords:
                    docs = retriever.invoke(kw) # 使用 AI 生成的关键词进行检索
                    context_list.extend([d.page_content for d in docs])

            # 去重并合并背景资料
            retrieved_context += "\n【本地文件参考】:\n" + "\n---\n".join(list(set(context_list)))
            
    if "[USE_TOOL]" in decision:
        retrieved_context += check_and_run_tools(query)

    # ========================== 阶段 3：最终流式回答 ==========================
    final_system_prompt = (
        "你是学习助手。请根据以下检索到的资料和对话历史回答用户。\n"
        "如果资料中没有相关信息，请诚实回答。如果存在【权威参考】，必须以此为准。"
    )
    
    full_prompt = (
        f"<|im_start|>system\n{final_system_prompt}\n\n"
        f"【检索到的资料】:\n{retrieved_context if retrieved_context else '无需外部资料'}\n\n"
        f"【对话历史记录】:\n{history}<|im_end|>\n"
        f"<|im_start|>user\n{query}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    def generate():
        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, timeout=60)
        inputs = tokenizer(full_prompt, return_tensors="pt").to(DEVICE)
        generation_kwargs = dict(inputs, streamer=streamer, max_new_tokens=1024, temperature=0.7, do_sample=True)
        thread = threading.Thread(target=model.generate, kwargs=generation_kwargs)
        thread.start()

        full_answer = ""
        try:
            for token in streamer:
                if '<|im_end|>' in token: break
                full_answer += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            print(f"Stream error: {e}")
        
        with app.app_context():
            new_record = Question(content=query, answer=full_answer.strip(), student_id=current_user.id)
            db.session.add(new_record)
            db.session.commit()

    response = Response(stream_with_context(generate()), mimetype='text/event-stream')
    response.headers.update({'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no', 'Connection': 'keep-alive'})
    return response


# ========================== 留言与邮件系统 ==========================

@app.route("/api/messages", methods=["GET", "POST"])
@login_required
@rate_limit(limit=20, window=60)  # 每分钟最多20次留言操作
def handle_messages():
    if flask.request.method == "POST":
        data = flask.request.json
        if not data or 'content' not in data:
            return flask.jsonify({"error": "缺少留言内容"}), 400
        
        # 清理和验证留言内容
        new_content = sanitize_input(data['content'], max_length=1000)
        if not new_content or len(new_content.strip()) < 1:
            return flask.jsonify({"error": "留言内容不能为空"}), 400
        if len(new_content) > 1000:
            return flask.jsonify({"error": "留言内容不能超过1000字"}), 400
        
        # 1. 先把留言存入数据库（无论是否重复，都要存）
        message = Message(content=new_content, sender_id=current_user.id)
        db.session.add(message)
        db.session.commit()
        
        # 邮件去重逻辑开始
        send_email = True
        
        # 获取最近 1 小时内的留言进行比对
        one_hour_ago = datetime.utcnow() - timedelta(hours=24)
        recent_msgs = Message.query.filter(
            Message.timestamp >= one_hour_ago,
            Message.id != message.id # 排除刚刚存入的这条
        ).all()

        if recent_msgs:
            # 计算当前留言的向量
            new_vec = embedding.embed_query(new_content)
            
            for m in recent_msgs:
                # 计算与最近留言的相似度
                m_vec = embedding.embed_query(m.content)
                sim = util.cos_sim(new_vec, m_vec).item()
                
                if sim > 0.85: # 语义相似度阈值
                    print(f"检测到相似留言 (相似度: {sim:.2f})，取消邮件提醒。")
                    send_email = False
                    break
        # 邮件去重逻辑结束

        # 执行邮件发送
        if send_email and app.config.get('MAIL_SERVER') and app.config['MAIL_SERVER'] != 'smtp.example.com':
            try:
                teachers = User.query.filter_by(role='teacher').all()
                for teacher in teachers:
                    msg = MailMessage(
                        '【新留言提醒】学生提交了新问题',
                        recipients=[teacher.email],
                        body=f"老师您好，\n\n学生 ({current_user.username}) 提交了新留言：\n\n\"{new_content}\"\n\n系统检测到这是近期首条此类内容的留言，请及时查看。"
                    )
                    mail.send(msg)
            except Exception as e:
                print(f"Error sending email: {e}")
                
        return flask.jsonify({"message": "Message sent successfully", "notified": send_email}), 201

    if flask.request.method == "GET":
        if current_user.role == 'student':
            msgs = Message.query.filter_by(sender_id=current_user.id).order_by(Message.timestamp.desc()).all()
        else:
            msgs = Message.query.order_by(Message.timestamp.desc()).all()
            
        result = []
        for m in msgs:
            sender = db.session.get(User, m.sender_id)
            result.append({
                "id": m.id,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "sender": sender.username if sender else "Unknown",
                "status": m.status,
                "reply_content": m.reply_content,
                "reply_timestamp": m.reply_timestamp.isoformat() if m.reply_timestamp else None
            })
        return flask.jsonify(result), 200

@app.route("/api/messages/<int:msg_id>/reply", methods=["POST"])
@login_required
def reply_message(msg_id):
    if current_user.role != 'teacher':
        return flask.jsonify({"error": "Permission denied"}), 403
    data = flask.request.json
    if not data or 'reply_content' not in data:
        return flask.jsonify({"error": "Missing reply content"}), 400
    message = db.session.get(Message, msg_id)
    if not message:
        return flask.jsonify({"error": "Message not found"}), 404
    message.reply_content = data['reply_content']
    message.reply_timestamp = datetime.utcnow()
    message.replier_id = current_user.id
    message.status = 'replied'
    db.session.commit()
    return flask.jsonify({"message": "Replied successfully"}), 200

@app.after_request
def add_security_headers(response):
    """添加安全响应头"""
    # 防止MIME类型嗅探
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # 防止点击劫持
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    # 启用XSS保护
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # 内容安全策略（基础配置，可根据需要调整）
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:;"
    # 严格传输安全（生产环境应启用）
    if app.config['SESSION_COOKIE_SECURE']:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response

# ========================== 用户认证接口 ==========================

@app.route("/api/auth/register", methods=["POST"])
@rate_limit(limit=5, window=300)  # 5分钟内最多5次注册
def register():
    """用户注册接口"""
    data = flask.request.json
    if not data:
        return flask.jsonify({"error": "请求数据不能为空"}), 400
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'student')  # 默认学生
    
    # 验证必填字段
    if not username or not email or not password:
        return flask.jsonify({"error": "用户名、邮箱和密码不能为空"}), 400
    
    # 验证角色
    if role not in ['student', 'teacher']:
        return flask.jsonify({"error": "角色必须是 'student' 或 'teacher'"}), 400
    
    # 验证用户名格式
    if len(username) < 3 or len(username) > 20:
        return flask.jsonify({"error": "用户名长度必须在3-20个字符之间"}), 400
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return flask.jsonify({"error": "用户名只能包含字母、数字和下划线"}), 400
    
    # 验证邮箱格式
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return flask.jsonify({"error": "邮箱格式不正确"}), 400
    
    # 检查密码强度
    is_strong, message = is_strong_password(password)
    if not is_strong:
        return flask.jsonify({"error": message}), 400
    
    # 检查用户名和邮箱是否已存在
    existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        if existing_user.username == username:
            return flask.jsonify({"error": "用户名已存在"}), 409
        else:
            return flask.jsonify({"error": "邮箱已存在"}), 409
    
    try:
        # 哈希密码
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # 创建新用户
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            role=role
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # 自动登录
        login_user(new_user, remember=True)
        
        return flask.jsonify({
            "message": "注册成功",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "role": new_user.role
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"注册错误: {e}")
        return flask.jsonify({"error": "注册失败，请稍后重试"}), 500

@app.route("/api/register", methods=["POST"])
@rate_limit(limit=5, window=300)  # 5分钟内最多5次注册
def register_legacy():
    """用户注册接口（兼容旧版前端）"""
    data = flask.request.json
    if not data:
        return flask.jsonify({"error": "请求数据不能为空"}), 400
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'student')  # 默认学生
    
    # 验证必填字段
    if not username or not email or not password:
        return flask.jsonify({"error": "用户名、邮箱和密码不能为空"}), 400
    
    # 验证角色
    if role not in ['student', 'teacher']:
        return flask.jsonify({"error": "角色必须是 'student' 或 'teacher'"}), 400
    
    # 验证用户名格式
    if len(username) < 3 or len(username) > 20:
        return flask.jsonify({"error": "用户名长度必须在3-20个字符之间"}), 400
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return flask.jsonify({"error": "用户名只能包含字母、数字和下划线"}), 400
    
    # 验证邮箱格式
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return flask.jsonify({"error": "邮箱格式不正确"}), 400
    
    # 检查密码强度
    is_strong, message = is_strong_password(password)
    if not is_strong:
        return flask.jsonify({"error": message}), 400
    
    # 检查用户名和邮箱是否已存在
    existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        if existing_user.username == username:
            return flask.jsonify({"error": "用户名已存在"}), 409
        else:
            return flask.jsonify({"error": "邮箱已存在"}), 409
    
    try:
        # 哈希密码
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # 创建新用户
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            role=role
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # 自动登录
        login_user(new_user, remember=True)
        
        return flask.jsonify({
            "message": "注册成功",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "role": new_user.role
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"注册错误: {e}")
        return flask.jsonify({"error": "注册失败，请稍后重试"}), 500

@app.route("/api/auth/login", methods=["POST"])
@rate_limit(limit=10, window=300)  # 5分钟内最多10次登录尝试
def login():
    """用户登录接口"""
    data = flask.request.json
    if not data:
        return flask.jsonify({"error": "请求数据不能为空"}), 400
    
    username = data.get('username')
    password = data.get('password')
    remember = data.get('remember', True)
    
    if not username or not password:
        return flask.jsonify({"error": "用户名和密码不能为空"}), 400
    
    # 查找用户（支持用户名或邮箱登录）
    user = User.query.filter((User.username == username) | (User.email == username)).first()
    
    if not user:
        return flask.jsonify({"error": "用户名或密码错误"}), 401
    
    # 验证密码
    if not bcrypt.check_password_hash(user.password, password):
        return flask.jsonify({"error": "用户名或密码错误"}), 401
    
    # 登录用户
    login_user(user, remember=remember)
    
    return flask.jsonify({
        "message": "登录成功",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }), 200

@app.route("/api/login", methods=["POST"])
@rate_limit(limit=10, window=300)  # 5分钟内最多10次登录尝试
def login_legacy():
    """用户登录接口（兼容旧版前端）"""
    data = flask.request.json
    if not data:
        return flask.jsonify({"error": "请求数据不能为空"}), 400
    
    # 旧版前端使用email字段，新版使用username字段
    email = data.get('email')
    password = data.get('password')
    remember = data.get('remember', True)
    
    if not email or not password:
        return flask.jsonify({"error": "邮箱和密码不能为空"}), 400
    
    # 查找用户（使用邮箱登录）
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return flask.jsonify({"error": "邮箱或密码错误"}), 401
    
    # 验证密码
    if not bcrypt.check_password_hash(user.password, password):
        return flask.jsonify({"error": "邮箱或密码错误"}), 401
    
    # 登录用户
    login_user(user, remember=remember)
    
    return flask.jsonify({
        "message": "登录成功",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }), 200

@app.route("/api/auth/logout", methods=["POST"])
@login_required
def logout():
    """用户登出接口"""
    logout_user()
    return flask.jsonify({"message": "登出成功"}), 200

@app.route("/api/auth/me", methods=["GET"])
@login_required
def get_current_user_info():
    """获取当前用户信息"""
    return flask.jsonify({
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "learning_summary": current_user.learning_summary,
        "summary_updated_at": current_user.summary_updated_at.isoformat() if current_user.summary_updated_at else None
    }), 200

@app.route("/api/auth/check", methods=["GET"])
def check_auth():
    """检查用户是否已登录"""
    if current_user.is_authenticated:
        return flask.jsonify({
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "role": current_user.role
            }
        }), 200
    else:
        return flask.jsonify({"authenticated": False}), 200

@app.route("/api/check-auth", methods=["GET"])
def check_auth_legacy():
    """检查用户是否已登录（兼容旧版前端）"""
    if current_user.is_authenticated:
        return flask.jsonify({
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "role": current_user.role
            }
        }), 200
    else:
        return flask.jsonify({"authenticated": False}), 200

# ========================== 老师管理接口 ==========================

@app.route("/api/questions/pending", methods=["GET"])
@login_required
def get_pending_questions():
    """获取待处理问题列表（仅老师）"""
    if current_user.role != 'teacher':
        return flask.jsonify({"error": "权限不足"}), 403
    
    # 获取所有问题，包括AI回答和权威答案
    questions = Question.query.order_by(Question.timestamp.desc()).all()
    
    result = []
    for q in questions:
        student = db.session.get(User, q.student_id)
        teacher = db.session.get(User, q.teacher_id) if q.teacher_id else None
        
        result.append({
            "id": q.id,
            "content": q.content,
            "ai_answer": q.answer,
            "authoritative_answer": q.authoritative_answer,
            "student_name": student.username if student else "未知学生",
            "teacher_name": teacher.username if teacher else None,
            "timestamp": q.timestamp.isoformat(),
            "has_authoritative": q.authoritative_answer is not None
        })
    
    return flask.jsonify(result), 200

@app.route("/api/questions/<int:q_id>/authoritative", methods=["POST"])
@login_required
def submit_authoritative_answer(q_id):
    """提交权威答案（仅老师）"""
    if current_user.role != 'teacher':
        return flask.jsonify({"error": "权限不足"}), 403
    
    data = flask.request.json
    if not data or 'answer' not in data:
        return flask.jsonify({"error": "缺少答案内容"}), 400
    
    answer = sanitize_input(data['answer'], max_length=2000)
    if not answer or len(answer.strip()) < 1:
        return flask.jsonify({"error": "答案内容不能为空"}), 400
    
    question = db.session.get(Question, q_id)
    if not question:
        return flask.jsonify({"error": "问题不存在"}), 404
    
    # 更新权威答案
    question.authoritative_answer = answer
    question.teacher_id = current_user.id
    db.session.commit()
    
    return flask.jsonify({
        "message": "权威答案已提交",
        "question_id": q_id,
        "teacher_id": current_user.id
    }), 200

@app.route("/api/questions/<int:q_id>", methods=["DELETE"])
@login_required
def delete_question(q_id):
    """删除问题（仅老师）"""
    if current_user.role != 'teacher':
        return flask.jsonify({"error": "权限不足"}), 403
    
    question = db.session.get(Question, q_id)
    if not question:
        return flask.jsonify({"error": "问题不存在"}), 404
    
    db.session.delete(question)
    db.session.commit()
    
    return flask.jsonify({"message": "问题已删除"}), 200

if __name__ == "__main__":
    app.run(debug=False, port=5000, threaded=True)