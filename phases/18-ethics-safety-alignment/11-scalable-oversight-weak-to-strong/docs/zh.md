# Scalable Oversight and Weak-to-Strong Generalization · 可扩展监督与弱到强泛化

> Burns 等人（OpenAI Superalignment，「Weak-to-Strong Generalization」，2023）为超对齐（superalignment）问题提出了一个代理问题：用更弱模型产生的标签去微调一个强模型。如果强模型能从不完美的弱监督中正确泛化，那么当前人类尺度的对齐方法或许可以延伸到超人类系统。可扩展监督（scalable oversight）与 W2SG 是互补的。可扩展监督（辩论、递归奖励建模、任务分解）提高监督者的有效能力，使它能跟上被监督的模型。W2SG 确保强模型从监督者所能提供的任何不完美监督中正确泛化。Debate Helps W2SG（arXiv:2501.13124，2025 年 1 月）把两者结合了起来。

> Burns et al. (OpenAI Superalignment, "Weak-to-Strong Generalization", 2023) proposed a proxy for the superalignment problem: fine-tune a strong model using labels produced by a weaker model. If the strong model generalizes correctly from imperfect weak supervision, current human-scale alignment methods may extend to superhuman systems. Scalable oversight and W2SG are complementary. Scalable oversight (debate, recursive reward modeling, task decomposition) increases the overseer's effective capability so it can keep up with the model under oversight. W2SG ensures the strong model generalizes correctly from whatever imperfect supervision the overseer provides. Debate Helps W2SG (arXiv:2501.13124, January 2025) combines them.

**Type:** Learn
**Languages:** Python (stdlib, W2SG gap simulator)
**Prerequisites:** Phase 18 · 01 (instruction-following), Phase 18 · 10 (AI Control), Phase 09 (RL foundations)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 定义可扩展监督（scalable oversight）与弱到强泛化（weak-to-strong generalization），并解释它们如何互补。
- 描述 Burns 等人 2023 年的实验设置：用 GPT-2 的标签微调 GPT-4。
- 解释「恢复的性能差距」（PGR）指标及其测量对象。
- 说出三种主要的可扩展监督机制（辩论、递归奖励建模、任务分解）及各自的一个优点。

> Define scalable oversight and weak-to-strong generalization and explain how they are complementary.
> Describe the Burns et al. 2023 experimental setup: fine-tune GPT-4 using labels from GPT-2.
> Explain the performance gap recovered (PGR) metric and what it measures.
> State the three major scalable-oversight mechanisms (debate, recursive reward modeling, task decomposition) and one strength of each.

## The Problem · 问题所在

Phase 18 到目前为止的每一种对齐技术都假定：监督者能够评估模型的行为。当模型是超人类的，监督者就是薄弱环节。超对齐（superalignment）问题：一个更弱的监督者能否可靠地产出一个更强的、对齐的模型？

Burns 等人把它化归为一个可操作化的实证设置：用弱者监督强者，测量强模型的能力有多少能在弱监督下存活。这不是超对齐的解决方案 —— 它是一个让我们能测量进展的代理问题。

> Every alignment technique so far in Phase 18 assumes the overseer can evaluate the model's behaviour. When the model is superhuman, the overseer is the weak link. The superalignment question: can a weaker supervisor reliably produce a stronger, aligned model?
> Burns et al. reduce this to an operationalized empirical setup: supervise strong with weak, measure how much of the strong model's capability survives the weak supervision. This is not a solution to superalignment — it is a proxy that lets us measure progress.

## The Concept · 概念

### W2SG: the Burns et al. setup · W2SG：Burns 等人的设置

- 弱模型：GPT-2 级。
- 强模型：GPT-4 级。
- 目标：强模型在该任务上的 GPT-4 上限。

流程：
1. 取弱模型在该任务上的零样本（zero-shot）预测。
2. 用弱标注数据微调强模型。
3. 测量微调后强模型的准确率。

基线：弱模型自身的准确率；强模型在金标签（gold labels）上的有监督上限。

差距指标：恢复的性能差距（Performance Gap Recovered, PGR）= (微调后 - 弱) / (上限 - 弱)。PGR 为 1.0 表示弱监督完全弥合了差距；PGR 为 0 表示弱监督没有帮助。

> - Weak model: GPT-2 class.
> - Strong model: GPT-4 class.
> - Target: strong GPT-4 ceiling on the task.
> Procedure:
> 1. Get weak model's zero-shot predictions on a task.
> 2. Fine-tune the strong model on weak-labeled data.
> 3. Measure the strong fine-tuned model's accuracy.
> Baselines: weak model's own accuracy, strong model's supervised ceiling on gold labels.
> Gap metric: Performance Gap Recovered (PGR) = (fine-tuned - weak) / (ceiling - weak). PGR of 1.0 means weak supervision fully closes the gap; PGR of 0 means weak supervision did not help.

### Burns et al. empirical findings · Burns 等人的实证发现

