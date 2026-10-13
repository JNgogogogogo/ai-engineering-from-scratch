# Janus-Pro: Decoupled Encoders for Unified Multimodal Models · Janus-Pro：统一多模态模型的解耦编码器

> 统一多模态模型有一个躲不开的矛盾。理解侧想要语义特征 —— SigLIP 或 DINOv2 输出的、饱含概念级信息的向量。生成侧想要利于重建的编码 —— 能重新拼回清晰像素的 VQ token。这两个目标在单个编码器里无法兼得。Janus（DeepSeek，2024 年 10 月）和 Janus-Pro（DeepSeek，2025 年 1 月）主张：别再硬凑了，直接解耦两个编码器。Transformer 主体在两个任务之间共享，但理解走 SigLIP 路由，生成走 VQ tokenizer 路由。在 7B 规模上，Janus-Pro 在 GenEval 上击败 DALL-E 3，同时在 MMMU 上追平 LLaVA。本课解读为什么两个编码器能成，一个反而失败。

> Unified multimodal models have an unavoidable tension. Understanding wants semantic features — SigLIP or DINOv2 output vectors rich with concept-level information. Generation wants reconstruction-friendly codes — VQ tokens that compose back into crisp pixels. The two goals are not compatible in a single encoder. Janus (DeepSeek, October 2024) and Janus-Pro (DeepSeek, January 2025) argue the fix is to stop trying: decouple the two encoders. Share the transformer body between tasks, but route understanding through SigLIP and generation through a VQ tokenizer. At 7B, Janus-Pro beats DALL-E 3 on GenEval while matching LLaVA on MMMU. This lesson reads why two encoders work where one fails.

**Type:** Build
**Languages:** Python (stdlib, dual-encoder routing + shared-body signal)
**Prerequisites:** Phase 12 · 13 (Transfusion), Phase 12 · 14 (Show-o)
**Time:** ~120 minutes

## Learning Objectives · 学习目标

- 解释为什么单一共享编码器会让理解或生成的质量打折扣。
- 描述 Janus-Pro 的路由设计：理解走输入侧的 SigLIP 特征，生成的输入与输出都走 VQ token。
- 梳理数据配比扩展如何让 Janus-Pro 在 Janus 失败之处取得成功。
- 对比解耦（Janus-Pro）、耦合连续（Transfusion）与耦合离散（Show-o）三种架构。

> Explain why a single shared encoder compromises either understanding or generation quality.
> Describe Janus-Pro's routing: SigLIP features on the input side for understanding, VQ tokens on both input and output for generation.
> Trace the data-mix scaling that makes Janus-Pro succeed where Janus did not.
> Compare decoupled (Janus-Pro), coupled-continuous (Transfusion), and coupled-discrete (Show-o) architectures.

## The Problem · 问题在哪

统一模型让理解与生成共享同一个 Transformer 主体。此前的尝试（Chameleon、Show-o、Transfusion）都在两个方向上使用同一个视觉 tokenizer。这个 tokenizer 只能是个折中：

- 为重建（生成）优化：VQ-VAE 能捕捉细粒度的像素细节，但产出的 token 语义连贯性弱。
- 为语义（理解）优化：SigLIP 嵌入会把「猫」的图像聚在「cat」token 附近，却无法支撑良好的重建。

Show-o 和 Transfusion 为此在其中一个方向上付出了肉眼可见的质量税。Janus-Pro 反问：既然两个任务需求不同，为什么非要用一个 tokenizer？

> Unified models share a transformer body across understanding and generation. Previous attempts (Chameleon, Show-o, Transfusion) all use one visual tokenizer for both directions. The tokenizer is a compromise: ... Show-o and Transfusion pay for this with a visible quality tax on one direction. Janus-Pro asks: why require one tokenizer when the tasks have different needs?

## The Concept · 概念

### Decoupled visual encoding · 解耦视觉编码

Janus-Pro 的架构把两个编码器分开：

- 理解路径：输入图像 → SigLIP-SO400m → 2 层 MLP → Transformer 主体。
- 生成路径：输入图像（若以已有图像为条件）→ VQ tokenizer → token ID → Transformer 主体。
- 输出生成：Transformer 预测的图像 token → VQ 解码器 → 像素。

Transformer 主体是共享的。主体的上下游一切组件都是任务专属的。

输入靠提示词格式来区分：`<understand>` 标签路由到 SigLIP；`<generate>` 路由到 VQ。或者由任务隐式决定路由。

> Janus-Pro's architecture separates the two encoders: ... The transformer body is shared. Everything upstream and downstream of the body is task-specific. ... Inputs are disambiguated by prompt format: a `<understand>` tag routes through SigLIP; `<generate>` routes through VQ. Or the routing is implicit from task.

