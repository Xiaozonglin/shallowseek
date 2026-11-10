# XDWe 演示版升级任务计划书
## DeepSeek API 迁移 + 知行 Agent / 智能 UI 移植

> 约束：**zhixing（`~/github/xdu-zhixing`）全程只读**，不写入、不复制其仓库文件；所有改动只落在 XDWe（`~/github/shallowseek`）。
> 本计划把上一轮的 DeepSeek 迁移补丁与本轮的 Agent/卡片迁移合并为一条交付线，按 4 个阶段、约 20 个子任务执行。

---

## 1. 目标与原则

**目标**：把 XDWe 从「文字流式问答 Demo」升级为「会调工具、卡片化呈现、过程可见」的智能体体验，演示效果接近知行但保持 XDWe 的单进程轻量架构。

**原则**：
- demo 优先：只做演示能看见的能力，不做生产化安全/多租户改造；
- 降级优先：agent 出错、卡片非法、模型不配合时，**自动退回纯文本问答**，演示不中断；
- 最小侵入：保留现有登录、教师权威答案、学情分析、留言等全部功能；
- 不搬技术栈：不引入 `pydantic-ai` / FastAPI / 独立 Harness 进程，Agent 循环用 `openai` SDK 手写，卡片校验用 `pydantic`（openai 已自带）；
- 前置基线：上一轮的 DeepSeek 迁移补丁（`migration/deepseek-migration.patch`）先评审通过并应用。

**吸收 vs 不吸收**：

| 吸收（只借鉴协议与设计，不复制代码） | 不吸收（对本 Demo 无收益/过重） |
|---|---|
| Agent 工具循环思想、预算/超时/轮次上限 | `pydantic-ai` 框架、独立 FastAPI Harness 进程 |
| SSE 事件协议（status / tool / delta / complete / error） | 三档模式全套（no-agent/pro/ultra）暂缓 |
| `present_ui` + `UIEnvelope` 卡片协议、服务端严格校验 | 校园检索/学术检索/网页抓取/附件/工单工具 |
| 模型只给引用号或 ID，标题与链接由服务端注入 | Next.js 组件原样搬迁（改写为 Vue 组件） |
| 卡片交互：来源筛选、步骤展开勾选、追问 | 会话/消息/轨迹完整数据库模型（XDWe 用 Question 扩展） |
| 提示词纪律（何时出卡、引用必须来自本轮）、验收题集方法 | CAS/权限体系、管理端、小程序等 |

---

## 2. 目标架构（改完后的 XDWe）

```txt
Vue StudentView（新增卡片区 / 工具轨迹 / 追问交互）
  │  fetch SSE：start / status / tool_call / tool_result / answer_delta / answer_reset / ui / complete / done / error
  ▼
Flask /api/qa（升级为事件流，保留旧 token 帧一个版本期兼容）
  ├─ modules/agent.py        Agent 工具循环（DeepSeek function calling，≤6 轮，整体超时）
  ├─ modules/agent_tools.py  工具：retrieve_knowledge / read_source / safe_math / present_ui
  ├─ modules/ui_cards.py     卡片 Pydantic 协议 + 引用校验（模型只交引用号/章节 ID）
  ├─ modules/retrieval.py    BM25 词法检索（DeepSeek 迁移已提供）
  ├─ modules/ai.py           DeepSeek API 封装（DeepSeek 迁移已提供）
  └─ SQLite：question 表新增 ui_json / trace_json（演示库可直接重建）
```

**卡片类型（校园场景 → 学习场景改造）**：

| 知行卡片 | XDWe 卡片 | 说明 |
|---|---|---|
| `source_list` | 参考资料卡 | 引用号来自本轮 BM25 检索；可筛选、逐条追问 |
| `guide` | 解题步骤卡 | 步骤 + 每步引用；勾选仅本页；「追问这一步」 |
| `service_links`（固定服务目录） | 相关章节卡（固定章节目录） | 模型只给 chapterId，服务端目录注入标题；不做外部跳转 |
| —（知行无） | 知识点卡（可选后续） | 概念/公式/易错点要点，Phase 4 候选 |

---

## 3. 阶段与子任务

### Phase 0：基线就绪（约 1 天）

| 编号 | 子任务 | 产出 | 依赖 | 预估 |
|---|---|---|---|---|
| T0.1 | 评审并应用 DeepSeek 迁移补丁；配置 Key；冒烟 + 建 BM25 索引 | XDWe 文本/图片问答跑在 DeepSeek API 上 | 补丁评审通过 | 0.5d |
| T0.2 | 冻结协议与 ADR：SSE 事件 v1、卡片 UIEnvelope、Question 字段、降级策略、uiVersion 开关 | ADR 1 页（并入本计划附录） | T0.1 | 0.5d |

