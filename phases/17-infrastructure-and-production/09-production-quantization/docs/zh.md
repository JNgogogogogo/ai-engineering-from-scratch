# Production Quantization — AWQ, GPTQ, GGUF K-quants, FP8, MXFP4/NVFP4 · 生产级量化——AWQ、GPTQ、GGUF K-quant、FP8、MXFP4/NVFP4

量化格式不是一个放之四海皆准的选择——它由硬件、推理引擎和工作负载共同决定。GGUF Q4_K_M 或 Q5_K_M 统治 CPU 和边缘端，通过 llama.cpp 和 Ollama 交付。当你在同一个基座模型上需要多 LoRA 时，GPTQ 在 vLLM 内取胜。AWQ 配 Marlin-AWQ 内核在 7B 级模型上跑出约 741 tok/s，并在 INT4 中拥有最好的 Pass@1——这是 2026 年数据中心生产的默认选择。FP8 在 Hopper、Ada 和 Blackwell 上仍是可靠的中间路线——近乎无损、支持广泛。NVFP4 与 MXFP4（Blackwell microscaling）很激进，需要逐模型验证。有两个坑会咬人：校准数据集必须匹配部署领域；KV cache 与权重量化是两回事——只记得「我的模型现在只有 4 GB 了」的 AWQ 教训，会忘掉生产批大小下达 10-30 GB 的 KV cache。

> Quantization format is not a universal choice — it is a function of hardware, serving engine, and workload. GGUF Q4_K_M or Q5_K_M owns CPU and edge, delivered through llama.cpp and Ollama. GPTQ wins inside vLLM when you need multi-LoRA on the same base. AWQ with Marlin-AWQ kernels delivers ~741 tok/s on a 7B class model with the best Pass@1 at INT4 — the 2026 default for datacenter production. FP8 stays the middle ground on Hopper, Ada, and Blackwell — near-lossless and widely supported. NVFP4 and MXFP4 (Blackwell microscaling) are aggressive and require per-block validation. Two traps bite teams: calibration dataset must match deployment domain, and KV cache is separate from weight quantization — the AWQ lesson "my model is 4 GB now" forgets the 10-30 GB KV cache at production batch sizes.

**Type:** Learn
**Languages:** Python（仅标准库；跨格式的玩具级显存与吞吐对比）
**Prerequisites:** Phase 10 · 13（Quantization foundations）、Phase 17 · 04（Serving Engine Internals）
**Time:** ~75 分钟

## Learning Objectives · 学习目标

- 说出 2026 年六种生产量化格式及各自的最佳适用场景（sweet spot）。
- 给定硬件（CPU vs GPU、Hopper vs Blackwell）、引擎（vLLM、TRT-LLM、llama.cpp）和工作负载（日常聊天、推理、多 LoRA），选出一种格式。
- 计算所选格式节省的权重显存，以及保持原样、未被触及的 KV cache。
- 说出会让量化模型在领域流量上退化的校准数据集陷阱。

> Name the six production quantization formats and their sweet spots in 2026.
> Pick a format given hardware (CPU vs GPU, Hopper vs Blackwell), engine (vLLM, TRT-LLM, llama.cpp), and workload (routine chat, reasoning, multi-LoRA).
> Compute the weight memory saved and the KV cache left untouched for a chosen format.
> Name the calibration-dataset pitfall that degrades quantized models on domain traffic.

## The Problem · 问题在哪

量化省的是显存和 HBM 带宽，而这正是 decode 需要的。FP16 的 70B 模型权重有 140 GB。把权重量化到 INT4（AWQ 或 GPTQ）后只要 35 GB——能塞进一张 H100 还给 KV cache 留出空间；这一点很关键，因为 128 路并发、2k 上下文时，仅 KV cache 一项就要 20-30 GB。

但量化不是免费的。激进的量化会损害质量，在重推理（reasoning-heavy）任务上尤其明显。不同格式适配不同引擎，不同硬件原生支持的精度也不同。2026 年的「格式动物园」是真实存在的，你不能照抄别人的选择——必须基于自己的技术栈来做决定。

> Quantization reduces memory and HBM bandwidth, which is exactly what decode needs. An FP16 70B model is 140 GB of weights. Quantize weights to INT4 (AWQ or GPTQ) and the model is 35 GB — fits in one H100 with room for KV cache, which matters because at 128 concurrent sequences with 2k context, KV cache alone is 20-30 GB.
> But quantization is not free. Aggressive quantization degrades quality, especially on reasoning-heavy tasks. Different formats work with different engines. Different hardware supports different precisions natively. The 2026 format zoo is real and you cannot copy someone else's choice — you have to pick based on your stack.

