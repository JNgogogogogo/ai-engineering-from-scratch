# Multi-Token Prediction (MTP) · 多 token 预测（MTP）

> 从 GPT-2 到 Llama 3，每个自回归 LLM 在每个位置只用一个损失训练：预测下一个 token。DeepSeek-V3 给每个位置加了第二个损失：预测再下一个 token。多出来的 14B 参数（在一个 671B 模型上）通过梯度回流蒸馏进主模型，而训练好的 MTP 头在推理时被改造成投机解码（speculative decoding）的草稿器，接受率超过 80%。1.8× 的生成吞吐是白捡的。本课从 DeepSeek 技术报告出发构建顺序式（sequential）MTP 模块，计算损失和共享输出头的参数布局，并解释为什么 MTP 保住了因果链、而 Gloeckle 等人的原始并行 MTP 破坏了它。

> Every autoregressive LLM from GPT-2 to Llama 3 trains on one loss per position: predict the next token. DeepSeek-V3 added a second loss per position: predict the token after that. The extra 14B of parameters (on a 671B model) got distilled back into the main model through gradient flow, and the trained MTP heads were repurposed at inference as speculative-decoding drafters with 80%+ acceptance. 1.8× generation throughput came for free. This lesson builds the sequential MTP module from the DeepSeek technical report, computes the loss and the shared-head parameter layout, and explains why MTP keeps the causal chain while Gloeckle et al.'s original parallel MTP broke it.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 10 · 04 (pre-training a mini GPT), Phase 10 · 15 (speculative decoding)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 陈述 MTP 训练目标，并推导跨预测深度的联合损失。
- 解释 Gloeckle 等人的并行 MTP 头（2024）与 DeepSeek-V3 顺序式 MTP 模块的区别，以及为什么顺序式设计保住了因果链。
- 计算给预训练运行加 MTP 模块带来的参数和内存开销。
- 从零实现一个 MTP 模块：共享嵌入、逐深度的 transformer 块、投影、共享输出头。

> State the MTP training objective and derive the joint loss across prediction depths.
> Explain the difference between Gloeckle et al.'s parallel MTP heads (2024) and DeepSeek-V3's sequential MTP modules and why the sequential design preserves the causal chain.
> Compute the parameter and memory overhead of adding MTP modules to a pre-training run.
> Implement one MTP module from scratch: the shared embedding, the per-depth transformer block, the projection, and the shared output head.

## The Problem · 问题在哪

下一 token 预测是标准的 LLM 训练目标。每个隐藏态只被监督去预测一件事：紧接着的下一个 token。这是一个出奇弱的信号。序列中的大多数信息都超出一个 token 之外——结构、连贯性、事实性、算术的走向。模型只能靠在数万亿 token 上累积大量单 token 信号来学会这些。

MTP 问的是：如果每个隐藏态都被监督去同时预测多个未来 token 会怎样？Gloeckle 等人（Meta，2024）证明了这有帮助。他们的实现把几个独立的输出头架在骨干之上，每个头预测一个不同的偏移量。并行、简单，但所有头看到的是同一个隐藏态，没有任何层级式的精炼——而且各预测之间没有因果链接，所以不能用于投机解码。

DeepSeek-V3（2024 年 12 月）把 MTP 重新设计成在每个预测深度都保持因果链的顺序式模块。模型从 `h_i^(0)` 预测 `t+1`，然后从一个把 `h_i^(0)` 与 `E(t+1)` 嵌入结合起来的新隐藏态 `h_i^(1)` 预测 `t+2`，以此类推。每个深度是自己的一个小 transformer 块。共享嵌入和共享输出头把参数开销压得很低。在 DeepSeek-V3 的规模上，MTP 模块在 671B 主模型权重之上只加了 14B 参数。这 2% 的开销既买到了更密的训练信号，又买到了一个推理时现成的投机解码草稿器。

本课从零构建一个 MTP 模块和 D 深度损失。数学很整洁。实现是 150 行。

> Next-token prediction is the standard LLM training objective. Every hidden state is supervised to predict exactly one thing: the immediately following token. That is a surprisingly weak signal. Most of the information in a sequence extends beyond one token — structure, coherence, factuality, arithmetic flow. The model has to learn those by accumulating many one-token signals over trillions of tokens.
> MTP asks: what if every hidden state were supervised to predict multiple future tokens at once? Gloeckle et al. (Meta, 2024) showed this helps. Their implementation put several independent output heads on top of the backbone, each predicting a different offset. Parallel, simple, but the heads saw the same hidden state without any hierarchical refinement — and the predictions did not chain causally, so they could not be used for speculative decoding.
> DeepSeek-V3 (December 2024) re-designed MTP as sequential modules that keep the causal chain at each prediction depth. ... The shared embedding and shared output head keep parameter overhead modest. At DeepSeek-V3's scale, 14B extra parameters across MTP modules on top of 671B main-model weights. That 2% overhead bought denser training signals AND a ready-made speculative-decoding draft at inference.
> This lesson builds a single MTP module and the D-depth loss from scratch. The math is tidy. The implementation is 150 lines.

