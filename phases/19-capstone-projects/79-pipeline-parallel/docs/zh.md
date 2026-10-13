# Pipeline Parallel and Bubble Analysis · 流水线并行与气泡分析

> 张量并行（tensor parallelism）把矩阵乘法切分到各个 rank 上；流水线并行（pipeline parallelism）把模型本身切分到各个 rank 上，每个 rank 承载一个阶段（stage）。微批次（microbatch）依次流过整条流水线。流水线开头和结尾的空转时间就是气泡（bubble）；把气泡压到最小，正是这门手艺的全部。

> Tensor parallelism splits the matrix multiply across ranks. Pipeline parallelism splits the model across ranks, one stage per rank. Microbatches flow through the pipeline. The empty time at the start and end is the bubble; minimising it is the whole craft.

**类型（Type）:** 构建（Build）
**语言（Languages）:** Python
**先修（Prerequisites）:** Phase 19 Track C 第 42-49 课
**时间（Time）:** ~90 分钟

## Learning Objectives · 学习目标

- 把一个顺序模型切成 N 个阶段，在 N 个 rank 上模拟前向流水线。
- 用 GPipe 调度（先灌满前向、再做反向）让 M 个微批次流过流水线，并计算气泡占比（bubble fraction）。
- 将气泡与 Megatron-LM 和 PipeDream 使用的交错式 1F1B 调度做对比。
- 论证阶段划分策略：每阶段计算量均衡，比每阶段参数量均衡更重要。

> Split a sequential model into N stages and simulate a forward pipeline across N ranks.
> Schedule M microbatches through the pipeline using the GPipe schedule (forward-only fill, then backward) and compute the bubble fraction.
> Compare bubble against the interleaved 1F1B schedule used in Megatron-LM and PipeDream.
> Defend stage assignment: equal compute per stage matters more than equal parameter count per stage.

## The Problem · 问题

一个 70B 参数的模型光参数本身在 fp16 下就要占 140 GB，没有一张消费级 GPU 装得下。ZeRO-3 把参数分片（shard）到各个 rank，但每个 rank 在每次前向时仍要对完整的层做 allgather，每层都要付出 log(N) 跳的通信。流水线并行走了另一条路：把模型切成 N 个阶段，每个 rank 放一个阶段。第 1 层的前向在 rank 0 上算完，把激活张量（activation）交给 rank 1；rank 1 跑第 2 层，再交给 rank 2；以此类推。反向沿相反方向流动。每个 rank 只持有自己那一个阶段，所以内存线性下降；但计算是串行的——这正是气泡问题的来源。

气泡是流水线开头（等第一个微批次到达最后一个阶段）和结尾（等最后一个微批次排空流回）的空转时间。设 M 个微批次、N 个阶段，每阶段的气泡占比是 (N-1)/(M+N-1)。M=8、N=4 时是 27%；M=64、N=4 时是 4.5%。每步的微批次越多，气泡越小——这意味着每个微批次的批量要更小，而这正是驱动微批次设计的那个约束。

> A 70B-parameter model in fp16 needs 140 GB of parameters alone. No consumer GPU holds it. ... Pipeline parallel takes a different route: cut the model into N stages and put one stage on each rank. ... Memory drops linearly because each rank only holds one stage; compute is sequential, which is the bubble problem.
> The bubble is the idle time at the start of the pipeline (waiting for the first microbatch to reach the last stage) and at the end (waiting for the last microbatch to drain back through). With M microbatches and N stages the per-stage bubble fraction is (N-1)/(M+N-1). At M=8, N=4 that is 27%. At M=64, N=4 it is 4.5%.

## The Concept · 概念

```mermaid
flowchart LR
  R0[rank 0: stage 0 / layer 0] --> R1[rank 1: stage 1 / layer 1]
  R1 --> R2[rank 2: stage 2 / layer 2]
  R2 --> R3[rank 3: stage 3 / loss]
  R3 -.backward.-> R2
  R2 -.backward.-> R1
  R1 -.backward.-> R0
```

### GPipe schedule · GPipe 调度

先把全部 M 个微批次灌满前向，再开始任何反向；然后按相反顺序排空反向。每个微批次的激活都必须保存到它自己的反向为止，所以内存随 M 线性增长。前向占 M+N-1 个周期，反向再占 M+N-1 个周期。每阶段的有效工作是 2M 个周期；每阶段的气泡是 2(N-1) 个周期。当前向和反向各占一个时间单位时，气泡占比为 (N-1)/(M+N-1)。把 M 取得远大于 N，就能把气泡藏起来。

