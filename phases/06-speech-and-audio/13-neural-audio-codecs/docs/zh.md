# Neural Audio Codecs — EnCodec, SNAC, Mimi, DAC and the Semantic-Acoustic Split · 神经音频编解码器——EnCodec、SNAC、Mimi、DAC 与语义-声学分离

> 2026 年的音频生成几乎全是 token。EnCodec、SNAC、Mimi 和 DAC 把连续波形变成 transformer 能预测的离散序列。「语义 vs 声学」的 token 分离——第一个 codebook 管语义、其余管声学——是音频领域自 Transformer 以来最重要的架构变革。
>
> 2026 audio generation is almost all tokens. EnCodec, SNAC, Mimi, and DAC turn continuous waveforms into discrete sequences that a transformer can predict. The semantic-vs-acoustic token split — first-codebook as semantic, rest as acoustic — is the most important architectural shift since the Transformer for audio.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 6 · 02 (Spectrograms), Phase 10 · 11 (Quantization), Phase 5 · 19 (Subword Tokenization)
**Time:** ~60 minutes

---

## The Problem · 问题在哪

语言模型处理的是离散 token，而音频是连续的。如果你想要一个 LLM 风格的语音 / 音乐模型——MusicGen、Moshi、Sesame CSM、VibeVoice、Orpheus——首先需要一个**神经音频编解码器（neural audio codec）**：一个学习得到的编码器，把音频离散化成一个小词表的 token，外加一个配对的解码器，把 token 还原成波形。

涌现出两大家族：

1. **重建优先（reconstruction-first）编解码器** —— EnCodec、DAC。优化感知音频质量。token 是「声学的」——它们捕获一切，包括说话人身份、音色、背景噪声。
2. **语义优先（semantic-first）编解码器** —— Mimi（Kyutai）、SpeechTokenizer。强制第一个 codebook 编码语言学 / 语音学内容（通常从 WavLM 蒸馏）。后续 codebook 承载声学细节。

2024-2026 年的洞见：**纯重建编解码器在你试图从文本生成时只能给出含糊的语音。** 基于 codec token 的 LLM 必须在同一个 codebook 里同时学会语言结构和声学结构，这无法规模化。把它们分开——语义 codebook 0，声学 codebook 1-N——正是 Moshi 和 Sesame CSM 能工作的原因。

> Language models work on discrete tokens. Audio is continuous. If you want an LLM-style model for speech / music — MusicGen, Moshi, Sesame CSM, VibeVoice, Orpheus — you first need a **neural audio codec**: a learned encoder that discretizes audio into a small vocabulary of tokens, and a matching decoder that reconstructs the waveform.
> The 2024-2026 insight: **a pure reconstruction codec gives you blurry speech when you try to generate from text.** The LLM over codec tokens has to learn both language structure AND acoustic structure in the same codebook, which doesn't scale. ... Separating them — semantic codebook 0, acoustic codebooks 1-N — is what makes Moshi and Sesame CSM work.

---

## The Concept · 概念

![四种编解码器全景：EnCodec、DAC、SNAC（多尺度）、Mimi（语义+声学）](../assets/codec-comparison.svg)

### The core trick: Residual Vector Quantization (RVQ) · 核心技巧：残差向量量化（RVQ）

与其用一个大 codebook（好质量需要数百万个码字），所有现代音频编解码器都用 **RVQ（residual vector quantization，残差向量量化）**：一串小 codebook 的级联。第一个 codebook 量化编码器输出；第二个量化残差；依此类推。每个 codebook 有 1024 个码字。8 个 codebook = 1024^8 = 10^24 的等效词表。

推理时，解码器把每帧选中的所有码字求和来重建。

> Rather than one big codebook (which would need millions of codes for good quality), all modern audio codecs use **RVQ**: a cascade of small codebooks. The first codebook quantizes the encoder output; the second quantizes the residual; etc. Each codebook is 1024 codes. 8 codebooks = effective vocabulary of 1024^8 = 10^24.
> At inference time, the decoder sums all chosen codes per frame to reconstruct.

---

### The four codecs that matter in 2026 · 2026 年举足轻重的四个编解码器

