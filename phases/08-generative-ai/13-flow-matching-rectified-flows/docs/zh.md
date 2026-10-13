# Flow Matching & Rectified Flows · 流匹配与校正流

扩散模型要 20-50 个采样步，因为它走的是一条从噪声到数据的弯曲路径。流匹配（flow matching，Lipman et al., 2023）和校正流（rectified flow，Liu et al., 2022）训练的是笔直的路径。路径越直，步数越少，推理越快。Stable Diffusion 3、Flux.1 和 AudioCraft 2 都在 2024 年切换到了流匹配。

> Diffusion models take 20-50 sampling steps because they walk a curved path from noise to data. Flow matching (Lipman et al., 2023) and rectified flow (Liu et al., 2022) trained straight paths. Straighter paths mean fewer steps mean faster inference. Stable Diffusion 3, Flux.1, and AudioCraft 2 all switched to flow matching in 2024.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 8 · 06 (DDPM), Phase 1 · Calculus
**Time:** ~45 minutes

## The Problem · 问题在哪

DDPM 的反向过程是从 `N(0, I)` 走回数据分布的 1000 步随机游走。DDIM 把它压缩到 20-50 个确定性步。你想要更少 —— 理想是一步。障碍在于求解反向过程的 ODE 是刚性的（stiff），路径是弯的。

如果你能训练模型使从噪声到数据的路径是一条*直线*，那么从 `t=1` 到 `t=0` 一步欧拉法就能工作。流匹配直接把这个构造出来：定义一条从 `x_1 ∼ N(0, I)` 到 `x_0 ∼ data` 的直线插值，训练一个向量场 `v_θ(x, t)` 去匹配它对时间的导数，推理时做积分。

校正流（Liu 2022）更进一步：用 reflow（重整流）过程迭代地拉直路径，得到一个逐步逼近线性的 ODE。两次 reflow 迭代之后，2 步采样器就能匹配 50 步 DDPM 的质量。

> DDPM's reverse process is a 1000-step stochastic walk from `N(0, I)` back to the data distribution. DDIM collapsed it to 20-50 deterministic steps. You want fewer steps — ideally one. The blocker is that the ODE solving the reverse process is stiff; the path is curved.
> If you could train the model such that the path from noise to data was a *straight line*, a single Euler step from `t=1` to `t=0` would work. Flow matching builds this directly: define a straight-line interpolation from `x_1 ∼ N(0, I)` to `x_0 ∼ data`, train a vector field `v_θ(x, t)` to match its time derivative, integrate at inference.
> Rectified flow (Liu 2022) goes further: iteratively straighten the paths with a reflow procedure that produces a progressively closer-to-linear ODE. After two reflow iterations, a 2-step sampler matches 50-step DDPM quality.

## The Concept · 概念

![流匹配：噪声与数据之间的直线插值](../assets/flow-matching.svg)

### Straight-line flow · 直线流

定义：

```
x_t = t · x_1 + (1 - t) · x_0,   t ∈ [0, 1]
```

其中 `x_0 ~ data`，`x_1 ~ N(0, I)`。沿这条直线的时间导数是常数：

```
dx_t / dt = x_1 - x_0
```

定义一个神经向量场 `v_θ(x_t, t)`，训练它去匹配这个导数：

```
L = E_{x_0, x_1, t} || v_θ(x_t, t) - (x_1 - x_0) ||²
```

这就是**条件流匹配（conditional flow matching）**损失（Lipman 2023）。训练是无仿真（simulation-free）的：你从不需要展开 ODE。只需采样 `(x_0, x_1, t)` 然后做回归。

> Define a neural vector field `v_θ(x_t, t)` and train it to match this derivative:
> This is the **conditional flow matching** loss (Lipman 2023). Training is simulation-free: you never unroll the ODE. Just sample `(x_0, x_1, t)` and regress.

### Sampling · 采样

推理时，把学到的向量场沿时间*反向*积分：

```
x_{t-Δt} = x_t - Δt · v_θ(x_t, t)
```

从 `x_1 ~ N(0, I)` 出发，用欧拉步一路走到 `t=0`。

> At inference, integrate the learned vector field *backwards* in time:
> Start at `x_1 ~ N(0, I)`, Euler-step down to `t=0`.

