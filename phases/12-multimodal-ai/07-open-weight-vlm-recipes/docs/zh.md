# Open-Weight VLM Recipes: What Actually Matters · 开源权重 VLM 配方：什么才真正重要

> 2024-2026 年的开源权重 VLM 文献是一片消融表的森林。Apple 的 MM1 测试了图像编码器、连接器和数据配比的 13 种组合。Allen AI 的 Molmo 证明了详尽的人工 caption 胜过 GPT-4V 蒸馏。Cambrian-1 跑了 20 多个编码器的对比。Idefics2 把五轴设计空间形式化。Prismatic VLMs 在受控基准上比较了 27 种训练配方。从这片噪声中，有一小组结论跨越论文成立：图像编码器比连接器架构更重要，数据配比比两者都重要，详尽的人工 caption 胜过蒸馏的合成数据。本课替你把那些表读了一遍。
>
> The 2024-2026 open-weight VLM literature is a forest of ablation tables. Apple's MM1 tested 13 combinations of image encoder, connector, and data mix. Allen AI's Molmo proved detailed human captions beat GPT-4V distillation. Cambrian-1 ran 20+ encoder comparisons. Idefics2 formalized the five-axis design space. Prismatic VLMs compared 27 training recipes on a controlled benchmark. Out of all that noise, a small set of results holds across papers: image encoder matters more than connector architecture, data mixture matters more than either, and detailed human captions beat distilled synthetic data. This lesson reads those tables so you do not have to.

**类型:** Learn + lab
**语言:** Python（标准库，消融表解析器 + 配方选型器）
**先修:** Phase 12 · 05（LLaVA baseline）
**时长:** ~180 分钟

## Learning Objectives · 学习目标

- 说出 VLM 的五轴设计空间：图像编码器、连接器、LLM、数据配比、分辨率调度。
- 读一张 MM1 / Idefics2 / Cambrian-1 的消融表，预测哪个旋钮会推动哪个基准。
- 在给定算力预算和任务组合下，为新 VLM 挑出一套配方（编码器、连接器、数据、分辨率）。
- 解释为什么在相同 token 数下，详尽的人工 caption 胜过 GPT-4V 蒸馏。

> Name the five-axis VLM design space: image encoder, connector, LLM, data mix, resolution schedule.
> Read an MM1 / Idefics2 / Cambrian-1 ablation table and predict which knob moves a given benchmark.
> Pick a recipe (encoder, connector, data, resolution) for a new VLM given a compute budget and task mix.
> Explain why detailed human captions beat GPT-4V distillation at the same token count.

## The Problem · 问题在哪

开源权重的 VLM 已经有数百个。「好」与「最先进」之间的差距，大多不在架构，而在数据、分辨率调度和编码器选择。当你的模型表现不佳时，知道先拧哪个旋钮，能帮你省下一次 500 万 GPU 小时的错误。

2023 年这一波（LLaVA-1.5、InstructBLIP、MiniGPT-4）跑在 caption 对预训练 + LLaVA-Instruct-150k 上。是不错的基线。MMMU 大约停在 35%。

2024 年这一波（MM1、Idefics2、Molmo、Cambrian-1、Prismatic VLMs）做了穷举式消融。结果既出人意料又非常实用。

> Hundreds of open-weight VLMs exist. Most of the gap between "good" and "state-of-the-art" is not architecture. It is data, resolution schedule, and encoder choice. Knowing which knob to turn first when your model underperforms saves you a 5-million-GPU-hour mistake.
> The 2023 wave (LLaVA-1.5, InstructBLIP, MiniGPT-4) ran on caption-pair pretraining + LLaVA-Instruct-150k. Good baseline. Topped out around MMMU 35%.
> The 2024 wave (MM1, Idefics2, Molmo, Cambrian-1, Prismatic VLMs) ran exhaustive ablations. Results were surprising and practical.

## The Concept · 核心概念

### The five-axis design space · 五轴设计空间

Idefics2（Laurençon 等，2024）给这些轴命了名：

1. 图像编码器。CLIP ViT-L/14、SigLIP SO400m/14、DINOv2 ViT-g/14、InternViT-6B。编码器在 patch 大小、分辨率和预训练目标上各不相同。
2. 连接器。MLP（2-4 层）、Q-Former（32 query + cross-attn）、Perceiver Resampler（64 query）、C-Abstractor（卷积 + 双线性池化）。
3. 语言模型。Llama-3 8B / 70B、Mistral 7B、Phi-3、Gemma-2、Qwen2.5。LLM 规模是参数成本的大头。
4. 训练数据。Caption 对（CC3M、LAION）、交错数据（OBELICS、MMC4）、指令数据（LLaVA-Instruct、ShareGPT4V、PixMo、Cauldron）。
5. 分辨率调度。固定 224/336/448、AnyRes、原生动态。训练中爬升或保持恒定。