在 NLP、国际象棋谜题和奖励建模任务上，PGR 始终为正：强模型泛化得超出了弱监督者的错误。各任务的 PGR 从约 20% 到约 80% 不等。强模型从不完美标签中「理解」了目标任务，用它的预训练先验把空缺补上了。

Burns 等人指出的局限：
- 这里的弱到强差距是能力差距，不是对齐差距。弱模型是对齐的；而一个真正超人类的模型也许能被人类对齐，但能力差距要大得多。
- 强模型的泛化可能更多来自任务先验，而不是对真值意图的还原。
- 引出（elicit）强模型的潜在知识才是真正的问题；PGR 测量的是一种特定的操作化。

> Across NLP, chess-puzzle, and reward-modeling tasks, PGR was consistently positive: the strong model generalized beyond the weak supervisor's mistakes. Task-specific PGR varied from ~20% to ~80%. The strong model "understands" the intended task from imperfect labels, filling in with its pre-trained priors.
> Limitations Burns et al. note:
> - The weak-to-strong gap here is capability, not alignment. The weak model is aligned; a truly superhuman model might be aligned by a human but with a much larger capability gap.
> - The strong model's generalization may be more about task priors than about recovering ground-truth intent.
> - Eliciting the strong model's latent knowledge is the real problem; PGR measures a specific operationalization.

### Scalable oversight: three mechanisms · 可扩展监督：三种机制

- **辩论（Debate，Irving 等人 2018）。** U 的两个实例各执一方辩论；弱裁判来裁决。其假设：为一个正确答案找到有说服力的论证，比为错误答案找到有说服力的论证更容易。2024-2025 年的新工作（Khan 等人、Michael 等人）表明辩论有时有用、有时没用，是否有用取决于任务结构。
- **递归奖励建模（Recursive Reward Modeling，Leike 等人 2018）。** U 协助人类训练针对 U+1 的奖励模型。监督者的有效能力随模型的能力一起增长。
- **任务分解（Task Decomposition，Christiano、Shlegeris、Amodei 2018）。** 把难任务递归地分解成人类可核查的子任务。它假定任务可分解。

每种机制都对任务结构或中间组件的对齐性有所假定。

> - **Debate (Irving et al. 2018).** Two instances of U argue opposite sides; the weak judge decides. The assumption: finding a convincing true answer is easier than finding a convincing false answer. Recent 2024-2025 work (Khan et al., Michael et al.) shows debate sometimes helps and sometimes does not, and whether it helps depends on task structure.
> - **Recursive Reward Modeling (Leike et al. 2018).** U helps the human train the reward model for U+1. The overseer's effective capability grows with the model's.
> - **Task Decomposition (Christiano, Shlegeris, Amodei 2018).** Decompose a hard task into sub-tasks the human can check, recursively. Assumes decomposability.
> Each mechanism assumes something about the structure of the task or the alignment of the intermediate components.

### Why scalable oversight and W2SG are complementary · 为什么可扩展监督与 W2SG 互补

可扩展监督提高监督者信号的有效质量。
W2SG 从监督者所能提供的任何不完美信号中弥合差距。

Lang 等人 —— Debate Helps Weak-to-Strong Generalization（arXiv:2501.13124）把两者结合：辩论协议提供更好的弱标签，强模型再在这些标签上训练。在 NLP 任务上报告了 PGR 提升。

> Scalable oversight increases the overseer's effective signal quality.
> W2SG closes the gap from whatever imperfect signal the overseer can provide.
> Lang et al. — Debate Helps Weak-to-Strong Generalization (arXiv:2501.13124) combines them: a debate protocol provides better weak labels, and the strong model is trained on those labels. Reported PGR gains on NLP tasks.

### The organizational drama · 组织层面的波折

OpenAI 的 Superalignment 团队在 Jan Leike 离职加入 Anthropic 后，于 2024 年 5 月解散。该议程（可扩展监督、W2SG、自动化对齐研究）在 Anthropic 和各学术实验室延续 —— MATS（第 28 课）、Redwood（第 10 课）、Apollo（第 8 课）、METR（第 28 课）。组织结构变了；研究问题没变。

> OpenAI's Superalignment team dissolved in May 2024 after Jan Leike's departure to Anthropic. The agenda (scalable oversight, W2SG, automated alignment research) continued at Anthropic and at academic labs — MATS (Lesson 28), Redwood (Lesson 10), Apollo (Lesson 8), METR (Lesson 28). The organizational structure changed; the research questions did not.

### Where this fits in Phase 18 · 它在 Phase 18 中的位置

第 6-10 课描述了威胁，以及「假定 U 不可信」之下的防御范式。第 11 课是进攻范式：把监督者变得足够强，强到能验证 U 的对齐。第 12-16 课随后转向对抗评估的实用工具。

