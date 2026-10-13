# 3D Generation · 3D 生成

3D 是 2D 转 3D 杠杆最强的模态。2023 年的突破是 3D 高斯泼溅（3D Gaussian Splatting）。2024-2026 的生成式浪潮在其上叠加「多视角扩散 + 3D 重建」，从单个提示或一张照片生成物体和场景。

> 3D is the modality where 2D-to-3D leverage is strongest. The 2023 breakthrough was 3D Gaussian Splatting. The 2024-2026 generative push layers multi-view diffusion + 3D reconstruction on top to produce objects and scenes from a single prompt or photo.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 4 (Vision), Phase 8 · 07 (Latent Diffusion)
**Time:** ~45 minutes

## The Problem · 问题在哪

3D 内容很痛苦：

- **表示（representation）。** 网格（mesh）、点云、体素网格、符号距离场（signed distance field, SDF）、神经辐射场（neural radiance field, NeRF）、3D 高斯。各有取舍。
- **数据稀缺。** ImageNet 有 14M 张图像。最大的干净 3D 数据集（Objaverse-XL，2023）只有约 10M 个物体，而且大多质量不高。
- **内存。** 一个 512³ 的体素网格是 128M 个体素；一个可用的场景 NeRF 每条光线要采 1M 个样本。生成比重建难得多。
- **监督。** 对 2D 图像，你手里就有像素。对 3D，你通常只有少量 2D 视角，还得把它们提升（lift）到 3D。

2026 年的技术栈把这两个问题拆开。第一步，用扩散模型生成 *2D 多视角图像*。第二步，把这些图像拟合出一个 *3D 表示*（通常是高斯泼溅）。

> 3D content is painful:
> - **Representation.** Meshes, point clouds, voxel grids, signed distance fields (SDFs), neural radiance fields (NeRFs), 3D Gaussians. Each has trade-offs. ...
> - **Data scarcity.** ImageNet has 14M images. The largest clean 3D dataset (Objaverse-XL, 2023) has ~10M objects, most low quality. ...
> - **Supervision.** For a 2D image you have the pixels. For 3D you usually have a handful of 2D views and have to lift to 3D.
> The 2026 stack separates the two problems. First, generate *2D multi-view images* with a diffusion model. Second, fit a *3D representation* (usually Gaussian splatting) to those images.

## The Concept · 概念

![3D 生成：多视角扩散 + 3D 重建](../assets/3d-generation.svg)

### Representation: 3D Gaussian Splatting (Kerbl et al., 2023) · 表示：3D 高斯泼溅（Kerbl et al., 2023）

把场景表示成一团约 1M 个 3D 高斯。每个高斯有 59 个参数：位置（3）、协方差（6，或四元数 4 + 尺度 3）、不透明度（1）、球谐颜色（3 阶时 48，0 阶时 3）。

渲染 = 投影 + alpha 合成（alpha-compositing）。快（4090 上 1080p 约 100 fps）。可微。通过与真实照片之间的梯度下降来拟合。一个场景在消费级 GPU 上 5-30 分钟即可拟合完成。

其上的两个 2023-2024 创新：
- **生成式高斯泼溅。** LGM、LRM、InstantMesh 这类模型直接从一张或几张图像预测高斯云。
- **4D 高斯泼溅。** 带逐帧偏移的高斯，用于动态场景。

> Represent a scene as a cloud of ~1M 3D Gaussians. Each has 59 parameters: position (3), covariance (6, or quaternion 4 + scale 3), opacity (1), spherical-harmonics color (48 at degree 3, 3 at degree 0).
> Rendering = projection + alpha-compositing. Fast (~100 fps at 1080p on a 4090). Differentiable. Fit by gradient descent against ground-truth photos. A scene fits in 5-30 minutes on a consumer GPU.
> Two 2023-2024 innovations on top:
> - **Generative Gaussian splats.** Models like LGM, LRM, InstantMesh predict a Gaussian cloud directly from one or a few images. ...
> - **4D Gaussian Splatting.** Gaussians with per-frame offsets for dynamic scenes.

### Multi-view diffusion · 多视角扩散

