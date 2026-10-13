# Proximal Policy Optimization (PPO) · 近端策略优化（PPO）

> A2C 每份 rollout 用一次更新就扔掉。PPO 把策略梯度包进一个带裁剪的重要性比率里，让你能在同一份数据上跑 10 个以上的 epoch 而策略不炸。Schulman 等人（2017）。2026 年的今天仍是默认的策略梯度算法。

> A2C throws away each rollout after one update. PPO wraps the policy gradient in a clipped importance ratio so you can do 10+ epochs on the same data without the policy exploding. Schulman et al. (2017). Still the default policy-gradient algorithm in 2026.

**类型：** Build
**语言：** Python
**前置课程：** Phase 9 · 06（REINFORCE）、Phase 9 · 07（Actor-Critic）
**时间：** ~75 分钟

## The Problem · 问题在哪

A2C（第 07 课）是 on-policy 的：梯度 `E_{π_θ}[A · ∇ log π_θ]` 要求数据采样自*当前*的 `π_θ`。做一次更新，`π_θ` 就变了；你刚用的数据马上变成 off-policy。复用它，梯度就有偏。

Rollout 很贵。在 Atari 上，一次 rollout 跨 8 个环境 × 128 步 = 1024 条转移，外加十几秒的环境时间。走完一步梯度就扔掉太浪费。

信任域策略优化（TRPO，Schulman 2015）是第一个修法：约束每次更新，让新旧策略之间的 KL 散度保持在 `δ` 以下。理论干净，但每次更新都要解一次共轭梯度。2026 年没人在跑 TRPO。

PPO（Schulman 等人 2017）用一个简单的裁剪目标代替硬性信任域约束。多一行代码。每份 rollout 跑十个 epoch。不用共轭梯度。理论保证够用。九年过去，从 MuJoCo 到 RLHF，它仍然是默认的策略梯度算法。

> A2C (Lesson 07) is on-policy: the gradient `E_{π_θ}[A · ∇ log π_θ]` requires data sampled from the *current* `π_θ`. Take one update, and `π_θ` changes; the data you used is now off-policy. Re-use it and your gradient is biased.
> Rollouts are expensive. On Atari, one rollout across 8 envs × 128 steps = 1024 transitions and a dozen seconds of environment time. Throwing that away after one gradient step is wasteful.
> Trust Region Policy Optimization (TRPO, Schulman 2015) was the first fix: constrain each update so the KL divergence between old and new policy stays below `δ`. Theoretically clean, but requires a conjugate-gradient solve per update. Nobody runs TRPO in 2026.
> PPO (Schulman et al. 2017) replaces the hard trust-region constraint with a simple clipped objective. One extra line of code. Ten epochs per rollout. No conjugate gradients. Good-enough theoretical guarantees. Nine years later it is still the default policy-gradient algorithm for everything from MuJoCo to RLHF.

## The Concept · 概念

![PPO 裁剪代理目标：比率在 1 ± ε 处被裁剪](../assets/ppo.svg)

**重要性比率（importance ratio）。**

`r_t(θ) = π_θ(a_t | s_t) / π_{θ_old}(a_t | s_t)`

这是新策略相对于采集数据那个策略的似然比。`r_t = 1` 表示没变。`r_t = 2` 表示新策略取 `a_t` 的可能性是旧策略的两倍。

**裁剪代理目标（clipped surrogate）。**

`L^{CLIP}(θ) = E_t [ min( r_t(θ) A_t, clip(r_t(θ), 1-ε, 1+ε) A_t ) ]`

两项：

- 如果优势 `A_t > 0` 且比率想涨过 `1 + ε`，裁剪会把梯度压平——别把一个好动作推到比旧概率高出 `+ε` 还多。
- 如果优势 `A_t < 0` 且比率想越过 `1 - ε`（意味着相对其被裁剪的降幅，我们反而会让坏动作更容易出现），裁剪会封顶梯度——别把坏动作压到 `-ε` 以下。

`min` 负责另一个方向：如果比率已经朝*有利*方向移动，你仍然拿得到梯度（不会在会伤害你的那一侧裁剪）。

典型 `ε = 0.2`。把目标函数对 `r_t` 画出来：一个分段线性函数，「好的一侧」是平屋顶，「坏的一侧」是平地板。

**完整的 PPO 损失。**

`L(θ, φ) = L^{CLIP}(θ) - c_v · (V_φ(s_t) - V_t^{target})² + c_e · H(π_θ(·|s_t))`

和 A2C 相同的 actor-critic 结构。三个系数，通常 `c_v = 0.5`、`c_e = 0.01`、`ε = 0.2`。

