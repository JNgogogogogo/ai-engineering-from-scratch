# Inference Metrics — TTFT, TPOT, ITL, Goodput, P99 · 推理指标——TTFT、TPOT、ITL、Goodput、P99

四个指标决定一个推理部署是否健康。TTFT 是 prefill 加排队加网络。TPOT（等价于 ITL）是解码阶段每个 token 的访存瓶颈（memory-bound）成本。端到端（end-to-end）延迟是 TTFT 加 TPOT 乘以输出长度。吞吐量（throughput）是整个集群聚合的每秒 token 数。但真正对产品有意义的是 goodput——同时满足全部 SLO 的请求占比。高吞吐配低 goodput，意味着你处理的 token 永远无法按时到达用户手里。Llama-3.1-8B-Instruct 在 TRT-LLM 上 2026 年的参考数字：平均 TTFT 162 ms，平均 TPOT 7.33 ms，平均 E2E 1,093 ms。永远报告 P50、P90、P99——绝不要只报平均值。还要提防测量陷阱：GenAI-Perf 在 ITL 计算中不包含 TTFT，LLMPerf 则包含；同一次运行，两个工具给出的 TPOT 并不一致。

> Four metrics decide whether an inference deployment is working. TTFT is prefill plus queue plus network. TPOT (equivalently ITL) is the memory-bound decode cost per token. End-to-end latency is TTFT plus TPOT times output length. Throughput is tokens per second aggregated across the fleet. But the one that matters for product is goodput — the fraction of requests that met every SLO simultaneously. High throughput at low goodput means you are processing tokens that never reach users on time. Reference numbers for Llama-3.1-8B-Instruct on TRT-LLM in 2026: mean TTFT 162 ms, mean TPOT 7.33 ms, mean E2E 1,093 ms. Always report P50, P90, P99 — never just mean. And watch the measurement trap: GenAI-Perf excludes TTFT from ITL calculation, LLMPerf includes it; two tools disagree on TPOT for the same run.

**Type:** Learn
**Languages:** Python（仅标准库；玩具级分位数计算器与 goodput 报告器）
**Prerequisites:** Phase 17 · 04（Serving Engine Internals）
**Time:** ~60 分钟

## Learning Objectives · 学习目标

- 精确定义 TTFT、TPOT、ITL、E2E、吞吐量（throughput）和 goodput，并指出每个指标各自度量的是哪个组成部分。
- 解释为什么均值是 LLM 服务错误的统计量，以及如何读 P50/P90/P99。
- 构造一个 SLO 多重约束（例如 TTFT<500 ms AND TPOT<15 ms AND E2E<2 s），并针对它计算 goodput。
- 说出两个对同一次运行会给出不同 TPOT 的基准工具，并解释原因。

> Define TTFT, TPOT, ITL, E2E, throughput, and goodput precisely and name the component each one measures.
> Explain why mean is the wrong statistic for LLM serving and how to read P50/P90/P99.
> Construct an SLO multi-constraint (e.g. TTFT<500 ms AND TPOT<15 ms AND E2E<2 s) and compute goodput against it.
> Name two benchmark tools that disagree on TPOT for the same run and explain why.

## The Problem · 问题在哪

「我们的吞吐量是每秒 15,000 个 token。」所以呢？如果 40% 的请求端到端耗时冲破 2 秒，用户早已放弃这个会话。单看吞吐量，回答不了「产品到底行不行」。

推理延迟有多个维度，每个维度以不同的方式失败。Prefill 是算力瓶颈（compute-bound），随提示长度增长；decode 是访存瓶颈（memory-bound），随批大小增长；排队延迟是运维问题；网络是物理距离问题。你需要为每一维准备独立的指标，需要百分位数（percentile），还需要一个能一句话回答「用户是否得到了预期体验」的复合指标——那就是 goodput。

