# Vision Transformers and the Patch-Token Primitive · 视觉 Transformer 与 Patch-Token 原语

> 在谈任何「多模态」之前，图像必须先变成 transformer 能「吃」的 token 序列。2020 年的 ViT 论文给出的答案是：16x16 像素的 patch、一个线性投影、一个位置嵌入。五年之后，2026 年的每个前沿模型（原生 2576px 的 Claude Opus 4.7、Gemini 3.1 Pro、Qwen3.5-Omni）依然这样开场——编码器从 ViT 换成 DINOv2 再换成 SigLIP 2，加上了 register token，位置方案变成了 2D-RoPE，但这个原语从未动摇。本课从头到尾读一遍 patch-token 流水线，并用纯标准库 Python 把它造出来，让 Phase 12 的后续课程对「视觉 token」有一个具体的心智模型。
>
> Before anything multimodal, an image has to become a sequence of tokens a transformer can eat. The 2020 ViT paper answered this with 16x16 pixel patches, a linear projection, and a position embedding. Five years later every 2026 frontier model (Claude Opus 4.7 at 2576px native, Gemini 3.1 Pro, Qwen3.5-Omni) still begins this way — the encoder changed from ViT to DINOv2 to SigLIP 2, register tokens were added, the positional scheme became 2D-RoPE, but the primitive held. This lesson reads the patch-token pipeline end to end and builds it in stdlib Python so the rest of Phase 12 has a concrete mental model for "visual tokens."

**类型:** Learn
**语言:** Python（标准库，patch tokenizer + geometry calculator）
**先修:** Phase 7（Transformers）、Phase 4（Computer Vision）
**时长:** ~120 分钟

## Learning Objectives · 学习目标

- 把一张 HxWx3 的图像转换成带正确位置编码的 patch token 序列。
- 给定（patch 大小、分辨率、隐藏维度、深度），计算一个 ViT 的序列长度、参数量和 FLOPs。
- 说出让 ViT 从 2020 年研究走进 2026 年生产的三大升级：自监督预训练（DINO / MAE）、register token、原生分辨率打包。
- 针对下游任务，在 CLS pooling、mean pooling 和 register token 之间做出选择。

> Convert an HxWx3 image into a sequence of patch tokens with correct positional encoding.
> Compute sequence length, parameter count, and FLOPs for a ViT of a given (patch size, resolution, hidden dim, depth).
> Name the three upgrades that took ViT from 2020 research to 2026 production: self-supervised pretraining (DINO / MAE), register tokens, and native-resolution packing.
> Pick between CLS pooling, mean pooling, and register tokens for a downstream task.

## The Problem · 问题在哪

Transformer 处理的是向量序列。文本天然就是序列（字节或 token）。图像却是一个带三个颜色通道的 2D 像素网格——不是序列。如果把每个像素都拍平，一张 224x224 的 RGB 图会变成 150,528 个 token，在这个长度上做 self-attention 根本不可行（开销随序列长度平方增长）。

2020 年以前的做法是在前面接一个 CNN 特征提取器：ResNet 产出一个 7x7、每格 2048 维的特征图，把这 49 个 token 喂给 transformer。这样能跑，但继承了 CNN 的归纳偏置（平移等变性、局部感受野），也丢掉了 transformer 对规模的胃口。

Dosovitskiy 等人（2020）问了一个直白的问题：如果跳过 CNN 会怎样？把图像切成固定大小的 patch（比如 16x16 像素），每个 patch 线性投影成一个向量，加上位置嵌入，然后把整个序列喂给一个普通 transformer。在当时这是异端——没有卷积的视觉。但只要数据够多（JFT-300M，然后是 LAION），它就在 ImageNet 上击败了 ResNet，而且还在持续变好。

到 2026 年，ViT 原语已是无可争议的地基。每个开源权重 VLM 的视觉塔都是它的某种后裔（DINOv2、SigLIP 2、CLIP、EVA、InternViT）。问题不再是「该不该用 patch？」，而是「patch 取多大、分辨率怎么调度、预训练目标选什么、位置编码用哪种」。

> Transformers operate on sequences of vectors. Text is already a sequence (bytes or tokens). An image is a 2D grid of pixels with three color channels — not a sequence. If you flatten every pixel, a 224x224 RGB image becomes 150,528 tokens, and self-attention at that length is a non-starter (quadratic in sequence length).
> Pre-2020 approaches bolted a CNN feature extractor onto the front: ResNet produces a 7x7 feature map of 2048-dim vectors, feed those 49 tokens to a transformer. This works but inherits the CNN's biases (translation equivariance, local receptive fields) and loses the transformer's appetite for scale.
> Dosovitskiy et al. (2020) asked the blunt question: what if we skip the CNN? ... At the time this was heresy — vision without convolutions. With enough data (JFT-300M, then LAION) it beat ResNet on ImageNet and kept improving.
> By 2026 the ViT primitive is the unquestioned foundation. ... The question is no longer "should we use patches?" but "what patch size, what resolution schedule, what pretraining objective, what positional encoding."

