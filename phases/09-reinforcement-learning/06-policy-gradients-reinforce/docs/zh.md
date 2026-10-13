# Policy Gradient — REINFORCE from Scratch · 策略梯度——从零实现 REINFORCE

> 别再估计价值了。直接把策略参数化，算出期望回报的梯度，往坡上走。Williams（1992）用一个定理把它写完。PPO、GRPO 和每一个 LLM RL 训练回路都因它而存在。

> Stop estimating value. Parameterize the policy directly, compute the gradient of expected return, step uphill. Williams (1992) wrote it in one theorem. It is why PPO, GRPO, and every LLM RL loop exist.

**类型：** Build
**语言：** Python
**前置课程：** Phase 3 · 03（反向传播）、Phase 9 · 03（蒙特卡洛）、Phase 9 · 04（TD 学习）
**时间：** ~75 分钟

## The Problem · 问题在哪

Q-learning 和 DQN 参数化的是*价值*函数，动作靠 `argmax Q` 来挑。离散动作加离散状态时没问题。动作连续时会崩（对 10 维力矩做 `argmax`？），想要随机策略时也会崩（`argmax` 天生就是确定性的）。

策略梯度参数化的则是*策略*本身。`π_θ(a | s)` 是一个输出动作分布的神经网络。从分布里采样来动作。算期望回报对 `θ` 的梯度。往坡上走。没有 `argmax`。没有 Bellman 递归。就是对 `J(θ) = E_{π_θ}[G]` 做梯度上升。

REINFORCE 定理（Williams 1992）告诉你这个梯度算得出来：`∇J(θ) = E_π[ G · ∇_θ log π_θ(a | s) ]`。跑一个 episode。算回报。在每一步乘上 `∇ log π_θ(a | s)`。取平均。梯度上升。完事。

2026 年的每一个 LLM-RL 算法——PPO、DPO、GRPO——都是 REINFORCE 的改良。把它练到手指有记忆，是本阶段其余课程的前置，也是 Phase 10 · 07（RLHF 实现）和 Phase 10 · 08（DPO）的前置。

> Q-learning and DQN parameterize the *value* function. You pick actions by `argmax Q`. It breaks when actions are continuous (which `argmax` over a 10-dimensional torque?) or when you want a stochastic policy (`argmax` is deterministic by construction).
> Policy gradients parameterize the *policy* instead. `π_θ(a | s)` is a neural net that outputs a distribution over actions. Sample from it to act. Compute the gradient of expected return with respect to `θ`. Step uphill. No `argmax`. No Bellman recursion. Just gradient ascent on `J(θ) = E_{π_θ}[G]`.
> The REINFORCE theorem (Williams 1992) tells you this gradient is computable: `∇J(θ) = E_π[ G · ∇_θ log π_θ(a | s) ]`. Run an episode. Compute the return. Multiply by `∇ log π_θ(a | s)` at every step. Average. Gradient-ascent. Done.
> Every LLM-RL algorithm in 2026 — PPO, DPO, GRPO — is a refinement of REINFORCE. Understanding it in your fingers is the prerequisite for the rest of this phase, and for Phase 10 · 07 (RLHF implementation) and Phase 10 · 08 (DPO).

## The Concept · 概念

![策略梯度：softmax 策略、log-π 梯度、按回报加权的更新](../assets/policy-gradient.svg)

**策略梯度定理。** 对任何由 `θ` 参数化的策略 `π_θ`：

`∇J(θ) = E_{τ ~ π_θ}[ Σ_{t=0}^{T} G_t · ∇_θ log π_θ(a_t | s_t) ]`

其中 `G_t = Σ_{k=t}^{T} γ^{k-t} r_{k+1}` 是从第 `t` 步起的折扣回报。期望取自 `π_θ` 采样出的完整轨迹 `τ`。

**证明很短。** 在期望里面对 `J(θ) = Σ_τ P(τ; θ) G(τ)` 求导。用 `∇P(τ; θ) = P(τ; θ) ∇ log P(τ; θ)`（log-derivative 技巧）。把 `log P(τ; θ)` 分解成 `Σ log π_θ(a_t | s_t)` 加上不依赖 θ 的环境项。环境项消掉。两行代数就得到定理。

**降方差技巧。** 原味 REINFORCE 的方差是谋杀级的——回报有噪声，`∇ log π` 有噪声，两者的乘积噪声极大。两个标准修法：

