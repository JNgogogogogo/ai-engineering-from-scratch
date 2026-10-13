# Build a Voice Assistant Pipeline — The Phase 6 Capstone · 搭建语音助手流水线——Phase 6 毕业项目

> Everything from lessons 01-11, stitched together. Build a voice assistant that listens, reasons, and talks back. In 2026 that is a solved engineering problem, not a research problem — but the integration details decide whether it ships.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 6 · 04, 05, 06, 07, 11; Phase 11 · 09 (Function Calling); Phase 14 · 01 (Agent Loop)
**Time:** ~120 minutes

---

## The Problem · 问题在哪

搭建一个端到端的助手：

1. 采集麦克风输入（16 kHz 单声道）。
2. 检测用户语音的开始 / 结束。
3. 流式转写。
4. 把转写交给能调用工具（timer、weather、calendar）的 LLM。
5. 把 LLM 文本流式送给 TTS。
6. 把音频播放给用户。
7. 用户在回答中途打断时停下来。

延迟目标：在笔记本 CPU 上，用户说完话后 800 ms 内送出第一个 TTS 音频字节。质量目标：不漏词、静音上不幻觉出字幕、不泄漏声音克隆、没有提示注入（prompt injection）得逞。

> Build an end-to-end assistant:
> Latency target: first TTS audio byte within 800 ms of the user finishing their utterance on a laptop CPU. Quality target: no missed words, no hallucinated subtitles on silence, no voice cloning leakage, no prompt injection success.

---

## The Concept · 概念

![语音助手流水线：麦克风 → VAD → STT → LLM+工具 → TTS → 扬声器](../assets/voice-assistant.svg)

### The seven components · 七个组件

1. **音频采集。** 麦克风 → 16 kHz 单声道 → 20 ms 块。Python 里通常用 `sounddevice`，生产环境用原生 AudioUnit/ALSA/WASAPI。
2. **VAD（第 11 课）。** Silero VAD，阈值 0.5，最短语音 250 ms，静音悬挂（hang-over）500 ms。负责发出「开始」和「结束」信号。
3. **流式 STT（第 4-5 课）。** Whisper-streaming、Parakeet-TDT 或 Deepgram Nova-3（API）。部分 + 最终转写。
4. **带工具调用的 LLM。** GPT-4o / Claude 3.5 / Gemini 2.5 Flash。工具用 JSON schema 描述。token 流式输出。
5. **流式 TTS（第 7 课）。** Kokoro-82M（最快的开源）或 Cartesia Sonic（商业）。攒够 20 个 LLM token 就启动 TTS。
6. **播放。** 扬声器输出；低带宽网络用 opus 编码。
7. **打断处理器。** 如果 TTS 播放期间 VAD 触发，停止播放、取消 LLM、重启 STT。

> 1. **Audio capture.** Mic → 16 kHz mono → 20 ms chunks. Usually `sounddevice` in Python or native AudioUnit/ALSA/WASAPI in production.
> 2. **VAD (Lesson 11).** Silero VAD @ threshold 0.5, min speech 250 ms, silence hang-over 500 ms. Signals "start" and "end."
> 5. **Streaming TTS (Lesson 7).** Kokoro-82M (fastest open) or Cartesia Sonic (commercial). Start TTS after 20 LLM tokens.
> 7. **Interruption handler.** If VAD fires during TTS playback, stop playback, cancel LLM, restart STT.

---

### The three failure modes you will hit · 你一定会遇到的三种失败模式

1. **第一个词被剪掉。** VAD 晚了半拍。用户的「hey」丢了。起始阈值设 0.3，不是 0.5。
2. **回答中途被打断后的混乱。** 用户打断后 LLM 还在生成；助手盖过用户说话。把 VAD → 取消 LLM 这条线接上。
3. **静音幻觉。** Whisper 在无声的预热帧上输出 "Thanks for watching"。永远加 VAD 门控。

