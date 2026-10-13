# Agent Observability: Langfuse, Phoenix, Opik · Agent 可观测性：Langfuse、Phoenix、Opik

> 2026 年，三个开源 agent 可观测性平台领跑。Langfuse（MIT）——每月 600 万+ 安装，tracing + prompt 管理 + 评估 + 会话回放。Arize Phoenix（Elastic 2.0）——深入的 agent 专项评估、RAG 相关性、OpenInference 自动 instrumentation。Comet Opik（Apache 2.0）——自动化 prompt 优化、guardrails、LLM-judge 幻觉检测。
>
> Three open-source agent observability platforms dominate 2026. Langfuse (MIT) — 6M+ installs/month, tracing + prompt management + evals + session replay. Arize Phoenix (Elastic 2.0) — deep agent-specific evals, RAG relevancy, OpenInference auto-instrumentation. Comet Opik (Apache 2.0) — automated prompt optimization, guardrails, LLM-judge hallucination detection.

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 23 (OTel GenAI)
**Time:** ~45 minutes

## Learning Objectives · 学习目标

- 说出三个头部开源 agent 可观测性平台及各自的许可证。
- 区分各自最强的一面：Langfuse（prompt 管理 + 会话）、Phoenix（RAG + 自动 instrumentation）、Opik（优化 + guardrails）。
- 解释为什么到 2026 年有 89% 的组织报告已部署 agent 可观测性。
- 实现一个纯标准库的 trace-to-dashboard 流水线，带 LLM-judge 评估。

> Name the three top open-source agent observability platforms and their licenses.
> Distinguish what each one is strongest at: Langfuse (prompt mgmt + sessions), Phoenix (RAG + auto-instrumentation), Opik (optimization + guardrails).
> Explain why 89% of organizations report having agent observability in place by 2026.
> Implement a stdlib trace-to-dashboard pipeline with LLM-judge evaluation.

## The Problem · 问题在哪

OTel GenAI（第 23 课）给了你 schema。你还需要一个平台来摄取 span、跑评估、存 prompt 版本、把回归暴露出来。三个竞争者在生命周期的不同部分各有所长。

> OTel GenAI (Lesson 23) gives you the schema. You still need the platform that ingests spans, runs evaluations, stores prompt versions, and surfaces regressions. The three contenders each emphasize different parts of the lifecycle.

## The Concept · 概念

### Langfuse (MIT) · Langfuse

- 每月 600 万+ SDK 安装，19k+ GitHub stars。
- 功能：tracing、带版本管理 + playground 的 prompt 管理、评估（LLM-as-judge、用户反馈、自定义）、会话回放。
- 2025 年 6 月：原先的商业模块（LLM-as-a-judge、标注队列、prompt 实验、Playground）以 MIT 协议开源。
- 最强于：端到端可观测性 + 紧密的 prompt 管理闭环。

> - 6M+ SDK installs/month, 19k+ GitHub stars.
> - Features: tracing, prompt management with versioning + playground, evaluations (LLM-as-judge, user feedback, custom), session replays.
> - June 2025: formerly commercial modules (LLM-as-a-judge, annotation queues, prompt experiments, Playground) open-sourced under MIT.
> - Strongest for: end-to-end observability with tight prompt-management loop.

### Arize Phoenix (Elastic License 2.0) · Arize Phoenix

- 更深入的 agent 专项评估：trace 聚类、异常检测、RAG 的检索相关性。
- 原生 OpenInference 自动 instrumentation。
- 与托管版 Arize AX 配合上生产。
- 没有 prompt 版本管理——定位是放在更大平台旁边的漂移/行为回归工具。
- 最强于：RAG 相关性、行为漂移、异常检测。

> - Deeper agent-specific evaluation: trace clustering, anomaly detection, retrieval relevancy for RAG.
> - Native OpenInference auto-instrumentation.
> - Pairs with managed Arize AX for production.
> - No prompt versioning — positioned as a drift/behavioral-regression tool alongside broader platforms.
> - Strongest for: RAG relevancy, behavioral drift, anomaly detection.

### Comet Opik (Apache 2.0) · Comet Opik

- 通过 A/B 实验做自动化 prompt 优化。
- Guardrails（PII 脱敏、主题约束）。
- LLM-judge 幻觉检测。
- Comet 自己测的基准：Opik 记录 + 评估用 23.44s，Langfuse 327.15s（约 14 倍差距）——厂商基准当方向参考就好。
- 最强于：优化闭环、自动化实验、guardrail 执行。

> - Automated prompt optimization through A/B experiments.
> - Guardrails (PII redaction, topical constraints).
> - LLM-judge hallucination detection.
> - Benchmark from Comet's own measurement: Opik logs + evals in 23.44s vs Langfuse 327.15s (~14x gap) — take vendor benchmarks as directional.
> - Strongest for: optimization loop, automated experimentation, guardrail enforcement.

### Industry data · 行业数据

据 Maxim（2026 年行业分析）：89% 的组织已部署 agent 可观测性；质量问题是最大的生产障碍（32% 的受访者提到）。

> Per Maxim (2026 field analysis): 89% of organizations have agent observability in place; quality issues are the top production barrier (32% of respondents cite them).

