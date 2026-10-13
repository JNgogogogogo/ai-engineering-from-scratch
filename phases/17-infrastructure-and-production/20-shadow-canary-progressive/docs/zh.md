# Shadow Traffic, Canary Rollout, and Progressive Deployment for LLMs · 影子流量、金丝雀发布与 LLM 渐进式部署

> LLM 的发布同时集合了软件部署里最难的部分：没有单元测试、失败模式弥散、信号延迟。流程是：(1) 影子模式——把生产请求复制给候选模型，记录日志、做对比，对用户零影响；能抓住明显的分布问题，但不是质量保证；(2) 金丝雀发布——按 10% → 25% → 50% → 75% → 100% 渐进切流量，每步设门禁；跟踪延迟分位数、每请求成本、错误/拒答率、输出长度分布、用户反馈率；(3) 稳定性确认后，对截然不同的备选方案做 A/B 测试。非确定性不可消除——由于 GPU 浮点非结合性加上 batch 大小方差，相同输入的多次运行之间准确率差异可达 15%。成本是变量不是常量——一个好 20% 的模型可能每次调用贵 3 倍。回滚速度是决定性的：如果回滚需要重新部署，你就太慢了。策略放在配置/开关里；模型放在带固定摘要（pinned digest）的注册表里；回滚 = 翻转策略 + 还原阈值 + 几秒内钉回旧模型。

> LLM rollouts combine the hardest parts of software deployment: no unit tests, diffuse failure modes, delayed signals. The sequence is (1) shadow mode — duplicate prod requests to candidate model, log, compare with zero user impact; catches obvious distribution issues but is not a quality guarantee; (2) canary rollout — progressive traffic shift 10% → 25% → 50% → 75% → 100% with gates at each step; track latency percentiles, cost/request, error/refusal rate, output length distribution, user-feedback rate; (3) A/B testing for distinct alternatives after stability confirmed. Non-determinism is irreducible — up to 15% accuracy variation across runs with identical inputs due to GPU FP non-associativity plus batch-size variance. Cost is a variable, not constant — a 20% better model can be 3x more expensive per call. Rollback speed is decisive: if rollback requires redeploy, you are too slow. Policy lives in config/flags; model lives in registry with pinned digests; rollback = flip policy + revert threshold + pin old model in seconds.

**Type:** Learn
**Languages:** Python (stdlib, toy canary-progression simulator)
**Prerequisites:** Phase 17 · 13 (Observability), Phase 17 · 21 (A/B Testing)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 区分影子模式（零影响对比）、金丝雀（真实流量渐进）和 A/B（稳定性确认后的对比）。
- 列出五项 LLM 特有的金丝雀指标（延迟、每请求成本、错误/拒答、输出长度分布、用户反馈）。
- 解释 LLM 非确定性（最高 15%）如何改变发布语境中「稳定」的含义。
- 设计一个以秒计（翻策略开关）而非以小时计（重新部署）的回滚路径。

> Distinguish shadow mode (zero-impact compare), canary (live traffic progressive), and A/B (stability-confirmed comparison).
> Enumerate five LLM-specific canary metrics (latency, cost/request, error/refusal, output-length distribution, user feedback).
> Explain why LLM non-determinism (up to 15%) changes what "stable" means in a rollout.
> Design a rollback path that takes seconds (policy flip) not hours (redeploy).

## The Problem · 问题在哪

你上线了一个新模型。离线评测显示准确率提升 3%。你在生产把它切了上去。24 小时内，成本涨了 40%，用户点踩多了 8%，三个客户工单报告「答案怪怪的」。你回滚。重新部署花了 3 小时。你的周末毁了。

那一步其实都可以避免。影子模式本可以在任何用户看到之前抓住 40% 的成本飙升。金丝雀本可以在点踩一动时就停在 10%。策略开关回滚本只需 30 秒。这套纪律填补的正是「离线评测好看」与「真实用户满意」之间的缺口。

> You ship a new model. Offline evals show 3% accuracy gain. You flip it on in production. Within 24 hours, cost is up 40%, user thumbs-down is up 8%, three customer tickets report "weird answers." You roll back. Redeploy takes 3 hours. Your weekend is ruined.
> Every piece of that was avoidable. Shadow mode would have caught the 40% cost spike before any user saw it. Canary would have stopped at 10% when thumbs-down moved. Policy-flag rollback would have taken 30 seconds. The discipline is what fills in the gap between "offline evals look good" and "real users are happy."

## The Concept · 概念

### Shadow mode · 影子模式

候选模型收到和生产完全相同的请求；输出只记日志，不返回给用户。对用户零影响。记录：

