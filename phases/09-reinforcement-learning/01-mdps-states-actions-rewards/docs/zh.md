# MDPs, States, Actions & Rewards · MDP、状态、动作与奖励

> 马尔可夫决策过程（Markov Decision Process, MDP）就是五样东西：状态、动作、转移、奖励、折扣。强化学习（RL）里的一切——Q-learning、PPO、DPO、GRPO——都在对这个结构做优化。学一次，后面整个强化学习都免费读懂。
>
> A Markov Decision Process is five things: states, actions, transitions, rewards, a discount. Everything in RL — Q-learning, PPO, DPO, GRPO — optimizes over this shape. Learn it once, read the rest of reinforcement learning for free.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 1 · 06（概率与分布）、Phase 2 · 01（机器学习分类）
**Time:** ~45 分钟

## The Problem · 问题在哪

你可能在写一个国际象棋 bot、一个库存规划器、一个交易 agent，或者训练推理模型的 PPO 循环。四个完全不同的领域，一个惊人的事实：它们全部坍缩成同一个数学对象。

监督学习给你 `(x, y)` 数据对，让你去拟合一个函数。强化学习不给你标签——只给你一串状态流、你采取过的动作，以及一个标量奖励。这步棋赢下比赛了吗？这次补货决策省下钱了吗？这笔交易赚到利润了吗？LLM 刚生成的这个 token，有没有让 judge 给出更高的奖励？

不先把这条数据流形式化，你就无法从中学到东西。「我看到了什么」「我做了什么」「接下来发生了什么」「结果有多好」——每一项都必须变成一个可以推理的对象。这个形式化就是马尔可夫决策过程（MDP）。本阶段（Phase 9）的每一个 RL 算法，包括最后的 RLHF 和 GRPO 循环，都在对这个结构做优化。

> You are writing a chess bot. Or an inventory planner. Or a trading agent. Or the PPO loop that trains a reasoning model. Four different domains, one surprising fact: all four collapse to the same mathematical object.
> Supervised learning gives you `(x, y)` pairs and asks you to fit a function. Reinforcement learning gives you no labels — only a stream of states, the actions you took, and a scalar reward. ... You cannot learn from this stream until you formalize it. "What I saw," "what I did," "what happened next," "how good that was" — each has to become an object you can reason about. That formalization is a Markov Decision Process. Every RL algorithm in this phase, including the RLHF and GRPO loops at the end, optimizes over this shape.

## The Concept · 概念

![马尔可夫决策过程：状态、动作、转移、奖励、折扣](../assets/mdp.svg)

**五个对象。**

- **状态（States）** `S`：agent 做决策所需的一切。在 GridWorld 里是一个格子；在国际象棋里是棋盘；在 LLM 里是上下文窗口加上所有记忆。
- **动作（Actions）** `A`：可选项。上下左右移动、走一步棋、生成一个 token。
- **转移（Transitions）** `P(s' | s, a)`：给定状态 `s` 和动作 `a`，下一状态的概率分布。国际象棋是确定性的，库存问题是随机的，LLM 解码近乎确定。
- **奖励（Rewards）** `R(s, a, s')`：那个标量信号。赢 = +1，输 = -1；收入减去成本；GRPO 里的对数似然比项。
- **折扣（Discount）** `γ ∈ [0, 1)`：未来奖励相对当下奖励的折算比例。`γ = 0.99` 买到约 100 步的有效视野；`γ = 0.9` 约 10 步。

**马尔可夫性质（Markov property）** `P(s_{t+1} | s_t, a_t) = P(s_{t+1} | s_0, a_0, …, s_t, a_t)`。未来只取决于当前状态。如果不满足，说明你的状态表示不完整——不是方法的失败，是状态的失败。

**策略与回报。** 策略 `π(a | s)` 把状态映射到动作分布。回报（return）`G_t = r_t + γ r_{t+1} + γ² r_{t+2} + …` 是未来奖励的折扣和。价值 `V^π(s) = E[G_t | s_t = s]` 是在策略 `π` 下从 `s` 出发的期望回报。Q 值 `Q^π(s, a) = E[G_t | s_t = s, a_t = a]` 是以特定动作起步的期望回报。每个 RL 算法都在估计这两者之一，然后据此改进 `π`。

