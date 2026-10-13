# Topic Modeling — LDA and BERTopic · 主题建模——LDA 与 BERTopic

> LDA：文档是主题的混合，主题是词上的分布。BERTopic：文档在嵌入空间里聚类，簇就是主题。同一个目标，不同的分解。
> LDA: documents are mixtures of topics, topics are distributions over words. BERTopic: documents cluster in embedding space, clusters are topics. Same goal, different decompositions.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 5 · 02 (BoW + TF-IDF), Phase 5 · 03 (Word2Vec)
**Time:** ~45 minutes

## The Problem · 问题在哪

你手上有 10,000 张客服工单、50,000 篇新闻文章、或 200,000 条推文。你需要知道这堆语料在讲什么，但又不打算读它。你没有标注好的类别。你甚至不知道存在多少个类别。

主题建模（topic modeling）无需监督就能回答这个问题。给它一个语料，它还你一小撮连贯的主题，以及每篇文档在这些主题上的分布。

两个算法家族主导这个领域。LDA（2003）把每篇文档当作潜在主题的混合，把每个主题当作词上的分布。推断是贝叶斯的。在你需要混合隶属（mixed-membership）主题指派、以及可解释的词级概率分布的生产场景里，它至今仍在服役。

BERTopic（2020）用 BERT 编码文档，用 UMAP 降维，用 HDBSCAN 聚类，再通过基于类的 TF-IDF（class-based TF-IDF）抽取主题词。短文本、社交媒体、以及一切语义相似度比词面重叠重要的场景，它都赢。一篇文档只拿一个主题，这对长文内容是个限制。

本课为两者建立直觉，并指明给定语料该选哪个。

> You have 10,000 customer support tickets, 50,000 news articles, or 200,000 tweets. You need to know what the collection is about without reading it. You do not have labeled categories. You do not even know how many categories exist.
> Topic modeling answers that without supervision. Give it a corpus, get back a small set of coherent topics and, for each document, a distribution over those topics.
> Two algorithmic families dominate. LDA (2003) treats each document as a mixture of latent topics and each topic as a distribution over words. Inference is Bayesian. ... BERTopic (2020) encodes documents with BERT, reduces dimensionality with UMAP, clusters with HDBSCAN, and extracts topic words via class-based TF-IDF. It wins on short text, social media, and anything where semantic similarity matters more than word overlap. One document gets one topic, which is a limitation for long-form content.
> This lesson builds intuition for both and names which one to pick for a given corpus.

## The Concept · 概念

![LDA 混合模型 vs BERTopic 聚类](../assets/topic-modeling.svg)

**LDA 生成故事。** 每个主题是词上的一个分布。每篇文档是主题的一个混合。要生成文档中的一个词：先从文档的混合中抽一个主题，再从该主题的分布中抽一个词。推断反着来：给定观测到的词，推断每篇文档的主题分布和每个主题的词分布。数学由 collapsed Gibbs 采样或变分贝叶斯完成。

LDA 的关键输出：

- `doc_topic`：矩阵 `(n_docs, n_topics)`，每行和为 1（文档的主题混合）。
- `topic_word`：矩阵 `(n_topics, vocab_size)`，每行和为 1（主题的词分布）。

**BERTopic 管线。**

1. 用句子变换器（sentence transformer，如 `all-MiniLM-L6-v2`）编码每篇文档。384 维向量。
2. 用 UMAP 降到约 5 维。BERT 嵌入维度太高，没法直接聚类。
3. 用 HDBSCAN 聚类。基于密度，产出大小不一的簇和一个「离群」标签。
4. 对每个簇，在该簇的文档上计算基于类的 TF-IDF，抽取头部词。

输出是每篇文档一个主题（外加 -1 离群标签）。可选：通过 HDBSCAN 的概率向量得到软隶属。

```figure
topic-drift
```

> **LDA generative story.** Each topic is a distribution over words. Each document is a mixture of topics. To generate a word in a document, sample a topic from the document's mixture, then sample a word from that topic's distribution. Inference reverses this: given observed words, infer the topic distribution per document and the word distribution per topic. Collapsed Gibbs sampling or variational Bayes does the math.
> Key LDA output: ... **BERTopic pipeline.** 1. Encode each document with a sentence transformer (e.g., `all-MiniLM-L6-v2`). 384-dim vectors. 2. Reduce dimensionality with UMAP to ~5 dimensions. BERT embeddings are too high-dim for clustering. 3. Cluster with HDBSCAN. Density-based, produces variable-size clusters and an "outlier" label. 4. For each cluster, compute class-based TF-IDF over the cluster's documents to extract top words.
> Output is one topic per document (plus a -1 outlier label). Optionally, a soft membership via HDBSCAN's probability vector.

