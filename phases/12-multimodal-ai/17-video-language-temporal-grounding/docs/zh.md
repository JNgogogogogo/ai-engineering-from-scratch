# Video-Language Models: Temporal Tokens and Grounding · 视频语言模型：时间 token 与时间定位

> 视频不是一堆照片的堆叠。一段 5 秒的片段含有因果顺序、动作动词和事件时序，这些是图像模型无法表达的。Video-LLaMA（Zhang et al.，2023 年 6 月）发布了第一个带视听 grounding 的开源视频 LLM。VideoChat 和 Video-LLaVA 把这一模式放大。到 2025 年，Qwen2.5-VL 的 TMRoPE 追平了前沿闭源模型。每个系统都用不同方式解决时间 token —— 每片段一个 Q-former、每帧 concat 池化、每 token 一个 TMRoPE。本课解读这些模式，动手造一个均匀 vs 动态帧采样器，并在时间定位任务上做评估。

> Video is not a stack of photos. A 5-second clip has causal ordering, action verbs, and event timing that an image model cannot represent. Video-LLaMA (Zhang et al., June 2023) shipped the first open video-LLM with audio-visual grounding. VideoChat and Video-LLaVA scaled the pattern. By 2025 Qwen2.5-VL's TMRoPE closed the gap with frontier proprietary models. Each system solved temporal tokens differently — Q-former per clip, concat-pool per frame, TMRoPE per token. This lesson reads the patterns, builds a uniform-vs-dynamic frame sampler, and evaluates on temporal grounding tasks.

**Type:** Build
**Languages:** Python (stdlib, frame sampler + temporal-grounding evaluator)
**Prerequisites:** Phase 12 · 08 (LLaVA-OneVision)
**Time:** ~180 minutes

## Learning Objectives · 学习目标

- 解释为什么时间位置编码对视频 VLM 性能的影响独立于视觉编码器。
- 在 token/秒与定位精度之间对比均匀采样、动态 FPS 采样与事件驱动采样。
- 描述每片段 Q-former（Video-LLaMA）、逐帧池化（Video-LLaVA）、逐 token M-RoPE（Qwen2.5-VL）三种设计。
- 说出四大视频基准：VideoMME、TempCompass、EgoSchema、Video-MMMU。

> Explain why temporal positional encoding changes video VLM performance independently of the vision encoder.
> Compare uniform, dynamic-FPS, and event-driven frame sampling on tokens-per-second vs grounding accuracy.
> Describe Q-former-per-clip (Video-LLaMA) vs pooled-per-frame (Video-LLaVA) vs M-RoPE-per-token (Qwen2.5-VL) designs.
> Name the four video benchmarks: VideoMME, TempCompass, EgoSchema, Video-MMMU.

## The Problem · 问题在哪

一段 1 分钟、30 FPS 的视频有 1800 帧。按每帧 196 个视觉 token（224 分辨率的 ViT-B）计算，就是 35.2 万 token —— 超过 2024 年任何 LLM 的上下文。

三种压缩策略：

1. 对帧做下采样（依内容 1-8 FPS）。
2. 对每帧的 patch token 激进池化（3x3 或 4x4 双线性池化）。
3. 用 Q-former 压缩：吃进 16 帧片段，输出 64 个 token。

每种取舍各不相同。下采样丢时间细节。池化丢空间细节。Q-former 两头都丢一点，但省 token。

时间位置编码是另一根轴：模型怎么知道第 5 帧发生在第 6 帧之前？选项包括简单的一维时间 RoPE（Video-LLaMA）、可学习时间嵌入（Video-LLaVA）、TMRoPE（Qwen2.5-VL，完整 3D）。

> A 1-minute video at 30 FPS is 1800 frames. At 196 visual tokens per frame (ViT-B at 224), that is 352k tokens — larger than any 2024-era LLM context. ... Three reduction strategies exist: Subsample frames (1-8 FPS depending on content). Pool each frame's patch tokens aggressively (3x3 or 4x4 bilinear pool). Compress via a Q-former that takes a 16-frame clip and outputs 64 tokens. ... Each trade-off is different. Subsampling loses temporal detail. Pooling loses spatial detail. Q-former loses both a little but saves tokens. ... Temporal position encoding is the other axis: how does the model know frame 5 came before frame 6?

## The Concept · 概念

### Video-LLaMA: Q-former per clip + audio branch · Video-LLaMA：每片段一个 Q-former + 音频分支

Video-LLaMA（2023）是第一个开源视频 LLM。架构：

- 2 FPS 下的 16 帧片段（即 8 秒）。
- 逐帧 ViT 特征 → Video Q-former 对全部 16 帧做交叉注意力 → 32 个可学习查询 → LLM。
- 并行音频分支：波形 → ImageBind 音频编码器 → Audio Q-former → 32 个查询 → LLM。

强项：视听联合推理。弱点：片段长度固定，无法在任意时刻定位。

