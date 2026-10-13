# Real-Time Audio Processing · 实时音频处理

> Batch pipelines process a file. Real-time pipelines process the next 20 milliseconds before the next 20 arrive. Every conversational AI, broadcast studio, and telephony bot lives and dies by this latency budget.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 6 · 02 (Spectrograms), Phase 6 · 04 (ASR), Phase 6 · 07 (TTS)
**Time:** ~75 minutes

---

## The Problem · 问题在哪

你想要一个「感觉是活的」语音助手。人类对话轮替（turn-taking）延迟约 230 ms（从静音到回应）。超过 500 ms 就觉得像机器人；超过 1500 ms 就觉得坏了。2026 年，完整跑一轮 **听到 → 理解 → 生成 → 说出来** 的预算是：

| 阶段 | 预算 |
|-------|--------|
| 麦克风 → 缓冲 | 20 ms |
| VAD | 10 ms |
| ASR（流式） | 150 ms |
| LLM（首 token） | 100 ms |
| TTS（首块） | 100 ms |
| 渲染 → 扬声器 | 20 ms |
| **总计** | **~400 ms** |

Moshi（Kyutai，2024）做到 200 ms 全双工。GPT-4o-realtime（2024）约 320 ms。2022 年的级联（cascaded）流水线要 2500 ms。10 倍的提升来自三项技术：(1) 处处流式，(2) 带部分结果的异步流水线，(3) 可打断的生成。

> Human conversational turn-taking latency is ~230 ms (silence-to-response). Anything above 500 ms feels robotic; above 1500 ms feels broken. The budget for a full **hear → understand → respond → speak** loop in 2026 is:
> Moshi (Kyutai, 2024) clocked 200 ms full-duplex. GPT-4o-realtime (2024) clocks ~320 ms. Cascaded pipelines in 2022 shipped at 2500 ms. The 10× improvement came from three techniques: (1) streaming everywhere, (2) asynchronous pipelining with partial results, (3) interruptible generation.

---

## The Concept · 概念

![带环形缓冲、VAD 门控与打断的流式音频流水线](../assets/real-time.svg)

**帧 / 块 / 窗口（frame / chunk / window）。** 实时音频按固定大小的块流动。常见选择：20 ms（16 kHz 下 320 个采样点）。下游一切都必须跟上这个节奏。

**环形缓冲（ring buffer）。** 固定大小的循环缓冲。生产者线程写新帧，消费者线程读。避免在热路径上分配内存。容量 ≈ 最大延迟 × 采样率；2 秒的 16 kHz 环 = 32,000 个采样点。

**VAD（Voice Activity Detection，语音活动检测）。** 没人说话时挡住下游计算。Silero VAD 4.0（2024）在 CPU 上每 30 ms 帧耗时 <1 ms。`webrtcvad` 是更老的选择。

**流式 ASR。** 边收音频边吐部分转写的模型。Parakeet-CTC-0.6B 的流式模式（NeMo，2024）在 320 ms 延迟下做到 2–5% WER。Whisper-Streaming（Macháček et al., 2023）把 Whisper 分块，以约 2 s 延迟做准流式。

**打断（interruption）。** 用户在助手说话时开口，你必须 (a) 检测到 barge-in，(b) 停掉 TTS，(c) 丢弃 LLM 剩余输出。全部要在 100 ms 内完成，否则用户会觉得这是个聋了的助手。

**WebRTC Opus 传输。** 20 ms 帧、48 kHz、自适应码率 8–128 kbps。浏览器和移动端的标准。LiveKit、Daily.co、Pion 是 2026 年搭语音应用的常用组合。

**抖动缓冲（jitter buffer）。** 网络包会乱序 / 迟到。抖动缓冲负责重排和平滑；太小 → 听得见的空洞，太大 → 延迟。典型 60–80 ms。

> **Frame / chunk / window.** Real-time audio flows as fixed-size blocks. Common choice: 20 ms (320 samples at 16 kHz). Everything downstream must keep up with this cadence.
> **Ring buffer.** Fixed-size circular buffer. Producer thread writes new frames, consumer thread reads.
> **Interruption.** When the user speaks while the assistant is talking, you must (a) detect the barge-in, (b) stop the TTS, (c) discard the remaining LLM output. All within 100 ms, or the user perceives deaf assistant.
> **Jitter buffer.** Network packets arrive out of order / late. The jitter buffer reorders and smooths; too small → audible gaps, too large → latency. 60–80 ms typical.

