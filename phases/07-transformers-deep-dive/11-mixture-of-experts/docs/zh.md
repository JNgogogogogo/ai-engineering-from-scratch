# Mixture of Experts (MoE) · 混合专家（MoE）：稀疏即扩展

> 稠密 70B Transformer 对每个 token 激活全部参数。671B 的 MoE 每个 token 只激活 37B，却在所有基准上赢过前者。稀疏化是这十年最重要的缩放思想。
>
> A dense 70B transformer activates every parameter for every token. A 671B MoE activates only 37B per token and beats it on every benchmark. Sparsity is the most important scaling idea of the decade.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 7 · 05 (Full Transformer), Phase 7 · 07 (GPT)
**Time:** ~45 minutes

## The Problem · 问题在哪

稠密 Transformer 推理时的 FLOPs 约等于它的参数量（前向传播再乘 2）。把稠密模型放大，每个 token 都要付全款。到 2024 年，前沿模型撞上了算力墙：想明显更聪明，就得让每个 token 的 FLOPs 指数级增长。

混合专家（Mixture of Experts, MoE）打断这个绑定。把每个 FFN 换成 `E` 个独立专家 + 一个路由器（router），由路由器为每个 token 挑出 `k` 个专家。总参数 = `E × FFN_size`；每 token 激活参数 = `k × FFN_size`。2026 年的典型配置：`E=256`，`k=8`。存储随 `E` 涨，算力随 `k` 涨。

2026 年的前沿几乎全是 MoE：DeepSeek-V3（671B 总参 / 37B 激活）、Mixtral 8×22B、Qwen2.5-MoE、Llama 4、Kimi K2、gpt-oss。在 Artificial Analysis 的独立排行榜上，开源前 10 全是 MoE。

> A dense transformer's FLOPs at inference equal its parameter count (times 2 for forward pass). Scale up a dense model and every token pays the full bill. By 2024 the frontier was hitting a compute wall: to be meaningfully smarter, you needed exponentially more FLOPs per token.
> Mixture of Experts breaks this link. Replace each FFN with `E` independent experts + a router that picks `k` experts per token. Total parameters = `E × FFN_size`. Active parameters per token = `k × FFN_size`. Typical 2026 configuration: `E=256`, `k=8`. Storage scales with `E`, compute scales with `k`.
> The 2026 frontier is almost entirely MoE: DeepSeek-V3 (671B total / 37B active), Mixtral 8×22B, Qwen2.5-MoE, Llama 4, Kimi K2, gpt-oss. On Artificial Analysis's independent leaderboard, the top 10 open-source models are all MoE.

## The Concept · 概念

![MoE 层：路由器为每个 token 从 E 个专家中选出 k 个](../assets/moe.svg)

### The FFN swap · 替换 FFN

稠密 Transformer 块：

```
h = x + attn(norm(x))
h = h + FFN(norm(h))
```

MoE 块：

```
h = x + attn(norm(x))
scores = router(norm(h))              # (N_tokens, E)
top_k = argmax_k(scores)              # pick k of E per token
h = h + sum_{e in top_k}(
        gate(scores[e]) * Expert_e(norm(h))
    )
```

每个专家都是独立的 FFN（通常是 SwiGLU）。路由器只是一个线性层。每个 token 挑自己的 `k` 个专家，拿到它们输出的门控混合。

> Every expert is an independent FFN (typically SwiGLU). The router is a single linear layer. Each token picks its own `k` experts and gets a gated mixture of their outputs.

### The load-balancing problem · 负载均衡问题

如果路由器把 90% 的 token 都塞给专家 3，其他专家就会饿死。人们试过三种修法：

1. **辅助负载均衡损失**（Switch Transformer、Mixtral）。加一个与专家使用方差成正比的惩罚项。有效，但多了一个超参数和一路额外的梯度信号。
2. **专家容量 + 丢 token**（早期 Switch）。每个专家最多处理 `C × N/E` 个 token；超出的 token 跳过该层。伤质量。
3. **无辅助损失均衡**（auxiliary-loss-free，DeepSeek-V3）。加一个可学习的逐专家偏置来影响路由器的 top-k 选择。偏置在训练损失之外更新，不给主目标加惩罚。2024 年的大解锁。

