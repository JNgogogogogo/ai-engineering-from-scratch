# Prompt Caching and Context Caching · 提示缓存与上下文缓存

> 你的系统提示有 4,000 个 token。你的 RAG 上下文有 20,000 个 token。每次请求你都要把两者发过去，也要为两者付钱——每一次都是。提示缓存（prompt caching）让服务商在它们那边保持这个前缀「温热」，复用时只按正常费率的 10% 向你收费。用得对，它能把推理成本砍掉 50–90%，把首 token 延迟砍掉 40–85%。
>
> Your system prompt is 4,000 tokens. Your RAG context is 20,000 tokens. You send both with every request. You also pay for both — every time. Prompt caching lets the provider keep that prefix warm on their side and bill you 10% of the normal rate on reuse. Used correctly, it cuts inference cost by 50–90% and first-token latency by 40–85%.

**类型：** Build
**语言：** Python
**先修：** Phase 11 · 01（提示工程）、Phase 11 · 05（上下文工程）、Phase 11 · 11（缓存与成本）
**时间：** 约 60 分钟

## The Problem · 问题在哪

一个编码智能体在对话的每一轮都把同一段 15,000 token 的系统提示发给 Claude。按每百万输入 token $3 计算，二十轮就是 $0.90 的纯输入成本——这还没算用户真正的消息。乘以每天 10,000 场对话，账单就到了 $9,000/天，全花在从不变异的文本上。

你无法在不伤质量的前提下缩小提示。你也无法不发它——模型每一轮都需要它。唯一的招是：不要再为服务商早已见过的一段前缀付全价。

这一招就是提示缓存。Anthropic 在 2024 年 8 月上线了它（2025 年又推出 1 小时延长 TTL 的变体），OpenAI 在同年晚些时候把它自动化，Google 在 Gemini 1.5 旁推出了显式上下文缓存（context caching），如今三家都在自家旗舰模型上把它当一等公民特性提供。

> A coding agent sends the same 15,000-token system prompt to Claude on every turn of a conversation. Twenty turns at $3/M input tokens is $0.90 in input cost alone — before any of the user's actual messages. Multiply by 10,000 daily conversations and the bill hits $9,000/day for text that never changes.
> You cannot shrink the prompt without hurting quality. You cannot avoid sending it — the model needs it on every turn. The only move is to stop paying full price for a prefix the provider has already seen.
> That move is prompt caching. Anthropic shipped it in August 2024 (with a 1-hour extended-TTL variant in 2025), OpenAI automated it later that year, Google shipped explicit context caching alongside Gemini 1.5, and all three now offer it as a first-class feature on their frontier models.

## The Concept · 概念

![提示缓存：写一次，读得便宜](../assets/prompt-caching.svg)

**机制。** 当一个请求的前缀与近期某个请求的前缀匹配时，服务商直接用上一次运行留下的 KV 缓存（KV-cache），而不是重新编码这些 token。第一次你付一笔小的写入溢价，之后的每一次都享受大的读取折扣。

**2026 年的三种服务商风格。**

| 服务商 | API 风格 | 命中折扣 | 写入溢价 | 默认 TTL | 最小可缓存长度 |
|---------|-----------|--------------|---------------|-------------|---------------|
| Anthropic | 在内容块上显式标记 `cache_control` | 输入省 90% | 加收 25% | 5 分钟（可延长到 1 小时） | 1,024 tokens（Sonnet/Opus）、2,048（Haiku） |
| OpenAI | 自动前缀检测 | 输入省 50% | 无 | 最长 1 小时（尽力而为） | 1,024 tokens |
| Google (Gemini) | 显式 `CachedContent` API | 按存储计费；读取约为正常价的 25% | 每 token·小时收存储费 | 用户设定（默认 1 小时） | 4,096 tokens（Flash）、32,768（Pro） |

**不变量。** 三家都只缓存前缀。只要请求之间有任何一个 token 不同，第一个不同的 token 之后的一切都是 miss。把*稳定*的部分放顶部，*易变*的部分放底部。

> **The mechanic.** When a request's prefix matches one from a recent request, the provider serves the KV-cache from the previous run instead of re-encoding the tokens. You pay a small write premium the first time and a large read discount every time after.
> **The invariant.** All three cache prefixes only. If any token differs between requests, everything after the first differing token is a miss. Put the *stable* parts at the top, the *variable* parts at the bottom.

### The cache-friendly layout · 缓存友好布局

