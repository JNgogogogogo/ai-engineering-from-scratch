# KV Cache, Flash Attention & Inference Optimization · KV 缓存、Flash Attention 与推理优化

> 训练是并行的、受 FLOP 约束。推理是串行的、受内存约束。瓶颈不同，招数不同。
>
> Training is parallel and FLOP-bound. Inference is serial and memory-bound. Different bottleneck, different tricks.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 7 · 02 (Self-Attention), Phase 7 · 05 (Full Transformer), Phase 7 · 07 (GPT)
**Time:** ~75 minutes

## The Problem · 问题在哪

朴素的自回归解码器生成 `N` 个 token 要做 `O(N²)` 的计算：每一步都对整个前缀重算注意力。一段 4K token 的回复就是 1,600 万次注意力运算，其中大多数是冗余的。前缀 token 的每个隐藏状态一旦算出来就是确定的——你只需要拿新 token 的 query 去对之前所有 token 缓存好的 key 和 value 算一遍。

除此之外，注意力本身就是数据搬运大户。标准注意力要物化 N×N 的分数矩阵、N×d 的 softmax 输出、N×d 的最终输出——对 HBM 的读写次数太多。N≥2K 时，注意力先变成内存受限（memory-bound），然后才轮到 FLOP 受限。经典注意力核把现代 GPU 的算力浪费了 4–10 倍。

两项都出自 Dao et al. 的优化，把前沿推理从「慢」推到了「快」：

1. **KV 缓存（KV cache）。** 把每个前缀 token 的 K、V 向量存下来。每个新 token 的注意力就是一次 query 对缓存 key 的检索。每步生成的开销从 `O(N²)` 降到 `O(N)`。
2. **Flash Attention。** 把注意力计算分块（tile），让完整的 N×N 矩阵永远不落到 HBM。softmax + 矩阵乘全部在 SRAM 里完成。A100 上 2–4 倍墙钟加速；FP8 下 H100 上 5–10 倍。

到 2026 年，两者已是标配。每个生产推理栈（vLLM、TensorRT-LLM、SGLang、llama.cpp）都默认它们在。每个前沿模型出厂即开 Flash Attention。

> A naive autoregressive decoder does `O(N²)` work to generate `N` tokens: at each step it recomputes attention over the full prefix. For a 4K-token response that is 16M attention operations, most of them redundant. Every hidden state of a prefix token is deterministic once computed — you only need to run the new token's query against the cached keys and values of everything before.
> On top of that, attention itself moves a lot of data. Standard attention materializes an N×N score matrix, N×d softmax output, N×d final output — too many reads and writes to HBM. For N≥2K, attention becomes memory-bound before it becomes FLOP-bound. Classic attention kernels underuse modern GPUs by 4–10×.
> Two optimizations, both from Dao et al., pushed frontier inference from "slow" to "fast":
> 1. **KV cache.** Store the K and V vectors of every prefix token. Each new token's attention is one query against the cached keys. Inference reduces from `O(N²)` to `O(N)` per generation step.
> 2. **Flash Attention.** Tile the attention computation so the full N×N matrix never hits HBM. All of softmax + matmul happens in SRAM. 2–4× wall-clock speedup on A100; 5–10× on H100 with FP8.
> By 2026 both are universal. Every production inference stack (vLLM, TensorRT-LLM, SGLang, llama.cpp) assumes them. Every frontier model ships with Flash Attention enabled.

## The Concept · 概念

![KV 缓存的增长与 Flash Attention 的分块](../assets/kv-cache-flash-attn.svg)

### KV cache math · KV 缓存的账

每层解码器、每 token、每头：

```
bytes_per_token_per_layer = 2 * d_head * dtype_size
                          ^
                          K and V
```

7B 模型，32 层、32 头、d_head=128、fp16：

```
per token per layer = 2 * 128 * 2 = 512 bytes
per token (32 layers) = 16 KB
per 32K context = 512 MB
```

Llama 3 70B（80 层、d_head=128、GQA 用 8 个 KV 头）：

```
per token per layer = 2 * 8 * 128 * 2 = 4096 bytes (4 KB)
per 32K context = 10.4 GB
```

这 10 GB 就是为什么 Llama 3 70B 在 128K 上下文、batch size 为 1 时，光 KV 缓存就要吃掉一张 40 GB A100 的大半。

**GQA 是 KV 缓存上的最大赢家。** 64 头的 MHA 会是 32 GB。MLA 压得更狠。

拖动下面的维度，看缓存大小怎么动。把序列长度或 batch 拉大，看看多快就爆掉一张 GPU：

