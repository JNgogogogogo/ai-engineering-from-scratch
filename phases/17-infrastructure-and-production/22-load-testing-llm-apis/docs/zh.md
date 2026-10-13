# Load Testing LLM APIs — Why k6 and Locust Lie · LLM API 压测——为什么 k6 和 Locust 会说谎

> 传统压测工具从设计上就不适配流式响应、可变输出长度、token 级指标和 GPU 打满。大多数团队都会踩两个坑。GIL 陷阱（GIL trap）：Locust 的 token 级测量是在 Python GIL 下跑分词（tokenization）的，高并发时会跟请求生成抢资源；分词积压随之虚报 token 间延迟（inter-token latency）——瓶颈是你的客户端，不是服务端。提示词同质化陷阱（prompt-uniformity trap）：循环里发一模一样的提示词，等于只测了 token 分布上的一个点；真实流量的长度可变、前缀匹配也多样。LLMPerf 用 `--mean-input-tokens` + `--stddev-input-tokens` 修掉了这个问题。2026 年的工具选型：要 token 级精度就用 LLM 专用工具（GenAI-Perf、LLMPerf、LLM-Locust、guidellm）；**k6 v2026.1.0** + **k6 Operator 1.0 GA（2025 年 9 月）**支持流式感知、通过 TestRun/PrivateLoadZone CRD 实现 Kubernetes 原生分布式压测，最适合 CI/CD 门禁；Vegeta 负责 Go 技术栈的恒定速率打满；Locust 2.43.3 只有装上 LLM-Locust 扩展才能测流式。负载模式：稳态（steady-state）、爬坡（ramp）、尖刺（spike，测自动扩缩容）、浸泡（soak，测内存泄漏）。

> Traditional load testers were not designed for streaming responses, variable output lengths, token-level metrics, or GPU saturation. Two traps bite most teams. The GIL trap: Locust's token-level measurement runs tokenization under the Python GIL, which competes with request generation under heavy concurrency; tokenization backlog then inflates reported inter-token latency — your client is the bottleneck, not the server. The prompt-uniformity trap: identical prompts in a loop test one point on the token distribution; real traffic has variable length and diverse prefix matches. LLMPerf fixes this with `--mean-input-tokens` + `--stddev-input-tokens`. Tool mapping in 2026: LLM-specialized (GenAI-Perf, LLMPerf, LLM-Locust, guidellm) for token-level accuracy; **k6 v2026.1.0** + **k6 Operator 1.0 GA (Sept 2025)** — streaming-aware, Kubernetes-native distributed via TestRun/PrivateLoadZone CRDs, best for CI/CD gates; Vegeta for Go constant-rate saturation; Locust 2.43.3 only with LLM-Locust extension for streaming. Load patterns: steady-state, ramp, spike (autoscaling test), soak (memory leaks).

**Type:** Build
**Languages:** Python (stdlib, toy realistic-prompt generator + latency collector)
**Prerequisites:** Phase 17 · 08 (Inference Metrics), Phase 17 · 03 (GPU Autoscaling)
**Time:** ~75 minutes

---

## Learning Objectives · 学习目标

- 解释让通用压测工具在 LLM API 上「说谎」的两个反模式：GIL 陷阱（GIL trap）与提示词同质化陷阱（prompt-uniformity trap）
- 按用途选对工具：LLMPerf（基准跑分）、k6 + streaming 扩展（CI 门禁）、guidellm（大规模合成流量）、GenAI-Perf（NVIDIA 参考实现）
- 设计四种负载模式（稳态、爬坡、尖刺、浸泡），并说出每种模式各自能抓到的故障
- 用输入 token 的均值 + 标准差（而不是固定长度）构建真实的提示词分布

> Explain the two anti-patterns (GIL trap, prompt-uniformity trap) that make generic load testers lie for LLM APIs.
> Pick a tool for a given purpose: LLMPerf (benchmark run), k6 + streaming extension (CI gate), guidellm (large-scale synthetic), GenAI-Perf (NVIDIA reference).
> Design four load patterns (steady, ramp, spike, soak) and name the failure mode each catches.
> Build a realistic prompt distribution using mean + stddev of input tokens rather than fixed length.

---

## The Problem · 问题在哪

你用 k6 给 LLM 端点压了 500 并发用户，扛住了。你上线了。生产环境 200 个真实用户就把服务打挂了——P99 TTFT 飙升，GPU 全部打满。

发生了两件事。第一，k6 发的是 500 条一模一样的提示词——请求合并（request coalescing）和前缀缓存让它看起来像在处理 500 路并发解码，实际上只处理了 1 路。第二，k6 无法像人的体感那样跟踪流式响应的 token 间延迟；它看到的是一条 HTTP 连接，而不是以不同间隔陆续到达的 500 个 token。

LLM 压测是一门独立的学科。

