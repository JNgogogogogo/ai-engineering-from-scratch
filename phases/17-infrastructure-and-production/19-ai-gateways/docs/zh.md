# AI Gateways — LiteLLM, Portkey, Kong AI Gateway, Bifrost · AI 网关 —— LiteLLM、Portkey、Kong AI Gateway、Bifrost

> 网关（gateway）位于你的应用和模型厂商之间。核心特性是厂商路由、fallback、重试、限流、密钥引用、可观测性、护栏（guardrails）。2026 年的市场格局：**LiteLLM** 是 MIT 开源、支持 100+ 厂商、OpenAI 兼容，但在约 2000 RPS 附近开始崩（8 GB 内存，公开基准中出现级联失败）；最适合 Python、<500 RPS、开发/原型。**Portkey** 定位控制面（护栏、PII 脱敏、越狱检测、审计轨迹），2026 年 3 月转为 Apache 2.0 开源，延迟开销 20-40 ms，生产档 $49/月。**Kong AI Gateway** 构建在 Kong Gateway 之上——Kong 自己的基准（同等 12 CPU）里：比 Portkey 快 228%，比 LiteLLM 快 859%；定价 $100/模型/月（Plus 档最多 5 个）；如果你已经在用 Kong，它很适合企业。**Bifrost**（Maxim AI）——自动重试、退避可配置，OpenAI 429 时回退 Anthropic。**Cloudflare / Vercel AI Gateway**——托管、零运维、基础重试。数据驻留要求决定自托管与否；Portkey 和 Kong 居中，提供开源 + 可选托管。

> A gateway sits between your apps and model providers. Core features are provider routing, fallback, retries, rate limiting, secret references, observability, guardrails. Market split in 2026: **LiteLLM** is MIT OSS with 100+ providers, OpenAI-compatible, but breaks down around ~2000 RPS (8 GB memory, cascading failures in published benchmarks); best for Python, <500 RPS, dev/prototyping. **Portkey** is control-plane-positioned (guardrails, PII redaction, jailbreak detection, audit trails), went Apache 2.0 open-source March 2026, 20-40 ms latency overhead, $49/mo production tier. **Kong AI Gateway** built on Kong Gateway — Kong's own benchmark on same 12 CPUs: 228% faster than Portkey, 859% faster than LiteLLM; $100/model/month pricing (max 5 on Plus tier); enterprise-fit if you're already on Kong. **Bifrost** (Maxim AI) — automatic retries with configurable backoff, fallback to Anthropic on OpenAI 429. **Cloudflare / Vercel AI Gateways** — managed, zero-ops, basic retry. Data residency drives the self-host decision; Portkey and Kong sit in the middle with OSS + optional managed.

**Type:** Learn
**Languages:** Python (stdlib, toy gateway-routing simulator)
**Prerequisites:** Phase 17 · 01 (Managed LLM Platforms), Phase 17 · 16 (Model Routing)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 列出网关的核心特性（路由、fallback、重试、限流、密钥、可观测性、护栏）。
- 把四个 2026 年的网关（LiteLLM、Portkey、Kong AI、Bifrost）映射到规模上限和使用场景。
- 引用 Kong 的基准（比 Portkey 快 228%、比 LiteLLM 快 859%），并解释它为什么对 >500 RPS 重要。
- 在数据驻留和运维预算给定的情况下，在自托管与托管之间做选择。

> Enumerate the six core gateway features (routing, fallback, retries, rate limits, secrets, observability, guardrails).
> Map four 2026 gateways (LiteLLM, Portkey, Kong AI, Bifrost) to scale ceilings and use cases.
> Cite the Kong benchmark (228% vs Portkey, 859% vs LiteLLM) and explain why it matters for >500 RPS.
> Choose self-hosted vs managed given data residency and ops budget.

## The Problem · 问题在哪

你的产品调用 OpenAI、Anthropic 和一个自托管的 Llama。每家厂商有不同的 SDK、错误模型、限流和鉴权方式。你想要故障转移（OpenAI 返回 429 时试 Anthropic）、单一凭证库、统一可观测性，以及按租户限流。