> Fill the pipeline forward with all M microbatches before starting any backward; then drain backward in reverse. ... Activations from every microbatch must be held until its backward, so memory grows linearly with M. ... Bubble fraction is (N-1)/(M+N-1) when each forward and backward takes one unit of time. Picking M much greater than N hides the bubble.

### 1F1B schedule · 1F1B 调度

交错进行：某个微批次的前向一到达最后一个阶段，就立刻启动它的反向，让它往回流。该调度让每个阶段交替执行一次前向、一次反向。气泡仍然是 N-1，但激活内存的上界由流水线深度决定，而不是由微批次数量决定。生产级流水线用的是 1F1B（Megatron、PipeDream）。本课先实现更简单的 GPipe，1F1B 留作练习。

> Interleave: as soon as a microbatch's forward reaches the last stage, start its backward and let it stream back. The schedule alternates one forward and one backward per stage. Bubble is still N-1 but activation memory is bounded by the pipeline depth, not the microbatch count. Production pipelines use 1F1B (Megatron, PipeDream). The lesson implements GPipe first because it is simpler, and 1F1B as an exercise.

### Why equal compute per stage matters · 为什么每阶段计算量均衡更重要

如果阶段 0 耗时 50 ms、阶段 1 耗时 100 ms，那么每个周期都被阶段 1 卡住：其余阶段每个周期要空等 50 ms 等阶段 1 放行。按参数量均衡是错误的坐标轴：transformer 的计算量由每层的 attention 加 MLP 主导，embedding 层参数很多但计算很少。阶段划分应该让每阶段的 FLOPs 均衡，而不是每阶段的权重数均衡。

> If stage 0 takes 50 ms and stage 1 takes 100 ms, every cycle is gated on stage 1. The other stages idle 50 ms per cycle waiting for stage 1 to release. Equal parameter count is the wrong axis: a transformer's compute is dominated by attention plus MLP per layer, and embedding layers have many parameters but little compute. Stage assignment should equalise FLOPs per stage, not weights per stage.

### Microbatch versus batch · 微批次与批次

流水线每步跑 M 个微批次，每个大小为 B，等效批量大小（effective batch size）就是 M*B。流水线一步结束时的梯度，就是这 M*B 个样本合并出来的梯度。气泡占比取决于 M；优化器看到的却是 M*B。调 M 就是在做权衡：气泡（M 越大越小）对每微批次内存（GPipe 下 M 越大激活内存越高）。

> A pipeline runs M microbatches of size B each. The effective batch size is M*B. The gradient at the end of a pipeline step is the gradient on the combined M*B examples. Bubble fraction depends on M; the optimiser sees M*B. Tuning M means trading bubble (lower with high M) against per-microbatch memory (higher activation memory with high M for GPipe).

```figure
cd-pipeline-bubble
```

## Build It · 动手造

`code/main.py` 实现了：

- `PipelineStage`：一个小 `nn.Module`，持有一个阶段的参数，暴露 `forward(activation)`。
- `Pipeline(stages, num_microbatches)`：在模拟阶段上编排 GPipe 调度，使用每阶段模拟的墙钟时间（wall-clock）。
- `bubble_fraction(num_stages, num_microbatches)`：闭式解 (N-1)/(M+N-1)。
- 一个 4 阶段 demo，打印逐微批次的执行轨迹和实测气泡占比。

运行：

```bash
python3 code/main.py
```

输出：一张阶段×微批次的甘特图，以及实测气泡百分比与闭式解预测的对照。

> - `PipelineStage`: a small `nn.Module` that holds one stage's parameters and exposes `forward(activation)`.
> - `Pipeline(stages, num_microbatches)`: orchestrates the GPipe schedule on simulated stages using simulated wall-clock per stage.
> - `bubble_fraction(num_stages, num_microbatches)`: closed-form (N-1)/(M+N-1).
> - A 4-stage demo that prints the per-microbatch trace and the measured bubble fraction.
> Output: a stage-by-microbatch Gantt chart and the bubble percentage against the closed-form prediction.

## Production patterns in the wild · 生产环境的实战模式

三种模式把流水线并行加固到可以上线的程度。

**激活检查点（activation checkpointing）与流水线配套。** GPipe 下 M 个微批次同时在途时，激活内存是单个微批次的 M 倍。激活检查点在反向时重算前向，用计算换内存；正是这个组合让流水线能处理长序列。

**阶段均衡靠实测，不靠假设。** 生产团队会先跑一轮剖析（profiling），在目标硬件上实测每层的真实计算量（FLOPs 和墙钟时间），再按实测结果划分。Megatron-LM 的 `--num-layers-per-stage` 旗标接受一个列表，当各阶段每层成本不同时允许层数不均。

