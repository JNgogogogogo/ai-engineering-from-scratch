# Show-o and Discrete-Diffusion Unified Models · Show-o 与离散扩散统一模型

> Transfusion 混合连续与离散表征。Show-o（Xie et al.，2024 年 8 月）反着走：文本 token 用因果下一 token 预测，图像 token 用 MaskGIT 精神的掩码离散扩散。两者共处一个 transformer，配一块混合注意力掩码。结果是在一个骨干、每个模态一个分词器、一套 loss 公式（下一 token 预测扩展成掩码预测）上，统一了 VQA、文生图、图像修复和混合模态生成。本课走一遍 Show-o 的设计 —— 为什么掩码离散扩散是一个并行、少步数的图像生成器 —— 并与 Transfusion、Emu3 对比。

> Transfusion mixes continuous and discrete representations. Show-o (Xie et al., August 2024) goes the other way: text tokens use causal next-token prediction, image tokens use masked discrete diffusion in the spirit of MaskGIT. Both sit inside one transformer with a hybrid attention mask. The result unifies VQA, text-to-image, inpainting, and mixed-modality generation on one backbone, one tokenizer per modality, one loss formulation (next-token extended to masked prediction). This lesson walks the Show-o design — why masked discrete diffusion is a parallel, few-step image generator — and contrasts with Transfusion and Emu3.

**Type:** Learn
**Languages:** Python (stdlib, masked-discrete-diffusion sampler)
**Prerequisites:** Phase 12 · 13 (Transfusion)
**Time:** ~120 minutes

## Learning Objectives · 学习目标

- 解释掩码离散扩散：先把 token 均匀掩掉、再让 transformer 恢复它们的调度。
- 在速度与质量上，比较并行图像解码（Show-o、MaskGIT）与自回归图像解码（Chameleon、Emu3）。
- 说出 Show-o 在一个 checkpoint 里完成的三个任务：T2I、VQA、图像修复（inpainting）。
- 选一个掩码调度（cosine、线性、截断），并推理它对采样质量的影响。

> Explain masked discrete diffusion: the schedule that masks tokens uniformly then asks the transformer to recover them.
> Compare parallel image decoding (Show-o, MaskGIT) to autoregressive image decoding (Chameleon, Emu3) on speed and quality.
> Name the three tasks Show-o handles in one checkpoint: T2I, VQA, image inpainting.
> Pick a masking schedule (cosine, linear, truncated) and reason about its effect on sample quality.

## The Problem · 问题在哪

Transfusion 的双 loss 训练有效，但动态更难弄 —— 连续扩散 loss 和离散 NTP loss 活在不同的数值尺度上。平衡 loss 权重是场超参搜索。架构有效但复杂。

Show-o 的答案：两个模态都保持离散（像 Chameleon），但用掩码离散扩散并行生成图像，而不是按顺序来。训练目标变成单一的掩码 token 预测，它自然地泛化了下一 token 预测。

> Transfusion's two-loss training works but has trickier dynamics — the continuous diffusion loss lives on a different numerical scale from the discrete NTP loss. Balancing loss weights is a hyperparameter search. ... Show-o's answer: keep both modalities discrete (like Chameleon), but generate images in parallel via masked discrete diffusion instead of sequentially. The training objective becomes a single masked-token-prediction that generalizes next-token-prediction naturally.

## The Concept · 概念

### Masked discrete diffusion (MaskGIT) · 掩码离散扩散（MaskGIT）

Chang et al.（2022）的原始 MaskGIT 技巧很优雅。从一张全掩码的图开始（每个 token 都是特殊的 `<MASK>` id）。每一步并行预测所有被掩的 token，然后只保留最有把握的前 K 个预测，其余重新掩上。约 8-16 轮迭代后，所有 token 都被填满。每步解除多少 token 的调度是调出来的 —— cosine 调度效果很好。

训练很简单：从 [0, 1] 均匀采样一个掩码比例，套到图像的 VQ token 上，训练 transformer 恢复被掩的那些。正是 BERT 对文本做的事，放大到图像生成。

> The original Chang et al. (2022) MaskGIT trick is elegant. Start from a fully-masked image (every token is the special `<MASK>` id). At each step, predict all masked tokens in parallel, then keep the top-K most confident predictions and re-mask the rest. ... Training is simple: sample a masking ratio uniformly from [0, 1], apply it to the image's VQ tokens, train the transformer to recover the masked ones. Exactly what BERT did for text, scaled to image generation.

### Show-o: one transformer, hybrid mask · Show-o：一个 transformer，混合掩码

