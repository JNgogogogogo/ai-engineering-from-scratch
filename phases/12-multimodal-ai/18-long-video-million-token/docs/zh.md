# Long-Video Understanding at Million-Token Context · 百万 token 上下文下的长视频理解

> 一段 1 小时的 4K 视频、24 FPS，经 patch 化和嵌入后，产出大约 6000 万 token。一期 2 小时的播客转成文字是 3 万 token。一部完整的蓝光电影，即便激进池化，也有数十万 token。Google 的 Gemini 1.5（2024 年 3 月）以 1000 万 token 上下文开启了这一时代，能对一小时长的视频做可靠的大海捞针式召回。LWM（Liu et al.，2024 年 2 月）展示了环形注意力的扩展路径。LongVILA 和 Video-XL 把摄入规模继续推高。VideoAgent 则用智能体检索换掉原始上下文。每种方案都是在算力、召回和工程复杂度之间做不同的取舍。本课把它们放在一起对照解读。

> A 1-hour 4K video at 24 FPS, patched and embedded, produces on the order of 60 million tokens. A 2-hour podcast episode transcribed is 30,000 tokens. A full Blu-ray feature film, even compressed with aggressive pooling, is hundreds of thousands of tokens. Google's Gemini 1.5 (March 2024) opened this era with a 10-million-token context, doing reliable needle-in-a-haystack recall over hour-long videos. LWM (Liu et al., February 2024) showed ring attention's scaling path. LongVILA and Video-XL scaled ingestion further. VideoAgent swapped raw context for agentic retrieval. Each approach is a different trade-off on compute, recall, and engineering complexity. This lesson reads them side by side.

**Type:** Build
**Languages:** Python (stdlib, needle-in-haystack simulator + agentic-retrieval router)
**Prerequisites:** Phase 12 · 17 (video temporal tokens)
**Time:** ~180 minutes

## Learning Objectives · 学习目标

- 计算长视频在不同 FPS 与池化配置下的视觉 token 总量。
- 解释三条扩展路径：暴力上下文（Gemini 1.5）、环形注意力（LWM）、token 压缩（LongVILA / Video-XL）。
- 在精度与延迟上对比原始上下文视频 VLM 与智能体检索式视频 VLM（VideoAgent）。
- 为一段 30 分钟视频设计大海捞针测试，并测量特定分钟的召回率。

> Compute total visual-token counts for long-form video at varying FPS and pooling.
> Explain the three scaling paths: brute context (Gemini 1.5), ring attention (LWM), token compression (LongVILA / Video-XL).
> Compare raw-context video VLMs vs agentic-retrieval video VLMs (VideoAgent) on accuracy and latency.
> Design a needle-in-a-haystack test for a 30-minute video and measure recall at a specific minute.

## The Problem · 问题在哪

一帧 Qwen2.5-VL 规格、384 原生分辨率的 patch 约 729 个 token。做 3x3 池化后每帧 81 个 token。30 分钟片段、1 FPS = 1800 帧 = 145,800 个 token。2025 年的开源 VLM 装得下，但很紧。2 FPS 就是 291,600 个 token —— 只有最大的上下文才装得下。

一部 2 小时电影、1 FPS 是 58.3 万 token。超出多数 2026 年开源模型的能力；要么上 Gemini 2.5 Pro，要么池化得更狠。

三条扩展路径由此出现。

> A single frame of Qwen2.5-VL-sized patches at 384 native resolution is ~729 tokens. At 3x3 pooling that's 81 tokens per frame. A 30-minute clip at 1 FPS = 1800 frames = 145,800 tokens. Doable by 2025 open VLMs, tight. At 2 FPS, 291,600 tokens — only the biggest contexts fit. ... A 2-hour movie at 1 FPS is 583k tokens. Beyond most 2026 open models; requires Gemini 2.5 Pro or pooling more aggressively. ... Three scaling paths emerged.

## The Concept · 概念

### Path 1: Brute context (Gemini 1.5, Claude Opus) · 路线一：暴力上下文（Gemini 1.5、Claude Opus）

用硬件硬砸。把上下文扩到数百万 token，一次前向处理全部内容。

Gemini 1.5 Pro 发布时有 100 万 token；Gemini 1.5 Ultra 到 1000 万；2026 年的 Gemini 2.5 Pro 能稳定处理数小时的视频。论文（arXiv:2403.05530）记录了到约 950 万 token 为止 99.7% 的大海捞针召回率。

工程实现：带记忆层级（local + global + sparse）的定制注意力实现，加上面向长上下文效率的 MoE 专家路由。未公开完整细节。未开源。

> Throw hardware at the problem. Scale context to millions of tokens, process everything in one forward pass. ... Gemini 1.5 Pro launched with 1M tokens; Gemini 1.5 Ultra to 10M; Gemini 2.5 Pro in 2026 does hours of video reliably. The paper (arXiv:2403.05530) documents needle-in-a-haystack recall at 99.7% up to ~9.5M tokens. ... Engineering: a custom attention implementation with memory hierarchy (local + global + sparse) plus MoE expert routing for long-context efficiency. Not published in full detail. Not open-source.

