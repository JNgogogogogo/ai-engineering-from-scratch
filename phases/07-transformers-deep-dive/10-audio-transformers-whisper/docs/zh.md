# Audio Transformers — Whisper Architecture · 音频 Transformer——Whisper 架构

> 音频就是频率随时间铺开的一张「图像」。Whisper 是一个吃 mel 频谱图（mel spectrogram）、再反向吐出文字的 ViT。
>
> Audio is an image of frequency over time. Whisper is a ViT that eats mel spectrograms and speaks back.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 7 · 05 (Full Transformer), Phase 7 · 08 (Encoder-Decoder), Phase 7 · 09 (ViT)
**Time:** ~45 minutes

## The Problem · 问题在哪

在 Whisper（OpenAI，Radford et al. 2022）出现之前，最先进的自动语音识别（ASR, automatic speech recognition）是 wav2vec 2.0 和 HuBERT——自监督特征提取器加一个微调头。质量高，但数据管线昂贵、跨领域脆弱。多语言语音识别还得按语系各训一个模型。

Whisper 押了三个注：

1. **全量数据一起训。** 从互联网抓取的 680,000 小时弱标注音频，覆盖 97 种语言。不要干净的学术语料，不要音素标注。
2. **多任务、单模型。** 一个解码器，靠任务 token（task token）把转写、翻译、语音活动检测、语言识别、时间戳预测联合训练。
3. **标准 encoder-decoder Transformer。** 编码器吃 log-mel 频谱图，解码器自回归地产出文本 token。没有 vocoder，没有 CTC，没有 HMM。

结果就是：Whisper large-v3 在口音、噪声、以及完全没有干净标注数据的语言上都表现稳健。2026 年，它是每一个开源语音助手、以及大多数商用语音助手的默认语音前端。

> Before Whisper (OpenAI, Radford et al. 2022), state-of-the-art automatic speech recognition (ASR) meant wav2vec 2.0 and HuBERT — self-supervised feature extractors plus a fine-tuned head. High quality, expensive data pipelines, domain-brittle. Multilingual speech recognition needed separate models per language family.
> Whisper made three bets:
> 1. **Train on everything.** 680,000 hours of weakly-labeled audio scraped from the internet across 97 languages. No clean academic corpus. No phoneme labels.
> 2. **Multi-task single model.** One decoder trained jointly on transcription, translation, voice activity detection, language ID, and timestamping via task tokens.
> 3. **Standard encoder-decoder transformer.** Encoder consumes log-mel spectrograms. Decoder produces text tokens autoregressively. No vocoder, no CTC, no HMM.
> The result: Whisper large-v3 is robust across accents, noise, and languages that have zero clean labeled data. It is the default speech front-end for every open-source voice assistant and most commercial ones in 2026.

## The Concept · 概念

![Whisper 流水线：音频 → mel → 编码器 → 解码器 → 文本](../assets/whisper.svg)

### Step 1 — resample + window · 第 1 步——重采样与加窗

音频采样率 16 kHz。裁剪/填充到 30 秒。计算 log-mel 频谱图：80 个 mel 频带、10 ms 步进 → 约 3,000 帧 × 80 个特征。这就是 Whisper 眼中的「输入图像」。

> Audio at 16 kHz. Clip/pad to 30 seconds. Compute log-mel spectrogram: 80 mel bins, 10 ms stride → ~3,000 frames × 80 features. This is the "input image" that Whisper sees.

### Step 2 — convolutional stem · 第 2 步——卷积干层

两层 kernel 为 3、stride 为 2 的 Conv1D 把 3,000 帧压到 1,500。序列长度减半，而参数量几乎没有增加。

> Two Conv1D layers with kernel 3 and stride 2 reduce the 3,000 frames to 1,500. Halves sequence length without adding a lot of parameters.

### Step 3 — encoder · 第 3 步——编码器

一个 24 层（large 规格）的 Transformer 编码器，跑在 1,500 个时间步上。正弦位置编码、自注意力、GELU FFN。产出 1,500 × 1,280 的隐藏状态。

