# Voice Agents: Pipecat and LiveKit · 语音代理：Pipecat 与 LiveKit

> 到 2026 年，语音代理已经是正式的生产品类。Pipecat 给你一条 Python 的帧（frame）流水线（VAD → STT → LLM → TTS → 传输）。LiveKit Agents 通过 WebRTC 把 AI 模型桥接到用户。高端技术栈的生产延迟目标落在端到端 450–600ms。
>
> Voice agents are a first-class production category in 2026. Pipecat gives you a Python frame-based pipeline (VAD → STT → LLM → TTS → transport). LiveKit Agents bridges AI models to users over WebRTC. Production latency targets land at 450–600ms end-to-end for premium stacks.

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 12 (Workflow Patterns)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 描述 Pipecat 的帧流水线：DOWNSTREAM（源→汇）与 UPSTREAM（控制）。
- 说出经典语音流水线的各个阶段，以及 Pipecat 支持哪些传输层。
- 解释 LiveKit Agents 的两个语音 agent 类（MultimodalAgent、VoicePipelineAgent）及各自适用的场景。
- 总结 2026 年的生产延迟预期，以及它们如何决定架构选择。

> Describe Pipecat's frame-based pipeline: DOWNSTREAM (source→sink) and UPSTREAM (control).
> Name the canonical voice pipeline stages and which transports Pipecat supports.
> Explain LiveKit Agents' two voice agent classes (MultimodalAgent, VoicePipelineAgent) and when each fits.
> Summarize 2026 production latency expectations and how they drive architecture choices.

## The Problem · 问题在哪

语音代理不是「文本循环外加一个 TTS」。延迟预算残忍（约 600ms），部分音频（partial audio）是常态，轮次检测本身是个模型，传输层从电话 SIP 一直到 WebRTC。要么自己搭帧流水线（Pipecat），要么靠平台（LiveKit）。

> Voice agents are not a text loop with TTS bolted on. Latency budgets are brutal (~600ms), partial audio is the default, turn detection is a model, and transports range from telephony SIP to WebRTC. Either you build a frame-based pipeline (Pipecat) or you lean on a platform (LiveKit).

## The Concept · 概念

### Pipecat (pipecat-ai/pipecat) · Pipecat

- Python 帧式流水线框架。
- `Frame` → `FrameProcessor` 链。
- 两个流向：
  - **DOWNSTREAM** —— 源 → 汇（音频进，TTS 出）。
  - **UPSTREAM** —— 反馈与控制（取消、指标、打断插话 barge-in）。
- `PipelineTask` 用事件（`on_pipeline_started`、`on_pipeline_finished`、`on_idle_timeout`）管理生命周期，并用 observers 接指标/追踪/RTVI。

> - Python frame-based pipeline framework.
> - `Frame` → `FrameProcessor` chain.
> - Two flow directions:
>   - **DOWNSTREAM** — source → sink (audio in, TTS out).
>   - **UPSTREAM** — feedback and control (cancellation, metrics, barge-in).
> - `PipelineTask` manages lifecycle with events (`on_pipeline_started`, `on_pipeline_finished`, `on_idle_timeout`) and observers for metrics/tracing/RTVI.

典型流水线：

```
VAD (Silero) → STT → LLM (context alternates user/assistant) → TTS → transport
```

> Typical pipeline:

传输层：Daily、LiveKit、SmallWebRTCTransport、FastAPI WebSocket、WhatsApp。

> Transports: Daily, LiveKit, SmallWebRTCTransport, FastAPI WebSocket, WhatsApp.

Pipecat Flows 增加了结构化对话（状态机）。Pipecat Cloud 是托管运行时。

> Pipecat Flows adds structured conversations (state machines). Pipecat Cloud is the managed runtime.

### LiveKit Agents (livekit/agents) · LiveKit Agents

- 通过 WebRTC 把 AI 模型桥接到用户。
- 关键概念：`Agent`、`AgentSession`、`entrypoint`、`AgentServer`。
- 两个语音 agent 类：
  - **MultimodalAgent** —— 经 OpenAI Realtime 或等价物直连音频。
  - **VoicePipelineAgent** —— STT → LLM → TTS 级联；提供文本层的控制。
- 用 transformer 模型做语义轮次检测（semantic turn detection）。
- 原生 MCP 集成。
- 经 SIP 接电话网络。
- 通过 LiveKit Inference 可用 50+ 个模型且无需 API key；插件再加 200+。

> - Bridges AI models to users over WebRTC.
> - Key concepts: `Agent`, `AgentSession`, `entrypoint`, `AgentServer`.
> - Two voice agent classes:
>   - **MultimodalAgent** — direct audio via OpenAI Realtime or equivalent.
>   - **VoicePipelineAgent** — STT → LLM → TTS cascade; gives text-level control.
> - Semantic turn detection via a transformer model.
> - Native MCP integration.
> - Telephony via SIP.
> - 50+ models with no API keys via LiveKit Inference; 200+ more via plugins.

### Commercial platforms · 商业平台

Vapi（优化过的高端技术栈约 450–600ms）和 Retell（180 通测试电话端到端约 600ms）在这些组件之上构建。当你想要一套托管语音栈、又不想养 WebRTC 团队时，就选平台。

> Vapi (~450–600ms on an optimized premium stack) and Retell (~600ms end-to-end across 180 test calls) build on top of these. Pick a platform when you want a managed voice stack without a WebRTC team.

### Where this pattern goes wrong · 这个模式的常见坑

