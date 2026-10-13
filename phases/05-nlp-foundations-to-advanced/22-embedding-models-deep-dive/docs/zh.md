# Embedding Models — The 2026 Deep Dive · 嵌入模型——2026 深度剖析

> Word2Vec 给你的是每个词一个向量。现代嵌入模型（embedding model）给你的是每个段落一个向量，跨语言，同时有稀疏、稠密、多向量三种视图，尺寸还能贴合你的索引。选错了，你的 RAG 检索到的就是错的东西。
>
> Word2Vec gave you a vector per word. Modern embedding models give you a vector per passage, cross-lingual, with sparse, dense, and multi-vector views, sized to fit your index. Pick wrong and your RAG retrieves the wrong thing.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 5 · 03 (Word2Vec), Phase 5 · 14 (Information Retrieval)
**Time:** ~60 minutes

## The Problem · 问题在哪

你的 RAG 系统有 40% 的时候检索到错误的段落。罪魁祸首很少是向量数据库，也很少是提示词——而是嵌入模型。

2026 年选嵌入，要在五个轴上做取舍：

1. **稠密 vs 稀疏 vs 多向量。** 每个段落一个向量，还是每个 token 一个向量，还是一个稀疏的加权词袋。
2. **语言覆盖。** 纯英文任务上，单语英文模型仍然赢；语料混杂时，多语言模型赢。
3. **上下文长度。** 512 tokens vs 8,192 vs 32,768——而真实有效容量往往只有标称上限的 60-70%。
4. **维度预算。** 3,072 个全精度浮点数 = 每向量 12 KB。到了 1 亿向量，存储费每月 $1,300。Matryoshka 截断能砍掉 4 倍。
5. **开源 vs 托管。** 开源权重意味着你掌控整个技术栈和数据；托管意味着你用控制权换「永远最新」。

本课把这些权衡一一命名，让你基于证据选择，而不是跟着上季度的流行度走。

> Your RAG system retrieves the wrong passage 40% of the time. The culprit is rarely the vector database or the prompt. It is the embedding model.... This lesson names the tradeoffs so you can pick on evidence, not on whatever was popular last quarter.

## The Concept · 概念

![稠密、稀疏、多向量三种嵌入](../assets/embedding-modes.svg)

**稠密嵌入（dense embedding）。** 每个段落一个向量（通常 384-3,072 维）。余弦相似度按语义接近程度给段落排序。代表：OpenAI `text-embedding-3-large`、BGE-M3 稠密模式、Voyage-3。默认之选。

**稀疏嵌入（sparse embedding）。** SPLADE 风格。Transformer 给词表里的每个 token 预测一个权重，然后把大部分置零。结果是一个大小为 |vocab| 的稀疏向量。能捕捉词汇匹配（像 BM25 那样），但词权重是学出来的。在关键词密集的查询上很强。

**多向量（multi-vector，后期交互 late interaction）。** ColBERTv2、Jina-ColBERT。每个 token 一个向量。打分用 MaxSim：对每个查询 token，找出最相似的文档 token，把分数求和。存储和打分都更贵，但在长查询和领域专用语料上赢。

**BGE-M3：三种一起给。** 单个模型同时输出稠密、稀疏、多向量三种表示。每种都可以独立建索引查询；分数用加权和融合。想要「一个 checkpoint 就有全部灵活性」时的 2026 年默认之选。

**Matryoshka 表示学习（Matryoshka Representation Learning）。** 训练时让向量的前 N 维本身就构成一个有用的独立嵌入。把 1,536 维向量截到 256 维，只付出约 1% 的精度，换来 6 倍的存储节省。支持者：OpenAI text-3、Cohere v4、Voyage-4、Jina v5、Gemini Embedding 2、Nomic v1.5+。

### The MTEB leaderboard tells a partial story · MTEB 榜单只讲了一半故事

Massive Text Embedding Benchmark——发布时（2022）是横跨 8 类任务类型的 56 个任务，MTEB v2 扩展到 100+ 任务。2026 年初，Gemini Embedding 2 在检索上登顶（67.71 MTEB-R）。Cohere embed-v4 领跑综合（65.2 MTEB）。BGE-M3 是开源多语言第一（63.0）。榜单必要但不充分——永远要在你自己的领域上跑基准。

> Massive Text Embedding Benchmark — 56 tasks across 8 task types at launch (2022), expanded to 100+ tasks in MTEB v2. In early 2026, Gemini Embedding 2 tops retrieval (67.71 MTEB-R). Cohere embed-v4 leads general (65.2 MTEB). BGE-M3 leads open-weight multilingual (63.0). The leaderboard is necessary but not sufficient — always benchmark on your domain.

### The three-tier pattern · 三层模式

| 使用场景 | 模式 |
|----------|---------|
| 快速粗筛 | 稠密 bi-encoder（BGE-M3、text-3-small） |
| 召回增强 | 稀疏（SPLADE、BGE-M3 sparse）+ RRF 融合 |
| top-50 精排 | 多向量（ColBERTv2）或 cross-encoder 重排器 |

