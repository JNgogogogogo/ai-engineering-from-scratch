# Transfusion: Autoregressive Text + Diffusion Image in One Transformer · Transfusion：一个 Transformer，文本自回归 + 图像扩散

> Chameleon 和 Emu3 把一切都押在离散 token 上。它们可行，但量化瓶颈肉眼可见 —— 图像质量停在连续空间扩散模型之下。Transfusion（Meta，Zhou et al.，2024 年 8 月）反向押注：图像保持连续，彻底扔掉 VQ-VAE，用一个 transformer 训两个 loss。文本 token 走下一 token 预测。图像 patch 走 flow matching / 扩散 loss。两个目标优化同一份权重。Stable Diffusion 3 底下的架构（MMDiT）是它的近亲。本课读懂 Transfusion 论点，搭一个玩具双 loss 训练器，并追踪那块让一个 transformer 同时干两份活的注意力掩码。

> Chameleon and Emu3 bet everything on discrete tokens. They work, but the quantization bottleneck is visible — the image quality plateaus below continuous-space diffusion models. Transfusion (Meta, Zhou et al., August 2024) takes the opposite bet: keep images continuous, drop the VQ-VAE entirely, and train one transformer with two losses. Text tokens get next-token-prediction. Image patches get a flow-matching / diffusion loss. Both objectives optimize the same weights. The architecture underlying Stable Diffusion 3 (MMDiT) is a close cousin. This lesson reads the Transfusion thesis, builds a toy two-loss trainer, and traces the attention mask that lets one transformer do both jobs.

**Type:** Build
**Languages:** Python (stdlib, two-loss trainer on MNIST-scale toy)
**Prerequisites:** Phase 12 · 11 (Chameleon), Phase 8 (Generative AI)
**Time:** ~180 minutes

## Learning Objectives · 学习目标

- 在一个骨干上接好跑两个 loss（文本 token 的 NTP、图像 patch 的扩散 MSE）的 transformer。
- 解释为什么「图像 patch 之间双向注意力 + 文本 token 之上因果注意力」是正确的掩码选择。
- 在算力、质量和代码复杂度上，比较 Transfusion 式（连续图像、扩散 loss）与 Chameleon 式（离散图像、NTP）。
- 说出 MMDiT 的贡献：每个 block 里模态专属权重、残差流上的联合注意力。

> Wire a transformer that runs two losses (NTP on text tokens, diffusion MSE on image patches) on one backbone.
> Explain why bidirectional attention across image patches plus causal attention over text tokens is the right mask choice.
> Compare Transfusion-style (continuous images, diffusion loss) to Chameleon-style (discrete images, NTP) on compute, quality, and code complexity.
> Name MMDiT's contribution: modality-specific weights at each block, joint attention at the residual stream.

## The Problem · 问题在哪

离散 vs 连续图像 token 之争比 LLM 还老。连续表征（原始像素、VAE 潜变量）保细节。离散 token（VQ 索引）贴合 transformer 的原生词表，但在量化那一步丢细节。

Chameleon / Emu3 走离散：一个 loss、一个架构，但图像保真度被分词器质量封顶。

扩散模型走连续：图像质量卓越，但它是独立于 LLM 的另一个模型，噪声调度工程复杂，也没法和文本生成干净地整合。

Transfusion 问：能不能两者兼得？图像保持连续，仍然只训一个模型，把两个 loss 缝进同一次梯度步。

> The discrete vs continuous image tokens debate is older than LLMs. Continuous representations (raw pixels, VAE latents) preserve detail. Discrete tokens (VQ indices) fit the transformer's native vocabulary but lose detail at the quantization step. ... Transfusion asks: can we have both? Keep images continuous, still train one model, use two losses stitched into one gradient step.

## The Concept · 概念

### The two-loss architecture · 双 loss 架构

一个 decoder-only transformer 处理一条包含以下内容的序列：

- 文本 token（离散，来自 BPE 词表）。
- 图像 patch（连续，16x16 像素块经线性嵌入投影到隐藏维 —— 和 ViT 编码器的输入一样）。
- `<image>` 和 `</image>` 标签，标记连续 patch 所在的位置。

前向只跑一次。loss 按 token 二选一：

- 文本 token：词表 logits 头上的标准交叉熵。
- 图像 patch：连续 patch 上的扩散 loss —— 预测加到每个 patch 上的噪声。

梯度流过共享的 transformer 主体。两个 loss 同时改进共享权重。

> A single decoder-only transformer processes a sequence that contains: text tokens (discrete, from BPE vocab) ... image patches (continuous, 16x16 pixel blocks projected into hidden dim via linear embedding) ... The loss picks one of two heads per token: for text tokens, standard cross-entropy on the vocab-logits head; for image patches, diffusion loss on continuous patches ... The gradient flows through the shared transformer body. Both losses improve the shared weights simultaneously.

