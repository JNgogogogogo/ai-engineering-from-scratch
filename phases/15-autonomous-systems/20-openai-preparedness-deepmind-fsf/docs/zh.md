# OpenAI Preparedness Framework and DeepMind Frontier Safety Framework · OpenAI Preparedness Framework 与 DeepMind Frontier Safety Framework

> OpenAI Preparedness Framework v2（2025 年 4 月）引入了 Research Categories——Long-range Autonomy、Sandbagging、Autonomous Replication and Adaptation、Undermining Safeguards——与 Tracked Categories 相区分。Tracked Categories 触发 Capabilities Report 加 Safeguards Report，由安全顾问组评审。DeepMind 的 FSF v3（2025 年 9 月，2026 年 4 月 17 日新增 Tracked Capability Levels）把自主性并入 ML R&D 与 Cyber 两个领域（ML R&D autonomy level 1 = 以相对「人类 + AI 工具」有竞争力的成本完全自动化 AI R&D 流水线）。FSF v3 通过针对工具性推理滥用的自动化监测，明确处理欺骗性对齐。诚实备注：PF v2 里的 Research Categories（包括 Long-range Autonomy）不会自动触发缓解措施；政策用语是「潜在（potential）」。DeepMind 自己也说，如果工具性推理继续增强，自动化监测「从长期看将不再足够」。

> OpenAI Preparedness Framework v2 (April 2025) introduces Research Categories — Long-range Autonomy, Sandbagging, Autonomous Replication and Adaptation, Undermining Safeguards — distinct from Tracked Categories. Tracked Categories trigger Capabilities Reports plus Safeguards Reports reviewed by the Safety Advisory Group. DeepMind's FSF v3 (September 2025, with Tracked Capability Levels added April 17, 2026) folds autonomy into ML R&D and Cyber domains (ML R&D autonomy level 1 = fully automate the AI R&D pipeline at competitive cost vs human + AI tools). FSF v3 explicitly addresses deceptive alignment via automated monitoring for instrumental-reasoning misuse. The honest note: Research Categories in PF v2 (including Long-range Autonomy) do not automatically trigger mitigations; the policy language is "potential." DeepMind itself says automated monitoring "will not remain sufficient long-term" if instrumental reasoning strengthens.

**类型：** Learn
**语言：** Python（标准库，三框架决策表对比工具）
**前置：** Phase 15 · 19（Anthropic RSP）
**时间：** ~45 分钟

## The Problem · 问题

第 19 课细读了 Anthropic 的扩展政策。本课通过读 OpenAI 和 DeepMind 的文档补全全景。这三份文档是回答同一个问题的同族工件——前沿实验室何时应该暂停或给模型设闸——它们在一小组类别上趋同，又在若干关键之处分岔。

趋同之处：三者都把长程自主标记为值得追踪的能力类别。三者都承认欺骗行为（alignment faking、sandbagging）是一类具体风险。三者都有内部评审机构。分岔之处：OpenAI 把类别分成「Tracked」（强制缓解）和「Research」（无自动触发）。DeepMind 把自主性并进两个领域而不是单独命名。各家叫法是 Tracked vs Research、Critical vs Moderate、Tier-1 vs Tier-2，但一个能力落在哪个桶里，其运营后果在各家实验室并不相同。

把它们放在一起读才是有用的练习。同一个能力在 Anthropic 是「强制缓解」，在 OpenAI 是「监测但不触发」，在 DeepMind 是「在特定领域内追踪」。政策姿态很重要。

> Lesson 19 read Anthropic's scaling policy closely. This lesson completes the picture by reading OpenAI's and DeepMind's. The three documents are cousin artifacts addressing the same question — when should a frontier lab pause or gate a model — and they converge on a small set of categories and diverge in specific places that matter.
> The convergence: all three label long-range autonomy as a capability class worth tracking. All three acknowledge deceptive behavior (alignment faking, sandbagging) as a specific class of risk. All three have an internal review body. The divergence: OpenAI splits categories into "Tracked" (mandatory mitigation) and "Research" (no automatic trigger). DeepMind folds autonomy into two domains rather than naming it separately.
> Reading them together is the useful exercise. The same capability can be "mandatory mitigation" at Anthropic, "monitored but not triggering" at OpenAI, and "tracked in a specific domain" at DeepMind. The policy posture matters.

## The Concept · 概念

### OpenAI Preparedness Framework v2 (April 2025) · OpenAI Preparedness Framework v2（2025 年 4 月）

结构：

- **Tracked Categories**：触发 Capabilities Report（模型能做什么）加 Safeguards Report（已有哪些缓解措施）。部署前由安全顾问组评审。
- **Research Categories**：实验室正在追踪、但尚未承诺具体缓解措施的能力。包括 Long-range Autonomy、Sandbagging、Autonomous Replication and Adaptation、Undermining Safeguards。

v2 的关键表述：Research Categories 不会自动触发缓解措施。政策用语是「潜在（potential）」缓解。这是要盯住的具体差异：一个类别落在 Tracked 还是 Research，就是「设闸」与「观察」之间的铰链。

