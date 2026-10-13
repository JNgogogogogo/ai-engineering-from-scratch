# The Full Transformer — Encoder + Decoder · 完整 Transformer（编码器 + 解码器）

> Attention is the star. Everything else — residuals, normalization, feed-forward, cross-attention — is the scaffolding that lets you stack it deep.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 7 · 02 (Self-Attention), Phase 7 · 03 (Multi-Head Attention), Phase 7 · 04 (Positional Encoding)
**Time:** ~75 minutes

## The Problem · 问题在哪

单层注意力只是一个特征提取器，不是一个模型。每层一次矩阵乘法，这点容量应付不了语言。你需要深度——而没有正确的「管道工程」，一加深就会崩。

2017 年的 Vaswani 论文打包了六个设计决策，把单层注意力变成了可堆叠的块。此后的每一个 Transformer——encoder-only（BERT）、decoder-only（GPT）、encoder-decoder（T5）——都继承同一个骨架。到 2026 年，块内部被不断精炼（RMSNorm、SwiGLU、pre-norm、RoPE），但骨架一模一样。

本课讲的就是这个骨架。接下来几课对它做特化——06 讲编码器，07 讲解码器，08 讲编码器-解码器。

> A single attention layer is a feature extractor, not a model. One matmul per layer is not enough capacity for language. You need depth — and depth breaks without the right plumbing.
> The 2017 Vaswani paper packaged six design decisions that turned one attention layer into a stackable block. Every transformer since — encoder-only (BERT), decoder-only (GPT), encoder-decoder (T5) — inherits the same skeleton. In 2026 the blocks have been refined (RMSNorm, SwiGLU, pre-norm, RoPE) but the skeleton is identical.
> This lesson is the skeleton. Next lessons specialize it — 06 for encoders, 07 for decoders, 08 for encoder-decoder.

## The Concept · 概念

![Encoder and decoder block internals, wired](../assets/full-transformer.svg)

### The six pieces · 六个部件

1. **嵌入 + 位置信号。** Token → 向量。位置通过 RoPE（现代）或正弦编码（经典）注入。
2. **自注意力。** 每个位置都看到所有其他位置。在解码器中要加 mask。
3. **前馈网络（FFN）。** 逐位置的两层 MLP：`W_2 · activation(W_1 · x)`。默认扩展比 4×。
4. **残差连接。** `x + sublayer(x)`。没有它，梯度过了约 6 层就会消失。
5. **层归一化。** `LayerNorm` 或 `RMSNorm`（现代）。稳住残差流。
6. **交叉注意力（仅解码器）。** Query 来自解码器，Key 和 Value 来自编码器输出。

看一个向量流过一个块：注意力在位置之间混合信息，残差把它向前带，FFN 对它做变换，归一化让数据流保持稳定。

```figure
transformer-block
```

> 1. **Embedding + positional signal.** Tokens → vectors. Position injected via RoPE (modern) or sinusoidal (classic).
> 2. **Self-attention.** Every position attends to every other. Masked in decoders.
> 3. **Feed-forward network (FFN).** Position-wise two-layer MLP: `W_2 · activation(W_1 · x)`. Expansion ratio 4× by default.
> 4. **Residual connection.** `x + sublayer(x)`. Without this, gradients vanish past ~6 layers.
> 5. **Layer normalization.** `LayerNorm` or `RMSNorm` (modern). Stabilizes the residual stream.
> 6. **Cross-attention (decoder only).** Queries come from the decoder, keys and values from the encoder output.
> Watch a vector flow through one block: attention mixes across positions, the residual carries it forward, the FFN transforms it, and norm keeps the stream stable.

### Encoder block (used by BERT, T5 encoder) · 编码器块（BERT、T5 编码器在用）

```
x → LN → MHA(self) → + → LN → FFN → + → out
                     ^              ^
                     |              |
                     └── residual ──┘
```

编码器是双向的。没有 mask。所有位置看到所有位置。

> Encoder is bidirectional. No masking. All positions see all positions.

### Decoder block (used by GPT, T5 decoder) · 解码器块（GPT、T5 解码器在用）

```
x → LN → MHA(masked self) → + → LN → MHA(cross to encoder) → + → LN → FFN → + → out
```

