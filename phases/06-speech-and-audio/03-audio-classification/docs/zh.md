# Audio Classification — From k-NN on MFCCs to AST and BEATs · 音频分类：从 MFCC 上的 k-NN 到 AST 与 BEATs

> 从「狗叫还是警笛」到「这是哪种语言」，都是音频分类。特征是梅尔。架构每隔几年换一茬。评测始终是 AUC、F1 和逐类召回率。
>
> Everything from "dog barking vs siren" to "which language is this" is audio classification. The features are mels. The architecture moves each decade. The evaluation stays AUC, F1, and per-class recall.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 6 · 02 (Spectrograms & Mel), Phase 3 · 06 (CNNs), Phase 5 · 08 (CNNs & RNNs for Text)
**Time:** ~75 minutes

## The Problem · 问题在哪

你拿到一段 10 秒的音频，想知道：「这是什么？」城市声音（警笛、电钻、狗叫）、语音指令（yes/no/stop）、语言识别（en/es/ar）、说话人情绪（愤怒/中性）或环境声（室内/室外、嘈杂人声）——这些都是*音频分类*，而且 2026 年的基线架构已经成熟：log-mel → CNN 或 Transformer → softmax。

核心难点不在网络，在数据。音频数据集有惨烈的类别不平衡、强烈的域偏移（干净 vs 噪声）和标签噪声（谁来界定「城市嘈杂」和「餐厅噪声」？）。这个问题的 80% 在于数据整理、数据增强和评测，而不是把 CNN 换成 Transformer。

> You get a 10-second clip. You want to know: "what is it?" Urban sound (siren, drill, dog), speech command (yes/no/stop), language ID (en/es/ar), speaker emotion (angry/neutral), or environmental sound (indoor/outdoor, babble). All of these are *audio classification*, and in 2026 the baseline architecture is mature: log-mel → CNN or Transformer → softmax.
> The core difficulty is not the network. It is data. Audio datasets have brutal class imbalance, strong domain shift (clean vs noisy), and label noise (who decided "urban babble" vs "restaurant noise"?). The 80% of the problem is curation, augmentation, and evaluation, not swapping CNN for Transformer.

## The Concept · 概念

![音频分类阶梯：MFCC 上的 k-NN 到 AST 再到 BEATs](../assets/audio-classification.svg)

**MFCC 上的 k-NN（1990 年代的基线）**。把每条音频的 MFCC 展平，与一个带标签的特征库算余弦相似度，返回 top K 的多数投票。在干净的小数据集（Speech Commands、ESC-50）上出奇地强。不用 GPU 就能跑。

**log-mel 上的 2D CNN（2015-2019）**。把 `(T, n_mels)` 的 log-mel 当作图像。套用 ResNet-18 或 VGG 风格。沿时间轴做全局平均池化。对类别做 softmax。至今仍是大多数 2026 年 Kaggle 比赛的基线。

**Audio Spectrogram Transformer（AST，2021-2024）**。把 log-mel 切成 patch（如 16×16），加位置嵌入，喂给 ViT。是有监督学习在 AudioSet（mAP 0.485）上的最先进水平。

**BEATs 与 WavLM-base（2024-2026）**。在数百万小时音频上做自监督预训练，再用只需原来 1-10% 的有监督数据微调到你的任务上。2026 年，这是非语音音频的默认起点。BEATs-iter3 在 AudioSet 上以 1/4 的算力超过 AST 1-2 个 mAP。

**Whisper 编码器当冻结骨干（2024）**。拿 Whisper 的编码器，去掉解码器，接一个线性分类器。不做任何音频增强就能在语言识别和简单事件分类上逼近 SOTA。这是「免费午餐」基线。

### Class imbalance is the real challenge · 类别不平衡才是真正的挑战

ESC-50：50 类，每类 40 条——平衡、容易。UrbanSound8K：10 类，不平衡比例 10:1。AudioSet：632 类，长尾比例 100,000:1。有效的技术：

- 训练时做平衡采样（评测时不做）。
- Mixup：把两条音频（及其标签）线性插值作为增强。
- SpecAugment：遮住随机的时间段和频段。简单，但关键。

### Evaluation · 评测

- 单标签多分类（Speech Commands）：top-1 准确率、top-5 准确率。
- 多标签多分类（AudioSet、UrbanSound 风格）：平均精度均值（mAP）。
- 严重不平衡：逐类召回率 + 宏平均 F1。

