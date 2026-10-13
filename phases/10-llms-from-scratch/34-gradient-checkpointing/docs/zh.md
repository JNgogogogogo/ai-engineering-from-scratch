# Gradient Checkpointing and Activation Recomputation · 梯度检查点（gradient checkpointing）与激活重计算

> 反向传播会保留每一个中间激活。在 70B 参数、128K 上下文下，这是每 rank 3 TB 的激活。检查点用 FLOPs 换内存：重算而不是保存。问题在于丢弃哪些分段，而答案绝不是「全部都丢」。
>
> Backprop keeps every intermediate activation. At 70B parameters and 128K context that is 3 TB of activations per rank. Checkpointing trades FLOPs for memory: recompute instead of save. The question is which segments to drop, and the answer is not "all of them."

**Type:** Build
**Languages:** Python (with numpy, optional torch)
**Prerequisites:** Phase 10 Lesson 04 (Pre-Training Mini-GPT), Phase 10 Lesson 05 (Scaling & Distributed)
**Time:** ~70 minutes

## The Problem · 问题在哪

训练 transformer 时，每一层都要保存反向求导所需的每个算子的输入：注意力的输入、Q/K/V 投影、softmax 输出、FFN 输入、归一化输出，以及残差流（residual stream）。对 hidden 大小 `d`、序列长度 `L`、batch `B` 的一层来说，量级是每层 `12 * B * L * d` 个浮点数。

`d=8192, L=8192, B=1` 时，BF16 下每层 800 MB。64 层模型就是 51 GB 激活——这还没乘 microbatch 大小，没加注意力 softmax 中间量（每 head `L^2`），也没算张量并行的部分副本。

这是一张两边的账单：BF16 权重加优化器状态也许塞得进 80GB，但激活会把你挤爆。梯度检查点（gradient checkpointing，又名激活重计算 activation recomputation）是标准解法。丢弃大部分激活；反向时重跑前向把它们找回来。代价：额外 FLOPs。收益：内存按「检查点分段数 / 总层数」的比例下降。

朴素做法下，检查点让每步前向 FLOPs 多出约 33%。做得好——按 Korthikanti 等人的「聪明选择」做选择性检查点——能以不到 5% 的 FLOP 开销省下 5 倍内存。在 FP8 矩阵乘、FSDP offload 和专家并行 MoE 的时代这真的要紧：内存和浪费的算力，你都负担不起。

> Training a transformer stores, for each layer, the inputs to every op that is differentiated in backward: the attention inputs, the Q/K/V projections, the softmax output, the FFN inputs, the norm outputs, and the residual stream. For a layer with hidden size `d`, sequence length `L`, batch `B`, this is on the order of `12 * B * L * d` floats per layer. ... Gradient checkpointing (aka activation recomputation) is the standard fix. Drop most activations; redo the forward during backward to get them back. Cost: extra FLOPs. Benefit: memory drops by the ratio of checkpoint segments to total layers. ... Done naively, checkpointing costs roughly 33% more forward-pass FLOPs per step. Done well — selective checkpointing per the "smart selection" of Korthikanti et al. — you save 5x memory for under 5% FLOP overhead.

## The Concept · 概念

### What Backward Actually Needs · 反向传播真正需要什么

`output = layer(input)`。反向想要 `grad_input` 和 `grad_params`。要算出它们，需要：

- `input`（对线性层计算 `grad_params = input.T @ grad_output`）
- 某些激活导数的中间量（ReLU/GELU/softmax 的导数依赖激活值本身）

前向会把它们自动存进 autograd 图。每个 `tensor.retain_grad()` 和每个需要其输入的算子都持有一个引用。

> `output = layer(input)`. Backward wants `grad_input` and `grad_params`. To compute them it needs: ... The forward pass stores these automatically in the autograd graph. Every `tensor.retain_grad()` and every op that needs its input retains a reference.

### Naive Full Checkpointing · 朴素的全量检查点

把网络切成 `N` 段。前向时只存每段的*输入*。反向需要中间量时，重跑该段的前向把中间量物化出来，再求导。

