# The Multi-Agent Primitive Model · 多智能体原语模型

> Four primitives, nothing more — the agent, the handoff, the shared state, the orchestrator — span a four-dimensional design space, and the major multi-agent frameworks shipping in 2026 (AutoGen, LangGraph, CrewAI, OpenAI Agents SDK, Microsoft Agent Framework) are points in it. This lesson builds them from zero, runs a toy system on all four, then maps every major framework onto the same axes so you can read any new release in one paragraph.

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 (Agent Engineering), Phase 16 · 01 (Why Multi-Agent)
**Time:** ~60 minutes

## Problem · 问题

每半年就有一个新的多智能体框架发布。AutoGen 在 2023 年。CrewAI 在 2024 年。LangGraph 和 OpenAI Swarm 在 2024 年。Google ADK 在 2025 年 4 月。Microsoft Agent Framework RC 在 2026 年 2 月。每一份新闻稿都宣称自己才是「正确的抽象」。

如果你试图一个一个学，你会把自己烧干。API 长得不一样。文档对「什么是一个 agent」各执一词。一个框架把共享内存叫做「blackboard」，另一个叫「message pool」，第三个叫「StateGraph」。你开始怀疑这个领域只是在空转。

它没有。营销之下，四个原语（primitive）是稳定的。学一次，就能用一段话读懂每一个新框架。

> Every six months a new multi-agent framework ships. AutoGen in 2023. CrewAI in 2024. LangGraph and OpenAI Swarm in 2024. Google ADK in April 2025. Microsoft Agent Framework RC in February 2026. Each press release claims to be "the right abstraction."
> If you try to learn them one at a time you will burn out. The APIs look different. The docs disagree about what an "agent" is. One framework calls its shared memory a "blackboard," another calls it a "message pool," a third calls it a "StateGraph." You start suspecting the field is just churning.
> It is not. Underneath the marketing, the four primitives are stable. Learn them once, read every new framework in one paragraph.

## Concept · 概念

### The four primitives · 四个原语

1. **Agent（智能体）** —— 一份系统提示词加一个工具列表。无状态；每次运行都从它的系统提示词和当前消息历史出发。
2. **Handoff（交接）** —— 控制权从一个智能体到另一个的结构化转移。机械地看，就是一次返回新 agent 的工具调用，或者一条按条件走下去的图边。
3. **共享状态（Shared state）** —— 任何能被多于一个智能体读（有时写）的数据结构。消息池、blackboard、键值存储、向量记忆。
4. **Orchestrator（编排器）** —— 决定下一个由谁说话的人。选项：显式图（确定性）、LLM 说话者选择器（软性）、上一个说话者的 handoff 调用（OpenAI Swarm）、或队列之上的调度器（swarm 架构）。

这就是全部设计空间。每个框架在每根轴上挑一组默认值；剩下的都是表层语法。

> 1. **Agent** — a system prompt plus a tool list. Stateless; every run starts from its system prompt and the current message history.
> 2. **Handoff** — a structured transfer of control from one agent to another. Mechanically, a tool call that returns a new agent or a graph edge that follows a condition.
> 3. **Shared state** — any data structure that more than one agent can read (sometimes write). Message pool, blackboard, key-value store, vector memory.
> 4. **Orchestrator** — whoever decides who speaks next. Options: an explicit graph (deterministic), an LLM speaker-selector (soft), the last speaker's handoff call (OpenAI Swarm), or a scheduler over a queue (swarm architecture).
> That is the entire design space. Every framework picks defaults for each axis; the rest is surface syntax.

### How every 2026 framework maps to it · 2026 年的框架如何映射到它

| 框架 | Agent | Handoff | 共享状态 | Orchestrator |
|-----------|-------|---------|--------------|--------------|
| OpenAI Swarm / Agents SDK | `Agent(instructions, tools)` | 工具返回 Agent | 调用方的问题 | LLM 的下一次 handoff 调用 |
| AutoGen v0.4 / AG2 | `ConversableAgent` | GroupChat 上的说话者选择器 | 消息池 | 选择器函数（LLM 或轮询） |
| CrewAI | `Agent(role, goal, backstory)` | `Process.Sequential / Hierarchical` | Task 输出串成链 | 管理 LLM 或固定顺序 |
| LangGraph | 节点函数 | 图边 + 条件 | `StateGraph` reducer | 图本身，确定性 |
| Microsoft Agent Framework | agent + 编排模式 | 随模式而定 | thread／上下文 | 随模式而定 |
| Google ADK | agent + A2A 卡片 | A2A 任务 | A2A 工件 | host 决定 |

