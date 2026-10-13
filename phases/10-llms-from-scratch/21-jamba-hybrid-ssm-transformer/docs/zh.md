# Jamba — Hybrid SSM-Transformer · Jamba：混合 SSM-Transformer（hybrid SSM-Transformer）

> 状态空间模型（SSM）和 Transformer 想要的东西不一样。Transformer 用平方代价的注意力购买质量；SSM 通过递归换来线性时间推理和恒定内存，但质量落后。AI21 的 Jamba（2024 年 3 月）和 Jamba 1.5（2024 年 8 月）把两者放进同一个模型：每 7 层 Mamba 配 1 层 Transformer，每隔一个块上 MoE，256k 上下文窗口塞进单张 80GB GPU。Mamba-3（ICLR 2026）用复数值状态空间和 MIMO 投影收紧了 SSM 这一侧。本课端到端通读这两种架构，并解释为什么纯 SSM 和纯 Transformer 的长上下文尝试都没能活下来，而这个混合配方却挺过了三年的规模扩张。
>
> State space models (SSMs) and transformers want different things. Transformers buy quality via attention at quadratic cost. SSMs buy linear-time inference and constant memory via a recurrence but lag quality. AI21's Jamba (March 2024) and Jamba 1.5 (August 2024) put them in the same model: 1 Transformer layer for every 7 Mamba layers, MoE on every other block, and a 256k context window that fits on a single 80GB GPU. Mamba-3 (ICLR 2026) tightens the SSM side with complex-valued state spaces and MIMO projections. This lesson reads both architectures end to end and explains why the hybrid recipe has survived three years of scaling when pure-SSM and pure-Transformer long-context attempts have not.

**Type:** Learn
**Languages:** Python (stdlib, layer-mix calculator)
**Prerequisites:** Phase 10 · 14 (open-model architectures), Phase 10 · 17 (native sparse attention)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 解释一个 Jamba 块里的三种原语——Transformer 层、Mamba 层、MoE——以及 1:7:偶数位交错的配方。
- 说明 SSM 的递归在大致层面上长什么样，以及它为什么能实现恒定内存推理。
- 计算一个 Jamba 模型在 256k 上下文下的 KV cache 占用，并与纯 Transformer 模型所需的开销对比。
- 说出 Mamba-3 的三项创新（指数梯形离散化、复数值状态更新、MIMO）以及各自针对的问题。

> Explain the three primitives in a Jamba block — Transformer layers, Mamba layers, MoE — and the 1:7:even interleaving recipe.
> State what an SSM's recurrence looks like at a high level and why it enables constant-memory inference.
> Compute the KV cache footprint of a Jamba model at 256k context and compare to what a pure-Transformer model would need.
> Name the three Mamba-3 innovations (exponential-trapezoidal discretization, complex-valued state update, MIMO) and the problem each one targets.

## The Problem · 问题在哪

注意力对序列长度是平方复杂度，状态空间模型是线性。这个差异会复利式放大：在 256k token 下，一个 Transformer 注意力图每 head 有 65B 个条目；而 SSM 的递归状态不论序列多长都是固定大小。

纯 SSM 模型（Mamba、Mamba-2）在小规模上能追平 Transformer 的困惑度（perplexity），但在状态追踪任务上落后，并且在某些类别的上下文检索上会失败。直觉是：SSM 把历史压缩进一个固定状态，历史一长信息就泄漏。注意力对一切记得分毫不差，但要付平方代价。

显而易见的修法：两个都用。把 Transformer 层放在需要精确回忆的地方，其余地方用 SSM 层，再调比例。Jamba 是第一个把这个混合配方做到规模化出货的生产级模型（52B 总参、12B 激活、256k 上下文、单张 80GB GPU）。Jamba 1.5 把这个家族扩展到 398B 总参 / 94B 激活。Mamba-3（ICLR 2026）是当前最强的纯 SSM 基线，混合架构可以围绕它重建。

本课通读这三篇论文，建立「选对比例」所需的心智模型。

> Attention is quadratic in sequence length. State space models are linear. That difference compounds: at 256k tokens, a Transformer attention map is 65B entries per head; an SSM's recurrent state is fixed-size regardless of sequence length. ... Pure-SSM models (Mamba, Mamba-2) match Transformer perplexity at small scales but lag on state-tracking tasks and fail on some categories of in-context retrieval. ... Jamba is the first production-grade model to ship this hybrid recipe at scale (52B total, 12B active, 256k context, single 80GB GPU). ... This lesson reads all three papers and produces the mental model for "pick the right ratio."

