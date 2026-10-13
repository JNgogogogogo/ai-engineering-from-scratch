# Video Generation · 视频生成

> An image is a 2-D tensor. A video is a 3-D one. The theory is the same; the compute is 10-100x harder. OpenAI's Sora (Feb 2024) proved it was possible. By 2026 Veo 2, Kling 1.5, Runway Gen-3, Pika 2.0, and WAN 2.2 ship production video from text at 1080p — and the open-weights stack (CogVideoX, HunyuanVideo, Mochi-1, WAN 2.2) is 12 months behind.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 8 · 07 (Latent Diffusion), Phase 7 · 09 (ViT), Phase 8 · 06 (DDPM)
**Time:** ~45 minutes

## The Problem · 问题

一段 24fps 的 10 秒 1080p 视频是 240 帧 1920×1080×3 像素。每段约 1.5 GB 原始数据。像素空间扩散不可行。你需要：

1. **时空压缩。** 一个对视频（而非单帧）编码的 VAE，编码成时空 patch 序列。
2. **时间一致性。** 相邻帧需要在数秒的跨度上共享内容、光照和物体身份。网络必须对运动建模。
3. **算力预算。** 同样的模型规模下，视频训练比图像贵 10-100 倍。
4. **条件化。** 文本、图像（首帧）、音频或另一段视频。大多数生产模型四种都接受。

解决这个问题的架构是作用在时空 patch 上的 **Diffusion Transformer（DiT）**，在海量（prompt, caption, video）数据集上训练。扩散损失与第 06 课相同。

> A 10-second 1080p video at 24fps is 240 frames of 1920×1080×3 pixels ... You need: ... The architecture that solved this is the **Diffusion Transformer (DiT)** applied to spatiotemporal patches, trained on huge (prompt, caption, video) datasets. Same diffusion loss as Lesson 06.

## The Concept · 概念

![视频扩散：切 patch、DiT、解码](../assets/video-generation.svg)

### Patchify · 切 patch

用一个 3D VAE（学出来的时空压缩）编码视频。latent 形状为 `[T_latent, H_latent, W_latent, C_latent]`。再切成大小为 `[t_p, h_p, w_p]` 的 patch。对 Sora 风格的模型，`t_p = 1`（逐帧 patch）或 `t_p = 2`（每两帧一个）。一段 10 秒 1080p 视频压缩后约为 2 万到 10 万个 patch。

> Encode the video with a 3D VAE (learned spatiotemporal compression). The latent is shape `[T_latent, H_latent, W_latent, C_latent]` ... A 10-second 1080p video compresses to ~20,000-100,000 patches.

### Spatiotemporal DiT · 时空 DiT

一个 transformer 处理扁平化的 patch 序列。每个 patch 带一个 3D 位置嵌入（时间 + y + x）。注意力通常做因式分解：

- **空间注意力**作用于每帧内部的 patch。
- **时间注意力**跨帧作用于同一空间位置。
- **完整 3D 注意力**要贵 16-100 倍；只在低分辨率或研究场景使用。

> A transformer processes the flat sequence of patches. Each patch has a 3D positional embedding (time + y + x). Attention is usually factorized ... **Full 3D attention** is 16-100x more expensive; used only at low resolution or in research.

### Text conditioning · 文本条件化

用大型文本编码器做交叉注意力（Sora 用 T5-XXL，CogVideoX-5B 也用 T5-XXL）。长 prompt 很重要 —— Sora 的训练集配了 GPT 生成的密集重写描述（re-caption），平均每段视频 200 个 token。

> Cross-attention with a large text encoder (T5-XXL for Sora, CogVideoX-5B uses T5-XXL). Long prompts matter — Sora's training set had GPT-generated dense re-captions averaging 200 tokens per clip.

### Training · 训练

