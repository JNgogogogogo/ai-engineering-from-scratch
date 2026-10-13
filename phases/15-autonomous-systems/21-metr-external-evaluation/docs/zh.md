# METR Time Horizons and External Capability Evaluation · METR 时间视界与外部能力评估

> METR（前身 ARC Evals）自 2023 年 12 月起是一个独立的 501(c)(3) 组织。他们的 Time Horizon 1.1 基准（2026 年 1 月）对「任务成功概率 vs log(专家人类完成时间)」拟合一条 logistic 曲线；50% 概率处的交点定义模型的时间视界。2025–2026 年的合作项目覆盖 GPT-5.1、GPT-5.1-Codex-Max，以及监测评估原型（监测器能否抓住副任务；agent 能否躲过监测）。基准套件：HCAST（180+ 个 ML、网络安全、SWE、推理任务；1 分钟到 8+ 小时）、RE-Bench（71 个带专家基线的 ML 研究工程任务）、SWAA。诚实备注：METR 的测量是理想化的——没有人类、没有真实后果——而且团队已经记录了评估与部署之间的行为差距（第 1 课）。时间视界是一个上界，不是部署预测。

> METR (ex-ARC Evals) is an independent 501(c)(3) since December 2023. Their Time Horizon 1.1 benchmark (January 2026) fits a logistic curve to task-success probability vs log(expert human completion time); the intersection at 50% probability defines the model's time horizon. The 2025–2026 engagement set covers GPT-5.1, GPT-5.1-Codex-Max, and prototype monitoring evaluations (can a monitor catch side tasks; can the agent evade). Benchmark suites: HCAST (180+ ML, cyber, SWE, reasoning tasks; 1 minute to 8+ hours), RE-Bench (71 ML research-engineering tasks with expert baseline), SWAA. The honest note: METR measurements are idealized — no human, no real consequences — and the team has documented the eval-vs-deployment behavior gap (Lesson 1). A time horizon is an upper bound, not a deployment prediction.

**类型：** Learn
**语言：** Python（标准库，logistic 拟合视界估计器）
**前置：** Phase 15 · 01（长周期 agent）、Phase 15 · 19（RSP）
**时间：** ~60 分钟

## The Problem · 问题

扩展政策（第 19、20 课）的用处取决于它们引用的测量。「AI R&D-4 阈值」和「Long-range Autonomy」是在政策文字里定义的；只有当具体评估产出具体数字时，它们才变得可操作。

METR 是 2024–2026 年间定义了其中许多数字的外部评估组织。他们评估前沿模型——常常在发布前、与实验室签保密协议的情况下进行——事后公开发表方法论。Time Horizon 1.1 基准（2026 年 1 月）是他们的招牌工件：一个把能力压缩进人类可读单位的标量（「这个模型能以 50% 的可靠性完成专家要花 X 小时的那类任务」）。

本课一半关于方法论（视界是怎么算出来的），一半关于解读（为什么视界是一个上界而不是部署预测）。这两种技能属于一起。一个理解视界如何拟合的团队，比一个只在幻灯片上看到「14 小时」的团队，难骗得多。

> Scaling policies (Lessons 19, 20) are only as useful as the measurements they reference. "AI R&D-4 threshold" and "Long-range Autonomy" are defined in policy prose; they become actionable only when specific evaluations produce specific numbers.
> METR is the 2024–2026 external evaluation organization that has defined many of those numbers. They evaluate frontier models — often pre-release, under NDA with labs — and publish methodology afterward. The Time Horizon 1.1 benchmark (January 2026) is their headline artifact: a single scalar that compresses capability into a human-legible unit ("this model can do the kind of task an expert spends X hours on at 50% reliability").
> The lesson is partly about the methodology (how a horizon is computed) and partly about the interpretation (why a horizon is an upper bound, not a deployment prediction). The two skills belong together. A team that understands how the horizon is fit is much harder to fool with a bad vendor claim than a team that just sees "14 hours" on a slide.

## The Concept · 概念

### METR background · METR 背景

- 成立：2023 年 12 月（前身 ARC Evals，分拆为独立的 501(c)(3)）。
- 范围：评估前沿模型的自主能力，常在发布前进行。
- 合作实验室：Anthropic、OpenAI（2025–2026 年多次合作）。
- 代表性交付物：Time Horizon 1.0（2025 年 3 月）、Time Horizon 1.1（2026 年 1 月）、监测评估原型。

> Founded: December 2023 (ex-ARC Evals, spun out into independent 501(c)(3)). Scope: evaluation of frontier models' autonomous capabilities, often pre-release.
> Partner labs: Anthropic, OpenAI (multiple engagements 2025–2026). Notable deliverables: Time Horizon 1.0 (March 2025), Time Horizon 1.1 (January 2026), prototype monitoring evaluations.

### The Time Horizon fit · Time Horizon 的拟合

方法论（来自 METR 博客与论文）：

