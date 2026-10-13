# Multi-Agent RL · 多智能体强化学习

单智能体 RL 假设环境是平稳的。把两个学习中的智能体放进同一个世界，这个假设就碎了：每个智能体都是对方环境的一部分，而且双方都在变。多智能体强化学习（multi-agent RL）就是在马尔可夫假设失效时让学习仍能收敛的一整套技巧。

> Single-agent RL assumes the environment is stationary. Put two learning agents in the same world and that assumption breaks: each agent is part of the other's environment, and both are changing. Multi-agent RL is the set of tricks to make learning converge when the Markov assumption no longer holds.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 9 · 04 (Q-learning), Phase 9 · 06 (REINFORCE), Phase 9 · 07 (Actor-Critic)
**Time:** ~45 minutes

## The Problem · 问题在哪

一个学会在房间里导航的机器人是单智能体 RL 问题。足球队不是。AlphaStar 对阵 StarCraft 对手不是。由竞价智能体组成的市场不是。两辆车在四方停牌路口互相博弈不是。现实中大量「多对多」问题都不是。

在任何多智能体场景里，从任意一个智能体的视角看，其他智能体*就是*环境的一部分。当它们学习并改变行为时，环境就变成非平稳的。马尔可夫性质——「下一状态只依赖当前状态和我的动作」——被破坏了，因为下一状态还依赖*其他*智能体选了什么，而它们的策略是移动靶。

这会打破表格型收敛证明（Q-learning 的保证假设环境平稳）。朴素的深度 RL 同样被打破：智能体互相追逐、循环打转，永远收敛不到稳定策略。你需要多智能体专属技术：集中训练 / 去中心化执行（centralized training / decentralized execution）、反事实基线（counterfactual baselines）、联盟赛（league play）、自博弈（self-play）。

2026 年的应用：机器人集群、交通路由、自动驾驶车队、市场模拟器、多智能体 LLM 系统（Phase 16），以及任何有不止一个智能玩家的游戏。

> In every multi-agent setting, from the perspective of any one agent, the other agents *are* part of the environment. As they learn and change their behavior, the environment becomes non-stationary. ... The Markov property — "next state depends only on current state and my action" — gets violated because the next state also depends on what the *other* agents chose, and their policies are moving targets. ... You need multi-agent-specific techniques: centralized training / decentralized execution, counterfactual baselines, league play, self-play.

## The Concept · 概念

![Four MARL regimes: indep, centralized critic, self-play, league](../assets/marl.svg)

**形式化：马尔可夫博弈（Markov Game）。** MDP 的推广：状态 `S`、联合动作 `a = (a_1, …, a_n)`、转移 `P(s' | s, a)`、以及每个智能体各自的奖励 `R_i(s, a, s')`。每个智能体 `i` 在自己的策略 `π_i` 下最大化自己的回报。如果奖励相同，就是**完全合作（fully cooperative）**；如果是零和，就是**对抗（adversarial）**；如果混合，就是**一般和（general-sum）**。

**核心挑战：**

- **非平稳性。** 从智能体 `i` 的视角看，`P(s' | s, a_i)` 依赖于 `π_{-i}`，而后者正在变化。
- **信用分配。** 奖励是共享的，那是哪个智能体造成的？
- **探索协调。** 智能体要探索互补的策略，而不是冗余地探索同一个状态。
- **可扩展性。** 联合动作空间随 `n` 指数增长。
- **部分可观测。** 每个智能体只看到自己的观测；全局状态是隐藏的。

**四种主流范式：**

**1. 独立 Q-learning / 独立 PPO（IQL、IPPO）。** 每个智能体学自己的 Q 或策略，把其他智能体当成环境的一部分。简单，有时也能行（经验回放会充当一种平滑的「对手建模」技巧）。理论收敛性：没有。实践中：松耦合任务够用，紧耦合任务不行。

