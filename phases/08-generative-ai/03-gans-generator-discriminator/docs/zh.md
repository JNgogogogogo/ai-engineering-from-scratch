# GANs — Generator vs Discriminator · GAN——生成器对判别器

> Goodfellow's trick in 2014 was to skip density entirely. Two networks. One makes fakes. One catches them. They fight until the fakes are indistinguishable from real. It shouldn't work. It often doesn't. When it does, the samples are still the sharpest in the literature for narrow domains.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 3 · 02 (Backprop), Phase 3 · 08 (Optimizers), Phase 8 · 02 (VAE)
**Time:** ~75 minutes

## The Problem · 问题在哪

VAE 的样本发糊，因为它的 MSE 解码器损失对*均值图像*是贝叶斯最优的——而一堆合情合理的数字的均值，是一团糊。你想要一个奖励*合情合理*（plausibility）的损失，而不是对某个目标逐像素逼近。合情合理没有闭式解。你只能去学它。

Goodfellow 的想法：训练一个分类器 `D(x)` 来区分真图和假图；训练一个生成器 `G(z)` 去骗过 `D`。`G` 的损失信号，就是 `D` 当前认为「什么东西看起来真」的那套标准。这个信号随着 `G` 变强而更新——追着一个移动的靶子。如果两个网络收敛，`G` 就在从未写下 `log p(x)` 的情况下学到了数据分布。

这就是对抗训练（adversarial training）。数学是一个极小极大博弈（minimax game）：

```
min_G max_D  E_real[log D(x)] + E_fake[log(1 - D(G(z)))]
```

2026 年，GAN 已不是最强的生成器（那顶王冠被扩散和 flow matching 拿走了）。但 StyleGAN 2/3 仍是有史以来最锐利的人脸模型，GAN 判别器在扩散训练里被当作*感知损失*（perceptual loss）使用，而对抗训练驱动着让你能实时出图的快速 1 步蒸馏（SDXL-Turbo、SD3-Turbo、LCM）。

> VAEs produce blurry samples because their MSE decoder loss is Bayes-optimal for the *mean* image — and the mean of many plausible digits is a fuzzy digit. ... Goodfellow's idea: train a classifier `D(x)` to distinguish real images from fakes. Train a generator `G(z)` to fool `D`. ... This is adversarial training. The math is a minimax game: ... In 2026 GANs are no longer the SOTA generator (diffusion and flow matching ate that crown).

## The Concept · 概念

![GAN 训练：极小极大博弈中的生成器与判别器](../assets/gan.svg)

**生成器 `G(z)`。** 把噪声向量 `z ~ N(0, I)` 映射成样本 `x̂`。一个解码器形状的网络（全连接或转置卷积）。

**判别器 `D(x)`。** 把样本映射成一个标量概率（或分数）。真 → 1，假 → 0。

**损失。** 两组交替更新：

- **训练 `D`：** `loss_D = -[ log D(x) + log(1 - D(G(z))) ]`。对 真=1、假=0 做二元交叉熵。
- **训练 `G`：** `loss_G = -log D(G(z))`。这是 Goodfellow 用的*非饱和*（non-saturating）形式（原始的 `log(1 - D(G(z)))` 会饱和，`D` 一自信梯度就没了）。

**训练循环。** `D` 走一步，`G` 走一步。重复。

**为什么有效。** 如果 `G` 完美匹配 `p_data`，那么 `D` 最多只能瞎猜、处处输出 0.5；`G` 拿不到更多梯度。均衡。

**为什么崩。** 模式坍缩（mode collapse，`G` 找到一个 `D` 分不清的模式然后无限铸造它）、梯度消失（`D` 学得太快，`log D` 饱和）、训练不稳定（学习率、batch 大小、什么都能让它炸）。

