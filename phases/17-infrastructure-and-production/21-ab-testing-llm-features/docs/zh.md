# A/B Testing LLM Features — GrowthBook, Statsig, and the Vibes Problem · LLM 功能 A/B 测试 —— GrowthBook、Statsig 与「凭感觉」问题

> 传统的 A/B 测试不是为非确定性的 LLM 设计的。关键区分：评测（evals）回答「模型能不能干这活？」A/B 测试回答「用户在不在乎？」两者都需要；靠「感觉不错」就上线的日子结束了。2026 年要测的东西：提示工程（措辞）、模型选择（GPT-4 vs GPT-3.5 vs 开源；准确率 vs 成本 vs 延迟）、生成参数（temperature、top-p）。真实案例：一个聊天机器人奖励模型变体带来了会话时长 +70%、留存 +30%；Nextdoor 的 AI 主题行实验在打磨奖励函数后带来 CTR +1%；可汗学院的 Khanmigo 在延迟 vs 数学准确率的轴上迭代。平台格局：**Statsig**（2025 年 9 月被 OpenAI 以 $1.1B 收购）——序贯检验、CUPED、一体化。**GrowthBook**——开源、仓库原生（warehouse-native）、贝叶斯 + 频率派 + 序贯引擎、CUPED、SRM 检查、Benjamini-Hochberg + Bonferroni 校正。选哪家取决于你的仓库-SQL 偏好，以及「被 OpenAI 收购」对你的组织是否重要。

> Traditional A/B testing was not built for non-deterministic LLMs. The critical distinction: evals answer "can the model do the job?" A/B tests answer "do users care?" Both are required; shipping on vibe checks is over. What to test in 2026: prompt engineering (wording), model selection (GPT-4 vs GPT-3.5 vs OSS; accuracy vs cost vs latency), generation parameters (temperature, top-p). Real cases: a chatbot reward-model variant delivered +70% conversation length and +30% retention; Nextdoor AI subject-line experiments delivered +1% CTR after reward-function refinement; Khan Academy Khanmigo iterated on a latency-vs-math-accuracy axis. Platform split: **Statsig** (acquired by OpenAI for $1.1B in September 2025) — sequential testing, CUPED, all-in-one. **GrowthBook** — open-source, warehouse-native, Bayesian + Frequentist + Sequential engines, CUPED, SRM checks, Benjamini-Hochberg + Bonferroni corrections. You pick based on warehouse-SQL preference and whether "acquired by OpenAI" matters to your organization.

**Type:** Learn
**Languages:** Python (stdlib, toy sequential test simulator)
**Prerequisites:** Phase 17 · 13 (Observability), Phase 17 · 20 (Progressive Deployment)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 区分评测（「模型能不能干这活」）与 A/B 测试（「用户在不在乎」）。
- 列出三个可测的轴（提示、模型、参数），并为每个轴选出合适的指标。
- 解释 CUPED、序贯检验和 Benjamini-Hochberg 多重比较校正。
- 根据仓库-SQL 姿态和公司对收购的立场，在 Statsig 和 GrowthBook 之间做选择。

> Distinguish evals ("can the model do the job") from A/B tests ("do users care").
> Enumerate three testable axes (prompt, model, parameters) and pick the metric for each.
> Explain CUPED, sequential testing, and Benjamini-Hochberg multiple-comparison corrections.
> Pick Statsig or GrowthBook based on warehouse-SQL posture and corporate acquisition stance.

## The Problem · 问题在哪

你手工调了一条系统提示。感觉更好。你上线了。转化率的变化在噪声以内。你怪指标。或者你上线了一个新模型，转化没动——是模型退化了，还是变化小到测不出来？你不知道，因为你没做 A/B 就上线了。

评测回答的是模型能否在标注集上完成任务。它不回答用户是否更喜欢输出。只有受控的在线实验能回答后者，而且前提是实验有足够的统计功效、控制了非确定性、并对多重比较做了校正。

> You hand-tuned a system prompt. It feels better. You ship it. Conversion changes by noise. You blame the metric. Or you shipped a new model and conversion didn't move — did the model degrade or was the change too small to detect? You don't know, because you shipped without an A/B.
> Evals answer whether the model can do a task on a labeled set. They do not answer whether users prefer the output. Only a controlled online experiment answers that, and only if the experiment has enough power, controls for non-determinism, and corrects for multiple comparisons.

## The Concept · 概念

### Evals vs A/B tests · 评测 vs A/B 测试

**评测（Evals）** —— 离线，标注集，评审（评分细则、LLM-as-judge 或人工）。回答：「在这个固定分布上，输出是否正确 / 有用 / 安全？」

**A/B 测试** —— 在线，真实用户，随机化。回答：「新变体是否移动了真正要紧的用户级指标？」

两者都需要。评测在曝光前抓住回退；A/B 在之后确认产品影响。