## The Concept · 概念

### The sequential MTP recipe · 顺序式 MTP 配方

DeepSeek-V3 在主模型之上加 `D` 个 MTP 模块。模块 `k`（`k = 1..D`）预测深度 `k` 处的 token——即给定到位置 `i` 为止的前缀，预测 `t_{i+k}`。

模块 `k` 由以下部分组成：

- 一个带自己注意力和 MLP 的 transformer 块 `T_k`。
- 一个投影矩阵 `M_k`，把上一深度的隐藏态与下一深度真值 token 的嵌入组合起来。
- 共享嵌入 `E`（与主模型相同）。
- 共享输出头 `Out`（与主模型相同）。

训练时，对到位置 `i` 为止的前缀，逐深度隐藏态为：

```
h_i^(0) = main model backbone at position i
h_i^(k) = T_k( M_k * concat(RMSNorm(h_i^(k-1)), RMSNorm(E(t_{i+k}))) )   for k >= 1
```

逐深度预测为：

```
logits_{i+k} = Out(h_i^(k-1))   for k = 1..D
```

逐深度损失是对真值 `t_{i+k}` 的交叉熵：

```
L_k = CE(logits_{i+k}, t_{i+k})
```

跨深度的联合损失：

```
L_MTP = (lambda / D) * sum_{k=1..D} L_k
```

`lambda` 是一个小的加权因子——DeepSeek-V3 在训练的前 10% 用 0.3，之后用 0.1。总训练损失是 `L_main + L_MTP`。

> DeepSeek-V3 adds `D` MTP modules on top of the main model. Each module `k` (for `k = 1..D`) predicts the token at depth `k` — that is, `t_{i+k}` given a prefix through position `i`.
> Module `k` consists of:
> - A transformer block `T_k` with its own attention and MLP.
> - A projection matrix `M_k` that combines the previous-depth hidden state with the embedding of the next-depth ground-truth token.
> - The shared embedding `E` (same as the main model).
> - The shared output head `Out` (same as the main model).
> At training, for a prefix through position `i`, the per-depth hidden state is:
> The per-depth prediction is:
> The per-depth loss is cross-entropy against the ground-truth `t_{i+k}`:
> The joint loss across depths:
> `lambda` is a small weighting factor — DeepSeek-V3 uses 0.3 for the first 10% of training and 0.1 afterward. The total training loss is `L_main + L_MTP`.

### Why sequential, not parallel · 为什么是顺序式而不是并行式

Gloeckle 的原始并行 MTP 有 D 个输出头，每个头直接作用在 `h_i^(0)` 上。每个头从同一个骨干隐藏态预测 `t_{i+k}`。这样训练没问题，但各预测之间互不条件化。你不能用 `head_1` 的输出帮 `head_2`——所有头并行开火。

DeepSeek-V3 的顺序式设计用 `h_i^(k-1)` 加上真实的下一 token 嵌入 `E(t_{i+k})` 来构造 `h_i^(k)`。这保住了因果链：要预测 `t_{i+k+1}`，深度 `k+1` 的模块能看到 `t_{i+k}` 处是什么。这与自回归解码器消费自身输出的结构一模一样——让 MTP 模块可以被直接用作投机解码的草稿器。

推理时：把 `h_i^(k-1)` 和草拟的 `t_{i+k}` 喂进模块 `k+1`，得到对 `t_{i+k+1}` 的预测。重复。这正是 EAGLE 式的草稿，只是草稿网络用的是训练好的 MTP 模块。DeepSeek-V3 报告第一个 MTP 模块的接受率 80% 以上，加速约 1.8×。

