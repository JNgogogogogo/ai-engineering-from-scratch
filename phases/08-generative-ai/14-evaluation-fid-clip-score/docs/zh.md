# Evaluation — FID, CLIP Score, Human Preference · 评测 —— FID、CLIP score 与人类偏好

每个生成模型排行榜都会引用 FID、CLIP score，以及人类偏好竞技场的胜率。每个数字都有一种失效模式，较真的研究者可以拿它刷分。如果你不知道这些失效模式，你就分不清真实提升和刷分。

> Every generative model leaderboard cites FID, CLIP score, and a win rate from a human-preference arena. Each number has a failure mode a determined researcher can game. If you do not know the failure modes, you cannot tell a real improvement from a gaming run.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 8 · 01 (Taxonomy), Phase 2 · 04 (Evaluation Metrics)
**Time:** ~45 minutes

## The Problem · 问题在哪

生成模型要在*样本质量*和*条件遵从度*两方面接受评审。两者都没有闭式度量。你的模型得渲染 10,000 张图像；得有东西给它们打分；你还得相信这些分数跨模型家族、跨分辨率、跨架构都可比。三个度量挺过了 2014-2026 的洗礼：

- **FID（Fréchet Inception Distance）。** 在 Inception 网络的特征空间里，度量两个分布 —— 真实分布与生成分布 —— 之间的距离。越低越好。
- **CLIP score。** 生成图像的 CLIP 图像嵌入与提示的 CLIP 文本嵌入之间的余弦相似度。越高越好。度量提示遵从度。
- **人类偏好。** 让两个模型在同一个提示上正面对决，由人类（或 GPT-4 级模型）挑出更好的那个，聚合为 Elo 分。

你还会见到：IS（inception score，基本退役）、KID、CMMD、ImageReward、PickScore、HPSv2、MJHQ-30k。每一个都是对前一个某种失效的修正。

> A generative model is judged on *sample quality* and *conditioning adherence*. Neither has a closed-form measure. Your model has to render 10,000 images; something has to assign them numbers; you have to trust the numbers across model families, across resolutions, across architectures. Three metrics survived the 2014-2026 gauntlet:
> - **FID (Fréchet Inception Distance).** A distance between two distributions — real and generated — in an Inception network's feature space. Lower is better. ...
> - **CLIP score.** Cosine similarity between a generated image's CLIP-image embedding and a prompt's CLIP-text embedding. Higher is better. Measures prompt adherence. ...
> - **Human preference.** Pit two models head-to-head on the same prompt, have humans (or a GPT-4-class model) pick the better one, aggregate to an Elo score.
> You will also see: IS (inception score, largely retired), KID, CMMD, ImageReward, PickScore, HPSv2, MJHQ-30k. Each corrects for one failure of the previous.

## The Concept · 概念

![FID、CLIP 与偏好：三条轴，不同的失效模式](../assets/evaluation.svg)

### FID — sample quality · FID —— 样本质量

Heusel et al.（2017）。步骤：

1. 对 N 张真实图像和 N 张生成图像提取 Inception-v3 特征（2048 维）。
2. 对每个池拟合高斯：计算均值 `μ_r, μ_g` 和协方差 `Σ_r, Σ_g`。
3. FID = `||μ_r - μ_g||² + Tr(Σ_r + Σ_g - 2 · (Σ_r · Σ_g)^0.5)`。

解释：特征空间中两个多元高斯之间的 Fréchet 距离。越低 = 分布越相似。

失效模式：
- **小 N 下有偏。** FID 是对特征分布的均方量 —— 小 N 会低估协方差，给出虚假的低 FID。永远用 N ≥ 10,000。
- **依赖 Inception。** Inception-v3 是在 ImageNet 上训练的。离 ImageNet 远的领域（人脸、艺术、文字图像）算出的 FID 没有意义。用领域专属的特征提取器。
- **可被刷分。** 过拟合 Inception 先验，可以在视觉质量毫无提升的情况下拿到低 FID。CMMD（见下）就是来治它的。

