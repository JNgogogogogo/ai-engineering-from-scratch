# Information Retrieval and Search · 信息检索与搜索

> BM25 精准但脆弱。稠密检索撒大网但漏关键词。混合检索是 2026 年的默认。其余一切都是调参。
> BM25 is precise but brittle. Dense casts a wide net but misses keywords. Hybrid is the 2026 default. Everything else is tuning.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 02 (BoW + TF-IDF), Phase 5 · 04 (GloVe, FastText, Subword)
**Time:** ~75 minutes

## The Problem · 问题在哪

用户输入 "what happens if someone lies to get money"，期望找到真正覆盖这种情况的那条法条："Section 420 IPC。" 关键词搜索完全找不到（没有共享词汇）。语义搜索也找不到——如果嵌入模型没在法律文本上训练过。真实的搜索必须两者都能处理。

IR（information retrieval，信息检索）是每个 RAG 系统、每个搜索框、每个文档站的模糊查找底下那条管线。2026 年在生产环境验证过的架构不是单一方法，而是一条互补方法的链，每一环接住前一环的失败。

本课逐件构建，并指名每一件接住哪些失败。

> The user types "what happens if someone lies to get money" and expects to find the statute that actually covers that: "Section 420 IPC." A keyword search misses it entirely (no shared vocabulary). A semantic search misses it if the embeddings were not trained on legal text. Real search has to handle both.
> IR is the pipeline under every RAG system, every search bar, every docs site's fuzzy lookup. The 2026 architecture that works in production is not a single method. It is a chain of complementary methods, each catching the failures of the one before.
> This lesson builds each piece and names which failures each catches.

## The Concept · 概念

![混合检索：BM25 + 稠密 + RRF + 交叉编码器重排](../assets/retrieval.svg)

四层。按需取用。

1. **稀疏检索（BM25）。** 快、精确匹配上精准、语义上一塌糊涂。跑在倒排索引上。百万文档每查询 10 毫秒以内。法条编号、产品编码、错误信息、命名实体，靠它拿对。
2. **稠密检索（Dense retrieval）。** 把查询和文档编码成向量。最近邻搜索。捕捉意译和语义相似。漏掉只差一个字符的精确关键词匹配。用 FAISS 或向量数据库每查询 50-200 毫秒。
3. **融合（Fusion）。** 合并稀疏和稠密两个排序列表。倒数排名融合（Reciprocal Rank Fusion, RRF）是省事的默认：它无视原始分数（各自量纲不同），只用排名位置。当你知道某个信号在你的领域占主导时，加权融合也是一个选项。
4. **交叉编码器重排（Cross-encoder rerank）。** 从融合结果取前 30。跑一个交叉编码器（查询 + 文档一起送入，逐对打分）。保留前 5。交叉编码器每对比双编码器慢，但准确得多。只在前 30 上跑它，把成本摊薄。

三路检索（BM25 + 稠密 + SPLADE 这类学习型稀疏）在 2026 年的基准上胜过两路，但需要学习型稀疏索引的基础设施。对多数团队来说，两路加交叉编码器重排就是甜点位。

> Four layers. Pick the ones you need.
> 1. **Sparse retrieval (BM25).** Fast, precise on exact matches, terrible on semantics. Run over an inverted index. Sub-10ms per query on millions of documents. Gets you statute references, product codes, error messages, named entities right.
> 2. **Dense retrieval.** Encode query and documents into vectors. Nearest neighbor search. Captures paraphrases and semantic similarity. Misses exact keyword matches that differ by one character. 50-200ms per query with FAISS or a vector DB.
> 3. **Fusion.** Merge the ranked lists from sparse and dense. Reciprocal Rank Fusion (RRF) is the easy default because it ignores raw scores (which live in different scales) and only uses rank positions. Weighted fusion is an option when you know one signal dominates for your domain.
> 4. **Cross-encoder rerank.** Take the top-30 from fusion. Run a cross-encoder (query + document together, scoring each pair). Keep the top-5. Cross-encoders are slower per pair than bi-encoders but far more accurate. You amortize by only running them on the top-30.
> Three-way retrieval (BM25 + dense + learned-sparse like SPLADE) outperforms two-way in 2026 benchmarks but needs infrastructure for learned-sparse indexes. For most teams, two-way plus cross-encoder rerank is the sweet spot.

```figure
gx-hybrid-retrieval
```

## Build It · 动手造

