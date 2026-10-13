# Any-Resolution Vision: Patch-n'-Pack and NaFlex · 任意分辨率视觉：Patch-n'-Pack 与 NaFlex

> 真实图像不是 224x224 的正方形。收据是 9:16，图表是 16:9，医学影像可能是 4096x4096，手机截图是 9:19.5。2024 年以前 VLM 的答案——把一切都缩放成固定正方形——丢掉的正是让 OCR、文档理解和高清场景解析得以成立的那部分信号。NaViT（Google，2023）证明了你可以把可变分辨率的 patch 打包进一个 transformer batch，用块对角掩码隔开。Qwen2-VL 的 M-RoPE（2024）干脆扔掉了绝对位置表。LLaVA-NeXT 的 AnyRes 把高分辨率图平铺成底图 + 子图。SigLIP 2 的 NaFlex 变体（2025）如今是开源 VLM 想用一个 checkpoint 服务所有宽高比时的默认编码器。本课端到端实现 patch-n'-pack。
>
> Real images are not 224x224 squares. A receipt is 9:16, a chart is 16:9, a medical scan might be 4096x4096, a mobile screenshot is 9:19.5. The pre-2024 VLM answer — resize everything to a fixed square — threw away the signal that makes OCR, document understanding, and high-resolution scene parsing work. NaViT (Google, 2023) showed you could pack variable-resolution patches into a single transformer batch with block-diagonal masking. Qwen2-VL's M-RoPE (2024) dropped absolute positional tables entirely. LLaVA-NeXT's AnyRes tiled high-resolution images into a base + sub-images. SigLIP 2's NaFlex variant (2025) is now the default encoder for open VLMs that want a single checkpoint to serve every aspect ratio. This lesson implements patch-n'-pack end to end.

**类型:** Build
**语言:** Python（标准库，patch packer + 块对角掩码）
**先修:** Phase 12 · 01（ViT patches）、Phase 12 · 05（LLaVA）
**时长:** ~120 分钟

## Learning Objectives · 学习目标

- 把一批可变分辨率图像的 patch 打包进一个序列，并构建块对角注意力掩码。
- 针对给定任务，在 AnyRes 平铺（LLaVA-NeXT）、NaFlex（SigLIP 2）和 M-RoPE（Qwen2-VL）之间做选择。
- 不缩放地为 OCR、图表和摄影计算 token 预算。
- 说出正方形缩放的三种失败模式：文字压扁、内容被裁掉、padding 浪费 token。

> Pack patches from a batch of variable-resolution images into one sequence and build the block-diagonal attention mask.
> Pick between AnyRes tiling (LLaVA-NeXT), NaFlex (SigLIP 2), and M-RoPE (Qwen2-VL) for a given task.
> Compute token budgets for OCR, charts, and photography without resizing.
> Name the three failure modes of square-resize: squished text, cropped content, wasted tokens on padding.

## The Problem · 问题在哪

Transformer 期望序列。batch 是等长序列的堆叠。如果你的图像都是 224x224，那么每次都是 196 个 patch token，不需要 padding，完事。224 训练，224 推理，再也不用想分辨率的事。

可世界不配合。文档是竖版（8.5x11 英寸，约 2:3）。图表截图是横版（16:9）。收据又高又窄（1:3）。医学影像以 2048x2048 或更大出厂。手机截图是 1170x2532（0.46:1）。

2024 年以前的三种选项，以及各自失败的原因：

1. 缩放到固定正方形（224x224 或 336x336）。挤压使文字和脸变形。降采样毁掉图表标签和 OCR 内容。LLaVA-1.5 之前的标准做法。
2. 裁剪成固定宽高比。你扔掉了图像的大部分，而且挑裁剪位置本身就是一道视觉难题。
3. 补齐到最长边。解决了变形，但竖版图像要浪费 50%+ 的 token 在 padding 上。所有这些 pad token 都要付平方级的注意力成本。

2024-2025 的答案：让 transformer 直接以图像的原生分辨率吃 patch，并解决如何把异构 batch 打包进一个序列而不浪费算力。