> Heusel et al. (2017). Steps:
> 1. Extract Inception-v3 features (2048-D) for N real images and N generated. ...
> 2. Fit a Gaussian to each pool: compute mean `μ_r, μ_g` and covariance `Σ_r, Σ_g`. ...
> 3. FID = `||μ_r - μ_g||² + Tr(Σ_r + Σ_g - 2 · (Σ_r · Σ_g)^0.5)`.
> Interpretation: Fréchet distance between two multivariate Gaussians in feature space. Lower = more similar distributions.
> Failure modes:
> - **Biased on small N.** FID is mean-squared over the feature distribution — small N under-estimates covariance, gives falsely low FID. Always use N ≥ 10,000. ...
> - **Inception-dependent.** Inception-v3 was trained on ImageNet. Domains far from ImageNet (faces, art, text images) produce meaningless FID. Use a domain-specific feature extractor. ...
> - **Gaming.** Overfitting to the Inception prior gives low FID without visual quality improvement. Beat it with CMMD (below).

### CLIP score — prompt adherence · CLIP score —— 提示遵从度

Radford et al.（2021）。对一张生成图像 + 提示：

```
clip_score = cos_sim( CLIP_image(x_gen), CLIP_text(prompt) )
```

在 30k 张生成图像上取平均 → 一个可以在模型之间比较的标量。

失效模式：
- **CLIP 自己的盲区。** CLIP 的组合推理很弱（「蓝色球体上的红色立方体」经常失败）。模型可以在 CLIP score 上排名靠前，却不真正遵循复杂提示。
- **短提示偏差。** 短提示在真实场景里有更多 CLIP 图像匹配。更长的提示机械地拿到更低的 CLIP 分数。
- **提示刷分。** 在提示里塞进「high quality, 4k, masterpiece」，可以在不改善图文绑定的情况下抬高 CLIP score。

CMMD（Jayasumana et al., 2024）修正了其中一些：用 CLIP 特征代替 Inception，用最大均值差异（maximum-mean discrepancy）代替 Fréchet 距离。对细微的质量差异更敏感。

> Radford et al. (2021). For a generated image + prompt:
> Average across 30k generated images → a scalar comparable between models.
> Failure modes:
> - **CLIP's own blind spots.** CLIP has weak compositional reasoning ("a red cube on a blue sphere" often fails). Models can rank well on CLIP score without really following complex prompts. ...
> - **Short prompt bias.** Short prompts have more CLIP-image matches in the wild. Longer prompts have lower CLIP scores mechanically. ...
> - **Prompt gaming.** Including "high quality, 4k, masterpiece" in the prompt inflates CLIP score without improving image-text binding.
> CMMD (Jayasumana et al., 2024) fixes some of these: uses CLIP features instead of Inception, maximum-mean discrepancy instead of Fréchet. Better at detecting subtle quality differences.

### Human preference — the ground truth · 人类偏好 —— 真值

选一个提示池。用模型 A 和模型 B 各自生成。把配对展示给人类（或一个强 LLM 评审）。把胜负聚合成 Elo 或 Bradley-Terry 分。基准：

- **PartiPrompts（Google）**：1,600 个多样化提示，12 个类别。
- **HPSv2**：107k 条人类标注，被广泛用作自动化代理。
- **ImageReward**：137k 个提示-图像偏好对，MIT 许可。
- **PickScore**：在 Pick-a-Pic 的 2.6M 条偏好上训练。
- **Chatbot-Arena 风格的图像竞技场**：https://imagearena.ai/ 等。

失效模式：
- **评审方差。** 非专家与专家的偏好不同。两者都要用。
- **提示分布。** 精挑过的提示会偏袒某一个模型家族。永远写清楚。
- **LLM 评审的奖励劫持。** GPT-4 评审会被「好看但错误」的输出骗过。要用人类做三角验证。

