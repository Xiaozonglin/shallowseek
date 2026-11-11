import os
import json
import re
import time as _time
import base64
import logging
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from time import time

import flask
from flask import Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message as MailMessage

from modules import answer_modes

# ========================== 基础与安全配置 ==========================
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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
    # 智能 UI / Agent：卡片与工具轨迹（演示版新增列，旧库启动时自动补齐）
    ui_json = db.Column(db.Text, nullable=True)
    trace_json = db.Column(db.Text, nullable=True)
    mode = db.Column(db.String(10), default='fast')
    title = db.Column(db.String(120), nullable=True)  # 侧边栏历史标题（LLM 生成，可由学生修改）
    # 隐私边界：问答默认仅学生本人可见，只有学生主动提交后教师端才能查看/回答
    shared = db.Column(db.Boolean, nullable=False, default=False)
    shared_at = db.Column(db.DateTime, nullable=True)
    # 回答效果：模板（学习新知/复习旧知/探索未知）× 交流方式（逐轮短对话/长对话）
    template = db.Column(db.String(20), default=answer_modes.DEFAULT_TEMPLATE)
    style = db.Column(db.String(20), default=answer_modes.DEFAULT_STYLE)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(1000), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='unread')
    reply_content = db.Column(db.String(2000), nullable=True)
    reply_timestamp = db.Column(db.DateTime, nullable=True)
    replier_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

# ========================== AI 引擎（DeepSeek API，无本地模型） ==========================
from modules.ai import AIEngine
from modules.agent import AgentRuntime

# 全局初始化 AI 引擎：未配置 DEEPSEEK_API_KEY 时会直接抛错，便于尽早暴露配置问题
ai = AIEngine()
agent_runtime = AgentRuntime(ai)

# ========================== 业务辅助函数 ==========================
def get_user_history(user_id):
    records = Question.query.filter_by(student_id=user_id).order_by(Question.timestamp.desc()).limit(3).all()
    records.reverse()
    return "\n".join([f"问：{r.content}\n答：{r.answer}" for r in records])

AUTHORITATIVE_SIM_THRESHOLD = float(os.getenv("AUTHORITATIVE_SIM_THRESHOLD", "0.45"))

# 侧边栏历史标题：由 LLM 概括，学生可自定义修改
TITLE_MAX_CHARS = 24


def _fallback_question_title(question, answer=""):
    """LLM 不可用时的兜底标题：去掉图像/文件标记后截断原文。"""
    for text in (question, answer):
        cleaned = re.sub(r"^\[\s*(图像|文件)\s*\]\s*", "", (text or "").strip())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            return cleaned[:TITLE_MAX_CHARS]
    return "学习提问"


def _generate_question_title(question, answer=""):
    """调用 LLM 生成一句历史标题；失败时退化为截断文本。"""
    try:
        title = ai.generate_title(question or "", answer or "", max_chars=TITLE_MAX_CHARS)
    except Exception:
        logger.exception("生成历史标题失败")
        title = ""
    return (title or _fallback_question_title(question, answer))[:TITLE_MAX_CHARS]


def get_authoritative_context(query):
    """在教师权威答案中找与当前提问最接近的一条（词法相似度）。"""
    questions = Question.query.filter(Question.authoritative_answer.isnot(None)).all()
    if not questions:
        return ""

    best_match, best_sim = None, AUTHORITATIVE_SIM_THRESHOLD
    for question in questions:
        sim = ai.text_similarity(query, question.content)
        if sim > best_sim:
            best_sim, best_match = sim, question

    if best_match:
        teacher = db.session.get(User, best_match.teacher_id)
        teacher_name = teacher.username if teacher else "老师"
        return f"\n【历史权威参考】来自{teacher_name}的解答：\n{best_match.authoritative_answer}\n"
    return ""


def truncate_for_prompt(text, max_chars=220):
    if not text:
        return "暂无"
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text[:max_chars] + ("..." if len(text) > max_chars else "")

def generate_ai_text(system_prompt, user_prompt, max_new_tokens=360):
    """非流式生成（学情分析等场景），由 DeepSeek API 完成。"""
    return ai.generate_text(system_prompt, user_prompt, max_tokens=max_new_tokens)


