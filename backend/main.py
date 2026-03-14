import os
import json
import torch
import threading
import requests
import sympy
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

# --- 核心：RTX 5060 兼容性与性能补丁 ---
os.environ["CUDA_MODULE_LOADING"] = "LAZY"  # 延迟加载，防止初始化卡死
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com" # 镜像加速

import flask
from flask import Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message as MailMessage

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
from sentence_transformers import SentenceTransformer

# ========================== 基础配置 ==========================
load_dotenv()
app = flask.Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_default_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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

# ========================== 数据库模型 ==========================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(10), nullable=False) # 'student' or 'teacher'

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(1000), nullable=False)
    answer = db.Column(db.String(2000), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(1000), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='unread')
    
    # --- 新增：老师回复相关字段 ---
    reply_content = db.Column(db.String(2000), nullable=True)
    reply_timestamp = db.Column(db.DateTime, nullable=True)
    replier_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

with app.app_context():
    db.create_all()

# ========================== AI 模型初始化 ==========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 确保权重存在项目根目录下的对应文件夹
MODEL_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "model_weights"))
EMBED_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "rag-embedding"))

os.makedirs(MODEL_PATH, exist_ok=True)
os.makedirs(EMBED_PATH, exist_ok=True)

def is_locally_available(path):
    # 检查是否存在核心配置文件
    return os.path.exists(os.path.join(path, "config.json"))

print("🚀 正在初始化 RTX 5060 加速引擎...")

# 1. 加载 LLM (Qwen)
if not is_locally_available(MODEL_PATH):
    print("🌐 第一次运行：正在从镜像站拉取 Qwen 模型...")
    t_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", trust_remote_code=True)
    t_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", torch_dtype=torch.float16, device_map="auto", trust_remote_code=True)
    t_tokenizer.save_pretrained(MODEL_PATH)
    t_model.save_pretrained(MODEL_PATH)
    print(f"✅ Qwen 已保存至: {MODEL_PATH}")

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, torch_dtype=torch.float16, device_map="auto", local_files_only=True, trust_remote_code=True)

# 2. 加载 Embedding (BGE)
if not is_locally_available(EMBED_PATH):
    print("🌐 第一次运行：正在拉取 BGE 向量模型...")
    e_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    e_model.save(EMBED_PATH) # 关键：save 方法会直接平铺文件在根目录
    print(f"✅ Embedding 已保存至: {EMBED_PATH}")

embedding = HuggingFaceEmbeddings(
    model_name=EMBED_PATH, 
    model_kwargs={'device': 'cuda'},
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
        loader = DirectoryLoader(docs_dir, glob="**/*.md", loader_cls=TextLoader)
        docs = loader.load()
        if not docs: return None
        splits = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100).split_documents(docs)
        vstore = FAISS.from_documents(splits, embedding)
        vstore.save_local(faiss_path)
    return vstore.as_retriever(search_kwargs={"k": 3})

retriever = init_vector_db()

# ========================== 核心业务工具库 ==========================

def get_history(user_id):
    records = Question.query.filter_by(student_id=user_id).order_by(Question.timestamp.desc()).limit(3).all()
    records.reverse()
    return "\n".join([f"问：{r.content}\n答：{r.answer}" for r in records])

def check_and_run_tools(query):
    """
    AI 工具预处理模块：利用极速的单次推理判断是否需要调用工具
    """
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
    
    # 极速推理，限制最多输出 30 个 token
    outputs = model.generate(**inputs, max_new_tokens=30, temperature=0.1, do_sample=False)
    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
    
    tool_result = ""
    if response.startswith("CALL:fetch_url|"):
        url = response.split("|", 1)[1].strip()
        try:
            res = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(res.text, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)[:1000] # 截取前 1000 字防止爆显存
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

# ... (注册和登录逻辑与之前保持一致) ...
@app.route("/api/register", methods=["POST"])
def register():
    data = flask.request.json
    if not data or 'username' not in data or 'email' not in data or 'password' not in data or 'role' not in data:
        return flask.jsonify({"error": "Missing required fields"}), 400
    if User.query.filter_by(username=data['username']).first():
        return flask.jsonify({"error": "Username already exists"}), 400
    if User.query.filter_by(email=data['email']).first():
        return flask.jsonify({"error": "Email already exists"}), 400
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = User(username=data['username'], email=data['email'], password=hashed_password, role=data['role'])
    db.session.add(user)
    db.session.commit()
    return flask.jsonify({"message": "User registered successfully"}), 201

