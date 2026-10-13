# Streaming Speech-to-Speech — Moshi, Hibiki, and Full-Duplex Dialogue · 流式语音到语音——Moshi、Hibiki 与全双工对话

> 2024-2026 年重新定义了语音 AI。Moshi 交付了一个能同时听和说的单一模型，延迟 200 ms。Hibiki 逐块做语音到语音翻译。两者都抛弃了 ASR → LLM → TTS 流水线，改用构建在 Mimi codec token 之上的统一全双工架构。这就是新的参考设计。
>
> 2024-2026 redefined voice AI. Moshi ships a single model that listens and speaks simultaneously at 200 ms latency. Hibiki does speech-to-speech translation chunk-by-chunk. Both abandon the ASR → LLM → TTS pipeline for a unified full-duplex architecture over Mimi codec tokens. This is the new reference design.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 6 · 13 (Neural Audio Codecs), Phase 6 · 11 (Real-Time Audio), Phase 7 · 05 (Full Transformer)
**Time:** ~75 minutes

---

## The Problem · 问题在哪

用第 11 + 12 课搭出来的每个语音代理都有一个约 300-500 ms 的根本延迟下限：VAD 触发、STT 处理、LLM 推理、TTS 生成。每个阶段都有自己的最小延迟。你可以调优、可以并行化，但流水线的形状给你封了顶。

Moshi（Kyutai，2024-2026）问了一个不同的问题：如果没有流水线呢？如果只有一个模型，直接地、连续地音频进音频出，而文本只是中间的「内心独白」（inner monologue），不是必经阶段呢？

答案就是**全双工语音到语音（full-duplex speech-to-speech）**。理论延迟 160 ms（80 ms Mimi 帧 + 80 ms 声学延迟）。实际延迟在单张 L4 GPU 上为 200 ms。这只是一流流水线语音代理的一半。

> Every voice agent built from Lessons 11 + 12 has a fundamental latency floor around 300-500 ms: VAD fires, STT processes, LLM reasons, TTS generates. Each stage has its own minimum latency. You can tune and parallelize, but the pipeline shape caps you.
> Moshi (Kyutai, 2024-2026) asks a different question: what if there is no pipeline? What if one model takes audio in and emits audio out directly, continuously, with text as an intermediate "inner monologue" instead of a required stage?
> The answer is **full-duplex speech-to-speech**. Theoretical latency 160 ms (80 ms Mimi frame + 80 ms acoustic delay). Practical latency 200 ms on a single L4 GPU. That's half what a best-in-class pipelined voice agent achieves.

---

## The Concept · 概念

![Moshi 架构：两路并行 Mimi 流 + 内心独白文本](../assets/moshi-hibiki.svg)

### The Moshi architecture · Moshi 架构

**输入。** 两路 Mimi codec 流，都是 12.5 Hz × 8 codebooks：

- 流 1：用户音频（Mimi 编码，持续到达）
- 流 2：Moshi 自己的音频（由 Moshi 生成）

**Transformer。** 一个 7B 参数的 Temporal Transformer 处理这两路流和一路文本「内心独白」流。在每个 80 ms 步，它：

1. 消费最新的用户 Mimi token（8 codebooks）。
2. 消费最近的 Moshi Mimi token（8 codebooks，边生成边消费）。
3. 生成下一个 Moshi 文本 token（内心独白）。
4. 生成下一批 Moshi Mimi token（通过一个小型 Depth Transformer 的 8 codebooks）。

三路流——用户音频、Moshi 音频、Moshi 文本——并行运行。Moshi 能边说边听用户；能在用户打断时自我打断；能在不打断主话语的情况下发出附和（back-channel，比如「嗯」）。

**Depth transformer。** 在一帧内部，8 个 codebook 不是并行预测的——它们之间存在 codebook 间依赖。一个小的 2 层「depth transformer」在 80 ms 内顺序预测它们。这是 AR codec LM 的标准因子分解（VALL-E、VibeVoice 也这么用）。