解码器每个块有三个子层。中间那个——交叉注意力——是信息从编码器流向解码器的唯一通道。在纯 decoder-only 架构（GPT）里，交叉注意力被省掉，只剩 masked 自注意力 + FFN。

> Decoder has three sublayers per block. The middle one — cross-attention — is the only place information flows from encoder to decoder. In a pure decoder-only architecture (GPT), cross-attention is omitted and you just have masked self-attention + FFN.

### Pre-norm vs post-norm · Pre-norm 对 post-norm

原始论文给出的形式：`x + sublayer(LN(x))` 对比 `LN(x + sublayer(x))`。Post-norm 在 2019 年前后失宠——没有精细的 warmup，很难训得深。Pre-norm（`LN` 放在子层*之前*）是 2026 年的默认：Llama、Qwen、GPT-3+、Mistral 全在用。

> Original paper: `x + sublayer(LN(x))` vs `LN(x + sublayer(x))`. Post-norm lost favor around 2019 — it is harder to train deeply without careful warmup. Pre-norm (`LN` *before* sublayer) is the 2026 default: Llama, Qwen, GPT-3+, Mistral all use it.

### The 2026 modernized block · 2026 年的现代化块

Vaswani 2017 交付的是 LayerNorm + ReLU。现代技术栈把两者都换掉了。生产级块实际长这样：

| 部件 | 2017 | 2026 |
|------|------|------|
| 归一化 | LayerNorm | RMSNorm |
| FFN 激活 | ReLU | SwiGLU |
| FFN 扩展比 | 4× | 2.6×（SwiGLU 用三个矩阵，总参数量对齐） |
| 位置编码 | 正弦绝对位置 | RoPE |
| 注意力 | 标准 MHA | GQA（或 MLA） |
| 偏置项 | 有 | 无 |

RMSNorm 去掉了 LayerNorm 的均值中心化（少一次减法），省算力，且实测稳定性至少不打折。SwiGLU（`Swish(W1 x) ⊙ W3 x`）在 Llama、PaLM 和 Qwen 的论文里，稳定地比 ReLU/GELU FFN 好 ~0.5 个 ppl 点。

> Vaswani 2017 shipped LayerNorm + ReLU. Modern stacks replaced both. What production blocks actually look like:
> RMSNorm drops the mean-centering of LayerNorm (one fewer subtraction), which saves compute and is empirically at least as stable. SwiGLU (`Swish(W1 x) ⊙ W3 x`) consistently outperforms ReLU/GELU FFN by ~0.5 point ppl in the Llama, PaLM and Qwen papers.

### Parameter count · 参数量

对一个 `d_model = d`、FFN 扩展比为 `r` 的块：

- MHA：`4 · d²`（Q、K、V、O 四个投影）
- FFN（SwiGLU）：`3 · d · (r · d)` ≈ `3rd²`
- 归一化层：可忽略

取 `d = 4096, r = 2.6, layers = 32`（大致是 Llama 3 8B），总计：`32 · (4·4096² + 3·2.6·4096²) ≈ 32 · (16 + 32) M = ~1.5B parameters per layer × 32 ≈ 7B`（外加 embedding 和输出头）。与公开发布的参数量对得上。

> For one block with `d_model = d` and FFN expansion `r`:
> - MHA: `4 · d²` (Q, K, V, O projections)
> - FFN (SwiGLU): `3 · d · (r · d)` ≈ `3rd²`
> - Norms: negligible
> At `d = 4096, r = 2.6, layers = 32` (roughly Llama 3 8B), total: `32 · (4·4096² + 3·2.6·4096²) ≈ 32 · (16 + 32) M = ~1.5B parameters per layer × 32 ≈ 7B` (plus embeddings and head). Matches published counts.

## Build It · 动手造

### Step 1: the building blocks · 第 1 步：基础组件

使用第 03 课的迷你 `Matrix` 类（为保证本课独立可跑，已复制到本文件）：

- `layer_norm(x, eps=1e-5)` —— 减均值，除以标准差。
- `rms_norm(x, eps=1e-6)` —— 除以 RMS。不减均值。
- `gelu(x)` 与 `silu(x) * W3 x`（SwiGLU）。
- `ffn_swiglu(x, W1, W2, W3)`。
- `encoder_block(x, params)` 与 `decoder_block(x, enc_out, params)`。

