# From CLIP to BLIP-2 — Q-Former as Modality Bridge · 从 CLIP 到 BLIP-2——Q-Former 作为模态桥梁

> CLIP 能对齐图像和文本，却不能生成描述、回答问题或对话。BLIP-2（Salesforce，2023）用一个小的可训练桥梁解决了这件事：32 个可学习的 query 向量通过 cross-attention 关注冻结 ViT 的特征，然后直接插进冻结 LLM 的输入流。1.88 亿参数的桥梁把一个 11B 的 LLM 连到了 ViT-g/14 上。到 2026 年为止，每一个基于 adapter 的 VLM——MiniGPT-4、InstructBLIP、LLaVA 的同门——都是它的后裔。本课解读 Q-Former 的架构，讲清它的两阶段训练，并造一个把视觉 token 喂给冻结文本解码器的玩具版本。
>
> CLIP aligns image and text but cannot generate captions, answer questions, or hold a conversation. BLIP-2 (Salesforce, 2023) solved that with a small trainable bridge: 32 learnable query vectors attend over a frozen ViT's features via cross-attention, then slot directly into a frozen LLM's input stream. 188M parameters of bridge connected an 11B LLM to a ViT-g/14. Every adapter-based VLM through 2026 — MiniGPT-4, InstructBLIP, LLaVA's cousins — is a descendant. This lesson reads the Q-Former's architecture, explains its two-stage training, and builds a toy version that feeds visual tokens into a frozen text decoder.

**类型:** Build
**语言:** Python（标准库，cross-attention + 可学习 query 演示）
**先修:** Phase 12 · 02（CLIP）、Phase 7（Transformers）
**时长:** ~180 分钟

## Learning Objectives · 学习目标

- 解释为什么在冻结视觉编码器和冻结 LLM 之间放一个可训练瓶颈，在成本和稳定性上都胜过端到端微调。
- 实现一个 cross-attention block：一组固定的可学习 query 关注外部图像特征。
- 走通 BLIP-2 的两阶段预训练：先表示学习（ITC + ITM + ITG），再生成学习（用冻结解码器算 LM 损失）。
- 比较 Q-Former 与 LLaVA 使用的更简单的 MLP projector，并论证各自何时占优。

> Explain why a trainable bottleneck between a frozen vision encoder and frozen LLM beats end-to-end finetuning in cost and stability.
> Implement a cross-attention block where a fixed set of learnable queries attend to external image features.
> Walk through BLIP-2's two-stage pretraining: representation (ITC + ITM + ITG) then generative (LM loss with frozen decoder).
> Compare Q-Former to the simpler MLP projector used in LLaVA and argue when each choice wins.

## The Problem · 问题在哪

你有一个冻结的 ViT，每张图产出 256 个 1408 维的 patch token。你有一个冻结的 7B LLM，它期望 4096 维的 token 嵌入。最直接的桥梁——一个从 1408 到 4096 的线性层——能用，但把全部 256 个 patch token 塞进 LLM 上下文，每张图要花掉 256 个额外 token。一个 32 张图的 batch，仅视觉模态就要消耗 8192 个 token。

BLIP-2 的问题是：能不能把 256 个 token 的图像表示压缩到少得多的 token（比如 32 个），同时保留足够的信息，让 LLM 能描述图像、回答问题和做推理？以及，能不能不碰冻结的骨干就训练这座桥，把训练成本压到只剩桥自己的参数？

答案是：Q-Former。32 个可学习的「query」向量对 ViT 的 patch token 做 cross-attention，产出一个 32 token 的视觉摘要供 LLM 消费。总共 1.88 亿参数。在碰 LLM 之前，先用对比、匹配和生成目标训练它。

> You have a frozen ViT that produces 256 patch tokens of dim 1408 per image. You have a frozen 7B LLM that expects token embeddings of dim 4096. The obvious bridge — a linear layer from 1408 to 4096 — works, but feeding all 256 patch tokens into the LLM's context costs 256 extra tokens per image. Over a batch of 32 images that is 8192 tokens consumed by the visual modality alone.
> The BLIP-2 question: can you compress the 256-token image representation into far fewer tokens (say 32) while preserving enough information for the LLM to caption, answer questions, and reason about the image? And can you train this bridge without touching the frozen backbones, keeping the training cost at just the bridge's parameters?
> The answer: a Q-Former. 32 learnable "query" vectors that cross-attend to the ViT's patch tokens, producing a 32-token visual summary that the LLM consumes. 188M parameters total. Trained with contrastive, matching, and generative objectives before ever touching the LLM.

