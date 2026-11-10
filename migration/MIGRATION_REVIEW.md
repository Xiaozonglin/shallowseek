# DeepSeek API 迁移评审包（Review Package）

- 基线：`main` @ `cd3fc28`（迁移前最后一个提交）
- 补丁：`migration/deepseek-migration.patch`（1,739 行，SHA-256 `50e7fc6a4edbc04a1760bdc0f02e17fdd4830488c443ffcd877bdfc64c5cfb61`）
- 状态：**未应用**。当前工作区仍是迁移前代码（`git status` 只有未跟踪的 `migration/` 目录），补丁已通过 `git apply --check`。
- 决策记录（已与你确认）：
  1. 不再使用任何本地大模型（移除 Qwen3-VL / BGE / FAISS / PyTorch）；
  2. RAG 与「教师权威答案」匹配改用 **jieba + BM25 词法检索（方案 B3）**；
  3. 保留图片问答 —— `deepseek-flash` 原生支持视觉；
  4. 演示优先：`DEEPSEEK_THINKING=disabled`（更快更省钱）；
  5. 前端 SSE 契约不变，仅增强解析健壮性与错误提示。

---

## 1. 变更总览

`git apply --stat` 结果：

| 文件 | 变更 | 说明 |
|---|---|---|
| `backend/modules/ai.py` | 重写（298 → 240 行） | 本地模型推理 → DeepSeek API 封装；对外接口保持旧风格 |
| `backend/modules/retrieval.py` | **新增（372 行）** | jieba 分词 + BM25 + 短文本相似度，替代 BGE/FAISS |
| `backend/main.py` | 修改（606 → 548 行） | 8 处 hunk：移除 torch/线程/Streamer，问答/统计/图片/留言改走 API |
| `backend/build_index.py` | **新增（66 行）** | 构建 `backend/bm25_index/index.json`，可 `--query` 自检 |
| `backend/smoke_deepseek.py` | **新增（51 行）** | P0 冒烟：验证 Key + 模型 + 流式输出 |
| `backend/modules/detecter.py` | **删除（14 行）** | 死代码（依赖不存在的 `prompt_guard`，从未接线） |
| `frontend/src/views/StudentView.vue` | 修改（+67 行） | 流式解析改为跨 chunk 缓冲；处理 `error`/`done` 帧；错误文案透出；断流保留部分回答 |
| `requirements.txt` | 重写（109 → 26 行） | 删除 torch/transformers/faiss/langchain 等全部重型依赖 |
| `.env.example` | **新增（33 行）** | 配置模板（含 DeepSeek 变量） |
| `.gitignore` | 修改（+7 行） | 忽略 `.env`、`.env.local`、`bm25_index` |
| `README.md` | 重写（+132/-34） | 新架构、10 分钟部署步骤、配置表、安全提示 |
| **合计** | **+954 / −550** | 11 个文件 |

**补丁之外需要手动执行的两步**（patch 无法表达）：

1. `git rm --cached .env` —— 取消跟踪已被公开的占位 `.env`，保留本地文件（迁移后 `.env` 会放 API Key，**必须做**）；
2. `git rm environment.yml` —— UTF-16 的 Windows 导出文件，已无价值（patch 无法对二进制文件生成文本删除）。

---

## 2. 关键实现

### 2.1 `backend/modules/ai.py`：AIEngine 新接口

| 方法 | 用途 | 替代的旧实现 |
|---|---|---|
| `stream_answer(system_prompt, user_text, image_data_url=None)` | 流式回答，yield 文本增量 | `_build_inputs_from_messages` + `TextIteratorStreamer` + 手动子线程 `generate` |
| `generate_text(system_prompt, user_prompt, max_tokens)` | 非流式生成（学情分析） | 本地 `llm.generate` + batch_decode |
| `analyze_image_standalone(image_b64)` | 纯图片解析 | Qwen3-VL 本地推理 |
| `retrieve_context(query)` | BM25 检索上下文 | `FAISS + BGE` retriever.invoke |
| `text_similarity(a, b)` | 权威答案匹配 / 留言去重 | `embeddings.embed_query` + `util.cos_sim` |
| `safe_math(query)` | 四则运算工具 | 原样保留（纯 Python） |
| `friendly_error(exc)` | 401/402/429/5xx/超时/断网 → 中文提示 | 无 |

