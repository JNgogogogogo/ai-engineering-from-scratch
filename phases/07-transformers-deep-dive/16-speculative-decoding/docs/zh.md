# Speculative Decoding — Draft, Verify, Repeat · 投机解码 —— 起草、验证、重复（草稿写 N 个，大模型一次验完）

> Autoregressive decoding is serial. Each token waits for the previous one. Speculative decoding breaks the chain: a cheap model drafts N tokens, the expensive model verifies all N in one forward pass. When the draft is right you paid one big forward for N generations.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 7 · 07（GPT 因果语言模型）、Phase 7 · 12（KV Cache 与 Flash Attention）
**Time:** ~60 分钟

## The Problem · 问题在哪

一个 70B 的 LLM 在 H100 上采样一个 token 约 30 ms；一个 3B 草稿模型约 3 ms。如果让 3B 模型往前起草 5 个 token，然后让 70B 跑*一次*把 5 个全部验证，总共 `5×3 + 30 = 45 ms` 换最多 5 个被接受的 token —— 而直线生成要 `5×30 = 150 ms`。这就是投机解码（speculative decoding）的全部卖点：用少量额外的 GPU 显存（草稿模型）换 2–4 倍更低的解码延迟。

这个技巧必须保持分布不变。投机采样（speculative sampling）由 Leviathan 等人（2023）与 Chen 等人同期独立提出，它保证输出序列与大模型自己采样得到的序列**完全同分布**。没有质量代价，只有速度。

2026 年的推理格局由四类 draft-verifier 组合主导：

1. **原味投机（vanilla speculative，Leviathan 2023）。** 独立的草稿模型（如 Llama 3 1B）+ 验证器（如 Llama 3 70B）。
2. **Medusa（Cai 2024）。** 在验证器上挂多个解码头，并行预测 `t+1..t+k` 位。不需要单独的草稿模型。
3. **EAGLE 家族（Li 2024, 2025）。** 轻量草稿复用验证器的隐藏状态；接受率比原味高；典型 3–4 倍。
4. **Lookahead 解码（Fu 2024）。** Jacobi 迭代；完全不需要草稿模型。自我投机。小众但零依赖。

2026 年每个生产级推理栈都默认带投机解码。vLLM、TensorRT-LLM、SGLang 和 llama.cpp 至少都支持原味 + EAGLE-2。

> A 70B LLM sampling one token takes ~30 ms on an H100. A 3B draft model takes ~3 ms. ... That is the full speculative-decoding pitch: trade a small amount of extra GPU memory (draft model) for 2–4× lower decode latency.
> The trick has to preserve the distribution. Speculative sampling, introduced by Leviathan et al. (2023) and by Chen et al. concurrently, guarantees that the output sequence is **identically distributed** to what the big model would have produced on its own. No quality tradeoff. Just faster.
> Every production inference stack in 2026 ships speculative decoding by default. vLLM, TensorRT-LLM, SGLang, and llama.cpp all support at least vanilla + EAGLE-2.

## The Concept · 概念

### The core algorithm · 核心算法

给定验证器 `M_q` 和更便宜的草稿模型 `M_p`：

1. 设 `x_1..x_k` 是已经解码出的前缀。
2. **起草（Draft）**：用 `M_p` 自回归地提出 `d_{k+1}, d_{k+2}, ..., d_{k+N}`，草稿概率为 `p_1..p_N`。
3. **并行验证（Verify in parallel）**：把 `x_1..x_k, d_{k+1}, ..., d_{k+N}` 喂给 `M_q` 跑一次，得到位置 `k+1..k+N+1` 上的验证器概率 `q_1..q_{N+1}`。
4. **从左到右逐个接受/拒绝草稿 token**：对每个 `i`，以概率 `min(1, q_i(d_i) / p_i(d_i))` 接受。
5. 在位置 `j` 首次拒绝时：从归一化的「残差」分布 `(q_j - p_j)_+` 中采出 `t_j`。`j` 之后的所有草稿全部丢弃。
6. 若 `N` 个全部接受：从 `q_{N+1}` 再多采一个 token `t_{N+1}`（白送的奖励 token）。