大多数生产系统三层全用。

```figure
gx-matryoshka
```

> Fast first-pass: Dense bi-encoder... Recall boost: Sparse + RRF fuse... Precision on top-50: Multi-vector (ColBERTv2) or cross-encoder reranker.... Most production stacks use all three.

## Build It · 动手造

### Step 1: baseline — dense embeddings with Sentence-BERT · 基线——用 Sentence-BERT 做稠密嵌入

```python
from sentence_transformers import SentenceTransformer
import numpy as np

encoder = SentenceTransformer("BAAI/bge-small-en-v1.5")
corpus = [
    "The first iPhone launched in 2007.",
    "Apple released the iPod in 2001.",
    "Android is an operating system from Google.",
]
emb = encoder.encode(corpus, normalize_embeddings=True)

query = "When was the iPhone released?"
q_emb = encoder.encode([query], normalize_embeddings=True)[0]
scores = emb @ q_emb
print(sorted(enumerate(scores), key=lambda x: -x[1]))
```

`normalize_embeddings=True` 让点积等于余弦相似度。永远记得设它。

> `normalize_embeddings=True` makes the dot product equal cosine similarity. Always set it.

### Step 2: Matryoshka truncation · Matryoshka 截断

```python
def truncate(vectors, dim):
    out = vectors[:, :dim]
    return out / np.linalg.norm(out, axis=1, keepdims=True)

emb_256 = truncate(emb, 256)
emb_128 = truncate(emb, 128)
```

截断之后要重新归一化。Nomic v1.5、OpenAI text-3、Voyage-4 在训练时就保证了前几个层级截断无损。非 Matryoshka 模型（原版 Sentence-BERT）截断后性能会急剧退化。

> Re-normalize after truncation. Nomic v1.5, OpenAI text-3, and Voyage-4 are trained so this is lossless for the first few levels. Non-Matryoshka models (original Sentence-BERT) degrade sharply when truncated.

### Step 3: BGE-M3 multi-functionality · BGE-M3 的多功能性

```python
from FlagEmbedding import BGEM3FlagModel

model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)

output = model.encode(
    corpus,
    return_dense=True,
    return_sparse=True,
    return_colbert_vecs=True,
)
# output["dense_vecs"]:    (n_docs, 1024)
# output["lexical_weights"]: list of dict {token_id: weight}
# output["colbert_vecs"]:  list of (n_tokens, 1024) arrays
```

一次推理，三个索引。分数融合：

```python
dense_score = ... # cosine over dense_vecs
sparse_score = model.compute_lexical_matching_score(q_lex, d_lex)
colbert_score = model.colbert_score(q_col, d_col)
final = 0.4 * dense_score + 0.2 * sparse_score + 0.4 * colbert_score
```

权重要在你自己的领域上调。

> Three indexes, one inference call. Score fusion:... Tune the weights on your domain.

### Step 4: MTEB eval on a custom task · 在自定义任务上跑 MTEB 评估

```python
from mteb import MTEB

tasks = ["ArguAna", "SciFact", "NFCorpus"]
evaluation = MTEB(tasks=tasks)
results = evaluation.run(encoder, output_folder="./mteb-results")
```

在一个*有代表性*的子集上跑你的候选模型。不要只信榜单排名——你的领域才是关键。

> Run your candidate models on a *representative* subset. Do not trust leaderboard rank alone — your domain matters.

### Step 5: hand-rolled cosine from scratch · 从零手写余弦相似度

见 `code/main.py`。平均哈希技巧（Averaged Hashing Trick）嵌入（纯标准库）。打不过 Transformer 嵌入，但它展示了任务的形状：分词 → 向量 → 归一化 → 点积。

> See `code/main.py`. Averaged Hashing Trick embeddings (stdlib-only). Not competitive with transformer embeddings, but shows the shape: tokenize → vector → normalize → dot product.

## Pitfalls · 常见的坑

- **查询和文档用同一个模型。** 有些模型（Voyage、Jina-ColBERT）用非对称编码（asymmetric encoding）——查询和文档走不同的路径。永远要读模型卡（model card）。
- **漏掉前缀。** `bge-*` 系列模型需要在查询前拼上 `"Represent this sentence for searching relevant passages: "`。忘了会损失 3-5 个点的召回率。
- **Matryoshka 截得太狠。** 1,536 → 256 通常安全；1,536 → 64 不行。在你的评估集上验证。
- **上下文截断。** 大多数模型会悄悄截断超过最大长度的输入。长文档需要分块（见第 23 课）。
- **忽视延迟长尾。** MTEB 分数掩盖了 p99 延迟。一个 600M 模型可能比 335M 模型高 2 个点，但每个查询贵 3 倍。

> Some models (Voyage, Jina-ColBERT) use asymmetric encoding — query and document pass through different paths. Always check the model card.... `bge-*` models need `"Represent this sentence for searching relevant passages: "` prepended to queries. 3-5 point recall gap if you forget.... Most models silently truncate inputs over their max length. Long docs need chunking (see lesson 23).... MTEB scores hide p99 latency. A 600M model might beat a 335M model by 2 points but cost 3× more per query.