其他要点：
- 初始化时校验 `DEEPSEEK_API_KEY`，缺失直接抛错（避免"能启动但所有 AI 功能静默失败"）；**不加载任何模型，启动秒级**；
- 思考模式不是 OpenAI SDK 标准字段，通过 `extra_body={"thinking": {"type": ...}}` 传递；
- 图片按官方要求放在 `user` 消息的 `image_url` 内容块中（`detail: "auto"`），`system` 消息只放文本；
- `stream_answer` 在 `finally` 中关闭流；空 `choices` / `delta.content=None` 的 chunk 已跳过；
- 错误分类基于 `status_code` 与异常类名，`main.py` 与 `smoke_deepseek.py` 复用。

### 2.2 `backend/modules/retrieval.py`：词法检索

- 分词：`jieba.lcut_for_search` + 中文双字 bigram；**jieba 缺失时自动退化为字符 n-gram**（保证无依赖环境也能跑/测试）；
- 索引：Markdown 按空行/标题切块（800 字、150 字重叠），过滤图片语法与 HTML，写入 JSON（含预分词结果），启动只读 JSON + 建 BM25 表，毫秒级；
- BM25：自实现（k1=1.5, b=0.75，与 `rank_bm25` 口径一致），**不新增检索依赖**；
- 相似度：`max(词元余弦, 中文双字 Jaccard)`，用于权威答案匹配与留言去重；
- 索引缺失/损坏/版本不符时只 warning 并关闭检索（与旧 FAISS 行为一致），不影响服务启动。

### 2.3 `backend/main.py`：8 处 hunk

1. **导入区**：删除 `torch`/`threading`/`io`/`PIL`/`langchain*`/`sentence_transformers`，新增 `logging`；
2. **AI 引擎段**：注释与初始化说明改为 DeepSeek（`ai = AIEngine()` 位置不变）；
3. **`get_authoritative_context`**：embedding 余弦 → `ai.text_similarity`，阈值改为环境变量 `AUTHORITATIVE_SIM_THRESHOLD`（默认 0.45）；
4. **`generate_ai_text`**：35 行本地推理 → 1 行调用 `ai.generate_text`；
5. **`handle_qa` 的 `generate()`**：删掉 Streamer + `threading.Thread` + `llm.generate`，改为 `for token in ai.stream_answer(...)`；
   - 保留 `data: {"token": ...}` 契约（前端无需同步升级）；
   - 新增 `data: {"done": true}` 结束帧与 `data: {"error": "..."}` 错误帧；
   - 落库逻辑保留（流结束后写 `question` 表），异常时不再 500，而是返回可展示错误；
6. **`/api/upload/image`**：注释更新（图片交给 DeepSeek 视觉），调用签名不变；
7. **留言去重**：embedding 余弦 → `ai.text_similarity`（阈值 0.8）；
8. **启动横幅**：改为"DeepSeek API，不加载本地模型"的提示。

未改动：认证、数据库模型、教师端路由、留言/邮件、安全响应头、限流、`safe_math` 调用逻辑。

### 2.4 前端（`StudentView.vue`）

- `readStreamingResponse` 改为 **buffer + `\n` 切行**：解决跨 chunk 半行导致 `JSON.parse` 失败、丢 token 的老 bug；
- `TextDecoder` 使用 `{ stream: true }`，避免多字节中文被切断；
- 识别 `data.error` 帧并 `throw`，两个 catch 改为 `alert(error.message || 兜底文案)`；
- `data.done` 帧被安全忽略（无需额外处理）。
- 其他视图未改动。