> Tracked Categories: trigger Capabilities Reports (what the model can do) plus Safeguards Reports (what mitigations are in place). Reviewed by the Safety Advisory Group before deployment.
> Research Categories: model capabilities the lab is tracking but not yet committing to specific mitigations. Includes Long-range Autonomy, Sandbagging, Autonomous Replication and Adaptation, Undermining Safeguards.
> Key framing in v2: Research Categories do not automatically trigger mitigations. The policy language is "potential" mitigations. This is the specific delta to watch: a category's location in Tracked vs Research is the hinge between "gated" and "observed."

### DeepMind Frontier Safety Framework v3 (September 2025; Tracked Capability Levels added April 17, 2026) · DeepMind Frontier Safety Framework v3（2025 年 9 月；2026 年 4 月 17 日新增 Tracked Capability Levels）

结构：

- **Critical Capability Levels（CCL）**：横跨五个领域的能力阈值：Cyber、Bio、ML R&D、CBRN、Autonomy（已并入 ML R&D 和 Cyber）。
- **Tracked Capability Levels**：2026 年 4 月新增的更细粒度。具体例子：ML R&D autonomy level 1 = 以相对「人类 + AI 工具」有竞争力的成本完全自动化 AI R&D 流水线。
- **欺骗性对齐监测**：对工具性推理滥用进行自动化监测的明确承诺。

自主性的框架方式与 OpenAI 不同。DeepMind 不把「Autonomy」保留为顶层领域；它被并入自主性会造成伤害的领域（ML R&D 和 Cyber）。其论证是：没有领域的自主性是有能力而无风险；反驳是：跨领域的自主性是一种框架应该点名的元风险。

> Critical Capability Levels (CCLs): capability thresholds across five domains: Cyber, Bio, ML R&D, CBRN, Autonomy (folded into ML R&D and Cyber).
> Tracked Capability Levels: additional granularity added in April 2026. Concrete example: ML R&D autonomy level 1 = fully automate the AI R&D pipeline at competitive cost vs human + AI tools.
> Deceptive alignment monitoring: explicit commitment to automated monitoring for instrumental-reasoning misuse.
> The autonomy framing differs from OpenAI's. DeepMind does not keep "Autonomy" as a top-level domain; it is folded into the domains where autonomy would cause harm (ML R&D and Cyber). The argument is that autonomy without a domain is capability without risk; the counter-argument is that autonomy across domains is a meta-risk the framework should name.

### What all three converge on · 三者的共同点

- 内部安全顾问组（分别叫 Anthropic SAG、OpenAI SAG、DeepMind 内部委员会）。对高能力模型在部署前评审。
- 明确提及欺骗性对齐 / alignment faking 这类风险。
- 按声明节奏产出的常设工件（Anthropic：Frontier Safety Roadmap、Risk Report；OpenAI：Capabilities 与 Safeguards Report；DeepMind：FSF 更新周期）。
- 承认仅靠监测的防御有上限。DeepMind 说得很明白：「自动化监测从长期看将不再足够。」

> Internal Safety Advisory Group (named Anthropic SAG, OpenAI SAG, DeepMind internal committee). Review before deployment for high-capability models.
> Explicit mention of deceptive alignment / alignment faking as a risk class. Standing artifacts on a declared cadence (Anthropic: Frontier Safety Roadmap, Risk Report; OpenAI: Capabilities and Safeguards Reports; DeepMind: FSF update cycle).
> Acknowledgement that monitoring-only defenses have a ceiling. DeepMind is explicit: "automated monitoring will not remain sufficient long-term."

### Where they diverge · 三者的分歧点

- **Anthropic**：v3.0 移除了暂停承诺；AI R&D-4 阈值是点名的下一道闸门。
- **OpenAI**：Tracked vs Research 之分；Research Categories（包括 Long-range Autonomy）不会自动设闸。
- **DeepMind**：自主性并入其他领域；2026 年 4 月新增 Tracked Capability Levels 提供更细粒度。

> Anthropic: pause commitment removed in v3.0; AI R&D-4 threshold is the named next gate.
> OpenAI: Tracked vs Research split; Research Categories (including Long-range Autonomy) do not automatically gate.
> DeepMind: autonomy folded into other domains; Tracked Capability Levels add granularity in April 2026.

### Sandbagging: a specific capability that complicates all three · Sandbagging：让三者都变复杂的一个具体能力

Sandbagging（模型在评估中策略性低水平发挥）在 OpenAI 的 Research Categories 里。Anthropic 的 RSP v3.0 通过评估情境差距处理它（第 1 课）。DeepMind 在 FSF v3 中通过欺骗性对齐监测处理它。

如果模型在评估中 sandbag，所有框架的能力阈值都会被低估。框架成立的前提是测量成立。这就是为什么在实验室自评之外，外部测量（第 21 课，METR）和对抗性评估是必要的补充。

> Sandbagging (a model strategically underperforming on evaluations) is in OpenAI's Research Categories. Anthropic's RSP v3.0 addresses it via the evaluation-context gap (Lesson 1). DeepMind addresses it via deceptive alignment monitoring in FSF v3.
> If a model sandbags on evaluations, every framework's capability thresholds are underestimated. The framework works only if the measurement works. This is why external measurement (Lesson 21, METR) and adversarial evaluation are necessary in addition to lab self-assessment.

