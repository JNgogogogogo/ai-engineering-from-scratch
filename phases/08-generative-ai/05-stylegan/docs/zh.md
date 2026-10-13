# StyleGAN · 基于风格的 GAN

> Most generators stir `z` into every layer at the same time. StyleGAN split it apart: first map `z` to an intermediate `w`, then *inject* `w` at every resolution level through AdaIN. That single change untangled the latent space and made photorealistic faces a solved problem for seven years running.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 8 · 03 (GANs), Phase 4 · 08 (Normalization), Phase 3 · 07 (CNNs)
**Time:** ~45 minutes

## The Problem · 问题在哪

DCGAN 通过一摞转置卷积把 `z` 映射成图像。问题在于：`z` 同时控制一切——姿态、光照、身份、背景——全都缠在一起。沿 `z` 的某个轴移动，四个一起变。你没法对模型说「同一个人，换个姿势」，因为这个表示根本不做那种分解。

Karras et al.（2019，NVIDIA）提出：别再把 `z` 直接喂进卷积层。把一个常数 `4×4×512` 张量当作网络输入。学一个 8 层 MLP，把 `z ∈ Z` 映射到 `w ∈ W`。在每个分辨率上通过*自适应实例归一化*（AdaIN）注入 `w`：先归一化每个卷积特征图，再用 `w` 的仿射投影去缩放和平移。再加逐层噪声来产生随机细节（皮肤毛孔、发丝）。

结果是：`W` 里「高层风格」（姿态、身份）与「细粒度风格」（光照、颜色）的轴大致正交。你可以交换两张图像的风格：低分辨率层用图像 A 的 `w`，高分辨率层用图像 B 的 `w`。由此解锁了编辑、跨域风格化，以及整条「StyleGAN 反演（inversion）」研究线。

> A DCGAN maps `z` to an image through a stack of transposed convolutions. The problem: `z` controls everything — pose, lighting, identity, background — entangled together. ... The result: `W` has roughly orthogonal axes for "high-level style" (pose, identity) vs "fine style" (lighting, color). You can swap styles between two images by using image A's `w` for the low-resolution levels and image B's `w` for the high.

## The Concept · 概念

![StyleGAN：映射网络 + AdaIN + 逐层噪声](../assets/stylegan.svg)

**映射网络（mapping network）。** `f: Z → W`，一个 8 层 MLP。`Z = N(0, I)^512`。`W` 不被强制成高斯——它学出一个贴合数据的形状。

**合成网络（synthesis network）。** 从一个学出来的常数 `4×4×512` 出发。每个分辨率块：`upsample → conv → AdaIN(w_i) → noise → conv → AdaIN(w_i) → noise`。分辨率逐级翻倍：4, 8, 16, 32, 64, 128, 256, 512, 1024。

**AdaIN。**

```
AdaIN(x, y) = y_scale · (x - mean(x)) / std(x) + y_bias
```

其中 `y_scale` 和 `y_bias` 来自 `w` 的仿射投影。先按特征图归一化，再重新上风格。这里的「风格」就是特征图的一阶和二阶统计量。

**逐层噪声。** 加到每个特征图上的单通道高斯噪声，乘一个可学的逐通道系数。控制随机细节而不动全局结构。

**截断技巧（truncation trick）。** 推理时，采样 `z`，算 `w = mapping(z)`，然后 `w' = ŵ + ψ·(w - ŵ)`，其中 `ŵ` 是许多样本的平均 `w`。`ψ < 1` 用多样性换质量。几乎每个 StyleGAN 演示都用 `ψ ≈ 0.7`。

> **Mapping network.** `f: Z → W`, an 8-layer MLP. `Z = N(0, I)^512`. `W` is not forced to be Gaussian — it learns a data-adapted shape. ... **Truncation trick.** At inference, sample `z`, compute `w = mapping(z)`, then `w' = ŵ + ψ·(w - ŵ)` where `ŵ` is the mean `w` over many samples. `ψ < 1` trades diversity for quality. Almost every StyleGAN demo uses `ψ ≈ 0.7`.

## StyleGAN 1 → 2 → 3

| 版本 | 年份 | 创新 |
|---------|------|------------|
| StyleGAN | 2019 | 映射网络 + AdaIN + 噪声 + 渐进增长（progressive growing）。 |
| StyleGAN2 | 2020 | 权重解调（weight demodulation）替代 AdaIN（修好水滴伪影）；跳连/残差架构；路径长度正则化。 |
| StyleGAN3 | 2021 | 抗混叠卷积 + 等变核；消除纹理粘在像素网格上。 |
| StyleGAN-XL | 2022 | 类条件、1024²、ImageNet。 |
| R3GAN | 2024 | 以更强的正则化重新出发；参数少 20 倍，在 FFHQ-1024 上追平与扩散的差距。 |

