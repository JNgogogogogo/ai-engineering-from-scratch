# Vision Transformers (ViT) · 视觉 Transformer

> An image is a grid of patches. A sentence is a grid of tokens. The same transformer eats both.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 7 · 05 (Full Transformer), Phase 4 · 03 (CNNs), Phase 4 · 14 (Vision Transformers intro)
**Time:** ~45 minutes

## The Problem · 问题在哪

2020 年以前，计算机视觉就是卷积。ImageNet、COCO 和检测基准上的每一个 SOTA 都用 CNN 骨干。Transformer 是语言的东西。

Dosovitskiy et al.（2020）——"An Image is Worth 16x16 Words"——证明你可以把卷积完全扔掉。把图像切成固定大小的 patch，把每个 patch 线性投影成一个 embedding，把序列喂给普通的 transformer 编码器。规模足够时（ImageNet-21k 预训练或更大），ViT 追平或击败 ResNet 系模型。

ViT 是 2026 年一个更大趋势的起点：一种架构，多种模态。Whisper 把音频 token 化。ViT 把图像 token 化。机器人有动作 token。视频有像素 token。Transformer 不在乎——喂它一个序列，它就学。

到 2026 年，ViT 及其后代（DeiT、Swin、DINOv2、ViT-22B、SAM 3）拿下了视觉的大半壁江山。CNN 仍然在边缘设备和延迟敏感任务上占优。除此之外的一切，栈里的某个地方都有 ViT。

> Before 2020, computer vision meant convolutions. Every SOTA on ImageNet, COCO, and detection benchmarks used a CNN backbone. Transformers were for language.
> Dosovitskiy et al. (2020) — "An Image is Worth 16x16 Words" — showed you can drop the convolutions entirely. Slice an image into fixed-size patches, linearly project each patch into an embedding, feed the sequence to a vanilla transformer encoder. At sufficient scale (ImageNet-21k pretraining or bigger), ViT matches or beats ResNet-based models.
> ViT was the start of a broader pattern in 2026: one architecture, many modalities. Whisper tokenizes audio. ViT tokenizes images. Action tokens for robotics. Pixel tokens for video. The transformer doesn't care — feed it a sequence and it learns.
> By 2026, ViT and its descendants (DeiT, Swin, DINOv2, ViT-22B, SAM 3) own most of vision. CNNs still win on edge devices and latency-sensitive tasks. Everything else has a ViT somewhere in the stack.

## The Concept · 概念

![Image → patches → tokens → transformer](../assets/vit.svg)

### Step 1 — patchify · 第 1 步——patchify

把 `H × W × C` 的图像切成 `N × (P·P·C)` 的扁平 patch 序列。典型配置：`224 × 224` 图像、`16 × 16` patch → 196 个 patch，每个 768 个值。

```
image (224, 224, 3) → 14 × 14 grid of 16x16x3 patches → 196 vectors of length 768
```

Patch 大小就是那根杠杆。更小的 patch = 更多 token、更好分辨率、平方级的注意力开销。更大的 patch = 更粗、更便宜。

> Split a `H × W × C` image into an `N × (P·P·C)` sequence of flat patches. Typical setup: `224 × 224` image, `16 × 16` patches → 196 patches of 768 values each.
> Patch size is the lever. Smaller patches = more tokens, better resolution, quadratic attention cost. Larger patches = coarser, cheaper.

### Step 2 — linear embedding · 第 2 步——线性嵌入

一个可学习的矩阵把每个扁平 patch 投影到 `d_model`。等价于 kernel 大小为 `P`、stride 为 `P` 的卷积。在 PyTorch 里字面上就是 `nn.Conv2d(C, d_model, kernel_size=P, stride=P)`——两行的实现。

> A single learned matrix projects each flat patch to `d_model`. Equivalent to a convolution of kernel size `P` and stride `P`. In PyTorch this is literally `nn.Conv2d(C, d_model, kernel_size=P, stride=P)` — a 2-line implementation.

### Step 3 — prepend `[CLS]` token, add positional embeddings · 第 3 步——前置 `[CLS]` token、加位置 embedding

- 前置一个可学习的 `[CLS]` token。它最终的隐状态就是用于分类的图像表示。
- 加可学习的位置 embedding（ViT 原版）或二维正弦编码（后来的变体）。
- 2024 年起 RoPE 扩展到二维位置，有时甚至不用显式 embedding。

> - Prepend a learnable `[CLS]` token. Its final hidden state is the image representation used for classification.
> - Add learnable positional embeddings (ViT-original) or sinusoidal 2D (later variants).
> - In 2024+ RoPE extended to 2D for position, sometimes without explicit embeddings.

### Step 4 — standard transformer encoder · 第 4 步——标准 transformer 编码器

