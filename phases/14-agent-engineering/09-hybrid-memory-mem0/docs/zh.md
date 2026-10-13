# Hybrid Memory: Vector + Graph + KV · 混合记忆：向量 + 图 + KV

> Hybrid memory runs three stores in parallel — vector for semantic similarity, KV for fast fact lookup, graph for entity-relationship reasoning — with a scoring layer that fuses them on retrieval. This is a widely used production pattern for external memory; Mem0 (Chhikara et al., 2025) is one reference implementation.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 07 (MemGPT), Phase 14 · 08 (Letta Blocks)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 解释为什么单一存储（只有向量、只有图、只有 KV）不足以支撑 agent 记忆
- 说出 Mem0 的三个并行存储，以及各自优化的方向
- 描述 Mem0 的融合评分——相关性（relevance）、重要性（importance）、新近度（recency）——以及为什么它是一个加权和而不是层级结构
- 用 stdlib 实现一个玩具版三存储记忆：`add()` 写入全部三个存储，`search()` 融合结果

> Explain why a single store (vector only, graph only, KV only) is insufficient for agent memory.
> Name Mem0's three parallel stores and what each one optimizes for.
> Describe Mem0's fusion scoring — relevance, importance, recency — and why it is a weighted sum, not a hierarchy.
> Implement a toy three-store memory in stdlib with an `add()` that writes to all three and a `search()` that fuses results.

## The Problem · 问题在哪

单一存储总会在三类查询中的一类上出错：

- **语义相似** —— 「我们上周关于 agent drift 都聊了什么？」向量存储赢；KV 和图都查不到。
- **事实查询** —— 「用户的电话号码是多少？」KV 赢；向量是浪费，图是杀鸡用牛刀。
- **关系推理** —— 「哪些客户共享同一个计费主体？」图赢；向量和 KV 都答不了。

生产环境的 agent 在同一个会话里会把这三类查询全发出来。单存储记忆必然在其中两类上是错的。Mem0 的贡献是把三个存储接到同一个 `add`/`search` 接口后面，再用一个评分函数把它们融合起来。

> One store is wrong for one of three query classes:
> - **Semantic similarity** — "what did we discuss about agent drift last week?" Vector wins; KV and graph miss.
> - **Fact lookup** — "what is the user's phone number?" KV wins; vector is wasteful, graph is overkill.
> - **Relationship reasoning** — "which customers share the same billing entity?" Graph wins; vector and KV cannot answer.
> Production agents issue all three in one session. A single-store memory is always wrong for two of them. Mem0's contribution is wiring all three behind a single `add`/`search` surface with a scoring function that fuses them.

## The Concept · 概念

### Three stores in parallel · 三个存储并行

Mem0（arXiv:2504.19413，2025 年 4 月）在 `add(text, user_id, metadata)` 时：

1. 从文本中抽取候选事实（由 LLM 驱动的一步）。
2. 把每条事实写入向量存储（vector store，做 embedding），用于语义检索。
3. 把每条事实写入 KV 存储，键为 (user_id, fact_type, entity)，实现 O(1) 查询。
4. 把每条事实写入图存储（Mem0g），成为带类型的边，用于关系查询。

在 `search(query, user_id)` 时：

1. 向量存储按 embedding 余弦相似度返回 top-k。
2. KV 存储按查询解析出的 (user_id, type, entity) 返回直接命中。
3. 图存储返回从查询实体可达的子图。
4. 一个评分层把三者融合。

> Mem0 (arXiv:2504.19413, April 2025) on `add(text, user_id, metadata)`: 1. Extract candidate facts from the text (an LLM-driven step). 2. Write each fact to the vector store (embedding) for semantic search. 3. Write each fact to the KV store keyed on (user_id, fact_type, entity) for O(1) lookup. 4. Write each fact to the graph store (Mem0g) as typed edges for relationship queries.
> On `search(query, user_id)`: Vector store returns top-k by embedding cosine. KV store returns direct hits keyed on query-derived (user_id, type, entity). Graph store returns subgraph reachable from query entities. A scoring layer fuses the three.

### Fusion scoring · 融合评分

