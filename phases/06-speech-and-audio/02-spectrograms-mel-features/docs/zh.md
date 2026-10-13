# Spectrograms, Mel Scale & Audio Features · 频谱图、梅尔刻度与音频特征

> 神经网络吃原始波形的效果不好。它们吃的是频谱图（spectrogram），吃梅尔频谱图（mel spectrogram）效果更好。2026 年的每一个 ASR、TTS 和音频分类器，都生死攸关地取决于这一个预处理选择。
>
> Neural nets do not consume raw waveforms well. They consume spectrograms. They consume mel spectrograms even better. Every ASR, TTS, and audio classifier in 2026 lives or dies by this single preprocessing choice.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 6 · 01 (Audio Fundamentals)
**Time:** ~45 minutes

## The Problem · 问题在哪

拿一段 10 秒的 16 kHz 音频：160,000 个浮点数，全部落在 `[-1, 1]`，与「狗叫」或「单词 cat」这些标签几乎完全不相关。原始波形里有信息，但它的形态模型很难提取。同一音素相隔 100 ms 读两遍，原始采样点截然不同。

频谱图解决了这个问题。它把人类感知忽略的时间细节（微秒级抖动）压缩掉，保留感知关注的结构（在约 10–25 ms 的时间窗内，哪些频率有能量）。

梅尔频谱图更进一步。人类以对数方式感知音高：100 Hz 对 200 Hz 听起来与 1000 Hz 对 2000 Hz「距离一样远」。梅尔刻度（Mel scale）就是对频率轴做这种扭曲。从 2010 年到 2026 年，梅尔频谱图一直是语音机器学习里最重要的单一特征。

> Take a 10-second 16 kHz clip. That is 160,000 floats, all in `[-1, 1]`, almost perfectly uncorrelated with the label "dog barking" or "the word cat". The raw waveform has the information but in a form the model cannot easily extract. Two identical phonemes spoken 100 ms apart have completely different raw samples.
> A spectrogram fixes this. It collapses the temporal detail where human perception ignores it (microsecond jitter) and preserves the structure where perception attends (which frequencies are energetic, over time windows of ~10–25 ms).
> Mel spectrograms push further. Humans perceive pitch logarithmically: 100 Hz vs 200 Hz sounds "the same distance apart" as 1000 Hz vs 2000 Hz. The mel scale warps the frequency axis to match. A mel-scaled spectrogram is the single most important feature in speech ML from 2010 through 2026.

## The Concept · 概念

![从波形到 STFT 到梅尔频谱图再到 MFCC 的阶梯](../assets/mel-features.svg)

**STFT（短时傅里叶变换，Short-Time Fourier Transform）**。把波形切成互相重叠的帧（典型值：25 ms 窗长、10 ms 帧移，即 16 kHz 下的 400 样本 / 160 样本）。每帧乘一个窗函数（默认 Hann；Hamming 是略有不同的折中）。对每帧做 FFT。把幅值谱堆叠成形状为 `(n_frames, n_freq_bins)` 的矩阵。这就是你的频谱图。

**对数幅值（Log-magnitude）**。原始幅值横跨 5-6 个数量级。取 `log(|X| + 1e-6)` 或 `20 * log10(|X|)` 来压缩动态范围。所有生产流水线用的都是对数幅值，不是原始幅值。

**梅尔刻度（Mel scale）**。频率 `f`（Hz）到梅尔 `m` 的映射为 `m = 2595 * log10(1 + f / 700)`。这个映射在 1 kHz 以下近似线性，以上近似对数。覆盖 0–8 kHz 的 80 个梅尔 bin 是标准 ASR 输入。

**梅尔滤波器组（Mel filterbank）**。一组在梅尔刻度上等距排布的三角滤波器。每个滤波器是相邻 FFT bin 的加权和。STFT 幅值乘上滤波器组矩阵，一次矩阵乘法就得到梅尔频谱图。

