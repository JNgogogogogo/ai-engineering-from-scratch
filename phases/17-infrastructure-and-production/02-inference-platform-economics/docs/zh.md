# Inference Platform Economics — Fireworks, Together, Baseten, Modal, Replicate, Anyscale · 推理平台经济学 —— Fireworks、Together、Baseten、Modal、Replicate、Anyscale

> 2026 年的推理市场不再是租 GPU 时间。它分化成三个世界：定制硅片（Groq、Cerebras、SambaNova）、GPU 平台（Baseten、Together、Fireworks、Modal）和 API 优先的市场（Replicate、DeepInfra）。Fireworks 在 2026 年 5 月 1 日把每块 GPU 的价格上调 $1/hr，而 40 亿美元估值配上日处理 10T+ token 说明走量的模式成立。Baseten 在 2026 年 1 月以 50 亿美元估值完成 3 亿美元的 E 轮。竞争定位规则很简单：Fireworks 优化延迟，Together 优化目录广度，Baseten 优化企业级打磨，Modal 优化 Python 原生开发体验，Replicate 优化多模态覆盖，Anyscale 优化分布式 Python。本课给你一张可以直接递给创始人的矩阵。

> The 2026 inference market is no longer GPU time rental. It bifurcates into custom silicon (Groq, Cerebras, SambaNova), GPU platforms (Baseten, Together, Fireworks, Modal), and API-first marketplaces (Replicate, DeepInfra). Fireworks raised price $1/hr per GPU on May 1, 2026, and $4B valuation on 10T+ tokens/day tells you the volume-driven model works. Baseten closed $300M Series E at $5B in January 2026. The competitive positioning rule is simple: Fireworks optimizes latency, Together optimizes catalog breadth, Baseten optimizes enterprise polish, Modal optimizes Python-native DX, Replicate optimizes multimodal reach, Anyscale optimizes distributed Python. This lesson gives you a matrix you can hand a founder.

**Type:** Learn
**Languages:** Python (stdlib, toy per-call economics comparator)
**Prerequisites:** Phase 17 · 01 (Managed LLM Platforms), Phase 17 · 04 (Serving Engine Internals)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 说出三个市场细分（定制硅片、GPU 平台、API 优先），并把每家厂商映射到对应细分。
- 解释为什么「按 token」的 API 定价会向 serving 引擎的成本曲线压缩，而不是向硬件的成本曲线。
- 至少跨三家厂商计算每次请求的有效成本，并解释什么时候按分钟计费（Baseten、Modal）胜过按 token。
- 针对给定负载（serverless 突发型、稳定高吞吐、微调变体、多模态）判断哪个平台是正确的默认选择。

> Name the three market segments (custom silicon, GPU platforms, API-first) and map each vendor to a segment.
> Explain why the "per-token" API pricing model compresses toward the serving engine's cost curve, not the hardware's.
> Compute effective cost per request across at least three vendors and explain when per-minute (Baseten, Modal) beats per-token.
> Identify which platform is the right default for a given workload (serverless bursty, steady high-throughput, fine-tuned variants, multimodal).

## The Problem · 问题在哪

你评估过托管超大规模平台。你决定需要一个更窄、更快的提供商——要延迟找 Fireworks，要广度找 Together，要跑微调自定义模型找 Baseten。现在你面对六个真实选项，而它们的定价页完全对不上。Fireworks 显示 $/M tokens；Baseten 显示 $/分钟；Modal 显示 $/秒；Replicate 显示 $/prediction。不建模负载就没法头对头比较。

更糟的是，每个定价页背后的商业模式都不同。Fireworks 在共享 GPU 上跑自研引擎（FireAttention）；按 token 的费率反映的是它们的利用率曲线。Baseten 给你 Truss + 专用 GPU；按分钟计费反映的是独占性。Modal 是真正的 Python serverless——按秒计费、亚秒级冷启动。同样的输出（一次 LLM 响应），三种不同的成本函数。

本课把这六家建模一遍，告诉你各自什么时候赢。

