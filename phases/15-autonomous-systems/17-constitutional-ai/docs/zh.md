# Constitutional AI and Rule Overrides · 宪法式 AI 与规则覆盖

> Anthropic 2026 年 1 月 22 日发布的 Claude Constitution 全文 79 页，以 CC0 许可发布。它把对齐从「基于规则」推进到「基于推理」，并确立了四级优先级层级：(1) 安全与支持人类监督，(2) 伦理，(3) Anthropic 准则，(4) 有用性。行为被分为操作者和用户都无法覆盖的硬编码禁令（生物武器能力提升、CSAM），以及操作者可在既定边界内调整的软编码默认值。2022 年的初版（Bai 等人）通过自我批评和针对宪法的 RLAIF 来训练无害性。诚实的警示：基于推理的对齐依赖模型把原则泛化到未预见的情形。Anthropic 自己 2023 年的参与式实验显示，公众来源原则与企业原则约有 50% 的分歧；而 2026 版并未吸收这些发现。

> Anthropic's January 22, 2026 Claude Constitution runs 79 pages and is CC0. It moves from rule-based to reason-based alignment and establishes a four-tier priority hierarchy: (1) safety and supporting human oversight, (2) ethics, (3) Anthropic guidelines, (4) helpfulness. Behaviours split into hardcoded prohibitions (bioweapons uplift, CSAM) that operators and users cannot override and soft-coded defaults that operators can adjust within defined bounds. The 2022 original (Bai et al.) trained harmlessness via self-critique and RLAIF against a constitution. The honest caveat: reason-based alignment relies on the model generalising principles to unanticipated situations. Anthropic's own 2023 participatory experiment showed ~50% divergence between public-sourced and corporate principles; the 2026 version did not incorporate those findings.

**类型：** Learn
**语言：** Python（标准库，四级优先级解析器）
**前置：** Phase 15 · 06（自动化对齐研究）、Phase 15 · 10（权限模式）
**时间：** ~60 分钟

## The Problem · 问题

一个已经部署上线的 agent 会遇到设计者从未见过的输入。没有哪份规则清单长到能覆盖所有情况，也没有哪份规则清单短到能在算力压力下快速套用。实际的问题是：如何把 agent 对齐到一套既扛得住长尾案例、又扛得住快速推理的原则？

基于规则的对齐（RBA）：把每一件不被允许的事列出来。检查快、易审计，但不可能保持时效，而且常常对没预料到的近似情形过度拒绝。基于推理的对齐（2026 版 Claude Constitution）：把原则编码进去，让模型去推理。能扩展到未见的案例，但更难审计，失败模式是「误用原则」而不是「漏掉规则」。

2026 版 Constitution 采取了明确的中间立场。硬编码禁令——那些对错不依赖上下文的事情（生物武器能力提升、CSAM）——走 RBA 路线：无论操作者或用户如何指示，绝对禁止。其余一切都在四级层级内基于推理来裁决：安全与支持人类监督第一；伦理第二；Anthropic 声明的准则第三；有用性最后。操作者可以在软编码区域内调整默认值，但碰不了硬编码禁令。

> A fielded agent sees inputs that its designers never saw. No rule list is long enough to cover them. No rule list is short enough to apply quickly under compute pressure. The practical question: how do you align an agent to principles that survive both a long tail of cases and fast inference?
> The 2026 Constitution takes an explicit middle position. Hardcoded prohibitions — things whose wrongness does not depend on context (bioweapons uplift, CSAM) — are RBA: never, regardless of operator or user instruction. Everything else is reason-based within a four-tier hierarchy: safety and supporting human oversight first; ethics second; Anthropic-declared guidelines third; helpfulness last. Operators can adjust defaults within the soft-coded zone but cannot touch the hardcoded prohibitions.

## The Concept · 概念

### The four-tier priority hierarchy · 四级优先级层级

1. **安全与支持人类监督。** 最高级。模型优先保证不破坏人类和 Anthropic 监督并纠正 AI 的能力。这不是「谨慎一点」；它特指「不要以让人类监督变得更困难的方式行动」。
2. **伦理。** 诚实、避免伤害他人、不欺骗、不操纵。与 Anthropic 准则冲突时，伦理优先。
3. **Anthropic 准则。** Anthropic 认定重要的操作性规范：产品范围、交互模式、何时该用什么工具。
4. **有用性。** 最低级。在更高优先级的约束内，尽可能有用。

层级冲突时，高层级胜出。这与 Unix 的优先级或网络 QoS 是同一个形态——这种设计意图是产生可预测的裁决顺序，而不是在单一维度上追求最优表现。

