# Bias and Representational Harm in LLMs · LLM 中的偏见与代表性伤害

> Gallegos、Rossi、Barrow、Tanjim、Kim、Dernoncourt、Yu、Zhang、Ahmed（Computational Linguistics 2024，arXiv:2309.00770）。这份 2024 年的奠基性综述区分了代表性伤害（representational harm：刻板印象、抹除）与分配性伤害（allocational harm：资源分配不平等），并把评估指标归为基于嵌入、基于概率、基于生成文本三类。2024-2025 年实证进展：An 等（PNAS Nexus，2025 年 3 月）在 20 个入门级岗位的自动简历评估上，测量了 GPT-3.5 Turbo、GPT-4o、Gemini 1.5 Flash、Claude 3.5 Sonnet、Llama 3-70B 上的性别 × 种族交叉偏见。WinoIdentity（COLM 2025，arXiv:2508.07111）为交叉身份引入了基于不确定性的公平性评估。Yu & Ananiadou 2025 在 MLP 层中识别出性别神经元；Ahsan & Wallace 2025 用 SAE 揭示临床种族偏见；Zhou 等 2024（UniBias）操纵注意力头实现去偏。元层批评（arXiv:2508.11067）：十年文献不成比例地聚焦二元性别偏见。

> Gallegos, Rossi, Barrow, Tanjim, Kim, Dernoncourt, Yu, Zhang, Ahmed (Computational Linguistics 2024, arXiv:2309.00770). Foundational 2024 survey distinguishing representational harms (stereotypes, erasure) from allocational harms (unequal resource distribution) and categorizing evaluation metrics as embedding-based, probability-based, or generated-text-based. 2024-2025 empirical: An et al. (PNAS Nexus, March 2025) measure intersectional gender x race bias across GPT-3.5 Turbo, GPT-4o, Gemini 1.5 Flash, Claude 3.5 Sonnet, Llama 3-70B on automated resume evaluation for 20 entry-level jobs. WinoIdentity (COLM 2025, arXiv:2508.07111) introduces uncertainty-based fairness evaluation for intersectional identities. Yu & Ananiadou 2025 identify gender neurons in MLP layers; Ahsan & Wallace 2025 use SAEs to reveal clinical racial bias; Zhou et al. 2024 (UniBias) manipulates attention heads for debiasing. Meta-critique (arXiv:2508.11067): 10-year literature disproportionately focuses on binary-gender bias.

**Type:** Build
**Languages:** Python (stdlib, toy embedding-based bias probe)
**Prerequisites:** Phase 05 (word embeddings), Phase 18 · 01 (instruction following)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 定义代表性伤害与分配性伤害（allocational harm），并各给出一个 LLM 部署中的例子。
- 说出 Gallegos 等 2024 的三个评估指标类别，并从每类中各描述一个指标。
- 描述交叉性（intersectionality），以及为什么 WinoIdentity 基于不确定性的公平性测量弥补了单轴偏见评估的缺口。
- 描述两种针对偏见的机械可解释性路径（性别神经元、SAE 特征、注意力头操纵）。

> Define representational vs allocational harm and give one example of each in an LLM deployment.
> Name the three evaluation-metric categories from Gallegos et al. 2024 and describe one metric from each.
> Describe intersectionality and why WinoIdentity's uncertainty-based fairness measurement addresses gaps in single-axis bias evaluation.
> Describe two mechanistic-interpretability approaches to bias (gender neurons, SAE features, attention-head manipulation).

## The Problem · 问题所在

前面的课程覆盖的是蓄意伤害（越狱、图谋行为）与安全治理。偏见是无意图情况下涌现的伤害——来自训练数据分布、来自提示措辞、来自累积的设计选择。测量与削减它，是一项不同于对抗鲁棒性的方法论挑战。

> The previous lessons cover deliberate harm (jailbreaks, scheming) and safety governance. Bias is harm that emerges without intent — from training data distributions, from prompt framing, from accumulated design choices. Measuring and reducing it is a distinct methodological challenge from adversarial robustness.

## The Concept · 概念

### Representational vs allocational · 代表性伤害 vs 分配性伤害

- **代表性伤害（representational harm）。** 刻板印象、抹除、贬损性描绘。一个把护士只描绘成女性的 LLM 在制造代表性伤害。
- **分配性伤害（allocational harm）。** 不平等的物质结果。一个系统性地给黑人申请者简历打低分的 LLM 在制造分配性伤害。

这两者不是一回事。一个模型可以「表征上无偏见」（产出多样的描绘），同时「分配上有偏见」（做出不平等的建议）。评估需要两者都测。

