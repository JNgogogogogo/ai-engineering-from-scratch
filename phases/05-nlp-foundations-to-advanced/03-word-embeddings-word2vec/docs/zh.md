# Word Embeddings — Word2Vec from Scratch · 词向量——从零实现 Word2Vec

> 要知其词，先观其伴。在这个想法上训练一个浅层网络，几何结构自然浮现。
> A word is the company it keeps. Train a shallow net on that idea and geometry falls out.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 02 (BoW + TF-IDF), Phase 3 · 03 (Backpropagation from Scratch)
**Time:** ~75 minutes

## The Problem · 问题在哪

TF-IDF 知道 `dog` 和 `puppy` 是两个不同的词，但不知道它们的意思几乎相同。在 `dog` 上训练的分类器，无法泛化到讲 `puppy` 的评论。你可以罗列同义词来糊弄过去，但稀有词、领域行话、以及每一种你没预料到的语言都会让它失效。

你要的是这样一种表示：`dog` 和 `puppy` 在空间里落得很近；`king - man + woman` 落在 `queen` 附近；在 `dog` 上训练的模型，免费把一部分信号迁移给 `puppy`。

Word2Vec 给了我们这个空间。两层神经网络，万亿 token 的训练规模，2013 年发表。架构简单得近乎尴尬，结果却重塑了此后十年的 NLP。

> TF-IDF knows `dog` and `puppy` are different words. It does not know they mean nearly the same thing. A classifier trained on `dog` cannot generalize to a review about `puppy`. You can paper over this by listing synonyms, but that fails on rare terms, domain jargon, and every language you did not anticipate.
> You want a representation where `dog` and `puppy` land close together in space. Where `king - man + woman` lands near `queen`. Where a model trained on `dog` transfers some signal to `puppy` for free.
> Word2Vec gave us that space. Two layer neural network, trillion-token training runs, published in 2013. The architecture is almost embarrassingly simple. The results reshaped NLP for a decade.

## The Concept · 概念

**分布假说（distributional hypothesis）**（Firth, 1957）：「观其伴，知其义（You shall know a word by the company it keeps）。」如果两个词出现在相似的上下文里，它们的意思可能相近。

Word2Vec 有两种形态，都在利用这个想法。

- **Skip-gram。** 给定中心词，预测周围的词。窗口大小为 2 时：`cat -> (the, sat, on)`。
- **CBOW（连续词袋，continuous bag of words）。** 给定周围的词，预测中心词。`(the, sat, on) -> cat`。

Skip-gram 训练更慢，但对稀有词处理得更好，于是成了默认。

网络只有一个隐藏层，没有非线性。输入是词表上的 one-hot 向量，输出是词表上的 softmax。训练完把输出层扔掉：隐藏层的权重就是词向量。

```
one-hot(center) ── W ──▶ hidden (d-dim) ── W' ──▶ softmax(vocab)
                          ^
                          this is the embedding
```

诀窍在于：对 10 万个词做 softmax，贵得离谱。Word2Vec 用**负采样（negative sampling）**把它变成一个二元分类任务：预测「这个上下文词是否出现在这个中心词附近，是或否」。每个训练对采一小撮负例（不共现的）词，而不是对整个词表算 softmax。

```figure
word-vector-arithmetic
```

> **Distributional hypothesis** (Firth, 1957): "You shall know a word by the company it keeps." If two words appear in similar contexts, they probably mean similar things.
> Skip-gram is slower to train but handles rare words better. It became the default.
> The network has one hidden layer with no nonlinearity. Input is a one-hot vector over the vocabulary. Output is a softmax over the vocabulary. After training, you throw away the output layer. The hidden layer weights are the embeddings.
> The trick: softmax over 100k words is prohibitively expensive. Word2Vec uses **negative sampling** to turn it into a binary classification task. Predict "did this context word appear near this center word, yes or no". Sample a handful of negative (non-co-occurring) words per training pair instead of computing softmax over the whole vocabulary.

## Build It · 动手造

### Step 1: training pairs from a corpus · 从语料生成训练对

```python
def skipgram_pairs(docs, window=2):
    pairs = []
    for doc in docs:
        for i, center in enumerate(doc):
            for j in range(max(0, i - window), min(len(doc), i + window + 1)):
                if i == j:
                    continue
                pairs.append((center, doc[j]))
    return pairs
```

