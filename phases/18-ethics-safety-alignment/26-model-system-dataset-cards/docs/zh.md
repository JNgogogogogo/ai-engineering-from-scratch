# Model, System, and Dataset Cards · 模型卡、系统卡与数据集卡

> 三种文档格式撑起了 AI 透明度。模型卡（model card，Mitchell et al. 2019）—— 模型的「营养成分表」：训练数据、按因素拆分的量化分析、伦理考量、局限性说明；而 Hugging Face 上只有 0.3% 的模型卡写明了伦理考量（Oreamuno et al. 2023）。数据表（datasheet，Gebru et al. 2018，发表于 CACM）—— 动机、构成、采集过程、标注、分发、维护；类比电子元件的数据表。数据卡（data card，Pushkarna et al.，Google 2022）—— 模块化的分层细节（telescopic 望远层、periscopic 潜望层、microscopic 显微层），作为服务不同读者的边界对象（boundary object）。2024-2025 年的进展：用 LLM 自动生成（CardGen，Liu et al. 2024）；模型卡的详细程度与 HF 上最高 29% 的下载量提升相关（Liang et al. 2024）；可验证证明（verifiable attestation，Laminator，Duddu et al. 2024）；面向碳/水的可持续性报告增补（Jouneaux et al.，2025 年 7 月）；EU/ISO 监管卡正在兴起。系统卡（system card，Sidhpurwala 2024；Meta 的系统级透明度工作；「Blueprints of Trust」arXiv:2509.20394）—— 覆盖安全能力、提示注入防护、数据外渗检测、与人类价值观对齐的端到端 AI 系统文档。

> Three documentation formats structure AI transparency. Model Cards (Mitchell et al. 2019) — nutrition labels for models: training data, quantitative disaggregated analyses, ethical considerations, caveats; only 0.3% of Hugging Face model cards document ethical considerations (Oreamuno et al. 2023). Datasheets for Datasets (Gebru et al. 2018, CACM) — motivation, composition, collection process, labeling, distribution, maintenance; electronics-datasheet analogy. Data Cards (Pushkarna et al., Google 2022) — modular layered detail (telescopic, periscopic, microscopic) as boundary objects for diverse readers. 2024-2025 developments: automated generation via LLMs (CardGen, Liu et al. 2024); model-card detail correlates with up to 29% download increase on HF (Liang et al. 2024); verifiable attestations (Laminator, Duddu et al. 2024); sustainability reporting additions for carbon/water (Jouneaux et al. July 2025); EU/ISO regulatory cards emerging. System Cards (Sidhpurwala 2024; Meta system-level transparency; "Blueprints of Trust" arXiv:2509.20394) — end-to-end AI system documentation covering security capabilities, prompt-injection protection, data-exfiltration detection, alignment with human values.

**Type:** Build
**Languages:** Python (stdlib, model-card + datasheet + system-card generator)
**Prerequisites:** Phase 18 · 18 (safety frameworks), Phase 18 · 24 (regulatory)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 描述 Mitchell et al. 2019 的原始模型卡与 Gebru et al. 2018 的数据表（datasheet）。
- 描述 Data Cards 的 telescopic / periscopic / microscopic 三层设计。
- 描述 System Cards 及其端到端覆盖范围。
- 说出三项 2024-2025 年的进展（自动生成、可验证证明、可持续性报告）。

> Describe the original Mitchell et al. 2019 model card and the Gebru et al. 2018 datasheet.
> Describe Data Cards' telescopic/periscopic/microscopic layering.
> Describe System Cards and their end-to-end coverage.
> State three 2024-2025 developments (automated generation, verifiable attestations, sustainability reporting).

## The Problem · 问题

监管框架（第 24 课）和实验室安全政策（第 18 课）都要求文档化。文档格式从模型专属（模型卡）演进到数据集专属（数据表），再到系统专属（系统卡），每种格式应对的是不同范围的透明度。2024-2025 年的自动化与可验证证明工作，则瞄准了长期悬而未决的落地采用难题。

> Regulatory frameworks (Lesson 24) and lab safety policies (Lesson 18) both require documentation. Documentation formats evolved from model-specific (model cards) to dataset-specific (datasheets) to system-specific (system cards). Each addresses a different scope of transparency. The 2024-2025 automation and verifiable-attestation work addresses the long-standing adoption problem.

