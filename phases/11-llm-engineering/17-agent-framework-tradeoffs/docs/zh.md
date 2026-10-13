# Agent Framework Tradeoffs — Graph, Role, and Actor Orchestration · 智能体框架取舍：图、角色与 Actor 编排

> 每个框架卖的都是同一个 demo（研究智能体写报告），藏的也是同一个 bug（状态 schema 与编排层打架）。选那个抽象与你的问题形态相匹配的框架；其余一切都是你要写两遍的胶水代码。
>
> Every framework sells the same demo (research agent builds a report) and hides the same bug (state schema fights with the orchestration layer). Pick the framework whose abstractions match the shape of your problem; everything else is glue you write twice.

**类型：** Learn
**语言：** Python
**先修：** Phase 11 · 09（函数调用）、Phase 11 · 16（LangGraph）
**时间：** 约 45 分钟

## The Problem · 问题在哪

你手上的任务需要不止一次 LLM 调用。也许是一条研究工作流（计划、搜索、总结、引用）。也许是一条代码评审流水线（解析 diff、批评、打补丁、验证）。也许是一个多轮助手，会订机票、写邮件、报销差旅。你选了一个框架。

三天之后，你发现框架的抽象在泄漏。CrewAI 给了你角色，但当「researcher」需要把一份结构化计划交给「writer」时它跟你打架。AutoGen 给了你智能体之间的聊天，却没有一流的状态，于是你的检查点成了一整份对话日志的 pickle。LangGraph 给了你状态图，却逼你在还不知道智能体会做什么之前就给每一条转移命名。Agno 给了你单智能体抽象，可一旦你想扇出（fan out）到三个并发 worker，它就叫唤起来。

解法不是「选出最好的框架」，而是把框架的核心抽象与你问题的形态相匹配。本课画出这张地图。

> You have a task that needs more than one LLM call. Maybe it is a research workflow (plan, search, summarize, cite). Maybe it is a code-review pipeline (parse diff, critique, patch, validate). Maybe it is a multi-turn assistant that books flights, writes emails, and files expense reports. You pick a framework.
> Three days later, you discover the framework's abstractions leak. CrewAI gives you roles but fights you when the "researcher" needs to hand a structured plan to the "writer." AutoGen gives you chat between agents but has no first-class state so your checkpoint is a pickle of a conversation log. LangGraph gives you a state graph but forces you to name every transition before you know what the agent will do. Agno gives you a single-agent abstraction that screams when you try to fan out to three concurrent workers.
> The fix is not "pick the best framework." It is to match the framework's core abstraction to the shape of your problem. This lesson draws that map.

## The Concept · 概念

![智能体框架矩阵：核心抽象对比问题形态](../assets/framework-matrix.svg)

四个框架主导 2026 年的版图。它们的核心抽象并不相同。

| 框架 | 核心抽象 | 最适合 | 最不适合 |
|-----------|------------------|----------|-----------|
| **LangGraph** | `StateGraph` —— 类型化状态、节点、条件边、检查点器。 | 有显式状态与人在环（human-in-the-loop）中断的工作流；需要时间旅行调试的生产智能体。 | 拓扑未知的松散、角色驱动的头脑风暴。 |
| **CrewAI** | `Crew` —— 角色（goal、backstory）、任务、流程（sequential 或 hierarchical）。 | 角色扮演或人设驱动、计划较短且线性/分层的工作流。 | 任何超出 crew 轮次历史的带状态场景；复杂分支。 |
| **AutoGen** | `ConversableAgent` 对 —— 两个或多个智能体轮流说话，直到满足退出条件。 | 多智能体 *对话*（师生、提议者-批评者、演员-评审），思考从聊天中涌现。 | 有已知 DAG 的确定性工作流；任何需要跨重启持久状态的东西。 |
| **Agno** | `Agent` —— 单个 LLM + 工具 + 记忆，可组合成团队。 | 快速构建的单智能体与轻量团队；强多模态与内置存储驱动。 | 带自定义 reducer 的深度显式分支图。 |

> Four frameworks dominate the 2026 landscape. Their core abstractions are not the same.

### What "abstraction" actually means · 「抽象」到底是什么意思

框架的核心抽象，就是你推销架构时在白板上画的那个东西。

