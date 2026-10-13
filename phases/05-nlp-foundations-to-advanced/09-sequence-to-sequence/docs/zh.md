# Sequence-to-Sequence Models · 序列到序列模型（Seq2Seq）

> Two RNNs pretending to be a translator. The bottleneck they hit is the reason attention exists.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 08 (CNNs + RNNs for Text), Phase 3 · 11 (PyTorch Intro)
**Time:** ~75 minutes

## The Problem · 问题在哪

分类把一个变长序列映射成单个标签。翻译把一个变长序列映射成另一个变长序列。输入和输出活在不同的词表里，可能是不同的语言，而且完全不保证长度对齐。

seq2seq 架构（Sutskever, Vinyals, Le, 2014）用一个刻意简单的配方解决了这个问题。两个 RNN。一个读源句子，产出一个固定尺寸的上下文向量（context vector）。另一个读这个向量，逐 token 生成目标句子。就是你第 08 课写过的同一套代码，换个方式粘起来。

这东西值得学有两个原因。第一，上下文向量瓶颈是 NLP 里教学价值最高的失败案例，attention 和 Transformer 的全部长处都是由它引发的。第二，那套训练配方（teacher forcing、计划采样 scheduled sampling、推理时的束搜索 beam search）至今适用于包括 LLM 在内的每一个现代生成系统。

> Classification maps a variable-length sequence to a single label. Translation maps a variable-length sequence to another variable-length sequence. The input and output live in different vocabularies, possibly different languages, with no guarantee of length parity.
> The seq2seq architecture (Sutskever, Vinyals, Le, 2014) cracked this with a deliberately simple recipe. Two RNNs. One reads the source sentence and produces a fixed-size context vector. The other reads that vector and generates the target sentence token by token.
> First, the context-vector bottleneck is the most pedagogically useful failure in NLP. It motivates everything attention and transformers are good at. Second, the training recipe (teacher forcing, scheduled sampling, beam search at inference) still applies to every modern generation system including LLMs.

## The Concept · 概念

**编码器（Encoder）。** 一个读源句子的 RNN。它的最终隐状态就是**上下文向量（context vector）**——整个输入的固定尺寸摘要。理想情况下，丢掉的只有源句子本身。

**解码器（Decoder）。** 另一个 RNN，从上下文向量初始化。每一步它拿上一个生成的 token 作输入，产出一个目标词表上的分布。采样或取 argmax 选出下一个 token，再喂回去，直到产生 `<EOS>` 或达到最大长度。

**训练：** 解码器每一步都算交叉熵损失，对整个序列求和。标准的贯穿两个网络的时间反向传播（backprop through time）。

**Teacher forcing（教师强制）。** 训练时，解码器在步 `t` 的输入是位置 `t-1` 的*真实* token，而不是解码器自己上一步的预测。这能稳定训练；没有它，早期的错误会级联放大，模型什么都学不会。推理时你只能用模型自己的预测，所以训练/推理之间始终存在分布鸿沟。这个鸿沟叫**曝光偏差（exposure bias）**。

**瓶颈。** 编码器学到的关于源句子的一切，都必须塞进那一个上下文向量。长句子丢细节。生僻词被糊掉。语序重排（chat noir vs. black cat）只能靠死记，不能靠计算。

Attention（第 10 课）的修法是让解码器看*每一个*编码器隐状态，而不只是最后一个。这就是全部卖点。

```figure
lstm-gates
```

> **Encoder.** An RNN that reads the source sentence. Its final hidden state is the **context vector** — a fixed-size summary of the entire input.
> **Decoder.** Another RNN initialized from the context vector. At each step it takes the previously generated token as input and produces a distribution over the target vocabulary. Sample or argmax to pick the next token. Feed it back in. Repeat until an `<EOS>` token is produced or max length is hit.
> **Teacher forcing.** During training, the decoder's input at step `t` is the *ground-truth* token at position `t-1`, not the decoder's own previous prediction. ... That gap is called **exposure bias**.
> **The bottleneck.** Everything the encoder learned about the source must be squeezed into that one context vector. Long sentences lose detail. Rare words get blurred.
> Attention (lesson 10) fixes this by letting the decoder look at *every* encoder hidden state, not just the last one. That is the whole pitch.

