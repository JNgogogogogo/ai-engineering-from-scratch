# Audio-Language Models: the Whisper to Audio Flamingo 3 Arc · 音频语言模型：从 Whisper 到 Audio Flamingo 3 的演进

> Whisper（Radford et al.，2022 年 12 月）一锤定音地解决了语音识别 —— 68 万小时弱监督多语言语音、一个简单的编码器-解码器 Transformer、一套此后每一次 ASR 发布都要引用的基准。但识别不是推理。问「这段录音里有哪些乐器」「说话人在表达什么情绪」「第 3 分钟发生了什么」，需要的是音频理解，而不是转写。Qwen-Audio、SALMONN、LTU 和 NVIDIA 的 Audio Flamingo 3（AF3，2025 年 7 月）逐步搭起了这套栈：保留 Whisper 级编码器，接上 Q-former，用音频-文本指令数据训练，再加思维链推理。本课走完这条演进弧线。

> Whisper (Radford et al., December 2022) settled speech recognition — 680k hours of weakly-supervised multilingual speech, a simple encoder-decoder transformer, a benchmark that made every subsequent ASR release cite it. But recognition is not reasoning. Asking "what instruments are in this recording" or "what emotion is the speaker expressing" or "what happened at minute 3" requires audio understanding, not transcription. Qwen-Audio, SALMONN, LTU, and NVIDIA's Audio Flamingo 3 (AF3, July 2025) progressively built that stack: keep Whisper-class encoders, bolt on Q-formers, train on audio-text instruction data, add chain-of-thought reasoning. This lesson walks the arc.

**Type:** Build
**Languages:** Python (stdlib, log-Mel spectrogram + audio Q-former skeleton)
**Prerequisites:** Phase 6 (Speech and Audio), Phase 12 · 03 (Q-Former)
**Time:** ~180 minutes

## Learning Objectives · 学习目标

- 从波形计算 log-Mel 频谱图：加窗、FFT、滤波器组、对数变换。
- 对比编码器选项：Whisper 编码器、BEATs、AF-Whisper 混合。各自何时占优。
- 搭一个音频 Q-former：N 个可学习查询对频谱图 patch 做交叉注意力。
- 解释级联（先 Whisper 后 LLM）与端到端音频-LLM 训练：为什么端到端在推理能力上扩展性更好。

> Compute a log-Mel spectrogram from a waveform: windowing, FFT, filter banks, log transform.
> Compare encoder options: Whisper encoder, BEATs, AF-Whisper hybrid. When each wins.
> Build an audio Q-former: N learnable queries cross-attending to spectrogram patches.
> Explain cascaded (Whisper-then-LLM) vs end-to-end audio-LLM training: why end-to-end scales better for reasoning.

## The Problem · 问题在哪

语音识别已被 Whisper 解决。「音频 OCR」已是白菜价。但「白菜价」止步于转写。如果模型无法对听到的内容做推理 —— 时机、说话人、情绪、音乐结构、环境音 —— 光靠转写驱动不了产品功能。

三条显而易见的路线：

1. 级联：Whisper 转写，LLM 对文字稿做推理。纯语音场景可行。音乐、环境音、多人重叠、情绪全部失效。

2. 端到端音频-LLM：音频编码器把音频 token 直接喂进 LLM，跳过转写。保留声学信息（情绪、说话人、环境）。需要新的训练数据。

3. 混合：音频编码器 + 文本解码器，既能转写也能推理。Qwen-Audio 和 Audio Flamingo 选这条路。

> Speech recognition was solved by Whisper. OCR-of-audio is a commodity. But "commodity" stops at transcription. If the model cannot reason over what it heard — timing, speakers, emotion, music structure, environmental sounds — transcription alone cannot drive product features. ... Three obvious routes: Cascade: Whisper transcribes, LLM reasons over the transcript. Works for pure-speech scenarios. Fails for music, environmental audio, multi-speaker overlap, emotion. ... End-to-end audio-LLM: an audio encoder feeds audio tokens directly into an LLM, skipping transcription. ... Hybrid: audio encoder + text decoder that can both transcribe and reason. Qwen-Audio and Audio Flamingo pick this route.

## The Concept · 概念

