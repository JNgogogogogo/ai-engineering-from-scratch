# Capstone 02 — RAG over Codebase (Cross-Repo Semantic Search) · 代码库 RAG（跨仓库语义搜索）

> 到 2026 年，每个严肃的工程组织都在跑一个理解语义、而不只是字符串的内部代码搜索。Sourcegraph Amp、Cursor 的 codebase answers、Augment 的企业图谱、Aider 的 repomap、Pinterest 的内部 MCP —— 同一个形状。摄取多个仓库，用 tree-sitter 解析，对函数级和类级 chunk 做嵌入，混合检索，重排序，带引用作答。这个毕业项目（capstone）要你造一个能处理 10 个仓库共 200 万行代码的系统，并且扛得住每次 git push 的增量重索引。

> Every serious engineering org in 2026 runs an internal code search that understands meaning, not just strings. Sourcegraph Amp, Cursor's codebase answers, Augment's enterprise graph, Aider's repomap, Pinterest's internal MCP — same shape. Ingest many repos, parse with tree-sitter, embed function- and class-level chunks, hybrid-search, re-rank, answer with citations. This capstone asks you to build one that handles 2M lines of code across 10 repos and survives incremental re-indexing on every git push.

**类型（Type）:** 毕业项目（Capstone）
**语言（Languages）:** Python（摄取），TypeScript（API + UI）
**先修（Prerequisites）:** Phase 5（NLP 基础）、Phase 7（transformers）、Phase 11（LLM 工程）、Phase 13（工具）、Phase 17（基础设施）
**实践阶段（Phases exercised）:** P5 · P7 · P11 · P13 · P17
**时间（Time）:** 30 小时

## Problem · 问题

到 2026 年，每个前沿编码智能体都自带一个代码库检索层，因为单靠上下文窗口解不了跨仓库问题。Claude 的 1M-token 上下文有帮助；但它没有消除对排序检索的需求。对原始 chunk 做朴素的余弦相似搜索，会在生成代码、monorepo 重复代码以及鲜少被导入的长尾符号上产生毒性结果。生产级的答案是：在 AST 感知（AST-aware）的 chunk 上做（稠密 + BM25）混合检索，配一个重排序器（re-ranker），背后再由符号引用图支撑。

你要通过索引一支真实的仓库舰队来学会它 —— 不是某一个教程仓库 —— 并测量 MRR@10、引用忠实度（citation faithfulness）和增量新鲜度。失败模式是基础设施层面的：一个 10 万文件的 monorepo、一次碰到了一半文件的 push、一个要跨四个仓库才能正确回答的查询。

> By 2026 every frontier coding agent ships with a codebase retrieval layer because context windows alone do not solve cross-repo questions. ... The production answer is a hybrid (dense + BM25) search over AST-aware chunks with a re-ranker, backed by a graph of symbol references. ... You learn this by indexing a real fleet — not one tutorial repo — and measuring MRR@10, citation faithfulness, and incremental freshness. The failure modes are infrastructural: a 100k-file monorepo, a push that retouches half the files, a query that needs to cross four repos to answer correctly.

## Concept · 概念

AST 感知的摄取管线用 tree-sitter 解析每个文件，抽取函数与类节点，并在节点边界处切 chunk，而不是用固定 token 窗口。每个 chunk 拿到三种表示：稠密 embedding（Voyage-code-3 或 nomic-embed-code）、稀疏 BM25 词项，以及一段简短的自然语言摘要。摘要提供了第三种可检索模态 —— 用户问「X 是怎么做授权的」，摘要里写了「authz」，即使代码里只有 `check_permission`。

检索是混合式的。一个查询同时触发稠密与 BM25 两路搜索，合并 top-k，把并集交给交叉编码器重排序器（Cohere rerank-3 或 bge-reranker-v2-gemma-2b）。重排序后的列表交给长上下文合成器（带 prompt caching 的 Claude Sonnet 4.7，或自托管 Llama 3.3 70B），并要求每条论断都按文件与行区间引用。没有引用的回答会被后置过滤器拒掉。

