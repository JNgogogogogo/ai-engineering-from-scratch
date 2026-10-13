# Evaluation and Coordination Benchmarks · 评估与协调基准

> Five 2025-2026 benchmarks cover the multi-agent evaluation space. **MultiAgentBench / MARBLE** (ACL 2025, arXiv:2503.01935) evaluates star/chain/tree/graph topologies with milestone KPIs; **graph is best for research**, cognitive planning adds ~3% milestone achievement. **COMMA** evaluates multimodal asymmetric-information coordination; state-of-the-art models including GPT-4o struggle to beat a random baseline. **MedAgentBoard** (arXiv:2505.12371) covers four medical task categories and often finds multi-agent does not dominate single-LLM. **AgentArch** (arXiv:2509.10769) benchmarks enterprise agent architectures combining tool-use + memory + orchestration. **SWE-bench Pro** ([arXiv:2509.16941](https://arxiv.org/abs/2509.16941)) has 1865 problems across 41 repos spanning business apps, B2B services, and developer tools; frontier models score ~23% on Pro vs 70%+ on Verified — a reality check on contamination. Claude Opus 4.7 (April 2026) is reported at **64.3%** on Pro with explicit agent-teams coordination (no Anthropic primary source published yet — treat as preliminary); Verdent (agent scaffold) hits **76.1% pass@1** on Verified ([Verdent technical report](https://www.verdent.ai/blog/swe-bench-verified-technical-report)). **AAAI 2026 Bridge Program WMAC** (https://multiagents.org/2026/) is the 2026 community focal point. This lesson builds on MARBLE's metrics, runs a topology-vs-metric sweep, and pins the "just passing SWE-bench Verified is not evidence of generalization" rule.

五个 2025-2026 年的基准覆盖了多智能体评估版图。**MultiAgentBench / MARBLE**（ACL 2025, arXiv:2503.01935）用里程碑 KPI 评估 star/chain/tree/graph 四种拓扑；**图拓扑最适合研究类任务**，认知规划额外带来约 3% 的里程碑达成。**COMMA** 评估多模态非对称信息协调；包括 GPT-4o 在内的最先进模型都难以击败随机基线。**MedAgentBoard**（arXiv:2505.12371）覆盖四个医疗任务类别，经常发现多智能体并不占优于单 LLM。**AgentArch**（arXiv:2509.10769）对结合工具使用 + 记忆 + 编排的企业级智能体架构做基准测试。**SWE-bench Pro**（[arXiv:2509.16941](https://arxiv.org/abs/2509.16941)）有横跨 41 个仓库的 1865 道题，覆盖商业应用、B2B 服务和开发者工具；前沿模型在 Pro 上约 23%，而在 Verified 上 70%+ —— 这是对数据污染的一次现实检验。Claude Opus 4.7（2026 年 4 月）据报道在 Pro 上凭显式智能体团队协调达到 **64.3%**（尚无 Anthropic 一手来源 —— 视为初步结果）；Verdent（智能体脚手架）在 Verified 上达到 **76.1% pass@1**（[Verdent 技术报告](https://www.verdent.ai/blog/swe-bench-verified-technical-report)）。**AAAI 2026 Bridge Program WMAC**（https://multiagents.org/2026/）是 2026 年的社区焦点。本课基于 MARBLE 的指标展开，运行一次拓扑对指标的扫描，并钉死一条规则：「仅通过 SWE-bench Verified 不构成泛化能力的证据」。

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** Phase 16 · 15 (Voting and Debate Topology), Phase 16 · 23 (Failure Modes)
**Time:** ~75 minutes

## Problem · 问题

当一篇论文声称「我们的多智能体系统更好」，问题是：比什么好、在什么上好、怎么测的？2023-2024 年的多智能体评估是一片混乱 —— 每个人用自己挑的指标、自己的基线、自己的任务集。2025-2026 年的基准带来了秩序。

没有共享基准，你就无法有意义地比较两个多智能体系统。更糟的是，没有隔离的留出基准，前沿模型就会被污染。到 2025 年年中，SWE-bench Verified 已在训练语料中被部分污染；前沿模型的分数虚高；Pro 就是为充当未被污染的现实检验而设计的。

本课枚举五个 2026 年的权威基准，说明各自测什么，并教你怎么带着怀疑读基准声明。

> When a paper claims "our multi-agent system is better," the question is: better than what, on what, measured how? The 2023-2024 era of multi-agent evaluation was chaos — everyone picked their own metrics, their own baselines, and their own task sets. The 2025-2026 benchmarks imposed structure.
> Without shared benchmarks, you cannot compare two multi-agent systems meaningfully. Worse, without hold-out benchmarks, frontier models can contaminate. SWE-bench Verified became partially contaminated in training corpora by mid-2025; frontier scores inflated; Pro was designed as an uncontaminated reality check.
> This lesson enumerates the five canonical 2026 benchmarks, names what each measures, and teaches you to read benchmark claims skeptically.

## Concept · 概念

### MultiAgentBench (MARBLE) — ACL 2025 · MultiAgentBench（MARBLE）—— ACL 2025

arXiv:2503.01935。在研究、编码和规划任务上评估四种协调拓扑（star、chain、tree、graph）。基于里程碑的 KPI 跟踪部分进展，而不只看最终成功。

实测结果：

- **图（graph）**拓扑最适合研究场景；支持任意对任意的相互批评。
- **链（chain）**最适合逐步求精的编码。
- **星（star）**最适合快速事实汇总。
- 图拓扑在约 4 个智能体之后出现**协调税**。
- **认知规划**在各拓扑上一致带来约 3% 的里程碑达成。

使用场景：你想对协调拓扑做同口径比较。MARBLE 仓库（https://github.com/ulab-uiuc/MARBLE）提供评测器。

> arXiv:2503.01935. Evaluates four coordination topologies (star, chain, tree, graph) on research, coding, and planning tasks. Milestone-based KPIs track partial progress rather than only final success.
> Measured results: graph topology best for research scenarios; chain best for stepwise-refinement coding; star best for fast-factual consolidation; coordination tax appears past ~4 agents on graph; cognitive planning adds ~3% milestone achievement across topologies.
> Use when: you want to compare coordination topologies apples-to-apples. The MARBLE repo (https://github.com/ulab-uiuc/MARBLE) provides the evaluator.

### COMMA — multimodal asymmetric information · COMMA —— 多模态非对称信息

覆盖智能体拥有不同观察模态、必须在信息不完整共享的情况下协调的任务。报告的结果令人不安：在 COMMA 的智能体间协作上，包括 GPT-4o 在内的前沿模型难以击败**随机基线**。信号是：多智能体模态的训练和评估都不足 —— LLM 处理单模态合作还行；多模态协调会崩。

使用场景：你的系统有多模态或非对称信息协调。COMMA 的零结果是一个警告：先测量，再宣称。

> Covers tasks where agents have different observation modalities and must coordinate without full information sharing. The reported result is uncomfortable: frontier models including GPT-4o struggle to beat a **random baseline** on agent-agent collaboration in COMMA. The signal is that multi-agent modalities are under-trained and under-evaluated — LLMs handle single-modality cooperation reasonably; multi-modality coordination collapses.
> Use when: your system has multimodal or asymmetric-information coordination. The null result from COMMA is a warning to measure before claiming.

### MedAgentBoard — domain stress test · MedAgentBoard —— 领域压力测试

arXiv:2505.12371。四个医疗任务类别：诊断、治疗方案、报告生成、患者沟通。比较多智能体 vs 单 LLM vs 传统规则系统。

发现：在多数类别上，多智能体并不占优于单 LLM。多智能体的优势是狭窄的 —— 当子任务清晰可分时（诊断 + 治疗），任务分解有帮助；当协调开销超过专门化收益时（报告生成），它反而有害。

使用场景：你的领域有清晰的单 LLM 基线。如果 MedAgentBoard 的教训可以泛化，那么许多被提出的多智能体系统都属于过度设计。

> arXiv:2505.12371. Four medical task categories: diagnosis, treatment planning, report generation, patient communication. Compares multi-agent vs single-LLM vs conventional rule-based systems.
> Finding: multi-agent does NOT dominate single-LLM on most categories. The multi-agent advantage is narrow — task decomposition helps when the subtasks are clearly separable (diagnosis + treatment); it hurts when coordination overhead exceeds specialization gain (report generation).
> Use when: your domain has clear-cut single-LLM baselines. If MedAgentBoard's lesson generalizes, many proposed multi-agent systems are over-engineered.

### AgentArch — enterprise architectures · AgentArch —— 企业级架构

arXiv:2509.10769。企业场景，把工具使用、记忆和编排叠在一起。基准隔离每一层的贡献：加工具有多大帮助？加记忆呢？加多智能体编排呢？

使用场景：你在设计企业智能体技术栈，需要为每一层给出理由。AgentArch 帮你避免为测不出价值的功能买单。

> arXiv:2509.10769. Enterprise settings with tool use, memory, and orchestration layered together. Benchmark isolates the contribution of each layer: how much does adding tools help? Adding memory? Adding multi-agent orchestration?
> Use when: you are designing an enterprise agent stack and need to justify each layer. AgentArch helps avoid buying features you cannot measure the value of.

### SWE-bench Pro — the reality check · SWE-bench Pro —— 现实检验

arXiv:2509.16941。横跨 41 个仓库的 1865 道题，覆盖商业应用、B2B 服务和开发者工具。设计上对之后的训练截断**无污染**。前沿模型在 Pro 上约 23%，在 Verified 上 70%+。这个差距就是污染信号。

2026 年 4 月的分数：
- Claude Opus 4.7 在 Pro 上：**64.3%**（报道使用显式智能体团队协调；尚无 Anthropic 一手来源 —— 视为初步结果）。
- Verdent（智能体脚手架）在 Verified 上：**76.1% pass@1**（[技术报告](https://www.verdent.ai/blog/swe-bench-verified-technical-report)）。
- 无智能体脚手架的前沿模型在 Pro 上的原始分数：约 23-35%（[SWE-bench Pro 论文](https://arxiv.org/abs/2509.16941)）。

要点：「我们打赢了 SWE-bench Verified」不再构成能力证据。Pro 是当前的门槛测试。智能体团队脚手架在 Pro 上带来可测量的收益（约 30-40 个百分点），这是 2026 年支持多智能体协调最有力的实证论据之一。

> arXiv:2509.16941. 1865 problems across 41 repositories spanning business apps, B2B services, and developer tools. Designed to be **uncontaminated** with later training cutoffs. Frontier models score ~23% on Pro vs 70%+ on Verified. The gap is the contamination signal.
> The takeaway: "we beat SWE-bench Verified" is no longer evidence of capability. Pro is the current gating test. Agent-team scaffolding produces measurable gains on Pro (~30-40 point delta), which is one of the strongest empirical arguments for multi-agent coordination in 2026.

### AAAI 2026 WMAC · AAAI 2026 WMAC

AAAI 2026 Bridge Program —— 多智能体协调研讨会（Workshop on Multi-Agent Coordination，https://multiagents.org/2026/）。2026 年多智能体 AI 研究的社区焦点。被接收的论文和研讨会论文集是评估新方法的权威场合；做生产决策时，以 WMAC 接收的结论为准，而非 arXiv 预印本。

> AAAI 2026 Bridge Program — Workshop on Multi-Agent Coordination (https://multiagents.org/2026/). The 2026 community focal point for multi-agent AI research. Accepted papers and workshop proceedings are the canonical venue for evaluating new methods; defer to WMAC-accepted claims over arXiv preprints for production decisions.

### Read benchmark claims skeptically — the 2026 checklist · 带着怀疑读基准声明 —— 2026 年检查清单

当有人声称一个多智能体结果时：

1. **哪个基准、哪个 split？** SWE-bench 的 Verified 和 Pro 差别巨大。报错 split 的数字一文不值。
2. **污染检查。** 基准发布是否晚于模型的训练截断？如果不是，保持警惕。
3. **基线对比。** 对单 LLM 基线、对随机、对先前多智能体工作。而不是「对着同一个系统的未调优版本」。
4. **统计显著性。** N 次试验、p 值、置信区间。前沿模型方差很大；单次运行会误导。
5. **任务多样性。** 一个任务还是多个任务？泛化对生产很重要。
6. **成本披露。** 每任务 token 数、墙钟时间。20 倍成本换来的 90% 方案是一个商业决策，不是能力声明。

> When someone claims a multi-agent result: which benchmark, which split; contamination check; baseline comparison; statistical significance; task diversity; cost disclosure.
> A 90% solution at 20x cost is a business decision, not a capability claim.

### What none of the benchmarks measure well · 所有基准都测不好的东西

- **长时程协调。** 以天计的墙钟交互。当前所有基准都跑得很短。
- **对抗韧性。** 当一个智能体是恶意或被攻陷时会怎样？
- **部署中的漂移。** 基准是静态的；生产分布会变。
- **成本归一化的性能。** 多数基准报告原始精度，而不是每美元精度。

为你真正关心的那个轴自建内部基准，往往是正确的做法。

> What none of the benchmarks measure well: long-horizon coordination, adversarial resilience, drift under deployment, cost-normalized performance.
> Building your own internal benchmark for the axis you actually care about is often the right move.

```figure
a5-bench-gap
```

## Build It · 动手造

`code/main.py` 是一个非交互式的完整走查：

- 在一个玩具任务上模拟 3 个多智能体系统。
- 为每个系统计算 MARBLE 式的里程碑指标。
- 通过从「训练」集中扣留任务来运行一次污染检查。
- 显式地与随机基线比较。
- 打印一张基准声明记分卡。

运行：

```bash
python3 code/main.py
```

预期输出：系统记分卡，包含原始精度、里程碑达成、每任务成本、相对随机基线的差值，以及一条污染检查备注。

> Expected output: system scorecard with raw accuracy, milestone achievement, cost-per-task, vs-random baseline delta, and a contamination-check note.

## Use It · 实战用法

`outputs/skill-benchmark-reader.md` 读取任何多智能体基准声明并应用审查清单。输出：一个评级和注意事项。

> `outputs/skill-benchmark-reader.md` reads any multi-agent benchmark claim and applies the scrutiny checklist. Output: a grade and caveats.

## Ship It · 交付

生产评估纪律：

- **建一个反映你真实生产分布的内部基准。** 公共基准提供参考，但不能替代。
- **每次比较都包含一个随机基线。** 如果在一个协调任务上你无法大幅击败随机，这个任务本身可能就不成立。
- **成本与精度一起报告。** Token 成本和墙钟时间。运维团队两者都需要。
- **每季度重建基准。** 生产分布会漂移；过期的基准会误导。
- **避免对已发布基准过拟合。** 如果你的团队专门为 SWE-bench Pro 的数字优化，你在生产上会退化。

> Production evaluation discipline: build an internal benchmark; include a random baseline in every comparison; report cost alongside accuracy; rebuild the benchmark quarterly; avoid published-benchmark overfitting. If your team is optimizing specifically for SWE-bench Pro numbers, you will regress on production.

## Exercises · 练习

1. 运行 `code/main.py`。找出三个模拟系统里哪个的每里程碑成本最优。它与原始精度最高的系统是同一个吗？
2. 阅读 MultiAgentBench（arXiv:2503.01935）。针对你自己的任务领域，判断 MARBLE 会推荐四种拓扑中的哪一种。用论文的结果给出理由。
3. 阅读 SWE-bench Pro 论文。具体是什么让它抗污染？同样的技术能否应用到你关心的其他基准上？
4. 阅读 COMMA 关于多模态协调的发现。设计一个可以加入你内部基准的简单多模态协调任务。什么才算有用的信号？
5. 把基准声明检查清单应用到最近一篇多智能体论文的核心结果上。你会给这个声明打什么评级？

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| MARBLE | 「MultiAgentBench」 | ACL 2025；star/chain/tree/graph 拓扑，配里程碑 KPI。 |
| COMMA | 「多模态基准」 | 多模态非对称信息协调；前沿模型难以击败随机。 |
| MedAgentBoard | 「领域压力测试」 | 四个医疗类别；经常发现多智能体并不占优于单 LLM。 |
| AgentArch | 「企业基准」 | 工具 + 记忆 + 编排分层叠加。 |
| SWE-bench Pro | 「抗污染」 | 1865 道题、41 个仓库；Pro 约 23% vs Verified 70%+（即污染信号）。 |
| Milestone achievement | 「部分得分」 | 奖励进展而不只奖励最终成功的基准。 |
| Contamination | 「基准泄漏进训练」 | 发布之后，基准漂移进训练语料；分数虚高。 |
| WMAC | 「AAAI 2026 Bridge Program」 | 多智能体协调研讨会；社区焦点。 |

## Further Reading · 延伸阅读

- [MultiAgentBench / MARBLE](https://arxiv.org/abs/2503.01935) — 带里程碑 KPI 的拓扑基准
- [MARBLE repository](https://github.com/ulab-uiuc/MARBLE) — 参考实现
- [MedAgentBoard](https://arxiv.org/abs/2505.12371) — 领域压力测试；多智能体常常并不占优
- [AgentArch](https://arxiv.org/abs/2509.10769) — 企业智能体架构
- [SWE-bench leaderboards](https://www.swebench.com/) — 前沿模型的 Verified 与 Pro 分数
- [AAAI 2026 WMAC](https://multiagents.org/2026/) — 2026 年的社区焦点
