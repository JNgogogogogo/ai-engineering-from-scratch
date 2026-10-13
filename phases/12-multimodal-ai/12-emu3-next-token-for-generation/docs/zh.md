# Emu3: Next-Token Prediction for Image and Video Generation · Emu3：用下一 token 预测做图像与视频生成

> BAAI 的 Emu3（Wang et al.，2024 年 9 月）是那份本该终结「扩散 vs 自回归」之争的 2024 年成果。一个 Llama 风格的 decoder-only transformer，只靠下一 token 预测这一个目标，在覆盖文本 + VQ 图像 token + 3D VQ 视频 token 的统一词表上训练，图像生成赢 SDXL，感知赢 LLaVA-1.6。没有 CLIP loss。没有扩散调度。推理时用 classifier-free guidance 提质量，但核心训练目标就是带 teacher forcing 的下一 token 预测。发表在 Nature。本课读懂 Emu3 论点 —— 更好的分词器加规模就是全部所需 —— 并与扩散路线对比。

> BAAI's Emu3 (Wang et al., September 2024) is the 2024 result that should have ended the diffusion-versus-autoregressive debate. A single Llama-style decoder-only transformer, trained only on the next-token-prediction objective, across a unified vocabulary of text + VQ image tokens + 3D VQ video tokens, beats SDXL on image generation and LLaVA-1.6 on perception. No CLIP loss. No diffusion schedule. Classifier-free guidance is used at inference for quality, but the core training objective is next-token prediction with teacher forcing. Published in Nature. This lesson reads the Emu3 thesis — why a better tokenizer plus scale is all you need — and contrasts with diffusion approaches.

**Type:** Learn
**Languages:** Python (stdlib, 3D video tokenizer math + autoregressive sampler skeleton)
**Prerequisites:** Phase 12 · 11 (Chameleon)
**Time:** ~120 minutes

## Learning Objectives · 学习目标

- 解释为什么 Emu3 的单 loss 下一 token 目标能成立，打破「图像质量必须靠扩散」的长期假设。
- 描述 3D 视频分词器：时空 VQ 码本长什么样、patch 为什么要跨时间。
- 在（训练算力、推理成本、质量上限）三个维度上比较 Emu3 与 Stable Diffusion XL。
- 说出同一个 Emu3 模型扮演的三个角色：Emu3-Gen（图像生成）、Emu3-Chat（感知）、Emu3-Stage2（视频生成）。

> Explain why Emu3's single-loss next-token objective works despite the long-held assumption that diffusion is required for image quality.
> Describe the 3D video tokenizer: what a spatiotemporal VQ codebook looks like, why patches span time.
> Compare Emu3 vs Stable Diffusion XL on (training compute, inference cost, quality ceiling).
> Name the three roles the same Emu3 model plays: Emu3-Gen (image gen), Emu3-Chat (perception), Emu3-Stage2 (video gen).

## The Problem · 问题在哪

到 2024 年为止的共识：图像生成需要扩散。论据是：离散图像 token 丢的信息太多、重建不出细节，而且自回归采样会在成千上万个 token 上累积误差。Stable Diffusion、DALL-E 3、Imagen、Midjourney 全都在用某种形式的扩散。Chameleon（第 12.11 课）在小规模上部分反驳了这一点，但质量没追上 SDXL。

Emu3 正面进攻这个论据。它的主张：更好的视觉分词器 + 足够的规模 + 下一 token loss = 在同一个还能做感知的模型里，做出打败扩散的图像生成。

这个赌注发表时颇有争议。两年后，开源统一生成家族（Emu3、Show-o、Janus-Pro、Transfusion）已是研究界的默认路线；生产级前沿模型看起来也在用某种变体。

> The conventional wisdom through 2024: image generation needs diffusion. ... Stable Diffusion, DALL-E 3, Imagen, Midjourney all use some form of diffusion. ... Emu3 attacked the argument head-on. The claim: better visual tokenizer + enough scale + next-token loss = diffusion-beating image generation in the same model that also does perception. ... Two years on, the open-source unified-generation family (Emu3, Show-o, Janus-Pro, Transfusion) is the default path for research; production frontier models appear to use some variant.

## The Concept · 概念

### The Emu3 tokenizer · Emu3 分词器

关键原料是视觉分词器。Emu3 训了一个 IBQ 类的自定义分词器（Inverse Bottleneck Quantizer，SBER-MoVQGAN 家族），每个 token 降低 8x8 的分辨率。一张 512x512 图变成 64x64 = 4096 个 token，码本大小 32768。

这比 Chameleon 每张 512x512 用 1024 token（K=8192）更多，但单个 token 更便宜（码本查找更小、编解码更简单）。关键指标：重建 PSNR 30.5 dB，与 Stable Diffusion 连续潜空间的 32 dB 有得一拼。

视频方面：3D VQ 分词器把一个时空 patch（4x4x4 像素）编成一个整数。8 FPS 的 4 秒片段有 32 帧；256x256 分辨率、空间压 4 倍、时间压 4 倍后，token 数是 (256/4) * (256/4) * (32/4) = 64 * 64 * 8 = 32,768 个。

