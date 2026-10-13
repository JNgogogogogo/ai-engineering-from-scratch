# Bag of Words, TF-IDF, and Text Representation · 词袋、TF-IDF 与文本表示

> 先数数，再思考。2026 年，在目标明确的任务上 TF-IDF 仍然打赢嵌入。
> Count first, think later. TF-IDF still beats embeddings on well-defined tasks in 2026.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 01 (Text Processing), Phase 2 · 02 (Linear Regression from Scratch)
**Time:** ~75 minutes

## The Problem · 问题在哪

模型需要数字，你手里是字符串。

每条 NLP 流水线都得回答同一个问题：怎么把一条变长的 token 流，变成分类器能消费的定长向量？这个领域落地的第一个答案，是「能用」里最蠢的那个：数词，做成向量。

这个向量扛起的生产 NLP，比任何嵌入模型都多。垃圾邮件过滤、主题分类、日志异常检测、搜索排序（BM25 之前的时代）、第一波情感分析、学术 NLP 基准的头一个十年。2026 年的从业者在窄分类任务上仍然首选它。它快、可解释，而且在「词是否出现」才是关键的任务上，常常与 4 亿参数的嵌入模型打不出差别。

本课从零构建词袋（bag of words），再构建 TF-IDF；然后展示 scikit-learn 如何用三行做同样的事；最后点名那个逼你转向嵌入的失败模式。

> The model needs numbers. You have strings.
> Every NLP pipeline has to answer the same question. How do we turn a variable-length stream of tokens into a fixed-size vector that a classifier can consume. The first answer the field landed on was the dumbest one that works. Count the words. Make a vector.
> That vector has carried more production NLP than any embedding model. Spam filters, topic classifiers, log anomaly detection, search ranking (before BM25), the first wave of sentiment analysis, the first decade of academic NLP benchmarks. ... It is fast, interpretable, and often indistinguishable from a 400M-parameter embedding model on tasks where word presence is what matters.
> This lesson builds bag of words, then TF-IDF, from scratch. Then shows scikit-learn doing the same in three lines. Then names the failure mode that makes you reach for embeddings.

## The Concept · 概念

**词袋（Bag of Words, BoW）** 丢掉词序。对每个文档，数每个词表词出现了多少次。向量长度就是词表大小，位置 `i` 是词 `i` 的计数。

**TF-IDF** 对 BoW 重新加权。出现在每个文档里的词没有信息量，把它压低；语料里罕见、却在单个文档里高频的词是信号，把它抬高。

```
TF-IDF(w, d) = TF(w, d) * IDF(w)
             = count(w in d) / |d| * log(N / df(w))
```

其中 `TF` 是词在文档中的词频，`df` 是文档频率（多少文档包含这个词），`N` 是文档总数。`log` 让无处不在的词的权重保持有界。

关键性质：两者产出的都是稀疏向量，且轴可解释。你可以查看训练好的分类器的权重，直接读出哪些词把文档推向哪个类别。768 维的 BERT 嵌入做不到这一点。

```figure
bow-tfidf
```

> **Bag of Words (BoW)** throws away order. For each document, count how many times each vocabulary word appears. Vector length is the vocabulary size. Position `i` is the count of word `i`.
> **TF-IDF** reweights BoW. A word that appears in every document is uninformative, so scale it down. A word rare across the corpus but frequent in a single document is signal, so scale it up.
> Key property: both produce sparse vectors with interpretable axes. You can look at a trained classifier's weights and read which words push a document toward each class. You cannot do this with a 768-dimensional BERT embedding.

## Build It · 动手造

### Step 1: build the vocabulary · 构建词表

```python
def build_vocab(docs):
    vocab = {}
    for doc in docs:
        for token in doc:
            if token not in vocab:
                vocab[token] = len(vocab)
    return vocab
```

输入：已分词文档的列表（任何词级分词器都行；本课的 `code/main.py` 用的是简化的小写化变体）。输出：`{word: index}` 字典。插入顺序稳定，所以词索引 0 就是第一个文档里第一个出现的词。约定各有不同；scikit-learn 按字母序排序。

> Input: list of tokenized documents (any word-level tokenizer will do; the `code/main.py` in this lesson uses a simplified lowercase variant). Output: `{word: index}` dict. Stable insertion order means word index 0 is the first word seen in the first document. Convention varies; scikit-learn sorts alphabetically.

### Step 2: bag of words · 词袋