## Build It · 动手造

### Step 1: LDA via scikit-learn · 用 scikit-learn 跑 LDA

```python
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import numpy as np


def fit_lda(documents, n_topics=5, max_features=1000):
    cv = CountVectorizer(
        max_features=max_features,
        stop_words="english",
        min_df=2,
        max_df=0.9,
    )
    X = cv.fit_transform(documents)
    lda = LatentDirichletAllocation(
        n_components=n_topics,
        random_state=42,
        max_iter=50,
        learning_method="online",
    )
    doc_topic = lda.fit_transform(X)
    feature_names = cv.get_feature_names_out()
    return lda, cv, doc_topic, feature_names


def print_top_words(lda, feature_names, n_top=10):
    for idx, topic in enumerate(lda.components_):
        top_idx = np.argsort(-topic)[:n_top]
        words = [feature_names[i] for i in top_idx]
        print(f"topic {idx}: {' '.join(words)}")
```

注意：去除了停用词，min_df 和 max_df 过滤掉过稀有和过普遍的词，用 CountVectorizer（而不是 TfidfVectorizer），因为 LDA 吃的是原始计数。

> Notice: stopwords removed, min_df and max_df filter rare and ubiquitous terms, CountVectorizer (not TfidfVectorizer) because LDA expects raw counts.

### Step 2: BERTopic (production) · BERTopic（生产）

```python
from bertopic import BERTopic

topic_model = BERTopic(
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    min_topic_size=15,
    verbose=True,
)

topics, probs = topic_model.fit_transform(documents)
info = topic_model.get_topic_info()
print(info.head(20))
valid_topics = info[info["Topic"] != -1]["Topic"].tolist()
for topic_id in valid_topics[:5]:
    print(f"topic {topic_id}: {topic_model.get_topic(topic_id)[:10]}")
```

`Topic != -1` 的过滤丢掉了 BERTopic 的离群桶（HDBSCAN 聚不进去的文档）。`min_topic_size` 控制 HDBSCAN 的最小簇大小；BERTopic 库的默认是 10。本课为了这个规模把它显式设成 15。超过 10,000 篇文档的语料，调到 50 或 100。

> The filter on `Topic != -1` drops BERTopic's outlier bucket (documents HDBSCAN could not cluster). `min_topic_size` controls HDBSCAN's minimum cluster size; BERTopic's library default is 10. This example sets it to 15 explicitly for the lesson's scale. For corpora over 10,000 documents, increase to 50 or 100.

### Step 3: evaluation · 评估

两种方法都输出主题词。问题是这些词连起来是否成一个意思。

- **主题一致性（c_v）。** 在滑动窗口上下文上计算头部词对的 NPMI（normalized pointwise mutual information，归一化逐点互信息），把分数聚合成主题向量，再用余弦相似度比较这些向量。越高越好。用 `gensim.models.CoherenceModel` 加 `coherence="c_v"`。
- **主题多样性。** 所有主题的头部词中唯一词的占比。越高越好（主题之间不重叠）。
- **定性检查。** 去读每个主题的头部词。它们点名了一个真实存在的东西吗？人类判断仍是最后一道防线。

> Both methods output topic words. The question is whether those words cohere.
> - **Topic coherence (c_v).** Combines NPMI (normalized pointwise mutual information) of top-word pairs over sliding-window contexts, aggregates the scores into topic vectors, and compares those vectors via cosine similarity. Higher is better. Use `gensim.models.CoherenceModel` with `coherence="c_v"`.
> - **Topic diversity.** Fraction of unique words across all topics' top words. Higher is better (topics do not overlap).
> - **Qualitative inspection.** Read the top words of each topic. Do they name a real thing? Human judgment is still the last line of defense.

## When to pick which · 何时选哪个

| 场景 | 选择 |
|-----------|------|
| 短文本（推文、评论、标题） | BERTopic |
| 有主题混合的长文档 | LDA |
| 无 GPU / 算力有限 | LDA 或 NMF |
| 需要文档级多主题分布 | LDA |
| 用 LLM 给主题打标签 | BERTopic（直接支持） |
| 资源受限的边缘部署 | LDA |
| 追求最大语义一致性 | BERTopic |

最大的实践考量是文档长度。BERT 嵌入会截断；LDA 的计数对任意长度都有效。文档超过嵌入模型的上下文时，要么分块再聚合，要么用 LDA。