### Path 2: Ring attention (LWM, LongVILA) · 路线二：环形注意力（LWM、LongVILA）

环形注意力把长序列分布到一组「环」上的设备，每台设备持有一个分块。跨全序列的注意力这样完成：每台设备把自己的分块按环形模式发给下一台，计算部分注意力，再聚合。

LWM（Liu et al.，2024）用这种方式训练了 100 万 token 上下文的模型。训练算力随上下文线性增长，而非二次方 —— 注意力的二次方代价被环上的设备摊薄了。

LongVILA（arXiv:2408.10188）把这一模式移植到 VLM。1400 帧视频、每帧 192 token = 268k 上下文，用 8 路并行的环形注意力训练。

> Ring attention distributes long sequences across devices in a "ring" where each device holds a chunk. Attention across the full sequence happens by each device sending its chunk to the next in a ring pattern, computing partial attention, and aggregating. ... LWM (Liu et al., 2024) trained a 1M-token context model this way. Training compute scales linearly with context, not quadratically ... LongVILA (arXiv:2408.10188) adapted the pattern to VLMs. 1400-frame videos at 192 tokens per frame = 268k context, trained with ring attention across 8-way parallelism.

### Path 3: Token compression (Video-XL, LongVA) · 路线三：token 压缩（Video-XL、LongVA）

比暴力上下文便宜：在 LLM 看到序列之前先激进压缩。

Video-XL（arXiv:2409.14485）使用视觉摘要 token：每 N 帧的片段产出一个对这 N 帧做注意力的「摘要」token。推理时 LLM 每个片段只看到一个摘要 token，上下文急剧缩短。

LongVA 用「长上下文迁移」技术把 LLM 上下文从 20 万扩到 200 万。先在长上下文文本上训练，再通过共享表示迁移到长上下文视频。

token 压缩用「特定时间戳上的召回」换「可扩展性」。模型大致知道发生了什么，但有时会漏掉确切的帧。

> Cheaper than brute context: compress aggressively before the LLM sees the sequence. ... Video-XL (arXiv:2409.14485) uses a visual summary token: each clip of N frames produces a single "summary" token that attends over the N. At inference, the LLM sees one summary token per clip, drastically shrinking the context. ... LongVA extends LLM context from 200k to 2M with a "long context transfer" technique. ... Token compression trades off recall at specific timestamps for scalability. The model knows generally what happened but sometimes misses exact frames.

### Path 4: Agentic retrieval (VideoAgent) · 路线四：智能体检索（VideoAgent）

不要把整个视频喂给 LLM。把视频当成数据库，让 LLM 来查询它。

VideoAgent（arXiv:2403.10517）：

1. LLM 读问题。
2. LLM 向检索工具索要相关片段（「给我看有猫的段落」）。
3. 工具返回匹配片段的时间戳。
4. LLM 通过 VLM 读取这些片段。
5. LLM 组织出答案，或继续追问。

这是把 LLM-as-agent 模式应用到长视频上。推理更便宜（只编码相关片段），工程更难（检索质量成为瓶颈）。

> Do not feed the full video to the LLM. Instead, treat the video as a database and use an LLM to query it. ... VideoAgent (arXiv:2403.10517): LLM reads the question. LLM asks a retrieval tool for relevant clips ("show me segments with a cat"). ... LLM reads those clips via a VLM. LLM composes the answer or asks follow-up queries. ... This is the LLM-as-agent pattern applied to long video. Cheaper inference (only relevant clips encoded), harder engineering (retrieval quality becomes the bottleneck).

### Needle-in-a-haystack benchmarks · 大海捞针基准

标准的长上下文测试：在视频的随机位置插入一个独特的视觉或文本标记，然后问一个必须回忆起它的问题。

指标：跨视频长度与标记位置的 Recall@k。

Gemini 2.5 Pro 在最长 90 分钟的视频上召回率 >99%。开源 72B 模型（Qwen2.5-VL-72B、InternVL3-78B）在 30 分钟上约 85-90%，过了 60 分钟开始退化。

VideoAgent 在 2 小时以上能持平甚至超过原始上下文模型 —— 只要工具够好，检索就能命中那根针。

> The standard long-context test: insert a unique visual or textual marker at a random point in the video, then ask a query that requires recalling it. ... Metric: Recall@k across video length and marker position. ... Gemini 2.5 Pro scores >99% recall at up to 90-minute videos. Open 72B models (Qwen2.5-VL-72B, InternVL3-78B) score ~85-90% at 30 minutes and degrade past 60. ... VideoAgent can match or beat raw-context models at 2+ hours because retrieval hits the needle if the tool is good.

### Which path to pick · 怎么选路线

15 分钟片段、要前沿精度：开源 72B + 原生上下文通常够用。选 Qwen2.5-VL-72B。