微调一个预训练的图像扩散模型，让它从文本提示或单张图像生成同一物体的多个一致视角。Zero123（Liu et al., 2023）、MVDream（Shi et al., 2023）、SV3D（Stability，2024）、CAT3D（Google，2024）。通常输出环绕物体的 4-16 个视角，再通过高斯泼溅或 NeRF 提升到 3D。

> Fine-tune a pretrained image diffusion model to generate multiple consistent views of the same object from a text prompt or single image. Zero123 (Liu et al., 2023), MVDream (Shi et al., 2023), SV3D (Stability, 2024), CAT3D (Google, 2024). Usually output 4-16 views around the object, lifted to 3D via Gaussian splatting or NeRF.

### Text-to-3D pipelines · 文本转 3D 流水线

| 模型 | 输入 | 输出 | 耗时 |
|-------|-------|--------|------|
| DreamFusion (2022) | 文本 | 经 SDS 的 NeRF | 每个资产 ~1 小时 |
| Magic3D | 文本 | 网格 + 纹理 | ~40 分钟 |
| Shap-E (OpenAI, 2023) | 文本 | 隐式 3D | ~1 分钟 |
| SJC / ProlificDreamer | 文本 | NeRF / 网格 | ~30 分钟 |
| LRM (Meta, 2023) | 图像 | triplane | ~5 s |
| InstantMesh (2024) | 图像 | 网格 | ~10 s |
| SV3D (Stability, 2024) | 图像 | 新视角 | ~2 分钟 |
| CAT3D (Google, 2024) | 1-64 张图像 | 3D NeRF | ~1 分钟 |
| TripoSR (2024) | 图像 | 网格 | ~1 s |
| Meshy 4 (2025) | 文本 + 图像 | PBR 网格 | ~30 s |
| Rodin Gen-1.5 (2025) | 文本 + 图像 | PBR 网格 | ~60 s |
| Tencent Hunyuan3D 2.0 (2025) | 图像 | 网格 | ~30 s |

2025-2026 方向：带适合游戏引擎的 PBR 材质的直接文本转网格（text-to-mesh）模型。对通用物体而言，多视角扩散作为中间步骤仍然是效果最好的配方。

> 2025-2026 direction: direct text-to-mesh models with PBR materials suitable for game engines. Multi-view diffusion intermediate step is still the best-performing recipe for general objects.

### NeRF (for context) · NeRF（背景知识）

神经辐射场（Neural Radiance Field，Mildenhall et al., 2020）。一个小型 MLP 接收 `(x, y, z, 视线方向)`，输出 `(颜色, 密度)`。沿光线积分来渲染。在新视角合成质量上胜过基于网格的方法，但渲染慢 100-1000 倍。在大多数实时用途上已被高斯泼溅取代，但在研究中仍占主导。

> Neural Radiance Field (Mildenhall et al., 2020). A tiny MLP takes `(x, y, z, view direction)` and outputs `(color, density)`. Render by integrating along rays. Beats mesh-based novel-view synthesis in quality but is 100-1000x slower to render. Superseded by Gaussian splatting for most real-time use but still dominant in research.

```figure
v4-3d-multiview
```

## Build It · 动手造

`code/main.py` 实现一个玩具版 2D「高斯泼溅」拟合：把一张合成目标图像（一个平滑梯度）表示成 2D 高斯 splat 之和。用梯度下降优化位置、颜色和协方差来匹配目标。你会看到两个核心操作：前向渲染（splat + alpha 合成）和梯度下降拟合。

> `code/main.py` implements a toy 2D "Gaussian splatting" fit: represent a synthetic target image (a smooth gradient) as a sum of 2D Gaussian splats. Optimize positions, colors, and covariances by gradient descent to match the target. You see the two core operations: forward render (splat + alpha-composite) and fit by gradient descent.

### Step 1: 2D Gaussian splat · 第 1 步：2D 高斯 splat

```python
def gaussian_at(x, y, gaussian):
    px, py = gaussian["pos"]
    sigma = gaussian["sigma"]
    d2 = (x - px) ** 2 + (y - py) ** 2
    return math.exp(-d2 / (2 * sigma * sigma))
```

### Step 2: render by summing splats · 第 2 步：把 splat 求和来渲染

```python
def render(image_size, gaussians):
    img = [[0.0] * image_size for _ in range(image_size)]
    for g in gaussians:
        for y in range(image_size):
            for x in range(image_size):
                img[y][x] += g["color"] * gaussian_at(x, y, g)
    return img
```

