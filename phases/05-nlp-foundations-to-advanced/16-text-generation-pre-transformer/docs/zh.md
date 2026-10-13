# Text Generation Before Transformers — N-gram Language Models · Transformer 之前的文本生成 —— N-gram 语言模型

> 如果一个词让模型「惊讶」，说明这个模型不好。困惑度（perplexity）把「惊讶」变成一个数字，平滑（smoothing）让概率保持有限。
>
> If a word is surprising, the model is bad. Perplexity makes surprise a number. Smoothing keeps it finite.

**类型:** Build（构建）
**语言:** Python
**前置课程:** Phase 5 · 01（文本处理）、Phase 2 · 14（朴素贝叶斯）
**时间:** ~45 分钟

## The Problem · 问题

在 transformer、RNN、词向量（word embedding）出现之前，语言模型预测下一个词的方式是「数数」：统计它跟在前面 `n-1` 个词后面的次数。数出 "the cat" → "sat" 47 次、"the cat" → "jumped" 12 次、"the cat" → "refrigerator" 0 次，再归一化得到概率分布。

这就是 n-gram 语言模型。从 1980 到 2015 年，每一个语音识别器、每一个拼写检查器、每一个基于短语的机器翻译系统跑的都是它。直到今天，当你需要廉价的端侧（on-device）语言建模时，跑的仍然是它。

真正有意思的问题是怎么处理没见过的 n-gram。纯计数模型给它没见过的任何 n-gram 分配零概率，而这是灾难性的：句子很长，几乎每个长句子里都至少包含一段没见过的序列。五十年的平滑研究解决了这个问题，其结晶就是 Kneser-Ney 平滑；现代深度学习继承了它那套经验主义传统。

> Before transformers, before RNNs, before word embeddings, a language model predicted the next word by counting how often it followed the previous `n-1` words. ... That is an n-gram language model. It ran every speech recognizer, every spell checker, and every phrase-based machine translation system from 1980 through 2015. ... The interesting problem is what to do about unseen n-grams. ... Fifty years of smoothing research fixed that. Kneser-Ney smoothing is the result, and modern deep learning inherited its empirical tradition.

## The Concept · 概念

![N-gram 模型：计数、平滑、生成](../assets/ngram.svg)

### The prediction game · 预测游戏

在这些机器出现之前，一个实验定义了「语言模型是什么」。盖住英文句子的下一个字母，让一个人去猜，一次猜一个，直到猜对为止，记下猜测次数。对几百个字母重复这个实验。

猜测次数不是冷知识。它是对文本的一次无损重编码（lossless re-encoding）：把猜测次数序列交给第二个同样的猜字母者，他能重建每一个字母，因为在每个位置上他都确切知道哪些猜测排在前面。一条能用更少符号重新编码的消息，每个符号携带的信息就更少，所以猜次数统计给英文的熵（entropy）划了一条上界。

Shannon 在 1951 年跑了这个实验，得到一个至今仍支配着这个领域的数字。一个 27 符号的字母表（26 个字母加空格）每个字母最多可携带 `log2(27) ≈ 4.75` bit。拥有 100 个字母上下文的人类猜字母者落在每字母 0.6 到 1.3 bit 之间。英文大约四分之三是「被迫的走法」。模型必须学习的结构，早在任何模型能学习它之前就被测量好了。

此后的每一个语言模型都是这个游戏的机械玩家，本课里的每个评估数字都是这个游戏的得分：

- **交叉熵损失（cross-entropy loss）** 是模型每个符号平均需要的 bit 数。训练语言模型，字面上就是在最小化它在这个猜字母游戏里的得分。
- **困惑度（perplexity）** 是 `2^bits`（或 `e^nats`）：玩家猜完之后仍面对的分支因子（branching factor）。在 27 个符号上均匀瞎猜的困惑度是 27；每字母 1 bit 的玩家困惑度是 2。
- **上下文长度就是玩家的记忆。** 三元组（trigram）模型带着两个 token 的记忆上场。transformer 玩的是同一个游戏，带着 10 万 token 的记忆。规则从没变过；玩家变强了。

还要记住一个单位换算：这个游戏按字母、以 bit（`log2`）计分，而下面的 n-gram 公式按词 token、以 nat（自然对数）计分——由于 nat 单位下的困惑度 `e^H` 等于 bit 单位下的 `2^H`，两种视角是同一测量在不同单位下的表达。

