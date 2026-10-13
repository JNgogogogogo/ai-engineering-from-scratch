# Attention Variants — Sliding Window, Sparse, Differential · 注意力变体 —— 滑动窗口、稀疏、差分（弯折注意力的圆环，把省下的成本拿回来）

> Full attention is a circle. Every token sees every token, and memory pays the price. Four variants bend the shape of the circle and recover half the cost.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 7 · 02（自注意力）、Phase 7 · 03（多头）、Phase 7 · 12（KV Cache / Flash Attention）
**Time:** ~60 分钟

## The Problem · 问题在哪

全注意力（full attention）的内存和计算在序列长度上都是 `O(N²)`。对一个 128K 上下文的 Llama 3 70B 来说，这意味着每层 160 亿个注意力条目，再乘以 80 层。Flash Attention（第 12 课）把 `O(N²)` 的激活内存藏了起来，但没有改变算术量 —— 每个 token 仍然要看到其他所有 token。

三类变体直接改变注意力矩阵本身的拓扑：

1. **滑动窗口注意力（sliding window attention, SWA）。** 每个 token 只看固定窗口内的邻居，不看整个前缀。内存和计算降到 `O(N · W)`，`W` 是窗口大小。用例：Gemma 2/3、Mistral 7B 的前几层、Phi-3-Long。
2. **稀疏 / 分块注意力（sparse / block attention）。** 只有被选中的 `(i, j)` 对参与打分；其余强制为零权重。用例：Longformer、BigBird、OpenAI sparse transformer。
3. **差分注意力（differential attention）。** 用两组独立的 Q/K 投影算出两张注意力图，一张减去另一张。杀掉把权重「漏」给前几个 token 的「注意力黑洞（attention sink）」。用例：微软的 DIFF Transformer（2024）。

它们可以共存。2026 年的前沿模型常常混着用：大多数层是 SWA-1024，每五层有一个全局全注意力层，再配少量差分头做检索清理。Gemma 3 的 5:1 SWA 对全局比例是当前的教科书默认。

> Full attention costs `O(N²)` memory and `O(N²)` compute in sequence length. For a 128K-context Llama 3 70B that is 16 billion attention entries per layer, times 80 layers. ... Three classes of variants change the topology of the attention matrix itself: ... **Sliding window attention (SWA).** Each token attends to a fixed window of neighbors, not the full prefix. Memory and compute drop to `O(N · W)` where `W` is the window. ... **Differential attention.** Compute two attention maps with separate Q/K projections, subtract one from the other. Kills the "attention sink" that bleeds weight into the first few tokens. ... These coexist. A 2026 frontier model often mixes them: most layers are SWA-1024, every fifth is global full attention, and a handful are differential heads that clean up retrieval. Gemma 3's 5:1 SWA-to-global ratio is the current textbook default.

## The Concept · 概念

### Sliding Window Attention (SWA) · 滑动窗口注意力

位置 `i` 上的每个 query 只关注 `[i - W, i]`（因果 SWA）或 `[i - W/2, i + W/2]`（双向）内的位置。窗口外的 token 在打分矩阵里拿到 `-inf`。

```
full causal:           sliding window (W=4):
positions 0-7          positions 0-7, W=4
    0 1 2 3 4 5 6 7        0 1 2 3 4 5 6 7
0 | x                0 |  x
1 | x x              1 |  x x
2 | x x x            2 |  x x x
3 | x x x x          3 |  x x x x
4 | x x x x x        4 |    x x x x
5 | x x x x x x      5 |      x x x x
6 | x x x x x x x    6 |        x x x x
7 | x x x x x x x x  7 |          x x x x
```

取 `N = 8192`、`W = 1024`：打分矩阵期望只有 1024 × 8192 个非零行 —— 缩减 8 倍。

**KV cache 随 SWA 一起缩小。** 每层只需要保留 K 和 V 的最后 `W` 个 token。对一个 Gemma-3 风格的配置（窗口 1024、上下文 128K），KV cache 缩小 128 倍。

**质量代价。** 纯 SWA 的 transformer 在长程检索上吃力。解法：把 SWA 层和全注意力层交错排布。Gemma 3 用的是 5:1 的 SWA 对全局。Mistral 7B 用的是一个因果 SWA 堆叠，让信息透过重叠窗口「向前流」—— 每一层把有效感受野（effective receptive field）扩大 `W`，`L` 层之后模型能往回看 `L × W` 个 token。

> Each query at position `i` attends only to positions in `[i - W, i]` (causal SWA) or `[i - W/2, i + W/2]` (bidirectional). Tokens outside the window get `-inf` in the score matrix. ... **KV cache shrinks with SWA.** Only the last `W` tokens of K and V need to be kept per layer. For a Gemma-3-ish config (1024 window, 128K context), KV cache drops 128×. ... **Quality cost.** SWA-only transformers struggle with long-range retrieval. The fix: interleave SWA layers with full-attention layers. Gemma 3 uses 5:1 SWA:global. ... each layer extends effective receptive field by `W`, and after `L` layers the model can attend `L × W` tokens back.

