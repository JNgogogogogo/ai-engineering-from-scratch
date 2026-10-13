# The Actor Model for Agents — Async Messages and Typed Runtimes · 面向 agent 的 actor 模型——异步消息与类型化运行时

> Agents as actors: async message exchange, event-driven handlers, fault isolation, natural concurrency. AutoGen v0.4 (Microsoft Research, Jan 2025) redesigned agent orchestration around this model; the framework is now in maintenance mode, with Microsoft Agent Framework (public preview Oct 2025) as its production successor.

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 12 (Workflow Patterns)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 描述 actor 模型：agent 即 actor，消息是唯一的进程间通信，失败按 actor 隔离
- 说出 AutoGen v0.4 的三个 API 层——Core、AgentChat、Extensions——以及各自的用途
- 解释为什么把消息投递与处理解耦能带来故障隔离和天然并发
- 用 Python 实现一个 stdlib actor 运行时，并把一个双 agent 代码评审流程移植上去

> Describe the actor model: agents as actors, messages as the only IPC, failure isolation per actor.
> Name AutoGen v0.4's three API layers — Core, AgentChat, Extensions — and what each is for.
> Explain why decoupling message delivery from handling gives fault isolation and natural concurrency.
> Implement a stdlib actor runtime in Python and port a two-agent code-review flow onto it.

## The Problem · 问题在哪

大多数 agent 框架是同步的：一个 agent 生产、一个 agent 消费，挤在同一条调用栈里。失败会炸掉整条栈。并发是事后焊上去的。要分布式就得重写。

AutoGen v0.4 的回答：actor 模型。每个 agent 是一个带私有收件箱（inbox）的 actor。消息是唯一的交互方式。运行时把投递与处理解耦。失败隔离到单个 actor。并发是原生的。分布式只是换一种传输而已。

> Most agent frameworks are synchronous: one agent produces, one agent consumes, in a call stack. Failures crash the stack. Concurrency is bolted on. Distribution requires rewriting.
> AutoGen v0.4's answer: the actor model. Each agent is an actor with a private inbox. Messages are the only interaction. The runtime decouples delivery from handling. Failures isolate to one actor. Concurrency is native. Distribution is just different transport.

## The Concept · 概念

### Actors · Actor

一个 actor 有：

- 私有状态（外部从不直接触碰）。
- 一个收件箱（消息队列）。
- 一个处理器：`receive(message) -> effects`，效果可以是「回复」「发给其他 actor」「派生新 actor」「更新状态」「停止自己」。

两个 actor 不能共享内存。它们只能发消息。

> An actor has: a private state (never directly touched from outside); an inbox (message queue); a handler: `receive(message) -> effects` where effects can be "reply," "send to other actor," "spawn new actor," "update state," "stop self."
> Two actors cannot share memory. They can only send messages.

### Three API layers · 三个 API 层

AutoGen v0.4 把自己的表面切成三层：

1. **Core。** 底层 actor 框架。`AgentRuntime`、`Agent`、`Message`、`Topic`。异步消息交换，事件驱动。
2. **AgentChat。** 任务驱动的高层 API（v0.2 ConversableAgent 的替代品）。`AssistantAgent`、`UserProxyAgent`、`RoundRobinGroupChat`、`SelectorGroupChat`。
3. **Extensions。** 集成——OpenAI、Anthropic、Azure、工具、记忆。

