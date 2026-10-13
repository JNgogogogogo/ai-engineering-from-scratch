# Audio Fundamentals — Waveforms, Sampling, Fourier Transform · 音频基础：波形、采样与傅里叶变换

> 波形是原始信号，频谱图是表示，梅尔特征是机器学习友好的形式。每一条现代 ASR 和 TTS 流水线都在爬这架梯子，而第一级台阶就是理解采样和傅里叶变换。
>
> Waveforms are the raw signal. Spectrograms are the representation. Mel features are the ML-friendly form. Every modern ASR and TTS pipeline walks this ladder, and the first rung is understanding sampling and Fourier.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 1 · 06 (Vectors & Matrices), Phase 1 · 14 (Probability Distributions)
**Time:** ~45 minutes

## The Problem · 问题在哪

麦克风产生的是随时间变化的气压信号，而神经网络吃的是张量。两者之间隔着一整套约定；一旦违反，就会产生静默的 bug：模型训练一切正常但词错误率（WER）翻倍，或者 TTS 上线后带嘶嘶声，或者声音克隆系统记住的是麦克风而不是说话人。

语音系统里的每一个 bug 都能追溯到三个问题之一：

1. 数据是用什么采样率（sample rate）录的，模型期望的又是什么？
2. 信号有没有混叠（aliasing）？
3. 你操作的是原始采样点，还是频率表示？

这三问答对，Phase 6 剩下的内容就顺畅；答错，连 Whisper-Large-v4 都会输出垃圾。

> A microphone produces a pressure-vs-time signal. Your neural net consumes tensors. Between them sits a stack of conventions that, when violated, produce silent bugs: the model trains fine but the WER doubles, or TTS ships a hiss, or a voice cloning system memorizes the microphone instead of the speaker.
> Every bug in speech systems traces back to one of three questions: what sample rate was the data recorded at and what does the model expect; is the signal aliased; are you operating on raw samples or on a frequency representation.
> Get these right and the rest of Phase 6 is tractable. Get them wrong and even Whisper-Large-v4 produces garbage.

## The Concept · 概念

![波形、采样、DFT 与频率 bin 的可视化](../assets/audio-fundamentals.svg)

**波形（Waveform）**。一个取值范围在 `[-1.0, 1.0]` 的一维浮点数组，按采样点编号索引。要换算成秒，除以采样率即可：`t = n / sr`。16 kHz 下的 10 秒片段就是 160,000 个浮点数组成的数组。

**采样率（sr）**。每秒采集多少个样本。2026 年的常见采样率：

| 采样率 | 用途 |
|------|-----|
| 8 kHz | 电话、老式 VOIP。4 kHz 的奈奎斯特上限会吃掉辅音。ASR 请避免。 |
| 16 kHz | ASR 标准。Whisper、Parakeet、SeamlessM4T v2 都吃 16 kHz 输入。 |
| 22.05 kHz | 老模型的 TTS 声码器训练。 |
| 24 kHz | 现代 TTS（Kokoro、F5-TTS、xTTS v2）。 |
| 44.1 kHz | CD 音频、音乐。 |
| 48 kHz | 影视、专业音频、高保真 TTS（VALL-E 2、NaturalSpeech 3）。 |

**奈奎斯特-香农采样定理（Nyquist-Shannon）**。采样率为 `sr` 时，能无歧义表示的最高频率是 `sr/2`。这条 `sr/2` 边界就是*奈奎斯特频率（Nyquist frequency）*。高于奈奎斯特频率的能量会发生*混叠（aliasing）*——被折叠到低频段——并污染信号。降采样之前务必先做低通滤波。

**位深（bit depth）**。16 位 PCM（有符号 int16，范围 ±32,767）是通用交换格式。音乐用 24 位，内部 DSP 用 32 位浮点。`soundfile` 这类库读取 int16，但暴露的是 `[-1, 1]` 范围内的 float32 数组。

**傅里叶变换（Fourier Transform）**。任何有限信号都是不同频率正弦波的叠加。离散傅里叶变换（DFT）对 `N` 个样本计算出 `N` 个复系数——每个频率 bin（频点）一个。`bin k` 对应频率 `k · sr / N` Hz。幅值是该频率处的振幅，相角是相位。

**FFT（快速傅里叶变换）**。当 `N` 是 2 的幂时计算 DFT 的 `O(N log N)` 算法。所有音频库底层都是 FFT。16 kHz 下的 1024 点 FFT 给出 512 个可用的频率 bin，覆盖 0–8 kHz，分辨率 15.6 Hz。