### Sparse / Block Attention · 稀疏 / 分块注意力

提前选定一个 `N × N` 的稀疏模式。三种经典形状：

- **局部 + 跨步（local + strided，OpenAI sparse transformer）。** 关注最后 `W` 个 token，再外加在此之前每隔 `stride` 个取一个的 token。以 `O(N · sqrt(N))` 的计算量同时抓住局部和长程。
- **Longformer / BigBird。** 局部窗口 + 一小撮全局 token（例如 `[CLS]`）：它们关注所有人、也被所有人关注，再加随机稀疏连接。经验上在相同质量下换来 2 倍上下文。
- **Native Sparse Attention（DeepSeek，2025）。** 学习 `(Q, K)` 的哪些块重要；在 kernel 层面跳过零块。与 FlashAttention 兼容。

稀疏注意力本质上是一个 kernel 工程故事。数学很简单（给打分矩阵加掩码）；收益来自永远不把零条目加载进 SRAM。FlashAttention-3 和 2026 年的 FlexAttention API 让自定义稀疏模式在 PyTorch 里成了一等公民。

> Pick an `N × N` sparsity pattern ahead of time. Three canonical shapes: ... **Local + strided (OpenAI sparse transformer).** Attend to the last `W` tokens plus every `stride`-th token before that. Captures both local and long-range at `O(N · sqrt(N))` compute. ... **Longformer / BigBird.** Local window + a small set of global tokens (e.g. `[CLS]`) that attend to everyone and are attended by everyone + random-sparse links. Empirical 2× context at matched quality. ... **Native Sparse Attention (DeepSeek, 2025).** Learn which blocks of `(Q, K)` matter; skip the zero blocks at kernel level. FlashAttention-compatible. ... Sparse attention is a kernel-engineering story. The math is simple (mask the score matrix); the win comes from never loading the zero entries into SRAM.

### Differential Attention (DIFF Transformer, 2024) · 差分注意力

常规注意力有一个「注意力黑洞（attention sink）」问题：softmax 强制每一行求和为 1，于是那些其实不想关注任何东西的 token 会把权重倾倒给第一个 token（或前几个）。这偷走了本该留给真实内容的容量。

差分注意力的修法是计算**两张**注意力图再相减：

```
A1 = softmax(Q1 K1^T / √d)
A2 = softmax(Q2 K2^T / √d)
DiffAttn = (A1 - λ · A2) V
```

其中 `λ` 是一个可学习标量（通常 0.5–0.8）。A1 捕捉真实内容的权重；A2 捕捉黑洞。相减抵消黑洞，把权重重新分配给相关的 token。

已报告的结果（微软 2024）：困惑度（perplexity）低 5–10%，同样训练长度下有效上下文长 1.5–2 倍，needle-in-haystack 检索更锐利。

> Regular attention has an "attention sink" problem: softmax forces every row to sum to 1, so tokens that don't want to attend to anything in particular dump weight on the first token (or the first few). This steals capacity that should have gone to real content. ... where `λ` is a learned scalar (typically 0.5–0.8). A1 captures real content weights; A2 captures the sink. Subtraction cancels the sink, reallocates weight to relevant tokens. ... Reported results (Microsoft 2024): 5–10% lower perplexity, 1.5–2× longer effective context at same trained length, sharper needle-in-haystack retrieval.

### Variant Comparison · 变体对比

| 变体 | 计算量 | KV cache | 相比全注意力的质量 | 生产使用 |
|---------|----------|-----------------|----------------|----------------|
| Full attention（全注意力） | O(N²) | 每层 O(N) | 基线 | 所有模型的默认层 |
| SWA（窗口 1024） | O(N·W) | 每层 O(W) | -0.1 ppl，配合全局层表现好 | Gemma 2/3、Phi-3-Long |
| 局部 + 跨步稀疏 | O(N·√N) | 混合 | 与 SWA 相近 | OpenAI sparse transformer、Longformer |
| BigBird（局部 + 全局 + 随机） | O(N) 近似 | 混合 | 2 倍上下文下追平全注意力 | 早期长上下文 BERT |
| Native Sparse（DeepSeek-V3.2） | O(N · 激活比例) | O(N) | 0.05 ppl 以内 | DeepSeek-V3.2、2025 |
| 差分（Differential） | O(2·N²) | O(2N) | ppl 低 5–10% | DIFF Transformer、2026 年初的模型 |