## The Concept · 概念

### An SSM in one page · 一页讲完 SSM

状态空间模型通过一个固定大小的状态 `h` 处理序列 `x_1, ..., x_N`：

```
h_t = A h_{t-1} + B x_t
y_t = C h_t
```

每一步，状态经线性动力学 `A` 演化，接收输入 `B x_t`，并输出 `C h_t`。`A, B, C` 可以学习。注意这个关键性质：计算 `y_t` 只需要 `h_{t-1}` 和 `x_t`，不需要任何更早的 `x`。内存恒定。推理每 token O(1)。

建模质量的关键在于 `A` 的结构。S4（Gu 2021）使用一个高度结构化的矩阵，训练时可以高效地按长卷积求值。Mamba（Gu, Dao 2023）把固定的 `A, B, C` 换成了依赖数据的版本（即「selective」的部分）。Mamba-2（2024）进一步简化了结构。Mamba-3（2026）在特定位置重新加回复杂性。

关键性质：对一个 decoder LLM 而言，SSM 层就是注意力层的即插即用替代品，只是把不断增长的 KV cache 换成了每层固定大小的状态。

> A state space model processes a sequence `x_1, ..., x_N` via a fixed-size state `h`: ... Note the critical property: computing `y_t` needs only `h_{t-1}` and `x_t`, not any earlier `x`. Memory is constant. Inference is O(1) per token. ... The trick for modeling quality is the structure of `A`. ... The key property: for a decoder LLM, an SSM layer is a drop-in replacement for an attention layer, with fixed-size per-layer state instead of a growing KV cache.

### The Jamba block · Jamba 块

一个 Jamba 块按两个数字交错排布层：

- `l`：注意力与 Mamba 之比。Jamba 取 `l = 8`，即每 7 层 Mamba 配 1 层 Transformer（7 Mamba + 1 Attention = 每组 8 层）。
- `e`：MoE 频率。Jamba 取 `e = 2`，即每隔一层应用一次 MoE。

块内的层序列：

```
M  M  M  M  M  M  M  A    (7 Mamba + 1 Attention)
|  M  |  M  |  M  |  M    (where | marks MoE applied)
```

每个 Jamba 块 8 层。深 4 个块（共 32 层）时，你得到 28 层 Mamba 和 4 层 Attention，其中 16 层使用 MoE。

> A Jamba block interleaves layers according to two numbers: ... `l`: the attention-to-Mamba ratio. Jamba uses `l = 8`, meaning 1 Transformer layer for every 7 Mamba layers (7 Mamba + 1 Attention = 8 layers per group). ... `e`: the MoE frequency. Jamba uses `e = 2`, meaning every other layer applies MoE. ... Each Jamba block is 8 layers. At 4 blocks deep (32 layers total), you get 28 Mamba and 4 Attention layers. 16 of those use MoE.

### Why the 1:7 ratio · 为什么是 1:7

AI21 做过消融实验：注意力与 Mamba 取什么比例，才能在他们的长上下文评测上同时拿到最佳的每参数困惑度 AND 上下文回忆？

- 注意力太多（1:1）：质量上升，但内存和速度劣化。
- 注意力太少（1:15）：内存很好，但上下文检索失败。
- 甜点：1:7 或 1:8。

直觉：Transformer 层负责精确回忆和状态追踪，Mamba 层负责处理中那些廉价的粗活。

> AI21 ran ablations: what ratio of attention-to-Mamba gives the best perplexity-per-parameter AND in-context recall on their long-context evals? ... Too much attention (1:1): quality goes up but memory and speed degrade. ... Too little attention (1:15): memory is great but in-context retrieval fails. ... Sweet spot: 1:7 or 1:8. ... The intuition: the Transformer layers handle exact recall and state tracking. The Mamba layers handle the cheap bulk of processing.

### Positional encoding · 位置编码

Mamba 层本身就带位置感知（通过递归）。最早一批基于 Mamba 的混合模型里，注意力层不使用 RoPE——位置信息由 SSM 层提供。Jamba 1.5 给注意力层加上了 RoPE，以获得更好的长上下文泛化，这是基于长上下文实证评估做出的事后改进。

> Mamba layers are themselves position-aware (via the recurrence). Attention layers in the original Mamba-based hybrids did not use RoPE — the SSM layers provided position info. Jamba 1.5 adds RoPE to the attention layers for longer-context generalization, a post-hoc refinement based on empirical long-context evaluation.

### The memory budget · 内存预算

