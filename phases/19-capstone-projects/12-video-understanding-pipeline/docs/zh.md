# Capstone 12 — Video Understanding Pipeline (Scene, QA, Search) · 毕业项目 12 —— 视频理解流水线（场景、问答、搜索）

> Twelve Labs 把 Marengo + Pegasus 做成了产品。VideoDB 发布了「视频版 CRUD」API。AI2 的 Molmo 2 放出了开源 VLM 检查点。Gemini 长上下文可以原生处理数小时的视频。TimeLens-100K 定义了大规模时序定位（temporal grounding）。2026 年的流水线形态已经定型：场景切分、逐场景字幕 + 嵌入、转写对齐、多向量索引，以及一个能以（start, end）时间戳加帧预览来作答的查询。本次毕业项目要摄入 100 小时视频、打到公开基准，并度量计数类和动作类问题上的幻觉。

> Twelve Labs productized Marengo + Pegasus. VideoDB shipped the CRUD-for-video API. AI2's Molmo 2 published open VLM checkpoints. Gemini long-context handles hours of video natively. TimeLens-100K defined temporal grounding at scale. The 2026 pipeline is settled: scene segmentation, per-scene caption + embedding, transcript alignment, multi-vector index, and a query that answers with (start, end) timestamps plus frame previews. The capstone is ingesting 100 hours, hitting public benchmarks, and measuring hallucination on counting and action questions.

**Type:** Capstone
**Languages:** Python (pipeline), TypeScript (UI)
**Prerequisites:** Phase 4 (CV), Phase 6 (speech), Phase 7 (transformers), Phase 11 (LLM engineering), Phase 12 (multimodal), Phase 17 (infrastructure)
**Phases exercised:** P4 · P6 · P7 · P11 · P12 · P17
**Time:** 30 hours

## Problem · 问题

长视频问答是 2026 年规模下最吃带宽的多模态问题。Gemini 2.5 Pro 能原生读一部 2 小时的视频，但要把 100 小时视频摄入一个可查询的语料库，仍然需要场景级索引。生产形态是：场景切分（TransNetV2 或 PySceneDetect）、用 VLM 逐场景生成字幕（Gemini 2.5、Qwen3-VL-Max 或 Molmo 2）、转写对齐（Whisper-v3-turbo 带词级时间戳），以及一个并排存放字幕、帧嵌入和转写的多向量索引。查询流水线以（start, end）时间戳加帧预览作答。

基准是公开的（ActivityNet-QA、NeXT-GQA），外加你自己的 100 题定制集。计数类和动作类问题上的幻觉是公认的困难失败类别；本次毕业项目明确度量它。

> Long-form video QA is the most bandwidth-hungry multimodal problem at 2026 scale. Gemini 2.5 Pro can read a 2-hour video natively, but ingesting 100 hours of video into a queryable corpus still requires a scene-level index. The production shape combines scene segmentation (TransNetV2 or PySceneDetect), per-scene captioning with a VLM (Gemini 2.5, Qwen3-VL-Max, or Molmo 2), transcript alignment (Whisper-v3-turbo with word timestamps), and a multi-vector index that stores caption, frame embedding, and transcript side by side. The query pipeline answers with (start, end) timestamps plus frame previews.
> Benchmarks are public (ActivityNet-QA, NeXT-GQA) plus your own 100-query custom set. Hallucination on counting and action-type questions is the known-hard failure class; the capstone explicitly measures it.

## Concept · 概念

摄入时三条流水线并行。**场景切分**把视频切成场景。**VLM 字幕**为每个场景生成字幕，并从关键帧提取帧嵌入。**ASR 对齐**产出词级时间戳。三条流按（scene_id, 时间区间）对齐拼接。每个场景在多向量索引（Qdrant）里拿到三种向量：字幕嵌入、关键帧嵌入、转写嵌入。

查询时，自然语言问题同时打向三种向量；结果用 RRF 合并；一个时序定位适配器（TimeLens 风格）在 top 场景内部细化（start, end）窗口。VLM 合成器（Gemini 2.5 Pro 或 Qwen3-VL-Max）拿到问题 + top 场景 + 裁剪出的帧，给出带引用时间戳和帧预览的答案。

幻觉度量是重点。计数类（「有几个人进了房间？」）和动作类（「厨师是先倒料还是先搅拌？」）问题的可靠性出了名地差。要把它们的准确率与描述类问题分开报告。

