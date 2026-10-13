# Qwen-VL Family and Dynamic-FPS Video · Qwen-VL 家族与动态 FPS 视频

> Qwen-VL 家族 —— Qwen-VL（2023）、Qwen2-VL（2024）、Qwen2.5-VL（2025）、Qwen3-VL（2025）—— 是 2026 年影响力最大的开源视觉-语言模型谱系。每一代都做了一个决定性的架构押注，而开源生态在十二个月内纷纷跟进：M-RoPE 带来的原生动态分辨率、带绝对时间对齐的动态 FPS 采样、ViT 里的窗口注意力、结构化的 agent 输出格式。到 Qwen3-VL 为止，配方已经定型：一个接受原生宽高比输入的 2D-RoPE-ViT 编码器，一个投影进大 Qwen3 语言基座的 MLP，以及把 OCR、定位（grounding）和 agent 行为当一等目标的训练阶段。本课按时间顺序读这个家族，让你明白每个旋钮为什么在那儿。

> The Qwen-VL family — Qwen-VL (2023), Qwen2-VL (2024), Qwen2.5-VL (2025), Qwen3-VL (2025) — is the most influential open vision-language model lineage in 2026. Each generation made a single decisive architectural bet that the rest of the open ecosystem copied within twelve months: native dynamic resolution via M-RoPE, dynamic-FPS sampling with absolute time alignment, window attention in the ViT, and structured agent output formats. By Qwen3-VL, the recipe had stabilized: a 2D-RoPE-ViT encoder with native-aspect-ratio inputs, an MLP projector into a large Qwen3 language base, and training stages that emphasized OCR, grounding, and agent behavior as first-class targets. This lesson reads the family chronologically so you understand why every knob is where it is.

