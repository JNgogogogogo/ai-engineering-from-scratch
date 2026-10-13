# Why Transformers — The Problems with RNNs · 为什么是 Transformer——RNN 的问题

> RNNs process tokens one at a time. Transformers process all tokens at once. That single architectural bet changed every scaling curve in deep learning after 2017.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 3 (Deep Learning Core), Phase 5 · 09 (Sequence-to-Sequence), Phase 5 · 10 (Attention Mechanism)
**Time:** ~45 minutes

## The Problem · 问题在哪

2017 年以前，地球上所有最先进的序列模型——语言、翻译、语音——全都是循环神经网络（RNN）。LSTM 和 GRU 在翻译基准上当了整整五年的霸主，相当于它们那个领域的 ImageNet 时刻。那是所有人手里唯一的工具。

它们有三个致命弱点。**串行计算**意味着你无法沿时间轴并行：token `t+1` 需要 token `t` 的隐藏状态。1,024 个 token 的序列意味着在一块每个周期能做 1,000,000 次浮点运算的 GPU 上串行跑 1,024 步。在为并行而生的硬件上，训练墙钟时间却随序列长度线性增长。

**梯度消失**意味着 50 个 token 之前的信息已经被压过 50 层非线性。门控循环单元（gated recurrent unit，LSTM、GRU）缓解了这种碾压，但从没消灭它。长程依赖——"the book I read last summer on a plane to Kyoto was…"——经常断线。

**固定宽度的隐藏状态**意味着编码器要在解码器看到任何东西之前，把整个源序列挤进单个向量。源是 5 个 token 还是 500 个都无所谓；瓶颈的形状一模一样。

2017 年的论文《Attention Is All You Need》提出了一个激进方案：彻底扔掉循环。让每个位置并行地注意其他所有位置。用一次大矩阵乘法代替 1,024 次串行矩阵乘法来完成训练。

结果是到 2026 年它统治了每一种模态：语言（GPT-5、Claude 4、Llama 4）、视觉（ViT、DINOv2、SAM 3）、音频（Whisper）、生物（AlphaFold 3）、机器人（RT-2）。同一个模块，不同的输入。

> Before 2017, every state-of-the-art sequence model on the planet — language, translation, speech — was a recurrent neural network. ... Sequential computation meant you could not parallelize along the time axis: token `t+1` needs the hidden state from token `t`. ... Vanishing gradients meant information 50 tokens back was already compressed through 50 non-linearities. ... Fixed-width hidden states meant the encoder squeezed the entire source sequence into a single vector before the decoder saw anything. ... The 2017 paper "Attention Is All You Need" proposed something radical: drop recurrence entirely. Let every position attend to every other position in parallel. Train in one big matrix multiplication instead of 1,024 sequential ones.

## The Concept · 概念

![RNN 串行计算 vs Transformer 并行注意力](../assets/rnn-vs-transformer.svg)

**循环是瓶颈。** RNN 计算 `h_t = f(h_{t-1}, x_t)`，每一步依赖上一步。你没法在算出 `h_4` 之前算 `h_5`。在有 10,000+ 并行核心的现代 GPU 上，长序列会浪费掉 99% 的硅片。

**注意力是广播。** 自注意力（self-attention）对每一对 `(i, j)` 同时计算 `output_i = sum_j(a_ij * v_j)`。整个 N×N 注意力矩阵在一次批量矩阵乘（batched matmul）里填满。没有哪一步依赖另一步。GPU 爱死了。

**加速比不是一个常数。** 它是 `O(N)` 串行深度与 `O(1)` 串行深度之间的差。实践中，在 N=512 的同等硬件上，transformer 每个 epoch 训练快 5–10 倍，而且差距随序列长度继续拉大，直到你撞上注意力 `O(N²)` 的内存墙（Flash Attention 后来修掉了它——见第 12 课）。

**transformer 付出的代价。** 注意力内存按 `O(N²)` 增长。2K 上下文，没问题。128K 上下文，你需要滑动窗口、RoPE 外推、Flash Attention 分块，或者线性注意力变体。循环在时间和内存上都是 `O(N)`；transformer 用内存换时间，再用并行性把时间赢回来。

