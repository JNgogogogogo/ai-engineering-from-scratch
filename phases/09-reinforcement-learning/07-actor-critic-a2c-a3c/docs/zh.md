# Actor-Critic — A2C and A3C · 演员-评论家：A2C 与 A3C

> REINFORCE 噪声很大。加一个学 `V̂(s)` 的 critic，从回报里减掉它，你就得到一个期望相同、方差低得多的优势（advantage）。这就是演员-评论家（actor-critic）。A2C 同步地跑它；A3C 跨线程跑它。两者是所有现代深度 RL 方法的心智模型。

> REINFORCE is noisy. Add a critic that learns `V̂(s)`, subtract it from the return, and you get an advantage that has the same expectation but far lower variance. That is actor-critic. A2C runs it synchronously; A3C runs it across threads. Both are the mental model for every modern deep-RL method.

**类型：** Build
**语言：** Python
**前置课程：** Phase 9 · 04（TD 学习）、Phase 9 · 06（REINFORCE）
**时间：** ~75 分钟

## The Problem · 问题在哪

原味 REINFORCE 能用，但方差糟糕透顶。蒙特卡洛回报 `G_t` 在不同 episode 之间能摆动 10 倍以上。把这个噪声乘上 `∇ log π` 再平均，得到的梯度估计器要几千个 episode，才能把策略推动 DQN 用少得多的更新就能推到的距离。

方差来自直接使用原始回报。如果减掉一个基线 `b(s_t)`——任何状态的函数，包括学出来的价值——期望不变，方差下降。最好的可行基线是 `V̂(s_t)`。此时乘在 `∇ log π` 上的量就是*优势*（advantage）：

`A(s, a) = G - V̂(s)`

一个动作产出高于平均的回报就是好动作；低于平均就是坏动作。带学习 critic 的 REINFORCE 就是 *actor-critic*。critic 给 actor 一位低方差的老师。2015 年之后的每一个深度策略方法（A2C、A3C、PPO、SAC、IMPALA）都是它。

> Vanilla REINFORCE works, but its variance is terrible. Monte Carlo returns `G_t` can swing over a factor of 10 between episodes. Multiplying that noise by `∇ log π` and averaging produces a gradient estimator that takes thousands of episodes to move the policy the same distance you could move it with far fewer DQN updates.
> The variance comes from using raw returns. If you subtract a baseline `b(s_t)` — any function of state, including a learned value — the expectation is unchanged and the variance drops. The best tractable baseline is `V̂(s_t)`. Now the quantity multiplying `∇ log π` is the *advantage*:
> An action is good if it produced above-average return; bad if below. REINFORCE with a learned critic is *actor-critic*. The critic gives the actor a low-variance teacher. This is every deep-policy method after 2015 (A2C, A3C, PPO, SAC, IMPALA).

## The Concept · 概念

![Actor-critic：策略网络加价值网络，TD 残差作为优势](../assets/actor-critic.svg)

**两个网络，一份合并损失：**

- **Actor** `π_θ(a | s)`：策略。采样它来动作。用策略梯度训练。
- **Critic** `V_φ(s)`：估计从状态出发的期望回报。训练目标是最小化 `(V_φ(s) - target)²`。

**优势。** 两种标准形式：

- *MC 优势：* `A_t = G_t - V_φ(s_t)`。无偏，方差更高。
- *TD 优势：* `A_t = r_{t+1} + γ V_φ(s_{t+1}) - V_φ(s_t)`。有偏（用了 `V_φ`），方差低得多。也叫 *TD 残差* `δ_t`。

**n-step 优势。** 在两者之间插值：

`A_t^{(n)} = r_{t+1} + γ r_{t+2} + … + γ^{n-1} r_{t+n} + γ^n V_φ(s_{t+n}) - V_φ(s_t)`

`n = 1` 是纯 TD。`n = ∞` 是 MC。多数实现里 Atari 用 `n = 5`，MuJoCo 上的 PPO 用 `n = 2048`。

**广义优势估计（GAE）。** Schulman 等人（2016）提出对所有 n-step 优势做指数加权平均：

`A_t^{GAE} = Σ_{l=0}^{∞} (γλ)^l δ_{t+l}`