表层的差异看起来巨大。底下：同样四个旋钮。

> Surface differences look huge. Underneath: same four knobs.

### Why this matters · 这为什么重要

一旦看清这些原语，框架比较就变成一张短清单：

- 编排器是信任 LLM 来路由（Swarm），还是把路由钉死在代码里（LangGraph）？
- 共享状态是全量历史（GroupChat）还是投影（StateGraph reducer）？
- 智能体能修改彼此的提示词（CrewAI manager），还是只能交接（Swarm）？

这三个问题能回答 80% 的「哪个框架适合手头问题」。你不再逛「最好的多智能体框架」，而是开始围绕你真正在乎的那根轴做设计。

> Once you see the primitives, framework comparison becomes a short checklist:
> - Does the orchestrator trust the LLM to route (Swarm) or does it pin routing in code (LangGraph)?
> - Is shared state full-history (GroupChat) or projected (StateGraph reducer)?
> - Can agents modify each other's prompts (CrewAI manager) or only hand off (Swarm)?
> Those three questions answer 80% of which framework fits a given problem. You stop shopping for "the best multi-agent framework" and start designing for the axis you actually care about.

### The stateless insight · 无状态洞见

除共享状态之外，每个原语都是无状态的。Agent 是 (prompt, tools) 的函数。Handoff 是一次函数调用。Orchestrator 是一个调度器。**系统里唯一有状态的东西就是共享状态。** 所有有意思的 bug 都住在那里：记忆投毒（Lesson 15）、消息排序、版本化、写竞争。

把共享状态藏起来的框架（Swarm）把问题推给调用方。把共享状态集中起来的框架（LangGraph checkpoint、AutoGen pool）让它变得可检查，却把协调成本转嫁给了共享状态的实现。

> Every primitive except shared state is stateless. Agent is a function of (prompt, tools). Handoff is a function call. Orchestrator is a scheduler. **The only stateful thing in the system is shared state.** That is where all the interesting bugs live: memory poisoning (Lesson 15), message ordering, versioning, write contention.
> Frameworks that hide shared state (Swarm) push the problem to the caller. Frameworks that centralize it (LangGraph checkpoint, AutoGen pool) make it inspectable but shift coordination cost onto the shared-state implementation.

### Anatomy of a single primitive · 单个原语的解剖

#### Agent

```
Agent = (system_prompt, tools, model, optional_name)
```

没有记忆，没有状态。系统提示词和工具相同的两个 agent 可以互换。一切看起来像 per-agent 状态的东西，实际都在共享状态或 handoff 协议里。

> No memory. No state. Two agents with the same system prompt and tools are interchangeable. Everything that looks like per-agent state is actually in shared state or the handoff protocol.

#### Handoff

```
Handoff = (from_agent, to_agent, reason, payload)
```

三种实现占主导：

- **函数返回** —— 工具返回下一个 agent。这就是 OpenAI Swarm 模式。agent 把路由写进自己的工具 schema。
- **图边** —— LangGraph。边是声明式的。LLM 产出一个值；一个条件选出下一个节点。
- **说话者选择** —— AutoGen GroupChat。一个选择器函数（有时本身是一次 LLM 调用）读池子，挑出下一个说话者。

> Three implementations dominate:
> - **Function return** — the tool returns the next agent. This is the OpenAI Swarm pattern. Agents carry routing in their tool schemas.
> - **Graph edge** — LangGraph. Edges are declarative. The LLM produces a value; a condition selects the next node.
> - **Speaker selection** — AutoGen GroupChat. A selector function (sometimes itself an LLM call) reads the pool and picks who speaks next.

#### Shared state

```
SharedState = { messages: [], artifacts: {}, context: {} }
```

最起码是一条消息列表。往往更多：结构化工件（CrewAI Task 输出）、类型化上下文（LangGraph reducer）、外部记忆（MCP、向量库）。

