# Cold Start Mitigation for Serverless LLMs · Serverless LLM 的冷启动缓解

一个 20 GB 的模型镜像从冷态到可服务，7B 要 5-10 分钟，70B 要 20 分钟以上。在真正的 serverless 世界里，这不是预热——是宕机。缓解手段分布在五层：预置（pre-seeded）节点镜像（AWS 上的 Bottlerocket、双卷架构）、模型流式加载（NVIDIA Run:ai Model Streamer，vLLM 原生集成）、GPU 显存快照（Modal checkpoint，重启最快可快 10 倍）、暖池（warm pool，`min_workers=1`）、分层加载（ServerlessLLM 的 NVMe→DRAM→HBM 流水线，延迟降低 10-200 倍），以及迁移输入 token（KB 级）而非 KV cache（GB 级）的活迁移（live migration）。Modal 公布的冷启动下限是 2-4 秒；Baseten 默认 5-10 秒，预热后亚秒级。本课教你怎么测量、怎么做预算、怎么把这五层叠起来。

> A 20 GB model image takes 5-10 minutes (7B) to 20+ minutes (70B) to go from cold to serving. In a true serverless world, that is not a warm-up — it is an outage. Mitigations operate at five layers: pre-seeded node images (Bottlerocket on AWS, dual-volume arch), model streaming (NVIDIA Run:ai Model Streamer, native in vLLM), GPU memory snapshots (Modal checkpoints, up to 10x faster restart), warm pools (`min_workers=1`), tiered loading (ServerlessLLM's NVMe→DRAM→HBM pipeline, 10-200x latency reduction), and live migration that moves input tokens (KB) rather than KV cache (GB). Modal publishes 2-4s cold starts as a floor; Baseten 5-10s default, sub-second with pre-warming. This lesson teaches you to measure, budget, and stack the five layers.

**Type:** Learn
**Languages:** Python（仅标准库；玩具级冷启动路径模拟器）
**Prerequisites:** Phase 17 · 02（Inference Platform Economics）、Phase 17 · 03（GPU Autoscaling）
**Time:** ~60 分钟

## Learning Objectives · 学习目标

- 列出冷启动缓解的五个层次，并说出每一层对应的一个工具或模式。
- 把 70B 模型的总冷启动时间拆成（节点供给）+（权重下载）+（权重载入 HBM）+（引擎初始化）之和来计算。
- 解释为什么活迁移传输的是输入 token（KB）而不是 KV cache（GB），以及代价是什么（重计算）。
- 说出暖池的取舍（为闲置 GPU 付费，或接受冷启动长尾），以及 `min_workers > 0` 在什么 SLA 阈值下成为必选项。

> Enumerate the five layers of cold-start mitigation and name one tool or pattern at each layer.
> Compute total cold-start time as a sum of (node provision) + (weights download) + (weights load into HBM) + (engine init) for a 70B model.
> Explain why live migration transfers input tokens (KB) not KV cache (GB) and what the penalty is (recomputation).
> Name the warm-pool trade-off (pay for idle GPU or accept cold-start tail) and the SLA threshold at which `min_workers > 0` becomes mandatory.

## The Problem · 问题在哪

你的 serverless LLM 端点夜间缩容到零。早上 8 点流量涌进来。第一个请求要等：

1. Karpenter 供给一个 GPU 节点：45-60 秒。
2. 容器拉取带权重的 30 GB 镜像：120-300 秒。
3. 引擎把权重载入 HBM：视模型大小和存储速度，45-120 秒。
4. vLLM 或 TRT-LLM 初始化 CUDA graph、KV cache 池、分词器：10-30 秒。

合计 220-510 秒（约 3-8 分钟）后才等来回第一个 token。你的 SLA 是 2 秒。你上了暖池（`min_workers=1`），问题看似消失——但现在你要为一台闲置 GPU 付 7×24 的钱。如果你的服务有 5 个产品、每个常驻一台暖副本，那就是 5 × 24 × 30 = 3,600 GPU 小时/月，哪怕一个用户都没来。

冷启动缓解，就是如何在保住 serverless 经济学的同时，逼近常驻（always-on）的延迟。

> Your serverless LLM endpoint scales to zero overnight. At 8 a.m. traffic spikes. The first request waits while:
> Total: 220-510s (roughly 3-8 minutes) before one token comes back. Your SLA is 2s. You ship a warm-pool (`min_workers=1`) and the problem seems to vanish — but now you pay for one idle GPU 24x7. If your service has 5 products each with one warm replica, that's 5 × 24 × 30 = 3,600 GPU-hours/month whether or not a single user called.
> Cold-start mitigation is how to keep the serverless economics while approximating the latency of always-on.

## The Concept · 概念

### Layer 1 — pre-seeded node images (Bottlerocket) · 第 1 层——预置节点镜像（Bottlerocket）

在 AWS 上，Bottlerocket 的双卷架构把 OS 和数据分开。给预拉取了容器镜像的数据卷打快照；在 `EC2NodeClass` 里引用这个快照 ID。新节点启动时，本地 NVMe 上已经有权重——第 2 步和第 3 步的一部分直接消失。与 Karpenter 原生配合。典型节省：大模型每次冷启动省 2-4 分钟。

GCP 上的等价物：预烘焙容器层的自定义 VM 镜像。Azure 上：同一模式的托管磁盘快照。

> On AWS, Bottlerocket's dual-volume architecture separates OS from data. Snapshot the data volume with your container image pre-pulled; reference the snapshot ID in your `EC2NodeClass`. New nodes boot with weights already on local NVMe — steps 2 and part of 3 vanish. Works with Karpenter natively. Typical savings: 2-4 minutes per cold start for large models.
> Equivalent on GCP: custom VM images with pre-baked container layers. On Azure: managed disk snapshots with the same pattern.

### Layer 2 — model streaming (Run:ai Model Streamer) · 第 2 层——模型流式加载（Run:ai Model Streamer）

与其在响应第一个请求前加载完整文件，不如把权重逐层流式送进 GPU 显存，第一个 transformer 块就位后立刻开始处理。NVIDIA Run:ai Model Streamer 已在 vLLM 2026 中原生提供。支持 S3、GCS 和本地 NVMe。通过让 I/O 与计算准备重叠，大模型的权重加载时间大约减半。

> Instead of loading the full file before answering the first request, stream weights into GPU memory layer-by-layer and start processing as soon as the first transformer block is resident. The NVIDIA Run:ai Model Streamer ships native in vLLM 2026. Works with S3, GCS, and local NVMe. Cuts weight-load time roughly in half for large models by overlapping I/O with compute setup.

### Layer 3 — GPU memory snapshots (Modal) · 第 3 层——GPU 显存快照（Modal）

Modal 在首次加载后给 GPU 状态（权重、CUDA graph、KV cache 区域）打 checkpoint。后续重启直接反序列化进 HBM——比重新初始化快 10 倍。这是最接近「2 秒启动一个暖 GPU」的东西。代价：快照是按 GPU 拓扑绑定的，如果 Karpenter 把你迁到不同 SKU，就得重新打 checkpoint。

> Modal takes a checkpoint of the GPU state (weights, CUDA graphs, KV cache region) after first load. Subsequent restarts deserialize directly into HBM — 10x faster than re-initializing. This is the closest thing to "boot a warm GPU in 2 seconds." Trade-off: snapshots are per-GPU-topology, so if Karpenter migrates you to a different SKU, you re-checkpoint.

### Layer 4 — warm pools (min_workers=1) · 第 4 层——暖池（min_workers=1）

最简单的缓解：永远保留一个就绪副本。成本是一台 GPU 每小时费率 × 7×24。这笔账对小模型很残酷（花 $0.85-$1.50/小时去避免一次 30 秒冷启动），对大模型却友好（花 $4/小时避免一次 5 分钟冷启动）。暖池成为必选项的 SLA 阈值：通常是 70B+ 模型要求 TTFT P99 < 60 秒。

> Simplest mitigation: keep one replica always ready. Cost is one GPU's hourly rate 24x7. The arithmetic is brutal on small models (you pay $0.85-$1.50/hr to avoid a 30s cold start) and kind to large ones (pay $4/hr to avoid a 5-minute cold start). The SLA threshold where warm pools become mandatory: typically TTFT P99 < 60s on a 70B+ model.

### Layer 5 — tiered loading (ServerlessLLM) · 第 5 层——分层加载（ServerlessLLM）

ServerlessLLM 把存储当层级对待：NVMe（快但大）、DRAM（中等但分层）、HBM（小但即时）。权重预加载到 DRAM，按需装入 HBM。论文报告：相比朴素的磁盘到 HBM 加载，冷加载延迟降低 10-200 倍。生产采用尚早，但已有与 vLLM 的集成。

> ServerlessLLM treats storage as a hierarchy: NVMe (fast but big), DRAM (medium but tiered), HBM (tiny but instant). Weights are pre-loaded to DRAM; load-on-demand into HBM. Paper reports 10-200x latency reduction on cold loads versus naive disk-to-HBM. Production adoption is early but integrations with vLLM exist.

### Layer 6 — live migration (bonus pattern) · 第 6 层——活迁移（加分模式）

节点不可用时（spot 回收、节点排水），传统做法是冷启动一个新副本再排空请求队列。活迁移把输入 token（KB 级）搬到一台已加载好模型的目标机器上，在目标端重算 KV cache。重计算比走网络传 GB 级 KV cache 便宜。适用于分离式（disaggregated）部署。

> When a node becomes unavailable (spot eviction, node drain), traditional pattern is cold-start another replica and drain request queue. Live migration moves the input tokens (kilobytes) to a destination that has the model loaded and recomputes KV cache on the destination. Recomputation is cheaper than transferring GB of KV cache over the network. Applicable to disaggregated deployments.

### The warm-pool math · 暖池的账

对一个 P99 TTFT SLA 为 2 秒的服务，问题不是「暖池要不要」，而是「留几个暖副本、给哪些路径留」。

- 高价值交互路径（在线聊天、语音 agent）：`min_workers=1-2`。
- 后台批处理路径（夜间分类）：接受缩容到零，5-10 分钟冷启动可以容忍。
- 高级套餐：按租户设 `min_workers`，配专属容量。

> For a service with P99 TTFT SLA of 2s, the question is not "warm pool yes/no" but "how many warm replicas, and which paths get them."
> - High-value interactive paths (live chat, voice agent): `min_workers=1-2`.
> - Background batch paths (nightly classification): scale-to-zero accepted, 5-10 minute cold start tolerable.
> - Premium tier: `min_workers` per tenant with dedicated capacity.

### Measure before optimizing · 先测量再优化

70B 模型在全新节点上的冷启动解剖（示意）：

| 阶段 | 耗时 | 缓解手段 |
|-------|------|-----------|
| 节点供给 | 50s | Bottlerocket + 预置镜像、暖池 |
| 镜像拉取 | 180s | 预置数据卷（消除） |
| 权重进 HBM | 75s | 模型流式加载（减半）；GPU 快照（消除） |
| 引擎初始化 | 20s | 持久化 CUDA graph 缓存 |
| 首次前向 | 3s | 固有最低延迟 |
| **冷启动合计** | **328s** | |
| **缓解后合计** | **~15s** | 降低 22 倍 |

> Cold-start anatomy for a 70B model on a fresh node (illustrative):
> | Phase | Time | Mitigation |
> | Node provision | 50s | Bottlerocket + pre-seeded image, warm pool |
> | Image pull | 180s | Pre-seeded data volume (eliminate) |
> | Weights to HBM | 75s | Model streamer (halve); GPU snapshot (eliminate) |
> | Engine init | 20s | Persistent CUDA graph cache |
> | First forward | 3s | Min inherent latency |
> | **Total cold** | **328s** | |
> | **Total with mitigations** | **~15s** | 22x reduction |

### Numbers you should remember · 该记住的数字

- Modal 冷启动：2-4 秒（用 GPU 快照）。
- Baseten 默认冷启动：5-10 秒；预热后亚秒级。
- 裸 70B 冷启动：3-8 分钟。
- Run:ai Model Streamer：权重加载约 2 倍加速。
- ServerlessLLM 分层加载：延迟降低 10-200 倍（论文数字）。

```figure
cold-start-pipeline
```

> - Modal cold start: 2-4s (with GPU snapshots).
> - Baseten default cold start: 5-10s; sub-second with pre-warming.
> - Raw 70B cold start: 3-8 minutes.
> - Run:ai Model Streamer: ~2x weight-load speedup.
> - ServerlessLLM tiered loading: 10-200x latency reduction (paper numbers).

## Use It · 实战用法

`code/main.py` 对比了带与不带每种缓解手段的冷启动路径。报告总冷启动时间、暖池成本，以及暖池开始回本时的盈亏平衡请求速率。

> `code/main.py` models a cold-start path with and without each mitigation. Reports total cold-start time, warm-pool cost, and the break-even request rate above which warm pool pays for itself.

## Ship It · 交付

本课产出 `outputs/skill-cold-start-planner.md`。给定 SLA、模型大小和流量形态，它会选出该叠加哪些缓解手段。

> This lesson produces `outputs/skill-cold-start-planner.md`. Given SLA, model size, and traffic shape, picks which mitigations to stack.

## Exercises · 练习

1. 运行 `code/main.py`。计算盈亏平衡请求速率：超过它之后，一个暖副本比「以 SLO 内额外丢弃请求的形式缴纳冷启动税」更便宜。
2. 你要部署一个 13B 模型，P99 TTFT SLA 为 3 秒。选出达成它的最小缓解组合（层数最少）。
3. Bottlerocket 预置消除了镜像拉取，但权重仍要从快照读进 HBM。若快照支撑的 NVMe 读取速度为 7 GB/s，计算 70B 模型的墙钟时间。
4. 你的 serverless 厂商提供 GPU 快照（Modal），团队以「快照会泄漏 PII」为由拒绝。为双方辩护——现实风险是什么，缓解手段是什么（临时快照、加密、命名空间隔离）？
5. 设计一个分层暖池策略：付费用户、试用用户、批处理负载各留几个暖副本？把账算出来。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Cold start | 「大停顿」 | 全新副本上从请求到首 token 的时间 |
| Warm pool | 「常开最小值」 | 用 `min_workers >= 1` 保证至少一个副本就绪 |
| Pre-seeded image | 「预烘焙 AMI」 | 容器与权重已预置在上的节点镜像 |
| Bottlerocket | 「AWS 节点 OS」 | AWS 容器优化 OS，支持双卷快照 |
| Model streamer | 「流式加载」 | 让权重 I/O 与计算准备重叠 |
| GPU snapshot | 「checkpoint 进 HBM」 | 序列化加载后的 GPU 状态；重启时反序列化 |
| Tiered loading | 「NVMe + DRAM + HBM」 | 存储层级；按需加载 |
| Live migration | 「搬 token」 | 迁移输入（KB），在目标端重算 KV |
| `min_workers` | 「暖副本」 | serverless 的最小保活数量 |
| Scale-to-zero | 「完全 serverless」 | 空闲零成本；接受全额冷启动税 |

## Further Reading · 延伸阅读

- [Modal — Cold start performance](https://modal.com/docs/guide/cold-start) —— Modal 公布的基准与 checkpoint 架构。
- [AWS Bottlerocket](https://github.com/bottlerocket-os/bottlerocket) —— 预置数据卷快照模式。
- [NVIDIA Run:ai Model Streamer](https://github.com/run-ai/runai-model-streamer) —— 权重加载与计算准备重叠。
- [Baseten — Cold starts](https://docs.baseten.co/deployment/autoscaling/cold-starts) —— 预热操作手册。
- [ServerlessLLM paper (USENIX OSDI'24)](https://www.usenix.org/conference/osdi24/presentation/fu) —— 分层加载设计。
- [NVIDIA — Disaggregated LLM Inference on Kubernetes](https://developer.nvidia.com/blog/deploying-disaggregated-llm-inference-workloads-on-kubernetes/) —— 分离式部署的活迁移。
