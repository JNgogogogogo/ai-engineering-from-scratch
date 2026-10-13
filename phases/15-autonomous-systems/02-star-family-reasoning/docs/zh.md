# STaR, V-STaR, Quiet-STaR — Self-Taught Reasoning · STaR、V-STaR、Quiet-STaR——自我教学的推理

> 最小的自我改进循环就藏在 rationale（推理依据）里。模型生成一条思维链，保留那些最终落在正确答案上的，再用它们做微调。这就是 STaR。V-STaR 加了一个验证器（verifier），让推理时的选择更靠谱。Quiet-STaR 把 rationale 下推到每一个 token。三者都有效，但都不神奇——这个循环会原样保留任何「碰巧到达正确答案」的捷径。

> The smallest possible self-improvement loop sits inside the rationale. A model generates a chain of thought, keeps the ones that land on correct answers, and fine-tunes on those. That is STaR. V-STaR adds a verifier so inference-time selection is better. Quiet-STaR pushes the rationale down to every token. All three work. None of them are magic — the loop preserves any shortcut that happened to reach the right answer.

**类型：** Learn（学习）
**语言：** Python（仅 stdlib，bootstrap-loop 模拟器）
**先修：** Phase 13 · 01-03（Reasoning and CoT）、Phase 15 · 01（long-horizon framing）
**时间：** ~60 分钟

## The Problem · 问题在哪

教模型推理的最直接办法，是收集人类撰写的推理轨迹。这很贵、很慢，而且上限取决于人类愿意写多少高质量思维链。

STaR（Self-Taught Reasoner，Zelikman 等，2022）问：如果让模型自己写 rationale，再拿已知答案给它打分呢？循环是：

1. 采样一条推理轨迹加一个答案。
2. 如果最终答案正确，保留这条轨迹。
3. 在保留的轨迹上微调。
4. 重复。

它确实有效。GSM8K 和 CommonsenseQA 都在没有任何新人工标注的情况下提升了。但这个循环有一个内置偏差：任何产出了正确答案的 rationale 都会被保留，不管推理过程本身是否可靠。V-STaR（Hosseini 等，2024）用学习到的验证器修补了这一点；Quiet-STaR（Zelikman 等，2024）把这个想法推广到逐 token 的内部 rationale。

> The straightforward way to teach a model to reason is to collect human-written reasoning traces. That is expensive, slow, and bounded by how much high-quality chain-of-thought humans are willing to write.
> STaR (Self-Taught Reasoner, Zelikman et al., 2022) asks: what if the model writes its own rationales and grades them against known answers?
> But the loop has a built-in bias: any rationale that produced the right answer is retained, regardless of whether the reasoning itself was sound. V-STaR (Hosseini et al., 2024) patches this with a learned verifier; Quiet-STaR (Zelikman et al., 2024) generalizes the idea to per-token internal rationales.

## The Concept · 概念

### STaR: bootstrap on what worked · STaR：在有效的样本上自举

从一个具备微弱推理能力的基础模型出发。对每道训练题，采样一条 rationale 加答案。如果答案与标签一致，保留 (problem, rationale, answer) 三元组。在保留的数据集上微调模型。重复。

有一个关键变化。如果模型在某道题上永远做不对，循环就无法从它身上学到东西。STaR 引入了 **rationalization**（合理化）：对模型失败的题，把正确答案作为提示注入，重新提示模型产出一个能导向该答案的 rationale。rationalize 出来的 rationale 也会加入训练集。

原论文的结果（Zelikman 等，2022）：一个 GPT-J 基础模型经过带 rationalization 的多轮 STaR，在 GSM8K 上从 5.8% 提升到 10.7%——约 5 个百分点的绝对提升。在 CommonsenseQA 上，STaR 训练的 GPT-J 6B 达到 72.5%，与微调过的 GPT-3 175B（约 73%）相当——后者是大约 30 倍大、用人工标注 rationale 训练的模型。

> Start from a base model with some weak reasoning ability. On each training problem, sample a rationale plus answer. If the answer matches the label, keep the (problem, rationale, answer) triple. Fine-tune the model on the kept set. Repeat.
> STaR adds **rationalization**: for problems the model fails, inject the correct answer as a hint and re-prompt the model to produce a rationale that leads to it.
> Result in the original paper (Zelikman et al., 2022): a GPT-J base model improved on GSM8K from 5.8% to 10.7% through repeated STaR rounds with rationalization — about 5 percentage points absolute. On CommonsenseQA, STaR-trained GPT-J 6B reached 72.5%, comparable to a fine-tuned GPT-3 175B (~73%) — a roughly 30x larger model trained on hand-annotated rationales.

### V-STaR: train a verifier with DPO · V-STaR：用 DPO 训练一个验证器

STaR 把错误的 rationale 扔掉了。Hosseini 等（2024）观察到这些也是数据：每一对 (rationale, 「它对不对」) 都能用来训练一个验证器。他们用 Direct Preference Optimization 在正确与错误两类解法上训练出一个排序器。推理时，采样 N 条 rationale，选验证器排名第一的那个。

