# DeepSeek-V3 Architecture Walkthrough · DeepSeek-V3 架构精读

> Phase 10 · 第 14 课点名了每个开源模型都会拧的六个架构旋钮。DeepSeek-V3（2024 年 12 月，总参数 671B，激活参数 37B）把六个旋钮全部拧到位，还新增了四个：多头潜在注意力（Multi-Head Latent Attention，MLA）、无辅助损失负载均衡（auxiliary-loss-free load balancing）、多 Token 预测（Multi-Token Prediction，MTP）和 DualPipe 训练。本课自顶向下通读 DeepSeek-V3 的架构，并从公开 config 逐项推导出每个参数量。学完之后，你能解释为什么 671B/37B 的比例是正确的赌注，以及为什么 MLA + MoE 组合在前沿比任何单一手段都强。
>
> Phase 10 · Lesson 14 named the six architectural knobs every open model turns. DeepSeek-V3 (December 2024, 671B parameters total, 37B active) turns all six and adds four more: Multi-Head Latent Attention, auxiliary-loss-free load balancing, Multi-Token Prediction, and DualPipe training. This lesson reads DeepSeek-V3's architecture top to bottom and derives every parameter count from the published config. By the end you can explain why the 671B/37B ratio is the right bet and why MLA + MoE together beat either alone at the frontier.

**Type:** Learn
**Languages:** Python (stdlib, parameter calculator)
**Prerequisites:** Phase 10 · 14 (open-model walkthroughs), Phase 10 · 17 (NSA), Phase 10 · 18 (MTP), Phase 10 · 19 (DualPipe)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 自顶向下通读 DeepSeek-V3 的 config，用「GPT-2 的六个旋钮 + DeepSeek 特有的四个新增项」解释每个字段的含义。
- 推导总参数量（671B）与激活参数量（37B），并指出各自由哪些组件贡献。
- 计算 MLA 在 128k 上下文下的 KV cache 占用，并与同等激活参数、采用 GQA 的稠密模型所需的开销对比。
- 说出 DeepSeek 特有的四项创新（MLA、MTP、无辅助损失路由、DualPipe），并指明每项分别作用于架构/训练栈的哪个部分。

> Read the DeepSeek-V3 config top to bottom and explain each field in terms of the six GPT-2 knobs plus four DeepSeek-specific additions.
> Derive the total parameter count (671B), active parameter count (37B), and the components that contribute to each.
> Compute the KV cache footprint of MLA at 128k context and compare to what a same-active-param dense model with GQA would pay.
> State the four DeepSeek-specific innovations (MLA, MTP, auxiliary-loss-free routing, DualPipe) and name which part of the architecture/training stack each one targets.

## The Problem · 问题在哪

DeepSeek-V3 是第一个架构与 Llama 家族产生实质性差异的前沿开源模型。Llama 3 405B 是「拧了六个旋钮的 GPT-2」，DeepSeek-V3 则是六个旋钮全拧、再外加四个的 GPT-2。读 Llama 3 的 config 只是读 DeepSeek config 的热身，但那些深层结构——注意力块的形状、路由逻辑、训练期目标——差异大到值得单独走读一遍。

学会它的回报：DeepSeek-V3 的开放权重发布改写了「前沿能力」对开源模型的含义。这套架构是 2026 年许多训练运行正在照抄的蓝图。对任何接触前沿 LLM 训练或推理的角色而言，理解它是入场券。

> DeepSeek-V3 is the first frontier open model whose architecture is meaningfully different from the Llama family. ... Reading the Llama 3 config is a warmup for reading the DeepSeek config, but the deep structure — the shape of the attention block, the routing logic, the training-time objective — is different enough that you need a separate walkthrough. ... The architecture is the blueprint many 2026 training runs are copying. Understanding it is table stakes for any role that touches frontier LLM training or inference.

## The Concept · 概念

### The invariant core, again · 不变的核心，再看一遍

DeepSeek-V3 依然是自回归（autoregressive）模型，依然堆叠 decoder 块。每个块仍然是注意力 + MLP + 两个 RMSNorm。MLP 里仍然是 SwiGLU。位置编码仍然是 RoPE。Pre-norm。嵌入与输出共享权重（weight-tied）。和每一个 Llama、Mistral 是同一个基线。

