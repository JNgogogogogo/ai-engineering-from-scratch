# Music Generation — MusicGen, Stable Audio, Suno, and the Licensing Earthquake · 音乐生成——MusicGen、Stable Audio、Suno 与许可大地震

> 2026 music generation: Suno v5 and Udio v4 dominate commercial; MusicGen, Stable Audio Open, and ACE-Step lead open-source. The technical problem is mostly solved. The legal problem (Warner Music $500M settlement, UMG settlement) reshaped the field in 2025-2026.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 6 · 02 (Spectrograms), Phase 4 · 10 (Diffusion Models)
**Time:** ~75 minutes

---

## The Problem · 问题在哪

文本 → 一段 30 秒到 4 分钟的音乐，带歌词、人声和曲式结构。三个子问题：

1. **器乐生成（instrumental generation）。** "lo-fi hip-hop drums with warm keys" 这样的文本 → 音频。MusicGen、Stable Audio、AudioLDM。
2. **整首歌生成（带人声 + 歌词）。** "Country song about rainy Texas nights" → 完整歌曲。Suno、Udio、YuE、ACE-Step。
3. **条件生成 / 可控生成。** 延长现有片段、重生成一段桥段、切换曲风、分轨（stem separation）或修补（inpaint）。Udio 的 inpainting + 分轨是 2026 年必须对标的功能。

> Text → a 30-second to 4-minute music clip, with lyrics, vocals, and structure. Three sub-problems:
> 1. **Instrumental generation.** Text like "lo-fi hip-hop drums with warm keys" → audio. MusicGen, Stable Audio, AudioLDM.
> 2. **Song generation (with vocals + lyrics).** "Country song about rainy Texas nights" → full song. Suno, Udio, YuE, ACE-Step.
> 3. **Conditional / controllable.** Extend an existing clip, regenerate a bridge, swap genre, stem-separate, or inpaint. Udio's inpainting + stem separation is the 2026 feature to match.

---

## The Concept · 概念

![音乐生成：token-LM vs 扩散，2026 年模型地图](../assets/music-generation.svg)

### Token LM over neural-codec tokens · 神经编解码 token 上的 token 语言模型

Meta 的 **MusicGen**（2023，MIT 许可）及众多衍生品：以文本/旋律嵌入为条件，自回归预测 EnCodec token（32 kHz、4 个码本），再用 EnCodec 解码。300M - 3.3B 参数。强 baseline；超过 30 秒就吃力。

**ACE-Step**（开源，2026 年 4 月发布 4B XL）把它扩展为整首歌、歌词条件的生成。这是开源社区手里最接近 Suno 的东西。

### Diffusion over mels or latents · 在梅尔谱或隐变量上做扩散

**Stable Audio（2023）**与 **Stable Audio Open（2024）**：对压缩后的音频做潜在扩散（latent diffusion）。擅长 loop、声音设计、氛围纹理。不太擅长有结构的完整歌曲。

**AudioLDM / AudioLDM2**：用 T2I 风格的潜在扩散做文本到音频，泛化到音乐、音效、语音。

### Hybrid (production) — Suno, Udio, Lyria · 混合架构（生产级）——Suno、Udio、Lyria

闭源权重。大概率是 AR codec LM + 基于扩散的声码器，再配上专门的人声 / 鼓 / 旋律输出头。Suno v5（2026）是 ELO 1293 的质量领头羊。Udio v4 加上了 inpainting + 分轨（bass、drums、vocals 可分开下载）。

### Evaluation · 评测方法

- **FAD（Fréchet Audio Distance）。** 用 VGGish 或 PANNs 特征，度量生成音频分布与真实音频分布在嵌入层面的距离。越低越好。MusicGen small 在 MusicCaps 上 FAD 为 4.5；SOTA 约 3.0。
- **音乐性（subjective，主观）。** 人类偏好。Suno v5 以 ELO 1293 领先。
- **文本-音频对齐。** 提示词与输出之间的 CLAP 分数。
- **音乐性瑕疵。** 不合拍的过渡、人声短语漂移、超过 30 秒后结构散架。

> Meta's **MusicGen** (2023, MIT) and many derivatives: condition on text/melody embeddings, autoregressively predict EnCodec tokens (32 kHz, 4 codebooks), decode with EnCodec.
> **FAD (Fréchet Audio Distance).** Embedding-level distance between generated vs real audio distribution using VGGish or PANNs features. Lower is better. MusicGen small: 4.5 FAD on MusicCaps; SOTA ~3.0.
> **Musicality (subjective).** Human preference. Suno v5 ELO 1293 leads.
> **Text-audio alignment.** CLAP score between prompt and output.
> **Musicality artifacts.** Off-beat transitions, vocal-phrase drift, loss of structure past 30 s.

---

