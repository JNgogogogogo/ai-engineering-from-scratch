# Caching, Rate Limiting & Cost Optimization · 缓存、限流与成本优化

> 大多数 AI 创业公司不是死于模型差，而是死于糟糕的单位经济学（unit economics）。一次 GPT-4o 调用只花零点几美分。一万个用户每人每天打十个请求，光输入 token 就要 $250——这还是在你收进第一美元之前。能活下来的公司，是把每次 API 调用当成一笔金融交易、而不是一次函数调用的公司。

> Most AI startups do not die from bad models. They die from bad unit economics. A single GPT-4o call costs fractions of a cent. Ten thousand users making ten calls per day costs $250 in input tokens alone -- before you charge a single dollar. The companies that survive are the ones that treat every API call as a financial transaction, not a function call.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 11 Lesson 09 (Function Calling)
**Time:** ~45 minutes
**Related:** Phase 11 · 15（Prompt Caching）——本课讲应用层缓存（语义缓存、精确哈希缓存、模型路由）；Lesson 15 讲提供商层的提示词缓存（Anthropic cache_control、OpenAI 自动缓存、Gemini CachedContent）。两者结合可以省 50-95% 的成本。

---

## Learning Objectives · 学习目标

- 实现语义缓存（semantic caching）：重复或相似的查询直接由缓存服务，不再发起新的 API 调用
- 计算跨提供商的每请求成本，实现感知 token 的限流（rate limiting）和预算告警
- 构建成本优化层：提示词压缩、模型路由（贵模型 vs 便宜模型）、响应缓存
- 针对不同查询类型，设计组合精确匹配、语义相似度和前缀缓存的分层缓存策略

> Implement semantic caching that serves repeated or similar queries from cache instead of making a new API call
> Calculate per-request costs across providers and implement token-aware rate limiting and budget alerts
> Build a cost optimization layer with prompt compression, model routing (expensive vs cheap), and response caching
> Design a tiered caching strategy using exact match, semantic similarity, and prefix caching for different query types

---

## The Problem · 问题在哪

你做了一个 RAG 聊天机器人。它运行得非常漂亮。用户也喜欢。

然后账单来了。

GPT-5 输入 $5/百万 token、输出 $15/百万。Claude Opus 4.7 是 $15 输入 / $75 输出。Gemini 3 Pro 是 $1.25 输入 / $5 输出。GPT-5-mini 是 $0.25/$2。以下价格仅为示意；请以各提供商当前的定价页为准。

压垮创业公司的账是这样算的：

- 10,000 日活用户
- 每用户每天 10 次查询
- 每次查询 1,000 输入 token（系统提示词 + 上下文 + 用户消息）
- 每条响应 500 输出 token

**每日输入成本：** 10,000 x 10 x 1,000 / 1,000,000 x $2.50 = **$250/天**
**每日输出成本：** 10,000 x 10 x 500 / 1,000,000 x $10.00 = **$500/天**
**月总计：** **$22,500/月**

这还只是 LLM。再加上嵌入、向量数据库托管、基础设施——一个聊天机器人，你要面对每月 $30,000。

残酷的部分在于：这些查询里有 40-60% 是近似重复。用户用稍微不同的措辞问同样的问题。你的系统提示词——每个请求都一模一样——却每次都被计费。RAG 检索到的上下文文档，在问同一话题的用户之间反复出现。

你在为冗余计算付全价。

> You build a RAG chatbot. It works beautifully. Users love it. Then the invoice arrives.
> The brutal part: 40-60% of those queries are near-duplicates. Users ask the same questions in slightly different words. Your system prompt -- identical across every request -- gets billed every single time. Context documents retrieved by RAG repeat across users who ask about the same topic.
> You are paying full price for redundant computation.

---

## The Concept · 概念

### The Cost Anatomy of an LLM Call · 一次 LLM 调用的成本解剖

每次 API 调用有五个成本组成部分。

```mermaid
graph LR
    A[User Query] --> B[System Prompt<br/>500-2000 tokens]
    A --> C[Retrieved Context<br/>500-4000 tokens]
    A --> D[User Message<br/>50-500 tokens]
    B --> E[Input Cost<br/>$2.50/1M tokens]
    C --> E
    D --> E
    E --> F[Model Processing]
    F --> G[Output Cost<br/>$10.00/1M tokens]
```

系统提示词是沉默的杀手。一个 1,500 token 的系统提示词随每个请求发送，仅这个前缀每百万次请求就要花 $3.75。按每天 10 万次请求算，那是 $375/天——$11,250/月——花在一段永远不会变的文字上。

> Every API call has five cost components.
> System prompts are the silent killer. A 1,500-token system prompt sent with every request costs $3.75 per million requests just for that prefix. At 100K requests per day, that is $375/day -- $11,250/month -- for text that never changes.

---

### Provider Caching: Built-in Discounts · 提供商缓存：内置折扣

到 2026 年，三家主要提供商都提供提供商侧的提示词缓存，但机制各不相同。深入分析见 Phase 11 · 15。

| 提供商 | 机制 | 折扣 | 最低要求 | 缓存时长 |
|----------|-----------|----------|---------|----------------|
| Anthropic | 显式 cache_control 标记 | 缓存命中省 90%（写入加收 25%） | 1,024 token（Sonnet/Opus）、2,048（Haiku） | 默认 5 分钟；可延长到 1 小时（写入加收 2 倍溢价） |
| OpenAI | 自动前缀匹配 | 缓存命中省 50% | 1,024 token | 尽力而为，最长 1 小时 |
| Google Gemini | 显式 CachedContent API | 约省 75%（另加存储费） | 4,096（Flash）/ 32,768（Pro） | 用户可配置 TTL |

**Anthropic 的方案**是显式的。你用 `cache_control: {"type": "ephemeral"}` 标记提示词的某些段落。首次请求付 25% 的写入溢价；之后相同前缀的请求享受 90% 折扣。一个正常成本 $0.005 的 2,000 token 系统提示词，缓存命中时只花 $0.000625。按 10 万次请求算，每天省 $437.50。

