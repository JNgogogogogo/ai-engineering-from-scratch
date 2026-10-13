# Scaling Laws · 缩放定律：算力该怎么花

> 2020 年的 Kaplan 论文说：模型越大，loss 越低。2022 年的 Hoffmann 论文说：你之前训得不够。算力要分进两个桶——参数和 token——怎么分并不显然。
>
> The 2020 Kaplan paper said: bigger model, lower loss. The 2022 Hoffmann paper said: you were under-training. Compute goes into two buckets — parameters and tokens — and the split is not obvious.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 7 · 05 (Full Transformer), Phase 7 · 07 (GPT)
**Time:** ~45 minutes

## The Problem · 问题在哪

当你有 C FLOPs 的训练算力、想要最好的模型时，面前有两个旋钮：

1. **参数量（N）取多少？** 模型越大，容量越高。
2. **训练 token 数（D）取多少？** 数据越多，容量利用越充分。

FLOPs 近似为 `6 × N × D`。你可以把 N 推大、D 压小，也可以 D 推大、N 压小。哪个更好？

2022 年之前，答案是「猛推 N」。GPT-3（2020）有 175B 参数、约 300B token 的训练量，比率约为每参数 1.7 token。Kaplan 缩放定律（scaling laws）也支持这个方向。

Hoffmann et al.（2022）训练了一个叫 Chinchilla 的小模型家族，发现了不同的结论：最优比率接近**每参数 20 token**。GPT-3 训练不足了 10 倍。Chinchilla（70B 参数、1.4T token）在每个基准上击败 GPT-3（175B、300B token），推理成本还只有它的 1/2.5。

2026 年是 Chinchilla 的世界——但带一个重要转折。Llama 3 8B 用 15 万亿 token 训练，比率是每参数 1,875 token，达到 Chinchilla 最优值的 94 倍。对将要大规模使用的模型来说，推理成本比训练成本更重要，所以「越过 Chinchilla 做过训练（over-training），换一个更小的可部署体积」是 2026 年的默认做法。

> When you have C FLOPs of training compute and want the best model, you face two knobs:
> 1. **How many parameters (N)?** Bigger model, higher capacity.
> 2. **How many training tokens (D)?** More data, better use of capacity.
> FLOPs scale approximately as `6 × N × D`. You can push N up and D down, or D up and N down. Which is better?
> Before 2022, the answer was "push N hard." GPT-3 (2020) was 175B parameters trained on ~300B tokens. A ratio of about 1.7 tokens per parameter. The Kaplan scaling laws backed this up.
> Hoffmann et al. (2022), training a small family of models called Chinchilla, found something different: optimal ratio is closer to **20 tokens per parameter**. GPT-3 was 10× undertrained. Chinchilla (70B params, 1.4T tokens) beat GPT-3 (175B, 300B tokens) on every benchmark at 2.5× less inference cost.
> 2026 is Chinchilla's world — with one important twist. Llama 3 8B was trained on 15 trillion tokens, a ratio of 1,875 tokens per parameter. Ninety-four times past Chinchilla-optimal. Inference cost matters more than training cost for models that will be used at scale, so over-training (past Chinchilla) for a smaller deployable footprint is the 2026 default.

## The Concept · 概念

![Chinchilla 曲线：不同 N/D 比率下 loss 随算力的变化](../assets/scaling-laws.svg)

### The Hoffmann law · Hoffmann 定律

来自 Chinchilla 论文，loss 满足：

```
L(N, D) = A / N^α + B / D^β + E
```

- `N` = 参数量（非嵌入部分）。
- `D` = 训练 token 数。
- `α ≈ 0.34`，`β ≈ 0.28`（大致对称）。
- `E ≈ 1.69`，不可约的 loss 天花板。
- `A ≈ 406`，`B ≈ 411`。

缩放时两项互相拉锯。在固定算力（C = 6ND）下对 `N` 求导并求解：

