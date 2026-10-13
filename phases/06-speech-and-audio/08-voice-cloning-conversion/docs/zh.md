# Voice Cloning & Voice Conversion · 声音克隆与语音转换

> Voice cloning reads your text in someone else's voice. Voice conversion rewrites your voice into someone else's while preserving what you said. Both hang on the same decomposition: separate speaker identity from content.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 6 · 06 (Speaker Recognition), Phase 6 · 07 (TTS)
**Time:** ~75 minutes

---

## The Problem · 问题在哪

2026 年，一段 5 秒的音频加上一张消费级 GPU，就足以高质量克隆任何人的声音。ElevenLabs、F5-TTS、OpenVoice v2、VoiceBox 都提供 zero-shot 或 few-shot 克隆。这项技术既是福祉（无障碍 TTS、配音、辅助语音），也是武器（诈骗电话、政治深度伪造、IP 盗用）。

两个紧密相关的任务：

- **声音克隆（voice cloning，TTS 侧）：** 文本 + 5 秒参考语音 → 该音色的音频。
- **语音转换（voice conversion，VC，语音侧）：** 源音频（人 A 说 X）+ 人 B 的参考语音 → 人 B 说 X 的音频。

两者都把波形分解为（内容、说话人、韵律），再把一个来源的内容与另一个来源的说话人重新组合。

2026 年你发布时必须面对的关键约束：**在欧盟（《AI 法案》，2026 年 8 月起可执行）和加州（AB 2905，2025 年生效），水印与同意门槛是法定要求**。你的流水线必须内嵌听不见的水印，并拒绝未经同意的克隆。

> In 2026, a 5-second audio clip is enough to produce a high-quality clone of anyone's voice with a consumer GPU. ElevenLabs, F5-TTS, OpenVoice v2, VoiceBox all ship zero-shot or few-shot cloning. The technology is a blessing (accessibility TTS, dubbing, assistive voices) and a weapon (scam calls, political deepfakes, IP theft).
> Both factor a waveform into (content, speaker, prosody) and recombine content from one source with speaker from another.
> Key constraint you now ship under in 2026: **watermarking and consent gates are legally required in the EU (AI Act, enforceable August 2026) and in California (AB 2905, effective 2025)**. Your pipeline must emit an inaudible watermark and refuse non-consensual clones.

---

## The Concept · 概念

![声音克隆 vs 语音转换：分解、替换说话人、重组](../assets/voice-cloning.svg)

**Zero-shot 克隆。** 把 5 秒片段交给一个在数千说话人上训练过的模型。说话人编码器（speaker encoder）把片段映射为说话人嵌入（speaker embedding）；TTS 解码器以该嵌入加文本为条件生成语音。

使用者：F5-TTS（2024）、YourTTS（2022）、XTTS v2（2024）、OpenVoice v2（2024）。

**Few-shot 微调。** 录 5–30 分钟目标音色的语音，用 LoRA 微调基座模型约一小时。质量从「还行」跃升到「无法分辨」。Coqui 和 ElevenLabs 都支持这种模式；社区也在 F5-TTS 上这么用。

**语音转换（VC）。** 两大家族：

- **识别-再合成（recognition-synthesis）。** 先跑一个类 ASR 模型提取内容表示（如软音素后验、PPG），再用目标说话人嵌入重新合成。对语言和口音鲁棒。使用者：KNN-VC（2023）、Diff-HierVC（2023）。
- **解耦（disentanglement）。** 训练一个自编码器，在瓶颈处把内容、说话人、韵律在隐空间里分开。推理时替换说话人嵌入。质量低一些但更快。使用者：AutoVC（2019）、VITS-VC 变体。

**基于神经编解码的克隆（2024+）。** VALL-E、VALL-E 2、NaturalSpeech 3、VoiceBox——把音频当作 SoundStream / EnCodec 输出的离散 token，在 codec token 上训练大型自回归或 flow-matching 模型。短提示上的质量可与 ElevenLabs 比肩。

> **Zero-shot cloning.** Pass a 5-second clip to a model that has been trained on thousands of speakers. The speaker encoder maps the clip to a speaker embedding; the TTS decoder conditions on that embedding plus text.
> **Voice conversion (VC).** Two families:
> **Neural codec-based cloning (2024+).** VALL-E, VALL-E 2, NaturalSpeech 3, VoiceBox — treat audio as discrete tokens from SoundStream / EnCodec, train a large autoregressive or flow-matching model over codec tokens. Quality comparable to ElevenLabs on short prompts.

---

### The ethics bit, not a bolt-on · 伦理不是外挂，是必答题

**水印（watermarking）。** PerTh（Perth）和 SilentCipher（2024）能在音频里嵌入不可感知的约 16–32 bit ID。扛得住重编码、流媒体传输和常见编辑。已达到生产可用的开源方案。