> You evaluated managed hyperscaler platforms. You decided you need a narrower, faster provider — Fireworks for latency, Together for breadth, Baseten for a fine-tuned custom model. Now you have six real choices and the pricing pages do not line up. Fireworks shows $/M tokens; Baseten shows $/minute; Modal shows $/second; Replicate shows $/prediction. You cannot compare them head-to-head without modeling the workload.
> Worse, the business model behind each pricing page is different. Fireworks runs its own custom engine (FireAttention) on shared GPUs; the per-token rate reflects their utilization curve. Baseten gives you Truss + dedicated GPUs; per-minute reflects exclusivity. Modal is true Python serverless — per-second billing with sub-second cold starts. Same output (an LLM response), three different cost functions.
> This lesson models the six and tells you when each wins.

## The Concept · 概念

### The three segments · 三个细分市场

**定制硅片** —— Groq（LPU）、Cerebras（WSE）、SambaNova（RDU）。同一模型上解码速度通常比 GPU 集群快 5-10 倍。每 token 价格更高（2025 年底 Groq 在 Llama-70B 上约 $0.99/M），但对延迟敏感的场景无可匹敌。语音助手和实时翻译的生产之选是 Groq。

**GPU 平台** —— Baseten、Together、Fireworks、Modal、Anyscale。跑在 NVIDIA（H100、H200，2026 年还有 B200）上，偶尔是 AMD。位于「裸 GPU 租赁」（RunPod、Lambda）和「超大规模托管服务」（Bedrock）之间的经济层。

**API 优先市场** —— Replicate、DeepInfra、OpenRouter、Fal。目录广、按 prediction 或按秒付费，强调从上手到第一次调用的时间。

> **Custom silicon** — Groq (LPU), Cerebras (WSE), SambaNova (RDU). Typically 5-10x faster decode than a GPU-based cluster on the same model. Higher per-token price (Groq was ~$0.99/M on Llama-70B late 2025) but unbeatable for latency-sensitive use cases. Groq is the production pick for voice agents and real-time translation.
> **GPU platforms** — Baseten, Together, Fireworks, Modal, Anyscale. ... The economic layer between "raw GPU rental" (RunPod, Lambda) and "hyperscaler managed service" (Bedrock).
> **API-first marketplaces** — Replicate, DeepInfra, OpenRouter, Fal. Broad catalog, pay-per-prediction or pay-per-second, emphasize time-to-first-call.

### Fireworks — latency-optimized GPU platform · Fireworks —— 延迟优先的 GPU 平台

- FireAttention 引擎（自研）；宣传在同等配置下比 vLLM 延迟低 4 倍。
- 批处理层价格约为 serverless 费率的 50%，面向非交互负载。
- 微调模型以与基座模型相同的费率提供服务——相比对你的 LoRA 收溢价的提供商，这是真正的差异点。
- 2026 年中：自 2026 年 5 月 1 日起按需 GPU 租赁涨价 $1/小时。上规模后量价可谈。
- 财务信号：估值 40 亿美元，日处理 10T+ token。

> - FireAttention engine (custom); marketed as 4x lower latency than vLLM on equivalent configs.
> - Batch tier at ~50% of serverless rate for non-interactive workloads.
> - Fine-tuned model served at the same rate as the base model — a real differentiator versus providers that charge a premium for your LoRA.
> - Mid-2026: raised on-demand GPU rental $1/hour effective May 1, 2026. Volume pricing negotiable at scale.
> - Financial signal: $4B valuation, 10T+ tokens/day handled.

### Together — breadth-optimized · Together —— 广度优先

- 200+ 模型，开源模型在上游发布几天内即上线。
- 同等 LLM 模型上比 Replicate 便宜 50-70%——「AI Native Cloud」的定位就是走量和目录。
- 推理 + 微调 + 训练一个 API 全包。

> - 200+ models including open-source releases within days of upstream publication.
> - 50-70% cheaper than Replicate on equivalent LLM models — the "AI Native Cloud" positioning is volume and catalog.
> - Inference + fine-tuning + training in one API.

### Baseten — enterprise-polish-optimized · Baseten —— 企业级打磨优先

- Truss 框架：把依赖、密钥、serving 配置打进一个 manifest 的模型打包方式。
- GPU 从 T4 一路到 B200。按分钟计费，冷启动缓解合理。
- SOC 2 Type II、HIPAA-ready。金融科技和医疗的常见选择。
- 估值 50 亿美元，2026 年 1 月 E 轮（CapitalG、IVP、NVIDIA 投的 3 亿美元）。