---

### Common gotchas · 常见暗坑

- **线程争用。** Python 的 GIL + 大模型可能饿死音频线程。用 C 回调的音频库（sounddevice、PortAudio），别让 Python 待在热路径上。
- **采样率转换延迟。** 在流水线内部重采样会加 5–20 ms。要么提前（upfront）重采样，要么用零延迟重采样器（PolyPhase、`soxr_hq`）。
- **TTS 预热。** 再快的 TTS（比如 Kokoro）第一次请求也有 100–200 ms 热身。缓存模型，并在第一个真实轮次前用一次空跑把它暖起来。
- **回声消除。** 没有 AEC，TTS 输出会重新进麦克风，触发 ASR 去识别机器人自己的声音。WebRTC AEC3 是开源默认。

> **Thread contention.** Python's GIL + heavy models can starve the audio thread. Use a C-callback audio library (sounddevice, PortAudio) and keep Python off the hot path.
> **Sample-rate conversion latency.** Resampling inside the pipeline adds 5–20 ms. Either resample upfront or use a zero-latency resampler (PolyPhase, `soxr_hq`).
> **TTS priming.** Even fast TTS like Kokoro has a 100–200 ms warm-up on first request. Cache model + warm it with a dummy run before the first real turn.
> **Echo cancellation.** Without AEC, TTS output re-enters the mic and triggers ASR on the bot's own voice. WebRTC AEC3 is the open-source default.

```figure
nyquist-aliasing
```

---

## Build It · 动手造

### Step 1: ring buffer · 环形缓冲

```python
import collections

class RingBuffer:
    def __init__(self, capacity):
        self.buf = collections.deque(maxlen=capacity)
    def write(self, frame):
        self.buf.extend(frame)
    def read(self, n):
        return [self.buf.popleft() for _ in range(min(n, len(self.buf)))]
    def level(self):
        return len(self.buf)
```

容量决定最大缓冲延迟。16 kHz 下 32,000 个采样点 = 2 秒。

> Capacity determines max buffering latency. 32,000 samples at 16 kHz = 2 s.

### Step 2: VAD gate · VAD 门控

```python
def simple_energy_vad(frame, threshold=0.01):
    return sum(x * x for x in frame) / len(frame) > threshold ** 2
```

生产环境换成 Silero VAD：

```python
import torch
vad, _ = torch.hub.load("snakers4/silero-vad", "silero_vad")
is_speech = vad(torch.tensor(frame), 16000).item() > 0.5
```

> Replace with Silero VAD in production:

### Step 3: streaming ASR · 流式 ASR

```python
# Parakeet-CTC-0.6B streaming via NeMo
from nemo.collections.asr.models import EncDecCTCModelBPE
asr = EncDecCTCModelBPE.from_pretrained("nvidia/parakeet-ctc-0.6b")
# chunk_ms=320 ms, look_ahead_ms=80 ms
for chunk in audio_stream():
    partial_text = asr.transcribe_streaming(chunk)
    print(partial_text, end="\r")
```

### Step 4: interruption handler · 打断处理器

```python
class Dialog:
    def __init__(self):
        self.tts_task = None

    def on_user_speech(self, frame):
        if self.tts_task and not self.tts_task.done():
            self.tts_task.cancel()   # barge-in
        # then feed to streaming ASR

    def on_final_user_utterance(self, text):
        self.tts_task = asyncio.create_task(self.reply(text))

    async def reply(self, text):
        async for tts_chunk in llm_then_tts(text):
            speaker.write(tts_chunk)
```

成败在于异步 I/O 和可取消的 TTS 流。WebRTC 对 audio track 调 peerconnection.stop() 是标准做法。

> Hinges on async I/O and cancellable TTS streaming. WebRTC peerconnection.stop() on the audio track is the canonical way.

---

## Use It · 实战用法

2026 年的选型组合：

