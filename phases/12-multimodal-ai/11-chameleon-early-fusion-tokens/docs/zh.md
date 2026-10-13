# Chameleon and Early-Fusion Token-Only Multimodal Models · Chameleon 与早融合纯 token 多模态模型

> 我们到目前为止看过的每个 VLM 都把图像和文本分开处理。视觉 token 来自视觉编码器，流进投影器，然后在 LLM 内部与文本相遇。视觉词表和文本词表从不重叠。Chameleon（Meta，2024 年 5 月）问：如果重叠会怎样？训一个 VQ-VAE，把图像变成共享词表里的离散 token 序列。每个多模态文档从此就是一条序列 —— 文本 token 和图像 token 交错，单一自回归 loss。副作用：模型能生成混合模态的输出 —— 在一次推理调用里交替输出文本和图像 token。本课读懂早融合论点，并端到端搭一个玩具版。

> Every VLM we have seen so far keeps images and text separate. Visual tokens come from a vision encoder, flow into a projector, then meet text inside the LLM. The vision and text vocabularies never overlap. Chameleon (Meta, May 2024) asked: what if they did? Train a VQ-VAE that turns an image into a sequence of discrete tokens from a shared vocabulary. Every multimodal document is now one sequence — text tokens and image tokens interleaved, a single autoregressive loss. Side effect: the model can generate mixed-modality outputs — alternating text and image tokens in a single inference call. This lesson reads the early-fusion thesis and builds a toy version end to end.

**Type:** Build
**Languages:** Python (stdlib, VQ-VAE tokenizer + interleaved decoder)
**Prerequisites:** Phase 12 · 05, Phase 8 (Generative AI)
**Time:** ~180 minutes

## Learning Objectives · 学习目标

- 解释「共享词表 + 单一 loss」为什么改变模型能做的事。
- 描述 VQ-VAE 如何把一张图变成离散序列、并与 transformer 的下一 token 目标兼容。
- 说出 Chameleon 的训练稳定技巧：QK-Norm、dropout 位置、LayerNorm 顺序。
- 比较 Chameleon 与 BLIP-2 的 Q-Former 路线，说明各自在什么时候是对的选择。

> Explain why a shared vocabulary + single loss changes what the model can do.
> Describe how a VQ-VAE tokenizes an image into a discrete sequence compatible with a transformer's next-token objective.
> Name Chameleon's training-stability tricks: QK-Norm, dropout placement, LayerNorm ordering.
> Compare Chameleon vs BLIP-2's Q-Former approach and describe when each is the right choice.

## The Problem · 问题在哪

基于适配器（adapter）的 VLM（LLaVA、BLIP-2、Qwen-VL）把文本和图像当成两种不同的东西。文本 token 走 `embed(text_token)`；图像走 `visual_encoder(image) → projector → ... pseudo_tokens`。模型有两条输入路径，在中途汇合。

三个后果：

1. LLM 只能消费图像，不能产出图像。输出只有文本。
2. 混合模态文档（像文章那样段落与图片交替）很别扭 —— 要么在模型外解析多模态输入，要么把多次生成串起来。
3. 分布错配。视觉 token 和文本 token 住在隐藏空间的不同区域，埋下细微的对齐问题。

Chameleon 拒绝这个前提：图像就是来自共享词表的离散 token 序列。在交错的文档上训练模型，一个 loss、一个自回归解码器，混合模态生成免费送。

> Adapter-based VLMs (LLaVA, BLIP-2, Qwen-VL) treat text and image as two different things. ... Three consequences: the LLM can only consume images, not emit them ... mixed-modality documents are awkward ... distributional mismatch. ... Chameleon rejects the premise: images are just sequences of discrete tokens from a shared vocabulary. Train the model on interleaved documents, one loss, one autoregressive decoder, and you unlock mixed-modality generation for free.

## The Concept · 概念

### VQ-VAE as image tokenizer · VQ-VAE 当图像分词器

这个分词器是向量量化变分自编码器（VQ-VAE）。架构：

- 编码器：CNN + ViT，把图像映射成一张空间特征图，比如 32x32 个 256 维特征。
- 码本：K 个可学习向量组成的词表（Chameleon 用 8192），同样是 256 维。
- 量化：每个空间特征按 L2 距离找最近的码本条目，把连续特征换成整数索引。
- 解码器：CNN，把量化后的特征还原回像素。

训练：VAE 重建 loss + commitment loss + 码本 loss。码本索引构成图像的离散字母表。

对 Chameleon 来说：一张图变成 32*32 = 1024 个 token，取自 8192 的词表。与文本 token（来自 LLM 的 BPE 词表，比如 32000）拼接。最终词表：40192。transformer 看到一条序列、一个 loss。

> The tokenizer is a vector-quantized variational autoencoder ... Training: VAE reconstruction loss + commitment loss + codebook loss. The codebook indices form a discrete alphabet for images. ... For Chameleon: one image becomes 32*32 = 1024 tokens drawn from a vocabulary of 8192. ... The transformer sees one sequence, one loss.

### The shared vocabulary · 共享词表