2026 年，StyleGAN3 依然是以下场景的默认选择：(a) 高帧率的窄域照片级真实感，(b) 少样本域适应（用 100 张图训一个新数据集，冻结映射网络），(c) 基于反演的编辑（找到能重建一张真实照片的 `w`，然后编辑这个 `w`）。开放域文生图不是它的战场——那是扩散的。

```figure
gx-stylegan-mapping
```

> In 2026 StyleGAN3 remains the default for (a) narrow-domain photorealism at high FPS, (b) few-shot domain adaptation (train on a new dataset with 100 images, freeze mapping), (c) inversion-based editing (find the `w` that reconstructs a real photo, then edit that `w`). For open-domain text-to-image, it is not the tool — diffusion is.

## Build It · 动手造

`code/main.py` 在一维上实现一个玩具版「style-GAN lite」：一个映射 MLP、一个合成函数（吃一个学出来的常数向量，用来自 `w` 的 scale/bias 调制它），外加逐层噪声。它展示：通过仿射调制注入 `w`，效果持平或好于把 `z` 拼进生成器的输入。

> `code/main.py` implements a toy "style-GAN lite" in 1-D: a mapping MLP, a synthesis function that takes a learned constant vector and modulates it with `w`-derived scale/bias, and per-layer noise. It shows that injecting `w` via affine-modulation matches or beats concatenating `z` into the generator's input.

### Step 1: mapping network · 第 1 步：映射网络

```python
def mapping(z, M):
    h = z
    for i in range(num_layers):
        h = leaky_relu(add(matmul(M[f"W{i}"], h), M[f"b{i}"]))
    return h
```

### Step 2: adaptive instance normalization · 第 2 步：自适应实例归一化

```python
def adain(x, w_scale, w_bias):
    mu = mean(x)
    sd = std(x)
    x_norm = [(xi - mu) / (sd + 1e-8) for xi in x]
    return [w_scale * xi + w_bias for xi in x_norm]
```

每个特征图的 scale 和 bias 由 `w` 经线性投影得到。

> Per-feature-map scale and bias come from `w` via linear projection.

### Step 3: per-layer noise · 第 3 步：逐层噪声

```python
def add_noise(x, sigma, rng):
    return [xi + sigma * rng.gauss(0, 1) for xi in x]
```

Sigma 逐通道可学。

> Sigma per-channel is learnable.

## Pitfalls · 常见的坑

- **水滴伪影（droplet artifacts）。** StyleGAN 1 的特征图上会出现水滴状斑块，因为 AdaIN 把均值清零了。StyleGAN 2 的权重解调改成缩放卷积权重，把它修好了。
- **纹理粘连（texture sticking）。** StyleGAN 1 和 2 的纹理跟着像素坐标走，而不是物体坐标（插值时可见）。StyleGAN 3 用加窗 sinc 滤波器的抗混叠卷积修好了它。
- **模式覆盖。** 截断 `ψ < 0.7` 看着干净，但样本来自一个窄锥；需要多样性就用 `ψ = 1.0`。
- **反演有损。** 把真实照片反演进 `W` 通常靠优化或编码器（e4e、ReStyle、HyperStyle）。迭代多了结果会漂移。

> **Droplet artifacts.** StyleGAN 1 produced a blobby droplet in the feature maps because AdaIN zeroed out mean. StyleGAN 2's weight demodulation fixes it by scaling the convolution weights instead. ... **Texture sticking.** StyleGAN 1 and 2 textures followed pixel coordinates, not object coordinates (visible when interpolating). StyleGAN 3's alias-free convolutions fix this with windowed sinc filters.

## Use It · 实战用法

| 用例 | 方案 |
|----------|----------|
| 照片级真人脸（动漫、产品、窄域） | StyleGAN3 FFHQ / 自定义微调 |
| 从一张照片编辑人脸 | e4e 反演 + StyleSpace / InterFaceGAN 方向 |
| 换脸 / 面部重现 | StyleGAN + 编码器 + 融合 |
| 头像管线 | StyleGAN3 配 ADA 做低数据微调 |
| 从几张图做域适应 | 冻结映射网络，微调合成网络 |
| 多模态或文本条件生成 | 别用——上扩散 |

对「一个人脸照片」就是答案的产品级演示，StyleGAN 在推理成本（单次前向，4090 上 <10ms）和同等质量门槛下的锐利度上都打赢扩散。

> For product-grade demos where the answer is "photo of a person's face", StyleGAN beats diffusion on inference cost (single forward pass, <10ms on a 4090) and sharpness for the same quality bar.

## Ship It · 交付

