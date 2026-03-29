import os
import json
import re
import torch
import threading
import requests
import sympy
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
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
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

os.makedirs(MODEL_PATH, exist_ok=True)
os.makedirs(EMBED_PATH, exist_ok=True)

def is_locally_available(path):
    return os.path.exists(os.path.join(path, "config.json"))

print("🚀 正在初始化 RTX 5060 加速引擎...")

# 1. 加载 LLM
if not is_locally_available(MODEL_PATH):
    print("🌐 第一次运行：正在从镜像站拉取 Qwen 模型...")
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
    print("🌐 第一次运行：正在拉取 BGE 向量模型...")
    e_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    e_model.save(EMBED_PATH)

embedding = HuggingFaceEmbeddings(
    model_name=EMBED_PATH, 
    model_kwargs={'device': DEVICE},
    encode_kwargs={'normalize_embeddings': True}
)

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
    """
    检索数据库中老师提供的权威答案
    """
    # 查找所有包含权威答案的问题
    auth_questions = Question.query.filter(Question.authoritative_answer != None).all()
    if not auth_questions:
        return ""
    
    # 简单的语义匹配逻辑：通过 Embedding 计算当前问题与已有权威问题的相似度
    query_vec = embedding.embed_query(query)
    best_match = None
    max_sim = 0.0
    
    for q in auth_questions:
        # 这里为了演示使用实时计算，实际生产环境建议将权威答案也存入 FAISS
        q_vec = embedding.embed_query(q.content)
        sim = util.cos_sim(query_vec, q_vec).item()
        if sim > max_sim:
            max_sim = sim
            best_match = q
            
    # 如果相似度高于阈值 (例如 0.8)，则作为权威参考提供
    if best_match and max_sim > 0.8:
        return f"\n【老师提供的权威参考内容 (匹配度: {max_sim:.2f})】:\n{best_match.authoritative_answer}\n"
    return ""

def check_and_run_tools(query):
    system_msg = (
        "你是一个工具决策器。根据用户提问，判断是否需要调用外部工具。可用工具：\n"
        "1. fetch_url(url: 网址) - 用于访问特定网址。\n"
        "2. calculate(expr: 表达式) - 用于数学计算。\n"
        "如果需要访问网页，严格输出：CALL:fetch_url|网址\n"
        "如果需要计算，严格输出：CALL:calculate|数学表达式\n"
        "如果都不需要，严格输出：NONE"
    )
    
    prompt = f"<|im_start|>system\n{system_msg}<|im_end|>\n<|im_start|>user\n{query}<|im_end|>\n<|im_start|>assistant\n"
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs, max_new_tokens=30, temperature=0.1, do_sample=False)
    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
    
    tool_result = ""
    if response.startswith("CALL:fetch_url|"):
        url = response.split("|", 1)[1].strip()
        try:
            res = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(res.text, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)[:1000]
            tool_result = f"\n【AI工具: 从 {url} 抓取的内容】:\n{text}\n"
        except Exception as e:
            tool_result = f"\n【AI工具: 访问网页失败】: {str(e)}\n"
    elif response.startswith("CALL:calculate|"):
        expr = response.split("|", 1)[1].strip()
        try:
            ans = sympy.sympify(expr).evalf()
            tool_result = f"\n【AI工具: 数学计算结果】: {expr} = {ans}\n"
        except Exception as e:
            tool_result = f"\n【AI工具: 计算解析失败】: {str(e)}\n"
            
    return tool_result