**OpenAI 的方案**是自动的。任何与之前请求匹配的提示词前缀自动享受 50% 折扣，不需要任何标记。代价是：折扣少一点、控制少一点，但实现成本为零。

> All three major providers offer provider-side prompt caching in 2026, but the mechanics differ. See Phase 11 · 15 for the deep dive.
> Anthropic's approach is explicit. You mark sections of your prompt with `cache_control: {"type": "ephemeral"}`. The first request pays a 25% write premium. Subsequent requests with the same prefix get a 90% discount.
> OpenAI's approach is automatic. Any prompt prefix that matches a previous request gets a 50% discount. No markers needed. The tradeoff: less discount, less control, but zero implementation effort.

---

### Semantic Caching: Your Custom Layer · 语义缓存：你自己加的那一层

提供商缓存只对完全相同的前缀有效。语义缓存处理更难的情况：意思相同、问法不同的查询。

「退货政策是什么？」和「怎么退货？」是不同的字符串，但意图完全一样。语义缓存把两个查询都做嵌入（embed），计算余弦相似度，相似度超过阈值（通常 0.92-0.95）就返回缓存的响应。

```mermaid
flowchart TD
    A[User Query] --> B[Embed Query]
    B --> C{Similar query<br/>in cache?}
    C -->|sim > 0.95| D[Return Cached Response]
    C -->|sim < 0.95| E[Call LLM API]
    E --> F[Cache Response<br/>with Embedding]
    F --> G[Return Response]
    D --> G
```

嵌入的成本可以忽略不计。OpenAI 的 text-embedding-3-small 是 $0.02/百万 token。和一次完整的 LLM 调用相比，查缓存的成本几乎为零。

> Provider caching only works for identical prefixes. Semantic caching handles the harder case: different queries with the same meaning.
> "What is the return policy?" and "How do I return an item?" are different strings but identical intent. A semantic cache embeds both queries, computes cosine similarity, and returns the cached response if similarity exceeds a threshold (typically 0.92-0.95).
> The embedding costs are negligible. OpenAI's text-embedding-3-small costs $0.02 per million tokens. Checking the cache costs almost nothing compared to a full LLM call.

---

### Exact Caching: Hash and Match · 精确缓存：先哈希再匹配

对确定性调用（temperature=0、同模型、同提示词），精确缓存更简单、更快。对完整提示词做哈希，查缓存，命中就返回。

它完美适用于：
- 系统提示词 + 固定上下文 + 一模一样的用户查询
- 工具定义完全相同的函数调用
- 同一文档要处理多遍的批处理

> For deterministic calls (temperature=0, same model, same prompt), exact caching is simpler and faster. Hash the full prompt, check the cache, return if found.
> This works perfectly for: system prompt + fixed context + identical user queries; function calling with identical tool definitions; batch processing where the same document gets processed multiple times.

---

### Rate Limiting: Protecting Your Budget · 限流：保护你的预算

限流不只是公平问题，它是生存问题。

**令牌桶算法（token bucket）**：每个用户有一个装着 N 个 token 的桶，以每秒 R 个的速度补充。一个请求从桶里消耗 token。桶空了，请求就被拒绝。它允许突发（一口气用光整桶），同时约束平均速率。

**按用户配额**：按用户层级设置每日/每月 token 上限。

| 层级 | 每日 token 上限 | 每分钟最大请求数 | 可用模型 |
|------|------------------|------------------|-------------|
| Free | 50,000 | 10 | 仅 GPT-4o-mini |
| Pro | 500,000 | 60 | GPT-4o、Claude Sonnet |
| Enterprise | 5,000,000 | 300 | 全部模型 |

> Rate limiting is not just about fairness. It is about survival.
> Token bucket algorithm: each user gets a bucket of N tokens that refills at rate R per second. A request consumes tokens from the bucket. If the bucket is empty, the request is rejected. This allows bursts (use the full bucket at once) while enforcing an average rate.
> Per-user quotas: set daily/monthly token limits per user tier.

---

### Model Routing: Right Model for the Right Job · 模型路由：合适的模型干合适的活

不是每个查询都需要 GPT-4o。

「商店几点关门？」不需要一个 $10/M 输出的模型。$0.60/M 输出的 GPT-4o-mini 处理它绰绰有余，$1.25/M 输出的 Claude Haiku 也行。一个简单的分类器把便宜的查询路由给便宜模型，把复杂查询路由给贵模型。

```mermaid
flowchart TD
    A[User Query] --> B[Complexity Classifier]
    B -->|Simple: lookup, FAQ| C[GPT-4o-mini<br/>$0.15/$0.60 per 1M]
    B -->|Medium: analysis, summary| D[Claude Sonnet<br/>$3.00/$15.00 per 1M]
    B -->|Complex: reasoning, code| E[GPT-4o / Claude Opus<br/>$2.50/$10.00+]
```

一个调好的路由器，光模型成本就能省 40-70%。

> Not every query needs GPT-4o.
> "What time does the store close?" does not require a $10/M-output model. GPT-4o-mini at $0.60/M output handles it perfectly. Claude Haiku at $1.25/M output handles it. A simple classifier routes cheap queries to cheap models and complex queries to expensive models.
> A well-tuned router saves 40-70% on model costs alone.

---

### Cost Tracking: Know Where the Money Goes · 成本追踪：知道钱花在哪

测不了的东西优化不了。记录每次 API 调用的：

- 时间戳
- 模型名
- 输入 token
- 输出 token
- 延迟（ms）
- 计算出的成本（$）
- 用户 ID
- 缓存命中/未命中
- 请求类别

这些数据会告诉你哪些功能烧钱、哪些用户是重度使用者、缓存在哪里收益最大。

> You cannot optimize what you do not measure. Log every API call with: timestamp, model name, input tokens, output tokens, latency, computed cost, user ID, cache hit/miss, and request category.
> This data reveals which features are expensive, which users are heavy consumers, and where caching has the most impact.