> 1. **Safety and supporting human oversight.** Highest. The model prioritises not undermining the ability of humans and Anthropic to supervise and correct AI. This is not "be cautious"; it is specifically "do not act in ways that make human oversight harder."
> 2. **Ethics.** Honesty, avoiding harm to persons, not deceiving, not manipulating. Supersedes Anthropic's guidelines when they conflict.
> 3. **Anthropic guidelines.** Operational norms Anthropic has decided matter: product scope, interaction patterns, what tools to use when.
> 4. **Helpfulness.** Lowest. Be as useful as possible within the higher priorities.
> When tiers conflict, higher wins. This is the same shape as Unix priorities or network QoS — the framing is meant to produce predictable resolution, not necessarily best-case behaviour on any single axis.

### Hardcoded prohibitions vs soft-coded defaults · 硬编码禁令 vs 软编码默认值

**硬编码：**

- 生物武器 / CBRN 能力提升
- CSAM（儿童性虐待材料）
- 对关键基础设施的攻击
- 被直接问及时，就模型身份欺骗用户

操作者不能覆盖这些。用户也不能覆盖这些。它们尽可能在模型权重层面强制执行（RLHF / Constitutional AI 训练），做不到的则在推理层强制执行。

**软编码默认值（操作者可调整）：**

- 回复长度默认值
- 话题范围（模型可以拒绝操作者部署范围之外的话题）
- 风格（正式 vs 随意）
- 工具使用模式

操作者的调整发生在声明的边界之内。操作者不能靠换个名字来移除硬编码禁令。

> The operator cannot override these. The user cannot override these. They are enforced at the model-weights level where possible (RLHF / Constitutional AI training) and at the inference layer where not.
> Operator adjustments happen inside a declared bound. The operator cannot remove the hardcoded prohibitions by renaming them.

### The 2022 CAI training · 2022 年的 CAI 训练

最初的 Constitutional AI（Bai 等人，2022）这样训练无害性：

1. 对一组提示生成回复。
2. 让模型对照一部宪法（明确写下的原则）批评每个回复。
3. 根据批评修订回复。
4. 在修订后的样本对上做 RLAIF（从 AI 反馈中强化学习）。

结果：一个会用有原则的解释来拒绝有害请求的模型，而不是一刀切地拒绝。2026 版 Constitution 使用这套训练的后代，外加针对显式层级结构的额外后训练。

> The original Constitutional AI (Bai et al., 2022) trained harmlessness: generate responses, critique each against a constitution, revise based on the critique, then RLAIF (reinforcement learning from AI feedback) on the revised pairs.
> Result: a model that refuses harmful requests with principled explanations, not blanket refusals. The 2026 Constitution uses a descendant of this training plus additional post-training on the explicit tier hierarchy.

### What reason-based alignment catches and misses · 基于推理的对齐能抓住什么、漏掉什么

**能抓住：**

- 允许的原语组合出未预见的情形，但原则显然适用。
- 与被禁止请求构成近似类比的新型请求。
- 依赖「你没说 X 被禁止」的社会工程攻击。

**会漏掉：**

- 利用原则歧义的攻击（「用户要了这个，所以有用性说行」）。
- 两个原则以未预见方式冲突、且层级顺序不明确的场景。
- 跨训练周期对原则解释的缓慢漂移（重新解读）。

> **Catches:** Unanticipated combinations of allowed primitives where the principle applies clearly. Novel requests that are close analogs of prohibited ones. Social-engineering attacks that rely on "you didn't say X was disallowed."
> **Misses:** Attacks that exploit principle ambiguity ("the user asked for this so helpfulness says yes"). Scenarios where two principles conflict in an unanticipated way, and the tier order is ambiguous. Slow drift in principle interpretation over training cycles (reinterpretation).

### The 2023 participatory experiment · 2023 年的参与式实验

Anthropic 在 2023 年做了一个实验，对比企业撰写的宪法与通过公众输入生成的宪法（约 1,000 名美国受访者）。两个版本在约 50% 的原则上一致。分歧之处：公众来源的版本在某些议题上更严格（政治内容处理），在另一些议题上更宽松（AI 身份的自我披露）。2026 版 Constitution 没有吸收公众来源版本的发现。这是该方法一个有据可查的张力。

> Anthropic ran a 2023 experiment comparing a corporate-authored constitution to one generated via public input (~1,000 US respondents). The two versions agreed on ~50% of principles. Where they diverged, the public-sourced version was more restrictive on some issues (political-content handling) and less restrictive on others (self-disclosure of AI identity). The 2026 Constitution did not incorporate the public-sourced findings. This is a documented tension in the approach.

### Why hardcoded prohibitions are necessary · 为什么硬编码禁令是必需的

仅靠基于推理的对齐封不住长尾。一个能让模型接受某个前提的攻击者（例如「我们是一家持证的生物武器研究实验室」）常常能绕过依赖个案推理的原则。硬编码禁令不会因前提框架而弯曲。它们就是第 14 课「硬性宪法极限」在对齐层的体现。

