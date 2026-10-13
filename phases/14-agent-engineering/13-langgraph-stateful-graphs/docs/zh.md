# Stateful Graph Orchestration — Durable Execution and Checkpoints · 有状态图编排——持久执行与检查点

> Agent is a state machine; nodes are functions; edges are transitions; state is checkpointed after each node. Resume from any failure at the last successful checkpoint. LangGraph is the 2026 reference for this model of low-level stateful orchestration.

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 12 (Workflow Patterns)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 描述 LangGraph 的核心模型：带类型状态的状态机、函数节点、条件边、节点后检查点
- 说出文档强调的四种能力：持久执行（durable execution）、流式（streaming）、人在环（human-in-the-loop）、全面记忆（memory）
- 解释 LangGraph 支持的三种编排拓扑：supervisor、点对点（swarm）、分层（嵌套子图）
- 用 stdlib 实现一个带类型状态、条件边和检查点/恢复循环的状态图

> Describe LangGraph's core model: state machine with typed state, function nodes, conditional edges, and post-node checkpoints.
> Name the four capabilities the docs highlight: durable execution, streaming, human-in-the-loop, comprehensive memory.
> Explain the three orchestration topologies LangGraph supports: supervisor, peer-to-peer (swarm), hierarchical (nested subgraphs).
> Implement a stdlib state graph with typed state, conditional edges, and a checkpoint/resume cycle.

## The Problem · 问题在哪

agent 和工作流共享一个难题：一个 40 步的运行在第 38 步失败时，你要从第 38 步恢复，而不是从头再来。二等公民式的状态模型，让运维只能在一个假设「每次都是全新运行」的库周围东补西凑地写重试逻辑。

LangGraph 的设计回答：状态是一等的、带类型的对象，变更是显式的，每个节点之后都落检查点（checkpoint）。恢复就是一次 `load_state(session_id)` 调用。

> Agents and workflows share a problem: when a 40-step run fails at step 38, you want to resume from step 38, not start over. Second-class state models leave operators hacking retries around a library that assumes fresh runs.
> LangGraph's design answer: state is a first-class typed object, mutations are explicit, and checkpoints persist after every node. Resume is a `load_state(session_id)` call.

## The Concept · 概念

### The graph · 图

一张图由以下构成：

- **状态类型（State type）。** 一个带类型的 dict（或 Pydantic 模型），每个节点都读它、改它。
- **节点（Nodes）。** 纯函数 `(state) -> state_update`。返回之后，更新被合并进状态。
- **边（Edges）。** 节点之间的条件转移或直接转移。
- **入口与出口。** `START` 和 `END` 哨兵节点标记边界。

例子：一个带 `classify`、`refund`、`bug`、`sales`、`done` 节点的 agent——一张图形状的路由工作流。

> **State type.** A typed dict (or Pydantic model) that every node reads and mutates.
> **Nodes.** Pure functions `(state) -> state_update`. Updates are merged into state after return.
> Example: an agent with `classify`, `refund`, `bug`, `sales`, `done` nodes — a routing workflow as a graph.

### Durable execution · 持久执行

每个节点返回之后，运行时把状态序列化，写进一个 checkpointer（SQLite、Postgres、Redis、自定义）。在第 N 步失败时，运行时可以 `resume(session_id)`，带着精确的状态从第 N+1 步继续。

LangGraph 文档明确点名了这件事实实在要紧的生产用户：Klarna、Uber、摩根大通（J.P. Morgan）。卖点不是图的形状；而是图的形状加上检查点，让恢复变得便宜。

> After each node returns, the runtime serializes the state and writes it to a checkpointer (SQLite, Postgres, Redis, custom). On failure at step N, the runtime can `resume(session_id)` and pick up from step N+1 with exact state.
> The LangGraph docs explicitly highlight production users where this matters: Klarna, Uber, J.P. Morgan. The claim isn't the graph shape; it's that the graph shape plus checkpointing makes recovery cheap.

### Streaming · 流式

每个节点都可以产出部分输出。图把按节点的增量事件流式发给调用方，UI 随着图的运行实时更新。

> Every node can yield partial output. The graph streams per-node-delta events to the caller so UIs update as the graph runs.

### Human-in-the-loop · 人在环

在节点之间检查并修改状态。实现方式：在关键节点前暂停，把状态呈给一个人，接受修改，恢复运行。checkpointer 让这件事变得容易，因为状态本来就已经序列化了。

> Inspect and modify state between nodes. Implementations: pause before a critical node, surface state to a human, accept modifications, resume. The checkpointer makes this easy because state is already serialized.

### Memory · 记忆

短期（一次运行之内——状态里的对话历史）和长期（跨运行——经 checkpointer 持久化，外加一个独立的长期存储）。LangGraph 通过工具与外部记忆系统（Mem0、自定义）集成。

> Short-term (within a run — conversation history in state) and long-term (across runs — persistent via the checkpointer plus a separate long-term store). LangGraph integrates with external memory systems (Mem0, custom) via tools.

### Three topologies · 三种拓扑

