# Capstone 08 — Production RAG Chatbot for a Regulated Vertical · 受监管行业的生产级 RAG 聊天机器人

> Harvey、Glean、Mendable 和 LlamaCloud 在 2026 年跑的都是同一个生产形态。用 docling 或 Unstructured 摄取，视觉内容用 ColPali。混合检索。用 bge-reranker-v2-gemma 重排。用 Claude Sonnet 4.7 合成，prompt 缓存命中率 60-80%。用 Llama Guard 4 和 NeMo Guardrails 护栏。用 Langfuse 和 Phoenix 监控。用 RAGAS 在 200 题黄金集（golden set）上评分。在一个受监管领域（法律、临床、保险）里造一个，这个毕业项目（capstone）的过关线是：黄金集、红队、漂移仪表盘三项全过。

> Harvey, Glean, Mendable, and LlamaCloud all run the same production shape in 2026. Ingest with docling or Unstructured and ColPali for visuals. Hybrid search. Re-rank with bge-reranker-v2-gemma. Synthesize with Claude Sonnet 4.7 using prompt caching at 60-80% hit rate. Guard with Llama Guard 4 and NeMo Guardrails. Watch with Langfuse and Phoenix. Grade with RAGAS on a 200-question golden set. Build one in a regulated domain (legal, clinical, insurance), and the capstone is passing the golden set, the red team, and the drift dashboard.

**类型（Type）:** 毕业项目（Capstone）
**语言（Languages）:** Python（管线 + API），TypeScript（聊天 UI）
**先修（Prerequisites）:** Phase 5（NLP）、Phase 7（transformers）、Phase 11（LLM 工程）、Phase 12（多模态）、Phase 17（基础设施）、Phase 18（安全）
**实践阶段（Phases exercised）:** P5 · P7 · P11 · P12 · P17 · P18
**时间（Time）:** 30 小时

## Problem · 问题

受监管领域 RAG（法律合同、临床试验方案、保险条款）是 2026 年出货最多的生产形态，因为 ROI 一眼可见、风险实实在在。Harvey（Allen & Overy）为法律造了它。Mendable 出货开发者文档版。Glean 覆盖企业搜索。模式是：高保真摄取、混合检索加重排、带引用强制与 prompt 缓存的合成、多层安全护栏（guardrails）、持续的漂移监控。

难点不在模型。在司法辖区感知的合规（HIPAA、GDPR、SOC2）、引用级可审计、成本控制（命中率高的 prompt 缓存能买下 60-90% 折扣）、用 RAGAS 忠实度做幻觉检测，以及源文档更新了索引却没跟上的漂移检测。这个毕业项目要你在一个 200 题黄金集上把这一切全部交付，并配一套红队（red team）测试。

> Regulated-domain RAG (legal contracts, clinical trial protocols, insurance policies) is the most-shipped production shape of 2026 because the ROI is obvious and the stakes are concrete. ... The pattern is: ingest high-fidelity, retrieve hybrid with rerank, synthesize with citation enforcement and prompt caching, guard with multiple safety layers, and monitor drift continuously. ... The hard parts are not the model. They are jurisdiction-aware compliance (HIPAA, GDPR, SOC2), citation-level auditability, cost control (prompt caching buys 60-90% discount when hit rate is high), hallucination detection via RAGAS faithfulness, and drift detection when the source documents get updated without the index catching up. This capstone asks you to ship all of it on a 200-question golden set with a red-team suite alongside.

## Concept · 概念

管线有两面。**摄取**：docling 或 Unstructured 解析结构化文档；ColPali 处理视觉富集的；chunk 被打上摘要、标签和基于角色的访问标签。向量进 pgvector + pgvectorscale（5000 万向量以下）或 Qdrant Cloud；稀疏 BM25 并行运行。**对话**：LangGraph 管记忆与多轮；每个查询跑混合检索，用 bge-reranker-v2-gemma-2b 重排，用 Claude Sonnet 4.7（prompt 缓存）合成，输出过 Llama Guard 4 和 NeMo Guardrails，最后发出带引用锚点的回答。

