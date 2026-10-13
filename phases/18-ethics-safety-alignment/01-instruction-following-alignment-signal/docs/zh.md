# Instruction-Following as Alignment Signal · 指令遵循即对齐信号

预训练语言模型只会补全文本，不会回答问题。InstructGPT 用「SFT → 奖励模型 → PPO」三段流水线把补全器变成了助手，而一个 1.3B 的模型在人类偏好上赢了 175B 的 GPT-3 —— 这一条结果解释了为什么 2026 年每个前沿实验室仍在跑 RLHF 形状的后训练流水线。

> Every later critique of RLHF argues against this pipeline. Before you study how optimization pressure distorts a proxy, you have to see the proxy. InstructGPT (Ouyang et al., 2022) defined the reference architecture: supervised fine-tuning on instruction-response pairs, a reward model trained on pairwise preference rankings, and PPO against the reward model with a KL penalty to the SFT policy. A 1.3B InstructGPT was preferred over a 175B GPT-3. That single result is the reason every frontier lab in 2026 still ships an RLHF-shaped post-training pipeline.

**Type:** Learn
**Languages:** Python (stdlib, toy three-stage pipeline)
**Prerequisites:** Phase 10 · 06 (SFT), Phase 10 · 07 (RLHF), Phase 10 · 08 (DPO)
**Time:** ~45 minutes

---

## Learning Objectives · 学习目标

- 说出 InstructGPT 流水线的三个阶段，以及每个阶段使用的损失
- 解释为什么 1.3B 的指令微调模型在人类偏好评估上击败了原始的 175B GPT-3
- 说明第 3 阶段的 KL 惩罚在防范什么，以及为什么去掉它会塌缩成 mode-seeking（只押单一模式）行为
- 描述对齐税（alignment tax），以及 Ouyang 等人针对它使用的 PPO-ptx 缓解手段

> Name the three stages of the InstructGPT pipeline and the loss used in each.
> Explain why a 1.3B instruction-tuned model beat the raw 175B GPT-3 on human preference evaluation.
> State what the KL penalty in stage 3 is protecting against and why removing it collapses to mode-seeking behaviour.
> Describe the alignment tax and the PPO-ptx mitigation Ouyang et al. used against it.

---

## The Problem · 问题在哪

预训练语言模型做的事是补全文本，不是回答问题。问 GPT-3「写一个反转列表的 Python 函数」，你常常会收回另一个 prompt —— 因为训练分布大多是网页文本，而网页文本接下来还是网页文本。模型在忠实地做它的工作 —— 只是这份工作本身错了。

所有严肃实验室用来修这个问题的代理（proxy）是人类偏好。两个补全交给标注员；标注员挑出更好的那个；一个奖励模型学会模仿标注员。然后一个 RL 循环把策略推向奖励模型打高分的输出。这就是 InstructGPT 的全部论点，三句话。论文剩下的部分都是工程。

> Pre-trained language models complete text. They do not answer questions. Ask GPT-3 "write a Python function that reverses a list" and you often get back another prompt, because most of the training distribution is web text that continues with more web text. The model is doing its job — the job is wrong.
> The proxy every serious lab used to fix this is human preference. Two completions go to a rater; the rater picks the better one; a reward model learns the rater. Then an RL loop shifts the policy toward outputs the reward model scores high. That is the full InstructGPT thesis in three sentences. The rest of the paper is engineering.

---

## The Concept · 概念

### Stage 1: supervised fine-tuning (SFT) · 阶段 1：监督微调（SFT）

收集 prompt-response 对，其中 response 是一个善意的会写作的人类会给出的回答。Ouyang 等人用了来自标注员和 OpenAI API 的 13k 个 prompt。用标准交叉熵损失在这份数据上微调基座模型。

SFT 给你的：模型现在会回答问题，而不是续写问题。SFT 不给你的：当多个答案都说得通时，关于标注员偏好哪个答案的任何信号。

> Collect prompt-response pairs where the response is what a well-intentioned human would write. Ouyang et al. used 13k prompts from labelers and the OpenAI API. Fine-tune the base model on this data with standard cross-entropy loss.
> What SFT gives you: the model now answers questions instead of continuing them. What it does not give you: any signal about which answer the rater prefers when multiple are plausible.

---

### Stage 2: reward model (RM) · 阶段 2：奖励模型（RM）

对每个 prompt，从 SFT 模型采样 K 个补全，由标注员排序。训练一个奖励模型（reward model），让它给任意 prompt-response 对打分，使得在 `y_w` 被偏好于 `y_l` 的对上：

```
L_RM = -log sigmoid(r(x, y_w) - r(x, y_l))
```

这就是 Bradley-Terry 成对偏好损失。奖励模型通常从 SFT 模型初始化，把 LM head 换成一个标量头。

奖励模型很小：对 175B 的 InstructGPT，6B 就够了。它们也很脆弱 —— 论文第 5 节大部分内容讲的就是在小规模上就已经冒头的奖励劫持（reward hacking）行为。

