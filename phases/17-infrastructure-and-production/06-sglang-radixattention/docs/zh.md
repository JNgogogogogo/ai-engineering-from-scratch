# Prefix-Cache Serving — RadixAttention and KV Reuse · 前缀缓存 Serving —— RadixAttention 与 KV 复用

> 把 KV cache 当作存储在 radix tree（基数树）里的一等可复用资源，调度也随之改变：不再是 vLLM 那样的 FCFS（first-come, first-served，先来先服务），cache 感知的调度器优先处理共享前缀更长的请求——实质上是一次深度优先的 radix 遍历，让热的分支常驻 HBM。SGLang 就是围绕这个想法构建 serving 的引擎。Llama 3.1 8B 配 ShareGPT 风格的 1K 提示词，SGLang 跑出约 16,200 tok/s，vLLM 约 12,500，领先约 29%。前缀密集的 RAG 负载上优势达到 6.4 倍。语音克隆形态的负载上缓存命中率突破 86%。2026 年部署在 400,000+ 块 GPU 上，横跨 xAI、LinkedIn、Cursor、Oracle、GCP、Azure、AWS。坑在于：前缀顺序不一致时，6.4 倍这个数字会蒸发——顺序是工程师手里的杠杆。

> Treat the KV cache as a first-class, reusable resource stored in a radix tree, and scheduling changes with it: instead of FCFS (first-come, first-served) as vLLM schedules, a cache-aware scheduler prioritizes requests with longer shared prefixes — effectively a depth-first radix traversal so hot branches stay resident in HBM. SGLang is the engine that built serving around this idea. On Llama 3.1 8B with ShareGPT-like 1K prompts, SGLang hits ~16,200 tok/s to vLLM's ~12,500, a ~29% edge. On prefix-heavy RAG workloads the advantage reaches 6.4x. On voice-cloning-shaped workloads cache hit rate cleared 86%. Deployed on 400,000+ GPUs in 2026 across xAI, LinkedIn, Cursor, Oracle, GCP, Azure, AWS. The gotcha is that the 6.4x number evaporates when prefix ordering is inconsistent — ordering is the engineer's lever.

**Type:** Learn
**Languages:** Python (stdlib, toy radix-tree cache + cache-aware scheduler)
**Prerequisites:** Phase 17 · 04 (Serving Engine Internals), Phase 14 (Agentic RAG)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 画出 RadixAttention：前缀如何存进 radix tree，KV block 如何在同一分支根下的多个序列间共享。
- 解释 cache 感知调度，以及为什么前缀密集的流量上 FCFS 是错的。
- 给定前缀缓存命中率和提示词长度分布，计算一个负载的期望加速比。
- 说出让 6.4 倍成为现实（而不是错失的上限）的提示词顺序纪律。

> Diagram RadixAttention: how prefixes are stored in a radix tree and how KV blocks are shared across sequences rooted at the same branch.
> Explain cache-aware scheduling and why FCFS is wrong for prefix-heavy traffic.
> Compute expected speedup for a workload given prefix-cache hit rate and prompt length distribution.
> Name the prompt-ordering discipline that makes the 6.4x number real vs a lost upside.

## The Problem · 问题在哪

经典 serving 把每个请求的提示词当成不透明的东西。哪怕 5,000 个 RAG 请求全都以同一个 2,000-token 的 system prompt 加同一段检索前言开头，vLLM 也会把这 2,000-token 的前缀 prefill 5,000 次。GPU 把同样的活一遍遍地重做。

关键观察：agentic 和 RAG 负载里的提示词几乎总是共享长前缀。System prompt、工具 schema、few-shot 示例、检索头部、对话历史——全都在请求之间重复。如果你把这段前缀的 KV cache 存一次然后复用，就根本不用再 prefill 它。

RadixAttention 干的正是这件事。Token 被索引进一棵 radix tree；每个节点拥有「从根到它的路径上那段 token 序列」的 KV block。新请求走一遍树：任何 token 匹配的节点都复用该节点的 KV block。Prefill 成本变得正比于「新的」后缀，而不是完整提示词。

