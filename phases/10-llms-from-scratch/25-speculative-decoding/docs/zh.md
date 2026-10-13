# Speculative Decoding and EAGLE · 投机解码与 EAGLE

> 前沿 LLM 生成一个 token，需要对数十亿参数做一次完整前向。这次前向严重供过于求：大多数时候，一个小得多的模型就能猜对接下来 3-5 个 token，大模型只需要*验证*这个猜测。猜对了，你就用一次前向的代价拿到 5 个 token。投机解码（speculative decoding，Leviathan et al. 2023）把这件事做到了数学上精确，EAGLE-3（2025）把接受率推到每次验证约 4.5 个 token——在输出分布完全一致的前提下加速 4-5 倍。
>
> A frontier LLM generating one token requires a full forward pass over billions of parameters. That forward pass is massively over-provisioned: most of the time a much smaller model can guess the next 3-5 tokens correctly, and the big model only needs to *verify* the guess. When the guess is right you got 5 tokens for the price of one. Speculative decoding (Leviathan et al. 2023) made this exact, and EAGLE-3 (2025) pushed acceptance rates to ~4.5 tokens per verify — a 4-5x speedup at matched output distribution.

**Type:** Build
**Languages:** Python (with numpy)
**Prerequisites:** Phase 10 Lesson 12 (Inference Optimization), Phase 10 Lesson 04 (Pre-training Mini-GPT)
**Time:** ~75 minutes

## The Problem · 问题在哪

70B 级模型在 H100 上的解码吞吐通常是 40-80 token/秒。每个 token 都要做一次完整前向、把全部模型权重从 HBM 读一遍。你不能把模型变小而不改变它的输出，也不能在内存限制之上继续加大 batch。你被卡死了——除非让模型每次前向输出不止一个 token。

自回归生成看起来天生串行：`x_{t+1} = sample(p(· | x_{1:t}))`。但这里有一个并发机会。如果你有一个便宜的预测器说「接下来 4 个 token 大概率是 [a, b, c, d]」，你就可以用**大模型的单次前向**验证全部 5 个位置，接受最长的匹配前缀。

Leviathan、Kalai、Matias（2023，「Fast Inference from Transformers via Speculative Decoding」）用一个聪明的接受/拒绝规则把这件事做到了精确，保持目标模型的采样分布不变。同样的输出分布，快 2-4 倍。

> Decode throughput for a 70B-class model on H100 is typically 40-80 tokens/second. Each token requires a full forward pass reading all model weights from HBM. You cannot make the model smaller without changing its output. You cannot increase batch size beyond memory. You're stuck — unless you can let the model output more than one token per forward pass. ... If you had a cheap predictor that said "the next 4 tokens are probably [a, b, c, d]" you could verify all 5 positions in a **single forward pass of the big model** and accept the longest matching prefix. ... Leviathan, Kalai, Matias (2023, "Fast Inference from Transformers via Speculative Decoding") made this exact via a clever accept/reject rule that preserves the target model's sampling distribution. The same output distribution, 2-4× faster.

## The Concept · 概念

### The Two-Model Setup · 双模型设置

- **目标模型（target model）** `M_p`：你真正想要其样本的大而慢、高质量模型。分布：`p(x)`。
- **草稿模型（draft model）** `M_q`：小而快、质量较低的模型。分布：`q(x)`。比目标小 5-30 倍。

每一步：

1. 草稿模型自回归地提出 `K` 个 token：`x_1, x_2, ..., x_K ~ q`。
2. 目标模型对全部 `K+1` 个位置并行跑一次前向，对每个被提议的 token 产出 `p(x_k)`。
3. 用下文的修改版拒绝采样规则从左到右逐个接受/拒绝，接受最长匹配前缀。
4. 若有 token 被拒绝，从修正后的分布采样替换 token 并停止。否则从 `p(· | x_1...x_K)` 再采样一个奖励 token。