## The Concept · 核心概念

### Patches as tokens · 图像块即 token

给定一张形状为 `(H, W, 3)` 的图像和 patch 大小 `P`，把图像切成 `(H/P) x (W/P)` 个不重叠的 patch 网格。每个 patch 是一个 `P x P x 3` 的像素立方体。把每个立方体展平成 `3 P^2` 维向量，再用一个共享的线性投影 `W_E`（形状 `(3 P^2, D)`）把每个 patch 映射到模型的隐藏维度 `D`。

以 ViT-B/16 经典配置为例：

- 分辨率 224、patch 大小 16 → 网格 14x14 → 196 个 patch token。
- 每个 patch 是 `16 x 16 x 3 = 768` 个像素值，投影到 `D = 768`。
- 加上一个可学习的 `[CLS]` token → 序列长度 197。

patch 投影在数学上等价于一个 kernel 大小为 `P`、stride 为 `P`、输出通道数为 `D` 的 2D 卷积。生产代码实际上就是这么实现的——`nn.Conv2d(3, D, kernel_size=P, stride=P)`。「线性投影」是概念层面的说法；卷积写法才是高效实现。

> Given an image `x` of shape `(H, W, 3)` and a patch size `P`, you carve the image into a grid of `(H/P) x (W/P)` non-overlapping patches. Each patch is a `P x P x 3` cube of pixels. ... The patch projection is mathematically identical to a 2D convolution with kernel size `P`, stride `P`, and `D` output channels. That is how production code actually implements it — `nn.Conv2d(3, D, kernel_size=P, stride=P)`. The "linear projection" framing is conceptual; the kernel framing is efficient.

### Positional embeddings · 位置嵌入

patch 本身没有内在顺序——transformer 眼里它们就是一袋无序向量。早期 ViT 加的是可学习的 1D 位置嵌入（每个位置一个 768 维向量，共 197 个）。能用，但把模型绑死在训练分辨率上：推理时一旦改变网格大小，就得对位置表做插值。

现代视觉骨干用的是 2D-RoPE（Qwen2-VL 的 M-RoPE、SigLIP 2 的默认配置）或因子化的 2D 位置。2D-RoPE 依据 patch 所在的（行, 列）索引旋转 query 和 key 向量，模型从旋转角里推断出相对 2D 位置。没有位置表。推理时模型能处理任意网格尺寸。

> Patches have no inherent order — the transformer sees them as a bag. Early ViTs added a learnable 1D positional embedding (one 768-dim vector per position, 197 of them). ... Modern vision backbones use 2D-RoPE (Qwen2-VL's M-RoPE, SigLIP 2's default) or factorized 2D positions. 2D-RoPE rotates the query and key vectors based on the patch's (row, column) index, so the model infers relative 2D position from the rotation angle. No position table. The model handles arbitrary grid sizes at inference.

### CLS token, pooled output, and register tokens · CLS token、池化输出与 register token

图像级的表示是什么？三种选择并存：

1. `[CLS]` token。在 patch 序列前面拼上一个可学习向量。经过所有 transformer block 之后，CLS token 的隐藏状态就是图像表示。继承自 BERT。原始 ViT 和 CLIP 用它。
2. Mean pool（平均池化）。对 patch token 的输出隐藏状态取平均。SigLIP、DINOv2 和多数现代 VLM 用它。
3. Register token。Darcet 等人（2023）观察到：没有显式 sink token 的 ViT 会长出高范数的「伪影」patch，劫持 self-attention。加上 4–16 个可学习的 register token 可以吸收这部分负载，并提升密集预测任务（分割、深度）的质量。DINOv2 和 SigLIP 2 都自带 register。

这个选择对下游任务很重要。CLS 做分类足够了。对于把 patch token 喂给 LLM 的 VLM，则完全跳过池化——每个 patch 都成为一个 LLM 输入 token。Register 在交接前被丢弃（它们是脚手架，不是内容）。

> What is the image-level representation? Three choices coexist: ... Register tokens. Darcet et al. (2023) observed that ViTs trained without an explicit sink token develop high-norm "artifact" patches that hijack self-attention. Adding 4–16 learnable register tokens absorbs this load and improves dense-prediction quality (segmentation, depth). ... The choice matters for downstream tasks. CLS is fine for classification. For VLMs that feed patch tokens into an LLM, you skip pooling entirely — every patch becomes an LLM input token. Registers get discarded before handoff (they are scaffolding, not content).

### Pretraining: supervised, contrastive, masked, self-distilled · 预训练：监督、对比、掩码、自蒸馏

2020 年的 ViT 用 JFT-300M 上的有监督分类做预训练。很快被以下方法取代：

