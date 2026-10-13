# Fairness Criteria — Group, Individual, Counterfactual · 公平性准则：群体、个体与反事实

> 公平性文献由三大家族撑起。群体公平（group fairness）：demographic parity、equalized odds、conditional use accuracy equality —— 各受保护群体的比率在平均意义上相等。个体公平（individual fairness，Dwork et al. 2012）：相似的个体获得相似的决策，即决策映射上的 Lipschitz 条件。反事实公平（counterfactual fairness，Kusner et al. 2017）：如果把一个个体的敏感属性做反事实改变后决策不变，那么这个决策对他是公平的。2024 年的理论结果（NeurIPS 2024）：反事实公平与准确率之间存在固有权衡；一种模型无关方法能把「最优但不公平」的预测器转换为反事实公平的预测器，准确率损失有界。回溯反事实（backtracking counterfactuals，arXiv:2401.13935，2024 年 1 月）：一种新范式，避免对法律保护属性做干预。哲学调和（ICLR Blogposts 2024）：在因果图下，满足某些群体公平性度量会蕴含反事实公平。

> Three families structure the fairness literature. Group fairness: demographic parity, equalized odds, conditional use accuracy equality — equal rates across protected groups on average. Individual fairness (Dwork et al. 2012): similar individuals receive similar decisions; Lipschitz condition on the decision map. Counterfactual fairness (Kusner et al. 2017): a decision is fair to an individual if it is unchanged when sensitive attributes are counterfactually altered. 2024 theoretical result (NeurIPS 2024): there is an inherent CF-vs-accuracy trade-off; a model-agnostic method converts an optimal-but-unfair predictor into a CF one with bounded accuracy loss. Backtracking counterfactuals (arXiv:2401.13935, January 2024): new paradigm that avoids requiring interventions on legally protected attributes. Philosophical reconciliation (ICLR Blogposts 2024): with causal graphs, satisfying certain group fairness measures entails counterfactual fairness.

**Type:** Learn
**Languages:** Python (stdlib, three-criteria comparison)
**Prerequisites:** Phase 18 · 20 (bias), Phase 02 (classical ML)
**Time:** ~60 minutes

---

## Learning Objectives · 学习目标

- 说出三种群体公平准则（demographic parity、equalized odds、conditional use accuracy equality）以及一个不可能性结果。
- 用 Dwork et al. 2012 的 Lipschitz 形式化描述个体公平。
- 描述反事实公平及其对因果图的依赖。
- 解释回溯反事实（backtracking counterfactuals），以及它为什么绕开了「对受保护属性做干预」的难题。

> State the three group-fairness criteria (demographic parity, equalized odds, conditional use accuracy equality) and one impossibility result.
> Describe individual fairness via the Dwork et al. 2012 Lipschitz formulation.
> Describe counterfactual fairness and its causal-graph dependency.
> Explain backtracking counterfactuals and why they sidestep the intervention-on-protected-attribute problem.

---

## The Problem · 问题在哪

第 20 课讲的是如何度量偏见。第 21 课要定义的是度量所服务的公平性标准。三大家族给出结构上不同的标准 —— 一个模型可以群体公平却个体不公平，也可以反事实公平却群体不公平。选择标准是一个政策决定；没有任何标准是普遍最优的。

> Lesson 20 was about measuring bias. Lesson 21 is about defining the fairness standard the measurement should serve. The three families give structurally different standards — a model can be group-fair and individual-unfair, counterfactually fair and group-unfair. Choosing a standard is a policy decision; no standard is universally optimal.

---

## The Concept · 概念

### Group fairness · 群体公平

