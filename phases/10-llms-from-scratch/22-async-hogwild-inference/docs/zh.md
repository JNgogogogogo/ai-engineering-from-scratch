# Async and Hogwild! Inference · 异步与 Hogwild! 推理

> 投机解码（speculative decoding，Phase 10 · 15）在一条序列内部并行 token。多智能体框架跨整条序列并行，却强迫你做显式协调（投票、子任务拆分）。Hogwild! Inference（Rodionov et al.，arXiv:2504.06261）走了另一条路：让同一个 LLM 的 N 个实例并行运行，共享同一个键值 cache（KV cache）。每个 worker 即时看到其他所有 worker 生成的 token。现代推理模型——QwQ、DeepSeek-R1——无需任何微调就能通过这个共享 cache 自行协调。这套方法是实验性的，但它开辟了一条与投机解码正交的全新推理并行轴。本课用标准库 Python 实现一个双 worker 的 Hogwild! 模拟器，并解释这种共享 cache 协作为什么能从模型既有的推理能力中涌现。
>
> Speculative decoding (Phase 10 · 15) parallelizes tokens within one sequence. Multi-agent frameworks parallelize across whole sequences but force explicit coordination (voting, sub-task splitting). Hogwild! Inference (Rodionov et al., arXiv:2504.06261) does something else: run N instances of the same LLM in parallel against a SHARED key-value cache. Each worker sees every other worker's generated tokens instantly. Modern reasoning models — QwQ, DeepSeek-R1 — can self-coordinate through that shared cache without any fine-tuning. The approach is experimental but it opens an entirely new axis of inference parallelism that sits orthogonal to spec decode. This lesson implements a two-worker Hogwild! simulator in stdlib Python and explains why the shared-cache collaboration emerges from the existing model's reasoning abilities.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 10 · 12 (inference optimization), Phase 10 · 15 (speculative decoding)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 描述三种常见的并行 LLM 拓扑（投票、子任务、Hogwild!），并说出各自针对的问题。
- 陈述 Hogwild! 的核心设置：多个 worker、一个共享 KV cache、通过自我提示（self-prompting）涌现的协调。
- 计算 Hogwild! 的墙钟时间加速比，表示为 worker 数 `N`、任务级并行度 `p` 和协调开销 `c` 的函数。
- 在一个玩具问题上实现双 worker 的 Hogwild! 模拟器，观察自发涌现的任务分工。

> Describe the three common parallel-LLM topologies (voting, sub-task, Hogwild!) and name which problems each one targets.
> State the core Hogwild! setup: multiple workers, one shared KV cache, emergent coordination via self-prompting.
> Compute the wall-time speedup of Hogwild! as a function of worker count `N`, task-level parallelism `p`, and coordination overhead `c`.
> Implement a two-worker Hogwild! simulator on a toy problem and observe the emergent task division.

## The Problem · 问题在哪

现代 LLM 靠生成长串推理来解难题——5000 token 的逐步逻辑很常见，深层数学题上几万 token 也会出现。70B 模型按 35 token/秒解码，50k token 就是 24 分钟。完全谈不上交互。

投机解码（Phase 10 · 15）通过在一条序列内部并行，给你 3-5 倍加速。再往上，自回归解码的串行依赖就是硬天花板：每个新 token 依赖之前的每一个 token。

显而易见的问题：能不能跨序列并行？让同一个模型的多份副本跑同一道题，让它们合作、分工？

已有工作：投票集成（跑 N 个模型，取多数答案）、思维树（branch 出推理路径再合并）、多智能体框架（给每个 agent 分派子任务，配一个协调者）。它们在特定任务域都有帮助，但也都引入了显式的协调机器——投票规则、分支剪枝逻辑、agent 间消息协议。

Hogwild! Inference 换了个思路。N 个 worker 共享一个 KV cache。每个 worker 立刻看到其他 worker 生成的 token，就好像它们出现在自己的上下文里。这些 worker——不经任何训练或微调——自己琢磨出怎么分工。现代推理模型（QwQ、DeepSeek-R1、Claude 家族的推理模式）能读共享 cache 并说出「我看到 worker 2 已经处理了基础情形，那我来做归纳步骤」这种话。

加速比取决于工作负载，而且截至 2026 年 4 月仍是实验性的。但这个想法值得了解，因为它开辟了推理并行的一条新轴。