其中 `λ ∈ [0, 1]`。`λ = 0` 是 TD（低方差、高偏差）。`λ = 1` 是 MC（高方差、无偏）。`λ = 0.95` 是 2026 年的默认值——把偏差/方差这个旋钮拧到你要的位置为止。

**A2C：同步优势演员-评论家。** 在 `N` 个并行环境各收集 `T` 步。给每一步算优势。在合并的 batch 上更新 actor 和 critic。重复。A3C 更简单、更可扩展的兄弟版本。

**A3C：异步优势演员-评论家。** Mnih 等人（2016）。起 `N` 个 worker 线程，各跑一个环境。每个 worker 在自己的 rollout 上局部算梯度，然后异步地应用到共享参数服务器上。不需要回放缓冲区——worker 靠跑不同轨迹来去相关。A3C 证明了用 CPU 也能大规模训练。2026 年，GPU 版 A2C（批量并行环境）占主流，因为 GPU 要大 batch。

**合并损失。**

`L(θ, φ) = -E[ A_t · log π_θ(a_t | s_t) ]  +  c_v · E[(V_φ(s_t) - G_t)²]  -  c_e · E[H(π_θ(·|s_t))]`

三项：策略梯度损失、价值回归、熵奖励。`c_v ~ 0.5`、`c_e ~ 0.01` 是经典起点。

```figure
actor-critic
```

> **Two networks, one shared loss:** **Actor** `π_θ(a | s)`: the policy. Sampled to act. Trained with policy gradient. **Critic** `V_φ(s)`: estimates expected return from state. Trained to minimize `(V_φ(s) - target)²`.
> **The advantage.** *MC advantage:* `A_t = G_t - V_φ(s_t)`. Unbiased, higher variance. *TD advantage:* `A_t = r_{t+1} + γ V_φ(s_{t+1}) - V_φ(s_t)`. Biased (uses `V_φ`), far lower variance. Also called the *TD residual* `δ_t`.
> **Generalized Advantage Estimation (GAE).** `λ = 0` is TD (low variance, high bias). `λ = 1` is MC (high variance, unbiased). `λ = 0.95` is the 2026 default — tune until the bias/variance dial is where you want it.
> **A3C: asynchronous advantage actor-critic.** Spawn `N` worker threads, each running an env. Each worker computes gradients locally on its own rollout, then asynchronously applies them to a shared parameter server. No replay buffer needed — workers decorrelate by running different trajectories.
> Three terms: policy-gradient loss, value regression, entropy bonus. `c_v ~ 0.5`, `c_e ~ 0.01` are canonical starting points.

## Build It · 动手造

### Step 1: a critic · 一个 critic

线性 critic `V_φ(s) = w · features(s)`，用 MSE 更新：

```python
def critic_update(w, x, target, lr):
    v_hat = dot(w, x)
    err = target - v_hat
    for j in range(len(w)):
        w[j] += lr * err * x[j]
    return v_hat
```

表格型环境上 critic 几百个 episode 就收敛。Atari 上把线性 critic 换成共享 CNN 主干 + 价值头。

> On a tabular env the critic converges in a few hundred episodes. On Atari, replace the linear critic with a shared CNN trunk + value head.

### Step 2: n-step advantage · n-step 优势

给定长度为 `T` 的 rollout 和自举的末端 `V(s_T)`：

```python
def compute_advantages(rewards, values, gamma=0.99, lam=0.95, last_value=0.0):
    advantages = [0.0] * len(rewards)
    gae = 0.0
    for t in reversed(range(len(rewards))):
        next_v = values[t + 1] if t + 1 < len(values) else last_value
        delta = rewards[t] + gamma * next_v - values[t]
        gae = delta + gamma * lam * gae
        advantages[t] = gae
    returns = [a + v for a, v in zip(advantages, values)]
    return advantages, returns
```

`returns` 是 critic 的目标。`advantages` 是乘在 `∇ log π` 上的量。

> `returns` is the critic target. `advantages` is what multiplies `∇ log π`.

### Step 3: combined update · 合并更新