> Gloeckle's original parallel MTP had D output heads, each directly applied to `h_i^(0)`. Each head predicts `t_{i+k}` from the same backbone hidden state. That trains fine, but the predictions are not conditioned on each other. You cannot use `head_1`'s output to help `head_2` — the heads fire in parallel.
> DeepSeek-V3's sequential design builds `h_i^(k)` from `h_i^(k-1)` plus the actual next-token embedding `E(t_{i+k})`. That preserves the causal chain: to predict `t_{i+k+1}`, the module at depth `k+1` sees what was at `t_{i+k}`. This is structurally identical to how an autoregressive decoder consumes its own output — making the MTP modules directly usable as speculative-decoding drafters.
> At inference: feed `h_i^(k-1)` and the drafted `t_{i+k}` into module `k+1`, get a prediction for `t_{i+k+1}`. Repeat. That is exactly an EAGLE-style draft, using the trained MTP module as the draft network. DeepSeek-V3 reports 80%+ acceptance on the first MTP module and ~1.8× speedup.

### Parameter accounting · 参数核算

对一个 hidden 为 `h`、词表为 `V` 的模型：

- 主模型：数十亿参数，外加一个大小 `V * h` 的输出头。
- 共享输出头：复用主模型的头。零额外参数。
- 共享嵌入：复用主模型的嵌入。零额外参数。
- 每个 MTP 模块：
  - 投影 `M_k`：`(2h) * h = 2h^2`。
  - transformer 块 `T_k`：注意力（MHA 为 `4h^2`）加 MLP（SwiGLU 比例 8/3 时通常 `8h^2`）。每块约 `12h^2`。

每模块总增量：`~14h^2`。DeepSeek-V3 的 `h = 7168`、D = 1 个模块时，纸面上 `~14 * 7168^2 = ~720M` 参数。DeepSeek-V3 报告 14B——差距主要在于 MTP 模块里的专家层同样是 MoE。

> For a model with hidden `h` and vocabulary `V`:
> - Main model: billions of parameters, plus one output head of size `V * h`.
> - Shared output head: reuse the main model's head. No extra params.
> - Shared embedding: reuse the main model's embedding. No extra params.
> - Per-MTP module:
>   - Projection `M_k`: `(2h) * h = 2h^2`.
>   - Transformer block `T_k`: attention (`4h^2` for MHA) plus MLP (typically `8h^2` for SwiGLU with ratio 8/3). About `12h^2` per block.
> Total extra per module: `~14h^2`. For DeepSeek-V3's `h = 7168`, D = 1 module: `~14 * 7168^2 = ~720M` parameters on paper. DeepSeek-V3 reports 14B — the difference is mostly expert layers being MoE in the MTP module too.

### The speculative-decoding payoff · 投机解码的回报

预训练期间，MTP 模块让训练慢约 10%（前向计算更多、多一份损失）。回报有两笔：

1. 更密的训练信号。每个隐藏态看到 D+1 个监督目标。DeepSeek-V3 的消融在 MMLU、GSM8K、MATH、HumanEval 上测得一致的几个百分点提升。

2. 推理时白送一个投机解码草稿器。MTP 模块本来就是训练来预测后几个 token 的。改造成草稿网络后，接受率 80% 以上。在这个水平上，N=3 或 N=5 的投机解码给出 1.8× 吞吐。那 10% 的训练成本，第一次跑推理就回本了。

> During pre-training, the MTP modules slow training by about 10% (more forward compute, extra loss). The payoff is two-fold:
> 1. Denser training signal. Each hidden state sees D+1 supervision targets. Measured effect on MMLU, GSM8K, MATH, HumanEval: consistent few-percentage-point improvements in DeepSeek-V3's ablations.
> 2. Free speculative decoding draft at inference. The MTP module is already trained to predict the next few tokens. Repurposed as a draft network, it delivers 80%+ acceptance rates. At that level, N=3 or N=5 spec decoding gives 1.8× throughput. The 10% training-time cost pays back the first time you run inference.

### Relation to EAGLE · 与 EAGLE 的关系

EAGLE 在预训练之后单独训练一个小草稿模型。MTP 把草稿直接烤进预训练。两条路线在接受率上殊途同归，但管道不同：

| Dimension | EAGLE-3 | MTP (DeepSeek-V3) |
|-----------|---------|------------------|
| 训练时机 | 预训练之后 | 预训练期间 |
| 与现有权重向后兼容 | 是 | 否（需要重训） |
| 草稿参数 | 1-2 个 transformer 层 | 1 个 transformer 块 + 投影 |
| 接受率 | 0.88-0.92 | 深度 1 处 0.80+ |
| 加速之外的收益 | 只有投机解码 | 更密的训练信号 + 加速 |

> EAGLE trains a small draft model SEPARATELY after pre-training. MTP bakes the draft into pre-training. The two approaches converge on similar accept rates but via different pipelines:

```figure
multi-token-predict
```

## Build It · 动手造

