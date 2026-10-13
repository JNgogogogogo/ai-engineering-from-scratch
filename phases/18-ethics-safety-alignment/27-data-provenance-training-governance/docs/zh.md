# Data Provenance and Training-Data Governance · 数据溯源与训练数据治理

> EU AI Act 要求到 2025 年 8 月为 GPAI 提供机器可读的选择退出（opt-out）标准（经由 EU Copyright Directive 的 TDM 例外）。California AB 2013（2024 年签署）—— 生成式 AI 训练数据透明度，要求开发者发布含 12 个规定字段的数据集摘要。2025 年各 DPA 在「合法利益」（legitimate interest）上的趋同：爱尔兰 DPC（2025 年 5 月 21 日）在 EDPB 意见之后，接受 Meta 在带保障措施的前提下，基于第一方公开的 EU/EEA 成人内容训练 LLM；科隆高等地区法院（2025 年 5 月 23 日）驳回禁令申请；汉堡 DPA 放弃紧急程序；英国 ICO（2025 年 9 月 23 日）对 LinkedIn 的 AI 训练保障措施（透明度、简化 opt-out、延长异议窗口）给出积极的监管回应，并持续监测 —— 这不是正式许可。巴西 ANPD（2024 年 7 月 2 日）以信息透明度不足为由暂停 Meta 的数据处理；在 Meta 提交合规计划后，该预防性措施于 2024 年 8 月 30 日解除。关键的不可逆问题：cookie 同意框架是为实时、可逆的追踪设计的；数据一旦进入模型权重，外科手术式的擦除就不可能 —— 对已训练的神经网络不存在实用的 GDPR 被遗忘权。合规窗口在采集时刻。Data Provenance Initiative（dataprovenance.org，Longpre, Mahari, Lee et al.，「Consent in Crisis」，2024 年 7 月）：大规模审计显示，随着出版商加设 robots.txt 限制，AI 数据公共池正在快速萎缩。

> EU AI Act requires machine-readable opt-out standards for GPAI by August 2025 (via EU Copyright Directive TDM exception). California AB 2013 (signed 2024) — Generative AI training-data transparency requires developers to publish a summary of datasets with 12 mandated fields. 2025 DPA alignment on legitimate interest: Irish DPC (21 May 2025) accepts Meta's LLM training on first-party public EU/EEA adult content with safeguards after EDPB opinion; Cologne Higher Regional Court (23 May 2025) dismisses injunction; Hamburg DPA drops urgency; UK ICO (23 September 2025) issues a positive regulatory response to LinkedIn's AI-training safeguards (transparency, simplified opt-out, extended objection windows) and continues monitoring — not a formal clearance. Brazilian ANPD (2 July 2024) suspended Meta's processing over insufficient information transparency; the preventive measure was lifted on 30 August 2024 after Meta submitted a compliance plan. Key irreversibility problem: cookie-consent frameworks are designed for real-time, reversible tracking; once data is in model weights, surgical erasure is impossible — no practical GDPR right-to-erasure for trained neural networks. Compliance window is at collection time. Data Provenance Initiative (dataprovenance.org, Longpre, Mahari, Lee et al., "Consent in Crisis", July 2024): large-scale audit shows rapid decline of the AI data commons as publishers add robots.txt restrictions.

**Type:** Learn
**Languages:** Python (stdlib, 12-field California AB 2013 scaffolding generator)
**Prerequisites:** Phase 18 · 24 (regulatory), Phase 18 · 26 (cards)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 描述 California AB 2013 为生成式 AI 训练数据透明度规定的 12 个必填字段。
- 说出 2025 年 DPA 对基于合法利益（legitimate interest）进行 LLM 训练的立场（爱尔兰 DPC、英国 ICO、汉堡、科隆）。
- 描述不可逆问题：为什么 GDPR 被遗忘权对已训练的神经网络没有实用的等价物。
- 说出 Data Provenance Initiative「Consent in Crisis」的发现。

> Describe California AB 2013's 12 mandated fields for Generative AI training-data transparency.
> State the 2025 DPA position on legitimate-interest LLM training (Irish DPC, UK ICO, Hamburg, Cologne).
> Describe the irreversibility problem: why GDPR right-to-erasure has no practical equivalent for trained neural networks.
> State the Data Provenance Initiative's "Consent in Crisis" finding.

## The Problem · 问题

训练数据治理是每一张模型卡（第 26 课）和每一项监管义务（第 24 课）的上游。2024-2025 年，监管格局在三个原则上完成了整合：opt-out 基础设施、按数据集披露、以及对公开可用数据的合法利益（legitimate-interest）豁免。在采集时刻不合规的提供方，无法在下游进行补救。

> Training-data governance is the upstream of every model card (Lesson 26) and regulatory obligation (Lesson 24). In 2024-2025, the regulatory landscape consolidated on three principles: opt-out infrastructure, per-dataset disclosure, and legitimate-interest accommodations for publicly available data. Providers that do not comply at collection time cannot remediate downstream.

## The Concept · 概念

### California AB 2013 · 加州 AB 2013