**EnCodec（Meta，2022）。** 基线。波形上的编码器-解码器 + RVQ 瓶颈。24 kHz，最多可 32 个 codebook，默认 4 个 codebook @ 1.5 kbps。采用 `1D conv + transformer + 1D conv` 架构。MusicGen 用的就是它。

**DAC（Descript，2023）。** 带L2 归一化 codebook 的 RVQ、周期激活函数、改进的损失。所有开源编解码器里重建保真度最高——12 个 codebook 时有时与原始语音难以区分。44.1 kHz 全频带。

**SNAC（Hubert Siuzdak，2024）。** 多尺度 RVQ——粗 codebook 的帧率比细 codebook 低。实质上按层级建模音频：~12 Hz 的粗「草图」加上 50 Hz 的细节。Orpheus-3B 使用它，因为这种层级结构能很好地映射到基于 LM 的生成。

**Mimi（Kyutai，2024）。** 2026 年的游戏规则改变者。12.5 Hz 帧率（极低），8 个 codebook @ 4.4 kbps。Codebook 0 **从 WavLM 蒸馏**——训练目标是预测 WavLM 的语音内容特征。Codebook 1-7 是声学残差。这一分离支撑了 Moshi（第 15 课）和 Sesame CSM。

> **EnCodec (Meta, 2022).** The baseline. Encoder-decoder over waveform, RVQ bottleneck. 24 kHz, 32 codebooks possible, default 4 codebooks @ 1.5 kbps. ... Used by MusicGen.
> **DAC (Descript, 2023).** RVQ with L2-normalized codebooks, periodic activation functions, improved losses. Highest reconstruction fidelity of any open codec — sometimes indistinguishable from original speech with 12 codebooks. 44.1 kHz full-band.
> **SNAC (Hubert Siuzdak, 2024).** Multi-scale RVQ — the coarse codebooks operate at a lower frame rate than fine ones. ... Used by Orpheus-3B because the hierarchical structure maps well onto LM-based generation.
> **Mimi (Kyutai, 2024).** The 2026 game-changer. 12.5 Hz frame rate (extremely low), 8 codebooks @ 4.4 kbps. Codebook 0 is **distilled from WavLM** — trained to predict WavLM's speech-content features. Codebooks 1-7 are acoustic residuals. This split powers Moshi (Lesson 15) and Sesame CSM.

---

### Frame rates matter for language modeling · 帧率决定语言建模的成败

帧率越低 = 序列越短 = LM 越快。

| 编解码器 | 帧率 | 1 秒 = N 帧 | 适用场景 |
|-------|-----------|----------------|---------|
| EnCodec-24k | 75 Hz | 75 | 音乐、通用音频 |
| DAC-44.1k | 86 Hz | 86 | 高保真音乐 |
| SNAC-24k（粗） | ~12 Hz | 12 | 对 AR-LM 高效 |
| Mimi | 12.5 Hz | 12.5 | 流式语音 |

12.5 Hz 下，10 秒语音只有 125 个 codec 帧——transformer 轻松就能预测它们。

> Lower frame rate = shorter sequence = faster LM.
> At 12.5 Hz, a 10-second utterance is only 125 codec frames — a transformer can easily predict them.

---

### Semantic vs acoustic tokens · 语义 token 与声学 token

```
frame_t → [semantic_token_t, acoustic_token_0_t, acoustic_token_1_t, ..., acoustic_token_6_t]
```

- **语义 token（Mimi 的 codebook 0）。** 编码说了什么——音素、词、内容。通过辅助预测损失从 WavLM 蒸馏。
- **声学 token（codebook 1-7）。** 编码音色、说话人身份、韵律、背景噪声、细节。

AR LM 先预测语义 token（以文本为条件），再预测声学 token（以语义 + 说话人参考为条件）。正是这个因子分解让现代 TTS 能零样本克隆声音：语义模型管内容，声学模型管音色。

> **Semantic token (codebook 0 in Mimi).** Encodes what was said — phonemes, words, content. Distilled from WavLM via an auxiliary prediction loss.
> **Acoustic tokens (codebooks 1-7).** Encode timbre, speaker identity, prosody, background noise, fine detail.
> An AR LM predicts the semantic token first (conditioned on text), then predicts acoustic tokens (conditioned on semantic + speaker reference). This factorization is why modern TTS can zero-shot-clone voices: the semantic model handles content; the acoustic model handles timbre.