**2. 集中训练、去中心化执行（centralized training, decentralized execution, CTDE）。** 现代最常用的范式。每个智能体有自己的*策略* `π_i`，只条件于局部观测 `o_i`——部署时就是标准的去中心化执行。*训练*时，一个集中式 critic `Q(s, a_1, …, a_n)` 条件于完整的全局状态和联合动作。例子：
- **MADDPG**（Lowe et al. 2017）：DDPG 加上每个智能体各自的集中式 critic。
- **COMA**（Foerster et al. 2017）：反事实基线——问「如果我当初选的是动作 `a'` 而不是它，我的奖励会是什么？」——把我的贡献分离出来。
- **MAPPO** / 带共享 critic 的 **IPPO**（Yu et al. 2022）：带集中式价值函数的 PPO。2026 年合作式 MARL 的主流。
- **QMIX**（Rashid et al. 2018）：价值分解——`Q_tot(s, a) = f(Q_1(s, a_1), …, Q_n(s, a_n))`，用单调混合。

**3. 自博弈（self-play）。** 同一个智能体的两个副本互相对打。对手策略*就是*我自己某个过去快照的策略。AlphaGo / AlphaZero / MuZero、OpenAI Five。对零和博弈最有效；训练信号是对称的。

**4. 联盟赛（league play）。** 自博弈向一般和 / 对抗环境的扩展：保留一个由过去和当前策略组成的种群，从联盟中采样一个对手，对着它训练。再加入 exploiter（专门克制当前最强者）和 main exploiter（专门克制 exploiter）。AlphaStar（StarCraft II）。当游戏存在「石头剪刀布」式的策略循环时，这是必需品。

**通信。** 允许智能体互发学习到的消息 `m_i`。在合作场景中有效。Foerster et al. (2016) 证明了智能体间的可微通信可以端到端训练。今天基于 LLM 的多智能体系统（Phase 16）本质上就是在用自然语言通信。

```figure
f3-marl-orbit
```

> If rewards are identical, it is **fully cooperative**. If zero-sum, it is **adversarial**. If mixed, it is **general-sum**. ... Most common modern paradigm. Each agent has its own *policy* `π_i` that conditions on local observation `o_i` — standard decentralized execution at deployment. During *training*, a centralized critic `Q(s, a_1, …, a_n)` conditions on the full global state and joint action. ... Works best for zero-sum games; the training signal is symmetric.

## Build It · 动手造

本课用一个 6×6 GridWorld 和两个合作智能体。它们从对角出发，必须抵达同一个共享目标。共享奖励：只要有智能体还在移动，每步 `-1`；两者都到达时 `+10`。见 `code/main.py`。

> This lesson uses a 6×6 GridWorld with two cooperative agents. They start in opposite corners and must reach a shared goal. Shared reward: `-1` per step while either agent is still moving, `+10` when both arrive. See `code/main.py`.

### Step 1: the multi-agent env · 多智能体环境

```python
class CoopGridWorld:
    def __init__(self):
        self.size = 6
        self.goal = (5, 5)

    def reset(self):
        return ((0, 0), (5, 0))  # two agents

    def step(self, state, actions):
        a1, a2 = state
        new1 = move(a1, actions[0])
        new2 = move(a2, actions[1])
        done = (new1 == self.goal) and (new2 == self.goal)
        reward = 10.0 if done else -1.0
        return (new1, new2), reward, done
```

*联合*动作空间是 `|A|² = 16`。全局状态就是两个位置。

> The *joint* action space is `|A|² = 16`. The global state is two positions.

### Step 2: independent Q-learning · 独立 Q-learning

每个智能体维护自己的 Q 表，以联合状态为键。每一步：双方都按 ε-greedy 选动作、收集联合转移，然后各自用共享奖励更新自己的 Q。

```python
def independent_q(env, episodes, alpha, gamma, epsilon):
    Q1, Q2 = defaultdict(default_q), defaultdict(default_q)
    for _ in range(episodes):
        s = env.reset()
        while not done:
            a1 = epsilon_greedy(Q1, s, epsilon)
            a2 = epsilon_greedy(Q2, s, epsilon)
            s_next, r, done = env.step(s, (a1, a2))
            target1 = r + gamma * max(Q1[s_next].values())
            target2 = r + gamma * max(Q2[s_next].values())
            Q1[s][a1] += alpha * (target1 - Q1[s][a1])
            Q2[s][a2] += alpha * (target2 - Q2[s][a2])
            s = s_next
```

它在这个任务上有效，因为奖励稠密且一致。在紧耦合任务上会失败（比如一个智能体必须*等*另一个的那种）。