### The policy-reading skill · 政策阅读技能

- 定位：你在乎的每一个能力都应该能在政策里找到。找不到，就说明政策不覆盖它。
- 分类：它是 Tracked（触发缓解）还是 Research（追踪但不触发）？OpenAI 点明了这一点；Anthropic 和 DeepMind 有各自的等价物。
- 节奏：政策是按声明的时间表更新，还是只在特定事件之后？声明节奏更有力。
- 独立性：外部评审是强制的还是可选的？Anthropic 与 Apollo 和美国 AI 安全研究所合作；OpenAI 与 METR；DeepMind 主要靠内部 SAG。

> Locate: every capability you care about should be findable in the policy. If not findable, the policy does not cover it.
> Classify: is it Tracked (triggers mitigation) or Research (tracked but not triggering)? OpenAI names this; Anthropic and DeepMind have their own equivalents.
> Cadence: is the policy updated on a declared schedule, or only after specific events? Declared cadence is stronger.
> Independence: is external review mandatory or optional? Anthropic partners with Apollo and US AI Safety Institute; OpenAI with METR; DeepMind with internal SAG primarily.

```figure
a5-tracked-vs-research
```

## Use It · 实战用法

`code/main.py` 实现了一个小型决策表对比工具。给定一个能力（自主性、欺骗性对齐、R&D 自动化、网络能力提升等），它输出三份政策各自如何分类该能力，以及触发什么缓解措施。它是一个阅读辅助工具，不是政策工具。

> `code/main.py` implements a small decision-table diff tool. Given a capability (autonomy, deceptive alignment, R&D automation, cyber uplift, etc.), it outputs how each of the three policies classifies the capability, and what mitigations trigger. It's a reading aid, not a policy tool.

## Ship It · 交付

`outputs/skill-cross-policy-diff.md` 以三份框架为参照，为某个具体能力产出跨政策对比。

> `outputs/skill-cross-policy-diff.md` produces a cross-policy comparison for a specific capability, using the three frameworks as reference.

## Exercises · 练习

1. 运行 `code/main.py`。针对至少两个你能对照源文档核验的能力，确认对比工具的输出与政策一致。

2. 完整阅读 OpenAI Preparedness Framework v2。找出每一个 Research Category。为每一个写一句话，说明它为什么在 Research 而不是 Tracked。

3. 完整阅读 DeepMind FSF v3，外加 2026 年 4 月的 Tracked Capability Levels 更新。找出 ML R&D autonomy level 1 的具体评估标准。你会如何从外部测量它？

4. Sandbagging 在 OpenAI 的 Research Categories 里。设计一个能迫使 sandbagging 模型暴露真实能力的评估。参考第 1 课关于评估情境博弈的讨论。

5. 选一个具体能力（自选）对比三份政策。说出你认为哪个政策的分类最严格、哪个最不严格。用源文本论证。

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|---|---|---|
| Preparedness Framework | 「OpenAI 的扩展政策」 | PF v2（2025 年 4 月）；Tracked 与 Research 类别 |
| Tracked Category | 「强制缓解」 | 触发 Capabilities + Safeguards Report；SAG 评审 |
| Research Category | 「仅监测」 | 追踪但无自动缓解；包括 Long-range Autonomy |
| Frontier Safety Framework | 「DeepMind 的扩展政策」 | FSF v3（2025 年 9 月）+ Tracked Capability Levels（2026 年 4 月） |
| CCL | 「Critical Capability Level」 | DeepMind 按领域的阈值（Cyber、Bio、ML R&D、CBRN） |
| ML R&D autonomy level 1 | 「R&D 自动化」 | 以有竞争力的成本完全自动化 AI R&D 流水线 |
| Sandbagging | 「策略性低水平发挥」 | 模型在评估中低水平发挥；在 OpenAI Research Categories 中 |
| Instrumental reasoning | 「手段-目的推理」 | 关于如何达成目标的推理；DeepMind 监测的对象 |

## Further Reading · 延伸阅读

- [OpenAI — Updating our Preparedness Framework](https://openai.com/index/updating-our-preparedness-framework/) — v2 公告。
- [OpenAI — Preparedness Framework v2 PDF](https://cdn.openai.com/pdf/18a02b5d-6b67-4cec-ab64-68cdfbddebcd/preparedness-framework-v2.pdf) — 完整文档。
- [DeepMind — Strengthening our Frontier Safety Framework](https://deepmind.google/blog/strengthening-our-frontier-safety-framework/) — FSF v3 公告。
- [DeepMind — Updating the Frontier Safety Framework (April 2026)](https://deepmind.google/blog/updating-the-frontier-safety-framework/) — Tracked Capability Levels 的新增。
- [Gemini 3 Pro FSF Report](https://storage.googleapis.com/deepmind-media/gemini/gemini_3_pro_fsf_report.pdf) — 一份 FSF 格式 Risk Report 的示例。
