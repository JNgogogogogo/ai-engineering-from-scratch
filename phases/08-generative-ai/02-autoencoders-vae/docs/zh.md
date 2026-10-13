# Autoencoders & Variational Autoencoders (VAE) · 自编码器与变分自编码器（VAE）

> A plain autoencoder compresses then reconstructs. It memorizes. It does not generate. Add one trick — force the code to look Gaussian — and you get a sampler. That single trick, the reparameterization of `z = μ + σ·ε`, is why every latent-diffusion and flow-matching image model you use in 2026 has a VAE at the input.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 3 · 02 (Backprop), Phase 3 · 07 (CNNs), Phase 8 · 01 (Taxonomy)
**Time:** ~75 minutes

## The Problem · 问题在哪

把一个 784 像素的 MNIST 数字压成一个 16 个数的编码，再重建出来。普通自编码器（autoencoder）能把重建 MSE 做得很漂亮，但编码空间是一团坑坑洼洼的乱麻。在编码空间里随便挑一个点，解码它，你得到的是噪声。它没有采样器。它只是一个穿了马甲的压缩模型。

你真正想要的是：(a) 编码空间是一个干净、平滑、可以采样的分布——比如各向同性高斯 `N(0, I)`；(b) 解码任何一个样本都能得到一个像样的数字；(c) 编码器和解码器的压缩能力依然在线。三个目标，一套架构，一个损失。

Kingma 2013 年的 VAE 这样解决：训练编码器输出一个*分布* `q(z|x) = N(μ(x), σ(x)²)`，用 KL 惩罚把这个分布拉向先验 `N(0, I)`，然后在解码前从 `q(z|x)` 采样 `z`。推理时，扔掉编码器，采样 `z ~ N(0, I)`，解码。KL 惩罚正是强迫编码空间结构化的那只手。

到 2026 年，VAE 已经很少单独出厂——就原始图像质量而言，它早已被扩散模型超越——但它是每个潜空间扩散模型（SD 1/2/XL/3、Flux、AudioCraft）首选的编码器。学会了 VAE，你就学会了你用过的每一条图像管线里那层看不见的第一层。

> Compress a 784-pixel MNIST digit to a 16-number code, then reconstruct. A plain autoencoder will ace reconstruction MSE but the code space is a lumpy mess. ... Kingma's 2013 VAE solves this by training the encoder to output a *distribution* `q(z|x) = N(μ(x), σ(x)²)`, pulling that distribution toward the prior `N(0, I)` via a KL penalty, and then sampling `z` from `q(z|x)` before decoding. ... Learn the VAE and you learn the invisible first layer of every image pipeline you use.

## The Concept · 概念

![自编码器 vs VAE：重参数化技巧](../assets/vae.svg)

**自编码器（autoencoder）。** `z = encoder(x)`，`x̂ = decoder(z)`，损失 = `||x - x̂||²`。编码空间无结构。

**VAE 编码器。** 输出两个向量：`μ(x)` 和 `log σ²(x)`。它们定义了 `q(z|x) = N(μ, diag(σ²))`。

**重参数化技巧（reparameterization trick）。** 从 `q(z|x)` 采样这一步不可微。把样本改写成 `z = μ + σ·ε`，其中 `ε ~ N(0, I)`。这样 `z` 就是 `(μ, σ)` 的确定性函数加上一份非参数噪声——梯度可以流过 `μ` 和 `σ`。

**损失。** 证据下界（ELBO），两项：

```
loss = reconstruction + β · KL[q(z|x) || N(0, I)]
     = ||x - x̂||²  + β · Σ_i ( σ_i² + μ_i² - log σ_i² - 1 ) / 2
```

重建项把 `x̂` 推向 `x`。KL 项把 `q(z|x)` 推向先验。两者互相拉扯。β 小（<1）= 样本更锐利，编码空间不那么高斯。β 大（>1）= 编码空间更规整，样本更模糊。β-VAE（Higgins 2017）让这个旋钮出了名，并开启了解耦表示（disentanglement）研究。