## The Concept · 概念

### Model Cards (Mitchell et al. 2019) · 模型卡

包含的章节：
- 模型细节（model details）。
- 预期用途（intended use）。
- 因素（factors）：评估中相关的人口或环境因素。
- 指标（metrics）。
- 评估数据（evaluation data）。
- 训练数据（training data）。
- 量化分析（quantitative analyses，按因素拆分）。
- 伦理考量（ethical considerations）。
- 局限与建议（caveats and recommendations）。

采用难题：Oreamuno et al. 2023 对 Hugging Face 模型卡的审计发现，只有 0.3% 的模型卡写明了伦理考量。

> Sections: Model details. Intended use. Factors (relevant demographic or environmental factors for evaluation). Metrics. Evaluation data. Training data. Quantitative analyses (disaggregated by factors). Ethical considerations. Caveats and recommendations. ... Adoption problem: Oreamuno et al. 2023 audit of Hugging Face model cards found only 0.3% document ethical considerations.

### Datasheets for Datasets (Gebru et al. 2018) · 数据集的数据表

类比电子元件的数据表（electronics datasheet）。包含的章节：
- 动机（motivation）：数据集为什么被创建。
- 构成（composition）：里面有什么。
- 采集过程（collection process）：它是如何被组装起来的。
- 标注（labeling，如适用）。
- 用途（uses）：预期用途、禁止用途、风险。
- 分发（distribution）。
- 维护（maintenance）。

数据表论文发表于 CACM 2021。数据表是上游文档；模型卡是否可信，取决于数据表是否准确。

> Electronics-datasheet analogy. Sections: Motivation (why was the dataset created). Composition (what is in it). Collection process (how was it assembled). Labeling (if applicable). Uses (intended, prohibited, risks). Distribution. Maintenance. ... Published in CACM 2021. The datasheet is the upstream documentation; the model card depends on the datasheet being accurate.

### Data Cards (Pushkarna et al., Google 2022) · 数据卡

模块化的分层细节。三个缩放级别：
- **Telescopic（望远层）。** 面向非专家的高层摘要。
- **Periscopic（潜望层）。** 面向 ML 从业者的中观概览。
- **Microscopic（显微层）。** 面向审计者的特征级详细文档。

边界对象（boundary object）框架：不同读者从同一份文档中各取所需。

> Modular layered detail. Three zoom levels: Telescopic. High-level summary for non-experts. Periscopic. Middle-level overview for ML practitioners. Microscopic. Detailed feature-level documentation for auditors. ... Boundary-object framing: different readers extract different information from the same document.

### System Cards · 系统卡

范围：端到端 AI 系统，包括模型 + 安全栈 + 部署上下文。典型章节包括：
- 安全能力（security capabilities）。
- 提示注入（prompt injection）防护。
- 数据外渗（data exfiltration）检测。
- 与既有人类价值观的对齐。
- 事件响应（incident response）。

背景是 Sidhpurwala 2024 与 Meta 的系统级透明度工作。「Blueprints of Trust」（arXiv:2509.20394）把 System Card 形式化为 Model Card 在部署层的互补文档。

> Scope: end-to-end AI system including model + safety stack + deployment context. ... Sidhpurwala 2024 and Meta system-level transparency work. "Blueprints of Trust" (arXiv:2509.20394) formalizes the System Card as the deployment-layer complement to Model Cards.

### 2024-2025 developments · 2024-2025 年的进展

- **CardGen（Liu et al. 2024）。** 用 LLM 自动生成模型卡；在标准化的 Mitchell 2019 字段上，其客观性高于许多人工撰写的卡片。
- **下载量相关性（Liang et al. 2024）。** 详细的模型卡与 HF 上最高 29% 的下载量提升相关 —— 采用压力如今是市场驱动的，而不只是合规驱动的。
- **Laminator（Duddu et al. 2024）。** 通过硬件 TEE / 密码学签名实现可验证证明 —— 让模型卡能携带「声明的证明」，而不只是一纸声明。
- **可持续性（Jouneaux et al.，2025 年 7 月）。** 新增碳、水与计算能耗足迹的披露；ISO 标准正在成形。
- **监管卡。** EU AI Act（第 24 课）GPAI 行为准则的透明度章节要求把模型卡作为合规工件（compliance artifact）。