---

### Batching: Bulk Discounts · 批处理：批发折扣

OpenAI 的 Batch API 以 50% 折扣异步处理请求。你一次最多提交 50,000 个请求，24 小时内返回结果。

适合批处理的场景：
- 夜间文档处理
- 批量分类
- 评估运行
- 数据富化流水线

不适合：实时的面向用户的查询（延迟要紧）。

> OpenAI's Batch API processes requests asynchronously at a 50% discount. You submit a batch of up to 50,000 requests, and results come back within 24 hours.
> Use batching for: nightly document processing, bulk classification, evaluation runs, data enrichment pipelines.
> Not for: real-time user-facing queries (latency matters).

---

### Budget Alerts and Circuit Breakers · 预算告警与熔断器

熔断器（circuit breaker）在你触及上限时停止花钱。没有它，一个 bug 或一次滥用能在几小时内烧光你的月度预算。

设三个阈值：
1. **警告**（预算的 70%）：发告警
2. **限流**（预算的 85%）：只切到便宜模型
3. **停止**（预算的 95%）：拒绝新请求，只返回缓存响应

> A circuit breaker stops spending when you hit a limit. Without one, a bug or abuse can burn through your monthly budget in hours.
> Set three thresholds: Warning (70% of budget): send an alert; Throttle (85% of budget): switch to cheaper models only; Stop (95% of budget): reject new requests, return cached responses only.

---

### The Optimization Stack · 优化栈

按顺序叠加这些技术。每一层都在前几层的基础上继续省钱。

| 层 | 技术 | 典型节省 | 实现成本 |
|-------|-----------|----------------|----------------------|
| 1 | 提供商提示词缓存 | 30-50% | 低（加缓存标记） |
| 2 | 精确缓存 | 10-20% | 低（哈希 + 字典） |
| 3 | 语义缓存 | 15-30% | 中（嵌入 + 相似度） |
| 4 | 模型路由 | 40-70% | 中（分类器） |
| 5 | 限流 | 保护预算 | 低（令牌桶） |
| 6 | 提示词压缩 | 10-30% | 中（重写提示词） |
| 7 | 批处理 | 符合条件部分省 50% | 低（Batch API） |

一个用上 1-5 层的 RAG 应用，通常能把成本从 $22,500/月 压到 $4,000-6,000/月。这就是烧光跑道和做成一门生意之间的差别。

> Apply these techniques in order. Each layer compounds on the previous ones.
> A RAG app applying layers 1-5 typically reduces costs from $22,500/month to $4,000-6,000/month. That is the difference between burning runway and building a business.

---

### Real Savings: Before and After · 真实节省：优化前后

这是一个服务 10,000 DAU 的 RAG 聊天机器人的真实拆账。

| 指标 | 优化前 | 优化后 | 节省 |
|--------|--------------------|--------------------|---------|
| 月度 LLM 成本 | $22,500 | $5,200 | 77% |
| 每查询平均成本 | $0.0075 | $0.0017 | 77% |
| 缓存命中率 | 0% | 52% | -- |
| 路由到 mini 的查询占比 | 0% | 65% | -- |
| P95 延迟 | 2,800ms | 900ms（缓存命中 50ms） | 68% |
| 月度嵌入成本 | $0 | $180 | （新增成本） |
| 月度总成本 | $22,500 | $5,380 | 76% |

语义缓存的嵌入成本（$180/月），在缓存开始命中的第一个小时内就回本了。

```figure
semantic-cache
```

> Here is a real breakdown for a RAG chatbot serving 10,000 DAU.
> The embedding cost for semantic caching ($180/month) pays for itself within the first hour of cache hits.

## Build It · 动手造

### Step 1: Cost Calculator · 第 1 步：成本计算器

构建一个知道主流模型当前价格的 token 成本计算器。

```python
import hashlib
import time
import json
import math
from dataclasses import dataclass, field


MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00, "cached_input": 1.25},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "cached_input": 0.075},
    "gpt-4.1": {"input": 2.00, "output": 8.00, "cached_input": 0.50},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60, "cached_input": 0.10},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40, "cached_input": 0.025},
    "o3": {"input": 2.00, "output": 8.00, "cached_input": 0.50},
    "o3-mini": {"input": 1.10, "output": 4.40, "cached_input": 0.55},
    "o4-mini": {"input": 1.10, "output": 4.40, "cached_input": 0.275},
    "claude-opus-4": {"input": 15.00, "output": 75.00, "cached_input": 1.50},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00, "cached_input": 0.30},
    "claude-haiku-3.5": {"input": 0.80, "output": 4.00, "cached_input": 0.08},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00, "cached_input": 0.3125},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60, "cached_input": 0.0375},
}


def calculate_cost(model, input_tokens, output_tokens, cached_input_tokens=0):
    if model not in MODEL_PRICING:
        return {"error": f"Unknown model: {model}"}
    pricing = MODEL_PRICING[model]
    non_cached = input_tokens - cached_input_tokens
    input_cost = (non_cached / 1_000_000) * pricing["input"]
    cached_cost = (cached_input_tokens / 1_000_000) * pricing["cached_input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total = input_cost + cached_cost + output_cost
    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_input_tokens": cached_input_tokens,
        "input_cost": round(input_cost, 6),
        "cached_input_cost": round(cached_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(total, 6),
    }
```

> Build a token cost calculator that knows current pricing for major models.

### Step 2: Exact Cache · 第 2 步：精确缓存

对完整提示词做哈希，一模一样的请求直接返回缓存的响应。

```python
class ExactCache:
    def __init__(self, max_size=1000, ttl_seconds=3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0

    def _hash(self, model, messages, temperature):
        key_data = json.dumps({"model": model, "messages": messages, "temperature": temperature}, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, model, messages, temperature=0.0):
        if temperature > 0:
            self.misses += 1
            return None
        key = self._hash(model, messages, temperature)
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                self.hits += 1
                entry["access_count"] += 1
                return entry["response"]
            del self.cache[key]
        self.misses += 1
        return None

    def put(self, model, messages, temperature, response):
        if temperature > 0:
            return
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache, key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest_key]
        key = self._hash(model, messages, temperature)
        self.cache[key] = {
            "response": response,
            "timestamp": time.time(),
            "access_count": 1,
        }

    def stats(self):
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 4) if total > 0 else 0,
            "cache_size": len(self.cache),
        }
```

