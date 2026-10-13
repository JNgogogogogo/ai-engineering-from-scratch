# Swarm Optimization for LLMs (PSO, ACO) · 面向 LLM 的群优化（PSO、ACO）

> Bio-inspired optimization is making an LLM comeback. **LMPSO** (arXiv:2504.09247) uses PSO where each particle's velocity is a prompt and the LLM generates the next candidate; works well on structured-sequence outputs (math expressions, programs). **Model Swarms** (arXiv:2410.11163) treats each LLM expert as a PSO particle on a model-weight manifold and reports **13.3% average gain** over 12 baselines on 9 datasets with just 200 instances. **SwarmPrompt** (ICAART 2025) hybridizes PSO + Grey Wolf for prompt optimization. **AMRO-S** (arXiv:2603.12933) is ACO-inspired pheromone specialists for multi-agent LLM routing — **4.7x speedup**, interpretable routing evidence, quality-gated asynchronous update that decouples inference from learning. This lesson implements PSO on prompt parameter space and ACO on agent routing, measures why these classical algorithms fit the LLM era, and when they do not.

受生物启发的优化正在 LLM 领域回归。**LMPSO**（arXiv:2504.09247）使用 PSO，每个粒子的速度是一条提示（prompt），由 LLM 生成下一个候选；在结构化序列输出（数学表达式、程序）上效果很好。**Model Swarms**（arXiv:2410.11163）把每个 LLM 专家当作模型权重流形上的一个 PSO 粒子，报告在 9 个数据集上、仅用 200 个实例就取得对 12 个基线**平均 13.3% 的提升**。**SwarmPrompt**（ICAART 2025）混合 PSO + 灰狼优化（Grey Wolf）做提示优化。**AMRO-S**（arXiv:2603.12933）是 ACO 启发的信息素专家机制，用于多智能体 LLM 路由 —— **4.7 倍加速**、可解释的路由证据、把推理与学习解耦的质量门控异步更新。本课在提示参数空间上实现 PSO、在智能体路由上实现 ACO，分析这些经典算法为什么适配 LLM 时代，以及什么时候不适配。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 16 · 09 (Parallel Swarm Networks), Phase 16 · 14 (Consensus and BFT)
**Time:** ~75 minutes

## Problem · 问题

你有一个提示，在任务评测上得分 62%。你想改进它。天真的做法是无梯度的手工微调，扩展性很差。强化学习需要奖励信号和足够多的 rollout 才能训练。对提示做反向传播基本不可行 —— 提示是离散字符串，不是可微参数。

经典的仿生优化 —— PSO 面向连续搜索空间、ACO 面向路径选择 —— 恰好就是为这种场景设计的：无梯度、基于种群、单次评估便宜。把它们与 LLM 搭配来做无梯度搜索这一步，你就得到一个出奇实用的优化器。

同样的模式也适用于多智能体系统中的智能体*路由*。一条 ACO 式的信息素轨迹记录哪类任务上哪个智能体表现最好，让路由器利用这条轨迹，并让信息素衰减以便路由可以被重新发现。

> You have a prompt that scores 62% on your task eval. You want to improve it. The naive move is gradient-free manual tweaking, which scales badly. Reinforcement learning needs reward signals and enough rollouts to train. Backprop through prompts is not really possible — the prompt is a discrete string, not a differentiable parameter.
> Classical bio-inspired optimization — PSO for continuous search spaces, ACO for path selection — was designed exactly for this regime: gradient-free, population-based, cheap per evaluation. Pair them with LLMs for the gradient-free search step, and you get a surprisingly practical optimizer.
> The same patterns apply to agent *routing* in multi-agent systems. An ACO-style pheromone trail records which agent worked best on which task-type, lets the router exploit the trail, and decays pheromones so routes can be rediscovered.

## Concept · 概念

### PSO refresher (Kennedy & Eberhart 1995) · PSO 回顾（Kennedy & Eberhart 1995）

粒子群优化（Particle Swarm Optimization）：一群粒子在连续搜索空间中运动。每个粒子有位置 `x_i` 和速度 `v_i`。每次迭代：

```
v_i <- w * v_i + c1 * r1 * (p_best_i - x_i) + c2 * r2 * (g_best - x_i)
x_i <- x_i + v_i
evaluate fitness(x_i)
update p_best_i if improved
update g_best if global best
```