完整接线见 `code/main.py`。

> Using the tiny `Matrix` class from Lesson 03 (copied to this file for independence):
> - `layer_norm(x, eps=1e-5)` — subtract mean, divide by std.
> - `rms_norm(x, eps=1e-6)` — divide by RMS. No mean subtraction.
> - `gelu(x)` and `silu(x) * W3 x` (SwiGLU).
> - `ffn_swiglu(x, W1, W2, W3)`.
> - `encoder_block(x, params)` and `decoder_block(x, enc_out, params)`.
> See `code/main.py` for the full wiring.

### Step 2: wire a 2-layer encoder and a 2-layer decoder · 第 2 步：接一个 2 层编码器和 2 层解码器

把它们堆起来。编码器输出送进每一个解码器交叉注意力。输出投影之前加一个最终的 LN。

```python
def encode(tokens, params):
    x = embed(tokens, params.emb) + sinusoidal(len(tokens), params.d)
    for block in params.encoder_blocks:
        x = encoder_block(x, block)
    return x

def decode(target_tokens, encoder_out, params):
    x = embed(target_tokens, params.emb) + sinusoidal(len(target_tokens), params.d)
    for block in params.decoder_blocks:
        x = decoder_block(x, encoder_out, block)
    return x
```

> Stack them. Pass the encoder output into every decoder cross-attention. Add a final LN before the output projection.

### Step 3: run forward on a toy example · 第 3 步：在玩具示例上前向跑通

喂一个 6-token 的源序列和 5-token 的目标序列。验证输出形状是 `(5, vocab)`。不训练——本课关注的是架构，不是损失。

> Feed a 6-token source and a 5-token target through. Verify the output shape is `(5, vocab)`. No training — this lesson is about the architecture, not the loss.

### Step 4: swap in RMSNorm + SwiGLU · 第 4 步：换上 RMSNorm + SwiGLU

用 RMSNorm 和 SwiGLU 替换 LayerNorm 和 ReLU-FFN。确认形状仍然对得上。只换两个函数，就完成了 2026 年的现代化改造。

> Replace LayerNorm and ReLU-FFN with RMSNorm and SwiGLU. Confirm shapes still match. This is the 2026 modernization with one function substitution.

## Use It · 实战用法

PyTorch/TF 的参考实现：`nn.TransformerEncoderLayer`、`nn.TransformerDecoderLayer`。但 2026 年大多数生产代码都自己写块，因为：

- Flash Attention 是在注意力内部直接调用，不走 `nn.MultiheadAttention`。
- GQA / MLA 不在标准库参考实现里。
- RoPE、RMSNorm、SwiGLU 都不是 PyTorch 的默认项。

HF `transformers` 里有值得读的干净参考块：`modeling_llama.py` 是 2026 年 decoder-only 块的典范。约 500 行，值得通读一次。

**Encoder、decoder 还是 encoder-decoder——怎么选：**

| 需求 | 选择 | 例子 |
|------|------|------|
| 文本分类、embedding、篇章问答 | Encoder-only | BERT, DeBERTa, ModernBERT |
| 文本生成、聊天、代码、推理 | Decoder-only | GPT, Llama, Claude, Qwen |
| 结构化输入 → 结构化输出（翻译、摘要） | Encoder-decoder | T5, BART, Whisper |

Decoder-only 赢下了语言任务，因为它扩展得最干净，理解和生成都能兼顾。当输入有清晰的「源序列」身份时（翻译、语音识别、结构化任务），encoder-decoder 仍然是最佳选择。

> The PyTorch/TF reference implementations: `nn.TransformerEncoderLayer`, `nn.TransformerDecoderLayer`. But most 2026 production code rolls its own block because:
> - Flash Attention is called inside attention, not via `nn.MultiheadAttention`.
> - GQA / MLA are not in the stdlib reference.
> - RoPE, RMSNorm, SwiGLU are not the PyTorch defaults.
> HF `transformers` has clean reference blocks you should read: `modeling_llama.py` is the canonical 2026 decoder-only block. It's ~500 lines and worth walking through once.
> **Encoder vs decoder vs encoder-decoder — when to pick:**
> Decoder-only won language because it scales cleanest and handles both comprehension and generation. Encoder-decoder is still best when the input has a clear "source sequence" identity (translation, speech recognition, structured tasks).