Show-o 把 MaskGIT 装进因果语言模型的 transformer。注意力掩码是：

- 文本 token：因果（标准 LLM）。
- 图像 token：图像块内部完全双向（这样被掩的 token 在预测时能看到其余所有图像 token）。
- 文本到图像：文本注意先前的图像，图像注意先前的文本。

训练在以下之间交替：
1. 文本序列上的标准 NTP。
2. T2I 样本：文本 → 图像，图像 token 被掩，掩码 token 预测 loss。
3. VQA 样本：图像 → 文本，文本 token 被掩（其实就是 NTP）。

统一 loss 是 `<MASK>` token 上的交叉熵，它同时覆盖文本 NTP（只有最后一个 token 被「掩」）和图像掩码扩散（随机子集被掩）。

> Show-o puts MaskGIT inside a causal-language-model transformer. The attention mask is: text tokens causal (standard LLM); image tokens full bidirectional within the image block ... Training alternates between: standard NTP on text sequences ... The unified loss is cross-entropy on `<MASK>` tokens, which covers both text NTP (only the last token is "masked") and image masked-diffusion (random subset is masked).

### Parallel sampling · 并行采样

Show-o 约 16 步生成一张图，而不是约 1000 步（逐 token 自回归）或约 20 步（扩散）。每一步并行预测所有被掩 token；提交最有把握的前 K 个；重复。

对比：
- Chameleon / Emu3（token 间自回归）：N_tokens 次前向，每张图典型 1024-4096 次。
- Transfusion（连续扩散）：约 20 步，每步一次完整 transformer 前向。
- Show-o（掩码离散扩散）：约 16 步，每步一次完整 transformer 前向。

同等规模的模型里，Show-o 比 Chameleon 快，步数与 Transfusion 大致持平且单步成本更低（离散词表 logits vs 连续 MSE loss）。

> Show-o generates an image in ~16 steps instead of ~1000 (autoregressive per token) or ~20 (diffusion). At each step, predict all masked tokens in parallel; commit the top-K confident; repeat. ... Show-o is faster than Chameleon at similar-scale models, roughly matches Transfusion step count with lower per-step cost (discrete vocab logits vs continuous MSE loss).

### Tasks in one checkpoint · 一个 checkpoint，多个任务

Show-o 推理时支持四个任务，靠 prompt 格式选择：

- 文本生成：标准自回归文本输出。
- VQA：图像进、文本出。
- T2I：文本进，经掩码离散扩散出图像。
- Inpainting：图像带一部分被掩 token，填空。

修复能力是掩码预测训练免费送的。把 VQ token 网格的一块掩掉，喂进其余部分加一条文本 prompt，预测被掩的 token。

> Show-o supports four tasks at inference, selected by prompt format: text generation ... VQA ... T2I ... Inpainting ... The inpainting capability comes for free from the masked-prediction training. Mask a region of the VQ-token grid, feed the rest plus a text prompt, predict the masked tokens.

### Masking schedule · 掩码调度

每步解除多少 token 的调度决定质量。Show-o 推荐 cosine：

```
mask_ratio(t) = cos(pi * t / (2 * T))   # t = 0..T
```

第 0 步全掩（比例 1.0）。第 T 步全开。Cosine 把质量集中在中间段的比例上 —— 那里预测的信息量最大。线性调度也能用，但更早进入平台期。

> The schedule of how many tokens to unmask per step shapes quality. Show-o recommends cosine ... At step 0, all tokens masked (ratio 1.0). At step T, none masked. Cosine concentrates mass on mid-range ratios where prediction is most informative. Linear schedules also work but plateau faster.

### Show-o2 · Show-o2

Show-o2（2025 年续作，arXiv 2506.15564）把 Show-o 放大：更大的 LLM 基座、更好的分词器、改进的掩码调度。架构模式不变。

> Show-o2 (2025 follow-up, arXiv 2506.15564) scales Show-o: larger LLM base, better tokenizer, improved mask schedule. Same architectural pattern.

### Where Show-o sits · Show-o 的位置

2026 年的分类学：

- 离散 token + NTP：Chameleon、Emu3。简单但推理慢。
- 离散 token + 掩码扩散：Show-o、MaskGIT、LlamaGen、Muse。并行采样，但仍受分词器有损限制。
- 连续 + 扩散：Transfusion、MMDiT、DiT。质量最高，训练更复杂。
- 连续 + VLM 内 flow matching：JanusFlow、InternVL-U。最新。

按任务选：想要一个开源模型同时做 T2I + 修复 + VQA 且速度过得去，选 Show-o；质量至上、也养得起双 loss 管道，选 Transfusion。

