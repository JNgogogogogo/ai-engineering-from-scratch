# Flamingo and Gated Cross-Attention for Few-Shot VLMs · Flamingo 与少样本 VLM 的门控 Cross-Attention

> DeepMind 的 Flamingo（2022）抢在所有人之前做到了两件事。它证明了单个模型可以处理图像、视频、文本任意交错的序列。它还证明了 VLM 能做 in-context 学习——给一个带三个（图像, caption）示例的少样本 prompt，模型不加任何梯度步骤就能给一张新图像写 caption。机制是：门控 cross-attention 层，插在冻结 LLM 已有的层之间，带一个初始为零的 tanh 可学习门，使初始化时 LLM 的文本能力被完整保留。本课走读 Flamingo 的 Perceiver resampler 与门控 cross-attention 架构——Gemini 交错输入与 Idefics2 视觉 token 的祖先。
>
> DeepMind's Flamingo (2022) did two things before anyone else. It showed a single model could process arbitrarily interleaved sequences of images, videos, and text. And it showed VLMs could learn in-context — give a few-shot prompt with three example (image, caption) pairs and the model captions a new image without any gradient step. The mechanism: gated cross-attention layers, inserted between the frozen LLM's existing layers, with a learned tanh gate that starts at zero so the LLM's text capability is preserved at initialization. This lesson walks Flamingo's Perceiver resampler and gated cross-attention architecture — the ancestor of Gemini's interleaved inputs and Idefics2's visual tokens.

**类型:** Learn
**语言:** Python（标准库，gated cross-attention + Perceiver resampler 演示）
**先修:** Phase 12 · 03（BLIP-2 Q-Former）
**时长:** ~120 分钟

## Learning Objectives · 学习目标

- 解释门控 cross-attention 如何通过 tanh(gate) = 0 在初始化时保住冻结 LLM 的文本能力。
- 走通 Perceiver resampler：N 个图像 patch → 通过 cross-attention 变成 K 个固定的「latent」query。
- 描述 Flamingo 如何用尊重图像位置的因果掩码处理交错的图文序列。
- 复现一个少样本多模态 prompt 结构（3 个图文示例 + 1 张查询图像）。

> Explain how gated cross-attention preserves a frozen LLM's text capability at initialization via tanh(gate) = 0.
> Walk through a Perceiver resampler: N image patches → K fixed "latent" queries via cross-attention.
> Describe how Flamingo handles interleaved image-text sequences with causal masking that respects image placement.
> Reproduce a few-shot multimodal prompt structure (3 image-caption examples then a query image).

## The Problem · 问题在哪

BLIP-2 把 32 个视觉 token 喂进冻结 LLM 的输入层。每个 prompt 一张图时没问题。但如果你想喂 *很多* 张与文本交错的图呢——「这是图 A，描述它；这是图 B，描述它；现在这是图 C，描述它」？LLM 的 self-attention 得在单一数据流里同时处理图像 token 和文本 token，而哪些位置能看到哪些图像就成了麻烦事。

Flamingo 的答案：完全不改 LLM 的输入流。在已有的 LLM block 之间插入额外的 cross-attention 层。文本 token 照旧流过 LLM 的因果 self-attention。每隔几个 LLM block，文本 token 再通过一个新的门控层去 cross-attend 图像特征。门（初始化为零）意味着在第 0 步新层是无操作——模型的行为与预训练 LLM 完全一致。随着训练推进，门逐渐打开，视觉信息开始流入。

Flamingo 回答的第二个问题：每个 prompt 的图像数量可变（0、1 或很多张）时怎么办？答案是 Perceiver resampler——一个小 cross-attention 模块，无论你有多少 patch，都产出固定数量的视觉 latent token。LLM 的 cross-attention 层看到的形状与 prompt 里有多少张图无关。

> BLIP-2 feeds 32 visual tokens into a frozen LLM's input layer. Works for one image per prompt. But what if you want to feed *many* images interleaved with text, as in "here is image A, caption it; here is image B, caption it; now here is image C, caption it"? The LLM's self-attention would need to handle image tokens and text tokens in a single stream, and the question of which positions can attend to which images gets fussy.
> Flamingo's answer: do not change the LLM's input stream at all. Insert extra cross-attention layers between existing LLM blocks. ... The gate (initialized to zero) means at step zero the new layers are no-ops — the model behaves exactly like the pretrained LLM. As training progresses the gate opens and visual information starts flowing.
> The second question Flamingo answered: how do you handle a variable number of images (0, 1, or many) per prompt? A Perceiver resampler — a small cross-attention module that takes whatever number of patches you have and produces a fixed number of visual latent tokens. The LLM cross-attention layer sees the same shape regardless of how many images are in the prompt.