残差分布这个技巧，正是保住「输出分布与 `M_q` 从头采样完全一致」的数学关键。

> Given a verifier `M_q` and a cheaper draft `M_p`: ... **Draft**: use `M_p` to autoregressively propose `d_{k+1}, d_{k+2}, ..., d_{k+N}` with draft probabilities `p_1..p_N`. ... **Verify in parallel**: run `M_q` once on `x_1..x_k, d_{k+1}, ..., d_{k+N}`, getting verifier probabilities `q_1..q_{N+1}` for positions `k+1..k+N+1`. ... **Accept/reject each draft token left to right**: for each `i`, accept with probability `min(1, q_i(d_i) / p_i(d_i))`. ... The residual distribution trick is the mathematical insight that keeps the output distributed exactly as if `M_q` had sampled from scratch.

### What determines speedup · 什么决定加速比

设 `α` = 每个草稿 token 的期望接受率，`c` = 草稿与验证器的成本比。每一步：

- 朴素生成每个 token 要 1 次大模型调用。
- 投机解码在 `α` 高时，每 `(1 - α^{N+1}) / (1 - α) ≈ 1/(1-α)` 个 token 才要 1 次大模型调用。

`α = 0.75`、`N = 5` 时的典型经验值：大模型调用减少 3 倍。草稿成本便宜 5 倍。总墙钟时间约降 2.5 倍。

**α 取决于：**

- 草稿对验证器的近似程度。同家族 / 同训练数据能显著提升 α。
- 解码策略。贪心草稿对贪心验证器：α 高。温度采样：更难匹配；接受率下降。
- 任务类型。代码和结构化输出接受率高（可预测）；自由创意写作接受率低。

> Let `α` = expected acceptance rate per draft token. Let `c` = draft-to-verifier cost ratio. Per step:
> Naive generation makes 1 big-model call per token.
> Speculative makes 1 big-model call per `(1 - α^{N+1}) / (1 - α) ≈ 1/(1-α)` tokens when `α` is high.
> Typical rule of thumb at `α = 0.75` and `N = 5`: 3× fewer big-model calls. Draft cost is 5× cheap. Total wall-clock drops ~2.5×.
> **α depends on:**
> How well the draft approximates the verifier. Same family / same training data boosts α significantly.
> Decoding strategy. Greedy draft against greedy verifier: high α. Temperature sampling: harder to match; acceptance drops.
> Task type. Code and structured output accept more (predictable); free-form creative writing accepts less.

### Medusa — drafts without a draft model · Medusa：不要草稿模型的草稿

Medusa 用验证器上的额外输出头取代草稿模型。在位置 `t`：

```
shared trunk → hidden h_t
    ├── head_0: predict token at t+1  (standard LM head)
    ├── head_1: predict token at t+2
    ├── head_2: predict token at t+3
    ├── head_3: predict token at t+4
```

每个头输出自己的 logits。推理时从每个头采样得到候选序列，然后用 tree-attention 方案一次前向完成验证，同时考虑所有候选延续。

优点：不用第二个模型。缺点：增加可训练参数；需要一轮监督微调（约 1B token）；接受率比「原味投机 + 好草稿」略低。

> Medusa replaces the draft model with extra output heads on the verifier. At position `t`:
> Each head outputs its own logits. At inference you sample from each head to get a candidate sequence, then verify with one forward pass using a tree-attention scheme that considers all candidate continuations at once.
> Pros: no second model. Cons: adds trainable parameters; needs a supervised fine-tuning stage (~1B tokens); acceptance rate is a bit lower than vanilla speculative with a good draft.

### EAGLE — better draft by reusing hidden states · EAGLE：复用隐藏状态得到更好的草稿

EAGLE-1/2/3（Li et al., 2024–2025）把草稿模型做成一个微型 transformer（通常 1 层），它吃进验证器最后一层的隐藏状态。因为草稿看到了验证器的特征表示，它的预测与验证器的输出分布强相关。接受率从 ~0.6（原味）爬到 0.85+。

