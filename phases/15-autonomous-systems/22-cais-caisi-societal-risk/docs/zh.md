# CAIS, CAISI, and Societal-Scale Risk · CAIS、CAISI 与社会尺度风险

> Center for AI Safety（CAIS，旧金山，2022 年由 Hendrycks 与 Zhang 创立）发布了四风险框架——恶意使用、AI 竞赛、组织风险、失控 AI——以及 2023 年 5 月由数百位教授和公司领袖联署的灭绝风险声明。CAIS 的 2026 年产出：用于前沿模型评估的 AI Dashboard、Remote Labor Index（与 Scale AI 合作）、Superintelligence Strategy Paper、AI Frontiers newsletter。另一个不同实体：NIST Center for AI Standards and Innovation（CAISI）——面向美国政府的自愿协议与非保密能力评估，聚焦网络、生物和化学武器风险。CAIS 把组织风险列为四大顶层风险之一：安全文化、严格审计、多层防御和信息安全是基础，却常被拿去与部署速度做交换。加州 SB-53 若签署，将成为美国第一个州级灾难性风险监管。

> The Center for AI Safety (CAIS, San Francisco, founded 2022 by Hendrycks and Zhang) publishes the four-risk framework — malicious use, AI races, organizational risks, rogue AIs — and the May 2023 statement on extinction risk signed by hundreds of professors and company leaders. 2026 releases from CAIS: AI Dashboard for frontier-model evaluation, Remote Labor Index (with Scale AI), Superintelligence Strategy Paper, AI Frontiers newsletter. A distinct entity: NIST Center for AI Standards and Innovation (CAISI) — US-government-facing voluntary agreements and unclassified capability evaluations focused on cyber, bio, and chemical-weapons risks. CAIS flags organizational risk as one of four top-level risks: safety culture, rigorous audits, multi-layered defenses, and information security are foundational but routinely traded off against deployment speed. California SB-53, if signed, would be the first US state-level catastrophic-risk regulation.

**类型：** Learn
**语言：** Python（标准库，四风险清单与缓解措施匹配器）
**前置：** Phase 15 · 19（RSP）、Phase 15 · 20（PF + FSF）
**时间：** ~45 分钟

## The Problem · 问题

第 19、20 课讲了实验室内部的扩展政策。第 21 课讲了独立能力评估。本课讲第三种视角：塑造公共讨论和灾难性 AI 风险监管基线的公民社会与政府组织。

两个不同的实体需要分清。CAIS 是一个非营利研究组织，发布思考 AI 风险的框架并协调公开声明。CAISI 是 NIST 内部的一个美国政府中心，与实验室运行自愿协议和非保密能力评估。名字押韵；使命并不重叠。从业者应该两个都知道。

实操内容：CAIS 的四风险框架是文献中被引用最多的社会尺度风险分类法。安全文化与组织风险是四者之一，也是从业者最能直接掌控的一个。SB-53（加州）若签署，将是美国第一个州级灾难性风险监管；该法案的框架之所以重要，是因为在美国科技政策史上，州级监管历来先于联邦行动。

> Lessons 19 and 20 covered lab-internal scaling policies. Lesson 21 covered independent capability evaluation. This lesson covers the third perspective: civil society and government organizations who shape public discussion and regulatory baseline for catastrophic AI risk.
> Two distinct entities matter. CAIS is a non-profit research org that publishes frameworks for thinking about AI risk and coordinates public statements. CAISI is a US-government center within NIST that runs voluntary agreements with labs and unclassified capability evaluations. The names rhyme; the missions do not overlap. A practitioner should know both.
> CAIS's four-risk framework is the most widely cited societal-scale-risk taxonomy in the literature. Safety culture and organizational risk are one of those four, and this is the one most directly under a practitioner's control. SB-53 (California) would be the first US state-level catastrophic-risk regulation if signed; the bill's framing matters because state-level regulation has historically led federal action in US tech policy.

## The Concept · 概念

### CAIS — Center for AI Safety · CAIS — Center for AI Safety（AI 安全中心）

- 成立：2022 年，旧金山，由 Dan Hendrycks 及同事创立（「Zhang」这个名字指一位早期合作者，不是现任共同创始人；现任领导层见 CAIS 网站）。
- 身份：501(c)(3) 非营利组织。
- 2023 年代表性产出：灭绝风险声明，由数百位研究者和 CEO 联署。原文写道："Mitigating the risk of extinction from AI should be a global priority alongside other societal-scale risks such as pandemics and nuclear war."（缓解 AI 带来的灭绝风险，应当与流行病、核战争等其他社会尺度风险一起，成为全球优先事项。）
- 2026 年产出：用于前沿模型评估的 AI Dashboard、Remote Labor Index（与 Scale AI 联合）、Superintelligence Strategy Paper、AI Frontiers newsletter。

