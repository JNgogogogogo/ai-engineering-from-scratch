# Diffusion Models — DDPM from Scratch · 扩散模型：从零实现 DDPM

> Ho, Jain, Abbeel (2020) gave the field a recipe it could not quit. Destroy the data with noise over a thousand small steps. Train one neural net to predict the noise. Reverse the process at inference. Today every mainstream image, video, 3D, and music model runs on this loop, possibly with flow matching or consistency tricks on top.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 3 · 02 (Backprop), Phase 8 · 02 (VAE)
**Time:** ~75 minutes

## The Problem · 问题

你想要一个 `p_data(x)` 的采样器。GAN 在玩一个经常发散的 minimax 博弈；VAE 从高斯解码器里产出的样本很模糊。你真正想要的训练目标是：(a) 一个单一且稳定的损失（没有鞍点、没有 minimax），(b) `log p(x)` 的一个下界（这样你才有似然），(c) 样本质量达到 SOTA 水平。

Sohl-Dickstein 等人（2015）给出了理论答案：定义一条逐步加入高斯噪声的马尔可夫链 `q(x_t | x_{t-1})`，再训练一条反向链 `p_θ(x_{t-1} | x_t)` 来去噪。Ho、Jain、Abbeel（2020）证明这个损失可以简化成一行 —— 预测噪声 —— 并把数学清理干净。2020 年它还是个冷门珍奇，2021 年它产出了最先进的样本，2022 年它变成了 Stable Diffusion，2026 年它是整个领域的地基。

> You want a sampler for `p_data(x)`. ... What you really want is a training objective that is (a) a single stable loss (no saddle point, no minimax), (b) a lower bound on `log p(x)` (so you have likelihoods), and (c) samples that match SOTA quality. ... Sohl-Dickstein et al. (2015) had a theoretical answer: define a Markov chain `q(x_t | x_{t-1})` that gradually adds Gaussian noise, and train a reverse chain `p_θ(x_{t-1} | x_t)` to denoise. ... Ho, Jain, Abbeel (2020) showed the loss could be simplified to one line — predict the noise — and cleaned up the math. ... In 2020 this was a curiosity. In 2021 it produced state-of-the-art samples. In 2022 it became Stable Diffusion. In 2026 it is the substrate.

## The Concept · 概念

![DDPM：前向加噪，反向去噪](../assets/ddpm.svg)

**前向过程 `q`。** 在 `T` 个小步里逐步加入高斯噪声。闭式解（closed form）—— 数学之所以可处理的原因 —— 是累计加噪之后的分布仍然是高斯的：

```
q(x_t | x_0) = N( sqrt(α̅_t) · x_0,  (1 - α̅_t) · I )
```

其中 `α̅_t = ∏_{s=1..t} (1 - β_s)`，`β_t` 来自某个噪声调度（schedule）。在 T=1000 步内把 `β_t` 从 1e-4 线性取到 0.02，`x_T` 就近似服从 `N(0, I)`。

**反向过程 `p_θ`。** 学习一个神经网络 `ε_θ(x_t, t)`，让它预测当初加进去的噪声。给定 `x_t`，按下式去噪：

```
x_{t-1} = (1 / sqrt(α_t)) · ( x_t - (β_t / sqrt(1 - α̅_t)) · ε_θ(x_t, t) )  +  σ_t · z
```

其中 `σ_t` 取 `sqrt(β_t)` 或一个可学习的方差。这个表达式很丑，但它只是代数 —— 从后验 `q(x_{t-1} | x_t, x_0)` 解出 `x_{t-1}`，再用噪声预测得到的 `x_0` 估计代入。

**训练损失。**

```
L_simple = E_{x_0, t, ε} [ || ε - ε_θ( sqrt(α̅_t) · x_0 + sqrt(1 - α̅_t) · ε,  t ) ||² ]
```

从数据中采样 `x_0`，随机挑一个 `t`，采样 `ε ~ N(0, I)`，用闭式解一步算出带噪的 `x_t`，然后对噪声做回归。一个损失，没有 minimax，没有 KL，没有重参数化技巧。

**采样。** 从 `x_T ~ N(0, I)` 出发，把反向步从 `t = T` 迭代到 `1`。完成。