```python
for step_i, (x, a, _r, probs) in enumerate(traj):
    adv = advantages[step_i]
    target_v = returns[step_i]

    # critic
    critic_update(w, x, target_v, lr_v)

    # actor
    for i in range(N_ACTIONS):
        grad_logpi = (1.0 if i == a else 0.0) - probs[i]
        for j in range(N_FEAT):
            theta[i][j] += lr_a * adv * grad_logpi * x[j]
```

On-policy，每次更新一个 rollout，actor 和 critic 各用各的学习率。

> On-policy, one rollout per update, separate learning rates for actor and critic.

### Step 4: parallelization (A3C vs A2C) · 并行化（A3C vs A2C）

- **A3C：** 起 `N` 个线程，各跑各的环境和各跑各的前向传播。周期性地把梯度更新推给共享 master。master 上不加锁——数据竞争没关系，只是多点噪声。
- **A2C：** 单进程里跑 `N` 个环境实例，把观测堆成 `[N, obs_dim]` 的 batch，批量前向、批量反向。GPU 利用率更高、确定性强、更好推理。2026 年的默认选择。

我们的玩具代码为了清晰是单线程的；改写成批量 A2C 只需三行 numpy。

> **A3C:** spin up `N` threads. Each runs its own env and its own forward pass. Periodically push gradient updates to a shared master. No locks on the master — races are ok, they just add noise.
> **A2C:** run `N` env instances in a single process, stack observations into a `[N, obs_dim]` batch, batched forward pass, batched backward pass. Higher GPU utilization, deterministic, easier to reason about. The default in 2026.
> Our toy code is single-threaded for clarity; rewriting to batched A2C is three lines of numpy.

## Pitfalls · 常见的坑

- **critic 还没热身就上 actor 梯度。** critic 随机时它的基线没有信息量，你是在纯噪声上训练。先把 critic 预热几百步再打开策略梯度，或者用很小的 actor 学习率。
- **优势归一化。** 每个 batch 把优势归一化到零均值/单位标准差。以近乎零的成本极大稳定训练。
- **共享主干。** 图像输入上让 actor 和 critic 共享特征提取器，头分开。共享特征在两份损失上搭便车。
- **On-policy 契约。** A2C 的数据只复用一次更新。多了梯度就有偏（PPO 加的就是重要性采样修正）。
- **熵坍缩。** 没有 `c_e > 0`，策略几百次更新内就变得近乎确定，停止探索。
- **奖励尺度。** 优势的量级取决于奖励尺度。归一化奖励（比如除以滑动标准差），让梯度量级跨任务保持一致。

> **Critic bias before actor gradient.** If the critic is random, its baseline is uninformative and you are training on pure noise. Warm up the critic for a few hundred steps before turning on the policy gradient, or use a slow actor learning rate.
> **Advantage normalization.** Normalize advantages to zero-mean/unit-std per batch. Stabilizes training massively at near-zero cost.
> **On-policy contract.** A2C reuses data for exactly one update. More and your gradient is biased (importance-sampling correction is what PPO adds).
> **Entropy collapse.** Without `c_e > 0`, policy becomes near-deterministic in a few hundred updates and stops exploring.

## Use It · 实战用法

2026 年 A2C/A3C 很少是最终选择，但它们是后来一切方法所精化的架构：

| 方法 | 与 A2C 的关系 |
|--------|----------------|
| PPO | A2C + 裁剪的重要性比率，可做多 epoch 更新 |
| IMPALA | A3C + V-trace 异策略修正 |
| SAC（Phase 9 · 07） | 异策略 A2C，带软价值 critic（下一课） |
| GRPO（Phase 9 · 12） | 去掉 critic 的 A2C——组相对优势 |
| DPO | A2C 坍缩成偏好排序损失，无需采样 |
| AlphaStar / OpenAI Five | A2C + 联赛训练 + 模仿预训练 |

2026 年的论文里看到「advantage」，想到的就是 actor-critic。

> A2C/A3C are rarely the final choice in 2026 but they are the architecture everything later refines...
> If you see "advantage" in a 2026 paper, think actor-critic.

## Ship It · 交付

保存为 `outputs/skill-actor-critic-trainer.md`：

