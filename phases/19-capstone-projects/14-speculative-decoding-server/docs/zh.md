# Capstone 14 — Speculative-Decoding Inference Server · 毕业项目 14 —— 投机解码推理服务器

> 投机解码（speculative decoding）——便宜的草稿提议 token，目标模型一次前向完成验证——如今已是生产可用的优化手段，不再是研究技巧。vLLM 0.7 里的 EAGLE-3 在真实流量上交付 2.5-3 倍吞吐。P-EAGLE（AWS 2026）把并行投机推得更远。SGLang 的 SpecForge 在大规模下训练草稿头。Red Hat 的 Speculators hub 为常见开源模型发布了配对草稿。TensorRT-LLM 让投机解码在 NVIDIA 上成为一等公民。本次毕业项目要以 2.5 倍以上基线吞吐服务两个开源模型，并交出完整的尾延迟报告。

> Speculative decoding — a cheap draft proposes tokens, the target model verifies them in one pass — is now a production-ready optimization, not a research trick. EAGLE-3 in vLLM 0.7 ships 2.5-3x throughput on real traffic. P-EAGLE (AWS 2026) pushed parallel speculation even further. SGLang's SpecForge trained draft heads at scale. Red Hat's Speculators hub published aligned drafts for common open models. TensorRT-LLM made speculative decoding first-class on NVIDIA. ... The 2026 production serving stack is vLLM or SGLang with EAGLE-family drafts, FP8 or INT4 quantization, and HPA on queue-wait. This capstone is to serve two open models at 2.5x+ baseline throughput with a full tail-latency report.

**Type:** Capstone
**Languages:** Python (serving), C++ / CUDA (kernel inspection), YAML (configs)
**Prerequisites:** Phase 3 (deep learning), Phase 7 (transformers), Phase 10 (LLMs from scratch), Phase 17 (infrastructure)
**Phases exercised:** P3 · P7 · P10 · P17
**Time:** 30 hours

## Problem · 问题

投机解码在 2026 年已经平民化。EAGLE-3 草稿头在目标模型的隐藏态上训练，一次向前预测 N 个 token；目标模型单次前向完成验证。60-80% 的接受率换算成 2-3 倍端到端吞吐。vLLM 0.7 原生集成了它。SGLang + SpecForge 给你训练流水线。Red Hat 的 Speculators 为 Llama 3.3 70B、Qwen3-Coder-30B MoE、GPT-OSS-120B 发布配对草稿。

功夫在服务运维，不在模型本身。接受率随流量分布漂移（ShareGPT vs 代码 vs 领域数据）。被拒绝时的尾延迟比不投机还差——你必须报告多个批大小下的 p99，而不是只报稳态 tokens/sec。对比 Anthropic / OpenAI API 的每百万 token 成本是可信度杠杆。

> Speculative decoding became a commodity in 2026. EAGLE-3 draft heads train on the target model's hidden states and predict N tokens ahead; the target model verifies in a single pass. Acceptance rates of 60-80% translate to 2-3x end-to-end throughput. vLLM 0.7 integrates this natively. SGLang + SpecForge gives you the training pipeline. Red Hat's Speculators publishes aligned drafts for Llama 3.3 70B, Qwen3-Coder-30B MoE, GPT-OSS-120B.
> The craft is in the serving operations, not the model. Acceptance rate drifts with the traffic distribution (ShareGPT vs code vs domain data). Tail latency under rejection is worse than without speculation — you must report p99 at multiple batch sizes, not just steady-state tokens/sec. Cost per 1M tokens vs Anthropic / OpenAI API is the credibility lever.

## Concept · 概念

投机解码有两层。一个**草稿**模型（EAGLE-3 头、ngram，或更小的目标对齐模型）每步提议 k 个候选 token。**目标**模型一次前向验证全部 k 个；被接受的任意前缀替换贪心路径。接受率取决于草稿与目标的对齐程度以及输入分布。

在大多数流量上 EAGLE-3 胜过 ngram 草稿。P-EAGLE 用并行投机跑更深的草稿树。代价是：被拒绝时的 P99 延迟更高，因为验证那次前向更大。服务配置必须按批大小分桶报告延迟，把这个现象暴露出来。

部署用 Kubernetes。vLLM 0.7 每张 GPU 或每个张量并行分片跑一个副本。HPA 按队列等待时间而不是 CPU 自动扩缩。FP8（Marlin）和 INT4（AWQ）量化把 GPU 显存压在 H100 / H200 的包络之内。端到端报告包括吞吐、接受率、batch 1/8/32 下的 p50/p99，以及 $/1M token。

