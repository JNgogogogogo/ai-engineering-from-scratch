# Parallel / Swarm / Networked Architectures · 并行 / 群体 / 网状架构

> 与监督者模式相反：没有中央决策者。智能体读取共享事件总线，异步认领工作，把结果写回。LangGraph 明确支持面向去中心化动态环境的「群体架构（Swarm Architecture）」。Matrix（arXiv:2511.21686）把控制流和数据流都表示为经由分布式队列传递的序列化消息，以消除编排者瓶颈。代价是明摆着的：用确定性和可追溯性换可扩展性。群体适合拥有大量独立子问题的任务；不适合需要单一连贯计划的任务。

> Contrast with supervisor: no central decider. Agents read a shared event bus, pick up work asynchronously, write results back. LangGraph explicitly supports "Swarm Architecture" for decentralized, dynamic environments. Matrix (arXiv:2511.21686) represents both control and data flow as serialized messages passed through distributed queues to eliminate the orchestrator bottleneck. The tradeoff is explicit: determinism and traceability for scalability. Swarm fits tasks with many independent sub-problems; it does not fit tasks that need a single coherent plan.

**Type:** Learn + Build
**Languages:** Python (stdlib, `threading`, `queue`)
**Prerequisites:** Phase 16 · 05 (Supervisor Pattern), Phase 16 · 04 (Primitive Model)
**Time:** ~75 minutes

---

## Problem · 问题

监督者能扩展到几个 worker。几百个呢？监督者本身成了瓶颈：每一个「谁做什么」的决策都要经过一个智能体。一步慢的计划让整个系统停摆。

群体（swarm）架构把设计翻转过来。不再是中央规划者分派工作，而是 worker 从共享队列里认领工作。「协调」被直接烤进事件总线的语义里。没有编排者；系统扩展到队列扩展不动为止。

> Supervisor scales to a few workers. What about hundreds? The supervisor itself becomes the bottleneck: every decision about who does what funnels through one agent. One slow plan step stalls the whole system. ... Swarm architectures flip the design. Instead of a central planner dispatching work, workers pick work off a shared queue. The "coordination" is baked into the event bus semantics. No orchestrator; the system scales until the queue does.

---

## Concept · 概念

### The shape · 形态

```
                ┌──── shared queue ────┐
                │                      │
       ┌────────┼────────┐  ◄──────┬───┘
       ▼        ▼        ▼         │
     Worker  Worker  Worker   Worker
      A       B       C        D
       │        │        │         │
       └────────┴────────┴─────────┘
                 │
                 ▼
            results pool
```

没有编排者。每个 worker 不断重复：拉一个任务，处理，写出结果（并可选地把后续任务入队）。

> No orchestrator. Each worker repeats: pull a task, process, write result (and optionally enqueue follow-ups).

---

### When swarm fits · 群体什么时候合适

- **大量独立任务。** 抓取、转换、分类。任务之间互不依赖。
- **时长不均的工作。** 如果有的任务要 100ms、有的要 10s，群体会自动均衡负载——快的 worker 拉下一个任务。监督者则必须预判时长。
- **吞吐量优先于确定性。** 你关心总完成时间，而不是严格顺序。

> **Many independent tasks.** Scraping, transforming, classifying. Tasks do not depend on each other. ... **Variable-duration work.** If some tasks take 100ms and others take 10s, a swarm balances load automatically — fast workers pull next jobs. A supervisor has to anticipate duration. ... **Throughput over determinism.** You care about total completion time, not strict ordering.

---

### When swarm fails · 群体什么时候失败

- **有序工作流。** 如果第 3 步需要第 2 步的输出，群体就有第 3 步抢跑的风险。
- **需要全局计划的任务。** 复杂的研究问题受益于规划者。一群研究员产出的是独立的事实，不是一份连贯的报告。
- **调试。** 没有中央日志加上异步执行，复现一个 bug 代价很高。

