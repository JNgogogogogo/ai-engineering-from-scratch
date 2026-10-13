# Prompt Caching and Semantic Caching Economics · 提示词缓存与语义缓存的经济学

> **价格快照，数据截至 2026-04。** 下文中的数字性论断反映本课发布时抓取的厂商价目表；在向下游引用之前，请对照链接文档核实。

缓存发生在两层。L2（厂商级）的 prompt/prefix 缓存为重复前缀复用注意力 KV——Anthropic 的 prompt-caching 文档宣称长提示上最多可降 90% 成本、降 85% 延迟；对 Claude 3.5 Sonnet，缓存读为 $0.30/M，而新鲜输入为 $3.00/M，默认 5 分钟 TTL，1 小时 TTL 选项需付 2 倍写入溢价（docs.anthropic.com，2026-04）。OpenAI prompt caching 对 ≥1024 token 的提示自动生效，缓存输入价格相比新鲜输入约有 90% 的折扣（platform.openai.com，2026-04）；确切的每模型缓存费率以在线价目表为准。L1（应用级）语义缓存在嵌入相似度命中时完全跳过 LLM。厂商宣称的「95% 准确率」指的是匹配正确性，不是命中率——生产环境报告的命中率从 10%（开放式聊天）到 70%（结构化 FAQ）不等；两家厂商都不公布官方基线，所以应把这些数字当社区遥测数据，而不是保证。生产中的坑：并行化会杀死缓存（第一批缓存写完成前并发发出的 N 个请求能把开销放大数倍），前缀中的动态内容会彻底阻止缓存命中。ProjectDiscovery 报告，通过把动态文本移出可缓存前缀，命中率从 7% 提升到 74%（2025-11）。

> **Pricing snapshot dated 2026-04.** Numeric claims below reflect vendor rate cards captured at this lesson's publication; verify against the linked docs before quoting them downstream.
>
> Caching happens at two layers. L2 (provider-level) prompt/prefix caching reuses attention KV for repeated prefixes — Anthropic's prompt-caching docs advertise up to 90% cost reduction and 85% latency reduction on long prompts; for Claude 3.5 Sonnet cache reads are $0.30/M vs $3.00/M fresh with a 5-minute TTL and a 2x write premium for the 1-hour TTL option (docs.anthropic.com, 2026-04). OpenAI prompt caching applies automatically for prompts ≥1024 tokens and prices cached input at roughly a 90% discount vs fresh (platform.openai.com, 2026-04); the exact per-model cached rate depends on the live rate card. L1 (app-level) semantic caching skips the LLM entirely on embedding similarity hits. Vendor "95% accuracy" refers to match correctness, not hit rate — reported production hit rates range from 10% (open-ended chat) up to 70% (structured FAQ); neither provider publishes an official baseline, so treat these as community telemetry rather than guarantees. The production pitfalls: parallelization kills caching (N parallel requests issued before the first cache write can inflate spend several-fold), and dynamic content inside the prefix prevents cache hits entirely. ProjectDiscovery reported moving from 7% to 74% hit rate (2025-11) by moving dynamic text out of the cacheable prefix.

**Type:** Learn
**Languages:** Python（仅标准库；玩具级双层缓存模拟器）
**Prerequisites:** Phase 17 · 04（Serving Engine Internals）、Phase 17 · 06（SGLang RadixAttention）
**Time:** ~60 分钟

## Learning Objectives · 学习目标

- 区分 L2 prompt/prefix 缓存（厂商侧复用 KV）与 L1 语义缓存（相似提示直接绕过 LLM）。
- 解释 Anthropic 的 `cache_control` 显式标记，以及两种 TTL 选项（5 分钟 vs 1 小时）各自的价格乘数。
- 给定命中率、提示/响应构成和 token 价格，计算预期的月度节省。
- 说出会把账单放大 5-10 倍的并行化反模式，以及会让命中率崩塌的动态内容反模式。

> Distinguish L2 prompt/prefix caching (KV reuse at provider) from L1 semantic caching (LLM bypass on similar prompts).
> Explain Anthropic's `cache_control` explicit marking and the two TTL options (5-min vs 1-hour) with their price multipliers.
> Compute expected monthly savings given hit rate, prompt/response mix, and token prices.
> Name the parallelization anti-pattern that inflates bills by 5-10x and the dynamic-content anti-pattern that collapses hit rate.

