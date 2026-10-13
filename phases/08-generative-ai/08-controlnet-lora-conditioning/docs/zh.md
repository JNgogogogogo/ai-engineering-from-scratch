# ControlNet, LoRA & Conditioning · ControlNet、LoRA 与条件化

> Text alone is a clumsy control signal. ControlNet lets you clone a pretrained diffusion model and steer it with a depth map, pose skeleton, scribble, or edge image. LoRA lets you fine-tune a 2B-parameter model by training 10 million parameters. Together they turned Stable Diffusion from a toy into the 2026 image pipeline that ships at every agency.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 8 · 07 (Latent Diffusion), Phase 10 (LLMs from Scratch — for LoRA foundation)
**Time:** ~75 minutes

## The Problem · 问题

像 "a woman in a red dress walking a dog on a busy street" 这样的 prompt，不会告诉模型狗*在哪*、女人*摆的是什么姿势*、街道*是什么样的透视*。文本只能钉死指定一张图所需信息的 10% 左右。剩下的部分是视觉的，没法用语言高效描述。

为每种信号（姿态、深度、canny、分割）都从头训练一个新的条件模型，代价高得离谱。你想要的是：冻结 2.6B 参数的 SDXL 主干，挂一个小型侧网络去读取条件信号，让它轻轻推动主干的中间特征。这就是 ControlNet。

你还想在不重训整个模型的前提下教模型新概念（你的脸、你的产品、你的风格）。你想要一个小 100 倍的增量。这就是 LoRA —— 插进现有注意力权重里的低秩适配器（low-rank adapter）。

ControlNet + LoRA + 文本 = 2026 年从业者的工具箱。大多数生产级图像 pipeline 都是在 SDXL / SD3 / Flux 底座之上，叠 2-5 个 LoRA、1-3 个 ControlNet，再加一个 IP-Adapter。

> A prompt like "a woman in a red dress walking a dog on a busy street" gives the model no information about *where* the dog is ... That is ControlNet. ... That is LoRA — low-rank adapters that plug into existing attention weights. ... Most production image pipelines layer 2-5 LoRAs, 1-3 ControlNets, and an IP-Adapter on top of an SDXL / SD3 / Flux base.

## The Concept · 概念

![ControlNet 克隆编码器；LoRA 添加低秩增量](../assets/controlnet-lora.svg)

### ControlNet (Zhang et al., 2023) · ControlNet（Zhang et al., 2023）

拿一个预训练好的 SD。*克隆* U-Net 的编码器一半。冻结原件。训练克隆体去接收一个额外的条件输入（边缘、深度、姿态）。再用*零卷积*（zero-convolution）跳连把克隆体接回原件的解码器一半（初始化为零的 1×1 卷积 —— 起步时是无操作，逐渐学出一个增量）。

```
SD U-Net decoder:   ... ← orig_enc_features + zero_conv(controlnet_enc(condition))
```

零卷积初始化意味着 ControlNet 起步时是恒等映射 —— 训练之前也不会有任何破坏。用标准扩散损失在 100 万条（prompt, condition, image）三元组上训练。

每种模态的 ControlNet 都以小型侧模型的形式发布（SDXL 约 360M，SD 1.5 约 70M）。推理时可以组合它们：

```
features += weight_a * control_a(depth) + weight_b * control_b(pose)
```

> Take a pretrained SD. *Clone* the encoder half of the U-Net ... Connect the clone back to the decoder half of the original with *zero-convolution* skip connections (1×1 convs initialized to zero — start as a no-op, learn a delta) ... Zero-conv init means ControlNet starts as identity — no harm even before training ... Per-modality ControlNets ship as small side models (~360M for SDXL, ~70M for SD 1.5).

### LoRA (Hu et al., 2021) · LoRA（Hu et al., 2021）

对模型里任意线性层 `W ∈ R^{d×d}`，冻结 `W`，加一个低秩增量（delta）：

