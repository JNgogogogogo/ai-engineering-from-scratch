# GPU Autoscaling on Kubernetes — Karpenter, KAI Scheduler, Gang Scheduling · Kubernetes 上的 GPU 自动扩缩 —— Karpenter、KAI Scheduler、Gang Scheduling

> 是三层，不是一层。Karpenter 动态供应节点（一分钟以内，比 Cluster Autoscaler 快 40%）。KAI Scheduler 处理 gang 调度、拓扑感知和层级队列——它防住了「8 块只分到 7 块」的局部分配陷阱：七个节点干等并烧钱，就缺一块 GPU。应用层自动扩缩器（NVIDIA Dynamo Planner、llm-d Workload Variant Autoscaler）根据推理专属信号扩缩——队列深度、KV cache 利用率——而不是 CPU/DCGM 占空比。经典 HPA 陷阱在于 `DCGM_FI_DEV_GPU_UTIL` 是一个占空比测量：100% 可能对应 10 个请求，也可能对应 100 个。vLLM 预分配 KV cache 内存，所以内存永远不会触发缩容。本课教你把三层组合起来，并避开 Karpenter 默认的 `WhenEmptyOrUnderutilized` 策略——它会在推理进行到一半时终止正在跑的 GPU 任务。

> Three layers, not one. Karpenter provisions nodes dynamically (under one minute, 40% faster than Cluster Autoscaler). KAI Scheduler handles gang scheduling, topology awareness, and hierarchical queues — it prevents the 7-of-8 partial allocation trap where seven nodes wait and burn on one missing GPU. Application-level autoscalers (NVIDIA Dynamo Planner, llm-d Workload Variant Autoscaler) scale on inference-specific signals — queue depth, KV cache utilization — not CPU/DCGM duty cycle. The classic HPA trap is that `DCGM_FI_DEV_GPU_UTIL` is a duty-cycle measurement: 100% could be 10 requests or 100. vLLM pre-allocates KV cache memory, so memory never triggers scale-down. This lesson teaches you to compose the three layers and avoid the default Karpenter `WhenEmptyOrUnderutilized` policy that terminates running GPU jobs mid-inference.

**Type:** Learn
**Languages:** Python (stdlib, toy queue-depth autoscaler simulator)
**Prerequisites:** Phase 17 · 02 (Inference Platform Economics), Phase 17 · 04 (Serving Engine Internals)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 画出自动扩缩的三层（节点供应、gang 调度、应用层），并说出每一层各用哪个工具。
- 解释为什么 `DCGM_FI_DEV_GPU_UTIL` 对 vLLM 是错误的 HPA 信号，并说出两个替代信号（队列深度、KV cache 利用率）。
- 描述 gang 调度，以及 KAI Scheduler 防住的局部分配失败模式（8 块 GPU 闲着 7 块）。
- 说出会终止正在运行 GPU 任务的 Karpenter 整合策略（`WhenEmptyOrUnderutilized`），并给出 2026 年的安全替代。

> Diagram the three autoscaling layers (node provisioning, gang scheduling, application-level) and name the tool used at each layer.
> Explain why `DCGM_FI_DEV_GPU_UTIL` is the wrong HPA signal for vLLM and name two replacements (queue depth, KV cache utilization).
> Describe gang scheduling and the partial-allocation failure mode KAI Scheduler prevents (7 of 8 GPUs idle).
> Name the Karpenter consolidation policy (`WhenEmptyOrUnderutilized`) that terminates running GPU jobs and state the 2026 safe alternative.

## The Problem · 问题在哪

你的团队在 Kubernetes 上交付一个 LLM serving 服务。你用 `DCGM_FI_DEV_GPU_UTIL` 作为信号配了 HPA。工作时间服务利用率钉死在 100%。HPA 永远不扩——它已经认为你满了。你手动加了一个副本；TTFT 降下来了。HPA 还是不动。信号在骗你。

另一件事，你用 Cluster Autoscaler 管节点。凌晨 2 点来了一个 1M token 的提示词；集群花 3 分钟供应节点，请求超时了。

又一件事，你部署一个需要 8 块 GPU 跨 2 个节点的 70B 模型。集群有 7 块 GPU 空闲，还有 1 块散落在 3 个节点上。Cluster Autoscaler 为缺的那 1 块 GPU 供应一个节点。七个节点干等 4 分钟烧钱，就等 Kubernetes 把最后一块 GPU 拉起来。