### Step 1: BM25 from scratch · 从零实现 BM25

```python
import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text):
    return TOKEN_RE.findall(text.lower())


class BM25:
    def __init__(self, corpus, k1=1.5, b=0.75):
        if not corpus:
            raise ValueError("corpus must not be empty")
        self.corpus = [tokenize(d) for d in corpus]
        self.k1 = k1
        self.b = b
        self.n_docs = len(self.corpus)
        self.avg_dl = sum(len(d) for d in self.corpus) / self.n_docs
        self.df = Counter()
        for doc in self.corpus:
            for term in set(doc):
                self.df[term] += 1

    def idf(self, term):
        n = self.df.get(term, 0)
        return math.log(1 + (self.n_docs - n + 0.5) / (n + 0.5))

    def score(self, query, doc_idx):
        q_tokens = tokenize(query)
        doc = self.corpus[doc_idx]
        dl = len(doc)
        freq = Counter(doc)
        score = 0.0
        for term in q_tokens:
            f = freq.get(term, 0)
            if f == 0:
                continue
            numerator = f * (self.k1 + 1)
            denominator = f + self.k1 * (1 - self.b + self.b * dl / self.avg_dl)
            score += self.idf(term) * numerator / denominator
        return score

    def rank(self, query, top_k=10):
        scored = [(self.score(query, i), i) for i in range(self.n_docs)]
        scored.sort(reverse=True)
        return scored[:top_k]
```

两个值得认识的参数。`k1=1.5` 控制词频饱和；越大，词的重复出现权重越高。`b=0.75` 控制长度归一化；0 表示无视文档长度，1 表示完全归一化。默认值来自 Robertson 原始论文的推荐，几乎不用调。

> Two parameters worth knowing. `k1=1.5` controls term-frequency saturation; higher means more weight on term repetition. `b=0.75` controls length normalization; 0 ignores document length, 1 fully normalizes. The defaults are Robertson's recommendations from the original paper and rarely need tuning.

### Step 2: dense retrieval with a bi-encoder · 用双编码器做稠密检索

```python
from sentence_transformers import SentenceTransformer
import numpy as np


def build_dense_index(corpus, model_id="sentence-transformers/all-MiniLM-L6-v2"):
    encoder = SentenceTransformer(model_id)
    embeddings = encoder.encode(corpus, normalize_embeddings=True)
    return encoder, embeddings


def dense_search(encoder, embeddings, query, top_k=10):
    q_emb = encoder.encode([query], normalize_embeddings=True)
    sims = (embeddings @ q_emb.T).flatten()
    order = np.argsort(-sims)[:top_k]
    return [(float(sims[i]), int(i)) for i in order]
```

对嵌入做 L2 归一化，点积才等于余弦相似度。`all-MiniLM-L6-v2` 是 384 维，快，对多数英语检索足够强。多语言场景用 `paraphrase-multilingual-MiniLM-L12-v2`。追最高精度用 `bge-large-en-v1.5` 或 `e5-large-v2`。

> L2-normalize embeddings so dot product equals cosine. `all-MiniLM-L6-v2` is 384-dim, fast, and strong enough for most English retrieval. For multilingual work, use `paraphrase-multilingual-MiniLM-L12-v2`. For top accuracy, `bge-large-en-v1.5` or `e5-large-v2`.

### Step 3: Reciprocal Rank Fusion · 倒数排名融合（RRF）

```python
def reciprocal_rank_fusion(rankings, k=60):
    scores = {}
    for ranking in rankings:
        for rank, (_, doc_idx) in enumerate(ranking):
            scores[doc_idx] = scores.get(doc_idx, 0.0) + 1.0 / (k + rank + 1)
    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [(score, doc_idx) for doc_idx, score in fused]
```

`k=60` 这个常数来自 RRF 原始论文。`k` 越大，排名差异的贡献越平；`k` 越小，头部排名越占主导。60 是论文发表的默认值，几乎不用调。

> The `k=60` constant comes from the original RRF paper. Higher `k` flattens the contribution of rank differences; lower `k` makes top ranks dominate. 60 is the published default and rarely needs tuning.

