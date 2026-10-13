# Batch APIs — the 50% Discount as Industry Standard · 批量 API —— 五折折扣成为行业标配

> 每家主流厂商都提供一个五折计价、约 24 小时交付的异步批量 API。OpenAI、Anthropic、Google 以及大多数推理平台（Fireworks 的 batch 档、Together 的 batch）实现的都是同一套模式。把 batch 与提示缓存（prompt caching）叠加，隔夜流水线的成本可以降到同步未缓存成本的约 10%。规则残酷地简单：只要不是交互式的，就该上 batch。内容生成流水线、文档分类、数据抽取、报告生成、批量打标、商品目录打标签——任何能容忍 24 小时延迟的工作负载，在迁上 batch 之前都是在把钱留在桌上。2026 年的生产模式是把每个新的 LLM 工作负载分流到三条车道：交互式（同步 + 缓存）、半交互式（异步队列 + 回退）、批量（隔夜、叠加缓存输入）。那些假装自己是交互式、实际能容忍几分钟延迟的工作负载，浪费得最多。
>
> Every major provider ships an async batch API with a 50% discount and ~24-hour turnaround. OpenAI, Anthropic, Google, and most of the inference platforms (Fireworks batch tier, Together batch) implement the same pattern. Stack batch with prompt caching and overnight pipelines drop to ~10% of synchronous-uncached cost. The rule is brutally simple: if it is not interactive, it belongs on batch. Content generation pipelines, document classification, data extraction, report generation, bulk labeling, catalog tagging — anything tolerant of 24-hour latency is money left on the table until it moves to batch. The 2026 production pattern is to triage every new LLM workload into three lanes: interactive (synchronous with caching), semi-interactive (async queue with fallback), batch (overnight, cached input stacked). Workloads that pretend to be interactive but tolerate minutes of latency waste most.

**Type:** Learn
**Languages:** Python (stdlib, toy batch-vs-sync cost simulator)
**Prerequisites:** Phase 17 · 14 (Prompt & Semantic Caching)
**Time:** ~45 minutes

## Learning Objectives · 学习目标

- 说出三家厂商的批量 API（OpenAI、Anthropic、Google）以及共同的「五折 + 24 小时交付」保证。
- 为一个隔夜分类工作负载计算 batch + 缓存输入叠加后的成本，并与同步未缓存基线比较。
- 把一个工作负载分流到交互式 / 半交互式 / 批量车道，并说明归属理由。
- 说出两个陷阱：部分交互性（用户期望比 24 小时快）和输出模式漂移（batch 文件格式各家不同）。

> Name the three provider batch APIs (OpenAI, Anthropic, Google) and the common 50% discount + 24h turnaround guarantees.
> Compute the cost for stacking batch + cached-input on an overnight classification workload and compare to synchronous-uncached baseline.
> Triage a workload into interactive / semi-interactive / batch and justify the lane.
> Name the two traps: partial interactivity (user expects faster than 24h) and output-schema drift (batch file format differs per provider).

## The Problem · 问题在哪

你的团队上线了一条夜间报告生成流水线：50,000 份文档，逐份摘要，把摘要聚类，起草一份高管简报。同步跑要 4 小时，每晚 $2,000。你听说了批量 API。

batch 给你打五折。你再对系统提示（所有 50k 次调用共享）开启提示缓存。叠加之后，账单降到每晚 $180 —— 约为基线的 9%。同一条流水线，三处配置改动。

batch 是 LLM 成本工具箱里最便宜的一根杠杆，却几乎没人去拉。原因主要是组织层面的：团队想的口号是「实时」，SLA 实际写的却是「明早之前」。这一课讲的就是别把账单的 90% 留在桌上。

> Your team ships a nightly report generation pipeline. 50,000 documents, summarize each, cluster the summaries, draft an executive brief. Running synchronously it takes 4 hours at $2,000/night. You hear about batch APIs.
> The batch gets you 50% off. You also enable prompt caching on the system prompt (shared across all 50k calls). Stacked, the bill drops to $180/night — ~9% of baseline. Same pipeline, three config changes.
> Batch is the cheapest lever in the LLM cost toolkit that nobody pulls. The reason is mostly organizational: teams think "real-time" when the SLA actually is "by morning." This lesson is about not leaving 90% of the bill on the table.

## The Concept · 概念

### The three batch APIs · 三家批量 API

**OpenAI Batch API**：上传一个 JSONL 文件，内含一组请求。承诺 24 小时交付（实践中通常约 2-8 小时）。输入和输出 token 五折。端点是 `/v1/batches`。可缓存的输入还能在此之上再享受缓存输入定价。