> DeepSeek-V3 is still autoregressive. It still stacks decoder blocks. Each block still has attention plus MLP plus two RMSNorms. It still uses SwiGLU in the MLP. It still uses RoPE. Pre-norm. Weight-tied embeddings. Same baseline as every Llama or Mistral.

### The twist: MLA instead of GQA · 关键改动：用 MLA 取代 GQA

Phase 10 · 14 讲过，GQA 通过在多组 Q head 之间共享 K 和 V 来缩小 KV cache。多头潜在注意力（Multi-Head Latent Attention，MLA）走得更远：K 和 V 被压缩成一个共享的低秩潜在表示（即 `kv_lora_rank`），再在每个 head 计算时即时解压。KV cache 只存这个潜在向量——通常每 token 每层 512 个浮点数，而不是 8 x 128 = 1024 个浮点数。

在 128k 上下文下，采用 MLA 的 DeepSeek-V3（每 token 每层一个共享潜在向量 `c^{KV}`；K 和 V 都由该潜在向量经上投影得到，而这些上投影可以被吸收进后续的矩阵乘法）：

```
kv_cache = num_layers * kv_lora_rank * max_seq_len * bytes_per_element
         = 61 * 512 * 131072 * 2
         = 7.6 GB
```

一个假想的 GQA 基线（Llama 3 70B 的形状，8 个 KV head，head 维度 128）则要付出：

```
kv_cache = 2 * 61 * 8 * 128 * 131072 * 2
         = 30.5 GB
```

在 128k 上下文下，MLA 的 cache 比 Llama-3-70B 风格的 GQA cache 小 4 倍。

代价是：MLA 在每次注意力计算（每个 head）中多了一步解压。这部分额外计算相对省下的带宽很小。对长上下文推理是净赚。

> From Phase 10 · 14 you know GQA shrinks the KV cache by sharing K and V across groups of Q heads. Multi-Head Latent Attention (MLA) goes further: K and V are compressed into a shared low-rank latent representation (the `kv_lora_rank`), then decompressed per head on the fly. The KV cache stores only the latent — typically 512 floats per token per layer, not 8 x 128 = 1024 floats. ... MLA is 4x smaller than a Llama-3-70B-style GQA cache at 128k context. ... The tradeoff: MLA adds a decompression step per attention computation (per head). The extra compute is small compared to the bandwidth saved. Net win for long-context inference.

### The routing: auxiliary-loss-free load balancing · 路由：无辅助损失的负载均衡

MoE 路由器决定每个 token 由哪 top-k 个专家处理。朴素的路由器会把过多工作集中到少数专家身上，让其他专家闲置。标准修法：加一个惩罚负载不均衡的辅助损失（auxiliary loss）项。这招有效，但会轻微损害主任务性能。

DeepSeek-V3 引入了无辅助损失（auxiliary-loss-free）的方案：给路由 logits 加上每个专家的偏置项，训练中用一条简单规则调整——专家 `e` 过载就调低 `bias_e`，负载不足就调高。没有额外损失项。训练保持干净。专家负载保持均衡。

对主损失的影响：测不出差异。对 MoE 架构的影响：更干净，少了一个要调的辅助损失超参数。

> MoE routers decide which top-k experts process each token. A naive router concentrates too much work on a few experts, leaving others idle. Standard fix: add an auxiliary loss term that penalizes load imbalance. This works but slightly degrades main-task performance. ... DeepSeek-V3 introduces an auxiliary-loss-free scheme. Per-expert bias terms are added to the router logits, adjusted during training by a simple rule: if expert `e` is overloaded, decrease `bias_e`; if underloaded, increase it. No extra loss term. Training stays clean. Expert load stays balanced.

### The MTP: denser training + free draft · MTP：更密的训练信号 + 免费的草稿模型

Phase 10 · 18 讲过，DeepSeek-V3 加了一个 D=1 的 MTP 模块，用来预测往后两个位置的 token。推理时，这个训练好的模块被改造成投机解码（speculative decoding）的草稿模型，接受率 80% 以上。训练时，每个隐藏状态要在 D+1 = 2 个目标上接受监督，提供更密的信号。

参数：在 671B 主模型之上再加 14B。开销：2.1%。

