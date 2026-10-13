# Managed LLM Platforms — Bedrock, Vertex AI, Azure OpenAI · 托管 LLM 平台 —— Bedrock、Vertex AI、Azure OpenAI

> 三家超大规模云厂商，三种截然不同的战略。AWS Bedrock 是模型市场——Claude、Llama、Titan、Stability、Cohere 收在同一套 API 背后。Azure OpenAI 是独家的 OpenAI 合作关系，外加提供专用容量的 Provisioned Throughput Units（PTU）。Vertex AI 以 Gemini 为先，长上下文与多模态的故事最完整。2026 年，Artificial Analysis 测得在 Llama 3.1 405B 同级部署上 Azure OpenAI 中位数约 50 ms、Bedrock 约 75 ms——PTU 解释了这个差距，因为专用容量胜过共享按需。决策规则不是「谁最快」，而是「谁的模型目录和 FinOps 界面匹配我的产品」。本课教你把权衡写下来再做选择，而不是凭感觉。

> Three hyperscalers, three distinct strategies. AWS Bedrock is a model marketplace — Claude, Llama, Titan, Stability, Cohere behind one API. Azure OpenAI is an exclusive OpenAI partnership plus Provisioned Throughput Units (PTUs) for dedicated capacity. Vertex AI is Gemini-first with the best long-context and multimodal story. In 2026 Artificial Analysis measures Azure OpenAI at ~50 ms median and Bedrock at ~75 ms on Llama 3.1 405B equivalents — PTUs explain the gap because dedicated capacity beats shared on-demand. The decision rule is not "which is fastest" but "which model catalog and FinOps surface match my product." This lesson teaches you to pick with the tradeoffs written down, not vibes.

**Type:** Learn
**Languages:** Python (stdlib, toy cost-and-latency comparator)
**Prerequisites:** Phase 11 (LLM Engineering), Phase 13 (Tools & Protocols)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 说出三种平台战略（marketplace 市场型 vs 独家合作型 vs Gemini 优先型），并为每一种匹配一个产品用例。
- 解释在 Azure OpenAI 里买 Provisioned Throughput Units（PTU）能换来什么，以及为什么在 405B 量级上按需的 Bedrock 通常读数慢约 25 ms。
- 画出每个平台的 FinOps 成本归集界面（Bedrock Application Inference Profiles vs Vertex 的每团队一个项目 vs Azure 的 scope + PTU 预留）。
- 写下一条「至少双供应商」策略，并解释为什么单一厂商锁定是 2026 年最昂贵的错误。

> Name the three platform strategies (marketplace vs exclusive vs Gemini-first) and match each to a product use case.
> Explain what Provisioned Throughput Units (PTUs) buy you in Azure OpenAI and why on-demand Bedrock typically reads ~25 ms slower at the 405B scale.
> Diagram the FinOps attribution surface for each platform (Bedrock Application Inference Profiles vs Vertex project-per-team vs Azure scopes + PTU reservations).
> Write down a "two-provider minimum" policy and explain why single-vendor lock-in is the expensive mistake in 2026.

## The Problem · 问题在哪

你为产品选定了 Claude 3.7 Sonnet。现在你需要把它服务出去。你可以直接调 Anthropic API，也可以通过 AWS Bedrock 调用，或者再走一层网关。直连 API 最简单；Bedrock 加上 BAA、VPC endpoints、IAM 和 CloudWatch 成本归集；网关则加上故障转移、统一计费和跨提供商的速率限制。

更深一层的问题是目录。如果你要在同一个产品里同时要 Claude、Llama 和 Gemini，你不可能从一家买齐——除非同时签下 Bedrock、Vertex 和 Azure OpenAI 三家。超大规模厂商之间不可互换——它们各自对「谁拥有模型层」下了不同的赌注。

本课梳理这三种赌注、延迟差距、FinOps 差距和锁定风险。

> You picked Claude 3.7 Sonnet for your product. Now you need to serve it. You can call the Anthropic API directly, or you can call it through AWS Bedrock, or you can go through a gateway. The direct API is the simplest; Bedrock adds BAAs, VPC endpoints, IAM, and CloudWatch attribution. The gateway adds failover, unified billing, and rate limits across providers.
> The deeper question is catalog. If you need Claude and Llama and Gemini in the same product, you cannot buy them all from one place unless that place is Bedrock plus Vertex plus Azure OpenAI simultaneously. The hyperscalers are not interchangeable — they each made a different bet on who owns the model layer.
> This lesson maps the three bets, the latency gap, the FinOps gap, and the lock-in risk.

