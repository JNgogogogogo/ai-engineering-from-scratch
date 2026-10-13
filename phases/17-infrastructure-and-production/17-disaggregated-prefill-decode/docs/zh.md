# Disaggregated Prefill/Decode — NVIDIA Dynamo and llm-d · 分离式 prefill/decode —— NVIDIA Dynamo 与 llm-d

> Prefill 是计算受限（compute-bound）的；decode 是内存受限（memory-bound）的。把两者跑在同一块 GPU 上，总有一种资源在被浪费。分离式（disaggregation）把它们拆到独立的资源池，并通过 NIXL（RDMA/InfiniBand，TCP 兜底）在池间传输 KV cache。NVIDIA Dynamo（GTC 2025 发布，1.0 GA）位于 vLLM/SGLang/TRT-LLM 之上——它的 Planner Profiler + SLA Planner 会自动匹配 prefill:decode 比例以满足 SLO。NVIDIA 公布的吞吐收益就在这个量级——developer.nvidia.com（2025-06）显示 GB200 NVL72 + Dynamo 上 DeepSeek-R1 MoE 在中等延迟区间约有 6 倍提升，Dynamo 产品页（developer.nvidia.com，无日期）宣传 GB300 NVL72 + Dynamo 对 Hopper 的 MoE 吞吐最高 50 倍。「30 倍」这个数字是社区对完整 Blackwell + Dynamo + DeepSeek-R1 栈报告的汇总；我们没有找到任何一个恰好说出 30 倍的一手来源，请把它当方向性说法。llm-d（Red Hat + AWS）是 Kubernetes 原生的：prefill / decode / router 作为独立 Service，各自有按角色的 HPA。llm-d 0.5 增加了分层 KV 卸载、缓存感知 LoRA 路由、UCCL 网络、scale-to-zero。经济账：对多份客户披露的内部汇总显示，在 SLA 不变的前提下，从 colocated 服务切换到 Dynamo 分离式，$2M 量级的推理支出可省 30–40%（即 $600-800K/年）；$2M→$600-800K 这个具体数字是内部综合，不是单一已发表案例——把它当数量级锚点，不要当引用出处。短提示（<512 token、短输出）不值得付这笔传输成本。

> Prefill is compute-bound; decode is memory-bound. Running both on the same GPU wastes one resource. Disaggregation splits them onto separate pools and transfers KV cache between them over NIXL (RDMA/InfiniBand or TCP fallback). NVIDIA Dynamo (GTC 2025 announce, 1.0 GA) sits above vLLM/SGLang/TRT-LLM — its Planner Profiler + SLA Planner auto-rate-match prefill:decode ratios to meet SLOs. NVIDIA publishes throughput gains in this ballpark — developer.nvidia.com (2025-06) shows a ~6x improvement for DeepSeek-R1 MoE on GB200 NVL72 + Dynamo in the medium-latency regime, and the Dynamo product page (developer.nvidia.com, undated) advertises up to 50x MoE throughput on GB300 NVL72 + Dynamo vs Hopper. The "30x" figure is a community aggregate across full-stack Blackwell + Dynamo + DeepSeek-R1 reports; we have not found a single primary source stating exactly 30x, so treat it as a directional claim. llm-d (Red Hat + AWS) is Kubernetes-native: prefill / decode / router as independent Services with per-role HPA. llm-d 0.5 adds hierarchical KV offloading, cache-aware LoRA routing, UCCL networking, scale-to-zero. Economics: internal rollup of multiple customer disclosures suggests 30–40% savings on $2M-class inference spend (i.e., $600-800K/year) when switching from colocated serving to disaggregated with Dynamo at constant SLA; the specific $2M→$600-800K figure is an internal composite, not a single published case study — use it as an order-of-magnitude anchor, not a reference citation. Short prompts (<512 tokens, short output) don't justify the transfer cost.

