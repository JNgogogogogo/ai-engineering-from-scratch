# MIO and Any-to-Any Streaming Multimodal Models · MIO 与 any-to-any 流式多模态模型

> GPT-4o 交付了一个多数开源模型难以复制的产品：一个能听语音、看视频并实时开口回话的智能体。到 2024 年底，开源生态给出的答案是 MIO（Wang et al.，2024 年 9 月）。MIO 把文本、图像、语音和音乐全部 token 化，用一个因果 Transformer 在交错序列上训练，并以任意模态进、任意模态出的方式生成。AnyGPT（Zhan et al.，2024 年 2 月）是概念验证；MIO 是规模放大；Unified-IO 2（Allen AI，2023 年 12 月）是带视觉 + 动作落地的表亲。本课解读 any-to-any 模式 —— 四个 tokenizer、一个 Transformer、对流式友好的解码。

> GPT-4o ships a product most open models cannot replicate: an agent that hears voice, sees video, and speaks back in real time. The open-ecosystem answer by late 2024 was MIO (Wang et al., September 2024). MIO tokenizes text, image, speech, and music, trains one causal transformer over the interleaved sequences, and generates any modality to any modality. AnyGPT (Zhan et al., February 2024) was the proof of concept; MIO is the scale-up; Unified-IO 2 (Allen AI, December 2023) is the cousin with vision + action grounding. This lesson reads the any-to-any pattern — four tokenizers, one transformer, streaming-friendly decode.

**Type:** Learn
**Languages:** Python (stdlib, four-modality token allocator + streaming decode loop)
**Prerequisites:** Phase 12 · 11 (Chameleon), Phase 6 (Speech and Audio)
**Time:** ~120 minutes

## Learning Objectives · 学习目标

- 设计一个承载文本、图像、语音、音乐 token 而互不冲突的共享词表。
- 在压缩率与重建质量的取舍上对比 SEED-Tokenizer（图像）与 SpeechTokenizer 残差 VQ（语音）。
- 解释构建 any-to-any 生成能力的四阶段训练课程。
- 说出三个开源 any-to-any 方案及其主要取舍：MIO、AnyGPT、Unified-IO 2。

> Design a shared vocabulary that hosts text, image, speech, and music tokens without collisions.
> Compare SEED-Tokenizer (images) and SpeechTokenizer residual-VQ (speech) on compression + reconstruction trade-offs.
> Explain the four-stage curriculum that builds up any-to-any generation.
> Name the three open any-to-any recipes and their main trade-offs: MIO, AnyGPT, Unified-IO 2.

## The Problem · 问题在哪

统一多模态模型说来容易，做到规模化很难。2024 年之前的多数「any-to-any」系统都是流水线式的：视觉模型 → 文本表示 → 语音模型 → 音频。每一跳都丢失信息、增加延迟，并让训练变复杂。GPT-4o 的演示视频展示了单模型的替代方案，响应低于一秒；开源系统落后了好几个月。

工程上的挑战：

- 每种模态都必须有 tokenizer，压缩到「足够无损」以支持重建，并以 Transformer 消化得动的速率产出 token。
- 单一词表必须为文本（32k+）、图像（16k+）、语音（4k+）、音乐（8k+）分配空间。最少四万多条目。
- 训练数据必须覆盖每一种输入-输出对（文本→图像、图像→语音、语音→图像等），否则模型必须学会自行组合。
- 推理必须以足够快的速度流出输出 token，满足对话延迟（首个音频字节 <500ms）。

> A unified multimodal model is easy to claim and hard to build at scale. Most "any-to-any" systems until 2024 were pipelined: vision model → text representation → speech model → audio. Each hop loses information, adds latency, and complicates training. ... The engineering challenges: Tokenizers must exist for every modality, compress losslessly-enough for reconstruction, and produce tokens at rates the transformer can consume. ... Inference must stream output tokens fast enough for conversational latency (<500ms time-to-first-audio-byte).

## The Concept · 概念

### Four tokenizers for four modalities · 四种模态，四个 tokenizer

MIO 的 tokenizer 栈：

- 文本：标准 BPE，词表约 32000。
- 图像：SEED-Tokenizer（2023）—— 带离散码本的量化 VAE，4096 个条目，每张图 32x32 个 token。
- 语音：SpeechTokenizer 残差 VQ（2023）—— 把 16kHz 波形编码进 8 个分层码本；第一层是粗粒度内容，后面的层补充韵律和说话人身份。
- 音乐：类似的残差 VQ（Meta 的 MusicGen / Encodec 一族），4-8 个码本。

每种模态产出整数 token。这些 token 在共享词表里占据互不重叠的 ID 区段：

```
text:   0..31999
image:  32000..36095  (4096 image tokens)
speech: 36096..40191  (4096 speech base tokens, plus residual layers)
music:  40192..48383  (8192 music tokens)
sep:    48384..48390  (<image>, <speech>, <music>, </...>, etc.)
```

总计约 48k 词表。输入嵌入与输出投影覆盖全部区间。

