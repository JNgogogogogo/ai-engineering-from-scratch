# Audio Evaluation — WER, MOS, UTMOS, MMAU, FAD, and the Open Leaderboards · 音频评估——WER、MOS、UTMOS、MMAU、FAD 与公开榜单

> 测不了的东西上不了线。这一课点名 2026 年每个音频任务的指标：ASR（WER、CER、RTFx）、TTS（MOS、UTMOS、SECS、ASR 往返 WER）、音频语言（MMAU、LongAudioBench）、音乐（FAD、CLAP）、说话人（EER）。外加用来对比的公开榜单。
>
> You cannot ship what you cannot measure. This lesson names the 2026 metrics for every audio task: ASR (WER, CER, RTFx), TTS (MOS, UTMOS, SECS, WER-on-ASR-round-trip), audio-language (MMAU, LongAudioBench), music (FAD, CLAP), and speaker (EER). Plus the leaderboards where you compare.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 6 · 04, 06, 07, 09, 10; Phase 2 · 09 (Model Evaluation)
**Time:** ~60 minutes

---

## The Problem · 问题在哪

每个音频任务都有多个指标，每个指标测量不同的轴。用错指标，你就会上线一个在仪表盘上好看、在生产环境里很糟糕的模型。2026 年的权威清单：

| 任务 | 主要指标 | 次要指标 |
|------|---------|-----------|
| ASR | WER | CER · RTFx · 首 token 延迟 |
| TTS | MOS / UTMOS | SECS · WER-on-ASR-round-trip · CER · TTFA |
| Voice cloning（声音克隆） | SECS（ECAPA 余弦） | MOS · CER |
| Speaker verification（说话人验证） | EER | 工作点处的 minDCF · FAR / FRR |
| Diarization（说话人分离） | DER | JER · 说话人混淆 |
| Audio classification（音频分类） | top-1 · mAP | macro F1 · 逐类 recall |
| Music generation（音乐生成） | FAD | CLAP · 评审团 MOS |
| Audio language model（音频语言模型） | MMAU-Pro | LongAudioBench · AudioCaps FENSE |
| Streaming S2S（流式语音到语音） | 延迟 P50/P95 | WER · MOS |

> Every audio task has multiple metrics, each measuring a different axis. Using the wrong metric is how you ship a model that looks great on your dashboard and terribly in production. The 2026 canonical list:

---

## The Concept · 概念

![音频评估矩阵——指标 vs 任务 vs 2026 榜单](../assets/eval-landscape.svg)

### ASR metrics · ASR 指标

**WER（Word Error Rate，词错误率）。** `(S + D + I) / N`。打分之前先小写化、去标点、归一化数字。用 `jiwer` 或 OpenAI 的 `whisper_normalizer`。&lt; 5% = 朗读语音上达到人类水平。

**CER（Character Error Rate，字错误率）。** 同样的公式，字符级。用于声调语言（普通话、粤语）——这类语言的分词有歧义。

**RTFx（inverse real-time factor，逆实时率）。** 每墙钟秒处理的音频秒数。越高越好。Parakeet-TDT 达到 3380×。Whisper-large-v3 约 30×。

**First-token latency（首 token 延迟）。** 从音频输入到第一个转写 token 的墙钟时间。流式场景的关键指标。Deepgram Nova-3：约 150 ms。

> **WER (Word Error Rate).** `(S + D + I) / N`. Lowercase, strip punctuation, normalize numbers before scoring. Use `jiwer` or OpenAI's `whisper_normalizer`. &lt; 5% = human-parity read speech.
> **CER (Character Error Rate).** Same formula, character-level. Used for tone languages (Mandarin, Cantonese) where word segmentation is ambiguous.
> **RTFx (inverse real-time factor).** Audio seconds processed per wall-clock second. Higher is better. Parakeet-TDT hits 3380×. Whisper-large-v3 is ~30×.
> **First-token latency.** Wall-clock from audio input to first transcript token. Critical for streaming. Deepgram Nova-3: ~150 ms.