> Hash the full prompt and return cached responses for identical requests.

### Step 3: Semantic Cache · 第 3 步：语义缓存

把查询做嵌入，相似度超过阈值就返回缓存的响应。

```python
def simple_embed(text):
    words = text.lower().split()
    vocab = {}
    for w in words:
        vocab[w] = vocab.get(w, 0) + 1
    norm = math.sqrt(sum(v * v for v in vocab.values()))
    if norm == 0:
        return {}
    return {k: v / norm for k, v in vocab.items()}


def cosine_similarity(a, b):
    if not a or not b:
        return 0.0
    all_keys = set(a) | set(b)
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in all_keys)
    return dot


class SemanticCache:
    def __init__(self, similarity_threshold=0.85, max_size=500, ttl_seconds=3600):
        self.entries = []
        self.threshold = similarity_threshold
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0

    def get(self, query):
        query_embedding = simple_embed(query)
        now = time.time()
        best_match = None
        best_sim = 0.0
        for entry in self.entries:
            if now - entry["timestamp"] > self.ttl:
                continue
            sim = cosine_similarity(query_embedding, entry["embedding"])
            if sim > best_sim:
                best_sim = sim
                best_match = entry
        if best_match and best_sim >= self.threshold:
            self.hits += 1
            best_match["access_count"] += 1
            return {"response": best_match["response"], "similarity": round(best_sim, 4), "original_query": best_match["query"]}
        self.misses += 1
        return None

    def put(self, query, response):
        if len(self.entries) >= self.max_size:
            self.entries.sort(key=lambda e: e["timestamp"])
            self.entries.pop(0)
        self.entries.append({
            "query": query,
            "embedding": simple_embed(query),
            "response": response,
            "timestamp": time.time(),
            "access_count": 1,
        })

    def stats(self):
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 4) if total > 0 else 0,
            "cache_size": len(self.entries),
        }
```

> Embed queries and return cached responses when similarity exceeds a threshold.

### Step 4: Rate Limiter · 第 4 步：限流器

带按用户配额的令牌桶限流器。

```python
class TokenBucketRateLimiter:
    def __init__(self):
        self.buckets = {}
        self.tiers = {
            "free": {"capacity": 50_000, "refill_rate": 500, "max_requests_per_min": 10},
            "pro": {"capacity": 500_000, "refill_rate": 5_000, "max_requests_per_min": 60},
            "enterprise": {"capacity": 5_000_000, "refill_rate": 50_000, "max_requests_per_min": 300},
        }

    def _get_bucket(self, user_id, tier="free"):
        if user_id not in self.buckets:
            tier_config = self.tiers.get(tier, self.tiers["free"])
            self.buckets[user_id] = {
                "tokens": tier_config["capacity"],
                "capacity": tier_config["capacity"],
                "refill_rate": tier_config["refill_rate"],
                "last_refill": time.time(),
                "request_timestamps": [],
                "max_rpm": tier_config["max_requests_per_min"],
                "tier": tier,
                "total_tokens_used": 0,
            }
        return self.buckets[user_id]

    def _refill(self, bucket):
        now = time.time()
        elapsed = now - bucket["last_refill"]
        refill = int(elapsed * bucket["refill_rate"])
        if refill > 0:
            bucket["tokens"] = min(bucket["capacity"], bucket["tokens"] + refill)
            bucket["last_refill"] = now

    def check(self, user_id, tokens_needed, tier="free"):
        bucket = self._get_bucket(user_id, tier)
        self._refill(bucket)
        now = time.time()
        bucket["request_timestamps"] = [t for t in bucket["request_timestamps"] if now - t < 60]
        if len(bucket["request_timestamps"]) >= bucket["max_rpm"]:
            return {"allowed": False, "reason": "rate_limit", "retry_after_seconds": 60 - (now - bucket["request_timestamps"][0])}
        if bucket["tokens"] < tokens_needed:
            deficit = tokens_needed - bucket["tokens"]
            wait = deficit / bucket["refill_rate"]
            return {"allowed": False, "reason": "token_limit", "tokens_available": bucket["tokens"], "retry_after_seconds": round(wait, 1)}
        return {"allowed": True, "tokens_available": bucket["tokens"]}

    def consume(self, user_id, tokens_used, tier="free"):
        bucket = self._get_bucket(user_id, tier)
        bucket["tokens"] -= tokens_used
        bucket["request_timestamps"].append(time.time())
        bucket["total_tokens_used"] += tokens_used

    def get_usage(self, user_id):
        if user_id not in self.buckets:
            return {"error": "User not found"}
        b = self.buckets[user_id]
        return {
            "user_id": user_id,
            "tier": b["tier"],
            "tokens_remaining": b["tokens"],
            "capacity": b["capacity"],
            "total_tokens_used": b["total_tokens_used"],
            "utilization": round(b["total_tokens_used"] / b["capacity"], 4) if b["capacity"] else 0,
        }
```

> Token bucket rate limiter with per-user quotas.

### Step 5: Cost Tracker · 第 5 步：成本追踪器

记录每次调用，并计算累计总额。

