# DualPipe Parallelism · DualPipe 并行

> DeepSeek-V3 在 2,048 块 H800 上训练，MoE 专家散布在不同节点之间。跨节点的专家 all-to-all 通信，每 1 GPU 小时计算就要配 1 GPU 小时通信。GPU 有一半时间在空转。DualPipe（DeepSeek，2024 年 12 月）是一条双向流水线，把前向和反向计算与它们触发的 all-to-all 通信重叠起来。气泡（bubble）下降、吞吐上升，而维护两份模型参数拷贝（名字里那个「dual」）在专家并行（Expert Parallelism）早已把专家摊到各 rank 上的前提下是廉价的。本课是一堂 Learn 型走读：DualPipe 到底在做什么，以及 Sea AI Lab 的 DualPipeV 改进为什么能砍掉 2 倍参数成本、代价只是一个略紧的气泡。

> DeepSeek-V3 was trained on 2,048 H800 GPUs with MoE experts scattered across nodes. Cross-node expert all-to-all communication cost 1 GPU-hour of comm for every 1 GPU-hour of compute. GPUs were idle half the time. DualPipe (DeepSeek, Dec 2024) is a bidirectional pipeline that overlaps forward and backward computation with the all-to-all comms they trigger. Bubbles drop, throughput climbs, and the keeping of two model-parameter copies (the "dual" that gives the name) is cheap once Expert Parallelism is already spreading experts across ranks anyway. This lesson is a Learn-type walkthrough of what DualPipe actually does and why Sea AI Lab's DualPipeV refinement drops the 2x parameter cost at the expense of a marginally tighter bubble.

**Type:** Learn
**Languages:** Python (stdlib, schedule simulator)
**Prerequisites:** Phase 10 · 05 (distributed training, FSDP, DeepSpeed), Phase 10 · 14 (open-model architectures and MoE)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 说出 DualPipe 前向-反向 chunk 的四个组成部分，以及为什么每个都有自己的重叠窗口。
- 解释规模化的流水线气泡问题，以及「无气泡」在实践和营销里各是什么意思。
- 为 8 个 PP rank、16 个微批（micro-batch）手工走查一条 DualPipe 调度，确认前向流和反向流互相填满对方的空槽。
- 陈述 DualPipeV（Sea AI Lab, 2025）的取舍：砍掉 2 倍参数复制，代价是专家并行未激活时气泡略大。

> Name the four components of a DualPipe forward-backward chunk and why each one gets its own overlap window.
> Explain the pipeline bubble problem at scale, and what "bubble-free" means in practice versus in marketing.
> Trace a DualPipe schedule by hand for 8 PP ranks and 16 micro-batches and confirm the forward and reverse streams fill each other's idle slots.
> State the tradeoff DualPipeV (Sea AI Lab, 2025) makes: drops the 2x parameter replication at the cost of a slightly larger bubble when Expert Parallelism is inactive.

## The Problem · 问题在哪

在 2k 块 H800 上训练一个 671B 的 MoE 模型，会撞上三个互相叠加的瓶颈：

1. **内存压力。** 每块 GPU 持有模型的一片。61 层、128 头、序列 8k 的激活内存巨大。
2. **流水线气泡。** 传统流水线并行（GPipe、1F1B）会让 GPU 在等待本阶段输入或梯度时空转。8 个阶段时，即使用 1F1B 调度，也大约有 12% 的 GPU 时间可能是气泡。
3. **跨节点 all-to-all。** 带专家并行的 MoE 把专家散到各节点。每次前向都要触发一次 all-to-all 把 token 派发给专家，再一次把结果合并回来。到 2k GPU 规模，这轻松变成 1:1 的计算-通信比。

每一个都有单独的解法：内存靠梯度 checkpointing，流水线气泡靠 Zero Bubble（Sea AI Lab, 2023），all-to-all 靠专家并行通信 kernel。DualPipe 做的是让它们协同。这个调度在单个前向-反向 chunk 内部重叠计算与通信，从流水线两端同时注入微批，并利用 resulting 的调度把 all-to-all 藏进计算窗口里。