其中 `p_best` 是粒子自己的历史最优，`g_best` 是群体最优，`w, c1, c2` 是惯性 + 认知 + 社会权重，`r1, r2` 是随机因子。

> Particle Swarm Optimization: population of particles in a continuous search space. Each particle has position `x_i` and velocity `v_i`.
> Where `p_best` is particle's own best, `g_best` is swarm's best, `w, c1, c2` are inertia + cognitive + social weights, `r1, r2` are random factors.

### PSO on LLM outputs — LMPSO · PSO 用于 LLM 输出 —— LMPSO

arXiv:2504.09247 把 PSO 改造用于 LLM 生成的结构化输出（数学表达式、程序）。每个粒子是一个候选输出。速度是一条*提示*，描述如何把当前输出向个人/全局最优修改。LLM 根据这条速度提示生成新输出。速度的「惯性」是类似「做小的增量式修改」这样的提示。

它在以下情况效果好：
- 输出是结构化的（可解析、可评估）。
- 适应度是自动的（跑测试、算术求值）。
- 种群小（约 10-30 个粒子），LLM 调用总量可控。

当适应度需要人工评审时，它效果不好 —— 每次迭代的成本会变得难以承受。

> arXiv:2504.09247 adapts PSO for LLM-generated structured outputs (math expressions, programs). Each particle is a candidate output. Velocity is a *prompt* that describes how to modify the current output toward the personal/global best. The LLM generates the new output from the velocity prompt. The "inertia" of the velocity is a prompt like "make small incremental changes."
> It does not work well when fitness needs human review — the per-iteration cost becomes prohibitive.

### Model Swarms · 模型群

arXiv:2410.11163 把 PSO 从输出层搬到了*模型*层。每个「粒子」是一个专家 LLM（参数）。群体通过无梯度更新把参数移向集体最优。报告结果：9 个数据集、每次迭代仅 200 个实例，对 12 个基线平均提升 13.3%。

关键洞察是：LLM 专家模型本来就处在同一个共享参数流形上的相邻位置（adapter 权重、LoRA delta）。在这个低维子空间上跑 PSO 既便宜又有效。

> arXiv:2410.11163 takes PSO off the output layer and into the *model* layer. Each "particle" is an expert LLM (parameters). The swarm moves the parameters toward the collective best via a gradient-free update. Reported: 13.3% average gain over 12 baselines on 9 datasets, with just 200 instances per iteration.
> The key insight is that LLM expert models are already nearby in a shared parameter manifold (adapter weights, LoRA deltas). PSO on this low-dimensional subspace is cheap and effective.

### ACO refresher (Dorigo 1992) · ACO 回顾（Dorigo 1992）

蚁群优化（Ant Colony Optimization）：蚂蚁在图上穿行；每条路径有一条信息素轨迹。蚂蚁的移动概率按信息素强度加权。完成任务的蚂蚁按解质量成比例地沉积信息素。信息素随时间衰减。

> Ant Colony Optimization: ants traverse a graph; each path has a pheromone trail. Ant move probabilities weight by pheromone strength. Ants that complete the task deposit pheromone proportional to solution quality. Pheromone decays over time.

### AMRO-S — ACO for agent routing · AMRO-S —— 用于智能体路由的 ACO

arXiv:2603.12933 用 ACO 做多智能体路由。每个任务类型是一个「目的地」；每个智能体是一条可能的路径。产生好输出的路径信息素增强。关键贡献：

- **可解释的路由证据。** 信息素强度是人可读的信号。
- **质量门控异步更新。** 信息素只在质量检查通过后更新，把推理与学习解耦。
- 多智能体路由基准上 **4.7 倍加速**。

质量门控很关键：没有它，快但错的智能体会累积信息素，系统会锁死在坏路由上。

> arXiv:2603.12933 uses ACO for multi-agent routing. Each task-type is a "destination"; each agent is a possible route. Pheromones strengthen routes that produce good outputs. Key contributions: interpretable routing evidence; quality-gated asynchronous update; 4.7x speedup on the multi-agent routing benchmark.
> The quality gate matters: without it, fast-but-wrong agents accrue pheromone, and the system locks in on bad routes.