```
score = w_relevance * relevance(q, record)
      + w_importance * importance(record)
      + w_recency * recency(record)
```

- **Relevance（相关性）** — 向量余弦、KV 精确命中、图路径权重。
- **Importance（重要性）** — 写入时打标，或者学习得到（有些事实更重要：姓名、ID、政策）。
- **Recency（新近度）** — 距上次写入或读取的时间按指数衰减。

权重按产品调。聊天 agent 调高 `w_recency`；合规 agent 调高 `w_importance`；检索 agent 调高 `w_relevance`。

> **Relevance** — vector cosine, KV exact match, graph path weight.
> **Importance** — tagged at write time or learned (some facts matter more: names, IDs, policies).
> **Recency** — exponential decay over time since last write or read.
> Weights are tuned per product. Higher `w_recency` for chat agents; higher `w_importance` for compliance agents; higher `w_relevance` for retrieval agents.

### Mem0g and temporal reasoning · Mem0g 与时序推理

Mem0g 加了一个冲突检测器。当一条新事实与已有边矛盾时，已有边被标记为失效（invalid），但不会删除。时序查询（「用户三月的时候在哪个城市？」）遍历「在某一时刻有效」的子图。

这正是 Letta 的失效模式（invalidation pattern）推广后的合规级行为。

> Mem0g adds a conflict detector. When a new fact contradicts an existing edge, the existing edge is marked invalid but not deleted. Temporal queries ("what was the user's city in March?") traverse the valid-at-time subgraph.
> This is the compliance-grade behavior Letta's invalidation pattern generalizes.

### Benchmark numbers · 基准成绩

Mem0 论文（2025）报告：

- **LoCoMo**（长对话记忆）：91.6
- **LongMemEval**（长程情景记忆）：93.4
- **BEAM 1M**（100 万 token 记忆基准）：64.1

对比基线（128k 全上下文 LLM、纯平面向量存储、纯平面 KV）都要低 10 分以上。单看基准不足以支撑选型——运营形态（operational shape）才是关键——但这些数字说明融合设计不是可以忽略的零头。

> Comparison baselines (full-context 128k LLM, flat vector store, flat KV) all lose by 10+ points. Benchmarks alone don't justify choice — operational shape does — but the numbers show the fusion design is not a rounding error.

### Scope taxonomy · 作用域分类

Mem0 按作用域（scope）拆分记忆：

- **User memory（用户记忆）** — 跨会话持久，按 `user_id` 键控。
- **Session memory（会话记忆）** — 在一个线程内持久。
- **Agent memory（agent 记忆）** — 每个 agent 实例各自的状态。

每次写入都要选定一个作用域。检索可以跨作用域查询，并给每个作用域配权重。不加思考地混用作用域，就会出「助手把 Bob 的项目讲给了 Alice 听」这类事故。

> Every write picks one scope. Retrieval can query across scopes with per-scope weights. Mixing scopes without thought is how you get "the assistant told Alice about Bob's project" incidents.

### Where this pattern goes wrong · 这个模式哪里会出错

- **Embedding 漂移。** 头一百次查询看起来正确的向量结果，会随语料增长而退化。要周期性地对最常用的前 N 条记录重新做 embedding。
- **KV schema 蔓延。** `(user_id, type, entity)` 看着简单，直到每个团队都加自己的 `type`。每季度审计一遍 type 集合。
- **图爆炸。** 一个不靠谱的抽取器每条消息加 50 条边。给每次 `add` 调用的图写入设上限；丢弃低置信度的边。

```figure
ae-memory-fusion
```

> **Embedding drift.** Vector results that look right on the first hundred queries degrade as the corpus grows. Add periodic re-embedding of the top-N-used records.
> **KV schema creep.** `(user_id, type, entity)` looks simple until every team adds their own `type`. Audit the type set quarterly.
> **Graph explosion.** One noisy extractor adds 50 edges per message. Cap graph writes per `add` call; drop low-confidence edges.

## Build It · 动手造

`code/main.py` 用 stdlib 实现三存储模式：