```
N_opt ≈ 0.6 × (C/6)^0.5
D_opt ≈ 0.6 × (C/6)^0.5
D_opt / N_opt ≈ 20
```

计算最优（compute-optimal）：每参数 20 token。

> From the Chinchilla paper, loss follows:
> - `N` = parameters (non-embedding).
> - `D` = training tokens.
> - `α ≈ 0.34`, `β ≈ 0.28` (roughly symmetric).
> - `E ≈ 1.69`, the irreducible loss ceiling.
> - `A ≈ 406`, `B ≈ 411`.
> Two terms trade against each other as you scale. Take the derivative w.r.t. `N` at fixed compute (C = 6ND) and solve:
> Compute-optimal: 20 tokens per parameter.

### Why over-training anyway · 那为什么还要过训练

Chinchilla 最优最小化的是「每训练 FLOP 的训练 loss」。但训练成本只付一次，推理成本却是永久的。

对一个每月服务一万亿 token 的聊天机器人来说，推理成本主导总成本。Llama 的路线：训得更小、更久。8B 配 15T token 是深度推理优化的：

- 塞得进消费级 GPU。
- 延迟只有 70B Chinchilla 最优模型的零头。
- 对多数任务质量足够接近。

DeepMind 2024 年的论文（"Over-training is the new optimal"）把这一点正式化了。对推理主导的负载，合适的比率更接近每参数 100–500 token，取决于服务量。

> Chinchilla-optimal minimizes training loss per training FLOP. But you pay training cost once; inference cost forever.
> For a chatbot that serves a trillion tokens per month, inference dominates total cost. Llama's approach: train smaller, longer. 8B at 15T tokens is deeply inference-optimized:
> - Fits on consumer GPUs.
> - Latency is a fraction of 70B Chinchilla-optimal.
> - Quality is close enough for most tasks.
> DeepMind's 2024 paper ("Over-training is the new optimal") formalized this. For inference-dominated workloads, the right ratio is closer to 100–500 tokens per parameter depending on serving volume.

### Emergence vs smoothness · 涌现 vs 平滑

说法：某些能力（算术、多步推理、遵循思维链）会在某个规模上「突然涌现」。

Schaeffer et al.（2023）指出这多半是测量假象：涌现类指标使用不连续的打分（精确匹配、阈值准确率），掩盖了底层 logits 的平滑进步。连续指标（交叉熵）显示的则是平滑曲线。

2026 年的共识是：基于连续 loss 做预测是可靠的。基准上的跳变常常是打分器的假象。做预算规划时盯住连续指标。

> Claim: certain abilities (arithmetic, multi-step reasoning, chain-of-thought following) "emerge" suddenly at some scale.
> Schaeffer et al. (2023) argued this is a measurement artifact: emergent metrics use discontinuous scoring (exact match, accuracy at threshold) that hide smooth improvement in the underlying logits. Continuous metrics (cross-entropy) show smooth curves.
> In 2026 the consensus is: predictions via continuous loss are reliable. Benchmark jumps are often scorer artifacts. Plan budgets against continuous metrics.

### The 2026 picture · 2026 年的图景

缩放定律依然有效，但是：

| 因素 | 改变方式 |
|--------|-------------|
| 数据质量 | 策展「好」token（Phi 风格）能把曲线平移超过 2 倍有效算力 |
| MoE | 总参数与激活 FLOPs 解耦；缩放定律按每激活 FLOP 计 |
| 后训练 | 有些能力（指令遵循、代码）随 SFT+RLHF 的变化大于随预训练的变化 |
| 多模态 | 图像 + 文本 token 一起缩放；每个模态各有曲线 |
| 合成数据 | 模型自己生成训练数据；有效算力可以复利 |

Muon 优化器（Kimi Moonlight，2024）在同等数据下展示了相对 AdamW 约 2 倍的有效算力增益。一些 2026 年的训练任务默认使用 Muon。它改变的是缩放定律里的绝对常数，而不是形状。

```figure
scaling-laws
```