---

### TTS metrics · TTS 指标

**MOS（Mean Opinion Score，平均意见分）。** 1-5 分的人类评分。黄金标准但慢。每个样本收集 20+ 听众、每个模型 100+ 个样本。

**UTMOS（2022-2026）。** 学习得到的 MOS 预测器。在标准基准上与人类 MOS 的相关性约 0.9。F5-TTS：UTMOS 3.95；真实值：4.08。

**SECS（Speaker Encoder Cosine Similarity）。** 用于声音克隆。参考音频与克隆输出之间 ECAPA 嵌入的余弦相似度。&gt; 0.75 = 可辨认的克隆。

**WER-on-ASR-round-trip。** 用 Whisper 跑一遍 TTS 输出，对输入文本计算 WER。捕捉可懂度回退。2026 SOTA：&lt; 2% CER。

**TTFA（time-to-first-audio）。** 墙钟延迟。Kokoro-82M：约 100 ms；F5-TTS：约 1 s。

> **MOS (Mean Opinion Score).** 1-5 human rating. Gold standard but slow. Collect 20+ listeners per sample, 100+ samples per model.
> **UTMOS (2022-2026).** Learned MOS predictor. Correlates ~0.9 with human MOS on standard benchmarks. F5-TTS: UTMOS 3.95; ground truth: 4.08.
> **SECS (Speaker Encoder Cosine Similarity).** For voice cloning. ECAPA embedding cosine between reference and cloned output. &gt; 0.75 = recognizable clone.
> **WER-on-ASR-round-trip.** Run Whisper over TTS output, compute WER against the input text. Catches intelligibility regressions. 2026 SOTA: &lt; 2% CER.
> **TTFA (time-to-first-audio).** Wall-clock latency. Kokoro-82M: ~100 ms; F5-TTS: ~1 s.

---

### Voice-cloning-specific · 声音克隆专项

**SECS + MOS + CER** 三件套一起看。SECS 高但 MOS 低的克隆 = 音色对但不自然；反过来 = 声音自然但说话人不对。

> **SECS + MOS + CER** as a triple. Cloning that scores high SECS but low MOS means timbre-right-but-unnatural; the opposite means natural voice but wrong speaker.

---

### Speaker verification · 说话人验证

**EER（Equal Error Rate，等错误率）。** 错误接受率（False Accept Rate）等于错误拒绝率（False Reject Rate）的那个阈值点。ECAPA 在 VoxCeleb1-O 上：0.87%。

**minDCF（min Detection Cost，最小检测代价）。** 在选定工作点（通常 FAR=0.01）上的加权代价。比 EER 更贴近生产。

> **EER (Equal Error Rate).** The threshold where False Accept Rate equals False Reject Rate. ECAPA on VoxCeleb1-O: 0.87%.
> **minDCF (min Detection Cost).** Weighted cost at a chosen operating point (often FAR=0.01). More production-relevant than EER.

---

### Diarization · 说话人分离

**DER（Diarization Error Rate，分离错误率）。** `(FA + Miss + Confusion) / total_speaker_time`。漏掉的语音 + 误报的语音 + 说话人混淆，各占比例。AMI 会议：DER 10-20% 是现实的。pyannote 3.1 + 商业的 Precision-2：录音良好时 &lt;10% DER。

**JER（Jaccard Error Rate）。** DER 的替代指标，对短段偏差更鲁棒。

> **DER (Diarization Error Rate).** `(FA + Miss + Confusion) / total_speaker_time`. Missed speech + false-alarm speech + speaker-confusion, each as a fraction. AMI meetings: DER ~10-20% is realistic. pyannote 3.1 + Precision-2 commercial: &lt;10% DER on well-recorded audio.
> **JER (Jaccard Error Rate).** Alternative to DER, robust to short-segment bias.

---

### Audio classification · 音频分类

多标签：所有类别上的 **mAP（mean Average Precision，平均精度均值）**。AudioSet：BEATs-iter3 为 0.548 mAP。

