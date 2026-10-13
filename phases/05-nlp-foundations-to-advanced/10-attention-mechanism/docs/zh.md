# Attention Mechanism — The Breakthrough · 注意力机制——突破性的一步

> The decoder stops squinting at a compressed summary and starts looking at the whole source. Everything after this is attention plus engineering.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 09 (Sequence-to-Sequence Models)
**Time:** ~45 minutes

## The Problem · 问题在哪

第 09 课结束在一个被量化的失败上：在玩具复制任务上训练的 GRU 编码器-解码器，长度 5 时准确率 89%，到长度 80 已接近瞎猜。原因是结构性的，不是训练 bug：编码器收集到的每一点信息都必须塞进一个固定尺寸的隐状态，而解码器别的什么都看不到。

Bahdanau、Cho 和 Bengio 在 2014 年发表了一个三行字的修法。不要只给解码器最终的编码器状态，把每一个编码器状态都留着。解码器每走一步，就对编码器状态算一个加权平均，权重回答「解码器此刻需要看编码器位置 `i` 多少？」这个加权平均就是上下文，而且它每一步都在变。

这就是全部思想。Transformer 是它的延伸。Self-attention 把它用到了单一序列上。Multi-head attention 让它并行跑。但 2014 年的版本已经打破了瓶颈；一旦拥有它，转向 Transformer 就只是工程问题，不再是概念问题。

> Lesson 09 ended on a measured failure. A GRU encoder-decoder trained on a toy copy task goes from 89% accuracy at length 5 to near-chance at length 80. The reason is structural, not a training bug: every bit of information the encoder gleaned has to fit in one fixed-size hidden state, and the decoder never sees anything else.
> Bahdanau, Cho, and Bengio published a three-line fix in 2014. Instead of giving the decoder only the final encoder state, keep every encoder state. ... That weighted average is the context, and it changes every decoder step.
> That is the whole idea. Transformers extended it. Self-attention applied it to a single sequence. Multi-head attention ran it in parallel. ... once you have it, the pivot to transformers is engineering, not conceptual.

## The Concept · 概念

![Bahdanau attention: decoder queries all encoder states](../assets/attention.svg)

在解码器的每一步 `t`：

1. 用上一个解码器隐状态 `s_{t-1}` 作为**查询（query）**。
2. 它和每个编码器隐状态 `h_1, ..., h_T` 打分。每个编码器位置得一个标量。
3. 对分数做 softmax，得到和为 1 的注意力权重 `α_{t,1}, ..., α_{t,T}`。
4. 上下文向量 `c_t = Σ α_{t,i} * h_i`，即编码器状态的加权平均。
5. 解码器拿 `c_t` 加上一个输出 token，产出下一个 token。

加权平均才是要点。解码器要把 "Je" 翻成 "I" 时，它给 "Je" 上的编码器状态高权重、其余低权重。要翻 "not" 时，它给 "pas" 高权重。上下文向量随每一步重新塑形。

> At each decoder step `t`: Use the previous decoder hidden state `s_{t-1}` as a **query**. Score it against every encoder hidden state `h_1, ..., h_T`. ... Softmax the scores to get attention weights `α_{t,1}, ..., α_{t,T}` that sum to 1. ... Context vector `c_t = Σ α_{t,i} * h_i`. Weighted average of encoder states.
> The weighted average is the point. When the decoder needs to translate "Je" to "I", it weights the encoder state over "Je" high and the others low. When it needs "not", it weights "pas" high. The context vector reshapes each step.

## Shapes (the thing that bites everyone) · 形状（坑所有人的地方）

每个注意力实现第一次都栽在这里。慢点读。

| 对象 | 形状 | 说明 |
|-------|-------|-------|
| 编码器隐状态 `H` | `(T_enc, d_h)` | 如果是 BiLSTM，`d_h = 2 * d_hidden` |
| 解码器隐状态 `s_{t-1}` | `(d_s,)` | 一个向量 |
| 注意力分数 `e_{t,i}` | scalar | 每个编码器位置一个 |
| 注意力权重 `α_{t,i}` | scalar | 对所有 `i` 做 softmax 之后 |
| 上下文向量 `c_t` | `(d_h,)` | 与单个编码器状态同形 |

**Bahdanau（加性）分数。** `e_{t,i} = v_α^T * tanh(W_a * s_{t-1} + U_a * h_i)`。