草稿与目标完全一致时，每次目标前向拿到 K+1 个 token。草稿在第 1 个位置就错时，只拿到 1 个 token。

> **Target model** `M_p`: the big, slow, high-quality model you actually want samples from. Distribution: `p(x)`. ... **Draft model** `M_q`: a small, fast, lower-quality model. Distribution: `q(x)`. 5-30× smaller. ... If the draft matches the target perfectly, you get K+1 tokens per target-forward. If the draft is wrong at position 1, you get only 1 token.

### The Exactness Rule · 精确性规则

投机解码**在分布上可证明等价于从 p 采样**。拒绝规则：

```
For each drafted token x_t:
    r ~ Uniform(0, 1)
    if r < p(x_t) / q(x_t):
        accept x_t
    else:
        sample replacement from residual: (p - q)+ / ||(p - q)+||_1
        stop
```

其中 `(p - q)+` 表示逐点差的正部。草稿与目标一致（`p ≈ q`）时，接受率接近 1；不一致时，残差分布的构造保证整体样本仍然严格是 `p`。

**贪心情形。** temperature=0 采样只需检查 `argmax(p) == x_t`。是则接受；否则输出 `argmax(p)` 并停止。

> Speculative decoding is **provably equivalent in distribution to sampling from p**. The rejection rule: ... where `(p - q)+` denotes the positive part of the pointwise difference. When the draft and target agree (`p ≈ q`) acceptance is nearly 1. When they disagree, the residual distribution is constructed so that the overall sample is still exactly `p`. ... **Greedy case.** For temperature=0 sampling just check `argmax(p) == x_t`. If yes, accept; if no, output `argmax(p)` and stop.

### Expected Speedup · 期望加速比

若草稿模型的 token 级接受率为 `α`，每次目标前向期望产出的 token 数为：

```
E[tokens] = (1 - α^{K+1}) / (1 - α)        # K = draft length, α in [0, 1]
```

`α = 0.8, K = 4` 时：`(1 - 0.8^5)/(1 - 0.8) = 3.36` 个 token/前向。一次目标前向的成本约为 `cost_q * K + cost_p`（K 步草稿加一次目标验证）。若 `cost_p >> cost_q * K`，吞吐加速比就是 `3.36× / 1 = 3.36×`。

唯一真实的参数是 `α`，而它完全取决于草稿与目标的对齐程度。一个好的草稿就是一切。

> If the draft model's token-level acceptance rate is `α`, the expected tokens produced per target-forward pass is: ... At `α = 0.8, K = 4`: `(1 - 0.8^5)/(1 - 0.8) = 3.36` tokens per forward. ... The only real parameter is `α`, which depends entirely on the draft-target alignment. A good draft is everything.

### Training the Draft: Distillation · 训练草稿模型：蒸馏

随机挑一个小模型当草稿效果很差。标准配方是从目标模型蒸馏：

1. 选一个小架构（70B 目标配约 1B，7B 目标配约 500M）。
2. 让目标模型跑大语料；存下它的下一 token 分布。
3. 用 KL 散度对照目标的分布训练草稿（而不是对照真实 token）。

结果：编码任务上 `α` 典型为 0.6-0.8，自然语言聊天上 0.7-0.85。生产环境加速 2-3 倍。

> A random small model makes a poor draft. The standard recipe is to distill from the target: ... Train the draft with KL divergence against the target's distribution (not against ground-truth tokens). ... The result: `α` typically 0.6-0.8 on coding, 0.7-0.85 on natural-language chat. Speedups 2-3× in production.

### EAGLE: Tree Drafting + Feature Reuse · EAGLE：树状草稿 + 特征复用

Li、Wei、Zhang、Zhang（2024，「EAGLE: Speculative Sampling Requires Rethinking Feature Uncertainty」）指出了标准投机解码的两处低效：

