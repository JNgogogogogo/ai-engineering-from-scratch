# The Direct Preference Optimization Family · 直接偏好优化家族

Rafailov 等人（2023）证明 RLHF 的最优解关于偏好数据有闭式形式，所以你可以跳过显式的奖励模型、直接优化策略。这个洞见催生了一个家族 —— IPO、KTO、SimPO、ORPO、BPO —— 每一个都在修 DPO 的某个失败模式。到 2026 年，直接对齐算法（direct alignment algorithms）支撑的前沿后训练运行比 PPO 还多。但第 2 课的过度优化曲线依然成立：DAA 逃不出古德哈特，它们只是改变了它咬人的位置。

> Rafailov et al. (2023) showed RLHF's optimum has a closed form in terms of the preference data, so you can skip the explicit reward model and optimize the policy directly. That insight spawned a family — IPO, KTO, SimPO, ORPO, BPO — each fixing a failure mode of DPO. In 2026, direct alignment algorithms ship more frontier post-training runs than PPO. But the over-optimization curve from Lesson 2 still applies: DAAs do not escape Goodhart, they just move where it bites.

**Type:** Learn
**Languages:** Python (stdlib, six-variant preference-loss comparator)
**Prerequisites:** Phase 18 · 01 (InstructGPT), Phase 18 · 02 (Reward hacking), Phase 10 · 08 (DPO basics)
**Time:** ~75 minutes

---

## Learning Objectives · 学习目标

- 从带 KL 的 RLHF 最优解推导出 DPO 闭式形式
- 说出 IPO、KTO、SimPO、ORPO、BPO 各自修复了 DPO 的哪个失败模式
- 区分「隐式奖励差距」与「偏好强度」，并解释 IPO 的恒等映射为什么重要
- 解释为什么 Rafailov 等人（NeurIPS 2024）证明 DAA 即使没有显式 RM 仍会过度优化

> Derive the DPO closed form from the RLHF-with-KL optimum.
> State the failure mode each of IPO, KTO, SimPO, ORPO, BPO fixes in DPO.
> Distinguish "implicit reward gap" from "preference strength" and explain why IPO's identity mapping matters.
> Explain why Rafailov et al. (NeurIPS 2024) prove DAAs over-optimize despite having no explicit RM.

---

## The Problem · 问题在哪

RLHF 目标（第 1 课）：

```
max_pi E_{x,y~pi} [ r(x, y) ] - beta * KL(pi || pi_ref)
```

有一个已知的最优解：

```
pi*(y|x) = (1/Z(x)) * pi_ref(y|x) * exp(r(x, y) / beta)
```

于是奖励被最优策略与参考策略之比隐式定义：

```
r(x, y) = beta * log(pi*(y|x) / pi_ref(y|x)) + beta * log Z(x)
```

把它代入 Bradley-Terry 偏好似然，配分函数 `Z(x)` 因为只依赖 `x` 而被消掉。剩下的就是一个只含策略参数的损失 —— 不再需要奖励模型。这就是 DPO。

麻烦在于：这个推导假设最优解可达、偏好数据在分布内、参考策略是真正的模式锚点。这三条没有一条严格成立。家族的每个成员修的都各是一条被违反的假设。

> The RLHF objective (Lesson 1):
> has a known optimum:
> So the reward is implicitly defined by the ratio of the optimal policy to the reference:
> Substitute this into the Bradley-Terry preference likelihood and the partition function `Z(x)` cancels because it depends only on `x`. What remains is a loss in the policy parameters alone — no reward model needed. That is DPO.
> The wrinkle: the derivation assumes the optimum is reachable, the preference data is in-distribution, and the reference policy is the true mode anchor. None of these hold exactly. Every family member fixes a different violated assumption.

---

## The Concept · 概念

### DPO (Rafailov et al., 2023) · DPO（Rafailov 等人，2023）

```
L_DPO = -log sigmoid(
  beta * log(pi(y_w | x) / pi_ref(y_w | x))
  - beta * log(pi(y_l | x) / pi_ref(y_l | x))
)
```

