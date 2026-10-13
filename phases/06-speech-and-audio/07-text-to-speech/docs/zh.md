# Text-to-Speech (TTS) — From Tacotron to F5 and Kokoro · 文本转语音——从 Tacotron 到 F5 与 Kokoro

> ASR inverts speech to text; TTS inverts text to speech. The 2026 stack is three parts: text → tokens, tokens → mel, mel → waveform. Each part has a default model that fits in a laptop.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 6 · 02 (Spectrograms & Mel), Phase 5 · 09 (Seq2Seq), Phase 7 · 05 (Full Transformer)
**Time:** ~75 minutes

---

## The Problem · 问题在哪

你手上有一个字符串："Please remind me to water the plants at 6 pm." 你需要一段 3 秒的音频：听起来自然、韵律（prosody，停顿与重音）正确、把 "plants" 的元音发对，还要在 CPU 上 300 ms 内出声，供实时语音助手使用。你还得能切换音色、处理语码转换（code-switched）的输入（"remind me at 6 pm, daijoubu?"），并且别在人名上出丑。

现代文本转语音（TTS）流水线长这样：

1. **文本前端（text frontend）。** 归一化文本（日期、数字、邮箱），转成音素（phoneme）或子词（subword）token，预测韵律特征。
2. **声学模型（acoustic model）。** 文本 → 梅尔频谱图（mel spectrogram）。Tacotron 2（2017）、FastSpeech 2（2020）、VITS（2021）、F5-TTS（2024）、Kokoro（2024）。
3. **声码器（vocoder）。** 梅尔谱 → 波形（waveform）。WaveNet（2016）、WaveRNN、HiFi-GAN（2020）、BigVGAN（2022）、2024 年以后的神经编解码（neural codec）声码器。

2026 年，随着端到端扩散模型与 flow-matching 模型的兴起，「声学模型 + 声码器」的分界正在模糊。但调试时，三段式的心智模型依然成立。

> You have a string: "Please remind me to water the plants at 6 pm." You need a 3-second audio clip that sounds natural, has correct prosody (pauses, stress), pronounces "plants" with the right vowel, and runs in under 300 ms on a CPU for a live voice assistant. You also need to swap voices, handle code-switched input ("remind me at 6 pm, daijoubu?"), and not embarrass yourself on names.
> Modern TTS pipelines look like this:
> In 2026 the acoustic + vocoder split blurs with end-to-end diffusion and flow-matching models. But the mental model of three parts still holds for debugging.

---

## The Concept · 概念

![Tacotron、FastSpeech、VITS、F5/Kokoro 并排对比](../assets/tts.svg)

**Tacotron 2（2017）。** Seq2seq：字符 embedding → BiLSTM 编码器 → 位置敏感注意力（location-sensitive attention）→ 自回归（autoregressive）LSTM 解码器逐帧输出梅尔谱。慢（自回归），长文本上会抖。如今仍被当作 baseline 引用。

**FastSpeech 2（2020）。** 非自回归。时长预测器（duration predictor）输出每个音素该拿多少帧梅尔谱。一次前向，比 Tacotron 快 10 倍。牺牲了一点自然度（单调对齐），但部署无处不在。

**VITS（2021）。** 用变分推断端到端联合训练编码器 + 基于流的时长模块 + HiFi-GAN 声码器。单模型、高质量。2022–2024 年开源 TTS 的霸主。变体：YourTTS（多说话人 zero-shot）、XTTS v2（2024，Coqui）。

**F5-TTS（2024）。** 构建在 flow matching 之上的扩散 Transformer。韵律自然，只需 5 秒参考音频即可 zero-shot 声音克隆（voice cloning）。2026 年开源 TTS 排行榜第一。335M 参数。

**Kokoro（2024）。** 小（82M）、CPU 可跑、实时使用下最强一档的英文 TTS。封闭词表、仅英文，apache-2.0。

**OpenAI TTS-1-HD、ElevenLabs v2.5、Google Chirp-3。** 商业 SOTA。ElevenLabs v2.5 的情绪标签（"[whispered]"、"[laughing]"）与角色音色在 2026 年的有声书制作中占主导地位。

> **Tacotron 2 (2017).** Seq2seq: char-embedding → BiLSTM encoder → location-sensitive attention → autoregressive LSTM decoder emits mel frames. ... **FastSpeech 2 (2020).** Non-autoregressive. Duration predictor outputs how many mel frames each phoneme gets. ... **VITS (2021).** Jointly trains encoder + flow-based duration + HiFi-GAN vocoder end-to-end with variational inference. ... **F5-TTS (2024).** Diffusion transformer over flow matching. Natural prosody, zero-shot voice cloning with 5 seconds of reference audio. Top of the 2026 open-source TTS leaderboards. ... **Kokoro (2024).** Small (82M), CPU-runnable, best-in-class English TTS for real-time use.

---

### Vocoder evolution · 声码器的演进