### Log-Mel spectrogram: the input feature · Log-Mel 频谱图：输入特征

每个音频编码器都从同一个特征出发：log-Mel 频谱图。

1. 重采样到 16 kHz。
2. 短时傅里叶变换，25ms 窗、10ms 步进。
3. 取 FFT 结果的幅值。
4. 施加 Mel 滤波器组（典型为 80 个、在 0-8000 Hz 上按对数分布的滤波器），把频率扭曲到感知尺度。
5. 对数压缩（log(1 + x)) 以适配动态范围。

结果：形状为 (T, 80) 的二维数组，T 是时间帧数。30 秒片段、100 Hz 帧率： (3000, 80)。

> Every audio encoder starts with the same feature: a log-Mel spectrogram. ... Resample to 16 kHz. Short-time Fourier transform with 25ms windows, 10ms hop. Take magnitude of the FFT result. Apply Mel filter banks (typically 80 filters log-spaced 0-8000 Hz) to warp to perceptual frequency. Log compress (log(1 + x)) for dynamic range. ... Result: a 2D array of shape (T, 80) where T is the number of time frames. For a 30-second clip at 100 Hz frame rate: (3000, 80).

### Whisper's encoder · Whisper 的编码器

Whisper 的编码器是一个 12 层 ViT 风格的 Transformer，把 log-Mel 频谱图当作时间帧序列来处理。输出：每个时间帧一个隐状态向量。

做 ASR 时，Whisper 的解码器是一个交叉注意力 Transformer，以编码器输出为条件生成文本 token。标准的编码器-解码器。

做 ALM（音频-LLM）时，你要把编码器输出接给另一个 LLM 当输入。模式是：Whisper 编码器冻结，Q-former 可训练，LLM 冻结或微调。

> Whisper's encoder is a 12-layer ViT-style transformer processing the log-Mel spectrogram as a sequence of time frames. Output: one hidden-state vector per time frame. ... For ASR, Whisper's decoder is a cross-attention transformer that generates text tokens conditioned on the encoder output. Standard encoder-decoder. ... For ALMs (audio-LLMs), you want the encoder output as input to a different LLM. The pattern: Whisper encoder frozen, Q-former trainable, LLM frozen or tuned.

### BEATs and audio-specific encoders · BEATs 与音频专用编码器

Whisper 的训练数据以语音为主。它在音乐和环境音上较弱。

BEATs（Chen et al.，2022）是在 AudioSet 上训练的自监督 Transformer。同等参数量下，它对音乐和环境音的捕捉优于 Whisper。

AF-Whisper（Audio Flamingo 3 的混合方案）：把 Whisper + BEATs 特征拼接为音频输入。Whisper 携带语言信号，BEATs 携带声学信号。

