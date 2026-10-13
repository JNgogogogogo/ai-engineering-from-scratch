# Model Routing as a Cost-Reduction Primitive · 模型路由 —— 作为降本原语

> 一个动态代理（broker）评估每个请求（任务类型、token 长度、嵌入相似度、置信度），把简单查询送到便宜模型，把复杂请求升级到前沿模型。这也叫模型级联（model cascading）。生产案例研究显示，在美国/英国/欧洲的部署中，iso-quality（同质量）前提下可降本 20-60%；高流量 SaaS 上 30% 的路由效率提升能变成六位数的年节省。2026 年的背景是 LLM 推理价格每年降约 10 倍——一个 GPT-4 级 token 从 2022 年末的 $20/M 降到 2026 年的约 $0.40/M。降幅大部分来自更好的服务栈（Phase 17 · 04-09），不是硬件。路由就是让你把这次降价变成利润、而产品不回退的手段。失败模式是便宜模型漂移（cheap-model drift）：路由把 40% 流量推给更弱的模型，推理任务质量掉了 3-5%，一个季度都没人发现。要用在线质量指标给路由设门禁，不能只靠离线评测集。

> A dynamic broker evaluates every request (task type, token length, embedding similarity, confidence) and sends simple queries to a cheap model, escalating complex ones to a frontier model. Also called model cascading. Production case studies show 20-60% cost reduction at iso-quality across US/UK/EU deployments; a 30% routing efficiency improvement on high-volume SaaS turns into six-figure annual savings. The 2026 context is that LLM inference prices dropped ~10x per year — a GPT-4-class token went from $20/M to ~$0.40/M from late 2022 to 2026. Most of the drop is better serving stacks (Phase 17 · 04-09), not hardware. Routing is how you convert that price drop into margin without product regression. The failure mode is cheap-model drift: the route pushes 40% to a weaker model, quality drops 3-5% on reasoning tasks, no one notices for a quarter. Gate routes by online quality metrics, not just offline eval sets.

**Type:** Learn
**Languages:** Python (stdlib, toy cascading router simulator)
**Prerequisites:** Phase 17 · 01 (Managed LLM Platforms), Phase 17 · 19 (AI Gateways)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 解释模型级联（model cascading）：便宜优先并做置信度检查，置信度低时升级。
- 列出四种路由信号（任务分类、提示长度、与已知困难集的嵌入相似度、首过自置信度）。
- 在目标路由比例和质量损失容忍度下计算期望混合成本。
- 说出能抓住「便宜模型悄悄扩散」的漂移监控指标（在线质量门禁）。

> Explain model cascading: cheap-first with confidence check, escalate on low confidence.
> Enumerate the four routing signals (task classification, prompt length, embedding similarity to known-hard set, self-confidence from first-pass).
> Compute expected blended cost at target routing split and quality loss tolerance.
> Name the drift-monitoring metric (online quality gate) that catches cheap-model creep.

## The Problem · 问题在哪

你的服务在 GPT-5 上每月花 $80k。分析显示 70% 的查询很简单：「巴黎现在几点？」「改写这句话。」一个 Haiku 级模型能以 3% 的成本完美处理它们。剩下 30% 需要 GPT-5 的推理能力——写代码、数学、多步规划。

如果你把 70% 路由到便宜模型、30% 留给贵模型，在产品质量不变的前提下账单降约 65%。这就是路由。难点在于构建这个代理而不让质量回退。

> Your service costs $80k/month on GPT-5. Your analytics show 70% of queries are simple: "what time is it in Paris?" "rephrase this sentence." A Haiku-class model handles those perfectly at 3% of the cost. 30% need GPT-5's reasoning — coding, math, multi-step planning.
> If you route the 70% to cheap and 30% to expensive, your bill drops ~65% at the same product quality. This is routing. The trick is building the broker without regressing quality.

## The Concept · 概念

### Four routing signals · 四种路由信号

1. **任务分类**：simple/complex/codegen/math/chat。可以是一个基于规则的分类器、一个小 LLM（Haiku 级，$0.25/M），或与已标注桶的嵌入相似度。输出：route = cheap / balanced / frontier。

2. **提示长度**：超过 4K token 的提示常常需要 frontier 才能保持连贯。低于 500 token 的通常不需要。

