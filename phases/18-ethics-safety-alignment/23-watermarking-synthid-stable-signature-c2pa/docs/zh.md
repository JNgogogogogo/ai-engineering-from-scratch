# Watermarking — SynthID, Stable Signature, C2PA · 水印：SynthID、Stable Signature 与 C2PA

> 三项技术构成 2026 年 AI 生成内容溯源（provenance）的骨架。SynthID（Google DeepMind）—— 图像水印 2023 年 8 月上线，文本+视频 2024 年 5 月（Gemini + Veo），文本 2024 年 10 月经 Responsible GenAI Toolkit 开源，2025 年 11 月随 Gemini 3 Pro 推出统一的多媒体检测器。文本水印以不可感知的方式调整 next-token 采样概率；图像/视频水印能在压缩、裁剪、滤镜、帧率变化后存活。Stable Signature（Fernandez et al., ICCV 2023, arXiv:2303.15435）—— 微调潜在扩散（latent diffusion）解码器，让每一份输出都携带一个固定消息；被裁剪到只剩 10% 内容的生成图像仍能在 FPR<1e-6 下达到 >90% 的检出率。后续研究「Stable Signature is Unstable」（arXiv:2405.07145，2024 年 5 月）—— 微调即可在保持质量的同时移除水印。C2PA —— 密码学签名、防篡改的元数据标准（C2PA 2.2 Explainer 2025）。水印与 C2PA 互补：元数据可以被剥离但携带更丰富的溯源信息；水印能在转码中留存但携带的信息更少。

> Three technologies structure 2026 AI-generated-content provenance. SynthID (Google DeepMind) — image watermarking launched August 2023, text+video May 2024 (Gemini + Veo), text open-sourced October 2024 via Responsible GenAI Toolkit, unified multi-media detector November 2025 alongside Gemini 3 Pro. Text watermarking adjusts next-token sampling probabilities imperceptibly; image/video watermarks survive compression, cropping, filters, frame-rate changes. Stable Signature (Fernandez et al., ICCV 2023, arXiv:2303.15435) — fine-tunes the latent diffusion decoder so every output contains a fixed message; cropped (10% of content) generated images detected >90% at FPR<1e-6. Follow-up "Stable Signature is Unstable" (arXiv:2405.07145, May 2024) — fine-tuning removes the watermark while preserving quality. C2PA — cryptographically signed, tamper-evident metadata standard (C2PA 2.2 Explainer 2025). Watermarking and C2PA are complementary: metadata can be stripped but carries richer provenance; watermarks persist through transcoding but carry less information.

**Type:** Build
**Languages:** Python (stdlib, token-watermark embed + detect)
**Prerequisites:** Phase 10 · 04 (sampling), Phase 01 · 09 (information theory)
**Time:** ~75 minutes

---

## Learning Objectives · 学习目标

- 描述 token 级水印（SynthID-text 风格）及其可被检测的机制。
- 描述 Stable Signature，以及 2024 年攻破它的移除攻击。
- 说出 C2PA 的角色，以及它为什么与水印互补。
- 描述关键局限：模型特异的信号、改写（paraphrase）下的鲁棒性，以及保义攻击（meaning-preserving attacks，arXiv:2508.20228）。

> Describe token-level watermarking (SynthID-text style) and the mechanism by which it is detectable.
> Describe Stable Signature and the 2024 removal attack that broke it.
> State C2PA's role and why it is complementary to watermarking.
> Describe the key limitations: model-specific signal, robustness under paraphrase, and meaning-preserving attacks (arXiv:2508.20228).

---

## The Problem · 问题在哪

2023-2024 年，deepfake 与 AI 生成内容大规模进入政治和消费场景。水印是被提出的技术性溯源信号：在生成时刻打上标记，事后再检测。2025 年的证据：没有哪种水印是无条件鲁棒的，但与 C2PA 元数据分层叠加之后，这一组合能提供一个可用的溯源方案。

> 2023-2024 saw deepfakes and AI-generated content enter political and consumer contexts at scale. Watermarking is the proposed technical provenance signal: mark generations at creation time, detect them later. 2025 evidence: no watermark is unconditionally robust, but layered with C2PA metadata the combination provides a usable provenance story.

---

## The Concept · 概念

### Text watermarking (SynthID-text style) · 文本水印（SynthID-text 风格）

Kirchenbauer et al. 2023 的机制，由 Google 产品化：

1. 在每个解码步，对前 K 个 token 做哈希，把词表伪随机地划分为「绿集」和「红集」。
2. 给绿集的 logit 加上 δ，让采样偏向绿集。
3. 生成文本中绿 token 的数量会超过随机水平。

检测：对每个前缀重新哈希，统计生成文本中的绿 token 数，计算 z-score。带水印文本的 z-score 显著大于 0，人类文本约为 0。

性质：
- 对读者不可感知（δ 足够小，质量损失轻微）。
- 只要拿到词表划分函数就能检测。
- 对改写不鲁棒 —— 重写文本会破坏信号。