会出什么问题：

- 隐式奖励差距 `beta * (log(pi/pi_ref)_w - log(pi/pi_ref)_l)` 是无界的。极小的偏好也能产生任意大的差距。
- 这个损失把 chosen 和 rejected 的对数概率往相反方向推。只要 rejected 降得更快，chosen 的绝对对数概率也可以被推着下降。这就是「chosen 退化响应」（Degraded Chosen Response）现象。
- 分布外偏好（稀有对 vs 稀有对）会产生任意的隐式奖励。

> What can go wrong:
> - The implicit reward gap `beta * (log(pi/pi_ref)_w - log(pi/pi_ref)_l)` is unbounded. A tiny preference can produce an arbitrarily large gap.
> - The loss drives chosen and rejected log-probs in opposite directions. It can push the chosen absolute log-prob down as long as the rejected falls faster. This is the Degraded Chosen Response phenomenon.
> - Out-of-distribution preferences (rare rare pair vs rare rare pair) produce arbitrary implicit rewards.

---

### IPO (Azar et al., 2024) · IPO（Azar 等人，2024）

恒等偏好优化（Identity Preference Optimization）把 log-sigmoid 换成对偏好概率的恒等映射。损失变成对一个有界目标的平方误差：

```
L_IPO = (log(pi(y_w | x) / pi_ref(y_w | x)) - log(pi(y_l | x) / pi_ref(y_l | x)) - 1/(2 beta))^2
```

间隔被 `1/(2 beta)` 封顶。偏好强度与隐式奖励差距成正比。不会爆炸。

> Identity Preference Optimization replaces the log-sigmoid with an identity mapping on the preference probability. The loss becomes a squared-error on a bounded target:
> The margin is bounded by `1/(2 beta)`. Preference strength and implicit-reward gap are proportional. No blow-up.

---

### KTO (Ethayarajh et al., 2024) · KTO（Ethayarajh 等人，2024）

卡尼曼-特沃斯基优化（Kahneman-Tversky Optimization）完全抛弃成对结构。给定单个带标签的输出和一个二值「desirable / undesirable」信号，它映射到一个前景理论（prospect theory）效用：

```
v(x, y) = sigma(beta * log(pi(y|x) / pi_ref(y|x)) - z_ref)
```

收益和损失用不同的权重（损失厌恶，loss aversion）。好处：你可以用非成对数据，而这种数据多得多。

> Kahneman-Tversky Optimization drops pairwise structure entirely. Given a single labeled output and a binary "desirable" or "undesirable" signal, it maps to a prospect-theory utility:
> with different weights for gains and losses (loss aversion). Benefit: you can use unpaired data, which is far more plentiful.

---

### SimPO (Meng et al., 2024) · SimPO（Meng 等人，2024）

简单偏好优化（Simple Preference Optimization）让训练信号与生成对齐：完全去掉参考策略，用长度归一化对数似然：

```
L_SimPO = -log sigmoid(
  (beta / |y_w|) * log pi(y_w | x)
  - (beta / |y_l|) * log pi(y_l | x)
  - gamma
)
```

再加一个间隔 `gamma` 来稳定。长度归一化消除了利用 DPO 长度偏差失败模式的激励（按构造，更长的 `y_w` 天生就有更大的对数概率差距）。

> Simple Preference Optimization aligns the training signal with generation. Remove the reference policy entirely and normalize log-likelihood by length:
> with a margin `gamma` to stabilize. The length normalization removes the incentive to exploit DPO's length-bias failure mode (longer `y_w` gives a larger log-prob gap by construction).

---

### ORPO (Hong et al., 2024) · ORPO（Hong 等人，2024）

几率比偏好优化（Odds-Ratio Preference Optimization）在标准 SFT 负对数似然上加一个偏好项：

```
L_ORPO = L_NLL(y_w) + lambda * L_OR
L_OR = -log sigmoid(log(odds(y_w) / odds(y_l)))
```

