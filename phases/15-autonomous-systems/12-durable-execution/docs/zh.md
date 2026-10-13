# Long-Running Background Agents: Durable Execution · 长时运行的后台 Agent：持久化执行（Durable Execution）

> Production long-horizon agents do not run in `while True`. Every LLM call becomes an activity with checkpoint, retry, and replay. Temporal's OpenAI Agents SDK integration went GA March 2026. Claude Code Routines (Anthropic) runs scheduled Claude Code invocations without a persistent local process. Sessions pause on human-input, survive deploys, and resume from the latest checkpoint keyed by `thread_id`. Behind the new ergonomics sits an old pattern — workflow orchestration — with one new input: LLM calls as non-deterministic activities that must be deterministically replayed on recovery.

**类型:** Learn（学习）
**语言:** Python（仅标准库；最小化持久化执行状态机）
**前置课程:** Phase 15 · 10（Permission modes）、Phase 15 · 01（Long-horizon agents）
**时间:** ~60 分钟

---

## The Problem · 问题在哪

设想一个要跑四个小时的 agent。它调用三个工具、向用户提示两次、发起四十次 LLM 调用。进行到一半，它所在的主机重启了。会发生什么？

- 在朴素的 `while True` 循环里：一切都丢了。这次运行从头再来。那三次工具调用（带着真实副作用）再次执行。用户被再次要求确认他们早已批准过的事情。四十次 LLM 调用重新计费。
- 在持久化执行下：运行从最近的检查点（checkpoint）恢复。已完成的活动（activity）不会被重新执行；它们的结果从持久化日志里重放（replay）。用户不会被再次要求确认已经批准过的事情。已经发生过的 LLM 调用也不会重新计费。

这和工作流引擎已经交付了十年的模式是同一个（Temporal、Cadence、Uber 的 Cherami）。新的是：LLM 调用现在也成了一种活动——非确定、昂贵、带副作用——而且它们与这个模式严丝合缝。

本课贯穿的主题：长程可靠性会衰减（METR 观察到「35 分钟衰减」——成功率随时长大致按平方律下降）。持久化执行让你能跑出超出可靠性曲线支撑范围的时长——设计对了，这是一种新的安全失败方式；设计错了，就是新的不安全失败方式。