> MIO's tokenizer stack: Text: standard BPE, vocab ~32000. Image: SEED-Tokenizer (2023)... Speech: SpeechTokenizer residual-VQ (2023)... Music: similar residual-VQ... ... Each modality produces integer tokens. The tokens get disjoint ID ranges in the shared vocabulary: ... Total: ~48k vocabulary. The input embedding and output projection span all of it.

### Streaming decode · 流式解码

语音生成使用残差 VQ。Transformer 预测基础层（layer 0）语音 token；并行解码的残差量化器预测后续各层。每个 layer 0 token 大约对应 16kHz 音频的 50ms。

流式模式：

1. 用户对着麦克风说话；实时音频 tokenizer 每 50ms 产出一批语音 token。
2. MIO 随到随消化（prompt 预填充 + 增量前向）。
3. 输出 token 边生成边流出；并行语音解码器以约 50-150ms 的延迟把它们转成音频采样。
4. 首个音频字节时间：MIO 论文约 300-500ms，逼近 GPT-4o 的约 250ms。

Mini-Omni（arXiv:2408.16725）、GLM-4-Voice（arXiv:2412.02612）和 Moshi（arXiv:2410.00037）是互补的流式语音-LLM 设计。其中 Moshi 在单张 GPU 上做到 160ms 往返。

> Speech generation uses residual-VQ. The transformer predicts the base (layer 0) speech tokens; a parallel-decoded residual quantizer predicts the subsequent layers. ... The streaming pattern: ... Time-to-first-audio-byte: ~300-500ms in MIO paper, approaching GPT-4o's ~250ms. ... Mini-Omni (arXiv:2408.16725), GLM-4-Voice (arXiv:2412.02612), and Moshi (arXiv:2410.00037) are complementary streaming speech-LLM designs. Moshi in particular achieves 160ms round-trip on a single GPU.

### Four-stage curriculum · 四阶段训练课程

MIO 的训练课程：

1. 阶段 1 —— 对齐。大规模模态对语料：文本-图像、文本-语音、文本-音乐。每一对使用自己的词表区段。训练共享词表。
2. 阶段 2 —— 交错。多模态交错文档（带图像和视频的博客、带文字稿的播客等）。训练跨模态上下文。
3. 阶段 3 —— 语音增强。额外音频数据，在不损失文本能力的前提下抬升语音质量。
4. 阶段 4 —— SFT。跨模态指令微调：VQA、描述、旁白、语音到语音对话。

缺了哪个阶段，对应能力就会退化：跳过阶段 2，模型失去跨模态上下文；跳过阶段 3，语音就差。

> MIO's training curriculum: Stage 1 — alignment. Large-scale modality-pair corpora: text-image, text-speech, text-music. ... Stage 2 — interleaved. Multi-modality interleaved documents... Stage 3 — speech-enhanced. Extra audio data to lift speech quality without losing text capability. Stage 4 — SFT. Instruction tuning across modalities... ... Missing a stage degrades specific capabilities: skip stage 2 and the model loses cross-modality context; skip stage 3 and speech is poor.

### Chain-of-visual-thought · 视觉思维链

MIO 提出视觉思维链（chain-of-visual-thought）：模型把中间图像 token 当作一个推理步骤输出。对「猫在爬树吗？」这个问题，模型会：

1. 产出 `<image>` token，渲染出场景（来自输入图像或一张草图）。
2. 产出文本分析这张草图。
3. 产出最终答案。

渲染出的中间图像就是一块草稿纸。空间推理类任务的基准成绩因此提升。这个思路对标文本推理的思维链（chain-of-thought）。

> MIO introduces chain-of-visual-thought: the model emits intermediate image tokens as a reasoning step. For "is the cat climbing a tree?" the model: Emits `<image>` tokens rendering the scene... Emits text analyzing the sketch. Emits the final answer. ... The rendered intermediate image serves as a scratchpad. Benchmarks improve on spatial-reasoning tasks. The idea mirrors chain-of-thought for text reasoning.

### Competitors in any-to-any · any-to-any 的竞争者们

- AnyGPT（arXiv:2402.12226）：4 种模态（文本、图像、语音、音乐），设计类似。
- Unified-IO 2（arXiv:2312.17172）：增加视觉动作输出、深度、法线。任务更多样，规模更小。
- NExT-GPT（arXiv:2309.05519）：LLM + 模态专属扩散解码器。不是单模型方案。
- CoDi（arXiv:2305.11846）：可组合扩散；经由共享潜空间实现 any-to-any。

MIO 是最接近纯 token any-to-any 的方案。AnyGPT 是它的概念前身。

> AnyGPT (arXiv:2402.12226): 4 modalities (text, image, speech, music), similar design. Unified-IO 2 (arXiv:2312.17172): adds vision action outputs, depth, normals. ... NExT-GPT (arXiv:2309.05519): LLM + modality-specific diffusion decoders. Not a single-model approach. CoDi (arXiv:2305.11846): composable diffusion; any-to-any via shared latent. ... MIO is the closest to pure-token any-to-any. AnyGPT is its conceptual ancestor.

### Latency budget · 延迟预算

对一个对话产品，每个环节的延迟都算数：

