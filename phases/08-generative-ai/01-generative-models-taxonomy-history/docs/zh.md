# Generative Models — Taxonomy & History · 生成模型——分类与历史

> Every image model, text model, video model, and 3D model fits in one of five buckets. Pick the wrong bucket and you will fight the math for weeks. Pick the right one and the field's last twelve years of progress stacks cleanly in your head.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 2 (ML Fundamentals), Phase 3 (Deep Learning Core), Phase 7 · 14 (Transformers)
**Time:** ~45 minutes

## The Problem · 问题在哪

生成模型只做一件事：给定从某个未知分布 `p_data(x)` 中抽出的训练样本，输出看起来像来自同一分布的新样本。人脸、句子、MIDI 文件、蛋白质结构——眯起眼睛看，全是同一个问题。

麻烦在于：`p_data` 活在一个数百万维的空间里（一张 512x512 的 RGB 图像约有 78.6 万维），样本只是这个空间里一块薄薄的流形（manifold），而你手里大概只有 1000 万个样本。硬暴力估计密度是没有出路的。每一个生成模型都是一种折中：拿一个难题，去换一个稍微不那么难的难题。

过去十二年存活下来的是五个家族。搞清楚每个家族各自做的是哪种折中，你就明白它为什么在有些任务上称王、在另一些任务上崩盘。

> A generative model does one job: given training samples drawn from some unknown distribution `p_data(x)`, output new samples that look like they came from the same distribution. ... The rub is that `p_data` lives in a space with millions of dimensions (a 512x512 RGB image is ~786k dimensions), the samples sit on a thin manifold inside that space, and you only have maybe 10M examples. ... Every generative model is a compromise that trades one hard problem for a slightly less hard one. ... Five families have survived the last twelve years.

## The Concept · 概念

![五大家族生成模型——按建模对象分类](../assets/taxonomy.svg)

**1. 显式密度、可解（tractable）。** 把 `log p(x)` 写成一个你真的算得动的和。自回归模型（autoregressive，PixelCNN、WaveNet、GPT）把联合分布因式分解为 `p(x) = ∏ p(x_i | x_<i)`。归一化流（normalizing flows，RealNVP、Glow）把 `p(x)` 构造成一个简单基分布的可逆变换。优点：精确似然、干净的训练损失。缺点：自回归推理是串行的（长序列慢），流需要可逆架构（架构上受限）。

**2. 显式密度、近似。** 给 `log p(x)` 找一个下界（ELBO），然后优化这个界。VAE（Kingma 2013）用带变分后验的编码器-解码器。扩散模型（diffusion，DDPM，Ho 2020）训练一个去噪器，隐式地优化一个加权 ELBO。在 2026 年，扩散是图像、视频、3D 的主流骨干。

**3. 隐式密度。** 干脆跳过密度；学一个产出样本的生成器 `G(z)` 和一个辨别真伪的判别器 `D(x)`。这就是 GAN（Goodfellow 2014）。推理快（一次前向）但训练出了名的不稳定。即便到 2026 年，StyleGAN 1/2/3 在固定领域的照片级真实感（人脸、卧室）上仍是最先进水平。

**4. 基于分数 / 连续时间。** 直接学对数密度的梯度 `∇_x log p(x)`（即 score）。Song & Ermon（2019）证明 score matching 把扩散推广成了一个 SDE。Flow matching（Lipman 2023）是 2024-2026 年最热的方向：免模拟（simulate-free）训练、更直的路径、采样比 DDPM 快 4-10 倍。Stable Diffusion 3、Flux、AudioCraft 2 用的都是 flow matching。

**5. 在离散编码上做 token 自回归。** 先用 VQ-VAE 或残差量化器（residual quantizer）把高维数据压成一小段离散 token 序列，再用 Transformer 建模这个 token 序列。Parti、MuseNet、AudioLM、VALL-E、Sora 的 patch tokenizer 用的都是这条路。它等于第 1 桶再加一个学出来的 tokenizer。

> **1. Explicit density, tractable.** Write `log p(x)` as a sum you can actually evaluate. ... **3. Implicit density.** Skip density entirely; learn a generator `G(z)` that produces samples and a discriminator `D(x)` that tells real from fake. ... **4. Score-based / continuous-time.** Learn the gradient of the log-density `∇_x log p(x)` (the score) directly. ... **5. Token-based autoregressive over discrete codes.** Compress high-dim data with a VQ-VAE or residual quantizer into a short sequence of discrete tokens, then use a Transformer to model the token sequence.

## A brief history · 简史