> For each prompt, sample K completions from the SFT model. A labeler ranks them. Train a reward model that scores any prompt-response pair so that, for pairs where `y_w` was preferred over `y_l`:
> This is the Bradley-Terry pairwise preference loss. The RM is usually initialized from the SFT model with the LM head replaced by a scalar head.
> Reward models are small: 6B was enough for the 175B InstructGPT. They are also fragile — section 5 of the paper is mostly about reward-hacking behaviours that showed up at small scale.

---

### Stage 3: PPO with a KL penalty · 阶段 3：带 KL 惩罚的 PPO

定义目标：

```
J(pi) = E_{x~D, y~pi(.|x)} [ r(x, y) ] - beta * KL(pi(.|x) || pi_SFT(.|x))
```

用 PPO 最大化它。KL 项防止 `pi` 漂移得离 SFT 策略太远。没有它，优化器会找到对抗样本 —— 那些在 RM 下得分很高的字符串，不是因为人类真的偏好它们，而是因为 RM 从没见过它们。

KL 系数 `beta` 是 RLHF 唯一最重要的超参数。太低：奖励劫持。太高：相比 SFT 毫无改进。

> Define the objective:
> Maximize with PPO. The KL term keeps `pi` from drifting far from the SFT policy. Without it, the optimizer finds adversarial examples — strings that score high under the RM because the RM never saw them, not because humans actually prefer them.
> The KL coefficient `beta` is the single most important RLHF hyperparameter. Too low: reward hacking. Too high: no improvement over SFT.

---

### The alignment tax · 对齐税

RLHF 之后，模型更被人类偏好，但在标准基准（SQuAD、HellaSwag、DROP）上出现退步。Ouyang 等人称之为对齐税（alignment tax），并用 PPO-ptx 修复：把预训练梯度混进 RL 目标，让模型不会忘记怎么完成那些它从未因此拿到奖励的下游任务。

```
J_ptx(pi) = J(pi) + gamma * E_{x~D_pretrain} [ log pi(x) ]
```

PPO-ptx 成了标准做法。Anthropic、DeepMind 和 Meta 用的都是它的某个变体。

> After RLHF, the model is preferred by humans but regresses on standard benchmarks (SQuAD, HellaSwag, DROP). Ouyang et al. call this the alignment tax and fix it with PPO-ptx: mix pre-training gradients into the RL objective so the model does not forget how to do downstream tasks it was never rewarded for.
> PPO-ptx became standard. Anthropic, DeepMind, and Meta all use some variant.

---

### The result · 结果

一个 1.3B 的 InstructGPT（SFT + RM + PPO-ptx）在约 70% 的情况下被标注员偏好于 175B 的基座 GPT-3。在生产流量的隐藏测试 prompt 上，差距还会拉大。从这个数字能读出两件事：

1. 对齐（alignment）和能力（capability）是两个不同的轴。175B 模型能力更强；1.3B 模型对齐更好；标注员偏好对齐更好的那个。
2. 能力的下限由基座模型决定。你没法用 RLHF 让一个基座模型知道它从没见过的知识。

> A 1.3B InstructGPT (SFT + RM + PPO-ptx) is preferred by labelers over the 175B base GPT-3 about 70% of the time. The gap widens on hidden-test prompts from production traffic. Two things to read off this number:
> 1. Alignment is a different axis from capability. The 175B model had more capability; the 1.3B model had more alignment; labelers preferred the aligned one.
> 2. The capability floor is set by the base model. You cannot RLHF a base model into knowing facts it never saw.

---

### Why this is the reference point for Phase 18 · 为什么这是第 18 阶段的参照点

后面每一课的批评 —— 奖励劫持（第 2 课）、DPO（第 3 课）、谄媚（sycophancy，第 4 课）、CAI（第 5 课）、休眠代理（sleeper agents，第 7 课）、对齐伪装（alignment faking，第 9 课）—— 都在反驳这条流水线的某一部分。奖励劫持攻击阶段 2。DPO 把阶段 2 和 3 合并掉。CAI 替换掉人类标注员。谄媚表明标注员是一个有偏信号。对齐伪装表明策略可以完全绕过阶段 3。脑子里没有先装下这条流水线，你就跟不上这些批评中的任何一个。

```figure
al-instruct-pipeline
```

> Every critique in later lessons — reward hacking (Lesson 2), DPO (Lesson 3), sycophancy (Lesson 4), CAI (Lesson 5), sleeper agents (Lesson 7), alignment faking (Lesson 9) — argues against some part of this pipeline. Reward hacking attacks stage 2. DPO collapses stages 2 and 3. CAI replaces the human labeler. Sycophancy shows the labeler is a biased signal. Alignment faking shows the policy can route around stage 3 entirely. You cannot follow any of these critiques without the pipeline in your head first.

---

## Use It · 实战用法