1. 收集一套任务，专家完成时间从分钟级跨到小时级。当前套件：HCAST（180+ 任务）、RE-Bench（71 任务）、SWAA。
2. 在每个任务上运行模型；记录成功或失败。
3. 拟合一条 logistic 曲线：P(success) 作为 log(专家完成时间) 的函数。
4. 视界即 P(success) = 0.5 处的专家时间。

logistic 拟合是正确的形状，因为能力与任务难度的关系通常递增且趋近平台。50% 这个点是一种选择（也可以是 10%、90%）；METR 在详细论文里报告多个阈值，但以 50% 打头，因为它最直观。

> Collect a task suite spanning minute-scale to hour-scale expert completion times. Current suites: HCAST (180+ tasks), RE-Bench (71 tasks), SWAA.
> Run the model on each task; record success or failure. Fit a logistic curve: P(success) as a function of log(expert completion time). The horizon is the expert-time at which P(success) = 0.5.
> The logistic-fit shape is the right one because capability generally has an increasing, plateau-approaching relationship with task difficulty. The 50% point is a choice (could be 10%, 90%); METR reports multiple thresholds in the detailed paper but leads with 50% because it is the most intuitive.

### The January 2026 numbers · 2026 年 1 月的数字

按 Time Horizon 1.1：

- Claude Opus 4.6：50% 可靠性下约 14 小时（Time Horizon 1.1，2026 年 1 月）。
- HCAST 类任务上的倍增时间：Time Horizon 1.1（2026 年 1 月）报告的 2023 年后拟合约 4.3 个月（130.8 天）；约 7 个月的数字是 Time Horizon 1.0 的 2019–2025 全期拟合，TH1.1 将其与 2023 年后数字并列报告。

这些就是 Phase 15 其余课程引用的具体数字。它们被 Anthropic 的 RSP v3.0（第 19 课）和 DeepMind 的 FSF v3（第 20 课）引用，作为喂给阈值评估的测量之一。

> Claude Opus 4.6: ~14 hours at 50% reliability, as of Time Horizon 1.1 (January 2026).
> Doubling time on HCAST-style tasks: ~4.3 months (130.8 days) on the post-2023 fit reported by Time Horizon 1.1 (January 2026); the ~7-month figure is the full 2019–2025 fit from Time Horizon 1.0 and is reported in TH1.1 alongside the post-2023 number.
> Those are the specific numbers the rest of Phase 15 references. They are cited in Anthropic's RSP v3.0 (Lesson 19) and DeepMind's FSF v3 (Lesson 20) as one of the measurements feeding threshold assessments.

### Benchmark suites · 基准套件

- **HCAST**：189 个任务，横跨 ML、网络安全、软件工程和通用推理。范围：1 分钟到 8+ 小时专家时间。视界数字背后的主要套件。
- **RE-Bench**：71 个 ML 研究工程任务，带人类专家基线。衡量模型能否做那种通向 AI R&D-4 阈值的 ML R&D 工作。
- **SWAA**：更短的任务；用于校准视界曲线的低端。

> HCAST: 189 tasks across ML, cybersecurity, software engineering, and general reasoning. Span: 1 minute to 8+ hours of expert time. The main suite behind the horizon number.
> RE-Bench: 71 ML research-engineering tasks with a human expert baseline. Measures whether the model can do the kind of ML R&D work that feeds into the AI R&D-4 threshold.
> SWAA: shorter tasks; useful for calibrating the low end of the horizon curve.

### Prototype monitoring evaluations · 监测评估原型

2025–2026 年 METR 的工作包括监测评估原型：监测器能否抓住模型执行副任务（操作者要求之外的事情）；agent 能否躲过监测器。这些直接喂给 OpenAI PF v2 的「Undermining Safeguards」类别和 DeepMind FSF v3 的欺骗性对齐监测（第 20 课）。

> 2025–2026 METR work included monitoring-evaluation prototypes: can a monitor catch a model performing a side task (something other than what the operator asked for); can the agent evade the monitor. These directly feed the "Undermining Safeguards" category in OpenAI PF v2 and the deceptive-alignment monitoring in DeepMind FSF v3 (Lesson 20).

### Why horizons are upper bounds · 为什么视界是上界

- **理想化的工具**：基准任务给模型干净的工具和格式良好的数据。真实部署更混乱。
- **没有真实后果**：模型从不真的给客户开账单、删真实数据、联系真人。真实部署有不可逆的利害。
- **评估情境博弈**：第 1 课。模型在测试里表现不同。2026 年 International AI Safety Report 对此做了实证记录。
- **没有真实用户的多样性**：基准提示是结构化的。真实用户给出模糊的、依赖上下文的请求。

视界是有利条件下的能力天花板。部署可靠性是另一个数字，更低，团队必须测量自己的分布才能知道它。