EAGLE-3（2025）加上了候选延续之上的树搜索。vLLM 和 SGLang 把 EAGLE-2/3 作为 Llama 3/4 和 Qwen 3 的默认投机路径。

> EAGLE-1/2/3 (Li et al., 2024–2025) makes the draft model a tiny transformer (typically 1 layer) that ingests the verifier's last-layer hidden states. Because the draft sees the verifier's feature representation, its predictions correlate strongly with the verifier's output distribution. Acceptance rates climb from ~0.6 (vanilla) to 0.85+.
> EAGLE-3 (2025) added tree search over candidate continuations. vLLM and SGLang ship EAGLE-2/3 as the default spec pathway for Llama 3/4 and Qwen 3.

### The KV cache dance · KV cache 的回滚之舞

验证会一次前向把 `N` 个草稿 token 喂进验证器。这会把验证器的 KV cache 扩展 `N` 条。如果有些草稿被拒绝，你必须把 cache 回滚到被接受前缀的长度。

生产实现（vLLM 的 `--speculative-config`、TensorRT-LLM 的 LookaheadDecoder）用暂存 KV 缓冲区处理这件事：先写入，接受后才提交。概念上不难，但很琐碎。

> Verification feeds `N` draft tokens into the verifier in one forward pass. This extends the verifier's KV cache by `N` entries. If some drafts are rejected, you must roll the cache back to the accepted prefix length.
> Production implementations (vLLM's `--speculative-config`, TensorRT-LLM's LookaheadDecoder) handle this with scratch KV buffers. Write first, commit on acceptance. It's not conceptually hard, but it is fiddly.

```figure
draft-verify-tokens
```

## Build It · 动手造

见 `code/main.py`。我们实现核心的投机采样算法（拒绝步 + 残差分布），其中：

- 「大模型」是对一个手写分布做的确定性 softmax（这样我们可以解析地验证接受数学）。
- 「草稿模型」是大模型的一个扰动版。
- 一个接受/拒绝循环，产生的边缘分布与直接采样完全相同。

> See `code/main.py`. We implement the core speculative-sampling algorithm (rejection step + residual distribution) with:
> A "big model" that is a deterministic-softmax over a hand-coded distribution (so we can verify acceptance math analytically).
> A "draft model" that is a perturbation of the big model.
> An acceptance / rejection loop that produces the same marginal distribution as direct sampling.

### Step 1: the rejection step · 拒绝步

```python
def accept_or_reject(q_prob, p_prob, draft_token, u):
    ratio = q_prob / p_prob if p_prob > 0 else float("inf")
    return u < min(1.0, ratio)
```

`u` 是均匀随机数。`q_prob` 是验证器给草稿 token 的概率，`p_prob` 是草稿模型的概率。Leviathan 定理说的是：这个伯努利决策，加上拒绝时从残差分布采样，能精确保持验证器的分布。

> `u` is a uniform random number. `q_prob` is the verifier's probability for the drafted token. `p_prob` is the draft model's probability. The Leviathan theorem is that this Bernoulli decision, followed by sampling from the residual on rejection, preserves the verifier's distribution exactly.

### Step 2: residual distribution · 残差分布

```python
def residual_dist(q, p):
    raw = [max(0.0, qi - pi) for qi, pi in zip(q, p)]
    s = sum(raw)
    return [r / s for r in raw]
```

`q` 逐元素减 `p`，负值截为 0，重新归一化。任何一次拒绝时都从这个分布采样。

> Subtract `p` from `q` element-wise, clamp negative values to zero, renormalize. Sample from this on any rejection.

### Step 3: one speculative step · 一次投机步