# ========================== 路由逻辑 ==========================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route("/api/register", methods=["POST"])
@rate_limit(limit=5, window=300)  # 5分钟内最多5次注册尝试
def register():
    data = flask.request.json
    if not data or 'username' not in data or 'email' not in data or 'password' not in data or 'role' not in data:
        return flask.jsonify({"error": "Missing required fields"}), 400
    
    # 用户名验证
    username = sanitize_input(data['username'], max_length=20)
    if not username or len(username) < 3:
        return flask.jsonify({"error": "用户名至少需要3个字符"}), 400
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return flask.jsonify({"error": "用户名只能包含字母、数字和下划线"}), 400
    
    # 邮箱验证
    email = sanitize_input(data['email'], max_length=120).lower()
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return flask.jsonify({"error": "邮箱格式不正确"}), 400
    
    # 密码强度验证
    password = data['password']
    is_valid, msg = is_strong_password(password)
    if not is_valid:
        return flask.jsonify({"error": msg}), 400
    
    # 角色验证
    role = sanitize_input(data['role'], max_length=10)
    if role not in ['student', 'teacher']:
        return flask.jsonify({"error": "角色必须是 student 或 teacher"}), 400
    
    # 检查重复
    if User.query.filter_by(username=username).first():
        return flask.jsonify({"error": "用户名已存在"}), 400
    if User.query.filter_by(email=email).first():
        return flask.jsonify({"error": "邮箱已被注册"}), 400
    
    # 创建用户
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(username=username, email=email, password=hashed_password, role=role)
    db.session.add(user)
    db.session.commit()
    return flask.jsonify({"message": "注册成功"}), 201

@app.route("/api/login", methods=["POST"])
@rate_limit(limit=5, window=300)  # 5分钟内最多5次登录尝试
def login():
    data = flask.request.json
    if not data or 'email' not in data or 'password' not in data:
        return flask.jsonify({"error": "缺少必填字段"}), 400
    
    # 清理输入
    email = sanitize_input(data['email'], max_length=120).lower()
    password = data['password']
    
    # 邮箱格式验证
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return flask.jsonify({"error": "邮箱格式不正确"}), 400
    
    # 密码长度限制
    if len(password) > 128:
        return flask.jsonify({"error": "密码过长"}), 400
    
    # 验证用户
    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return flask.jsonify({"error": "邮箱或密码错误"}), 401
    
    login_user(user)
    return flask.jsonify({"message": "登录成功", "role": user.role}), 200