## The Concept · 概念

### Three strategies · 三种战略

**AWS Bedrock** —— 市场型。Claude（Anthropic）、Llama（Meta）、Titan（AWS 第一方）、Stability（图像）、Cohere（embeddings）、Mistral，外加图像与 embedding 子目录。一个 API、一个 IAM 界面、一个 CloudWatch 导出。Bedrock 赌的是：客户要的可选性多过要单一模型。

**Azure OpenAI** —— 独家合作型。你得到 GPT-4 / 4o / 5 / o-series、DALL·E、Whisper，以及 OpenAI 模型在 Azure 数据中心里的微调。「Azure OpenAI Service」目录里没有非 OpenAI 模型——那些归 Azure AI Foundry（另一个产品）。Azure 赌的是：OpenAI 仍是前沿，客户想在这段特定关系上拿到企业级管控。

**Vertex AI** —— Gemini 优先，其余靠后。Gemini 1.5 / 2.0 / 2.5 Flash 与 Pro，外加 Model Garden（第三方）。Vertex 赌的是多模态长上下文——100 万 token 的 Gemini 上下文就是差异化卖点。

> **AWS Bedrock** — the marketplace. ... One API, one IAM surface, one CloudWatch export. Bedrock's bet is that customers want optionality more than they want a single model.
> **Azure OpenAI** — the exclusive partnership. ... Azure's bet is that OpenAI remains the frontier and customers want enterprise controls on that specific relationship.
> **Vertex AI** — Gemini first, everything else second. ... Vertex's bet is multimodal long-context — 1M-token Gemini context is the differentiator.

### Latency gap at scale · 规模化下的延迟差距

Artificial Analysis 持续跑基准。在同等的 Llama 3.1 405B 部署（共享按需）上，Azure OpenAI 首 token 中位延迟约 50 ms；Bedrock 约 75 ms。这个差距不是 AWS 的失败——它是容量模型的差异。Azure 卖 PTU（Provisioned Throughput Units），为你的租户预留 GPU 容量。Bedrock 的对应物（Provisioned Throughput）存在但每单元约 $21/小时起，大多数客户仍留在共享按需上。

按需共享容量要和所有其他客户的流量抢资源。专用容量不用。如果你的产品 SLA 是 P99 TTFT < 100 ms，你要么在 Azure 买 PTU，要么买 Bedrock Provisioned Throughput，要么接受默认的波动。

> Artificial Analysis runs continuous benchmarks. On equivalent Llama 3.1 405B deployments (shared on-demand), Azure OpenAI median first-token latency is around 50 ms; Bedrock is around 75 ms. The gap is not an AWS failure — it is a capacity model difference. Azure sells PTUs (Provisioned Throughput Units), which reserve GPU capacity for your tenant. ... On-demand shared capacity competes with every other customer's traffic. Dedicated capacity does not. If your product SLA is TTFT < 100 ms at P99, you either buy PTUs on Azure, buy Bedrock Provisioned Throughput, or accept the default variance.

### Provisioned Throughput economics · 预留吞吐的经济学

Azure PTU：一块预留的推理算力。对可预测的负载，相比按需最多省约 70%。成本按小时固定、与流量无关——闲置时你也在为预留付费。盈亏平衡点通常在 40-60% 的持续利用率附近。

Bedrock Provisioned Throughput：按模型和区域，$21-$50/小时。算法类似——盈亏平衡大约在峰值利用率的一半。需要按月承诺。

Vertex 的预留容量按 Gemini SKU 出售；价格因模型和区域而异，公开宣传较少。

> Azure PTUs: a reserved block of inference compute. Up to ~70% savings vs on-demand for predictable workloads. Costs fixed per hour regardless of traffic — you pay for the reservation even when idle. The break-even is usually around 40-60% sustained utilization.
> Bedrock Provisioned Throughput: $21-$50 per hour depending on model and region. Similar math — break-even is around half peak utilization. Monthly commitment required.

### FinOps surface — the real differentiator · FinOps 界面：真正的差异化

**Bedrock Application Inference Profiles** 是市场上最干净的成本归集。给一个 profile 打上 `team`、`product`、`feature` 标签；把所有模型调用都路由到它；CloudWatch 直接按 profile 拆分成本，无需后处理。2025 年推出，至今仍是超大规模厂商原生的最细粒度方案。

