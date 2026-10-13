# Multimodal RAG and Cross-Modal Retrieval · 多模态 RAG 与跨模态检索

视觉原生文档 RAG 只是一个切片。生产级多模态 RAG 走得更宽——跨文本、图像、音频、视频检索，服务诸如行程规划（「帮我找一家安静、有自然采光、做纯素早午餐的店」）、医疗分诊（「这张照片加这些症状对应什么伤」）、电商（「和我这张自拍相似、且我有码的穿搭」）、现场维修（「诊断这个引擎声音加上零件照片」）之类的工作流。2025 年的三篇综述——Abootorabi et al.、Mei et al.、Zhao et al.——把这些子问题规范化：跨模态检索（cross-modal retrieval）、检索融合、生成接地（generation grounding）、多模态评测。本课解读这三篇综述并设计一条生产级流水线。

> Vision-native document RAG is one slice. Production multimodal RAG goes wider — retrieving across text, images, audio, and video for workflows like trip planning ("find me a quiet vegan brunch with natural light"), medical triage ("what injury matches this photo + these notes"), e-commerce ("outfits similar to this selfie, in my size"), and field service ("diagnose this engine sound plus photo of the part"). Three 2025 surveys — Abootorabi et al., Mei et al., Zhao et al. — codified the sub-problems: cross-modal retrieval, retrieval fusion, generation grounding, multimodal evaluation. This lesson reads the surveys and designs a production pipeline.

**Type:** Build
**Languages:** Python（标准库，带融合的跨模态检索器 + 接地生成器）
**Prerequisites:** Phase 12 · 23（ColPali）、Phase 11（RAG 基础）
**Time:** ~180 分钟

---

## Learning Objectives · 学习目标

- 设计跨模态检索：文本 → 图像、图像 → 文本、音频 → 视频等。
- 比较三种融合策略：分数融合（score fusion）、基于注意力的融合、MoE 融合。
- 解释生成接地（generation grounding）：当「来源」是多种模态的混合时，「引用你的出处」长什么样。
- 说出 2025 年三篇权威多模态 RAG 综述及其子问题分类法。

> Design cross-modal retrieval: text → image, image → text, audio → video, etc.
> Compare three fusion strategies: score fusion, attention-based fusion, MoE fusion.
> Explain generation grounding: what "cite your sources" looks like when sources are a mix of modalities.
> Name the three canonical multimodal RAG surveys of 2025 and their sub-problem taxonomy.

---

## The Problem · 问题在哪

单模态 RAG 是已被解决的模式：嵌入查询、嵌入文本块、检索、塞进 LLM。多模态 RAG 则要求：

1. 多个检索头（每种模态都要有兼容空间里的嵌入）。
2. 跨模态融合检索结果。
3. 生成接地：引用跨模态的来源。
4. 覆盖跨模态信号的评测指标。

2025 年的综述都收敛到同一套分类法。

> Single-modality RAG is a solved pattern: embed query, embed chunks, retrieve, stuff into LLM.
> The 2025 surveys all arrive at the same taxonomy.

---

## The Concept · 概念

### Cross-modal retrieval · 跨模态检索

给定 A 模态的查询，检索 B 模态的文档。三种模式：

1. 共享嵌入空间。CLIP 和 CLAP 在共享空间里产出文本 + 图像 / 文本 + 音频嵌入。跨模态余弦相似度可以直接用。局限于 CLIP 训练过的模态对。

2. 每模态编码器 + 翻译。文本编码器 + 图像编码器，外加一个在两个空间之间映射的小翻译模块。Gupta et al. 的 Sen2Sen 和其他 2024 年的设计。灵活但增加复杂度。

3. VLM 当编码器。用 VLM 的隐藏状态（hidden states）做检索表示。VLM 支持的任何模态都能用。质量更高，也更贵。

选型：文本+图像用 CLIP / SigLIP 2；文本+音频用 CLAP；追求前沿质量的跨模态用 VLM 隐藏状态。

