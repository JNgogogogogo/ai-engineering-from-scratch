# Production Serving Stack — KV Offloading and Cache-Aware Routing · 生产级服务栈 —— KV 卸载与缓存感知路由

> 一套生产级服务栈把路由器、引擎和可观测性接成一个 Kubernetes 部署——并把 KV cache 当作一种可以离开 GPU 的资源来对待。KV 卸载（KV offloading）把 KV cache 从 GPU 显存里抽出来，在查询和引擎之间复用（先 CPU DRAM，再磁盘/Ceph）。vLLM 的 production-stack 是参考部署；LMCache 是卸载层。vLLM 0.11.0 的 KV Offloading Connector（2026 年 1 月）让这一切变成异步、可插拔（经 Connector API，v0.9.0+）。卸载路径通常对请求路径不可见，但缓存未命中和提升（promotion）仍可能增加端到端延迟。即便没有共享前缀，LMCache 也有价值——当 GPU 的 KV 槽位耗尽时，被抢占的请求可以从 CPU 恢复，而不是重新计算 prefill。已发表的基准在 4 台 a3-highgpu-4g 上的 16x H100（80GB HBM）进行：当 KV cache 超出 HBM 时，原生 CPU 卸载和 LMCache 都能大幅提升吞吐；KV 占用低时，所有配置与基线持平，只有少量开销。

> A production serving stack wires router, engines, and observability into one Kubernetes deployment — and treats KV cache as a resource that can leave the GPU. KV offloading extracts KV cache out of GPU memory and reuses it across queries and engines (CPU DRAM, then disk/Ceph). vLLM's production-stack is the reference deployment; LMCache is the offloading layer. The vLLM 0.11.0 KV Offloading Connector (January 2026) makes this asynchronous and pluggable via the Connector API (v0.9.0+). The offload path is usually hidden from the request path, though cache misses and promotions can add end-to-end latency. LMCache is valuable even without shared prefixes — when a GPU runs out of KV slots, preempted requests can be restored from CPU instead of recomputing prefill. Published benchmarks on 16x H100 (80GB HBM) across 4 a3-highgpu-4g: when KV cache exceeds HBM, both native CPU offload and LMCache substantially improve throughput; at low KV footprint, all configs match baseline with small overhead.

**Type:** Learn
**Languages:** Python (stdlib, toy KV-spill simulator)
**Prerequisites:** Phase 17 · 04 (Serving Engine Internals), Phase 17 · 06 (SGLang/RadixAttention)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 画出 vLLM production-stack 的分层：路由器、引擎、KV 卸载、可观测性。
- 解释 KV Offloading Connector API（v0.9.0+），以及 0.11.0 的异步路径如何隐藏卸载延迟。
- 量化 LMCache 的 CPU-DRAM 何时有帮助（KV > HBM）、何时只添开销（KV 小到能装进 HBM）。
- 在给定部署约束时，在原生 vLLM CPU 卸载和 LMCache connector 之间做选择。

> Diagram the vLLM production-stack layers: router, engines, KV offload, observability.
> Explain the KV Offloading Connector API (v0.9.0+) and how the 0.11.0 asynchronous path hides offload latency.
> Quantify when LMCache CPU-DRAM helps (KV > HBM) vs adds overhead (KV small enough to fit HBM).
> Pick between native vLLM CPU offload and LMCache connector given deployment constraints.

## The Problem · 问题在哪

你的 vLLM 服务显示 GPU 的 HBM 占用 100%，并发一爬升就出现抢占（preemption）事件。请求被驱逐、重新排队，同一条 2K token 的提示你一分钟内重新 prefill 了四次。GPU 算力花在冗余 prefill 上；goodput 远低于原始吞吐。

加 GPU 成本线性上升。加 HBM 做不到。但 CPU DRAM 便宜——一个 socket 有 512 GB+，延迟比 HBM 差几个数量级，但对「暂时保温」的 KV cache 来说足够了。

LMCache 把 KV cache 抽到 CPU DRAM，被抢占的请求就能快速恢复，跨引擎的重复前缀也能共享缓存而不必各自重新 prefill。

> Your vLLM serving shows GPUs at 100% HBM with preemption events whenever concurrency climbs. Requests get evicted, requeued, and you re-prefill the same 2K-token prompt four times in a minute. GPU compute is spent on redundant prefills; goodput is well below raw throughput.
> Adding more GPUs costs linearly. Adding more HBM is not possible. But CPU DRAM is cheap — one socket has 512 GB+ at latency orders of magnitude worse than HBM but fine for "temporarily warm" KV cache.
> LMCache extracts KV cache to CPU DRAM so preempted requests recover fast, and repeated prefixes across engines share cache without each engine re-prefilling.

## The Concept · 概念

### vLLM production-stack · vLLM 生产栈

`github.com/vllm-project/production-stack` 是参考 Kubernetes 部署：

