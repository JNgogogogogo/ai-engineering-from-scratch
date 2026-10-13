# Differential Attention (V2) · 差分注意力（V2）

> Softmax 注意力会在每一个不匹配的 token 上摊出一点概率。到了 10 万 token 的规模，这些噪声累积起来会淹没信号。Differential Transformer（Ye et al., ICLR 2025）的修法是把注意力算成两个 softmax 之差，把共享的噪声底座减掉。DIFF V2（Microsoft，2026 年 1 月）是面向生产栈的重写：解码延迟追平基线 Transformer、不需要自定义 kernel、兼容 FlashAttention。本课覆盖从 V1 到 V2 的全程，并带一个可以直接在 stdlib Python 里跑通的差分操作玩具实现。

> Softmax attention spreads a small amount of probability over every non-matching token. Over 100k tokens that noise adds up and drowns the signal. Differential Transformer (Ye et al., ICLR 2025) fixes it by computing attention as the difference of two softmaxes, subtracting the shared noise floor. DIFF V2 (Microsoft, January 2026) is the production-stack rewrite: matching decode latency to baseline Transformer, no custom kernels, FlashAttention-compatible. This lesson is V1 to V2 end-to-end, with a working toy implementation of the difference operation you can run in stdlib Python.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 7 · 02 (self-attention), Phase 7 · 15 (attention variants), Phase 10 · 14 (architecture walkthrough)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 精确陈述 softmax 注意力为什么存在噪声底座（noise floor），以及它为什么随上下文长度增长。
- 推导差分注意力（differential attention）公式，并解释为什么相减能消去共享噪声分量、同时保住信号。
- 走完 V1 到 V2 的 diff：什么变快了、什么变简单了、什么变稳定了，以及为什么每一处改动都是生产级预训练的必要条件。
- 用纯 Python 从零实现差分注意力，并在一个合成的「信号+噪声」查询上经验性地验证噪声抵消性质。

> State precisely why softmax attention has a noise floor and why it grows with context length.
> Derive the differential attention formula and explain why the subtraction cancels the shared noise component while preserving signal.
> Walk the V1-to-V2 diff: what got faster, what got simpler, what got more stable, and why each change was necessary for production pre-training.
> Implement differential attention from scratch in pure Python and empirically verify the noise-cancellation property on a synthetic signal-plus-noise query.

## The Problem · 问题在哪

标准 softmax 注意力有一个数学性质，到了规模上就变成运维层面的头疼事。对一个查询 `q`，注意力权重是 `softmax(qK^T / sqrt(d))`。softmax 永远产不出精确的零——每个不匹配的 token 都会分到一点正概率质量。这份残余质量就是噪声，而且它随上下文长度增长。在 128k token 下，即使每个不匹配 token 只分到 0.001% 的概率，127,999 个加起来也贡献了总量的约 12%。模型不得不学着绕开一个随上下文增长的噪声底座。

经验上，这表现为注意力头之间的相互干扰：长上下文 RAG 里编造出来的引用、10 万 token 检索任务上的 lost-in-the-middle 失败、以及超过 32k 之后 needle-in-haystack 基准上细微的精度滑坡。Differential Transformer 论文（arXiv:2410.05258, ICLR 2025）量化了差距：DIFF Transformer 拿到了更低的困惑度、更高的长上下文精度、以及比同规模基线更少的幻觉。

DIFF V1 有三个把它挡在前沿预训练流水线门外的问题。它的 value cache 每个解码步要加载两次；它需要自定义 CUDA kernel，破坏了 FlashAttention 兼容性；它的逐头 RMSNorm 在 70B 以上的规模上让长期训练失稳。DIFF V2（Microsoft unilm 博客，2026 年 1 月 20 日）把这三个全修了。本课把两个版本都走一遍，构建差分算子，并在一个玩具查询上对噪声抵消做基准测量。

> Standard softmax attention has a mathematical property that turns into an operational headache at scale. ... Softmax can never produce exact zeros — every non-matching token gets some positive mass. That residual mass is noise, and it scales with context length. At 128k tokens, even if each non-matching token gets only 0.001% of the probability, 127,999 of them combined contribute about 12% of the total. The model has to learn to route around a noise floor that grows with context.
> Empirically this shows up as attention-head interference: hallucinated citations in long-context RAG, lost-in-the-middle failures on 100k-token retrieval tasks, and subtle accuracy degradation on needle-in-haystack benchmarks past 32k. The Differential Transformer paper (arXiv:2410.05258, ICLR 2025) measured the gap: DIFF Transformers hit lower perplexity, higher long-context accuracy, and fewer hallucinations than same-size baselines.
> DIFF V1 had three problems that kept it out of frontier pre-training pipelines. ... DIFF V2 (Microsoft unilm blog, January 20, 2026) fixed all three. This lesson walks both versions, builds the difference operator, and benchmarks noise cancellation on a toy query.

