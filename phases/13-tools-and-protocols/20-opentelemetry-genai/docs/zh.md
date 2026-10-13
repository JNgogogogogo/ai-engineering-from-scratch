# OpenTelemetry GenAI — Tracing Tool Calls End-to-End · OpenTelemetry GenAI —— 端到端追踪工具调用

> 一个 agent 调用五个工具、三个 MCP 服务器和两个子 agent。你需要一条贯穿全部的追踪（trace）。OpenTelemetry GenAI 语义约定（semantic conventions，v1.37 起属性已稳定）是 2026 年的标准，被 Datadog、Langfuse、Arize Phoenix、OpenLLMetry 和 AgentOps 原生支持。本课指名必需属性，走完 span 层级（agent → LLM → 工具），并交付一个可以插入任何 OTel 导出器（exporter）的标准库 span 发射器。
>
> An agent calls five tools, three MCP servers, and two sub-agents. You need one trace across all of it. The OpenTelemetry GenAI semantic conventions (stable attributes in v1.37 and up) are the 2026 standard, natively supported by Datadog, Langfuse, Arize Phoenix, OpenLLMetry, and AgentOps. This lesson names the required attributes, walks the span hierarchy (agent → LLM → tool), and ships a stdlib span emitter you can plug into any OTel exporter.

**Type:** Build
**Languages:** Python (stdlib, OTel span emitter)
**Prerequisites:** Phase 13 · 07 (MCP server), Phase 13 · 08 (MCP client)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 说出 LLM span 与工具执行 span 所需的 OTel GenAI 属性
- 构建一个覆盖 agent 循环、LLM 调用、工具调用与 MCP 客户端分发的追踪层级
- 决定捕获哪些内容（opt-in）与脱敏哪些内容（默认）
- 把 span 发射到本地收集器（Jaeger、Langfuse），而无需改写工具代码

> Name the required OTel GenAI attributes for an LLM span and a tool-execution span.
> Build a trace hierarchy that covers agent loop, LLM call, tool call, and MCP client dispatch.
> Decide what content to capture (opt-in) vs redact (defaults).
> Emit spans to a local collector (Jaeger, Langfuse) without rewriting tool code.

## The Problem · 问题在哪

2026 年 2 月的一次调试：用户报告「我的 agent 有时要 30 秒才响应，有时 3 秒。」没有任何追踪。日志显示了 LLM 调用，但没有工具分发，没有 MCP 服务器往返，也没有子 agent。你只能猜。最终你发现：某个 MCP 服务器在冷启动时偶尔会挂起。

没有端到端追踪，你找不到这种问题。OTel GenAI 就是修这个的。

这些约定在 2025-2026 年间于 OpenTelemetry semantic-conventions 小组下定稿。它们定义稳定的属性名，让 Datadog、Langfuse、Phoenix、OpenLLMetry 和 AgentOps 都能解析同样的 span。做一次埋点；发送到任何后端。

> A debug from February 2026: user reports "my agent sometimes takes 30 seconds to respond; other times 3 seconds." No traces. Logs show the LLM call, but not the tool dispatch, not the MCP server round-trip, not the sub-agent. You guess. Eventually you find: one MCP server occasionally hangs on a cold-start.
> Without end-to-end tracing, you cannot find this. OTel GenAI fixes it.
> The conventions settled in 2025-2026 under the OpenTelemetry semantic-conventions group. They define stable attribute names so Datadog, Langfuse, Phoenix, OpenLLMetry, and AgentOps all parse the same spans. Instrument once; ship to any backend.

## The Concept · 概念

### Span hierarchy · Span 层级

```
agent.invoke_agent  (top, INTERNAL span)
 ├── llm.chat       (CLIENT span)
 ├── tool.execute   (INTERNAL)
 │    └── mcp.call  (CLIENT span)
 ├── llm.chat       (CLIENT span)
 └── subagent.invoke (INTERNAL)
```

这一切都嵌套在同一个 trace id 之下。Span id 把父子关系链接起来。

> The whole thing nests under one trace id. Span ids link the parent-child relationships.

### Required attributes · 必需属性

按 2025-2026 语义约定（semconv）：

- `gen_ai.operation.name` —— `"chat"`、`"text_completion"`、`"embeddings"`、`"execute_tool"`、`"invoke_agent"`。
- `gen_ai.provider.name` —— `"openai"`、`"anthropic"`、`"google"`、`"azure_openai"`。
- `gen_ai.request.model` —— 请求的模型字符串（例如 `"gpt-4o-2024-08-06"`）。
- `gen_ai.response.model` —— 实际服务的模型。
- `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens`。
- `gen_ai.response.id` —— 用于关联的提供方响应 id。

工具 span：

- `gen_ai.tool.name` —— 工具标识符。
- `gen_ai.tool.call.id` —— 那次具体调用的 id。
- `gen_ai.tool.description` —— 工具描述（可选）。

agent span：

- `gen_ai.agent.name` / `gen_ai.agent.id` / `gen_ai.agent.description`。