以 Jamba-1 的形状为例（32 层：28 Mamba + 4 Attention，hidden 4096，32 个注意力 head）：

- KV cache（只有注意力层贡献）：256k 下 BF16 为 `2 * 4 * 32 * 128 * 256k * 2 = 8.4 GB`。只有那 4 层注意力出钱。
- SSM 状态：每 token 前缀为 `28 * hidden * state_size`，但它是每层固定大小，不随序列长度增长。典型 Mamba 状态每特征 16，hidden 4096：总计 `28 * 4096 * 16 * 2 = 3.7 MB`。

对比一个 32 层、同 hidden、32 head 全量 MHA 的纯 Transformer：256k 下 BF16 为 `2 * 32 * 32 * 128 * 256k * 2 = 128 GB`。KV cache 缩减 8 倍。即使对照多数 2024 年模型在用的 GQA(8) 基线（`2 * 32 * 8 * 128 * 256k * 2 = 32 GB`），16 GB 的 Jamba 1:7 混合仍要小 2 倍。

这就是 AI21 说「单张 80GB GPU 跑 256k 上下文」的含义：全量 MHA 纯 Transformer 的 KV cache 根本放不下；GQA 基线也给权重和激活留不下空间；Jamba 的放得下。

> For a Jamba-1 shape (32 layers: 28 Mamba + 4 Attention, hidden 4096, 32 attention heads): ... KV cache (attention layers only): `2 * 4 * 32 * 128 * 256k * 2 = 8.4 GB` at 256k BF16. Only the 4 attention layers contribute. ... Compare to a pure Transformer at 32 layers, same hidden, full MHA at 32 heads: `2 * 32 * 32 * 128 * 256k * 2 = 128 GB` at 256k BF16. An 8x reduction in KV cache. ... That is what AI21 means by "256k context on a single 80GB GPU." The KV cache of a full-MHA pure Transformer would not fit; even a GQA baseline leaves no room for weights and activations; Jamba's does.

### Mamba-3: the pure-SSM baseline in 2026 · Mamba-3：2026 年的纯 SSM 基线

Mamba-3（ICLR 2026，arXiv:2603.15569）在纯 SSM 一侧引入三项创新：

1. **指数梯形离散化（exponential-trapezoidal discretization）。** 用一个更有表达力的递归取代 Mamba-2 的欧拉法离散化。类卷积运算被放进核心递归内部、作用在状态-输入上，而不是作为作用在 `x_t` 上的外层卷积。

2. **复数值状态更新（complex-valued state update）。** 之前的 Mamba 把状态矩阵从复数（S4）降到实对角（Mamba），再降到缩放单位阵（Mamba-2）。Mamba-3 重新加回复数值——等价于在状态上做一个依赖数据的 rotary embedding。这找回了此前实数值简化所牺牲的状态追踪能力。

3. **多输入多输出（MIMO）投影。** 不再使用逐特征的标量投影，改用矩阵值投影。在不增加解码延迟的前提下提升建模能力和推理期硬件利用率。

在 1.5B 参数规模，Mamba-3 的平均下游精度比 Gated DeltaNet 高 0.6 个点；MIMO 变体再多 1.2 个点，合计 1.8 个点的增益。相同状态大小下，Mamba-3 用一半的状态追平 Mamba-2。

Mamba-3 尚未以生产级混合模型的形式规模化出货——但它显然是下一代 Jamba 级模型 SSM 一侧的头号候选。

> Mamba-3 (ICLR 2026, arXiv:2603.15569) introduces three innovations on the pure-SSM side: ... Complex-valued state update. Previous Mambas reduced the state matrix from complex (S4) to real diagonal (Mamba) to scaled identity (Mamba-2). Mamba-3 re-adds complex values — equivalent to a data-dependent rotary embedding on the state. This restores state-tracking capabilities that previous real-valued simplifications cost. ... At 1.5B parameters, Mamba-3 improves average downstream accuracy by 0.6 points over Gated DeltaNet; the MIMO variant adds 1.2 more for a total 1.8-point gain. At the same state size, Mamba-3 matches Mamba-2 with half the state. ... Mamba-3 is not yet shipping in a production hybrid at scale — but it is the obvious candidate for the SSM side of the next Jamba-class model.

### When to reach for a hybrid · 什么时候选混合架构

混合架构赢的场景：

- 上下文长到纯 Transformer 的 KV cache 开始难受（64k 以上）。
- 任务混合了短程结构（SSM 擅长）与长程回忆（需要 Transformer）。
- 你要在单卡内存预算内部署，而 Transformer 的 KV cache 光自己就放不下。

