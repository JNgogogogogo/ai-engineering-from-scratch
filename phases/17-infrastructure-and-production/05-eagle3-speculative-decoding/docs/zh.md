# EAGLE-3 Speculative Decoding in Production · 生产环境中的 EAGLE-3 投机解码

> 投机解码把一个快的草稿模型和目标模型配对。草稿提出 K 个 token；目标模型用一次前向完成验证；被接受的 token 是免费的。2026 年，EAGLE-3 是生产级的变体——它在目标模型的隐藏状态（而不是原始 token）上训练草稿头，把通用聊天的接受率 alpha 推进 0.6-0.8 区间。正确的问题不是「草稿多快」，而是「我的流量上 alpha 是多少？」如果 alpha 掉到约 0.55 以下，高并发下投机解码就是净负收益，因为每个被拒绝的草稿都要多付一次目标前向。本课教你先测 alpha，再翻开关。

> Speculative decoding pairs a fast draft model with the target model. The draft proposes K tokens; the target verifies in a single forward; accepted tokens are free. In 2026, EAGLE-3 is the production-grade variant — it trains a draft head on the target model's hidden states rather than on raw tokens, pushing acceptance rate alpha into the 0.6-0.8 band on general chat. The right question is not "how fast is the draft" but "what is alpha on my traffic?" If alpha drops below ~0.55, speculative decoding is net negative at high concurrency because every rejected draft costs a second target forward pass. This lesson teaches you to measure alpha first and flip the flag second.

**Type:** Learn
**Languages:** Python (stdlib, toy acceptance-rate simulator)
**Prerequisites:** Phase 17 · 04 (Serving Engine Internals), Phase 10 · 18 (Multi-Token Prediction)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 说出投机解码的三代，并解释 EAGLE-3 相对 EAGLE-2 和经典草稿模型各改变了什么。
- 定义接受率 alpha，用 alpha 和 K（草稿长度）计算期望加速比，并找出你的目标并发下的盈亏平衡 alpha。
- 解释为什么投机解码在 2026 年的 vLLM 里是 opt-in（不是默认），以及不测 alpha 就打开它为什么是生产反模式。
- 写一份测量计划：用哪个基准、哪种提示词分布、哪个并发点、以哪个指标作为门槛。

> Name the three generations of speculative decoding and explain what EAGLE-3 changes from EAGLE-2 and from a classic draft model.
> Define acceptance rate alpha, compute expected speedup from alpha and K (draft length), and identify the break-even alpha for your target concurrency.
> Explain why speculative decoding is opt-in (not default) in vLLM 2026 and why turning it on without measuring alpha is a production anti-pattern.
> Write a measurement plan: which benchmark, which prompt distribution, which concurrency point, which metric to gate on.

## The Problem · 问题在哪

Decode 是内存受限的。H100 跑 Llama 3.3 70B FP8 时，每解码一个 token 要以约 140 GB/s 读权重、产出一个 token。decode 期间 GPU 算力几乎闲置——瓶颈是 HBM 带宽，不是矩阵乘吞吐。

投机解码利用这个空隙。用便宜的草稿模型生成 K 个候选 token，然后让目标模型在单次前向里验证全部 K 个。每个被验证的 token 实际上是免费的（摊销进一次 batch-of-K 的前向，而这次前向反正目标模型也躲不掉）。

经典草稿模型方法用同家族的更小模型（Llama 3.2 1B 给 Llama 3.3 70B 起草）。能用，但接受率平庸——小模型的分布偏离目标。EAGLE、然后 EAGLE-2、然后 EAGLE-3 直接在目标模型的内部状态上训练一个轻量草稿头，草稿分布因此贴着目标走。这就是 alpha 从草稿模型的 0.4 到 EAGLE-3 的 0.6-0.8 的原因。

坑在于：EAGLE-3 在 2026 年的 vLLM 里是 opt-in。`speculative_config` 必须显式设置。没有 flag，就没有加速。不在真实流量上测 alpha 就把开关打开的团队，常常看到尾延迟变得更差，而不是更好。

