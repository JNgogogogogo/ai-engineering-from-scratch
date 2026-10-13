# Positional Encoding — Sinusoidal, RoPE, ALiBi · 位置编码——正弦、RoPE、ALiBi

> Attention is permutation-invariant. "The cat sat on the mat" and "mat the on sat cat the" produce the same output without positional signal. Three algorithms fix it — each with a different bet on what "position" means.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 7 · 02 (Self-Attention), Phase 7 · 03 (Multi-Head Attention)
**Time:** ~45 minutes

## The Problem · 问题在哪

缩放点积注意力对顺序是盲的。注意力矩阵 `softmax(Q K^T / √d) V` 从成对相似度算出。把 `X` 的行打乱，输出的行也会按同样的方式打乱。注意力内部没有任何东西在乎位置。

在词袋模型里这不算 bug。但对语言、代码、音频、视频——任何顺序承载意义的东西——这是致命的。

修法是把位置以某种方式注入嵌入（embedding）。三代答案：

1. **绝对正弦编码（absolute sinusoidal）**（Vaswani 2017）。把位置的 `sin/cos` 加进嵌入。简单、无需学习，但超出训练长度后外推很差。
2. **RoPE——旋转位置编码（Rotary Position Embeddings）**（Su 2021）。按正比于位置的角旋转 Q 和 K 向量。在点积里直接编码*相对*位置。2026 年的主流。
3. **ALiBi——Attention with Linear Biases**（Press 2022）。完全跳过嵌入；按距离给注意力分数加一个每头线性的惩罚。长度外推极佳。

到 2026 年，几乎所有前沿开放模型都用 RoPE：Llama 2/3/4、Qwen 2/3、Mistral、Mixtral、DeepSeek-V3、Kimi。少数长上下文模型用 ALiBi 或其现代变体。绝对正弦编码已成历史。

> Scaled dot-product attention is order-blind. The attention matrix `softmax(Q K^T / √d) V` is computed from pairwise similarities. Shuffle the rows of `X`, get the rows of the output shuffled the same way. Nothing inside attention cares about position. ... That is not a bug in a bag-of-words model. For language, code, audio, video — anything where order carries meaning — it is fatal. ... The fix is to inject position into the embeddings somehow. ... As of 2026, essentially every frontier open model uses RoPE: Llama 2/3/4, Qwen 2/3, Mistral, Mixtral, DeepSeek-V3, Kimi.

## The Concept · 概念

![正弦绝对编码 vs RoPE 旋转 vs ALiBi 距离偏置](../assets/positional-encoding.svg)

### Absolute sinusoidal · 绝对正弦编码

预计算一个形状为 `(max_len, d_model)` 的固定矩阵 `PE`：

```
PE[pos, 2i]   = sin(pos / 10000^(2i / d_model))
PE[pos, 2i+1] = cos(pos / 10000^(2i / d_model))
```

然后在注意力之前 `X' = X + PE[:N]`。每个维度是不同频率的一条正弦曲线。模型学会从相位模式里读出位置。超过 `max_len` 就失效：模型只见过位置 0–2047，没有任何东西告诉它位置 2048 会发生什么。

> Pre-compute a fixed matrix `PE` of shape `(max_len, d_model)`:
> Then `X' = X + PE[:N]` before attention. Each dimension is a sinusoid at a different frequency. The model learns to read position from the phase pattern. Fails beyond `max_len`: nothing told the model what happens at position 2048 when it only saw positions 0–2047.

### RoPE · RoPE

旋转 Q 和 K 向量（不是嵌入）。对维度对 `(2i, 2i+1)`：

```
[q'_2i    ]   [ cos(pos·θ_i)  -sin(pos·θ_i) ] [q_2i   ]
[q'_2i+1  ] = [ sin(pos·θ_i)   cos(pos·θ_i) ] [q_2i+1 ]

θ_i = base^(-2i / d_head),  base = 10000 by default
```

对位置为 `pos_k` 的 key 施加同样的旋转。点积 `q'_m · k'_n` 就变成只依赖 `(m - n)` 的函数。也就是说：**注意力分数只取决于相对距离**，尽管旋转本身是按绝对位置施加的。漂亮的技巧。

扩展 RoPE：`base` 可以缩放（NTK-aware、YaRN、LongRoPE），不用重训就能外推到更长上下文。Llama 3 就是这样把上下文从 8K 扩到 128K 的。

> Rotate the Q and K vectors (not embeddings). For a pair of dimensions `(2i, 2i+1)`:
> Apply the same rotation to keys with position `pos_k`. The dot product `q'_m · k'_n` becomes a function of `(m - n)` alone. That is: **the attention score depends only on the relative distance**, even though the rotation was keyed off absolute positions. Beautiful trick.
> Extending RoPE: `base` can be scaled (NTK-aware, YaRN, LongRoPE) to extrapolate to longer contexts without retraining. Llama 3 extended from 8K to 128K context this way.

### ALiBi · ALiBi

跳过嵌入把戏。直接给注意力分数加偏置：

