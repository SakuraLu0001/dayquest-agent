# DayQuest：未来四个月行动路线图

> 放置建议：将本文件保留在 DayQuest GitHub 仓库根目录，文件名保持为 `ROADMAP_4_MONTHS.md`，并在 README 顶部增加链接。这样每次打开仓库都能看到，不会埋在归档文件夹里。

## 总目标

在申请前四个月，把 DayQuest 从“一天内完成的 Hackathon prototype”整理成：

1. 别人 5 分钟内能理解；
2. 10 分钟内能跑起来；
3. 你能脱离 AI 完整解释；
4. 能放入简历、个人主页和套瓷材料；
5. 与你的主线形成一致叙事：Trustworthy NLP + evaluation + practical AI systems。

---

## 第 1 个月：DayQuest v1.0 收尾与工程基础

### 必须完成

- 逐文件阅读代码，能解释 `app.py`、Agent state、Nexla client、Akash client、Pomerium MCP server、story reel。
- 清理临时代码、过时 demo 数据、无关文件和历史敏感信息。
- 补齐 README：问题、架构、Agent Loop、运行方法、示例、测试、限制。
- 增加一张架构图和一次完整运行截图。
- 保证无 API key 的本地 fallback demo 可以运行。
- 保持全部测试通过。
- 创建 GitHub Release：`v0.1-hackathon-submission`，封存比赛当天版本。
- 再创建后续开发版本：`v1.0.0` 目标清单。

### 学习重点

Git、GitHub、HTTP、API、环境变量、pytest、mock、日志、端口与本地服务。

### 完成标准

你能不看提示回答：

- Observation 如何改变下一轮 Action？
- 为什么 Nexla 16 条 sample 最终使用 8 条？
- Akash 实际负责什么？
- Pomerium 的 HTTP 401 证明了什么，又没有证明什么？
- 哪些测试是 mock，哪些是真实联网验证？
- 系统当前最主要的限制是什么？

---

## 第 2 个月：研究方向工程项目

建议只做一个与研究经历强相关的项目：

## AIGT Detector Robustness Evaluation Studio

最小垂直切片：

输入一组 human / AI-generated text<br>
→ 统一数据格式<br>
→ 调用或运行 1–2 个 detector<br>
→ 计算 detector-side metrics<br>
→ 对比 baseline 与一种扰动或攻击<br>
→ 输出可复现报告

### 第一版禁止加入

- 多 Agent；
- 用户登录；
- 数据库；
- 复杂云部署；
- 十几个 detector；
- 与评估无关的复杂前端。

### 完成标准

仓库包含：

- 可复现实验配置；
- 数据处理脚本；
- detector 评估；
- 指标表；
- README；
- 示例输出；
- 测试；
- 明确的个人贡献说明。

---

## 第 3 个月：公开化与质量提升

- 邀请 2–3 位同学运行 DayQuest 或评估工具。
- 记录真实使用问题，转化为 GitHub Issues。
- 修复高优先级问题。
- 增加 examples、错误提示和最小部署方式。
- 写一篇中英文技术复盘：
  - 为什么这不是固定 pipeline；
  - 如何处理 schema、duplicate、privacy 和 fallback；
  - AI 辅助编码中哪些判断必须由人完成。
- 整理 GitHub Profile README，让项目主线清晰。

### 完成标准

至少有：

- 1 个稳定 Release；
- 1 篇技术复盘；
- 2 个可公开展示的完整仓库；
- 1 个简短项目演示页面或视频；
- 你能现场解释主要设计取舍。

---

## 第 4 个月：申请材料转化

- 更新一页简历。
- 为 DayQuest 和研究评估项目各准备：
  - 30 秒介绍；
  - 1 分钟介绍；
  - 3 分钟技术讲解；
  - 常见问答。
- 将相关项目写入个人主页。
- 只在方向相关的导师邮件中加入 GitHub 链接。
- 准备 SoP 中关于“从评估研究到可信 AI 系统”的连接段落。
- 检查所有公开表述，确保不夸大功能、奖项或研究贡献。

---

## 每周固定节奏

每周只安排一个主要工程目标：

- 周一：明确本周唯一目标和验收标准。
- 周二至周四：实现、测试、查看 diff。
- 周五：人工验证、README 更新、Commit、Push。
- 周末：用 30 分钟复盘：
  - 我独立理解了什么？
  - AI 完成了什么？
  - 哪些部分我仍无法解释？
  - 下周最小改进是什么？

## AI 编程使用规则

固定工作流：

目标<br>
→ 限定允许修改的文件<br>
→ AI 先读代码并给短计划<br>
→ 最小修改<br>
→ 运行测试<br>
→ 查看 `git diff`<br>
→ 人工验证<br>
→ 让 AI 解释关键代码<br>
→ Commit

每次完成后必须能回答：

1. 修改了哪些文件？
2. 为什么这样改？
3. 输入输出是什么？
4. 失败如何 fallback？
5. 安全风险是什么？
6. 测试覆盖了什么？
7. 哪些结论是实际验证，哪些只是 mock？

## 四个月内不要做的事

- 同时启动 4–5 个项目；
- 为了 GitHub 绿色格子提交无意义内容；
- 继续堆 Sponsor 或框架；
- 在不了解代码时大规模重构；
- 把 AI 生成结果直接当成自己的理解；
- 声称未完成的功能或奖项。