## The Concept · 概念

### The six formats · 六种格式

| 格式 | 位宽 | 最佳场景 | 引擎 |
|--------|------|-----------|---------|
| GGUF Q4_K_M / Q5_K_M | 4-5 | CPU、边缘设备、笔记本 | llama.cpp、Ollama |
| GPTQ | 4-8 | vLLM 上的多 LoRA | vLLM、TGI |
| AWQ | 4 | 数据中心 GPU 生产 | vLLM（Marlin-AWQ）、TGI |
| FP8 | 8 | Hopper/Ada/Blackwell 数据中心 | vLLM、TRT-LLM、SGLang |
| MXFP4 | 4 | Blackwell 多用户 | TRT-LLM |
| NVFP4 | 4 | Blackwell 多用户 | TRT-LLM |

### GGUF — the CPU/edge default · GGUF——CPU/边缘端默认

GGUF 是一种文件格式，本身并不是一种量化方案——它把多种 K-quant 变体（Q2_K、Q3_K_M、Q4_K_M、Q5_K_M、Q6_K、Q8_0）打包进同一个容器。Q4_K_M 和 Q5_K_M 是生产默认——4-5 bit 下接近 BF16 的质量。CPU 或边缘推理的最佳选择，因为 llama.cpp 是目前最快的 CPU 推理引擎。

在 vLLM 里的吞吐代价：7B 上约 93 tok/s——这种格式没有针对 GPU 内核优化。部署目标是 CPU/边缘时用 GGUF，其他情况不要用。

> GGUF is a file format, not a quantization scheme per se — it bundles K-quant variants (Q2_K, Q3_K_M, Q4_K_M, Q5_K_M, Q6_K, Q8_0) in one container. Q4_K_M and Q5_K_M are the production defaults — near-BF16 quality at 4-5 bits. Best choice for CPU or edge serving because llama.cpp is by far the fastest CPU inference engine.
> Throughput penalty in vLLM: ~93 tok/s on 7B — the format is not optimized for GPU kernels. Use GGUF when the deployment target is CPU/edge. Not otherwise.

### GPTQ — multi-LoRA in vLLM · GPTQ——vLLM 里的多 LoRA

GPTQ 是带校准环节的训练后量化（post-training quantization）算法。Marlin 内核让它在 GPU 上很快（相比非 Marlin 的 GPTQ 有 2.6 倍加速）。7B 上约 712 tok/s。

独特优势：GPTQ-Int4 在 vLLM 中支持 LoRA adapter。如果你要服务一个基座模型加 10-50 个微调变体（每个是一个 LoRA），GPTQ 就是你的路。截至 2026 年初，NVFP4 还不支持 LoRA。

> GPTQ is a post-training quantization algorithm with a calibration pass. Marlin kernels make it fast on GPU (2.6x speedup vs non-Marlin GPTQ). ~712 tok/s on 7B.
> The unique win: GPTQ-Int4 supports LoRA adapters in vLLM. If you are serving a base model plus 10-50 fine-tuned variants (each as a LoRA), GPTQ is your path. NVFP4 does not support LoRA yet as of early 2026.

### AWQ — the datacenter GPU default · AWQ——数据中心 GPU 默认

Activation-aware Weight Quantization（激活感知权重量化）。量化时保护约 1% 最显著的权重。Marlin-AWQ 内核：相比朴素实现 10.9 倍加速。7B 上约 741 tok/s，是 INT4 格式中 Pass@1 最好的。

新的 GPU 推理服务默认选 AWQ，除非你需要多 LoRA（GPTQ）或激进的 Blackwell FP4（NVFP4）。

> Activation-aware Weight Quantization. Protects the ~1% most-salient weights during quantization. Marlin-AWQ kernels: 10.9x speedup vs naive. ~741 tok/s on 7B, best Pass@1 among INT4 formats.
> Pick AWQ for new GPU serving unless you need multi-LoRA (GPTQ) or aggressive Blackwell FP4 (NVFP4).

### FP8 — the reliable middle · FP8——可靠的中间路线

