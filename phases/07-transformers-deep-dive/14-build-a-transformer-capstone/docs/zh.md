# Build a Transformer from Scratch — The Capstone · 从零构建 Transformer —— 毕业设计（十三课，一个模型，没有捷径）

> Thirteen lessons. One model. No shortcuts.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 7 · 01 到 13 课。不要跳课。
**Time:** ~120 分钟

## The Problem · 问题在哪

你已经读遍了该读的论文，也已经亲手实现了注意力、多头切分、位置编码、编码器与解码器块、BERT 与 GPT 损失、MoE、KV cache。现在，让它们在一个真实任务上协同工作。

毕业设计（capstone）是：在一个字符级（character-level）语言建模任务上，端到端训练一个小型 decoder-only transformer。它读莎士比亚，然后生成新的「莎士比亚」。它足够小，在笔记本电脑上 10 分钟内就能训完；又足够正确，只要换上更大的数据集、训练更久，你就能得到一个真正的语言模型（LM）。

这就是本课程的「nanoGPT」。它并非原创 —— Karpathy 2023 年的 nanoGPT 教程是每个学生至少手写一遍的参考实现。我们沿用它的骨架，并围绕本课程已经覆盖的内容重新打磨。

> You've read every paper. You've implemented attention, multi-head splits, positional encodings, encoder and decoder blocks, BERT and GPT losses, MoE, KV cache. Now make them work together on a real task. ... The capstone: train a small decoder-only transformer end-to-end on a character-level language modeling task. It reads Shakespeare. It generates new Shakespeare. It is small enough to train on a laptop in under 10 minutes. It is correct enough that swapping in a bigger dataset and longer training gets you a real LM. ... This is the "nanoGPT" of the course. It is not original — Karpathy's 2023 nanoGPT tutorial is the reference implementation every student writes at least once. We lift the shape and retool it around what we've covered.

## The Concept · 概念

![Transformer-from-scratch block diagram](../assets/capstone.svg)

架构总览（带注解）：

```
input tokens (B, N)
   │
   ▼
token embedding + positional embedding  ◀── Lesson 04 (RoPE option)
   │
   ▼
┌──── block × L ────────────────────┐
│  RMSNorm                          │  ◀── Lesson 05
│  MultiHeadAttention (causal)      │  ◀── Lesson 03 + 07 (causal mask)
│  residual                         │
│  RMSNorm                          │
│  SwiGLU FFN                       │  ◀── Lesson 05
│  residual                         │
└────────────────────────────────── ┘
   │
   ▼
final RMSNorm
   │
   ▼
lm_head (tied to token embedding)
   │
   ▼
logits (B, N, V)
   │
   ▼
shift-by-one cross-entropy            ◀── Lesson 07
```

> The architecture, annotated:

### What we ship · 我们交付什么

- `GPTConfig` —— 所有超参数的统一配置入口。
- `MultiHeadAttention` —— 因果（causal）、批量化的多头注意力，带可选的 Flash 风格路径（PyTorch 的 `scaled_dot_product_attention`）。
- `SwiGLUFFN` —— 现代 FFN。
- `Block` —— pre-norm、残差包裹的注意力 + FFN。
- `GPT` —— embedding、堆叠的 block、LM head、generate()。
- 训练循环：AdamW、cosine 学习率、梯度裁剪。
- 莎士比亚文本上的字符级 tokenizer。