### Picking one · 怎么选

| Need | Pick |
|------|------|
| 一体化且要 prompt 管理 | Langfuse |
| 深度 RAG 评估 + 漂移 | Phoenix |
| 自动化优化 + guardrails | Opik |
| 开源许可证、不要 ELv2 | Langfuse（MIT）或 Opik（Apache 2.0） |
| Datadog / New Relic 集成 | 都行——它们都能导出 OTel |

> | Need | Pick |
> |------|------|
> | All-in-one with prompt management | Langfuse |
> | Deep RAG evaluation + drift | Phoenix |
> | Automated optimization + guardrails | Opik |
> | Open licensing, no ELv2 | Langfuse (MIT) or Opik (Apache 2.0) |
> | Datadog / New Relic integration | Any — they all export OTel |

### Where this pattern goes wrong · 这个模式的常见坑

- **没有评估策略。** 只有 tracing 没有评估，就是昂贵的日志。
- **自造 LLM-judge 却不做事实 grounding。** CRITIC 模式（第 05 课）适用——裁判需要外部工具做事实核验。
- **prompt 版本没和 trace 关联。** 生产一回归，你没法二分定位到肇事的 prompt。

> - **No eval strategy.** Tracing without evaluation is just expensive logging.
> - **Self-rolled LLM-judge without grounding.** CRITIC pattern (Lesson 05) applies — judges need external tools for factual verification.
> - **Prompt versions not tied to traces.** When prod regresses, you cannot bisect to the prompt that caused it.

```figure
wb-trace-ingest
```

## Build It · 动手造

`code/main.py` 用标准库实现了一个 trace 收集器 + LLM-judge 评估器：

- 摄取 GenAI 形状的 span。
- 按会话分组，给失败运行打标（guardrail 触发、低置信度评估）。
- 一个脚本化的 LLM-judge，按 rubric 给 agent 回应打分。
- 一个类仪表盘汇总：失败率、Top 失败原因、评估分数分布。

运行：

```
python3 code/main.py
```

> `code/main.py` implements a stdlib trace collector + LLM-judge evaluator:
> - Ingest GenAI-shaped spans.
> - Group by session, tag failed runs (guardrail trips, low-confidence evals).
> - A scripted LLM-judge that scores agent responses on a rubric.
> - A dashboard-like summary: failure rate, top failure reasons, eval score distribution.

输出：逐会话的评估分数与失败归类，和 Langfuse/Phoenix/Opik 会展示的一致。

> Output: per-session eval scores and failure categorization matching what Langfuse/Phoenix/Opik would show.

## Use It · 实战用法

- **Langfuse** 自托管或云端；经 OTel 或它们的 SDK 接入。
- **Arize Phoenix** 自托管；自动 instrumentation 走 OpenInference。
- **Comet Opik** 自托管或云端；自动化优化闭环。
- **Datadog LLM Observability** 适合已经在跑 Datadog 的运维 + ML 混合团队。

> - **Langfuse** self-hosted or cloud; wire via OTel or their SDK.
> - **Arize Phoenix** self-hosted; auto-instrument OpenInference.
> - **Comet Opik** self-hosted or cloud; automated optimization loop.
> - **Datadog LLM Observability** for mixed ops+ML teams that already run Datadog.

## Ship It · 交付

`outputs/skill-obs-platform-wiring.md` 选定一个平台，把 trace + 评估 + prompt 版本接进现有 agent。

> `outputs/skill-obs-platform-wiring.md` picks a platform and wires traces + evals + prompt versions into an existing agent.

## Exercises · 练习

1. 把一周的 OTel trace 导出到 Langfuse 云（免费档）。哪些会话失败了？为什么？
2. 为你的领域写一份 LLM-judge rubric（事实正确性、语气、范围遵循）。在 50 条 trace 上试跑。
3. 对比 Langfuse 的 prompt 版本管理与 Phoenix 的 trace 聚类。哪个更快告诉你什么东西坏了？
4. 读 Opik 的 guardrail 文档。给你的某次 agent 运行接一个 PII 脱敏 guardrail。
5. 在你自己的语料上给三者做基准。无视厂商公布的数字；测你自己的。

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| Tracing | 「span 收集器」 | 摄取 OTel / SDK span；按会话建索引 |
| Prompt management | 「prompt CMS」 | 与 trace 关联的带版本 prompt |
| LLM-as-judge | 「自动化评估」 | 用另一个 LLM 按 rubric 给 agent 输出打分 |
| Session replay | 「trace 回放」 | 逐步回放过去的运行来调试 |
| RAG relevancy | 「检索质量」 | 检索到的上下文是否匹配查询 |
| Trace clustering | 「行为分组」 | 聚类相似运行以检测漂移 |
| Guardrail enforcement | 「日志时刻的策略」 | 对记录内容做 PII/毒性/范围检查 |

## Further Reading · 延伸阅读

- [Langfuse docs](https://langfuse.com/) —— tracing、评估、prompt 管理
- [Arize Phoenix docs](https://docs.arize.com/phoenix) —— 自动 instrumentation、漂移
- [Comet Opik](https://www.comet.com/site/products/opik/) —— 优化 + guardrails
- [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) —— 三家共同消费的 schema