`code/main.py` 端到端构建单个 MTP 模块：共享嵌入、投影、transformer 块、共享输出头。然后在一条短合成序列上计算逐深度交叉熵损失，并按组件打印参数量。32 个 token 的玩具词表让数字保持可读。

> `code/main.py` builds a single MTP module end to end: shared embedding, projection, transformer block, shared output head. It then computes the per-depth cross-entropy loss on a short synthetic sequence and prints the parameter count by component. A toy vocabulary of 32 tokens keeps the numbers readable.

### Step 1: shared embedding table · 第 1 步：共享嵌入表

一张 `vocab_size x hidden` 的表，主模型和每个 MTP 模块在每个深度都用它。不是第二份拷贝——就是同一个张量。

> A single `vocab_size x hidden` table is used by the main model AND by every MTP module at every depth. Not a second copy — literally the same tensor.

### Step 2: the per-depth combination · 第 2 步：逐深度组合

```python
def combine(prev_hidden, next_token_embed, M_k):
    # concat along feature dim, then project down to hidden
    concat = rms_norm(prev_hidden) + rms_norm(next_token_embed)  # vector addition stand-in
    projected = matvec(M_k, concat)
    return projected
```

真实的 DeepSeek-V3 把两个 RMSNorm 过的向量拼接到 `[2h]`，再用一个 `h x 2h` 矩阵投影。玩具为了 stdlib 简洁用了向量加法。

> Real DeepSeek-V3 concatenates the two RMSNormed vectors to `[2h]` and projects with an `h x 2h` matrix. The toy uses vector addition for stdlib brevity.

### Step 3: the transformer block at depth k · 第 3 步：深度 k 的 transformer 块

自注意力加 MLP。玩具里用单层线性注意力块和一个 SwiGLU MLP，在不引入 numpy 的前提下保持结构可见。

> Self-attention plus MLP. In the toy, a one-layer linear attention block and a SwiGLU MLP keep the structure visible without numpy.

### Step 4: the shared output head · 第 4 步：共享输出头

复用主模型的输出投影。得到词表上的 logits。

> Reuse the main model's output projection. Logits over the vocabulary.

### Step 5: per-depth loss · 第 5 步：逐深度损失

softmax(logits) 对偏移 `k` 处真值 token 的交叉熵。用 `lambda / D` 缩放因子跨深度聚合。

> Cross-entropy of softmax(logits) against the ground-truth token at offset `k`. Aggregate across depths with the `lambda / D` scaling factor.

### Step 6: parameter accounting · 第 6 步：参数核算

打印总参数量、共享部分（嵌入、头）的参数量和每模块的额外参数量。展示 MTP 增量与主模型大小之比。

> Print the total parameter count, the shared (embedding, head) count, and the per-module extra count. Show the ratio of MTP extra to main-model size.

## Use It · 实战用法

MTP 已集成进 DeepSeek-V3（2024 年 12 月）和 DeepSeek-R1 系列。推理侧：

- DeepSeek 自家的服务栈开箱即用地把 MTP 模块当投机解码器消费。
- 截至 2026 年 4 月，vLLM 和 SGLang 都有 DeepSeek-V3 MTP 的集成路径。
- AMD 的 ROCm SGLang 教程展示了一个具体的 MTP 投机解码配置，在 V3 checkpoint 上实测 1.8× 加速。

新的预训练运行什么时候用 MTP：

- 你掌控完整预训练流水线，想存下一笔更密的训练信号。
- 你知道模型会规模化上线，想白得投机解码。
- 你的 hidden size 至少 4096。在 1B 规模，开销的害处大于收益。

什么时候不用：

- 微调一个已存在的预训练稠密模型。MTP 模块没有训练过。
- 你想要干净基线做对照的研究模型。MTP 会改架构。

> MTP is integrated into DeepSeek-V3 (December 2024) and the DeepSeek-R1 series. At inference:
> - DeepSeek's own serving stack consumes MTP modules as speculative decoders out of the box.
> - vLLM and SGLang have integration paths for DeepSeek-V3 MTP as of April 2026.
> - AMD's ROCm SGLang tutorial shows a specific MTP speculative-decoding config with measured 1.8× speedup on the V3 checkpoint.
> When to use MTP in a new pre-training run:
> - You control the full pre-training pipeline and want to bank denser training signal.
> - You know you will serve the model at scale and want speculative decoding for free.
> - Your hidden size is at least 4096. At 1B-scale the overhead hurts more than the gain helps.
> When not to:
> - Fine-tuning an existing pre-trained dense model. The MTP module is not trained.
> - Research models where you want a clean baseline to compare against. MTP changes the architecture.

