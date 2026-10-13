# LLM Routing Layer — LiteLLM, OpenRouter, Portkey · LLM 路由层 —— LiteLLM、OpenRouter、Portkey

> 被单一提供方锁死（lock-in）代价高昂。不同的工具调用工作负载适合不同的模型。路由网关（routing gateway）提供统一的 API 表面、重试、故障转移（failover）、成本追踪和护栏（guardrails）。2026 年有三种主要形态：LiteLLM（开源自托管）、OpenRouter（托管 SaaS）、Portkey（生产级，2026 年 3 月开源）。本课给出决策标准，并带你走一个标准库实现的路由网关。
>
> Provider lock-in is expensive. Different tool-calling workloads suit different models. Routing gateways give one API surface, retries, failover, cost tracking, and guardrails. Three archetypes dominate 2026: LiteLLM (open-source self-hosted), OpenRouter (managed SaaS), Portkey (production-grade, open-sourced in March 2026). This lesson names the decision criteria and walks a stdlib routing gateway.

**Type:** Learn
**Languages:** Python (stdlib, routing + failover + cost tracker)
**Prerequisites:** Phase 13 · 02 (function calling), Phase 13 · 17 (gateways)
**Time:** ~45 minutes

## Learning Objectives · 学习目标

- 区分自托管、托管与生产级三种路由选项
- 实现一条按定义的优先级顺序、在提供方故障时重试的回退链（fallback chain）
- 跨提供方追踪每个请求的成本与 token 用量
- 在给定的生产约束下，在 LiteLLM、OpenRouter 与 Portkey 之间做选择

> Distinguish self-hosted, managed, and production-grade routing options.
> Implement a fallback chain that retries on provider failures in a defined priority order.
> Track per-request cost and token usage across providers.
> Decide between LiteLLM, OpenRouter, and Portkey for a given production constraint.

## The Problem · 问题在哪

提供方路由真正要紧的场景：

1. **成本。** Claude Sonnet 的价格是 Haiku 的 3 倍。分诊类任务用 Haiku 就够了；综合类任务才值得上 Sonnet。按请求路由。

2. **故障转移。** OpenAI 有一个糟糕的小时，每个请求都失败。你想要自动回退到 Anthropic，而不用重新部署。

3. **延迟。** 实时聊天 UI 需要快速的首 token 时间（time-to-first-token）。批量摘要器不在乎。按延迟 SLA 路由。

4. **合规。** 欧盟用户必须留在欧盟区域。按区域路由。

5. **实验。** 在同一工作负载上 A/B 两个模型。按测试桶路由。

在每个集成里手工编码这一切是重复劳动。一个路由网关给你一个 OpenAI 兼容的 API，剩下的它来处理。

> **Cost.** Claude Sonnet costs 3x what Haiku costs. For a triage task, Haiku is enough; for a synthesis task, Sonnet is worth it. Route per-request.
> **Failover.** OpenAI has a bad hour. Every request fails. You want automatic fallback to Anthropic without redeploying.
> **Latency.** A live chat UI needs fast time-to-first-token. A batch summarizer does not. Route by latency SLA.
> **Compliance.** EU users must stay in EU regions. Route by region.
> **Experimentation.** A/B two models on the same workload. Route by test bucket.
> Hand-coding all of this per integration is repetitive. A routing gateway gives one OpenAI-compatible API and handles the rest.

## The Concept · 概念

### OpenAI-compatible proxy shape · OpenAI 兼容代理的形状

人人都在说 OpenAI 形状。路由网关暴露 `/v1/chat/completions`，接受 OpenAI 模式（schema），在内部代理到 Anthropic / Gemini / Cohere / Ollama / 任何东西。客户端不在乎。

> Everyone speaks OpenAI-shape. The routing gateway exposes `/v1/chat/completions`, accepts the OpenAI schema, and internally proxies to Anthropic / Gemini / Cohere / Ollama / anything. The client does not care.

### Model aliases · 模型别名（alias）

你的代码不再钉死一个快照 id，而是写 `our_smart_model`。网关把别名映射到真实模型。当某个提供方发布新一代模型时，你在服务端改一下别名映射；你的代码一行不动。

> Instead of a pinned snapshot id, your code says `our_smart_model`. The gateway maps aliases to real models. When a provider ships a new generation, you change the alias server-side; your code does not touch a thing.

### Fallback chains · 回退链（fallback chain）

```
primary: openai/gpt-4o
on 5xx: anthropic/claude-3-5-sonnet
on 5xx: google/gemini-1.5-pro
on 5xx: refuse
```

网关在一份配置里定义这一切。重试计入一个预算，让回退级联不会把成本炸掉。

> Gateways define this in a config. Retries count against a budget so fallback cascades do not explode cost.

### Semantic caching · 语义缓存（semantic caching）

相同或近似相同的提示词命中缓存，而不是打提供方。在重复的 agent 循环上可以省 30% 到 60%。键基于嵌入（embedding）；近似相同的提示词共享一个缓存槽位。