## The Problem · 问题在哪

你给 RAG 服务加了 prompt caching。账单纹丝不动。你测了命中率：7%。你的提示看起来是静态的，其实不是——系统提示里包含格式精确到分钟、一个请求 ID，还有为了多样性而随机重排的示例。每个请求都在写一条新缓存，读取为零。

另外，你的 agent 对每个用户问题并行发十个工具调用。十个全部在第一次缓存写完成之前到达厂商。十次写、零次读。你的账单是「加了缓存后本该花的钱」的 5-10 倍。

缓存是一套协议，不是一个开关。两层，两种不同的失败模式。

> You add prompt caching to your RAG service. The bill stays flat. You measure the hit rate; it is 7%. Your prompts look static but they are not — the system prompt includes the current date formatted to the minute, a request ID, and a randomized example reorder for diversity. Every request writes a new cache entry, reads zero.
> Separately, your agent runs ten parallel tool calls per user question. All ten arrive at the provider before the first cache write completes. Ten writes, zero reads. Your bill is 5-10x what "with caching" was supposed to cost.
> Caching is a protocol, not a flag. Two layers, two different failure modes.

## The Concept · 概念

### L2 — provider prompt/prefix caching · L2——厂商 prompt/prefix 缓存

厂商为可缓存前缀存储注意力 KV，在下一个匹配该前缀的请求上复用。写成本只付一次，读取几乎免费。

**Anthropic（Claude 3.5 / 3.7 / 4 系列）**：请求里的显式 `cache_control` 标记。由你指定哪些块可缓存。TTL：5 分钟（写入为基础价的 1.25 倍）或 1 小时（写入为基础价的 2 倍）。缓存读：Claude 3.5 Sonnet 上 $0.30/M，而新鲜输入 $3.00/M——便宜 10 倍（docs.anthropic.com，截至 2026-04）。各模型费率不同（Opus/Haiku 单独公布）；永远对照在线定价页复核。

**OpenAI**：对 ≥1024 token 的提示自动缓存（platform.openai.com，2026-04）。没有显式开关。按当前 gpt-4o/gpt-5 价目表，缓存输入比新鲜输入便宜约 10 倍。文档和发布说明都不公布官方命中率基线；社区报告在精心设计提示的前提下集中在 30-60%。监控 `usage.cached_tokens` 来测量你自己的命中率。

**Google（Gemini）**：经显式 API 做上下文缓存；1M token 的上下文意味着缓存回报更大。

**自托管（vLLM、SGLang）**：Phase 17 · 06 讲的 RadixAttention——同样的模式，跑在你自己的算力上。

> Provider stores the attention KV for a cacheable prefix and reuses it on the next request that matches the prefix. You pay a write cost once, reads nearly free.
> **Anthropic (Claude 3.5 / 3.7 / 4 series)**: explicit `cache_control` marker in the request. You tag which blocks are cacheable. TTL: 5-minute (write costs 1.25x base) or 1-hour (write costs 2x base). Cache reads: $0.30/M on Claude 3.5 Sonnet vs $3.00/M fresh — 10x cheaper (docs.anthropic.com, as of 2026-04). Rates differ per model (Opus/Haiku published separately); always cross-check the live pricing page.
> **OpenAI**: automatic caching for prompts ≥1024 tokens (platform.openai.com, 2026-04). No explicit flag. Cached input is roughly 10x cheaper than fresh on current gpt-4o/gpt-5 rate cards. Neither docs nor release notes publish an official hit-rate baseline; community reports cluster around 30–60% with careful prompt design. Monitor `usage.cached_tokens` to measure your own.
> **Google (Gemini)**: context caching via explicit API; 1M-token context means caching pays even more.
> **Self-hosted (vLLM, SGLang)**: Phase 17 · 06 covers RadixAttention — same pattern at your own compute.

### L1 — app-level semantic caching · L1——应用级语义缓存

在调用 LLM 之前，先对提示做哈希、算嵌入，然后查找相似的已缓存请求（余弦相似度超过阈值，通常 0.95 以上）。命中就返回缓存响应；未命中就调 LLM 并把结果存入缓存。