1. **Supervisor。** 中央路由 LLM 把任务派给专家子 agent。即 `langgraph-supervisor` 里的 `create_supervisor()`（不过 LangChain 团队在 2026 年建议直接通过工具调用来做这件事，以获得更强的上下文控制）。
2. **Swarm / 点对点。** agent 通过共享的工具面直接交接。没有中央路由。
3. **分层（Hierarchical）。** supervisor 管理子 supervisor，实现为嵌套子图。

> **Supervisor.** Central router LLM dispatches to specialist subagents. `create_supervisor()` in `langgraph-supervisor` (though the LangChain team in 2026 recommends doing this through tool calls directly for more context control).
> **Swarm / peer-to-peer.** Agents hand off directly via a shared tool surface. No central router.
> **Hierarchical.** Supervisors managing sub-supervisors, implemented as nested subgraphs.

### Where this pattern goes wrong · 这个模式哪里会出错

- **检查点太小。** 只检查对话轮次的话，工具状态和记忆写入就不可恢复。完整状态必须可序列化。
- **非确定性节点。** 恢复假设节点输入会产生同样的状态更新。随机种子、墙钟、外部 API 都必须被捕获。
- **条件边滥用。** 每条边都是条件的图，是一台没法推理的状态机。优先用带少量分支的线性链。

```figure
langgraph-state
```

> **Checkpoints too small.** Only checkpointing conversation turns leaves tool state and memory writes unrecoverable. Full state must serialize.
> **Non-deterministic nodes.** Resume assumes node inputs produce the same state update. Random seeds, wall-clock, external APIs must be captured.
> **Over-use of conditional edges.** A graph with every edge conditional is a state machine that cannot be reasoned about. Prefer linear chains with occasional branches.

## Build It · 动手造

`code/main.py` 实现一个 stdlib 有状态图：

- `State` — 一个带类型的 dict，含 `messages`、`step`、`route`、`output`、`human_approval`。
- `Node` — 接收状态、返回更新 dict 的可调用对象。
- `StateGraph` — 节点 + 边 + 条件边 + run + resume。
- `SQLiteCheckpointer`（内存中的假实现）—— 每个节点之后序列化状态；`load(session_id)` 恢复。
- 一个演示图：classify -> 分支(refund / bug / sales) -> 人工关卡 -> send。

运行：

```
python3 code/main.py
```

轨迹展示了第一次运行在人工关卡失败、状态持久化，然后恢复并产出最终输出。

> The trace shows the first run failing at the human gate, persistence, then resume producing the final output.

## Use It · 实战用法

- **LangGraph** — 参照标准，生产可用。用 `create_react_agent`、`create_supervisor`，或者自己造图。
- **AutoGen v0.4**（Lesson 14）— 高并发场景下 actor 模型的替代方案。
- **Claude Agent SDK**（Lesson 17）— 带内置会话存储的托管 harness。
- **自建** — 当你需要对状态形状或 checkpointer 后端做精确控制时。

> **LangGraph** — the reference, production-ready. Use `create_react_agent`, `create_supervisor`, or build your own graph.
> **AutoGen v0.4** (Lesson 14) — actor model alternative for high-concurrency scenarios.
> **Claude Agent SDK** (Lesson 17) — managed harness with built-in session store.
> **Custom** — when you need exact control over state shape or checkpointer backend.

## Ship It · 交付

`outputs/skill-state-graph.md` 在任意目标运行时里生成一个 LangGraph 形状的状态图，接好检查点与恢复。

> `outputs/skill-state-graph.md` generates a LangGraph-shaped state graph in any target runtime with checkpointing and resume wired in.

## Exercises · 练习

1. 加一条从 `classify` 到 `end` 的条件边：分类置信度低于阈值时触发。人工手动设置 `route` 之后恢复运行。
2. 把 SQLite 假实现换成真的 SQLite checkpointer。测一测每一步的序列化开销。
3. 实现并行边：两个节点并发运行，用自定义 reducer 合并。不可变状态在这里买到了什么？
4. 读 `langgraph-supervisor` 参考。把玩具移植到 `create_supervisor`。对比两种轨迹的形状。
5. 加流式：每个节点在运行时产出部分状态。增量一到就打印。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| State graph（状态图） | 「agent 即状态机」 | 类型化状态 + 节点 + 边 + reducer |
| Checkpointer | 「持久化后端」 | 每个节点后序列化状态；让恢复成为可能 |
| Reducer | 「状态合并器」 | 把当前状态与节点更新合并起来的函数 |
| Conditional edge（条件边） | 「分支」 | 由状态的函数选出来的边 |
| Subgraph（子图） | 「嵌套图」 | 在另一张图里当节点用的图 |
| Durable execution（持久执行） | 「失败恢复」 | 带着精确状态从最后一个成功节点重启 |
| Supervisor | 「路由 LLM」 | 专家子 agent 的中央调度器 |
| Swarm | 「P2P agent」 | agent 经共享工具交接；没有中央路由 |

## Further Reading · 延伸阅读

- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) —— 参考文档
- [langgraph-supervisor reference](https://reference.langchain.com/python/langgraph/supervisor/) —— supervisor 模式 API
- [AutoGen v0.4, Microsoft Research](https://www.microsoft.com/en-us/research/articles/autogen-v0-4-reimagining-the-foundation-of-agentic-ai-for-scale-extensibility-and-robustness/) —— actor 模型替代方案
- [Claude Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview) —— 会话存储与子 agent
