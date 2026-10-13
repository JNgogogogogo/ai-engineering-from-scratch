# Temporal Difference — Q-Learning & SARSA · 时序差分——Q-Learning 与 SARSA

> 蒙特卡洛要等到 episode 结束。TD 每走一步就更新，做法是自举（bootstrap）下一个价值估计。Q-learning 是离策的、乐观的；SARSA 是在策的、谨慎的。两者都只有一行代码。本阶段的每个深度 RL 方法都踩在它们之上。
>
> Monte Carlo waits until the episode ends. TD updates after every step by bootstrapping the next value estimate. Q-learning is off-policy and optimistic; SARSA is on-policy and cautious. Both are one line of code. Both underpin every deep-RL method in this phase.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 9 · 01（MDP）、Phase 9 · 02（动态规划）、Phase 9 · 03（蒙特卡洛）
**Time:** ~75 分钟

## The Problem · 问题在哪

蒙特卡洛能用，但它有两个昂贵的先决条件：它要求 episode 会终止，而且要等最终回报到手才更新。如果你的 episode 有 1,000 步，MC 就干等 1,000 步才更新任何东西。它高方差、低偏差，实践中还慢。

动态规划的画像正好相反——零方差的自举 backup——但要求模型已知。

时序差分（temporal difference, TD）学习取其中道：从单次转移 `(s, a, r, s')` 出发，构造一个一步目标 `r + γ V(s')`，把 `V(s)` 朝它挪一点。不需要模型。不需要完整 episode。等式右边用了近似的 `V` 所以有偏差，但方差比 MC 低得多，而且从第一步起就是在线更新。

这就是整个现代 RL——DQN、A2C、PPO、SAC——赖以转动的轴心。Phase 9 的剩余部分，就是叠在你将在本课亲手写出的那个一步 TD 更新之上的函数逼近与技巧层。

> Monte Carlo works but it has two expensive demands. It needs episodes that terminate, and it only updates after the final return is in. If your episode is 1,000 steps, MC waits 1,000 steps to update anything. It is high-variance, low-bias, and slow in practice.
> Temporal difference (TD) learning splits the difference. From a single transition `(s, a, r, s')`, form a one-step target `r + γ V(s')` and nudge `V(s)` toward it. No model. No complete episodes. ... This is the pivot on which all of modern RL — DQN, A2C, PPO, SAC — turns. The rest of Phase 9 is layers of function approximation and tricks built on top of the one-step TD update you will write in this lesson.

## The Concept · 概念

![Q-learning vs SARSA：离策 max vs 在策 Q(s', a')](../assets/td.svg)

**V 的 TD(0) 更新：**

`V(s) ← V(s) + α [r + γ V(s') - V(s)]`

方括号里的量就是 TD 误差（TD error）`δ = r + γ V(s') - V(s)`，它是 MC 中 `G_t - V(s_t)` 的在线对应物。收敛要求 `α` 满足 Robbins-Monro 条件（`Σ α = ∞`、`Σ α² < ∞`），且所有状态被访问无穷多次。

**Q-learning。** 一种离策（off-policy）的 TD 控制方法：

`Q(s, a) ← Q(s, a) + α [r + γ max_{a'} Q(s', a') - Q(s, a)]`

这个 `max` 假定从 `s'` 之后将执行*贪心*策略，而不管 agent 实际采取的动作是什么。正是这种解耦，让 Q-learning 能在 agent 用 ε-greedy 探索的同时学到 `Q*`。Mnih 等人（2015）把它变成了 Atari 上的深度 Q-learning（第 05 课）。

**SARSA。** 一种在策（on-policy）的 TD 方法：

`Q(s, a) ← Q(s, a) + α [r + γ Q(s', a') - Q(s, a)]`

名字就是那个元组 `(s, a, r, s', a')`。SARSA 用的是 agent 下一步*实际*执行的动作 `a'`，而不是贪心的 `argmax`。它收敛到当前运行的 ε-greedy 策略 `π` 所对应的 `Q^π`；在 `ε → 0` 的极限下，这个 `Q^π` 变成 `Q*`。

