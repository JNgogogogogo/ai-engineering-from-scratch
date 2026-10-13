# Anthropic Responsible Scaling Policy v3.0 · Anthropic 负责任扩展政策 v3.0

> RSP v3.0 于 2026 年 2 月 24 日生效，取代 2023 年政策。两级缓解：Anthropic 将单方面做什么 vs 哪些被表述为全行业建议（包含 RAND SL-4 安全标准）。把 Frontier Safety Roadmap 和 Risk Report 设为常设文件，而不是一次性交付物。删除了 2023 年的暂停承诺。引入 AI R&D-4 阈值：一旦跨越，Anthropic 必须发布一份肯定性论证，指明对齐失误风险与缓解措施。Claude Opus 4.6 未跨越该阈值。Anthropic 在 v3.0 公告中表示，「自信地排除这一点正变得困难」。SaferAI 给 2023 版 RSP 打了 2.2 分；他们将 v3.0 下调至 1.9，把 Anthropic 与 OpenAI、DeepMind 一起归入「弱」RSP 类别。定性阈值取代了 2023 年的定量承诺；删除暂停条款是最尖锐的退步。

> RSP v3.0 went into effect February 24, 2026, replacing the 2023 policy. Two-tier mitigation: what Anthropic will do unilaterally vs what is framed as an industry-wide recommendation (including RAND SL-4 security standards). Adds Frontier Safety Roadmaps and Risk Reports as standing documents rather than one-off deliverables. Drops the 2023 pause commitment. Introduces the AI R&D-4 threshold: once crossed, Anthropic must publish an affirmative case identifying misalignment risks and mitigations. Claude Opus 4.6 does not cross it. Anthropic states in the v3.0 announcement that "confidently ruling this out is becoming difficult." SaferAI rated the 2023 RSP at 2.2; they downgraded v3.0 to 1.9, putting Anthropic in the "weak" RSP category alongside OpenAI and DeepMind. Qualitative thresholds replaced the 2023 quantitative commitments; removing the pause clause is the sharpest regression.

**类型：** Learn
**语言：** Python（标准库，RSP 阈值决策引擎）
**前置：** Phase 15 · 06（AAR）、Phase 15 · 07（RSI）
**时间：** ~45 分钟

## The Problem · 问题

前沿实验室发布的扩展政策，一部分是技术文档，一部分是治理文档，还有一部分是发给监管者的信号。RSP v3.0 是 Anthropic 目前的文档。仔细读它的原因不在于遵守它有约束力（并没有），而在于它的框架塑造了一个实验室如何构想灾难性风险、以及如何向公众传达权衡。

v3.0 对 v2.0 的 diff 是最有用的分析单元。新增了什么：Frontier Safety Roadmap、Risk Report、AI R&D-4 阈值。删掉了什么：2023 年的暂停承诺。重构了什么：一份拆分为「Anthropic 单方面」和「行业建议」的两级缓解表。外部评审方 SaferAI 把评分从 2.2（v2）下调到 1.9（v3.0）。这就是一份扩展政策如何在看起来更精致的同时变得更不严格。

> Frontier labs publish scaling policies that are partly technical documents, partly governance documents, and partly signals to regulators. RSP v3.0 is the current Anthropic document. Reading it closely matters not because compliance with it is binding (it is not), but because the framing shapes how a lab conceives of catastrophic risk and how they communicate trade-offs to the public.
> The v3.0 vs v2.0 diff is the useful unit. What got added: Frontier Safety Roadmaps, Risk Reports, the AI R&D-4 threshold. What got removed: the 2023 pause commitment. External review — SaferAI — downgraded the score from 2.2 (v2) to 1.9 (v3.0). This is how a scaling policy can get less rigorous while looking more polished.

## The Concept · 概念

### The two-tier mitigation schedule · 两级缓解措施表

- **Anthropic 单方面行动**：无论其他实验室做什么，Anthropic 都会做的事。超过阈值即停止训练、特定安全措施、特定部署闸门。
- **全行业建议**：Anthropic 认为行业应该共同做的事。包括 RAND SL-4 安全标准。这些不是 Anthropic 一方的承诺；它们是政策倡导。

两级结构在 v2 中并不存在。它意味着读者必须看清每条承诺落在哪一栏。「全行业建议」栏里的安全措施不是 Anthropic 的承诺；它是 Anthropic 的期望。

> Anthropic unilateral actions: what Anthropic will do regardless of what other labs do. Training stops above a threshold, specific security measures, specific deployment gates.
> Industry-wide recommendations: what Anthropic thinks the industry should do collectively. Includes RAND SL-4 security standards. These are not commitments on Anthropic's side; they are policy advocacy.
> The two-tier structure was not in v2. It means that a reader needs to look at which column each commitment lives in. A security measure in the "industry-wide recommendation" column is not Anthropic's promise; it is Anthropic's hope.

