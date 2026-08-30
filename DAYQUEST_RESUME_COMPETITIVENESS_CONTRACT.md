# DayQuest Resume-Flagship Competitiveness Contract

Contract ID：`DQ-RESUME-FLAGSHIP-PRODUCTIZATION-20260830-01-R0`

状态：`Proposed Competitiveness Contract / R0 Technical Draft Complete`

本文件把用户已明确接受的差异化主张、非主张和 R0–R4 工作包整理成单一审查面；新增的综合验收门与 kill criteria 属于 `Proposed`，只有最终候选验收时经用户明确接受才成为持续治理。依据是已接受的 DayQuest MVP 证据与 2026-08-30 官方/公开项目对标；主要不确定性是尚无招聘方或真实用户外部反馈。执行成本是本地产品化、评测与复现检查；例外仅限安全或授权边界。复审条件为 R4 技术候选完成、目标岗位改变或任一核心证据失效；未获接受时不约束 R4 之后工作。

## 1. 目标读者与岗位

主要读者：招聘 Agent / LLM Research Engineer、AI Engineer、Agent Evaluation / Reliability Engineer 实习生的工程负责人和面试官。

读者应在 30 秒内回答：

1. DayQuest 解决什么用户问题？
2. 为什么它不是普通的“数据转故事”Demo？
3. 哪些行为已经实现并被测试？
4. 哪些能力仍未验证？
5. 如何在没有 API key 的情况下复现？

## 2. 用户已冻结的差异化主张

> DayQuest is a provenance-first daily timeline reconstructor: it turns bounded local MCP evidence into a human-readable timeline while explicitly preserving Supported, Unknown, and Conflict states, keeping evidence sufficiency separate from policy compliance, and preventing unsupported or conflicted claims from becoming facts in downstream summaries.

中文：DayQuest 是证据优先的日程时间线重建器；它从有界的本地 MCP 证据重建用户一天，并在证据缺失、冲突和工具故障时保守呈现 `Supported / Unknown / Conflict`。每条关键结论可追溯，事实证据与隐私/策略状态分离，摘要不得把 `Unknown` 或 `Conflict` 写成事实。

竞争力必须来自可运行行为、对照评测和复现证据，而不是项目命名、功能数量或宣传语。

## 3. Top-1 用户任务

用户从一个 synthetic-safe（合成安全）日程包开始，通过一个无密钥、本地运行入口获得按时间排序的“我的一天”时间线。普通用户无需阅读 JSON 或代码即可看见：

- 发生了什么；
- 为什么可信、证据来自哪里；
- 哪项必要证据缺失；
- 哪些来源互相冲突；
- 为什么系统拒绝下结论；
- 为什么某条结论虽有证据却因 policy（策略）违规不能进入摘要。

## 4. 成熟项目对照矩阵