### Step 4: hybrid search + rerank · 混合搜索 + 重排

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def hybrid_search(query, bm25, encoder, dense_embeddings, corpus, top_k=5, pool_size=30, reranker=reranker):
    sparse_ranking = bm25.rank(query, top_k=pool_size)
    dense_ranking = dense_search(encoder, dense_embeddings, query, top_k=pool_size)
    fused = reciprocal_rank_fusion([sparse_ranking, dense_ranking])[:pool_size]

    pairs = [(query, corpus[doc_idx]) for _, doc_idx in fused]
    scores = reranker.predict(pairs)
    reranked = sorted(zip(scores, [doc_idx for _, doc_idx in fused]), reverse=True)
    return reranked[:top_k]
```

三个阶段组合起来。BM25 找词面匹配。稠密找语义匹配。RRF 在不需要分数校准的情况下合并两个排序。交叉编码器把查询-文档成对送入、给前 30 重新打分，捕捉双编码器漏掉的细粒度相关性。保留前 5。

> Three stages composed. BM25 finds lexical matches. Dense finds semantic matches. RRF merges the two rankings without needing score calibration. Cross-encoder rescores the top-30 using query-document pairs together, which captures fine-grained relevance the bi-encoder missed. Keep top-5.

### Step 5: evaluation · 评估

| 指标 | 含义 |
|--------|---------|
| Recall@k | 在正确文档存在的那些查询里，它有多大比例出现在前 k？ |
| MRR（Mean Reciprocal Rank，平均倒数排名） | 第一个相关文档的 1/rank 的平均。 |
| nDCG@k | 考虑相关性的分级，而不只是相关/不相关的二值。 |

对 RAG 而言，检索器的 **Recall@k** 是最重要的数字。正确的段落不在检索集合里，阅读器就无能为力。

调试技巧：对失败的查询，diff 稀疏和稠密两个排序。如果一个找到了正确文档而另一个没有，那你要么碰上了词汇不匹配（修法：补上缺的那一半），要么碰上了语义歧义（修法：更好的嵌入，或加一个重排器）。

> For RAG specifically, **Recall@k** of the retriever is the most important number. Your reader cannot answer if the right passage is not in the retrieved set.
> Debugging tip: for failing queries, diff the sparse and dense rankings. If one finds the right document and the other does not, you have a vocabulary mismatch (fix: add the missing half) or a semantic ambiguity (fix: better embeddings or a reranker).

## Use It · 实战用法

2026 年的技术栈：

| 规模 | 技术栈 |
|-------|-------|
| 1k-10 万文档 | 内存内 BM25 + `all-MiniLM-L6-v2` 嵌入 + RRF。不需要独立数据库。 |
| 10 万-1000 万文档 | FAISS 或 pgvector 做稠密 + Elasticsearch / OpenSearch 做 BM25。并行跑。 |
| 1000 万+ 文档 | 支持混合检索的 Qdrant / Weaviate / Vespa / Milvus。再叠交叉编码器对前 30 重排。 |
| 最高质量前沿 | 三路（BM25 + 稠密 + SPLADE）+ ColBERT 后期交互（late-interaction）重排 |

无论选什么，给评估留预算。先基准测试检索召回，再测端到端 RAG 准确率。检索器漏掉的，阅读器救不回来。

> The 2026 stack: ... Whatever you pick, budget for evaluation. Benchmark retrieval recall before benchmarking end-to-end RAG accuracy. A reader cannot fix what the retriever missed.

### The hard-won lessons from 2026 production RAG · 2026 年生产 RAG 的血泪教训

- **80% 的 RAG 失败要追溯到摄取与分块（chunking），而不是模型。** 团队花几周换 LLM、调提示词，而检索每三次查询就悄悄返回一次错误上下文。先修分块。
- **分块策略比分块大小更重要。** 固定长度切分会切碎表格、代码和嵌套标题。句子感知切分是默认；对技术文档和产品手册，语义切分或基于 LLM 的切分有回报。
- **父文档模式（Parent-doc pattern）。** 检索小的「子」chunk 换精度。当同一父章节的多个子块同时出现，换入父块以保留上下文。这一招不重训就能稳定提升答案质量。
- **k_rerank=3 通常最优。** 每多一个 chunk 都增加 token 成本和生成延迟，却不提升答案质量。如果你那里 k=8 仍然好于 k=3，说明重排器表现不佳。
- **HyDE / 查询扩展。** 从查询生成一个假设性答案，用它做嵌入、去检索。弥合短问题与长文档之间的措辞鸿沟。零训练的精度提升。
- **上下文预算低于 8K token。** 在该限制上持续撞线，说明重排器阈值太松。
- **一切都要版本化。** 提示词、分块规则、嵌入模型、重排器。任何漂移都会悄悄毁掉答案质量。在忠实度、上下文精确率、未答率上设 CI 门禁，在用户看到之前拦住回归。
- **三路检索（BM25 + 稠密 + SPLADE 这类学习型稀疏）胜过两路**——在 2026 年的基准上，尤其对专有名词和语义混在一起的查询。基础设施支持 SPLADE 索引时就上。

据 2026 年的行业测量，合理的检索设计能把幻觉减少 70-90%。RAG 的大多数性能提升来自更好的检索，而不是模型微调。

> **80% of RAG failures trace to ingestion and chunking, not the model.** Teams spend weeks swapping LLMs and tuning prompts while the retrieval quietly returns the wrong context every third query. Fix chunking first. ... **Chunking strategy matters more than chunk size.** Fixed-size splits break tables, code, and nested headers. ... **Parent-doc pattern.** Retrieve small "child" chunks for precision. When multiple children from the same parent section appear, swap in the parent block to preserve context. This consistently lifts answer quality without retraining. ... Proper retrieval design reduces hallucinations by 70-90% according to 2026 industry measurements. Most RAG performance gains come from better retrieval, not model fine-tuning.

## Ship It · 交付

保存为 `outputs/skill-retrieval-picker.md`：

```markdown
---
name: retrieval-picker
description: Pick a retrieval stack for a given corpus and query pattern.
version: 1.0.0
phase: 5
lesson: 14
tags: [nlp, retrieval, rag, search]
---

