# Latent Diffusion & Stable Diffusion · 潜空间扩散与 Stable Diffusion

> Pixel-space diffusion on 512×512 images is a computational war crime. Rombach et al. (2022) noticed that you do not need all 786k dimensions to generate an image — you need enough to capture semantic structure, and a separate decoder for the rest. Run diffusion inside a VAE's latent space. That one idea is Stable Diffusion.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 8 · 02 (VAE), Phase 8 · 06 (DDPM), Phase 7 · 09 (ViT)
**Time:** ~75 minutes

## The Problem · 问题

512² 的像素空间扩散意味着 U-Net 要在形状为 `[B, 3, 512, 512]` 的张量上运行。对一个 5 亿参数的 U-Net，每个采样步约 100 GFLOPS。五十步就是每张图 5 TFLOPS。再在十亿张图上训练，算力账单就是个天文数字。

这些 FLOP 的大头都花在把「感知上不重要的细节」推过网络 —— 那些有损 VAE 本可以压缩掉的高频纹理。Rombach 的想法：训练一次 VAE（*第一阶段*，first stage），冻结它，然后把扩散完全放进 4 通道 64×64 的潜空间（latent space）里跑（*第二阶段*，second stage）。同一个 U-Net，1/16 的像素量，质量相近的情况下 FLOP 少约 64 倍。

这就是 Stable Diffusion 的配方。SD 1.x / 2.x 用 860M 的 U-Net 跑在 `64×64×4` 的 latent 上；SDXL 用 2.6B 的 U-Net 跑在 `128×128×4` 上；SD3 把 U-Net 换成了带 flow matching 的 Diffusion Transformer（DiT）。Flux.1-dev（Black Forest Labs, 2024）则是一个 12B 参数的 DiT-MMDiT。它们全都跑在同一个两阶段底座上。

> Pixel-space diffusion at 512² means the U-Net runs on tensors of shape `[B, 3, 512, 512]`. ... Rombach's idea: train a VAE once (the *first stage*), freeze it, and run diffusion entirely in the 4-channel 64×64 latent space (the *second stage*). Same U-Net. 1/16th the pixels. ~64x fewer FLOPs for comparable quality. ... This is the Stable Diffusion recipe. ... All run on the same two-stage substrate.

## The Concept · 概念

![潜空间扩散：VAE 压缩 + 潜空间中的扩散](../assets/latent-diffusion.svg)

**两个阶段，分开训练。**

1. **第 1 阶段 —— VAE。** 编码器 `E(x) → z`，解码器 `D(z) → x`。目标压缩率：每个空间轴下采样 8 倍 + 调整通道数，使 latent 总大小约为像素数的 1/16。损失 = 重建（L1 + LPIPS 感知损失）+ KL（权重很小，避免把 `z` 逼得太高斯，因为我们不需要从 `z` 精确采样）。通常还会加对抗损失，让解码出的图像更锐利。

2. **第 2 阶段 —— 在 `z` 上做扩散。** 把 `z = E(x_real)` 当作数据。训练一个 U-Net（或 DiT）对 `z_t` 去噪。推理时：先用扩散采样出 `z_0`，然后 `x = D(z_0)`。

**文本条件化。** 额外两个组件。一个冻结的文本编码器（SD 1.x 用 CLIP-L，SD 2/XL 用 CLIP-L+OpenCLIP-G，SD3 和 Flux 用 T5-XXL）。一个交叉注意力（cross-attention）注入：每个 U-Net block 都接收 `[Q = 图像特征, K = V = 文本 token]`，并把它们混合进来。这些 token 是文本影响图像的唯一通道。

**损失函数与第 06 课完全相同。** 同样的 DDPM / flow matching 噪声 MSE。你只是换了数据域。

> **Two stages, separately trained.** ... **Stage 1 — VAE.** Encoder `E(x) → z`, decoder `D(z) → x`. Target compression: 8× downsample in each spatial axis + adjust channels so total latent size is ~1/16th of pixel count ... **Text conditioning.** Two additional components. A frozen text encoder ... The tokens are the only way text influences the image. ... **The loss function is identical to Lesson 06.** Same DDPM / flow matching MSE on noise. You just swap the data domain.