例：32 层 transformer 切成 32 段、每段 1 层。

- 内存：32 个层输入（小）对比 32 *（每层激活体积）（巨大）。
- 额外计算：每段多一次前向，即总前向 FLOPs 多约 33%（反向是 2 倍前向，整个 step 从 1 + 2 = 3 个单位变成 1 + 1 + 2 = 4 个单位）。

这就是 Chen 等人 2016 年的原始配方：每 `sqrt(L)` 层放一个检查点，以平衡内存与计算。L=64 时即 8 个检查点。

> Split the network into `N` segments. During forward, store only the *input* to each segment. When backward needs intermediates, rerun the segment's forward pass to materialize them, then differentiate. ... This is the original Chen et al. 2016 recipe: one checkpoint every `sqrt(L)` layers to balance memory and compute. For L=64, that's 8 checkpoints.

### Selective Checkpointing (Korthikanti 2022) · 选择性检查点（Korthikanti 2022）

不是所有激活的存储成本都一样。注意力 softmax 输出是 `B*L*L*heads`，随序列长度*平方*增长。FFN 隐藏激活是 `B*L*4d`，线性增长。长序列下 softmax 占主导。

选择性检查点保留存储便宜的激活（线性投影、残差），只重算昂贵的（注意力）。你付出极小的重算 FLOPs，省下 O(L^2) 的内存。

Megatron-Core 把它实现为「selective」激活重计算。多数 2024 年之后的前沿训练运行都在用。

> Not all activations cost the same. The attention softmax output is `B*L*L*heads` and grows *quadratically* with sequence length. The FFN hidden activation is `B*L*4d` and grows linearly. For long sequences the softmax dominates. ... Selective checkpointing keeps the cheap-to-store activations (linear projections, residuals) and recomputes only the expensive ones (attention). You pay minimal FLOPs to recompute but save the O(L^2) memory. ... Megatron-Core implements this as "selective" activation recomputation. Used in most 2024+ frontier training runs.

### Offload · 卸载（offload）

重计算的替代方案：在前向与反向之间把激活搬到 CPU RAM。需要 PCIe 带宽；当空闲带宽超过重物化（rematerialization）的成本时划算。混合策略很常见：一部分层做检查点，另一部分层做 offload。

FSDP2 把 offload 作为一等公民选项提供。GPU 被内存卡住而 CPU-GPU 传输有余量时，offload 大放异彩。

> Alternative to recompute: ship activations to CPU RAM between forward and backward. Requires PCIe bandwidth; beneficial when idle bandwidth exceeds the cost of rematerialization. Mixed strategies are common: checkpoint some layers, offload others. ... FSDP2 ships offload as a first-class option. Offload shines when GPU is bottlenecked on memory but CPU-GPU transfer has headroom.

### Recompute Cost Model · 重计算的成本模型

`L` 层中每 `k` 层做一次朴素检查点时，每步 FLOPs：

```
flops_fwd_normal = L * f_layer
flops_bwd_normal = 2 * L * f_layer
flops_total_normal = 3 * L * f_layer

flops_fwd_ckpt = L * f_layer
flops_recompute = L * f_layer  # one extra forward per layer in the segment
flops_bwd_ckpt = 2 * L * f_layer
flops_total_ckpt = 4 * L * f_layer
overhead = 4 / 3 - 1 = 0.33 = 33%
```

选择性检查点只重算注意力核，不重算整层：

```
flops_recompute_selective = L * f_attention ~= L * f_layer * 0.15
overhead_selective = (3 + 0.15) / 3 - 1 = 0.05 = 5%
```

> Per-step FLOPs with naive checkpointing every `k` layers out of `L`: ... With selective checkpointing you recompute only the attention kernel, not the whole layer: ...

### Memory Savings Model · 内存节省模型

每层激活体积记为 `A`。`L` 层的总激活内存为 `L * A`。

全量检查点（分段大小 1）：只存 `L * input_volume`（标准 transformer 约 `L * 1/10 A`）。省下约 `9 * L * A * 1/10`。

每 `k` 层检查点：存 `L/k * A`，外加活动段内 `k-1` 层的量。