1. 草稿要做 K 个串行步，每步都是完整栈。但草稿本可以复用目标最近一次验证留下的特征（隐藏状态）——目标早已算出丰富的表示，草稿却在从零重推。
2. 草稿输出一条线性链。如果草稿能输出一棵候选*树*（每个节点多个猜测），目标的一次前向就能用树注意力掩码并行验证多条候选路径，并挑出最长的被接受分支。

EAGLE-1 的改动：
- 草稿输入 = 目标在位置 t 的最终隐藏状态，而不是原始 token。
- 草稿架构 = 1 层 transformer decoder（不是独立的小模型）。
- 输出 = 每层深度 K = 4-8 个候选的树，深度 4-6。

EAGLE-2（2024）加入动态树拓扑：树在草稿不确定处长宽，在自信处保持窄。在不增加验证成本的情况下抬高 `α_effective`。

EAGLE-3（Li et al. 2025，「EAGLE-3: Scaling up Inference Acceleration of Large Language Models via Training-Time Test」）去掉了对固定顶层特征的依赖，用新的「训练时测试」（test-time simulation）损失训练草稿——草稿训练所用的输出对齐目标的测试时分布，而不是 teacher-forced 的训练分布。接受率从 0.75（EAGLE-2）升至 0.82（EAGLE-3），每次验证的平均 token 数从 3.0 升至 4.5。

> EAGLE-1 changes: ... Draft input = target's final hidden state at position t, not raw tokens. ... EAGLE-2 (2024) adds dynamic tree topology: the tree grows wider where the draft is uncertain and stays narrow where it is confident. Raises `α_effective` without increasing verify cost. ... EAGLE-3 ... removes the fixed top-layer feature dependency and trains the draft with a new "test-time simulation" loss — the draft is trained on outputs that match the target's test-time distribution rather than teacher-forced training distribution. Acceptance rate rises from 0.75 (EAGLE-2) to 0.82 (EAGLE-3), and mean tokens/verify from 3.0 to 4.5.

### Tree Attention Verification · 树注意力验证

草稿输出树时，目标模型用**树注意力掩码（tree attention mask）**在单次前向中完成验证——这是一条编码树拓扑而非纯直线的因果掩码。每个 token 只 attend 树中的祖先。验证仍然是一次前向、一次矩阵乘；拓扑掩码只多花几个 KV 条目。

```
        root
       /    \
      a      b
     / \    / \
    c  d   e   f
```

若 `a, b` 是相互竞争的第一 token 候选，`c, d, e, f` 是第二 token 候选，则全部六个位置在一次前向中完成验证。输出是任一被接受路径上的最长前缀。

> When the draft outputs a tree, the target model verifies it in a single forward pass using a **tree attention mask** — a causal mask that encodes the tree topology rather than a pure line. Each token attends only to its ancestors in the tree. The verify pass is still one forward, one matmul; the topological mask costs only a few extra KV entries. ... If `a, b` are competing first-token candidates and `c, d, e, f` are second-token candidates, all six positions are verified in one forward pass. The output is the longest prefix along any accepted path.

### When It Wins, When It Doesn't · 什么时候赢，什么时候不赢

**赢：**
- 文本可预测的聊天 / 补全（代码、常见英文、结构化输出）。`α` 高。
- 解码期有闲置 GPU 算力的场景（内存受限阶段）。树草稿把闲置的 FLOPs 用起来。

**输 / 无收益：**
- 高随机输出（高 temperature 的创意写作）。`α` 跌向 `1/|vocab|`。
- 高并发的批量服务——batching 早已填满 FLOPs，树验证没多少空间。
- 目标模型非常小、草稿小不了多少的场景。

生产团队的典型报告：聊天 2-3 倍墙钟加速，代码生成 3-5 倍，创意写作接近零。

> **Wins:** ... Chat / completion with predictable text (code, common English, structured output). `α` is high. ... Settings with unused GPU compute during decode (memory-bound phase). Tree drafting uses the available FLOPs. ... **Loses / no win:** ... Highly stochastic outputs (creative writing at high temperature). `α` drops toward `1/|vocab|`. ... Production shops typically report 2-3× wall-clock speedup on chat, 3-5× on code generation, and near-zero on creative writing.

