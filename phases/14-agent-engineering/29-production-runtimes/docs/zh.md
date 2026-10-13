# Production Runtimes: Queue, Event, Cron · 生产级运行时：队列、事件、定时

生产级智能体跑在六种运行时形态上：请求-响应（request-response）、流式（streaming）、持久化执行（durable execution）、基于队列的后台任务、事件驱动（event-driven）、定时调度（scheduled）。先选形态，再选框架。可观测性在每种形态上都是承重墙。

> Production agents run on six runtime shapes: request-response, streaming, durable execution, queue-based background, event-driven, and scheduled. Pick the shape before you pick the framework. Observability is load-bearing at every shape.

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 13 (LangGraph), Phase 14 · 22 (Voice)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 说出六种生产运行时形态，并把每种匹配到一个框架 / 产品模式。
- 解释为什么持久化执行（durable execution，LangGraph）对长程任务至关重要。
- 描述事件驱动运行时，以及 Claude Managed Agents 适用于什么场合。
- 解释「可观测性即承重墙」这个论断对多步智能体的意义。

> Name the six production runtime shapes and match each to a framework / product pattern.
> Explain why durable execution (LangGraph) matters for long-horizon tasks.
> Describe the event-driven runtime and when Claude Managed Agents fits.
> Explain the observability-as-load-bearing claim for multi-step agents.

## The Problem · 问题在哪

生产级智能体的失败方式，是 Jupyter notebook 暴露不了的：第 37 步网络超时、用户在语音通话中途挂断、cron 任务在机器重启后死掉、后台 worker 内存耗尽。运行时形态决定了哪些失败是可存活的。

> Production agents fail in ways a Jupyter notebook doesn't surface: network timeouts at step 37, user hangs up mid-voice call, cron job dies on machine reboot, background worker runs out of memory. The runtime shape determines which failures are survivable.

## The Concept · 概念

### Request-response · 请求-响应

- 同步 HTTP。用户等待完成。
- 只适用于短任务（<30s）。
- 技术栈：Agno（Python + FastAPI）、Mastra（TypeScript + Express/Hono/Fastify/Koa）。
- 可观测性：标准 HTTP 访问日志 + OTel span。

> Synchronous HTTP. User waits for completion.
> Only viable for short tasks (<30s).
> Stacks: Agno (Python + FastAPI), Mastra (TypeScript + Express/Hono/Fastify/Koa).

### Streaming · 流式

- 用 SSE 或 WebSocket 做渐进式输出。
- LiveKit 把它扩展到 WebRTC，支持语音/视频（第 22 课）。
- 技术栈：任何支持流式的框架 + 一个能处理 SSE/WS 的前端。
- 可观测性：逐 chunk 计时、首 token 延迟、尾延迟。

> SSE or WebSocket for progressive output.
> LiveKit extends this to WebRTC for voice/video (Lesson 22).
> Observability: per-chunk timing, first-token latency, tail latency.

### Durable execution · 持久化执行

- 每一步之后都做状态 checkpoint；失败后自动恢复。
- AutoGen v0.4 的 actor 模型把故障隔离到单个智能体（第 14 课）。
- LangGraph 的核心差异点（第 13 课）。
- 当步数未知、恢复成本又高时，这必不可少。

> State checkpointed after every step; auto-resumes on failure.
> AutoGen v0.4 actor model isolates failures to one agent (Lesson 14).
> LangGraph's core differentiator (Lesson 13).
> Essential when step count is unknown and recovery cost is high.

### Queue-based / background · 基于队列 / 后台

- 任务进入队列，worker 认领，结果经 webhook 或 pub/sub 流回。
- 对长程智能体必不可少（按 Anthropic 的 computer use 公告，每个任务几十到几百步）。
- 技术栈：Celery（Python）、BullMQ（Node）、SQS + Lambda（AWS）、自研。
- 可观测性：队列深度、单任务延迟分布、DLQ 大小。