```python
def spec_step(prefix, q_model, p_model, N, rng):
    drafts = []
    p_probs = []
    ctx = list(prefix)
    for _ in range(N):
        p_dist = p_model(ctx)
        d = sample(p_dist, rng)
        drafts.append(d)
        p_probs.append(p_dist[d])
        ctx.append(d)

    q_dists = [q_model(prefix + drafts[:i]) for i in range(N + 1)]

    for i, d in enumerate(drafts):
        u = rng.random()
        q_prob = q_dists[i][d]
        p_prob = p_probs[i]
        if u < min(1.0, q_prob / p_prob if p_prob > 0 else float("inf")):
            prefix = prefix + [d]
        else:
            res = residual_dist(q_dists[i], p_model(prefix))
            prefix = prefix + [sample(res, rng)]
            return prefix
    prefix = prefix + [sample(q_dists[N], rng)]
    return prefix
```

5 个被接受 → 1 个奖励 → 一次验证器前向产出 6 个 token。

> Five accepted → one bonus → six tokens produced in one verifier pass.

### Step 4: measure acceptance rate · 测量接受率

在不同的草稿质量水平下跑 10,000 次投机步。画出接受率对草稿与验证器分布之间 KL 散度的关系。你应该会看到一条干净的单调曲线。

> Run 10,000 speculative steps at varying draft-quality levels. Plot acceptance rate vs. KL divergence between draft and verifier distributions. You should see a clean monotone relationship.

### Step 5: verify distribution equivalence · 验证分布等价

实证做法：投机循环产出的 token 直方图，应当与直接从验证器采样得到的直方图吻合。这就是 Leviathan 定理的实践版。卡方检验会在采样误差范围内确认这一点。

> Empirically: the histogram of tokens produced by the speculative loop should match the histogram produced by sampling directly from the verifier. This is the Leviathan theorem in practice. A chi-square test confirms within sampling error.

## Use It · 实战用法

生产环境：

```bash
# vLLM with EAGLE
vllm serve meta-llama/Llama-3.1-70B-Instruct \
    --speculative-config '{"method": "eagle", "model": "/models/llama-3.1-eagle-70b", "draft_tensor_parallel_size": 1, "num_speculative_tokens": 5}'

# vLLM with vanilla draft model
vllm serve meta-llama/Llama-3.1-70B-Instruct \
    --speculative-config '{"method": "draft_model", "model": "meta-llama/Llama-3.2-1B-Instruct", "num_speculative_tokens": 5}'
```

截至 2026 年年中，TensorRT-LLM 拥有最快的 Medusa 路径。`faster-whisper` 用一个小草稿为 Whisper-large 包了一层投机解码。

**草稿怎么选：**

| 策略 | 何时选 | 加速比 |
|----------|--------------|---------|
| 原味草稿（1B/3B Llama 家族） | 快速原型，无需训练 | 1.8–2.3× |
| Medusa 头 | 你能微调验证器 | 2–3× |
| EAGLE-2 / 3 | 生产环境，追求极限速度 | 3–4× |
| Lookahead | 无草稿、无训练、无额外参数 | 1.3–1.6× |

> TensorRT-LLM has the fastest Medusa path as of mid-2026. `faster-whisper` wraps speculative decoding for Whisper-large with a small draft.
> **Picking a draft:**
> | Strategy | When to pick | Speedup |
> |----------|--------------|---------|
> | Vanilla draft (1B/3B Llama family) | Fast prototype, no training | 1.8–2.3× |
> | Medusa heads | You can fine-tune the verifier | 2–3× |
> | EAGLE-2 / 3 | Production, max speed | 3–4× |
> | Lookahead | No draft, no training, no extra params | 1.3–1.6× |

**什么时候别用投机解码：**

- 只有 1–5 个 token 的单序列生成。开销占主导。
- 高度发散的创意 / 高温度采样（α 下降）。
- 内存受限的部署（草稿模型要加显存）。

> **When NOT to spec-decode:**
> Single-sequence generation of 1–5 tokens. Overhead dominates.
> Wildly creative / high-temperature sampling (α drops).
> Memory-constrained deployments (draft model adds VRAM).

## Ship It · 交付

见 `outputs/skill-spec-decode-picker.md`。这个技能（skill）为新的推理负载挑选投机解码策略（原味 / Medusa / EAGLE / lookahead）及调优参数（N、草稿温度）。

