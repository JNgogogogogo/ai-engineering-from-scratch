# CLIP and Contrastive Vision-Language Pretraining · CLIP 与对比式视觉-语言预训练

> OpenAI 的 CLIP（2021）证明了一个大到足以驱动之后五年的想法：只用嘈杂的网络图文对和一个对比损失，把图像编码器和文本编码器对齐到同一个向量空间。零人工标签，4 亿对数据。得到的嵌入空间能做零样本分类、图文检索，并作为视觉塔插进 2026 年的每一个 VLM。SigLIP 2（2025）把 softmax 换成 sigmoid，以更低成本在规模上超越了 CLIP。本课把数学从 InfoNCE 一路推到 sigmoid 成对损失，并用纯标准库 Python 实现训练步。
>
> OpenAI's CLIP (2021) proved a single idea big enough to power the next five years: align an image encoder and a text encoder in the same vector space using only noisy web image-caption pairs and a contrastive loss. Zero supervised labels. 400M pairs. The resulting embedding space does zero-shot classification, image-text retrieval, and plugs into every 2026 VLM as its vision tower. SigLIP 2 (2025) replaced softmax with sigmoid and scaled past CLIP at lower cost. This lesson walks the math from InfoNCE to sigmoid pairwise loss and builds the training step in stdlib Python.

**类型:** Build
**语言:** Python（标准库，InfoNCE + sigmoid loss 实现）
**先修:** Phase 12 · 01（ViT patches）、Phase 7（Transformers）
**时长:** ~180 分钟

## Learning Objectives · 学习目标

- 从互信息推出 InfoNCE 损失，并实现一个数值稳定、向量化的版本。
- 解释为什么 sigmoid 成对损失（SigLIP）能扩展到 32768+ 的 batch，而不需要 softmax 所要求的 all-gather 开销。
- 通过构造文本模板（`a photo of a {class}`）并在余弦相似度上取 argmax，跑通零样本 ImageNet 分类。
- 说出 CLIP / SigLIP 预训练给你的四个杠杆：batch 大小、温度、prompt 模板、数据质量。

> Derive InfoNCE loss from mutual information and implement a numerically-stable vectorized version.
> Explain why sigmoid pairwise loss (SigLIP) scales to batch 32768+ without the all-gather overhead softmax demands.
> Run zero-shot ImageNet classification by constructing text templates (`a photo of a {class}`) and taking argmax over cosine similarity.
> Name the four levers CLIP / SigLIP pretraining gives you: batch size, temperature, prompt template, data quality.

## The Problem · 问题在哪

CLIP 之前的视觉是监督学习。收集标注数据集（ImageNet：120 万张图、1000 类），训练一个 CNN，交付。标签昂贵，标签偏向标注者们能达成共识的东西，而且不微调就迁移不到新任务。

网络上的图文对免费提供了十亿级以上的松散标注样本。一张金毛的照片配着 alt 文本「my dog Max in the park」，本身就带着监督信号——文本在描述图像。问题是：能不能把它变成有用的训练？

CLIP 的答案：把图文对当成一个匹配任务。给定一个 batch 的 N 张图和 N 条 caption，学习把每张图与它自己的 caption 配对，对抗 N-1 个干扰项。监督信号就是「这两样东西是一对；其余 N-1 个不是」。没有类别标签，没有人工标注，只有一个对比损失。

得到的嵌入空间能做到比训练目标更多的事。ImageNet 零样本之所以有效，是因为「a photo of a cat」的嵌入落在猫的图片附近——尽管这些图片从未被显式标注为猫。正是这个赌注催生了 2026 年的每一个 VLM。

> Pre-CLIP vision was supervised. Collect labeled datasets (ImageNet: 1.2M images, 1000 classes), train a CNN, ship it. Labels are expensive, labels bias to what labelers can agree on, and labels do not transfer to new tasks without finetuning.
> The image-caption web has one billion-plus loosely-labeled pairs for free. A picture of a golden retriever with alt text "my dog Max in the park" carries a supervisory signal — the text describes the image. The question: can you turn this into useful training?
> CLIP's answer: treat image-caption pairs as a matching task. Given a batch of N images and N captions, learn to match each image to its own caption against N-1 distractors. The supervision is "these two things belong together; these N-1 do not." No class labels. No human annotation. Just a contrastive loss.
> The resulting embedding space does more than CLIP was trained for. ... This is the bet that spawned every 2026 VLM.

