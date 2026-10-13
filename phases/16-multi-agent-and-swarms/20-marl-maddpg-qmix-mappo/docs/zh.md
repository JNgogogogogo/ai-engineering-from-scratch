# MARL — MADDPG, QMIX, MAPPO · 多智能体强化学习 —— MADDPG、QMIX、MAPPO

> The reinforcement-learning heritage of multi-agent coordination, which still informs LLM-agent systems in 2026. **MADDPG** (Lowe et al., NeurIPS 2017, arXiv:1706.02275) introduced Centralized Training, Decentralized Execution (CTDE): each critic sees all agents' states and actions during training; at test time only local actors run. Works for cooperative, competitive, and mixed settings. **QMIX** (Rashid et al., ICML 2018, arXiv:1803.11485) is value-decomposition with a monotonic mixing network; per-agent Qs combine into joint Q so `argmax` distributes cleanly — dominant on StarCraft Multi-Agent Challenge (SMAC). **MAPPO** (Yu et al., NeurIPS 2022, arXiv:2103.01955) is PPO with a centralized value function; "surprisingly effective" on particle-world, SMAC, Google Research Football, Hanabi with minimal tuning. These underpin training policies for agent teams that must act decentrally. MAPPO is the **default 2026 cooperative-MARL baseline**. This lesson builds each from a small grid-world toy and lands the three ideas in muscle memory before touching LLM-agent training.

多智能体协调的强化学习传统，到 2026 年仍在为 LLM 智能体系统提供思想养分。**MADDPG**（Lowe et al., NeurIPS 2017, arXiv:1706.02275）提出了集中训练、分散执行（Centralized Training, Decentralized Execution，CTDE）：训练时每个 critic 能看到所有智能体的状态和动作；测试时只运行本地 actor。适用于合作、竞争与混合场景。**QMIX**（Rashid et al., ICML 2018, arXiv:1803.11485）是用单调混合网络做价值分解：各智能体的 Q 组合成联合 Q，使 `argmax` 能干净地分布化 —— 在 StarCraft Multi-Agent Challenge（SMAC）上称霸。**MAPPO**（Yu et al., NeurIPS 2022, arXiv:2103.01955）是带集中式价值函数的 PPO；在 particle-world、SMAC、Google Research Football、Hanabi 上「出奇地有效」，且几乎不用调参。它们共同支撑着必须分散执行的智能体团队策略训练。MAPPO 是 **2026 年默认的合作式 MARL 基线**。本课在一个小网格世界玩具上逐一构建这三者，在接触 LLM 智能体训练之前，把这三个思想刻进肌肉记忆。

**Type:** Learn
**Languages:** Python (stdlib, small NumPy-free implementations)
**Prerequisites:** Phase 09 (Reinforcement Learning), Phase 16 · 09 (Parallel Swarm Networks)
**Time:** ~90 minutes

## Problem · 问题

LLM 智能体系统越来越多地要为智能体之间的协调训练策略：什么时候让位、什么时候行动、调用哪个同伴。告诉你如何训练这类策略的文献就是多智能体强化学习（Multi-Agent Reinforcement Learning，MARL），它早于 LLM 浪潮，并有一小组占主导地位的算法。

没有模式词汇就去读 MARL 论文会很痛苦。集中训练分散执行（CTDE）、价值分解、集中式 critic 都不是口号 —— 它们是对特定问题的具体回答：

- 独立 RL（每个智能体自己学）从每个智能体的视角看是非平稳的。糟糕。
- 集中式 RL（一个智能体控制一切）无法扩展，且违反执行约束。
- CTDE 把两头的好处都拿到：用全局信息训练，用本地策略部署。

> LLM-agent systems increasingly train policies for inter-agent coordination: when to defer, when to act, which peer to call. The literature that tells you how to train such policies is Multi-Agent Reinforcement Learning (MARL), which predates the LLM wave and has a small set of dominant algorithms.
> Reading MARL papers without the pattern vocabulary is painful. Centralized training with decentralized execution (CTDE), value decomposition, and centralized critics are not buzzwords — they are specific answers to specific problems.
> Independent RL (each agent learns alone) is non-stationary from each agent's perspective. Bad. Centralized RL (one agent controls all) does not scale and violates execution constraints. CTDE gets the best of both: train with global information, deploy with local policies.

## Concept · 概念

### Three environments the papers use · 论文使用的三个环境

- **Particle World（多智能体粒子环境）。** 简单的 2D 物理，合作/竞争任务。MADDPG 的原始试验场。
- **StarCraft Multi-Agent Challenge（SMAC）。** 合作式微观操作、部分可观测。QMIX 的试验场。离散动作、连续状态。
- **Google Research Football、Hanabi、MPE。** MAPPO 的基线。

