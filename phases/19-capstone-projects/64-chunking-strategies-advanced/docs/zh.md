# Chunking Strategies, Compared · 分块策略对比

分块（chunking）决定了你的检索器最好能捞出什么。边界切错了，下游再好的嵌入模型、重排序器（reranker）、LLM 都救不回来。

> Chunking decides what your retriever can ever surface. Get the boundaries wrong and no embedding model, no reranker, no LLM can repair the damage downstream.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 11 lessons 04 (embeddings), 06 (RAG), 07 (advanced RAG); Phase 19 Track B foundations (lessons 20-29)
**Time:** ~90 minutes

## Learning Objectives · 学习目标

- 从零实现五种分块策略：固定窗口（fixed-window）、按句（sentence）、递归切分（recursive-split）、语义聚类（semantic clustering）、结构化 markdown 标题（structural markdown headers）。
- 在带黄金标注答案区间（gold-labeled answer span）的测试语料上测量 recall@k，并解释为什么一种策略在散文上赢、另一种在技术文档上赢。
- 读懂块长分布，识别每种策略引入的失败模式：孤儿句、符号中间切断、只有标题的块、语义漂移。
- 不跑基准，通过检查三个属性——文档类型、平均段落长度、格式是否带显式结构——为新语料选出默认策略。

> Implement five chunking strategies from scratch: fixed-window, sentence, recursive-split, semantic clustering, and structural markdown headers.
> Measure recall@k on a fixture corpus with gold-labeled answer spans and explain why one strategy wins on prose and a different strategy wins on technical documents.
> Read a chunk-length distribution and recognize the failure modes each strategy injects: orphan sentences, mid-symbol cuts, header-only chunks, semantic drift.
> Pick a default for a new corpus without running the benchmark by inspecting three properties: document type, average paragraph length, and whether the format carries explicit structure.

## The Problem · 问题在哪

每个 RAG 管线的第一步，都是把源文档切成小块：要小到嵌入模型装得下，又要大到每块携带一个自包含的想法。在哪里切不是一个超参数，它是检索器所能返回内容的上限。

一个问「预算中止阈值（abort threshold）长什么样」的查询，只有在持有中止阈值的那个块可被检索到时才可能成功。如果固定窗口切分器把阈值数值从周围上下文里切走了，嵌入会漂到另一个簇，BM25 分数下跌，重排序器看到的是噪声，LLM 生成的答案就是错的。2024 年的论文 "LongRAG: Enhancing Retrieval-Augmented Generation with Long-context LLMs" 测得：仅分块选择一项，就能让检索召回产生 35 个百分点的绝对波动。2025 年关于上下文块标题（contextual chunk headers）的后续工作缩小了差距，但没有消除它。

本课把五种策略并排造出来，在带黄金标注答案区间的测试语料上运行，让你亲自读那些召回数字。

> Every RAG pipeline starts by cutting source documents into pieces small enough that an embedding model fits them and large enough that each piece carries a self-contained idea. The choice of where to cut is not a hyperparameter. It is the upper bound on what the retriever can ever return.
> The 2024 paper "LongRAG: Enhancing Retrieval-Augmented Generation with Long-context LLMs" measured a 35 percent absolute swing in retrieval recall purely from the chunking choice. The follow-up work in 2025 on contextual chunk headers narrowed the gap but did not close it.
> This lesson builds five strategies side by side, runs them against a fixture corpus with gold-labeled answer spans, and lets you read the recall numbers yourself.

## The Concept · 概念

```mermaid
flowchart LR
  Doc[Source Document] --> S1[Fixed Window]
  Doc --> S2[Sentence]
  Doc --> S3[Recursive Split]
  Doc --> S4[Semantic Cluster]
  Doc --> S5[Structural Markdown]
  S1 --> Chunks1[Chunks]
  S2 --> Chunks2[Chunks]
  S3 --> Chunks3[Chunks]
  S4 --> Chunks4[Chunks]
  S5 --> Chunks5[Chunks]
  Chunks1 --> Index[Embedding Index]
  Chunks2 --> Index
  Chunks3 --> Index
  Chunks4 --> Index
  Chunks5 --> Index
  Index --> Eval[Recall@k vs Gold Spans]
```

### Fixed-window · 固定窗口

蛮力基线。每 N 个字符切一刀。可选重叠（overlap），让在位置 N 被切断的句子在从 N - overlap 开始的块里保持完整。快、确定性强、边界处理糟糕。把它当对照组，不要当默认。

> The brute-force baseline. Cut every N characters. ... Fast, deterministic, terrible at boundaries. Use it as a control, not a default.

### Sentence · 按句切分

用正则或一个简单状态机在句子边界切分。把一句或多句打包进一个块，直到达到目标字符预算。不会在词中间切，但仍会在段落和节中间切。许多早期 RAG 管线的默认选择，对没有其他结构的散文是合理的。