> Transformers expect a sequence. A batch is a stack of sequences the same length. If your images are 224x224, you get 196 patch tokens every time, padding not required, job done. Train on 224, infer on 224, never think about resolution again.
> The world does not cooperate. Documents are portrait (8.5x11 inches, 2:3-ish). Chart screenshots are landscape (16:9). Receipts are tall and thin (1:3). Medical imaging ships at 2048x2048 or larger. Mobile device screenshots are 1170x2532 (0.46:1).
> Three pre-2024 options and why each fails: ... The 2024-2025 answer: let the transformer eat patches at the image's native resolution, and figure out how to pack a heterogeneous batch into one sequence without wasted compute.

## The Concept · 核心概念

### NaViT and patch-n'-pack · NaViT 与 patch-n'-pack

NaViT（Dehghani 等，2023）是证明这件事能在规模上成立的论文。做法很机械：

1. 对 batch 里的每张图，按选定的 patch 大小（比如 14）算出它的原生 patch 网格。
2. 把每张图的 patch 展平成它自己的变长序列。
3. 把所有图像的 patch 拼接成 batch 的一条长序列。
4. 构建一个块对角注意力掩码，使图像 A 的 patch 只在图像 A 内部相互关注。
5. 携带每个 patch 的位置信息（2D RoPE 或分数位置嵌入）。

三张图：336x336（576 token）、224x224（256 token）、448x336（768 token），打包成一条 1600 token 的序列，配一个 1600x1600 的块对角掩码。没有 padding，没有浪费的算力。transformer 处理任意宽高比。

NaViT 还在训练中引入了分数 patch 丢弃——在 batch 里随机丢掉 50% 的 patch——既正则化又加速训练。SigLIP 2 继承了这一点。

> NaViT (Dehghani et al., 2023) was the paper that showed this works at scale. The idea is mechanical: ... A batch of three images at 336x336 (576 tokens), 224x224 (256 tokens), and 448x336 (768 tokens) becomes one 1600-token sequence with a 1600x1600 block-diagonal mask. No padding. No wasted compute. The transformer handles arbitrary aspect ratios.
> NaViT also introduced fractional patch dropping during training — drop 50% of patches at random across the batch — which both regularizes and speeds training. SigLIP 2 inherited this.

### AnyRes (LLaVA-NeXT) · AnyRes（LLaVA-NeXT）

LLaVA-NeXT 的 AnyRes 是务实替代方案。给定一张高分辨率图和一个固定编码器（336 的 CLIP 或 SigLIP），对图像做平铺：

1. 从预定义集合里选一个最匹配图像宽高比的网格布局——(1x1)、(1x2)、(2x1)、(1x3)、(3x1)、(2x2) 等。
2. 把整张图按网格切分；每个 tile 变成一个 336x336 的 crop。
3. 同时产出一个缩略图：整张图缩放到 336x336，作为全局上下文 token。
4. 每个 tile 都过一遍冻结的 336 编码器。拼接 tile token + 缩略图 token。

一张 672x672 的图按 2x2 网格加缩略图：4 * 576 + 576 = 2880 个视觉 token。贵但有效——LLM 同时看到局部细节和全局上下文。

当你的编码器被冻结且只支持一个分辨率时，AnyRes 是首选路线。它对大图的 token 数是爆炸式的（一张 1344x1344 的图按 4x4 网格是 9216 + 576 ≈ 9800 个 token，能填满 8k LLM 上下文的大半）。

> LLaVA-NeXT's AnyRes is the pragmatic alternative. Given a high-resolution image and a fixed encoder (CLIP or SigLIP at 336), tile the image: ... For a 672x672 image at 2x2 grid plus thumbnail: 4 * 576 + 576 = 2880 visual tokens. Expensive but effective — the LLM sees both local detail and global context. ... It explodes token count for large images (a 1344x1344 image at 4x4 grid is 9216 + 576 ≈ 9800 tokens, which fills most of a 8k LLM context).

### M-RoPE (Qwen2-VL) · M-RoPE（Qwen2-VL）

Qwen2-VL 引入了多模态旋转位置嵌入（Multimodal Rotary Position Embedding）。它不用 NaViT 的分数位置，也不用 AnyRes 的平铺加缩略图，而是让每个 patch 携带一个 3D 位置（时间, 高, 宽）。query/key 的旋转天然处理任意的 H、W 和时间长度。

M-RoPE 原生支持动态分辨率，无需重训。推理时你喂任意 HxW 的图，patch embedder 产出 H/14 x W/14 个 token，每个 token 拿到它的 (t=0, r=行, c=列) 位置，RoPE 用正确的频率旋转注意力，完成。Qwen2.5-VL 和 Qwen3-VL 延续了这一设计。InternVL3 的 V2PE 是同一思想的变体，按模态使用可变编码。

