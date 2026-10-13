# Differential Privacy for LLMs · 大语言模型的差分隐私（Differential Privacy）

> DP-SGD 仍是标准做法 —— 在梯度更新中注入噪声，提供形式化的 (epsilon, delta) 保证。它在算力、内存和效用上的开销都很可观；参数高效的 DP 微调（LoRA + DP-SGD）是 2025 年的常见配置（ACM 2025）。两套证据互相矛盾：基于金丝雀（canary）的成员推断（membership inference，Duan et al., 2024）报告对语言模型的攻击成功率有限；训练数据抽取（training-data extraction，Carlini et al., 2021; Nasr et al., 2025）却能恢复大量逐字记忆的内容。解决之道（arXiv:2503.06808，2025 年 3 月）：分歧在于度量的对象 —— 插入的金丝雀 vs「最易抽取」的数据。新的金丝雀设计让基于 loss 的 MIA 无需影子模型（shadow models），并完成了首次对「真实数据 + 真实 DP 保证」训练的大语言模型的非平凡 DP 审计。替代方案：PMixED（arXiv:2403.15638）—— 在推理时通过对 next-token 分布的专家混合实现隐私预测；DP 合成数据生成（Google Research 2024）。新兴攻击：Differential Privacy Reversal via LLM Feedback —— 置信度分数泄露。

> DP-SGD remains the standard — noise-injected gradient updates provide formal (epsilon, delta) guarantees. Overhead in compute, memory, and utility is substantial; parameter-efficient DP fine-tuning (LoRA + DP-SGD) is the common 2025 configuration (ACM 2025). Two bodies of evidence in tension: canary-based membership inference (Duan et al., 2024) reports limited success against language models; training-data extraction (Carlini et al., 2021; Nasr et al., 2025) recovers substantial verbatim memorization. Resolution (arXiv:2503.06808, March 2025): the gap is in what is measured — inserted canaries vs "most extractable" data. New canary designs enable loss-based MIA without shadow models and yield the first nontrivial DP audit of an LLM trained on real data with realistic DP guarantees. Alternatives: PMixED (arXiv:2403.15638) — private prediction at inference time via mixture of experts on next-token distributions; DP synthetic data generation (Google Research 2024). Emerging attack: Differential Privacy Reversal via LLM Feedback — confidence-score leakage.

**Type:** Build
**Languages:** Python (stdlib, DP-SGD noise-injection and ε-δ accountant demonstration)
**Prerequisites:** Phase 01 · 09 (information theory), Phase 10 · 01 (large-model training)
**Time:** ~60 minutes

---

## Learning Objectives · 学习目标

- 定义 (epsilon, delta)-差分隐私（differential privacy），说出 DP-SGD 的配方。
- 解释 2024-2025 年的矛盾：金丝雀 MIA 与训练数据抽取给出两幅不同的图景。
- 描述 PMixED，以及为什么推理时隐私预测是 DP 训练的一种替代方案。
- 描述 Differential Privacy Reversal via LLM Feedback 攻击。

> Define (epsilon, delta)-differential privacy and state the DP-SGD recipe.
> Explain the 2024-2025 tension: canary MIA vs training-data extraction give different pictures.
> Describe PMixED and why inference-time private prediction is an alternative to DP training.
> Describe the Differential Privacy Reversal via LLM Feedback attack.

---

## The Problem · 问题在哪

大语言模型会记忆。Carlini et al. 2021 证明生产级语言模型能按需逐字复现训练文本。DP 是形式化的防御：让训练做到「输出对任何单条训练样本都可证明地不敏感」。2024-2025 年的证据表明 DP-SGD 是必要的，但部署中使用的 ε 值未必匹配威胁模型（threat model）。

> LLMs memorize. Carlini et al. 2021 showed production language models reproduce verbatim training text on demand. DP is the formal defense: train so that the output is provably insensitive to any single training example. The 2024-2025 evidence shows DP-SGD is necessary but the deployed ε values may not match the threat model.

---

## The Concept · 概念

### (ε, δ)-differential privacy · (ε, δ)-差分隐私