```figure
kv-cache-sizer
```

> That 10 GB is why Llama 3 70B at 128K context needs most of a 40 GB A100 just for KV cache at batch size 1.
> **GQA is the KV-cache win.** MHA with 64 heads would be 32 GB. MLA compresses even further.
> Drag the dimensions and watch the cache size move. Push the sequence length or batch up and see how fast it blows past a single GPU:

### Flash Attention — the tiling trick · Flash Attention——分块的门道

标准注意力：

```
S = Q @ K^T          (HBM read, N×N, HBM write)
P = softmax(S)       (HBM read, HBM write)
O = P @ V            (HBM read, HBM write)
```

三次 HBM 往返。H100 上，HBM 带宽是 3 TB/s；SRAM 是 30 TB/s。每多一次 HBM 往返，相比把一切留在片上就是 10 倍的减速。

Flash Attention：

```
for each block of Q (tile size ~128 × 128):
    load Q_tile into SRAM
    for each block of K, V:
        load K_tile, V_tile into SRAM
        compute S_tile = Q_tile @ K_tile^T     (SRAM)
        running softmax aggregation             (SRAM)
        accumulate into O_tile                  (SRAM)
    write O_tile to HBM
```

每个 tile 只有一次 HBM 往返。总内存占用从 `O(N²)` 降到 `O(N)`。反向传播选择重算部分前向值而不是存储它们——又一个内存上的赢面。

**数值技巧。** 运行中的 softmax 跨 tile 维护 `(max, sum)`，因此最终归一化是精确的。这不是近似——Flash Attention 的输出与标准注意力逐位一致（fp16 加法结合性的差异除外）。

**版本演进：**

| 版本 | 年份 | 关键变化 | 参考硬件上的加速 |
|---------|------|-----------|-------------------------------|
| Flash 1 | 2022 | 分块 SRAM kernel | A100 上 2× |
| Flash 2 | 2023 | 更好的并行度、causal 优先的排布 | A100 上 3× |
| Flash 3 | 2024 | Hopper 异步、FP8 | H100 上 1.5–2×（约 740 TFLOPs FP16） |
| Flash 4 | 2026 | Blackwell 5 级流水线、软件 exp2 | 推理优先（初期仅前向） |

Flash 4 发布时仅支持前向传播。训练仍用 Flash 3。Flash 4 的 GQA 与 varlen 支持尚未就绪（2026 年中）。

> Standard attention:
> Three HBM round trips. On H100, HBM bandwidth is 3 TB/s; SRAM is 30 TB/s. Every HBM trip is a factor-of-10 slowdown vs keeping everything on-chip.
> One HBM trip per tile. Total memory footprint drops from `O(N²)` to `O(N)`. Backward pass recomputes some values from the forward pass instead of storing them — another memory win.
> **Numerical trick.** Running softmax maintains `(max, sum)` across tiles so the final normalization is exact. Not an approximation — Flash Attention computes bit-identical output to standard attention (modulo fp16 non-associativity).
> Flash 4 is forward-pass only at launch. Training still uses Flash 3. GQA and varlen support for Flash 4 is pending (mid-2026).

### Speculative decoding — the other latency win · 投机解码——另一条延迟收益

便宜的小模型一次提出 N 个 token，大模型并行验证这 N 个。若验证接受了 k 个，你就用 1 次大模型前向换来了 k 个 token 的生成。代码和普通文本上典型 k=3–5。

2026 年的默认选项：

- **EAGLE 2 / Medusa。** 与验证器共享隐藏状态的集成草稿头。2–3 倍加速，无质量损失。
- **带草稿模型的投机解码。** 消费级硬件上 2–4 倍加速。
- **Lookahead 解码。** Jacobi 迭代；不需要草稿模型。小众但免费。

> Cheap model proposes N tokens. Big model verifies all N in parallel. If verification accepts k tokens, you paid 1 big-model forward pass for k generations. Typical k=3–5 on code and prose.
> 2026 defaults: **EAGLE 2 / Medusa.** Integrated draft heads that share the verifier's hidden states. 2–3× speedup with no quality loss. **Speculative decoding with draft model.** 2–4× speedup on consumer hardware. **Lookahead decoding.** Jacobi iteration; no draft model needed. Niche but free.

### Continuous batching · 连续批处理

经典批式推理：等最慢的序列跑完，再开新批。短回复提前完成时，GPU 就在空转。

连续批处理（continuous batching，首发于 Orca，现已在 vLLM、TensorRT-LLM、SGLang）：旧请求一完成就把新请求换入 batch。典型聊天负载下吞吐提升 5–10 倍。