- **Demographic parity（人口平等）。** P(Y=1 | A=a) = P(Y=1 | A=a') 对所有群体成立。接受率相等。
- **Equalized odds（均等几率）。** P(Y=1 | Y*=y, A=a) = P(Y=1 | Y*=y, A=a')。各群体的 TPR 与 FPR 相等。
- **Conditional use accuracy equality（条件使用精度平等）。** P(Y*=y | Y=y, A=a) = P(Y*=y | Y=y, A=a')。各群体的预测值相等。

不可能性结果（Chouldechova；Kleinberg-Mullainathan-Raghavan 2017）：在基础率（base rate）不相等时，这三条不可能同时满足。

> **Demographic parity.** P(Y=1 | A=a) = P(Y=1 | A=a') for all groups. Equal acceptance rates.
> **Equalized odds.** P(Y=1 | Y*=y, A=a) = P(Y=1 | Y*=y, A=a'). Equal TPR and FPR across groups.
> **Conditional use accuracy equality.** P(Y*=y | Y=y, A=a) = P(Y*=y | Y=y, A=a'). Equal predictive value across groups.
> Impossibility (Chouldechova, Kleinberg-Mullainathan-Raghavan 2017): these three cannot be satisfied simultaneously under unequal base rates.

### Individual fairness · 个体公平

Dwork et al. 2012。如果存在 Lipschitz 常数 L，使得 |f(x) - f(x')| <= L * d(x, x')，那么决策映射 f 关于任务特定的相似度度量 d 是个体公平的。相似的个体得到相似的决策。

难点在于定义 d。这是政策问题，不是统计问题。

> Dwork et al. 2012. A decision map f is individually fair with respect to a task-specific similarity metric d if |f(x) - f(x')| <= L * d(x, x') for some Lipschitz constant L. Similar individuals get similar decisions.
> Requires defining d. Policy question, not statistical.

### Counterfactual fairness · 反事实公平

Kusner et al. 2017。在总体的一个因果模型下，如果把个体 i 的敏感属性做反事实改变后其决策不变，那么该决策对个体 i 是反事实公平的。

这需要一个因果 DAG。而 DAG 本身是一种建模选择。反事实公平的正当性有多强，完全取决于那个 DAG。

> Kusner et al. 2017. A decision is counterfactually fair to individual i if, under a causal model of the population, the decision is unchanged when i's sensitive attributes are counterfactually altered.
> Requires a causal DAG. The DAG is a modeling choice. Counterfactual fairness is only as justified as the DAG.

### The CF-vs-accuracy trade-off · 反事实公平与准确率的取舍

NeurIPS 2024 理论结果：反事实公平与预测准确率之间存在固有权衡。一种模型无关（model-agnostic）方法可以把一个「最优但不公平」的预测器转换为反事实公平的预测器，代价是准确率损失有界。损失的大小取决于最优不公平预测器中敏感属性系数的量级。

> NeurIPS 2024 theoretical: there is an inherent trade-off between counterfactual fairness and predictive accuracy. A model-agnostic method can convert an optimal-but-unfair predictor into a CF one, at a bounded accuracy cost. The accuracy cost depends on the magnitude of the sensitive-attribute coefficient in the optimal unfair predictor.

### Backtracking counterfactuals · 回溯反事实

arXiv:2401.13935（2024 年 1 月）。传统反事实要求对敏感属性做干预 —— 「如果这个人是另一种性别，决策会变吗」。这在法律上有问题：在分类法（classification law）下，受保护属性不容许被干预。

回溯反事实把方向反过来：不去干预属性，而是问「该个体实际特征的哪种组合本可以产生那个反事实结果」。这就绕开了法律上的反对意见。

> arXiv:2401.13935 (January 2024). Traditional counterfactuals require interventions on the sensitive attribute — "would the decision change if this person had been a different gender." Legally, this is problematic: protected attributes cannot be intervened on in classification law.
> Backtracking counterfactuals flip the direction: instead of intervening on the attribute, ask what combination of the individual's actual features would have produced the counterfactual outcome. This sidesteps the legal objection.

### Philosophical reconciliation · 哲学层面的调和

ICLR Blogposts 2024。只要手里有因果图，满足某些群体公平性度量就会蕴含反事实公平。三大家族并不正交；它们是同一个底层因果结构的不同侧面。

这并没有解决不可能性定理（基础率不等仍然让群体公平无法同时满足）。但它说明：「群体」与「个体 / 反事实」之间的表面对立，部分上是没有把因果模型讲清楚所造成的人为假象。

> ICLR Blogposts 2024. With a causal graph in hand, satisfying certain group-fairness measures entails counterfactual fairness. The three families are not orthogonal; they are different facets of the same underlying causal structure.
> This does not resolve the impossibility theorems (unequal base rates still prevent simultaneous group fairness). But it shows the apparent opposition between "group" and "individual / counterfactual" is partially an artifact of not being explicit about the causal model.

### Where this fits in Phase 18 · 在 Phase 18 中的位置

第 20 课是偏见度量。第 21 课是公平性定义。第 22 课是隐私（差分隐私（differential privacy））。第 23 课是水印（watermarking）。这些是与「分配」相邻的课程，与第 7-11 课那些与「欺骗」相邻的课程互补。

```figure
an-fairness-trilemma
```

---

## Use It · 实战用法

`code/main.py` 构建一个带敏感属性、基础率不等的玩具二分类数据集。在一个简单分类器上计算 demographic parity、equalized odds 和 conditional use accuracy equality，观察三个指标互相不一致。再施加面向 demographic parity 的重加权（re-weighting），观察它在另外两个指标上的代价。

> `code/main.py` builds a toy binary-classification dataset with a sensitive attribute and unequal base rates. Compute demographic parity, equalized odds, and conditional use accuracy equality on a simple classifier. Observe the three metrics disagreeing. Apply a re-weighting for demographic parity and observe its cost on the other two.

---

## Ship It · 交付

本课产出 `outputs/skill-fairness-criterion.md`。给定一个公平性主张或政策，它会识别出：被主张的是哪条准则；在所主张的不等基础率下，模型能否同时满足其余准则；该主张依赖什么样的因果 DAG。

> This lesson produces `outputs/skill-fairness-criterion.md`. Given a fairness claim or policy, identifies which criterion is being claimed, whether the model can satisfy the remaining criteria under the claimed unequal base rates, and what causal DAG the claim depends on.

---

## Exercises · 练习

1. 运行 `code/main.py`。报告默认数据上的三个群体指标。施加面向 demographic parity 的重加权后重新报告。

2. 用非敏感特征上的 L2 距离实现 Dwork et al. 2012 的个体公平度量。报告在 Lipschitz 常数 L=1 下有多少对样本违反条件。

3. 阅读 Kusner et al. 2017。为简历评分构建一个简单的双特征因果 DAG，并指出它蕴含的反事实公平条件。

4. 2024 年的回溯反事实论文避免了对受保护属性的干预。描述一个这对法律合规有影响的场景。

5. ICLR 2024 的调和论证认为群体公平与反事实公平是同一结构的两个侧面。从 `code/main.py` 的三条准则中任选两条，写出使它们等价的因果假设。

> 1. Run `code/main.py`. Report the three group metrics on the default data. Apply the demographic-parity-targeted re-weighting and re-report.
> 2. Implement the Dwork et al. 2012 individual-fairness metric using L2 on non-sensitive features. Report how many pairs violate Lipschitz with constant L=1.
> 3. Read Kusner et al. 2017. Construct a simple two-feature causal DAG for resume scoring and identify the counterfactual-fairness condition it implies.
> 4. The 2024 backtracking-counterfactuals paper avoids intervention on protected attributes. Describe a scenario where this matters for legal compliance.
> 5. The ICLR 2024 reconciliation argues group and counterfactual fairness are facets of the same structure. Pick two of the three criteria in `code/main.py` and state the causal assumption that would make them equivalent.

---

## Key Terms · 术语表

| 术语 | 大家常说 | 实际含义 |
|------|-----------------|------------------------|
| Demographic parity | 「各群体比率相等」 | P(Y=1 | A=a) 在各群体间相等 |
| Equalized odds | 「TPR/FPR 相等」 | 各群体间真正例率与假正例率相等 |
| Conditional use accuracy | 「PPV/NPV 相等」 | 各群体间预测值相等 |
| Individual fairness | 「Lipschitz 条件」 | 相似的个体得到相似的决策 |
| Counterfactual fairness | 「反事实属性改变下的不变性」 | 反事实改变敏感属性后决策不变 |
| Backtracking counterfactual | 「用实际特征反向解释」 | 从结果反推、而非从属性正推的反事实 |
| Impossibility theorem | 「三条准则互相冲突」 | Chouldechova / KMR 2017：基础率不等时群体准则互斥 |

---

## Further Reading · 延伸阅读

- [Dwork et al. — Fairness through Awareness (arXiv:1104.3913)](https://arxiv.org/abs/1104.3913) —— 个体公平
- [Kusner, Loftus, Russell, Silva — Counterfactual Fairness (arXiv:1703.06856)](https://arxiv.org/abs/1703.06856) —— 反事实公平
- [Chouldechova — Fair prediction with disparate impact (arXiv:1703.00056)](https://arxiv.org/abs/1703.00056) —— 不可能性结果
- [Backtracking Counterfactuals (arXiv:2401.13935)](https://arxiv.org/abs/2401.13935) —— 受保护属性干预问题的新范式