你应该知道的 2026 年数字：

| 基准 | 基线 | 2026 SOTA | 来源 |
|-----------|----------|-----------|--------|
| ESC-50 | 82% (AST) | 97.0% (BEATs-iter3) | BEATs paper (2024) |
| AudioSet mAP | 0.485 (AST) | 0.548 (BEATs-iter3) | HEAR leaderboard 2026 |
| Speech Commands v2 | 98% (CNN) | 99.0% (Audio-MAE) | HEAR v2 results |

```figure
mfcc-pipeline
```

> **k-NN on MFCCs (the 1990s baseline).** Flatten MFCCs per clip, compute cosine similarity to a labeled bank, return majority vote of the top K.
> **Audio Spectrogram Transformer, AST (2021-2024).** Patchify the log-mel (e.g. 16×16 patches), add position embeddings, feed to a ViT. State of the art on AudioSet (mAP 0.485) for supervised learning.
> **BEATs and WavLM-base (2024-2026).** Self-supervised pretraining on millions of hours. ... In 2026 this is the default starting point for non-speech audio.
> **Whisper-encoder as a frozen backbone (2024).** Take Whisper's encoder, drop the decoder, attach a linear classifier. ... The "free lunch" baseline.
> ESC-50: 50 classes, 40 clips each — balanced, easy. UrbanSound8K: 10 classes, imbalanced 10:1. AudioSet: 632 classes with a 100,000:1 long tail.

## Build It · 动手造

### Step 1: featurize · 特征化

```python
def featurize_mfcc(signal, sr, n_mfcc=13, n_mels=40, frame_len=400, hop=160):
    mag = stft_magnitude(signal, frame_len, hop)
    fb = mel_filterbank(n_mels, frame_len, sr)
    mels = apply_filterbank(mag, fb)
    log = log_transform(mels)
    return [dct_ii(frame, n_mfcc) for frame in log]
```

### Step 2: fixed-length summary · 定长汇总

```python
def summarize(mfcc_frames):
    n = len(mfcc_frames[0])
    mean = [sum(f[i] for f in mfcc_frames) / len(mfcc_frames) for i in range(n)]
    var = [
        sum((f[i] - mean[i]) ** 2 for f in mfcc_frames) / len(mfcc_frames) for i in range(n)
    ]
    return mean + var
```

简单但强大：沿时间取均值 + 方差，13 系数 MFCC 就得到 26 维定长嵌入。瞬间跑完。直到 2017 年还能在 ESC-50 上打败最先进的神经网络基线。

> Simple but strong: mean + variance across time gives a 26-dim fixed embedding for a 13-coef MFCC. Runs instantly. Beat state-of-the-art NN baselines on ESC-50 as recently as 2017.

### Step 3: k-NN · k 近邻

```python
def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-12
    nb = math.sqrt(sum(x * x for x in b)) or 1e-12
    return dot / (na * nb)

def knn_classify(q, bank, labels, k=5):
    sims = sorted(range(len(bank)), key=lambda i: -cosine(q, bank[i]))[:k]
    votes = Counter(labels[i] for i in sims)
    return votes.most_common(1)[0][0]
```

### Step 4: upgrade to CNN on log-mels · 升级到 log-mel 上的 CNN

在 PyTorch 中：

```python
import torch.nn as nn

class AudioCNN(nn.Module):
    def __init__(self, n_mels=80, n_classes=50):
        super().__init__()
        self.body = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
        )
        self.head = nn.Linear(128, n_classes)

    def forward(self, x):  # x: (B, 1, T, n_mels)
        return self.head(self.body(x).flatten(1))
```

300 万参数。单张 RTX 4090 上在 ESC-50 训练约 10 分钟。准确率 80% 以上。

> 3M parameters. Trains in ~10 min on ESC-50 with a single RTX 4090. 80%+ accuracy.

### Step 5: fine-tune a pretrained audio transformer (AST shown) · 微调预训练音频 Transformer（以 AST 为例）

```python
from transformers import ASTFeatureExtractor, ASTForAudioClassification

ext = ASTFeatureExtractor.from_pretrained("MIT/ast-finetuned-audioset-10-10-0.4593")
model = ASTForAudioClassification.from_pretrained(
    "MIT/ast-finetuned-audioset-10-10-0.4593",
    num_labels=50,
    ignore_mismatched_sizes=True,
)

inputs = ext(audio, sampling_rate=16000, return_tensors="pt")
logits = model(**inputs).logits
```