**验收**：`smoke_deepseek.py` 通过；前端文本问答流式正常；旧版前端不传 `uiVersion` 时行为不变。

### Phase 1：Agent 后端（约 2 天）

| 编号 | 子任务 | 产出 | 依赖 | 预估 |
|---|---|---|---|---|
| T1.1 | Agent runtime：DeepSeek function-calling 循环、工具白名单、轮次/超时/预算、失败回退纯文本、注入最近历史 | `backend/modules/agent.py` | T0.2 | 1d |
| T1.2 | 工具层 + 本轮引用注册表：`retrieve_knowledge`、`read_source`、`safe_math` | `backend/modules/agent_tools.py` | T1.1 | 0.5d |
| T1.3 | 卡片协议与校验：`source_list` / `guide` / `related_chapters`；移植知行校验思想（丢弃非法卡片不丢文字）| `backend/modules/ui_cards.py` + `chapter_catalog.json` | T0.2 | 0.5d |
| T1.4 | `/api/qa` 升级为 SSE 事件流 + 落库（`ui_json`、`trace_json`、耗时）；历史接口返回卡片与轨迹 | `backend/main.py` | T1.1/T1.3 | 0.5d |

**验收**：脚本触发「检索→读原文→出卡→回答」完整链路；非法引用/非法卡片被丢弃且文字正常返回；curl 可见完整事件序列。

### Phase 2：智能 UI 前端（约 2 天）

| 编号 | 子任务 | 产出 | 依赖 | 预估 |
|---|---|---|---|---|
| T2.1 | SSE 事件解析与状态机（含 answer_reset、帧合并、旧 token 兼容） | `frontend/src/utils/sse.js` + StudentView | T1.4 | 0.5d |
| T2.2 | 卡片组件：参考资料卡（筛选/来源）、解题步骤卡（展开/勾选/每步依据）、相关章节卡 | `frontend/src/components/cards/*.vue` | T1.3 | 1d |
| T2.3 | 引用联动：正文 `[n]` 定位来源、来源折叠摘要、来源卡与正文互跳 | StudentView + 卡片组件 | T2.2 | 0.5d |
| T2.4 | 工具轨迹面板（流式显示「正在检索知识库…」、耗时）+「追问这一步」 | 组件 + StudentView | T2.1/T2.2 | 0.5d |
| T2.5 | 历史回放（从 `ui_json`/`trace_json` 恢复卡片）、旧消息降级纯文本、移动端适配 | 组件 + 历史接口 | T2.2 | 0.5d |

**验收**：三类卡片渲染与交互正常；非法数据不崩溃、降级为文字；刷新后卡片恢复；暗色主题与移动端宽度正常。

### Phase 3：联调、提示词与演示打磨（约 1 天）

| 编号 | 子任务 | 产出 | 依赖 | 预估 |
|---|---|---|---|---|
| T3.1 | XDWe 学习助手提示词（何时出卡、最多 3 张、引用必须来自本轮检索、文字必须独立可读）+ 12 题演示题库与验收表 | `backend/agent_prompts.py` + 验收表 | T1.3 | 0.5d |
| T3.2 | 稳定性兜底：超时/断网/401/429/模型不出卡 → 中文提示或纯文本；工具轮次上限 | 改造 | T2.5 | 0.5d |
| T3.3 | 演示数据与 runbook：账号、历史问答、权威答案样例、卡片效果截图/录屏备份 | `migration/demo-runbook.md` | 各阶段 | 0.5d |
| T3.4 | （可选）快答 / 深度两档切换，用于现场对比「普通问答 vs Agent 卡片」 | StudentView 开关 | T1.4 | 0.5d |

**验收**：演示题库 10 题中 ≥8 题按预期出卡或无卡；断网/欠费等异常有可读提示；全流程 ≤5 分钟。

### Phase 4：可选后续（不阻塞演示）

- 多轮会话实体（conversations/messages）与历史预算；
- 混合检索（BM25 + 远程 embedding API）替换纯词法；
- 联网检索（DeepSeek Search & Fetch）+ 来源核验；
- 三档模式、trace 落库与评测脚本；
- 生产化：教师注册审核、XSS 消毒、密钥管理、对话归属等。

---

## 4. 里程碑与排期

| 里程碑 | 内容 | 预计 |
|---|---|---|
| **M0** | DeepSeek 基线：文本/图片问答可用（T0） | 1 天 |
| **M1** | Agent 后端：工具循环 + 事件流 + 卡片数据（T1） | +2 天 |
| **M2** | 智能 UI：卡片渲染 + 引用/轨迹/追问（T2） | +2 天 |
| **M3** | 演示打磨：提示词/题库/兜底/runbook（T3） | +1 天 |
| 合计 | 前后端可并行，压到约 **4–5 天** | — |

