# Production Scaling — Queues, Checkpoints, Durability · 生产级扩展 —— 队列、检查点与持久性

> Scaling multi-agent systems to thousands of concurrent runs requires **durable execution** — work queues plus checkpoints, so any worker can resume any run after any crash, provided lease handling, idempotent side effects, and deterministic replay are in place. LangGraph's runtime is the reference example: it writes a checkpoint after each super-step keyed by `thread_id` (Postgres by default); worker crashes release a lease and another worker resumes. Agents can sleep indefinitely waiting for human input. **MegaAgent** (arXiv:2408.09955) ran a per-agent producer-consumer queue with three states (Idle / Processing / Response) and two-layer coordination (intra-group chat + inter-group admin chat). **Fiber/async** beats thread-per-job for LLM streaming: threads sit idle 99% of the time waiting for tokens, fibers cooperatively yield on I/O. Counterpoint: Ashpreet Bedi's "Scaling Agentic Software" argues for **FastAPI + Postgres + nothing else** until load proves otherwise — simple architectures go further than expected. This lesson builds a durable checkpoint log, a per-agent work queue with state transitions, an async-vs-thread demo, and lands the pragmatic "start simple" rule.

把多智能体系统扩展到数千个并发运行，需要**持久执行**（durable execution）—— 工作队列加检查点，这样任何一个 worker 在任何一次崩溃后都能恢复任何一个运行，前提是租约（lease）处理、幂等副作用和确定性重放都已就位。LangGraph 的运行时是参考示例：它每个 super-step 之后写一个以 `thread_id` 为键的检查点（默认用 Postgres）；worker 崩溃会释放租约，另一个 worker 接着跑。智能体可以无限期休眠等待人类输入。**MegaAgent**（arXiv:2408.09955）为每个智能体跑了生产者-消费者队列，三个状态（Idle / Processing / Response），两层协调（组内聊天 + 组间管理聊天）。对 LLM 流式输出来说，**纤程/async** 胜过每任务一线程：线程 99% 的时间在空等 token，纤程在 I/O 上协作式让出。反面观点：Ashpreet Bedi 的「Scaling Agentic Software」主张在负载证明有必要之前，**只用 FastAPI + Postgres，别的什么都不加** —— 简单架构能走得更远。本课构建一个持久检查点日志、一个带状态转换的每智能体工作队列、一个 async-vs-thread 演示，并把「从简单开始」这条务实规则讲透。

**Type:** Learn + Build
**Languages:** Python (stdlib, `asyncio`, `sqlite3`)
**Prerequisites:** Phase 16 · 09 (Parallel Swarm Networks), Phase 16 · 13 (Shared Memory)
**Time:** ~75 minutes

## Problem · 问题

一个原型多智能体系统在一台笔记本上跑得好好的：三个智能体、内存事件循环。一到生产环境：

- 智能体有时一跑几个小时（长时间研究、人在环路的等待）。
- 工作进程崩溃。重启会丢状态。
- 峰值负载是均值的 10 倍；你需要水平扩展。
- 用户按智能体运行次数付费；你需要精确一次的计费语义。

内存事件循环一样都做不到。你需要在底下加一层持久执行层。2026 年的标配选项：

1. 带检查点的工作流引擎（Temporal、LangGraph runtime）。
2. 消息队列加状态存储（Postgres + SQS/RabbitMQ）。
3. Actor 模型框架（MegaAgent 的每智能体生产者-消费者）。
4. 手写 FastAPI + Postgres（Bedi 的主张）。

本课把每一种都做一个迷你版。

> A prototype multi-agent system works on one laptop with three agents in an in-memory event loop. You move to production: agents sometimes run for hours; worker processes crash; peak load is 10x average; users pay per agent-run.
> The in-memory event loop does none of these. You need a durable execution layer underneath. The 2026 canonical options are: a workflow engine with checkpoints (Temporal, LangGraph runtime); a message queue with a state store (Postgres + SQS/RabbitMQ); actor-model frameworks (MegaAgent's producer-consumer per agent); hand-rolled FastAPI + Postgres (Bedi's argument).
> This lesson builds a miniature of each.

## Concept · 概念

### Durable execution, the pattern · 持久执行：这个模式