> Retrieve documents of modality B given a query of modality A. Three patterns:
> Choice: CLIP / SigLIP 2 for text+image; CLAP for text+audio; VLM-hidden-states for cross-modal at frontier quality.

---

### Fusion strategies · 融合策略

你检索到 10 条结果：5 张图像、3 段文本、2 段音频。怎么合并？

分数融合（score fusion，最便宜）。每种模态各有检索器，各自返回分数。先在模态内部归一化，再求和。简单，常常就够用。

基于注意力的融合。把所有检索结果拼接起来，让一个小的注意力网络给它们加权。需要训练。

MoE 融合。门控网络把请求路由到模态专属的专家。不同类型的查询走不同的路由——视觉类问题会给图像更高的权重。

生产默认：分数融合，并稍微偏向查询的主导模态。如果你的领域里 A/B 测试显示明显优势，再升级到 MoE。

> You retrieved 10 results: 5 images, 3 text passages, 2 audio clips. How do you merge?
> Production default: score fusion with a slight bias toward the query's dominant modality. Upgrade to MoE if A/B shows clear wins on your domain.

---

### Generation grounding · 生成接地

LLM 应该为每个论断引用是哪条检索结果支撑的。多模态场景下：

- 文本来源：标准引用 `[1]`。
- 图像来源：`[img 3]` 加一句简短说明。
- 音频：`[audio 2 at 0:34]`。

用「接地感知」的数据训练生成器：训练目标里的每个论断都打上来源索引。推理时模型自然就会带出引用。

> The LLM should cite which retrieved item drove each claim.
> Train the generator with grounding-aware data: each claim in the training target is tagged with the source index. At inference, the model naturally emits citations.

---

### The 2025 surveys · 2025 年的三篇综述

Abootorabi et al.（arXiv:2502.08826，"Ask in Any Modality"）：多模态 RAG 的分类法。覆盖检索、融合、生成。覆盖面最广。

Mei et al.（arXiv:2504.08748，"A Survey of Multimodal RAG"）：聚焦子任务基准与失败模式。对设计评测有用。

Zhao et al.（arXiv:2503.18016）：视觉方向的综述。对 ColPali 一系工作着墨最多。

三篇都读完，你就掌握了截至 2025 年春季的技术水平。大多数子问题仍是开放问题。

> Abootorabi et al. (arXiv:2502.08826, "Ask in Any Modality"): taxonomy for multimodal RAG. Covers retrieval, fusion, generation. Broadest coverage.
> Reading all three gives you the state of the art as of spring 2025. Most of the sub-problems are still open.

---

### MuRAG — the foundational paper · MuRAG——奠基论文

MuRAG（Chen et al.，2022）是第一个多模态 RAG。它从多模态知识库里检索图像 + 文本并生成回答。在 VLM 浪潮到来之前就证明了可行性。现代系统（REACT、VisRAG、M3DocRAG）都建立在它之上。

> MuRAG (Chen et al., 2022) was the first multimodal RAG. Retrieved image + text from a multimodal KB, generated answers. Showed feasibility before the VLM wave. Modern systems (REACT, VisRAG, M3DocRAG) build on it.

---

### A production trip-planner example · 一个生产级行程规划示例

查询：「帮我找一家安静、有自然采光、做纯素早午餐的店。」（"find me a quiet vegan brunch with natural light."）

流水线：

1. 分解查询。"quiet" → 音频 / 评论关键词；"vegan brunch" → 菜单项；"natural light" → 图像特征。
2. 按模态检索：
   - 在评论上做文本检索："vegan brunch, quiet ambiance."
   - 在餐厅照片上做图像检索："natural light, airy."
   - 在环境音片段上做音频检索："low decibel, no music."
3. 融合分数。每家餐厅得到一个综合分。
4. top-k 餐厅 → 连同全部证据交给 VLM 生成器 → 带引用的回答。

这已经远超文本 RAG。每种模态都在补充纯文本看不见的信号。

> This is well beyond text-RAG. Each modality adds signal that text alone misses.

---

### Agentic multimodal RAG · Agentic 多模态 RAG

