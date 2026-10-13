# Chunking Strategies for RAG · RAG 分块策略

> 分块（chunking）配置对检索质量的影响，不亚于嵌入模型的选择（Vectara NAACL 2025）。分块做错了，再多重排也救不了你。
>
> Chunking configuration influences retrieval quality as much as the choice of embedding model (Vectara NAACL 2025). Get chunking wrong and no amount of reranking saves you.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 14 (Information Retrieval), Phase 5 · 22 (Embedding Models)
**Time:** ~60 minutes

## The Problem · 问题在哪

你把一份 50 页的合同放进 RAG 系统。用户问：「终止条款是什么？」检索器返回了封面页。为什么？因为模型是在 512-token 的块上训练的，而终止条款埋在第 20 页，还跨了页断开，没有任何局部关键词把它和查询关联起来。

解法不是「买一个更好的嵌入模型」。解法是分块（chunking）。多大？要不要重叠（overlap）？在哪里切？要不要附带周围上下文？

2026 年 2 月的基准给出了出人意料的结果：

- Vectara 2026 年的研究：递归 512-token 分块以 69% → 54% 的准确率击败语义分块。
- SPLADE + Mistral-8B 在 Natural Questions 上：重叠没有带来任何可测量的收益。
- 上下文悬崖（context cliff）：上下文在 2,500 tokens 附近时，回答质量急剧下降。

「显而易见」的答案（语义分块、20% 重叠、1000 tokens）常常是错的。本课帮你建立对六种策略的直觉，并告诉你什么时候该用哪一种。

> You put a 50-page contract into a RAG system. User asks: "What is the termination clause?" The retriever returns the cover page. Why? Because the model was trained on 512-token chunks and the termination clause sits 20 pages in, split across a page break, with no local keywords tying it to the query.... The fix is not "buy a better embedding model." The fix is chunking.... The "obvious" answer (semantic chunking, 20% overlap, 1000 tokens) is often wrong. This lesson builds intuition for six strategies and tells you when to reach for which.

## The Concept · 概念

![六种分块策略在同一段落上的可视化](../assets/chunking.svg)

**固定分块（fixed chunking）。** 每 N 个字符或 token 切一刀。最简单的基线。会把句子拦腰切断。压缩率好，连贯性差。

**递归分块（recursive）。** LangChain 的 `RecursiveCharacterTextSplitter`。先试按 `\n\n` 切，再试 `\n`，再 `.`，再空格。回退得很干净。2026 年的默认选择。

**语义分块（semantic）。** 给每个句子做嵌入。计算相邻句子间的余弦相似度。在相似度跌破阈值的地方切。保留主题连贯性。更慢；有时会切出伤害检索的 40-token 小碎片。

**句子分块（sentence）。** 按句子边界切。一句一块，或 N 句一个窗口。成本只是零头，却在 ~5k tokens 以内追平语义分块。

**父子文档分块（parent-document）。** 存小的子块（child）用于检索，*同时*存更大的父块（parent）用于上下文。按子块检索，返回父块。优雅退化：子块再差，返回的父块也还说得过去。

**后期分块（late chunking，2024）。** 先在 token 级嵌入整篇文档，再把 token 嵌入池化（pool）成块嵌入。保留跨块上下文。需要长上下文嵌入器（BGE-M3、Jina v3）。算力开销更高。

**上下文检索（contextual retrieval，Anthropic，2024）。** 给每个块前面拼上一段 LLM 生成的「它在文档中的位置」摘要（「这个块是终止条款章节的 3.2 节……」）。在 Anthropic 自己的基准上检索提升 35-50%。建索引很贵。

### The rule that beats every default · 比一切默认值都好的一条规则

让块大小匹配查询类型：

| 查询类型 | 块大小 |
|------------|-----------|
| 事实型（factoid，「CEO 叫什么名字？」） | 256-512 tokens |
| 分析型 / 多跳（multi-hop） | 512-1024 tokens |
| 整节理解 | 1024-2048 tokens |

来自 NVIDIA 2026 年基准。块要大到能装下答案加局部上下文，又要小到检索器的 top-K 返回聚焦在答案上而不是上下文噪声上。

```figure
n5-chunk-cuts
```

> **Fixed chunking.** Split every N characters or tokens.... **Recursive.** Try splitting on `\n\n` first, then `\n`, then `.`, then space. Falls back cleanly. The 2026 default.... **Late chunking (2024).** Embed the whole document at the token level first, then pool token embeddings into chunk embeddings.... **Contextual retrieval (Anthropic, 2024).** 35-50% retrieval improvement in Anthropic's own benchmark. Expensive to index.

> Match the chunk size to the query type.... The chunk should be big enough to contain the answer plus local context, small enough that the retriever's top-K returns focus on the answer rather than context noise.

## Build It · 动手造

