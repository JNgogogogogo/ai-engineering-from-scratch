# CNNs and RNNs for Text · 面向文本的 CNN 与 RNN

> Convolutions learn n-grams. Recurrences remember. Both are superseded by attention. Both still matter on constrained hardware.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 3 · 11 (PyTorch Intro), Phase 5 · 03 (Word Embeddings), Phase 4 · 02 (Convolutions from Scratch)
**Time:** ~75 minutes

## The Problem · 问题在哪

TF-IDF 和 Word2Vec 产出的是忽略词序的扁平向量。建在其上的分类器分不清 `dog bites man` 和 `man bites dog`。而词序有时恰恰携带全部信号。

在 Transformer 出现之前，有两族架构填补了这个空缺。

**文本卷积网络（TextCNN）。** 在词嵌入（embedding）序列上做 1D 卷积。宽度为 3 的滤波器是一个可学习的 trigram 检测器：它横跨三个词，输出一个分数。叠放不同宽度（2、3、4、5）来检测多尺度模式。最大池化（max-pool）成固定尺寸的表示。扁平、可并行、快。

**循环网络（RNN、LSTM、GRU）。** 一次处理一个 token，维护一个把信息向前传递的隐状态（hidden state）。串行、带记忆、输入长度灵活。从 2014 到 2017 年统治序列建模，然后 attention 来了。

本课把两者都造出来，然后点出那个催生 attention 的失败。

> TF-IDF and Word2Vec produced flat vectors that ignored word order. A classifier built on them could not tell `dog bites man` from `man bites dog`. Word order sometimes carries the signal.
> **Convolutional nets for text (TextCNN).** Apply 1D convolutions over sequences of word embeddings. A filter of width 3 is a learnable trigram detector ... **Recurrent nets (RNN, LSTM, GRU).** Process tokens one at a time, maintaining a hidden state that carries information forward. ... Dominated sequence modeling from 2014 to 2017, then attention happened.
> This lesson builds both, then names the failure that motivated attention.

## The Concept · 概念

**TextCNN**（Kim, 2014）。token 先做嵌入。宽度为 `k` 的 1D 卷积让一个滤波器在连续的 `k`-gram 嵌入上滑动，产出一个特征图（feature map）。对特征图做全局最大池化，挑出最强的激活。把多个滤波器宽度各自的最大池化输出拼接起来，接一个分类头。

它为什么有效：一个滤波器就是一个可学习的 n-gram。最大池化对位置不变，所以 "not good" 无论出现在评论的开头还是中间，触发的都是同一个特征。三种宽度、每种 100 个滤波器，你就有 300 个学出来的 n-gram 检测器。训练是并行的，没有串行依赖。

**RNN。** 在每个时间步 `t`，隐状态 `h_t = f(W * x_t + U * h_{t-1} + b)`。`W`、`U`、`b` 在所有时间步之间共享。时间 `T` 的隐状态是整个前缀的摘要。做分类时，对 `h_1 ... h_T` 做池化（max、mean 或取最后一个）。

朴素 RNN 有梯度消失问题。**LSTM** 增加了门控（gate）来决定忘什么、存什么、输出什么，让梯度在长序列上保持稳定。**GRU** 把 LSTM 简化成两个门；参数更少，表现相当。

**双向 RNN（bidirectional RNN）** 跑一个正向 RNN 和一个反向 RNN，把隐状态拼接。每个 token 的表示都能同时看到左右上下文。对标注类任务必不可少。

```figure
rnn-unroll
```

> **TextCNN** (Kim, 2014). Tokens get embedded. A width-`k` 1D convolution slides a filter over consecutive `k`-grams of embeddings, producing a feature map. Global max-pooling over that map picks the strongest activation. ... Why it works. A filter is a learnable n-gram. Max-pooling is position-invariant ... Training is parallel; no sequential dependency.
> **RNN.** At each time step `t`, the hidden state `h_t = f(W * x_t + U * h_{t-1} + b)`. Share `W`, `U`, `b` across time. ... Plain RNNs suffer vanishing gradients. The **LSTM** adds gates that decide what to forget, what to store, and what to output, stabilizing gradients through long sequences. The **GRU** simplifies LSTM to two gates; performs similarly with fewer parameters.
> **Bidirectional RNNs** run one RNN forward and another backward, concatenating hidden states. Every token's representation sees both left and right context. Essential for tagging tasks.