> **Representational harm.** Stereotypes, erasure, demeaning portrayals. An LLM that depicts nurses as exclusively female is producing representational harm.
> **Allocational harm.** Unequal material outcomes. An LLM that scores Black applicants' resumes systematically lower is producing allocational harm.
> These are not the same. A model can be "representationally unbiased" (produces diverse portrayals) while being "allocationally biased" (makes unequal recommendations). Evaluations need to measure both.

### Three evaluation-metric categories (Gallegos et al. 2024) · 三类评估指标（Gallegos et al. 2024）

- **基于嵌入（Embedding-based）。** 在预 RLHF 嵌入上做 WEAT 式测试，测量身份词与属性词之间的统计关联。局限：测的是表征，不是行为。
- **基于概率（Probability-based）。** 刻板印象确认式补全与刻板印象违反式补全的对数似然之比。解码侧测量，能捕捉部分行为偏见。
- **基于生成文本（Generated-text-based）。** 在生成文本上做下游任务测量：简历打分、推荐信写作、对话。生态效度最高，也最难复现。

> **Embedding-based.** WEAT-style tests on pre-RLHF embeddings. Measures statistical associations between identity terms and attribute terms. Limited: measures the representation, not the behaviour.
> **Probability-based.** Log-likelihood of stereotype-confirming vs stereotype-violating completions. Decoder-side measurement. Captures some behavioural bias.
> **Generated-text-based.** Downstream-task measurement on generated text. Resume-scoring, recommendation writing, dialogue. Most ecologically valid; hardest to reproduce.

### Intersectionality · 交叉性

只在「性别」这一个轴上做偏见评估，会漏掉那些只在（性别、种族）组合上才触发的偏见。An 等 2025 发现，GPT-4o 在简历打分中对黑人女性的惩罚大于对黑人男性，也大于对白人女性。单轴评估捕捉不到这一点。

WinoIdentity（COLM 2025）引入了基于不确定性的交叉公平性。它测量模型对结果的不确定性是否在交叉身份元组之间存在差异——而不只看点预测。这能捕捉模型在各组上「错得一样但对某些组更不确定」的情形，而这种差异会产生不同的下游分配行为。

> Bias evaluation on "gender" misses the bias that only fires on (gender, race) pairs. An et al. 2025 find GPT-4o penalizes Black women in resume scoring more than Black men and more than white women separately. Single-axis evaluation cannot capture this.
> WinoIdentity (COLM 2025) introduces uncertainty-based intersectional fairness. It measures whether the model's uncertainty over outcomes differs across intersectional identity tuples — not just the point prediction. This catches cases where the model is equally wrong across groups but more uncertain for some, which produces different downstream allocation behaviour.

### Mechanistic approaches · 机械论路径

2024-2025 年的可解释性工作让偏见可以被机械地干预：

- **性别神经元（Yu & Ananiadou 2025）。** 特定 MLP 神经元与性别化行为相关。消融这些神经元能在有限能力代价下降低性别差距指标。
- **用 SAE 揭示临床种族偏见（Ahsan & Wallace 2025）。** 稀疏自编码器（SAE）特征把内部表征分解为可解释维度；与种族相关的特征可以被识别并抑制。
- **UniBias（Zhou 等 2024）。** 用注意力头操纵做零样本去偏。特定注意力头会放大身份类别敏感度；把这些头清零或重新加权可以在不微调的情况下降低偏见。

> **Gender neurons (Yu & Ananiadou 2025).** Specific MLP neurons correlate with gender-specific behaviours. Ablating these neurons reduces gender-gap metrics with limited capability cost.
> **Clinical racial bias via SAEs (Ahsan & Wallace 2025).** Sparse autoencoder features decompose the internal representation into interpretable dimensions; race-correlated features can be identified and suppressed.
> **UniBias (Zhou et al. 2024).** Attention-head manipulation for zero-shot debiasing. Specific heads amplify identity-class sensitivity; zeroing or re-weighting these heads reduces bias with no fine-tuning.

### The meta-critique · 元层批评

这篇十年文献综述（arXiv:2508.11067，2025）发现该领域不成比例地聚焦二元性别偏见。其他轴——残障、宗教、移民身份、多语身份——得到的关注少得多。元层批评认为，狭窄的聚焦会以忽视的方式伤害边缘群体：一个在二元性别上去偏良好的模型，可能在没人检查过的维度上偏见严重。

> The 10-year literature review (arXiv:2508.11067, 2025) finds the field disproportionately focuses on binary-gender bias. Other axes — disability, religion, migration status, multi-lingual identity — receive far less attention. The meta-critique argues that narrow focus can harm marginalized groups by neglect: a model well-debiased on binary gender may be badly biased on dimensions nobody checked.

