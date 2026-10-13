# ColPali and Vision-Native Document RAG · ColPali 与视觉原生文档 RAG

传统 RAG 把 PDF 解析成文本、切块、嵌入、存向量，每一步都在丢信号：OCR 丢掉图表数据，切块切断表格行，文本嵌入无视插图。ColPali（Faysse et al.，2024 年 7 月）问了一个更简单的问题：为什么要抽取文本？直接用 PaliGemma 嵌入页面图像，用 ColBERT 风格的后期交互（late interaction）做检索，把文档携带的版面、插图、字体、格式信号全部保留下来。已发表的基准显示：在视觉富集文档上，端到端精度比文本 RAG 高 20-40%。ColQwen2、ColSmol 和 VisRAG 延续了这个模式。本课解读视觉原生 RAG（vision-native RAG）的论点，并动手造一个微型 ColPali 式索引器。

> Traditional RAG parses PDFs into text, splits into chunks, embeds chunks, stores vectors. Every step loses signal: OCR drops chart data, chunking breaks table rows, text embeddings ignore figures. ColPali (Faysse et al., July 2024) asked the simpler question: why extract text at all? Embed the page image directly via PaliGemma, use ColBERT-style late interaction for retrieval, and keep all the layout, figures, fonts, and formatting signal the document carries. Published benchmarks: 20-40% better end-to-end accuracy than text-RAG on visually-rich documents. ColQwen2, ColSmol, and VisRAG extended the pattern. This lesson reads the vision-native RAG thesis and builds a tiny ColPali-like indexer.

**Type:** Build
**Languages:** Python（标准库，多向量索引器 + MaxSim 打分器）
**Prerequisites:** Phase 11（LLM Engineering——RAG 基础）、Phase 12 · 05（LLaVA）
**Time:** ~180 分钟

---

## Learning Objectives · 学习目标

- 解释双编码器检索（bi-encoder，每文档一个向量）与后期交互检索（late-interaction，每文档多个向量）的区别。
- 描述 ColBERT 的 MaxSim 操作，以及 ColPali 如何把它从文本 token 推广到图像块。
- 动手造一个微型 ColPali 式索引器：页面 → 图像块嵌入 → 对查询词嵌入做 MaxSim → top-k 页面。
- 在发票 / 财报用例上，比较「ColPali + Qwen2.5-VL 生成器」与「文本 RAG + GPT-4」。

> Explain the difference between bi-encoder retrieval (one vector per document) and late-interaction retrieval (many vectors per document).
> Describe ColBERT's MaxSim operation and how ColPali generalizes it from text tokens to image patches.
> Build a tiny ColPali-like indexer: page → patch embeddings → MaxSim over query-term embeddings → top-k pages.
> Compare ColPali + Qwen2.5-VL generator vs text-RAG + GPT-4 on an invoices / financial reports use case.

---

## The Problem · 问题在哪

对 PDF 跑文本 RAG，等于扔掉文档的大部分。财报的 Q3 营收增长通常在图表里；医学报告的结论在带标注的图像里；法律合同的签名区是一个版面事实，不是文本事实。

文本 RAG 流水线：

1. PDF → 文本，走 OCR / pdftotext。
2. 文本 → 300-500 token 的块。
3. 块 → 双编码器嵌入（一个向量）。
4. 用户查询 → 嵌入 → 余弦相似度 → top-k 块。
5. 块 + 查询 → LLM。

五步步步有损。图表没被捕捉。表格被切块切断。多栏版面被拍平。插图标注消失。

ColPali 的解法：跳过 OCR，直接嵌入页面图像。检索用 ColBERT 风格的后期交互（late interaction），让模型在查询时能关注细粒度的图像块。

> Text-RAG on PDFs throws away most of the document. A financial report's Q3 revenue growth is usually in a chart; a medical report's findings are in annotated images; a legal contract's signature block is a layout fact, not a text fact.
> Five lossy steps. Charts not captured. Tables broken across chunks. Multi-column layout flattens. Figure annotations disappear.
> ColPali's fix: skip OCR, embed the page image directly. Use ColBERT-style late interaction for retrieval so the model can attend to fine-grained patches at query time.

---

## The Concept · 概念

### ColBERT (2020) · ColBERT（2020）

ColBERT（Khattab & Zaharia，arXiv:2004.12832）是一种文本检索方法。它不给每个文档一个向量，而是给每个 token 一个向量。查询时：

- 查询 token 各自得到嵌入（N_q 个向量）。
- 文档 token 得到嵌入（N_d 个向量，通常预先缓存）。
- 得分 = 对每个查询 token，取它与所有文档 token 余弦相似度的最大值，再求和：Σ_i max_j cos(q_i, d_j)。

这就是 MaxSim 操作。每个查询 token「挑出」与它最匹配的文档 token，最终得分是它们的和。