- `VectorStore` — 用朴素的词元重叠相似度充当 embedding 替身。
- `KVStore` — 以 `(user_id, fact_type, entity)` 为键的 dict。
- `GraphStore` — 带类型的边（subject, relation, object, valid）。
- `Mem0` — 顶层门面，提供 `add()`、`search()`、融合评分和作用域感知检索。
- 一段多用户、多会话对话的完整运行轨迹。

运行：

```
python3 code/main.py
```

输出展示三条独立的召回路径，加上融合后的 top-k。把 `main()` 顶部的评分权重改一改，看排名怎么变。

> `code/main.py` implements the three-store pattern in stdlib:
> The output shows three separate recall paths plus the fused top-k. Flip the scoring weights at the top of `main()` and watch the ranking change.

## Use It · 实战用法

- **Mem0（Apache 2.0）** — 生产可用。用 Postgres + Qdrant + Neo4j 自托管，或者用托管云。
- **Letta** — core/recall/archival 三层结构；向量和图后端可自带接入。
- **Zep** — 商业替代品，带时序知识图谱（KG）和事实抽取。
- **自建** — 当你需要对抽取器（合规场景）或融合权重（新近度主导的语音 agent）做精确控制时。

> **Mem0 (Apache 2.0)** — production-ready. Self-host with Postgres + Qdrant + Neo4j, or use the managed cloud.
> **Letta** — three-tier core/recall/archival; bring your own vector and graph backends.
> **Zep** — commercial alternative with temporal KG and fact extraction.
> **Custom builds** — when you need exact control over the extractor (compliance) or fusion weights (voice agents where recency dominates).

## Ship It · 交付

`outputs/skill-hybrid-memory.md` 生成一个三存储记忆脚手架，内置融合评分器、作用域分类和时序失效处理。

> `outputs/skill-hybrid-memory.md` generates a three-store memory scaffold with a fusion scorer, scope taxonomy, and temporal invalidation wired in.

## Exercises · 练习

1. 把玩具向量相似度换成真实的 embedding 模型（sentence-transformers、Ollama、OpenAI embeddings）。在一段合成的长对话上测 recall@10。1000 次写入之后排名会漂移吗？
2. 加一个时序查询：`search(query, as_of=timestamp)`。只返回在该时刻或之前有效的记录。哪个存储需要改的最多？
3. 实现一个冲突检测器：如果新事实与图中某条边矛盾，把旧边置为失效，并把两边都记进日志。用「用户住在柏林」->「用户住在里斯本」测试。
4. 给融合评分器加一个 `user_feedback` 维度（对召回的记录点赞）。你怎么防刷分（agent 只返回它自己已经点过赞的记录）？
5. 读 Mem0 文档（`docs.mem0.ai`）。把玩具实现移植成 `mem0` 客户端调用。在同样 20 条测试查询上比较检索质量。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| Hybrid memory（混合记忆） | 「向量加图加 KV」 | 三个存储并行写入，检索时融合 |
| Fact extraction（事实抽取） | 「记忆摄取」 | 把文本拆成 (entity, relation, fact) 元组的 LLM 步骤 |
| Fusion scoring（融合评分） | 「相关性排序」 | 相关性、重要性、新近度的加权和 |
| Scope（作用域） | 「记忆命名空间」 | user / session / agent —— 决定谁看到什么 |
| Mem0g | 「记忆图」 | 带时序有效性、带类型的边，用于关系查询 |
| Temporal invalidation（时序失效） | 「软删除」 | 把矛盾的边标记为失效；从不删除 |
| Embedding drift（embedding 漂移） | 「检索腐烂」 | 向量质量随语料增长而退化；周期性重新嵌入 |

## Further Reading · 延伸阅读

- [Chhikara et al., Mem0 (arXiv:2504.19413)](https://arxiv.org/abs/2504.19413) —— 原始论文
- [Mem0 docs](https://docs.mem0.ai/platform/overview) —— 生产 API、SDK、托管云
- [Packer et al., MemGPT (arXiv:2310.08560)](https://arxiv.org/abs/2310.08560) —— 虚拟上下文的前身
- [Letta, Memory Blocks blog](https://www.letta.com/blog/memory-blocks) —— 三层结构的姊妹设计
