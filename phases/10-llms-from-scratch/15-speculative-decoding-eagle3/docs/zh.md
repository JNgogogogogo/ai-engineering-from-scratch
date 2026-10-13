# Speculative Decoding and EAGLE-3 · 投机解码与 EAGLE-3

> Phase 7 · 第 16 课已经证明了数学：Leviathan 拒绝规则能精确保持验证器（verifier）的分布。本课是 2026 年生产级投机解码（speculative decoding）的训练栈视角。EAGLE-3 把草稿模型（draft model）从一个廉价的近似物，变成了一个专门构建的小网络——在验证器自己的隐藏态上训练，然后加入一个训练时测试（training-time test）环节来对齐它的训练分布和推理分布。结果：3× 到 6.5× 的端到端加速，聊天场景每 token 接受率超过 0.9，没有任何分布上的妥协。2026 年每一条生产推理栈都默认搭载它。

> Phase 7 · Lesson 16 proved the math: the Leviathan rejection rule preserves the verifier's distribution exactly. This lesson is the training-stack view of 2026 production speculative decoding. EAGLE-3 turned the draft model from a cheap approximation into a purpose-built tiny network trained on the verifier's own hidden states, then added a training-time test loop that aligns its train and inference distributions. Result: 3× to 6.5× end-to-end speedup, accepted per-token rates above 0.9 on chat, no distributional tradeoff. Every production inference stack in 2026 ships it by default.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 7 · 16 (speculative decoding math), Phase 10 · 12 (inference optimization)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 用一句话陈述 Leviathan 定理，并证明投机循环产出的样本与验证器同分布。
- 走完从原味投机解码（Leviathan 2023）到 EAGLE、EAGLE-2、EAGLE-3 的两年演进，说出每一步具体移除了什么限制。
- 由接受率 `α` 和草稿与验证器的成本比 `c` 计算期望加速比，并为每种场景选出最优草稿长度 `N`。
- 从零实现完整的投机循环：起草、验证、从残差分布做拒绝采样、拒绝时回滚 KV cache、全部接受时发出奖励 token（bonus token）。

> State the Leviathan theorem in one sentence and prove that the speculative loop produces samples identically distributed to the verifier.
> Walk the two-year progression from vanilla spec-decoding (Leviathan 2023) through EAGLE, EAGLE-2, and EAGLE-3 and name the exact limitation each step removed.
> Compute expected speedup from acceptance rate `α` and draft-to-verifier cost ratio `c`, and choose the optimal draft length `N` for each regime.
> Implement the full speculative loop from scratch: draft, verify, reject-sample from the residual, roll the KV cache back on rejection, emit the bonus token on full acceptance.

## The Problem · 问题在哪

70B 模型的自回归解码在 H100 上大概只能跑 35 token/秒。GPU 远没吃饱。天花板是内存带宽：每个 token 都要从 HBM 加载 70B 权重、做一步算术、产出一个浮点数。计算单元大半时间在闲置。

投机解码把它变成一个你真能解决的吞吐问题。一个便宜的草稿模型用 N 次小前向提出 `N` 个 token。验证器对「前缀 + 全部 N 个草稿」只跑一次前向。如果验证器在位置 `i` 的分布与草稿一致（按一个我们马上会讲清楚的统计意义），就接受；不一致就拒绝，并从残差分布（residual distribution）采样一个修正。一次大模型前向最多产出 `N+1` 个被接受的 token，而不是 1 个。

关键定理是 Leviathan, Kalman, Matias（ICML 2023）：输出分布与「直接从验证器采样」会得到的分布完全相同。不是近似。是完全相同。这就是投机解码能在生产中立足的全部理由——它是一个没有质量妥协的纯延迟优化。

Phase 7 · 第 16 课给你的是数学。本课给你的是训练栈。一个好草稿比一个便宜草稿多值 2 倍加速。EAGLE、EAGLE-2 和 EAGLE-3（Li et al., 2024–2025）把「草稿 = 同一模型的缩小版」变成了一门精确的工程学科。2026 年的生产推理服务器默认 EAGLE-3。