**Bellman 方程。** 本阶段一切算法都要用的不动点方程：

`V^π(s) = Σ_a π(a|s) Σ_{s', r} P(s', r | s, a) [r + γ V^π(s')]`
`Q^π(s, a) = Σ_{s', r} P(s', r | s, a) [r + γ Σ_{a'} π(a'|s') Q^π(s', a')]`

它们把期望回报拆成「这一步的奖励」加上「落点的折扣价值」。递归。Phase 9 的每个算法，要么把这个方程迭代到收敛（动态规划），要么从它采样（蒙特卡洛方法），要么对它做一步自举（bootstrap，即时序差分）。

> **The five objects.** ... The future depends only on the present state. If it does not, the state representation is incomplete — not a failure of the method, a failure of the state.
> Every RL algorithm estimates one of these two, then improves `π` accordingly. ... These split expected return into "this step's reward" plus "discounted value of where you land." Recursive. Every algorithm in Phase 9 either iterates this equation to convergence (dynamic programming), samples from it (Monte Carlo), or bootstraps it one step (temporal difference).

```figure
discount-horizon
```

## Build It · 动手造

### Step 1: a tiny deterministic MDP · 一个微型确定性 MDP

一个 4×4 的 GridWorld：agent 从左上角出发，右下角是终止态，每走一步奖励 -1，动作集合是 `{up, down, left, right}`。代码见 `code/main.py`。

```python
GRID = 4
TERMINAL = (3, 3)
ACTIONS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}

def step(state, action):
    if state == TERMINAL:
        return state, 0.0, True
    dr, dc = ACTIONS[action]
    r, c = state
    nr = min(max(r + dr, 0), GRID - 1)
    nc = min(max(c + dc, 0), GRID - 1)
    return (nr, nc), -1.0, (nr, nc) == TERMINAL
```

五行代码，就是整个环境：确定性转移、恒定的步数惩罚、吸收型的终止状态。

> A 4×4 GridWorld. Agent starts top-left, terminal at bottom-right, reward of -1 per step, actions `{up, down, left, right}`. ... Five lines. That is the entire environment. Deterministic transitions, constant step penalty, absorbing terminal state.

### Step 2: roll out a policy · rollout 一条策略

策略是一个从状态到动作分布的函数。最简单的版本：均匀随机。

```python
def uniform_policy(state):
    return {a: 0.25 for a in ACTIONS}

def rollout(policy, max_steps=200):
    s, total, steps = (0, 0), 0.0, 0
    for _ in range(max_steps):
        a = sample(policy(s))
        s, r, done = step(s, a)
        total += r
        steps += 1
        if done:
            break
    return total, steps
```

把随机策略跑 1000 次。在这个 4×4 棋盘上，平均回报大约在 -60 到 -80 之间。最优回报是 -6（沿右下方走直线）。把这中间的差距消掉，就是 Phase 9 的全部内容。

> A policy is a function from state to action distribution. The simplest: uniform random. ... Run the random policy 1000 times. Average return is around -60 to -80 for this 4×4 board. The optimal return is -6 (straight-line path down-right). Closing that gap is everything in Phase 9.

### Step 3: compute `V^π` exactly via the Bellman equation · 用 Bellman 方程精确计算 `V^π`

对小型 MDP 来说，Bellman 方程就是一个线性方程组：枚举所有状态、代入期望、迭代到数值不再变化为止。

```python
def policy_evaluation(policy, gamma=0.99, tol=1e-6):
    V = {s: 0.0 for s in all_states()}
    while True:
        delta = 0.0
        for s in all_states():
            if s == TERMINAL:
                continue
            v = 0.0
            for a, pi_a in policy(s).items():
                s_next, r, _ = step(s, a)
                v += pi_a * (r + gamma * V[s_next])
            delta = max(delta, abs(v - V[s]))
            V[s] = v
        if delta < tol:
            return V
```

这就是迭代式策略评估（iterative policy evaluation）。它是 Sutton & Barto 书中的第一个算法，也是之后所有 RL 方法的理论基础。