def build_qa_digest(qa_list, max_items=8, answer_chars=180):
    lines = []
    for index, qa in enumerate(qa_list[:max_items], start=1):
        question = truncate_for_prompt(qa.get("question"), 180)
        answer = truncate_for_prompt(qa.get("answer"), answer_chars)
        lines.append(f"{index}. 问：{question}\n   AI答：{answer}")
    return "\n".join(lines)

def build_class_digest(questions_by_student, max_students=12, max_items_per_student=5):
    blocks = []
    for student_name, qa_list in list(questions_by_student.items())[:max_students]:
        blocks.append(
            f"学生：{student_name}（提问 {len(qa_list)} 次）\n"
            f"{build_qa_digest(qa_list, max_items=max_items_per_student, answer_chars=120)}"
        )
    return "\n\n".join(blocks)

def fallback_learning_summary(student_name, qa_list):
    samples = "；".join([truncate_for_prompt(qa.get("question"), 36) for qa in qa_list[:4]])
    if not samples:
        samples = "暂无可归纳的问题样本"
    return (
        f"{student_name} 近期主要围绕「{samples}」提问。建议教师结合这些问题定位具体知识点，"
        "优先补充概念边界、解题步骤和典型例题，并观察后续提问是否仍集中在同一类误区。"
    )

def fallback_class_summary(total_questions, questions_by_student):
    samples = []
    for qa_list in questions_by_student.values():
        for qa in qa_list[:2]:
            samples.append(truncate_for_prompt(qa.get("question"), 34))
            if len(samples) >= 6:
                break
        if len(samples) >= 6:
            break

    if not samples:
        return "暂无学生提问数据，暂时无法形成具体学情分析。"

    return (
        f"本次记录包含 {total_questions} 个问题。代表性问题包括：{'；'.join(samples)}。"
        "从这些问题看，学生需要的不只是答案数量统计，而是对概念区分、题意识别、图像/公式理解和解题路径的归纳。"
        "建议后续按知识点整理共性问题，配合错因讲解与同类变式练习。"
    )

# ========================== 用户认证路由 ==========================
# (由于空间限制，认证路由 register, login, logout, check_auth 逻辑与你原有代码保持绝对一致)
@app.route("/api/register", methods=["POST"])
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

    def _load(raw):
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return None

    return flask.jsonify([
        {
            "id": q.id,
            "question": q.content,
            "title": q.title or "",
            "answer": q.answer,
            "authoritative_answer": q.authoritative_answer,
            "timestamp": q.timestamp.isoformat(),
            "mode": q.mode or "fast",
            "ui": _load(q.ui_json),
            "trace": _load(q.trace_json),
            "shared": bool(q.shared),
            "shared_at": q.shared_at.isoformat() if q.shared_at else None,
            "template": q.template or answer_modes.DEFAULT_TEMPLATE,
            "style": q.style or answer_modes.DEFAULT_STYLE,
        }
        for q in questions
    ]), 200


@app.route("/api/questions/<int:q_id>/share", methods=["POST"])
@login_required
@rate_limit(limit=30)
def share_question_to_teacher(q_id):
    """学生主动把某次问答提交给老师（默认私密，提交后才进入教师端）。"""
    if current_user.role != 'student':
        return flask.jsonify({"error": "权限不足"}), 403
    question = db.session.get(Question, q_id)
    if not question:
        return flask.jsonify({"error": "问题不存在"}), 404
    if question.student_id != current_user.id:
        return flask.jsonify({"error": "权限不足"}), 403

    if not question.shared:
        question.shared = True
        question.shared_at = datetime.utcnow()
        student = db.session.get(User, current_user.id)
        if student:
            # 学情分析只基于学生提交的内容，提交后需要重新生成
            student.learning_summary = None
            student.summary_updated_at = None
        db.session.commit()

    return flask.jsonify({
        "shared": True,
        "shared_at": question.shared_at.isoformat() if question.shared_at else None,
        "message": "已提交给老师，老师可在教师端查看并回复",
    }), 200