- **不处理 barge-in。** 用户打断了；agent 还在说。Pipecat 里需要 UPSTREAM 取消帧，LiveKit 里要有等价机制。
- **无视 STT 置信度。** 低置信度的转写被当成圣旨喂给 LLM。要么按置信度设门禁，要么请求用户确认。
- **TTS 句中截断。** 流水线在半句话时取消，TTS 得知道这件事，否则就得切音频。
- **无视延迟预算。** 每个组件都加 50–200ms。上线前把整条链加一遍。

> - **No barge-in handling.** User interrupts; agent keeps talking. Requires UPSTREAM cancel frames in Pipecat, equivalent in LiveKit.
> - **STT confidence ignored.** Low-confidence transcripts fed to the LLM as if gospel. Gate on confidence or request confirmation.
> - **TTS mid-sentence cutoff.** When the pipeline cancels mid-utterance, TTS needs to know or cut audio.
> - **Latency budget ignored.** Every component adds 50–200ms. Sum your chain before shipping.

### Typical 2026 latencies · 2026 年的典型延迟

- VAD：20–60ms
- STT 部分结果：100–250ms
- LLM 首 token：150–400ms
- TTS 首段音频：100–200ms
- 传输 RTT：30–80ms

> - VAD: 20–60ms
> - STT partial: 100–250ms
> - LLM first token: 150–400ms
> - TTS first audio: 100–200ms
> - Transport RTT: 30–80ms

端到端 450–600ms 是高端水准。800–1200ms 是常态。超过 1500ms 用户就觉得坏了。

> End-to-end 450–600ms is premium. 800–1200ms is common. Anything > 1500ms feels broken.

```figure
voice-pipeline
```

## Build It · 动手造

`code/main.py` 是一个帧式玩具流水线，包含：

- `Frame` 类型（audio、transcript、text、tts_audio、control）。
- 带 `process(frame)` 的 `Processor` 接口。
- 一条五阶段流水线（VAD → STT → LLM → TTS → 传输），由脚本化的 processor 扮演。
- 一个 UPSTREAM 取消帧，演示 barge-in。

运行：

```
python3 code/main.py
```

> `code/main.py` is a frame-based toy pipeline with:
> - `Frame` types (audio, transcript, text, tts_audio, control).
> - `Processor` interface with `process(frame)`.
> - A five-stage pipeline (VAD → STT → LLM → TTS → transport) as scripted processors.
> - An UPSTREAM cancel frame to demonstrate barge-in.

追踪输出会展示正常流程，以及一次在半句话处停掉 TTS 的 barge-in 取消。

> The trace shows normal flow and a barge-in cancel that stops TTS mid-utterance.

## Use It · 实战用法

- **Pipecat** 适合要完全掌控的场合——自定义 processor、Python 优先、提供商可插拔。
- **LiveKit Agents** 适合 WebRTC 优先的部署和电话场景。
- **Vapi / Retell** 适合没有 WebRTC 团队还要托管语音代理的场合。
- **OpenAI Realtime / Gemini Live** 适合直连音频进/音频出（MultimodalAgent）。

> - **Pipecat** for full control — custom processors, Python-first, pluggable providers.
> - **LiveKit Agents** for WebRTC-first deployments and telephony.
> - **Vapi / Retell** for hosted voice agents without a WebRTC team.
> - **OpenAI Realtime / Gemini Live** for direct audio-in/audio-out (MultimodalAgent).

## Ship It · 交付

`outputs/skill-voice-pipeline.md` 搭建一个 Pipecat 形态的语音流水线脚手架：VAD + STT + LLM + TTS + 传输层，外加 barge-in 处理。

> `outputs/skill-voice-pipeline.md` scaffolds a Pipecat-shaped voice pipeline with VAD + STT + LLM + TTS + transport plus barge-in handling.

## Exercises · 练习

1. 给你的玩具流水线加一个指标 observer：统计每秒每阶段的帧数。延迟在哪里堆积？
2. 实现置信度门禁的 STT：低于阈值就请求「您能再说一遍吗？」
3. 加语义轮次检测：简单规则——转写以「?」结尾即为轮次结束。
4. 读 Pipecat 的传输层文档。把标准库传输换成 SmallWebRTCTransport 配置（stub 即可）。
5. 在同一个问题上实测 OpenAI Realtime 与 STT+LLM+TTS 级联。文本层控制付出了多少延迟代价？

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| Frame | 「事件」 | 流水线里带类型的数据单元（audio、transcript、text、control） |
| Processor | 「流水线阶段」 | 带 process(frame) 的处理器 |
| DOWNSTREAM | 「正向流」 | 源到汇：音频进、语音出 |
| UPSTREAM | 「反馈流」 | 控制：取消、指标、barge-in |
| VAD | 「人声活动检测」 | 检测用户是否正在说话 |
| Semantic turn detection | 「聪明的轮次结束判断」 | 用模型判断用户说完了没有 |
| MultimodalAgent | 「直连音频 agent」 | 音频进、音频出；中间不经过文本 |
| VoicePipelineAgent | 「级联 agent」 | STT + LLM + TTS；文本层控制 |

## Further Reading · 延伸阅读

- [Pipecat docs](https://docs.pipecat.ai/getting-started/introduction) —— 帧式流水线、processor、传输层
- [LiveKit Agents docs](https://docs.livekit.io/agents/) —— WebRTC 与语音原语
- [Vapi](https://vapi.ai/) —— 托管语音平台
- [Retell AI](https://www.retellai.com/) —— 托管语音，带延迟基准