- 输出内容（与生产做 diff）。
- token 计数（成本差）。
- 延迟。
- 拒答与错误。

能抓住：成本爆表、长度回退、明显的拒答变化、硬错误。抓不到：用户能感知的质量差异。影子是冒烟测试，不是质量测试。

> Candidate receives the same requests as production; outputs are logged, not returned to users. Zero user impact. Log: Output content (diff against production). Token counts (cost delta). Latency. Refusal and error.
> Catches: cost blow-ups, length regressions, obvious refusal changes, hard errors. Does NOT catch: quality delta users would perceive. Shadow is a smoke test, not a quality test.

### Canary rollout · 金丝雀发布

带门禁的渐进流量切换。典型进程：1% → 10% → 25% → 50% → 75% → 100%。每步对 5 项指标设门禁：

1. **延迟分位数** —— P50、P95、P99。破线：canary 的 P99 > 基线的 1.5 倍。
2. **每请求成本** —— 混合 $。破线：高于基线 20%。
3. **错误 / 拒答率** —— 5xx 加显式拒答。破线：基线的 2 倍。
4. **输出长度分布** —— 均值 + P99。破线：出现分布漂移。
5. **用户反馈率** —— 点踩 / 工单提交。破线：基线的 1.5 倍。

> Progressive traffic shift with gates. Typical progression: 1% → 10% → 25% → 50% → 75% → 100%. Gate on 5 metrics at each step:
> 1. **Latency percentiles** — P50, P95, P99. Breach: canary has P99 > 1.5x baseline.
> 2. **Cost per request** — blended $. Breach: >20% above baseline.
> 3. **Error / refusal rate** — 5xx plus explicit refusals. Breach: 2x baseline.
> 4. **Output length distribution** — mean + P99. Breach: distributional shift.
> 5. **User-feedback rate** — thumbs-down / ticket filings. Breach: 1.5x baseline.

### Non-determinism is the new variance · 非确定性是新的方差

相同的输入产生不相同的输出。原因：

- GPU 浮点非结合性（浮点归约顺序随 batch 而变）。
- batch 大小方差（同一提示在 128 的 batch 和 16 的 batch 里结果不同）。
- 采样（temperature > 0）。

实测：相同评测集上 run-to-run 准确率差异可达 15%。发布语境里的「稳定」指指标在预期方差之内，而不是与基线完全一致。把门禁设在噪声底之上。

> Identical inputs produce non-identical outputs. Reasons: GPU FP non-associativity (floating-point reduction order varies by batch). Batch-size variance (same prompt in a batch of 128 vs batch of 16). Sampling (temperature > 0).
> Measured: up to 15% accuracy variation run-to-run on identical eval sets. "Stable" in a rollout means metrics are within expected variance, not identical to baseline. Set gates above the noise floor.

### Cost is a variable · 成本是变量

一个好 20% 的模型可能每次调用贵 3 倍。每请求成本是五项门禁之一。上线一个「更好」但破坏单位经济学的模型，就是回滚案例。

> A 20% better model can be 3x more expensive per call. Cost/request is one of the five gates. Shipping a "better" model that breaks unit economics is a rollback case.

### Rollback is the weapon · 回滚就是武器

- 策略开关（feature flag 系统）：在配置里翻转百分比；以秒计。
- 模型钉定（registry digest）：被钉定的模型不会自动升级。
- 回滚 = 翻回开关 + 把钉定 digest 设回上一版。以秒计，不是小时。

如果你的栈需要重新部署才能回滚，先修好这个再发布。

> Policy flag (feature flag system): flip percentage in config; takes seconds.
> Model pinning (registry digest): pinned model does not auto-upgrade.
> Rollback = revert flag + set pinned digest to previous. Seconds, not hours.
> If your stack requires redeploy to rollback, fix that before rolling.

### Tooling · 工具

**Argo Rollouts** / **Flagger** —— Kubernetes 渐进交付控制器。与 Istio/Linkerd 加权路由集成。

**Istio weighted routing** —— 服务网格层的流量切分。

**KServe / Seldon Core** —— 带内置 canary 的模型服务。

**Feature flags** —— LaunchDarkly、Flagsmith、Unleash。策略级翻转，无需重新部署。

> **Argo Rollouts** / **Flagger** — Kubernetes progressive delivery controllers. Integrate with Istio/Linkerd weighted routing.
> **Istio weighted routing** — service-mesh-level traffic split.
> **KServe / Seldon Core** — model serving with built-in canary.
> **Feature flags** — LaunchDarkly, Flagsmith, Unleash. Policy-level flip, no redeploy.

### Metrics cadence · 指标节奏

