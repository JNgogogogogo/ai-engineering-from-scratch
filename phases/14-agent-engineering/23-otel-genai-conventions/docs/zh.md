# OpenTelemetry GenAI Semantic Conventions · OpenTelemetry GenAI 语义约定

> OpenTelemetry 的 GenAI SIG（2024 年 4 月成立）定义了 agent 遥测的标准 schema。span 命名、属性和内容捕获规则在众多厂商之间收敛，于是 agent 的 trace 在 Datadog、Grafana、Jaeger 和 Honeycomb 里意味着同一件事。
>
> OpenTelemetry's GenAI SIG (launched April 2024) defines the standard schema for agent telemetry. Span names, attributes, and content-capture rules converge across vendors so agent traces mean the same thing in Datadog, Grafana, Jaeger, and Honeycomb.

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 13 (LangGraph), Phase 14 · 24 (Observability Platforms)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 说出 GenAI 的 span 类别：model/client、agent、tool。
- 区分 `invoke_agent` 的 CLIENT 与 INTERNAL span，以及各自的适用时机。
- 列出顶层 GenAI 属性：provider name、request model、data-source ID。
- 解释内容捕获契约：opt-in、`OTEL_SEMCONV_STABILITY_OPT_IN`、外部引用建议。

> Name the GenAI span categories: model/client, agent, tool.
> Distinguish `invoke_agent` CLIENT vs INTERNAL spans and when each applies.
> List the top-level GenAI attributes: provider name, request model, data-source ID.
> Explain the content-capture contract: opt-in, `OTEL_SEMCONV_STABILITY_OPT_IN`, external-reference recommendation.

## The Problem · 问题在哪

每家厂商都发明自己的 span 命名。运维团队最后只能给每个框架单独搭一套仪表盘。OpenTelemetry 的 GenAI SIG 解决了这个问题：定义一个整个生态都对齐的标准。

> Every vendor invents their own span names. Ops teams end up building per-framework dashboards. OpenTelemetry's GenAI SIG fixes this by defining one standard the whole ecosystem targets.

## The Concept · 概念

### Span categories · Span 类别

1. **Model / client span。** 覆盖裸 LLM 调用。由提供商 SDK（Anthropic、OpenAI、Bedrock）和框架的模型适配器发出。
2. **Agent span。** `create_agent`（agent 被构建时）和 `invoke_agent`（agent 运行时）。
3. **Tool span。** 每次工具调用一个；通过父子关系挂到 agent span 上。

> 1. **Model / client spans.** Cover raw LLM calls. Emitted by provider SDKs (Anthropic, OpenAI, Bedrock) and framework model adapters.
> 2. **Agent spans.** `create_agent` (when the agent is constructed) and `invoke_agent` (when it runs).
> 3. **Tool spans.** One per tool invocation; connected to the agent span by parent-child relation.

### Agent span naming · Agent span 命名

- Span 名称：agent 有名字时用 `invoke_agent {gen_ai.agent.name}`；否则回退到 `invoke_agent`。
- Span kind：
  - **CLIENT** —— 远程 agent 服务（OpenAI Assistants API、Bedrock Agents）。
  - **INTERNAL** —— 进程内的 agent 框架（LangChain、CrewAI、本地 ReAct）。

> - Span name: `invoke_agent {gen_ai.agent.name}` if named; fallback to `invoke_agent`.
> - Span kind:
>   - **CLIENT** — for remote agent services (OpenAI Assistants API, Bedrock Agents).
>   - **INTERNAL** — for in-process agent frameworks (LangChain, CrewAI, local ReAct).

### Key attributes · 关键属性

- `gen_ai.provider.name` —— `anthropic`、`openai`、`aws.bedrock`、`google.vertex`。
- `gen_ai.request.model` —— 模型 ID。
- `gen_ai.response.model` —— 实际解析出的模型（因路由可能与请求的不同）。
- `gen_ai.agent.name` —— agent 标识。
- `gen_ai.operation.name` —— `chat`、`completion`、`invoke_agent`、`tool_call`。
- `gen_ai.data_source.id` —— RAG 场景：查的是哪个语料库或存储。

> - `gen_ai.provider.name` — `anthropic`, `openai`, `aws.bedrock`, `google.vertex`.
> - `gen_ai.request.model` — the model ID.
> - `gen_ai.response.model` — the resolved model (may differ from request due to routing).
> - `gen_ai.agent.name` — agent identifier.
> - `gen_ai.operation.name` — `chat`, `completion`, `invoke_agent`, `tool_call`.
> - `gen_ai.data_source.id` — for RAG: which corpus or store was consulted.

针对 Anthropic、Azure AI Inference、AWS Bedrock、OpenAI 还有各自的技术专属约定。

> Technology-specific conventions exist for Anthropic, Azure AI Inference, AWS Bedrock, OpenAI.

### Content capture · 内容捕获

默认规则：instrumentation 默认不应该（SHOULD NOT）捕获输入/输出。捕获是 opt-in 的，通过：

- `gen_ai.system_instructions`
- `gen_ai.input.messages`
- `gen_ai.output.messages`

> The default rule: instrumentations SHOULD NOT capture inputs/outputs by default. Capture is opt-in via:
> - `gen_ai.system_instructions`
> - `gen_ai.input.messages`
> - `gen_ai.output.messages`

推荐的生产模式：把内容存到外部（S3、你自己的日志存储），span 上只记录引用（指针 ID，不是正文）。这正是第 27 课内容投毒防御在可观测性上的接线方式。