**训练回路。**

1. 在 `N` 个并行环境里各采 `T` 步，共 `N × T` 条转移。
2. 计算优势（GAE），冻结为常数。
3. 把 `π_{θ_old}` 冻结为当前 `π_θ` 的快照。
4. 跑 `K` 个 epoch，对每个 minibatch 的 `(s, a, A, V_target, log π_old(a|s))`：
   - 计算 `r_t(θ) = exp(log π_θ(a|s) - log π_old(a|s))`。
   - 应用 `L^{CLIP}` + 价值损失 + 熵。
   - 走一步梯度。
5. 丢掉 rollout。回到第 1 步。

`K = 10`、minibatch 64 是标准超参数组合。PPO 很皮实：数值在 ±50% 范围内几乎无关紧要。

**KL 惩罚变体。** 原论文提出过另一种方案，用自适应 KL 惩罚：`L = L^{PG} - β · KL(π_θ || π_old)`，`β` 根据观测到的 KL 调整。裁剪版成了主流；KL 变体在 RLHF 里活了下来（在那里，对参考策略的 KL 本来就是永远想要的独立约束）。

```figure
ppo-clip
```

> **The importance ratio.** `r_t(θ) = π_θ(a_t | s_t) / π_{θ_old}(a_t | s_t)` — the likelihood ratio of the new policy vs the policy that collected the data. `r_t = 1` means no change. `r_t = 2` means the new policy is twice as likely to take `a_t` as the old.
> **The clipped surrogate.** If the advantage `A_t > 0` and the ratio tries to grow past `1 + ε`, the clip flattens the gradient — don't push a good action further than `+ε` above old probability. If the advantage `A_t < 0` and the ratio tries to grow past `1 - ε`... the clip caps the gradient — don't push a bad action below `-ε`.
> The `min` handles the other direction: if the ratio has moved in the *beneficial* direction, you still get the gradient (no clipping on the side that would hurt you).
> `K = 10` and minibatches of 64 is a standard hyperparameter set. PPO is robust: the exact numbers rarely matter within ±50%.
> **KL-penalty variant.** The clipping version became dominant; the KL variant survives in RLHF (where KL to the reference policy is a separate constraint you always want anyway).

## Build It · 动手造

### Step 1: capture `log π_old(a | s)` at rollout time · 在 rollout 时抓下 `log π_old(a | s)`

```python
for step in range(T):
    probs = softmax(logits(theta, state_features(s)))
    a = sample(probs, rng)
    s_next, r, done = env.step(s, a)
    buffer.append({
        "s": s, "a": a, "r": r, "done": done,
        "v_old": value(w, state_features(s)),
        "log_pi_old": log(probs[a] + 1e-12),
    })
    s = s_next
```

快照只在 rollout 时拍一次。更新 epoch 期间不变。

> The snapshot is taken once, at rollout time. It does not change during the update epochs.

### Step 2: compute GAE advantages (Lesson 07) · 计算 GAE 优势（第 07 课）

和 A2C 一样。在 batch 上归一化。

> Same as A2C. Normalize across the batch.

### Step 3: clipped surrogate update · 裁剪代理目标更新

```python
for _ in range(K_EPOCHS):
    for mb in minibatches(buffer, size=64):
        for rec in mb:
            x = state_features(rec["s"])
            probs = softmax(logits(theta, x))
            logp = log(probs[rec["a"]] + 1e-12)
            ratio = exp(logp - rec["log_pi_old"])
            adv = rec["advantage"]
            surrogate = min(
                ratio * adv,
                clamp(ratio, 1 - EPS, 1 + EPS) * adv,
            )
            # backprop -surrogate, add value loss, subtract entropy
            grad_logpi = onehot(rec["a"]) - probs
            if (adv > 0 and ratio >= 1 + EPS) or (adv < 0 and ratio <= 1 - EPS):
                pg_grad = 0.0  # clipped
            else:
                pg_grad = ratio * adv
            for i in range(N_ACTIONS):
                for j in range(N_FEAT):
                    theta[i][j] += LR * pg_grad * grad_logpi[i] * x[j]
```

「裁剪 → 零梯度」这个模式是 PPO 的心脏。如果新策略已经朝有利方向漂得太远，更新就停下来。

> The "clipped → zero gradient" pattern is the heart of PPO. If the new policy has already drifted too far in the beneficial direction, the update stops.

### Step 4: value and entropy · 价值与熵

给 critic 目标加标准 MSE，给 actor 加熵奖励，与 A2C 相同。