> Video-LLaMA (2023) was the first open video-LLM. Architecture: 16-frame clips at 2 FPS (so 8 seconds). ... Per-frame ViT features -> Video Q-former that cross-attends over all 16 frames -> 32 learned queries -> LLM. Parallel audio branch: waveform -> ImageBind audio encoder -> Audio Q-former -> 32 queries -> LLM. ... Strength: audio-visual joint reasoning. Weakness: fixed clip length, no arbitrary time grounding.

### VideoChat and Video-LLaVA · VideoChat 与 Video-LLaVA

VideoChat 保留了 Video-LLaMA 的想法，但砍掉音频并做了简化。Video-LLaVA（Lin et al.，2023）在图像和视频帧上训练同一个视觉编码器（「投影之前先对齐」），得到统一表示。两者都是冻结 CLIP 编码器 + MLP + LLM 的组合。

两者都处理不了长视频。它们都是 8-16 帧的系统。

> VideoChat kept the Video-LLaMA idea but dropped audio and simplified. Video-LLaVA (Lin et al., 2023) trained a single visual encoder on both images and video frames ("alignment before projection"), giving a unified representation. Both are frozen-CLIP-encoder + MLP + LLM. ... Neither handles long video. Both are 8-16 frame systems.

### Qwen2.5-VL and TMRoPE · Qwen2.5-VL 与 TMRoPE

Qwen2.5-VL 引入了 TMRoPE —— 时间-模态旋转位置编码（Temporal-Modality Rotary Position Embedding）。每个 patch token 携带一个 (t, h, w) 位置，其中 t 是真实时间戳（不是帧序号）。

与简单时间嵌入的关键差异：

- 绝对时间，而非序号。模型看到的是「在第 4.2 秒」，不是「在第 15 帧」。
- 逐 token 旋转，而非逐片段。每个视觉 token 按自己的时间戳独立旋转。
- 与动态 FPS 兼容。这里 2 FPS、那里 4 FPS 的不均匀采样间隔，TMRoPE 原生就能处理。

TMRoPE 让「猫在第几秒跳起来？」这类查询成为可能。模型能输出「在第 4.2 秒」。Video-LLaMA 只能说「在片段前段」。

> Qwen2.5-VL introduced TMRoPE — Temporal-Modality Rotary Position Embedding. Each patch token carries an (t, h, w) position where t is the actual timestamp (not frame index). ... Absolute time, not index. The model sees "at 4.2 seconds" not "at frame 15." Per-token rotation, not per-clip. Each visual token rotates independently by its timestamp. Compatible with dynamic FPS. ... TMRoPE enables "at what second does the cat jump?" queries. The model can output "at 4.2 seconds." Video-LLaMA could only say "early in the clip."

### Frame sampling strategies · 帧采样策略

均匀采样：在整段时长上均匀取 N 帧。简单，但会错过运动峰值。

动态 FPS：按运动强度自适应采样。光流或帧差分挑出高运动片段做更密的采样。Qwen2.5-VL 就是用这个训练的。

事件驱动：先跑一个轻量检测器，在动作发生处多采样。VideoAgent 采用。

关键帧 + 上下文：在镜头切换点采样 + 相邻几帧。适合影视类内容。

> Uniform: sample N frames evenly over duration. Simple, loses motion peaks. Dynamic FPS: sample adaptively based on motion intensity. ... Event-driven: run a lightweight detector, sample more where action happens. Used by VideoAgent. Keyframe + context: sample at shot boundaries + a few adjacent frames. Used for cinematic content.

### Pooling per frame · 逐帧池化

1 FPS、每帧 576 token 时，5 分钟片段是 172,800 个 token。Qwen2.5-VL-72B 的 128k 上下文装得下，但代价高。

3x3 双线性池化降到每帧 64 token → 5 分钟 19,200 个 token。多数任务的最佳平衡点。

再激进一点（6x6 → 每帧 16 token）适合智能体工作流，那里空间细节没那么重要。

> At 1 FPS and 576 tokens per frame, a 5-minute clip is 172,800 tokens. Doable with Qwen2.5-VL-72B's 128k context but expensive. ... 3x3 bilinear pool reduces to 64 tokens per frame -> 19,200 tokens for 5 minutes. Sweet spot for most tasks. ... Pool more aggressively (6x6 -> 16 tokens per frame) for agent workflows where spatial detail matters less.

### The four video benchmarks · 四大视频基准

- VideoMME：全面的视频理解，短 + 中 + 长。
- TempCompass：细粒度时间推理，「之前」/「之后」类问题。
- EgoSchema：长时程第一人称视频。
- Video-MMMU：多学科多模态视频问答。

完整的视频 VLM 评估要四个都打。它们压测的维度各不相同 —— TempCompass 专考时序，EgoSchema 考 3 分钟以上的推理，VideoMME 覆盖各种时长。

> VideoMME: comprehensive video understanding, short + medium + long. TempCompass: fine-grained temporal reasoning, "before" / "after" questions. EgoSchema: long-horizon first-person video. Video-MMMU: multimodal multi-discipline video questions. ... A full video-VLM evaluation hits all four. They stress different axes — TempCompass is all about ordering, EgoSchema is about 3+ minute reasoning, VideoMME spans durations.

### Grounding output formats · 定位输出格式

时间定位的输出格式：