> - Truss framework: model packaging with dependencies, secrets, serving config in one manifest.
> - GPU range from T4 through B200. Per-minute billing with reasonable cold-start mitigation.
> - SOC 2 Type II, HIPAA-ready. Common fintech and healthcare pick.
> - $5B valuation, January 2026 Series E ($300M from CapitalG, IVP, NVIDIA).

### Modal — Python-native-optimized · Modal —— Python 原生优先

- 基础设施即代码，纯 Python。给函数加 `@modal.function(gpu="A100")` 装饰器，一条命令部署。
- 按秒计费。预热后冷启动 2-4 秒；小模型 <1 秒。
- 2025 年 B 轮 8,700 万美元，估值 11 亿美元。独立调研中最强的开发者体验评分。

> - Infrastructure-as-code in pure Python. Decorate a function with `@modal.function(gpu="A100")` and deploy with one command.
> - Per-second billing. Cold starts 2-4s with pre-warming; <1s for small models.
> - $87M Series B at $1.1B valuation (2025). Strongest developer experience score in independent surveys.

### Replicate — multimodal breadth · Replicate —— 多模态广度

- 按 prediction 付费。图像、视频、音频模型的默认平台。
- 集成生态（Zapier、Vercel、CMS 插件）。
- LLM 每 token 费率竞争力较弱，但赢在多模态种类。

> - Pay-per-prediction. The default platform for image, video, and audio models.
> - Integration ecosystem (Zapier, Vercel, CMS plugins).
> - Less competitive on LLM per-token rates but wins on multimodal variety.

### Anyscale — Ray-native · Anyscale —— Ray 原生

- 基于 Ray 构建；RayTurbo 是 Anyscale 的专有推理引擎（与 vLLM 竞争）。
- 最适合分布式 Python 负载——推理只是更大计算图里的一个节点。
- 托管 Ray 集群；与 Ray AIR、Ray Serve 紧密集成。

> - Built on Ray; RayTurbo is Anyscale's proprietary inference engine (competes with vLLM).
> - Best for distributed Python workloads where the inference step is one node in a larger graph.
> - Managed Ray clusters; tight integration with Ray AIR and Ray Serve.

### Per-token versus per-minute — when each wins · 按 token 对按分钟 —— 各自何时赢

负载延迟不敏感且突发时，按 token 合理——用多少付多少。利用率高且可预测时，按分钟合理——一旦你把 GPU 打满，按分钟就赢了。

粗略规则：负载对一块专用 GPU 的持续利用率超过约 30% 时，按分钟（Baseten、Modal）开始胜过按 token（Fireworks、Together）。低于这个值，按 token 赢，因为你不用为闲置买单。

> Per-token makes sense when the workload is latency-insensitive and bursty — you only pay for what you use. Per-minute makes sense when utilization is high and predictable — you beat per-token once you're saturating the GPU.
> Rough rule: for workloads above ~30% sustained utilization of a dedicated GPU, per-minute (Baseten, Modal) starts to beat per-token (Fireworks, Together). Below that, per-token wins because you avoid paying for idle.

### Custom engine is the real moat · 自研引擎才是真护城河

上面每一家在 vLLM 和 SGLang 之外都声称有自研引擎。FireAttention、RayTurbo、Baseten 的推理栈。自研引擎的说法带着营销滤镜——诚实的说法是：vLLM + SGLang 占生产级开源推理的约 80%，平台层的真正差异在 DX、成本归集和 SLA。

> Every platform above vLLM and SGLang claims a custom engine. FireAttention, RayTurbo, Baseten's inference stack. Custom-engine claims shade marketing — the honest framing is that vLLM + SGLang represent about 80% of production open-source inference, and the differentiators at the platform layer are DX, attribution, and SLAs.

### Numbers you should remember · 你该记住的数字

- Fireworks GPU 租赁：自 2026 年 5 月 1 日起涨价 $1/hr。
- Fireworks 宣称：同等配置下比 vLLM 延迟低 4 倍。
- Together：LLM 上比 Replicate 便宜 50-70%。
- Baseten 估值：50 亿美元（E 轮，2026 年 1 月，3 亿美元）。
- Modal 估值：11 亿美元（B 轮，2025 年）。
- 持续利用率超过约 30% 后，按分钟胜过按 token。