```python
>>> skipgram_pairs([["the", "cat", "sat", "on", "mat"]], window=2)
[('the', 'cat'), ('the', 'sat'),
 ('cat', 'the'), ('cat', 'sat'), ('cat', 'on'),
 ('sat', 'the'), ('sat', 'cat'), ('sat', 'on'), ('sat', 'mat'),
 ...]
```

窗口内每一个（中心词, 上下文词）对，都是一个正训练样本。

> Every (center, context) pair in a window is a positive training example.

### Step 2: embedding tables · 嵌入表

两个矩阵。`W` 是中心词嵌入表（你要保留的那张），`W'` 是上下文词表（经常被丢弃，有时与 `W` 平均）。

```python
import numpy as np


def init_embeddings(vocab_size, dim, seed=0):
    rng = np.random.default_rng(seed)
    W = rng.normal(0, 0.1, size=(vocab_size, dim))
    W_prime = rng.normal(0, 0.1, size=(vocab_size, dim))
    return W, W_prime
```

小随机初始化。词表 1 万、维度 100 是现实规模；教学用 50 词 × 16 维就足以看到几何结构。

> Two matrices. `W` is the center-word embedding table (the one you keep). `W'` is the context-word table (often discarded, sometimes averaged with `W`).
> Small random init. Vocab size 10k and dim 100 is realistic; for teaching, 50 vocab x 16 dim is enough to see the geometry.

### Step 3: negative sampling objective · 负采样目标

对每个正样本对 `(center, context)`，从词表随机采 `k` 个词作负例。训练模型，让点积 `W[center] · W'[context]` 对正例高、对负例低。

```python
def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -20, 20)))


def train_pair(W, W_prime, center_idx, context_idx, negative_indices, lr):
    v_c = W[center_idx]
    u_pos = W_prime[context_idx]
    u_negs = W_prime[negative_indices]

    pos_score = sigmoid(v_c @ u_pos)
    neg_scores = sigmoid(u_negs @ v_c)

    grad_center = (pos_score - 1) * u_pos
    for i, u in enumerate(u_negs):
        grad_center += neg_scores[i] * u

    W[context_idx] = W[context_idx]
    W_prime[context_idx] -= lr * (pos_score - 1) * v_c
    for i, neg_idx in enumerate(negative_indices):
        W_prime[neg_idx] -= lr * neg_scores[i] * v_c
    W[center_idx] -= lr * grad_center
```

核心公式：正对上的 logistic 损失（希望 sigmoid 接近 1），加上负对上的 logistic 损失（希望 sigmoid 接近 0）。梯度流向两张表。完整推导在原论文里；想真正掌握，就拿纸笔推一遍。

> For each positive pair `(center, context)`, sample `k` random words from the vocabulary as negatives. Train the model so the dot product `W[center] · W'[context]` is high for positives and low for negatives.
> The magic formula: logistic loss on positive pair (want sigmoid near 1) plus logistic loss on negative pairs (want sigmoid near 0). Gradients flow to both tables. Full derivation is in the original paper; walk through it once with pencil and paper if you want it to stick.

### Step 4: train on a toy corpus · 在玩具语料上训练

```python
def train(docs, dim=16, window=2, k_neg=5, epochs=100, lr=0.05, seed=0):
    vocab = build_vocab(docs)
    vocab_size = len(vocab)
    rng = np.random.default_rng(seed)
    W, W_prime = init_embeddings(vocab_size, dim, seed=seed)
    pairs = skipgram_pairs(docs, window=window)

    for epoch in range(epochs):
        rng.shuffle(pairs)
        for center, context in pairs:
            c_idx = vocab[center]
            ctx_idx = vocab[context]
            negs = rng.integers(0, vocab_size, size=k_neg)
            negs = [n for n in negs if n != ctx_idx and n != c_idx]
            train_pair(W, W_prime, c_idx, ctx_idx, negs, lr)
    return vocab, W
```

在大语料上跑够多个 epoch 之后，共享上下文的词会有相近的中心词嵌入。玩具语料上你只能隐约看到这个效果；在几十亿 token 上，效果惊人地明显。

> After enough epochs on a large corpus, words that share contexts have similar center embeddings. On a toy corpus, you see the effect faintly. On billions of tokens, you see it dramatically.

### Step 5: the analogy trick · 类比戏法