在应用层重复造这些轮子，会把每个服务和每家厂商耦合在一起。网关层把它收敛成一个进程、一个 API（通常是 OpenAI 兼容的），再向各厂商扇出。

> Your product calls OpenAI, Anthropic, and a self-hosted Llama. Each provider has a different SDK, error model, rate limit, and auth scheme. You want failover (if OpenAI 429s, try Anthropic), a single credential store, unified observability, and rate limits per tenant.
> Reinventing this at the app layer couples every service to every provider. A gateway layer consolidates it into one process with one API (typically OpenAI-compatible) that fans out to providers.

## The Concept · 概念

### Six core features · 六大核心特性

1. **厂商路由（Provider routing）** —— OpenAI、Anthropic、Gemini、自托管等，都在同一个 API 后面。
2. **Fallback（故障转移）** —— 遇到 429、5xx 或质量失败，换别处重试。
3. **重试（Retries）** —— 指数退避，次数有界。
4. **限流（Rate limits）** —— 按租户、按 key、按模型。
5. **密钥引用（Secret references）** —— 运行时从 vault 取凭证（绝不下发到应用）。
6. **可观测性（Observability）** —— OTel + GenAI 属性（Phase 17 · 13）+ 成本归因。
7. **护栏（Guardrails）** —— PII 脱敏、越狱检测、允许主题过滤。

> 1. **Provider routing** — OpenAI, Anthropic, Gemini, self-hosted, etc. behind one API.
> 2. **Fallback** — on 429, 5xx, or quality failure, retry elsewhere.
> 3. **Retries** — exponential backoff, bounded attempts.
> 4. **Rate limits** — per-tenant, per-key, per-model.
> 5. **Secret references** — pull credentials from vault at runtime (never in app).
> 6. **Observability** — OTel + GenAI attributes (Phase 17 · 13) + cost attribution.
> 7. **Guardrails** — PII redaction, jailbreak detection, allowed-topics filters.

### LiteLLM — MIT OSS, Python · LiteLLM —— MIT 开源，Python

- 100+ 厂商，OpenAI 兼容，router 配置，fallback，基础可观测性。
- 在 Kong 的基准里 2000 RPS 左右崩掉；内存占用 8 GB，持续负载下出现级联失败。
- 最适合：Python 应用、<500 RPS、开发/预发网关、试验性路由。
- 成本：开源 $0；有云免费档。

> 100+ providers, OpenAI-compatible, router config, fallback, basic observability.
> Breaks down around 2000 RPS in Kong's benchmark; 8 GB memory footprint, cascading failures under sustained load.
> Best fit: Python app, <500 RPS, dev/staging gateways, experimental routing.
> Cost: $0 for OSS; cloud free tier exists.

### Portkey — control plane positioning · Portkey —— 控制面定位

- 2026 年 3 月起 Apache 2.0 开源。护栏、PII 脱敏、越狱检测、审计轨迹。
- 每请求延迟开销 20-40 ms。
- 生产档 $49/月，含保留期 + SLA。
- 最适合：需要护栏 + 可观测性打包的受监管行业。

> Apache 2.0 OSS as of March 2026. Guardrails, PII redaction, jailbreak detection, audit trails.
> 20-40 ms per-request latency overhead.
> $49/mo for production tier with retention + SLA.
> Best fit: regulated industries needing guardrails + observability bundled.

### Kong AI Gateway — the scale play · Kong AI Gateway —— 规模打法

- 构建在 Kong Gateway 之上（成熟的 API 网关产品，lua+OpenResty）。
- Kong 自己的基准（同等 12 CPU）：比 Portkey 快 228%，比 LiteLLM 快 859%。
- 定价：$100/模型/月，Plus 档最多 5 个。
- 最适合：已经在用 Kong；>1000 RPS；愿意付费授权。

