# InternVL3: Native Multimodal Pretraining · InternVL3：原生多模态预训练

> 在 InternVL3 之前，每个开源 VLM 都走同一条三步配方：拿一个在海量文本 token 上训好的文本 LLM，装上视觉编码器，再微调接缝。这能跑通，但带着对齐债（alignment debt）—— 文本 LLM 把全部预训练预算花在了纯文本上，并不天然理解视觉 token。事后加装视觉时，LLM 得在不忘掉文本的前提下，重新学习怎么把视觉输入和自己的文本推理联系起来。InternVL3（Zhu et al.，2025 年 4 月）拒绝事后加装：一次预训练，文本和多模态从第一步就交错。结果是 78B 参数的开源模型在 MMMU-Pro 上追平 Gemini 2.5 Pro。本课读懂原生预训练的理由，以及选择它之后什么会变。

> Every open VLM before InternVL3 followed the same three-step recipe: take a text LLM trained on trillions of text tokens, bolt on a vision encoder, then fine-tune the seams. This works but has alignment debt — the text LLM has spent its full pretraining budget on pure text and does not natively understand visual tokens. When you add vision post-hoc, the LLM has to re-learn how to relate visual input to its text reasoning without forgetting the text. InternVL3 (Zhu et al., April 2025) rejects the post-hoc approach: one pretraining run, text and multimodal interleaved from step one. The result matches Gemini 2.5 Pro on MMMU-Pro at 78B params open. This lesson reads the case for native pretraining and what changes when you make it.

**Type:** Learn
**Languages:** Python (stdlib, training-corpus mixer)
**Prerequisites:** Phase 12 · 05, Phase 12 · 07 (recipes)
**Time:** ~120 minutes

## Learning Objectives · 学习目标

- 解释为什么事后补视觉的 VLM 训练会累积对齐债，并举出三个可测症状（灾难性遗忘、答案漂移、视觉-文本不一致）。
- 描述 InternVL3 的原生预训练语料配比，以及 text : interleaved : caption 的比例为什么重要。
- 比较 V2PE（可变视觉位置编码）与 Qwen2-VL 的 M-RoPE。
- 说出 Visual Resolution Router（ViR）与 Decoupled Vision-Language（DvD）两个部署优化。

> Explain why post-hoc VLM training accumulates alignment debt, citing the three measurable symptoms (catastrophic forgetting, answer drift, visual-text inconsistency).
> Describe InternVL3's native pretraining corpus mix and why the ratio of text : interleaved : caption matters.
> Compare V2PE (variable visual position encoding) to Qwen2-VL's M-RoPE.
> Name the Visual Resolution Router (ViR) and Decoupled Vision-Language (DvD) deployment optimizations.

## The Problem · 问题在哪

事后补视觉（post-hoc）的 VLM 训练是默认做法。LLaVA、BLIP-2、Qwen-VL、Idefics —— 全都是拿一个已预训练好的 LLM（Llama、Vicuna、Qwen、Mistral）再加上视觉。训练阶段通常长这样：

1. 冻结 LLM + 冻结视觉编码器 + 可训练投影器，用 caption 对训练来对齐嵌入。
2. 解冻 LLM，用指令数据训练（LLaVA-Instruct、ShareGPT4V）。
3. 可选的任务专项微调。

对齐债的三个症状随之出现：

- 灾难性遗忘。事后补视觉的 VLM 忘掉纯文本技能。GSM8K 掉 5-10 分。Hellaswag 掉分。纯文本 agent 退化。
- 答案漂移。同一个视觉问题换个措辞，答案就不一样。视觉编码器连进 LLM 的「绑定」，比 LLM 自己的 token 之间的绑定更弱。
- 视觉-文本不一致。VLM 能正确描述一张图，然后给出与自己的描述相矛盾的答案。视觉 token 没有像文本那样参与 LLM 的内部一致性检查。

这些症状都有据可查。MM1.5 第 4 节量化了它们。LLaVA-OneVision 的消融也暗示了它们。原生预训练就是答案。

> Post-hoc VLM training is the default. ... Three symptoms of alignment debt show up: catastrophic forgetting ... answer drift ... visual-text inconsistency ... These symptoms are well-documented. MM1.5 Section 4 quantifies them. LLaVA-OneVision's ablations hint at them. Native pretraining is the answer.

## The Concept · 概念

### Native multimodal pretraining · 原生多模态预训练

InternVL3 从第一步起就在原生多模态语料上从头训练。配比是：

- 40% 纯文本数据（FineWeb、Proof-Pile-2 等）
- 35% 图文交错数据（OBELICS、MMC4 风格）
- 20% 成对的图文 caption 数据
- 5% 视频-文本数据

视觉 token、文本 token、跨模态交互从第一个梯度步起就进入同一个 loss。没有对齐预训练，没有冻结投影器阶段，没有要恢复的灾难性遗忘。

基座模型的训练只有单一阶段。后面跟着指令微调，但基座已经把视觉 token 当一等公民对待。

