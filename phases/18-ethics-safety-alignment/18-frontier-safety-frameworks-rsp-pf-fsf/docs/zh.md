# Frontier Safety Frameworks — RSP, PF, FSF · 前沿安全框架——RSP、PF、FSF

> 三大实验室框架定义了 2026 年的前沿能力行业治理。Anthropic 负责任扩展政策（Responsible Scaling Policy）v3.0（2026 年 2 月）引入分级 AI 安全等级（ASL-1 到 ASL-5+），仿照生物安全等级设计，其中 ASL-3 已于 2025 年 5 月针对 CBRN 相关模型激活。OpenAI Preparedness Framework v2（2025 年 4 月）为受追踪能力定义了五条判据，并将 Capabilities Reports 与 Safeguards Reports 分开。DeepMind Frontier Safety Framework v3.0（2025 年 9 月）引入关键能力等级（Critical Capability Levels），其中包括新增的有害操纵（Harmful Manipulation）CCL。三家如今都包含竞争者调整条款，允许在同行实验室不带可比安全措施发布时推迟执行。跨实验室对齐仍是结构性的而非术语性的：「Capability Thresholds」「High Capability thresholds」与「Critical Capability Levels」指称的是类似构造。

> Three major-lab frameworks define the 2026 industry governance of frontier capability. Anthropic Responsible Scaling Policy v3.0 (February 2026) introduces tiered AI Safety Levels (ASL-1 through ASL-5+), modeled on biosafety levels, with ASL-3 activated May 2025 for CBRN-relevant models. OpenAI Preparedness Framework v2 (April 2025) defines five criteria for tracked capabilities and separates Capabilities Reports from Safeguards Reports. DeepMind Frontier Safety Framework v3.0 (September 2025) introduces Critical Capability Levels including a new Harmful Manipulation CCL. All three now include competitor-adjustment clauses allowing deferral if peer labs ship without comparable safeguards. Cross-lab alignment remains structural, not terminological: "Capability Thresholds," "High Capability thresholds," and "Critical Capability Levels" denote analogous constructs.

**Type:** Learn
**Languages:** none
**Prerequisites:** Phase 18 · 17 (WMDP), Phase 18 · 07-09 (deception failures)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 描述 Anthropic 的 ASL 等级结构，以及是什么激活了 ASL-3。
- 说出 OpenAI Preparedness Framework v2 追踪能力的五条判据。
- 描述 DeepMind 的关键能力等级（CCL）结构与有害操纵 CCL。
- 解释竞争者调整条款，以及它们为什么对竞赛动力学很重要。
- 定义安全论证（safety case），并描述其三支柱结构（监控、不可读性、无能力）。

> Describe Anthropic's ASL tier structure and what activated ASL-3.
> Name the five OpenAI Preparedness Framework v2 criteria for tracked capabilities.
> Describe DeepMind's Critical Capability Level structure and the Harmful Manipulation CCL.
> Explain the competitor-adjustment clauses and why they matter for race dynamics.
> Define a safety case and describe the three-pillar structure (monitoring, illegibility, incapability).

## The Problem · 问题所在

第 7-17 课确立了：欺骗是可能的，双重用途能力存在，而评估有其局限。一家拥有前沿能力模型的实验室需要一套内部治理结构，它要：
- 定义何时需要新安全措施的阈值。
- 定义扩展之前必须完成的评估。
- 描述安全论证长什么样。
- 处理竞赛动力学问题（如果竞争者不带安全措施就发布，你怎么办？）。

这三个 2025-2026 年的框架就是当前最先进的实践——不完美、仍在演化，而且各实验室之间已足够对齐，以至于治理问题如今是「这些框架够不够」，而不是「要不要有框架」。

> Lessons 7-17 establish that deception is possible, dual-use capability exists, and evaluation has limits. A lab with a frontier-capable model needs an internal governance structure that:
> - Defines thresholds for when new safeguards are required.
> - Defines required evaluations before scaling.
> - Describes what a safety case looks like.
> - Handles the race-dynamic problem (if competitors ship without safeguards, what do you do?).
> The three 2025-2026 frameworks are the state of the art — imperfect, evolving, and aligned enough across labs that the governance question is now whether the frameworks are adequate, not whether they exist.