> In the 2026 taxonomy: discrete tokens + NTP: Chameleon, Emu3 ... discrete tokens + masked diffusion: Show-o, MaskGIT, LlamaGen, Muse ... continuous + diffusion: Transfusion, MMDiT, DiT ... Pick by task: Show-o when you want T2I + inpainting + VQA in one open model with reasonable speed; Transfusion when quality is paramount and you can afford the two-loss plumbing.

```figure
masked-diffusion-unmask
```

## Use It · 实战用法

`code/main.py` 模拟 Show-o 采样：

- 一个 16 个 VQ token 的玩具网格。
- 一个 mock「transformer」，根据 prompt 和当前未掩 token 预测 logits。
- cosine 调度下 8 步的并行掩码采样。
- 打印中间状态（掩码模式演化）和最终 token。

跑一遍，看掩码一步步消融。

> `code/main.py` simulates Show-o sampling: a toy grid of 16 VQ tokens ... a mock "transformer" that predicts logits based on a prompt and the currently-unmasked tokens ... Run it, watch the mask dissolve step by step.

## Ship It · 交付

本课产出 `outputs/skill-unified-gen-model-picker.md`。给定一个既要理解（VQA、caption）又要生成（T2I、修复）、还限定开源权重的产品，它在 Show-o 家族、Transfusion/MMDiT 家族、Emu3 / Chameleon 家族之间做选择，并给出具体的折中分析。

> This lesson produces `outputs/skill-unified-gen-model-picker.md`. Given a product that needs both understanding (VQA, captioning) and generation (T2I, inpainting) with an open-weights constraint, picks between Show-o family, Transfusion/MMDiT family, and Emu3 / Chameleon family with concrete trade-offs.

## Exercises · 练习

1. 掩码离散扩散约 16 步采样。为什么不 1 步？如果第 0 步就解除全部掩码，会坏在哪？

2. 掩码扩散让修复免费。提出一个（真实或假想的）产品用例，让 Show-o 的修复能力打赢专用模型。

3. Cosine 调度 vs 线性调度：追踪 T=8 时每步未掩 token 的数量。哪个更均衡？

4. 512x512 的 Show-o 图是 1024 个 token。词表 K=16384 时，模型吐出 1024 * log2(16384) = 14,336 bit（约 1.75 KiB）数据。Stable Diffusion 输出 512*512*24 bit = 6,291,456 bit（约 768 KiB）原始像素。压缩比是多少？它买到了什么质量？

5. 读 LlamaGen（arXiv:2406.06525）。LlamaGen 的类条件自回归图像模型与 Show-o 的掩码路线有何不同？

> Masked discrete diffusion samples in ~16 steps. Why not 1? What breaks if you unmask everything at step 0? ... Cosine schedule vs linear schedule: trace the number of unmasked tokens per step for T=8. Which is more balanced? ... A 512x512 Show-o image is 1024 tokens. At vocab K=16384, the model emits 1024 * log2(16384) = 14,336 bits (~1.75 KiB) of data. Stable Diffusion outputs 512*512*24 bits = 6,291,456 bits (~768 KiB) of raw pixels. What is the compression ratio and what quality does it buy?

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Masked discrete diffusion | "MaskGIT 风格" | 训练预测被掩 token；推理时迭代解除最有把握的预测 |
| Cosine schedule | "解除掩码调度" | 掩码比例随推理步数衰减；把置信度增长集中在中间段 |
| Parallel decoding | "一次出所有 token" | 每步用一次前向预测全部被掩 token，然后提交前 K 个 |
| Hybrid attention | "因果 + 双向" | 文本 token 之间因果、图像块内双向的掩码 |
| Inpainting | "填空生成" | 以带掩 token 的图像为条件预测缺失部分；训练目标免费附带 |
| Commitment rate | "每步前 K 个" | 每轮宣布「完成」的 token 数；控制推理速度与质量的折中 |

## Further Reading · 延伸阅读

- [Xie et al. — Show-o (arXiv:2408.12528)](https://arxiv.org/abs/2408.12528)
- [Show-o2 (arXiv:2506.15564)](https://arxiv.org/abs/2506.15564)
- [Chang et al. — MaskGIT (arXiv:2202.04200)](https://arxiv.org/abs/2202.04200)
- [Sun et al. — LlamaGen (arXiv:2406.06525)](https://arxiv.org/abs/2406.06525)
- [Chang et al. — Muse (arXiv:2301.00704)](https://arxiv.org/abs/2301.00704)
