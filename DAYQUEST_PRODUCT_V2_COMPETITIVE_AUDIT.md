# DayQuest Product V2 Competitive Audit

Audit ID：`DQ-FLAGSHIP-COMPETITIVE-GAP-PRODUCT-V2-20260830-02`

状态：`Competitive Evidence Complete / Product V2 Local Technical Complete / Awaiting Public-Evidence Review`

访问日期：`2026-08-30`

本审计绑定公开仓库的固定 Git ref 与官方文档，只把可运行产品或工程行为视为差异。Stars、README 宣传语和文档数量不构成结果证据。由于相邻产品需要下载安装桌面采集器、Docker 栈、Node/Python 依赖或 API key，本轮没有执行第三方代码；相邻项目结论属于固定版本的文档、架构与公开产品流程比较，不是性能比较。

## 1. 结论先行

`local-first`、活动时间线、MCP、source reference（来源引用）、离线 demo、trace viewer（轨迹查看器）和 eval matrix（评测矩阵）均已有成熟实现。它们不能单独构成 DayQuest 的独特性。

唯一值得继续的 Top-1：

> **DayQuest is an epistemic timeline debugger for personal activity evidence. It shows not only what may have happened, but exactly which bounded evidence makes a claim Supported, Unknown, or Conflict; users can replay reversible source/evidence interventions and inspect how claim state and downstream summaries change without rewriting the canonical evidence.**

中文：DayQuest 是个人活动证据的认知状态时间线调试器。它不只展示“发生了什么”，还显示哪条有界证据使结论成为 `Supported / Unknown / Conflict`；用户可对来源缺失、证据补入和冲突隔离进行可逆 replay（回放），观察结论和摘要如何变化，而不改写原始权威证据。

这是产品/工程差异候选，不是学术创新声明。V2 必须以交互式 before/after、稳定 receipt 和同一输入上的行为门证明它存在。

## 2. 固定身份与成熟项目证据

| 项目 | 2026-08-30 固定身份 | 官方用户任务与成熟能力 | 与 DayQuest 的重叠 | 对 DayQuest 的直接结论 |
|---|---|---|---|---|
| ActivityWatch | `ActivityWatch/activitywatch@5d26465fd54e513e9e912bb410e08ac52facfb4d` | 跨平台本地时间追踪；heartbeat/bucket/event/query API；Dashboard、timeline、query explorer、raw event browser、JSON export；公开 release 与集成测试 | local-first、一天的时间线、事件来源、查询与导出 | DayQuest 不能把“本地时间线”或“查看原始事件”作为独特性；必须展示 claim-level（结论级）证据状态和可逆推理回放 |
| screenpipe | `dp466/screenpipe@dd071b490d4dc5067e67b104723cc4992094c377` | 本地持续采集屏幕/音频/应用；SQLite、搜索、timeline、local API、MCP、agent automation；跨平台桌面产品 | local capture、MCP、一天总结、agent 可访问历史 | DayQuest 不应扩张为全面采集器，也不能把 MCP 或“总结我的一天”作为独特性；隐私风险和资源成本反而是 screenpipe 的成熟优势与 DayQuest 的刻意非目标 |
| DailyOS | `stadimeti19/DailyOS@34a06910b87a897cfd00447df71b0788fad960b3` | 多来源 Plan My Day、source-linked brief、partial failure 可见、approval-gated writes、SQLite runs、deterministic offline demo | 多来源一天工作流、来源引用、失败可见、离线演示 | DayQuest 的静态 provenance/policy 结构已被覆盖；V2 必须让证据变化可操作、可回放并产生可审计状态差分 |
| Langfuse | `langfuse/langfuse@1124345b79bbf1ffe346abc8cbd4c35bb51a2ac1` | tracing、scores、datasets、experiments、prompt management、自托管与版本化 release | trace drill-down、dataset/eval、可视化审核 | DayQuest 不应成为通用 LLM observability backend；应把复杂工程概念压缩为普通用户能理解的“为什么这条日程不能成为事实” |
| Arize Phoenix | `Arize-ai/phoenix@37916d7351002222fc5a3ee8560528834da85134` | OpenTelemetry/OpenInference tracing、evals、datasets、experiments、replay/playground，本地或云运行 | agent/tool trace、失败调试、同输入实验比较 | replay 和实验比较不是 DayQuest 独有；差异只能来自个人时间线领域的 epistemic state propagation（认知状态传播）和受约束摘要 |
| Promptfoo | `promptfoo/promptfoo@90fa399b941364363f57288fbf305b6d6aaff7ed` | 版本化 test cases、providers、assertions、CLI/CI、red team、失败退出码 | repeatable eval、case matrix、CI | 12-case 和 CLI 本身只是工程底线；V2 需要真实用户工作流和可解释状态变化，而不是增加 case 数量 |
| Inspect AI | `UKGovernmentBEIS/inspect_ai@b6aa1214ddd5bc399f72072c703e44d26524af45` | tasks/solvers/scorers、tool-using agents、limits、checkpointing、intervention、第三方 agent bridge、人类 baseline | agent 环境、工具限制、恢复与 scorer | DayQuest 不能声称通用 agent eval harness；应提供小而完整的领域工作流，并把每个状态变化绑定到证据和 receipt |
| MCP Inspector | `modelcontextprotocol/inspector@edf54f5dec5f1fcd6772074f11238d087dd7a1e2` | Web/CLI/TUI 三入口、同一 MCP client core、tools/resources/prompts 调试、CI 反馈 | MCP server 调试、UI/CLI 一致 | DayQuest 的 MCP 价值必须体现在产品结果而非协议测试；Inspector 已覆盖通用 MCP 调试需求 |