> - Fireworks GPU rental: $1/hr raise effective May 1, 2026.
> - Fireworks claim: 4x lower latency than vLLM on equivalent configs.
> - Together: 50-70% cheaper than Replicate on LLMs.
> - Baseten valuation: $5B (Series E, Jan 2026, $300M round).
> - Modal valuation: $1.1B (Series B, 2025).
> - Per-minute beats per-token above ~30% sustained utilization.

```figure
cost-per-token
```

## Use It · 实战用法

`code/main.py` 在一个合成负载上按不同定价模型对比六家厂商。报告 $/天和有效 $/M tokens。跑一下，找到按 token 与按分钟之间的盈亏平衡点。

> `code/main.py` compares the six vendors on a synthetic workload across pricing models. Reports $/day and effective $/M tokens. Run it to find the break-even between per-token and per-minute.

## Ship It · 交付

本课产出 `outputs/skill-inference-platform-picker.md`。给定负载画像、SLA 和预算，选出主推理平台并给出次选。

> This lesson produces `outputs/skill-inference-platform-picker.md`. Given workload profile, SLA, and budget, picks the primary inference platform and names the runner-up.

## Exercises · 练习

1. 运行 `code/main.py`。一块 H100 上跑 70B 模型，Baseten（按分钟）在多少持续利用率以上胜过 Fireworks（按 token）？自己推导交叉点，再和经验规则对比。
2. 你的产品同时要做图像生成、聊天和语音转文字。为每种模态选平台，并说出统一它们的网关模式。
3. Fireworks 把你的主力模型涨价 $1/hr。如果 40% 的流量转移到批处理层（5 折），建模混合成本的影响。
4. 一个受监管客户要求 SOC 2 Type II + HIPAA + 专用 GPU。哪三家平台可行？哪家在 FinOps 上赢？
5. 对比 Llama 3.1 70B 在 Fireworks serverless、Together 按需、Baseten 专用、Replicate API 上每 1,000 次 prediction 的成本。每天 10 次时谁最便宜？每天 10,000 次呢？

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| Custom silicon | "非 GPU 芯片" | Groq LPU、Cerebras WSE、SambaNova RDU——为 decode 优化 |
| FireAttention | "Fireworks 的引擎" | 自研 attention kernel；宣传比 vLLM 延迟低 4 倍 |
| Truss | "Baseten 的打包格式" | 模型打包 manifest；依赖 + 密钥 + serving 配置 |
| Per-token | "API 计价" | 按消耗的 token 收费；不为闲置付费 |
| Per-minute | "专用计价" | 按 GPU 墙钟时间收费；高利用率时占优 |
| Per-prediction | "Replicate 计价" | 按每次模型调用收费；图像/视频常见 |
| RayTurbo | "Anyscale 的引擎" | Ray 上的专有推理；在 Ray 集群上与 vLLM 竞争 |
| Batch tier | "打五折" | 非交互队列的优惠费率；Fireworks、OpenAI 常见 |
| Fine-tuned at base rate | "Fireworks 的 LoRA 待遇" | LoRA 服务的请求按基座模型费率收费（差异点） |

## Further Reading · 延伸阅读

- [Fireworks Pricing](https://fireworks.ai/pricing) —— 按 token 费率、批处理层、GPU 租赁。
- [Baseten Pricing](https://www.baseten.co/pricing/) —— 按分钟费率、承诺容量、企业分层。
- [Modal Pricing](https://modal.com/pricing) —— 按秒 GPU 费率与免费层。
- [Together AI Pricing](https://www.together.ai/pricing) —— 模型目录与按 token 费率。
- [Anyscale Pricing](https://www.anyscale.com/pricing) —— RayTurbo 与托管 Ray 定价。
- [Northflank — Fireworks AI Alternatives](https://northflank.com/blog/7-best-fireworks-ai-alternatives-for-inference) —— 比较评估。
- [Infrabase — AI Inference API Providers 2026](https://infrabase.ai/blog/ai-inference-api-providers-compared) —— 厂商全景。