---

## 3. 行为变化（需要你确认）

| 项 | 迁移前 | 迁移后 |
|---|---|---|
| 启动依赖 | GPU/模型权重/5GB 下载/约 109 个包 | 只需 API Key，约 26 个包，无 GPU |
| 启动耗时 | 加载 Qwen3-VL（分钟级） | 秒级 |
| 文本回答 | 本地 Qwen3-VL | DeepSeek `deepseek-flash`（质量通常明显更好） |
| 图片问答 | 本地 Qwen3-VL | `deepseek-flash` 视觉（支持 JPEG/PNG/GIF/WebP，单图≤32MB，图片按尺寸计 token） |
| 知识库检索 | BGE 向量 + FAISS（语义） | jieba + BM25（词法；近义改写召回弱于向量） |
| 权威答案匹配 | 余弦 > 0.75 | 词法相似度 > 0.45（可配） |
| 留言邮件去重 | 余弦 > 0.85 | 词法相似度 > 0.8 |
| 回答长度 | max_new_tokens=1024 | `DEEPSEEK_MAX_TOKENS=1024`（同） |
| 思考模式 | 无 | 默认 `disabled`（可开，开后有 `reasoning_content` 但更慢更贵） |
| SSE 帧 | 仅 `token` | `token` + `done` + `error`（需配合本次前端补丁） |
| 索引文件 | `backend/faiss_index/` | `backend/bm25_index/index.json`（都 gitignore） |
| 离线可用 | 完全离线 | 需要网络（现场请准备热点） |
| 失败模式 | 本地 OOM/慢 | 401/402/429/5xx/超时 → 中文提示（不影响服务进程） |

> 提示：由于 `deepseek-flash` 非思考模式下 `top_p` 固定 1.0（传参会被忽略），代码只传 `temperature`。

---

## 4. 已验证项（本次评审前已执行）

| # | 验证 | 结果 |
|---|---|---|
| 1 | `git apply --check` | ✅ 干净应用 |
| 2 | 临时 worktree 应用补丁后 `py_compile` 全部 Python 文件 | ✅ main/ai/retrieval/build_index/smoke 均通过 |
| 3 | 应用后运行 `build_index.py`（本机无 jieba，走字符 n-gram 退化路径） | ✅ 100 篇文档 → 4,011 片段，0.1s；自检 "二分查找/动态规划/快速排序/二叉树遍历/图 BFS" 均命中正确章节 |
| 4 | 检索质量抽样（fallback 分词） | "快速排序"→quick_sort.md；"动态规划 背包问题"→knapsack_problem.md；"二叉树遍历"→binary_tree_traversal.md |
| 5 | `text_similarity` 抽样 | 同句 1.000；"什么是二分查找"↔"二分查找是什么" 0.818；"怎么实现"↔"的实现方式" 0.668；不相关 0.000 |
| 6 | 用 fake OpenAI SDK 离线测试 `AIEngine` | ✅ 流式增量、非流式、视觉调用、data URL 规整、402/超时文案、缺 Key 守卫全部符合预期 |
| 7 | 应用补丁后的 worktree 中加载 AIEngine + 索引 | ✅ retriever 正常加载、流式返回预期 token |

**未验证（需要真实环境，评审通过后第一步执行）：**

```bash
# 1) 真实 API 联调（需要 Key）
cd backend && python smoke_deepseek.py
# 2) Flask 启动 + 前端联调（需要 pip install / npm install）
python main.py
cd ../frontend && npm run dev
# 3) 浏览器冒烟：学生提问流式→落库→历史；教师端学情；图片问答
```

---

## 5. 评审后如何应用

