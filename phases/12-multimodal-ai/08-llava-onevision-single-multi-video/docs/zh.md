# LLaVA-OneVision: Single-Image, Multi-Image, Video in One Model · LLaVA-OneVision：单图、多图、视频，一个模型全包

> 在 LLaVA-OneVision（Li et al.，2024 年 8 月）之前，开源 VLM 世界分成几条独立路线：单图有 LLaVA-1.5，多图有 Mantis、VILA 一类，视频有 Video-LLaVA、Video-LLaMA 一类。各家赢自己的基准、输别人的。LLaVA-OneVision 主张：一份课程就能把一个模型训到通吃三个场景，而且涌现的任务迁移效应（单图技能输出到视频、多图推理输出到单图）胜过一队专才之和。配方看似简单：一个跨场景保持恒定的视觉 token 预算，加一条从单图走到 OneVision（多图）再到视频的显式课程。本课读懂这份预算、这条课程和那些涌现行为。

> Before LLaVA-OneVision (Li et al., August 2024) the open-VLM world had separate lineages: LLaVA-1.5 for single images, multi-image models like Mantis and VILA, video models like Video-LLaVA and Video-LLaMA. Each won its benchmark and failed at the others. LLaVA-OneVision argued a single curriculum could train one model to dominate all three scenarios, and that the emergent task-transfer effects (single-image skills exported to video, multi-image reasoning exported to single-image) beat the sum of specialists. The recipe is deceptively simple: a visual-token budget that stays constant across scenarios, plus an explicit curriculum that moves from single-image to OneVision (multi-image) to video. This lesson reads the budget, the curriculum, and the emergent behaviors.

**Type:** Build
**Languages:** Python (stdlib, token budget solver + curriculum planner)
**Prerequisites:** Phase 12 · 05 (LLaVA), Phase 12 · 06 (any-resolution)
**Time:** ~180 minutes

## Learning Objectives · 学习目标

- 设计一个在单图、多图、视频输入之间保持恒定的视觉 token 预算。
- 排出一份训练课程顺序，让单图技能迁移到视频而不发生灾难性遗忘。
- 解释为什么只要课程安排得当，同等参数量下一个模型能打败一队专才模型。
- 说出 LLaVA-OneVision 报告的三种涌现能力：多相机推理、set-of-mark 提示、iPhone 截图 agent。

> Design a visual-token budget that holds constant across single-image, multi-image, and video inputs.
> Order a training curriculum that transfers skills from single-image to video without catastrophic forgetting.
> Explain why a single model beats specialists at the same parameter count when curriculum is done right.
> Name the three emergent capabilities reported by LLaVA-OneVision: multi-camera reasoning, set-of-mark prompting, iPhone-screenshot agent.

## The Problem · 问题在哪

单图、多图、视频对模型的压力各不相同。

单图需要高分辨率 token（AnyRes，约 2880 个视觉 token）来抓住 OCR 和精细细节。每样本预算：1 张图，2880 个 token。

多图需要多张中等分辨率的图（每张约 576 个 token），让跨图推理装得进上下文。每样本预算：4-8 张图，每张 576，共 2300-4600 个 token。

视频需要大量低分辨率帧（池化后每帧约 196 个 token）来捕捉时间动态。每样本预算：8-32 帧，每帧 196，共 1600-6200 个 token。

如果你分开训多个模型，每种场景挑一个预算就行。如果要训一个模型，你就需要这份预算能在各场景之间合理伸缩、又不撑爆上下文。

在 OneVision 之前，默认答案是「只训一个场景，别的不管」。Video-LLaVA 靠额外训练阶段把视频硬接到图像模型上。LLaVA-NeXT 用切片（tiling）加上多图支持。没有一个能干净地同时搞定三种场景。

> Image, multi-image, and video each stress a model differently. Single-image wants high-resolution tokens (AnyRes, ~2880 visual tokens) to catch OCR and fine detail. ... Video wants many frames at low resolution (~196 tokens per frame after pooling) to capture temporal dynamics. ... If you train separate models, you pick one budget. If you train one model, you need the budget to scale sensibly across scenarios without blowing context. ... Pre-OneVision, the default answer was "train one scenario, ignore the others." ... None handled all three cleanly.

## The Concept · 概念

### The OneVision token budget · OneVision 的 token 预算

LLaVA-OneVision 选定了一个约每样本 3000-4000 token 的统一视觉 token 预算，按场景以不同方式分配：

- 单图：AnyRes-9（3x3 切片 + 缩略图），每片 384 分辨率、729 个 patch，做激进的 2x2 双线性池化 → 每片 182 个 token。合计：9 * 182 + 182 = 1820 个 token。或者 AnyRes-4、每片 729 = 2916 + 729。
- 多图：每张中等分辨率（384，不切片），729 个 token、不池化。预算 6 张图 → 4374 个 token。
- 视频：32 帧、384 分辨率、激进的 3x3 双线性池化 → 每帧 81 个 token。合计：32 * 81 = 2592 个 token。