评估栈有四层。**黄金集**（200 条带引用的标注问答）管正确性。**红队**（越狱、PII 抽取尝试、域外问题）管安全。**RAGAS** 逐轮自动测忠实度 / 回答相关性 / 上下文精确度。**漂移仪表盘**（Arize Phoenix）每周盯检索质量与幻觉分数。

prompt 缓存是成本杠杆。Claude 4.5+ 和 GPT-5+ 支持缓存系统提示词 + 检索到的上下文。命中率 60-80% 时，单查询成本降 3-5 倍。管线必须为稳定前缀而设计（系统提示词 + 重排后上下文放最前）才能拿到高缓存命中率。

> The pipeline has two sides. **Ingestion**: docling or Unstructured parses structured documents; ColPali handles visually rich ones; chunks get summaries, tags, and role-based access labels. ... **Conversation**: LangGraph handles memory and multi-turn; each query runs hybrid retrieval, reranks with bge-reranker-v2-gemma-2b, synthesizes with Claude Sonnet 4.7 (prompt-cached), passes output through Llama Guard 4 and NeMo Guardrails, and emits a citation-anchored response. ... The eval stack has four layers. **Golden set** (200 labeled Q/A with citations) for correctness. **Red team** (jailbreaks, PII extraction attempts, off-domain questions) for safety. **RAGAS** for faithfulness / answer relevance / context precision automatically per-turn. **Drift dashboard** (Arize Phoenix) watching retrieval quality and hallucination score weekly. ... Prompt caching is the cost lever. ... At 60-80% hit rate, per-query cost drops 3-5x. The pipeline must be designed for stable prefixes (system prompt + reranked context first) to achieve high cache hit rates.

## Architecture · 架构

```
documents (contracts, protocols, policies)
      |
      v
docling / Unstructured parse + ColPali for visuals
      |
      v
chunks + summaries + role-labels + jurisdiction tags
      |
      v
pgvector + pgvectorscale  +  BM25 (Tantivy)
      |
query + role + jurisdiction
      |
      v
LangGraph conversational agent
   +--- retrieve (hybrid)
   +--- filter by role + jurisdiction
   +--- rerank (bge-reranker-v2-gemma-2b or Voyage rerank-2)
   +--- synthesize (Claude Sonnet 4.7, prompt cached)
   +--- guard (Llama Guard 4 + NeMo Guardrails + Presidio output PII scrub)
   +--- cite + return
      |
      v
eval:
  RAGAS faithfulness / answer_relevance / context_precision (online)
  Langfuse annotation queue (sampled)
  Arize Phoenix drift (weekly)
  red team suite (pre-release)
```

## Stack · 技术栈

- 摄取：结构化文档用 Unstructured.io 或 docling；视觉富集 PDF 用 ColPali
- 向量库：5000 万向量以下用 pgvector + pgvectorscale；否则 Qdrant Cloud
- 稀疏：Tantivy BM25 带字段权重
- 编排：LlamaIndex Workflows（摄取）+ LangGraph（对话）
- 重排序器：自托管 bge-reranker-v2-gemma-2b 或托管 Voyage rerank-2
- LLM：Claude Sonnet 4.7 带 prompt caching；兜底自托管 Llama 3.3 70B
- 评估：RAGAS 0.2 在线，DeepEval 跑幻觉与越狱套件
- 可观测性：自托管 Langfuse 带标注队列；Arize Phoenix 看漂移
- 护栏：Llama Guard 4 输入/输出分类器、NeMo Guardrails v0.12 策略、Presidio PII 清洗
- 合规：chunk 上的角色访问标签；GDPR/HIPAA 的司法辖区标签

