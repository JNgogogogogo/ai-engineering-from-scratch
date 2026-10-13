# Voice Anti-Spoofing & Audio Watermarking — ASVspoof 5, AudioSeal, WaveVerify · 语音反欺骗与音频水印——ASVspoof 5、AudioSeal、WaveVerify

> 声音克隆的普及速度超过了防御的普及速度。2026 年的生产级语音系统需要两样东西：一个能分辨真伪语音的检测器（AASIST、RawNet2），和一个能在压缩与编辑后存活的水印（AudioSeal）。两个都上，否则就不要上线声音克隆。
>
> Voice cloning shipped faster than defenses. 2026 production voice systems need two things: a detector (AASIST, RawNet2) that classifies real vs fake speech, and a watermark (AudioSeal) that survives compression and editing. Ship both or do not ship voice cloning.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 6 · 06 (Speaker Recognition), Phase 6 · 08 (Voice Cloning)
**Time:** ~75 minutes

---

## The Problem · 问题在哪

三种相关的防御：

1. **反欺骗 / 深度伪造检测（anti-spoofing / deepfake detection）。** 给定一段音频，它是合成的还是真的？ASVspoof 基准（ASVspoof 2019 → 2021 → 5）是黄金标准。
2. **音频水印（audio watermarking）。** 在生成的音频里嵌入一个不可感知的信号，检测器之后可以把它提取出来。AudioSeal（Meta）和 WavMark 是开源选择。
3. **可认证的溯源（authenticated provenance）。** 音频文件的加密签名 + 元数据。C2PA / Content Authenticity Initiative。

检测应对的是不配合的攻击者。水印应对的是合规——AI 生成的音频应当能被识别为 AI 生成。2026 年，两者都是必需品。

> Three related defenses:
> 1. **Anti-spoofing / deepfake detection.** Given an audio clip, is it synthetic or real? ASVspoof benchmarks (ASVspoof 2019 → 2021 → 5) are the gold standard.
> 2. **Audio watermarking.** Embed an imperceptible signal in generated audio that a detector can extract later. AudioSeal (Meta) and WavMark are the open options.
> 3. **Authenticated provenance.** Cryptographic signing of audio files + metadata. C2PA / Content Authenticity Initiative.
> Detection handles adversaries who don't cooperate. Watermarking handles compliance — AI-generated audio should be identifiable as such. Both are required in 2026.

---

## The Concept · 概念

![反欺骗 vs 水印 vs 溯源——三层防御](../assets/spoofing-watermark.svg)

### ASVspoof 5 — the 2024-2025 benchmark · ASVspoof 5——2024-2025 年的基准

相对以往版本的最大变化：

- **众包数据**（不是录音棚级的干净）——真实条件。
- **约 2000 名说话人**（此前约 100 人）。
- **32 种攻击算法。** TTS + 语音转换 + 对抗扰动。
- **两条赛道。** Countermeasure（CM）独立检测；面向生物识别系统的 Spoofing-robust ASV（SASV）。

ASVspoof 5 上的 SOTA：约 7.23% EER。更早的 ASVspoof 2019 LA 上：0.42% EER。真实部署：在野外音频上预期 5-10% EER。

> Biggest change from prior editions: ...
> State-of-the-art on ASVspoof 5: ~7.23% EER. On the older ASVspoof 2019 LA: 0.42% EER. Real-world deployment: expect 5-10% EER on in-the-wild clips.

---

### AASIST and RawNet2 — detection model families · AASIST 与 RawNet2——检测模型家族

**AASIST**（2021 年，持续更新到 2026）。谱特征上的图注意力（graph-attention）。当前 ASVspoof 5 countermeasure 任务的 SOTA。

**RawNet2。** 原始波形上的卷积前端 + TDNN 骨干。更简单的基线；微调之后仍有竞争力。

