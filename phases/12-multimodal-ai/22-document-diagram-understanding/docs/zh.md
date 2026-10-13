# Document and Diagram Understanding · 文档与图表理解

文档不是普通照片。一份 PDF、科学论文、发票或手写表单，携带着版面、表格、图示、脚注、页眉和语义结构，这些是朴素的图像理解捕捉不到的。VLM 之前的技术栈是一条流水线：Tesseract OCR + LayoutLMv3 + 表格抽取启发式规则。VLM 浪潮用免 OCR（OCR-free）模型取代了它——Donut（2022）、Nougat（2023）、DocLLM（2023）——直接产出结构化标记（structured markup）。到 2026 年，前沿做法就是「把页面图像按 2576px 原生分辨率喂给 Claude Opus 4.7」，结构化标记输出顺手就有。本课解读文档 AI 的三个时代。

> Documents are not photos. A PDF, scientific paper, invoice, or handwritten form has layout, tables, diagrams, footnotes, headers, and semantic structure that plain image understanding cannot capture. The pre-VLM stack was a pipeline: Tesseract OCR + LayoutLMv3 + table-extraction heuristics. The VLM wave replaced that with OCR-free models — Donut (2022), Nougat (2023), DocLLM (2023) — that emit structured markup directly. By 2026 the frontier is just "feed the page image to Claude Opus 4.7 at 2576px native," and the structured-markup output comes for free. This lesson reads the three-era arc of document AI.

**Type:** Build
**Languages:** Python（标准库，版面感知的文档解析器骨架）
**Prerequisites:** Phase 12 · 05（LLaVA）、Phase 5（NLP）
**Time:** ~180 分钟

---

## Learning Objectives · 学习目标

- 讲解文档 AI 的三个时代：OCR 流水线、免 OCR（OCR-free）、VLM 原生（VLM-native）。
- 描述 LayoutLMv3 的三路输入：文本、版面（bbox）、图像块（image patches），以及跨模态统一掩码。
- 比较 Donut（免 OCR，图像 → 标记）、Nougat（科学论文 → LaTeX）、DocLLM（版面感知生成式）、PaliGemma 2（VLM 原生）。
- 为一个新任务（发票、科学论文、手写表单、中文票据）挑选合适的文档模型。

> Explain the three eras of document AI: OCR pipeline, OCR-free, VLM-native.
> Describe LayoutLMv3's three input streams: text, layout (bbox), image patches, with unified masking.
> Compare Donut (OCR-free, image → markup), Nougat (scientific paper → LaTeX), DocLLM (layout-aware generative), PaliGemma 2 (VLM-native).
> Pick a document model for a new task (invoices, scientific papers, handwritten forms, Chinese receipts).

---

## The Problem · 问题在哪

「理解这份 PDF」说起来容易做起来难。信息分布在：

- 文本内容（90% 的信号）。
- 版面（页眉、脚注、侧栏、双栏排版）。
- 表格（行、列、合并单元格）。
- 插图与图示。
- 手写批注。
- 字体与排版（标题 vs 正文）。

原始 OCR 只把文本倒出来，其余全丢。一个关心发票的系统需要知道「Total: $1,245」来自右下角，而不是某个脚注。

> "Understand this PDF" is deceptively hard. The information sits in:
> Raw OCR dumps the text and loses the rest. A system that cares about invoices needs to know "Total: $1,245" came from the bottom-right, not from a footnote.

---

## The Concept · 概念

### Era 1 — OCR pipeline (pre-2021) · 第一代——OCR 流水线（2021 年前）

经典技术栈：

1. PDF → 每页一张图像。
2. Tesseract（或商业 OCR）抽取文本，附带每个词的边界框（bounding box）。
3. 版面分析器识别区块（页眉、表格、段落）。
4. 表格结构识别器解析表格。
5. 领域规则 + 正则表达式抽取字段。

对干净的印刷体有效。遇到手写体、倾斜扫描件、复杂表格、非英文文字就崩。每一种失败模式都需要一条定制的异常处理路径。

> Works for clean printed text. Breaks on handwriting, skewed scans, complex tables, non-English scripts. Every failure mode requires a custom exception path.

---

### TrOCR (2021) · TrOCR（2021）

TrOCR（Li et al.，arXiv:2109.10282）用一个在合成 + 真实文本图像上训练的 transformer 编码器-解码器，取代了 Tesseract 的经典 CNN-CTC。在手写和多语言文本上是干净的胜利。它仍然是一条流水线（先检测、再 TrOCR、再版面），但 OCR 这一步有了质的飞跃。

> TrOCR (Li et al., arXiv:2109.10282) replaced Tesseract's classic CNN-CTC with a transformer encoder-decoder trained on synthetic + real text images. Clean win on handwritten and multilingual text. Still a pipeline (detector then TrOCR then layout), but the OCR step improved dramatically.

---

### Era 2 — OCR-free (2022-2023) · 第二代——免 OCR（2022-2023）

