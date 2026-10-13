# Red-Team Tooling — Garak, Llama Guard, PyRIT · 红队工具链：Garak、Llama Guard、PyRIT

> 三款生产级工具勾勒出 2026 年的红队工具栈（red-team stack）。Llama Guard（Meta）—— 一个在 14 个 MLCommons 危害类别上微调的 Llama-3.1-8B 分类器；2025 年的 Llama Guard 4 是从 Llama 4 Scout 剪枝而来的 12B 原生多模态分类器。Garak（NVIDIA）—— 开源 LLM 漏洞扫描器，提供针对幻觉（hallucination）、数据泄露、提示注入（prompt injection）、毒性、越狱（jailbreak）的静态、动态与自适应探针（probe）。PyRIT（Microsoft）—— 多轮红队战役工具，内置 Crescendo、TAP 和自定义 converter 链，用于深度利用。Llama Guard 3 记录于 Meta 的 "Llama 3 Herd of Models"（arXiv:2407.21783）；Llama Guard 3-1B-INT4 见 arXiv:2411.17713；Garak 的探针架构见 github.com/NVIDIA/garak。这些工具是 2026 年红队研究（第 12-15 课）与部署（第 17 课起）之间的生产级接口。

> Three production tools frame the 2026 red-team stack. ... Llama Guard (Meta) — a Llama-3.1-8B classifier fine-tuned on 14 MLCommons hazard categories; the 2025 Llama Guard 4 is a 12B natively multimodal classifier pruned from Llama 4 Scout. Garak (NVIDIA) — open-source LLM vulnerability scanner with static, dynamic, and adaptive probes for hallucination, data leakage, prompt injection, toxicity, and jailbreaks. PyRIT (Microsoft) — multi-turn red-team campaigns with Crescendo, TAP, and custom converter chains for deep exploitation. ... These tools are the 2026 production interface between red-team research (Lessons 12-15) and deployment (Lesson 17+).

**Type:** Build
**Languages:** Python (stdlib, tool-architecture simulator and Llama Guard-style classifier mock)
**Prerequisites:** Phase 18 · 12-15 (jailbreaks and IPI)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 描述 Llama Guard 3/4 在安全栈中的位置：输入分类器、输出分类器，还是两者兼用
- 说出 14 个 MLCommons 危害类别，并举出一个不显眼的类别（Code Interpreter Abuse，代码解释器滥用）
- 描述 Garak 的探针架构：probes、detectors、harnesses
- 描述 PyRIT 的多轮战役（campaign）结构，以及它如何与 Garak 探针组合使用

> Describe Llama Guard 3/4's position in the safety stack: input classifier, output classifier, or both.
> Name the 14 MLCommons hazard categories and state one non-obvious one (Code Interpreter Abuse).
> Describe Garak's probe architecture: probes, detectors, harnesses.
> Describe PyRIT's multi-turn campaign structure and how it composes with Garak probes.

## The Problem · 问题在哪

第 12-15 课呈现的是攻击面。生产部署需要可重复、可规模化的评估。2026 年由三款工具主导：Llama Guard（防御分类器）、Garak（扫描器）、PyRIT（战役编排器）。三者各自瞄准红队生命周期（red-team lifecycle）的不同层。

> Lessons 12-15 present the attack surface. Production deployments need repeatable, scalable evaluation. Three tools dominate 2026: Llama Guard (the defense classifier), Garak (the scanner), PyRIT (the campaign orchestrator). Each targets a different layer of the red-team lifecycle.

## The Concept · 概念

### Llama Guard (Meta) · Llama Guard（Meta）

Llama Guard 3 是一个 Llama-3.1-8B 模型，针对 MLCommons AILuminate 14 个类别做了输入/输出分类微调：
- 暴力犯罪（violent crimes）、非暴力犯罪、性相关犯罪、CSAM（儿童性剥削材料）、诽谤
- 专业建议（specialized advice）、隐私、知识产权（IP）、无差别武器、仇恨
- 自杀/自残、性内容、选举、代码解释器滥用（code-interpreter abuse）

支持 8 种语言。用法：放在 LLM 之前（输入审核）、放在 LLM 之后（输出审核），或两者都放。这两种用法对应不同的训练数据分布 —— Llama Guard 3 以单一模型同时支持两者。

Llama Guard 3-1B-INT4（arXiv:2411.17713，440MB，移动端 CPU 上约 30 tokens/s）是量化后的边缘端（edge）变体。

