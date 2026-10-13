# Native Sparse Attention (DeepSeek NSA) · 原生稀疏注意力（DeepSeek NSA）

> 在 64k token 下，注意力吃掉了解码延迟的 70-80%。每家开源模型实验室都有一套修复方案。DeepSeek 的 NSA（ACL 2025 最佳论文）是那个最终站住脚的：三条并行的注意力分支——压缩后的粗粒度 token、筛选保留的细粒度 token、服务局部上下文的滑窗——通过一个可学习的门控组合起来。它对硬件友好（kernel 好写）、原生可训练（在预训练里就生效，而不是推理时外挂），并且在 64k 解码上比 FlashAttention 更快，同时质量持平甚至超过全注意力。本课端到端构建这三条分支，并说明为什么这种稀疏性是端到端可微的。

> At 64k tokens, attention eats 70-80% of decode latency. Every open-model lab has a plan to fix it. DeepSeek's NSA (ACL 2025 best paper) is the one that stuck: three parallel attention branches — compressed coarse-grained tokens, selectively retained fine-grained tokens, and sliding windows for local context — combined through a learned gate. It is hardware-aligned (kernel-friendly), natively trainable (works in pre-training, not bolted on at inference), and on 64k decodes it runs faster than FlashAttention while matching or beating full attention quality. This lesson builds the three branches end-to-end and shows why the sparsity is end-to-end differentiable.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 7 · 12 (KV cache, flash-attention), Phase 7 · 15 (attention variants), Phase 10 · 16 (differential attention)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 说出 NSA 的三条注意力分支，以及每条各捕捉什么。
- 解释为什么 NSA 是「原生可训练」的，而以往的稀疏注意力方法都只能用在推理阶段。
- 以压缩块大小和选择 top-k 为变量，计算 NSA 在 64k 上下文下相对全注意力的计算量节省。
- 在短合成序列上用 stdlib Python 实现三路分支组合，并验证门控权重行为正常。

> State the three NSA attention branches and what each one captures.
> Explain why NSA is "natively trainable" where prior sparse-attention methods were inference-only.
> Compute the attention compute savings of NSA versus full attention at 64k context as a function of compression block size and selection top-k.
> Implement the three-branch combination in stdlib Python on a short synthetic sequence and verify the gating weights behave.

## The Problem · 问题在哪

序列长度为 N 的全注意力，每层要付出 `O(N^2)` 时间和 `O(N)` 的 KV cache。到了 64k token，计算量和内存带宽数字都是灾难性的。NSA 论文给出的理论估算：在 64k 下，注意力占总解码延迟的 70-80%。下游的一切——TTFT、每秒 token 数、每百万 token 成本——都被注意力成本支配。

稀疏注意力是显而易见的答案。此前的尝试分两派。固定模式稀疏（sliding-window、strided、block-local）直接扔掉信息，在长程回忆任务上失败。推理时稀疏（KV cache 剪枝、H2O、StreamingLLM）施加在一个用稠密注意力预训练过的模型上，只能收回潜在加速的一小部分，因为模型从未被要求把信息路由过这个稀疏模式。

Native Sparse Attention（Yuan et al., DeepSeek + PKU + UW，ACL 2025 最佳论文，arXiv:2502.11089）两头都占：一个模型在预训练中学会的稀疏模式，加上一个与 kernel 对齐、能在推理时真正兑现计算节省的算法实现。两年之内，NSA 或它的直系后代就是每个前沿长上下文模型的默认注意力。

> Full attention at sequence length N costs `O(N^2)` time and `O(N)` KV cache per layer. At 64k tokens, the compute and memory bandwidth numbers are catastrophic. Measured theoretical estimate from the NSA paper: attention accounts for 70-80% of total decode latency at 64k. Everything downstream — TTFT, tokens/sec, cost per million tokens — is dominated by attention cost.
> Sparse attention is the obvious answer. Prior attempts fall into two buckets. Fixed-pattern sparsity (sliding-window, strided, block-local) throws information away and fails on long-range recall tasks. Inference-time sparsity (KV cache pruning, H2O, StreamingLLM) is applied to a model pre-trained on dense attention and recovers only a fraction of the potential speedup because the model was never asked to route information through the sparse pattern.
> Native Sparse Attention (Yuan et al., DeepSeek + PKU + UW, ACL 2025 best paper, arXiv:2502.11089) does both: a sparsity pattern the model learns during pre-training, implemented as a kernel-aligned algorithm that actually delivers the compute savings at inference. Two years from now, NSA or a direct descendant is the default attention on every frontier long-context model.