## 2026 model map · 2026 年模型地图

| 模型 | 参数量 | 长度 | 人声 | 许可证 |
|-------|--------|--------|--------|---------|
| MusicGen-large | 3.3B | 30 秒 | 无 | MIT |
| Stable Audio Open | 1.2B | 47 秒 | 无 | Stability 非商业 |
| ACE-Step XL（2026 年 4 月） | 4B | &gt; 2 分钟 | 有 | Apache-2.0 |
| YuE | 7B | &gt; 2 分钟 | 有，多语言 | Apache-2.0 |
| Suno v5（闭源） | ? | 4 分钟 | 有，ELO 1293 | 商业 |
| Udio v4（闭源） | ? | 4 分钟 | 有 + 分轨 | 商业 |
| Google Lyria 3（闭源） | ? | 实时 | 有 | 商业 |
| MiniMax Music 2.5 | ? | 4 分钟 | 有 | 商业 API |

---

## The legal landscape (2025-2026) · 法律版图（2025–2026）

- **Warner Music 与 Suno 和解。** 5 亿美元。WMG 现在对 Suno 上的 AI 相似性、音乐版权和用户生成曲目拥有监督权。UMG 也与 Udio 达成了类似和解。
- **EU AI Act** + **加州 SB 942**：AI 生成的音乐必须披露。
- **Riffusion / MusicGen** 采用 MIT 许可，没有合规包袱，但也没有商业级人声。

可以放心发布的模式：

1. 只生成器乐（MusicGen、Stable Audio Open，MIT/CC0 输出）。
2. 用商业 API（Suno、Udio、ElevenLabs Music），按次生成取得许可。
3. 在自有或已获授权的曲库上训练（大多数企业最终走到这一步）。
4. 给生成结果打上水印 + 元数据标签。

> **Warner Music vs Suno settlement.** $500M. WMG now has oversight of AI-likeness, music rights, and user-generated tracks on Suno. Similar UMG settlement on Udio.
> **EU AI Act** + **California SB 942**: AI-generated music must be disclosed.
> **Riffusion / MusicGen** under MIT have no compliance baggage but also no commercial vocals.
> Safe-to-ship patterns:
> 1. Generate instrumental only (MusicGen, Stable Audio Open, MIT/CC0 outputs).
> 2. Use commercial APIs (Suno, Udio, ElevenLabs Music) with per-generation license.
> 3. Train on owned or licensed catalog (most enterprises end up here).
> 4. Tag generations with watermarks + metadata.

```figure
sp-codec-tokens
```

---

## Build It · 动手造

### Step 1: generate with MusicGen · 用 MusicGen 生成

```python
from audiocraft.models import MusicGen
import torchaudio

model = MusicGen.get_pretrained("facebook/musicgen-small")
model.set_generation_params(duration=10)
wav = model.generate(["upbeat synthwave with driving drums, 128 BPM"])
torchaudio.save("out.wav", wav[0].cpu(), 32000)
```

三个尺寸：`small`（300M，快）、`medium`（1.5B）、`large`（3.3B）。要验证「这个点子行不行」，small 就够了。

> Three sizes: `small` (300M, fast), `medium` (1.5B), `large` (3.3B). Small is enough for "does the idea land."

### Step 2: melody conditioning · 旋律条件

```python
melody, sr = torchaudio.load("humming.wav")
wav = model.generate_with_chroma(
    ["jazz piano cover"],
    melody.squeeze(),
    sr,
)
```

MusicGen-melody 接收色度图（chromagram），在保留旋律的同时替换音色。适合「把这段旋律给我改成弦乐四重奏」。

> MusicGen-melody takes a chromagram and preserves the tune while swapping timbre. Useful for "give me this melody as a string quartet."

### Step 3: FAD evaluation · FAD 评测

```python
from frechet_audio_distance import FrechetAudioDistance
fad = FrechetAudioDistance()

fad.get_fad_score("generated_folder/", "reference_folder/")
```

计算 VGGish 嵌入距离。适合做曲风级别的回归测试；替代不了真人听众。

> Computes VGGish-embedding distance. Useful for genre-level regression tests; not a substitute for human listeners.

### Step 4: adding to the LLM-music workflow · 接入 LLM 音乐工作流

结合第 7-8 课的思路：

```python
prompt = "Write a 30-second jazz loop. Describe the drums, bass, and piano voicing."
description = llm.complete(prompt)
music = musicgen.generate([description], duration=30)
```

> Combine with the ideas from Lessons 7-8:

---

## Use It · 实战用法