DeepSeek-V3 的做法：每个训练步之后，检查每个专家的使用量是高于还是低于目标，按 `±γ` 微调偏置。选择用 `scores + bias`；用于门控的专家概率保持原始 `scores` 不变。把「路由」与「表达」解耦。

> If the router puts 90% of tokens through expert 3, the other experts starve. Three fixes have been tried:
> 1. **Auxiliary load-balancing loss** (Switch Transformer, Mixtral). Add a penalty proportional to the variance in expert usage. Works, but adds a hyperparameter and a second gradient signal.
> 2. **Expert capacity + token dropping** (early Switch). Each expert processes at most `C × N/E` tokens; overflow tokens skip the layer. Hurts quality.
> 3. **Auxiliary-loss-free balancing** (DeepSeek-V3). Add a learned per-expert bias that shifts the router's top-k selection. Bias is updated outside the training loss. No penalty on the main objective. 2024's big unlock.
> DeepSeek-V3's approach: after each training step, for every expert, check if its usage is above or below the target. Nudge the bias by `±γ`. Selection uses `scores + bias`. Expert probabilities used for gating are the raw `scores` unchanged. Decouples routing from expression.

### Shared experts · 共享专家

DeepSeek-V2/V3 还把专家分成*共享*与*路由*两类。每个 token 都要过所有共享专家；路由专家靠 top-k 挑选。共享专家捕获共性知识，路由专家负责专精。V3 用 1 个共享专家加 256 选 8 的路由专家。

> DeepSeek-V2/V3 also split experts into *shared* and *routed*. Every token passes through all shared experts. Routed experts are picked via top-k. Shared experts capture common knowledge; routed experts specialize. V3 runs 1 shared expert plus top-8 of 256 routed.

### Fine-grained experts · 细粒度专家

经典 MoE（GShard、Switch）：每个专家和一个完整 FFN 一样宽。`E` 小（8–64），`k` 小（1–2）。

现代细粒度 MoE（DeepSeek-V3、Qwen-MoE）：每个专家更窄（FFN 的 1/8）。`E` 大（256+），`k` 更大（8+）。总参数相同，但组合数增长快得多——每 token 有 `C(256, 8) = 400 万亿` 种可能的「专家组合」。质量上升，延迟持平。

> Classic MoE (GShard, Switch): each expert is as wide as a full FFN. `E` is small (8–64), `k` is small (1–2).
> Modern fine-grained MoE (DeepSeek-V3, Qwen-MoE): each expert is narrower (1/8 FFN size). `E` is large (256+), `k` is larger (8+). Same total parameters, but combinations scale much faster. `C(256, 8) = 400 trillion` possible "experts" per token. Quality goes up, latency stays flat.

### The cost profile · 成本画像

每个 token、每一层：

| 配置 | 每 token 激活参数 | 总参数 |
|--------|-----------------------|--------------|
| Mixtral 8×22B | ~39B | 141B |
| Llama 3 70B（稠密） | 70B | 70B |
| DeepSeek-V3 | 37B | 671B |
| Kimi K2（MoE） | ~32B | 1T |

DeepSeek-V3 在几乎每个基准上都赢 Llama 3 70B（稠密），而每 token 激活的 FLOPs 更少。参数越多 = 知识越多；激活 FLOPs 越多 = 每 token 算力越多。MoE 把两者解耦。

> DeepSeek-V3 beats Llama 3 70B (dense) on almost every benchmark while doing **fewer active FLOPs per token**. More parameters = more knowledge. More active FLOPs = more compute per token. MoE decouples them.

### The catch: memory · 代价：显存

无论哪些专家被触发，所有专家都常驻 GPU。一个 671B 模型的 fp16 权重需要约 1.3 TB 显存。前沿 MoE 的部署必须用专家并行（expert parallelism）——把专家分片到多张 GPU，让 token 跨网络路由。延迟瓶颈是 all-to-all 通信，不是矩阵乘法。