> Autoregressive decoding on a 70B model runs at maybe 35 tokens per second on an H100. The GPU is nowhere near saturated. Memory bandwidth is the ceiling: every token loads 70B of weights from HBM, does one step of arithmetic, and produces one float. The compute units sit mostly idle.
> Speculative decoding turns that into a throughput problem you can actually solve. ... A single big-model forward produces up to `N+1` accepted tokens instead of one.
> The theorem that matters is Leviathan, Kalman, Matias (ICML 2023): the output distribution is identical to what sampling from the verifier directly would have produced. Not approximately. Identically. This is the entire reason speculative decoding is acceptable in production — it is a pure latency optimization with no quality tradeoff.
> What Phase 7 · Lesson 16 gave you was the math. What this lesson gives you is the training stack. A good draft is worth 2× more speedup than a cheap draft. ... 2026 production inference servers default to EAGLE-3.

## The Concept · 概念

### The invariant: Leviathan rejection sampling · 不变量：Leviathan 拒绝采样

设 `p(t)` 为草稿在给定某前缀下对下一个 token 的分布，`q(t)` 为验证器的分布。采样一个草稿 token `d ~ p`。以概率 `min(1, q(d) / p(d))` 接受。拒绝时，从残差分布 `(q - p)_+ / ||(q - p)_+||_1` 采样。得到的样本服从 `q`。这与 `p` 有多差无关——`p` 越差，你拒绝得越频繁，但输出依然精确。

把 N 次这样的调用背靠背堆起来，验证器对 `prefix + d_1 + ... + d_N` 只做一次前向，同时返回 `q_1, q_2, ..., q_{N+1}`。从左到右走。在位置 `j` 第一次拒绝时，从 `residual(q_j, p_j)` 采样并停止。全部接受时，从 `q_{N+1}` 再采样一个奖励 token。

> Let `p(t)` be the draft's distribution for the next token given some prefix, and `q(t)` be the verifier's. Sample a draft token `d ~ p`. Accept with probability `min(1, q(d) / p(d))`. On reject, sample from the residual distribution `(q - p)_+ / ||(q - p)_+||_1`. The resulting samples are distributed according to `q`. This is true regardless of how bad `p` is — the worse it is, the more often you reject, but the output remains exact.
> Stack `N` of these calls back to back using one verifier forward pass on `prefix + d_1 + ... + d_N`. The verifier returns `q_1, q_2, ..., q_{N+1}` simultaneously. Walk left to right. On the first rejection at position `j`, sample from `residual(q_j, p_j)` and stop. On full acceptance, sample one bonus token from `q_{N+1}`.

### What determines speedup · 什么决定加速比

设 `α` 为每个被起草 token 的期望接受率，`c = cost(draft) / cost(verifier)` 为成本比。每次验证器前向的期望接受 token 数为：

```
E[accepted] = (1 - α^(N+1)) / (1 - α)
```

每个接受 token 的期望总耗时是 `(N * c + 1) / E[accepted]`。对 `N` 求最小值，就得到最优点。`α = 0.8, c = 0.05` 时：最优 `N` 在 5–7 左右，加速比 3.2×。`α = 0.95, c = 0.02` 时：最优 `N` 在 8–10 左右，加速比逼近 5×。

最大的单一杠杆是 `α`。固定 `N = 5`，从 `α = 0.6`（原味草稿）提升到 `α = 0.9`（EAGLE-3），每次验证器前向的期望接受 token 从 2.2 涨到 4.1。同一台验证器，吞吐接近翻倍。

> Let `α` be the expected acceptance rate per drafted token. Let `c = cost(draft) / cost(verifier)` be the cost ratio. The expected number of accepted tokens per verifier forward is:
> The expected total wall time per accepted token is `(N * c + 1) / E[accepted]`. Minimize that with respect to `N` and you get the sweet spot. For `α = 0.8, c = 0.05`: optimal `N` is around 5–7, speedup is 3.2×. For `α = 0.95, c = 0.02`: optimal `N` is around 8–10, speedup pushes 5×.
> The single biggest lever is `α`. Going from `α = 0.6` (vanilla draft) to `α = 0.9` (EAGLE-3) at fixed `N = 5` takes you from 2.2 expected accepted tokens per verifier forward to 4.1. Nearly 2× more throughput from the same verifier.

