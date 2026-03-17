# 学习助手系统 API 开发文档 (v2.0)

本系统是一个集成了 **Qwen 2.5**、**RAG 知识库检索**以及**老师权威回答机制**的智能教育平台。所有接口均基于 `flask-login` 进行 Session 认证，调用需携带有效的 Cookie。

---

## 1. 用户认证接口

### 1.1 用户注册

* **路径**：`/api/register`
* **方法**：`POST`
* **参数**：
| 参数名 | 类型 | 必填 | 描述 |
| :--- | :--- | :--- | :--- |
| `username` | `string` | 是 | 用户名 (唯一) |
| `email` | `string` | 是 | 邮箱 (唯一) |
| `password` | `string` | 是 | 密码 |
| `role` | `string` | 是 | 角色: `student` 或 `teacher` |

### 1.2 用户登录

* **路径**：`/api/login`
* **方法**：`POST`
* **说明**：登录成功后，服务器会设置包含 Session ID 的 Cookie。
* **请求示例**：
```json
{ "email": "teacher@edu.com", "password": "secure_password" }

```

* **返回结果**：
```json
{ "message": "Login successful", "role": "teacher" }

```

### 1.3 检查登录状态

* **路径**：`/api/check-auth`
* **方法**：`GET`
* **描述**：检查当前用户的登录状态和角色信息
* **返回示例**：

**已登录**：
```json
{
  "authenticated": true,
  "user": {
    "id": 1,
    "username": "student1",
    "email": "student1@example.com",
    "role": "student"
  }
}
```

**未登录**：
```json
{
  "authenticated": false
}
```
* **状态码**：已登录返回200，未登录返回401

### 1.4 用户登出

* **路径**：`/api/logout`
* **方法**：`POST`
* **描述**：用户登出，清除session
* **返回示例**：

```json
{ "message": "Logout successful" }
```



---

## 2. 核心 AI 问答接口

### 2.1 智能问答 (流式响应)

* **路径**：`/api/qa`
* **方法**：`POST`
* **特性**：**SSE (Server-Sent Events)**。AI 会自动检索：
1. **老师权威答案** (最高优先级)
2. **本地 .md 知识库**
3. **计算/网页抓取工具**
4. **历史对话记录**


* **参数**：
```json
{ "question": "如何计算 $E=mc^2$ 中的能量？" }

```


* **响应格式**：`text/event-stream`
```text
data: {"token": "根"}
data: {"token": "据"}
data: {"token": "老师的权威解答..."}

```



---

## 3. 老师权威回答管理

### 3.1 获取待处理/所有问题列表

* **路径**：`/api/questions/pending`
* **方法**：`GET`
* **权限**：仅限 `teacher`
* **描述**：老师查看系统内产生的所有学生提问，以便决定是否覆盖 AI 的回答。
* **响应示例**：
```json
[
  {
    "id": 1,
    "content": "深度学习是什么？",
    "ai_answer": "AI 自动生成的初步回答...",
    "authoritative_answer": null, // 若为 null 则表示老师尚未介入
    "student_name": "张三",
    "timestamp": "2026-03-15T..."
  }
]

```



### 3.2 提交权威答案

* **路径**：`/api/questions/<int:q_id>/authoritative`
* **方法**：`POST`
* **权限**：仅限 `teacher`
* **描述**：老师针对特定问题提供专业答案。一旦提交，AI 在后续遇到类似问题时将**强制参考**此内容。
* **参数**：
```json
{ "answer": "这是来自资深专家的标准定义：..." }

```



---

## 4. 留言与通知系统

### 4.1 获取/发送留言

* **路径**：`/api/messages`
* **方法**：`GET` | `POST`
* **说明**：
* **GET**: 学生看到自己的留言；老师看到所有留言。
* **POST**: 学生发送留言，系统触发邮件提醒（若配置了 SMTP）。


* **参数 (POST)**：
```json
{ "content": "老师，我还是没明白导数的物理意义。" }

```

### 4.2 回复学生留言

* **路径**：`/api/messages/<int:msg_id>/reply`
* **方法**：`POST`
* **权限**：仅限 `teacher`
* **参数**：
```json
{ "reply_content": "下周二课间你可以来办公室，我们详细讨论。" }

```

---

## 5. 前端集成建议

[!TIP]
**关于权威答案的逻辑：**
系统内部使用 **Cosine Similarity** (余弦相似度) 进行语义匹配。当学生提问时，系统会计算该问题与数据库中已有“权威答案”问题的相似度向量。

$$\text{similarity} = \cos(\theta) = \frac{\mathbf{A} \cdot \mathbf{B}}{\|\mathbf{A}\| \|\mathbf{B}\|}$$

如果相似度 $\text{similarity} > 0.8$，AI 将会把老师的回答作为“绝对真理”注入到 Prompt 中。


## 3. 技术说明

### 3.1 认证机制
- 使用Flask-Login实现基于cookie的用户认证
- 登录后，用户信息会存储在session中
- 受保护的接口需要使用`@login_required`装饰器

### 3.2 数据库设计
- 使用SQLAlchemy ORM
- 数据库表结构：
  - `user`：用户表，存储用户信息
  - `question`：问题表，存储学生的问题和AI的回答
  - `message`：留言表，存储学生给老师的留言

### 3.3 AI模型
- 使用HuggingFace的预训练模型
- 实现RAG（Retrieval-Augmented Generation）架构
- 从文档中检索相关信息，增强AI回答的准确性

### 3.4 邮箱提醒
- 使用Flask-Mail发送邮件
- 当学生给老师留言时，系统会自动给所有老师发送邮件提醒

## 4. 配置说明

所有配置项都存储在`.env`文件中，包括：
- 数据库连接信息
- 邮箱配置
- 应用配置
- AI模型配置

示例配置：
```
# 数据库配置
DATABASE_URL=sqlite:///./learning_assistant.db

# 邮箱配置
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USERNAME=your_email@example.com
EMAIL_PASSWORD=your_email_password
EMAIL_FROM=your_email@example.com

# 应用配置
SECRET_KEY=your_secret_key
DEBUG=True

# AI模型配置
MODEL_NAME=google/flan-t5-base
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```