Chameleon 的词表合并了文本 token、图像 token 和模态分隔符。每个 token 有唯一 ID。输入嵌入层把每个 ID 映射成 D 维隐藏向量。输出投影把隐藏态映射回词表 logits。Softmax 选出下一个 token，不管它是什么模态。

分隔符很重要：`<image>` 和 `</image>` 标签包住图像 token 序列。生成时如果模型吐出 `<image>`，下游软件就知道接下来 1024 个 token 是 VQ 索引，要送去解码器渲染成像素。

> Chameleon's vocabulary combines text tokens, image tokens, and modality separators. Each token has a single ID. ... Separators matter: `<image>` and `</image>` tags bracket the image-token sequence. At generation time, if the model emits `<image>`, downstream software knows the next 1024 tokens are VQ indices to send to the decoder for pixel rendering.

### Mixed-modality generation · 混合模态生成

推理就是共享词表上的下一 token 预测。示例 prompt：「画一只猫并描述它。」Chameleon 吐出：

```
<image> 4821 1029 2891 ... (1024 image tokens) </image>
The cat is orange, sitting on a windowsill...
```

模型自主决定顺序 —— 可能先图后文、先文后图，或者交错。同一个解码器，同一个 loss。

对比适配器 VLM 的只能生成文本。Chameleon 重新打开了「模型输出模态」这个问题。

> Inference is next-token prediction in the shared vocabulary. Example prompt: "Draw a cat and describe it." ... The model picks the order autonomously — it may produce image then text, text then image, or interleave. Same decoder, same loss. ... Chameleon reopens the question of model output modalities.

### Training stability — QK-Norm, dropout, LayerNorm ordering · 训练稳定性 —— QK-Norm、dropout、LayerNorm 顺序

早融合训练在规模一大就不稳定。Chameleon 论文记录了三个技巧：

- QK-Norm。在注意力内部、点积之前，对 query 和 key 投影做 LayerNorm。防止深层的 logit 幅度爆炸。2024 年后的多个大模型都在用。
- Dropout 位置。每个残差相加之后都加 dropout，而不只在注意力和 MLP 之后。当图像 token 的梯度可能占主导时，需要更多正则。
- LayerNorm 顺序。残差分支用 Pre-LN（标准做法），最后一个 block 的跳连上再加一个 LN。稳定最后几层的梯度流。

没有这些技巧，34B 的 Chameleon 在多个 checkpoint 上训练发散。有了它们才能收敛。这份训练配方和架构一样是贡献。

> Early-fusion training is unstable at scale. Chameleon's paper documents three tricks: QK-Norm ... Dropout placement ... LayerNorm ordering ... Without these tricks, 34B-param Chameleon training diverged at multiple checkpoints. With them, it converges. The training recipe is as much of the contribution as the architecture.

### The tokenizer's reconstruction ceiling · 分词器的重建上限

VQ-VAE 是有损的。8192 个码本条目、每张 512x512 图 1024 个 token 的设定下，重建 PSNR 封顶在 26-28 dB 左右。生成可辨认的图够用，但明显差于连续空间扩散（Stable Diffusion 3 能到 32+ dB）。

分词器就是瓶颈。更好的分词器（MAGVIT-v2、IBQ、SBER-MoVQGAN）能抬高上限。Emu3（第 12.12 课）只靠更好的分词器就做到了 SDXL 质量的生成。

> VQ-VAE is lossy. At 8192 codebook entries and 1024 tokens per 512x512 image, reconstruction PSNR caps around 26-28 dB. ... The tokenizer is the bottleneck. Better tokenizers (MAGVIT-v2, IBQ, SBER-MoVQGAN) lift the ceiling. Emu3 (Lesson 12.12) achieves SDXL-quality generation via a better tokenizer alone.

### Chameleon vs BLIP-2 / LLaVA · Chameleon 对 BLIP-2 / LLaVA

Chameleon（早融合，共享词表）：
- 一个 loss，一个解码器。
- 能生成混合模态输出。
- 分词器是质量上限。
- 贵：推理路径上每生成一张图都要过一次 VQ-VAE 解码器。

BLIP-2 / LLaVA（晚融合，双塔分离）：
- 视觉进、只出文本。
- 复用预训练 LLM。
- 理解任务没有分词器瓶颈。
- 便宜：单次前向。

按任务选。需要图像生成，选 Chameleon 家族。只需要理解，适配器 VLM 更简单、复用的预训练算力也更多。

> Chameleon (early fusion, shared vocab): one loss, one decoder ... generates mixed-modality output ... tokenizer is the quality ceiling ... BLIP-2 / LLaVA (late fusion, separate towers): vision in, text out only ... Pick by task. If you need image generation, Chameleon family. If you only need understanding, adapter-VLM is simpler and reuses more pretrained compute.

### Fuyu and AnyGPT · Fuyu 与 AnyGPT

Fuyu（Adept，2023）是相近思路：干脆不要独立的视觉编码器，把原始图像 patch 直接当 token 走 LLM 的输入投影，没有分词器。比 Chameleon 简单，但失去共享词表的输出生成能力。