## Build It · 动手造

### Step 1: TextCNN in PyTorch · 用 PyTorch 写 TextCNN

```python
import torch
import torch.nn as nn
import torch.nn.functional as F


class TextCNN(nn.Module):
    def __init__(self, vocab_size, embed_dim, n_classes, filter_widths=(2, 3, 4), n_filters=64, dropout=0.3):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.convs = nn.ModuleList([
            nn.Conv1d(embed_dim, n_filters, kernel_size=k)
            for k in filter_widths
        ])
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(n_filters * len(filter_widths), n_classes)

    def forward(self, token_ids):
        x = self.embed(token_ids).transpose(1, 2)
        pooled = []
        for conv in self.convs:
            c = F.relu(conv(x))
            p = F.max_pool1d(c, c.size(2)).squeeze(2)
            pooled.append(p)
        h = torch.cat(pooled, dim=1)
        return self.fc(self.dropout(h))
```

`transpose(1, 2)` 把 `[batch, seq_len, embed_dim]` 重排成 `[batch, embed_dim, seq_len]`，因为 `nn.Conv1d` 把中间那根轴当作通道（channels）。池化后的输出是固定尺寸的，与输入长度无关。

> The `transpose(1, 2)` reshapes `[batch, seq_len, embed_dim]` to `[batch, embed_dim, seq_len]` because `nn.Conv1d` treats the middle axis as channels. The pooled output is fixed-size regardless of input length.

### Step 2: LSTM classifier · LSTM 分类器

```python
class LSTMClassifier(nn.Module):
    def __init__(self, vocab_size, embed_dim, hidden_dim, n_classes, bidirectional=True, dropout=0.3):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm = nn.LSTM(embed_dim, hidden_dim, batch_first=True, bidirectional=bidirectional)
        factor = 2 if bidirectional else 1
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim * factor, n_classes)

    def forward(self, token_ids):
        x = self.embed(token_ids)
        out, _ = self.lstm(x)
        pooled = out.max(dim=1).values
        return self.fc(self.dropout(pooled))
```

在序列维度上做 max 池化，而不是取最后状态。做分类时，max 池化通常胜过取最后一个隐状态，因为长序列末端的信息容易垄断最后的状态。

> Max-pool over the sequence, not last-state pool. For classification, max-pooling usually beats taking the last hidden state because information at the end of a long sequence tends to dominate the last state.

### Step 3: the vanishing gradient demo (intuition) · 梯度消失演示（直觉）

不带门控的朴素 RNN 学不会长程依赖。想一个玩具任务：预测 token `A` 是否出现在序列的任何位置。如果 `A` 在位置 1，序列长 100 个 token，损失产生的梯度要一路流过 99 次循环权重的连乘。权重小于 1，梯度消失；大于 1，梯度爆炸。

```python
def vanishing_gradient_sim(seq_len, recurrent_weight=0.9):
    import math
    return math.pow(recurrent_weight, seq_len)


# At weight=0.9 over 100 steps:
#   0.9 ^ 100 ≈ 2.7e-5
# The gradient from step 100 to step 1 is effectively zero.
```

LSTM 用一条**细胞状态（cell state）**修复了这个问题：它贯穿整个网络、只经过加法交互（遗忘门会对它做乘法缩放，但梯度仍然能沿这条「高速路」流动）。GRU 用更少的参数做类似的事。两者都能在 100+ 步的序列上稳定训练。

