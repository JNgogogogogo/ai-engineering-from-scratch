# OCR & Document Understanding · OCR 与文档理解

> OCR is a three-stage pipeline — detect text boxes, recognise the characters, then lay them out. Every modern OCR system reorders these stages or merges them.

**Type:** Learn + Use
**Languages:** Python
**Prerequisites:** Phase 4 Lesson 06 (Detection), Phase 7 Lesson 02 (Self-Attention)
**Time:** ~45 minutes

## Learning Objectives · 学习目标

- 梳理经典 OCR 流水线（检测 -> 识别 -> 版面）和现代端到端替代方案（Donut、Qwen-VL-OCR）
- 为序列到序列的 OCR 训练实现 CTC（Connectionist Temporal Classification）损失
- 不训练，直接用 PaddleOCR 或 EasyOCR 做生产级文档解析
- 分清 OCR、版面解析（layout parsing）和文档理解——按任务选对工具

> Trace the classical OCR pipeline (detect -> recognise -> layout) and the modern end-to-end alternatives (Donut, Qwen-VL-OCR)
> Implement CTC (Connectionist Temporal Classification) loss for sequence-to-sequence OCR training
> Use PaddleOCR or EasyOCR for production document parsing without training
> Distinguish OCR, layout parsing, and document understanding — and pick the right tool per task

## The Problem · 问题在哪

写满文字的图片无处不在：收据、发票、证件、扫描书、表单、白板、路牌、截图。从中提取结构化数据——不只是字符，而是「这是总金额」——是应用视觉里价值最高的问题之一。

这个领域分成三层技能：

1. **狭义 OCR**：把像素变成文字。
2. **版面解析**：把 OCR 输出分组为区域（标题、正文、表格、页眉）。
3. **文档理解**：从版面中提取结构化字段（"invoice_total = $42.50"）。

每一层都有经典和现代两种做法，而「我想从图里拿文字」和「我要这张收据上的总金额」之间的差距，比大多数团队以为的要大。

> Images full of text are everywhere: receipts, invoices, IDs, scanned books, forms, whiteboards, signs, screenshots. Extracting structured data from them — not just the characters, but "this is the total amount" — is one of the highest-value applied-vision problems.
> The field splits into three skill layers:
> Each layer has classical and modern approaches, and the gap between "I want text from an image" and "I need the total amount from this receipt" is bigger than most teams realise.

## The Concept · 概念

### The classical pipeline · 经典流水线

```mermaid
flowchart LR
    IMG["Image"] --> DET["Text detection<br/>(DB, EAST, CRAFT)"]
    DET --> BOX["Word/line<br/>bounding boxes"]
    BOX --> CROP["Crop each region"]
    CROP --> REC["Recognition<br/>(CRNN + CTC)"]
    REC --> TXT["Text strings"]
    TXT --> LAY["Layout<br/>ordering"]
    LAY --> OUT["Reading-order text"]

    style DET fill:#dbeafe,stroke:#2563eb
    style REC fill:#fef3c7,stroke:#d97706
    style OUT fill:#dcfce7,stroke:#16a34a
```

- **文本检测**产出逐行或逐词的四边形框。
- **识别**把每个区域裁剪到固定高度，跑一个 CNN + BiLSTM + CTC，产出字符序列。
- **版面**重建阅读顺序（拉丁文从上到下、从左到右；阿拉伯文、日文则不同）。

> - **Text detection** produces per-line or per-word quadrilaterals.
> - **Recognition** crops each region to a fixed height, runs a CNN + BiLSTM + CTC to produce a character sequence.
> - **Layout** rebuilds reading order (top-to-bottom, left-to-right for Latin; different for Arabic, Japanese).

### CTC in one paragraph · 一段话讲完 CTC

OCR 识别要从定长特征图产出变长序列。CTC（Graves 等，2006）让你无需字符级对齐就能训练它。模型在每个时间步输出一个（词表 + blank）上的分布；CTC 损失对所有「合并重复、去掉 blank 之后恰好还原成目标文本」的对齐路径做边缘化求和。

```
raw output: "h h h _ _ e e l l _ l l o _ _"
after merge repeats and remove blanks: "hello"
```

