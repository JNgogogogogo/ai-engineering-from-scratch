# LLM Observability Stack Selection · LLM 可观测性技术栈选型

2026 年的可观测性市场分成两类。开发平台（LangSmith、Langfuse、Comet Opik）把监控与评测（evals）、提示词管理、会话回放打包在一起。网关/埋点工具（Helicone、SigNoz、OpenLLMetry、Phoenix）专注遥测。Langfuse 核心是 MIT 许可，OSS 平衡做得好（免费云版每月 5 万事件）。Phoenix 是 OpenTelemetry 原生，采用 Elastic License 2.0——擅长漂移/RAG 可视化，不适合当持久化的生产后端。Arize AX 用零拷贝 Iceberg/Parquet 集成，宣称比单体可观测性便宜 100 倍。LangSmith 在 LangChain/LangGraph 上领先，$39/用户/月，仅 Enterprise 版可自托管。Helicone 基于代理，15-30 分钟即可接入，免费档每月 10 万请求，但 agent trace 深度不足。常见的生产模式：网关（Helicone/Portkey）+ 评测平台（Phoenix/TruLens），用 OpenTelemetry 粘合。

> The 2026 observability market splits into two categories. Development platforms (LangSmith, Langfuse, Comet Opik) bundle monitoring with evals, prompt management, session replays. Gateway/instrumentation tools (Helicone, SigNoz, OpenLLMetry, Phoenix) focus on telemetry. Langfuse is MIT-licensed core with strong OSS balance (50K events/month free cloud). Phoenix is OpenTelemetry-native under Elastic License 2.0 — excellent for drift/RAG visualization, not a persistent production backend. Arize AX uses zero-copy Iceberg/Parquet integration claiming 100x cheaper than monolithic observability. LangSmith leads for LangChain/LangGraph, $39/user/mo, self-host in Enterprise only. Helicone is proxy-based with 15-30 min setup, 100K req/mo free, but less depth on agent traces. Common production pattern: Gateway (Helicone/Portkey) + eval platform (Phoenix/TruLens) glued by OpenTelemetry.

**Type:** Learn
**Languages:** Python（仅标准库；玩具级 trace 采样模拟器）
**Prerequisites:** Phase 17 · 08（Inference Metrics）、Phase 14（Agent Engineering）
**Time:** ~60 分钟

## Learning Objectives · 学习目标

- 区分开发平台（打包了评测 + 提示 + 会话）与网关/遥测工具（只有 trace + 指标）。
- 把六个主要工具（Langfuse、LangSmith、Phoenix、Arize AX、Helicone、Opik）映射到各自的许可证、定价和最佳适用场景。
- 解释 OpenTelemetry 粘合模式——它让你把网关工具和独立的评测平台组合起来。
- 说出 2026 年的成本分水岭（Arize AX 的零拷贝方案 vs 单体摄取），并给出约 100 倍的量级。