## The Concept · 核心概念

### The dual encoder · 双塔编码器

CLIP 有两座塔：

- 图像编码器 `f`：ViT 或 ResNet，每张图输出一个 D 维向量。
- 文本编码器 `g`：一个小 transformer，每条 caption 输出一个 D 维向量。

两座塔都把输出归一化到单位长度。相似度即 `cos(f(x), g(y)) = f(x)^T g(y)`，因为两者都是单位范数。

对一个含 N 对（图像, caption）的 batch，构建形状为 `(N, N)` 的相似度矩阵 `S`：

```
S[i, j] = cos(f(x_i), g(y_j)) / tau
```

其中 `tau` 是可学习的温度（CLIP 初始化为 0.07；在对数空间中学习）。

> CLIP has two towers: ... Both towers normalize their outputs to unit length. Similarity is `cos(f(x), g(y)) = f(x)^T g(y)` since both are unit-norm. ... where `tau` is a learned temperature (CLIP initializes to 0.07; learned in log-space).

### InfoNCE loss · InfoNCE 损失

CLIP 对行和列使用对称的交叉熵：

```
loss_i2t = CE(S, labels=identity)     # each image's positive is its own caption
loss_t2i = CE(S^T, labels=identity)   # each caption's positive is its own image
loss = (loss_i2t + loss_t2i) / 2
```

这就是 InfoNCE。CE 里的 softmax 迫使每张图像与自己 caption 的匹配程度超过 batch 里其他所有 caption。「负样本」就是 batch 里的其他所有样本。batch 越大 = 负样本越多 = 信号越强。CLIP 用 32k 的 batch 训练；规模很重要。

> CLIP uses a symmetric cross-entropy over rows and columns: ... This is InfoNCE. The softmax in CE forces each image to match its caption more than every other caption in the batch. The "negatives" are all other batch items. Bigger batches = more negatives = stronger signal. CLIP trained at batch 32k; scale matters.

### Temperature · 温度

`tau` 控制 softmax 的锐度。低 tau → 分布尖锐，产生难负样本挖掘的效果。高 tau → 分布平缓，所有样本都有贡献。CLIP 学习 log(1/tau)，并做裁剪以防坍缩。SigLIP 2 固定初始 tau，改用可学习的偏置。

> `tau` controls the sharpness of the softmax. Low tau → sharp distribution, hard negative mining effect. High tau → soft, all samples contribute. CLIP learns log(1/tau), clipped to prevent collapse. SigLIP 2 fixes the initial tau and uses a learned bias instead.

### Why sigmoid scales better (SigLIP) · 为什么 sigmoid 扩展性更好（SigLIP）

Softmax 需要整张相似度矩阵保持同步。分布式训练时，你必须把所有嵌入 all-gather 到每个副本，然后再做 softmax。通信量随 world size 平方增长。

SigLIP 用逐元素 sigmoid 替换 softmax：对每一对 `(i, j)`，损失是一个二分类——「这是不是匹配的一对？」正类标签在对角线上，其余全是负样本。损失为：

```
L = -1/N sum over (i, j) [ y_ij log sigmoid(S[i,j]) + (1-y_ij) log sigmoid(-S[i,j]) ]
```

`i == j` 时 `y_ij = 1`，否则为 0。每对的损失相互独立，不需要 all-gather。每张 GPU 只计算自己的局部块再求和。SigLIP 2 能以低成本扩展到 32k-512k 的 batch，而 CLIP 在同样的规模下需要成比例增加的通信。

> Softmax needs the whole similarity matrix in sync. In distributed training you must all-gather every embedding to every replica, then do the softmax. This is quadratic in world size for communication. ... `y_ij = 1` if `i == j`, else 0. Each pair's loss is independent. No all-gather needed. Each GPU computes its local block and sums. SigLIP 2 scales to batch 32k-512k cheaply where CLIP would need proportionally more communication.

### Zero-shot classification · 零样本分类

给定 N 个类名，为每个类构造一个文本模板：

```
"a photo of a {class}"
```

用文本编码器嵌入每个模板，用图像编码器嵌入你的图像。余弦相似度取 argmax = 预测类别。不在目标类别上做任何训练。

prompt 模板很重要。CLIP 原论文对每个类用了 80 个模板（plain、artistic、photo、painting 等）并对嵌入取平均，换来 ImageNet 上 +3 个点。现代用法通常只挑一两个模板。

