# Multi-Agent Debate and Collaboration · 多智能体辩论与协作

Du 等人（ICML 2024，「Society of Minds」）让 N 个模型实例各自独立提出答案，再经过 R 轮互相批评、逐步收敛。它能提升事实性、规则遵循与推理质量；稀疏拓扑在 token 成本上优于全连接网状结构。

> Du et al. (ICML 2024, "Society of Minds") run N model instances that independently propose answers, then iteratively critique each other over R rounds to converge. Improves factuality, rule-following, reasoning. Sparse topology beats full mesh on token cost.

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 12 (Workflow Patterns), Phase 14 · 05 (Self-Refine and CRITIC)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 解释辩论协议（debate protocol）：N 个提案者、R 轮辩论、收敛到一个共享答案。
- 描述辩论为什么能提升事实性、规则遵循和推理质量。
- 解释稀疏拓扑（sparse topology）：不是每个辩手都需要看到所有其他辩手。
- 在脚本化 LLM 上用 stdlib 实现辩论，包含全连接（full-mesh）与稀疏两种变体；测量 token 成本与准确率的取舍。

> Explain the debate protocol: N proposers, R rounds, converge on a shared answer.
> Describe why debate improves factuality, rule-following, and reasoning.
> Explain sparse topology: not every debater needs to see every other.
> Implement a stdlib debate over a scripted LLM with full-mesh and sparse variants; measure token cost vs accuracy.

## The Problem · 问题在哪

Self-Refine（第 05 课）是同一个模型自己批评自己——有群体思维（groupthink）的风险。CRITIC（第 05 课）把批评锚定在外部工具上——但外部工具并不总是可用。辩论引入第三种模式：多个实例、交叉批评、靠分歧达成收敛。

> Self-Refine (Lesson 05) is one model critiquing itself — risks groupthink. CRITIC (Lesson 05) grounds critique in external tools — not always available. Debate introduces a third mode: multiple instances, cross-critique, convergence by disagreement.

## The Concept · 概念

### Society of Minds (Du et al., ICML 2024) · 群体心智

- N 个模型实例独立地对同一个问题给出提案。
- 在 R 轮中，每个模型阅读其他模型的提案并加以批评。
- 模型根据批评更新自己的答案。
- R 轮结束后，返回收敛后的答案。

受成本所限，原始实验只用了 N=3、R=2。在困难问题上（MMLU、GSM8K、国际象棋走子合法性、传记生成），智能体越多、轮次越多，准确率越高。

跨模型组合胜过单模型辩论：ChatGPT + Bard 搭档优于任一单独模型。

> N model instances independently propose answers to the same question.
> Over R rounds, each model reads the others' proposals and critiques them.
> Models update their answers based on the critiques.
> After R rounds, return the convergent answer.
> Original experiments used N=3, R=2 due to cost... Cross-model combinations beat single-model debates: ChatGPT + Bard together > either alone.

### Sparse topology · 稀疏拓扑

《Improving Multi-Agent Debate with Sparse Communication Topology》（arXiv:2406.11776，2024-2025）表明：全连接辩论并不总是最优。稀疏拓扑（星形、环形、hub-and-spoke）能以更低的 token 成本达到相当的准确率。每个辩手只看到一部分同伴。

这意味着：

- 全连接 N=5、R=3：5 × 3 = 15 份提案，每份要读 4 个同伴 = 60 次批评操作。
- 星形 N=5、R=3（1 个 hub + 4 个 spoke）：15 份提案，spoke 只读 hub = 12 次批评操作。

> "Improving Multi-Agent Debate with Sparse Communication Topology" (arXiv:2406.11776, 2024-2025) showed full-mesh debate is not always optimal. Sparse topologies (star, ring, hub-and-spoke) can match accuracy at lower token cost. Each debater sees only a subset of peers.
> Full mesh N=5, R=3 = 5 × 3 = 15 proposals, each reading 4 peers = 60 critique ops.
> Star N=5, R=3 (one hub + 4 spokes) = 15 proposals, spokes read only the hub = 12 critique ops.

### When debate helps · 辩论何时有帮助

- **事实性（factuality）。** N 份独立提案互相交叉核对，减少幻觉。
- **规则遵循（rule-following）。** 国际象棋走子合法性——一个模型漏看的规则，其他模型能抓住。
- **开放式推理（open-ended reasoning）。** 多种视角逼近正确答案。

> Factuality. N independent proposals, cross-check reduces hallucination.
> Rule-following. Chess move validity — one model misses a rule, others catch it.
> Open-ended reasoning. Multiple framings narrow in on the right answer.

### When debate hurts · 辩论何时有害

- **延迟敏感的 UX。** N × R 轮串行开销，这种延迟你未必负担得起。
- **成本敏感的大规模场景。** 每个问题要花 N × R 份 token。
- **简单的事实查询。** 一次查询比五轮辩论便宜。

> Latency-sensitive UX. N × R serial rounds is latency you may not have.
> Cost-sensitive scale. N × R tokens per question.
> Simple factual lookups. One lookup is cheaper than five debates.

### 2026 practical instantiations · 2026 年的落地形态