报告结果：流水线气泡近乎消灭，DeepSeek-V3 的 14.8T token 训练运行中 GPU 利用率超过 95%。

> Training a 671B MoE model on 2k H800 GPUs runs into three compounding bottlenecks:
> 1. **Memory pressure.** Each GPU holds a slice of the model. Activation memory at sequence 8k across 61 layers on 128 heads is enormous.
> 2. **Pipeline bubbles.** Traditional pipeline parallelism (GPipe, 1F1B) leaves GPUs idle while they wait for their stage's input or gradient. At 8 stages, roughly 12% of GPU time can be bubble even with 1F1B scheduling.
> 3. **Cross-node all-to-all.** MoE with expert parallelism scatters experts across nodes. Every forward pass triggers an all-to-all to dispatch tokens to their experts, and another to combine. At 2k GPUs this easily becomes a 1:1 compute-to-comm ratio.
> Each of these has separate solutions: gradient checkpointing for memory, Zero Bubble (Sea AI Lab, 2023) for pipeline bubbles, expert-parallel comm kernels for all-to-all. What DualPipe does is make them play together. The schedule overlaps compute and comm within a single forward-backward chunk, injects micro-batches from both ends of the pipeline simultaneously, and uses the resulting schedule to hide all-to-all inside the compute windows.
> Reported result: near-elimination of pipeline bubbles, over 95% GPU utilization in DeepSeek-V3's 14.8T-token training run.

## The Concept · 概念

### Pipeline parallelism refresher · 流水线并行温习

把 N 层模型切到 P 个设备上。设备 `i` 持有第 `i * N/P .. (i+1) * N/P - 1` 层。一个微批从设备 0 到 P-1 正向流过，再从 P-1 到 0 反向流回。每个设备只有在上一设备发来输出后才能开始自己的前向，只有下游设备发来上游梯度后才能开始反向。

GPipe（Huang et al., 2019）一次调度一个微批，浪费了大部分 GPU 时间。1F1B（Narayanan et al., 2021）为多个微批交错安排前向和反向。Zero Bubble（Qi et al., 2023）把反向拆成两部分——对输入的反向（B）和对权重的反向（W）——并调度它们去填气泡。经过 Zero Bubble，流水线几乎收紧了。

DualPipe 是下一步。它在之上加两个想法：

> Split an N-layer model across P devices. Device `i` holds layers `i * N/P .. (i+1) * N/P - 1`. A micro-batch flows forward through devices 0 to P-1, then backward from P-1 to 0. Each device can only start its forward stage when the prior device sends its output and can only start backward when the downstream device sends the upstream gradient.
> GPipe (Huang et al., 2019) schedules one micro-batch at a time, which wastes most GPU time. 1F1B (Narayanan et al., 2021) interleaves forward and backward passes for multiple micro-batches. Zero Bubble (Qi et al., 2023) splits the backward pass into two parts — backward-for-input (B) and backward-for-weights (W) — and schedules them to fill the bubble. After Zero Bubble, the pipeline is almost tight.
> DualPipe is the next step. It adds two ideas on top:

### Idea 1: chunk decomposition · 想法 1：chunk 分解

每个前向 chunk 拆成四个组件：

- **注意力。** Q/K/V 投影、注意力、输出投影。
- **All-to-all 派发。** 把 token 送到其专家的跨节点通信。
- **MLP。** MoE 专家计算。
- **All-to-all 合并。** 把专家输出带回来的跨节点通信。

反向 chunk 再加上每一项的梯度版本。DualPipe 这样调度：all-to-all 派发与下一个 chunk 的注意力计算并行，all-to-all 合并与再下一个 chunk 的 MLP 计算并行。

