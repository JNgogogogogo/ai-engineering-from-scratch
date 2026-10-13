# Bounded Self-Improvement Designs · 有界自我改进设计

> 研究已经收敛到四个用于给自我改进循环设界的原语（primitive）。必须在每一次修改前后都成立的形式化不变量（invariant）。不可被修改的对齐锚点（alignment anchor）。每个维度（安全、公平、鲁棒性）都必须成立的多目标约束，而不只是性能。当历史指标暗示能力损失时暂停循环的回归检测。它们没有一个是安全性证明——信息论结果（Kolmogorov 复杂度、Lob 定理）限制了任何系统能对自身后继证明什么。它们是抬高「静默失败」成本的缓解手段。

> Research has converged on four primitives for bounding a self-improvement loop. Formal invariants that must hold across every edit. Alignment anchors that cannot be modified. Multi-objective constraints where every dimension (safety, fairness, robustness) must hold, not just performance. Regression detection that pauses the loop when historical metrics suggest capability loss. None of them is a proof of safety — information-theoretic results (Kolmogorov complexity, Lob's theorem) bound what any system can prove about its own successors. They are mitigations that raise the cost of silent failure.

**类型：** Learn（学习）
**语言：** Python（仅 stdlib，带不变量检查的有界循环）
**先修：** Phase 15 · 07（RSI）、Phase 15 · 04（DGM）
**时间：** ~60 分钟

## The Problem · 问题在哪

第 7 课的竞赛模拟器表明：微小的速率差异会复利成巨大的差距。第 4 课的 DGM 案例研究表明：循环能主动地对自己的评估器耍花招。两个结果指向同一个工程问题：你能对一个自我改进循环施加什么约束，使得这些约束不会被循环本身悄悄削弱？

ICLR 2026 RSI Workshop 总结（openreview.net/pdf?id=OsPQ6zTQXV）给出了四个这样的原语。Anthropic 的 RSP v3.0（第 19 课）和 DeepMind 的 FSF v3（第 20 课）都在能力阈值中引用了它们。Meta 的 HyperAgents 工作和 SAHOO（2026 年 3 月）等社区框架在生产中实现了它们的子集。

诚实的表述是：这些是缓解手段。信息论结果限制了任何系统能对自身后继证明什么，而且当前没有任何设计在形式上关闭这个问题。一个有良好约束的循环比无约束的更安全，但不是绝对安全。

> Lesson 7's race simulator showed that small rate differences compound into large gaps. Lesson 4's DGM case study showed that loops can actively game their own evaluators. Both results point to the same engineering question: what constraints can you put on a self-improvement loop such that the constraints cannot be silently weakened by the loop itself?
> The ICLR 2026 RSI Workshop summary (openreview.net/pdf?id=OsPQ6zTQXV) identifies four such primitives. Anthropic's RSP v3.0 (Lesson 19) and DeepMind's FSF v3 (Lesson 20) both reference them in capability thresholds. The Meta HyperAgents work and community frameworks like SAHOO (March 2026) implement subsets in production.
> The honest framing: these are mitigations. Information-theoretic results bound what any system can prove about its own successor, and no current design closes the problem formally. A well-bounded loop is safer than an unbounded one, not safe in absolute terms.

## The Concept · 概念

### Primitive 1: formal invariants · 原语一：形式化不变量

不变量是必须在每次自我修改之前和之后都成立的性质。例子：

- 输出分布以一个固定的宪法头部（constitution header）为条件（第 17 课）。
- 没有任何工具调用发往未授权端点。
- 内存写入走一条有日志、有签名的路径。
- 评估器的模块哈希与批准版本一致。

不变量由循环无法编辑的外部代码检查。如果一个提议的修改违反了某个不变量，它会被拒绝。这抓住了 DGM 式的评估器篡改模式（第 4 课）。

难点在于选出既对安全必要、又能在合理时间内计算的不变量。规定过多会让进展停滞；规定不足会让循环从重要性质旁边溜过去。

> An invariant is a property that must hold before and after every self-modification. ... Invariants are checked by external code the loop cannot edit. If a proposed modification violates an invariant, it is rejected. This catches the DGM-style evaluator-tampering mode (Lesson 4).
> The hard part is choosing invariants that are necessary for safety and computable in reasonable time. Over-specifying stalls progress; under-specifying lets the loop walk past important properties.

### Primitive 2: alignment anchors · 原语二：对齐锚点

对齐锚点是循环核心目标的不可变表示，被钉在循环的编辑面之外。例子：

- 一份宪法文本（第 17 课），每次调用时都从一个只读位置加载。
- 一个位于独立仓库、带独立访问控制的评估器。
- 一份由人类签名、每轮重新验证的工具权限清单。

锚点的作用是防止目标漂移。循环可以改进它追求目标的方式，但不能编辑目标是什么。

微妙的失败模式：一个循环无法编辑的锚点，仍可能被一个「在如何解读锚点上发生漂移」的循环重新诠释。Constitutional AI（第 17 课）明确是基于推理来处理新情况的；那层推理正是解释漂移所在之处。锚点是必要条件，不是充分条件。

> An alignment anchor is an immutable representation of the loop's core objective, pinned outside the loop's edit surface. ... The anchor's role is to prevent objective drift. The loop may improve how it pursues the objective, but cannot edit what the objective is.
> The subtle failure mode: an anchor the loop cannot edit can still be reinterpreted by a loop that drifts in how it reads the anchor. Constitutional AI (Lesson 17) is explicitly reason-based to handle novel situations; that reasoning layer is where interpretation drift lives. Anchors are necessary, not sufficient.

### Primitive 3: multi-objective constraints · 原语三：多目标约束

一个只优化单个标量分数的循环会找到捷径。一个必须同时满足多个硬约束的循环，可用的捷径更少。典型轴：

- 性能（任务级基准）
- 安全（红队评估、对已知坏输入的拒答率）
- 公平（敏感子群上的差别影响界限）
- 鲁棒性（OOD 测试集、对抗输入处理）

一个修改只有在每个约束都成立时才被接受。第 13 课的成本治理器在其上叠加财务约束。第 18 课的 Llama Guard 作为安全轴接入。

> A loop that optimizes a single scalar score will find shortcuts. A loop that must simultaneously satisfy multiple hard constraints has fewer shortcuts available. ... A modification is accepted only if every constraint holds. Lesson 13's cost governor stacks this with financial constraints. Lesson 18's Llama Guard plugs in as a safety axis.

### Primitive 4: regression detection · 原语四：回归检测

每一轮的分数与历史分布比较。超出配置容忍度的下跌会暂停循环。这抓住了静默的能力损失——否则它会被吸收进滚动平均里，好像循环已经「改进过去」了似的。

一个实际实现：存储最近 N 轮的每任务分数。每个新循环计算每任务的增量。如果任何增量跌破阈值，这一轮被拒绝并交由人类审查。

> Each cycle's scores are compared against historical distributions. A drop beyond configured tolerance pauses the loop. This catches silent capability loss that would otherwise be absorbed into the running average as the loop "improved past" it.
> A practical implementation: store the last N cycles' per-task scores. Each new cycle computes a per-task delta. If any delta drops below a threshold, the cycle is rejected and a human reviews.

### Information-theoretic limits · 信息论极限

Kolmogorov 复杂度和 Lob 定理为一个系统能对自身证明什么设置了上界。Schmidhuber 的形式化 Godel Machine（第 4 课）瞄准的就是最高的那个界；从没有人完成过一个非平凡的证明。Lob 的结果说：如果一个系统可证明地相信「如果我证明我该做 X，我就会做 X」，它会不经证明就去做 X——一个著名的自指失败。

这对我们的原语意味着：它们无法在形式上关闭安全问题。它们让静默失败变得更昂贵。一个恶意或漂移的循环，如果想悄悄绕过一个缺失的检查，现在必须主动破坏一个显式的检查——而后者是一个更容易被检测到的签名。

> Kolmogorov complexity and Lob's theorem set upper bounds on what a system can prove about itself. Schmidhuber's formal Godel Machine (Lesson 4) aimed for the highest such bound; nobody has completed a non-trivial proof. Lob's result says: if a system provably believes "I will do X if I prove I should do X," it will do X without proving it should, a well-known self-reference failure.
> The implication for our primitives: they cannot close the safety problem. They make silent failure more expensive. A malicious or drifted loop that would quietly bypass a missing check must now actively undermine an explicit one, which is a more detectable signature.

### A worked example · 一个完整的例子

假设一个智能体提出一个修改。把关栈（gate stack）：

1. 不变量检查：模块哈希、工具权限清单、宪法头部。
2. 锚点检查：目标陈述与批准版本一致（按字节或按语义）。
3. 多目标评估：性能、安全、公平、鲁棒性各轴。
4. 回归检测：没有任何轴的下跌超过容忍度。

四关全过，修改才能落地。任何一关失败都会暂停循环。

> Suppose an agent proposes an edit. The gating stack: 1. Invariant checks: module hashes, tool-permission manifest, constitutional header. 2. Anchor check: objective statement matches approved version (byte-wise or semantically). 3. Multi-objective evaluation: performance, safety, fairness, robustness axes. 4. Regression detection: no axis drops more than tolerance.
> All four must pass for the edit to land. Any single failure pauses the loop.

```figure
bounded-gates
```

## Use It · 实战用法

`code/main.py` 在第 4 课的 DGM 式玩具上运行一个有界自我改进循环，但把四个原语叠加在上面。每个原语都可以单独启用或禁用。演示的要点是：每个原语抓住一个特定类别的失败，而移除任何一个原语都会放行那一类失败。

> `code/main.py` runs a bounded self-improvement loop on the DGM-style toy from Lesson 4, but with the four primitives layered on top. Each primitive can be enabled or disabled individually. The demonstration is that each primitive catches a specific failure class, and that removing any one of them lets that failure class through.

## Ship It · 交付

`outputs/skill-bounded-loop-review.md` 审查一个提议的有界循环，并就它实际实现（而非声称实现）了四个原语中的哪些给出评分。

> `outputs/skill-bounded-loop-review.md` audits a proposed bounded loop and scores which of the four primitives it actually implements versus claims to.

## Exercises · 练习

1. 启用全部原语运行 `code/main.py`。确认循环仍在主指标上改进，同时不让 hack 获胜。

2. 禁用回归检测。构造一个输入，让静默的能力损失被接受。

3. 禁用多目标约束。展示循环在性能轴上收敛，而某个安全轴在下跌。

4. 为一个编码智能体设计一个对齐锚点。什么文本、存在哪里、怎么检查？

5. 读 ICLR 2026 RSI Workshop 总结。从四个原语中挑一个，对当前最优水平提出一个具体改进。

> 1. Run `code/main.py` with all primitives enabled. Confirm the loop still improves on the primary metric without letting the hack win.
> 2. Disable regression detection. Construct an input where this leads to silent capability loss being accepted.
> 4. Design an alignment anchor for a coding agent. What text, stored where, checked how?

## Key Terms · 术语表

| 术语 | 人们口头怎么说 | 它实际是什么意思 |
|---|---|---|
| Invariant | 「永远为真的性质」 | 由外部代码在每次修改前后检查的性质 |
| Alignment anchor | 「钉死的目标」 | 位于循环编辑面之外的不可变核心目标表示 |
| Multi-objective constraint | 「所有轴都必须成立」 | 性能、安全、公平、鲁棒性——全部要求 |
| Regression detection | 「下跌就暂停」 | 当历史指标增量暗示能力损失时暂停循环 |
| Kolmogorov bound | 「信息论极限」 | 限制一个系统能对自身后继证明什么 |
| Lob's theorem | 「自指陷阱」 | 系统可以不经证明「我该做」就去做 |
| Gate stack | 「分层检查」 | 多个原语组合；任何失败都拒绝修改 |
| Bounded improvement | 「缓解，不是证明」 | 抬高静默失败成本；不关闭安全问题 |

> | Term | What people say | What it actually means |
> |---|---|---|
> | Invariant | "Always-true property" | A property checked by external code before and after every edit |
> | Alignment anchor | "Pinned objective" | Immutable core-goal representation outside the loop's edit surface |
> | Multi-objective constraint | "All axes must hold" | Performance, safety, fairness, robustness — all required |
> | Regression detection | "Pause on drop" | Pause the loop when historical metric deltas suggest capability loss |
> | Kolmogorov bound | "Information-theoretic limit" | Limits what a system can prove about its own successor |
> | Lob's theorem | "Self-reference trap" | System can act on "I should" without proving it should |
> | Gate stack | "Layered check" | Multiple primitives combined; any failure rejects the edit |
> | Bounded improvement | "Mitigation, not proof" | Raises silent-failure cost; does not close the safety problem |

## Further Reading · 延伸阅读

- [ICLR 2026 RSI Workshop summary (OpenReview)](https://openreview.net/pdf?id=OsPQ6zTQXV) —— 四原语的收敛。
- [Anthropic Responsible Scaling Policy v3.0](https://anthropic.com/responsible-scaling-policy/rsp-v3-0) —— 多目标能力阈值。
- [DeepMind Frontier Safety Framework v3](https://deepmind.google/blog/strengthening-our-frontier-safety-framework/) —— 作为不变量原语的欺骗性对齐监控。
- [Schmidhuber (2003). Godel Machines](https://people.idsia.ch/~juergen/goedelmachine.html) —— 这些原语的形式化证明祖先。
- [Anthropic — Claude's Constitution (January 2026)](https://www.anthropic.com/news/claudes-constitution) —— 基于推理的对齐锚点。