## The Concept · 概念

### Anthropic Responsible Scaling Policy v3.0 (February 2026) · Anthropic 负责任扩展政策 v3.0（2026 年 2 月）

ASL 结构：
- ASL-1：不是前沿模型（被弱于前沿的基线所涵盖）。
- ASL-2：当前的前沿基线；以常规安全措施部署。
- ASL-3：灾难性误用的风险显著更高；CBRN 相关能力。2025 年 5 月激活。
- ASL-4：越过 AI R&D-2 阈值；能自动化入门级 AI 研究的模型。
- ASL-5+：高级 AI R&D；能极大加速有效扩展的模型。

v3.0 的新内容：
- Frontier Safety Roadmaps（以脱敏形式公开）。
- Risk Reports（每季度，部分经外部评审）。
- AI R&D 被拆分为 AI R&D-2 与 AI R&D-4。
- 一旦越过 AI R&D-4，就要求一份肯定式安全论证，识别模型追求未对齐目标所带来的未对齐风险。

> ASL structure:
> - ASL-1: not a frontier model (subsumed by weaker-than-frontier baseline).
> - ASL-2: current frontier baseline; deployed with usual safeguards.
> - ASL-3: substantially higher risk of catastrophic misuse; CBRN-relevant capabilities. Activated May 2025.
> - ASL-4: AI R&D-2 crossing threshold; models that can automate entry-level AI research.
> - ASL-5+: advanced AI R&D; models that dramatically accelerate effective scaling.
> New in v3.0:
> - Frontier Safety Roadmaps (public in redacted form).
> - Risk Reports (quarterly, some externally reviewed).
> - AI R&D is disaggregated into AI R&D-2 and AI R&D-4.
> - Once AI R&D-4 is crossed, an affirmative safety case is required, identifying misalignment risks from models pursuing misaligned goals.

### OpenAI Preparedness Framework v2 (April 15, 2025) · OpenAI Preparedness Framework v2（2025 年 4 月 15 日）

五条受追踪能力的判据：
- **Plausible（合理存在）。** 存在合理的威胁模型。
- **Measurable（可测量）。** 可以做实证评估。
- **Severe（严重）。** 伤害巨大。
- **Net-new（全新）。** 不是既有风险被放大。
- **Instantaneous-or-irremediable（瞬时或不可挽回）。** 伤害发生极快，或无法撤销。

同时满足五条的能力会被追踪。其余不会。

PF v2 的其他结构：
- 把 Capabilities Reports（模型能做什么）与 Safeguards Reports（存在哪些管控）分开。
- Safety Advisory Group 评审。
- 领导层批准；董事会的 Safety & Security Committee 监督。
- 「调整条款（Adjustment clause）」：如果另一家实验室不带可比安全措施就发布，OpenAI 可以降低要求。

> Five criteria for tracked capabilities:
> - **Plausible.** Reasonable threat model exists.
> - **Measurable.** Empirical evaluation possible.
> - **Severe.** Harm is large.
> - **Net-new.** Not a pre-existing risk scaled up.
> - **Instantaneous-or-irremediable.** Harm occurs fast or cannot be undone.
> Capabilities that meet all five are tracked. Others are not.
> Other PF v2 structure:
> - Separate Capabilities Reports (what the model can do) from Safeguards Reports (what controls exist).
> - Safety Advisory Group reviews.
> - Leadership approves; Board's Safety & Security Committee oversees.
> - "Adjustment clause": OpenAI may reduce requirements if another lab ships without comparable safeguards.

### DeepMind Frontier Safety Framework v3.0 (September 2025) · DeepMind 前沿安全框架 v3.0（2025 年 9 月）

按领域划分的关键能力等级（Critical Capability Levels, CCL）：
- Bioweapon Uplift（生物武器增强）
- Cyber Uplift（网络增强）
- ML R&D Acceleration（机器学习研发加速）
- Harmful Manipulation（有害操纵，v3.0 新增）：能在高风险情境中实质性改变信念/行为的模型。