```python
class CostTracker:
    def __init__(self, monthly_budget=1000.0):
        self.logs = []
        self.monthly_budget = monthly_budget
        self.alerts = []

    def log_call(self, model, input_tokens, output_tokens, cached_input_tokens=0, latency_ms=0, user_id="anonymous", cache_status="miss"):
        cost = calculate_cost(model, input_tokens, output_tokens, cached_input_tokens)
        entry = {
            "timestamp": time.time(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_input_tokens": cached_input_tokens,
            "latency_ms": latency_ms,
            "cost": cost["total_cost"],
            "user_id": user_id,
            "cache_status": cache_status,
        }
        self.logs.append(entry)
        self._check_budget()
        return entry

    def _check_budget(self):
        total = self.total_cost()
        pct = total / self.monthly_budget if self.monthly_budget > 0 else 0
        if pct >= 0.95 and not any(a["level"] == "stop" for a in self.alerts):
            self.alerts.append({"level": "stop", "message": f"Budget 95% consumed: ${total:.2f}/${self.monthly_budget:.2f}", "timestamp": time.time()})
        elif pct >= 0.85 and not any(a["level"] == "throttle" for a in self.alerts):
            self.alerts.append({"level": "throttle", "message": f"Budget 85% consumed: ${total:.2f}/${self.monthly_budget:.2f}", "timestamp": time.time()})
        elif pct >= 0.70 and not any(a["level"] == "warning" for a in self.alerts):
            self.alerts.append({"level": "warning", "message": f"Budget 70% consumed: ${total:.2f}/${self.monthly_budget:.2f}", "timestamp": time.time()})

    def total_cost(self):
        return round(sum(e["cost"] for e in self.logs), 6)

    def cost_by_model(self):
        by_model = {}
        for e in self.logs:
            m = e["model"]
            if m not in by_model:
                by_model[m] = {"calls": 0, "cost": 0, "input_tokens": 0, "output_tokens": 0}
            by_model[m]["calls"] += 1
            by_model[m]["cost"] = round(by_model[m]["cost"] + e["cost"], 6)
            by_model[m]["input_tokens"] += e["input_tokens"]
            by_model[m]["output_tokens"] += e["output_tokens"]
        return by_model

    def cache_savings(self):
        cache_hits = [e for e in self.logs if e["cache_status"] == "hit"]
        if not cache_hits:
            return {"saved": 0, "cache_hits": 0}
        saved = 0
        for e in cache_hits:
            full_cost = calculate_cost(e["model"], e["input_tokens"], e["output_tokens"])
            saved += full_cost["total_cost"]
        return {"saved": round(saved, 4), "cache_hits": len(cache_hits)}

    def summary(self):
        if not self.logs:
            return {"total_calls": 0, "total_cost": 0}
        total_latency = sum(e["latency_ms"] for e in self.logs)
        cache_hits = sum(1 for e in self.logs if e["cache_status"] == "hit")
        return {
            "total_calls": len(self.logs),
            "total_cost": self.total_cost(),
            "avg_cost_per_call": round(self.total_cost() / len(self.logs), 6),
            "avg_latency_ms": round(total_latency / len(self.logs), 1),
            "cache_hit_rate": round(cache_hits / len(self.logs), 4),
            "cost_by_model": self.cost_by_model(),
            "cache_savings": self.cache_savings(),
            "budget_remaining": round(self.monthly_budget - self.total_cost(), 2),
            "budget_utilization": round(self.total_cost() / self.monthly_budget, 4) if self.monthly_budget > 0 else 0,
            "alerts": self.alerts,
        }
```

> Log every call and compute running totals.

### Step 6: Model Router · 第 6 步：模型路由

把查询路由给能处理它的最便宜模型。

```python
SIMPLE_KEYWORDS = ["what time", "hours", "address", "phone", "price", "return policy", "hello", "hi", "thanks", "yes", "no"]
COMPLEX_KEYWORDS = ["analyze", "compare", "explain why", "write code", "debug", "architect", "design", "trade-off", "evaluate"]


def classify_complexity(query):
    q = query.lower()
    if len(q.split()) <= 5 or any(kw in q for kw in SIMPLE_KEYWORDS):
        return "simple"
    if any(kw in q for kw in COMPLEX_KEYWORDS):
        return "complex"
    return "medium"


def route_model(query, tier="pro"):
    complexity = classify_complexity(query)
    routing_table = {
        "simple": {"free": "gpt-4.1-nano", "pro": "gpt-4o-mini", "enterprise": "gpt-4o-mini"},
        "medium": {"free": "gpt-4o-mini", "pro": "claude-sonnet-4", "enterprise": "claude-sonnet-4"},
        "complex": {"free": "gpt-4o-mini", "pro": "gpt-4o", "enterprise": "claude-opus-4"},
    }
    model = routing_table[complexity].get(tier, "gpt-4o-mini")
    return {"query": query, "complexity": complexity, "model": model, "tier": tier}
```

> Route queries to the cheapest model that can handle them.

### Step 7: Run the Demo · 第 7 步：跑 Demo