- 自由文本：「猫在第 4 秒左右跳起来。」易解析但不精确。
- 结构化 JSON：`{"event": "jump", "start": 4.1, "end": 4.3}`。Qwen2.5-VL 训练这种。
- 基于 token：特殊的 `<time>4.1</time>` token 与答案交错。Qwen2.5-VL 的内部格式。

基于 token 的格式对下游使用最精确。Qwen2.5-VL 的 JSON 输出格式可直接解析。

> Output formats for temporal grounding: Free text: "The cat jumps around the 4-second mark." Easy to parse but imprecise. Structured JSON: `{"event": "jump", "start": 4.1, "end": 4.3}`. Qwen2.5-VL trains this. Token-based: special `<time>4.1</time>` tokens interleaved with the answer. ... Token-based is most accurate for downstream use. Qwen2.5-VL's JSON output format parses directly.

### 2026 best practice · 2026 年最佳实践

2026 年的视频 VLM：

- 编码器：SigLIP 2，配 M-RoPE 或 TMRoPE（Qwen2.5-VL）。
- 帧采样：动态 FPS（按运动 1-4），并设最大帧数上限。
- 逐帧池化：3x3 双线性。
- 输出：带时间 + 事件字段的结构化 JSON。
- 基准：通用看 VideoMME + TempCompass；长时程看 EgoSchema。

> For video VLMs in 2026: Encoder: SigLIP 2 with M-RoPE or TMRoPE (Qwen2.5-VL). Frame sampling: dynamic FPS (1-4 depending on motion) with max-frame cap. Per-frame pooling: 3x3 bilinear. Output: structured JSON with time + event fields. Benchmarks: VideoMME + TempCompass for general; EgoSchema for long-horizon.

```figure
video-temporal-patches
```

## Use It · 实战用法

`code/main.py` 包含：

- 均匀采样与动态 FPS 两种帧采样器。
- 一个玩具级时间定位评估器：给定时刻 T 的「真值」事件和模型输出，带容差地打准确率分。
- 一个三方对比：Video-LLaMA（16 帧、Q-former）、Video-LLaVA（8 帧、MLP）、Qwen2.5-VL（动态 FPS + TMRoPE）。

> `code/main.py` includes: Uniform and dynamic-FPS frame samplers. A toy temporal-grounding evaluator: given a "ground truth" event at time T and a model output, score accuracy with tolerance. A comparison across Video-LLaMA (16 frames, Q-former), Video-LLaVA (8 frames, MLP), Qwen2.5-VL (dynamic FPS + TMRoPE).

## Ship It · 交付

本课产出 `outputs/skill-video-vlm-frame-planner.md`。给定一个视频任务（监控、动作识别、时间定位、摘要），它会挑选帧采样器、池化倍率、输出格式和预期精度档位。

> This lesson produces `outputs/skill-video-vlm-frame-planner.md`. Given a video task (monitoring, action recognition, temporal grounding, summarization), it picks the frame sampler, pooling factor, output format, and expected accuracy tier.

## Exercises · 练习

1. 对一段 3 分钟的烹饪演示，选均匀采样还是动态 FPS？用 token 数说明理由。

2. TMRoPE 具体多做了什么，是简单时间嵌入表做不到的？

3. 写一个 VLM 能学会输出的时间定位 JSON schema。把错误情形也考虑进去。

4. 阅读 Video-LLaVA 论文第 3 节「Alignment Before Projection」。为什么这比分别训练图像和视频编码器更好？

5. 看 VideoMME 排行榜：截至 2026 年，开源最强模型与闭源最强模型的差距有多大？其中多少归因于时间编码，多少归因于基座 LLM 规模？

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|------------------------|
| 时间定位（Temporal grounding） | 「带时间定位的回答」 | VLM 为事件发生的时刻输出具体时间区间 |
| TMRoPE | 「时间-多模态 RoPE」 | 带绝对时间戳的 3D 旋转位置编码，Qwen2.5-VL 使用 |
| 动态 FPS（Dynamic FPS） | 「运动感知采样」 | 高运动片段多采样，静态片段少采样 |
| 帧池化（Frame pooling） | 「逐帧空间压缩」 | 在进入 LLM 前用双线性插值减少每帧 patch 数 |
| 视频 Q-former（Video Q-former） | 「片段压缩器」 | 交叉注意力瓶颈，把 N 帧映射到 K 个可学习查询 |
| VideoMME | 「视频基准」 | 覆盖短/中/长视频的综合基准，2500+ 样本 |

## Further Reading · 延伸阅读

- [Zhang et al. — Video-LLaMA (arXiv:2306.02858)](https://arxiv.org/abs/2306.02858)
- [Li et al. — VideoChat (arXiv:2305.06355)](https://arxiv.org/abs/2305.06355)
- [Lin et al. — Video-LLaVA (arXiv:2311.10122)](https://arxiv.org/abs/2311.10122)
- [Qwen Team — Qwen2.5-VL (arXiv:2502.13923)](https://arxiv.org/abs/2502.13923)
- [Lin et al. — VILA-1.5 (arXiv:2312.07533)](https://arxiv.org/abs/2312.07533)
