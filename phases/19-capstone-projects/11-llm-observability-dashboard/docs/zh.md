# Capstone 11 — LLM Observability & Eval Dashboard · 毕业项目 11 —— LLM 可观测性与评估仪表盘

> Langfuse 转向 open-core。Arize Phoenix 发布了 2026 年 GenAI 语义约定映射。Helicone 和 Braintrust 都在按用户成本归因上加倍投入。Traceloop 的 OpenLLMetry 成了事实标准的 SDK 埋点方案。生产形态是：ClickHouse 存 trace，Postgres 存元数据，Next.js 做 UI，外加一小队评估任务（DeepEval、RAGAS、LLM-judge）跑在采样 trace 上。自建一套，接入至少四个 SDK 家族，并演示在五分钟内抓到一个注入的回归。

> Langfuse went open-core. Arize Phoenix published the 2026 GenAI semconv mappings. Helicone and Braintrust both doubled down on per-user cost attribution. Traceloop's OpenLLMetry became the de-facto SDK instrumentation. The production shape is ClickHouse for traces, Postgres for metadata, Next.js for UI, and a small army of eval jobs (DeepEval, RAGAS, LLM-judge) running over sampled traces. Build one self-hosted, ingest from at least four SDK families, and demonstrate catching an injected regression in under five minutes.

**Type:** Capstone
**Languages:** TypeScript (UI), Python / TypeScript (ingest + evals), SQL (ClickHouse)
**Prerequisites:** Phase 11 (LLM engineering), Phase 13 (tools), Phase 17 (infrastructure), Phase 18 (safety)
**Phases exercised:** P11 · P13 · P17 · P18
**Time:** 25 hours

## Problem · 问题

2026 年每一个跑生产流量的 AI 团队，都在模型旁边养着一个可观测性平面：成本归因、幻觉检测、漂移监控、越狱信号、SLO 仪表盘、PII 泄漏告警。开源参照系——Langfuse、Phoenix、OpenLLMetry——已收敛到 OpenTelemetry GenAI 语义约定（semantic conventions）作为接入 schema。现在你可以用一套 SDK 给 OpenAI、Anthropic、Google、LangChain、LlamaIndex 和 vLLM 埋点，产出兼容的 span。

你要自建一个仪表盘：接入至少四个 SDK 家族，对采样 trace 跑一组评估任务，检测漂移并告警。度量门槛：给定一个故意注入的回归（某个 prompt 开始产出 PII），仪表盘要在五分钟内抓住它并触发告警。

> Every AI team running production traffic in 2026 keeps an observability plane alongside the model. Cost attribution. Hallucination detection. Drift monitoring. Jailbreak signal. SLO dashboards. PII leak alerts. The open-source references — Langfuse, Phoenix, OpenLLMetry — converged on OpenTelemetry GenAI semantic conventions as the ingest schema. You can now instrument OpenAI, Anthropic, Google, LangChain, LlamaIndex, and vLLM with one SDK and ship compatible spans.
> You will build a self-hosted dashboard that ingests from at least four SDK families, runs a small set of eval jobs over sampled traces, detects drift, and alerts. The measurement bar: given a deliberately injected regression (a prompt that starts producing PII), the dashboard catches it and fires an alert in under five minutes.

## Concept · 概念

接入走 OTLP HTTP。SDK 产出 GenAI 语义约定 span：`gen_ai.system`、`gen_ai.request.model`、`gen_ai.usage.input_tokens`、`gen_ai.response.id`、`llm.prompts`、`llm.completions`。span 落进 ClickHouse 做列式分析；元数据（用户、会话、应用）落进 Postgres。

评估以批处理任务的形式跑在采样 trace 上。DeepEval 给忠实度（faithfulness）、毒性和答案相关性打分。trace 携带检索上下文时，RAGAS 计算检索指标。自定义 LLM-judge 跑领域专属检查（PII 泄漏、偏离政策的回答）。评估结果以 eval span 的形式写回同一个 ClickHouse，并链接到父 trace。

漂移检测盯着随时间变化的嵌入空间分布（对 prompt 嵌入算 PSI 或 KL 散度），外加评估分数趋势。告警先进 Prometheus Alertmanager，再进 Slack / PagerDuty。UI 是 Next.js 15 + Recharts。