## The Concept · 概念

### The noise floor of softmax · softmax 的噪声底座

对一个查询 `q` 和键 `K = [k_1, ..., k_N]`，注意力权重是：

```
w_i = exp(q . k_i / sqrt(d)) / sum_j exp(q . k_j / sqrt(d))
```

没有任何 `w_i` 会是零。如果 `k_i` 与 `q` 毫无关系，分数 `q . k_i` 也不是 0——它在零附近波动，方差为 `||q||^2 / d`。经过 softmax 归一化后，每个无关 token 仍然对加权和贡献 `O(1/N)`。所有无关 token 的总贡献是 `O((N-1)/N) = O(1)`——这不是一个小量。

模型想要的是某种硬 top-k：匹配的 token 上权重大，其余地方接近零。softmax 太平滑了，做不到。

> For a query `q` and keys `K = [k_1, ..., k_N]`, attention weights are:
> No `w_i` is ever zero. If `k_i` is completely unrelated to `q`, the score `q . k_i` is not 0 — it fluctuates around zero with variance `||q||^2 / d`. After softmax normalization, each unrelated token still contributes `O(1/N)` to the weighted sum. The total contribution of unrelated tokens is `O((N-1)/N) = O(1)` — not a small quantity.
> What the model wants is something like a hard top-k: high weight on matching tokens, near-zero weight everywhere else. Softmax is too smooth to do that directly.

### The differential idea · 差分思想

把每个头的 Q、K 投影各拆成两份：Q = (Q_1, Q_2) 和 K = (K_1, K_2)。计算两张注意力图：

```
A_1 = softmax(Q_1 K_1^T / sqrt(d))
A_2 = softmax(Q_2 K_2^T / sqrt(d))
```

输出：

```
DiffAttn = (A_1 - lambda * A_2) V
```

相减会消去两张图共享的那部分噪声分布。如果两张图对那 12.7 万个无关 token 都摊了大致均匀的权重（随机初始化时必然如此），它们就互相抵消。而信号——集中在少数真正相关 token 上的尖峰权重——只有当它以同样大小出现在两张图里时才会被抵消；模型一旦开始训练，这就不会发生。

`lambda` 是每头一个的可学习标量，参数化为 `lambda = exp(lambda_q1 dot lambda_k1) - exp(lambda_q2 dot lambda_k2) + lambda_init`。它可以是负数。`lambda_init` 默认取一个小的正数，比如 0.8。

> Split each head's Q and K projections into two: Q = (Q_1, Q_2) and K = (K_1, K_2). Compute two attention maps:
> The subtraction cancels whatever noise distribution the two maps share. If both maps have roughly uniform weight on the 127k unrelated tokens (which they will, at random initialization), those cancel. The signal — peaked weight on the few actually relevant tokens — only cancels if it appears in both maps at the same magnitude, which it will not once the model trains.
> `lambda` is a learnable scalar per head, parameterized as `lambda = exp(lambda_q1 dot lambda_k1) - exp(lambda_q2 dot lambda_k2) + lambda_init`. It can be negative. `lambda_init` defaults to a small positive number like 0.8.

### Why this matches headed noise-canceling · 为什么这像有源降噪

想象两支录下同一个声音的嘈杂麦克风。两支都收到说话人，加上相关的背景噪声。把一支从另一支里减掉，共享的噪声就没了。人声活了下来，因为两路信号在相位或幅度上差得足够多，不至于完全抵消。逐头的 `lambda` 学的正是这个平衡。

> Think of two noisy microphones recording the same voice. Both pick up the speaker plus correlated background noise. Subtract one from the other and the shared noise drops out. The voice survives because the two signals differ in phase or amplitude by enough to prevent full cancellation. The per-head `lambda` learns exactly this balance.

### V1 vs V2: the diff · V1 vs V2：改动清单

V1 把参数量保持在和基线 Transformer 持平。为了每头拿到两个查询，它把头维度砍半。代价是头的表达力，而且更难受的是：每头的 value cache 也被砍半。解码时每步要加载两次 value cache（每个 softmax 分支一次）。结果：参数量持平，解码却比基线慢。