持久执行引擎在每个「步骤」（用 LangGraph 的话说叫 super-step）之后持久化完整的程序状态。崩溃时：

```
worker crashes mid-step
  -> lease timeout
  -> another worker picks up the thread_id
  -> resumes from last checkpoint
  -> no duplicate side effects
```

要让这一切成立，需要：

- **可序列化的状态。** 所有智能体状态都必须可持久化。带着活跃数据库连接的函数闭包是活不下来的。
- **确定性恢复。** 给定相同的状态和相同的输入，智能体产出相同的动作（或者对 LLM 调用委托给一个外部确定性预言机）。
- **幂等的副作用。** 外部调用（工具调用、支付）必须幂等，或者使用去重键。

LangGraph 在每个 super-step 后写检查点；Temporal 在每个 activity 后写；Restate 用事件溯源日志。三者实现的是同一个模式。

> A durable-execution engine persists the full program state after each "step" (super-step, in LangGraph's language). On crash: lease timeout, another worker picks up the thread_id, resumes from last checkpoint, no duplicate side effects.
> Requirements for this to work: serializable state; deterministic resume; idempotent side effects.
> LangGraph writes a checkpoint after each super-step; Temporal writes after each activity; Restate uses event-sourced journals. All three implement the same pattern.

### A checkpoint-per-step runtime · 每步一个检查点的运行时

LangGraph 的运行时是完整的示例：每个智能体有一个 `thread_id`；状态是一个带类型的 dict；每个 super-step 向检查点表写入一行。恢复时，运行时从最后一个检查点重放，而不是从头再来。智能体可以 `interrupt()` 等待人类输入；运行时把状态持久化并释放 worker。输入到达时，任何一个 worker 都能继续跑。

这是 2026 年 4 月的参考生产设计。

> LangGraph's runtime is the worked example: each agent has a `thread_id`; state is a typed dict; each super-step writes a row to the checkpoints table. On resume, the runtime replays from the last checkpoint, not from scratch. Agents can `interrupt()` waiting for human input; the runtime persists and releases the worker. When input arrives, any worker can resume.
> This is the reference production design in April 2026.

### MegaAgent's per-agent queue · MegaAgent 的每智能体队列

arXiv:2408.09955 描述了一个规模实验：一个集群里数千个并发智能体。架构：

```
agent i:
  state ∈ {Idle, Processing, Response}
  in_queue   <- messages addressed to agent i
  out_queue  -> replies + side effects

coordinators:
  intra-group chat  (agents in the same group)
  inter-group admin chat  (high-level routing)
```

两层协调让组内对话可以很密集，而组间保持稀疏 —— 这就是让成本在数千个智能体规模下保持线性的模式。

> arXiv:2408.09955 describes a scale experiment: thousands of concurrent agents in one cluster.
> The two-layer coordination lets intra-group conversation happen densely while inter-group stays sparse — the pattern used for keeping cost linear in thousands of agents.

### Async vs thread-per-job · Async 对比每任务一线程

LLM 调用是 I/O 密集的。等下一个 token 的线程有 99% 的时间处于空闲。线程每个约占 1MB 内存；10,000 个并发调用，光栈就要 10GB。

纤程（Python 的 `asyncio`、Go 的 goroutine、Rust 的 `tokio`）在 I/O 上协作式让出。同样 10,000 个调用轻松装进一个进程。在 LLM 智能体的规模下，async 不是一种优化 —— 它就是架构本身。

例外：CPU 密集的后处理（嵌入、分词器技巧）仍然需要线程或进程。把 I/O 层和 CPU 层分开。

> LLM calls are I/O-bound. A thread waiting for the next token is idle 99% of the time. Threads cost ~1MB RAM each; at 10,000 concurrent calls, that is 10GB just for stacks.
> Fibers (Python `asyncio`, Go goroutines, Rust `tokio`) cooperatively yield on I/O. The same 10,000 calls fit comfortably in process. At LLM-agent scale, async is not an optimization — it is the architecture.
> Exception: CPU-bound post-processing (embedding, tokenizer tricks) still wants threads or processes. Separate your I/O layer from your CPU layer.

### Bedi's counterpoint · Bedi 的反面观点

「Scaling Agentic Software」（Ashpreet Bedi，2026）论证：大多数团队在测得负载之前就过度设计了。务实的默认方案：

- FastAPI + Postgres。
- 每次智能体运行是一行；状态用乐观并发原地更新。
- 后台任务用 `pg_notify` 或一个简单的 Celery worker。
- 重试策略写在应用代码里。

对于约 100 个以下并发智能体运行、任务可控的负载，这通常就是全部所需。等你测到它撑不住了再升级。

规则是：当你撞上一个简单架构解决不了的具体问题时，才采用持久执行框架。过早采用会把时间烧在看不到回报的仪式上。

> "Scaling Agentic Software" (Ashpreet Bedi, 2026) argues that most teams over-engineer before they have measured load. The pragmatic default: FastAPI + Postgres; each agent run is a row; background jobs via `pg_notify` or a simple Celery worker; retry policy in application code.
> For loads under ~100 concurrent agent-runs on manageable tasks, this is often all you need. Upgrade when you measure it failing.
> The rule: adopt durable-execution frameworks when you hit a concrete problem that simple architectures cannot solve. Premature adoption burns time on ceremonies that do not pay off.

### Exactly-once semantics · 精确一次语义

对付费的智能体运行，你需要「效果上的精确一次」（至少一次投递 + 幂等消费）。工程手段：

- **每次运行一个去重键。** 每个副作用调用都带上它。
- **发件箱（Outbox）模式。** 副作用先写入一张表，再由一个独立进程执行。两步都幂等。
- **补偿事务。** 当副作用成功但其追踪写入失败时，安排一次补偿。

这些是数据库工程模式，不是 LLM 专属。LLM 带来的额外负担只是 LLM 调用很慢；其余都是标准的分布式系统内容。

> For paid agent runs, you need "exactly-once effective" (at-least-once delivery + idempotent consumer). The engineering moves: dedup key per run; outbox pattern; compensating transactions.
> These are database-engineering patterns, not LLM-specific. The LLM tax is only that LLM calls are slow; everything else is standard distributed systems.

### Rainbow deployment · 彩虹部署

Anthropic 的多智能体研究系统使用「彩虹部署」：多个版本的智能体运行时并发运行，这样长时间运行的智能体不必在每次代码部署时被杀掉。把新版本金丝雀放量到一部分流量上；等旧版本上的智能体跑完再退役它们。

这对长时间运行的有状态系统是标准做法；2026 年的新变化是智能体可以活好几个小时，所以部署周期必须为此留出余地。

> Anthropic's multi-agent research system uses "rainbow deployments": multiple versions of the agent runtime run concurrently so long-running agents do not have to be killed on every code deploy. Canary new versions on a slice of traffic; retire old versions when their agents finish.
> This is standard for long-running stateful systems; the 2026 adaptation is that agents can live for hours, so deployment cycles must accommodate.

### The canonical production checklist · 生产环境标准检查清单

- 持久状态（检查点、快照，或 outbox + 可重放日志）。
- 幂等的副作用。
- LLM 调用的异步 I/O 层。
- 至少一次投递加去重。
- 面向有状态工作负载的彩虹/金丝雀部署。
- 可观测性：按智能体的追踪、super-step 审计、重试计数器。

> Durable state (checkpoints, snapshots, or outbox + replayable log); idempotent side effects; async I/O layer for LLM calls; at-least-once delivery with dedup; rainbow/canary deployment for stateful workloads; observability: per-agent traces, super-step audit, retry counter.

```figure
sw-checkpoint-replay
```

## Build It · 动手造

`code/main.py` 实现：

- `CheckpointStore` —— 以 thread-id 为键的 SQLite 检查点日志。每个 super-step 追加一行。
- `run_with_checkpoint(agent, thread_id)` —— 模拟运行中途崩溃；第二个 worker 从最后一个检查点恢复。
- `AgentQueue` —— 每个智能体的 Idle / Processing / Response 状态机，带一个小工作队列。
- `demo_async_vs_threads()` —— 分别用 asyncio 和线程跑 500 个并发的模拟「LLM 调用」；报告墙钟时间和峰值内存（近似值）。

运行：

```
python3 code/main.py
```

预期输出：模拟崩溃后检查点恢复成功；async 版本在 1 秒内处理完 500 个并发调用；线程版本要花好几秒，且每个并发单元占用的内存高出若干个数量级。

> Expected output: checkpoint resume succeeds after simulated crash; async version handles 500 concurrent calls in < 1s; thread version takes several seconds and uses orders of magnitude more memory per concurrent unit.

## Use It · 实战用法

`outputs/skill-scaling-advisor.md` 为持久执行选型提供建议：FastAPI + Postgres、LangGraph runtime、Temporal、还是自研。按负载、状态保留需求和部署频率来校准。

> `outputs/skill-scaling-advisor.md` advises on durable-execution choice: FastAPI + Postgres, LangGraph runtime, Temporal, or custom. Calibrated by load, state-retention needs, and deploy frequency.

## Ship It · 交付

生产环境的标准加固：

- **从简单开始（Bedi 规则）。** FastAPI + Postgres，直到你测到它撑不住。
- **优化之前先埋点。** 每次运行的延迟直方图、每步耗时、重试次数、失败分类。
- **副作用用 outbox 模式。** 支付和外部 API 调用尤其如此。
- **彩虹部署。** 绝不在部署时杀掉运行中的智能体任务。
- **什么时候采用持久执行引擎（Temporal / LangGraph / Restate）：** 当你撞上具体问题 —— 小时级的人环路等待、跨区域协调、复杂的重试/补偿策略。
- **I/O 层用 async。** 线程只留给 CPU 密集的后处理。

> Canonical production hardening: start simple (Bedi's rule); instrument everything before optimizing; outbox pattern for side effects; rainbow deploys; adopt durable-execution engines when you hit specific problems; async for the I/O layer, threads only for CPU-bound post-processing.

## Exercises · 练习

1. 运行 `code/main.py`。确认检查点恢复有效；测量 async 与 thread 的并发差异。
2. 实现 **outbox** 表：每个工具调用先写入 outbox，再由一个独立的 goroutine/task 执行。把工具调用跑两遍来验证幂等性。
3. 模拟一次**彩虹部署**：两个运行时版本并发；把新的 thread_id 一半路由给每个版本；确认旧版本上运行中的线程不被打断。
4. 阅读 LangGraph 的运行时文档（链接见下）。找出哪些运行时特性在手写 FastAPI + Postgres 版本里复刻耗时最长。这是采用它的理由吗，还是可以推迟？
5. 阅读 MegaAgent（arXiv:2408.09955）第 3 节。两层协调（组内 + 组间管理聊天）是显式设计的。勾画出你会如何把它映射到带两个队列族的消息队列上。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Durable execution | 「持久化程序状态」 | 引擎在每个 super-step 后写入状态；崩溃恢复是确定性的。 |
| Super-step | 「事务边界」 | 检查点之间的工作单元。LangGraph 术语。 |
| thread_id | 「智能体运行标识符」 | 绑定检查点与恢复逻辑的键。 |
| Idempotency | 「重试安全」 | 重复执行一个副作用，结果与执行一次相同。 |
| Outbox pattern | 「副作用解耦」 | 先把意图写入一张表；由独立执行器执行并标记完成。 |
| At-least-once delivery | 「可能有重复」 | 消息队列语义；去重键让消费端效果上只处理一次。 |
| Rainbow deploy | 「多版本并存」 | 长时间运行的工作负载期间，多个运行时版本并发。 |
| Async fiber | 「协作式让出」 | 用户态并发；对 I/O 密集负载比线程便宜得多。 |
| Checkpoint | 「状态快照」 | super-step 边界上的序列化状态；恢复的关键。 |

## Further Reading · 延伸阅读

- [LangChain — The runtime behind production deep agents](https://www.langchain.com/conceptual-guides/runtime-behind-production-deep-agents) — LangGraph 运行时设计
- [MegaAgent](https://arxiv.org/abs/2408.09955) — 每智能体生产者-消费者队列；数千并发智能体下的两层协调
- [Matrix](https://arxiv.org/abs/2511.21686) — 以消息队列为协调基底的去中心化框架
- [Temporal docs](https://docs.temporal.io/) — 持久执行的参考工作流引擎
- [Anthropic — Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) — 生产经验，包括彩虹部署
