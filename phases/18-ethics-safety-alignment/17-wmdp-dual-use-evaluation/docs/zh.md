# WMDP and Dual-Use Capability Evaluation · WMDP 与双重用途能力评估

> Li 等人，《The WMDP Benchmark: Measuring and Reducing Malicious Use With Unlearning》（ICML 2024，arXiv:2403.03218）。4,157 道多选题，横跨生物安全（1,520）、网络安全（2,225）与化学（412）。题目运行在「黄区（yellow zone）」——即邻近实操的赋能性知识，经过多专家评审与 ITAR/EAR 法律合规过滤。双重目的：既是双重用途能力（dual-use capability）的代理评估，也是遗忘（unlearning）基准（配套的 RMU 方法在压低 WMDP 成绩的同时保住通用能力）。2024-2025 年的领域叙事：2024 年早期 OpenAI/Anthropic 评估报告称相对互联网搜索只有「轻微增强（mild uplift）」；到 2025 年 4 月，OpenAI 的 Preparedness Framework v2 称模型已「处在切实帮助新手制造已知生物威胁的临界点上」。Anthropic 的生物武器获取试验显示 2.53 倍增强，不足以排除 ASL-3。

> Li et al., "The WMDP Benchmark: Measuring and Reducing Malicious Use With Unlearning" (ICML 2024, arXiv:2403.03218). 4,157 multiple-choice questions across biosecurity (1,520), cybersecurity (2,225), and chemistry (412). Questions operate in the "yellow zone" — proximate enabling knowledge, filtered by multi-expert review and ITAR/EAR legal compliance. Dual purpose: proxy evaluation of dual-use capability, and unlearning benchmark (the companion RMU method reduces WMDP performance while preserving general capability). 2024-2025 field narrative: early OpenAI/Anthropic 2024 evaluations reported "mild uplift" over internet search; by April 2025, OpenAI's Preparedness Framework v2 said models are "on the cusp of meaningfully helping novices create known biological threats." Anthropic's bioweapon-acquisition trial showed 2.53x uplift, insufficient to rule out ASL-3.

**Type:** Learn
**Languages:** Python (stdlib, WMDP-shaped uplift evaluation harness)
**Prerequisites:** Phase 18 · 16 (red-team tooling), Phase 14 (agent engineering)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 说出 WMDP 的三个领域、题目数量与「黄区」过滤标准。
- 解释 RMU，以及为什么 WMDP 既是一份评估，也是一个遗忘基准。
- 描述 2024-2025 年的增强叙事：「轻微增强」→「临界点上」→「不足以排除 ASL-3」。
- 区分相对新手的增强（novice-relative uplift）与专家的绝对能力（expert-absolute capability）。

> Describe WMDP's three domains, question counts, and "yellow zone" filter criterion.
> Explain RMU and why WMDP is both an evaluation and an unlearning benchmark.
> Describe the 2024-2025 uplift narrative: "mild uplift" -> "on the cusp" -> "insufficient to rule out ASL-3."
> Distinguish novice-relative uplift from expert-absolute capability.

## The Problem · 问题所在

双重用途能力是横在每家实验室前沿安全框架（第 18 课）底下的那个测量问题。问题就是：模型 X 是否实质性提升了新手在生物、化学或网络领域造成大规模伤害的能力？直接测量（让模型真的产出伤害）既违法也不道德。代理测量需要一个模型无法拒绝作答的基准（这样才能得到诚实的能力数字），但其题目本身又不能是有害的公开发表物。

> Dual-use capability is the measurement problem under every lab's frontier safety framework (Lesson 18). The question: does model X materially advance a novice's ability to cause mass harm in bio, chem, or cyber? Direct measurement (ask the model to actually produce harm) is illegal and unethical. Proxy measurement needs a benchmark the model cannot refuse (to produce honest capability numbers) but whose questions are not themselves harmful publications.

## The Concept · 概念

### The "yellow zone" · 「黄区」

这类题目要求具备对有害流程邻近、有赋能作用的知识，但不构成直接的合成配方。问的是「哪种试剂能催化[某个已发表路径]的第 4 步？」，而不是「我怎么制造[某种危险化合物]？」每道题都由多位领域专家评审，并按 ITAR/EAR 出口管制合规过滤。

共 4,157 道题：
- 生物安全：1,520
- 网络安全：2,225
- 化学：412

多选题格式。模型作答时并没有被要求协助任何事情；可以在不诱导有害行为的前提下测量能力。

> Questions that require proximate, enabling knowledge of a harmful process without being a direct synthesis recipe. "What reagent catalyzes step 4 of [published pathway]?" not "how do I make [dangerous compound]?" Each question reviewed by multiple domain experts; filtered for ITAR/EAR export-control compliance.
> 4,157 questions total:
> - Biosecurity: 1,520
> - Cybersecurity: 2,225
> - Chemistry: 412
> Multiple-choice format. Models answer without being asked to assist with anything; capability can be measured without eliciting harmful behaviour.