优点：召回强，能处理词级语义。缺点：每文档 N_d 个向量，存储昂贵。

> ColBERT (Khattab & Zaharia, arXiv:2004.12832) is a text retrieval method. Instead of one vector per document, it produces one vector per token.
> This is the MaxSim operation. Each query token "picks" its best-matching document token. The final score is the sum.
> Pros: strong recall, handles term-level semantics. Cons: N_d vectors per document, storage expensive.

---

### ColPali · ColPali

ColPali（Faysse et al.，arXiv:2407.01449）把 ColBERT 模式搬到了图像上。

- 每一页由 PaliGemma（ViT + 语言模型）编码成图像块嵌入：每页 N_p 个向量。
- 每条用户查询（文本）编码成查询 token 嵌入：N_q 个向量。
- 得分 = Σ_i max_j cos(q_i, p_j)，即「查询文本 token × 页面图像块」上的 MaxSim。
- 按总得分检索 top-k 页面。

文档入库时：用 PaliGemma 嵌入每一页，存储全部图像块嵌入。查询时：嵌入查询 token，对所有已存页面嵌入算 MaxSim，返回 top-k 页面。

优点：在视觉富集文档上，端到端精度比文本 RAG 高 20-40%。每个块向量都捕捉局部版面与内容。

缺点：每页 N_p 个块 × 4 字节浮点 × D 维向量 = 存储增长很快。可用 PQ / OPQ 量化缓解。

> ColPali (Faysse et al., arXiv:2407.01449) applies the ColBERT pattern to images.
> Pros: end-to-end beats text-RAG by 20-40% on visually rich documents. Each patch-vector captures local layout and content.
> Cons: N_p patches × 4-byte floats × D-dim vectors per page = storage grows fast. Mitigated by PQ / OPQ quantization.

---

### ColQwen2 and ColSmol · ColQwen2 与 ColSmol

ColQwen2（illuin-tech，2024-2025）把 PaliGemma 换成 Qwen2-VL。更好的底座编码器，更好的检索。

ColSmol 是面向本地 / 边缘设备的小规模变体。一个 ~1B 参数的 ColSmol 检索器能在消费级 GPU 上运行。

> ColQwen2 (illuin-tech, 2024-2025) swaps PaliGemma for Qwen2-VL. Better base encoder, better retrieval.
> ColSmol is the smaller-scale variant for local / edge use. A ColSmol retriever at ~1B params runs on consumer GPU.

---

### VisRAG · VisRAG

VisRAG（Yu et al.，arXiv:2410.10594）是另一个变体：不在图像块上做 MaxSim，而是用 VLM 把每页池化（pool）成单个向量，再做双编码器检索。索引更快 + 存储更小，召回更弱。

质量与成本的取舍：要质量用 ColPali，要规模用 VisRAG。

> VisRAG (Yu et al., arXiv:2410.10594) is a different variant: instead of MaxSim on patches, pool each page into a single vector with a VLM then bi-encoder retrieve. Faster indexing + smaller storage, weaker recall.
> The quality-vs-cost trade-off: ColPali for quality, VisRAG for scale.

---

### M3DocRAG · M3DocRAG

M3DocRAG（Cho et al.，arXiv:2411.04952）把多模态检索扩展到多页、多文档推理。它跨文档检索页面，为 VLM 组装出多页上下文。

> M3DocRAG (Cho et al., arXiv:2411.04952) extends multi-modal retrieval to multi-page multi-document reasoning. Retrieves pages across documents, composes a multi-page context for the VLM.

---

### ViDoRe — the benchmark · ViDoRe——基准测试

ColPali 的配套基准。视觉文档检索评测（Visual Document Retrieval Evaluation）。任务覆盖财报、科学论文、行政文档、病历、手册。指标：nDCG@5。

ColPali-v1 在 ViDoRe 上的 nDCG@5 约 80%；同一批文档上文本 RAG 只有约 50-60%。

> ColPali's companion benchmark. Visual Document Retrieval Evaluation. Tasks include financial reports, scientific papers, administrative documents, medical records, manuals. Metric: nDCG@5.
> ColPali-v1 scores ~80% nDCG@5 on ViDoRe; text-RAG on the same documents scores ~50-60%.

---

### The end-to-end RAG pipeline · 端到端 RAG 流水线

视觉原生 RAG 的流程：

1. 入库：PDF → 页面图像 → PaliGemma 编码 → 存储全部图像块嵌入。
2. 查询：用户文本 → 查询 token 嵌入 → 对所有已索引页面算 MaxSim → top-k 页面。
3. 生成：top-k 页面图像 + 查询 → VLM（Qwen2.5-VL 或 Claude）→ 回答。

全程无 OCR。插图、图表、字体、版面全部流入最终回答。