## The Concept · 核心概念

### Learnable queries · 可学习的 query

Q-Former 的核心技巧：不让 LLM 的文本 token 去关注图像 patch，而是引入一组新的 32 个可学习 query 向量 `Q`，让 *它们* 去关注图像 patch。这些 query 是模型的参数——训练中学出来，而且每张图用的都是同一组 32 个 query。

cross-attention 之后，每个 query 持有图像的一份压缩摘要——「描述主体」「描述背景」「数一数物体」等等。这些 query 并不会真的按语义标签分工；它们学到的是任何能让下游损失下降的编码。

> The Q-Former's core trick: instead of letting the LLM's text tokens attend to image patches, introduce a new set of 32 learnable query vectors `Q` and let *them* attend to image patches. The queries are parameters of the model — they are learned during training and the same 32 queries are used for every image.
> After cross-attention, each query holds a compressed summary of the image — "describe the main object", "describe the background", "count the objects", etc. The queries do not literally specialize on semantic labels; they learn whatever encoding makes downstream losses drop.

### Architecture · 架构

Q-Former 是一个小 transformer（12 层，约 1 亿参数），有两条路径：

1. Query 路径：32 个 query 向量先过 self-attention（在彼此之间），再对冻结 ViT 的 patch token 做 cross-attention，然后过 FFN。
2. 文本路径：一个类 BERT 的文本编码器，与 query 路径共享 self-attention 和 FFN 权重。文本路径关闭 cross-attention。

训练时两条路径都运行。query 和文本通过共享的 self-attention 交互，这意味着在需要的任务上（ITM、ITG），query 能以文本为条件。推理时为了交接给 VLM，只有 query 流过，产出 32 个视觉 token。

> The Q-Former is a small transformer (12 layers, ~100M params) with two paths: ... At training time both paths run. The queries and text interact through shared self-attention, which means the queries can condition on text for tasks that need it (ITM, ITG). At inference time for VLM handoff, only the queries flow through, yielding 32 visual tokens.

### Two-stage training · 两阶段训练

BLIP-2 分两个阶段做预训练：

阶段 1：表示学习（不涉及 LLM）。三个损失：

- ITC（image-text contrastive，图文对比）：在池化的 query token 与文本 CLS token 之间做 CLIP 式对比。
- ITM（image-text matching，图文匹配）：一个二分类器——这对图文匹配吗？用难负样本挖掘。
- ITG（image-grounded text generation，图像接地的文本生成）：文本上的因果 LM 头，以 query 为条件。迫使 query 编码可被文本生成的内容。

只有 Q-Former 在训练。ViT 冻结。没有 LLM 参与。

阶段 2：生成学习。接上一个冻结 LLM（OPT-2.7B 或 Flan-T5-XL 等）。用一个小的线性层把 32 个 query 输出投影到 LLM 的嵌入维度，并拼在文本 prompt 前面。在拼接后的 prompt + 图像 + caption 序列上，只训练线性投影和 Q-Former 的 LM 损失。

阶段 2 之后，Q-Former + 投影就是完整的视觉 adapter。推理流程：图像 → ViT → Q-Former → 线性投影 → 拼到文本前面 → 冻结 LLM 产出输出。

> BLIP-2 pretrains in two stages:
> Stage 1: representation learning (no LLM). Three losses: ... Only the Q-Former trains. The ViT is frozen. No LLM involved.
> Stage 2: generative learning. Attach a frozen LLM (OPT-2.7B or Flan-T5-XL, etc.). Project the 32 query outputs to the LLM's embedding dim via a small linear layer. ... After stage 2, the Q-Former + projection is the full visual adapter. At inference: image → ViT → Q-Former → linear proj → prepended to text → frozen LLM emits output.

### Parameter economics · 参数经济学

BLIP-2 = ViT-g/14（1.1B，冻结）+ OPT-6.7B（6.7B，冻结）+ Q-Former（188M，训练）= 总计 8B，其中训练 188M。Q-Former 只占整个栈参数的约 2.4%。训练成本也体现了这一点：几块 A100 上跑几天，对比端到端训练的数周。

质量方面：BLIP-2 在零样本 VQA 上追平或超过 Flamingo-80B，同时小 50 倍。这座桥管用。

> BLIP-2 with ViT-g/14 (1.1B, frozen) + OPT-6.7B (6.7B, frozen) + Q-Former (188M, trained) = 8B total, 188M trained. The Q-Former alone is ~2.4% of the full stack's parameters. Training cost reflects this: days on a handful of A100s vs weeks for end-to-end.
> Quality: BLIP-2 matches or beats Flamingo-80B on zero-shot VQA while being 50x smaller. The bridge works.