> You k6-tested your LLM endpoint at 500 concurrent users. It held. You shipped. In production at 200 actual users the service fell over — P99 TTFT exploded, GPUs pinned. ... Load testing for LLMs is its own discipline.

---

## The Concept · 概念

### The GIL trap (Locust) · GIL 陷阱（Locust）

Locust 基于 Python，分词在客户端的 GIL 下运行。高并发时，分词器要排在请求生成后面排队。上报的 token 间延迟里混入了客户端的分词积压。你以为是服务端慢，其实是测试框架的问题。

修复：LLM-Locust 扩展把分词挪到独立进程，或者换用编译型语言的测试框架（k6，以及用 tokenizers.rs 的 LLMPerf）。

> Locust uses Python and runs tokenization client-side under the GIL. Under high concurrency the tokenizer queues behind request generation. Reported inter-token latency includes client-side tokenization backlog. You think the server is slow; it's the test harness.
> Fix: LLM-Locust extension moves tokenization to separate processes, or use a compiled-language harness (k6, LLMPerf using tokenizers.rs).

### The prompt-uniformity trap · 提示词同质化陷阱

所有已知压测工具都只让你配置一条提示词。跑 10,000 次循环，每次发出去的都是同一条。服务端每次看到的都是同一个前缀——前缀缓存命中率逼近 100%，吞吐量看起来非常漂亮。

修复：从提示词分布里采样。LLMPerf 用 `--mean-input-tokens 500 --stddev-input-tokens 150`——长度多样、内容多样。

> All known load testers let you configure one prompt. In a loop test of 10,000 iterations the exact same prompt sends each time. Server sees the same prefix every time — prefix cache hits approach 100%, throughput looks great.
> Fix: sample from a prompt distribution. LLMPerf uses `--mean-input-tokens 500 --stddev-input-tokens 150` — diverse lengths, diverse content.

### Four load patterns · 四种负载模式

1. **稳态（Steady-state）**——恒定 RPS 持续 30-60 分钟。能抓到：基线性能回退。
2. **爬坡（Ramp）**——15 分钟内把 RPS 从 0 线性加到目标值。能抓到：容量拐点、预热异常。
3. **尖刺（Spike）**——RPS 突然冲到 3-10 倍，持续 2 分钟后回落。能抓到：自动扩缩容延迟、队列打满、冷启动影响。
4. **浸泡（Soak）**——稳态跑 4-8 小时。能抓到：内存泄漏、连接池漂移、可观测性数据溢出。

> **Steady-state** — constant RPS for 30-60 min. Catches: baseline performance regressions.
> **Ramp** — linearly increase RPS from 0 to target over 15 min. Catches: capacity breakpoint, warm-up anomalies.
> **Spike** — sudden 3-10x RPS for 2 min then back. Catches: autoscaling latency, queue saturation, cold-start impact.
> **Soak** — steady-state for 4-8 hours. Catches: memory leaks, connection-pool drift, observability overflow.

### 2026 tool mapping · 2026 年工具选型

**LLMPerf**（Anyscale）——Python 外壳，分词由 Rust 支撑。均值/标准差提示词分布。流式感知。性能跑分的最佳默认选择。

**NVIDIA GenAI-Perf**——NVIDIA 官方参考实现。基于 Triton 客户端；指标覆盖最全。注意它的 ITL 不含 TTFT，而 LLMPerf 包含。同一台服务器，两个工具算出的 TPOT 不一样。

**LLM-Locust**（TrueFoundry）——修复了 GIL 陷阱的 Locust 扩展。熟悉的 Locust DSL + 流式指标。

**guidellm**——大规模合成基准测试。

**k6 v2026.1.0** + **k6 Operator 1.0 GA（2025 年 9 月）**：
- k6 本体（Go 编译型，没有 GIL）加入了流式感知指标。
- k6 Operator 用 TestRun / PrivateLoadZone CRD 做 Kubernetes 原生分布式压测。
- 最适合 CI/CD 门禁和 SLA 测试。

**Vegeta**——Go 写的，比 k6 简单。恒定速率 HTTP 打满。不感知 LLM，但适合网关 / 限流测试。

**Locust 2.43.3 原生版**——对 LLM 有 GIL 陷阱。只有配上 LLM-Locust 扩展才能用。

> **LLMPerf** (Anyscale) — Python but Rust-backed tokenization. Mean/stddev prompts. Streaming-aware. Best default for performance runs. ... **NVIDIA GenAI-Perf** — NVIDIA's reference. Uses Triton client; comprehensive metric coverage. Note its ITL excludes TTFT; LLMPerf's includes it. Two tools produce different TPOT for the same server. ... k6 itself (Go, compiled, no GIL) added streaming-aware metrics. ... k6 Operator uses TestRun / PrivateLoadZone CRDs for Kubernetes-native distributed testing. ... Best for CI/CD gates and SLA testing.

### SLA gate in CI · CI 中的 SLA 门禁