**悬崖行走的差别。** 在经典的 cliff-walking 任务上（掉下悬崖 = 奖励 -100），Q-learning 学到沿悬崖边缘的最优路径，但探索时会偶尔吃到惩罚。SARSA 学到一条离悬崖一步之遥的更安全路径，因为它把探索噪声算进了自己的 Q 值。训练充分后，两者在 `ε → 0` 时都达到最优。实践中这很重要：如果部署时探索仍在发生，SARSA 的行为更保守。

**Expected SARSA。** 把 `Q(s', a')` 换成它在 `π` 下的期望：

`Q(s, a) ← Q(s, a) + α [r + γ Σ_{a'} π(a'|s') Q(s', a') - Q(s, a)]`

比 SARSA 方差更低（不用采样 `a'`），目标同样是在策的。现代教材里常作为默认讲法。

**n-step TD 与 TD(λ)。** 通过等 `n` 步再自举，在 TD(0) 与 MC 之间插值。`n=1` 是 TD，`n=∞` 是 MC。TD(λ) 用几何权重 `(1-λ)λ^{n-1}` 对所有 `n` 求平均。大多数深度 RL 用 3 到 20 之间的 `n`。

> The bracketed quantity is the TD error `δ = r + γ V(s') - V(s)`. It is the online analogue of `G_t - V(s_t)` in MC. Convergence requires `α` satisfying Robbins-Monro (`Σ α = ∞`, `Σ α² < ∞`) and all states visited infinitely often.
> The `max` assumes the *greedy* policy will be followed from `s'` onward, regardless of what action the agent actually takes. That decoupling makes Q-learning learn `Q*` while the agent explores via ε-greedy. ... SARSA uses the action `a'` the agent *actually* takes next, not the greedy `argmax`. Converges to `Q^π` for whatever ε-greedy `π` is running, which in the limit `ε → 0` becomes `Q*`.
> On the classic cliff-walking task (fall-off-cliff = reward -100), Q-learning learns the optimal path along the cliff edge but occasionally takes the penalty during exploration. SARSA learns a safer path one step away from the cliff because it factors exploration noise into its Q-value. ... Most deep-RL uses `n` between 3 and 20.

```figure
qlearning-gridworld
```

## Build It · 动手造

### Step 1: SARSA on ε-greedy policy · ε-greedy 策略上的 SARSA

```python
def sarsa(env, episodes, alpha=0.1, gamma=0.99, epsilon=0.1):
    Q = defaultdict(lambda: {a: 0.0 for a in ACTIONS})

    def choose(s):
        if random() < epsilon:
            return choice(ACTIONS)
        return max(Q[s], key=Q[s].get)

    for _ in range(episodes):
        s = env.reset()
        a = choose(s)
        while True:
            s_next, r, done = env.step(s, a)
            a_next = choose(s_next) if not done else None
            target = r + (gamma * Q[s_next][a_next] if not done else 0.0)
            Q[s][a] += alpha * (target - Q[s][a])
            if done:
                break
            s, a = s_next, a_next
    return Q
```

八行。与 Q-learning *唯一*的差别就是 target 那一行。

> Eight lines. The *only* difference from Q-learning is the target line.

### Step 2: Q-learning · Q-learning

```python
def q_learning(env, episodes, alpha=0.1, gamma=0.99, epsilon=0.1):
    Q = defaultdict(lambda: {a: 0.0 for a in ACTIONS})
    for _ in range(episodes):
        s = env.reset()
        while True:
            a = choose(s, Q, epsilon)
            s_next, r, done = env.step(s, a)
            target = r + (gamma * max(Q[s_next].values()) if not done else 0.0)
            Q[s][a] += alpha * (target - Q[s][a])
            if done:
                break
            s = s_next
    return Q
```

这个 `max` 把目标与行为解耦。在策与离策的差别，就在这一个符号上。

> The `max` decouples target from behavior. That one symbol is the difference between on-policy and off-policy.

### Step 3: learning curves · 学习曲线

每 100 个 episode 记录一次平均回报。在简单的确定性 GridWorld 上 Q-learning 收敛更快；在 cliff-walking 上 SARSA 更保守。在 `code/main.py` 的 4×4 GridWorld 上，用 `α=0.1, ε=0.1` 跑约 2,000 个 episode 后，两者都接近最优。

