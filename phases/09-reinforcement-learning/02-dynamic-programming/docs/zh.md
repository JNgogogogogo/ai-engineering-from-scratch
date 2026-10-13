# Dynamic Programming — Policy Iteration & Value Iteration · 动态规划——策略迭代与价值迭代

> 动态规划是「允许作弊的 RL」：转移函数和奖励函数你都已经知道，只需要迭代 Bellman 方程，直到 `V` 或 `π` 不再变化。它是所有基于采样的方法努力逼近的那个基准。
>
> Dynamic programming is RL with cheating. You already know the transition and reward functions; you just iterate the Bellman equation until `V` or `π` stops moving. It is the benchmark every sampling-based method tries to approach.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 9 · 01（MDP）
**Time:** ~75 分钟

## The Problem · 问题在哪

你手里是一个模型已知的 MDP：对任意「状态-动作」对，你都能查询 `P(s' | s, a)` 和 `R(s, a, s')`。库存经理知道需求分布；棋盘游戏的转移是确定的；一个 gridworld 就是四行 Python。你拥有一个*模型*。

无模型 RL（Q-learning、PPO、REINFORCE）是为「没有模型、只能从环境采样」的场景发明的。但当你真的有模型时，存在更快、更好的方法：动态规划（dynamic programming）。Bellman 在 1957 年设计了它们。它们至今仍定义着「正确」：当人们说「这个 MDP 的最优策略」时，指的就是 DP 会返回的那个策略。

2026 年你仍然需要它们，原因有三。第一，RL 研究中的每个表格型（tabular）环境（GridWorld、FrozenLake、CliffWalking）都用 DP 求解，以产出黄金标准策略。第二，精确价值让你能*调试*采样方法：如果 Q-learning 对 `V*(s_0)` 的估计和 DP 的答案差了 30%，那你的 Q-learning 有 bug。第三，现代离线 RL 与规划方法（MCTS、AlphaZero 的搜索、Phase 9 · 10 的 model-based RL）全都在一个学到的或给定的模型上迭代 Bellman backup。

> Model-free RL (Q-learning, PPO, REINFORCE) was invented for the case where you don't have a model — you can only sample from the environment. ... Bellman designed them in 1957. They still define correctness: when people say "optimal policy for this MDP," they mean the policy DP would return.
> Second, exact values let you *debug* sampling methods: if Q-learning's estimate for `V*(s_0)` disagrees with the DP answer by 30%, your Q-learning has a bug. Third, modern offline RL and planning methods (MCTS, AlphaZero's search, model-based RL in Phase 9 · 10) all iterate a Bellman backup over a learned or given model.

## The Concept · 概念

![策略迭代与价值迭代，并排对照](../assets/dp.svg)

**两个算法，都是对 Bellman 方程的不动点迭代。**

**策略迭代（policy iteration）。** 交替执行两个步骤，直到策略不再变化。

1. *评估（evaluation）：* 给定策略 `π`，反复应用 `V(s) ← Σ_a π(a|s) Σ_{s',r} P(s',r|s,a) [r + γ V(s')]` 直到收敛，得到 `V^π`。
2. *改进（improvement）：* 给定 `V^π`，让 `π` 对 `V^π` 贪心：`π(s) ← argmax_a Σ_{s',r} P(s',r|s,a) [r + γ V(s')]`。

收敛有保证，因为 (a) 每次改进要么保持 `π` 不变、要么让某些状态的 `V^π` 严格上升，(b) 确定性策略的空间是有限的。即使状态空间很大，通常也只要约 5–20 轮外层迭代就收敛。

**价值迭代（value iteration）。** 把评估和改进合并成一次扫描（sweep）。应用 Bellman *最优性*方程：

`V(s) ← max_a Σ_{s',r} P(s',r|s,a) [r + γ V(s')]`

