# Capstone 07 — End-to-End Fine-Tuning Pipeline (Data to SFT to DPO to Serve) · 端到端微调管线（数据到 SFT 到 DPO 到服务）

> 一个用你自己的数据训练的 8B 模型，按你自己的偏好做过 DPO 对齐，再量化、投机解码（speculative decoding），以可测量的 $/1M token 成本对外服务。2026 年的开源技术栈是 Axolotl v0.8、TRL 0.15、迭代用 Unsloth、量化用 GPTQ/AWQ/GGUF、服务用 vLLM 0.7 配 EAGLE-3。这个毕业项目（capstone）是把整条管线可复现地跑通 —— YAML 进，服务端点出 —— 并按 2026 Model Openness Framework 发布一张模型卡。

> An 8B model trained on your own data, DPO-aligned on your own preferences, quantized, speculative-decoded, and served at measurable $/1M tokens. The 2026 open stack is Axolotl v0.8, TRL 0.15, Unsloth for iteration, GPTQ/AWQ/GGUF for quantization, vLLM 0.7 with EAGLE-3 for serving. The capstone is to run the whole pipeline reproducibly — YAML in, served endpoint out — and publish a model card under the 2026 Model Openness Framework.

**类型（Type）:** 毕业项目（Capstone）
**语言（Languages）:** Python（管线），YAML（配置），Bash（脚本）
**先修（Prerequisites）:** Phase 2（ML）、Phase 3（DL）、Phase 7（transformers）、Phase 10（从零造 LLM）、Phase 11（LLM 工程）、Phase 17（基础设施）、Phase 18（安全）
**实践阶段（Phases exercised）:** P2 · P3 · P7 · P10 · P11 · P17 · P18
**时间（Time）:** 35 小时

## Problem · 问题

2026 年每个严肃的 AI 团队都常备一条微调管线。不是因为他们要发布前沿基座模型，而是因为下游适配 —— 领域 SFT、对标注偏好做 DPO、为投机解码蒸馏草稿模型、用 EAGLE-3 服务 —— 才是可测量收益所在。Axolotl v0.8 处理多 GPU SFT 配置。TRL 0.15 处理 DPO 和 GRPO。Unsloth 让你单 GPU 快速迭代。vLLM 0.7 配 EAGLE-3 把解码吞吐推高 2-3 倍而无质量损失。工具都能用；手艺在 YAML、数据卫生和评估纪律里。

你要把一个 8B 基座（Llama 3.3、Qwen3 或 Gemma 3）在任务专属数据上先 SFT 再 DPO，量化后服务，并用 lm-evaluation-harness、RewardBench-2、MT-Bench-v2 和 MMLU-Pro 测增益。你要按 2026 Model Openness Framework 产出一张模型卡。要点是可复现性 —— 一条命令端到端重跑整条管线。

> Every serious AI team in 2026 keeps a fine-tuning pipeline on tap. Not because they ship a frontier base model, but because downstream adaptation — domain SFT, DPO against labeled preferences, distilled drafts for speculative decoding, serving with EAGLE-3 — is where the measurable wins live. ... The tooling works; the craft is in the YAMLs, the data hygiene, and the eval discipline. ... You will run an 8B base (Llama 3.3, Qwen3, or Gemma 3) through SFT then DPO on task-specific data, quantize for serving, and measure gains against lm-evaluation-harness, RewardBench-2, MT-Bench-v2, and MMLU-Pro. You will produce a model card under the 2026 Model Openness Framework. The point is reproducibility — one command reruns the whole pipeline end to end.

## Concept · 概念

管线有五个阶段。**数据**：去重（MinHash / Datatrove）、质量过滤（Nemotron-CC 风格分类器）、PII 清洗、对照公开基准的切分卫生检查。**SFT**：Axolotl YAML，8xH100 上 ZeRO-3，cosine 调度，序列打包，2-3 个 epoch。**DPO 或 GRPO**：TRL 配置，1 个 epoch，偏好对来自人工标注或模型评审，调 beta。**量化**：GPTQ + AWQ + GGUF，服务部署灵活性。**服务**：vLLM 0.7 配 EAGLE-3 投机头（或 SGLang 配 SpecForge），K8s 部署，按排队等待时间做 HPA。