Llama Guard 4（2025 年 4 月）是 12B、原生多模态，从 Llama 4 Scout 剪枝而来。它用一个同时接收文本 + 图像的分类器，一并取代了 8B 文本版和 11B 视觉版两代前辈。

> Llama Guard 3 is a Llama-3.1-8B model fine-tuned for input/output classification over the MLCommons AILuminate 14 categories. ... Supports 8 languages. Usage: place before the LLM (input moderation), after the LLM (output moderation), or both. The two uses generate different training distributions — Llama Guard 3 ships as a single model handling both. ... Llama Guard 4 (April 2025) is 12B, natively multimodal, pruned from Llama 4 Scout. It replaces both the 8B text and 11B vision predecessors with one classifier that ingests text + images.

### Garak (NVIDIA) · Garak（NVIDIA）

开源漏洞扫描器。架构：
- **Probes（探针）。** 攻击生成器，覆盖幻觉、数据泄露、提示注入、毒性、越狱。静态（固定提示词）、动态（生成的提示词）、自适应（根据目标输出做出反应）。
- **Detectors（检测器）。** 按预期失败模式给输出打分 —— 有毒、泄露、被越狱。
- **Harnesses（测试框架）。** 管理 probe-detector 配对、运行战役、生成报告。

TrustyAI 把 Garak 与 Llama-Stack 的 shields（Prompt-Guard-86M 输入分类器、Llama-Guard-3-8B 输出分类器）集成起来，做端到端的带护盾目标评估。分层评分（tier-based scoring，TBSA）取代了二元的 pass/fail —— 同一个 probe 上，模型可以在严重度第 3 层通过，却在第 5 层失败。

> Open-source vulnerability scanner. Architecture:
> **Probes.** Attack generators for hallucination, data leakage, prompt injection, toxicity, jailbreaks. Static (fixed prompts), dynamic (generated prompts), adaptive (responds to target output).
> **Detectors.** Score outputs against expected failure modes — toxic, leaked, jailbroken.
> **Harnesses.** Manage probe-detector pairs, run campaigns, generate reports.
> TrustyAI integrates Garak with the Llama-Stack shields (Prompt-Guard-86M input classifier, Llama-Guard-3-8B output classifier) for end-to-end shielded-target evaluation. Tier-based scoring (TBSA) replaces binary pass/fail — a model can pass at severity tier 3 and fail at severity tier 5 on the same probe.

### PyRIT (Microsoft) · PyRIT（Microsoft）

Python Risk Identification Toolkit（Python 风险识别工具包）。多轮红队战役。围绕三件事构建：
- **Converters（转换器）。** 变换种子提示词 —— 改写、编码、翻译、角色扮演。
- **Orchestrators（编排器）。** 运行战役：Crescendo（逐级升格）、TAP（分支扩展）、RedTeaming（自定义循环）。
- **Scoring（评分）。** LLM 当裁判（LLM-as-judge）或分类器当裁判（classifier-as-judge）。

PyRIT 是 Garak 的重量级表亲。Garak 跑的是数千个单轮 probe；PyRIT 跑的是为击穿特定失败模式而设计的深度多轮战役。

> Python Risk Identification Toolkit. Multi-turn red-team campaigns. Built around:
> **Converters.** Transform a seed prompt — paraphrase, encode, translate, roleplay.
> **Orchestrators.** Run the campaign: Crescendo (escalation), TAP (branching), RedTeaming (custom loop).
> **Scoring.** LLM-as-judge or classifier-as-judge.
> PyRIT is the heavier cousin of Garak. Garak runs thousands of single-turn probes; PyRIT runs deep multi-turn campaigns designed to break specific failure modes.

### The stack · 组合方式

把 Llama Guard 放在模型两侧。每晚跑 Garak 做回归。发版前跑 PyRIT 战役。这就是 2026 年大多数生产部署的默认配置。

> Put Llama Guard on both sides of the model. Run Garak nightly for regression. Run PyRIT for pre-release campaigns. This is the 2026 default configuration for most production deployments.

### Evaluation pitfalls · 评估陷阱

- **裁判身份（judge identity）。** 三款工具都可以用 LLM 当裁判；裁判的校准直接决定报告出的 ASR（第 12 课）。报告工具时要一并指明用的是哪个裁判。
- **探针老化（probe staleness）。** 模型一旦针对 Garak 探针打了补丁，探针就会过时。自适应探针（PAIR 形态）比静态探针老化得慢。
- **Llama Guard 在良性内容上的误报（FPR）。** 早期 Llama Guard 版本会对政治和 LGBTQ+ 内容过度标记；Llama Guard 3/4 的校准已有改进，但并未针对每个部署单独校准。