### InstructBLIP and the instruction-aware Q-Former · InstructBLIP 与指令感知的 Q-Former

InstructBLIP（2023）给 Q-Former 加了一个额外输入：指令文本本身。cross-attention 时，query 现在能同时看到图像 patch 和指令。query 可以按指令特化（「数一数有几辆车」「描述一下情绪」），而不是学一个单一的固定摘要。在留出任务上有基准提升。

> InstructBLIP (2023) extends the Q-Former with an extra input: the instruction text itself. At cross-attention time, the queries now have access to both the image patches and the instruction. The queries can specialize per-instruction ("count the cars", "describe the mood") rather than learning a single fixed summary. Benchmark gains on held-out tasks.

### MiniGPT-4 and the projector-only approach · MiniGPT-4 与只训投影层的路线

MiniGPT-4 保留了 Q-Former，但只训练输出线性投影，其余全部冻结。便宜，但代价是质量——query 是 BLIP-2 的，不是你的。适合快速迭代，不是最好的架构。

> MiniGPT-4 kept the Q-Former but trained only the output linear projection while freezing everything else. Cheap, but cost is quality — the queries were BLIP-2's, not yours. Good for rapid iteration, not the best architecture.

### Why LLaVA went simpler · LLaVA 为什么选了更简单的

LLaVA（2023，12.05 课）用一个普通的 2 层 MLP 替换了 Q-Former，把每个 ViT patch token 投影进 LLM 空间——24x24 网格即每图 576 个 token，全部喂给 LLM。压缩更差，但让 LLM 能在原始 patch 上做注意力。当时这有争议；到 2023 年底它成了主流，因为视觉指令数据（LLaVA-Instruct-150k）证明了 MLP 可以被训练到保留足够的信号。代价是：LLaVA 的上下文填得更快，但它能自然扩展到多图和视频。

到 2026 年，领域已经分裂：在 token 预算要紧的地方（长视频、多图），Q-Former 仍然存活；在单 token 质量优先的地方，MLP projector 占统治地位。

> LLaVA (2023, Lesson 12.05) replaced the Q-Former with a plain 2-layer MLP that projects every ViT patch token into LLM space — 576 tokens per image for a 24x24 grid, all fed to the LLM. ... By 2026 the field split: Q-Former survives where token budget matters (long video, many images); MLP projector dominates where raw quality per token is the priority.

### Gated cross-attention: Flamingo, the ancestor · 门控 cross-attention：祖先 Flamingo

Flamingo（12.04 课）早于 BLIP-2，用了同样的 cross-attention 思想，但插在冻结 LLM 的每一层，而不是作为单一桥梁。BLIP-2 证明了只压缩到输入层也能工作。Gemini 和 Idefics 把两者结合：交错的输入 token，外加可选的门控 cross-attention 以支持 in-context few-shot。

> Flamingo (Lesson 12.04) predated BLIP-2 and used the same cross-attention idea but at every frozen LLM layer, not as a single bridge. BLIP-2 showed you can compress to the input layer only and still work. Gemini and Idefics combine both: interleaved input tokens plus optional gated cross-attention for in-context few-shot.

### The 2026 descendants · 2026 年的后裔

- Q-Former：BLIP-2、InstructBLIP、MiniGPT-4，以及出于 token 预算考虑的大多数视频-语言模型。
- Perceiver resampler：Flamingo 的变体（12.04 课）；Idefics 家族、Eagle、OmniMAE。
- MLP projector：LLaVA、LLaVA-NeXT、LLaVA-OneVision、Cambrian-1。
- Attention pool：VILA、PaliGemma。

四种都成立。决定性的问题是：你受限于 token 预算，还是受限于单位 token 质量。

> - Q-Former: BLIP-2, InstructBLIP, MiniGPT-4, and most video-language models for token budget reasons. ... All four are valid. The deciding question is whether you are constrained on token budget or on quality-per-token.

```figure
modality-projection
```

## Use It · 实战用法

`code/main.py` 构建一个标准库版的 Q-Former 式 cross-attention：

1. 模拟 256 个图像 patch token（128 维）。
2. 实例化 32 个可学习 query（128 维）。
3. 运行缩放点积 cross-attention（Q 来自 query，K/V 来自 patch）。
4. 通过一个线性层投影到 LLM 维度（512）。
5. 输出 32 个 LLM 可用的视觉 token。