```
[system prompt]          <-- cache this
[tool definitions]       <-- cache this
[few-shot examples]      <-- cache this
[retrieved documents]    <-- cache if reused, else don't
[conversation history]   <-- cache up to last turn
[current user message]   <-- never cache (different every time)
```

破坏这个顺序——把用户消息放到系统提示上面、把动态检索插进 few-shot 中间——缓存就永远不会命中。

> Violate the order — put the user message above the system prompt, interleave dynamic retrievals between few-shots — and the cache never hits.

### The break-even calculation · 盈亏平衡计算

Anthropic 25% 的写入溢价意味着一个缓存块至少要被读两次才能净省钱。1 次写 + 1 次读平均每次请求成本 0.675x（省 32%）；1 次写 + 10 次读平均 0.205x（省 80%）。经验法则：凡是你预期在 TTL 内复用至少 3 次的内容，都值得缓存。

```figure
prompt-cache-hit
```

> Anthropic's 25% write premium means a cached block has to be read at least twice to net-save money. 1 write + 1 read averages 0.675x cost per request (saves 32%); 1 write + 10 reads averages 0.205x (saves 80%). Rule of thumb: cache anything you expect to reuse at least 3 times within the TTL.

## Build It · 动手造

### Step 1: Anthropic prompt caching with explicit markers · Anthropic 用显式标记做提示缓存

```python
import anthropic

client = anthropic.Anthropic()

SYSTEM = [
    {
        "type": "text",
        "text": "You are a senior Python reviewer. Follow the rubric exactly.\n\n" + RUBRIC_15K_TOKENS,
        "cache_control": {"type": "ephemeral"},
    }
]

def review(code: str):
    return client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        system=SYSTEM,
        messages=[{"role": "user", "content": code}],
    )
```

`cache_control` 标记告诉 Anthropic 把这个块存 5 分钟。窗口内的重用即命中；过期后再用就重新写入。

**响应中的 usage 字段：**

```python
response = review(code_a)
response.usage
# InputTokensUsage(
#     input_tokens=120,
#     cache_creation_input_tokens=15023,   # paid at 1.25x
#     cache_read_input_tokens=0,
#     output_tokens=340,
# )

response_b = review(code_b)
response_b.usage
# cache_creation_input_tokens=0
# cache_read_input_tokens=15023           # paid at 0.1x
```

在 CI 里同时检查这两个字段——如果 `cache_read_input_tokens` 在多次请求之间一直是 0，说明你的缓存键在漂移。

> The `cache_control` marker tells Anthropic to store the block for 5 minutes. Reuse within that window hits; reuse after expires and writes again.
> Check both fields in CI — if `cache_read_input_tokens` stays at zero across requests, your cache keys are drifting.

### Step 2: one-hour extended TTL · 一小时延长 TTL

对长时间运行的批处理任务，5 分钟默认值会在任务之间过期。设置 `ttl`：

```python
{"type": "text", "text": RUBRIC, "cache_control": {"type": "ephemeral", "ttl": "1h"}}
```

1 小时 TTL 的写入溢价是 2 倍（比基线高 50% 而不是 25%），但对任何复用该前缀超过 5 次的批任务来说回本很快。

> For long-running batch jobs, the 5-minute default expires between jobs. Set `ttl`.
> 1-hour TTL costs 2x the write premium (50% over baseline instead of 25%) but pays back fast on any batch reusing the prefix more than 5 times.

### Step 3: OpenAI automatic caching · OpenAI 自动缓存

OpenAI 没有任何需要你配置的东西。任何超过 1,024 token、且与近期请求匹配的前缀，自动获得 50% 折扣。

```python
from openai import OpenAI
client = OpenAI()

resp = client.chat.completions.create(
    model="gpt-5",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},   # long and stable
        {"role": "user", "content": user_msg},
    ],
)
resp.usage.prompt_tokens_details.cached_tokens  # the discounted portion
```

同样的缓存友好布局规则适用。有两件事会杀死 OpenAI 的缓存但不会杀死 Anthropic 的：改变 `user` 字段（它被用作缓存键的一个组成部分）和重排工具顺序。

> OpenAI gives you nothing to configure. Any prefix over 1,024 tokens that matches a recent request gets a 50% discount automatically.
> Same cache-friendly layout rule applies. Two things kill OpenAI's cache that don't kill Anthropic's: changing the `user` field (used as a cache key component) and reordering tools.

### Step 4: Gemini explicit context caching · Gemini 显式上下文缓存

Gemini 把缓存当作一等公民对象，由你创建并命名：