V2 把查询头的数量翻倍、KV 头数保持不变（从上投影那里借参数）。头维度与基线保持一致。相减之后，多出来的维度再被投影回基线 Transformer 的 O_W 投影的形状。三件事同时发生：

1. 解码速度追平基线（KV cache 只加载一次）。
2. FlashAttention 原样可用（没有自定义 kernel）。
3. 解码时的算术强度上去了（从 HBM 每加载一个字节能做更多计算）。

V2 还移除了 V1 用来稳定相减的逐头 RMSNorm。在 70B 级预训练规模上，那个 RMSNorm 会让训练后期失稳。V2 用一个更简单的初始化方案取代它，不加额外模块也保住了训练稳定。

> V1 kept the parameter count equal to the baseline Transformer. To get two queries per head it halved the head dimension. That cost head expressiveness and — more painfully — halved the value cache per head. Decode had to load the value cache twice per step (once per softmax branch). Result: decode slower than baseline despite matching parameter count.
> V2 doubles the number of query heads and keeps the KV heads the same (borrowing parameters from the up-projection). The head dimension stays the same as baseline. After the subtraction, the extra dimension is projected back down to match baseline Transformer's O_W projection. Three things happen at once:
> 1. Decode speed matches baseline (KV cache is loaded once).
> 2. FlashAttention runs unchanged (no custom kernel).
> 3. Arithmetic intensity at decode goes up (more compute per byte loaded from HBM).
> V2 also removes the per-head RMSNorm that V1 used to stabilize the subtraction. At 70B-class pre-training scales, that RMSNorm destabilized late training. V2 replaces it with a simpler initialization scheme that keeps training stable without the extra module.

### When to reach for it · 什么时候用它

| Workload | Benefit |
|----------|---------|
| 长上下文 RAG（64k+） | 更干净的注意力图，更少的编造引用 |
| Needle-in-haystack 基准 | 超过 32k 后精度大幅提升 |
| 多文档问答 | 更少的跨文档干扰 |
| 8k 代码补全 | 收益甚微，不值得改架构 |
| 短聊天（< 4k） | 与基线基本无法区分 |

价值随上下文长度增长。4k token 时噪声底座小到标准注意力足够好；128k 时它就在伤害你了。

> The value grows with context length. At 4k tokens the noise floor is small enough that standard attention is fine. At 128k it is hurting you.

### How it stacks with other 2026 knobs · 它与 2026 年其他旋钮的兼容性

| Feature | Compatible with DIFF V2? |
|---------|------------------------|
| GQA | 兼容（V2 增加的是 Q 头，不是 KV 头） |
| MLA (DeepSeek) | 原理上兼容，尚无二者结合的公开论文 |
| MoE | 兼容（注意力与 MLP 块相互独立） |
| RoPE | 兼容（原样不动） |
| YaRN / 长上下文缩放 | 兼容（恰好是 DIFF 帮助最大的地方） |
| FlashAttention | V2 兼容（V1 不兼容） |
| Speculative decoding | 兼容（注意力的改动对投机解码循环不可见） |

```figure
differential-attention
```

## Build It · 动手造

`code/main.py` 用纯 Python 实现差分注意力。一个具有已知「信号+噪声」结构的玩具查询，让你直接测出噪声抵消比。

> `code/main.py` implements differential attention in pure Python. A toy query with known signal-plus-noise structure lets you measure the noise-cancellation ratio directly.

### Step 1: standard softmax attention · 第 1 步：标准 softmax 注意力

标准库矩阵运算：列表的列表、手写 matmul、带数值稳定减最大值操作的 softmax。

```python
def softmax(row):
    m = max(row)
    exps = [math.exp(x - m) for x in row]
    s = sum(exps)
    return [e / s for e in exps]
```

> Stdlib matrix ops: lists of lists, manual matmul, softmax with numerical-stability subtraction of the max.

### Step 2: split Q, K into two halves · 第 2 步：把 Q、K 拆成两半

V1 风格：把头维度砍半。V2 风格：保持头维度、把头的数量翻倍。玩具实现为了教学清晰采用 V1——数学完全一样，只是簿记不同。

> V1 style: halve the head dimension. V2 style: keep the head dimension and double the number of heads. The toy implementation uses V1 for pedagogical clarity — the math is identical, only the bookkeeping differs.

### Step 3: two softmax branches + subtraction · 第 3 步：两个 softmax 分支 + 相减