消融就是交付物：三个任务专属基准上的 SFT-only vs SFT+DPO vs SFT+GRPO。服务指标：batch 1 / 8 / 32 的 tokens/s、EAGLE-3 接受率、$/1M token。安全评估：Llama Guard 4 通过率。模型卡：偏见评估、可复现种子、数据许可。

> The pipeline has five stages. **Data**: dedup (MinHash / Datatrove), quality filter (Nemotron-CC style classifier), PII scrub, split-hygiene check against public benchmark contamination. **SFT**: Axolotl YAML, ZeRO-3 on 8xH100, cosine schedule, packed sequences, 2-3 epochs. **DPO or GRPO**: TRL config, 1 epoch, preference pairs either human-labeled or model-judged, beta tuning. **Quantize**: GPTQ + AWQ + GGUF for deployment flexibility. **Serve**: vLLM 0.7 with EAGLE-3 speculative heads (or SGLang with SpecForge), K8s deployment, HPA on queue-wait. ... Ablations are the deliverable: SFT-only vs SFT+DPO vs SFT+GRPO on three task-specific benchmarks. Serving metrics: tokens/s at batch 1 / 8 / 32, EAGLE-3 acceptance rate, $/1M tokens. Safety eval: Llama Guard 4 pass rate. Model card: bias evaluations, reproducibility seeds, data licensing.

## Architecture · 架构

```
raw data (HF datasets + internal)
    |
    v
Datatrove dedup + Nemotron-CC quality filter + PII scrub
    |
    v
split hygiene (MMLU-Pro contamination check)
    |
    v
Axolotl SFT config (YAML)  ---> 8xH100, ZeRO-3
    |
    v
TRL DPO / GRPO config       ---> 4xH100, 1 epoch
    |
    v
GPTQ + AWQ + GGUF quantize
    |
    v
vLLM 0.7 + EAGLE-3 speculative decoding
    |
    v
K8s deployment, HPA on queue-wait
    |
    v
lm-eval-harness + RewardBench-2 + MT-Bench-v2 + MMLU-Pro
    |
    v
model card (2026 MOF) + safety eval (Llama Guard 4)
```

## Stack · 技术栈

- 数据：Datatrove 去重，Nemotron-CC 分类器做质量，Presidio 做 PII
- 基座：Llama 3.3 8B、Qwen3 14B 或 Gemma 3 12B
- SFT：Axolotl v0.8 配 ZeRO-3、Flash Attention 3、序列打包
- 偏好调优：TRL 0.15 跑 DPO 或 GRPO；单 GPU 迭代用 Unsloth
- 量化：GPTQ（Marlin）、AWQ、GGUF（经 llama.cpp）
- 服务：vLLM 0.7 配 EAGLE-3 投机解码（或 SGLang 0.4 + SpecForge）
- 评估：lm-evaluation-harness、RewardBench-2、MT-Bench-v2、MMLU-Pro
- 安全评估：Llama Guard 4、ShieldGemma-2
- 基础设施：Kubernetes + NVIDIA device plugin，HPA 挂 queue-wait 指标
- 可观测性：训练用 W&B，推理用 Langfuse

> - Data: Datatrove for dedup, Nemotron-CC classifier for quality, Presidio for PII
> - Base: Llama 3.3 8B, Qwen3 14B, or Gemma 3 12B
> - SFT: Axolotl v0.8 with ZeRO-3, Flash Attention 3, packed sequences
> - Preference tuning: TRL 0.15 for DPO or GRPO; Unsloth for single-GPU iteration
> - Quantization: GPTQ (Marlin), AWQ, GGUF via llama.cpp
> - Serving: vLLM 0.7 with EAGLE-3 speculative decoding (or SGLang 0.4 + SpecForge)
> - Eval: lm-evaluation-harness, RewardBench-2, MT-Bench-v2, MMLU-Pro
> - Safety eval: Llama Guard 4, ShieldGemma-2
> - Infrastructure: Kubernetes + NVIDIA device plugin, HPA on queue-wait metric
> - Observability: W&B for training, Langfuse for inference