> Track mean return per 100 episodes. Q-learning converges faster on simple deterministic GridWorld; SARSA is more conservative on cliff-walking. On the 4×4 GridWorld in `code/main.py`, both are near-optimal after ~2,000 episodes with `α=0.1, ε=0.1`.

### Step 4: compare to DP truth · 与 DP 真值对比

跑价值迭代（第 02 课）得到 `Q*`，然后检查 `max_{s,a} |Q_learned(s,a) - Q*(s,a)|`。一个健康的表格型 TD agent，在 4×4 GridWorld 上跑 10,000 个 episode 后，误差应落在 `~0.5` 以内。

> Run value iteration (Lesson 02) to get `Q*`. Check `max_{s,a} |Q_learned(s,a) - Q*(s,a)|`. A healthy tabular TD agent lands within `~0.5` on the 4×4 GridWorld after 10,000 episodes.

## Pitfalls · 常见坑

- **Q 初值有影响。** 乐观初始化（负奖励任务上取 `Q = 0`）鼓励探索；悲观初始化可能让贪心策略永远被困。
- **α 调度。** 常数 `α` 对非平稳问题够用。衰减 `α_n = 1/n` 理论上收敛，但实践太慢——把 `α` 钉在 `[0.05, 0.3]`，盯着学习曲线。
- **ε 调度。** 从高起步（`ε=1.0`），衰减到 `ε=0.05`。「GLIE」（无限探索下的极限贪心，greedy in the limit with infinite exploration）是收敛条件。
- **Q-learning 的 max 偏差。** `Q` 有噪声时，`max` 算子向上偏，导致高估——Hasselt 的 Double Q-learning（第 05 课的 DDQN 在用）用两张 Q 表修复了这个问题。
- **不终止的 episode。** TD 没有终止态也能学，但你要么封住步数，要么在封顶处正确处理自举。标准做法：把触顶当作非终止，继续自举。
- **状态哈希。** 如果状态是元组/张量，要用可哈希的键（元组而非列表；取整后的浮点元组而非原始值）。

> **Initial Q values matter.** Optimistic init (`Q = 0` for a negative-reward task) encourages exploration. ... **Max bias in Q-learning.** The `max` operator is biased upward when `Q` is noisy. Leads to overestimation — Hasselt's Double Q-learning (used by DDQN in Lesson 05) fixes this with two Q tables. ... **Non-terminating episodes.** TD can learn without terminals, but you need to either cap steps or handle bootstrap correctly at the cap. Standard: treat cap as non-terminal, keep bootstrapping.

## Use It · 实战用法

2026 年的 TD 版图：

| 任务 | 方法 | 理由 |
|------|--------|--------|
| 小型表格型环境 | Q-learning | 直接学到最优策略。 |
| 在策、安全关键 | SARSA / Expected SARSA | 探索期间更保守。 |
| 高维状态 | DQN（Phase 9 · 05） | 带 replay 和 target network 的神经网络 Q 函数。 |
| 连续动作 | SAC / TD3（Phase 9 · 07） | 在 Q 网络上做 TD 更新；策略网络输出动作。 |
| LLM RL（基于奖励模型） | PPO / GRPO（Phase 9 · 08, 12） | actor-critic，通过 GAE 得到 TD 风格的优势。 |
| 离线 RL | CQL / IQL（Phase 9 · 08） | 带保守正则化的 Q-learning。 |

2026 年论文里读到的「RL」，九成都是 Q-learning 或 SARSA 的某种 elaboration。在往深处读之前，先把这个表格型更新练到手指头上。

> Ninety percent of the "RL" you read about in 2026 papers is some elaboration of Q-learning or SARSA. Understand the tabular update in your fingers before reading deeper.

## Ship It · 交付

保存为 `outputs/skill-td-agent.md`：