3. **与已知困难集的嵌入相似度**：如果查询与某个已知困难桶很接近（cosine > 0.88），直接升级到 frontier。

4. **首过自置信度（self-confidence from first-pass）**：先发到便宜模型；如果模型的 log-probs 显示置信度低、拒绝作答、或输出含糊措辞，就在 frontier 上重试。这给约 10% 的流量增加了 P95 延迟，但在另外 90% 上省下 50% 以上。

> 1. **Task classification**: simple/complex/codegen/math/chat. Can be a rules-based classifier, a small LLM (Haiku-class at $0.25/M), or embedding similarity to labeled buckets. Output: route = cheap / balanced / frontier.
> 2. **Prompt length**: prompts >4K tokens often need frontier for coherence. Prompts <500 tokens usually don't.
> 3. **Embedding similarity to known-hard set**: if the query is close (cosine > 0.88) to a known-hard bucket, escalate to frontier directly.
> 4. **Self-confidence from first-pass**: send to cheap; if model's log-probs show low confidence OR it refuses OR outputs hedging language, retry on frontier. Adds P95 latency on ~10% of traffic but saves 50%+ on the other 90%.

### Three patterns · 三种模式

**预路由（Pre-route）**（前置分类器）：额外约 5-10ms 延迟；整体最快。

**级联（Cascade）**（便宜优先，低置信度时升级）：中位延迟约 1.2 倍（便宜跑一次加验证），被升级的请求约 2 倍。质量下限最好。

**集成路由（Ensemble route）**（对抽样流量并行跑便宜模型和 frontier，由奖励模型挑选）：质量最高、成本最高；只用于关键 A/B。

> **Pre-route** (classifier up front): ~5-10ms latency added; fastest overall.
> **Cascade** (cheap-first, escalate on low confidence): ~1.2x median latency (cheap run plus verify), ~2x on escalated. Best quality floor.
> **Ensemble route** (run cheap and frontier in parallel for a sample, reward-model pick): highest quality, highest cost; use only for critical A/B.

### Implementation · 实现

AI 网关（Phase 17 · 19）暴露路由能力。LiteLLM 有带 fallback 和成本路由的 `router` 配置。Portkey 有 guards + 路由。Kong AI Gateway 有基于插件的路由。OpenRouter 的模型市场提供推荐 API。

开源项目：RouteLLM（LMSYS）、Not Diamond（商业）、Prompt Mule。

> AI gateways (Phase 17 · 19) expose routing. LiteLLM has `router` config with fallback and cost-routing. Portkey has guards + routing. Kong AI Gateway has plugin-based routing. OpenRouter's model marketplace exposes a recommendation API.
> Open-source: RouteLLM (LMSYS), Not Diamond (commercial), Prompt Mule.

### The 2026 price curve · 2026 年价格曲线

| 模型档次 | 2022 年末 | 2026 年 | 变化 |
|-------------|-----------|------|--------|
| GPT-4 级质量 | ~$20/M | ~$0.40/M | 便宜 50 倍 |
| Frontier（GPT-5、Claude 4） | — | ~$3-10/M | 新档次 |

大部分改进来自服务效率——Phase 17 · 04-09 的核心课程变成了厂商侧的成本下降。路由让你在应用层就收获这些红利，而不用等所有用户迁移到便宜档。

> Most of the improvement is serving efficiency — the core lessons in Phase 17 · 04-09 turned into provider-side cost drops. Routing lets you capture those gains at the app layer instead of waiting for all your users to migrate to the cheap tier.

### Drift is the real risk · 漂移才是真正的风险

你的路由把 40% 流量发给便宜模型。六个月里任务分布漂移了（用户变得更老练，问的问题更长）。路由器没察觉，因为它的分类器是用 Q1 的数据训练的。质量悄悄下滑。没有人抱怨得足够大声。你是在一场输掉的竞品基准测试里才发现的。

用在线质量指标给路由设门禁：

- 每条路由的用户点赞 / 点踩。
- 对每条路由的保留样本（5%）跑自动 LLM 评审（LLM-judge）。
- 升级率（escalation rate）：如果级联里有超过 30% 的请求往上升级，说明便宜模型被过度路由了。
- 每条路由的拒绝率。

