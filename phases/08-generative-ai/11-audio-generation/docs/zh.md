# Audio Generation · 音频生成

音频是 16-48 kHz 的一维信号。五秒钟的片段有 80-240k 个采样点，没有任何 transformer 能直接对这种长度的序列做注意力。2026 年所有生产级音频模型的解法都一样：神经编解码器（Encodec、SoundStream、DAC）先把音频压成 50-75 Hz 的离散 token，再由 transformer 或扩散模型生成这些 token。

> Audio is a 1-D signal at 16-48 kHz. A five-second clip is 80-240k samples. No transformer attends to that sequence directly. The solution for every production audio model in 2026 is the same: a neural codec (Encodec, SoundStream, DAC) compresses audio to discrete tokens at 50-75 Hz, and a transformer or diffusion model generates tokens.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 6 · 02 (Audio Features), Phase 6 · 04 (ASR), Phase 8 · 06 (DDPM)
**Time:** ~45 minutes

## The Problem · 问题在哪

三类音频生成任务：

1. **文本转语音（text-to-speech）。** 给定文本，生成语音。干净语音是窄带信号、有很强的语音学结构 —— 「token 之上的 transformer」把它解决得很好。VALL-E（微软）、NaturalSpeech 3、ElevenLabs、OpenAI TTS。
2. **音乐生成。** 给定提示（文本、旋律、和弦进行、流派），生成音乐。分布要宽得多。MusicGen（Meta）、Stable Audio 2.5、Suno v4、Udio、Riffusion。
3. **音效 / 声音设计。** 给定提示，生成环境音或拟音（Foley）。AudioGen、AudioLDM 2、Stable Audio Open。

三者都跑在同一套底座上：神经音频编解码器 + token 自回归（token-AR）或扩散生成器。

> Three audio generation tasks:
> 1. **Text-to-speech.** Given text, produce speech. ...
> 2. **Music generation.** Given a prompt (text, melody, chord progression, genre), produce music. ...
> 3. **Audio effects / sound design.** Given a prompt, produce ambient sound or Foley. ...
> All three run on the same substrate: neural audio codec + token-AR or diffusion generator.

## The Concept · 概念

![音频生成：编解码器 token + transformer 或扩散](../assets/audio-generation.svg)

### Neural audio codecs · 神经音频编解码器

Encodec（Meta，2022）、SoundStream（Google，2021）、Descript Audio Codec（DAC，2023）。卷积编码器把波形压缩成每个时间步一个向量；残差向量量化（residual vector quantization, RVQ）把每个向量转换成 K 个码本（codebook）索引的级联。解码器逆向执行这一过程。24 kHz 音频、2 kbps 码率、8 个 RVQ 码本、75 Hz，等于每秒 600 个 token。

```
waveform (16000 samples/sec)
    └─ encoder conv ─┐
                     ├─ RVQ layer 1 → indices at 75 Hz
                     ├─ RVQ layer 2 → indices at 75 Hz
                     ├─ ...
                     └─ RVQ layer 8
```

> Encodec (Meta, 2022), SoundStream (Google, 2021), Descript Audio Codec (DAC, 2023). A convolutional encoder compresses waveform to a per-timestep vector; residual vector quantization (RVQ) converts each vector to a cascade of K codebook indices. Decoder reverses it. 24 kHz audio at 2 kbps using 8 RVQ codebooks at 75 Hz = 600 tokens/sec.

### Two generative paradigms on top · 其上的两种生成范式

**Token 自回归（token-autoregressive）。** 把 RVQ token 摊平成一个序列，跑一个 decoder-only transformer。MusicGen 用「delayed parallel」方式、以每条流各自错开的偏移并行发射 K 条码本流。VALL-E 从文本提示 + 3 秒声音样本生成语音 token。

**隐空间扩散（latent diffusion）。** 把编解码器 token 打包成连续隐变量，或者用类别扩散（categorical diffusion）对它们建模。Stable Audio 2.5 在连续音频隐变量上用流匹配（flow matching）。AudioLDM 2 用文本→mel→音频的扩散。

