# Conditional GANs & Pix2Pix · 条件 GAN 与 Pix2Pix

> The first big unlock of 2014-2017 was controlling what a GAN makes. Attach a label, or an image, or a sentence. Pix2Pix did the image version and it still beats every generic text-to-image model on narrow image-to-image tasks.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 8 · 03 (GANs), Phase 4 · 06 (U-Net), Phase 3 · 07 (CNNs)
**Time:** ~75 minutes

## The Problem · 问题在哪

无条件 GAN 采样出的是随便什么人脸。演示有用，生产没用。你想要的是：*把草图映射成照片*、*把地图映射成航拍图*、*把白天场景映射成夜晚*、*给灰度图上色*。这些任务里，给定输入图像 `x`，你要输出与之有某种语义对应的 `y`。每个 `x` 对应许多个说得通的 `y`。均方误差把它们抹成一团浆糊。对抗损失不会，因为「看起来真」是锐利的。

条件 GAN（conditional GAN，Mirza & Osindero, 2014）给 `G` 和 `D` 都加一个条件输入 `c`。Pix2Pix（Isola et al., 2017）把它特化：条件是一整张输入图像，生成器是 U-Net，判别器是*基于 patch* 的分类器（PatchGAN），损失是对抗 + L1。即便在 2026 年，这个配方在窄的图像到图像领域仍然打赢从零训练的文生图模型，因为它在*成对数据*上训练——你恰好握着你需要的那份信号。

> An unconditional GAN samples arbitrary faces. Useful for a demo, useless in production. ... Mean-squared error flattens them into mush. An adversarial loss doesn't, because "looks real" is sharp. ... Pix2Pix (Isola et al., 2017) specialized this: condition is a full input image, generator is a U-Net, discriminator is a *patch-based* classifier (PatchGAN), and loss is adversarial + L1.

## The Concept · 概念

![Pix2Pix：U-Net 生成器，PatchGAN 判别器](../assets/pix2pix.svg)

**条件 G。** `G(x, z) → y`。在 Pix2Pix 里，`z` 是 G 内部的 dropout（没有输入噪声——Isola 发现显式噪声会被无视）。

**条件 D。** `D(x, y) → [0, 1]`。输入是*一对*（条件，输出）。这是关键差别：D 要判断的是 `y` 是否与 `x` 一致，而不只是 `y` 看起来真不真。

**U-Net 生成器。** 带跨瓶颈跳连（skip connections）的编码器-解码器。对输入输出共享低层结构（边缘、轮廓）的任务至关重要。没有跳连，高频细节会消失。

**PatchGAN 判别器。** D 不输出单一的真/假分数，而是输出一个 `N×N` 网格，每个格子只裁决约 70×70 像素的一块感受野。最后取平均。这是一个马尔可夫随机场（Markov random field）假设：真实性是局部的。训练快得多、参数更少、输出更锐利。

**损失。**

```
loss_G = -log D(x, G(x)) + λ · ||y - G(x)||_1
loss_D = -log D(x, y) - log (1 - D(x, G(x)))
```

L1 项稳定训练，并把 G 推向已知目标。L1 比 L2 边缘更锐利（L1 对应中位数，不是均值）。`λ = 100` 是 Pix2Pix 的默认值。

> **Conditional D.** `D(x, y) → [0, 1]`. Input is the *pair* (condition, output). This is the key difference: D must judge whether `y` is consistent with `x`, not just whether `y` looks real. ... **PatchGAN discriminator.** Instead of outputting a single real/fake score, D outputs an `N×N` grid where each cell judges a receptive field of ~70×70 pixels. ... The L1 term stabilizes training and pushes G toward the known target. L1 gives sharper edges than L2 (medians, not means). `λ = 100` was the Pix2Pix default.

## CycleGAN — when you don't have pairs · CycleGAN——没有成对数据的时候

Pix2Pix 需要成对的 `(x, y)` 数据。CycleGAN（Zhu et al., 2017）放弃这个要求，代价是多一个损失：*循环一致性*（cycle consistency）损失。两个生成器 `G: X → Y` 和 `F: Y → X`。训练它们使得 `F(G(x)) ≈ x` 且 `G(F(y)) ≈ y`。这让你无需成对样本，就能把马翻译成斑马、夏天翻译成冬天。

2026 年，非配对的图像到图像大多用扩散来做（ControlNet、IP-Adapter）而不是 CycleGAN，但循环一致性这个想法活在几乎所有非配对域适应（domain adaptation）论文里。

```figure
gx-patchgan
```

