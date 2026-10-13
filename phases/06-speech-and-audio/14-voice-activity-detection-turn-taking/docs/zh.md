# Voice Activity Detection & Turn-Taking — Silero, Cobra, and the Flush Trick · 语音活动检测与轮次交替——Silero、Cobra 与 Flush 技巧

> 每个语音代理的生死都系于两个决策：用户现在在说话吗？以及，他说完了吗？VAD（语音活动检测）回答第一个。轮次检测（turn-detection，VAD + 静音悬挂 + 语义端点模型）回答第二个。任何一个是错的，你的助手要么打断用户，要么永远闭不上嘴。
>
> Every voice agent lives or dies on two decisions: is the user speaking now, and are they done? VAD answers the first. Turn-detection (VAD + silence-hangover + semantic endpoint model) answers the second. Get either wrong and your assistant either cuts users off or never shuts up.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 6 · 11 (Real-Time Audio), Phase 6 · 12 (Voice Assistant)
**Time:** ~45 minutes

---

## The Problem · 问题在哪

语音代理在每个 20 ms 块上要做三个不同的决策：

1. **这一帧是语音吗？** —— VAD（voice activity detection，语音活动检测）。二元的，逐帧判断。
2. **用户开始一段新话语（utterance）了吗？** —— 起始检测（onset detection）。
3. **用户说完了吗？** —— 端点检测（end-pointing，轮次结束）。

朴素答案（能量阈值）在任何噪声下都会失效——车流、键盘、人群嘈杂声。2026 年的答案：Silero VAD（开源、深度学习）+ 轮次检测模型（语义端点检测，semantic endpointing）+ VAD 校准的静音悬挂（silence hangover）。

> Three distinct decisions a voice agent makes on every 20 ms chunk:
> 1. **Is this frame speech?** — VAD. Binary, per-frame.
> 2. **Has the user started a new utterance?** — onset detection.
> 3. **Has the user finished?** — end-pointing (turn-end).
> The naive answer (energy threshold) fails on any noise — traffic, keyboards, crowd babble. The 2026 answer: Silero VAD (open, deep-learned) + a turn-detection model (semantic endpointing) + a VAD-calibrated silence hangover.

---

## The Concept · 概念

![VAD 级联：能量 → Silero → 轮次检测器 → flush 技巧](../assets/vad-turn-taking.svg)

### The three-tier VAD cascade · 三级 VAD 级联

**第 1 级：能量门。** 最便宜。以 -40 dBFS 为 RMS 阈值。能滤掉明显的静音，但任何高于阈值的噪声都会触发。

**第 2 级：Silero VAD**（2020-2026，MIT 许可）。100 万参数。在 6000+ 种语言上训练。单 CPU 线程上每 30 ms 块约 1 ms。5% FPR 下 TPR 87.7%。开源默认之选。

**第 3 级：语义轮次检测器。** LiveKit 的 turn-detection 模型（2024-2026）或你自己的小分类器。区分「句子中间的停顿」和「说完了」。用语言学上下文（语调 + 最近的词），而不只是静音。

> **Tier 1: energy gate.** Cheapest. Threshold RMS at -40 dBFS. Filters obvious silence but fires on any noise above the threshold.
> **Tier 2: Silero VAD** (2020-2026, MIT). 1M parameters. Trained on 6000+ languages. Runs in ~1 ms per 30 ms chunk on a single CPU thread. 87.7% TPR at 5% FPR. The open-source default.
> **Tier 3: semantic turn detector.** LiveKit's turn-detection model (2024-2026) or your own small classifier. Distinguishes "pause mid-sentence" from "done talking." Uses linguistic context (intonation + recent words), not just silence.

---

### Key parameters and their defaults · 关键参数与默认值

- **阈值（threshold）。** Silero 输出一个概率；以 &gt; 0.5（默认）或 &gt; 0.3（灵敏）判定为语音。阈值更低 = 更少剪掉第一个词，但误报更多。
- **最短语音时长。** 短于 250 ms 的语音直接丢弃——通常是咳嗽或椅子声。
- **静音悬挂（silence hangover，即端点检测）。** VAD 归零之后，等 500-800 ms 再判定轮次结束。太短 → 打断用户。太长 → 感觉迟钝。
- **预卷缓冲（pre-roll buffer）。** 在 VAD 触发前保留 300-500 ms 音频。避免「hey」被剪掉。

> **Threshold.** Silero outputs a probability; classify speech at &gt; 0.5 (default) or &gt; 0.3 (sensitive). Lower threshold = fewer first-word clips, more false positives.
> **Minimum speech duration.** Reject speech shorter than 250 ms — usually coughs or chair noise.
> **Silence hangover (end-pointing).** After VAD returns to 0, wait 500-800 ms before declaring end-of-turn. Too short → interrupt user. Too long → feels sluggish.
> **Pre-roll buffer.** Keep 300-500 ms of audio before VAD fires. Prevents "hey" being clipped.