2024-2026 的趋势：流匹配正在音乐生成上胜出（推理更快、样本更干净），而 token-AR 仍主导语音，因为它天然因果、适合流式输出。

> **Token-autoregressive.** Flatten RVQ tokens into a sequence, run a decoder-only transformer. MusicGen uses "delayed parallel" to emit K codebook streams in parallel with per-stream offsets. VALL-E generates speech tokens from a text prompt + 3-second voice sample.
> **Latent diffusion.** Pack codec tokens as continuous latents or model them with categorical diffusion. Stable Audio 2.5 uses flow matching on continuous audio latents. AudioLDM 2 uses text-to-mel-to-audio diffusion.
> The 2024-2026 trend: flow matching is winning for music (faster inference, cleaner samples) while token-AR still dominates speech because it is naturally causal and streams well.

## Production landscape · 生产环境全景

| 系统 | 任务 | 骨干架构 | 延迟 |
|--------|------|----------|---------|
| ElevenLabs V3 | TTS | Token-AR + 神经声码器 | 首 token ~300ms |
| OpenAI GPT-4o audio | 全双工语音 | 端到端多模态自回归 | ~200ms |
| NaturalSpeech 3 | TTS | 隐空间流匹配 | 非流式 |
| Stable Audio 2.5 | 音乐 / 音效 | DiT + 音频隐变量上的流匹配 | 1 分钟片段 ~10s |
| Suno v4 | 完整歌曲 | 未公开；疑似 token-AR | 每首 ~30s |
| Udio v1.5 | 完整歌曲 | 未公开 | 每首 ~30s |
| MusicGen 3.3B | 音乐 | Encodec 32kHz 上的 Token-AR | 实时 |
| AudioCraft 2 | 音乐 + 音效 | 流匹配 | 5s 片段 ~5s |
| Riffusion v2 | 音乐 | 频谱图扩散 | ~10s |

```figure
score-matching
```

## Build It · 动手造

`code/main.py` 模拟核心思想：在由两种不同「风格」生成的合成「音频 token」序列上训练一个微型下一 token（next-token）transformer（风格 A 是低 token 与高 token 交替，风格 B 是单调爬升）。以风格为条件并采样。

> `code/main.py` simulates the core idea: train a tiny next-token transformer on synthetic "audio token" sequences generated from two distinct "styles" (alternating low and high tokens for style A, monotonic ramp for style B). Condition on style and sample.

### Step 1: synthetic audio tokens · 第 1 步：合成音频 token

```python
def make_tokens(style, length, vocab_size, rng):
    if style == 0:  # "speech-like": alternating
        return [i % vocab_size for i in range(length)]
    # "music-like": ramp
    return [(i * 3) % vocab_size for i in range(length)]
```

### Step 2: train a tiny token predictor · 第 2 步：训练一个微型 token 预测器

一个以风格为条件的 bigram 式预测器。重点是这个模式：编解码器 token → 交叉熵训练 → 自回归采样。

> A bigram-style predictor conditioned on style. The point is the pattern: codec tokens → cross-entropy training → autoregressive sampling.

### Step 3: sample conditionally · 第 3 步：条件采样

给定风格 token 和一个起始 token，从预测分布中采样下一个 token。持续采样 20-40 个 token。

> Given the style token and a starting token, sample the next token from the predicted distribution. Continue for 20-40 tokens.

## Pitfalls · 常见坑