**Vertex** 的归集是每团队一个项目加到处打标签。把每个团队建成一个 GCP 项目，给每个资源贴标签，用 BigQuery Billing Export + DataStudio 做汇总。活更多，但 BigQuery 让你能对成本数据跑任意 SQL。

**Azure** 依赖订阅/资源组 scope 加标签，PTU 预留是一等成本对象。标签从资源组继承而不是来自请求，所以按请求归集需要 Application Insights 自定义指标，或者一个会打 header 的网关。

规律：Bedrock 原生最干净，Vertex 借 BigQuery 最灵活，Azure 不做埋点就最不透明。

> **Bedrock Application Inference Profiles** are the cleanest attribution in the marketplace. Tag a profile with `team`, `product`, `feature`; route all model invocations through it; CloudWatch breaks out cost per profile without post-processing. Added 2025, still the most granular hyperscaler native.
> **Vertex** attribution is project-per-team plus labels-everywhere. ... More work, but BigQuery gives you arbitrary SQL on the cost data.
> **Azure** relies on subscription/resource-group scopes plus tags, with PTU reservations as a first-class cost object. Tags are inherited from resource groups, not requests, so per-request attribution requires Application Insights custom metrics or a gateway that stamps headers.
> The pattern: Bedrock is cleanest native, Vertex is most flexible via BigQuery, Azure is most opaque unless you instrument.

### Lock-in is the 2026 risk · 锁定是 2026 年的风险

单一超大规模厂商承诺在一家模型独大时没问题。2026 年前沿以月为单位移动——上季度 Claude 3.7，下季度 Gemini 2.5，再下季度 GPT-5。锁死一个平台等于把自己挡在三分之二的前沿之外。

能打的团队采用的模式：任何产品关键 LLM 调用至少双供应商。Bedrock 加 Azure OpenAI 是常见组合——Claude 走一家，GPT 走另一家，之间做故障转移，同一个网关。成本上升可忽略，因为网关按最优路由；故障期间的可用性提升（比如 Azure OpenAI 2025 年 1 月事故、AWS us-east-1 故障）是决定性的。

> Single-hyperscaler commitment was fine when one model dominated. In 2026 the frontier moves monthly — Claude 3.7 one quarter, Gemini 2.5 the next, GPT-5 the quarter after. Locking to one platform locks you out of two-thirds of the frontier.
> The pattern working teams adopt: two-provider minimum for any product-critical LLM call. Bedrock plus Azure OpenAI is the common pair — Claude from one, GPT from the other, failover between them, same gateway. Cost uplift is negligible because gateway routes optimal; availability uplift during outages (like the Azure OpenAI January 2025 incident, the AWS us-east-1 outage) is decisive.

### Data residency, BAAs, and regulated industries · 数据驻留、BAA 与受监管行业

Bedrock：多数区域有 BAA；VPC endpoints；guardrails。常见的金融科技默认选择。
Azure OpenAI：HIPAA、SOC 2、ISO 27001；欧盟数据驻留；企业受监管场景的默认选择。
Vertex：HIPAA、GDPR、按区域数据驻留；Google Cloud 的合规栈。

三家都满足基本勾选项。差异在数据保留策略、日志如何处理，以及滥用监控是否读取你的流量（大多数默认开启；企业可 opt-out）。

> Bedrock: BAAs in most regions; VPC endpoints; guardrails. Common fintech default.
> Azure OpenAI: HIPAA, SOC 2, ISO 27001; EU data residency; the enterprise-regulated default.
> Vertex: HIPAA, GDPR, data residency per region; Google Cloud's compliance stack.
> All three meet the basic checkbox. The differences are in data retention policies, how logs are handled, and whether abuse-monitoring reads your traffic (default opt-in on most; opt-out available for enterprise).

### Numbers you should remember · 你该记住的数字

- Azure OpenAI 在 Llama 3.1 405B 同级部署上的中位 TTFT：约 50 ms（使用 PTU）。
- Bedrock 按需中位 TTFT：约 75 ms。
- Bedrock Provisioned Throughput：每单元 $21-$50/小时。
- Azure PTU 盈亏平衡：约 40-60% 持续利用率。
- 高利用率下 PTU 相比按需的节省：最高 70%。

