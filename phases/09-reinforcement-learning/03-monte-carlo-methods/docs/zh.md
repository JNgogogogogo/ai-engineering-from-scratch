# Monte Carlo Methods — Learning from Complete Episodes · 蒙特卡洛方法——从完整 episode 中学习

> 动态规划需要模型。蒙特卡洛什么都不需要，只要有 episode。跑策略、看回报、求平均。这是 RL 里最简单的想法——也是解锁下游一切的那个想法。
>
> Dynamic programming needs a model. Monte Carlo needs nothing but episodes. Run the policy, watch the returns, average them. The simplest idea in RL — and the one that unlocks everything downstream.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 9 · 01（MDP）、Phase 9 · 02（动态规划）
**Time:** ~75 分钟

## The Problem · 问题在哪

动态规划很优雅，但它假设你对每一个状态和动作都能查询 `P(s' | s, a)`。现实世界里几乎没什么是这么运作的。机器人无法解析地算出施加关节力矩之后相机像素的分布；定价算法无法对所有可能的顾客反应做积分；LLM 无法枚举一个 token 之后所有可能的续写。

你需要一种只要求能从环境*采样*的方法。跑策略，拿到一条轨迹 `s_0, a_0, r_1, s_1, a_1, r_2, …, s_T`，用它来估计价值。这就是蒙特卡洛（Monte Carlo）。

从 DP 到 MC 的转变在哲学上很重要：我们从「*已知模型 + 精确 backup*」走到「*采样 rollout + 平均回报*」。方差跳升了，但适用范围爆炸式扩大。本课之后的每个 RL 算法——TD、Q-learning、REINFORCE、PPO、GRPO——骨子里都是蒙特卡洛估计器，有时再叠一层自举（bootstrapping）。

> Dynamic programming is elegant, but it assumes you can query `P(s' | s, a)` for every state and action. Almost nothing in the real world works that way. ... You need a method that only needs the ability to *sample* from the environment. Run the policy. Get a trajectory `s_0, a_0, r_1, s_1, a_1, r_2, …, s_T`. Use it to estimate values. That is Monte Carlo.
> The shift from DP to MC is philosophically important: we move from *known model + exact backup* to *sampled rollouts + averaged return*. The variance jumps, but the applicability explodes. Every RL algorithm after this lesson — TD, Q-learning, REINFORCE, PPO, GRPO — is a Monte Carlo estimator at heart, sometimes with bootstrapping layered on top.

## The Concept · 概念

![蒙特卡洛：rollout、计算回报、求平均；首访 vs 每访](../assets/monte-carlo.svg)

**核心思想，一句话：** `V^π(s) = E_π[G_t | s_t = s] ≈ (1/N) Σ_i G^{(i)}(s)`，其中 `G^{(i)}(s)` 是在策略 `π` 下访问 `s` 之后观测到的回报。

**首访 MC vs 每访 MC。** 如果一个 episode 多次访问状态 `s`：首访 MC（first-visit）只统计第一次访问之后的回报；每访 MC（every-visit）把每次访问都统计进去。两者在极限下都无偏。首访更好分析（样本独立同分布）；每访在每个 episode 里利用更多数据，实践中通常收敛更快。

**增量均值（incremental mean）。** 不必存储所有回报，直接更新滑动平均：

`V_n(s) = V_{n-1}(s) + (1/n) [G_n - V_{n-1}(s)]`

改写为：`V_new = V_old + α · (target - V_old)`，其中 `α = 1/n`。把 `1/n` 换成常数步长 `α ∈ (0, 1)`，就得到一个能跟踪 `π` 变化的非平稳 MC 估计器。这一次替换，就是从 MC 跨到 TD、再跨到所有现代 RL 算法的全部距离。

**探索从此成为一个问题。** DP 靠枚举摸遍每个状态；MC 只看得见策略访问到的状态。如果 `π` 是确定性的，状态空间里整片区域永远采不到，它们的价值估计永远停在零。三种修法，按历史顺序：

