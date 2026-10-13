# GloVe, FastText, and Subword Embeddings · GloVe、FastText 与子词嵌入

> Word2Vec 给每个词训练一个向量；GloVe 分解共现矩阵；FastText 嵌入词的碎片；BPE 通向 transformer。
> Word2Vec trained one embedding per word. GloVe factorized the co-occurrence matrix. FastText embedded the pieces. BPE bridged to transformers.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 03 (Word2Vec from Scratch)
**Time:** ~45 minutes

## The Problem · 问题在哪

Word2Vec 留下了两个悬而未决的问题。

第一，一直存在一条平行的研究路线，直接分解共现矩阵（LSA、HAL），而不是做在线的 skip-gram 更新。Word2Vec 的迭代方法是不是本质上更好？还是说，差异只是两者处理计数方式不同带来的假象？**GloVe** 给出了答案：带着精心选择的损失做矩阵分解，能追平或打赢 Word2Vec，训练成本还更低。

第二，两种方法对从没见过的词都没有说法。`Zoomer-approved`、`dogecoin`、上周才被造出来的任何专有名词、一个罕见词根的每一个屈折形式。**FastText** 把字符 n-gram 也嵌入进来，解决了这个问题：词是其各部分之和（包括语素），于是连词表外的词也能得到一个合理的向量。

第三，transformer 到来之后，问题再次转向。词级词表大约在一百万条目就到顶了，而真实的语言比这开放得多。**字节对编码（byte-pair encoding, BPE）**及其近亲解决了这个问题：学习一个由高频子词单元构成的词表，覆盖一切。如今每个现代 LLM 用的每个现代分词器都是子词分词器。

本课把三者都走一遍，然后讲清楚什么时候该用哪个。

> Word2Vec left two open questions.
> First, there was a parallel line of research that factorized the co-occurrence matrix directly (LSA, HAL) rather than doing online skip-gram updates. ... **GloVe** answered that: matrix factorization with a thoughtfully chosen loss matches or beats Word2Vec, and costs less to train.
> Second, neither method had a story for words it had never seen. ... **FastText** fixed this by embedding character n-grams: a word is the sum of its parts, including morphemes, so even out-of-vocabulary words get a sensible vector.
> Third, once transformers arrived, the question shifted again. ... Every modern tokenizer for every modern LLM is a subword tokenizer.
> This lesson walks all three, then explains which to reach for when.

## The Concept · 概念

**GloVe（Global Vectors）。** 构建词-词共现矩阵 `X`，其中 `X[i][j]` 是词 `j` 出现在词 `i` 上下文中的次数。训练向量，使得 `v_i · v_j + b_i + b_j ≈ log(X[i][j])`。给损失加权，让高频对不至于主导一切。完成。

**FastText。** 一个词 = 它的字符 n-gram 之和，再加词本身。`where` 变成 `<wh, whe, her, ere, re>, <where>`。词向量就是这些成分向量之和。训练方式照搬 Word2Vec。好处：没见过的词（`whereupon`）可以用已知 n-gram 组合出来。

**BPE（Byte-Pair Encoding，字节对编码）。** 从单个字节（或字符）构成的词表出发。统计语料里每一对相邻项。把最高频的一对合并成新 token。重复 `k` 轮。结果：一个 `k + 256` 个 token 的词表，高频序列（`ing`、`tion`、`the`）是单个 token，稀有词被拆成眼熟的碎片。任何句子都能切出个结果来。

```figure
n5-subword-merge
```

> **GloVe (Global Vectors).** Build the word-word co-occurrence matrix `X` where `X[i][j]` is how often word `j` appears in the context of word `i`. Train vectors such that `v_i · v_j + b_i + b_j ≈ log(X[i][j])`. Weight the loss so frequent pairs do not dominate. Done.
> **FastText.** A word is the sum of its character n-grams plus the word itself. `where` becomes `<wh, whe, her, ere, re>, <where>`. The word vector is the sum of those component vectors. Train as Word2Vec. Benefit: unseen words (`whereupon`) compose from known n-grams.
> **BPE (Byte-Pair Encoding).** Start with a vocabulary of individual bytes (or characters). Count every adjacent pair in the corpus. Merge the most frequent pair into a new token. Repeat for `k` iterations. Result: a vocabulary of `k + 256` tokens where frequent sequences (`ing`, `tion`, `the`) are single tokens and rare words are broken into familiar pieces. Every sentence tokenizes into something.

