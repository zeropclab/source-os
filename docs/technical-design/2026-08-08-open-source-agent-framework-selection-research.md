---
title: SourceOS 自治浏览器研究 Agent 开源框架选型调研
document_type: technical-research
status: proposed
version: v0.1
created: 2026-08-08
product: SourceOS
research_scope: agent-orchestration-framework
---

# SourceOS 自治浏览器研究 Agent 开源框架选型调研

## 0. 结论先行

SourceOS 应选择 **LangGraph 开源内核**作为自治研究 Agent 的主编排框架，并保持以下分层：

```text
SourceOS 业务控制面
  ├─ 任务、来源清单、证据、完整性、身份、监控、成本与长期记忆
  ├─ LangGraph OSS：规划 / 执行 / 评估 / 恢复 / 重规划的运行状态机
  ├─ Playwright + 浏览器扩展：确定性浏览器执行主通道
  ├─ Browser Use OSS：未知站点的探索式浏览器执行器（可插拔工具）
  └─ RQ / APScheduler / FFmpeg / ASR Worker：长任务、重任务与定时任务
```

关键决策不是“所有 Agent 能力都交给 LangGraph”，而是：

> LangGraph 只拥有 Agent 运行游标和短期编排状态；SourceOS 继续拥有业务事实、证据事实和执行工具。

选择 LangGraph 的主要原因：