**Type:** Learn
**Languages:** Python (stdlib, toy disaggregated-vs-colocated simulator)
**Prerequisites:** Phase 17 · 04 (Serving Engine Internals), Phase 17 · 08 (Inference Metrics)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 解释为什么 prefill 和 decode 的最优 GPU 配置不同，并量化 colocated 下的浪费。
- 画出分离式架构图：prefill 池、decode 池、经 NIXL 的 KV 传输、路由器。
- 说出分离式不划算的条件（短提示、短输出）。
- 区分 NVIDIA Dynamo（栈上层编排）与 llm-d（Kubernetes 原生），并把各自匹配到对应的运维场景。

> Explain why prefill and decode have different optimal GPU allocations and quantify the waste under colocation.
> Diagram the disaggregated architecture: prefill pool, decode pool, KV transfer via NIXL, router.
> Name the condition when disaggregation does NOT pay off (short prompts, short outputs).
> Distinguish NVIDIA Dynamo (stack-above) from llm-d (Kubernetes-native) and match each to an operational context.

## The Problem · 问题在哪

你在 8 张 H100 上跑 Llama 3.3 70B。混合负载（长提示 + 短输出）下，decode 阶段 GPU 在空转，因为大部分算力花在了 prefill 上。换成另一种负载（短提示 + 长输出），情况正好反过来。把 prefill + decode 放在一起（colocated），意味着两种资源你都过度配置了。

预算影响：20-40% 的 GPU 时间浪费在错误的资源上。你买 H100 算力去跑内存受限的 decode，或者买 H100 的 HBM 带宽去跑计算受限的 prefill。两者都是昂贵的浪费。

分离式把 prefill 和 decode 拆到按各自瓶颈定容的独立池。KV cache 通过高带宽互连从 prefill 池传到 decode 池。

> You run Llama 3.3 70B on 8 H100s. Under mixed workload (long prompts + short outputs), GPUs idle during decode because most of the compute was spent on prefill. Under different workload (short prompts + long outputs), the opposite happens. Colocated prefill + decode means you over-provision both.
> Budget impact: 20-40% of GPU time is wasted on the wrong resource. You are buying H100 compute to run memory-bound decode, or buying H100 HBM bandwidth to run compute-bound prefill. Both are expensive waste.
> Disaggregation splits prefill and decode onto separate pools sized for each's bottleneck. KV cache transfers from prefill pool to decode pool via high-bandwidth interconnect.

## The Concept · 概念

### Why the bottlenecks differ · 为什么瓶颈不同

**Prefill** —— 一次前向把 transformer 跑完整个输入提示。矩阵乘法主导；计算受限。H100 FP8 提供约 2000 TFLOPS 的有效吞吐。批处理效率好——一次前向处理很多 token。

**Decode** —— 一次生成一个 token，每步迭代都要读完整的权重。内存带宽受限。HBM3 提供约 3 TB/s。只有高并发时批处理效率才好——权重读取在 batch 内摊薄。

把两者放在一起（colocate）：你得买对两者都优化的 GPU。H100 两者都擅长，但不管怎么用成本都一样。上规模之后，你会想要 prefill 池用 H100 / 偏算力；decode 池用 H200 / 偏内存，或配合激进量化。

> **Prefill** — run the transformer over the full input prompt in one forward. Matrix multiplications dominate; compute-bound. H100 FP8 gives ~2000 TFLOPS of useful throughput. Batch efficiency is good — one forward processes many tokens.
> **Decode** — generate one token at a time, reading the full weights each iteration. Memory-bandwidth-bound. HBM3 gives ~3 TB/s. Batch efficiency is good only at high concurrency — the weights read amortizes across the batch.
> Colocating them: you buy GPUs optimized for both. H100 is good at both but costs the same either way. At scale, you want prefill pool on H100 / compute-heavy; decode pool on H200 / memory-heavy, or with aggressive quantization.

### The architecture · 架构

```
            ┌──────────────┐
  Request → │    Router    │ ───────────────────────┐
            └──────┬───────┘                        │
                   │                                │
                   ▼ (prompt only)                  │
            ┌──────────────┐    KV cache    ┌───────▼──────┐
            │ Prefill pool │ ─── NIXL ────► │ Decode pool  │
            │  (compute)   │                │  (memory)    │
            └──────────────┘                └──────┬───────┘
                                                   │ tokens
                                                   ▼
                                                 Client
```