```figure
ce-finetune-stages
```

## Build It · 动手造

1. **数据管线。** 对原始语料跑 Datatrove 去重。应用 Nemotron-CC 风格质量分类器。Presidio 清洗 PII。用显式种子写 train/val 切分。

2. **污染检查。** 对每个验证切分，对 MMLU-Pro、MT-Bench-v2、RewardBench-2 测试集算 MinHash。任何重叠都拒绝。

3. **Axolotl SFT。** YAML 配 ZeRO-3、FA3、序列打包。8xH100 上 2-3 个 epoch。记录到 W&B。

4. **TRL DPO / GRPO。** 拿 SFT checkpoint，在偏好对上跑一个 epoch 的 DPO（或在数学/代码上跑带可验证奖励的 GRPO）。扫 beta。

5. **量化。** 产出三种量化：GPTQ-INT4-Marlin、AWQ-INT4、GGUF-Q4_K_M（供 llama.cpp）。记录大小与标称吞吐。

6. **带投机解码的服务。** vLLM 0.7 配经 Red Hat Speculators 训练的 EAGLE-3 草稿头。测 batch 1 / 8 / 32 下的接受率与尾延迟。报告在同一评估上对比 Anthropic / OpenAI 的 $/1M token。

7. **评估矩阵。** 在 base、SFT-only、SFT+DPO、SFT+GRPO 上跑 lm-eval-harness、RewardBench-2、MT-Bench-v2、MMLU-Pro。产出一表。

8. **安全评估。** Llama Guard 4 在开发集上的通过率。ShieldGemma-2 输出过滤器。

9. **模型卡。** MOF 2026 模板：数据、训练、评估、安全、许可，以及带 YAML 与 commit SHA 的可复现性章节。

> **Data pipeline.** Run Datatrove dedup on raw corpus. Apply Nemotron-CC-style quality classifier. Presidio scrubs PII. Write train/val splits with explicit seed. ... **Contamination check.** For every validation split, compute MinHash against MMLU-Pro, MT-Bench-v2, RewardBench-2 test sets. Reject any overlap. ... **Axolotl SFT.** YAML with ZeRO-3, FA3, sequence packing. 2-3 epochs on 8xH100. Log to W&B. ... **Serve with speculative decoding.** vLLM 0.7 config with EAGLE-3 draft heads trained via Red Hat Speculators. Measure acceptance rate and tail latency at batch 1 / 8 / 32. Report $/1M tokens vs Anthropic / OpenAI on the same eval. ... **Model card.** MOF 2026 template: data, training, eval, safety, license, reproducibility section with YAMLs and commit SHAs.

## Use It · 实战用法

```
$ ./pipeline.sh config/llama3.3-8b-domainX.yaml
[data]    300k deduped, 12k filtered, 280k accepted (seed=7)
[SFT]     3 epochs, 8xH100, 6h12m, val loss 1.42 -> 1.03
[DPO]     1 epoch, beta=0.08, 4xH100, 1h40m
[quant]   GPTQ-INT4 4.6 GB, AWQ-INT4 4.8 GB, GGUF-Q4_K_M 5.1 GB
[serve]   vLLM 0.7, EAGLE-3 acceptance 0.74, p99 126ms @ bs=8
[eval]    MMLU-Pro +3.2, MT-Bench-v2 +0.41, RewardBench-2 +0.08
[card]    model-card.md generated under 2026 MOF
```

## Ship It · 交付

`outputs/skill-finetuning-pipeline.md` 描述了交付物。一条命令把数据送过 SFT、DPO、量化、服务、评估，并产出一张模型卡 + 服务端点。