挑战在调度。如果两个请求共享一个 2,000-token 前缀，第三个只共享同一前缀的 200 个 token，你会希望把那两个长共享请求放在一起服务，让长前缀留在 HBM 里。FCFS 反着来——谁先来服务谁，可能在前一个长前缀请求到达之前就把热的分支逐出了。

> Classic serving treats each request's prompt as opaque. Even when 5,000 RAG requests all start with the same 2,000-token system prompt plus same retrieval preamble, vLLM prefills that 2,000-token prefix 5,000 times. The GPU does the same work over and over.
> The observation: prompts in agentic and RAG workloads share long prefixes almost always. ... RadixAttention does exactly this. ... The challenge is scheduling. If two requests share a 2,000-token prefix and a third shares only 200 tokens of the same prefix, you want to serve the two long-shared requests together so the long prefix stays in HBM. FCFS does the opposite — it serves whoever arrived first, potentially evicting the hot branch before the next long-prefix request hits.

## The Concept · 概念

### The radix tree as a KV index · radix tree：KV 的索引

radix tree（压缩 trie）存储 token 序列。每个节点拥有一段 token 区间和为这段区间算好的 KV block。子节点把序列延长一个或多个 token。

```
root
 |- "You are a helpful assistant..."  (2,000 tokens, 124 KV blocks)
      |- "Context: <doc A>..."        (500 tokens, 31 blocks)
           |- "Question: Alice..."    (80 tokens, 5 blocks)
           |- "Question: Bob..."      (95 tokens, 6 blocks)
      |- "Context: <doc B>..."        (520 tokens, 33 blocks)
```

一个新请求带着 system prompt + "Context: <doc A>" + "Question: Carol" 进来。调度器走树：system 前缀命中（复用 124 个 block），doc-A 分支命中（复用 31 个 block），然后只为 "Question: Carol" 分配新 block（4 个）。Prefill 成本：4 个 block 的新 token。没有树的话：160 个 block。Prefill 省了约 40 倍。

> A radix tree (compact trie) stores token sequences. Each node owns a token range and the KV blocks computed for that range. Children extend the sequence one or more tokens. ... A new request comes in with system prompt + "Context: <doc A>" + "Question: Carol". The scheduler walks: system prefix matches (124 blocks reused), doc-A branch matches (31 blocks reused), then allocates fresh blocks only for "Question: Carol" (4 blocks). Prefill cost: 4 blocks of new tokens. Without the tree: 160 blocks. ~40x savings on prefill.

### Cache-aware scheduling · cache 感知调度

如果 cache 一直被冲刷，radix tree 支撑的复用就毫无意义。两条关键策略：

1. **深度优先派发**。从队列挑下一个请求时，优先选和当前运行集合同根分支的请求。这让热的分支被钉住。
2. **分支级 LRU，不是 block 级**。整枝逐出（从最少使用的叶子开始），而不是逐个 block，让 cache 的形状匹配 radix 的形状。

FCFS 两条都违反。一个共享 2,000 token 的请求排在一个共享 50 token 的请求后面，然后那根 2,000-token 的分支被逐出，就为了塞进那个 50-token 的请求。

> Radix-tree-backed reuse is pointless if the cache churns. Two key policies:
> 1. **Depth-first dispatch**. When picking the next request from the queue, prefer requests rooted at the same branch as the current running set. This keeps the hot branch pinned.
> 2. **LRU at branch level, not block level**. Evict whole branches (starting from shortest-used leaves) rather than individual blocks, so cache shape matches radix shape.
> FCFS violates both. A request sharing 2,000 tokens sits behind a request sharing 50, then the 2,000-token branch gets evicted to admit the 50-token one.

### Benchmark numbers you should memorize · 你该背下来的基准数字

