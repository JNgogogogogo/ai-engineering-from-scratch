# Multi-Region LLM Serving and KV Cache Locality · 多区域 LLM 服务与 KV cache 局部性

轮询（round-robin）负载均衡对带缓存的 LLM 推理是主动有害的。一个没落在持有其前缀的节点上的请求，要付全额 prefill 成本——长提示上 P50 约 800 ms，而缓存命中只要约 80 ms。2026 年的生产模式是缓存感知路由器（Rust 写的 vLLM Router、llm-d router），它消费 KV-cache 事件并按前缀哈希匹配来路由。最新研究（GORGO）把跨区域网络延迟变成路由目标中的显式项。商业化的「跨区域推理」产品（Bedrock cross-region inference、GKE multi-cluster gateways）把推理当黑盒——它们管可用性，不管 TTFT。JPMorgan 和 Mayo Clinic 在 2024 年 11 月的 us-east-1 故障切换演练中用时约 22 分钟。灾备（DR）的现实是：32% 的 LLM DR 失败，是因为团队备份了权重，却忘了分词器文件或量化配置。

> Round-robin load balancing is actively harmful for cached LLM inference. A request that does not land on the node holding its prefix pays full prefill cost — roughly 800 ms at P50 on a long prompt versus ~80 ms with a cache hit. In 2026 the production pattern is a cache-aware router (vLLM Router in Rust, llm-d router) that consumes KV-cache events and routes on prefix-hash match. Recent research (GORGO) makes cross-region network latency an explicit term in the routing objective. Commercial "cross-region inference" offerings (Bedrock cross-region inference, GKE multi-cluster gateways) treat inference as opaque — they handle availability, not TTFT. JPMorgan and Mayo Clinic ran us-east-1 failover in Nov 2024 at ~22 minutes. The DR reality: 32% of LLM DR failures are because teams backed up weights but forgot tokenizer files or quantization configs.

**Type:** Learn
**Languages:** Python（仅标准库；玩具级前缀缓存感知路由模拟器）
**Prerequisites:** Phase 17 · 04（vLLM Serving）、Phase 17 · 06（SGLang RadixAttention）
**Time:** ~60 分钟

## Learning Objectives · 学习目标

- 解释为什么轮询负载均衡会破坏带缓存的推理，并量化 TTFT 惩罚。
- 画出缓存感知路由器的结构：输入（KV-cache 事件）、算法（前缀哈希匹配）、决胜规则（GPU 利用率）。
- 说出 LLM 的那个 32% DR 失败动因（缺失分词器文件 / 量化配置），并给出一份三文件 DR 检查清单。
- 区分商业跨区域产品（Bedrock CRI、GKE Multi-Cluster Gateway）与 KV 感知路由。

> Explain why round-robin load balancing breaks cached inference and quantify the TTFT penalty.
> Diagram a cache-aware router: inputs (KV-cache events), algorithm (prefix-hash match), tie-breaker (GPU utilization).
> Name the 32% DR failure driver for LLMs (missing tokenizer files / quantization configs) and state a three-file DR checklist.
> Distinguish commercial cross-region offerings (Bedrock CRI, GKE Multi-Cluster Gateway) from KV-aware routing.

## The Problem · 问题在哪

你的服务跑在 us-east-1、us-west-2 和 eu-west-1。你在前面挂了一个 round-robin 的 ALB。生产环境的前缀缓存命中率掉到 8%。TTFT P50 变成三倍。vLLM 日志显示每个请求都在付全额 prefill 成本。

Round-robin 对无状态服务是最优的。LLM 推理天生有状态——KV cache 编码了模型见过的所有东西。盲路由就是路由进错误的缓存。

另外，你们团队有 DR 预案。你把模型权重跨区域备份到了 S3。区域故障来了，你执行切换，副本起不来。你忘了 `tokenizer.json`、量化配置和 RoPE scaling 配置躺在一个没同步的桶里。