**Anthropic Message Batches**：JSONL 上传。24 小时交付。五折。支持 `cache_control` —— 缓存写入是显式的，读取则在 batch 内自动发生。

**Google Vertex AI Batch Prediction**：BigQuery 或 GCS 作为输入。Gemini 同样约五折。与 Vertex 流水线集成。

> **OpenAI Batch API**: JSONL file upload with a list of requests. Promised 24-hour turnaround (usually ~2-8 hours in practice). 50% discount on input and output tokens. `/v1/batches` endpoint. Cache-eligible inputs also get cached-input pricing on top.
> **Anthropic Message Batches**: JSONL upload. 24-hour turnaround. 50% discount. Supports `cache_control` — cache writes are explicit, reads happen automatically within the batch.
> **Google Vertex AI Batch Prediction**: BigQuery or GCS input. Similar 50% discount for Gemini. Integrates with Vertex pipelines.

### Semantic: asynchronous, not slow · 语义：异步而非慢

batch 的含义是「我承诺 24 小时内返回」——不是「这要花 24 小时」。典型 P50 是 2-6 小时。厂商把你的 batch 安排在 GPU 库存未被充分利用的低峰窗口调度。

> Batch is "I promise to return within 24 hours" — not "this will take 24 hours." Typical P50 is 2-6 hours. Provider schedules your batch during off-peak windows when GPU inventory is underutilized.

### Stack with caching · 与缓存叠加

一个 5 万文档摘要任务，共享同一条 4K token 的系统提示：

- 同步未缓存：50000 × ($input × 4000 + $output × 200)，全价。
- 同步缓存：系统提示首次写入后被缓存；其余 49999 次调用的输入便宜 10 倍。
- batch 缓存：以上全部，再对读和写都打五折。

叠加公式：batch + 缓存 = 同步未缓存账单的约 10%。任何隔夜运行且共享系统提示的工作负载都应该这么用。

> A 50k-document summarization with the same 4K-token system prompt: Synchronous uncached: 50000 × ($input × 4000 + $output × 200) at full rates. Synchronous cached: system prompt cached after first write; remaining 49999 get 10x cheaper input. Batch cached: all of the above plus 50% discount on both read and write. ... The stack: batch + cache = ~10% of sync uncached bill. Any workload that runs overnight and has a shared system prompt should use this.

### Workload triage · 工作负载分流

**交互式（Interactive）** —— 用户等待响应。TTFT 很重要。带提示缓存的同步调用。不能 batch。

**半交互式（Semi-interactive）** —— 用户提交任务，几分钟后回来查看。异步队列，batch 不可用时回退同步。想想中等规模的 RAG 索引。

**批量（Batch）** —— 用户期望「明早」或「下个小时」出结果。内容流水线、大规模分类、离线分析。永远 batch，永远叠加缓存。

常见错误：因为流水线「跑在生产环境」，就把一切都归为交互式。生产环境不是延迟规格——SLA 才是。

> **Interactive** — user waits for the response. TTFT matters. Synchronous call with prompt caching. Cannot batch.
> **Semi-interactive** — user submits a task, checks back in minutes. Async queue with fallback to sync if batch not available. Think moderate-volume RAG indexing.
> **Batch** — user expects results "by morning" or "next hour." Content pipelines, classification at scale, offline analysis. Always batch, always stack caching.
> Common mistake: classifying everything as interactive because the pipeline is production. Production is not a latency spec — SLA is.

### The partial-interactivity trap · 部分交互性陷阱

有些功能看起来交互式，实际能容忍 5-10 分钟。例子：一个带「刷新」按钮的夜间客户健康报告。用户点刷新；等 10 分钟没问题。团队却把它做成了同步。50 个并发刷新的成本，是「批处理完、邮件送达」方案的 10 倍。

该问的问题是：「对这个用户来说，24 小时意味着什么？」如果答案是「他们根本不会注意到」，那就 batch。

> Some features look interactive but tolerate 5-10 minutes. Example: a nightly customer health report with "refresh" button. User clicks refresh; wait 10 minutes is fine. Team ships it as synchronous. 50 concurrent refreshes cost 10x what batched-and-delivered-via-email would cost.
> The question to ask: "What does 24-hour mean for this user?" If the answer is "they wouldn't notice," batch it.

### The output-schema trap · 输出模式（schema）陷阱

batch 文件格式各家不同：

- OpenAI：JSONL，每行一个请求。
- Anthropic：JSONL，每行一条 message；响应格式内嵌其中。
- Vertex：BigQuery 表或带 TFRecord 的 GCS 前缀。