## Build It · 动手造

### GloVe: factorize the co-occurrence matrix · GloVe：分解共现矩阵

```python
import numpy as np
from collections import Counter


def build_cooccurrence(docs, window=5):
    pair_counts = Counter()
    vocab = {}
    for doc in docs:
        for token in doc:
            if token not in vocab:
                vocab[token] = len(vocab)
    for doc in docs:
        indexed = [vocab[t] for t in doc]
        for i, center in enumerate(indexed):
            for j in range(max(0, i - window), min(len(indexed), i + window + 1)):
                if i != j:
                    distance = abs(i - j)
                    pair_counts[(center, indexed[j])] += 1.0 / distance
    return vocab, pair_counts


def glove_train(vocab, pair_counts, dim=16, epochs=100, lr=0.05, x_max=100, alpha=0.75, seed=0):
    n = len(vocab)
    rng = np.random.default_rng(seed)
    W = rng.normal(0, 0.1, size=(n, dim))
    W_tilde = rng.normal(0, 0.1, size=(n, dim))
    b = np.zeros(n)
    b_tilde = np.zeros(n)

    for epoch in range(epochs):
        for (i, j), x_ij in pair_counts.items():
            weight = (x_ij / x_max) ** alpha if x_ij < x_max else 1.0
            diff = W[i] @ W_tilde[j] + b[i] + b_tilde[j] - np.log(x_ij)
            coef = weight * diff

            grad_W_i = coef * W_tilde[j]
            grad_W_tilde_j = coef * W[i]
            W[i] -= lr * grad_W_i
            W_tilde[j] -= lr * grad_W_tilde_j
            b[i] -= lr * coef
            b_tilde[j] -= lr * coef

    return W + W_tilde
```

两个值得点名的运动部件。加权函数 `f(x) = (x/x_max)^alpha` 压低极高频的对（比如 `(the, and)`），不让它们主导损失。最终嵌入是 `W`（中心词）与 `W_tilde`（上下文词）两张表之和。两张表求和是一个有出处的技巧，通常比只用其中一张效果更好。

> Two moving pieces worth naming. The weighting function `f(x) = (x/x_max)^alpha` downweights very frequent pairs (like `(the, and)`) so they do not dominate the loss. The final embedding is the sum of `W` (center) and `W_tilde` (context) tables. Summing both is a published trick that tends to outperform using just one.

### FastText: subword-aware embeddings · FastText：子词感知的嵌入

```python
def char_ngrams(word, n_min=3, n_max=6):
    wrapped = f"<{word}>"
    grams = {wrapped}
    for n in range(n_min, n_max + 1):
        for i in range(len(wrapped) - n + 1):
            grams.add(wrapped[i:i + n])
    return grams
```

```python
>>> char_ngrams("where")
{'<where>', '<wh', 'whe', 'her', 'ere', 're>', '<whe', 'wher', 'here', 'ere>', '<wher', 'where', 'here>'}
```

每个词用它的一组 n-gram（通常 3 到 6 个字符）表示，词嵌入就是其 n-gram 嵌入的总和。做 skip-gram 训练时，把 Word2Vec 原来放单个向量的位置换成这套东西就行。

```python
def fasttext_vector(word, ngram_table):
    grams = char_ngrams(word)
    vecs = [ngram_table[g] for g in grams if g in ngram_table]
    if not vecs:
        return None
    return np.sum(vecs, axis=0)
```

对没见过的词，只要它的一部分 n-gram 是已知的，你照样能拿到向量。`whereupon` 与 `where` 共享 `<wh`、`her`、`ere` 和 `<where`，所以两者落得很近。