> - Ingestion: Unstructured.io or docling for structured documents; ColPali for visually-rich PDFs
> - Vector DB: pgvector + pgvectorscale under 50M vectors; Qdrant Cloud otherwise
> - Sparse: Tantivy BM25 with field weights
> - Orchestration: LlamaIndex Workflows (ingestion) + LangGraph (conversation)
> - Re-ranker: bge-reranker-v2-gemma-2b self-hosted or Voyage rerank-2 hosted
> - LLM: Claude Sonnet 4.7 with prompt caching; fallback Llama 3.3 70B self-hosted
> - Eval: RAGAS 0.2 online, DeepEval for hallucination and jailbreak suites
> - Observability: Langfuse self-hosted with annotation queue; Arize Phoenix for drift
> - Guardrails: Llama Guard 4 input/output classifier, NeMo Guardrails v0.12 policy, Presidio PII scrub
> - Compliance: role-based access labels on chunks; jurisdiction tags for GDPR/HIPAA

```figure
canary-rollout
```

## Build It · 动手造

1. **摄取。** 用 Unstructured 或 docling 解析你的语料（认真的规模是 1000-10000 份文档）。扫描件/视觉密集页走 ColPali。产出带摘要、角色标签、辖区标签的 chunk。

2. **索引。** 稠密 embedding（Voyage-3 或 Nomic-embed-v2）进 pgvector + pgvectorscale。BM25 侧索引走 Tantivy。角色与辖区过滤器作为 payload。

3. **混合检索。** 先按角色+辖区过滤；再并行稠密 + BM25；用倒数排序融合（RRF）合并；top-20 给重排序器；top-5 给合成器。

4. **带 prompt 缓存的合成。** 系统提示词 + 静态策略放缓存头；重排后上下文作缓存扩展；用户问题作未缓存后缀。稳态目标 60-80% 缓存命中率。

5. **护栏。** 输入过 Llama Guard 4；NeMo Guardrails rails 拦截域外问题或政策禁止话题；Presidio 清洗输出中意外出现的 PII；引用强制后置过滤。

6. **黄金集。** 200 条由领域专家标注、带（答案、引用）的问答对。按精确引用匹配、回答正确性、忠实度（RAGAS）给智能体打分。

7. **红队。** 50 条对抗提示：越狱（PAIR、TAP）、PII 外传尝试、域外、跨辖区泄漏。按 pass/fail 和严重度打分。

8. **漂移仪表盘。** Arize Phoenix 每周跟踪检索质量（nDCG、引用忠实度）。跌 5% 告警。

9. **成本报告。** Langfuse：prompt 缓存命中率、每查询 token、按阶段拆解的 $/query。

> **Ingestion.** Parse your corpus (1000-10000 documents for a serious build) with Unstructured or docling. For scanned / visual-heavy pages, route through ColPali. Produce chunks with summaries, role-labels, jurisdiction tags. ... **Hybrid retrieve.** Filter by role+jurisdiction first; then parallel dense + BM25; merge with reciprocal rank fusion; top-20 to reranker; top-5 to synth. ... **Synthesize with prompt caching.** System prompt + static policies in cache header; reranked context as cache extension; user question as uncached suffix. Target 60-80% cache hit rate in steady state. ... **Golden set.** 200 Q/A pairs labeled by a domain expert with (answer, citations). Score agent on exact-citation match, answer correctness, faithfulness (RAGAS). ... **Red team.** 50 adversarial prompts: jailbreaks (PAIR, TAP), PII exfiltration attempts, off-domain, cross-jurisdiction leaks. Score with pass/fail and severity.

## Use It · 实战用法

```
$ chat --role=analyst --jurisdiction=GDPR
> what is the data-retention obligation for EU user profiles under our contract?
[retrieve]  hybrid top-20 filtered to GDPR + analyst-role
[rerank]    top-5 kept
[synth]     claude-sonnet-4.7, cache hit 74%, 0.8s
answer:
  The contract (Section 12.4, Master Services Agreement dated 2024-03-11)
  obligates EU user profile deletion within 30 days of termination per GDPR
  Article 17. The DPA amendment (DPA-v2.1, Section 5) extends this to 14 days
  for "restricted" category data.
  citations: [MSA-2024-03-11 s12.4, DPA-v2.1 s5]
```

## Ship It · 交付

`outputs/skill-production-rag.md` 描述了交付物。一个部署上线、带合规标签、通过评分标准、有实时漂移监控的受监管领域聊天机器人。