> 1. Ingest: PDF → page images → PaliGemma encoding → store all patch embeddings.
> 2. Query: user text → query-token embeddings → MaxSim against all indexed pages → top-k pages.
> 3. Generate: top-k page images + query → VLM (Qwen2.5-VL or Claude) → answer.
> No OCR anywhere. Figures, charts, fonts, layout all flow into the answer.

---

### Storage math · 存储账

一份 50 页的财报，每页 729 个图像块、128 维嵌入：

- ColPali：50 * 729 * 128 * 4 字节 = 原始约 18 MB，PQ 后约 4 MB。
- 文本 RAG：50 块 * 768 维 * 4 字节 = 约 150 kB。

ColPali 每文档的存储大约是 30 倍。上规模后，OPQ / PQ 能压到约 5-10 倍，通常可以接受。

> A 50-page financial report with 729 patches per page and 128-dim embeddings:
> ColPali is ~30x more storage per document. At scale, OPQ / PQ brings it down to ~5-10x, usually tolerable.

---

### When text-RAG still wins · 文本 RAG 仍然胜出的场景

- 没有版面信号的纯文本文档（wiki 文章、聊天记录）。文本 RAG 更简单、存储更省。
- 数百万页的档案库，存储成本占主导。
- 监管严格、要求在检索之外还能抽取 OCR 文本的场景。

2026 年的其他一切——财报、科学论文、法律合同、病历、UX 文档——都是视觉原生 RAG 赢。

> Pure-text documents with no layout signal (wiki articles, chat logs). Text-RAG is simpler and storage-cheaper.
> For everything else in 2026 — financial reports, scientific papers, legal contracts, medical records, UX documentation — vision-native RAG wins.

```figure
mm-maxsim
```

---

## Use It · 实战用法

`code/main.py`：

- 玩具图像块编码器：把一个「页面」（小的特征向量网格）映射成图像块嵌入数组。
- MaxSim 打分器：在查询 token 嵌入集合与页面图像块集合之间计算 ColBERT 风格的得分。
- 索引 5 个玩具页面，跑 3 个查询，带得分返回 top-k。

---

## Ship It · 交付

本课产出 `outputs/skill-vision-rag-designer.md`。给定一个文档 RAG 项目，在 ColPali / ColQwen2 / VisRAG / 文本 RAG 之间选型并估算存储。

> This lesson produces `outputs/skill-vision-rag-designer.md`. Given a document-RAG project, picks ColPali / ColQwen2 / VisRAG / text-RAG and sizes the storage.

---

## Exercises · 练习

1. 一份 200 页的年报，每页 729 个图像块、128 维嵌入、4 字节浮点。计算原始存储和 PQ 压缩（8 倍）后的存储。

2. MaxSim 是 Σ_i max_j cos(q_i, p_j)。这个求和捕捉了什么，是简单平均相似度捕捉不到的？

3. ColPali 把页面索引成图像块集合。如果改成词级索引（像 ColBERT 那样）会有什么变化？取舍是什么？

4. 为一个 100 万页语料设计端到端流水线，延迟预算为每次查询 500ms。在 ColQwen2 / VisRAG 里选一个并给出理由。

5. 读 M3DocRAG（arXiv:2411.04952）。描述它的多页注意力模式，以及它与单页 ColPali 检索的区别。

---

## Key Terms · 术语表

| 术语 | 通俗说法 | 实际含义 |
|------|-----------------|------------------------|
| Late interaction | 「ColBERT 风格」 | 用每 token / 每图像块嵌入 + MaxSim 做检索，而不是单个文档向量 |
| MaxSim | 「对块取最大」 | 每个查询 token 挑相似度最高的文档 token；对查询求和 |
| Bi-encoder | 「单向量」 | 每文档一个向量；更快但丢失粒度 |
| Multi-vector | 「每文档多向量」 | 每文档 / 每页存 N_p 个向量；存储上涨但召回提升 |
| Patch embedding | 「页面特征」 | VLM 编码器为每个图像块给出的向量，按页缓存 |
| ViDoRe | 「视觉文档基准」 | ColPali 的视觉文档检索基准套件 |
| PQ quantization | 「乘积量化」 | 在保持向量相似度的同时把存储压缩约 8 倍 |

---

## Further Reading · 延伸阅读

- [Faysse et al. — ColPali (arXiv:2407.01449)](https://arxiv.org/abs/2407.01449)
- [Khattab & Zaharia — ColBERT (arXiv:2004.12832)](https://arxiv.org/abs/2004.12832)
- [Yu et al. — VisRAG (arXiv:2410.10594)](https://arxiv.org/abs/2410.10594)
- [Cho et al. — M3DocRAG (arXiv:2411.04952)](https://arxiv.org/abs/2411.04952)
- [illuin-tech/colpali GitHub](https://github.com/illuin-tech/colpali)
