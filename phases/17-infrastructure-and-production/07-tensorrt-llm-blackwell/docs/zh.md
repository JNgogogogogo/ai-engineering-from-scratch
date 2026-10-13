# Hardware-Specialized Inference Compilation — FP8 and NVFP4 on Blackwell · 硬件特化的推理编译 —— Blackwell 上的 FP8 与 NVFP4

> 硬件特化的推理编译用可移植性换吞吐，而 TensorRT-LLM——只属于 NVIDIA、为 Blackwell 调优——是这笔交易最清楚的划算样本。在配 Dynamo 编排的 GB200 NVL72 上，SemiAnalysis InferenceX 测得 2026 年 Q1-Q2 一个 120B 模型每百万 token $0.012，对照 H100 + vLLM 的 $0.09/M——7 倍的经济差距。这套栈是三种浮点体制的叠加：FP8 对 KV cache 和 attention kernel 仍然关键，因为它有它们需要的动态范围；NVFP4（4 位 microscaling）负责权重和激活；multi-token prediction（MTP）和分离式 prefill/decode 在其上再叠 2-3 倍。Day-0 模型支持直接加载 FP4 权重，无需训练后转换。2026 年工程团队的坑在于：TRT-LLM 开源但 NVIDIA 专属——CUDA 和 Blackwell 特化——采用它就是用可移植性换吞吐。在下注之前，先对你的模型与硬件组合算一遍账。

> Hardware-specialized inference compilation trades portability for throughput, and TensorRT-LLM — NVIDIA-only, tuned for Blackwell — is the clearest example of the trade paying off. On GB200 NVL72 with Dynamo orchestration, SemiAnalysis InferenceX measured $0.012 per million tokens on a 120B model in Q1-Q2 2026, against $0.09/M on H100 + vLLM — a 7x economic gap. The stack is three floating-point regimes compounded: FP8 stays critical for KV cache and attention kernels because it has the dynamic range they need; NVFP4 (4-bit microscaling) handles weights and activations; multi-token prediction (MTP) and disaggregated prefill/decode add another 2-3x on top. Day-0 model support loads FP4 weights directly without post-training conversion. The catch for 2026 engineering teams: TRT-LLM is open-source but NVIDIA-specific — CUDA- and Blackwell-specialized — so adopting it trades portability for throughput. Run the math on your mix of models and hardware before committing.

**Type:** Learn
**Languages:** Python (stdlib, toy FP8/NVFP4 memory and cost calculator)
**Prerequisites:** Phase 17 · 04 (Serving Engine Internals), Phase 10 · 13 (Quantization)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 解释为什么即便权重用 NVFP4，FP8 对 KV cache 和 attention 仍然关键。
- 计算一个前沿模型在 BF16、FP8、NVFP4 下的 HBM 占用，并推理节省从哪来。
- 说出 TRT-LLM 利用的 Blackwell 专属特性（day-0 FP4、MTP、分离式 serving、all-to-all 原语）。
- 判断什么时候 TRT-LLM 的 NVIDIA 锁定值得那 7 倍的成本差距（对比 Hopper 上的 vLLM）。

> Explain why FP8 stays critical for KV cache and attention even when weights are in NVFP4.
> Compute the HBM footprint of a frontier model under BF16, FP8, and NVFP4 and reason about where the savings come from.
> Name the Blackwell-specific features TRT-LLM exploits (day-0 FP4, MTP, disaggregated serving, all-to-all primitives).
> Decide when TRT-LLM's NVIDIA-lock is worth the 7x cost gap vs vLLM on Hopper.

## The Problem · 问题在哪

2026 年推理经济学的前沿问题是「一美元多少 token」。答案取决于四个叠起来的选择：硬件代际（Hopper H100/H200 对 Blackwell B200/GB200）、精度（BF16 → FP8 → NVFP4）、serving 引擎（vLLM 对 SGLang 对 TRT-LLM）、编排（普通 对 分离式 对 Dynamo）。

Hopper 加 vLLM 上，一个 120B MoE 跑在约 $0.09 每百万 token。Blackwell 加 TRT-LLM + Dynamo 上，同一个模型跑在约 $0.012——便宜 7 倍。这个差距一部分是硬件（Blackwell 每 GPU 的 LLM 吞吐是 Hopper 的 11-15 倍），一部分是栈：FP4 权重、MTP 草稿、分离式 prefill/decode，以及为 MoE 专家通信准备的 NVLink 5 all-to-all。