```python
from google import genai
from google.genai import types

client = genai.Client()

cache = client.caches.create(
    model="gemini-3.8-flash",
    config=types.CreateCachedContentConfig(
        display_name="rubric-v3",
        system_instruction=RUBRIC,
        contents=[FEW_SHOT_EXAMPLES],
        ttl="3600s",
    ),
)

resp = client.models.generate_content(
    model="gemini-3.8-flash",
    contents=["Review this code:\n" + code],
    config=types.GenerateContentConfig(cached_content=cache.name),
)
```

只要缓存存活，Gemini 就按 token·小时收存储费，读取约为正常输入费率的 25%。当你要跨多个会话、跨越多天复用同一个巨型提示时，这就是正确的形态。

> Gemini treats the cache as a first-class object you create and name.
> Gemini charges storage per token·hour for as long as the cache lives, and reads at ~25% of normal input rate. This is the right shape when you reuse the same giant prompt across many sessions over days.

### Step 5: measuring hit rate in production · 在生产环境测命中率

见 `code/main.py`：一个模拟的三服务商记账器，跟踪写/读/未命中次数并计算每 1K 请求的混合成本。部署要以目标命中率作为门槛——大多数生产环境的 Anthropic 配置在预热之后，读取占比应超过 80%。

> See `code/main.py` for a simulated three-provider accountant that tracks write/read/miss counts and computes blended cost per 1K requests. Gate deploys on a target hit rate — most production Anthropic setups should see >80% read fraction after warmup.

## Pitfalls that still ship in 2026 · 2026 年仍在翻车的坑

- **顶部放动态时间戳。** 系统提示顶部出现 `"Current time: 2026-04-22 15:30:02"`。每次请求都 miss。把时间戳挪到缓存断点之下。
- **工具重排。** 用稳定顺序序列化工具——两次部署之间字典顺序一变，所有命中全部报废。
- **自由文本近似重复。** "You are helpful." 和 "You are a helpful assistant."——一个字节的差别 = 全部 miss。
- **块太小。** Anthropic 强制 1,024 token 下限（Haiku 为 2,048）。更小的块会静默地不缓存。
- **盲目的成本看板。** 把「输入 token」拆成缓存 vs 未缓存。否则一次流量下滑会被误读成缓存的功劳。

> **Dynamic timestamps at the top.** `"Current time: 2026-04-22 15:30:02"` at the top of the system prompt. Every request misses. Move timestamps below the cache breakpoint.
> **Tool reordering.** Serialize tools in a stable order — a dict reshuffle between deploys breaks every hit.
> **Free-text near-duplicates.** "You are helpful." vs "You are a helpful assistant." — one byte difference = full miss.
> **Too-small blocks.** Anthropic enforces a 1,024-token floor (2,048 for Haiku). Smaller blocks silently do not cache.
> **Blind cost dashboards.** Split "input tokens" into cached vs uncached. Otherwise a traffic drop looks like a cache win.

## Use It · 实战用法

2026 年的缓存选型：

| 情况 | 选择 |
|-----------|------|
| 稳定的 10k+ 系统提示、多轮对话的智能体 | Anthropic `cache_control`，5 分钟 TTL |
| 复用同一前缀超过 30 分钟的批处理任务 | Anthropic，`ttl: "1h"` |
| GPT-5 上的 serverless 端点、没有自定义基础设施 | OpenAI 自动缓存（只需让前缀稳定且够长） |
| 跨多天复用巨型代码/文档语料 | Gemini 显式 `CachedContent` |
| 跨服务商回退 | 让可缓存前缀布局在多家服务商之间保持一致，任一家的命中都能用 |

用户消息这一层可以与语义缓存（semantic caching，Phase 11 · 11）组合：提示缓存处理 *token 完全相同* 的重用，语义缓存处理 *含义相同* 的重用。

> The 2026 caching stack.
> Combine with semantic caching (Phase 11 · 11) for the user-message layer: prompt caching handles *token-identical* reuse, semantic caching handles *meaning-identical* reuse.

## Ship It · 交付

保存 `outputs/skill-prompt-caching-planner.md`：