### Rectified flow (Liu 2022) · 校正流（Liu 2022）

直线流能用，但学到的路径*其实并不直* —— 因为许多 `x_0` 会映射到同一个 `x_1`，路径会弯。校正流的 reflow 步骤：

1. 用随机配对训练流模型 v_1。
2. 通过把 v_1 从 `x_1` 积分到它的落点 `x_0`，采样 N 对 `(x_1, x_0)`。
3. 在这些配对样本上训练 v_2。因为这些配对现在「ODE 匹配」，它们之间的直线插值就真的更平了。
4. 重复。

实践中 2 次 reflow 迭代就能接近线性，从而支持 2-4 步推理。SDXL-Turbo、SD3-Turbo、LCM 全是从流匹配蒸馏出来的模型。

> Straight-line flow works but the learned paths are *not actually straight* — they curve because many `x_0`s can map to the same `x_1`. Rectified flow's reflow step:
> 1. Train flow model v_1 with random pairings. ...
> 2. Sample N pairs `(x_1, x_0)` by integrating v_1 from `x_1` to its landing `x_0`. ...
> 3. Train v_2 on those paired examples. Because the pairs are now "ODE-matched", the straight-line interpolant between them is genuinely flatter. ...
> In practice 2 reflow iterations get you to near-linear, enabling 2-4 step inference. SDXL-Turbo, SD3-Turbo, LCM are all distilled-from-flow-matching models.

### Why this won for images in 2024 · 为什么它在 2024 年赢下了图像

三个原因：

1. **无仿真训练** —— 训练时不展开 ODE，实现极其简单。
2. **更好的损失几何** —— 直线路径有稳定的信噪比，而 DDPM 的 ε 损失在调度两端 SNR 很差。
3. **更快的推理** —— SDXL-Turbo 质量只要 4-8 步；加一致性蒸馏可以 1 步。

> Three reasons:
> 1. **Simulation-free training** — no ODE unrolling during training, trivial to implement. ...
> 2. **Better loss geometry** — straight paths have consistent signal-to-noise, whereas DDPM ε-loss has bad SNR at edges of the schedule. ...
> 3. **Faster inference** — 4-8 steps at SDXL-Turbo quality; 1 step with consistency distillation.

## Flow matching vs DDPM — the exact connection · 流匹配 vs DDPM —— 精确联系

高斯条件路径下的流匹配就是*带特定噪声调度*的扩散。取 `x_t = α(t) x_0 + σ(t) x_1` 这种调度，流匹配就恢复出 Stratonovich 重构形式的扩散，其中 `v = α'·x_0 - σ'·x_1`。对高斯路径而言，两者在代数上等价。

流匹配真正 adds 的东西：目标（一个朴素的速度）的*清晰性*、更干净的损失，以及尝试非高斯插值的自由。

> Flow matching with a Gaussian-conditional path is diffusion *with a specific noise schedule*. Pick the `x_t = α(t) x_0 + σ(t) x_1` schedule and flow matching recovers Stratonovich-reformulated diffusion with `v = α'·x_0 - σ'·x_1`. The two are algebraically equivalent for Gaussian paths.
> What flow matching added: the *clarity* of the target (a plain velocity), a cleaner loss, and the license to experiment with non-Gaussian interpolants.

```figure
normalizing-flow
```

## Build It · 动手造

`code/main.py` 在双峰高斯混合上实现 1-D 流匹配。向量场 `v_θ(x, t)` 是一个用直线目标训练的微型 MLP。推理时分别用 1、2、4、20 个欧拉步积分，并比较样本质量。

> `code/main.py` implements 1-D flow matching on a two-mode Gaussian mixture. The vector field `v_θ(x, t)` is a tiny MLP trained with the straight-line target. At inference, integrate 1, 2, 4, and 20 Euler steps and compare sample quality.

### Step 1: training loss · 第 1 步：训练损失

```python
def train_step(x0, net, rng, lr):
    x1 = rng.gauss(0, 1)
    t = rng.random()
    x_t = t * x1 + (1 - t) * x0
    target = x1 - x0
    pred = net_forward(x_t, t)
    loss = (pred - target) ** 2
    # backprop + update
```

### Step 2: multi-step inference · 第 2 步：多步推理