> Given N class names, for each class build a text template: ... Embed each template with the text encoder. Embed your image with the image encoder. Argmax cosine similarity = predicted class. No training on the target classes. ... Prompt templates matter. CLIP's original paper used 80 templates per class (plain, artistic, photo, painting, etc.) and averaged the embeddings. +3 ImageNet points. Modern usage typically picks one or two templates.

### Linear probes and finetuning · 线性探针与微调

零样本只是基线。线性探针（在冻结的 CLIP 特征之上，为你的目标类训练一个线性层）在域内任务上胜过零样本。完整微调在域内胜过线性探针，但可能损害零样本迁移。三种模式，三种权衡。

> Zero-shot is a baseline. A linear probe (train one linear layer on top of frozen CLIP features for your target classes) beats zero-shot on in-domain tasks. Full finetuning beats linear probe on in-domain but can hurt zero-shot transfer. Three regimes with three trade-offs.

### SigLIP 2: NaFlex and dense features · SigLIP 2：NaFlex 与密集特征

SigLIP 2（2025）增加了：

- NaFlex：单个模型处理可变宽高比和分辨率。
- 更好的密集特征，用于分割和深度估计，目标是充当 VLM 中的冻结骨干。
- 多语言：用 100+ 种语言训练，而 CLIP 只有英语。
- 1B 参数规模，而 CLIP 止步于 400M。

在 2026 年的开源 VLM 中，SigLIP 2 SO400m/14 是默认视觉塔。当 LAION-2B 的特定训练分布恰好匹配你的查询模式时，CLIP 仍是纯图文检索的默认选择。

> SigLIP 2 (2025) adds: - NaFlex: single model handles variable aspect ratios and resolutions. ... In 2026 open VLMs, SigLIP 2 SO400m/14 is the default vision tower. CLIP remains the default for pure image-text retrieval where the specific LAION-2B training distribution matches your query pattern.

### ALIGN, BASIC, OpenCLIP, EVA-CLIP · 同门家族

ALIGN（Google，2021）：与 CLIP 同一个想法，18 亿对规模，90% 是噪声。证明了噪声数据可以堆出规模。OpenCLIP（LAION）：CLIP 的开源复现，在 LAION-400M / 2B 上训练，多个规模，是首选的开源 checkpoint。EVA-CLIP：从掩码图像建模初始化；VLM 的强骨干。BASIC：Google 的 CLIP+ALIGN 混合体。它们都是同一家族，差别在数据和调参。

> ALIGN (Google, 2021): same idea as CLIP, 1.8B pair scale, 90% noisy. Proved noisy data scales. OpenCLIP (LAION): open reproduction of CLIP on LAION-400M / 2B, multiple scales, the go-to open checkpoint. EVA-CLIP: initializes from masked image modeling; strong backbone for VLMs. BASIC: Google's CLIP+ALIGN hybrid. All the same family, different data and tuning.

### The zero-shot ceiling · 零样本天花板

CLIP 类模型的 ImageNet 零样本上限在 76% 左右（CLIP-G、OpenCLIP-G）。要突破，要么数据大得多（SigLIP 2 达到 80%+），要么改架构（有监督头、更多参数）。这个基准正在饱和；真正的价值在于下游 VLM 消费的嵌入空间。

> CLIP-class models cap around 76% ImageNet zero-shot (CLIP-G, OpenCLIP-G). Beyond requires either much larger data (SigLIP 2 gets 80%+) or architecture changes (supervised heads, more parameters). The benchmark is saturating; the real value is the embedding space that downstream VLMs consume.

```figure
multimodal-fusion
```

## Use It · 实战用法

`code/main.py` 实现了：

1. 一个玩具双塔编码器（基于哈希的图像特征 + 文本字符特征），让你在没有 numpy 的情况下看到 InfoNCE 的形状。
2. 纯 Python 的 InfoNCE 损失（用 log-sum-exp 保证数值稳定）。
3. 用于对比的 sigmoid 成对损失。
4. 一个零样本分类例程：对一组文本 prompt 计算余弦相似度，argmax 得到预测。

跑一跑，盯着损失曲线。绝对数值是玩具级的；但形状与真实 CLIP 训练器输出的一致。

> `code/main.py` implements: 1. A toy dual encoder (hash-based image features, text char features) so you can see the InfoNCE shape without numpy. ... Run it and watch the loss curve. The absolute numbers are toy; the shape matches what a real CLIP trainer emits.