```python
def simulate_llm_call(model, query):
    input_tokens = len(query.split()) * 4 + 500
    output_tokens = 150 + (len(query.split()) * 2)
    latency = 200 + (output_tokens * 2)
    return {
        "model": model,
        "response": f"[Simulated {model} response to: {query[:50]}...]",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency,
    }


def run_demo():
    print("=" * 60)
    print("  Caching, Rate Limiting & Cost Optimization Demo")
    print("=" * 60)

    print("\n--- Model Pricing ---")
    for model, pricing in list(MODEL_PRICING.items())[:6]:
        cost_1k = calculate_cost(model, 1000, 500)
        print(f"  {model}: ${cost_1k['total_cost']:.6f} per 1K in + 500 out")

    print("\n--- Cost Comparison: 100K Requests ---")
    for model in ["gpt-4o", "gpt-4o-mini", "claude-sonnet-4", "claude-haiku-3.5"]:
        cost = calculate_cost(model, 1000 * 100_000, 500 * 100_000)
        print(f"  {model}: ${cost['total_cost']:.2f}")

    print("\n--- Anthropic Cache Savings ---")
    no_cache = calculate_cost("claude-sonnet-4", 2000, 500, 0)
    with_cache = calculate_cost("claude-sonnet-4", 2000, 500, 1500)
    saving = no_cache["total_cost"] - with_cache["total_cost"]
    print(f"  Without cache: ${no_cache['total_cost']:.6f}")
    print(f"  With 1500 cached tokens: ${with_cache['total_cost']:.6f}")
    print(f"  Savings per call: ${saving:.6f} ({saving/no_cache['total_cost']*100:.1f}%)")

    exact_cache = ExactCache(max_size=100, ttl_seconds=300)
    semantic_cache = SemanticCache(similarity_threshold=0.75, max_size=100)
    rate_limiter = TokenBucketRateLimiter()
    tracker = CostTracker(monthly_budget=100.0)

    print("\n--- Exact Cache ---")
    messages_1 = [{"role": "user", "content": "What is the return policy?"}]
    result = exact_cache.get("gpt-4o-mini", messages_1, 0.0)
    print(f"  First lookup: {'HIT' if result else 'MISS'}")
    exact_cache.put("gpt-4o-mini", messages_1, 0.0, "You can return items within 30 days.")
    result = exact_cache.get("gpt-4o-mini", messages_1, 0.0)
    print(f"  Second lookup: {'HIT' if result else 'MISS'} -> {result}")
    result = exact_cache.get("gpt-4o-mini", messages_1, 0.7)
    print(f"  With temp=0.7: {'HIT' if result else 'MISS (non-deterministic, skip cache)'}")
    print(f"  Stats: {exact_cache.stats()}")

    print("\n--- Semantic Cache ---")
    test_queries = [
        ("What is the return policy?", "Items can be returned within 30 days with receipt."),
        ("How do I return an item?", None),
        ("What are your store hours?", "We are open 9am-9pm Monday through Saturday."),
        ("When does the store open?", None),
        ("Tell me about quantum computing", "Quantum computers use qubits..."),
        ("Explain quantum mechanics", None),
    ]
    for query, response in test_queries:
        cached = semantic_cache.get(query)
        if cached:
            print(f"  '{query[:40]}' -> CACHE HIT (sim={cached['similarity']}, original='{cached['original_query'][:40]}')")
        elif response:
            semantic_cache.put(query, response)
            print(f"  '{query[:40]}' -> MISS (stored)")
        else:
            print(f"  '{query[:40]}' -> MISS (no match)")
    print(f"  Stats: {semantic_cache.stats()}")

    print("\n--- Rate Limiting ---")
    for i in range(12):
        check = rate_limiter.check("user_1", 1000, "free")
        if check["allowed"]:
            rate_limiter.consume("user_1", 1000, "free")
        status = "OK" if check["allowed"] else f"BLOCKED ({check['reason']})"
        if i < 5 or not check["allowed"]:
            print(f"  Request {i+1}: {status}")
    print(f"  Usage: {rate_limiter.get_usage('user_1')}")

    print("\n--- Model Routing ---")
    routing_queries = [
        "What time do you close?",
        "Summarize this quarterly earnings report",
        "Analyze the trade-offs between microservices and monoliths",
        "Hello",
        "Write code for a binary search tree with deletion",
    ]
    for q in routing_queries:
        route = route_model(q, "pro")
        print(f"  '{q[:50]}' -> {route['model']} ({route['complexity']})")

    print("\n--- Full Pipeline: Before vs After Optimization ---")
    queries = [
        "What is the return policy?",
        "How do I return something?",
        "What are your hours?",
        "When do you open?",
        "Explain the difference between TCP and UDP",
        "Compare TCP vs UDP protocols",
        "Hello",
        "What is your phone number?",
        "Write a Python function to sort a list",
        "Analyze the pros and cons of serverless architecture",
    ]

    print("\n  [Before: no caching, single model (gpt-4o)]")
    tracker_before = CostTracker(monthly_budget=1000.0)
    for q in queries:
        result = simulate_llm_call("gpt-4o", q)
        tracker_before.log_call("gpt-4o", result["input_tokens"], result["output_tokens"], latency_ms=result["latency_ms"], cache_status="miss")
    before = tracker_before.summary()
    print(f"  Total cost: ${before['total_cost']:.6f}")
    print(f"  Avg cost/call: ${before['avg_cost_per_call']:.6f}")
    print(f"  Avg latency: {before['avg_latency_ms']}ms")

    print("\n  [After: caching + routing + rate limiting]")
    exact_c = ExactCache()
    semantic_c = SemanticCache(similarity_threshold=0.75)
    tracker_after = CostTracker(monthly_budget=1000.0)

    for q in queries:
        messages = [{"role": "user", "content": q}]
        cached = exact_c.get("gpt-4o", messages, 0.0)
        if cached:
            tracker_after.log_call("gpt-4o-mini", 0, 0, latency_ms=5, cache_status="hit")
            continue
        sem_cached = semantic_c.get(q)
        if sem_cached:
            tracker_after.log_call("gpt-4o-mini", 0, 0, latency_ms=15, cache_status="hit")
            continue
        route = route_model(q)
        result = simulate_llm_call(route["model"], q)
        tracker_after.log_call(route["model"], result["input_tokens"], result["output_tokens"], latency_ms=result["latency_ms"], cache_status="miss")
        exact_c.put(route["model"], messages, 0.0, result["response"])
        semantic_c.put(q, result["response"])

    after = tracker_after.summary()
    print(f"  Total cost: ${after['total_cost']:.6f}")
    print(f"  Avg cost/call: ${after['avg_cost_per_call']:.6f}")
    print(f"  Avg latency: {after['avg_latency_ms']}ms")
    print(f"  Cache hit rate: {after['cache_hit_rate']:.0%}")

    if before["total_cost"] > 0:
        savings_pct = (1 - after["total_cost"] / before["total_cost"]) * 100
        print(f"\n  SAVINGS: {savings_pct:.1f}% cost reduction")
        print(f"  Latency improvement: {(1 - after['avg_latency_ms'] / before['avg_latency_ms']) * 100:.1f}% faster")

    print("\n--- Budget Alerts Demo ---")
    alert_tracker = CostTracker(monthly_budget=0.01)
    for i in range(5):
        alert_tracker.log_call("gpt-4o", 5000, 2000, latency_ms=500)
    print(f"  Total spent: ${alert_tracker.total_cost():.6f} / ${alert_tracker.monthly_budget}")
    for alert in alert_tracker.alerts:
        print(f"  ALERT [{alert['level'].upper()}]: {alert['message']}")

    print("\n--- Cost Breakdown by Model ---")
    multi_tracker = CostTracker(monthly_budget=500.0)
    for _ in range(50):
        multi_tracker.log_call("gpt-4o-mini", 800, 200, latency_ms=150)
    for _ in range(30):
        multi_tracker.log_call("claude-sonnet-4", 1500, 500, latency_ms=400)
    for _ in range(10):
        multi_tracker.log_call("gpt-4o", 2000, 800, latency_ms=600)
    for _ in range(10):
        multi_tracker.log_call("claude-opus-4", 3000, 1000, latency_ms=1200)
    breakdown = multi_tracker.cost_by_model()
    for model, data in sorted(breakdown.items(), key=lambda x: x[1]["cost"], reverse=True):
        print(f"  {model}: {data['calls']} calls, ${data['cost']:.6f}, {data['input_tokens']:,} in / {data['output_tokens']:,} out")
    print(f"  Total: ${multi_tracker.total_cost():.6f}")

    print("\n" + "=" * 60)
    print("  Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
```