```python
def sample(net, num_steps):
    x = rng.gauss(0, 1)
    for i in range(num_steps):
        t = 1.0 - i / num_steps
        dt = 1.0 / num_steps
        x -= dt * net_forward(x, t)
    return x
```

### Step 3: compare step counts · 第 3 步：比较步数

预期 4 步采样器就已经能匹配 20 步的质量 —— 对延迟来说是件大事。

> Expect the 4-step sampler to already match the 20-step quality — a big deal for latency.

## Pitfalls · 常见坑

- **时间参数化。** 流匹配用 `t ∈ [0, 1]`，`t=0` 在数据端，`t=1` 在噪声端。DDPM 用 `t ∈ [0, T]`，`t=0` 在数据端，`t=T` 在噪声端。方向相同，尺度不同。论文经常在这上面出错。
- **调度选择。** 校正流的直线是「那个」流匹配调度，但你也可以用 cosine 或 logit-normal 的 t 采样（SD3 就是这么做的）来获得更好的尺度覆盖。
- **Reflow 的代价。** 为 reflow 生成配对数据集，每个样本都要跑一整次推理。只有真的需要 1-2 步推理时才做 reflow。
- **Classifier-free guidance 依然适用。** 只要把线性组合里的 ε 换成 v：`v_cfg = (1+w) v_cond - w v_uncond`。

> **Time parameterization.** Flow matching uses `t ∈ [0, 1]` with `t=0` at data, `t=1` at noise. DDPM uses `t ∈ [0, T]` with `t=0` at data, `t=T` at noise. Same direction, different scale. Papers get this wrong constantly. ...
> **Reflow cost.** Generating the paired dataset for reflow is a full inference pass per sample. Only do reflow when you really need 1-2 step inference. ...
> **Classifier-free guidance still applies.** Just swap ε for v in the linear combination: `v_cfg = (1+w) v_cond - w v_uncond`.

## Use It · 实战用法

| 用例 | 2026 年技术栈 |
|----------|-----------|
| 文生图，最佳质量 | 流匹配：SD3、Flux.1-dev |
| 文生图，1-4 步 | 蒸馏流匹配：Flux.1-schnell、SD3-Turbo、SDXL-Turbo |
| 实时推理 | 从流匹配基座做一致性蒸馏（LCM、PCM） |
| 音频生成 | 流匹配：Stable Audio 2.5、AudioCraft 2 |
| 视频生成 | 流匹配与扩散混用（Sora、Veo、Stable Video） |
| 科学 / 物理（粒子轨迹、分子） | 流匹配 + 等变向量场 |

2025-2026 年，每当一篇论文说「比扩散快」，它几乎总是在说流匹配 + 蒸馏。

> Whenever a paper says "faster than diffusion" in 2025-2026, it is almost always flow matching + distillation.

## Ship It · 交付

保存 `outputs/skill-fm-tuner.md`。这个 skill 接收一个扩散风格的模型规格，把它转换成流匹配训练配置：调度选择、时间采样分布（uniform / logit-normal）、优化器、reflow 计划、目标步数、评测协议。

> Save `outputs/skill-fm-tuner.md`. Skill takes a diffusion-style model spec and converts it to a flow-matching training config: schedule choice, time sampling distribution (uniform / logit-normal), optimizer, reflow plan, target step count, eval protocol.

## Exercises · 练习

1. **简单。** 跑 `code/main.py`，比较 1 步与 20 步相对真实数据分布的 MSE。
2. **中等。** 把均匀 `t` 采样换成 logit-normal（把采样集中在中段 t）。模型质量提高了吗？
3. **困难。** 实现一次 reflow 迭代：积分第一个模型生成配对 (x_0, x_1)，在配对上训练第二个模型，比较 1 步采样质量。