> **Evals** — offline, labeled set, judge (rubric or LLM-as-judge or human). Answer: "Is the output correct / helpful / safe on this fixed distribution?"
> **A/B test** — online, live users, randomized. Answer: "Does the new variant move the user-level metric that matters?"
> Both required. Evals catch regressions before exposure; A/B confirms product impact after.

### What to test · 测什么

1. **提示工程** —— 措辞、系统提示结构、示例。指标：任务成功率、用户留存、每请求成本。
2. **模型选择** —— GPT-4 vs GPT-3.5-Turbo vs Llama-OSS。指标：准确率（任务）+ 每请求成本 + 延迟 P99。多目标。
3. **生成参数** —— temperature、top-p、max_tokens。指标：任务特定（输出多样性 vs 确定性）。

> 1. **Prompt engineering** — wording, system-prompt structure, examples. Metric: task success, user retention, cost/request.
> 2. **Model selection** — GPT-4 vs GPT-3.5-Turbo vs Llama-OSS. Metric: accuracy (task) + cost/request + latency P99. Multi-objective.
> 3. **Generation parameters** — temperature, top-p, max_tokens. Metric: task-specific (output diversity vs determinism).

### CUPED — variance reduction · CUPED —— 方差缩减

Controlled-experiments Using Pre-Experiment Data（用实验前数据做受控实验）。在比较实验后数据之前，先把实验前时段的方差回归掉。典型方差缩减：30-70%。有效样本量免费上升。

实现：Statsig 和 GrowthBook 都有。

> Controlled-experiments Using Pre-Experiment Data. Regress out pre-period variance before comparing post-period. Typical variance reduction: 30-70%. Effective sample size goes up for free.
> Implementation: both Statsig and GrowthBook implement.

### Sequential testing · 序贯检验

经典 A/B 假设固定样本量。序贯检验（「边看边决定」）在反复查看下控制假阳性率。始终有效（always-valid）的序贯程序（mSPRT、Howard 置信序列）让你见到明显赢家就可以提前停。