**对数梅尔频谱图（Log-mel spectrogram）**。`log(mel_spec + 1e-10)`。Whisper 的输入。Parakeet 的输入。SeamlessM4T 的输入。2026 年通用的音频前端。

**MFCC**。对对数梅尔频谱图做 DCT（II 型），保留前 13 个系数。它为特征去相关并进一步压缩。大约 2015 年之前一直是主导特征，之后 CNN/Transformer 直接吃原始 log-mel 追平了它。说话人识别（x-vectors、ECAPA）至今仍在用。

**分辨率权衡（Resolution trade）**。FFT 越大 = 频率分辨率越好，但时间分辨率越差。25 ms / 10 ms 是音频机器学习的默认值；音乐用 50 ms / 12.5 ms；瞬态检测（鼓点、爆破音）用 5 ms / 2 ms。

```figure
spectrogram-window
```

> **STFT.** Slice the waveform into overlapping frames (typical: 25 ms window, 10 ms hop = 400 samples / 160 samples at 16 kHz). ... FFT each frame. Stack the magnitude spectra into a matrix of shape `(n_frames, n_freq_bins)`. That is your spectrogram.
> **Log-magnitude.** Raw magnitudes span 5-6 orders of magnitude. ... Every production pipeline uses log-magnitude, not raw magnitude.
> **Mel scale.** Frequency `f` in Hz maps to mel `m` by `m = 2595 * log10(1 + f / 700)`. The mapping is roughly linear below 1 kHz and roughly logarithmic above. 80 mel bins covering 0–8 kHz is the standard ASR input.
> **Log-mel spectrogram.** `log(mel_spec + 1e-10)`. Whisper's input. Parakeet's input. SeamlessM4T's input. The universal 2026 audio frontend.
> **Resolution trade.** Larger FFT = better frequency resolution but worse time resolution.

## Build It · 动手造

### Step 1: frame the waveform · 给波形分帧

```python
def frame(signal, frame_len, hop):
    n = 1 + (len(signal) - frame_len) // hop
    return [signal[i * hop : i * hop + frame_len] for i in range(n)]
```

10 秒 16 kHz 片段在 `frame_len=400, hop=160` 下产生 998 帧。

> A 10-second 16 kHz clip with `frame_len=400, hop=160` yields 998 frames.

### Step 2: Hann window · Hann 窗

```python
import math

def hann(N):
    return [0.5 * (1 - math.cos(2 * math.pi * n / (N - 1))) for n in range(N)]
```

FFT 之前逐元素相乘。它消除在非零端点处截断造成的频谱泄漏。

> Multiply element-wise before the FFT. Removes spectral leakage caused by truncating at non-zero endpoints.

### Step 3: STFT magnitude · STFT 幅值

```python
def stft_magnitude(signal, frame_len=400, hop=160):
    win = hann(frame_len)
    frames = frame(signal, frame_len, hop)
    return [magnitudes(dft([w * s for w, s in zip(win, f)])) for f in frames]
```

生产环境用 `torch.stft` 或 `librosa.stft`（FFT 加持、向量化）。这里的循环是教学用的；`code/main.py` 在短片段上运行它。

> Production uses `torch.stft` or `librosa.stft` (FFT-backed, vectorized). The loop here is pedagogical; it runs on short clips in `code/main.py`.

### Step 4: mel filterbank · 梅尔滤波器组