`k = sqrt(L)` 时，内存与重算成本都按 `sqrt(L)` 缩放——对成本均匀的层，这是最优折中。

> Activation volume per layer: `A`. For `L` layers, total activation memory: `L * A`. ... At `k = sqrt(L)`, memory and recompute cost both scale with `sqrt(L)` — the optimal tradeoff for uniform-cost layers.

### When Not to Checkpoint · 什么时候不要做检查点

- 流水线阶段内部已经在途（in-flight）的最内层。反正它们必须完成。
- 首尾层若主导了该阶段的计算（transformer 中罕见），不要动。
- 已经在用 FlashAttention 的注意力核——Flash 本身就在快速重算 softmax，再叠加层级检查点收益很小。

> The innermost layers of a pipeline stage already in-flight. They have to finish anyway. ... The first and last layers if they dominate the stage's compute (rare in transformers). ... Attention kernels already using FlashAttention — Flash already recomputes the softmax fast, so additional layer-level checkpointing adds little on top.

### Implementation Patterns · 实现模式

1. **函数包装器：**用 `torch.utils.checkpoint.checkpoint(fn, input)` 包住一段。PyTorch 只存 `input`，反向时重算其余一切。

2. **装饰器式：**把层标记为可检查点；trainer 在配置阶段决定包装哪些段。

3. **手写显式重算：**自己写反向，调用自定义的 `recompute_forward`，用存储的输入复现前向。

三种方式功能上等价。包装器是标准写法。

> All three give the same functional result. Wrappers are the standard idiom.

### Interaction with TP / PP / FP8 · 与 TP / PP / FP8 的交互

- **张量并行：**重算时检查点输入需要重新 gather 或 rescatter；要把通信成本算进去。
- **流水线并行：**典型模式是对每个流水线阶段的前向做检查点，让逆序 microbatch 能复用激活内存。
- **FP8 重算：**重算期间更新的 amax 历史必须与原始前向一致，否则 FP8 scale 会漂移。多数框架会对 scale 做快照。

> **Tensor parallel:** checkpoint inputs must be gathered or rescattered on recompute; handle the communication cost. ... **Pipeline parallel:** typical pattern is to checkpoint each pipeline-stage's forward so reverse-order microbatches can reuse activation memory. ... **FP8 recompute:** amax histories updated during recompute must match the original forward's, or the FP8 scale drifts. Most frameworks snapshot the scale.

```figure
activation-recompute
```

## Build It · 动手造

### Step 1: A Toy Model With Segments · 第 1 步：带分段的玩具模型

```python
import numpy as np


def linear_forward(x, w, b):
    return x @ w + b


def relu(x):
    return np.maximum(x, 0)


def layer_forward(x, w1, b1, w2, b2):
    h = relu(linear_forward(x, w1, b1))
    return linear_forward(h, w2, b2)


def model_forward(x, params):
    activations = [x]
    h = x
    for w1, b1, w2, b2 in params:
        h = layer_forward(h, w1, b1, w2, b2)
        activations.append(h)
    return h, activations
```

### Step 2: Naive Backward Needing All Activations · 第 2 步：需要全部激活的朴素反向传播

```python
def model_backward(grad_output, activations, params):
    grads = [None] * len(params)
    g = grad_output
    for i in range(len(params) - 1, -1, -1):
        w1, b1, w2, b2 = params[i]
        x_in = activations[i]
        h_pre = linear_forward(x_in, w1, b1)
        h = relu(h_pre)
        gh = g @ w2.T
        gw2 = h.T @ g
        gb2 = g.sum(axis=0)
        g_pre = gh * (h_pre > 0)
        gx = g_pre @ w1.T
        gw1 = x_in.T @ g_pre
        gb1 = g_pre.sum(axis=0)
        grads[i] = (gw1, gb1, gw2, gb2)
        g = gx
    return g, grads
```

### Step 3: Checkpoint-Every-k Memory · 第 3 步：每 k 层做检查点的内存

