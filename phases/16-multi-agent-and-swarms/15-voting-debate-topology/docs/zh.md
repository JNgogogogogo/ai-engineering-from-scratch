# 投票、自一致性与辩论拓扑（Voting, Self-Consistency, and Debate Topology）

> 最便宜的聚合方式：采样 N 个独立 agent，多数投票。Wang et al. 2022 的自一致性（self-consistency）用一个模型采样 N 次做到了这一点。多 agent 用**异构**（heterogeneous）agent 加以扩展以摆脱单一化（monoculture）——不同的模型、不同的提示词、不同的温度、不同的上下文。在多数投票之外，辩论拓扑同样关键：MultiAgentBench（arXiv:2503.01935, ACL 2025）评估了星型 / 链式 / 树形 / 图状协作，发现**图状最适合研究类任务**，并且在超过约 4 个 agent 后出现「协作税」（coordination tax）。AgentVerse（ICLR 2024）记录了两种涌现模式——志愿行为（volunteer behaviors）与从众行为（conformity behaviors）——而从众既是特性（达成共识）也是风险（群体思维，第 24 课）。本课绘制拓扑空间的全图，逐一构建每种变体，并度量协作税。

> The cheapest aggregation: sample N independent agents, majority-vote. Wang et al. 2022 self-consistency did this with one model sampled N times. Multi-agent extends it with **heterogeneous** agents to escape monoculture — different models, different prompts, different temperatures, different contexts. Beyond majority vote, debate topology matters: MultiAgentBench (arXiv:2503.01935, ACL 2025) evaluated star / chain / tree / graph coordination and found **graph best for research**, with a "coordination tax" past ~4 agents. AgentVerse (ICLR 2024) documents two emergent patterns — volunteer behaviors and conformity behaviors — and conformity is both a feature (finding consensus) and a risk (groupthink, Lesson 24). This lesson maps the topology space, builds each variant, and measures the coordination tax.

**Type:** Learn + Build
**Languages:** Python（stdlib）
**Prerequisites:** Phase 16 · 07（Society of Mind and Debate）、Phase 16 · 14（Consensus and BFT）
**Time:** ~75 分钟

## Problem · 问题

辩论可以提高准确率（Du et al., arXiv:2305.14325），也可以让它下降。辩论是否有帮助取决于四个结构性选择：

1. 谁和谁说话（拓扑）。
2. 多少轮（Du 2023：轮数和 agent 数各自独立地产生影响）。
3. agent 是否异构（不同的基础模型打破单一化）。
4. 是否存在对抗性声音（钢人论证 vs. 稻草人论证）。

把「跑 5 个 agent 然后投票」硬套在任务上的团队，常常比单个 agent 还退步。这些失败不是随机的，它们追踪拓扑与异构性。本课就是那张拓扑地图。

> Debate can improve accuracy (Du et al., arXiv:2305.14325). It can also degrade it. Whether debate helps depends on four structural choices:
> 1. Who talks to whom (topology).
> 2. How many rounds (Du 2023: both rounds and agents matter independently).
> 3. Whether agents are heterogeneous (different base models break monoculture).
> 4. Whether an adversarial voice is present (steel-manning vs. straw-manning).
> Teams that bolt "run 5 agents and vote" onto a task often regress vs. a single agent. The failures are not random. They track topology and heterogeneity. This lesson is the topology map.

## Concept · 概念

### Self-consistency, the single-model baseline · 自一致性：单模型基线

Wang et al. 2022（"Self-Consistency Improves Chain of Thought Reasoning"）在温度 > 0 下把同一个模型采样 N 次，对推理路径的答案做多数投票。GSM8K 上的结果：N=40 个样本相比单次贪心解码有大幅提升。自一致性是多 agent 投票的单 agent 前身。

局限：自一致性只用一个基础模型。错误按构造就是相关的。如果模型有系统性偏差，全部 N 个样本都共享它。