**采样。** 推理时：抽 `z ~ N(0, I)`，过一遍解码器。一次前向——不像扩散那样要迭代采样。

```figure
vae-latent-grid
```

> **Autoencoder.** `z = encoder(x)`, `x̂ = decoder(z)`, loss = `||x - x̂||²`. Code space unstructured. ... **Reparameterization trick.** Sampling from `q(z|x)` is not differentiable. Rewrite the sample as `z = μ + σ·ε` where `ε ~ N(0, I)`. Now `z` is a deterministic function of `(μ, σ)` plus a non-parameter noise — gradients flow through `μ` and `σ`. ... Reconstruction pushes `x̂` toward `x`. KL pushes `q(z|x)` toward the prior. They trade off.

## Build It · 动手造

`code/main.py` 实现一个微型 VAE，不用 numpy 也不用 torch。输入是 8 维合成数据，抽自 8 维空间里的双分量高斯混合。编码器和解码器都是单隐层 MLP。我们手写 tanh 激活、前向、损失和一个手写的反向传播。不为生产——为教学。

> `code/main.py` implements a tiny VAE without numpy or torch. Input is 8-dimensional synthetic data drawn from a 2-component Gaussian mixture in 8-D. ... Not production — pedagogy.

### Step 1: encoder forward · 第 1 步：编码器前向

```python
def encode(x, enc):
    h = tanh(add(matmul(enc["W1"], x), enc["b1"]))
    mu = add(matmul(enc["W_mu"], h), enc["b_mu"])
    log_sigma2 = add(matmul(enc["W_sig"], h), enc["b_sig"])
    return mu, log_sigma2
```

用 `log σ²` 而不是 `σ`，这样网络输出不受约束（对 σ 做 softplus 是个陷阱——σ ≈ 0 处梯度会死掉）。

> `log σ²` instead of `σ` so the network output is unconstrained (softplus of σ is a trap — gradients die at σ ≈ 0).

### Step 2: reparameterize and decode · 第 2 步：重参数化与解码

```python
def reparameterize(mu, log_sigma2, rng):
    eps = [rng.gauss(0, 1) for _ in mu]
    sigma = [math.exp(0.5 * lv) for lv in log_sigma2]
    return [m + s * e for m, s, e in zip(mu, sigma, eps)]

def decode(z, dec):
    h = tanh(add(matmul(dec["W1"], z), dec["b1"]))
    return add(matmul(dec["W_out"], h), dec["b_out"])
```

### Step 3: the ELBO · 第 3 步：ELBO

```python
def elbo(x, x_hat, mu, log_sigma2, beta=1.0):
    recon = sum((a - b) ** 2 for a, b in zip(x, x_hat))
    kl = 0.5 * sum(math.exp(lv) + m * m - lv - 1 for m, lv in zip(mu, log_sigma2))
    return recon + beta * kl, recon, kl
```

两个分布都是高斯，所以 KL 有精确的闭式解。不要做数值积分。到 2026 年还有人往代码里塞 monte-carlo KL 估计——白白慢 3 倍，毫无理由。

> Exact closed-form KL because both distributions are Gaussian. Do not integrate numerically. People still ship code with monte-carlo KL estimates in 2026 — it is 3x slower for no reason.

### Step 4: generate · 第 4 步：生成

```python
def sample(dec, z_dim, rng):
    z = [rng.gauss(0, 1) for _ in range(z_dim)]
    return decode(z, dec)
```

这就是生成模型。五行代码。

> That is the generative model. Five lines.

## Pitfalls · 常见的坑