- CLIP（2021）：4 亿对图文上的对比学习。见 12.02 课。
- MAE（2021，He 等）：掩掉 75% 的 patch，重建像素。自监督，只用纯图像。
- DINO（2021）/ DINOv2（2023）：学生-教师式自蒸馏，无标签、无 caption。2023 年的 DINOv2 ViT-g/14 是最强的纯视觉骨干，也是「密集特征」场景的默认选择。
- SigLIP / SigLIP 2（2023、2025）：用 sigmoid 损失的 CLIP，外加支持原生宽高比的 NaFlex。2026 年开源 VLM 的主流视觉塔（Qwen、Idefics2、LLaVA-OneVision）。

你选的预训练方式决定了这个骨干擅长什么：CLIP/SigLIP 擅长与文本做语义匹配，DINOv2 擅长密集视觉特征，MAE 适合作为下游微调的起点。

> The 2020 ViT was pretrained with supervised classification on JFT-300M. Quickly supplanted by: ... DINO (2021) / DINOv2 (2023): self-distillation with student-teacher, no labels, no captions. The 2023 DINOv2 ViT-g/14 is the strongest purely-visual backbone and the default for "dense features" use cases. ... Your choice of pretraining determines what the backbone is good for: CLIP/SigLIP for semantic matching with text, DINOv2 for dense visual features, MAE as a starting point for downstream finetuning.

### Scaling laws · 缩放定律

ViT 的缩放研究（Zhai 等，2022）确立了：ViT 的质量在模型大小、数据量和算力上服从可预测的规律。固定算力下：

- 更大的模型 + 更多的数据 → 更好的质量。
- patch 大小是「序列长度 vs 保真度」的调节杆。patch 14（DINOv2/SigLIP SO400m 的典型值）比 patch 16 每张图产出更多 token；对 OCR 和密集任务更好，对速度更差。
- 分辨率是另一根大杠杆。从 224 到 384 再到 512 几乎总有提升，代价是 FLOPs 平方级增长。

ViT-g/14（1B 参数，patch 14，分辨率 224 → 256 token）和 SigLIP SO400m/14（400M 参数，patch 14）是 2026 年开源 VLM 的两大主力编码器。

> ViT scaling (Zhai et al. 2022) established that a ViT's quality obeys predictable laws in model size, data size, and compute. At fixed compute: ... Patch size is a lever on sequence length vs fidelity. ... Resolution is the other big lever. Going from 224 to 384 to 512 almost always helps, at quadratic cost in FLOPs. ... ViT-g/14 (1B params, patch 14, resolution 224 → 256 tokens) and SigLIP SO400m/14 (400M params, patch 14) are the two workhorse encoders for 2026 open VLMs.

### Parameter count for a ViT · ViT 的参数量

完整计算在 `code/main.py` 里。以 224 分辨率的 ViT-B/16 为例：

```
patch_embed = 3 * 16 * 16 * 768 + 768  =  591k
cls + pos    = 768 + 197 * 768          =  152k
block        = 4 * 768^2 (QKVO) + 2 * 4 * 768^2 (MLP) + 2 * 2*768 (LN)
             = 12 * 768^2 + 3k          =  7.1M
12 blocks    = 85M
final LN    = 1.5k
total       ≈ 86M
```

加载 checkpoint 之前，先用这种方式粗估每一个 ViT。骨干的规模决定了任何下游 VLM 的 VRAM 下限。

> The full calculation lives in `code/main.py`. For ViT-B/16 at 224: ... Ball-park every ViT this way before you load the checkpoint. The backbone size sets your VRAM floor in any downstream VLM.

### 2026 production config · 2026 年的生产配置

2026 年大多数开源 VLM 随附的编码器是原生分辨率（NaFlex）的 SigLIP 2 SO400m/14。它有：

- 400M 参数。
- patch 大小 14，默认分辨率 384 → 每张图 729 个 patch token。
- 图像级任务用 mean pool；VQA 时全部 729 个 patch 流入 LLM。
- 4 个 register token，在交给 LLM 前丢弃。
- 2D-RoPE 加图像级缩放，支持原生宽高比。

这份配置里的每个决定，都能追溯到你读得到的一篇论文。

```figure
image-patch-tokens
```

> The encoder most open VLMs ship with in 2026 is SigLIP 2 SO400m/14 at native resolution (NaFlex). It has: ... 2D-RoPE with image-level scaling for native aspect ratio. ... Every decision in that config traces back to a paper you can read.

## Use It · 实战用法

`code/main.py` 是一个 patch tokenizer 加几何计算器。输入（图像 H、W，patch P，隐藏维 D，深度 L），它会报告：