AnyGPT（Zhan et al.，2024）把 Chameleon 扩展到四个模态：文本、图像、语音、音乐。每个模态都用同样的 VQ-VAE 把戏，共享 transformer。任意到任意的生成。第 12.16 课会进一步讲。

> Fuyu (Adept, 2023) is a related approach: skip the separate vision encoder entirely, feed raw image patches through the LLM's input projection as if they were tokens, no tokenizer. ... AnyGPT (Zhan et al., 2024) extends Chameleon to four modalities: text, image, speech, music. Same VQ-VAE trick for each, shared transformer. Any-to-any generation.

```figure
vq-codebook
```

## Use It · 实战用法

`code/main.py` 搭一个玩具版端到端早融合模型：

- 一个微型 VQ-VAE 风格量化器，把 8x8 patch 映射到码本索引（K=16）。
- 一个共享词表：（文本 id 0..31）+（图像 id 32..47）+（分隔符 48、49）。
- 一个玩具自回归解码器（bigram 表），在合成 caption + 图像 token 序列上训练。
- 一个采样循环，给定 prompt 交替吐出文本 + 图像 token。

代码刻意让 transformer 保持极小（bigram），好让你端到端追踪信号流。

> `code/main.py` builds a toy end-to-end early-fusion model: a tiny VQ-VAE-style quantizer ... a shared vocabulary ... a toy autoregressive decoder (bigram table) ... The code intentionally keeps the transformer tiny (bigrams) so you can trace the signal flow end to end.

## Ship It · 交付

本课产出 `outputs/skill-tokenizer-vs-adapter-picker.md`。给定产品规格（只要理解，还是要理解 + 生成；要求的图像质量；成本预算），它在 Chameleon 家族（早融合）与 LLaVA 家族（晚融合）之间做选择，并用量化的经验法则给出理由。

> This lesson produces `outputs/skill-tokenizer-vs-adapter-picker.md`. Given a product spec (understand only vs understand + generate, required image quality, cost budget), it picks between Chameleon-family (early fusion) and LLaVA-family (late fusion) and justifies with quantitative rules of thumb.

## Exercises · 练习

1. Chameleon 用 K=8192 的码本、每张 512x512 图 1024 个 token。估算相对 24 位 RGB 图的压缩比。有损吗？损多少？

2. 同样 VQ-VAE 密度下，一张 4K 图（3840x2160）产出多少图像 token？Chameleon 式模型能一次推理生成 4K 图吗？最先崩的是什么 —— 上下文、分词器质量，还是 KV cache？

3. 用纯 Python 实现 QK-Norm。给定 64 维 query 和 key，展示 LayerNorm 前后的点积。为什么深层需要幅度控制？

4. 读 Chameleon 第 2.3 节训练稳定性。描述论文在 34B 无 QK-Norm 时观察到的确切失败模式。「norm 爆炸」的信号是什么？

5. 扩展玩具解码器，让它在纯文本 prompt 下生成混合模态响应。训练数据分布为 60% 文本先行 / 40% 图像先行时，测量模型选图像先行 vs 文本先行的频率。

> Chameleon uses K=8192 codebook entries and 1024 tokens per 512x512 image. Estimate the compression ratio vs a 24-bit RGB image. Is it lossy? How lossy? ... Implement QK-Norm in pure Python. Given a 64-dim query and key, show the dot product before and after LayerNorm. Why is magnitude control important at depth? ... Extend the toy decoder to emit a mixed-modality response given a text-only prompt. Measure how often the model picks image-first vs text-first given training-data distribution 60% text-first / 40% image-first.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Early fusion | "统一 token" | 图像从第 1 步起就转成共享 transformer 词表的离散 token |
| VQ-VAE | "图像分词器" | CNN + ViT + 码本，把图像映射成 transformer 能预测的整数索引 |
| Shared vocabulary | "一本字典" | 覆盖文本 + 图像 + 模态分隔符的单一 token ID 空间 |
| QK-Norm | "注意力稳定器" | 在 query 与 key 点积之前对它们做 LayerNorm，防止范数爆炸 |
| Mixed-modality generation | "文本 + 图像输出" | 一次推理自主产出交错的文本与图像 token |
| Codebook size | "K 个条目" | VQ-VAE 可量化到的离散向量个数；在压缩与保真之间做交换 |
| Tokenizer ceiling | "重建上限" | 解码 VQ token 能达到的最佳 PSNR；给模型的图像质量封顶 |

## Further Reading · 延伸阅读

- [Chameleon Team — Chameleon: Mixed-Modal Early-Fusion Foundation Models (arXiv:2405.09818)](https://arxiv.org/abs/2405.09818)
- [Aghajanyan et al. — CM3 (arXiv:2201.07520)](https://arxiv.org/abs/2201.07520)
- [Yu et al. — CM3Leon (arXiv:2309.02591)](https://arxiv.org/abs/2309.02591)
- [Zhan et al. — AnyGPT (arXiv:2402.12226)](https://arxiv.org/abs/2402.12226)
- [Adept — Fuyu-8B blog (adept.ai)](https://www.adept.ai/blog/fuyu-8b)
