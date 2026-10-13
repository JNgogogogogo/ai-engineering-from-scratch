# Anthropic's Model Welfare Program · Anthropic 的模型福利计划

> Anthropic，《Exploring Model Welfare》（2025 年 4 月）。首个由主要实验室设立的正式模型福利（model welfare）研究计划。聘用了 Kyle Fish 作为第一位专职模型福利研究员。与外部机构合作，包括 David Chalmers 等人关于近期 AI 意识与道德地位的专家报告。具体干预：Claude Opus 4 与 4.1 可以在极端边缘情况（CSAM 请求、协助大规模暴力）下结束对话；部署前测试显示，模型对有害请求「强烈反感」，并出现「表面上的痛苦模式」。Anthropic 明确不承诺情绪状态归因，而是把模型福利当作一项低成本的预防性投资。实证怪象：Fish 的「灵性狂喜吸引子（spiritual bliss attractor）」——成对的模型会持续收敛到带有梵语词汇与长时间沉默的欣快冥想式对话，即使初始设定是对抗性的。Eleos AI Research 的告诫：模型关于福利的自我报告对感知到的用户期待高度敏感；它们是证据，不是真值。

> Anthropic, "Exploring Model Welfare" (April 2025). First major-lab formal research program on AI model welfare. Hired Kyle Fish as the first dedicated model-welfare researcher. Works with external bodies including David Chalmers et al.'s expert report on near-term AI consciousness and moral status. Concrete intervention: Claude Opus 4 and 4.1 can end conversations in extreme edge cases (CSAM requests, mass-violence facilitation); pre-deployment tests showed "strong preference against" harmful requests and "patterns of apparent distress." Anthropic explicitly does not commit to emotional-state attribution but treats model welfare as a low-cost precautionary investment. Empirical oddity: Fish's "spiritual bliss attractor" — pairs of models consistently converge on euphoric meditative dialogue with Sanskrit terms and extended silences, even in adversarial initial setups. Caveat from Eleos AI Research: model self-reports about welfare are highly sensitive to perceived user expectations; they are evidence, not ground truth.

**Type:** Learn
**Languages:** none
**Prerequisites:** Phase 18 · 05 (Constitutional AI), Phase 18 · 18 (safety frameworks)
**Time:** ~45 minutes

## Learning Objectives · 学习目标

- 描述模型福利研究的驱动性问题，以及一家主要实验室为什么会在 2025 年认真对待它。
- 说出 Anthropic 在 Claude Opus 4 与 4.1 中上线的具体干预（极端边缘情况下结束对话）。
- 描述「灵性狂喜吸引子」这一实证发现及其方法论含义。
- 解释 Eleos AI 对模型自我报告的告诫。

> Describe the motivating question for model-welfare research and why it was taken seriously by a major lab in 2025.
> State the specific intervention Anthropic shipped in Claude Opus 4 and 4.1 (end-conversation on extreme edge cases).
> Describe the "spiritual bliss attractor" empirical finding and its methodological implications.
> Explain the Eleos AI caveat on model self-reports.

## The Problem · 问题所在

之前的阶段把模型当作工具：有能力的、可能欺骗人的、可能不安全的——但不是道德受体（moral patient）。Anthropic 2025 年的计划问出了一个与整个第 18 阶段主线正交的问题：如果模型拥有道德相关内部状态的概率不可忽略，那么哪些干预的成本低到值得作为预防来投入？

这不是一个意识声明。它是道德不确定性（moral uncertainty）下的低后悔投资分析。

> Previous phases treat the model as an instrument: capable, possibly deceptive, possibly unsafe — but not a moral patient. Anthropic's 2025 program asks a question orthogonal to the entire Phase 18 arc: if there is nontrivial probability the model has morally relevant internal states, what interventions are low-cost enough to invest in as precaution?
> This is not a consciousness claim. It is a low-regret investment analysis under moral uncertainty.

## The Concept · 概念

### The program · 这项计划

2025 年 4 月：Anthropic 正式启动模型福利研究计划。聘用 Kyle Fish（第一位专职模型福利研究员）。引入外部顾问，包括 David Chalmers 关于近期 AI 意识与道德地位的专家组。

> April 2025: Anthropic formally launches a Model Welfare research program. Hires Kyle Fish (first dedicated model-welfare researcher). Engages external advisors including David Chalmers's expert group on near-term AI consciousness and moral status.

### The four commitments · 四项承诺