> Pix2Pix needs paired `(x, y)` data. CycleGAN (Zhu et al., 2017) drops this requirement at the cost of an extra loss: the *cycle consistency* loss. Two generators `G: X → Y` and `F: Y → X`. Train them so `F(G(x)) ≈ x` and `G(F(y)) ≈ y`. This lets you translate horses to zebras, summer to winter, without paired examples.

## Build It · 动手造

`code/main.py` 在一维数据上实现一个微型条件 GAN。条件 `c` 是类别标签（0 或 1）。任务：对给定类别，从条件分布中产出一个样本。

> `code/main.py` implements a tiny conditional GAN on 1-D data. The condition `c` is a class label (0 or 1). The task: produce a sample from the conditional distribution for the given class.

### Step 1: append condition to both G and D inputs · 第 1 步：把条件拼接到 G 和 D 的输入

```python
def G(z, c, params):
    return mlp(concat([z, one_hot(c)]), params)

def D(x, c, params):
    return mlp(concat([x, one_hot(c)]), params)
```

One-hot 编码是最简单的办法。更大的模型会用学出来的 embedding、FiLM 调制，或 cross-attention。

> One-hot encoding is the simplest way. Larger models use learned embeddings, FiLM modulation, or cross-attention.

### Step 2: train conditional · 第 2 步：训练条件化

```python
for step in range(steps):
    x, c = sample_real_conditional()
    noise = sample_noise()
    update_D(x_real=x, x_fake=G(noise, c), c=c)
    update_G(noise, c)
```

生成器必须匹配的是*给定条件下*的真实分布，而不是边缘分布。

> The generator must match the real distribution *for the given condition*, not the marginal.

### Step 3: verify per-class output · 第 3 步：逐类验证输出

```python
for c in [0, 1]:
    samples = [G(noise, c) for noise in batch]
    mean_c = mean(samples)
    assert_near(mean_c, real_mean_for_class_c)
```

## Pitfalls · 常见的坑

- **条件被无视。** G 学会把条件边缘化掉，D 也不惩罚，因为条件信号太弱。修法：更激进地把条件喂给 D（放在浅层，别只放深层）、用 projection discriminator（Miyato & Koyama 2018）。
- **L1 权重太低。** G 漂向任意「看起来真」的输出，而不是忠实的输出。Pix2Pix 类任务从 λ≈100 起步。
- **L1 权重太高。** G 产出模糊的结果，因为 L1 仍是 L_p 范数。训练稳定后退火降权。
- **D 里的真值泄漏。** 把 `(x, y)` 拼起来作为 D 的输入，别只给 `y`。否则 D 无法检查一致性。
- **逐类模式坍缩。** 每个类可以独立坍缩。跑一遍类条件的多样性检查。

> **Condition ignored.** G learns to marginalize, D never penalizes because condition signal is weak. Fix: condition D more aggressively (early layer, not just late), use projection discriminator (Miyato & Koyama 2018). ... **Ground-truth leakage in D.** Concatenate `(x, y)` as D input, not just `y`. Without this D cannot check consistency.

## Use It · 实战用法

2026 年图像到图像任务的现状：

| 任务 | 最佳方案 |
|------|---------------|
| 草图 → 照片、同域、成对数据 | Pix2Pix / Pix2PixHD（依然快、依然锐利） |
| 草图 → 照片、非配对 | ControlNet 配 Scribble 条件模型 |
| 语义分割 → 照片 | SPADE / GauGAN2 或 SD + ControlNet-Seg |
| 风格迁移 | 扩散 + IP-Adapter 或 LoRA；GAN 方法已是遗留技术 |
| 深度 → 照片 | 在 Stable Diffusion 上加 ControlNet-Depth |
| 超分辨率 | Real-ESRGAN（GAN）、ESRGAN-Plus，或 SD-Upscale（扩散） |
| 上色 | ColTran、基于扩散的上色器，或 Pix2Pix-color |
| 白天 → 夜晚、季节、天气 | CycleGAN 或基于 ControlNet |

当 (a) 你有成千上万个成对样本，(b) 任务窄且可重复，(c) 你需要快推理时，Pix2Pix 仍然是对的工具。泛用的开放域任务，扩散赢。

> Pix2Pix remains the right tool when (a) you have thousands of paired examples, (b) the task is narrow and repeatable, and (c) you need fast inference. On generic open-domain tasks, diffusion wins.

## Ship It · 交付

