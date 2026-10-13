# Compliance — SOC 2, HIPAA, GDPR, PCI-DSS, EU AI Act, ISO 42001 · 合规——SOC 2、HIPAA、GDPR、PCI-DSS、EU AI Act 与 ISO 42001

> 多框架覆盖是 2026 年企业级签单的入场券。**EU AI Act**：2024 年 8 月 1 日生效，大部分高风险要求于 2026 年 8 月 2 日开始执行。高风险系统义务的罚款最高 1500 万欧元或全球年营业额的 3%（Art. 99(4)）；禁止性 AI 实践最高 3500 万欧元或 7%（Art. 99(3)）。只要服务欧盟用户就受管辖。**Colorado AI Act**：2026 年 6 月 30 日生效（被 SB25B-004 从 2026 年 2 月推迟）——高风险系统要做影响评估，AI 决策有申诉权。Virginia 对信贷 / 就业 / 住房 / 教育有类似规定。**SOC 2 Type II**：事实上的 B2B AI 门槛（金融科技要 Type II，不要 Type I）。**GDPR**：有据可查的最大 AI 专项罚款是针对 Clearview AI 的 €30.5M（荷兰 DPA，2024 年 9 月）；意大利 Garante 于 2024 年 12 月对 OpenAI 开出 €15M 罚单（2026 年 3 月在上诉中被推翻）。推理时实时 PII 脱敏（redaction）是可辩护的标准；后处理清理是不够的。**HIPAA**：医疗健康受约束——没有 BAA 就不能把 PHI 发给外部 AI 服务。**PCI-DSS**：AI 交互层的覆盖需要配置 + 合同约定，不是自动生效。**ISO 42001**：新兴的 AI 治理标准，正随 ISO 27001 一起成为越来越多的采购要求。参考配置：OpenAI 持有 SOC 2 Type 2、ISO/IEC 27001:2022、ISO/IEC 27701:2019、GDPR/CCPA/HIPAA (BAA)/FERPA，以及 ChatGPT 支付组件的 PCI-DSS。跨框架映射能减少审计疲劳：访问控制可以同时映射到 ISO 27001 A.5.15-5.18、GDPR Art. 32、HIPAA §164.312(a)。

> Multi-framework coverage is table stakes for 2026 enterprise deals. **EU AI Act**: in force since August 1, 2024. Most high-risk requirements enforce August 2, 2026. Fines up to €15M or 3% global annual turnover for high-risk-system obligations (Art. 99(4)); up to €35M or 7% for prohibited AI practices (Art. 99(3)). Applies globally if serving EU users. **Colorado AI Act**: effective June 30, 2026 (delayed from February 2026 by SB25B-004) — impact assessments for high-risk systems, right to appeal AI decisions. Virginia similar for credit/employment/housing/education. **SOC 2 Type II**: de facto B2B AI requirement (Type II, not Type I, for fintech). **GDPR**: largest documented AI-specific fine is €30.5M against Clearview AI (Dutch DPA, Sept 2024); Italy's Garante issued €15M against OpenAI in Dec 2024 (later overturned on appeal in March 2026). Real-time PII redaction at inference is the defensible standard; post-processing cleanup is not enough. **HIPAA**: healthcare bound — cannot send PHI to external AI services without BAA. **PCI-DSS**: AI-interaction-layer coverage requires configuration + contractual agreements, not automatic. **ISO 42001**: emerging AI governance standard, growing procurement requirement alongside ISO 27001. Reference profile: OpenAI maintains SOC 2 Type 2, ISO/IEC 27001:2022, ISO/IEC 27701:2019, GDPR/CCPA/HIPAA (BAA)/FERPA, PCI-DSS for ChatGPT payment components. Cross-framework mapping reduces audit fatigue: access controls map across ISO 27001 A.5.15-5.18, GDPR Art. 32, HIPAA §164.312(a).

**Type:** Learn
**Languages:** (Python optional — compliance is policy + process, not code)
**Prerequisites:** Phase 17 · 25 (Security), Phase 17 · 13 (Observability)
**Time:** ~60 minutes

---

## Learning Objectives · 学习目标

- 列举与 LLM 产品相关的七个 2026 年合规框架，并把每个框架对应到一个客户群
- 引用 EU AI Act 的执行时间线（2024 年 8 月生效；2026 年 8 月执行高风险要求）和两档罚款上限（高风险义务 €15M / 3%，禁止性实践 €35M / 7%）
- 解释为什么后处理 PII 清理对 GDPR 不够，并指出推理层实时脱敏才是可辩护的标准
- 描述跨框架控制映射（例如访问控制同时映射到 ISO 27001 A.5.15-5.18 + GDPR Art. 32 + HIPAA §164.312(a)）