- Llama 3.1 8B、H100、ShareGPT 1K 提示词：SGLang 约 16,200 tok/s 对 vLLM 约 12,500（领先约 29%）。
- 前缀密集 RAG（同 system + 同文档，问题不同）：SGLang 上最高 6.4 倍。
- 语音克隆负载：86.4% 前缀缓存命中率。
- SGLang 客户的生产命中率：50-99%，取决于提示词纪律。
- 2026 年部署在 400,000+ 块 GPU 上。

> - Llama 3.1 8B, H100, ShareGPT 1K prompts: SGLang ~16,200 tok/s vs vLLM ~12,500 (~29% edge).
> - Prefix-heavy RAG (same system + same doc, varying question): up to 6.4x on SGLang.
> - Voice cloning workloads: 86.4% prefix-cache hit rate.
> - Production hit rates across SGLang customers: 50-99% depending on prompt discipline.
> - Deployed on 400,000+ GPUs in 2026.

### The ordering gotcha · 顺序的坑

6.4 倍这个数字依赖一致的提示词模板顺序。如果你的客户端在一些请求里把提示词构造成 `[system, tools, context, history, question]`，在另一些里构造成 `[system, context, tools, history, question]`，树就找不到共享前缀。在人眼里是共享前缀的东西，在 radix tree 眼里是两条不同的序列。

工程师的杠杆：你的提示词模板就是缓存键。固定顺序。所有不可变的内容（system、tools、schemas）放最前面。检索上下文放其次。用户问题放最后。不要把动态内容插进前缀里。

研究里的真实案例：把动态内容挪出可缓存前缀，一次改动就把一个部署的缓存命中率从 7% 提到 74%。

> The 6.4x number relies on consistent prompt-template ordering. If your client constructs prompts as `[system, tools, context, history, question]` in some requests and `[system, context, tools, history, question]` in others, the tree cannot find the shared prefix. What looks like a shared prefix to a human is two distinct sequences to the radix tree.
> Engineer's lever: your prompt template is a cache key. Fix the order. Put everything immutable (system, tools, schemas) first. Put retrieval context next. Put user question last. Do not interleave dynamic content into the prefix.
> Real case from the research: moving dynamic content out of the cacheable prefix took one deployment from 7% to 74% cache hit rate in one change.

### Where RadixAttention wins and loses · RadixAttention 在哪赢、在哪输

赢的场景：
- RAG（同一段检索前言，问题不同）。
- Agent（同一套工具 schema，查询不同）。
- 带长 system prompt 的聊天。
- 带重复前导的语音 / 视觉负载。

输的场景（回落到 vLLM 级吞吐）：
- 提示词各不相同的单发生成（代码补全、没有 system prompt 的开放式聊天）。
- 每个请求都往前缀里塞独特内容的动态提示词。

> Wins:
> - RAG (same retrieval preamble, varying question).
> - Agents (same tool schemas, varying query).
> - Chat with long system prompt.
> - Voice / vision workloads with repeated preambles.
> Loses (returns to vLLM-level throughput):
> - Single-shot generation with unique prompts (code completion, open-ended chat without system prompt).
> - Dynamic prompts where every request interleaves unique content into the prefix.

### Why this is a scheduler problem, not just a kernel problem · 为什么这是调度器问题，不只是 kernel 问题

你可以把 KV 复用做成一个 kernel 技巧。SGLang 的洞见是：只有调度器让热分支常驻，复用才划算。天真的「有就复用」策略会在混合负载下把 cache 冲刷掉。radix-tree 索引的调度器，才是把 kernel 技巧变成 29% 生产优势的那一环。

> You can implement KV reuse as a kernel trick. SGLang's insight is that reuse only pays if the scheduler keeps the hot branch resident. A naive "reuse if available" policy will churn the cache under mixed load. The radix-tree-indexed scheduler is what turns the kernel trick into a 29% production edge.

### Interplay with vLLM · 与 vLLM 的互动

两套系统不是严格意义上的对手。2026 年 vLLM 加上了前缀缓存（`--enable-prefix-caching`）和一个 cache 感知的路由器（Rust 写的 vLLM Router）。差距缩小了但没有消失——SGLang 的整个栈是 radix 优先的；vLLM 是后来嫁接的。前缀复用主导的负载，SGLang 仍是默认选择。没有强前缀模式的通用 serving，vLLM 依旧持平或更好。