> Ingest is OTLP HTTP. The SDK produces GenAI-semconv spans: `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.response.id`, `llm.prompts`, `llm.completions`. Spans land in ClickHouse for columnar analytics; metadata (users, sessions, apps) lands in Postgres.
> Evals run as batch jobs over sampled traces. DeepEval scores faithfulness, toxicity, and answer relevance. RAGAS scores retrieval metrics when the trace carries retrieval context. Custom LLM-judges run domain-specific checks (PII leak, off-policy response). Eval runs write back to the same ClickHouse as eval spans linked to the parent trace.
> Drift detection watches embedding-space distributions over time (PSI or KL divergence on prompt embeddings) plus eval-score trends. Alerts feed Prometheus Alertmanager and then Slack / PagerDuty. The UI is Next.js 15 with Recharts.

## Architecture · 架构

```
production apps:
  OpenAI SDK  +  Anthropic SDK  +  Google GenAI SDK
  LangChain + LlamaIndex + vLLM
       |
       v
  OpenTelemetry SDK with GenAI semconv
       |
       v  OTLP HTTP
  collector (ingest, sample, fan-out)
       |
       +-------------+-----------+
       v             v           v
   ClickHouse    Postgres    S3 archive
   (spans)       (metadata)  (raw events)
       |
       +---> eval jobs (DeepEval, RAGAS, LLM-judge)
       |     sampled or all-trace
       |     write eval spans back
       |
       +---> drift detector (PSI / KL on prompt embeddings)
       |
       +---> Prometheus metrics -> Alertmanager -> Slack / PagerDuty
       |
       v
   Next.js 15 dashboard (Recharts)
```

## Stack · 技术栈

- 接入：OpenTelemetry SDK + GenAI 语义约定；OTLP HTTP 传输
- 采集器：OpenTelemetry Collector，带尾采样处理器（tail-sampling，用于成本控制）
- 存储：ClickHouse 存 span，Postgres 存元数据，S3 存原始事件归档
- 评估：DeepEval、RAGAS 0.2、Arize Phoenix 评估器包、自定义 LLM-judge
- 漂移：对合并的 prompt 嵌入（sentence-transformers）每周算 PSI / KL
- 告警：Prometheus Alertmanager → Slack / PagerDuty
- UI：Next.js 15 App Router + Recharts + server actions
- 开箱即支持的 SDK：OpenAI、Anthropic、Google GenAI、LangChain、LlamaIndex、vLLM

```figure
ce-otel-drift
```

## Build It · 动手造

1. **采集器配置。** OpenTelemetry Collector：OTLP HTTP receiver，一个尾采样器（错误 trace 100% 保留、成功 trace 保留 10%），以及导出到 ClickHouse 和 S3 的 exporter。

2. **ClickHouse schema。** `spans` 表，列对应 GenAI 语义约定：`gen_ai_system`、`gen_ai_request_model`、`input_tokens`、`output_tokens`、`latency_ms`、`prompt_hash`、`trace_id`、`parent_span_id`，外加一个装长载荷的 JSON 字段。按 user_id 和 app_id 加二级索引。

3. **SDK 覆盖测试。** 用每个 SDK（OpenAI、Anthropic、Google、LangChain、LlamaIndex、vLLM）各写一个带 OpenLLMetry 自动埋点的小客户端应用。验证每一个都产出规范的 GenAI span 并落进 ClickHouse。

4. **评估任务。** 一个定时任务读取最近 15 分钟的采样 trace，跑 DeepEval 的忠实度、毒性和答案相关性。输出是链接到父 trace 的 eval span。

5. **自定义 LLM-judge。** 一个 PII 泄漏 judge：给定一条回复，调用一个守护 LLM 给 PII 泄漏可能性打分。高分配回复进入分诊队列。

6. **漂移检测。** 每周任务计算本周合并 prompt 嵌入与过去 4 周基线之间的 PSI。PSI 超过阈值就告警。

7. **仪表盘。** Next.js 15，页面包括：总览（span/秒、成本/用户、p95 延迟）、traces（搜索 + 瀑布图）、评估（忠实度趋势、毒性）、漂移（PSI 随时间）、告警。

8. **告警链。** Prometheus exporter 读取评估分数聚合和延迟分位数；Alertmanager 把告警路由到 Slack（警告级）和 PagerDuty（严重级）。

9. **回归探针。** 注入一个 bug：被评估的聊天机器人开始以 1% 的概率泄漏假 SSN。度量 MTTR：从 bug 上线到 Slack 告警的时间。

> 1. **Collector config.** OpenTelemetry Collector with the OTLP HTTP receiver, a tail-sampler keeping 100% of errored traces and 10% of successes, and exporters to ClickHouse and S3.
> 5. **Custom LLM-judge.** A PII-leak judge: given a response, call a guard LLM to score likelihood of PII leak. High-score responses land in a triage queue.
> 6. **Drift detection.** Weekly job computes PSI between this week's pooled prompt embeddings and the trailing 4-week baseline. If PSI above threshold, alert.
> 9. **Regression probe.** Inject a bug: the evaluated chatbot starts leaking fake SSNs 1% of the time. Measure MTTR: from bug deployed to Slack alert.