> For small MDPs the Bellman equation is a linear system. Enumerate states, apply the expectation, iterate until the values stop changing. ... This is iterative policy evaluation. It is the first algorithm in Sutton & Barto and the theoretical foundation of every RL method that follows.

### Step 4: `γ` is a hyperparameter with physical meaning · `γ` 是有物理含义的超参数

有效视野大约是 `1 / (1 - γ)`。`γ = 0.9` → 10 步。`γ = 0.99` → 100 步。`γ = 0.999` → 1000 步。

太低，agent 会变得短视；太高，信用分配（credit assignment）会变得嘈杂，因为许多早期步骤都要为遥远未来的奖励分担责任。LLM 的 RLHF 通常用 `γ = 1`，因为 episode 短且有界。控制任务用 `0.95–0.99`。长视野策略游戏用 `0.999`。

> Effective horizon is roughly `1 / (1 - γ)`. `γ = 0.9` → 10 steps. `γ = 0.99` → 100 steps. `γ = 0.999` → 1000 steps.
> Too low and the agent acts myopically. Too high and credit assignment becomes noisy, because many early steps share responsibility for far-future reward. LLM RLHF typically uses `γ = 1` because episodes are short and bounded. Control tasks use `0.95–0.99`. Long-horizon strategy games use `0.999`.

## Pitfalls · 常见坑

- **非马尔可夫状态。** 如果你需要最近三次观测才能做决策，那「状态」就不只是当前观测。修法：堆叠帧（Atari 上的 DQN 堆 4 帧），或使用循环状态（对观测跑 LSTM/GRU）。
- **稀疏奖励。** 只有输赢的奖励在大型状态空间里几乎学不动。做奖励塑形（reward shaping，加入中间信号），或用模仿学习打底（Phase 9 · 09）。
- **奖励劫持（reward hacking）。** 优化代理奖励常常产生病态行为。OpenAI 的赛船 agent 原地转圈无限收集道具，就是不肯冲线。奖励一定要从目标结果本身定义，而不是从代理指标定义。
- **折扣设错。** 在无限视野任务上取 `γ = 1`，所有价值都会变成无穷。要么有限视野、要么 `γ < 1`，必须封一个。
- **奖励量纲。** {+100, -100} 和 {+1, -1} 给出完全相同的最优策略，但梯度量级天差地别。喂给 PPO/DQN 之前，先归一化到 `[-1, 1]` 附近。

> **Non-Markovian state.** If you need the last three observations to decide, the "state" is not just the current observation. ... **Reward hacking.** Optimizing a proxy reward often produces pathological behavior. OpenAI's boat-racing agent spun in circles collecting powerups forever instead of finishing the race. Always define reward from the target outcome, not the proxy. ... **Discount mis-spec.** `γ = 1` on an infinite-horizon task makes every value infinite. ... **Reward scale.** Rewards of {+100, -100} vs {+1, -1} give identical optimal policies but vastly different gradient magnitudes.

## Use It · 实战用法

2026 年的实践套路是：在碰任何代码之前，先把每个 RL 流水线归约成一个 MDP：

| 场景 | 状态 | 动作 | 奖励 | γ |
|-----------|-------|--------|--------|---|
| 控制（运动、操作） | 关节角度 + 速度 | 连续力矩 | 按任务塑形 | 0.99 |
| 游戏（象棋、围棋、扑克） | 棋盘 + 历史 | 合法着法 | 赢=+1 / 输=-1 | 1.0（有限） |
| 库存 / 定价 | 库存 + 需求 | 订货量 | 收入 - 成本 | 0.95 |
| LLM 的 RLHF | 上下文 token | 下一个 token | 结束时奖励模型打分 | 1.0（episode 约 200 token） |
| 推理的 GRPO | 提示 + 部分回复 | 下一个 token | 结束时验证器 0/1 | 1.0 |

先写出五元组，再写训练循环。大多数「RL 不 work」的 bug 报告，最后都能追溯到纸面上就没建好的 MDP 形式化。