## Build It · 动手造

### Step 1: an encoder · 编码器

```python
import torch
import torch.nn as nn


class Encoder(nn.Module):
    def __init__(self, src_vocab_size, embed_dim, hidden_dim):
        super().__init__()
        self.embed = nn.Embedding(src_vocab_size, embed_dim, padding_idx=0)
        self.gru = nn.GRU(embed_dim, hidden_dim, batch_first=True)

    def forward(self, src):
        e = self.embed(src)
        outputs, hidden = self.gru(e)
        return outputs, hidden
```

`outputs` 的形状是 `[batch, seq_len, hidden_dim]`——每个输入位置一个隐状态。`hidden` 的形状是 `[1, batch, hidden_dim]`——最后一步。第 08 课说「对 outputs 做池化来做分类」；这里我们把最后一个隐状态留作上下文向量，忽略每一步的输出。

> `outputs` has shape `[batch, seq_len, hidden_dim]` — one hidden state per input position. `hidden` has shape `[1, batch, hidden_dim]` — the final step. Lesson 08 said "pool over outputs for classification." Here we keep the last hidden state as the context vector, and ignore the per-step outputs.

### Step 2: a decoder · 解码器

```python
class Decoder(nn.Module):
    def __init__(self, tgt_vocab_size, embed_dim, hidden_dim):
        super().__init__()
        self.embed = nn.Embedding(tgt_vocab_size, embed_dim, padding_idx=0)
        self.gru = nn.GRU(embed_dim, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim, tgt_vocab_size)

    def forward(self, token, hidden):
        e = self.embed(token)
        out, hidden = self.gru(e, hidden)
        logits = self.fc(out)
        return logits, hidden
```

解码器一次只被调用一步。输入：一批单个 token 和当前隐状态。输出：下一个 token 的词表 logits 和更新后的隐状态。

> Decoder is called one step at a time. Input: a batch of single tokens and the current hidden state. Output: vocabulary logits for the next token and the updated hidden state.

### Step 3: training loop with teacher forcing · 带 teacher forcing 的训练循环

```python
def train_batch(encoder, decoder, src, tgt, bos_id, optimizer, teacher_forcing_ratio=0.9):
    optimizer.zero_grad()
    _, hidden = encoder(src)
    batch_size, tgt_len = tgt.shape
    input_token = torch.full((batch_size, 1), bos_id, dtype=torch.long)
    loss = 0.0
    loss_fn = nn.CrossEntropyLoss(ignore_index=0)

    for t in range(tgt_len):
        logits, hidden = decoder(input_token, hidden)
        step_loss = loss_fn(logits.squeeze(1), tgt[:, t])
        loss += step_loss
        use_teacher = torch.rand(1).item() < teacher_forcing_ratio
        if use_teacher:
            input_token = tgt[:, t].unsqueeze(1)
        else:
            input_token = logits.argmax(dim=-1)

    loss.backward()
    optimizer.step()
    return loss.item() / tgt_len
```

两个值得叫出名字的旋钮。`ignore_index=0` 让填充（padding）token 不计入损失。`teacher_forcing_ratio` 是每一步用真实 token（而非模型预测）的概率。从 1.0（完全 teacher forcing）开始，训练过程中退火到约 0.5，以缩小曝光偏差的鸿沟。

> Two knobs worth naming. `ignore_index=0` skips loss on padding tokens. `teacher_forcing_ratio` is the probability of using the true token vs. the model's prediction at each step. Start at 1.0 (full teacher forcing) and anneal down to ~0.5 over training to close the exposure-bias gap.

### Step 4: inference loop (greedy) · 推理循环（贪心）

```python
@torch.no_grad()
def greedy_decode(encoder, decoder, src, bos_id, eos_id, max_len=50):
    _, hidden = encoder(src)
    batch_size = src.shape[0]
    input_token = torch.full((batch_size, 1), bos_id, dtype=torch.long)
    output_ids = []
    for _ in range(max_len):
        logits, hidden = decoder(input_token, hidden)
        next_token = logits.argmax(dim=-1)
        output_ids.append(next_token)
        input_token = next_token
        if (next_token == eos_id).all():
            break
    return torch.cat(output_ids, dim=1)
```