混合架构输的场景：

- 上下文短（16k 以下）。SSM 的开销白花；纯 Transformer 就够。
- 任务需要处处对处处（everywhere-to-everywhere）的注意力（深度推理、多文档交叉引用）。混合中注意力层的稀疏性会拖后腿。
- 你要冲万亿参数前沿模型。纯 Transformer + MLA + MoE（DeepSeek-V3 风格）目前在这场能力竞赛中胜出。

> Hybrids win when: ... Context is long enough that pure Transformer KV cache becomes painful (64k+). ... Tasks mix short-range structure (good for SSM) with long-range recall (needs Transformer). ... You want to deploy on single-GPU memory budgets where the Transformer KV cache alone would not fit. ... Hybrids lose when: ... Context is short (under 16k). The SSM overhead is wasted; pure Transformer is fine. ... Tasks need everywhere-to-everywhere attention (deep reasoning, multi-document cross-reference). The sparsity of attention layers in the hybrid hurts. ... You are scaling to trillion-parameter frontier models. Pure-Transformer + MLA + MoE (DeepSeek-V3 style) is currently winning the capability race.

### The competitive landscape · 竞争格局

| 模型 | 家族 | 规模 | 独特卖点 |
|-------|--------|------|-------------|
| Mamba-2 | 纯 SSM | 3B | 线性时间、恒定内存 |
| Jamba | 混合 | 52B/12B | 单卡 80GB 跑 256k |
| Jamba 1.5 Large | 混合 | 398B/94B | 企业级长上下文 |
| Mamba-3 | 纯 SSM | 1.5B（论文） | 状态追踪能力回归 |
| DeepSeek-V3 | 纯 Transformer + MoE | 671B/37B | 前沿能力 |

2026 年的格局：纯 Transformer MoE 统治前沿，但混合架构占据 256k 以上的上下文利基。Mamba-3 在状态追踪上的胜利，可能把下一代混合比例推向更低（更多 SSM、更少注意力）。

> | Model | Family | Scale | Unique claim |
> |-------|--------|------|-------------|
> | Mamba-2 | pure SSM | 3B | linear time, constant memory |
> | Jamba | hybrid | 52B/12B | 256k on 80GB |
> | Jamba 1.5 Large | hybrid | 398B/94B | enterprise-grade long-context |
> | Mamba-3 | pure SSM | 1.5B (paper) | state-tracking restored |
> | DeepSeek-V3 | pure Transformer + MoE | 671B/37B | frontier capability |
>
> The 2026 landscape: pure-Transformer MoE dominates the frontier, but hybrids own the 256k-plus context niche. Mamba-3's state-tracking wins may push hybrid ratios lower (more SSM, less attention) in the next generation.

```figure
swiglu-ffn
```

## Use It · 实战用法

`code/main.py` 是混合架构的内存计算器。给定 SSM-Transformer 比例和 hidden 大小 / 层数配置，它计算：

- 目标上下文下的 KV cache。
- SSM 状态内存。
- 一系列模型形状在上下文 N 下的总内存。

计算器支持：

- 纯 Transformer 基线（KV cache 随 N 增长）。
- Jamba 式 1:7 混合。
- 纯 SSM（完全没有 KV cache）。

已发布形状的数字直接来自 Jamba-1 和 Jamba-1.5 论文，假想变体的数字为外推。

真实部署的集成考量：

- 多数生产推理服务器（vLLM、SGLang）支持 Jamba 和 Mamba。请核对具体版本。
- 在 256k 上下文，Jamba 的内存优势体现在并发请求吞吐上。同样的显存，你塞得下的 Jamba 序列比 Transformer 序列多。
- Mamba-3 作为独立模型尚未进入生产——1.5B 规模的研究预览。

> `code/main.py` is a memory calculator for hybrid architectures. Given an SSM-Transformer ratio and a hidden-size / layer-count config, it computes: ... The calculator supports: ... Most production inference servers (vLLM, SGLang) support Jamba and Mamba. Check the specific version. ... At 256k context, Jamba's memory advantage shows up in concurrent-request throughput. On the same VRAM you fit more Jamba sequences than Transformer sequences. ... Mamba-3 as a standalone model is not yet shipping in production — research preview at 1.5B.

## Ship It · 交付

本课产出 `outputs/skill-hybrid-picker.md`。给定一份工作负载规格（上下文长度画像、任务组合、内存预算），它在纯 Transformer、Jamba 式混合和纯 SSM 之间给出推荐，并对内存与质量的取舍给出明确理由。