| 年份 | 模型 | 为什么重要 |
|------|-------|-----------------|
| 2013 | VAE (Kingma) | 第一个拥有可用训练损失的深度生成模型。 |
| 2014 | GAN (Goodfellow) | 隐式密度、不算似然——样本却出奇地锐利。 |
| 2015 | DRAW, PixelCNN | 串行的图像生成。 |
| 2017 | Glow, RealNVP | 可逆流；有深度还能保持精确似然。 |
| 2017 | Progressive GAN | 第一批百万像素人脸。 |
| 2019 | StyleGAN / StyleGAN2 | 在「人脸」这一个领域，照片级真实感至今难以超越。 |
| 2020 | DDPM (Ho) | 扩散从此变得实用。 |
| 2021 | CLIP, DALL-E 1, VQGAN | 文生图走向主流。 |
| 2022 | Imagen, Stable Diffusion 1, DALL-E 2 | 潜空间扩散 + 文本条件 = 普惠化。 |
| 2022 | ControlNet, LoRA | 对预训练扩散的精细控制。 |
| 2023 | SDXL, Midjourney v5, Flow matching | 规模 + 更好的训练动态。 |
| 2024 | Sora, Stable Diffusion 3, Flux.1 | 视频扩散；flow matching 胜出。 |
| 2025 | Veo 2, Kling 1.5, Runway Gen-3, Nano Banana | 生产级视频。 |
| 2026 | Consistency + Rectified Flow | 从扩散骨干一步采样。 |

> | 2013 | VAE (Kingma) | First deep generative model with a usable training loss. |
> | 2014 | GAN (Goodfellow) | Implicit density, no likelihood — shockingly sharp samples. |
> | 2020 | DDPM (Ho) | Diffusion becomes practical. |

## The five-question triage · 五问分诊

当一篇新的生成模型论文出现时，先回答下面五个问题，再去读方法部分。

1. **建模的对象是什么？** 像素、潜变量、离散 token、3D 高斯、网格（mesh）、波形？
2. **密度是显式还是隐式？** 他们写没写出 `log p(x)`？
3. **采样：一步生成还是迭代？** 迭代意味着推理更慢；一步生成通常意味着对抗训练或蒸馏。
4. **条件：无条件、类别、文本、图像、姿态？** 这决定了损失函数和架构脚手架。
5. **评估：FID、CLIP score、IS、人类偏好、任务准确率？** 每一种都有已知的失效模式（见第 14 课）。

本阶段的每一课，你都要重新回答这五问。到课程结束，它们会变成本能。

```figure
autoencoder-bottleneck
```

> When a new generative model paper drops, answer these five questions before reading the method section. ... You will re-answer these five for every lesson in this phase. By the end, they will be reflex.

## Build It · 动手造

本课的代码是一个轻量可视化：用三种玩具方法从样本拟合一个一维高斯混合（kernel density、离散直方图、以及一个「最近邻样本」式的类 GAN 生成器），让你在一个一屏就打印得下的问题上，看清显式密度与隐式密度的区别。

运行 `code/main.py`。它从一个双峰高斯混合抽取 2000 个样本，然后打印：

```
explicit density (histogram): p(x in [-0.5, 0.5]) ≈ 0.38
approximate density (KDE):     p(x in [-0.5, 0.5]) ≈ 0.41
implicit (nearest-sample gen): 20 new samples printed, no p(x)
```

注意：前两种方法让你能问「这个点有多大概率出现？」第三种做不到。这就是*显式 vs 隐式*的区别，后面每一课都会反复用到它。

> The code for this lesson is a lightweight visualization: fit a 1-D mixture-of-Gaussians from samples using three toy approaches (kernel density, discrete histogram, and a nearest-sample "GAN-ish" generator) so you can see the difference between explicit vs implicit density on a problem you can print on one screen. ... Notice: the first two let you ask "how likely is this point?" The third cannot. This is the *explicit vs implicit* distinction that will matter for every future lesson.

## Use It · 实战用法

2026 年，什么任务用什么家族？

| 任务 | 最佳家族 | 为什么 |
|------|-------------|-----|
| 照片级人脸、窄领域 | StyleGAN 2/3 | 依然最锐利、推理最快。 |
| 通用文生图 | Latent diffusion + flow matching | SD3、Flux.1、DALL-E 3。 |
| 快速文生图 | Rectified flow + 蒸馏 | SDXL-Turbo、SD3-Turbo、LCM。 |
| 文生视频 | Diffusion Transformer + flow matching | Sora、Veo 2、Kling。 |
| 语音 + 音乐 | 基于 token 的自回归（AudioLM、VALL-E、MusicGen）或 flow matching（AudioCraft 2） | 离散 token 的扩展成本更低。 |
| 3D 场景 | Gaussian Splatting 拟合 + diffusion prior | 3D-GS 做重建，diffusion 做新视角合成。 |
| 密度估计（不采样） | Flows | 唯一能给出精确 `log p(x)` 的家族。 |
| 仿真 / 物理 | Flow matching、score SDE | 直线路径、平滑向量场。 |