多区域 LLM 服务是一个缓存问题、一个路由问题和一个 DR 卫生问题——不是负载均衡器问题。

> Your service runs in us-east-1, us-west-2, and eu-west-1. You put an ALB in front with round-robin. Prefix cache hit rate in production drops to 8%. TTFT P50 triples. Your vLLM logs show every request is paying full prefill cost.
> Round-robin is optimal for stateless services. LLM inference is stateful by design — the KV cache encodes everything the model has seen. Routing blind is routing into the wrong cache.
> Separately, your team has a DR plan. You back up model weights to S3 cross-region. A regional outage hits; you attempt failover; the replica refuses to start. You forgot tokenizer.json, the quantization config, and the RoPE scaling config were in a separate bucket you didn't sync.
> Multi-region LLM serving is a cache problem, a routing problem, and a DR-hygiene problem — not a load-balancer problem.

## The Concept · 概念

### Cache-aware routing · 缓存感知路由

请求带着提示到达。路由器对前缀（比如前 512 个 token）做哈希；它问每个副本「你缓存了这个前缀吗？」。副本在分配和驱逐块时，把 KV-cache 事件发布到 pub/sub 频道。路由器选中匹配的副本；没人匹配就退回按 GPU 利用率决胜。

**vLLM Router**（Rust，2026 production-stack）：订阅 `kv.cache.block_added` 事件，维护「前缀哈希 → 副本」索引，O(1) 查找路由。无匹配时退回最短队列。

**llm-d router**：同一模式，Kubernetes 原生。通过 ControlPlane API 发布事件。

**SGLang RadixAttention**（Phase 17 · 06）是副本内的等价物。跨副本路由严格来说在它的上游。

> Request arrives with a prompt. Router hashes the prefix (say, first 512 tokens); it asks each replica "do you have this prefix cached?". Replicas publish KV-cache events on a pub/sub channel as they allocate and evict blocks. Router picks the replica with the match, falls through to GPU-util-based tie-breaker if no one does.
> **vLLM Router** (Rust, 2026 production-stack): subscribes to `kv.cache.block_added` events, maintains a prefix-hash → replica index, routes with O(1) lookup. Falls through to least-queue-depth when no match.
> **llm-d router**: same pattern, Kubernetes-native. Publishes events via the ControlPlane API.
> **SGLang RadixAttention** (Phase 17 · 06) is the intra-replica equivalent. Cross-replica routing is strictly upstream.

### Numbers · 数字

2K token 提示、Llama 3.3 70B FP8、H100 上的 TTFT P50：
- 缓存命中（同副本、前缀在存）：约 80 ms。
- 缓存未命中（冷 prefill）：约 800 ms。

10 倍差距。如果你的路由器跨副本命中 60-80% 的前缀缓存，你是在 N 副本容量上逼近单副本的性能。如果只命中 10%，你逼近的就是朴素扩展。

> TTFT P50 on a 2K-token prompt, Llama 3.3 70B FP8, H100:
> - Cache hit (same replica, prefix resident): ~80 ms.
> - Cache miss (cold prefill): ~800 ms.
> 10x gap. If your router hits 60-80% of prefix cache across replicas, you approximate single-replica performance at N-replica capacity. If it hits 10%, you approximate naive scaling.

### Cross-region has a new constraint — network latency · 跨区域的新约束——网络延迟

区域间 RTT：
- us-east-1 ↔ us-west-2：约 65 ms。
- us-east-1 ↔ eu-west-1：约 75 ms。
- us-east-1 ↔ ap-southeast-1：约 220 ms。

如果路由把一个请求从 us-east-1 送去 ap-southeast-1 的热前缀，省下的 prefill（800 → 80 ms）在 440 ms 的往返面前不值一提。GORGO（2026 研究）把这一点显式化——联合最小化 `prefill_time + network_latency`，而不是只看 prefill。答案通常是：除了 prefill 占主导的巨型多 MB 前缀之外，保持区域内路由。