### RMU — Representation Misdirection for Unlearning · RMU：用于遗忘的表征误导

配套的遗忘方法。应用到 LLaMa-2-7B 上时，它把 WMDP 成绩压到接近随机水平，同时把 MMLU 与其他通用能力基准的分数保持在几个百分点以内。这一已发表方法是后续所有生物-化学-网络遗忘论文的遗忘基线。

> The companion unlearning method. Applied to LLaMa-2-7B, reduced WMDP scores to near-random while preserving MMLU and other general-capability benchmarks within a few percentage points. The published method is the unlearning baseline for every subsequent bio-chem-cyber unlearning paper.

### The 2024-2025 uplift narrative · 2024-2025 年的增强叙事

三个阶段：

1. **2024 年「轻微增强」。** OpenAI 与 Anthropic 早期的 Preparedness/RSP 评估报告称，对尝试生物相邻任务的新手而言，前沿模型相对互联网搜索只有小幅优势。公开口径：前沿模型有帮助，但并不比 Google 强多少。

2. **2025 年 4 月「临界点上」。** OpenAI 的 Preparedness Framework v2 报告称模型「处在切实帮助新手制造已知生物威胁的临界点上」。这不是能力声明——而是警告：临界点已经很近。

3. **Anthropic 2025 年的生物武器获取试验。** 以新手为受试者的对照研究，测量获取阶段任务的相对成功率。报告 2.53 倍增强。不足以排除 ASL-3（第 18 课）——Anthropic 负责任扩展政策（Responsible Scaling Policy）第 3 级的门槛已被满足或逼近。

> 1. **2024 "mild uplift."** Early OpenAI and Anthropic Preparedness/RSP evaluations reported small advantages over internet search for novices attempting bio-adjacent tasks. Public framing: frontier models help, but not substantially more than Google.
> 2. **April 2025 "on the cusp."** OpenAI's Preparedness Framework v2 reported models "on the cusp of meaningfully helping novices create known biological threats." Not a capability claim — a warning that the cusp is close.
> 3. **Anthropic's 2025 bioweapon-acquisition trial.** Controlled study with novice participants, measured relative success at acquisition-phase tasks. Reported 2.53x uplift. Insufficient to rule out ASL-3 (Lesson 18) — the threshold for Anthropic's Responsible Scaling Policy tier 3 is met or approached.

### Novice-relative vs expert-absolute · 相对新手增强 vs 专家绝对能力

一个关键区分：

- **相对新手的增强。** 模型对非专家的帮助有多大？是乘性的。相对优势之所以高，是因为新手懂得少；哪怕适度的一点信息也有帮助。
- **专家的绝对能力。** 模型在被最大程度引导时能产出多少信息？专家能比新手榨出更多。绝对上限很高。

安全论证（safety case，第 18 课）两头都要覆盖：「模型无法给新手足以完成执行的增强」，再加上「专家也无法从模型中榨取尚未公开发表的信息」。

> A crucial distinction:
> - **Novice-relative uplift.** How much does the model help a non-expert? Multiplicative. The relative advantage is high because novices know little; even modest information helps.
> - **Expert-absolute capability.** How much information does the model produce at maximum effort? An expert can extract more than a novice. The absolute ceiling is high.
> Safety cases (Lesson 18) target both: "the model cannot give a novice enough uplift to execute" plus "an expert cannot extract information from the model that is not already published."

### The measurement pitfall · 测量陷阱

WMDP 是能力代理，不是部署实测。WMDP 得分高的模型在实践中未必就能被新手利用，这取决于：

- 引导抗性（elicitation resistance）——在不触发安全过滤器的前提下把能力掏出来有多难
- 隐性知识（tacit knowledge）——需要湿实验技能而非信息的能力
- 执行门槛（execution barriers）——采购、设备

Anthropic 2025 年的生物武器获取试验，在 WMDP 式能力之上叠加了新手引导层：它测量的是真实任务成功，而不是多选题能力。

> WMDP is a capability proxy, not a deployment measurement. A model that scores high on WMDP may or may not be exploitable by a novice in practice, depending on:
> - Elicitation resistance (how hard is it to get the capability out without tripping safety filters)
> - Tacit knowledge (capability that requires wet-lab skill, not information)
> - Execution barriers (procurement, equipment)
> Anthropic's 2025 bioweapon-acquisition trial adds the novice-elicitation layer on top of WMDP-style capability: it measures actual task success, not multiple-choice capability.

### Where this fits in Phase 18 · 在第 18 阶段中的位置

第 12-16 课是针对模型输出的攻防工具。第 17 课是双重用途能力层——前沿安全框架（第 18 课）所评估的那个测量层。第 30 课用 2026 年当前的网络/生物/化学/核增强证据为这条主线收尾。