### The AI R&D-4 threshold · AI R&D-4 阈值

这是 RSP v3.0 点名的下一个重要能力阈值。具体说：一个能以有竞争力的成本自动化相当大比例 AI 研究的模型。一旦 Anthropic 相信某个模型跨越了它，他们必须在继续扩展之前发布一份肯定性论证，指明对齐失误风险与缓解措施。

按 v3.0 公告，Claude Opus 4.6 未跨越该阈值。文档还补充道：「自信地排除这一点正变得困难。」这个措辞很重要；它承认阈值近到已经成为一个现实的关切，而不是一个思辨性的极限。

第 6 课（自动化对齐研究）和第 7 课（递归自我改进）直接通向这个阈值。自动化对齐研究员跨过研究质量门槛，就是 AI R&D-4 阈值正在逼近的证据。

> This is the capability level RSP v3.0 names as the important next threshold. Specifically: a model that could automate a substantial fraction of AI research at competitive cost. Once Anthropic believes a model crosses it, they must publish an affirmative case identifying misalignment risks and mitigations before continued scaling.
> Claude Opus 4.6 does not cross it per the v3.0 announcement. The document adds: "confidently ruling this out is becoming difficult." That phrasing matters; it concedes that the threshold is close enough to be a live concern, not a speculative limit.

### Frontier Safety Roadmaps and Risk Reports · Frontier Safety Roadmap 与 Risk Report

v3.0 把两类工件提升为常设文档：

- **Frontier Safety Roadmap（前沿安全路线图）**：前瞻性文档，描述计划中的安全工作、能力预期和缓解研究。
- **Risk Report（风险报告）**：针对发布后特定模型的回顾性文档，描述观测到的能力与残余风险。

两者都公开。两者都按声明的节奏更新。其效用在于：读者可以拿 Anthropic 在 Roadmap 里说要做什么，与他们在 Risk Report 里报告做了什么，进行对照追踪。

> Frontier Safety Roadmap: forward-looking document describing planned safety work, capability expectations, and mitigation research.
> Risk Report: retrospective document on specific models after release, describing observed capability and residual risk.
> Both are public. Both are updated on a declared cadence. The utility is: reader can track how what Anthropic said they would do in a Roadmap compares to what they report in a Risk Report.

### Removing the pause clause · 移除暂停条款

2023 版 RSP 包含明确的暂停承诺：如果模型跨越特定能力阈值，训练将暂停，直到缓解措施到位。v3.0 用更软的表述取代了明确暂停（发布一份肯定性论证，若缓解措施充分则继续）。SaferAI 和其他分析者直接指出这是新文档中最严重的退步。

支持这一改动的政策论证是：2023 年的定量阈值到 2026 年代的能力基准下已不可达，因为基准本身被重新标定了。反驳是：扩展政策里的暂停条款是一件承诺装置；删掉它就删掉了政策的可信度。

> The 2023 RSP included an explicit pause commitment: if a model crossed specific capability thresholds, training would pause until mitigations were in place. v3.0 replaces the explicit pause with a softer formulation (publish an affirmative case, proceed if mitigations are adequate). SaferAI and other analysts called this out directly as the strongest regression in the new document.
> The policy argument for the change: quantitative thresholds in 2023 turned out to be unreachable by 2026-era capability benchmarks because the benchmarks themselves were re-scaled. The counter-argument: a pause clause in a scaling policy is a commitment device; removing it removes the credibility of the policy.

### SaferAI's downgrade · SaferAI 的降级

SaferAI 是一个给 RSP 类文档打分的独立组织。他们的公开评分：2023 版 Anthropic RSP 得 2.2（量表上 4.0 是当前最好的 RSP，1.0 是名义性的）。v3.0 得 1.9。这使 Anthropic 从「中等」掉到「弱」，与 OpenAI 和 DeepMind 同列弱档。

按 SaferAI 的说法，降级因素：

- 定性阈值取代了定量阈值。
- 暂停承诺被移除。
- AI R&D-4 阈值的缓解措施被描述为「肯定性论证」而不是具体措施。
- 评审机制依赖 Anthropic 的安全顾问组（Safety Advisory Group），独立监督有限。

> SaferAI is an independent organization that rates RSP-style documents. Their public rating: 2023 Anthropic RSP scored 2.2 (out of a scale where 4.0 is the best current RSP and 1.0 is nominal). v3.0 scored 1.9. This moved Anthropic from "moderate" to "weak," joining OpenAI and DeepMind in the weak category.
> The downgrade factors per SaferAI: qualitative thresholds replaced quantitative ones. Pause commitment removed. AI R&D-4 threshold mitigations are described as "affirmative case" rather than specific measures. Review mechanisms depend on Anthropic's Safety Advisory Group, with limited independent oversight.

