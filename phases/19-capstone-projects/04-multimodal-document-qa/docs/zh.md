# Capstone 04 — Multimodal Document QA (Vision-First PDF, Tables, Charts) · 多模态文档问答（视觉优先的 PDF、表格与图表）

> 2026 年的文档问答（document QA）前沿从「先 OCR 再文本」转向了视觉优先的后期交互（late interaction）。ColPali、ColQwen2.5 和 ColQwen3-omni 把每一页 PDF 当作图像，用多向量后期交互做嵌入，让查询直接注意（attend）到图块（patch）上。在财务 10-K、科学论文和手写笔记上，这一模式大幅领先 OCR 优先方案。在 1 万页上端到端建好这条管线，并发布与「先 OCR 再文本」的正面对比。

> The 2026 document-QA frontier moved away from OCR-then-text and toward vision-first late interaction. ColPali, ColQwen2.5, and ColQwen3-omni treat each PDF page as an image, embed it with multi-vector late interaction, and let the query attend to patches directly. On financial 10-Ks, scientific papers, and handwritten notes this pattern beats OCR-first by a large margin. Build the pipeline end to end on 10k pages and publish the side-by-side against OCR-then-text.

**类型（Type）:** 毕业项目（Capstone）
**语言（Languages）:** Python（管线），TypeScript（查看器 UI）
**先修（Prerequisites）:** Phase 4（计算机视觉）、Phase 5（NLP）、Phase 7（transformers）、Phase 11（LLM 工程）、Phase 12（多模态）、Phase 17（基础设施）
**实践阶段（Phases exercised）:** P4 · P5 · P7 · P11 · P12 · P17
**时间（Time）:** 30 小时

## Problem · 问题

企业的 PDF 库正被 OCR 管线糟蹋：带旋转表格的扫描版 10-K、公式密集的科学论文、只有作为图像才有意义的图表、手写批注。把它们当文本优先处理意味着丢掉一半信号。2026 年的答案是在原始页面图像上做多向量后期交互检索。ColPali（Illuin Tech）首创；ColQwen2.5-v0.2 与 ColQwen3-omni 推高了准确率。在 ViDoRe v3 上，视觉优先检索以有意义的幅度超过「先 OCR 再文本」—— 而在图表、表格和手写体上差距进一步拉大。

代价是存储与延迟。一个 ColQwen embedding 是每页约 2048 个 patch 向量，而不是一个 1024 维向量。原始存储暴涨。DocPruner（2026）实现了 50% 剪枝而无可测的精度损失。你要索引 1 万页，测 ViDoRe v3 nDCG@5，在 2 秒内出答案，并直接与 OCR-then-text 基线对比。

> Enterprises sit on PDFs that OCR pipelines mangle: scanned 10-Ks with rotated tables, scientific papers dense with equations, charts that only make sense as images, handwritten annotations. ... The 2026 answer is late-interaction multi-vector retrieval on raw page images. ... On ViDoRe v3, vision-first retrieval scores above OCR-then-text by meaningful margins — and the gap widens on charts, tables, and handwriting. ... The trade-off is storage and latency. A ColQwen embedding is ~2048 patch vectors per page, not a single 1024-dim vector. Raw storage balloons. DocPruner (2026) brings 50% pruning without measurable accuracy loss.

## Concept · 概念

后期交互（late interaction）指每个查询 token 与每个 patch token 逐一打分，再对每个查询 token 取最大分求和。无需汇聚成单一向量就能得到细粒度匹配。多向量（multi-vector）索引（Vespa、Qdrant multi-vector 或 AstraDB）保存逐 patch 的 embedding，并在检索时跑 MaxSim。

回答器是一个视觉语言模型（VLM），输入查询加 top-k 检索页图像，写出带证据区域（边界框或页码引用）的回答。Qwen3-VL-30B、Gemini 2.5 Pro 和 InternVL3 是 2026 年的前沿选择。对公式和科学记号，接一条 OCR 兜底通路（Nougat、dots.ocr）作为可选文本通道。

评估是一张二维矩阵。一条轴：内容类型（纯文本段落、密集表格、柱状/折线图、手写笔记、公式）。另一条轴：检索方案（视觉优先后期交互 vs 先 OCR 再文本 vs 混合）。每个格子填 nDCG@5 和回答准确率。报告就是交付物。

> Late interaction means every query token scores against every patch token, and the maximum score per query token is summed. You get fine-grained matching without needing a single pooled vector. A multi-vector index (Vespa, Qdrant multi-vector, or AstraDB) stores the per-patch embeddings and runs MaxSim at retrieval time. ... The answerer is a vision-language model that takes the query plus the top-k retrieved pages as images and writes an answer with evidence regions (bounding boxes or page references). ... Evaluation is a two-dimensional matrix. One axis: content type (plain text paragraphs, dense tables, bar/line charts, handwritten notes, equations). Other axis: retrieval approach (vision-first late interaction vs OCR-then-text vs hybrid). Each cell gets nDCG@5 and answer accuracy. The report is the deliverable.

## Architecture · 架构