在 PR 上跑 k6，配置如下：

- 在基线 RPS 下各跑 30-50 次迭代。
- 门禁指标：P50/P95 TTFT、5xx < 5%、TPOT 低于阈值。
- 超标就打断构建（break the build）。

> Run k6 on the PR with:
> - 30-50 iterations each at baseline RPS.
> - Gate: P50/P95 TTFT, 5xx < 5%, TPOT under threshold.
> - Break the build on breach.

### Realistic prompt distribution · 真实提示词分布

优先从真实流量样本构建（如果你有），否则用公开分布（例如聊天用 ShareGPT 提示词，代码用 HumanEval）。把均值 + 标准差喂给 LLMPerf。不惜一切代价避免「一条提示词跑循环」。

> Build from real traffic samples (if you have them) or from published distributions (e.g., ShareGPT prompts for chat, HumanEval for code). Feed the mean + stddev to LLMPerf. Avoid loop-with-one-prompt at all costs.

### Numbers you should remember · 该记住的数字

- k6 Operator 1.0 GA：2025 年 9 月。
- k6 v2026.1.0：流式感知指标。
- 典型 LLMPerf 跑批：并发 X 下 100-1000 个请求。
- 典型 CI 门禁：每个 PR 30-50 次迭代。
- 四种模式：稳态、爬坡、尖刺、浸泡。

> k6 Operator 1.0 GA: September 2025.
> k6 v2026.1.0: streaming-aware metrics.
> Typical LLMPerf run: 100-1000 requests at concurrency X.
> Typical CI gate: 30-50 iterations per PR.
> Four patterns: steady, ramp, spike, soak.

```figure
load-pattern-waves
```

---

## Use It · 实战用法

`code/main.py` 模拟一次带真实提示词分布的压测，测量有效 TPOT，并演示提示词同质化陷阱。

> `code/main.py` simulates a load test with realistic prompt distribution, measures effective TPOT, and demonstrates the uniform-prompt trap.

---

## Ship It · 交付

本课产出 `outputs/skill-load-test-plan.md`。输入工作负载和 SLA，它帮你选工具并设计四种负载模式。

> This lesson produces `outputs/skill-load-test-plan.md`. Given workload and SLA, picks tool and designs the four load patterns.

---

## Exercises · 练习

1. 跑 `code/main.py`。对比同质分布与真实分布——差距在哪里？
2. 写一个 CI 门禁用的 k6 脚本：100 并发下 TTFT P95 < 800 ms，运行 5 分钟。
3. 你的浸泡测试显示内存每小时涨 50 MB。说出三个可能原因，以及区分它们所需的监控手段。
4. 尖刺测试从 10 RPS 冲到 100 RPS。如果 Karpenter + vLLM production-stack 已经就位（Phase 17 · 03 + 18），预期恢复时间是多少？
5. GenAI-Perf 报 TPOT=6ms；同一台服务器上 LLMPerf 报 TPOT=11ms。解释原因。

---

## Key Terms · 术语表

| 术语 | 人们口头说 | 实际含义 |
|------|----------------|------------------------|
| LLMPerf | 「那个 LLM 测试框架」 | Anyscale 的基准测试工具，流式感知 |
| GenAI-Perf | 「NVIDIA 的工具」 | NVIDIA 参考测试框架 |
| LLM-Locust | 「LLM 版 Locust」 | 修复 GIL 陷阱的 Locust 扩展 |
| guidellm | 「合成基准」 | 大规模合成压测工具 |
| k6 Operator | 「K8s 版 k6」 | 基于 CRD 的分布式 k6 |
| GIL trap | 「Python 客户端开销」 | 分词积压虚报延迟 |
| Prompt-uniformity trap | 「单提示词谎言」 | 同一提示词循环打满缓存，虚增吞吐 |
| Steady-state | 「恒定负载」 | 恒定 RPS 持续 N 分钟 |
| Ramp | 「线性加压」 | 在设定时长内从 0 加到目标值 |
| Spike | 「突发测试」 | 突然放大数倍再回落 |
| Soak | 「长跑测试」 | 连续数小时检测泄漏 |

---

## Further Reading · 延伸阅读

- [TianPan — Load Testing LLM Applications](https://tianpan.co/blog/2026-03-19-load-testing-llm-applications)
- [PremAI — Load Testing LLMs 2026](https://blog.premai.io/load-testing-llms-tools-metrics-realistic-traffic-simulation-2026/)
- [NVIDIA NIM — Introduction to LLM Inference Benchmarking](https://docs.nvidia.com/nim/large-language-models/1.0.0/benchmarking.html)
- [TrueFoundry — LLM-Locust](https://www.truefoundry.com/blog/llm-locust-a-tool-for-benchmarking-llm-performance)
- [LLMPerf](https://github.com/ray-project/llmperf)
- [k6 Operator](https://github.com/grafana/k6-operator)