- **LangGraph** → 你画一张图。节点是步骤，边是转移，每一点上的状态对象都有类型。心智模型是状态机（state machine）。
- **CrewAI** → 你画一张组织架构图。每个角色有一份职位描述，由一个经理分派任务。心智模型是一个小的专家团队。
- **AutoGen** → 你画一条 Slack 私信。两个智能体互发消息；需要仲裁时第三个加入。心智模型是聊天。
- **Agno** → 你画一个挂着工具的单独方块。把方块并排放就是团队。心智模型是「自带电池的智能体」。

> A framework's core abstraction is the thing you draw on the whiteboard when you pitch the architecture.
> **LangGraph** → you draw a graph. **CrewAI** → you draw an org chart. **AutoGen** → you draw a Slack DM. **Agno** → you draw a single box with tools hanging off it.

### The state question · 状态问题

状态是大多数框架选择在生产中翻车的地方。

- **LangGraph。** 类型化状态（`TypedDict` 或 Pydantic 模型）、每字段 reducer、一流的检查点器（SQLite/Postgres/Redis）。恢复、中断、时间旅行都是免费的。*（见 Phase 11 · 16。）*
- **CrewAI。** 状态经 `context` 字段以字符串形式在任务之间流动，或经 `output_pydantic` 结构化传递。开箱没有持久的 per-crew 存储；如果 crew 必须在重启后存活，你得自己加上。
- **AutoGen。** 状态就是聊天历史和任何用户自定义的 `context`。对话记录可以持久化；任意工作流状态则不然，除非你自己写适配器。
- **Agno。** 内置存储驱动（SQLite、Postgres、Mongo、Redis、DynamoDB），通过 `storage=` 挂到一个 `Agent` 上——会话与用户记忆自动持久化。它不是完整的图检查点器，而是会话存储。

> State is where most framework choices break down in production.
> **LangGraph.** Typed state, per-field reducers, first-class checkpointer. Resume, interrupt, and time-travel are free.
> **CrewAI.** State flows as strings between tasks via the `context` field, or structured through `output_pydantic`. No durable per-crew store out of the box.
> **AutoGen.** State is the chat history and any user-defined `context`. Conversation transcripts persist; arbitrary workflow state does not unless you write adapters.
> **Agno.** Built-in storage drivers attached to an `Agent` via `storage=` — conversation sessions and user memories persist automatically. Not a full graph checkpointer; a session store.

### The branching question · 分支问题

每个不平凡的智能体都有分支。由谁决定分支，关系重大。

- **LangGraph** —— 你决定，通过条件边。路由是一个带命名分支的 Python 函数。分支在编译后的图里是一等公民；检查点器会记录走了哪条分支。
- **CrewAI** —— hierarchical 模式下由经理决定；sequential 模式下你在构建时决定。路由隐含在任务列表里；在经理的提示之外，没有一等公民的「if」。
- **AutoGen** —— 智能体通过聊天决定。分支从「谁下一个说话」中涌现。`GroupChatManager` 选择下一个发言者；你可以手写 `speaker_selection_method`，但默认是 LLM 驱动。
- **Agno** —— 智能体通过选择下一个调用的工具来决定。团队有 coordinator/router/collaborator 模式；超出这些之外的分支是开发者的责任。

> Every non-trivial agent branches. Who decides the branch matters.
> **LangGraph** — you decide, via conditional edges. **CrewAI** — the manager decides in hierarchical mode; in sequential mode you decide at build time. **AutoGen** — the agents decide via chat; `GroupChatManager` selects the next speaker. **Agno** — the agent decides by which tool to call next.

### The observability question · 可观测性问题

- **LangGraph** —— 经 LangSmith 或任意 OTel 导出器的 OpenTelemetry。每个节点转移都是一条 trace span；检查点同时就是可重放的 trace。LangSmith 是第一方选项；Langfuse/Phoenix 也有适配器。
- **CrewAI** —— 自 2025 年末起支持一流的 OpenTelemetry；与 Langfuse、Phoenix、Opik、AgentOps 集成。
- **AutoGen** —— 经 `autogen-core` 的 OpenTelemetry 集成；AgentOps 和 Opik 有连接器。追踪粒度是每条智能体消息，不是每个节点。
- **Agno** —— 内置 `monitoring=True` 开关加 OpenTelemetry 导出器；与 Langfuse 深度集成做会话 trace。

> **LangGraph** — OpenTelemetry via LangSmith or any OTel exporter. Every node transition is a trace span; checkpoints double as replayable traces.
> **CrewAI** — first-class OpenTelemetry since late-2025; integrations with Langfuse, Phoenix, Opik, AgentOps.
> **AutoGen** — OpenTelemetry integration via `autogen-core`; tracing granularity is per-agent-message, not per-node.
> **Agno** — built-in `monitoring=True` flag plus OpenTelemetry exporters; tight integration with Langfuse for session traces.