> Each word is represented by its set of n-grams (typically 3 to 6 characters). The word embedding is the sum of its n-gram embeddings. For skip-gram training, plug this in where Word2Vec used a single vector.
> For an unseen word, you still get a vector as long as some of its n-grams are known. `whereupon` shares `<wh`, `her`, `ere`, and `<where` with `where`, so the two land near each other.

### BPE: learned subword vocabulary · BPE：学出来的子词词表

```python
def learn_bpe(corpus, k_merges):
    vocab = Counter()
    for word, freq in corpus.items():
        tokens = tuple(word) + ("</w>",)
        vocab[tokens] = freq

    merges = []
    for _ in range(k_merges):
        pair_freq = Counter()
        for tokens, freq in vocab.items():
            for a, b in zip(tokens, tokens[1:]):
                pair_freq[(a, b)] += freq
        if not pair_freq:
            break
        best = pair_freq.most_common(1)[0][0]
        merges.append(best)

        new_vocab = Counter()
        for tokens, freq in vocab.items():
            new_tokens = []
            i = 0
            while i < len(tokens):
                if i + 1 < len(tokens) and (tokens[i], tokens[i + 1]) == best:
                    new_tokens.append(tokens[i] + tokens[i + 1])
                    i += 2
                else:
                    new_tokens.append(tokens[i])
                    i += 1
            new_vocab[tuple(new_tokens)] = freq
        vocab = new_vocab
    return merges


def apply_bpe(word, merges):
    tokens = list(word) + ["</w>"]
    for a, b in merges:
        new_tokens = []
        i = 0
        while i < len(tokens):
            if i + 1 < len(tokens) and tokens[i] == a and tokens[i + 1] == b:
                new_tokens.append(a + b)
                i += 2
            else:
                new_tokens.append(tokens[i])
                i += 1
        tokens = new_tokens
    return tokens
```

```python
>>> corpus = Counter({"low": 5, "lower": 2, "newest": 6, "widest": 3})
>>> merges = learn_bpe(corpus, k_merges=10)
>>> apply_bpe("lowest", merges)
['low', 'est</w>']
```

第一轮合并最高频的相邻对。跑够多轮之后，高频子串（`low`、`est`、`tion`）变成单个 token，稀有词被干净地拆开。

真正的 GPT / BERT / T5 分词器学习 3 万到 10 万次合并。结果：任何文本都能切成一串长度有界的已知 ID，永远没有 OOV。

> First iteration merges the most common adjacent pair. After enough iterations, frequent substrings (`low`, `est`, `tion`) become single tokens and rare words break cleanly.
> The real GPT / BERT / T5 tokenizers learn 30k-100k merges. Result: any text tokenizes into a bounded-length sequence of known IDs, no OOV ever.

## Use It · 实战用法

实践中你几乎从不自己训练这些东西，而是加载预训练检查点。

> In practice, you rarely train any of these yourself. You load pre-trained checkpoints.

```python
import fasttext.util
fasttext.util.download_model("en", if_exists="ignore")
ft = fasttext.load_model("cc.en.300.bin")
print(ft.get_word_vector("whereupon").shape)
print(ft.get_word_vector("zoomerapproved").shape)
```

transformer 时代的 BPE 式子词分词：

```python
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained("gpt2")
print(tok.tokenize("unbelievably tokenized"))
```

```
['un', 'bel', 'iev', 'ably', 'Ġtoken', 'ized']
```

`Ġ` 前缀标记词边界（GPT-2 的约定）。每个现代分词器都是 BPE 变体、WordPiece（BERT）或 SentencePiece（T5、LLaMA）。

> The `Ġ` prefix marks word boundaries (a GPT-2 convention). Every modern tokenizer is a BPE variant, WordPiece (BERT), or SentencePiece (T5, LLaMA).

### When to pick which · 怎么选