**同意门槛（consent gates）。** 每一个克隆输出都必须配一条可验证的同意记录。"I, Rohit, on 2026-04-22, authorize this voice for X purpose." 存入防篡改日志。

**检测（detection）。** AASIST、RawNet2、Wav2Vec2-AASIST 都是现成的检测器。ASVspoof 2025 挑战赛公布：最先进检测器对 ElevenLabs、VALL-E 2、Bark 输出的 EER 为 0.8–2.3%。

> **Watermarking.** PerTh (Perth) and SilentCipher (2024) embed a ~16-32 bit ID imperceptibly in the audio. Survives re-encoding, streaming, and common edits. Production-ready open source.
> **Consent gates.** Must pair every cloned output with a verifiable consent record. "I, Rohit, on 2026-04-22, authorize this voice for X purpose." Store in a tamper-evident log.
> **Detection.** AASIST, RawNet2, and Wav2Vec2-AASIST ship as detectors. ASVspoof 2025 challenge published EERs of 0.8–2.3% for state-of-the-art detectors against ElevenLabs, VALL-E 2, and Bark outputs.

---

### Numbers (2026) · 数字一览（2026）

| 模型 | Zero-shot？ | SECS（目标相似度） | WER（可懂度） | 参数量 |
|-------|-----------|--------------------|--------------|--------|
| F5-TTS | 是 | 0.72 | 2.1% | 335M |
| XTTS v2 | 是 | 0.65 | 3.5% | 470M |
| OpenVoice v2 | 是 | 0.70 | 2.8% | 220M |
| VALL-E 2 | 是 | 0.77 | 2.4% | 370M |
| VoiceBox | 是 | 0.78 | 2.1% | 330M |

SECS > 0.70 时，大多数听众基本分辨不出克隆与目标。

```figure
sp-voice-factorize
```

> SECS > 0.70 is generally indistinguishable from the target for most listeners.

---

## Build It · 动手造

### Step 1: decompose with recognition-synthesis (code-only demo in main.py) · 用识别-再合成做分解（main.py 中是纯代码演示）

```python
def clone_pipeline(ref_audio, text, target_embedder, tts_model):
    speaker_emb = target_embedder.encode(ref_audio)
    mel = tts_model(text, speaker=speaker_emb)
    return vocoder(mel)
```

概念上很简单；实现的大头在 `tts_model` 和说话人编码器里。

> Conceptually simple; implementation mass is in `tts_model` and speaker encoder.

### Step 2: zero-shot clone with F5-TTS · 用 F5-TTS 做 zero-shot 克隆

```python
from f5_tts.api import F5TTS
tts = F5TTS()
wav = tts.infer(
    ref_file="rohit_5s.wav",
    ref_text="The quick brown fox jumps over the lazy dog.",
    gen_text="Please add milk and bread to my list.",
)
```

参考转写必须与音频严格一致；不一致会破坏对齐。

> Reference transcript must exactly match the audio; mismatch breaks alignment.

### Step 3: voice conversion with KNN-VC · 用 KNN-VC 做语音转换

```python
import torch
from knnvc import KNNVC  # 2023 model, https://github.com/bshall/knn-vc
vc = KNNVC.load("wavlm-base-plus")
out_wav = vc.convert(source="my_voice.wav", target_pool=["alice_1.wav", "alice_2.wav"])
```

KNN-VC 跑 WavLM 提取源音频与目标池的逐帧嵌入，然后把每个源帧替换成池中离它最近的邻居。非参数化方法，一分钟的目标语音即可工作。

> KNN-VC runs WavLM to extract per-frame embeddings for source and target pool, then replaces each source frame with its nearest neighbor in the pool. Non-parametric, works with a minute of target speech.

### Step 4: embed a watermark · 嵌入水印

```python
from silentcipher import SilentCipher
sc = SilentCipher(model="2024-06-01")
payload = b"consent_id:abc123;ts:1745353200"
watermarked = sc.embed(wav, sr=24000, message=payload)
detected = sc.detect(watermarked, sr=24000)   # returns payload bytes
```

约 32 bit 的载荷，经得起 MP3 重编码和轻度噪声。

> ~32 bits of payload, detectable after MP3 re-encode and light noise.

### Step 5: consent gate · 同意门槛

```python
def cloned_inference(text, ref_audio, consent_record):
    assert verify_signature(consent_record), "Signed consent required"
    assert consent_record["speaker_id"] == hash_speaker(ref_audio)
    wav = tts.infer(ref_file=ref_audio, gen_text=text)
    wav = watermark(wav, payload=consent_record["id"])
    return wav
```

---

## Use It · 实战用法