没有参考策略 —— SFT 项就是正则项。从基座模型到对齐模型单阶段训练。不需要单独的 SFT checkpoint。

> Odds-Ratio Preference Optimization adds a preference term to the standard SFT negative log-likelihood:
> No reference policy — the SFT term is the regularizer. Train in a single stage from the base model to the aligned model. No separate SFT checkpoint.

---

### BPO (ICLR 2026 submission, OpenReview id=b97EwMUWu7) · BPO（ICLR 2026 投稿，OpenReview id=b97EwMUWu7）

它指出了「chosen 退化响应」问题：DPO 保住了排序 `y_w > y_l`，但 `y_w` 的绝对对数概率可能下跌。BPO 加了一行修正，惩罚 chosen 响应上的下降。报告在 Llama-3.1-8B-Instruct 的数学推理上比 DPO 高 +10.1% 的准确率。

> Identifies the Degraded Chosen Responses problem: DPO preserves the ranking `y_w > y_l` but the absolute log-prob of `y_w` can drop. BPO adds a single-line correction that penalizes downward moves on the chosen response. Reported +10.1% accuracy on Llama-3.1-8B-Instruct on math reasoning over DPO.

---

### The universal result: DAAs still over-optimize · 通用结论：DAA 仍会过度优化

Rafailov 等人 "Scaling Laws for Reward Model Overoptimization in Direct Alignment Algorithms"（NeurIPS 2024）用 DPO、IPO、SLiC 在多个数据集、多个 KL 预算上训练策略。黄金奖励对 KL 的曲线呈现出与 Gao 等人相同的「见顶即崩」形状。隐式奖励在训练期间会查询分布外样本；KL 正则化稳不住这一点。

DAA 逃不出古德哈特。它们只是把咬人的表面从「奖励模型被过度优化」换成了「参考策略比值被过度优化」。通用解法 —— 更好的数据、集成、早停 —— 对两者都适用。

> Rafailov et al. "Scaling Laws for Reward Model Overoptimization in Direct Alignment Algorithms" (NeurIPS 2024) trained policies with DPO, IPO, SLiC on multiple datasets across KL budgets. The gold-reward-vs-KL curves have the same Gao et al. peak-and-collapse shape. The implicit reward queries out-of-distribution samples during training; KL regularization does not stabilize this.
> DAAs do not escape Goodhart. They change the surface where it bites from "reward model over-optimized" to "reference policy ratio over-optimized." The universal fix — better data, ensembles, early stopping — applies to both.

---

### Choosing among them (2026) · 怎么选（2026）

- 如果你有大量成对偏好数据：保守 beta 的 DPO；长度偏差明显就用 SimPO。
- 如果你只有非成对的二值反馈：KTO。
- 如果你想要从基座模型出发的单阶段流水线：ORPO。
- 如果你在 DPO 日志里看到 chosen 对数概率退化：BPO。
- 如果偏好强度差异很大且 DPO 已经饱和：IPO。

每个实验室都把这五个放在一组基准上跑，按任务挑赢家。数学推理和安全的最佳选择没有理由相同。

> - If you have large paired preference data: DPO with conservative beta, SimPO if length bias is evident.
> - If you have unpaired binary feedback: KTO.
> - If you want a single-stage pipeline from a base model: ORPO.
> - If you see degraded chosen log-probs in DPO logs: BPO.
> - If preference strengths vary widely and DPO is saturating: IPO.
> Every lab runs all five on a battery and picks the winner per task. There is no reason the optimum is the same for math reasoning and safety.

```figure
dpo-margin
```

---

## Use It · 实战用法

`code/main.py` 在一个玩具偏好数据集上比较六个损失（DPO、IPO、KTO、SimPO、ORPO、BPO），数据集中真实偏好强度逐对变化。每个损失都在同一个 500 对样本上用小型 softmax 策略优化。画出每个方法的最终胜率、chosen 对数概率漂移和隐式奖励散布。

