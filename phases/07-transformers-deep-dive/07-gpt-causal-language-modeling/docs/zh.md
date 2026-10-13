# GPT — Causal Language Modeling · GPT——因果语言建模

> BERT sees both sides. GPT sees only the past. The triangle mask is the most consequential single line of code in modern AI.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 7 · 02 (Self-Attention), Phase 7 · 05 (Full Transformer), Phase 7 · 06 (BERT)
**Time:** ~75 minutes

## The Problem · 问题在哪

语言模型只回答一个问题：给定前 `t-1` 个 token，第 `t` 个 token 上的概率分布是什么？用这个信号训练——next-token prediction——你就得到一个能逐 token 生成任意文本的模型。

要在整个序列上端到端并行训练，必须让每个位置的预测只依赖更早的位置。否则模型会轻而易举地作弊——偷看答案。

因果掩码（causal mask）干的就是这件事。它是一个单纯的 `-inf` 上三角矩阵，在 softmax 之前加到注意力分数上。softmax 之后这些位置变成 0。每个位置只能注意它自己和更早的位置。又因为它一次性作用在整个序列上，一次前向就能得到 N 个并行的 next-token 预测。

GPT-1（2018）、GPT-2（2019）、GPT-3（2020）、GPT-4（2023）、GPT-5（2025）、Claude、Llama、Qwen、Mistral、DeepSeek、Kimi——全都是同一个核心循环的 decoder-only 因果 transformer。把它们区分开的是数据质量、规模与架构精修，以及后训练（SFT、RLHF、DPO 及其后继者）。

> A language model answers one question: given the first `t-1` tokens, what is the probability distribution over token `t`? Train on that signal — next-token prediction — and you get a model that can generate arbitrary text one token at a time.
> To train it end-to-end on a whole sequence in parallel, you need each position's prediction to depend only on earlier positions. Otherwise the model trivially cheats by looking at the answer.
> The causal mask does this. It is a single upper-triangular matrix of `-inf` values added to attention scores before softmax. After softmax, those positions become 0. Each position can attend only to itself and earlier positions. And because you apply it once to the whole sequence, you get N parallel next-token predictions in one forward pass.
> GPT-1 (2018), GPT-2 (2019), GPT-3 (2020), GPT-4 (2023), GPT-5 (2025), Claude, Llama, Qwen, Mistral, DeepSeek, Kimi — they are all decoder-only causal transformers with the same core loop. What separates them is data quality, scale and architectural refinements, and post-training (SFT, RLHF, DPO, and their successors).

## The Concept · 概念

![Causal mask creates a triangular attention matrix](../assets/causal-attention.svg)

### The mask · 掩码

给定长度为 `N` 的序列，构建一个 `N × N` 矩阵：

```
M[i, j] = 0       if j <= i
M[i, j] = -inf    if j > i
```

在 softmax 之前把 `M` 加到原始注意力分数上。`exp(-inf) = 0`，所以被 mask 的位置权重为零。注意力矩阵的每一行都是一个只覆盖之前位置的概率分布。

实现代价：一次 `torch.tril()` 调用。计算耗时：纳秒级。对整个领域的影响：一切。

> Given a sequence of length `N`, build an `N × N` matrix:
> Add `M` to the raw attention scores before softmax. `exp(-inf) = 0`, so masked positions contribute zero weight. Each row of the attention matrix is a probability distribution over previous positions only.
> Implementation cost: one `torch.tril()` call. Time to compute: nanoseconds. Impact on the field: everything.

### Where the triangle comes from · 三角形从哪来

mask 通常被讲成打在注意力上的一个补丁。把推导换个方向走，它就不再神秘：注意力是前缀平均（prefix average）的第三次精炼，而三角形就是那个平均的循环边界，写成了矩阵的形式。

**阶段 1 —— 前缀平均。** 对序列最笨的因果摘要：位置 `i` 变成位置 `0…i` 的均值。写成循环就是 `out[i] = X[:i+1].mean(0)`。同样的计算也是一次矩阵乘法。取一个全 1 的下三角矩阵，每行除以行内计数，再相乘：

```python
import numpy as np

A = np.tril(np.ones((n, n)))
A = A / A.sum(axis=1, keepdims=True)
out = A @ X
```

`A` 的第 `i` 行是 `[1/(i+1), …, 1/(i+1), 0, …, 0]`。对角线上方的零就是因果性。未来没有被「mask 掉」；未来根本就没进过这个求和。