> Enumerate the seven 2026 frameworks relevant to LLM products and match each to a customer segment.
> Cite the EU AI Act enforcement timeline (in force August 2024; high-risk enforcement August 2026) and the two-tier fine ceiling (€15M / 3% for high-risk obligations, €35M / 7% for prohibited practices).
> Explain why post-processing PII cleanup is not enough for GDPR and name real-time inference-layer redaction as the defensible standard.
> Describe cross-framework control mapping (e.g., access control maps to ISO 27001 A.5.15-5.18 + GDPR Art. 32 + HIPAA §164.312(a)).

---

## The Problem · 问题在哪

一个企业客户的采购团队索要 SOC 2 Type II、GDPR、HIPAA BAA、ISO 27001，以及一份「EU AI Act 合规声明」。你的团队只有 SOC 2 Type I。距离 Type II 还有六个月，GDPR Article 30 记录连头都没开。

多框架覆盖不是 LLM 问题——它是企业级 SaaS 问题，外加 LLM 特有的附加层。2026 年的采购团队想要一张矩阵：每个框架一行、每个控制一项，而不是一份 PDF。

> An enterprise customer's procurement asks for SOC 2 Type II, GDPR, HIPAA BAA, ISO 27001, and "EU AI Act compliance statement." Your team has SOC 2 Type I. You're six months from Type II and haven't started GDPR Article 30 records. ... Multi-framework coverage is not an LLM problem — it's an enterprise-SaaS problem, with LLM-specific overlays. Procurement teams in 2026 want a matrix with a row per framework and a column per control, not a PDF.

---

## The Concept · 概念

### The seven frameworks · 七个框架

| 框架 | 适用范围 | LLM 特有要求 |
|-----------|-------|--------------------------|
| SOC 2 Type II | B2B SaaS 基线 | 过程控制需经 6-12 个月持续审计 |
| HIPAA | 美国医疗健康 | 需要 BAA；无签署协议 PHI 不得离开基础设施 |
| GDPR | 欧盟用户 | 实时 PII 脱敏；数据主体权利；Article 30 记录 |
| PCI-DSS | 支付数据 | 涉支付的 AI 需要配置 + 合同 |
| EU AI Act | 服务欧盟用户 | 风险分级；高风险系统：合格性评估、文档、日志 |
| Colorado AI Act | 服务科罗拉多州居民 | 影响评估；申诉权 |
| ISO 42001 | AI 治理 | 新兴标准；与 ISO 27001 配套 |

> | Framework | Scope | LLM-specific requirement |
> SOC 2 Type II: B2B SaaS baseline; process controls audited over 6-12 months. ... GDPR: EU users; real-time PII redaction; data subject rights; Article 30 records. ... EU AI Act: serving EU users; risk tier classification; high-risk systems: conformity assessment, documentation, logging. ... ISO 42001: AI governance; emerging; pairs with ISO 27001.

### EU AI Act timeline · EU AI Act 时间线

- 2024 年 8 月 1 日：生效。
- 2025 年 2 月 2 日：禁止性 AI 实践开始执行。
- 2026 年 8 月 2 日：高风险系统开始执行（合格性评估、文档、日志）。
- 2027 年 8 月：协调立法（harmonized legislation）下产品内嵌的高风险系统。

风险分级：不可接受（禁止）、高风险（合格性评估 + 日志）、有限风险（透明度要求）、最小风险（无约束）。大多数 B2B LLM SaaS 属于有限风险；高风险集中在就业、信贷、教育、执法、移民、基础公共服务。

罚款（Article 99）：违反高风险系统义务最高 €15M 或全球年营业额的 3%（Art. 99(4)）；禁止性 AI 实践最高 €35M 或 7%（Art. 99(3)）；取两者中较高者。

> August 1, 2024: in force. ... August 2, 2026: high-risk systems enforced (conformity assessment, documentation, logging). ... Risk tiers: Unacceptable (banned), High-risk (conformity + logging), Limited-risk (transparency), Minimal-risk (no constraint). Most B2B LLM SaaS is limited-risk; high-risk kicks in for employment, credit, education, law enforcement, migration, essential services. ... Fines (Article 99): up to €15M or 3% global annual turnover for breaches of high-risk-system obligations (Art. 99(4)); up to €35M or 7% for prohibited AI practices (Art. 99(3)); whichever higher applies.

### GDPR — real-time redaction is the standard · GDPR——实时脱敏才是标准

后处理清理（等 LLM 看完数据再脱敏）站不住脚——模型已经看过数据了。推理层实时脱敏是 2026 年的标准：

- LLM 调用前做实体识别。
- 一致性令牌化（Mesh 方案）保住语义。
- 只存脱敏后的提示词；用户同意加入（opt-in）才存原始文本。

