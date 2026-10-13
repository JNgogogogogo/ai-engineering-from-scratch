# Visual Autoregressive Modeling (VAR): Next-Scale Prediction · 视觉自回归建模（VAR）：下一尺度预测

扩散模型在时间上迭代采样（去噪步）。VAR 在尺度上迭代采样 —— 先预测一个 1x1 token，再 2x2，再 4x4，一直到最终分辨率，每个尺度都以前面的尺度为条件。2024 年的论文显示：VAR 在图像生成上符合 GPT 式缩放定律，并在同等算力预算下击败 DiT。本课构建其核心机制。

> Diffusion models sample iteratively in time (denoising steps). VAR samples iteratively in scale — it predicts a 1x1 token, then 2x2, then 4x4, up to the final resolution, each scale conditioning on the previous. The 2024 paper showed VAR matches GPT-style scaling laws for image generation and beats DiT at the same compute budget. This lesson builds the core mechanism.

**Type:** Build
**Languages:** Python (with PyTorch)
**Prerequisites:** Phase 7 Lesson 03 (Multi-Head Attention), Phase 8 Lesson 06 (DDPM)
**Time:** ~90 minutes

## The Problem · 问题在哪

自回归生成统治语言建模，因为它可以预测地扩展：更多算力、更多参数，带来更低困惑度、更好输出。2024 年之前，图像生成有过两次主要的自回归尝试：PixelRNN/PixelCNN（逐像素）和 DALL-E 1 / Parti / MuseGAN（在 VQ-VAE 码上逐 token）。

两者都栽在生成顺序问题上。像素和 token 排列在 2D 网格上，但 AR 模型只能按 1D 光栅顺序访问它们。一个早生成的角落像素完全不知道这张图最终会长成什么样。生成质量的扩展性比 GPT-在文本上更差，且在同等算力下从未达到扩散模型的质量。

VAR 通过改变「生成的是什么」来修复生成顺序问题。VAR 不再在空间上逐个预测图像 token，而是以递增的分辨率预测整张图。第 1 步：预测一个 1x1 token（整张图的「摘要」）。第 2 步：预测一个 2x2 的 token 网格（更粗的特征）。第 3 步：预测 4x4 网格。第 K 步：预测最终的 (H/8)x(W/8) 网格。

每个尺度都对之前所有尺度做注意力（在「尺度顺序」上因果），并在自己尺度内部并行。顺序问题就此消失：尺度 k 的整张图在一次 transformer 前向中产生。

> Autoregressive generation dominated language modeling because it scales predictably: more compute, more parameters, lower perplexity, better outputs. Image generation had two main AR attempts before 2024: PixelRNN/PixelCNN (pixel-by-pixel) and DALL-E 1 / Parti / MuseGAN (token-by-token on VQ-VAE codes).
> Both suffered from a generation-order problem. Pixels and tokens are arranged in a 2D grid, but the AR model has to visit them in a 1D raster order. An early corner pixel has no idea what the image eventually becomes. Generation quality scaled worse than GPT-on-text and never reached diffusion-model quality at matched compute.
> VAR fixes the generation-order problem by changing what is being generated. Instead of predicting image tokens one by one in space, VAR predicts a whole image at increasing resolutions. Step 1: predict a 1x1 token (the overall image "summary"). ...
> Each scale attends to all previous scales (causally in "scale order") and parallel within its own scale. The order problem disappears: the whole image at scale k is produced in one transformer pass.

## The Concept · 概念

### VQ-VAE Multi-Scale Tokenizer · VQ-VAE 多尺度分词器

VAR 需要一个**多尺度离散分词器（multi-scale discrete tokenizer）**。对图像 x，它产出一列分辨率递增的 token 网格：

```
x -> encoder -> latent f
f -> tokenize at 1x1: token grid z_1 of shape (1, 1)
f -> tokenize at 2x2: token grid z_2 of shape (2, 2)
...
f -> tokenize at (H/p)x(W/p): token grid z_K of shape (H/p, W/p)
```

每个 z_k 用同一个码本（典型大小 4096-16384）。各尺度的分词并不独立 —— 训练目标使得各尺度残差求和能重建 f：