2015 年 CRNN 能成，靠的就是 CTC；2026 年大多数生产 OCR 模型的训练依然靠它。

> OCR recognition produces a variable-length sequence from a fixed-length feature map. CTC (Graves et al., 2006) lets you train this without character-level alignment. The model outputs a distribution over (vocab + blank) at every time step; CTC loss marginalises over all alignments that reduce to the target text after merging repeats and removing blanks.
> CTC is the reason CRNN worked in 2015 and still trains most production OCR models in 2026.

### Modern end-to-end models · 现代端到端模型

- **Donut**（Kim 等，2022）— ViT 编码器 + 文本解码器；读入图片直接输出 JSON。没有文本检测器，也没有版面模块。
- **TrOCR** — 面向行级 OCR 的 ViT + transformer 解码器。
- **Qwen-VL-OCR / InternVL** — 为 OCR 任务微调的完整视觉语言模型；2026 年在复杂文档上精度最佳。
- **PaddleOCR** — 装进成熟生产包的经典 DB + CRNN 流水线；依然是开源界的主力。

端到端模型需要更多数据和算力，但跳过了多级流水线的误差累积。

> - **Donut** (Kim et al., 2022) — a ViT encoder + a text decoder; reads an image and emits JSON directly. No text detector, no layout module.
> - **TrOCR** — ViT + transformer decoder for line-level OCR.
> - **Qwen-VL-OCR / InternVL** — full vision-language models fine-tuned for OCR tasks; best accuracy in 2026 on complex documents.
> End-to-end models need more data and compute but skip the error accumulation of multi-stage pipelines.

### Layout parsing · 版面解析

对结构化文档，跑一个版面检测器（LayoutLMv3、DocLayNet）给每个区域打标签：Title、Paragraph、Figure、Table、Footnote。阅读顺序于是变成「按版面顺序遍历区域、拼接」。

对表单，用**键值抽取（Key-Value extraction）**模型（视觉信息丰富的文档用 Donut，普通扫描件用 LayoutLMv3）。它们吃图片 + 检出的文字 + 位置，预测结构化的键值对。

> For structured documents, run a layout detector (LayoutLMv3, DocLayNet) that labels each region: Title, Paragraph, Figure, Table, Footnote. Reading order then becomes "iterate through regions in layout order, concatenate."
> For forms, use **Key-Value extraction** models (Donut for visually-rich documents, LayoutLMv3 for plain scans). They take image + detected text + positions and predict structured key-value pairs.

### Evaluation metrics · 评估指标

- **字符错误率（CER）** — Levenshtein 距离 / 参考文本长度。越低越好。生产目标：干净扫描件上 < 2%。
- **词错误率（WER）** — 同上，但在词粒度。
- **结构化字段的 F1** — 面向键值任务；衡量 `{invoice_total: 42.50}` 是否被正确抽出。
- **JSON 编辑距离** — 面向端到端文档解析；Donut 论文提出了归一化树编辑距离。

> - **Character Error Rate (CER)** — Levenshtein distance / length of reference. Lower is better. Production target: < 2% on clean scans.
> - **F1 on structured fields** — for key-value tasks; measures whether `{invoice_total: 42.50}` appears correctly.
> - **Edit distance on JSON** — for end-to-end document parsing; the Donut paper introduced normalised tree edit distance.

```figure
cv3-ctc-collapse
```

## Build It · 动手造

### Step 1: CTC loss + greedy decoder · CTC 损失 + 贪心解码器

```python
import torch
import torch.nn as nn
import torch.nn.functional as F


def ctc_loss(log_probs, targets, input_lengths, target_lengths, blank=0):
    """
    log_probs:      (T, N, C) log-softmax over vocab including blank at index 0
    targets:        (N, S) int targets (no blanks)
    input_lengths:  (N,) per-sample time steps used
    target_lengths: (N,) per-sample target length
    """
    return F.ctc_loss(log_probs, targets, input_lengths, target_lengths,
                      blank=blank, reduction="mean", zero_infinity=True)


def greedy_ctc_decode(log_probs, blank=0):
    """
    log_probs: (T, N, C) log-softmax
    returns: list of index sequences (blanks removed, repeats merged)
    """
    preds = log_probs.argmax(dim=-1).transpose(0, 1).cpu().tolist()
    out = []
    for seq in preds:
        decoded = []
        prev = None
        for idx in seq:
            if idx != prev and idx != blank:
                decoded.append(idx)
            prev = idx
        out.append(decoded)
    return out
```