> Built on Kong Gateway (mature API gateway product, lua+OpenResty).
> Kong's own benchmark on 12-CPU equivalent: 228% faster than Portkey, 859% faster than LiteLLM.
> Pricing: $100/model/month, max 5 on Plus tier.
> Best fit: already on Kong; >1000 RPS; willing to license.

### Bifrost (Maxim AI) · Bifrost（Maxim AI）

- 自动重试，退避可配置。
- OpenAI 429 时回退 Anthropic 是经典配方。
- 较新的进入者；商业产品。

> Automatic retries with configurable backoff.
> Fallback to Anthropic on OpenAI 429 is a canonical recipe.
> Newer entrant; commercial.

### Cloudflare AI Gateway / Vercel AI Gateway · 托管边缘网关

- 托管、零运维。基础重试和可观测性。
- 最适合：跑在 Cloudflare/Vercel 上的边缘 JavaScript 应用。
- 在护栏和限流上比 Kong/Portkey 有限。

> Managed, zero-ops. Basic retry and observability.
> Best fit: Edge-serving JavaScript apps on Cloudflare/Vercel.
> Limited compared to Kong/Portkey on guardrails and rate limits.

### Self-hosted vs managed · 自托管 vs 托管

数据驻留是决定性因素。医疗和金融默认自托管（LiteLLM 或 Portkey OSS 或 Kong）。消费级产品默认托管（Cloudflare AI Gateway）或中间档（Portkey 托管）。混合模式：受监管的租户自托管，其余托管。

> Data residency is the forcing function. Healthcare and finance default self-host (LiteLLM or Portkey OSS or Kong). Consumer products default managed (Cloudflare AI Gateway) or middle-tier (Portkey managed). Hybrid: self-hosted for regulated tenant, managed for others.

### Latency budget · 延迟预算

- LiteLLM：典型开销 5-15 ms。
- Portkey：开销 20-40 ms。
- Kong：开销 3-8 ms。
- Cloudflare/Vercel：开销 1-3 ms（边缘优势）。

网关延迟直接加到 TTFT 上。TTFT P99 < 100 ms 的 SLA 选 Kong 或 Cloudflare。P99 < 500 ms 用哪家都行。

> LiteLLM: 5-15 ms overhead typical. Portkey: 20-40 ms overhead. Kong: 3-8 ms overhead. Cloudflare/Vercel: 1-3 ms overhead (edge advantage).
> Gateway latency directly adds to TTFT. For TTFT P99 < 100 ms SLA, Kong or Cloudflare. For P99 < 500 ms, any.

### Rate-limit semantics matter · 限流语义很重要

简单的令牌桶（token-bucket）撑到中等规模没问题。多租户需要滑动窗口（sliding-window）+ 突发余量 + 按租户分层。LiteLLM 用令牌桶；Kong 用滑动窗口；Portkey 用分层。

> Simple token-bucket works up to moderate scale. Multi-tenant requires sliding-window + burst allowance + per-tenant tiering. LiteLLM ships token-bucket; Kong ships sliding-window; Portkey ships tiered.

### Gateway + observability + routing compose · 网关 + 可观测性 + 路由的组合

Phase 17 · 13（可观测性）+ 16（模型路由）+ 19（网关）在生产里是同一层。选一个覆盖三者的工具，或者仔细接线：2026 年的大多数部署把 Helicone（可观测性）或 Portkey（护栏）与 Kong（规模）组合分工。

> Phase 17 · 13 (observability) + 16 (model routing) + 19 (gateways) are the same layer in production. Pick one tool that covers all three or wire them carefully: most 2026 deployments combine Helicone (observability) or Portkey (guardrails) with Kong (scale) for split roles.

### Numbers you should remember · 你该记住的数字

- LiteLLM：约 2000 RPS 崩掉，8 GB 内存。
- Portkey：20-40 ms 开销；2026 年 3 月起 Apache 2.0。
- Kong：比 Portkey 快 228%，比 LiteLLM 快 859%。
- Kong 定价：$100/模型/月，Plus 档最多 5 个。
- Cloudflare/Vercel：边缘开销 1-3 ms。