增量新鲜度是基础设施问题。git push 触发一次 diff：哪些文件变了、哪些符号变了。只有受影响的 chunk 重新嵌入。受影响的跨文件符号边（imports、方法调用）重新计算。索引保持一致，无需每次提交都重处理 200 万行。

> An AST-aware ingestion pipeline parses each file with tree-sitter, extracts function and class nodes, and chunks at node boundaries rather than fixed token windows. ... Retrieval is hybrid. A query fires both dense and BM25 searches, merges top-k, and hands the union to a cross-encoder re-ranker (Cohere rerank-3 or bge-reranker-v2-gemma-2b). ... Answers without citations are rejected by a post-filter. ... Incremental freshness is the infrastructure problem. Git push triggers a diff: which files changed, which symbols changed. Only affected chunks re-embed. The index stays consistent without reprocessing 2M lines each commit.

## Architecture · 架构

```
git push --> webhook --> ingest worker (LlamaIndex Workflow)
                           |
                           v
             tree-sitter parse + AST chunk
                           |
            +--------------+----------------+
            v              v                v
          dense        BM25 index       summary (LLM)
        (Voyage / bge)  (Tantivy)        (Haiku 4.5)
            |              |                |
            +------> Qdrant / pgvector <----+
                            |
                            v
                      symbol graph (Neo4j / kuzu)
                            |
  query --> LangGraph agent (retrieve -> rerank -> synth)
                            |
                            v
                 Claude Sonnet 4.7 1M context
                            |
                            v
                 answer + file:line citations
```

## Stack · 技术栈

- 解析：tree-sitter 配 17 种语言语法（Python、TS、Rust、Go、Java、C++ 等）
- 稠密 embedding：Voyage-code-3（托管）或 nomic-embed-code-v1.5（自托管），bge-code-v1 兜底
- 稀疏索引：Tantivy（Rust）配 BM25F，对符号名与函数体做字段加权
- 向量库：Qdrant 1.12 带混合检索；5000 万向量以下的团队可用 pgvector + pgvectorscale
- chunk 摘要模型：Claude Haiku 4.5 或 Gemini 2.5 Flash，prompt 缓存
- 重排序器：Cohere rerank-3，或自托管 bge-reranker-v2-gemma-2b
- 编排：摄取用 LlamaIndex Workflows，查询智能体用 LangGraph
- 合成器：Claude Sonnet 4.7（1M 上下文），带 prompt caching
- 符号图：Neo4j（托管）或 kuzu（嵌入式），存 import 与调用边
- 可观测性：每次检索 + 合成步骤一条 Langfuse span

> - Parsing: tree-sitter with 17 language grammars (Python, TS, Rust, Go, Java, C++, etc.)
> - Dense embeddings: Voyage-code-3 (hosted) or nomic-embed-code-v1.5 (self-host), bge-code-v1 fallback
> - Sparse index: Tantivy (Rust) with BM25F, field-weighted on symbol name vs body
> - Vector DB: Qdrant 1.12 with hybrid search, or pgvector + pgvectorscale for teams under 50M vectors
> - Chunk summary model: Claude Haiku 4.5 or Gemini 2.5 Flash, prompt-cached
> - Re-ranker: Cohere rerank-3 or bge-reranker-v2-gemma-2b self-hosted
> - Orchestration: LlamaIndex Workflows for ingestion, LangGraph for query agent
> - Synthesizer: Claude Sonnet 4.7 (1M context) with prompt caching
> - Symbol graph: Neo4j (managed) or kuzu (embedded) for import and call edges
> - Observability: Langfuse spans per retrieval + synthesis step

```figure
ce-hybrid-retrieval
```

## Build It · 动手造

1. **摄取遍历器。** 在每次 push hook 上迭代 git 历史。收集变更文件。对每个文件，用 tree-sitter 解析，抽出函数与类节点及其完整源码区间。产出 chunk 记录 `{repo, path, start_line, end_line, symbol, body}`。