- **后验坍缩（posterior collapse）。** KL 项把 `q(z|x) → N(0, I)` 推得太狠，`z` 里不再携带任何关于 `x` 的信息。修法：β 退火（β 从 0 起步 ramp 到 1）、free bits，或者对不活跃维度跳过 KL。
- **样本模糊。** 高斯解码器似然意味着 MSE 重建，而 MSE 的贝叶斯最优解就是 L2 均值——一堆合情合理的数字的均值是一团糊。修法：离散解码器（VQ-VAE、NVAE），或者只把 VAE 当编码器用、在潜变量上叠扩散（Stable Diffusion 就是这么干的）。
- **β 太大、太早。** 见后验坍缩。从 β≈0.01 起步，再 ramp。
- **潜维度太小。** 16 维够 MNIST 用，ImageNet 256² 要 256 维，ImageNet 1024² 要 2048 维。Stable Diffusion 的 VAE 把 512×512×3 压到 64×64×4（空间面积上 32 倍下采样，通道上 32 倍）。

> **Posterior collapse.** KL term drives `q(z|x) → N(0, I)` so aggressively that `z` carries no info about `x`. ... **Blurry samples.** The Gaussian decoder likelihood implies MSE reconstruction, which is Bayes-optimal for L2 (the mean) — the mean of a set of plausible digits is a fuzzy digit. ... **Latent dim too small.** 16-D works for MNIST, 256-D for ImageNet 256², 2048-D for ImageNet 1024².

## Use It · 实战用法

2026 年的 VAE 技术栈：

| 场景 | 选择 |
|-----------|------|
| 扩散的图像潜编码器 | Stable Diffusion VAE（`sd-vae-ft-ema`）或 Flux VAE |
| 音频潜编码器 | Encodec（Meta）、SoundStream 或 DAC（Descript） |
| 视频潜变量 | Sora 的时空 patch、Latte VAE、WAN VAE |
| 解耦表示学习 | β-VAE、FactorVAE、TCVAE |
| 离散潜变量（供 transformer 建模） | VQ-VAE、RVQ（ResidualVQ） |
| 用于生成的连续潜变量 | 普通 VAE，然后在该潜空间里条件化一个 flow/diffusion 模型 |

潜空间扩散模型就是「一个 VAE，编码器和解码器之间住着一个扩散模型」。VAE 做粗压缩，扩散模型干重活。视频（VAE + 视频 diffusion DiT）和音频（Encodec + MusicGen transformer）是同一个模式。

> A latent-diffusion model is a VAE with a diffusion model living between encoder and decoder. The VAE does coarse compression, the diffusion model does the heavy lifting. Same pattern for video (VAE + video-diffusion DiT) and audio (Encodec + MusicGen transformer).

## Ship It · 交付

保存 `outputs/skill-vae-trainer.md`。

这个 skill 接收：数据集画像 + 目标潜维度 + 下游用途（重建、采样、或作为潜空间扩散的输入），输出：架构选择（plain/β/VQ/RVQ）、β 调度、潜维度、解码器似然（高斯还是类别分布）、以及评估方案（重建 MSE、每维 KL、`q(z|x)` 与 `N(0, I)` 之间的 Fréchet 距离）。

> Save `outputs/skill-vae-trainer.md`.
> Skill takes: dataset profile + latent-dim target + downstream use (reconstruction, sampling, or latent-diffusion input) and outputs: architecture choice (plain/β/VQ/RVQ), β schedule, latent dim, decoder likelihood (Gaussian vs categorical), and evaluation plan (recon MSE, KL per dim, Fréchet distance between `q(z|x)` and `N(0, I)`).

## Exercises · 练习

1. **简单。** 把 `code/main.py` 里的 `β` 改成 `0.01`、`0.1`、`1.0`、`5.0`。记录最终的重建 MSE 和 KL。对你的合成数据，哪个 β 是帕累托最优的？
2. **中等。** 把高斯解码器似然换成伯努利似然（交叉熵损失）。在同一份合成数据的二值化版本上比较样本质量。
3. **困难。** 把 `code/main.py` 扩展成一个迷你 VQ-VAE：把连续的 `z` 换成在 K=32 个条目的码本（codebook）里做最近邻查表。比较重建 MSE，并报告有多少码本条目被真正用到（码本坍缩是真实存在的）。