与 AnyRes 不同，M-RoPE 在原生分辨率下是 O(H x W / P^2) 个 token——没有乘法级的 tile 开销。与 NaViT 不同，它仍然期望每次前向只有一张图。跨分辨率组 batch 仍需要在它上面叠加 patch-n'-pack。

> Qwen2-VL introduced Multimodal Rotary Position Embedding. Instead of NaViT's fractional positions or AnyRes's tile-and-thumbnail, each patch carries a 3D position (temporal, height, width). The query/key rotations handle arbitrary H, W, and temporal length. ... Unlike AnyRes, M-RoPE is O(H x W / P^2) tokens at native resolution — no multiplicative tile overhead. Unlike NaViT, it still expects a single image per forward. Batching across resolutions still needs patch-n'-pack on top.

### NaFlex (SigLIP 2) · NaFlex（SigLIP 2）

NaFlex 是 SigLIP 2 checkpoint 的原生弹性模式。单个模型在推理时服务多种序列长度（256、729、1024 token）。内部在训练时使用 NaViT 式的 patch-n'-pack，每个 patch 用绝对分数位置。卖点：一个 checkpoint，推理时按任务挑选你的 token 预算。

语义任务（分类、检索）用 256 token。OCR 或图表理解用 1024 token。不用重训。

> NaFlex is the SigLIP 2 checkpoint's native-flex mode. A single model serves multiple sequence lengths (256, 729, 1024 tokens) at inference. ... The selling point: one checkpoint, pick your token budget at inference based on the task. ... No retraining.

### The packing mask · 打包掩码

块对角掩码是大多数实现跌倒的地方。对一条覆盖图像 `i=0..B-1`、各长 `n_i` 的打包序列 `N_total`，形状为 `(N_total, N_total)` 的掩码 `M` 在两个下标落在同一图像块内时为 1，否则为 0。可以用累计长度表来构建它：

```
offsets = [0, n_0, n_0+n_1, ..., N_total]
M[i, j] = 1 iff there exists b where offsets[b] <= i < offsets[b+1] and offsets[b] <= j < offsets[b+1]
```

在 PyTorch 里，这是带 `torch.block_diag` 或显式 gather 的一行代码。FlashAttention 的变长路径（`cu_seqlens`）干脆完全跳过掩码，直接用累计长度张量在序列内部做注意力——对典型 batch 来说比稠密掩码快约 10 倍。

> The block-diagonal mask is where most implementations stumble. ... You can build it from a cumulative length list: ... FlashAttention's variable-length path (`cu_seqlens`) skips the mask entirely and attends within sequences using the cumulative-length tensor directly — ~10x faster than a dense mask for typical batches.

### Token budgets · Token 预算

按任务选策略：

- OCR / 文档：1024-4096 token。1024 的 SigLIP 2 NaFlex，或 AnyRes 3x3 + 缩略图。
- 图表和 UI：384-448 原生下 729-1024 token。Qwen2.5-VL 动态分辨率加最大像素上限。
- 自然照片：256-576 token 就够了。下游 LLM 看到的信息已经足够。把 token 花在内容密度高的地方。
- 视频：空间池化后每帧 64-128 token，2-8 FPS。12.17 课讲这个。

2026 年的生产法则：按任务定一个最大像素上限，在不超上限的前提下按原生宽高比编码，打包 batch，跳过 padding。Qwen2.5-VL 暴露的 `min_pixels` 和 `max_pixels` 正是这个旋钮。

> Pick your strategy by task: ... The 2026 production rule: pick a per-task max-pixels cap, encode at native aspect ratio up to that cap, pack the batch, and skip padding. Qwen2.5-VL exposes `min_pixels` and `max_pixels` for exactly this knob.

```figure
mm-patch-n-pack
```

## Use It · 实战用法

`code/main.py` 为一批带整数像素坐标的异构图像实现 patch-n'-pack。它：

- 接受一列 (H, W) 图像尺寸。
- 按 patch 大小 14 计算每张图的 patch 序列长度。
- 把它们打包成总长 `sum(n_i)` 的一条序列。
- 构建块对角注意力掩码（稠密版，为了清晰）。
- 对比打包成本 vs 正方形缩放和 AnyRes 平铺。
- 打印一个混合 batch（收据、图表、截图、照片）的 token 预算表。

