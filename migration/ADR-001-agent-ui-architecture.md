# ADR-001：演示版 Agent 与智能 UI 架构决策

- 状态：已采纳（Phase 0）
- 日期：2026-11-10
- 背景：XDWe 演示版从本地模型迁移到 DeepSeek API 后，需要吸收 xdu-zhixing 的 Agent 与智能 UI 能力（卡片化回答）。
- 约束：zhixing 仓库只读；XDWe 保持单进程 Flask；演示优先、可降级；不破坏现有登录/教师/留言功能。

## 决策

### D1 Agent 采用进程内模块，不引入独立服务
- 实现：`backend/modules/agent.py`（DeepSeek function-calling 循环）+ `backend/modules/agent_tools.py`（工具层）。
- 理由：演示只需单进程；避免 FastAPI/pydantic-ai 依赖与第二套进程；与 DeepSeek 迁移后的 `ai.py` 天然衔接。
- 代价：不搬知行 harness 的预算/多档/多租户能力，后续如需可再拆服务。

### D2 卡片类型固定为三类（学习场景改造）
| 类型 | 说明 | 数据来源 |
|---|---|---|
| `source_list` 参考资料卡 | 列出本轮实际检索到的资料，可筛选、逐条追问 | 本轮 BM25 检索的引用注册表 |
| `guide` 解题步骤卡 | 分步骤讲解，每步可带引用；可展开、勾选、追问这一步 | 模型生成步骤文本 + 引用号 |
| `related_chapters` 相关章节卡 | 指向本地知识库章节目录，便于继续学习 | 服务端固定章节目录，模型只给 chapterId |

- 模型只提交引用号/章节 ID 与纯文本，**标题、来源地址、章节标题由服务端注入**；禁止 HTML/脚本/外链。
- 校验规则（移植知行 `ui.py` 思路）：`{version:1, cards:[...]}`、最多 3 张、引用 1–8 个、非法卡片丢弃但保留文字回答。

### D3 SSE 事件协议 v1（向后兼容）
- 事件：`start` / `status` / `tool_call` / `tool_result` / `answer_delta` / `answer_reset` / `ui` / `complete` / `done` / `error`。
- 兼容：`answer_delta` 同时按旧 `data: {"token": ...}` 渲染；不传 `uiVersion` 的客户端不启用卡片（纯文本降级）。
- 请求：`POST /api/qa` 新增可选 `uiVersion`、`mode`（`fast`/`deep`）。

### D4 工具集（第一版只做演示必需）
- `retrieve_knowledge`：BM25 检索知识库，返回引用注册表；
- `read_source`：按引用号读取资料原文片段（限量）；
- `safe_math`：四则运算工具（沿用现有实现）；
- `present_ui`：提交卡片描述（工具内校验，失败不消耗重试预算）。
- 不迁移：校园/学术/网页检索、附件、权限体系。

### D5 存储与历史回放
- `question` 表新增可空列 `ui_json`、`trace_json`、`mode`；演示库可直接重建。
- 历史接口按存储内容回放卡片与工具轨迹；旧数据（无 ui_json）降级纯文本。
- 卡片交互状态（筛选/展开/勾选）不持久化，刷新重置（与知行一致）。

### D6 快答 / 深度两档
- `fast`：单次模型请求 + 预检索（不启用工具循环与卡片）；
- `deep`：Agent 工具循环（最多 6 轮）+ 卡片；
- 前端输入框上方切换；每轮请求携带 mode，历史记录保存 mode。

## 后续（Phase 4+，不在演示关键路径）
多轮会话实体、混合检索、联网检索、知行三档模式、trace 落库与评测、生产化安全。