重复直到 `max_s |V_new(s) - V(s)| < ε`，最后取贪心动作提取出策略。单次迭代严格更快——没有内层评估循环——但通常需要更多次迭代才能收敛。

**广义策略迭代（Generalized Policy Iteration, GPI）。** 统一框架：价值函数和策略被锁进一个双向改进的循环；任何驱动两者走向相互一致的方法（异步价值迭代、改进型策略迭代、Q-learning、actor-critic、PPO）都是 GPI 的一个实例。

**为什么 `γ < 1` 重要。** Bellman 算子在 sup 范数下是 `γ`-压缩（contraction）映射：`||T V - T V'||_∞ ≤ γ ||V - V'||_∞`。压缩意味着唯一不动点与几何级收敛。去掉 `γ < 1`，保证就没了——你需要有限视野或吸收型终止状态。

> **Two algorithms, both fixed-point iteration on Bellman.** ... Convergence is guaranteed because (a) each improvement step either keeps `π` the same or strictly increases `V^π` for some state, (b) the space of deterministic policies is finite. Usually converges in ~5–20 outer iterations even for large state spaces.
> Repeat until `max_s |V_new(s) - V(s)| < ε`. Extract the policy at the end by taking the greedy action. ... any method that drives both toward mutual consistency (async value iteration, modified policy iteration, Q-learning, actor-critic, PPO) is an instance of GPI.
> The Bellman operator is a `γ`-contraction in the sup-norm: `||T V - T V'||_∞ ≤ γ ||V - V'||_∞`. Contraction implies unique fixed point and geometric convergence. Drop `γ < 1` and you lose the guarantee — you need a finite horizon or an absorbing terminal state.

```figure
value-iteration-gamma
```

## Build It · 动手造

### Step 1: build the GridWorld MDP model · 搭建 GridWorld 的 MDP 模型

沿用第 01 课的 4×4 GridWorld，加一个随机变体：agent 有 `0.1` 的概率滑向一个随机的垂直方向。

```python
SLIP = 0.1

def transitions(state, action):
    if state == TERMINAL:
        return [(state, 0.0, 1.0)]
    outcomes = []
    for direction, prob in action_probs(action):
        outcomes.append((apply_move(state, direction), -1.0, prob))
    return outcomes
```

`transitions(s, a)` 返回一个 `(s', r, p)` 列表。这就是全部的模型。

> Use the same 4×4 GridWorld from Lesson 01. We add a stochastic variant: with probability `0.1` the agent slips to a random perpendicular direction. ... `transitions(s, a)` returns a list of `(s', r, p)`. This is the entire model.

### Step 2: policy evaluation · 策略评估

给定策略 `π(s) = {action: prob}`，迭代 Bellman 方程，直到 `V` 不再变化：

```python
def policy_evaluation(policy, gamma=0.99, tol=1e-6):
    V = {s: 0.0 for s in states()}
    while True:
        delta = 0.0
        for s in states():
            v = sum(pi_a * sum(p * (r + gamma * V[s_prime])
                              for s_prime, r, p in transitions(s, a))
                   for a, pi_a in policy(s).items())
            delta = max(delta, abs(v - V[s]))
            V[s] = v
        if delta < tol:
            return V
```

> Given a policy `π(s) = {action: prob}`, iterate the Bellman equation until `V` stops moving.

### Step 3: policy improvement · 策略改进

用对 `V` 贪心的策略替换 `π`。如果 `π` 没有变化，直接返回——我们已经到达最优。

```python
def policy_improvement(V, gamma=0.99):
    new_policy = {}
    for s in states():
        best_a = max(
            ACTIONS,
            key=lambda a: sum(p * (r + gamma * V[s_prime])
                              for s_prime, r, p in transitions(s, a)),
        )
        new_policy[s] = best_a
    return new_policy
```

> Replace `π` with the greedy policy w.r.t. `V`. If `π` did not change, return — we are at the optimum.

### Step 4: stitch them together · 把它们拼起来