```python
def hz_to_mel(f):
    return 2595.0 * math.log10(1.0 + f / 700.0)

def mel_to_hz(m):
    return 700.0 * (10 ** (m / 2595.0) - 1)

def mel_filterbank(n_mels, n_fft, sr, fmin=0, fmax=None):
    fmax = fmax or sr / 2
    mels = [hz_to_mel(fmin) + (hz_to_mel(fmax) - hz_to_mel(fmin)) * i / (n_mels + 1)
            for i in range(n_mels + 2)]
    hzs = [mel_to_hz(m) for m in mels]
    bins = [int(h * n_fft / sr) for h in hzs]
    fb = [[0.0] * (n_fft // 2 + 1) for _ in range(n_mels)]
    for m in range(n_mels):
        for k in range(bins[m], bins[m + 1]):
            fb[m][k] = (k - bins[m]) / max(1, bins[m + 1] - bins[m])
        for k in range(bins[m + 1], bins[m + 2]):
            fb[m][k] = (bins[m + 2] - k) / max(1, bins[m + 2] - bins[m + 1])
    return fb
```

`n_fft=400`、覆盖 0–8 kHz 的 80 个梅尔 bin 给出 `(80, 201)` 矩阵。把 `(n_frames, 201)` 的 STFT 幅值乘上它的转置，得到 `(n_frames, 80)` 的梅尔频谱图。

> 80 mels covering 0–8 kHz with `n_fft=400` gives an `(80, 201)` matrix. Multiply the `(n_frames, 201)` STFT magnitude by the transpose to get `(n_frames, 80)` mel spectrogram.

### Step 5: log-mel · 对数梅尔

```python
def log_mel(mel_spec, eps=1e-10):
    return [[math.log(max(v, eps)) for v in frame] for frame in mel_spec]
```

常见替代方案：`librosa.power_to_db`（以参考值归一化的 dB）、`10 * log10(power + eps)`。Whisper 用的是更复杂的裁剪加归一化流程（见 Whisper 的 `log_mel_spectrogram`）。