> **Forward process `q`.** Add Gaussian noise in `T` small steps. The closed form — the reason the math is tractable — is that the cumulative step is also Gaussian ... **Reverse process `p_θ`.** Learn a neural net `ε_θ(x_t, t)` that predicts the noise that was added ... **Training loss.** Sample `x_0` from data, pick a random `t`, sample `ε ~ N(0, I)`, compute the noisy `x_t` in one shot via the closed form, and regress on the noise. One loss, no minimax, no KL, no reparameterization tricks ... **Sampling.** Start `x_T ~ N(0, I)`. Iterate the reverse step from `t = T` to `1`. Done.

## Why it works · 为什么有效

三条直觉：

1. **去噪容易，生成难。** 在 `t=T` 时，数据就是纯噪声 —— 网络要解决的是一个轻而易举的问题。在 `t=0` 时，网络只需要清理少量像素。在中间的 `t`，问题很难，但每个噪声 level 的梯度都流过同一批权重，网络因此获得大量学习信号。

2. **伪装起来的 score matching（分数匹配）。** Vincent（2011）证明了预测噪声等价于估计 `∇_x log q(x_t | x_0)`，也就是 *score*。反向 SDE 利用这个 score 沿着密度梯度向上走 —— 一场朝高概率区域前进的「有引导的随机游走」。

3. **ELBO 化简为简单的 MSE。** 完整的变分下界在每个时间步都有一个 KL 项。在 DDPM 的参数化下，这些 KL 项化简为带特定系数的「噪声预测 MSE」；Ho 直接把系数丢掉（称之为 simple 损失），质量反而*提升*了。

```figure
diffusion-denoise
```

> **Denoising is easy; generating is hard.** At `t=T`, the data is pure noise — the net has to solve a trivial problem ... **Score matching in disguise.** Vincent (2011) proved that predicting the noise is equivalent to estimating `∇_x log q(x_t | x_0)`, the *score* ... **The ELBO reduces to simple MSE.** ... Ho dropped the coefficients (calling it "simple" loss) and quality *improved*.

## Build It · 动手造

`code/main.py` 实现了一个 1-D DDPM。数据是一个双峰混合分布。「网络」是一个接收 `(x_t, t)`、输出预测噪声的小型 MLP。训练就是那个单行损失。采样则迭代反向链。

> `code/main.py` implements a 1-D DDPM. Data is a two-mode mixture. ... Training is the one-line loss. Sampling iterates the reverse chain.

### Step 1: the forward schedule (closed form) · 第 1 步：前向调度（闭式解）

```python
betas = [1e-4 + (0.02 - 1e-4) * t / (T - 1) for t in range(T)]
alphas = [1 - b for b in betas]
alpha_bars = []
cum = 1.0
for a in alphas:
    cum *= a
    alpha_bars.append(cum)
```

### Step 2: sample `x_t` in one shot · 第 2 步：一步采出 `x_t`

```python
def forward_sample(x0, t, alpha_bars, rng):
    a_bar = alpha_bars[t]
    eps = rng.gauss(0, 1)
    x_t = math.sqrt(a_bar) * x0 + math.sqrt(1 - a_bar) * eps
    return x_t, eps
```

### Step 3: one training step · 第 3 步：一次训练步

```python
def train_step(x0, model, alpha_bars, rng):
    t = rng.randrange(T)
    x_t, eps = forward_sample(x0, t, alpha_bars, rng)
    eps_hat = model_forward(model, x_t, t)
    loss = (eps - eps_hat) ** 2
    return loss, gradient_step(model, ...)
```

### Step 4: reverse sampling · 第 4 步：反向采样

```python
def sample(model, alpha_bars, T, rng):
    x = rng.gauss(0, 1)
    for t in range(T - 1, -1, -1):
        eps_hat = model_forward(model, x, t)
        beta_t = 1 - alphas[t]
        x = (x - beta_t / math.sqrt(1 - alpha_bars[t]) * eps_hat) / math.sqrt(alphas[t])
        if t > 0:
            x += math.sqrt(beta_t) * rng.gauss(0, 1)
    return x
```

对一个 1-D 问题、40 个时间步、24 个单元的 MLP，大约 200 个 epoch 就能学会这个双峰混合分布。

> For a 1-D problem with 40 timesteps and a 24-unit MLP, this learns the two-mode mixture in ~200 epochs.

## Time conditioning · 时间步条件化