> Classic batched inference: wait for the slowest sequence to finish, then start a new batch. Wastes GPU when short responses finish early.
> Continuous batching (first shipped in Orca, now in vLLM, TensorRT-LLM, SGLang): swap new requests into the batch as soon as old ones finish. 5–10× throughput gain for typical chat workloads.

### PagedAttention — KV cache as virtual memory · PagedAttention——把 KV 缓存当虚拟内存

vLLM 的招牌特性。KV 缓存按 16-token 块分配；页表把逻辑位置映射到物理块。让你能在并行采样之间共享 KV（束搜索、并行采样）、热替换前缀做提示缓存、并整理内存碎片。相比朴素的连续分配，吞吐提升 4 倍。

> vLLM's headline feature. KV cache is allocated in 16-token blocks; a page table maps logical positions to physical blocks. Lets you share KV across parallel samples (beam search, parallel sampling), hot-swap prefixes for prompt caching, and defragment memory. 4× throughput improvement over naive contiguous allocation.

```figure
flash-attention-memory
```

## Build It · 动手造

见 `code/main.py`。我们实现：

1. 一个朴素的 `O(N²)` 增量解码器。
2. 一个 `O(N)` 的 KV 缓存解码器。
3. 一个模拟 Flash Attention 运行最大值算法的分块 softmax。

> See `code/main.py`. We implement: 1. A naive `O(N²)` incremental decoder. 2. A `O(N)` KV-cached decoder. 3. A tiled softmax that simulates Flash Attention's running-max algorithm.

### Step 1: KV cache · 第 1 步：KV 缓存

```python
class KVCache:
    def __init__(self, n_layers, n_heads, d_head):
        self.K = [[[] for _ in range(n_heads)] for _ in range(n_layers)]
        self.V = [[[] for _ in range(n_heads)] for _ in range(n_layers)]

    def append(self, layer, head, k, v):
        self.K[layer][head].append(k)
        self.V[layer][head].append(v)

    def read(self, layer, head):
        return self.K[layer][head], self.V[layer][head]
```

很简单：在按层、按头的列表里持续追加每 token 的 K、V 向量。

> Simple: keep growing per-token K, V vectors in per-layer, per-head lists.

### Step 2: tiled softmax · 第 2 步：分块 softmax

```python
def tiled_softmax_dot(q, K, V, tile=4):
    """Flash-attention-style softmax(qK^T)V with running max/sum."""
    m = float("-inf")
    s = 0.0
    out = [0.0] * len(V[0])
    for start in range(0, len(K), tile):
        k_block = K[start:start + tile]
        v_block = V[start:start + tile]
        scores = [sum(qi * ki for qi, ki in zip(q, k)) for k in k_block]
        new_m = max(m, *scores)
        exp_old = math.exp(m - new_m) if m != float("-inf") else 0.0
        exp_new = [math.exp(sc - new_m) for sc in scores]
        s = s * exp_old + sum(exp_new)
        for j in range(len(out)):
            out[j] = out[j] * exp_old + sum(e * v[j] for e, v in zip(exp_new, v_block))
        m = new_m
    return [o / s for o in out]
```

与一次性 `softmax(qK) V` 的输出逐位一致，但任意时刻的工作集只是一个 `tile × d_head` 块，而不是完整的 `N × d_head`。

> Bit-identical output to `softmax(qK) V` in one shot, but at any time the working set is a `tile × d_head` block, not the full `N × d_head`.

### Step 3: compare naive vs cached decoding on 100-token generation · 第 3 步：在 100 token 生成上对比朴素与缓存解码

统计注意力运算次数。朴素：`O(N²)` = 5050；缓存：`O(N)` = 100。代码会把两者都打印出来。

> Count attention operations. Naive: `O(N²)` = 5050. Cached: `O(N)` = 100. The code prints both.

## Use It · 实战用法

```python
# HuggingFace transformers auto-enables KV cache on decoder-only generate().
from transformers import AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.2-3B",
    attn_implementation="flash_attention_2",  # use FA3 if Hopper
    torch_dtype="bfloat16",
)
# generate() uses KV cache automatically
```

vLLM 生产部署：

```bash
pip install vllm
vllm serve meta-llama/Llama-3.1-70B-Instruct \
    --tensor-parallel-size 4 \
    --max-model-len 32768 \
    --enable-prefix-caching \
    --kv-cache-dtype fp8
```

跨请求的前缀缓存（prefix caching）是 2026 年的一大利好——同一个系统提示、few-shot 示例或长上下文文档可以跨调用复用 KV。对带有重复工具提示的 agent 负载，前缀缓存通常能带来 5 倍的吞吐提升。