> Your route sends 40% to the cheap model. Over six months, the task distribution shifts (users get more sophisticated, ask longer questions). The router doesn't notice because its classifier was trained on Q1 data. Quality drops silently. Nobody complains loud enough. You find out in a competitor benchmark you lost.
> Gate routes by online quality metrics: User thumbs-up / thumbs-down per route. Automated LLM-judge on a held-out sample (5%) per route. Escalation rate: if cascade is kicking up-route >30%, the cheap model is being over-routed. Refusal rate per route.

### Numbers you should remember · 你该记住的数字

- 2026 年 iso-quality 路由节省：案例研究为 20-60%。
- 2022-2026 年 LLM 降价：合计约每年 10 倍。
- GPT-4 级 2022 vs 2026：~$20/M → ~$0.40/M。
- 级联延迟影响：中位约 1.2 倍，被升级请求约 2 倍（约 10% 流量）。

```figure
model-cascade-router
```

> 2026 routing savings at iso-quality: 20-60% case studies. LLM price drop 2022-2026: ~10x per year aggregate. GPT-4-level 2022 vs 2026: ~$20/M → ~$0.40/M. Cascade latency impact: ~1.2x median, ~2x escalated (~10% of traffic).

## Use It · 实战用法

`code/main.py` 在一个混合工作负载上模拟 pre-route、cascade 和 ensemble。报告混合成本、质量损失和升级率。

> `code/main.py` simulates pre-route, cascade, and ensemble on a mixed workload. Reports blended cost, quality loss, and escalation rate.

## Ship It · 交付

本课产出 `outputs/skill-router-plan.md`。给定工作负载和质量预算，它挑选路由模式和信号。

> This lesson produces `outputs/skill-router-plan.md`. Given workload and quality budget, picks a routing pattern and signals.

## Exercises · 练习

1. 跑 `code/main.py`。精度下限为多少时 cascade 胜过 pre-route？
2. 你的用户群 30% 是企业（复杂查询），70% 是免费档（简单查询）。设计路由比例。用什么在线指标做门禁？
3. 某条路由质量下降 2% 但节省 40%。该不该上线？取决于产品——正反两面都论证一下。
4. 用 OpenAI / Anthropic API 的 logprobs 实现一个置信度检查。起始阈值取多少？
5. 六个月里升级率从 8% 爬到 22%。诊断三个可能原因及各自的修复办法。

> 1. Run `code/main.py`. At what accuracy floor does cascade beat pre-route? ... 3. A route drops quality by 2% but saves 40%. Is that a ship? Depends on product — argue both. ... 5. Over six months, escalation rate climbs from 8% to 22%. Diagnose three causes and the fix for each.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|------------|----------|
| Model routing | 「成本代理」 | 按请求动态选择模型 |
| Model cascade | 「便宜优先、低置信升级」 | 先跑便宜模型，置信度低时落到 frontier |
| Pre-route | 「先分类」 | 前置分类器；不重跑 |
| Ensemble route | 「并行挑选」 | 多模型并行跑，奖励模型挑最好的 |
| Escalation rate | 「升级比例」 | 级联请求中被升级的比例 |
| RouteLLM | 「LMSYS 路由器」 | 开源路由库 |
| Not Diamond | 「商业路由器」 | SaaS 模型路由产品 |
| Drift | 「便宜模型悄悄扩散」 | 路由器未察觉的分布漂移 |
| Online quality gate | 「在线检查」 | 对线上流量采样的自动 LLM 评审 |

## Further Reading · 延伸阅读

- [AbhyashSuchi — Model Routing LLM 2026 Best Practices](https://web.archive.org/web/20260413143335/https://abhyashsuchi.in/model-routing-llm-2026-best-practices/)
- [Lukas Brunner — Rise of Inference Optimization 2026](https://dev.to/lukas_brunner/the-rise-of-inference-optimization-the-real-llm-infra-trend-shaping-2026-4e4o)
- [RouteLLM paper / code](https://github.com/lm-sys/RouteLLM)
- [Not Diamond — model routing](https://www.notdiamond.ai/)
- [OpenRouter](https://openrouter.ai/) —— 带路由原语的多模型网关。