三层，三种不同的失败模式。2026 年的 GPU 感知自动扩缩不是「把 HPA 打开」。它是节点供应、gang 调度、应用信号扩缩的组合。

> Your team ships an LLM-serving service on Kubernetes. You set up HPA with `DCGM_FI_DEV_GPU_UTIL` as the signal. The service pins at 100% utilization during business hours. HPA never scales up — it already thinks you're full. You add a replica manually; TTFT drops. HPA still doesn't scale. The signal is lying to you.
> Separately, you use Cluster Autoscaler for nodes. A 1M-token prompt arrives at 2 a.m.; the cluster spends 3 minutes provisioning a node, and the request times out.
> Separately again, you deploy a 70B model requiring 8 GPUs across 2 nodes. The cluster has 7 GPUs free and 1 spread across 3 nodes. Cluster Autoscaler provisions a node for the 1 missing GPU. Seven nodes wait 4 minutes burning money while Kubernetes gets the last GPU up.
> Three layers, three different failure modes. GPU-aware autoscaling in 2026 is not "turn on HPA." It's composing node provisioning, gang scheduling, and application-signal autoscaling.

## The Concept · 概念

### Layer 1 — node provisioning (Karpenter) · 第一层 —— 节点供应（Karpenter）

Karpenter 监听 pending 的 pod，约 45-60 秒内供应节点（Cluster Autoscaler 对 GPU 节点通常要 90-120 秒）。它按 `NodePool` 约束动态挑选实例类型——如果你的 pod 需要 8 块 H100 而集群里没有匹配节点，Karpenter 直接供应一个，而不是去扩容现有的组。

**整合陷阱**：Karpenter 默认的 `consolidationPolicy: WhenEmptyOrUnderutilized` 对 GPU 池很危险。它会终止一个正在运行的 GPU 节点，把 pod 迁到更便宜、尺寸更合适的实例上。对推理负载，这意味着赶跑正在处理的请求，并在新节点上重新加载 70B 模型。损失是几分钟的容量外加请求失败。

GPU 池的安全配置：

```yaml
disruption:
  consolidationPolicy: WhenEmpty
  consolidateAfter: 1h
```

让 Karpenter 一小时后整合真正空掉的节点，但绝不赶跑正在运行的任务。

> Karpenter watches pending pods and provisions nodes within ~45-60 seconds (Cluster Autoscaler typically takes 90-120 seconds for GPU nodes). ... **The consolidation trap**: Karpenter's default `consolidationPolicy: WhenEmptyOrUnderutilized` is dangerous for GPU pools. It will terminate a running GPU node to migrate pods to a cheaper right-sized instance. For inference workloads that means evicting running requests and reloading a 70B model on the new node. Loss is minutes of capacity plus request failures. ... Lets Karpenter consolidate truly empty nodes after an hour but never evict a running job.

### Layer 2 — gang scheduling (KAI Scheduler) · 第二层 —— gang 调度（KAI Scheduler）

KAI Scheduler（项目原名 "Karp"，后改名）处理默认 kube-scheduler 不做的事：

**Gang 调度** —— 全有或全无。一个需要 8 块 GPU 的分布式推理 pod，要么 8 个一起启动，要么一个都不启动。没有它，你就会掉进局部分配陷阱：8 个 pod 起了 7 个，无限期等待，烧钱。

**拓扑感知** —— 知道哪些 GPU 共享 NVLink、哪些在同一机架、哪些之间有 InfiniBand，并据此放置 pod。DeepSeek-V3 67B 的张量并行负载必须待在同一个 NVLink 域里；KAI Scheduler 会尊重这一点。

**层级队列** —— 多个团队用优先级和配额竞争同一个 GPU 池。只有优先级规则允许时，团队 A 的生产紧急任务才会被团队 B 的训练任务抢占。

KAI 作为二级 scheduler 与 kube-scheduler 并存部署；你给工作负载打注解来使用它。Ray 和 vLLM production-stack 都有集成。

> **Gang scheduling** — schedule all-or-nothing. A distributed inference pod requiring 8 GPUs either all 8 start together or none do. Without this, you get the partial-allocation trap: 7 of 8 pods start, wait indefinitely, burn money.
> **Topology awareness** — know which GPUs share NVLink, which sit on the same rack, which have InfiniBand between them. Place pods accordingly. A DeepSeek-V3 67B tensor-parallel workload must stay on one NVLink domain; KAI Scheduler respects that.
> **Hierarchical queues** — multiple teams compete for the same GPU pool with priority and quota. Team A's production pinch gets preempted by Team B's training job only if priority rules allow.
> KAI is deployed alongside kube-scheduler as a secondary scheduler; you annotate workloads to use it. Ray and vLLM production-stack both integrate.