> Consider an agent that runs for four hours. It calls three tools, prompts the user twice, and makes forty LLM calls. Halfway through, the host it is running on reboots. What happens?
> - In a naive `while True` loop: everything is lost. The run restarts from scratch. The three tool calls (with real side effects) execute again. The user is prompted again for things they already approved. Forty LLM calls are re-billed.
> - With durable execution: the run resumes from the most recent checkpoint. Already-completed activities are not re-executed; their results are replayed from the durable log. The user does not re-approve things they already approved. The LLM calls already made are not re-billed.
> This is the same pattern workflow engines have shipped for a decade (Temporal, Cadence, Uber's Cherami). What's new is that LLM calls are now a kind of activity — non-deterministic, expensive, with side effects — and they fit this pattern cleanly.
> The running theme of the lesson: long-horizon reliability decays (METR observes a "35-minute degradation" — success rate drops roughly quadratically with horizon). Durable execution enables runs that are longer than the reliability profile supports, which is a new way to fail safely if the design is right and unsafely if the design is wrong.

---

## The Concept · 概念

### Activities, workflows, and replay · 活动、工作流与重放

- **工作流（Workflow）**：确定性的编排代码。定义活动的顺序、分支、等待。必须保持确定性，才能从事件日志重放而不会出现意料之外的分叉。
- **活动（Activity）**：一个非确定、可能失败的工作单元。LLM 调用、工具调用、文件写入、HTTP 请求。每个活动的输入和（完成后）输出都会被记录。
- **事件日志（Event log）**：持久化的后备存储。每一次活动的开始、完成、失败、重试，以及每一个工作流决策，都被记录在案。
- **重放（Replay）**：恢复时，工作流代码从头重新运行；每个已完成的活动直接返回日志中的结果，不再重新执行。只有尚未完成的活动才真正被运行。

这和 React 针对虚拟 DOM 重新渲染、或 Git 从提交重建工作区是同一个形状。**编排器的确定性，正是让持久化变得廉价的原因。**

> - **Workflow**: deterministic orchestration code. Defines the sequence of activities, the branches, the waits. Must be deterministic so it can be replayed from the event log without surprising divergence.
> - **Activity**: a non-deterministic, potentially failing unit of work. LLM call, tool call, file write, HTTP request. Each activity is logged with its inputs and (once complete) its outputs.
> - **Event log**: the durable backing store. Every activity start, complete, fail, retry, and every workflow decision is recorded.
> - **Replay**: on recovery, the workflow code re-runs from the start; every activity that already completed returns its logged result without re-executing. Only activities that had not completed are actually run.
> This is the same shape as React re-rendering against a virtual DOM, or Git rebuilding a working tree from commits. Determinism in the orchestrator is what makes durability cheap.

### Why LLM calls fit the pattern · 为什么 LLM 调用天然契合这个模式

LLM 调用是：
- 非确定的（temperature > 0；即使 temperature 0 也会随模型版本漂移）。
- 昂贵的（钱和延迟）。
- 可能失败的（限流、超时）。
- 带副作用的（当它们调用工具时）。

这正是活动（activity）的画像。把每一次 LLM 调用包装成活动，你就得到了：带指数退避的重试、跨重启的检查点、以及一条可重放的调试轨迹。

> LLM calls are:
> - Non-deterministic (temperature > 0; even temperature 0 drifts across model versions).
> - Expensive (money and latency).
> - Potentially failing (rate limits, timeouts).
> - Side-effectful (if they invoke tools).
> This is exactly the activity profile. Wrapping every LLM call as an activity gives you retry with exponential backoff, checkpointing across restarts, and a replayable trace for debugging.

### Checkpoints keyed by `thread_id` · 以 `thread_id` 为键的检查点

LangGraph、Microsoft Agent Framework、Cloudflare Durable Objects 和 Claude Code Routines 都收敛到了同一个 API 形状：一个 `thread_id`（或等价物）标识会话；每次状态转移都持久化到后端（默认 PostgreSQL，开发用 SQLite，缓存用 Redis）；恢复时读取最新检查点。

后端的选择很重要：

- **PostgreSQL**：持久、可查询、能挺过部署。LangGraph 的默认。
- **SQLite**：仅限本地开发；跨主机即丢数据。
- **Redis**：快，但除非配置了 AOF/快照，否则是易失的。
- **Cloudflare Durable Objects**：透明的分布式；以唯一键为作用域；存活数小时到数周。

> LangGraph, Microsoft Agent Framework, Cloudflare Durable Objects, and Claude Code Routines all converged on the same API shape: a `thread_id` (or equivalent) identifies the session; each state transition persists to a backend (PostgreSQL default, SQLite for dev, Redis for cache); resume reads the latest checkpoint.
> The backend choice matters:
> - **PostgreSQL**: durable, queryable, survives deploys. Default for LangGraph.
> - **SQLite**: local-dev only; loses data across hosts.
> - **Redis**: fast but ephemeral unless AOF/snapshot configured.
> - **Cloudflare Durable Objects**: transparently distributed; scoped by a unique key; survives for hours to weeks.

### Human-input as a first-class state · 把「等待人工输入」当作一等状态

Propose-then-commit（第 15 课）需要一个持久的「等待人工」状态。工作流暂停，外部队列持有待处理请求，一次批准会让工作流从恰好那个点恢复。没有持久化，这只能是尽力而为（best-effort）；有了持久化，一个隔夜才来的批准，会让工作流在第二天早上接着跑。

> Propose-then-commit (Lesson 15) requires a durable "waiting on human" state. The workflow pauses, the external queue holds the pending request, and an approval resumes from exactly that point. Without durability this is best-effort; with it, an overnight approval arrives and the workflow picks up in the morning.

### The 35-minute degradation · 35 分钟衰减

METR 观察到：所有被测量的 agent 类别，在连续运行约 35 分钟之后都出现可靠性衰减。任务时长翻倍，失败率大致翻两番（平方律）。持久化执行修不了这个问题；它只是让你能跑到可靠性曲线支撑范围之外。安全的做法是把持久化与「重新进入时要求新的一次 HITL」的检查点，以及与预算 kill switch（第 13 课，无论墙钟时间多长都封顶总算力）组合起来。

> METR observed that every agent class measured shows reliability decay beyond ~35 minutes of continuous operation. Doubling the task duration roughly quadruples the failure rate. Durable execution does not fix this; it lets you run longer than the reliability profile supports. The safe pattern is to combine durability with checkpoints that require fresh HITL on re-entry, and with budget kill switches (Lesson 13) that cap total compute regardless of wall-clock time.

### When durable execution is the wrong answer · 什么时候持久化执行是错误的答案

- 运行短于几分钟且没有人工输入。开销 > 收益。
- 严格的只读信息检索。
- 正确性要求在单个上下文窗口内端到端完成的任务（某些推理任务；某些一次性生成）。

```figure
memory-consolidation
```

> - Runs shorter than a few minutes with no human input. Overhead > benefit.
> - Strictly read-only information retrieval.
> - Tasks where correctness requires end-to-end within one context window (some reasoning tasks; some one-shot generation).

---

## Use It · 实战用法

`code/main.py` 用标准库 Python 实现一个最小的持久化执行引擎。它支持：

- `@activity` 装饰器：把输入和输出记录到 JSON 事件日志。
- 一个把活动串起来的工作流函数。
- 一个 `run_or_replay(workflow, event_log)` 函数：重放已完成的活动而不重新执行它们。

驱动脚本模拟一个三活动的工作流，中途崩溃，然后展示 (a) 朴素重试把一切都重新执行，对比 (b) 重放只运行缺失的那个活动。

> `code/main.py` implements a minimal durable-execution engine in stdlib Python. It supports:
> - `@activity` decorator that logs inputs and outputs to a JSON event log.
> - A workflow function that sequences activities.
> - A `run_or_replay(workflow, event_log)` function that replays completed activities without re-executing them.
> The driver simulates a three-activity workflow, crashes halfway through, and shows (a) a naive retry re-executing everything versus (b) a replay running only the missing activity.

---

## Ship It · 交付

`outputs/skill-durable-execution-review.md` 对一个拟议的长时运行 agent 部署做审查，检查其持久化执行的形态是否正确：活动、确定性、检查点后端、人工输入状态，以及「恢复时是否要求 HITL」的策略。

> `outputs/skill-durable-execution-review.md` reviews a proposed long-running agent deployment for correct durable-execution shape: activities, determinism, checkpoint backend, human-input state, and HITL-on-resume policy.

---

## Exercises · 练习

1. 运行 `code/main.py`。观察朴素重试与重放在活动执行次数上的差异。改变崩溃点，展示重放次数随之变化。
2. 把玩具引擎改造成显式使用 `thread_id`。模拟两个共享引擎的并发会话，确认它们的事件日志互不冲突。
3. 取玩具引擎里的一个活动。引入一处非确定性（在工作流决策里放一个墙钟时间戳）。在重放时演示分叉。解释真实引擎如何处理这件事（副作用注册、`Workflow.now()` API）。
4. 读 LangChain 的「Runtime behind production deep agents」文章。列出运行时持久化的每一种状态，并说明每种状态覆盖的是哪种失败模式。
5. 为一个 6 小时的自主编程任务设计检查点策略。你在哪里打检查点？崩溃后恢复长什么样？哪些环节要求新的 HITL？

> 1. Run `code/main.py`. Observe the difference in activity-execution count between naive retry and replay. Change the crash point and show the replay count changes accordingly.
> 2. Convert the toy engine to use `thread_id` explicitly. Simulate two concurrent sessions sharing the engine and confirm their event logs do not collide.
> 3. Take one activity in the toy engine. Introduce a non-determinism (a wall-clock timestamp inside a workflow decision). Demonstrate the divergence on replay. Explain how real engines handle this (side-effect registration, `Workflow.now()` APIs).
> 4. Read the LangChain "Runtime behind production deep agents" post. List every state that the runtime persists and name which failure mode each covers.
> 5. Design a checkpoint policy for a 6-hour autonomous coding task. Where do you checkpoint? What does resume-on-crash look like? What requires fresh HITL?

---

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|---|---|---|
| Workflow | 「agent 的脚本」 | 确定性编排代码；可从事件日志重放 |
| Activity | 「一个步骤」 | 非确定的工作单元（LLM 调用、工具调用）；前后都会记录 |
| Event log | 「后备存储」 | 每次状态转移的持久化记录 |
| Replay | 「恢复」 | 重新运行工作流；已完成的活动返回日志结果而不重新执行 |
| Checkpoint | 「存档点」 | 以 thread_id 为键的持久化状态；恢复时最新者胜 |
| thread_id | 「会话键」 | 为持久化状态划定作用域的标识符 |
| 35-minute degradation | 「可靠性衰减」 | METR：成功率随时长按约平方律下降 |
| Non-determinism | 「重放时漂移」 | 墙钟、随机数、LLM 输出；必须注册为副作用 |

---

## Further Reading · 延伸阅读

- [Anthropic — Claude Code Agent SDK: agent loop](https://code.claude.com/docs/en/agent-sdk/agent-loop) — 预算、轮数与恢复语义。
- [Microsoft — Agent Framework: human-in-the-loop and checkpointing](https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop) — RequestInfoEvent 形状。
- [LangChain — The Runtime Behind Production Deep Agents](https://www.langchain.com/conceptual-guides/runtime-behind-production-deep-agents) — 具体的运行时需求。
- [OpenAI Agents SDK + Temporal integration (Trigger.dev announcement)](https://trigger.dev) — LLM 调用的活动形态。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 35 分钟衰减的出处。