**归纳偏置（inductive bias）的转移。** RNN 假设局部性和就近性。transformer 什么都不假设——每一对位置都是注意力的候选。这就是为什么 transformer 需要更多数据才能训练好，但一旦有了数据就能扩展得更远。Chinchilla（2022）把它形式化了：只要 token 足够多，同参数量的 transformer 总能赢过 RNN。

```figure
rnn-vs-parallel
```

> **Recurrence as a bottleneck.** An RNN computes `h_t = f(h_{t-1}, x_t)`. Each step depends on the previous. ... **Attention as a broadcast.** Self-attention computes `output_i = sum_j(a_ij * v_j)` for every pair `(i, j)` simultaneously. The whole N×N attention matrix fills in one batched matmul. No step depends on another. ... **The speedup is not a constant.** It is the difference between `O(N)` serial depth and `O(1)` serial depth. ... **What transformers cost.** Attention memory scales as `O(N²)`. ... **The inductive bias shift.** RNNs assume locality and recency. Transformers assume nothing — every pair is a candidate for attention.

## Build It · 动手造

这里没有神经网络——我们在数值上模拟核心瓶颈，让你在笔记本上亲手感受到差距。

> No neural network here — we simulate the core bottleneck numerically so you feel the gap on your laptop.

### Step 1: measure serial depth · 测量串行深度

见 `code/main.py`。我们写两个函数：一个把序列编码成一串加法（串行，像 RNN）；一个把它编码成并行归约（广播，像注意力）。同样的数学，不同的依赖图。

```python
def rnn_style(xs):
    h = 0.0
    for x in xs:
        h = 0.9 * h + x   # can't parallelize: h depends on previous h
    return h

def attention_style(xs):
    return sum(xs) / len(xs)  # every x is independent
```

我们在最长 100,000 个元素的序列上给两者计时。RNN 版本是 O(N) 的单条 CPU 流水线。即使在纯 Python 里，注意力式归约也在长度 ≥ 1,000 时胜出，因为 Python 的 `sum()` 由 C 实现，逐步迭代不带解释器开销。

> See `code/main.py`. We build two functions. One encodes a sequence as a chain of additions (serial, like an RNN). One encodes it as a parallel reduction (broadcast, like attention). Same math, different dependency graph.
> We time both on sequences up to 100,000 elements. The RNN version is O(N) and a single CPU pipeline. Even in pure Python, the attention-style reduction beats it at length ≥ 1,000 because Python's `sum()` is implemented in C and iterates without interpreter overhead per step.

### Step 2: count theoretical operations · 数一数理论操作数

两个算法都做 N 次加法。区别在*依赖深度（dependency depth）*：在下一个操作开始之前，必须串行完成多少个操作。RNN 深度 = N。注意力深度用树形归约是 log(N)，用并行扫描是 1。决定 GPU 时间的是深度，不是操作数。

> Both algorithms do N adds. The difference is *dependency depth*: how many operations must happen sequentially before the next can start. RNN depth = N. Attention depth = log(N) with a tree reduction, or 1 with a parallel scan. Depth, not op count, decides GPU time.

### Step 3: empirical scaling on long sequences · 长序列上的实测扩展

我们打印一张计时表，把 O(N) 的差距变成肉眼可见。在 2026 年的 Mac 笔记本上，1,000 元素以内的序列快到测不准。100,000 的序列显示出一条干净的线性扫描。把它放大到一台 16,384 token、等价于 12 层 LSTM 的 transformer，你就明白为什么 2016 年训练墙钟时间是个拦路虎。

> We print a timing table that makes the O(N) gap visible. On a 2026 Mac laptop, sequences under 1,000 elements are too fast to measure. Sequences of 100,000 show a clean linear scan. Scale that to a 16,384-token transformer with a 12-layer LSTM equivalent and you see why training wall-clock was a blocker in 2016.

## Use It · 实战用法

2026 年还在什么情况下选 RNN：

| 情形 | 选择 |
|------|------|
| 流式推理，一次一个 token，内存恒定 | RNN 或状态空间模型（Mamba、RWKV） |
| 超长序列（>100 万 token），注意力内存爆炸 | 线性注意力、Mamba 2、Hyena |
| 没有 matmul 加速器的边缘设备 | 深度可分离 RNN 在 FLOPs/瓦特上仍然赢 |
| 其他一切（训练、批量推理、上下文 128K 以内） | Transformer |