开源方案：Redis Vector Similarity、GPTCache、Qdrant。商业方案：Portkey Cache、Helicone Cache。

厂商的准确率宣称指的是「返回的缓存响应在语义上有多合适」——不是你命中得多频繁。生产命中率：

- 开放式聊天：10-15%。
- 结构化 FAQ / 客服：40-70%。
- 代码问题：20-30%（小变体杀死命中）。
- 重复提示的语音 agent：50-80%（语音归一化后的固定集合）。

> Before calling the LLM at all, hash the prompt, embed it, and look for a similar cached request (cosine similarity above threshold, typically 0.95+). On hit, return the cached response. On miss, call LLM and cache the result.
> Open-source: Redis Vector Similarity, GPTCache, Qdrant. Commercial: Portkey Cache, Helicone Cache.
> Vendor accuracy claims refer to how often the returned cached response was semantically appropriate — not how often you hit. Production hit rates:
> - Open-ended chat: 10-15%.
> - Structured FAQ / support: 40-70%.
> - Code questions: 20-30% (small variants kill hits).
> - Voice agents repeating prompts: 50-80% (voice normalization fixed set).

### The parallelization anti-pattern · 并行化反模式

你的 agent 并行发 10 个工具调用。10 个都带同一个 4K token 的系统提示。Anthropic 的缓存写是按请求计的；厂商看到提示后约 300 ms，第一次缓存写才完成。请求 2-10 在同一毫秒窗口到达，各自看到缓存未命中。你付 10 份写入溢价，拿 0 份读取折扣。

修复：按「串行先行」的方式分批——先单独发请求 1，等它的缓存落好再发 2-10。给第一个工具调用增加 300 ms；省下 5-10 倍账单。

> Your agent makes 10 tool calls in parallel. All 10 have the same 4K-token system prompt. Anthropic cache writes are per-request; the first cache-write completes around 300 ms after the provider sees the prompt. Requests 2-10 arrive in the same millisecond window and each sees cache miss. You pay 10 write premiums, 0 read discounts.
> Fix: batch with sequential-first — make request 1 alone, then fire 2-10 once 1's cache has populated. Adds 300 ms to the first tool call; saves 5-10x the bill.

### The dynamic content anti-pattern · 动态内容反模式

你的系统提示长这样：

```
You are a helpful assistant. The current time is 14:32:17.
User ID: abc123. Today is Tuesday...
```

每个请求都是唯一的。每个请求都在写。命中为零。

修复：把真正静态的内容全部移进可缓存前缀；把动态内容追加到缓存边界之后：

```
[cacheable]
You are a helpful assistant. [rules, examples, instructions]
[/cacheable]
[dynamic, not cached]
Current time: 14:32:17. User: abc123.
```

ProjectDiscovery 就是这样把缓存命中率从 7% 提到 74% 的，并公布了问题解剖。

> Your system prompt looks like:
> Every request is unique. Every request writes. Zero hits.
> Fix: move everything truly static to the cacheable prefix; append dynamic content after the cache boundary:
> ProjectDiscovery moved from 7% to 74% cache hit rate this way and published the anatomy.

### Stack batch + cache for overnight workloads · 过夜负载：批量 + 缓存叠加

Batch API（Phase 17 · 15）以 24 小时周转换 5 折优惠。叠加缓存输入再赚约 10 倍。过夜分类、标注和报告生成类工作负载，通过叠加可以把成本压到同步未缓存方案的约 10%。

> Batch APIs (Phase 17 · 15) give 50% discount at 24-hour turnaround. Cached input on top gets you ~10x on top of that. Overnight classification, labeling, and report generation workloads can drop to ~10% of synchronous-uncached cost by stacking.

### Numbers you should remember · 该记住的数字

价格点为 2026-04 从链接的厂商文档抓取，每隔几个月就会漂移——依赖之前请复核。