```figure
prediction-game
```

**N-gram 概率：** `P(w_i | w_{i-n+1}, ..., w_{i-1})`。固定 `n`（trigram 通常取 3，4-gram 取 4），从计数算出：

```text
P(w | context) = count(context, w) / count(context)
```

**零计数问题。** 任何训练中没见过的 n-gram 概率为零。2007 年一项针对 Brown 语料库的研究发现，即使是 4-gram 模型，也有 30% 的留出集（held-out）4-gram 在训练中从未出现过。不做平滑，你没法在任何真实文本上做评估。

**平滑方法，按精致程度排序：**

1. **Laplace（加一法）。** 每个计数加 1。简单，但对稀有事件很糟糕。
2. **Good-Turing。** 依据「频率的频率」，把概率质量从高频事件重新分配给未见事件。
3. **插值（Interpolation）。** 用可调权重组合 n-gram、(n-1)-gram 等多阶估计。
4. **回退（Backoff）。** n-gram 计数为零就退回 (n-1)-gram。Katz backoff 把它规范化了。
5. **绝对减值（Absolute discounting）。** 从所有计数里减去固定折扣 `D`，把扣下的质量重新分配给未见事件。
6. **Kneser-Ney。** 绝对减值，再给低阶模型一个聪明的选择：用*延续概率*（continuation probability，一个词出现在多少个上下文里）代替原始频率。

Kneser-Ney 的洞见很深。"San Francisco" 是常见 bigram。单独看 "Francisco" 几乎总跟在 "San" 后面。朴素的绝对减值会给 "Francisco" 很高的一元概率（因为计数很高）。Kneser-Ney 注意到 "Francisco" 只出现在一个上下文里，于是相应调低它的延续概率。结果：一个以 "Francisco" 结尾的新 bigram 会得到恰当的低概率。

**评估：困惑度。** 它是留出测试集上每词平均负对数似然的指数。越低越好。困惑度 100 意味着模型的状态相当于在 100 个词里均匀瞎选。

```text
perplexity = exp(- (1/N) * Σ log P(w_i | context_i))
```

```figure
ngram-backoff
```

> Cover the next letter of an English sentence. Ask someone to guess it, one guess at a time, until they get it right. Write down the guess count. ... The guess counts are not trivia. They are a lossless re-encoding of the text ... so the guess-count statistics put a ceiling on the entropy of English.
> Shannon ran this in 1951 and got a number that still governs the field. ... Every language model since is a mechanical player of this game, and every evaluation number in this lesson is the game scored.
> **Perplexity** is `2^bits` (or `e^nats`): the branching factor still facing the model after its guesswork. ... **Context length is the player's memory.** ... The rules never changed; the player got better.
> **The zero-count problem.** Any n-gram not seen in training gets probability zero. ... You cannot evaluate on any real text without smoothing.
> The Kneser-Ney insight is deep. ... Kneser-Ney notices that "Francisco" appears in only one context and lowers its continuation probability accordingly.
> **Evaluation: perplexity.** The exponent of the average negative log-likelihood per word on a held-out test set. Lower is better.

## Build It · 动手造

### Step 1: trigram counts · 第 1 步：trigram 计数

```python
from collections import Counter, defaultdict


def train_ngram(corpus_tokens, n=3):
    ngrams = Counter()
    contexts = Counter()
    for sentence in corpus_tokens:
        padded = ["<s>"] * (n - 1) + sentence + ["</s>"]
        for i in range(len(padded) - n + 1):
            ctx = tuple(padded[i:i + n - 1])
            word = padded[i + n - 1]
            ngrams[ctx + (word,)] += 1
            contexts[ctx] += 1
    return ngrams, contexts


def raw_probability(ngrams, contexts, context, word):
    ctx = tuple(context)
    if contexts.get(ctx, 0) == 0:
        return 0.0
    return ngrams.get(ctx + (word,), 0) / contexts[ctx]
```

输入是分好词的句子列表，输出是 n-gram 计数和上下文计数。`<s>` 和 `</s>` 是句子边界。

> Input is a list of tokenized sentences. Output is n-gram counts and context counts. `<s>` and `</s>` are sentence boundaries.

### Step 2: Laplace smoothing · 第 2 步：Laplace 平滑

```python
def laplace_probability(ngrams, contexts, vocab_size, context, word):
    ctx = tuple(context)
    numerator = ngrams.get(ctx + (word,), 0) + 1
    denominator = contexts.get(ctx, 0) + vocab_size
    return numerator / denominator
```