> Pick a pool of prompts. Generate with model A and model B. Show pairs to humans (or a strong LLM judge). Aggregate wins into an Elo or Bradley-Terry score. Benchmarks:
> - **PartiPrompts (Google)**: 1,600 diverse prompts, 12 categories. ...
> - **HPSv2**: 107k human annotations, widely used as automated proxy. ...
> - **ImageReward**: 137k prompt-image preference pairs, MIT-licensed. ...
> - **PickScore**: trained on Pick-a-Pic 2.6M preferences. ...
> - **Chatbot-Arena-style image arenas**: https://imagearena.ai/ and others.
> Failure modes:
> - **Judge variance.** Non-experts have different preferences than experts. Use both. ...
> - **Prompt distribution.** Cherry-picked prompts favor one family. Always document. ...
> - **LLM-judge reward hacking.** GPT-4-judge gets fooled by pretty-but-wrong outputs. Triangulate with human.

## Use together · 组合使用

一份生产级评测报告应包含：

1. 在 10-30k 样本上、相对留出的真实分布算 FID（样本质量）。
2. 在同批样本上、相对各自提示算 CLIP score / CMMD（遵从度）。
3. 与上一代模型在盲测竞技场中的胜率（整体偏好）。
4. 失效模式分析：随机抽 50 个输出，标记已知问题（手部解剖、文字渲染、物体数量一致性）。

任何单一度量都是谎言。三个互相印证的度量 + 定性审查，才算一个主张。

> A production eval report should include:
> 1. FID on 10-30k samples against a held-out real distribution (sample quality). ...
> 2. CLIP score / CMMD on the same samples vs their prompts (adherence). ...
> 3. Win rate in a blinded arena vs the previous model (overall preference). ...
> 4. Failure mode analysis: 50 randomly sampled outputs, flagged for known issues (hand anatomy, text rendering, consistent object count).
> Any single metric is a lie. Three corroborating metrics + qualitative review are a claim.

```figure
gx-fid-distributions
```

## Build It · 动手造

`code/main.py` 在合成「特征向量」上实现 FID、类 CLIP score 和 Elo 聚合（我们用 4 维向量充当 Inception 特征的替身）。你会看到：

- 小 N 和大 N 下的 FID 计算 —— 那个偏差。
- 作为特征池之间余弦相似度的「CLIP score」。
- 来自合成偏好流的 Elo 更新规则。

> `code/main.py` implements FID, CLIP-score-like, and Elo aggregation on synthetic "feature vectors" (we use 4-D vectors as stand-ins for Inception features). You see:
> - FID computation on a small N and on a large N — the bias. ...
> - "CLIP score" as cosine similarity between feature pools. ...
> - Elo update rule from a synthetic preference stream.

### Step 1: FID in four lines · 第 1 步：四行 FID

```python
def fid(real_features, gen_features):
    mu_r, cov_r = mean_and_cov(real_features)
    mu_g, cov_g = mean_and_cov(gen_features)
    mean_diff = sum((a - b) ** 2 for a, b in zip(mu_r, mu_g))
    trace_term = trace(cov_r) + trace(cov_g) - 2 * sqrt_cov_product(cov_r, cov_g)
    return mean_diff + trace_term
```

### Step 2: CLIP-style cosine-similarity · 第 2 步：CLIP 式余弦相似度

```python
def clip_like(image_feat, text_feat):
    dot = sum(a * b for a, b in zip(image_feat, text_feat))
    norm = math.sqrt(dot_self(image_feat) * dot_self(text_feat))
    return dot / max(norm, 1e-8)
```

### Step 3: Elo aggregation · 第 3 步：Elo 聚合

```python
def elo_update(r_a, r_b, winner, k=32):
    expected_a = 1 / (1 + 10 ** ((r_b - r_a) / 400))
    actual_a = 1.0 if winner == "a" else 0.0
    r_a_new = r_a + k * (actual_a - expected_a)
    r_b_new = r_b - k * (actual_a - expected_a)
    return r_a_new, r_b_new
```