> Modern LLMs solve hard problems by producing long chains of reasoning — 5000 tokens of step-by-step logic is common, tens of thousands of tokens happens on deep math problems. ... Speculative decoding (Phase 10 · 15) gets you a 3-5x speedup by parallelizing within one sequence. Past that the sequential dependency of autoregressive decoding is the hard ceiling. Each new token depends on every prior token. ... Hogwild! Inference takes a different approach. N workers share a single KV cache. Each worker sees every other worker's generated tokens immediately, as if they were its own context. The workers — without any training or fine-tuning — figure out how to divide the work. ... The speedup is workload-dependent and experimental as of April 2026. But the idea is worth knowing because it opens a new axis of inference parallelism.

## The Concept · 概念

### The setup · 基本设置

初始化 N 个 worker 进程，全部运行同一个 LLM。不用每 worker 一个 KV cache，而是维护唯一一个共享 cache。当 worker `i` 生成 token `t_j` 时，这个 token 被写进共享 cache 的下一个位置。当 worker `k` 迈出下一步时，它读取 cache 的当前状态（其中包含全部 N 个 worker 迄今生成的一切）。

步进时，worker 们竞争写入 token。没有每 worker 的位置索引——cache 是一条不断增长的单序列。顺序由写入的到达时间决定。

> Initialize N worker processes, all running the same LLM. Instead of per-worker KV caches, maintain ONE shared cache. When worker `i` generates token `t_j`, the token is written into the shared cache at the next position. When worker `k` takes its next step, it reads the current state of the cache (which includes everything all N workers have generated so far). ... At step time, workers race to write tokens. There is no per-worker position index — the cache is a single growing sequence. Order is determined by write arrival time.

### Why coordination emerges · 协调为何自发涌现

worker 们共享同一个提示词。典型内容是「你是共同解这道题的 N 个实例之一。每个实例读取共享内存，能看到其他实例写了什么。避免重复劳动。」提示词加上共享 cache 就够了。推理模型读 cache，注意到问题的哪些部分已经有人尝试过，然后（常常但不总是）转向尚未探索的部分。

Hogwild! 论文（Rodionov et al., 2025）报告了这样的观察：

- worker 们制定计划，并通过 cache 把计划传达给其他 worker。
- worker 们发现其他 worker 推理中的错误，并且指出来。
- 计划失败时 worker 们会调整，并提出替代方案。
- 被提示检查冗余时，worker 们能检测到冗余并转向。

这一切都不需要微调。涌现行为来自模型已经具备的推理能力。

> The workers share a prompt. Typically something like "You are one of N instances working together on this problem. Each instance reads the shared memory and can see what other instances have written. Avoid redundant work." The prompt plus the shared cache is enough. ... The Hogwild! paper (Rodionov et al., 2025) reports observations like: ... None of this requires fine-tuning. The emergent behavior comes from the reasoning capabilities the model already has.

### The naming · 名字的由来

论文的名字戏仿了 Hogwild! SGD（Recht et al., 2011），一个异步更新优化器。类比是：SGD 的异步 worker 都往一个共享参数向量里写；Hogwild! Inference 的 worker 都往一个共享 KV cache 里写。两者都依赖经验上的收敛，而不是同步保证。

> The paper's name riffs on Hogwild! SGD (Recht et al., 2011), an asynchronous-update optimizer. The analogy: SGD's asynchronous workers all write to a shared parameter vector; Hogwild! Inference's workers all write to a shared KV cache. Both rely on empirical convergence rather than synchronization guarantees.

### RoPE makes this tractable · RoPE 让这一切可行

旋转位置编码（Rotary Position Embeddings，RoPE，Su et al. 2021）通过 Q、K 向量中的旋转来编码位置信息。因为位置是旋转而不是硬编码的偏移，一个 token 的位置可以平移而不必重算 KV cache 条目。当 worker `i` 把内容写进共享 cache 的位置 `p` 时，其他 worker 读这个位置可以直接用缓存的条目——不需要重新旋转。

在可学习位置或绝对位置的模型里，Hogwild! 每次并发写入都得让 cache 失效。RoPE 让 cache 保持稳定。

> Rotary Position Embeddings (RoPE, Su et al. 2021) encode position information via rotation in the Q and K vectors. Because positions are rotations and not baked-in offsets, a token's position can shift without recomputing the KV cache entry. ... In a learned-position or absolute-position model, Hogwild! would need cache invalidation on every concurrent write. RoPE lets the cache stay stable.

### Wall-time math · 墙钟时间的账

设 `T_serial` 是一个 worker 独自解题所需的时间。设 `p` 是任务级可并行的比例。设 `c` 是每步协调开销（读扩展后的 cache、决定要写什么）。

