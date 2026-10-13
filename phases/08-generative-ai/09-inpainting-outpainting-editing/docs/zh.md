# Inpainting, Outpainting & Image Editing · 图像修复、外扩与图像编辑

> Text-to-image makes new things. Inpainting fixes old ones. In production, 70% of billable image work is editing — swap a background, remove a logo, extend the canvas, regenerate a hand. Inpainting is where diffusion earns its keep.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 8 · 07 (Latent Diffusion), Phase 8 · 08 (ControlNet & LoRA)
**Time:** ~75 minutes

## The Problem · 问题

客户发来一张完美的产品照，背景里有一块碍事的招牌。你想抹掉招牌，其余部分保持像素级不变。你不能从头跑文生图 —— 结果会有不同的颜色、不同的光照、不同的产品角度。你只想*重新生成*被遮罩（mask）的区域，并且让重生成尊重周围的上下文。

这就是图像修复（inpainting）。几种变体：

- **Inpainting（修复）。** 在遮罩内重生成，遮罩外像素保持不变。
- **Outpainting（外扩）。** 在遮罩外（或画布之外）重生成，遮罩内保持不变。
- **Image editing（图像编辑）。** 重生成整张图，但保持对原图的语义或结构保真（SDEdit、InstructPix2Pix）。

2026 年每一个扩散 pipeline 都自带修复模式。Flux.1-Fill、Stable Diffusion Inpaint、SDXL-Inpaint、DALL-E 3 Edit。它们遵循同一个原理。

> A client sends a perfect product photo with a distracting sign in the background ... You want to regenerate *only* the masked region, and you want the regeneration to respect the surrounding context ... Every diffusion pipeline in 2026 ships an inpainting mode. Flux.1-Fill, Stable Diffusion Inpaint, SDXL-Inpaint, DALL-E 3 Edit. They work on the same principle.

## The Concept · 概念

![图像修复：遮罩感知的去噪与保上下文回注](../assets/inpainting.svg)

### The naive approach (and why it's wrong) · 朴素做法（以及它为什么是错的）

用标准文生图加一个遮罩来跑。每个采样步，把带噪 latent 的未遮罩区域替换成前向扩散后的干净图像。它能跑……但效果很糟。边界伪影会渗透出来，因为模型对遮罩区域里有什么一无所知。

> Run standard text-to-image with a mask. At each sampling step, replace the unmasked region of the noisy latent with the forward-diffused clean image. It works... badly. Boundary artifacts bleed through because the model has no information about what is in the masked region.

### The proper inpainting model · 正经的修复模型

训练一个改造过的 U-Net，输入通道从 4 个变成 9 个：

```
input = concat([ noisy_latent (4ch), encoded_image (4ch), mask (1ch) ], dim=channel)
```

多出来的通道是 VAE 编码后的源图副本，再加一个单通道遮罩。训练时，随机遮住图像的一些区域，训练模型只对被遮区域去噪，未遮区域作为干净的条件信号给出。推理时，模型能「看见」被遮区域周围的东西，产出连贯的补全。

SD-Inpaint、SDXL-Inpaint、Flux-Fill 都用这种 9 通道（或类似）输入。Diffusers 里对应 `StableDiffusionInpaintPipeline`、`FluxFillPipeline`。

> Train a modified U-Net that takes 9 input channels instead of 4 ... The extra channels are a copy of the VAE-encoded source image plus a single-channel mask ... At inference, the model can "see" what surrounds the masked region and produces coherent completions ... SD-Inpaint, SDXL-Inpaint, Flux-Fill all use this 9-channel (or analog) input.

### SDEdit (Meng et al., 2022) — free editing · SDEdit（Meng et al., 2022）—— 免训练编辑

给源图加噪到某个中间时刻 `t`，然后带着一个新 prompt，把反向链从 `t` 跑回 0。无需重训。起始 `t` 的选择是在保真与创作自由之间做交换：

- `t/T = 0.3` → 与源图几乎一致，只有细微的风格变化
- `t/T = 0.6` → 中等幅度的编辑，保留粗略结构
- `t/T = 0.9` → 接近从纯噪声生成，几乎不保留源图

> Add noise to the source image up to some intermediate `t`, then run the reverse chain from `t` down to 0 with a new prompt. No retraining. The choice of starting `t` trades fidelity for creative freedom ...

### InstructPix2Pix (Brooks et al., 2023) · InstructPix2Pix（Brooks et al., 2023）

在 `(input_image, instruction, output_image)` 三元组上微调一个扩散模型。推理时同时以输入图像和文本指令为条件（「让它变日落」「加一条龙」）。两个 CFG scale：图像 scale 和文本 scale。

> Fine-tune a diffusion model on `(input_image, instruction, output_image)` triples. At inference, condition on both the input image and a text instruction ("make it sunset", "add a dragon"). Two CFG scales: image scale and text scale.

### RePaint (Lugmayr et al., 2022) · RePaint（Lugmayr et al., 2022）

保留一个标准的无条件扩散模型。在每个反向步重采样 —— 偶尔跳回更噪的状态再重新生成。避免边界伪影。用在你没有训练好的修复模型的时候。