每个生产级 VLM 都在每根轴上做了选择。MMMU 分数的大部分方差由轴 1、4、5 解释——跟你选了哪个连接器关系不大。

> Idefics2 (Laurençon et al., 2024) named the axes: ... Every production VLM makes a choice on each axis. Most of the variance in MMMU scores is explained by axes 1, 4, and 5 — not by which connector you picked.

### Axis 1: encoder > connector · 轴 1：编码器 > 连接器

MM1 第 3.2 节显示：把 CLIP ViT-L/14 换成 SigLIP SO400m/14，MMMU 涨 3 个点以上；把连接器从 MLP 换成 Perceiver Resampler，涨不到 1 个点。Idefics2 复现了这一结论：SigLIP > CLIP，在相同 token 数下 Q-Former ≈ MLP ≈ Perceiver。

Cambrian-1 的「Cambrian Vision Encoders Match-Up」（Tong 等，2024）在一个视觉中心基准（CV-Bench）上跑了 20 多个编码器。榜首是 DINOv2 和 SigLIP 的混战；CLIP 居中；ImageBind 和 ViT-MAE 偏低。从 CLIP ViT-L 到 DINOv2 ViT-g/14 的差距在 CV-Bench 上约 5-7 个点。

2026 年开源 VLM 的默认编码器是 SigLIP 2 SO400m/14（语义 + 密集特征），有时与 DINOv2 ViT-g/14 特征拼接使用（Cambrian 的「Spatial Vision Aggregator」就是这么干的）。