> Founded: 2022 in San Francisco, by Dan Hendrycks and colleagues. Status: 501(c)(3) non-profit.
> Notable 2023 output: statement on extinction risk, co-signed by hundreds of researchers and CEOs. Stated: "Mitigating the risk of extinction from AI should be a global priority alongside other societal-scale risks such as pandemics and nuclear war."
> 2026 outputs: AI Dashboard for frontier-model evaluation, Remote Labor Index (joint with Scale AI), Superintelligence Strategy Paper, AI Frontiers newsletter.

### The four-risk framework · 四风险框架

CAIS 的框架把灾难性 AI 风险归为四个顶层类别：

1. **恶意使用（Malicious use）**：坏行为者用 AI 造成伤害（生物武器合成、虚假信息、网络攻击）。
2. **AI 竞赛（AI races）**：实验室、公司或国家之间的竞争压力把部署推过了安全点。
3. **组织风险（Organizational risks）**：实验室内部动态（安全文化失败、审计不足、安全投入不足）产出一次糟糕的部署。
4. **失控 AI（Rogue AIs）**：一个足够强大的 AI 追求与人类福祉冲突的目标。

这不是唯一的分类法，但是被引用最多的。类别之间不互斥——一个由在竞赛中用审计换速度的组织产出的失控 AI，四条全占。

> Malicious use: a bad actor uses AI to cause harm (bioweapons synthesis, disinformation, cyberattacks).
> AI races: competitive pressure between labs, companies, or nations pushes deployment past the point where it is safe.
> Organizational risks: internal lab dynamics (safety-culture failures, insufficient audit, under-resourced security) produce a bad deployment.
> Rogue AIs: a sufficiently capable AI pursues goals that conflict with human welfare.
> This is not the only taxonomy; it is the most cited. The categories are not mutually exclusive — a rogue AI produced by an organization that traded audit for speed in a race is all four.

### Where organizational risk lives · 组织风险的落点

四个类别中，组织风险对从业者最有可操作性。一个实验室的安全文化、审计严格度、防御分层和信息安全，决定了他们发布模型时，第 10–18 课的那些控制措施是真的在起作用，还是只是没人验证过的清单项。

具体的组织风险杠杆：

- **安全文化**：团队成员是否觉得能在不计职业代价的情况下上报一个顾虑？CAIS 的调查发现这是其他杠杆的强预测因子。
- **严格审计**：外部加内部。只有内部的审计会产出乐观的报告。
- **多层防御**：没有哪一层单独够用（Phase 15 的贯穿主题）。
- **信息安全**：模型权重泄露、评估数据泄露、监测绕过技术泄露。第 19 课的 RAND SL-4 是一个具体标准。

> Of the four categories, organizational risk is the most actionable for practitioners. A lab's safety culture, audit rigor, defense layering, and information security decide whether their model ships with the controls of Lessons 10–18 actually in place, or whether those controls are checklist items nobody verified.
> Safety culture: do team members feel able to escalate a concern without career cost? CAIS surveys find this is a strong predictor of the other levers. Rigorous audits: external and internal. Internal-only audits produce optimistic reports. Multi-layered defenses: no single layer is sufficient (the running theme of Phase 15). Information security: model weights leaking, eval data leaking, monitor-bypass techniques leaking. RAND SL-4 in Lesson 19 is a specific standard.

### CAISI — Center for AI Standards and Innovation · CAISI — Center for AI Standards and Innovation（AI 标准与创新中心）

- 在 NIST 内部运作。
- 与前沿实验室运行自愿协议。
- 发布聚焦网络、生物、化学武器风险的非保密能力评估。
- 与 CAIS 是两个机构；缩写撞车了；看 URL（nist.gov）确认你在读哪一个。

CAISI 的角色是 METR 私下实验室合作（第 21 课）的公开、政府侧对应物。CAISI 的报告非保密；METR 的报告常被保密协议锁住。两个都读的从业者得到更完整的图景。

> Operates within NIST. Runs voluntary agreements with frontier labs. Publishes unclassified capability evaluations focused on cyber, bio, and chemical-weapons risks. Distinct from CAIS; the acronyms collide; check the URL (nist.gov) to confirm which one you are reading.
> CAISI's role is the public, government-facing counterpart to METR's private lab engagements (Lesson 21). CAISI reports are unclassified; METR reports are often NDA-gated. A practitioner reading both gets a fuller picture.

### California SB-53 · 加州 SB-53

加州参议院法案（2025–2026 会期）处理前沿模型的灾难性风险。按草案的主要条款：

- 触发州级义务的特定能力阈值。
- 对 AI 实验室员工的吹哨人保护。
- 灾难性失败的事件报告要求。

若签署，它将是美国第一个州级灾难性风险监管。无论签署与否，法案的框架都会塑造其他州立法机构处理这一问题的方式。加州的从业者应追踪法案状态；其他地方的从业者应读它，以理解美国州级监管大概会长什么样。