```
f ≈ upsample(embed(z_1), target_size) + ... + upsample(embed(z_K), target_size)
```

这是**残差 VQ（residual VQ）**的一个变体。尺度 k 捕捉的是尺度 1..k-1 没捕捉到的部分。解码器取所有尺度嵌入之和，生成图像。

多尺度 VQ 分词器只训练一次（像 VQGAN 那样），然后冻结。所有生成工作都由其上的自回归模型完成。

> VAR needs a **multi-scale discrete tokenizer**. For an image x, it produces a sequence of progressively higher-resolution token grids:
> Each z_k uses the same codebook (typical size 4096-16384). The tokenization at each scale is not independent — it is trained so that summing the residuals at each scale reconstructs f:
> This is a **residual VQ** variant. Scale k captures what scales 1..k-1 missed. Decoder takes the sum of all scale embeddings and produces the image.
> The multi-scale VQ tokenizer is trained once (like VQGAN) and then frozen. All the generative work is done by the autoregressive model on top.

### Next-Scale Prediction · 下一尺度预测

生成模型是一个 transformer：它看到之前所有尺度的 token，预测下一个尺度的 token。

输入序列结构：
```
[START, z_1 tokens, z_2 tokens, z_3 tokens, ..., z_K tokens]
```

位置嵌入同时编码尺度索引和尺度内的空间位置。注意力在尺度顺序上是因果的：尺度 k、位置 (i, j) 的 token 可以注意到尺度 1..k 的所有 token，以及尺度 k 自身中按所用尺度内顺序更早出现的 token（VAR 使用固定的位置注意力、没有尺度内因果 —— 尺度内所有位置并行预测）。

训练损失：在每个尺度 k，给定所有前序尺度的 token 预测 z_k。对离散 VQ 码做交叉熵损失。与 GPT 结构相同，只是「序列」现在带上了尺度结构。

> The generative model is a transformer that sees tokens from all previous scales and predicts the tokens at the next scale.
> Position embeddings encode both scale index and spatial position within the scale. Attention is causal in scale order: token at scale k, position (i, j) can attend to all tokens at scales 1..k and to tokens at scale k itself that come earlier in whatever intra-scale order is used (VAR uses fixed positional attention with no intra-scale causality — all positions within a scale are predicted in parallel).
> Training loss: at each scale k, predict the tokens z_k given all prior-scale tokens. Cross-entropy loss on the discrete VQ codes. Same structure as GPT except the "sequence" is now scale-structured.

### Generation · 生成

推理时：
```
generate z_1 = sample from p(z_1)                    # 1 token
generate z_2 = sample from p(z_2 | z_1)              # 4 tokens in parallel
generate z_3 = sample from p(z_3 | z_1, z_2)         # 16 tokens in parallel
...
decode: f = sum of embed-and-upsample scales 1..K
image = VAE_decoder(f)
```

对 K = 10 个尺度，生成就是 10 次 transformer 前向。每次前向并行产生它的整个尺度 —— 尺度内没有逐 token 自回归。对一张 256x256 图像，这大约是 10 次前向 vs DiT 的 28-50 次。

> For K = 10 scales, generation is 10 transformer forward passes. Each pass produces its entire scale in parallel — no per-token autoregression within a scale. For a 256x256 image this is roughly 10 passes vs DiT's 28-50.

### Why Next-Scale Wins Over Next-Token · 为什么「下一尺度」赢过「下一 token」

三个结构性优势：

1. **由粗到细符合自然图像统计。** 人类视觉感知和图像数据集都呈现尺度相关的规律：低频结构稳定且可预测；高频细节以低频内容为条件。下一尺度预测正好利用了这一点。
2. **尺度内并行生成。** 不像 GPT 式 token AR，VAR 一步产出某个尺度的全部 token。有效生成长度是对数级的，而不是线性的。
3. **没有生成顺序偏差。** 尺度 k 的 token 看到整个尺度 k-1；不存在「左边」「上边」这种迫使早期 token 在后文到来之前就仓促定形的偏差。