`F.ctc_loss` 在可用时走高效的 CuDNN 实现。贪心解码器比束搜索（beam search）简单，CER 通常只差 1% 以内。

> `F.ctc_loss` uses the efficient CuDNN implementation when available. The greedy decoder is simpler than a beam search and usually within 1% CER of it.

### Step 2: Tiny CRNN recogniser · 迷你 CRNN 识别器

面向行级 OCR 的最小 CNN + BiLSTM。

```python
class TinyCRNN(nn.Module):
    def __init__(self, vocab_size=40, hidden=128, feat=32):
        super().__init__()
        self.cnn = nn.Sequential(
            nn.Conv2d(1, feat, 3, 1, 1), nn.BatchNorm2d(feat), nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(feat, feat * 2, 3, 1, 1), nn.BatchNorm2d(feat * 2), nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(feat * 2, feat * 4, 3, 1, 1), nn.BatchNorm2d(feat * 4), nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 1)),
            nn.Conv2d(feat * 4, feat * 4, 3, 1, 1), nn.BatchNorm2d(feat * 4), nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 1)),
        )
        self.rnn = nn.LSTM(feat * 4, hidden, bidirectional=True, batch_first=True)
        self.head = nn.Linear(hidden * 2, vocab_size)

    def forward(self, x):
        # x: (N, 1, H, W)
        f = self.cnn(x)                # (N, C, H', W')
        f = f.mean(dim=2).transpose(1, 2)  # (N, W', C)
        h, _ = self.rnn(f)
        return F.log_softmax(self.head(h).transpose(0, 1), dim=-1)  # (W', N, vocab)
```

固定高度的输入（CNN 把高度最大池化到 1）。宽度就是 CTC 的时间维。

> Fixed-height input (the CNN max-pools height to 1). Width is the time dimension for CTC.

### Step 3: Synthetic OCR · 合成 OCR 数据

生成白底黑字的数字字符串，做端到端冒烟测试。

```python
import numpy as np

def synthetic_line(text, height=32, char_width=16):
    W = char_width * len(text)
    img = np.ones((height, W), dtype=np.float32)
    for i, c in enumerate(text):
        x = i * char_width
        shade = 0.0 if c.isalnum() else 0.5
        img[6:height - 6, x + 2:x + char_width - 2] = shade
    return img


def build_batch(strings, vocab):
    H = 32
    W = 16 * max(len(s) for s in strings)
    imgs = np.ones((len(strings), 1, H, W), dtype=np.float32)
    target_lengths = []
    targets = []
    for i, s in enumerate(strings):
        imgs[i, 0, :, :16 * len(s)] = synthetic_line(s)
        ids = [vocab.index(c) for c in s]
        targets.extend(ids)
        target_lengths.append(len(ids))
    return torch.from_numpy(imgs), torch.tensor(targets), torch.tensor(target_lengths)


vocab = ["_"] + list("0123456789abcdefghijklmnopqrstuvwxyz")
imgs, targets, lengths = build_batch(["hello", "world"], vocab)
print(f"images: {imgs.shape}   targets: {targets.shape}   lengths: {lengths.tolist()}")
```

真实 OCR 数据集还要加上字体、噪声、旋转、模糊和色彩。上面的流水线一模一样。

> A real OCR dataset adds fonts, noise, rotation, blur, and colour. The pipeline above is identical.

### Step 4: Training sketch · 训练草图

```python
model = TinyCRNN(vocab_size=len(vocab))
opt = torch.optim.Adam(model.parameters(), lr=1e-3)

for step in range(200):
    strings = ["abc" + str(step % 10)] * 4 + ["xyz" + str((step + 1) % 10)] * 4
    imgs, targets, target_lens = build_batch(strings, vocab)
    log_probs = model(imgs)  # (W', 8, vocab)
    input_lens = torch.full((8,), log_probs.size(0), dtype=torch.long)
    loss = ctc_loss(log_probs, targets, input_lens, target_lens, blank=0)
    opt.zero_grad(); loss.backward(); opt.step()
```