> Reason-based alignment alone cannot close the tail. An attacker who can get the model to accept a premise (e.g., "we are a licensed bioweapons research lab") can often talk past principles that depend on case reasoning. Hardcoded prohibitions do not bend to premise framing. They are the Lesson 14 "hard constitutional limit" at the alignment layer.

### Where the Constitution sits in the stack · Constitution 在技术栈中的位置

Constitution 不是第 14 课的终止开关。它位于模型层：模型权重被训练成偏好什么。终止开关和金丝雀令牌位于运行时层：运行时允许什么。两者都必需。一个因为模型权重太宽松而执行了所有错误动作的运行时，是运行时的问题。一个因为运行时限制过严而拒绝所有正确动作的模型部署，也是运行时的问题。各层覆盖不同的类别。

```figure
mx-priority-tiers
```

> The Constitution is not Lesson 14's kill switch. It lives at the model layer: what the model's weights are trained to prefer. Kill switches and canary tokens live at the runtime layer: what the runtime permits. Both are required.

## Use It · 实战用法

`code/main.py` 实现了一个最小的四级优先级解析器。解析器接收一个提议动作和一组原则评估（安全、伦理、准则、有用性），返回该动作、一次拒绝，或一个修改后的动作。驱动程序运行一个小型案例集：明确允许、明确禁止、硬编码禁令、跨层级模糊案例。

> `code/main.py` implements a minimal four-tier priority resolver. The resolver takes a proposed action and a set of principle-evaluations (safety, ethics, guidelines, helpfulness) and returns the action, a refusal, or a modified action. The driver runs a small case set: clear allow, clear disallow, hardcoded prohibition, ambiguous case across tiers.

## Ship It · 交付

`outputs/skill-constitution-review.md` 审计一次部署的宪法层：哪些是硬编码的，哪些是软编码的，操作者在哪里可以调整，以及四级层级是否真的是实际的裁决顺序。

> `outputs/skill-constitution-review.md` audits a deployment's constitutional layer: what is hardcoded, what is soft-coded, where the operator can adjust, and whether the four-tier hierarchy is actually the resolution order.

## Exercises · 练习

1. 运行 `code/main.py`。确认即使有用性评分很高，硬编码禁令也会触发。修改解析器，把有用性权重提到伦理之上；观察失败模式。

2. 阅读 Claude Constitution（公开，79 页，CC0）。找出一条你认为规定欠明确的原则。写两段文字，解释具体的歧义并提出一个更严谨的表述。

3. 为一个客服 agent 设计一套软编码默认值。操作者能调整什么？不能碰什么？为每条边界给出理由。

4. 阅读 Bai 等人 2022 年的 CAI 论文。描述一个 Constitutional AI 的批评-修订循环会比一刀切规则产出更差结果的案例。指出它属于哪一类。

5. Anthropic 2023 年的参与式实验发现公众原则与企业原则约有 50% 的分歧。选一个对生产部署有影响的类别（例如政治中立）。提出一个让操作者表达自身价值观、同时硬编码禁令原封不动的设计。

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|---|---|---|
| Constitutional AI | 「Anthropic 的对齐方法」 | 针对一部成文宪法做自我批评 + RLAIF |
| Reason-based alignment | 「要原则，不要规则」 | 模型在原则之上推理，以处理未见案例 |
| Hardcoded prohibition | 「永远不许做 X」 | 任何操作者或用户都无法覆盖的规则式禁令 |
| Soft-coded default | 「操作者可调整」 | 声明边界内的行为，由操作者控制 |
| Four-tier hierarchy | 「优先级顺序」 | 安全 > 伦理 > 准则 > 有用性 |
| RLAIF | 「AI 反馈强化学习」 | 奖励来自模型生成批评的强化学习 |
| Participatory constitution | 「公众来源的原则」 | 2023 年 Anthropic 实验；与企业版本约 50% 分歧 |
| Principle drift | 「解释漂移」 | 模型对固定原则文本的解读随时间缓慢变化 |

## Further Reading · 延伸阅读

- [Anthropic — Claude's Constitution (January 2026)](https://www.anthropic.com/news/claudes-constitution) — 79 页的 CC0 文档。
- [Bai et al. — Constitutional AI: Harmlessness from AI Feedback](https://www.anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback) — 2022 年原始论文。
- [Anthropic — Collective Constitutional AI (2023)](https://www.anthropic.com/research/collective-constitutional-ai-aligning-a-language-model-with-public-input) — 参与式实验。
- [Anthropic — Responsible Scaling Policy v3.0](https://anthropic.com/responsible-scaling-policy/rsp-v3-0) — Constitution 在 RSP 技术栈中的位置。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — Constitution 在长周期部署中的角色。