> Each agent runs its own Q-table keyed on joint state. At each step: both pick ε-greedy actions, collect joint transition, each updates its own Q with the shared reward. ... Works on this task because rewards are dense and aligned. Fails on tightly-coupled tasks (e.g., where one agent has to *wait* for the other).

### Step 3: centralized Q with decomposed-value update · 集中式 Q 与分解价值更新

用一个覆盖联合动作的 Q：`Q(s, a_1, a_2)`，从共享奖励更新。执行时通过边缘化实现去中心化：`π_i(s) = argmax_{a_i} max_{a_{-i}} Q(s, a_1, a_2)`。用指数级的联合动作空间，换一个*正确*的全局视角。

> Use one Q over joint actions `Q(s, a_1, a_2)`. Update from shared reward. Decentralize at execution by marginalizing: `π_i(s) = argmax_{a_i} max_{a_{-i}} Q(s, a_1, a_2)`. Trades exponential joint action space for a *correct* global view.

### Step 4: simple self-play (adversarial 2-agent) · 简单自博弈（对抗性双智能体）

同一个智能体，两个角色。训练智能体 A 对抗智能体 B；每 `K` 个 episode 后把 A 的权重拷贝进 B。对称训练，稳定进步。微缩版 AlphaZero 配方。

> Same agent, two roles. Train agent A against agent B; after `K` episodes, copy A's weights into B. Symmetric training, consistent progress. The AlphaZero recipe in miniature.

## Pitfalls · 常见陷阱

- **非平稳的回放。** 独立智能体用经验回放比单智能体更糟，因为旧转移是已经被淘汰的旧对手生成的。对策：重标注，或按新旧程度加权。
- **信用分配歧义。** 长 episode 结束后只有一份共享奖励，说不清哪个智能体贡献了什么。对策：反事实基线（COMA），或按智能体做奖励塑形（reward shaping）。
- **策略漂移 / 互相追逐。** 每个智能体的最优应对随对方的更新而变。对策：集中式 critic、调低学习率，或一次冻结一个。
- **通过协调进行奖励黑客。** 智能体会找到设计者没预料到的协调性漏洞。拍卖智能体会集体收敛到出价为零。对策：仔细的奖励设计、行为约束。
- **探索冗余。** 两个智能体探索同一批「状态-动作」对。对策：给每个智能体加熵奖励，或按角色条件化。
- **联盟循环。** 纯自博弈可能卡在支配循环里。对策：用带多样化对手的联盟赛。
- **样本爆炸。** `n` 个智能体 × 状态空间 × 联合动作。用函数近似来压缩；用分解的动作空间（每个智能体一个策略输出头）。

> Experience replay with independent agents is worse than single-agent because old transitions were generated by now-obsolete opponents. ... Each agent's best response changes with each other's update. ... Agents find coordinated exploits the designer did not anticipate. Auction agents converge to bid zero.

## Use It · 实战用法

2026 年的 MARL 应用地图：

| 领域 | 方法 | 备注 |
|--------|--------|-------|
| 合作导航 / 操作 | MAPPO / QMIX | CTDE；共享 critic + 去中心化执行器。 |
| 双人游戏（国际象棋、围棋、扑克） | 带 MCTS 的自博弈（AlphaZero） | 零和；对称训练。 |
| 复杂多人游戏（Dota、StarCraft） | 联盟赛 + 模仿学习预训练 | OpenAI Five、AlphaStar。 |
| 自动驾驶车队 | 带注意力的 CTDE MAPPO / PPO | 部分可观测；队伍规模可变。 |
| 拍卖市场 | 博弈论均衡 + RL | `n` → ∞ 时用平均场 RL（mean-field RL）。 |
| LLM 多智能体系统（Phase 16） | 自然语言通信 + 角色条件化 | RL 循环放在智能体规划层。 |

2026 年 MARL 最大的增长点是基于 LLM 的：成群的语言模型智能体在谈判、辩论、写软件。RL 体现在对*轨迹级*输出（而非 token 级）的偏好优化上（Phase 16 · 03）。

> In 2026, MARL's biggest growth area is LLM-based: swarms of language-model agents negotiating, debating, building software. The RL shows up as preference optimization on *trajectory-level* outputs, not token-level (Phase 16 · 03).

## Ship It · 交付

保存为 `outputs/skill-marl-architect.md`：