> "Our throughput is 15,000 tokens per second." So what? If 40% of requests blew past 2 seconds end-to-end, users abandoned the session. Throughput alone does not tell you whether the product works.
> Inference has multiple axes of latency and each one fails differently. Prefill is compute-bound and scales with prompt length. Decode is memory-bound and scales with batch size. Queuing delay is an operational problem. Network is a physical-distance problem. You need distinct metrics for each, and you need percentiles, and you need a single composite that says "did the user get what they expected" — that is goodput.

## The Concept · 概念

### TTFT — time to first token · TTFT——首 token 时间

`TTFT = queue_time + network_request + prefill_time`

提示越长，prefill 越占主导。在 H100 上运行 Llama-3.3-70B FP8，一条 32k 提示的纯 prefill 约需 800 ms。排队时间是高负载下调度器的行为；网络请求是线路传输时间（含 TLS）。TTFT 是用户在任何内容流式返回之前看到的延迟。

> Prefill dominates when prompts are long. On Llama-3.3-70B FP8 on H100, a 32k prompt takes ~800 ms of pure prefill. Queue time is scheduler behavior under load. Network request is wire time including TLS. TTFT is the latency the user sees before anything streams back.

### TPOT / ITL — inter-token latency · TPOT / ITL——token 间延迟

同一个量有一堆名字。`TPOT`（每输出 token 时间）、`ITL`（token 间延迟）、`decode latency per token`——全是同一回事。它指的是第一个 token 之后，相邻两个流式 token 之间的时间。

`TPOT = (decode_forward_time + scheduler_overhead) / tokens_produced`

在同一套 Llama-3.3-70B H100 配置加 chunked prefill 上，TPOT 均值约 7 ms。如果不用 chunked prefill，当相邻序列正在做长 prefill 时，TPOT 可能飙到 50 ms。盯住 P99，别盯均值。

> Many names for one quantity. `TPOT` (time per output token), `ITL` (inter-token latency), `decode latency per token` — all the same. It is the time between consecutive streamed tokens after the first.
> On the same Llama-3.3-70B H100 stack with chunked prefill, TPOT mean ~7 ms. Without chunked prefill, during a long prefill on a neighboring sequence, TPOT can spike to 50 ms. Watch P99, not mean.

### E2E latency · E2E 延迟

`E2E = TTFT + TPOT * output_tokens + network_response`

长输出（>500 token）时，E2E 由 TPOT 主导；短输出配长提示时，E2E 由 TTFT 主导。要按输出长度分档报告 E2E。

> For long outputs (>500 tokens), E2E is TPOT-dominated. For short outputs with long prompts, E2E is TTFT-dominated. Report output-length-conditioned E2E.

### Throughput · 吞吐量

`throughput = total_output_tokens / elapsed_time`

聚合指标。它告诉你集群效率，回答不了单个请求是否健康。

> Aggregate metric. Tells you fleet efficiency. Does not tell you individual-request health.

### Goodput — the metric you actually care about · Goodput——你真正关心的指标

`goodput = fraction of requests meeting (TTFT <= a) AND (TPOT <= b) AND (E2E <= c)`

SLO 是一个多重约束：只有每一条约束都成立，请求才算「好」。Goodput 就是「好请求」的占比。60% goodput 的高吞吐是失败；99% goodput 的较低吞吐才是目标。

2026 年，goodput 是 MLPerf Inference v6.0 提交结果以及 AI 平台厂商内部 SLA 跟踪所采用的指标。

> The SLO is a multi-constraint. A request is "good" only if every constraint held. Goodput is the share. High throughput at 60% goodput is failure. Lower throughput at 99% goodput is the target.
> In 2026, goodput is the metric used in MLPerf Inference v6.0 submissions and in internal SLA tracking at AI platform providers.

### Why mean is the wrong statistic · 为什么均值是错误的统计量

LLM 延迟分布是右偏的。一个解码批次里只要混进一个长 prefill 邻居，就可能一边是 500 个 token 的 TPOT 约 7 ms，另一边是 20 个 token 的 TPOT 约 60 ms。均值 TPOT 是 9 ms，P99 TPOT 是 65 ms。用户会经常撞上 P99——这正是他们流失的原因。