一个随机化算法 M 是 (ε, δ)-DP 的，如果对任意两个只差一条样本的数据集 D 与 D'，以及任意事件 S：
P(M(D) in S) <= e^ε * P(M(D') in S) + δ。

解读：输出分布足够接近（接近程度由 ε 参数化），以至于任何单个个体的贡献都无法被可靠地推断出来 —— 除非允许以概率 δ 失效。

> A randomized algorithm M is (ε, δ)-DP if for any two datasets differing in one example and any event S:
> P(M(D) in S) <= e^ε * P(M(D') in S) + δ.
> Interpretation: the output distribution is close enough (parametrized by ε) that the contribution of any single individual cannot be reliably inferred, except with probability δ.

### DP-SGD

Abadi et al. 2016。标准配方：
1. 采样一个 mini-batch。
2. 计算逐样本（per-example）梯度。
3. 把每个逐样本梯度裁剪（clip）到阈值 C。
4. 对裁剪后的梯度求和，加入标准差为 σ * C 的高斯噪声。
5. 用带噪的和更新参数。

隐私代价由会计器（accountant）跟踪（Moments Accountant、Rényi DP accountant）。LLM 文献中报告的 ε 值因威胁模型、数据敏感度和效用目标不同而差异巨大；不存在普遍「安全」的默认 ε。已发表的例子在某些 LLM 训练设置中大致落在 ε ≈ 1–10，但这些只是示意 —— 不是推荐默认值。更低的 ε 通常需要更多噪声，并可能加大效用损失。

> Abadi et al. 2016. The standard recipe: sample a mini-batch, compute per-example gradients, clip each per-example gradient to a threshold C, sum the clipped gradients and add Gaussian noise with std σ * C, then use the noisy sum to update parameters.
> Privacy cost is tracked by an accountant (Moments Accountant, Rényi DP accountant). Reported ε values in the LLM literature vary widely by threat model, data sensitivity, and utility target; there is no universally "safe" default ε. Lower ε generally requires more noise and can increase utility loss.

### LoRA + DP-SGD

对前沿模型做完整的 DP-SGD 代价高得令人却步。LoRA（Hu et al. 2022）把梯度更新限制在一个小适配器（adapter）上，减少了逐样本梯度的存储开销。LoRA + DP-SGD 是 2025 年的常见配置。DP 保证只作用于适配器；基座模型保持不变。

> Full DP-SGD of a frontier model is prohibitive. LoRA (Hu et al. 2022) limits gradient updates to a small adapter, reducing per-example gradient storage. LoRA + DP-SGD is the common 2025 configuration. DP guarantees apply to the adapter; the base model is held fixed.

### The 2024-2025 tension · 2024-2025 年的矛盾

两套证据：

- **金丝雀 MIA（Duan et al. 2024）。** 把独一无二的金丝雀样本插入训练数据，测成员推断攻击者能否把它们识别出来。报告的成功率有限。暗示 MIA 很难。
- **训练数据抽取（Carlini 2021、Nasr et al. 2025）。** 用一个前缀提示模型；测它能否逐字恢复训练文本。报告了大量的记忆现象。暗示在相关意义上 MIA 很容易。

2025 年 3 月的解决（arXiv:2503.06808）：两者度量的东西不同。MIA 在插入的金丝雀上问「样本 e 在 D 里吗？」。抽取问的是「我能从 D 里恢复什么？」。对隐私真正要紧的是「最易抽取」的那个样本；金丝雀低估了它，因为金丝雀并没有为「易抽取」做优化。

新的金丝雀设计。无需影子模型、基于 loss 的 MIA。首次对真实数据、真实 DP 保证下的 LLM 做的非平凡 DP 审计。

> **Canary MIA (Duan et al. 2024).** Insert unique canaries into training data, measure whether a membership-inference attacker can identify them. Reports limited success on language models. Suggests MIA is hard.
> **Training-data extraction (Carlini 2021, Nasr et al. 2025).** Prompt the model with a prefix; measure whether it recovers verbatim text from training. Reports substantial memorization. Suggests MIA is easy in the relevant sense.
> March 2025 resolution (arXiv:2503.06808): the two measure different things. MIA asks "is example e in D?" on inserted canaries. Extraction asks "what can I recover of D?" The "most extractable" example is what matters for privacy; canaries under-report this because they are not optimized to be extractable.
> New canary designs. Loss-based MIA without shadow models. First nontrivial DP audit of an LLM on real data with realistic DP guarantees.

### Alternatives to DP training · DP 训练的替代方案

- **PMixED（arXiv:2403.15638）。** 推理时的隐私预测。在 next-token 分布上做专家混合（mixture of experts）；每个专家只看一份训练数据分片；聚合时加噪声以实现 DP。完全避开 DP 训练。
- **DP 合成数据生成（Google Research 2024）。** 用 DP-SGD 做 LoRA 微调，采样生成合成数据，再用合成数据训练下游分类器。

两者都绕开了完整 DP 训练的效用代价，代价是换了一个不同的威胁模型。

> **PMixED (arXiv:2403.15638).** Private prediction at inference time. Mixture of experts on next-token distributions; each expert sees a shard of training data; aggregation adds noise for DP. Avoids DP training entirely.
> **DP synthetic data generation (Google Research 2024).** LoRA-fine-tune with DP-SGD, sample synthetic data, train a downstream classifier on the synthetic data.
> Both sidestep the utility cost of full DP training at the cost of a different threat model.

### Differential Privacy Reversal via LLM Feedback · 经 LLM 反馈的差分隐私反转

2025 年新兴攻击。把 DP 训练模型的置信度分数当作预言机（oracle），用来重新识别个体。即使输出本身不泄露，置信度分布也可能泄露。

防御：不要暴露置信度，或者在暴露之前先截断/量化。这是 (ε, δ)-DP 训练之外的又一项要求。

> Emerging 2025 attack. Use a DP-trained model's confidence scores as an oracle to re-identify individuals. Even when outputs do not leak, confidence distributions can.
> The defense: do not expose confidences, or truncate/quantize them before exposure. This is an additional requirement beyond (ε, δ)-DP training.

### Where this fits in Phase 18 · 在 Phase 18 中的位置

第 20-21 课是偏见/公平。第 22 课是隐私。第 23 课是通过水印（watermarking）实现来源验证（provenance）。第 27 课讲监管层面的数据来源治理。

```figure
an-dp-clip-noise
```

---

## Use It · 实战用法

`code/main.py` 在一个玩具二分类数据集上模拟 DP-SGD。你可以扫描噪声乘子 σ 和裁剪范数 C，跟踪 (ε, δ) 预算和准确率代价。「金丝雀攻击」会插入一条独一无二的训练样本，测 log-loss 检验在 DP 之前和之后能否把它检测出来。

> `code/main.py` simulates DP-SGD on a toy binary-classification dataset. You can sweep the noise multiplier σ and the clipping norm C and track the (ε, δ) budget and the accuracy cost. A "canary attack" inserts a unique training example and measures whether a log-loss test can detect it before and after DP.

---

## Ship It · 交付

本课产出 `outputs/skill-dp-audit.md`。给定一个语言模型部署上的 DP 主张，它会审计：(ε, δ) 数值、所用会计器、MIA 评估协议，以及是否评估过置信度暴露向量。

> This lesson produces `outputs/skill-dp-audit.md`. Given a DP claim on a language model deployment, it audits: the (ε, δ) values, the accountant used, the MIA evaluation protocol, and whether confidence-exposure vectors have been assessed.

---

## Exercises · 练习

1. 运行 `code/main.py`。扫描 σ ∈ {0.5, 1.0, 2.0}，报告 (ε, δ)-准确率的取舍。找出效用崩塌的临界点。

2. 实现金丝雀插入和 log-loss 检验。测 σ = 1.0 时 DP-SGD 前后的检测率。

3. 阅读 Nasr et al. 2025 关于训练数据抽取的工作。为什么中等强度的 ε 之下抽取仍然能成功？这对「把 MIA 当评估手段」意味着什么？

4. 设计一个完全在推理时运行的、使用 PMixED（arXiv:2403.15638）的部署。PMixED 应对了哪个 DP-SGD 没有应对的威胁模型？

5. 草拟 DP Reversal via LLM Feedback 攻击。设计一个限制置信度分数泄露的对策，并估计其部署成本。

> 1. Run `code/main.py`. Sweep σ in {0.5, 1.0, 2.0} and report the (ε, δ)-accuracy trade-off. Identify the point at which utility collapses.
> 2. Implement a canary insertion and a log-loss test. Measure detection rate before and after DP-SGD at σ = 1.0.
> 3. Read Nasr et al. 2025 on training-data extraction. Why does extraction success not collapse under moderate ε? What does this imply about MIA-as-evaluation?
> 4. Design a deployment using PMixED (arXiv:2403.15638) that operates entirely at inference time. What is the threat model that PMixED addresses that DP-SGD does not?
> 5. Sketch the DP Reversal via LLM Feedback attack. Design a countermeasure that limits confidence-score leakage and estimate its deployment cost.

---

## Key Terms · 术语表

| 术语 | 大家常说 | 实际含义 |
|------|-----------------|------------------------|
| DP | 「(ε, δ)-差分隐私」 | 形式化隐私：相邻数据集变化下输出分布相近 |
| DP-SGD | 「注入噪声的 SGD」 | 梯度裁剪 + 高斯噪声注入；标准 DP 训练 |
| LoRA + DP-SGD | 「高效的隐私微调」 | 在低秩适配器上做 DP-SGD；2025 年标准配置 |
| MIA | 「成员推断」 | 判断某条样本是否在训练数据中的攻击 |
| Canary | 「插入的水印样本」 | 用于度量 DP 泄露的独特训练样本 |
| PMixED | 「隐私推理混合」 | 通过 next-token 分布的专家混合在推理时实现 DP |
| DP Reversal | 「置信度泄露攻击」 | 用模型置信度当预言机做重识别的攻击 |

---

## Further Reading · 延伸阅读

- [Abadi et al. — DP-SGD (arXiv:1607.00133)](https://arxiv.org/abs/1607.00133) —— 标准 DP 训练算法
- [Carlini et al. — Extracting Training Data (arXiv:2012.07805)](https://arxiv.org/abs/2012.07805) —— 抽取攻击的奠基论文
- [Duan et al. — Canary MIA on LLMs (arXiv:2402.07841, 2024)](https://arxiv.org/abs/2402.07841) —— 成功率有限的 MIA
- [Kowalczyk et al. — Auditing DP for LLMs (arXiv:2503.06808, March 2025)](https://arxiv.org/abs/2503.06808) —— 对上述矛盾的解决
- [PMixED (arXiv:2403.15638)](https://arxiv.org/abs/2403.15638) —— 推理时隐私预测