## Ship It · 交付

本课产出 `outputs/skill-clip-zero-shot.md`。给定一组图像（路径）和目标类别列表，它按 CLIP 模板构造文本 prompt，用指定的 checkpoint（例如 `openai/clip-vit-large-patch14`）嵌入两侧，返回带相似度分数的 top-1 / top-5 预测。该 skill 拒绝对不在 prompt 列表里的类别做任何断言。

> This lesson produces `outputs/skill-clip-zero-shot.md`. Given a set of images (via path) and a list of target classes, it builds text prompts with the CLIP template, embeds both sides with a stated checkpoint (e.g., `openai/clip-vit-large-patch14`), and returns top-1 / top-5 predictions with similarity scores. The skill refuses to make claims about classes not in the prompt list.

## Exercises · 练习

1. 手工为一个 4 对样本的 batch 实现 InfoNCE。构造 4x4 相似度矩阵，做 softmax，取对角线，计算交叉熵。用这个手算结果验证你的 Python 实现。

2. SigLIP 在温度之外还用了偏置参数 `b`：`S'[i,j] = S[i,j]/tau + b`。当一个 batch 存在严重的类别不均衡（每行的负样本远多于正样本）时，`b` 起什么作用？读 SigLIP 第 3 节（arXiv:2303.15343）。

3. 做一个猫 vs 狗的零样本分类器。试两个 prompt 模板：`a photo of a {class}` 和 `a picture of a {class}`。在 100 张测试图上测精度。模板集成会胜过单个模板吗？

4. 计算一个 512 GPU、batch 32k 的任务中 softmax InfoNCE 与 sigmoid 成对损失的通信开销。哪个按 O(N) 扩展，哪个按 O(N^2)？引 SigLIP 第 4 节。

5. 读 OpenCLIP 缩放定律论文（arXiv:2212.07143，Cherti 等）。从图中复现他们关于数据扩展的结论：固定模型规模时，ImageNet 零样本精度与训练数据量之间的对数线性关系是什么？

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| InfoNCE | "对比损失" | 对一个 batch 的相似度矩阵做交叉熵；每个样本的正样本是它配对的样本，负样本是其余全部 |
| Sigmoid loss | "SigLIP 损失" | 逐对二分类交叉熵；没有 softmax、无需 all-gather，分布式训练下扩展成本低 |
| Temperature | "tau" | 在 softmax/sigmoid 之前缩放 logits 的标量；控制分布的锐度 |
| Zero-shot | "免微调分类" | 用文本 prompt 构造类别嵌入，按余弦相似度分类；不在目标类上训练 |
| Prompt template | "a photo of a ..." | 包在类名外的文本脚手架；对零样本精度影响 1-5 个点 |
| Dual encoder | "双塔" | 一个图像编码器 + 一个文本编码器，输出落在共享的 D 维空间 |
| Hard negative | "难缠的干扰项" | 与正样本足够相似的负样本，模型必须下功夫才能把它们分开 |
| Linear probe | "冻结 + 一层" | 在冻结特征之上只训练一个线性分类器；用来衡量特征质量 |
| NaFlex | "原生弹性分辨率" | SigLIP 2 的能力：不缩放即可摄入任意宽高比和分辨率的图像 |
| Temperature scaling | "对数参数化的 tau" | CLIP 参数化 `log(1/tau)` 让梯度表现良好；并做裁剪防止 tau 坍缩到接近零 |

## Further Reading · 延伸阅读

- [Radford et al. — Learning Transferable Visual Models From Natural Language Supervision (arXiv:2103.00020)](https://arxiv.org/abs/2103.00020) — CLIP 论文。
- [Zhai et al. — Sigmoid Loss for Language Image Pre-Training (arXiv:2303.15343)](https://arxiv.org/abs/2303.15343) — SigLIP。
- [Tschannen et al. — SigLIP 2 (arXiv:2502.14786)](https://arxiv.org/abs/2502.14786) — 多语言 + NaFlex。
- [Jia et al. — ALIGN (arXiv:2102.05918)](https://arxiv.org/abs/2102.05918) — 用嘈杂的网络数据堆规模。
- [Cherti et al. — Reproducible scaling laws for contrastive language-image learning (arXiv:2212.07143)](https://arxiv.org/abs/2212.07143) — OpenCLIP 缩放定律。