> Keep a standard unconditional diffusion model. At each reverse step, resample — jump back to a noisier state occasionally and regenerate. Avoids boundary artifacts. Used when you don't have a trained inpainting model.

```figure
inpaint-mask-reinject
```

## Build It · 动手造

`code/main.py` 在 5 维数据上实现一个玩具级 1-D 修复方案。我们在 5-D 混合数据上训练一个 DDPM，每个样本是来自两个簇之一的 5 个浮点数。推理时，我们「遮住」5 个维度中的 2 个，每一步把未遮的 3 个维度以加噪前向的形式注入回去，只重新生成被遮的维度。

> `code/main.py` implements a toy 1-D inpainting scheme on 5-dimensional data ... At inference, we "mask" 2 of the 5 dimensions, inject the noisy-forward version of the unmasked three at each step, and regenerate only the masked dimensions.

### Step 1: 5-D DDPM data · 第 1 步：5-D DDPM 数据

```python
def sample_data(rng):
    cluster = rng.choice([0, 1])
    center = [-1.0] * 5 if cluster == 0 else [1.0] * 5
    return [c + rng.gauss(0, 0.2) for c in center], cluster
```

### Step 2: train denoiser over all 5 dims · 第 2 步：在全部 5 个维度上训练去噪器

标准 DDPM。网络对 5-D 带噪输入输出 5-D 噪声预测。

> Standard DDPM. Net outputs 5-D noise prediction for 5-D noisy input.

### Step 3: at inference, mask-aware reverse · 第 3 步：推理时的遮罩感知反向

```python
def inpaint_step(x_t, mask, clean_image, alpha_bars, t, rng):
    # replace unmasked dims with a freshly noised version of the clean source
    a_bar = alpha_bars[t]
    for i in range(len(x_t)):
        if not mask[i]:
            x_t[i] = math.sqrt(a_bar) * clean_image[i] + math.sqrt(1 - a_bar) * rng.gauss(0, 1)
    # ...then run the normal reverse step on x_t
```

这就是朴素做法，在玩具级 1-D 数据上够用。真实的图像修复用 9 通道输入，因为纹理连贯性重要得多。

> This is the naive approach and it works on toy 1-D data. Real image inpainting uses the 9-channel input because texture coherence matters more.

### Step 4: outpainting · 第 4 步：外扩

外扩就是遮罩取反的修复：遮住新的（原本不存在的）画布区域，其余用原图填充。训练目标完全相同。

> Outpainting is inpainting with the mask inverted: mask the new (previously non-existent) canvas, fill the rest with the original. Identical training objective.

## Pitfalls · 常见坑

- **接缝。** 朴素做法会留下可见的边界，因为梯度信息无法跨越遮罩流动。修复办法：把遮罩膨胀 8-16 像素，或者用正经的修复模型。
- **遮罩泄漏。** 如果条件图像的未遮区域低质或有噪声，会污染遮罩内的生成结果。先去噪或轻微模糊。
- **CFG 与遮罩大小互相作用。** 小遮罩配高 CFG = 一块过饱和的补丁。小编辑就调低 CFG。
- **SDEdit 保真悬崖。** 从 `t/T = 0.5` 调到 `t/T = 0.6` 就可能丢掉主体的身份特征。要扫描参数并保存检查点。
- **Prompt 不匹配。** Prompt 应该描述*整张*图像，而不只是新内容。「一只坐在椅子上的猫」而不是「一只猫」。

> **Seams.** The naive approach leaves visible boundaries because gradient info doesn't flow across the mask ... **CFG interacts with mask size.** High CFG on a small mask = saturated patch. Reduce CFG for small edits ... **Prompt mismatch.** The prompt should describe the *whole* image, not just the new content. "A cat sitting on a chair" not "a cat".

## Use It · 实战用法

| 任务 | Pipeline |
|------|----------|
| 去除物体、小遮罩 | SD-Inpaint 或 Flux-Fill，标准 prompt |
| 替换天空 | SD-Inpaint + "blue sky at sunset" |
| 扩展画布 | SDXL 外扩模式（8px 羽化）或 Flux-Fill 加外扩遮罩 |
| 重生成手 / 脸 | SD-Inpaint，prompt 重新描述主体 + ControlNet-Openpose |
| 改变某个区域的风格 | SDEdit 在 `t/T=0.5` 作用于遮罩区域 |
| 「让它变日落」 | InstructPix2Pix 或 Flux-Kontext |
| 背景替换 | SAM 遮罩 → SD-Inpaint |
| 超高保真 | 最难的情形用 Flux-Fill 或 GPT-Image（托管） |

SAM（Meta 的 Segment Anything，2023）+ 扩散修复是 2026 年的背景去除流水线。SAM 2（2024）可以处理视频。