两种拓扑：**全量池（full pool）**（每个 agent 看到每条消息）和**投影（projected）**（agent 看到按角色裁剪的视图）。全量池简单但扩展性差。投影池能扩展，但需要预先设计 schema。

> At minimum, a list of messages. Often more: structured artifacts (CrewAI Task outputs), typed context (LangGraph reducers), external memory (MCP, vector DB).
> Two topologies: **full pool** (every agent sees every message) and **projected** (agents see a role-scoped view). Full pools are simple and scale badly. Projected pools scale but require upfront schema design.

#### Orchestrator

```
Orchestrator = ({state, last_speaker}) -> next_agent
```

四种风味：

- **静态（Static）** —— 图在构建时固定（LangGraph 确定性、CrewAI Sequential）。
- **LLM 选择（LLM-selected）** —— 一个 LLM 读池子，挑出下一个说话者（AutoGen、CrewAI Hierarchical）。
- **Handoff 驱动（Handoff-driven）** —— 当前 agent 通过调用 handoff 工具来决定（Swarm）。
- **队列驱动（Queue-driven）** —— 工人从共享队列拉活；没有显式的下一个说话者（swarm 架构、Matrix）。

> Four flavors:
> - **Static** — the graph is fixed at build time (LangGraph deterministic, CrewAI Sequential).
> - **LLM-selected** — an LLM reads the pool and picks the next speaker (AutoGen, CrewAI Hierarchical).
> - **Handoff-driven** — the current agent decides by calling a handoff tool (Swarm).
> - **Queue-driven** — workers pull from a shared queue; no explicit next-speaker (swarm architectures, Matrix).

### What changes between frameworks · 框架之间还在变什么

原语固定之后，剩下的设计决策是：

- **记忆策略** —— 临时 vs 持久检查点（LangGraph checkpointer）。
- **安全边界** —— 谁能批准一次 handoff（human-in-the-loop）。
- **成本核算** —— 按 agent 计的 token 预算。
- **可观测性** —— 追踪 handoff、持久化状态以便回放。

全部都可以架在原语之上实现。没有一个是新原语。

```figure
a5-primitive-radar
```

> Once the primitives are fixed, the remaining design decisions are:
> - **Memory strategy** — ephemeral vs durable checkpointing (LangGraph checkpointer).
> - **Safety boundary** — who can approve a handoff (human-in-the-loop).
> - **Cost accounting** — per-agent token budgets.
> - **Observability** — tracing handoffs, persisting state for replay.
> All implementable on top of the primitives. None of them are new primitives.

## Build It · 动手造

`code/main.py` 用约 150 行 stdlib Python 实现这四个原语。没有真 LLM——每个 agent 是一段脚本化的策略，这样注意力就留在协调结构上。

这个文件导出：

- `Agent` —— 一个 dataclass：名字、系统提示词、工具、策略函数。
- `Handoff` —— 一个返回新 agent 的函数。
- `SharedState` —— 一个线程安全的消息池。
- `Orchestrator` —— 三个变体：`StaticOrchestrator`、`HandoffOrchestrator`、`LLMSelectorOrchestrator`（模拟）。

演示把同一条三智能体流水线（research → write → review）跑过全部三种编排器类型，最后打印消息池。你会看到输出只在*由谁挑下一个*上不同；agent 和共享状态在各次运行之间完全一致。

运行：

```
python3 code/main.py
```

预期输出：三次编排器运行，每种模式一次，各自打印最终的消息池。如果 researcher 提前认为自己干完了，handoff 驱动的那次运行会触及更少的 agent——这就是 LLM 路由取舍的微缩版。

> `code/main.py` implements the four primitives in ~150 lines of stdlib Python. No real LLM — each agent is a scripted policy so the focus stays on the coordination structure.
> The file exports:
> - `Agent` — a dataclass of name, system prompt, tools, policy function.
> - `Handoff` — a function that returns a new agent.
> - `SharedState` — a thread-safe message pool.
> - `Orchestrator` — three variants: `StaticOrchestrator`, `HandoffOrchestrator`, `LLMSelectorOrchestrator` (simulated).
> The demo runs the same three-agent pipeline (research → write → review) through all three orchestrator types and prints the message pool at the end. You can see that the outputs differ only in *who picks next*; the agents and shared state are identical across runs.
> Expected output: three orchestrator runs, one per pattern. Each prints the final message pool. The handoff-driven run reaches fewer agents if the researcher decides it is done early — that is the LLM-routing tradeoff in miniature.

