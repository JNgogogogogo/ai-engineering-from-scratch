# Alignment Research Ecosystem — MATS, Redwood, Apollo, METR · 对齐研究生态 —— MATS、Redwood、Apollo、METR

> 五家机构定义了 2026 年实验室之外的对齐研究层。MATS（ML Alignment & Theory Scholars）：自 2021 年底以来 527+ 名研究者、180+ 篇论文、10K+ 引用、h 指数 47；2024 年夏季班以 501(c)(3) 形式注册，约 90 名学者和 40 名导师；2025 年之前的校友中 80% 从事安全/安保工作，其中 200+ 人在 Anthropic、DeepMind、OpenAI、UK AISI、RAND、Redwood、METR、Apollo。Redwood Research：由 Buck Shlegeris 创立的应用对齐实验室；提出了 AI Control（第 10 课）；与 UK AISI 合作控制类安全论证（control safety cases）。Apollo Research：面向前沿实验室的部署前 scheming 评估；撰写了 In-Context Scheming（第 8 课）与 Towards Safety Cases for AI Scheming。METR（Model Evaluation and Threat Research）：基于任务的能力评估、自主任务时间视界（time-horizon）研究；「Common Elements of Frontier AI Safety Policies」对比各实验室框架。Eleos AI Research：模型福祉（model welfare）部署前评估（第 19 课）；实施了 Claude Opus 4 福祉评估。

> Five organisations define the 2026 non-lab alignment research layer. MATS (ML Alignment & Theory Scholars): 527+ researchers since late 2021, 180+ papers, 10K+ citations, h-index 47; summer 2024 cohort incorporated as 501(c)(3) with ~90 scholars and 40 mentors; 80% of pre-2025 alumni work on safety/security with 200+ at Anthropic, DeepMind, OpenAI, UK AISI, RAND, Redwood, METR, Apollo. Redwood Research: applied alignment lab founded by Buck Shlegeris; introduced AI Control (Lesson 10); collaborates with UK AISI on control safety cases. Apollo Research: pre-deployment scheming evaluations for frontier labs; authored In-Context Scheming (Lesson 8) and Towards Safety Cases for AI Scheming. METR (Model Evaluation and Threat Research): task-based capability evaluations, autonomous-task time-horizon studies; "Common Elements of Frontier AI Safety Policies" compares lab frameworks. Eleos AI Research: model-welfare pre-deployment evaluations (Lesson 19); conducted Claude Opus 4 welfare assessment.

**Type:** Learn
**Languages:** none
**Prerequisites:** Phase 18 · 01-27 (prior Phase 18 lessons)
**Time:** ~45 minutes

## Learning Objectives · 学习目标

- 识别非实验室对齐研究生态的五家机构及其核心产出。
- 描述 MATS 的规模（学者数、论文数、h 指数）及其人才管道角色。
- 描述 Redwood 的 AI Control 议程及其与 UK AISI 的合作关系。
- 描述 METR 基于任务的评估方法论。

> Identify the five organisations of the non-lab alignment research ecosystem and their core output.
> Describe MATS's scale (scholars, papers, h-index) and its role as a talent pipeline.
> Describe Redwood's AI Control agenda and its partnership with UK AISI.
> Describe METR's task-based evaluation methodology.

## The Problem · 问题

前沿实验室（第 18 课）在内部产出安全评估，并挑选部分结果发表。实验室之外的生态，是评估被验证的地方，是新失效模式最先被发现的地方，也是人才被训练出来的地方。理解这个生态，有助于判断哪些研究结论被谁信任。

> The frontier labs (Lesson 18) produce safety evaluations internally and publish selected results. The ecosystem outside the labs is where the evaluations are validated, where novel failure modes are first discovered, and where talent is trained. Understanding the ecosystem helps interpret which research findings are trusted by whom.

## The Concept · 概念

### MATS (ML Alignment & Theory Scholars) · MATS（ML 对齐与理论学者计划）

始于 2021 年底。一个研究导师制项目；学者与一位资深研究员共事 10-12 周，攻一个具体的对齐问题。

规模（2026 年）：
- 自创立以来 527+ 名研究者。
- 发表 180+ 篇论文。
- 10K+ 引用。
- h 指数 47。
- 2024 年夏：90 名学者 + 40 名导师；注册为 501(c)(3)。

职业去向：2025 年之前的校友约 80% 在做安全/安保工作。200+ 人任职于 Anthropic、DeepMind、OpenAI、UK AISI、RAND、Redwood、METR、Apollo。