> `GPTConfig` — one place to configure all hyperparameters.
> `MultiHeadAttention` — causal, batched, with optional Flash-style pathway (PyTorch's `scaled_dot_product_attention`).
> `SwiGLUFFN` — modern FFN.
> `Block` — pre-norm, residual-wrapped attention + FFN.
> `GPT` — embeddings, stacked blocks, LM head, generate().
> Training loop with AdamW, cosine LR, gradient clipping.
> Char-level tokenizer on Shakespeare text.

### What we don't ship · 我们不交付什么

- RoPE —— 第 04 课已在概念上实现过。这里为了简单使用可学习的位置 embedding。练习会要求你把它换进来。
- 生成时的 KV cache —— 生成的每一步都对整个前缀重算注意力。更慢但更简单。练习会要求你加上 KV cache。
- Flash Attention —— PyTorch 2.0+ 会在输入匹配时自动分派；我们用 `F.scaled_dot_product_attention`。
- MoE —— 每个 block 一个 FFN。MoE 你已经在第 11 课见过。

> RoPE — implemented conceptually in Lesson 04. Here we use learned positional embeddings for simplicity. The exercises ask you to swap in RoPE.
> KV cache during generation — each generation step recomputes attention over the full prefix. Slower but simpler. The exercises ask you to add a KV cache.
> Flash Attention — PyTorch 2.0+ auto-dispatches if the inputs match; we use `F.scaled_dot_product_attention`.
> MoE — single FFN per block. You saw MoE in Lesson 11.

### Target metrics · 目标指标

在一台 Mac M2 笔记本上，一个 4 层、4 头、d_model=128 的 GPT 在 `tinyshakespeare.txt` 上训练 2,000 步：

- 训练 loss 从 ~4.2（随机初始化）收敛到 ~1.5，耗时约 6 分钟。
- 采样输出已经「像莎士比亚」：古体词、换行、以及「ROMEO:」这类人名格式都会浮现。
- 验证 loss（held-out 的最后 10% 文本）与训练 loss 贴得很近；在这个规模/预算下没有过拟合。

> On a Mac M2 laptop, a 4-layer, 4-head, d_model=128 GPT trained for 2,000 steps on `tinyshakespeare.txt`:
> Training loss converges from ~4.2 (random) to ~1.5 in about 6 minutes.
> Sampled output looks Shakespeare-shaped: archaic words, line breaks, proper names like "ROMEO:" emerge.
> Val loss (held-out final 10% of text) tracks training loss closely; no overfitting at this size/budget.

```figure
n5-block-stack
```

## Build It · 动手造

本课使用 PyTorch。安装 `torch`（CPU 版即可）。见 `code/main.py`。脚本会处理：

- `tinyshakespeare.txt` 缺失时自动下载（或读取本地副本）。
- 字节级字符 tokenizer。
- 90/10 的训练/验证切分。
- 在支持的硬件上使用 bf16 autocast 的训练循环。
- 训练完成后采样生成。

> This lesson uses PyTorch. Install `torch` (CPU build is fine). See `code/main.py`. The script handles:
> Downloading `tinyshakespeare.txt` if missing (or reading a local copy).
> Byte-level char tokenizer.
> Train/val split at 90/10.
> Training loop with bf16 autocast on supported hardware.
> Sampling after training completes.

### Step 1: data · 数据

```python
text = open("tinyshakespeare.txt").read()
chars = sorted(set(text))
stoi = {c: i for i, c in enumerate(chars)}
itos = {i: c for c, i in stoi.items()}
encode = lambda s: [stoi[c] for c in s]
decode = lambda xs: "".join(itos[x] for x in xs)
```

共 65 个不同字符。词表极小，一个 4 字节的 vocab_size 就装得下。没有 BPE，没有 tokenizer 的麻烦事。

> 65 unique characters. Tiny vocabulary. Fits a 4-byte vocab_size. No BPE, no tokenizer drama.

### Step 2: model · 模型

见 `code/main.py`。这个 block 就是第 05 课的教科书式结构 —— pre-norm、RMSNorm、SwiGLU、因果 MHA。4 层/4 头/128 维的参数量约 80 万（~800K）。

> See `code/main.py`. The block is textbook from Lesson 05 — pre-norm, RMSNorm, SwiGLU, causal MHA. Parameter count for 4/4/128: ~800K.

### Step 3: training loop · 训练循环

取一个随机 batch 的长度 256 token 窗口。前向。错一位（shift-by-one）交叉熵。反向。AdamW 更新一步。打日志。重复。

```python
for step in range(max_steps):
    x, y = get_batch("train")
    logits = model(x)
    loss = F.cross_entropy(logits.view(-1, vocab_size), y.view(-1))
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    opt.step()
    opt.zero_grad()
```

> Get a random batch of length-256 token windows. Forward. Shift-by-one cross-entropy. Backward. AdamW step. Log. Repeat.

### Step 4: sample · 采样

给定 prompt，反复执行：前向、从 top-p logits 采样、把新 token 接到末尾、继续。生成满 500 个 token 后停止。

> Given a prompt, repeatedly forward, sample from top-p logits, append, and continue. Stop after 500 tokens.

### Step 5: read the output · 读输出

2,000 步之后：

```
ROMEO:
Away and mild will not thy friend, that thou shalt wit:
The chief that well shame and hath been his friends,
...
```

不是莎士比亚，但已经有莎士比亚的形状。对 ~80 万参数、笔记本上 6 分钟的投入来说，这是一场干净的胜利。

> Not Shakespeare. But Shakespeare-shaped. A clear win for ~800K parameters and 6 minutes on a laptop.

## Use It · 实战用法

这个毕业设计是一个参考架构。三个扩展可以把它推向真实的东西：

1. **换 tokenizer。** 用 BPE（例如 `tiktoken.get_encoding("cl100k_base")`）。词表从 65 跳到约 50,000。模型容量也要相应放大来补偿。
2. **在更大的语料上训练。** 用 `OpenWebText` 或 `fineweb-edu`（HuggingFace）。单个 A100 上训一个 125M 参数的 GPT、吃 10B token 大约要 24 小时。
3. **加上 RoPE + KV cache + Flash Attention。** 下面的练习会带你逐个完成。

最终你会得到一个能生成流畅英文的 125M 参数 GPT。不是前沿模型。但同一条代码路径 —— 只是更大 —— 就是 Karpathy、EleutherAI 和 Allen Institute 在 2026 年训练研究 checkpoint 时用的东西。

> This capstone is a reference architecture. Three extensions to ship it to something real:
> 1. **Swap the tokenizer.** Use BPE (e.g. `tiktoken.get_encoding("cl100k_base")`). Vocab size jumps from 65 to ~50,000. Model capacity needs to scale up to compensate.
> 2. **Train on a bigger corpus.** Use `OpenWebText` or `fineweb-edu` (HuggingFace). 10B tokens on a single A100 takes ~24 hours for a 125M-param GPT.
> 3. **Add RoPE + KV cache + Flash Attention.** The exercises below walk you through each.
> This ends up as a 125M-parameter GPT that generates fluent English. Not a frontier model. But the same code path — just bigger — is what Karpathy, EleutherAI, and the Allen Institute use to train research checkpoints in 2026.

## Ship It · 交付

见 `outputs/skill-transformer-review.md`。这个技能（skill）会对照此前全部 13 课，审查一个从零实现的 transformer 的正确性。

> See `outputs/skill-transformer-review.md`. The skill reviews a transformer-from-scratch implementation for correctness across all 13 prior lessons.

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。验证你训练出的模型最后一步的验证 loss 低于 2.0。把 `max_steps` 从 2,000 改成 5,000 —— 验证 loss 还会继续改善吗？
2. **中等。** 把可学习的位置 embedding 换成 RoPE：在 `MultiHeadAttention` 内部对 Q 和 K 施加旋转。训练并验证验证 loss 至少不比原来高。
3. **中等。** 在采样循环里实现 KV cache。分别带 cache 和不带 cache 各生成 500 个 token。在笔记本上墙钟时间应该能快 5–20 倍。
4. **困难。** 给模型加第二个预测头，去预测「下下个」token（MTP —— 来自 DeepSeek-V3 的 Multi-Token Prediction）。联合训练。它有帮助吗？
5. **困难。** 把每个 block 的单个 FFN 换成 4 专家 MoE：router + top-2 路由。在激活参数量对齐的前提下，看验证 loss 如何变化。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| nanoGPT | 「Karpathy 的教程仓库」 | 极简的 decoder-only transformer 训练代码，约 300 行；公认的参考实现。 |
| tinyshakespeare | 「标准玩具语料」 | 约 1.1 MB 文本；2015 年以来每个字符级 LM 教程都在用它。 |
| Tied embeddings | 「输入/输出共享矩阵」 | LM head 权重 = token embedding 矩阵的转置；省参数、提质量。 |
| bf16 autocast | 「训练精度技巧」 | 前向/反向用 bf16 跑，优化器状态留在 fp32；2021 年起成为标准。 |
| Gradient clipping | 「防梯度爆炸」 | 把全局梯度范数限制在 1.0；防止训练炸掉。 |
| Cosine LR schedule | 「2020 年后的默认」 | 学习率先线性爬升（warmup），再按余弦形状衰减到峰值的 10%。 |
| MFU | 「Model FLOP Utilization」 | 实际 FLOPs / 理论峰值；2026 年 dense 40%、MoE 30% 就算强。 |
| Val loss | 「held-out loss」 | 模型从未见过的数据上的交叉熵；过拟合探测器。 |

## Further Reading · 延伸阅读

- [The Annotated Transformer (Harvard NLP)](https://nlp.seas.harvard.edu/annotated-transformer/) —— 经典的逐行注解实现。
