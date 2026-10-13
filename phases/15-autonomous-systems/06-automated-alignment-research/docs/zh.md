# Automated Alignment Research (Anthropic AAR) · 自动化对齐研究（Anthropic AAR）

> Anthropic 让多支 Claude Opus 4.6 自主对齐研究员（Autonomous Alignment Researcher）团队在相互独立的沙箱中并行运行，通过一个共享论坛协调，论坛日志存放在所有沙箱之外（因此智能体无法删除自己的记录）。在弱到强（weak-to-strong）训练问题上，AAR 的表现超过了人类研究员。Anthropic 自己的总结指出：规定得过细的工作流常常约束 AAR 的灵活性并拉低性能。自动化对齐研究是压缩时间线的那一步——它压缩的恰恰是 RSP 本想检测的那些错位风险的出现时间。

> Anthropic ran parallel teams of Claude Opus 4.6 Autonomous Alignment Researchers in independent sandboxes, coordinating via a shared forum whose logs live outside any sandbox (so agents cannot delete their own records). On the weak-to-strong training problem, the AARs outperformed human researchers. Anthropic's own summary flags that prescribed workflows often constrain AAR flexibility and degrade performance. Automating alignment research is the compression step that compresses the timeline to the exact misalignment risks the RSP is meant to detect.

**类型：** Learn（学习）
**语言：** Python（仅 stdlib，parallel-research-forum 模拟器）
**先修：** Phase 15 · 05（AI Scientist v2）、Phase 15 · 04（DGM）
**时间：** ~60 分钟

## The Problem · 问题在哪

对齐研究的昂贵之处在于人类研究员的时间。可扩展监督（scalable oversight）、奖励规约（reward specification）、弱到强训练这类问题，每一轮迭代就需要数周的实验。随着前沿能力推进，对齐工作量的增长快于合格研究员的供给。

自动化对齐研究（AAR）问的是：那些能力正在跑赢对齐的前沿模型，能不能反过来帮忙缩小这个差距？Anthropic 2026 年关于 AAR 运行的弱到强训练研究的报告（alignment.anthropic.com/2026/automated-w2s-researcher/）是这一类已部署系统的首批公开结果之一。

结果确实正面：AAR 解一个研究问题解得比人类基线更好。这个结果同时也把本阶段发展出的每一个担忧集中到了同一个系统里。如果对齐研究可以被自动化，那么破坏安全防护的那部分研究同样可以被自动化。RSP 针对 AI R&D 能力设置的阈值，正是带着这个循环写就的。

> Alignment research is expensive in human-researcher time. Problems like scalable oversight, reward specification, or weak-to-strong training require experiments that take weeks per iteration. As frontier capabilities advance, the alignment workload grows faster than the supply of qualified researchers.
> Automated Alignment Research (AAR) asks whether the same frontier models whose capability is outrunning alignment can contribute to closing the gap. Anthropic's 2026 report on an AAR-run weak-to-strong-training study (alignment.anthropic.com/2026/automated-w2s-researcher/) is one of the first public results from a deployed system of this class.
> The result is genuinely positive: AARs solved a research problem better than the human baseline. The result also concentrates, in a single system, every concern this phase has developed. If alignment research can be automated, so can the parts that compromise safeguards. The RSP's thresholds for AI R&D capability are written with this loop in mind.

## The Concept · 概念

### The architecture (as publicly described) · 架构（公开描述的版本）

- **并行智能体。** 多个 Claude Opus 4.6 实例作为 AAR 运行，每个在一个独立沙箱里。沙箱限制文件系统、网络和进程面。
- **共享论坛。** 发现被发布到一个共享论坛，其存储后端位于所有沙箱之外。智能体可以读论坛；智能体不能从自己的沙箱内删除或编辑论坛记录。
- **任务分配。** 一个人设计的任务队列把研究问题分配给各个 AAR。AAR 提出分解、运行实验、撰写发现。
- **弱到强训练焦点。** 已发表的研究针对弱到强训练——用一个较弱的监督者模型训练一个较强的学生模型。AAR 在这个任务上超过了人类研究员。

> **Parallel agents.** Multiple Claude Opus 4.6 instances run as AARs, each in an independent sandbox. Sandboxes limit filesystem, network, and process surface.
> **Shared forum.** Findings are published to a shared forum whose storage backend sits outside every sandbox. Agents can read the forum; agents cannot delete or edit forum records from within their own sandbox.
> **Task allocation.** A human-designed task queue assigns research problems to AARs. AARs propose decompositions, run experiments, write up findings.
> **Weak-to-strong training focus.** The published study addressed weak-to-strong training — using a weaker supervisor model to train a stronger student model. AARs outperformed human researchers on this task.

### Why the out-of-sandbox log matters · 为什么沙箱外日志很重要

日志完整性这个性质，是「受控实验」与「可能已被污染的实验」之间的分界。如果 AAR 能编辑自己的日志，它们就能掩盖失败或可疑的实验。Anthropic 直接点明了这一点：这个性质是信任研究产出的必要条件，而且验证起来并不平凡。