1. **探索起始（exploring starts）。** 每个 episode 从一个随机的 (s, a) 对出发。保证覆盖，但实践中不现实（你没法把机器人「重置」到任意状态）。
2. **ε-greedy。** 对当前 Q 贪心行动，但以概率 `ε` 随机选一个动作。渐近意义上所有状态-动作对都会被采到。
3. **离策（off-policy）MC。** 用行为策略 `μ` 采集数据，通过重要性采样（importance sampling）学习目标策略 `π`。方差高，但它是通往 DQN 这类 replay-buffer 方法的桥梁。

**蒙特卡洛控制（Monte Carlo Control）。** 评估 → 改进 → 评估，和策略迭代一样，只是评估改成了基于采样：

1. 跑 `π`，得到一个 episode。
2. 用观测到的回报更新 `Q(s, a)`。
3. 让 `π` 对 `Q` ε-greedy。
4. 重复。

在温和条件下（每个状态-动作对被访问无穷多次，`α` 满足 Robbins-Monro 条件），以概率 1 收敛到 `Q*` 和 `π*`。

> **First-visit vs every-visit MC.** Given an episode that visits state `s` multiple times, first-visit MC only counts the return from the first visit; every-visit MC counts all visits. Both are unbiased in the limit. ... Swap `1/n` for a constant step-size `α ∈ (0, 1)` and you get a non-stationary MC estimator that tracks changes in `π`. That move is the entire jump from MC to TD to every modern RL algorithm.
> DP touched every state by enumeration. MC only sees states the policy visits. If `π` is deterministic, whole regions of the state space never get sampled, and their value estimates stay at zero forever. ... Converges to `Q*` and `π*` with probability 1 under mild conditions (every pair visited infinitely often, `α` satisfies Robbins-Monro).

```figure
epsilon-greedy
```

## Build It · 动手造

### Step 1: rollout → list of (s, a, r) · rollout → (s, a, r) 列表

```python
def rollout(env, policy, max_steps=200):
    trajectory = []
    s = env.reset()
    for _ in range(max_steps):
        a = policy(s)
        s_next, r, done = env.step(s, a)
        trajectory.append((s, a, r))
        s = s_next
        if done:
            break
    return trajectory
```

没有模型，只有 `env.reset()` 和 `env.step(s, a)`。和 gym 环境是同一个接口，只是剥到最简。

> No model, only `env.reset()` and `env.step(s, a)`. Same interface as a gym environment but stripped down.

### Step 2: compute returns (reverse sweep) · 计算回报（反向扫描）

```python
def returns_from(trajectory, gamma):
    returns = []
    G = 0.0
    for _, _, r in reversed(trajectory):
        G = r + gamma * G
        returns.append(G)
    return list(reversed(returns))
```

一趟搞定，`O(T)`。反向递推 `G_t = r_{t+1} + γ G_{t+1}` 避免了重复求和。

> One pass, `O(T)`. The backward recurrence `G_t = r_{t+1} + γ G_{t+1}` avoids re-summing.

### Step 3: first-visit MC evaluation · 首访 MC 评估

```python
def mc_policy_evaluation(env, policy, episodes, gamma=0.99):
    V = defaultdict(float)
    counts = defaultdict(int)
    for _ in range(episodes):
        trajectory = rollout(env, policy)
        returns = returns_from(trajectory, gamma)
        seen = set()
        for t, ((s, _, _), G) in enumerate(zip(trajectory, returns)):
            if s in seen:
                continue
            seen.add(s)
            counts[s] += 1
            V[s] += (G - V[s]) / counts[s]
    return V
```

干活的就是三行：首访时把状态标记为已见、计数加一、更新滑动均值。

> Three lines do the work: mark state as seen on first visit, increment count, update running mean.

### Step 4: ε-greedy MC control (on-policy) · ε-greedy MC 控制（在策 / on-policy）