> `code/main.py` compares six losses (DPO, IPO, KTO, SimPO, ORPO, BPO) on a toy preference dataset where the true preference strength varies by pair. Each loss is optimized against the same 500-pair sample with a small softmax policy. Plots final win rate, chosen-log-prob drift, and implicit-reward spread per method.

---

## Ship It · 交付

本课产出 `outputs/skill-preference-loss-selector.md`。给定数据集统计（成对 vs 非成对、偏好强度可变 vs 均匀、长度分布）和目标（单阶段或先 SFT 再偏好训练），推荐一个偏好损失并报告它防范的失败模式。

> This lesson produces `outputs/skill-preference-loss-selector.md`. Given dataset statistics (paired vs unpaired, variable vs uniform preference strength, length distribution) and a target (single-stage or SFT-then-preference), recommend a preference loss and report the failure mode it protects against.

---

## Exercises · 练习

1. 运行 `code/main.py`。报告 DPO 和 BPO 的最终 chosen 对数概率下降。BPO 应该保住更高的 chosen 绝对概率 —— 验证这一点。

2. 修改偏好数据，让所有对的强度相等。六个方法里哪个最稳健？哪个退化？解释 IPO 在这里的优势。

3. 让 rejected 响应平均比 chosen 长 2 倍。其他什么都不改，用数值展示 DPO 的长度利用和 SimPO 的修复。

4. Rafailov 等人（NeurIPS 2024）声称 DAA 会过度优化。复现一个单点版本：画出 chosen 减 rejected 的 KL 散度，观察大 beta 下 DPO 的过度优化。

5. 阅读 BPO 论文摘要（OpenReview b97EwMUWu7）。写下 BPO 加给 DPO 的那一行修正。对照 `code/main.py` 里的实现确认。

---

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|------------------------|
| DPO | "没有奖励模型的 RLHF" | 由 RLHF 闭式最优解导出的损失；只涉及策略参数 |
| Implicit reward | "那个对数比" | `beta * log(pi(y\|x) / pi_ref(y\|x))` —— DPO 蕴含的奖励 |
| IPO | "有界的 DPO" | 用恒等映射替换 log-sigmoid；隐式奖励差距被 `1/(2 beta)` 封顶 |
| KTO | "非成对的 DPO" | 在单个标签上用带损失厌恶的前景理论效用 |
| SimPO | "无参考的 DPO" | 长度归一化对数似然 + 间隔；没有参考策略 |
| ORPO | "单阶段的 DPO" | NLL + 几率比偏好项；从基座模型一遍训练完成 |
| BPO | "保 chosen 的 DPO" | DPO 加上对「降低 chosen 响应绝对对数概率」的惩罚 |
| Degraded Chosen | "chosen 掉下去了" | 只要 rejected 掉得更快，DPO 就会让 chosen 的对数概率下降 |
| DAA | "直接对齐算法" | 任何跳过显式 RM 的偏好损失方法 |

---

## Further Reading · 延伸阅读

- [Rafailov et al. — Direct Preference Optimization (NeurIPS 2023, arXiv:2305.18290)](https://arxiv.org/abs/2305.18290)
- [Azar et al. — A General Theoretical Paradigm to Understand Learning from Human Preferences (AISTATS 2024, arXiv:2310.12036)](https://arxiv.org/abs/2310.12036) —— 即 IPO
- [Ethayarajh et al. — KTO: Model Alignment as Prospect Theoretic Optimization (arXiv:2402.01306)](https://arxiv.org/abs/2402.01306)
- [Meng, Xia, Chen — SimPO (NeurIPS 2024, arXiv:2405.14734)](https://arxiv.org/abs/2405.14734)
- [Hong, Lee, Thorne — ORPO (EMNLP 2024, arXiv:2403.07691)](https://arxiv.org/abs/2403.07691)
- [BPO — Behavior Preservation Optimization (ICLR 2026 OpenReview b97EwMUWu7)](https://openreview.net/forum?id=b97EwMUWu7)
- [Rafailov et al. — Scaling Laws for RM Overoptimization in DAAs (NeurIPS 2024, arXiv:2406.02900)](https://arxiv.org/abs/2406.02900)