> Common alternatives: `librosa.power_to_db` (reference-normalized dB), `10 * log10(power + eps)`. Whisper uses a more involved clip + normalize routine (see Whisper's `log_mel_spectrogram`).

### Step 6: MFCCs · MFCC 系数

```python
def dct_ii(x, n_coeffs):
    N = len(x)
    return [
        sum(x[n] * math.cos(math.pi * k * (2 * n + 1) / (2 * N)) for n in range(N))
        for k in range(n_coeffs)
    ]
```

对每个 log-mel 帧做 DCT，保留前 13 个系数。这就是你的 MFCC 矩阵。第一个系数通常丢弃（它编码的是整体能量）。

> Apply DCT to each log-mel frame, keep the first 13 coefficients. That is your MFCC matrix. The first coefficient is usually dropped (it encodes overall energy).

## Use It · 实战用法

2026 年的技术栈：

| 任务 | 特征 |
|------|----------|
| ASR（Whisper、Parakeet、SeamlessM4T） | 80 维 log-mel，10 ms 帧移，25 ms 窗长 |
| TTS 声学模型（VITS、F5-TTS、Kokoro） | 80 维梅尔，5–12 ms 帧移以获得精细时间控制 |
| 音频分类（AST、PANNs、BEATs） | 128 维 log-mel，10 ms 帧移 |
| 说话人嵌入（ECAPA-TDNN、WavLM） | 80 维 log-mel 或原始波形 SSL |
| 音乐（MusicGen、Stable Audio 2） | EnCodec 离散 token（不是梅尔） |
| 关键词检出（keyword spotting） | 40 维 MFCC，面向微型设备 |

经验法则：**只要不是做音乐，就从 80 维 log-mel 开始。** 任何偏离都要自己举证。

> Rule of thumb: **if you are not working on music, start with 80 log-mels.** The burden of proof is on any deviation.

## Pitfalls that still ship in 2026 · 2026 年仍在发生的坑

- **梅尔数量不匹配。** 训练用 80 维梅尔，推理用 128 维。静默失败。在两端都记录特征形状。
- **上游采样率不匹配。** 22.05 kHz 算出的梅尔与 16 kHz 的看起来不一样。在特征化*之前*先修好采样率。
- **dB 与 log 之别。** Whisper 期望 log-mel，不是 dB-mel。有些 HF 流水线会自动检测，你自己写的代码不会。
- **归一化漂移。** 训练时按整句归一化，推理时全局归一化。这是让 WER 翻倍的生产 bug。
- **补零造成的泄漏。** 在片段末尾补零会让末尾几帧出现平坦频谱。对称补零或复制边界样本。

> **Mel count mismatch.** Training with 80 mels, inference with 128 mels. Silent failure. Log the feature shape at both ends.
> **Sample-rate mismatch upstream.** Mels computed at 22.05 kHz look different from 16 kHz. Fix SR *before* featurization.
> **dB vs log.** Whisper expects log-mel, not dB-mel.
> **Normalization drift.** Per-utterance normalization during training, global normalization during inference. Production bug that doubles WER.
> **Leakage from padding.** Zero-padding the end of a clip produces a flat spectrum in the trailing frames.

## Ship It · 交付

保存为 `outputs/skill-feature-extractor.md`。这个 skill 为给定的目标模型挑选特征类型、梅尔数量、帧长/帧移和归一化方案。

> Save as `outputs/skill-feature-extractor.md`. The skill picks feature type, mel count, frame/hop, and normalization for a given model target.

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。它合成一个扫频信号（频率从 200 扫到 4000 Hz）并打印每帧的 argmax 梅尔 bin。（可选）画图确认与扫频一致。
2. **中等。** 用 `n_mels` 取 `{40, 80, 128}`、`frame_len` 取 `{200, 400, 800}` 重跑。沿时间轴测量尖峰带宽。哪种组合分辨扫频的效果最好？
3. **困难。** 实现 `power_to_db`，在一个用 AudioMNIST 的小型 CNN 分类器上比较三种特征的 ASR 精度：(a) 原始 log-mel，(b) `ref=max` 的 dB-mel，(c) MFCC-13 + 一阶差分 + 二阶差分。报告 top-1 精度。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 它实际上是什么意思 |
|------|-----------------|-----------------------|
| 帧（Frame） | 一小段 | 喂给一次 FFT 的 25 ms 波片段。 |
| 帧移（Hop） | 步幅 | 相邻两帧之间的样本数；10 ms 是 ASR 默认值。 |
| 窗（Window） | Hann/Hamming 那个东西 | 逐点乘子，把帧边缘收敛到零。 |
| STFT | 频谱图生成器 | 分帧加窗的 FFT；产出时间 × 频率矩阵。 |
| 梅尔（Mel） | 扭曲的频率 | 对数感知刻度；`m = 2595·log10(1 + f/700)`。 |
| 滤波器组（Filterbank） | 那个矩阵 | 把 STFT 投影到梅尔 bin 的三角滤波器。 |
| Log-mel | Whisper 的输入 | `log(mel_spec + eps)`；2026 年的标准。 |
| MFCC | 老派特征 | log-mel 的 DCT；13 个系数，去相关。 |

## Further Reading · 延伸阅读

- [Davis, Mermelstein (1980). Comparison of parametric representations for monosyllabic word recognition](https://ieeexplore.ieee.org/document/1163420) —— MFCC 的原始论文。
- [Stevens, Volkmann, Newman (1937). A Scale for the Measurement of the Psychological Magnitude Pitch](https://pubs.aip.org/asa/jasa/article-abstract/8/3/185/735757/) —— 梅尔刻度的出处。
- [OpenAI — Whisper source, log_mel_spectrogram](https://github.com/openai/whisper/blob/main/whisper/audio.py) —— 去读参考实现。
- [librosa feature extraction docs](https://librosa.org/doc/latest/api/feature.html) —— `mfcc`、`melspectrogram`、hop/window 的参考文档。
- [NVIDIA NeMo — audio preprocessing](https://docs.nvidia.com/deeplearning/nemo/user-guide/docs/en/main/asr/asr_all.html#featurizers) —— Parakeet + Canary 模型的生产级流水线。