> - Azure OpenAI median TTFT on Llama 3.1 405B equivalents: ~50 ms (with PTUs).
> - Bedrock median TTFT on-demand: ~75 ms.
> - Bedrock Provisioned Throughput: $21-$50/hr per unit.
> - Azure PTU break-even: ~40-60% sustained utilization.
> - PTU savings vs on-demand at high utilization: up to 70%.

```figure
i4-platform-lanes
```

## Use It · 实战用法

`code/main.py` 在一个合成负载上对比三个平台——它建模按需 vs PTU 的经济学、TTFT 方差和成本归集保真度。跑一下，看看 PTU 在哪里划算，市场型的模型广度又在哪里能盖过一个 TTFT 差距。

> `code/main.py` compares the three platforms on a synthetic workload — it models on-demand vs PTU economics, TTFT variance, and cost attribution fidelity. Run it to see where PTUs pay off and where the marketplace's model breadth outweighs a TTFT gap.

## Ship It · 交付

本课产出 `outputs/skill-managed-platform-picker.md`。给定一个负载画像（所需模型、TTFT SLA、日调用量、合规要求），它会推荐一个主平台、一个备选，以及一套 FinOps 埋点方案。

> This lesson produces `outputs/skill-managed-platform-picker.md`. Given a workload profile (models needed, TTFT SLA, daily volume, compliance requirements), it recommends a primary platform, a fallback, and a FinOps instrumentation plan.

## Exercises · 练习

1. 运行 `code/main.py`。对一个 70B 级模型，Azure PTU 在多少持续利用率以上胜过按需？算出盈亏平衡点，再和宣传的 40-60% 区间对比。
2. 你的产品需要 Claude 3.7 Sonnet 和 GPT-4o。设计一个双供应商部署——谁放在哪家超大规模厂商，前面放什么网关，故障转移策略是什么？
3. 一家受监管的医疗客户要求 BAA、美东数据驻留和低于 100 ms 的 P99 TTFT。选一个平台，用三个具体特性说明理由。
4. 你发现本月 Bedrock 账单涨了 4 倍而流量没变。如果没有 Application Inference Profiles，你会怎么找到元凶？有了 profile 又要多久？
5. 阅读 Azure OpenAI 与 Bedrock 的定价页。对一个每月 1 亿 token 的 Claude 负载，哪个更便宜——Anthropic API 直连、Bedrock 按需，还是 Bedrock Provisioned Throughput？

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| Bedrock | "AWS 的 LLM 服务" | 横跨 Claude、Llama、Titan、Mistral、Cohere 的模型市场 |
| Azure OpenAI | "Azure 版的 ChatGPT" | OpenAI 模型独家跑在 Azure 数据中心，附带企业级管控 |
| Vertex AI | "Google 的 LLM" | Gemini 优先的平台，Model Garden 提供第三方模型 |
| PTU | "专用容量" | Provisioned Throughput Unit——预留的推理 GPU，按小时计价 |
| Application Inference Profile | "Bedrock 的标签机制" | 按产品打标签的成本/用量 profile，CloudWatch 原生 |
| Model Garden | "Vertex 的目录" | Vertex AI 的第三方模型区，与 Gemini 分开 |
| Two-provider minimum | "LLM 冗余" | 每条关键 LLM 路径都跑在 ≥2 家超大规模厂商上的策略 |
| BAA | "HIPAA 要签的文件" | Business Associate Agreement；处理 PHI 必需；三家都提供 |
| Abuse monitoring | "盯日志的" | 提供商侧对提示词/输出的安全扫描；企业可 opt-out |

## Further Reading · 延伸阅读

- [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/) —— 权威费率表与 Provisioned Throughput 定价。
- [Azure OpenAI Service Pricing](https://azure.microsoft.com/en-us/pricing/details/azure-openai/) —— PTU 经济学与费率表。
- [Vertex AI Generative AI Pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing) —— Gemini 分层与 Model Garden 附加费。
- [Artificial Analysis LLM Leaderboard](https://artificialanalysis.ai/) —— 跨提供商的持续延迟与吞吐基准。
- [The AI Journal — AWS Bedrock vs Azure OpenAI CTO Guide 2026](https://theaijournal.co/2026/03/aws-bedrock-vs-azure-openai/) —— 企业决策框架。
- [Finout — Bedrock vs Vertex vs Azure FinOps](https://www.finout.io/blog/bedrock-vs.-vertex-vs.-azure-cognitive-a-finops-comparison-for-ai-spend) —— 并排对比各家归集机制。