| 场景 | 选择 |
|------|------|
| 预训练通用词向量，不需要容忍 OOV | GloVe 300d |
| 预训练通用词向量，必须处理拼写错误 / 新造词 / 形态丰富的语言 | FastText |
| 任何要进入 transformer 的东西（训练或推理） | 模型出厂自带的分词器。永不更换。 |
| 从零训练自己的语言模型 | 先在你的语料上训练一个 BPE 或 SentencePiece 分词器 |
| 用线性模型做生产文本分类 | 依然是 TF-IDF。见第 02 课。 |

> Pretrained general-purpose word vectors, no OOV tolerance needed: GloVe 300d. Pretrained general-purpose word vectors, must handle misspellings / neologisms / morphologically rich languages: FastText.
> Anything going into a transformer (training or inference): whatever tokenizer the model shipped with. Never swap.

## Ship It · 交付

保存为 `outputs/skill-embeddings-picker.md`：

```markdown
---
name: tokenizer-picker
description: Pick a tokenization approach for a new language model or text pipeline.
version: 1.0.0
phase: 5
lesson: 04
tags: [nlp, tokenization, embeddings]
---

Given a task and dataset description, you output:

1. Tokenization strategy (word-level, BPE, WordPiece, SentencePiece, byte-level). One-sentence reason.
2. Vocabulary size target (e.g., 32k for an English-only LM, 64k-100k for multilingual).
3. Library call with the exact training command. Name the library. Quote the arguments.
4. One reproducibility pitfall. Tokenizer-model mismatch is the single most common silent production bug; call out which pair must be used together.

Refuse to recommend training a custom tokenizer when the user is fine-tuning a pretrained LLM. Refuse to recommend word-level tokenization for any model targeting production inference. Flag non-English / multi-script corpora as needing SentencePiece with byte fallback.
```

> Save as `outputs/skill-embeddings-picker.md`:

## Exercises · 练习

1. **简单。** 跑 `char_ngrams("playing")` 和 `char_ngrams("played")`，计算两个 n-gram 集合的 Jaccard 重叠。你会看到大量共享的片段（`pla`、`lay`、`play`）——这正是 FastText 能在形态变体之间良好迁移的原因。
2. **中等。** 扩展 `learn_bpe`，让它追踪词表的增长。画出「每个语料字符对应的 token 数」随合并次数变化的曲线。你会看到开始时压缩飞快，之后渐近到每个 token 约 2-3 个字符。
3. **困难。** 在莎士比亚全集上训练一个 1k 次合并的 BPE。比较常见词和稀有专有名词的分词结果，测量前后平均每词 token 数。写下让你感到意外的东西。

## Key Terms · 术语表

| 术语 | 人们的说法 | 实际含义 |
|------|-----------|---------|
| Co-occurrence matrix | 「词-词频率表」 | `X[i][j]` = 词 `j` 在词 `i` 周围窗口内出现的频率。 |
| Subword | 「词的碎片」 | 字符 n-gram（FastText）或学出来的 token（BPE/WordPiece/SentencePiece）。 |
| BPE | 「字节对编码」 | 反复合并最高频的相邻对，直到词表达到目标大小。 |
| OOV | 「词表外」 | 模型从没见过的词。Word2Vec/GloVe 拿它没办法，FastText 和 BPE 能处理。 |
| Byte-level BPE | 「字节级 BPE」 | GPT-2 的方案。词表从 256 个字节起步，所以永远不会有 OOV。 |

## Further Reading · 延伸阅读

- [Pennington, Socher, Manning (2014). GloVe: Global Vectors for Word Representation](https://nlp.stanford.edu/pubs/glove.pdf) —— GloVe 原论文，七页，损失推导至今仍是最好的。
- [Bojanowski et al. (2017). Enriching Word Vectors with Subword Information](https://arxiv.org/abs/1607.04606) —— FastText。
- [Sennrich, Haddow, Birch (2016). Neural Machine Translation of Rare Words with Subword Units](https://arxiv.org/abs/1508.07909) —— 把 BPE 带进现代 NLP 的那篇论文。
- [Hugging Face tokenizer summary](https://huggingface.co/docs/transformers/tokenizer_summary) —— BPE、WordPiece、SentencePiece 在实践中到底差在哪。
