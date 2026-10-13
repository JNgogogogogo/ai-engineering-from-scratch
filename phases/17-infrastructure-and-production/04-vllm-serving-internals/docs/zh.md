# Serving Engine Internals — PagedAttention, Continuous Batching, Chunked Prefill · Serving 引擎内部机制 —— PagedAttention、Continuous Batching、Chunked Prefill

> 现代 serving 引擎的吞吐建立在三个层层叠加的默认项上，而不是某个单点技巧。PagedAttention 永远开着。Continuous batching 在 decode 迭代之间把新请求注入活跃 batch。Chunked prefill 把长提示词切片，让 decode token 永不挨饿。三个全开，一块 H100 SXM5 上的 Llama 3.3 70B FP8 在 128 并发下能推到 2,200-2,400 tok/s——大约比 vLLM 自己的默认值高 25%，是朴素 PyTorch 循环的 3-4 倍。本课带你读懂 vLLM——这三种技术的参考引擎——的调度器和 attention kernel，读到你能画出图的程度，最后在 `code/main.py` 里按 vLLM 调度 prefill 和 decode 的方式写一个玩具 continuous batcher。

> Modern serving-engine throughput rests on three compounding defaults, not a single trick. PagedAttention is always on. Continuous batching injects new requests into the active batch between decode iterations. Chunked prefill slices long prompts so decode tokens never starve. Turn all three on and a Llama 3.3 70B FP8 on one H100 SXM5 pushes 2,200-2,400 tok/s at 128 concurrent — roughly 25% above vLLM's own default and 3-4x a naive PyTorch loop. This lesson reads the scheduler and attention kernel of vLLM — the reference engine for all three techniques — at a level you can diagram, and ends with a toy continuous batcher in `code/main.py` that schedules prefill and decode the way vLLM does.

**Type:** Learn
**Languages:** Python (stdlib, toy continuous batching scheduler)
**Prerequisites:** Phase 17 · 01 (Model Serving), Phase 11 (LLM Engineering)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 把 PagedAttention 当作 KV cache 分配器来解释：block、block table，以及为什么生产负载下碎片率保持在 4% 以下。
- 在迭代级别画出 continuous batching：完成的序列如何离开 batch、新序列如何不排空 batch 就加入。
- 用一句话描述 chunked prefill，并说出它保护的是哪个延迟指标（提示：是 TTFT 尾部，不是平均吞吐）。
- 在一口气打开所有优化之前，对照你手上版本的兼容性矩阵检查 vLLM 特性组合。

> Explain PagedAttention as a KV cache allocator: blocks, block tables, and why fragmentation stays under 4% at production load.
> Diagram continuous batching at the iteration level: how finished sequences leave the batch and new ones join without draining.
> Describe chunked prefill in one sentence and name which latency metric it protects (hint: it is TTFT tail, not mean throughput).
> Check a vLLM feature combination against the compatibility matrix for your version before enabling every optimization at once.

## The Problem · 问题在哪

朴素的 PyTorch serve 循环一次跑一个请求：tokenize、prefill、decode 到 EOS、返回。一个用户没问题。一百个用户，就变成一队有耐心的人排长队。显而易见的修法——静态 batching——把每个请求 pad 到窗口里最长的提示词，把每次 decode pad 到最长的预期输出，然后整个 batch 卡在最慢的序列上。你为永远用不到的 padding 买单，快请求等慢请求。

vLLM 一次解决三个问题。PagedAttention 不让 KV cache 碎片像经典连续分配那样吃掉 60-80% 的 GPU 内存。Continuous batching 让请求在每次 decode 迭代之间进出 batch，batch 里永远装着真实的活。Chunked prefill 把 32k token 的提示词拆成约 512 token 的切片，与 decode 交错执行，长提示词就不会冻住 GPU 上每一个 decode token。

2026 年的生产默认是三个全开。你必须理解每个在做什么，因为失败模式全在调度器上，不在模型上。

> A naive PyTorch serve loop runs one request at a time: tokenize, prefill, decode until EOS, return. At one user this works. At one hundred, it is a queue of patient people. The obvious fix — static batching — pads every request to the longest prompt in the window, pads every decode to the longest expected output, and stalls the whole batch on the slowest sequence. You pay for padding you never use, and fast requests wait for slow ones.
> vLLM solves three problems at once. PagedAttention stops KV cache fragmentation from eating 60-80% of GPU memory the way classic contiguous allocation does. Continuous batching lets requests join and leave the batch between each decode iteration, so the batch is always full of real work. Chunked prefill breaks a 32k-token prompt into ~512-token slices that interleave with decode, so a long prompt does not freeze every decode token on the GPU.
> The 2026 production default is all three on. You need to understand what each one does because the failure modes are all on the scheduler, not the model.