多跳（multi-hop）：如果第一轮检索没有返回高置信度的答案，LLM 就改写查询再检索一次。Phase 14 的 agentic RAG 模式在这里适用。例子：

- 先检索 top-10 → LLM 判断「太吵，过滤到 <40 dB」→ 重新检索。
- 检索图像 → LLM 发现其中一张有菜单 → 检索菜单文本 → 回答。

复杂度增加，但能处理单轮检索搞不定的查询。

> Multi-hop: if the first retrieval does not return high-confidence answers, the LLM reformulates and retrieves again. Agentic RAG patterns from Phase 14 apply here.
> Adds complexity but handles queries that single-shot retrieval cannot.

---

### Evaluation · 评测

跨模态评测还不成熟。常用的代理指标：

- 每种模态的 Recall@k。
- 融合后 top-k 准确率。
- 人工评判的端到端满意度。
- 任务型指标（完成预订数、成交数）。

没有覆盖所有模态的标准基准。大多数论文都在领域专属任务上评测。

> Cross-modal evaluation is still immature. Common proxies:
> No standard benchmark spans all modalities. Most papers evaluate on domain-specific tasks.

```figure
contrastive-matrix
```

---

## Use It · 实战用法

`code/main.py`：

- 三个模拟检索器（文本、图像、音频），作用在一个共享的餐厅语料上。
- 分数融合：用可配置权重合并各模态分数。
- 一个生成器桩（stub），产出带引用的最终回答。
- 一个简单的 agentic 循环：置信度低时改写查询重试。

---

## Ship It · 交付

本课产出 `outputs/skill-multimodal-rag-designer.md`。给定带多模态查询流程的产品规格，设计检索器、融合、生成器与评测。

> This lesson produces `outputs/skill-multimodal-rag-designer.md`. Given a product spec with a multimodal query flow, designs retrievers, fusion, generator, and evaluation.

---

## Exercises · 练习

1. 设计一个医疗分诊多模态 RAG：查询 = 伤情照片 + 文本症状。各模态分别从什么知识库检索？

2. 分数融合是简单的加权和。它有什么 MoE 融合能避免的失败模式？

3. 读 Abootorabi et al. 的分类法（第 3 节）。三个权威子问题是什么？它们如何映射到你选的产品？

4. 为行程规划多模态 RAG 设计一份评测规格。哪些指标覆盖图像召回、音频召回和综合正确性？

5. Agentic 多跳 RAG 每一往返都有延迟税。查询难度到什么程度，精度收益才值得付这个延迟？

---

## Key Terms · 术语表

| 术语 | 通俗说法 | 实际含义 |
|------|-----------------|------------------------|
| Cross-modal retrieval | 「用一个模态查询，检回另一个模态」 | 文本查询检回图像；图像查询检回文本；需要共享空间或翻译器 |
| Score fusion | 「合并分数」 | 各模态检索分数的加权和；最简单的融合 |
| MoE fusion | 「按模态路由的专家」 | 门控网络按查询决定信任哪个模态的分数 |
| Grounded generation | 「引用你的出处」 | 回答中的每个论断都打上来源索引 |
| MuRAG | 「第一个多模态 RAG」 | 2022 年确立多模态 RAG 模式的论文 |
| Agentic multi-hop | 「改写重试」 | 首轮置信度低时 LLM 重新查询检索器 |

---

## Further Reading · 延伸阅读

- [Abootorabi et al. — Ask in Any Modality (arXiv:2502.08826)](https://arxiv.org/abs/2502.08826)
- [Mei et al. — A Survey of Multimodal RAG (arXiv:2504.08748)](https://arxiv.org/abs/2504.08748)
- [Zhao et al. — Vision RAG Survey (arXiv:2503.18016)](https://arxiv.org/abs/2503.18016)
- [Chen et al. — MuRAG (arXiv:2210.02928)](https://arxiv.org/abs/2210.02928)
- [Liu et al. — REACT (arXiv:2301.10382)](https://arxiv.org/abs/2301.10382)
