# Omni Models: Qwen2.5-Omni and the Thinker-Talker Split · 全模态模型：Qwen2.5-Omni 与 Thinker-Talker 分工

> GPT-4o 在 2024 年 5 月的产品演示之所以颠覆，不在于底层模型，而在于产品形态 —— 一个语音界面：你说话，模型看到摄像头看到的，并在 250ms 内开口回话。开源生态在 2024 到 2025 年剩下的时间里都在追赶这个产品形态。Qwen2.5-Omni（2025 年 3 月）是参考级的开源设计：一个 Thinker（生成文本的大 Transformer）加一个 Talker（并行生成语音的 Transformer），以流式语音 token 相连。Mini-Omni 做了简化，Moshi 追平了它的延迟，GLM-4-Voice 把它扩展到中文。本课解读 Thinker-Talker 架构，以及让流式实时对话成立的那份延迟预算。

> GPT-4o's product demo in May 2024 was disruptive not because of the underlying model but because of the product shape — a voice interface where you talk, the model sees what the camera sees, and it talks back in under 250ms. The open ecosystem spent the rest of 2024 and 2025 racing to reach that product surface. Qwen2.5-Omni (March 2025) is the reference open design: a Thinker (large text-generating transformer) plus a Talker (parallel speech-generating transformer), linked by streaming speech tokens. Mini-Omni simplified it, Moshi matched its latency, GLM-4-Voice extended it to Chinese. This lesson reads the Thinker-Talker architecture and the latency budget that makes streaming real-time dialogue work.

**Type:** Build
**Languages:** Python (stdlib, streaming pipeline latency simulator + VAD loop)
**Prerequisites:** Phase 12 · 19 (audio-LLMs), Phase 12 · 16 (any-to-any)
**Time:** ~180 minutes

## Learning Objectives · 学习目标

- 把推理流水线拆成 Thinker（文本推理）与 Talker（语音合成），解释为什么并行流式可行。
- 逐组件计算一次对话交互的首个音频字节时间（TTFAB）预算。
- 描述 TMRoPE 在 Thinker 内部对视觉、音频、文本做时间对齐位置编码的方式。
- 说出三种实时对话模式：半双工、轮次切换、全双工。

> Split the inference pipeline into Thinker (text reasoning) and Talker (speech synthesis) and explain why parallel streaming works.
> Compute the time-to-first-audio-byte (TTFAB) budget for a conversational interaction, component by component.
> Describe TMRoPE's time-aligned position encoding across vision, audio, and text within the Thinker.
> Name the three real-time conversational patterns: half-duplex, turn-taking, full-duplex.

## The Problem · 问题在哪

一个实时语音助手必须又多又快地干活：

1. 听见用户。实时语音 token 化，加上判断用户是否说完的语音活动检测（VAD）。
2. 可选地看见。摄像头输入 2-4 FPS，与音频一起流进 Thinker。
3. 思考。结合对话历史组织一个回复。
4. 说话。合成音频 token，解码成波形，流到用户扬声器。

每一步都加延迟。对话体感要求总往返 < 500ms —— 低于这个数，用户才不会察觉卡顿。GPT-4o 宣称约 250ms。Moshi 约 160ms。Qwen2.5-Omni 约 350-500ms。

每个组件都必须流式。任何「先攒一批再解码」都行不通。

> A real-time voice assistant has to do a lot, fast: Hear the user. Real-time speech tokenization, voice activity detection (VAD) to know when they're done speaking. Optionally see. Camera input at 2-4 FPS, streamed into the Thinker alongside audio. Think. Compose a response conditioned on the conversation history. Speak. Synthesize audio tokens, decode to waveform, stream to the user's speakers. ... Each step adds latency. Conversational-feel requires total round-trip < 500ms — below that, the user stops noticing the lag. GPT-4o claims ~250ms. Moshi ~160ms. Qwen2.5-Omni ~350-500ms. ... Every component needs to stream. Nothing can be "batch everything then decode."

## The Concept · 概念

### Thinker and Talker · Thinker 与 Talker

Qwen2.5-Omni 的分解：

- Thinker：一个 7B-80B 的文本生成 Transformer。消化交错的文本 + 图像 + 音频 token。输出表达「该说什么」的文本 token。
- Talker：一个更小的语音生成 Transformer（200M-1B）。消化 Thinker 的文本输出 token 加上近期的语音上下文 token。输出离散语音 token（残差 VQ 索引）。
- 语音解码器：一个流式波形解码器（SNAC、MoVQGAN 一族），把语音 token 实时转成音频采样。

这个分工很重要。Thinker 必须大才能推理好。Talker 可以小，因为它的职责是局部的 —— 把文本变成语音 token。更大的 Talker 不会更有表现力，只会更慢。

两者并行运行：