> Identical-or-near-identical prompts hit a cache instead of the provider. Savings on repeated agent loops can be 30 to 60 percent. Keys are embedding-based; near-identical prompts share a cache slot.

### Guardrails · 护栏（guardrails）

网关层：

- **PII 脱敏。** 在发送提示词前做一次正则或 ML 处理。
- **策略违规。** 拒绝含违禁内容的提示词。
- **输出过滤器。** 清洗补全内容里的泄漏。

Portkey 和 Kong 都内置了有主张的护栏。LiteLLM 把它们留作可选。

> **PII redaction.** Regex or ML-based pass before sending prompts.
> **Policy violations.** Reject prompts with prohibited content.
> **Output filters.** Scrub completions for leaks.
> Portkey and Kong both ship opinionated guardrails. LiteLLM leaves them optional.

### Per-key rate limits · 按密钥的速率限制

一个 API 密钥 = 一个团队。按密钥的预算防止一个团队吃光共享配额。大多数网关都支持。

> One API key = one team. Per-key budgets prevent one team from consuming the shared quota. Most gateways support this.

### Self-hosted vs managed trade-offs · 自托管与托管的取舍

| 因素 | LiteLLM（自托管） | OpenRouter（托管） | Portkey（生产级） |
|--------|----------------------|----------------------|----------------------|
| 代码 | 开源，Python | 托管 SaaS | 开源（2026 年 3 月）+ 托管 |
| 搭建 | 部署一个代理 | 注册即用 | 两者皆可 |
| 提供方 | 100+ | 300+ | 100+ |
| 计费 | 你自己的密钥 | OpenRouter 点数 | 你自己的密钥 |
| 可观测性 | OpenTelemetry | 仪表盘 | 全套 OTel + PII 脱敏 |
| 最适合 | 想要完全控制的团队 | 快速原型 | 有合规要求的生产 |

当你有 SRE 团队并且想要数据主权时，LiteLLM 赢。当你想要一份订阅、零基础设施时，OpenRouter 赢。当你需要开箱即用的护栏与合规时，Portkey 赢。

> LiteLLM wins when you have an SRE team and want data sovereignty. OpenRouter wins when you want a single subscription and no infra. Portkey wins when you need guardrails and compliance out of the box.

### Cost tracking · 成本追踪

每个请求携带 `provider`、`model`、`input_tokens`、`output_tokens`。乘以每模型每 token 的价格（从网关维护的一份价目表里取）。再按用户 / 团队 / 项目聚合。

> Every request carries `provider`, `model`, `input_tokens`, `output_tokens`. Multiply by per-model per-token prices (pulled from a pricing sheet the gateway maintains). Per-user / per-team / per-project aggregation.

### MCP plus routing · MCP 加路由

一个网关可以同时路由 LLM 调用和 MCP 采样（sampling）请求。当采样请求的 modelPreferences 偏好某个具体模型时，网关把它翻译到正确的后端。Phase 13 · 17（MCP 网关）与本课的路由网关有时就在这里合并成一个服务。

> A gateway can route both LLM calls AND MCP sampling requests. When a sampling request's modelPreferences prefer a specific model, the gateway translates to the right backend. This is where Phase 13 · 17 (MCP gateway) and this lesson's routing gateway sometimes merge into one service.

### Routing strategies · 路由策略

- **静态优先级。** 取列表第一个；出错就回退。
- **负载均衡。** 轮询（round-robin）或加权。
- **成本感知。** 挑满足延迟 / 质量要求的最便宜模型。
- **延迟感知。** 挑最近 N 分钟里最快的模型。
- **任务感知。** 提示词分类器把编码类路由给一个模型，摘要类路由给另一个。

> **Static priority.** First in list; fall back on error.
> **Load balancing.** Round-robin or weighted.
> **Cost-aware.** Pick the cheapest model meeting latency / quality.
> **Latency-aware.** Pick the fastest model in the last N minutes.
> **Task-aware.** Prompt classifier routes coding to one model, summarization to another.

```figure
tp-router-failover
```

## Use It · 实战用法

`code/main.py` 用约 150 行实现了一个路由网关：接受 OpenAI 形状的请求，翻译到各提供方的 stub，运行一条优先级回退链，追踪每请求成本，并对输入做一次 PII 脱敏。它跑三个场景：普通请求、主提供方宕机触发回退、PII 泄漏被脱敏拦截。

值得看的地方：

- `ROUTES` 字典：别名 → 按优先级排序的具体提供方列表。
- 回退循环在 5xx 时重试。
- 成本追踪器把 token 用量乘以每模型费率。
- PII 脱敏器在转发前清洗掉 SSN 形状的模式。

> `code/main.py` implements a routing gateway in ~150 lines: accepts OpenAI-shaped requests, translates to per-provider stubs, runs a priority fallback chain, tracks per-request cost, and applies a PII redaction pass on inputs. Run it with three scenarios: normal request, primary-provider outage triggering fallback, PII leakage caught by redaction.
> `ROUTES` dict: alias -> priority-ordered list of concrete providers.
> Fallback loop retries on 5xx.
> Cost tracker multiplies token usage by per-model rates.
> PII redactor scrubs SSN-shaped patterns before forwarding.