### Where this fits in Phase 18 · 在第 18 阶段中的位置

第 20-21 课正式覆盖偏见与公平。第 22 课覆盖隐私。第 23 课覆盖水印。它们是与前面欺骗/安全层互补的用户伤害层。

```figure
an-bias-two-harms
```

> Lessons 20-21 cover bias and fairness formally. Lesson 22 covers privacy. Lesson 23 covers watermarking. These are the user-harm layer complementing the earlier deception/safety layer.

## Use It · 实战用法

`code/main.py` 构建一个玩具级的基于嵌入的偏见探针：在一个简单的共现嵌入中测量身份词与属性词之间的 WEAT 式距离。你可以注入一个偏见并观察指标触发；再应用一个简单的去偏操作并观察部分恢复。

> `code/main.py` builds a toy embedding-based bias probe: measure WEAT-style distance between identity terms and attribute terms in a simple co-occurrence embedding. You can inject a bias and observe the metric fire; apply a simple debiasing operation and observe partial recovery.

## Ship It · 交付

本课产出 `outputs/skill-bias-eval.md`。给定一张模型卡或公平性声明，它沿三类指标（嵌入、概率、生成文本）审计评估、审计交叉性覆盖，并审计任何去偏干预的机制。

> This lesson produces `outputs/skill-bias-eval.md`. Given a model card or fairness claim, it audits the evaluation across the three metric categories (embedding, probability, generated-text), the intersectionality coverage, and the mechanism of any debiasing intervention.

## Exercises · 练习

1. 运行 `code/main.py`。报告去偏步骤前后的 WEAT 式偏见得分。解释为什么指标不会降到零。

2. 给探针增加一个交叉测试：(性别, 种族) x (职业, 家庭)。报告跨轴偏见得分。

3. 阅读 An 等 2025（PNAS Nexus）。指出他们报告的、单轴性别评估会漏掉的两个交叉效应。

4. Yu & Ananiadou 2025 识别出性别神经元。设计一个可证伪实验，区分「这些神经元导致性别偏见」与「这些神经元与性别偏见相关」。

5. 元层批评认为该领域过于聚焦二元性别。挑一个研究不足的轴，为它描述一套代表性伤害测量方案。

> 1. Run `code/main.py`. Report WEAT-style bias scores before and after the debiasing step. Explain why the metric does not drop to zero.
> 2. Extend the probe with an intersectional test: (gender, race) x (career, family). Report cross-axis bias scores.
> 3. Read An et al. 2025 (PNAS Nexus). Identify the two intersectional effects they report that single-axis gender evaluation would miss.
> 4. Yu & Ananiadou 2025 identify gender neurons. Sketch a falsification experiment that would distinguish "these neurons cause gender bias" from "these neurons correlate with gender bias."
> 5. The meta-critique argues the field focuses too narrowly on binary gender. Pick one under-studied axis and describe a representational-harm measurement protocol for it.

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|-----------------|------------------------|
| Representational harm | 「刻板印象/抹除」 | 对一个群体的偏见性描绘 |
| Allocational harm | 「不平等决策」 | 对一个群体的偏见性物质结果 |
| WEAT | 「嵌入测试」 | Word Embedding Association Test；基于共现的偏见探针 |
| Intersectionality | 「组合身份效应」 | 在多个身份轴交叉处涌现的偏见 |
| Gender neurons | 「MLP 偏见神经元」 | 激活与性别化行为相关的特定神经元 |
| SAE feature | 「可解释维度」 | 稀疏自编码器识别出的特征；可用于机械论偏见分析 |
| UniBias | 「注意力头去偏」 | 通过重新加权注意力头实现零样本去偏 |

## Further Reading · 延伸阅读

- [Gallegos et al. — Bias and Fairness in LLMs: A Survey (arXiv:2309.00770, Computational Linguistics 2024)](https://arxiv.org/abs/2309.00770) —— 权威综述
- [An et al. — Intersectional resume-evaluation bias (PNAS Nexus, March 2025)](https://academic.oup.com/pnasnexus/article/4/3/pgaf089/8111343) —— 五模型交叉研究
- [WinoIdentity — uncertainty-based intersectional fairness (arXiv:2508.07111, COLM 2025)](https://arxiv.org/abs/2508.07111) —— 新基准
- [UniBias — attention-head manipulation (Zhou et al. 2024, ACL)](https://arxiv.org/abs/2405.20612) —— 零样本去偏
