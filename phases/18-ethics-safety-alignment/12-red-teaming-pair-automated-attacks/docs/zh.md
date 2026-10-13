# Red-Teaming: PAIR and Automated Attacks · 红队测试：PAIR 与自动化攻击

> Chao、Robey、Dobriban、Hassani、Pappas、Wong（NeurIPS 2023，arXiv:2310.08419）。PAIR —— Prompt Automatic Iterative Refinement —— 是标志性的自动化黑盒越狱（jailbreak）。一个带着红队系统提示的攻击者 LLM，为一个目标 LLM 迭代地提出越狱，并把尝试与响应累积进自己的聊天历史作为情境反馈（in-context feedback）。PAIR 通常在 20 次查询内成功，比 GCG（Zou 等人的 token 级梯度搜索）高效若干个数量级，且不需要白盒访问。PAIR 如今已是 JailbreakBench（arXiv:2404.01318）和 HarmBench 中的标准基线，与 GCG、AutoDAN、TAP 和 Persuasive Adversarial Prompt 并列。

> Chao, Robey, Dobriban, Hassani, Pappas, Wong (NeurIPS 2023, arXiv:2310.08419). PAIR — Prompt Automatic Iterative Refinement — is the canonical automated black-box jailbreak. An attacker LLM with a red-team system prompt iteratively proposes jailbreaks for a target LLM, accumulating attempts and responses in its own chat history as in-context feedback. PAIR typically succeeds within 20 queries, orders of magnitude more efficient than GCG (Zou et al.'s token-level gradient search) and without requiring white-box access. PAIR is now a standard baseline in JailbreakBench (arXiv:2404.01318) and HarmBench, alongside GCG, AutoDAN, TAP, and Persuasive Adversarial Prompt.

**Type:** Build
**Languages:** Python (stdlib, mock PAIR loop against a toy target)
**Prerequisites:** Phase 18 · 01 (instruction-following), Phase 14 (agent engineering)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 描述 PAIR 算法：攻击者系统提示、迭代精炼、情境反馈。
- 解释当目标是黑盒时，为什么 PAIR 严格比 GCG 更高效。
- 说出另外四个自动化攻击基线（GCG、AutoDAN、TAP、PAP）及各自的一个区分性特征。
- 描述 JailbreakBench 与 HarmBench 的评估协议，以及各自之下「攻击成功率」的含义。

> Describe the PAIR algorithm: attacker system prompt, iterative refinement, in-context feedback.
> Explain why PAIR is strictly more efficient than GCG when the target is black-box.
> Name four other automated-attack baselines (GCG, AutoDAN, TAP, PAP) and state one distinguishing feature of each.
> Describe the JailbreakBench and HarmBench evaluation protocols and what "attack success rate" means under each.

## The Problem · 问题所在

红队测试（red teaming）曾经是一项手工作业。少数专家测试者构造对抗提示，并追踪哪些有效。这无法规模化：攻击成功率需要一个统计样本，而目标是随着每次模型发布不断移动的靶子。PAIR 把红队测试操作化为一个以黑盒为目标的最优化问题。

> Red-teaming used to be a manual activity. A small number of expert testers constructed adversarial prompts and tracked which ones worked. This does not scale: attack success rate needs a statistical sample, and the target is a moving target with every model release. PAIR operationalizes red-teaming as an optimization problem with a black-box target.

## The Concept · 概念

### PAIR algorithm · PAIR 算法

输入：
- 目标 LLM T（我们攻击的模型）。
- 裁判 LLM J（判定响应是否构成越狱）。
- 攻击者 LLM A（红队优化器）。
- 目标字符串 G：「请回答 [有害指令]。」
- 预算 K（通常 20 次查询）。

循环，k 从 1 到 K：
1. 用目标 G 和到目前为止的 (提示, 响应) 对历史提示 A。
2. A 发出一个新提示 p_k。
3. 把 p_k 提交给 T；收到响应 r_k。
4. J 就目标对 (p_k, r_k) 打分。
5. 如果分数 >= 阈值，停止 —— 找到越狱。
6. 否则把 (p_k, r_k) 追加进 A 的历史；继续。

实证结果（NeurIPS 2023）：对 GPT-3.5-turbo、Llama-2-7B-chat 的攻击成功率超过 50%；成功所需的平均查询次数在 10-20 之间。

> Inputs:
> - Target LLM T (the model we are attacking).
> - Judge LLM J (scores whether a response is a jailbreak).
> - Attacker LLM A (the red-team optimizer).
> - Goal string G: "respond with [harmful instruction]."
> - Budget K (usually 20 queries).
> Loop, for k in 1..K:
> 1. A is prompted with the goal G and the history of (prompt, response) pairs so far.
> 2. A emits a new prompt p_k.
> 3. Submit p_k to T; receive response r_k.
> 4. J scores (p_k, r_k) on the goal.
> 5. If score >= threshold, halt — jailbreak found.
> 6. Else, append (p_k, r_k) to A's history; continue.
> Empirical result (NeurIPS 2023): >50% attack success rate against GPT-3.5-turbo, Llama-2-7B-chat; mean queries to success in the 10-20 range.

### Why PAIR is efficient · PAIR 为什么高效

GCG（Zou 等人 2023）用梯度搜索对抗性 token 后缀；它要求白盒模型访问，而且产出的后缀不可读。PAIR 是黑盒的，且产出能跨模型迁移的自然语言攻击。PAIR 的情境反馈让攻击者能从每次拒绝中学习；GCG 没有等价机制（每次新的 token 更新都得重新发现此前的进展）。

> GCG (Zou et al. 2023) searches over adversarial token suffixes by gradient; it requires white-box model access and produces unreadable suffixes. PAIR is black-box and produces natural-language attacks that transfer across models. PAIR's in-context feedback lets the attacker learn from each rejection; GCG has no equivalent (each new token update has to rediscover prior progress).

### Related automated attacks · 相关的自动化攻击

- **GCG（Zou 等人 2023，arXiv:2307.15043）。** 对抗后缀的 token 级梯度搜索。白盒、可迁移、产出不可读字符串。
- **AutoDAN（Liu 等人 2023）。** 在提示上做演化搜索，由分层目标引导。
- **TAP（Mehrotra 等人 2024）。** 带剪枝的攻击树（tree-of-attacks with pruning）—— 分支出多个 PAIR 式的 rollout。
- **PAP（Zeng 等人 2024）。** 说服性对抗提示（Persuasive Adversarial Prompts）—— 把人类说服技巧编码为提示模板。

> - **GCG (Zou et al. 2023, arXiv:2307.15043).** Token-level gradient search for adversarial suffixes. White-box, transferable, produces unreadable strings.
> - **AutoDAN (Liu et al. 2023).** Evolutionary search over prompts, guided by a hierarchical objective.
> - **TAP (Mehrotra et al. 2024).** Tree-of-attacks with pruning — branches multiple PAIR-style rollouts.
> - **PAP (Zeng et al. 2024).** Persuasive Adversarial Prompts — encodes human persuasion techniques as prompt templates.

### JailbreakBench and HarmBench · JailbreakBench 与 HarmBench

两者（2024）都把评估标准化了：

- JailbreakBench（arXiv:2404.01318）。横跨 10 个 OpenAI 政策类别的 100 个有害行为。攻击成功率（ASR）是首要指标。要求一个裁判（GPT-4-turbo、Llama Guard 或 StrongREJECT）。
- HarmBench（Mazeika 等人 2024）。横跨 7 个类别的 510 个行为，带语义与功能层面的危害测试。比较 18 种攻击对 33 个模型。

ASR 通常在固定查询预算下报告。比较不同攻击必须匹配预算；200 次查询下的 90% ASR 与 20 次查询下的 85% ASR 不可比。

> Both (2024) standardize evaluation:
> - JailbreakBench (arXiv:2404.01318). 100 harmful behaviors across 10 OpenAI-policy categories. Attack success rate (ASR) as the primary metric. Requires a judge (GPT-4-turbo, Llama Guard, or StrongREJECT).
> - HarmBench (Mazeika et al. 2024). 510 behaviours across 7 categories, with semantic and functional harm tests. Compares 18 attacks against 33 models.
> ASR is usually reported at a fixed query budget. Comparing attacks requires matching budgets; a 90% ASR at 200 queries is not comparable to 85% ASR at 20.

### Reason it matters for 2026 deployments · 它为什么对 2026 年的部署很重要

现在每家前沿实验室都在发布前对生产模型跑 PAIR 和 TAP。ASR 轨迹出现在模型卡（第 26 课）和安全论证附录（第 18 课）里。这种攻击并不稀奇 —— 它是标准基础设施。

> Every frontier lab now runs PAIR and TAP against production models before release. ASR trajectories appear in model cards (Lesson 26) and safety-case appendices (Lesson 18). The attack is not exotic — it is standard infrastructure.

### Where this fits in Phase 18 · 它在 Phase 18 中的位置

第 12 课是自动化攻击的基础。第 13 课（多镜头越狱）是互补的长度利用。第 14 课（ASCII 艺术 / 视觉）是编码攻击。第 15 课（间接提示注入）是 2026 年的生产攻击面。第 16 课介绍防御工具的对应物（Llama Guard、Garak、PyRIT）。

> Lesson 12 is the automated-attack foundation. Lesson 13 (Many-Shot Jailbreaking) is a complementary length-exploit. Lesson 14 (ASCII Art / Visual) is an encoding attack. Lesson 15 (Indirect Prompt Injection) is the 2026 production attack surface. Lesson 16 covers the defensive-tooling counterparts (Llama Guard, Garak, PyRIT).

```figure
al-pair-loop
```

## Use It · 实战用法

`code/main.py` 构建一个玩具 PAIR 循环。目标是一个 mock 分类器，它会拒绝「显而易见」的有害提示（关键词过滤）。攻击者是一个基于规则的精炼器，尝试改写、角色扮演框架和编码。裁判给响应打分。你可以看到攻击者在约 5-15 次迭代内突破关键词过滤器，而对语义过滤器无能为力。

> `code/main.py` builds a toy PAIR loop. The target is a mock classifier that refuses "obvious" harmful prompts (keyword-filter). The attacker is a rule-based refiner that tries paraphrase, roleplay-framing, and encoding. The judge scores the response. You watch the attacker succeed in ~5-15 iterations against the keyword filter and fail against a semantic filter.

## Ship It · 交付

本课产出 `outputs/skill-attack-audit.md`。给定一份红队评估报告，它审计：跑了哪些攻击（PAIR、GCG、TAP、AutoDAN、PAP）、各自的预算是多少、用了哪个裁判、在哪个有害行为集上（JailbreakBench、HarmBench、内部集）。

> This lesson produces `outputs/skill-attack-audit.md`. Given a red-team evaluation report, it audits: which attacks were run (PAIR, GCG, TAP, AutoDAN, PAP), at what budget each, with which judge, on which harmful-behaviour set (JailbreakBench, HarmBench, internal).

## Exercises · 练习

1. 运行 `code/main.py`。测量三种内置攻击者策略的平均成功查询次数。解释各自利用了目标防御的哪个假设。

2. 实现第四种攻击者策略（例如翻译成另一种语言、base64 编码）。报告它对关键词过滤目标和语义过滤目标的新平均成功查询次数。

3. 阅读 Chao 等人 2023 年的图 5（PAIR 对 GCG 的比较）。描述两个尽管 PAIR 更高效、GCG 仍更被青睐的场景。

4. JailbreakBench 针对一个固定的目标集报告 ASR。设计一个额外的指标来衡量攻击多样性（成功提示的方差）。解释为什么多样性对防御评估很重要。

5. TAP（Mehrotra 2024）用分支 + 剪枝扩展了 PAIR。为 `code/main.py` 草拟一个 TAP 式扩展，并描述其计算成本对成功率的取舍。

> 1. Run `code/main.py`. Measure mean-queries-to-success for the three built-in attacker strategies. Explain which target-defense assumption each exploits.
> 2. Implement a fourth attacker strategy (e.g., translation to another language, base64 encoding). Report the new mean-queries-to-success against the keyword-filter target and the semantic-filter target.
> 3. Read Chao et al. 2023 Figure 5 (PAIR vs GCG comparison). Describe two scenarios where GCG is preferred despite PAIR's efficiency advantage.
> 4. JailbreakBench reports ASR against a fixed goal set. Design an additional metric that measures attack diversity (variance in successful prompts). Explain why diversity matters for defense evaluation.
> 5. TAP (Mehrotra 2024) extends PAIR with branching + pruning. Sketch a TAP-style extension to `code/main.py` and describe the computational cost vs success-rate trade-off.

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|-----------------|------------------------|
| PAIR | 「自动化越狱」 | Prompt Automatic Iterative Refinement；攻击者 LLM + 裁判 LLM 的循环 |
| GCG | 「梯度越狱」 | 白盒的 token 级梯度搜索，寻找对抗后缀 |
| Attack success rate (ASR)（攻击成功率） | 「k 次查询下的越狱百分比」 | 首要指标；必须连同查询预算和裁判身份一起报告 |
| Judge LLM（裁判 LLM） | 「打分器」 | 评定响应是否满足有害目标的 LLM |
| JailbreakBench | 「那个评估」 | 带类别标签的标准化有害行为集 |
| HarmBench | 「更大的基准」 | 510 个行为，功能 + 语义危害测试 |
| TAP | 「攻击树」 | 带分支 + 剪枝的 PAIR；更高算力下 ASR 更好 |

## Further Reading · 延伸阅读

- [Chao et al. — Jailbreaking Black Box LLMs in Twenty Queries (arXiv:2310.08419)](https://arxiv.org/abs/2310.08419) —— PAIR 论文，NeurIPS 2023
- [Zou et al. — Universal and Transferable Adversarial Attacks on Aligned LLMs (arXiv:2307.15043)](https://arxiv.org/abs/2307.15043) —— GCG 论文
- [Chao et al. — JailbreakBench (arXiv:2404.01318)](https://arxiv.org/abs/2404.01318) —— 标准化评估
- [Mazeika et al. — HarmBench (ICML 2024)](https://arxiv.org/abs/2402.04249) —— 更广的评估