- 切 patch 之后的网格形状和序列长度。
- 一张 8x8 像素玩具图像的 token 序列（走一遍展平 + 投影路径）。
- 按 patch embed、位置嵌入、transformer block 和 head 分项的参数量。
- 目标分辨率下每次前向传播的 FLOPs。
- ViT-B/16 @ 224、ViT-L/14 @ 336、DINOv2 ViT-g/14 @ 224、SigLIP SO400m/14 @ 384 的对比表。

跑一跑。把参数量与公开发表的数字对上。调一调 patch 大小和分辨率，感受 token 数量的代价。

> `code/main.py` is a patch tokenizer and geometry calculator. It takes (image H, W, patch P, hidden D, depth L) and reports: ... Run it. Match the parameter counts to the published numbers. Play with patch size and resolution to feel the token-count cost.

## Ship It · 交付

本课产出 `outputs/skill-patch-geometry-reader.md`。给定一个 ViT 配置（patch 大小、分辨率、隐藏维度、深度），它给出带依据的 token 数、参数量和 VRAM 估算。以后每次为 VLM 挑选视觉骨干都可以用这个 skill——它能避免「token 爆了、LLM 上下文被塞满」的意外。

> This lesson produces `outputs/skill-patch-geometry-reader.md`. Given a ViT config (patch size, resolution, hidden dim, depth), it produces a token-count, parameter-count, and VRAM estimate with justifications. Use this skill whenever you pick a vision backbone for a VLM — it prevents "the tokens exploded and my LLM context filled up" surprises.

## Exercises · 练习

1. 计算 Qwen2.5-VL 在原生 1280x720 输入、patch 大小 14 下的 patch token 序列长度。与只用 CLS 的表示相比如何？

2. 一帧 1080p（1920x1080）在 patch 14 下产出多少 token？30 FPS 的 5 分钟视频总共有多少视觉 token？哪个省钱手段收益最大：池化、抽帧，还是 token 合并？

3. 用纯 Python 实现对 patch token 的 mean pooling。验证：对 DINOv2 输出的 196 个 token 做 mean-pool，结果与你在请求 pooled embedding 时模型 `forward` 返回的一致。

4. 读《Vision Transformers Need Registers》（arXiv:2309.16588）第 3 节。用两句话说清 register 吸收的是什么伪影，以及它为什么对下游密集预测很重要。

5. 修改 `code/main.py` 以支持 patch-n'-pack：给定一组不同分辨率的图像，产出一个打包序列和块对角注意力掩码。学到 12.06 课时用它做验证。

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| Patch | "16x16 像素小块" | 输入图像中固定大小、互不重叠的区域；变成一个 token |
| Patch embedding | "线性投影" | 一个共享的可学习矩阵（或 stride=P 的 Conv2d），把展平的 patch 像素映射成 D 维向量 |
| CLS token | "类别 token" | 前置的可学习向量，其最终隐藏状态表示整张图；在 2026 年已是可选项 |
| Register token | "sink token" | 额外的可学习 token，吸收 ViT 预训练期间出现的高范数注意力伪影 |
| Position embedding | "位置信息" | 按位置给出的向量或旋转，让序列具备顺序感知；2D-RoPE 是现代默认 |
| Grid | "patch 网格" | 给定分辨率和 patch 大小时，(H/P) x (W/P) 的 2D patch 阵列 |
| NaFlex | "原生弹性分辨率" | SigLIP 2 特性：单个模型无需重训即可服务多种宽高比和分辨率 |
| Backbone | "视觉塔" | 预训练图像编码器，其 patch token 输出在 VLM 中喂给 LLM |
| Pooling | "图像级摘要" | 把 patch token 变成一个向量的策略：CLS、均值、注意力池化或基于 register |
| Patch 14 vs 16 | "更细 vs 更粗的网格" | patch 14 每张图产出更多 token，对 OCR 保真度更好但更慢；patch 16 是经典默认 |

## Further Reading · 延伸阅读

- [Dosovitskiy et al. — An Image is Worth 16x16 Words (arXiv:2010.11929)](https://arxiv.org/abs/2010.11929) — ViT 原始论文。
- [He et al. — Masked Autoencoders Are Scalable Vision Learners (arXiv:2111.06377)](https://arxiv.org/abs/2111.06377) — MAE，自监督预训练。
- [Oquab et al. — DINOv2 (arXiv:2304.07193)](https://arxiv.org/abs/2304.07193) — 规模化自蒸馏，无需标签。
- [Darcet et al. — Vision Transformers Need Registers (arXiv:2309.16588)](https://arxiv.org/abs/2309.16588) — register token 与伪影分析。
- [Tschannen et al. — SigLIP 2 (arXiv:2502.14786)](https://arxiv.org/abs/2502.14786) — 2026 年的默认视觉塔。
- [Zhai et al. — Scaling Vision Transformers (arXiv:2106.04560)](https://arxiv.org/abs/2106.04560) — 经验缩放定律。