### When to use PSO / ACO for LLMs · 什么时候对 LLM 用 PSO / ACO

**用 PSO 当：**
- 搜索空间连续，或可映射到连续参数（提示嵌入、LoRA 权重、数值生成参数）。
- 适应度便宜且自动。
- 种群可以小（10-30）。

**用 ACO 当：**
- 你面对的是路由或路径选择问题。
- 决策随时间自我强化（同类任务反复出现）。
- 你需要路由决策的可解释证据。

**两种都别用当：**
- 适应度需要人工评审（每次迭代成本太高）。
- 搜索空间是 PSO 覆盖不了的离散组合结构（改用遗传算法）。
- 实时决策要求严格延迟（相对单遍启发式方法，PSO/ACO 收敛慢）。

> **Use PSO when:** search space is continuous or maps to continuous parameters; fitness is cheap and automatic; population can be small (10-30). **Use ACO when:** you have a routing or path-selection problem; decisions reinforce over time; you need interpretable evidence for routing decisions. **Do not use either when:** fitness requires human review; the search space is discrete and combinatorial in a way that PSO does not cover; real-time decisions need strict latency.

### Why bio-inspired still wins · 为什么仿生方法仍然能打

基于梯度的方法需要可微信号。LLM 输出和路由决策都不是天然可微的。伪梯度方法（强化学习路由器、DPO 式提示调优器）可行但训练昂贵。

PSO 和 ACO 只需要一个*评估器*函数。只要你能给候选输出或路由决策打分，你就能在这个空间上做优化。这把适用门槛拉低了很多。

> Gradient-based methods need differentiable signals. LLM outputs and routing decisions are not trivially differentiable. Pseudo-gradient methods (reinforcement-learned routers, DPO-style prompt tuners) work but need expensive training.
> PSO and ACO need only an *evaluator* function. If you can score a candidate output or a routing decision, you can optimize over the space. That makes the bar for applicability much lower.

### Practical limits · 实践限制

- **种群预算。** N 个粒子 × T 次迭代 × 单次评估成本。LLM 评估约 $0.02/次调用时，一个 20 粒子 PSO 跑 50 次迭代约 $20。要提前规划。
- **探索 vs 利用。** 信息素衰减率与 PSO 惯性相互制衡；衰减太快 → 忘掉解；太慢 → 卡在早期局部最优上。
- **灾难性漂移。** 两种算法都可能在收敛后因适应度地形变化（新数据分布）而发散。监控最优适应度的稳定性。

```figure
swarm-stigmergy
```

> **Population budget.** N particles × T iterations × per-eval cost. For LLM evals at ~$0.02 / call, a 20-particle PSO running 50 iterations costs ~$20. Plan accordingly.
> **Exploration vs exploitation.** Pheromone decay rate and PSO inertia trade off; too fast decay → forget solutions; too slow → stuck on early local optima.
> **Catastrophic drift.** Both algorithms can converge and then diverge if fitness landscape shifts (new data distribution). Monitor best-fitness stability.

## Build It · 动手造

`code/main.py` 实现：

- `LMPSO` —— 在数值提示参数（temperature、top_k 权重）上跑 PSO。每个粒子的「LLM 生成」用脚本化的适应度函数模拟。运行 30 次迭代并展示 g_best 收敛。
- `AMRO_S` —— ACO 式路由。3 个智能体、4 种任务类型、信息素矩阵、100 个路由任务。随时间打印（任务类型 → 智能体选择）分布，展示轨迹的形成。
- 对比：同一任务流上随机路由 vs ACO 路由。测量质量与延迟。

运行：

```
python3 code/main.py
```

预期输出：
- LMPSO：g_best 适应度在 30 次迭代内从随机提升到接近最优。
- AMRO-S：信息素表在每个任务类型上稳定到正确的智能体；ACO 路由在质量上比随机路由高约 30-40%，同时还降低延迟（重试更少）。

> Expected output: LMPSO — g_best fitness improves from random to near-optimal over 30 iterations. AMRO-S — pheromone table stabilizes on the right agent per task-type; ACO routing beats random by ~30-40% on quality and also reduces latency (fewer retries).

## Use It · 实战用法