**send-recv 调度必须避免死锁。** 如果每个阶段都先 send 后 recv，流水线会在通信上死锁。标准修法是交错：偶数 rank 的阶段先 send 再 recv，奇数 rank 的阶段先 recv 再 send。本课显式调度各 rank，让这个模式清晰可见。

> **Activation checkpointing pairs with pipeline.** With M microbatches in flight on GPipe, activation memory is M times one microbatch. Activation checkpointing recomputes the forward at backward time, trading compute for memory; the combination is what makes pipeline tractable for long sequences. ... **Stage balance is measured, not assumed.** Production teams run a profiling pass that measures actual per-layer compute (FLOPs and wall-clock) on the target hardware, then partition by that measurement. ... **Send-recv schedule must avoid deadlock.** A pipeline that has every stage send before receive deadlocks on the wire. The standard fix is to interleave: even-rank stages send first then recv, odd-rank stages recv first then send.

## Use It · 实战用法

生产级实现：

- **Megatron-LM.** 大规模流水线并行的参照实现。使用 1F1B，支持张量并行 + 流水线并行 + 数据并行的组合。
- **DeepSpeed Pipeline.** 与 ZeRO 集成；ZeRO-1 + 流水线是最大型开源模型的常见组合。
- **PyTorch Pipe.** PyTorch 原生的流水线封装，构建在 `torch.distributed.pipeline.sync.Pipe` 之上。

> - **Megatron-LM.** The reference for pipeline parallel at scale. Uses 1F1B and supports tensor + pipeline + data parallel combined.
> - **DeepSpeed Pipeline.** Integrates with ZeRO; ZeRO-1 + pipeline is a common combo for the largest open models.
> - **PyTorch Pipe.** The PyTorch-native pipeline wrapper, built on `torch.distributed.pipeline.sync.Pipe`.

## Ship It · 交付

第 80 课把各阶段的参数分片存进分片检查点（sharded checkpoint）。第 81 课在端到端 demo 上组合 DDP + ZeRO + 流水线（神似即可；demo 为控制运行时长把流水线保持为模拟实现）。

> Lesson 80 stores the per-stage parameter shards in the sharded checkpoint. Lesson 81 composes DDP + ZeRO + pipeline on the end-to-end demo (in spirit; the demo keeps the pipeline simulated for runtime).

## Exercises · 练习

1. 实现 1F1B，验证气泡占比与 GPipe 一致，但激活内存有上界。
2. 在更深的模型上实测各阶段耗时，按实测墙钟时间重新均衡阶段。
3. 加上跨流水线微批次的梯度累积，验证该梯度等于等效全批量前向的梯度。
4. 把流水线与激活检查点配对，测量内存下降对比计算开销。
5. 把流水线与 DDP 结合（每个流水线 rank 在数据并行组内做副本），推演二维调度。

> Implement 1F1B and verify the bubble fraction matches GPipe but activation memory is bounded. ... Profile real per-stage time on a deeper model and rebalance stages by measured wall-clock. ... Add gradient accumulation across pipeline microbatches and check the gradient equals the gradient of the equivalent full-batch forward. ... Pair the pipeline with activation checkpointing and measure the memory drop versus compute cost. ... Combine pipeline with DDP (each pipeline rank is replicated across a data-parallel group) and reason through the 2D schedule.

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|----------------|------------------------|
| Pipeline | 「按深度切模型并行」 | 每个 rank 一个阶段，激活逐阶段流动 |
| Bubble | 「流水线空转时间」 | 开头 + 结尾共 (N-1) 步部分阶段无活可干 |
| Microbatch | 「批量的一片」 | 一次前向/反向单元；M 越大气泡越小 |
| GPipe | 「先灌满再排空」 | 全部 M 个前向做完才做反向；激活内存高 |
| 1F1B | 「交错调度」 | 每阶段一前向一反向；激活内存有上界 |

## Further Reading · 延伸阅读

- [Huang et al, GPipe: Efficient Training of Giant Neural Networks](https://arxiv.org/abs/1811.06965)
- [Narayanan et al, PipeDream: Generalized Pipeline Parallelism for DNN Training](https://arxiv.org/abs/1806.03377)
- [Megatron-LM pipeline parallel docs](https://github.com/NVIDIA/Megatron-LM)
- Phase 19 Lesson 76 —— 调度所用的 send/recv 原语
- Phase 19 Lesson 78 —— ZeRO 与流水线正交，且经常组合使用