### The two-year progression · 两年演进

**原味投机解码（Leviathan，2023）。** 草稿模型是同家族独立训练的更小 LLM。接线容易，`α ≈ 0.6`，加速比最好也就 2× 左右。

**EAGLE-1（Li et al., 2024）。** 草稿是一个微型 transformer——通常一两层——它以验证器最后一层的隐藏态为输入，直接预测下一个 token。因为草稿看到的是验证器的特征表示，它的分布离验证器近得多。`α` 爬升到 0.7–0.8。

**EAGLE-2（Li et al., 2024）。** 加入动态草稿树：不再提出单一一条 `N` 个 token 的序列，而是提出一棵小的候选树，用验证器一次前向给每个候选打分（tree attention），然后走概率最高的路径。草稿长度变成每步自适应。每条被接受路径上的 `α` 爬到 0.85 以上。

**EAGLE-3（Li et al., 2025, NeurIPS）。** 又改了两处。第一，完全去掉特征预测损失——EAGLE-1/2 训练草稿去匹配验证器的隐藏态，这限制了数据能带来的收益；EAGLE-3 直接用 token 预测来训练。第二，训练时测试（training-time test，TTT）：在草稿训练期间，把草稿自己之前的预测在多步中喂回作为输入，与它在推理时的运作方式完全一致。这让训练分布和测试分布对齐，阻止了误差累积。实测加速比：聊天最高 6.5×，在 H100 上 SGLang batch 64 时吞吐提升 38%。

> **Vanilla speculative (Leviathan, 2023).** Draft model is an independently trained smaller LLM from the same family. Easy to wire up, `α ≈ 0.6`, speedup around 2× at best.
> **EAGLE-1 (Li et al., 2024).** Draft is a tiny transformer — typically one or two layers — that takes the verifier's last-layer hidden state as input and predicts the next token directly. Because the draft sees the verifier's feature representation, its distribution is much closer to the verifier's. `α` climbs to 0.7–0.8.
> **EAGLE-2 (Li et al., 2024).** Adds a dynamic draft tree: instead of proposing a single sequence of `N` tokens, propose a small tree of candidates, score each with the verifier in one forward pass (tree attention), and walk the highest-probability path. Draft length becomes adaptive per step. `α` per accepted-path token climbs above 0.85.
> **EAGLE-3 (Li et al., 2025, NeurIPS).** Two more changes. First, drop the feature-prediction loss entirely ... Second, training-time test (TTT): during draft training, feed the draft's own previous predictions back as inputs over multiple steps, the same way it operates at inference. This aligns the train and test distributions and stops error accumulation. Measured speedup: up to 6.5× on chat, 38% throughput improvement at batch 64 in SGLang on H100.

### KV cache rollback · KV cache 回滚

验证过程会在一次前向里给验证器的 KV cache 追加 `N` 个条目。如果拒绝发生在位置 `j`，那么位置 `j-1` 之后的 cache 内容就错了。两种常见实现：写入一个临时缓冲区、接受时才提交（vLLM、TensorRT-LLM）；或者保留物理 KV cache 外加一个逻辑长度，拒绝时截断。无论哪种，回滚成本都是每层每头若干字节的搬运，与前向成本相比可以忽略。

对 EAGLE-2 的树搜索，验证器用一个尊重树拓扑的非因果掩码跑注意力。工程上有点琐碎，但计算本身是一次带自定义掩码的标准 flash-attention 调用。

> Verification extends the verifier's KV cache by `N` entries in one pass. If rejection happens at position `j`, the cache contents past position `j-1` are now wrong. Two common implementations: write to a scratch buffer and commit on acceptance (vLLM, TensorRT-LLM), or keep a physical KV cache plus a logical length and truncate on reject. Either way, the rollback cost is bytes per layer per head, which is negligible next to the forward-pass cost.
> For EAGLE-2 tree search, the verifier runs attention with a non-causal mask that respects tree topology. The engineering is fiddly but the computation is a standard flash-attention call with a custom mask.