> | Variant | Compute | KV cache | Quality vs full | Production use |
> |---------|---------|----------|-----------------|----------------|
> | Full attention | O(N²) | O(N) per layer | baseline | every model's default layer |
> | SWA (window 1024) | O(N·W) | O(W) per layer | -0.1 ppl, good with global layers | Gemma 2/3, Phi-3-Long |
> | Local + strided sparse | O(N·√N) | mixed | similar to SWA | OpenAI sparse transformer, Longformer |
> | BigBird (local + global + random) | O(N) approx | mixed | matches full at 2× context | early long-context BERT |
> | Native Sparse (DeepSeek-V3.2) | O(N · active fraction) | O(N) | within 0.05 ppl | DeepSeek-V3.2, 2025 |
> | Differential | O(2·N²) | O(2N) | -5 to -10% ppl | DIFF Transformer, early 2026 models |

```figure
gqa-kv-sharing
```

## Build It · 动手造

见 `code/main.py`。我们实现了一个因果掩码对比器，在一条玩具序列上并排展示 full、SWA、local+strided 和 differential 注意力。

> See `code/main.py`. We implement a causal mask comparator that shows full, SWA, local+strided, and differential attention side by side on a toy sequence.

### Step 1: full causal mask (baseline) · 全因果掩码（基线）

```python
def causal_mask(n):
    return [[0.0 if j <= i else float("-inf") for j in range(n)] for i in range(n)]
```

第 07 课的基线。下三角；对角线之上权重为零。

> Baseline from Lesson 07. Lower triangular; zero weight above the diagonal.

### Step 2: sliding window causal mask · 滑动窗口因果掩码

```python
def swa_mask(n, window):
    M = [[float("-inf")] * n for _ in range(n)]
    for i in range(n):
        lo = max(0, i - window + 1)
        for j in range(lo, i + 1):
            M[i][j] = 0.0
    return M
```

只有一个参数 —— `window`。`window >= n` 时你就还原出完整因果注意力；`window = 1` 时每个 token 只看自己。

> One parameter — `window`. For `window >= n`, you recover full causal attention. For `window = 1`, each token attends only to itself.

### Step 3: local + strided sparse mask · 局部 + 跨步稀疏掩码

```python
def strided_mask(n, window, stride):
    M = [[float("-inf")] * n for _ in range(n)]
    for i in range(n):
        lo = max(0, i - window + 1)
        for j in range(lo, i + 1):
            M[i][j] = 0.0
        for j in range(0, i + 1, stride):
            M[i][j] = 0.0
    return M
```

稠密的局部窗口，加上回溯到序列开头、每隔 `stride` 个取一个的 token。感受野随层数按对数级步数增长。

> Dense local window plus every `stride`-th token back to the start of the sequence. Receptive field grows in log steps with additional layers.

### Step 4: differential attention · 差分注意力

```python
def diff_attention(Q1, K1, Q2, K2, V, lam):
    A1 = softmax_causal(Q1 @ K1.T / sqrt_d)
    A2 = softmax_causal(Q2 @ K2.T / sqrt_d)
    return (A1 - lam * A2) @ V
```

两次注意力前向，用一个可学习的混合系数相减。代码里我们对比单注意力与差分注意力的 attention-sink 热力图，看着黑洞坍缩。

> Two attention passes, subtract with a learned mixing coefficient. In the code we compare the attention-sink heatmap of single vs differential and watch the sink collapse.

### Step 5: KV cache sizes · KV cache 大小

打印 `N = 131072` 时每种变体每层的 cache 大小。SWA 和稀疏变体缩小 10–100 倍；差分翻倍。清醒地为自己的内存账单买单。

> Print the cache size per layer at `N = 131072` for each variant. SWA and sparse variants drop by 10–100×. Differential doubles. Pay your memory bill consciously.

## Use It · 实战用法

2026 年的生产模式：

```python
from transformers import AutoModelForCausalLM
# Gemma 3 mixes SWA (window=1024) and global layers at 5:1.
model = AutoModelForCausalLM.from_pretrained("google/gemma-3-27b-it")
# print(model.config.sliding_window, model.config.layer_types)
```

PyTorch 2.5+ 的 FlexAttention 接受一个掩码函数：

```python
from torch.nn.attention.flex_attention import flex_attention, create_block_mask

def swa_pattern(b, h, q_idx, kv_idx):
    return (q_idx - kv_idx < 1024) & (q_idx >= kv_idx)

mask = create_block_mask(swa_pattern, B=batch, H=heads, Q_LEN=n, KV_LEN=n)
out = flex_attention(q, k, v, block_mask=mask)
```

它会被编译成定制 Triton kernel。常见模式下能达到 FlashAttention-3 速度的 90% 以内，而且掩码函数就是一个 Python callable。

**什么时候选哪个：**

