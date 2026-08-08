---
title: SourceOS 开源 Agent 框架选型（已废止）
document_type: superseded-technical-selection
status: superseded
created_at: 2026-08-08 Asia/Shanghai
superseded_at: 2026-08-08 Asia/Shanghai
superseded_by: 2026-08-08-pi-agent-framework-correction-research.md
---

# SourceOS 开源 Agent 框架选型（已废止）

> [!danger] 不得据此实施
> 本文原先提出的 LangGraph / LangChain 主编排方案已经撤销。它把耐久编排能力的权重放得过高，会为 SourceOS 引入不必要的图运行时、检查点语义和依赖体系，不符合本项目“小而可控、智能体自行泛化、业务状态由产品自己拥有”的架构原则。

当前有效决策是：

- Agent 认知执行内核采用 Pi Agent Harness 的 `@earendil-works/pi-agent-core@0.84.1`；
- 不采用 LangGraph、LangChain，也不再引入第二套浏览器 Agent 框架；
- Pi 只负责一次有界运行中的模型回合、工具调用、事件、中止和运行内消息；
- SourceOS 自己拥有 PostgreSQL mission/action 状态机、RQ 调度、浏览器、全量采集、完整性、证据、身份和长期记忆；
- Pi 通过轻量 TypeScript NDJSON adapter 驱动 SourceOS 的 Playwright、浏览器扩展、评论、弹幕与转写工具。

请以以下两份文档为准：

- [Pi Agent 框架修正调研](./2026-08-08-pi-agent-framework-correction-research.md)
- [自治浏览器研究智能体设计](../superpowers/specs/2026-08-08-autonomous-browser-research-agent-design.md)

保留本文件仅用于维持已有链接和明确记录决策已被推翻；它不再是候选方案、比较报告或实施依据。