> Per the 2025-2026 semconv:
> `gen_ai.operation.name` — `"chat"`, `"text_completion"`, `"embeddings"`, `"execute_tool"`, `"invoke_agent"`.
> `gen_ai.provider.name` — `"openai"`, `"anthropic"`, `"google"`, `"azure_openai"`.
> `gen_ai.request.model` — requested model string (e.g. `"gpt-4o-2024-08-06"`).
> `gen_ai.response.model` — the model actually served.
> `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens`.
> `gen_ai.response.id` — provider response id for correlation.

### Span kinds · Span 种类

- `SpanKind.CLIENT` 用于跨越进程边界的调用（LLM 提供方、MCP 服务器）。
- `SpanKind.INTERNAL` 用于 agent 自己的循环步骤和工具执行。

> `SpanKind.CLIENT` for calls crossing a process boundary (LLM provider, MCP server).
> `SpanKind.INTERNAL` for the agent's own loop steps and tool execution.

### Opt-in content capture · 可选加入的内容捕获

默认情况下，span 只带指标和计时——不带提示词或补全内容。大载荷与 PII 默认关闭。设置 `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` 和特定的内容捕获环境变量才能包含内容。在生产环境启用之前仔细评估。

> By default, spans carry metrics and timing — not prompts or completions. Large payloads and PII are off by default. Set `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` and specific content-capture env vars to include content. Review carefully before enabling in prod.

### Events on spans · Span 上的事件

Token 级事件可以作为 span event 添加：

- `gen_ai.content.prompt` —— 输入消息。
- `gen_ai.content.completion` —— 输出消息。
- `gen_ai.content.tool_call` —— 记录下来的工具调用。

事件在 span 内按时间排序，可用于详细回放。

> Token-level events can be added as span events:
> `gen_ai.content.prompt` — input messages.
> `gen_ai.content.completion` — output messages.
> `gen_ai.content.tool_call` — tool call as recorded.
> Events time-order within a span for detailed replay.

### Exporters · 导出器（exporters）

OTel span 可以导出到：

- **Jaeger / Tempo。** 开源，可自部署。
- **Langfuse。** 专攻 LLM 可观测性；可视化 token 用量。
- **Arize Phoenix。** 评估（eval）+ 追踪二合一。
- **Datadog。** 商业产品；原生解析 `gen_ai.*` 属性。
- **Honeycomb。** 列式存储；查询友好。

它们都说 OTLP——线上传输格式。你的代码不用关心。

> OTel spans export to:
> **Jaeger / Tempo.** OSS, on-prem.
> **Langfuse.** LLM-observability-specific; visualizes token usage.
> **Arize Phoenix.** Evals + tracing combined.
> **Datadog.** Commercial; natively parses `gen_ai.*` attributes.
> **Honeycomb.** Column-oriented; query-friendly.
> All speak OTLP, the wire format. Your code does not care.

### Propagation across MCP · 跨 MCP 的传播

当 MCP 客户端调用服务器时，把 W3C 的 traceparent 头注入请求。Streamable HTTP 支持标准头。Stdio 原生不携带 HTTP 头；规范的 2026 路线图讨论在 JSON-RPC 调用上添加 `_meta.traceparent` 字段。

在该特性发布之前：手动把 traceparent 放进每个请求的 `_meta` 里。服务器记录这个 trace id。

> When an MCP client calls a server, inject the W3C traceparent header into the request. Streamable HTTP supports standard headers. Stdio does not carry HTTP headers natively; the spec's 2026 roadmap discusses adding a `_meta.traceparent` field on JSON-RPC calls.
> Until that ships: include the traceparent in the `_meta` of every request manually. Server logs the trace id.

### Metrics · 指标（metrics）

与 span 并行，GenAI 语义约定还定义了指标：

- `gen_ai.client.token.usage` —— 直方图（histogram）。
- `gen_ai.client.operation.duration` —— 直方图。
- `gen_ai.tool.execution.duration` —— 直方图。

用它们做不需要每次调用细节的仪表盘。

> Alongside spans, the GenAI semconv defines metrics:
> `gen_ai.client.token.usage` — histogram.
> `gen_ai.client.operation.duration` — histogram.
> `gen_ai.tool.execution.duration` — histogram.
> Use these for dashboards that do not need per-call detail.

### AgentOps layer · AgentOps 层

AgentOps（2024 年成立）专注于 GenAI 可观测性。它包装流行框架（LangGraph、Pydantic AI、CrewAI）来自动发射 OTel span。如果你的技术栈用了被支持的框架，它很方便；否则用手动埋点。

> AgentOps (founded 2024) specializes in GenAI observability. It wraps popular frameworks (LangGraph, Pydantic AI, CrewAI) to emit OTel spans automatically. Useful if your stack uses a supported framework; use manual instrumentation otherwise.

```figure
t3-span-waterfall
```

## Use It · 实战用法

`code/main.py` 向 stdout（以类似 OTLP-JSON 的格式）发射 OTel 形状的 span，场景是一个 agent 调用一次 LLM、分发两个工具，并做一次 MCP 往返。没有真实导出器——本课聚焦 span 形状与属性集合。把输出粘贴进任何 OTLP 兼容的查看器，或者直接阅读。

值得看的地方：