在这点简单的合成数据上，200 步内损失应从约 3 降到约 0.2。

> Loss should drop from ~3 to ~0.2 over 200 steps on this trivial synthetic data.

## Use It · 实战用法

三条生产路线：

- **PaddleOCR** — 成熟、快、多语言。一行用法：`paddleocr.PaddleOCR(lang="en").ocr(image_path)`。
- **EasyOCR** — Python 原生、多语言、PyTorch 骨干。
- **Tesseract** — 经典；模型搞不定的老旧扫描文档上依然有用。

端到端文档解析用 Donut 或 VLM：

```python
from transformers import DonutProcessor, VisionEncoderDecoderModel

processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-cord-v2")
model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-cord-v2")
```

收据、发票和结构重复的表单，微调 Donut。任意文档或需要推理的 OCR，Qwen-VL-OCR 这类 VLM 是当前默认。

> - **PaddleOCR** — mature, fast, multilingual. One-line usage: `paddleocr.PaddleOCR(lang="en").ocr(image_path)`.
> - **EasyOCR** — Python-native, multilingual, PyTorch backbone.
> - **Tesseract** — classical; still useful for old scanned documents when models struggle.
> For receipts, invoices, and forms with repeatable structure, fine-tune Donut. For arbitrary documents or OCR with reasoning, a VLM like Qwen-VL-OCR is the current default.

## Ship It · 交付

本课产出：

- `outputs/prompt-ocr-stack-picker.md` — 一个提示词：按文档类型、语言和结构在 Tesseract / PaddleOCR / Donut / VLM-OCR 之间做选择。
- `outputs/skill-ctc-decoder.md` — 一个技能：从零写出贪心和束搜索两种 CTC 解码器，含长度归一化。

> `outputs/prompt-ocr-stack-picker.md` — a prompt that picks Tesseract / PaddleOCR / Donut / VLM-OCR given document type, language, and structure.
> `outputs/skill-ctc-decoder.md` — a skill that writes greedy and beam-search CTC decoders from scratch, including length normalisation.

## Exercises · 练习

1. **（简单）**用 5 位随机数字字符串训练 TinyCRNN 500 步。在留出集上报告 CER。
2. **（中等）**把贪心解码换成束搜索（beam_width=5）。报告 CER 变化。在哪类输入上束搜索占优？
3. **（困难）**用 PaddleOCR 处理 20 张收据，抽取明细行，对手工标注的真值计算 {item_name, price} 键值对的 F1。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|------------|----------|
| OCR | 「从像素到文字」 | 把图像区域变成字符序列 |
| CTC | 「免对齐损失」 | 无需逐时间步标签就能训练序列模型的损失；对所有对齐路径做边缘化 |
| CRNN | 「经典 OCR 模型」 | 卷积特征提取器 + BiLSTM + CTC；2015 年的基线，生产中仍在用 |
| Donut | 「端到端 OCR」 | ViT 编码器 + 文本解码器；直接从图片输出 JSON |
| Layout parsing | 「找区域」 | 检测并标注文档中的 Title/Table/Figure/Paragraph 区域 |
| Reading order | 「文字顺序」 | 把识别出的区域排成句子的顺序；对拉丁文平凡，对混合版面不平凡 |
| CER / WER | 「错误率」 | Levenshtein 距离 / 参考长度，分别在字符或词粒度 |
| VLM-OCR | 「会读的 LLM」 | 为 OCR 任务训练或提示的视觉语言模型；当前复杂文档上的 SOTA |

## Further Reading · 延伸阅读

- [CRNN (Shi et al., 2015)](https://arxiv.org/abs/1507.05717) — CNN+RNN+CTC 的原始架构
- [CTC (Graves et al., 2006)](https://www.cs.toronto.edu/~graves/icml_2006.pdf) — CTC 原始论文；算法思想高度密集
- [Donut (Kim et al., 2022)](https://arxiv.org/abs/2111.15664) — 免 OCR 的文档理解 transformer
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — 开源生产级 OCR 技术栈