## The Concept · 概念

### PagedAttention as a virtual memory system · PagedAttention —— 一套虚拟内存系统

每个序列的 KV cache 是 `num_layers × 2 × num_heads × head_dim × seq_len × bytes_per_element`。对 Llama 3.3 70B 在 8192 token 下，BF16 大约是每序列 1.25 GB。如果你为每个请求预留 8192 个槽位，而平均请求只用 1500 token，你浪费了约 82% 预留的 HBM。经典 batching 付的就是这个浪费。

PagedAttention 从操作系统虚拟内存借来这个想法。KV cache 不再按序列连续存放。它按固定大小的 block（默认 16 token）分配。每个序列有一张 block table，把逻辑 token 位置映射到物理 block ID。序列长过已分配的 block 时，就再加一个 block。序列结束时，它的 block 归还池子。

碎片率从 60-80%（经典）降到 4% 以下（PagedAttention）。PagedAttention 不是用开关打开的——它是 vLLM 唯一自带的分配器。旋钮是 `--gpu-memory-utilization`（默认 0.9），它告诉 vLLM 在加载权重和激活之后，留多少 HBM 给 KV block。

> A KV cache is `num_layers × 2 × num_heads × head_dim × seq_len × bytes_per_element` per sequence. For Llama 3.3 70B at 8192 tokens, that is roughly 1.25 GB per sequence in BF16. If you pre-reserve 8192 slots for every request but the average request only uses 1500 tokens, you waste roughly 82% of the HBM you reserved. Classic batching pays this waste.
> PagedAttention borrows the idea from OS virtual memory. KV cache is not contiguous per sequence. It is allocated in fixed-size blocks (default 16 tokens). Each sequence has a block table that maps its logical token positions to physical block IDs. When a sequence grows past its allocated blocks, one more block is added. When it finishes, its blocks return to the pool.
> Fragmentation drops from 60-80% (classic) to under 4% (PagedAttention). You do not enable PagedAttention with a flag — it is the only allocator vLLM ships. The knob is `--gpu-memory-utilization` (default 0.9), which tells vLLM how much HBM to reserve for KV blocks after loading weights and activations.

### Continuous batching at the iteration level · 迭代级的 continuous batching

老的「dynamic batching」等一个窗口（比如 10 ms）攒满一个 batch，然后跑 prefill + decode + decode + decode 直到每个序列结束。快的序列早早离场，闲着等 GPU 磨完慢的。

Continuous batching 在每个 decode 步之间运作。把正在运行的序列集合叫 `RUNNING` 列表。每次迭代：

1. `RUNNING` 里刚碰到 EOS 或 max_tokens 的序列被移除。
2. 调度器查看等待队列。如果有空闲 KV block，就接纳新序列（prefill 或续跑）。
3. 前向跑在当前 `RUNNING` 上，每个序列产出一个新 token。

batch 大小永远不会 pad 到固定数。处在输出不同位置的序列共享一次融合前向。2026 年的 vLLM 里它叫 `V1 scheduler`。关键不变量：调度器每次 decode 迭代跑一次，而不是每个请求跑一次。

> The old "dynamic batching" waited for a window (say 10 ms) to fill a batch, then ran prefill + decode + decode + decode until every sequence finished. Fast sequences left early and sat idle while the GPU finished the slow ones.
> Continuous batching operates between each decode step. Call the set of running sequences the `RUNNING` list. At each iteration:
> 1. Any sequence in `RUNNING` that just hit EOS or max_tokens is removed.
> 2. The scheduler looks at the waiting queue. If there are free KV blocks, it admits new sequences (prefill or resumed).
> 3. The forward pass runs on whatever is now in `RUNNING`, emitting one new token per sequence.
> The batch size is never padded to a fixed number. Sequences at different positions in their output share one fused forward. In 2026 vLLM this is called the `V1 scheduler`. The key invariant: the scheduler runs once per decode iteration, not once per request.

### Chunked prefill protects TTFT tail · Chunked prefill 保护 TTFT 尾部

Prefill 是计算受限的。32k token 的提示词在 Llama 3.3 70B 上，一块 H100 要约 800 ms 的纯 prefill。prefill 期间，batch 里其他所有序列的 decode token 都在等。在 serve 循环里，一个长提示词的首 token 延迟（TTFT）会变成几十个其他用户的 token 间延迟（ITL）毛刺。

Chunked prefill 把 prefill 切成固定大小的块（默认 512 token），每块作为一个调度单元。块与块之间，调度器可以让 decode 序列前进一个 token。你用一点点绝对 prefill 延迟损失（每块几毫秒）换来大幅降低的 decode 抖动。公开基准里，混合负载下的 P99 ITL 从约 50 ms 降到约 15 ms。