8 位浮点。近乎无损，支持广泛。Hopper Tensor Core 原生加速 FP8，Blackwell 继承了这一点。当质量不容妥协（推理、医疗、代码生成）时，FP8 是 2026 年的安全默认。显存节省只有 INT4 的一半，但质量风险低得多。

> 8-bit floating point. Near-lossless. Widely supported. Hopper Tensor Cores accelerate FP8 natively. Blackwell inherits. FP8 is the safe 2026 default when quality is non-negotiable (reasoning, medical, code-gen). Memory savings are half of INT4 but quality risk is far lower.

### MXFP4 / NVFP4 — Blackwell aggressive · MXFP4 / NVFP4——Blackwell 上的激进派

Microscaling FP4。每一块权重都有自己的 scale 因子。激进，但在 Blackwell Tensor Core 上有硬件加速。相比 FP8 每 token 字节数减半——这正是 Phase 17 · 07 里的经济性赢家。

注意事项：
- 尚无 LoRA 支持（2026 年初）。
- 重推理工作负载上可见质量下降。
- 按模型在你的评测集上验证。

> Microscaling FP4. Each block of weights has its own scale factor. Aggressive but hardware-accelerated on Blackwell Tensor Cores. Halve the bytes per token versus FP8 — the economic win in Phase 17 · 07.
> Caveats:
> - No LoRA support yet (early 2026).
> - Quality drop visible on reasoning-heavy workloads.
> - Validate on your eval set per model.

### The calibration trap · 校准陷阱

AWQ 和 GPTQ 需要校准数据集——通常用 C4 或 WikiText。对领域模型（代码、医疗、法律）来说，用通用网页文本做校准，会让算法对「该保护哪些权重」做出错误决策。HumanEval 上的 Pass@1 可能掉好几分。

修复办法：用领域内数据做校准。几百条领域样本通常就够。上线前先在评测集上测。

> AWQ and GPTQ require a calibration dataset — typically C4 or WikiText. For domain models (code, medical, legal), calibrating on generic web text lets the algorithm make wrong decisions about which weights to protect. Pass@1 on HumanEval can drop several points.
> The fix: calibrate on in-domain data. Hundreds of domain samples is usually enough. Test on the eval set before shipping.

### The KV cache trap · KV cache 陷阱

AWQ 把权重压到 4 bit。KV cache 是独立的，仍保持 FP16/FP8。对一个做了 AWQ 的 70B 模型：

- 权重：约 35 GB（140 GB 压到 INT4）。
- 128 并发 × 2k 上下文的 KV cache：约 20 GB。
- 激活值：约 5 GB。
- 总计：约 60 GB——放得进 H100 80GB。

天真地宣称「我把模型量化到了 4 GB」，忘掉的是另外那 30-50 GB。请整体规划 HBM 预算。

另外，KV cache 量化（FP8 KV 或 INT8 KV）是另一个独立的选择，有自己的权衡——它直接影响注意力（attention）精度，不是白捡的便宜。

> AWQ shrinks weights to 4 bits. KV cache is separate and stays at FP16/FP8. For a 70B model with AWQ:
> - Weights: ~35 GB (INT4 from 140 GB).
> - KV cache at 128 concurrent × 2k context: ~20 GB.
> - Activations: ~5 GB.
> - Total: ~60 GB — fits on H100 80GB.
> Naively "I quantized my model to 4 GB" forgets the other 30-50 GB. Budget HBM holistically.
> Separately, KV cache quantization (FP8 KV or INT8 KV) is a different choice with its own tradeoffs — it affects attention accuracy directly and is not a free win.

### AWQ INT4 is hazardous for reasoning · AWQ INT4 对推理任务是危险的

思维链（chain-of-thought）、数学、长上下文代码生成——这些在激进量化下退化明显。AWQ INT4 在 MATH 上要掉约 3-5 分。重推理工作负载请上 FP8 或 BF16，接受显存代价。

> Chain-of-thought, math, code-gen with long context — these suffer visibly from aggressive quantization. AWQ INT4 loses ~3-5 points on MATH. For reasoning-heavy workloads, ship FP8 or BF16; accept the memory cost.

### 2026 picking guide · 2026 年选择指南

- CPU/边缘部署：GGUF Q4_K_M。完事。
- GPU 部署、日常聊天、无 LoRA：AWQ。
- GPU 部署、多 LoRA：GPTQ + Marlin。
- 推理工作负载：FP8。
- Blackwell 数据中心、质量已验证：NVFP4 + FP8 KV。
- 拿不准：对每个候选格式跑一次 1,000 样本的评测。