> The biggest practical consideration is document length. BERT embeddings truncate; LDA counts work on whatever length. For documents longer than the embedding model's context, either chunk + aggregate or use LDA.

## Use It · 实战用法

2026 年的技术栈：

- **BERTopic。** 短文本以及一切语义重要场景的默认。
- **`gensim.models.LdaModel`。** 生产级经典 LDA，成熟、久经战阵。
- **`sklearn.decomposition.LatentDirichletAllocation`。** 实验用的顺手 LDA。
- **NMF。** 非负矩阵分解。LDA 的快速替代，短文本上质量相当。
- **Top2Vec。** 与 BERTopic 设计类似。社区更小，但某些基准上表现好。
- **FASTopic。** 更新，在超大语料上比 BERTopic 快。
- **基于 LLM 的标注。** 随便跑一个聚类，然后提示模型给每个簇命名。

> The 2026 stack: ... **BERTopic.** Default for short text and anything where semantics matter. ... **NMF.** Non-negative matrix factorization. Fast alternative to LDA, comparable quality on short text. ... **LLM-based labeling.** Run any clustering, then prompt a model to name each cluster.

## Ship It · 交付

保存为 `outputs/skill-topic-picker.md`：

```markdown
---
name: topic-picker
description: Pick LDA or BERTopic for a corpus. Specify library, knobs, evaluation.
version: 1.0.0
phase: 5
lesson: 15
tags: [nlp, topic-modeling]
---

Given a corpus description (document count, avg length, domain, language, compute budget), output:

1. Algorithm. LDA / NMF / BERTopic / Top2Vec / FASTopic. One-sentence reason.
2. Configuration. Number of topics: `recommended = max(5, round(sqrt(n_docs)))`, clamped to 200 for corpora under 40,000 docs; permit >200 only when the corpus is genuinely large (>40k) and note the increased compute cost. `min_df` / `max_df` filters and embedding model for neural approaches also belong here.
3. Evaluation. Topic coherence (c_v) via `gensim.models.CoherenceModel`, topic diversity, and a 20-sample human read.
4. Failure mode to probe. For LDA, "junk topics" absorbing stopwords and frequent terms. For BERTopic, the -1 outlier cluster swallowing ambiguous documents.

Refuse BERTopic on documents longer than the embedding model's context window without a chunking strategy. Refuse LDA on very short text (tweets, reviews under 10 tokens) as coherence collapses. Flag any n_topics choice below 5 as likely wrong; flag >200 on corpora under 40k docs as likely over-splitting.
```

> Save as `outputs/skill-topic-picker.md`:

## Exercises · 练习

1. **简单。** 在 20 Newsgroups 数据集上拟合 5 个主题的 LDA。打印每个主题的前 10 个词。亲手给每个主题贴标签。算法找到真实类别了吗？
2. **中等。** 在同一个 20 Newsgroups 子集上拟合 BERTopic。对比两者找到的主题数、头部词和定性一致性。哪个更干净地浮现出真实类别？
3. **困难。** 在你的语料上为 LDA 和 BERTopic 都计算 c_v 一致性。各用 5、10、20、50 个主题跑一遍。画出一致性 vs 主题数的曲线。报告哪个方法在主题数变化下更稳定。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Topic（主题） | 语料在讲的一件事 | 词上的概率分布（LDA）或相似文档的簇（BERTopic）。 |
| Mixed membership（混合隶属） | 一篇文档属于多个主题 | LDA 给每篇文档分配一个在所有主题上的分布。 |
| UMAP | 降维 | 保持局部结构的流形学习；BERTopic 使用它。 |
| HDBSCAN | 密度聚类 | 找大小不一的簇；为离群点产出「噪声」标签（-1）。 |
| c_v coherence（c_v 一致性） | 主题质量指标 | 主题头部词在滑动窗口内的平均逐点互信息。 |

## Further Reading · 延伸阅读

- [Blei, Ng, Jordan (2003). Latent Dirichlet Allocation](https://www.jmlr.org/papers/volume3/blei03a/blei03a.pdf) —— LDA 论文。
- [Grootendorst (2022). BERTopic: Neural topic modeling with a class-based TF-IDF procedure](https://arxiv.org/abs/2203.05794) —— BERTopic 论文。
- [Röder, Both, Hinneburg (2015). Exploring the Space of Topic Coherence Measures](https://svn.aksw.org/papers/2015/WSDM_Topic_Evaluation/public.pdf) —— 提出 c_v 等指标的那篇论文。
- [BERTopic documentation](https://maartengr.github.io/BERTopic/) —— 生产参考。示例极佳。