### Draft architectures in 2026 · 2026 年的草稿架构

| Strategy | Draft type | `α` | Speedup | Training cost |
|----------|-----------|-----|---------|---------------|
| Vanilla | 独立的小 LLM | 0.55-0.70 | 1.8-2.3× | 无（复用现成小模型） |
| Medusa | 验证器上加额外 LM 头 | 0.65-0.75 | 2-3× | ~1B SFT tokens |
| EAGLE-1 | 以隐藏态为输入的 1 层 transformer | 0.70-0.80 | 2.5-3× | ~60B tokens |
| EAGLE-2 | EAGLE-1 + 动态草稿树 | 0.80-0.88 | 3-4× | ~60B tokens |
| EAGLE-3 | 多层特征融合 + TTT | 0.88-0.92 | 3.5-6.5× | ~60-200B tokens |
| Lookahead | 无草稿（Jacobi 迭代） | N/A | 1.3-1.6× | 无 |

2026 年的生产现状：可用时 vLLM 和 SGLang 默认 EAGLE-3，否则 EAGLE-2。TensorRT-LLM 为 Meta 和 NVIDIA 的公开模型提供最快的 Medusa 路径。llama.cpp 为 CPU 部署内置了原味草稿。

```figure
l5-spec-decode-eagle
```

> In 2026 production: vLLM and SGLang default to EAGLE-3 when available, EAGLE-2 otherwise. TensorRT-LLM has the fastest Medusa path for Meta and NVIDIA public models. llama.cpp ships vanilla draft for CPU deployments.

## Build It · 动手造

完整实现见 `code/main.py`。这是带全套部件的 Leviathan 投机循环：起草 N 个、验证器并行前向、逐位置拒绝、残差采样、奖励 token、KV 回滚，以及「输出分布与直接从 `q` 采样一致」的经验验证。

> See `code/main.py`. This is the full Leviathan speculative loop with all the pieces: draft-of-N, verifier parallel pass, per-position rejection, residual sampling, bonus token, KV rollback, and empirical verification that the output distribution matches direct sampling from `q`.

### Step 1: the rejection rule · 第 1 步：拒绝规则

```python
def accept(q_prob, p_prob, u):
    if p_prob <= 0:
        return True
    return u < min(1.0, q_prob / p_prob)
```

### Step 2: residual distribution · 第 2 步：残差分布

```python
def residual(q, p):
    raw = [max(0.0, qi - pi) for qi, pi in zip(q, p)]
    s = sum(raw)
    if s == 0:
        return list(q)
    return [r / s for r in raw]
```

### Step 3: a full speculative step · 第 3 步：完整的投机步

`spec_step` 函数从 `p` 起草 `N` 个 token，然后在一次并行的 `q` 求值中验证全部草稿。对每个草稿 token 应用拒绝规则；第一次拒绝处，从残差分布采样修正。如果全部接受，就从 `q_{N+1}` 发出一个奖励 token。

> The `spec_step` function drafts `N` tokens from `p`, then verifies all of them in one parallel `q` evaluation. For each drafted token it applies the rejection rule, and on the first rejection it samples the correction from the residual. If everything accepts, it emits a bonus token from `q_{N+1}`.

### Step 4: KV rollback bookkeeping · 第 4 步：KV 回滚簿记

模拟器为每个 worker 追踪一个逻辑 `kv_length`。接受 `k` 个草稿时，`kv_length += k`。在位置 `j` 发生拒绝时，cache 已经写过了 `j`，但逻辑长度被设为 `prefix_length + j + 1`——即修正 token 的后一位。后续读取一律截断到逻辑长度。

> The simulator tracks a logical `kv_length` per worker. On acceptance of `k` drafts, `kv_length += k`. On a rejection at position `j`, the cache is already written past `j`, but the logical length is set to `prefix_length + j + 1` — one past the correction token. Subsequent reads truncate to the logical length.