> Recommended production pattern: store content externally (S3, your log store), record references on spans (pointer IDs, not prose). This is the Lesson 27 content-poisoning defense wired into observability.

### Stability · 稳定性

截至 2026 年 3 月，大部分约定仍处于实验性（experimental）阶段。用下面这个开关加入稳定预览：

```
OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental
```

> Most conventions are experimental as of March 2026. Opt in to the stable preview with:

Datadog v1.37+ 把 GenAI 属性原生映射进它的 LLM Observability schema。其他后端（Grafana、Honeycomb、Jaeger）支持原始属性。

> Datadog v1.37+ maps GenAI attributes natively into its LLM Observability schema. Other backends (Grafana, Honeycomb, Jaeger) support the raw attributes.

### Where this pattern goes wrong · 这个模式的常见坑

- **把完整 prompt 塞进 span。** PII、密钥、客户数据躺在运维都能读的 trace 里。请存外部。
- **不设 `gen_ai.provider.name`。** 归因缺失时，多提供商仪表盘直接报废。
- **span 没有父链接。** 孤儿 tool span。永远传播上下文。
- **不设稳定性 opt-in。** 后端一升级，你的属性可能就被改名了。

> - **Capturing full prompts in spans.** PII, secrets, customer data in traces that ops can read. Store externally.
> - **No `gen_ai.provider.name`.** Multi-provider dashboards break when attribution is missing.
> - **Spans without parent links.** Orphaned tool spans. Always propagate context.
> - **Not setting stability opt-in.** Your attributes may get renamed on backend upgrade.

```figure
ae-genai-span-tree
```

## Build It · 动手造

`code/main.py` 用标准库实现了一个符合 GenAI 约定的 span 发射器：

- 带 GenAI 属性 schema 的 `Span`。
- 带 `start_span` 和嵌套上下文的 `Tracer`。
- 一次脚本化的 agent 运行，发出：`create_agent`、`invoke_agent`（INTERNAL）、逐工具 span、LLM 调用的 `chat` span。
- 一个内容捕获模式：prompt 存外部，span 上只记 ID。

运行：

```
python3 code/main.py
```

> `code/main.py` implements a stdlib span emitter matching GenAI conventions:
> - `Span` with GenAI attribute schema.
> - `Tracer` with `start_span`, nested contexts.
> - A scripted agent run that emits: `create_agent`, `invoke_agent` (INTERNAL), per-tool spans, `chat` spans for LLM calls.
> - A content-capture mode that stores prompts externally and records IDs on spans.

输出：一棵带全部必需 GenAI 属性的 span 树，外加一个展示 opt-in 内容引用的「外部存储」。

> Output: a span tree with all required GenAI attributes, and an "external store" showing the opt-in content references.

## Use It · 实战用法

- **Datadog LLM Observability**（v1.37+）原生映射这些属性。
- **Langfuse / Phoenix / Opik**（第 24 课）—— 对整个生态自动 instrumentation。
- **Jaeger / Honeycomb / Grafana Tempo** —— 原始 OTel trace；用 GenAI 属性搭仪表盘。
- **自托管** —— 跑 OTel Collector，配一个 GenAI processor。

> - **Datadog LLM Observability** (v1.37+) maps attributes natively.
> - **Langfuse / Phoenix / Opik** (Lesson 24) — auto-instrument the ecosystem.
> - **Jaeger / Honeycomb / Grafana Tempo** — raw OTel traces; build dashboards from GenAI attributes.
> - **Self-hosted** — run the OTel Collector with a GenAI processor.

## Ship It · 交付

`outputs/skill-otel-genai.md` 把 OTel GenAI span 接进现有 agent，带内容捕获默认值和外部引用存储。

> `outputs/skill-otel-genai.md` wires OTel GenAI spans into an existing agent with content-capture defaults and external-reference storage.

## Exercises · 练习

1. 给第 01 课的 ReAct 循环做 instrumentation：`invoke_agent`（INTERNAL）+ 逐工具 span。发送到一个 Jaeger 实例。
2. 以「只存引用」模式加内容捕获：prompt 进 SQLite，span 属性只带行 ID。
3. 读 `gen_ai.data_source.id` 的规范。把它接进你第 09 课的 Mem0 搜索。
4. 设置 `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`，验证你的属性不会被 collector 改名。
5. 搭一个仪表盘：仅凭 GenAI 属性回答「哪些工具报错与哪些模型相关」。

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| GenAI SIG | 「OpenTelemetry GenAI 工作组」 | 定义这套 schema 的 OTel 工作组 |
| invoke_agent | 「agent span」 | 代表一次 agent 运行的 span 名称 |
| CLIENT span | 「远程调用」 | 调用远程 agent 服务的 span |
| INTERNAL span | 「进程内」 | 进程内 agent 运行的 span |
| gen_ai.provider.name | 「提供商」 | anthropic / openai / aws.bedrock / google.vertex |
| gen_ai.data_source.id | 「RAG 来源」 | 这次检索命中了哪个语料库/存储 |
| Content capture | 「prompt 日志」 | opt-in 的消息捕获；生产环境请存外部 |
| Stability opt-in | 「预览模式」 | 用来钉住实验性约定的环境变量 |

## Further Reading · 延伸阅读

- [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) —— 规范本体
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) —— 默认发出 GenAI span
- [AutoGen v0.4 (Microsoft Research)](https://www.microsoft.com/en-us/research/articles/autogen-v0-4-reimagining-the-foundation-of-agentic-ai-for-scale-extensibility-and-robustness/) —— 内置 OTel span
- [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview) —— W3C trace context 传播