- **Anthropic orchestrator-workers**（第 12 课）——辩论的一个变体，带一个综合（synthesis）步骤。
- **LangGraph supervisor**（第 13 课）——中央路由器 + 专家智能体，可以把辩论实现成一个节点。
- **OpenAI Agents SDK**（第 16 课）——智能体之间来回交接（handoff），实现迭代式批评。
- **Multi-agent evals**——把辩论与 evaluator-optimizer 配对，产出评估信号。

> Anthropic orchestrator-workers (Lesson 12) — one variant of debate with a synthesis step.
> LangGraph supervisor (Lesson 13) — central router + specialist agents can implement debate as a node.
> OpenAI Agents SDK (Lesson 16) — agents handoff back and forth for iterative critique.
> Multi-agent evals — pair debate + evaluator-optimizer for eval signal.

### Where this pattern goes wrong · 这个模式哪里会出问题

- **收敛坍缩（convergence collapse）。** 所有智能体在第一个错误答案上过早收敛。用「强制分歧轮」来缓解。
- **Hub 失效。** 星形拓扑里，一个坏 hub 会带坏所有人。轮换 hub 或使用多个 hub。
- **提示同质化（prompt homogenization）。** 所有智能体用同一个提示词，产出的就是同样的答案。使用多样的提示词和/或多样的模型。

> Convergence collapse. All agents converge on the first wrong answer. Mitigate with required disagreement rounds.
> Hub failure. In a star topology, a bad hub corrupts everyone. Rotate or use multiple hubs.
> Prompt homogenization. All agents use the same prompt; they produce the same answers. Use diverse prompts and/or models.

```figure
debate-converge
```

## Build It · 动手造

`code/main.py` 用 stdlib 实现了辩论：

- `Debater` 类（脚本化 LLM，每个辩手带自己的观点漂移）。
- `FullMeshDebate` 和 `SparseDebate` 两个运行器。
- 三个问题：一个事实型、一个规则型、一个推理型。
- 指标：收敛答案、收敛所需轮数、总批评操作数。

运行：

```
python3 code/main.py
```

输出：每个协议的准确率与成本；稀疏拓扑在 3 个问题中的 2 个上以更低成本追平全连接。

> Metrics: convergent answer, rounds to convergence, total critique ops.
> Output: per-protocol accuracy and cost; sparse matches full mesh on 2/3 questions at lower cost.

## Use It · 实战用法

- **Anthropic orchestrator-workers** 适合简单的 2-3 个 worker 的辩论。
- **LangGraph** 适合带检查点（checkpointing）的有状态多轮辩论。
- **自研** 适合科研场景或需要特殊正确性保证的场合。

> Anthropic orchestrator-workers for simple 2-3-worker debates.
> LangGraph for stateful multi-round debate with checkpointing.
> Custom for research or specialized correctness guarantees.

## Ship It · 交付

`outputs/skill-debate.md` 提供一个多智能体辩论的脚手架，拓扑、N、R 和收敛规则都可配置。

> `outputs/skill-debate.md` scaffolds a multi-agent debate with configurable topology, N, R, and a convergence rule.

## Exercises · 练习

1. 实现一条「强制分歧」规则：第 1 轮中每个辩手必须给出一个不同的提案。测量它对收敛速度的影响。
2. 加一个置信度加权聚合：辩手返回（答案, 置信度），聚合器按置信度加权。这有帮助吗？
3. 把其中一个「智能体」换成另一个观点不同的脚本化 LLM。异质性会提升准确率吗？
4. 在你的 3 个问题上测量全连接与稀疏拓扑的 token 成本。画出「成本-准确率」曲线。
5. 阅读 Society of Minds 论文。把你的玩具实现移植到 N=5、R=3。什么会崩？什么会变好？

> Implement a "forced disagreement" rule: in round 1, every debater must produce a distinct proposal. Measure effect on convergence speed.
> Measure token cost for full mesh vs sparse on your 3 questions. Plot cost vs accuracy.
> Read the Society of Minds paper. Port your toy to N=5, R=3. What breaks? What gets better?

## Key Terms · 术语表

| Term 术语 | What people say 大家怎么说 | What it actually means 实际含义 |
|------|------------------------|------------------------|
| Debate（辩论） | 「多智能体互评」 | N 个提案者、R 轮交叉批评、最终收敛 |
| Full mesh（全连接） | 「每个人都读所有人」 | 每一轮每个辩手读所有同伴 |
| Sparse topology（稀疏拓扑） | 「有限的同伴视野」 | 辩手只读一部分同伴 |
| Hub-and-spoke（中心辐射） | 「星形拓扑」 | 一个中央辩手，N-1 个 spoke 只读 hub |
| Convergence（收敛） | 「达成一致」 | 辩手收敛到一个共享答案 |
| Society of Minds（群体心智） | 「Du 等人的辩论论文」 | ICML 2024 的多智能体辩论方法 |

## Further Reading · 延伸阅读

- [Du et al., Society of Minds (arXiv:2305.14325)](https://arxiv.org/abs/2305.14325) —— 多智能体辩论的原始文献
- [Sparse Communication Topology (arXiv:2406.11776)](https://arxiv.org/abs/2406.11776) —— 稀疏拓扑的实验结果
- [Anthropic, Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) —— 把 orchestrator-workers 视为辩论变体
- [Madaan et al., Self-Refine (arXiv:2303.17651)](https://arxiv.org/abs/2303.17651) —— 单模型自我批评的对照面