**阶段 2 —— 可学习的权重。** 均匀平均把每个过去的 token 都当成同等相关。把 1 换成可学习的分数矩阵 `S`。此时各行不再天然和为 1，所以改用 softmax 而不是除以计数来归一化每一行。softmax 永远不会输出精确的零，这会破坏因果性——除非把未来位置的分数以 `-inf` 输入，因为 `exp(-inf) = 0`：

```python
def softmax(x, axis):
    e = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e / e.sum(axis=axis, keepdims=True)

S = S + np.triu(np.full((n, n), -np.inf), k=1)
A = softmax(S, axis=1)
out = A @ X
```

同样的三角形，同样的行随机矩阵，同样的一次矩阵乘法。`-inf` mask 不是什么新机器。它就是阶段 1 里的零元素，翻译到了 softmax 的输入域。

**阶段 3 —— 依赖内容的权重。** 阶段 2 里，`S` 训练完就固定了：不管 token 内容是什么，位置 7 对位置 3 的权重永远一样。让分数依赖 token 本身：`S = Q @ K.T / sqrt(d_k)`。其他一切不变。mask、softmax、矩阵乘——一模一样。

三个阶段，一个不变量：下三角行随机矩阵乘以序列。均匀平均、可学习的静态权重、依赖内容的权重。mask 从来不是加到注意力上的。它是从前缀平均一路存活下来的。

```figure
mask-derivation
```

> The mask is usually presented as a patch bolted onto attention. Run the derivation in the other direction and it stops being mysterious: attention is the third refinement of a prefix average, and the triangle is the loop bounds of that average, written as a matrix.
> Row `i` of `A` is `[1/(i+1), …, 1/(i+1), 0, …, 0]`. The zeros above the diagonal are the causality. Nothing about the future was masked out; the future was never in the sum.
> Same triangle, same row-stochastic matrix, same one matmul. The `-inf` mask is not new machinery. It is stage 1's zero entries, translated into softmax's input domain.
> Three stages, one invariant: a lower-triangular row-stochastic matrix times the sequence. Uniform average, learned static weights, content-dependent weights. The mask was never added to attention. It survived from the average.

### Parallel training, serial inference · 并行训练，串行推理

训练：整个 `(N, d_model)` 序列过一次前向，计算 N 个交叉熵损失（每个位置一个），求和，反向传播。沿序列并行。这就是 GPT 训练能 scale 的原因——一个 GPU pass 处理一批 100 万 token。

推理：你一个 token 一个 token 地生成。喂 `[t1, t2, t3]`，得到 `t4`。喂 `[t1, t2, t3, t4]`，得到 `t5`。喂 `[t1, t2, t3, t4, t5]`，得到 `t6`。KV cache（第 12 课）把 `t1…tn` 的隐状态存下来，每步就不用重算。但推理时的串行深度 = 输出长度。这就是自回归税，也是解码成为所有 LLM 延迟瓶颈的原因。

> Training: forward-pass the whole `(N, d_model)` sequence once, compute N cross-entropy losses (one per position), sum, backprop. Parallel along the sequence. This is why GPT training scales — you process 1M tokens in a batch in one GPU pass.
> Inference: you generate token by token. Feed `[t1, t2, t3]`, get `t4`. Feed `[t1, t2, t3, t4]`, get `t5`. Feed `[t1, t2, t3, t4, t5]`, get `t6`. The KV cache (Lesson 12) saves the hidden states of `t1…tn` so you don't recompute them each step. But serial depth at inference = output length. That is the autoregressive tax and why decoding is the latency bottleneck of every LLM.

### The loss — shift-by-one · 损失——错位一格

给定 token `[t1, t2, t3, t4]`：

- 输入：`[t1, t2, t3]`
- 目标：`[t2, t3, t4]`

对每个位置 `i`，计算 `-log P(target_i | inputs[:i+1])`。求和。这就是整个序列的交叉熵。

你听过的每一个 transformer 语言模型都用这个损失训练。预训练、微调、SFT——同一个损失，不同的数据。

> Given tokens `[t1, t2, t3, t4]`:
> - Input: `[t1, t2, t3]`
> - Targets: `[t2, t3, t4]`
> For every position `i`, compute `-log P(target_i | inputs[:i+1])`. Sum. This is the cross-entropy for the whole sequence.
> Every transformer LM you've heard of trains on this loss. Pre-training, fine-tuning, SFT — same loss, different data.

### Decoding strategies · 解码策略

训练完之后，采样的选择比人们以为的更重要。