分词器质量就是天花板。Emu3 的贡献有一部分就是「我们训了一个非常好的分词器」。

> The key ingredient is the visual tokenizer. Emu3 trains a custom IBQ-class tokenizer (Inverse Bottleneck Quantizer, SBER-MoVQGAN family) at 8x8 resolution-reduction per token. A 512x512 image becomes 64x64 = 4096 tokens at codebook size 32768. ... The key metric: reconstruction PSNR at 30.5 dB, competitive with Stable Diffusion's continuous latent space at 32 dB. ... Tokenizer quality is the ceiling. Emu3's contribution is partly "we trained a very good tokenizer."

### Single-loss training · 单 loss 训练

Emu3 只用一个目标：在覆盖文本 token、2D 图像 token、3D 视频 token 的共享词表上做下一 token 预测。训练时权重乘上按模态区分的因子来平衡贡献，但 loss 函数完全相同。

训练数据混合：
- 图像生成：`<text caption> <image> image_tokens </image>`
- 图像感知：`<image> image_tokens </image> <question> text_tokens`
- 视频生成：`<text caption> <video> video_tokens </video>`
- 视频感知：同理。
- 纯文本：标准 NTP。

模型从数据分布里学会什么时候吐图像 token、什么时候吐文本 token。生成能力从模型在 `<image>` 标签之后预测图像 token 中涌现。

> Emu3 uses one objective: next-token prediction on a shared vocabulary across text tokens, 2D image tokens, and 3D video tokens. ... The model learns when to emit image tokens vs text tokens from the data distribution. Generation emerges from the model predicting image tokens after the `<image>` tag.

### Classifier-free guidance and temperature · CFG 与温度

自回归图像生成在推理时用 classifier-free guidance（CFG）会好非常多。Emu3 就用它：生成两次，一次带完整 caption，一次空 caption，按引导权重（典型 3.0-7.0）混合 logits。这是扩散模型同款的 CFG 技巧，被借到了自回归场景。

温度很关键：太高出伪影，太低模式坍缩。Emu3 推荐感知用 1.0，图像生成用 0.8。

> Autoregressive image generation gets much better with classifier-free guidance (CFG) at inference. Emu3 uses it: generate twice, once with the full caption, once with an empty caption, mix the logits with a guidance weight (typical 3.0-7.0). ... Temperature matters: too high, artifacts; too low, mode collapse. Emu3's recommended temperature is 1.0 for perception, 0.8 for image generation.

### Three roles, one model · 三个角色，一个模型

Emu3 以三个功能不同的 API 发布，但底层是同一套权重：

- Emu3-Gen。图像生成。输入文本，输出图像 token。
- Emu3-Chat。VQA 和 caption。输入图像（token），输出文本。
- Emu3-Stage2。视频生成和视频 VQA。输入文本或视频，输出文本或视频。

没有任务专用头。只是不同的 prompt 模板。同一个 checkpoint。

> Emu3 ships as three functionally distinct APIs but one underlying weight set: Emu3-Gen ... Emu3-Chat ... Emu3-Stage2 ... No task-specific heads. Just different prompt templates. Same checkpoint.

### Benchmarks · 基准

来自 Emu3 论文（2024 年 9 月）：

- 图像生成：MJHQ-30K FID 上赢 SDXL（5.4 vs 5.6），GenEval 总分（0.54 vs 0.55 —— 统计上的平手），Deep-Eval 综合分持平。
- 图像感知：VQAv2 上赢 LLaVA-1.6（75.1 vs 72.4），MMMU 大致持平。
- 视频生成：4 秒片段的质量，与 Sora 时期公开基准模型比，FVD 有竞争力。

这些数字并非处处赢 —— Emu3 这里丢一分、那里赚一分 —— 但「下一 token 预测就是全部所需」这个主张在所有模态上都站得住。

> From Emu3 paper (September 2024): image generation beats SDXL on MJHQ-30K FID (5.4 vs 5.6), GenEval overall (0.54 vs 0.55 — statistical tie) ... image perception beats LLaVA-1.6 on VQAv2 (75.1 vs 72.4) ... The numbers are not always winning — Emu3 trades a point here for a point there — but the claim "next-token prediction is all you need" is defensible across modalities.

### Compute cost · 算力成本

Emu3 用一个 7B 参数模型在约 3000 亿多模态 token 上训练。GPU 小时与 Llama-2-7B 预训练大致相当（A100 级硬件上 2k-4k GPU 年）。Stable Diffusion 3 这类扩散模型的训练预算类似，但需要单独的文本编码器和更复杂的流水线。

推理时 Emu3 每张图比 SDXL 慢：4096 个图像 token、30 tok/s，一张 512x512 图约 2 分钟，而 SDXL 只要 2-5 秒。投机解码和 KV cache 优化能缩小差距，但关不掉它。自回归图像生成本来就吃算力；这是长期存在的折中。

> Emu3 was trained on ~300 billion multimodal tokens with a 7B-parameter model. GPU-hours roughly comparable to Llama-2-7B pretraining (2k-4k GPU-years on A100-class silicon). ... At inference, Emu3 is slower than SDXL per image: 4096 image tokens at 30 tok/s is ~2 minutes per 512x512 image, vs 2-5 seconds for SDXL. ... Autoregressive image gen is compute-heavy; this is the standing trade-off.