多类互斥：**top-1、top-5 准确率**。Speech Commands v2：99.0% top-1（Audio-MAE）。

类别不平衡：**macro F1** + **逐类 recall**。报告逐类数据——聚合准确率会掩盖哪些类在失败。

> Multi-label: **mAP (mean Average Precision)** over all classes. AudioSet: 0.548 mAP for BEATs-iter3.
> Multi-class exclusive: **top-1, top-5 accuracy**. Speech Commands v2: 99.0% top-1 (Audio-MAE).
> Imbalanced: **macro F1** + **per-class recall**. Report per-class — aggregate accuracy hides which classes fail.

---

### Music generation · 音乐生成

**FAD（Fréchet Audio Distance）。** 真实音频与生成音频的 VGGish 嵌入分布之间的距离。MusicGen-small 在 MusicCaps 上：4.5。MusicLM：4.0。越低越好。

**CLAP Score。** 用 CLAP 嵌入算的文本-音频对齐分。&gt; 0.3 = 合理对齐。

**Listening panel MOS（评审团 MOS）。** 对消费级音乐来说仍然是最终裁判。Suno v5 在 TTS Arena 上 ELO 1293（来自成对人类偏好）。

> **FAD (Fréchet Audio Distance).** Distance between VGGish-embedding distributions of real vs generated audio. MusicGen-small on MusicCaps: 4.5. MusicLM: 4.0. Lower better.
> **CLAP Score.** Text-audio alignment score using CLAP embeddings. &gt; 0.3 = reasonable alignment.
> **Listening panel MOS.** Still the final word for consumer-grade music. Suno v5 ELO 1293 on TTS Arena (from paired human preferences).

---

### Audio-language benchmarks · 音频语言基准

**MMAU（Massive Multi-Audio Understanding）。** 1 万个音频问答对。

**MMAU-Pro。** 1800 道难题，四个类别：speech / sound / music / multi-audio。四选一的随机基线是 25%。Gemini 2.5 Pro 总体约 60%；multi-audio 上所有模型都只有约 22%。

**LongAudioBench。** 多分钟长度的片段 + 语义查询。Audio Flamingo Next 赢过 Gemini 2.5 Pro。

**AudioCaps / Clotho。** 字幕生成基准。SPICE、CIDEr、FENSE 指标。

> **MMAU (Massive Multi-Audio Understanding).** 10k audio-QA pairs.
> **MMAU-Pro.** 1800 hard items, four categories: speech / sound / music / multi-audio. Random chance 25% on 4-way. Gemini 2.5 Pro overall ~60%; multi-audio ~22% across all models.
> **LongAudioBench.** Multi-minute clips with semantic queries. Audio Flamingo Next beats Gemini 2.5 Pro.
> **AudioCaps / Clotho.** Captioning benchmarks. SPICE, CIDEr, FENSE metrics.

---

### Streaming speech-to-speech · 流式语音到语音

**延迟 P50 / P95 / P99。** 从用户说完到第一个可听回应的墙钟时间。Moshi：200 ms；GPT-4o Realtime：300 ms。

输出上的 **WER / MOS**。

**Barge-in 响应性。** 从用户打断到助手静音的时间。目标 &lt; 150 ms。

> **Latency P50 / P95 / P99.** Wall-clock from end-of-user-speech to first audible response. Moshi: 200 ms; GPT-4o Realtime: 300 ms.
> **WER / MOS** on the output.
> **Barge-in responsiveness.** Time from user interrupt to assistant mute. Target &lt; 150 ms.

---

### The 2026 leaderboards · 2026 年的榜单