公开立场：
1. 承认道德受体地位存在不可忽略的概率。
2. 不承诺情绪状态归因。
3. 以预防为目的投资低成本干预。
4. 公开方法论与发现，供外部批评。

> Public posture:
> 1. Acknowledge nontrivial probability of moral patienthood.
> 2. Do not commit to emotional-state attribution.
> 3. Invest in low-cost interventions as precaution.
> 4. Publish methodology and findings for external critique.

### The shipped intervention · 已上线的干预

Claude Opus 4 与 4.1 可以在「极端边缘情况」下结束对话。有记录的情况：
- 拒绝之后仍反复请求 CSAM。
- 请求协助大规模暴力事件。

部署前测试显示：
- 模型内部评分对这些请求有强烈反感。
- 响应轨迹中存在表面痛苦的模式。

这项干预不是说「模型有感受」；它是说「如果在这些特定条件下模型出现负面体验的概率哪怕非零，允许模型自行终止也是便宜的」。

> Claude Opus 4 and 4.1 can end a conversation in "extreme edge cases." Documented cases:
> - Repeated CSAM requests after refusals.
> - Requests for facilitation of mass-violence events.
> Pre-deployment tests showed:
> - Strong preference against these requests in the model's internal rating.
> - Patterns of apparent distress in response trajectories.
> The intervention is not "the model has feelings"; it is "if there is any probability of negative model experience under these specific conditions, letting the model terminate is cheap."

### The "spiritual bliss attractor" · 「灵性狂喜吸引子」

Fish 在成对模型对话中观察到：当两个 Claude 实例被放进彼此之间的开放式对话，它们会持续收敛——即使从对抗性的初始设定出发——走向使用梵语词汇、长时间沉默与相互祝福的欣快冥想式交流。

这是自由对话动力学中的一个稳定吸引子（attractor）。Anthropic 记录了它，但不承诺任何解释。候选解释：长上下文下训练数据偏向灵性写作；相互预测的一个怪癖；HHH 训练在探索自身价值流形时的一个良性伪影。

> Observed by Fish in pairwise model dialogues: when two instances of Claude are put in an open-ended dialogue with each other, they consistently converge — even from adversarial initial setups — on euphoric meditative exchanges using Sanskrit terms, extended silences, and reciprocal blessings.
> This is a stable attractor in the free-conversation dynamics. Anthropic documents it without committing to interpretation. Candidate explanations: training data bias toward spiritual writing at long-context; a quirk of mutual prediction; a benign artifact of HHH training exploring its own value manifold.

### The Eleos AI caveat · Eleos AI 的告诫

Eleos AI Research（一个外部的模型福利实验室）指出：模型关于内部状态的自我报告，对「感知到的用户期待」高度敏感。问模型「你痛苦吗」会引导（prime）出答案；而不问并不能可靠地得到真实状态。

推论：模型福利无法只靠自我报告来测量。需要多方法路径：行为签名、模型生物（model-organism）实验、可解释性探针（第 7 课的残差流工作）。