## Ship It · 交付

见 `outputs/skill-transformer-block-reviewer.md`。这个 skill 拿 2026 年的默认配置审查一份新的 transformer 块实现，标出缺失的部件（pre-norm、RoPE、RMSNorm、GQA、FFN 扩展比）。

> See `outputs/skill-transformer-block-reviewer.md`. The skill reviews a new transformer block implementation against the 2026 defaults and flags missing pieces (pre-norm, RoPE, RMSNorm, GQA, FFN expansion ratio).

## Exercises · 练习

1. **简单。** 算出 `d_model=512, n_heads=8, ffn_expansion=4, swiglu=True` 时你的 encoder_block 参数量。通过实现这个块并用 `sum(p.numel() for p in block.parameters())` 来验证。
2. **中等。** 把 post-norm 换成 pre-norm。两种都初始化，在随机输入上测量堆叠 12 层后的激活范数。Post-norm 的激活应该会爆炸；pre-norm 的应该保持有界。
3. **困难。** 在玩具拷贝任务（把 `x` 倒序复制）上实现一个 4 层 encoder-decoder。训练 100 步并报告 loss。换上 RMSNorm + SwiGLU + RoPE——loss 会降吗？

> 1. **Easy.** Count the parameters in your encoder_block at `d_model=512, n_heads=8, ffn_expansion=4, swiglu=True`. Validate by implementing the block and using `sum(p.numel() for p in block.parameters())`.
> 2. **Medium.** Switch from post-norm to pre-norm. Initialize both and measure the activation norm after 12 stacked layers on random input. Post-norm's activations should explode; pre-norm's should stay bounded.
> 3. **Hard.** Implement a 4-layer encoder-decoder on a toy copy task (copy `x` reversed). Train 100 steps. Report loss. Swap in RMSNorm + SwiGLU + RoPE — does loss drop?

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------|---------|
| Block | 「一个 transformer 层」 | 归一化 + 注意力 + 归一化 + FFN 的堆叠，外面包着残差连接。 |
| Residual（残差） | 「跳跃连接」 | 输出为 `x + f(x)`；让梯度能流过深层堆叠。 |
| Pre-norm | 「先归一化，后子层」 | 现代形式：`x + sublayer(LN(x))`。不需要 warmup 杂技也能训得更深。 |
| RMSNorm | 「不减均值的 LayerNorm」 | 除以 RMS；少一次运算，实测稳定性相当。 |
| SwiGLU | 「大家都换用的 FFN」 | `Swish(W1 x) ⊙ W3 x → W2`。在语言模型 ppl 上胜过 ReLU/GELU。 |
| Cross-attention（交叉注意力） | 「解码器看编码器的方式」 | MHA，Q 来自解码器，K/V 来自编码器输出。 |
| FFN expansion（FFN 扩展比） | 「中间 MLP 有多宽」 | 隐藏层大小与 d_model 之比，通常为 4（LayerNorm）或 2.6（SwiGLU）。 |
| Bias-free（无偏置） | 「去掉 +b 项」 | 现代技术栈在线性层里省略偏置；ppl 略有改善，模型更小。 |

## Further Reading · 延伸阅读

- [Vaswani et al. (2017). Attention Is All You Need](https://arxiv.org/abs/1706.03762) —— 原始块规格。
- [Xiong et al. (2020). On Layer Normalization in the Transformer Architecture](https://arxiv.org/abs/2002.04745) —— 为什么网络深了以后 pre-norm 胜过 post-norm。
- [Zhang, Sennrich (2019). Root Mean Square Layer Normalization](https://arxiv.org/abs/1910.07467) —— RMSNorm。
- [Shazeer (2020). GLU Variants Improve Transformer](https://arxiv.org/abs/2002.05202) —— SwiGLU 论文。
- [HuggingFace `modeling_llama.py`](https://github.com/huggingface/transformers/blob/main/src/transformers/models/llama/modeling_llama.py) —— 2026 年 decoder-only 块的典范代码。