## Use It · 实战用法

```
$ curl -X POST https://my-otel-collector/v1/traces -d @trace.json
[collector]  accepted 1 trace, 3 spans
[clickhouse] inserted 3 spans (app=chat, user=u_42)
[eval]       DeepEval faithfulness 0.82, toxicity 0.03
[drift]      weekly PSI 0.08 (below 0.2 threshold)
[ui]         live at https://obs.example.com
```

## Ship It · 交付

`outputs/skill-llm-observability.md` 是交付物。给定一个 LLM 应用，仪表盘接入它的 trace、跑评估、对漂移告警，并在 Next.js 里呈现按用户的成本分解。

| 权重 | 评分标准 | 度量方式 |
|:-:|---|---|
| 25 | Trace schema 覆盖 | 产出规范 GenAI span 的 SDK 家族数（目标：6+） |
| 20 | 评估正确性 | DeepEval / RAGAS 分数 vs 人工标注集 |
| 20 | 仪表盘 UX | 注入回归的 MTTR（目标：5 分钟以内） |
| 20 | 成本 / 规模 | 1k span/秒持续接入无积压 |
| 15 | 告警 + 漂移检测 | Prometheus/Alertmanager 链路端到端演练 |
| **100** | | |

> `outputs/skill-llm-observability.md` is the deliverable. Given an LLM application, the dashboard ingests its traces, runs evals, alerts on drift, and surfaces cost/user breakdown in Next.js.

## Exercises · 练习

1. 为 Haystack 框架加自定义埋点。验证规范 span 带着 `gen_ai.*` 原样属性落进 ClickHouse。

2. 在同一批 trace 上把 DeepEval 换成 Phoenix 评估器。度量两套评估引擎之间的分数漂移。

3. 把漂移检测做细：按 app-id 而不是全局计算 PSI。展示每个应用的漂移轨迹。

4. 加一个「用户影响」页面：按用户的成本和失败率，带 sparkline。

5. 构建一个尾采样策略：毒性 > 0.5 的 trace 100% 保留，其余按 10% 分层抽样。度量由此引入的抽样偏差。

> 1. Add custom instrumentation for the Haystack framework. Verify canonical spans land in ClickHouse with faithful `gen_ai.*` attributes.
> 5. Build a tail-sampling policy that keeps 100% of traces with toxicity > 0.5 plus a 10% stratified sample of the rest. Measure sampling bias introduced.

## Key Terms · 术语表

| 术语 | 俗称 | 实际含义 |
|------|-----------------|------------------------|
| GenAI semconv | "OTel 的 LLM 属性" | 2025 年 OpenTelemetry 规范中的 LLM span 属性（system、model、tokens） |
| Tail sampling（尾采样） | "trace 完成后抽样" | 采集器在一条 trace 结束后决定保留还是丢弃（能看到是否出错） |
| PSI | "总体稳定性指数" | 对比两个分布的漂移指标；> 0.2 通常意味着显著漂移 |
| LLM-judge | "用模型做评估" | 一个 LLM 按评分细则给另一个 LLM 的输出打分（忠实度、毒性、PII） |
| Tail-sampling policy（尾采样策略） | "保留规则" | 决定哪些 trace 持久化、哪些丢弃的规则；出错全留 + 采样率 |
| Eval span | "链接式评估 trace" | 携带评估分数、链接到原始 LLM 调用 span 的子 span |
| Cost per user（按用户成本） | "单位经济" | 一个 user_id 在某窗口内归因到的美元成本；关键产品指标 |

## Further Reading · 延伸阅读

- [Langfuse](https://github.com/langfuse/langfuse) —— open-core 可观测性平台的参照实现
- [Arize Phoenix](https://github.com/Arize-ai/phoenix) —— 另一个参照实现，漂移支持很强
- [OpenLLMetry (Traceloop)](https://github.com/traceloop/openllmetry) —— 自动埋点 SDK 家族
- [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) —— 接入 schema
- [Helicone](https://www.helicone.ai) —— 另一个托管可观测性方案
- [Braintrust](https://www.braintrust.dev) —— 另一个评估优先的平台
- [ClickHouse documentation](https://clickhouse.com/docs) —— 列式 span 存储
- [DeepEval](https://github.com/confident-ai/deepeval) —— 评估器库