> Distinguish development platforms (bundled: evals + prompts + sessions) from gateway/telemetry tools (traces + metrics only).
> Map six major tools (Langfuse, LangSmith, Phoenix, Arize AX, Helicone, Opik) to their licensing, pricing, and sweet-spot use cases.
> Explain the OpenTelemetry-glue pattern that lets you combine a gateway tool with a separate eval platform.
> Name the 2026 cost differentiator (Arize AX's zero-copy approach vs monolithic ingest) and state the rough 100x multiplier.

## The Problem · 问题在哪

你上线了一个 LLM 功能。它能跑。但你看不到提示失败、工具循环、延迟回退、成本飙涨或提示缓存命中率。你 Google「LLM observability」，得到八个工具，全都声称在三个不同价位上解决同一个问题。

它们解决的不是同一个问题。LangSmith 回答「这条 LangGraph run 为什么失败？」Phoenix 回答「我的 RAG 流水线在漂移吗？」Helicone 回答「哪个应用在烧 token？」Langfuse 回答「我能把整套东西自托管吗？」不同的工具，不同的受众。

选型涉及四个轴：技术栈（LangChain？裸 SDK？多厂商？）、许可证容忍度（只要 MIT？Elastic 可以吗？商业无所谓？）、预算（免费档？$100/月？$1000/月？）、自托管（必须？最好有？绝不？）。

> You shipped an LLM feature. It works. You have no visibility into prompt failures, tool loops, latency regressions, cost spikes, or prompt-cache hit rate. You Google "LLM observability" and get eight tools all claiming they solve the same problem at three different price points.
> They don't solve the same problem. LangSmith answers "why did this LangGraph run fail?" Phoenix answers "is my RAG pipeline drifting?" Helicone answers "which app is burning tokens?" Langfuse answers "can I self-host the whole thing?" Different tools, different audiences.
> Picking involves four axes: stack (LangChain? raw SDK? multi-vendor?), license tolerance (MIT only? Elastic OK? commercial fine?), budget (free tier? $100/mo? $1000/mo?), and self-host (must? nice-to-have? never?).

## The Concept · 概念

### Two categories · 两个品类

**开发平台**把可观测性与评测、提示词管理、数据集版本控制、会话回放打包。你做实验、看哪个提示有效、用数据集回归来检验新提示能否胜过旧赢家。LangSmith、Langfuse、Comet Opik。

**网关/遥测工具**给推理调用埋点——提示、响应、token、延迟、模型、成本。Helicone、SigNoz、OpenLLMetry、Phoenix。极简主义。可以经 OpenTelemetry 与独立的评测工具组合。

> **Development platforms** bundle observability with evals, prompt management, dataset versioning, session replay. You run experiments, see which prompt worked, dataset-regression a new prompt against old winners. LangSmith, Langfuse, Comet Opik.
> **Gateway/telemetry tools** instrument inference calls — prompt, response, tokens, latency, model, cost. Helicone, SigNoz, OpenLLMetry, Phoenix. Minimalist. Can be combined with a separate eval tool via OpenTelemetry.

### Langfuse — OSS balance · Langfuse——OSS 平衡派

- 核心 Apache / MIT 许可；用 Docker 自托管。
- 云免费档：每月 5 万事件。付费：团队版 $29/月。
- 评测、提示管理、trace、数据集。四大开发平台功能都有合理覆盖。
- 最佳场景：想要 LangSmith 级别的功能，但必须自托管或留在 OSS 许可内。

> - Core Apache / MIT licensed; self-host via Docker.
> - Cloud free tier: 50K events/month. Paid: $29/mo for team.
> - Evals, prompt management, traces, datasets. Reasonable coverage of all four dev-platform features.
> - Sweet spot: you want LangSmith-class features but must self-host or stay on OSS license.

### Phoenix (Arize) — telemetry-first, OpenTelemetry-native · Phoenix（Arize）——遥测优先、OpenTelemetry 原生

- Elastic License 2.0；自托管轻而易举。
- 擅长 RAG 与漂移可视化。嵌入空间散点图是一等公民。
- 不是为持久化生产后端设计的——主要面向开发期可观测性。
- 最佳场景：RAG 流水线开发、漂移调试，生产环境配一个独立网关。

> - Elastic License 2.0; self-host trivial.
> - Excellent at RAG and drift visualization. Embedding-space scatter plots shipped as first-class.
> - Not designed as persistent production backend — primarily development-time observability.
> - Sweet spot: RAG pipeline development, drift debugging, pairs with a separate gateway for production.

### Arize AX — the scale play · Arize AX——规模化打法

- 商业产品。经 Iceberg/Parquet 做零拷贝数据湖集成。
- 宣称在规模上比单体可观测性（Datadog 档）便宜约 100 倍。算法是：trace 存在你自己的 S3 Parquet 里，Arize 直接读。
- 最佳场景：日 trace 超 1000 万、已有数据湖、想要 LLM 专属看板但不想付 Datadog 的价格。

> - Commercial. Zero-copy data lake integration via Iceberg/Parquet.
> - Claims ~100x cheaper than monolithic observability (Datadog-class) at scale. The math: you store traces in your own Parquet on S3; Arize reads directly.
> - Sweet spot: >10M traces/day, existing data lake, want LLM-specific dashboards without Datadog pricing.

### LangSmith — LangChain/LangGraph first · LangSmith——LangChain/LangGraph 优先

- 商业产品，$39/用户/月。仅 Enterprise 版可自托管。
- 对 LangChain 和 LangGraph 技术栈是同类最佳。如果两者你都没用，它就没那么吸引人。
- 最佳场景：团队已押注 LangChain、愿意付费。

> - Commercial, $39/user/month. Self-host only on Enterprise.
> - Best-in-class for LangChain and LangGraph stacks. If you are not on either, it is less compelling.
> - Sweet spot: team committed to LangChain, willing to pay.

### Helicone — proxy-based minimum viable · Helicone——基于代理的最小可行

- 把 `OPENAI_API_BASE` 换成 Helicone 代理，15-30 分钟即可接入。
- MIT 许可；免费档每月 10 万请求，付费 $20/月起。
- 自带故障切换、缓存、限流——同时也充当网关。
- agent / 多步 trace 的深度不足。
- 最佳场景：快速起步、单一技术栈应用、需要网关 + 可观测性二合一。

> - 15-30 minute setup by swapping your `OPENAI_API_BASE` to Helicone proxy.
> - MIT licensed; 100K req/mo free, paid $20/mo+.
> - Includes failover, caching, rate limits — acts as a gateway too.
> - Less depth on agent / multi-step traces.
> - Sweet spot: quick start, single-stack app, need gateway + observability in one.

### Opik (Comet) — OSS dev platform · Opik（Comet）——OSS 开发平台

- Apache 2.0，完全开源。
- 功能集与 Langfuse 相近，带着 Comet 的血统。
- 最佳场景：已经在用 Comet 的 ML 团队，想在同一个面板里看 LLM 可观测性。

> - Apache 2.0, fully OSS.
> - Similar feature set to Langfuse with Comet heritage.
> - Sweet spot: ML teams already on Comet, want LLM observability in the same pane.

### SigNoz — OpenTelemetry-first full APM · SigNoz——OpenTelemetry 优先的全栈 APM

- Apache 2.0。经 OpenTelemetry 处理通用 APM 加 LLM。
- 最佳场景：跨服务与 LLM 调用的统一可观测性。

> - Apache 2.0. Handles general APM plus LLM via OpenTelemetry.
> - Sweet spot: unified observability across services and LLM calls.

### The glue: OpenTelemetry + GenAI semantic conventions · 粘合剂：OpenTelemetry + GenAI 语义约定

OpenTelemetry 在 2025 年底发布了 GenAI 语义约定（`gen_ai.system`、`gen_ai.request.model`、`gen_ai.usage.input_tokens`）。消费 OTel 的工具可以互通。正在成型的生产模式：

1. 每次 LLM 调用都按 GenAI 约定发出 OTel。
2. 日常流量路由到网关（Helicone / Portkey）。
3. 双写到评测平台（Phoenix / Langfuse）用于回归检测。
4. 归档进数据湖（Iceberg），经 Arize AX 或 DuckDB 做长期分析。

> OpenTelemetry published GenAI semantic conventions in late 2025 (`gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`). Tools that consume OTel can interoperate. The production pattern emerging:
> 1. Emit OTel with GenAI conventions from every LLM call.
> 2. Route to gateway (Helicone / Portkey) for day-to-day.
> 3. Dual-ship to eval platform (Phoenix / Langfuse) for regressions.
> 4. Archive in data lake (Iceberg) for long-term analysis via Arize AX or DuckDB.

### The trap: instrumenting at the wrong layer · 陷阱：在错误的层埋点

在你的 agent 框架内部埋点（比如加 LangSmith trace）会把你和那个框架绑死。在 HTTP/OpenAI-SDK 层埋点（经 OpenLLMetry 或你的网关）是可移植的。

> Instrumenting inside your agent framework (e.g., adding LangSmith traces) couples you to that framework. Instrumenting at the HTTP/OpenAI-SDK layer (via OpenLLMetry or your gateway) is portable.

### Sampling — you can't keep everything · 采样——你留不下所有东西

日请求超过 100 万时，全量 trace 留存的成本比 LLM 调用本身还高。按规则采样：错误 100%、高成本 100%、成功 5%。聚合永远保留；长尾的原始数据按需保留。

> At >1M requests/day, full-trace retention costs more than the LLM calls. Sample by rules: 100% errors, 100% high-cost, 5% success. Keep aggregates always; keep raw for the long tail.

### Numbers you should remember · 该记住的数字

- Langfuse 免费云版：每月 5 万事件。
- LangSmith：$39/用户/月。
- Helicone 免费档：每月 10 万请求。
- Arize AX 宣称：规模上比单体方案便宜约 100 倍。
- OpenTelemetry GenAI 约定：2025 年发布，2026 年广泛采用。

```figure
i4-otel-glue
```

> - Langfuse free cloud: 50K events/month.
> - LangSmith: $39/user/month.
> - Helicone free: 100K req/month.
> - Arize AX claim: ~100x cheaper than monolithic at scale.
> - OpenTelemetry GenAI conventions: 2025 shipping, 2026 widely adopted.

## Use It · 实战用法

`code/main.py` 在不同留存策略（100% 摄取、采样、采样 + 错误全留）下模拟一个 100 万 trace 的日量。报告存储成本，以及每种策略各损失了什么。

> `code/main.py` simulates a 1M-trace day across retention strategies (100% ingest, sampling, sampling + errors). Reports storage cost and what's lost under each.

## Ship It · 交付

本课产出 `outputs/skill-observability-stack.md`。给定技术栈、规模、预算和许可证立场，它会选出该用的工具。

> This lesson produces `outputs/skill-observability-stack.md`. Given stack, scale, budget, license posture, picks the tool(s).

## Exercises · 练习

1. 你的团队用 LangChain，想要 OSS 自托管可观测性。在 Langfuse 和 Opik 里选一个并说明理由。
2. 日 trace 500 万，Datadog 报价 $150K/月，计算 Arize AX 的盈亏平衡点。
3. 设计一套你组织的规范应该在每个 LLM 调用上强制要求的 OpenTelemetry GenAI 属性集。
4. 论证只有 Phoenix 是否足以支撑生产。什么时候不够？
5. Helicone 有 20 ms 代理开销。P99 TTFT 300 ms 时可以接受吗？如果 SLA 是 100 ms 呢？

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| OpenLLMetry | 「LLM 的 OTel」 | 面向 LLM 的开源 OpenTelemetry 埋点 |
| GenAI conventions | 「OTel 属性」 | LLM 调用的标准 OTel 属性名 |
| LangSmith | 「LangChain 可观测性」 | 与 LangChain 生态捆绑的商业平台 |
| Langfuse | 「OSS 版 LangSmith」 | MIT 开源，功能集相近 |
| Phoenix | 「Arize 开发工具」 | OpenTelemetry 原生的开发/评测平台 |
| Arize AX | 「规模化可观测性」 | 商业零拷贝 Iceberg/Parquet 可观测性 |
| Helicone | 「代理式可观测性」 | 收集 LLM 遥测的 HTTP 代理 + 网关功能 |
| Opik | 「Comet 的 LLM」 | 来自 Comet 的 Apache 2.0 OSS 开发平台 |
| Session replay | 「trace 重放」 | 连同工具调用完整重放一次 agent 会话 |
| Eval | 「离线测试」 | 让候选模型/提示在带标签数据集上运行 |

## Further Reading · 延伸阅读

- [SigNoz — Top LLM Observability Tools 2026](https://signoz.io/comparisons/llm-observability-tools/)
- [Langfuse — Arize AX Alternative analysis](https://langfuse.com/faq/all/best-phoenix-arize-alternatives)
- [PremAI — Setting Up Langfuse, LangSmith, Helicone, Phoenix](https://blog.premai.io/llm-observability-setting-up-langfuse-langsmith-helicone-phoenix/)
- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [Arize Phoenix docs](https://docs.arize.com/phoenix)
- [Helicone docs](https://docs.helicone.ai/)