> Decode is memory-bound. On an H100 running Llama 3.3 70B FP8, each decoded token reads ~140 GB/s of weights and emits one token. The GPU compute is almost idle during decode — the bottleneck is HBM bandwidth, not matmul throughput.
> Speculative decoding exploits the gap. Generate K candidate tokens with a cheap draft model, then ask the target model to verify all K in a single forward pass. Each verified token is effectively free (amortized into a batch-of-K forward the target would have had to do anyway).
> The classic draft-model approach uses a smaller model of the same family (Llama 3.2 1B drafting for Llama 3.3 70B). It works but acceptance rate is mediocre — the smaller model distribution diverges from the target. EAGLE, then EAGLE-2, then EAGLE-3 train a light draft head directly on the target model's internal states, so the draft's distribution tracks the target much more closely. That is why alpha goes from 0.4 with draft-model to 0.6-0.8 with EAGLE-3.
> The catch: EAGLE-3 is opt-in in vLLM 2026. `speculative_config` must be set explicitly. No flag, no acceleration. Teams that flip it on without measuring alpha on their real traffic often see tail latency get worse, not better.

## The Concept · 概念

### What speculative decoding actually buys · 投机解码真正买到什么

没有 spec decode 时，每 token 成本是一次目标前向。有 spec decode 时，草稿长度 K、接受率 alpha 下，每次目标前向的期望 token 数是 `1 + K * alpha`。加速比是 `(1 + K * alpha) / (1 + epsilon)`，其中 epsilon 是草稿加验证的开销。K=5、alpha=0.7 时：`(1 + 5*0.7) / (1 + 0.1) = 4.5 / 1.1 = 4.1x`。真实世界的数字聚在 2-3 倍附近，因为生产流量上 alpha 很少有那么高，而且 epsilon 在高 batch 下会变大。

> Without spec decode, per-token cost is one target forward. With spec decode at draft length K and acceptance alpha, expected tokens per target forward is `1 + K * alpha`. The speedup is `(1 + K * alpha) / (1 + epsilon)` where epsilon is draft-plus-verify overhead. For K=5, alpha=0.7: `(1 + 5*0.7) / (1 + 0.1) = 4.5 / 1.1 = 4.1x`. Real-world numbers cluster around 2-3x because alpha is rarely that high on production traffic and epsilon grows at high batch size.

### Why alpha is the only metric that matters · 为什么 alpha 是唯一重要的指标

被拒绝的 token 不会凭空消失——它们迫使目标为第一个被拒绝的 token 再跑一次前向。在 alpha 掉到 0.4 的负载上，你要付草稿开销加验证开销加重掷开销。高并发下（比如 256 并发），decode batch 本来就够大，「目标单独跑」和「目标带验证跑」之间的内存带宽差距会缩小。2026 年的大多数硬件上，alpha 低于 0.55 时 spec decode 就是净负收益。

Alpha 随负载变化。ShareGPT 风格的通用聊天上，用 ShareGPT 训练的 EAGLE-3 能到 0.6-0.8。领域特定流量（代码、医疗、法律）上，用通用数据训练的草稿头会掉到 0.4-0.6。训练一个领域专属草稿头能把 alpha 找回来——相比目标模型微调，这是个轻量、快速的训练任务。

> Rejected tokens do not disappear — they force a second target forward for the first rejected token. On a workload where alpha drops to 0.4, you pay draft overhead plus verification plus re-roll. At high concurrency (say 256 concurrent), the decode batch is already large enough that the memory-bandwidth gap between "target alone" and "target with verify" shrinks. Below alpha 0.55 on most 2026 hardware, spec decode is net negative.
> Alpha varies by workload. On ShareGPT-style general chat, EAGLE-3 trained on ShareGPT hits 0.6-0.8. On domain-specific traffic (code, medical, legal) the draft head trained on general data drops to 0.4-0.6. Training a domain-specific draft head recovers alpha — it is a light, quick training job compared to target finetuning.

### EAGLE generations at a glance · 一眼看懂 EAGLE 各代

- **经典草稿模型**：同家族的小模型。Alpha 0.3-0.5。基础设施简单——加载两个模型，草稿为每次目标前向跑 K 次前向。
- **EAGLE-1（2024）**：在目标隐藏状态（最后一层）上训练的单个草稿头。Alpha 约 0.5-0.6。在目标之上参数开销很小。
- **EAGLE-2（2025）**：自适应草稿长度和树形草稿（一次目标前向验证多个分支）。Alpha 约 0.6-0.7。草稿调度器更复杂。
- **EAGLE-3（2025-2026）**：草稿头在目标的多层（不只最后一层）上训练，对齐更好。通用聊天上 alpha 约 0.6-0.8。