```figure
speculative-decoding
```

## Build It · 动手造

`code/main.py`：

- 一个参考实现 `speculative_decode(target, draft, prompt, K, temperature)`，实现精确拒绝规则，并验证它保持目标分布（与朴素目标采样相比经验 KL < 0.01）。
- 一个 EAGLE 风格的树草稿器，按 top-p 分支构建深度 K 的树。
- 一个树注意力掩码构造器，为验证器生成正确的因果模式。
- 一个接受率测量台，在微型 LM 上运行两者（从 GPT-2-medium 目标蒸馏一个 GPT-2-small）。

```python
def speculative_step(p_target, q_draft, K, temperature=1.0):
    """One round of speculative decoding. Returns list of accepted tokens."""
    # 1. Draft K tokens
    draft_tokens = []
    q_probs = []
    state = draft_state_init()
    for _ in range(K):
        probs = softmax(q_draft(state) / temperature)
        t = np.random.choice(len(probs), p=probs)
        draft_tokens.append(t)
        q_probs.append(probs[t])
        state = draft_step(state, t)

    # 2. Target computes p at every drafted position + 1 extra
    p_probs_all = target_forward_batched(p_target, draft_tokens, temperature)

    # 3. Accept/reject left-to-right
    accepted = []
    for k, tok in enumerate(draft_tokens):
        r = np.random.uniform()
        if r < p_probs_all[k][tok] / q_probs[k]:
            accepted.append(tok)
        else:
            residual = np.maximum(p_probs_all[k] - q_probs[k], 0)
            residual /= residual.sum()
            accepted.append(np.random.choice(len(residual), p=residual))
            return accepted
    # 4. All K accepted → sample bonus token from target
    accepted.append(np.random.choice(len(p_probs_all[-1]), p=p_probs_all[-1]))
    return accepted
```

> `code/main.py`: ... A reference `speculative_decode(target, draft, prompt, K, temperature)` that implements the exact rejection rule and verifies it preserves the target's distribution (empirical KL < 0.01 vs plain target sampling). ... An acceptance-rate harness that runs both on a tiny LM (distill one GPT-2-small from a GPT-2-medium target).

## Use It · 实战用法

- **vLLM** 和 **SGLang** 提供一等公民的投机解码。在 vLLM 里，给 `--speculative-config` 传一个含 `method`、`model`、`num_speculative_tokens` 的 JSON 对象；EAGLE-3 即 `"method": "eagle3"`。
- **NVIDIA TensorRT-LLM** 原生支持 Medusa 和 EAGLE 树。
- **参考草稿模型**：`Qwen/Qwen3-0.6B`（给 Qwen3-32B 当草稿）、`meta-llama/Llama-3.2-1B-Instruct`（给 Llama 3.x 70B 当草稿）。
- **Medusa heads**（Cai et al. 2024，「Medusa: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads」）：不要草稿模型，直接给目标本身加 K 个并行预测头。部署更简单，接受率略低于 EAGLE。

> **vLLM** and **SGLang** ship first-class speculative decoding. In vLLM, pass `--speculative-config` a JSON object with `method`, `model`, and `num_speculative_tokens`; EAGLE-3 is `"method": "eagle3"`. ... **Medusa heads** (Cai et al. 2024, "Medusa: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads"): instead of a draft model, add K parallel prediction heads to the target itself. Simpler to deploy, slightly lower acceptance than EAGLE.

## Ship It · 交付

本课产出 `outputs/skill-speculative-tuning.md` —— 一个技能：剖析目标模型的工作负载，然后选择草稿模型、K（草稿长度）、树宽、temperature，以及何时退回普通解码。

> This lesson produces `outputs/skill-speculative-tuning.md` — a skill that profiles a target model's workload and chooses: draft model, K (draft length), tree width, temperature, and when to fall back to plain decode.