## The Concept · 核心概念

### The frozen LLM · 冻结的 LLM

Flamingo 从一个冻结的 Chinchilla 70B LLM 出发。全部 700 亿参数原封不动。已有的文本 self-attention 和 FFN 正常工作。

> Flamingo starts with a frozen Chinchilla 70B LLM. All 70B weights untouched. The existing text self-attention and FFN operate normally.

### Perceiver resampler · Perceiver resampler

对 prompt 里的每张图，ViT 产出 N 个 patch token。Perceiver resampler 有 K 个固定的可学习 latent（Flamingo 用 K=64）。每个 resampler block 分两小步：

1. Cross-attention：K 个 latent 对 N 个 patch token 做注意力（Q 来自 latent，K/V 来自 patch）。
2. latent 之间的 self-attention + FFN。

过完 6 个 resampler block 后，输出是 K=64 个 1024 维视觉 token，与 ViT 产出了多少 patch 无关。一张 224x224 的图（196 个 patch）和一张 480x480 的图（900 个 patch）都以 64 个 resampler token 出来。

对视频，resampler 沿时间维应用：每帧的 patch 产出 64 个 latent，再加一个时间位置编码让模型区分 t=0 和 t=N。整段视频变成 T * 64 个视觉 token。

> For each image in the prompt, the ViT produces N patch tokens. The Perceiver resampler has K fixed learnable latents (Flamingo uses K=64). ... After 6 resampler blocks, the output is K=64 visual tokens of dim 1024, regardless of how many patches the ViT produced. ... For video, the resampler is applied temporally: each frame's patches produce 64 latents, and a temporal positional encoding lets the model distinguish t=0 from t=N. The full video becomes T * 64 visual tokens.

### Gated cross-attention · 门控 cross-attention

在冻结 LLM 的每 M 层之间（Flamingo 用 M=4）插入一个新的门控 cross-attention block：

```
x_after_llm_block = llm_block(x_before)
cross = cross_attn(x_after, resampler_output)
gated = tanh(alpha) * cross + x_after
x_before_next_block = gated
```

- `alpha` 是一个初始化为零的可学习标量。
- `tanh(0) = 0`，所以初始时门控分支的贡献为零。
- 当 `alpha` 偏离零之后，cross-attention 的贡献平滑增长。
- 残差连接意味着即使门全开也不会覆写 LLM 的文本表示；只是在上面叠加视觉信息。

这是 Flamingo 最重要的单一设计选择：视觉条件化是加性的、门控的、初始化为零。第 0 步的 Flamingo 就是一个完美的纯文本 Chinchilla 70B。

> Between every M layers of the frozen LLM (Flamingo uses M=4), insert a new gated cross-attention block: ... - `alpha` is a learnable scalar initialized to zero. - `tanh(0) = 0`, so at init the gated branch contributes zero. ... This is the single most important design choice in Flamingo: visual conditioning is additive, gated, and zero at initialization. A Flamingo at step 0 is a perfect Chinchilla 70B on text-only inputs.

### Masked cross-attention for interleaved inputs · 交错输入的掩码 cross-attention

在「&lt;image A&gt; caption A &lt;image B&gt; caption B &lt;image C&gt; ?」这样的 prompt 里，每个文本 token 只应看到序列里在它之前出现的图像。cross-attention 掩码强制：位置 `t` 的文本 token 只关注图像索引 `i < i_t` 的 resampler token，其中 `i_t` 是位置 `t` 之前最近的那张图。「只看前一张最近的图」和「看所有之前的图」都是合法选择；Flamingo 选了前者。

> In a prompt like "<image A> caption A <image B> caption B <image C> ?", each text token should only see images that came before it in the sequence. The cross-attention mask enforces: text token at position `t` attends only to image resampler tokens whose image index `i < i_t` where `i_t` is the most recent image before position `t`. "Sees only the last preceding image" or "sees all preceding images" are both valid choices; Flamingo chose the former.

### In-context few-shot learning · In-context 少样本学习

Flamingo 的 prompt 长这样：

```
<image1> A photo of a cat. <image2> A photo of a dog. <image3> A photo of a
```

模型看到补全模式，输出「bird」（或 image3 里实际是什么）。没有梯度步骤。冻结 LLM 的 in-context 学习能力穿透门控 cross-attention 传递了下来——这是论文的点睛之笔，也是它重要的原因。