| 目标 | 技术栈 |
|------|-------|
| 器乐声音设计 | Stable Audio Open |
| 游戏 / 自适应音乐 | Google Lyria RealTime（闭源） |
| 带人声的完整歌曲（商业） | Suno v5 或 Udio v4，需明确许可 |
| 带人声的完整歌曲（开源） | ACE-Step XL 或 YuE |
| 短广告 jingle | MusicGen 以哼唱参考做旋律条件生成 |
| 音乐视频背景 | MusicGen + Stable Video Diffusion |

---

## Pitfalls that still ship in 2026 · 2026 年依然会踩的坑

- **洗版权的提示词。** "Song in the style of Taylor Swift"——商业版 Suno/Udio 现在会过滤这类提示，开源模型不会。自己加一份过滤词表。
- **超过 30 秒的重复 / 漂移。** AR 模型会打转。把多段生成做交叉淡化（crossfade），或者用 ACE-Step 保证结构连贯。
- **速度漂移（tempo drift）。** 模型会跑偏 BPM。在提示词里写 BPM 标签，并用 librosa 的 `beat_track` 做后置过滤。
- **人声可懂度。** Suno 很出色；开源模型唱词常常含混。歌词重要就用商业 API 或微调。
- **单声道输出。** 开源模型生成单声道或假立体声。用正经的立体声重建来升级（ezst、Cartesia 的 stereo diffusion）。

> **Copyright-laundering prompts.** "Song in the style of Taylor Swift" — commercial Suno/Udio filter these now, open models do not. Add your own filter list.
> **Repetition / drift past 30 s.** AR models loop. Crossfade multiple generations, or use ACE-Step for structural coherence.
> **Tempo drift.** Models wander off the BPM. Use BPM tags in the prompt and post-filter with librosa's `beat_track`.
> **Vocal intelligibility.** Suno is excellent; open models are often mushy on words. If lyrics matter, use a commercial API or fine-tune.
> **Mono output.** Open models generate mono or fake-stereo. Upgrade with a proper stereo reconstruction (ezst, Cartesia's stereo diffusion).

---

## Ship It · 交付

保存为 `outputs/skill-music-designer.md`：为一次音乐生成部署选定模型、许可策略、时长 / 结构方案和披露元数据。

> Save as `outputs/skill-music-designer.md`. Pick model, license strategy, length / structure plan, and disclosure metadata for a music-gen deployment.

---

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。它用 ASCII 符号生成一段「生成式」和弦进行 + 鼓点——一幅音乐生成的漫画。想听的话可以用任意 MIDI 渲染器播放。
2. **中等。** 安装 `audiocraft`，用 MusicGen-small 按 4 个曲风提示各生成 10 秒片段，对参考曲风集测 FAD。
3. **困难。** 用 ACE-Step（或 MusicGen-melody），对同一段旋律用不同音色提示生成三个变体。计算与提示词的 CLAP 相似度以验证对齐。

> 1. **Easy.** Run `code/main.py`. It produces a "generative" chord progression + drum pattern as ASCII symbols — a music-gen cartoon. Play it back via any MIDI renderer if you want.
> 2. **Medium.** Install `audiocraft`, generate 10-second clips across 4 genre prompts with MusicGen-small, measure FAD against a reference genre set.
> 3. **Hard.** Using ACE-Step (or MusicGen-melody), generate three variations of the same tune with different timbre prompts. Compute CLAP similarity to the prompt to verify alignment.

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| FAD | 音频版 FID | 真实与生成音频嵌入分布之间的 Fréchet 距离。 |
| Chromagram（色度图） | 旋律即音高 | 每帧 12 维向量；旋律条件化的输入。 |
| Stems（分轨） | 乐器轨道 | 分离出的 bass / drums / vocals / melody，WAV 格式。 |
| Inpainting（修补） | 重生成某一段 | 遮住一个时间窗口；模型只重生成这一段。 |
| CLAP | 文本-音频版 CLIP | 对比式音频-文本嵌入；评测文本-音频对齐。 |
| EnCodec | 音乐编解码器 | MusicGen 使用的 Meta 神经编解码器；32 kHz、4 个码本。 |

---

## Further Reading · 延伸阅读

- [Copet et al. (2023). MusicGen](https://arxiv.org/abs/2306.05284) —— 开源自回归基准。
- [Evans et al. (2024). Stable Audio Open](https://arxiv.org/abs/2407.14358) —— 声音设计的默认选择。
- [ACE-Step](https://github.com/ace-step/ACE-Step) —— 开源 4B 整首歌生成器，2026 年 4 月。
- [Suno v5 platform docs](https://suno.com) —— 商业质量领头羊。
- [AudioLDM2](https://arxiv.org/abs/2308.05734) —— 面向音乐 + 音效的潜在扩散。
- [WMG-Suno settlement coverage](https://www.musicbusinessworldwide.com/warner-music-group-settles-with-suno-strikes-first-of-its-kind-deal-with-ai-song-generator/) —— 2025 年 11 月的先例。