@app.route("/api/questions/<int:q_id>/share", methods=["DELETE"])
@login_required
@rate_limit(limit=30)
def withdraw_question_from_teacher(q_id):
    """学生撤回提交；老师已回复的问答保留在课程记录中，不允许撤回。"""
    if current_user.role != 'student':
        return flask.jsonify({"error": "权限不足"}), 403
    question = db.session.get(Question, q_id)
    if not question:
        return flask.jsonify({"error": "问题不存在"}), 404
    if question.student_id != current_user.id:
        return flask.jsonify({"error": "权限不足"}), 403
    if question.authoritative_answer:
        return flask.jsonify({"error": "老师已回复，该问答已保留在课程记录中，无法撤回"}), 409

    if question.shared:
        question.shared = False
        question.shared_at = None
        student = db.session.get(User, current_user.id)
        if student:
            student.learning_summary = None
            student.summary_updated_at = None
        db.session.commit()

    return flask.jsonify({"shared": False, "message": "已撤回，老师将不再看到这条问答"}), 200


@app.route("/api/agent/meta", methods=["GET"])
@login_required
def get_agent_meta():
    """前端启动时读取：卡片协议版本、可选模式、相关章节目录。"""
    from modules.agent import available_chapter_payload
    return flask.jsonify({
        "uiVersion": 1,
        "modes": ["fast", "deep"],
        "chapters": available_chapter_payload(),
        "answerModes": answer_modes.metadata(),
    }), 200


# ========================== 核心 AI 问答路由（快答 / 深度 Agent + 智能 UI） ==========================
QA_MODES = {"fast", "deep"}
# 前端上传的文本文件内容单独通过 file 字段传入，与提问一起作为上下文（不计入提问长度）
MAX_FILE_CONTEXT_CHARS = 12000


def _sse(payload):
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _parse_file_payload(data):
    """解析前端可选的上传文件：{"name": str, "content": str} -> (file_name, file_context)。"""
    payload = data.get("file")
    if not isinstance(payload, dict):
        return "", ""

    file_name = sanitize_input(payload.get("name") or "", max_length=80) or "未命名文件"
    file_context = sanitize_input(payload.get("content") or "", max_length=MAX_FILE_CONTEXT_CHARS)
    return file_name, file_context


def _question_record_content(query, image_base64=None, file_name="", file_context=""):
    """落库的提问摘要：带文件/图片时加简短标记，避免把大段文件正文写进历史列表。"""
    if image_base64:
        return f"[图像] {query[:50]}" if query else "[图像]"
    if file_context:
        label = f"[文件] {file_name}"
        return f"{label} {query[:50]}" if query else label
    return query


def _save_question(student_id, content_text, answer_text, ui_payload=None, trace_payload=None, mode="fast", template=None, style=None):
    with app.app_context():
        record = Question(
            content=content_text,
            answer=(answer_text or "").strip(),
            student_id=student_id,
            ui_json=json.dumps(ui_payload, ensure_ascii=False) if ui_payload else None,
            trace_json=json.dumps(trace_payload, ensure_ascii=False) if trace_payload else None,
            mode=mode,
            template=answer_modes.normalize_template(template),
            style=answer_modes.normalize_style(style),
        )
        db.session.add(record)
        db.session.commit()
        return record.id


def _build_fast_prompt(student_id, query, image_base64, file_name="", file_context="", template=None, style=None):
    """快答模式上下文：教师权威答案 + BM25 检索 + 最近历史 + 上传文件 + 回答效果（无工具循环）。"""
    context = ""
    history_text = get_user_history(student_id)
    authority_matched = False
    if query:
        if not image_base64:
            context += ai.safe_math(query)
        authority_context = get_authoritative_context(query)
        authority_matched = bool(authority_context.strip())
        context += authority_context
        context += ai.retrieve_context(query)

    system_content = (
        "你是专业的学习助手。请根据提供的资料、上下文或图片准确回答用户问题。"
        "如果用户上传了图片，请精确识别其中的文字、公式或逻辑结构并进行解答。"
        "如果用户上传了文件，请先阅读文件内容，再结合用户问题作答。"
    )
    system_content += "\n\n" + answer_modes.mode_instructions(template, style)
    if context:
        system_content += f"\n\n背景上下文:\n{context}"
    if file_context:
        system_content += f"\n\n用户上传的文件「{file_name}」内容如下，请结合文件内容回答：\n{file_context}"
    if history_text:
        system_content += f"\n\n历史对话记录:\n{history_text}"

    image_data_url = ai.to_data_url(image_base64) if image_base64 else None
    if query:
        final_query = query
    elif file_context:
        final_query = "请阅读并分析用户上传的文件，提炼关键信息并给出要点。"
    else:
        final_query = "请详细提取和描述这张图片中的所有关键信息、数字与文字。"
    return system_content, final_query, image_data_url, authority_matched