永远报告三元组（P50、P90、P99）。就用户体验而言，P99 才是你该优化的那个。

> LLM latency distributions are right-skewed. A decode batch with one long-prefill neighbor can ship 500 tokens with TPOT ~7 ms and 20 tokens with TPOT ~60 ms. Mean TPOT is 9 ms. P99 TPOT is 65 ms. Users hit the P99 regularly — that is why they leave.
> Always report the triple (P50, P90, P99). For user experience, P99 is the one you optimize.

### Reference numbers — Llama-3.1-8B-Instruct on TRT-LLM, 2026 · 参考数字——2026 年 Llama-3.1-8B-Instruct on TRT-LLM

- 平均 TTFT：162 ms
- 平均 TPOT：7.33 ms
- 平均 E2E：1,093 ms
- P99 TPOT：随 chunked-prefill 配置不同，在 10-25 ms 之间浮动。

这些是 NVIDIA 公开的参考值。它们随模型规模（70B 会差 3-5 倍）、硬件（H100 vs B200 约 3 倍）和负载而变化。

> These are the published NVIDIA reference points. They change with model size (70B would show 3-5x), hardware (H100 vs B200 ~3x), and load.

### The measurement trap · 测量陷阱

2026 年最常用的两个基准工具，对同一次运行会给出不同的 TPOT：

- **NVIDIA GenAI-Perf**：ITL 计算不包含 TTFT。ITL 从第 2 个 token 起算。
- **LLMPerf**：包含 TTFT。ITL 从第 1 个 token 起算。

对一个 TTFT 500 ms、100 个输出 token 共花 700 ms 解码的请求，GenAI-Perf 报告 `ITL = 700/99 = 7.07 ms`，LLMPerf 报告 `ITL = 1200/100 = 12.00 ms`。工具的选择改变了数字。

永远注明用了哪个工具，永远公开口径定义。

> Two of the most-used 2026 benchmark tools disagree on TPOT for the same run:
> - **NVIDIA GenAI-Perf**: excludes TTFT from the ITL calculation. ITL starts from token 2.
> - **LLMPerf**: includes TTFT. ITL starts from token 1.
> For a request with TTFT 500 ms and 100 output tokens in 700 ms total decode, GenAI-Perf reports `ITL = 700/99 = 7.07 ms`, LLMPerf reports `ITL = 1200/100 = 12.00 ms`. Tool choice changes the number.
> Always state which tool. Always publish the definition.

### Constructing an SLO · 构造一个 SLO

2026 年，一个面向消费者的 70B 聊天模型的合理 SLO：

- TTFT P99 <= 800 ms。
- TPOT P99 <= 25 ms。
- 小于 300 token 的输出，E2E P99 <= 3 s。
- Goodput 目标 >= 99%。

企业级 SLO 通常收紧 TTFT（200-400 ms）、放宽 E2E。重点是：把它们写下来、三项全测、并把 goodput 当作单一复合指标来跟踪。

> A reasonable consumer-facing SLO for a 70B chat model in 2026:
> - TTFT P99 <= 800 ms.
> - TPOT P99 <= 25 ms.
> - E2E P99 <= 3 s for <300-token outputs.
> - Goodput target >= 99%.
> Enterprise SLOs tighten TTFT (200-400 ms) and loosen E2E. The point is to write them down, measure all three, and track goodput as a single composite.

### How to measure · 如何测量

- 跑真实流量，或逼真的合成流量（LLMPerf 加 `--mean-input-tokens 800 --stddev-input-tokens 300 --mean-output-tokens 150`）。
- 基准压测的并发目标设为峰值的 2 倍。
- 跑 30-50 轮，对合并样本取百分位数。
- 发布时注明工具名、工具版本、模型、硬件、并发与提示分布。

```figure
throughput-latency
```