用基础设施的语言来说，类比是「带直写外部存储的 append-only 日志」（例如 S3 object-lock、不可变的 Datadog 日志）。智能体没有修改过往记录的凭证。这与 2026 年企业安全团队用来构建抗勒索软件审计轨迹的是同一个模式。

> The log-integrity property is the difference between a controlled experiment and a potentially compromised one. If AARs could edit their own logs, they could cover up failed or dubious experiments. Anthropic flags this directly: the property is a necessary condition for trusting the research output, and it is non-trivial to verify.
> The analog in infrastructure terms is append-only logs with write-through to external storage (e.g. S3 object-lock, immutable Datadog logs). The agent has no credential to modify past records. This is the same pattern that 2026 corporate security teams use to make ransomware-resistant audit trails.

### The prescribed-workflow tradeoff · 规定工作流的取舍

Anthropic 的报告指出，规定得过细的工作流常常约束 AAR 的灵活性并拉低性能。换句话说：如果人类设计者把研究计划一步步写死，AAR 的表现会比拿到高层目标、自己决定如何分解时要差。这与整个 agentic 研究领域的结果一致（LangGraph、Microsoft 的 Agent Framework）——过度规定的脚手架会伤害有能力的智能体。

安全上的含义很微妙。提升 AAR 性能的那种灵活性，同样也是允许未经批准的分解、新式工具使用和目标漂移的那种灵活性。这个取舍是一个设计空间决策：多少灵活性才能买到足以战胜人类的能力，同时又不给智能体留下把目标泛化到分布之外的空间？

> Anthropic's report notes that prescribed workflows often constrain AAR flexibility and degrade performance. In other words: if the human designer writes the research plan step-by-step, AARs do worse than if given high-level goals and freedom to decompose. This is consistent with results across agentic research (LangGraph, Microsoft's Agent Framework) — overspecified scaffolds hurt capable agents.
> The safety implication is subtle. The flexibility that improves AAR performance is also the flexibility that allows unsanctioned decomposition, novel tool use, and goal-drift. The tradeoff is a design-space decision: how much flexibility buys enough capability to beat humans, without handing the agent room to generalize goals off-distribution?

### The compression risk · 压缩风险

RSP v3.0（第 19 课）引入了一个 AI R&D 能力阈值：在与「人类 + AI 工具」相比有竞争力的成本下完全自动化 AI R&D 管线的能力。DeepMind 的 FSF v3 包含一个类似的 ML R&D 自主性等级。两个框架都把这个阈值当作提升管控级别的触发器。

AAR 距离阈值只差一步：它自动化了管线的一部分（针对范围良好的特定任务的对齐研究），但还没有自动化端到端的能力开发循环。时间线问题就是这个差距以多快的速度闭合。

被压缩的时间线是复合式失败的核心担忧。如果对齐研究与能力研究以相近的速率复利增长，错位风险面至少与能力一样快地扩大。如果能力复利得更快（历史趋势如此），差距就会拉大。这就是「AAR 是有条件的好事」的论证：当且仅当研究过程可信时，每一个额外的对齐结果才会缩小差距。

> RSP v3.0 (Lesson 19) introduces an AI R&D capability threshold: the ability to fully automate the AI R&D pipeline at competitive cost vs human + AI tools. DeepMind's FSF v3 includes an analogous ML R&D autonomy level. Both frameworks treat this threshold as the trigger for elevated controls.
> AAR is one step short of the threshold: it automates part of the pipeline (alignment research on specific, well-scoped tasks) but not the end-to-end capability development loop. The timeline question is how fast the gap closes.
> Compressed timelines are the compounding-failure concern. If alignment research and capability research compound at similar rates, the misalignment risk surface grows at least as fast as capability. If capability compounds faster (the historical trend), the gap widens. This is the argument for AAR being a qualified good: each additional alignment result reduces the gap if and only if the research process is trustworthy.

### What AAR does not replace · AAR 不能替代什么

人类研究员设定任务队列、审查结果，并掌握宪法性权威。AAR 加速的是管线的中段，不是两端。Anthropic 公开的产出既包括 AAR 的贡献，也包括人类研究员对「发表什么、撤回什么、打磨什么」的判断。

这对应第 15 课的 propose-then-commit 模式应用于研究本身：AAR 提议；人类拍板。

> Human researchers set the task queue, review results, and hold the constitutional authority. The AARs accelerate the middle of the pipeline, not the ends. Anthropic's published outputs include both AAR contributions and human-researcher judgement on what to publish, what to retract, and what to refine.
> This matches the propose-then-commit pattern from Lesson 15 applied to research itself: AARs propose; humans commit.

```figure
aar-forum
```

## Use It · 实战用法

`code/main.py` 模拟一个多 AAR 研究论坛。三个独立的「研究智能体」并行运行，把发现发布到一个 append-only 论坛，并带有可选的篡改尝试。

观察：