```figure
gpu-memory-breakdown
```

> - CPU/edge serve: GGUF Q4_K_M. Done.
> - GPU serve, routine chat, no LoRA: AWQ.
> - GPU serve, multi-LoRA: GPTQ with Marlin.
> - Reasoning workload: FP8.
> - Blackwell datacenter, validated quality: NVFP4 + FP8 KV.
> - Ambiguous: run a 1,000-sample eval on each candidate format.

## Use It · 实战用法

`code/main.py` 计算六种格式在一系列模型规模下的显存占用（权重 + KV + 激活值）与相对吞吐。它展示了 KV cache 何时占主导、权重压缩何时划算、FP8 何时是安全选择。

> `code/main.py` computes memory footprint (weights + KV + activations) and relative throughput across the six formats for a range of model sizes. Shows where KV cache dominates, where weight compression pays, and where FP8 is the safe pick.

## Ship It · 交付

本课产出 `outputs/skill-quantization-picker.md`。给定硬件、模型规模、工作负载类型和质量容忍度，它会选出一种格式并给出校准/验证计划。

> This lesson produces `outputs/skill-quantization-picker.md`. Given hardware, model size, workload type, and quality tolerance, picks a format and produces a calibration/validation plan.

## Exercises · 练习

1. 运行 `code/main.py`。对 128 并发、2k 上下文的 70B 模型，计算每种格式所需的总 HBM。哪种格式能塞进一张 H100 80GB？
2. 你有一个 7B 代码模型。选一种格式并说明理由。如果我对质量容忍度判断错了，恢复路径是什么？
3. 计算为医疗领域模型校准 AWQ 所需的校准数据集规模。为什么数据不是越多越好？
4. 阅读 Marlin-AWQ 内核论文或发布说明，用三句话解释为什么 AWQ 在 7B 上跑到 741 tok/s，而原始 GPTQ 只有约 712。
5. 什么时候值得把 AWQ 权重和 FP8 KV cache 组合，而不是让 KV 保持 BF16？

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| GGUF | 「llama.cpp 格式」 | 打包多种 K-quant 变体的文件格式；CPU/边缘端默认 |
| Q4_K_M | 「Q4 K M」 | 4-bit K-quant 中等档；生产环境 GGUF 默认 |
| GPTQ | 「G-P-T-Q」 | 带校准的训练后 INT4；在 vLLM 中支持 LoRA |
| AWQ | 「A-W-Q」 | 激活感知 INT4；Marlin 内核；INT4 中最佳 Pass@1 |
| Marlin kernels | 「快速 INT4 内核」 | Hopper 上 INT4 的定制 CUDA 内核；10 倍加速 |
| FP8 | 「8 位浮点」 | Hopper/Ada/Blackwell 上安全的精度默认 |
| MXFP4 / NVFP4 | 「microscaling 4 bit」 | Blackwell 4-bit 浮点，带按块 scale 因子 |
| Calibration dataset | 「校准数据」 | 用来挑选量化参数的输入文本；必须匹配领域 |
| KV cache quantization | 「KV INT8」 | 与权重相互独立的选择；影响注意力精度 |

## Further Reading · 延伸阅读

- [VRLA Tech — LLM Quantization 2026](https://vrlatech.com/llm-quantization-explained-int4-int8-fp8-awq-and-gptq-in-2026/) —— 对比基准测试。
- [Jarvis Labs — vLLM Quantization Complete Guide](https://jarvislabs.ai/blog/vllm-quantization-complete-guide-benchmarks) —— 按格式给出的吞吐数字。
- [PremAI — GGUF vs AWQ vs GPTQ vs bitsandbytes 2026](https://blog.premai.io/llm-quantization-guide-gguf-vs-awq-vs-gptq-vs-bitsandbytes-compared-2026/) —— 逐格式选型。
- [vLLM docs — Quantization](https://docs.vllm.ai/en/latest/features/quantization/index.html) —— 支持的格式与参数。
- [AWQ paper (arXiv:2306.00978)](https://arxiv.org/abs/2306.00978) —— AWQ 原始论文。
- [GPTQ paper (arXiv:2210.17323)](https://arxiv.org/abs/2210.17323) —— GPTQ 原始论文。