### Layer 3 — application-level signals · 第三层 —— 应用层信号

**HPA 陷阱**：`DCGM_FI_DEV_GPU_UTIL` 是一个占空比指标——它测的是 GPU 在每个采样间隔里有没有在做活。100% 利用率可能是 10 个并发请求，也可能是 100 个；反正 GPU 都忙。按占空比扩缩就是盲扩。

更糟的是，vLLM 和类似引擎会预分配 KV cache 内存（最多到 `--gpu-memory-utilization`）。哪怕只有一个请求，内存占用也停在 90% 附近。基于内存的 HPA 永远不会缩容。

**2026 年的替代信号**：

- 队列深度（等待 prefill 的请求数）。
- KV cache 利用率（有多大比例的 block 分配给了活跃序列）。
- 每副本 P99 TTFT（你的 SLA 信号）。
- Goodput（每秒满足全部 SLO 的请求数）。

NVIDIA Dynamo Planner 和 llm-d Workload Variant Autoscaler 消费这些信号并扩缩副本。对 LLM serving 来说，它们完全取代 HPA。

> **The HPA trap**: `DCGM_FI_DEV_GPU_UTIL` is a duty-cycle metric — it measures whether the GPU was doing work at each sampling interval. 100% utilization could mean 10 concurrent requests or 100; the GPU was busy either way. Scaling on duty cycle is scaling blindly.
> Worse, vLLM and similar engines pre-allocate KV cache memory (up to `--gpu-memory-utilization`). Memory usage stays near 90% even at one request. Memory-based HPA never scales down.
> NVIDIA Dynamo Planner and llm-d Workload Variant Autoscaler consume these signals and scale replicas. They replace HPA entirely for LLM serving.

### When to use what · 什么时候用什么

| 扩缩决策 | 工具 |
|----------------|------|
| 加/删节点 | Karpenter |
| 调度多 GPU 任务 | KAI Scheduler |
| 加/删副本 | Dynamo Planner / llm-d WVA（或基于队列深度的自定义 HPA） |
| 选 GPU 类型 | Karpenter NodePool |
| 抢占低优先级任务 | KAI Scheduler 队列 |

### Disaggregated prefill/decode complicates everything · 分离式 prefill/decode 让一切更复杂

如果你跑分离式 prefill/decode（Phase 17 · 17），你就有两类 pod、两套扩缩触发条件：prefill pod 按队列深度扩，decode pod 按 KV cache 压力扩。llm-d 把它们暴露为带各自 HPA 的独立 `Services`。不要试图用一个 HPA 同时罩住两边。

> If you run disaggregated prefill/decode (Phase 17 · 17), you have two pod classes with different scaling triggers: prefill pods scale on queue depth, decode pods scale on KV cache pressure. llm-d exposes these as separate `Services` with per-role HPA. Do not try to put a single HPA in front of both.

### Cold start matters here too · 冷启动在这里同样重要

冷启动缓解（Phase 17 · 10）正是节点供应时间变成用户可见时间的地方。Karpenter 45-60 秒的预热，加上 20GB 的模型加载，加上引擎初始化，意味着一个从零开始的请求要 2-5 分钟。给 SLO 关键路径保留一个温池（`min_workers=1`），或者在应用层用 Modal 式的 checkpointing。

> Cold-start mitigation (Phase 17 · 10) is where node provisioning time becomes user-visible. Karpenter's 45-60 second warm-up plus a 20GB model load plus engine init means a from-zero request takes 2-5 minutes. Keep a warm pool (`min_workers=1`) for SLO-critical paths, or use Modal-style checkpointing at application layer.

### Numbers you should remember · 你该记住的数字

- Karpenter 节点供应：约 45-60 秒，对比 Cluster Autoscaler 约 90-120 秒（GPU 节点）。
- KAI Scheduler 防住局部分配浪费——8 缺 1 陷阱。
- `DCGM_FI_DEV_GPU_UTIL` 作为 HPA 信号：坏的；改用队列深度或 KV 利用率。
- Karpenter `WhenEmptyOrUnderutilized`：会终止正在运行的 GPU 任务。推理用 `WhenEmpty + consolidateAfter: 1h`。