> Three pipelines run in parallel at ingest. **Scene segmentation** cuts the video into scenes. **VLM captioning** generates a caption per scene and a frame embedding from a keyframe. **ASR alignment** produces word-level timestamps. The three streams are joined by (scene_id, time range). Each scene gets three vector types in a multi-vector index (Qdrant): caption embedding, keyframe embedding, transcript embedding.
> At query time, the natural-language question fires against all three vectors; results merge with RRF; a temporal-grounding adapter (TimeLens-style) refines the (start, end) window within the top scene. The VLM synthesizer (Gemini 2.5 Pro or Qwen3-VL-Max) takes query + top scenes + cropped frames and answers with cited timestamps and a frame preview.
> The hallucination measurement matters. Counting ("how many people enter the room?") and action-type ("does the chef pour before stirring?") questions are notoriously unreliable. Report accuracy separately from descriptive questions.

## Architecture · 架构

```
video file / URL
      |
      v
PySceneDetect / TransNetV2  (scene segmentation)
      |
      +--- per-scene keyframe --- VLM caption + frame embedding
      |                            (Gemini 2.5 Pro / Qwen3-VL-Max / Molmo 2)
      |
      +--- audio channel --- Whisper-v3-turbo ASR + word timestamps
      |
      v
multi-vector Qdrant: {caption_emb, keyframe_emb, transcript_emb}
      |
query:
  dense queries against all three -> RRF merge -> top-k scenes
      |
      v
TimeLens / VideoITG temporal grounding (refine start/end within scene)
      |
      v
VLM synth: query + top scenes + frame previews
      |
      v
answer + (start, end) timestamps + frame thumbs + citations
```

## Stack · 技术栈

- 场景切分：TransNetV2（2024-26 的最优选择）或 PySceneDetect
- ASR：faster-whisper 跑 Whisper-v3-turbo，带词级时间戳
- VLM 字幕 + 作答：Gemini 2.5 Pro 或 Qwen3-VL-Max 或 Molmo 2
- 时序定位：TimeLens-100K 训练的适配器或 VideoITG
- 索引：Qdrant，带多向量支持（字幕 / 帧 / 转写）
- UI：Next.js 15，HTML5 视频播放器加场景缩略图
- 评估：ActivityNet-QA、NeXT-GQA、自定义 100 题人工标注集
- 幻觉基准：计数类和动作类子集，附人工标注

```figure
cf-scene-index
```

## Build It · 动手造

1. **摄入遍历器。** 接受 YouTube URL 或本地 MP4。需要时降采样到 720p。持久化 `{video_id, file_path}`。

2. **场景切分。** 跑 TransNetV2 或 PySceneDetect，产出 `[{scene_id, start_ms, end_ms, keyframe_path}]`。按 100 小时计：约 6k-8k 个场景。

3. **ASR 轮。** 对音频跑 Whisper-v3-turbo；导出词级时间戳；切成按场景的转写片段。

4. **VLM 字幕。** 每个场景拿关键帧配一个短字幕模板调用 Gemini 2.5 Pro（或 Qwen3-VL-Max）。产出字幕 + 帧嵌入。

5. **多向量索引。** Qdrant collection，三个命名向量。Payload：`{video_id, scene_id, start_ms, end_ms, keyframe_url}`。

6. **查询。** 自然语言问题打出三路稠密查询；用倒数排名融合（RRF）合并；top-k=5 个场景。

7. **时序定位。** 在 top 场景上跑 TimeLens 风格适配器，在场景内部细化（start, end）窗口。

8. **VLM 合成。** 用问题 + top-3 场景片段（图片或短视频）+ 转写调用 Gemini 2.5 Pro。要求给出 `(video_id, start_ms, end_ms)` 引用。

9. **评估。** 跑 ActivityNet-QA 和 NeXT-GQA。建一个 100 题定制集。报告总体准确率 + 分类别明细（计数、动作、描述）。

> 2. **Scene segmentation.** Run TransNetV2 or PySceneDetect to produce `[{scene_id, start_ms, end_ms, keyframe_path}]`. Target 100 hours: ~6k-8k scenes.
> 5. **Multi-vector index.** Qdrant collection with three named vectors. Payload: `{video_id, scene_id, start_ms, end_ms, keyframe_url}`.
> 7. **Temporal grounding.** Run TimeLens-style adapter on the top scene to refine the (start, end) window within the scene.
> 8. **VLM synth.** Call Gemini 2.5 Pro with query + top-3 scene clips (as images or short clips) + transcripts. Require `(video_id, start_ms, end_ms)` citations.

