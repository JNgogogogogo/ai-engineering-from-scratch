# Multi-Head Attention · 多头注意力

> One attention head learns one relation at a time. Eight heads learn eight. Heads are free. Take more of them.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 7 · 02 (Self-Attention from Scratch)
**Time:** ~75 minutes

## The Problem · 问题在哪

单个自注意力头只计算一个注意力矩阵。那个矩阵捕捉一种关系——通常是在当前训练信号下让 loss 最小的那一种。如果你的数据里主谓一致、共指（co-reference）、长距离语篇、句法分块全都缠在一起，一个头会把它们抹进同一个 softmax 分布，丢掉一半信号。

2017 年 Vaswani 论文给出的修法：并行运行多个注意力函数，每个有自己的 Q、K、V 投影，再把输出拼接起来。每个头在维度为 `d_model / n_heads` 的更小子空间里工作。总参数量不变。表达能力上升。

多头注意力是 2026 年每一台 transformer 出厂自带的默认配置。唯一还有争论的是*头要多少个*，以及 key 和 value 是否共享投影（Grouped-Query Attention、Multi-Query Attention、Multi-head Latent Attention）。

> A single self-attention head computes one attention matrix. That matrix captures one kind of relationship — usually the one that minimizes loss on whatever the training signal is. ... The fix from the 2017 Vaswani paper: run several attention functions in parallel, each with its own Q, K, V projections, and concatenate the outputs. Each head operates in a smaller subspace of dimension `d_model / n_heads`. Total parameters stay the same. Expressive power goes up. ... Multi-head attention is the default every transformer in 2026 ships with.

## The Concept · 概念

![多头注意力：切分、注意、拼接](../assets/multi-head-attention.svg)

**切分（Split）。** 取形状为 `(N, d_model)` 的 `X`。投影成 Q、K、V，各为 `(N, d_model)`。重排成 `(N, n_heads, d_head)`，其中 `d_head = d_model / n_heads`。转置成 `(n_heads, N, d_head)`。

**并行注意（Attend in parallel）。** 在每个头内部运行缩放点积注意力。每个头产出 `(N, d_head)`。各头在嵌入的不同子空间上工作，注意力计算本身互不通信。

**拼接并投影（Concatenate and project）。** 把各头堆回 `(N, d_model)`，再乘一个形状为 `(d_model, d_model)` 的可学习输出矩阵 `W_o`。`W_o` 就是头与头之间混合的地方。

**为什么有效。** 每个头可以专精自己的分工，不必跟其他头抢表示预算。2019–2024 年的探针研究显示出头的分工各不相同：位置头、注意前一个 token 的头、复制头、命名实体头、归纳头（induction head，in-context learning 的底层机制）。

**2026 年的变体谱系：**

| 变体 | Q 头数 | K/V 头数 | 使用者 |
|---------|---------|-----------|---------|
| Multi-head（MHA） | N | N | GPT-2、BERT、T5 |
| Multi-query（MQA） | N | 1 | PaLM、Falcon |
| Grouped-query（GQA） | N | G（如 N/8） | Llama 2 70B、Llama 3+、Qwen 2+、Mistral |
| Multi-head latent（MLA） | N | 压缩到低秩 | DeepSeek-V2、V3 |

GQA 是现代默认：它把 KV-cache 内存砍到 `N/G` 分之一，质量几乎不损失。MLA 走得更远——把 K/V 压进一个潜空间（latent space），计算时再投影回来——多花 FLOPs，省下多得多的内存。

```figure
multihead-split
```

> **Split.** Take `X` of shape `(N, d_model)`. Project to Q, K, V each of shape `(N, d_model)`. Reshape to `(N, n_heads, d_head)` where `d_head = d_model / n_heads`. Transpose to `(n_heads, N, d_head)`. ... **Concatenate and project.** Stack heads back to `(N, d_model)` and multiply by a learned output matrix `W_o` of shape `(d_model, d_model)`. `W_o` is where heads get to mix. ... **Why it works.** Each head can specialize without competing with the others for representational budget. ... GQA is the modern default because it cuts KV-cache memory by a factor of `N/G` while keeping nearly full quality.

## Build It · 动手造

### Step 1: split heads from the single-head attention we already have · 从已有的单头注意力切出多头

拿第 02 课的 `SelfAttention`，给它包一层切分/拼接。numpy 实现见 `code/main.py`；逻辑是：