> Job enters a queue, workers pick up, results flow back via webhooks or pub/sub.
> Essential for long-horizon agents (dozens-to-hundreds of steps per task, per Anthropic's computer use announcement).
> Observability: queue depth, per-job latency distribution, DLQ size.

### Event-driven · 事件驱动

- 智能体订阅触发器：新邮件、PR 打开、cron 触发。
- Claude Managed Agents 开箱即用地覆盖了这一形态（第 17 课）。
- CrewAI Flows（第 15 课）把事件驱动的确定性工作流结构化。
- 可观测性：触发源、事件到启动的延迟、智能体延迟。

> Agents subscribe to triggers: new email, PR opened, cron fire.
> Claude Managed Agents covers this out of the box (Lesson 17).
> CrewAI Flows (Lesson 15) structures event-driven deterministic workflows.

### Scheduled · 定时调度

- cron 形态的智能体，周期性运行。
- 与持久化执行结合，让失败的夜间任务在下个 tick 续跑。
- 技术栈：Kubernetes CronJob + 一个持久化框架；托管服务（Render cron、Vercel cron）。

> Cron-shaped agents that run periodically.
> Combine with durable execution so a failing nightly run resumes next tick.
> Stacks: Kubernetes CronJob + a durable framework; hosted (Render cron, Vercel cron).

### 2026 deployment patterns · 2026 年的部署模式

- **CrewAI Flows** 用于事件驱动的生产环境。
- **Agno** 无状态 FastAPI 用于 Python 微服务。
- **Mastra** 服务器适配器（Express、Hono、Fastify、Koa）用于嵌入。
- **Pipecat Cloud / LiveKit Cloud** 用于托管语音（第 22 课）。
- **Claude Managed Agents** 用于托管的长时异步任务。

> CrewAI Flows for event-driven production.
> Agno stateless FastAPI for Python microservices.
> Mastra server adapters (Express, Hono, Fastify, Koa) for embedding.
> Pipecat Cloud / LiveKit Cloud for managed voice (Lesson 22).
> Claude Managed Agents for hosted long-running async.

### Observability is load-bearing · 可观测性是承重墙

没有 OpenTelemetry GenAI span（第 23 课）加一个 Langfuse/Phoenix/Opik 后端（第 24 课），你无法调试一个在第 40 步失败的多步智能体。这在生产里不是可选项。它是「我们调试很快」与「我们带着更多日志从头重放」之间的区别。

> Without OpenTelemetry GenAI spans (Lesson 23) plus a Langfuse/Phoenix/Opik backend (Lesson 24), you cannot debug a multi-step agent that failed at step 40. This is not optional for production. It's the difference between "we debug fast" and "we replay from scratch with more logging."

### Where production runtimes fail · 生产运行时哪里会失败

- **形态选错。** 给一个 5 分钟的任务选了 request-response。用户挂断；worker 堆积；重试叠加。
- **没有 DLQ。** 队列 worker 没有死信队列。失败的任务凭空消失。
- **后台工作不透明。** 后台智能体跑着却不导出 trace。失败在用户报告之前不可见。
- **跳过持久化状态。** 任何超过 30 秒、你又承受不起重启的运行，都需要持久化执行。

> Wrong shape choice. Picking request-response for a 5-minute task. Users hang up; workers pile up; retries compound.
> No DLQ. Queue workers without dead-letter. Failed jobs vanish.
> Opaque background work. Background agent runs without trace export. Failures are invisible until the user reports them.
> Skipping durable state. Any run > 30 seconds where you can't afford to restart needs durable execution.

```figure
wb-runtime-shapes
```

## Build It · 动手造

`code/main.py` 是一个 stdlib 多形态演示：

- 请求-响应端点（普通函数）。
- 流式 handler（生成器）。
- 带 DLQ 的队列 worker。
- 事件触发器注册表。
- cron 形态的调度器。

运行：

```bash
python3 code/main.py
```

输出：五条 trace，展示每种形态在同一任务上的行为。同一套智能体逻辑，不同的外壳。第六种形态（持久化执行）刻意留在第 13 课，用 LangGraph 的 checkpointing 讲。

> Output: five traces showing each shape's behavior on the same task. Same agent logic, different outer shells. Durable execution (the sixth shape) is intentionally covered in Lesson 13 with LangGraph checkpointing.

## Use It · 实战用法

- **请求-响应** 用于聊天式 UX。
- **流式** 用于渐进式响应。
- **持久化** 用于长程任务。
- **队列** 用于批量 / 异步 / 长时运行。
- **事件** 用于智能体的反应能力。
- **Cron** 用于日常维护（记忆整合、评估、成本报告）。

> Request-response for chat-style UX.
> Streaming for progressive responses.
> Durable for long-horizon tasks.
> Queue for batch / async / long-running.
> Event for agent reactivity.
> Cron for housekeeping (memory consolidation, evals, cost reports).

## Ship It · 交付

`outputs/skill-runtime-shape.md` 为一个任务选出运行时形态，并把可观测性要求接线到位。

> `outputs/skill-runtime-shape.md` picks a runtime shape for a task and wires the observability requirements.

## Exercises · 练习

1. 把你的第 01 课 ReAct 循环移植到你技术栈的全部六种形态上。哪种形态适合哪种产品表面？
2. 给基于队列的演示加一个 DLQ。模拟 10% 的任务失败；把 DLQ 大小暴露出来。
3. 写一个 cron 触发的评估智能体，每晚对当天前 20 条轨迹运行。
4. 实现带背压（backpressure）的流式：客户端慢时暂停智能体。这和回合预算（turn budget）如何互相影响？
5. 阅读 Claude Managed Agents 文档。什么情况下你会把自托管的长程智能体迁到托管服务？

> Port your Lesson 01 ReAct loop to all six shapes in your stack. Which shape fits which product surface?
> Add a DLQ to the queue-based demo. Simulate 10% job failure; surface DLQ size.
> Implement streaming with backpressure: if the client is slow, pause the agent. How does this interact with a turn budget?

## Key Terms · 术语表

| Term 术语 | What people say 大家怎么说 | What it actually means 实际含义 |
|------|------------------------|------------------------|
| Request-response（请求-响应） | 「同步」 | 用户等待；只适合短任务 |
| Streaming（流式） | 「SSE / WS」 | 渐进式输出；更好的 UX；延迟可逐 chunk 观测 |
| Durable execution（持久化执行） | 「从失败处恢复」 | 状态有 checkpoint；从最后一步重启 |
| Queue-based（基于队列） | 「后台任务」 | 生产者 / worker 池 / DLQ |
| Event-driven（事件驱动） | 「触发器驱动」 | 智能体响应外部事件 |
| DLQ（死信队列） | 「dead-letter queue」 | 失败任务的停车场 |
| Claude Managed Agents | 「托管 harness」 | Anthropic 托管的长时异步，带缓存 + 压缩 |

## Further Reading · 延伸阅读

- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) —— 持久化执行的细节
- [Claude Managed Agents overview](https://platform.claude.com/docs/en/managed-agents/overview) —— 托管的长时异步
- [Anthropic, Introducing computer use](https://www.anthropic.com/news/3-5-models-and-computer-use) —— 「每个任务几十到几百步」
- [AutoGen v0.4 (Microsoft Research)](https://www.microsoft.com/en-us/research/articles/autogen-v0-4-reimagining-the-foundation-of-agentic-ai-for-scale-extensibility-and-robustness/) —— actor 模型的故障隔离