贪心解码每一步都选概率最高的 token。它可能跑偏：一旦确定了一个 token，就再也不能反悔。**束搜索（beam search）** 同时保住 top-`k` 条部分序列，最后挑得分最高的完整序列。束宽 3-5 是标准配置。

> Greedy decoding picks the highest-probability token at every step. It can wander off: once you commit to a token, you cannot unsay it. **Beam search** keeps the top-`k` partial sequences alive and picks the highest-scoring complete one at the end. Beam width 3-5 is standard.

### Step 5: the bottleneck, demonstrated · 瓶颈现场演示

在一个玩具复制任务上训练模型：源 `[a, b, c, d, e]`，目标 `[a, b, c, d, e]`。加大序列长度，观察准确率。

```
seq_len=5   copy accuracy: 98%
seq_len=10  copy accuracy: 91%
seq_len=20  copy accuracy: 62%
seq_len=40  copy accuracy: 23%
```

单个 GRU 隐状态无法无损记住 40 个 token 的输入。信息在编码器的每一步都在场，但解码器只看得到最后一个状态。Attention 直接修的就是这个。

> Train the model on a toy copy task: source `[a, b, c, d, e]`, target `[a, b, c, d, e]`. Increase sequence length. Observe accuracy.
> A single GRU hidden state cannot losslessly memorize a 40-token input. The information is there at every encoder step, but the decoder only sees the last state. Attention fixes this directly.

## Use It · 实战用法

PyTorch 自带 `nn.Transformer` 和基于 `nn.LSTM` 的 seq2seq 模板。Hugging Face 的 `transformers` 库提供在数十亿 token 上训练好的完整编码器-解码器模型（BART、T5、mBART、NLLB）。

```python
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

tok = AutoTokenizer.from_pretrained("facebook/bart-base")
model = AutoModelForSeq2SeqLM.from_pretrained("facebook/bart-base")

src = tok("Translate this to French: Hello, how are you?", return_tensors="pt")
out = model.generate(**src, max_new_tokens=50, num_beams=4)
print(tok.decode(out[0], skip_special_tokens=True))
```

现代编码器-解码器把 RNN 换成了 Transformer。高层形状（编码器、解码器、逐 token 生成）和 2014 年的 seq2seq 论文一模一样，只是每个模块内部的机制不同。

> PyTorch has `nn.Transformer` and `nn.LSTM`-based seq2seq templates. Hugging Face's `transformers` library ships full encoder-decoder models (BART, T5, mBART, NLLB) trained on billions of tokens.
> Modern encoder-decoders dropped RNNs for transformers. The high-level shape (encoder, decoder, generate-token-by-token) is identical to the 2014 seq2seq paper. The mechanism inside each block is different.

### When to still reach for RNN-based seq2seq · 什么时候还该用 RNN 版 seq2seq

对新项目来说，几乎从不。具体例外：

- 流式翻译：一次消费一个 token 的输入，内存有上界。
- 端侧文本生成：Transformer 的内存成本不可接受。
- 教学。理解编码器-解码器瓶颈是理解 Transformer 为什么获胜的最快路径。

> Almost never, for new projects. Specific exceptions:
> Streaming translation where you consume input one token at a time with bounded memory.
> On-device text generation where transformer memory cost is prohibitive.
> Pedagogy. Understanding the encoder-decoder bottleneck is the fastest path to understanding why transformers won.

### Exposure bias and its mitigations · 曝光偏差及其缓解

- **计划采样（scheduled sampling）。** 训练中逐步降低 teacher forcing 比例，让模型学会从自己的错误中恢复。
- **最小风险训练（minimum risk training）。** 直接在句子级 BLEU 分数上训练，而不是 token 级交叉熵。更贴近你真正想要的东西。
- **强化学习微调。** 用某个指标奖励序列生成器。现代 LLM 的 RLHF 就在用。

这三招对基于 Transformer 的生成依然全部适用。