```python
def model_forward_checkpointed(x, params, k=4):
    saved_inputs = [x]
    h = x
    for i, (w1, b1, w2, b2) in enumerate(params):
        h = layer_forward(h, w1, b1, w2, b2)
        if (i + 1) % k == 0:
            saved_inputs.append(h)
    return h, saved_inputs


def model_backward_checkpointed(grad_output, saved_inputs, params, k=4):
    grads = [None] * len(params)
    g = grad_output
    segments = [(j * k, min((j + 1) * k, len(params))) for j in range(len(saved_inputs))]
    for seg_idx in range(len(saved_inputs) - 1, -1, -1):
        start, end = segments[seg_idx]
        if start >= end:
            continue
        x_in = saved_inputs[seg_idx]
        _, seg_acts = model_forward(x_in, params[start:end])
        g, seg_grads = model_backward(g, seg_acts, params[start:end])
        for j, gr in enumerate(seg_grads):
            grads[start + j] = gr
    return g, grads
```

### Step 4: Cost Model · 第 4 步：成本模型

```python
def checkpoint_cost(n_layers, segment_size, flops_per_layer=1.0):
    fwd = n_layers * flops_per_layer
    recompute = n_layers * flops_per_layer
    bwd = 2 * n_layers * flops_per_layer
    return {
        "fwd": fwd,
        "recompute": recompute,
        "bwd": bwd,
        "total": fwd + recompute + bwd,
        "overhead_vs_no_ckpt": (fwd + recompute + bwd) / (fwd + bwd) - 1.0,
    }


def selective_checkpoint_cost(n_layers, attention_fraction=0.15,
                              flops_per_layer=1.0):
    fwd = n_layers * flops_per_layer
    recompute = n_layers * attention_fraction * flops_per_layer
    bwd = 2 * n_layers * flops_per_layer
    return {
        "fwd": fwd,
        "recompute": recompute,
        "bwd": bwd,
        "total": fwd + recompute + bwd,
        "overhead_vs_no_ckpt": (fwd + recompute + bwd) / (fwd + bwd) - 1.0,
    }
```

### Step 5: Memory Estimator · 第 5 步：内存估算器

```python
def activation_memory_mb(n_layers, hidden=8192, seq=8192,
                        batch=1, bytes_per_value=2):
    per_layer = 12 * batch * seq * hidden * bytes_per_value
    return n_layers * per_layer / 1e6


def memory_after_checkpoint(n_layers, segment_size, hidden=8192,
                           seq=8192, batch=1, bytes_per_value=2):
    n_seg = max(1, n_layers // segment_size)
    saved = (n_seg + segment_size) * 1 * batch * seq * hidden * bytes_per_value
    return saved / 1e6
```

### Step 6: Optimal Segment Size · 第 6 步：最优分段大小

```python
def optimal_segment(n_layers):
    return int(round(np.sqrt(n_layers)))
```

### Step 7: Selective Checkpoint Decision · 第 7 步：选择性检查点决策

```python
def should_recompute(layer_type, activation_bytes, recompute_flops_ratio):
    if layer_type == "attention" and activation_bytes > 100 * 1e6:
        return True
    if layer_type == "ffn" and activation_bytes > 500 * 1e6:
        return recompute_flops_ratio < 0.1
    return False
```

## Use It · 实战用法

- **torch.utils.checkpoint**：`from torch.utils.checkpoint import checkpoint` —— PyTorch 的标准包装器。包住一个函数；只存输入，反向时重算。
- **Megatron-Core 激活重计算**：支持 `selective`、`full`、`block` 三种模式。2024 年之后前沿训练的标准配置。
- **FSDP2 offload**：`module.to_empty(device="cpu")` 配合 FSDP2 的 `offload_policy`，把激活分片卸到 CPU 而不是重算。
- **DeepSpeed ZeRO-Offload**：把优化器状态和激活卸到 CPU，与检查点互补。

> **torch.utils.checkpoint**: `from torch.utils.checkpoint import checkpoint` — the canonical wrapper in PyTorch. Wraps a function; stores only inputs, recomputes on backward. ... **FSDP2 offload**: `module.to_empty(device="cpu")` with `offload_policy` in FSDP2 shards activations to CPU instead of recomputing. ... **DeepSpeed ZeRO-Offload**: CPU offload for optimizer states and activations, complementing checkpointing.