> This lesson produces `outputs/skill-hybrid-picker.md`. Given a workload specification (context length profile, task mix, memory budget), it recommends between a pure Transformer, a Jamba-style hybrid, and a pure SSM, with explicit reasoning about the memory and quality tradeoffs.

## Exercises · 练习

1. 运行 `code/main.py`，计算 32 层纯 Transformer（hidden 4096、32 heads）与同形状 Jamba-1 混合在 256k 上下文下的 KV cache。验证 AI21 论文声称的约 8 倍内存缩减。

2. 修改计算器，建模 1:3 混合（4 Mamba : 1 Attention）和 1:15 混合（14 Mamba : 1 Attention）。画出 KV cache 随比例变化的曲线。比例取多少时 KV cache 恰好等于 SSM 状态内存？

3. 阅读 Jamba 论文（arXiv:2403.19887）第 3 节。解释为什么 AI21 在 Mamba-2 更快的情况下仍选用 Mamba-1。提示：混合消融那一节记录了原因。

4. 计算 Jamba 1.5 Large（398B 总参、94B 激活）中「每隔一层上 MoE」的参数开销。把激活比与 DeepSeek-V3（37B/671B）对比，并解释为什么 Jamba 的架构把激活比推得更高。

5. 阅读 Mamba-3 论文（arXiv:2603.15569）第 3 节。用三句话解释为什么复数值状态更新等价于一个依赖数据的 rotary embedding。把答案与 Phase 7 · Lesson 04 的 RoPE 推导联系起来。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| State space model (SSM) | 「带固定状态的递归」 | 一个带可学习递归 `h_t = A h_{t-1} + B x_t` 的层；每 token 恒定内存 |
| Selective SSM | 「Mamba 的诀窍」 | 依赖数据的 A、B、C 参数，让模型以线性时间获得类似门控的选择性 |
| Attention-to-Mamba ratio | 「有多少注意力层」 | 在 Jamba 中，`l = 8` 表示每 7 层 Mamba 配 1 层注意力 |
| Jamba block | 「那个 8 层小组」 | 1 层注意力 + 7 层 Mamba，交替位置上加 MoE |
| SSM state | 「隐藏缓冲区」 | 每层固定大小的状态，在 Mamba 层中取代 KV cache |
| 256k context | 「Jamba 的招牌数字」 | Jamba-1 能塞进单张 80GB GPU 的序列长度；同规模的纯 Transformer 做不到 |
| Mamba-3 | 「2026 年的纯 SSM」 | 当前最强的纯 SSM 架构，复数状态 + MIMO；混合架构重建所围绕的基线 |
| MIMO | 「多输入多输出」 | Mamba-3 的创新，用矩阵值投影取代逐特征标量投影 |
| Exponential-trapezoidal discretization | 「Mamba-3 的递归」 | 更有表达力的递归，涵盖了 Mamba-2 的欧拉法离散化 |
| Hybrid architecture | 「注意力和 SSM 混着用」 | 任何交错排布 Transformer 层与 SSM 层的模型；Jamba 是生产级原型 |

## Further Reading · 延伸阅读

- [Lieber et al. — Jamba: A Hybrid Transformer-Mamba Language Model (arXiv:2403.19887)](https://arxiv.org/abs/2403.19887) —— Jamba 原始论文：比例消融与 256k 上下文声明
- [AI21 — Jamba 1.5: Hybrid Transformer-Mamba at Scale (arXiv:2408.12570)](https://arxiv.org/abs/2408.12570) —— 扩展后的家族：398B/94B 与 12B/52B 公开发布
- [Gu, Dao — Mamba: Linear-Time Sequence Modeling with Selective State Spaces (arXiv:2312.00752)](https://arxiv.org/abs/2312.00752) —— Jamba 所依赖的 selective SSM 论文
- [Dao, Gu — Mamba-2 (arXiv:2405.21060)](https://arxiv.org/abs/2405.21060) —— 简化版结构化状态空间后继者
- [Lahoti et al. — Mamba-3 (arXiv:2603.15569, ICLR 2026)](https://arxiv.org/abs/2603.15569) —— 复数值状态、MIMO，2026 年的纯 SSM 前沿
- [Gu et al. — Efficiently Modeling Long Sequences with Structured State Spaces (arXiv:2111.00396)](https://arxiv.org/abs/2111.00396) —— S4 论文，LLM 的 SSM 谱系起点