v2.0（2025 年 2 月）新增了 Deceptive Alignment 章节，并为 ML R&D CCL 设定了更高的安全等级。

> Critical Capability Levels (CCLs) by domain:
> - Bioweapon Uplift
> - Cyber Uplift
> - ML R&D Acceleration
> - Harmful Manipulation (new in v3.0): models that could substantially change beliefs/behavior in high-stakes contexts.
> v2.0 (February 2025) added a Deceptive Alignment section and higher security levels for ML R&D CCLs.

### Cross-lab alignment · 跨实验室对齐

- Anthropic 的「Capability Thresholds（能力阈值）」。
- DeepMind 的「Critical Capability Levels（关键能力等级）」。
- OpenAI 的「High Capability thresholds（高能力阈值）」。

没有行业统一术语。结构上是对齐的：三个层级的前沿能力，配有公开的评估标准。三家从 2025 年起都包含竞争者调整条款。

> Anthropic "Capability Thresholds."
> DeepMind "Critical Capability Levels."
> OpenAI "High Capability thresholds."
> No industry-standard terminology. Structurally aligned: three tiers of frontier capability with published evaluation criteria. All three include competitor-adjustment clauses (2025 onward).

### Safety cases · 安全论证

安全论证（safety case）是一份书面论证，说明在最坏情况假设下某次部署是可接受地安全的。标准结构瞄准三根支柱：

- **监控（Monitoring）。** 如果坏行为发生，我们能检测到吗？
- **不可读性（Illegibility）。** 模型是否缺乏执行一个连贯致害计划的能力？
- **无能力（Incapability）。** 模型是否缺乏造成所述伤害的能力？

不同的安全论证瞄准不同的支柱。ASL-3 的 CBRN 论证以无能力（通过遗忘实现）为主要目标。欺骗性对齐的论证以监控与不可读性为目标。网络增强的论证则三者都相关。

> A safety case is a written argument that a deployment is acceptably safe under worst-case assumptions. The standard structure targets three pillars:
> - **Monitoring.** Can we detect bad behaviour if it occurs?
> - **Illegibility.** Does the model lack the ability to execute a coherent plan to cause harm?
> - **Incapability.** Does the model lack the capability to cause the harm in question?
> Different safety cases target different pillars. For a ASL-3 CBRN case, incapability (via unlearning) is the primary target. For deceptive alignment, monitoring and illegibility are targets. For cyber uplift, all three are relevant.

### The race-dynamic problem · 竞赛动力学问题

竞争者调整条款是有争议的。批评者认为它制造了逐底竞争：如果三家实验室都会在对手「叛逃」时降低要求，均衡就会向叛逃偏移。辩护者则认为，如果叛逃的那家实验室安全意识更差，那么另一种做法（单边安全措施）会带来更糟的结果。

UK AISI、US CAISI 与 EU AI Office（第 24 课）是外部治理的对应机构。实验室框架是自愿性的；监管框架正在成形。

> Competitor-adjustment clauses are controversial. Critics argue they create a race to the bottom: if all three labs will reduce requirements when a competitor defects, the equilibrium shifts toward defection. Defenders argue the alternative (unilateral safeguards) produces worse outcomes if the defecting lab is less safety-conscious.
> UK AISI, US CAISI, and EU AI Office (Lesson 24) are the external governance counterparts. The lab frameworks are voluntary; the regulatory frameworks are emerging.

### Where this fits in Phase 18 · 在第 18 阶段中的位置

第 17-18 课是叠加在欺骗与红队分析之上的测量与治理层。第 19-24 课覆盖福利、偏见、隐私、水印与监管结构。第 28 课描绘把这些评估落地为实践的研发生态（MATS、Redwood、Apollo、METR）。

```figure
al-asl-ladder
```

> Lessons 17-18 are the measurement-and-governance layer on top of the deception and red-team analyses. Lessons 19-24 cover welfare, bias, privacy, watermarking, and regulatory structure. Lesson 28 maps the research ecosystem (MATS, Redwood, Apollo, METR) that operationalizes the evaluations.

## Use It · 实战用法

本课没有代码。阅读三份一手材料：RSP v3.0、PF v2、FSF v3.0。把每家实验室的等级结构相互映射，并找出每一家定义了而其他两家没有定义的一个阈值。