单 worker 时间：`T_serial`。
协调免费时，N-worker Hogwild! 时间：`T_serial * ((1 - p) + p / N)`。经典的 Amdahl 定律。
算上协调开销：`T_serial * ((1 - p) + p / N) + c * steps_per_worker`。

worker 要有产出，`c` 必须相对每步解码时间足够小。对产出 5k+ token 的推理模型，worker 们负担得起几百 token 的协调开销还能占便宜。对短聊天任务，协调开销占主导，Hogwild! 不如串行。

> Let `T_serial` be the time for one worker to solve the problem alone. Let `p` be the task-level parallelizable fraction. Let `c` be the per-step coordination overhead (reading the extended cache, deciding what to write). ... For a worker to be productive, `c` must be small relative to the per-step decode time. On reasoning models producing 5k+ tokens, the workers can afford hundreds of tokens of coordination overhead and still come out ahead. On short chat tasks, coordination dominates and Hogwild! is worse than serial.

### Concrete example · 具体例子

推理问题：10k token 的思维链。假设问题有 `p = 0.7` 的可并行内容（不同的证明策略、不同的情形分析），每个 worker 的协调开销 `c = 200` token。取 `N = 4` 个 worker：

- 串行时间：10000 个解码步。
- Hogwild! 时间：10000 * (0.3 + 0.7 / 4) + 200 * 4 = 10000 * 0.475 + 800 = 5550 个解码步。
- 加速比：10000 / 5550 = 1.8x。

这不算多。但在更长的推理题（50k token）上，协调开销被摊薄，加速比推向 2.5-3x。Hogwild! 之于推理，就像在一种能自然写多线程代码的语言里做线程级并行。

> Reasoning problem: 10k tokens of chain-of-thought. Suppose the problem has `p = 0.7` parallelizable content (different proof strategies, different case analyses) and `c = 200` tokens of coordination overhead per worker. With `N = 4` workers: ... Speedup: 10000 / 5550 = 1.8x. ... That is modest. But on longer reasoning problems (50k tokens), the coordination overhead amortizes and the speedup pushes 2.5-3x. Hogwild! is the inference equivalent of thread-level parallelism in a language that lets you write multi-threaded code naturally.

### When to reach for Hogwild! · 什么时候用 Hogwild!

- 长推理题（几千 token 起），且任务能沿独立子目标并行。
- 经过训练、会逐步思考的推理模型。非推理模型的自协调能力不行。
- 单机部署，显存足以装下共享 cache 加 N 个 worker 进程。cache 是共享的，但每个 worker 有自己的激活内存。

### When not to · 什么时候不要用

- 短平快的交互聊天。协调开销占主导。
- 不可并行的任务（单条线性证明、单次编译）。N=1 就是上限。
- 非推理模型。涌现不出协调。
- 多机部署。共享 cache 需要极快的跨 worker 同步。节点内没问题；跨节点是延迟灾难。

> When to reach for Hogwild!: ... Long reasoning problems (thousands of tokens) where the task can be parallelized across independent sub-goals. ... Reasoning models that have been trained to think step by step. Non-reasoning models do not self-coordinate well. ... Single-node deployments with enough VRAM to hold the shared cache plus N worker processes. ... When not to: ... Short interactive chat. Coordination overhead dominates. ... Tasks that don't parallelize (single linear proof, single compilation). N=1 is the max. ... Non-reasoning models. No coordination emerges. ... Multi-node deployments. The shared cache needs very fast cross-worker synchronization. Intra-node is fine; cross-node is a latency disaster.

### The experimental status · 实验性状态

截至 2026 年 4 月，Hogwild! 是一个带开源 PyTorch 实现的研究方法。生产采用尚未发生。三个障碍：

1. 跨并发进程管理共享 KV cache 是不小的工程。
2. 涌现协调依赖具体任务；基准测试仍在搭建中。
3. 相比投机解码已经交出的加速，这些加速并不惊人；两者可以叠加，但叠加本身又是一层工程。

值得了解。值得实验。还不值得押上一个产品。

> As of April 2026, Hogwild! is a research method with an open-source PyTorch implementation. Production adoption has not happened. Three blockers: ... Shared KV cache management across concurrent processes is non-trivial engineering. ... Emergent coordination is task-dependent; benchmarks are still being built. ... The speedups are modest compared to what speculative decoding already delivers, and the two can be combined but the combined engineering is another layer. ... Worth knowing. Worth experimenting with. Not yet worth betting a product on.