```python
A1 = [softmax([dot(q1, k) / scale for k in K1]) for q1 in Q1]
A2 = [softmax([dot(q2, k) / scale for k in K2]) for q2 in Q2]
diff_weights = [[a1 - lam * a2 for a1, a2 in zip(r1, r2)] for r1, r2 in zip(A1, A2)]
out = [[sum(w * v[j] for w, v in zip(row, V)) for j in range(d_v)] for row in diff_weights]
```

注意：输出的权重可以是负数。这没问题——value cache 本来就处理带符号的贡献，符号会被后续的 V 投影吸收。

> Note: the output weights can be negative. That is fine — the value cache still handles signed contributions. The subsequent V projection absorbs the sign.

### Step 4: noise cancellation measurement · 第 4 步：噪声抵消测量

构造一条长度 1024 的合成序列。把信号 token 放在已知位置，其余用噪声填满。分别计算 (a) 标准 softmax 注意力在信号位置上的权重，(b) 差分注意力的权重，测出各自的信噪比。DIFF 注意力可靠地给出更高的信噪比，倍数在 3x-10x 之间，取决于两个分支被训练得有多不同。

> Build a synthetic sequence of length 1024. Place the signal token at a known position, fill the rest with noise. Compute (a) standard softmax attention weight on the signal position and (b) differential attention weight. Measure the ratio of signal-to-noise in each. DIFF attention reliably produces a higher signal-to-noise ratio by a factor of 3x-10x depending on how much the two branches have been trained to differ.

### Step 5: V1 vs V2 parameter accounting · 第 5 步：V1 vs V2 参数核算

给定配置（hidden=4096, heads=32, d_head=128），打印：

- 基线 Transformer：Q、K、V 各 `hidden * hidden`，MLP 为 4 * hidden。
- DIFF V1：Q、K 各 `hidden * hidden`，V 为 `hidden * hidden`（不变），头维度内部砍半。新增逐头 `lambda` 参数（O(heads * d_head)）。
- DIFF V2：Q 为 `2 * hidden * hidden`，K 为 `hidden * hidden`，V 为 `hidden * hidden`。多出的维度在 O_W 之前投影回去。新增同样的 `lambda` 参数。

玩具会测出 V2 的额外参数成本（大约每个注意力块多 `hidden * hidden`）并打印出来。

> Given a config (hidden=4096, heads=32, d_head=128), print:
> - Baseline Transformer: Q, K, V each size `hidden * hidden`, MLP at 4 * hidden.
> - DIFF V1: Q, K each size `hidden * hidden`, V size `hidden * hidden` (unchanged), head dim halved internally. Adds per-head `lambda` parameters (O(heads * d_head)).
> - DIFF V2: Q size `2 * hidden * hidden`, K size `hidden * hidden`, V size `hidden * hidden`. Extra dim projected back down before O_W. Adds same `lambda` parameters.
> The toy measures the extra parameter cost for V2 (roughly `hidden * hidden` extra per attention block) and prints it.

## Use It · 实战用法

截至 2026 年 4 月，DIFF V2 还没有在所有生产推理服务器上上线，但 vLLM 和 SGLang 的集成正在进行中。与此同时，这个模式已经出现在：

- Microsoft 内部的长上下文生产模型。
- 若干瞄准 256k+ 上下文的开源模型训练复现工作。
- 把 DIFF 注意力与滑窗注意力在相邻层交替的混合架构。

2026 年你会用它的时机：

- 从头训练一个瞄准 64k+ 有效上下文的新模型。一开始就上差分注意力；事后重训太贵。
- 微调一个 lost-in-the-middle 失败主导评测结果的长上下文模型。在 Q 投影上加 LoRA 可以近似 DIFF 结构。

你不会用它的时机：

- 你在服务一个长上下文表现稳定的预训练稠密模型。在现成权重上重训的成本几乎收不回来。
- 你的上下文始终低于 16k。噪声底座可以忽略。

> DIFF V2 is not yet shipping in every production inference server as of April 2026, but integration is underway in vLLM and SGLang. Meanwhile the pattern shows up in:
> When you would reach for this in 2026:
> - Training a new model from scratch targeting 64k-plus effective context. Add differential attention from the start; retraining later is expensive.
> - Fine-tuning a long-context model where lost-in-the-middle failures dominate your eval. A LoRA on the Q projections can approximate the DIFF structure.
> When you would not:
> - You are serving a pre-trained dense model with stable long-context performance. The retraining cost rarely pays back on existing weights.
> - Your context is always under 16k. Noise floor is negligible.

