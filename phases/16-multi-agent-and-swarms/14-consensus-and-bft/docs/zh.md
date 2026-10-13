# 面向 agent 的共识与拜占庭容错（Consensus and Byzantine Fault Tolerance for Agents）

> 经典分布式系统的拜占庭容错（BFT）遇上了随机性的 LLM。2025-2026 年出现了三个研究方向：**CP-WBFT**（arXiv:2511.10400）用置信度探针给每张选票加权；**DecentLLMs**（arXiv:2507.14928）走向无领导（leaderless），由并行的 worker 提案加几何中位数（geometric-median）聚合；**WBFT**（arXiv:2505.05103）把加权投票与层级结构聚类（Hierarchical Structure Clustering）结合，切分出 Core 与 Edge 节点。"Can AI Agents Agree?"（arXiv:2603.01213）给出的诚实实证结论是：如今连标量上的一致（agreement）都是脆弱的——单个欺骗性 agent 就能破坏一个 Mixture-of-Agents。BFT 是必要的，但不充分。本课构建一个最小 BFT 协议，注入三种 agent 特有的攻击（拜占庭谎言、谄媚式从众、相关错误的单一化），并度量每种共识变体如何应对。

> Classical distributed-systems BFT meets stochastic LLMs. In 2025-2026 three research directions emerged: **CP-WBFT** (arXiv:2511.10400) weighs each vote by a confidence probe; **DecentLLMs** (arXiv:2507.14928) goes leaderless with parallel worker proposals and geometric-median aggregation; **WBFT** (arXiv:2505.05103) combines weighted voting with Hierarchical Structure Clustering to split Core and Edge nodes. The honest empirical result from "Can AI Agents Agree?" (arXiv:2603.01213) is that even scalar agreement is fragile today — a single deceptive agent can compromise a Mixture-of-Agents. BFT is necessary but not sufficient. This lesson builds a minimal BFT protocol, injects three agent-specific attacks (byzantine lie, sycophantic conformity, correlated-error monoculture), and measures how each consensus variant copes.

**Type:** Learn + Build
**Languages:** Python（stdlib）
**Prerequisites:** Phase 16 · 07（Society of Mind and Debate）、Phase 16 · 13（Shared Memory）
**Time:** ~75 分钟

## Problem · 问题

你有 N 个 LLM agent，各自产出答案。它们意见不一。多数投票选中了错的那个，因为其中两个 agent 是相关的（相同的基础模型、相同的训练数据、相同的失败模式）。第三个 agent 恰好以一种新颖的方式出错——于是多数成了假多数。

现在再加一个欺骗性 agent：它故意撒谎。或者一个谄媚性 agent：它附和最后发言的人。在经典 BFT 中，假设是拜占庭节点占比 `f < n/3` 且行为任意。而 2026 年的现实是：LLM 节点即使在诚实时也是随机的、跨模型相关的、并且会被彼此的输出影响。你不能把它们当作独立的伯努利投票者。

经典 BFT（PBFT，1999）没有错——它只是不完整。它能处理任意的比特翻转，却处理不了「三个诚实 agent 因为共享训练数据而共享同一个幻觉」。本课从 PBFT 的地基出发，叠加三种 2025-2026 年的适配。

> You have N LLM agents each producing an answer. They disagree. Majority vote picks the wrong one because two agents are correlated (same base model, same training data, same failure modes). A third agent happens to be wrong in a novel way — so the majority is a false majority.
> Now add a deceptive agent: it lies on purpose. Or a sycophantic agent: it agrees with whoever spoke last. In classical BFT, the assumption is that Byzantine nodes are a fraction `f < n/3` and behave arbitrarily. The 2026 reality is that LLM nodes are stochastic even when honest, correlated across models, and influenced by each other's outputs. You cannot treat them as independent Bernoulli voters.
> Classical BFT (PBFT, 1999) is not wrong — it is incomplete. It handles arbitrary bit-flipping. It does not handle "three honest agents share a hallucination because they share training data." This lesson builds from PBFT's foundation and layers on three 2025-2026 adaptations.