```figure
continuous-batching
```

## Build It · 动手造

`code/main.py` 实现一个玩具级 Hogwild! 模拟器：

- 两个 worker 进程，各是一个确定性的「LLM」，按已知概率产出几种 token 类别之一（工作 token、观察 token、协调 token）。
- 一个共享 cache（就是 token 列表），两个 worker 都读写。
- 一条简单的协调逻辑：当 worker 看到对方在某个类别已经产出足够多工作 token，它就换一个类别。

模拟器按固定步数预算运行，并报告：

- 产出的工作 token 总数。
- 总墙钟时间（worker 步数）。
- 相对单 worker 的有效加速比。
- 哪个 worker 写了哪个 token 的轨迹。

> `code/main.py` implements a toy Hogwild! simulator: ... A shared cache (just a list of tokens) that both workers read and write. ... The simulator runs for a fixed step budget and reports: ... A trace of which worker wrote which token.

### Step 1: the shared cache · 第 1 步：共享 cache

一个两个 worker 都往里追加的列表。真实实现中用简单的锁（Python `threading.Lock`）；我们用一个计数器来模拟。

> A list that both workers append to. Simple locking (Python `threading.Lock`) in a real implementation; we simulate with a counter.

### Step 2: the worker loop · 第 2 步：worker 循环

每个 worker 每一步：

- 读取当前共享 cache。
- 根据 cache 里已有的内容，决定要写哪个类别的 token。
- 写入一个 token。

> Each worker, on each step: ... Reads the current shared cache. ... Decides what category of token to write based on what is already there. ... Writes one token.

### Step 3: the coordination heuristic · 第 3 步：协调启发式

如果类别 X 在 cache 里已经有 K 个 token，而 worker 打算写的也是 X，worker 就切换到类别 Y。这是「发现这块已被覆盖，那就干点别的」这一推理模型行为的玩具替身。

> If category X already has K tokens in the cache and worker's intended category is X, worker switches to category Y. This is a toy stand-in for the reasoning-model behavior of "notice this is already covered, do something else instead."

### Step 4: measured speedup · 第 4 步：实测加速比

分别以 N=1 和 N=2 个 worker、同样的总步数预算运行模拟器。统计产出的工作 token。N=2 应该产出大约 1.5-1.8 倍的工作 token，因为协调驱动了任务分工。

> Run the simulator with N=1 worker and with N=2 workers, same total step budget. Count work-tokens produced. N=2 should produce roughly 1.5-1.8x more work-tokens because of the coordination-driven task division.

### Step 5: stress the coordination · 第 5 步：压测协调机制

调低协调启发式的敏感度，再跑一次。观察到：没有好的协调，N=2 会冗余地产出同样的 token，加速比跌破 1。这与论文的观察吻合：只有 worker 具备自协调所需的推理能力，这一招才有效。

> Reduce the coordination heuristic's sensitivity. Run again. Observe that without good coordination, N=2 redundantly produces the same tokens and the speedup drops below 1. This matches the paper's observation: the trick only works if the workers have the reasoning capacity to self-coordinate.

## Use It · 实战用法

截至 2026 年 4 月，Hogwild! 的生产集成仍是研究级。Yandex/HSE/IST 的参考实现基于 PyTorch，面向 DeepSeek-R1 和 QwQ 模型的单机多进程设置。

务实的采用路径：

1. 剖析你的推理任务工作负载。测量探索性 token（多策略、情形分析、搜索）相对线性 token 的比例。
2. 如果探索占主导，跑一个双 worker 的 Hogwild! 实验。测量墙钟时间的改善。
3. 如果改善不到 1.3 倍，你处在协调开销主导区。退回单 worker。
4. 如果改善超过 1.5 倍，推到 N=4 再测。收益递减通常出现在 N=4-8 附近。

与投机解码结合：每个 Hogwild! worker 都可以独立使用投机解码。两个加速比（大致）相乘——3x 的投机解码乘 1.8x 的 Hogwild!，对朴素单 worker 解码得到约 5.4x 的有效加速。

> Hogwild! integration in production as of April 2026 is research-grade. The reference implementation from Yandex/HSE/IST is PyTorch-based and targets single-node multi-process setups on DeepSeek-R1 and QwQ models. ... If the improvement is under 1.3x, you are in the coordination-dominated regime. Revert to single-worker. ... If the improvement is over 1.5x, push to N=4 and measure again. Diminishing returns typically hit around N=4-8. ... Combine with speculative decoding: each Hogwild! worker can independently use spec decode. The two speedups multiply (roughly), bringing a 3x spec decode and 1.8x Hogwild! to an effective 5.4x over naive single-worker decoding.