1. Thinker 吐出文本 token t_i。
2. Talker（经由流式）消化 t_i，吐出语音 token s_i, s_{i+1}, ..., s_{i+k}。
3. 语音解码器随到随消化语音 token，产出音频采样。
4. 当 Thinker 走到文本 token t_{i+3} 时，Talker 已经把 t_0..t_{i+2} 的音频流出去了。

> Qwen2.5-Omni's decomposition: Thinker: a 7B-80B text-generating transformer. Consumes interleaved text + image + audio tokens. Outputs text tokens representing what to say. Talker: a smaller speech-generating transformer (200M-1B). ... The separation matters. Thinker has to be big for good reasoning. Talker can be small because its job is local — convert text to speech tokens. Bigger Talker is not more expressive; it's slower. ... Running both in parallel: Thinker emits text token t_i. Talker consumes t_i (via streaming) and emits speech tokens s_i, s_{i+1}, ..., s_{i+k}. ... By the time Thinker is at text token t_{i+3}, Talker has already streamed audio for t_0..t_{i+2}.

### TMRoPE — time-aligned multimodal positions · TMRoPE——时间对齐的多模态位置编码

Thinker 要同时整合图像帧（比如以 4 FPS 到达）、音频帧（以每秒 50 帧到达）和来自对话历史的文本。朴素的序列顺序（先全部图像、再全部音频、再文本）会丢掉时间对齐。

TMRoPE 给每个 token 分配绝对时间戳。t=2.3s 的视觉 token。t=2.32s 的音频 token。用户在 t=2.35s 说出的文本 token「停」。RoPE 按时间戳旋转注意力；模型把它们视为同一时刻发生。

这就是让「他一边说你好一边挥手」成立的基础设施 —— 模型在同一个概念时刻看到视频帧和音频。

> The Thinker needs to integrate image frames (arriving at, say, 4 FPS), audio frames (arriving at 50 frames/second), and text from conversation history. A naive sequence order (all images, then all audio, then text) loses temporal alignment. ... TMRoPE assigns absolute timestamps to every token. Vision token at t=2.3s. Audio token at t=2.32s. Text token from the user "stop" at t=2.35s. RoPE rotates attention by timestamp; the model sees them as temporally concurrent. ... This is the infrastructure for "he waved while saying hello" to work — the model sees the video frame and the audio at the same conceptual moment.

### Streaming speech synthesis · 流式语音合成

语音 token 必须流式。Mini-Omni（Xie & Wu，2024）提出了「语言模型能听见，一边思考一边在流中说」：Thinker 的输出 token 与 Talker 的输出 token 交错在同一条序列里。Thinker 一提交下一个文本 token，Talker 立刻开火。没有批边界。

Moshi（Défossez et al.，2024 年 10 月）是最快的开源实现。单张 A100 上 160ms TTFAB。架构：单个 7B Transformer 在交替位置上输出文本与语音 token，用「内心独白」把思考流和说话流分开。这实际上是用精心的训练把 Thinker + Talker 融进了一个模型。

> Speech tokens must stream. Mini-Omni (Xie & Wu, 2024) introduced "language models can hear, talk while thinking in streaming": Thinker output tokens and Talker output tokens interleave in the same sequence. Talker fires as soon as Thinker commits the next text token. No batch boundaries. ... Moshi (Défossez et al., October 2024) is the fastest open implementation. 160ms TTFAB on a single A100. Architecture: a single 7B transformer that emits text and speech tokens on alternating positions, with an "inner monologue" that separates the thinking stream from the speaking stream. This is effectively Thinker + Talker fused into one model with careful training.

### VAD and turn-taking · VAD 与轮次切换

语音活动检测跑在输入侧。两种模式：

- 半双工：用户说，模型听。模型说，用户听。通过 VAD 静音检测（约 200ms）清晰交接。
- 全双工：双方可以同时说话。模型可以附和（「嗯哼」）或被打断。难得多。Moshi 支持这个。

Qwen2.5-Omni 默认半双工，通过静音阈值做轮次切换。全双工需要应用层处理。

> Voice activity detection runs on the input side. Two patterns: Half-duplex: user speaks, model listens. Model speaks, user listens. Clear handoff via VAD silence detection (~200ms). Full-duplex: both can speak simultaneously. Model can backchannel ("uh-huh") or interrupt. Much harder. Moshi supports this. ... Qwen2.5-Omni supports half-duplex by default, with turn-taking via silence threshold. Full-duplex requires application-layer handling.

### Qwen3-Omni (November 2025) · Qwen3-Omni（2025 年 11 月）

继任者。Qwen3-80B Thinker、更大的 Talker、改进的 TMRoPE-v2。延迟逼近 GPT-4o 的 250ms。开放权重。OmniBench 基准成绩与 Gemini 2.0 Live 相当。

> The successor. Qwen3-80B Thinker, larger Talker, improved TMRoPE-v2. Latency close to GPT-4o's 250ms. Open weights. Benchmarks on OmniBench competitive with Gemini 2.0 Live.

### Production latency budget · 生产延迟预算

一次典型的流式交互：