> Scaling laws still work, but:
> The Muon optimizer (Kimi Moonlight, 2024) showed a ~2× effective-compute gain over AdamW at matched data. Some 2026 training runs use Muon by default. Changes the absolute constant in the scaling law, not its shape.

## Build It · 动手造

见 `code/main.py`。我们实现 Chinchilla loss 方程，并在多个算力预算下解出 compute-optimal 的 `(N, D)`。

> See `code/main.py`. We implement the Chinchilla loss equation and solve for compute-optimal `(N, D)` at each of several compute budgets.

### Step 1: Chinchilla loss · 第 1 步：Chinchilla loss

```python
def chinchilla_loss(N, D, A=406.4, B=410.7, alpha=0.34, beta=0.28, E=1.69):
    return A / N ** alpha + B / D ** beta + E
```

在固定 `C = 6ND` 下，把 `L` 画成 `(N, D)` 上的等高线。找出最小值。

> Plot `L` as a contour over `(N, D)` at fixed `C = 6ND`. Find the minimum.

### Step 2: compute-optimal frontier · 第 2 步：compute-optimal 前沿

对从 `1e17` 到 `1e25` FLOPs 的算力预算，在 `6ND = C` 约束下找出最小化 loss 的 `(N, D)`。验证比率 `D/N ≈ 20`。

> For compute budgets from `1e17` to `1e25` FLOPs, find `(N, D)` that minimize loss subject to `6ND = C`. Verify the ratio `D/N ≈ 20`.

### Step 3: over-training cost · 第 3 步：过训练的代价

计算把模型训小 10 倍（最优 N 的 1/10、最优 D 的 10 倍）需要额外付出的 loss。报告换来的推理 FLOP 节省（与 N 成正比）。

> Compute the extra loss you pay to train a 10× smaller model (1/10 of optimal N, 10× the optimal D). Reports the inference FLOP savings (proportional to N) in exchange.

### Step 4: compare to real models · 第 4 步：与真实模型对比

代入 GPT-3、Chinchilla、Llama 3 8B、DeepSeek-V3（激活参数）的已知 `(N, D)` 组合，对比预测 loss 与公开报告的 loss。

> Drop in known `(N, D)` pairs for GPT-3, Chinchilla, Llama 3 8B, DeepSeek-V3 (active params), and compare predicted vs reported loss.

## Use It · 实战用法

你自己大概率不会去训前沿模型。但缩放定律能告诉你：

1. **你的微调数据够不够。** 如果任务数据低于基座模型每参数 20 token，预期会在某个 loss 地板上饱和。
2. **要不要选更大的基座。** 如果预算全都花在推理上，选更小、训得更久的模型。
3. **收益递减点在哪。** 超过 Chinchilla 最优 1000 倍之后，log-loss 的变化就成了噪声。

**2026 年的研究走向：**

- **数据受限区间。** 高质量 token 是有限的（过滤后英语约 5–10 万亿）。前沿预训练正在逼近这个天花板。合成数据、多语言、多模态、以及 RLHF 放大的微调是下一批杠杆。
- **算力乘数技巧。** Muon 优化器、MoE、更好的数据策展——每一个都移动绝对常数，不移动渐近线。
- **RL 的缩放定律。** 开放问题。早期证据显示 RL 样本里也存在幂律，但指数与预训练差别很大。

> You're unlikely to train a frontier model yourself. But scaling laws tell you:
> 1. **Whether your fine-tune has enough data.** If your task-specific data is below 20 tokens per param of the base model, expect saturation at some loss floor.
> 2. **Whether to pick a bigger base model.** If you're spending all your budget on inference, prefer a smaller, longer-trained model.
> 3. **Where the returns diminish.** Beyond 1000× Chinchilla-optimal, log-loss changes become noise.
> **The research trajectory in 2026:**
> - **Data-constrained regime.** The web has a finite number of high-quality tokens (~5–10 trillion English after filtering). Frontier pretraining is approaching this ceiling. Synthetic data, multilingual, multimodal, and RLHF-scaled fine-tuning are the next levers.
> - **Compute-multiplier tricks.** Muon optimizer, MoE, better data curation — each shifts the absolute constants, not the asymptote.
> - **Scaling laws for RL.** Open question. Early evidence suggests power-law in RL samples but with very different exponents than pretraining.

