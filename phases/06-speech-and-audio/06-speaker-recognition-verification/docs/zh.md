# Speaker Recognition & Verification · 说话人识别与验证

> ASR 问的是「说了什么？」，说话人识别问的是「谁在说话？」数学看起来一样——嵌入加余弦——但每一个生产决策都系于一个 EER 数字。
>
> ASR asks "what did they say?" Speaker recognition asks "who said it?" The math looks the same — embeddings plus cosine — but every production decision hinges on a single EER number.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 6 · 02 (Spectrograms & Mel), Phase 5 · 22 (Embedding Models)
**Time:** ~45 minutes

## The Problem · 问题在哪

用户说了一句口令。你想知道：这个人是不是他声称的那位（*验证*，verification，1:1），还是注册库里匹配上的第一位（*辨认*，identification，1:N）？或者都不是——这是一个未知说话人（*开集*，open-set）？

2018 年之前：GMM-UBM + i-vectors。EER 尚可，但对信道偏移（手机 vs 笔记本）和情绪很脆弱。2018–2022：x-vectors（带角度间隔训练的 TDNN 骨干）。2022 年之后：ECAPA-TDNN 和 WavLM-large 嵌入。到 2026 年，这个领域由三个模型和一个指标主导。

这个指标就是 **EER**——等错误率（Equal Error Rate）。把决策阈值调到错误接受率 = 错误拒绝率，交叉点就是 EER。每篇论文、每个榜单、每次采购评估都在用它。

> A user says a passphrase. You want to know: is this the person they claim to be (*verification*, 1:1), or is it the first person in your enrollment bank (*identification*, 1:N)? Or neither — is this an unknown speaker (*open-set*)?
> Pre-2018: GMM-UBM + i-vectors. Reasonable EER but fragile to channel shift (phone vs laptop) and emotion. 2018–2022: x-vectors (TDNN backbone trained with angular margin). 2022+: ECAPA-TDNN and WavLM-large embeddings. By 2026 the field is dominated by three models and one metric.
> The metric is **EER** — Equal Error Rate. Set your decision threshold so False Accept Rate = False Reject Rate. The crossover is EER. Used in every paper, every leaderboard, every procurement call.

## The Concept · 概念

![带嵌入、余弦与 EER 的注册加验证流水线](../assets/speaker-verification.svg)

**流水线**。注册（enrollment）：录下目标说话人 5–30 秒，计算一个固定维度的嵌入（ECAPA-TDNN 是 192 维，WavLM-large 是 256 维）。验证（verification）：取测试语句的嵌入，计算余弦相似度，与阈值比较。

**ECAPA-TDNN（2020 年发布，2026 年仍占主导）**。全称 Emphasized Channel Attention, Propagation and Aggregation - Time-Delay Neural Network。带 squeeze-excitation 的一维卷积块、多头注意力池化，最后接一个线性层到 192 维。在 VoxCeleb 1+2（2,700 个说话人、110 万条语句）上用加性角度间隔损失（AAM-softmax）训练。

**WavLM-SV（2022 年之后）**。用 AAM 损失微调预训练的 WavLM-large SSL 骨干。质量更高但更慢——300+ MB 对 15 MB。

**x-vector（基线）**。TDNN + 统计池化。经典方案；在 CPU / 边缘设备上依然有用。

**AAM-softmax**。在角度空间加间隔 `m` 的标准 softmax：对正确类为 `cos(θ + m)`。迫使类间角度分开。典型值 `m=0.2`，尺度 `s=30`。

> **The pipeline.** Enrollment: record 5–30 seconds of the target speaker; compute a fixed-dimension embedding (192-d for ECAPA-TDNN, 256-d for WavLM-large). Verification: get the test utterance embedding; compute cosine similarity; compare to a threshold.
> **ECAPA-TDNN (2020, still dominant 2026).** ... Trained on VoxCeleb 1+2 (2,700 speakers, 1.1M utterances) with Additive Angular Margin loss (AAM-softmax).
> **WavLM-SV (2022+).** Fine-tune a pretrained WavLM-large SSL backbone with AAM loss. Higher quality but slower — 300+ MB vs 15 MB.
> **AAM-softmax.** Standard softmax with added margin `m` in the angular space: `cos(θ + m)` for the correct class. Forces inter-class angular separation. Typical `m=0.2`, scale `s=30`.

### Scoring · 打分