> Each forward chunk is split into four components:
> - **Attention.** Q/K/V projections, attention, output projection.
> - **All-to-all dispatch.** Cross-node communication that sends tokens to their experts.
> - **MLP.** The MoE expert computation.
> - **All-to-all combine.** Cross-node communication that brings expert outputs back.
> A backward chunk adds gradient versions of each of these. DualPipe schedules them so that all-to-all dispatch happens in parallel with the attention compute of the next chunk, and all-to-all combine happens in parallel with the MLP compute of the following chunk.

### Idea 2: bidirectional scheduling · 想法 2：双向调度

大多数流水线调度从阶段 0 注入微批、向阶段 P-1 流动。DualPipe 从两端同时注入微批。阶段 0 看到源自自己的前向微批；阶段 P-1 也看到源自自己的前向微批。两股流在中间会合。

为此，设备 `i` 必须同时持有流水线前段的第 `i` 层和后段的第 `P - 1 - i` 层。这就是 DualPipe 名字里的「dual」：每个设备保存它需要服务的模型层的两份拷贝（每个方向一份）。在 DeepSeek-V3 的规模上，这是 2 倍参数复制成本。它负担得起，因为专家并行已经把 MoE 专家摊得足够薄，把非专家层复制两份只是小钱。

关键在于：一个方向的前向流与另一个方向的反向流，恰好重叠在单向调度中本该出现气泡的位置。气泡消失了。

> Most pipeline schedules inject micro-batches from stage 0 and flow toward stage P-1. DualPipe injects micro-batches from BOTH ends. Stage 0 sees forward micro-batches originating there; stage P-1 sees forward micro-batches originating there too. The two streams meet in the middle.
> For this to work, device `i` must hold BOTH the early-pipeline layer `i` AND the late-pipeline layer `P - 1 - i`. That is the "dual" part of DualPipe: each device keeps two copies of the model layers it needs to serve (one for each direction). At DeepSeek-V3's scale, this is a 2x parameter replication cost. It is affordable because Expert Parallelism already spreads the MoE experts so thin that replicating the non-expert layers twice is small potatoes.
> Crucially, the forward stream in one direction and the backward stream in the other direction overlap exactly where the bubbles would be in a single-direction schedule. The bubbles vanish.

### A hand-traced schedule · 手工走查的调度

取 P = 4 个 rank、8 个微批，分为 4 前向 / 4 反向。时间从左到右流动；每一行是一个设备 rank。

```
           Time →
rank 0:  F1 F2 F3 F4  F5R F6R F7R F8R  B1 B2 B3 B4  ...
rank 1:     F1 F2 F3  F4/F5R F6R F7R   B1 B2 ...
rank 2:        F1 F2  F3/F5R F4/F6R    B1 ...
rank 3:           F1  F2/F5R F3/F6R    ...
```

读「F4/F5R」这个记法：rank 1 在同一个时间槽里，既跑微批 4 的前向（沿流水线从左到右），又跑微批 5 的前向（从右到左）。这就是「双向」在操作层面的含义。

在 rank 2，两股交叉流更早重叠；在 rank 0 和 P-1，重叠最晚。在调度的稳定中段，每个 rank 都在把 X 方向的前向与 Y 方向的反向重叠起来。计算是满的。前向的 all-to-all 派发藏进反向计算里，all-to-all 合并藏进前向计算里。气泡被挤了出去。

> Consider P = 4 ranks, 8 micro-batches, divided 4 forward / 4 reverse. Time moves left to right; rows are device ranks.
> Reading the "F4/F5R" notation: rank 1 is running forward of micro-batch 4 (going left-to-right in the pipeline) AND forward of micro-batch 5 (going right-to-left) in the same time slot. That is what "bidirectional" means operationally.
> At rank 2 the cross streams overlap sooner, at rank 0 and P-1 they overlap latest. In the stable middle phase of the schedule, every rank runs forward-of-X-direction overlapped with backward-of-Y-direction. Compute is busy. All-to-all dispatches for the forward pass hide inside backward compute. All-to-all combines hide inside forward compute. The bubbles are squeezed out.

