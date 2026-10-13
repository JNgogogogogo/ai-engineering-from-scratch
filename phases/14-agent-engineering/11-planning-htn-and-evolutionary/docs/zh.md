# Planning with HTN and Evolutionary Search · HTN 规划与演化搜索

> Symbolic planning handles the cases where the plan is provably correct. Evolutionary code search handles the cases where the fitness function is machine-checkable. ChatHTN (2025) and AlphaEvolve (2025) show what each unlocks when paired with an LLM.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 02 (ReWOO and Plan-and-Execute)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 解释分层任务网络（Hierarchical Task Networks, HTN）：任务、方法、操作符、前置条件、效果
- 描述 ChatHTN 的混合回路——符号搜索 + LLM 兜底分解
- 解释 AlphaEvolve 的演化回路，以及为什么它只有在配了程序化评估器时才成立
- 用 stdlib 实现一个玩具 HTN 规划器，再加一个玩具演化搜索

> Explain Hierarchical Task Networks: tasks, methods, operators, preconditions, effects.
> Describe ChatHTN's hybrid loop — symbolic search with LLM fallback decomposition.
> Explain AlphaEvolve's evolutionary loop and why it only works with a programmatic evaluator.
> Implement a toy HTN planner plus a toy evolutionary search in stdlib.

## The Problem · 问题在哪

ReWOO（Lesson 02）、Plan-and-Execute 和 ReAct 覆盖了大部分 agent 规划。有两类场景它们覆盖不好：

1. **需要可证明正确性的计划。** 排程、航路规划、合规工作流——计划必须由构造保证可靠（sound by construction）。一个偶尔幻觉出多余步骤的流畅 LLM 计划是不可接受的。
2. **有机器可查适应度函数的优化。** 矩阵乘法、排程启发式、编译器 pass——目标不是「一个正确的计划」，而是「最好的计划」。

HTN 规划和 AlphaEvolve 解决的是两个不同的问题。两者都把 LLM 用作放大器，而不是替代品。

> 1. **Plans with provable correctness.** Scheduling, flight pathing, compliance workflows — the plan must be sound by construction. A fluent LLM plan that sometimes hallucinates a step is unacceptable.
> 2. **Optimizations with a machine-checkable fitness function.** Matrix multiplication, scheduling heuristics, compiler passes — the goal is not "a correct plan" but "the best plan."
> HTN planning and AlphaEvolve solve the two different problems. Both use LLMs as amplifiers, not replacements.

## The Concept · 概念

### Hierarchical Task Networks · 分层任务网络

一个 HTN 包含：

- **任务（Tasks）** — 复合任务（待分解）和原语任务（可直接执行）。
- **方法（Methods）** — 把复合任务分解成子任务的方式，带前置条件。
- **操作符（Operators）** — 带前置条件和效果的原语动作。
- **状态（State）** — 一组事实。

规划：给定一个目标任务和一个初始状态，找到一个分解成原语操作符的序列，使各操作符的前置条件依次得到满足。

HTN 比 LLM 老得多，而且至今仍是「可证明正确的计划」的参照标准。

> Planning: given a goal task and an initial state, find a decomposition into primitive operators whose preconditions are satisfied in sequence.
> HTN is older than LLMs and still the reference for provably-correct plans.

### ChatHTN (Gopalakrishnan et al., 2025) · ChatHTN：符号 + LLM 混合规划

ChatHTN（arXiv:2505.11814）把符号 HTN 与 LLM 查询交错进行：

1. 先尝试用已有方法分解当前复合任务。
2. 如果没有方法适用，就去问 LLM：「在状态 `s` 下你会怎么分解 `task`？」
3. 把 LLM 的回答翻译成候选子任务。
4. 对照操作符 schema 做校验；拒绝非法分解。
5. 递归。

论文的核心主张：产出的每个计划都可证明可靠，因为 LLM 的建议只作为候选分解进入，从不直接修改计划。符号层掌管正确性；LLM 负责扩充方法库。

在线方法学习（online method learning，OpenReview `gwYEDY9j2x`，2025 年后续工作）加了一个学习器，通过回归把 LLM 产出的分解泛化成方法——把 LLM 查询频率最多砍掉 75%。

> The paper's central claim: every plan produced is provably sound because LLM suggestions only enter as candidate decompositions, never as direct plan edits. The symbolic layer owns correctness; the LLM expands the method library.
> Online method learning (OpenReview `gwYEDY9j2x`, 2025 follow-up) adds a learner that generalizes LLM-produced decompositions by regression — cutting LLM query frequency up to 75%.

### AlphaEvolve (Novikov et al., 2025) · AlphaEvolve：演化代码搜索

AlphaEvolve（arXiv:2506.13131，DeepMind，2025 年 6 月）是另一种野兽：由 Gemini 2.0 Flash/Pro 模型组合编排的演化代码搜索。

回路：

1. 从一个种子程序 + 一个程序化评估器（返回适应度分数）开始。
2. LLM 组合提出变异。
3. 变异跑过评估器。
4. 保留最好的；继续变异。

已发表的战绩：

- 56 年来首次改进 Strassen 的 4x4 复矩阵乘法（48 次标量乘法）。
- 通过一个 Borg 调度启发式为 Google 找回 0.7% 的算力。
- 在一个前沿负载上把 FlashAttention 提速 32%。

硬约束：适应度函数必须机器可查。对散文式的答案做演化搜索是不会收敛的。

> AlphaEvolve (arXiv:2506.13131, DeepMind, June 2025) is a different beast: evolutionary code search orchestrated by a Gemini 2.0 Flash/Pro ensemble.
> First improvement over Strassen for 4x4 complex matrix multiplication in 56 years (48 scalar multiplications).
> The hard constraint: the fitness function must be machine-checkable. Evolutionary search over prose answers does not converge.