第一批免 OCR 模型的主张是：完全跳过检测，把图像像素直接映射为结构化输出。

Donut（Kim et al.，arXiv:2111.15664）：

- 编码器-解码器 transformer，编码器是 Swin-B。
- 输出可以是表单理解用的 JSON、摘要用的 markdown，或任何任务专属 schema。
- 没有 OCR、没有版面、没有检测。

Nougat（Blecher et al.，arXiv:2308.13418）：

- 专门在科学论文上训练。
- 输出是 LaTeX / markdown。
- 能处理公式、多栏版面、插图。
- 每个 arXiv 解析器都在调用的模型。

这些是专才，不是通才。拿 Donut 去读科学论文会失败；拿 Nougat 去读发票也会失败。

> The first OCR-free models said: skip detection entirely, map image pixels to structured output directly.
> These are specialists, not generalists. Donut on a scientific paper fails; Nougat on an invoice fails.

---

### LayoutLMv3 (2022) · LayoutLMv3（2022）

另一条路线。LayoutLMv3（Huang et al.，arXiv:2204.08387）保留 OCR，但加入版面理解：

- 三路输入：OCR 文本 token、每个 token 的 2D 边界框、图像块。
- 跨三种模态的掩码训练目标（掩码文本、掩码图像块、掩码版面）。
- 下游任务：分类、实体抽取、表格问答。

LayoutLMv3 是基于 OCR 的文档理解的巅峰。在表单和发票上很强。上游需要 OCR。在标准化文档基准上，它是 VLM 之前最好的精度。

> A different track. LayoutLMv3 (Huang et al., arXiv:2204.08387) keeps OCR but adds layout understanding:
> LayoutLMv3 is the peak of OCR-based document understanding. Strong on forms and invoices. Requires OCR upstream. Best pre-VLM accuracy on standardized document benchmarks.

---

### DocLLM (2023) · DocLLM（2023）

DocLLM（Wang et al.，arXiv:2401.00908）是 LayoutLM 的生成式兄弟。它以版面 token 为条件生成自由格式的回答。更适合文档问答；但仍然依赖 OCR 输入。

> DocLLM (Wang et al., arXiv:2401.00908) is LayoutLM's generative sibling. Generates free-form answers conditioned on layout tokens. Better for QA on documents; still depends on OCR input.

---

### Era 3 — VLM-native (2024+) · 第三代——VLM 原生（2024 之后）

2024 年，VLM 好用到可以整条取代流水线了。把整页高分辨率图像喂给 VLM，问问题，拿回答。

- LLaVA-NeXT 的 336-tile AnyRes 能应付小文档。
- Qwen2.5-VL 的动态分辨率原生支持 2048+ 像素。
- Claude Opus 4.7 支持 2576px 文档。
- PaliGemma 2（2025 年 4 月）专门为文档 + 手写体训练。

VLM 原生与 OCR 流水线之间的差距迅速收窄。到 2026 年，VLM 原生在以下场景获胜：

- 场景文字（hand-written + printed，混合文字系统）。
- 带合并单元格的复杂表格。
- 嵌在文本里的数学公式。
- 带文字标注的插图。

OCR 流水线仍然在以下场景获胜：

- 超大规模纯扫描件负载，单页延迟很关键。
- 流水线可靠性（确定性失败 vs VLM 幻觉）。
- 要求 OCR 输出可审计的受监管环境。

> 2024 VLMs became good enough to replace the pipeline entirely. Feed the full page image at high resolution to a VLM, ask the question, get an answer.
> The gap between VLM-native and OCR-pipeline closed rapidly.

---

### The Claude 4.7 / GPT-5 frontier · Claude 4.7 / GPT-5 前沿

在 2576 像素原生输入下，前沿 VLM 做文档理解已接近人类精度。2026 年年初的基准数字：

- DocVQA：Claude 4.7 ~95.1，PaliGemma 2 ~88.4，Nougat ~77.3，流水线版 LayoutLMv3 ~83。
- ChartQA：Claude 4.7 ~92.2，GPT-4V ~78。
- VisualMRC：Claude 4.7 ~94。

闭源模型的领先主要来自分辨率和底座 LLM 规模。7B 的开源模型落后几个百分点，但在追赶。

> At 2576-pixel native input, frontier VLMs do document understanding at near-human accuracy. The benchmark numbers from early 2026:
> The closed-model gap is mostly resolution and base-LLM scale. Open models at 7B are a few points behind but catching up.

---

### Math equations and LaTeX output · 数学公式与 LaTeX 输出

科学论文需要公式有精确的 LaTeX 输出。Nougat 就是在这上面训练的。用 LaTeX 目标训练过的 VLM（Qwen2.5-VL-Math、Nougat 衍生模型）能产出可用的 LaTeX。没有做过显式 LaTeX 训练的 VLM，转写结果可读但不精确。

2026 年的科学论文流水线：先用 Nougat 过一遍 PDF，再让 VLM 处理棘手的页面。