```markdown
---
name: prompt-caching-planner
description: Design a cache-friendly prompt layout and pick the right provider caching mode.
version: 1.0.0
phase: 11
lesson: 15
tags: [llm-engineering, caching, cost]
---

Given a prompt (system + tools + few-shot + retrieval + history + user) and a usage profile (requests per hour, TTL needed, provider), output:

1. Layout. Reordered sections with a single cache breakpoint marked; explain which sections are stable, which are volatile.
2. Provider mode. Anthropic cache_control, OpenAI automatic, or Gemini CachedContent. Justify from TTL and reuse pattern.
3. Break-even. Expected reads per write within TTL; net cost vs no-cache with math.
4. Verification plan. CI assertion that cache_read_input_tokens > 0 on the second identical request; dashboard split by cached vs uncached tokens.
5. Failure modes. List the three most likely reasons the cache will miss in this setup (dynamic timestamp, tool reorder, near-duplicate text) and how you will prevent each.

Refuse to ship a cache plan that places a dynamic field above the breakpoint. Refuse to enable 1h TTL without a reuse count that makes the 2x write premium pay back.
```

> Save `outputs/skill-prompt-caching-planner.md`.

## Exercises · 练习

1. **简单。** 对 Claude 跑一段 10 轮对话，带 5,000 token 的系统提示。先不加 `cache_control` 跑一遍，再加上跑一遍。报告两种情况的输入 token 账单。
2. **中等。** 写一个测试工具：给定提示模板和请求日志，按服务商（Anthropic 5m、Anthropic 1h、OpenAI 自动、Gemini 显式）计算预期命中率与美元节省。
3. **困难。** 做一个布局优化器：给定一个提示和一组标记 `stable=True/False` 的字段，重写提示，在不丢失信息的前提下把唯一的缓存断点放到最大的缓存友好位置。在真实 Anthropic 端点上验证。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Prompt caching（提示缓存） | “让长提示变便宜” | 对匹配前缀复用服务商侧的 KV 缓存；重复输入 token 享受 50-90% 折扣。 |
| `cache_control` | “Anthropic 的标记” | 内容块属性，声明「到这里的所有内容都可缓存」；`{"type": "ephemeral"}`。 |
| Cache write（缓存写入） | “付溢价” | 第一次填充缓存的请求；Anthropic 按 ~1.25x 输入费率计费，OpenAI 免费。 |
| Cache read（缓存读取） | “折扣” | 后续匹配前缀的请求；按 10%（Anthropic）、50%（OpenAI）、约 25%（Gemini）计费。 |
| TTL | “能活多久” | 缓存保持温热的秒数；Anthropic 默认 5 分钟（可延长到 1 小时），OpenAI 尽力而为最长 1 小时，Gemini 用户设定。 |
| Extended TTL | “Anthropic 的 1 小时缓存” | `{"type": "ephemeral", "ttl": "1h"}`；写入溢价 2 倍，但对批处理复用值得。 |
| Prefix match（前缀匹配） | “我的缓存为什么 miss” | 只有从头到断点的每个 token 都逐字节一致，缓存才命中。 |
| Context caching (Gemini)（上下文缓存） | “那个显式的” | Google 的命名式、按存储计费的缓存对象；最适合跨多天复用大型语料。 |

## Further Reading · 延伸阅读

- [Anthropic — Prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) —— `cache_control`、1 小时 TTL、盈亏平衡表。
- [OpenAI — Prompt caching](https://platform.openai.com/docs/guides/prompt-caching) —— 自动前缀匹配。
- [Google — Context caching](https://ai.google.dev/gemini-api/docs/caching) —— `CachedContent` API 与存储定价。
- [Anthropic engineering — Prompt caching for long-context workloads](https://www.anthropic.com/news/prompt-caching) —— 带延迟数字的原始发布文章。
- Phase 11 · 05（Context Engineering / 上下文工程）—— 决定从哪里切分提示，缓存才落得下来。
- Phase 11 · 11（Caching and Cost / 缓存与成本）—— 把提示缓存与用户消息上的语义缓存配对。
- [Pope et al., "Efficiently Scaling Transformer Inference" (2022)](https://arxiv.org/abs/2211.05102) —— 提示缓存所暴露给用户的 KV 缓存内存模型；解释为什么重读一段缓存前缀比重新计算便宜约 10 倍。
- [Agrawal et al., "SARATHI: Efficient LLM Inference by Piggybacking Decodes with Chunked Prefills" (2023)](https://arxiv.org/abs/2308.16369) —— prefill 正是提示缓存抄近路的阶段；这篇论文解释了为什么缓存命中时 TTFT 大幅下降而 TPOT 不受影响。
- [Leviathan et al., "Fast Inference from Transformers via Speculative Decoding" (2023)](https://arxiv.org/abs/2211.17192) —— 提示缓存与投机解码（speculative decoding）、Flash Attention、MQA/GQA 并列，都是能掰弯推理成本曲线的杠杆；想了解另外三个就读这篇。