## Use It · 实战用法

2026 年的选型：

| 场景 | 选择 |
|-----------|------|
| 纯英文、要快、走 API | `text-embedding-3-large` 或 `voyage-3-large` |
| 开源权重、英文 | `BAAI/bge-large-en-v1.5` |
| 开源权重、多语言 | `BAAI/bge-m3` 或 `Qwen3-Embedding-8B` |
| 长上下文（32k+） | Voyage-3-large、Cohere embed-v4、Qwen3-Embedding-8B |
| 纯 CPU 部署 | Nomic Embed v2（137M 参数，MoE） |
| 存储受限 | Matryoshka 截断 + int8 量化 |
| 关键词密集的查询 | 加 SPLADE 稀疏，与稠密做 RRF 融合 |

2026 年的模式：从 BGE-M3 或 text-3-large 起步，用 MTEB 在你的领域上评估，如果某个领域专用模型赢超过 3 个点就换掉。

> 2026 pattern: start with BGE-M3 or text-3-large, evaluate on your domain with MTEB, swap if a domain-specific model wins by more than 3 points.

## Ship It · 交付

保存为 `outputs/skill-embedding-picker.md`：

```markdown
---
name: embedding-picker
description: Pick embedding model, dimension, and retrieval mode for a given corpus and deployment.
version: 1.0.0
phase: 5
lesson: 22
tags: [nlp, embeddings, retrieval]
---

Given a corpus (size, languages, domain, avg length), deployment target (cloud / edge / on-prem), latency budget, and storage budget, output:

1. Model. Named checkpoint or API. One-sentence reason.
2. Dimension. Full / Matryoshka-truncated / int8-quantized. Reason tied to storage budget.
3. Mode. Dense / sparse / multi-vector / hybrid. Reason.
4. Query prefix / template if required by the model card.
5. Evaluation plan. MTEB tasks relevant to domain + held-out domain eval with nDCG@10.

Refuse recommendations that truncate Matryoshka to <64 dims without domain validation. Refuse ColBERTv2 for corpora under 10k passages (overhead not justified). Flag long-document corpora (>8k tokens) routed to models with 512-token windows.
```

> Save as `outputs/skill-embedding-picker.md`.

## Exercises · 练习

1. **简单。** 用 `bge-small-en-v1.5` 以全维度（384）编码 100 个句子，再用 Matryoshka 128 维编码一次。在 10 个查询上测 MRR 降幅。
2. **中等。** 在来自你领域的 500 个段落上，比较 BGE-M3 的稠密、稀疏、colbert 三种模式。recall@10 上谁赢？RRF 融合能打败最好的单一模式吗？
3. **困难。** 在你领域的 top-2 任务上，对三个候选模型跑 MTEB。报告 MTEB 分数、100 查询批次的 p99 延迟、以及每百万查询成本（$/1M queries）。选出帕累托最优的那个。

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|-----------------------|
| Dense embedding（稠密嵌入） | 「那个向量」 | 每段文本一个固定尺寸的向量。用余弦相似度排序。 |
| Sparse embedding（稀疏嵌入） | 「学出来的 BM25」 | 词表里每个 token 一个权重；大部分为零；端到端训练。 |
| Multi-vector（多向量） | 「ColBERT 那一套」 | 每个 token 一个向量；MaxSim 打分；索引更大，召回更好。 |
| Matryoshka | 「俄罗斯套娃技巧」 | 向量的前 N 维自己就是一个合法的更小嵌入。 |
| MTEB | 「那个榜单」 | Massive Text Embedding Benchmark——发布时 56 个任务，v2 已到 100+。 |
| BEIR | 「检索基准」 | 18 个零样本检索任务；常被用来衡量跨领域鲁棒性。 |
| Asymmetric encoding（非对称编码） | 「查询 ≠ 文档路径」 | 模型对查询和文档使用不同的投影。 |

## Further Reading · 延伸阅读

- [Reimers, Gurevych (2019). Sentence-BERT](https://arxiv.org/abs/1908.10084) —— bi-encoder 原始论文。
- [Muennighoff et al. (2022). MTEB: Massive Text Embedding Benchmark](https://arxiv.org/abs/2210.07316) —— 榜单论文。
- [Chen et al. (2024). BGE-M3: Multi-lingual, Multi-functionality, Multi-granularity](https://arxiv.org/abs/2402.03216) —— 三模式统一的模型。
- [Kusupati et al. (2022). Matryoshka Representation Learning](https://arxiv.org/abs/2205.13147) —— 维度阶梯训练目标。
- [Santhanam et al. (2022). ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction](https://arxiv.org/abs/2112.01488) —— 后期交互的生产实践。
- [MTEB leaderboard on Hugging Face](https://huggingface.co/spaces/mteb/leaderboard) —— 实时排名。