def _legacy_fast_stream(student_id, query, image_base64, file_name="", file_context="", template=None, style=None):
    """旧客户端（不传 uiVersion）：保持 data:{"token"} 契约，纯文本流式。"""
    full_answer = ""
    try:
        system_content, final_query, image_data_url, _authority_matched = _build_fast_prompt(
            student_id, query, image_base64, file_name, file_context, template, style
        )
        for token in ai.stream_answer(system_content, final_query, image_data_url=image_data_url):
            full_answer += token
            yield f"data: {json.dumps({'token': token})}\n\n"

        db_content = _question_record_content(query, image_base64, file_name, file_context)
        _save_question(student_id, db_content, full_answer, mode="fast", template=template, style=style)
        yield f"data: {json.dumps({'done': True})}\n\n"
    except Exception as exc:
        logger.exception("AI 回答失败")
        yield f"data: {json.dumps({'error': ai.friendly_error(exc)}, ensure_ascii=False)}\n\n"


def _typed_fast_stream(student_id, query, image_base64, file_name="", file_context="", template=None, style=None):
    """新客户端 + 快答：统一事件协议，无工具、无卡片。"""
    answer = ""
    template_id = answer_modes.normalize_template(template)
    style_id = answer_modes.normalize_style(style)
    started = _time.monotonic()
    try:
        yield _sse({"type": "start", "mode": "fast", "uiVersion": 1})
        yield _sse({"type": "status", "stage": "answer", "message": "正在生成回答…"})
        system_content, final_query, image_data_url, authority_matched = _build_fast_prompt(
            student_id, query, image_base64, file_name, file_context, template_id, style_id
        )
        for token in ai.stream_answer(system_content, final_query, image_data_url=image_data_url):
            answer += token
            yield _sse({"type": "answer_delta", "text": token})

        duration_ms = int((_time.monotonic() - started) * 1000)
        trace_payload = {
            "trace": [],
            "sources": [],
            "durationMs": duration_ms,
            "mode": "fast",
            "authorityMatched": authority_matched,
            "template": template_id,
            "style": style_id,
        }
        yield _sse({
            "type": "complete",
            "answer": answer,
            "sources": [],
            "trace": [],
            "durationMs": duration_ms,
            "mode": "fast",
            "authorityMatched": authority_matched,
            "template": template_id,
            "style": style_id,
        })
        db_content = _question_record_content(query, image_base64, file_name, file_context)
        record_id = _save_question(
            student_id, db_content, answer, trace_payload=trace_payload, mode="fast", template=template_id, style=style_id
        )
        yield _sse({
            "type": "done",
            "saved": True,
            "messageId": record_id,
            "mode": "fast",
            "authorityMatched": authority_matched,
            "template": template_id,
            "style": style_id,
        })
    except Exception as exc:
        logger.exception("AI 回答失败")
        yield _sse({"type": "error", "code": "ai_error", "message": ai.friendly_error(exc)})