**Type:** Learn
**Languages:** Python (stdlib, M-RoPE encoder + dynamic-FPS sampler)
**Prerequisites:** Phase 12 · 06 (patch-n'-pack)
**Time:** ~120 minutes

## Learning Objectives · 学习目标

- 计算 M-RoPE 的三轴旋转（时间、高、宽），并解释为什么三者缺一不可。
- 为一段视频选择动态 FPS 采样策略，并权衡每秒 token 数与事件检测精度。
- 按顺序说出 Qwen-VL 四代的升级点，以及每一次分别解锁了什么。
- 接好 Qwen2.5-VL 风格的 JSON agent 输出格式，并从 VLM 响应中解析出结构化工具调用。

> Compute M-RoPE's three-axis rotations (temporal, height, width) and explain why all three are needed.
> Pick a dynamic-FPS sampling strategy for a video and reason about tokens-per-second vs event-detection accuracy.
> Name the four Qwen-VL generational upgrades in order and what each enabled.
> Wire a Qwen2.5-VL-style JSON agent output format and parse structured tool calls from a VLM response.

## The Problem · 问题在哪

Qwen-VL 于 2023 年 8 月发布，是对 LLaVA-1.5 和 BLIP-2 的直接回应。Qwen 团队瞄准的差距有三重：分辨率、视频、结构化输出。

分辨率：LLaVA-1.5 跑在 336x336。照片够用，面对中文发票或密密麻麻的表格截图就毫无用处。Qwen-VL 的第一个创新是 448x448 加上可定位（grounded）的边界框输出，让模型能「指」东西。

视频：Video-LLaMA 把逐帧编码器堆起来喂给 LLM。短视频还行，但对以时间轴为信号的多分钟视频就不行。Qwen 团队想要一个理解时间的单一编码器。

结构化输出：LLaVA 吐自由文本。agent 需要的是 JSON。Qwen-VL 直接用显式 JSON 输出格式训练，边界框坐标也作为文本输出。

Qwen-VL 的每一代都在延伸这三根轴之一。

> Qwen-VL shipped in August 2023 as a direct response to LLaVA-1.5 and BLIP-2. The gap the Qwen team targeted was threefold: resolution, video, and structured output. ... Resolution: LLaVA-1.5 ran at 336x336. Fine for photos, useless for a Chinese-language invoice or a dense spreadsheet screenshot. ... Every Qwen-VL generation extends one of these three axes.

## The Concept · 概念

### Qwen-VL (August 2023) · Qwen-VL（2023 年 8 月）

第一代：OpenCLIP ViT-bigG/14 编码器（2.5B 参数）、兼容 LLama 的 Q-Former（1 步、256 个 query）、Qwen-7B 基座。贡献：

- 448x448 分辨率（当时开源 VLM 的 SOTA）。
- 定位（Grounding）：用带显式坐标 token 输出的图文对训练。「The cat is at <box>(112, 204), (280, 344)</box>」。
- 从一开始就中英双语训练。

当时的基准：英文与 GPT-4V 打得有来有回，中文占优。真正的头条是那份定位监督。

> The first generation: OpenCLIP ViT-bigG/14 as encoder (2.5B params), LLama-compatible Q-Former (1-step with 256 queries), Qwen-7B base. Contributions: 448x448 resolution (then SOTA for an open VLM) ... Grounding: trained on image-text pairs with explicit coordinate-token output ... Benchmarks at the time: competitive with GPT-4V on English, dominant on Chinese. The grounding supervision was the real headline.

### Qwen2-VL (September 2024) — M-RoPE and native resolution · Qwen2-VL（2024 年 9 月）—— M-RoPE 与原生分辨率

Qwen2-VL 用原生动态分辨率的 ViT 编码器，取代了固定分辨率 + Q-Former 的组合。关键变化：

- 原生动态分辨率。ViT 接受任何 HxW、只要能被 28 整除（patch 14、2 倍空间合并）。一张 1120x672 的图（40x24 个合并后 patch）产出 960 个视觉 token。不缩放、不切片、不要缩略图。
- M-RoPE（Multimodal RoPE）。每个 token 携带 3D 位置 (t, h, w) 而不是 1D。图像 t=0，视频 t = frame_index。RoPE 按每轴一个频率旋转 query/key 向量。没有位置嵌入表。
- MLP 投影器。扔掉 Q-Former；在合并后的 patch token 上用一个 2 层 MLP。
- 动态 FPS 视频。默认按 1-2 FPS 采样，但模型接受任意帧数。

结果：Qwen2-VL-7B 在多个多模态基准上追平 GPT-4o，并在 DocVQA 上赢过它（94.5 vs 88.4）。架构变化才是决定性的一步。

> Qwen2-VL replaced the fixed-resolution + Q-Former stack with a natively dynamic-resolution ViT encoder. Key changes: native dynamic resolution ... M-RoPE (Multimodal RoPE) ... Result: Qwen2-VL-7B matched GPT-4o on several multimodal benchmarks and beat it on DocVQA (94.5 vs 88.4). The architecture change was the decisive move.

### Qwen2.5-VL (February 2025) — dynamic FPS + absolute time · Qwen2.5-VL（2025 年 2 月）—— 动态 FPS + 绝对时间

Qwen2.5-VL 的大变化在视频。动态 FPS 不只是「需要时多采几帧」。论文把它形式化为：

- 绝对时间 token。不用位置索引（第 0、1、2 帧……），而用真实时间戳。「在 0:04，猫跳了起来。」模型看到的是与帧 token 交错的 `<time>0.04</time>` token。
- 动态 FPS。慢镜头 1 FPS，动作戏 4+ FPS。用户或训练者来选；M-RoPE 自适应。
- ViT 里的窗口注意力。空间注意力开窗口（块内局部）换吞吐；每隔几层做一次全局注意力。
- 显式 JSON 输出格式。用工具调用数据训练：`{\"tool\": \"click\", \"coords\": [380, 220]}`。开箱即是 agent。
- MRoPE-v2 缩放。位置随最大输入尺寸缩放，10 分钟的视频也不会耗尽频率范围。

基准：Qwen2.5-VL-72B 在大多数视频基准上赢 GPT-4o，文档上与 Gemini 2.0 打平，并把 GUI 定位的开源模型 SOTA 写在自己名下（ScreenSpot：84% 准确率，GPT-4o 只有 38%）。

> Qwen2.5-VL's big shift was video. Dynamic FPS is not just "sample more frames when needed." The paper formalized: absolute time tokens ... dynamic FPS ... window attention in ViT ... Benchmarks: Qwen2.5-VL-72B beats GPT-4o on most video benchmarks, matches Gemini 2.0 on documents, and sets the open-model SOTA for GUI grounding (ScreenSpot: 84% accuracy vs 38% for GPT-4o).

### Qwen3-VL (November 2025) · Qwen3-VL（2025 年 11 月）

Qwen3-VL 是一次巩固而非重构的增量升级：更大的 LLM 骨干（Qwen3-72B）、更多训练数据、改进的 OCR、借 Qwen3「思考模式」获得更强推理。ViT 和 M-RoPE 保持不变。论文的重点在数据与训练改进，而不是架构。

这条谱系的启示：到 2025 年，Qwen-VL 架构已经定型。后续世代加的是算力和数据，不是新原语。

> Qwen3-VL is an incremental upgrade that consolidates rather than reinvents: larger LLM backbone (Qwen3-72B), expanded training data, improved OCR, stronger reasoning via the Qwen3 "thinking mode." ... The lineage takeaway: by 2025 the Qwen-VL architecture had stabilized. Additional generations scale compute and data, not primitives.

### M-RoPE mathematically · M-RoPE 的数学

经典 RoPE 用成对坐标把 `d` 维 query `q` 按位置 `m` 旋转：

```
q_rot[2i]   = q[2i]   * cos(m * theta_i) - q[2i+1] * sin(m * theta_i)
q_rot[2i+1] = q[2i]   * sin(m * theta_i) + q[2i+1] * cos(m * theta_i)
theta_i     = 10000^(-2i/d)
```

M-RoPE 把隐藏维拆成三个频段。设 `d = 96`：32 维给时间、32 维给高、32 维给宽。每个频段按自己轴的位置旋转。一个位于 (t=5, h=10, w=20) 的 patch，其三个频段分别乘上 `R_t(5)`、`R_h(10)`、`R_w(20)`。

文本 token 用 `t = text_index, h = 0, w = 0`（或某种归一化选择），保持兼容。视频帧用 `t = frame_time, h = row, w = col`。单图用 `t = 0`。

好处：一套位置编码通吃文本、图像、视频，不需要分支代码，也不需要不同的位置表。

> Classical RoPE rotates a query `q` of dimension `d` by position `m` using paired coordinates ... M-RoPE splits the hidden dim into three bands. Say `d = 96`. Assign 32 dims to temporal, 32 to height, 32 to width. ... The benefit: one position encoding handles text, image, and video without branching code or different position tables.

### Dynamic-FPS sampling logic · 动态 FPS 采样逻辑

给定时长 `T` 秒的视频和目标 token 预算 `B`：

1. 算出你负担得起的最大 FPS：`fps_max = B / (T * tokens_per_frame)`。
2. 从 `{1, 2, 4, 8}` 里挑一个满足 `fps <= fps_max` 的目标 FPS。
3. 如果运动量大（光流启发式或用户显式要求），选高 FPS。运动量小就选低。
4. 按选定 FPS 均匀采样；在帧之间插入 `<time>t</time>` token。

Qwen2.5-VL 在训练中隐式学会这套逻辑；推理时用户通过 `fps` 参数控制。一段 60 秒的动作序列、4 FPS、每帧 81 token = 19440 个 token，32k 上下文装得下。

> Given a video of duration `T` seconds and a target-tokens budget `B`: compute the maximum FPS you can afford: `fps_max = B / (T * tokens_per_frame)` ... pick a target FPS from `{1, 2, 4, 8}` that satisfies `fps <= fps_max` ... A 60-second action sequence at 4 FPS with 81 tokens per frame = 19440 tokens, manageable in a 32k context.

### Structured agent output · 结构化 agent 输出

Qwen2.5-VL 的 agent 训练明确以结构化工具调用为目标：

```
{
  "tool": "mouse_click",
  "coords": [1024, 512],
  "button": "left",
  "modifier": null
}
```

解析是确定性的：对模型输出直接 JSON.parse。对比自由文本的「click at (1024, 512)」—— 那需要正则和歧义处理。正是这一转变让 Qwen2.5-VL 的 ScreenSpot 分数从 Qwen2-VL 的 55% 跳到 84%。

> Qwen2.5-VL's agent training explicitly targets structured tool calls ... Parsing is deterministic: JSON.parse over the model's output. Compare to free-form "click at (1024, 512)" which required regex and ambiguity handling. The shift is why Qwen2.5-VL's ScreenSpot scores jumped from Qwen2-VL's 55% to 84%.

```figure
mm-mrope-axes
```

## Use It · 实战用法

`code/main.py` 实现：

- 混合文本、图像 patch 和视频帧的打包序列的 M-RoPE 位置计算。
- 动态 FPS 采样器：给定（时长、预算、运动等级），选 FPS 并生成帧时间戳。
- 一个玩具版 Qwen2.5-VL JSON 输出解析器，处理带坐标字段的工具调用响应。

跑一遍，然后在一部 5 分钟视频上把固定 FPS 换成动态 FPS，感受差别。

> `code/main.py` implements: M-RoPE position computation for a packed sequence mixing text, image patches, and video frames ... a dynamic-FPS sampler ... Run it, then feel the difference when you swap fixed-FPS for dynamic-FPS on a 5-minute video.

## Ship It · 交付

本课产出 `outputs/skill-qwen-vl-pipeline-designer.md`。给定一个视频任务（监控、agent、动作识别、无障碍），它给出 Qwen2.5-VL 配置（帧预算、FPS 策略、窗口注意力开关、agent 输出模式）和延迟估计。只要你为视频产品部署 Qwen-VL 家族模型，就用它。

> This lesson produces `outputs/skill-qwen-vl-pipeline-designer.md`. Given a video task (monitoring, agent, action recognition, accessibility), it emits the Qwen2.5-VL configuration (frame budget, FPS strategy, window-attention flag, agent-output mode) and a latency estimate. Use this whenever you deploy a Qwen-VL-family model for a video product.

## Exercises · 练习

1. 对隐藏维 48（每频段 16，base theta 10000）计算 (t=3, h=5, w=7) 处 patch 的 M-RoPE 旋转。写出每个频段前三个坐标对的旋转角。

2. 一段 10 分钟的监控录像按 1 FPS 采出多少帧？384 分辨率加 3 倍池化，总共多少 token？Qwen2.5-VL 默认的 32k 上下文装得下吗？

3. 为 30 秒网球对拉、30 秒菜谱演示、30 秒 UI-agent 录屏分别选 FPS。用动态 FPS 逻辑为每个选择辩护。

4. Qwen2.5-VL 彻底扔掉了 Q-Former。为什么一个简单 MLP 在 2025 年可行、在 2023 年不行？（提示：数据规模与编码器质量。）

5. 把三段 Qwen2.5-VL JSON 工具调用输出解析成 Python dict。畸形 JSON 会让什么失败？Qwen cookbook 推荐什么恢复策略？

> A 10-minute security-camera recording at 1 FPS produces how many frames? At 384 resolution with 3x pool, how many total tokens? Does Qwen2.5-VL's default 32k context handle it? ... Pick FPS for a 30-second tennis rally vs a 30-second recipe demo vs a 30-second UI-agent recording. Justify each with the dynamic-FPS logic. ... Qwen2.5-VL drops the Q-Former entirely. Why does a simple MLP work in 2025 but not in 2023? (Hint: data scale and encoder quality.)

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|------------------------|
| M-RoPE | "多模态 RoPE" | 隐藏维里分时间、高、宽三个频段的 3D 旋转位置编码 |
| Dynamic FPS | "聪明采样" | 按运动、时长和 token 预算为每段视频选帧采样率 |
| Absolute time token | "时间戳 token" | 交错在序列里的 `<time>t</time>`，让模型看到真实秒数而不是帧序号 |
| Window attention | "局部注意力" | 空间自注意力限制在小窗口内换速度；周期性插入全局注意力 |
| Structured agent output | "JSON 模式" | 用训练数据监督教 VLM 输出带坐标和工具名的可解析 JSON |
| min_pixels / max_pixels | "分辨率上下限" | Qwen2.5-VL 的每请求控制项，框住总像素数、进而框住 token 数 |
| Grounding | "指给你看" | 把边界框坐标当文本 token 输出；从 Qwen-VL v1 起就有 |

## Further Reading · 延伸阅读

- [Bai et al. — Qwen-VL (arXiv:2308.12966)](https://arxiv.org/abs/2308.12966)
- [Wang et al. — Qwen2-VL (arXiv:2409.12191)](https://arxiv.org/abs/2409.12191)
- [Qwen Team — Qwen2.5-VL Technical Report (arXiv:2502.13923)](https://arxiv.org/abs/2502.13923)
- [Qwen Team — Qwen3-VL (arXiv:2511.21631)](https://arxiv.org/abs/2511.21631)
- [Zhu et al. — InternVL3 (arXiv:2504.10479)](https://arxiv.org/abs/2504.10479)