---

### 2026 reconstruction quality (bits per sec, lower bitrate is better) · 2026 年重建质量（比特每秒，码率越低越好）

| 编解码器 | 码率 | PESQ | ViSQOL |
|-------|---------|------|--------|
| Opus-20kbps | 20 kbps | 4.0 | 4.3 |
| EnCodec-6kbps | 6 kbps | 3.2 | 3.8 |
| DAC-6kbps | 6 kbps | 3.5 | 4.0 |
| SNAC-3kbps | 3 kbps | 3.3 | 3.8 |
| Mimi-4.4kbps | 4.4 kbps | 3.1 | 3.7 |

Opus 这样的传统编解码器在每比特感知质量上仍然赢。神经编解码器赢在**离散 token**（Opus 不产生这东西）和**生成模型质量**（LM 拿这些 token 能做什么）。

> Traditional codecs like Opus still win per bit on perceptual quality. Neural codecs win on **discrete tokens** (which Opus does not produce) and **generative-model quality** (what the LM can do with those tokens).

```figure
rvq-codec-cascade
```

---

## Build It · 动手造

### Step 1: encode with EnCodec · 用 EnCodec 编码

```python
from encodec import EncodecModel
import torch

model = EncodecModel.encodec_model_24khz()
model.set_target_bandwidth(6.0)  # kbps

wav = torch.randn(1, 1, 24000)
with torch.no_grad():
    encoded = model.encode(wav)
codes, scale = encoded[0]
# codes: (1, n_codebooks, n_frames), dtype=int64
```

6 kbps 下 `n_codebooks=8`。每个码是 0-1023（10 bit）。

> `n_codebooks=8` at 6 kbps. Each code is 0-1023 (10-bit).

### Step 2: decode and measure reconstruction · 解码并测量重建

```python
with torch.no_grad():
    wav_recon = model.decode([(codes, scale)])

from torchaudio.functional import compute_deltas
import torch.nn.functional as F

mse = F.mse_loss(wav_recon[:, :, :wav.shape[-1]], wav).item()
```

### Step 3: the semantic-acoustic split (Mimi-style) · 语义-声学分离（Mimi 风格）

```python
from moshi.models import loaders
mimi = loaders.get_mimi()

with torch.no_grad():
    codes = mimi.encode(wav)  # shape (1, 8, frames@12.5Hz)

semantic = codes[:, 0]
acoustic = codes[:, 1:]
```

语义 codebook 0 与 WavLM 对齐。你可以训练一个 text-to-semantic transformer——词表比直接生成音频小得多。然后用一个单独的 acoustic-to-waveform 解码器，以说话人参考为条件。

> Semantic codebook 0 is WavLM-aligned. You can train a text-to-semantic transformer — much smaller vocabulary than going direct-to-audio. Then a separate acoustic-to-waveform decoder conditions on a speaker reference.

### Step 4: why AR LM over codec tokens works · 为什么基于 codec token 的 AR LM 行得通

按 Mimi 的 12.5 Hz × 8 codebooks 算一段 10 秒语音：

```
N_tokens = 10 * 12.5 * 8 = 1000 tokens
```

1000 个 token 对 transformer 来说是微不足道的上下文。一个 2.56 亿参数的 transformer 能在现代 GPU 上毫秒级生成 10 秒语音。

> For a 10 s speech clip at Mimi's 12.5 Hz × 8 codebooks: 1000 tokens is a trivial context for a transformer. A 256M-parameter transformer can generate 10 seconds of speech in milliseconds on a modern GPU.

---

## Use It · 实战用法

把问题映射到编解码器：

| 任务 | 编解码器 |
|------|-------|
| 通用音乐生成 | EnCodec-24k |
| 最高保真重建 | DAC-44.1k |
| 语音上的 AR LM（TTS） | SNAC 或 Mimi |
| 流式全双工语音 | Mimi（12.5 Hz） |
| 带文本条件的音效库 | EnCodec + T5 条件 |
| 细粒度音频编辑 | DAC + inpainting |

经验法则：**如果你在构建生成式模型，从 Mimi 或 SNAC 开始。如果你在构建压缩流水线，用 Opus。**

> Rule of thumb: **if you're building a generative model, start with Mimi or SNAC. If you're building a compression pipeline, use Opus.**