> A 24-layer (for large) transformer encoder over 1,500 timesteps. Sinusoidal positional encoding, self-attention, GELU FFN. Produces 1,500 × 1,280 hidden states.

### Step 4 — decoder · 第 4 步——解码器

一个 24 层的 Transformer 解码器。它从一个 BPE 词表自回归地产出 token——该词表是 GPT-2 词表的超集，外加几个音频专用的特殊 token。

> A 24-layer transformer decoder. It autoregressively produces tokens from a BPE vocabulary that is a superset of GPT-2's with a few audio-specific special tokens.

### Step 5 — task tokens · 第 5 步——任务 token

解码器的提示以控制 token 开头，告诉模型要做什么：

```
<|startoftranscript|>  <|en|>  <|transcribe|>  <|0.00|>
```

或者：

```
<|startoftranscript|>  <|fr|>  <|translate|>   <|0.00|>
```

模型就是按这个约定训练出来的。你用前缀控制任务——相当于 2026 年「指令微调」的语音版。

> The decoder prompt starts with control tokens that tell the model what to do:
> The model was trained on this convention. You control task by prefix. The 2026 equivalent of instruction-tuning, but applied to speech.

### Step 6 — output · 第 6 步——输出

束搜索（beam search，宽度 5）加一个 log-prob 阈值。当 `<|notimestamps|>` token 缺席时，每 0.02 秒音频预测一次时间戳。

> Beam search (width 5) with a log-prob threshold. Timestamps are predicted every 0.02 seconds of audio when the `<|notimestamps|>` token is absent.

### Whisper sizes · Whisper 各规格

| 模型 | 参数量 | 层数 | d_model | 注意力头数 | VRAM（fp16） |
|-------|--------|--------|---------|-------|-------------|
| Tiny | 39M | 4 | 384 | 6 | ~1 GB |
| Base | 74M | 6 | 512 | 8 | ~1 GB |
| Small | 244M | 12 | 768 | 12 | ~2 GB |
| Medium | 769M | 24 | 1024 | 16 | ~5 GB |
| Large | 1550M | 32 | 1280 | 20 | ~10 GB |
| Large-v3 | 1550M | 32 | 1280 | 20 | ~10 GB |
| Large-v3-turbo | 809M | 32 | 1280 | 20 | ~6 GB（4 层解码器） |

Large-v3-turbo（2024）把解码器从 32 层砍到 4 层。解码快 8 倍，WER（词错误率）回退不到 1 个点。正是这个解码速度的解锁，让 Whisper-turbo 成为 2026 年实时语音代理的默认选择。

> Large-v3-turbo (2024) cut the decoder from 32 layers to 4. 8× faster decoding with <1 WER point regression. That decode speed unlock is why Whisper-turbo is the default for real-time voice agents in 2026.

### What Whisper does not do · Whisper 不做什么

- 不做说话人分离（diarization，判断谁在说话）。需要的话搭配 pyannote。
- 原生不支持实时流式——30 秒窗口是固定的。现代封装（`faster-whisper`、`WhisperX`）用 VAD + 重叠拼接出流式能力。
- 超过 30 秒的长音频不做内部上下文建模，需要外部切块。实践中效果不错，因为人类语音的转写很少需要长程上下文。

> No diarization (who is speaking). Pair with pyannote for that.
> No real-time streaming natively — the 30-second window is fixed. Modern wrappers (`faster-whisper`, `WhisperX`) bolt on streaming via VAD + overlap.
> No long-form context beyond 30 s without external chunking. Works well in practice because human speech rarely needs long-range context for transcription.

### 2026 landscape · 2026 年格局

| 任务 | 模型 | 备注 |
|------|-------|-------|
| 英语 ASR | Whisper-turbo, Moonshine | Moonshine 在边缘设备上快 4 倍 |
| 多语言 ASR | Whisper-large-v3 | 97 种语言 |
| 流式 ASR | faster-whisper + VAD | 可以做到 150 ms 延迟目标 |
| TTS | Piper, XTTS-v2, Kokoro | encoder-decoder 模式，但形态与 Whisper 类似 |
| 音频 + 语言 | AudioLM, SeamlessM4T | 一个 Transformer 里同时用文本 token + 音频 token |