在 NVIDIA 栈之外你复制不出这个数字。这就是那笔交易——可移植性换经济学。理解哪些栈选择贡献了差距的哪一份，正是本课的要点。

> The frontier of inference economics in 2026 is "how many tokens per dollar". The answer depends on four stacked choices: hardware generation (Hopper H100/H200 vs Blackwell B200/GB200), precision (BF16 → FP8 → NVFP4), serving engine (vLLM vs SGLang vs TRT-LLM), and orchestration (plain vs disaggregated vs Dynamo).
> On Hopper with vLLM, a 120B MoE runs at ~$0.09 per million tokens. On Blackwell with TRT-LLM + Dynamo, the same model runs at ~$0.012 — 7x cheaper. Some of that gap is hardware (Blackwell is 11-15x per-GPU LLM throughput vs Hopper). Some is the stack: FP4 weights, MTP draft, disaggregated prefill/decode, and NVLink 5 all-to-all for MoE expert communication.
> You cannot replicate this outside NVIDIA's stack. That is the tradeoff — portability for economics. Understanding which stack choices give which share of the gap is the point of this lesson.

## The Concept · 概念

### Why FP8 is still the floor for KV cache · 为什么 FP8 仍是 KV cache 的下限

2026 年的一个常见错误：以为 NVFP4 到处都能用。不能。KV cache 需要 FP8（8 位浮点），因为它存的是跨越很宽动态范围的 attention 键和值。把 KV 量化到 FP4 会造成灾难性的精度损失——分布的尾部掉下去，attention 分数崩塌。FP8 的指数位给了 KV cache 需要的范围。

NVFP4（2025-2026）适用于权重和激活。Microscaling：每块权重有自己的 scale factor，小块可以跨不同的动态范围而不损失每张量的 scale。对激活，FP4 也扛得住，因为激活在层内是小范围的。

典型的 Blackwell 配置：

- 权重：NVFP4（4 位 microscaling）。
- 激活：NVFP4。
- KV cache：FP8。
- Attention 累加器：FP32（softmax 稳定性）。

> A common mistake in 2026: assuming NVFP4 applies everywhere. It does not. KV cache needs FP8 (8-bit floating point) because it stores attention keys and values that span a wide dynamic range. Quantizing KV to FP4 causes catastrophic accuracy loss — the tail of the distribution drops off and attention scores collapse. FP8's exponent bits give KV cache the range it needs.
> NVFP4 (2025-2026) applies to weights and activations. Microscaling: each block of weights has its own scale factor so small blocks can span different dynamic ranges without per-tensor scale loss. For activations, FP4 holds up because activations are small-range within a layer.

### The Blackwell-specific primitives TRT-LLM uses · TRT-LLM 用到的 Blackwell 专属原语

- **Day-0 FP4 权重**：模型厂商直接发布 FP4 权重；TRT-LLM 加载时无需训练后转换。FP4 不需要 AWQ / GPTQ 那一步。
- **Multi-token prediction（MTP）**：与 EAGLE（Phase 17 · 05）同一个想法，但集成进 TRT-LLM 构建里。
- **分离式 serving**：prefill 和 decode 放在独立的 GPU 池，KV cache 经 NVLink 或 InfiniBand 传输。与 Dynamo（Phase 17 · 20）同一个想法。
- **All-to-all 通信原语**：NVLink 5 把 MoE 专家通信延迟对比 Hopper 降到 1/3。TRT-LLM 的 MoE kernel 为此调优。
- **NVFP4 + MXFP8 microscaling**：Blackwell Tensor Cores 上硬件加速的 scale factor 处理。

> - **Day-0 FP4 weights**: model providers ship FP4 weights directly; TRT-LLM loads without post-training conversion. No AWQ / GPTQ step for FP4.
> - **Multi-token prediction (MTP)**: same idea as EAGLE (Phase 17 · 05) but integrated into the TRT-LLM build.
> - **Disaggregated serving**: prefill and decode on separate GPU pools, KV cache transferred over NVLink or InfiniBand. Same idea as Dynamo (Phase 17 · 20).
> - **All-to-all communication primitives**: NVLink 5 cut MoE expert communication latency by 3x vs Hopper. TRT-LLM's MoE kernels are tuned for this.
> - **NVFP4 + MXFP8 microscaling**: hardware-accelerated scale-factor handling on Blackwell Tensor Cores.