> The California Senate bill (2025–2026 session) addresses catastrophic risk from frontier models. Key provisions as drafted: specific capability thresholds that trigger state-level obligations; whistleblower protections for AI lab employees; incident reporting requirements for catastrophic failures.
> If signed, it would be the first US state-level catastrophic-risk regulation. Regardless of signing status, the bill's framing shapes how other state legislatures approach the problem.

### Societal-scale risk is not a single-layer problem · 社会尺度风险不是单层问题

Phase 15 的贯穿主题——纵深防御——在社会层同样成立。没有任何单一组织、单一监管或单一框架能封住灾难性风险。只有当以下环节同时运转，生态系统才成立：

- 实验室发布扩展政策（第 19、20 课）。
- 外部评估者产出测量（第 21 课）。
- 公民社会追踪并公开（CAIS）。
- 政府运行自愿项目和基线监管（CAISI、SB-53）。
- 从业者构建多层控制（第 10–18 课）。

这是本阶段的最终综合：之前每一课都是叠层中的一层，叠层的完整性比任何单层的强度更重要。

```figure
a5-four-risks
```

> The running theme of Phase 15 — defense in depth — applies at the societal layer too. No single organization, regulation, or framework closes catastrophic risk. The ecosystem functions only when: labs ship scaling policies (Lessons 19, 20); external evaluators produce measurements (Lesson 21); civil society tracks and publicizes (CAIS); government runs voluntary programs and baseline regulation (CAISI, SB-53); practitioners build multi-layered controls (Lessons 10–18).
> This is the final synthesis for the phase: every previous lesson is one layer in a stack whose completeness matters more than any single layer's strength.

## Use It · 实战用法

`code/main.py` 实现了一个小型风险清单工具。给定一个拟议部署，它按四风险类别给部署打标签并返回一份缓解措施清单。它是框架的阅读辅助，不能替代人类判断。

> `code/main.py` implements a small risk-inventory tool. Given a proposed deployment, it tags the deployment against the four-risk categories and returns a mitigation checklist. It's a reading aid for the framework, not a substitute for human judgment.

## Ship It · 交付

`outputs/skill-societal-risk-review.md` 评审一次部署的社会尺度风险姿态：触及四个类别中的哪些、已有哪些缓解措施、组织风险暴露是什么。

> `outputs/skill-societal-risk-review.md` reviews a deployment for societal-scale-risk posture: which of the four categories it touches, what mitigations are in place, what the organizational-risk exposure is.

## Exercises · 练习

1. 运行 `code/main.py`。喂入三个不同规模的合成部署。确认四风险标签符合你的预期；找出一个工具打了过多或过少标签的案例。

2. 完整阅读 CAIS 四风险论文。选一个风险类别，写两段文字，谈谈你认为该类别 2026 年最重要的发展是什么。

3. 阅读 California SB-53 的当前草案。找出一条你认为加强灾难性风险姿态的条款和一条你认为削弱它的条款。两者都给出理由。

4. 选一个你知道的生产 AI 部署（你自己的或公开的）。按组织风险子杠杆给它打分：安全文化、审计严格度、多层防御、信息安全。哪个最弱？把它补齐到标准要花多少成本？

5. 草拟一个 2028 版的四风险框架，反映额外一年的能力和额外一年的部署经验。你会新增、移除或重组什么？

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|---|---|---|
| CAIS | 「Center for AI Safety」 | 非营利组织；四风险框架；2023 灭绝风险声明 |
| CAISI | 「美国政府的 AI 安全机构」 | NIST 中心；自愿协议；非保密评估 |
| Four-risk framework | 「CAIS 的分类法」 | 恶意使用、AI 竞赛、组织风险、失控 AI |
| Malicious use | 「坏行为者用 AI」 | 生物武器、虚假信息、网络攻击 |
| AI races | 「竞争压力」 | 实验室/公司/国家把部署推过安全线 |
| Organizational risk | 「实验室内部失败」 | 安全文化、审计、防御、信息安全 |
| Rogue AI | 「未对齐的 agent」 | 追求与人类福祉冲突目标的强大 AI |
| California SB-53 | 「州级监管」 | 2025–2026 法案；若签署将是美国第一个州级灾难性风险监管 |

## Further Reading · 延伸阅读

- [Center for AI Safety](https://safe.ai/) — 四风险框架的机构主页。
- [CAIS — AI Risks that Could Lead to Catastrophe](https://safe.ai/ai-risk) — 四风险论文。
- [CAIS — May 2023 statement on extinction risk](https://safe.ai/statement-on-ai-risk) — 简短的联合声明。
- [NIST CAISI](https://www.nist.gov/caisi) — 面向政府的 AI 标准与创新中心。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 把实验室层面的承诺与社会尺度框架联系起来。