> Wang et al. 2022 ("Self-Consistency Improves Chain of Thought Reasoning") sampled the same model N times at temperature > 0 and majority-voted on reasoning-path answers. The result on GSM8K: substantial gains with N=40 samples over a single greedy decode. Self-consistency is the single-agent precursor to multi-agent voting.
> Limit: self-consistency uses one base model. Errors are correlated by construction. If the model has a systematic bias, all N samples share it.

### Multi-agent vote, the heterogeneous extension · 多 agent 投票：异构扩展

把 N 个样本换成 N 个*不同的* agent。不同的基础模型（Claude、GPT、Llama）、不同的提示词、不同的工具访问权限。好处：错误不相关。代价：不同 agent 成本不同；协调它们增加开销。

异构辩论在 2026 年的准官方名称是 **A-HMAD** —— Adversarial Heterogeneous Multi-Agent Debate（对抗性异构多 agent 辩论）。这个名字没有被普遍采用，但论文用它指「不同模型进行辩论，从而减少单一化崩溃带来的相关错误」。

> Replace N samples with N *different* agents. Different base models (Claude, GPT, Llama), different prompts, different tool access. The benefit: uncorrelated errors. The cost: different agents cost different amounts; coordinating them adds overhead.
> The canonical 2026 name for heterogeneous debate is **A-HMAD** — Adversarial Heterogeneous Multi-Agent Debate. Not universally adopted, but papers use the term for "different models debate, which reduces correlated errors from monoculture collapse."

### The four topologies · 四种拓扑

```
star                chain               tree                graph

    ┌─A─┐           A─B─C─D         ┌──A──┐              A───B
    │   │                           │     │              │ × │
    B   C                           B     C              D───C
    │   │                          / \   / \
    D   E                         D   E F   G           (fully connected)
```

Star（星型）：一个中心，其他所有 agent 只和中心说话。等价于没有后门的 supervisor-worker。
Chain（链式）：线性，每个 agent 看到前一个的输出。类似流水线。
Tree（树形）：分层，分层 agent 系统使用（第 06 课）。
Graph（图状）：任意到任意。包括全连接 clique 和任意 DAG。

> Star: one hub, all others talk only to hub. Equivalent to supervisor-worker without back-channel.
> Chain: linear, each agent sees the prior one's output. Pipeline-like.
> Tree: hierarchical, used by hierarchical agent systems (Lesson 06).
> Graph: any-to-any. Includes fully-connected clique and arbitrary DAGs.

### The coordination tax (MultiAgentBench) · 协作税（MultiAgentBench）

MultiAgentBench（MARBLE, ACL 2025, arXiv:2503.01935）在包括研究、编码和规划的任务套件上对星型、链式、树形、图状做了基准测试。关键测量结果：

- **Graph（图状）**拓扑在研究类任务上获胜。信息任意流动；agent 可以互相批评。
- **Star（星型）**在快速作答的事实型任务上获胜。中心负责过滤与汇总。
- **Chain（链式）**在逐步流水线（分阶段精炼）上获胜。
- **协作税**在图状拓扑下超过约 4 个 agent 后出现。墙钟时间与 token 成本的增长快于质量的增长。

4-agent 的天花板是经验性的，不是根本性的。它反映的是 2026 年 LLM 的上下文容量：每个 agent 的上下文被同伴的输出填满，一旦所有人都能看到所有人，增加第 N+1 个 agent 的边际价值就下降了。

> MultiAgentBench (MARBLE, ACL 2025, arXiv:2503.01935) benchmarked star, chain, tree, graph on a task suite including research, coding, and planning. Key measured results:
> - **Graph** topology wins on research tasks. Information flows any-to-any; agents can critique each other.
> - **Star** wins on fast-answer factual tasks. Hub filters and consolidates.
> - **Chain** wins on stepwise pipelines (staged refinement).
> - **Coordination tax** appears past ~4 agents in graph topology. Wall-clock and token cost grow faster than quality.
> The 4-agent ceiling is empirical, not fundamental. It reflects 2026 LLM context capacity: each agent's context fills with peers' outputs, and marginal value of adding agent N+1 drops once everyone can see everyone.