- `s_{t-1}` 形状 `(d_s,)`，`h_i` 形状 `(d_h,)`。
- `W_a` 形状 `(d_attn, d_s)`。`U_a` 形状 `(d_attn, d_h)`。
- tanh 里相加的结果形状 `(d_attn,)`。
- `v_α` 形状 `(d_attn,)`。与 `v_α` 的内积坍缩成一个标量。**这就是 `v_α` 的作用。** 它不神奇，它就是那个把注意力维度的向量投影成标量分数的投影。

**Luong（乘性）分数。** 三种变体：

- `dot`：`e_{t,i} = s_t^T * h_i`。要求 `d_s == d_h`，硬性约束。编码器是双向的就别用它。
- `general`：`e_{t,i} = s_t^T * W * h_i`，`W` 形状 `(d_s, d_h)`。解除了等维约束。
- `concat`：本质就是 Bahdanau 形式。前两种更便宜，所以很少用。

**一个必须点名的 Bahdanau / Luong 坑。** Bahdanau 用 `s_{t-1}`（生成当前词*之前*的解码器状态）。Luong 用 `s_t`（*之后*的状态）。混用会产生极其难调试的、微妙错误的梯度。选定一篇论文，坚持它的约定。

```figure
attention-heatmap
```

> This is where every attention implementation goes wrong the first time. Read slowly.
> **Bahdanau (additive) score.** `e_{t,i} = v_α^T * tanh(W_a * s_{t-1} + U_a * h_i)`. ... `v_α` has shape `(d_attn,)`. The inner product with `v_α` collapses to a scalar. **This is what `v_α` does.** It is not magic. It is the projection that turns an attention-dim vector into a scalar score.
> **Luong (multiplicative) score.** Three variants: `dot` ... `general` ... `concat` ...
> **One Bahdanau / Luong gotcha worth naming.** Bahdanau uses `s_{t-1}` (the decoder state *before* generating the current word). Luong uses `s_t` (the state *after*). Mixing them up produces subtly wrong gradients that are extremely hard to debug. Pick one paper and stick to its convention.

## Build It · 动手造

### Step 1: additive (Bahdanau) attention · 加性（Bahdanau）注意力

```python
import numpy as np


def additive_attention(decoder_state, encoder_states, W_a, U_a, v_a):
    projected_dec = W_a @ decoder_state
    projected_enc = encoder_states @ U_a.T
    combined = np.tanh(projected_enc + projected_dec)
    scores = combined @ v_a
    weights = softmax(scores)
    context = weights @ encoder_states
    return context, weights


def softmax(x):
    x = x - np.max(x)
    e = np.exp(x)
    return e / e.sum()
```

对照上面的表检查形状。`encoder_states` 形状 `(T_enc, d_h)`。`projected_enc` 形状 `(T_enc, d_attn)`。`projected_dec` 形状 `(d_attn,)`，靠广播对齐。`combined` 形状 `(T_enc, d_attn)`。`scores` 形状 `(T_enc,)`。`weights` 形状 `(T_enc,)`。`context` 形状 `(d_h,)`。齐活。

> Check your shapes against the table above. `encoder_states` has shape `(T_enc, d_h)`. `projected_enc` has shape `(T_enc, d_attn)`. `projected_dec` has shape `(d_attn,)` and broadcasts. `combined` has shape `(T_enc, d_attn)`. `scores` has shape `(T_enc,)`. `weights` has shape `(T_enc,)`. `context` has shape `(d_h,)`. Ship it.

### Step 2: Luong dot and general · Luong 的 dot 与 general

```python
def dot_attention(decoder_state, encoder_states):
    scores = encoder_states @ decoder_state
    weights = softmax(scores)
    return weights @ encoder_states, weights


def general_attention(decoder_state, encoder_states, W):
    projected = W.T @ decoder_state
    scores = encoder_states @ projected
    weights = softmax(scores)
    return weights @ encoder_states, weights
```

各三行代码。这就是 Luong 的论文能落地的原因：多数任务上精度相同，代码少一大截。

> Three lines each. This is why Luong's paper landed. Same accuracy on most tasks, a lot less code.

### Step 3: a worked numerical example · 数值演算示例

给定三个编码器状态（大致对应 "cat"、"sat"、"mat"）和一个与第一个最对齐的解码器状态，注意力分布集中在位置 0。把解码器状态挪到与最后一个对齐，注意力就移到位置 2。上下文向量跟着走。