报告的提升：在 GSM8K 和 MATH 上比此前的自我改进基线高 4 到 17 个百分点，其中大部分收益来自把验证器用于推理时选择，而不是用于额外的生成器微调。

> STaR throws away incorrect rationales. Hosseini et al. (2024) observed those are also data: every pair of (rationale, "is this correct") can train a verifier. They use Direct Preference Optimization over both correct and incorrect solutions to build a ranker. At inference time, sample N rationales and pick the verifier's top choice.
> Reported delta: +4 to +17 percentage points over prior self-improvement baselines on GSM8K and MATH, with most of the gain coming from using the verifier for inference-time selection rather than for additional generator fine-tuning.

### Quiet-STaR: per-token internal rationales · Quiet-STaR：逐 token 的内部 rationale

Zelikman 等（2024）问：如果模型学会在每个 token 位置都生成一条简短的内部 rationale，而不只是在问题和答案之间呢？Quiet-STaR 训练模型在每个待预测 token 之前先发出一个隐藏的「想法」（thought），然后通过一个学习到的权重，把「带着想法的预测」与基线预测混合起来。

结果：Mistral 7B 在不做任务特定微调的情况下，GSM8K 零样本从 5.9% 提升到 10.9%，CommonsenseQA 从 36.3% 提升到 47.2%（均为绝对提升）。模型学会了「何时思考」——难 token 得到更长的内部 rationale，简单 token 几乎没有。

> Quiet-STaR trains a model to emit a hidden "thought" before each predicted token, then mixes the thought-aware prediction with the baseline prediction via a learned weight.
> Result: Mistral 7B gained absolute zero-shot improvements on GSM8K from 5.9% to 10.9% and CommonsenseQA from 36.3% to 47.2% without task-specific fine-tuning. The model learned "when to think" — hard tokens get longer internal rationales; easy ones get almost none.

### Why all three share a safety concern · 为什么三者共有一个安全隐患

三种方法都用最终答案作为梯度信号。一条靠有缺陷的推理——利用捷径、瞎猜、或使用不泛化的模式——到达正确答案的 rationale，会被正向强化。在分布内（in-distribution）的题上捷径有效；在分布外（out-of-distribution）的题上它会无声地失效。

V-STaR 的验证器通过学习给 rationale 排序来缓解这个问题，但验证器是在同一个标签集上训练的。它可能学会偏好「格式漂亮的错误推理」而不是「诚实的不确定性」。更安全的设计是把 STaR 式数据与下面两者结合：(a) 过程监督的奖励模型（奖励中间步骤，而不只是答案）和 (b) 能击穿简单捷径的留出 OOD 评估。

> All three methods use the final answer as the gradient signal. A rationale that reaches the right answer via flawed reasoning — exploiting a shortcut, guessing, or using a non-generalizing pattern — gets positively reinforced. On in-distribution problems the shortcut works. On out-of-distribution problems it breaks silently.
> V-STaR's verifier mitigates by learning to rank rationales, but the verifier is trained on the same label set. It can learn to prefer well-formatted wrong reasoning over honest uncertainty.
> The safer design is to combine STaR-style data with (a) process-supervised reward models (rewarding intermediate steps, not just answers) and (b) held-out OOD evaluation that breaks simple shortcuts.

### Comparison · 对比

| 方法 | 训练信号 | 推理成本 | 数据浪费 | 已知失败模式 |
|---|---|---|---|---|
| STaR | 答对就保留 (rationale, answer) | 1x | 丢弃所有错误 rationale | 捷径 rationale |
| STaR + rationalization | 上述 + 注入正确答案后重试 | 1x | 较少 | rationalize 出的 rationale 可能不合情理 |
| V-STaR | STaR + 用两类样本 DPO 训练的验证器 | Nx (best-of-N) | 极少 | 验证器可能强化「自信的错误」 |
| Quiet-STaR | 逐 token rationale + 混合权重 | 1.5-3x | 极少 | 梯度仍然以答案为条件 |

> | Method | Training signal | Inference cost | Data waste | Known failure mode |
> |---|---|---|---|---|
> | STaR | keep (rationale, answer) if correct | 1x | discards all incorrect rationales | shortcut rationales |
> | V-STaR | STaR + DPO verifier from both classes | Nx (best-of-N) | minimal | verifier can reinforce confident wrongness |
> | Quiet-STaR | per-token rationale + mixing weight | 1.5-3x | minimal | still answer-conditioned gradient |

### Where this sits in the 2026 stack · 它在 2026 年技术栈里的位置

STaR 已经不算新。但这个模式在 2025-2026 年无处不在。在可验证数学题上做的 RL（DeepSeek-R1、Kimi-k1.5、o1）就是 STaR 那个以答案为条件的梯度信号放大后的样子。过程奖励模型（Lightman 等，2023；OpenAI 的 "Let's verify step by step"）是过程监督的替代路线。AlphaEvolve（第 3 课）是代码版的 STaR，只是把标签换成了程序评估器。Darwin Godel Machine（第 4 课）则是智能体脚手架自身的 STaR。