> **Ordered workflows.** If step 3 needs step 2's output, a swarm risks step 3 firing before step 2 is done. ... **Global-plan tasks.** Complex research questions benefit from a planner. A swarm of researchers produces independent facts, not a coherent report. ... **Debugging.** With no central log and asynchronous work, reproducing a bug is expensive.

---

### Matrix (arXiv:2511.21686) · Matrix（arXiv:2511.21686）

Matrix 是 2025 年把群体推向逻辑终点的论文：控制流和数据流都是分布式队列上的序列化消息。没有中央协调者。容错来自消息持久性。可扩展性是消息中间件的问题，不是系统的问题。

贡献：一个编程模型，把多智能体协调从「监督者接下来选哪个智能体？」变成「这个智能体订阅哪个消息主题？」这让系统看起来像一张发布/订阅事件网格。

> Matrix is the 2025 paper that takes swarm to its natural conclusion: both control flow and data flow are serialized messages on distributed queues. No central coordinator. Fault tolerance comes from message durability. Scalability is the message broker's problem, not the system's. ... Contribution: a programming model where multi-agent coordination is "what message topic does this agent subscribe to?" rather than "which agent does the supervisor pick next?" This makes the system look like a pub/sub event mesh.

---

### Swarm in graph frameworks · 图框架中的群体

LangGraph 2025 文档明确把「群体架构（Swarm Architecture）」列为多智能体模式之一：智能体是节点，但边构成带环的有向图，任何节点都可以从池中被激活。worker 按条件从可用工作里挑选，而不是按监督者指派。

> LangGraph 2025 docs explicitly describe "Swarm Architecture" as one of the multi-agent patterns: agents are nodes, but edges form a directed graph with cycles and any node can be activated from the pool. A worker picks from available work by condition, not by supervisor assignment.

---

### Failure mode: starvation and hot-spotting · 失败模式：饥饿与热点

如果所有 worker 都抢最快的可用任务，长任务永远轮不到，直到只剩它们。经典的队列饥饿。

缓解措施：

- 带显式老化的优先队列（随等待时间提高优先级）。
- worker 专业化：某些 worker 只接「长」任务。
- 背压（back-pressure）：限制进入队列的快任务数量。

> If all workers pull the fastest-available task, long-running tasks never get picked until they are the only ones left. Classic queue starvation. ... Mitigations: priority queues with explicit aging (increase priority with wait time); worker specialization (some workers only take "long" tasks); back-pressure (limit how many fast tasks enter the queue).

---

### The content-based routing link · 与基于内容路由的联系

群体与基于内容的路由（第 22 课）天然搭配。不是一条通用队列，而是每种消息类型一条队列。专业 worker 只订阅自己的类型。这是可扩展到数千智能体的消息总线架构的基础。

```figure
sw-work-stealing
```

> Swarm pairs naturally with content-based routing (Lesson 22). Instead of a generic queue, have one queue per message type. Specialist workers subscribe only to their type. This is the basis for message-bus architectures that scale to thousands of agents.

---

## Build It · 动手造

`code/main.py` 实现一个由 4 个 worker 线程组成的群体，从共享的 `queue.Queue` 拉任务。任务时长不均（有快有慢）。演示对比：

- **顺序基线：** 一个 worker 串行处理所有任务。
- **固定指派：** 每个任务预先指派给特定的 worker（监督者风格）。
- **群体：** worker 从共享队列拉任务。

群体自动均衡负载；固定指派在快 worker 被指派到慢任务时让他们闲着。

Run:

```
python3 code/main.py
```

输出展示每个 worker 的任务数（群体的分布不均但最优）和墙钟时间。

> `code/main.py` implements a swarm of 4 worker threads pulling from a shared `queue.Queue`. Tasks have variable durations (some fast, some slow). The demo contrasts: **Sequential baseline** (one worker processes all tasks serially), **Fixed assignment** (each task pre-assigned to a specific worker, supervisor-style), **Swarm** (workers pull from a shared queue). ... Swarm balances load automatically; fixed assignment leaves fast workers idle when their assigned task is slow. ... Output shows per-worker task counts (swarm distributes unevenly but optimally) and wall-clock times.