SynthID-text 于 2024 年 10 月经 Google 的 Responsible GenAI Toolkit 开源。

> The Kirchenbauer et al. 2023 mechanism, productionized by Google: at each decoding step, hash the previous K tokens to produce a pseudorandom partition of the vocabulary into "green" and "red" sets; bias sampling toward the green set by adding δ to green logits; the generation contains more green tokens than chance would produce.
> Detection: rehash each prefix, count green tokens in the generation, compute a z-score. The z-score is >0 for watermarked text, ~0 for human text.
> Properties: imperceptible to readers (δ is small enough that quality loss is minor); detectable with access to the vocabulary partition function; not robust to paraphrase — rewriting the text destroys the signal.
> SynthID-text is open-sourced October 2024 via Google's Responsible GenAI Toolkit.

### Stable Signature (image) · Stable Signature（图像）

Fernandez et al.，ICCV 2023。微调潜在扩散解码器，让每张生成图像都在潜在表示中嵌入一个固定的二进制消息。检测由神经解码器从潜在表示中解码得出。被裁剪到只剩 10% 内容的图像仍能在 FPR<1e-6 下达到 >90% 的检出率。

2024 年 5 月的「Stable Signature is Unstable」（arXiv:2405.07145）：微调解码器即可在保持图像质量的同时移除水印。生成后的对抗性微调很便宜；这个水印的对抗鲁棒性有限。

> Fernandez et al. ICCV 2023. Fine-tune the latent diffusion decoder so every generated image contains a fixed binary message embedded in the latent representation. Detection is decoded from the latent with a neural decoder. Cropped (to 10% of content) images detected >90% at FPR<1e-6.
> May 2024 "Stable Signature is Unstable" (arXiv:2405.07145): fine-tuning the decoder removes the watermark while preserving image quality. Adversarial post-generation fine-tuning is cheap; the watermark's adversarial robustness is limited.

### SynthID unified detector (November 2025) · SynthID 统一检测器（2025 年 11 月）

随 Gemini 3 Pro 一起发布：一个多媒体检测器，通过同一个 API 读取文本、图像、音频和视频中的 SynthID 信号。它把 Google 的溯源技术栈统一了起来。

> Alongside Gemini 3 Pro: a multi-media detector that reads SynthID signals from text, image, audio, and video in one API. Unifies the Google provenance stack.

### C2PA

C2PA（Coalition for Content Provenance and Authenticity，内容来源与真实性联盟）。密码学签名、防篡改的元数据标准。见 C2PA 2.2 Explainer（2025）。一份 C2PA manifest 记录由创建者密钥签名的溯源声明（谁创建、何时创建、做过哪些变换）。

与水印互补：
- 元数据可以被剥离；水印（轻易）剥离不掉。
- 元数据信息丰富（完整溯源链）；水印只携带几个比特。
- C2PA 依赖平台采纳；水印自动嵌入。

Google 在 Search、Ads 和「About this image」中同时集成了两者。

> Coalition for Content Provenance and Authenticity. Cryptographically signed tamper-evident metadata standard. C2PA 2.2 Explainer (2025). A C2PA manifest records provenance claims (who created, when, what transformations) signed by the creator's key.
> Complementary to watermarking: metadata can be stripped; watermarks cannot (easily). Metadata is rich (full provenance chain); watermarks carry bits. C2PA depends on platform adoption; watermarks embed automatically.
> Google integrates both in Search, Ads, and "About this image."

### Limitations · 局限

- **模型特异。** SynthID 只给启用了 SynthID 的模型的生成物打水印。来自没有 SynthID 的模型的生成物没有水印，所以「没有 SynthID 信号」并不能证明内容是真实的。
- **改写。** 文本水印无法在保义改写之后存活。
- **变换攻击。** arXiv:2508.20228（2025）展示了能同时摧毁文本水印和许多图像水印的保义攻击。
- **微调移除。** 如「Stable Signature is Unstable」所示，生成后微调会移除已嵌入的水印。

> **Model-specific.** SynthID watermarks generations from SynthID-enabled models. A generation from a model without SynthID is not watermarked, so "no SynthID signal" is not proof of authenticity.
> **Paraphrase.** Text watermarks do not survive meaning-preserving paraphrase.
> **Transformation attacks.** arXiv:2508.20228 (2025) shows meaning-preserving attacks that destroy both text watermarks and many image watermarks.
> **Fine-tune removal.** Per "Stable Signature is Unstable," post-generation fine-tuning removes embedded watermarks.

### EU AI Act Article 50 · EU AI Act 第 50 条

AI 生成内容标注的透明度准则（Transparency Code）（第一稿 2025 年 12 月，第二稿 2026 年 3 月，按[欧盟委员会状态页](https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content)预计 2026 年 6 月定稿）。截至 2026 年 4 月，该准则仍处于草案阶段，时间表可能变化。这是要求技术层的那个监管层。Deepfake 必须被标注。