NIXL 是 NVIDIA 的跨节点传输层。有条件时用 RDMA/InfiniBand，否则回退 TCP。传输延迟是真实存在的——70B FP8 下，4K token 提示的 KV cache 通常要 20-80 ms。这正是短提示不值得分离的原因：传输税超过了节省。

> NIXL is NVIDIA's inter-node transport. Uses RDMA/InfiniBand when available, TCP fallback otherwise. Transfer latency is real — typically 20-80 ms for KV cache of a 4K-token prompt on 70B FP8. This is why short prompts don't justify disaggregation: the transfer tax exceeds the savings.

### Dynamo vs llm-d · Dynamo 与 llm-d

**NVIDIA Dynamo**（GTC 2025 发布，1.0 GA）：
- 作为编排器位于 vLLM、SGLang、TRT-LLM 之上。
- Planner Profiler 测量工作负载，SLA Planner 自动配置 prefill:decode 比例。
- Rust 内核，Python 扩展。
- 吞吐收益：NVIDIA 报告 GB200 NVL72 + Dynamo 上 DeepSeek-R1 MoE 在中等延迟区间为 6 倍（developer.nvidia.com，2025-06）；完整 Blackwell + Dynamo + DeepSeek-R1 栈上「最高 30 倍」的社区报告缺乏单一一手来源，应视为方向性说法。
- GB300 NVL72 + Dynamo：按 Dynamo 产品页（developer.nvidia.com，无日期），MoE 吞吐最高达 Hopper 的 50 倍。

**llm-d**（Red Hat + AWS，Kubernetes 原生）：
- prefill / decode / router 作为独立的 Kubernetes Service。
- 每角色 HPA，信号用队列深度（prefill）/ KV 利用率（decode）。
- `topologyConstraint packDomain: rack` 把 prefill+decode 机组打包到同一机架，保证高带宽 KV 传输。
- llm-d 0.5（2026）：分层 KV 卸载、缓存感知 LoRA 路由、UCCL 网络、scale-to-zero。

想要一个托管的上层编排器，就用 Dynamo。想要 Kubernetes 原生原语、且已投入 CNCF 生态，就用 llm-d。

> **NVIDIA Dynamo** (GTC 2025 announce, 1.0 GA): Sits above vLLM, SGLang, TRT-LLM as an orchestrator. Planner Profiler measures workload, SLA Planner auto-configures prefill:decode ratios. Rust core, Python extensibility. Throughput gains: NVIDIA reports 6x for DeepSeek-R1 MoE on GB200 NVL72 + Dynamo in the medium-latency regime (developer.nvidia.com, 2025-06); community reports of "up to 30x" on full Blackwell + Dynamo + DeepSeek-R1 stacks lack a single primary source and should be treated as directional. GB300 NVL72 + Dynamo: up to 50x MoE throughput vs Hopper per the Dynamo product page (developer.nvidia.com, undated).
> **llm-d** (Red Hat + AWS, Kubernetes-native): Prefill / decode / router as independent Kubernetes Services. Per-role HPA with queue depth (prefill) / KV utilization (decode) signals. `topologyConstraint packDomain: rack` packs prefill+decode cliques on the same rack for high-bandwidth KV transfer. llm-d 0.5 (2026): hierarchical KV offloading, cache-aware LoRA routing, UCCL networking, scale-to-zero.
> Use Dynamo if you want a managed stack-above orchestrator. Use llm-d if you want Kubernetes-native primitives and are committed to the CNCF ecosystem.

### Economics · 经济账

内部综合估算（不是单一已发表案例——数量级锚点）：

- colocated 服务的推理支出为 $2M/年。
- 切换到 Dynamo 分离式。
- 请求量不变，P99 延迟 SLA 不变。
- 报告节省：$600K–$800K/年（降幅 30–40%）。
- 不买新硬件。