> A plain RNN without gating cannot learn long-range dependencies. Consider a toy task: predict whether token `A` appeared anywhere in a sequence. If `A` is at position 1 and the sequence is 100 tokens long, the gradient from the loss has to flow back through 99 multiplications of the recurrent weight. If the weight is less than 1, the gradient vanishes. If more than 1, it explodes. ... LSTMs fix this with a **cell state** that runs through the network with only additive interactions ... Both give you stable training through 100+ step sequences.

### Step 4: why this still was not enough · 为什么这仍然不够

即便有了 LSTM，三个问题依然存在。

1. **串行瓶颈。** 在长度 1000 的序列上训练 RNN 需要 1000 步串行的前向/反向计算。无法沿时间并行。
2. **编码器-解码器结构里的固定尺寸上下文向量。** 解码器只看到编码器的最终隐状态——整个输入被压缩进那一个向量。长输入丢失细节。第 09 课正面处理这一点。
3. **远距离依赖的精度天花板。** LSTM 优于朴素 RNN，但跨 200+ 步传递特定信息仍然吃力。

Attention 把三个问题全解决了。Transformer 干脆扔掉了循环。第 10 课就是那个转折点。

> Three problems persisted even with LSTMs.
> **Sequential bottleneck.** Training an RNN on a sequence of length 1000 requires 1000 serial forward/backward steps. Cannot parallelize across time.
> **Fixed-size context vector in encoder-decoder setups.** The decoder sees only the final hidden state of the encoder, compressed over the entire input. Long inputs lose detail. Lesson 09 covers this directly.
> **Distant-dependency accuracy ceiling.** LSTMs outperform plain RNNs but still struggle to propagate specific information across 200+ steps.
> Attention solved all three. Transformers dropped recurrence entirely. Lesson 10 is the pivot.

## Use It · 实战用法

PyTorch 的 `nn.LSTM`、`nn.GRU` 和 `nn.Conv1d` 都是生产可用的。训练代码也是标准写法。

Hugging Face 提供预训练嵌入，可以直接插进输入层：

```python
from transformers import AutoModel

encoder = AutoModel.from_pretrained("bert-base-uncased")
for param in encoder.parameters():
    param.requires_grad = False


class BertCNN(nn.Module):
    def __init__(self, n_classes, filter_widths=(2, 3, 4), n_filters=64):
        super().__init__()
        self.encoder = encoder
        self.convs = nn.ModuleList([nn.Conv1d(768, n_filters, kernel_size=k) for k in filter_widths])
        self.fc = nn.Linear(n_filters * len(filter_widths), n_classes)

    def forward(self, input_ids, attention_mask):
        with torch.no_grad():
            out = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        x = out.transpose(1, 2)
        pooled = [F.max_pool1d(F.relu(conv(x)), kernel_size=conv(x).size(2)).squeeze(2) for conv in self.convs]
        return self.fc(torch.cat(pooled, dim=1))
```

「约束合适就用」清单：

- **边缘 / 端侧推理。** 带 GloVe 嵌入的 TextCNN 比 Transformer 小 10-100 倍。如果你的部署目标是手机，这就是那套技术栈。
- **流式 / 在线分类。** RNN 一次处理一个 token；Transformer 需要完整序列。对实时涌入的文本，LSTM 仍然占优。
- **小模型基线。** 在新任务上快速迭代。在 CPU 上 5 分钟训一个 TextCNN。
- **数据有限的序列标注。** BiLSTM-CRF（第 06 课）在只有 1k-10k 句标注数据时仍然是生产级的 NER 架构。

其余所有场景都交给 Transformer。

> PyTorch's `nn.LSTM`, `nn.GRU`, and `nn.Conv1d` are production-ready. Training code is standard. ... Hugging Face ships pretrained embeddings you plug in as the input layer.
> **Edge / on-device inference.** TextCNN with GloVe embeddings is 10-100x smaller than a transformer. If your deploy target is a phone, this is the stack.
> **Streaming / online classification.** RNN processes one token at a time; transformers need the full sequence. For real-time incoming text, LSTMs still win.
> **Sequence labeling with limited data.** BiLSTM-CRF (lesson 06) is still a production-grade NER architecture for 1k-10k labeled sentences.
> Everything else goes to a transformer.