```markdown
---
name: actor-critic-trainer
description: Produce an A2C / A3C / GAE configuration for a given environment, with advantage estimation and loss weights specified.
version: 1.0.0
phase: 9
lesson: 7
tags: [rl, actor-critic, gae]
---

Given an environment and compute budget, output:

1. Parallelism. A2C (GPU batched) vs A3C (CPU async) and the number of workers.
2. Rollout length T. Steps per env per update.
3. Advantage estimator. n-step or GAE(λ); specify λ.
4. Loss weights. `c_v` (value), `c_e` (entropy), gradient clip.
5. Learning rates. Actor and critic (separate if using).

Refuse single-worker A2C on environments with horizon > 1000 (too on-policy, too slow). Refuse to ship without advantage normalization. Flag any run with `c_e = 0` and observed entropy < 0.1 as entropy-collapsed.
```

> Save as `outputs/skill-actor-critic-trainer.md`.

## Exercises · 练习

1. **简单。** 在 4×4 GridWorld 上用 MC 优势（`G_t - V(s_t)`）训练 actor-critic。对比第 06 课带滑动平均基线的 REINFORCE 的样本效率。
2. **中等。** 换成 TD 残差优势（`r + γ V(s') - V(s)`）。测一测优势批次的方差。降了多少？
3. **困难。** 实现 GAE(λ)。扫描 `λ ∈ {0, 0.5, 0.9, 0.95, 1.0}`。画出最终回报与样本效率。这个任务的偏差/方差甜点位在哪？

> **Easy.** Train actor-critic with MC advantage (`G_t - V(s_t)`) on 4×4 GridWorld. Compare sample efficiency to REINFORCE-with-running-mean-baseline from Lesson 06.
> **Medium.** Switch to TD-residual advantage (`r + γ V(s') - V(s)`). Measure variance of the advantage batches. By how much does it drop?
> **Hard.** Implement GAE(λ). Sweep `λ ∈ {0, 0.5, 0.9, 0.95, 1.0}`. Plot final return vs sample efficiency. Where is the bias/variance sweet spot for this task?

## Key Terms · 术语表

| Term | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Actor | "策略网络" | `π_θ(a\|s)`，由策略梯度更新。 |
| Critic | "价值网络" | `V_φ(s)`，对回报 / TD 目标做 MSE 回归来更新。 |
| Advantage | "比平均好多少" | `A(s, a) = Q(s, a) - V(s)` 或其估计量。乘在 `∇ log π` 上的系数。 |
| TD residual | "δ" | `δ_t = r + γ V(s') - V(s)`；单步优势估计。 |
| GAE | "插值旋钮" | n-step 优势的指数加权和，由 `λ` 参数化。 |
| A2C | "同步 actor-critic" | 跨环境批量并行；每个 rollout 一次梯度步。 |
| A3C | "异步 actor-critic" | worker 线程把梯度推给共享参数服务器。原始论文的做法；2026 年已较少用。 |
| Bootstrap | "在截断处用 V" | 截断 rollout，加上 `γ^n V(s_{t+n})` 把和闭合。 |

## Further Reading · 延伸阅读

- [Mnih et al. (2016). Asynchronous Methods for Deep Reinforcement Learning](https://arxiv.org/abs/1602.01783) —— A3C，异步 actor-critic 的原始论文。
- [Schulman et al. (2016). High-Dimensional Continuous Control Using Generalized Advantage Estimation](https://arxiv.org/abs/1506.02438) —— GAE。
- [Sutton & Barto (2018). Ch. 13 — Actor-Critic Methods](http://incompleteideas.net/book/RLbook2020.pdf) —— 基础；critic 是神经网络时，配合第 9 章（函数逼近）一起读。
- [Espeholt et al. (2018). IMPALA](https://arxiv.org/abs/1802.01561) —— 可扩展的分布式 actor-critic，带 V-trace 异策略修正。
- [OpenAI Baselines / Stable-Baselines3](https://stable-baselines3.readthedocs.io/) —— 值得一读的生产级 A2C/PPO 实现。
- [Konda & Tsitsiklis (2000). Actor-Critic Algorithms](https://papers.nips.cc/paper/1786-actor-critic-algorithms) —— 双时间尺度 actor-critic 分解的奠基性收敛结果。