1. **基线减除（baseline subtraction）。** 把 `G_t` 换成 `G_t - b(s_t)`，其中 `b(s_t)` 是任何不依赖 `a_t` 的基线。无偏，因为 `E[b(s_t) · ∇ log π(a_t | s_t)] = 0`。典型选择：用 critic 学出 `b(s_t) = V̂(s_t)` → 这就是 actor-critic（第 07 课）。
2. **Reward-to-go。** 把 `Σ_t G_t · ∇ log π_θ(a_t | s_t)` 换成 `Σ_t G_t^{from t} · ∇ log π_θ(a_t | s_t)`。对给定的动作来说只有未来回报才重要——过去的奖励只贡献零均值噪声。

合起来得到：

`∇J ≈ (1/N) Σ_{i=1}^{N} Σ_{t=0}^{T_i} [ G_t^{(i)} - V̂(s_t^{(i)}) ] · ∇_θ log π_θ(a_t^{(i)} | s_t^{(i)})`

这就是带基线的 REINFORCE——A2C（第 07 课）和 PPO（第 08 课）的直系祖先。

**Softmax 策略参数化。** 离散动作的标准选择：

`π_θ(a | s) = exp(f_θ(s, a)) / Σ_{a'} exp(f_θ(s, a'))`

其中 `f_θ` 是任意一个给每个动作输出分数的神经网络。梯度有一个干净的形式：

`∇_θ log π_θ(a | s) = ∇_θ f_θ(s, a) - Σ_{a'} π_θ(a' | s) ∇_θ f_θ(s, a')`

即：所取动作的分数减去它在策略下的期望值。

**连续动作用高斯策略。** `π_θ(a | s) = N(μ_θ(s), σ_θ(s))`。`∇ log N(a; μ, σ)` 有闭式解。Phase 9 · 07 的 SAC 需要的全部就这些。

```figure
policy-gradient-landscape
```

> **The policy gradient theorem.** `∇J(θ) = E_{τ ~ π_θ}[ Σ_{t=0}^{T} G_t · ∇_θ log π_θ(a_t | s_t) ]` where `G_t = Σ_{k=t}^{T} γ^{k-t} r_{k+1}` is the discounted return from step `t`. The expectation is over full trajectories `τ` sampled from `π_θ`.
> **The proof is short.** Use `∇P(τ; θ) = P(τ; θ) ∇ log P(τ; θ)` (the log-derivative trick)... The environment terms vanish. Two lines of algebra give you the theorem.
> **Baseline subtraction.** Replace `G_t` with `G_t - b(s_t)` for any baseline `b(s_t)` that does not depend on `a_t`. Unbiased because `E[b(s_t) · ∇ log π(a_t | s_t)] = 0`. **Reward-to-go.** Only future returns matter for a given action — past rewards contribute zero-mean noise.
> **Softmax policy parameterization.** `∇_θ log π_θ(a | s) = ∇_θ f_θ(s, a) - Σ_{a'} π_θ(a' | s) ∇_θ f_θ(s, a')` — i.e., score of the taken action minus its expected value under the policy.

## Build It · 动手造

### Step 1: softmax policy network · softmax 策略网络

```python
def policy_logits(theta, state_features):
    return [dot(theta[a], state_features) for a in range(N_ACTIONS)]

def softmax(logits):
    m = max(logits)
    exps = [exp(l - m) for l in logits]
    Z = sum(exps)
    return [e / Z for e in exps]
```

表格型环境用线性策略（每个动作一个权重向量）。Atari 就换上 CNN，保留 softmax 头。

> Use a linear policy (one weight vector per action) for a tabular env. For Atari, swap in a CNN and keep the softmax head.

### Step 2: sampling and log-probability · 采样与对数概率

```python
def sample_action(probs, rng):
    x = rng.random()
    cum = 0
    for a, p in enumerate(probs):
        cum += p
        if x <= cum:
            return a
    return len(probs) - 1

def log_prob(probs, a):
    return log(probs[a] + 1e-12)
```

### Step 3: rollout with log-probs captured · 采集轨迹并记录 log 概率

```python
def rollout(theta, env, rng, gamma):
    trajectory = []
    s = env.reset()
    while not done:
        logits = policy_logits(theta, s)
        probs = softmax(logits)
        a = sample_action(probs, rng)
        s_next, r, done = env.step(s, a)
        trajectory.append((s, a, r, probs))
        s = s_next
    return trajectory
```