```python
H = np.array([
    [1.0, 0.0, 0.2],
    [0.5, 0.5, 0.1],
    [0.1, 0.9, 0.3],
])

s_close_to_cat = np.array([0.9, 0.1, 0.2])
ctx, w = dot_attention(s_close_to_cat, H)
print("weights:", w.round(3))
```

```
weights: [0.464 0.305 0.231]
```

第一行赢了。再把解码器状态挪近第三个编码器状态，看权重随之转移。就这么回事：attention 就是显式的对齐（alignment）。

> Given three encoder states (roughly "cat", "sat", "mat") and a decoder state that aligns most with the first, the attention distribution concentrates on position 0. If the decoder state shifts to align with the last, attention moves to position 2. The context vector tracks.
> First row wins. Then move the decoder state closer to the third encoder state and watch the weights shift. That is it. Attention is explicit alignment.

### Step 4: why this is the bridge to transformers · 为什么这是通往 Transformer 的桥

把上面的语言翻译成 Q/K/V：

- **Query** = 解码器状态 `s_{t-1}`
- **Key** = 编码器状态（被打分的对象）
- **Value** = 编码器状态（被加权求和的对象）

在经典 attention 里，key 和 value 是同一个东西。Self-attention 把它们分开：你可以让一个序列对自身做查询，K 和 V 各用不同的可学习投影。Multi-head attention 用不同的可学习投影并行地跑它。Transformer 把整个舞台堆叠很多次，并把 RNN 扔掉。

数学是同一套。形状是同一套。从 Bahdanau attention 到缩放点积注意力（scaled dot-product attention），教学上的跳跃主要是记号。

> Translate the language above into Q/K/V:
> **Query** = decoder state `s_{t-1}` ... **Key** = encoder states (what we score against) ... **Value** = encoder states (what we weight and sum)
> In classical attention, keys and values are the same thing. Self-attention separates them: you can query a sequence against itself, with different learned projections for K and V. Multi-head attention runs it in parallel with different learned projections. Transformers stack the whole stage many times and drop RNNs.
> The math is the same. The shapes are the same. The pedagogical jump from Bahdanau attention to scaled dot-product attention is mostly notation.

## Use It · 实战用法

PyTorch 和 TensorFlow 都直接内置了 attention。

```python
import torch
import torch.nn as nn

mha = nn.MultiheadAttention(embed_dim=128, num_heads=8, batch_first=True)
query = torch.randn(2, 5, 128)
key = torch.randn(2, 10, 128)
value = torch.randn(2, 10, 128)

output, weights = mha(query, key, value)
print(output.shape, weights.shape)
```

```
torch.Size([2, 5, 128]) torch.Size([2, 5, 10])
```

这就是一个 Transformer 注意力层：query 是一批 5 个位置，key/value 是一批 10 个位置，各 128 维，8 个头。`output` 是增广了上下文的新 query。`weights` 是那个 5x10 的对齐矩阵，可以直接画出来看。

> PyTorch and TensorFlow ship attention directly. ... That is a transformer attention layer. Query batch of 5 positions, key/value batch of 10 positions, 128-dim each, 8 heads. `output` is the new context-augmented queries. `weights` is the 5x10 alignment matrix you can visualize.

### When classical attention still matters · 经典 attention 仍然重要的场合

- 教学。单头、单层、基于 RNN 的版本让每个概念都看得见。
- Transformer 放不下的端侧序列任务。
- 2014-2017 年的任何论文。不懂 Bahdanau 的约定你一定会读错。
- 机器翻译里的细粒度对齐分析。原始注意力权重即便在 Transformer 模型上也是可解释性工具，而读懂它们的前提是知道它们是什么。

> Pedagogy. The single-head, single-layer, RNN-based version makes every concept visible.
> On-device sequence tasks where transformers do not fit.
> Any paper from 2014-2017. You will misread it without knowing Bahdanau's convention.
> Fine-grained alignment analysis in MT. Raw attention weights are an interpretability tool even on transformer models, and reading them requires knowing what they are.

### The attention-weight-as-explanation trap · 「注意力权重即解释」的陷阱

注意力权重看起来可解释：它们是跨位置和为 1 的权重，可以画图，数值高表示「看了这里」。审稿人很吃这一套。