```
attn_score[i, j] = (q_i · k_j) / √d  -  m_h · |i - j|
```

其中 `m_h` 是每个头自己的斜率（如 `1 / 2^(8·h/H)`）。近处的 token 被增强；远处的被惩罚。训练期零成本。论文显示其长度外推胜过正弦编码，并在原始训练长度上与 RoPE 打平。

> Skip the embedding trick. Bias the attention scores directly:
> Where `m_h` is a head-specific slope (e.g. `1 / 2^(8·h/H)`). Closer tokens get boosted; far tokens get penalized. No training-time cost. The paper shows length extrapolation beats sinusoidal and matches RoPE on its original trained length.

### What to pick in 2026 · 2026 年怎么选

| 变体 | 外推 | 训练成本 | 使用者 |
|---------|---------------|---------------|---------|
| 绝对正弦编码 | 差 | 免费 | 原始 transformer、早期 BERT |
| 可学习绝对编码 | 无 | 极小 | GPT-2、GPT-3 |
| RoPE | 配合缩放很好 | 免费 | Llama 2/3/4、Qwen 2/3、Mistral、DeepSeek-V3、Kimi |
| RoPE + YaRN | 极佳 | 微调阶段 | Qwen2-1M、Llama 3.1 128K |
| ALiBi | 极佳 | 免费 | BLOOM、MPT、Baichuan |

RoPE 赢了，因为它不用改架构就能插进注意力、编码相对位置，而且它的 `base` 超参数给长上下文微调提供了一个干净利落的旋钮。

```figure
rope-explorer
```

> RoPE won because it slots into attention without changing the architecture, encodes relative position, and its `base` hyperparameter gives a clean knob for long-context fine-tuning.

## Build It · 动手造

### Step 1: sinusoidal encoding · 正弦编码

见 `code/main.py`。一个 4 行的计算：

```python
def sinusoidal(N, d):
    pe = [[0.0] * d for _ in range(N)]
    for pos in range(N):
        for i in range(d // 2):
            theta = pos / (10000 ** (2 * i / d))
            pe[pos][2 * i]     = math.sin(theta)
            pe[pos][2 * i + 1] = math.cos(theta)
    return pe
```

把它的输出加到嵌入矩阵上，放在第一个注意力层之前。

> See `code/main.py`. A 4-line computation:
> Add this to the embedding matrix before the first attention layer.

### Step 2: RoPE applied to Q, K · 把 RoPE 施加到 Q、K

RoPE 原地作用于 Q 和 K。对每一对维度：

```python
def apply_rope(x, pos, base=10000):
    d = len(x)
    out = list(x)
    for i in range(d // 2):
        theta = pos / (base ** (2 * i / d))
        c, s = math.cos(theta), math.sin(theta)
        a, b = x[2 * i], x[2 * i + 1]
        out[2 * i]     = a * c - b * s
        out[2 * i + 1] = a * s + b * c
    return out
```

关键：对位置 `m` 的 Q 和位置 `n` 的 K 施加同一个函数。它们的点积会在每个坐标对上多出一个 `cos((m-n)·θ_i)` 因子。注意力免费学到相对位置。

> RoPE operates in-place on Q and K. For each pair of dims:
> Crucial: apply the same function to Q at position `m` and K at position `n`. Their dot product picks up a `cos((m-n)·θ_i)` factor on every coordinate pair. Attention learns relative position for free.

### Step 3: ALiBi slopes and bias · ALiBi 斜率与偏置

```python
def alibi_bias(n_heads, seq_len):
    # slope_h = 2 ** (-8 * h / n_heads) for h = 1..n_heads
    slopes = [2 ** (-8 * (h + 1) / n_heads) for h in range(n_heads)]
    bias = []
    for m in slopes:
        row = [[-m * abs(i - j) for j in range(seq_len)] for i in range(seq_len)]
        bias.append(row)
    return bias  # add to attention scores before softmax
```

把 `bias[h]` 加到头 `h` 的 `(seq_len, seq_len)` 注意力分数矩阵上，然后 softmax。

> Add `bias[h]` to the `(seq_len, seq_len)` attention score matrix of head `h`, then softmax.

### Step 4: verify relative-distance property of RoPE · 验证 RoPE 的相对距离性质

取两个随机向量 `a, b`。按 `(pos_a, pos_b)` 旋转。再按 `(pos_a + k, pos_b + k)` 旋转。两个点积必须在浮点误差内相等。这个性质就是 RoPE 的全部意义——它对绝对偏移不变，只有相对间隔才重要。

> Pick two random vectors `a, b`. Rotate by `(pos_a, pos_b)`. Then by `(pos_a + k, pos_b + k)`. Both dot products must match within floating-point error. That property is the whole point of RoPE — it is invariant to the absolute offset, only the relative gap matters.

## Use It · 实战用法

PyTorch 2.5+ 在 `torch.nn.functional` 里自带 RoPE 工具。大多数生产代码用 `flash_attn` 或 `xformers`，RoPE 在注意力 kernel 内部施加。