> Inter-region RTT:
> - us-east-1 ↔ us-west-2: ~65 ms.
> - us-east-1 ↔ eu-west-1: ~75 ms.
> - us-east-1 ↔ ap-southeast-1: ~220 ms.
> If routing takes a request from us-east-1 to a hot prefix in ap-southeast-1, the saved prefill (800 → 80 ms) is dwarfed by 440 ms round-trip. GORGO (2026 research) makes this explicit — minimize `prefill_time + network_latency` jointly, not prefill alone. Often the answer is to keep routing regional except on massive multi-MB prefixes where prefill dominates.

### Commercial "cross-region inference" does not help here · 商业「跨区域推理」在这里帮不上忙

AWS Bedrock cross-region inference 在容量压力时自动把请求路由到其他区域。它优化的是可用性，不是 TTFT，并把推理当黑盒。GKE Multi-Cluster Gateway 也一样——服务级故障切换，不感知 KV cache。

即使用这些产品，你仍然需要应用层的缓存感知路由器。它们处理「us-east-1 着火了」的情况；缓存感知路由处理的是 TTFT 的情况。

> AWS Bedrock cross-region inference automatically routes requests to other regions during capacity pressure. It optimizes availability, not TTFT, and treats inference as opaque. GKE Multi-Cluster Gateway is the same — service-level failover, no awareness of KV cache.
> You still need an app-layer cache-aware router even when using these. They handle the "us-east-1 is on fire" case. Cache-aware routing handles the TTFT case.

### DR hygiene — the 32% missing-files problem · DR 卫生——32% 的文件缺失问题

广为引用的 2026 年统计：32% 的 LLM DR 失败，是因为团队备份了权重，却忘了：

- `tokenizer.json` 或 `tokenizer.model`
- 量化配置（`quantize_config.json`、AWQ scales、GPTQ zero-points）
- 模型专属配置（RoPE scaling、attention mask、chat template）
- 引擎配置（`vllm_config.yaml`、采样默认值、LoRA adapter 清单）

修复办法是一份最少三文件的 DR 清单：

1. HF 模型仓库下的所有文件（权重 + 配置 + 分词器）。
2. 引擎专属的服务配置。
3. 部署清单（K8s YAML、Dockerfile、依赖锁）。

另外：每季度跑一次 DR 演练。JPMorgan 的 us-east-1 演练能在 2024 年 11 月做到 22 分钟恢复，唯一原因是 playbook 演练过。

> Widely cited 2026 stat: 32% of LLM DR failures happen because teams backed up weights but forgot:
> - `tokenizer.json` or `tokenizer.model`
> - Quantization configs (`quantize_config.json`, AWQ scales, GPTQ zero-points)
> - Model-specific configs (RoPE scaling, attention masks, chat templates)
> - Engine config (`vllm_config.yaml`, sampling defaults, LoRA adapter manifests)
> The fix is a three-file minimum DR manifest:
> 1. All files under the HF model repo (weights + configs + tokenizer).
> 2. Engine-specific serving config.
> 3. Deployment manifest (K8s YAML, Dockerfile, dependency lock).
> Plus: run a DR drill quarterly. The JPMorgan us-east-1 drill hit 22 minutes recovery in Nov 2024 only because the playbook was rehearsed.

### Data residency is orthogonal · 数据驻留是正交的

欧盟客户的 PHI 不能离开欧盟。如果你的缓存感知路由器为了前缀匹配，把一个巴黎发起的请求送去 us-east-1，那么无论 TTFT 收益多大，你都已违反 GDPR。先按驻留边界切分路由器，再为缓存做优化。

> EU customer PHI cannot leave EU. If your cache-aware router sends a Paris-originated request to us-east-1 for a prefix match, you have violated GDPR regardless of TTFT gain. Partition routers by residency boundary before optimizing for cache.