### Attention mask: causal text + bidirectional image · 注意力掩码：文本因果 + 图像双向

文本 token 必须因果 —— 不能让文本 token 看到未来的文本，否则 teacher forcing 就坏了。但图像 patch 表示的是同一张快照；同一图像块内部应该互相双向注意。

掩码规则：

```
M[i, j] = 1 if:
  (i is text and j is text and j <= i)   # causal for text
  OR (i is image and j is image and same_image_block(i, j))   # bidirectional within image
  OR (i is text and j is image and j < i_image_end)   # text attends to previous images
  OR (i is image and j is text and j < i_image_start)   # image attends to preceding text
```

训练和推理时都实现为块三角掩码。

> Text tokens must be causal — you cannot let a text token attend to future text, or teacher forcing breaks. Image patches, however, represent one snapshot; they should attend to each other bidirectionally within the same image block. ... Implemented as a block-triangular mask at training and inference.

### Diffusion loss inside the transformer · transformer 内部的扩散 loss

扩散 loss 是标准款：给图像 patch 加噪，让模型预测噪声（或者等价地预测干净 patch）。Transfusion 的版本用 flow matching —— 预测从噪声到干净数据的速度场。

训练时：
1. 对每个图像 patch x0，随机采样一个时间步 t。
2. 采样噪声 ε，算 xt = (1-t) * x0 + t * ε（flow matching 的线性插值）。
3. transformer 预测 v_theta(xt, t)；loss = MSE(v_theta(xt, t), ε - x0)。
4. 与同一条序列上的文本 NTP loss 一起反向传播。

推理时，生成是：
- 文本 token：标准自回归采样。
- 图像 patch：以前文文本 token 为条件的扩散采样循环（典型 10-30 步）。

> The diffusion loss is standard: add noise to an image patch, ask the model to predict the noise (or the clean patch, equivalently). Transfusion's version uses flow matching — predict the velocity field from noisy to clean. ... At inference, generation is: text tokens, standard autoregressive sampling; image patches, diffusion sampling loop (10-30 steps typical) conditioned on the prior text tokens.

### MMDiT: Stable Diffusion 3's variant · MMDiT：Stable Diffusion 3 的变体

Stable Diffusion 3（Esser et al.，2024 年 3 月）几乎与 Transfusion 同时发布了 MMDiT（Multimodal Diffusion Transformer）。两个架构是兄弟。

MMDiT 的关键差异：

- 每个 block 模态专属权重。每个 transformer block 里，文本 token 与图像 patch 各有独立的 Q、K、V 和 MLP 权重。注意力是联合的（跨模态）；其余全部按模态分离。
- Rectified flow 训练。flow matching 的一个特定变体，采样性质已知、数学比 DDPM 简单。
- 规模。MMDiT 是 SD3 的骨干（2B 和 8B 参数版）。Transfusion 论文做到 7B。

两者收敛在同一个核心想法上：一个 transformer，文本跑 NTP、连续图像表征跑扩散。

> Stable Diffusion 3 (Esser et al., March 2024) shipped MMDiT (Multimodal Diffusion Transformer) around the same time as Transfusion. The architectures are siblings. ... MMDiT's key differences: modality-specific weights per block ... Both converge on the same core idea: one transformer runs NTP on text and diffusion on continuous image representations.

### Why this beats Chameleon-style · 为什么它赢过 Chameleon 式

连续扩散与离散 NTP 在图像生成上的质量差距是可测的。Transfusion 论文报告：

- 7B 参数下，FID 比同等规模的 Chameleon 式模型好 3-5 分。
- 不需要训练分词器 —— 图像编码器更简单（线性投影到隐藏维，同 ViT 的输入层）。
- 推理时图像 patch 的去噪可以并行，不像自回归图像 token。

缺点：Transfusion 是双 loss 模型，训练动态更难弄。loss 权重需要调。NTP 与扩散之间的调度不匹配，会让某一头压过另一头。

> The quality gap between continuous-diffusion and discrete-NTP on image generation is measurable. Transfusion paper reports: at 7B params, beats a same-size Chameleon-style model on FID by 3-5 points ... Downside: Transfusion is a dual-loss model, making training dynamics trickier. Loss weights need tuning. Schedule mismatch between NTP and diffusion can cause one head to dominate.

### What sits downstream · 下游衍生

Janus-Pro（第 12.15 课）细化了 Transfusion 的想法：把理解与生成用的视觉编码器解耦 —— 一个用 SigLIP、一个用 VQ —— 同时共享 transformer 主体。Show-o（第 12.14 课）把扩散换成离散扩散（掩码预测）。统一生成家族在 Transfusion 之后迅速分叉。