网络需要知道自己正在对哪个时间步去噪。两种标准做法：

- **正弦嵌入（sinusoidal embedding）。** 类似 Transformer 的位置编码。`embed(t) = [sin(t/ω_0), cos(t/ω_0), sin(t/ω_1), ...]`。过一个 MLP，再广播进网络。
- **FiLM / group-norm 条件化。** 把嵌入投影成每个 block 的逐通道 scale/bias（FiLM）。

我们的玩具代码用正弦嵌入 → 拼接。生产级 U-Net 用 FiLM。

> The net needs to know which timestep it is denoising. Two standard options: ... Our toy code uses sinusoidal → concat. Production U-Nets use FiLM.

## Pitfalls · 常见坑

- **调度非常关键。** 线性 `β` 是 DDPM 的默认，但 cosine 调度（Nichol & Dhariwal, 2021）在同等算力下 FID 更好。质量停滞时换个调度。
- **时间步嵌入很脆弱。** 把原始 `t` 当浮点数传入，在玩具级 1-D 里能跑，在图像上就失效；永远用正规的嵌入。
- **V-prediction vs ε-prediction。** 在极端区间（t 特别小或特别大）里，`ε` 的信噪比很差。V-prediction（`v = α·ε - σ·x`）更稳定；SDXL、SD3、Flux 都用它。
- **Classifier-free guidance。** 推理时同时计算条件与无条件 `ε`，然后 `ε_cfg = (1 + w) · ε_cond - w · ε_uncond`，`w ≈ 3-7`。第 08 课讲。
- **1000 步太多了。** 生产环境用 DDIM（20-50 步）、DPM-Solver（10-20 步）或蒸馏（1-4 步）。见第 12 课。

> **Schedule matters a lot.** Linear `β` is the DDPM default but cosine schedule (Nichol & Dhariwal, 2021) gives better FID for the same compute ... **V-prediction vs ε-prediction.** For narrow regimes (very small or very large t), `ε` has poor signal-to-noise. V-prediction (`v = α·ε - σ·x`) is more stable; SDXL, SD3, and Flux use it ... **1000 steps is a lot.** Production uses DDIM (20-50 steps), DPM-Solver (10-20 steps), or distillation (1-4 steps).

## Use It · 实战用法

| 用途 | 2026 年典型技术栈 |
|------|-----------------------|
| 图像像素空间扩散（小型、玩具级） | DDPM + U-Net |
| 图像潜空间扩散（latent diffusion） | VAE encoder + U-Net 或 DiT（第 07 课） |
| 视频潜空间扩散 | 时空 DiT（Sora、Veo、WAN） |
| 音频潜空间扩散 | Encodec + diffusion transformer |
| 科学（分子、蛋白质、物理） | 等变扩散（EDM、RFdiffusion、AlphaFold3） |

扩散是通用的生成式底座。Flow matching（第 13 课）是 2024-2026 年的竞争者，在同等质量下通常推理速度更胜一筹。

> Diffusion is the universal generative backbone. Flow matching (Lesson 13) is the 2024-2026 competitor that usually wins on inference speed for the same quality.

## Ship It · 交付

保存 `outputs/skill-diffusion-trainer.md`。这个 skill 接收一个数据集 + 算力预算，输出：调度（linear/cosine/sigmoid）、预测目标（ε/v/x）、步数、guidance scale、采样器家族，以及一套评估协议。

> Save `outputs/skill-diffusion-trainer.md`. Skill takes a dataset + compute budget and outputs: schedule (linear/cosine/sigmoid), prediction target (ε/v/x), number of steps, guidance scale, sampler family, and an eval protocol.

## Exercises · 练习