30 分钟到 1 小时的内容：开源选 LongVILA 或 Video-XL；闭源选 Gemini 2.5 Pro。质量门槛很关键 —— 要前沿就得上闭源。

2 小时以上的内容：VideoAgent 或类似的检索模式。或者切成小块做摘要，再喂层级摘要。

> For a 15-minute clip at frontier accuracy: open 72B + native context usually works. Pick Qwen2.5-VL-72B. ... For 30-minute to 1-hour content: LongVILA or Video-XL for open; Gemini 2.5 Pro for closed. The quality bar matters — frontier goes closed. ... For 2+ hour content: VideoAgent or similar retrieval patterns. Alternatively, summarize to smaller chunks and feed hierarchical summaries.

### 2026 production pattern · 2026 年的生产模式

实践中，生产级长视频流水线是混合式的：

1. 对整段视频跑动态 FPS 采样 + 激进池化（得到 10 万 token 量级的全局表示）。
2. 交给 72B VLM 产出全局摘要。
3. 用户追问细节时，以摘要为索引跑智能体检索。

这样把暴力上下文的全局理解和检索的局部细节结合起来。

> In practice, production long-video pipelines are hybrid: Run dynamic-FPS sampling + aggressive pooling on the entire video (get a 100k-token global representation). Pass to a 72B VLM for a global summary. If user asks detailed questions, run agentic retrieval using the summary as an index. ... This combines brute-context for global understanding and retrieval for local detail.

```figure
mm-video-token-budget
```

## Use It · 实战用法

`code/main.py`：

- 计算从 1 分钟到 3 小时的视频在不同 FPS + 池化下的 token 预算。
- 模拟一次大海捞针：在随机时间戳注入标记、提问、给召回打分。
- 内置一个智能体检索路由模拟器，挑选要喂给下游 VLM 的具体片段。

跑一遍预算表，直观感受量级差距。

> `code/main.py`: Computes token budgets for videos from 1 minute to 3 hours at varying FPS + pooling. Simulates a needle-in-a-haystack run: inject a marker at a random timestamp, ask a question, score recall. Includes an agentic-retrieval router simulator that picks specific clips to feed to a downstream VLM. ... Run the budget table and feel the scale gap.

## Ship It · 交付

本课产出 `outputs/skill-long-video-strategy-planner.md`。给定视频时长和查询复杂度，它在暴力上下文、压缩、智能体检索之间做选择，并计算延迟与质量预期。

> This lesson produces `outputs/skill-long-video-strategy-planner.md`. Given a video duration and query complexity, it picks between brute-context, compression, and agentic retrieval, and computes the latency + quality expectations.

## Exercises · 练习

1. 一段 45 分钟的讲座，1 FPS，每帧 81 token。总 token 数是多少？能装进哪些模型的上下文？

2. 设计一个大海捞针测试：标记注入在第几分钟？查询的精确格式是什么？

3. 在 1 小时视频上对比暴力上下文的 Qwen2.5-VL-72B（80k 上下文）与 VideoAgent（Claude 3.5 + 检索）。谁的召回赢？谁的延迟赢？

4. 环形注意力的内存开销随序列长度线性、随设备数线性。解释为什么，以及去掉环旋转阶段会坏掉什么。

5. 阅读 Gemini 1.5 论文第 5 节的大海捞针部分。论文关于 100 万与 1000 万 token 边界处的召回发现了什么？

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|------------------------|
| 暴力上下文（Brute context） | 「token 堆上去就行」 | 把 LLM 上下文扩到数百万 token；一次前向处理全部 |
| 环形注意力（Ring attention） | 「LWM 式并行」 | 分布式注意力模式：每台设备持有一个分块并沿环轮转 |
| token 压缩（Token compression） | 「摘要 token」 | 在 LLM 之前用可学习压缩器减少每片段 token 数 |
| 大海捞针（Needle-in-haystack） | 「NIH 测试」 | 在随机位置插入独特标记，测试时要求模型回忆它 |
| 智能体检索（Agentic retrieval） | 「LLM 当查询规划器」 | LLM 向检索工具索要相关片段，经 VLM 读取，再组织答案 |
| VideoAgent | 「视频检索模式」 | 经典的智能体检索设计：问题 -> 工具 -> 片段 -> 答案 |

## Further Reading · 延伸阅读

- [Gemini Team — Gemini 1.5 (arXiv:2403.05530)](https://arxiv.org/abs/2403.05530)
- [Liu et al. — LWM / RingAttention (arXiv:2402.08268)](https://arxiv.org/abs/2402.08268)
- [Xue et al. — LongVILA (arXiv:2408.10188)](https://arxiv.org/abs/2408.10188)
- [Shu et al. — Video-XL (arXiv:2409.14485)](https://arxiv.org/abs/2409.14485)
- [Wang et al. — VideoAgent (arXiv:2403.10517)](https://arxiv.org/abs/2403.10517)