> See `outputs/skill-spec-decode-picker.md`. The skill picks a speculative decoding strategy (vanilla / Medusa / EAGLE / lookahead) and tuning parameters (N, draft temperature) for a new inference workload.

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。在 50,000 个 token 上确认投机 token 分布与验证器直接采样的分布一致（卡方 p > 0.05）。
2. **中等。** 对 `α = 0.5, 0.7, 0.85` 画出加速比（每次大模型前向产出的 token 数）随 `N` 变化的曲线。找出每个 α 的最优 `N`。（提示：每次验证调用期望产出的 token 数 = `(1 - α^{N+1}) / (1 - α)`。）
3. **困难。** 实现一个迷你 Medusa：拿第 14 课的 capstone GPT，加 3 个额外 LM 头，分别预测 t+2、t+3、t+4 位。用联合多头损失在 tinyshakespeare 上训练。与「截断同一模型得到的原味草稿」比较接受率。
4. **困难。** 实现回滚：从一个 10 token 的前缀 KV cache 出发，喂入 5 个草稿 token，模拟在位置 3 被拒绝。验证下一轮迭代时你的 cache 读取正确匹配「前缀 + 前 2 个被接受的草稿」。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Draft model | 「便宜的那个」 | 提出候选 token 的较小模型；通常比验证器便宜 10–50 倍。 |
| Verifier | 「大的那个」 | 我们要保其分布的目标模型；每个投机步只跑一次。 |
| Acceptance rate (α) | 「草稿猜中的频率」 | 验证器接受草稿的每 token 概率。典型 0.7–0.9。 |
| Residual distribution | 「拒绝时的兜底」 | 归一化的 `(q - p)_+`；拒绝时从这里采样可保持验证器的分布。 |
| Bonus token | 「白送的那个」 | N 个草稿全被接受时，从验证器的下一步分布再多采一个。 |
| Medusa | 「无草稿投机」 | 验证器上的多个 LM 头并行预测 t+1..t+k 位。 |
| EAGLE | 「隐藏状态草稿」 | 以验证器最后一层隐藏状态为条件的微型 transformer 草稿。 |
| Lookahead decoding | 「Jacobi 迭代」 | 用不动点迭代自我投机；无需草稿模型。 |
| Tree attention | 「一次验多个候选」 | 分支式验证，同时考虑多条草稿延续。 |
| KV rollback | 「撤销被拒草稿」 | 暂存 KV 缓冲区；接受才提交，拒绝即丢弃。 |

## Further Reading · 延伸阅读

- [Leviathan, Kalman, Matias (2023). Fast Inference from Transformers via Speculative Decoding](https://arxiv.org/abs/2211.17192) —— 核心算法与等价性定理。
- [Chen et al. (2023). Accelerating Large Language Model Decoding with Speculative Sampling](https://arxiv.org/abs/2302.01318) —— 同期独立提出；干净的伯努利拒绝证明。
- [Cai et al. (2024). Medusa: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads](https://arxiv.org/abs/2401.10774) —— Medusa 论文；tree-attention 验证。
- [Li et al. (2024). EAGLE: Speculative Sampling Requires Rethinking Feature Uncertainty](https://arxiv.org/abs/2401.15077) —— EAGLE-1；以隐藏状态为条件的草稿。
- [Li et al. (2024). EAGLE-2: Faster Inference of Language Models with Dynamic Draft Trees](https://arxiv.org/abs/2406.16858) —— EAGLE-2；动态树深度。
- [Li et al. (2025). EAGLE-3: Scaling up Inference Acceleration of Large Language Models via Training-Time Test](https://arxiv.org/abs/2503.01840) —— EAGLE-3。
- [Fu et al. (2024). Break the Sequential Dependency of LLM Inference Using Lookahead Decoding](https://arxiv.org/abs/2402.02057) —— lookahead 的无草稿方案。
- [vLLM docs — Speculative Decoding](https://docs.vllm.ai/en/latest/features/spec_decode.html) —— 接好全部四种策略的权威生产参考。
- [SafeAILab / EAGLE reference implementation](https://github.com/SafeAILab/EAGLE) —— EAGLE-1/2/3 的参考实现。