在时空 latent 上用标准扩散损失（ε 或 v 预测）。数据：网络视频 + 约 1 亿条精选片段 + 合成文本描述。算力：即便一个小型研究项目也要 1 万+ GPU 小时；Sora 量级是 10 万+。

> Standard diffusion loss (ε or v prediction) over spatiotemporal latents. Data: web video + ~100M curated clips + synthetic text captions. Compute: 10,000+ GPU hours for even a small research run; Sora-scale is 100,000+.

## The 2026 production landscape · 2026 年生产格局

| 模型 | 时间 | 最大时长 | 最大分辨率 | 开放权重？ | 备注 |
|-------|------|--------------|---------|---------------|---------|
| Sora (OpenAI) | 2024-02 | 60s | 1080p | 否 | 首个在大规模上展示「世界模拟器」特性的模型 |
| Sora Turbo | 2024-12 | 20s | 1080p | 否 | 生产版 Sora，推理快 5 倍 |
| Veo 2 (Google) | 2024-12 | 8s | 4K | 否 | 2025 年画质 + 物理模拟最佳 |
| Veo 3 | 2025 Q3 | 15s | 4K | 否 | 原生音频与更强的镜头控制 |
| Kling 1.5 / 2.1 (快手) | 2024-2025 | 10s | 1080p | 否 | 2025 Q1 最佳人体运动 |
| Runway Gen-3 Alpha | 2024-06 | 10s | 768p | 否 | 上面叠了一层专业视频工具 |
| Pika 2.0 | 2024-10 | 5s | 1080p | 否 | 最强的角色一致性 |
| CogVideoX (THUDM) | 2024 | 10s | 720p | 是（2B、5B） | 首个开放的 5B 量级视频模型 |
| HunyuanVideo (腾讯) | 2024-12 | 5s | 720p | 是（13B） | 2024 年末的开放 SOTA |
| Mochi-1 (Genmo) | 2024-10 | 5.4s | 480p | 是（10B） | 许可证最宽松 |
| WAN 2.2 (阿里巴巴) | 2025-07 | 5s | 720p | 是 | 2025 年中最强的开放模型 |

开放权重追赶的速度比图像领域更快：到 2026 年年中，HunyuanVideo + WAN 2.2 LoRA 已经支撑着大多数开源工作流。

```figure
video-diffusion-denoise
```

> Open weights are closing the gap faster than in the image space: HunyuanVideo + WAN 2.2 LoRAs already power most open-source workflows by mid-2026.

## Build It · 动手造

`code/main.py` 模拟时空 DiT 的核心思想：把一段小型合成视频切成 patch，给每个 patch 加位置嵌入，然后用 transformer 风格的 patch 注意力对整个序列去噪。不用 numpy；纯 Python。我们展示：只要相邻帧的 patch 共享同一个去噪器和位置嵌入，时间一致性即便在 1-D 里也会涌现。

> `code/main.py` simulates the core spatiotemporal DiT idea: patchify a small synthetic video, add a per-patch position embedding, and denoise the whole sequence with a transformer-style attention over patches. No numpy; pure Python. ... We show that temporal coherence emerges even in 1-D when adjacent-frame patches share a denoiser and position embeddings.

### Step 1: patchify a synthetic 1-D "video" · 第 1 步：切分合成的 1-D「视频」

```python
def make_video(T_frames=8, rng=None):
    # a "video" is a sequence of 1-D values following a smooth trajectory
    base = rng.gauss(0, 1)
    return [base + 0.3 * t + rng.gauss(0, 0.1) for t in range(T_frames)]
```

### Step 2: position embedding per frame · 第 2 步：逐帧位置嵌入

```python
def pos_embed(t, dim):
    return sinusoidal(t, dim)
```

### Step 3: denoiser sees the whole sequence · 第 3 步：去噪器看到整个序列

我们的小网络不是对每一帧独立去噪，而是把所有帧的取值 + 各自的位置嵌入拼接起来，联合预测所有帧的噪声。