## The Concept · 概念

### Three parallel branches · 三条并行分支

对每个查询，NSA 对 KV cache 的三种不同视图各做一次注意力：

1. **压缩分支。** token 按 `l`（通常 32 或 64）分组成块。每个块经一个小型可学习 MLP 压缩成一个摘要 token。查询在这些压缩 token 上做注意力，得到整条序列的粗粒度视图。

2. **选择分支。** 利用压缩分支给出的注意力分数，找出与当前查询最相关的 top-k 个块。把这些块中的细粒度（未压缩）token 读出来，查询在它们之上做注意力。可以把压缩分支的注意力理解为选择步骤的路由信号。

3. **滑窗分支。** 查询关注最近的 `W` 个 token（通常 512）作为局部上下文。这条分支捕捉结构为主的短程模式（句法、局部指代），另外两条分支可能漏掉它们。

三个分支输出经由一个可学习的逐位置门控组合：

```
out = g_cmp * out_cmp + g_sel * out_sel + g_win * out_win
```

`g_cmp, g_sel, g_win` 是作用在查询上的一个小 MLP 给出的门控权重。它们不必和为 1——可以独立地为各分支加权。

> For each query, NSA runs attention three times, against three different views of the KV cache:
> 1. **Compressed branch.** Tokens are grouped into blocks of size `l` (typically 32 or 64). Each block is compressed into a single summary token via a small learned MLP. The query attends over these compressed tokens, getting a coarse-grained view of the whole sequence.
> 2. **Selected branch.** Using attention scores from the compressed branch, the top-k blocks most relevant to the current query are identified. Fine-grained (uncompressed) tokens from those blocks are read and the query attends over all of them. Think of compressed-branch attention as the routing signal for the selection.
> 3. **Sliding-window branch.** The query attends to the most recent `W` tokens (typically 512) for local context. This branch captures the structure-heavy short-range patterns (syntax, local coreference) that the other two might miss.
> The three branch outputs are combined via a learned per-position gate:
> `g_cmp, g_sel, g_win` are gate weights from a small MLP on the query. They do not have to sum to 1 — they can weight branches independently.

### Why this is "natively trainable" · 为什么它「原生可训练」

选择步骤（top-k 块）是离散的。离散操作会切断梯度流。此前的稀疏注意力工作要么不让梯度穿过选择步骤（限制了训练），要么用连续松弛——推理时给不出真正的稀疏。

NSA 绕开了这个死结：压缩分支的注意力本身就是对整条序列的可微粗粒度注意力。top-k 操作只是复用压缩分支排前的注意力分数，来决定加载哪些细粒度块。梯度流经压缩分支的分数（它们同时影响压缩输出和选择逻辑），被选块的贡献对最终输出也是可微的。不可微的 `top_k` 操作在前向计算图上是个 no-op——它只控制哪些块从内存里被加载。

这就是 NSA 能端到端用于预训练的原因。模型学着把信息路由过三条分支，产出的稀疏模式在推理时真的能兑现承诺的加速。

> The selection step (top-k blocks) is discrete. Discrete operations break gradient flow. Prior sparse-attention work either skipped backprop through selection (limiting training) or used continuous relaxations that did not give real sparsity at inference.
> NSA sidesteps this: the compressed-branch attention IS a differentiable coarse-grained attention on the whole sequence. The top-k operation just reuses the top attention scores from the compressed branch to pick which fine-grained blocks to load. Gradients flow through the compressed-branch scores (which influence both the compressed output AND the selection logic), and the selected blocks' contribution to the final output is also differentiable. The non-differentiable `top_k` operation is a no-op on the forward computational graph — it only controls which blocks get loaded from memory.
> This is why NSA can be used in pre-training end to end. The model learns to route information through the three branches jointly, producing a sparse pattern that at inference actually delivers the promised speedup.

### Hardware-aligned kernel · 硬件对齐的 kernel

NSA 的 kernel 是为现代 GPU 内存层次设计的。kernel 按 GQA 组加载查询（外层循环），按组取对应的稀疏 KV 块（内层循环），在 SRAM 上跑注意力。因为同一查询组看到的是同一批被选块（选择按查询组而非按查询头），KV 加载被摊到整组上。算术强度保持高位。