### When to use which · 什么时候用哪个

| 问题类别 | 用什么 | 为什么 |
|---------------|-----|-----|
| 带硬约束的排程 | HTN + ChatHTN | 可证明的可靠性 |
| 编译器优化 | AlphaEvolve | 机器可查的适应度 |
| 多步任务执行 | ReAct / ReWOO | LLM 在环，无形式化保证 |
| 带测试的代码改进 | AlphaEvolve | 测试就是评估器 |
| 受政策约束的自动化 | HTN | 前置条件编码了政策 |

### Where this pattern goes wrong · 这个模式哪里会出错

- **有 HTN 没操作符。** 没有前置条件/效果 schema，「可靠性」主张就塌了。ChatHTN 的「LLM 建议分解」依赖 schema 来拒绝非法动作。
- **有 AlphaEvolve 没有真评估器。** 「问 LLM 这段代码是不是更好」不是适应度函数。评估器必须是确定性的、快的。
- **过度工程。** 大多数 agent 任务两者都不需要。先伸手拿 ReAct 或 ReWOO。

```figure
htn-tree-expand
```

> **HTN without operators.** Without precondition/effect schemas the soundness claim collapses. ChatHTN's "LLM suggests decomposition" requires the schema to reject invalid moves.
> **AlphaEvolve without a real evaluator.** "Ask the LLM if the code is better" is not a fitness function. The evaluator must be deterministic and fast.
> **Over-engineering.** Most agent tasks don't need either. Reach for ReAct or ReWOO first.

## Build It · 动手造

`code/main.py` 实现两个玩具：

- 一个 stdlib HTN 规划器，带操作符、方法、前置条件、效果，以及一个在没有方法匹配复合任务时接管的 `LLMFallback`。这个「LLM」是一个脚本化的分解器，所以规划器可以离线运行。
- 一个针对算术程序的 stdlib 演化搜索：让表达式的输出在一组测试上最小化 `|f(x) - target|`。评估器是确定性的。

运行：

```
python3 code/main.py
```

轨迹展示了 HTN 规划器分解一个复合任务（中途触发一次 LLM 兜底），以及演化回路收敛到目标表达式。

> The trace shows the HTN planner decomposing a compound task (with a mid-plan LLM fallback) and the evolutionary loop converging on a target expression.

## Use It · 实战用法

- **HTN 规划器** — `pyhop`、`SHOP3`，或者为了领域特定的政策执行自己造一个。
- **ChatHTN** — 研究代码；这个模式（符号 + LLM 兜底）可以干净地移植到任何 HTN 规划器上。
- **AlphaEvolve** — DeepMind 论文；这个模式（模型组合 + 评估器）可复现。OpenEvolve 和类似的开源分支正在涌现。
- **Agent 框架** — 目前没有一个内置一等公民的 HTN 或 AlphaEvolve。把它建成一个子 agent 或后台 worker。

> **HTN planners** — `pyhop`, `SHOP3`, or build your own for domain-specific policy enforcement.
> **ChatHTN** — research code; the pattern (symbolic + LLM fallback) ports cleanly to any HTN planner.
> **AlphaEvolve** — DeepMind paper; the pattern (ensemble + evaluator) is reproducible. OpenEvolve and similar open-source forks are emerging.
> **Agent frameworks** — none ship first-class HTN or AlphaEvolve yet. Build it as a subagent or a background worker.

## Ship It · 交付

`outputs/skill-hybrid-planner.md` 生成一个混合规划器脚手架（HTN 或演化式），并把 LLM 的角色明确限定好。

> `outputs/skill-hybrid-planner.md` generates a hybrid planner scaffold (HTN or evolutionary) with the LLM role explicitly scoped.

## Exercises · 练习

1. 给 HTN 规划器加回溯：当某个操作符的后置条件在运行时失败，回滚并尝试下一个方法。
2. 给 ChatHTN 加一个 LLM 方法缓存：当 LLM 在状态模式 `P` 下分解了任务 `T`，把结果存下来。下一次调用先重查方法库。
3. 把演化搜索的评估器换成真实的测试套件。演化出一个能通过 20 个测试用例的排序函数；报告收敛所需的代数。
4. 读 AlphaEvolve 的评估器设计笔记。为你关心的领域（SQL 查询优化、测试套件最小化、部署 YAML）设计一个评估器。
5. 打组合拳：用 HTN 把复合任务分解成子任务，再对每个子任务的原语操作符跑演化搜索。哪里出彩，哪里过度工程？

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| HTN | 「分层规划器」 | 带操作符、前置条件、效果的任务分解 |
| Method（方法） | 「分解规则」 | 把复合任务拆成子任务的方式 |
| Operator（操作符） | 「原语动作」 | 带前置条件和效果的具体步骤 |
| ChatHTN | 「LLM + HTN」 | 符号规划器在没有方法匹配时去问 LLM |
| AlphaEvolve | 「演化代码搜索」 | LLM 组合变异代码；确定性评估器做选择 |
| Fitness function（适应度函数） | 「评估器」 | 对输出的确定性、机器可查的评分 |
| Online method learning（在线方法学习） | 「缓存的 LLM 分解」 | 存储并泛化 LLM 计划，以削减查询成本 |

## Further Reading · 延伸阅读

- [Gopalakrishnan et al., ChatHTN (arXiv:2505.11814)](https://arxiv.org/abs/2505.11814) —— 符号 + LLM 混合规划器
- [Novikov et al., AlphaEvolve (arXiv:2506.13131)](https://arxiv.org/abs/2506.13131) —— 用 LLM 变异的演化代码搜索
- [Anthropic, Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) —— 什么时候该上规划器，什么时候简单回路就够