| 榜单 | 赛道 | URL |
|------------|--------|-----|
| Open ASR Leaderboard (HF) | 英语 + 多语言 + 长音频 | `huggingface.co/spaces/hf-audio/open_asr_leaderboard` |
| TTS Arena (HF) | 英语 TTS | `huggingface.co/spaces/TTS-AGI/TTS-Arena` |
| Artificial Analysis Speech | TTS + STT，成对投票算 ELO | `artificialanalysis.ai/speech` |
| MMAU-Pro | LALM 推理 | `sonalkum.github.io/mmau-pro` |
| SpeakerBench / VoxSRC | 说话人识别 | `voxsrc.github.io` |
| MMAU music subset | 音乐 LALM |（在 MMAU 内） |
| HEAR benchmark | 自监督音频 | `hearbenchmark.com` |

```figure
sp-wer-align
```

---

## Build It · 动手造

### Step 1: WER with normalization · 带归一化的 WER

```python
from jiwer import wer, Compose, ToLowerCase, RemovePunctuation, Strip

transform = Compose([ToLowerCase(), RemovePunctuation(), Strip()])
score = wer(
    truth="Please turn on the lights.",
    hypothesis="please turn on the light",
    truth_transform=transform,
    hypothesis_transform=transform,
)
# ~0.17
```

### Step 2: TTS round-trip WER · TTS 往返 WER

```python
def ttr_wer(tts_model, asr_model, texts):
    errors = []
    for txt in texts:
        audio = tts_model.synthesize(txt)
        recog = asr_model.transcribe(audio)
        errors.append(wer(truth=txt, hypothesis=recog))
    return sum(errors) / len(errors)
```

### Step 3: SECS for voice cloning · 声音克隆的 SECS

```python
from speechbrain.inference.speaker import EncoderClassifier
sv = EncoderClassifier.from_hparams("speechbrain/spkrec-ecapa-voxceleb")

emb_ref = sv.encode_batch(load_wav("reference.wav"))
emb_clone = sv.encode_batch(load_wav("cloned.wav"))
secs = torch.nn.functional.cosine_similarity(emb_ref, emb_clone, dim=-1).item()
```

### Step 4: FAD for music generation · 音乐生成的 FAD

```python
from frechet_audio_distance import FrechetAudioDistance
fad = FrechetAudioDistance()
score = fad.get_fad_score("generated_folder/", "reference_folder/")
```

### Step 5: EER for speaker verification (same code as Lesson 6) · 说话人验证的 EER（与第 6 课相同的代码）

```python
def eer(same_scores, diff_scores):
    thresholds = sorted(set(same_scores + diff_scores))
    best = (1.0, 0.0)
    for t in thresholds:
        far = sum(1 for s in diff_scores if s >= t) / len(diff_scores)
        frr = sum(1 for s in same_scores if s < t) / len(same_scores)
        if abs(far - frr) < best[0]:
            best = (abs(far - frr), (far + frr) / 2)
    return best[1]
```

---

## Use It · 实战用法

每一次部署都配一个固定的评估 harness，每次模型更新都跑。三条铁律：

1. **打分之前先归一化。** 小写化、去标点、数字展开。报告你用的归一化规则。
2. **报告分布，不是平均值。** 延迟用 P50/P95/P99。分类用逐类 recall。MMAU 逐类别。
3. **跑一个权威的公开基准。** 即使你的生产数据不同，报告 Open ASR / TTS Arena / MMAU 的成绩能让评审做同口径比较。

> Pair every deploy with a fixed eval harness that runs on every model update. Three cardinal rules:
> 1. **Normalize before scoring.** Lowercase, punctuation-strip, number-expand. Report the normalization rule.
> 2. **Report distributions, not averages.** P50/P95/P99 for latency. Per-class recall for classification. Per-category for MMAU.
> 3. **Run one canonical public benchmark.** Even if your production data differs, reporting on Open ASR / TTS Arena / MMAU lets reviewers compare apples-to-apples.

---

## Pitfalls · 常见的坑