### Why this works · 为什么有效

理解损失拿到的是 SigLIP 特征，而 CLIP 式预训练早已把它们调校得适合语义相似度。模型在感知类基准上超过 Show-o / Transfusion，原因就是输入特征更契合任务。

生成损失拿到的是 VQ token，而 tokenizer 早已把它们调校得适合重建。图像质量超过 Show-o，原因就是 VQ 编码能干净地拼回像素。

共享的 Transformer 主体面对两种输入分布（SigLIP 与 VQ），并学会同时处理两者。论断是：数据够多 + 参数够多，主体就能吸收这种切换。

> Understanding loss gets SigLIP features, which CLIP-style pretraining has tuned for semantic similarity. The model's perception benchmarks improve over Show-o / Transfusion because the input features are better for the task. ... Generation loss gets VQ tokens, which a tokenizer has tuned for reconstruction. Image quality improves over Show-o because VQ codes compose back to pixels cleanly. ... The shared transformer body sees two input distributions (SigLIP and VQ) and learns to work with both. The claim: enough data + enough parameters, the body absorbs the switching.

### Data scaling — Janus vs Janus-Pro · 数据扩展——Janus 对 Janus-Pro

Janus（原始版，arXiv 2410.13848）提出了解耦，但规模很小（1.3B 参数，数据有限）。Janus-Pro（arXiv 2501.17811）把规模拉了上去：

- 7B 参数（此前是 1.3B）。
- 阶段 1（对齐）的图文对从 72M 提升到 90M。
- 阶段 2（统一）从 26M 提升到 72M。
- 为阶段 3 新增 20 万条图像生成指令样本。

结果：Janus-Pro-7B 在 MMMU 上追平 LLaVA（60.3 对约 58），在 GenEval 上击败 DALL-E 3（0.80 对 0.67）。一个开源模型，在统一谱系的两端都有竞争力。

> Janus (original, arXiv 2410.13848) introduced the decoupling but at small scale (1.3B params, limited data). Janus-Pro (arXiv 2501.17811) scaled: ... 7B params (vs 1.3B). ... The upshot: Janus-Pro-7B matches LLaVA on MMMU (60.3 vs ~58) and beats DALL-E 3 on GenEval (0.80 vs 0.67). One open model, competitive on both sides of the unified spectrum.

### JanusFlow — the rectified flow variant · JanusFlow——整流流变体

JanusFlow（arXiv 2411.07975）把 VQ 生成路径换成整流流（rectified flow）生成路径（连续型）。拆分方式于是变成「理解用 SigLIP + 生成用整流流」。质量上限进一步抬高。架构依然是解耦编码器 + 共享主体。

> JanusFlow (arXiv 2411.07975) swaps the VQ generation path for a rectified-flow generation path (continuous). The split becomes SigLIP-for-understanding + rectified-flow-for-generation. Quality ceilings lift further. The architecture remains decoupled-encoders-shared-body.

### The shared body's job · 共享主体的职责

Transformer 主体处理统一序列，但输入来自两种分布。它的职责是：

- 理解时：消化 SigLIP 特征 + 文本 token → 自回归地产出文本。
- 生成时：消化文本 token +（可选的图像 VQ token）→ 自回归地产出图像 VQ token。

主体内部没有按模态划分的权重。它就是你在 Qwen 或 Llama 内部会看到的那种文本式 Transformer，再加上两个输入适配器。

有趣的是，这意味着 Janus-Pro 的主体可以从预训练 LLM 初始化。Janus-Pro 确实是从 DeepSeek-MoE-7B 初始化的。这个选择很关键：LLM 带来了推理能力，而纯从零训练的统一模型很难企及。

> The transformer body processes a unified sequence but with two input distributions. Its job is to: ... The body has no modality-specific weights per block. It is the text-style transformer you'd expect to find inside Qwen or Llama, plus the two input adapters. ... Janus-Pro does initialize from DeepSeek-MoE-7B. That choice matters: the LLM contributes reasoning ability that pure-from-scratch unified models struggle to reach.

### Compared to InternVL-U · 与 InternVL-U 对比

InternVL-U（第 12.10 课）是 2026 年的后续之作。它组合了：

- 原生多模态预训练（InternVL3 骨干）。
- 解耦编码器路由（SigLIP 进，VQ + 扩散头出）。
- 统一的理解 + 生成 + 编辑。

InternVL-U 把 Janus-Pro 的架构选择吸收进一个更大的框架。解耦编码器思想如今已是大规模统一模型的默认选择。

> InternVL-U (Lesson 12.10) is the 2026 follow-up. It combines: Native multimodal pretraining (InternVL3 backbone). Decoupled-encoder routing (SigLIP in, VQ + diffusion heads out). Unified understanding + generation + editing. ... InternVL-U subsumes Janus-Pro's architectural choice into a larger framework. The decoupled-encoder idea is now the default for unified models at scale.