### Bubble accounting · 气泡核算

标准 1F1B 的流水线气泡（每个 rank 浪费的时间）：

```
bubble_1F1B = (P - 1) * forward_chunk_time
```

Zero Bubble 的改进能压低它，但压不到零。DualPipe 在稳定阶段，只要微批数能被 2 倍流水线深度整除，气泡就是零。稳定阶段之外（warmup 和 cooldown），有一些气泡，但它不随微批数增长——这是论文强调的关键性质。

用营销语言说：「bubble-free」。用技术语言说：气泡不随微批数增长。Sea AI Lab 的后续分析（DualPipeV / Cut-in-half）表明：只有当专家并行不是瓶颈时才有完全的零气泡；在 EP 驱动的 all-to-all 下，调度上总要做出些妥协。

> Standard 1F1B pipeline bubble (time wasted per rank):
> Zero Bubble refinement brings it down but not to zero. DualPipe, in the stable phase, has zero bubble if the micro-batch count is divisible by 2 times the pipeline depth. Outside the stable phase (warmup and cooldown), there is some bubble but it does not grow with the number of micro-batches — a key property the paper highlights.
> In marketing terms: "bubble-free". In technical terms: bubbles do not grow with micro-batch count. Sea AI Lab's follow-up analysis (DualPipeV / Cut-in-half) shows the full zero-bubble only when Expert Parallelism is not the bottleneck; with EP-driven all-to-all, some scheduling compromise is always present.

### DualPipeV — the refinement · DualPipeV——改进版

Sea AI Lab（2025）观察到：当 EP 通信重叠不是重点时，2 倍参数复制是浪费。他们的 DualPipeV 调度把双向注入折叠成一个「V 形」调度，只跑单份参数拷贝。气泡比 DualPipe 略大，但内存节省可观。DeepSeek 在其开源 DualPipe 实现中把 DualPipeV 采纳为 EP-off 模式。

取舍如下：

| Feature | DualPipe | DualPipeV | 1F1B | Zero Bubble |
|---------|---------|-----------|------|------------|
| 每设备参数拷贝 | 2 | 1 | 1 | 1 |
| 气泡 vs 微批数 | 恒定 | 缓慢增长 | 增长 | 增长 |
| 计算-通信重叠 | 完全 | 部分 | 极少 | 部分 |
| 适用场景 | EP 重的 MoE | 稠密或 EP 轻 | 基线 | 任何流水线 |

> Sea AI Lab (2025) observed that the 2x parameter replication is wasteful when EP comm overlap is not the point. Their DualPipeV schedule folds the bidirectional injection into a "V-shape" schedule that runs on a single parameter copy. The bubble is slightly larger than DualPipe's, but the memory savings are substantial. DeepSeek adopted DualPipeV in their open-source DualPipe implementation as an EP-off mode.
> The tradeoff:

### What it means for a 14.8T-token run · 对一次 14.8T token 运行意味着什么

DeepSeek-V3 的预训练在 2,048 块 H800 上、约 280 万 GPU 小时里消耗了 14.8T token。如果用朴素的 1F1B，他们会在流水线气泡上损失 12-15%——即 34-42 万 GPU 小时，足够训练一个完整的 70B 模型。DualPipe 把其中大部分救了回来。没有内部日志很难精确量化它的贡献，但论文的说法是：训练全程平均 GPU 利用率超过 95%。

对更小的运行（1k GPU 以下），DualPipe 是杀鸡用牛刀——流水线气泡相对总成本更小，稠密模型训练也很少撞上 all-to-all 瓶颈。对多千卡规模的前沿 MoE 训练，它实际上是必需品。