> Lessons 6-10 describe the threat and the defensive paradigm under the assumption U is untrustworthy. Lesson 11 is the offensive paradigm: make the overseer strong enough to verify U's alignment. Lessons 12-16 then turn to the practical tooling of adversarial evaluation.

```figure
scalable-oversight
```

## Use It · 实战用法

`code/main.py` 在一个合成任务上模拟 W2SG 微调。弱标注器有 70% 准确率且错误呈结构化；强模型在金标签上有 95% 的上限。你用弱标签微调强模型，测量 PGR，并与「强模型在金标签上」和「弱模型单打独斗」比较。

> `code/main.py` simulates a W2SG fine-tune on a synthetic task. Weak labeler has 70% accuracy with structured errors; strong model has 95% ceiling on gold labels. You fine-tune the strong model on weak labels, measure PGR, and compare to strong-on-gold and weak-alone.

## Ship It · 交付

本课产出 `outputs/skill-w2sg-pgr.md`。给定一个监督设置的描述，它识别弱监督者、强模型、监督质量，并计算（或索取）PGR。它会标记该主张到底是「弱者能监督强者」，还是「弱者 + 监督机制能监督强者」。

> This lesson produces `outputs/skill-w2sg-pgr.md`. Given an oversight setup description, it identifies the weak supervisor, the strong model, the supervision quality, and computes (or requests) PGR. It flags whether the claim is "weak can supervise strong" or "weak + oversight mechanism can supervise strong."

## Exercises · 练习

1. 运行 `code/main.py`。报告 weak_accuracy = 0.60、0.70、0.80 时的 PGR。解释 PGR 曲线的形状。

2. 修改弱标注器，让它带有结构化错误（例如在某一类输入上总是错）。PGR 会升高、降低还是不变？解释原因。

3. 阅读 Burns 等人 2023 年第 4.3 节（NLP 任务）。复现「置信度辅助损失」的直觉：当强模型比弱标签更自信时，谁赢？

4. 为一个软件工程任务设计一个结合辩论与任务分解的可扩展监督协议。为每个组件指出一种失效模式，并解释这种组合如何解决（或未能解决）每种失效。

5. 阐明什么样的证据能证伪「弱到强泛化是通往超对齐的可行路径」这一主张。具体说明你需要看到的经验签名。

> 1. Run `code/main.py`. Report PGR for weak_accuracy = 0.60, 0.70, 0.80. Explain the shape of the PGR curve.
> 2. Modify the weak labeler to have structured error (e.g., always wrong on a specific input class). Does PGR increase, decrease, or stay the same? Explain.
> 3. Read Burns et al. 2023 Section 4.3 (NLP tasks). Reproduce the "confidence auxiliary loss" intuition: when the strong model is more confident than the weak labels, who wins?
> 4. Design a scalable-oversight protocol that combines debate and task decomposition for a software-engineering task. Name one failure mode of each component and explain how the combination addresses or fails to address each.
> 5. Articulate what would falsify the "weak-to-strong generalization is a viable path to superalignment" claim. Be specific about the empirical signature you would need to see.

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|-----------------|------------------------|
| Scalable oversight（可扩展监督） | 「把监督者变强」 | 提高监督者评估更强模型之能力的机制 |
| W2SG（弱到强泛化） | 「弱监督强」 | 用弱标签微调强模型，并测量能恢复多少能力 |
| PGR（恢复的性能差距） | 「performance gap recovered」 | (微调后 - 弱) / (上限 - 弱)；1.0 = 完全弥合，0 = 没有帮助 |
| Debate（辩论） | 「两个 U 实例对垒」 | 由弱裁判在两个 U 辩手之间做裁决的可扩展监督机制 |
| RRM（递归奖励建模） | 「recursive reward modeling」 | U 协助训练针对 U+1 的奖励模型；监督者能力随 U 增长 |
| Task decomposition（任务分解） | 「人类可核查的子任务」 | 把难任务递归地拆成人类可验证的子任务 |
| Superalignment（超对齐） | 「对齐超人类 AI」 | 关注对齐人类无法直接评估的模型的研究议程 |

## Further Reading · 延伸阅读

- [Burns et al. — Weak-to-Strong Generalization (OpenAI 2023)](https://openai.com/index/weak-to-strong-generalization/) —— W2SG 论文
- [Irving, Christiano, Amodei — AI safety via debate (arXiv:1805.00899)](https://arxiv.org/abs/1805.00899) —— 辩论机制
- [Leike et al. — Scalable agent alignment via reward modeling (arXiv:1811.07871)](https://arxiv.org/abs/1811.07871) —— 递归奖励建模
- [Khan et al. — Debating with More Persuasive LLMs Leads to More Truthful Answers (arXiv:2402.06782)](https://arxiv.org/abs/2402.06782) —— 2024 年关于更强辩手参与辩论的实证研究
- [Lang et al. — Debate Helps Weak-to-Strong Generalization (arXiv:2501.13124)](https://arxiv.org/abs/2501.13124) —— 2025 年辩论 + W2SG 的结合