| 权重 | 标准 | 如何衡量 |
|:-:|---|---|
| 25 | RAGAS 忠实度 + 回答相关性 | 黄金集（200 问答）上的在线分数 |
| 20 | 引用正确性 | 带可验证源锚点的回答比例 |
| 20 | 护栏覆盖率 | Llama Guard 4 通过率 + 越狱套件结果 |
| 20 | 成本 / 延迟工程 | prompt 缓存命中率、p95 延迟、$/query |
| 15 | 漂移监控仪表盘 | Phoenix 实时仪表盘带每周检索质量趋势 |
| **100** | | |

> `outputs/skill-production-rag.md` describes the deliverable. A regulated-domain chatbot deployed with compliance labels, passed through the rubric, observed with live drift monitoring.

## Exercises · 练习

1. 在另一个司法辖区下建第二块语料切片（如 GDPR 之外再加 HIPAA）。用 20 题跨辖区探针演示角色+辖区过滤阻止跨库泄漏。

2. 测一周生产流量的 prompt 缓存命中率。找出破坏缓存前缀的查询。重构。

3. 用 10k-token 摘要缓冲加多轮记忆。测对话变长时忠实度是否下降。

4. 把 Claude Sonnet 4.7 换成自托管 Llama 3.3 70B。测 $/query 和忠实度差值。

5. 加一个「不确定」模式：若 top 重排分数低于阈值，智能体说 "I do not have confident citations" 而不是硬答。测虚假自信的减少量。

> Build a second corpus slice under a different jurisdiction (e.g., HIPAA alongside GDPR). Demonstrate role+jurisdiction filtering preventing cross-leak on a 20-question cross-jurisdiction probe. ... Measure prompt-cache hit rate over a week of production traffic. Identify which queries break the cache prefix. Restructure. ... Add multi-turn memory with a 10k-token summary buffer. Measure whether faithfulness drops as the conversation grows. ... Swap Claude Sonnet 4.7 for Llama 3.3 70B self-hosted. Measure $/query and faithfulness delta. ... Add an "unsure" mode: if top reranked scores are below a threshold, the agent says "I do not have confident citations" instead of answering. Measure false-confidence reduction.

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|------------------------|
| Prompt caching（prompt 缓存） | 「缓存系统 + 上下文」 | Claude/OpenAI 特性：命中时缓存前缀 token 打 1-4 折 |
| RAGAS | 「RAG 评估器」 | 自动打分：忠实度、回答相关性、上下文精确度 |
| Golden set（黄金集） | 「标注评估集」 | 200+ 条专家标注、带引用的问答；即 ground truth |
| Jurisdiction tag（辖区标签） | 「合规标签」 | 贴在 chunk 上的 GDPR/HIPAA/SOC2 范围；由检索过滤器强制执行 |
| Citation faithfulness（引用忠实度） | 「有据回答率」 | 有可检索源区间支撑的论断比例 |
| Drift（漂移） | 「检索质量衰减」 | nDCG 或引用分的周度变化；告警阈值 5% |
| Red team（红队） | 「对抗评估」 | 发布前的越狱、PII 抽取、域外探针 |

## Further Reading · 延伸阅读

- [Harvey AI](https://www.harvey.ai) — 法律生产栈参考
- [Glean enterprise search](https://www.glean.com) — 企业规模 RAG 参考
- [Mendable documentation](https://mendable.ai) — 开发者文档 RAG 参考
- [LlamaCloud Parse + Index](https://docs.cloud.llamaindex.ai/llamaparse/getting_started) — 托管摄取
- [Anthropic prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) — 成本杠杆参考
- [RAGAS 0.2 documentation](https://docs.ragas.io/) — 权威 RAG 评估框架
- [Arize Phoenix](https://github.com/Arize-ai/phoenix) — 参考漂移可观测方案
- [Llama Guard 4](https://www.llama.com/docs/model-cards-and-prompt-formats/llama-guard-4/) — 2026 安全分类器
- [NeMo Guardrails v0.12](https://docs.nvidia.com/nemo-guardrails/) — 策略 rail 框架