金丝雀门禁每 5-15 分钟检查一次，取决于流量大小。10 req/min 的 1% 流量每个窗口只有 50-150 个数据点——对延迟够用，对用户反馈来说太吵。10% 流量多约 10 倍。进程应该在每一步停留足够久，以积累足够的样本。

> Canary gates check every 5-15 minutes depending on traffic volume. 1% traffic with 10 req/min gives 50-150 data points per window — enough for latency but noisy for user feedback. 10% gives ~10x more. Progressions should pause long enough to accumulate enough samples at each step.

### The A/B step is optional · A/B 这一步是可选的

如果新模型明显不同（行为不同、成本曲线不同、语气不同），canary 通过后在 50% 流量上做 A/B。如果只是改进版，canary 门禁通过后直接到 100%。

> If the new model is distinctly different (different behavior, different cost curve, different tone), A/B test it at 50% after canary passes. If it's just an improved version, skip to 100% when canary gates pass.

### Numbers you should remember · 你该记住的数字

- Canary 进程：1% → 10% → 25% → 50% → 75% → 100%。
- 非确定性上限：相同输入 run-to-run 方差可达 15%。
- 五项 canary 指标：延迟、成本、错误/拒答、输出长度、用户反馈。
- 成本门禁：高于基线 20% 即破线。
- 回滚：以秒计，不是小时。

```figure
i4-canary-ramp
```

> Canary progression: 1% → 10% → 25% → 50% → 75% → 100%. Non-determinism ceiling: up to 15% run-to-run variance on identical inputs. Five canary metrics: latency, cost, error/refusal, output length, user feedback. Cost gate: >20% above baseline is a breach. Rollback: seconds, not hours.

## Use It · 实战用法

`code/main.py` 模拟注入了回归的金丝雀发布。报告发布停在哪个阶段、哪个门禁触发。

> `code/main.py` simulates a canary rollout with injected regressions. Reports which stage the rollout halts at and which gate triggered.

## Ship It · 交付

本课产出 `outputs/skill-rollout-runbook.md`。给定候选模型、基线和风险容忍度，它设计 shadow→canary→100% 方案。

> This lesson produces `outputs/skill-rollout-runbook.md`. Given candidate model, baseline, and risk tolerance, designs shadow→canary→100% plan.

## Exercises · 练习

1. 跑 `code/main.py`。注入 25% 的成本回归。canary 停在哪一步？
2. 你的新模型离线准确率 +3%，但每请求成本 +18%。上不上线？取决于策略——把两条路径都写出来。
3. 设计一个端到端 60 秒内完成的回滚。列出所需的基础设施。
4. 非确定性在你的评测上显示 ±7%。设置金丝雀门禁以免误报。你用什么倍数？
5. 影子模式在 canary 之前抓住了 40% 的成本飙升。写出影子阶段触发的告警规则。

> 1. Run `code/main.py`. Inject a 25% cost regression. At which stage does the canary halt? ... 3. Design a rollback that takes under 60 seconds end-to-end. List the required infrastructure. ... 5. Shadow mode catches a 40% cost spike before canary. Write the alert rule that fires in shadow.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|------------|----------|
| Shadow mode | 「复制给新模型」 | 零影响地把请求发给候选模型记日志 |
| Canary | 「渐进流量」 | 带门禁的逐步用户曝光发布 |
| Gates | 「发布检查」 | 阻止推进的指标阈值 |
| Non-determinism | 「LLM 方差」 | 不可消除的 run-to-run 差异 |
| Policy flag | 「翻开关回滚」 | 配置级回滚，以秒计不是小时 |
| Model pin | 「注册表摘要」 | 指向某个模型版本的不可变引用 |
| Argo Rollouts | 「K8s 渐进交付」 | Kubernetes 原生 canary/回滚控制器 |
| KServe | 「K8s 推理」 | 带 canary 原语的模型服务 |
| Istio weighted | 「网格切分」 | 服务网格流量切分器 |

## Further Reading · 延伸阅读

- [TianPan — Releasing AI Features Without Breaking Production](https://tianpan.co/blog/2026-04-09-llm-gradual-rollout-shadow-canary-ab-testing)
- [MarkTechPost — Safely Deploying ML Models](https://www.marktechpost.com/2026/03/21/safely-deploying-ml-models-to-production-four-controlled-strategies-a-b-canary-interleaved-shadow-testing/)
- [APXML — Advanced LLM Deployment Patterns](https://apxml.com/courses/mlops-for-large-models-llmops/chapter-4-llm-deployment-serving-optimization/advanced-llm-deployment-patterns)
- [Argo Rollouts docs](https://argo-rollouts.readthedocs.io/)
- [Flagger docs](https://docs.flagger.app/)