> Which family, for which task, in 2026?
> | Photoreal faces, narrow domain | StyleGAN 2/3 | Still sharpest, fastest inference. |
> | Density estimation (no sampling) | Flows | Only family with exact `log p(x)`. |

## Ship It · 交付

保存为 `outputs/skill-model-chooser.md`。

这个 skill 接收一段任务描述，输出：(1) 该用哪个家族，(2) 三个开源与三个托管选项的排名列表，(3) 你该警惕的最可能的失效模式，(4) 一份算力/时间预算。

> Save as `outputs/skill-model-chooser.md`.
> The skill takes a task description and outputs: (1) which family to use, (2) a ranked list of three open and three hosted options, (3) the likely failure mode you should watch for, and (4) a compute/time budget.

## Exercises · 练习

1. **简单。** 对下面五个产品，分别指出所属家族和骨干：ChatGPT image、Midjourney v7、Sora、Runway Gen-3、ElevenLabs。证据应来自公开技术报告。
2. **中等。** 你明天要读的某篇论文声称采样速度比扩散快 100 倍。写下三个问题，用来检验这个加速在加上条件生成与高分辨率之后是否还成立。
3. **困难。** 选一个你在意的领域（例如蛋白质结构、CAD、分子、轨迹）。对该领域当前的 SOTA 模型做一遍五问分诊，并勾画一个更好的模型会改变什么。

## Key Terms · 术语表

| 术语 | 人们的说法 | 实际含义 |
|------|-----------------|-----------------------|
| Generative model | 「会生成新东西」 | 学到 `p_data(x)` 的一个采样器，可选地暴露 `log p(x)`。 |
| Explicit density | 「能把它算出来」 | 模型提供闭式或可解的 `log p(x)`。 |
| Implicit density | 「GAN 那一路」 | 只有一个采样器——没法计算给定点处的 `p(x)`。 |
| ELBO | 「证据下界」 | `log p(x)` 的一个可解下界；VAE 和扩散优化的都是它。 |
| Score | 「对数密度的梯度」 | `∇_x log p(x)`；扩散和 SDE 模型学的就是这个场。 |
| Manifold hypothesis | 「数据住在一张曲面上」 | 高维数据集中在一个低维流形上；这就是降维为什么有效。 |
| Autoregressive | 「预测下一块」 | 把联合分布分解成一串条件分布的乘积。 |
| Latent | 「压缩后的编码」 | 一个低维表示，解码器可以从它重建输入。 |

## Production note: five families, five inference shapes · 生产备注：五个家族，五种推理形态

每个家族对应一条不同的推理服务器成本曲线。生产推理文献把 LLM 推理拆成 prefill + decode；同样的分解在这里也成立：

- **自回归（第 1、5 桶）。** 串行解码主导延迟；KV-cache、continuous batching、speculative decoding 全部直接适用。
- **VAE / 扩散 / flow matching（第 2、4 桶）。** 这里不存在 LLM 意义上的 decode。成本 = `num_steps × step_cost`，而 `step_cost` 是一个 transformer 或 U-Net 在完整潜分辨率上的一次前向。生产上能拧的旋钮是步数（DDIM / DPM-Solver / 蒸馏）、batch 大小和精度（bf16 / fp8 / int4）。
- **GAN（第 3 桶）。** 一次前向。没有调度，没有 KV-cache。TTFT ≈ 总延迟。这就是 StyleGAN 在窄领域用户体验上依然能赢的原因。

当你在论文摘要里看到「比扩散快」时，把它翻译成「更少步数 × 相同单步成本」或「相同步数 × 更便宜的单步成本」。其余都是营销话术。

> Each family maps to a different inference-server cost curve. ... **GAN (bucket 3).** One forward pass. No schedule, no KV-cache. TTFT ≈ total latency. This is why StyleGAN still wins on narrow-domain UX. ... When you see "faster than diffusion" in a paper abstract, translate it to "fewer steps × same step cost" or "same steps × cheaper step cost". Everything else is marketing.

## Further Reading · 延伸阅读

- [Goodfellow et al. (2014). Generative Adversarial Nets](https://arxiv.org/abs/1406.2661) —— GAN 原始论文。
- [Kingma & Welling (2013). Auto-Encoding Variational Bayes](https://arxiv.org/abs/1312.6114) —— VAE 原始论文。
- [Ho, Jain, Abbeel (2020). Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239) —— DDPM 原始论文。
- [Song et al. (2021). Score-Based Generative Modeling through SDEs](https://arxiv.org/abs/2011.13456) —— 把扩散写成一个 SDE。
- [Lipman et al. (2023). Flow Matching for Generative Modeling](https://arxiv.org/abs/2210.02747) —— flow matching 原始论文。
- [Esser et al. (2024). Scaling Rectified Flow Transformers for High-Resolution Image Synthesis](https://arxiv.org/abs/2403.03206) —— Stable Diffusion 3。