- **纯全注意力** —— 上下文 ~16K 以内的每一层都用它；或检索质量绝对优先时。
- **SWA + 全局混合** —— 长上下文（>32K）、训练和推理都受内存约束。这是 2026 年 32K 以上的默认。
- **稀疏分块注意力** —— 定制 kernel、定制模式。留给专用负载（检索、音频）。
- **差分注意力** —— 任何被 attention sink 污染所伤害的负载（长上下文 RAG、needle-in-haystack）。

> FlexAttention in PyTorch 2.5+ accepts a mask function:
> This compiles to a custom Triton kernel. Within 10% of FlashAttention-3 speed for common patterns, and the mask function is a Python callable.
> **When to pick each:**
> - **Pure full attention** — every layer up to ~16K context, or when retrieval quality is paramount.
> - **SWA + global mix** — long context (>32K), training and inference memory-bound. The 2026 default above 32K.
> - **Sparse block attention** — custom kernel, custom pattern. Reserved for specialized workloads (retrieval, audio).
> - **Differential attention** — any workload where attention-sink contamination hurts (long-context RAG, needle-in-haystack).

## Ship It · 交付

见 `outputs/skill-attention-variant-picker.md`。这个技能（skill）在给定目标上下文长度、检索需求和训练/推理算力画像时，为新模型挑选注意力拓扑。

> See `outputs/skill-attention-variant-picker.md`. The skill picks an attention topology for a new model given target context length, retrieval demands, and training/inference compute profile.

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。验证 `window=4` 的 SWA 把每行最后 4 个 token 之外的全部清零；验证 `window=n` 与完整因果注意力逐位（bit-identical）一致。
2. **中等。** 在第 07 课 capstone 之上实现 `window=1024` 的因果 SWA。在 tinyshakespeare 上训 1,000 步。相比全注意力，验证 loss 退化了多少？峰值内存降了多少？
3. **困难。** 在 capstone 模型里实现 Gemma-3 风格的 5:1 层混合（5 层 SWA、1 层全局）。在参数量对齐的前提下，与纯 SWA 和纯全局基线比较 loss、内存和生成质量。
4. **困难。** 实现每个头带可学习 `λ` 的差分注意力。在一个合成检索任务（1 根 needle、2,000 个干扰项）上训练。在参数量对齐下测量相对单注意力基线的检索准确率。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Sliding window attention (SWA) | 「局部注意力」 | 每个 query 只看自己最近 `W` 个 token；KV cache 缩到 `O(W)`。 |
| Effective receptive field | 「模型能回看多远」 | 在窗口为 `W` 的 `L` 层 SWA 堆叠中，最多 `L × W` 个 token。 |
| Longformer / BigBird | 「局部 + 全局 + 随机」 | 带少数永远全连接的全局 token 的稀疏模式；早期长上下文方案。 |
| Native Sparse Attention | 「DeepSeek 的 kernel 技巧」 | 学习块级稀疏性；在 kernel 层面跳过零块且不损质量。 |
| Differential attention | 「两张图，一减」 | DIFF Transformer：从第一张注意力图减去可学习 `λ` 倍的第二张，抵消 attention sink。 |
| Attention sink | 「权重漏给 token 0」 | softmax 归一化强制每行和为 1；无信息量的 query 把权重倾倒在位置 0。 |
| FlexAttention | 「掩码即 Python」 | PyTorch 2.5+ API，把任意掩码函数编译成 FlashAttention 形状的 kernel。 |
| Layer type mix | 「5:1 SWA 对全局」 | 在堆叠中交错稀疏与全注意力层，用更低的内存保住质量。 |

## Further Reading · 延伸阅读

- [Beltagy, Peters, Cohan (2020). Longformer: The Long-Document Transformer](https://arxiv.org/abs/2004.05150) —— 滑动窗口 + 全局 token 的奠基论文。
- [Zaheer et al. (2020). Big Bird: Transformers for Longer Sequences](https://arxiv.org/abs/2007.14062) —— 局部 + 全局 + 随机。
- [Child et al. (2019). Generating Long Sequences with Sparse Transformers](https://arxiv.org/abs/1904.10509) —— OpenAI 的局部 + 跨步模式。
- [Gemma Team (2024). Gemma 2: Improving Open Language Models at a Practical Size](https://arxiv.org/abs/2408.00118) —— 1:1 的 SWA 对全局混合。
- [Gemma Team (2025). Gemma 3 technical report](https://arxiv.org/abs/2503.19786) —— window=1024 的 5:1 混合，如今的教科书默认。
- [Ye et al. (2024). Differential Transformer](https://arxiv.org/abs/2410.05258) —— DIFF Transformer 论文。
- [Yuan et al. (2025). Native Sparse Attention](https://arxiv.org/abs/2502.11089) —— DeepSeek-V3.2 的可学习稀疏注意力。
- [PyTorch — FlexAttention blog and docs](https://pytorch.org/blog/flexattention/) —— Use It 中「掩码即 callable」模式的 API 参考。