**分帧加窗（Framing + window）**。我们不会对整段音频做 FFT。而是把它切成互相重叠的*帧*（典型值：25 ms 窗长、10 ms 帧移），每帧乘一个窗函数（Hann、Hamming）以消除边缘不连续，再对每帧做 FFT。这就是短时傅里叶变换（STFT）。第 02 课从这里接着讲。

```figure
mel-scale
```

> **Waveform.** A one-dimensional array of floats in `[-1.0, 1.0]`. Indexed by sample number. To convert to seconds, divide by the sample rate: `t = n / sr`. A 10-second clip at 16 kHz is an array of 160,000 floats.
> **Nyquist-Shannon.** A sample rate of `sr` can unambiguously represent frequencies up to `sr/2`. Energy above Nyquist gets *aliased* — folded down into lower frequencies — and corrupts the signal. Always low-pass filter before downsampling.
> **Fourier Transform.** Any finite signal is a sum of sinusoids at different frequencies. The Discrete Fourier Transform (DFT) computes, for `N` samples, `N` complex coefficients — one per frequency bin. `bin k` maps to frequency `k · sr / N` Hz.
> **FFT.** ... A 1024-sample FFT at 16 kHz gives 512 usable frequency bins spanning 0–8 kHz at 15.6 Hz resolution.
> **Framing + window.** ... This is the Short-Time Fourier Transform (STFT). Lesson 02 picks up from here.

## Build It · 动手造

### Step 1: read a clip and plot the waveform · 读入片段并画出波形

`code/main.py` 只用标准库的 `wave` 模块，保证演示零依赖。生产环境你会用 `soundfile` 或 `torchaudio.load`（两者都返回 `(waveform, sr)` 元组）：

```python
import soundfile as sf
waveform, sr = sf.read("clip.wav", dtype="float32")  # shape (T,), sr=int
```

> `code/main.py` uses only the stdlib `wave` module to keep the demo dependency-free. For production you will use `soundfile` or `torchaudio.load` (both return `(waveform, sr)` tuples).

### Step 2: synthesize a sine wave from first principles · 从第一性原理合成正弦波

```python
import math

def sine(freq_hz, sr, seconds, amp=0.5):
    n = int(sr * seconds)
    return [amp * math.sin(2 * math.pi * freq_hz * i / sr) for i in range(n)]
```

16 kHz 下 1 秒的 440 Hz 正弦波（音乐会标准音 A）是 16,000 个浮点数。用 `wave.open(..., "wb")` 以 16 位 PCM 编码写盘。

> A 440 Hz sine (concert A) at 16 kHz for 1 second is 16,000 floats. Write with `wave.open(..., "wb")` using 16-bit PCM encoding.

### Step 3: compute the DFT by hand · 手算 DFT

```python
def dft(x):
    N = len(x)
    out = []
    for k in range(N):
        re = sum(x[n] * math.cos(-2 * math.pi * k * n / N) for n in range(N))
        im = sum(x[n] * math.sin(-2 * math.pi * k * n / N) for n in range(N))
        out.append((re, im))
    return out
```

`O(N²)` —— `N=256` 时足够验证正确性，对真实音频毫无用处。真实代码调用 `numpy.fft.rfft` 或 `torch.fft.rfft`。

> `O(N²)` — fine for `N=256` to confirm correctness, useless for real audio. Real code calls `numpy.fft.rfft` or `torch.fft.rfft`.

### Step 4: find the dominant frequency · 找出主频

幅值峰值索引 `k_star` 对应频率 `k_star * sr / N`。在 440 Hz 正弦波上运行，应返回 bin `440 * N / sr` 处的峰值。

> Magnitude peak index `k_star` maps to frequency `k_star * sr / N`. Running this on the 440 Hz sine should return a peak at bin `440 * N / sr`.

### Step 5: demonstrate aliasing · 演示混叠

以 10 kHz 采样一个 7 kHz 正弦波（奈奎斯特 = 5 kHz）。7 kHz 的音高于奈奎斯特频率，会折叠到 `10 − 7 = 3 kHz`。FFT 峰值出现在 3 kHz。这是经典的混叠演示，也是每块 DAC/ADC 都内置砖墙低通滤波器的原因。