它们没有看起来那么可解释。Jain 和 Wallace（2019）证明，对某些任务，注意力分布可以被置换成任意替代分布，而模型预测不变。没有消融（ablation）或反事实检验，永远不要把注意力权重当作推理过程的证据。

> Attention weights look interpretable. They are weights that sum to one across positions; you can plot them; high means "looked at this." Reviewers love them.
> They are not as interpretable as they look. Jain and Wallace (2019) showed that attention distributions can be permuted and replaced by arbitrary alternatives without changing model predictions for some tasks. Never report attention weights as evidence of reasoning without an ablation or counterfactual check.

## Ship It · 交付

保存为 `outputs/prompt-attention-shapes.md`：

```markdown
---
name: attention-shapes
description: Debug shape bugs in attention implementations.
phase: 5
lesson: 10
---

Given a broken attention implementation, you identify the shape mismatch. Output:

1. Which matrix has the wrong shape. Name the tensor.
2. What its shape should be, derived from (d_s, d_h, d_attn, T_enc, T_dec, batch_size).
3. One-line fix. Transpose, reshape, or project.
4. A test to catch regressions. Typically: assert `output.shape == (batch, T_dec, d_h)` and `weights.shape == (batch, T_dec, T_enc)` and `weights.sum(dim=-1) close to 1`.

Refuse to recommend fixes that silently broadcast. Broadcast-hiding bugs surface later as silent accuracy degradation, the worst kind of attention bug.

For Bahdanau confusion, insist the decoder input is `s_{t-1}` (pre-step state). For Luong, `s_t` (post-step state). For dot-product, flag dimension mismatch between query and key as the most common first-time error.
```

> Save as `outputs/prompt-attention-shapes.md`.

## Exercises · 练习

1. **简单。** 给 `softmax` 实现掩码，让编码器的填充 token 拿到零注意力权重。在一个变长序列的 batch 上测试。
2. **中等。** 给 Luong 的 `general` 形式加上多头注意力。把 `d_h` 切成 `n_heads` 组，每组各跑 attention，再拼接。验证单头情形与你之前的实现一致。
3. **困难。** 在第 09 课的玩具复制任务上训练一个带 Bahdanau attention 的 GRU 编码器-解码器。画出准确率随序列长度的曲线，与无 attention 的基线比较。你应该看到差距随长度拉大，从而确认 attention 抬高了瓶颈。

> **Easy.** Implement `softmax` masking so padding tokens in the encoder get attention weight zero. Test on a batch with variable-length sequences.
> **Medium.** Add multi-head attention to the Luong `general` form. Split `d_h` into `n_heads` groups, run attention per head, concatenate. Verify the single-head case matches your earlier implementation.
> **Hard.** Train a GRU encoder-decoder with Bahdanau attention on the toy copy task from lesson 09. Plot accuracy vs sequence length. Compare against the no-attention baseline. You should see the gap widen as length grows, confirming attention lifts the bottleneck.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Attention | 看这里看那里 | 值序列的加权平均，权重由 query-key 相似度算出。 |
| Query, Key, Value | QKV | 三个投影：Q 提问，K 是用来匹配的，V 是用来返回的。 |
| Additive attention | Bahdanau | 前馈式打分：`v^T tanh(W q + U k)`。 |
| Multiplicative attention | Luong dot / general | 分数是 `q^T k` 或 `q^T W k`。更便宜，多数任务精度相同。 |
| Alignment matrix | 那张漂亮的图 | 注意力权重排成 `(T_dec, T_enc)` 网格。读它就知道模型在看什么。 |

## Further Reading · 延伸阅读

- [Bahdanau, Cho, Bengio (2014). Neural Machine Translation by Jointly Learning to Align and Translate](https://arxiv.org/abs/1409.0473) —— 那篇论文。
- [Luong, Pham, Manning (2015). Effective Approaches to Attention-based Neural Machine Translation](https://arxiv.org/abs/1508.04025) —— 三种分数变体及其比较。
- [Jain and Wallace (2019). Attention is not Explanation](https://arxiv.org/abs/1902.10186) —— 可解释性方面的那记警钟。
- [Dive into Deep Learning — Bahdanau Attention](https://d2l.ai/chapter_attention-mechanisms-and-transformers/bahdanau-attention.html) —— 可运行的 PyTorch 走读。
