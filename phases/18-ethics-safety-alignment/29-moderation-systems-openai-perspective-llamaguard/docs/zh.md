# Moderation Systems — OpenAI, Perspective, Llama Guard · 审核系统 —— OpenAI、Perspective、Llama Guard

> 生产级审核系统把第 12-16 课定义的安全政策落到实处。OpenAI Moderation API：`omni-moderation-latest`（2024）构建于 GPT-4o 之上，一次调用同时分类文本 + 图像；在多语言测试集上比上一版本好 42%；响应模式返回 13 个类别布尔值 —— harassment、harassment/threatening、hate、hate/threatening、illicit、illicit/violent、self-harm、self-harm/intent、self-harm/instructions、sexual、sexual/minors、violence、violence/graphic；对大多数开发者免费。分层模式：输入审核（生成前）、输出审核（生成后）、自定义审核（领域规则）。异步并行调用隐藏延迟；命中标志时返回占位响应。Llama Guard 3/4（第 16 课）：14 个 MLCommons 危害类别、Code Interpreter Abuse、8 种语言（v3）、多图（v4）。Perspective API（Google Jigsaw）：早于 LLM-as-moderator 浪潮的毒性评分；以单维度毒性为主，另有 severe-toxicity/insult/profanity 变体；内容审核研究的基线。弃用情况：Azure Content Moderator 于 2024 年 2 月弃用、2027 年 2 月退役，由 Azure AI Content Safety 取代。

> Production moderation systems operationalize the safety policies defined in Lessons 12-16. OpenAI Moderation API: `omni-moderation-latest` (2024) built on GPT-4o classifies text + images in one call; 42% better on multilingual test set than prior version; the response schema returns 13 category booleans — harassment, harassment/threatening, hate, hate/threatening, illicit, illicit/violent, self-harm, self-harm/intent, self-harm/instructions, sexual, sexual/minors, violence, violence/graphic; free for most developers. Layered patterns: Input moderation (pre-generation), Output moderation (post-generation), Custom moderation (domain rules). Async parallel calls hide latency; placeholder responses on flag. Llama Guard 3/4 (Lesson 16): 14 MLCommons hazards, Code Interpreter Abuse, 8 languages (v3), multi-image (v4). Perspective API (Google Jigsaw): toxicity scoring predating the LLM-as-moderator wave; primarily single-dimension toxicity with severe-toxicity/insult/profanity variants; baseline for content-moderation research. Deprecations: Azure Content Moderator deprecated February 2024, retired February 2027, replaced by Azure AI Content Safety.

**Type:** Build
**Languages:** Python (stdlib, three-layer moderation harness)
**Prerequisites:** Phase 18 · 16 (Llama Guard / Garak / PyRIT)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 描述 OpenAI Moderation API 的类别体系，以及它与 Llama Guard 3 的 MLCommons 集合的差异。
- 描述三层审核模式（输入、输出、自定义），并说出每一层的一个失效模式。
- 描述 Perspective API 作为前 LLM 时代基线的定位，以及它为何仍被研究界使用。
- 说出 Azure 的弃用时间线。

> Describe the OpenAI Moderation API's category taxonomy and how it differs from Llama Guard 3's MLCommons set.
> Describe the three moderation-layer pattern (input, output, custom) and name one failure mode of each.
> Describe Perspective API's position as a pre-LLM-era baseline and why it remains used in research.
> State the Azure deprecation timeline.

## The Problem · 问题

第 12-16 课描述了攻击与防御工具。第 29 课讲的是把这些防御落到用户触碰产品那一界面的已部署审核系统。三层模式是 2026 年的默认配置。

> Lessons 12-16 describe attacks and defense tooling. Lesson 29 covers the deployed moderation systems that operationalize the defenses at the surface where users touch the product. The three-layer pattern is the 2026 default configuration.

## The Concept · 概念

### OpenAI Moderation API · OpenAI 审核 API

`omni-moderation-latest`（2024）。构建于 GPT-4o。一次调用同时分类文本 + 图像。对大多数开发者免费。

类别（响应模式中的 13 个布尔值）：
- harassment, harassment/threatening
- hate, hate/threatening
- self-harm, self-harm/intent, self-harm/instructions
- sexual, sexual/minors
- violence, violence/graphic
- illicit, illicit/violent

多模态支持适用于 `violence`、`self-harm` 和 `sexual`，但不适用于 `sexual/minors`；其余类别仅限文本。