> - Karpenter node provisioning: ~45-60s vs Cluster Autoscaler ~90-120s (GPU nodes).
> - KAI Scheduler prevents partial-allocation waste — 7-of-8 trap.
> - `DCGM_FI_DEV_GPU_UTIL` as HPA signal: broken; use queue depth or KV utilization.
> - Karpenter `WhenEmptyOrUnderutilized`: terminates running GPU jobs. Use `WhenEmpty + consolidateAfter: 1h` for inference.

```figure
autoscaling
```

## Use It · 实战用法

`code/main.py` 在一个突发的 GPU 负载上模拟一个三层自动扩缩器。对比朴素 HPA（占空比）、队列深度 HPA 和 KAI gang 调度扩缩。报告未满足请求数、GPU 闲置分钟数和一个综合得分。

> `code/main.py` simulates a three-layer autoscaler on a bursty GPU workload. Compares naive HPA (duty cycle), queue-depth HPA, and KAI-gang-scheduled scaling. Reports unmet requests, idle-GPU minutes, and a composite score.

## Ship It · 交付

本课产出 `outputs/skill-gpu-autoscaler-plan.md`。给定集群拓扑、负载形态和 SLO，它设计一个三层自动扩缩方案。

> This lesson produces `outputs/skill-gpu-autoscaler-plan.md`. Given cluster topology, workload shape, and SLO, it designs a three-layer autoscaling plan.

## Exercises · 练习

1. 运行 `code/main.py`。突发负载下，朴素占空比 HPA 会丢掉多少队列深度 HPA 能接住的请求？差距从哪来？
2. 为一个在 H100 SXM5 上服务 Llama 3.3 70B FP8 的集群设计 Karpenter NodePool。写明 `capacity-type`、`disruption.consolidationPolicy`、`consolidateAfter`，以及一条把非 GPU 负载挡在这些节点之外的 taint。
3. 团队报告部署卡在 Pending，理由是「GPU 有空的但 pod 调度不上」。诊断——问题出在 Karpenter、kube-scheduler 还是 KAI Scheduler？哪些指标能确认？
4. 为分离式部署的 prefill pod 选一个扩缩信号，为 decode pod 选另一个。两个都给出理由。
5. 计算一个 24x7 生产服务上 `WhenEmptyOrUnderutilized` 整合陷阱的成本：平均每天 60 次掉请求事件，P99 TTFT > 10s。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| Karpenter | "节点供应器" | Kubernetes 节点自动扩缩器；分钟以内的供应速度 |
| Cluster Autoscaler | "老扩缩器" | Kubernetes 节点自动扩缩器前身；更慢，按组扩缩 |
| KAI Scheduler | "GPU 调度器" | 提供 gang + 拓扑 + 队列的二级调度器 |
| Gang scheduling | "全有或全无" | N 个 pod 原子性一起调度，否则全部推迟 |
| Topology awareness | "机架感知" | 基于 NVLink/IB/机架位置放置 pod |
| `DCGM_FI_DEV_GPU_UTIL` | "GPU 利用率" | 占空比指标；对 LLM 不是有效的扩缩信号 |
| Queue depth | "排队的请求" | prefill 受限扩缩的正确 HPA 信号 |
| KV cache utilization | "内存压力" | decode 受限扩缩的正确 HPA 信号 |
| Consolidation | "Karpenter 整合" | 终止节点、迁去更便宜的实例类型 |
| `WhenEmpty + 1h` | "安全整合" | 不会赶跑正在运行 GPU 任务的策略 |

## Further Reading · 延伸阅读

- [KAI Scheduler GitHub](https://github.com/kai-scheduler/KAI-Scheduler) —— 设计文档与配置示例。
- [Karpenter Disruption Controls](https://karpenter.sh/docs/concepts/disruption/) —— 整合策略语义与 GPU 安全默认值。
- [NVIDIA — Disaggregated LLM Inference on Kubernetes](https://developer.nvidia.com/blog/deploying-disaggregated-llm-inference-workloads-on-kubernetes/) —— Dynamo Planner 的扩缩信号。
- [Ray docs — KAI Scheduler for RayClusters](https://docs.ray.io/en/latest/cluster/kubernetes/k8s-ecosystem/kai-scheduler.html) —— Ray 集成模式。
- [AWS EKS Compute and Autoscaling Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/aiml-compute.html) —— 托管 Kubernetes 场景的专属指南。
- [llm-d GitHub](https://github.com/llm-d/llm-d) —— Workload Variant Autoscaler 设计。