| 方法 | 做什么 | 什么时候用 |
|------|--------|-----------|
| Greedy（贪心） | 每步取 argmax | 确定性任务、代码补全 |
| Temperature（温度） | logits 除以 T 再采样 | 创意任务，T 越高多样性越高 |
| Top-k | 只从 top-k token 里采样 | 砍掉低概率尾部 |
| Top-p（nucleus） | 从累计概率 ≥ p 的最小集合里采样 | 2020 年以来的默认；能适应分布形状 |
| Min-p | 保留 `p > min_p * max_p` 的 token | 2024 年以来；比 top-p 更擅长拒绝长尾 |
| Speculative decoding（投机解码） | 小模型起草 N 个 token，大模型验证 | 同等质量下延迟降低 2–3× |

2026 年，对开源权重模型来说 min-p + temperature 0.7 是一个合理默认。投机解码则是任何生产级推理栈的入场券。

> After training, sampling choices matter more than people think.
> In 2026, min-p + temperature 0.7 is a reasonable default for open-weights models. Speculative decoding is table stakes for any production inference stack.

### What made the "GPT recipe" work · 「GPT 配方」为什么成立

1. **Decoder-only。** 没有编码器开销。每层一次注意力 + FFN。
2. **规模化。** 124M → 1.5B → 175B → 万亿。Chinchilla 缩放定律（第 13 课）告诉你算力该怎么花。
3. **上下文学习（in-context learning）。** 大约 6B–13B 规模时涌现。模型不用微调就能跟随 few-shot 示例。
4. **RLHF。** 在人类偏好上做后训练，把原始的预训练文本模型变成聊天助手。
5. **Pre-norm + RoPE + SwiGLU。** 大规模下的训练稳定性。

核心架构自 GPT-2 以来没怎么变。所有有趣的事都发生在数据、规模和后训练上。

```figure
causal-mask
```

> 1. **Decoder-only.** No encoder overhead. One pass of attention + FFN per layer.
> 2. **Scaling.** 124M → 1.5B → 175B → trillions. Chinchilla scaling laws (Lesson 13) tell you how to spend compute.
> 3. **In-context learning.** Emerged around 6B–13B. The model can follow few-shot examples without fine-tuning.
> 4. **RLHF.** Post-training on human preferences converted raw pretrained text into chat assistants.
> 5. **Pre-norm + RoPE + SwiGLU.** Stable training at scale.
> The core architecture hasn't changed much since GPT-2. Everything interesting has happened in data, scale, and post-training.

## Build It · 动手造

### Step 1: the causal mask · 第 1 步：因果 mask

见 `code/main.py`。一行代码：

```python
def causal_mask(n):
    return [[0.0 if j <= i else float("-inf") for j in range(n)] for i in range(n)]
```

在 softmax 之前把它加到注意力分数上。整个机制就这些。

> See `code/main.py`. A one-liner:
> Add it to attention scores before softmax. That's the entire mechanism.

### Step 2: a 2-layer GPT-ish model · 第 2 步：一个 2 层的类 GPT 模型

堆两个解码器块（masked 自注意力 + FFN，没有交叉注意力）。加一个 token embedding、一个位置编码，以及一个 unembedding（与 token embedding 矩阵绑定——GPT-2 以来的标准技巧）。

> Stack two decoder blocks (masked self-attention + FFN, no cross-attention). Add a token embedding, a positional encoding, and an unembedding (tied to the token embedding matrix — a standard trick since GPT-2).

### Step 3: next-token prediction, end-to-end · 第 3 步：端到端的 next-token 预测

在 20 个 token 的玩具词表上，在每个位置产出 logits。对错位一格的目标计算交叉熵损失。不求梯度——这是前向 sanity check。

> On a 20-token toy vocab, produce logits at every position. Compute cross-entropy loss against the shift-by-one target. No gradient — this is a forward-pass sanity check.

### Step 4: sampling · 第 4 步：采样

实现 greedy、temperature、top-k、top-p、min-p。在固定 prompt 上各跑一遍并对比输出。一个采样函数就是 10 行。

> Implement greedy, temperature, top-k, top-p, min-p. Run each on a fixed prompt and compare outputs. A sampling function is 10 lines.

## Use It · 实战用法

PyTorch，2026 年的惯用写法：

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.2-3B-Instruct")
tok = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-3B-Instruct")