### Step 1: fixed and recursive chunking · 固定分块与递归分块

```python
def chunk_fixed(text, size=512, overlap=0):
    step = size - overlap
    return [text[i:i + size] for i in range(0, len(text), step)]


def chunk_recursive(text, size=512, seps=("\n\n", "\n", ". ", " ")):
    if len(text) <= size:
        return [text]
    for sep in seps:
        if sep not in text:
            continue
        parts = text.split(sep)
        chunks = []
        buf = ""
        for p in parts:
            if len(p) > size:
                if buf:
                    chunks.append(buf)
                    buf = ""
                chunks.extend(chunk_recursive(p, size=size, seps=seps[1:] or (" ",)))
                continue
            candidate = buf + sep + p if buf else p
            if len(candidate) <= size:
                buf = candidate
            else:
                if buf:
                    chunks.append(buf)
                buf = p
        if buf:
            chunks.append(buf)
        return [c for c in chunks if c.strip()]
    return chunk_fixed(text, size)
```

### Step 2: semantic chunking · 语义分块

```python
def chunk_semantic(text, encoder, threshold=0.6, min_chars=200, max_chars=2048):
    sentences = split_sentences(text)
    if not sentences:
        return []
    embs = encoder.encode(sentences, normalize_embeddings=True)
    chunks = [[sentences[0]]]
    for i in range(1, len(sentences)):
        sim = float(embs[i] @ embs[i - 1])
        current_len = sum(len(s) for s in chunks[-1])
        if sim < threshold and current_len >= min_chars:
            chunks.append([sentences[i]])
        else:
            chunks[-1].append(sentences[i])

    result = []
    for group in chunks:
        text_group = " ".join(group)
        if len(text_group) > max_chars:
            result.extend(chunk_recursive(text_group, size=max_chars))
        else:
            result.append(text_group)
    return result
```

在你的领域上调 `threshold`。太高 → 碎片。太低 → 一整块巨无霸。

> Tune `threshold` on your domain. Too high → fragments. Too low → one giant chunk.

### Step 3: parent-document · 父子文档分块

```python
def chunk_parent_child(text, parent_size=2048, child_size=256):
    parents = chunk_recursive(text, size=parent_size)
    mapping = []
    for p_idx, parent in enumerate(parents):
        children = chunk_recursive(parent, size=child_size)
        for child in children:
            mapping.append({"child": child, "parent_idx": p_idx, "parent": parent})
    return mapping


def retrieve_parent(child_query, mapping, encoder, top_k=3):
    child_embs = encoder.encode([m["child"] for m in mapping], normalize_embeddings=True)
    q_emb = encoder.encode([child_query], normalize_embeddings=True)[0]
    scores = child_embs @ q_emb
    top = np.argsort(-scores)[:top_k]
    seen, parents = set(), []
    for i in top:
        if mapping[i]["parent_idx"] not in seen:
            parents.append(mapping[i]["parent"])
            seen.add(mapping[i]["parent_idx"])
    return parents
```

关键洞察：父块要去重。多个子块会映射到同一个父块；全都返回会浪费上下文。

> Key insight: dedupe parents. Multiple children can map to the same parent; returning all would waste context.

### Step 4: contextual retrieval (Anthropic pattern) · 上下文检索（Anthropic 模式）

```python
def contextualize_chunks(document, chunks, llm):
    context_prompts = [
        f"""<document>{document}</document>
Here is the chunk to situate: <chunk>{c}</chunk>
Write 50-100 words placing this chunk in the document's context."""
        for c in chunks
    ]
    contexts = llm.batch(context_prompts)
    return [f"{ctx}\n\n{c}" for ctx, c in zip(contexts, chunks)]
```

给上下文化后的块建索引。查询时，检索就能吃到这些额外的周边信号。

> Index the contextualized chunks. At query time, retrieval benefits from the extra surrounding signal.

### Step 5: evaluate · 评估

```python
def recall_at_k(queries, corpus_chunks, encoder, k=5):
    chunk_embs = encoder.encode(corpus_chunks, normalize_embeddings=True)
    hits = 0
    for q_text, gold_idxs in queries:
        q_emb = encoder.encode([q_text], normalize_embeddings=True)[0]
        top = np.argsort(-(chunk_embs @ q_emb))[:k]
        if any(i in gold_idxs for i in top):
            hits += 1
    return hits / len(queries)
```

永远要跑基准。适合你语料的「最佳」策略，可能跟任何博客文章都对不上。

> Always benchmark. The "best" strategy for your corpus may not match any blog post.

## Pitfalls · 常见的坑