```python
def bag_of_words(docs, vocab):
    matrix = [[0] * len(vocab) for _ in docs]
    for i, doc in enumerate(docs):
        for token in doc:
            if token in vocab:
                matrix[i][vocab[token]] += 1
    return matrix
```

```python
>>> docs = [["cat", "sat", "on", "mat"], ["cat", "cat", "ran"]]
>>> vocab = build_vocab(docs)
>>> bag_of_words(docs, vocab)
[[1, 1, 1, 1, 0], [2, 0, 0, 0, 1]]
```

行是文档，列是词表索引。条目 `[i][j]` 回答「词 `j` 在文档 `i` 里出现了几次」。文档 1 里 `cat` 出现了两次，所以计 2；文档 0 里 `ran` 一次都没出现，所以计 0。

> Rows are documents. Columns are vocabulary indices. Entry `[i][j]` is "how many times word `j` appears in document `i`." Doc 1 has `cat` twice because it did. Doc 0 has `ran` zero times because it did not.

### Step 3: term frequency and document frequency · 词频与文档频率

```python
import math


def term_frequency(doc_bow, doc_length):
    return [c / doc_length if doc_length else 0 for c in doc_bow]


def document_frequency(bow_matrix):
    df = [0] * len(bow_matrix[0])
    for row in bow_matrix:
        for j, count in enumerate(row):
            if count > 0:
                df[j] += 1
    return df


def inverse_document_frequency(df, n_docs):
    return [math.log((n_docs + 1) / (d + 1)) + 1 for d in df]
```

两个值得点名的平滑技巧。`(n+1)/(d+1)` 避免了 `log(x/0)`；末尾的 `+1` 保证出现在所有文档里的词的 IDF 仍是 1（而不是 0），与 scikit-learn 的默认一致。其他实现用原始的 `log(N/df)`。两者都能用；平滑版更友好。

> Two smoothing tricks worth naming. The `(n+1)/(d+1)` avoids `log(x/0)`. The trailing `+1` ensures a word in every document still has IDF 1 (not 0), matching scikit-learn's default. Other implementations use raw `log(N/df)`. Both work; the smoothed version is friendlier.

### Step 4: TF-IDF

```python
def tfidf(bow_matrix):
    n_docs = len(bow_matrix)
    df = document_frequency(bow_matrix)
    idf = inverse_document_frequency(df, n_docs)
    out = []
    for row in bow_matrix:
        length = sum(row)
        tf = term_frequency(row, length)
        out.append([tf_j * idf_j for tf_j, idf_j in zip(tf, idf)])
    return out
```

```python
>>> docs = [
...     ["the", "cat", "sat"],
...     ["the", "dog", "sat"],
...     ["the", "cat", "ran"],
... ]
>>> vocab = build_vocab(docs)
>>> bow = bag_of_words(docs, vocab)
>>> tfidf(bow)
```

三个文档，五个词表词（`the`、`cat`、`sat`、`dog`、`ran`）。`the` 在三个文档里都出现，所以它的 IDF 低；`dog` 只出现在一个文档里，所以它的 IDF 高。向量稀疏（大多数条目都很小），有区分力的词凸显出来。

> Three documents, five vocab words (`the`, `cat`, `sat`, `dog`, `ran`). `the` appears in all three, so its IDF is low. `dog` appears in one, so its IDF is high. The vectors are sparse (most entries are small) and the discriminative words pop.

### Step 5: L2-normalize rows · 对行做 L2 归一化

```python
def l2_normalize(matrix):
    out = []
    for row in matrix:
        norm = math.sqrt(sum(x * x for x in row))
        out.append([x / norm if norm else 0 for x in row])
    return out
```

不归一化，长文档就会得到更大的向量，在相似度得分里占便宜。L2 归一化把每个文档放到单位超球面上。行与行之间的余弦相似度从此就是一次点积。

> Without normalization, a longer document gets a larger vector and dominates similarity scores. L2 normalization puts every document on the unit hypersphere. Cosine similarity between rows is now just a dot product.

## Use It · 实战用法

scikit-learn 提供了生产级实现。

> scikit-learn ships the production version.

```python
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

docs = ["the cat sat on the mat", "the dog sat on the mat", "the cat ran"]

bow_vectorizer = CountVectorizer()
bow = bow_vectorizer.fit_transform(docs)
print(bow_vectorizer.get_feature_names_out())
print(bow.toarray())

tfidf_vectorizer = TfidfVectorizer()
tfidf = tfidf_vectorizer.fit_transform(docs)
print(tfidf.toarray().round(3))
```