**NeXt-TDNN + SSL 特征。** 2025 年的变体：ECAPA 风格 + WavLM 特征 + focal loss。在 ASVspoof 2019 LA 上拿下 0.42% EER 的就是它。

> **AASIST** (2021, updated through 2026). Graph-attention on spectral features. Current SOTA on ASVspoof 5 countermeasure task.
> **RawNet2.** Convolutional front-end over raw waveform + TDNN backbone. Simpler baseline; still competitive with fine-tuning.
> **NeXt-TDNN + SSL features.** 2025 variant: ECAPA-style + WavLM features + focal loss. Achieves the 0.42% EER on ASVspoof 2019 LA.

---

### AudioSeal — the 2024 watermark default · AudioSeal——2024 年的默认水印

Meta 的 **AudioSeal**（2024 年 1 月，v0.2 为 2024 年 12 月）。关键设计：

- **局部化（localized）。** 以 16 kHz 采样分辨率（1/16000 s）逐帧检测水印。
- **生成器 + 检测器联合训练。** 生成器学会嵌入不可闻的信号；检测器学会在各种数据增广下找到它。
- **鲁棒。** 扛得住 MP3 / AAC 压缩、EQ、±10% 变速、+10 dB SNR 的噪声混合。
- **快。** 检测器以 485 倍实时运行；比 WavMark 快 1000 倍。
- **容量。** 每条话语可嵌入 16 bit 载荷（可编码模型 ID、生成时间戳、用户 ID）。

> Meta's **AudioSeal** (Jan 2024, v0.2 Dec 2024). Key design: ...
> **Localized.** Detects the watermark per-frame at 16 kHz sample resolution (1/16000 s).
> **Generator + detector jointly trained.** Generator learns to embed inaudible signal; detector learns to find it through augmentations.
> **Robust.** Survives MP3 / AAC compression, EQ, speed-shift ±10%, noise mix +10 dB SNR.
> **Fast.** Detector runs at 485× realtime; 1000× faster than WavMark.

---

### WavMark · WavMark

AudioSeal 之前的开源基线。可逆神经网络，32 bit/秒。问题：

- 同步的暴力搜索很慢。
- 高斯噪声或 MP3 压缩就能把它去掉。
- 对实时不友好。

> The pre-AudioSeal open baseline. Invertible neural network, 32 bits/sec. Problems: Synchronization brute-force is slow. ... Not real-time friendly.

---

### WaveVerify (July 2025) · WaveVerify（2025 年 7 月）

针对 AudioSeal 的弱点——特别是时间篡改（反转、变速）。使用基于 FiLM 的生成器 + Mixture-of-Experts 检测器。在标准攻击上与 AudioSeal 相当；还能处理时间编辑。

> Addresses AudioSeal's weaknesses — specifically temporal manipulations (reversal, speed). Uses FiLM-based generator + Mixture-of-Experts detector. Competitive with AudioSeal on standard attacks; handles temporal edits.

---

### The gap adversaries exploit · 攻击者利用的缺口

来自 AudioMarkBench 的结论："under pitch shift, all watermarks show Bit Recovery Accuracy below 0.6, indicating near-complete removal."（变调之下，所有水印的 Bit Recovery Accuracy 都低于 0.6，等于几乎被完全去除。）**变调（pitch-shift）是万能攻击。** 2026 年没有任何水印能完全扛住激进的音高修改。这就是为什么你需要在水印之外再配上检测（AASIST）。

> From AudioMarkBench: "under pitch shift, all watermarks show Bit Recovery Accuracy below 0.6, indicating near-complete removal." **Pitch-shift is the universal attack.** No 2026 watermark is fully robust to aggressive pitch modification. This is why you need detection (AASIST) alongside watermarking.

---

### C2PA / Content Authenticity Initiative · C2PA / Content Authenticity Initiative

不是 ML 技术——而是一种清单（manifest）格式。音频文件携带关于创建工具、作者、日期的加密签名元数据。Audobox / Seamless 在用它。对溯源有好处；但如果坏分子重新编码并剥掉元数据，它毫无办法。