### Step 4: REINFORCE update · REINFORCE 更新

```python
def reinforce_step(theta, trajectory, gamma, lr, baseline=0.0):
    returns = compute_returns(trajectory, gamma)
    for (s, a, _, probs), G in zip(trajectory, returns):
        advantage = G - baseline
        grad_log_pi_a = [-p for p in probs]
        grad_log_pi_a[a] += 1.0
        for i in range(N_ACTIONS):
            for j in range(len(s)):
                theta[i][j] += lr * advantage * grad_log_pi_a[i] * s[j]
```

梯度 `∇ log π(a|s) = e_a - π(·|s)`（`a` 的 onehot 减去概率向量）是 softmax 策略梯度的心脏。把它烧进肌肉记忆。

> The gradient `∇ log π(a|s) = e_a - π(·|s)` (onehot of `a` minus probabilities) is the heart of softmax policy gradients. Burn it into muscle memory.

### Step 5: baselines · 基线

对最近若干 episode 的 `G` 取滑动平均，这点方差缩减就足以让 4×4 GridWorld 跑起来；大约 500 个 episode 收敛。把基线升级成学出来的 `V̂(s)`，就得到了 actor-critic。

> A running mean of `G` over recent episodes is enough variance reduction to get a 4×4 GridWorld running; it takes ~500 episodes to converge. Upgrade the baseline to a learned `V̂(s)` and you get actor-critic.

## Pitfalls · 常见的坑

- **梯度爆炸。** 回报可能巨大。乘 `∇ log π` 之前，永远先在 batch 上把 `G` 归一化到约 `N(0, 1)`。
- **熵坍缩。** 策略过早收敛到近乎确定的动作，停止探索，卡死。修法：在目标里加熵奖励 `β · H(π(·|s))`。
- **高方差。** 原味 REINFORCE 需要几千个 episode。critic 基线（第 07 课）或 TRPO/PPO 的信任域（第 08 课）是标准修法。
- **样本效率低。** On-policy 意味着每次更新后就扔掉所有转移。用重要性采样做异策略修正能把数据找回来，代价是方差（PPO 的 ratio 就是被裁剪的 IS 权重）。
- **非平稳梯度。** 100 个 episode 前的同一份梯度用的是旧 `π`。正因如此，on-policy 方法每隔几个 rollout 就更新一次。
- **信用分配。** 不用 reward-to-go，过去的奖励就只贡献噪声。永远用 reward-to-go。

> **Exploding gradients.** Returns can be huge. Always normalize `G` to `~N(0, 1)` across the batch before multiplying by `∇ log π`.
> **Entropy collapse.** The policy converges to a near-deterministic action too early, stops exploring, gets stuck. Fix: add entropy bonus `β · H(π(·|s))` to the objective.
> **High variance.** Vanilla REINFORCE needs thousands of episodes. A critic baseline (Lesson 07) or TRPO/PPO's trust region (Lesson 08) is the standard fix.
> **Credit assignment.** Without reward-to-go, past rewards contribute noise. Always use reward-to-go.

## Use It · 实战用法

2026 年的今天，很少有人直接跑 REINFORCE，但它的梯度公式无处不在：

| 使用场景 | 衍生方法 |
|----------|---------------|
| 连续控制 | 高斯策略的 PPO / SAC |
| LLM RLHF | 带 KL 惩罚的 PPO，跑在 token 级策略上 |
| LLM 推理（DeepSeek） | GRPO——带组相对基线的 REINFORCE，无 critic |
| 多智能体 | 集中式 critic 的 REINFORCE（MADDPG、COMA） |
| 离散动作机器人学 | A2C、A3C、PPO |
| 只有偏好数据 | DPO——REINFORCE 改写成偏好似然损失，无需采样 |

当你在 2026 年的训练脚本里读到 `loss = -advantage * log_prob`，那就是带基线的 REINFORCE。一整篇论文（DPO、GRPO、RLOO）都只是在这一行之上叠降方差技巧。

> In 2026, REINFORCE is rarely run directly but its gradient formula is everywhere...
> When you read `loss = -advantage * log_prob` in a 2026 training script, that is REINFORCE with a baseline. Entire papers (DPO, GRPO, RLOO) are variance-reduction tricks on top of this one line.

## Ship It · 交付

保存为 `outputs/skill-policy-gradient-trainer.md`：