> MM1 Section 3.2 showed: swapping from CLIP ViT-L/14 to SigLIP SO400m/14 added 3+ points MMMU. Swapping the connector from MLP to Perceiver Resampler added less than 1 point. Idefics2 replicated: SigLIP > CLIP, Q-Former ≈ MLP ≈ Perceiver at the same token count. ... The 2026 default encoder for open VLMs is SigLIP 2 SO400m/14 for semantic + dense features, sometimes concatenated with DINOv2 ViT-g/14 features (Cambrian's "Spatial Vision Aggregator" does this).

### Axis 2: connector design is a wash · 轴 2：连接器设计打平

MM1、Idefics2、Prismatic 和 MM-Interleaved 得出了同一个结论：固定视觉 token 数时，连接器架构几乎无关紧要。在相同 token 预算下，mean-pool patch 上的 2 层 MLP，与 32 query 的 Q-Former 表现相差不到 1 个点。

真正要紧的是 token 数。更多视觉 token = 更多 LLM 算力 = 性能更好，直到某一点之后收益递减。每图 64 token 对 OCR 太少。576-1024 token 是多数开源 VLM 的甜点区。2048+ 只对文档和图表有帮助。

Q-Former vs MLP 是成本问题，不是质量问题：无论图像分辨率多大，Q-Former 都把 token 封顶在 32-64；MLP 则吐出全部 patch token。高分辨率输入时，Q-Former 省 LLM 上下文；低分辨率时，差异只是噪声。

> MM1, Idefics2, Prismatic, and MM-Interleaved all reached the same conclusion: at a fixed visual-token count, connector architecture barely matters. ... What does matter is the token count. More visual tokens = more LLM compute = better performance up to a point, then diminishing returns. ... Q-Former vs MLP is a cost question, not a quality question: Q-Former caps tokens at 32-64 regardless of image resolution; MLP emits all patch tokens.

### Axis 3: LLM size sets the ceiling · 轴 3：LLM 规模决定天花板

把 LLM 从 7B 翻倍到 13B，在每一篇 VLM 论文里都能稳定地在 MMMU 上涨 2-4 个点。到 70B 时，大多数基准都会饱和。VLM 的多模态推理天花板就是 LLM 的文本推理天花板——视觉编码器只能喂养它，不能替它推理。

这就是 Qwen2.5-VL-72B 和 Claude Opus 4.7 能碾压 MMMU-Pro 和 ScreenSpot-Pro 的原因：语言大脑足够大。一个 7B VLM 靠聪明的连接器设计，替代不了 70B VLM。

> Doubling the LLM from 7B to 13B reliably adds 2-4 points on MMMU across every VLM paper. At 70B you saturate most benchmarks. The VLM's multimodal reasoning ceiling is the LLM's text reasoning ceiling — the visual encoder can only feed it, not reason for it.
> This is why Qwen2.5-VL-72B and Claude Opus 4.7 crush MMMU-Pro and ScreenSpot-Pro: the language brain is huge. A 7B VLM cannot substitute for a 70B VLM through clever connector design.

### Axis 4: data — detailed human captions beat distillation · 轴 4：数据——详尽的人工 caption 胜过蒸馏

Molmo + PixMo（Deitke 等，2024）是 2024 年人人都该读的结果。Allen AI 让人工标注员用 1-3 分钟的密集语音转文字来描述图像，得到 712K 张密集标注的图像。训练数据里没有任何 GPT-4V 蒸馏。

Molmo-72B 在 11 个基准中的 11 个上击败 Llama-3.2-90B-Vision。差距不在架构——在 caption 质量。详尽的人工 caption 每张图携带的信息是短网络 caption 的 5-10 倍，而且在 GPT-4V 蒸馏产生幻觉的地方保持事实接地。

ShareGPT4V（Chen 等，2023）和 Cauldron（Idefics2）用人工 + GPT-4V 混合 caption 沿用了同一套打法。趋势明确：对 2026 年的前沿而言，caption 密度 > caption 数量 > 蒸馏便利性。

> Molmo + PixMo (Deitke et al., 2024) is the 2024 result everyone should read. Allen AI had human annotators describe images in 1-3 minute dense speech-to-text passes, yielding 712K densely-captioned images. No GPT-4V distillation anywhere in the training data.
> Molmo-72B beat Llama-3.2-90B-Vision on 11 of 11 benchmarks. The delta is not architecture — it is caption quality. Detailed human captions contain 5-10x more information per image than short web captions and stay factually grounded where GPT-4V distillation hallucinates. ... The trend is clear: for the 2026 frontier, caption density > caption quantity > distillation convenience.

### Axis 5: resolution and its schedule · 轴 5：分辨率及其调度

Idefics2 的消融：384 → 448 涨 1-2 个点。448 → 980 加图像切分（AnyRes）在 OCR 基准上再涨 3-5 个点。恒定分辨率的训练在中段精度上原地踏步；分辨率爬升（224 起步，448 或原生收尾）训得更快、终点更高。

Cambrian-1 跑了一个分辨率 vs token 的权衡：固定算力下，你可以用低分辨率换更多 token，或用高分辨率配更少 token。OCR 是高分辨率赢；通用场景理解是低分辨率多 token 赢。

2026 年的生产配方：阶段 1 固定 384 训练，阶段 2 用动态分辨率冲到 1280（针对 OCR 重的任务）。

> Idefics2's ablations: 384 -> 448 adds 1-2 points. 448 -> 980 with image splitting (AnyRes) adds another 3-5 on OCR benchmarks. Flat resolution training plateaus at medium accuracy; resolution ramping (start 224, finish 448 or native) trains faster and ends higher. ... The 2026 production recipe: train Stage 1 at 384 fixed, Stage 2 with dynamic resolution up to 1280 for OCR-heavy tasks.

### The Prismatic controlled comparison · Prismatic 的受控对比

Prismatic VLMs（Karamcheti 等，2024）是那篇控制了所有轴的论文。同一个 13B LLM、同一份指令数据、同一套评估——每次只动一根轴。结果：

- 每图视觉 token 数解释了约 60% 的方差。
- 编码器选择解释约 20%。
- 连接器架构解释约 5%。
- 其余一切（数据配比、调度器、学习率）占剩下的约 15%。

这是一个粗分解，但它是文献里对「我该先消融什么」最干净的回答。

> Prismatic VLMs (Karamcheti et al., 2024) is the paper that controlled all the axes. Same 13B LLM, same instruction data, same evaluation — only one axis varies at a time. Results: ... This is a rough decomposition, but it is the cleanest answer to "what should I ablate first" in the literature.

### A picker for 2026 · 2026 年的选型器

综合以上证据，2026 年新项目的默认开源 VLM 配方：

- 编码器：原生分辨率 + NaFlex 的 SigLIP 2 SO400m/14；若需要分割/定位，拼接 DINOv2 ViT-g/14 的密集特征。
- 连接器：patch token 上的 2 层 MLP。除非被 token 卡死，否则跳过 Q-Former。
- LLM：Qwen2.5 / Llama-3.1 / Gemma 2，求成本用 7B，求质量用 70B，按目标延迟挑选。
- 数据：PixMo + ShareGPT4V + Cauldron，再用任务特定的指令数据补足。
- 分辨率：动态（长边最小 256、最大 1280 像素）。
- 调度：阶段 1 对齐（只训 projector），阶段 2 全量微调，阶段 3 任务特定微调。

这些默认值里的每一条，都能追溯到本课末尾引用的论文中的某次实测消融。

> Given the evidence, the default open-VLM recipe for a new project in 2026: ... Every one of those defaults traces back to a measured ablation in the papers cited at the end of this lesson.

```figure
l5-vlm-recipe-knobs
```

## Use It · 实战用法

`code/main.py` 是一个消融表解析器加配方选型器。它编码了（精简版）MM1 和 Idefics2 的消融表，支持查询：

- 「给定预算 X 和任务 Y，哪套配方会赢？」
- 「如果我在 7B Llama 上把 SigLIP 换成 CLIP，MMMU 预期变化多少？」
- 「要得到一个 80% 置信度的答案，该先消融哪根轴？」

输出是带预期基准增量的配方排名，外加一条「先消融它」的建议。

> `code/main.py` is an ablation table parser and recipe picker. It encodes the MM1 and Idefics2 ablation tables (condensed) and lets you query: ... The output is a ranked recipe list with expected benchmark deltas and an "ablate first" recommendation.

## Ship It · 交付

本课产出 `outputs/skill-vlm-recipe-picker.md`。给定目标任务组合、算力预算和延迟目标，它产出一套完整配方（编码器、连接器、LLM、数据配比、分辨率调度），并为每个选择附上佐证消融的引用。免得每个新 VLM 项目启动时，都把 Idefics2 的消融表重新发明一遍。

> This lesson produces `outputs/skill-vlm-recipe-picker.md`. Given a target task mix, a compute budget, and a latency target, it emits a full recipe (encoder, connector, LLM, data mix, resolution schedule) with citations to the ablation that justifies each choice. Stops engineers from reinventing the Idefics2 ablation table every time a new VLM project starts.

## Exercises · 练习

1. 读 MM1 第 3.2 节。固定 2B LLM、5000 万张图的预算下，哪个编码器赢？换到 13B LLM，答案会翻转吗？为什么？

2. Cambrian-1 发现拼接 DINOv2 + SigLIP 在视觉中心基准上胜过任何单独一个，但在 MMMU 上没有增益。预测哪些基准会涨、哪些原地不动。

3. 你的目标是跑在 2B LLM 上的移动端 UI agent。挑出编码器、连接器、分辨率和数据配比。用一张具体的消融表为每个选择辩护。

4. Molmo 发布了 4B 和 72B 两个模型。4B 能与闭源 7B VLM 掰手腕；72B 在 11/11 个基准上击败 Llama-3.2-90B-Vision。这对「LLM 规模平台期」假说说明了什么？

5. 设计一张消融表，在 7B VLM 上把数据配比质量与编码器质量隔离开。最少需要多少次训练？给出四根轴的设置。

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|-----------------|------------------------|
| Ablation | "拧一个旋钮" | 多次训练，每次只在设计空间的一根轴上不同，其余全部保持不变 |
| Connector | "桥" / "projector" | 把视觉编码器输出映射进 LLM token 空间的可训练模块（MLP、Q-Former、Perceiver） |
| Detailed human caption | "密集 caption" | 人工撰写的多句描述（通常 80-300 token），比网页 alt 文本更丰富 |
| Distillation | "GPT-4V caption" | 由更强的闭源 VLM 生成的训练数据；方便，但容易继承幻觉 |
| AnyRes / dynamic res | "高分辨率路径" | 通过平铺或 M-RoPE 喂入超过编码器原生分辨率图像的策略 |
| Resolution ramp | "课程表" | 从低分辨率起步、逐步升高的训练调度，加快对齐的学习 |
| Vision-centric bench | "CV-Bench / BLINK" | 强调细粒度视觉感知、而非语言重度推理的评测 |
| PixMo | "Molmo 的数据" | Allen AI 的 712K 密集标注图像数据集；人工语音转写成的密集 caption |

## Further Reading · 延伸阅读

- [McKinzie et al. — MM1 (arXiv:2403.09611)](https://arxiv.org/abs/2403.09611)
- [Laurençon et al. — Idefics2 / What matters building VLMs (arXiv:2405.02246)](https://arxiv.org/abs/2405.02246)
- [Deitke et al. — Molmo and PixMo (arXiv:2409.17146)](https://arxiv.org/abs/2409.17146)
- [Tong et al. — Cambrian-1 (arXiv:2406.16860)](https://arxiv.org/abs/2406.16860)
- [Karamcheti et al. — Prismatic VLMs (arXiv:2402.07865)](https://arxiv.org/abs/2402.07865)