论文报告其 Triton kernel 在 64k 解码上比 FlashAttention 快 9 倍，且加速比随序列长度继续增长。前向和反向 kernel 都有提供。

> NSA's kernel is designed for modern GPU memory hierarchies. The kernel loads queries by GQA groups (outer loop), fetches the corresponding sparse KV blocks per group (inner loop), and runs attention on SRAM. Because each query group sees the same selected blocks (selection is per-query-group, not per-query-head), the KV loads are amortized across the group. Arithmetic intensity stays high.
> The paper reports Triton kernels running 9x faster than FlashAttention on 64k decodes, with the speedup ratio growing with sequence length. Forward and backward kernels are both provided.

### The compute budget · 计算量预算

设 `N` 为序列长度，`l` 为压缩块大小，`k` 为 top-k 选择数，`w` 为滑窗宽度，`b` 为被选块大小（通常等于 `l`）。

- 压缩分支：每查询 `O(N/l)` 个键，总计 `O(N * N / l)`。
- 选择分支：每查询 `O(k * b)` 个键，总计 `O(N * k * b)`。
- 滑窗分支：每查询 `O(w)` 个键，总计 `O(N * w)`。

总计：`O(N * (N/l + k*b + w))`。

`N = 64k, l = 64, k = 16, b = 64, w = 512` 时：每查询成本 `1000 + 1024 + 512 = 2536` 个键。全注意力是 `64000` 个键。25 倍计算缩减。

`N = 128k, l = 64, k = 16, b = 64, w = 512` 时：每查询成本 `2000 + 1024 + 512 = 3536` 个键。全注意力是 `128000` 个键。36 倍缩减。收益随序列长度增长——这正是全部意义所在。

> Let `N` be sequence length, `l` the compression block size, `k` the top-k selection count, `w` the sliding window, `b` the selected block size (typically equals `l`).
> - Compressed branch: `O(N/l)` keys per query, so `O(N * N / l)` total.
> - Selected branch: `O(k * b)` keys per query, so `O(N * k * b)`.
> - Sliding branch: `O(w)` keys per query, so `O(N * w)`.
> Total: `O(N * (N/l + k*b + w))`.
> With `N = 64k, l = 64, k = 16, b = 64, w = 512`: per-query cost is `1000 + 1024 + 512 = 2536 keys`. Full attention is `64000 keys`. 25x compute reduction.
> With `N = 128k, l = 64, k = 16, b = 64, w = 512`: per-query cost is `2000 + 1024 + 512 = 3536 keys`. Full attention is `128000 keys`. 36x reduction. The benefit grows with sequence length, which is the whole point.

### How does it compare · 横向对比

| Method | Differentiable | Real inference speedup | Long-range recall |
|--------|---------------|----------------------|-------------------|
| 仅滑窗 | yes | yes | 失败 |
| Strided / block-sparse | yes | yes | 部分 |
| KV 剪枝（H2O, StreamingLLM） | N/A（推理时） | yes | 部分 |
| MoBA (Moonshot) | partial | yes | 良好 |
| NSA | yes（原生） | yes（64k 下 9x） | 持平全注意力 |

MoBA（Moonshot，arXiv:2502.13189）同期发表，采用类似「三比一好」的思路，把 MoE 原则搬到注意力块上。NSA 和 MoBA 是 2026 年长上下文预训练必须知道的两个架构。

> MoBA (Moonshot, arXiv:2502.13189) was concurrently published and takes a similar three-is-better-than-one approach, applying the MoE principle to attention blocks. NSA and MoBA are the two architectures to know for 2026 long-context pre-training.

```figure
sliding-window-attention
```

## Build It · 动手造

`code/main.py` 在一条短合成序列上实现三条分支，并展示：

- 压缩 MLP（出于教学清晰，用一个简单的均值池化作基线；真实的 NSA 用可学习 MLP）。
- 由压缩分支分数驱动的 top-k 块选择。
- 最后 `w` 个 token 上的滑窗注意力。
- 门控组合。
- 与全注意力对比的计算量统计。