> Three structural wins:
> 1. **Coarse-to-fine aligns with natural image statistics.** Human visual perception and image datasets both exhibit scale-dependent regularities: low-frequency structure is stable and predictable; high-frequency detail is conditional on low-frequency content. Next-scale prediction exploits this. ...
> 2. **Parallel generation within scale.** Unlike GPT-style token AR, VAR produces all tokens at a scale in one step. Effective generation length is log-scale instead of linear. ...
> 3. **No generation order bias.** Tokens at scale k see all of scale k-1; there is no "left-of" or "above" bias that forces early tokens to commit before late context is available.

### Scaling Law · 缩放定律

Tian et al. 证明：VAR 在 ImageNet 上的 FID 服从幂律缩放曲线 —— 就像 GPT 的困惑度一样。参数或算力翻倍，误差就可靠地减半。这是第一个像语言模型一样干净地展现这种缩放行为的图像生成模型。其结果是：VAR 尺度的预测可以从算力推算出来，而不再是对每个架构做经验猜测。

> Tian et al. demonstrated that VAR follows a power-law scaling curve for FID on ImageNet — just like GPT does for perplexity. Doubling parameters or compute reliably halves error. This was the first image-generative model to exhibit this kind of scaling behavior as cleanly as language models. The result is that VAR-scale predictions become predictable from compute, not empirical guesses per architecture.

### Relationship to Diffusion · 与扩散模型的关系

VAR 和扩散共享同一个「数据压缩」故事：都把生成问题拆成一串更容易的子问题。

- 扩散：逐步加噪，学习撤销一步。
- VAR：逐步加分辨率，学习预测下一个尺度。

它们是穿过同一问题的不同轴。都给出可处理的条件分布。实证上，VAR 推理更快（前向次数更少、尺度内全并行），并在类别条件的 ImageNet 上追平或击败 DiT。文本条件的 VAR（VARclip、HART）是活跃的研究方向。

> VAR and diffusion share the same data-compression story: both break the generation problem into a sequence of easier subproblems.
> - Diffusion: gradually add noise, learn to undo one step. ...
> - VAR: gradually add resolution, learn to predict the next scale. ...
> They are different axes through the problem. Both yield tractable conditional distributions. Empirically VAR is faster at inference (fewer passes, all parallel within a scale) and matches or beats DiT on class-conditional ImageNet. Text-conditional VAR (VARclip, HART) is an active research direction.

```figure
gx-var-next-scale
```

## Build It · 动手造

在 `code/main.py` 中你将：
1. 在合成「图像」数据（2D 高斯环）上构建一个微型**多尺度 VQ 分词器**。
2. 训练一个 **VAR 风格的 transformer** 做下一尺度 token 预测。
3. 调用 transformer 4 次（4 个尺度）来采样并解码。
4. 验证按尺度排序的训练让尺度内生成真正并行。

这是一个玩具实现。重点是亲眼看到尺度结构的注意力掩码和尺度内并行的生成确实在工作。

> In `code/main.py` you will:
> 1. Build a tiny **multi-scale VQ tokenizer** on synthetic "image" data (2D Gaussian rings). ...
> 2. Train a **VAR-style transformer** to next-scale-predict the tokens. ...
> 3. Sample by calling the transformer 4 times (4 scales) and decoding. ...
> 4. Verify that scale-ordered training makes generation parallel within a scale.
> This is a toy implementation. The point is to see the scale-structured attention mask and the parallel-within-scale generation actually working.

## Ship It · 交付

本课产出 `outputs/skill-var-tokenizer-designer.md` —— 一个设计多尺度分词器的 skill：尺度数量、尺度比例、码本大小、残差共享、解码器架构。

> This lesson produces `outputs/skill-var-tokenizer-designer.md` — a skill for designing a multi-scale tokenizer: number of scales, scale ratios, codebook size, residual sharing, decoder architecture.

## Exercises · 练习

1. **尺度数量消融。** 用 4、6、8、10 个尺度训练 VAR。测量重建质量 vs 自回归前向次数。尺度越多 = 残差越细 = 质量越好，但前向次数越多。

2. **码本大小。** 用 512、4096、16384 的码本大小训练分词器。码本越大重建越好，但预测越难。找出拐点。