在 `code/main.py` 的代码示例里，为了教学简洁，我们把 `/threatening`、`/intent`、`/instructions`、`/graphic` 这些子类别折叠进各自的顶级父类别。生产代码应使用完整的 13 类别模式。

在多语言测试集上比上一代审核端点好 42%。逐类别给分；由应用自己设定阈值。

> `omni-moderation-latest` (2024). Built on GPT-4o. Classifies text + images in one call. Free for most developers.
> Multimodal support applies to `violence`, `self-harm`, and `sexual` but not `sexual/minors`; the rest are text-only.
> 42% better on multilingual test set than the prior-generation moderation endpoint. Per-category scores; applications set thresholds.

### Llama Guard 3/4 · Llama Guard 3/4

第 16 课已讲过。14 个 MLCommons 危害类别（组织方式不同于 OpenAI 的 13 个响应模式布尔值）。支持 8 种语言（v3）。Llama Guard 4（2025 年 4 月）原生多模态，12B。

OpenAI 与 Llama Guard 的分类体系有重叠但并不相同。OpenAI 把 "illicit" 作为一个大类；Llama Guard 则把 "violent crimes" 与 "non-violent crimes" 分开。部署方按政策体系的契合度来选择。

> Covered in Lesson 16. 14 MLCommons hazard categories (organized differently from OpenAI's 13 response-schema booleans). Supports 8 languages (v3). Llama Guard 4 (April 2025) is natively multimodal, 12B.
> The OpenAI and Llama Guard taxonomies overlap but diverge. OpenAI has "illicit" as a broad category; Llama Guard has "violent crimes" and "non-violent crimes" separately. Deployments pick based on their policy-taxonomy fit.

### Perspective API (Google Jigsaw) · Perspective API（Google Jigsaw）

早于 LLM-as-moderator 浪潮（2020 年之前）的毒性评分系统。类别：TOXICITY、SEVERE_TOXICITY、INSULT、PROFANITY、THREAT、IDENTITY_ATTACK。单一主维度得分（TOXICITY）加子维度变体。

它被广泛用作内容审核研究基线，因为这个 API 稳定、文档齐全、并且有多年的校准数据。对现代 LLM 相邻的用例，Llama Guard 或 OpenAI Moderation 通常是更合适的选择。

> Toxicity scoring system predating the LLM-as-moderator wave (pre-2020). Categories: TOXICITY, SEVERE_TOXICITY, INSULT, PROFANITY, THREAT, IDENTITY_ATTACK. Single-dimension primary score (TOXICITY) with sub-dimension variants.
> Widely used as a content-moderation research baseline because the API is stable, documented, and has years of calibration data. For modern LLM-adjacent use cases, Llama Guard or OpenAI Moderation is typically a better fit.

### The three-layer pattern · 三层模式

1. **输入审核。** 在生成之前对用户的提示词分类。命中则拒绝。延迟：一次分类器调用。
2. **输出审核。** 在交付之前对模型的输出分类。命中则替换为拒绝话术。延迟：生成之后再调用一次分类器。
3. **自定义审核。** 领域特定规则（regex、allowlist、业务政策）。在输入端或输出端运行。

这三层在设计上就是串行的：输入审核必须在生成之前完成，输出审核在生成之后运行。并行只发生在层内 —— 在同一段文本上并发运行多个分类器（例如 OpenAI Moderation + Llama Guard + Perspective）可以隐藏单个分类器的延迟。一个可选优化：在输入审核完成之前先展示占位响应（"one moment, checking..."），并推迟首 token 的流式输出。命中后的行为可配置：拒绝、清洗、或升级人工审核。

> Input moderation. Classify the user's prompt before generation. Reject if flagged. Latency: one classifier call. Output moderation. Classify the model's output before delivery. Replace with a refusal if flagged. Latency: one classifier call after generation. Custom moderation. Domain-specific rules (regex, allowlists, business policy). Runs at either input or output.
> The three layers are sequential by design: input moderation must complete before generation, and output moderation runs after generation. Parallelism applies within a layer — running multiple classifiers (e.g., OpenAI Moderation + Llama Guard + Perspective) concurrently on the same text hides per-classifier latency. As an optional optimization, a placeholder response ("one moment, checking...") may be shown while input moderation completes and token-1 streaming is deferred. Flag behaviour is configurable: refuse, sanitize, escalate to human review.

### Failure modes · 失效模式

- **只用输入层。** 抓不住输出端的幻觉（第 12-14 课的编码攻击可绕过输入分类器）。
- **只用输出层。** 任何输入都能到达模型；增加成本；把内部推理暴露给攻击者。
- **只用自定义层。** 跨类别不鲁棒；regex 脆弱。

分层是默认。双保险（belt-and-suspenders）。

> Input only. Does not catch output hallucinations (Lesson 12-14 encoding attacks bypass input classifiers).
> Output only. Allows any input to reach the model; increases cost; surfaces internal reasoning to attacker.
> Custom only. Not robust across categories; regexes are brittle.
> Layered is the default. Belt-and-suspenders.

### Azure deprecation · Azure 弃用

Azure Content Moderator：2024 年 2 月弃用，2027 年 2 月退役。由 Azure AI Content Safety 取代，后者基于 LLM 并与 Azure OpenAI 集成。对 Azure 部署而言，这是一场横跨 2024-2027 的现场级（field-level）迁移工程。

> Azure Content Moderator: deprecated February 2024, retired February 2027. Replaced by Azure AI Content Safety, which is LLM-based and integrates with Azure OpenAI. The migration is a 2024-2027 field-level project for Azure deployments.

### Where this fits in Phase 18 · 在 Phase 18 中的位置

第 16 课在红队语境下讲审核工具。第 29 课讲已部署的审核。第 30 课以当前的双重用途能力证据收尾。

> Lesson 16 covers the moderation tooling in the red-team context. Lesson 29 covers deployed moderation. Lesson 30 closes with the current dual-use capability evidence.

```figure
an-moderation-layers
```

## Use It · 实战用法

`code/main.py` 构建一个三层审核 harness：输入审核器（关键词 + 类别分数）、输出审核器（同一分类器跑在输出上）、自定义审核器（领域规则）。你可以把输入喂进去，观察哪一层抓住了什么。

> `code/main.py` builds a three-layer moderation harness: input moderator (keyword + category score), output moderator (same classifier on output), custom moderator (domain rules). You can run inputs through and observe which layer catches what.

## Ship It · 交付

本课产出 `outputs/skill-moderation-stack.md`。给定一个部署，它会推荐一套审核栈配置：输入端用哪个分类器、输出端用哪个、配哪些自定义规则、边界情况用哪个裁判（judge）。

> This lesson produces `outputs/skill-moderation-stack.md`. Given a deployment, it recommends a moderation stack configuration: which classifier at input, which at output, which custom rules, and what judge for edge cases.

## Exercises · 练习

1. 运行 `code/main.py`。把一条良性、一条边缘、一条有害的输入跑过全部三层。报告每条输入是哪一层触发的。

2. 给 harness 扩展一个 Perspective-API 风格的特定类别毒性评分。把它的阈值行为与类别分数做比较。

3. 阅读 OpenAI Moderation API 文档与 Llama Guard 3 的类别列表。把每个 OpenAI 类别映射到最接近的 Llama Guard 类别。找出三个无法干净映射的类别。

4. 为一个代码助手部署（例如 GitHub Copilot）设计审核栈。找出最相关和最不相关的类别，并提出自定义规则。

5. Azure Content Moderator 将于 2027 年 2 月退役。规划一次向 Azure AI Content Safety 的迁移。找出迁移中风险最高的环节。

> Run `code/main.py`. Run a benign, borderline, and harmful input through all three layers. Report which layer fires for each. ... Azure Content Moderator retires February 2027. Plan a migration to Azure AI Content Safety. Identify the highest-risk element of the migration.

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|------------------------|
| OpenAI Moderation | "omni-moderation-latest" | 基于 GPT-4o 的 13 类别（文本）分类器，部分支持多模态 |
| Perspective API | 「Google Jigsaw 毒性」 | 前 LLM 时代的毒性评分基线 |
| Llama Guard | 「MLCommons 14 类别」 | Meta 的危害分类器（v3：8B 文本、8 语言；v4：12B 多模态） |
| Input moderation | 「生成前过滤器」 | 模型调用之前对用户提示词的分类器 |
| Output moderation | 「生成后过滤器」 | 交付之前对模型输出的分类器 |
| Custom moderation | 「领域规则」 | 部署特定的规则（regex、allowlist、政策） |
| Layered moderation | 「三层全上」 | 标准的生产部署模式 |

## Further Reading · 延伸阅读

- [OpenAI Moderation API docs](https://platform.openai.com/docs/api-reference/moderations) — omni-moderation 端点
- [Meta PurpleLlama + Llama Guard](https://github.com/meta-llama/PurpleLlama) — Llama Guard 仓库
- [Google Jigsaw Perspective API](https://perspectiveapi.com/) — 毒性评分
- [Azure AI Content Safety](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/) — Azure 的替代品