这个数字是我们从多份客户披露中综合出来的，而非单一可引用的案例研究；最接近的公开数据点是 Baseten 借助 Dynamo KV 路由实现的 TTFT 快 2 倍 / 吞吐高 61%（baseten.co，2025-10），以及 VAST + CoreWeave 预测的 KV 命中率 40–60% 时每美元 token 数多 60–130%（vastdata.com，2025-12）。节省来自给每个池按需定容；prefill 重的负载（带 8K+ 前缀的 RAG）比均衡负载受益更大。

> Internal composite (not a single published case study — order-of-magnitude anchor): $2M/year inference spend on colocated serving. Switched to disaggregated with Dynamo. Same request volume, same P99 latency SLA. Reported savings: $600K–$800K/year (30–40% reduction). No new hardware. ... We synthesize this figure from multiple customer disclosures rather than a single citable case study; closest published data point is Baseten's 2x faster TTFT / 61% higher throughput with Dynamo KV routing (baseten.co, 2025-10), and VAST + CoreWeave's projection of 60–130% more tokens/$ at 40–60% KV hit rate (vastdata.com, 2025-12). The savings come from right-sizing each pool; prefill-heavy workloads (RAG with 8K+ prefixes) benefit more than balanced ones.

### When NOT to disaggregate · 什么时候不要分离

- 提示 < 512 token 且输出 < 200 token：传输税压过收益。
- 小集群（< 4 GPU）：池多样性不够。
- 团队无法运维两个带按角色扩缩的 GPU 池：Dynamo 有帮助，但并不省事。
- 没有 RDMA 网络：TCP 传输税更重。

> Prompts < 512 tokens and outputs < 200 tokens: transfer tax dominates gain. Small cluster (< 4 GPUs): not enough pool diversity. Team cannot operate two GPU pools with per-role scaling: Dynamo helps but not trivially. No RDMA fabric: TCP transfer tax is heavier.

### The router integrates with Phase 17 · 11 · 路由器与 Phase 17 · 11 的集成

分离式路由器是 KV-cache 感知的（Phase 17 · 11）。请求会落到持有其前缀的 decode 池上——没有匹配就走 prefill → decode。命中率与分离式相互放大——缓存感知路由器决定了是否还需要一次新的 prefill。

> Disaggregated routers are KV-cache-aware (Phase 17 · 11). A request lands on the decode pool holding its prefix — if no match, it flows prefill → decode. Hit rate and disaggregation compound — the cache-aware router determines whether a new prefill is even needed.

### MoE on Blackwell is where the real numbers are · Blackwell 上的 MoE 才有真正的大数字

GB300 NVL72 + Dynamo 展示了对 Hopper 基线 50 倍的 MoE 吞吐。MoE 专家路由在 prefill 上偏算力、在 decode 上偏内存（专家缓存），所以分离是双重赢。2026 年的前沿模型服务以 MoE 为主（DeepSeek-V3、未来的 GPT-5 变体）。

> GB300 NVL72 + Dynamo shows 50x MoE throughput over Hopper baselines. MoE expert routing is compute-heavy on prefill but memory-heavy on decode (expert caches), so disaggregation is a double win. 2026 frontier model serving is MoE-dominant (DeepSeek-V3, future GPT-5 variants).

### Numbers you should remember · 你该记住的数字

基准数字会漂移——NVIDIA 和推理栈每个季度都在发布更新结果。引用前先复核。

- DeepSeek-R1 在 GB200 NVL72 + Dynamo：中等延迟区间吞吐约为基线的 6 倍（developer.nvidia.com，2025-06）；完整 Blackwell + Dynamo 栈上社区「最高 30 倍」的说法是缺乏单一一手来源的方向性汇总。
- GB300 NVL72 + Dynamo：MoE 吞吐最高 50 倍于 Hopper（developer.nvidia.com，无日期）。
- 节省锚点（内部综合，非单一案例研究）：$2M 年支出下每年省 $600-800K，SLA 不变。
- 分离阈值：提示 >512 token 且输出 >200 token。
- NIXL KV 传输：70B FP8 下 4K 提示 KV 为 20-80 ms。

```figure
prefill-decode-split
```