## Architecture variants · 架构变体

| 模型 | 年份 | 骨干网络 | Latent 形状 | 文本编码器 | 参数量 |
|-------|------|----------|--------------|--------------|--------|
| SD 1.5 | 2022 | U-Net | 64×64×4 | CLIP-L（77 tokens） | 860M |
| SD 2.1 | 2022 | U-Net | 64×64×4 | OpenCLIP-H | 865M |
| SDXL | 2023 | U-Net + refiner | 128×128×4 | CLIP-L + OpenCLIP-G | 2.6B + 6.6B |
| SDXL-Turbo | 2023 | 蒸馏版 | 128×128×4 | 同上 | 1-4 步采样 |
| SD3 | 2024 | MMDiT（multimodal DiT） | 128×128×16 | T5-XXL + CLIP-L + CLIP-G | 2B / 8B |
| Flux.1-dev | 2024 | MMDiT | 128×128×16 | T5-XXL + CLIP-L | 12B |
| Flux.1-schnell | 2024 | MMDiT 蒸馏版 | 128×128×16 | T5-XXL + CLIP-L | 12B，1-4 步 |

趋势：用 DiT（作用在 latent patch 上的 transformer）替换 U-Net、加大文本编码器（在 prompt 遵循度上 T5 胜过 CLIP）、增加 latent 通道数（4 → 16，给细节留出更多余量）。

```figure
noise-schedule
```

> The trend: replace U-Net with DiT (transformer over latent patches), scale the text encoder (T5 beats CLIP for prompt adherence), increase latent channels (4 → 16 gives more detail headroom).

## Build It · 动手造

`code/main.py` 在第 06 课的 DDPM 之上叠了一个玩具级 1-D「VAE」（恒等编码器 + 解码器，仅作演示；真正的 VAE 会是卷积网络），并加上了带 classifier-free guidance 的类别条件化。它展示了：无论你跑在原始 1-D 数值上还是编码后的数值上，同一个扩散损失都成立 —— 这就是核心洞见。

> `code/main.py` stacks a toy 1-D "VAE" (identity encoder + decoder, for demonstration; a real VAE would be a conv net) on top of the DDPM from Lesson 06 and adds class conditioning with classifier-free guidance. ... It shows that the same diffusion loss works whether you run on raw 1-D values or on encoded values — the key insight.

### Step 1: encoder/decoder · 第 1 步：编码器/解码器

```python
def encode(x):    return x * 0.5          # toy "compression" to smaller scale
def decode(z):    return z * 2.0
```

真实的 VAE 有训练出来的权重。出于教学目的，这个线性映射足以说明：扩散作用于 `z`，并不关心原始数据空间。

> A real VAE has trained weights. For pedagogy, this linear map is enough to show that diffusion operates on `z` without caring about the original data space.

### Step 2: diffusion in `z`-space · 第 2 步：在 `z` 空间中扩散

与第 06 课相同的 DDPM。网络看到的数据是 `z = E(x)`。采样出 `z_0` 之后，用 `D(z_0)` 解码。

> Same DDPM as Lesson 06. The data the net sees is `z = E(x)`. After sampling `z_0`, decode with `D(z_0)`.

### Step 3: classifier-free guidance · 第 3 步：classifier-free guidance

训练时以 10% 的概率丢弃类别标签（替换成 null token）。推理时同时计算 `ε_cond` 和 `ε_uncond`，然后：

```python
eps_cfg = (1 + w) * eps_cond - w * eps_uncond
```

`w = 0` = 无引导（完全的多样性），`w = 3` = 默认值，`w = 7+` = 过饱和 / 过锐。

> During training, drop the class label 10% of the time (replace with a null token). At inference, compute both `ε_cond` and `ε_uncond`, then: ... `w = 0` = no guidance (full diversity), `w = 3` = default, `w = 7+` = saturated / over-sharp.

### Step 4: text conditioning (concept, not code) · 第 4 步：文本条件化（概念，非代码）

把类别标签换成冻结文本编码器的输出。通过 cross-attention 把文本嵌入喂给 U-Net：

```python
h = h + CrossAttention(Q=h, K=text_embed, V=text_embed)
```