每个计数加 1。能平滑，但把太多质量分给未见事件，同时也伤害了那些稀有的已知事件。

> Add 1 to every count. Smooths but over-allocates mass to unseen events, hurting rare-known events too.

### Step 3: Kneser-Ney (bigram, interpolated) · 第 3 步：Kneser-Ney（bigram、插值版）

```python
def kneser_ney_bigram_model(corpus_tokens, discount=0.75):
    unigrams = Counter()
    bigrams = Counter()
    unigram_contexts = defaultdict(set)

    for sentence in corpus_tokens:
        padded = ["<s>"] + sentence + ["</s>"]
        for i, w in enumerate(padded):
            unigrams[w] += 1
            if i > 0:
                prev = padded[i - 1]
                bigrams[(prev, w)] += 1
                unigram_contexts[w].add(prev)

    total_unique_bigrams = sum(len(ctx_set) for ctx_set in unigram_contexts.values())
    continuation_prob = {
        w: len(ctx_set) / total_unique_bigrams for w, ctx_set in unigram_contexts.items()
    }

    context_totals = Counter()
    for (prev, w), count in bigrams.items():
        context_totals[prev] += count

    unique_follow = defaultdict(set)
    for (prev, w) in bigrams:
        unique_follow[prev].add(w)

    def prob(prev, w):
        count = bigrams.get((prev, w), 0)
        denom = context_totals.get(prev, 0)
        if denom == 0:
            return continuation_prob.get(w, 1e-9)
        first_term = max(count - discount, 0) / denom
        lambda_prev = discount * len(unique_follow[prev]) / denom
        return first_term + lambda_prev * continuation_prob.get(w, 1e-9)

    return prob
```

三个活动部件。`continuation_prob` 刻画「这个词出现在多少个不同上下文里？」（这就是 Kneser-Ney 的创新点）。`lambda_prev` 是折扣释放出来的概率质量，用来给回退项加权。最终概率是打折后的主项加上加权的延续项。

> Three moving parts. `continuation_prob` captures "how many different contexts does this word appear in?" (the Kneser-Ney innovation). `lambda_prev` is the mass freed by the discount, used to weight the backoff. The final probability is the discounted main term plus the weighted continuation term.

### Step 4: generating text with sampling · 第 4 步：按采样生成文本

```python
import random


def generate(prob_fn, vocab, prefix, max_len=30, seed=0):
    rng = random.Random(seed)
    tokens = list(prefix)
    for _ in range(max_len):
        candidates = [(w, prob_fn(tokens[-1], w)) for w in vocab]
        total = sum(p for _, p in candidates)
        r = rng.random() * total
        acc = 0.0
        for w, p in candidates:
            acc += p
            if r <= acc:
                tokens.append(w)
                break
        if tokens[-1] == "</s>":
            break
    return tokens
```

按概率成比例采样。同一个 seed 每次都会给出不同的输出。想要类似 beam search 的输出，就在每一步取 argmax（贪心），再加一个小小的随机旋钮（温度 temperature）。

> Sampling proportional to probability. Always gives different output per seed. For beam-search-like output, pick the argmax at each step (greedy) and add a small randomness knob (temperature).

### Step 5: perplexity · 第 5 步：困惑度

```python
import math


def perplexity(prob_fn, sentences):
    total_log_prob = 0.0
    total_tokens = 0
    for sentence in sentences:
        padded = ["<s>"] + sentence + ["</s>"]
        for i in range(1, len(padded)):
            p = prob_fn(padded[i - 1], padded[i])
            total_log_prob += math.log(max(p, 1e-12))
            total_tokens += 1
    return math.exp(-total_log_prob / total_tokens)
```

越低越好。在 Brown 语料库上，调校好的 4-gram KN 模型困惑度约 140。transformer 语言模型在同一测试集上是 15-30。差距大约 10 倍。这个差距就是整个领域继续前进的原因。

> Lower is better. For Brown corpus, a well-tuned 4-gram KN model hits perplexity around 140. A transformer LM hits 15-30 on the same test set. The gap is about 10x. That gap is why the field moved on.

## Use It · 实战用法