> 1. **Easy.** Run `code/main.py` and compare 1-step vs 20-step MSE vs the true data distribution. ...
> 2. **Medium.** Switch from uniform `t` sampling to logit-normal (concentrates sampling at mid-t). Does the model quality improve? ...
> 3. **Hard.** Implement one reflow iteration: generate paired (x_0, x_1) by integrating the first model, train a second model on the pairs, and compare 1-step sample quality.

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Flow matching（流匹配） | "直线版扩散" | 训练 `v_θ(x, t)` 去匹配插值路径上的 `x_1 - x_0`。 |
| Rectified flow（校正流） | "Reflow" | 迭代拉直已学流的过程。 |
| Velocity field（速度场） | "v_θ" | 模型的输出 —— `x_t` 该移动的方向。 |
| Straight-line interpolant（直线插值） | "那条路径" | `x_t = (1-t)·x_0 + t·x_1`；目标导数一目了然。 |
| Euler sampler | "一阶 ODE 求解器" | 最简单的积分器；路径直的时候很好用。 |
| Logit-normal t | "SD3 采样" | 把 `t` 采样集中到梯度最强的中段取值。 |
| Consistency distillation（一致性蒸馏） | "1 步采样器" | 训练一个学生模型把任意 `x_t` 直接映射到 `x_0`。 |
| CFG with velocity | "v-CFG" | `v_cfg = (1+w) v_cond - w v_uncond`；同一个技巧，换了变量。 |

## Production note: Flux.1-schnell is flow matching at its fastest · 生产备注：Flux.1-schnell 是流匹配的最快形态

流匹配在生产上的胜利是 Flux.1-schnell —— 一个蒸馏到 1-4 步推理、同时保住 Flux-dev 级质量的流匹配 DiT。Niels 的「在 8GB 机器上跑 Flux」notebook 是参考部署配方：T5 + CLIP 编码、量化 MMDiT 去噪（schnell 用 4 步 vs dev 用 50 步）、VAE 解码。成本核算：

| 变体 | 步数 | L4 上 1024² 延迟 | 总 FLOPs（相对） |
|---------|-------|------------------------|------------------------|
| Flux.1-dev (raw) | 50 | ~15 s | 1.0× |
| Flux.1-schnell | 4 | ~1.2 s | 0.08×（快 12 倍） |
| SDXL-base | 30 | ~4 s | 0.25× |
| SDXL-Lightning 2-step | 2 | ~0.3 s | 0.03× |

生产规则：**流匹配基座 + 蒸馏 = 2026 年快速文生图的默认选择。** 每个主要厂商都在发这套组合：SD3-Turbo（SD3 + 流匹配 + 蒸馏）、Flux-schnell（Flux-dev + 校正流拉直）、CogView-4-Flash。纯扩散基座只以遗留 checkpoint 的形式存在。

> Flow matching's production win is Flux.1-schnell — a flow-matched DiT distilled to 1-4 inference steps while keeping Flux-dev-grade quality. Niels' "Run Flux on an 8GB machine" notebook is the reference deployment recipe: T5 + CLIP encode, quantized MMDiT denoise (in 4 steps for schnell vs 50 for dev), VAE decode. The cost accounting:
> The production rule: **flow-matched base + distillation = the 2026 default for fast text-to-image.** Every major vendor ships this combo: SD3-Turbo (SD3 + flow + distillation), Flux-schnell (Flux-dev + rectified-flow straightening), CogView-4-Flash. Pure diffusion bases exist only for legacy checkpoints.

## Further Reading · 延伸阅读

- [Liu, Gong, Liu (2022). Flow Straight and Fast: Learning to Generate and Transfer Data with Rectified Flow](https://arxiv.org/abs/2209.03003) —— 校正流。
- [Lipman et al. (2023). Flow Matching for Generative Modeling](https://arxiv.org/abs/2210.02747) —— 流匹配。
- [Esser et al. (2024). Scaling Rectified Flow Transformers for High-Resolution Image Synthesis](https://arxiv.org/abs/2403.03206) —— SD3，大规模的校正流。
- [Albergo, Vanden-Eijnden (2023). Stochastic Interpolants](https://arxiv.org/abs/2303.08797) —— 覆盖流匹配 + 扩散的一般框架。
- [Song et al. (2023). Consistency Models](https://arxiv.org/abs/2303.01469) —— 扩散 / 流的 1 步蒸馏。
- [Sauer et al. (2023). Adversarial Diffusion Distillation (SDXL-Turbo)](https://arxiv.org/abs/2311.17042) —— turbo 变体。
- [Black Forest Labs (2024). Flux.1 models](https://blackforestlabs.ai/announcing-black-forest-labs/) —— 生产中的流匹配。