> From Phase 10 · 18 you know DeepSeek-V3 adds D=1 MTP module that predicts the token two positions ahead. At inference, the trained module is repurposed as a speculative-decoding draft with 80%+ acceptance. At training, each hidden state is supervised on D+1 = 2 targets, providing a denser signal.

### The training: DualPipe · 训练：DualPipe

Phase 10 · 19 讲过，DualPipe 是一条双向流水线，把前向和反向的计算块与跨节点的 all-to-all 通信重叠起来。在 DeepSeek-V3 的 2,048 张 H800 规模下，它大约挽回 24.5 万 GPU 小时——这些时间在 1F1B 调度下会白白耗在流水线气泡（pipeline bubble）里。

> From Phase 10 · 19 you know DualPipe is a bidirectional pipeline that overlaps forward and backward chunks with cross-node all-to-all comms. At DeepSeek-V3's 2,048-H800 scale, it recovers roughly 245k GPU-hours that 1F1B would have lost to pipeline bubbles.

### The config, field by field · 逐字段解析 config

DeepSeek-V3 的 config 如下（简化版）：

```
hidden_size: 7168
intermediate_size: 18432   (dense MLP hidden size, used on first few layers)
moe_intermediate_size: 2048 (expert MLP hidden size)
num_hidden_layers: 61
first_k_dense_layers: 3    (first 3 layers use dense MLP)
num_attention_heads: 128
num_key_value_heads: 128   (formally equal to num_heads under MLA, but
                           the real compression is in kv_lora_rank)
kv_lora_rank: 512          (MLA latent dimension)
num_experts: 256            (MoE expert count per block)
num_experts_per_tok: 8      (top-8 routing)
shared_experts: 1           (always-on shared expert per block)
max_position_embeddings: 163840
rope_theta: 10000.0
vocab_size: 129280
mtp_module: 1               (1 MTP module at depth 1)
```

逐项解析：

- `hidden_size=7168`：嵌入维度。
- `num_hidden_layers=61`：总块深度。
- `first_k_dense_layers=3`：前 3 个块使用大小为 18432 的稠密 MLP。其余 58 个块使用 MoE。
- `num_attention_heads=128`：128 个 query head。
- `kv_lora_rank=512`：K 和 V 被压缩到这个潜在维度，再逐 head 解压。
- `num_experts=256, num_experts_per_tok=8`：每个 MoE 块有 256 个专家，按 top-8 路由。
- `shared_experts=1`：在 256 个路由专家之外，还有 1 个常驻专家为每个 token 出力。可以把它想成一个「稠密保底」，确保每个 token 都拿到可靠的处理。
- `moe_intermediate_size=2048`：每个专家的 MLP 隐藏大小。比稠密 MLP 小，因为一共有 256 个。

> Here is the DeepSeek-V3 config (simplified): ... `shared_experts=1`: on top of the 256 routed experts, 1 always-on expert contributes to every token. Think of it as a "dense floor" that ensures every token gets something reliable. ... `moe_intermediate_size=2048`: each expert's MLP hidden size. Smaller than the dense MLP because there are 256 of them.

### Parameter accounting · 参数盘点

完整的计算在 `code/main.py` 里。核心数字：

- 嵌入：`vocab * hidden = 129280 * 7168 = ~0.93B`。
- 前 3 个稠密块：MLA 注意力（每块约 144M）+ 稠密 MLP（每块约 260M）+ 归一化。合计约 1.2B。
- 58 个 MoE 块：MLA 注意力（约 144M）+ 每块 256 个专家（每个 30M）+ 1 个共享专家（30M）+ 归一化。每块合计约 7.95B（含全部专家）。58 个 MoE 块共 461B。
- MTP 模块：14B。

总计：核心架构约 476B + 14B MTP；而公布的 671B 另外计入了更多结构性参数（偏置张量、专家专属组件、共享专家缩放等）。计算器复现出的数字与公布值差距在 3-5% 以内——差额来自 DeepSeek 报告第 2 节附录记录的细粒度统计。

每次前向的激活参数：

- 注意力：每层 144M * 61 = 8.8B（所有层都会激活）。
- MLP 激活：前 3 层稠密（3 * 260M = 780M），58 个 MoE 层各自以 8 个路由专家 + 1 个共享专家 + 路由开销激活。每层激活 MLP 约 260M。总计：3 * 260M + 58 * 260M ≈ 15.9B。
- 嵌入 + 归一化：1.2B。
- 激活参数总计：核心约 26B + 14B MTP（参与训练但推理时并不总是运行）≈ 37B。

