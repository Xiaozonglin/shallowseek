import os
import json
import torch
import threading
from datetime import datetime
from dotenv import load_dotenv

# --- 核心：RTX 5060 兼容性与性能补丁 ---
# 必须在 import torch 之前设置
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

# ========================== 基础配置 ==========================
load_dotenv()
app = flask.Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_default_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['MAIL_SERVER'] = os.getenv('EMAIL_HOST')
app.config['MAIL_PORT'] = int(os.getenv('EMAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
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
    questions = db.relationship('Question', backref='student', lazy=True)

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

with app.app_context():
    db.create_all()

# ========================== AI 模型初始化 (RTX 5060 加速版) ==========================
print("🚀 正在初始化 RTX 5060 加速引擎...")

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    dtype=torch.float16,  # 半精度，5060 运行极快
    device_map="auto",          # 自动挂载到显卡
    trust_remote_code=True
)

# RAG 检索器初始化
embedding = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")
vectorstore = None

def init_vector_db():
    global vectorstore
    faiss_path = "faiss_index"
    if os.path.exists(faiss_path):
        vectorstore = FAISS.load_local(faiss_path, embedding, allow_dangerous_deserialization=True)
    else:
        # 自动扫描 docs 目录下的 md 文件
        docs_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
        if not os.path.exists(docs_dir): os.makedirs(docs_dir)
        loader = DirectoryLoader(docs_dir, glob="**/*.md", loader_cls=TextLoader)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
        splits = text_splitter.split_documents(documents)
        vectorstore = FAISS.from_documents(splits, embedding)
        vectorstore.save_local(faiss_path)
    return vectorstore.as_retriever(search_kwargs={"k": 3})

retriever = init_vector_db()

# ========================== 业务逻辑 ==========================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def get_history(user_id):
    # 从数据库获取最近 3 轮对话作为上下文
    records = Question.query.filter_by(student_id=user_id).order_by(Question.timestamp.desc()).limit(3).all()
    records.reverse()
    return "\n".join([f"问：{r.content}\n答：{r.answer}" for r in records])

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

@app.route("/api/qa", methods=["POST"])
@login_required
def qa():
    data = flask.request.json
    query = data.get('question')
    if not query: return flask.jsonify({"error": "Empty question"}), 400

    # 1. 检索知识库
    docs = retriever.invoke(query)
    context = "\n".join([d.page_content for d in docs])
    
    # 2. 获取对话历史
    history = get_history(current_user.id)

    # 3. 构造 Qwen 专用 Prompt
    full_prompt = (
        f"<|im_start|>system\n你是学习助手。请参考以下资料回答问题。\n\n"
        f"【资料】:\n{context}\n\n"
        f"【历史记录】:\n{history}<|im_end|>\n"
        f"<|im_start|>user\n{query}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    def generate():
        # 使用 TextIteratorStreamer 实现打字机效果
        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, timeout=10)
        inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)
        
        generation_kwargs = dict(inputs, streamer=streamer, max_new_tokens=512, temperature=0.7, do_sample=True)
        thread = threading.Thread(target=model.generate, kwargs=generation_kwargs)
        thread.start()

        full_answer = ""
        for token in streamer:
            full_answer += token
            # 每一个 chunk 都要符合 SSE 格式：data: 内容\n\n
            yield f"data: {json.dumps({'token': token})}\n\n"
        
        # 4. 生成结束后，存入数据库
        # 注意：在 generate() 这种生成器里，需要手动推入 app_context
        with app.app_context():
            new_record = Question(content=query, answer=full_answer.strip(), student_id=current_user.id)
            db.session.add(new_record)
            db.session.commit()

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route("/api/messages", methods=["POST"])
@login_required
def send_message():
    data = flask.request.json
    if not data or 'content' not in data:
        return flask.jsonify({"error": "Missing message content"}), 400
    message = Message(content=data['content'], sender_id=current_user.id)
    db.session.add(message)
    db.session.commit()
    try:
        teachers = User.query.filter_by(role='teacher').all()
        for teacher in teachers:
            msg = MailMessage(
                'New message from student',
                recipients=[teacher.email],
                body=f"You have a new message from {current_user.username}:\n\n{data['content']}"
            )
            mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")
    return flask.jsonify({"message": "Message sent successfully"}), 201



if __name__ == "__main__":
    # threaded=True 必须开启以支持流式传输
    app.run(debug=False, port=5000, threaded=True)