> A Flamingo prompt looks like: ... The model sees the completion pattern and outputs "bird" (or whatever image3 shows). No gradient steps. The frozen LLM's in-context learning capability carries through the gated cross-attention — this is the punchline of the paper and why it matters.

### Training data · 训练数据

Flamingo 在三个数据集上训练：

1. MultiModal MassiveWeb（M3W）：4300 万个图文交错、并重建了阅读顺序的网页。
2. 图文对（ALIGN + LTIP）：44 亿对。
3. 视频-文本对（VTP）：2700 万段短视频。

OBELICS（2023）是交错网页语料的开源复现，Idefics、Idefics2 和多数开源「Flamingo 类」模型都在它上面训练。

> Flamingo trained on three datasets: 1. MultiModal MassiveWeb (M3W): 43M web pages with interleaved images and text, reconstructing reading order. 2. Image-Text Pairs (ALIGN + LTIP): 4.4B pairs. 3. Video-Text Pairs (VTP): 27M short video clips. ... OBELICS (2023) is an open reproduction of the interleaved web corpus, which Idefics, Idefics2, and most open "Flamingo-like" models train on.

### OpenFlamingo and Otter · OpenFlamingo 与 Otter

OpenFlamingo（2023）是开源复现。架构完全一致（Perceiver resampler + 冻结 LLaMA 或 MPT 上的门控 cross-attention）。checkpoint 有 3B、4B、9B。由于基础 LLM 更小、数据更少，质量落后于 Flamingo。

Otter（2023）在 OpenFlamingo 之上，用 MIMIC-IT（一个多模态指令数据集）做指令微调，证明门控 cross-attention 也能做指令跟随。

> OpenFlamingo (2023) is the open reproduction. Architecture identical (Perceiver resampler + gated cross-attention on frozen LLaMA or MPT). Checkpoints at 3B, 4B, 9B. Quality lags Flamingo due to smaller base LLM and less data. ... Otter (2023) builds on OpenFlamingo with instruction tuning on MIMIC-IT (a dataset of multimodal instructions), showing gated cross-attention works for instruction following too.

### The descendants · 后裔

- Idefics / Idefics2 / Idefics3：Hugging Face 的门控 cross-attention 血统，逐代简化（Idefics2 弃用了 resampler，改为直接 patch token 加自适应池化）。
- Flamingo 到 Chameleon 的过渡：到 2024 年，很多团队转向了早期融合（12.11 课）；在必须冻结骨干的场景，Flamingo 式门控 cross-attention 仍在生产中使用。
- Gemini 的交错输入：概念上继承了 Flamingo 交错格式的灵活性，虽然具体机制未公开。

> - Idefics / Idefics2 / Idefics3: Hugging Face's gated cross-attention lineage, progressively simpler (Idefics2 dropped the resampler in favor of direct patch tokens with adaptive pooling). ... - Gemini's interleaved input: conceptually inherits Flamingo's interleaved-format flexibility, though the exact mechanism is proprietary.

### Comparison to BLIP-2 · 与 BLIP-2 对比

| | BLIP-2 | Flamingo |
|---|---|---|
| 视觉桥梁 | 在输入端用一次 Q-Former | 每 M 层插一次门控 cross-attention |
| 视觉 token | 每图 32 个 | 每图每层 cross-attn 64 个 |
| 冻结 LLM | 是 | 是 |
| 少样本 in-context | 弱 | 强——论文的核心卖点 |
| 交错输入 | 无原生支持 | 有，正是设计目标 |
| 训练数据 | 1.3 亿对 | 13 亿对 + 4300 万交错网页 |
| 参数量 | 训练 188M | 训练约 10B（cross-attn 层） |
| 算力 | 8 块 A100 跑几天 | 数千块 TPUv4 跑数周 |

预算内做单图 VQA，选 BLIP-2。交错输入、少样本、多图推理，选 Flamingo/Idefics2。

> Pick BLIP-2 for single-image VQA on a budget. Pick Flamingo/Idefics2 for interleaved, few-shot, or multi-image reasoning.

```figure
cross-attention-fusion
```

## Use It · 实战用法

`code/main.py` 演示：

1. 对 36 个假 patch token、8 个可学习 latent 运行 Perceiver resampler（纯 Python cross-attention）。
2. 一个门控 cross-attention 步骤：`alpha = 0` → 输出等于输入（LLM 不变），然后 `alpha = 2.0` → 视觉贡献混入。
3. 一个交错掩码构造器：为「(image 1) (text 1) (image 2) (text 2)」序列产出 2D 注意力掩码。