> Prefix caching across requests is a big 2026 win — the same system prompt, few-shot examples, or long context document reuses KV across calls. For agent workloads with repeated tool prompts, prefix caching is routinely 5× throughput gain.

## Ship It · 交付

见 `outputs/skill-inference-optimizer.md`。这个技能为一个新的推理部署挑选注意力实现、KV 缓存策略、量化方案和投机解码配置。

> See `outputs/skill-inference-optimizer.md`. The skill picks attention implementation, KV cache strategy, quantization, and speculative decoding for a new inference deployment.

## Exercises · 练习

1. **简单。** 跑 `code/main.py`。确认朴素与缓存解码器产出相同的结果；留意运算次数的差异。
2. **中等。** 实现前缀缓存：给定提示 P 和若干续写，先对 P 跑一次前向填充 KV 缓存，再按续写分支。测与每次重新编码 P 相比的加速比。
3. **困难。** 实现玩具版 PagedAttention：KV 缓存按固定 16-token 块分配并配一个空闲链表。序列结束时把块还给池子。模拟 1,000 次不同长度的聊天补全，对比连续分配下的内存碎片。

> 1. **Easy.** Run `code/main.py`. Confirm the naive and cached decoders produce the same output; note the op-count difference.
> 2. **Medium.** Implement prefix caching: given a prompt P and several completions, run one forward pass over P to fill the KV cache, then branch per-completion. Measure speedup vs re-encoding P for each.
> 3. **Hard.** Implement a toy PagedAttention: KV cache in fixed 16-token blocks with a free-list. When a sequence finishes, return its blocks to the pool. Simulate 1,000 chat completions with varying lengths. Compare memory fragmentation vs contiguous allocation.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| KV cache（KV 缓存） | 「让解码变快的那个技巧」 | 存下每个前缀 token 的 K 和 V；新 query 直接对它们算注意力，不再重算。 |
| HBM | 「GPU 主存」 | High Bandwidth Memory；H100 上 80 GB，B200 上 192 GB。带宽约 3 TB/s。 |
| SRAM | 「片上内存」 | 每 SM 的快速内存，H100 上每 SM 约 256 KB。带宽约 30 TB/s。 |
| Flash Attention | 「分块注意力 kernel」 | 不在 HBM 里物化 N×N 矩阵就把注意力算完。 |
| Continuous batching（连续批处理） | 「不等待的批处理」 | 完成的序列换出、新序列换入，不用清空整个 batch。 |
| PagedAttention | 「vLLM 的招牌」 | KV 缓存按固定块分配并配页表；消除碎片。 |
| Prefix caching（前缀缓存） | 「复用长提示」 | 跨请求缓存共享前缀的 KV；对 agent 是重大成本削减。 |
| Speculative decoding（投机解码） | 「草稿 + 验证」 | 便宜的草稿模型提出 token；大模型一次前向验证 k 个。 |

## Further Reading · 延伸阅读

- [Dao et al. (2022). FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness](https://arxiv.org/abs/2205.14135) — Flash 1。
- [Dao (2023). FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning](https://arxiv.org/abs/2307.08691) — Flash 2。
- [Shah et al. (2024). FlashAttention-3: Fast and Accurate Attention with Asynchrony and Low-precision](https://arxiv.org/abs/2407.08608) — Flash 3。
- [FlashAttention-4 release notes (Dao-AILab, 2026)](https://github.com/Dao-AILab/flash-attention) — Blackwell 5 级流水线与软件 exp2 技巧；读仓库 README 可看到本课提到的仅前向发布的注意事项。
- [Kwon et al. (2023). Efficient Memory Management for Large Language Model Serving with PagedAttention](https://arxiv.org/abs/2309.06180) — vLLM 论文。
- [Leviathan et al. (2023). Fast Inference from Transformers via Speculative Decoding](https://arxiv.org/abs/2211.17192) — 投机解码。
- [Li et al. (2024). EAGLE: Speculative Sampling Requires Rethinking Feature Uncertainty](https://arxiv.org/abs/2401.15077) — 本课引用的集成草稿路线的 EAGLE-1/2 论文。
- [Cai et al. (2024). Medusa: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads](https://arxiv.org/abs/2401.10774) — 与 EAGLE 并列引用的 Medusa 路线。
- [vLLM docs — PagedAttention](https://docs.vllm.ai/en/latest/design/kernel/paged_attention.html) — 关于 16-token 块与页表设计的权威深读。