> The two systems are not strict competitors. In 2026 vLLM added prefix caching (`--enable-prefix-caching`) and a cache-aware router (vLLM Router in Rust). The gap closed but did not fully disappear — SGLang's whole stack is radix-first; vLLM grafted it on. For workloads dominated by prefix reuse, SGLang remains the default. For general-purpose serving without strong prefix patterns, vLLM remains equal or better.

```figure
roofline
```

## Use It · 实战用法

`code/main.py` 实现一个玩具 radix-tree KV cache 加一个带两种策略的调度器：FCFS 和 cache 感知。把同一个负载分别跑过两者，报告前缀缓存命中率和吞吐差。然后跑一个「顺序打乱」的负载，展示 6.4 倍如何崩塌。

> `code/main.py` implements a toy radix-tree KV cache plus a scheduler with two policies: FCFS and cache-aware. Runs the same workload through both, reports prefix-cache hit rate and throughput delta. Then runs a "scrambled ordering" workload to show the 6.4x collapse.

## Ship It · 交付

本课产出 `outputs/skill-radix-scheduler-advisor.md`。给定负载描述（提示词模板形状、检索模式、并发租户数），它产出一份提示词顺序处方，以及一个是否采用 SGLang 的 go/no-go 结论。

> This lesson produces `outputs/skill-radix-scheduler-advisor.md`. Given a workload description (prompt-template shape, retrieval pattern, number of concurrent tenants), it produces a prompt-ordering prescription and a go/no-go for SGLang adoption.

## Exercises · 练习

1. 运行 `code/main.py`。在同一个负载上对比 FCFS 和 cache 感知。差值来自哪——prefill 节省、decode 节省，还是排队延迟？
2. 修改负载，让提示词随机打乱 `[system, tools, context]` 的顺序。重跑。命中率发生了什么？为什么？
3. 计算在 Llama 3.1 8B 上把一个 2,000-token system prompt 作为一条 radix 分支常驻的 HBM 成本。和没有前缀复用时一个 16 序列 batch 的成本比呢？
4. 阅读 SGLang RadixAttention 论文。用三句话解释为什么前缀密集负载下树形 LRU 逐出胜过 block 形 LRU。
5. 客户报告缓存命中率只有 8%。说出三个可能原因，以及你会为每个原因跑的诊断。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| RadixAttention | "SGLang 的那套东西" | KV cache 以 radix tree 索引，共享前缀复用 block |
| Radix tree | "压缩 trie" | 每个节点拥有一段 token 区间及其 KV block 的树 |
| Cache-aware scheduler | "热分支优先" | 优先服务共享常驻分支请求的调度器 |
| Prefix-cache hit rate | "你的提示词有多少是免费的" | 从复用 KV block 服务的提示词 token 比例 |
| FCFS | "先来先服务" | 破坏前缀局部性的默认调度 |
| Branch-level LRU | "逐出叶子" | 与 radix 形状匹配的逐出策略 |
| Prompt template ordering | "缓存键" | 提示词组件的顺序决定树能共享什么 |
| System prompt pinning | "常驻前缀" | 把不可变的 system 部分钉住，避免逐出抖动 |

## Further Reading · 延伸阅读

- [SGLang GitHub](https://github.com/sgl-project/sglang) —— 源码与文档。
- [SGLang documentation](https://sgl-project.github.io/) —— RadixAttention 与调度细节。
- [SGLang paper — Efficiently Programming Large Language Models (arXiv:2312.07104)](https://arxiv.org/abs/2312.07104) —— 设计参考。
- [LMSYS blog — SGLang with RadixAttention](https://www.lmsys.org/blog/2024-01-17-sglang/) —— 基准数字与调度器设计动机。
- [vLLM — Prefix Caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/) —— vLLM 自己的类 radix 实现，可作对比。