### Limitations · 局限

解耦编码器增加了架构复杂度：要训练两个 tokenizer，维护两条输入路径，承担两套失败模式。对不需要生成的产品，Janus-Pro 属于过度设计 —— 选一个 LLaVA 系的理解模型即可。

对不需要理解的产品，Janus-Pro 属于大材小用 —— 选 Stable Diffusion 3 / Flux 即可。

对两者都需要的产品，Janus-Pro 就是当前的开源参考架构。

> Decoupled encoders add architectural complexity. Two tokenizers to train, two input paths to maintain, two sets of fail modes. For products that do not need generation, Janus-Pro is over-engineered — pick a LLaVA-family understanding model. ... For products that need both, Janus-Pro is now the reference open architecture.

```figure
l5-janus-decouple
```

## Use It · 实战用法

`code/main.py` 模拟 Janus-Pro 的路由：

- 两个模拟编码器：类 SigLIP（产出 256 维语义向量）与类 VQ（产出整数编码）。
- 一个提示词路由器，根据任务标签挑选编码器。
- 一个共享主体（替身），无论 token 由哪个编码器产出都照单处理。
- 一个从阶段 1（对齐）切换到阶段 3（指令微调）的加权采样调度。

打印 3 个示例的路由路径：图像问答、文生图、图像编辑。

> `code/main.py` simulates Janus-Pro routing: ... Two mock encoders: SigLIP-like (produces 256-dim semantic vectors) and VQ-like (produces integer codes). A prompt router that picks the encoder based on a task tag. A shared body (stand-in) that processes token sequences regardless of which encoder produced them. A switch from stage 1 (alignment) to stage 3 (instruction tune) weighted-sample schedule. ... Print the routed paths for 3 examples: image QA, T2I, image editing.

## Ship It · 交付

本课产出 `outputs/skill-decoupled-encoder-picker.md`。给定一个想在接近前沿的质量上同时统一生成与理解的产品，它会挑选 Janus-Pro、JanusFlow 或 InternVL-U，并给出具体的数据规模建议。

> This lesson produces `outputs/skill-decoupled-encoder-picker.md`. Given a product that wants unified generation + understanding at frontier-ish quality, it picks Janus-Pro, JanusFlow, or InternVL-U with a concrete data-scale recommendation.

## Exercises · 练习

1. Janus-Pro-7B 在 GenEval 上击败了 DALL-E 3。解释为什么 7B 开源模型能在生成上追平前沿闭源模型，在理解上却不能。

2. 实现一个路由函数：给定提示词文本，分类为 `understand` 或 `generate`。对「先描述一下再画张草图」这类模糊提示词，你会怎么处理？

3. JanusFlow 用整流流替换了 VQ 路径。此时 Transformer 主体输出什么？损失有什么变化？

4. 提出第四种任务，让 Janus-Pro 架构通过再加一个解耦编码器来支持。例如：图像分割（DINO 风格）、深度估计（MiDaS 风格）。

5. 阅读 Janus-Pro 论文 4.2 节关于数据扩展的内容。相对 Janus，对文生图质量提升贡献最大的是哪个数据阶段？

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|------------------------|
| 解耦编码（Decoupled encoding） | 「两个视觉编码器」 | 每个方向使用独立的 tokenizer 或编码器：理解用语义，生成用重建 |
| 共享主体（Shared body） | 「一个 Transformer」 | 单个 Transformer 处理任一编码器的输出；没有模态专属权重 |
| SigLIP 用于理解 | 「语义特征」 | CLIP 家族视觉塔，提供丰富的概念特征但重建能力差 |
| VQ 用于生成 | 「重建编码」 | 能干净解码回像素的向量量化 token |
| JanusFlow | 「整流流变体」 | Janus-Pro 换用连续 flow-matching 生成头替代 VQ |
| 路由标签（Routing tag） | 「任务标签」 | 挑选输入编码器的提示词标记（`<understand>` / `<generate>`） |

## Further Reading · 延伸阅读

- [Wu et al. — Janus (arXiv:2410.13848)](https://arxiv.org/abs/2410.13848)
- [Chen et al. — Janus-Pro (arXiv:2501.17811)](https://arxiv.org/abs/2501.17811)
- [Ma et al. — JanusFlow (arXiv:2411.07975)](https://arxiv.org/abs/2411.07975)
- [InternVL-U (arXiv:2603.09877)](https://arxiv.org/abs/2603.09877)
- [Dong et al. — DreamLLM (arXiv:2309.11499)](https://arxiv.org/abs/2309.11499)