> Add standard MSE to the critic target and an entropy bonus on the actor, same as A2C.

### Step 5: diagnostics · 诊断指标

每次更新盯三件事：

- **平均 KL** `E[log π_old - log π_θ]`。应保持在 `[0, 0.02]`。冲过 `0.1` 就调小 `K_EPOCHS` 或 `LR`。
- **裁剪比例（clip fraction）**——比率落在 `[1-ε, 1+ε]` 之外的样本占比。应在 `~0.1-0.3`。若 `~0`，裁剪从未触发 → 调大 `LR` 或 `K_EPOCHS`。若 `~0.5+`，你在对 rollout 过拟合 → 调小它们。
- **解释方差（explained variance）** `1 - Var(V_target - V_pred) / Var(V_target)`。critic 质量指标。应随 critic 学习爬向 1。

> **Mean KL** `E[log π_old - log π_θ]`. Should stay in `[0, 0.02]`. If it blows past `0.1`, reduce `K_EPOCHS` or `LR`.
> **Clip fraction** — the fraction of samples whose ratio lies outside `[1-ε, 1+ε]`. Should be `~0.1-0.3`. If `~0`, the clip never triggers → raise `LR` or `K_EPOCHS`. If `~0.5+`, you are over-fitting the rollout → lower them.
> **Explained variance** `1 - Var(V_target - V_pred) / Var(V_target)`. Critic quality metric. Should climb toward 1 as the critic learns.

## Pitfalls · 常见的坑

- **裁剪系数没调好。** `ε = 0.2` 是事实标准。调到 `0.1` 更新太畏缩；`0.3+` 招致不稳定。
- **epoch 太多。** `K > 20` 经常让训练失稳，因为策略漂得离 `π_old` 太远。限制 epoch 数，大网络尤其如此。
- **不做奖励归一化。** 大奖励尺度会吃掉裁剪范围。算优势之前先归一化奖励（滑动标准差）。
- **忘了优势归一化。** 每 batch 零均值/单位标准差归一化是标准操作。跳过它会在多数基准上毁掉 PPO。
- **学习率不衰减。** PPO 受益于线性 LR 衰减到零。恒定 LR 往往更差。
- **重要性比率数学错误。** 为了数值稳定，永远用 `exp(log_new - log_old)`，不要 `new / old`。
- **梯度符号写反。** 最大化代理目标 = *最小化* `-L^{CLIP}`。符号写反是最常见的 PPO bug。

> **Clip coefficient mistuned.** `ε = 0.2` is the de-facto standard. Going to `0.1` makes updates too timid; `0.3+` invites instability.
> **Too many epochs.** `K > 20` routinely destabilizes because the policy drifts far from `π_old`. Cap epochs, especially for large networks.
> **Forgetting advantage normalization.** Per-batch zero-mean/unit-std normalization is standard. Skipping it wrecks PPO on most benchmarks.
> **Importance ratio math errors.** Always `exp(log_new - log_old)` for numerical stability, not `new / old`.
> **Wrong gradient sign.** Maximize the surrogate = *minimize* `-L^{CLIP}`. A flipped sign is the most common PPO bug.

## Use It · 实战用法

PPO 是 2026 年横跨出奇多领域的默认 RL 算法：

| 使用场景 | PPO 变体 |
|----------|-------------|
| MuJoCo / 机器人控制 | 高斯策略 PPO，GAE(0.95) |
| Atari / 离散游戏 | 类别分布策略 PPO，128 步滚动 rollout |
| LLM 的 RLHF | 对参考模型加 KL 惩罚的 PPO，奖励来自回应末尾的 RM |
| 大规模游戏智能体 | IMPALA + PPO（AlphaStar、OpenAI Five） |
| 推理 LLM | GRPO（第 12 课）——无 critic 的 PPO 变体 |
| 只有偏好数据 | DPO——PPO+KL 的闭式坍缩，无需在线采样 |

PPO 的*损失形状*——裁剪代理目标 + 价值 + 熵——是 DPO、GRPO 以及几乎每条 RLHF 流水线的脚手架。

> PPO is 2026's default RL algorithm across a surprising number of domains...
> The PPO *loss shape* — clipped surrogate + value + entropy — is the scaffolding for DPO, GRPO, and nearly every RLHF pipeline.

## Ship It · 交付

保存为 `outputs/skill-ppo-trainer.md`：