### Why it matters · 为什么重要

Emu3 深层的贡献是概念性的。如果下一 token 预测能在图像生成上追平扩散，统一模型路线（一个 loss、一个骨干、任意模态）就成立。未来的模型不再需要单独的文本编码器、单独的扩散调度器、单独的 VAE。一个 transformer，每个模态一个分词器，然后堆规模。

Show-o、Janus-Pro、InternVL-U 都在继承或挑战这个论点。到 2025 年为止，中国实验室（BAAI、DeepSeek）在这个方向上的发表比美国实验室激进得多。

> Emu3's deep contribution is conceptual. If next-token prediction scales to match diffusion on image generation, the unified-model path (one loss, one backbone, any modality) is viable. Future models do not need separate text encoders, separate diffusion schedulers, separate VAEs. One transformer, one tokenizer per modality, scale. ... Show-o, Janus-Pro, and InternVL-U all build on or challenge this thesis.

```figure
l5-emu3-next-token
```

## Use It · 实战用法

`code/main.py` 搭两个玩具件：

- 一个 2D vs 3D VQ 分词器计数器：给定（分辨率、patch、片段长度、FPS），算图像 vs 视频的 token 数。
- 一个带 classifier-free guidance 和温度的自回归图像 token 采样器。

CFG 实现对齐 Emu3 的配方 —— 用引导权重混合条件与无条件 logits。

> `code/main.py` builds two toy pieces: a 2D vs 3D VQ tokenizer count calculator ... an autoregressive image-token sampler with classifier-free guidance at temperature. ... The CFG implementation matches Emu3's recipe — mix conditional and unconditional logits with a guidance weight.

## Ship It · 交付

本课产出 `outputs/skill-token-gen-cost-analyzer.md`。给定生成产品的规格（图像或视频、目标分辨率、质量档位、延迟预算），它计算 token 数和推理成本，并在 Emu3 家族与扩散之间做选择。

> This lesson produces `outputs/skill-token-gen-cost-analyzer.md`. Given a generation product spec (image or video, target resolution, quality tier, latency budget), it computes token counts, inference cost, and picks Emu3-family vs diffusion.

## Exercises · 练习

1. Emu3 在 8x8 压缩下每张 512x512 图产出 4096 个 token。算出 1024x1024 和 2048x2048 的对应值。推理延迟会怎样？

2. 读 Emu3 第 3.3 节视频分词器。描述 3D VQ patch 的形状，以及为什么是 4x4x4 而不是 8x8x1。

3. CFG 权重 5.0 vs 3.0：视觉效果有什么差别？在 `code/main.py` 里追一遍数学。

4. 算 Emu3-7B 在 300B token 上的训练 FLOPs，与 Stable Diffusion 3 比较。谁训起来更贵？

5. Emu3 在 FID 上赢 SDXL，但在 VQAv2 上赢不了专用 VLM。解释为什么统一 loss 路线在不同基准上对专才模型互有强弱。

> Emu3 produces 4096 tokens per 512x512 image at 8x8 reduction. Compute the equivalent for 1024x1024 and 2048x2048. What happens to inference latency? ... Classifier-free guidance weight 5.0 vs 3.0: what visual effect? Trace the math in `code/main.py`. ... Emu3 beats SDXL on FID but not on VQAv2 vs specialized VLMs. Explain why the unified-loss approach shows different strengths vs specialists on different benchmarks.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Next-token prediction | "NTP" | 标准自回归 loss：给定 token[0..i] 预测 token[i+1]；只要能 token 化，任何模态都适用 |
| IBQ tokenizer | "Inverse bottleneck quantizer" | 一类码本更大（32768+）、重建好于 Chameleon 的 VQ-VAE |
| 3D VQ | "时空量化器" | 码本按（时间、行、列）索引；一个 token 覆盖 4x4x4 像素立方 |
| Classifier-free guidance | "CFG" | 用权重 gamma 混合条件与无条件 logits；推理时提升图像质量 |
| Unified vocabulary | "共享 token" | 文本 + 图像 + 视频取自同一个整数空间；模型预测接下来出现的是哪个模态 |
| MJHQ-30K | "图像生成基准" | 3 万条 prompt 的 Midjourney 质感基准；Emu3 在这里报 FID |

## Further Reading · 延伸阅读

- [Wang et al. — Emu3: Next-Token Prediction is All You Need (arXiv:2409.18869)](https://arxiv.org/abs/2409.18869)
- [Sun et al. — Emu: Generative Pretraining in Multimodality (arXiv:2307.05222)](https://arxiv.org/abs/2307.05222)
- [Liu et al. — LWM (arXiv:2402.08268)](https://arxiv.org/abs/2402.08268)
- [Yu et al. — MAGVIT-v2 (arXiv:2310.05737)](https://arxiv.org/abs/2310.05737)
- [Tian et al. — VAR (arXiv:2404.02905)](https://arxiv.org/abs/2404.02905)