```python
def split_heads(X, n_heads):
    n, d = X.shape
    d_head = d // n_heads
    return X.reshape(n, n_heads, d_head).transpose(1, 0, 2)  # (heads, n, d_head)

def combine_heads(H):
    h, n, d_head = H.shape
    return H.transpose(1, 0, 2).reshape(n, h * d_head)
```

一次 reshape 加一次 transpose。没有循环。这正是 PyTorch 在 `nn.MultiheadAttention` 底下做的事。

> Take the `SelfAttention` from Lesson 02 and wrap it with a split/concat pair. See `code/main.py` for a numpy implementation; the logic is:
> One reshape and one transpose. No loop. This is exactly what PyTorch does under `nn.MultiheadAttention`.

### Step 2: run scaled-dot-product attention per head · 每个头跑缩放点积注意力

每个头拿到 Q、K、V 自己的一份。注意力变成一个批量矩阵乘（batched matmul）：

```python
def mha_forward(X, W_q, W_k, W_v, W_o, n_heads):
    Q = X @ W_q
    K = X @ W_k
    V = X @ W_v
    Qh = split_heads(Q, n_heads)         # (heads, n, d_head)
    Kh = split_heads(K, n_heads)
    Vh = split_heads(V, n_heads)
    scores = Qh @ Kh.transpose(0, 2, 1) / np.sqrt(Qh.shape[-1])
    weights = softmax(scores, axis=-1)
    out = weights @ Vh                    # (heads, n, d_head)
    concat = combine_heads(out)
    return concat @ W_o, weights
```

在真实硬件上，`Qh @ Kh.transpose(...)` 是一条 `bmm`。GPU 看到的是形状 `(heads, N, d_head) × (heads, d_head, N) -> (heads, N, N)` 的单个批量矩阵乘。加头是免费的。

> Each head gets its own slice of Q, K, V. Attention becomes a batched matmul:
> On real hardware `Qh @ Kh.transpose(...)` is one `bmm`. The GPU sees a single batched matmul of shape `(heads, N, d_head) × (heads, d_head, N) -> (heads, N, N)`. Adding heads is free.

### Step 3: Grouped-Query Attention variant · Grouped-Query Attention 变体

只有 key 和 value 投影变了。Q 有 `n_heads` 组；K 和 V 只有 `n_kv_heads < n_heads` 组，重复到与 Q 匹配为止：

```python
def gqa_project(X, W, n_kv_heads, n_heads):
    kv = split_heads(X @ W, n_kv_heads)       # (kv_heads, n, d_head)
    repeat = n_heads // n_kv_heads
    return np.repeat(kv, repeat, axis=0)      # (n_heads, n, d_head)
```

推理时这省内存，因为 KV cache 里只活 `n_kv_heads` 份拷贝，不是 `n_heads`。Llama 3 70B 用 64 个 query 头配 8 个 KV 头——缓存缩到 1/8。

> Only the key and value projections change. Q gets `n_heads` groups; K and V get `n_kv_heads < n_heads` groups and are repeated to match:
> At inference this saves memory because only `n_kv_heads` copies live in the KV cache, not `n_heads`. Llama 3 70B uses 64 query heads with 8 KV heads — an 8× cache shrink.

### Step 4: probe what each head learned · 探查每个头学到了什么

在一个短句子上跑 4 头的 MHA。对每个头，打印它的 `(N, N)` 注意力矩阵。你会看到不同的头挑出不同的结构，即便是随机初始化——一部分是信号，一部分是子空间里的旋转对称性。

> Run MHA on a short sentence with 4 heads. For each head, print the `(N, N)` attention matrix. You'll see different heads pick out different structure even with random initialization — that's partly signal, partly rotational symmetry in the subspaces.

## Use It · 实战用法

PyTorch 里的一行版：

```python
import torch.nn as nn

mha = nn.MultiheadAttention(embed_dim=512, num_heads=8, batch_first=True)
```

PyTorch 2.5+ 的 GQA：

```python
from torch.nn.functional import scaled_dot_product_attention

# scaled_dot_product_attention auto-dispatches Flash Attention on CUDA.
# For GQA, pass Q of shape (B, n_heads, N, d_head) and K,V of shape
# (B, n_kv_heads, N, d_head). PyTorch handles the repeat.
out = scaled_dot_product_attention(q, k, v, is_causal=True, enable_gqa=True)
```