> All experts live on GPU regardless of which ones fire. A 671B model needs ~1.3 TB of VRAM for fp16 weights. Frontier MoE deployment requires expert parallelism — shard experts across GPUs, route tokens across the network. Latency is dominated by the all-to-all communication, not the matmul.

```figure
expert-routing
```

## Build It · 动手造

见 `code/main.py`。一个纯标准库实现的紧凑 MoE 层，包含：

- `n_experts=8` 个类 SwiGLU 专家（为便于演示，每个只是一层线性）
- top-k=2 路由
- softmax 归一化的门控权重
- 通过逐专家偏置实现的无辅助损失均衡

> See `code/main.py`. A compact MoE layer in pure stdlib with: `n_experts=8` SwiGLU-ish experts (one linear each, for illustration); top-k=2 routing; softmax-normalized gating weights; auxiliary-loss-free balancing via per-expert bias.

### Step 1: the router · 第 1 步：路由器

```python
def route(hidden, W_router, top_k, bias):
    scores = [sum(h * w for h, w in zip(hidden, W_router[e])) for e in range(len(W_router))]
    biased = [s + b for s, b in zip(scores, bias)]
    top_idx = sorted(range(len(biased)), key=lambda i: -biased[i])[:top_k]
    # softmax over ORIGINAL scores of the chosen experts
    chosen = [scores[i] for i in top_idx]
    m = max(chosen)
    exps = [math.exp(c - m) for c in chosen]
    s = sum(exps)
    gates = [e / s for e in exps]
    return top_idx, gates
```

偏置影响选择，不影响门控权重。这正是 DeepSeek-V3 的窍门——偏置纠正负载不均，却不左右模型的预测。

> Bias affects selection, not gate weight. That is the DeepSeek-V3 trick — bias corrects load imbalance without steering the model's predictions.

### Step 2: run 100 tokens through the router · 第 2 步：让 100 个 token 过一遍路由器

统计每个专家被触发的频率。不加偏置时，使用量是偏斜的；加上偏置更新循环（过度使用的专家 `-γ`，使用不足的 `+γ`），几轮迭代后使用量就收敛到均匀分布。

> Track which experts fire how often. Without the bias, usage is skewed. With a bias update loop (`-γ` for over-used experts, `+γ` for under-used), usage converges to a uniform distribution over a few iterations.

### Step 3: param count comparison · 第 3 步：参数量对比

打印一个 MoE 配置的「稠密等价物」。DeepSeek-V3 形态：256 路由 + 1 共享，8 个激活，d_model=7168。总参数量大得吓人；激活量只有稠密 Llama 3 70B 的七分之一。

> Print the "dense equivalent" of an MoE config. DeepSeek-V3-shaped: 256 routed + 1 shared, 8 active, d_model=7168. The total parameter count is eye-watering. The active count is a seventh of a dense Llama 3 70B.

## Use It · 实战用法