保存 `outputs/skill-img2img-chooser.md`。这个 skill 接收任务描述、数据可得性（配对与否、样本数 N）、时延/质量预算，然后输出：方案（Pix2Pix、CycleGAN、ControlNet 变体、SDXL + IP-Adapter）、训练数据要求、推理成本，以及评估协议（LPIPS、FID、任务特定指标）。

> Save `outputs/skill-img2img-chooser.md`. Skill takes a task description, data availability (paired vs unpaired, N samples), and latency/quality budget, then outputs: approach (Pix2Pix, CycleGAN, ControlNet variant, SDXL + IP-Adapter), training data requirements, inference cost, and eval protocol (LPIPS, FID, task-specific).

## Exercises · 练习

1. **简单。** 修改 `code/main.py` 加上第三个类。确认 G 仍然把每个类的噪声映射到正确的模式。
2. **中等。** 在一维设定里把 L1 换成一个感知风格的损失（例如用一个冻结的小 D 当特征提取器）。条件分布的锐利度变了吗？
3. **困难。** 在一维设定里勾画一个 CycleGAN：两个分布、两个生成器、循环损失。展示它能在这两者之间学会互映射，全程不用成对数据。

## Key Terms · 术语表

| 术语 | 人们的说法 | 实际含义 |
|------|-----------------|-----------------------|
| Conditional GAN | 「带标签的 GAN」 | G(z, c)，D(x, c)。两个网络都看到条件。 |
| Pix2Pix | 「图像到图像的 GAN」 | 配对 cGAN：U-Net 生成器 + PatchGAN 判别器 + L1 损失。 |
| U-Net | 「带跳连的编码器-解码器」 | 对称卷积网络；跳连保住高频。 |
| PatchGAN | 「局部真实性分类器」 | D 输出逐 patch 的分数，而不是全局分数。 |
| CycleGAN | 「非配对图像翻译」 | 两个 G + 循环一致性损失；无需成对数据。 |
| SPADE | 「GauGAN」 | 用语义图归一化中间激活；分割图到图像。 |
| FiLM | 「特征级线性调制」 | 从条件出发的逐特征仿射变换；便宜的条件化方式。 |

## Production note: Pix2Pix as a latency-bound baseline · 生产备注：作为时延基准的 Pix2Pix

当你有成对数据和一个窄任务（草图 → 渲染图、语义图 → 照片、白天 → 夜晚），Pix2Pix 的一次前向推理在时延上比扩散低一个数量级。生产上通常这样比：

| 路径 | 步数 | 单张 L4 上 512² 的典型时延 |
|------|-------|----------------------------------------|
| Pix2Pix（U-Net 前向） | 1 | ~30 ms |
| SD-Inpaint 或 SD-Img2Img | 20 | ~1.2 s |
| SDXL-Turbo Img2Img | 1-4 | ~0.15-0.35 s |
| ControlNet + SDXL base | 20-30 | ~3-5 s |

Pix2Pix 在静态 batch 下赢得吞吐（每个请求的 FLOPs 相同）。扩散在质量和泛化上赢。现代打法往往是：窄任务上线一个 Pix2Pix 风格的蒸馏模型，长尾输入配一个扩散兜底。

> When you have paired data and a narrow task (sketch → render, semantic map → photo, day → night), Pix2Pix's one-shot inference beats diffusion by an order of magnitude on latency. ... Pix2Pix wins on throughput in static batches (every request is the same FLOPs). Diffusion wins on quality and generalization. The modern play is often to ship a Pix2Pix-style distilled model for the narrow task and a diffusion fallback for tail inputs.

## Further Reading · 延伸阅读

- [Mirza & Osindero (2014). Conditional Generative Adversarial Nets](https://arxiv.org/abs/1411.1784) —— cGAN 原始论文。
- [Isola et al. (2017). Image-to-Image Translation with Conditional Adversarial Networks](https://arxiv.org/abs/1611.07004) —— Pix2Pix。
- [Zhu et al. (2017). Unpaired Image-to-Image Translation using Cycle-Consistent Adversarial Networks](https://arxiv.org/abs/1703.10593) —— CycleGAN。
- [Wang et al. (2018). High-Resolution Image Synthesis with Conditional GANs](https://arxiv.org/abs/1711.11585) —— Pix2PixHD。
- [Park et al. (2019). Semantic Image Synthesis with Spatially-Adaptive Normalization](https://arxiv.org/abs/1903.07291) —— SPADE / GauGAN。
- [Miyato & Koyama (2018). cGANs with Projection Discriminator](https://arxiv.org/abs/1802.05637) —— projection 判别器。