> Sample a 7 kHz sine at 10 kHz (Nyquist = 5 kHz). The 7 kHz tone is above Nyquist and folds to `10 − 7 = 3 kHz`. The FFT peak appears at 3 kHz. This is the classic aliasing demo and the reason every DAC/ADC ships with a brick-wall low-pass filter.

## Use It · 实战用法

2026 年你实际会交付的技术栈：

| 任务 | 库 | 理由 |
|------|---------|-----|
| 读写 WAV/FLAC/OGG | `soundfile`（libsndfile 封装） | 最快、稳定、返回 float32。 |
| 重采样 | `torchaudio.transforms.Resample` 或 `librosa.resample` | 内置正确的抗混叠。 |
| STFT / 梅尔 | `torchaudio` 或 `librosa` | GPU 友好；属于 PyTorch 生态。 |
| 实时流式 | `sounddevice` 或 `pyaudio` | 跨平台 PortAudio 绑定。 |
| 检查文件 | `ffprobe` 或 `soxi` | 命令行、快速，报告 sr/声道/编解码器。 |

决策规则：**先匹配采样率，再匹配其他任何东西**。Whisper 期望 16 kHz 单声道 float32。喂给它 44.1 kHz 立体声，你会得到看起来像模型 bug 的垃圾输出。

> Decision rule: **match sample rate before you match anything else**. Whisper expects 16 kHz mono float32. Pass it 44.1 kHz stereo and you will get garbage that looks like a model bug.

## Ship It · 交付

保存为 `outputs/skill-audio-loader.md`。这个 skill 帮你检查音频输入是否匹配下游模型的期望，并在不匹配时正确重采样。

> Save as `outputs/skill-audio-loader.md`. The skill helps you check that audio input matches the expectations of the downstream model and resamples correctly when it does not.

## Exercises · 练习

1. **简单。** 在 16 kHz 下合成 1 秒的 220 Hz + 440 Hz + 880 Hz 混合信号。运行 DFT，确认在预期的 bin 上出现三个峰。
2. **中等。** 用 48 kHz 录一段 3 秒的自己说话的 WAV。用 `torchaudio.transforms.Resample`（带抗混叠）降到 16 kHz，再用朴素抽取（每三个样本取一个）降到 16 kHz。对两者做 FFT。混叠出现在哪里？
3. **困难。** 只用 `math` 和第 3 步的 DFT 从零实现 STFT。帧长 400，帧移 160，Hann 窗。用 `matplotlib.pyplot.imshow` 画出幅值。这就是第 02 课的频谱图。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 它实际上是什么意思 |
|------|-----------------|-----------------------|
| 采样率（Sample rate） | 每秒采多少个样本 | ADC 测量信号的频率，单位 Hz。 |
| 奈奎斯特（Nyquist） | 你能表示的最高频率 | `sr/2`；超过它的能量会混叠折返。 |
| 位深（Bit depth） | 每个样本的分辨率 | `int16` = 65,536 级；`float32` = `[-1, 1]` 内 24 位精度。 |
| DFT | 序列的傅里叶变换 | `N` 个样本 → `N` 个复数频率系数。 |
| FFT | 快速 DFT | `O(N log N)` 算法，要求 `N` 为 2 的幂。 |
| Bin（频点） | 频率列 | `k · sr / N` Hz；分辨率 = `sr / N`。 |
| STFT | 频谱图的底层实现 | 沿时间做分帧加窗的 FFT。 |
| 混叠（Aliasing） | 诡异的鬼影频率 | 高于奈奎斯特的能量镜像折叠到低频 bin。 |

## Further Reading · 延伸阅读

- [Shannon (1949). Communication in the Presence of Noise](https://people.math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf) —— 采样定理背后的论文。
- [Smith — The Scientist and Engineer's Guide to Digital Signal Processing](https://www.dspguide.com/ch8.htm) —— 免费、权威的 DSP 教科书。
- [librosa docs — audio primer](https://librosa.org/doc/latest/auto_tutorials/index.html) —— 带代码的实战演练。
- [Heinrich Kuttruff — Room Acoustics (6th ed.)](https://www.taylorfrancis.com/books/mono/10.1201/9781315372150/room-acoustics-heinrich-kuttruff) —— 理解真实世界音频为何不是干净正弦波的参考书。
- [Steve Eddins — FFT Interpretation notebook](https://blogs.mathworks.com/steve/2020/03/30/fft-spectrum-and-spectral-densities/) —— 10 分钟讲清频率 bin 的直觉。