## Use It · 实战用法

### Anthropic Prompt Caching · Anthropic 提示词缓存

```python
# import anthropic
#
# client = anthropic.Anthropic()
#
# response = client.messages.create(
#     model="claude-sonnet-5",
#     max_tokens=1024,
#     system=[
#         {
#             "type": "text",
#             "text": "You are a helpful customer support agent for Acme Corp...",
#             "cache_control": {"type": "ephemeral"},
#         }
#     ],
#     messages=[{"role": "user", "content": "What is the return policy?"}],
# )
#
# print(f"Input tokens: {response.usage.input_tokens}")
# print(f"Cache creation tokens: {response.usage.cache_creation_input_tokens}")
# print(f"Cache read tokens: {response.usage.cache_read_input_tokens}")
```

第一次调用写入缓存（25% 溢价）。之后每次带相同系统提示词前缀的调用都从缓存读（90% 折扣）。缓存存活 5 分钟，每次命中都会重置计时器。

> The first call writes to the cache (25% premium). Every subsequent call with the same system prompt prefix reads from the cache (90% discount). The cache lasts 5 minutes and resets the timer on every hit.

### OpenAI Automatic Caching · OpenAI 自动缓存

```python
# from openai import OpenAI
#
# client = OpenAI()
#
# response = client.chat.completions.create(
#     model="gpt-4o",
#     messages=[
#         {"role": "system", "content": "You are a helpful customer support agent..."},
#         {"role": "user", "content": "What is the return policy?"},
#     ],
# )
#
# print(f"Prompt tokens: {response.usage.prompt_tokens}")
# print(f"Cached tokens: {response.usage.prompt_tokens_details.cached_tokens}")
# print(f"Completion tokens: {response.usage.completion_tokens}")
```

OpenAI 是自动缓存的。任何 1,024 token 以上、与近期请求匹配的提示词前缀都享受 50% 折扣。不需要改任何代码——查一下响应里的 `prompt_tokens_details.cached_tokens` 就能确认它生效了。

> OpenAI caches automatically. Any prompt prefix of 1,024+ tokens that matches a recent request gets a 50% discount. No code changes needed -- just check `prompt_tokens_details.cached_tokens` in the response to verify it is working.

### OpenAI Batch API · OpenAI Batch API

```python
# import json
# from openai import OpenAI
#
# client = OpenAI()
#
# requests = []
# for i, query in enumerate(queries):
#     requests.append({
#         "custom_id": f"request-{i}",
#         "method": "POST",
#         "url": "/v1/chat/completions",
#         "body": {
#             "model": "gpt-4o-mini",
#             "messages": [{"role": "user", "content": query}],
#         },
#     })
#
# with open("batch_input.jsonl", "w") as f:
#     for r in requests:
#         f.write(json.dumps(r) + "\n")
#
# batch_file = client.files.create(file=open("batch_input.jsonl", "rb"), purpose="batch")
# batch = client.batches.create(input_file_id=batch_file.id, endpoint="/v1/chat/completions", completion_window="24h")
# print(f"Batch ID: {batch.id}, Status: {batch.status}")
```

Batch API 对所有 token 一律 50% 折扣，24 小时内返回结果。适合一切非实时负载：评估、数据标注、批量摘要。

> Batch API gives a flat 50% discount on all tokens. Results arrive within 24 hours. Perfect for non-real-time workloads: evaluations, data labeling, bulk summarization.

### Production Semantic Cache with Redis · 用 Redis 搭生产级语义缓存

```python
# import redis
# import numpy as np
# from openai import OpenAI
#
# r = redis.Redis()
# client = OpenAI()
#
# def get_embedding(text):
#     response = client.embeddings.create(model="text-embedding-3-small", input=text)
#     return response.data[0].embedding
#
# def semantic_cache_lookup(query, threshold=0.95):
#     query_emb = np.array(get_embedding(query))
#     keys = r.keys("cache:emb:*")
#     best_sim, best_key = 0, None
#     for key in keys:
#         stored_emb = np.frombuffer(r.get(key), dtype=np.float32)
#         sim = np.dot(query_emb, stored_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(stored_emb))
#         if sim > best_sim:
#             best_sim, best_key = sim, key
#     if best_sim >= threshold and best_key:
#         response_key = best_key.decode().replace("cache:emb:", "cache:resp:")
#         return r.get(response_key).decode()
#     return None
```

生产环境里，把线性扫描换成向量索引（Redis Vector Search、Pinecone 或 pgvector）。1,000 条以内线性扫描够用；超过这个量，用 ANN（近似最近邻）拿到 O(log n) 的查找。

> In production, replace the linear scan with a vector index (Redis Vector Search, Pinecone, or pgvector). Linear scan works for <1,000 entries. Beyond that, use ANN (approximate nearest neighbor) for O(log n) lookup.