---

## Pitfalls · 常见的坑

- **Codebook 太多。** 加 codebook 让保真度线性提升，但 LM 序列长度也线性变长。停在 8-12 个。
- **帧率不匹配。** 在 12.5 Hz Mimi 上训练 LM，再到 50 Hz EnCodec 上微调，会无声地失败。
- **假设所有 codebook 平等。** 在 Mimi 里，codebook 0 承载内容；丢掉它可懂度就被摧毁。丢掉 codebook 7 几乎无感。
- **把重建质量当唯一指标。** 一个编解码器可能重建很棒，但只要语义结构不好，对基于 LM 的生成就毫无用处。

> **Too many codebooks.** Adding codebooks increases fidelity linearly but LM sequence length linearly too. Stop at 8-12.
> **Frame-rate mismatch.** Training LM on 12.5 Hz Mimi then fine-tuning on 50 Hz EnCodec fails silently.
> **Assuming all codebooks equal.** In Mimi, codebook 0 carries content; losing it destroys intelligibility. Losing codebook 7 is barely noticeable.
> **Using reconstruction quality as the only metric.** A codec can have great reconstruction but be useless for LM-based generation if the semantic structure is bad.

---

## Ship It · 交付

保存为 `outputs/skill-codec-picker.md`：为给定的生成或压缩任务挑选编解码器。

> Save as `outputs/skill-codec-picker.md`. Pick a codec for a given generative or compression task.

---

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。它实现了一个玩具级的标量 + 残差量化器，并测量每加一个 codebook 时的重建误差。
2. **中等。** 安装 `encodec`，在一段留出的语音上对比 1、4、8、32 个 codebook。画出 PESQ 或 MSE 对码率的曲线。
3. **困难。** 加载 Mimi，编码一段音频。把 codebook 0 换成随机整数再解码；然后用同样方式换掉 codebook 7。对比两种破坏——codebook 0 的破坏应该摧毁可懂度；codebook 7 的破坏应该几乎无变化。

> 1. **Easy.** Run `code/main.py`. It implements a toy scalar + residual quantizer and measures reconstruction error as you add codebooks.
> 2. **Medium.** Install `encodec` and compare 1, 4, 8, 32 codebooks on a held-out speech clip. Plot PESQ or MSE vs bitrate.
> 3. **Hard.** Load Mimi. Encode a clip. Replace codebook 0 with random integers; decode. Then replace codebook 7 similarly. Compare the two corruptions — codebook 0 corruption should destroy intelligibility; codebook 7 corruption should barely change anything.

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| RVQ | 残差量化 | 一串小 codebook 的级联；每个量化前一级的残差。 |
| Frame rate（帧率） | 编解码器速度 | 每秒多少个 token 帧。越低 LM 越快。 |
| Semantic codebook（语义 codebook） | Codebook 0（Mimi） | 从 SSL 特征蒸馏出来的 codebook；编码内容。 |
| Acoustic codebooks（声学 codebook） | 其余全部 | 音色、韵律、噪声、细节。 |
| PESQ / ViSQOL | 感知质量 | 与 MOS 相关的客观指标。 |
| EnCodec | Meta 编解码器 | RVQ 基线；MusicGen 使用。 |
| Mimi | Kyutai 编解码器 | 12.5 Hz 帧率；语义-声学分离；驱动 Moshi。 |

---

## Further Reading · 延伸阅读

- [Défossez et al. (2023). EnCodec](https://arxiv.org/abs/2210.13438) —— RVQ 基线。
- [Kumar et al. (2023). Descript Audio Codec (DAC)](https://arxiv.org/abs/2306.06546) —— 开源中保真度最高。
- [Siuzdak (2024). SNAC](https://arxiv.org/abs/2410.14411) —— 多尺度 RVQ。
- [Kyutai (2024). Mimi codec](https://kyutai.org/codec-explainer) —— 语义-声学分离、WavLM 蒸馏。
- [Borsos et al. (2023). AudioLM](https://arxiv.org/abs/2209.03143) —— 两阶段语义/声学范式。
- [Zeghidour et al. (2021). SoundStream](https://arxiv.org/abs/2107.03312) —— 最早的流式 RVQ 编解码器。