公开权威入口：

- https://github.com/ActivityWatch/activitywatch
- https://github.com/dp466/screenpipe
- https://github.com/stadimeti19/DailyOS
- https://github.com/langfuse/langfuse
- https://github.com/Arize-ai/phoenix
- https://github.com/promptfoo/promptfoo
- https://github.com/UKGovernmentBEIS/inspect_ai
- https://github.com/modelcontextprotocol/inspector
- https://docs.github.com/en/account-and-profile/tutorials/using-your-github-profile-to-enhance-your-resume

## 3. 未保留为核心对标

| 对象 | 处理 | 原因 |
|---|---|---|
| OpenRecall | Secondary reference | local screen recall 与隐私方向相邻，但公开证据显示部分安全能力仍以计划形式表达，且核心仍是 capture/search，不是 claim reconciliation |
| HAT | Discovery only | 个人日程/间隙标注很相邻，但平台单一且能力范围小，不能代表成熟 Agent/LLM 工程上界 |
| OpenAI Evals | Capability reference | 高质量 eval 的重要来源，但默认路径需要 API key，用户产品流与 DayQuest 不相邻 |
| LangChain AgentEvals | Capability reference | trajectory match 对工具路径评测有价值，但不是个人时间线产品，也不能证明 DayQuest 的用户价值 |
| AgentProvenance / 新兴 evidence-first benchmarks | Frontier recognition | 概念非常接近，但成熟度与使用范围不足以替代 ActivityWatch、screenpipe、Langfuse、Phoenix、Promptfoo、Inspect 的主对标地位；同时证明“provenance-first”本身已不是空白词汇 |

## 4. DayQuest V1 的真实位置

### 已实现且保留

- 真实 localhost MCP acquisition 与 privacy-safe projection；
- 稳定 evidence pointer、canonical artifact identity 和 byte-stable reports；
- `Supported / Unknown / Conflict` 与 policy 分轴；
- constrained summary 不消费 Unknown/Conflict/non-compliant claim；
- 12-case deterministic matrix、tool-fault fixtures、fresh-directory reproduction；
- no-key UI、dependency lock、scoped privacy scan、CI configuration。

### 只有文案或不足以区分

- “provenance-first”目前主要是静态展示，用户不能操作证据状态；
- 当前产品日只有三个从不同 case 拼接的 claim，没有统一的 replay session；
- 现有三个透明对照是 ablation（消融）自检，不是成熟产品行为比较；
- 没有 claim state transition、summary delta 或 intervention receipt；
- 没有把失败定位变成“下一条最小证据行动”。

### 已被成熟项目覆盖，删除为核心主张

- local-first；
- activity timeline；
- MCP integration；
- source-linked output；
- offline demo；
- trace/eval dashboard；
- CI + tests + deterministic fixtures。

这些继续作为工程底座，但不再进入一句话独特性。

## 5. 招聘竞争力证据门（Proposed）

依据：GitHub 官方建议招聘方只会短时间浏览项目，应在 README 中提供 concise overview、features、setup、demo 和 tests；当前 Agent/Eval Research Engineer 岗位反复要求 realistic workflows、environments、graders、reliability/variance、offline replay、failure analysis、product impact、end-to-end ownership 和可复现报告。主要不确定性是尚无真实招聘方反馈，因此这些门是候选审查启发式，不是已采用治理或招聘成功保证。

### 30 秒

必须看到：一句用户价值、一个可理解的 V2 screenshot/live surface、一个 before/after 状态变化、一个明确非主张。不能先读架构史或 12-case 表。

### 3 分钟

必须完成：选择一个 claim → 查看证据图/缺口 → 运行可逆 replay → 看状态和摘要 delta → 打开 receipt。必须看见 baseline evidence 未被改写、hypothetical preview 不冒充事实。