`CountVectorizer` 一次调用完成分词、词表和 BoW。`TfidfVectorizer` 加上 IDF 加权和 L2 归一化。两者都返回稀疏矩阵。到了 10 万文档的规模，稠密版本塞不进内存；在分类器要求稠密之前，保持稀疏。

> `CountVectorizer` does tokenization, vocabulary, and BoW in one call. `TfidfVectorizer` adds IDF weighting and L2 normalization. Both return sparse matrices. For 100k documents, the dense version does not fit in memory; stay sparse until the classifier demands dense.

改变一切的旋钮：

| 参数 | 作用 |
|------|------|
| `ngram_range=(1, 2)` | 引入二元组（bigram）。通常能提升分类效果。 |
| `min_df=2` | 丢弃出现在少于 2 个文档里的词。在噪声数据上给词表瘦身。 |
| `max_df=0.95` | 丢弃出现在超过 95% 文档里的词。不需要硬编码词表就能近似停用词去除。 |
| `stop_words="english"` | scikit-learn 内置停用词表。取决于任务——情感分析*不应该*丢掉否定词。 |
| `sublinear_tf=True` | 用 `1 + log(tf)` 代替原始 `tf`。某个词在单个文档里重复很多次时有帮助。 |

> Knobs that change everything:
> `ngram_range=(1, 2)` | Include bigrams. Usually boosts classification.
> `max_df=0.95` | Drop words in more than 95% of docs. Approximates stopword removal without a hardcoded list.
> `stop_words="english"` | scikit-learn's builtin stopword list. Task-dependent — sentiment analysis should *not* drop negations.

### When TF-IDF still wins (as of 2026) · TF-IDF 仍然赢的场景（截至 2026）

- 垃圾检测、主题打标、日志异常标记。起作用的是「词是否出现」，语义细节无关紧要。
- 低数据场景（几百条标注样本）。TF-IDF 加逻辑回归，没有预训练成本。
- 任何延迟要紧的地方。TF-IDF 加线性模型，微秒级出答案；把文档喂过 transformer 做嵌入要 10-100 毫秒。
- 必须能解释自身预测的系统。直接查看分类器系数：得分最高的正向词就是理由。

> Spam detection, topic labeling, log anomaly flagging. Word presence is what matters; semantic nuance does not.
> Low-data regimes (hundreds of labeled examples). TF-IDF plus logistic regression has no pretraining cost.
> Anywhere latency matters. TF-IDF plus a linear model answers in microseconds. Embedding a document through a transformer takes 10-100ms.
> Systems that must explain their predictions. Inspect the classifier's coefficients. Top positive words are the reason.

### When TF-IDF fails · TF-IDF 什么时候会输

语义盲区失败。看这两个文档：

- "The movie was not good at all."
- "The movie was excellent."

一个是负面评论，一个是正面评论。它们的 TF-IDF 重叠恰好是 `{the, movie, was}`。词袋分类器只能靠死记硬背：`not` 出现在 `good` 附近会翻转标签。数据足够多时它能学会，但永远不会像真正理解语法的模型那样优雅。

另一个失败：推理时遇到词表外（out-of-vocabulary）词。在 IMDb 评论上训练的 BoW 模型，面对 `Zoomer-approved` 完全不知所措——如果这个 token 训练时没出现过。子词嵌入（第 04 课）能处理，TF-IDF 不能。

> The semantic blindness failure. Consider these two documents:
> One is a negative review. One is positive. Their TF-IDF overlap is exactly `{the, movie, was}`. A bag-of-words classifier has to memorize that the word `not` near `good` flips the label. It can learn this on enough data, but never as gracefully as a model that understands syntax.
> The other failure: out-of-vocabulary words at inference. A BoW model trained on IMDb reviews has no idea what to do with `Zoomer-approved` if that token never appeared in training. Subword embeddings (lesson 04) handle this. TF-IDF cannot.

### Hybrid: TF-IDF weighted embeddings · 混合方案：TF-IDF 加权嵌入

2026 年中等数据量分类的务实默认：把 TF-IDF 权重当作施加在词嵌入上的注意力。

```python
def tfidf_weighted_embedding(doc, tfidf_scores, embedding_table, dim):
    vec = [0.0] * dim
    total_weight = 0.0
    for token in doc:
        if token not in embedding_table or token not in tfidf_scores:
            continue
        weight = tfidf_scores[token]
        emb = embedding_table[token]
        for i in range(dim):
            vec[i] += weight * emb[i]
        total_weight += weight
    if total_weight == 0:
        return vec
    return [v / total_weight for v in vec]
```