> `code/main.py` implements the three branches on a short synthetic sequence and shows:
> - The compression MLP (a simple mean-pool baseline is used for pedagogical clarity; the real NSA uses a learned MLP).
> - The top-k block selection driven by compressed-branch scores.
> - The sliding-window attention on the last `w` tokens.
> - The gated combination.
> - A compute-count printout comparing to full attention.

### Step 1: compress tokens into blocks · 第 1 步：把 token 压缩成块

```python
def compress(K, l):
    n = len(K)
    n_blocks = (n + l - 1) // l
    out = []
    for b in range(n_blocks):
        start, end = b * l, min((b + 1) * l, n)
        block = K[start:end]
        summary = [sum(row[d] for row in block) / len(block) for d in range(len(K[0]))]
        out.append(summary)
    return out
```

### Step 2: compressed-branch attention · 第 2 步：压缩分支注意力

让查询对压缩后的键跑 softmax 注意力。压缩分支的分数同时充当 top-k 选择的信号。

> Run softmax attention of the query against the compressed keys. The compressed-branch scores double as the signal for top-k selection.

### Step 3: top-k block selection · 第 3 步：top-k 块选择

挑出得分最高的 `k` 个压缩块的索引。把这些块里原始的未压缩 token 加载出来，在其上做注意力。

> Pick the indices of the `k` highest-scoring compressed blocks. Load the original uncompressed tokens from those blocks and run attention on them.

### Step 4: sliding-window attention · 第 4 步：滑窗注意力

取最后 `w` 个 token，对它们跑标准注意力。

> Take the last `w` tokens and run standard attention against them.

### Step 5: gate + combine · 第 5 步：门控 + 组合

作用于查询的小型 MLP 产出三个门控权重。最终输出是三个分支输出的加权和。

> A small MLP on the query produces three gate weights. The final output is a weighted sum of the three branch outputs.

### Step 6: compute counting · 第 6 步：计算量统计

打印每个分支每查询关注的键数和总数，与 `N`（全注意力）比较。在 1024 token 合成序列、`l = 32, k = 4, w = 128` 下，NSA 每查询看 `32 + 128 + 128 = 288` 个键，而全注意力是 1024——少了 3.5 倍。

> Print the number of keys attended per query for each branch and the total. Compare to `N` (full attention). On a 1024-token synthetic with `l = 32, k = 4, w = 128`, NSA sees `32 + 128 + 128 = 288` keys per query versus 1024 for full attention — 3.5x fewer.

## Use It · 实战用法

NSA 已在 DeepSeek 自家的长上下文预训练流水线中服役。截至 2026 年 4 月，公开推理栈的集成状态：

- **DeepSeek 内部**：原生使用；已发布的权重用 NSA 或其继任者 DSA（Deepseek Sparse Attention）。
- **vLLM**：面向 DeepSeek-V3.x 权重的实验性 NSA 支持开发中。
- **SGLang**：已发布 NSA 基准；生产路径跟随 vLLM。
- **llama.cpp / CPU**：不支持；kernel 分解的开销在 CPU 吞吐下不划算。

什么时候用 NSA：

- 瞄准 64k+ 上下文、预算认真的预训练或继续训练。
- 推理 DeepSeek 自家的长上下文 checkpoint。这些权重本身就是 NSA 原生的。

什么时候不用：

- 服务一个已存在的稠密注意力预训练模型。不做继续训练就无法改造（retrofit）NSA。
- 上下文低于 16k。三路分支的开销盖过节省。
- batch-1 交互式聊天。延迟敏感的解码确实受益，但只在长上下文下。

> NSA is shipping in DeepSeek's own long-context pre-training pipeline. Integration status in public inference stacks as of April 2026:
> - **DeepSeek internal**: native, published weights use NSA or its successor DSA (Deepseek Sparse Attention).
> - **vLLM**: experimental NSA support in development for DeepSeek-V3.x weights.
> - **SGLang**: NSA benchmarks published; production path follows vLLM.
> - **llama.cpp / CPU**: not supported; overhead of the kernel decomposition is not worth it at CPU throughput.
> When to reach for NSA:
> - Pre-training or continued-training run targeting 64k-plus context with a serious compute budget.
> - Inference of DeepSeek's own long-context checkpoints. The weights are NSA-native.
> When not to:
> - Serving an existing dense-attention pre-trained model. You cannot retrofit NSA without continued training.
> - Context under 16k. The three-branch overhead dominates the savings.
> - Batch-1 interactive chat. Latency-sensitive decode benefits, but only at long contexts.