HuggingFace 加载：

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained("mistralai/Mixtral-8x22B-v0.1")
```

2026 年的生产推理：vLLM 原生支持 MoE 路由；SGLang 拥有最快的专家并行路径。两者都会自动处理 top-k 选择和专家并行。

**什么时候选 MoE：**

- 你想要前沿质量，同时压低每 token 推理成本。
- 你有显存 / 专家并行的基础设施。
- 你的负载是 token 密集型（聊天、代码），不是上下文密集型（长文档）。

**什么时候不要选 MoE：**

- 边缘部署——不管激活多少 FLOP，你都要为全部存储买单。
- 延迟敏感的单用户服务——专家路由有额外开销。
- 小模型（<7B）——MoE 的质量优势只在算力阈值（约 6B 激活参数）之上才出现。

> **When to pick MoE:** You want frontier quality at lower inference cost per token. You have the VRAM / expert-parallel infrastructure. Your workload is token-heavy (chat, code) not context-heavy (long docs).
> **When NOT to pick MoE:** Edge deployment — you pay full storage for any active FLOP. Latency-critical single-user serving — expert routing adds overhead. Small models (<7B) — MoE's quality advantage only appears above a compute threshold (~6B active params).

## Ship It · 交付

见 `outputs/skill-moe-configurator.md`。这个技能在给定参数预算、训练 token 数和部署目标的前提下，为一个新 MoE 挑选 E、k 和共享专家布局。

> See `outputs/skill-moe-configurator.md`. The skill picks E, k, and shared-expert layout for a new MoE given parameter budget, training tokens, and deployment target.

## Exercises · 练习

1. **简单。** 跑 `code/main.py`。观察无辅助损失的偏置更新如何在 50 轮迭代内把专家使用量拉平。
2. **中等。** 把可学习路由器换成基于哈希的路由器（确定性、无学习）。对比质量与均衡度。为什么可学习路由器更好？
3. **困难。** 实现 GRPO 风格的「rollout 匹配路由」（DeepSeek-V3.2 窍门）：记录推理时哪些专家被触发，在梯度计算时强制同样的路由。在一个玩具策略梯度设置上测量效果。

> 1. **Easy.** Run `code/main.py`. Watch how the auxiliary-loss-free bias update evens out expert usage over 50 iterations.
> 2. **Medium.** Replace the learned router with a hash-based router (deterministic, no learning). Compare quality and balance. Why is the learned router better?
> 3. **Hard.** Implement GRPO-style "rollout-matched routing" (DeepSeek-V3.2 trick): log which experts fire during inference, force the same routing during gradient computation. Measure the effect on a toy policy-gradient setup.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Expert（专家） | 「众多 FFN 之一」 | 一个独立的前馈网络；其参数专门服务 FFN 计算的一个稀疏切片。 |
| Router（路由器） | 「那道闸门」 | 一个极小的线性层，为每个 token 对每个专家打分；做 top-k 选择。 |
| Top-k routing（top-k 路由） | 「每 token 激活 k 个专家」 | 每个 token 的 FFN 计算恰好经过 k 个专家，按门控加权。 |
| Auxiliary loss（辅助损失） | 「负载均衡惩罚」 | 惩罚专家使用偏斜的额外损失项。 |
| Auxiliary-loss-free（无辅助损失） | 「DeepSeek-V3 的窍门」 | 只通过路由器选择上的逐专家偏置来均衡；不产生额外梯度。 |
| Shared expert（共享专家） | 「永远在线」 | 每个 token 都要经过的额外专家；捕获共性知识。 |
| Expert parallelism（专家并行） | 「按专家分片」 | 把不同专家分发到不同 GPU；token 跨网络路由。 |
| Sparsity（稀疏度） | 「激活参数 < 总参数」 | 比值 `k × expert_size / (E × expert_size)`；DeepSeek-V3 为 37/671 ≈ 5.5%。 |

## Further Reading · 延伸阅读

- [Shazeer et al. (2017). Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer](https://arxiv.org/abs/1701.06538) — 思想源头。
- [Fedus, Zoph, Shazeer (2022). Switch Transformer: Scaling to Trillion Parameter Models with Simple and Efficient Sparsity](https://arxiv.org/abs/2101.03961) — Switch，经典 MoE。
- [Jiang et al. (2024). Mixtral of Experts](https://arxiv.org/abs/2401.04088) — Mixtral 8×7B。
- [DeepSeek-AI (2024). DeepSeek-V3 Technical Report](https://arxiv.org/abs/2412.19437) — MLA + 无辅助损失 MoE + MTP。
- [Wang et al. (2024). Auxiliary-Loss-Free Load Balancing Strategy for Mixture-of-Experts](https://arxiv.org/abs/2408.15664) — 基于偏置的均衡论文。
- [Dai et al. (2024). DeepSeekMoE: Towards Ultimate Expert Specialization in Mixture-of-Experts Language Models](https://arxiv.org/abs/2401.06066) — 本课路由器使用的细粒度 + 共享专家拆分。
- [Kim et al. (2022). DeepSpeed-MoE: Advancing Mixture-of-Experts Inference and Training](https://arxiv.org/abs/2201.05596) — 共享专家概念的原始论文。