## Ship It · 交付

本课产出 `outputs/prompt-cost-optimizer.md`——一个可复用的提示词，分析你的 LLM 应用，给出具体的成本优化建议和预估节省。

它还产出 `outputs/skill-cost-patterns.md`——一个决策框架，帮你的用例选对缓存策略、限流配置和模型路由规则。

> This lesson produces `outputs/prompt-cost-optimizer.md` -- a reusable prompt that analyzes your LLM application and recommends specific cost optimizations with projected savings.
> It also produces `outputs/skill-cost-patterns.md` -- a decision framework for choosing the right caching strategy, rate limiting configuration, and model routing rules for your use case.

## Exercises · 练习

1. **给语义缓存实现 LRU 淘汰。** 把「最旧优先」的淘汰策略换成最近最少使用（LRU）。记录每个条目的最后访问时间，缓存满时淘汰访问时间最旧的条目。对比两种策略在 100 次查询上的命中率。

2. **做一个成本预测工具。** 给定一份 API 调用日志（CostTracker 的日志），按最近 7 天的平均值预测月成本，并考虑工作日/周末模式。如果预测月成本超出预算 20% 以上，触发告警。

3. **实现分层语义缓存。** 用两个相似度阈值：0.98 用于高置信命中（直接返回），0.90 用于中置信命中（带免责声明返回：「基于一个相似的过往问题……」）。记录每次命中来自哪一层，并测量用户满意度差异。

4. **建一个模型路由分类器。** 把基于关键词的分类器换成基于嵌入的。嵌入 50 条带标签的查询（simple/medium/complex），然后通过找最近的带标签样本来分类新查询。在 20 条查询的测试集上测分类准确率。

5. **实现带降级档位的熔断器。** 预算到 70%，记录一条警告。到 85%，自动把所有路由切到最便宜模型（gpt-4o-mini）。到 95%，只服务缓存响应、拒绝新查询。用 $1.00 预算模拟 1,000 个请求来测试，验证每个阈值都正确触发。

## Key Terms · 术语表

| Term | 大家怎么说 | 实际含义 |
|------|----------------|----------------------|
| Prompt caching | 「缓存系统提示词」 | 提供商层缓存，重复的提示词前缀享受折扣（Anthropic 90%、OpenAI 50%）——OpenAI 无需改代码，Anthropic 需要显式标记 |
| Semantic caching | 「聪明缓存」 | 把查询做嵌入、与过往查询算相似度、相似度超阈值就返回缓存的响应——能抓住精确匹配漏掉的换说法 |
| Exact caching | 「哈希缓存」 | 对完整提示词（模型 + 消息 + 温度）做哈希，一模一样的输入返回缓存响应——只适用于 temperature=0 的确定性调用 |
| Token bucket | 「限流器」 | 每个用户有一个装 N 个 token 的桶、以每秒 R 个的速度补充——允许最多 N 的突发，同时约束平均速率 R |
| Model routing | 「抠门路由」 | 用分类器把简单查询发给便宜模型（GPT-4o-mini、Haiku）、把复杂查询发给贵模型（GPT-4o、Opus）——模型成本省 40-70% |
| Cost tracking | 「计量」 | 记录每次 API 调用的模型、token、延迟、成本和用户 ID，让你确切知道钱花在哪、哪些功能烧钱 |
| Circuit breaker | 「kill switch」 | 当花费逼近预算上限时自动降级服务（切便宜模型、只走缓存）或直接停止请求 |
| Batch API | 「批发折扣」 | OpenAI 的 50% 折扣异步处理——最多提交 50,000 个请求，24 小时内拿到结果 |
| Prompt compression | 「给 token 减肥」 | 重写系统提示词和上下文，在保住含义的前提下用更少 token——更短的提示词更便宜，而且往往表现更好 |
| Cache hit rate | 「缓存效率」 | 请求由缓存服务、而不是调用 LLM 的比例——生产聊天机器人典型为 40-60%，成本按比例下降 |

## Further Reading · 延伸阅读

- [Anthropic Prompt Caching Guide](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) —— Anthropic 显式 cache_control 标记、定价与缓存存活行为的官方文档
- [OpenAI Prompt Caching](https://platform.openai.com/docs/guides/prompt-caching) —— OpenAI 自动缓存，如何通过 usage 字段验证缓存命中，以及最小前缀长度
- [OpenAI Batch API](https://platform.openai.com/docs/guides/batch) —— 异步处理 50% 折扣、JSONL 格式、24 小时完成窗口、5 万请求上限
- [GPTCache](https://github.com/zilliztech/GPTCache) —— 开源语义缓存库，支持多种嵌入后端、向量库和淘汰策略
- [Martian Model Router](https://docs.withmartian.com) —— 生产级模型路由，自动为每个查询挑选能胜任的最便宜模型
- [Not Diamond](https://www.notdiamond.ai) —— 基于机器学习的模型路由，从你的流量模式中学习，跨提供商优化成本/质量权衡
- [Helicone](https://www.helicone.ai) —— LLM 可观测性平台，以代理层形式提供成本追踪、缓存、限流和预算告警
- [Dean & Barroso, "The Tail at Scale" (CACM 2013)](https://research.google/pubs/the-tail-at-scale/) —— 延迟、吞吐、TTFT/TPOT 百分位与对冲请求；「选还满足 P95 的最便宜模型」背后的成本模型。
- [Kwon et al., "Efficient Memory Management for Large Language Model Serving with PagedAttention" (SOSP 2023)](https://arxiv.org/abs/2309.06180) —— vLLM 论文；为什么分页 KV-cache + 连续批处理能把吞吐做到朴素服务器的 24 倍，「缓存与成本」下面的那层基础设施。
- [Dao et al., "FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning" (ICLR 2024)](https://arxiv.org/abs/2307.08691) —— 与提示词缓存正交的内核级降本；配合投机解码和 GQA 一起读，才是完整的成本曲线图。