def _typed_deep_stream(student_id, query, file_name="", file_context="", template=None, style=None):
    """新客户端 + 深度：进程内 Agent 工具循环，流式事件 + 卡片。上传文件内容并入 Agent 提问。"""
    answer = ""
    template_id = answer_modes.normalize_template(template)
    style_id = answer_modes.normalize_style(style)
    saved_ui = None
    completed = None
    failed = False
    try:
        yield _sse({"type": "start", "mode": "deep", "uiVersion": 1})
        history_text = get_user_history(student_id)

        # 教师权威答案在快答/深度两条路径都必须生效：深度模式先做词法匹配，再注入 Agent 提示词
        authority_context = get_authoritative_context(query) if query else ""
        authority_matched = bool(authority_context.strip())
        if authority_matched:
            yield _sse({
                "type": "status",
                "stage": "authority",
                "message": "已匹配到教师权威答案，将优先采用",
            })

        agent_question = query
        if file_context:
            file_block = f"【上传文件「{file_name}」内容】\n{file_context}"
            agent_question = (
                f"{query}\n\n{file_block}"
                if query
                else f"请阅读并分析以下文件内容，提炼关键信息并给出要点：\n\n{file_block}"
            )
        run_kwargs = {
            "history_text": history_text,
            "ui_enabled": True,
            "template": template_id,
            "style": style_id,
        }
        if authority_matched:
            run_kwargs["authoritative_context"] = authority_context
        for event in agent_runtime.run(agent_question, **run_kwargs):
            event_type = event.get("type")
            if event_type == "answer_delta":
                answer += event.get("text", "")
            elif event_type == "answer_reset":
                answer = ""
            elif event_type == "ui":
                saved_ui = event.get("ui")
            elif event_type == "complete":
                event = {
                    **event,
                    "authorityMatched": authority_matched,
                    "template": template_id,
                    "style": style_id,
                }
                completed = event
                answer = event.get("answer") or answer
            elif event_type == "error":
                failed = True
            yield _sse(event)

        if failed or completed is None:
            return

        trace_payload = {
            "trace": completed.get("trace", []),
            "sources": completed.get("sources", []),
            "durationMs": completed.get("durationMs", 0),
            "mode": "deep",
            "authorityMatched": authority_matched,
            "template": template_id,
            "style": style_id,
        }
        record_id = _save_question(
            student_id,
            _question_record_content(query, None, file_name, file_context),
            answer,
            ui_payload=saved_ui,
            trace_payload=trace_payload,
            mode="deep",
            template=template_id,
            style=style_id,
        )
        yield _sse({
            "type": "done",
            "saved": True,
            "messageId": record_id,
            "ui": saved_ui,
            "mode": "deep",
            "authorityMatched": authority_matched,
            "template": template_id,
            "style": style_id,
        })
    except Exception as exc:
        logger.exception("Agent 回答失败")
        yield _sse({"type": "error", "code": "ai_error", "message": ai.friendly_error(exc)})