> Prefill is compute-bound. A 32k-token prompt on Llama 3.3 70B takes ~800 ms of pure prefill on one H100. While prefill runs, decode tokens for every other sequence in the batch wait. In a serving loop, the first-token latency (TTFT) of one long prompt becomes the inter-token latency (ITL) blip for dozens of other users.
> Chunked prefill splits prefill into fixed-size chunks (default 512 tokens) and schedules each chunk as a unit. Between chunks the scheduler can advance decode sequences by one token. You trade a small absolute prefill latency hit (a few ms per chunk) for much lower decode-time jitter. P99 ITL under mixed load drops from ~50 ms to ~15 ms in published benchmarks.

### The three defaults interact · 三个默认项互相咬合

三个特性互为前提。PagedAttention 给调度器一个可细粒度交易的 KV 资源。Continuous batching 需要这种细粒度资源，这样接纳新序列才不会逼出一次全局重排。Chunked prefill 是调度器在同一个 `RUNNING` 列表上做的决定——它是又一条调度策略，不是独立系统。

你不需要记住每个 flag。你需要知道调度器在优化什么：KV block 预算约束下、附带 chunked prefill 切片的 goodput。

> All three features assume each other. PagedAttention gives the scheduler a fine-grained KV resource to trade against. Continuous batching needs that fine-grained resource so admitting a new sequence does not force a global reshuffle. Chunked prefill is a decision the scheduler makes on the same `RUNNING` list — it is one more scheduler policy, not a separate system.
> You do not need to know every flag. You need to know what the scheduler optimizes: goodput under KV-block budget, subject to chunked prefill slicing.

### Check the compatibility matrix · 查一查兼容性矩阵

在一次性启用全部特性之前，对照你手上 vLLM 版本的兼容性矩阵检查每一个特性组合，因为能组合什么在版本之间会变。在 v0.18.0 中，特性矩阵标注 speculative decoding 与 chunked prefill、prefix caching 兼容，speculative-decoding 页面列出两个已知不兼容：pipeline parallelism（到 v0.15.0 为止）和 draft-model speculation（到 v0.10.0 为止）。至于 draft 方法本身，2026 年的默认通常是 EAGLE-3（`"method": "eagle3"`），见 Phase 17 · 05。

> Check every feature combination against the compatibility matrix for your exact vLLM version before enabling all of them at once, because what composes changes between releases. In v0.18.0 the feature matrix marks speculative decoding as compatible with chunked prefill and prefix caching, and the speculative-decoding page lists two known incompatibilities: pipeline parallelism through v0.15.0, and draft-model speculation through v0.10.0. For the draft method itself, the 2026 default is often EAGLE-3 (`"method": "eagle3"`), covered in Phase 17 · 05.

### Numbers you should remember · 你该记住的数字

- Llama 3.3 70B FP8、H100 SXM5、128 并发、三个全开：2,200-2,400 tok/s。
- 同模型，vLLM 默认（无 chunked prefill）：约 1,800 tok/s。
- 同模型，朴素 PyTorch 前向循环：约 600 tok/s。
- PagedAttention 在生产负载下的 KV 碎片浪费：<4%。
- 混合负载下的 P99 ITL：有 chunked prefill 约 15 ms，没有约 50 ms。

> - Llama 3.3 70B FP8, H100 SXM5, 128 concurrent, all three on: 2,200-2,400 tok/s.
> - Same model, default vLLM (no chunked prefill): ~1,800 tok/s.
> - Same model, naive PyTorch forward loop: ~600 tok/s.
> - KV fragmentation waste under PagedAttention at production load: <4%.
> - P99 ITL under mixed load: ~15 ms with chunked prefill, ~50 ms without.

### What the scheduler looks like · 调度器长什么样

```
while True:
    finished = [s for s in RUNNING if s.is_done()]
    for s in finished: release_blocks(s); RUNNING.remove(s)

    while WAITING and have_free_blocks_for(WAITING[0]):
        s = WAITING.pop(0)
        allocate_initial_blocks(s)
        RUNNING.append(s)

    # schedule prefill chunks + decode in one batch
    batch = []
    for s in RUNNING:
        if s.in_prefill:
            batch.append(next_prefill_chunk(s))   # e.g. 512 tokens
        else:
            batch.append(decode_one_token(s))     # 1 token

    run_forward(batch)                            # one fused GPU call
```

`code/main.py` 就是这个循环的 stdlib Python 版本，用假的 token 数和假的前向延迟。跑它会看到 chunked prefill 如何在长 prefill 期间让 decode 序列保活。

> `code/main.py` is exactly this loop in stdlib Python with fake token counts and fake forward latency. Running it shows how chunked prefill keeps decode sequences alive during a long prefill.