想写一个「跨厂商通用 batch 客户端」，就意味着每个厂商都要写适配代码。宣称支持多厂商 batch 的网关（Portkey、LiteLLM 的部分档位）也只是对原始格式做了薄封装。

> Batch file formats differ per provider: OpenAI: JSONL, one request per line. Anthropic: JSONL, one message per line; response format embedded. Vertex: BigQuery table or GCS prefix with TFRecord. ... Writing "one batch client" across providers means adapter code per provider. Gateways that advertise multi-provider batch (Portkey, LiteLLM some tiers) still thin-wrap the raw format.

### Numbers you should remember · 你该记住的数字

- 各厂商 batch 折扣：输入 + 输出一律五折。
- 交付 SLA：保证 24 小时，典型 P50 为 2-6 小时。
- batch + 缓存输入叠加：约为同步未缓存成本的 10%。
- 分流规则：只要 24 小时延迟可接受，永远 batch。

```figure
batch-lane-triage
```

> Batch discount across providers: 50% flat on input + output. Turnaround SLA: 24 hours guaranteed, 2-6 hours typical P50. Stacked batch + cached input: ~10% of sync uncached cost. Workload triage rule: if 24h latency acceptable, always batch.

## Use It · 实战用法

`code/main.py` 针对一个 5 万文档工作负载，计算 sync、sync+cache、batch、batch+cache 四种方式的成本，并以美元和百分比报告节省。

> `code/main.py` computes costs across sync, sync+cache, batch, and batch+cache for a 50k-document workload. Reports savings in $ and percent.

## Ship It · 交付

本课产出 `outputs/skill-batch-triager.md`。给定工作负载特征，它将其分流为交互式/半交互式/批量，并估算节省。

> This lesson produces `outputs/skill-batch-triager.md`. Given workload characteristics, triages into interactive/semi/batch and estimates savings.

## Exercises · 练习

1. 跑 `code/main.py`。对一个 10 万文档、3K token 系统提示、500 token 输出的流水线，计算完全叠加（batch + cache）相对同步基线的节省。
2. 从你熟悉的一个真实产品里挑三个功能，把每个分流到交互式/半交互式/批量。
3. 一位用户抱怨他的报告花了 3 小时。这是 batch 分流失误，还是合法的交互式场景？写出判定标准。
4. 你的 batch API 交付 SLA 是 24h，但 P99 是 20 小时。你怎么向用户传达——边界情况下下游系统的行为是什么？
5. 算出盈亏平衡点：共享前缀多长时，batch + cache 比在自己预留的 GPU 上跑隔夜任务更便宜？

> 1. Run `code/main.py`. For a 100k-doc pipeline with 3K-token system prompt and 500-token output, compute the savings of full stack (batch + cache) vs sync baseline. ... 3. A user complains their report took 3 hours. Was that a batch mis-triage or a legitimate interactive? Write the decision criterion. ... 5. Compute break-even: at what shared-prefix length does batch + cache become cheaper than running overnight on your own reserved GPU?

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|------------|----------|
| Batch API | 「异步折扣」 | 五折，24 小时交付 |
| JSONL | 「batch 格式」 | 每行一个 JSON 请求；OpenAI/Anthropic 标准 |
| Message Batches | 「Anthropic batch」 | Anthropic 批量 API 的产品名 |
| Batch prediction | 「Vertex batch」 | Vertex AI 的批量 API 产品 |
| Turnaround SLA | 「24 小时承诺」 | 是保证值不是典型值；典型为 2-6 小时 |
| Workload triage | 「交互性决策」 | 交互式 / 半交互式 / 批量的路由决策 |
| Output schema | 「响应格式」 | 各厂商不同的 JSONL 布局；不可移植 |
| Stacked discount | 「batch + cache」 | 两者同时生效时约为未缓存同步账单的 10% |

## Further Reading · 延伸阅读

- [OpenAI Batch API](https://platform.openai.com/docs/guides/batch) —— JSONL 格式与 `/v1/batches` 语义。
- [Anthropic Message Batches](https://docs.anthropic.com/en/docs/build-with-claude/batch-processing) —— batch 格式与 `cache_control` 的交互。
- [Vertex AI Batch Prediction](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/batch-prediction-gemini) —— Gemini batch 语义。
- [Finout — OpenAI vs Anthropic API Pricing 2026](https://www.finout.io/blog/openai-vs-anthropic-api-pricing-comparison)
- [Zen Van Riel — LLM API Cost Comparison 2026](https://zenvanriel.com/ai-engineer-blog/llm-api-cost-comparison-2026/)