- **只在事实型查询上评估分块。** 多跳查询会选出非常不一样的赢家。要用按查询类型分层的评估集。
- **语义分块不设最小尺寸。** 会产出伤害检索的 40-token 碎片。永远强制 `min_tokens`。
- **重叠变成货物崇拜（cargo cult）。** 2026 年的研究发现重叠常常毫无收益，还让索引成本翻倍。要测量，不要想当然。
- **不设最小/最大尺寸。** 5 个 token 的块和 5000 个 token 的块都会毁掉检索。要做钳制（clamp）。
- **跨文档分块。** 永远不要让一个块横跨两个文档。先按文档分块，再合并。

> Chunking evaluated only on factoid queries: multi-hop queries reveal very different winners. Use a query-type-stratified eval set.... 2026 studies find overlap often provides zero benefit and doubles index cost. Measure, do not assume.... Chunks of 5 tokens or 5000 tokens both break retrieval. Clamp.... Never let a chunk span two documents. Always chunk per-doc, then merge.

## Use It · 实战用法

2026 年的选型：

| 场景 | 策略 |
|-----------|----------|
| 第一次搭、语料未知 | 递归、512 tokens、无重叠 |
| 事实型 QA | 递归、256-512 tokens |
| 分析型 / 多跳 | 递归、512-1024 tokens + 父子文档 |
| 大量交叉引用（合同、论文） | 后期分块或上下文检索 |
| 对话 / 会话语料 | 按轮次分块 + 说话人元数据 |
| 超短文本（推文、评论） | 一个文档 = 一个块 |

从递归 512 起步。在 50 个查询的评估集上测 recall@5，再从那里调优。

> Start with recursive 512. Measure recall@5 on a 50-query eval set. Tune from there.

## Ship It · 交付

保存为 `outputs/skill-chunker.md`：

```markdown
---
name: chunker
description: Pick a chunking strategy, size, and overlap for a given corpus and query distribution.
version: 1.0.0
phase: 5
lesson: 23
tags: [nlp, rag, chunking]
---

Given a corpus (document types, avg length, domain) and query distribution (factoid / analytical / multi-hop), output:

1. Strategy. Recursive / sentence / semantic / parent-document / late / contextual. Reason.
2. Chunk size. Token count. Reason tied to query type.
3. Overlap. Default 0; justify if >0.
4. Min/max enforcement. `min_tokens`, `max_tokens` guards.
5. Evaluation plan. Recall@5 on 50-query stratified eval set (factoid, analytical, multi-hop).

Refuse any chunking strategy without min/max chunk size enforcement. Refuse overlap above 20% without an ablation showing it helps. Flag semantic chunking recommendations without a min-token floor.
```

> Save as `outputs/skill-chunker.md`.

## Exercises · 练习

1. **简单。** 用 fixed(512, 0)、recursive(512, 0)、recursive(512, 100) 三种方式给一份 20 页的文档分块。比较块数量和边界质量。
2. **中等。** 在 5 份文档上建一个 30 查询的评估集。测递归、语义、父子文档三种策略的 recall@5。谁赢？跟博客文章说的一致吗？
3. **困难。** 实现上下文检索。测它相对递归基线的 MRR 提升。报告索引成本（LLM 调用次数）与精度收益。

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|-----------------------|
| Chunk（块） | 「文档的一小片」 | 被嵌入、建索引、检索的子文档单元。 |
| Overlap（重叠） | 「安全余量」 | 相邻块之间共享的 N 个 token；2026 年的基准里常常没用。 |
| Semantic chunking（语义分块） | 「聪明分块」 | 在相邻句子嵌入相似度下降的地方切。 |
| Parent-document（父子文档） | 「两级检索」 | 检索小的子块，返回更大的父块。 |
| Late chunking（后期分块） | 「先嵌入后分块」 | 在 token 级嵌入整篇文档，再池化成块向量。 |
| Contextual retrieval（上下文检索） | 「Anthropic 的招」 | 建索引前给每个块前置一段 LLM 生成的摘要。 |
| Context cliff（上下文悬崖） | 「2500-token 之墙」 | 2026 年 1 月观察到 RAG 在约 2.5k 上下文 token 处质量骤降。 |

## Further Reading · 延伸阅读

- [Yepes et al. / LangChain — Recursive Character Splitting docs](https://python.langchain.com/docs/how_to/recursive_text_splitter/) —— 生产环境的默认选择。
- [Vectara (2024, NAACL 2025). Chunking configurations analysis](https://arxiv.org/abs/2410.13070) —— 分块的重要性不亚于嵌入选择。
- [Jina AI — Late Chunking in Long-Context Embedding Models (2024)](https://jina.ai/news/late-chunking-in-long-context-embedding-models/) —— 后期分块的论文。
- [Anthropic — Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval) —— 用 LLM 生成的上下文前缀带来 35-50% 的检索提升。
- [NVIDIA 2026 chunk-size benchmark — Premai summary](https://blog.premai.io/rag-chunking-strategies-the-2026-benchmark-guide/) —— 按查询类型选块大小。