最近的执法：针对 Clearview AI 的 €30.5M（荷兰 DPA，2024 年 9 月）是迄今有据可查的最大 AI 专项 GDPR 罚款；针对 OpenAI 的 €15M（意大利 Garante，2024 年 12 月）是最大的 LLM 专项罚款，不过它在 2026 年 3 月的上诉中被推翻，裁决仍在进一步复审中。后处理式的说法已经在审计里折过戟。

> Post-processing cleanup (redact PII after the LLM sees it) is not a defensible posture — the model already saw the data. Real-time inference-layer redaction is the 2026 standard:
> - Entity recognition before the LLM call.
> - Consistent tokenization (Mesh approach) preserves semantics.
> - Store only redacted prompts + consented opt-in raw.
> Recent enforcement: €30.5M against Clearview AI (Dutch DPA, Sept 2024) is the largest documented AI-specific GDPR fine to date; €15M against OpenAI (Italy's Garante, Dec 2024) is the largest LLM-specific fine, though it was overturned on appeal in March 2026 and the ruling remains under further review. Post-processing claims have failed at audit.

### HIPAA — BAA is not optional · HIPAA——BAA 不是可选项

没有签署的商业伙伴协议（Business Associate Agreement, BAA），就不能把 PHI 发给外部 AI 服务。三家超大规模云厂商的 LLM 平台（Bedrock、Azure OpenAI、Vertex）都提供 BAA。OpenAI 直连 API 提供 BAA。Anthropic 直连 API 提供 BAA。发 PHI 之前先确认。

> You cannot send PHI to external AI services without a signed Business Associate Agreement. All three hyperscaler LLM platforms (Bedrock, Azure OpenAI, Vertex) offer BAAs. OpenAI direct API offers BAA. Anthropic direct API offers BAA. Confirm before sending PHI.

### SOC 2 Type II · SOC 2 Type II

Type I：控制项已设计并有文档。
Type II：控制项在 6-12 个月内持续有效运行。

2026 年的 B2B 采购默认要 Type II。Type I 是入门；Type II 才是门槛。

常见审计驱动项：访问日志（谁看了什么）、变更管理（怎么部署的）、风险评估（每季度做吗）、事件响应（演练过吗）。Phase 17 · 25 的审计日志可以直接复用。

> Type I: controls designed and documented.
> Type II: controls operate effectively over 6-12 months.
> B2B procurement in 2026 defaults to Type II. Type I is a starter; Type II is the gate.
> Common audit drivers: access logs (who saw what), change management (how was it deployed), risk assessments (quarterly), incident response (tested?). Audit log from Phase 17 · 25 is directly reusable.

### Cross-framework mapping · 跨框架映射

一份访问控制策略就能满足多个框架的控制项：

| 控制项 | 对应框架 |
|---------|-----------|
| 访问日志（Access logging） | ISO 27001 A.5.15-5.18, GDPR Art. 32, HIPAA §164.312(a) |
| 变更管理（Change management） | ISO 27001 A.8.32, PCI DSS Req. 6, HIPAA breach-notification scope |
| 传输中加密（Encryption in transit） | ISO 27001 A.8.24, GDPR Art. 32, HIPAA §164.312(e) |
| 密钥管理（Secrets management） | ISO 27001 A.8.19, PCI DSS Req. 8, SOC 2 CC6.1 |

合规工具（Drata、Vanta、Secureframe）能自动化这个映射。规模化之后物有所值。

> One access control policy satisfies multiple framework controls: ... Compliance tools (Drata, Vanta, Secureframe) automate this mapping. Worth the cost at scale.

### ISO 42001 — emerging · ISO 42001——新兴标准

2023 年底发布。正随 ISO 27001 一起成为越来越多的采购要求。这是一套 AI 治理框架，涵盖风险管理、数据质量、透明度、人类监督。

> Published late 2023. Growing procurement requirement alongside ISO 27001. Framework for AI governance including risk management, data quality, transparency, human oversight.

### OpenAI's reference profile · OpenAI 的参考配置

OpenAI 持有 SOC 2 Type 2、ISO/IEC 27001:2022、ISO/IEC 27701:2019、GDPR/CCPA/HIPAA (BAA)/FERPA，以及 ChatGPT 支付组件的 PCI-DSS。这大致就是 2026 年企业级签单的入场券。

> OpenAI maintains SOC 2 Type 2, ISO/IEC 27001:2022, ISO/IEC 27701:2019, GDPR/CCPA/HIPAA (BAA)/FERPA, PCI-DSS for ChatGPT payment components. That is roughly the enterprise table stakes in 2026.

### Numbers you should remember · 该记住的数字

- EU AI Act 罚款：最高 €15M / 3%（高风险义务，Art. 99(4)）；最高 €35M / 7%（禁止性实践，Art. 99(3)）。
- EU AI Act 高风险执行日：2026 年 8 月 2 日。
- 有据可查的最大 AI 专项 GDPR 罚款：€30.5M，Clearview AI（荷兰 DPA，2024 年 9 月）。
- 最大 LLM 专项 GDPR 罚款：€15M，OpenAI（意大利 Garante，2024 年 12 月；2026 年 3 月上诉被推翻）。
- SOC 2 Type II 观察窗：控制项持续运行 6-12 个月。
- Colorado AI Act 生效日：2026 年 6 月 30 日（被 SB25B-004 从 2026 年 2 月推迟）。

> EU AI Act fines: up to €15M / 3% (high-risk obligations, Art. 99(4)); up to €35M / 7% (prohibited practices, Art. 99(3)).
> EU AI Act high-risk enforcement: August 2, 2026.
> Largest documented AI-specific GDPR fine: €30.5M, Clearview AI (Dutch DPA, Sept 2024).
> Largest LLM-specific GDPR fine: €15M, OpenAI (Italy's Garante, Dec 2024; overturned on appeal March 2026).
> SOC 2 Type II window: 6-12 months of operated controls.
> Colorado AI Act effective date: June 30, 2026 (delayed from February 2026 by SB25B-004).

```figure
i4-control-matrix
```

---

## Use It · 实战用法

`code/main.py` 是一个用 Python 写的合规映射表——输入一个控制项，列出它满足哪些框架。

> `code/main.py` is a compliance-mapping spreadsheet in Python — given a control, lists frameworks it satisfies.

---

## Ship It · 交付

本课产出 `outputs/skill-compliance-matrix.md`。输入客户群和地域，它给出所需的框架和控制项。

> This lesson produces `outputs/skill-compliance-matrix.md`. Given customer segment and geography, specifies required frameworks and controls.

---

## Exercises · 练习

1. 你的第一个企业客户要求 SOC 2 Type II、HIPAA BAA 和 EU AI Act 声明。拿下这单的最低可行合规姿态是什么？
2. 把三个假想的 LLM 产品归入 EU AI Act 风险分级。到了高风险会改变什么？
3. 你在无 BAA 的情况下误发了 PHI。走一遍事件响应流程。
4. 论证 ISO 42001 对一个中端市场 AI 供应商来说在 2026 年是否「必要」。
5. 把你的 LLM 审计日志字段（Phase 17 · 25）映射到至少三个框架控制项。

---

## Key Terms · 术语表

| 术语 | 人们口头说 | 实际含义 |
|------|----------------|------------------------|
| SOC 2 Type II | 「经审计的控制项」 | 控制项持续运行 6-12 个月，由第三方独立证明 |
| HIPAA BAA | 「医疗合同」 | 商业伙伴协议；处理 PHI 必需 |
| GDPR | 「欧盟隐私」 | 推理层实时 PII 脱敏是 2026 年可辩护的标准 |
| EU AI Act | 「欧盟 AI 法规」 | 高风险 2026 年 8 月执行；€15M / 3%（高风险义务）——€35M / 7%（禁止性实践） |
| Colorado AI Act | 「美国州级 AI 法」 | 2026 年 6 月 30 日生效（被 SB25B-004 推迟）；影响评估 |
| ISO 42001 | 「AI 治理」 | 新兴的 AI 风险 + 透明度框架 |
| ISO 27001 | 「安全 ISMS」 | 信息安全管理体系基线 |
| Conformity assessment | 「EU AI 文档包」 | 高风险要求：文档、测试、日志 |
| Cross-framework mapping | 「一控多框」 | 单一策略满足多个框架的控制项 |

---

## Further Reading · 延伸阅读

- [OpenAI Security and Privacy](https://openai.com/security-and-privacy/) —— 参考合规配置
- [GuardionAI — LLM Compliance 2026: ISO 42001, EU AI Act, SOC 2, GDPR](https://guardion.ai/blog/llm-compliance-guide-iso-42001-eu-ai-act-soc2-gdpr-2026)
- [Dsalta — SOC 2 Type 2 Audit Guide 2026: 10 AI Controls](https://www.dsalta.com/resources/ai-compliance/soc-2-type-2-audit-guide-2026-10-ai-powered-controls-every-saas-team-needs)
- [EU AI Act official text](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) —— 一手来源
- [Colorado AI Act](https://leg.colorado.gov/bills/sb24-205) —— 一手来源
- [ISO/IEC 42001:2023](https://www.iso.org/standard/81230.html) —— AI 管理体系标准