```python
def nearest(vocab, W, target_vec, topk=5, exclude=None):
    exclude = exclude or set()
    inv_vocab = {i: w for w, i in vocab.items()}
    norms = np.linalg.norm(W, axis=1, keepdims=True) + 1e-9
    W_norm = W / norms
    target = target_vec / (np.linalg.norm(target_vec) + 1e-9)
    sims = W_norm @ target
    order = np.argsort(-sims)
    out = []
    for i in order:
        if i in exclude:
            continue
        out.append((inv_vocab[i], float(sims[i])))
        if len(out) == topk:
            break
    return out


def analogy(vocab, W, a, b, c, topk=5):
    v = W[vocab[b]] - W[vocab[a]] + W[vocab[c]]
    return nearest(vocab, W, v, topk=topk, exclude={vocab[a], vocab[b], vocab[c]})
```

在预训练的 300 维 Google News 向量上：

```python
>>> analogy(vocab, W, "man", "king", "woman")
[('queen', 0.71), ('monarch', 0.62), ('princess', 0.59), ...]
```

`king - man + woman = queen`。不是因为模型懂什么是王室，而是因为向量 `(king - man)` 捕捉到了类似「王室」的东西，把它加到 `woman` 上，就落在「王室女性」区域附近。

> `king - man + woman = queen`. Not because the model knows what royalty is. Because the vector `(king - man)` captures something like "royal", and adding it to `woman` lands near the royal-female region.

## Use It · 实战用法

手写 Word2Vec 是为了教学。生产 NLP 用 `gensim`。

> Writing Word2Vec from scratch is teaching. Production NLP uses `gensim`.

```python
from gensim.models import Word2Vec

sentences = [
    ["the", "cat", "sat", "on", "the", "mat"],
    ["the", "dog", "ran", "across", "the", "room"],
]

model = Word2Vec(
    sentences,
    vector_size=100,
    window=5,
    min_count=1,
    sg=1,
    negative=5,
    workers=4,
    epochs=30,
)

print(model.wv["cat"])
print(model.wv.most_similar("cat", topn=3))
```

真实工作里你几乎从不自己训练 Word2Vec，而是下载预训练向量。

- **GloVe** —— Stanford 的共现矩阵分解方案。有 50d、100d、200d、300d 检查点，通用覆盖好。第 04 课专门讲 GloVe。
- **fastText** —— Facebook 对 Word2Vec 的扩展，把字符 n-gram 也嵌入进去，靠组合子词处理词表外单词。第 04 课。
- **Google News 预训练 Word2Vec** —— 300d、300 万词表，2013 年发布，至今每天都有人下载。

> For real work, you almost never train Word2Vec yourself. You download pre-trained vectors.
> **GloVe** — Stanford's co-occurrence-matrix factorization approach. 50d, 100d, 200d, 300d checkpoints. Good general coverage. Lesson 04 covers GloVe specifically.
> **fastText** — Facebook's Word2Vec extension that embeds character n-grams. Handles out-of-vocabulary words by composing subwords. Lesson 04.
> **Pretrained Word2Vec on Google News** — 300d, 3M word vocabulary, published 2013. Still downloaded daily.

### When Word2Vec still wins in 2026 · Word2Vec 在 2026 年仍然赢的场景

- 轻量级的领域专属检索。在笔记本上花一小时训练医学摘要，就得到任何通用模型都捕捉不到的专用向量。
- 类比式特征工程。`gender_vector = mean(man - woman pairs)`，从其他词的向量里减去它，就得到一条无性别轴。公平性研究仍在用。
- 可解释性。100 维小到可以用 PCA 或 t-SNE 画出来，亲眼看到聚类成形。
- 任何必须在设备端、无 GPU 推理的地方。Word2Vec 查询就是取一行。

> Lightweight domain-specific retrieval. Train on medical abstracts in an hour on a laptop, get specialized vectors no general model captures.
> Analogy-style feature engineering. `gender_vector = mean(man - woman pairs)`. Subtract it from other words to get a gender-neutral axis. Still used in fairness research.
> Interpretability. 100d is small enough to plot via PCA or t-SNE and actually see clusters form.
> Anywhere inference has to run on-device with no GPU. Word2Vec lookup is a single row fetch.

### Where Word2Vec fails · Word2Vec 在哪里失败

一词多义之墙。`bank` 只有一个向量，`river bank` 和 `financial bank` 共用它；`table`（电子表格 vs 家具）也共用。下游分类器无法从这个向量里区分词义。