> **Core.** Low-level actor framework. `AgentRuntime`, `Agent`, `Message`, `Topic`. Async message exchange, event-driven.
> **AgentChat.** Task-driven high-level API (replacement for v0.2's ConversableAgent). `AssistantAgent`, `UserProxyAgent`, `RoundRobinGroupChat`, `SelectorGroupChat`.
> **Extensions.** Integrations — OpenAI, Anthropic, Azure, tools, memory.

### Why decoupling matters · 解耦为什么重要

在 v0.2 模型里，调用 `agent_a.chat(agent_b)` 会同步阻塞 agent_a，直到 agent_b 返回。在 v0.4 里，`send(agent_b, msg)` 把消息放进 agent_b 的收件箱就返回。运行时稍后投递。三个后果：

- **故障隔离。** Agent B 崩掉不会崩掉 Agent A——运行时在 B 的处理器里接住失败，并决定怎么办（记日志、重试、进死信）。
- **天然并发。** 很多消息同时在途；actor 并发地处理自己的收件箱。
- **面向分布式。** 无论 actor 在本进程内还是在另一台主机上，「收件箱 + 传输」都是同一个抽象。

> In v0.2, calling `agent_a.chat(agent_b)` synchronously blocks agent_a until agent_b returns. In v0.4, `send(agent_b, msg)` puts the message in agent_b's inbox and returns. The runtime delivers later. Three consequences:
> **Fault isolation.** Agent B crashing does not crash Agent A — the runtime catches the failure in B's handler and decides what to do (log, retry, dead-letter).
> **Natural concurrency.** Many messages in flight at once; actors process their inbox concurrently.
> **Distribution-ready.** Inbox + transport is the same abstraction whether the actor is in-process or on another host.

### Topologies · 拓扑

- **RoundRobinGroupChat。** agent 按固定轮转依次发言。
- **SelectorGroupChat。** 一个选择器 agent 根据对话上下文挑选下一个谁上场。
- **Magentic-One。** 面向网页浏览、代码执行、文件处理的参考级多 agent 团队。构建在 AgentChat 之上。

> **RoundRobinGroupChat.** Agents take turns in a fixed rotation.
> **SelectorGroupChat.** A selector agent picks who goes next based on conversation context.
> **Magentic-One.** Reference multi-agent team for web browsing, code execution, file handling. Built on AgentChat.

### Observability · 可观测性

内置 OpenTelemetry 支持。每条消息发一个 span；工具调用按照 2026 年的 OTel GenAI 语义约定（semantic conventions）携带 `gen_ai.*` 属性（Lesson 23）。

> OpenTelemetry support is built in. Every message emits a span; tool calls carry `gen_ai.*` attributes per the 2026 OTel GenAI semantic conventions (Lesson 23).

### Status: maintenance mode · 现状：维护模式

2026 年初：AutoGen v0.7.x 对研究和原型开发来说仍然稳定。微软已把活跃开发转移到 Microsoft Agent Framework——生产化的继任者（2025 年 10 月 1 日公开预览；1.0 GA 原本定在 2026 年 Q1 末）。AutoGen 的模式可以干净地向前移植——actor 模型才是那个耐用的思想。

> Early 2026: AutoGen v0.7.x is stable for research and prototyping. Microsoft has shifted active development to the Microsoft Agent Framework, the production successor (public preview Oct 1 2025; 1.0 GA was targeted for end of Q1 2026). AutoGen patterns port forward cleanly — the actor model is the durable idea.

```figure
actor-mailbox
```

## Build It · 动手造

`code/main.py` 实现一个 stdlib actor 运行时：

- `Message` — 带类型的载荷，含 `sender`、`recipient`、`topic`、`body`。
- `Actor` — 抽象类，带 `receive(message, runtime)`。
- `Runtime` — 带共享队列的事件循环，负责投递和故障隔离。
- 一个双 actor 演示：`ReviewerAgent` 评审代码，`ChecklistAgent` 跑检查清单；两者交换消息直到达成共识。

运行：

```
python3 code/main.py
```

轨迹展示了消息投递、一个 actor 里模拟的失败（另一个 actor 不受影响），以及在一个共同结论上的收敛。

> The trace shows message delivery, a simulated failure in one actor that does not crash the other, and convergence on a shared verdict.

## Use It · 实战用法

- **AutoGen v0.4/v0.7**（维护模式）— 对研究、原型、多 agent 模式来说稳定。
- **Microsoft Agent Framework** — 生产化的继任者（2025 年 10 月公开预览）；同样的 actor 模型思想，API 翻新。
- **LangGraph swarm 拓扑**（Lesson 13）— 通过共享工具交接实现的类似模式。
- **自建 actor 运行时** — 当你需要特定传输层（NATS、RabbitMQ、gRPC）时。

> **AutoGen v0.4/v0.7** (maintenance) — stable for research, prototyping, multi-agent patterns.
> **Microsoft Agent Framework** — the production successor (public preview Oct 2025); same actor-model ideas in a refreshed API.
> **LangGraph swarm topology** (Lesson 13) — similar pattern via shared-tool handoffs.
> **Custom actor runtime** — when you need specific transport (NATS, RabbitMQ, gRPC).

## Ship It · 交付

`outputs/skill-actor-runtime.md` 生成一个最小 actor 运行时，外加一个团队模板（RoundRobin 或 Selector），适配给定的多 agent 任务。

> `outputs/skill-actor-runtime.md` generates a minimal actor runtime plus a team template (RoundRobin or Selector) for a given multi-agent task.

## Exercises · 练习

1. 加一个死信队列（dead-letter queue）：处理器抛异常时，把失败的消息停好等人工检查。你的玩具里 DLQ 被打中的频率如何？
2. 实现 `SelectorGroupChat`：一个选择器 actor 根据对话状态挑选谁来处理下一条消息。
3. 加分布式传输：把进程内队列换成 JSON-over-HTTP 服务器，让 actor 能跑在各自独立的进程里。
4. 给每条消息接一个 OTel span（或者一个 no-op 替身）。按 Lesson 23 发出 `gen_ai.agent.name`、`gen_ai.operation.name`。
5. 读 AutoGen v0.4 的架构文章。把你的玩具移植到真正的 `autogen_core` API。你跳过了什么在生产里要紧的东西？

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| Actor | 「Agent」 | 私有状态 + 收件箱 + 处理器；无共享内存 |
| Message（消息） | 「事件」 | 带类型的载荷；actor 之间唯一的交互方式 |
| Inbox（收件箱） | 「邮箱」 | 每个 actor 一个的待处理消息队列 |
| Runtime（运行时） | 「agent 宿主」 | 路由消息并隔离失败的事件循环 |
| Topic | 「频道」 | actor 之间命名的发布-订阅路由 |
| Fault isolation（故障隔离） | 「随它崩」 | 一个 actor 失败不会拖垮其他 actor |
| RoundRobinGroupChat | 「固定轮转团队」 | agent 按顺序轮流上场 |
| SelectorGroupChat | 「按上下文路由的团队」 | 选择器挑选下一个谁上场 |
| Magentic-One | 「参考团队」 | 覆盖网页 + 代码 + 文件的多 agent 小队 |

## Further Reading · 延伸阅读

- [AutoGen v0.4, Microsoft Research](https://www.microsoft.com/en-us/research/articles/autogen-v0-4-reimagining-the-foundation-of-agentic-ai-for-scale-extensibility-and-robustness/) —— 重设计文章
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) —— 图形状的替代方案
- [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) —— AutoGen 默认发出的那些 span