### 10 分钟

必须能：无 key 复现 V2 artifact；展示三类 intervention；核对 canonical receipt；查看成熟项目 workflow gap matrix；运行 focused tests/scan；解释 failure taxonomy、评测边界和下一步真实实验。

复审条件：V2 行为改变、目标岗位改变、公开后收到真实 reviewer 反馈，或成熟项目增加等价的 end-user evidence replay flow。

## 6. 唯一 Product V2 冻结

### 目标用户

需要从多来源重建一天、但不能接受“AI 把不确定内容写成事实”的个人用户；第二读者是审核该 Agent 可靠性的工程师/招聘方。

### 端到端流程

1. 打开一个 committed synthetic-safe day；
2. 查看 source health、coverage 和按时间排序的 claims；
3. 选择一个 claim，看到 supporting / contradicting / missing evidence graph；
4. 选择一个固定、可逆 intervention：source dropout、missing-evidence arrival preview、conflict-source quarantine；
5. 系统从相同 frozen contract replay before/after；
6. 显示 claim status delta、summary eligibility delta、仍未解决的 evidence gap；
7. 生成 canonical intervention receipt，明确 baseline 与 hypothetical preview；
8. Evaluation / Review 显示 V1 regression、V2 transition gates 和成熟项目 workflow gap，而不是伪造跨项目性能。

### 核心功能

- Immutable baseline（不可变基线）+ counterfactual replay（反事实回放）；
- claim evidence graph；
- minimal next evidence action；
- summary impact preview；
- deterministic intervention receipt；
- V1 12-case identity regression。

### 辅助功能

- localhost MCP lineage；
- privacy-pattern scan；
- dependency lock、CI configuration；
- reviewer-friendly UI 和 README。

### 明确删除/不扩张

- 不做全面屏幕/音频采集；
- 不做通用 observability/eval backend；
- 不新增 provider、LangGraph、多 agent、RAG、长期记忆或写操作；
- 不用更多 ablation 数量替代成熟项目差距；
- 不把 hypothetical evidence 进入 canonical summary。

## 7. Product V2 evidence gates

1. 三类 replay 均有明确 before/after，且至少覆盖 `Supported→Unknown`、`Unknown→Supported preview`、`Conflict→Unknown`；
2. baseline report bytes 与 V1 aggregate identity 不变；
3. hypothetical pointer 明确标记，不得伪装为 observed evidence；
4. canonical summary 不因 preview 改变；preview summary 单独显示；
5. 每次 intervention 有稳定 receipt identity、contract、changed evidence、remaining gap；
6. 同一输入两次生成 byte-identical V2 artifact；
7. UI 30 秒可理解，3 分钟可完成 replay；
8. 比较页明确区分 executable DayQuest gates 与 document/architecture-level mature-project comparison；
9. V1 185-test baseline 仅在相关接口变化后做最小回归；最终完整矩阵重新闭合；
10. push、remote CI、LICENSE、release、私人数据与最终简历仍不执行。

## 8. Kill criteria

- replay 只是切换预写文案，未从 evidence contract 计算状态；
- hypothetical evidence 被写入 baseline 或事实摘要；
- V2 只能通过增加简单弱基线显示优势；
- 用户必须读 JSON 才能理解 before/after；
- V1 evidence identity、D3/VS1 binding 或 privacy boundary 被改写；
- 为补功能数量引入新 provider/framework；
- Product V2 的差异仍可被“ActivityWatch + 普通 source link”完整描述。

## 9. 本地实现与复现结果

- V2 deterministic replay model、artifact、UI 产品流与 review surface：`Local Technical Complete`；
- 三类 transition gate、规范回执、hypothetical/observed 边界与 V1 identity regression：`Verified`；
- 两份独立本地 clone 在提交 `598028a983539240126233e23edb1f02b359e03b` 上分别两次通过 Product V2 check；raw artifact bytes 与 canonical identity 均为 `81D0431BD4E9E712D7FFFDE6ACF7E3DF28B03C7A93465120249CE360B5D4F5D3`；
- `.gitattributes` 固定 evidence artifact checkout 为 LF，避免 Windows checkout 产生 raw-byte identity 漂移；
- 实际桌面浏览器已核验 30 秒首屏、三种 replay、hypothetical warning、summary delta、receipt 和成熟项目工作流卡片；
- push、remote CI、release、LICENSE、私人数据与最终简历仍未执行。

Exact Resume Point：`Review Product V2 and RESUME_EVIDENCE_CANDIDATE.md; then separately decide license, public repository/push, external CI and final resume wording. Do not claim public evidence before those gates close.`