prompt = "Attention is all you need because"
inputs = tok(prompt, return_tensors="pt")
out = model.generate(
    **inputs,
    max_new_tokens=64,
    temperature=0.7,
    top_p=0.9,
    do_sample=True,
)
print(tok.decode(out[0]))
```

底层里，`generate()` 跑前向、取最后位置的 logits、采样下一个 token、拼上去、再重复。每个生产级 LLM 推理栈（vLLM、TensorRT-LLM、llama.cpp、Ollama、MLX）都在用重度优化实现同一个循环——batched prefill、continuous batching、KV cache 分页、投机解码。

**GPT vs BERT，各一句话：** GPT 预测 `P(x_t | x_{<t})`。BERT 预测 `P(x_masked | x_unmasked)`。损失决定了模型能不能生成。

> PyTorch, 2026 idiom:
> Under the hood, `generate()` runs the forward pass, pulls the final-position logits, samples the next token, appends it, and repeats. Every production LLM inference stack (vLLM, TensorRT-LLM, llama.cpp, Ollama, MLX) implements the same loop with heavy optimization — batched prefill, continuous batching, KV cache paging, speculative decoding.
> **GPT vs BERT, one line each:** GPT predicts `P(x_t | x_{<t})`. BERT predicts `P(x_masked | x_unmasked)`. The loss determines whether the model can generate.

## Ship It · 交付

见 `outputs/skill-sampling-tuner.md`。这个 skill 为新的生成任务挑选采样参数，并标出何时必须用确定性解码。

> See `outputs/skill-sampling-tuner.md`. The skill picks sampling parameters for a new generation task and flags when deterministic decoding is required.

## Exercises · 练习

1. **简单。** 跑 `code/main.py`，验证因果注意力矩阵在 softmax 之后是下三角的。抽查：第 3 行应该只有第 0–3 列有权重。
2. **中等。** 实现宽度为 4 的 beam search。在 10 个短 prompt 上对比 beam-4 与 greedy 的困惑度。beam 总是赢吗？（提示：通常在翻译上赢，在开放式聊天上不一定。）
3. **困难。** 实现投机解码：用一个 2 层小模型做起草，一个 6 层模型做验证。在 100 条长度 64 的补全上测量实际耗时加速比。确认输出与验证模型的 greedy 输出一致。

> 1. **Easy.** Run `code/main.py` and verify the causal attention matrix is lower-triangular after softmax. Spot-check: row 3 should have weights only in columns 0–3.
> 2. **Medium.** Implement beam search for width 4. Compare perplexity of beam-4 vs greedy on 10 short prompts. Does beam always win? (Hint: usually for translation, not for open-ended chat.)
> 3. **Hard.** Implement speculative decoding: use a tiny 2-layer model as the draft and a 6-layer model as the verifier. Measure wall-clock speedup on 100 completions of length 64. Confirm outputs match greedy of the verifier.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------|---------|
| Causal mask（因果掩码） | 「那个三角形」 | 加到注意力分数上的 `-inf` 上三角矩阵，让位置 `i` 只能看到 `≤ i` 的位置。 |
| Next-token prediction | 「那个损失」 | 每个位置上，模型分布对真实下一个 token 的交叉熵。 |
| Autoregressive（自回归） | 「一次生成一个」 | 把输出当输入喂回去；并行只在训练时有，生成时没有。 |
| Logits | 「softmax 前的分数」 | LM 头在 softmax 之前的原始输出；采样就发生在它们身上。 |
| Temperature（温度） | 「创造力旋钮」 | logits 除以 T；T→0 = greedy，T→∞ = 均匀分布。 |
| Top-p | 「nucleus 采样」 | 把分布截断到和 ≥ p 的最小集合；从剩下的里面采样。 |
| Min-p | 「比 top-p 更好」 | 保留 `p ≥ min_p × max_p` 的 token；截断阈值随分布尖锐度自适应。 |
| Speculative decoding（投机解码） | 「起草 + 验证」 | 便宜模型提出 N 个 token；大模型并行验证。 |
| Teacher forcing | 「训练技巧」 | 训练时喂真实的上一个 token，而不是模型的预测。所有 seq2seq 语言模型的标准做法。 |

## Further Reading · 延伸阅读

- [Radford et al. (2018). Improving Language Understanding by Generative Pre-Training](https://cdn.openai.com/research-covers/language-unsupervised/language_understanding_paper.pdf) —— GPT-1。
- [Radford et al. (2019). Language Models are Unsupervised Multitask Learners](https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf) —— GPT-2。
- [Brown et al. (2020). Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165) —— GPT-3 与 in-context learning。
- [Leviathan, Kalman, Matias (2023). Fast Inference from Transformers via Speculative Decoding](https://arxiv.org/abs/2211.17192) —— 投机解码论文。
- [HuggingFace `modeling_llama.py`](https://github.com/huggingface/transformers/blob/main/src/transformers/models/llama/modeling_llama.py) —— 因果 LM 的典范参考代码。