## Use It · 实战用法

`outputs/skill-primitive-mapper.md` 是一个技能（skill）：读任意多智能体代码库或框架文档，返回四原语映射。新框架发布时先跑它，得到一段话级别的理解，再深入读文档。

> `outputs/skill-primitive-mapper.md` is a skill that reads any multi-agent codebase or framework doc and returns the four-primitive mapping. Run it on a new framework release to get a one-paragraph understanding before reading docs in depth.

## Ship It · 交付

采用一个新框架之前，先为它写下原语映射。如果写不出来，要么是文档不全，要么是这个框架在发明第五个原语（罕见——检查一下是不是有一种你没见过的共享状态形态）。

把映射钉进你的架构文档。新团队成员加入时，先发映射，再发 API 文档。框架版本变化时，diff 的是映射，不是 changelog。

> Before adopting a new framework, write the primitive mapping for it. If you cannot, the docs are incomplete or the framework is inventing a fifth primitive (rare — check for a shared-state flavor you have not seen).
> Pin the mapping in your architecture doc. When a new team member joins, send them the mapping before the API docs. When framework versions change, diff the mapping, not the changelog.

## Exercises · 练习

1. 用不同的 agent 策略把 `code/main.py` 跑三遍。观察编排器的选择如何改变哪些 agent 会运行。
2. 实现第四种编排器：队列驱动，agent 轮询共享状态来认领工作。会出现什么死锁？怎么检测？
3. 拿 LangGraph 快速上手（https://docs.langchain.com/oss/python/langgraph/workflows-agents），用四个原语重写它。LangGraph 的哪些抽象能 1:1 映射，哪些只是便利封装？
4. 读 OpenAI Swarm cookbook（https://developers.openai.com/cookbook/examples/orchestrating_agents）。指出 Swarm 把四个原语中的哪一个做得最顺手，又把哪一个推给了调用方。
5. 在表中找一个把共享状态完全藏起来的框架。解释当 agent 需要在 handoff 之间协调、又不重新读历史时，什么会坏掉。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| Agent | 「带工具的 LLM」 | 一个 `(system_prompt, tools, model)` 三元组。无状态。 |
| Handoff | 「控制权转移」 | 一个指名下一个 agent 和可选载荷的结构化调用。三种实现：函数返回、图边、说话者选择。 |
| Shared state | 「记忆」／「上下文」 | 多智能体系统里唯一有状态的部分。消息池或 blackboard。 |
| Orchestrator | 「协调者」 | 决定下一个由谁运行的人。静态图、LLM 选择器、handoff 驱动或队列驱动。 |
| Primitive | 「抽象」 | 每个框架都要参数化的四根轴之一。不是框架特性。 |
| Message pool | 「共享聊天历史」 | 全量历史的共享状态。好推理，扩展差。 |
| Projected state | 「裁剪视图」 | 共享状态的按角色视图。能扩展，需要 schema 设计。 |
| Speaker selection | 「谁下一个说」 | 一种编排模式：由一个函数（通常是 LLM）从一群里挑出下一个 agent。 |

## Further Reading · 延伸阅读

- [OpenAI cookbook: Orchestrating Agents — Routines and Handoffs](https://developers.openai.com/cookbook/examples/orchestrating_agents) —— handoff 驱动编排的最清晰表述
- [AutoGen stable docs](https://microsoft.github.io/autogen/stable/) —— GroupChat + 说话者选择是 LLM 选择编排的参照实现
- [LangGraph workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) —— 图边编排与基于 reducer 的共享状态
- [CrewAI introduction](https://docs.crewai.com/en/introduction) —— role-goal-backstory agent、Sequential / Hierarchical 过程
- [AG2 (community AutoGen continuation)](https://github.com/ag2ai/ag2) —— 微软把 v0.4 转入维护之后依然活跃的 AutoGen v0.2 线