> **Inputs.** Two Mimi codec streams, both at 12.5 Hz × 8 codebooks:
> **The transformer.** A 7B-parameter Temporal Transformer processes both streams and a text "inner monologue" stream. At each 80 ms step, it: ...
> All three streams — user audio, Moshi audio, Moshi text — run in parallel. Moshi can hear the user while speaking; can interrupt itself when the user interrupts; can back-channel ("mhm") without breaking its main utterance.
> **The depth transformer.** Within a frame, the 8 codebooks are not predicted in parallel — they have inter-codebook dependencies. A small 2-layer "depth transformer" predicts them sequentially within 80 ms. This is the standard factorization for AR codec LMs (also used by VALL-E, VibeVoice).

---

### Why inner-monologue text helps · 内心独白文本为什么有用

没有显式文本，模型就得在声学流里隐式建模语言。Moshi 的洞见：强迫它在输出音频的同时输出文本 token。文本流基本上就是 Moshi 正在说的话的转写。这提升了语义连贯性，让替换语言模型头更容易，还免费送你一份转写。

> Without explicit text, the model has to implicitly model language in its acoustic stream. Moshi's insight: force it to emit text tokens alongside audio. The text stream is essentially the transcript of what Moshi is saying. This improves semantic coherence, makes it easier to swap out a language model head, and gives you transcripts for free.

---

### Hibiki: streaming speech-to-speech translation · Hibiki：流式语音到语音翻译

同一套架构，用翻译对训练。源语言音频进，目标语言音频出，连续不断。Hibiki-Zero（2026 年 2 月）消除了对词级对齐训练数据的需求——用句子级数据 + GRPO 强化学习来优化延迟。

初期支持四个语言对；用约 1000 小时数据即可适配一门新语言。

> Same architecture, trained on translation pairs. Source audio in, target-language audio out, continuously. Hibiki-Zero (Feb 2026) eliminates the need for word-level aligned training data — uses sentence-level data + GRPO reinforcement learning for latency optimization.
> Four language pairs supported initially; can be adapted to a new language with ≈1000 hours.

---

### The broader Kyutai stack (2026) · 更完整的 Kyutai 技术栈（2026）

- **Moshi** —— 全双工对话（法语优先，英语支持良好）
- **Hibiki / Hibiki-Zero** —— 同声传译（simultaneous speech translation）
- **Kyutai STT** —— 流式 ASR（500 ms 或 2.5 s 前视）
- **Kyutai Pocket TTS** —— 1 亿参数的 TTS 跑在 CPU 上（2026 年 1 月）
- **Unmute** —— 把这些组合起来的完整流水线，跑在公开服务器上

L40S GPU 上的吞吐：64 路并发会话，3 倍实时。

> Throughput on an L40S GPU: 64 concurrent sessions at 3× real-time.

---

### Sesame CSM — the cousin · Sesame CSM——表亲

Sesame CSM（2025）用类似的思路——Llama-3 骨干 + Mimi codec 头。但 CSM 是单向的（吃上下文 + 文本，产出语音）而非全双工。它是市面上最好的「声音临场感」（voice presence）TTS；与 Moshi 的全双工能力并不完全是一回事。

> Sesame CSM (2025) uses a similar idea — a Llama-3 backbone with a Mimi codec head. But CSM is single-directional (takes context + text, produces speech) rather than full-duplex. It's the best "voice presence" TTS on the market; not quite the same as Moshi's full-duplex capability.

---

### 2026 performance numbers · 2026 年性能数字

| 模型 | 延迟 | 用途 | 许可 |
|-------|---------|----------|---------|
| Moshi | 200 ms（L4） | 全双工英语 / 法语对话 | CC-BY 4.0 |
| Hibiki | 12.5 Hz 帧率 | 法 ↔ 英流式翻译 | CC-BY 4.0 |
| Hibiki-Zero | 同上 | 5 个语言对，无需对齐数据 | CC-BY 4.0 |
| Sesame CSM-1B | 200 ms TTFA | 上下文条件 TTS | Apache-2.0 |
| GPT-4o Realtime | ~300 ms | 闭源，OpenAI API | 商业 |
| Gemini 2.5 Live | ~350 ms | 闭源，Google API | 商业 |