`outputs/skill-swarm-optimizer.md` 帮你在 PSO、ACO、遗传算法和基于梯度的优化器之间做选择，用于 LLM / 智能体优化问题。

> `outputs/skill-swarm-optimizer.md` helps choose between PSO, ACO, genetic algorithms, and gradient-based optimizers for LLM / agent optimization problems.

## Ship It · 交付

- **从小规模开始。** 10-20 个粒子，20-50 次迭代。只有收敛曲线显示明确收益时才扩大规模。
- **每次迭代记录信息素或 g_best。** 没有轨迹记录，调试群优化器非常痛苦。
- **给更新加质量门控。** 对 ACO 路由尤其如此：快而错的智能体绝不能累积信息素。
- **分布漂移时重置衰减。** 评测分布改变时，老化的信息素已经失效；临时重置或加倍衰减率。
- **给单次迭代成本设上限。** 输出每次迭代的成本指标。一次迭代花 $500、收益只有 0.5% 的 PSO 是不可交付的。

> **Start small.** 10-20 particles, 20-50 iterations. Scale up only if the convergence curve shows clear gain.
> **Log pheromones or g_best per iteration.** Debugging swarm optimizers without a trail is painful.
> **Quality-gate updates.** Especially for ACO routing: fast-and-wrong agents must not accrue pheromone.
> **Reset decay on distribution shift.** When your eval distribution changes, aged pheromones are stale; reset or double the decay rate temporarily.
> **Cap the per-iteration cost.** Emit a cost-per-iteration metric. PSO that costs $500 / iteration and gains 0.5% is not shippable.

## Exercises · 练习

1. 运行 `code/main.py`。观察 LMPSO 收敛。把种群规模改为 5、10、20、50。规模多大时收敛时间趋于饱和？
2. 实现「灾难性漂移」实验：第 30 次迭代后更换适应度函数。PSO 多快能适应？重置 `p_best` 有帮助吗？
3. 给 AMRO-S 加质量门控：只有评测得分 > 0.7 的运行才沉积信息素。与无门控版本相比，收敛如何变化？
4. 阅读 LMPSO（arXiv:2504.09247）。把论文的「速度即提示」映射回你的数值速度。仿真丢失了什么、保留了什么？
5. 阅读 AMRO-S（arXiv:2603.12933）。实现解耦的「推理快速通道」与异步信息素更新。持续负载下系统延迟如何变化？

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| PSO | 「粒子群优化」 | Kennedy-Eberhart 1995。基于种群的无梯度优化器。 |
| ACO | 「蚁群优化」 | Dorigo 1992。通过信息素轨迹做路径/路由优化。 |
| LMPSO | 「用 LLM 生成的 PSO」 | arXiv:2504.09247。速度是一条提示；LLM 产出候选。 |
| Model Swarms | 「专家权重上的 PSO」 | arXiv:2410.11163。在模型参数子空间上做无梯度更新。 |
| AMRO-S | 「智能体路由的 ACO」 | arXiv:2603.12933。任务类型 × 智能体上的信息素矩阵。 |
| p_best / g_best | 「个人/全局最优」 | 迄今发现的粒子级与群体级最优解。 |
| Pheromone | 「路由记忆」 | 边上的强度；随时间衰减；按质量沉积。 |
| Quality-gated update | 「只从好的运行学习」 | 信息素沉积以质量检查通过为条件。 |
| Catastrophic drift | 「分布漂移」 | 适应度地形改变；旧的 p_best 与信息素失效。 |

## Further Reading · 延伸阅读

- [Kennedy & Eberhart — Particle Swarm Optimization](https://ieeexplore.ieee.org/document/488968) — 1995 年 PSO 原始论文
- [Dorigo — Ant Colony Optimization](https://www.aco-metaheuristic.org/about.html) — 1992 年 ACO 奠基工作
- [LMPSO — Language Model Particle Swarm Optimization](https://arxiv.org/abs/2504.09247) — 面向结构化 LLM 输出的 PSO
- [Model Swarms — gradient-free LLM expert optimization](https://arxiv.org/abs/2410.11163) — 模型权重子空间上的 PSO
- [AMRO-S — ant-colony multi-agent routing](https://arxiv.org/abs/2603.12933) — 带质量门控的信息素驱动路由