- **余弦（Cosine）**：注册嵌入与测试嵌入之间算余弦，按阈值决策。
- **PLDA（Probabilistic LDA，概率线性判别分析）**。把嵌入投影到一个潜在空间，使同说话人 vs 不同说话人具有闭式似然比。叠加在余弦之上可再降 10–20% EER。2020 年之前是标准做法；现在只在闭集场景使用。
- **分数归一化（Score normalization）**。`S-norm` 或 `AS-norm`：用一组冒名者（imposter）分数的均值和标准差对每个分数归一化。跨领域评测的必备品。

> **Cosine** between enrollment and test embeddings. Threshold-based decision.
> **PLDA (Probabilistic LDA).** Project embeddings into a latent space where same-speaker vs different-speaker has a closed-form likelihood ratio. Added on top of cosine for +10–20% EER reduction. Standard pre-2020; now used only in closed-set setups.
> **Score normalization.** `S-norm` or `AS-norm`: normalize each score against a cohort of imposter means and stds. Essential for cross-domain eval.

### Numbers you should know (2026) · 你应该知道的数字（2026）

| 模型 | VoxCeleb1-O EER | 参数量 | 吞吐 (A100) |
|-------|-----------------|--------|-------------------|
| x-vector (classic) | 3.10% | 5 M | 400× 实时 |
| ECAPA-TDNN | 0.87% | 15 M | 200× 实时 |
| WavLM-SV large | 0.42% | 316 M | 20× 实时 |
| Pyannote 3.1 segmentation + embedding | 0.65% | 6 M | 100× 实时 |
| ReDimNet (2024) | 0.39% | 24 M | 100× 实时 |

### Diarization · 说话人分离

回答多说话人音频里「谁在什么时候说话」。流水线：VAD → 切段 → 每段算嵌入 → 聚类（凝聚层次或谱聚类）→ 平滑边界。现代技术栈：`pyannote.audio` 3.1，一次调用打包了说话人分割 + 嵌入 + 聚类。2026 年 AMI 上的 SOTA DER 约 15%（2022 年是 23%）。

> "Who spoke when" in a multi-speaker clip. Pipeline: VAD → segment → embed each segment → cluster (agglomerative or spectral) → smooth boundaries. Modern stack: `pyannote.audio` 3.1, which bundles speaker segmentation + embedding + clustering behind one call. 2026 SOTA DER on AMI is ~15% (down from 23% in 2022).

```figure
sp-eer-crossover
```

## Build It · 动手造

### Step 1: toy embedding from MFCC statistics · 用 MFCC 统计量做玩具嵌入

```python
def embed_mfcc_stats(signal, sr):
    frames = featurize_mfcc(signal, sr, n_mfcc=13)
    mean = [sum(f[i] for f in frames) / len(frames) for i in range(13)]
    std = [
        math.sqrt(sum((f[i] - mean[i]) ** 2 for f in frames) / len(frames))
        for i in range(13)
    ]
    return mean + std  # 26-d
```

离 SOTA 差得远——仅用于教学。`code/main.py` 在合成说话人数据上把它当概念验证。

> Not SOTA by a mile — for teaching only. `code/main.py` uses this as a proof-of-concept on synthetic speaker data.

### Step 2: cosine similarity + threshold · 余弦相似度加阈值

```python
def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0

def verify(enroll, test, threshold=0.75):
    return cosine(enroll, test) >= threshold
```

### Step 3: EER from similarity pairs · 从相似度对算 EER

```python
def eer(same_scores, diff_scores):
    thresholds = sorted(set(same_scores + diff_scores))
    best = (1.0, 1.0, 0.0)  # (fa, fr, threshold)
    for t in thresholds:
        fr = sum(1 for s in same_scores if s < t) / len(same_scores)
        fa = sum(1 for s in diff_scores if s >= t) / len(diff_scores)
        if abs(fa - fr) < abs(best[0] - best[1]):
            best = (fa, fr, t)
    return (best[0] + best[1]) / 2, best[2]
```

返回 (eer, threshold_at_eer)。两者都要上报。

> Returns (eer, threshold_at_eer). Report both.

### Step 4: production with SpeechBrain · 用 SpeechBrain 走生产路线

```python
from speechbrain.pretrained import EncoderClassifier

clf = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb")

# enroll: average the embeddings of 3-5 clean samples
enroll = torch.stack([clf.encode_batch(load(x)) for x in enrollment_clips]).mean(0)
# verify
score = clf.similarity(enroll, clf.encode_batch(load("test.wav"))).item()
verdict = score > 0.25   # ECAPA typical threshold; tune on your data
```

### Step 5: diarize with pyannote · 用 pyannote 做说话人分离

```python
from pyannote.audio import Pipeline

pipe = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")
diarization = pipe("meeting.wav", num_speakers=None)
for turn, _, speaker in diarization.itertracks(yield_label=True):
    print(f"{turn.start:.1f}–{turn.end:.1f}  {speaker}")
```