## Use It · 实战用法

```
$ video-qa ask --url=https://youtube.com/watch?v=X "how many cars pass the intersection in the first minute?"
[scene]    23 scenes detected
[asr]      transcript complete, 4m12s
[index]    69 vectors written (23 scenes x 3)
[query]    top scene: scene 3 [01:32-01:54], confidence 0.84
[ground]   refined window: [00:12-00:58]
[synth]    gemini 2.5 pro, 1.4s
answer:    5 cars pass the intersection between 00:12 and 00:58.
citations: [scene 3: 00:12-00:58]
          [frame preview at 00:14, 00:27, 00:44, 00:51, 00:57]
```

## Ship It · 交付

`outputs/skill-video-qa.md` 是交付物。给定一个 YouTube URL 或上传的视频，流水线为场景建索引，并以带时间戳的引用回答问题。

| 权重 | 评分标准 | 度量方式 |
|:-:|---|---|
| 25 | 时序定位 IoU | 留出定位集上的交并比 |
| 20 | 问答准确率 | NeXT-GQA 与自定义 100 题 |
| 20 | 摄入吞吐 | 每美元能处理的视频小时数 |
| 20 | UI 与引用体验 | 时间戳链接、缩略图条、跳转到帧 |
| 15 | 幻觉率 | 计数类和动作类准确率分开报告 |
| **100** | | |

> `outputs/skill-video-qa.md` is the deliverable. Given a YouTube URL or uploaded video, the pipeline indexes scenes and answers questions with timestamped citations.

## Exercises · 练习

1. 在字幕环节把 Gemini 2.5 Pro 换成 Qwen3-VL-Max。在一个人工评定的 50 场景样本上报告字幕质量差。

2. 把逐场景帧嵌入缩减成一个池化向量，放弃多向量。度量检索退化。

3. 做一个「严格计数」模式：合成器为每个被计数的实例给出时间戳，由用户点击核验。度量用户核验能否降低幻觉。

4. 基准测试摄入成本：三种 VLM 选择下每美元可处理的视频小时数。选出性价比最优点。

5. 加说话人分离转写：对音频跑 pyannote 说话人分离，按说话人嵌入转写。演示「Alice 关于 X 说了什么？」这类查询。

> 1. Swap Gemini 2.5 Pro for Qwen3-VL-Max on the captioning pass. Report caption quality delta on a human-rated 50-scene sample.
> 3. Build a "counting strict" mode: the synthesizer extracts each counted instance with a timestamp and the user clicks to verify. Measure whether user-verification reduces hallucination.

## Key Terms · 术语表

| 术语 | 俗称 | 实际含义 |
|------|-----------------|------------------------|
| Scene segmentation（场景切分） | "镜头检测" | 在镜头边界处把视频切成场景 |
| Multi-vector index（多向量索引） | "字幕 + 帧 + 转写" | 一个 Qdrant collection，每种表示一个命名向量 |
| Temporal grounding（时序定位） | "到底发生在何时" | 为查询答案细化（start, end）窗口 |
| Frame embedding（帧嵌入） | "视觉表示" | 关键帧的向量嵌入；用于场景视觉相似度 |
| RRF fusion | "倒数排名融合" | 跨多个排序列表的合并策略；经典的混合检索技巧 |
| Counting hallucination（计数幻觉） | "数错" | VLM 在「有多少个 X」问题上的已知失败模式 |
| ActivityNet-QA | "视频问答基准" | 长视频问答准确率基准 |

## Further Reading · 延伸阅读

- [AI2 Molmo 2](https://allenai.org/blog/molmo2) —— 开源 VLM 检查点
- [TimeLens (CVPR 2026)](https://github.com/TencentARC/TimeLens) —— 大规模时序定位
- [Gemini Video long-context](https://deepmind.google/technologies/gemini) —— 托管参照实现
- [VideoDB](https://videodb.io) —— 视频版 CRUD API 参照
- [Twelve Labs Marengo + Pegasus](https://www.twelvelabs.io) —— 商业参照
- [TransNetV2](https://github.com/soCzech/TransNetV2) —— 场景切分模型
- [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) —— 经典开源替代
- [ActivityNet-QA](https://arxiv.org/abs/1906.02467) —— 参照评估基准