## Ship It · 交付

本课产出 `outputs/skill-nsa-integrator.md`。给定一份长上下文预训练运行规格，它会产出 NSA 集成计划：压缩块大小、top-k、滑窗、门控 MLP 宽度、kernel 选择，以及足以证明架构改动合理性的具体长上下文评测。

> This lesson produces `outputs/skill-nsa-integrator.md`. Given a long-context pre-training run specification, it produces an NSA integration plan: compression block size, top-k, sliding window, gate MLP width, kernel choice, and the specific long-context evals that would justify the architecture change.

## Exercises · 练习

1. 在 1024 token 合成序列上运行 `code/main.py`。在三个预设间扫 `(l, k, w)`，打印计算量统计。找出在 needle-in-haystack 测试上对全注意力保持 95% 召回的前提下、每查询键数最低的预设。

2. 把均值池化压缩器换成一个微型可学习 MLP（2 层，隐藏 32）。在一个「信号是块均值」的合成任务上训练它。在留出数据上测它相对均值池化基线的困惑度差距。

3. 实现门控 MLP。它以查询为输入、输出三个标量。展示门控行为合理：随机查询上接近均匀加权；查询命中远处块时，选择分支拿到大头权重。

4. 计算一个启用 NSA 的 70B 模型在 128k 上下文下的 KV cache 内存预算。KV 头 8、head dim 128、BF16。与全注意力以及 MLA（Phase 10 · 14 给过 MLA 的数字）比较。找出 NSA 细粒度分支的 KV cache 等于全注意力的序列长度。

5. 阅读 NSA 论文（arXiv:2502.11089）第 4 节，用三句话解释为什么 top-k 选择的分数复用压缩分支的注意力分数、而不是另算一路路由分数。把答案与梯度流挂钩。

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| Compressed branch | 「粗粒度视图」 | 在块平均后的键上做注意力，每查询只花 O(N/l) 个键就拿到全局上下文 |
| Selected branch | 「top-k 块」 | 对压缩分支得分最高的 `k` 个块里的 token 做细粒度注意力 |
| Sliding window | 「局部上下文」 | 对最近 `W` 个 token 做注意力，捕捉短程模式 |
| Native trainability | 「预训练时就开着稀疏」 | 稀疏模式在预训练中学会，而不是推理时外挂 |
| Compression block size l | 「粗视图的分组大小」 | 多少个 token 合并成一个摘要；典型 32-64 |
| Top-k | 「保留几个块」 | 其未压缩 token 会被读出的压缩块数量；典型 16 |
| Sliding window W | 「局部注意力半径」 | 典型 512；短了伤局部连贯性，长了浪费计算 |
| Branch gate | 「三路怎么混」 | 逐位置的 MLP 输出，为三个分支的贡献加权 |
| Hardware alignment | 「对 kernel 友好的稀疏」 | 稀疏模式的选择保证实际 GPU kernel 能达到理论加速 |
| DSA | 「NSA 的继任者」 | Deepseek Sparse Attention，DeepSeek 谱系里跟随 NSA 的架构 |

## Further Reading · 延伸阅读

- [Yuan et al. — Native Sparse Attention: Hardware-Aligned and Natively Trainable Sparse Attention (arXiv:2502.11089, ACL 2025 Best Paper)](https://arxiv.org/abs/2502.11089) —— 原始论文
- [DeepSeek-V3 Technical Report (arXiv:2412.19437)](https://arxiv.org/abs/2412.19437) —— NSA 所瞄准的架构家族
- [Moonshot AI — MoBA: Mixture of Block Attention for Long-Context LLMs (arXiv:2502.13189)](https://arxiv.org/abs/2502.13189) —— 同期工作，MoE 风格的块注意力
- [Beltagy et al. — Longformer: The Long-Document Transformer (arXiv:2004.05150)](https://arxiv.org/abs/2004.05150) —— 滑窗注意力的源头
- [Xiao et al. — StreamingLLM: Efficient Streaming Language Models with Attention Sinks (arXiv:2309.17453)](https://arxiv.org/abs/2309.17453) —— NSA 所超越的推理时稀疏基线
- [Dao et al. — FlashAttention-2 (arXiv:2307.08691)](https://arxiv.org/abs/2307.08691) —— NSA kernel 在 64k 上击败的全注意力基线