## Concept · 概念

### What classical BFT gives you · 经典 BFT 给你什么

实用拜占庭容错（Practical Byzantine Fault Tolerance，Castro & Liskov，OSDI 1999）能容忍 `f < n/3` 的拜占庭节点。协议有三个阶段（pre-prepare、prepare、commit）和两个原语（签名消息、法定证书 quorum certificate）。在 `n >= 3f + 1` 个或诚实或恶意的节点之间就单一取值达成一致。

它的保证很强，但前提是：

1. **故障相互独立。** 拜占庭节点之间不协作。
2. **诚实节点真的诚实。** 诚实输出的正确性不是问题；协议只负责对齐分歧。
3. **问题存在真值答案。** 就一个错误的事实达成共识仍然是共识。

LLM agent 把这三条全违反了。跑在相同基础模型上的两个 agent 共享故障。一个「诚实」的 LLM 依然会幻觉。而在模糊问题上，「真相」就是 agent 们决定的东西——没有外部 oracle。

> Practical Byzantine Fault Tolerance (Castro & Liskov, OSDI 1999) tolerates `f < n/3` Byzantine nodes. The protocol has three phases (pre-prepare, prepare, commit) and two primitives (signed messages, quorum certificates). Agreement on a single value among `n >= 3f + 1` honest-or-malicious nodes.
> The guarantees are strong but assume:
> 1. **Independent faults.** Byzantines do not coordinate.
> 2. **Honest nodes are truly honest.** Correctness of honest outputs is a non-issue; the protocol only aligns disagreement.
> 3. **The question has a ground-truth answer.** Consensus on a wrong fact is still consensus.
> LLM agents violate all three. Two agents running the same base model share faults. An "honest" LLM still hallucinates. And on ambiguous questions, the "truth" is what the agents decide — there is no external oracle.

### The three LLM-specific attacks · 三种 LLM 特有攻击

**拜占庭谎言（Byzantine lie）。** 一个 agent 输出故意错误的答案。若 `f < n/3`，经典 BFT 能处理它。

**谄媚式从众（sycophantic conformity）。** 一个 agent 在投票前先读别人的答案，并附和最后发言者。并非恶意，但与最响亮的声音相关。经典 BFT 防不住它，因为这个 agent 能通过所有签名检查。

**相关错误的单一化（correlated-error monoculture）。** 三个 agent 共享同一个基础模型。它们幻觉出同一个错误答案。多数是错的。经典 BFT 帮不上忙，因为三者是「诚实地」一致的。

> **Byzantine lie.** One agent outputs a deliberately wrong answer. Classical BFT handles this if `f < n/3`.
> **Sycophantic conformity.** One agent reads others' answers before voting and aligns with whoever spoke last. Not malicious, but correlates with the loudest voice. Classical BFT does not prevent this because the agent passes every signature check.
> **Correlated-error monoculture.** Three agents share a base model. They hallucinate the same wrong answer. The majority is wrong. Classical BFT does not help because all three "honestly" agree.

### The 2025-2026 responses · 2025-2026 年的三种回应

**CP-WBFT**（arXiv:2511.10400）—— 置信度探针加权 BFT（Confidence-Probed Weighted BFT）。每个投票者给答案附加一个置信度探针（自报概率，或独立校准模型的预测）。选票权重随置信度缩放。报告在完全图上有 +85.71% 的 BFT 提升。缓解对象：谄媚式从众（从众的 agent 对自己主动选定的立场往往置信度低）。

**DecentLLMs**（arXiv:2507.14928）—— 无领导（leaderless）。worker agent 并行提案，evaluator agent 给提案打分，最终答案是得分位置的几何中位数。在 `f < n/2` 时稳健。缓解对象：拜占庭谎言与相关错误（几何中位数对离群值稳健，并拉向密集簇，而不是被模型偏差影响的平均值）。