---

### The flush trick (Kyutai 2025) · Flush 技巧（Kyutai 2025）

流式 STT 模型有一个前视延迟（look-ahead delay）（Kyutai STT-1B 为 500 ms，STT-2.6B 为 2.5 s）。通常你得在语音结束后等这么久才能拿到转写。Flush 技巧：当 VAD 判定语音结束时，**给 STT 发一个 flush 信号**，强制它立即输出。STT 以约 4 倍实时速度处理，所以 500 ms 的缓冲约 125 ms 就能处理完。

端到端：125 ms VAD + flush STT = 对话级延迟。

> Streaming STT models have a look-ahead delay (500 ms for Kyutai STT-1B, 2.5 s for STT-2.6B). Normally you'd wait that long after end-of-speech for the transcript. Flush trick: when VAD fires end-of-speech, **send a flush signal to the STT** that forces immediate output. STT processes at ~4× realtime, so the 500 ms buffer finishes in ~125 ms.
> End-to-end: 125 ms VAD + flush STT = conversational latency.

---

### 2026 VAD comparison · 2026 年 VAD 对比

| VAD | TPR @ 5% FPR | 延迟 | 许可 |
|-----|--------------|---------|---------|
| WebRTC VAD (Google, 2013) | 50.0% | 30 ms | BSD |
| Silero VAD (2020-2026) | 87.7% | ~1 ms | MIT |
| Cobra VAD (Picovoice) | 98.9% | ~1 ms | 商业 |
| pyannote segmentation | 95% | ~10 ms | 类 MIT |

Silero 是正确的默认。Cobra 是合规 / 精度升级版。纯能量 VAD 在 2026 年的生产环境里没有位置。

> Silero is the right default. Cobra is the compliance / accuracy upgrade. Energy-only VAD has no place in 2026 production.

```figure
sp-vad-cascade
```

---

## Build It · 动手造

### Step 1: the energy gate · 能量门

```python
def energy_vad(chunk, threshold_dbfs=-40.0):
    rms = (sum(x * x for x in chunk) / len(chunk)) ** 0.5
    dbfs = 20.0 * math.log10(max(rms, 1e-10))
    return dbfs > threshold_dbfs
```

### Step 2: Silero VAD in Python · 用 Python 跑 Silero VAD

```python
from silero_vad import load_silero_vad, get_speech_timestamps

vad = load_silero_vad()
audio = torch.tensor(waveform_16k, dtype=torch.float32)
segments = get_speech_timestamps(
    audio, vad, sampling_rate=16000,
    threshold=0.5,
    min_speech_duration_ms=250,
    min_silence_duration_ms=500,
    speech_pad_ms=300,
)
for s in segments:
    print(f"{s['start']/16000:.2f}s - {s['end']/16000:.2f}s")
```

### Step 3: turn-end state machine · 轮次结束状态机

```python
class TurnDetector:
    def __init__(self, silence_hangover_ms=500, min_speech_ms=250):
        self.state = "idle"
        self.speech_ms = 0
        self.silence_ms = 0
        self.silence_hangover_ms = silence_hangover_ms
        self.min_speech_ms = min_speech_ms

    def update(self, is_speech, chunk_ms=20):
        if is_speech:
            self.speech_ms += chunk_ms
            self.silence_ms = 0
            if self.state == "idle" and self.speech_ms >= self.min_speech_ms:
                self.state = "speaking"
                return "START"
        else:
            self.silence_ms += chunk_ms
            if self.state == "speaking" and self.silence_ms >= self.silence_hangover_ms:
                self.state = "idle"
                self.speech_ms = 0
                return "END"
        return None
```

### Step 4: the flush trick skeleton · Flush 技巧骨架

```python
def flush_on_end(stt_client, audio_buffer):
    stt_client.send_audio(audio_buffer)
    stt_client.send_flush()
    return stt_client.recv_transcript(timeout_ms=150)
```

STT（Kyutai、Deepgram、AssemblyAI）必须支持 flush，这招才有效。Whisper 流式不支持——它是按块处理的，永远在等下一个块。

> STT (Kyutai, Deepgram, AssemblyAI) must support flush for this to work. Whisper streaming does not — it's block-based and always waits for chunks.

---

## Use It · 实战用法