真正的 3D 高斯泼溅会按深度对高斯排序并按序做 alpha 合成。我们的 2D 玩具版只做求和。

> Real 3D Gaussian splatting sorts Gaussians by depth and alpha-composites in order. Our 2D toy just sums.

### Step 3: fit by gradient descent · 第 3 步：用梯度下降拟合

```python
for step in range(steps):
    pred = render(size, gaussians)
    loss = mse(pred, target)
    gradients = compute_grads(pred, target, gaussians)
    update(gaussians, gradients, lr)
```

## Pitfalls · 常见坑

- **视角不一致。** 如果独立生成 4 个视角而它们对物体结构的看法互相矛盾，3D 拟合结果就会发糊。修复：带共享注意力的多视角扩散。
- **背面幻觉。** 单图 → 3D 必须凭空发明看不见的那一面。质量参差不齐。
- **高斯 splat 爆炸。** 不加约束的训练会长到 10M 个 splat 并过拟合。致密化（densification）+ 剪枝启发式（来自 3D-GS 原论文）必不可少。
- **拓扑问题。** 从隐式场（SDF）提取的网格常有孔洞或自交。交付前先跑一遍重网格化（remesher，例如 blender 的 voxel remesh）。
- **训练数据授权。** Objaverse 的授权混杂；能否商用因模型而异。

> **View inconsistency.** If you generate 4 views independently and they disagree about object structure, the 3D fit is blurry. Fix: multi-view diffusion with shared attention. ...
> **Back-side hallucination.** Single-image → 3D has to invent the unseen side. Quality varies wildly. ...
> **Gaussian splat explosion.** Unconstrained training grows to 10M splats and overfits. Densification + pruning heuristics (from 3D-GS original paper) are essential. ...
> **License of training data.** Objaverse has mixed licenses; commercial use varies per model.

## Use It · 实战用法

| 任务 | 2026 年首选 |
|------|-----------|
| 照片场景重建 | 高斯泼溅（3DGS、Gsplat、Scaniverse） |
| 游戏用文本转 3D 物体 | Meshy 4 或 Rodin Gen-1.5（PBR 输出） |
| 图像转 3D | Hunyuan3D 2.0、TripoSR、InstantMesh |
| 少图新视角合成 | CAT3D、SV3D |
| 动态场景重建 | 4D Gaussian Splatting |
| 头像 / 穿衣人体 | Gaussian Avatar、HUGS |
| 研究 / SOTA | 上周刚发布的那个 |

要把生产级 3D 交付进游戏或电商流水线：Meshy 4 或 Rodin Gen-1.5 输出的 PBR 网格可以直接进入 Unity / Unreal。

> For shipping production 3D in a game or e-commerce pipeline: Meshy 4 or Rodin Gen-1.5 output PBR meshes that go straight into Unity / Unreal.

## Ship It · 交付

保存 `outputs/skill-3d-pipeline.md`。这个 skill 接收 3D 需求简报（输入：文本 / 单图 / 少量图像；输出：网格 / splat / NeRF；用途：渲染 / 游戏 / VR），输出：流水线（多视角扩散 + 拟合，或直接网格模型）、基础模型、迭代预算、拓扑后处理、所需材质通道。

> Save `outputs/skill-3d-pipeline.md`. Skill takes a 3D brief (input: text / one image / few images; output: mesh / splat / NeRF; usage: render / game / VR) and outputs: pipeline (multi-view diffusion + fit, or direct mesh model), base model, iteration budget, topology post-processing, material channels needed.

## Exercises · 练习

1. **简单。** 分别用 4、16、64 个高斯跑 `code/main.py`。报告相对目标的最终 MSE。
2. **中等。** 扩展到彩色高斯（RGB）。确认重建能匹配目标的颜色图案。
3. **困难。** 用 gsplat 或 Nerfstudio，从 50 张照片的采集重建一个真实物体。报告拟合时间和留出视角上的最终 SSIM。