> - **Classic draft model**: small model of same family. Alpha 0.3-0.5. Infrastructure simple — two models loaded, draft runs K forwards per target forward.
> - **EAGLE-1 (2024)**: single draft head trained on target hidden states (last layer). Alpha ~0.5-0.6. Small param overhead on top of target.
> - **EAGLE-2 (2025)**: adaptive draft length and tree-based drafts (verify multiple branches in one target pass). Alpha ~0.6-0.7. More complex draft scheduler.
> - **EAGLE-3 (2025-2026)**: draft head trained on multiple target layers (not just last), better alignment. Alpha ~0.6-0.8 on general chat.

### The 2026 production recipe · 2026 年的生产配方

1. 先裸跑目标模型。在目标并发下测量基线 TTFT、ITL、吞吐。
2. 通过 vLLM `speculative_config` 启用 EAGLE-3 草稿。重跑基准。
3. 记录接受率 alpha。vLLM V1 用 `spec_decode_metrics.accepted_tokens_per_request` 报告它。除以请求的草稿长度得到 alpha。
4. 如果生产流量分布上 alpha < 0.55，关掉 spec decode，或训练一个领域专属的 EAGLE-3 草稿。
5. 在生产并发下重跑。确认 P99 ITL 没有变差。

> 1. Ship target model plain. Measure baseline TTFT, ITL, throughput at target concurrency.
> 2. Enable EAGLE-3 draft via vLLM `speculative_config`. Re-run the benchmark.
> 3. Log acceptance rate alpha. vLLM V1 reports this as `spec_decode_metrics.accepted_tokens_per_request`. Divide by requested draft length to get alpha.
> 4. If alpha < 0.55 on production traffic distribution, disable spec decode or train a domain-specific EAGLE-3 draft.
> 5. At production concurrency, re-run. Confirm P99 ITL did not get worse.

### The production pitfall: P99 tail · 生产陷阱：P99 尾部

开了 spec decode 后，ITL 均值会降。不调优的话，P99 可能变差。被拒绝的草稿触发一个两遍序列（草稿 + 验证失败 + 重掷）。满 batch 时，这两遍是串行的。盯 P99 ITL，别只看 P50。

> Mean ITL drops with spec decode. P99 can get worse if you do not tune. Rejected drafts trigger a two-pass sequence (draft + verify-fail + reroll). Under full batch, those two passes serialize. Watch P99 ITL, not P50.

### Where EAGLE-3 is already deployed · EAGLE-3 已经部署在哪里

Google 在 2025 年于 AI Overviews 中部署了投机解码（质量不变，响应更快）。vLLM V1 把 `speculative_config` 作为文档化的接口提供，其特性矩阵标注 speculative decoding 与 chunked prefill 兼容。SGLang 支持 EAGLE-3，并把它作为前缀密集负载的推荐草稿路径。

> Google deployed speculative decoding in AI Overviews in 2025 (same quality, faster response). vLLM V1 ships `speculative_config` as the documented interface, and its feature matrix marks speculative decoding as compatible with chunked prefill. SGLang supports EAGLE-3 as the recommended draft path for prefix-heavy workloads.

### Break-even math in one line · 一行算清盈亏平衡

期望加速比：`S(alpha, K) = (1 + K*alpha) / (1 + verify_overhead)`。令 `S = 1` 解出 alpha：`alpha_breakeven = verify_overhead / K`。典型 verify_overhead 约 0.15、K=5 时：`alpha_breakeven = 0.03`。但那是裸 decode 算术。高并发下验证开销上升，而且 decode batch 本来就已经把内存读取摊销到多个序列上，所以实践中有效的 alpha_breakeven 会爬到约 0.45-0.55。

> Expected speedup: `S(alpha, K) = (1 + K*alpha) / (1 + verify_overhead)`. Setting `S = 1` solves for alpha: `alpha_breakeven = verify_overhead / K`. For typical verify_overhead ~0.15 and K=5: `alpha_breakeven = 0.03`. But that is the raw decode math. At high concurrency the verify overhead rises and the decode batch already amortizes memory reads across sequences, so effective alpha_breakeven climbs to ~0.45-0.55 in practice.

### When not to use speculative decoding · 什么时候不要用投机解码

- 延迟无关紧要的 batch-1 离线生成。用裸目标模型。
- 极短的输出（50 token 以下）。草稿开销和验证成本占主导。
- 没有领域训练草稿头的专门领域。Alpha 太低。
- 假定任意两个特性都能组合。查你版本的 vLLM 兼容性矩阵：v0.18.0 标注 speculative decoding 与 chunked prefill 兼容。