- Anthropic 缓存读：Claude 3.5 Sonnet 上 $0.30/M，比新鲜输入便宜约 10 倍（docs.anthropic.com）。
- Anthropic 缓存写溢价：1.25 倍（5 分钟 TTL）或 2 倍（1 小时 TTL）。
- OpenAI 自动缓存：适用于 ≥1024 token 的提示；按当前价目表，缓存输入定价约为新鲜输入的 10%（platform.openai.com）。
- 语义缓存命中率（社区报告）：开放式聊天约 10%；结构化 FAQ 最高约 70%。并非厂商文档化的基线。
- ProjectDiscovery：把动态内容移出前缀后命中率 7% → 74%（项目博客，2025-11）。
- 并行化反模式：N 个并行请求错过第一次缓存写时，常见报告为账单膨胀 5-10 倍。

```figure
semantic-cache-hit
```

> Pricing points are captured 2026-04 from the linked vendor docs and drift every few months — re-check before relying on them.
> - Anthropic cached read: $0.30/M on Claude 3.5 Sonnet, roughly 10x cheaper than fresh input (docs.anthropic.com).
> - Anthropic cache write premium: 1.25x (5-min TTL) or 2x (1-hour TTL).
> - OpenAI auto-cache: applies to prompts ≥1024 tokens; cached input priced at roughly 10% of fresh input on current rate cards (platform.openai.com).
> - Semantic cache hit rate (community-reported): ~10% open chat; up to ~70% structured FAQ. Not a vendor-documented baseline.
> - ProjectDiscovery: 7% → 74% hit rate by moving dynamic out of prefix (project blog, 2025-11).
> - Parallelization anti-pattern: typical reports of 5–10x bill inflation when N parallel requests miss the first cache write.

## Use It · 实战用法

`code/main.py` 在混合工作负载上模拟 L1 + L2 缓存。报告命中率与账单，并演示并行化惩罚。

> `code/main.py` simulates L1 + L2 caching on mixed workloads. Reports hit rates, bill, and shows the parallelization penalty.

## Ship It · 交付

本课产出 `outputs/skill-cache-auditor.md`。给定提示模板和流量，它会审计可缓存性并给出重构建议。

> This lesson produces `outputs/skill-cache-auditor.md`. Given prompt template and traffic, audits cacheability and recommends restructure.

## Exercises · 练习

1. 运行 `code/main.py`，切换并行化开关。账单变化多少？
2. 你的系统提示里有个日期。把它移出去，给出前后命中率对比的算术。
3. 给定你的请求到达速率，计算 1 小时 TTL（2 倍写入）对 5 分钟 TTL（1.25 倍写入）的盈亏平衡点。
4. 语义缓存在 0.95 阈值下命中 20%。降到 0.85 命中 50%，但你看到错误的缓存响应。选出正确的阈值并说明理由。
5. 你对每个用户问题批量发 10 个并行子查询。在不增加端到端延迟的前提下，为缓存友好性重写它。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| L2 prompt cache | 「前缀缓存」 | 厂商为重复前缀存储 KV |
| `cache_control` | 「Anthropic 缓存标记」 | 显式标记可缓存块的属性 |
| Cache write premium | 「写入税」 | 首次未命中写缓存的额外成本（1.25 倍或 2 倍） |
| L1 semantic cache | 「嵌入缓存」 | 调 LLM 前在应用层做哈希与嵌入 |
| GPTCache | 「LLM 缓存库」 | 流行的 OSS L1 缓存库 |
| Cache hit rate | 「命中数 / 总数」 | 从缓存得到服务的请求占比 |
| Parallelization anti-pattern | 「N 次写入陷阱」 | N 个并行请求 N 次全部未命中缓存 |
| Dynamic content trap | 「提示里带时间的陷阱」 | 前缀里的动态字节杀死命中率 |
| RadixAttention | 「副本内缓存」 | SGLang 的前缀缓存实现 |

## Further Reading · 延伸阅读

- [Anthropic Prompt Caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) —— `cache_control` 语义与 TTL 的官方文档。
- [OpenAI Prompt Caching](https://platform.openai.com/docs/guides/prompt-caching) —— 自动缓存行为与资格条件。
- [TianPan — Semantic Caching for LLMs Production](https://tianpan.co/blog/2026-04-10-semantic-caching-llm-production)
- [ProjectDiscovery — Cut LLM Costs 59% With Prompt Caching](https://projectdiscovery.io/blog/how-we-cut-llm-cost-with-prompt-caching)
- [DigitalOcean / Anthropic — Prompt Caching](https://www.digitalocean.com/blog/prompt-caching-with-digital-ocean)