```python
def policy_iteration(gamma=0.99):
    policy = {s: "up" for s in states()}   # arbitrary start
    for _ in range(100):
        V = policy_evaluation(lambda s: {policy[s]: 1.0}, gamma)
        new_policy = policy_improvement(V, gamma)
        if new_policy == policy:
            return V, policy
        policy = new_policy
```

4×4 上的典型收敛：4–6 轮外层迭代。输出 `V*(0,0) ≈ -6`，以及一个严格减少步数的策略。

> Typical convergence on 4×4: 4–6 outer iterations. Outputs `V*(0,0) ≈ -6` and a policy that strictly decreases the step count.

### Step 5: value iteration (the one-loop version) · 价值迭代（单循环版）

```python
def value_iteration(gamma=0.99, tol=1e-6):
    V = {s: 0.0 for s in states()}
    while True:
        delta = 0.0
        for s in states():
            v = max(sum(p * (r + gamma * V[s_prime])
                       for s_prime, r, p in transitions(s, a))
                   for a in ACTIONS)
            delta = max(delta, abs(v - V[s]))
            V[s] = v
        if delta < tol:
            break
    policy = policy_improvement(V, gamma)
    return V, policy
```

同一个不动点，更少的代码。

> Same fixed point, fewer lines of code.

## Pitfalls · 常见坑

- **忘了处理终止态。** 对吸收态套 Bellman，它照样会挑出一个「什么也改变不了的最优动作」。加一道护栏：`if s == terminal: V[s] = 0`。
- **sup 范数 vs L2 收敛判据。** 用 `max |V_new - V|`，不要用平均值。理论保证是建立在 sup 范数上的。
- **原地更新 vs 同步更新。** 原地更新 `V[s]`（Gauss-Seidel 风格）比用单独的 `V_new` 字典（Jacobi 风格）收敛更快。生产代码用原地更新。
- **策略平局。** 两个动作 Q 值相同时，`argmax` 每次迭代打破平局的方式可能不同，导致「策略稳定」检查来回震荡。用稳定的 tie-break（按固定顺序取第一个动作）。
- **状态空间爆炸。** DP 每次扫描的复杂度是 `O(|S| · |A|)`，撑得到约 10⁷ 个状态。再往上就需要函数逼近（Phase 9 · 05 起）。

> **Forgetting to handle terminals.** If you apply Bellman to an absorbing state, it still picks up a "best action" that changes nothing. Guard with `if s == terminal: V[s] = 0`. ... **Sup-norm vs L2 convergence.** Use `max |V_new - V|`, not average. The theoretical guarantee is on the sup-norm. ... **State-space explosion.** DP is `O(|S| · |A|)` per sweep. Works up to ~10⁷ states. Beyond that, you need function approximation (Phase 9 · 05 onwards).

## Use It · 实战用法

2026 年，DP 是正确性基线，也是规划器的内层循环：

| 用例 | 方法 |
|----------|--------|
| 精确求解一个小型表格型 MDP | 价值迭代（更简单）或策略迭代（外层步数更少） |
| 验证一个 Q-learning / PPO 实现 | 在玩具环境上与 DP 最优的 V* 比较 |
| Model-based RL（Phase 9 · 10） | 在学到的转移模型上做 Bellman backup |
| AlphaZero / MuZero 中的规划 | 蒙特卡洛树搜索 = 异步 Bellman backup |
| 离线 RL（CQL、IQL） | 保守 Q 迭代——对 OOD 动作加惩罚的 DP |

每当有人说「最优价值函数」，指的就是「DP 的不动点」。在论文里看到 `V*` 或 `Q*` 时，脑子里就浮现这个循环。

> In 2026, DP is the correctness baseline and the inner loop of planners: ... Every time someone says "the optimal value function," they mean "the DP fixed point." When you see `V*` or `Q*` in a paper, picture this loop.

## Ship It · 交付

保存为 `outputs/skill-dp-solver.md`：