@app.route("/api/check-auth", methods=["GET"])
def check_auth():
    """检查用户登录状态"""
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
        return flask.jsonify({"authenticated": False}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    # 移除@login_required装饰器，允许任何用户调用登出
    # 即使session已经过期，也应该允许用户登出
    try:
        logout_user()
        return flask.jsonify({"message": "Logout successful"}), 200
    except Exception as e:
        # 即使登出失败，也返回成功，让前端可以跳转到登录页
        print(f"Logout error: {e}")
        return flask.jsonify({"message": "Logout successful"}), 200

# ========================== 学生历史问答接口 ==========================

@app.route("/api/student/questions/history", methods=["GET"])
@login_required
def get_student_question_history():
    """获取当前学生的历史问答记录"""
    if current_user.role != 'student':
        return flask.jsonify({"error": "Permission denied"}), 403
    
    # 获取最近50条问答记录
    questions = Question.query.filter_by(
        student_id=current_user.id
    ).order_by(Question.timestamp.desc()).limit(50).all()
    
    result = []
    for q in questions:
        result.append({
            "id": q.id,
            "question": q.content,
            "answer": q.answer,
            "authoritative_answer": q.authoritative_answer,
            "timestamp": q.timestamp.isoformat()
        })
    
    return flask.jsonify(result), 200

# ========================== 权威答案管理 (老师专属) ==========================

@app.route("/api/questions/stats", methods=["GET"])
@login_required
def get_question_stats():
    """获取问题统计数据"""
    if current_user.role != 'teacher':
        return flask.jsonify({"error": "Permission denied"}), 403
    
    # 获取所有问题
    questions = Question.query.all()
    
    # 统计总提问数
    total_questions = len(questions)
    
    # 按学生分组统计
    questions_by_student = {}
    student_summaries = {}
    
    for q in questions:
        student = db.session.get(User, q.student_id)
        if student:
            if student.username not in questions_by_student:
                questions_by_student[student.username] = []
            questions_by_student[student.username].append({
                "question": q.content,
                "answer": q.answer
            })
    
    # 为每个学生生成 AI 学习情况分析
    for student_name, qa_list in questions_by_student.items():
        # 查找学生用户
        student_user = User.query.filter_by(username=student_name).first()
        
        # 检查是否需要更新分析（每24小时更新一次）
        need_update = False
        if student_user:
            if not student_user.summary_updated_at:
                need_update = True
            elif (datetime.utcnow() - student_user.summary_updated_at).total_seconds() > 86400:  # 24小时
                need_update = True
        
        # 如果有缓存且不需要更新，使用缓存
        if student_user and student_user.learning_summary and not need_update:
            student_summaries[student_name] = student_user.learning_summary
            continue
        
        # 构建学生的学习内容
        qa_text = "\n".join([
            f"问题: {qa['question']}\n回答摘要: {qa['answer'][:100] if qa['answer'] else '无'}..."
            for qa in qa_list[:5]  # 最多取5个问题
        ])
        
        # 调用 AI 生成学习情况分析
        prompt = f"""<|im_start|>system
你是一位教育专家，请根据学生的提问记录，分析该学生的学习情况。请简要总结学生的学习兴趣、知识薄弱点和建议。回答要简洁，不超过100字。
<|im_end|>
<|im_start|>user
学生 {student_name} 的提问记录如下：
{qa_text}

请分析该学生的学习情况。
<|im_end|>
<|im_start|>assistant
"""
        
        try:
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            outputs = model.generate(
                **inputs,
                max_new_tokens=150,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
            full_output = tokenizer.decode(outputs[0], skip_special_tokens=False)
            
            # 提取 assistant 的回复
            summary = full_output
            
            # 方法1：找到最后一个 <|im_start|>assistant 之后的内容
            if "<|im_start|>assistant" in full_output:
                parts = full_output.split("<|im_start|>assistant")
                if len(parts) > 1:
                    summary = parts[-1]
                    # 移除 <|im_end|> 标记
                    if "<|im_end|>" in summary:
                        summary = summary.split("<|im_end|>")[0]
                    summary = summary.strip()
            
            # 方法2：如果方法1失败，尝试其他方式
            if not summary or len(summary) < 10:
                # 移除所有特殊标记后重新尝试
                clean_output = full_output.replace('<|im_start|>', '').replace('<|im_end|>', '')
                clean_output = clean_output.replace('', '')
                
                # 移除 system 和 user 部分
                if "system" in clean_output:
                    clean_output = clean_output.split("system")[0]
                if "user" in clean_output:
                    clean_output = clean_output.split("user")[0]
                
                # 提取 assistant 之后的内容
                if "assistant" in clean_output:
                    clean_output = clean_output.split("assistant")[-1]
                
                summary = clean_output.strip()
            
            # 方法3：如果还是失败，取最后一段有意义的文本
            if not summary or len(summary) < 10:
                lines = full_output.replace('<|im_start|>', '\n').replace('<|im_end|>', '\n')
                lines = lines.split('\n')
                for line in reversed(lines):
                    line = line.strip()
                    if line and len(line) > 10 and not line.startswith('<|') and 'system' not in line.lower() and 'user' not in line.lower():
                        summary = line
                        break
            
            student_summaries[student_name] = summary if summary and len(summary) >= 10 else f"该学生共提问 {len(qa_list)} 次"
            
            # 存储到数据库
            if student_user:
                student_user.learning_summary = student_summaries[student_name]
                student_user.summary_updated_at = datetime.utcnow()
                db.session.commit()
                
        except Exception as e:
            print(f"生成学习情况分析失败: {e}")
            student_summaries[student_name] = f"该学生共提问 {len(qa_list)} 次"
    
    # 生成总体 AI 总结
    overall_summary = f"共有 {total_questions} 个问题，来自 {len(questions_by_student)} 位学生。"
    
    return flask.jsonify({
        "total_questions": total_questions,
        "questions_by_student": questions_by_student,
        "student_summaries": student_summaries,
        "summary": overall_summary
    }), 200

@app.route("/api/questions/pending", methods=["GET"])
@login_required
def get_pending_questions():
    """获取所有学生的问题，方便老师查看并提供权威回复"""
    if current_user.role != 'teacher':
        return flask.jsonify({"error": "Permission denied"}), 403
    
    questions = Question.query.order_by(Question.timestamp.desc()).all()
    result = []
    for q in questions:
        student = db.session.get(User, q.student_id)
        result.append({
            "id": q.id,
            "content": q.content,
            "ai_answer": q.answer,
            "authoritative_answer": q.authoritative_answer,
            "student_name": student.username if student else "Unknown",
            "timestamp": q.timestamp.isoformat()
        })
    return flask.jsonify(result), 200

@app.route("/api/questions/<int:q_id>/authoritative", methods=["POST"])
@login_required
def set_authoritative_answer(q_id):
    """老师针对某个问题提供权威答案"""
    if current_user.role != 'teacher':
        return flask.jsonify({"error": "Permission denied"}), 403
    
    data = flask.request.json
    if not data or 'answer' not in data:
        return flask.jsonify({"error": "Missing answer content"}), 400
    
    question = db.session.get(Question, q_id)
    if not question:
        return flask.jsonify({"error": "Question not found"}), 404
    
    question.authoritative_answer = data['answer']
    question.teacher_id = current_user.id
    db.session.commit()
    
    return flask.jsonify({"message": "Authoritative answer updated. AI will now prioritize this info."}), 200

# ========================== AI 问答接口 ==========================
@app.route("/api/qa", methods=["POST"])
@login_required
@rate_limit(limit=10, window=60)  # 每分钟最多10次提问
def qa():
    data = flask.request.json
    query = data.get('question')
    if not query: return flask.jsonify({"error": "问题不能为空"}), 400
    
    # 清理和验证问题内容
    query = sanitize_input(query, max_length=1000)
    if not query or len(query.strip()) < 1:
        return flask.jsonify({"error": "问题不能为空"}), 400

    # 1. 核心：检索老师提供的权威知识 (最高优先级)
    authoritative_context = find_authoritative_knowledge(query)

    # 2. AI 极速前置工具推断
    tool_context = check_and_run_tools(query)

    # 3. 检索本地文件知识库
    context = ""
    if retriever:
        docs = retriever.invoke(query)
        context = "\n".join([d.page_content for d in docs])
    
    # 4. 获取对话历史
    history = get_history(current_user.id)

    # 5. 构造 Prompt
    # 注意：权威答案放在了最显眼的位置，并要求 AI 优先参考
    full_prompt = (
        f"<|im_start|>system\n你是学习助手。请参考以下资料回答。如果【权威参考】存在且与问题相关，请务必以该答案为准。\n\n"
        f"【权威参考】:\n{authoritative_context if authoritative_context else '暂无老师提供的权威参考资料。'}\n\n"
        f"【本地资料库】:\n{context}\n\n"
        f"{tool_context}\n"
        f"【历史记录】:\n{history}<|im_end|>\n"
        f"<|im_start|>user\n{query}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    def generate():
        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, timeout=60)
        inputs = tokenizer(full_prompt, return_tensors="pt").to(DEVICE)
        generation_kwargs = dict(inputs, streamer=streamer, max_new_tokens=512, temperature=0.7, do_sample=True)
        thread = threading.Thread(target=model.generate, kwargs=generation_kwargs)
        thread.start()

        full_answer = ""
        try:
            for token in streamer:
                # 过滤特殊标记
                if '<|im_end|>' in token or '<|im_start|>' in token:
                    token = token.replace('<|im_end|>', '').replace('<|im_start|>', '')
                    if not token.strip():
                        continue
                full_answer += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            print(f"Stream error: {e}")
        
        with app.app_context():
            new_record = Question(content=query, answer=full_answer.strip(), student_id=current_user.id)
            db.session.add(new_record)
            db.session.commit()

    # 禁用缓冲，确保实时传输
    response = Response(stream_with_context(generate()), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
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

if __name__ == "__main__":
    app.run(debug=False, port=5000, threaded=True)