# XDWe: Teacher-Augmented AI Learning System for Xidian University

<p style="text-align:center;">XDWe：一个 AI 驱动的师生交流互动平台，实现教学相长</p>

**Student Developers**
- 肖宗林 (Zonglin Xiao) - [xiaozonglin@stu.xidian.edu.cn](mailto:xiaozonglin@stu.xidian.edu.cn)
- 姚焱夫 (Yanfu Yao) - [YvesYao0209@foxmail.com](mailto:YvesYao0209@foxmail.com)
- 孟子钦 (Ziqin Meng) - [3862834578@qq.com](mailto:3862834578@qq.com)

---

**XDWe** (Xidian + We) is a collaborative, RAG-driven platform designed to transform Xidian University's academic resources into an intelligent, teacher-verified knowledge network. It empowers students with instant, high-fidelity answers while ensuring educators retain full pedagogical control.

传统教育场景中，学生提问存在响应滞后、答案同质化严重、教师负担过重等问题。现有知识库缺乏针对性，无法有效沉淀教学过程中的个性化问题与解答。XDWe 尝试通过整合西安电子科技大学本地化学习资料（如课程讲义、实验文档、历年真题），结合大模型 RAG 技术，构建“学生提问-AI初答-教师审核-知识沉淀”的闭环生态，实现教学资源的智能化管理与个性化学习支持。

## 技术架构

采用前后端分离架构，各组件职责与交互关系如下：

- 前端：Vue.js 3.x + Ant Design Vue，负责页面渲染与用户交互，通过 Axios / fetch 调用后端 RESTful API；
- 后端：Flask 框架提供 API 接口，Flask-Login 管理会话认证，SQLAlchemy 操作 SQLite 数据库；
- AI 服务：调用 **DeepSeek API**（`deepseek-flash`，OpenAI 兼容协议，支持文本与图片理解、SSE 流式输出），**不加载任何本地大模型**，无需 GPU 与模型权重；
- 知识检索：jieba 分词 + BM25 词法检索，索引由 `backend/build_index.py` 在本地生成（演示场景可跳过，跳过时自动关闭检索）；
- **Agent / 智能 UI**：深度模式在进程内跑 DeepSeek function-calling 工具循环（检索、读原文、计算、提交卡片），以 SSE 事件流输出过程与卡片；前端渲染「参考资料 / 解题步骤 / 相关章节」三类卡片。设计决策见 `migration/ADR-001-agent-ui-architecture.md`，演示题库见 `migration/DEMO_QA.md`。

> 与旧版本的差异：已移除本地 Qwen3-VL / BGE / FAISS / PyTorch 方案，图片问答改由 DeepSeek 视觉能力完成，并吸收了 xdu-zhixing 的 Agent / 卡片化回答思路，详情见 `migration/MIGRATION_REVIEW.md` 与 `migration/AGENT_UI_MIGRATION_PLAN.md`。

## 目录结构

```txt
│  .env.example // 后端配置模板（复制为 .env 后填写）
│  requirements.txt // pip 环境配置（不含深度学习框架）
│
├─backend
│  │  API文档.md // 接口文档
│  │  main.py // Flask 主文件
│  │  build_index.py // 构建 BM25 词法索引
│  │  smoke_deepseek.py // 冒烟测试：验证 API Key 与流式输出
│  │  smoke_agent.py // 冒烟测试：验证深度模式 Agent 工具循环与卡片
│  │
│  ├─modules
│  │      ai.py // DeepSeek API 封装（AIEngine）
│  │      agent.py // 进程内 Agent 运行时（工具循环 + 事件流）
│  │      agent_tools.py // 检索/读原文/计算/提交卡片工具与引用注册表
│  │      agent_prompts.py // 深度模式提示词
│  │      ui_cards.py // 卡片协议与校验
│  │      chapter_catalog.json // 相关章节卡使用的固定章节目录
│  │      retrieval.py // 词法检索与短文本相似度
│  │
│  ├─tests // 离线测试（卡片协议 / Agent / 事件流）
│  ├─bm25_index // 由 build_index.py 生成的本地索引（gitignore）
│  └─instance // 数据库（gitignore）
│
├─docs // 知识库语料（Markdown）
├─documents_workflow // 文档转 Markdown 工具脚本（可选）
│
├─frontend
│  │  index.html
│  │  vite.config.js // 前端配置（/api 代理到 127.0.0.1:5000）
│  │
│  └─src
│      │  App.vue
│      │  main.js
│      ├─components
│      │      ToolTrace.vue // 工具执行过程折叠面板
│      │      cards // 智能 UI 卡片组件（参考/步骤/章节/引用）
│      ├─router // 路由
│      ├─stores
│      ├─utils // SSE 事件流解析、卡片校验
│      └─views // Vue 视图
```