> Scientific papers need exact LaTeX output for equations. Nougat was trained on this. VLMs trained with LaTeX targets (Qwen2.5-VL-Math, Nougat derivatives) produce usable LaTeX. Without explicit LaTeX training, VLMs produce readable but imprecise transcriptions.
> For scientific-paper pipelines in 2026: chain Nougat on the PDF, then a VLM on tricky pages.

---

### Handwriting · 手写体

仍然是最难的子任务。印刷 + 手写混合（医生病历、填写过的表单）是 OCR 流水线在成本上仍能赢过 VLM 的地方。纯手写场景的 VLM 在进步（Claude 4.7、PaliGemma 2）。

> Still the hardest sub-task. Mixed printed + handwritten (doctors' notes, filled forms) is where OCR pipelines still beat VLMs for cost. Handwritten-only VLMs are improving (Claude 4.7, PaliGemma 2).

---

### 2026 recipe · 2026 年选型配方

一个新的文档 AI 项目：

- 大规模纯印刷发票：LayoutLMv3 + 规则，成本最优。
- 混合文档（科学论文 + 手写 + 表单）：VLM 原生（PaliGemma 2 或 Qwen2.5-VL）。
- arXiv 全量入库：数学用 Nougat，插图用 VLM。
- 受监管场景：OCR 流水线 + VLM 校验器做交叉核对。

> For a new document-AI project:
> - Pure-printed invoices at scale: LayoutLMv3 + rules, cost-efficient.
> - Mixed documents (scientific + handwritten + forms): VLM-native (PaliGemma 2 or Qwen2.5-VL).
> - Full arXiv ingestion: Nougat for math, VLM for figures.
> - Regulatory: OCR pipeline + VLM validator for cross-check.

```figure
mm-doc-layout
```

---

## Use It · 实战用法

`code/main.py`：

- 一个玩具版版面感知分词器（layout-aware tokenizer）：给定（文本, bbox）对，产出 LayoutLMv3 风格的输入。
- 一个 Donut 风格的任务 schema 生成器：表单用的 JSON 模板。
- 一份单页 token 预算对比：OCR 流水线、Donut、Nougat、VLM 原生四种方案。

---

## Ship It · 交付

本课产出 `outputs/skill-document-ai-stack-picker.md`。给定一个文档 AI 项目（领域、规模、质量、监管），在 OCR 流水线、免 OCR 专才模型、VLM 原生三者之间做选型。

> This lesson produces `outputs/skill-document-ai-stack-picker.md`. Given a document-AI project (domain, scale, quality, regulatory), picks between OCR pipeline, OCR-free specialist, and VLM-native.

---

## Exercises · 练习

1. 你的项目每天要处理 1000 万张发票。哪套技术栈能在不丢精度的前提下把单页成本压到最低？

2. 为什么 LayoutLMv3 在表单问答上胜过纯 CLIP 式 VLM，却在场景文字上落后？bbox 这一路输入放弃了什么？

3. Nougat 生成 LaTeX。提出一个 VLM 原生输出在 LaTeX 保真度上胜过 Nougat 的测试用例，再提出一个 Nougat 胜出的用例。

4. 读 PaliGemma 2 论文（Google, 2024）。相比 PaliGemma 1，让文档精度提升的关键训练数据增量是什么？

5. 设计一个监管安全的混合方案：OCR 流水线为主，VLM 做二次交叉校验。两者不一致时如何裁决？

---

## Key Terms · 术语表

| 术语 | 通俗说法 | 实际含义 |
|------|-----------------|------------------------|
| OCR pipeline | 「Tesseract 那一套」 | 分阶段流水线：detect -> OCR -> layout -> rules；确定性强但脆弱 |
| OCR-free | 「Donut 那一套」 | 图像直出结果的 transformer，跳过显式 OCR；单一模型 |
| Layout-aware | 「LayoutLM」 | 输入包含每个 token 的 bbox 坐标；跨模态统一掩码 |
| VLM-native | 「前沿 VLM」 | 把页面图像高分辨率直接喂给 Claude/GPT/Qwen 等 VLM；无流水线 |
| DocVQA | 「文档基准」 | 文档视觉问答（VQA）标准；被引用最多的分数 |
| Markup output | 「LaTeX / MD」 | 用结构化输出格式替代自由文本；支撑下游自动化 |

---

## Further Reading · 延伸阅读

- [Li et al. — TrOCR (arXiv:2109.10282)](https://arxiv.org/abs/2109.10282)
- [Blecher et al. — Nougat (arXiv:2308.13418)](https://arxiv.org/abs/2308.13418)
- [Huang et al. — LayoutLMv3 (arXiv:2204.08387)](https://arxiv.org/abs/2204.08387)
- [Kim et al. — Donut (arXiv:2111.15664)](https://arxiv.org/abs/2111.15664)
- [Wang et al. — DocLLM (arXiv:2401.00908)](https://arxiv.org/abs/2401.00908)