> 1. **Easy.** Run `code/main.py` with 4, 16, 64 Gaussians. Report final MSE vs target. ...
> 2. **Medium.** Extend to color Gaussians (RGB). Confirm reconstruction matches the target color pattern. ...
> 3. **Hard.** Using gsplat or Nerfstudio, reconstruct a real object from a 50-photo capture. Report fit time and final SSIM on held-out views.

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| 3D Gaussian Splatting | "3DGS" | 把场景表示成 3D 高斯云；可微的 alpha 合成渲染。 |
| NeRF | "神经辐射场" | 在 3D 点上输出颜色 + 密度的 MLP；沿光线积分渲染。 |
| Triplane | "三张 2D 平面" | 把 3D 分解成三个 2D 轴对齐特征网格；比体积表示便宜。 |
| SDS | "Score distillation sampling" | 用 2D 扩散的 score 当伪梯度来训练 3D 模型。 |
| Multi-view diffusion | "一次出多个视角" | 输出一批一致相机视角的扩散模型。 |
| PBR | "基于物理的渲染" | 带反照率、粗糙度、金属度、法线通道的材质。 |
| Densification | "让 splat 变多" | 3DGS 训练启发式：在高梯度区域分裂 / 克隆 splat。 |

## Production note: 3D has no shared substrate yet · 生产备注：3D 还没有统一底座

与图像（隐空间扩散 + DiT）和视频（时空 DiT）不同，2026 年的 3D 还没有一个占主导地位的统一运行时。生产决策树在「表示」这一层分叉：

- **NeRF / triplane。** 推理是光线步进（ray-marching）+ 每个样本一次 MLP 前向。一张 512² 的渲染需要数百万次 MLP 前向。要激进地对光线样本做批处理；SDPA/xformers 适用。
- **多视角扩散 + LRM 重建。** 两阶段流水线。阶段 1（多视角 DiT）就是一个 diffusion server，与第 07 课完全一样。阶段 2（LRM transformer）是对这些视角的一次性前向。整体延迟特征是「扩散 + 一次性前向」—— 按阶段挑选相应的服务原语。
- **SDS / DreamFusion。** 每个资产一次优化，不是推理。要构建的是作业（job），不是请求处理器。

对大多数 2026 年的产品，正确答案是「按请求跑一个多视角扩散模型，异步重建成 3DGS，再用 3DGS 提供实时浏览」。这样把工作负载干净地拆给 GPU 推理服务器（快）和离线优化器（慢）。

> Unlike image (latent diffusion + DiT) and video (spatiotemporal DiT), 3D has no single dominant runtime in 2026. The production decision tree forks on the representation:
> - **NeRF / triplane.** Inference is ray-marching + an MLP forward per sample. A 512² render requires millions of MLP forwards. ...
> - **Multi-view diffusion + LRM reconstruction.** Two-stage pipeline. ...
> - **SDS / DreamFusion.** Per-asset optimization, not inference. Build jobs, not request handlers.
> For most 2026 products, the right answer is "run a multi-view diffusion model on request, reconstruct to 3DGS asynchronously, serve the 3DGS for real-time viewing". This splits the workload cleanly between a GPU-inference server (fast) and an offline optimizer (slow).

## Further Reading · 延伸阅读

- [Mildenhall et al. (2020). NeRF: Representing Scenes as Neural Radiance Fields](https://arxiv.org/abs/2003.08934) —— NeRF。
- [Kerbl et al. (2023). 3D Gaussian Splatting for Real-Time Radiance Field Rendering](https://arxiv.org/abs/2308.04079) —— 3DGS。
- [Poole et al. (2022). DreamFusion: Text-to-3D using 2D Diffusion](https://arxiv.org/abs/2209.14988) —— SDS。
- [Liu et al. (2023). Zero-1-to-3: Zero-shot One Image to 3D Object](https://arxiv.org/abs/2303.11328) —— Zero123。
- [Shi et al. (2023). MVDream](https://arxiv.org/abs/2308.16512) —— 多视角扩散。
- [Hong et al. (2023). LRM: Large Reconstruction Model for Single Image to 3D](https://arxiv.org/abs/2311.04400) —— LRM。
- [Gao et al. (2024). CAT3D: Create Anything in 3D with Multi-View Diffusion Models](https://arxiv.org/abs/2405.10314) —— CAT3D。
- [Stability AI (2024). Stable Video 3D (SV3D)](https://stability.ai/research/sv3d-novel-multi-view-synthesis-and-3d-generation-from-a-single-image-using-latent-video-diffusion) —— SV3D。