> **Scheduled sampling.** Anneal teacher forcing ratio during training so the model learns to recover from its own mistakes.
> **Minimum risk training.** Train on sentence-level BLEU score instead of token-level cross-entropy. Closer to what you actually want.
> **Reinforcement learning fine-tuning.** Reward the sequence generator with a metric. Used in modern LLM RLHF.
> All three still apply to transformer-based generation.

## Ship It · 交付

保存为 `outputs/prompt-seq2seq-design.md`：

```markdown
---
name: seq2seq-design
description: Design a sequence-to-sequence pipeline for a given task.
phase: 5
lesson: 09
---

Given a task (translation, summarization, paraphrase, question rewrite), output:

1. Architecture. Pretrained transformer encoder-decoder (BART, T5, mBART, NLLB) is the default. RNN-based seq2seq only for specific constraints.
2. Starting checkpoint. Name it (`facebook/bart-base`, `google/flan-t5-base`, `facebook/nllb-200-distilled-600M`). Match the checkpoint to task and language coverage.
3. Decoding strategy. Greedy for deterministic output, beam search (width 4-5) for quality, sampling with temperature for diversity. One sentence justification.
4. One failure mode to verify before shipping. Exposure bias manifests as generation drift on longer outputs; sample 20 outputs at the 90th-percentile length and eyeball.

Refuse to recommend training a seq2seq from scratch for under a million parallel examples. Flag any pipeline that uses greedy decoding for user-facing content as fragile (greedy repeats and loops).
```

> Save as `outputs/prompt-seq2seq-design.md`.

## Exercises · 练习

1. **简单。** 实现玩具复制任务。在目标等于源句子的输入-输出对上训练一个 GRU seq2seq。测长度 5、10、20 的准确率。亲手复现那个瓶颈。
2. **中等。** 给解码加上束宽为 3 的束搜索。在一个小的平行语料上测 BLEU，与贪心比较。记录束搜索在哪里赢（通常是最后几个 token）、在哪里毫无差别。
3. **困难。** 在一个 1 万对的释义（paraphrase）数据集上微调 `facebook/bart-base`。在留出输入上比较微调模型和基础模型的束宽 4 输出。报告 BLEU，并挑 10 个定性例子。

> **Easy.** Implement the toy copy task. Train a GRU seq2seq on input-output pairs where the target equals the source. Measure accuracy at lengths 5, 10, 20. Reproduce the bottleneck.
> **Medium.** Add beam search decoding with beam width 3. Measure BLEU on a small parallel corpus against greedy. Document where beam search wins (usually last tokens) and where it makes no difference.
> **Hard.** Fine-tune `facebook/bart-base` on a 10k-pair paraphrase dataset. Compare the fine-tuned model's beam-4 output to the base model's on held-out inputs. Report BLEU and pick 10 qualitative examples.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Encoder | 输入 RNN | 读源句子。产出每步隐状态和一个最终上下文向量。 |
| Decoder | 输出 RNN | 从上下文向量初始化。一次生成一个目标 token。 |
| Context vector | 那份摘要 | 编码器最终隐状态。固定尺寸。就是 attention 解决的那个瓶颈。 |
| Teacher forcing | 用真实 token | 训练时喂真实的上一个 token。稳定学习。 |
| Exposure bias | 训练/测试鸿沟 | 模型一直喂真实 token，从没练过从自己的错误里恢复。 |
| Beam search | 更好的解码 | 每步保住 top-k 条部分序列，而不是贪心一步到位。 |

## Further Reading · 延伸阅读

- [Sutskever, Vinyals, Le (2014). Sequence to Sequence Learning with Neural Networks](https://arxiv.org/abs/1409.3215) —— seq2seq 原始论文。四页。
- [Cho et al. (2014). Learning Phrase Representations using RNN Encoder-Decoder for Statistical Machine Translation](https://arxiv.org/abs/1406.1078) —— 提出 GRU 和编码器-解码器框架的论文。
- [Bahdanau, Cho, Bengio (2014). Neural Machine Translation by Jointly Learning to Align and Translate](https://arxiv.org/abs/1409.0473) —— attention 论文。上完本课立刻读。
- [PyTorch NLP from Scratch tutorial](https://pytorch.org/tutorials/intermediate/seq2seq_translation_tutorial.html) —— 可以亲手跑的 seq2seq + attention 代码。