## Ship It · 交付

本课产出 `outputs/skill-diff-attention-integrator.md`。给定模型架构、目标上下文长度、幻觉画像和训练预算，它会产出一份把差分注意力集成进新预训练运行或 LoRA 微调的整合计划。

> This lesson produces `outputs/skill-diff-attention-integrator.md`. Given a model architecture, target context length, hallucination profile, and training budget, it produces an integration plan for adding differential attention to a new pre-training run or LoRA fine-tune.

## Exercises · 练习

1. 运行 `code/main.py`。验证差分注意力在合成查询上报告的信噪比高于标准 softmax 注意力。改变噪声幅度，找出标准注意力变得不可用的交叉点。

2. 计算从基线到 DIFF V1、从基线到 DIFF V2 的参数量增量，按一个 7B 级模型（hidden=4096, heads=32, d_head=128, 32 层）算。展示哪些组件增加了参数、哪些保持不变。

3. 阅读 DIFF V1 论文（arXiv:2410.05258）第 3 节和 DIFF V2 Hugging Face 博客第 2 节。用两句话解释：为什么 V1 的逐头 RMSNorm 是必要的，以及为什么 V2 能去掉它而不引发训练发散。

4. 实现一个消融实验：分别用 `lambda = 0`（纯第一个 softmax）和 `lambda = 1`（完全相减）计算差分注意力。在合成查询上测信噪比随扫描的变化。找出最大化信噪比的 `lambda`。

5. 把玩具扩展到 GQA + DIFF V2。取 8 个 KV 头、32 个 Q 头。证明其 KV cache 大小与同配置（8, 32）的基线 GQA 模型一致。

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| Differential attention | 「两个 softmax 相减」 | 把 Q、K 各拆成两半，算两张 softmax 图，把第二张（乘 lambda 后）从第一张里减掉，再乘 V |
| Noise floor | 「softmax 的非零尾巴」 | softmax 摊在每个无关 token 上的 O(1/N) 权重，长上下文里加总会变成 O(1) |
| lambda | 「相减的系数」 | 每头一个的可学习标量，参数化为 `exp(lq1.lk1) - exp(lq2.lk2) + lambda_init`；可以为负 |
| DIFF V1 | 「ICLR 2025 版本」 | 原始 Differential Transformer；砍半头维度以保持参数量，需要自定义 kernel，解码更慢 |
| DIFF V2 | 「2026 年 1 月的修复」 | Q 头翻倍而 KV 头不动；解码速度追平基线，兼容 FlashAttention |
| Per-head RMSNorm | 「V1 的稳定器」 | V1 在相减之后加的额外归一化；V2 为避免训练后期失稳而移除 |
| Signal-to-noise ratio | 「注意力浪费了多少」 | 真正信号位置上的权重与无关位置平均权重之比 |
| Lost in the middle | 「长上下文失败模式」 | 经验现象：长上下文中部的文档检索精度下陷——DIFF 注意力能减轻它 |
| Arithmetic intensity | 「每加载一字节做多少 FLOPs」 | V2 通过让每次 KV 加载对应双倍查询而提高的比值；对内存受限的解码很关键 |

## Further Reading · 延伸阅读

- [Ye et al. — Differential Transformer (arXiv:2410.05258, ICLR 2025)](https://arxiv.org/abs/2410.05258) —— 原始论文，含噪声抵消理论与长上下文消融
- [Microsoft unilm — Differential Transformer V2 (Hugging Face blog, January 2026)](https://huggingface.co/blog/microsoft/diff-attn-v2) —— 面向生产栈的重写，解码追平基线，兼容 FlashAttention
- [Understanding Differential Transformer Unchains Pretrained Self-Attentions (arXiv:2505.16333)](https://arxiv.org/abs/2505.16333) —— 为什么相减能还原预训练注意力结构的理论分析
- [Shared DIFF Transformer (arXiv:2501.17900)](https://arxiv.org/html/2501.17900) —— 参数共享变体
- [Vaswani et al. — Attention Is All You Need (arXiv:1706.03762)](https://arxiv.org/abs/1706.03762) —— DIFF 从中做减法的基线 Transformer
- [Liu et al. — Lost in the Middle (arXiv:2307.03172)](https://arxiv.org/abs/2307.03172) —— DIFF 注意力瞄准的长上下文基准