> Split on sentence boundaries with a regex or a simple state machine. Pack one or more sentences into a chunk up to a target character budget. Stops cutting mid-word. Still cuts mid-paragraph and mid-section. The default in many early RAG pipelines and a reasonable choice for prose with no other structure.

### Recursive split · 递归切分

2023 年前后各家库推广开来的层级策略。先尝试用最强分隔符切（双换行、段落），退而求其次用次强的（单换行），再退到句子，最后退到字符。块装进预算时递归终止。对结构不一致的文档很强，因为它按区域自适应。

> The hierarchy strategy popularized by 2023-era libraries. Try to split on the strongest separator first (double newline, paragraph), fall back to the next (single newline), then to sentences, then to characters. The recursion terminates when the chunk fits the budget. Strong on documents that have inconsistent structure because it adapts per region.

### Semantic clustering · 语义聚类

给每个句子做嵌入。把共享同一主题质心（centroid）的连续句子聚成簇。当滚动相似度跌破阈值时就切。边界反映语义，而不是字符。构建更慢、依赖嵌入模型，但对段内切换话题的文档有韧性。

> Embed every sentence. Cluster contiguous sentences that share a topic centroid. Cut whenever the running similarity to the centroid drops below a threshold. The boundaries reflect meaning, not characters. ... but resilient against documents that switch topics inside a paragraph.

### Structural markdown headers · 结构化 markdown 标题

对自带显式结构的文档（markdown、reStructuredText、RFC 式编号小节），在标题边界切。每个块成为「标题 + 它下面直到下一个同级或更高级标题之间的全部内容」。每主题块最小，但只在语料格式良好时可用。

> For documents that carry explicit structure (markdown, reStructuredText, RFC-style numbered sections), cut at heading boundaries. Each chunk becomes the heading plus everything underneath it down to the next heading at the same or higher level. Smallest chunks per topic, but only available when the corpus is well-formed.

### How recall@k measures the boundary choice · recall@k 如何度量边界选择

一条黄金标注查询携带答案区间在源文档中的精确字符偏移。分块之后你问：检索器返回的 top-k 块中是否有任何一个与黄金区间重叠？有，该查询的 recall@k 记 1；没有，记 0。在查询集上取平均。对每种策略跑同一套评测，分数的散布就会告诉你：哪种边界策略能活在你手上这个语料里。

> A gold-labeled query carries the exact character offsets of the answer span inside the source document. After chunking, you ask: does any of the top-k chunks the retriever returned overlap the gold span? If yes, recall@k for that query is 1. If no, it is 0. Average across the query set. Run the same evaluation for each strategy and the spread shows you which boundary policy survives the corpus you have.

```figure
ci-chunk-boundaries
```

## Build It · 动手造

`code/main.py` 实现了：

- `fixed_window(text, size, overlap)` —— 基线。
- `sentence_chunks(text, target)` —— 简单的按句打包器。
- `recursive_split(text, separators, target)` —— 层级递归。
- `semantic_chunks(text, similarity_threshold)` —— 在确定性 mock 嵌入之上做基于质心的聚类。
- `structural_markdown(text)` —— 感知标题的切分器。
- `mock_embed(text, dim)` —— 基于哈希的嵌入，让整个循环离线可跑。
- `DenseIndex` —— 与第 19 章 Track B 混合检索课相同的形状。
- `eval_recall(strategy, corpus, queries, k)` —— 对比循环。
- 一个 `main()`：在测试语料上跑每一种策略，并打印 recall@k 表。

运行：

```bash
python3 code/main.py
```

输出是一张小表：每种策略一行，每个 k 一列。按句策略在结构化测试集上输。结构化 markdown 在 markdown 测试集上赢。递归切分在混合测试集上守得住，因为递归会自适应。语义聚类在没有任何有用结构线索的散文测试集上赢。

> The output is a small table with one row per strategy and one column per k. Sentence loses on the structured fixture. Structural-markdown wins on the markdown fixture. Recursive holds its own on the mixed fixture because the recursion adapts. Semantic clustering wins on the prose fixture where there are no useful structural cues.

## Failure modes the table will not hide · 表格藏不住的失败模式

**孤儿句。** 按句打包产出的块会漏掉主题句。嵌入随之指向错误的簇。

**符号中间切断。** 固定窗口在代码或 YAML 里会把一个标识符劈成两半。两半各自嵌入后都是噪声。

**只有标题的块。** 结构化 markdown 会产出只有 `## Title` 的块。把它们过滤掉，或者把下一个块的第一段挂上来。

**语义漂移。** 语料整体都在同一话题上时，语义聚类会切得太少。一个 5000 字符的块把许多具体答案塞进一个发散的嵌入。把语义切分与硬字符上限组合使用。