```markdown
---
name: policy-gradient-trainer
description: Produce a REINFORCE / actor-critic / PPO training config for a given task and diagnose variance issues.
version: 1.0.0
phase: 9
lesson: 6
tags: [rl, policy-gradient, reinforce]
---

Given an environment (discrete / continuous actions, horizon, reward stats), output:

1. Policy head. Softmax (discrete) or Gaussian (continuous) with parameter counts.
2. Baseline. None (vanilla), running mean, learned `V̂(s)`, or A2C critic.
3. Variance controls. Reward-to-go on by default, return normalization, gradient clip value.
4. Entropy bonus. Coefficient β and decay schedule.
5. Batch size. Episodes per update; on-policy data freshness contract.

Refuse REINFORCE-no-baseline on horizons > 500 steps. Refuse continuous-action control with a softmax head. Flag any run with `β = 0` and observed policy entropy < 0.1 as entropy-collapsed.
```

> Save as `outputs/skill-policy-gradient-trainer.md`.

## Exercises · 练习

1. **简单。** 在 4×4 GridWorld 上用线性 softmax 策略实现 REINFORCE。不用基线训练 1,000 个 episode。画出学习曲线；测量方差（回报的标准差）。
2. **中等。** 加滑动平均基线。再训一次。对比原味运行的样本效率与方差。基线把收敛步数降低了多少？
3. **困难。** 加熵奖励 `β · H(π)`。扫描 `β ∈ {0, 0.01, 0.1, 1.0}`。画出最终回报和策略熵。这个任务的甜点位在哪？

> **Easy.** Implement REINFORCE on 4×4 GridWorld with a linear softmax policy. Train for 1,000 episodes without a baseline. Plot the learning curve; measure variance (std of returns).
> **Medium.** Add a running-mean baseline. Train again. Compare sample efficiency and variance to the vanilla run. By how much does the baseline reduce steps to convergence?
> **Hard.** Add an entropy bonus `β · H(π)`. Sweep `β ∈ {0, 0.01, 0.1, 1.0}`. Plot final return and policy entropy. Where is the sweet spot on this task?

## Key Terms · 术语表

| Term | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Policy gradient | "直接训练策略" | `∇J(θ) = E[G · ∇ log π_θ(a\|s)]`；由 log-derivative 技巧推出。 |
| REINFORCE | "最初的 PG 算法" | Williams（1992）；蒙特卡洛回报乘以 log 策略梯度。 |
| Log-derivative trick | "得分函数估计量" | `∇P(τ;θ) = P(τ;θ) · ∇ log P(τ;θ)`；让期望的梯度变得可算。 |
| Baseline | "降方差" | 任何从 `G` 里减掉的 `b(s)`；无偏，因为 `E[b · ∇ log π] = 0`。 |
| Reward-to-go | "只算未来回报" | 用 `G_t^{from t}` 替代完整的 `G_0`；正确且方差更低。 |
| Entropy bonus | "鼓励探索" | `+β · H(π(·\|s))` 项防止策略坍缩。 |
| On-policy | "用刚采的数据训练" | 梯度期望是对当前策略取的——旧数据不能直接复用。 |
| Advantage | "比平均好多少" | `A(s, a) = G(s, a) - V(s)`；带基线 REINFORCE 所乘的带符号量。 |

## Further Reading · 延伸阅读

- [Williams (1992). Simple Statistical Gradient-Following Algorithms for Connectionist Reinforcement Learning](https://link.springer.com/article/10.1007/BF00992696) —— REINFORCE 原始论文。
- [Sutton et al. (2000). Policy Gradient Methods for Reinforcement Learning with Function Approximation](https://papers.nips.cc/paper_files/paper/1999/hash/464d828b85b0bed98e80ade0a5c43b0f-Abstract.html) —— 带函数逼近的现代策略梯度定理。
- [Sutton & Barto (2018). Ch. 13 — Policy Gradient Methods](http://incompleteideas.net/book/RLbook2020.pdf) —— 教科书讲法。
- [OpenAI Spinning Up — VPG / REINFORCE](https://spinningup.openai.com/en/latest/algorithms/vpg.html) —— 讲解清晰，配 PyTorch 代码。
- [Peters & Schaal (2008). Reinforcement Learning of Motor Skills with Policy Gradients](https://homes.cs.washington.edu/~todorov/courses/amath579/reading/PolicyGradient.pdf) —— 降方差与自然梯度视角，把 REINFORCE 和信任域家族（TRPO、PPO）连了起来。