## Ship It · 交付

本课产出 `outputs/skill-mtp-planner.md`。给定一份预训练运行规格（模型大小、数据、算力），它会返回集成 MTP 的计划：深度数 D、`lambda` 调度、内存开销，以及推理时的投机解码接线方式。

> This lesson produces `outputs/skill-mtp-planner.md`. Given a pre-training run specification (model size, data, compute), it returns a plan for integrating MTP: number of depths D, `lambda` schedule, memory overhead, and the inference-time speculative-decoding wiring.

## Exercises · 练习

1. 运行 `code/main.py`。展示逐深度损失随合成信号增强而单调下降。把合成数据改成固定模式，验证深度 1 和深度 2 的损失都收敛。

2. 计算一个稠密 70B 模型（hidden 8192，80 层）配 D=1 MTP 模块的参数开销。与 DeepSeek-V3 报告的 14B 开销比较。解释 DeepSeek 的数字为什么更高：MTP 的 transformer 块继承了同样的 MoE 结构，抬高了每模块参数量。

3. 在玩具里实现 D=2：加第二个 MTP 模块，它取 `h^(1)` 并预测 `t_{i+2}`。验证联合损失和参数核算与 DeepSeek 论文的式 19-21 一致。

4. 把玩具改成并行 MTP（Gloeckle 风格）：在主隐藏态上加 D 个输出头，各预测一个不同偏移。在同一合成信号上测各深度损失与顺序版的差距。顺序版在 k > 1 时深度-k 损失应更低，因为它条件化于中间预测。

5. 把训练好的 MTP 模块当 EAGLE 式草稿用：推理时调用模块 k 提出 `t_{i+k}`。在一条留出序列上测这些草稿 token 相对主模型预测的接受率。如果玩具上能到 50%+，你就复现了「MTP 即草稿」的经验性质。

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| MTP module | 「额外损失块」 | 一个小 transformer 块加投影，预测主模型前方 `k` 个位置的 token |
| Prediction depth | 「哪个偏移」 | 整数 `k`：模块 `k` 从到位置 `i` 为止的前缀预测 `t_{i+k}` |
| Parallel MTP | 「Gloeckle 风格」 | 同一骨干隐藏态上的 D 个独立头，没有条件链 |
| Sequential MTP | 「DeepSeek-V3 风格」 | 每个模块条件化于上一深度隐藏态加下一 token 嵌入；保持因果链 |
| Shared output head | 「复用主头」 | MTP 模块调用主模型的 LM 头，而不是单独的输出投影 |
| Shared embedding | 「复用主表」 | 全处共用同一张词表嵌入表；没有重复参数 |
| Projection matrix M_k | 「合并隐藏态 + 下一 token」 | 一个 `h x 2h` 线性层，把上一隐藏态和目标 token 嵌入折叠成下一深度的输入 |
| Joint loss L_MTP | 「额外损失的平均」 | 逐深度交叉熵损失的算术平均，再乘 `lambda` |
| Acceptance rate at depth 1 | 「MTP 草稿多久对一次」 | D=1 的 MTP 模块 top-1 预测等于主模型 top-1 预测的比率；DeepSeek-V3 上 80%+ |
| Lambda weighting | 「额外损失的权重」 | 逐深度缩放因子；DeepSeek-V3 上训练开始 0.3、之后 0.1 |

## Further Reading · 延伸阅读

- [DeepSeek-AI — DeepSeek-V3 Technical Report (arXiv:2412.19437)](https://arxiv.org/abs/2412.19437) —— 完整的顺序式 MTP 描述（2.2 节），含联合损失方程和推理时 1.8× 加速
- [Gloeckle et al. — Better & Faster Large Language Models via Multi-token Prediction (arXiv:2404.19737)](https://arxiv.org/abs/2404.19737) —— DeepSeek 设计所改进的并行 MTP 基线
- [DeepSeek-V3 model card on Hugging Face](https://huggingface.co/deepseek-ai/DeepSeek-V3) —— 总参数 685B（671B 主模型 + 14B MTP），部署注意事项
- [Leviathan et al. — Fast Inference from Transformers via Speculative Decoding (arXiv:2211.17192)](https://arxiv.org/abs/2211.17192) —— MTP 所嵌入的投机解码框架
- [Li et al. — EAGLE-3 (arXiv:2503.01840)](https://arxiv.org/abs/2503.01840) —— EAGLE 2025 年的草稿架构，MTP 的竞争对手