不同环境的动作/观测类型不同。算法会据此选择。

> **Particle World (multi-agent particle env).** Simple 2D physics with cooperative/competitive tasks. MADDPG's original testbed.
> **StarCraft Multi-Agent Challenge (SMAC).** Cooperative micro-management, partial observation. QMIX's testbed. Discrete actions, continuous states.
> **Google Research Football, Hanabi, MPE.** MAPPO baselines.
> Different envs have different action/observation types. The algorithms pick accordingly.

### MADDPG (2017) — the CTDE pattern · MADDPG（2017）—— CTDE 模式

每个智能体 `i` 有一个 actor `mu_i(o_i)`，把自己的观测映射为动作。每个智能体还有一个 critic `Q_i(x, a_1, ..., a_n)`，训练时能看到所有观测和所有动作。actor 依据 critic 的评估通过策略梯度来更新。

```
actor update:    grad_theta_i J = E[grad_theta mu_i(o_i) * grad_a_i Q_i(x, a_1..n) at a_i=mu_i(o_i)]
critic update:   TD on Q_i(x, a_1..n) given next-state joint estimate
```

为什么用 CTDE：训练时我们知道所有人的动作；我们利用这一点降低每个 critic 的方差。部署时，每个智能体只看到 `o_i`，调用 `mu_i(o_i)`。

失败模式：critic 随 N 个智能体增长（输入包含所有动作）。不做近似就无法扩展到约 10 个以上智能体。

> Each agent `i` has an actor `mu_i(o_i)` that maps its own observation to action. Each agent also has a critic `Q_i(x, a_1, ..., a_n)` that sees all observations and all actions during training. The actor is updated by policy gradient against the critic's evaluation.
> Why CTDE: at training time, we know everyone's actions; we use that to reduce variance in each critic. At deploy time, each agent only sees `o_i` and calls `mu_i(o_i)`.
> Failure mode: critics grow with N agents (input includes all actions). Does not scale past ~10 agents without approximations.

### QMIX (2018) — value decomposition · QMIX（2018）—— 价值分解

仅限合作场景。全局奖励是各智能体 Q 值的某个单调函数：

```
Q_tot(tau, a) = f(Q_1(tau_1, a_1), ..., Q_n(tau_n, a_n)),   df/dQ_i >= 0
```

单调性保证 `argmax_a Q_tot` 可以由每个智能体独立地取 `argmax_{a_i} Q_i` 计算得到。这正是你需要的**分散执行性质**。训练时，一个混合网络从各智能体的 Q 产出 `Q_tot`。

QMIX 在 SMAC 上赢的原因：合作式 StarCraft 微操作具有同构智能体、局部观测、全局奖励 —— 与价值分解完美契合。

失败模式：单调性约束很有局限；有些任务的奖励结构不可单调分解（一个智能体为团队牺牲自己）。扩展工作（QTRAN、QPLEX）放松了这一约束。

> Cooperative only. Global reward is the sum of a monotone function of per-agent Q-values.
> The monotonicity guarantees `argmax_a Q_tot` can be computed by each agent choosing `argmax_{a_i} Q_i` independently. That is **exactly the decentralized execution property** you need. At training time, a mixing network produces `Q_tot` from the per-agent Qs.
> Why QMIX wins on SMAC: cooperative StarCraft micro-management has homogeneous agents, local obs, global reward — perfect fit for value decomposition.
> Failure mode: the monotonicity constraint is restrictive; some tasks have reward structures that are not monotone decomposable (one agent sacrificing for the team). Extensions (QTRAN, QPLEX) relax this.

### MAPPO (2022) — the overlooked default · MAPPO（2022）—— 被忽视的默认选择

多智能体 PPO：带集中式价值函数的 PPO。每个智能体有自己的策略；所有智能体共享（或各自拥有）能看到完整状态的价值函数。Yu 等人 2022 年在五个基准上把 MAPPO 与 MADDPG、QMIX 及其扩展做了对比，发现：

- MAPPO 在 particle-world、SMAC、Google Research Football、Hanabi、MPE 上持平或击败 off-policy MARL 方法。
- 几乎不需要调超参数。
- 训练稳定；跨随机种子可复现。

社区在此之前低估了 on-policy MARL。2026 年，MAPPO 是合作式 MARL 的默认基线；任何新方法都必须先击败它。

> Multi-Agent PPO: PPO with a centralized value function. Each agent has its own policy; all agents share (or have per-agent) value functions that see the full state. Yu et al. 2022 benchmarked MAPPO against MADDPG, QMIX, and their extensions on five benchmarks and found:
> MAPPO matches or beats off-policy MARL methods on particle-world, SMAC, Google Research Football, Hanabi, MPE. Minimal hyperparameter tuning required. Stable training; reproducible across seeds.
> The community underrated on-policy MARL until this paper. In 2026, MAPPO is the default baseline for cooperative MARL; any new method must beat it.