```
PDFs -> page renderer (PyMuPDF, 180 DPI)
           |
           v
  ColQwen2.5-v0.2 embed (multi-vector per page, ~2048 patches)
           |
           +------> DocPruner 50% compression
           |
           v
   multi-vector index (Vespa or Qdrant multi-vector)
           |
query ----+----> retrieve top-k pages (MaxSim)
           |
           v
  VLM answerer: Qwen3-VL-30B | Gemini 2.5 Pro | InternVL3
    inputs: query + top-k page images + optional OCR text
           |
           v
  answer with cited page numbers + evidence regions
           |
           v
  Streamlit / Next.js viewer: highlighted boxes on source page
```

## Stack · 技术栈

- 页面渲染：PyMuPDF（fitz），180 DPI，纵向归一化
- 后期交互模型：ColQwen2.5-v0.2 或 ColQwen3-omni（Hugging Face 上的 vidore 团队）
- 索引：Vespa 多向量字段，或 Qdrant multi-vector，或带 MaxSim 的 AstraDB
- 剪枝：DocPruner 2026 策略（保留高方差 patch，50% 压缩下精度损失 < 0.5%）
- OCR 兜底（公式 / 密集表格）：dots.ocr 或 Nougat
- VLM 回答器：自托管 Qwen3-VL-30B 或托管 Gemini 2.5 Pro；InternVL3 兜底
- 评估：ViDoRe v3 基准，多页推理用 M3DocVQA
- 查看器 UI：Next.js 15，证据区域用 canvas 叠加层

> - Page rendering: PyMuPDF (fitz) at 180 DPI, portrait-normalized
> - Late-interaction model: ColQwen2.5-v0.2 or ColQwen3-omni (vidore team on Hugging Face)
> - Index: Vespa with multi-vector field, or Qdrant multi-vector, or AstraDB with MaxSim
> - Pruning: DocPruner 2026 policy (keep high-variance patches, 50% compression at < 0.5% accuracy loss)
> - OCR fallback (equations / dense tables): dots.ocr or Nougat
> - VLM answerer: Qwen3-VL-30B self-hosted or Gemini 2.5 Pro hosted; InternVL3 as fallback
> - Evaluation: ViDoRe v3 benchmark, M3DocVQA for multi-page reasoning
> - Viewer UI: Next.js 15 with canvas overlay for evidence regions

```figure
ce-late-interaction
```

## Build It · 动手造

1. **摄取。** 走一遍 1 万页 PDF 语料，覆盖 10-K、科学论文与扫描件。每页渲染成 1536x2048 PNG。持久化 `{doc_id, page_num, image_path}`。

2. **嵌入。** 对每页图像跑 ColQwen2.5-v0.2。输出约 2048 个 128 维 patch embedding。用 DocPruner 保留信号最强的一半。写入 Vespa 多向量字段或 Qdrant multi-vector。

3. **查询。** 对每个进来的查询，用查询塔（token 级 embedding）嵌入。对索引跑 MaxSim：对每个查询 token，在页面 patch embedding 上取最大点积，再求和。返回 top-k 页。

4. **合成。** 用查询和 top-5 页面图像调用 Qwen3-VL-30B。提示词："Answer using only the supplied pages. Cite each claim by (doc_id, page) and name the region (figure, table, paragraph)."

5. **证据区域。** 后处理回答，抽取被引区域。若 VLM 输出边界框（Qwen3-VL 会），在查看器里渲染成叠加层。

6. **OCR 兜底。** 对被识别为公式密集的页面（基于图像方差的启发式），跑 Nougat 或 dots.ocr，把 OCR 文本作为图像之外的额外通道传入。

7. **评估。** 跑 ViDoRe v3（检索 nDCG@5）和 M3DocVQA（多页问答准确率）。在相同语料、相同合成器上再跑一遍 OCR-then-text 管线。产出「内容类型 × 方案」矩阵。

8. **UI。** 先做 Streamlit 原型；再做 Next.js 15 生产查看器，逐页叠加证据区域。

> **Ingest.** Walk a corpus of 10k PDF pages across 10-Ks, scientific papers, and scanned documents. Render each page to a 1536x2048 PNG. Persist `{doc_id, page_num, image_path}`. ... **Embed.** Run ColQwen2.5-v0.2 on each page image. Output shape ~2048 patch embeddings of dim 128. Apply DocPruner to keep the highest-signal half. ... **Query.** For each incoming query, embed with the query tower (token-level embeddings). Run MaxSim against the index: for every query token, take the max dot-product over page patch embeddings, sum. Return top-k pages. ... **Synthesize.** Call Qwen3-VL-30B with the query and the top-5 page images. Prompt: "Answer using only the supplied pages. Cite each claim by (doc_id, page) and name the region (figure, table, paragraph)." ... **OCR fallback.** For pages identified as equation-dense (heuristic on image variance), run Nougat or dots.ocr and pass the OCR text as an extra channel alongside the image.

## Use It · 实战用法