> Speculative decoding has two layers. A **draft** model (EAGLE-3 head, ngram, or smaller target-aligned model) proposes k candidate tokens per step. The **target** model verifies all k in one pass; any prefix accepted replaces the greedy path. Acceptance rate depends on draft-target alignment and the input distribution.
> EAGLE-3 beats ngram drafts on most traffic. P-EAGLE runs parallel speculation for deeper draft trees. The trade-off: P99 latency on rejection is higher because the verify pass is larger. The serving config must report batch-size-bucketed latency to surface this.
> Deployment is Kubernetes. vLLM 0.7 runs one replica per GPU or tensor-parallel shard. HPA autoscales on queue-wait rather than CPU. FP8 (Marlin) and INT4 (AWQ) quants keep GPU memory inside an H100 / H200 envelope. The end-to-end report is throughput, acceptance rate, p50/p99 at batch 1/8/32, and $/1M tokens.

## Architecture · 架构

```
request ingress
    |
    v
vLLM server (0.7) or SGLang (0.4)
    |
    +-- draft: EAGLE-3 heads | P-EAGLE parallel | ngram fallback
    +-- target: Llama 3.3 70B | Qwen3-Coder-30B | GPT-OSS-120B
    |     quantized FP8-Marlin or INT4-AWQ
    |
    v
verify pass: batch k draft tokens through target
    |
    v (accept prefix; resample for rejected suffix)
    v
token stream back to client
    |
    v
Prometheus metrics: throughput, acceptance rate, queue wait, latency p50/p99
    |
    v
HPA on queue-wait metric
```

## Stack · 技术栈

- 服务：vLLM 0.7 或 SGLang 0.4
- 投机方法：EAGLE-3 草稿头、P-EAGLE 并行投机、ngram 兜底
- 草稿训练：SpecForge（SGLang）或 Red Hat Speculators
- 目标模型：Llama 3.3 70B、Qwen3-Coder-30B MoE、GPT-OSS-120B
- 量化：FP8（Marlin）、INT4 AWQ
- 部署：Kubernetes + NVIDIA device plugin；HPA 挂队列等待指标
- 评估：ShareGPT、MT-Bench-v2、GSM8K、HumanEval，用于度量领域分布上的接受率
- 对照：TensorRT-LLM 投机解码作为厂商基线

```figure
cf-spec-decode
```

## Build It · 动手造

1. **目标模型准备。** 选 Llama 3.3 70B，用 Marlin 量化到 FP8，部署在 vLLM 0.7 下（1xH100 或 2x 张量并行）。

2. **草稿来源。** 从 Red Hat Speculators 拉一个对齐的 EAGLE-3 草稿头（或用 SpecForge 训练一个）。加载进 vLLM 的投机解码配置。

3. **基线数字。** 投机开启前：batch 1/8/32 的 tokens/s、p50/p99 延迟、GPU 利用率。发布出来。

4. **启用 EAGLE-3。** 翻配置；重跑同一基准。报告加速比、接受率、p99 尾延迟差。

5. **P-EAGLE。** 启用并行投机；度量更深的草稿树对比串行 EAGLE-3。报告 P-EAGLE 从有帮助转为有害的拐点。

6. **领域流量。** 让 ShareGPT、HumanEval、领域专属流量过同一台服务器。度量每种分布下的接受率。找出草稿何时开始漂移。

7. **第二个目标模型。** 在 Qwen3-Coder-30B MoE 上跑同一流水线。草稿更难做（MoE 路由噪声）。报告结果。

8. **K8s HPA。** 部署到 K8s，HPA 追踪 `queue_wait_ms`。演示负载翻三倍时的扩容。

9. **成本对比。** 在同一评估上计算 $/1M token，对比 Anthropic Claude Sonnet 4.7 和 OpenAI GPT-5.4。发布出来。

> 3. **Baseline numbers.** Before speculation: tokens/s at batch 1/8/32, p50/p99 latency, GPU utilization. Publish.
> 4. **Enable EAGLE-3.** Flip config; rerun the same benchmark. Report speedup, acceptance rate, p99 tail-latency delta.
> 6. **Domain traffic.** Run ShareGPT vs HumanEval vs domain-specific traffic through the same server. Measure acceptance rate per distribution. Identify when drafts drift.
> 9. **Cost comparison.** Compute $/1M tokens vs Anthropic Claude Sonnet 4.7 and OpenAI GPT-5.4 on the same eval. Publish.