```markdown
---
name: dp-solver
description: Solve a small tabular MDP exactly via policy iteration or value iteration. Report convergence behavior.
version: 1.0.0
phase: 9
lesson: 2
tags: [rl, dynamic-programming, bellman]
---

Given an MDP with a known model, output:

1. Choice. Policy iteration vs value iteration. Reason tied to |S|, |A|, γ.
2. Initialization. V_0, starting policy. Convergence sensitivity.
3. Stopping. Sup-norm tolerance ε. Expected number of sweeps.
4. Verification. V*(s_0) computed exactly. Greedy policy extracted.
5. Use. How this baseline will be used to debug/evaluate sampling-based methods.

Refuse to run DP on state spaces > 10⁷. Refuse to claim convergence without a sup-norm check. Flag any γ ≥ 1 on an infinite-horizon task as a guarantee violation.
```

## Exercises · 练习

1. **简单。** 在 4×4 GridWorld 上用 `γ ∈ {0.9, 0.99}` 跑价值迭代。多少次扫描后 `max |ΔV| < 1e-6`？把 `V*` 打印成 4×4 网格。
2. **中等。** 在*随机* GridWorld（打滑概率 `0.1`）上比较策略迭代与价值迭代。统计：扫描次数、实际耗时、最终的 `V*(0,0)`。按迭代次数谁收敛更快？按实际耗时呢？
3. **困难。** 实现改进型策略迭代（modified policy iteration）：评估步只跑 `k` 次扫描，不跑到收敛。画出 `k ∈ {1, 2, 5, 10, 50}` 时 `V*(0,0)` 的误差对 `k` 的曲线。这条曲线告诉你评估/改进之间的取舍是什么？

## Key Terms · 术语表

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Policy iteration（策略迭代） | 「DP 算法」 | 交替进行评估（`V^π`）与改进（对 `V^π` 贪心的 `π`），直到策略不再变化。 |
| Value iteration（价值迭代） | 「更快的 DP」 | 一次扫描内应用 Bellman 最优性 backup；几何级收敛到 `V*`。 |
| Bellman operator（Bellman 算子） | 「那个递归式」 | `(T V)(s) = max_a Σ P (r + γ V(s'))`；sup 范数下的 `γ`-压缩。 |
| Contraction（压缩映射） | 「DP 为什么收敛」 | 满足 `\|\|T x - T y\|\| ≤ γ \|\|x - y\|\|` 的算子 `T` 有唯一不动点。 |
| GPI | 「万物皆 DP」 | 广义策略迭代：任何驱动 `V` 与 `π` 走向相互一致的方法。 |
| Synchronous update（同步更新） | 「Jacobi 风格」 | 整轮扫描都使用旧的 `V`；分析起来干净但更慢。 |
| In-place update（原地更新） | 「Gauss-Seidel 风格」 | 边更新边使用 `V`；实践中收敛更快。 |

## Further Reading · 延伸阅读

- [Sutton & Barto (2018). Ch. 4 — Dynamic Programming](http://incompleteideas.net/book/RLbook2020.pdf) —— 策略迭代与价值迭代的权威表述。
- [Bertsekas (2019). Reinforcement Learning and Optimal Control](http://www.athenasc.com/rlbook_athena.html) —— 压缩映射论证的严谨处理。
- [Puterman (2005). Markov Decision Processes](https://onlinelibrary.wiley.com/doi/book/10.1002/9780470316887) —— 改进型策略迭代及其收敛性分析。
- [Howard (1960). Dynamic Programming and Markov Processes](https://mitpress.mit.edu/9780262582300/dynamic-programming-and-markov-processes/) —— 策略迭代的原始论文。
- [Bertsekas & Tsitsiklis (1996). Neuro-Dynamic Programming](http://www.athenasc.com/ndpbook.html) —— 从 DP 通向近似 DP / 深度 RL 的桥梁，本阶段后续每一课都要用到。