这种分配让总 token 数大致恒定。LLM 永远不会看到撑爆上下文的 batch。编码器在不同场景产出不同的几何形状，但 LLM 消耗的是同一份预算。

> LLaVA-OneVision picks a unified visual-token budget of approximately 3000-4000 tokens per sample, allocated differently per scenario ... The allocation maintains roughly constant total tokens. The LLM never sees a batch that blows its context. The encoder produces different geometry per scenario, but the LLM consumes the same budget.

### The three-stage curriculum · 三阶段课程

LLaVA-OneVision 分三个阶段训练：

1. 单图 SFT（stage SI）。数据全部是单图加文本。在高分辨率 AnyRes 输入上训练。这一阶段教感知、OCR 和细粒度理解。使用 LLaVA-NeXT 数据加上 OneVision 专用的单图数据。
2. OneVision SFT（stage OV）。混合单图 + 多图 + 视频（均匀采样的帧）。在统一 token 预算上训练。这一阶段教模型处理异构的 batch 形状。不重置权重 —— 从 stage SI 继续。
3. 任务迁移（stage TT）。继续用目标任务的混合数据，通常按产品需要偏重多图或视频。可选地为部署做微调。

关键：课程顺序很重要。先训视频或多图、后训单图，即便数据完全相同，图像性能也更差。论文明确做了这项消融。

> LLaVA-OneVision trains in three stages: single-image SFT (stage SI) ... OneVision SFT (stage OV) ... Task transfer (stage TT) ... Critical: the curriculum order matters. Training video-first or multi-image-first produces worse image performance than single-image-first, even with the same data. The paper ablates this explicitly.

### Why curriculum works · 课程为什么有效

单图训练打下感知底子。patch token 携带细粒度视觉特征，LLM 学会把它们与文本整合。多图和视频引入结构性挑战（哪张图是哪张、什么先发生），没有强感知底子很难学会。

如果三种场景从零一起混训，模型会欠拟合感知（每个 batch 里的单图数据有限）、过拟合结构（多图/视频数据一大堆）。结果是一个会跟跨图推理套路、但视觉上很浅的模型。

课程顺序让你从 stage SI 拿到感知强度，再从 stage OV 拿到组合/时序推理，两者都不丢。

> Single-image training builds the perceptual base. ... If you train all scenarios from scratch together, the model underfits perception (limited single-image data per batch) and overfits structure (lots of multi-image / video data). ... Curriculum ordering gives you perception strength from stage SI, then compositional/temporal reasoning from stage OV, without losing either.

### Emergent cross-scenario skills · 涌现的跨场景能力

LLaVA-OneVision 论文报告了三种涌现能力：

1. 多相机推理。训练时多图和视频是分开的；推理时要求它对多相机驾驶场景做推理。模型正确整合了各个视角，尽管训练中从没见过这种确切格式。
2. Set-of-mark 提示。用户给图中的物体标上编号；模型推理「标记 3 相对标记 7 在做什么」。标记和标注都没训过；这是从空间定位 + 多图参照的组合中学来的。
3. iPhone 截图 agent。用户给一张 iPhone 屏幕截图，要求规划下一步点击。训练数据有 UI 截图、用户操作流程的视频、多图前后对照。它泛化到了 agent 用例。

这些都不是训练过的任务；它们从课程的组合结构中涌现。

> The LLaVA-OneVision paper reports three emergent capabilities: multi-camera reasoning ... set-of-mark prompting ... iPhone-screenshot agent ... These are not trained tasks; they emerge from the curriculum's compositional structure.

### Visual-token pooling · 视觉 token 池化

token 预算需要池化。OneVision 在 2D patch 网格上做双线性插值：24x24 = 576 个 patch 变成 12x12 = 144（2 倍）或 8x8 = 64（3 倍）。池化在 patch 网格空间做、不在 token 空间做，为的是保住局部性。

每个场景选多大池化因子，本身就是一个超参数。池化越少 = token 越多 = 表征越丰富。池化越多 = token 越少 = 装得下更多帧/图。

> The token budget requires pooling. OneVision uses bilinear interpolation on the 2D patch grid: 24x24 = 576 patches becomes 12x12 = 144 (2x factor) or 8x8 = 64 (3x factor). Pooling is done in patch-grid space, not token space, to preserve locality. ... The choice of pooling factor per scenario is itself a hyperparameter. Less pooling = more tokens = richer representation. More pooling = fewer tokens = more frames / images fit.

### LLaVA-OneVision-1.5 · 2025 续作

2025 年的续作（LLaVA-OneVision-1.5，arXiv 2509.23661）在训练数据、模型权重和代码上都「完全开源」。它在部分基准上追平了专有模型的差距，把这套配方民主化了。同样的课程、更多数据、更好的基座 LLM。架构没变。

> The 2025 follow-up (LLaVA-OneVision-1.5, arXiv 2509.23661) is "fully open" in training data, model weights, and code. Matches the proprietary gap on some benchmarks and democratizes the recipe. Same curriculum, more data, better base LLM. No architecture change.

### Contrast with Qwen2.5-VL · 与 Qwen2.5-VL 对比

