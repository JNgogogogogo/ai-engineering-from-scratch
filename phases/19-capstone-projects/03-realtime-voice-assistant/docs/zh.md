# Capstone 03 — Real-Time Voice Assistant (ASR to LLM to TTS) · 实时语音助手（从 ASR 到 LLM 到 TTS）

> 一个手感对的语音助手：端到端延迟低于 800ms，知道你什么时候说完了，能处理插话（barge-in），调用工具时也不卡顿。Retell、Vapi、LiveKit Agents 和 Pipecat 在 2026 年都达到了这条线。它们用同一个形状：流式 ASR、轮次检测器（turn-detector）、流式 LLM、流式 TTS，全部通过 WebRTC 连接，每一跳都卡着激进的延迟预算。造一个，测 WER、MOS 和误切断率，再放到丢包环境下运行。

> A voice agent that feels right has end-to-end latency under 800ms, knows when you have stopped talking, handles barge-in, and can call a tool without stalling. Retell, Vapi, LiveKit Agents, and Pipecat all hit this bar in 2026. They do it with the same shape: a streaming ASR, a turn-detector, a streaming LLM, and a streaming TTS, all wired through WebRTC with aggressive latency budgets at every hop. Build one, measure WER and MOS and false-cutoff rate, and run it under packet loss.

**类型（Type）:** 毕业项目（Capstone）
**语言（Languages）:** Python（agent + 管线），TypeScript（web 客户端）
**先修（Prerequisites）:** Phase 6（语音与音频）、Phase 7（transformers）、Phase 11（LLM 工程）、Phase 13（工具）、Phase 14（智能体 agent）、Phase 17（基础设施）
**实践阶段（Phases exercised）:** P6 · P7 · P11 · P13 · P14 · P17
**时间（Time）:** 30 小时

## Problem · 问题

语音是 2025-2026 年演进最快的 AI 交互品类。技术天花板每个季度都在下探。OpenAI Realtime API、Gemini 2.5 Live、Cartesia Sonic-2、ElevenLabs Flash v3、LiveKit Agents 1.0 和 Pipecat 0.0.70 都把 sub-800ms 的首音频输出（first-audio-out）带进了射程。门槛不只是延迟，而是交互手感：不切断用户、不被用户切断、从句中被打断中恢复、在对话中途调用工具而不卡住音频、在抖动的移动网络下活下来。

把三个 REST 调用串起来到不了那里。架构必须是端到端流水线化的流式。亲手造它，失败模式才会显形：一个为电话音频调校的 VAD 被背景电视触发；一个轮次检测器在等一个永远不会来的标点；一个先缓冲 400ms 才肯出声的 TTS。这个毕业项目（capstone）就是在负载下一项项修掉它们，并发布一份延迟与质量报告。

> Voice has been the fastest-moving AI UX category of 2025-2026. ... The bar is not latency alone. It is the interaction feel: not cutting the user off, not getting cut off, recovering from a mid-sentence interruption, calling a tool mid-conversation without stalling the audio, surviving jittery mobile networks. ... You cannot get there by stitching three REST calls. The architecture is pipelined streaming end to end. ... The capstone is to fix these one at a time under load and publish a latency-and-quality report.

## Concept · 概念

管线有五个流式阶段：**音频输入**（来自浏览器或 PSTN 的 WebRTC）、**ASR**（Deepgram Nova-3 或 faster-whisper 的流式部分转写）、**轮次检测**（VAD 加一个小型轮次检测模型，读取部分转写寻找「话说完了」的线索）、**LLM**（一旦判定轮次完成就开始流式吐 token）、**TTS**（在首个 LLM token 之后约 200ms 内流式输出音频）。

三个横切关注点。**插话（barge-in）**：当用户在智能体说话时开口，TTS 立即取消，ASR 立即接管。**工具使用**：对话中途的函数调用（天气、日历）必须在旁路信道上运行，不阻塞音频；若延迟超过 300ms，智能体先预填一句确认语（"one second..."）。**背压（backpressure）**：丢包时，部分转写被扣住，VAD 调高语音门限，智能体避免在未被确认的消息上继续说话。