### Cost and latency · 成本与延迟

四个框架都增加每次调用的开销（框架逻辑、校验、序列化）。开销大致按递增排序：Agno ≈ LangGraph < CrewAI ≈ AutoGen。差异主要由框架额外做多少 LLM 路由决定。CrewAI 的分层经理要花 token 决定下一个谁上；AutoGen 的 `GroupChatManager` 同样如此。LangGraph 只在你写了 `llm.invoke` 的地方花 token。Agno 的单智能体路径很薄。

当每次运行的成本重要时，优先选显式路由（LangGraph 的边、AutoGen 的 `speaker_selection_method`），而不是 LLM 选择的路由。

> All four frameworks add per-call overhead (framework logic, validation, serialization). Rough order of increasing overhead: Agno ≈ LangGraph < CrewAI ≈ AutoGen. The difference is dominated by how much extra LLM routing the framework does.
> When cost per run matters, prefer explicit routing (LangGraph edges, AutoGen `speaker_selection_method`) over LLM-selected routing.

### Interoperability · 互操作性

- **LangGraph** ↔ **LangChain** 的工具、检索器、LLM。一流的 MCP 适配器（工具以 MCP 服务器形式导入）。
- **CrewAI** ↔ 工具继承自 `BaseTool`；LangChain 工具、LlamaIndex 工具、MCP 工具都能适配进来。Crew 之间经 `allow_delegation=True` 互相委托。
- **AutoGen** → `FunctionTool` 包装任意 Python 可调用对象；有 MCP 适配器。智能体到智能体模式与 AG2 生态紧耦合。
- **Agno** → `@tool` 装饰器或 BaseTool 子类；有 MCP 适配器；工具可以跨智能体和团队共享。

> **LangGraph** ↔ **LangChain** tools, retrievers, LLMs. First-class MCP adapter (tools imported as MCP servers).
> **CrewAI** ↔ tools inherit from `BaseTool`; LangChain tools, LlamaIndex tools, and MCP tools all adapt in. Crew-to-crew delegation via `allow_delegation=True`.
> **AutoGen** → `FunctionTool` wraps any Python callable; MCP adapter available. **Agno** → `@tool` decorator or BaseTool subclass; MCP adapter; tools can be shared across agents and teams.

## The Skill · 技能

> 你能用一句话解释：为什么某个框架适合某个智能体问题。
>
> You can explain, in one sentence, why a given framework is right for a given agent problem.

构建前的检查清单：

1. **画出形态。** 这是一张图（类型化状态、命名转移）？一场角色扮演（专业人士交接工作）？一场聊天（智能体聊到完成为止）？还是一个带工具的单智能体？
2. **决定谁来分支。** 开发者决定分支 → LangGraph。经理智能体决定 → CrewAI hierarchical。聊天中涌现 → AutoGen。工具调用决定 → Agno。
3. **检查状态预算。** 需要从检查点恢复吗？时间旅行？运行中途的人类中断？如果需要，LangGraph 是默认；Agno 的会话覆盖会话级状态。
4. **检查成本预算。** LLM 选择的路由每轮多花 token。如果智能体每天要跑几千次，优先显式路由。
5. **给框架开销做预算。** 每个框架都是又一个依赖。如果任务是两次 LLM 调用加一个工具，那就写 30 行纯 Python；没有框架比零个框架更便宜。

在你能画出那张图、那张组织架构图、那场聊天或那个智能体方块之前，拒绝伸手拿框架。拒绝选择那个逼你为了真正需要的东西跟它的状态模型搏斗的框架。

> Draw the shape. Decide who branches. Check the state budget. Check the cost budget. Budget the framework overhead.
> Refuse to reach for a framework before you can draw the graph, the org chart, the chat, or the agent box. Refuse to pick one that forces you to fight its state model for the thing you actually need.

## The Decision Matrix · 决策矩阵

| 问题形态 | 首选框架 | 为什么 |
|---------------|---------------------|-----|
| 带类型化状态、人类审批、长时运行的工作流 DAG | LangGraph | 一流的状态、检查点器、中断、时间旅行。 |
| 角色分明的研究/写作流水线 | CrewAI（sequential）或 LangGraph 子图 | 「一个角色一个任务」在 CrewAI 里表达成本很低；分支变复杂后再用 LangGraph 扩展。 |
| 提议者-批评者或师生对话 | AutoGen | 双智能体聊天是它的原生形态。 |
| 带工具、会话、记忆的单智能体 | Agno | 最薄的配置，内置存储与记忆。 |
| 上千路带 reducer 的并行扇出 | LangGraph + `Send` | 唯一拥有一等并行派发 API 的框架。 |
| 快速原型、不想绑定框架 | 纯 Python + 服务商 SDK | 没有框架就是最快的框架。 |