堆 L 个 `LayerNorm → Self-Attention → + → LayerNorm → MLP → +` 块。与 BERT 完全一样。没有任何视觉专用层。这就是这篇论文的教学金句。

> Stack L blocks of `LayerNorm → Self-Attention → + → LayerNorm → MLP → +`. Identical to BERT. No vision-specific layers. This is the pedagogical punchline of the paper.

### Step 5 — head · 第 5 步——输出头

分类时：取 `[CLS]` 隐状态 → 线性层 → softmax。DINOv2 或 SAM 则丢掉 `[CLS]`，直接用 patch embedding。

> For classification: take `[CLS]` hidden state → linear → softmax. For DINOv2 or SAM, discard `[CLS]`, use the patch embeddings directly.

### Variants that mattered · 举足轻重的变体

| 模型 | 年份 | 变化 |
|------|------|------|
| ViT | 2020 | 原版。固定 patch 大小，全量全局注意力。 |
| DeiT | 2021 | 蒸馏；只在 ImageNet-1k 上就能训练。 |
| Swin | 2021 | 移位窗口的层级结构。开销固定为亚二次。 |
| DINOv2 | 2023 | 自监督（无标签）。最好的通用视觉特征。 |
| ViT-22B | 2023 | 22B 参数；缩放定律适用。 |
| SigLIP | 2023 | ViT + 语言配对，sigmoid 对比损失。 |
| SAM 3 | 2025 | 分割一切；ViT-Large + 可提示的 mask 解码器。 |

### Why it took a while · 为什么姗姗来迟

ViT 需要*海量*数据才能追平 CNN，因为它没有 CNN 的任何归纳偏置（inductive bias：平移不变性、局部性）。没有超过 1 亿的标注图像或强大的自监督预训练，同等算力下 CNN 仍然赢。DeiT 在 2021 年用蒸馏技巧缓解了这个问题；DINOv2 在 2023 年用自监督永久解决了它。

```figure
n5-patch-stream
```

> ViT needs *a lot* of data to match CNNs because it has none of the CNN inductive biases (translation invariance, locality). Without >100M labeled images or strong self-supervised pretraining, CNNs still win at matched compute. DeiT fixed this in 2021 with distillation tricks; DINOv2 fixed it permanently in 2023 with self-supervision.

## Build It · 动手造

见 `code/main.py`。纯标准库的 patchify + 线性嵌入 + sanity check。不训练——任何现实规模的 ViT 都需要 PyTorch 和数小时的 GPU 时间。

> See `code/main.py`. Pure-stdlib patchify + linear embedding + sanity checks. No training — ViT at any realistic scale needs PyTorch and hours of GPU time.

### Step 1: fake image · 第 1 步：假图像

一张 24 × 24 的 RGB 图像，表示为按行排列的 `(R, G, B)` 元组列表。我们用 6×6 的 patch → 16 个 patch，每个是 108 维的 embedding 向量。

> A 24 × 24 RGB image as a list of rows of `(R, G, B)` tuples. We use 6×6 patches → 16 patches, 108-d embedding vector each.

### Step 2: patchify · 第 2 步：patchify

```python
def patchify(image, P):
    H = len(image)
    W = len(image[0])
    patches = []
    for i in range(0, H, P):
        for j in range(0, W, P):
            patch = []
            for di in range(P):
                for dj in range(P):
                    patch.extend(image[i + di][j + dj])
            patches.append(patch)
    return patches
```

光栅顺序：网格上按行优先。每个 ViT 都用这个顺序。

> Raster order: row-major across the grid. Every ViT uses this ordering.

### Step 3: linear embed · 第 3 步：线性嵌入

每个扁平 patch 乘一个随机的 `(patch_flat_size, d_model)` 矩阵。验证前置 `[CLS]` 后输出形状是 `(N_patches + 1, d_model)`。

> Multiply each flat patch by a random `(patch_flat_size, d_model)` matrix. Verify output shape is `(N_patches + 1, d_model)` after prepending `[CLS]`.

### Step 4: count parameters for a realistic ViT · 第 4 步：数一数真实 ViT 的参数

打印 ViT-Base 的参数量：12 层、12 头、d=768、patch=16。与 ResNet-50（约 25M）对比。ViT-Base 落在约 86M。ViT-Large 约 307M。ViT-Huge 约 632M。

> Print the param count for ViT-Base: 12 layers, 12 heads, d=768, patch=16. Compare to ResNet-50 (~25M). ViT-Base lands at ~86M. ViT-Large ~307M. ViT-Huge ~632M.

## Use It · 实战用法

```python
from transformers import ViTImageProcessor, ViTModel
import torch
from PIL import Image

processor = ViTImageProcessor.from_pretrained("google/vit-base-patch16-224-in21k")
model = ViTModel.from_pretrained("google/vit-base-patch16-224-in21k")

img = Image.open("cat.jpg")
inputs = processor(img, return_tensors="pt")
out = model(**inputs).last_hidden_state   # (1, 197, 768): [CLS] + 196 patches
cls_emb = out[:, 0]                       # image representation
```