| 场景 | VAD 选择 |
|-----------|-----------|
| 开放、快速、通用 | Silero VAD |
| 商业呼叫中心 | Cobra VAD |
| 端侧（手机） | Silero VAD ONNX |
| 研究 / 说话人分离（diarization） | pyannote segmentation |
| 零依赖兜底 | WebRTC VAD（遗留） |
| 需要轮次结束质量 | Silero + LiveKit turn-detector 叠加 |

经验法则：除非真的别无选择，绝不上线纯能量 VAD。

> Rule of thumb: never ship energy-only VAD unless you really have no other option.

---

## Pitfalls · 常见的坑

- **固定阈值。** 安静环境能用，嘈杂环境失效。要么在设备上校准，要么换成 Silero。
- **静音悬挂太短。** 代理在句子中间打断用户。500-800 ms 是对话语音的最佳区间。
- **悬挂太长。** 感觉迟钝。和目标用户一起做 A/B 测试。
- **没有预卷缓冲。** 用户音频的前 200-300 ms 丢了。永远保留一个滚动的 pre-roll。
- **忽略语义端点检测。** 「嗯，让我想想……」里有很长的停顿。用户讨厌话说到一半被打断。用 LiveKit 的 turn-detector 或类似方案。

> **Fixed threshold.** Works in quiet, fails in noisy. Either calibrate on-device or switch to Silero.
> **Too-short silence hangover.** Agent interrupts mid-sentence. 500-800 ms is the sweet spot for conversational speech.
> **Too-long hangover.** Feels sluggish. A/B test with target users.
> **No pre-roll buffer.** First 200-300 ms of user audio lost. Always keep a rolling pre-roll.
> **Ignoring semantic endpointing.** "Hmm, let me think..." contains long pauses. Users hate being cut off mid-thought. Use LiveKit's turn-detector or similar.

---

## Ship It · 交付

保存为 `outputs/skill-vad-tuner.md`：为一个工作负载挑选 VAD 模型、阈值、悬挂时长、pre-roll 和轮次检测策略。

> Save as `outputs/skill-vad-tuner.md`. Pick VAD model, threshold, hangover, pre-roll, and turn-detection strategy for a workload.

---

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。它模拟「语音 + 静音 + 语音 + 咳嗽」序列并测试三级 VAD。
2. **中等。** 安装 `silero-vad`，处理一段 5 分钟录音，调阈值使首词剪断和误触发同时最小化。报告 precision/recall。
3. **困难。** 做一个迷你轮次检测器：Silero VAD + 一个建在最近 10 个词的嵌入上的 3 层 MLP（用 sentence-transformers）。在人工标注的轮次结束数据集上训练。F1 比只用 Silero 高出 10%。

> 1. **Easy.** Run `code/main.py`. It simulates a speech + silence + speech + coughs sequence and tests three VAD tiers.
> 2. **Medium.** Install `silero-vad`, process a 5-min recording, tune threshold to minimize both first-word clips and false triggers. Report precision/recall.
> 3. **Hard.** Build a mini turn-detector: Silero VAD + a 3-layer MLP on the last 10 words' embeddings (use sentence-transformers). Train on a hand-labeled turn-end dataset. Beat Silero-only by 10% F1.

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| VAD（语音活动检测） | 语音检测器 | 逐帧二元判断：这是语音吗？ |
| Turn detection（轮次检测） | 端点检测 | VAD + 静音悬挂 + 语义端点。 |
| Silence hangover（静音悬挂） | 说完之后再等等 | 判定轮次结束前等待的时间；500-800 ms。 |
| Pre-roll（预卷缓冲） | 语音前的缓冲 | VAD 触发前保留 300-500 ms 音频。 |
| Flush trick | Kyutai 的招数 | VAD → flush-STT → 125 ms，而不是 500 ms 延迟。 |
| Semantic endpoint（语义端点） | 「他们是真想停吗？」 | 看词而不只看静音的 ML 分类器。 |
| TPR @ FPR 5% | ROC 上的一个点 | 标准 VAD 基准；Silero 87.7%，WebRTC 50%。 |

---

## Further Reading · 延伸阅读

- [Silero VAD](https://github.com/snakers4/silero-vad) —— 参考级开源 VAD。
- [Picovoice Cobra VAD](https://picovoice.ai/products/voice/voice-activity-detection/) —— 商业精度领先者。
- [Kyutai — Unmute + flush trick](https://kyutai.org/stt) —— 200 ms 以内的工程技巧。
- [LiveKit — turn detection](https://docs.livekit.io/agents/logic/turns/) —— 生产环境中的语义端点检测。
- [WebRTC VAD](https://webrtc.googlesource.com/src/) —— 遗留基线。
- [pyannote segmentation](https://github.com/pyannote/pyannote-audio) —— 说话人分离级的分段。