跑一跑。掉出来的那些数字，就是 2026 年每个开源 VLM 都用 patch-n'-pack 的原因。

> `code/main.py` implements patch-n'-pack for a heterogeneous batch of images with integer pixel coordinates. It: ... Run it. The numbers that drop out are the reason every 2026 open VLM uses patch-n'-pack.

## Ship It · 交付

本课产出 `outputs/skill-resolution-budget-planner.md`。给定一个混合宽高比的工作负载（OCR、图表、照片、视频帧）和总 token 预算，它挑出正确的策略（NaFlex、AnyRes、M-RoPE 或固定正方形），并产出按请求的配置。为产品做 VLM 规模选型时用这个 skill——它能避免那个悄悄杀死延迟预算的 10 倍 token 爆炸。

> This lesson produces `outputs/skill-resolution-budget-planner.md`. Given a mixed-aspect-ratio workload (OCR, charts, photos, video frames) and a total-token budget, it picks the right strategy (NaFlex, AnyRes, M-RoPE, or fixed-square) and emits a per-request configuration. Use this skill when you are sizing a VLM for a product — it prevents the silent 10x token blowup that kills latency budgets.

## Exercises · 练习

1. 一张收据是 600x1500（1:2.5）。patch 大小 14 下，原生分辨率有多少 token？缩放到 336 正方形后呢？实践中哪个损失更多 OCR 精度？

2. 为长度 256、576、729、1024 的四张图构建块对角掩码。验证注意力矩阵是 2585x2585，且恰好有 `256^2 + 576^2 + 729^2 + 1024^2` 个非零元素。

3. 对一张 1792x896 的图（patch 14）比较三种方案：(a) 缩放到 336 正方形再编码，(b) AnyRes 2x1 + 缩略图，(c) 原生 M-RoPE。哪个用的 token 最少？哪个保留的细节最多？

4. 实现分数 patch 丢弃：给定一条打包序列，均匀随机丢弃 50% 的 token，并相应更新块对角掩码。测量掩码稀疏度的变化。

5. 读 Qwen2-VL 论文（arXiv:2409.12191）第 3.2 节。用两句话说清 `min_pixels` 和 `max_pixels` 各控制什么，以及为什么两个边界都重要。

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|-----------------|------------------------|
| Patch-n'-pack | "NaViT 式打包" | 把来自不同图像的变长 patch 序列拼接进同一个 batch 维度 |
| Block-diagonal mask | "打包掩码" | 限制每张图的 patch 只关注自身、不关注打包中邻居的注意力掩码 |
| AnyRes | "LLaVA-NeXT 平铺" | 把高分辨率图切成固定大小 tile 网格加全局缩略图；每个 tile 用固定编码器编码 |
| NaFlex | "SigLIP 2 原生弹性" | 单个 SigLIP 2 checkpoint 在推理时服务 256/729/1024-token 预算而无需重训 |
| M-RoPE | "多模态 RoPE" | 3D 旋转位置编码（时间, 行, 列），无需位置表即可处理任意 H、W、T |
| cu_seqlens | "FlashAttention 打包" | FlashAttention varlen 路径用来替代稠密块对角掩码的累计长度张量 |
| min_pixels / max_pixels | "分辨率边界" | Qwen2.5-VL 的按请求旋钮，为极小或极大输入封顶 token 数 |
| Visual token budget | "每图多少 token" | 每张图产出的 patch token 粗估；决定 LLM 的 prompt 预算和注意力成本 |

## Further Reading · 延伸阅读

- [Dehghani et al. — Patch n' Pack: NaViT (arXiv:2307.06304)](https://arxiv.org/abs/2307.06304)
- [Wang et al. — Qwen2-VL (arXiv:2409.12191)](https://arxiv.org/abs/2409.12191)
- [Laurençon et al. — What matters when building vision-language models? (Idefics2, arXiv:2405.02246)](https://arxiv.org/abs/2405.02246)
- [Tschannen et al. — SigLIP 2 (arXiv:2502.14786)](https://arxiv.org/abs/2502.14786)
- [Qwen Team — Qwen2.5-VL Technical Report (arXiv:2502.13923)](https://arxiv.org/abs/2502.13923)