```
W' = W + ΔW,  ΔW = B @ A,  A ∈ R^{r×d},  B ∈ R^{d×r}
```

其中 `r << d`。注意力层常用秩 4-16，重度微调用秩 64-128。新增参数量：`2 · d · r` 而不是 `d²`。对 SDXL 的注意力 `d=640`、`r=16`：每个适配器 2 万参数而不是 41 万 —— 缩小 20 倍。整个模型算下来：一个 LoRA 通常 20-200MB，而底座是 5GB。

推理时你可以缩放 LoRA：`W' = W + α · B @ A`。`α = 0.5-1.5` 是常态。多个 LoRA 以加法方式叠加（老生常谈的提醒：它们之间会以非线性方式互相影响）。

> For any linear layer `W ∈ R^{d×d}` in the model, freeze `W` and add a low-rank delta ... with `r << d`. Rank 4-16 is standard for attention, rank 64-128 for heavy fine-tunes ... At inference you can scale the LoRA: `W' = W + α · B @ A`. `α = 0.5-1.5` is normal. Multiple LoRAs stack additively.

### IP-Adapter (Ye et al., 2023) · IP-Adapter（Ye et al., 2023）

一个接收*图像*作为条件（与文本并列）的微型适配器。用 CLIP 图像编码器生成图像 token，把它们与文本 token 一起注入交叉注意力。每个底座约 20MB。让你不用 LoRA 就能实现「按这张参考图的风格生成一张图」。

> A tiny adapter that accepts an *image* as conditioning (alongside text). Uses the CLIP image encoder to produce image tokens, injects them into cross-attention alongside text tokens. ~20MB per base model. Lets you do "generate an image in the style of this reference" without a LoRA.

## Composability matrix · 可组合性矩阵

| 工具 | 控制什么 | 大小 | 何时使用 |
|------|------------------|------|-------------|
| ControlNet | 空间结构（姿态、深度、边缘） | 70-360MB | 精确的布局与构图 |
| LoRA | 风格、主体、概念 | 20-200MB | 个性化、风格化 |
| IP-Adapter | 从参考图取风格或主体 | 20MB | 文字描述不出的那种外观 |
| Textual Inversion | 把单个概念编码为新 token | 10KB | 遗留方案，大多已被 LoRA 取代 |
| DreamBooth | 对一个主体做全量微调 | 2-5GB | 强身份一致性、算力充足 |
| T2I-Adapter | 更轻量的 ControlNet 替代 | 70MB | 边缘设备、推理预算紧张 |

ControlNet ≈ 空间。LoRA ≈ 语义。两个都用。

```figure
v4-controlnet-zero
```

> ControlNet ≈ spatial. LoRA ≈ semantic. Use both.

## Build It · 动手造

`code/main.py` 在 1-D 上模拟这两个机制：

1. **LoRA。** 一个预训练的线性层 `W`。冻结它。训练一个低秩的 `B @ A`，使 `W + BA` 匹配一个目标线性层。展示 `r = 1` 就足以完美学出一个秩 1 修正。

2. **ControlNet-lite。** 一个「冻结底座」预测器，加一个读取额外信号的「侧网络」。侧网络的输出被一个初始化为零的可学习标量门控（我们版本的零卷积）。训练时观察这个门逐渐抬升。

> `code/main.py` simulates the two mechanisms on 1-D ... **LoRA.** A pretrained linear layer `W`. Freeze it. Train a low-rank `B @ A` such that `W + BA` matches a target linear layer ... **ControlNet-lite.** The side network's output is gated by a learnable scalar initialized to zero (our version of zero-conv).

### Step 1: LoRA math · 第 1 步：LoRA 数学

```python
def lora(W, A, B, x, alpha=1.0):
    # W is frozen; A, B are the trainable low-rank factors.
    return [W[i][j] * x[j] for i, j in ...] + alpha * (B @ (A @ x))
```

### Step 2: zero-init side network · 第 2 步：零初始化侧网络