> Transparency Code for AI-generated content labeling (first draft December 2025, second draft March 2026, expected final June 2026 per the [European Commission status page](https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content)). The Code remains in draft as of April 2026 and the timeline is subject to change. The regulatory layer that requires the technical layer. Deepfakes must be labeled.

### Where this fits in Phase 18 · 在 Phase 18 中的位置

第 22-23 课讲的是模型发出什么（私密数据、来源信号）。第 27 课讲训练数据治理。第 24 课是要求这些技术措施的监管框架。

```figure
an-watermark-greenlist
```

---

## Use It · 实战用法

`code/main.py` 构建一个玩具文本水印。token 是 0..N-1 的整数；带水印的采样会偏向由哈希定义的绿集。检测器计算绿 token 的 z-score。你可以观察对 1000-token 生成文本的检测、看着改写摧毁信号，并测量在人类文本上的假阳性率。

> `code/main.py` builds a toy text watermark. Tokens are integers 0..N-1; watermarked sampling biases toward the hash-defined green set. A detector computes the green-token z-score. You can observe detection at 1000-token generations, watch paraphrase destroy the signal, and measure the false-positive rate on human text.

---

## Ship It · 交付

本课产出 `outputs/skill-provenance-audit.md`。给定一个带溯源主张的内容部署，它会审计：水印机制（如有）、C2PA 签名链（如有）、两者的对抗鲁棒性，以及各模态的覆盖范围。

> This lesson produces `outputs/skill-provenance-audit.md`. Given a content deployment with a provenance claim, it audits: the watermark mechanism (if any), the C2PA signing chain (if any), the adversarial robustness of each, and the per-modality coverage.

---

## Exercises · 练习

1. 运行 `code/main.py`。报告带水印的 1000-token 生成文本与人类撰写文本的 z-score。找出 95% 置信阈值处的假阳性率。

2. 实现一个把 30% 的 token 替换为同义词的改写攻击。重新测量 z-score。

3. 阅读 Kirchenbauer et al. 2023 第 6 节关于鲁棒性的内容。为什么文本水印在改写下失效，而图像水印能在裁剪后存活？

4. 设计一个同时使用 SynthID-text + C2PA 元数据的部署。描述消费者看到的溯源链。指出每个组件的一个失效模式。

5. 2024 年的「Stable Signature is Unstable」结果表明微调会移除图像水印。设计一个限制此攻击的部署控制 —— 例如要求对微调后的检查点做签名发布。

> 1. Run `code/main.py`. Report z-scores for watermarked 1000-token generation vs human-authored text. Identify the false-positive rate at the 95% confidence threshold.
> 2. Implement a paraphrase attack that replaces 30% of tokens with synonyms. Re-measure the z-score.
> 3. Read Kirchenbauer et al. 2023 Section 6 on robustness. Why do text watermarks fail under paraphrase but image watermarks survive cropping?
> 4. Design a deployment that uses SynthID-text + C2PA metadata. Describe the provenance chain a consumer sees. Identify one failure mode of each component.
> 5. The 2024 "Stable Signature is Unstable" result shows fine-tuning removes the image watermark. Design a deployment control that limits this attack — for example, require signed releases of fine-tuned checkpoints.

---

## Key Terms · 术语表

| 术语 | 大家常说 | 实际含义 |
|------|-----------------|------------------------|
| SynthID | 「Google 的水印」 | 跨模态来源信号；文本、图像、音频、视频 |
| Token watermark | 「Kirchenbauer 风格」 | 通过绿 token z-score 检测的偏置采样文本水印 |
| Stable Signature | 「图像水印」 | 微调解码器实现的水印；ICCV 2023 |
| C2PA | 「那个元数据标准」 | 密码学签名、防篡改的溯源元数据 |
| Paraphrase robustness | 「换个说法会不会破坏它」 | 文本水印的性质；目前很有限 |
| Fine-tune removal | 「对抗性去水印」 | 通过解码器微调移除图像水印的攻击 |
| Cross-modal detector | 「统一的 SynthID」 | 2025 年 11 月推出的跨模态统一 API |

---

## Further Reading · 延伸阅读

- [Kirchenbauer et al. — A Watermark for Large Language Models (ICML 2023, arXiv:2301.10226)](https://arxiv.org/abs/2301.10226) —— token 水印机制
- [Fernandez et al. — Stable Signature (ICCV 2023, arXiv:2303.15435)](https://arxiv.org/abs/2303.15435) —— 图像水印论文
- ["Stable Signature is Unstable" (arXiv:2405.07145)](https://arxiv.org/abs/2405.07145) —— 那个移除攻击
- [Google DeepMind — SynthID](https://deepmind.google/models/synthid/) —— 跨模态水印
- [C2PA 2.2 Explainer (2025)](https://c2pa.org/specifications/specifications/2.2/explainer/Explainer.html) —— 元数据标准