**WBFT**（arXiv:2505.05103）—— 带层级结构聚类的加权 BFT。选票权重由回答质量加上从历史学到的信任分决定。把 agent 聚类成 Core 与 Edge；Core agent 先达成共识，Edge agent 跟随。缓解对象：可扩展性（Core 共识小而快），以及部分缓解单一化（Core 可以按多样性挑选）。

> **CP-WBFT** (arXiv:2511.10400) — Confidence-Probed Weighted BFT. Each voter attaches a confidence probe to its answer (a self-reported probability, or a separate calibration model's prediction). Vote weights scale with confidence. Reported +85.71% BFT improvement on complete graphs. Mitigation for: sycophantic conformity (conforming agents tend to have low confidence on their volunteered position).
> **DecentLLMs** (arXiv:2507.14928) — Leaderless. Worker agents propose in parallel, evaluator agents score proposals, final answer is the geometric median of scored positions. Robust when `f < n/2`. Mitigation for: Byzantine lie and correlated errors (geometric median is robust to outliers and pulls toward the dense cluster, not the model-biased average).
> **WBFT** (arXiv:2505.05103) — Weighted BFT with Hierarchical Structure Clustering. Vote weights are assigned by response quality plus a trust score learned from history. Cluster agents into Core and Edge; Core agents must achieve consensus first, Edge agents follow. Mitigation for: scalability (Core consensus is small and fast) and partially for monoculture (Core can be chosen for diversity).

### Empirical: "Can AI Agents Agree?" (arXiv:2603.01213) · 实证："Can AI Agents Agree?"

该论文测量了多个前沿模型之间 LLM agent 在标量上的一致性（对同一个数值达成一致）。结论令人不安：

- 即使没有对手，LLM agent 在标量问题上的分歧率在许多基准上超过 30%。
- 单个采用欺骗性人格的 agent 能把 Mixture-of-Agents 的共识拉离诚实基线 40 多个百分点。
- 分歧率与模型多样性相关——异构集成比同构集成分歧更多（好事：错误不相关），但收敛也更慢（坏事：达成一致的时间更长）。

要点是：BFT 给你对齐输出的机制，但它不告诉你对齐后的输出是否正确。要配合验证（Phase 16 · 08 角色专门化）、多样性（Phase 16 · 15 辩论变体）和评估 agent（Phase 16 · 24 基准）一起用。

> The paper measures scalar agreement (LLM agents agreeing on a single numeric value) across multiple frontier models. The finding is uncomfortable:
> - Even with no adversaries, LLM agents disagree on scalar questions at rates above 30% on many benchmarks.
> - A single agent that adopts a deceptive persona can pull the Mixture-of-Agents consensus 40+ percentage points off the honest baseline.
> - Disagreement rates correlate with model diversity — heterogeneous ensembles disagree more than homogeneous ones (good: uncorrelated errors) but also drift more slowly (bad: longer time-to-agreement).
> The takeaway: BFT gives you machinery to align outputs, but it does not tell you whether the aligned output is right. Combine with verification (Phase 16 · 08 role specialization), diversity (Phase 16 · 15 debate variants), and evaluator agents (Phase 16 · 24 benchmarks).

### The core protocol, stripped down · 核心协议的极简版

面向 LLM agent 的一个最小 BFT 轮次：

```
1. task arrives; each agent i produces answer a_i
2. each agent attaches confidence probe c_i in [0, 1]
3. aggregator collects (a_i, c_i) from all n agents
4. aggregator groups by semantic cluster (equivalent answers)
5. aggregator computes weight for each cluster C:
     w(C) = sum_{i in C} c_i
6. winner = cluster with max weight, if max > threshold * sum(c_i)
   else: retry or escalate
7. minority clusters logged with provenance for post-hoc audit
```

语义聚类这一步是 LLM 特有的关键改动。「该研究报告 4.2%」和「4.2% 提升」这两个答案属于同一个簇。朴素的字符串相等检查会漏掉这一点。生产中用一个便宜的 embedding 模型或显式的规范化（canonicalization）。

> A minimal BFT round for LLM agents:
> The semantic clustering step is the LLM-specific twist. Two answers "the study reports 4.2%" and "4.2% improvement" are the same cluster. A naive string-equality check would miss this. In production, use a cheap embedding model or explicit canonicalization.

### Threshold tuning · 阈值调节

`threshold` 参数决定什么时候接受、什么时候重试。太低：你会接受弱势多数。太高：你什么也不接受。经验范围：`n=5-7` 个 agent 时取 0.5-0.67，更小的 `n` 则取更高。低于阈值时，升级给人类或另一组 agent 集成。

> The `threshold` parameter decides when to accept and when to retry. Too low: you accept weak majorities. Too high: you never accept anything. Empirical range: 0.5-0.67 for `n=5-7` agents, higher for smaller `n`. Below a threshold, escalate to a human or to a different agent ensemble.

### Where consensus does not help · 共识帮不上忙的地方

- **模糊问题。** 如果问题没有真值，共识只是一种意见。就叫它意见。
- **复合问题。** 「写代码并解释」——两个答案。对每一个独立投票。
- **对抗性多轮。** 如果 agent 能观察之前轮次并模仿（Du 2023 辩论），它们会开始不顾真相地互相附和。给轮次设上限（通常 2-3 轮）。

> - **Ambiguous questions.** If the question has no ground truth, consensus is an opinion. Call it that.
> - **Compound questions.** "Write code and explain it" — two answers. Vote on each independently.
> - **Adversarial multi-round.** If agents can observe prior rounds and mimic (Du 2023 debate), they start agreeing with each other regardless of truth. Bound the rounds (2-3 typically).

```figure
swarm-consensus-wave
```

## Build It · 动手造

`code/main.py` 实现：

- `AgentVoter` —— 一个带 (answer, confidence) 的脚本化策略。
- `MajorityVote` —— 经典简单多数。
- `CPWBFT` —— 带语义聚类的置信度加权投票。
- `DecentLLMs` —— 对打分提案做几何中位数聚合。
- `Scenario` —— 在三种攻击模式下运行每个聚合器。

实现的攻击模式：

1. `byzantine`：一个 agent 高置信度地说谎。
2. `sycophancy`：一个 agent 抄它看到的第一个答案，置信度也照抄。
3. `monoculture`：三个 agent 共享同一个错误答案（相关错误），置信度中等。

运行：

```
python3 code/main.py
```

预期输出：一张 (attack, aggregator) → final answer 的表，正确答案高亮。简单多数在 monoculture 情形上失败。CPWBFT 的置信度加权缓解谄媚。DecentLLMs 的几何中位数在 monoculture 不足半数时拉向诚实簇。

> `code/main.py` implements:
> - `AgentVoter` — a scripted policy with (answer, confidence).
> - `MajorityVote` — classical plurality.
> - `CPWBFT` — confidence-weighted voting with semantic clustering.
> - `DecentLLMs` — geometric-median aggregation on scored proposals.
> - `Scenario` — runs each aggregator under three attack patterns.
> Attack patterns implemented:
> 1. `byzantine`: one agent lies with high confidence.
> 2. `sycophancy`: one agent copies the first answer it sees, with matching confidence.
> 3. `monoculture`: three agents share a wrong answer (correlated error) with moderate confidence.
> Expected output: a table of (attack, aggregator) -> final answer, with the correct answer highlighted. Plurality fails the monoculture case. CPWBFT's confidence weighting mitigates sycophancy. DecentLLMs' geometric-median pulls toward the honest cluster when monoculture is less than half the population.

## Use It · 实战用法

`outputs/skill-consensus-designer.md` 为多 agent 集成设计共识协议：聚类方法、加权、阈值，以及低于阈值轮次的升级策略。

> `outputs/skill-consensus-designer.md` designs a consensus protocol for a multi-agent ensemble: clustering method, weighting, threshold, and the escalation policy for sub-threshold rounds.

## Ship It · 交付

上线任何共识机制之前：

- **至少用上面三种模式做攻击测试。** 你的协议应该可预测地失败，而不是无声地失败。
- **记录每个少数簇**及其来源。少数簇是相关错误的预警系统。
- **强制轮次有界。** 不要「一直辩论到达成一致」——那是在奖励谄媚。
- **把一致与正确分开。** 共识的输出交给验证器；验证器独立于这个集成。
- **监控一致率。** 骤升意味着从众偏差；骤降意味着模型漂移。

> Before shipping any consensus mechanism:
> - **Attack-test with at least the three patterns** above. Your protocol should fail predictably, not silently.
> - **Log every minority cluster** with provenance. Minority clusters are your early-warning system for correlated errors.
> - **Enforce bounded rounds.** No "keep debating until agreement" — that rewards sycophancy.
> - **Separate agreement from correctness.** Consensus output goes to a verifier; verifier is independent of the ensemble.
> - **Monitor the agreement rate.** A sharp rise means conformity bias; a sharp fall means model drift.

## Exercises · 练习

1. 运行 `code/main.py`。确认简单多数在 monoculture 攻击上失败，而 CPWBFT 在 monoculture 置信度低于 0.7 时能部分缓解。
2. 加第四种攻击模式：**沉默弃权（silent abstention）**——一个 agent 拒绝回答（"I don't know"）。每个聚合器应该怎么处理弃权？实现你的选择。
3. 把语义聚类从字符串规范化换成 embedding 相似度（用任意开源 embedding 模型）。谄媚攻击会怎样？
4. 阅读 CP-WBFT（arXiv:2511.10400）。实现置信度探针的校准步骤（用一个独立的校准模型核查每个 agent 自报的置信度）。在 monoculture 场景上测量准确率提升。
5. 阅读 "Can AI Agents Agree?"（arXiv:2603.01213）。复现一个简化的标量一致性实验：三个 agent、一个标量问题、欺骗性人格提示。CPWBFT 和 DecentLLMs 能抓住它吗？

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| BFT | "拜占庭容错" | Castro-Liskov 1999 年的共识协议，容忍 `f < n/3` 的任意故障。 |
| Byzantine | "任何坏行为" | 能撒谎、丢消息、静默失效的节点——除了安全崩溃之外的任何行为。 |
| Confidence probe | "你有多确定？" | 附在选票上的自报或校准器预测的概率。 |
| Semantic clustering | "同一个答案，不同的说法" | 在计票前把等价答案分组。 |
| Geometric median | "稳健的中心" | 到各样本点距离之和最小的点。对离群值稳健，平均值则不然。 |
| Monoculture | "同一个模型，同样的失败" | agent 共享训练数据或基础模型导致的相关错误。 |
| Sycophantic conformity | "附和最响的声音" | agent 的投票偏向先发言/最大声者。 |
| Core/Edge | "层级化 BFT" | WBFT 的切分：小的 Core 先共识，Edge 节点跟随。限定延迟。 |

## Further Reading · 延伸阅读

- [Castro & Liskov — Practical Byzantine Fault Tolerance (OSDI 1999)](https://pmg.csail.mit.edu/papers/osdi99.pdf) —— 地基之作
- [CP-WBFT — Confidence-Probe Weighted BFT](https://arxiv.org/abs/2511.10400) —— 按置信度给选票加权
- [DecentLLMs — leaderless multi-agent consensus](https://arxiv.org/abs/2507.14928) —— 几何中位数聚合
- [WBFT — Weighted BFT with Hierarchical Structure Clustering](https://arxiv.org/abs/2505.05103) —— 限定延迟的 Core/Edge 切分
- [Can AI Agents Agree?](https://arxiv.org/abs/2603.01213) —— 标量一致性的脆弱性与欺骗性人格攻击