@app.route("/api/qa", methods=["POST"])
@app.route("/api/multimodal/qa", methods=["POST"])
@login_required
@rate_limit(limit=10)
def handle_qa():
    data = flask.request.get_json(silent=True) or {}
    query = sanitize_input(data.get("question", ""))
    image_base64 = data.get("image")
    file_name, file_context = _parse_file_payload(data)

    template = data.get("template")
    style = data.get("style")
    if template is not None and not answer_modes.is_valid_template(template):
        return flask.jsonify({"error": "不支持的模板"}), 400
    if style is not None and not answer_modes.is_valid_style(style):
        return flask.jsonify({"error": "不支持的交流方式"}), 400
    template = answer_modes.normalize_template(template)
    style = answer_modes.normalize_style(style)

    if not query and not image_base64 and not file_context:
        return flask.jsonify({"error": "请求内容为空"}), 400

    mode = str(data.get("mode") or "fast").strip().lower()
    if mode not in QA_MODES:
        return flask.jsonify({"error": "不支持的问答模式"}), 400

    try:
        ui_version = int(data.get("uiVersion") or 0)
    except (TypeError, ValueError):
        ui_version = 0

    student_id = current_user.id
    typed = ui_version == 1

    if typed and mode == "deep" and not image_base64:
        stream = _typed_deep_stream(student_id, query, file_name, file_context, template, style)
    elif typed:
        stream = _typed_fast_stream(student_id, query, image_base64, file_name, file_context, template, style)
    else:
        stream = _legacy_fast_stream(student_id, query, image_base64, file_name, file_context, template, style)

    response = Response(stream_with_context(stream), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


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
    
    # 将解码后图片交由 DeepSeek 视觉能力单独处理
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
        for m in recent_msgs:
            if ai.text_similarity(content, m.content) > 0.8:
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
    
    # 1. 只统计学生主动提交给老师的问答（默认私密的问答不进入学情分析）
    questions = Question.query.filter(Question.shared.is_(True)).order_by(Question.timestamp.desc()).all()
    total_questions = len(questions)
    
    questions_by_student = {}
    for q in questions:
        student = db.session.get(User, q.student_id)
        if student:
            if student.username not in questions_by_student:
                questions_by_student[student.username] = []
            questions_by_student[student.username].append({
                "question": q.content,
                "answer": q.answer,
                "timestamp": q.timestamp.isoformat()
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

        qa_text = build_qa_digest(qa_list)

        try:
            summary = generate_ai_text(
                "你是一位教师教研助手。请基于学生的真实提问和 AI 回答，分析具体知识点、可能误区和后续辅导建议。不要只统计提问次数；必须点出学生正在困惑的知识点或能力点。输出 3 句以内，150 到 220 个中文字符。",
                f"学生 {student_name} 的问答记录如下：\n{qa_text}",
                max_new_tokens=260
            )
            if not summary:
                summary = fallback_learning_summary(student_name, qa_list)
            
            # 更新数据库
            if student_user:
                student_user.learning_summary = summary
                student_user.summary_updated_at = datetime.utcnow()
                db.session.commit()
                
            student_summaries[student_name] = summary

        except Exception as e:
            student_summaries[student_name] = fallback_learning_summary(student_name, qa_list)

    # 5. 返回结果
    if total_questions == 0:
        overall_summary = "暂无学生提问数据，暂时无法形成具体学情分析。"
    else:
        class_digest = build_class_digest(questions_by_student)
        try:
            overall_summary = generate_ai_text(
                "你是一位面向教师的学情分析助手。请根据全班问答记录，生成具体的班级学情分析，必须归纳知识点、共性困惑、学习能力表现和下一步教学建议。不要只说有几个学生、问了几个问题。用清晰的中文分段输出，可包含「知识点归纳」「共性问题」「教学建议」。",
                f"全班共有 {total_questions} 个问题，来自 {len(questions_by_student)} 位学生。\n\n问答记录摘要：\n{class_digest}",
                max_new_tokens=520
            )
            if not overall_summary:
                overall_summary = fallback_class_summary(total_questions, questions_by_student)
        except Exception as e:
            overall_summary = fallback_class_summary(total_questions, questions_by_student)
    
    return flask.jsonify({
        "total_questions": total_questions,
        "questions_by_student": questions_by_student,
        "student_summaries": student_summaries,
        "summary": overall_summary
    }), 200

@app.route("/api/messages/<int:msg_id>", methods=["DELETE"])
@login_required
def delete_message(msg_id):
    msg = db.session.get(Message, msg_id)
    if not msg:
        return flask.jsonify({"error": "留言不存在"}), 404

    if current_user.role != 'teacher' and msg.sender_id != current_user.id:
        return flask.jsonify({"error": "权限不足"}), 403

    db.session.delete(msg)
    db.session.commit()
    return flask.jsonify({"message": "删除成功"}), 200

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
    questions = Question.query.filter(Question.shared.is_(True)).order_by(Question.timestamp.desc()).all()
    return flask.jsonify([
        {
            "id": q.id,
            "content": q.content,
            "ai_answer": q.answer,
            "authoritative_answer": q.authoritative_answer,
            "student_id": q.student_id,
            "student_name": db.session.get(User, q.student_id).username if db.session.get(User, q.student_id) else "未知",
            "timestamp": q.timestamp.isoformat(),
            "shared_at": q.shared_at.isoformat() if q.shared_at else None,
        }
        for q in questions
    ]), 200

@app.route("/api/questions/<int:q_id>/authoritative", methods=["POST"])
@login_required
def submit_authoritative_answer(q_id):
    if current_user.role != 'teacher': return flask.jsonify({"error": "权限不足"}), 403
    answer = sanitize_input(flask.request.json.get('answer'))
    question = db.session.get(Question, q_id)
    if not question: return flask.jsonify({"error": "问题不存在"}), 404
    if not question.shared:
        return flask.jsonify({"error": "该提问未提交给老师，教师端无权查看或回答"}), 403
    question.authoritative_answer = answer
    question.teacher_id = current_user.id
    db.session.commit()
    return flask.jsonify({"message": "权威答案已收录，将在后续 RAG 中生效"}), 200

@app.route("/api/questions/<int:q_id>", methods=["DELETE"])
@login_required
def delete_question(q_id):
    q = db.session.get(Question, q_id)
    if not q:
        return flask.jsonify({"error": "问题不存在"}), 404

    if current_user.role != 'teacher' and q.student_id != current_user.id:
        return flask.jsonify({"error": "权限不足"}), 403
    if current_user.role == 'teacher' and not q.shared:
        return flask.jsonify({"error": "该提问未提交给老师，教师端无权删除"}), 403

    student = db.session.get(User, q.student_id)
    db.session.delete(q)
    if student:
        student.learning_summary = None
        student.summary_updated_at = None
    db.session.commit()
    return flask.jsonify({"message": "删除成功"}), 200


@app.route("/api/questions/<int:q_id>/title", methods=["POST"])
@login_required
@rate_limit(limit=30)
def generate_question_title(q_id):
    """为历史记录生成 LLM 标题（幂等：已有标题也会按当前内容重新概括）。"""
    q = db.session.get(Question, q_id)
    if not q:
        return flask.jsonify({"error": "问题不存在"}), 404
    if q.student_id != current_user.id:
        return flask.jsonify({"error": "权限不足"}), 403

    title = _generate_question_title(q.content, q.answer or "")
    q.title = title
    db.session.commit()
    return flask.jsonify({"title": title}), 200


@app.route("/api/questions/<int:q_id>/title", methods=["PATCH"])
@login_required
def update_question_title(q_id):
    """学生自定义修改历史标题。"""
    q = db.session.get(Question, q_id)
    if not q:
        return flask.jsonify({"error": "问题不存在"}), 404
    if q.student_id != current_user.id:
        return flask.jsonify({"error": "权限不足"}), 403

    data = flask.request.get_json(silent=True) or {}
    title = re.sub(r"\s+", " ", sanitize_input(data.get("title", ""), max_length=80)).strip()
    if not title:
        return flask.jsonify({"error": "标题不能为空"}), 400

    q.title = title[:TITLE_MAX_CHARS]
    db.session.commit()
    return flask.jsonify({"title": q.title}), 200

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
def ensure_schema():
    """演示版轻量迁移：为已有演示库补齐 question 新列（不引入迁移框架）。"""
    from sqlalchemy import inspect, text as sql_text
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        if "question" not in inspector.get_table_names():
            return
        columns = {column["name"] for column in inspector.get_columns("question")}
        additions = {
            "ui_json": "TEXT",
            "trace_json": "TEXT",
            "mode": "VARCHAR(10)",
            "title": "VARCHAR(120)",
            "shared": "BOOLEAN DEFAULT 0",
            "shared_at": "DATETIME",
            "template": "VARCHAR(20)",
            "style": "VARCHAR(20)",
        }
        first_privacy_migration = "shared" not in columns
        with db.engine.begin() as connection:
            for name, ddl in additions.items():
                if name not in columns:
                    connection.execute(sql_text(f"ALTER TABLE question ADD COLUMN {name} {ddl}"))
            if first_privacy_migration:
                # 旧缓存可能包含学生未同意的问答，隐私边界上线时统一作废
                connection.execute(sql_text("UPDATE user SET learning_summary = NULL, summary_updated_at = NULL"))


if __name__ == "__main__":
    ensure_schema()
    
    print("\n✅ 系统启动成功！")
    print(f"🤖 AI 服务: DeepSeek API（{os.getenv('DEEPSEEK_MODEL', 'deepseek-flash')}），不加载本地模型。")
    print("⚠️ 仅适合演示：API Key 请放在本地 .env 或环境变量中，切勿提交到仓库。\n")

    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)