```bash
# 建议在新分支上操作
git checkout -b feat/deepseek-api

# 1) 应用补丁
git apply migration/deepseek-migration.patch

# 2) 必须手动执行：取消跟踪 .env（保留本地文件），防止 API Key 被提交到公开仓库
git rm --cached .env

# 3) 可选：删除无用的二进制环境文件
git rm environment.yml

# 4) 配置 Key
cp .env.example .env        # 若本地已有 .env，则手动补 DEEPSEEK_API_KEY 等变量
#   编辑 .env：填入 DEEPSEEK_API_KEY=sk-xxxx

# 5) 安装依赖（不再需要 GPU/PyTorch）
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r ../requirements.txt

# 6) 冒烟 + 建索引 + 启动
python smoke_deepseek.py
python build_index.py --query 二分查找
python main.py

# 7) 前端（另开终端）
cd frontend && npm install && npm run dev
```

**回滚**：
```bash
git apply -R migration/deepseek-migration.patch    # 反向应用
# 或直接切回迁移前提交
git checkout cd3fc28 -- backend requirements.txt README.md .gitignore frontend/src/views/StudentView.vue
```

---

## 6. 本补丁之外的建议待办（不阻塞评审）

| 优先级 | 事项 | 说明 |
|---|---|---|
| P1 | 更新 `backend/API文档.md` | 模型名、登录响应、7 条缺失路由、阈值、思考模式等，建议单独一版补丁 |
| P1 | 前端体验小修 | 学生历史展示 `authoritative_answer`；教师端操作 toast；axios 超时/401 拦截；注册后直接跳工作台（均为迁移前已列出的 C 类） |
| P1 | `stats` 并行化 | 学生数多时逐个学生调用 API 会变慢，可用线程池只并行"生成"、串行写库 |
| P2 | 可选增强 | 思考过程 SSE 展示、DeepSeek Search & Fetch（恢复联网能力）、JSON 化学情分析、图片压缩 |
| P2 | 清理 | `backend/modules/helpers.py`（空文件）可删；`.gitignore` 里旧的 `model_weights/rag-embedding/vlm_weights/faiss_index` 行可清理；`documents_workflow/` 依赖按需保留 |
| — | 明确 demo-only | 公开部署前需处理：教师自助注册、XSS 消毒、密钥管理、数据合规、限流/迁移等（见此前"演示 vs 部署"清单） |

---

## 7. 请评审确认的 5 个点

1. **词法阈值**：权威答案 0.45、留言去重 0.8 是否接受？（演示剧本会"近义复问"触发；阈值都可通过环境变量调整，无需改代码）
2. **依赖版本**：`openai>=1.66,<3` 的宽松范围是否可接受？安装后建议 `pip freeze` 锁一版。
3. **删除项**：同意删除 `backend/modules/detecter.py`（死代码）与 `environment.yml`（二进制、已过时）吗？
4. **思考模式**：演示默认关闭（速度/成本优先）；若想现场展示推理过程，把 `.env` 的 `DEEPSEEK_THINKING` 改为 `enabled` 即可——是否需要前端配套展示 `reasoning_content`（本补丁未含）？
5. **索引产物**：`bm25_index` 保持 gitignore + 现场 `build_index.py` 生成，还是随仓库提交一份（约 2MB JSON）以便"克隆即可检索"？

---

## 8. 风险提示

- **API Key 泄露**：`.env` 目前仍被 git 跟踪且仓库公开；应用补丁后必须先 `git rm --cached .env`。若 Key 曾出现在任何提交中，请立即在平台吊销。
- **网络依赖**：演示现场断网则 AI 全不可用；建议手机热点兜底，并在演示前实测一次 `smoke_deepseek.py`。
- **数据合规**：学生问答会发送到 DeepSeek；演示用虚构数据，勿上传真实学生信息。
- **成本**：`deepseek-flash` 闲时输入 $0.15/M、输出 $0.6/M；一场演示（50 问 + 学情）约 $0.05–0.1，可忽略。
- **前后端需一起更新**：若只改后端不改前端，`error` 帧会被旧解析忽略（表现为"空白答案"）；补丁已同时包含前端增强，建议一起应用。