> Benchmark numbers drift — NVIDIA and the inference stack post updated results every quarter. Re-check before quoting. ... DeepSeek-R1 on GB200 NVL72 + Dynamo: ~6x throughput vs baseline in the medium-latency regime (developer.nvidia.com, 2025-06); community "up to 30x" claims on full Blackwell + Dynamo stacks are directional aggregates without a single primary source. GB300 NVL72 + Dynamo: up to 50x MoE throughput vs Hopper (developer.nvidia.com, undated). Savings anchor (internal composite, not a single case study): $600-800K/year off a $2M annual spend at constant SLA. Disaggregation threshold: prompts >512 tokens + outputs >200 tokens. KV transfer via NIXL: 20-80 ms for 4K-prompt KV on 70B FP8.

## Use It · 实战用法

`code/main.py` 模拟 colocated 与分离式两种服务方式。报告吞吐、每请求成本和提示长度交叉点。

> `code/main.py` simulates colocated vs disaggregated serving. Reports throughput, cost per request, and the prompt-length crossover.

## Ship It · 交付

本课产出 `outputs/skill-disaggregation-decider.md`。给定工作负载和集群，它决定是否采用分离式。

> This lesson produces `outputs/skill-disaggregation-decider.md`. Given workload and cluster, decides whether to disaggregate.

## Exercises · 练习

1. 跑 `code/main.py`。提示长度为多少时分离式胜过 colocated？
2. 为一个 P99 前缀长度 8K、输出 300 的 RAG 服务设计 prefill 池和 decode 池。
3. Dynamo vs llm-d：一家纯 Kubernetes、对 Python 运行时没有偏好的团队，选哪个？
4. 计算 KV 传输成本：70B FP8 下 4K prefill ≈ 500 MB KV。RDMA 100 GB/s 时传输 = 5 ms。TCP 10 GB/s 时 = 50 ms。哪个会影响你的 SLA？
5. MoE 专家路由改变了 KV 访问模式。对每个 token 激活不同专家的 MoE，分离式表现如何？

> 1. Run `code/main.py`. At what prompt length does disaggregation beat colocation? ... 3. Dynamo vs llm-d: pick one for a pure-Kubernetes shop with no Python runtime preference. ... 5. MoE expert routing changes KV access patterns. How does disaggregation behave with MoE that activates different experts per token?

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|------------|----------|
| Disaggregated serving | 「拆开 prefill/decode」 | 每个阶段独立的 GPU 池 |
| NIXL | 「NVIDIA 传输层」 | Dynamo 的跨节点 KV 传输（RDMA/TCP） |
| NVIDIA Dynamo | 「编排器」 | 位于 vLLM/SGLang/TRT-LLM 之上的协调器 |
| llm-d | 「Kubernetes 原生」 | Red Hat + AWS 的 K8s 分离式栈 |
| Planner Profiler | 「Dynamo 自动配置」 | 测量工作负载、配置池比例 |
| SLA Planner | 「Dynamo 策略」 | 自动匹配 prefill:decode 以满足 SLO |
| `packDomain: rack` | 「llm-d 拓扑」 | 把 prefill+decode 打包到同一机架以加速 KV |
| UCCL | 「统一集合通信」 | llm-d 0.5 支撑 scale-to-zero 的网络层 |
| MoE expert routing | 「每 token 选专家」 | DeepSeek-V3 模式；分离式对其有帮助 |

## Further Reading · 延伸阅读

- [NVIDIA — Introducing Dynamo](https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models/)
- [NVIDIA — Disaggregated LLM Inference on Kubernetes](https://developer.nvidia.com/blog/deploying-disaggregated-llm-inference-workloads-on-kubernetes/)
- [TensorRT-LLM Disaggregated Serving blog](https://nvidia.github.io/TensorRT-LLM/blogs/tech_blog/blog5_Disaggregated_Serving_in_TensorRT-LLM.html)
- [llm-d GitHub](https://github.com/llm-d/llm-d)
- [llm-d 0.5 release notes](https://github.com/llm-d/llm-d/releases)