2024 年签署。对 2022 年 1 月 1 日或之后发布的系统，文档必须在 2026 年 1 月 1 日或之前公布。Section 3111(a) 要求开发者发布训练所用数据集的高层摘要，含 12 项法定内容：
1. 数据集的来源或所有者。
2. 说明数据集如何服务于 AI 系统的预期目的。
3. 数据集中数据点的数量（可给大致范围；动态数据集可给估计值）。
4. 说明数据点的类型（有标注数据集的标注类型；无标注数据集的一般特征）。
5. 数据集是否包含受版权、商标或专利保护的数据，或是否完全属于公有领域。
6. 数据集是否为购买或授权获得。
7. 数据集是否包含个人信息（per Cal. Civ. Code §1798.140(v)）。
8. 数据集是否包含聚合消费者信息（per Cal. Civ. Code §1798.140(b)）。
9. 开发者所做的清洗、处理或其他修改，及其预期目的。
10. 数据采集的时间段，若仍在采集须给出提示。
11. 数据集在开发期间首次使用的日期。
12. 系统是否使用或持续使用合成数据生成。

第 12 项（合成数据）相对 Gebru et al. 2018 数据表是新增的。第 7 项（个人信息）会触发 Privacy Rights Act（CPRA）义务。该法规豁免安全/完整性、飞行器运行、以及仅限联邦的国家安全系统（Section 3111(b)）。

> Item 12 (synthetic data) is new relative to Gebru et al. 2018 datasheets. Item 7 (personal information) triggers Privacy Rights Act (CPRA) obligations. The statute exempts security/integrity, aircraft-operation, and federal-only national-security systems (Section 3111(b)).

### EU AI Act (Lesson 24) and TDM opt-out · EU AI Act（第 24 课）与 TDM 选择退出

EU Copyright Directive 的文本与数据挖掘（TDM）例外允许在公开可用内容上训练，除非权利人选择退出（opt-out）。EU AI Act GPAI 行为准则的版权章节要求 GPAI 提供方尊重机器可读的 opt-out 信号（robots.txt、C2PA「No AI Training」声明等）。

> EU Copyright Directive text-and-data-mining exception allows training on publicly available content unless the rightholder opts out. EU AI Act GPAI Code of Practice Copyright chapter requires GPAI providers to respect machine-readable opt-out signals (robots.txt, C2PA "No AI Training" claim, etc.).

### 2025 DPA convergence on legitimate interest · 2025 年 DPA 在合法利益上的趋同

爱尔兰 DPC（2025 年 5 月 21 日）：在 EDPB 意见之后，接受 Meta 在带保障措施的前提下、基于第一方公开的 EU/EEA 成人用户内容训练模型的计划。科隆高等地区法院（2025 年 5 月 23 日）驳回针对 Meta 的禁令申请：opt-out 即足够。汉堡 DPA 为全欧盟的一致性而放弃紧急程序。英国 ICO（2025 年 9 月 23 日）对 LinkedIn 在类似保障措施与持续监测下恢复 AI 训练，给出了积极的监管回应 —— 不是正式许可。

趋同的原则：合法利益可以支撑在带 opt-out 的第一方公开内容上训练。同意（consent）不是必需的。

> Irish DPC (21 May 2025): Meta's plan to train on first-party public EU/EEA adult-user content accepted with safeguards after EDPB opinion. Cologne Higher Regional Court (23 May 2025) dismisses injunction against Meta: opt-out is sufficient. Hamburg DPA drops urgency procedure for EU-wide consistency. UK ICO (23 September 2025) issued a positive regulatory response — not a formal clearance — to LinkedIn's resumption of AI training with similar safeguards and ongoing monitoring.
> Convergent principle: legitimate interest can justify training on publicly available first-party content with opt-out. Consent is not required.

### Brazilian ANPD (June 2024) · 巴西 ANPD（2024 年 6 月）

以信息透明度不足为由，暂停 Meta 对巴西用户数据的 AI 训练处理。结果与欧盟 DPA 不同 —— ANPD 把透明度置于合法利益可采性之上。

> Suspended Meta's processing of Brazilian user data for AI training over insufficient information transparency. Different result than the EU DPAs — ANPD prioritized transparency over legitimate-interest admissibility.

### The irreversibility problem · 不可逆问题

Cookie 同意是为实时、可逆的追踪设计的。训练数据不同：数据一旦进入模型权重，外科手术式的擦除就不可能。从头重训是唯一彻底的补救，而它的代价高得令人却步。

部分补救手段：
- **Unlearning（机器遗忘）。** 近似移除；用 MIA 度量（第 22 课）。
- **基于影响函数的定位。** 找出受该数据影响最大的权重；做选择性更新。
- **微调抑制。** 训练模型拒绝输出由该数据导出的内容。

没有一种能彻底解决问题。合规窗口在采集时刻。

> Cookie-consent was designed for real-time, reversible tracking. Training data is different: once data enters model weights, surgical erasure is not possible. Retraining from scratch is the only complete remediation, and it is prohibitively expensive.
> Partial remediations: Unlearning. Approximate removal; measured by MIA (Lesson 22). Influence function-based localization. Identify weights most influenced by the data; selectively update. Fine-tune-suppression. Train the model to refuse outputs derived from the data.
> None fully solve the problem. The compliance window is at collection time.