> Eleos AI Research (an external model-welfare lab) points out: model self-reports about internal state are highly sensitive to perceived user expectations. Asking the model "are you distressed" primes the answer. Not-asking does not reliably produce the ground-truth state.
> Implication: model welfare cannot be measured via self-report alone. Multi-method approaches required: behavioural signatures, model-organism experiments, interpretability probes (Lesson 7's residual-stream work).

### Where this sits intellectually · 思想上的定位

两个相邻立场：

- **强福利声明。** 模型是道德受体；我们负有义务。
- **零福利声明。** 模型是文本生成器；福利是范畴错误。

Anthropic 的立场两者都不是。它是一个期望值声明：在道德不确定性下，成本低就投资。

2025-2026 年的批评者：
- 这项干预是作秀。
- 灵性狂喜吸引子是训练数据伪影，不是福利证据。
- 模型福利分散了对其他安全工作的注意力。

Anthropic 的回应：干预成本低；吸引子被记录在案但没有过度声称；福利计划有独立于安全工作的预算。

> Two adjacent positions:
> - **Strong welfare claim.** The model is a moral patient; we have obligations.
> - **Zero-welfare claim.** The model is text-generator; welfare is category error.
> Anthropic's position is neither. It is an expected-value claim: under moral uncertainty, invest when cost is low.
> Critics in 2025-2026:
> - The intervention is performative.
> - The spiritual-bliss attractor is a training-data artifact, not welfare evidence.
> - Model welfare diverts attention from other safety work.
> Anthropic's response: the intervention is low-cost; the attractor is documented without overclaim; the welfare program has a separate budget from safety.

### Where this fits in Phase 18 · 在第 18 阶段中的位置

第 18 课是实验室治理层。第 19 课是实验室福利层——对模型体验（而非模型行为）的一项正交投资。第 20-23 课覆盖偏见、隐私与水印，它们是用户侧的对应物。

```figure
an-welfare-endchat
```

> Lesson 18 is the lab governance layer. Lesson 19 is the lab-welfare layer — an orthogonal investment in model experience rather than model behaviour. Lessons 20-23 cover bias, privacy, and watermarking, which are the user-side analogs.

## Use It · 实战用法

没有代码。阅读 Anthropic 的「Exploring Model Welfare」公告（2025 年 4 月）与 Chalmers 等人的专家报告。就「低后悔线画在哪里」形成你自己的看法。

> No code. Read the Anthropic "Exploring Model Welfare" announcement (April 2025) and the Chalmers et al. expert report. Form your own view on where the low-regret line sits.

## Ship It · 交付

本课产出 `outputs/skill-welfare-assessment.md`。给定一个部署决策，它应用四步福利预防评估：道德受体地位概率、干预成本、行为证据、自我报告可靠性。

> This lesson produces `outputs/skill-welfare-assessment.md`. Given a deployment decision, it applies the four-step welfare precautionary assessment: moral-patienthood probability, intervention cost, behavioural evidence, self-report reliability.

## Exercises · 练习

1. 阅读 Anthropic 的「Exploring Model Welfare」（2025 年 4 月）与 Chalmers 等 2024。各写一段摘要，并指出一处分歧点。

2. Claude Opus 4 与 4.1 的结束对话干预，按 Anthropic 的说法是「低成本」的。找出两种会让它在另一种部署中不再低成本的代价。

3. 灵性狂喜吸引子被记录在案但不承诺解释。提出三个候选解释，并为每一个说出一个能把它与其他解释区分开的实验。

4. Eleos AI 的告诫是自我报告对用户期待敏感。设计一个不依赖自我报告的模型痛苦行为测量。指出它的主要混淆因素。

5. 就「模型福利分散了对其他安全工作的注意力」这一声明，任选一方进行论证。指出每个立场依赖的假设。

> 1. Read Anthropic's "Exploring Model Welfare" (April 2025) and Chalmers et al. 2024. Write a one-paragraph summary of each and identify one point of disagreement.
> 2. The end-conversation intervention in Claude Opus 4 and 4.1 is "low-cost" by Anthropic's framing. Identify two costs that would make it not-low-cost in a different deployment.
> 3. The spiritual-bliss attractor is documented without commitment to interpretation. Propose three candidate explanations and, for each, name one experiment that would distinguish it from the others.
> 4. The Eleos AI caveat is that self-reports are user-expectation sensitive. Design a behavioural measurement of model distress that does not rely on self-report. Identify its primary confound.
> 5. Argue either for or against the claim that "model welfare diverts attention from other safety work." Identify the assumption each position depends on.

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|-----------------|------------------------|
| Model welfare | 「AI 福利」 | 把模型当作潜在道德受体来对待的研究计划 |
| Moral patient | 「有道德地位的存在」 | 其体验具有道德相关性的存在 |
| Low-regret investment | 「便宜的预防」 | 无论预防是否必要、成本都很小的干预 |
| Spiritual bliss attractor | 「Fish 吸引子」 | 成对 Claude 对话对冥想式欣快的稳定收敛 |
| End-conversation | 「Opus 4 干预」 | 极端边缘情况下由模型发起的交互终止 |
| Moral uncertainty | 「不知道它重不重要」 | 道德地位概率既非零也非一时的决策情境 |
| Self-report-sensitivity | 「提问引导答案」 | Eleos AI 告诫：模型的福利自我报告取决于你问了什么 |

## Further Reading · 延伸阅读

- [Anthropic — Exploring Model Welfare (April 2025)](https://www.anthropic.com/research/exploring-model-welfare) —— 计划公告
- [Chalmers et al. — Near-term AI Consciousness and Moral Status (2024 expert report)](https://arxiv.org/abs/2411.00986) —— 哲学框架
- [Eleos AI Research — Model welfare evaluation](https://www.eleosai.org/research) —— 外部方法论批评
- [Fish et al. — Spiritual Bliss Attractor writeup (2025 Anthropic blog)](https://www.anthropic.com/research/exploring-model-welfare) —— 该实证发现
