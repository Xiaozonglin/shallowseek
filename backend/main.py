# 学习助手系统后端
import os
from dotenv import load_dotenv
import flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from datetime import datetime
import sqlalchemy
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFacePipeline
from langchain_community.vectorstores import FAISS
from langchain_classic.chains.retrieval_qa.base import RetrievalQA
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
from langchain_core.prompts import PromptTemplate
import torch


# 加载配置
load_dotenv()

# 应用配置
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


# 加载文档和初始化AI模型
def load_ai_model():
    try:
        # 加载文档
        loader = DirectoryLoader(
            path="../docs",
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"}
        )
        documents = loader.load()

        # 分割文档
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
        splits = text_splitter.split_documents(documents)
        print(f"Split into {len(splits)} chunks")

        # 初始化嵌入模�?
        embedding = HuggingFaceEmbeddings(
            model_name=os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        )

        # 构建向量存储
        vectorstore = FAISS.from_documents(splits, embedding)
        vectorstore.save_local("faiss_index")

        # 初始化LLM
        model_name = os.getenv('MODEL_NAME', 'google/flan-t5-base')
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

        device = 0 if torch.cuda.is_available() else -1

        pipe = pipeline(
            "text2text-generation",
            model=model,
            tokenizer=tokenizer,
            device=device,
            max_new_tokens=256,
            do_sample=True,
            top_p=0.95,
            temperature=0.7
        )

        llm = HuggingFacePipeline(pipeline=pipe)

        # 构建RAG QA�?
        retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

        prompt = PromptTemplate(
            template="""You are a helpful assistant. Based on the document content below, provide a comprehensive, detailed, and informative answer to the question. If the document doesn't provide an answer, respond with "Unable to answer."

Document content:
{context}

Question: {question}
Full answer:""",
            input_variables=["context", "question"]
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            chain_type="stuff",
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt}
        )

        return qa_chain
    except Exception as e:
        print(f"Error loading AI model: {e}")
        return None


# 加载AI模型
qa_chain = load_ai_model()


# 登录管理器回�?
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# 路由
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
    user = User(
        username=data['username'],
        email=data['email'],
        password=hashed_password,
        role=data['role']
    )

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
        query = data['question']
        result = qa_chain.invoke(query)

        # 记录问题到数据库
        question = Question(
            content=query,
            answer=result["result"],
            student_id=current_user.id
        )
        db.session.add(question)
        db.session.commit()

        return flask.jsonify({"answer": result["result"]}), 200
    except Exception as e:
        return flask.jsonify({"error": str(e)}), 500


@app.route("/api/questions/stats", methods=["GET"])
@login_required
def get_question_stats():
    if current_user.role != 'teacher':
        return flask.jsonify({"error": "Access denied"}), 403

    # 获取所有问�?
    questions = Question.query.all()

    # 生成统计信息
    stats = {
        "total_questions": len(questions),
        "questions_by_student": {}
    }

    # 按学生分�?
    for question in questions:
        student_name = question.student.username
        if student_name not in stats["questions_by_student"]:
            stats["questions_by_student"][student_name] = []
        stats["questions_by_student"][student_name].append({
            "content": question.content,
            "answer": question.answer,
            "timestamp": question.timestamp.isoformat()
        })

    # 生成AI总结
    if questions:
        # 构建总结提示
        questions_text = "\n".join([q.content for q in questions])
        summary_prompt = f"Please summarize the following student questions:\n{questions_text}"

        if qa_chain:
            summary_result = qa_chain.invoke(summary_prompt)
            stats["summary"] = summary_result["result"]

    return flask.jsonify(stats), 200


@app.route("/api/messages", methods=["POST"])
@login_required
def send_message():
    data = flask.request.json
    if not data or 'content' not in data:
        return flask.jsonify({"error": "Missing message content"}), 400

    # 创建留言
    message = Message(
        content=data['content'],
        sender_id=current_user.id
    )
    db.session.add(message)
    db.session.commit()

    # 发送邮件提醒老师
    try:
        teachers = User.query.filter_by(role='teacher').all()
        for teacher in teachers:
            msg = Message(
                'New message from student',
                recipients=[teacher.email],
                body=f"You have a new message from {current_user.username}:\n\n{data['content']}"
            )
            mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")

    return flask.jsonify({"message": "Message sent successfully"}), 201


# Swagger API文档

if __name__ == "__main__":
    app.run(debug=os.getenv('DEBUG', 'True') == 'True')
