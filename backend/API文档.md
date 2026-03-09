# 学习助手系统API文档

## 1. 接口列表

| 接口路径                   | 方法     | 功能描述     | 角色要求    |
|:-----------------------|:-------|:---------|:--------|
| `/api/register`        | `POST` | 注册新用户    | 无       |
| `/api/login`           | `POST` | 用户登录     | 无       |
| `/api/logout`          | `POST` | 用户登出     | 已登录     |
| `/api/qa`              | `POST` | 学生提问     | 已登录（学生） |
| `/api/questions/stats` | `GET`  | 老师查看问题统计 | 已登录（老师） |
| `/api/messages`        | `POST` | 学生给老师留言  | 已登录（学生） |

## 2. 详细接口说明

### 2.1 注册新用户

**接口路径**：`/api/register`
**请求方法**：`POST`
**功能描述**：注册新用户，支持学生和老师两种角色

**请求参数**：

| 参数名        | 类型       | 必填 | 描述                         |
|:-----------|:---------|:---|:---------------------------|
| `username` | `string` | 是  | 用户名                        |         
| `email`    | `string` | 是  | 邮箱地址                       |     
| `password` | `string` | 是  | 密码                         |  
| `role`     | `string` | 是  | 角色，可选值：`student`、`teacher` |

**请求示例**：
```json
{
  "username": "student1",
  "email": "student1@example.com",
  "password": "123456",
  "role": "student"
}
```

**返回结果**：
- 成功：`201 Created`
  ```json
  {
    "message": "User registered successfully"
  }
  ```
- 失败：`400 Bad Request`
  ```json
  {
    "error": "Username already exists" // 或 "Email already exists" 或 "Missing required fields"
  }
  ```

### 2.2 用户登录

**接口路径**：`/api/login`
**请求方法**：`POST`
**功能描述**：用户登录，返回登录状态和角色信息

**请求参数**：
| 参数名 | 类型 | 必填 | 描述 |
| :--- | :--- | :--- | :--- |
| `email` | `string` | 是 | 邮箱地址 |
| `password` | `string` | 是 | 密码 |

**请求示例**：
```json
{
  "email": "student1@example.com",
  "password": "123456"
}
```

**返回结果**：
- 成功：`200 OK`
  ```json
  {
    "message": "Login successful",
    "role": "student" // 或 "teacher"
  }
  ```
- 失败：`401 Unauthorized`
  ```json
  {
    "error": "Invalid email or password"
  }
  ```

### 2.3 用户登出

**接口路径**：`/api/logout`
**请求方法**：`POST`
**功能描述**：用户登出

**请求参数**：无

**返回结果**：
- 成功：`200 OK`
  ```json
  {
    "message": "Logout successful"
  }
  ```

### 2.4 学生提问

**接口路径**：`/api/qa`
**请求方法**：`POST`
**功能描述**：学生向AI提问，系统记录问题并返回答案

**请求参数**：
| 参数名 | 类型 | 必填 | 描述 |
| :--- | :--- | :--- | :--- |
| `question` | `string` | 是 | 问题内容 |

**请求示例**：
```json
{
  "question": "什么是机器学习？"
}
```

**返回结果**：
- 成功：`200 OK`
  ```json
  {
    "answer": "机器学习是人工智能的一个分支，它使计算机能够从数据中学习而不需要明确编程..."
  }
  ```
- 失败：`400 Bad Request`
  ```json
  {
    "error": "Missing question"
  }
  ```
- 失败：`500 Internal Server Error`
  ```json
  {
    "error": "AI model not loaded" // 或其他错误信息
  }
  ```

### 2.5 老师查看问题统计

**接口路径**：`/api/questions/stats`
**请求方法**：`GET`
**功能描述**：老师查看所有学生的问题统计，包括问题数量、按学生分组的问题列表，以及AI生成的问题总结

**请求参数**：无

**返回结果**：
- 成功：`200 OK`
  ```json
  {
    "total_questions": 5,
    "questions_by_student": {
      "student1": [
        {
          "content": "什么是机器学习？",
          "answer": "机器学习是人工智能的一个分支...",
          "timestamp": "2026-03-09T12:00:00Z"
        }
      ],
      "student2": [
        {
          "content": "如何学习Python？",
          "answer": "学习Python的步骤包括...",
          "timestamp": "2026-03-09T13:00:00Z"
        }
      ]
    },
    "summary": "学生主要关注机器学习、Python编程等技术问题..."
  }
  ```
- 失败：`403 Forbidden`
  ```json
  {
    "error": "Access denied"
  }
  ```

### 2.6 学生给老师留言

**接口路径**：`/api/messages`
**请求方法**：`POST`
**功能描述**：学生给老师发送留言，系统会给老师发送邮箱提醒

**请求参数**：
| 参数名 | 类型 | 必填 | 描述 |
| :--- | :--- | :--- | :--- |
| `content` | `string` | 是 | 留言内容 |

**请求示例**：
```json
{
  "content": "老师，我对机器学习的概念还有些疑问，希望能得到更详细的解释。"
}
```

**返回结果**：
- 成功：`201 Created`
  ```json
  {
    "message": "Message sent successfully"
  }
  ```
- 失败：`400 Bad Request`
  ```json
  {
    "error": "Missing message content"
  }
  ```

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