> `code/main.py` demonstrates: 1. A Perceiver resampler on 36 fake patch tokens with 8 learnable latents (pure Python cross-attention). 2. A gated cross-attention step with `alpha = 0` → output equals input (LLM unchanged), then `alpha = 2.0` → visual contribution mixed in. 3. An interleaved-mask builder that produces the 2D attention mask for a "(image 1) (text 1) (image 2) (text 2)" sequence.

## Ship It · 交付

本课产出 `outputs/skill-gated-bridge-diagnostic.md`。给定一个开源 VLM 的配置（有无 resampler、cross-attn 频率、门控方案），它识别其中的 Flamingo 血统元素并解释冻结策略。调试「微调为什么把文本能力搞坏了」时很有用（答案：门开得太快太宽）。

> This lesson produces `outputs/skill-gated-bridge-diagnostic.md`. Given an open VLM's config (resampler Y/N, cross-attn frequency, gate scheme), it identifies the Flamingo lineage elements and explains the freezing strategy. Useful for debugging why a fine-tune degraded text performance (answer: the gate got too wide too fast).

## Exercises · 练习

1. 计算 Flamingo-9B 的视觉参数量：9B LLM + 1.4B 门控 cross-attention 层 + 64M resampler。训练的参数占总参数的多大比例？

2. 用 PyTorch 实现门控残差 `y = tanh(alpha) * cross + x`。用实验证明 `alpha=0` 时初始处 `y==x` 精确成立。

3. 读 OpenFlamingo 第 3.2 节（arXiv:2308.01390），了解当 batch 里每个 prompt 的图像数不同时他们如何处理多图。描述其 padding 策略。

4. 为什么 Flamingo 的 cross-attention 掩码让文本 token 只关注 *最近* 一张前序图像，而不是所有前序图像？读 Flamingo 论文第 2.4 节并解释其中的权衡。

5. In-context 少样本：为一个新的 Flamingo 变体构造一个带 4 个「图像 → 主体颜色」示例的 prompt。描述示例数从 0 变到 8 时预期的精度模式。

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| Perceiver resampler | "固定 latent cross-attention" | 从可变数量的输入 patch 产出 K 个固定 token 的模块 |
| Gated cross-attention | "tanh 门控桥" | 残差层 `y = tanh(alpha)*cross + x`，alpha 可学习，初始为 0 |
| Interleaved input | "混合序列" | 图像与文本按阅读顺序自由混合的 prompt 格式 |
| Frozen LLM | "LLM 无梯度" | 文本 LLM 的权重不更新；只有 resampler + cross-attn 层训练 |
| Few-shot | "in-context 示例" | 在 prompt 里给几个（图像, 答案）对；模型不经微调即可泛化 |
| OBELICS | "交错网页语料" | 开源数据集：1.41 亿个按阅读顺序含图和文的网页 |
| Chinchilla | "70B 冻结底座" | Flamingo 的冻结文本 LLM，出自 DeepMind 的 Chinchilla 论文 |
| Gate schedule | "alpha 怎么动" | 训练中 cross-attention 门打开的速率 |
| Cross-attn frequency | "每 M 层一次" | 门控 cross-attention block 的插入频率；Flamingo 用 M=4 |
| OpenFlamingo | "开源复现" | MosaicML/LAION 的 3-9B 开源 checkpoint；架构与 Flamingo 完全一致 |

## Further Reading · 延伸阅读

- [Alayrac et al. — Flamingo (arXiv:2204.14198)](https://arxiv.org/abs/2204.14198) — 原始论文。
- [Awadalla et al. — OpenFlamingo (arXiv:2308.01390)](https://arxiv.org/abs/2308.01390) — 开源复现。
- [Laurençon et al. — OBELICS (arXiv:2306.16527)](https://arxiv.org/abs/2306.16527) — 交错网页语料。
- [Jaegle et al. — Perceiver IO (arXiv:2107.14795)](https://arxiv.org/abs/2107.14795) — 通用 Perceiver 架构。
- [Li et al. — Otter (arXiv:2305.03726)](https://arxiv.org/abs/2305.03726) — 指令微调的 Flamingo 后裔。
- [Laurençon et al. — Idefics2 (arXiv:2405.02246)](https://arxiv.org/abs/2405.02246) — Flamingo 路线的现代简化版。