```markdown
---
name: marl-architect
description: Pick the right multi-agent RL regime (IPPO, CTDE, self-play, league) for a given task.
version: 1.0.0
phase: 9
lesson: 10
tags: [rl, multi-agent, marl, self-play]
---

Given a task with `n` agents, output:

1. Regime classification. Cooperative / adversarial / general-sum. Justify.
2. Algorithm. IPPO / MAPPO / QMIX / self-play / league. Reason tied to coupling tightness and reward structure.
3. Information access. Centralized training (what global info goes to the critic)? Decentralized execution?
4. Credit assignment. Counterfactual baseline, value decomposition, or reward shaping.
5. Exploration plan. Per-agent entropy, population-based training, or league.

Refuse independent Q-learning on tightly-coupled cooperative tasks. Refuse to recommend self-play for general-sum with cycle risks. Flag any MARL pipeline without a fixed-opponent eval (cherry-picked self-play numbers are common).
```

> Save as `outputs/skill-marl-architect.md`:

## Exercises · 练习

1. **简单。** 在双智能体合作 GridWorld 上训练独立 Q-learning。多少个 episode 后平均回报 > 0？画出联合学习曲线。
2. **中等。** 加一个「协调」任务：只有两个智能体在同一回合都踩上目标格才算到达。独立 Q 还能收敛吗？什么东西坏掉了？
3. **困难。** 实现一个集中式 critic 做 MAPPO 式训练，在协调任务上与独立 PPO 比较收敛速度。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Markov game | 「多智能体 MDP」 | `(S, A_1, …, A_n, P, R_1, …, R_n)`；每个智能体有自己的奖励。 |
| CTDE | 「集中训练、去中心化执行」 | 训练时用联合 critic；每个智能体的策略只用局部观测。 |
| IPPO | 「独立 PPO」 | 每个智能体单独跑 PPO。简单基线；常被低估。 |
| MAPPO | 「多智能体 PPO」 | 带条件于全局状态的集中式价值函数的 PPO。 |
| QMIX | 「单调价值分解」 | `Q_tot = f_monotone(Q_1, …, Q_n)`，允许去中心化 argmax。 |
| COMA | 「反事实多智能体」 | 优势 = 我的 Q 减去对我的动作做边缘化后的期望 Q。 |
| Self-play | 「智能体打过去的自己」 | 单智能体、两个角色；零和博弈的标准做法。 |
| League play | 「种群训练」 | 缓存过去的策略、从池中采样对手；能应对策略循环。 |

## Further Reading · 延伸阅读

- [Lowe et al. (2017). Multi-Agent Actor-Critic for Mixed Cooperative-Competitive Environments (MADDPG)](https://arxiv.org/abs/1706.02275) —— 带集中式 critic 的 CTDE。
- [Foerster et al. (2017). Counterfactual Multi-Agent Policy Gradients (COMA)](https://arxiv.org/abs/1705.08926) —— 用于信用分配的反事实基线。
- [Rashid et al. (2018). QMIX: Monotonic Value Function Factorisation](https://arxiv.org/abs/1803.11485) —— 带单调性的价值分解。
- [Yu et al. (2022). The Surprising Effectiveness of PPO in Cooperative Multi-Agent Games (MAPPO)](https://arxiv.org/abs/2103.01955) —— PPO 在 MARL 里出奇地强。
- [Vinyals et al. (2019). Grandmaster level in StarCraft II using multi-agent reinforcement learning (AlphaStar)](https://www.nature.com/articles/s41586-019-1724-z) —— 大规模联盟赛。
- [Silver et al. (2017). Mastering the game of Go without human knowledge (AlphaGo Zero)](https://www.nature.com/articles/nature24270) —— 零和博弈中的纯自博弈。
- [Sutton & Barto (2018). Ch. 15 — Neuroscience & Ch. 17 — Frontiers](http://incompleteideas.net/book/RLbook2020.pdf) —— 教科书对多智能体场景及非平稳问题的简短论述，CTDE 正是为解决非平稳性而生。
- [Zhang, Yang & Başar (2021). Multi-Agent Reinforcement Learning: A Selective Overview](https://arxiv.org/abs/1911.10635) —— 覆盖合作、竞争与混合 MARL 及收敛结果的综述。