> Not an ML technique — a manifest format. Audio files carry cryptographically signed metadata about creation tool, author, date. Audobox / Seamless use it. Good for provenance; does nothing if a bad actor re-encodes and strips metadata.

```figure
v4-audio-watermark
```

---

## Build It · 动手造

### Step 1: a simple spectral-feature detector (toy) · 一个简单的谱特征检测器（玩具）

```python
def spectral_rolloff(spec, percentile=0.85):
    cum = 0
    total = sum(spec)
    if total == 0:
        return 0
    threshold = total * percentile
    for k, v in enumerate(spec):
        cum += v
        if cum >= threshold:
            return k
    return len(spec) - 1

def is_suspicious(audio):
    spec = magnitude_spectrum(audio)
    rolloff = spectral_rolloff(spec)
    return rolloff / len(spec) > 0.92
```

合成语音的高频能量常常异常平坦。生产检测器用的是 AASIST，不是这个。但直觉是成立的。

> Synthetic speech often has unusually flat high-frequency energy. Production detectors use AASIST, not this. But the intuition holds.

### Step 2: AudioSeal embed + detect · AudioSeal 嵌入 + 检测

```python
from audioseal import AudioSeal
import torch

generator = AudioSeal.load_generator("audioseal_wm_16bits")
detector = AudioSeal.load_detector("audioseal_detector_16bits")

audio = load_wav("generated.wav", sr=16000)[None, None, :]
payload = torch.tensor([[1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0]])
watermark = generator.get_watermark(audio, sample_rate=16000, message=payload)
watermarked = audio + watermark

result, decoded_payload = detector.detect_watermark(watermarked, sample_rate=16000)
# result: float in [0, 1] — probability of watermark presence
# decoded_payload: 16 bits; match against embedded payload
```

### Step 3: evaluation — EER · 评估——EER

```python
def eer(real_scores, fake_scores):
    thresholds = sorted(set(real_scores + fake_scores))
    best = (1.0, 0.0)
    for t in thresholds:
        far = sum(1 for s in fake_scores if s >= t) / len(fake_scores)
        frr = sum(1 for s in real_scores if s < t) / len(real_scores)
        if abs(far - frr) < best[0]:
            best = (abs(far - frr), (far + frr) / 2)
    return best[1]
```

### Step 4: the production integration · 生产集成

```python
def safe_tts(text, voice, clone_reference=None):
    if clone_reference is not None:
        verify_consent(user_id, clone_reference)
    audio = tts_model.synthesize(text, voice)
    audio_with_wm = audioseal_embed(audio, payload=build_payload(user_id, model_id))
    manifest = c2pa_sign(audio_with_wm, user_id, timestamp=now())
    return audio_with_wm, manifest
```

每次生成都要带上：(1) 水印，(2) 签过名的 manifest，(3) 符合保留策略的审计日志。

> Every generation ships: (1) watermark, (2) signed manifest, (3) retention-policy-compliant audit log.

---

## Use It · 实战用法

| 用例 | 防御 |
|----------|---------|
| 上线 TTS / 声音克隆 | 每个输出都嵌 AudioSeal（没得商量） |
| 生物识别声纹解锁 | AASIST + ECAPA 集成；加活体挑战（liveness challenge） |
| 呼叫中心欺诈检测 | 对 20% 的来电抽样跑 AASIST |
| 播客真实性 | 上传时做 C2PA 签名；AI 生成的加 AudioSeal |
| 研究 / 训练检测器 | ASVspoof 5 train/dev/eval 集 |

---

## Pitfalls · 常见的坑