**头要多少个？** 来自 2026 年生产模型的经验法则：

| 模型规模 | d_model | n_heads | d_head |
|------------|---------|---------|--------|
| 小型（~125M） | 768 | 12 | 64 |
| 基础（~350M） | 1024 | 16 | 64 |
| 大型（~1B） | 2048 | 16 | 128 |
| 前沿（~70B） | 8192 | 64 | 128 |

`d_head` 几乎总是落在 64 或 128。它是一个头「能看多少」的单位。低于 32，头开始跟缩放因子 `sqrt(d_head)` 打架；高于 256，你就丢掉了「一群小专家」的好处。

> **How many heads?** Rules of thumb from production models in 2026:
> `d_head` almost always lands at 64 or 128. It is the unit of how much one head can "see." Drop below 32 and heads start fighting the scaling factor `sqrt(d_head)`; go above 256 and you lose the "many small specialists" benefit.

## Ship It · 交付

见 `outputs/skill-mha-configurator.md`。该技能在给定参数预算、序列长度、部署目标的情况下，为新 transformer 推荐头数、kv 头数和投影策略。

> See `outputs/skill-mha-configurator.md`. The skill recommends head count, kv-head count, and projection strategy for a new transformer given parameter budget, sequence length, and deployment target.

## Exercises · 练习

1. **简单。** 拿 `code/main.py` 里的 MHA，固定 `d_model=64`，把 `n_heads` 从 1 改到 16。画一个单层小模型在合成复制任务上的 loss。更多的头是帮忙、躺平，还是帮倒忙？
2. **中等。** 实现 MQA（所有 query 头共享一个 KV 头）。测参数量比完整 MHA 降了多少。算推理时 N=2048 的 KV-cache 缩小了多少。
3. **困难。** 实现一个迷你版 Multi-head Latent Attention：把 K、V 压成秩-`r` 潜变量，KV cache 里存潜变量，注意力时再解压。`r` 取多少时，缓存内存降到完整 MHA 的 1/8 以下，同时质量保持在验证 ppl 的 1 bit 以内？

## Key Terms · 术语表

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|-----------------|-----------------------|
| 头（Head） | 「一条注意力回路」 | 一个维度为 `d_head = d_model / n_heads` 的 Q/K/V 投影，有自己的注意力矩阵。 |
| d_head | 「头维度」 | 每头的隐藏宽度；生产中几乎总是 64 或 128。 |
| 切分/拼接（Split / combine） | 「reshape 技巧」 | 注意力前后的 `(N, d_model) ↔ (n_heads, N, d_head)` reshape+transpose。 |
| W_o | 「输出投影」 | 头拼接之后乘的 `(d_model, d_model)` 矩阵；头在这里混合。 |
| MQA | 「一个 KV 头」 | Multi-Query Attention：单个共享的 K/V 投影。KV cache 最小，有一些质量损失。 |
| GQA | 「Llama 2 以来的默认」 | Grouped-Query Attention，`n_kv_heads < n_heads`；重复到与 Q 匹配。 |
| MLA | 「DeepSeek 的招」 | Multi-head Latent Attention：K、V 压成低秩潜变量，注意力时解压。 |
| 归纳头（Induction head） | 「in-context learning 背后的回路」 | 一对头：检测先前的出现位置，并复制其后继内容。 |

## Further Reading · 延伸阅读

- [Vaswani et al. (2017). Attention Is All You Need §3.2.2](https://arxiv.org/abs/1706.03762) —— 多头的原始规格。
- [Shazeer (2019). Fast Transformer Decoding: One Write-Head is All You Need](https://arxiv.org/abs/1911.02150) —— MQA 论文。
- [Ainslie et al. (2023). GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints](https://arxiv.org/abs/2305.13245) —— 训练完怎么把 MHA 转成 GQA。
- [DeepSeek-AI (2024). DeepSeek-V2 Technical Report](https://arxiv.org/abs/2405.04434) —— MLA，以及它在缓存内存上为什么打赢 MHA/GQA。
- [Olsson et al. (2022). In-context Learning and Induction Heads](https://transformer-circuits.pub/2022/in-context-learning-and-induction-heads/index.html) —— 对头到底在干嘛的机制性研究。