### Step 5: the Leviathan check · 第 5 步：Leviathan 校验

跑 50,000 步投机循环，统计被接受 token 数的经验分布；再与 50,000 次从 `q` 的直接采样比较。卡方统计量应远低于临界值。定理在实践中成立。

> Run 50,000 speculative steps. Count the empirical distribution of accepted tokens. Compare to 50,000 direct samples from `q`. The chi-square statistic should be well under the critical value. The theorem passes in practice.

### Step 6: speedup vs. α · 第 6 步：加速比 vs. α

用不同幅度把 `p` 从 `q` 上扰动开来，扫描草稿质量。测量 `α`，然后画出「每次验证器调用的期望 token 数」随 `α` 和 `N` 变化的曲线。代码会打印一张表，展示 EAGLE-3 级别的草稿质量（`α ≈ 0.9`）如何把每次验证器调用的产出解锁到 4–5 个 token。

> Sweep the draft quality by perturbing `p` away from `q` at different amplitudes. Measure `α`, then plot expected tokens per verifier call as a function of `α` and `N`. The code prints a table showing how EAGLE-3-class draft quality (`α ≈ 0.9`) unlocks 4–5 tokens per verifier call.

## Use It · 实战用法

生产级 `vllm serve` 配 EAGLE-3：

```bash
vllm serve meta-llama/Llama-3.3-70B-Instruct \
  --speculative-config '{
    "model": "yuhuili/EAGLE3-LLaMA3.3-Instruct-70B",
    "num_speculative_tokens": 5,
    "method": "eagle3"
  }'
```

在 H100 上以 batch 64 运行 SGLang + EAGLE-3：按 EAGLE-3 论文的数据，吞吐比 batch-64 原味解码高约 1.38×。

什么时候该上投机解码：

- 任何 p50 延迟比峰值吞吐更重要的交互式聊天负载。
- 代码生成和结构化输出（JSON、SQL）。目标分布高度可预测，`α` 在 0.9 以上。
- 长文本生成（数千 token）。摊销后的加速持续兑现。

什么时候不该：

- 非常小的模型（< 3B）。草稿并不比验证器便宜多少。
- 批量为 1 的小型 CPU 部署。草稿模型的内存开销可能不划算。
- 温度极高的创造性采样，`α` 会崩掉。

> Production-level `vllm serve` with EAGLE-3:
> SGLang with EAGLE-3 at batch 64 on H100: roughly 1.38× more throughput than batch-64 vanilla decoding, per the EAGLE-3 paper.
> When to reach for speculative decoding:
> - Any interactive chat workload where p50 latency matters more than peak throughput.
> - Code generation and structured output (JSON, SQL). `α` is above 0.9 because the target distribution is highly predictable.
> - Long-form generation (thousands of tokens). The amortized speedup keeps paying.
> When not to:
> - Very small models (< 3B). The draft is not that much cheaper than the verifier.
> - Tiny batch-1 CPU deployments. Memory overhead of the draft model may not be worth it.
> - Very-high-temperature creative sampling where `α` collapses.

## Ship It · 交付

本课产出 `outputs/skill-eagle3-tuner.md`。给定一个推理负载（模型、批量大小、目标延迟、任务画像），它会推荐一套投机解码策略和调优参数（草稿模型家族、`N`、树深度、按温度切换）。

> This lesson produces `outputs/skill-eagle3-tuner.md`. Given an inference workload (model, batch size, target latency, task profile), it recommends a speculative-decoding strategy and tuning parameters (draft family, `N`, tree depth, temperature-aware switching).

## Exercises · 练习

1. 运行 `code/main.py`。确认 Leviathan 分布检查的卡方统计量在 50,000 个样本上保持在 95% 临界值以下。

2. 固定 `α = 0.9`、`c = 0.04`，把 `N` 从 1 扫到 10。画出每次验证器调用的期望 token 数和每 token 实际耗时。找出最小化耗时的 `N`，并解释曲线的形状。