## Pitfalls · 常见坑

- **N=1000 的 FID。** N 低于 1 万时这个启发式不可靠。报告低 N FID 的论文是在刷分。
- **跨分辨率比较 FID。** Inception 的 299×299 缩放会改变特征分布。只在分辨率对齐时比较。
- **只报一个种子。** 最少跑 3 个种子。报告标准差。
- **用负向提示抬高 CLIP score。** 有些流水线靠过拟合提示来抬 CLIP。检查是否存在视觉饱和。
- **提示重叠导致的 Elo 偏差。** 如果两个模型在训练里都见过某个基准提示，Elo 就没有意义。用留出提示集。
- **人类评测的付费众包偏差。** Prolific、MTurk 标注员偏年轻 / 科技友好。混入招募来的艺术 / 设计专家。

> **FID at N=1000.** Heuristic is unreliable under N=10k. Papers reporting low-N FID are gaming. ...
> **Comparing FID across resolutions.** Inception's 299×299 resize changes the feature distribution. Compare at matched resolution only. ...
> **Elo bias from prompt overlap.** If both models saw a benchmark prompt during training, Elo is meaningless. Use held-out prompt sets. ...
> **Human eval paid-crowd skew.** Prolific, MTurk annotators skew younger / tech-friendly. Mix with recruited art/design experts.

## Use It · 实战用法

2026 年的生产评测协议：

| 支柱 | 最低要求 | 推荐配置 |
|--------|---------|-------------|
| 样本质量 | 10k 样本对留出真实分布的 FID | + 5k 的 CMMD + 按类别子集的 FID |
| 提示遵从 | 30k 上的 CLIP score | + HPSv2 + ImageReward + VQA 式问答 |
| 偏好 | 对基线的 200 个盲测配对 | + 2000 个配对人类 + LLM 评审 + Chatbot Arena |
| 失效分析 | 50 个人工标记 | 500 个人工标记 + 自动安全分类器 |

四根支柱都在同一份报告里 = 主张。只有任何一根 = 营销。

> Production eval protocol in 2026:
> All four pillars in one report = claim. Any one alone = marketing.

## Ship It · 交付

保存 `outputs/skill-eval-report.md`。这个 skill 接收新模型 checkpoint + 基线，输出完整的评测计划：样本量、度量、失效模式探针、签收标准。

> Save `outputs/skill-eval-report.md`. Skill takes a new model checkpoint + baseline and outputs a full eval plan: sample sizes, metrics, failure-mode probes, sign-off criteria.

## Exercises · 练习

1. **简单。** 跑 `code/main.py`。在同样的合成分布上比较 N=100 与 N=1000 的 FID。报告偏差幅度。
2. **中等。** 从合成的 CLIP 风格特征实现 CMMD（公式见 Jayasumana et al., 2024）。比较它与 FID 对质量差异的敏感度。
3. **困难。** 复刻 HPSv2 的设置：从 Pick-a-Pic 的一个子集取 1000 个图像-提示对，微调一个小的基于 CLIP 的打分器，测它与留出集的一致度。