- trace id 在所有 span 间共享。
- 父子链接通过 `parentSpanId` 编码。
- 必需的 `gen_ai.*` 属性都被填充。
- 内容捕获默认关闭；一个场景通过环境变量打开它。

> `code/main.py` emits OTel-shaped spans to stdout (in OTLP-JSON-like format) for an agent that calls an LLM, dispatches two tools, and makes one MCP round-trip. No real exporter — the lesson focuses on the span shape and attribute set. Paste the output into an OTLP-compatible viewer or just read it.
> Trace id is shared across all spans.
> Parent-child links are encoded via `parentSpanId`.
> Required `gen_ai.*` attributes are populated.
> Content capture is off by default; one scenario turns it on via env var.

## Ship It · 交付

本课产出 `outputs/skill-otel-genai-instrumentation.md`。给定一个 agent 代码库，该技能产出一份埋点计划：在哪里加 span、填充哪些属性、以及以哪些导出器为目标。

> This lesson produces `outputs/skill-otel-genai-instrumentation.md`. Given an agent codebase, the skill produces an instrumentation plan: where to add spans, which attributes to populate, and which exporters to target.

## Exercises · 练习

1. 运行 `code/main.py`。数一数 span 的数量，并指出哪个是 CLIENT、哪个是 INTERNAL。
2. 打开内容捕获（环境变量），确认 `gen_ai.content.prompt` 和 `gen_ai.content.completion` 事件出现。注意这对 PII 的影响。
3. 添加工具执行指标 `gen_ai.tool.execution.duration`，并按每次调用发射一个直方图样本。
4. 把一个 traceparent 从父 agent span 传播进 MCP 请求的 `_meta.traceparent` 字段。验证 MCP 服务器会看到同一个 trace id。
5. 阅读 OTel GenAI 语义约定规范。找出语义约定中列出、但本课代码**没有**发射的一个属性。把它加上。

> 1. Run `code/main.py`. Count the spans and identify which is CLIENT vs INTERNAL.
> 2. Turn on content capture (env var) and confirm `gen_ai.content.prompt` and `gen_ai.content.completion` events appear. Note the implications for PII.
> 3. Add the tool-execution metric `gen_ai.tool.execution.duration` and emit it as a histogram sample per call.
> 4. Propagate a traceparent from a parent agent span into an MCP request's `_meta.traceparent` field. Verify the MCP server would see the same trace id.
> 5. Read the OTel GenAI semconv spec. Identify one attribute listed in the semconv that this lesson's code does NOT emit. Add it.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| OTel | 「OpenTelemetry」 | 追踪、指标、日志的开放标准 |
| GenAI semconv | 「GenAI 语义约定」 | LLM / 工具 / agent span 的稳定属性名 |
| `gen_ai.*` | 「属性命名空间」 | 所有 GenAI 属性共享这个前缀 |
| Span | 「一段计时的操作」 | 有开始、结束和属性的工作单元 |
| Trace | 「跨 span 的祖先链」 | 共享同一个 trace id 的 span 树 |
| SpanKind | 「CLIENT / SERVER / INTERNAL」 | 关于 span 方向的提示 |
| OTLP | 「OpenTelemetry Line Protocol」 | 导出器使用的线上传输格式 |
| 可选内容捕获（Opt-in content） | 「提示词 / 补全捕获」 | 默认关闭；用环境变量开启 |
| traceparent | 「W3C 头」 | 跨服务传播追踪上下文 |
| 导出器（Exporter） | 「面向特定后端的发送器」 | 把 span 发到 Jaeger / Datadog 等的组件 |

> | Term | What people say | What it actually means |
> | OTel | "OpenTelemetry" | Open standard for traces, metrics, logs |
> | GenAI semconv | "GenAI semantic conventions" | Stable attribute names for LLM / tool / agent spans |
> | `gen_ai.*` | "The attribute namespace" | All GenAI attributes share this prefix |
> | Span | "Timed operation" | A unit of work with a start, end, and attributes |
> | Trace | "Cross-span ancestry" | Tree of spans sharing a trace id |
> | SpanKind | "CLIENT / SERVER / INTERNAL" | Hints about span direction |
> | OTLP | "OpenTelemetry Line Protocol" | Wire format for exporters |
> | Opt-in content | "Prompt / completion capture" | Off by default; env var to enable |
> | traceparent | "W3C header" | Propagates trace context across services |
> | Exporter | "Backend-specific shipper" | Component that sends spans to Jaeger / Datadog / etc. |

## Further Reading · 延伸阅读

- [OpenTelemetry — GenAI semconv](https://opentelemetry.io/docs/specs/semconv/gen-ai/) —— GenAI span、指标与事件的权威约定
- [OpenTelemetry — GenAI spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/) —— LLM 与工具执行 span 的属性列表
- [OpenTelemetry — GenAI agent spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/) —— agent 级的 `invoke_agent` span
- [open-telemetry/semantic-conventions — GenAI spans](https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-spans.md) —— GitHub 托管的源头文档
- [Datadog — LLM OTel semantic convention](https://www.datadoghq.com/blog/llm-otel-semantic-convention/) —— 生产集成实操