测量门槛是定量的。Hamming VAD 基准、15 dB SNR 下 WER（词错误率）低于 8%。100 通实测通话上，首音频输出 p50 低于 800ms。误切断率（false-cutoff rate）低于 3%。TTS 的 MOS 高于 4.2。单台 g5.xlarge 上跑 50 路并发。这些数字就是交付物。

> The pipeline has five streaming stages: **audio in** (WebRTC from browser or PSTN), **ASR** (streaming partial transcripts from Deepgram Nova-3 or faster-whisper), **turn detection** (VAD plus a small turn-detector model that reads partial transcripts for completion cues), **LLM** (streaming tokens as soon as the turn is judged complete), **TTS** (streaming audio out within ~200ms of the first LLM token). ... **Barge-in**: when the user starts speaking while the agent is speaking, the TTS cancels and the ASR picks up immediately. ... **Backpressure**: under packet loss, partial transcripts are held, VAD raises the speech-gate threshold, and the agent avoids speaking over an unacknowledged message. ... WER under 8% on the Hamming VAD benchmark at 15 dB SNR. First-audio-out p50 under 800ms on 100 measured calls. False-cutoff rate under 3%. MOS above 4.2 on TTS. 50 concurrent calls on a single g5.xlarge. These numbers are the deliverable.

## Architecture · 架构

```
browser / Twilio PSTN
        |
        v
   WebRTC / SIP edge
        |
        v
  LiveKit Agents 1.0  (or Pipecat 0.0.70)
        |
   +----+--------------+--------------+-----------------+
   |                   |              |                 |
   v                   v              v                 v
  ASR              VAD v5         turn-detector     side-channel
(Deepgram         (Silero)          (LiveKit)        tools
 Nova-3 /         speech-gate    completion score    (weather,
 Whisper-v3)      per 20ms        on partials        calendar)
   |                   |              |
   +--------+----------+--------------+
            v
        LLM (streaming)
     GPT-4o-realtime / Gemini 2.5 Flash /
     cascaded Claude Haiku 4.5
            |
            v
        TTS streaming
     Cartesia Sonic-2 / ElevenLabs Flash v3
            |
            v
     audio back to caller
            |
            v
   OpenTelemetry voice traces -> Langfuse
```

## Stack · 技术栈

- 传输：LiveKit Agents 1.0（WebRTC）加 Twilio PSTN 网关；Pipecat 0.0.70 作为备选框架
- ASR：Deepgram Nova-3（流式，sub-300ms 首个部分转写）或自托管 faster-whisper Whisper-v3-turbo
- VAD：Silero VAD v5 加 LiveKit turn-detector（读取部分转写的小型 transformer）
- LLM：紧集成用 OpenAI GPT-4o-realtime，Gemini 2.5 Flash Live，或级联的 Claude Haiku 4.5（流式补全，音频走独立通路）
- TTS：Cartesia Sonic-2（首字节最低）、ElevenLabs Flash v3，或开源 Orpheus 用于自托管
- 工具：FastMCP 旁路信道跑天气/日历/预订；工具超过 300ms 时智能体先发填充语（filler）
- 可观测性：OpenTelemetry 语音 span，带音频回放的 Langfuse 语音 trace
- 部署：单台 g5.xlarge（24GB VRAM）跑自托管 Whisper + Orpheus；追求最低延迟用托管 API

> - Transport: LiveKit Agents 1.0 (WebRTC) plus Twilio PSTN gateway; Pipecat 0.0.70 as the alternate framework
> - ASR: Deepgram Nova-3 (streaming, sub-300ms first partial) or faster-whisper Whisper-v3-turbo self-hosted
> - VAD: Silero VAD v5 plus the LiveKit turn-detector (small transformer that reads partial transcripts)
> - LLM: OpenAI GPT-4o-realtime for tight integration, Gemini 2.5 Flash Live, or cascaded Claude Haiku 4.5 (streaming completions, separate audio path)
> - TTS: Cartesia Sonic-2 (lowest first-byte), ElevenLabs Flash v3, or open-source Orpheus for self-host
> - Tools: FastMCP side-channel for weather/calendar/booking; agent pre-emits filler if tool takes >300ms
> - Observability: OpenTelemetry voice spans, Langfuse voice traces with audio replay
> - Deployment: single g5.xlarge (24GB VRAM) for self-hosted Whisper + Orpheus; hosted APIs for lowest latency