- **编解码器质量封顶输出质量。** 如果编解码器无法忠实地表示某个声音，生成器再好也救不回来。DAC 是当前开源最佳。
- **RVQ 误差累积。** 每一层 RVQ 建模的是上一层的残差。第 1 层的误差会向后传播。在较高层用温度 0 采样会有帮助。
- **音乐结构。** 30 秒的音频在 75 Hz 下是 20k+ 个 token，对 transformer 来说很难。MusicGen 用滑动窗口 + 提示延续；Stable Audio 用更短的片段 + 交叉淡入淡出（crossfading）。
- **边界伪影。** 在生成的片段之间做交叉淡化需要仔细的 overlap-add。
- **对干净数据的胃口。** 音乐生成器需要数万小时的授权音乐。Suno / Udio 被 RIAA 起诉（2024）把这一点摆上了台面。
- **声音克隆伦理。** 3 秒样本加一段文本提示，就足以让 VALL-E / XTTS / ElevenLabs 克隆一个声音。每个生产级模型都需要滥用检测 + 退出名单（opt-out）。

> **Codec quality caps output quality.** If the codec can't represent a sound faithfully, no amount of generator quality helps. ...
> **RVQ error accumulation.** Each RVQ layer models the residual of the previous. Errors on layer 1 propagate. ...
> **Musical structure.** 30 seconds of tokens is 20k+ tokens at 75 Hz. Hard for transformers. ...
> **Voice cloning ethics.** A 3-second sample plus a text prompt is enough for VALL-E / XTTS / ElevenLabs to clone a voice. Every production model needs abuse detection + opt-out lists.

## Use It · 实战用法

| 任务 | 2026 年技术栈 |
|------|------------|
| 商业 TTS | ElevenLabs、OpenAI TTS 或 Azure Neural |
| 声音克隆（已验证同意） | XTTS v2（开源）或 ElevenLabs Pro |
| 背景音乐，快速出活 | Stable Audio 2.5 API、Suno 或 Udio |
| 带歌词的音乐 | Suno v4 或 Udio v1.5 |
| 音效 / 拟音 | AudioCraft 2、ElevenLabs SFX 或 Stable Audio Open |
| 实时语音代理 | GPT-4o realtime 或 Gemini Live |
| 开源权重音乐研究 | MusicGen 3.3B、Stable Audio Open 1.0、AudioLDM 2 |
| 配音 / 翻译 | HeyGen、ElevenLabs Dubbing |

## Ship It · 交付

保存 `outputs/skill-audio-brief.md`。这个 skill 接收一份音频需求简报（任务、时长、风格、声音、授权），输出：模型 + 托管方式、提示词格式（流派标签、风格描述符、结构标记）、编解码器 + 生成器 + 声码器（vocoder）链路、种子（seed）协议，以及评测计划（MOS / CLAP score / TTS 的 CER / 用户 A/B 测试）。

> Save `outputs/skill-audio-brief.md`. Skill takes an audio brief (task, duration, style, voice, license) and outputs: model + hosting, prompt format (genre tags, style descriptors, structural markers), codec + generator + vocoder chain, seed protocol, and eval plan (MOS / CLAP score / CER for TTS / user A/B).

## Exercises · 练习

1. **简单。** 跑 `code/main.py` 并显式设置风格。验证生成的序列符合该风格的模式。
2. **中等。** 加入 delayed parallel 解码：模拟 2 条必须保持错开 1 步的 token 流。训练一个联合预测器。
3. **困难。** 用 HuggingFace transformers 在本地跑 MusicGen-small。用三个不同的提示各生成一段 10 秒片段；对风格贴合度做 A/B 对比。