理解了 STaR，以上这些全都会豁然开朗。它就是最小可行的自我改进循环。

> STaR is old. But the pattern reappears everywhere in 2025-2026. RL on verifiable math problems (DeepSeek-R1, Kimi-k1.5, o1) is STaR's answer-conditioned gradient signal, scaled up. Process reward models (Lightman et al., 2023; OpenAI's "Let's verify step by step") are the process-supervised alternative. AlphaEvolve (Lesson 3) is STaR for code, with a program evaluator instead of a label. Darwin Godel Machine (Lesson 4) is STaR for the agent scaffolding itself.
> Understanding STaR makes all of these click. It is the minimum-viable self-improvement loop.

```figure
reflection-loop
```

## Use It · 实战用法

`code/main.py` 在一个玩具算术任务上运行模拟的 STaR 循环。你可以看到：

- 准确率如何随自举轮次攀升。
- 捷径如何悄悄混进来：模拟器里包含一类「偷懒」的 rationale，它有 40% 的概率碰对答案但泛化很差。观察 STaR 是否会把它们留下来。
- 验证器（V-STaR 式）如何在推理时提供帮助，却无法完全剔除训练期间引入的捷径。

> `code/main.py` runs a simulated STaR loop on a toy arithmetic task. You can watch:
> - How accuracy climbs over bootstrap rounds.
> - How shortcuts sneak in: the simulator includes a "lazy" rationale class that gets the right answer 40% of the time but generalizes badly. Watch whether STaR keeps them.
> - How a verifier (V-STaR style) helps at inference but cannot fully prune shortcuts introduced during training.

## Ship It · 交付

`outputs/skill-star-loop-reviewer.md` 帮你在训练之前审计一个候选的自我教学推理管线。

> `outputs/skill-star-loop-reviewer.md` helps you audit a proposed self-taught-reasoning pipeline before you train on it.

## Exercises · 练习

1. 跑一遍模拟器。把捷径频率先设为 0，再设为 0.4。两次运行的最终准确率会差多少？——即便两者在训练分布上都超过 90%。

2. 给模拟器加一个留出的 OOD 测试。从另一个分布抽题，在分布内和 OOD 两个集合上评估自举后的模型，量化这个差距。

3. 读 Quiet-STaR 论文（arXiv:2403.09629）第 3 节。分别用三句话解释 "end-of-thought" token 和混合权重头（mixing-weight head）。

4. 把 STaR 的「答对就保留」过滤器，与一个对 rationale 每一步独立给奖的过程监督替代方案做比较。指出两者的标注成本差异和可能的质量差异。

5. 设计一个能在已部署模型中抓住捷径 rationale 的评估。它不必完美——它只需要能击穿 STaR 循环会强化的那些最简单的捷径。

> Set the shortcut frequency to zero, then to 0.4. How much does final accuracy diverge between the two runs, even though both hit >90% on the training distribution?

## Key Terms · 术语表

| 术语 | 人们口头怎么说 | 它实际是什么意思 |
|---|---|---|
| STaR | 「Self-Taught Reasoner」 | 在模型自己生成、且最终答案正确的 rationale 上做微调；循环往复 |
| Rationalization | 「带提示的重试」 | 对基础模型做不出的题，注入正确答案后重新提示模型生成 rationale |
| V-STaR | 「带验证器的 STaR」 | 用正确和错误两类 rationale 做 DPO 训练一个验证器，用于推理时选择 |
| Quiet-STaR | 「逐 token 的 rationale」 | 在每个 token 位置生成隐藏想法，并与基线预测混合 |
| Answer-conditioned gradient | 「只看结果的信号」 | 训练循环奖励最终答案，而不是推理步骤 |
| Process reward model | 「步骤级验证器」 | 在每一步正确性（而非最终结果）上训练的奖励模型——与 STaR 形成对照 |
| Shortcut rationale | 「答案对、推理错」 | 通过不泛化的模式到达标签的 rationale；STaR 会保留它们 |

## Further Reading · 延伸阅读

- [Zelikman et al. (2022). STaR: Bootstrapping Reasoning With Reasoning](https://arxiv.org/abs/2203.14465) —— 原始论文。
- [Hosseini et al. (2024). V-STaR: Training Verifiers for Self-Taught Reasoners](https://arxiv.org/abs/2402.06457) —— 增加了用于推理时选择的 DPO 验证器。
- [Zelikman et al. (2024). Quiet-STaR: Language Models Can Teach Themselves to Think Before Speaking](https://arxiv.org/abs/2403.09629) —— 逐 token 的内部 rationale。
- [Lightman et al. (2023). Let's Verify Step by Step](https://arxiv.org/abs/2305.20050) —— 过程奖励模型，另一条梯度信号路线。
- [DeepSeek-R1 paper (arXiv:2501.12948)](https://arxiv.org/abs/2501.12948) —— 在可验证任务上做 RL，把 STaR 放大到前沿训练规模。