```python
side_out = control_net(x, condition)
gated = gate * side_out  # gate initialized to 0
h = base(x) + gated
```

第 0 步时输出与底座完全一致。训练早期 `gate` 更新得很慢 —— 不会出现灾难性漂移。

> At step 0 the output is identical to base. Early training updates `gate` slowly — no catastrophic drift.

## Pitfalls · 常见坑

- **LoRA 过度缩放。** `α = 2` 或 `α = 3` 是常见的「让它更强」野路子，会产出过度风格化 / 崩坏的输出。保持 `α ≤ 1.5`。
- **ControlNet 权重冲突。** Pose ControlNet 权重 1.0 加 Depth ControlNet 权重 1.0，通常用力过猛。权重之和 ≈ 1.0 是安全默认。
- **LoRA 用错底座。** SDXL LoRA 在 SD 1.5 上会静默无效，因为注意力维度对不上。diffusers 0.30+ 会给出警告。
- **Textual Inversion 漂移。** 在一个 checkpoint 上训练的 token，换一个 checkpoint 会严重漂移。LoRA 的可移植性更好。
- **LoRA 权重合并与存储。** 你可以把 LoRA 烘焙进底座权重来加速推理（运行时不再做加法），但会失去运行时调节 `α` 的能力。两个版本都留着。

> **Over-scaling LoRAs.** `α = 2` or `α = 3` is a common "make it stronger" hack that produces over-stylized / broken outputs. Keep `α ≤ 1.5` ... **ControlNet weight conflict.** ... Sum of weights ≈ 1.0 is a safe default ... **LoRA weight-merging and storage.** You can bake a LoRA into the base model weights for faster inference (no runtime addition), but you lose the ability to scale `α` at runtime.

## Use It · 实战用法

| 目标 | 2026 年 pipeline |
|------|---------------|
| 复现一个品牌的艺术风格 | 用约 30 张精选图片、秩 32 训练的 LoRA |
| 把我的脸放进生成的图里 | DreamBooth 或 LoRA + IP-Adapter-FaceID |
| 特定姿势 + prompt | ControlNet-Openpose + SDXL + 文本 |
| 深度感知的构图 | ControlNet-Depth + SD3 |
| 参考图 + prompt | IP-Adapter + 文本 |
| 精确布局 | ControlNet-Scribble 或 ControlNet-Canny |
| 换背景 | ControlNet-Seg + Inpainting（第 09 课） |
| 快速 1 步风格化 | SDXL-Turbo 上的 LCM-LoRA |

## Ship It · 交付

保存 `outputs/skill-sd-toolkit-composer.md`。这个 skill 接收一个任务（输入资产：prompt、可选参考图、可选姿态、可选深度、可选涂鸦），输出工具栈、各工具权重，以及一套可复现的 seed 协议。

> Save `outputs/skill-sd-toolkit-composer.md`. Skill takes a task (input assets: prompt, optional reference image, optional pose, optional depth, optional scribble) and outputs the tool stack, weights, and a reproducible seed protocol.

## Exercises · 练习

1. **简单。** 在 `code/main.py` 里把 LoRA 秩 `r` 从 1 变到 4。秩为多少时 LoRA 能精确匹配一个秩 2 的目标增量？
2. **中等。** 在两个目标变换上分别训练两个 LoRA。同时加载它们，展示其加性交互。这种交互在什么时候会打破线性性？
3. **困难。** 用 diffusers 叠加：SDXL-base + Canny-ControlNet（权重 0.8）+ 一个风格 LoRA（α 0.8）+ IP-Adapter（权重 0.6）。测量叠加权重变化时 FID 与 prompt 遵循度之间的权衡。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| ControlNet | 「空间控制」 | 克隆的编码器 + 零卷积跳连；读取一张条件图像。 |
| Zero convolution | 「起步即恒等」 | 初始化为零的 1×1 卷积；ControlNet 起步时是无操作。 |
| LoRA | 「低秩适配器」 | `W + B @ A`，`r << d`；参数量比全量微调少 100 倍。 |
| rank r | 「那个旋钮」 | LoRA 的压缩率；常取 4-16，重度个性化用 64+。 |
| α | 「LoRA 强度」 | 对 LoRA 增量的运行时缩放。 |
| IP-Adapter | 「参考图」 | 通过 CLIP 图像 token 实现的小型图像条件适配器。 |
| DreamBooth | 「主体全量微调」 | 用约 30 张主体图片训练整个模型。 |
| Textual Inversion | 「新 token」 | 只学一个新的词嵌入；遗留方案，大多已被取代。 |