### Why LLM-agent engineers should care · LLM 智能体工程师为什么要关心

三个直接用途：

1. **路由器训练。** 一个元智能体选择由哪个子智能体处理任务。这是一个有 N 个分散子智能体加一个集中路由器的 MARL 问题。MAPPO 合适。
2. **角色涌现。** 在生成式智能体仿真中，训练智能体随时间形成互补角色，这是一个伪装起来的 MARL 问题。QMIX 式价值分解在构造上就强制互补性。
3. **多智能体工具使用。** 当智能体共享工具并竞争预算时，用 CTDE 训练它们能得到尊重资源约束、可部署的本地策略。

实践提醒：2026 年，大多数生产 LLM 智能体系统是「提示」策略而不是「训练」策略。当你同时具备 (a) 大量交互数据、(b) 清晰的奖励信号、(c) 投入训练基础设施的意愿时，MARL 才会登场。

> Three direct uses: router training, role emergence, multi-agent tool use.
> Practical caveat: in 2026, most production LLM-agent systems prompt their policies rather than train them. MARL comes in when you have (a) lots of interaction data, (b) a clear reward signal, and (c) willingness to invest in training infrastructure.

### CTDE as a design pattern beyond RL · 超越 RL 的 CTDE 设计模式

即使不做训练，CTDE 也是有用的架构模式：

- *设计*时，假设团队完全可见。
- *运行*时，强制分散执行：每个智能体只看到 `o_i`。

这个模式迫使你把每个智能体的状态保持显式，并提前思考部分可观测性。很多生产多智能体系统悄悄假设处处共享状态 —— CTDE 纪律防止这一点。

> Even without training, CTDE is a useful architectural pattern: during *design*, assume full team visibility; at *runtime*, enforce decentralized execution: each agent sees only `o_i`.
> The pattern forces you to keep per-agent state explicit and to think about partial observability up front. Many production multi-agent systems silently assume shared state everywhere — CTDE discipline prevents that.

### The non-stationarity problem · 非平稳性问题

当多个智能体同时学习时，每个智能体的环境（包含其他智能体的策略）是非平稳的。经典单智能体 RL 的证明失效。本课的 MARL 算法全都在解决这个问题：

- MADDPG：全局 critic 看到所有动作，所以它的价值估计是平稳的。
- QMIX：价值分解把学习搬到了最优性有良定义的联合 Q 空间。
- MAPPO：集中式价值函数抑制其他智能体策略变化带来的方差。

在 LLM 智能体系统中，非平稳性表现为「我的智能体上个月还好好的，现在上游那个智能体一改，我的就出问题了」。用 CTDE 训练 MARL 是有原则的修复；提示层面的修复更快，但更不持久。

> When multiple agents learn simultaneously, each agent's environment (which includes others' policies) is non-stationary. Classical single-agent RL proofs break. The MARL algorithms in this lesson all address this.
> In LLM-agent systems, non-stationarity manifests as "my agent worked last month, now that other agent upstream changed, mine misbehaves." Training MARL with CTDE is the principled fix; prompt-level fixes are faster but less durable.

### What this lesson does NOT cover · 本课不覆盖的内容

训练真实网络是 Phase 09 的主题。本课构建脚本化策略版本，演示 CTDE、价值分解和集中式价值这几种模式，不做梯度更新。目标是在你拿起完整的 MARL 库（PyMARL、MARLlib、RLlib multi-agent）之前，先内化这些模式。

> Training actual networks is a Phase 09 topic. This lesson builds scripted-policy versions that demonstrate the CTDE, value-decomposition, and centralized-value patterns without gradient updates. The goal is to internalize the patterns before you pick up a full MARL library (PyMARL, MARLlib, RLlib multi-agent).

```figure
sw-ctde
```

## Build It · 动手造

`code/main.py` 在一个微型的双智能体合作网格世界上实现三个模式演示：

- 环境：4x4 网格上的 2 个智能体，一颗奖励 pellet。任一智能体到达 pellet 即得奖励 1，任务结束。
- `IndependentAgents` —— 每个智能体把其他智能体当成环境的一部分。基线。
- `MADDPGStyle` —— 集中式 critic 计算联合价值；actor 策略据此更新。脚本化的策略改进。
- `QMIXStyle` —— 带单调混合器的价值分解。
- `MAPPOStyle` —— 集中式价值函数；策略对照共享基线更新。

四者运行相同的 episode，并报告平均到达步数。CTDE 变体收敛到比独立基线更短的路径。

运行：