| 权重 | 标准 | 如何衡量 |
|:-:|---|---|
| 25 | 相对基座的评估增益 | 目标任务上的实测增益（MMLU-Pro、MT-Bench-v2、任务专属） |
| 20 | 管线可复现性 | 相同种子一条命令端到端重跑 |
| 20 | 数据卫生 | 去重率、PII 清洗覆盖率、污染检查绿灯 |
| 20 | 服务效率 | bs=1/8/32 的 tokens/s、EAGLE-3 接受率、$/1M token |
| 15 | 模型卡 + 安全评估 | 2026 MOF 完整度 + Llama Guard 4 通过率 |
| **100** | | |

> `outputs/skill-finetuning-pipeline.md` describes the deliverable. A single command runs data through SFT through DPO through quant through serve through eval, and emits a model card + the served endpoint.

## Exercises · 练习

1. 在同一任务专属基准上跑 SFT-only vs SFT+DPO vs SFT+GRPO。报告哪种偏好方法赢、赢多少。

2. 把 Llama 3.3 8B 换成 Qwen3 14B。测同等质量下的 $/1M token。

3. 测 EAGLE-3 在领域数据与通用 ShareGPT 上的接受率。报告差值及其对延迟预算的意义。

4. 注入 1% 污染（把 MMLU-Pro 答案泄进训练数据）并重跑评估。看着 MMLU-Pro 准确率不真实地跳涨。建一个能抓住它的污染检查 CI 门。

5. 加 LoRA SFT 作为全量微调的替代。测内存低 10 倍时的质量差距。

> Run SFT-only vs SFT+DPO vs SFT+GRPO on the same task-specific benchmark. Report which preference method wins and by how much. ... Swap Llama 3.3 8B for Qwen3 14B. Measure the $/1M tokens at matched quality. ... Measure EAGLE-3 acceptance rate on domain data vs generic ShareGPT. Report the delta and what it means for latency budgets. ... Inject 1% of contamination (leak MMLU-Pro answers into training data) and rerun eval. Watch MMLU-Pro accuracy jump unrealistically. Build a contamination-check CI gate that catches this. ... Add LoRA SFT as an alternative to full fine-tune. Measure the quality gap at 10x lower memory.

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|------------------------|
| Axolotl | 「SFT 训练器」 | 统一的 YAML 驱动训练器：SFT、DPO、蒸馏 |
| TRL | 「偏好调优器」 | Hugging Face 的 LLM DPO、GRPO、PPO 库 |
| GRPO | 「组相对策略优化」 | DeepSeek R1 的 RL 配方，用可验证奖励 |
| EAGLE-3 | 「投机解码草稿」 | 预测前方 N 个 token 的草稿头；vLLM 用目标模型验证 |
| MOF | 「Model Openness Framework」 | 2026 年对模型发布在数据、代码、许可上分级的标准 |
| Contamination check（污染检查） | 「切分卫生」 | 基于 MinHash 检测测试集泄漏进训练 |
| Acceptance rate（接受率） | 「EAGLE / MTP 指标」 | 草稿 token 被目标模型接受的比例 |

## Further Reading · 延伸阅读

- [Axolotl documentation](https://axolotl-ai-cloud.github.io/axolotl/) — 参考 SFT / DPO 训练器
- [TRL documentation](https://huggingface.co/docs/trl) — DPO 与 GRPO 参考实现
- [Unsloth](https://github.com/unslothai/unsloth) — 单 GPU 迭代参考
- [DeepSeek R1 paper (arXiv:2501.12948)](https://arxiv.org/abs/2501.12948) — GRPO 方法论
- [vLLM + EAGLE-3 documentation](https://docs.vllm.ai) — 参考服务栈
- [SGLang SpecForge](https://github.com/sgl-project/SpecForge) — 备选投机解码训练器
- [Model Openness Framework 2026](https://isocpp.org/) — 开源发布分级标准
- [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) — 权威评估运行器