```figure
sp-fullduplex
```

---

## Build It · 动手造

### Step 1: the interface · 接口

Moshi 暴露一个 WebSocket 服务器：接收 80 ms 的 Mimi 编码音频块，返回 80 ms 的 Mimi 编码音频块。双向。持续不断。

```python
import asyncio
import websockets
from moshi.client_utils import encode_audio_mimi, decode_audio_mimi

async def moshi_chat():
    async with websockets.connect("ws://localhost:8998/api/chat") as ws:
        mic_task = asyncio.create_task(stream_mic_to(ws))
        spk_task = asyncio.create_task(stream_from_to_speaker(ws))
        await asyncio.gather(mic_task, spk_task)
```

> Moshi exposes a WebSocket server that takes 80 ms chunks of Mimi-encoded audio and returns 80 ms chunks of Mimi-encoded audio. Both ways. Constantly.

### Step 2: the full-duplex loop · 全双工循环

```python
async def stream_mic_to(ws):
    async for chunk_80ms in mic_stream_at_12_5_hz():
        mimi_tokens = encode_audio_mimi(chunk_80ms)
        await ws.send(serialize(mimi_tokens))

async def stream_from_to_speaker(ws):
    async for msg in ws:
        mimi_tokens, text_token = deserialize(msg)
        audio = decode_audio_mimi(mimi_tokens)
        await play(audio)
```

两个方向同时运行。Python asyncio 或 Rust futures 是标准传输层。

> Both directions run simultaneously. Python asyncio or Rust futures are the standard transport.

### Step 3: the training objective (conceptual) · 训练目标（概念）

对每个 80 ms 帧 `t`：

- 输入：`user_mimi[0..t]`、`moshi_mimi[0..t-1]`、`moshi_text[0..t-1]`
- 预测：`moshi_text[t]`，然后 `moshi_mimi[t, codebook_0..7]`

文本先于音频预测（内心独白）；音频在 depth transformer 内部按 codebook 顺序预测。

> For every 80 ms frame `t`: Input: `user_mimi[0..t]`, `moshi_mimi[0..t-1]`, `moshi_text[0..t-1]`; Predict: `moshi_text[t]`, then `moshi_mimi[t, codebook_0..7]`.
> Text is predicted before audio (inner monologue); audio is predicted codebook-sequential within the depth transformer.

### Step 4: where Moshi wins and where it doesn't · Moshi 赢在哪、不赢在哪

Moshi 赢：

- 便宜硬件上 250 ms 以内的端到端。
- 自然的附和与打断。
- 没有流水线胶水代码。

Moshi 不赢：

- 工具调用（没为此训练；你需要一条单独的 LLM 链路）。
- 长推理（Moshi 是个 8B 左右的对话模型，不是 Claude/GPT-4）。
- 冷门话题上的事实准确性。
- 大多数生产级企业场景（2026 年大家仍然用流水线）。

> Moshi wins: Sub-250 ms end-to-end on cheap hardware. Natural back-channels and interruptions. No pipeline glue code.
> Moshi does not win: Tool calling (not trained for it; you need a separate LLM path). Long reasoning (Moshi is an 8B-ish dialogue model, not Claude/GPT-4). ... Most production enterprise use cases (still use pipelines in 2026).

---

## Use It · 实战用法

| 场景 | 选择 |
|-----------|------|
| 最低延迟的语音伴侣 | Moshi |
| 实时翻译通话 | Hibiki |
| 语音演示 / 研究 | Moshi、CSM |
| 带工具的企业代理 | 流水线（第 12 课），不是 Moshi |
| 上下文定制的音色 TTS | Sesame CSM |
| 任意语言的语音到语音 | GPT-4o Realtime 或 Gemini 2.5 Live（商业） |