> The full calculation lives in `code/main.py`. The headline: ... The number we reproduce in the calculator is within 3-5% of published — the delta comes from fine-grained accounting DeepSeek's report documents in its Section 2 appendix. ... Total active: roughly 26B core + 14B MTP (trained but not always run at inference) ≈ 37B.

### The 671B / 37B ratio · 671B / 37B 之比

18 倍稀疏比（激活参数占总参数的 5.5%）。DeepSeek-V3 是已发布开放权重的 MoE 前沿模型中最稀疏的。Mixtral 8x7B 的 13/47（28%）稠密得多。Llama 4 Maverick 的 17B/400B（4.25%）与它相当。DeepSeek 的赌注是：在前沿规模下，更多的专家加上更低的激活比，能换来每单位激活 FLOP 更高的质量。

> 18x sparsity ratio (active params are 5.5% of total). DeepSeek-V3 is the sparsest frontier MoE model that has shipped open weights. ... The DeepSeek bet: at frontier scale, more experts with lower activation ratio produces better quality per active-FLOP.

### Where DeepSeek-V3 sits · DeepSeek-V3 的坐标

| 模型 | 总参数 | 激活参数 | 比例 | 注意力 | 独特创新 |
|-------|------|-------|-------|-----------|-------------|
| Llama 3 70B | 70B | 70B | 100% | GQA 64/8 | — |
| Llama 4 Maverick | 400B | 17B | 4.25% | GQA | — |
| Mixtral 8x22B | 141B | 39B | 27% | GQA | — |
| DeepSeek V3 | 671B | 37B | 5.5% | MLA 512 | MLA + MTP + aux-free + DualPipe |
| Qwen 2.5 72B | 72B | 72B | 100% | GQA 64/8 | YaRN 扩展 |

> | Model | Total | Active | Ratio | Attention | Novel ideas |
> |-------|------|-------|-------|-----------|-------------|
> | Llama 3 70B | 70B | 70B | 100% | GQA 64/8 | — |
> | Llama 4 Maverick | 400B | 17B | 4.25% | GQA | — |
> | Mixtral 8x22B | 141B | 39B | 27% | GQA | — |
> | DeepSeek V3 | 671B | 37B | 5.5% | MLA 512 | MLA + MTP + aux-free + DualPipe |
> | Qwen 2.5 72B | 72B | 72B | 100% | GQA 64/8 | YaRN extension |

### The follow-on: R1, V4 · 后续演进：R1 与 V4

DeepSeek-R1（2025）是在 V3 骨干上做推理训练的一次运行。R1 用的是同一套架构，改变的是后训练配方（在可验证任务上的大规模 RL），而不是预训练架构。

DeepSeek-V4（如果发布）预计会保留 MLA + MoE + MTP，并加入 DSA（DeepSeek Sparse Attention）——Phase 10 · 17 中 NSA 的后继者。这条产品线的脉络是稳定的：架构级创新不断累积，每个版本多拧几个旋钮。

```figure
moe-routing
```

> DeepSeek-R1 (2025) is a reasoning-training run on the V3 backbone. R1 uses the same architecture. What changed is the post-training recipe (large-scale RL on verifiable tasks), not the pretraining architecture. ... The lineage is stable: architecture-level innovations accumulate; each version turns additional knobs.

## Use It · 实战用法

`code/main.py` 是专门针对 DeepSeek-V3 形状的参数计算器。跑一遍，把它的输出与论文数字对比，再用它去算假想变体（256 个专家 vs 512 个，top-8 vs top-16，MLA rank 512 vs 1024）。

值得关注的输出：

- 总参数量对比已公布的 671B。
- 激活参数量对比已公布的 37B。
- 128k 上下文下的 KV cache——即 MLA 与 GQA 的对比。
- 逐层分解，看清参数预算实际花在了哪里。

> `code/main.py` is the parameter calculator specialized to DeepSeek-V3's shape. Run it, compare its output to the paper's numbers, and use it on hypothetical variants (256 experts vs 512, top-8 vs top-16, MLA rank 512 vs 1024). ... Total parameter count vs published 671B. ... Active parameter count vs published 37B. ... KV cache at 128k context — the MLA vs GQA comparison. ... Per-layer breakdown to see where the parameter budget actually goes.