3. **尺度内并行检查。** 对训练好的 VAR，显式测量注意力模式。在尺度 k 内，模型是注意到跨尺度位置而不注意到尺度内位置吗？验证掩码实现。

4. **VAR vs DiT 缩放。** 在同样的 ImageNet 类别条件任务上，以对齐的参数预算（例如 33M、130M、458M）训练 VAR 和 DiT。画出 FID vs 算力。VAR 应该在每个尺寸上都领先 DiT —— 在小尺度上复现论文结果。

5. **文本条件。** 扩展 VAR，让它通过 adaLN 接收文本嵌入（CLIP pooled）作为额外条件输入。这就是 HART 的配方。在文本对齐的采样上 FID 能提升多少？

> 1. **Scale count ablation.** Train VAR with 4, 6, 8, 10 scales. Measure reconstruction quality vs number of autoregressive passes. More scales = finer residuals = better quality but more passes. ...
> 2. **Codebook size.** Train tokenizers with codebook sizes 512, 4096, 16384. Larger codebooks give better reconstruction but harder prediction. Find the knee. ...
> 3. **Parallel-within-scale check.** For a trained VAR, measure the attention pattern explicitly. Within scale k, does the model attend to cross-scale positions but not intra-scale? Verify the mask implementation. ...
> 4. **VAR vs DiT scaling.** For the same ImageNet class-conditional task, train VAR and DiT at matched param budgets (e.g., 33M, 130M, 458M). Plot FID vs compute. VAR should pull ahead of DiT at each size — reproduce the paper's result at small scale. ...
> 5. **Text conditioning.** Extend VAR to take a text embedding (CLIP pooled) as an extra conditioning input via adaLN. This is the HART recipe. How much does FID improve on text-aligned sampling?

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|----------------------|
| VAR | "Visual AutoRegressive" | 通过在 VQ token 金字塔上做下一尺度预测来生成图像 |
| Next-scale prediction | "先粗后细" | 模型在分辨率递增的尺度上预测 token，以之前所有尺度为条件 |
| Multi-scale VQ tokenizer | "残差 VQ" | 产出 K 个分辨率递增 token 网格的 VQ-VAE，解码器对所有尺度求和 |
| Scale k | "金字塔第 k 层" | K 个分辨率层级之一，从 k=1 的 1x1 到 k=K 的 (H/p)x(W/p) |
| Parallel-within-scale | "每尺度一次前向" | 尺度 k 的所有 token 在一次 transformer 前向中预测，而非自回归 |
| Causal-across-scales | "按尺度排序的注意力" | 尺度 k 的 token 可以注意尺度 1..k 的全部，但不能注意尺度 k+1..K |
| Residual VQ | "可加分词" | 每个尺度的 token 编码低尺度剩下的残差；解码器对所有尺度嵌入求和 |
| VAR scaling law | "图像版 GPT 缩放" | FID 服从可预测的算力幂律，就像语言模型的困惑度 |
| HART | "VAR + 文本混合" | 文本条件 VAR 变体，把 MaskGIT 式迭代解码与 VAR 的尺度结构结合 |
| Scale position embedding | "(scale, row, col) 三元组" | 位置编码同时携带尺度索引和尺度内的空间坐标 |

## Further Reading · 延伸阅读

- [Tian et al., 2024 — "Visual Autoregressive Modeling: Scalable Image Generation via Next-Scale Prediction"](https://arxiv.org/abs/2404.02905) —— VAR 论文，权威参考
- [Peebles and Xie, 2022 — "Scalable Diffusion Models with Transformers"](https://arxiv.org/abs/2212.09748) —— DiT，扩散对比基线
- [Esser et al., 2021 — "Taming Transformers for High-Resolution Image Synthesis"](https://arxiv.org/abs/2012.09841) —— VQGAN，VAR 多尺度分词器所扩展的分词器家族
- [van den Oord et al., 2017 — "Neural Discrete Representation Learning"](https://arxiv.org/abs/1711.00937) —— VQ-VAE，离散图像分词的基础
- [Tang et al., 2024 — "HART: Efficient Visual Generation with Hybrid Autoregressive Transformer"](https://arxiv.org/abs/2410.10812) —— 文本条件的 VAR