本例从 Hub 微调 AST。2026 年的默认选择 BEATs 不在 Hugging Face Hub 上：从 [BEATs release in microsoft/unilm](https://github.com/microsoft/unilm/tree/master/beats) 下载 checkpoint，用该仓库的 `BEATs` 和 `BEATsConfig` 类加载；微调循环的形状保持不变。

> The example fine-tunes AST from the Hub. BEATs, the 2026 default, is not on the Hugging Face Hub: download a checkpoint from the [BEATs release in microsoft/unilm](https://github.com/microsoft/unilm/tree/master/beats) and load it with that repo's `BEATs` and `BEATsConfig` classes; the fine-tuning loop keeps the same shape.

## Use It · 实战用法

2026 年的技术栈：

| 场景 | 从哪开始 |
|-----------|-----------|
| 小数据集（<1000 条） | MFCC 均值上的 k-NN（你的基线）+ 音频增强 |
| 中等数据集（1K–100K） | BEATs 或 AST 微调 |
| 大数据集（>100K） | 从头训练或微调 Whisper 编码器 |
| 实时、边缘设备 | 40 维 MFCC 的 CNN，量化到 int8（KWS 风格） |
| 多标签（AudioSet） | BEATs-iter3 + BCE 损失 + mixup + SpecAugment |
| 语言识别 | MMS-LID、SpeechBrain VoxLingua107 基线 |

决策规则：**从冻结骨干开始，而不是从全新模型开始**。只微调 BEATs 的分类头，几个小时（而不是几周）就能拿到 SOTA 的 95%。

> Decision rule: **start with a frozen backbone, not a fresh model**. Fine-tuning a BEATs head gets you 95% of SOTA in hours, not weeks.

## Ship It · 交付

保存为 `outputs/skill-classifier-designer.md`。为给定的音频分类任务挑选架构、增强策略、类别平衡策略和评测指标。

> Save as `outputs/skill-classifier-designer.md`. Pick architecture, augmentations, class-balance strategy, and eval metric for a given audio classification task.

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。它在一个 4 类合成数据集（不同音高的纯音）上训练 k-NN MFCC 基线。报告混淆矩阵。
2. **中等。** 把 `summarize` 换成 [均值, 方差, 偏度, 峰度]。四矩池化在同一合成数据集上能打赢均值+方差吗？
3. **困难。** 用 `torchaudio` 在 ESC-50 第 1 折上训练一个 2D CNN。报告 5 折交叉验证准确率。加上 SpecAugment（时间遮罩 = 20，频率遮罩 = 10），报告增量。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 它实际上是什么意思 |
|------|-----------------|-----------------------|
| AudioSet | 音频界的 ImageNet | Google 的 200 万条、632 类弱标注 YouTube 数据集。 |
| ESC-50 | 小型分类基准 | 50 类 × 40 条环境声。 |
| AST | Audio Spectrogram Transformer | log-mel patch 上的 ViT；2021 年 SOTA。 |
| BEATs | 自监督音频模型 | 微软模型，截至 2026 年 iter3 领跑 AudioSet。 |
| Mixup | 成对增强 | `x = λ·x1 + (1-λ)·x2; y = λ·y1 + (1-λ)·y2`。 |
| SpecAugment | 遮罩式增强 | 把频谱图上随机的时间和频段置零。 |
| mAP | 多标签主指标 | 跨类别、跨阈值的平均精度均值。 |

## Further Reading · 延伸阅读

- [Gong, Chung, Glass (2021). AST: Audio Spectrogram Transformer](https://arxiv.org/abs/2104.01778) —— 2021–2024 年的标杆架构。
- [Chen et al. (2022, rev. 2024). BEATs: Audio Pre-Training with Acoustic Tokenizers](https://arxiv.org/abs/2212.09058) —— 2024 年以后的默认选择。
- [Park et al. (2019). SpecAugment](https://arxiv.org/abs/1904.08779) —— 占统治地位的音频增强方法。
- [Piczak (2015). ESC-50 dataset](https://github.com/karolpiczak/ESC-50) —— 至今仍在使用的 50 类基准。
- [Gemmeke et al. (2017). AudioSet](https://research.google.com/audioset/) —— 632 类的 YouTube 分类体系；依然是黄金标准。