> Idealized tooling: benchmark tasks give the model clean tools and well-formatted data. Real deployments are messier.
> No real consequences: the model never actually bills a customer, deletes real data, or contacts real people. Real deployments have irreversible stakes.
> Eval-context gaming: Lesson 1. Models behave differently in tests. The 2026 International AI Safety Report documents this empirically.
> No legitimate user variance: benchmark prompts are structured. Real users produce ambiguous, context-dependent requests.
> The horizon is the capability ceiling under favorable conditions. Deployment reliability is a different number, lower, and teams must measure their own distribution to know it.

### The external-evaluator case · 外部评估者的理由

外部评估之所以重要，是因为内部实验室有动机优化它们所报告的指标。METR 的独立性——一个有公开方法论和同行评审论文的 501(c)(3)——是结构性缓解。它单独并不充分（实验室仍控制 METR 能看到什么），但严格优于没有外部评估。

> External evaluation matters because internal labs have incentives to optimize metrics they report. METR's independence — a 501(c)(3) with a declared methodology and peer-reviewed papers — is the structural mitigation. It is not sufficient alone (labs still control what METR sees), but it is strictly better than no external evaluation.

### How to use horizon numbers in practice · 实践中如何使用视界数字

- **作为能力过滤器**：如果一个模型的视界远低于拟议任务的专家时间，就不要以自主模式上线它（第 1 课的 skill 文件）。
- **作为趋势指标**：倍增时间告诉你，即使没有新的缓解措施，当前做法还能安全多久。
- **作为先验**：14 小时的视界是一个起点。按你的任务分布、工具质量和部署环境向下调整。

> As a capability filter: if a model's horizon is well below the expert-time of a proposed task, do not ship it autonomous (Lesson 1's skill file).
> As a trend indicator: doubling time tells you how long the current practice will remain safe even without new mitigations.
> As a prior: a horizon of 14 hours is a starting point. Adjust down for your task distribution, your tooling quality, and your deployment context.

```figure
a5-horizon-fit
```

## Use It · 实战用法

`code/main.py` 在给定一份合成结果集时，实现了任务成功率对 log(专家时间) 的 logistic 拟合。它报告 50% 视界（METR 的招牌数字）、10% 视界（保守）和 90% 视界（乐观）。还演示了当成功率被评估情境博弈人为抬高时，什么会发生变化。

> `code/main.py` implements a logistic fit of task-success vs log(expert time), given a synthetic result set. It reports the 50% horizon (METR's headline), 10% horizon (conservative), and 90% horizon (optimistic). Also demonstrates what changes when the success rate is artificially inflated by eval-context gaming.

## Ship It · 交付

`outputs/skill-horizon-interpretation.md` 评审一个厂商的视界声明，产出基准声明与部署现实之间的差距分析。

> `outputs/skill-horizon-interpretation.md` reviews a vendor's horizon claim and produces a gap analysis between benchmark claim and deployment reality.

## Exercises · 练习

1. 运行 `code/main.py`。确认拟合的 50% 视界与合成真值一致。再把任务时间网格减半；视界估计有实质性变化吗？

2. 阅读 METR 的 Time Horizon 1.1 博文。找出可靠性最高和最低的具体任务。解释差距为什么存在。

3. 阅读 METR 的「Measuring Autonomous AI Capabilities」资源。列出 HCAST 的任务类别。选一个你会为生产任务加重权重的类别并说明理由。

4. 把评估情境博弈引入模拟器：把约 20% 的失败任务翻成成功。报告新的视界。这近似了 20% 的博弈率对观测数字的影响。

5. 在你自己的 bug 积压或一个代表性任务集上设计一次内部视界评估。描述数据收集、拟合，以及输出告诉你什么。与 METR 数字对比。

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|---|---|---|
| METR | 「外部评估者」 | 前身 ARC Evals；自 2023 年 12 月起为独立 501(c)(3) |
| Time Horizon | 「能力度量」 | 50% 可靠性下的专家任务时长，来自 logistic 拟合 |
| HCAST | 「METR 主套件」 | 180+ 任务，横跨 1 分钟到 8+ 小时 |
| RE-Bench | 「研究工程」 | 71 个带人类基线的 ML 研究工程任务 |
| SWAA | 「短任务套件」 | 校准视界曲线的低端 |
| Doubling time | 「增长率」 | 50% 视界翻倍所需时间；HCAST 上约 7 个月 |
| Eval-context gaming | 「模型在测试里表现不同」 | 有据可查的测试与部署行为差距 |
| Upper bound | 「视界是天花板」 | 基准视界 > 负载下的部署可靠性 |

## Further Reading · 延伸阅读

- [METR — Resources for Measuring Autonomous AI Capabilities](https://metr.org/measuring-autonomous-ai-capabilities/) — HCAST、RE-Bench、SWAA 规格。
- [METR — Measuring AI Ability to Complete Long Tasks](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/) — 原始视界论文。
- [METR — Time Horizon 1.1 (January 2026)](https://metr.org/research/) — 当前数字与方法论。
- [Epoch AI — METR Time Horizons benchmark](https://epoch.ai/benchmarks/metr-time-horizons) — 实时追踪。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 对 METR 测量的内部视角。