```python
from transformers import AutoModel
model = AutoModel.from_pretrained("meta-llama/Llama-3.2-3B")
# model.config.rope_scaling → {"type": "yarn", "factor": 32.0, "original_max_position_embeddings": 8192}
```

**2026 年的长上下文技巧：**

- **NTK-aware 插值。** 从 4K 扩展到 16K+ 时，把 `base` 重缩放为 `base * (scale_factor)^(d/(d-2))`。
- **YaRN。** 更聪明的插值，在长上下文上保住注意力熵（attention entropy）。Llama 3.1 128K 用它。
- **LongRoPE。** 微软 2024 年的方法，用进化搜索挑选每个维度的缩放因子。Phi-3-Long 用它。
- **位置插值 + 微调。** 直接把位置按扩展因子缩小，再微调 1–5B token。出奇地有效。

> PyTorch 2.5+ ships RoPE utilities in `torch.nn.functional`. Most production code uses `flash_attn` or `xformers` where RoPE is applied inside the attention kernel.
> **Long-context tricks in 2026:**
> - **NTK-aware interpolation.** Rescale `base` to `base * (scale_factor)^(d/(d-2))` when extending from 4K to 16K+.
> - **YaRN.** Smarter interpolation that preserves attention entropy on long contexts. Llama 3.1 128K uses it.
> - **LongRoPE.** Microsoft's 2024 method that uses evolutionary search to pick per-dimension scale factors. Phi-3-Long uses it.
> - **Position interpolation + fine-tuning.** Just shrink positions by the extension factor and fine-tune for 1–5B tokens. Surprisingly effective.

## Ship It · 交付

见 `outputs/skill-positional-encoding-picker.md`。该技能在给定目标上下文长度、外推需求、训练预算的情况下，为新模型挑选一个位置编码策略。

> See `outputs/skill-positional-encoding-picker.md`. The skill picks an encoding strategy for a new model given target context length, extrapolation needs, and training budget.

## Exercises · 练习

1. **简单。** 把正弦 `PE` 矩阵按 `max_len=512, d=128` 画成热力图。确认「维度索引越大，条纹越宽」的模式。
2. **中等。** 实现 NTK-aware RoPE 缩放。在长度 256 的序列上训练一个小 LM，然后在长度 1024 上分别测有缩放和无缩放的表现。量一量困惑度（perplexity）。
3. **困难。** 在同一个注意力模块里实现 ALiBi 和 RoPE。在长度 512 的复制任务上训练一个 4 层 transformer。测试时外推到 2048。比较退化程度。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|-----------------|-----------------------|
| 位置编码（Positional encoding） | 「告诉注意力顺序」 | 任何加进嵌入或注意力、用来编码位置的信号。 |
| 正弦编码（Sinusoidal） | 「最早的那个」 | 加进嵌入的、几何频率的 `sin/cos`；不能外推。 |
| RoPE | 「旋转位置编码」 | 按位置相关的角旋转 Q、K；点积编码相对距离。 |
| ALiBi | 「线性偏置技巧」 | 给注意力分数加 `-m·\|i-j\|`；不需要嵌入，外推极佳。 |
| base | 「RoPE 的旋钮」 | RoPE 里的频率缩放器；推理时调大即可扩展上下文。 |
| NTK-aware | 「一个 RoPE 缩放技巧」 | 重缩放 `base`，让高频维度在上下文扩展时不被挤压。 |
| YaRN | 「讲究的那个」 | 逐维度的插值+外推，能保住注意力熵。 |
| 外推（Extrapolation） | 「超过训练长度还能用」 | 位置方案能否在训练见过的 `max_len` 之外还给出正确输出？ |

## Further Reading · 延伸阅读

- [Vaswani et al. (2017). Attention Is All You Need §3.5](https://arxiv.org/abs/1706.03762) —— 正弦编码的出处。
- [Su et al. (2021). RoFormer: Enhanced Transformer with Rotary Position Embedding](https://arxiv.org/abs/2104.09864) —— RoPE 论文。
- [Press, Smith, Lewis (2021). Train Short, Test Long: Attention with Linear Biases Enables Input Length Extrapolation](https://arxiv.org/abs/2108.12409) —— ALiBi。
- [Peng et al. (2023). YaRN: Efficient Context Window Extension of Large Language Models](https://arxiv.org/abs/2309.00071) —— RoPE 缩放的当前最优。
- [Chen et al. (2023). Extending Context Window of Large Language Models via Positional Interpolation](https://arxiv.org/abs/2306.15595) —— Meta 的 Llama 2 长上下文论文。
- [Ding et al. (2024). LongRoPE: Extending LLM Context Window Beyond 2 Million Tokens](https://arxiv.org/abs/2402.13753) —— 微软的方法，Phi-3-Long 在用，Use It 一节引用过。
- [HuggingFace Transformers — `modeling_rope_utils.py`](https://github.com/huggingface/transformers/blob/main/src/transformers/modeling_rope_utils.py) —— 每一种 RoPE 缩放方案（default、linear、dynamic、YaRN、LongRoPE、Llama-3）的生产级实现。