```markdown
---
name: td-agent
description: Pick between Q-learning, SARSA, Expected SARSA for a tabular or small-feature RL task.
version: 1.0.0
phase: 9
lesson: 4
tags: [rl, td-learning, q-learning, sarsa]
---

Given a tabular or small-feature environment, output:

1. Algorithm. Q-learning / SARSA / Expected SARSA / n-step variant. One-sentence reason tied to on-policy vs off-policy and variance.
2. Hyperparameters. α, γ, ε, decay schedule.
3. Initialization. Q_0 value (optimistic vs zero) and justification.
4. Convergence diagnostic. Target learning curve, `|Q - Q*|` check if DP is possible.
5. Deployment caveat. How will exploration behave at inference? Is SARSA's conservatism needed?

Refuse to apply tabular TD to state spaces > 10⁶. Refuse to ship a Q-learning agent without a max-bias caveat. Flag any agent trained with ε held at 1.0 throughout (no exploitation phase).
```

## Exercises · 练习

1. **简单。** 在 4×4 GridWorld 上实现 Q-learning 和 SARSA。画 2,000 个 episode 的学习曲线（每 100 个 episode 的平均回报）。谁收敛更快？
2. **中等。** 搭一个 cliff-walking 环境（4×12，最后一行是奖励 -100 并重置回起点的悬崖）。比较 Q-learning 和 SARSA 的最终策略，把各自走的路径截图下来。哪条更贴近悬崖？
3. **困难。** 实现 Double Q-learning。在一个含噪奖励的 GridWorld 上（每步奖励加高斯噪声 σ=5），展示 Q-learning 对 `V*(0,0)` 的高估有实质幅度，而 Double Q-learning 没有。

## Key Terms · 术语表

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| TD error（TD 误差） | 「更新信号」 | `δ = r + γ V(s') - V(s)`，自举得到的残差。 |
| TD(0) | 「一步 TD」 | 每次转移后立即更新，只用下一状态的估计。 |
| Q-learning | 「离策 RL 入门」 | 对下一状态的动作取 `max` 的 TD 更新；无论行为策略如何都学到 `Q*`。 |
| SARSA | 「在策版 Q-learning」 | 使用实际下一动作的 TD 更新；学到当前 ε-greedy π 的 `Q^π`。 |
| Expected SARSA | 「低方差版 SARSA」 | 把采样的 `a'` 换成它在 π 下的期望。 |
| GLIE | 「正确的探索调度」 | 无限探索下的极限贪心（Greedy in the Limit with Infinite Exploration）；Q-learning 收敛所需。 |
| Bootstrapping（自举） | 「目标里用了当前估计」 | TD 区别于 MC 的地方。偏差的来源，也是方差的巨幅削减。 |
| Maximization bias（最大化偏差） | 「Q-learning 会高估」 | 对含噪估计取 `max` 向上偏；Double Q-learning 修复。 |

## Further Reading · 延伸阅读

- [Watkins & Dayan (1992). Q-learning](https://link.springer.com/article/10.1007/BF00992698) —— 原始论文与收敛性证明。
- [Sutton & Barto (2018). Ch. 6 — Temporal-Difference Learning](http://incompleteideas.net/book/RLbook2020.pdf) —— TD(0)、SARSA、Q-learning、Expected SARSA。
- [Hasselt (2010). Double Q-learning](https://papers.nips.cc/paper_files/paper/2010/hash/091d584fced301b442654dd8c23b3fc9-Abstract.html) —— 最大化偏差的修复。
- [Seijen, Hasselt, Whiteson, Wiering (2009). A Theoretical and Empirical Analysis of Expected SARSA](https://ieeexplore.ieee.org/document/4927542) —— Expected SARSA 的动机。
- [Rummery & Niranjan (1994). On-line Q-learning using connectionist systems](https://www.researchgate.net/publication/2500611_On-Line_Q-Learning_Using_Connectionist_Systems) —— 提出 SARSA 的论文（当时叫「modified connectionist Q-learning」）。
- [Sutton & Barto (2018). Ch. 7 — n-step Bootstrapping](http://incompleteideas.net/book/RLbook2020.pdf) —— 把 TD(0) 推广到 TD(n)；从 Q-learning 通向 eligibility traces、再到后来 PPO 中 GAE 的路径。