2026 年的选型组合：

| 场景 | 选择 |
|-----------|------|
| 5 秒 zero-shot 克隆，开源 | F5-TTS 或 OpenVoice v2 |
| 商业化生产级克隆 | ElevenLabs Instant Voice Clone v2.5 |
| 语音转换（改写声音） | KNN-VC 或 Diff-HierVC |
| 多说话人微调 | StyleTTS 2 + 说话人适配器 |
| 跨语言克隆 | XTTS v2 或 VALL-E X |
| 深度伪造检测 | Wav2Vec2-AASIST |

> The 2026 stack:

---

## Pitfalls · 常见的坑

- **参考转写没对齐。** F5-TTS 一类的模型要求参考文本与参考音频严格一致，连标点都不例外。
- **带混响的参考音频。** 回声会毁掉克隆。近距离干声录制。
- **情绪不匹配。** 用「欢快」的参考音频做训练，克隆出来干什么都欢快。让参考音频的情绪匹配目标用途。
- **语言泄漏。** 克隆一个说英语的人，再让模型说法语，口音往往还是会带过去；用跨语言模型（XTTS、VALL-E X）。
- **没有水印。** 2026 年 8 月起在欧盟无法合法发布。

> **Misaligned reference transcript.** F5-TTS and similar require the reference text to match the reference audio exactly, punctuation included.
> **Reverberant reference.** Echo kills the clone. Record dry, close-mic.
> **Emotional mismatch.** Training reference "cheerful" produces cheerful clones of everything. Match reference emotion to target use.
> **Language leakage.** Cloning an English speaker then asking the model to speak French often carries the accent anyway; use cross-lingual models (XTTS, VALL-E X).
> **No watermark.** Legally unshippable in EU from Aug 2026.

---

## Ship It · 交付

保存为 `outputs/skill-voice-cloner.md`：设计一条带同意门槛 + 水印 + 质量目标的克隆或转换流水线。

> Save as `outputs/skill-voice-cloner.md`. Design a cloning or conversion pipeline with consent gate + watermark + quality target.

---

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。它通过计算交换前后两个「说话人」之间的余弦相似度，演示说话人嵌入的交换。
2. **中等。** 用 OpenVoice v2 克隆你自己的声音。测量参考与克隆之间的 SECS，并经 Whisper 测量 CER。
3. **困难。** 给 20 个克隆音频加 SilentCipher 水印，跑一遍 128 kbps MP3 编码+解码后检测载荷。报告比特准确率（bit-accuracy）。

> 1. **Easy.** Run `code/main.py`. Demonstrates the speaker-embedding swap by computing the cosine between two "speakers" pre and post swap.
> 2. **Medium.** Use OpenVoice v2 to clone your own voice. Measure SECS between reference and clone. Measure CER via Whisper.
> 3. **Hard.** Apply SilentCipher watermark to 20 clones, run them through 128 kbps MP3 encode+decode, detect the payload. Report bit-accuracy.

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Zero-shot clone（零样本克隆） | 5 秒就够 | 预训练模型 + 说话人嵌入；无需训练。 |
| PPG | 音素后验图（phonetic posteriorgram） | 逐帧 ASR 后验，用作与语言无关的内容表示。 |
| KNN-VC | 最近邻转换 | 把每个源帧替换成目标池中最近的帧。 |
| Neural codec TTS | VALL-E 风格 | 在 EnCodec/SoundStream token 上的自回归模型。 |
| Watermark（水印） | 听不见的签名 | 嵌在音频里的比特，扛得住重编码。 |
| SECS | 克隆保真度 | 目标与克隆说话人嵌入之间的余弦相似度。 |
| AASIST | 深度伪造检测器 | 反欺骗（anti-spoof）模型；检测合成语音。 |

---

## Further Reading · 延伸阅读

- [Chen et al. (2024). F5-TTS](https://arxiv.org/abs/2410.06885) —— 开源 SOTA 的 zero-shot 克隆。
- [Baevski et al. / Microsoft (2023). VALL-E](https://arxiv.org/abs/2301.02111) 与 [VALL-E 2 (2024)](https://arxiv.org/abs/2406.05370) —— 神经编解码 TTS。
- [Qian et al. (2019). AutoVC](https://arxiv.org/abs/1905.05879) —— 基于解耦的语音转换。
- [Baas, Waubert de Puiseau, Kamper (2023). KNN-VC](https://arxiv.org/abs/2305.18975) —— 基于检索的 VC。
- [SilentCipher (2024) — Audio Watermarking](https://github.com/sony/silentcipher) —— 生产可用的 32-bit 音频水印。
- [ASVspoof 2025 results](https://www.asvspoof.org/) —— 检测器与合成器的军备竞赛，2026 年更新。