2026 年会出图的生产级 VLM —— Gemini 3 Pro、GPT-5、Claude Opus 4.7 的图像生成路径 —— 几乎可以肯定用的是这个家族的某个后代。细节保密。

> Janus-Pro (Lesson 12.15) refines Transfusion's idea by decoupling the vision encoder for understanding and generation — SigLIP for one, VQ for the other — while sharing the transformer body. Show-o (Lesson 12.14) swaps diffusion for discrete-diffusion (masked prediction). ... 2026 production VLMs that emit images — Gemini 3 Pro, GPT-5, Claude Opus 4.7's image generation path — almost certainly use some descendant of this family. Details are proprietary.

```figure
cfg-guidance-scale
```

## Use It · 实战用法

`code/main.py` 在一个微型 MNIST 风格的问题上搭玩具 Transfusion：

- 文本 caption 是描述某个数字（0-9）的短整数序列。
- 图像是 4x4 的字节网格。
- 一对共享权重的线性投影充当 transformer 替身；文本上 NTP loss、加噪 patch 上 MSE loss。
- 训练循环交替两个 loss，注意力掩码显式给出。
- 生成在一次前向里同时产出文本 caption 和 4x4 图像。

transformer 是玩具。双 loss 的管道、注意力掩码构造和推理循环才是真正的产物。

> `code/main.py` builds a toy Transfusion on a tiny MNIST-like problem: text captions are short integer sequences describing a digit (0-9) ... images are 4x4 grids of bytes ... The transformer is a toy. The two-loss plumbing, attention mask construction, and inference loop are the real artifacts.

## Ship It · 交付

本课产出 `outputs/skill-two-loss-trainer-designer.md`。给定一个新的多模态训练任务（文本 + 图像、文本 + 音频、文本 + 视频），它设计双 loss 调度（loss 权重、掩码形状、共享 vs 模态专属 block）并标记实现风险。

> This lesson produces `outputs/skill-two-loss-trainer-designer.md`. Given a new multimodal training task (text + image, text + audio, text + video), it designs the two-loss schedule (loss weights, mask shape, shared vs modality-specific blocks) and flags implementation risks.

## Exercises · 练习

1. 一个 Transfusion 式模型用 70% 文本 token、30% 图像 patch 训练。图像扩散 loss 的量级约是文本 NTP loss 的 10 倍。loss 权重该怎么配平？

2. 为序列 `[T, T, <image>, P, P, P, P, </image>, T]` 实现块三角掩码。把每个条目标成 0 或 1。

3. MMDiT 的 QKV 权重按模态分离。相对 Transfusion 的全共享 transformer，这额外加了多少参数？7B 参数下值得吗？

4. 生成：给定文本 prompt，模型先跑 50 个 token 的 NTP，然后碰到 `<image>`，再对 256 个 patch 跑 20 步去噪的扩散。总共多少次前向？

5. 读 SD3 论文第 3 节。描述 rectified flow，以及为什么它的推理步数比 DDPM 少。

> A Transfusion-style model trains 70% text tokens and 30% image patches. The image diffusion loss is ~10x the text NTP loss in magnitude. What loss weights balance them? ... Implement the block-triangular mask for a sequence: `[T, T, <image>, P, P, P, P, </image>, T]`. Mark each entry 0 or 1. ... Generation: given a text prompt, the model runs NTP for 50 tokens, then hits `<image>`, then runs diffusion on 256 patches over 20 denoise steps. How many forward passes total?

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Two-loss training | "NTP + 扩散" | 单个 transformer 在同一次梯度步里，同时优化文本 token 上的交叉熵和连续图像 patch 上的 MSE |
| Flow matching | "Rectified flow" | 预测从噪声到干净数据的速度场的扩散变体；数学比 DDPM 简单 |
| MMDiT | "多模态 DiT" | Stable Diffusion 3 的架构：联合注意力，模态专属的 MLP 和归一化 |
| Block-triangular mask | "文本因果 + 图像双向" | 文本之间因果、图像区域内双向的注意力掩码 |
| Continuous image representation | "不要 VQ" | 图像 patch 用实值向量，而不是整数码本索引 |
| Velocity prediction | "v 参数化" | 网络输出是噪声与数据之间的速度场，不是噪声本身 |

## Further Reading · 延伸阅读

- [Zhou et al. — Transfusion (arXiv:2408.11039)](https://arxiv.org/abs/2408.11039)
- [Esser et al. — Stable Diffusion 3 / MMDiT (arXiv:2403.03206)](https://arxiv.org/abs/2403.03206)
- [Peebles & Xie — DiT (arXiv:2212.09748)](https://arxiv.org/abs/2212.09748)
- [Zhao et al. — MonoFormer (arXiv:2409.16280)](https://arxiv.org/abs/2409.16280)
- [Xie et al. — Show-o (arXiv:2408.12528)](https://arxiv.org/abs/2408.12528)
