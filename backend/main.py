import os
import json
import re
import torch
import threading
import base64
import io
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from time import time
from PIL import Image

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
from sentence_transformers import SentenceTransformer, util

# ========================== 基础与安全配置 ==========================
from dotenv import load_dotenv
load_dotenv()

app = flask.Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'dev_secure_key_5060'),
    SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', 'sqlite:///learning_platform.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_HTTPONLY=True,
    # 邮件配置
    MAIL_SERVER=os.getenv('EMAIL_HOST', 'smtp.example.com'),
    MAIL_PORT=int(os.getenv('EMAIL_PORT', 587)),
    MAIL_USE_TLS=os.getenv('EMAIL_USE_TLS', 'True').lower() in ['true', '1'],
    MAIL_USERNAME=os.getenv('EMAIL_USERNAME'),
    MAIL_PASSWORD=os.getenv('EMAIL_PASSWORD'),
    MAIL_DEFAULT_SENDER=os.getenv('EMAIL_FROM')
)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ========================== 工具与装饰器 ==========================
RATE_LIMIT_STORE = defaultdict(list)

def rate_limit(limit=10, window=60):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = flask.request.remote_addr
            now = time()
            RATE_LIMIT_STORE[ip] = [t for t in RATE_LIMIT_STORE[ip] if now - t < window]
            if len(RATE_LIMIT_STORE[ip]) >= limit:
                return flask.jsonify({"error": "请求过于频繁，请稍后再试"}), 429
            RATE_LIMIT_STORE[ip].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def sanitize_input(text, max_length=1000):
    if not text: return text
    text = str(text)[:max_length]
    text = text.replace('<script', '&lt;script').replace('javascript:', '')
    return text.strip()

def is_strong_password(password):
    if len(password) < 8: return False, "密码长度至少需要 8 位"
    if not re.search(r'[A-Z]', password): return False, "需要至少一个大写字母"
    if not re.search(r'[a-z]', password): return False, "需要至少一个小写字母"
    if not re.search(r'\d', password): return False, "需要至少一个数字"
    return True, "密码强度符合要求"

# ========================== 数据库模型 ==========================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(10), default='student')  # 'student' or 'teacher'
    learning_summary = db.Column(db.String(1000), nullable=True)
    summary_updated_at = db.Column(db.DateTime, nullable=True)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(1000), nullable=False)
    answer = db.Column(db.Text, nullable=True)
    authoritative_answer = db.Column(db.Text, nullable=True)  # 老师的权威答案
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(1000), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='unread')
    reply_content = db.Column(db.String(2000), nullable=True)
    reply_timestamp = db.Column(db.DateTime, nullable=True)
    replier_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

# ========================== AI 引擎封装 (统一多模态架构) ==========================
from modules.ai import AIEngine

# 全局初始化 AI 引擎
ai = AIEngine()

# ========================== 业务辅助函数 ==========================
def get_user_history(user_id):
    records = Question.query.filter_by(student_id=user_id).order_by(Question.timestamp.desc()).limit(3).all()
    records.reverse()
    return "\n".join([f"问：{r.content}\n答：{r.answer}" for r in records])

def get_authoritative_context(query):
    questions = Question.query.filter(Question.authoritative_answer.isnot(None)).all()
    if not questions: return ""
    
    query_vec = ai.embeddings.embed_query(query)
    best_match, best_sim = None, 0.75
    
    for q in questions:
        q_vec = ai.embeddings.embed_query(q.content)
        sim = util.cos_sim(query_vec, q_vec).item()
        if sim > best_sim:
            best_sim, best_match = sim, q
            
    if best_match:
        teacher = db.session.get(User, best_match.teacher_id)
        t_name = teacher.username if teacher else "老师"
        return f"\n【历史权威参考】来自{t_name}的解答：\n{best_match.authoritative_answer}\n"
    return ""

# ========================== 用户认证路由 ==========================
# (由于空间限制，认证路由 register, login, logout, check_auth 逻辑与你原有代码保持绝对一致)
@app.route("/api/register", methods=["POST"])
@rate_limit(limit=5, window=300)
def register():
    data = flask.request.json
    username, email, password = data.get('username'), data.get('email'), data.get('password')
    role = data.get('role', 'student')
    
    if not all([username, email, password]): return flask.jsonify({"error": "缺少必填字段"}), 400
    is_strong, msg = is_strong_password(password)
    if not is_strong: return flask.jsonify({"error": msg}), 400
    if User.query.filter((User.username == username) | (User.email == email)).first():
        return flask.jsonify({"error": "用户名或邮箱已存在"}), 409
        
    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(username=username, email=email, password=hashed_pw, role=role)
    db.session.add(new_user)
    db.session.commit()
    login_user(new_user, remember=True)
    return flask.jsonify({"message": "注册成功", "user": {"id": new_user.id, "username": username, "role": role}}), 201

