# OpenAI Agents SDK: Handoffs, Guardrails, Tracing · OpenAI Agents SDK：Handoff、Guardrail、Tracing

> OpenAI Agents SDK is the lightweight multi-agent framework built on the Responses API. Five primitives: Agent, Handoff, Guardrail, Session, Tracing. Handoffs are tools named `transfer_to_<agent>`. Guardrails trip on input or output. Tracing is on by default.

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 06 (Tool Use)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 说出 OpenAI Agents SDK 的五个原语
- 解释 handoff：为什么建模成工具、模型看到的名字形状是什么、上下文如何转移
- 区分输入护栏（input guardrail）、输出护栏（output guardrail）和工具护栏（tool guardrail）；解释 `run_in_parallel` 与阻塞模式
- 实现一个带 handoff + 护栏 + span 风格 tracing 的 stdlib 运行时

> Name the five primitives of the OpenAI Agents SDK.
> Explain handoffs: why they are modeled as tools, what name shape the model sees, and how context transfers.
> Distinguish input guardrails, output guardrails, and tool guardrails; explain `run_in_parallel` vs blocking mode.
> Implement a stdlib runtime with handoffs + guardrails + span-style tracing.

## The Problem · 问题在哪

不能干净委托的 agent，最后会把一切都塞进一个 prompt。没有护栏的 agent，会把 PII、违反政策的输出发出去，或者永远循环。OpenAI 的 SDK 把让多 agent 工作变得可控的那三个原语成文化了。

> Agents that cannot delegate cleanly end up stuffing everything into one prompt. Agents without guardrails ship PII, policy-violating output, or loop forever. OpenAI's SDK codifies the three primitives that make multi-agent work tractable.

## The Concept · 概念

### Five primitives · 五个原语

1. **Agent。** LLM + instructions + tools + handoffs。
2. **Handoff。** 委托给另一个 agent。对模型呈现为一个名为 `transfer_to_<agent_name>` 的工具。
3. **Guardrail（护栏）。** 作用于输入（仅首个 agent）、输出（仅最后一个 agent）或工具调用（每个 function tool）之上的校验。
4. **Session（会话）。** 跨轮次的自动对话历史。
5. **Tracing（追踪）。** 内置 span，覆盖 LLM 生成、工具调用、handoff、护栏。

> **Agent.** LLM + instructions + tools + handoffs.
> **Handoff.** Delegation to another agent. Represented to the model as a tool named `transfer_to_<agent_name>`.
> **Guardrail.** Validation on input (first agent only), output (last agent only), or tool invocation (per function tool).
> **Session.** Automatic conversation history across turns.
> **Tracing.** Built-in spans for LLM generations, tool calls, handoffs, guardrails.

### Handoffs as tools · 作为工具的 handoff

模型在它的工具列表里看到 `transfer_to_billing_agent`。调用它等于向运行时发出信号：

1. 复制对话上下文（或者通过 `nest_handoff_history` beta 把它折叠起来）。
2. 用目标 agent 自己的 instructions 初始化它。
3. 由目标 agent 继续这次运行。

这就是 supervisor 模式（Lesson 13 / Lesson 28）的产品化。

> The model sees `transfer_to_billing_agent` in its tool list. Calling it signals the runtime to:
> 1. Copy the conversation context (or collapse it via `nest_handoff_history` beta).
> 2. Initialize the target agent with its instructions.
> 3. Continue the run with the target agent.
> This is the supervisor pattern (Lesson 13 / Lesson 28) productized.

### Guardrails · 护栏

三种口味：

- **输入护栏。** 作用于首个 agent 的输入。在任何 LLM 调用之前，拒绝不安全或超出范围的请求。
- **输出护栏。** 作用于最后一个 agent 的输出。抓 PII 泄漏、政策违规、格式损坏的响应。
- **工具护栏。** 按 function tool 生效。校验参数、检查权限、审计执行。

模式：

- **并行（Parallel）**（默认）。护栏 LLM 与主 LLM 并排跑。尾部延迟更低。一旦触发（trip），主 LLM 的工作就被丢弃（浪费 token）。
- **阻塞（Blocking）**（`run_in_parallel=False`）。护栏 LLM 先跑。一旦触发，主调用一个 token 都不浪费。

触发时抛出 `InputGuardrailTripwireTriggered` / `OutputGuardrailTripwireTriggered`。

> **Input guardrails.** Run on the first agent's input. Reject unsafe or out-of-scope requests before any LLM call.
> **Output guardrails.** Run on the last agent's output. Catch PII leaks, policy violations, malformed responses.
> **Tool guardrails.** Run per-function-tool. Validate arguments, check permissions, audit execution.
> **Parallel** (default). Guardrail LLM runs alongside the main LLM. Lower tail latency. If tripped, the main LLM's work is discarded (token waste).
> **Blocking** (`run_in_parallel=False`). Guardrail LLM runs first. If tripped, no tokens wasted on the main call.
> Tripwires raise `InputGuardrailTripwireTriggered` / `OutputGuardrailTripwireTriggered`.

### Tracing · 追踪