> InternVL3 trains from scratch on a corpus that is native multimodal from step one ... Vision tokens, text tokens, and cross-modal interactions all participate in the same loss from the first gradient step. No alignment pretraining, no projector freezing stage, no catastrophic forgetting to recover from. ... Training is a single stage for the base model.

### V2PE (variable visual position encoding) · V2PE（可变视觉位置编码）

Qwen2-VL 用的是固定轴分配的 M-RoPE。InternVL3 引入 V2PE：位置编码按模态类型（文本、图像、视频）变化，缩放系数可学习。实践上：

- 文本 token 用 1D 位置（文本序号）。
- 图像 patch 用 2D 位置（行、列）。
- 视频帧用 3D 位置（时间、行、列）。

三者共享同一个 RoPE 频率基，但每个频段的隐藏维分配是学出来的参数，而不是固定切分。预训练时可以自由权衡时间与空间的频率分辨率。

V2PE 的消融结论：同样算力下，视频基准比 M-RoPE 高 1-2 分。不是革命，但更干净。

> Qwen2-VL uses M-RoPE with fixed axis allocation. InternVL3 introduces V2PE: the position encoding varies per modality type (text, image, video) with learnable scaling ... The three share the same RoPE frequency base, but the hidden-dim allocation per band is a learned parameter rather than a fixed split. ... V2PE's ablation claim: 1-2 points on video benchmarks over M-RoPE at the same compute. Not a revolution, but cleaner.

### Visual Resolution Router (ViR) · 视觉分辨率路由器（ViR）

部署优化。不是所有图都需要全分辨率编码。一张只有一个低细节物体的照片，按 1280px 原生编码就是浪费 token。ViR 是一个小分类器，在编码之前预测回答这个问题所需的最小分辨率。

路由分三档：低清（256 token）、中（576）、高（2048+）。生产流量里 60% 的查询用低或中就够了。净效果：同等质量下 2-3 倍吞吐。

> Deployment optimization. Not all images need full-resolution encoding. ... ViR is a small classifier that predicts the minimum resolution needed to answer the question, before encoding. ... The routing has three tiers: low-res (256 tokens), medium (576), high (2048+). For 60% of queries in production traffic, low or medium is sufficient. Net effect: 2-3x throughput at equal quality.

### Decoupled Vision-Language deployment (DvD) · 视觉-语言解耦部署（DvD）

服务一个大 VLM 时，视觉编码器每张图只跑一次，LLM 却要为每个输出 token 自回归地跑。两个组件的瓶颈不同（视觉 = 卷积 + 注意力的 GPU 显存带宽；LLM = KV cache）。DvD 把它们拆到不同 GPU 上，中间用流式传输衔接。

对一个 8B + 400M 编码器的模型，DvD 的单节点吞吐约是共置部署的两倍。

> When you serve a large VLM, the vision encoder runs once per image but the LLM runs autoregressively for every output token. The two components have different bottlenecks ... DvD splits them onto separate GPUs with streaming between. ... For an 8B + 400M encoder model, DvD roughly doubles per-node throughput vs co-located.

### Single-stage vs multi-stage quality · 单阶段 vs 多阶段的质量

InternVL3 的核心基准结论：78B 参数追平 Gemini 2.5 Pro 的 MMMU-Pro。38B 追平 GPT-4o。8B 领跑开源 8B 榜。全部用的是「单阶段预训练 + 指令微调」配方。

对齐债假说是可测的：每单位视觉基准涨分，InternVL3-8B 在文本基准（MMLU、GSM8K）上丢的分比 Qwen2.5-VL-7B 少。这个模型更像通才，因为训练是一整块，不是两块。

> InternVL3's primary benchmark claim: at 78B params, match Gemini 2.5 Pro's MMMU-Pro. At 38B, match GPT-4o. At 8B, lead the open-8B leaderboard. All on a single-stage pretrain + instruction-tune recipe. ... The alignment-debt hypothesis is measurable: InternVL3-8B loses fewer text-benchmark points (MMLU, GSM8K) than Qwen2.5-VL-7B per unit of vision-benchmark gain. The model is more of a generalist because training was one piece, not two.

### InternVL3.5 and InternVL-U · InternVL3.5 与 InternVL-U

InternVL3.5（2025 年 8 月）把配方放大。同样的原生预训练路线、更多数据、更多参数。MMMU 的提升是增量式的。

InternVL-U（2026）加入统一生成 —— 在同一骨干上通过 MMDiT 头输出图像。「U」代表「Understanding + generation」，追赶 Transfusion 式的统一模型（第 12.13 课）。同一个原生预训练骨干同时支撑理解头和生成头。

> InternVL3.5 (August 2025) scales the recipe. Same native-pretrain approach, more data, more params. ... InternVL-U (2026) adds unified generation — image output via MMDiT heads on top of the same backbone. The "U" stands for "Understanding + generation," chasing Transfusion-style unified models (Lesson 12.13).

### Trade-offs of native pretraining · 原生预训练的代价

原生预训练不是免费的：