Given requirements (corpus size, query pattern, latency budget, quality bar, infra constraints), output:

1. Stack. BM25 only, dense only, hybrid (BM25 + dense + RRF), hybrid + cross-encoder rerank, or three-way (BM25 + dense + learned-sparse).
2. Dense encoder. Name the specific model. Match to language(s), domain, and context length.
3. Reranker. Name the specific cross-encoder model if used. Flag that rerank adds 30-100ms latency on top-30.
4. Evaluation plan. Recall@10 is the primary retriever metric. MRR for multi-answer. Baseline first, incremental improvements measured against it.

Refuse to recommend dense-only for corpora with named entities, error codes, or product SKUs unless the user has evidence dense handles exact matches. Refuse to skip reranking for high-stakes retrieval (legal, medical) where the final top-5 decides the user's answer.
```

> Save as `outputs/skill-retrieval-picker.md`:

## Exercises · 练习

1. **简单。** 在一个 500 文档语料上实现上面的 `hybrid_search`。测 20 个查询。对比 BM25 单独、稠密单独和混合三者的 recall@5。
2. **中等。** 加上 MRR 计算。对每个已知正确文档的测试查询，找出正确文档在 BM25、稠密和混合排序中的排名。报告各自的 MRR。
3. **困难。** 用 MultipleNegativesRankingLoss（Sentence Transformers）在你的领域上微调一个稠密编码器。用 500 个查询-文档对搭一个训练集。对比微调前后的召回。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| BM25 | 关键词搜索 | Okapi BM25。按词频、IDF 和文档长度给文档打分。 |
| Dense retrieval（稠密检索） | 向量搜索 | 把查询 + 文档编码成向量，找最近邻。 |
| Bi-encoder（双编码器） | 嵌入模型 | 分别编码查询和文档。查询时快。 |
| Cross-encoder（交叉编码器） | 重排器模型 | 把查询 + 文档一起编码。慢但准。 |
| RRF | 排名融合 | 把两个排序按 `1/(k + rank)` 求和合并。 |
| Recall@k | 检索指标 | 相关文档出现在前 k 的查询比例。 |

## Further Reading · 延伸阅读

- [Robertson and Zaragoza (2009). The Probabilistic Relevance Framework: BM25 and Beyond](https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf) —— BM25 的权威论述。
- [Karpukhin et al. (2020). Dense Passage Retrieval for Open-Domain QA](https://arxiv.org/abs/2004.04906) —— DPR，公认的双编码器。
- [Formal et al. (2021). SPLADE: Sparse Lexical and Expansion Model](https://arxiv.org/abs/2107.05720) —— 追平稠密检索的学习型稀疏检索器。
- [Cormack, Clarke, Büttcher (2009). Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) —— RRF 论文。
- [Khattab and Zaharia (2020). ColBERT: Efficient and Effective Passage Search](https://arxiv.org/abs/2004.12832) —— 后期交互（late-interaction）检索。