```figure
n5-mel-decode
```

## Build It · 动手造

见 `code/main.py`。我们不训练 Whisper——我们搭建 log-mel 频谱图流水线 + 任务 token 提示格式化器。生产环境里你真正会亲手碰的就是这两块。

> See `code/main.py`. We don't train Whisper — we build the log-mel spectrogram pipeline + task-token prompt formatter. Those are the parts you actually touch in production.

### Step 1: synthesize audio · 第 1 步：合成音频

生成一段 440 Hz、以 16 kHz 采样的 1 秒正弦波。16,000 个采样点。

> Generate a 1-second sine wave at 440 Hz sampled at 16 kHz. 16,000 samples.

### Step 2: log-mel spectrogram (simplified) · 第 2 步：log-mel 频谱图（简化版）

完整的 mel 频谱图需要 FFT。我们做一个简化的分帧 + 逐帧能量版本，不依赖 `librosa` 也能展示整条流水线：

```python
def frame_signal(x, frame_size=400, hop=160):
    frames = []
    for start in range(0, len(x) - frame_size + 1, hop):
        frames.append(x[start:start + frame_size])
    return frames
```

帧长 25 ms，hop 10 ms。与 Whisper 的加窗方式一致。用逐帧能量代替 mel 频带，只为教学。

> Full mel spectrogram needs FFT. We do a simplified framing + per-frame energy version that shows the pipeline without requiring `librosa`:
> Frame = 25 ms, hop = 10 ms. Matches Whisper's windowing. Per-frame energy stands in for mel bins for pedagogy.

### Step 3: pad to 30 s · 第 3 步：填充到 30 秒

Whisper 永远按 30 秒一块处理。把频谱图填充（或裁剪）到 3,000 帧。

> Whisper always processes 30-second chunks. Pad (or clip) the spectrogram to 3,000 frames.

### Step 4: build the prompt tokens · 第 4 步：构造提示 token

```python
def whisper_prompt(lang="en", task="transcribe", timestamps=True):
    tokens = ["<|startoftranscript|>", f"<|{lang}|>", f"<|{task}|>"]
    if not timestamps:
        tokens.append("<|notimestamps|>")
    return tokens
```

这就是任务控制的全部接口：一个 4 token 的前缀。

> That is the whole task-control surface. A 4-token prefix.

## Use It · 实战用法

```python
import whisper
model = whisper.load_model("large-v3-turbo")
result = model.transcribe("meeting.wav", language="en", task="transcribe")
print(result["text"])
print(result["segments"][0]["start"], result["segments"][0]["end"])
```

更快、且与 OpenAI 接口兼容的：

```python
from faster_whisper import WhisperModel
model = WhisperModel("large-v3-turbo", compute_type="int8_float16")
segments, info = model.transcribe("meeting.wav", vad_filter=True)
for s in segments:
    print(f"{s.start:.2f} - {s.end:.2f}: {s.text}")
```

**2026 年什么时候选 Whisper：**

- 用一个模型搞定多语言 ASR。
- 对嘈杂、多样的音频做稳健转写。
- 研究 / 原型阶段的 ASR——最快的起步点。

**什么时候选别的：**

- 边缘设备上的超低延迟流式——同等质量下 Moonshine 赢过 Whisper。
- 需要 <200 ms 的实时对话 AI——用专门的流式 ASR。
- 说话人分离——Whisper 不做这个；叠加 pyannote。

> **When to pick Whisper in 2026:** Multilingual ASR with one model. Robust transcription of noisy, diverse audio. Research / prototype ASR — fastest starting point.
> **When to pick something else:** Ultra-low latency streaming on edge — Moonshine beats Whisper at matched quality. Real-time conversational AI needing <200 ms — dedicated streaming ASR. Speaker diarization — Whisper does not do this; bolt on pyannote.

## Ship It · 交付

见 `outputs/skill-asr-configurator.md`。这个技能为一个新的语音应用挑选 ASR 模型、解码参数和预处理管线。

> See `outputs/skill-asr-configurator.md`. The skill picks an ASR model, decoding parameters, and preprocessing pipeline for a new speech application.