> Whisper was trained on speech-dominant data. It is weaker for music and environmental audio. ... BEATs (Chen et al., 2022) is a self-supervised transformer trained on AudioSet. Captures music and environmental sounds better than Whisper at the same parameter count. ... AF-Whisper (Audio Flamingo 3's hybrid): concat Whisper + BEATs features as the audio input. Whisper carries linguistic signal, BEATs carries acoustic signal.

### Audio Q-former · 音频 Q-former

与 BLIP-2 的视觉 Q-former 同一套模式。固定数量的可学习查询（常见 32 或 64）对音频编码器的输出帧做交叉注意力。这些查询成为喂给 LLM 的音频 token。

训练的对齐阶段：只训 Q-former，在音频-文本对（AudioCaps、Clotho）上做对比 + 描述损失。指令阶段：端到端，解冻 LLM，在指令数据上训练。

> Same pattern as BLIP-2's visual Q-former. A fixed number of learnable queries (often 32 or 64) cross-attend over the audio encoder's output frames. The queries become audio tokens consumed by the LLM. ... Training alignment stage: Q-former alone, contrastive + captioning losses on audio-text pairs (AudioCaps, Clotho). Instruction stage: end-to-end, unfreeze LLM, train on instruction data.

### The arc — SALMONN, Qwen-Audio, AF3 · 演进弧线——SALMONN、Qwen-Audio、AF3

SALMONN（Tang et al.，2023）：Whisper + BEATs + Q-former + LLaMA。第一个具备正经推理能力的开源音频-LLM。MMAU 基准综合约 0.55。

Qwen-Audio（Chu et al.，2023）：架构类似，训练数据更丰富，为多轮对话做了调优。MMAU 约 0.60。

LTU——Listen, Think, Understand（Gong et al.，2023）：显式推理数据，专注音频片段上的思维链。更小但更聚焦。

Audio Flamingo 3（Goel et al.，2025 年 7 月）：当前的开源 SOTA。8B LLM 骨干（Qwen2 7B）、Whisper-large 编码器拼接 BEATs、64 查询 Q-former、在 100 万+ 音频-文本指令对上训练。MMAU 0.72，在部分子任务上追平闭源前沿。

AF3 还为音频引入了按需思维链：模型可以选择性地在最终答案前输出思考 token（「让我先识别一下乐器：……」）。开启思考后，复杂推理任务的准确率提升 3-5 个点。

> SALMONN (Tang et al., 2023): Whisper + BEATs + Q-former + LLaMA. The first open audio-LLM with serious reasoning ability. Benchmarks on MMAU show ~0.55 composite. ... Qwen-Audio (Chu et al., 2023): similar architecture, trained on a richer dataset, tuned for multi-turn dialogue. MMAU ~0.60. ... Audio Flamingo 3 (Goel et al., July 2025): the current open SOTA. 8B LLM backbone (Qwen2 7B), Whisper-large encoder concat BEATs, 64-query Q-former, training on 1M+ audio-text instruction pairs. MMAU 0.72, matches proprietary frontier on some sub-tasks. ... AF3 also introduces on-demand chain-of-thought for audio: the model can optionally emit thinking tokens ("let me identify the instruments first: ...") before the final answer. Accuracy on complex reasoning tasks lifts 3-5 points when thinking is enabled.

### Cascaded vs end-to-end · 级联 vs 端到端

级联流水线：

1. Whisper 把音频转成文字。
2. LLM 对文字做推理。

「总结这期播客」完美胜任。但下面这些会失败：
- 「这首歌的情绪是什么？」—— 情绪在声音里，不在词里。
- 「说话人是 Alice 还是 Bob？」—— 需要说话人识别。
- 「爆炸发生在第几秒？」—— 时间定位在文本里丢失了。
- 「这是真音频还是生成的？」—— 深伪检测需要声学特征。

端到端保留声学信号。Qwen-Audio 和 AF3 原生处理音乐、环境和情绪。

> Cascaded pipeline: Whisper transcribes audio → text. LLM reasons over text. ... Works perfectly for "summarize this podcast." Fails for: "What's the mood of this song?" — mood is in the sound, not words. "Who is speaking, Alice or Bob?" — requires speaker identification. "At what second does the explosion happen?" — temporal grounding lost in text. "Is this real or generated audio?" — deepfake detection needs acoustic features. ... End-to-end preserves acoustic signal. Qwen-Audio and AF3 handle music, environment, and emotion natively.

### 2026 production recipe · 2026 年生产配方

新的音频理解产品：

- 选级联：如果目标就是转写，没有音乐，不做情绪推断。
- 选 AF3 / Qwen-Audio 系：如果涉及音乐、情绪、多说话人或复杂音频推理。

级联更便宜、更简单。端到端能力更强。

> For a new audio-understanding product: Cascaded if: transcription is the goal, no music, no emotion inference. AF3 / Qwen-Audio-family if: music, emotion, multi-speaker, or complex audio reasoning. ... Cascaded is cheaper and simpler. End-to-end is more capable.

### MMAU — the audio reasoning benchmark · MMAU——音频推理基准

MMAU（Massive Multimodal Audio Understanding）是 2024-2025 年的音频推理基准：

- 10,000 对音频-文本 QA，横跨语音、音乐、环境音。
- 覆盖分类、时间推理、因果推理、开放式问答。
- 专门测级联流水线系统性漏掉的东西。

开源 SOTA（AF3）0.72；闭源前沿约 0.78（Gemini 2.5 Pro、Claude Opus 4.7）。这个差距比 VideoMME 的开源-闭源差值更小，说明音频-LLM 正在走向成熟。

> MMAU (Massive Multimodal Audio Understanding) is the 2024-2025 audio reasoning benchmark: 10,000 audio-text QA pairs across speech, music, environmental sounds. Covers classification, temporal reasoning, causal reasoning, open-ended QA. Tests what cascaded pipelines systematically miss. ... Open SOTA (AF3) at 0.72; proprietary frontier ~0.78 (Gemini 2.5 Pro, Claude Opus 4.7). The gap is smaller than VideoMME's open-vs-closed delta, indicating audio-LLMs are maturing.

```figure
audio-text-ctc
```

## Use It · 实战用法

`code/main.py`：

- 用纯标准库实现 log-Mel 频谱图计算：加窗、朴素 DFT、Mel 滤波器组。
- 音频 Q-former 骨架：给定编码器输出帧，计算 Q、K、V、注意力并产出 N 个 token。
- 在一个玩具任务上做级联 vs 端到端对比。

> `code/main.py`: Implements log-Mel spectrogram computation in stdlib: windowing, naive DFT, Mel filter-bank. Audio Q-former skeleton: given encoder output frames, compute Q, K, V, attention, and emit N tokens. Cascaded-vs-end-to-end comparison on a toy task.

## Ship It · 交付

本课产出 `outputs/skill-audio-llm-pipeline-picker.md`。给定一个音频任务（转写、音乐标注、情绪推断、多说话人分离、环境音分类），它会在级联、端到端 AF3 或混合方案之间做选择。

> This lesson produces `outputs/skill-audio-llm-pipeline-picker.md`. Given an audio task (transcription, music tagging, emotion inference, multi-speaker diarization, environment classification), it picks cascaded, end-to-end AF3, or a hybrid.

## Exercises · 练习

1. 计算 30 秒片段、16kHz、25ms 窗、10ms 步进、80 个 Mel 频带的 log-Mel 频谱图维度。48kHz 时会怎么变？

2. 为什么 Whisper 在音乐上表现不佳？BEATs 捕捉到了哪些 Whisper 没有的音频特征？

3. 64 查询 vs 32 查询的音频 Q-former：任务复杂到什么程度时 64 才划算？32 省下的算力换来了什么？

4. 阅读 AF3 论文第 4 节的按需思考。提出三个最受益于思维链的音频任务。

5. 用 AF3 的输出实现一个最小说话人分离（diarization）流水线。你如何标记说话人切换？

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|------------------------|
| Log-Mel 频谱图（Log-Mel spectrogram） | 「Mel 特征」 | 经 Mel 滤波器组后得到的对数幅值二维（时间，频率）数组 |
| 音频 Q-former（Audio Q-former） | 「音频 Perceiver」 | 从音频编码器输出到固定长度查询的交叉注意力瓶颈，查询喂给 LLM |
| 级联（Cascaded） | 「先 ASR 后 LLM」 | Whisper 转写、文本 LLM 推理的流水线；丢失声学信息 |
| 端到端（End-to-end） | 「音频-LLM」 | 音频特征经 Q-former 直接进入 LLM；保留声学信号 |
| BEATs | 「AudioSet 音频编码器」 | 在 AudioSet 上训练的 SSL Transformer；音乐 + 环境音见长 |
| MMAU | 「音频推理基准」 | 横跨语音、音乐、环境的 1 万对 QA；2024 年评估标准 |
| 按需思考（On-demand thinking） | 「音频 CoT」 | 模型可在最终答案前选择性地输出推理 token，准确率提升 3-5 个点 |

## Further Reading · 延伸阅读

- [Radford et al. — Whisper (arXiv:2212.04356)](https://arxiv.org/abs/2212.04356)
- [Chu et al. — Qwen-Audio (arXiv:2311.07919)](https://arxiv.org/abs/2311.07919)
- [Goel et al. — Audio Flamingo 3 (arXiv:2507.08128)](https://arxiv.org/abs/2507.08128)
- [Tang et al. — SALMONN (arXiv:2310.13289)](https://arxiv.org/abs/2310.13289)
- [Gong et al. — LTU (arXiv:2305.10790)](https://arxiv.org/abs/2305.10790)