## Ship It · 交付

本课产出 `outputs/prompt-activation-recompute-policy.md` —— 一个提示词：输入你的模型配置（层数、hidden、seq、batch）和可用 GPU 内存，输出一份逐层重计算策略（none / selective / full / offload）。

> This lesson produces `outputs/prompt-activation-recompute-policy.md` — a prompt that takes your model config (layers, hidden, seq, batch) and available GPU memory and emits a per-layer recompute policy (none / selective / full / offload).

## Exercises · 练习

1. 验证正确性。运行 `model_forward` + `model_backward`（全量激活）对比 `model_forward_checkpointed` + `model_backward_checkpointed`（分段）。参数梯度必须精确到机器精度一致。
2. 把分段大小 `k` 从 1 扫到 `L`。画出 FLOP 开销和内存。找出曲线的拐点。
3. 实现选择性检查点：保存注意力模块的输入，但不保存其中间量。对 seq=8192 的 32 层模型，测它与整层检查点相比的 FLOP 开销。
4. 加上 offload。把分段输入存进一个模拟的「CPU 缓冲区」（一个单独的列表）。把「PCIe 带宽」测成字节/时间，找出 offload 与重算的盈亏平衡点。
5. 基准测试一个真实的 PyTorch transformer，开与不开 `torch.utils.checkpoint` 各跑一次。测内存（用 `torch.cuda.max_memory_allocated`）和每步耗时。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|----------------------|
| Gradient checkpointing | 「重跑前向来省内存」 | 只存分段输入；反向时重算中间量，拿到支持求导的张量 |
| Activation recomputation | 「就是检查点」 | 同一技术的 HPC 风味叫法 |
| Segment size (k) | 「多少层共用一个检查点」 | 其中间量被一起丢弃、再一起重物化的层数 |
| Selective checkpointing | 「Korthikanti 的技巧」 | 只重算存储昂贵的激活（注意力 softmax）；便宜的保留 |
| Full checkpointing | 「朴素版本」 | 每个分段里每层的中间量都重算 |
| Block checkpointing | 「粗粒度」 | 以整个 transformer 块为单位做检查点；粒度最大 |
| FLOP overhead | 「算力税」 | 每步额外 FLOPs =（重算 FLOPs）/（前向 + 反向 FLOPs）；朴素 33%，选择性 5% |
| Activation offload | 「搬去 CPU」 | 在前向->反向之间把激活移到 CPU 内存；重算的替代方案 |
| sqrt-L rule | 「经典最优」 | 对成本均匀的层，最优检查点间隔是 sqrt(L) 层 |
| Attention-softmax volume | 「O(L^2) 问题」 | L^2 * heads * batch 个浮点数；长上下文下主导激活内存 |

## Further Reading · 延伸阅读

- [Chen et al., 2016 -- "Training Deep Nets with Sublinear Memory Cost"](https://arxiv.org/abs/1604.06174) —— 正式提出梯度检查点的原始论文
- [Korthikanti et al., 2022 -- "Reducing Activation Recomputation in Large Transformer Models"](https://arxiv.org/abs/2205.05198) —— 选择性激活重计算与形式化的成本分析
- [Pudipeddi et al., 2020 -- "Training Large Neural Networks with Constant Memory using a New Execution Algorithm"](https://arxiv.org/abs/2002.05645) —— 基于 reverse-mode 重物化的另一种恒定内存方案
- [Ren et al., 2021 -- "ZeRO-Offload: Democratizing Billion-Scale Model Training"](https://arxiv.org/abs/2101.06840) —— 规模化的激活 offload
- [PyTorch torch.utils.checkpoint docs](https://pytorch.org/docs/stable/checkpoint.html) —— 标准 API
- [Megatron Bridge activation recomputation documentation](https://docs.nvidia.com/nemo/megatron-bridge/latest/training/activation-recomputation.html) —— selective、full、block 三种模式