> **Why it works.** If `G` perfectly matches `p_data`, then `D` cannot do better than chance and outputs 0.5 everywhere; `G` gets no more gradient. Equilibrium. ... **Why it breaks.** Mode collapse (`G` finds one mode `D` can't classify and mints it forever), vanishing gradient (`D` learns too fast and `log D` saturates), training instability (learning rates, batch sizes, anything).

## Variants that made GANs work · 让 GAN 真正跑起来的变体

| 年份 | 创新 | 修的什么 |
|------|------------|-----|
| 2015 | DCGAN | 卷积/反卷积、batch norm、LeakyReLU——第一个稳定的架构。 |
| 2017 | WGAN, WGAN-GP | 用 Wasserstein 距离 + 梯度惩罚替换 BCE。修好梯度消失。 |
| 2017 | Spectral normalization | 给判别器上 Lipschitz 约束。2026 年的判别器还在用它。 |
| 2018 | Progressive GAN | 先训低分辨率，再加层。第一批百万像素结果。 |
| 2019 | StyleGAN / StyleGAN2 | 映射网络 + 自适应实例归一化。固定领域照片级真实感的最先进水平。 |
| 2021 | StyleGAN3 | 抗混叠、平移等变——2026 年人脸的黄金标准。 |
| 2022 | StyleGAN-XL | 条件化、类别感知、更大规模。 |
| 2024 | R3GAN | 以更强的正则化重新出发；不用技巧也能跑 1024²。 |

```figure
gan-minimax
```

> | 2015 | DCGAN | Conv/deconv, batch norm, LeakyReLU — the first stable architecture. |
> | 2017 | WGAN, WGAN-GP | Replace BCE with Wasserstein distance + gradient penalty. Fixes vanishing gradient. |
> | 2021 | StyleGAN3 | Alias-free, translation-equivariant — still the face gold standard in 2026. |

## Build It · 动手造

`code/main.py` 在一维数据上训练一个微型 GAN：两个高斯的混合。生成器和判别器都是单隐层 MLP。我们手写前向、反向和极小极大循环。目标是亲眼看到两种关键失败模式（模式坍缩 + 梯度消失）发生的过程。

> `code/main.py` trains a tiny GAN on 1-D data: a mixture of two Gaussians. ... The goal is to see the two key failure modes (mode collapse + vanishing gradient) as they happen.

### Step 1: non-saturating loss · 第 1 步：非饱和损失

原味 Goodfellow 损失 `log(1 - D(G(z)))` 在 D 高置信度地把 G 的假货判为假时趋于 0。此时 G 的梯度基本为零——G 无法改进。非饱和形式 `-log D(G(z))` 的渐近行为正好相反：D 越自信它越炸，给 G 一个强信号。

```python
def g_loss(d_fake):
    # maximize log D(G(z))  <=>  minimize -log D(G(z))
    return -sum(math.log(max(p, 1e-8)) for p in d_fake) / len(d_fake)
```

> The vanilla Goodfellow loss `log(1 - D(G(z)))` goes to 0 when D classifies G's fake as fake with high confidence. At that point the gradient for G is basically zero — G cannot improve. The non-saturating form `-log D(G(z))` has the opposite asymptote: it blows up when D is confident, giving G a strong signal.

### Step 2: one discriminator step per generator step · 第 2 步：每一步 G 配一步 D

```python
for step in range(steps):
    # train D
    real_batch = sample_real(batch_size)
    fake_batch = [G(z) for z in sample_noise(batch_size)]
    update_D(real_batch, fake_batch)

    # train G
    fake_batch = [G(z) for z in sample_noise(batch_size)]  # fresh fakes
    update_G(fake_batch)
```

给 G 用新鲜的假货，否则梯度是过期的。

> Fresh fakes for G, otherwise gradients are stale.

### Step 3: watch for mode collapse · 第 3 步：盯住模式坍缩

```python
if step % 200 == 0:
    samples = [G(z) for z in sample_noise(500)]
    mode_a = sum(1 for s in samples if s < 0)
    mode_b = 500 - mode_a
    if min(mode_a, mode_b) < 50:
        print("  [!] mode collapse: one mode is starved")
```

典型症状：两个真实模式中的一个不再被生成。判别器也不再纠正它，因为它从来不会被当作假货抓出来。

> The canonical symptom: one of the two real modes stops being generated. The discriminator stops correcting it because it's never seen as a fake.

## Pitfalls · 常见的坑

- **判别器太强。** 把 D 的学习率砍 2-5 倍，或加 instance/layer 噪声。D 的准确率一超过 95%，G 就死了。
- **生成器记住了一个模式。** 给 D 的输入加噪、用 minibatch-discriminator 层，或改用 WGAN-GP。
- **Batch norm 泄漏统计量。** 真批和假批流过同一个 BN 层会混掉两者的统计量。改用 instance norm 或 spectral norm。
- **Inception score 刷分。** 样本数少时 FID 和 IS 噪声很大。评估至少用 1 万个样本。
- **对条件任务而言「一步采样」是个谎言。** 你仍然需要 CFG scale、截断技巧和重采样，才能拿到可用的输出。

> **Discriminator too strong.** Cut D's learning rate by 2-5x, or add instance/layer noise. If D reaches >95% accuracy, G is dead. ... **Batch norm leaking statistics.** Real batch + fake batch flowing through the same BN layer mixes their statistics. Use instance norm or spectral norm instead.

## Use It · 实战用法

2026 年的 GAN 技术栈：

| 场景 | 选择 |
|-----------|------|
| 照片级真人脸、固定姿态 | StyleGAN3（最锐利、最小） |
| 动漫 / 风格化人脸 | StyleGAN-XL 或 Stable Diffusion LoRA |
| 图像到图像翻译 | Pix2Pix / CycleGAN（Phase 8 · 04）或 ControlNet（Phase 8 · 08） |
| 快速 1 步文生图 | 扩散的对抗蒸馏（SDXL-Turbo、SD3-Turbo） |
| 扩散训练器里的感知损失 | 在图像裁块上用一个小型 GAN 判别器 |
| 任何多模态、开放式的任务 | 别用——上扩散或 flow matching |

GAN 锐利但狭窄。一旦你的领域打开——照片、任意文本提示、视频——就换扩散。对抗技巧作为一个组件活了下来（感知损失、蒸馏），而不是一个独立的生成器。

> GANs are sharp but narrow. Once your domain opens up — photos, arbitrary text prompts, video — switch to diffusion. The adversarial trick lives on as a component (perceptual losses, distillation), not a standalone generator.

## Ship It · 交付

保存 `outputs/skill-gan-debugger.md`。这个 skill 接收一次失败的 GAN 训练（损失曲线、样本网格、数据集大小），输出一份按可能性排序的病因列表、一行式修法，以及一个重跑协议。

> Save `outputs/skill-gan-debugger.md`. Skill takes a failing GAN run (loss curves, sample grid, dataset size) and outputs a ranked list of likely causes, one-line fixes, and a rerun protocol.

## Exercises · 练习

1. **简单。** 用默认设置跑 `code/main.py`。然后把 `D_LR` 设为 `5 * G_LR` 再跑一遍。G 的损失多快塌缩成一个常数？
2. **中等。** 把 Goodfellow 的 BCE 损失换成 WGAN 损失：`loss_D = E[D(fake)] - E[D(real)]`、`loss_G = -E[D(fake)]`，并把 D 的权重裁剪到 `[-0.01, 0.01]`。训练更稳了吗？比较实际耗时下的收敛速度。
3. **困难。** 把一维例子扩展到二维数据（环上的 8 个高斯混合）。在 1k、5k、10k 步时追踪生成器抓住了 8 个模式中的几个。实现 minibatch discrimination 并重新测量。

## Key Terms · 术语表

| 术语 | 人们的说法 | 实际含义 |
|------|-----------------|-----------------------|
| Generator | 「G」 | 噪声到样本的网络，`G: z → x̂`。 |
| Discriminator | 「D」 | 分类器 `D: x → [0, 1]`，判真伪。 |
| Minimax | 「那场博弈」 | 一个联合目标的 `min_G max_D`。 |
| Non-saturating loss | 「那个修法」 | G 用 `-log D(G(z))` 而不是 `log(1 - D(G(z)))`。 |
| Mode collapse | 「G 记住了一样东西」 | 数据五花八门，生成器却只会产出寥寥几种输出。 |
| WGAN | 「Wasserstein」 | 用推土机距离 + 梯度惩罚替换 BCE；梯度更平滑。 |
| Spectral norm | 「Lipschitz 技巧」 | 约束 D 的权重范数来限制它的斜率；稳定训练。 |
| StyleGAN | 「那个真能用的」 | 映射网络 + AdaIN；人脸任务的最佳水准，2026 年依然如此。 |

## Production note: one-shot inference is GAN's lasting advantage · 生产备注：一步推理是 GAN 长久的优势

GAN 在开放域生成的样本质量上不再赢，但在推理成本上仍然赢。用生产推理文献的词汇说，一个 GAN 有：

- **没有 prefill、没有 decode 阶段。** 单次 `G(z)` 前向。TTFT ≈ 总延迟。
- **没有 KV-cache 压力。** 唯一的状态就是权重。batch 大小受激活内存约束，而不是缓存。
- **连续批处理轻而易举。** 每个请求的 FLOPs 相同，服务器在目标占用率下的静态 batch 通常就是最优。不需要在途调度器。

这就是为什么 GAN 蒸馏（SDXL-Turbo、SD3-Turbo、ADD、LCM）是 2026 年快速文生图的主流技术：它把一条 20-50 步的扩散管线压成 1-4 次 GAN 式前向，同时保住扩散基模型的分布。对抗损失作为训练期旋钮活了下来——把慢生成器变成快生成器。

> GANs no longer win on sample quality for open-domain generation, but they still win on inference cost. ... This is why GAN distillation (SDXL-Turbo, SD3-Turbo, ADD, LCM) is the dominant technique for fast text-to-image in 2026: it collapses a 20-50-step diffusion pipeline into 1-4 GAN-style forward passes while keeping the distribution of a diffusion base. The adversarial loss survives as a training-time knob for turning slow generators into fast ones.

## Further Reading · 延伸阅读

- [Goodfellow et al. (2014). Generative Adversarial Nets](https://arxiv.org/abs/1406.2661) —— GAN 开山之作。
- [Radford et al. (2015). Unsupervised Representation Learning with DCGAN](https://arxiv.org/abs/1511.06434) —— 第一个稳定的架构。
- [Arjovsky, Chintala, Bottou (2017). Wasserstein GAN](https://arxiv.org/abs/1701.07875) —— WGAN。
- [Miyato et al. (2018). Spectral Normalization for GANs](https://arxiv.org/abs/1802.05957) —— SN。
- [Karras et al. (2020). Analyzing and Improving the Image Quality of StyleGAN](https://arxiv.org/abs/1912.04958) —— StyleGAN2。
- [Karras et al. (2021). Alias-Free Generative Adversarial Networks](https://arxiv.org/abs/2106.12423) —— StyleGAN3。
- [Sauer et al. (2023). Adversarial Diffusion Distillation](https://arxiv.org/abs/2311.17042) —— SDXL-Turbo。