所有数学都是纯 Python（向量上的嵌套循环）。玩具级，但形状正确。注意力权重矩阵会被打印出来，让你看到每个 query 从哪些 patch 拉取了信息。

> `code/main.py` builds a stdlib Q-Former-style cross-attention: 1. Simulate 256 image patch tokens (dim 128). ... All math in pure Python (nested loops over vectors). Toy but correct shape. The attention-weight matrix is printed so you can see which patches each query pulled from.

## Ship It · 交付

本课产出 `outputs/skill-modality-bridge-picker.md`。给定一个目标 VLM 配置（视觉编码器 token 数、LLM 上下文预算、部署约束、质量目标），它会推荐 Q-Former vs MLP vs Perceiver resampler，附简短理由和每种桥的参数量估算。

> This lesson produces `outputs/skill-modality-bridge-picker.md`. Given a target VLM configuration (vision encoder token count, LLM context budget, deployment constraints, quality target), it recommends Q-Former vs MLP vs Perceiver resampler with a short justification and a parameter-count estimate for each bridge.

## Exercises · 练习

1. 用 PyTorch 实现 cross-attention block。验证：32 个 query 对 256 个 key/value，注意力权重矩阵是 32 x 256，且 softmax 后每行之和为 1。

2. BLIP-2 阶段 1 同时运行三个损失：ITC、ITM、ITG。用伪代码写出每一个的前向签名。哪一个要求文本编码器路径处于激活状态？

3. 比较参数量：Q-Former（12 层，768 隐藏维）vs 2 层 MLP projector（1408 → 4096，两层）。LLM 到什么规模时，188M 的 Q-Former 成本能在训练效率上赚回来？

4. 读 BLIP-2 论文（arXiv:2301.12597）第 3.2 节中关于 Q-Former 如何初始化的内容。解释为什么从 BERT-base（而非随机）初始化能加速收敛。

5. 一段 10 分钟、按 1 FPS 采样成 60 帧的视频，计算每帧的 token 成本：(Q-Former → 每帧 32 token) vs (MLP projector → 每帧 576 token)。哪一个能装进 128k token 的 LLM 上下文窗口？

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| Q-Former | "Querying transformer" | 带有 32 个可学习 query 向量的小 transformer，对冻结 ViT 特征做 cross-attention |
| Learnable queries | "视觉软 prompt" | 一组固定参数，充当 cross-attention 的 query 侧；按模型学习，在所有输入间共享 |
| Cross-attention | "Q 从这来，K/V 从那来" | query、key、value 来自不同来源的注意力；query 就是这样从 ViT patch 拉取信息的 |
| ITC | "图文对比" | 应用在 Q-Former 池化 query vs 文本 CLS 上的 CLIP 式损失 |
| ITM | "图文匹配" | 在难负样本挖掘出的对上做二分类；迫使 query 区分细粒度的不匹配 |
| ITG | "图像接地文本生成" | 以 query 为条件生成文本的因果 LM 损失；迫使 query 编码可被文本解码的内容 |
| Two-stage pretraining | "先表示，后生成" | 阶段 1 只训 Q-Former（ITC/ITM/ITG）；阶段 2 接上冻结 LLM，只训投影 + Q-Former |
| Frozen backbone | "不要微调" | 视觉编码器和 LLM 的权重固定；只有桥在训练 |
| Projection head | "线性投影到 LLM 维度" | 把 Q-Former 输出映射到 LLM 嵌入维度的最终线性层 |
| Perceiver resampler | "Flamingo 的版本" | 类似的可学习 query cross-attention，Flamingo 在每一层都用，而不是作为单一桥梁 |

## Further Reading · 延伸阅读

- [Li et al. — BLIP-2 (arXiv:2301.12597)](https://arxiv.org/abs/2301.12597) — 核心论文。
- [Li et al. — BLIP (arXiv:2201.12086)](https://arxiv.org/abs/2201.12086) — 前作，ITC/ITM/ITG 三件套的出处。
- [Li et al. — ALBEF (arXiv:2107.07651)](https://arxiv.org/abs/2107.07651) — "align before fuse"——阶段 1 训练的概念祖先。
- [Dai et al. — InstructBLIP (arXiv:2305.06500)](https://arxiv.org/abs/2305.06500) — 指令感知的 Q-Former。
- [Zhu et al. — MiniGPT-4 (arXiv:2304.10592)](https://arxiv.org/abs/2304.10592) — 只训投影层的路线。
- [Jaegle et al. — Perceiver IO (arXiv:2107.14795)](https://arxiv.org/abs/2107.14795) — 可学习 query cross-attention 的通用架构。