**DINOv2 embedding 是 2026 年图像特征的默认选择。** 冻结骨干，训练一个小头。分类、检索、检测、描述生成全都适用。Meta 的 DINOv2 checkpoint 在每个非文本视觉任务上都胜过 CLIP。

**Patch 大小的选择。** 小模型用 16×16（ViT-B/16）。稠密预测（分割）用 8×8 或 14×14（SAM、DINOv2）。超大规模模型用 14×14。

> **DINOv2 embeddings are the 2026 default for image features.** Freeze the backbone, train a tiny head. Works for classification, retrieval, detection, captioning. Meta's DINOv2 checkpoints outperform CLIP on every non-text vision task.
> **Patch-size picking.** Small models use 16×16 (ViT-B/16). Dense prediction (segmentation) uses 8×8 or 14×14 (SAM, DINOv2). Very large models use 14×14.

## Ship It · 交付

见 `outputs/skill-vit-configurator.md`。这个 skill 依据数据集规模、分辨率和算力预算，为新视觉任务挑选 ViT 变体和 patch 大小。

> See `outputs/skill-vit-configurator.md`. The skill picks a ViT variant and patch size for a new vision task given dataset size, resolution, and compute budget.

## Exercises · 练习

1. **简单。** 跑 `code/main.py`。验证 patch 数量等于 `(H/P) * (W/P)`，扁平 patch 维度等于 `P*P*C`。
2. **中等。** 实现二维正弦位置 embedding——为每个 patch 的 `row` 和 `col` 各编一套独立的正弦码，再拼接。喂给一个微型 PyTorch ViT，在 CIFAR-10 上与可学习位置 embedding 比准确率。
3. **困难。** 搭一个 3 层 ViT（PyTorch），用 4×4 patch 在 1,000 张 MNIST 图像上训练。测测试集准确率。然后在这同样的 1,000 张图上加 DINOv2 预训练（简化版：只训练编码器从被 mask 的 patch 预测 patch embedding）。准确率会提升吗？

> 1. **Easy.** Run `code/main.py`. Verify the number of patches equals `(H/P) * (W/P)` and the flat patch dimension equals `P*P*C`.
> 2. **Medium.** Implement 2D sinusoidal positional embeddings — two independent sinusoidal codes for `row` and `col` of each patch, concatenated. Feed them into a tiny PyTorch ViT and compare accuracy vs learnable positional embeddings on CIFAR-10.
> 3. **Hard.** Build a 3-layer ViT (PyTorch), train on 1,000 MNIST images with 4×4 patches. Measure test accuracy. Now add DINOv2 pretraining on the same 1,000 images (simplified: just train the encoder to predict patch embeddings from masked patches). Does accuracy improve?

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------|---------|
| Patch | 「视觉 transformer 的 token」 | 图像中一个 `P × P × C` 区域的像素值扁平向量。 |
| Patchify | 「切块 + 拉平」 | 把图像切成不重叠的 patch，每个拉平成向量。 |
| `[CLS]` token | 「图像摘要」 | 前置的可学习 token；它最终的 embedding 就是图像表示。 |
| Inductive bias（归纳偏置） | 「模型自带的假设」 | ViT 的先验比 CNN 少；需要更多数据来补差距。 |
| DINOv2 | 「自监督 ViT」 | 用图像增强 + 动量教师网络无标签训练。2026 年最好的通用图像特征。 |
| SigLIP | 「CLIP 的继任者」 | ViT + 文本编码器，用 sigmoid 对比损失训练；同等算力下比 CLIP 好。 |
| Swin | 「开窗口的 ViT」 | 局部注意力 + 移位窗口的层级 ViT；亚二次复杂度。 |
| Register tokens | 「2023 年的技巧」 | 几个额外的可学习 token，用来吸收注意力汇（attention sink）；改善 DINOv2 特征。 |

## Further Reading · 延伸阅读

- [Dosovitskiy et al. (2020). An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale](https://arxiv.org/abs/2010.11929) —— ViT 论文。
- [Touvron et al. (2021). Training data-efficient image transformers & distillation through attention](https://arxiv.org/abs/2012.12877) —— DeiT。
- [Liu et al. (2021). Swin Transformer: Hierarchical Vision Transformer using Shifted Windows](https://arxiv.org/abs/2103.14030) —— Swin。
- [Oquab et al. (2023). DINOv2: Learning Robust Visual Features without Supervision](https://arxiv.org/abs/2304.07193) —— DINOv2。
- [Darcet et al. (2023). Vision Transformers Need Registers](https://arxiv.org/abs/2309.16588) —— 修复 DINOv2 的 register-token 方案。