Qwen2.5-VL（第 12.09 课）做了不同的选择。它用 M-RoPE 和动态 FPS，而不是固定池化。它的预算随输入伸缩 —— 1 分钟的视频比 5 秒的视频用更多 token。LLaVA-OneVision 固定预算、伸缩池化。两条路都行；它们是用可配置性换可预测性。

> Qwen2.5-VL (Lesson 12.09) makes different choices. It uses M-RoPE and dynamic FPS instead of fixed pooling. Its budget scales with input — a 1-minute video uses more tokens than a 5-second video. LLaVA-OneVision fixes the budget and scales the pooling. Both work; they trade configurability for predictability.

```figure
l5-onevision-budget
```

## Use It · 实战用法

`code/main.py` 是一个面向 OneVision 风格 VLM 的课程与预算规划器。给定每样本 token 预算和一个目标场景配比（比如 40% 单图、30% 多图、30% 视频），它会：

- 为每个场景分配分辨率、池化因子和帧数。
- 检查每个场景都装得进共享预算。
- 报告预期 token 数、LLM FLOPs，以及哪些场景 token 不足。
- 打印逐阶段的训练日程。

可以用它规划一次 OneVision 微调，或给 VLM 部署的每请求成本做 sanity check。

> `code/main.py` is a curriculum and budget planner for a OneVision-style VLM. Given a token budget per sample and a target scenario mix (say 40% single-image, 30% multi-image, 30% video), it: allocates resolution, pooling factor, and frames per scenario ... Use it to plan a OneVision fine-tune or to sanity-check a VLM deployment's per-request cost.

## Ship It · 交付

本课产出 `outputs/skill-onevision-budget-planner.md`。给定目标任务分布和每样本预算，它会给出 AnyRes 因子、每帧池化、视频帧数和课程阶段权重。只要你训练或微调统一场景 VLM，就用它。

> This lesson produces `outputs/skill-onevision-budget-planner.md`. Given a target task distribution and a per-sample budget, it emits the AnyRes factor, per-frame pooling, video frame count, and curriculum stage weights. Use this whenever you train or fine-tune a unified-scenario VLM.

## Exercises · 练习

1. 你的产品支持 80% 单图、10% 多图（2-4 张图）、10% 视频（8-16 帧）。设计 token 预算。不做重量级多图省下来的预算，你会投到哪里？

2. 读 LLaVA-OneVision 第 4.3 节（涌现能力）。提出课程很可能解锁、但论文没有报告的第四种涌现技能。

3. 把课程顺序换掉 —— 先训多图，再单图，最后视频。预测哪些基准会退化，为什么。

4. 论文报告视频基准只用每样本 8 帧训练。它能泛化到推理时的 30 秒视频吗？最先崩的是什么 —— token 预算，还是时序推理？

5. 把 24x24 patch 双线性池化到 12x12 是每维 4 倍缩减。用 stdlib Python 实现这个池化，验证每个 2x2 块的均值与双线性输出一致。

> Your product supports 80% single-image, 10% multi-image (2-4 images), 10% video (8-16 frames). Design the token budget. Where would you put the extra budget you save from not doing heavy multi-image? ... Read LLaVA-OneVision Section 4.3 (emergent capabilities). Propose a fourth emergent skill the curriculum would likely unlock but the paper did not report. ... The paper reports video benchmarks trained on only 8 frames per sample. Does that generalize to 30-second videos at inference? What breaks first — the token budget or the temporal reasoning?

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|------------------------|
| OneVision scenario | "单图、多图或视频" | 统一 VLM 处理的三种输入形状之一；预算在三者间保持恒定 |
| Token budget | "每样本多少 token" | LLM 在每个训练/推理样本看到的视觉 token 总数，典型 3000-4000 |
| Curriculum | "训练顺序" | 为涌现迁移而选定的阶段顺序（单图 → 多图 → 视频） |
| Bilinear pooling | "token 缩水" | 在 patch 网格（2D）上做双线性插值，在保住局部性的同时减少 token 数 |
| Emergent skill | "没训过也会" | 推理时出现、却没有对应训练数据的能力，源自课程的组合结构 |
| AnyRes-k | "k 片布局" | k 个固定分辨率子切片加一张缩略图，k 典型取 4 或 9 |
| Task transfer | "跨场景泛化" | 单图上学到、经共享骨干应用到视频（反之亦然）的技能 |

## Further Reading · 延伸阅读

- [Li et al. — LLaVA-OneVision (arXiv:2408.03326)](https://arxiv.org/abs/2408.03326)
- [LLaVA-OneVision-1.5: Fully Open Framework (arXiv:2509.23661)](https://arxiv.org/abs/2509.23661)
- [Lin et al. — Video-LLaVA (arXiv:2311.10122)](https://arxiv.org/abs/2311.10122)
- [Lin et al. — VILA (arXiv:2312.07533)](https://arxiv.org/abs/2312.07533)
- [Wang et al. — Qwen2-VL (arXiv:2409.12191)](https://arxiv.org/abs/2409.12191)
