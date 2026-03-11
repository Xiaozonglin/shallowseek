# 学习助手系统后端（RAG中文文档版）
import os
from dotenv import load_dotenv
import flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message as MailMessage
from datetime import datetime
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_huggingface import HuggingFacePipeline
from langchain_classic.chains import StuffDocumentsChain
from langchain_classic.chains.retrieval_qa.base import RetrievalQA
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import PromptTemplate
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForCausalLM, pipeline
import torch

# 设置 HuggingFace 镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 加载环境变量
load_dotenv()

# Flask 配置
app = flask.Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = os.getenv('EMAIL_HOST')
app.config['MAIL_PORT'] = int(os.getenv('EMAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('EMAIL_FROM')

# 初始化扩展
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
mail = Mail(app)

# 数据库模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'student' or 'teacher'
    questions = db.relationship('Question', backref='student', lazy=True)
    messages = db.relationship('Message', backref='sender', lazy=True)

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

# 初始化数据库
with app.app_context():
    db.create_all()

# 加载文档并初始化 AI 模型
def load_ai_model():
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        # docs路径
        docs_path = os.path.join(BASE_DIR, "..", "docs")
        # 加载文档
        loader = DirectoryLoader(
            path=docs_path,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"}
        )
        documents = loader.load()
        
        # 分割文档
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(documents)
        print(f"Split into {len(splits)} chunks")
        
        # 嵌入模型
        embedding = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5", model_kwargs={"trust_remote_code": True})
        
        # FAISS 向量存储
        if os.path.exists("faiss_index"):
            vectorstore = FAISS.load_local("faiss_index", embedding, allow_dangerous_deserialization=True)
        else:
            vectorstore = FAISS.from_documents(splits, embedding)
            vectorstore.save_local("faiss_index")
        
        # 初始化 LLM
        try:
            # 尝试加载 Qwen
            model_name = "Qwen/Qwen2.5-1.5B-Instruct"
            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True, device_map="auto")
            pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=512,
                do_sample=True,
                temperature=0.7,
                top_p=0.9
            )
            llm = HuggingFacePipeline(pipeline=pipe)
        except Exception as e:
            print(f"Error loading Qwen model: {e}")
            print("Using google/flan-t5-small as fallback")
            model_name = "google/flan-t5-small"
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            device = 0 if torch.cuda.is_available() else -1
            pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                device=device,
                max_new_tokens=256,
                do_sample=False,
                top_p=0.95,
                temperature=0.7,
                return_full_text=False
            )
            llm = HuggingFacePipeline(pipeline=pipe)

        # 构建 RAG QA chain
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        prompt = PromptTemplate(
            template="""
<|system|>
你是学习助手。

规则：
1. 只能使用资料内容回答
2. 不要编造信息
3. 不要生成额外参考链接
4. 如果资料没有答案，请回答：资料中没有相关信息
5. 学生让你解读代码或者将编程任务发给你时，不能直接将代码答案告诉学生，应当进行一定的引导

<|user|>
资料：
{context}

问题：
{question}

<|assistant|>
""",
            input_variables=["context", "question"]
        )
        document_chain = create_stuff_documents_chain(
            llm,
            prompt
        )
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            chain_type="stuff",
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True
        )
        return qa_chain
    except Exception as e:
        print(f"Error loading AI model: {e}")
        return None

qa_chain = load_ai_model()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ========================== 路由 ==========================

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
    if not data or 'question' not in data:
        return flask.jsonify({"error": "Missing question"}), 400
    if not qa_chain:
        return flask.jsonify({"error": "AI model not loaded"}), 500
    try:
        query_text = data['question']

        # 动态获取输入键（兼容 'query' 或 'question'）
        input_key = "query"  # 默认
        if hasattr(qa_chain, "input_keys") and qa_chain.input_keys:
            input_key = qa_chain.input_keys[0]  # 使用 chain 定义的首个输入键

        result = qa_chain.invoke({input_key: query_text})

        # 兼容不同版本的输出键
        answer = result.get("result") or result.get("answer") or "无法获取答案"
        source_docs = result.get("source_documents") or result.get("context") or []
        sources = [doc.metadata.get("source", "") for doc in source_docs]

        # 曲线救国，适配一天了还是没搞出来
        if "<|assistant|>" in answer:
            answer = answer.split("<|assistant|>")[-1].strip()
        
        # 保存到数据库
        question = Question(content=query_text, answer=answer, student_id=current_user.id)
        db.session.add(question)
        db.session.commit()

        return flask.jsonify({"answer": answer, "sources": sources}), 200
    except Exception as e:
        # 打印详细错误到控制台以便调试
        print(f"QA Error: {str(e)}")
        return flask.jsonify({"error": str(e)}), 500

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

# ========================== 启动 ==========================
if __name__ == "__main__":
    app.run(debug=os.getenv('DEBUG', 'True') == 'True')