上下文嵌入（ELMo、BERT 以及此后的所有 transformer）解决了这个问题：根据周围上下文，为每次出现的词生成不同的向量。这就是从 Word2Vec 到 BERT 的飞跃：从静态到上下文。Phase 7 讲 transformer 那一半。

词表外（OOV）问题是另一个失败点。`Zoomer-approved` 若不在训练数据里，Word2Vec 就从没见过它，没有任何兜底。fastText 用子词组合修复了这一点（第 04 课）。

> The polysemy wall. `bank` has one vector. `river bank` and `financial bank` share it. `table` (spreadsheet vs. furniture) shares it. A classifier downstream cannot distinguish the senses from the vector.
> Contextual embeddings (ELMo, BERT, every transformer since) solved this by producing a different vector for each occurrence of the word based on surrounding context. That is the jump from Word2Vec to BERT: from static to contextual. Phase 7 covers the transformer half.
> The out-of-vocabulary problem is the other failure. Word2Vec has never seen `Zoomer-approved` if it was not in training data. No fallback. fastText fixes this with subword composition (lesson 04).

## Ship It · 交付

保存为 `outputs/skill-embedding-probe.md`：

```markdown
---
name: embedding-probe
description: Inspect a word2vec model. Run analogies, find neighbors, diagnose quality.
version: 1.0.0
phase: 5
lesson: 03
tags: [nlp, embeddings, debugging]
---

You probe trained word embeddings to verify they are working. Given a `gensim.models.KeyedVectors` object and a vocabulary, you run:

1. Three canonical analogy tests. `king : man :: queen : woman`. `paris : france :: tokyo : japan`. `walking : walked :: swimming : ?`. Report the top-1 result and its cosine.
2. Five nearest-neighbor tests on domain-specific words the user supplies. Print top-5 neighbors with cosines.
3. One symmetry check. `similarity(a, b) == similarity(b, a)` to within float precision.
4. One degenerate check. If any embedding has a norm below 0.01 or above 100, the model has a training bug. Flag it.

Refuse to declare a model good on analogy accuracy alone. Analogy benchmarks are gameable and do not transfer to downstream tasks. Recommend intrinsic + downstream evaluation together.
```

> Save as `outputs/skill-embedding-probe.md`:

## Exercises · 练习

1. **简单。** 在一个微型语料（20 句关于猫和狗的句子）上跑训练循环。200 个 epoch 后，验证 `nearest(vocab, W, W[vocab["cat"]])` 的前 3 名里有 `dog`。没有就加大 epoch 数或词表。
2. **中等。** 加上高频词子采样：频率高于 `10^-5` 的词，按与频率成比例的概率从训练对中丢弃。测量它对稀有词相似度的影响。
3. **困难。** 在 20 Newsgroups 语料上训练一个模型。计算两条偏置轴：`he - she` 和 `doctor - nurse`。把职业词投影到两条轴上，报告偏置差距最大的职业。这正是公平性研究者使用的那类探针。

## Key Terms · 术语表

| 术语 | 人们的说法 | 实际含义 |
|------|-----------|---------|
| Word embedding | 「词变成向量」 | 从上下文学到的稠密低维（通常 100-300）表示。 |
| Skip-gram | 「Word2Vec 的招式」 | 从中心词预测上下文词。比 CBOW 慢，对稀有词更好。 |
| Negative sampling | 「训练捷径」 | 用对 `k` 个随机词的二元分类，替代全词表 softmax。 |
| Static embedding | 「一词一向量」 | 无论上下文是什么，向量都相同。在一词多义上失败。 |
| Contextual embedding | 「随上下文变化的向量」 | 每次出现都依据周围的词生成不同向量。transformer 产出的东西。 |
| OOV | 「词表外」 | 训练时没见过的词。Word2Vec 给不出这些词的向量。 |

## Further Reading · 延伸阅读

- [Mikolov et al. (2013). Distributed Representations of Words and Phrases and their Compositionality](https://arxiv.org/abs/1310.4546) —— 负采样那篇论文。短且好读。
- [Rong, X. (2014). word2vec Parameter Learning Explained](https://arxiv.org/abs/1411.2738) —— 最清晰的梯度推导；如果原论文的数学让你发怵，就看这篇。
- [gensim Word2Vec tutorial](https://radimrehurek.com/gensim/models/word2vec.html) —— 真正能用的生产训练参数。