这就是「类别条件扩散模型」与「Stable Diffusion」之间唯一的实质性区别。

> Replace the class label with a frozen text encoder output. Feed the text embedding to the U-Net via cross-attention: ... This is the only substantive difference between a class-conditional diffusion model and Stable Diffusion.

## Pitfalls · 常见坑

- **VAE scale 不匹配。** SD 1.x 的 VAE 在编码之后要乘一个缩放常数（`scaling_factor ≈ 0.18215`）。忘了它，U-Net 就会在方差完全错误的 latent 上训练。每个 checkpoint 都自带一个。
- **文本编码器悄悄出错。** SD3 需要 T5-XXL 且 >=128 个 token，回退到只用 CLIP 是有损的。务必检查 `use_t5=True`，否则 prompt 保真度直接崩塌。
- **混用潜空间。** SDXL、SD3、Flux 用的是不同的 VAE。在 SDXL latent 上训练的 LoRA 到 SD3 上没法用。Hugging Face diffusers 0.30+ 会拒绝加载不匹配的 checkpoint。
- **CFG 过高。** `w > 10` 会产出饱和、油腻的图像，并以牺牲多样性为代价过拟合 prompt。甜蜜点是 `w = 3-7`。
- **负面 prompt 泄漏。** 空的负面 prompt 会变成 null token；填了内容的负面 prompt 会变成 `ε_uncond`。这两者不是一回事；有些 pipeline 会悄悄默认用 null。

> **VAE-scale mismatch.** SD 1.x VAEs have a scaling constant (`scaling_factor ≈ 0.18215`) applied after encoding ... **CFG too high.** `w > 10` produces saturated, oily images and over-fits the prompt at the cost of diversity. The sweet spot is `w = 3-7` ... **Negative prompts leaking.** Empty negative prompt becomes the null token; a filled negative prompt becomes the `ε_uncond`. These are not the same.

## Use It · 实战用法

2026 年的生产技术栈：

| 目标 | 推荐骨干 |
|--------|----------------------|
| 窄领域、有成对数据、从头训练模型 | SDXL 微调（LoRA / 全量）—— 上线最快 |
| 开放域文生图、开放权重 | Flux.1-dev（12B，Apache / 非商用）或 SD3.5-Large |
| 最快推理、开放权重 | Flux.1-schnell（1-4 步，Apache）或 SDXL-Lightning |
| 最佳 prompt 遵循度、托管服务 | GPT-Image / DALL-E 3（依然是）、Midjourney v7、Imagen 4 |
| 编辑工作流 | Flux.1-Kontext（2024 年 12 月）—— 原生接受图像 + 文本 |
| 研究、基线 | SD 1.5 —— 老旧但研究充分 |

## Ship It · 交付

保存 `outputs/skill-sd-prompter.md`。这个 skill 接收一个文本 prompt + 目标风格，输出：模型 + checkpoint、CFG scale、采样器、负面 prompt、分辨率、可选的 ControlNet/IP-Adapter 组合，以及一份逐步 QA 检查清单。

> Save `outputs/skill-sd-prompter.md`. Skill takes a text prompt + target style and outputs: model + checkpoint, CFG scale, sampler, negative prompt, resolution, optional ControlNet/IP-Adapter combo, and a per-step QA checklist.

## Exercises · 练习