- **只嵌水印、检测器从不运行。** 毫无意义。把检测器放进你的 CI。
- **检测不做校准。** 在 ASVspoof LA 上训练的 AASIST 会过拟合；真实世界精度下降。在你的领域数据上校准。
- **变调缺口。** 激进变调能去除大多数水印。留一个检测兜底。
- **剥元数据换个地方重发。** C2PA 重新编码就能绕过。永远把加密 + 感知（水印）防御一起上。
- **把活体检测当反欺骗。** 让用户念一个随机短语。能防重放攻击，防不了实时克隆。

> **Watermark without detector ever running.** Pointless. Ship the detector in your CI.
> **Detection without calibration.** AASIST trained on ASVspoof LA overfits; real-world accuracy drops. Calibrate on your domain.
> **Pitch-shift gap.** Aggressive pitch shift removes most watermarks. Have a detection fallback.
> **Metadata strip-and-rehost.** C2PA is trivially bypassable by re-encoding. Always add cryptographic + perceptual (watermark) defense together.
> **Liveness as detection.** Ask user to say a random phrase. Prevents replay attacks but not real-time cloning.

---

## Ship It · 交付

保存为 `outputs/skill-spoof-defender.md`：为一个语音生成部署挑选检测模型、水印、溯源 manifest 和运营手册。

> Save as `outputs/skill-spoof-defender.md`. Pick detection model, watermark, provenance manifest, and operational playbook for a voice-gen deployment.

---

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。在合成音频上做玩具检测器 + 玩具水印嵌入/检测。
2. **中等。** 安装 `audioseal`，在一段 TTS 输出里嵌入 16 bit 载荷，再解码。用噪声破坏音频并测量 Bit Recovery Accuracy。
3. **困难。** 在 ASVspoof 2019 LA 上微调一个 RawNet2 或 AASIST。测量 EER。在一组留出的 F5-TTS 生成音频上测试——看看 OOD 检测退化成什么样。

> 1. **Easy.** Run `code/main.py`. Toy detector + toy watermark embed/detect on synthetic audio.
> 2. **Medium.** Install `audioseal`, embed a 16-bit payload in a TTS output, re-decode. Corrupt the audio with noise and measure Bit Recovery Accuracy.
> 3. **Hard.** Fine-tune a RawNet2 or AASIST on ASVspoof 2019 LA. Measure EER. Test on a held-out set of F5-TTS-generated clips — see how OOD detection degrades.

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| ASVspoof | 那个基准 | 两年一届的挑战赛；2024 年 = ASVspoof 5。 |
| CM（countermeasure，反制） | 检测器 | 分类器：真语音 vs 合成 / 转换语音。 |
| SASV | 说话人验证 + CM | 生物识别 + 欺骗检测一体化。 |
| AudioSeal | Meta 的水印 | 局部化、16 bit 载荷、比 WavMark 快 485 倍。 |
| Bit Recovery Accuracy | 水印存活率 | 攻击之后恢复出来的载荷 bit 比例。 |
| C2PA | 溯源 manifest | 关于创建 / 作者的加密签名元数据。 |
| AASIST | 检测器家族 | 基于图注意力的反欺骗 SOTA。 |

---

## Further Reading · 延伸阅读

- [Todisco et al. (2024). ASVspoof 5](https://dl.acm.org/doi/10.1016/j.csl.2025.101825) —— 当前基准。
- [Defossez et al. (2024). AudioSeal](https://arxiv.org/abs/2401.17264) —— 默认的水印方案。
- [Chen et al. (2025). WaveVerify](https://arxiv.org/abs/2507.21150) —— 面向时间攻击的 MoE 检测器。
- [Jung et al. (2022). AASIST](https://arxiv.org/abs/2110.01200) —— SOTA 检测骨干。
- [AudioMarkBench (2024)](https://proceedings.neurips.cc/paper_files/paper/2024/file/5d9b7775296a641a1913ab6b4425d5e8-Paper-Datasets_and_Benchmarks_Track.pdf) —— 鲁棒性评估。
- [C2PA specification](https://spec.c2pa.org/specifications/specifications/2.4/index.html) —— 溯源 manifest 格式。