## Production note: LoRA swaps, ControlNet lanes, multi-tenant serving · 生产备注：LoRA 热切换、ControlNet 通道与多租户服务

一个真实的文生图 SaaS 会在同一个底座 checkpoint 上服务几百个 LoRA 和十来个 ControlNet。这个服务问题非常像 LLM 的多租户（生产文献在 continuous batching 和 LoRAX / S-LoRA 的名下讨论的是 LLM 情形）：

- **热切换 LoRA，不要合并。** 把 `W' = W + α·B·A` 合并进底座能让每步推理快约 3-5%，但会冻死 `α` 和底座。把 LoRA 作为 rank-r 增量热驻留在显存里；diffusers 提供 `pipe.load_lora_weights()` + `pipe.set_adapters([...], adapter_weights=[...])` 来按请求激活。切换成本是 `2 · d · r · num_layers` 个权重 —— MB 量级，亚秒级。
- **ControlNet 作为第二条注意力通道。** 克隆的编码器与底座并行运行。两个权重各 1.0 的 ControlNet = 每步多两次前向传播，而不是一次合并的前向。批量余量按平方级下降。给每个活跃的 ControlNet 预算约 1.5 倍步成本。
- **LoRA 也要量化。** 如果你量化了底座（见第 07 课，8GB 跑 Flux），LoRA 增量也能干净地量化到 8-bit 或 4-bit。QLoRA 式加载让你能在 4-bit Flux 底座上再叠 5-10 个 LoRA 而不爆显存。

Flux 专属说明：Niels 的 Flux-on-8GB notebook 把底座量化到 4-bit；在这个量化底座上叠一个风格 LoRA（`pipe.load_lora_weights("user/style-lora")`，`weight_name="pytorch_lora_weights.safetensors"`）依然可行。这就是 2026 年大多数 SaaS 机构上线的配方。

> **Hot-swap LoRAs, do not merge.** Merging `W' = W + α·B·A` into the base gives ~3-5% faster per-step inference but freezes `α` and the base ... **ControlNet as a second attention lane.** ... Budget for ~1.5× step cost per active ControlNet ... **Quantized LoRAs too.** QLoRA-style loading lets you stack 5-10 LoRAs on top of a 4-bit Flux base without blowing memory ... This is the recipe most SaaS agencies ship in 2026.

## Further Reading · 延伸阅读

- [Zhang, Rao, Agrawala (2023). Adding Conditional Control to Text-to-Image Diffusion Models](https://arxiv.org/abs/2302.05543) —— ControlNet。
- [Hu et al. (2021). LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685) —— LoRA（最初为 LLM 设计；后移植到扩散模型）。
- [Ye et al. (2023). IP-Adapter: Text Compatible Image Prompt Adapter](https://arxiv.org/abs/2308.06721) —— IP-Adapter。
- [Mou et al. (2023). T2I-Adapter: Learning Adapters to Dig Out More Controllable Ability](https://arxiv.org/abs/2302.08453) —— ControlNet 的更轻量替代。
- [Ruiz et al. (2023). DreamBooth: Fine Tuning Text-to-Image Diffusion Models for Subject-Driven Generation](https://arxiv.org/abs/2208.12242) —— DreamBooth。
- [HuggingFace Diffusers — ControlNet / LoRA / IP-Adapter docs](https://huggingface.co/docs/diffusers/training/controlnet) —— 参考 pipeline。