```
python3 code/main.py
```

预期输出：独立智能体平均约 6 步；CTDE 变体收敛到约 3.5 步（4x4 网格的最优是 3 步）。即使策略是脚本化的，模式差异也会显现出来。

> Expected output: independent agents take ~6 steps on average; CTDE variants converge toward ~3.5 steps (optimal for the 4x4 grid is 3). The pattern difference shows up despite scripted policies.

## Use It · 实战用法

`outputs/skill-marl-picker.md` 是一个为给定的多智能体任务挑选 MARL 算法的技能：合作 vs 竞争、同构 vs 异构、动作空间类型、规模、奖励信号。

> `outputs/skill-marl-picker.md` is a skill that picks a MARL algorithm for a given multi-agent task: cooperative vs competitive, homogeneous vs heterogeneous, action-space type, scale, reward signal.

## Ship It · 交付

生产环境用 MARL 的很少。真要用的时候：

- **从 MAPPO 开始。** 2022 年那篇论文把它确立为基线；先复现它，能省下数周追逐花哨方法的时间。
- **记录每个智能体的观测与动作流。** 没有按智能体的追踪，调试 MARL 毫无希望。
- **训练代码与执行代码分离。** CTDE 是纪律；让执行路径真的只看到 `o_i`。
- **奖励塑形警告。** MARL 对奖励设计极其敏感。塑形里一个协调 bug，智能体就会学会利用它。要跑对抗测试。
- **对 LLM 智能体**，优先考虑提示层面的策略。只有交互数据 + 奖励信号 + 基础设施三者齐备时，才投入 MARL 训练。

> MARL in production is rare. When you do use it: start with MAPPO; log every agent's observation and action stream; separate training code from execution code; beware reward shaping — run adversarial tests; for LLM agents, consider prompt-level policies first and only invest in MARL training when interaction data + reward signal + infrastructure are all present.

## Exercises · 练习

1. 运行 `code/main.py`。测量独立智能体与 MAPPO 式智能体的到达步数差。换到 6x6 网格上，这个差是变大还是变小？
2. 实现竞争变体：两个智能体、一颗 pellet，只有先到者获得奖励。哪种模式能干净地处理竞争？历史上是 MADDPG。
3. 阅读 MADDPG（arXiv:1706.02275）第 3 节。用自己的话把 critic 更新规则用伪代码符号化地写出来。
4. 阅读 MAPPO（arXiv:2103.01955）。作者为什么论证集中式价值 + PPO 在他们的基准上击败了 off-policy MARL？列出最有力的三个论点。
5. 把 CTDE 作为设计模式应用到一个假想的 LLM 智能体系统（例如研究智能体 + 摘要器 + 编码器）。设计时可得、而运行时不可得的联合信息是什么？

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| MARL | 「多智能体 RL」 | 面向多智能体系统的强化学习。 |
| CTDE | 「集中训练、分散执行」 | 用全局信息训练；用本地策略部署。 |
| MADDPG | 「Multi-Agent DDPG」 | CTDE，每个智能体的 critic 能看到所有观测 + 动作。 |
| QMIX | 「价值分解」 | 各智能体 Q 的单调混合。仅限合作。 |
| MAPPO | 「Multi-Agent PPO」 | 带集中式价值函数的 PPO。2026 年默认基线。 |
| Value decomposition | 「个体 Q 之和」 | 联合 Q 表示为各智能体 Q 的单调函数。 |
| Non-stationarity | 「会动的靶子」 | 其他智能体在学习，每个智能体的环境随之改变。MARL 的核心难题。 |
| On-policy / off-policy | 「从当前/回放数据学习」 | PPO 是 on-policy（MAPPO）；DDPG 和 Q-learning 是 off-policy。 |
| SMAC | 「StarCraft Multi-Agent Challenge」 | 合作式微操作基准；QMIX 的主场。 |

## Further Reading · 延伸阅读

- [Lowe et al. — Multi-Agent Actor-Critic for Mixed Cooperative-Competitive Environments](https://arxiv.org/abs/1706.02275) — MADDPG；NeurIPS 2017
- [Rashid et al. — QMIX: Monotonic Value Function Factorisation for Deep Multi-Agent Reinforcement Learning](https://arxiv.org/abs/1803.11485) — QMIX；ICML 2018
- [Yu et al. — The Surprising Effectiveness of PPO in Cooperative Multi-Agent Games](https://arxiv.org/abs/2103.01955) — MAPPO；NeurIPS 2022
- [BAIR blog post on MAPPO](https://bair.berkeley.edu/blog/2021/07/14/mappo/) — MAPPO 结果的一篇好读综述
- [SMAC repository](https://github.com/oxwhirl/smac) — StarCraft Multi-Agent Challenge