### Multi-Agent Debate Strategies ("Should we be going MAD?") · 多 agent 辩论策略

arXiv:2311.17371 是 2023 年对 MAD（多 agent 辩论）策略的综述。被他人重复验证的关键发现：那些在*结构上*与自一致性相似（独立采样 + 聚合）的 MAD 变体，在相同预算下常常跑不过自一致性。MAD 最有用的场景是：agent 真正异构，且辩论具有对抗性结构（有一个 agent 唱反调）。

> arXiv:2311.17371 is the 2023 survey of MAD strategies. Key finding replicated by others: MAD variants that are *structurally similar* to self-consistency (independent sampling + aggregation) often underperform self-consistency when using the same budget. MAD helps most when agents are genuinely heterogeneous and the debate has adversarial structure (one agent argues against).

### AgentVerse emergent patterns · AgentVerse 的涌现模式

AgentVerse（ICLR 2024, https://proceedings.iclr.cc/paper_files/paper/2024/file/578e65cdee35d00c708d4c64bce32971-Paper-Conference.pdf）记录了多 agent 辩论中即便没有显式设计也会涌现的两种行为：

- **志愿（Volunteer）。** 一个 agent 主动请缨（「我可以走下一步」），无人要求。有用：它把子任务分配给最能胜任的 agent。
- **从众（Conformity）。** 一个 agent 调整自己的立场去迎合某个批评者，哪怕批评者是错的。这就是辩论版谄媚（第 14 课）。

从众正是「辩论到达成一致」奖励恃强凌弱者的原因。有界轮次加独立裁判可以缓解。