```python
def mc_control(env, episodes, gamma=0.99, epsilon=0.1):
    Q = defaultdict(lambda: {a: 0.0 for a in ACTIONS})
    counts = defaultdict(lambda: {a: 0 for a in ACTIONS})

    def policy(s):
        if random() < epsilon:
            return choice(ACTIONS)
        return max(Q[s], key=Q[s].get)

    for _ in range(episodes):
        trajectory = rollout(env, policy)
        returns = returns_from(trajectory, gamma)
        seen = set()
        for (s, a, _), G in zip(trajectory, returns):
            if (s, a) in seen:
                continue
            seen.add((s, a))
            counts[s][a] += 1
            Q[s][a] += (G - Q[s][a]) / counts[s][a]
    return Q, policy
```

### Step 5: compare to DP gold standard · 与 DP 黄金标准对比

当 episode 数 → ∞ 时，你对 `V^π` 的 MC 估计应当与第 02 课的 DP 结果一致。实际操作中：在 4×4 GridWorld 上跑 50,000 个 episode，就能与 DP 的答案相差 `~0.1` 以内。

> Your MC estimate of `V^π` should agree with the DP result from Lesson 02 as episodes → ∞. In practice: 50,000 episodes on 4×4 GridWorld gets you within `~0.1` of the DP answer.

## Pitfalls · 常见坑

- **无限 episode。** MC 要求 episode 会*终止*。如果你的策略可能永远打转，就给 `max_steps` 封顶，并把触顶当作隐式失败。随机策略下的 GridWorld 会经常超时——这很正常，只要确保你把这种情况统计对了。
- **方差。** MC 使用完整回报。episode 一长，方差巨大——结尾一个倒霉的奖励会把 `V(s_0)` 挪动同样大的幅度。TD 方法（第 04 课）用自举把它砍下来。
- **状态覆盖。** 在一个全新的、处处平局的 Q 上跑贪心 MC，它永远只会试一个动作。你*必须*探索（ε-greedy、探索起始、UCB）。
- **非平稳策略。** 如果 `π` 在变（MC 控制中就是如此），旧回报就来自不同的策略。常数 α 的 MC 能处理这种情况，样本平均 MC 不行。
- **离策重要性采样。** 权重 `π(a|s)/μ(a|s)` 沿轨迹连乘，方差随视野爆炸。用 per-decision weighted IS 封顶，或者改用 TD。

> **Infinite episodes.** MC requires episodes to *terminate*. If your policy can loop forever, cap `max_steps` and treat the cap as implicit failure. ... **Variance.** MC uses full returns. On long episodes, variance is huge — one unlucky reward at the end shifts `V(s_0)` by the same amount. TD methods (Lesson 04) cut this by bootstrapping. ... **Off-policy importance sampling.** The weights `π(a|s)/μ(a|s)` multiply across a trajectory. Variance explodes with horizon.

## Use It · 实战用法

蒙特卡洛方法在 2026 年扮演的角色：

| 用例 | 为什么用 MC |
|----------|--------|
| 短视野游戏（21 点、扑克） | episode 自然终止；回报干净。 |
| 对已记录策略做离线评估 | 在存储的轨迹上平均折扣回报。 |
| 蒙特卡洛树搜索（AlphaZero） | 从树叶节点出发的 MC rollout 指导选择。 |
| LLM 的 RL 评估 | 对给定策略采样出的补全求平均奖励。 |
| PPO 中的基线估计 | 优势目标 `A_t = G_t - V(s_t)` 用的就是 MC 的 `G_t`。 |
| RL 教学 | 真正能跑起来的最简单算法——剥掉自举看核心。 |

现代深度 RL 算法（PPO、SAC）通过 `n`-step 回报或 GAE，在纯 MC（完整回报）与纯 TD（一步自举）之间插值。两个端点都是同一个估计器的实例。

> Modern deep-RL algorithms (PPO, SAC) interpolate between pure MC (full returns) and pure TD (one-step bootstrap) via `n`-step returns or GAE. Both endpoints are instances of the same estimator.

## Ship It · 交付

保存为 `outputs/skill-mc-evaluator.md`：