> Instead of denoising each frame independently, our tiny net concatenates all frame values + their position embeddings and predicts the noise for all frames jointly.

### Step 4: temporal coherence test · 第 4 步：时间一致性测试

训练完成后采样一段视频。测量帧间差值。如果模型学到了时间结构，这些差值会比逐帧独立采样更小。

> After training, sample a video. Measure the frame-to-frame delta. If the model has learned temporal structure, the deltas stay smaller than sampling each frame independently.

## Pitfalls · 常见坑

- **逐帧独立采样 = 闪烁。** 如果对每一帧分别跑图像扩散，输出会闪烁，因为每帧的噪声相互独立。视频扩散通过注意力或共享噪声把帧耦合起来解决这个问题。
- **朴素 3D 注意力 = OOM。** 对 10 秒 1080p 的 latent 做完整 3D 注意力是几千亿量级的运算。要分解成空间 + 时间。
- **数据描述比数据量更重要。** Sora 相对此前工作的主要升级，是在描述细致约 10 倍的数据上训练（GPT-4 重新标注的片段）。OpenAI 的技术报告对此说得很明白。
- **首帧条件化。** 大多数生产模型还接受一张图作为首帧。这就是「图生视频」（image-to-video）模式；训练覆盖了这个变体。
- **物理漂移。** 长片段（>10 秒）会累积细微的不一致。滑窗生成 + 关键帧锚定有帮助。

> **Independent per-frame sampling = flicker.** ... Video diffusion fixes this by coupling the frames through attention or shared noise ... **Data captioning matters more than size.** Sora's main upgrade over prior work was training on ~10x more detailed captions (GPT-4 re-labelled clips). OpenAI's technical report is explicit on this ... **Physics drift.** Long clips (>10s) accumulate subtle inconsistencies. Sliding-window generation + keyframe anchoring helps.

## Use It · 实战用法

| 用例 | 2026 年选择 |
|----------|-----------|
| 最高质量的文生视频、托管 | Veo 3 或 Sora |
| 镜头可控的电影感镜头 | Runway Gen-3 加运动笔刷 |
| 跨片段的角色一致性 | Pika 2.0 或 Kling 2.1 |
| 开放权重、快速微调 | WAN 2.2 + LoRA |
| 图生视频 | WAN 2.2-I2V、Kling 2.1 I2V 或 Runway |
| 音频驱动的唇形同步 | Veo 3（原生音频）或专用唇形同步模型 |
| 视频编辑 | Runway Act-Two、Kling Motion Brush、Flux-Kontext（静帧） |

同等质量下，每秒视频的成本在 2024 到 2026 年间下降了 20 倍。

> Cost per second of video at quality parity has dropped 20x between 2024 and 2026.

## Ship It · 交付

保存 `outputs/skill-video-brief.md`。这个 skill 接收一份视频需求单（时长、宽高比、风格、镜头计划、主体一致性、音频），输出：模型 + 托管方案、prompt 脚手架（镜头语言、主体描述、运动描述符）、seed 与可复现协议，以及一份逐帧 QA 检查清单。

> Save `outputs/skill-video-brief.md`. Skill takes a video brief (duration, aspect ratio, style, camera plan, subject consistency, audio) and outputs: model + hosting, prompt scaffolding (camera language, subject description, motion descriptors), seed + reproducibility protocol, and a frame-level QA checklist.

## Exercises · 练习