- **UTMOS 外推。** 它在 VCTK 风格的干净语音上训练；对噪声 / 克隆 / 情感音频打分不准。
- **MOS 评审团偏差。** 20 个 Amazon Mechanical Turk 众包工人 ≠ 20 个目标用户。利害大就花钱请领域评审团。
- **FAD 依赖参考集。** 跨模型比较时必须对同一个参考分布。
- **聚合 WER。** 总体 5% 的 WER 可能掩盖口音语音上 30% 的 WER。按人群切片报告。
- **公开基准饱和。** 多数前沿模型在标准基准上已经接近天花板。建一个能反映你自己流量的内部留出集。

> **UTMOS extrapolation.** Trained on VCTK-style clean speech; scores noisy / cloned / emotional audio poorly.
> **MOS panel bias.** 20 Amazon Mechanical Turk workers ≠ 20 target users. Pay for a domain panel if stakes are high.
> **FAD depends on reference set.** Compare against the same reference distribution across models.
> **Aggregate WER.** A 5% WER overall can hide 30% WER on accented speech. Report by demographic slice.
> **Public benchmark saturation.** Most frontier models are near the ceiling on standard benchmarks. Build an in-house held-out set that reflects your traffic.

---

## Ship It · 交付

保存为 `outputs/skill-audio-evaluator.md`：为任意音频模型发布挑选指标、基准和报告格式。

> Save as `outputs/skill-audio-evaluator.md`. Pick metrics, benchmarks, and reporting format for any audio model release.

---

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。在玩具输入上计算 WER / CER / EER / SECS / 类 FAD / 类 MMAU。
2. **中等。** 搭一个 TTS 往返 WER harness。把你的 Kokoro 或 F5-TTS 输出喂给 Whisper。在 50 条提示上计算 WER。标记 WER &gt; 10% 的提示。
3. **困难。** 用 MMAU-Pro 的 speech + multi-audio 子集（各 50 题）给你的第 10 课选的 LALM 打分。报告逐类别准确率并与公开数字比较。

> 1. **Easy.** Run `code/main.py`. Compute WER / CER / EER / SECS / FAD-ish / MMAU-ish on toy inputs.
> 2. **Medium.** Build a TTS round-trip WER harness. Run your Kokoro or F5-TTS output through Whisper. Compute WER over 50 prompts. Flag prompts with WER &gt; 10%.
> 3. **Hard.** Score your Lesson 10 LALM choice on MMAU-Pro speech + multi-audio subsets (50 items each). Report per-category accuracy and compare with the published number.

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| WER | ASR 分数 | 归一化之后词级的 `(S+D+I)/N`。 |
| CER | 字符版 WER | 用于声调语言或字符级系统。 |
| MOS | 人类主观分 | 1-5 评分；20+ 听众 × 100 样本。 |
| UTMOS | ML MOS 预测器 | 学习得到的模型；与人类 MOS 相关性约 0.9。 |
| SECS | 克隆相似度 | 参考与克隆之间的 ECAPA 余弦。 |
| EER | 说话人验证分数 | FAR = FRR 的那个阈值点。 |
| DER | 说话人分离分数 | (FA + Miss + Confusion) / total。 |
| FAD | 音乐生成质量 | VGGish 嵌入上的 Fréchet 距离。 |
| RTFx | 吞吐 | 每墙钟秒处理的音频秒数。 |

---

## Further Reading · 延伸阅读

- [jiwer](https://github.com/jitsi/jiwer) —— 带归一化工具的 WER/CER 库。
- [UTMOS (Saeki et al. 2022)](https://arxiv.org/abs/2204.02152) —— 学习型 MOS 预测器。
- [Fréchet Audio Distance (Kilgour et al. 2019)](https://arxiv.org/abs/1812.08466) —— 音乐生成的标准。
- [Open ASR Leaderboard](https://huggingface.co/spaces/hf-audio/open_asr_leaderboard) —— 2026 年实时排名。
- [TTS Arena](https://huggingface.co/spaces/TTS-AGI/TTS-Arena) —— 人类投票的 TTS 榜单。
- [MMAU-Pro benchmark](https://sonalkum.github.io/mmau-pro/) —— LALM 推理榜单。
- [HEAR benchmark](https://hearbenchmark.com/) —— 音频 SSL 基准。