### The numbers you should memorize · 你该背下来的数字

- HGX B200 在 GPT-OSS-120B 上经 TRT-LLM 达到 $0.02/M tokens。
- GB200 NVL72 经 Dynamo（编排 TRT-LLM）达到 $0.012/M tokens。
- H100 + vLLM 在可比负载上约 $0.09/M tokens。
- TRT-LLM 更新三个月带来 2.8 倍吞吐提升（2026 年）。
- 每 GPU LLM 吞吐，Blackwell 对 Hopper 为 11-15 倍。
- MLPerf Inference v6.0（2026 年 4 月）：Blackwell 横扫所有提交任务。

> - HGX B200 at $0.02/M tokens on GPT-OSS-120B via TRT-LLM.
> - GB200 NVL72 at $0.012/M tokens via Dynamo (orchestrating TRT-LLM).
> - H100 + vLLM ≈ $0.09/M tokens on comparable workload.
> - 2.8x throughput gain in three months of TRT-LLM updates (2026).
> - 11-15x per-GPU LLM throughput, Blackwell vs Hopper.
> - MLPerf Inference v6.0 (April 2026): Blackwell dominates every submitted task.

### What FP4 actually costs in quality · FP4 在质量上到底付出什么

NVFP4 很激进。在推理密集的负载上（思维链、数学、长上下文的代码生成），FP4 权重的退化肉眼可见。按块校准能缓解但消除不了。发布推理模型的团队常用 FP8 权重 + FP4 激活做折中，或者全程 FP8 留在 H200 上。

规则：在承诺 NVFP4 权重之前，永远先在你的评测集上验证任务质量。

> NVFP4 is aggressive. On reasoning-heavy workloads (chain-of-thought, math, code-gen with long context), FP4 weights degrade visibly. Per-block calibration mitigates but does not eliminate. Teams shipping reasoning models often use FP8 weights + FP4 activations as a compromise, or stick to H200 with FP8 throughout.
> The rule: always validate task quality on your eval set before committing to NVFP4 weights.

### Why this is an NVIDIA-lock decision · 为什么这是一个 NVIDIA 锁定决策

TRT-LLM 是 C++ + CUDA + 闭源 kernel。模型要为特定 GPU SKU 编译。不支持 AMD，不支持 Intel，不支持 ARM。如果你的基础设施战略是多厂商，TRT-LLM 对 TRT-LLM-served 这一层就是个 no-go——你仍然可以在混合硬件上用 vLLM 服务。如果你是 NVIDIA 独家，7 倍差距足以支付锁定的代价。

> TRT-LLM is C++ + CUDA + closed-source kernels. Models need to be compiled for a specific GPU SKU. No AMD, no Intel, no ARM. If your infra strategy is multi-vendor, TRT-LLM is a non-starter for the TRT-LLM-served tier — you can still serve from vLLM on mixed hardware. If you are NVIDIA-only, the 7x gap pays for the lock.

### 2026 practical recipe · 2026 年的实操配方

对一张每年 1 亿美元以上的推理账单，留在 Hopper + vLLM 上等于把 7-10 倍扔在桌上。把成本主导的负载迁到 Blackwell + TRT-LLM + Dynamo。实验层留在 H100 + vLLM 上保住模型迭代速度。每个转成 NVFP4 的模型都在上线前验证质量。

> For a $100M+ annual inference bill, running on Hopper + vLLM leaves 7-10x on the table. Migrate cost-dominant workloads to Blackwell + TRT-LLM + Dynamo. Keep experimentation tier on H100 + vLLM for model iteration speed. Validate quality on each NVFP4-converted model before production.

### The disaggregation bonus · 分离式的额外红利

TRT-LLM 的分离式 serving（独立的 prefill 与 decode 池）在 Phase 17 · 20 有深入讲解。在 Blackwell 上，乘数是叠着来的：FP4 权重 × MTP 加速 × 分离式放置 × cache 感知路由。7 倍这个数字假定的是全套栈。