> - Run real traffic or realistic synthetic (LLMPerf with `--mean-input-tokens 800 --stddev-input-tokens 300 --mean-output-tokens 150`).
> - Target 2x peak concurrency for the benchmark run.
> - Run 30-50 iterations, take percentiles of the combined sample.
> - Publish with tool name, tool version, model, hardware, concurrency, prompt distribution.

## Use It · 实战用法

`code/main.py` 是一个玩具级 goodput 计算器：生成合成延迟分布、套用 SLO、计算 goodput。它还在同一条 trace 上演示 GenAI-Perf 与 LLMPerf 的 TPOT 口径差异。

> `code/main.py` is a toy goodput calculator. Generate a synthetic latency distribution, apply an SLO, and compute goodput. Also shows the GenAI-Perf vs LLMPerf TPOT difference on the same trace.

## Ship It · 交付

本课产出 `outputs/skill-slo-goodput-gate.md`。给定工作负载和 SLO，它会生成一份可直接接入 CI/CD 的基准测试配方，用 goodput 而非吞吐量来卡部署。

> This lesson produces `outputs/skill-slo-goodput-gate.md`. Given a workload and SLO, it produces a CI/CD-ready benchmark recipe that gates deploys on goodput rather than throughput.

## Exercises · 练习

1. 运行 `code/main.py`，生成一个带 1% 尾部尖峰的分布。把 P99 TPOT 从 30 ms 收紧到 15 ms，goodput 会怎么变？
2. 有厂商宣称「Llama 3.3 70B H100 上 15,000 tok/s」。在采信之前，列出你会问的三个问题。
3. 为什么 chunked prefill 保护的是 P99 TPOT，而不是均值 TPOT？
4. 为一个语音助手构造面向消费者的 SLO（首 token 是被「听到」的，不是被读到的）。哪个指标对用户最可见？
5. 阅读 LLMPerf 的 README 和 GenAI-Perf 的文档，再找出三个两工具口径不一致的指标。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| TTFT | 「首 token 时间」 | 排队 + 网络 + prefill；长提示下由 prefill 主导 |
| TPOT | 「每输出 token 时间」 | 首 token 之后每 token 的访存瓶颈解码成本 |
| ITL | 「token 间延迟」 | 多数工具里等同于 TPOT（并非全部——见 GenAI-Perf） |
| E2E | 「端到端」 | TTFT + TPOT * output_len；再加响应侧网络 |
| Throughput | 「tok/s」 | 集群效率；没有延迟百分位数就是无用数字 |
| Goodput | 「SLO 达标率」 | 同时满足每一条 SLO 约束的请求占比 |
| P99 | 「尾部」 | 百分之一的最坏情形延迟；用户体验指标 |
| SLO multi-constraint | 「联合约束」 | 三条延迟上限的 AND；任何一条被违反，该请求即失败 |
| GenAI-Perf vs LLMPerf | 「工具陷阱」 | 两个工具对 ITL 是否包含 TTFT 口径不一 |

## Further Reading · 延伸阅读

- [NVIDIA NIM — LLM Benchmarking Metrics](https://docs.nvidia.com/nim/benchmarking/llm/latest/metrics.html) —— TTFT、ITL、TPOT 的权威定义。
- [Anyscale — LLM Serving Benchmarking Metrics](https://docs.anyscale.com/llm/serving/benchmarking/metrics) —— 另一套定义与测量配方。
- [BentoML — LLM Inference Metrics](https://bentoml.com/llm/inference-optimization/llm-inference-metrics) —— 真实部署上的应用级测量。
- [LLMPerf](https://github.com/ray-project/llmperf) —— 基于 Ray 的开源基准工具。
- [GenAI-Perf](https://github.com/triton-inference-server/perf_analyzer/blob/main/genai-perf/README.md) —— NVIDIA 的基准测试工具。
- [MLPerf Inference](https://mlcommons.org/benchmarks/inference-datacenter/) —— 业界公认的基于 goodput 的基准。