- **Router** —— 缓存感知（Phase 17 · 11）。消费 KV 事件。
- **Engines** —— vLLM worker。每 GPU 一个，或每 TP/PP 组一个。
- **KV cache offload** —— LMCache 部署或原生 connector。
- **Observability** —— Prometheus 抓取、Grafana 面板、OTel 追踪。
- **Control plane** —— 服务发现、配置、滚动更新。

以 Helm chart + operator 交付。

> `github.com/vllm-project/production-stack` is the reference Kubernetes deployment: **Router** — cache-aware (Phase 17 · 11). Consumes KV events. **Engines** — vLLM workers. One per GPU or per TP/PP group. **KV cache offload** — LMCache deployment or native connector. **Observability** — Prometheus scrape, Grafana dashboards, OTel traces. **Control plane** — service discovery, config, rolling updates. ... Shipped as Helm chart + operator.

### The KV Offloading Connector API (v0.9.0+) · KV 卸载 Connector API（v0.9.0+）

vLLM 0.9.0 引入了面向可插拔 KV cache 后端的 Connector API。引擎把 block 卸载给 connector；connector 负责存储（RAM、磁盘、对象存储、LMCache）。请求需要某个 block 时，connector 再把它装回来。

vLLM 0.11.0（2026 年 1 月）增加了异步卸载路径——卸载可以在后台进行，常见情况下引擎不必阻塞等待。端到端延迟和吞吐仍取决于工作负载形态、KV cache 命中率和系统压力；vLLM 自己的说明就指出：低命中率下自定义内核卸载可能拉低吞吐，且异步调度与投机解码（speculative decoding）之间存在已知的交互问题。

> vLLM 0.9.0 introduced a Connector API for pluggable KV cache backends. Your engine offloads blocks to the connector; connector stores them (RAM, disk, object storage, LMCache). Request needs a block, connector loads it back.
> vLLM 0.11.0 (January 2026) adds an asynchronous offload path — offload can happen in the background so the engine does not block on it in the common case. End-to-end latency and throughput still depend on workload shape, KV cache hit rate, and system pressure; vLLM's own notes call out that custom-kernel offload can degrade throughput at low hit rates and that async scheduling has known interaction issues with speculative decoding.

### Native CPU offload vs LMCache · 原生 CPU 卸载与 LMCache 的取舍

**原生 vLLM CPU 卸载**：引擎本地。KV block 存在主机 RAM 里。实现快、零网络跳数。不跨引擎。

**LMCache connector**：集群规模。block 存在共享的 LMCache 服务里（CPU DRAM + Ceph/S3 层）。任何引擎都能访问这些 block。有 16x H100 的公开基准。

单一引擎有 HBM 压力时选原生。多个引擎共享前缀时（共享系统提示的 RAG、共享模板的多租户）选 LMCache。

> **Native vLLM CPU offload**: engine-local. Stores KV blocks in host RAM. Fast to implement, zero network hop. Does not cross engines.
> **LMCache connector**: cluster-scale. Stores blocks in a shared LMCache server (CPU DRAM + Ceph/S3 tier). Blocks are accessible to any engine. 16x H100 benchmarks published.
> Pick native when a single engine has HBM pressure. Pick LMCache when multiple engines share prefixes (RAG with common system prompts, multi-tenant with shared templates).

### Benchmark behavior · 基准表现

16x H100（80 GB HBM）分布在 4 台 a3-highgpu-4g 上的测试：

- 低 KV 占用（短提示、低并发）：所有配置与基线持平，LMCache 增加约 3-5% 开销。
- 中等占用：LMCache 开始在跨引擎前缀复用上产生收益。
- KV 超过 HBM：原生 CPU 卸载和 LMCache 都显著提升吞吐；LMCache 收益更大，因为有跨引擎共享。

> The 16x H100 (80 GB HBM) spread across 4 a3-highgpu-4g test: Low KV footprint (short prompts, low concurrency): all configs match baseline, LMCache adds ~3-5% overhead. Moderate footprint: LMCache starts to help on prefix reuse across engines. KV exceeds HBM: native CPU offload and LMCache both improve throughput substantially; LMCache larger gain because cross-engine sharing.

### When LMCache is decisive · LMCache 何时是决定性的

- 系统提示跨租户共享的多租户服务。
- 文档分块在查询间反复出现的 RAG。
- 同一底座上的微调变体（LoRA）：底座模型 KV 复用削减冗余工作。
- 抢占频发的负载：从 CPU 恢复比重新 prefill 便宜。

> Multi-tenant serving where system prompts are shared across tenants. RAG where document chunks repeat across queries. Fine-tuned variants (LoRA) on the same base where base-model KV reuse cuts redundant work. Preemption-heavy workloads: restore from CPU cheaper than re-prefill.

### When NOT to enable · 什么时候不要开