> DeepSeek-V3's pre-training consumed 14.8T tokens on 2,048 H800 GPUs in roughly 2.8M GPU-hours. With naive 1F1B, they would have lost 12-15% of that to pipeline bubbles — 340-420K GPU-hours, enough to train a full 70B model. DualPipe recovered most of that. Directly quantifying the contribution is difficult without the internal logs, but the claim in the paper is over 95% GPU utilization averaged across training.
> For smaller runs (under 1k GPUs), DualPipe is overkill — pipeline bubbles are smaller relative to total cost, and dense-model training rarely hits the all-to-all bottleneck. For frontier MoE training at multi-thousand GPU scale, it is effectively required.

### Where it sits in the stack · 它在技术栈里的位置

- 与 **FSDP**（Phase 10 · 05）互补。FSDP 把模型参数分片到各 rank；DualPipe 调度各 rank 上的计算。两者可以组合。
- 兼容 **ZeRO-3** 梯度分片。两份拷贝的簿记需要与 ZeRO 的分片梯度协作。
- 需要针对具体集群拓扑调优的**自定义 all-to-all kernel**。DeepSeek 的开源 kernel 是参考实现。

```figure
expert-capacity
```

> - Complementary to **FSDP** (Phase 10 · 05). FSDP shards the model parameters across ranks; DualPipe schedules the compute across ranks. They combine.
> - Compatible with **ZeRO-3** gradient sharding. The bookkeeping for the two-copy replication needs to cooperate with ZeRO's sharded gradients.
> - Requires **custom all-to-all kernels** tuned for the specific cluster topology. DeepSeek's open-source kernels are the reference implementation.

## Use It · 实战用法

`code/main.py` 是一个流水线调度模拟器。它接收 `(P, n_micro_batches, schedule)`，打印 1F1B、Zero Bubble、DualPipe、DualPipeV 各自稳定阶段的利用率。它是一件教具——数字与各论文的定性结论一致，不构成对生产实测加速的断言。

模拟器的价值：换不同的 P 和微批数跑一跑，观察 1F1B 的气泡占比如何增长、而 DualPipe 不增长。

接入真实训练运行的注意事项：

- 选一个能整除你微批数的流水线并行深度。
- 确认你的专家并行网格支持双向 all-to-all。DeepSeek 的 kernel 是参考。
- 第一次要做好在调度本身上烧掉一周调试时间的心理准备。簿记很琐碎。
- 按 rank 监控 GPU 利用率，而不只看总量。DualPipe 的收益来自收紧最慢的那一环。

> `code/main.py` is a pipeline schedule simulator. It takes `(P, n_micro_batches, schedule)` and prints the stable-phase utilization for each of 1F1B, Zero Bubble, DualPipe, and DualPipeV. It is a teaching tool — the numbers match the qualitative claims in the papers, they are not a claim about production measured speedup.
> The simulator's value: run it with different P and micro-batch counts and watch how the bubble fraction grows for 1F1B but not DualPipe.
> Integration considerations for a real training run:
> - Pick a pipeline-parallel depth that divides cleanly into your micro-batch count.
> - Ensure your expert-parallel mesh supports bidirectional all-to-all. DeepSeek's kernels are the reference.
> - Expect to burn a week of debugging time on the schedule itself the first time. The bookkeeping is fiddly.
> - Monitor GPU utilization per rank, not just aggregate. DualPipe's benefit comes from tightening the stragglers.

## Ship It · 交付

本课产出 `outputs/skill-dualpipe-planner.md`。给定一份训练集群规格（GPU 数量、拓扑、互联、模型形状），它会推荐一条流水线并行策略、该用的调度算法，以及目标规模下的预期气泡占比。

> This lesson produces `outputs/skill-dualpipe-planner.md`. Given a training cluster specification (GPU count, topology, interconnect, model shape), it recommends a pipeline parallelism strategy, the scheduling algorithm to use, and the expected bubble fraction at the target scale.

## Exercises · 练习