@app.route("/api/login", methods=["POST"])
def login():
    data = flask.request.json
    if not data or 'email' not in data or 'password' not in data:
        return flask.jsonify({"error": "Missing required fields"}), 400
    user = User.query.filter_by(email=data['email']).first()
    if not user or not bcrypt.check_password_hash(user.password, data['password']):
        return flask.jsonify({"error": "Invalid email or password"}), 401
    login_user(user)
    return flask.jsonify({"message": "Login successful", "role": user.role}), 200

@app.route("/api/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return flask.jsonify({"message": "Logout successful"}), 200

# ========================== AI 问答接口 ==========================
@app.route("/api/qa", methods=["POST"])
@login_required
def qa():
    data = flask.request.json
    query = data.get('question')
    if not query: return flask.jsonify({"error": "Empty question"}), 400

    # 1. AI 极速前置工具推断 (获取网页或计算数学)
    tool_context = check_and_run_tools(query)

    # 2. 检索本地知识库
    context = ""
    if retriever:
        docs = retriever.invoke(query)
        context = "\n".join([d.page_content for d in docs])
    
    # 3. 获取对话历史
    history = get_history(current_user.id)

    # 4. 构造包含所有工具反馈的终极 Prompt
    full_prompt = (
        f"<|im_start|>system\n你是学习助手。请参考以下资料和历史回答问题。\n\n"
        f"【本地资料】:\n{context}\n\n"
        f"{tool_context}\n"  # 注入工具运行结果
        f"【历史记录】:\n{history}<|im_end|>\n"
        f"<|im_start|>user\n{query}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    def generate():
        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, timeout=10)
        inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)
        
        generation_kwargs = dict(inputs, streamer=streamer, max_new_tokens=512, temperature=0.7, do_sample=True)
        thread = threading.Thread(target=model.generate, kwargs=generation_kwargs)
        thread.start()

        full_answer = ""
        for token in streamer:
            full_answer += token
            yield f"data: {json.dumps({'token': token})}\n\n"
        
        with app.app_context():
            new_record = Question(content=query, answer=full_answer.strip(), student_id=current_user.id)
            db.session.add(new_record)
            db.session.commit()

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


# ========================== 留言与邮件系统 ==========================

@app.route("/api/messages", methods=["GET", "POST"])
@login_required
def handle_messages():
    # 1. 提交新留言 (学生可用)
    if flask.request.method == "POST":
        data = flask.request.json
        if not data or 'content' not in data:
            return flask.jsonify({"error": "Missing message content"}), 400
        
        message = Message(content=data['content'], sender_id=current_user.id)
        db.session.add(message)
        db.session.commit()
        
        # 判断环境是否配置了真实的邮件服务
        if app.config.get('MAIL_SERVER') and app.config['MAIL_SERVER'] != 'smtp.example.com':
            try:
                teachers = User.query.filter_by(role='teacher').all()
                for teacher in teachers:
                    msg = MailMessage(
                        '收到新的学生留言',
                        recipients=[teacher.email],
                        body=f"老师您好，\n\n您有一条来自学生 ({current_user.username}) 的新留言：\n\n\"{data['content']}\"\n\n请登录系统查看和回复。"
                    )
                    mail.send(msg)
            except Exception as e:
                print(f"Error sending email: {e}")
                
        return flask.jsonify({"message": "Message sent successfully"}), 201

    # 2. 获取留言列表
    if flask.request.method == "GET":
        if current_user.role == 'student':
            # 学生只能看自己发出的留言及老师的回复
            msgs = Message.query.filter_by(sender_id=current_user.id).order_by(Message.timestamp.desc()).all()
        else:
            # 老师可以看到所有留言
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
    # 仅老师可以回复
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

if __name__ == "__main__":
    app.run(debug=False, port=5000, threaded=True)