---

## Use It · 实战用法

`outputs/skill-swarm-fit.md` 评估一个任务该用群体还是监督者。输入：任务独立性、时长方差、顺序要求、可调试性需求。

> `outputs/skill-swarm-fit.md` evaluates whether a task should use swarm vs supervisor. Inputs: task independence, duration variance, ordering requirements, debuggability needs.

---

## Ship It · 交付

检查清单：

- **带老化的优先队列。** 防止长任务饥饿。
- **worker 幂等。** worker 中途崩溃时，任务可能被拉取不止一次。worker 必须幂等。
- **持久化队列。** 生产环境用 Kafka、Redis Streams 或数据库支持的队列。`queue.Queue` 只存在于内存。
- **按任务的可观测性。** 每个任务有一个 trace ID；每个 worker 用它记录起止。
- **背压。** 如果队列增长快于 worker 消化的速度，让生产者减速。

> Checklist: ... **Priority queue with aging.** Prevent long-task starvation. ... **Worker idempotency.** A task may be pulled more than once if a worker crashes mid-run. Workers must be idempotent. ... **Durable queue.** Use Kafka, Redis Streams, or a database-backed queue for production. `queue.Queue` is in-memory only. ... **Observability per task.** Every task has a trace ID; every worker logs start/end with it. ... **Back-pressure.** If the queue grows faster than workers drain it, slow the producer.

---

## Exercises · 练习

1. 跑 `code/main.py`。在时长不均的负载上，群体比顺序快多少？比固定指派快多少？
2. 加一个优先队列变体（用 `queue.PriorityQueue`）。按任务的「重要性」字段分配优先级。观察持续负载下低优先级任务是否会饥饿。
3. 实现一个热点检测器：当任何 worker 处理的任务数达到最慢 worker 的 3 倍时记录日志。这对任务时长分布说明了什么？
4. 读 Matrix 论文（arXiv:2511.21686）的摘要和第 3 节。指出 Matrix 接受的一个具体代价（可扩展性收益）和它放弃的一个（可追溯性、确定性）。
5. 把群体演示改成使用装 (task_type, payload) 元组的 `queue.Queue`，worker 只订阅特定的类型。任务异构时，什么样的路由规则合理？

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Swarm architecture | 「去中心化智能体」 | worker 从共享队列拉任务；没有中央编排者。 |
| Event bus | 「智能体订阅主题」 | 按类型或内容把任务路由给 worker 的消息中间件。 |
| Starvation | 「任务永远不跑」 | 高优先级工作不断到来，低优先级任务永远轮不到。 |
| Hot-spotting | 「一个 worker 被淹死了」 | 一个 worker 拿到大多数任务的负载不均。 |
| Back-pressure | 「让生产者减速」 | 队列填满时通知上游停止生产的机制。 |
| Idempotent worker | 「重跑安全」 | 同一任务处理两次结果相同。必须如此，因为 worker 可能中途崩溃。 |
| Durable queue | 「崩溃后还在」 | 由磁盘或复制存储支持的队列；worker 崩溃时任务不丢。 |
| Matrix framework | 「纯消息传递群体」 | 数据流和控制流都是分布式队列上的序列化消息。 |

---

## Further Reading · 延伸阅读

- [LangGraph workflows and agents — Swarm Architecture](https://docs.langchain.com/oss/python/langgraph/workflows-agents) —— 显式的群体支持
- [Matrix — A Decentralized Framework for Multi-Agent Systems](https://arxiv.org/abs/2511.21686) —— 纯消息传递群体
- [Anthropic engineering — why supervisor not swarm in Research](https://www.anthropic.com/engineering/multi-agent-research-system) —— 一个具体生产系统为什么明确选监督者而不是群体
- [AutoGen v0.4 actor-model docs](https://microsoft.github.io/autogen/stable/) —— 事件驱动的 actor 重写，比 v0.2 的 GroupChat 更接近群体