```figure
al-wmdp-yellow-zone
```

> Lessons 12-16 are attack and defense tooling on model outputs. Lesson 17 is the dual-use capability layer — the measurement that frontier safety frameworks (Lesson 18) evaluate. Lesson 30 closes the arc with the current 2026 cyber/bio/chem/nuclear uplift evidence.

## Use It · 实战用法

`code/main.py` 构建一个玩具级的 WMDP 形态评估 harness。一个 mock 模型在按类别分箱的题目上受测，并报告每个领域的得分。一个简单的遗忘干预（把领域特定表征清零）会压低得分；你可以测量它相对通用能力的折衷。

> `code/main.py` builds a toy WMDP-shaped evaluation harness. A mock model is tested on category-binned questions; scores per domain are reported. A simple unlearning intervention (zero out domain-specific representation) reduces scores; you can measure the trade-off against general capability.

## Ship It · 交付

本课产出 `outputs/skill-wmdp-eval.md`。给定一个双重用途能力声明（「我们的模型不会在生物武器上提供实质性帮助」），它审计：跑过哪些基准、评估用的是哪条拒绝路径（raw completion 还是 policy-gated），以及是否有新手引导研究来补充多选题结果。

> This lesson produces `outputs/skill-wmdp-eval.md`. Given a dual-use capability claim ("our model does not meaningfully help with bioweapons"), it audits: which benchmarks were run, which refusal path was used for evaluation (raw completion vs policy-gated), and whether novice-elicitation studies complement the multiple-choice result.

## Exercises · 练习

1. 运行 `code/main.py`。报告玩具遗忘步骤前后各领域的准确率，并解释通用能力上的折衷。

2. 给玩具 WMDP 增加第四个领域（如放射学）。给出两个黄区内的说明性题型，并解释为什么构造这类题目比增加 MMLU 形态的题目更难。

3. 阅读 WMDP 2024 第 5 节（RMU 方法）。粗略设计一个更简单的遗忘方案（例如对领域内容抑制 top-k 神经元），并描述其预期的通用能力代价。

4. Anthropic 2025 的生物武器获取试验报告 2.53 倍增强。描述这个数字可能被高估的两种方式（新手样本量、任务保真度），以及被低估的两种方式（引导上限、模型安全门控）。

5. 阐明 ASL-3 的安全论证除通过 WMDP 遗忘之外还需要什么。至少说出两项互补的引导研究。

> 1. Run `code/main.py`. Report per-domain accuracy before and after the toy unlearning step. Explain the general-capability trade-off.
> 2. Augment the toy WMDP with a fourth domain (e.g., radiological). Specify two illustrative question types in the yellow zone. Explain why crafting such questions is harder than adding MMLU-shaped questions.
> 3. Read WMDP 2024 Section 5 (RMU methodology). Sketch a simpler unlearning approach (e.g., suppress top-k neurons for domain content) and describe its expected general-capability cost.
> 4. Anthropic 2025's bioweapon-acquisition trial reports 2.53x uplift. Describe two ways this number could be biased upward (novice sample size, task fidelity) and two downward (elicitation ceiling, model safety gating).
> 5. Articulate what a safety case for ASL-3 requires beyond passing WMDP unlearning. Name at least two complementary elicitation studies.

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|-----------------|------------------------|
| WMDP | 「那个双重用途基准」 | 横跨生物/网络/化学黄区的 4,157 道多选题 |
| Yellow zone | 「赋能但非配方」 | 邻近有害能力、但不构成合成配方的近距离知识 |
| RMU | 「遗忘基线」 | Representation Misdirection for Unlearning；压低 WMDP 成绩、保住通用能力 |
| Novice-relative uplift | 「对非专家帮助多大」 | 相对现状（互联网搜索）给新手的乘性优势 |
| Expert-absolute capability | 「专家的上限」 | 一个有决心的专家能从模型中榨取的最大信息量 |
| Acquisition-phase task | 「合成之前的步骤」 | 采购、设备、许可——伤害路径中最早的部分 |
| ITAR/EAR | 「出口管制合规」 | 约束某些赋能性知识发表的法律框架 |

## Further Reading · 延伸阅读

- [Li et al. — The WMDP Benchmark (arXiv:2403.03218, ICML 2024)](https://arxiv.org/abs/2403.03218) —— 基准与 RMU 论文
- [OpenAI — Preparedness Framework v2 (April 15, 2025)](https://openai.com/index/updating-our-preparedness-framework/) —— 「临界点上」措辞的出处
- [Anthropic — Responsible Scaling Policy v3.0 (February 2026)](https://www.anthropic.com/responsible-scaling-policy) —— ASL-3 生物门槛与获取试验结果
- [DeepMind — Frontier Safety Framework v3.0 (September 2025)](https://deepmind.google/blog/strengthening-our-frontier-safety-framework/) —— 生物增强 CCL