```markdown
---
name: ppo-trainer
description: Produce a PPO training config and a diagnostic plan for a given environment.
version: 1.0.0
phase: 9
lesson: 8
tags: [rl, ppo, policy-gradient]
---

Given an environment and training budget, output:

1. Rollout size. `N` envs × `T` steps.
2. Update schedule. `K` epochs, minibatch size, LR schedule.
3. Surrogate params. `ε` (clip), `c_v`, `c_e`, advantage normalization on.
4. Advantage. GAE(`λ`) with explicit `γ` and `λ`.
5. Diagnostics plan. KL, clip fraction, explained variance thresholds with alerts.

Refuse `K > 30` or `ε > 0.3` (unsafe trust region). Refuse any PPO run without advantage normalization or KL/clip monitoring. Flag clip fraction sustained above 0.4 as drift.
```

> Save as `outputs/skill-ppo-trainer.md`.

## Exercises · 练习

1. **简单。** 在 4×4 GridWorld 上用 `ε=0.2, K=4` 跑 PPO。在相同环境步数下与 A2C（每 rollout 一个 epoch）对比样本效率。
2. **中等。** 扫描 `K ∈ {1, 4, 10, 30}`。画出回报对环境步数的曲线，并跟踪每次更新的平均 KL。这个任务上 `K` 多大时 KL 会爆炸？
3. **困难。** 把裁剪代理目标换成自适应 KL 惩罚（`KL > 2·target` 时 `β` 翻倍，`KL < target/2` 时减半）。对比最终回报、稳定性和「无裁剪性」。

> **Easy.** Run PPO on 4×4 GridWorld with `ε=0.2, K=4`. Compare sample efficiency to A2C (one epoch per rollout) at matched env steps.
> **Medium.** Sweep `K ∈ {1, 4, 10, 30}`. Plot return vs env steps and track mean KL per update. At what `K` does KL explode on this task?
> **Hard.** Replace the clipped surrogate with an adaptive KL penalty (`β` doubled if `KL > 2·target`, halved if `KL < target/2`). Compare final return, stability, and clip-free-ness.

## Key Terms · 术语表

| Term | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Importance ratio | "r_t(θ)" | `π_θ(a\|s) / π_old(a\|s)`；相对采集数据策略的偏离。 |
| Clipped surrogate | "PPO 的主技巧" | `min(r·A, clip(r, 1-ε, 1+ε)·A)`；有利一侧越过裁剪后梯度变平。 |
| Trust region | "TRPO / PPO 的本意" | 限制每次更新的 KL，保证单调改进。 |
| KL penalty | "软信任域" | PPO 的另一种形式：`L - β · KL(π_θ \|\| π_old)`。自适应 `β`。 |
| Clip fraction | "裁剪触发频率" | 诊断指标——应在 0.1-0.3；超出区间就是没调好。 |
| Multi-epoch training | "数据复用" | 每份 rollout 跑 K 个 epoch；用方差换样本效率。 |
| On-policy-ish | "基本 on-policy" | PPO 名义上 on-policy，但 K>1 个 epoch 会安全地使用略微 off-policy 的数据。 |
| PPO-KL | "另一个 PPO" | KL 惩罚变体；用在 RLHF 里，因为对参考策略的 KL 本来就是一个约束。 |

## Further Reading · 延伸阅读

- [Schulman et al. (2017). Proximal Policy Optimization Algorithms](https://arxiv.org/abs/1707.06347) —— 那篇论文。
- [Schulman et al. (2015). Trust Region Policy Optimization](https://arxiv.org/abs/1502.05477) —— TRPO，PPO 的前身。
- [Andrychowicz et al. (2021). What Matters In On-Policy RL? A Large-Scale Empirical Study](https://arxiv.org/abs/2006.05990) —— 每个 PPO 超参数都被消融过。
- [Ouyang et al. (2022). Training language models to follow instructions with human feedback](https://arxiv.org/abs/2203.02155) —— InstructGPT；RLHF 里的 PPO 配方。
- [OpenAI Spinning Up — PPO](https://spinningup.openai.com/en/latest/algorithms/ppo.html) —— 干净现代的讲解，配 PyTorch。
- [CleanRL PPO implementation](https://github.com/vwxyzjn/cleanrl) —— 许多论文使用的单文件参考 PPO。
- [Hugging Face TRL — PPOTrainer](https://huggingface.co/docs/trl/main/en/ppo_trainer) —— 语言模型上 PPO 的生产配方；配合第 09 课（RLHF）阅读。
- [Engstrom et al. (2020). Implementation Matters in Deep Policy Gradients](https://arxiv.org/abs/2005.12729) —— 「37 个代码级优化」那篇；哪些 PPO 技巧是承重墙，哪些只是民间传说。