1. 它明确定位为低层、长时间、有状态 Agent 编排框架，适合 SourceOS 这种“确定性流程与自主决策混合”的系统，而不是要求产品迁就框架预设的 Agent/Crew/Memory 模型。[LangGraph 官方概览](https://docs.langchain.com/oss/python/langgraph/overview)
2. 开源内核自带逐步 checkpoint、故障恢复、replay、pending writes 和生产可用的异步 PostgreSQL checkpointer；这与 SourceOS 已有 Python、FastAPI、PostgreSQL 技术栈直接吻合。[LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
3. 子图天然适合把“规划、来源发现、站点探索、质量复核、报告生成”做成边界清晰的子 Agent，并继承持久化与中断恢复能力。[LangGraph subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)
4. MIT 许可、仍在高频发布；截至本调研时点，官方仓库最新发布记录为 2026-08-07。[LangGraph LICENSE](https://github.com/langchain-ai/langgraph/blob/main/LICENSE)、[LangGraph releases](https://github.com/langchain-ai/langgraph/releases)

**不采用 LangGraph Agent Server / LangSmith 作为 SourceOS 的运行事实源。** 开源 `langgraph`、`langgraph-checkpoint-postgres` 足够支撑首版；SourceOS 应继续使用自己的 FastAPI、PostgreSQL、RQ、APScheduler 和可观测链路，避免把部署、任务队列、业务状态与追踪绑定到商业平台。

## 1. 调研范围与判定标准

### 1.1 一手资料范围

本报告只使用项目官方文档、官方 GitHub 仓库、官方许可证和官方发布记录。调研快照时间为 **2026-08-08**。

最低比较对象：

- LangGraph
- PydanticAI
- Microsoft AutoGen
- CrewAI
- Hugging Face smolagents
- Browser Use
- Letta

另加入 **Microsoft Agent Framework（MAF）**。原因是 AutoGen 官方已经把它标记为继任者；如果只评价 AutoGen 而忽略官方迁移方向，结论会失真。[AutoGen 官方仓库](https://github.com/microsoft/autogen)

### 1.2 SourceOS 的必要条件

框架必须适应以下约束，而不是反过来改写产品：

- Python / FastAPI 主栈；
- PostgreSQL 为业务事实源；
- 任务可运行数小时、数天并能断点恢复；
- Agent 决策与确定性采集、下载、转写、对账混合；
- 浏览器是关键执行环境，但浏览器执行器可替换；
- 模型供应商可替换；
- 单 Agent 可以起步，多 Agent 可以渐进引入；
- 原始评论、弹幕、媒体和逐字稿不能塞入 Agent checkpoint；
- Agent 框架退出后，SourceOS 的任务、证据和能力数据仍然完整可用。

### 1.3 评价符号

- `◎`：原生能力强，且与 SourceOS 直接匹配；
- `○`：可用，但需要适配或额外组件；
- `△`：能力有限、定位不同或引入明显代价；
- `×`：不满足核心条件。

## 2. 对比总表

| 框架 | 开源与维护状态 | Python / FastAPI | 长任务 checkpoint / resume | 工具与模型中立性 | 浏览器 | 多 Agent | 可观测性 | 运维负担 | SourceOS 结论 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| **LangGraph** | MIT；活跃 | ◎ | **◎：内建，PostgreSQL** | ◎：编排不绑定模型，工具可做节点/任务 | ○：无内置浏览器，易接 Playwright/Browser Use | ◎：子图、路由、并行 | ○：状态历史与流原生；高级 UI 多依赖 LangSmith | ○ | **主编排框架** |
| **PydanticAI** | MIT；活跃 | **◎** | ○：依赖 Temporal/DBOS/Prefect/Restate | **◎：类型安全、广泛 provider、MCP** | △：通过自定义工具 | ○：委派、handoff、graph | **◎：OpenTelemetry 原生** | △：要再引入耐久运行时 | 类型安全 Agent 很强；不作为首版主编排 |
| **Microsoft Agent Framework** | MIT；活跃；AutoGen 继任者 | ◎ | ○：本地 file / Azure Cosmos；分布式耐久需 Durable 扩展 | ◎：多 provider、工具、MCP | △：通过工具/MCP | **◎：多种内置编排** | ◎：OpenTelemetry | △：Azure/Cosmos/Durable 扩展增加体系 | 重点观察的第二候选，不是当前首选 |
| **CrewAI** | MIT；活跃 | ○ | ○：内建 event checkpoint，但自带 provider 为 JSON/SQLite | ◎：工具、MCP、多模型 | △：通过工具 | **◎：Crew/Flow 是核心** | ○：事件、AMP 与多种外部集成 | ○～△ | 高层抽象与 SourceOS 自有控制面重叠 |
| **AutoGen** | **CC BY 4.0；维护模式** | ○ | △：可序列化 save/load，不是逐步耐久工作流 | ○：工具、扩展模型客户端 | △：官方有 Playwright MCP 示例 | ◎ | ○ | △ | **新项目排除**，官方要求转向 MAF |
| **smolagents** | Apache-2.0；活跃但 API 官方标注 experimental | ◎ | **×：运行内存可回放，不是跨进程 checkpoint** | ◎：JSON/tool-code、LiteLLM/HF/自定义模型 | △：有示例但非浏览器运行时 | ○：managed agents | △：logger/callback 为主 | ◎：很轻 | 适合原型/局部工具 Agent，不适合主控制面 |
| **Browser Use OSS** | MIT；活跃 | ◎ | △：浏览器 profile 可持久化，任务流程无业务级 checkpoint | ◎：自定义 action、多 provider | **◎：核心能力** | △ | ○：Laminar / cloud sync | ○ | **浏览器探索执行器，不是 Agent 总框架** |
| **Letta** | Apache-2.0；活跃开发已迁到 Letta Code | **△：新 Agent SDK 以 TypeScript 为主；Python V1 为旧代** | ○：Agent 身份与长期记忆强；不是显式工作流 step checkpoint | ◎：多模型、工具、MCP | △：computer/tool 层 | ○：subagents | ○ | **△～×：需额外 App Server，且复制 SourceOS 记忆层** | 不作为核心；其记忆思想可借鉴 |

## 3. 逐项分析

### 3.1 LangGraph：最适合做 SourceOS 的低层自治编排内核

#### 官方事实

- LangGraph 将自己定义为面向长时间、有状态 Agent 的低层编排框架；它可以脱离 LangChain 使用。[官方概览](https://docs.langchain.com/oss/python/langgraph/overview)
- 编译图时接入 checkpointer 后，每个执行 step 都保存状态；官方列出的用途包括故障恢复、memory、time travel 和 replay。失败 superstep 中其他已成功节点的 pending writes 也会保存，恢复时无需重跑。[Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- 官方提供 `AsyncPostgresSaver`，并明确把 PostgreSQL checkpointer 标记为生产用途；异步调用可使用异步 saver。[Checkpointer libraries](https://docs.langchain.com/oss/python/langgraph/persistence#checkpointer-libraries)
- Functional API 的 task 结果进入 checkpoint，恢复时可跳过已经完成的任务。[Functional API](https://docs.langchain.com/oss/python/langgraph/functional-api)
- 子图可做多 Agent、复用流程和团队边界；子图可以继承父图的 checkpointer，支持持久化、中断和恢复。[Subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)
- 开源内核使用 MIT 许可。[LICENSE](https://github.com/langchain-ai/langgraph/blob/main/LICENSE)

#### 与 SourceOS 的匹配

SourceOS 的任务天然可表达为图：

```text
define_mission
  -> plan_sources
  -> dispatch_acquisition
  -> wait_or_poll_results
  -> assess_completeness
      -> recover_target
      -> expand_sources
      -> transcribe_media
  -> synthesize
  -> decide_monitoring
```

LangGraph 不强迫 SourceOS 使用特定“角色 Agent”或消息群聊模型。普通 Python 函数、模型调用、数据库读取和 RQ job dispatch 都能成为节点，适合将“模型自主判断”和“确定性完整性验证”放在同一张明确状态图中。

#### 代价与风险

- LangGraph 是编排内核，不是完整 Agent 产品。模型适配、工具目录、浏览器、身份、计划策略、业务 API 和 UI 仍需 SourceOS 实现。
- 节点在恢复时可能从节点开头重跑，官方要求副作用幂等；浏览器点击、创建账号、写入证据、派发 Worker 都必须有幂等键或执行前检查。[Durable execution：determinism and idempotency](https://docs.langchain.com/oss/python/langgraph/durable-execution)
- checkpoint 会持续增长，官方建议配置保留与清理策略。[Persistence troubleshooting](https://langchain-ai.github.io/langgraph/concepts/time-travel/)
- LangGraph 恢复旧 thread 时使用当前代码图，而不是把运行锁定到启动时的代码版本；SourceOS 必须在 state 中保存 `graph_schema_version`，对未完成任务做向前迁移或固定兼容期。[Backward compatibility](https://docs.langchain.com/oss/python/langgraph/backward-compatibility)
- LangSmith 是官方推荐的深度追踪产品，但不是 SourceOS 必选依赖。SourceOS 应把 LangGraph event 映射到自己的 OpenTelemetry 与 activity 记录。

#### 判定

**采用 `langgraph` + `langgraph-checkpoint-postgres`，不采用托管 Agent Server 作为核心依赖。**

### 3.2 PydanticAI：FastAPI 体验最佳，但耐久性需要第二套运行时

#### 官方事实

- PydanticAI 是 Python、类型安全、model-agnostic 的 Agent 框架，官方明确以“FastAPI feeling”为设计目标，并支持工具、MCP、图和 OpenTelemetry。[PydanticAI overview](https://pydantic.dev/docs/ai/overview/)
- 官方 provider 抽象覆盖 OpenAI、Anthropic、Gemini、Bedrock、Hugging Face、Ollama、LiteLLM 等，并允许自定义 model。[Models overview](https://pydantic.dev/docs/ai/models/overview/)
- 多 Agent 支持委派、程序化 handoff、图控制流和 deep-agent 模式。[Multi-Agent Patterns](https://pydantic.dev/docs/ai/guides/multi-agent-applications/)
- PydanticAI 的 instrumentation 基于 OpenTelemetry，可以接任意兼容后端，而不是必须使用 Logfire。[PydanticAI observability](https://pydantic.dev/docs/ai/integrations/logfire/)
- 耐久运行由 Temporal、DBOS、Prefect、Restate 四种集成提供，而不是 PydanticAI 单独完成。[Durable Execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/)
- 新的并行 graph builder 官方明确写明“没有原生持久化”，需要接上述 durable solution。[Graph builder persistence](https://pydantic.dev/docs/ai/graph/builder/#persistence-and-resumability)
- MIT 许可。[LICENSE](https://github.com/pydantic/pydantic-ai/blob/main/LICENSE)

#### SourceOS 判定

PydanticAI 在结构化输出、工具参数校验、依赖注入、provider 中立性和 OTel 上非常优秀。但 SourceOS 选择它作为主编排后，还必须选择 DBOS、Temporal、Prefect 或 Restate，等于同时替换/重叠现有的 RQ、APScheduler 和运行状态体系。

首版不建议同时引入 LangGraph 与 PydanticAI 两套 Agent loop。可以继续直接使用 Pydantic 模型定义所有 SourceOS state/tool schema；如果后续发现模型调用层需要更强的类型化工具和多 provider 封装，再把 PydanticAI Agent 作为某个 LangGraph 节点内的局部执行器进行独立验证。

### 3.3 Microsoft AutoGen：能力仍可用，但官方已终止新增功能

#### 官方事实

- AutoGen 官方仓库已标明 **Maintenance Mode**：不再接收新功能和增强，由社区维护；新用户应使用 Microsoft Agent Framework，现有用户应迁移。[AutoGen README](https://github.com/microsoft/autogen)
- AgentChat 支持保存和加载 agent、team 与 termination condition 的 JSON 可序列化状态，适用于应用端自行写入文件或数据库。[Managing State](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/state.html)
- 官方包含多 Agent、模型客户端、工具/MCP 和 Playwright MCP 示例，但状态保存仍由应用显式取出并落库，不等同于带 pending-write/step replay 的耐久工作流。[AutoGen state](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/state.html)
- 当前仓库许可为 CC BY 4.0，而非通常用于代码库的 MIT/Apache-2.0。[LICENSE](https://github.com/microsoft/autogen/blob/main/LICENSE)

#### SourceOS 判定

无论技术能力是否足够，官方维护状态已经使它不适合作为 2026 年新系统的基础依赖。选用 AutoGen 会立即背负一次迁移。

### 3.4 Microsoft Agent Framework：有竞争力，但当前更适合列入观察清单

#### 官方事实

- MAF 是 AutoGen 官方继任者，支持 Python 与 .NET、多个模型 provider、工具/MCP、图工作流、多 Agent 模式和 OpenTelemetry。[MAF README](https://github.com/microsoft/agent-framework)
- 标准工作流支持 superstep checkpoint 与恢复；Python 内置存储包括内存、文件和 Azure Cosmos DB。[MAF checkpoints](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints)
- Durable Extension 能让 agent、multi-agent orchestration 和 workflow 跨 worker 恢复，可自托管或运行于 Azure Functions，但会引入 Durable Task 基础设施。[Durable Extension](https://learn.microsoft.com/en-us/agent-framework/integrations/durable-extension)
- MIT 许可。[LICENSE](https://github.com/microsoft/agent-framework/blob/main/LICENSE)

#### SourceOS 判定

MAF 的功能面已经接近 LangGraph，且内置 OTel 和多 Agent 模式更完整。但当前 Python 生产 checkpoint 的官方直接选项偏向 Cosmos DB，真正分布式耐久执行还要引入 Durable Extension；与 SourceOS 已有 PostgreSQL + RQ 的契合度不如 LangGraph。其 1.0 后发展速度很快，应每 6 个月复核一次，尤其关注 PostgreSQL checkpoint、自托管 Python runtime 和版本兼容政策。

### 3.5 CrewAI：高层协作体验好，但会复制 SourceOS 控制面

#### 官方事实

- CrewAI 提供 Crew 与 Flow 两层：Crew 偏自主协作，Flow 偏显式、事件驱动的状态与控制流。[Flows](https://docs.crewai.com/v1.15.13/en/concepts/flows)
- 当前版本已有原生 checkpoint：默认在 `task_completed` 事件保存，恢复时跳过已完成任务；官方内置 `JsonProvider` 与 `SqliteProvider`，自动 checkpoint 写入为 best-effort。[Checkpointing](https://docs.crewai.com/v1.15.13/en/concepts/checkpointing)
- 具备工具、MCP、规划、memory、事件 listener、模型适配和多种 observability 集成。[CrewAI documentation index](https://docs.crewai.com/llms.txt)
- MIT 许可且持续发布。[LICENSE](https://github.com/crewAIInc/crewAI/blob/main/LICENSE)、[Releases](https://github.com/crewAIInc/crewAI/releases)

#### SourceOS 判定

CrewAI 已不再是“没有 checkpoint 的演示框架”，但它同时提供自己的 Agent、Task、Crew、Flow、Memory、Knowledge、Planning 和 production architecture。SourceOS 已经明确要拥有任务定义、证据记忆、能力库和监控状态；把这些再投射到 CrewAI 会产生双模型和排障复杂度。它更适合以“Agent 团队”为产品中心的系统，而 SourceOS 的中心是“可恢复研究任务与全量证据”。

### 3.6 smolagents：极轻且开放，但没有生产级耐久控制面

#### 官方事实

- smolagents 提供 `CodeAgent` 与 `ToolCallingAgent`，工具可为 Python tool，也可来自 MCP；通过自定义 `Model`、Hugging Face providers 或 LiteLLM 连接多种模型。[Agents](https://huggingface.co/docs/smolagents/reference/agents)、[Models](https://huggingface.co/docs/smolagents/reference/models)
- `managed_agents` 支持管理者调用子 Agent。[Multi-agent example](https://huggingface.co/docs/smolagents/en/examples/multiagents)
- `AgentMemory` 保存当前 run 的 step 并支持 replay，但官方文档没有提供跨进程、逐步 checkpoint 与恢复语义；API 页面还明确标注 experimental、可能随时变化。[Agents reference](https://huggingface.co/docs/smolagents/main/reference/agents)
- Apache-2.0 许可。[LICENSE](https://github.com/huggingface/smolagents/blob/main/LICENSE)

#### SourceOS 判定

适合做快速研究原型、局部代码 Agent 或评测不同模型的薄层，不适合作为数天任务、账号会话、全量评论和媒体处理的主控制面。若使用，只应位于 LangGraph 某个无副作用或可重复的局部节点内。

### 3.7 Browser Use：应作为浏览器执行库，而非主 Agent 框架

#### 官方事实

- Browser Use OSS 是 Python 浏览器 Agent 库，能执行导航、点击、输入、滚动、截图、提取和 JavaScript evaluate。[Available tools](https://docs.browser-use.com/open-source/customize/tools/available)
- 可以通过装饰器加入自定义 Python action，并直接访问 `BrowserSession`、CDP client 与文件系统；官方还给出与 Playwright 精确自动化混用的方式。[Add tools](https://docs.browser-use.com/open-source/customize/tools/add)
- 支持真实 Chrome profile、storage state、Cookie 与 TOTP 等认证方式。[Authentication](https://docs.browser-use.com/open-source/customize/browser/authentication)
- 支持多种模型 provider。[Supported models](https://docs.browser-use.com/open-source/supported-models)
- OSS 可通过 Laminar 捕获 Agent step、成本和浏览器录像；也可同步到 Browser Use Cloud。[Observability](https://docs.browser-use.com/open-source/development/monitoring/observability)
- MIT 许可。[LICENSE](https://github.com/browser-use/browser-use/blob/main/LICENSE)

#### SourceOS 判定

Browser Use 解决的是“让模型在网页上完成操作”，不是“让研究任务跨天恢复、调度媒体 Worker、验证评论完整性并维护证据事实”。它最适合成为以下接口的一个实现：

```python
class ExploratoryBrowserExecutor(Protocol):
    async def accomplish(self, goal, browser_profile, constraints) -> BrowserTrajectory: ...
```

SourceOS 应先调用已验证的站点能力和 Playwright/扩展确定性动作；未知站点或能力漂移时，再把局部目标交给 Browser Use。成功轨迹随后由 SourceOS 能力注册中心固化，而不是永远让 Browser Use 每次重新探索。

### 3.8 Letta：记忆理念强，但当前运行形态与 SourceOS 不匹配

#### 官方事实

- Letta 的核心概念是持久 Agent 身份：长期 memory、工具、模型配置与多个 conversation 共同属于一个 Agent。[Stateful agents](https://docs.letta.com/concepts/stateful-agents/)
- 支持完全本地或自托管 App Server；本地状态可以留在设备上。[Self-hosting](https://docs.letta.com/self-hosting/)
- 官方旧 `letta` 仓库已明确说明是 legacy V1 server，活跃开发迁移到 `letta-code`；新 Agent SDK 以 TypeScript 为主，Python V1 SDK 被标记为 previous-generation。[Letta repository README](https://github.com/letta-ai/letta)
- 当前 Letta Code 使用 Apache-2.0 许可。[Letta Code LICENSE](https://github.com/letta-ai/letta-code/blob/main/LICENSE)

#### SourceOS 判定

Letta 很适合研究“Agent 如何持续记忆和自我改善”，但把它作为 SourceOS 内核会引入 Node/App Server，并产生第二份 Agent memory、tool registry、conversation 和 identity 状态。它没有替代 SourceOS 对全量采集、完整性账本、媒体 Worker 和显式任务图的需求。建议借鉴 MemFS/持续身份思想，不采用其服务器作为系统事实源。

## 4. 推荐架构

### 4.1 框架边界

| 能力 | 归属 | 原因 |
|---|---|---|
| 任务目标、范围、来源对象、清单导入导出 | **SourceOS** | 是产品业务契约，不能成为框架私有 state |
| 评论、弹幕、视频、逐字稿、证据关系 | **SourceOS PostgreSQL + 文件库** | 数据体量大，必须可查询、可迁移、可脱离 Agent |
| 完整性账本与完成门槛 | **SourceOS** | 必须确定性验证，不能由 LLM/框架判定 |
| 账号、邮箱、凭据引用、浏览器 profile | **SourceOS** | 跨任务长期资源 |
| 站点能力注册、成功轨迹、版本与漂移 | **SourceOS** | 是可测试的执行资产 |
| `define → plan → acquire → assess → recover → synthesize` | **LangGraph** | 是长时间 Agent 编排游标 |
| 当前 plan、待执行节点、局部失败与重规划上下文 | **LangGraph checkpoint** | 适合 step 级恢复 |
| 站点确定性操作 | **Playwright + 浏览器扩展 + SourceOS adapter** | 稳定、可测、低成本 |
| 未知站点探索 | **Browser Use，可替换** | 视觉/语义探索专长，不接管全局任务 |
| 评论/弹幕/媒体/转写长任务 | **RQ Worker** | 已有队列，适合外部副作用和资源隔离 |
| 周期监控 | **APScheduler + SourceOS monitor state** | 不依赖 Agent thread 常驻 |
| 模型 provider 路由 | **SourceOS ModelGateway** | 避免 LangChain、PydanticAI 或单一厂商成为业务接口 |
| 运行追踪 | **SourceOS activity + OpenTelemetry** | 人类与机器共同可见，可替换后端 |

### 4.2 LangGraph state 最小化

建议 checkpoint 只保存 ID、摘要与游标：

```python
class MissionGraphState(TypedDict):
    mission_id: UUID
    graph_schema_version: int
    plan_revision: int
    active_target_ids: list[UUID]
    pending_job_ids: list[UUID]
    evidence_gap_ids: list[UUID]
    last_assessment_summary: str | None
    retry_budget_by_target: dict[str, int]
    next_decision: str | None
```

不要保存：

- 全量评论或弹幕数组；
- 网页完整 HTML / 网络响应；
- 视频、音频或字幕正文；
- 完整逐字稿；
- Cookie、密码或完整凭据；
- 能从 SourceOS 事务表重新查询的业务对象快照。

`thread_id` 使用稳定的 `mission_id`，每个子图使用独立 namespace。所有节点开始时从 SourceOS repository 读取当前业务状态，结束时只写业务事务和轻量 graph delta。

### 4.3 副作用和恢复契约

每个会产生外部动作的工具都必须接受：

```text
mission_id
target_id
operation_type
idempotency_key
attempt_id
```

规则：

1. LangGraph node 只负责决定和派发，不在一个不可恢复节点里完成数小时采集或转写。
2. RQ job 在 SourceOS 表中先创建唯一 operation；重复派发返回原 job，而不是重复下载或重复注册账号。
3. 浏览器动作需要定义前置状态、后置状态和验证函数；恢复时先观察后置状态，再决定是否重放。
4. checkpoint 不能代替业务事务；checkpoint 写失败与业务写成功之间必须可通过 reconciliation node 修复。
5. graph 发布新版本时，对仍未完成任务运行 state migration 或保留旧图执行器，不让旧 checkpoint 直接进入不兼容节点。

### 4.4 模型与工具接口

LangGraph 本身保持低层。SourceOS 应定义稳定协议：

```python
class ModelGateway(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse: ...

class AgentTool(Protocol):
    name: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    async def execute(self, context: ToolContext, input: BaseModel) -> BaseModel: ...
```

模型客户端、PydanticAI、MCP 或某个站点 adapter 都只能是协议实现。LangGraph node 依赖 SourceOS 协议，不直接依赖供应商 SDK 对象。

## 5. 建议的首轮技术验证

在正式扩展框架前，做一个只覆盖真实纵向链路的 spike：

1. 使用 `StateGraph` 建立 `plan → acquire → assess → recover → finish` 五节点图；
2. 接 `AsyncPostgresSaver`，以真实 `mission_id` 为 `thread_id`；
3. `acquire` 只派发一个 RQ 评论 job 和一个完整视频转写 job；
4. 在任意节点杀死 API/worker，再启动并验证 graph 与业务 job 均能继续；
5. 故意让浏览器工具完成动作后、checkpoint 写入前崩溃，验证幂等与后置状态检查；
6. 让 Browser Use 仅处理一个未知页面的局部探索目标，验证其轨迹能被 SourceOS 保存；
7. 升级一次 graph schema，验证旧任务迁移；
8. 把 LangGraph event、RQ job 和浏览器轨迹统一关联到一个 `mission_id` 的 OTel trace/activity timeline。

### 5.1 通过条件

- API、Agent worker、RQ worker 任意重启后任务可恢复；
- 已完成的下载、注册或采集不会重复产生副作用；
- checkpoint 删除后，SourceOS 业务数据和证据仍完整；
- 更换模型 provider 不改图结构与工具协议；
- 禁用 Browser Use 后，已适配站点仍能正常采集；
- LangSmith、Browser Use Cloud、Logfire 均不是运行必需项；
- graph state 保持轻量，不随评论/转写规模线性膨胀。

## 6. 最终决策与保留项

### 6.1 采用

- `langgraph`：Agent 状态机与编排；
- `langgraph-checkpoint-postgres`：持久 checkpoint；
- Playwright + 自有浏览器扩展：确定性浏览器执行；
- Browser Use OSS：未知站点探索式执行器；
- Pydantic：所有业务、工具与 graph state schema；
- SourceOS 现有 FastAPI、PostgreSQL、RQ、APScheduler、FFmpeg/ASR 运行面。

### 6.2 暂不采用

- LangGraph Agent Server / LangSmith 作为运行依赖；
- PydanticAI 作为第二套主 Agent loop；
- CrewAI 的 Crew/Flow 作为业务控制面；
- AutoGen；
- smolagents 作为耐久任务运行时；
- Letta App Server 作为记忆或身份事实源；
- Browser Use Cloud 作为首版必需基础设施。

### 6.3 保留的复核点

- PydanticAI + DBOS 是否能在未来合并 Agent、队列与调度，显著降低 SourceOS 运维；
- Microsoft Agent Framework 是否增加 PostgreSQL checkpoint 与更轻的自托管 Python durable runtime；
- Browser Use OSS 是否提供稳定的任务级 checkpoint/trajectory replay，足以承担更多浏览器子图；
- LangGraph 核心接口、checkpoint 格式和版本兼容政策是否仍满足未完成长任务迁移。

**最终建议：以 LangGraph OSS 为“自治编排内核”，而不是以任何框架为“产品内核”。产品内核始终是 SourceOS 自己拥有的任务、来源、证据、能力和长期记忆。**