```
$ doc-qa ask "what was the 2024 operating margin change for segment EMEA?"
[retrieve]   top-5 pages in 320ms (ColQwen2.5, MaxSim, Vespa)
[synth]      qwen3-vl-30b, 1.4s, cited (form-10k-2024, p. 88) + (..., p. 92)
answer:
  EMEA operating margin moved from 18.2% to 16.8%, a 140bp decline.
  cited: 10-K-2024.pdf p.88 (Table 4, Segment Operating Margin)
         10-K-2024.pdf p.92 (MD&A, Operating Performance)
[viewer]     open with highlighted bounding boxes overlaid on p.88 Table 4
```

## Ship It · 交付

`outputs/skill-doc-qa.md` 描述了交付物：一个视觉优先的多模态文档问答系统，针对特定语料调优，并在 ViDoRe v3 上与 OCR-then-text 基线对比评估。

| 权重 | 标准 | 如何衡量 |
|:-:|---|---|
| 25 | ViDoRe v3 / M3DocVQA 准确率 | 基准数字对比 OCR-text 基线与公开排行榜 |
| 20 | 证据区域落地 | 被引区域确实包含答案片段的比例 |
| 20 | 存储与延迟工程 | DocPruner 压缩率、索引 p95、回答 p95 |
| 20 | 多页推理 | 人工标注的 100 题多页集上的准确率 |
| 15 | 源检视 UX | 查看器清晰度、叠加保真度、并排对比工具 |
| **100** | | |

> `outputs/skill-doc-qa.md` describes the deliverable: a vision-first multimodal document QA system tuned to a specific corpus and evaluated against an OCR-then-text baseline on ViDoRe v3.

## Exercises · 练习

1. 在同一语料上测 ColQwen2.5-v0.2 vs ColQwen3-omni。哪些页面一个对、另一个错？给索引加一个「内容类别」标签，按类型路由。

2. 激进剪枝 embedding（75%、90%）。找出压缩悬崖：ViDoRe nDCG@5 跌破 OCR 基线的那个点。

3. 建一个混合方案：并行跑 OCR-then-text 和 ColQwen，用 RRF 融合，再用交叉编码器重排。混合能赢过任何单路吗？在哪里帮助最大？

4. 把 Qwen3-VL-30B 换成更小的 VLM（Qwen2.5-VL-7B）。测「准确率/美元」曲线。

5. 加手写笔记支持。渲染手写语料，用 ColQwen 嵌入并测检索。与手写 OCR 管线对比。

> Measure ColQwen2.5-v0.2 vs ColQwen3-omni on the same corpus. Which pages does one get right and the other miss? Add a "content class" tag to the index to route by type. ... Prune embeddings aggressively (75%, 90%). Find the compression cliff: the point where ViDoRe nDCG@5 drops below the OCR baseline. ... Build a hybrid: run OCR-then-text and ColQwen in parallel, fuse with RRF, rerank with a cross-encoder. Does the hybrid beat either alone? Where does it help most? ... Swap Qwen3-VL-30B for a smaller VLM (Qwen2.5-VL-7B). Measure the accuracy-per-dollar curve. ... Add handwritten-note support. Render the handwriting corpus, embed with ColQwen, measure retrieval. Compare against a handwriting OCR pipeline.

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|------------------------|
| Late interaction（后期交互） | 「ColPali 式检索」 | 查询 token 独立地对页面 patch 打分；MaxSim 聚合 |
| Multi-vector（多向量） | 「逐 patch 嵌入」 | 每个文档有很多向量，而非一个汇聚向量 |
| MaxSim | 「后期交互打分」 | 对每个查询 token，在文档向量上取最大相似度；再求和 |
| DocPruner | 「patch 压缩」 | 2026 年的剪枝法：保留 50% patch 而精度损失可忽略 |
| ViDoRe v3 | 「文档检索基准」 | 2026 年测量视觉文档检索的标准 |
| Evidence region（证据区域） | 「被引边界框」 | 源页面上定位答案片段的 bbox |
| OCR fallback（OCR 兜底） | 「公式通道」 | 与视觉并行使用的文本管线，用于公式或表格密集页 |

## Further Reading · 延伸阅读

- [ColPali (Illuin Tech) repository](https://github.com/illuin-tech/colpali) — 后期交互文档检索的参考实现
- [ColPali paper (arXiv:2407.01449)](https://arxiv.org/abs/2407.01449) — 奠基方法论文
- [ColQwen family on Hugging Face](https://huggingface.co/vidore) — 生产可用的 checkpoint
- [M3DocRAG (Adobe)](https://arxiv.org/abs/2411.04952) — 多页多模态 RAG 基线
- [Vespa multi-vector tutorial](https://docs.vespa.ai/en/colpali.html) — 参考服务栈
- [Qdrant multi-vector support](https://qdrant.tech/documentation/concepts/vectors/#multivectors) — 备选索引
- [AstraDB multi-vector](https://docs.datastax.com/en/astra-db-serverless/databases/vector-search.html) — 备选托管索引
- [Nougat OCR](https://github.com/facebookresearch/nougat) — 支持公式的 OCR 兜底