```figure
l5-framework-fit
```

> Workflow DAG with typed state, human approvals, long-running → LangGraph. Research / writing pipeline with distinct roles → CrewAI (sequential) or LangGraph subgraphs. Proposer-critic or teacher-student dialogue → AutoGen. Single agent with tools, sessions, memory → Agno. Thousands of parallel fanouts with reducers → LangGraph + `Send`. Quick prototype, no framework commitment → Plain Python + provider SDK.

## Exercises · 练习

1. **简单。** 拿同一个任务——「调研 Anthropic 的总部，写一篇 200 词简报，引用来源」——分别在 LangGraph（四个节点：plan、search、write、cite）和 CrewAI（三个角色：researcher、writer、editor）里实现。报告每次运行的 token 成本和代码行数。
2. **中等。** 在 AutoGen（researcher ↔ writer 聊天，editor 经 `GroupChat` 加入）和 Agno（带 `search_tools` 与 `write_tools` 的单个智能体，外加一个会话存储）里构建同一个任务。按 (a) 每次运行成本、(b) 崩溃后恢复的能力、(c) 在写步骤之前注入人类审批的能力，给四个实现排名。
3. **困难。** 写一个决策树脚本 `pick_framework.py`，接收一段简短的问题描述（JSON：`{has_typed_state, has_roles, has_dialogue, has_parallel_fanout, needs_resume}`），返回一个带一句话理由的推荐。在你自己设计的六个案例上验证它。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Orchestration（编排） | “智能体怎么协调” | 决定下一个运行哪个节点/角色/智能体的那一层。 |
| Durable state（持久状态） | “重启后能恢复” | 在进程死亡后存活的状态，挂在检查点或会话存储上。 |
| LLM-selected routing（LLM 选择路由） | “让模型决定” | 一个规划 LLM 每轮挑选下一步；灵活，但每次决策都要付 token。 |
| Explicit routing（显式路由） | “开发者决定” | 一个 Python 函数或静态边挑选下一步；便宜且可审计。 |
| Crew | “一个 CrewAI 团队” | 角色 + 任务 + 流程（sequential 或 hierarchical）绑定成的单个可运行体。 |
| GroupChat | “AutoGen 的多智能体聊天” | N 个智能体之间的受管对话，带发言者选择器。 |
| Team (Agno) | “多智能体的 Agno” | 在一组智能体之上的 route / coordinate / collaborate 模式。 |
| StateGraph | “LangGraph 的图” | 类型化状态、节点、条件边、检查点器的抽象。 |

## Further Reading · 延伸阅读

- [LangGraph documentation](https://langchain-ai.github.io/langgraph/) —— StateGraph、检查点器、中断、时间旅行。
- [CrewAI documentation](https://docs.crewai.com/) —— Crew、Flow、Agent、Task、Process。
- [AutoGen documentation](https://microsoft.github.io/autogen/) —— ConversableAgent、GroupChat、teams、tools。
- [Agno documentation](https://docs.agno.com/) —— Agent、Team、Workflow、存储、记忆。
- [Anthropic — Building effective agents (Dec 2024)](https://www.anthropic.com/research/building-effective-agents) —— 与框架无关的模式库（提示链、路由、并行化、orchestrator-workers、evaluator-optimizer）。
- [Yao et al., "ReAct: Synergizing Reasoning and Acting" (ICLR 2023)](https://arxiv.org/abs/2210.03629) —— 每个框架都在包装的那个循环。
- [Wu et al., "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation" (2023)](https://arxiv.org/abs/2308.08155) —— AutoGen 的设计论文。
- [Park et al., "Generative Agents: Interactive Simulacra of Human Behavior" (UIST 2023)](https://arxiv.org/abs/2304.03442) —— CrewAI 式人设栈所依托的角色扮演基础。
- Phase 11 · 16（LangGraph）—— 本课用来做基准对比的框架。
- Phase 11 · 19（Reflexion）—— 一个能干净映射到 LangGraph、却难以映射到 CrewAI 的模式。
- Phase 11 · 22（Production observability / 生产可观测性）—— 无论选哪个框架，都照这里说的做埋点。