> Started late 2021. Research mentorship program; scholars spend 10-12 weeks with a senior researcher on a specific alignment problem. ... Career outcomes: ~80% of pre-2025 alumni are working on safety/security. 200+ at Anthropic, DeepMind, OpenAI, UK AISI, RAND, Redwood, METR, Apollo.

### Redwood Research

应用对齐实验室。由 Buck Shlegeris 创立。提出了 AI Control 议程（第 10 课）。与 UK AISI 合作控制类安全论证（control safety cases）。为 DeepMind 与 Anthropic 的评估设计提供咨询。

代表论文：Greenblatt, Shlegeris et al., "AI Control"（arXiv:2312.06942，ICML 2024）；Alignment Faking（Greenblatt, Denison, Wright et al.，arXiv:2412.14093，与 Anthropic 合作）。

风格：具体的威胁模型、最坏情况的对手、可被压力测试的具体协议。

> Applied alignment lab. Founded by Buck Shlegeris. Introduced the AI Control agenda (Lesson 10). Collaborates with UK AISI on control safety cases. Advises DeepMind and Anthropic on evaluation design.
> Canonical papers: Greenblatt, Shlegeris et al., "AI Control" (arXiv:2312.06942, ICML 2024); Alignment Faking (Greenblatt, Denison, Wright et al., arXiv:2412.14093, joint with Anthropic).
> Style: specific threat models, worst-case adversaries, concrete protocols that can be stress-tested.

### Apollo Research

面向前沿实验室的部署前 scheming 评估。撰写了 In-Context Scheming（第 8 课，arXiv:2412.04984）。是 2025 年 OpenAI 反 scheming 训练合作的参与方。产出 Towards Safety Cases for AI Scheming（2024）。

风格：在欺骗可能涌现的智能体场景中做评估；三支柱分解（错对齐 misalignment、目标导向性 goal-directedness、情境觉察 situational awareness）。

> Pre-deployment scheming evaluations for frontier labs. Authored In-Context Scheming (Lesson 8, arXiv:2412.04984). Partner on 2025 OpenAI anti-scheming training collaboration. Produces Towards Safety Cases for AI Scheming (2024).
> Style: agentic-setting evaluations where deception can emerge; three-pillar decomposition (misalignment, goal-directedness, situational awareness).

### METR (Model Evaluation and Threat Research) · METR（模型评估与威胁研究）

基于任务的能力评估。自主任务完成时间视界（time-horizon）研究。「Common Elements of Frontier AI Safety Policies」（metr.org/common-elements，2025）对比各实验室框架。

与 Apollo 共同署名 AI Scheming 安全论证草案（safety-case sketch）。

风格：长时程任务评估、实证能力测量、框架综合。

> Task-based capability evaluations. Autonomous-task completion time-horizon studies. "Common Elements of Frontier AI Safety Policies" (metr.org/common-elements, 2025) compares lab frameworks.
> Co-author on AI Scheming safety-case sketch with Apollo.
> Style: long-horizon task evaluations, empirical capability measurement, framework synthesis.

### Eleos AI Research

模型福祉（model welfare）部署前评估。实施了系统卡 5.3 节记录的 Claude Opus 4 福祉评估。为第 19 课的福祉相关结论提供外部方法论校验。

> Model-welfare pre-deployment evaluations. Conducted the Claude Opus 4 welfare assessment documented in section 5.3 of the system card. Provides the external methodology check for Lesson 19's welfare-relevant claims.

### The flow · 人才与知识的流动

MATS 训练研究者。毕业生流向 Anthropic、DeepMind、OpenAI（实验室安全团队），或流向 Redwood、Apollo、METR、Eleos（外部评估）。外部评估者与实验室以及 UK AISI / CAISI 合作。发表物又回流到生态中，为 MATS 的下一批学者供料。

> MATS trains researchers. Graduates go to Anthropic, DeepMind, OpenAI (lab safety teams) or to Redwood, Apollo, METR, Eleos (external evaluation). External evaluators partner with labs and with UK AISI / CAISI. Publications feed the ecosystem back to MATS for the next cohort.

### Why this layer matters · 这一层为什么重要