```figure
ce-voice-latency
```

## Build It · 动手造

1. **WebRTC 会话。** 起一个 LiveKit 房间和一个推流麦克风音频的 web 客户端。在服务端挂上一个加入房间的 agent worker。

2. **ASR 流式。** 把 20ms PCM 帧喂给 Deepgram Nova-3（或 GPU 上的 faster-whisper）。订阅部分转写与最终转写。记录每个部分转写的延迟。

3. **VAD 与轮次检测器。** 在帧流上跑 Silero VAD v5。语音结束事件触发时，用最新的部分转写跑 LiveKit turn-detector。只有当 VAD 判定静音满 500ms 且 turn-detector 完成分数 > 0.6 时，才提交「轮次完成」。

4. **LLM 流。** 轮次完成后，带着运行中的对话加上最终转写发起 LLM 调用。流式吐出 token。拿到第一个 token 就交给 TTS。

5. **TTS 流。** Cartesia Sonic-2 流式返回音频块。第一块音频必须在首个 LLM token 之后 200ms 内离开服务器。音频块推给 LiveKit 房间；客户端经 WebRTC jitter buffer 播放。

6. **插话（barge-in）。** 当 VAD 在 TTS 播放中检测到新的用户语音，立即取消 TTS 流，丢弃剩余 LLM 输出，重新武装 ASR。发布一个 `tts_canceled` span。

7. **工具旁路信道。** 把天气和日历注册为函数调用工具。被调用时并发发起调用；若 300ms 内未返回，让 LLM 先发一句 "one second, let me check" 作为填充语；工具返回后继续。

8. **评估 harness。** 录 100 通通话。计算 WER（对照留出转写）、误切断率（用户说到一半时 TTS 被取消）、首音频输出 p50、TTS MOS（人工或 NISQA），以及抖动丢包测试（丢 3% 数据包）。

9. **负载测试。** 用合成呼叫方在单台 g5.xlarge 上打 50 路并发。测持续的首音频输出 p95。

> **WebRTC session.** Stand up a LiveKit room and a web client that streams microphone audio. On the server, attach an agent worker that joins the room. ... **VAD and turn detector.** Run Silero VAD v5 on the frame stream. Only commit to "turn complete" when VAD says silence for 500ms and the turn-detector scores completion > 0.6. ... **Barge-in.** When VAD detects new user speech while TTS is playing, cancel the TTS stream immediately, drop the remaining LLM output, and re-arm the ASR. Publish a `tts_canceled` span. ... **Tool side channel.** Register weather and calendar as function-calling tools. When invoked, fire the call concurrently; if it does not resolve within 300ms, have the LLM emit "one second, let me check" as a filler; resume once the tool returns. ... **Eval harness.** Record 100 calls. Compute WER (against a held-out transcript), false-cutoff rate (TTS cancelled while user was mid-sentence), first-audio-out p50, TTS MOS (human or NISQA), and a jitter-loss test (drop 3% of packets).

## Use It · 实战用法

```
caller: "what is the weather in tokyo tomorrow"
[asr  ] partial @280ms: "what is the"
[asr  ] partial @540ms: "what is the weather"
[turn ] completion score 0.82 at @820ms; commit
[llm  ] first token @960ms
[tool ] weather.tokyo tomorrow -> 68/52 partly cloudy @1140ms
[tts  ] first audio-out @1040ms: "Tokyo tomorrow will be partly cloudy..."
turn latency: 1040ms user-stop -> audio-out
```

## Ship It · 交付

`outputs/skill-voice-agent.md` 是交付物。给定一个领域（客服、日程或自助点单终端），它搭起一个 LiveKit 智能体，ASR/VAD/LLM/TTS 管线按测量门槛调优。评分标准：