1. **简单。** 用 guidance `w ∈ {0, 1, 3, 7, 15}` 跑 `code/main.py`。记录每个类别的样本均值。`w` 到多少时类别均值会偏离真实数据均值？
2. **中等。** 把玩具线性编码器换成一个带重建损失的 tanh-MLP 编码器/解码器对。在新 latent 上重新训练扩散。样本质量有变化吗？
3. **困难。** 用 diffusers 搭一个真实的 Stable Diffusion 推理：加载 `sdxl-base`，用 CFG=7 跑 30 步 Euler 并计时。然后换成 `sdxl-turbo`、4 步、CFG=0。同一个主体，不同的质量 —— 描述变化了什么、为什么。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| First stage | 「那个 VAE」 | 训练好的编码器/解码器对；把 512² 压到 64²。 |
| Second stage | 「那个 U-Net」 | 作用在潜空间上的扩散模型。 |
| CFG | 「guidance scale」 | `(1+w)·ε_cond - w·ε_uncond`；调节条件强度。 |
| Null token | 「空 prompt 嵌入」 | 用于 `ε_uncond` 的无条件嵌入。 |
| Cross-attention | 「文本如何进来」 | 每个 U-Net block 把文本 token 当作 K 和 V 来注意。 |
| DiT | 「Diffusion Transformer」 | 用作用在 latent patch 上的 transformer 替换 U-Net；扩展性更好。 |
| MMDiT | 「多模态 DiT」 | SD3 的架构：文本与图像两条流做联合注意力。 |
| VAE scaling factor | 「魔法数字」 | 把 latent 除以约 5.4，让扩散在单位方差空间里工作。 |

## Production note: running Flux-12B on an 8GB consumer GPU · 生产备注：在 8GB 消费级 GPU 上运行 Flux-12B

参考的 Flux 集成就是那个标准的「我有消费级 GPU，这玩意能上线吗？」配方。诀窍还是生产推理文献列出的那三个旋钮，只不过这次用在一个 diffusion DiT 上：

1. **错峰加载。** Flux 有三个从不需要同时驻留显存的网络：T5-XXL 文本编码器（fp32 下约 10 GB）、CLIP-L（很小）、12B 的 MMDiT，以及 VAE。先编码 prompt，*删掉*编码器，加载 DiT，去噪，*删掉* DiT，加载 VAE，解码。消费级 8GB GPU 一次只能装下一个阶段。
2. **用 bitsandbytes 做 4-bit 量化。** 在 T5 编码器和 DiT 上都加 `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16)`。显存省 8 倍；按 Aritra 的基准测试（notebook 里有链接），对文生图而言质量下降难以察觉。
3. **CPU offload。** `pipe.enable_model_cpu_offload()` 会在每次前向传播推进时自动在 CPU 和 GPU 之间换入换出模块。增加 10-20% 延迟，但至少能让整条 pipeline 跑起来。

显存账本是：量化后 `10 GB T5 / 8 = 1.25 GB`，量化 DiT `12 B params × 0.5 bytes = ~6 GB`，再加上激活值。用 stas00 的话说，这是 TP=1 推理的极端情况 —— 没有模型并行，量化拉满。生产环境你会在 H100 上跑 TP=2 或 TP=4；对一台开发笔记本来说，这就是配方。

> **Staggered loading.** Flux has three networks that never need to coexist in VRAM: T5-XXL text encoder (~10 GB in fp32), CLIP-L (small), the 12B MMDiT, and the VAE ... **4-bit quantization via bitsandbytes.** `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16)` on both the T5 encoder and the DiT ... **CPU offload.** `pipe.enable_model_cpu_offload()` auto-swaps modules between CPU and GPU as each forward pass advances ... For production you'd run TP=2 or TP=4 on H100s; for a single dev laptop, this is the recipe.

## Further Reading · 延伸阅读

- [Rombach et al. (2022). High-Resolution Image Synthesis with Latent Diffusion Models](https://arxiv.org/abs/2112.10752) —— Stable Diffusion。
- [Podell et al. (2023). SDXL: Improving Latent Diffusion Models for High-Resolution Image Synthesis](https://arxiv.org/abs/2307.01952) —— SDXL。
- [Peebles & Xie (2023). Scalable Diffusion Models with Transformers (DiT)](https://arxiv.org/abs/2212.09748) —— DiT。
- [Esser et al. (2024). Scaling Rectified Flow Transformers for High-Resolution Image Synthesis](https://arxiv.org/abs/2403.03206) —— SD3、MMDiT。
- [Ho & Salimans (2022). Classifier-Free Diffusion Guidance](https://arxiv.org/abs/2207.12598) —— CFG。
- [Labs (2024). Flux.1 — Black Forest Labs announcement](https://blackforestlabs.ai/announcing-black-forest-labs/) —— Flux.1 家族。
- [Hugging Face Diffusers docs](https://huggingface.co/docs/diffusers/index) —— 上面每个 checkpoint 的参考实现。