- **经典 NLP 教学。** 你能找到的关于平滑、MLE 和困惑度的最清晰的学习材料。
- **KenLM。** 生产级 n-gram 库。在对延迟敏感的语音和机器翻译系统里当重打分器（rescorer）用。
- **端侧自动补全。** 输入法键盘里的 trigram 模型。至今仍是。
- **基线。** 在宣布你的神经语言模型很好之前，先算一个 n-gram 语言模型的困惑度。如果你的 transformer 没有大幅击败 KN，那一定有什么地方不对。

> **Classical NLP teaching.** The clearest exposure to smoothing, MLE, and perplexity you can get.
> **KenLM.** Production n-gram library. Used as a rescorer in speech and MT systems where low latency matters.
> **On-device autocomplete.** Trigram models in keyboards. Still.
> **Baselines.** Always compute an n-gram LM perplexity before declaring your neural LM good. If your transformer does not beat KN by a wide margin, something is wrong.

## Ship It · 交付

保存为 `outputs/prompt-lm-baseline.md`：

```markdown
---
name: lm-baseline
description: Build a reproducible n-gram language model baseline before training a neural LM.
phase: 5
lesson: 16
---

Given a corpus and target use (next-word prediction, rescoring, perplexity baseline), output:

1. N-gram order. Trigram for general English, 4-gram if corpus is large, 5-gram for speech rescoring.
2. Smoothing. Modified Kneser-Ney is the default; Laplace only for teaching.
3. Library. `kenlm` for production, `nltk.lm` for teaching, roll your own only to learn.
4. Evaluation. Held-out perplexity with consistent tokenization between train and test sets.

Refuse to report perplexity computed with different tokenization between systems being compared — perplexity numbers are comparable only under identical tokenization. Flag OOV rate in test set; KN handles OOV poorly unless you reserve a special <UNK> token during training.
```

> Save as `outputs/prompt-lm-baseline.md`.

## Exercises · 练习

1. **简单。** 在 1000 句莎士比亚语料上训练一个 trigram 语言模型，生成 20 句。它们局部看着像话，全局完全不通。这是最经典的演示。
2. **中等。** 在留出的莎士比亚划分上为你的 KN 模型实现困惑度，并与 Laplace 比较。你应该会看到 KN 把困惑度降低 30-50%。
3. **困难。** 做一个 trigram 拼写纠正器：给定一个拼错的词和它的上下文，生成纠正候选并按语言模型下的上下文概率排序。在公开的 Birkbeck 拼写语料库上评估。

## Key Terms · 关键术语

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| N-gram | 词序列 | `n` 个连续 token 组成的序列。|
| Smoothing | 避免零概率 | 重新分配概率质量，让未见事件获得非零概率。|
| Perplexity | 语言模型质量指标 | 留出数据上的 `exp(-average log-prob)`。越低越好。|
| Backoff | 回退到更短上下文 | trigram 计数为零时改用 bigram。Katz backoff 把它形式化了。|
| Kneser-Ney | n-gram 的最佳平滑 | 绝对减值 + 低阶模型采用延续概率。|
| Continuation probability | KN 特有 | `P(w)` 按 `w` 出现的上下文数量加权，而不是按原始计数。|
| Entropy of text | 每个符号的信息量 | 给定上下文时编码下一个符号所需的平均 bit 数。Shannon 1951 年对最多利用 100 个字母上下文的印刷英文给出的估计：每字母 0.6-1.3 bit，在任何模型存在之前就已测得。|

## Further Reading · 延伸阅读

- [Shannon (1951). Prediction and Entropy of Printed English](https://www.princeton.edu/~wbialek/rome/refs/shannon_51.pdf) —— 那个定义了「每个语言模型至今仍在优化的目标」的猜字母游戏实验。
- [Jurafsky and Martin — Speech and Language Processing, Chapter 3 (2026 draft)](https://web.stanford.edu/~jurafsky/slp3/3.pdf) —— n-gram 语言模型与平滑的标准教材。
- [Chen and Goodman (1998). An Empirical Study of Smoothing Techniques for Language Modeling](https://dash.harvard.edu/handle/1/25104739) —— 确立 Kneser-Ney 为最佳 n-gram 平滑器的论文。
- [Kneser and Ney (1995). Improved Backing-off for M-gram Language Modeling](https://ieeexplore.ieee.org/document/479394) —— KN 原始论文。
- [KenLM](https://kheafield.com/code/kenlm/) —— 快速的生产级 n-gram 语言模型，2026 年仍用于延迟敏感的应用。