## Key Terms · 术语表

| 术语 | 人们的说法 | 实际含义 |
|------|-----------------|-----------------------|
| Autoencoder | 编码-解码网络 | `x → z → x̂`，学 MSE。不是生成模型。 |
| VAE | 带采样器的 AE | 编码器输出一个分布，KL 惩罚塑造编码空间。 |
| ELBO | 证据下界 | `log p(x) ≥ recon - KL[q(z\|x) \|\| p(z)]`；当 `q = p(z\|x)` 时取等。 |
| Reparameterization | `z = μ + σ·ε` | 把随机节点改写成「确定性部分 + 纯噪声」。让反向传播能穿过采样。 |
| Prior | `p(z)` | 潜变量的目标分布，通常取 `N(0, I)`。 |
| Posterior collapse | 「KL 项赢了」 | 编码器无视 `x`，直接输出先验；解码器只能靠幻觉。 |
| β-VAE | 可调的 KL 权重 | `loss = recon + β·KL`。β 越高越解耦，但越模糊。 |
| VQ-VAE | 离散潜变量 | 用码本里最近的向量替换连续 `z`；让 transformer 建模成为可能。 |

## Production note: the VAE is the hottest path in a diffusion server · 生产备注：VAE 是扩散服务器上最热的路径

在 Stable Diffusion / Flux / SD3 的管线里，每个请求要调用 VAE 两次——一次编码（做 img2img / inpainting 时），一次解码。在 1024² 分辨率下，解码那一趟往往是整条管线里最大的激活内存峰值，因为它要把 `128×128×16` 的潜变量上采样回 `1024×1024×3`。两个实操结论：

- **切片或分块解码。** `diffusers` 暴露了 `pipe.vae.enable_slicing()` 和 `pipe.vae.enable_tiling()`。分块用一点接缝伪影，换来 `O(tile²)` 的内存（而不是 `O(H·W)`）。在消费级 GPU 上跑 1024²+ 时必不可少。
- **解码器用 bf16，最终 resize 的数值用 fp32。** SD 1.x 的 VAE 是以 fp32 发布的，在 1024²+ 下强转 fp16 会*悄悄产出 NaN*。SDXL 附带 `madebyollin/sdxl-vae-fp16-fix`——永远优先用 fp16-fix 变体，或者直接用 bf16。

> In a Stable Diffusion / Flux / SD3 pipeline the VAE is called twice per request — once to encode (if doing img2img / inpainting) and once to decode. At 1024² the decoder pass is often the single largest activation-memory peak in the whole pipeline because it upsamples `128×128×16` latents back to `1024×1024×3`. ... The SD 1.x VAE was released in fp32 and *silently produces NaNs* when cast to fp16 at 1024²+.

## Further Reading · 延伸阅读

- [Kingma & Welling (2013). Auto-Encoding Variational Bayes](https://arxiv.org/abs/1312.6114) —— VAE 原始论文。
- [Higgins et al. (2017). β-VAE: Learning Basic Visual Concepts with a Constrained Variational Framework](https://openreview.net/forum?id=Sy2fzU9gl) —— 解耦的 β-VAE。
- [van den Oord et al. (2017). Neural Discrete Representation Learning](https://arxiv.org/abs/1711.00937) —— VQ-VAE。
- [Vahdat & Kautz (2021). NVAE: A Deep Hierarchical Variational Autoencoder](https://arxiv.org/abs/2007.03898) —— 最先进的图像 VAE。
- [Rombach et al. (2022). High-Resolution Image Synthesis with Latent Diffusion Models](https://arxiv.org/abs/2112.10752) —— Stable Diffusion；VAE 作为编码器。
- [Défossez et al. (2022). High Fidelity Neural Audio Compression](https://arxiv.org/abs/2210.13438) —— Encodec，音频 VAE 的标准。