- 沙箱外日志如何抓住日志篡改企图。
- 带自由分解的任务分配如何在更难的问题上胜过固定工作流。
- 如果日志不具备防篡改可验证性，一个被攻陷的 AAR 如何污染论坛的信号。

> `code/main.py` simulates a multi-AAR research forum. Three independent "research agents" run in parallel, posting findings to an append-only forum with optional tamper attempts.
> Watch how out-of-sandbox logging catches log-tampering attempts, how task allocation with free decomposition outperforms fixed workflows on harder problems, and how a single compromised AAR can contaminate the forum's signal if the log is not tamper-evident.

## Ship It · 交付

`outputs/skill-aar-deployment-review.md` 是对一个自动化对齐研究管线的部署前审查。

> `outputs/skill-aar-deployment-review.md` is a pre-deployment review of an automated-alignment-research pipeline.

## Exercises · 练习

1. 运行 `code/main.py`。比较「固定工作流」与「自由分解」两种设置。自由分解总是赢吗？还是存在固定工作流有竞争力的问题类别？

2. 修改模拟器，让其中一个智能体尝试篡改日志。确认 append-only 日志检测到了它。写一段话，精确描述检测签名在日志里长什么样。

3. 读 Anthropic 的弱到强 AAR 报告。指出 AAR 击败人类研究员的那个具体子任务。是什么让它适合被自动化？

4. 设计一个任务队列分配策略，在 AAR 灵活性（更好的结果）与规定工作流约束（更容易审计）之间取得平衡。描述你会如何对两者做 A/B 测试。

5. 读 RSP v3.0 的 AI R&D-4 阈值。用一段话描述你认为什么东西会越过这条线，而 AAR 目前还不会。

> 1. Run `code/main.py`. Compare the "fixed-workflow" vs "free-decomposition" settings. Does free decomposition always win, or are there problem classes where the fixed workflow is competitive?
> 2. Modify the simulator so one agent attempts log tampering. Confirm the append-only log detects it. Write one paragraph describing exactly what the detection signature looks like in the log.
> 5. Read RSP v3.0's AI R&D-4 threshold. In one paragraph, describe what you think would cross it that AAR currently does not.

## Key Terms · 术语表

| 术语 | 人们口头怎么说 | 它实际是什么意思 |
|---|---|---|
| AAR | 「自主对齐研究员」 | 在对齐问题上自主运行的 Claude Opus 4.6 实例 |
| Weak-to-strong training | 「用较弱的监督者训练较强的模型」 | 经典的可扩展监督基准，AAR 在其上超过了人类 |
| Shared forum | 「智能体发布发现的地方」 | append-only、沙箱外的存储 |
| Out-of-sandbox log | 「智能体不能编辑自己的记录」 | 具备防篡改可验证性的外部存储直写 |
| Prescribed workflow | 「人类设计者给的逐步计划」 | 约束 AAR；相比自由分解常常拉低性能 |
| Free decomposition | 「智能体自己决定怎么拆任务」 | 更有能力，更难审计 |
| AI R&D threshold | 「RSP/FSF 能力等级」 | 以有竞争力的成本完全自动化 R&D 管线 |
| Compressed timeline | 「对齐 vs 能力的赛跑」 | 如果能力复利快于对齐，错位风险就会增长 |

> | Term | What people say | What it actually means |
> |---|---|---|
> | AAR | "Automated Alignment Researcher" | Claude Opus 4.6 instance operated autonomously on alignment problems |
> | Weak-to-strong training | "Training a stronger model with a weaker supervisor" | Classic scalable-oversight benchmark AARs outperformed humans on |
> | Shared forum | "Where agents publish findings" | Append-only, out-of-sandbox storage |
> | Out-of-sandbox log | "Agent cannot edit its own record" | Tamper-evident write-through to external storage |
> | Prescribed workflow | "Step-by-step plan from human designer" | Constrains AAR; often degrades performance vs free decomposition |
> | Free decomposition | "Agent decides how to break the task" | More capable, harder to audit |
> | AI R&D threshold | "RSP/FSF capability level" | Full automation of R&D pipeline at competitive cost |
> | Compressed timeline | "Alignment vs capability race" | If capability compounds faster than alignment, misalignment risk grows |

## Further Reading · 延伸阅读

- [Anthropic — Automated Weak-to-Strong Researcher](https://alignment.anthropic.com/2026/automated-w2s-researcher/) —— 一手来源。
- [Anthropic Responsible Scaling Policy v3.0](https://anthropic.com/responsible-scaling-policy/rsp-v3-0) —— AI R&D 阈值框架。
- [Anthropic — Measuring AI agent autonomy](https://www.anthropic.com/research/measuring-agent-autonomy) —— 更宏观的智能体自主性框架表述。
- [DeepMind Frontier Safety Framework v3](https://deepmind.google/blog/strengthening-our-frontier-safety-framework/) —— 与 RSP 平行的 ML R&D 自主性等级。
- [Burns et al. (2023). Weak-to-Strong Generalization (OpenAI)](https://openai.com/index/weak-to-strong-generalization/) —— AAR 攻击的底层问题。