## Use It · 实战用法

```
$ curl https://infer.example.com/v1/chat/completions -d '{"messages":[...]}'
[serve]     vLLM 0.7, Llama 3.3 70B FP8, EAGLE-3 active
[decode]    bs=8, accepted_tokens_per_step=3.2, acceptance_rate=0.76
[latency]   first-token 42ms, full-response 980ms (620 tokens)
[cost]      $0.34 per 1M output tokens at sustained throughput
```

## Ship It · 交付

`outputs/skill-inference-server.md` 描述交付物：一个实测过的服务栈（带投机解码）、一份完整基准报告和一个 K8s 部署。

| 权重 | 评分标准 | 度量方式 |
|:-:|---|---|
| 25 | 相对基线的实测加速 | 两个模型在质量对齐下 2.5 倍以上吞吐 |
| 20 | 真实流量上的接受率 | 按分布拆分的接受率报告 |
| 20 | P99 尾延迟纪律 | batch 1/8/32 下开关投机两种情况的 p99 |
| 20 | 运维 | K8s 部署、HPA 挂队列等待、发布平滑 |
| 15 | 报告与方法论 | 讲清楚改了什么、为什么 |
| **100** | | |

> `outputs/skill-inference-server.md` describes the deliverable. A measured serving stack with speculative decoding, a full benchmark report, and a K8s deployment.

## Exercises · 练习

1. 度量草稿落后目标一个版本时的接受率退化（例如 Llama 3.3 → 3.4 的漂移）。建一个监控告警。

2. 实现 ngram 兜底：EAGLE-3 接受率跌破阈值就切到 ngram 草稿。报告可靠性提升。

3. 跑一个受控 MoE 实验：同一个 Qwen3-Coder-30B，分别注入和不注入路由噪声。度量草稿接受率的敏感度。

4. 扩展到 H200（141 GB）。报告每个副本在模型体积上获得的空间，以及能否服务未量化的 Llama 3.3 70B。

5. 在同样的 H100 硬件上基准测试 TensorRT-LLM 投机解码。报告它在哪些地方赢过 vLLM。

> 1. Measure acceptance-rate degradation when the draft is one version behind the target (e.g., Llama 3.3 -> 3.4 drift). Build a monitoring alert.
> 5. Benchmark TensorRT-LLM speculative decoding on the same H100 hardware. Report where it wins vs vLLM.

## Key Terms · 术语表

| 术语 | 俗称 | 实际含义 |
|------|-----------------|------------------------|
| Draft model（草稿模型） | "投机者" | 提议 N 个 token 供目标验证的小模型 |
| EAGLE-3 | "2026 年的草稿架构" | 在目标隐藏态上训练的草稿头；接受率约 75% |
| P-EAGLE | "并行投机" | 一棵草稿分支树，在目标的一次前向里验证 |
| Acceptance rate（接受率） | "命中率" | 被接受而无需重采样的草稿 token 占比 |
| Quantization（量化） | "FP8 / INT4" | 用低精度权重把更大的模型塞进 GPU 显存 |
| Queue wait（队列等待） | "HPA 指标" | 请求在推理开始前于待处理队列中等待的时间 |
| Speculators hub | "对齐草稿" | Red Hat Neural Magic 的 EAGLE 草稿 hub，覆盖常见开源模型 |

## Further Reading · 延伸阅读

- [vLLM EAGLE and P-EAGLE documentation](https://docs.vllm.ai) —— 参照服务栈
- [P-EAGLE (AWS 2026)](https://aws.amazon.com/blogs/machine-learning/p-eagle-faster-llm-inference-with-parallel-speculative-decoding-in-vllm/) —— 并行投机解码论文 + 集成
- [SGLang SpecForge](https://github.com/sgl-project/SpecForge) —— 草稿头训练流水线
- [Red Hat Speculators](https://github.com/neuralmagic/speculators) —— 对齐草稿 hub
- [TensorRT-LLM speculative decoding](https://nvidia.github.io/TensorRT-LLM/) —— 厂商替代方案
- [Fireworks.ai serving architecture](https://fireworks.ai/blog) —— 商业参照
- [EAGLE-3 paper (arXiv:2503.01840)](https://arxiv.org/abs/2503.01840) —— 方法论文
- [vLLM repository](https://github.com/vllm-project/vllm) —— 代码与基准