> - Batch-1 offline generation where latency does not matter. Use plain target.
> - Very short outputs (under 50 tokens). Draft overhead and verify cost dominate.
> - Specialized domains without a domain-trained draft head. Alpha too low.
> - Assuming every feature pair composes. Check the vLLM compatibility matrix for your version: v0.18.0 marks speculative decoding compatible with chunked prefill.

```figure
mx-speculative-tree
```

## Use It · 实战用法

`code/main.py` 在一系列 alpha 值和草稿长度 K 上模拟有/无投机解码的 decode 循环。它打印盈亏平衡 alpha、实测加速比和尾部行为。在几组 (alpha, K) 组合上跑它，看清投机解码在哪里开始不划算。

> `code/main.py` simulates a decode loop with and without speculative decoding across a range of alpha values and draft lengths K. It prints the break-even alpha, measured speedup, and tail behavior. Run it on several (alpha, K) combinations to see exactly where speculative decoding stops paying.

## Ship It · 交付

本课产出 `outputs/skill-eagle3-rollout.md`。给定目标模型、流量分布描述和并发目标，它产出一份分阶段的 EAGLE-3 上线计划——基准基线、启用配置、测量 alpha、以 alpha >= 0.55 做门槛、盯住 P99 ITL。

> This lesson produces `outputs/skill-eagle3-rollout.md`. Given a target model, traffic distribution description, and concurrency target, it produces a staged EAGLE-3 rollout plan — benchmark baseline, enable config, measure alpha, gate on alpha >= 0.55, watch P99 ITL.

## Exercises · 练习

1. 运行 `code/main.py`。K=5 时，2 倍加速需要多大的 alpha？3 倍呢？这个结果对 verify_overhead 有多敏感？
2. 假设生产流量 70% 通用聊天、30% 代码。用 ShareGPT 训练的 EAGLE-3 在通用聊天上 alpha 到 0.7；代码上 alpha 是 0.4。混合 alpha 是多少？spec decode 还是净收益吗？
3. 阅读 vLLM `speculative_config` 文档。说出三种模式（draft model、EAGLE、N-gram），并核对你的 vLLM 版本里各自能与哪些特性组合。
4. 你看到启用 EAGLE-3 后 ITL 均值降了 25%，但 P99 ITL 升了 15%。诊断并给出缓解方案。
5. 计算 Llama 3.3 70B 的 EAGLE-3 草稿头的内存成本。和用 Llama 3.2 1B 当经典草稿比呢？

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| Speculative decoding | "草稿加验证" | 用便宜模型提出 K 个 token，目标模型一次前向验证全部 K 个 |
| Acceptance rate alpha | "spec 接受率" | 草稿 token 被目标接受的比例；唯一重要的指标 |
| Draft length K | "spec k" | 草稿每次目标前向提出多少 token；典型 4-8 |
| Verify overhead epsilon | "spec 开销" | 相比纯目标前向，验证加重掷的额外成本；随 batch 增长 |
| EAGLE-3 | "最新版 EAGLE" | 2025-2026 变体；在目标多层上训练草稿头；通用聊天 alpha 0.6-0.8 |
| `speculative_config` | "vLLM 的 spec 配置" | vLLM V1 的显式 opt-in；不配置就没有加速 |
| N-gram spec decode | "N-gram 草稿" | GPU 侧用提示词内 N-gram 查表起草；与 chunked prefill 兼容 |
| Break-even alpha | "白忙一场的 alpha" | spec decode 加速为零时的 alpha；要在生产并发下盯住它 |
| Rejected-draft two-pass | "重掷成本" | 草稿被拒时的两次目标前向；推高 P99 尾部 |

## Further Reading · 延伸阅读

- [vLLM — Speculative Decoding docs](https://docs.vllm.ai/en/latest/features/spec_decode/) —— V1 中 `speculative_config` 与 chunked-prefill 兼容性的权威来源。
- [vLLM Speculative Config API](https://docs.vllm.ai/en/latest/api/vllm/config/speculative/) —— 确切的字段集合。
- [EAGLE paper (arXiv:2401.15077)](https://arxiv.org/abs/2401.15077) —— EAGLE 草稿头的原始提出。
- [EAGLE-2 paper (arXiv:2406.16858)](https://arxiv.org/abs/2406.16858) —— 自适应草稿与树形草稿。
- [UC Berkeley EECS-2025-224](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2025/EECS-2025-224.html) —— 带投机解码的高效 LLM 系统。
- [BentoML — Speculative Decoding](https://bentoml.com/llm/inference-optimization/speculative-decoding) —— 生产上线清单。