1. 分别在 `(P=8, micro_batches=16, schedule=dualpipe)` 和 `(P=8, micro_batches=16, schedule=1f1b)` 上运行 `code/main.py`。算出 GPU 利用率差，并折算成每百万 token 训练能挽回的 GPU 小时。

2. 手工画出 `(P=4, micro_batches=8, schedule=dualpipe)` 的调度表。给每个时间槽标注微批 ID 和方向。找出第一个没有气泡的时间槽。

3. 阅读 DeepSeek-V3 技术报告（arXiv:2412.19437）的图 5。找出 DualPipe 前向 chunk 内 all-to-all 派发的重叠窗口。解释计算调度如何把它藏起来。

4. 计算 DualPipe 对一个 P=8 流水线阶段的 70B 稠密模型、以及一个 P=16 流水线阶段的 671B MoE 模型的 2 倍参数开销。说明为什么 MoE 情况的开销比例更小（大多数参数是专家，已分片到很大的 EP 组上）。

5. 把 DualPipe 与 Chimera（2021 年的一个竞争性双向调度器）比较。以论文 3.4 节为参照，指出 DualPipe 拥有而 Chimera 没有的两个具体性质。

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| Pipeline bubble | 「每个 rank 的空转时间」 | 流水线阶段因等待输入或梯度而浪费掉的 GPU 周期 |
| 1F1B | 「默认流水线调度」 | 一前向 / 一反向交错的调度；DualPipe 所击败的基线 |
| Zero Bubble | 「Sea AI Lab 2023」 | 把反向拆成 B（输入梯度）和 W（权重梯度）；让流水线几乎完全收紧 |
| DualPipe | 「DeepSeek-V3 调度」 | 双向流水线 + 计算-通信重叠；气泡不随微批数增长 |
| DualPipeV | 「Cut-in-half」 | V 形改进，砍掉 2 倍参数复制，代价是气泡略大 |
| Chunk | 「流水线工作单元」 | 一个微批穿过一个流水线阶段的一次前向或反向 |
| All-to-all dispatch | 「把 token 送给专家」 | 把 token 路由到其所属 MoE 专家的跨节点通信 |
| All-to-all combine | 「把专家输出带回来」 | MLP 之后汇集专家输出的跨节点通信 |
| Expert Parallelism (EP) | 「专家摊到各 GPU」 | 把 MoE 专家分片到各 rank，让不同 GPU 持有不同的专家 |
| Pipeline Parallelism (PP) | 「层摊到各 GPU」 | 把模型层分片到各 rank；DualPipe 所调度的维度 |
| Bubble fraction | 「浪费的 GPU 时间」 | (bubble_time / total_time)；DualPipe 把它推向零的那个比例 |

## Further Reading · 延伸阅读

- [DeepSeek-AI — DeepSeek-V3 Technical Report (arXiv:2412.19437), Section 3.3.2 and Figure 5](https://arxiv.org/abs/2412.19437) —— DualPipe 的一手参考
- [DeepSeek — DualPipe GitHub repository](https://github.com/deepseek-ai/DualPipe) —— 开源参考实现，含 DualPipeV（Cut-in-half）模式
- [Qi et al. — Zero Bubble Pipeline Parallelism (arXiv:2401.10241, Sea AI Lab 2023)](https://arxiv.org/abs/2401.10241) —— Zero Bubble 前身
- [Sea AI Lab — DualPipe could be better without the Dual](https://sail.sea.com/blog/articles/63) —— 促成 DeepSeek EP-off 模式的 DualPipeV 分析
- [Narayanan et al. — PipeDream / 1F1B (arXiv:1806.03377, 2018-2021)](https://arxiv.org/abs/1806.03377) —— DualPipe 用来对比的 1F1B 调度
- [Huang et al. — GPipe (arXiv:1811.06965, 2018)](https://arxiv.org/abs/1811.06965) —— 流水线并行开山之作与气泡问题的出处