## Exercises · 练习

1. **简单。** 跑 `code/main.py`。确认 16 kHz、10 ms hop 下 1 秒信号的帧数约为 100 帧；30 秒约为 3,000 帧。
2. **中等。** 用 `numpy.fft` 构建完整的 log-mel 频谱图。验证 80 个 mel 频带与 `librosa.feature.melspectrogram(n_mels=80)` 在数值误差内一致。
3. **困难。** 实现流式推理：把音频切成 10 秒窗口、2 秒重叠，逐块跑 Whisper，合并转写。在一段 5 分钟播客样本上测与单次整段推理相比的词错误率（WER）。

> 1. **Easy.** Run `code/main.py`. Confirm the frame count for a 1-second signal at 16 kHz with 10 ms hop is ~100 frames. For 30 seconds: ~3,000 frames.
> 2. **Medium.** Build the full log-mel spectrogram using `numpy.fft`. Verify 80 mel bins match `librosa.feature.melspectrogram(n_mels=80)` within numerical error.
> 3. **Hard.** Implement streaming inference: chunk audio into 10 s windows with 2 s overlap, run Whisper on each chunk, merge transcripts. Measure word-error rate vs single-pass on a 5-minute podcast sample.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Mel spectrogram（mel 频谱图） | 「音频图像」 | 二维表示：一条轴是频带、另一条轴是时间帧，每个格子存对数尺度的能量。 |
| Log-mel | 「Whisper 眼里的东西」 | 经过 log 变换的 mel 频谱图；近似人耳对响度的感知。 |
| Frame（帧） | 「一个时间切片」 | 25 ms 的采样窗口；以 10 ms 步进重叠滑动。 |
| Task token（任务 token） | 「语音的提示前缀」 | 解码器提示里的特殊 token，如 `<\|transcribe\|>` / `<\|translate\|>`。 |
| Voice activity detection（VAD，语音活动检测） | 「找出有人说话的段落」 | 在 ASR 之前剔除静音的闸门；能大幅削减成本。 |
| CTC | 「Connectionist Temporal Classification」 | 经典的对齐无关 ASR 训练损失；Whisper 并不使用它。 |
| Whisper-turbo | 「小解码器 + 全量编码器」 | large-v3 编码器 + 4 层解码器；解码快 8 倍。 |
| Faster-whisper | 「生产级封装」 | CTranslate2 重实现；int8 量化；比 OpenAI 参考实现快 4 倍。 |

## Further Reading · 延伸阅读

- [Radford et al. (2022). Robust Speech Recognition via Large-Scale Weak Supervision](https://arxiv.org/abs/2212.04356) — Whisper 论文。
- [OpenAI Whisper repo](https://github.com/openai/whisper) — 参考代码 + 模型权重。读 `whisper/model.py`，约 400 行就能从头到尾看完整 Conv1D stem + 编码器 + 解码器。
- [OpenAI Whisper — `whisper/decoding.py`](https://github.com/openai/whisper/blob/main/whisper/decoding.py) — 第 5–6 步描述的束搜索 + 任务 token 逻辑就在这里；500 行，完全可读。
- [Baevski et al. (2020). wav2vec 2.0: A Framework for Self-Supervised Learning of Speech Representations](https://arxiv.org/abs/2006.11477) — 前身；在某些设定下仍是 SOTA 特征。
- [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) — 生产级封装，比参考实现快 4 倍。
- [Jia et al. (2024). Moonshine: Speech Recognition for Live Transcription and Voice Commands](https://arxiv.org/abs/2410.15608) — 2024 年面向边缘的 ASR，形态与 Whisper 类似但更小。
- [HuggingFace blog — "Fine-Tune Whisper For Multilingual ASR with 🤗 Transformers"](https://huggingface.co/blog/fine-tune-whisper) — 权威微调教程，覆盖 mel 频谱预处理器与 token-时间戳处理。
- [HuggingFace `modeling_whisper.py`](https://github.com/huggingface/transformers/blob/main/src/transformers/models/whisper/modeling_whisper.py) — 完整实现（编码器、解码器、交叉注意力、生成），与本课的架构图一一对应。