关键路径：`T0.1 → T1.1 → T1.2/T1.3 → T1.4 → T2.1 → T2.2 → T3.*`

---

## 5. 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 模型不按规范出卡 / 编造引用 | 卡片不出现或内容错 | 工具内校验 + 最多 1 次重试；文字始终独立可读；不达标就当纯文本回答 |
| Agent 工具循环拖慢演示 | 单问 20–60s | 工具轮次 ≤6、整体超时 45s、首问预热、可选快答降级 |
| SSE 协议改造破坏现有前端 | 问答不可用 | 新事件与旧 `token` 帧并存一版；`uiVersion` 开关控制卡片生成 |
| Question 表加列影响旧演示库 | 启动报错 | 演示库直接重建，附一次性 SQL；不引入迁移框架 |
| 依赖变重（pydantic-ai 等） | 安装困难 | 不引入知行框架；openai SDK 手写循环，pydantic 随 openai 自带 |
| 现场生成效果不稳定 | 演示翻车 | 题库演练 + 预录屏/截图兜底 + 权威答案案例 |
| 顺手改动 zhixing | 污染参考项目 | 全程只读；计划内所有任务只改 XDWe |

---

## 6. 演示前验收清单

- [ ] DeepSeek 文本问答正常，图片问答正常；
- [ ] Agent 工具链路可复现：至少 2 个「检索 → 读原文 → 出卡/回答」场景；
- [ ] 三类卡片均出现；非法卡片自动丢弃、文字回答完整；
- [ ] 正文引用可定位来源；步骤勾选、追问这一步、来源筛选可用；
- [ ] 刷新后卡片与轨迹恢复；工具执行过程可见；
- [ ] 断网/401/429/超时均有中文提示，不白屏；
- [ ] 教师端学情分析、留言、权威答案流程不受影响；
- [ ] 12 题验收 ≥8 达标；全流程 ≤5 分钟。

---

## 附录 A：知行 → XDWe 参考映射（只读参考，不复制文件）

| 知行文件 | 参考价值 | XDWe 落点 |
|---|---|---|
| `backend/agent_harness/ui.py` | 卡片 Pydantic 校验、引用/服务 ID 校验模式 | `backend/modules/ui_cards.py` |
| `backend/agent_harness/app.py`（present_ui、prepare_presentation、SSE、MODE_PROFILES） | 工具循环、事件协议、预算控制思想（2191 行不整体搬运） | `backend/modules/agent.py`、`backend/main.py` |
| `backend/agent_harness/tests/fixtures/ai-ui.json`、`tests/test_ui.py` | 非法卡片用例集（未知版本/伪造引用/超量卡片/HTML 注入） | `backend/tests/` 与前端 fixture |
| `src/lib/ai/ui.ts` | 双端校验、ID 注入、URL 白名单 | `frontend/src/utils/uiCards.js` |
| `src/app/(protected)/ai/UICards.tsx` | 卡片交互与文案（筛选/展开/勾选/追问） | `frontend/src/components/cards/*.vue` |
| `src/lib/ai/streamBuffer.ts`、`messagePhase.ts` | 流式合并写、卡片出现时序 | `frontend/src/utils/sse.js`、卡片入场动画 |
| `docs/intelligent-ui.md`、`docs/intelligent-agent-modes.md` | 协议语义、验收标准、失败降级 | 本计划与验收表 |
| `docs/ai/小电系统提示词.txt`、`docs/ai/小电验收场景.md` | 提示词纪律（引用必须来自本轮、不出卡也须文字完整）、验收题集做法 | `backend/agent_prompts.py`、T3.1 题库 |

## 附录 B：协议草案（简版）

- 请求：`POST /api/qa` 增加 `uiVersion: 1`（缺省 0 → 不启用卡片，纯文本降级）；
- SSE 事件：`start` → `status` / `tool_call` / `tool_result` / `answer_delta`（兼容旧 `token`）/ `answer_reset` / `ui` / `complete` / `done` / `error`；
- 卡片协议：`{version:1, cards:[...]}`，最多 3 张：
  - `{"type":"source_list","citations":[1..8]}`
  - `{"type":"guide","title":str,"steps":[{"title":str,"detail":str,"citations":[1..8]}...]}`
  - `{"type":"related_chapters","chapterIds":["searching","sorting"...]}`
- 服务端只接受引用号/章节 ID；标题、来源地址由本轮检索注册表与章节目录注入；含 `<`/`>` 的展示文本、非法 URL、伪造引用一律丢弃该卡片。