- 算力。从头训一个新 VLM 的成本等于训一个文本 LLM —— 数百万 GPU 小时。事后适配复用现成 LLM 权重，省下大头。
- 数据。大规模图文交错语料稀缺。OBELICS 是 1.41 亿文档；MMC4 是 5.71 亿。纯文本动辄 15T token。多模态预训练的数据稀缺是硬约束。
- 基座 LLM 复用。原生预训练放弃了以后换新 LLM 的选项。事后适配可以只重训适配器，就把 Llama-3.1 换成 Llama-4。

InternVL3 押的是：对齐债比复用损失更贵。基准支持这个判断。生产成本也把后来的实验室挡在廉价复刻之外。事后补视觉的 VLM 会继续存在，因为对多数项目它仍然更便宜。

> Native pretraining is not free: compute ... data ... base-LLM reuse ... The bet InternVL3 makes: the alignment debt is worse than the reuse loss. The benchmarks back the claim. The cost-to-produce bars future labs from cheaply replicating. Post-hoc VLMs will keep existing because they remain cheaper for most projects.

```figure
l5-native-pretrain
```

## Use It · 实战用法

`code/main.py` 是一个训练语料混合器加 ViR 路由模拟器。它：

- 接收目标语料配比（%text、%interleaved、%caption、%video），算出每个模态的预期步数。
- 在一批查询上模拟 ViR 路由（分布：50% 低细节、30% 中、20% 高细节），报告平均 token 数。
- 给定编码器与 LLM 的 FLOPs，报告 DvD 吞吐估计。
- 并排打印 post-hoc 与原生预训练在参数、算力、数据和预期对齐债症状上的对照。

> `code/main.py` is a training-corpus mixer and ViR router simulator. It: takes a target corpus mix (%text, %interleaved, %caption, %video) and computes expected steps per modality ... Prints a side-by-side of post-hoc vs native pretraining in params, compute, data, and expected alignment-debt symptoms.

## Ship It · 交付

本课产出 `outputs/skill-native-vs-posthoc-auditor.md`。给定一份 VLM 训练计划，它审计该走原生还是事后路线、标记对齐债风险、并推荐语料配比。当你在为一个新的开源 VLM 项目估规模、需要选训练策略时用它。

> This lesson produces `outputs/skill-native-vs-posthoc-auditor.md`. Given a proposed VLM training plan, it audits whether to go native or post-hoc, flags alignment-debt risk, and recommends a corpus mix. Use it when you are sizing a new open-VLM project and need to pick the training strategy.

## Exercises · 练习

1. 估算 InternVL3-8B（原生预训练）与 LLaVA-OneVision-7B（事后适配）之间的算力差。GPU 小时数大约差多少倍？怎么解释这个差距？

2. InternVL3 报告 40% 文本 / 35% 交错 / 20% caption / 5% 视频。如果你的目标任务偏视频，提出一个新配比，并论证为什么基座模型仍需要可观的文本和 caption 数据。

3. 读 MM1.5 第 4 节讲遗忘的部分。说出事后训练退化最大的那个基准。退化代价是多少？

4. ViR 把 60% 流量路由到低分辨率编码。它会把哪类查询路由错（该高清却给了低清）？提出三种路由器失效模式。

5. DvD 把视觉和 LLM 拆到不同 GPU。什么流量模式下 DvD 会损害而非提升吞吐？

> Estimate the compute delta between InternVL3-8B (native pretrain) and LLaVA-OneVision-7B (post-hoc). Ratio of GPU-hours approximately? What explains the gap? ... ViR routes 60% of traffic to low-resolution encoding. What kinds of queries does it misroute (sends to low-res when high-res was needed)? Propose three router-failure modes. ... DvD splits vision and LLM onto separate GPUs. Under what traffic pattern does DvD hurt throughput instead of helping?

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Native multimodal pretraining | "从零一起训" | 文本 + 图像 + 视频 token 从第 1 步就进 loss，而不是事后加装 |
| Alignment debt | "事后惩罚" | 把视觉硬接到冻结 LLM 上带来的、可测的文本能力与答案一致性退化 |
| V2PE | "可变视觉位置编码" | 按模态可学习的位置编码分配；InternVL3 对 M-RoPE 的接替者 |
| ViR | "分辨率路由器" | 编码前为每个查询挑最小够用分辨率的小分类器，省下推理 token |
| DvD | "解耦部署" | 视觉编码器一个 GPU、LLM 另一个 GPU、流式交接；大 VLM 吞吐翻倍 |
| InternVL-U | "理解 + 生成统一" | 2026 年续作，在原生预训练骨干上加图像生成头 |
| Interleaved corpus | "OBELICS / MMC4" | 文本和图像按自然阅读顺序交错的文档；原生预训练的原料 |

## Further Reading · 延伸阅读

- [Chen et al. — InternVL 1 (arXiv:2312.14238)](https://arxiv.org/abs/2312.14238)
- [Zhu et al. — InternVL3 (arXiv:2504.10479)](https://arxiv.org/abs/2504.10479)
- [InternVL3.5 (arXiv:2508.18265)](https://arxiv.org/abs/2508.18265)
- [InternVL-U (arXiv:2603.09877)](https://arxiv.org/abs/2603.09877)
- [Zhang et al. — MM1.5 (arXiv:2409.20566)](https://arxiv.org/abs/2409.20566)