> 1. **First-word clip.** VAD starts a beat too late. User's "hey" is missing. Start threshold at 0.3, not 0.5.
> 2. **Mid-response interrupt confusion.** LLM keeps generating after user interrupts; assistant talks over user. Wire VAD → cancel-LLM.
> 3. **Silence hallucination.** Whisper outputs "Thanks for watching" on the silent warm-up frames. Always VAD-gate.

---

### 2026 production reference stacks · 2026 年生产参考技术栈

| 技术栈 | 延迟 | 许可 | 备注 |
|-------|---------|---------|-------|
| LiveKit + Deepgram + GPT-4o + Cartesia | 350-500 ms | 商业 API | 2026 年的行业标准 |
| Pipecat + Whisper-streaming + GPT-4o + Kokoro | 500-800 ms | 大部分开源 | 对 DIY 友好 |
| Moshi（全双工） | 200-300 ms | CC-BY 4.0 | 单模型；不同架构，第 15 课 |
| Vapi / Retell（托管） | 300-500 ms | 商业 | 上线最快；定制受限 |
| Whisper.cpp + llama.cpp + Kokoro-ONNX | 离线 | 开源 | 隐私 / 边缘 |

```figure
v4-voice-latency
```

---

## Build It · 动手造

### Step 1: mic capture with chunking (pseudocode) · 带分块的麦克风采集（伪代码）

```python
import sounddevice as sd

def mic_stream(chunk_ms=20, sr=16000):
    q = queue.Queue()
    def cb(indata, frames, time, status):
        q.put(indata.copy().flatten())
    with sd.InputStream(channels=1, samplerate=sr, blocksize=int(sr * chunk_ms/1000), callback=cb):
        while True:
            yield q.get()
```

### Step 2: VAD-gated turn capture · VAD 门控的轮次采集

```python
def capture_turn(stream, vad, pre_roll_ms=300, silence_ms=500):
    buf, pre, triggered = [], collections.deque(maxlen=pre_roll_ms // 20), False
    silent = 0
    for chunk in stream:
        pre.append(chunk)
        if vad(chunk):
            if not triggered:
                buf = list(pre)
                triggered = True
            buf.append(chunk)
            silent = 0
        elif triggered:
            silent += 20
            buf.append(chunk)
            if silent >= silence_ms:
                return b"".join(buf)
```

### Step 3: streaming STT → LLM → TTS · 流式 STT → LLM → TTS

```python
async def turn(audio_bytes):
    transcript = await stt.transcribe(audio_bytes)
    async for token in llm.stream(transcript):
        async for audio in tts.stream(token):
            await speaker.play(audio)
```

### Step 4: tool calling inside the LLM loop · LLM 循环内的工具调用

```python
tools = [
    {"name": "get_weather", "parameters": {"location": "string"}},
    {"name": "set_timer", "parameters": {"seconds": "int"}},
]

async for chunk in llm.stream(user_text, tools=tools):
    if chunk.type == "tool_call":
        result = dispatch(chunk.name, chunk.args)
        continue_streaming(result)
    if chunk.type == "text":
        await tts.stream(chunk.text)
```

### Step 5: interruption handling · 打断处理

```python
tts_task = asyncio.create_task(tts_loop())
while True:
    chunk = await mic.get()
    if vad(chunk):
        tts_task.cancel()
        await speaker.stop()
        await new_turn()
        break
```

---

## Use It · 实战用法

`code/main.py` 里有一个可运行的模拟，用桩（stub）模型把七个组件全部接了起来，没有硬件也能看清流水线的形状。要真正实现，把桩换成：

- `silero-vad`（`pip install silero-vad`）
- `deepgram-sdk` 或 `openai-whisper`
- `openai`（`gpt-4o`）或 `anthropic`
- `kokoro` 或 `cartesia`
- I/O 用 `sounddevice`

> See `code/main.py` for a runnable simulation that wires all seven components with stub models, so you can see the pipeline shape even without hardware. For a real implementation, swap stubs with:

---

## Pitfalls · 常见的坑