2. **chunk 摘要器。** 把 chunk 分批送进 Haiku 4.5 调用，系统前导词开 prompt caching。提示词："Summarize this function in one sentence, naming its public contract and side effects." 摘要连同 chunk 一起存储。

3. **嵌入池。** 两条并行队列：稠密（Voyage-code-3，batch 128）与摘要（同一模型，但作用于摘要字符串）。向量连同 payload `{repo, path, start_line, end_line, symbol, kind}` 写入 Qdrant。

4. **BM25 索引。** 字段加权的 Tantivy 索引：符号名权重 4、函数体权重 1、摘要权重 2。让「找名字叫 X 的函数」与「找做 X 的函数」两类查询都能工作。

5. **符号图。** 对每个 chunk 记录边：imports（本文件使用了 repo Z 的符号 Y）、calls（本函数调用了类 C 上的方法 M）、继承。存入 kuzu。查询时用它把检索扩展到仓库边界之外。

6. **查询智能体。** LangGraph 三个节点。`retrieve` 并行触发稠密 + BM25，按 (repo, path, symbol) 去重。`rerank` 对 top-50 跑交叉编码器，保留 top-10。`synth` 调用 Claude Sonnet 4.7，把重排序后的 chunk 放进上下文，缓存系统提示词，强制 file:line 引用。

7. **引用强制。** 解析模型输出；任何缺少 `(repo/path:start-end)` 锚点的论断被标记重问或丢弃。只把带引用的回答返回给用户。

8. **增量重索引。** 每个 webhook 上计算符号级 diff。只对文本变化的 chunk 重新嵌入。对 imports 变化的 chunk 重算符号边。衡量标准：200 万行规模下，一次 50 文件的 push 在 60 秒内完成重索引。

9. **评估。** 为 100 个跨仓库问题标注 gold file:line 答案。测量 MRR@10、nDCG@10、引用忠实度（论断中带可验证锚点的比例）以及 p50/p99 延迟。

> **Ingestion walker.** Iterate git history on every push hook. Collect changed files. For each file, parse with tree-sitter, extract function and class nodes with their full source span. Emit chunk records `{repo, path, start_line, end_line, symbol, body}`. ... **BM25 index.** Field-weighted Tantivy index: symbol name weight 4, symbol body weight 1, summary weight 2. ... **Symbol graph.** For each chunk, record edges: imports, calls, inheritance. Used at query time to expand retrieval across repo boundaries. ... **Citation enforcement.** Parse the model output; any claim without a `(repo/path:start-end)` anchor gets flagged for re-ask or dropped. ... **Incremental re-index.** On each webhook, compute the symbol-level diff. Only re-embed chunks whose text changed. Measure: a 50-file push re-indexed in under 60 seconds for a 2M-LOC fleet.

## Use It · 实战用法

```
$ code-rag ask "how is S3 multipart abort wired into our retry budget?"
[retrieve]  12 chunks dense + 7 chunks bm25, 16 unique after dedup
[rerank]    top-5 kept (cohere rerank-3)
[synth]     claude-sonnet-4.7, cache hit rate 68%, 2.1s
answer:
  Multipart aborts are triggered by `AbortMultipartOnFail` in
  services/uploader/retry.go:122-148, which decrements the per-bucket
  retry budget defined in config/budgets.yaml:34-51 ...
  citations: [services/uploader/retry.go:122-148, config/budgets.yaml:34-51,
              libs/s3client/multipart.ts:44-61]
```

## Ship It · 交付

交付 skill 为 `outputs/skill-codebase-rag.md`。给定一组仓库语料，它搭起摄取管线、混合索引与查询智能体，并对任意跨仓库问题返回带引用的回答。评分标准：