### What this lesson is not · 本课不是什么

这不是一门合规课。RSP v3.0 不是法规；没有任何东西强制 Anthropic 遵守它。本课的价值在于带着它应得的精确性和怀疑精神去读这份文档。扩展政策是前沿实验室对外发出的关于灾难性风险姿态的首要公开信号。把它们读好，是任何工作依赖前沿能力的人的一项实用技能。

> This is not a lesson in compliance. RSP v3.0 is not a regulation; nothing forces Anthropic to follow it. The lesson is in reading the document with the specificity and skepticism it deserves. Scaling policies are the primary public signal frontier labs emit about catastrophic-risk posture. Reading them well is a practical skill for anyone whose work depends on frontier capabilities.

```figure
a5-rsp-ladder
```

## Use It · 实战用法

`code/main.py` 实现了一个小型决策引擎，镜像 RSP 阈值评估的形态：给定一个候选模型和一组能力测量，返回 AI R&D-4 阈值是否被跨越、所需的肯定性论证章节，以及部署能否继续。它有意保持简单；重点是让文档的逻辑显式化。

> `code/main.py` implements a small decision engine that mirrors the RSP threshold-evaluation shape: given a candidate model and a set of capability measurements, return whether the AI R&D-4 threshold is crossed, the required affirmative-case sections, and whether deployment can proceed. It's intentionally simple; the point is to make the document's logic explicit.

## Ship It · 交付

`outputs/skill-scaling-policy-review.md` 对照 v3.0 参考评审一份扩展政策（Anthropic、OpenAI、DeepMind 或内部）：两级结构、阈值、暂停承诺、独立评审。

> `outputs/skill-scaling-policy-review.md` reviews a scaling policy (Anthropic, OpenAI, DeepMind, or internal) against the v3.0 reference: two-tier structure, thresholds, pause commitments, independent review.

## Exercises · 练习

1. 运行 `code/main.py`。喂入三个不同能力水平的合成模型。确认阈值评估器行为符合预期并产出正确的肯定性论证模板。

2. 完整阅读 RSP v3.0（32 页）。找出落在「全行业建议」层的每一条承诺。其中哪些在 v2 里本应是「Anthropic 单方面」？

3. 阅读 SaferAI 的 RSP 评分方法论。把他们的量规应用到文档上，复现他们对 v3.0 的 1.9 分。哪一行量规对降级的贡献最大？

4. 2023 年的暂停承诺被移除了。提出一个替代承诺，既承认 2026 年基准重标定的问题，又保住政策的可信度。

5. 把 RSP v3.0 与 OpenAI Preparedness Framework v2（第 20 课）对比。选出一个 v3.0 更强的地方，再选出一个 Preparedness Framework 更强的地方。

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|---|---|---|
| RSP | 「Anthropic 的扩展政策」 | Responsible Scaling Policy；v3.0 于 2026 年 2 月 24 日生效 |
| AI R&D-4 | 「研究自动化阈值」 | 以有竞争力的成本自动化大量 AI 研究的能力 |
| Affirmative case | 「安全性论证」 | 公开发表的论证：风险已被识别、缓解措施充分 |
| Frontier Safety Roadmap | 「前瞻计划」 | 关于计划安全工作与预期能力的常设文档 |
| Risk Report | 「模型回顾」 | 关于发布后观测能力与残余风险的常设文档 |
| Two-tier mitigation | 「单方面 vs 行业」 | Anthropic 承诺与行业建议分列 |
| Pause commitment | 「2023 条款」 | 暂停训练的明确承诺；v3.0 中移除 |
| SaferAI rating | 「独立 RSP 评分」 | 第三方量规；v3.0 得 1.9（v2 为 2.2） |

## Further Reading · 延伸阅读

- [Anthropic — Responsible Scaling Policy v3.0](https://anthropic.com/responsible-scaling-policy/rsp-v3-0) — 全部 32 页政策。
- [Anthropic — RSP v3.0 announcement](https://www.anthropic.com/news/responsible-scaling-policy-v3) — 相对 v2 的变更摘要。
- [Anthropic — Frontier Safety Roadmap](https://www.anthropic.com/responsible-scaling-policy/roadmap) — 从 RSP v3.0 链接的常设文档。
- [Anthropic — Risk Report: February 2026](https://www.anthropic.com/feb-2026-risk-report) — 对 Claude Opus 4.6（发布时的前沿模型）的回顾。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 把 AI R&D-4 与实测自主性联系起来。