| 权重 | 标准 | 如何衡量 |
|:-:|---|---|
| 25 | 端到端延迟 | 100 通录音通话上首音频输出 p50 低于 800ms |
| 20 | 轮次交替质量 | Hamming VAD 基准上误切断率低于 3% |
| 20 | 工具使用正确性 | 对话中途的工具调用返回正确数据且不卡音频 |
| 20 | 丢包下的可靠性 | 注入 3% 丢包后的 WER 与轮次交替稳定性 |
| 15 | 评估 harness 完整度 | 配置公开、测量可复现 |
| **100** | | |

> `outputs/skill-voice-agent.md` is the deliverable. Given a domain (customer support, scheduling, or kiosk), it stands up a LiveKit agent with the ASR/VAD/LLM/TTS pipeline tuned to the measurement bar.

## Exercises · 练习

1. 把 Deepgram Nova-3 换成 g5.xlarge 上的 faster-whisper v3 turbo。测延迟与 WER 差距。找出 CPU-vs-GPU 决策在哪些环节最要紧。

2. 加一个打断仲裁策略：用户在工具调用期间插话时智能体怎么办？比较三种策略（硬取消、等工具完成再停、下一轮排队）。

3. 跑一个对抗性轮次检测测试：让用户在句子中间长时间停顿。调 VAD 静音阈值与 turn-detector 分数阈值，在不越过 900ms 的前提下把误切断降到最低。

4. 经 Twilio 把同一个智能体部署到 PSTN。对比 PSTN 与 WebRTC 的首音频输出。解释 jitter buffer 与编解码的差异。

5. 为非英语语言（日语、西班牙语）加语音活动检测。测 Silero VAD v5 的误触发率，并与语言特定微调版本对比。

> Swap Deepgram Nova-3 for faster-whisper v3 turbo on a g5.xlarge. Measure the latency and WER gap. ... Add an interruption-arbitration policy: what does the agent do when the user barges in during a tool call? Compare three policies (hard cancel, finish-tool-then-stop, queue next turn). ... Run an adversarial turn-detector test: give the user long pauses mid-sentence. Tune the VAD silence threshold and the turn-detector score threshold for lowest false-cutoff without blowing past 900ms. ... Deploy the same agent on PSTN via Twilio. Compare PSTN first-audio-out to WebRTC. Explain the jitter-buffer and codec differences. ... Add voice activity detection for non-English languages (Japanese, Spanish). Measure the Silero VAD v5 false-trigger rate versus language-specific fine-tunes.

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|------------------------|
| Turn detection（轮次检测） | 「话说完了」 | 给定 VAD 静音与部分转写，判定用户已说完的分类器 |
| Barge-in（插话） | 「打断处理」 | VAD 检测到新的用户语音时，在 TTS 播放中途取消它 |
| First-audio-out（首音频输出） | 「延迟」 | 从用户停止说话到首个音频包离开服务器的时长 |
| VAD | 「语音门」 | 把音频帧分类为语音/静音的模型；Silero VAD v5 是 2026 年默认 |
| Jitter buffer（抖动缓冲） | 「音频平滑」 | 客户端短暂扣住数据包以吸收网络波动的缓冲区 |
| Filler（填充语） | 「确认词」 | 工具太慢时智能体发出、用来避免冷场的短语 |
| MOS | 「平均意见分」 | 语音感知质量评分；NISQA 是其自动化代理 |

## Further Reading · 延伸阅读

- [LiveKit Agents 1.0](https://github.com/livekit/agents) — 参考 WebRTC 智能体框架
- [Pipecat](https://github.com/pipecat-ai/pipecat) — 备选的 Python 优先流式智能体框架
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime) — 集成语音模型的参考
- [Deepgram Nova-3 documentation](https://developers.deepgram.com/docs) — 流式 ASR 参考
- [Silero VAD v5](https://github.com/snakers4/silero-vad) — VAD 参考模型
- [Cartesia Sonic-2](https://docs.cartesia.ai) — 低延迟 TTS 参考
- [Retell AI architecture](https://docs.retellai.com) — 生产级语音智能体架构
- [Vapi.ai production stack](https://docs.vapi.ai) — 另一个生产级参考