像 Mamba 这样的状态空间模型（state-space model，SSM）本质上是带结构化参数化的 RNN，两头的好处都占了：`O(N)` 的扫描内存，靠选择性扫描（selective scan）实现并行训练。它们能找回 transformer 九成的质量，长上下文扩展性还更好。2026 年大多数前沿实验室训练的是 SSM+transformer 混合模型（例如 Jamba、Samba）——循环没有死，它成了一个组件。

> When to still pick an RNN in 2026:
> State-space models (SSMs) like Mamba are essentially RNNs with structured parameterization that gives them the best of both: `O(N)` scan memory, parallel training via selective scan. They recover 90% of transformer quality with better long-context scaling. In 2026 most frontier labs train hybrid SSM+transformer models (e.g. Jamba, Samba) — recurrence is not dead, it is a component.

## Ship It · 交付

见 `outputs/skill-architecture-picker.md`。这个技能在给定长度、吞吐量、训练预算约束下，为新的序列问题挑选架构。对超过 10 亿 token 的训练任务，它必须始终拒绝推荐纯 RNN，除非同时说明代价。

> See `outputs/skill-architecture-picker.md`. The skill picks an architecture for a new sequence problem given length, throughput, and training-budget constraints. It should always refuse to recommend a pure RNN for training runs above 1B tokens without stating the trade-off.

## Exercises · 练习

1. **简单。** 把 `code/main.py` 里的 `rnn_style` 拿来，把标量隐藏状态换成长度 64 的隐藏状态向量。重新计时。串行开销随隐藏状态维度增长了多少？
2. **中等。** 用纯 Python 实现并行前缀和（Hillis-Steele scan）。验证它在长度 1024 上与串行扫描给出相同的数值输出。数一数深度。
3. **困难。** 把注意力式归约移植到 GPU 上的 PyTorch。把序列长度从 64 扫到 65,536，给两者计时。画出曲线并解释其形状。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 它实际是什么意思 |
|------|-----------------|-----------------------|
| 循环（Recurrence） | 「RNN 是串行的」 | 第 `t` 步依赖第 `t-1` 步的计算，迫使执行沿时间轴串行。 |
| 串行深度（Serial depth） | 「计算图有多深」 | 相互依赖的操作构成的最长链；即使在无限硬件上也限制墙钟时间。 |
| 注意力（Attention） | 「让 token 互相看」 | 加权和 `sum_j a_ij v_j`，其中 `a_ij` 来自位置 i 和 j 之间的相似度分数。 |
| 上下文窗口（Context window） | 「模型能看多少」 | 注意力层可接受的输入位置数；二次方内存成本就按它增长。 |
| 归纳偏置（Inductive bias） | 「架构里焊死的假设」 | 关于数据长什么样的先验；CNN 假设平移不变，RNN 假设就近性。 |
| 状态空间模型（State-space model） | 「背后有代数的 RNN」 | 用结构化状态空间矩阵参数化、从而可并行训练的循环。 |
| 二次方瓶颈（Quadratic bottleneck） | 「上下文为什么这么贵」 | 注意力内存随序列长度为 `O(N²)`；Flash Attention 藏掉的是常数，不是这个标度。 |

## Further Reading · 延伸阅读

- [Vaswani et al. (2017). Attention Is All You Need](https://arxiv.org/abs/1706.03762) —— 在主流 NLP 里终结循环的那篇论文。
- [Bahdanau, Cho, Bengio (2014). Neural MT by Jointly Learning to Align and Translate](https://arxiv.org/abs/1409.0473) —— 注意力的诞生地，当时还挂在 RNN 上。
- [Hochreiter, Schmidhuber (1997). Long Short-Term Memory](https://www.bioinf.jku.at/publications/older/2604.pdf) —— LSTM 原始论文，存档备查。
- [Gu, Dao (2023). Mamba: Linear-Time Sequence Modeling with Selective State Spaces](https://arxiv.org/abs/2312.00752) —— 对 transformer 的现代循环式回答。