```figure
tensor-parallel
```

## Use It · 实战用法

`code/main.py` 模拟一个特性可开关的 vLLM 风格调度器。跑它看：

- `NAIVE` 模式：一次一个请求，无 batching。
- `STATIC` 模式：pad 加等待，经典 batching。
- `CONTINUOUS` 模式：迭代级接纳与释放。
- `CONTINUOUS + CHUNKED` 模式：prefill 切片与 decode 交错。

输出展示总吞吐（每虚拟秒 token 数）、TTFT 均值和 P99 ITL。混合流量下 `CONTINUOUS + CHUNKED` 那一行应该全面领先。

> `code/main.py` simulates a vLLM-style scheduler with toggleable features. Run it to see:
> - `NAIVE` mode: one request at a time, no batching.
> - `STATIC` mode: pad and wait, classic batching.
> - `CONTINUOUS` mode: iteration-level admission and release.
> - `CONTINUOUS + CHUNKED` mode: prefill slices interleaved with decode.
> The output shows total throughput (tokens per virtual second), TTFT mean, and P99 ITL. The `CONTINUOUS + CHUNKED` row should dominate on mixed traffic.

## Ship It · 交付

本课产出 `outputs/skill-vllm-scheduler-reader.md`。给定一个 serving 配置（batch 大小、KV 内存利用率、chunked prefill 大小、speculative 配置），它产出一份调度器诊断，指出三个默认项里哪个在卡脖子、该调什么。

> This lesson produces `outputs/skill-vllm-scheduler-reader.md`. Given a serving config (batch size, KV memory utilization, chunked prefill size, speculative config), it produces a scheduler diagnosis that names which of the three defaults is bottlenecking and what to tune.

## Exercises · 练习

1. 运行 `code/main.py`。在一个长短请求混合的负载上对比 `STATIC` 和 `CONTINUOUS`。吞吐差距来自哪——prefill 效率、decode 效率，还是尾延迟？
2. 给玩具调度器加上 `--max-num-batched-tokens`。对一块跑 Llama 3.3 70B FP8 的 H100，合适的值是多少？（提示：它是 KV block 大小和空闲 block 数的函数，不是裸 HBM 的函数。）
3. 重读 vLLM v0.18.0 的 release notes。哪些 flag 组合互斥？列出来。
4. 对一份 1,000 个请求、输出均值 1,500 token、标准差 600 token 的 trace，计算 KV cache 碎片浪费：(a) 按 8192 上限做每请求连续分配，(b) 16-token block 的 PagedAttention。
5. 用一段话解释为什么 chunked prefill 单独使用能改善 P99 ITL 却不改善吞吐。实践中的吞吐收益从哪来？

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| PagedAttention | "KV cache 的那一招" | KV cache 的定长 block 分配器；碎片率 <4% |
| Block table | "页表" | 每序列从逻辑 token 位置到物理 KV block 的映射 |
| Continuous batching | "做对了的 dynamic batching" | 每次 decode 迭代都做接纳/释放决策 |
| Chunked prefill | "prefill 切片" | 把长 prefill 拆成 512-token 切片与 decode 交错 |
| TTFT | "首 token 时间" | prefill + 排队 + 网络；长提示词下由 prefill 主导 |
| ITL | "token 间延迟" | 相邻 decode token 之间的时间；由 batch 大小主导 |
| Goodput | "满足 SLO 的吞吐" | 每个请求都达到 TTFT 和 ITL 目标的 tokens/sec |
| V1 scheduler | "新调度器" | vLLM 的 2026 调度器；以 chunked prefill 跑 continuous batching |
| `--gpu-memory-utilization` | "内存旋钮" | 权重和激活之外预留给 KV block 的 HBM 比例 |

## Further Reading · 延伸阅读

- [vLLM documentation — Speculative Decoding](https://docs.vllm.ai/en/latest/features/spec_decode/) —— 关于 chunked prefill 与 speculative decoding 兼容性的官方来源。
- [vLLM Release Notes (NVIDIA)](https://docs.nvidia.com/deeplearning/frameworks/vllm-release-notes/index.html) —— 2026 年的发布节奏与特定版本行为。
- [vLLM Blog — PagedAttention](https://blog.vllm.ai/2023/06/20/vllm.html) —— 最初的那篇文章，至今仍定义着该如何思考这个分配器。
- [PagedAttention paper (arXiv:2309.06180)](https://arxiv.org/abs/2309.06180) —— 碎片分析与调度器设计。
- [Aleksa Gordic — Inside vLLM](https://www.aleksagordic.com/blog/vllm) —— 带 flame graph 的详细 V1 调度器走读。