| 层 | 选择 |
|-------|------|
| 传输 | LiveKit (WebRTC) 或 Pion (Go) |
| VAD | Silero VAD 4.0 |
| 流式 ASR | Parakeet-CTC-0.6B 或 Whisper-Streaming |
| LLM 首 token | Groq、Cerebras、vLLM-streaming |
| 流式 TTS | Kokoro 或 ElevenLabs Turbo v2.5 |
| 回声消除 | WebRTC AEC3 |
| 端到端原生 | OpenAI Realtime API 或 Moshi |

> The 2026 stack:

---

## Pitfalls · 常见的坑

- **为保险起见缓冲 500 ms。** 缓冲*就是*你的延迟下限。砍掉它。
- **不绑线程。** 音频回调跑在优先级比 UI 还低的线程上 = 高负载时出爆音。
- **TTS 块太小。** 小于 200 ms 的块会让声码器瑕疵变得可闻。320 ms 的块才是甜点。
- **没有抖动缓冲。** 真实网络是有抖动的；没有平滑就会啪啪作响。
- **一次性的错误处理。** 音频流水线必须防崩。一个异常就能杀死整个会话。

> **Buffering 500 ms to be safe.** The buffer *is* your latency floor. Shrink it.
> **Not pinning threads.** Audio callback on a priority-lower-than-UI thread = glitches under load.
> **TTS chunks too small.** Sub-200 ms chunks make vocoder artifacts audible. 320 ms chunks are the sweet spot.
> **No jitter buffer.** Real networks are jittery; without smoothing you get pops.
> **Single-shot error handling.** Audio pipelines must be crash-proof. One exception kills the session.

---

## Ship It · 交付

保存为 `outputs/skill-realtime-designer.md`：设计一条实时音频流水线，给出每个阶段具体的延迟预算。

> Save as `outputs/skill-realtime-designer.md`. Design a real-time audio pipeline with concrete latency budgets per stage.

---

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。模拟环形缓冲 + 能量 VAD；为一段假的 10 秒流打印各阶段延迟。
2. **中等。** 用 `sounddevice` 搭一个直通环路，以 20 ms 帧处理你的麦克风，并在每帧打印 VAD 状态。
3. **困难。** 用 `aiortc` 搭一个全双工回声测试：浏览器 → WebRTC → Python → WebRTC → 浏览器。用 1 kHz 脉冲测量玻璃到玻璃（glass-to-glass）延迟。

> 1. **Easy.** Run `code/main.py`. Simulates a ring buffer + energy VAD; prints stage latencies for a fake 10-second stream.
> 2. **Medium.** Using `sounddevice`, build a passthrough loop that processes your mic in 20 ms frames and prints VAD state at each frame.
> 3. **Hard.** Build a full duplex echo test with `aiortc`: browser → WebRTC → Python → WebRTC → browser. Measure glass-to-glass latency with a 1 kHz pulse.

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Ring buffer（环形缓冲） | 循环队列 | 固定大小、无锁（或 SPSC 加锁）的音频帧 FIFO。 |
| VAD | 静音门 | 标记语音 / 非语音的模型或启发式方法。 |
| Streaming ASR | 实时 STT | 音频到达时吐出部分文本；前瞻有界。 |
| Jitter buffer（抖动缓冲） | 网络平滑器 | 重排乱序包的队列；典型 60–80 ms。 |
| AEC | 回声消除 | 减掉扬声器到麦克风的反馈路径。 |
| Barge-in | 用户打断 | 系统在 TTS 播放中检测到用户说话；必须取消播放。 |
| Full duplex（全双工） | 双方同时说 | 用户和机器人可以同时说话；Moshi 是全双工。 |

---

## Further Reading · 延伸阅读

- [Macháček et al. (2023). Whisper-Streaming](https://arxiv.org/abs/2307.14743) —— 分块准流式 Whisper。
- [Kyutai (2024). Moshi](https://kyutai.org/Moshi.pdf) —— 200 ms 延迟的全双工。
- [LiveKit Agents framework (2024)](https://docs.livekit.io/agents/) —— 生产级音频智能体编排。
- [Silero VAD repo](https://github.com/snakers4/silero-vad) —— 亚毫秒级 VAD，Apache 2.0。
- [WebRTC AEC3 paper](https://webrtc.googlesource.com/src/+/main/modules/audio_processing/aec3/) —— 开源实现的回声消除。