- **永久记录 PII。** 完整轮次的音频在大多数司法辖区都属于 PII。保留 30 天，静态加密存储。
- **没有 barge-in。** 用户一定会打断。你的助手必须学会闭嘴。
- **阻塞式 TTS。** 同步 TTS 会卡死事件循环。用异步或独立线程。
- **工具调用没有错误处理。** 工具会挂。必须把错误交还给 LLM + 重试一次，然后优雅降级。
- **过激的幻觉过滤器。** 过滤太狠，助手反复说「I can't help with that」；过滤太松，它什么都敢说。在留出集上校准。
- **没有唤醒词选项。** 常驻收音是隐私负债。加一个唤醒词门（Porcupine 或 openWakeWord）。

> **Logging PII forever.** Full-turn audio is PII in most jurisdictions. 30-day retention, encrypted at rest.
> **No barge-in.** Users will interrupt. Your assistant must stop talking.
> **TTS that blocks.** Synchronous TTS blocks the event loop. Use async or a separate thread.
> **No tool-call error handling.** Tools fail. LLM must get back the error + retry once, then gracefully degrade.
> **Overzealous hallucination filters.** Over-filter and the assistant repeats "I can't help with that." Under-filter and it says anything. Calibrate on a held-out set.
> **No wake-word option.** Always-listening is a privacy liability. Add a wake-word gate (Porcupine or openWakeWord).

---

## Ship It · 交付

保存为 `outputs/skill-voice-assistant-architect.md`：给定预算 + 规模 + 语言 + 合规约束，产出一份完整的技术栈规格。

> Save as `outputs/skill-voice-assistant-architect.md`. Given budget + scale + language + compliance constraints, produce a full stack spec.

---

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。它用桩模块端到端模拟完整的一轮对话，并打印各阶段延迟。
2. **中等。** 把 STT 桩换成跑在预录 `.wav` 上的真实 Whisper 模型。测量 WER 和端到端延迟。
3. **困难。** 加上工具调用：实现 `get_weather`（任意 API）和 `set_timer`。让 LLM 走工具链路，并验证当用户说 "set a 5 minute timer" 时正确的函数被触发、语音回复里也确认了它。

> 1. **Easy.** Run `code/main.py`. It simulates one full turn end-to-end with stub modules and prints per-stage latency.
> 2. **Medium.** Replace the STT stub with a real Whisper model on a pre-recorded `.wav`. Measure WER and end-to-end latency.
> 3. **Hard.** Add tool calling: implement `get_weather` (any API) and `set_timer`. Route the LLM through the tools and verify that when the user says "set a 5 minute timer" the right function fires and the spoken reply confirms it.

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Turn（轮次） | 一轮用户 + 助手往返 | 一次 VAD 界定的用户语音 + 一次 LLM-TTS 响应。 |
| Barge-in | 打断 | 助手说话时用户开口；助手停止。 |
| Wake word（唤醒词） | "Hey assistant"（嗨，助手） | 短关键词检测器；Porcupine、Snowboy、openWakeWord。 |
| End-pointing（端点检测） | 判定轮次结束 | VAD + 最短静音判定，确认用户说完了。 |
| Pre-roll（预卷缓冲） | 语音前的缓冲 | VAD 触发前保留 200-400 ms 音频，避免剪掉第一个词。 |
| Tool call（工具调用） | 函数调用 | LLM 吐出 JSON；运行时分发；结果在循环内回灌。 |

---

## Further Reading · 延伸阅读

- [LiveKit — voice agent quickstart](https://docs.livekit.io/agents/) —— 生产级参考。
- [Pipecat — voice agent examples](https://github.com/pipecat-ai/pipecat) —— 对 DIY 友好的框架。
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime) —— 托管的语音原生路线。
- [Kyutai Moshi](https://github.com/kyutai-labs/moshi) —— 全双工参考（第 15 课）。
- [Porcupine wake-word](https://picovoice.ai/products/porcupine/) —— 唤醒词门控。
- [Anthropic — tool use guide](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) —— LLM 函数调用。