你从嵌入得到语义容量，从 TF-IDF 得到对稀有词的强调；分类器在池化后的向量上训练。在标注样本约 5 万以下的情感、主题、意图分类上，这一混合方案胜过两者单独任何一个。

> The 2026 pragmatic default for medium-data classification: use TF-IDF weights as attention over word embeddings.
> You get semantic capacity from embeddings, and rare-word emphasis from TF-IDF. Classifier trains on the pooled vector. This outperforms either on its own for sentiment, topic, and intent classification below about 50k labeled examples.

## Ship It · 交付

保存为 `outputs/prompt-vectorization-picker.md`：

```markdown
---
name: vectorization-picker
description: Given a text-classification task, recommend BoW, TF-IDF, embeddings, or a hybrid.
phase: 5
lesson: 02
---

You recommend a text-vectorization strategy. Given a task description, output:

1. Representation (BoW, TF-IDF, transformer embeddings, or a hybrid). Explain why in one sentence.
2. Specific vectorizer configuration. Name the library. Quote the arguments (`ngram_range`, `min_df`, `max_df`, `sublinear_tf`, `stop_words`).
3. One failure mode to test before shipping.

Refuse to recommend embeddings when the user has under 500 labeled examples unless they show evidence of semantic failure in a TF-IDF baseline. Refuse to remove stopwords for sentiment analysis (negations carry signal). Flag class imbalance as needing more than a vectorizer change.

Example input: "Classifying 30k customer support tickets into 12 categories. Most tickets are 2-3 sentences. English only. Need explainability for audit logs."

Example output:

- Representation: TF-IDF. 30k examples is not small; explainability requirement rules out dense embeddings.
- Config: `TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_df=0.95, sublinear_tf=True, stop_words=None)`. Keep stopwords because category keywords sometimes are stopwords ("not working" vs "working").
- Failure to test: verify `min_df=3` does not drop rare category keywords. Run `get_feature_names_out` filtered by class and eyeball.
```

> Save as `outputs/prompt-vectorization-picker.md`:

## Exercises · 练习

1. **简单。** 在 L2 归一化的 TF-IDF 输出上实现 `cosine_similarity(doc_vec_a, doc_vec_b)`。验证：相同文档得分 1.0，词表不相交的文档得分 0.0。
2. **中等。** 给 `bag_of_words` 加上 `n-gram` 支持：参数 `n` 产出 n-gram 计数。测试 `n=2` 时 `["the", "cat", "sat"]` 产出 `["the cat", "cat sat"]` 的二元组计数。
3. **困难。** 用 GloVe 100d 向量（下载一次并缓存）构建上面的 TF-IDF 加权嵌入混合方案。在 20 Newsgroups 数据集上比较分类准确率：纯 TF-IDF、纯平均池化嵌入、混合方案。报告谁在哪种情况下赢。

## Key Terms · 术语表

| 术语 | 人们的说法 | 实际含义 |
|------|-----------|---------|
| BoW | 「词频向量」 | 一个文档里各词表词的计数。丢掉词序。 |
| TF | 「词频」 | 词在文档中的计数，可选按文档长度归一化。 |
| DF | 「文档频率」 | 至少包含该词一次的文档数量。 |
| IDF | 「逆文档频率」 | 平滑后的 `log(N / df)`。压低无处不在的词。 |
| Sparse vector | 「大部分是零的向量」 | 词表通常有 1 万到 10 万个词；任何一个文档里绝大多数词都不出现。 |
| Cosine similarity | 「向量夹角」 | L2 归一化向量的点积。1 是完全相同，0 是正交。 |

## Further Reading · 延伸阅读

- [scikit-learn — feature extraction from text](https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction) —— 权威 API 参考，附每个旋钮的说明。
- [Salton, G., & Buckley, C. (1988). Term-weighting approaches in automatic text retrieval](https://www.sciencedirect.com/science/article/pii/0306457388900210) —— 让 TF-IDF 当了十年默认方案的那篇论文。
- ["Why TF-IDF Still Beats Embeddings" — Ashfaque Thonikkadavan (Medium)](https://medium.com/@cmtwskb/why-tf-idf-still-beats-embeddings-ad85c123e1b2) —— 2026 年的视角：老方法何时赢、为什么赢。