**过期嵌入。** 语义聚类依赖嵌入模型。换了模型，就换了块。把分块模型与检索模型分开锁定版本，或者干脆一起重建索引。

> **Orphan sentences.** Sentence packing produces chunks that miss the topic sentence. The embedding then points at the wrong cluster.
> **Mid-symbol cuts.** Fixed-window inside code or YAML will split an identifier in half. The two halves embed to noise.
> **Header-only chunks.** Structural markdown emits a chunk containing nothing but `## Title`. Filter those out or attach the next chunk's first paragraph.
> **Semantic drift.** Semantic clustering under-cuts when the corpus is uniformly on topic. A 5000-character chunk packs many specific answers into one diffuse embedding. Combine semantic with a hard character cap.
> **Stale embeddings.** Semantic clustering uses an embedding model. If you change the model, you also change the chunks. Pin the chunk model separately from the retrieval model or rebuild the index together.

## Choosing a default without running the benchmark · 不跑基准也能选默认

三个属性决定新语料的默认分块器。

| 属性 | 取值 | 默认策略 |
|------|------|----------|
| 文档类型 | 无结构的散文 | 递归切分，target 800 |
| 文档类型 | Markdown / RFC / API 文档 | 结构化 markdown |
| 文档类型 | 代码 | AST 感知（超出本课范围；见 Phase 19 lesson 02） |
| 段落长度 | 长、单一主题 | 按句切分，target 500 |
| 段落长度 | 短、话题混杂 | 语义聚类，threshold 0.6 |

拿不准就选递归切分。它是最强的单策略基线。

> Three properties decide the default chunker for a new corpus.
> When in doubt, pick recursive split. It is the strongest single-strategy baseline.

## Use It · 实战用法

生产模式：

- 上线新管线之前先跑评测；不要相信你的库默认带的策略。
- 每次更换嵌入模型或语料配比都要重跑评测；赢家取决于语料。
- 把策略名持久化进每个块的元数据，方便日后归因回退。

> Production patterns:
> - Run the eval before you ship a new pipeline; do not trust the strategy your library defaults to.
> - Re-run the eval whenever you change the embedding model or the corpus mix; the winner is corpus-dependent.
> - Persist the strategy name in each chunk's metadata so you can attribute regressions later.

## Ship It · 交付

第 69 课的 Track F 端到端 RAG 系统，把这里选出的分块器用作它的第一阶段。第 68 课的评测框架读取 recall@k，用的正是本课 `eval_recall` 返回的同一形状。选出在你语料上赢的策略，向前传递。

> The Track F end-to-end RAG system in lesson 69 uses the chunker selected here as its first stage. The eval harness in lesson 68 reads recall@k from the same shape that `eval_recall` returns in this lesson. Pick the strategy that wins on your corpus and feed it forward.

## Exercises · 练习

1. 加第六种策略：token 窗口，用 `tiktoken` 代替字符计数。在同一测试集上与固定窗口对比。

2. 往散文测试集里注入 30% 的代码块。重跑表格。解释为什么除结构化 markdown 外，所有策略都掉了召回。

3. 把确定性嵌入换成你项目真实供应商的嵌入。测量语义聚类的召回差值。报告策略之间的分差是变宽还是变窄。

4. 给每个块加一个 `summary` 字段：一句话的质心描述。把 summary 附加到块体后面重跑评测。测量召回提升。

## Key Terms · 术语表

| 术语 | 人们口头说 | 实际含义 |
|------|-----------|----------|
| Recall@k | 「我们捞到对的块了吗？」 | top-k 块中至少一个与黄金答案区间重叠的查询比例 |
| Chunk overlap（块重叠） | 「滑动窗口」 | 把上一块的最后 N 个字符重新包含进下一块 |
| Structural splitter（结构切分器） | 「感知标题的块」 | 在 H1/H2/H3 边界切；标题文本属于块的一部分 |
| Semantic chunker（语义分块器） | 「感知话题的块」 | 嵌入句子，按质心相似度聚类，漂移即切 |
| Centroid drift（质心漂移） | 「话题切换」 | 滚动均值与下一句之间的余弦相似度跌破阈值 |

## Further Reading · 延伸阅读

- [LongRAG: Enhancing Retrieval-Augmented Generation with Long-context LLMs (arXiv 2406.15319)](https://arxiv.org/abs/2406.15319)
- [Anthropic, Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
- [LlamaIndex, Chunking strategies for production RAG](https://docs.llamaindex.ai/en/stable/optimizing/production_rag/)
- Phase 11 lesson 06 —— RAG 基础
- Phase 11 lesson 07 —— 高级 RAG
- Phase 19 lesson 65 —— 对这里产出的块做排序的混合检索
- Phase 19 lesson 68 —— 在生产中给策略选择打分的评测框架