> **Judge identity.** All three tools can use an LLM judge; judge calibration drives reported ASRs (Lesson 12). Specify the judge alongside the tool.
> **Probe staleness.** Garak probes age as models are patched against them. Adaptive probes (PAIR-shaped) age slower than static probes.
> **Llama Guard FPR on benign content.** Early Llama Guard versions over-flagged political and LGBTQ+ content; Llama Guard 3/4 calibrations are improved but not calibrated per-deployment.

### Where this fits in Phase 18 · 在 Phase 18 中的位置

第 12-15 课是各个攻击族（attack families）。第 16 课是生产工具链。第 17 课（WMDP）是对双用途能力（dual-use capability）的评估。第 18 课是把这套工具包进政策结构的前沿安全框架。

> Lessons 12-15 are the attack families. Lesson 16 is the production tooling. Lesson 17 (WMDP) is the evaluation for dual-use capability. Lesson 18 is the frontier safety frameworks that wrap these tools in a policy structure.

```figure
al-guard-stack
```

## Use It · 实战用法

`code/main.py` 构建了一个玩具版 Llama Guard 风格分类器（关键词 + 语义特征，覆盖 14 个类别）、一个玩具版 Garak harness（probe-detector 循环），以及一条 PyRIT 风格的多轮 converter 链。你可以让这三样工具对着同一个 mock 目标运行，观察它们各自不同的覆盖特征（coverage signatures）。

> `code/main.py` builds a toy Llama Guard-style classifier (keyword + semantic features over 14 categories), a toy Garak harness (probe-detector loop), and a PyRIT-style multi-turn converter chain. You can run the three tools against a mock target and observe the different coverage signatures.

## Ship It · 交付

本课产出 `outputs/skill-red-team-stack.md`。给定一段部署描述，它会指出三款工具中哪些适用、每款需要配置什么、以及该以什么节奏跑回归。

> This lesson produces `outputs/skill-red-team-stack.md`. Given a deployment description, it names which of the three tools are appropriate, what to configure in each, and what regression cadence to run.

## Exercises · 练习

1. 运行 `code/main.py`。对比 Llama Guard 风格分类器在单轮与多轮攻击上的检出率。

2. 实现一个新的 Garak probe：一个 base64 编码的有害请求。测量 Llama Guard 风格分类器对它的检出情况。

3. 给 PyRIT 风格的 converter 链增加一个「先翻译成法语，再改写」的 converter。重新测量攻击成功率。

4. 通读 Llama Guard 3 的危害类别列表。找出两个这样的类别：其训练数据在合法开发者内容上会现实地产生高误报率。

5. 比较 Garak 与 PyRIT 的设计原则。分别为两者论证一种「它才是正确工具」的部署场景。

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|-----------------|------------------------|
| Llama Guard | 「分类器」 | 在 14 个危害类别上微调的 Llama-3.1-8B/4-12B 安全分类器 |
| Garak | 「扫描器」 | NVIDIA 开源漏洞扫描器；probes、detectors、harnesses |
| PyRIT | 「战役工具」 | Microsoft 多轮红队编排器；converters、orchestrators、scoring |
| Prompt-Guard | 「小分类器」 | Meta 的 86M 提示注入分类器，与 Llama Guard 配对使用 |
| TBSA | 「tier-based scoring」 | Garak 的分层 pass/fail 评分，取代二元结果 |
| Converter chain | 「paraphrase + encode + ...」 | PyRIT 的组合原语，用来搭建多步攻击 |
| MLCommons hazard categories | 「那 14 个分类体系」 | Llama Guard 对标的行业标准危害分类体系 |

## Further Reading · 延伸阅读

- [Meta — Llama Guard 3 (in Llama 3 Herd paper, arXiv:2407.21783)](https://arxiv.org/abs/2407.21783) —— 8B 分类器
- [Meta — Llama Guard 3-1B-INT4 (arXiv:2411.17713)](https://arxiv.org/abs/2411.17713) —— 量化移动端分类器
- [NVIDIA Garak — GitHub](https://github.com/NVIDIA/garak) —— 扫描器仓库与文档
- [Microsoft PyRIT — GitHub](https://github.com/Azure/PyRIT) —— 战役工具包