> No code for this lesson. Read the three primary sources: RSP v3.0, PF v2, FSF v3.0. Map each lab's tier structure to the others and identify one threshold each lab defines that the others do not.

## Ship It · 交付

本课产出 `outputs/skill-framework-diff.md`。给定一份安全框架或发布说明，它会把该框架的阈值定义、所需评估与安全论证结构，与 RSP v3.0、PF v2、FSF v3.0 逐一比对，并标出跨实验室的缺口。

> This lesson produces `outputs/skill-framework-diff.md`. Given a safety framework or release note, it compares the framework's threshold definitions, evaluations required, and safety-case structure against RSP v3.0, PF v2, FSF v3.0 and flags cross-lab gaps.

## Exercises · 练习

1. 阅读 RSP v3.0、PF v2 与 FSF v3.0。编制一张表：每家实验室的 CBRN 阈值、各自的 AI R&D 阈值，以及各自要求的部署前评估。

2. 竞争者调整条款在三个框架（2025 年起）中都有。写一段支持它的论证；再写一段反对它的论证。指出每个立场依赖的假设。

3. 为一个即将越过 Anthropic AI R&D-4 阈值的模型设计安全论证。说出三根支柱（监控、不可读性、无能力）各自需要的证据。

4. DeepMind 的 FSF v3.0 引入了有害操纵 CCL。提出三项能表明模型已越过该阈值的实证测量。

5. 阅读 METR 的「Common Elements of Frontier AI Safety Policies」（2025）。说出三个最强的跨实验室趋同点与两个最大的分歧点。

> 1. Read RSP v3.0, PF v2, and FSF v3.0. Compile a table of each lab's CBRN threshold, each's AI R&D threshold, and each's required pre-deployment evaluation.
> 2. The competitor-adjustment clause is in all three frameworks (2025+). Write one paragraph arguing for it; write one paragraph arguing against. Identify the assumption each position depends on.
> 3. Design a safety case for a model crossing Anthropic's AI R&D-4 threshold. Name the evidence each of the three pillars (monitoring, illegibility, incapability) requires.
> 4. DeepMind's FSF v3.0 introduces a Harmful Manipulation CCL. Propose three empirical measurements that would indicate a model has crossed this threshold.
> 5. Read METR's "Common Elements of Frontier AI Safety Policies" (2025). Name the three strongest cross-lab convergences and the two largest divergences.

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|-----------------|------------------------|
| RSP | 「Anthropic 的框架」 | Responsible Scaling Policy；ASL 等级；v3.0，2026 年 2 月 |
| PF | 「OpenAI 的框架」 | Preparedness Framework；五条判据；v2，2025 年 4 月 |
| FSF | 「DeepMind 的框架」 | Frontier Safety Framework；CCL；v3.0，2025 年 9 月 |
| ASL-3 | 「类比生物安全 3 级」 | Anthropic 针对 CBRN 相关能力的等级；2025 年 5 月激活 |
| CCL | 「关键能力等级」 | DeepMind 的阈值构造；按领域划分 |
| Safety case | 「那份正式论证」 | 在最坏情况假设下说明部署可接受安全的书面论证 |
| Adjustment clause | 「允许竞争者叛逃」 | 当竞争者不带可比安全措施发布时降低要求的框架条款 |

## Further Reading · 延伸阅读

- [Anthropic — Responsible Scaling Policy v3.0 (February 2026)](https://www.anthropic.com/responsible-scaling-policy) —— ASL 等级、路线图、AI R&D 拆分
- [OpenAI — Updating the Preparedness Framework (April 15, 2025)](https://openai.com/index/updating-our-preparedness-framework/) —— 五条判据、调整条款
- [DeepMind — Strengthening our Frontier Safety Framework (September 2025)](https://deepmind.google/blog/strengthening-our-frontier-safety-framework/) —— CCL v3.0、有害操纵
- [METR — Common Elements of Frontier AI Safety Policies (2025)](https://metr.org/blog/2025-03-26-common-elements-of-frontier-ai-safety-policies/) —— 跨实验室比较