@app.route("/api/login", methods=["POST"])
@rate_limit(limit=10, window=300)
def login():
    data = flask.request.json
    login_id, password = data.get('username') or data.get('email'), data.get('password')
    user = User.query.filter((User.username == login_id) | (User.email == login_id)).first()
    if user and bcrypt.check_password_hash(user.password, password):
        login_user(user, remember=data.get('remember', True))
        return flask.jsonify({"message": "登录成功", "user": {"id": user.id, "username": user.username, "role": user.role}}), 200
    return flask.jsonify({"error": "账号或密码错误"}), 401

@app.route("/api/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return flask.jsonify({"message": "登出成功"}), 200

@app.route("/api/check-auth", methods=["GET"])
def check_auth():
    if current_user.is_authenticated:
        return flask.jsonify({"authenticated": True, "user": {"id": current_user.id, "username": current_user.username, "email": current_user.email, "role": current_user.role}}), 200
    return flask.jsonify({"authenticated": False}), 401

@app.route("/api/student/questions/history", methods=["GET"])
@login_required
def get_student_question_history():
    if current_user.role != 'student': return flask.jsonify({"error": "权限不足"}), 403
    questions = Question.query.filter_by(student_id=current_user.id).order_by(Question.timestamp.desc()).limit(50).all()
    return flask.jsonify([{"id": q.id, "question": q.content, "answer": q.answer, "authoritative_answer": q.authoritative_answer, "timestamp": q.timestamp.isoformat()} for q in questions]), 200

# ========================== 核心 AI 问答路由 (多模态升级版) ==========================
@app.route("/api/qa", methods=["POST"])
@app.route("/api/multimodal/qa", methods=["POST"])
@login_required
@rate_limit(limit=10)
def handle_qa():
    data = flask.request.json
    query = sanitize_input(data.get('question', ''))
    image_base64 = data.get('image')
    
    if not query and not image_base64:
        return flask.jsonify({"error": "请求内容为空"}), 400

    def generate():
        context = ""
        history_text = get_user_history(current_user.id)
        
        # 1. 文本 RAG 检索体系 (针对存在文字问题的场景)
        if query:
            if not image_base64:
                context += ai.safe_math(query)
            context += get_authoritative_context(query)
            
            if ai.retriever:
                docs = ai.retriever.invoke(query)
                unique_docs = list({d.page_content for d in docs})
                if unique_docs:
                    context += "\n【本地参考资料】:\n" + "\n---\n".join(unique_docs)

        # 2. 组装 Qwen-VL 原生消息体结构
        system_content = "你是专业的学习助手。请根据提供的资料、上下文或图片准确回答用户问题。如果用户上传了图片，请精确识别其中的文字、公式或逻辑结构并进行解答。"
        if context:
            system_content += f"\n\n背景上下文:\n{context}"
        if history_text:
            system_content += f"\n\n历史对话记录:\n{history_text}"

        messages = [
            {"role": "system", "content": system_content}
        ]

        # 构建 User 消息，支持纯文本或图文混排
        user_content = []
        if image_base64:
            # 补齐 base64 头部以满足 qwen_vl_utils 要求
            img_url = f"data:image/jpeg;base64,{image_base64}" if not image_base64.startswith("data:image") else image_base64
            user_content.append({"type": "image", "image": img_url})
            
        final_query = query if query else "请详细提取和描述这张图片中的所有关键信息、数字与文字。"
        user_content.append({"type": "text", "text": final_query})
        
        messages.append({"role": "user", "content": user_content})

        # 3. 数据预处理
        streamer, generation_kwargs = ai.stream_generate_from_messages(
            messages,
            max_new_tokens=1024,
            temperature=0.7,
            top_p=0.9,
     )
            
            
            # 使用子线程推理防止阻塞 Flask 事件循环
        thread = threading.Thread(target=ai.llm.generate, kwargs=generation_kwargs)
        thread.start()

        full_answer = ""
        for token in streamer:
                full_answer += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        
        # 5. 异步落库
        with app.app_context():
            db_content = f"[图像] {query[:50]}" if image_base64 else query
            db.session.add(Question(
                content=db_content, 
                answer=full_answer.strip(), 
                student_id=current_user.id
            ))
            db.session.commit()

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route("/api/upload/image", methods=["POST"])
@login_required
@rate_limit(limit=5)
def upload_only_image():
    """纯上传解析接口（直接调用独立解析方法）"""
    if 'image' not in flask.request.files:
        return flask.jsonify({"error": "无文件"}), 400
        
    file = flask.request.files['image']
    img_data = file.read()
    img_b64 = base64.b64encode(img_data).decode()
    
    # 将解码后图片交由 Qwen-VL 单独处理
    analysis = ai.analyze_image_standalone(img_b64)
    return flask.jsonify({"success": True, "analysis": analysis}), 200

# ========================== 留言与通知系统 ==========================
# (此部分与原代码完全保持一致)
@app.route("/api/messages", methods=["GET", "POST"])
@login_required
@rate_limit(limit=20)
def messages():
    if flask.request.method == "POST":
        content = sanitize_input(flask.request.json.get('content'))
        if not content: return flask.jsonify({"error": "内容不能为空"}), 400
        
        msg = Message(content=content, sender_id=current_user.id)
        db.session.add(msg)
        db.session.commit()
        
        send_email = True
        recent_msgs = Message.query.filter(Message.timestamp >= datetime.utcnow() - timedelta(hours=24), Message.id != msg.id).all()
        if recent_msgs:
            new_vec = ai.embeddings.embed_query(content)
            for m in recent_msgs:
                m_vec = ai.embeddings.embed_query(m.content)
                if util.cos_sim(new_vec, m_vec).item() > 0.85:
                    send_email = False
                    break
                    
        if send_email and app.config['MAIL_SERVER'] != 'smtp.example.com':
            try:
                teachers = User.query.filter_by(role='teacher').all()
                for t in teachers:
                    email_msg = MailMessage('【学习平台】学生提交了新留言', recipients=[t.email], body=f"老师您好，\n学生 {current_user.username} 提交新留言：\n\"{content}\"")
                    mail.send(email_msg)
            except Exception as e:
                print(f"邮件发送失败: {e}")
                
        return flask.jsonify({"message": "留言成功", "email_notified": send_email}), 201

    if current_user.role == 'student':
        msgs = Message.query.filter_by(sender_id=current_user.id).order_by(Message.timestamp.desc()).all()
    else:
        msgs = Message.query.order_by(Message.timestamp.desc()).all()
        
    return flask.jsonify([{"id": m.id, "content": m.content, "status": m.status, "reply_content": m.reply_content, "timestamp": m.timestamp.isoformat(), "sender": db.session.get(User, m.sender_id).username if db.session.get(User, m.sender_id) else "未知", "reply_timestamp": m.reply_timestamp.isoformat() if m.reply_timestamp else None} for m in msgs]), 200

# ========================== 教师管理端路由 ==========================
@app.route("/api/questions/stats", methods=["GET"])
@login_required
def get_question_stats():
    """获取问题统计数据并生成 AI 学习情况分析"""
    if current_user.role != 'teacher':
        return flask.jsonify({"error": "Permission denied"}), 403
    
    # 1. 获取所有问题并按学生分组
    questions = Question.query.all()
    total_questions = len(questions)
    
    questions_by_student = {}
    for q in questions:
        student = db.session.get(User, q.student_id)
        if student:
            if student.username not in questions_by_student:
                questions_by_student[student.username] = []
            questions_by_student[student.username].append({
                "question": q.content,
                "answer": q.answer
            })
    
    student_summaries = {}

    # 2. 遍历学生生成分析
    for student_name, qa_list in questions_by_student.items():
        student_user = User.query.filter_by(username=student_name).first()
        
        # 检查缓存逻辑
        need_update = False
        if student_user:
            if not student_user.summary_updated_at:
                need_update = True
            elif (datetime.utcnow() - student_user.summary_updated_at).total_seconds() > 86400:
                need_update = True
        
        if student_user and student_user.learning_summary and not need_update:
            student_summaries[student_name] = student_user.learning_summary
            continue

        # 3. 准备 AI Prompt 消息格式
        qa_text = "\n".join([
            f"问: {qa['question']}\n答: {qa['answer'][:50] if qa['answer'] else '未回答'}"
            for qa in qa_list[:5]
        ])

        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": "你是一位教育专家，请根据提供的学生提问记录简要分析其学习兴趣、薄弱点并给出建议。字数控制在100字以内。"}]
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": f"学生 {student_name} 的记录：\n{qa_text}"}]
            }
        ]

        # 4. 调用 AIEngine 进行生成
        try:
            # 使用 AIEngine 的私有方法构建输入（或直接在 AIEngine 增加一个非流式 generate 方法）
            inputs = ai._build_inputs_from_messages(messages)
            
            with torch.inference_mode():
                generated_ids = ai.llm.generate(
                    **inputs,
                    max_new_tokens=150,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=ai.processor.tokenizer.eos_token_id
                )

            # 剪切掉 Prompt 部分，只保留生成的回答
            generated_ids_trimmed = [
                out_ids[len(in_ids):]
                for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            
            output_text = ai.processor.batch_decode(
                generated_ids_trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False
            )

            summary = output_text[0].strip() if output_text else f"该生近期提问 {len(qa_list)} 次。"
            
            # 更新数据库
            if student_user:
                student_user.learning_summary = summary
                student_user.summary_updated_at = datetime.utcnow()
                db.session.commit()
                
            student_summaries[student_name] = summary

        except Exception as e:
            student_summaries[student_name] = f"统计：共提问 {len(qa_list)} 次（分析生成失败）"

    # 5. 返回结果
    overall_summary = f"全班共有 {total_questions} 个问题，来自 {len(questions_by_student)} 位学生。"
    
    return flask.jsonify({
        "total_questions": total_questions,
        "questions_by_student": questions_by_student,
        "student_summaries": student_summaries,
        "summary": overall_summary
    }), 200

@app.route("/api/messages/<int:msg_id>/reply", methods=["POST"])
@login_required
def reply_message(msg_id):
    if current_user.role != 'teacher': return flask.jsonify({"error": "权限不足"}), 403
    reply_content = sanitize_input(flask.request.json.get('reply_content'))
    msg = db.session.get(Message, msg_id)
    if not msg: return flask.jsonify({"error": "留言不存在"}), 404
    msg.reply_content = reply_content
    msg.reply_timestamp = datetime.utcnow()
    msg.replier_id = current_user.id
    msg.status = 'replied'
    db.session.commit()
    return flask.jsonify({"message": "回复成功"}), 200

@app.route("/api/questions/pending", methods=["GET"])
@login_required
def get_pending_questions():
    if current_user.role != 'teacher': return flask.jsonify({"error": "权限不足"}), 403
    questions = Question.query.order_by(Question.timestamp.desc()).all()
    return flask.jsonify([{"id": q.id, "content": q.content, "ai_answer": q.answer, "authoritative_answer": q.authoritative_answer, "student_id": q.student_id, "student_name": db.session.get(User, q.student_id).username if db.session.get(User, q.student_id) else "未知", "timestamp": q.timestamp.isoformat()} for q in questions]), 200

@app.route("/api/questions/<int:q_id>/authoritative", methods=["POST"])
@login_required
def submit_authoritative_answer(q_id):
    if current_user.role != 'teacher': return flask.jsonify({"error": "权限不足"}), 403
    answer = sanitize_input(flask.request.json.get('answer'))
    question = db.session.get(Question, q_id)
    if not question: return flask.jsonify({"error": "问题不存在"}), 404
    question.authoritative_answer = answer
    question.teacher_id = current_user.id
    db.session.commit()
    return flask.jsonify({"message": "权威答案已收录，将在后续 RAG 中生效"}), 200

@app.route("/api/questions/<int:q_id>", methods=["DELETE"])
@login_required
def delete_question(q_id):
    if current_user.role != 'teacher': return flask.jsonify({"error": "权限不足"}), 403
    q = db.session.get(Question, q_id)
    if q:
        db.session.delete(q)
        db.session.commit()
    return flask.jsonify({"message": "删除成功"}), 200

# ========================== 安全响应头中间件 ==========================
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self';"
    )
    if app.config.get('SESSION_COOKIE_SECURE', False):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# ========================== 应用启动 ==========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    
    print("\n✅ 系统启动成功！")
    print("⚠️ 警告: Web 框架与 ML 模型耦合运行仅适合开发与演示。")
    print("⚠️ 生产环境建议：将 AIEngine 剥离为 FastAPI 独立服务，或使用 vLLM 部署模型 API。\n")
    
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)