> TRT-LLM's disaggregated serving (separate prefill and decode pools) is covered in depth in Phase 17 · 20. On Blackwell, the multiplier stacks: FP4 weights × MTP speedup × disaggregated placement × cache-aware routing. The 7x number assumes this full stack.

```figure
pipeline-parallel
```

## Use It · 实战用法

`code/main.py` 为一个模型在三种栈上计算 HBM 占用、decode 吞吐（内存受限区间）和 $/M-tokens：H100 + BF16 + vLLM、H100 + FP8 + vLLM、B200 + NVFP4/FP8 + TRT-LLM。跑它看叠加效应，以及每次改动各贡献了差距的哪一份。

> `code/main.py` computes HBM footprint, decode throughput (memory-bound regime), and $/M-tokens for a model across three stacks: H100 + BF16 + vLLM, H100 + FP8 + vLLM, B200 + NVFP4/FP8 + TRT-LLM. Run it to see the compounding effect and the share of the gap each change contributes.

## Ship It · 交付

本课产出 `outputs/skill-trtllm-blackwell-advisor.md`。给定负载、模型规模和年 token 量，它判断 Blackwell + TRT-LLM 栈是否值得 NVIDIA 锁定。

> This lesson produces `outputs/skill-trtllm-blackwell-advisor.md`. Given a workload, model size, and annual token volume, it decides whether the Blackwell + TRT-LLM stack is worth the NVIDIA-lock.

## Exercises · 练习

1. 运行 `code/main.py`。对一个活跃参数占 30% 的 120B MoE，计算 H100 BF16、H100 FP8、B200 NVFP4/FP8 上内存带宽受限的 decode 吞吐。最大的一次跳变来自哪？
2. 一个客户每年在 H100 + vLLM 上花 200 万美元。给定 7 倍经济差距，要在 12 个月内摊销迁移到 TRT-LLM 的成本，他们需要买多少块 Blackwell GPU？
3. 你看到 NVFP4 权重转换后 MATH 准确率掉了 3 个点。说出两条恢复路径：一条质量优先（保住 FP8 权重），一条成本优先（用领域内数据校准）。
4. 阅读 MLPerf v6.0 推理结果。哪个任务上 Blackwell 对 Hopper 的差距最小？为什么？
5. 计算一个 405B 模型在 NVFP4 权重 + FP8 KV cache、128k 上下文下需要的 HBM。单台 GB200 NVL72 节点装得下吗？

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| FP8 | "8 位浮点" | 8 位浮点；因动态范围用于 KV cache 和 attention |
| NVFP4 | "4 位 micro" | NVIDIA 的 4 位 microscaling 浮点格式；Blackwell 上的权重与激活 |
| MXFP8 | "MX 八位" | Microscaling FP8 变体；Blackwell Tensor Cores 硬件加速 |
| Day-0 FP4 | "直接发 FP4 权重" | 模型厂商直接发布 FP4 权重；没有训练后转换步骤 |
| MTP | "multi-token prediction" | TRT-LLM 内置的投机解码草稿（Phase 17 · 05） |
| Disaggregated serving | "拆开 prefill/decode" | prefill 与 decode 放在独立 GPU 池；KV 经 NVLink/IB 传输 |
| All-to-all | "MoE 专家通信" | 把 token 路由到专家 GPU 的通信模式；NVLink 5 快 3 倍 |
| InferenceX | "SemiAnalysis 推理基准" | 2026 年业界公认的每 token 成本基准 |

## Further Reading · 延伸阅读

- [NVIDIA — Blackwell Ultra MLPerf Inference v6.0](https://developer.nvidia.com/blog/nvidia-blackwell-ultra-sets-new-inference-records-in-mlperf-debut/) —— 2026 年 4 月的 MLPerf 结果。
- [NVIDIA — MoE Inference on Blackwell](https://developer.nvidia.com/blog/delivering-massive-performance-leaps-for-mixture-of-experts-inference-on-nvidia-blackwell/) —— NVLink 5 all-to-all 与 MoE kernel。
- [TensorRT-LLM Overview](https://nvidia.github.io/TensorRT-LLM/overview.html) —— 官方引擎文档。
- [NVIDIA — Introducing Dynamo](https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models/) —— TRT-LLM 之上的分离式编排。
- [MLPerf Inference](https://mlcommons.org/benchmarks/inference-datacenter/) —— 发布 Blackwell 数字的那套基准。