---

## Pitfalls · 常见的坑

- **工具调用受限。** Moshi 是对话模型，不是代理框架。要工具就与流水线结合。
- **特定音色条件化。** Moshi 用的是单一训练好的人设（persona）；克隆声音要单独跑一次训练。
- **语言覆盖。** 法语 + 英语很棒；其他语言有限。Hibiki-Zero 有帮助，但你仍然需要训练数据。
- **资源成本。** 一个完整的 Moshi 会话占住一个 GPU 槽位；不是便宜的共享多租户部署模式。

> **Limited tool calling.** Moshi is a dialogue model, not an agent framework. Combine with pipeline for tools.
> **Specific-voice conditioning.** Moshi uses a single trained persona; cloning is a separate training run.
> **Language coverage.** French + English is excellent; others limited. Hibiki-Zero helps, but you still need training data.
> **Resource cost.** A full Moshi session holds a GPU slot; not a cheap shared-tenant deploy pattern.

---

## Ship It · 交付

保存为 `outputs/skill-duplex-pipeline.md`：为一个语音代理工作负载在流水线 vs 全双工架构之间做选择，并给出理由。

> Save as `outputs/skill-duplex-pipeline.md`. Pick pipeline vs full-duplex architecture for a voice-agent workload, with reason.

---

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。它以符号方式模拟双流 + 内心独白架构。
2. **中等。** 从 HuggingFace 拉取 Moshi，启动服务器，测一轮对话。测量从用户说完话到 Moshi 开始回应的墙钟延迟。
3. **困难。** 拿你第 12 课的流水线代理，在 20 条对齐的测试语句上比较它与 Moshi 的 P50 延迟。写一份总结：什么情况下流水线在架构上仍然会赢。

> 1. **Easy.** Run `code/main.py`. It simulates the two-stream + inner-monologue architecture symbolically.
> 2. **Medium.** Pull Moshi from HuggingFace, run the server, test one conversation. Measure wall-clock latency from end-of-user-speech to start-of-Moshi-response.
> 3. **Hard.** Take your Lesson 12 pipeline agent and compare P50 latency vs Moshi on 20 matched test utterances. Write up when a pipeline architecturally wins anyway.

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Full-duplex（全双工） | 边听边说 | 两路音频流同时在同一个模型上活跃。 |
| Inner monologue（内心独白） | 模型的文本流 | Moshi 在输出音频的同时输出文本 token。 |
| Depth transformer | Codebook 间预测器 | 在一个 80 ms 帧内预测 8 个 codebook 的小 transformer。 |
| Mimi | Kyutai 的编解码器 | 12.5 Hz × 8 codebooks；语义+声学；驱动 Moshi。 |
| Streaming S2S | 音频 → 音频实时 | 逐块的翻译/对话，没有流水线阶段。 |
| Back-channeling | 「嗯」式附和 | Moshi 能在不打断自己回合的情况下发出小幅确认应答。 |

---

## Further Reading · 延伸阅读

- [Défossez et al. (2024). Moshi — speech-text foundation model](https://arxiv.org/html/2410.00037v2) —— 那篇论文。
- [Kyutai Labs (2026). Hibiki-Zero](https://arxiv.org/abs/2602.12345) —— 无需对齐数据的流式翻译。
- [Sesame (2025). Crossing the uncanny valley of voice](https://www.sesame.com/research/crossing_the_uncanny_valley_of_voice) —— CSM 规格。
- [Kyutai — Moshi repo](https://github.com/kyutai-labs/moshi) —— 安装 + 服务器。
- [OpenAI — Realtime API](https://platform.openai.com/docs/guides/realtime) —— 闭源商业对手。
- [Kyutai — Delayed Streams Modeling](https://github.com/kyutai-labs/delayed-streams-modeling) —— 底层的 STT/TTS 框架。