## Ship It · 交付

见 `outputs/skill-training-budget-estimator.md`。这个技能在给定算力预算、部署约束和目标 loss 的前提下，为一个新训练任务挑选 `(N, D, hours, GPU)`。

> See `outputs/skill-training-budget-estimator.md`. The skill picks `(N, D, hours, GPU)` for a new training run given compute budget, deployment constraints, and target loss.

## Exercises · 练习

1. **简单。** 跑 `code/main.py`。打印算力预算 `1e20`、`1e22`、`1e24` 下的 Chinchilla 最优 `(N, D)`，与真实模型表对比。
2. **中等。** 实现 Hoffmann 的 loss-随-算力函数曲线。对 compute-optimal 前沿画出 loss vs `log10(C)`。找出定律预测下一次 cross-entropy 降低 0.1 需要 `>10^28` FLOPs 的位置。
3. **困难。** 在同一数据集上训练 5 个小模型（100K 到 10M 参数），拟合你自己的缩放定律。估计 `α` 和 `E`。你的指数与已发表结果的吻合度如何？

> 1. **Easy.** Run `code/main.py`. Print Chinchilla-optimal `(N, D)` for compute budgets `1e20`, `1e22`, `1e24`. Compare to the real model table.
> 2. **Medium.** Implement the Hoffmann loss-as-function-of-compute curve. Plot loss vs `log10(C)` for the compute-optimal frontier. Identify when the law predicts we'd need `>10^28` FLOPs for the next 0.1 reduction in cross-entropy.
> 3. **Hard.** Fit your own scaling law on 5 tiny models (100K to 10M params) trained on the same dataset. Estimate `α` and `E`. How well do your exponents match published ones?

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Parameters（N，参数量） | 「模型大小」 | 非嵌入权重数量；决定容量。 |
| Tokens（D，token 数） | 「训练数据」 | 看过的训练 token 数；决定参数被利用得多充分。 |
| Compute（C，算力） | 「花掉的 FLOPs」 | 标准 Transformer 约为 `6 × N × D`。 |
| Chinchilla-optimal | 「D/N ≈ 20」 | 使每 FLOP 预训练 loss 最小的比率。 |
| Over-training（过训练） | 「越过 Chinchilla」 | 多花训练 FLOPs 去省推理 FLOPs；D/N >> 20。 |
| Irreducible loss（不可约 loss） | 「地板」 | 缩放定律里的 `E` 项；数据本身的熵。 |
| Emergent capability（涌现能力） | 「规模到了突然出现」 | 常是打分器假象；连续 loss 是平滑的。 |
| Effective compute（有效算力） | 「训练效率乘数」 | 更好的数据 / 优化器 / 架构能放大每个 FLOP 的效用。 |

## Further Reading · 延伸阅读

- [Kaplan et al. (2020). Scaling Laws for Neural Language Models](https://arxiv.org/abs/2001.08361) — 第一篇缩放定律论文；训练不足。
- [Hoffmann et al. (2022). Training Compute-Optimal Large Language Models](https://arxiv.org/abs/2203.15556) — Chinchilla。
- [Schaeffer et al. (2023). Are Emergent Abilities of Large Language Models a Mirage?](https://arxiv.org/abs/2304.15004) — 涌现作为测量假象。
- [Sardana, Frankle (2024). Beyond Chinchilla-Optimal: Accounting for Inference in Language Model Scaling Laws](https://arxiv.org/abs/2401.00448) — 为什么 Llama 的过训练对它的负载是对的。
- [Jordan et al. (2024). Muon: An optimizer for hidden layers in neural networks](https://kellerjordan.github.io/posts/muon/) — 2 倍算力乘数。