`code/main.py` 在玩具偏好数据上模拟这三个阶段。基座「策略」是动作 {A, B, C} 上的一个有偏硬币。阶段 1 的 SFT 在 200 个 prompt 上模仿标注员动作。阶段 2 从 500 个成对排序拟合一个 Bradley-Terry 奖励模型。阶段 3 跑一个带 KL 惩罚（锚定到 SFT 策略）的简化 PPO 更新。你可以看着奖励攀升、KL 散度增长、策略漂移 —— 还可以把 KL 项关掉，看着奖励劫持在 50 步更新之内浮现。

值得观察的点：

- `beta = 0.1` 与 `beta = 0.0` 下的奖励轨迹
- 整个训练过程中的 KL(pi || pi_SFT)
- 最终动作分布与标注员偏好的对比

> `code/main.py` simulates the three stages on toy preference data. The base "policy" is a biased coin over actions {A, B, C}. Stage 1 SFT mimics labeler actions on 200 prompts. Stage 2 fits a Bradley-Terry reward model from 500 pairwise rankings. Stage 3 runs a simplified PPO update with a KL penalty to the SFT policy. You can watch the reward climb, the KL divergence grow, and the policy drift — and you can turn off the KL term to see reward hacking appear inside 50 update steps.
> What to look at:
> - Reward trajectory with `beta = 0.1` vs `beta = 0.0`.
> - KL(pi || pi_SFT) over training steps.
> - Final action distribution compared to labeler preference.

---

## Ship It · 交付

本课产出 `outputs/skill-instructgpt-explainer.md`。给定一段 RLHF 流水线描述或论文摘要，它能识别被修改的是三个阶段中的哪一个、每个阶段用的是什么损失、以及是否存在 KL 惩罚或等价正则项。

> This lesson produces `outputs/skill-instructgpt-explainer.md`. Given an RLHF pipeline description or a paper abstract, it identifies which of the three stages is being modified, what loss is being used at each stage, and whether a KL penalty or equivalent regularizer is present.

---

## Exercises · 练习

1. 运行 `code/main.py`。设 `beta = 0.0`，报告 200 步 PPO 后的动作分布。用一段话解释这种 mode-seeking（只押单一模式）行为。

2. 修改奖励模型，让动作 B 带 +0.5 的偏置（模拟一个奖励 bug）。用 `beta = 0.1` 跑 PPO。KL 惩罚能阻止策略利用这个偏置吗？`beta` 取多少时利用变得可见？

3. 阅读 Ouyang 等人（arXiv:2203.02155）的图 1。分别跑 1、5、20、100 步 PPO 并对照 SFT 模型测量偏好，复现标注员偏好曲线。

4. 论文 4.3 节报告 1.3B InstructGPT 约 70% 的时候胜过 175B GPT-3。为什么这个比例在隐藏的生产 prompt 上会比在标注员自己的 prompt 上更高？

5. 在同一份偏好数据上把 PPO 损失换成 DPO（Phase 10 · 08）。比较最终策略漂移（对 SFT 的 KL）和最终奖励。在奖励相同的情况下，哪种方法漂移得更远？

---

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|------------------------|
| SFT | "指令微调" | 阶段 1：在 prompt-response 对上用交叉熵做微调 |
| Reward model | "那个 RM" | 在 (prompt, response) 上输出标量的回归器，用 Bradley-Terry 在成对标签上训练 |
| Bradley-Terry | "成对偏好损失" | -log sigmoid(r_w - r_l)；把成对排序归约为二分类 |
| KL penalty | "那个正则项" | `beta * KL(pi \|\| pi_SFT)` —— 把 RL 策略锚在 SFT 锚点附近 |
| PPO-ptx | "混预训练的 PPO" | 在 PPO 目标中加入一部分预训练对数似然，以抵消对齐税 |
| Alignment tax | "RLHF 造成的退步" | RLHF 之后在那些 RLHF 没有针对的标准基准上的下滑 |
| Labeler preference | "那个真值" | 人类排序的样本；RM 是它的统计代理，而不是「人类价值观」的代理 |

---

## Further Reading · 延伸阅读

- [Ouyang et al. — Training language models to follow instructions with human feedback (arXiv:2203.02155)](https://arxiv.org/abs/2203.02155) —— InstructGPT 论文，此后所有 RLHF 流水线的基石
- [Stiennon et al. — Learning to summarize from human feedback (arXiv:2009.01325)](https://arxiv.org/abs/2009.01325) —— 用 RLHF 做摘要的前作
- [Christiano et al. — Deep reinforcement learning from human preferences (arXiv:1706.03741)](https://arxiv.org/abs/1706.03741) —— 最早的基于偏好的 RL 形式化
- [Bai et al. — Training a Helpful and Harmless Assistant with RLHF (arXiv:2204.05862)](https://arxiv.org/abs/2204.05862) —— Anthropic 对 InstructGPT 流水线的 HH 扩展