## Ship It · 交付

保存为 `outputs/prompt-text-encoder-picker.md`：

```markdown
---
name: text-encoder-picker
description: Pick a text encoder architecture for a given constraint set.
phase: 5
lesson: 08
---

Given constraints (task, data volume, latency budget, deploy target, compute budget), output:

1. Encoder architecture: TextCNN, BiLSTM, BiLSTM-CRF, transformer fine-tune, or "use a pretrained transformer as a frozen encoder + small head".
2. Embedding input: random init, GloVe / fastText frozen, or contextualized transformer embeddings.
3. Training recipe in 5 lines: optimizer, learning rate, batch size, epochs, regularization.
4. One monitoring signal. For RNN/CNN models: attention mechanism absence means they miss long-range deps; check per-length accuracy. For transformers: fine-tuning collapse if LR too high; check train loss.

Refuse to recommend fine-tuning a transformer when data is under ~500 labeled examples without showing that a TextCNN / BiLSTM baseline has plateaued. Flag edge deployment as needing architecture-before-everything.
```

> Save as `outputs/prompt-text-encoder-picker.md`.

## Exercises · 练习

1. **简单。** 在一个 3 类玩具数据集（数据自己造）上训练 TextCNN。验证滤波器宽度 (2, 3, 4) 的平均 F1 优于单一宽度 (3)。
2. **中等。** 给 LSTM 分类器实现 max 池化、mean 池化和最后状态池化。在小数据集上比较；记录哪种池化获胜，并给出假设解释为什么。
3. **困难。** 造一个 BiLSTM-CRF NER 标注器（合并第 06 课和本课）。在 CoNLL-2003 上训练。与第 06 课的纯 CRF 基线以及 BERT 微调版比较。报告训练时间、内存和 F1。

> **Easy.** Train a TextCNN on a 3-class toy dataset (you invent the data). Verify that filter widths (2, 3, 4) outperform a single width (3) on average F1.
> **Medium.** Implement max-pool, mean-pool, and last-state pooling for the LSTM classifier. Compare on a small dataset; document which pooling wins and hypothesize why.
> **Hard.** Build a BiLSTM-CRF NER tagger (combine lesson 06 and this one). Train on CoNLL-2003. Compare to the CRF-alone baseline from lesson 06 and to a BERT fine-tune. Report training time, memory, and F1.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| TextCNN | 文本上的 CNN | 在词嵌入上叠 1D 卷积，加全局最大池化。Kim (2014)。 |
| RNN | 循环网络 | 每个时间步更新隐状态：`h_t = f(W x_t + U h_{t-1})`。 |
| LSTM | 带门的 RNN | 增加输入/遗忘/输出门 + 一条细胞状态。在长序列上训练稳定。 |
| GRU | 简化版 LSTM | 两个门代替三个。精度相当，参数更少。 |
| Bidirectional | 两个方向 | 正向 + 反向 RNN 拼接。每个 token 都能看到两侧上下文。 |
| Vanishing gradient | 训练信号消失 | 朴素 RNN 里反复乘以小于 1 的权重，让早期时间步的梯度趋近于零。 |

## Further Reading · 延伸阅读

- [Kim, Y. (2014). Convolutional Neural Networks for Sentence Classification](https://arxiv.org/abs/1408.5882) —— TextCNN 论文。八页，可读。
- [Hochreiter, S. and Schmidhuber, J. (1997). Long Short-Term Memory](https://www.bioinf.jku.at/publications/older/2604.pdf) —— LSTM 论文。出乎意料地清晰。
- [Olah, C. (2015). Understanding LSTM Networks](https://colah.github.io/posts/2015-08-Understanding-LSTMs/) —— 那组让所有人看懂 LSTM 的图。