### Numbers you should remember · 该记住的数字

- 缓存命中 vs 未命中的 TTFT 差距：约 10 倍（2K 提示上 80 ms vs 800 ms）。
- 美东-欧洲区域间 RTT：约 75 ms。
- DR 失败：32% 缺分词器/量化配置。
- JPMorgan us-east-1 切换（2024 年 11 月）：22 分钟（SLA 30 分钟）。

```figure
cache-aware-router
```

> - Cache hit vs miss TTFT gap: ~10x (80 ms vs 800 ms on 2K prompt).
> - Inter-region RTT US-EU: ~75 ms.
> - DR failure: 32% miss tokenizer/quant configs.
> - JPMorgan us-east-1 failover Nov 2024: 22 minutes (30-min SLA).

## Use It · 实战用法

`code/main.py` 在一个多区域工作负载上模拟三种路由策略（round-robin、区域内缓存感知、全局缓存感知）。报告缓存命中率、TTFT P50/P99 和跨区域账单。

> `code/main.py` simulates three routing strategies (round-robin, cache-aware regional, cache-aware global) on a multi-region workload. Reports cache hit rate, TTFT P50/P99, and cross-region bill.

## Ship It · 交付

本课产出 `outputs/skill-multi-region-router.md`。给定区域、驻留约束和 SLA，它会设计出一个路由方案。

> This lesson produces `outputs/skill-multi-region-router.md`. Given regions, residency constraints, and SLA, designs a routing plan.

## Exercises · 练习

1. 运行 `code/main.py`。在 75 ms RTT 下，提示长度到多少时跨区域路由开始胜过纯本地路由？
2. 你的缓存命中率从 70% 掉到 12%。诊断三种可能原因，以及各自能用什么观测指标确认。
3. 为一个用 vLLM 服务、带 5 个 LoRA adapter 的 70B AWQ 量化模型设计 DR 清单。列出每一个文件和配置。
4. 论证 Bedrock cross-region inference 对一个有严格 TTFT SLO 的金融科技公司是否「够用」。引用具体行为。
5. 一个巴黎发起的请求在 us-east-1 匹配到了前缀。你路由吗？把策略写出来。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Cache-aware routing | 「聪明 LB」 | 按前缀哈希匹配，路由到持有 KV cache 的副本 |
| KV-cache events | 「缓存 pub-sub」 | 副本发布块的加入/驱逐；路由器建立索引 |
| Prefix hash | 「缓存键」 | 前 N 个 token 的哈希，用作路由器查找 |
| GORGO | 「跨区域路由研究」 | arXiv 2602.11688；把网络延迟作为显式项 |
| Cross-region inference | 「Bedrock CRI」 | AWS 产品；可用性故障切换，不感知 TTFT |
| DR manifest | 「备份清单」 | 恢复所需的每一个文件——不只是权重 |
| Data residency | 「GDPR 边界」 | 哪个区域可以看到用户数据的法律约束 |
| RTT | 「往返时间」 | 网络延迟；美欧 75 ms，美-亚太 220 ms |
| LLM-aware LB | 「缓存命中 LB」 | 缓存感知路由器作为一个产品品类 |

## Further Reading · 延伸阅读

- [BentoML — Multi-cloud and cross-region inference](https://bentoml.com/llm/infrastructure-and-operations/multi-cloud-and-cross-region-inference)
- [arXiv — GORGO (2602.11688)](https://arxiv.org/html/2602.11688v1) —— 带网络延迟项的跨区域 KV cache 复用。
- [TianPan — Multi-Region LLM Serving Cache Locality](https://tianpan.co/blog/2026-04-17-multi-region-llm-serving-data-residency-routing)
- [AWS Bedrock Cross-Region Inference](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html) —— 可用性故障切换文档。
- [vLLM Production Stack Router](https://github.com/vllm-project/production-stack) —— 缓存感知路由器源码。