| 参照 | 可核验来源 | 借鉴项 | DayQuest 独特项 | 明确不采用 |
|---|---|---|---|---|
| GitHub 求职项目指南 | [GitHub Docs](https://docs.github.com/en/account-and-profile/tutorials/using-your-github-profile-to-enhance-your-resume) | 30 秒可理解；features、setup、demo、tests | 用可运行证据证明项目主张 | 不把 README 包装当完成度 |
| ActivityWatch | [官网](https://activitywatch.net/) / [GitHub](https://github.com/ActivityWatch/activitywatch) | 单句用户价值、本地隐私、时间线 UI | claim-level provenance 与 Unknown/Conflict | 不采集真实、持续的全量用户行为 |
| DailyOS | [GitHub](https://github.com/stadimeti19/DailyOS) | local-first、bounded reads、引用、partial failure 可见 | 冻结三态与 deterministic checker | 不扩成可写邮箱/日历的通用助理 |
| Langfuse | [Tracing](https://langfuse.com/docs/observability/overview) / [Datasets](https://langfuse.com/docs/evaluation/experiments/datasets) | trace drill-down、数据集与实验分层 | 面向一个真实用户任务的证据审核产品 | 不建通用 LLM observability 平台 |
| Arize Phoenix | [GitHub](https://github.com/Arize-ai/phoenix) | tracing、evaluation、可视化调试 | 本地 MCP 时间线中的证据充分性 | 不引入通用 telemetry backend |
| Promptfoo | [Docs](https://www.promptfoo.dev/docs/intro/) | 可重复 CLI、透明测试矩阵、red-team fixture | provenance / policy / summary 三层指标 | 不把产品退化成测试框架 |
| OpenAI Evals | [GitHub](https://github.com/openai/evals) | 版本化 cases、数据与 scorer | human-readable timeline 与三态证据 | 不构建通用模型评测注册表 |
| UK AISI Inspect | [Docs](https://inspect.aisi.org.uk/) | tool-use、multi-turn、scorer、复现 | localhost MCP 真实 acquisition + 审核 UI | 不构建通用 eval runtime |
| LangChain AgentEvals | [Docs](https://docs.langchain.com/langsmith/trajectory-evals) | trajectory / tool-call 比较 | claim 证据与 policy 正交 | 不依赖 vendor-specific agent graph |
| METR Task Standard | [GitHub](https://github.com/METR/task-standard) | 版本化任务、隔离环境、执行/评分边界 | synthetic-safe 日程产品切片 | 不声称严格 sandbox 或生产隔离 |
| MCP Inspector | [GitHub](https://github.com/modelcontextprotocol/inspector) | 一条命令、真实 server、Web/CLI 一致语义 | 面向最终用户的时间线而非协议调试器 | 不复制通用 MCP 调试能力 |

Stars、forks 或宣传语不作为质量证据；只有与 DayQuest 当前消费者直接相关的实现和测试可进入验收。

## 5. 用户已确认的非主张

DayQuest 不声称：

- 学术创新或优于全部成熟项目；
- 通用个人助理或生产可靠性；
- 真实私人邮箱、日历、交易数据已经验证；
- 通用 secret scanning、跨平台路径检测或安全认证；
- 统计泛化、真实用户增长、生产流量、stars 或性能提升；
- LangGraph、多智能体、RAG、长期记忆、云部署是竞争点。

## 6. Proposed 最终验收门

建议只有以下全部可核验，才称为“简历旗舰项目候选”：

1. 产品首屏是普通用户时间线工作流，不是 12-case 测试台；
2. 至少一个完整 synthetic-safe “我的一天”同时展示 Supported、Unknown、Conflict；
3. constrained summary（受约束摘要）只消费 Supported + policy-compliant 事实；
4. 12-case 达到 expected status 12/12、false-supported 0、Unknown/Conflict summary leakage 0、conflict preservation 2/2、tool-failure safe 4/4；
5. 三个冻结对照公开其简单假设并报告不利数字；
6. unit、真实 localhost MCP、artifact identity、comparison benchmark、隐私模式扫描均有本地证据；
7. 一条 no-key 命令可在 fresh directory 复现；
8. README、SECURITY、CI configured 状态、依赖锁和 license 决策材料一致；
9. 10 分钟演示不需解释源代码即可展示用户价值和工程边界；
10. 正式简历、push、release、license 文件和公开发布继续等待单独用户决定。

## 7. Proposed kill criteria

建议出现以下任一情况时停止扩张并返回 `Hold / Compress / Replace`：

- 产品首屏仍以测试案例或 JSON 为主；
- DayQuest 只有文案差异，无法在相同 cases 上表现出可验证的证据优势；
- 对照必须被故意写坏才能让 DayQuest 获胜；
- Unknown / Conflict 或 policy-violating claim 进入事实摘要；
- 复现需要 `.env`、私人数据、网络服务或未声明的本地状态；
- D3、VS1、MVP identity 或 12-case 语义被改写；
- 为增加功能数量而引入 LangGraph、多智能体、RAG、长期记忆或新 provider；
- README / CI / 安全文档把 Configured、Locally Passed 或 Candidate 提升为 externally verified / public-ready。

## 8. 当前技术阶段

- R0｜竞争力合同技术草案：`Complete`
- R1｜真实用户产品流：`Technical Complete / Awaiting Final Candidate Review`
- R2｜透明比较评测：`Not Started`
- R3｜工程与复现：`Not Started`
- R4｜候选验收包：`Not Started`

当前 Resume Point：以 `timeline_app.py` 为唯一 no-key 产品入口，把产品首屏改为“我的一天”时间线，将 12-case matrix 移入独立 Evaluation / Review 区。