| 年代 | 声码器 | 延迟 | 质量 |
|-----|---------|---------|---------|
| 2016 | WaveNet | 仅限离线 | 发布时的 SOTA |
| 2018 | WaveRNN | 接近实时 | 良好 |
| 2020 | HiFi-GAN | 100 倍实时 | 接近真人 |
| 2022 | BigVGAN | 50 倍实时 | 跨说话人/语言泛化 |
| 2024 | SNAC、DAC（神经编解码） | 与 AR 模型集成 | 离散 token、比特效率高 |

到 2026 年，大多数「TTS」模型已经从文本端到端直出波形；梅尔频谱图只是内部表示。

> By 2026 most "TTS" models are end-to-end from text to waveform; the mel spectrogram is an internal representation.

---

### Evaluation · 评测方法

- **MOS（Mean Opinion Score，平均意见分）。** 1–5 分制，众包打分。仍是黄金标准，但慢得痛苦。
- **CMOS（Comparative MOS）。** A 对 B 的偏好比较。同样多的标注能得到更紧的置信区间。
- **UTMOS、DNSMOS。** 无参考（reference-free）的神经 MOS 预测器。排行榜用它们。
- **CER（Character Error Rate，字错误率），经 ASR 计算。** 把 TTS 输出跑一遍 Whisper，对输入文本算 CER。可懂度的代理指标。
- **SECS（Speaker Embedding Cosine Similarity，说话人嵌入余弦相似度）。** 衡量声音克隆质量。

2026 年在 LibriTTS test-clean 上的数字：

| 模型 | UTMOS | CER（经 Whisper） | 规模 |
|-------|-------|-------------------|------|
| 真实录音（ground truth） | 4.08 | 1.2% | — |
| F5-TTS | 3.95 | 2.1% | 335M |
| XTTS v2 | 3.81 | 3.5% | 470M |
| VITS | 3.62 | 3.1% | 25M |
| Kokoro v0.19 | 3.87 | 1.8% | 82M |
| Parler-TTS Large | 3.76 | 2.8% | 2.3B |

```figure
sp-tts-stack
```

> **MOS (Mean Opinion Score).** 1–5 scale, crowd-sourced. Still the gold standard; painfully slow.
> **UTMOS, DNSMOS.** Reference-free neural MOS predictors. Used for leaderboards.
> **CER (Character Error Rate) via ASR.** Run TTS output through Whisper, compute CER against the input text. Proxy for intelligibility.
> **SECS (Speaker Embedding Cosine Similarity).** Voice-cloning quality.

---

## Build It · 动手造

### Step 1: phonemize input · 音素化输入

```python
from phonemizer import phonemize
ph = phonemize("Hello world", language="en-us", backend="espeak")
# 'həloʊ wɜːld'
```

音素是通用桥梁。任何低于 VITS 水平的模型，都别直接喂原始文本。

> Phonemes are the universal bridge. Avoid feeding raw text to anything below VITS-level quality.

### Step 2: run Kokoro (2026 CPU default) · 跑 Kokoro（2026 年的 CPU 默认之选）

```python
from kokoro import KPipeline
tts = KPipeline(lang_code="a")  # "a" = American English
audio, sr = tts("Please remind me to water the plants at 6 pm.", voice="af_bella")
# audio: float32 tensor, sr=24000
```

离线可跑、单文件、82M 参数。

> Runs offline, single file, 82M params.

### Step 3: run F5-TTS with voice cloning · 用 F5-TTS 做声音克隆

```python
from f5_tts.api import F5TTS
tts = F5TTS()
wav = tts.infer(
    ref_file="my_voice_5s.wav",
    ref_text="The quick brown fox jumps over the lazy dog.",
    gen_text="Please remind me to water the plants.",
)
```

传入 5 秒参考片段 + 它的转写文本；F5 会克隆韵律和音色。

> Pass a 5-second reference clip + its transcript; F5 clones prosody and timbre.

### Step 4: HiFi-GAN vocoder from scratch · 从零实现 HiFi-GAN 声码器

太大，塞不进一篇教程脚本，但形状是这样：

```python
class HiFiGAN(nn.Module):
    def __init__(self, mel_channels=80, upsample_rates=[8, 8, 2, 2]):
        super().__init__()
        # 4 upsample blocks, total 256x to go from mel-rate to audio-rate
        ...
    def forward(self, mel):
        return self.blocks(mel)  # -> waveform
```

训练：对抗训练（在短窗口上跑判别器）+ 梅尔谱重建损失 + 特征匹配损失。这条路线已经完全商品化——直接用 `hifi-gan` 仓库或 NVIDIA NeMo 的预训练权重。

> Too big to fit in a tutorial script, but the shape is:
> Training: adversarial (discriminator on short windows) + mel-spectrogram reconstruction loss + feature-matching loss. Commoditized — use pretrained checkpoints from `hifi-gan` repo or nvidia-NeMo.

### Step 5: the full pipeline (pseudocode) · 完整流水线（伪代码）

```python
text = "Please remind me at 6 pm."
phones = phonemize(text)
mel = acoustic_model(phones, speaker=alice)      # [T, 80]
wav = vocoder(mel)                                # [T * 256]
soundfile.write("out.wav", wav, 24000)
```

---

## Use It · 实战用法

2026 年的选型组合：