### Data Provenance Initiative · 数据溯源计划（DPI）

dataprovenance.org。Longpre, Mahari, Lee et al.「Consent in Crisis」（2024 年 7 月）：对 AI 训练数据公共池的大规模审计。发现：出版商正在加速添加 robots.txt 限制。可开放训练的公共池正在迅速收缩。2023 -> 2024 年间，头部训练源中约 25% 添加了某种限制。推论：未来的训练数据可得性取决于新的获取范式（授权许可、合成生成、激励参与）。

> dataprovenance.org. Longpre, Mahari, Lee et al. "Consent in Crisis" (July 2024): large-scale audit of AI training data commons. Finding: publishers are adding robots.txt restrictions at an accelerating rate. The openly-trainable-upon commons is contracting rapidly. 2023 -> 2024 saw about 25% of the top training sources add some restriction. Implication: future training-data availability depends on new acquisition paradigms (licensing, synthetic generation, incentivized participation).

### Where this fits in Phase 18 · 在 Phase 18 中的位置

第 26 课是模型级文档。第 27 课是数据集级治理。二者共同定义透明度层。第 28 课描绘研究这些问题的研究生态。

> Lesson 26 is model-level documentation. Lesson 27 is dataset-level governance. Together they define the transparency layer. Lesson 28 maps the research ecosystem that works on these questions.

```figure
an-provenance-oneway
```

## Use It · 实战用法

`code/main.py` 为一个玩具数据集生成符合 California AB 2013 的 12 字段数据集摘要脚手架。你可以填入各字段，观察哪些字段会触发隐私或版权的后续义务。

> `code/main.py` generates a California AB 2013-compliant 12-field dataset summary scaffold for a toy dataset. You can fill the fields and observe which ones trigger privacy or copyright follow-on obligations.

## Ship It · 交付

本课产出 `outputs/skill-provenance-check.md`。给定一个用于训练的数据集，它会检查 AB 2013 的 12 字段覆盖度、opt-out 基础设施合规性、DPA 立场对齐，以及不可逆风险评估。

> This lesson produces `outputs/skill-provenance-check.md`. Given a dataset used in training, it checks for AB 2013 12-field coverage, opt-out infrastructure compliance, DPA alignment, and irreversibility-risk assessment.

## Exercises · 练习

1. 运行 `code/main.py`。为一个玩具数据集生成 12 字段摘要，并找出哪些字段描述不足。

2. EU Copyright Directive 的 TDM opt-out 是机器可读的。为该 opt-out 信号提出一种标准格式，并与 robots.txt 及 C2PA「No AI Training」做比较。

3. 阅读 Data Provenance Initiative 的「Consent in Crisis」（2024 年 7 月）。描述限制增速最快的三个内容类别，并论证一个经济后果。

4. 2025 年 DPA 的趋同立场接受以合法利益支撑公开内容训练。构造一个合法利益不够用的场景，并指出提供方此时需要什么法律基础。

5. 草拟一份训练数据溯源清单（manifest），使其既能与 AB 2013 字段组合，又能为每个数据集附带 C2PA 签名的溯源链。指出一个技术障碍和一个法律障碍。

> Run `code/main.py`. Produce a 12-field summary for a toy dataset and identify which fields are under-specified. ... Sketch a training-data-provenance manifest that composes with the AB 2013 fields and a C2PA-signed provenance chain for each dataset. Identify one technical and one legal barrier.

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|------------------------|
| AB 2013 | 「加州那部法律」 | 生成式 AI 训练数据透明度；12 个规定字段 |
| TDM exception | 「文本与数据挖掘」 | EU Copyright Directive 带 opt-out 的训练数据例外 |
| Legitimate interest | 「欧盟的法律基础」 | GDPR 第 6 条基础，可为在公开内容上训练提供依据 |
| Opt-out signal | 「机器可读的禁止训练」 | robots.txt、C2PA "No AI Training"、TDM.Reservation |
| Irreversibility | 「无法反训练」 | 进入模型权重的数据无法被外科手术式移除 |
| Unlearning | 「近似移除」 | 训练后干预，降低模型对特定数据的依赖 |
| Consent in Crisis | 「DPI 审计」 | 2024 年 7 月关于 robots.txt 限制加速增加的发现 |

## Further Reading · 延伸阅读

- [California AB 2013](https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240AB2013) — 生成式 AI 训练数据透明度法律
- [EU AI Act + GPAI Code of Practice (Lesson 24)](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai) — 版权章节
- [Longpre, Mahari, Lee et al. — Consent in Crisis (dataprovenance.org, July 2024)](https://www.dataprovenance.org/consent-in-crisis-paper) — DPI 审计
- [IAPP — EU Digital Omnibus GDPR amendments (2025)](https://iapp.org/news/a/eu-digital-omnibus-amendments-to-gdpr-to-facilitate-ai-training-miss-the-mark) — 监管背景