```figure
mx-gateway-fallback
```

> LiteLLM: breaks at ~2000 RPS, 8 GB memory. Portkey: 20-40 ms overhead; Apache 2.0 since March 2026. Kong: 228% faster than Portkey, 859% faster than LiteLLM. Kong pricing: $100/model/month, 5 max on Plus tier. Cloudflare/Vercel: 1-3 ms overhead at the edge.

## Use It · 实战用法

`code/main.py` 模拟在 429/5xx 注入下跨 3 家厂商的网关路由与 fallback。报告延迟、重试率和 fallback 命中率。

> `code/main.py` simulates gateway routing with fallback across 3 providers under 429/5xx injection. Reports latency, retry rate, and fallback hit rate.

## Ship It · 交付

本课产出 `outputs/skill-gateway-picker.md`。给定规模、运维姿态、合规要求和延迟预算，它挑选网关。

> This lesson produces `outputs/skill-gateway-picker.md`. Given scale, ops posture, compliance, latency budget, picks a gateway.

## Exercises · 练习

1. 跑 `code/main.py`。配置 OpenAI→Anthropic→自托管的 fallback。厂商错误率 5% 时期望命中率是多少？
2. 你的 SLA 是 300 ms 基线下 TTFT P99 < 200 ms。哪些网关在预算之内？
3. 一位医疗客户要求自托管 + PII 脱敏 + 审计。在 Portkey OSS 和 Kong 之间选一个。
4. 比较 LiteLLM 与 Kong：RPS 到多少时团队应该迁移？
5. 为一个多租户 SaaS 设计限流策略：免费档、试用档、付费档。令牌桶还是滑动窗口？

> 1. Run `code/main.py`. Configure fallback from OpenAI→Anthropic→self-hosted. What's the expected hit rate at 5% provider error rate? ... 3. A healthcare customer requires self-hosted + PII redaction + audit. Pick Portkey OSS or Kong. ... 5. Design a rate-limit policy for a multi-tenant SaaS: free tier, trial tier, paid tier. Token-bucket or sliding-window?

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|------------|----------|
| Gateway | 「API 中介」 | 位于应用与厂商之间的进程 |
| LiteLLM | 「MIT 那个」 | Python 开源，100+ 厂商，2K RPS 崩 |
| Portkey | 「护栏网关」 | 控制面 + 可观测性，Apache 2.0 |
| Kong AI Gateway | 「规模那个」 | 构建在 Kong Gateway 上，基准领先 |
| Bifrost | 「Maxim 的网关」 | 重试 + Anthropic 回退配方 |
| Cloudflare AI Gateway | 「边缘托管」 | 边缘部署的托管网关，零运维 |
| PII redaction | 「数据清洗」 | 发给模型之前用正则 + NER 打码 |
| Jailbreak detection | 「提示注入防护」 | 对用户输入跑分类器 |
| Audit trail | 「合规日志」 | 每次 LLM 调用的不可变记录 |
| Token-bucket | 「简单限流」 | 基于补充的限流器 |
| Sliding-window | 「精确限流」 | 时间窗限流器；公平性更好 |

## Further Reading · 延伸阅读

- [Kong AI Gateway Benchmark](https://konghq.com/blog/engineering/ai-gateway-benchmark-kong-ai-gateway-portkey-litellm)
- [TrueFoundry — AI Gateways 2026 Comparison](https://www.truefoundry.com/blog/a-definitive-guide-to-ai-gateways-in-2026-competitive-landscape-comparison)
- [Techsy — Top LLM Gateway Tools 2026](https://techsy.io/en/blog/best-llm-gateway-tools)
- [LiteLLM GitHub](https://github.com/BerriAI/litellm)
- [Portkey GitHub](https://github.com/Portkey-AI/gateway)
- [Kong AI Gateway docs](https://docs.konghq.com/gateway/latest/ai-gateway/)