> Classical A/B assumes fixed sample size. Sequential tests ("peek-and-decide") control false-positive rate under repeated looks. Always-valid sequential procedures (mSPRT, Howard's confidence sequences) let you stop early on clear winners.

### Multiple-comparison corrections · 多重比较校正

以 95% 置信度跑 20 个 A/B 测试，光凭运气就会出一个假阳性。Bonferroni 校正收紧每个检验的 α；Benjamini-Hochberg 控制错误发现率（false-discovery rate）。GrowthBook 两者都实现了。

> Running 20 A/B tests at 95% confidence produces one false positive by chance. Bonferroni correction tightens α per-test; Benjamini-Hochberg controls false-discovery rate. GrowthBook implements both.

### SRM — sample ratio mismatch · SRM —— 样本比例失配

分配哈希把用户随机分到各变体。如果 50/50 的 split 实际跑出了 47/53，说明哪里坏了——SRM 检查会把它标出来。两个平台都实现了。

> Assignment hash randomizes users to variants. If 50/50 split delivers 47/53, something is broken — SRM check flags it. Both platforms implement.

### Statsig vs GrowthBook · Statsig 与 GrowthBook

**Statsig**：
- 2025 年 9 月被 OpenAI 以 $1.1B 收购。托管、SaaS。
- 序贯检验、CUPED、held-out 群体。
- 一体化：feature flags + 实验平台 + 可观测性。
- 最适合：团队本来就想要打包产品、且不在乎 OpenAI 所有权的。

**GrowthBook**：
- 开源（MIT）；仓库原生（warehouse-native，直接读 Snowflake/BigQuery/Redshift）。
- 多引擎：贝叶斯、频率派、序贯。
- CUPED、SRM、Bonferroni、BH 校正。
- 自托管或托管云。
- 最适合：仓库-SQL 型团队、数据团队掌控指标层、想要开源的。

> **Statsig**: Acquired by OpenAI for $1.1B (September 2025). Hosted, SaaS. Sequential testing, CUPED, held-out populations. All-in-one: feature flags + experimentation + observability. Best fit: team already wants a bundled product, doesn't care about OpenAI ownership.
> **GrowthBook**: Open-source (MIT); warehouse-native (reads from Snowflake/BigQuery/Redshift directly). Multiple engines: Bayesian, Frequentist, Sequential. CUPED, SRM, Bonferroni, BH corrections. Self-host or managed cloud. Best fit: warehouse-SQL shop, data team controls the metric layer, wants OSS.

### Non-determinism complicates power · 非确定性让功效计算更复杂

同一提示产生不同的输出。传统功效计算假设观测独立同分布（IID）。存在 LLM 非确定性时，有效样本量低于名义值。把所需样本量乘以约 1.3-1.5 倍作为安全余量。

> Same prompt produces varying outputs. Traditional power calculations assume IID observations. With LLM non-determinism, effective sample size is lower than nominal. Multiply required sample size by ~1.3-1.5x as a safety margin.

### Real case outcomes · 真实案例结果

- 聊天机器人奖励模型变体：会话时长 +70%，留存 +30%。
- Nextdoor 主题行：奖励函数打磨后 CTR +1%。
- 可汗学院 Khanmigo：在延迟 vs 数学准确率之间迭代权衡。

> Chatbot reward model variant: +70% conversation length, +30% retention.
> Nextdoor subject lines: +1% CTR after reward-function refinement.
> Khan Academy Khanmigo: iterative latency-vs-math-accuracy trade.

### The anti-pattern: shipping on vibes · 反模式：凭感觉上线

每个资深工程师都能说出一个因为「感觉更好」、没做 A/B 就上线的功能。它们中的大多数让产品指标回退了几个月而没人察觉。A/B 就是那个强制纠偏机制。

> Every senior engineer can name a feature that was shipped because "it feels better" with no A/B. Most of them regressed product metrics the team didn't notice for months. A/B is the forcing function.

### Numbers you should remember · 你该记住的数字

- Statsig 被 OpenAI 收购：$1.1B，2025 年 9 月。
- GrowthBook：开源 MIT；贝叶斯 + 频率派 + 序贯。
- CUPED 方差缩减：30-70%。
- LLM 非确定性 → 样本量 +30-50% 余量。

```figure
mx-sequential-test
```

> Statsig acquired by OpenAI: $1.1B, September 2025. GrowthBook: open-source MIT; Bayesian + Frequentist + Sequential. CUPED variance reduction: 30-70%. LLM non-determinism → +30-50% sample-size buffer.

## Use It · 实战用法

`code/main.py` 模拟固定边界与序贯边界的 A/B 检验。展示序贯如何让你提前停。

> `code/main.py` simulates a sequential A/B test with fixed and sequential boundaries. Shows how sequential lets you stop early.

## Ship It · 交付

本课产出 `outputs/skill-ab-plan.md`。给定功能变更、工作负载和基线，它挑选平台、门禁和样本量。

> This lesson produces `outputs/skill-ab-plan.md`. Given feature change, workload, baseline, picks platform, gates, sample size.

## Exercises · 练习

1. 跑 `code/main.py`。期望提升 5%、基线转化 3% 时，80% 功效需要多大样本量？
2. 为一个受医疗合规监管、要求本地部署（on-prem）的客户，在 Statsig 和 GrowthBook 里选一个。
3. 设计一个在「每解决一张工单成本」上比较 GPT-4 与 GPT-3.5 的 A/B。主指标、护栏指标、次要指标各是什么？
4. 你的 canary 通过了，但 A/B 显示转化 -1.2%。上线吗？写出升级（escalation）标准。
5. 把 CUPED 应用到一个方差为实验后 60% 的实验前时段。计算有效样本量的提升。

> 1. Run `code/main.py`. For an expected 5% lift with baseline 3% conversion, what sample size to 80% power? ... 3. Design an A/B that tests GPT-4 vs GPT-3.5 on cost-per-resolved-ticket. What's the primary metric, guardrail metric, secondary? ... 5. Apply CUPED to a pre-period with 60% of the variance of post. Compute the effective-sample-size boost.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|------------|----------|
| Eval | 「离线测试」 | 在标注集上评估模型能力 |
| A/B test | 「实验」 | 在真实用户上随机化对比 |
| CUPED | 「方差缩减」 | 用实验前时段回归来降低方差 |
| Sequential test | 「可以偷看的检验」 | 允许提前停止的始终有效程序 |
| Multiple comparison | 「族错误」 | 跑很多检验会推高假阳性 |
| Bonferroni | 「严格校正」 | 把 α 除以检验数 |
| Benjamini-Hochberg | 「BH FDR」 | 错误发现率控制，没那么保守 |
| SRM | 「split 不对劲」 | 样本比例失配；分配有 bug |
| Statsig | 「OpenAI 家的」 | 商业一体化产品，2025 年被收购 |
| GrowthBook | 「开源那个」 | MIT 仓库原生平台 |
| mSPRT | 「序贯概率比检验」 | 经典序贯程序 |

## Further Reading · 延伸阅读

- [GrowthBook — How to A/B Test AI](https://blog.growthbook.io/how-to-a-b-test-ai-a-practical-guide/)
- [Statsig — Beyond Prompts: Data-Driven LLM Optimization](https://www.statsig.com/blog/llm-optimization-online-experimentation)
- [Statsig vs GrowthBook comparison](https://www.statsig.com/perspectives/ab-testing-feature-flags-comparison-tools)
- [Deng et al. — CUPED](https://www.exp-platform.com/Documents/2013-02-CUPED-ImprovingSensitivityOfControlledExperiments.pdf)
- [Howard — Confidence Sequences](https://arxiv.org/abs/1810.08240)