## Use It · 实战用法

2026 年的技术栈：

| 场景 | 选择 |
|-----------|------|
| 闭集 1:1 验证、边缘设备 | ECAPA-TDNN + 余弦阈值 |
| 开集验证、云端 | WavLM-SV + AS-norm |
| 说话人分离（会议、播客） | `pyannote/speaker-diarization-3.1` |
| 反欺骗（重放 / 深度伪造检测） | AASIST 或 RawNet2 |
| 微型嵌入式（关键词检出 + 注册） | Titanet-Small (NeMo) |

> Closed-set 1:1 verification, edge → ECAPA-TDNN + cosine threshold. Open-set verification, cloud → WavLM-SV + AS-norm. Diarization (meetings, podcasts) → `pyannote/speaker-diarization-3.1`. Anti-spoofing (replay / deepfake detection) → AASIST or RawNet2. Tiny embedded (KWS + enrollment) → Titanet-Small (NeMo).

## Pitfalls · 常见的坑

- **信道不匹配。** 在 VoxCeleb（网络视频）上训练的模型 ≠ 电话音频。务必在目标信道上评估。
- **语句太短。** 测试音频低于 3 秒时 EER 急剧恶化。
- **带噪声的注册。** 一条噪声注册会毒化锚点。用至少 3 条干净样本取平均。
- **跨场景用固定阈值。** 务必在目标领域的留出开发集上调阈值。
- **对未归一化的嵌入算余弦。** 先做 L2 归一化；否则模长会主导结果。

> **Channel mismatch.** Model trained on VoxCeleb (web video) ≠ phone-call audio. Always evaluate on target channel.
> **Short utterances.** EER degrades sharply below 3 seconds of test audio.
> **Enrollment with noise.** One noisy enrollment poisons the anchor. Use ≥3 clean samples and average.
> **Fixed threshold across conditions.** Always tune the threshold on a held-out dev set from the target domain.
> **Cosine on non-normalized embeddings.** L2-normalize first; otherwise the magnitude dominates.

## Ship It · 交付

保存为 `outputs/skill-speaker-verifier.md`。为给定场景挑选模型、注册协议、阈值调优计划和反欺诈保障。

> Save as `outputs/skill-speaker-verifier.md`. Pick model, enrollment protocol, threshold-tuning plan, and fraud safeguards.

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。它构建合成的「说话人」（不同音色轮廓），注册，并在一个 100 对的试验列表上计算 EER。
2. **中等。** 在 30 条 VoxCeleb1 语句（5 个说话人 × 每人 6 条）上用 SpeechBrain ECAPA。比较余弦与 PLDA 的 EER。
3. **困难。** 用 `pyannote.audio` 搭完整的注册 → 分离 → 验证流水线。在 AMI 开发集上评估 DER。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 它实际上是什么意思 |
|------|-----------------|-----------------------|
| EER | 头条指标 | 错误接受 = 错误拒绝的那个阈值。 |
| 验证（Verification） | 1:1 | 「这是 Alice 吗？」 |
| 辨认（Identification） | 1:N | 「谁在说话？」 |
| 开集（Open-set） | 未知说话人可能存在 | 测试集可以包含未注册的说话人。 |
| 注册（Enrollment） | 登记备案 | 计算某说话人的参考嵌入。 |
| AAM-softmax | 那个损失 | 带加性角度间隔的 softmax；迫使簇分开。 |
| PLDA | 经典打分 | 概率 LDA；在嵌入之上做似然比打分。 |
| DER | 分离指标 | 说话人错误率——漏检 + 虚警 + 混淆。 |

## Further Reading · 延伸阅读

- [Snyder et al. (2018). X-Vectors: Robust DNN Embeddings for Speaker Recognition](https://www.danielpovey.com/files/2018_icassp_xvectors.pdf) —— 经典深度嵌入论文。
- [Desplanques et al. (2020). ECAPA-TDNN](https://arxiv.org/abs/2005.07143) —— 2020–2026 年的主导架构。
- [Chen et al. (2022). WavLM: Large-Scale Self-Supervised Pre-Training for Full Stack Speech Processing](https://arxiv.org/abs/2110.13900) —— 面向 SV 和说话人分离的 SSL 骨干。
- [Bredin et al. (2023). pyannote.audio 3.1](https://github.com/pyannote/pyannote-audio) —— 生产级分离 + 嵌入技术栈。
- [VoxCeleb leaderboard (updated 2026)](https://www.robots.ox.ac.uk/~vgg/data/voxceleb/) —— 各模型当前 EER 排名。