> 1. **Easy.** Run `code/main.py` and set style explicitly. Verify the generated sequences match the style's pattern. ...
> 2. **Medium.** Add delayed parallel decoding: simulate 2 streams of tokens that must stay offset by 1 step. Train a joint predictor. ...
> 3. **Hard.** Use HuggingFace transformers to run MusicGen-small locally. Generate a 10-second clip with three different prompts; A/B for style adherence.

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Codec（编解码器） | "神经压缩" | 音频的编码器 / 解码器；典型输出是 50-75 Hz 的 token。 |
| RVQ | "残差 VQ" | K 个量化器的级联；每一级建模上一级的残差。 |
| Token | "一个编解码符号" | 码本中的离散索引；典型取 1024 或 2048。 |
| Delayed parallel | "错位码本" | 以错开的偏移发射 K 条 token 流，从而缩短序列长度。 |
| Flow matching（流匹配） | "2024 年音频的赢家" | 扩散的直线路径替代品；采样更快。 |
| Voice prompt（声音提示） | "3 秒样本" | 引导被克隆声音的说话人嵌入或 token 前缀。 |
| Mel spectrogram（梅尔频谱图） | "那张可视化图" | 对数量级的感知频谱图；许多 TTS 系统都在用。 |
| Vocoder（声码器） | "mel 转波形" | 把 mel 频谱图转换回音频的神经组件。 |

## Production note: audio is a streaming problem · 生产备注：音频是一个流式问题

音频是唯一一种用户期望它*边生成边到达*、而不是一次性全部给出的输出模态。用生产术语说，这意味着 TPOT（Time Per Output Token，每输出 token 耗时）很重要，因为用户的收听速度才是目标吞吐 —— 而不是他们的阅读速度。对以 ~75 token/秒（Encodec）分词的 16kHz 音频来说，服务器必须为每个用户生成 ≥75 token/秒，才能保证播放流畅。

两个架构上的推论：

- **流匹配音频模型无法简单地流式化。** Stable Audio 2.5 和 AudioCraft 2 一次前向渲染固定长度的片段。要流式输出，你得把片段切块并在边界上做重叠 —— 类似滑动窗口扩散 —— 相比编解码器 AR 模型增加 100-300ms 的延迟开销。

如果产品是「实时语音聊天」或「实时音乐续写」，选编解码器 AR 路线。如果是「提交后渲染一段 30 秒的片段」，流匹配在质量和总延迟上更优。

> Audio is the one output modality users expect to arrive *as it is generated*, not all-at-once. In production terms this means TPOT matters (Time Per Output Token) because the user's listening speed is the target throughput — not their reading speed. For 16kHz audio tokenized at ~75 tokens/second (Encodec), the server must generate ≥75 tokens/sec per user to keep playback smooth.
> Two architectural consequences:
> - **Flow-matching audio models cannot stream trivially.** Stable Audio 2.5 and AudioCraft 2 render a fixed clip length in one pass. To stream, you chunk the clip and overlap boundaries — think sliding-window diffusion — adding 100-300ms of latency overhead vs a codec AR model.
> If the product is "live voice chat" or "real-time music continuation", pick the codec AR path. If it is "render a 30-second clip on submit", flow-matching wins on quality and total latency.

## Further Reading · 延伸阅读

- [Défossez et al. (2022). Encodec: High Fidelity Neural Audio Compression](https://arxiv.org/abs/2210.13438) —— 编解码器的事实标准。
- [Zeghidour et al. (2021). SoundStream](https://arxiv.org/abs/2107.03312) —— 第一个被广泛使用的神经音频编解码器。
- [Kumar et al. (2023). High-Fidelity Audio Compression with Improved RVQGAN (DAC)](https://arxiv.org/abs/2306.06546) —— DAC。
- [Wang et al. (2023). Neural Codec Language Models are Zero-Shot Text to Speech Synthesizers (VALL-E)](https://arxiv.org/abs/2301.02111) —— VALL-E。
- [Copet et al. (2023). Simple and Controllable Music Generation (MusicGen)](https://arxiv.org/abs/2306.05284) —— MusicGen。
- [Liu et al. (2023). AudioLDM 2: Learning Holistic Audio Generation with Self-supervised Pretraining](https://arxiv.org/abs/2308.05734) —— AudioLDM 2。
- [Stability AI (2025). Stable Audio 2.5](https://stability.ai/news-updates/stability-ai-introduces-stable-audio-25-the-first-audio-model-built-for-enterprise-sound-production-at-scale) —— 2025 年用流匹配做的文本生成音乐。