## Ship It · 交付

本课产出 `outputs/skill-parallel-inference-router.md`。给定一份推理工作负载画像（token 预算、任务并行度画像、模型家族、部署目标），它在投票、思维树、多智能体、Hogwild! 和投机解码这些策略之间做路由。

> This lesson produces `outputs/skill-parallel-inference-router.md`. Given a reasoning workload profile (token budget, task parallelism profile, model family, deployment target), it routes between voting, tree-of-thought, multi-agent, Hogwild!, and speculative decoding strategies.

## Exercises · 练习

1. 用默认设置运行 `code/main.py`。确认 N=2 的 Hogwild! 配置在相同墙钟时间内比 N=1 基线产出更多工作 token。

2. 调低协调启发式的强度（设 `coordination_weight=0.1`）。重跑。展示加速比崩塌，并解释原因：worker 们无法协调时就会重复劳动。

3. 计算一个 50k token 推理任务在 `p=0.8, c=500`、N=4 时的期望 Hogwild! 加速比。再算一个 1k token 聊天任务在 `p=0.3, c=200`、N=4 时的情况。为什么一个是赚、一个是亏？

4. 阅读 Hogwild! 论文第 4 节（初步评估）。找出作者报告的两种失败模式。描述一个更好的协调提示词如何缓解每一种。

5. 在玩具模拟器里把 Hogwild! 与投机解码结合：每个 worker 内部使用 2-token 的投机解码。报告乘法加速比。当两个 worker 都想扩展同一条共享 cache 前缀时，会出现什么记账难题？

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| Hogwild! | 「并行 worker，共享 cache」 | 同一个 LLM 的 N 个实例并发运行、共用一个 KV cache；通过自我提示涌现协调 |
| Shared KV cache | 「协调媒介」 | 一条所有 worker 都读写的、不断增长的 KV 缓冲；让 token 在 worker 之间即时可见 |
| Emergent coordination | 「不用训练」 | 具备推理能力的 LLM 能读共享 cache 并分工，无需任何微调或显式协议 |
| Coordination overhead (c) | 「花在定位上的 token」 | 每 worker 读扩展 cache 并决定行动的成本；相对总解码时间必须保持很小 |
| Parallelizable fraction (p) | 「能并行的部分」 | 任务级并行度：总工作中非天然串行的比例 |
| RoPE enables Hogwild! | 「旋转位置是平移不变的」 | 因为位置是旋转，写入共享 cache 不需要重算先前的 token |
| Voting ensemble | 「跑 N 个取多数」 | 最简单的并行推理拓扑；对分类有用，对长篇推理用处不大 |
| Tree of thought | 「分支再剪枝」 | 探索多条分支并剪枝的推理策略；显式的协调逻辑 |
| Multi-agent framework | 「分派子任务」 | 每个 agent 领一个角色，由协调者编排；协议开销沉重 |

## Further Reading · 延伸阅读

- [Rodionov et al. — Hogwild! Inference: Parallel LLM Generation via Concurrent Attention (arXiv:2504.06261)](https://arxiv.org/abs/2504.06261) —— Hogwild! 论文，在 QwQ 和 DeepSeek-R1 上的初步评估
- [Recht, Re, Wright, Niu — Hogwild!: A Lock-Free Approach to Parallelizing Stochastic Gradient Descent (arXiv:1106.5730, NeurIPS 2011)](https://arxiv.org/abs/1106.5730) —— 原始 Hogwild!，名字的出处
- [Su et al. — RoFormer: Enhanced Transformer with Rotary Position Embedding (arXiv:2104.09864)](https://arxiv.org/abs/2104.09864) —— RoPE，让共享 cache 推理变得可行的性质
- [Yao et al. — Tree of Thoughts: Deliberate Problem Solving with Large Language Models (arXiv:2305.10601)](https://arxiv.org/abs/2305.10601) —— 与 Hogwild! 正交的思维树推理策略
- [Leviathan et al. — Fast Inference from Transformers via Speculative Decoding (arXiv:2211.17192)](https://arxiv.org/abs/2211.17192) —— 投机解码，Hogwild! 可与之叠加的序列内并行
- [Hogwild! reference PyTorch implementation](https://github.com/eqimp/hogwild_llm) —— 论文实验的唯一权威实现