3. 修改代码，模拟 EAGLE-2 树搜索：每一步草稿提出一棵形状为 `[2, 2, 2]` 的树（八条候选路径）。验证器只跑一次，概率最高的被接受路径胜出。计算每个叶子的 `α` 和每次验证器调用的总 token 数，并与同等计算量的线性链式投机解码比较。

4. 为两条并发序列实现一个批量 KV 回滚模拟器。序列 A 的草稿全部被接受；序列 B 在位置 2 被拒。展示每条序列的 `kv_length` 都被正确更新，且没有任何计算被浪费。

5. 阅读 EAGLE-3 论文第 4 节（Training-Time Test）。用两句话解释：为什么没有 TTT 的朴素草稿训练会受曝光偏差（exposure bias）之苦，以及为什么训练时把草稿自己的预测喂回给它能修复这个问题。把它与 seq2seq 中的 scheduled-sampling 文献联系起来。

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| Leviathan rule | "min(1, q over p)" | 以 `min(1, q(d)/p(d))` 的概率做伯努利接受/拒绝；拒绝时从残差分布采样，从而精确保持验证器分布 |
| Residual distribution | "(q minus p) plus, normalized" | `(q - p)_+` 在零处截断再重新归一化——拒绝时应当采样的正确分布 |
| Acceptance rate α | 「草稿多久对一次」 | 拒绝规则下每 token 的期望伯努利成功概率；所有加速比数学都由它决定 |
| EAGLE-1 | 「隐藏态草稿」 | 以验证器最后一层隐藏态为条件的小型 transformer 草稿（Li et al., 2024） |
| EAGLE-2 | 「动态草稿树」 | EAGLE-1 加一棵候选续写树，用 tree attention 在一次验证器前向中打分 |
| EAGLE-3 | 「训练时测试」 | 去掉特征预测损失，直接用 token 预测训练，并在训练时把草稿自己的输出喂回给它 |
| Training-time test (TTT) | 「曝光偏差修复」 | 训练时让草稿自回归地运行，使训练与测试的输入分布一致——scheduled sampling 的直接类比 |
| KV rollback | 「撤销被拒草稿」 | 拒绝发生后，把验证器 KV cache 重置到已接受前缀长度的簿记操作 |
| Bonus token | 「白送的那个」 | 全部 `N` 个草稿都接受时，从 `q_{N+1}` 免费再采样一个额外 token，无需额外的验证器开销 |
| Tree attention | 「一次验证多个候选」 | 使用尊重草稿树拓扑的非因果掩码的注意力；一次前向算出树中每个节点的 `q_i` |

## Further Reading · 延伸阅读

- [Leviathan, Kalman, Matias — Fast Inference from Transformers via Speculative Decoding (arXiv:2211.17192, ICML 2023)](https://arxiv.org/abs/2211.17192) —— 奠基论文与等价性定理
- [Chen et al. — Accelerating Large Language Model Decoding with Speculative Sampling (arXiv:2302.01318)](https://arxiv.org/abs/2302.01318) —— 同期独立提出，附一份干净的证明
- [Li et al. — EAGLE: Speculative Sampling Requires Rethinking Feature Uncertainty (arXiv:2401.15077)](https://arxiv.org/abs/2401.15077) —— EAGLE-1，以隐藏态为条件的草稿
- [Li et al. — EAGLE-2: Faster Inference of Language Models with Dynamic Draft Trees (arXiv:2406.16858)](https://arxiv.org/abs/2406.16858) —— 动态树搜索
- [Li et al. — EAGLE-3: Scaling up Inference Acceleration via Training-Time Test (arXiv:2503.01840, NeurIPS 2025)](https://arxiv.org/abs/2503.01840) —— 2026 年的生产默认
- [Cai et al. — Medusa: Multiple Decoding Heads (arXiv:2401.10774)](https://arxiv.org/abs/2401.10774) —— 另一种免草稿的路线
- [vLLM Speculative Decoding documentation](https://docs.vllm.ai/en/latest/features/spec_decode.html) —— 接入了全部策略的权威生产参考