## Ship It · 交付

本课产出 `outputs/skill-routing-config-designer.md`。给定一个工作负载画像（延迟、成本、合规），该技能挑选 LiteLLM / OpenRouter / Portkey，并产出一份路由配置。

> This lesson produces `outputs/skill-routing-config-designer.md`. Given a workload profile (latency, cost, compliance), the skill picks LiteLLM / OpenRouter / Portkey and produces a routing config.

## Exercises · 练习

1. 运行 `code/main.py`。触发宕机场景；确认回退落在第二个提供方上，且成本归属正确。
2. 添加语义缓存：提示词的 SHA256 作查找键；命中缓存立即返回。测量一次重复调用的成本节省。
3. 添加一个提示词分类器，把「code ...」提示词路由到一个偏智能的别名，把「summarize ...」提示词路由到一个偏速度的别名。
4. 设计按团队的预算：每个团队有一个月度消费上限；一旦触顶，网关拒绝请求。选择一个执行粒度（按请求或按时间窗口）。
5. 并排阅读 LiteLLM、OpenRouter 和 Portkey 的文档。说出每家独有、而另外两家没有的那一个特性。

> 1. Run `code/main.py`. Trigger the outage scenario; confirm fallback lands on the second provider and cost is attributed correctly.
> 2. Add semantic caching: SHA256 of the prompt is a lookup key; cache hits return instantly. Measure cost savings on a repeated call.
> 3. Add a prompt classifier that routes "code ..." prompts to an alias favoring intelligence and "summarize ..." prompts to an alias favoring speed.
> 4. Design per-team budgets: each team has a monthly spend cap; gateway refuses requests once cap is hit. Pick an enforcement granularity (per-request or windowed).
> 5. Read LiteLLM, OpenRouter, and Portkey docs side by side. Name the one feature each ships that the other two do not.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| 路由网关（Routing gateway） | 「LLM 代理」 | 站在众多提供方之前的单一 API 表面层 |
| OpenAI 兼容（OpenAI-compatible） | 「说 OpenAI 模式」 | 接受 `/v1/chat/completions` 形状，翻译到任何后端 |
| 模型别名（Model alias） | 「our_smart_model」 | 你代码里的名字，由网关映射到具体模型 |
| 回退链（Fallback chain） | 「重试列表」 | 失败时按序尝试的提供方列表 |
| 语义缓存（Semantic caching） | 「提示词嵌入缓存」 | 键是提示词的嵌入；近似重复共享一次缓存命中 |
| 护栏（Guardrails） | 「输入/输出过滤器」 | 脱敏 PII，拒绝策略违规 |
| 按密钥限速（Per-key rate limit） | 「团队预算」 | 以 API 密钥为作用域的配额 |
| 成本追踪（Cost tracking） | 「每请求开销」 | token 用量聚合 × 每模型价格 |
| LiteLLM | 「开源代理」 | 可自托管的开源路由网关 |
| OpenRouter | 「托管 SaaS」 | 按点数计费的托管网关 |
| Portkey | 「生产级选项」 | 开源 + 托管，内置护栏 |

> | Term | What people say | What it actually means |
> | Routing gateway | "LLM proxy" | One-API-surface layer in front of many providers |
> | OpenAI-compatible | "Speaks the OpenAI schema" | Accepts `/v1/chat/completions` shape, translates to any backend |
> | Model alias | "our_smart_model" | Name in your code that the gateway maps to a concrete model |
> | Fallback chain | "Retry list" | Ordered list of providers attempted on failure |
> | Semantic caching | "Prompt-embedding cache" | Key is embedding of the prompt; near-duplicates share a cache hit |
> | Guardrails | "Input/output filters" | Redact PII, reject policy violations |
> | Per-key rate limit | "Team budget" | Quota scoped to an API key |
> | Cost tracking | "Per-request spend" | Aggregate token usage x price per model |
> | LiteLLM | "The open proxy" | Self-hostable OSS routing gateway |
> | OpenRouter | "The managed SaaS" | Hosted gateway with credit-based billing |
> | Portkey | "The production option" | Open-source + managed with guardrails built in |

## Further Reading · 延伸阅读

- [LiteLLM — docs](https://docs.litellm.ai/) —— 自托管路由网关
- [OpenRouter — quickstart](https://openrouter.ai/docs/quickstart) —— 托管路由 SaaS
- [Portkey — docs](https://portkey.ai/docs) —— 带护栏的生产级路由
- [TrueFoundry — LiteLLM vs OpenRouter](https://www.truefoundry.com/blog/litellm-vs-openrouter) —— 决策指南
- [Relayplane — LLM gateway comparison 2026](https://relayplane.com/blog/llm-gateway-comparison-2026) —— 厂商调研