保存 `outputs/skill-stylegan-inversion.md`。这个 skill 接收一张真实照片，输出：反演方法（e4e / ReStyle / HyperStyle）、预期潜空间损失、编辑预算（在 `W` 里能走多远才出伪影），以及一组已知好用的编辑方向（年龄、表情、姿态）。

> Save `outputs/skill-stylegan-inversion.md`. Skill takes a real photo and outputs: inversion method (e4e / ReStyle / HyperStyle), expected latent loss, editing budget (how far in `W` you can move before artifacts), and a list of known-good editing directions (age, expression, pose).

## Exercises · 练习

1. **简单。** 分别用 `adain_on=True` 和 `adain_on=False` 跑 `code/main.py`。比较固定潜变量 vs 扰动潜变量时输出的散布。
2. **中等。** 实现混合正则化（mixing regularization）：对一个训练 batch，算出 `w_a`、`w_b`，合成的前半段用 `w_a`、后半段用 `w_b`。解码器学到解耦的风格了吗？
3. **困难。** 拿一个预训练的 StyleGAN3 FFHQ 模型（ffhq-1024.pkl）。在带标签样本上训练一个 SVM，找到控制「微笑」的 `w` 方向；报告推到多远之前身份不会漂移。

## Key Terms · 术语表

| 术语 | 人们的说法 | 实际含义 |
|------|-----------------|-----------------------|
| Mapping network | 「那个 MLP」 | `f: Z → W`，8 层，把潜空间几何与数据统计解耦。 |
| W space | 「风格空间」 | 映射网络的输出；大致解耦。 |
| AdaIN | 「自适应实例归一化」 | 先归一化特征图，再用 `w` 的投影做缩放 + 平移。 |
| Truncation trick | 「Psi」 | `w = mean + ψ·(w - mean)`，ψ<1 用多样性换质量。 |
| Path-length regularization | 「PL 正则」 | 惩罚 `w` 单位变化引起的图像大幅变化；让 `W` 更平滑。 |
| Weight demodulation | 「StyleGAN2 的修法」 | 归一化卷积权重而不是激活；消灭水滴伪影。 |
| Alias-free | 「StyleGAN3 的技巧」 | 加窗 sinc 滤波器；消除纹理粘在像素网格上。 |
| Inversion | 「给真实图像找 w」 | 优化或编码 `x → w`，使得 `G(w) ≈ x`。 |

## Production note: why StyleGAN still ships in 2026 · 生产备注：为什么 2026 年 StyleGAN 还在出货

StyleGAN3 在 4090 上生成一张 1024² 的 FFHQ 人脸用时不到 10 ms——`num_steps = 1`，没有 VAE 解码，没有 cross-attention。用生产的话说，这是一切图像生成器的时延地板。同分辨率下，一条 50 步 SDXL + VAE 解码的管线约 3 秒。这是 **300 倍的差距**，而对窄域产品（头像服务、证件照管线、库存人脸生成）来说，它在 TCO 上赢。

两个运营层面的后果：

- **没有调度器，没有批处理器。** 目标占用率下的静态 batch 就是最优。连续批处理（对 LLM 和扩散至关重要）在这里毫无收益，因为每个请求的 FLOPs 相同。
- **截断 `ψ` 是安全旋钮。** `ψ < 0.7` 只从映射网络值域的一个窄锥里采样。这是服务层手里唯一能拧样本方差的杠杆。峰值负载时调低 `ψ`，高级用户调高。

> StyleGAN3 on a 4090 generates a 1024² FFHQ face in under 10 ms — `num_steps = 1`, no VAE decode, no cross-attention pass. In production terms this is the floor latency for any image generator. ... **Truncation `ψ` is the safety knob.** `ψ < 0.7` samples from a narrow cone of the mapping network's range. This is the only lever the serving layer has over sample variance. Lower `ψ` at peak load, raise it for premium users.

## Further Reading · 延伸阅读

- [Karras et al. (2019). A Style-Based Generator Architecture for GANs](https://arxiv.org/abs/1812.04948) —— StyleGAN。
- [Karras et al. (2020). Analyzing and Improving the Image Quality of StyleGAN](https://arxiv.org/abs/1912.04958) —— StyleGAN2。
- [Karras et al. (2021). Alias-Free Generative Adversarial Networks](https://arxiv.org/abs/2106.12423) —— StyleGAN3。
- [Tov et al. (2021). Designing an Encoder for StyleGAN Image Manipulation](https://arxiv.org/abs/2102.02766) —— e4e 反演。
- [Sauer et al. (2022). StyleGAN-XL: Scaling StyleGAN to Large Diverse Datasets](https://arxiv.org/abs/2202.00273) —— StyleGAN-XL。
- [Huang et al. (2024). R3GAN: The GAN is dead; long live the GAN!](https://arxiv.org/abs/2501.05441) —— 现代极简 GAN 配方。