> AgentVerse (ICLR 2024, https://proceedings.iclr.cc/paper_files/paper/2024/file/578e65cdee35d00c708d4c64bce32971-Paper-Conference.pdf) documents two behaviors that emerge from multi-agent debate even without explicit design:
> - **Volunteer.** An agent offers help ("I can take the next step") unprompted. Useful: it allocates work to the most-capable agent for a subtask.
> - **Conformity.** An agent adjusts its stance to match a critic, even when the critic is wrong. This is the debate-equivalent of sycophancy (Lesson 14).
> Conformity is why debate-until-agreement rewards bullies. Bounded rounds with a separate judge mitigate.

### Heterogeneity: the actual knob that moves accuracy · 异构性：真正撬动准确率的旋钮

2024-2026 年实践文献中的一个模式：把 N 个 agent 中的一个换成不同基础模型，带来的准确率提升比把 N 加 1 更大。直觉就是单一化——每一个新的独立错误来源，都比一个额外的相关样本更值钱。

推到极限：异构胜过数量。在有干净真值的大多数任务上，三个不同的模型胜过同一个模型的五个副本。

> A 2024-2026 pattern in the practical literature: swapping one of your N agents for a different base model gives a bigger accuracy bump than increasing N by 1. The intuition is monoculture — each new independent-error source is worth more than an additional correlated sample.
> In the limit, heterogeneity beats numerosity. Three different models beat five copies of one model on most tasks that have clean ground truth.

### Jury methods · 陪审团方法

Sibyl 框架（见 Minsky-LLM 文献引用）形式化了一种「陪审团」——一小组专门化 agent，在每个阶段通过投票精炼答案。与简单多数投票不同，陪审团有角色分工：一个 agent 交叉质询，一个提供上下文，一个给合理性打分。陪审团方法是简单投票（便宜、易单一化）与完整 MAD（昂贵、易从众）之间的中间点。

> The Sibyl framework (cited in Minsky-LLM literature) formalizes a "jury" — a small set of specialized agents that refine answers by voting at each stage. Unlike plain majority vote, a jury has roles: one agent cross-examines, one supplies context, one scores plausibility. Jury methods are a midpoint between plain vote (cheap, monoculture-prone) and full MAD (expensive, conformity-prone).

### When vote-with-debate dominates · 投票加辩论占优的场景

- 问题有真值（事实、数学、代码行为）。投票收敛才有意义。
- agent 能访问不同的来源或工具（异构性可得）。
- 轮次有界（通常 2-3 轮），并且有独立的裁判或验证器。
- 预算允许 3-5 个 agent。在图状拓扑上超过 5-7 个，协作税占主导。

> - The question has ground truth (fact, math, code behavior). Vote convergence is meaningful.
> - Agents can access different sources or tools (heterogeneity is available).
> - Rounds are bounded (2-3 typical) and there is a separate judge or verifier.
> - Budget allows 3-5 agents. Beyond 5-7 on graph topology, coordination tax dominates.

### When vote-with-debate hurts · 投票加辩论有害的场景

- 问题是意见型的。agent 们收敛到看起来最自信的答案，而不是最正确的答案。
- 所有 agent 共享一个基础模型。单一化让共识失去意义。
- 轮次无界。从众每次都赢。
- 任务简单。单 agent 加 N=5 的自一致性更便宜且同样准确。

> - The question is opinion-shaped. Agents converge to whichever answer looks most confident, not most correct.
> - All agents share a base model. Monoculture makes consensus meaningless.
> - Rounds are unbounded. Conformity wins every time.
> - The task is simple. A single agent with self-consistency at N=5 is cheaper and as accurate.

```figure
sw-debate-topology
```

## Build It · 动手造

`code/main.py` 实现：

- `run_star(agents, hub, question)` —— 中心轮询每个 worker，然后聚合。
- `run_chain(agents, question)` —— 顺序精炼。
- `run_tree(root, children, question)` —— 分层，深度 2 的聚合。
- `run_graph(agents, question, rounds)` —— 全对全辩论，轮次有界。
- 一个脚本化的异构度旋钮：每个 agent 有一个 `error_bias` 表示它的系统性错误倾向。
- 一个测量装置：在 N=3、5、7 下运行每种拓扑，报告 (accuracy, total_tokens, wallclock_simulated)。

运行：

```
python3 code/main.py
```

预期输出：一张拓扑 × N → (accuracy, tokens, latency) 的表。研究类任务上图状在 N=3-5 时获胜；快速事实型任务上星型获胜；图状在 N=7 时显出协作税（延迟膨胀快于准确率）。

> `code/main.py` implements:
> - `run_star(agents, hub, question)` — hub polls each worker, aggregates.
> - `run_chain(agents, question)` — sequential refinement.
> - `run_tree(root, children, question)` — hierarchical with depth-2 aggregation.
> - `run_graph(agents, question, rounds)` — all-to-all debate, bounded rounds.
> - A scripted heterogeneity dial: each agent has an `error_bias` indicating its systematic wrongness.
> - A measurement harness that runs each topology at N=3, 5, 7 and reports (accuracy, total_tokens, wallclock_simulated).
> Expected output: a table of topology × N → (accuracy, tokens, latency). Graph wins at N=3-5 on the research-style tasks; star wins on the fast-factual tasks; graph at N=7 shows the coordination tax (latency inflates faster than accuracy).

## Use It · 实战用法

`outputs/skill-topology-picker.md` 是一个技能：读入任务描述，推荐一种拓扑（star / chain / tree / graph）、一个 N（agent 数量）、一个异构配置（使用哪些基础模型）和一个轮次上限。

> `outputs/skill-topology-picker.md` is a skill that reads a task description and recommends a topology (star / chain / tree / graph), an N (number of agents), a heterogeneity profile (base models to use), and a round bound.

## Ship It · 交付

对任何集成：

- 从**单模型 N=5 的自一致性**开始。它是便宜的基线。
- 如果准确率重要，升级到 **N=3 的异构投票**。测量提升的差值。
- 只有当任务有结构（研究、多步骤）且轮次有界可行时，才升级到**辩论拓扑**。
- 始终记录少数簇。当少数派持续正确时，你手里就有了一个多样性信号。
- 把墙钟时间和 token 与准确率一起做基准。「准确率更好但成本 10 倍」是一个商业决策。

> For any ensemble:
> - Start with **self-consistency at N=5** using one strong base model. It is the cheap baseline.
> - Upgrade to **heterogeneous voting at N=3** if accuracy matters. Measure the delta.
> - Only upgrade to **debate topology** if the task has structure (research, multi-step) and bounded rounds are feasible.
> - Always log the minority cluster. When a minority is persistently right, you have a diversity signal.
> - Benchmark wall-clock and tokens alongside accuracy. "Better accuracy at 10x cost" is a business decision.

## Exercises · 练习

1. 运行 `code/main.py`。画出图状拓扑的协作税曲线：accuracy vs N，tokens vs N。曲线在哪个 N 处出现拐点？
2. 实现 A-HMAD：三个带有刻意不同偏差的 agent。与全同偏差基线相比，A-HMAD 在第 14 课的 monoculture 攻击上表现如何？
3. 给图状拓扑加一个「裁判」角色：不投票，只给最终共识打分。这会改变涌现出的从众行为吗？
4. 阅读 AgentVerse 论文（ICLR 2024）。指出你的实现最强烈地表现出哪种涌现行为。你能通过改提示词诱发出相反的行为吗？
5. 阅读 MultiAgentBench（arXiv:2503.01935）第 4 节（拓扑实验）。用你的装置在论文的某一个任务上复现「图状在研究类任务上获胜」的结果。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Self-consistency | "采样 N 次，投票" | Wang 2022。单模型，N 个温度>0 的样本，对推理路径多数投票。 |
| Heterogeneity | "不同的模型" | 由不同基础模型或提示词家族组成的集成。打破单一化。 |
| MAD | "多 agent 辩论" | agent 间多轮交换批评的统称。见 Du 2023。 |
| A-HMAD | "对抗性异构 MAD" | 强调不同模型 + 对抗性结构的 MAD 变体。 |
| Topology | "谁和谁说话" | Star、chain、tree、graph。决定信息流动。 |
| Coordination tax | "收益递减" | 图状拓扑超过约 4 个 agent 后，成本增长快于质量。 |
| Volunteer behavior | "不请自来的帮助" | AgentVerse 涌现模式：agent 主动请缨走下一步。 |
| Conformity behavior | "压力下的附和" | AgentVerse 涌现模式：agent 调整立场迎合批评者。 |
| Jury | "小型专门小组" | Sibyl 式带角色的集成（质询者、上下文、打分者）。 |

## Further Reading · 延伸阅读

- [Wang et al. — Self-Consistency Improves Chain of Thought Reasoning](https://arxiv.org/abs/2203.11171) —— 单模型基线
- [Du et al. — Improving Factuality and Reasoning via Multiagent Debate](https://arxiv.org/abs/2305.14325) —— agent 数量与轮数各自独立地产生影响
- [MultiAgentBench / MARBLE](https://arxiv.org/abs/2503.01935) —— 拓扑基准：图状最适合研究，链式适合流水线
- [Should we be going MAD?](https://arxiv.org/abs/2311.17371) —— MAD 策略综述；发现等预算下 MAD 常输给自一致性
- [AgentVerse (ICLR 2024)](https://proceedings.iclr.cc/paper_files/paper/2024/file/578e65cdee35d00c708d4c64bce32971-Paper-Conference.pdf) —— 志愿与从众涌现模式
- [MARBLE repo](https://github.com/ulab-uiuc/MARBLE) —— 参考基准实现