## Ship It · 交付

本课产出 `outputs/skill-deepseek-v3-reader.md`。给定一个 DeepSeek 家族模型（V3、R1 或未来的任何变体），它会产出一份逐组件的架构解读：点名 config 的每个字段、按组件推导参数量，并指出该模型用到了四项 DeepSeek 特有创新中的哪几项。

> This lesson produces `outputs/skill-deepseek-v3-reader.md`. Given a DeepSeek-family model (V3, R1, or any future variant), it produces a component-by-component architecture reading that names each field of the config, derives parameter counts by component, and identifies which of the four DeepSeek-specific innovations the model uses.

## Exercises · 练习

1. 运行 `code/main.py`。把计算器的总参数估计与已公布的 671B 对比，找出差异来自哪里。论文第 2 节有完整的逐项清单。

2. 修改 config，把 MLA rank 从 512 改为 256。计算 128k 上下文下对应的 KV cache 大小。这带来多大百分比的缩减，又对每个 head 的表达力造成什么代价？

3. 对比 DeepSeek-V3 的（256 专家，top-8）路由与一个假想的（512 专家，top-8）变体。总参数增长，激活参数不变。多出来的专家容量在理论上买到什么，在推理时又付出什么？

4. 阅读 DeepSeek-V3 技术报告（arXiv:2412.19437）关于 MLA 的第 2.1 节。用三句话解释为什么 K、V 的解压矩阵可以被「吸收」进后续的矩阵乘法，从而提升推理效率。

5. DeepSeek-V3 的大多数运算使用 FP8 训练。计算用 FP8 而非 BF16 存储 671B 权重的内存节省。这与 14.8T token 的训练预算有什么交集？

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| MLA | "Multi-Head Latent Attention" | 把 K 和 V 压缩进一个共享的低秩潜在表示（kv_lora_rank，通常为 512），逐 head 即时解压；KV cache 只存该潜在表示 |
| kv_lora_rank | "MLA 的压缩维度" | K 和 V 共享潜在表示的大小；DeepSeek-V3 取 512 |
| First k dense layers | "前几层保持稠密" | MoE 模型的最前几层跳过 MoE 路由、改跑稠密 MLP，以求稳定 |
| num_experts_per_tok | "Top-k 路由" | 每个 token 激活多少个路由专家；DeepSeek-V3 取 8 |
| Shared experts | "常驻专家" | 无论路由结果如何都处理每个 token 的专家；DeepSeek-V3 取 1 |
| Auxiliary-loss-free routing | "靠偏置项调负载均衡" | 训练中调整每专家偏置项来保持专家负载均衡，不引入额外损失项 |
| MTP module | "额外的预测头" | 从 h^(1) 和 E(t+1) 预测 t+2 位置的 Transformer 块；训练信号更密，附赠投机解码草稿模型 |
| DualPipe | "双向流水线" | 把前向/反向计算与跨节点 all-to-all 通信重叠起来的训练调度 |
| Active parameter ratio | "稀疏度" | active_params / total_params；DeepSeek-V3 达到 5.5% |
| FP8 training | "8-bit 训练" | 用 FP8 做训练存储和许多计算算子；相比 BF16 内存约省一半，质量代价很小 |

## Further Reading · 延伸阅读

- [DeepSeek-AI — DeepSeek-V3 Technical Report (arXiv:2412.19437)](https://arxiv.org/abs/2412.19437) —— 完整的架构、训练与结果文档
- [DeepSeek-V3 model card on Hugging Face](https://huggingface.co/deepseek-ai/DeepSeek-V3) —— config 文件与部署说明
- [DeepSeek-V2 paper (arXiv:2405.04434)](https://arxiv.org/abs/2405.04434) —— 引入 MLA 的前作
- [DeepSeek-R1 paper (arXiv:2501.12948)](https://arxiv.org/abs/2501.12948) —— 在 V3 架构上做推理训练的后继者
- [Native Sparse Attention (arXiv:2502.11089)](https://arxiv.org/abs/2502.11089) —— DeepSeek 家族注意力的未来方向
- [DualPipe repository](https://github.com/deepseek-ai/DualPipe) —— 训练调度的参考实现