> The 2026 stack reduces every RL pipeline to an MDP before touching code: ... Write the five tuples before writing any training loop. Most "RL does not work" bug reports trace back to an MDP formulation that was broken on paper.

## Ship It · 交付

保存为 `outputs/skill-mdp-modeler.md`：

```markdown
---
name: mdp-modeler
description: Given a task description, produce a Markov Decision Process spec and flag formulation risks before training.
version: 1.0.0
phase: 9
lesson: 1
tags: [rl, mdp, modeling]
---

Given a task (control / game / recommendation / LLM fine-tuning), output:

1. State. Exact feature vector or tensor spec. Justify Markov property.
2. Action. Discrete set or continuous range. Dimensionality.
3. Transition. Deterministic, stochastic-with-known-model, or sample-only.
4. Reward. Function and source. Sparse vs shaped. Terminal vs per-step.
5. Discount. Value and horizon justification.

Refuse to ship any MDP where the state is non-Markovian without explicit mention of frame-stacking or recurrent state. Refuse any reward that was not defined in terms of the target outcome. Flag any `γ ≥ 1.0` on an infinite-horizon task. Flag any reward range >100x the typical step reward as a likely gradient-explosion source.
```

## Exercises · 练习

1. **简单。** 在 `code/main.py` 里实现 4×4 GridWorld 和随机策略 rollout。跑 10,000 个 episode，报告回报的均值和标准差，并与最优回报（-6）比较。
2. **中等。** 对均匀随机策略，用 `γ ∈ {0.5, 0.9, 0.99}` 分别运行 `policy_evaluation`，把每个 `V` 打印成 4×4 网格。解释为什么 `γ` 越大，终止态附近的状态价值增长越快。
3. **困难。** 把 GridWorld 改成随机的：每个动作有 `p = 0.1` 的概率滑向一个相邻方向。重新评估均匀策略。`V[start]` 变好了还是变坏了？为什么？

## Key Terms · 术语表

| 术语 | 人们常怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| MDP | 「强化学习的标准设定」 | 满足马尔可夫性质的元组 `(S, A, P, R, γ)`。 |
| State（状态） | 「agent 看到的东西」 | 在所选策略类下，对未来动态的充分统计量。 |
| Policy（策略） | 「agent 的行为」 | 条件分布 `π(a \| s)` 或确定性映射 `s → a`。 |
| Return（回报） | 「总奖励」 | 从当前步起的折扣和 `Σ γ^t r_t`。 |
| Value（价值） | 「一个状态有多好」 | 在 `π` 下从 `s` 出发的期望回报。 |
| Q-value（Q 值） | 「一个动作有多好」 | 在 `π` 下从 `s` 出发、第一步走 `a` 的期望回报。 |
| Bellman equation | 「动态规划递归式」 | 把价值 / Q 分解为「一步奖励 + 后继折扣价值」的不动点式。 |
| Discount `γ`（折扣） | 「未来 vs 当下」 | 远期奖励的几何权重；有效视野约 `~1/(1-γ)`。 |

## Further Reading · 延伸阅读

- [Sutton & Barto (2018). Reinforcement Learning: An Introduction, 2nd ed.](http://incompleteideas.net/book/RLbook2020.pdf) —— 教材本体。第 3 章讲 MDP 与 Bellman 方程；第 1 章论证了支撑后续每一课的奖励假设（reward hypothesis）。
- [Bellman (1957). Dynamic Programming](https://press.princeton.edu/books/paperback/9780691146683/dynamic-programming) —— Bellman 方程的源头。
- [OpenAI Spinning Up — Part 1: Key Concepts](https://spinningup.openai.com/en/latest/spinningup/rl_intro.html) —— 从深度 RL 视角写的简明 MDP 入门。
- [Puterman (2005). Markov Decision Processes](https://onlinelibrary.wiley.com/doi/book/10.1002/9780470316887) —— 运筹学视角的 MDP 与精确解法参考书。
- [Littman (1996). Algorithms for Sequential Decision Making (PhD thesis)](https://cs.brown.edu/media/filer_public/d1/a6/d1a6f66a-289a-4b81-9596-417114843489/littman.pdf) —— 把 MDP 推导为动态规划特例的最清晰文本。