单一来源的评估不可靠：实验室评估自己的模型，存在结构性利益冲突。外部评估者能提出并验证实验室可能低报的失效模式。2024 年的 Sleeper Agents 论文（第 7 课）出自 Anthropic + Redwood；Alignment Faking 出自 Anthropic + Redwood；In-Context Scheming 出自 Apollo；Anti-Scheming 出自 Apollo + OpenAI。多机构结构就是质量控制。

> Single-source evaluations are unreliable: labs evaluating their own models have a structural conflict of interest. External evaluators can raise and validate failure modes the lab may underreport. The 2024 Sleeper Agents paper (Lesson 7) was Anthropic + Redwood; Alignment Faking was Anthropic + Redwood; In-Context Scheming was Apollo; Anti-Scheming was Apollo + OpenAI. The multi-org structure is the quality control.

### Where this fits in Phase 18 · 在 Phase 18 中的位置

第 7-11 课引用了 Redwood 与 Apollo 的工作；第 18 课引用了 METR 的框架对比；第 19 课引用了 Eleos。第 28 课是这个生态的显式机构地图 —— Phase 的其余课程都依赖这个生态。

> Lessons 7-11 reference Redwood and Apollo work; Lesson 18 references METR's framework comparison; Lesson 19 references Eleos. Lesson 28 is the explicit organisational map for the ecosystem the rest of the Phase relies on.

```figure
sae-features
```

## Use It · 实战用法

无代码。阅读 METR 的「Common Elements of Frontier AI Safety Policies」，看外部综合如何为实验室内部的政策工作增值。

> No code. Read METR's "Common Elements of Frontier AI Safety Policies" as an example of how external synthesis adds value to lab-internal policy work.

## Ship It · 交付

本课产出 `outputs/skill-ecosystem-map.md`。给定一个对齐结论或评估，它会识别所属机构、发表载体和方法论风格，并与已知的对应机构做交叉核对。

> This lesson produces `outputs/skill-ecosystem-map.md`. Given an alignment claim or evaluation, it identifies the organisation, the publication venue, and the methodological style, and cross-checks against known-counterpart organisations.

## Exercises · 练习

1. 从第 7-15 课中挑一篇论文，识别参与的机构。把作者与 MATS 校友及当前生态中的任职做交叉核对。

2. 阅读 METR 的「Common Elements of Frontier AI Safety Policies」。找出他们强调的三个跨实验室趋同点和两个最大的分歧点。

3. MATS 的职业去向约 80% 是安全/安保。论证这种选择压力究竟是适应性的（训练了这个领域）还是有偏的（过滤掉了非主流立场）。

4. Redwood 和 Apollo 都做控制/scheming 工作，但风格不同。挑一个失效模式，描述各自会怎么研究它。

5. Eleos AI 是唯一纯粹的模型福祉机构。设计一个假想中的第二家机构，聚焦另一个与福祉相邻的问题（认知自由、机器人具身等），并阐明其方法论。

> Pick one paper from Lessons 7-15 and identify the organisations involved. Cross-check the authors against MATS alumni and current ecosystem affiliations. ... MATS career outcomes are ~80% safety/security. Argue whether this selection pressure is adaptive (trains the field) or biased (filters out heterodox positions).

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|------------------------|
| MATS | 「那个导师制项目」 | ML Alignment & Theory Scholars；2021 年以来 527+ 名研究者 |
| Redwood Research | 「控制实验室」 | 应用对齐；AI Control 作者；UK AISI 合作方 |
| Apollo Research | 「scheming 评估」 | 面向前沿实验室的部署前 scheming 评估 |
| METR | 「任务时界评估」 | 基于任务的能力评估；框架综合 |
| Eleos AI | 「福祉实验室」 | 模型福祉部署前评估 |
| Talent pipeline | 「MATS -> 实验室」 | MATS 毕业生流向 Anthropic、DM、OpenAI、Redwood、Apollo、METR |
| External evaluation | 「非实验室检查」 | 不由模型生产方执行的评估；增加可信度 |

## Further Reading · 延伸阅读

- [MATS (ML Alignment & Theory Scholars)](https://www.matsprogram.org/) — 那个导师制项目
- [Redwood Research](https://www.redwoodresearch.org/) — AI Control 论文
- [Apollo Research](https://www.apolloresearch.ai/) — scheming 评估
- [METR — Common Elements of Frontier AI Safety Policies](https://metr.org/blog/2025-03-26-common-elements-of-frontier-ai-safety-policies/) — 框架对比
- [Eleos AI Research](https://www.eleosai.org/research) — 模型福祉方法论