> 1. **Easy.** Run `code/main.py`. Compare FID at N=100 vs N=1000 on the same synthetic distributions. Report bias magnitude. ...
> 2. **Medium.** Implement CMMD from synthetic CLIP-style features (see Jayasumana et al., 2024 for the formula). Compare sensitivity to quality differences vs FID. ...
> 3. **Hard.** Replicate the HPSv2 setup: take 1000 image-prompt pairs from a subset of Pick-a-Pic, fine-tune a small CLIP-based scorer on the preferences, and measure its agreement with a held-out set.

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| FID | "Fréchet Inception Distance" | 真实 vs 生成 Inception 特征的高斯拟合之间的 Fréchet 距离。 |
| CLIP score | "图文相似度" | CLIP 图像嵌入与文本嵌入之间的余弦相似度。 |
| CMMD | "FID 的替代品" | CLIP 特征上的 MMD；偏差更小，无高斯假设。 |
| IS | "Inception score" | Exp KL(p(y|x) || p(y))；在现代模型上相关性差，已退役。 |
| HPSv2 / ImageReward / PickScore | "学出来的偏好代理" | 在人类偏好上训练的小模型；用作自动评审。 |
| Elo | "国际象棋等级分" | 成对胜负的 Bradley-Terry 聚合。 |
| PartiPrompts | "基准提示集" | Google 策展的 1,600 个提示，覆盖 12 个类别。 |
| FD-DINO | "自监督替代品" | 用 DINOv2 特征的 FD；对 ImageNet 之外的领域更好。 |

## Production note: evaluation is an inference workload too · 生产备注：评测也是一种推理负载

对 10k 样本跑 FID，意味着要生成 10k 张图。对一个 50 步的 SDXL base，在单卡 L4 上出 1024²，那是约 11 小时的单请求推理。评测预算是真金白银，而且这个场景恰恰就是离线推理（最大化吞吐、无视 TTFT）：

- **大胆批处理，忘掉延迟。** 离线评测 = 在显存放得下的最大尺寸上做静态批处理。在 80GB H100 上用 `num_images_per_prompt=8` 跑 `pipe(...).images`，墙钟时间比单请求快 4-6 倍。
- **缓存真实特征。** 对真实参考集做 Inception（FID）或 CLIP（CLIP score、CMMD）特征提取只跑*一次*，存成 `.npz`。不要每次评测都重算。

CI / 回归门禁：每个 PR 在 500 样本子集上跑 FID + CLIP score（约 30 分钟）；每晚跑完整 10k FID + HPSv2 + Elo。

> Running FID on 10k samples means generating 10k images. For a 50-step SDXL base at 1024² on a single L4, that is ~11 hours of single-request inference. Evaluation budgets are real, and the framing is exactly the offline-inference scenario (maximize throughput, ignore TTFT):
> - **Batch hard, forget latency.** Offline eval = static batching at the largest size that fits in memory. `pipe(...).images` with `num_images_per_prompt=8` on an 80GB H100 runs 4-6× faster wall-clock than single-request. ...
> - **Cache the real features.** The Inception (FID) or CLIP (CLIP-score, CMMD) feature extraction over the real reference set is run *once*, stored as a `.npz`. Do not recompute per eval.
> For CI / regression gates: run FID + CLIP score on a 500-sample subset per PR (~30 min); run full 10k FID + HPSv2 + Elo nightly.

## Further Reading · 延伸阅读

- [Heusel et al. (2017). GANs Trained by a Two Time-Scale Update Rule Converge to a Local Nash Equilibrium (FID)](https://arxiv.org/abs/1706.08500) —— FID 论文。
- [Jayasumana et al. (2024). Rethinking FID: Towards a Better Evaluation Metric for Image Generation (CMMD)](https://arxiv.org/abs/2401.09603) —— CMMD。
- [Radford et al. (2021). Learning Transferable Visual Models from Natural Language Supervision (CLIP)](https://arxiv.org/abs/2103.00020) —— CLIP。
- [Wu et al. (2023). HPSv2: A Comprehensive Human Preference Score](https://arxiv.org/abs/2306.09341) —— HPSv2。
- [Xu et al. (2023). ImageReward: Learning and Evaluating Human Preferences for Text-to-Image Generation](https://arxiv.org/abs/2304.05977) —— ImageReward。
- [Yu et al. (2023). Scaling Autoregressive Models for Content-Rich Text-to-Image Generation (Parti + PartiPrompts)](https://arxiv.org/abs/2206.10789) —— PartiPrompts。
- [Stein et al. (2023). Exposing flaws of generative model evaluation metrics](https://arxiv.org/abs/2306.04675) —— 失效模式综述。