1. **简单。** 在 `code/main.py` 里对比 (a) 逐帧独立采样与 (b) 联合序列采样的帧间差值。报告差值的均值与方差。
2. **中等。** 加一个首帧条件：把第 0 帧钉在给定值上，采样其余帧。测量钉住的值如何向后传播。
3. **困难。** 用 HuggingFace diffusers 在本地 GPU 上跑 CogVideoX-2B。给一段 6 秒 720p 片段的 20 步推理计时。对时空注意力做性能分析，找出瓶颈。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Video VAE | 「3-D VAE」 | 把 `(T, H, W, C)` 压缩成时空 latent 的编码器。 |
| Patches | 「那些 token」 | latent 上固定大小的 3-D 块；DiT 的输入。 |
| Factorized attention | 「空间 + 时间」 | 先在空间上做注意力，再在时间上做；跳过完整 3D 注意力。 |
| Image-to-video (I2V) | 「让这张照片动起来」 | 模型接收图像 + 文本，输出以它开头的视频。 |
| Keyframe conditioning | 「锚定帧」 | 把特定帧钉住，控制视频的走向。 |
| Motion brush | 「方向提示」 | 一种 UI 输入，用户在图上涂刷运动矢量。 |
| Re-captioning | 「密集描述」 | 用 LLM 给训练片段重新标注细致的 prompt。 |
| Flicker | 「时间伪影」 | 帧间不一致；用耦合去噪解决。 |

## Production note: video latents are a memory-bandwidth problem · 生产备注：视频 latent 是内存带宽问题

一段 24fps 的 10 秒 1080p 片段是 240 帧 × 1920 × 1080 × 3 ≈ 1.5 GB 原始像素。经过 4 倍视频 VAE 压缩（`2 × spatial × 2 × temporal`）之后，每个请求的 latent 约 100 MB。把它以 batch 1 送进时空 DiT 跑 30 步，意味着每步有约 3 GB 数据穿过 HBM —— 瓶颈是内存带宽，不是 FLOP。

三个生产旋钮，全部直接来自生产推理文献的推理章节：

- **DiT 上的张量并行（TP）。** 文生视频模型的参数量动辄 ≥100 亿。TP=4 横跨 4 张 H100 是标准做法；405B 量级的模型用 PP=2 × TP=2。每步延迟随 TP 大致线性下降，直到撞上 all-reduce 之墙。
- **帧批处理 = continuous batching。** 在生成时，视频在概念上就是一批由注意力连接起来的帧。Continuous batching（in-flight 调度）同样适用：如果模型架构允许滑窗生成，就在返回帧 `t-1` 的同时开始渲染帧 `t+1`。
- **片段级 prefill 缓存。** 对图生视频，首帧条件化类似 LLM 的 prompt prefill：计算一次，然后在时间维度解码的各轮中复用。这实际上就是视频的 KV-cache。

> A 10-second 1080p clip at 24 fps is 240 frames × 1920 × 1080 × 3 ≈ 1.5 GB of raw pixels ... memory bandwidth, not FLOPs, is the bottleneck ... **TP across the DiT.** Text-to-video models are routinely ≥10B params. TP=4 across 4 H100s is standard ... **Clip-level prefill cache.** ... This is effectively a KV-cache for video.

## Further Reading · 延伸阅读

- [Brooks et al. (2024). Video generation models as world simulators](https://openai.com/index/video-generation-models-as-world-simulators/) —— Sora 技术报告。
- [Yang et al. (2024). CogVideoX: Text-to-Video Diffusion Models with An Expert Transformer](https://arxiv.org/abs/2408.06072) —— CogVideoX。
- [Kong et al. (2024). HunyuanVideo: A Systematic Framework for Large Video Generative Models](https://arxiv.org/abs/2412.03603) —— HunyuanVideo。
- [Genmo (2024). Mochi-1 Technical Report](https://www.genmo.ai/blog/mochi) —— Mochi-1。
- [Alibaba (2025). WAN 2.2](https://wanvideo.io/) —— 2025 年中的开放 SOTA。
- [Ho, Salimans, Gritsenko et al. (2022). Video Diffusion Models](https://arxiv.org/abs/2204.03458) —— 视频扩散的开山论文。
- [Blattmann et al. (2023). Align your Latents (Video LDM)](https://arxiv.org/abs/2304.08818) —— Stable Video Diffusion 的前身。