- 麦克风 → 音频 token：40-80ms。
- 预填充（提示 + 历史）：7B 上 100-200ms，70B 上多得多。
- Thinker 首个文本 token：40ms。
- Talker 处理首个文本 token：20ms。
- 首批语音 token 提交：40ms。
- 残差 VQ 解码：30ms。
- 语音波形解码：50-80ms。

总 TTFAB：7B 上 320-510ms，70B 上 600-900ms。前沿质量通常意味着 70B+；这就是前沿延迟差距的来源。

> For a typical streaming interaction: Mic -> audio tokens: 40-80ms. Prefill (prompt + history): 100-200ms at 7B, much more at 70B. ... Total TTFAB: 320-510ms at 7B, 600-900ms at 70B. Frontier quality usually means 70B+; hence the frontier latency gap.

### Token-rate math · token 速率算术

16kHz 语音、50Hz 基础语音 token 时，每秒输出需要 50 个语音 token。Talker 必须以 ≥50 tok/s 的速率产出才跟得上。H100 上典型 LLM 吞吐是 30-80 tok/s，一个小的（200-300M）Talker 够快；7B 的 Talker 会掉队。

这就是为什么存在小而专的 Talker 模型，而不是「直接用主模型」。

> At 16kHz speech with 50 Hz base speech tokens, you need 50 speech tokens per second of output. Talker must emit ≥50 tok/s to keep up. At a typical LLM throughput of 30-80 tok/s on an H100, a small (200-300M) Talker is fast enough; a 7B Talker would fall behind. ... This is why small dedicated Talker models exist rather than "just use the main model."

```figure
l5-thinker-talker
```

## Use It · 实战用法

`code/main.py`：

- 用模拟的 token 产出速率模拟一条 Thinker-Talker 流水线。
- 对可配置的模型尺寸和麦克风采样率计算 TTFAB。
- 演示带 VAD 静音阈值的半双工轮次切换。

> `code/main.py`: Simulates a Thinker-Talker pipeline with mock token-emission rates. Computes TTFAB for configurable model sizes and mic sample rates. Demonstrates half-duplex turn-taking with VAD silence threshold.

## Ship It · 交付

本课产出 `outputs/skill-omni-streaming-budget.md`。给定一个实时语音产品的目标 TTFAB 和功能集（视觉输入、双语、全双工），它挑选 Qwen2.5-Omni、Qwen3-Omni、Moshi 或 Mini-Omni，并为 Thinker/Talker 定尺寸。

> This lesson produces `outputs/skill-omni-streaming-budget.md`. Given a real-time voice product's target TTFAB and feature set (vision-in, bilingual, full-duplex), picks Qwen2.5-Omni, Qwen3-Omni, Moshi, or Mini-Omni and sizes the Thinker/Talker.

## Exercises · 练习

1. 你的目标 TTFAB 是 300ms。在 7B Thinker + 300M Talker 上，写出每个组件的延迟。

2. Qwen2.5-Omni 使用 TMRoPE。对于用户在 t=1s 开始说话、摄像头在 t=1.2s 捕捉到一个手势的提示，描述模型看到的是什么。

3. 全双工要求模型边听边说。提出一种能教会这件事的训练数据格式。

4. 阅读 Moshi 论文第 4 节。描述「内心独白」的分离方式，以及它为什么能避免 Thinker-Talker 拆分。

5. 计算吞吐预算：要以 16kHz 语音、每秒 50 个基础层 token 的速率跟上，Talker 必须多快地产出 token？

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|------------------------|
| Thinker | 「推理大脑」 | 产出「该说什么」的大型文本生成 Transformer |
| Talker | 「说话的嘴」 | 从 Thinker 的文本产出离散语音 token 的小 Transformer |
| TTFAB | 「延迟预算」 | 首个音频字节时间：从用户说完到第一段音频采样输出 |
| TMRoPE | 「时间对齐 RoPE」 | 用绝对时间戳跨越视觉、音频、文本的位置编码 |
| 半双工（Half-duplex） | 「轮次切换」 | 用户与模型交替；VAD 静音检测用户说完 |
| 全双工（Full-duplex） | 「同时进行」 | 模型可以同时说和听；能附和 |
| 内心独白（Inner monologue） | 「Moshi 式分离」 | 单模型设计，思考流与说话流交错 |

## Further Reading · 延伸阅读

- [Xu et al. — Qwen2.5-Omni (arXiv:2503.20215)](https://arxiv.org/abs/2503.20215)
- [Qwen Team — Qwen3-Omni (arXiv:2509.17765)](https://arxiv.org/html/2509.17765v1)
- [Xie & Wu — Mini-Omni (arXiv:2408.16725)](https://arxiv.org/abs/2408.16725)
- [Défossez et al. — Moshi (arXiv:2410.00037)](https://arxiv.org/abs/2410.00037)
- [Zeng et al. — GLM-4-Voice (arXiv:2412.02612)](https://arxiv.org/abs/2412.02612)