> CardGen (Liu et al. 2024). Automated model-card generation via LLMs; reports higher objectivity than many human-authored cards on the standardized Mitchell 2019 fields. ... Download correlation (Liang et al. 2024). Detailed model cards correlate with up to 29% higher download rates on HF — adoption pressure is now market-driven, not only compliance-driven. ... Laminator (Duddu et al. 2024). Verifiable attestations via hardware TEE / cryptographic signatures — allows the model card to carry a proof-of-claim, not just a claim. ... Regulatory cards. EU AI Act (Lesson 24) GPAI Code of Practice Transparency chapter requires model cards as a compliance artifact.

### Where this fits in Phase 18 · 在 Phase 18 中的位置

第 24-25 课是监管层与 CVE 层。第 26 课是文档层。第 27 课是训练数据治理，也就是数据表的上游。第 28 课是研究生态，产出卡片中引用的那些评估。

> Lessons 24-25 are regulatory and CVE layers. Lesson 26 is the documentation layer. Lesson 27 is training-data governance, which is the datasheet's upstream. Lesson 28 is the research ecosystem that produces evaluations referenced in cards.

```figure
an-card-scopes
```

## Use It · 实战用法

`code/main.py` 为一个玩具部署生成一份最小化的模型卡、数据表和系统卡，每份都遵循标准章节结构。你可以检查这些格式，并比较三种范围。

> `code/main.py` generates a minimal model card, datasheet, and system card for a toy deployment. Each follows the canonical section structure. You can inspect the format and compare the three scopes.

## Ship It · 交付

本课产出 `outputs/skill-card-audit.md`。给定一份模型卡、数据表或系统卡，它会审计章节覆盖度、数值是否按因素拆分，以及是否带有可验证证明。

> This lesson produces `outputs/skill-card-audit.md`. Given a model card, datasheet, or system card, it audits section coverage, numerical disaggregation, and whether verifiable attestations are present.

## Exercises · 练习

1. 运行 `code/main.py`。检查生成的卡片。找出内容薄弱（只有占位符）的章节，并说明需要什么样的证据来加强它们。

2. 为模型卡补充一份跨两个人口群体的量化拆分分析（第 20 课）。

3. 阅读 Oreamuno et al. 2023 关于 0.3% 采用率的研究。针对模型卡规范提出一项结构性修改，以提高伦理考量章节的采用率。

4. Laminator（Duddu et al. 2024）用 TEE 实现可验证证明。设计一个携带评估结果密码学证明（attestation）的模型卡字段，并描述验证方的角色。

5. 为你过去的一个项目或一个假想的部署写一份 System Card（注意是系统卡，不是模型卡）。找出对第三方审计者价值最高的章节。

> Run `code/main.py`. Inspect the generated cards. Identify sections that are weak (placeholder-only) and specify what evidence would strengthen them. ... Write a System Card (System Card, not Model Card) for one of your past projects or a hypothetical deployment. Identify the highest-value section for third-party auditors.

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Model Card | 「Mitchell 卡」 | Mitchell et al. 2019 制定的 ML 模型标准文档 |
| Datasheet | 「Gebru 数据表」 | Gebru et al. 2018 制定的数据集标准文档 |
| Data Card | 「Pushkarna 卡」 | Google 2022 的模块化分层数据文档 |
| System Card | 「部署卡」 | 包含安全栈在内的端到端 AI 系统文档 |
| Boundary object | 「不同读者，同一份文档」 | Data Cards 的框架：同一份文档服务多种受众 |
| Verifiable attestation | 「Laminator 证明」 | 附在文档声明上的密码学或 TEE 证明 |
| Sustainability field | 「碳 / 水足迹」 | 2025 年兴起的环境核算新增字段 |

## Further Reading · 延伸阅读

- [Mitchell et al. — Model Cards for Model Reporting (arXiv:1810.03993, FAT* 2019)](https://arxiv.org/abs/1810.03993) — 模型卡的经典原始文献
- [Gebru et al. — Datasheets for Datasets (CACM 2021, arXiv:1803.09010)](https://arxiv.org/abs/1803.09010) — 数据表论文
- [Pushkarna et al. — Data Cards (Google 2022)](https://arxiv.org/abs/2204.01075) — 分层数据文档
- [Sidhpurwala et al. — Blueprints of Trust (arXiv:2509.20394)](https://arxiv.org/abs/2509.20394) — System Card 的形式化