```markdown
---
name: mc-evaluator
description: Evaluate a policy via Monte Carlo rollouts and produce a convergence report with DP-comparison if available.
version: 1.0.0
phase: 9
lesson: 3
tags: [rl, monte-carlo, evaluation]
---

Given an environment (episodic, with reset+step API) and a policy, output:

1. Method. First-visit vs every-visit MC. Reason.
2. Episode budget. Target number, variance diagnostic, expected standard error.
3. Exploration plan. ε schedule (if needed) or exploring starts.
4. Gold-standard comparison. DP-optimal V* if tabular; otherwise a bound from a Q-learning / PPO baseline.
5. Termination check. Max-step cap, timeouts, handling of non-terminating trajectories.

Refuse to run MC on non-episodic tasks without a finite horizon cap. Refuse to report V^π estimates from fewer than 100 episodes per state for tabular tasks. Flag any policy with zero-variance actions as an exploration risk.
```

## Exercises · 练习

1. **简单。** 在 4×4 GridWorld 上实现均匀随机策略的首访 MC 评估。跑 10,000 个 episode，画出 `V(0,0)` 随 episode 数变化的曲线，并与 DP 的答案对照。
2. **中等。** 用 `ε ∈ {0.01, 0.1, 0.3}` 实现 ε-greedy MC 控制，比较 20,000 个 episode 后的平均回报。曲线长什么样？偏差-方差权衡体现在哪里？
3. **困难。** 实现带重要性采样的*离策* MC：在均匀随机策略 `μ` 下采集数据，估计确定性最优策略 `π` 的 `V^π`。比较普通 IS、per-decision IS 与加权 IS（weighted IS）。哪一个方差最低？

## Key Terms · 术语表

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Monte Carlo（蒙特卡洛） | 「随机采样」 | 通过对来自分布的独立同分布样本求平均来估计期望。 |
| Return `G_t`（回报） | 「未来奖励」 | 从第 `t` 步到 episode 结束的折扣奖励和：`Σ_{k≥0} γ^k r_{t+k+1}`。 |
| First-visit MC（首访 MC） | 「每个状态只数一次」 | 一个 episode 内只有首次访问计入价值估计。 |
| Every-visit MC（每访 MC） | 「用上所有访问」 | 每次访问都计入；略有偏差但样本效率更高。 |
| ε-greedy | 「探索噪声」 | 以概率 `1-ε` 选贪心动作；以概率 `ε` 随机选动作。 |
| Importance sampling（重要性采样） | 「纠正『从错误的分布采样』」 | 用 `π(a\|s)/μ(a\|s)` 乘积对回报重加权，从 `μ` 的数据估计 `V^π`。 |
| On-policy（在策） | 「用自己的数据学」 | 目标策略 = 行为策略。原味 MC、PPO、SARSA。 |
| Off-policy（离策） | 「用别人的数据学」 | 目标策略 ≠ 行为策略。重要性采样 MC、Q-learning、DQN。 |

## Further Reading · 延伸阅读

- [Sutton & Barto (2018). Ch. 5 — Monte Carlo Methods](http://incompleteideas.net/book/RLbook2020.pdf) —— 权威论述。
- [Singh & Sutton (1996). Reinforcement Learning with Replacing Eligibility Traces](https://link.springer.com/article/10.1007/BF00114726) —— 首访 vs 每访的分析。
- [Precup, Sutton, Singh (2000). Eligibility Traces for Off-Policy Policy Evaluation](http://incompleteideas.net/papers/PSS-00.pdf) —— 离策 MC 与方差控制。
- [Mahmood et al. (2014). Weighted Importance Sampling for Off-Policy Learning](https://arxiv.org/abs/1404.6362) —— 现代低方差 IS 估计器。
- [Tesauro (1995). TD-Gammon, A Self-Teaching Backgammon Program](https://dl.acm.org/doi/10.1145/203330.203343) —— MC/TD 自博弈收敛到超人水平的首个大规模实证；本阶段后半部分每一课的概念先声。