## Exercises · 练习

1. 实现精确拒绝规则并做经验验证。分别通过 `speculative_decode` 和朴素目标采样各跑 10K 个样本；计算两个输出分布之间的 TV 距离。应当 < 0.01。
2. 推导加速比公式。给定固定的 `α` 和 `K`，画出每次目标前向的期望 token 数。为 α ∈ {0.5, 0.7, 0.9} 找出最优 K。
3. 训练一个微型草稿。取 124M 的 GPT-2 目标，在 100M token 上用 KL 损失蒸馏一个 30M 的 GPT-2 草稿。在留出文本上测 `α`。预期：0.6-0.7。
4. 实现 EAGLE 风格的树草稿。草稿每层深度输出 top-3 分支而非链式。构建树注意力掩码。验证目标接受最长的正确分支。
5. 测量失败模式。在 temperature=1.5（高随机性）下运行投机解码。展示 α 崩塌，且由于草稿开销，算法比朴素解码更慢。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|------------------------|
| Target model | 「大模型」 | 你想要其样本的慢速高质量模型（p 分布） |
| Draft model | 「投机者」 | 小而快的预测器（q 分布）；比目标小 5-30 倍 |
| K / draft length | 「前瞻步数」 | 每次验证所推测的 token 数 |
| α / acceptance rate | 「命中率」 | 草稿提议被接受的逐 token 概率 |
| Exact rejection rule | 「接受测试」 | 保持目标分布不变的 r < p/q 比较 |
| Residual distribution | 「修正后的 p-q」 | (p - q)+ / ||(p - q)+||_1，被拒时用于采样的分布 |
| Tree drafting | 「分支投机」 | 草稿输出候选树，用树状注意力掩码一次验证 |
| Tree attention mask | 「拓扑掩码」 | 编码树拓扑的因果掩码，使每个节点只 attend 其祖先 |
| Medusa heads | 「并行头」 | 目标模型自身上的 K 个额外预测头；无需独立草稿模型 |
| EAGLE feature reuse | 「隐藏状态草稿」 | 草稿输入是目标的最后隐藏状态而非原始 token，从而缩小草稿 |
| Test-time simulation loss | 「EAGLE-3 训练法」 | 用匹配目标测试时分布（而非 teacher forcing）的输出训练草稿 |

## Further Reading · 延伸阅读

- [Leviathan, Kalai, Matias, 2023 — "Fast Inference from Transformers via Speculative Decoding"](https://arxiv.org/abs/2211.17192) —— 精确拒绝规则与理论加速比分析
- [Chen, Borgeaud, Irving et al., 2023 — "Accelerating Large Language Model Decoding with Speculative Sampling"](https://arxiv.org/abs/2302.01318) —— DeepMind 同时发表的投机采样论文
- [Cai, Li, Geng, Wang, Wang, Zhu, Dao, 2024 — "Medusa: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads"](https://arxiv.org/abs/2401.10774) —— 草稿模型的并行头替代方案
- [Li, Wei, Zhang, Zhang, 2024 — "EAGLE: Speculative Sampling Requires Rethinking Feature Uncertainty"](https://arxiv.org/abs/2401.15077) —— 特征复用与树草稿
- [Li et al., 2024 — "EAGLE-2: Faster Inference of Language Models with Dynamic Draft Trees"](https://arxiv.org/abs/2406.16858) —— 动态树拓扑
- [Li et al., 2025 — "EAGLE-3: Scaling up Inference Acceleration of Large Language Models via Training-Time Test"](https://arxiv.org/abs/2503.01840) —— 训练时与测试时分布匹配
- [Fu, Haotian, Peng et al., 2024 — "Break the Sequential Dependency of LLM Inference Using Lookahead Decoding"](https://arxiv.org/abs/2402.02057) —— Jacobi/lookahead 解码，无需投机者的替代方案