- 麦克风到音频 token：约 50ms。
- 预填充（音频 token + 历史）：8B 模型约 100ms。
- 首个输出 token：约 50ms。
- 并行残差 VQ + 语音解码器：约 100-150ms。

首个音频字节总时间：最少约 300ms。GPT-4o 宣称约 250ms。Moshi 宣称 160ms。公开基准下 MIO/AnyGPT 处在 400-600ms 区间。

> For a conversational product, every component's latency matters: Mic to audio tokens: ~50ms. Prefill (audio tokens + history): ~100ms on an 8B model. ... Total time-to-first-audio-byte: ~300ms minimum. GPT-4o claims ~250ms. Moshi claims 160ms. MIO/AnyGPT are in the 400-600ms range per public benchmarks.

### Why any-to-any stays hard · 为什么 any-to-any 依然难

即便到了 2026 年，开源 any-to-any 模型仍在两个维度上落后于闭源：

- 语音质量。残差 VQ tokenizer 是有损的；对话语音比起 ElevenLabs 级别的声音显得机械。
- 跨模态推理。让模型「唱一首关于你眼前所见」仍然比纯视觉任务更容易失败。

这些是开放的研究问题。Qwen3-Omni（第 12.20 课）是 2025 年最先进的开源尝试。

> Even in 2026, open any-to-any models trail closed ones on two axes: Speech quality. The residual-VQ tokenizer is lossy; conversational speech sounds robotic compared to ElevenLabs-class voices. Cross-modality reasoning. Asking the model "sing about what you see" still fails more often than pure-vision tasks. ... These are open research problems. Qwen3-Omni (Lesson 12.20) is the most advanced open attempt in 2025.

```figure
any-to-any-stream
```

## Use It · 实战用法

`code/main.py`：

- 定义四模态词表分配并打印。
- 把一组多模态输入（文本、图像、音频片段、音乐）路由过 tokenizer 路由器。
- 模拟一次文本转语音响应的流式解码，并统计延迟。
- 给定编码器、预填充和解码器延迟，计算预期的首个音频字节时间。

> `code/main.py`: Defines the four-modality vocabulary allocation and prints it. Routes a list of multimodal inputs (text, image, audio-clip, music) through the tokenizer router. Simulates streaming decode for a text-to-speech response with latency counting. Computes the expected time-to-first-audio-byte given encoder, prefill, and decoder latencies.

## Ship It · 交付

本课产出 `outputs/skill-any-to-any-pipeline-auditor.md`。给定一个对话产品的规格（输入模态、输出模态、延迟目标），它审计 MIO 系的设计选择并计算延迟预算。

> This lesson produces `outputs/skill-any-to-any-pipeline-auditor.md`. Given a conversational product spec (modalities in, modalities out, latency target), it audits the MIO-family design choices and computes the latency budget.

## Exercises · 练习

1. 你的产品接收语音输入并返回语音输出。端到端延迟预算目标定多少？列出每一个耗时环节。

2. SpeechTokenizer 残差 VQ 使用 8 个码本。说明为什么残差各层必须并行解码（而非串行），以及它带来多少延迟节省。

3. 你的词表有 32k 文本 + 4k 图像 + 4k 语音。再加入 8k 音乐和约 10 个分隔符。隐藏维 4096 时嵌入矩阵的参数开销是多少？

4. 视觉思维链会产出一张中间图像。哪类问题因此受益？哪类问题会被额外的 token 拖累？

5. 阅读 Moshi（arXiv:2410.00037）。描述它的「内心独白」（inner monologue）技术，并与 MIO 的视觉思维链作比较。

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|------------------------|
| Any-to-any | 「多模态进出」 | 单个模型以任意方向接收并产出文本、图像、语音和音乐 |
| 残差 VQ（Residual-VQ） | 「语音 tokenizer 栈」 | 多码本 token 化，每层补充信息；基础层是内容，后续层是韵律 |
| SEED-Tokenizer | 「图像编码」 | MIO 使用的离散图像 tokenizer，码本 4096 个条目 |
| 视觉思维链（Chain-of-visual-thought） | 「视觉草稿纸」 | 模型在给出最终答案前，先生成一张中间图像作为推理步骤 |
| 首个音频字节时间（Time-to-first-audio-byte） | 「TTFAB」 | 从用户发声到第一段音频输出的延迟；对话体感要求 <500ms |
| 四阶段课程（Four-stage curriculum） | 「训练配方」 | 按此顺序：对齐 -> 交错 -> 语音增强 -> SFT |

## Further Reading · 延伸阅读

- [Wang et al. — MIO (arXiv:2409.17692)](https://arxiv.org/abs/2409.17692)
- [Zhan et al. — AnyGPT (arXiv:2402.12226)](https://arxiv.org/abs/2402.12226)
- [Lu et al. — Unified-IO 2 (arXiv:2312.17172)](https://arxiv.org/abs/2312.17172)
- [Wu et al. — NExT-GPT (arXiv:2309.05519)](https://arxiv.org/abs/2309.05519)
- [Tang et al. — CoDi (arXiv:2305.11846)](https://arxiv.org/abs/2305.11846)