## 快速开始

### 0. 准备

- Python 3.10+（**不需要 GPU / CUDA / PyTorch**）
- Node.js 20.19+ 或 22.12+
- 一个 DeepSeek API Key：<https://platform.deepseek.com/api_keys>

### 1. 后端

```bash
cd backend

# 建议使用虚拟环境
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r ../requirements.txt

# 配置：复制模板并填入 DEEPSEEK_API_KEY
cp ../.env.example ../.env

# 可选：构建知识库词法索引（不建则自动关闭检索功能）
python build_index.py --query 二分查找

# 冒烟测试（不需要启动 Flask）
python smoke_deepseek.py

# 深度模式冒烟（可选：验证 Agent 工具循环与卡片生成）
python smoke_agent.py

# 启动后端
python main.py                    # http://127.0.0.1:5000
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev                       # http://127.0.0.1:5173
```

前端开发服务器已把 `/api` 代理到 `http://127.0.0.1:5000`，浏览器打开 5173 端口即可。

### 3. 演示提示

- **快答 / 深度**：输入框上方可切换；快答只做一次文字回答（更快），深度走 Agent 工具循环并可能生成卡片；
- **智能 UI**：深度模式下可能生成「参考资料 / 解题步骤 / 相关章节」三类卡片，可筛选、展开、勾选（仅本页进度）与「追问这一步」；
- **执行过程**：回答下方的折叠面板展示本轮工具调用与耗时，便于演示 Agent 的检索过程；
- 教师账号：在注册页选择「教师」角色即可（仅演示用；生产环境应改为审核/邀请制）；
- 想看到「教师权威答案回流」：先用同一个问题或近义问法再问一次（词法匹配阈值见 `.env` 的 `AUTHORITATIVE_SIM_THRESHOLD`）；
- 教师端「学情分析」首次打开会实时调用模型生成，稍等几秒（24 小时缓存）。

演示题库、通过标准与失败兜底见 `migration/DEMO_QA.md`，完整演示流程见 `migration/demo-runbook.md`。

### 4. 测试与构建验证

```bash
# 后端离线测试（不调用真实 API）
cd backend
PYTHONPATH=. python -m unittest discover -s tests -v

# 前端构建验证
cd ../frontend
npm run build
```

## 配置说明

所有配置在 `.env` 中（从 `.env.example` 复制，**不要提交到仓库**）：

| 变量 | 说明 | 默认值 |
| :--- | :--- | :--- |
| `DATABASE_URL` | 数据库连接串（SQLite 相对路径落在 `backend/instance/`） | `sqlite:///./learning_assistant.db` |
| `EMAIL_*` | 留言通知邮件配置；保持占位值时自动跳过真实发信 | 占位值 |
| `SECRET_KEY` | Flask Session 签名密钥，部署时务必改随机值 | 占位值 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key（必需） | 无 |
| `DEEPSEEK_BASE_URL` | API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型名（`deepseek-flash` 支持图片） | `deepseek-flash` |
| `DEEPSEEK_THINKING` | 思考模式开关：`disabled` / `enabled` | `disabled` |
| `DEEPSEEK_MAX_TOKENS` | 单次回答最大输出 token | `1024` |
| `AGENT_MAX_ROUNDS` | 深度模式最多模型请求轮次 | `6` |
| `AGENT_TIMEOUT_SECONDS` | 深度模式单轮整体超时（秒） | `50` |
| `AGENT_MAX_OUTPUT_TOKENS` | 深度模式单次调用输出上限 | `2048` |
| `AUTHORITATIVE_SIM_THRESHOLD` | 权威答案词法匹配阈值（0~1） | `0.45` |

## 安全提示

- **不要提交 `.env`**：本仓库为公开仓库，API Key 一旦泄露请立即在平台吊销。若 `.env` 曾被 git 跟踪，执行 `git rm --cached .env`；
- 演示版默认允许自助注册教师账号、未做邮箱验证/XSS 深度防护，请勿直接公开部署；
- 学生问答内容会发送至 DeepSeek API，演示请使用虚构数据，勿上传真实学生隐私信息。

## 旧版本（本地模型方案）

旧的本地 Qwen3-VL + BGE + FAISS 实现保留在 git 历史中（迁移前最后一个提交为 `cd3fc28`），如需回退可执行 `git checkout cd3fc28 -- backend requirements.txt README.md`。