| 权重 | 标准 | 如何衡量 |
|:-:|---|---|
| 25 | 检索质量 | 100 题留出集上的 MRR@10 与 nDCG@10 |
| 20 | 引用忠实度 | 回答论断中带可验证 file:line 锚点的比例 |
| 20 | 延迟与规模 | 在已索引语料规模上 10k QPS 的 p95 查询延迟 |
| 20 | 增量索引正确性 | 一次 50 文件提交从 git push 到可搜索的耗时 |
| 15 | UX 与答案排版 | 引用可点击、片段预览、追问入口 |
| **100** | | |

> Deliverable skill `outputs/skill-codebase-rag.md`. Given a corpus of repos, it stands up the ingestion pipeline, the hybrid index, and the query agent, and returns a cited answer for any cross-repo question.

## Exercises · 练习

1. 把 Voyage-code-3 换成自托管的 nomic-embed-code。测量 MRR@10 差值。报告开启重排序后差距是否收敛。

2. 向语料注入 20% 生成代码（LLM 产出的样板代码）并重新评估。观察检索被污染。给 payload 加一个 "generated" 标志，并下调这些命中的权重。

3. 在你的语料规模下，对 Qdrant 混合检索与 pgvector + pgvectorscale 做基准对比。报告 batch size 1 时的 p99。

4. 加一个基于抽样的漂移检查：每周重跑 100 题评估。MRR@10 跌幅超过 5% 就告警。

5. 扩展到跨语言符号解析：一个 Python 函数通过 gRPC 调用一个 Go 服务。用符号图把两者连起来。

> Swap Voyage-code-3 for nomic-embed-code self-hosted. Measure the MRR@10 delta. ... Inject 20% generated code (LLM-produced boilerplate) into the corpus and re-evaluate. Observe retrieval poisoning. Add a "generated" flag to the payload and down-weight those hits. ... Benchmark Qdrant hybrid search vs pgvector + pgvectorscale at your corpus size. Report p99 at batch size 1. ... Add a sampling-based drift check: weekly, rerun the 100-question eval. Alert on MRR@10 drop > 5%. ... Extend to cross-language symbol resolution: a Python function that calls a Go service over gRPC. Use the symbol graph to link them.

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|------------------------|
| AST-aware chunking（AST 感知切分） | 「函数级切分」 | 在 tree-sitter 节点边界而非固定 token 窗口处切代码 |
| Hybrid search（混合检索） | 「稠密 + 稀疏」 | 并行跑 BM25 与向量检索，合并 top-k，再重排序 |
| Cross-encoder rerank（交叉编码器重排） | 「第二阶段排序」 | 对每个（查询，候选）对联合打分的模型，比余弦更准 |
| Prompt caching（提示词缓存） | 「缓存的系统提示词」 | 2026 Claude / OpenAI 特性：重复前缀 token 命中时最高打 1 折 |
| Symbol graph（符号图） | 「代码图谱」 | 跨文件、跨仓库的 import、调用、继承边 |
| Citation faithfulness（引用忠实度） | 「有据回答率」 | 用户可点开锚点、读到被引区间的论断比例 |
| Incremental re-index（增量重索引） | 「push 到可搜索时间」 | 从 git push 到变更符号可被查询的墙钟时间 |

## Further Reading · 延伸阅读

- [Sourcegraph Amp](https://ampcode.com) — 生产级跨仓库代码智能
- [Sourcegraph Cody RAG architecture](https://sourcegraph.com/blog/how-cody-understands-your-codebase) — 本毕业项目的参考深度解析
- [Aider repo-map](https://aider.chat/docs/repomap.html) — tree-sitter 排序的仓库视图
- [Augment Code enterprise graph](https://www.augmentcode.com) — 商业符号图 RAG
- [Qdrant hybrid search docs](https://qdrant.tech/documentation/concepts/hybrid-queries/) — 参考实现
- [Voyage AI code embeddings](https://docs.voyageai.com/docs/embeddings) — Voyage-code-3 细节
- [Cohere rerank-3](https://docs.cohere.com/reference/rerank) — 交叉编码器参考
- [Pinterest MCP internal search](https://medium.com/pinterest-engineering) — 内部平台参考