- HBM 压力小——你付了开销却没有收益。
- 短上下文（<1K token）——传输时间 > 重新 prefill。
- 单租户单提示负载——没有可捕获的复用。

> Small HBM pressure — you pay overhead without benefit. Short contexts (<1K tokens) — transfer time > re-prefill. Single-tenant single-prompt workload — no reuse to capture.

### Integration with disaggregated serving · 与分离式服务的集成

Phase 17 · 17 分离式服务 + LMCache 相互放大：从 prefill 池传到 decode 池、暂时没被用掉的 KV 会落进 LMCache；后续查询直接从 LMCache 取。Phase 17 · 11 缓存感知路由器可以路由到本地缓存或 LMCache 共享缓存命中的那个引擎。

> Phase 17 · 17 disaggregated serving + LMCache compounds: KV transfers from prefill pool to decode pool land in LMCache if not used; subsequent queries pull from LMCache. Phase 17 · 11 cache-aware router can route to the engine whose local OR LMCache-shared cache matches.

### Numbers you should remember · 你该记住的数字

- vLLM 0.9.0：Connector API 发布。
- vLLM 0.11.0（2026 年 1 月）：异步卸载路径；端到端延迟影响取决于工作负载、KV 命中率和系统压力（不是绝对保证）。
- 16x H100 基准：KV 占用超过 HBM 时 LMCache 有帮助。
- HBM 压力小：3-5% 开销、无收益。

```figure
zero-sharding
```

> vLLM 0.9.0: Connector API shipped. vLLM 0.11.0 (Jan 2026): asynchronous offload path; end-to-end latency impact depends on workload, KV hit rate, and system pressure (not an absolute guarantee). 16x H100 benchmark: LMCache helps when KV footprint exceeds HBM. Small HBM pressure: 3-5% overhead without benefit.

## Use It · 实战用法

`code/main.py` 模拟带与不带 LMCache 的抢占频发负载。报告避免的重新 prefill 次数、吞吐增益和盈亏平衡的 HBM 利用率。

> `code/main.py` simulates a preemption-heavy workload with and without LMCache. Reports re-prefills avoided, throughput gain, and the break-even HBM utilization.

## Ship It · 交付

本课产出 `outputs/skill-vllm-stack-decider.md`。给定工作负载形态和 vLLM 部署，它在原生、LMCache、都不用之间做决定。

> This lesson produces `outputs/skill-vllm-stack-decider.md`. Given workload shape and vLLM deployment, decides native vs LMCache vs neither.

## Exercises · 练习

1. 跑 `code/main.py`。HBM 利用率到多少时 LMCache 开始划算？
2. 一个租户以 200 次查询/小时的频率共享一条 6K token 系统提示。计算每租户的期望 LMCache 节省。
3. LMCache 服务是单点故障。设计 HA 策略（副本、回退到原生）。
4. LMCache 存到机械盘上的 Ceph。对 70B FP8 的一条 4K token KV（500 MB），读取时间与重新 prefill 相比如何？
5. 论证 vLLM 0.11.0 的异步路径是不是「免费」的——开销藏在哪里？

> 1. Run `code/main.py`. At what HBM utilization does LMCache start paying? ... 3. The LMCache server is a single point of failure. Design the HA strategy (replicas, fallback to native). ... 5. Argue whether the vLLM 0.11.0 asynchronous path is "free" — where does the overhead hide?

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|------------|----------|
| Production-stack | 「参考部署」 | vLLM 的 Kubernetes Helm chart + operator |
| Connector API | 「KV 后端接口」 | vLLM 0.9.0+ 的可插拔 KV 存储接口 |
| Native CPU offload | 「引擎本地卸载」 | 把 KV 存进同一引擎的主机 RAM |
| LMCache | 「集群级 KV cache」 | 跑在 CPU DRAM + 磁盘上的跨引擎 KV cache 服务 |
| 0.11.0 async | 「非阻塞卸载」 | 卸载隐藏在引擎流式处理之后 |
| Preemption | 「驱逐腾地方」 | HBM 满时的 KV cache 腾挪 |
| Prefix reuse | 「同一条系统提示」 | 多个查询共享开头；缓存命中 |
| Ceph tier | 「磁盘层」 | 缓存层级里 DRAM 之下的持久存储 |

## Further Reading · 延伸阅读

- [vLLM Blog — KV Offloading Connector (Jan 2026)](https://blog.vllm.ai/2026/01/08/kv-offloading-connector.html)
- [vLLM Production Stack GitHub](https://github.com/vllm-project/production-stack) —— Helm chart + operator。
- [LMCache for Enterprise-Scale LLM Inference (arXiv:2510.09665)](https://arxiv.org/html/2510.09665v2)
- [LMCache GitHub](https://github.com/LMCache/LMCache) —— Connector 实现。
- [vLLM 0.11.0 release notes](https://github.com/vllm-project/vllm/releases) —— 异步路径细节。