1. **简单。** 把 `code/main.py` 里的 T 从 40 改成 10。样本质量（输出的可视化直方图）如何退化？T 降到多少时双峰结构坍塌？
2. **中等。** 把 ε-prediction 换成 v-prediction。重新推导反向步。对比最终样本质量。
3. **困难。** 加上 classifier-free guidance。以类别标签 `c ∈ {0, 1}` 为条件，训练时 10% 的概率丢弃标签，采样时用 `ε = (1+w)·ε_cond - w·ε_uncond`。测量 `w = 0, 1, 3, 7` 下的条件模式命中率。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Forward process | 「加噪声」 | 固定的马尔可夫链 `q(x_t \| x_{t-1})`，负责毁掉数据。 |
| Reverse process | 「去噪」 | 学出来的链 `p_θ(x_{t-1} \| x_t)`，负责重建数据。 |
| β schedule | 「噪声梯子」 | 每一步的方差；线性、cosine 或 sigmoid。 |
| α̅ | 「alpha bar」 | 累乘 `∏(1 - β)`；给出从 `x_0` 直达 `x_t` 的闭式解。 |
| Simple loss | 「对噪声做 MSE」 | `\|\|ε - ε_θ(x_t, t)\|\|²`；所有变分推导最终都坍缩成它。 |
| ε-prediction | 「预测噪声」 | 输出是加进去的噪声；标准 DDPM。 |
| V-prediction | 「预测速度」 | 输出是 `α·ε - σ·x`；在各个 t 上条件更稳定。 |
| DDPM | 「那篇论文」 | Ho et al. 2020；线性 β、1000 步、U-Net。 |
| DDIM | 「确定性采样器」 | 非马尔可夫采样器，20-50 步，训练目标不变。 |
| Classifier-free guidance | 「CFG」 | 混合条件与无条件噪声预测，放大条件的作用。 |

## Production note: diffusion inference is a step-count problem · 生产备注：扩散推理是步数问题

DDPM 论文要跑 T=1000 个反向步。没有人在生产环境这么干。每个真实的推理栈都会从三种策略里挑一种 —— 每一种都能干净地对应到生产语境里的那个问题：「延迟到底从哪来」：

1. **更快的采样器，模型不动。** DDIM（20-50 步）、DPM-Solver++（10-20）、UniPC（8-16）。直接替换反向循环即可；训练好的 `ε_θ` 权重原封不动。延迟降低 20-50 倍。
2. **蒸馏。** 训一个学生模型，用更少的步数匹配老师：Progressive Distillation（2 → 1）、Consistency Models（任意 → 1-4）、LCM、SDXL-Turbo、SD3-Turbo。延迟再降 5-10 倍，但需要重新训练。
3. **缓存与编译。** `torch.compile(unet, mode="reduce-overhead")`、TensorRT-LLM 的 diffusion 后端、`xformers`/SDPA attention、bf16 权重。每步延迟降低约 2 倍。可与 (1) 和 (2) 叠加。

对一个生产级 diffusion 服务器，预算话题与生产文献对 LLM 的描述如出一辙：延迟是 `num_steps × step_cost + VAE_decode`，吞吐是 `batch_size × (num_steps × step_cost)^-1`。TTFT 很小（就一步）；TPOT 的等价物是完整响应时间，因为从用户视角看，图像生成是「一次性整体交付」的。

> The DDPM paper runs T=1000 reverse steps. Nobody ships that in production ... **Faster sampler, same model.** DDIM (20-50 steps), DPM-Solver++ (10-20), UniPC (8-16). Drop-in replacement of the reverse loop; the trained `ε_θ` weights are untouched. Cuts latency 20-50× ... latency is `num_steps × step_cost + VAE_decode`, throughput is `batch_size × (num_steps × step_cost)^-1`.

## Further Reading · 延伸阅读

- [Sohl-Dickstein et al. (2015). Deep Unsupervised Learning using Nonequilibrium Thermodynamics](https://arxiv.org/abs/1503.03585) —— 扩散模型的开山论文，超前于时代。
- [Ho, Jain, Abbeel (2020). Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239) —— DDPM。
- [Song, Meng, Ermon (2021). Denoising Diffusion Implicit Models](https://arxiv.org/abs/2010.02502) —— DDIM，步数更少。
- [Nichol & Dhariwal (2021). Improved DDPM](https://arxiv.org/abs/2102.09672) —— cosine 调度、可学习方差。
- [Dhariwal & Nichol (2021). Diffusion Models Beat GANs on Image Synthesis](https://arxiv.org/abs/2105.05233) —— classifier guidance。
- [Ho & Salimans (2022). Classifier-Free Diffusion Guidance](https://arxiv.org/abs/2207.12598) —— CFG。
- [Karras et al. (2022). Elucidating the Design Space of Diffusion-Based Generative Models (EDM)](https://arxiv.org/abs/2206.00364) —— 统一记号，最干净的配方。