默认开启。每一次 LLM 生成、工具调用、handoff、护栏都发一个 span。`OPENAI_AGENTS_DISABLE_TRACING=1` 可以关掉。`add_trace_processor(processor)` 把 span 顺着发给自己的后端，与 OpenAI 的并行不悖。

> On by default. Every LLM generation, tool call, handoff, and guardrail emits a span. `OPENAI_AGENTS_DISABLE_TRACING=1` opts out. `add_trace_processor(processor)` fans spans to your own backend alongside OpenAI's.

### Sessions · 会话

`Session` 把对话历史存在一个后端里（SQLite、Redis、自定义）。`Runner.run(agent, input, session=session)` 自动加载并追加。

> `Session` stores conversation history in a backend (SQLite, Redis, custom). `Runner.run(agent, input, session=session)` auto-loads and appends.

### Where this pattern goes wrong · 这个模式哪里会出错

- **handoff 漂移。** Agent A 交接给 Agent B，B 又交回给 A。加一个跳数计数器。
- **护栏绕过。** 工具护栏只对 function tool 生效；内置工具（文件读取、网页抓取）需要单独的政策。
- **过度追踪。** span 里混进了敏感内容。配合 OTel GenAI 内容捕获规则（Lesson 23）——内容外置存储，用 ID 引用。

```figure
ae-agent-handoff
```

> **Handoff drift.** Agent A hands off to Agent B which hands back to Agent A. Add a hop counter.
> **Guardrail bypass.** Tool guardrails only fire on function tools; built-in tools (file reader, web fetch) need separate policy.
> **Over-tracing.** Sensitive content in spans. Pair with OTel GenAI content-capture rules (Lesson 23) — store externally, reference by ID.

## Build It · 动手造

`code/main.py` 用 stdlib 实现 SDK 的形状：

- `Agent`、`FunctionTool`、`Handoff`（作为带转移语义的 function tool）。
- `Runner`，带输入/输出/工具护栏、handoff 分发和跳数计数器。
- 一个简单的 span 发射器，展示 trace 的形状。
- 一个 triage agent，根据用户查询交接给 billing 或 support；护栏在其中一条输入上触发。

运行：

```
python3 code/main.py
```

轨迹展示了两次成功的 handoff、一次输入护栏触发，以及一棵与真实 SDK 发出的形状相对应的 span 树。

> The trace shows two successful handoffs, one input guardrail trip, and a span tree mirroring what the real SDK emits.

## Use It · 实战用法

- **OpenAI Agents SDK** 给 OpenAI 优先的产品。
- **Claude Agent SDK**（Lesson 17）给 Claude 优先的产品。
- **LangGraph**（Lesson 13）当你想要显式状态和持久恢复时。
- **自建** 当你需要精确控制（语音、多供应商、联邦部署）时。

> **OpenAI Agents SDK** for OpenAI-first products.
> **Claude Agent SDK** (Lesson 17) for Claude-first products.
> **LangGraph** (Lesson 13) when you want explicit state and durable resume.
> **Custom** when you need exact control (voice, multi-provider, federated deployments).

## Ship It · 交付

`outputs/skill-agents-sdk-scaffold.md` 搭出一个 Agents SDK 应用：一个 triage agent、handoff、输入/输出/工具护栏、会话存储和一个 trace processor。

> `outputs/skill-agents-sdk-scaffold.md` scaffolds an Agents SDK app with a triage agent, handoffs, input/output/tool guardrails, session store, and a trace processor.

## Exercises · 练习

1. 加一个 handoff 跳数计数器：超过 N 次转移就拒绝。把行为轨迹打出来。
2. 把 `nest_handoff_history` 实现成一个可选项——交接之前把先前的消息折叠成一条摘要。
3. 写一个阻塞式输出护栏。对比「会触发它的 prompt」与「能通过的 prompt」的延迟。
4. 把 `add_trace_processor` 接到一个 JSON logger。每个 span 发出的形状是什么？
5. 读 SDK 文档。把你的 stdlib 玩具移植到 `openai-agents-python`。你把什么东西建模错了？

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| Agent | 「LLM + instructions」 | SDK 里的 Agent 类型；持有工具和 handoff |
| Handoff | 「转移」 | 模型调用来委托另一个 agent 的工具 |
| Guardrail | 「政策检查」 | 作用于输入 / 输出 / 工具调用的校验 |
| Tripwire | 「护栏触发」 | 护栏拒绝时抛出的异常 |
| Session | 「历史存储」 | 跨运行持久化的对话记忆 |
| Tracing | 「span」 | 覆盖 LLM + 工具 + handoff + 护栏的内置可观测性 |
| Blocking guardrail（阻塞护栏） | 「顺序检查」 | 护栏先跑；触发时不浪费 token |
| Parallel guardrail（并行护栏） | 「并发检查」 | 护栏并排跑；延迟更低，触发时浪费 token |

## Further Reading · 延伸阅读

- [OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/) —— 原语、handoff、护栏、tracing
- [Claude Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview) —— Claude 风味的对应物
- [Anthropic, Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) —— 到底什么时候才需要 handoff
- [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) —— Agents SDK 的 span 所对标的标准