> SAM (Meta's Segment Anything, 2023) + diffusion inpaint is the 2026 background-removal pipeline. SAM 2 (2024) works on video.

## Ship It · 交付

保存 `outputs/skill-editing-pipeline.md`。这个 skill 接收一张原图 + 编辑描述 + 可选遮罩（或 SAM prompt），输出：遮罩生成方案、底座模型、CFG scale（图像 + 文本）、SDEdit-t 或修复模式，以及一份 QA 检查清单。

> Save `outputs/skill-editing-pipeline.md`. Skill takes an original image + edit description + optional mask (or SAM prompt) and outputs: mask-generation approach, base model, CFG scales (image + text), SDEdit-t or inpainting mode, and QA checklist.

## Exercises · 练习

1. **简单。** 在 `code/main.py` 里把被遮维度的比例从 0.2 变到 0.8。比例到多少时，修复质量（被遮维度上的残差）等同于无条件生成？
2. **中等。** 实现 RePaint：每隔 10 个反向步，往回跳 5 步（加噪）再重新去噪。测量它是否降低了遮罩边缘处的边界残差。
3. **困难。** 用 Hugging Face diffusers 对比：在 20 个人脸重生成任务上比较 SD 1.5 Inpaint + ControlNet-Openpose 与 Flux.1-Fill。分别给姿态遵循度和身份保持打分。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Inpainting | 「补洞」 | 在遮罩内重生成；遮罩外像素保持不变。 |
| Outpainting | 「扩展画布」 | 在画布外重生成；画布内保持不变。 |
| 9-channel U-Net | 「正经的修复模型」 | 输入为 `noisy \| encoded-source \| mask` 的 U-Net。 |
| SDEdit | 「带噪声等级的 img2img」 | 加噪到时刻 `t`，再用新 prompt 去噪。 |
| InstructPix2Pix | 「纯文本编辑」 | 在（图像，指令，输出）三元组上微调的扩散模型。 |
| RePaint | 「无需重训」 | 反向过程中周期性重新加噪，减少接缝。 |
| SAM | 「Segment Anything」 | 通过点击或框生成遮罩；与修复搭配使用。 |
| Flux-Kontext | 「带上下文的编辑」 | 接受参考图 + 指令做编辑的 Flux 变体。 |

## Production note: edit pipelines are latency-sensitive · 生产备注：编辑流水线对延迟敏感

编辑图像的用户期望 5 秒以内的往返。1024² 下 30 步的 SDXL-Inpaint 在 L4 上要 3-4 秒，再加上 SAM 遮罩生成（约 200 ms）和 VAE 编解码（合计约 500 ms）。按生产框架来说，这是受 TTFT 约束而不是吞吐约束 —— batch 1、低并发，把每个阶段都压到最小：

- **SAM-H 才是慢的那个。** 1024² 下 SAM-H 约 200 ms；SAM-ViT-B 约 40 ms，质量损失轻微。SAM 2（视频）有额外的时间维度开销；单图编辑不要用它。
- **能跳过编码就跳过。** `pipe.image_processor.preprocess(img)` 会把图像编码成 latent。如果你手里已有上一次生成的 latent（迭代式编辑 UI 的常态），直接通过 `latents=...` 传入，省掉一次 VAE 编码。
- **遮罩膨胀也影响吞吐。** 遮罩小意味着 U-Net 前向传播的大部分被浪费（未遮像素反正会被钳制）。diffusers 的 `StableDiffusionInpaintPipeline` 无论如何都跑完整 U-Net；只有 9 通道的正经修复变体才利用了遮罩化计算。
- **Flux-Kontext 是 2025 年的答案。** 对 `(source_image, instruction)` 做单次前向传播 —— 没有单独的遮罩，没有 SDEdit 噪声扫描。在 H100 上约 1.5 秒交付一次编辑。架构层面的教训：把阶段折叠掉。

> Users editing an image expect sub-5-second round trips ... this is TTFT-bound rather than throughput-bound — batch 1, low concurrency, minimize every stage ... **SAM-H is the slow one.** SAM-H at 1024² is ~200 ms; SAM-ViT-B is ~40 ms with minor quality loss ... **Flux-Kontext is the 2025 answer.** Single forward pass over `(source_image, instruction)` — no separate mask, no SDEdit noise sweep ... The architectural lesson: collapse the stages.

## Further Reading · 延伸阅读

- [Lugmayr et al. (2022). RePaint: Inpainting using Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2201.09865) —— 免训练的图像修复。
- [Meng et al. (2022). SDEdit: Guided Image Synthesis and Editing with Stochastic Differential Equations](https://arxiv.org/abs/2108.01073) —— SDEdit。
- [Brooks, Holynski, Efros (2023). InstructPix2Pix](https://arxiv.org/abs/2211.09800) —— 文本指令编辑。
- [Kirillov et al. (2023). Segment Anything](https://arxiv.org/abs/2304.02643) —— SAM，遮罩的来源。
- [Ravi et al. (2024). SAM 2: Segment Anything in Images and Videos](https://arxiv.org/abs/2408.00714) —— 视频版 SAM。
- [Hertz et al. (2022). Prompt-to-Prompt Image Editing with Cross-Attention Control](https://arxiv.org/abs/2208.01626) —— 注意力层面的编辑。
- [Black Forest Labs (2024). Flux.1-Fill and Flux.1-Kontext](https://blackforestlabs.ai/flux-1-tools/) —— 2024 年的工具链。