| 场景 | 选择 |
|-----------|------|
| 实时英文语音助手 | Kokoro（CPU）或 XTTS v2（GPU） |
| 用 5 秒参考音频做克隆 | F5-TTS |
| 商业角色音色 | ElevenLabs v2.5 |
| 有声书旁白 | ElevenLabs v2.5 或 XTTS v2 + 微调 |
| 低资源语言 | 用 5–20 小时目标语言数据训练 VITS |
| 表现力 / 情绪标签 | ElevenLabs v2.5 或 StyleTTS 2 微调 |

截至 2026 年的开源领跑者：**要质量选 F5-TTS，要效率选 Kokoro**。除非你是搞历史研究的，否则别伸手拿 Tacotron。

> The 2026 stack:
> Open-source leader as of 2026: **F5-TTS for quality, Kokoro for efficiency**. Don't reach for Tacotron unless you are a historian.

---

## Pitfalls · 常见的坑

- **没有文本归一化器。** "Dr. Smith" 会被读成 "Doctor" 还是 "Drive"？"2026" 读成 "twenty twenty six" 还是 "two zero two six"？在音素化**之前**先做归一化。
- **OOV 专有名词。** "Ghumare" → "ghyu-mair"？给未知词配一个兜底的字素转音素（grapheme-to-phoneme）模型。
- **削波（clipping）。** 声码器输出很少削波，但推理时梅尔谱缩放不匹配可能冲破 ±1.0。永远 `np.clip(wav, -1, 1)`。
- **采样率不匹配。** Kokoro 输出 24 kHz，而你的下游流水线期望 16 kHz → 要么重采样，要么吃混叠（aliasing）。

> **No text normalizer.** "Dr. Smith" reads as "Doctor" or "Drive"? "2026" as "twenty twenty six" or "two zero two six"? Normalize BEFORE phonemizer.
> **OOV proper nouns.** "Ghumare" → "ghyu-mair"? Ship a fallback grapheme-to-phoneme model for unknown tokens.
> **Clipping.** Vocoder output rarely clips, but mel scaling mismatch at inference can overshoot ±1.0. Always `np.clip(wav, -1, 1)`.
> **Sample-rate mismatch.** Kokoro outputs 24 kHz; your downstream pipeline expects 16 kHz → resample or get aliasing.

---

## Ship It · 交付

保存为 `outputs/skill-tts-designer.md`：针对给定的音色、延迟与语言目标，设计一条 TTS 流水线。

> Save as `outputs/skill-tts-designer.md`. Design a TTS pipeline for a given voice, latency, and language target.

---

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。它从一个玩具词表构建音素字典，估计每个音素的时长，并打印一份假的「mel」调度表。
2. **中等。** 安装 Kokoro，用 `af_bella` 和 `am_adam` 两个音色合成同一句话，比较音频时长与主观质量。
3. **困难。** 录一段你自己 5 秒的参考音频，用 F5-TTS 克隆它，报告参考音频与克隆输出之间的 SECS。

> 1. **Easy.** Run `code/main.py`. Builds a phoneme dictionary from a toy vocab, estimates duration per phoneme, and prints a fake "mel" schedule.
> 2. **Medium.** Install Kokoro, synthesize the same sentence at voice `af_bella` and `am_adam`. Compare audio durations and subjective quality.
> 3. **Hard.** Record a 5-second reference clip of yourself. Use F5-TTS to clone it. Report SECS between reference and cloned output.

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Phoneme（音素） | 声音单位 | 抽象的声音类别；英语有 39 个（ARPABet）。 |
| Duration predictor（时长预测器） | 每个音素持续多久 | 非自回归模型的输出；每个音素对应的整数帧数。 |
| Vocoder（声码器） | 梅尔谱 → 波形 | 把梅尔频谱映射回原始采样点的神经网络。 |
| HiFi-GAN | 标准声码器 | 基于 GAN；2020–2024 年的主流。 |
| MOS | 主观质量 | 人类评分者给出的 1–5 平均意见分。 |
| SECS | 声音克隆指标 | 目标说话人嵌入与输出说话人嵌入之间的余弦相似度。 |
| F5-TTS | 2024 开源 SOTA | Flow-matching 扩散；zero-shot 克隆。 |
| Kokoro | CPU 英文 TTS 领头羊 | 82M 参数模型，Apache 2.0。 |

---

## Further Reading · 延伸阅读

- [Shen et al. (2017). Tacotron 2](https://arxiv.org/abs/1712.05884) —— seq2seq 基线。
- [Kim, Kong, Son (2021). VITS](https://arxiv.org/abs/2106.06103) —— 端到端、基于流的方法。
- [Chen et al. (2024). F5-TTS](https://arxiv.org/abs/2410.06885) —— 当前开源 SOTA。
- [Kong, Kim, Bae (2020). HiFi-GAN](https://arxiv.org/abs/2010.05646) —— 到 2026 年仍在出货的声码器。
- [Kokoro-82M on HuggingFace](https://huggingface.co/hexgrad/Kokoro-82M) —— 2024 年对 CPU 友好的英文 TTS。
