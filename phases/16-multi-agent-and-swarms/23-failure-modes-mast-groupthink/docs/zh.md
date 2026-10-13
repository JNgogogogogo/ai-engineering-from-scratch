# Failure Modes — MAST, Groupthink, Monoculture, Cascading Errors · 失败模式 —— MAST、群体思维、单一化与级联错误

> The reference taxonomy for 2026 is **MAST** (Cemri et al., NeurIPS 2025, arXiv:2503.13657), derived from 1642 execution traces across 7 state-of-the-art open-source MAS showing **41–86.7% failure rate**. Three root categories: **Specification Problems** (41.77%) — role ambiguity, unclear task definitions; **Coordination Failures** (36.94%) — communication breakdowns, state desync; **Verification Gaps** (21.30%) — missing validation, absent quality checks. The **Groupthink** family (arXiv:2508.05687) adds: monoculture collapse (same base model → correlated failures), conformity bias (agents reinforce each other's errors), deficient theory of mind, mixed-motive dynamics, cascading reliability failures. Cascading example: retry storms where a payment failure triggers order retries, which trigger inventory retries, which overwhelm inventory service (10x load in seconds — needs circuit breakers). Memory poisoning: one agent's hallucination enters shared memory, downstream agents treat it as fact; accuracy decays gradually, making root-cause diagnosis painful. **STRATUS** (NeurIPS 2025) reports 1.5x mitigation-success improvement via specialized detection / diagnosis / validation agents. This lesson treats failure modes as first-class engineering targets.

2026 年的参考分类法是 **MAST**（Cemri et al., NeurIPS 2025, arXiv:2503.13657），它源自 7 个最先进开源 MAS 的 1642 条执行轨迹，显示**失败率 41–86.7%**。三大根因类别：**规格问题（Specification Problems）**（41.77%）—— 角色模糊、任务定义不清；**协调失败（Coordination Failures）**（36.94%）—— 通信中断、状态失步；**验证缺口（Verification Gaps）**（21.30%）—— 缺少校验、没有质量检查。**群体思维（Groupthink）**家族（arXiv:2508.05687）补充了：单一化崩塌（同一个基座模型 → 相关的失败）、从众偏差（智能体互相强化对方的错误）、心智理论缺陷、混合动机动态、级联可靠性失败。级联示例：重试风暴 —— 支付失败触发订单重试，订单重试触发库存重试，最终压垮库存服务（几秒内 10 倍负载 —— 需要熔断器）。记忆投毒：一个智能体的幻觉进入共享内存，下游智能体把它当成事实；精度缓慢衰减，让根因诊断非常痛苦。**STRATUS**（NeurIPS 2025）报告通过专门的检测/诊断/验证智能体，缓解成功率提升 1.5 倍。本课把失败模式当作一等工程目标来对待。

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** Phase 16 · 13 (Shared Memory), Phase 16 · 14 (Consensus and BFT), Phase 16 · 15 (Voting and Debate Topology)
**Time:** ~75 minutes

## Problem · 问题

多智能体系统在真实任务上的失败率是 41-86.7%（Cemri 等人 2025 年在 7 个开源 MAS 上测得）。靠「多加几个智能体」是调试不好的。这些失败有结构性原因。MAST 分类法给了你类别。本课把每个类别映射到具体的检测、诊断和缓解模式，让这些数字不再显得随意。

2026 年的生产实践是把失败模式当作设计输入。在你能为每个 MAST 类别指认出你部署的缓解措施之前，你的架构都谈不上「够好」。

> Multi-agent systems fail 41-86.7% of the time on real tasks (Cemri et al. 2025 measured this across 7 open-source MAS). That is not debuggable by "just add more agents." The failures have structural causes. The MAST taxonomy gives you the categories. This lesson maps each category to a concrete detection, diagnosis, and mitigation pattern so the numbers stop looking arbitrary.
> The 2026 production practice is to treat failure modes as design inputs. Your architecture is not "good enough" until you can point to each MAST category and name the mitigation you deployed.

## Concept · 概念

### MAST categories · MAST 类别

**规格问题（占失败的 41.77%）。** 智能体的任务没有被足够紧地定义。例子：

- 角色模糊：两个智能体都认为自己是评审者。
- 任务欠规格：用户想要一个特定角度，提示却只写「总结一下」。
- 成功标准隐式：智能体无法判断自己是否成功了。

缓解措施：
- 写显式的角色契约。每个智能体的提示要说明它做什么*以及不做什么*。
- 每个任务配验收测试。智能体开工之前，先定义「完成长什么样」。
- 起飞前规格检查：派发之前由一个独立的智能体审查任务定义。

**协调失败（36.94%）。** 通信或状态的中断。

例子：
- 两个智能体在没有同步的情况下更新共享状态。
- 消息在智能体之间丢失（队列故障、超时）。
- 状态漂移：智能体 A 认为任务完成了；智能体 B 还在执行。

缓解措施：
- 带乐观并发的版本化共享状态。
- 关键消息要求显式确认（没确认就一直重试）。
- 周期性状态同步检查点；尽早发现漂移。

**验证缺口（21.30%）。** 输出没有独立检查。

例子：
- 一个智能体声称成功；没有人验证。
- 智能体链条上每个都信任前一个的输出。
- 涌现出来的组合行为没有测试覆盖。

缓解措施：
- 独立验证者智能体（第 13 课）。只读、独立的数据源访问。
- 显式的交接契约：「A 的输出必须先通过检查器 C，B 才能开工。」
- 为事后分析记录结果日志。

> **Specification Problems (41.77% of failures).** The agent's task was not defined tightly enough. Mitigations: write explicit role contracts; acceptance tests per task; pre-flight spec check.
> **Coordination Failures (36.94%).** Communication or state breakdowns. Mitigations: versioned shared state with optimistic concurrency; explicit acknowledgment for critical messages; periodic state-sync checkpoints.
> **Verification Gaps (21.30%).** No independent check on outputs. Mitigations: independent verifier agent; explicit handoff contract; outcome logging for post-hoc analysis.

### Groupthink family (arXiv:2508.05687) · 群体思维家族（arXiv:2508.05687）

智能体同质化或互相模仿时，会出现五种相关失败：

**单一化崩塌（Monoculture collapse）。** 同一个基座模型或训练数据 → 错误相关。三个智能体共享一个 LLM 时，它们也共享它的幻觉。

**从众偏差（Conformity bias）。** 智能体向声音最大或最自信的同伴靠拢，哪怕对方是错的。

**心智理论缺陷（Deficient ToM）。** 智能体无法对彼此的信念建模；协调随之崩塌（第 18 课）。

**混合动机动态（Mixed-motive dynamics）。** 激励部分对齐的智能体漂向折中点，而折中点谁都不满意。

**级联可靠性失败（Cascading reliability failures）。** 一个组件的错误模式触发依赖组件的错误模式。

> Five related failures when agents homogenize or mimic each other: monoculture collapse (same base model or training data → correlated errors); conformity bias (agents adjust toward the loudest or most-confident peer, even when wrong); deficient ToM; mixed-motive dynamics; cascading reliability failures.

### Cascading example — the retry storm · 级联示例 —— 重试风暴

一个经典的 2026 年事故模式：

```
payment service fails 10% of requests
   ↓
order agent retries payment (exponential backoff but naive)
   ↓
each retry is a new order-inventory check
   ↓
inventory service sees 2x normal load
   ↓
inventory service starts timing out
   ↓
every order retries inventory check
   ↓
inventory service sees 10x normal load
   ↓
cluster goes down
```

修法是经典的：**熔断器（circuit breakers）**。当下游错误率超过阈值，就短路，返回缓存或默认结果。再加上每个请求有上限的重试预算。

熔断器是少数几个可以直接从分布式系统照搬、无需修改的多智能体失败缓解手段之一。

> A classic 2026 incident pattern: a payment failure triggers order retries, which trigger inventory retries, which overwhelm inventory service (10x load in seconds — needs circuit breakers).
> The fix is classical: **circuit breakers**. When downstream error rate exceeds threshold, short-circuit with cached or default results. Plus capped retry budgets per request.
> Circuit breakers are one of the few multi-agent failure mitigations you borrow directly from distributed systems without modification.

### Memory poisoning (revisited) · 记忆投毒（回顾）

来自第 13 课：一个智能体的幻觉变成共享内存里的事实；下游智能体在这个被投毒的事实上推理。用 MAST 的话说，这是共享内存层上的一个验证缺口。

渐进的精度衰减是症状。你不会看到崩溃；你看到的是难以定位根因的缓慢漂移。

缓解：只追加日志、来源追踪、不可写的验证者。第 13 课已经讲过。

> From Lesson 13: one agent's hallucination becomes shared-memory fact; downstream agents reason on the poisoned fact. In MAST terms, this is a verification gap at the shared-memory layer.
> Gradual accuracy decay is the symptom. You do not get a crash; you get slow drift that is hard to root-cause.
> Mitigation: append-only log, provenance, unwritable verifier. Already covered in Lesson 13.

### STRATUS — specialized agents for failure detection · STRATUS —— 用于失败检测的专门智能体

STRATUS（NeurIPS 2025）报告，当你部署以下三者时，缓解成功率提升 1.5 倍：

- **检测智能体。** 监视症状模式（高分歧、重试尖峰、精度漂移）。
- **诊断智能体。** 给定症状，从 MAST 分类法推断可能的根因。
- **验证智能体。** 缓解措施生效后，检查症状是否消除。

这是 SRE 式的事故响应，应用到了智能体系统上。三个角色都可以是带专门提示的 LLM 智能体。

> STRATUS (NeurIPS 2025) reports 1.5x mitigation-success improvement when you deploy a detection agent (watches for symptom patterns), a diagnosis agent (infers likely root cause from the MAST taxonomy), and a validation agent (checks that symptoms clear after a mitigation is applied).
> This is SRE-style incident response, applied to agent systems. The three roles can all be LLM agents with specialized prompts.

### The failure-mode audit · 失败模式审计

2026 年的一个最佳实践是每年（或每个大版本）做一次失败模式审计：

1. **轨迹采样。** 收集约 1000 条真实执行轨迹。
2. **归类。** 把每条轨迹的失败映射到 MAST + 群体思维类别。
3. **计算按类别的失败率。** 哪些类别在你的系统里占主导？
4. **给缓解措施排序。** 哪个修复能消除最多的失败？
5. **挑 2-3 个缓解措施。** 落地；下个季度再审计。

纪律比具体选择更重要。没有审计，失败会混进噪声里，永远得不到系统性的处理。

> A 2026 best practice is an annual (or per-major-release) failure-mode audit: trace sample (~1000 real execution traces), categorize (map to MAST + Groupthink categories), compute failure-by-category rate, rank mitigations, pick 2-3 mitigations and re-audit next quarter.
> The discipline is more important than the specific choices. Without audits, failures blend into noise and never get systematically addressed.

### When systems fail silently · 系统静默失败时

最危险的失败类别是静默的正确性失败。响亮地失败的系统（崩溃、异常、告警）可以被监控。产出看似合理但错误的输出的系统，无法靠异常日志发现。这就是为什么验证缺口按次计只占 21.30%，却是单次失败最昂贵的类别。

值得投入的：
- 抽样人工评审。
- 黄金数据集回归测试。
- 重要输出上的跨智能体交叉检查。

> The most dangerous failure category is silent correctness failure. A system that fails loudly (crash, exception, alert) can be monitored. A system that produces plausible-but-wrong outputs cannot be detected by exception logs. This is why verification gaps are the most expensive category per-failure even though they are only 21.30% by count.
> Invest in: sample-based human review; golden-dataset regression tests; cross-agent cross-checking on important outputs.

### Failure vs slow failure · 即时失败与慢性失败

有些失败是即时的；有些是慢性的。即时失败（超时、schema 不匹配、认证错误）检测便宜。慢性失败（记忆投毒、单一化漂移、角色模糊）检测和预防都昂贵。

2026 年的工程动作：为慢性失败安装代理指标（proxy），在漂移变成可见错误之前抓住它。一致率、重试率、输出长度分布、相邻智能体版本之间的编辑距离，都是有用的代理指标。

> Some failures are immediate; some are slow. Immediate failures (timeout, schema mismatch, auth error) are cheap to detect. Slow failures (memory poisoning, monoculture drift, role ambiguity) are expensive to detect and prevent.
> The 2026 engineering move: instrument slow-failure proxies so you can catch drift before it becomes a visible error. Agreement rate, retry rate, output-length distribution, and edit-distance between consecutive agent versions are all useful proxies.

```figure
a5-retry-cascade
```

## Build It · 动手造

`code/main.py` 实现：

- `FailureTaxonomy` —— 把模拟事故归入 MAST + 群体思维类别。
- `CircuitBreaker` —— 经典模式；错误率超阈值即打开。
- `RetryStormSimulator` —— 展示级联失败；可开关熔断器。
- `DetectionAgent` —— 脚本化的 STRATUS 式症状匹配器。

运行：

```
python3 code/main.py
```

预期输出：
- 无熔断器的重试风暴：库存错误爆炸（模拟）。
- 有熔断器：封顶在阈值；返回降级模式的响应。
- 检测智能体标记出该模式并说出 MAST 类别。

> Expected output: retry storm with no circuit breaker — inventory errors blow up (simulated); with circuit breaker — cap at threshold, degraded-mode responses served; detection agent flags the pattern and names the MAST category.

## Use It · 实战用法

`outputs/skill-mast-auditor.md` 对一个多智能体系统运行 MAST 式的失败模式审计。轨迹 → 归类 → 缓解措施排序。

> `outputs/skill-mast-auditor.md` runs a MAST-style failure-mode audit on a multi-agent system. Traces → categorization → mitigation ranking.

## Ship It · 交付

生产环境的失败模式纪律：

- **MAST 审计每季度一次。** 不是每年。类别会随着系统成长而漂移。
- **熔断器无处不在。** 每一个对依赖服务的出站调用。默认打开阈值设在 5-10% 错误率。
- **黄金数据集。** 小而高质量、人工审计过。每周对着它们做回归测试。
- **STRATUS 三件套。** 检测 + 诊断 + 验证智能体监控生产。先只上检测智能体；症状嘈杂时再加诊断。
- **失败预算。** 按类别给失败率设显式 SLO。超出预算就触发「停止发布」的讨论。

> Failure-mode discipline in production: MAST audit per quarter; circuit breakers everywhere; golden datasets; STRATUS trio; failure budget. Exceeding budget triggers a stop-shipping conversation.

## Exercises · 练习

1. 运行 `code/main.py`。确认熔断器封住了重试风暴。调整失败阈值并观察其中的权衡。
2. 实现一个**慢性失败代理指标**：3 个并行智能体间的一致率。当它骤降时触发告警。通过逐渐关联智能体输出来模拟单一化漂移。
3. 阅读 Cemri 等人（arXiv:2503.13657）。挑出他们的 7 个 MAS 系统之一，映射它的前 3 个失败类别。这些与 MAST 的预测相比如何？
4. 阅读群体思维论文（arXiv:2508.05687）。找出五种模式里在生产中最难检测的一种。提出一个代理指标。
5. 为你熟悉的一个具体多智能体系统设计 STRATUS 式的检测-诊断-验证三件套。检测监视哪些症状？诊断推荐哪些缓解措施？验证如何确认它们有效？

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| MAST | 「2026 年的分类法」 | Cemri 2025；3 个根因类别 + 14 个失败子类型。 |
| Specification Problem | 「角色模糊」 | 任务或角色定义不足；智能体不知道该做什么。 |
| Coordination Failure | 「状态失步」 | 智能体之间的通信或同步中断。 |
| Verification Gap | 「没人检查」 | 输出在没有独立校验的情况下被接受。 |
| Groupthink family | 「同质化失败」 | 单一化、从众、ToM 缺陷、混合动机、级联。 |
| Monoculture collapse | 「同一个模型，同一批幻觉」 | 共享基座模型或训练数据导致的错误相关。 |
| Retry storm | 「级联错误放大」 | 一次失败触发重试，重试放大下游负载。 |
| Circuit breaker | 「错误率超限即快速失败」 | 错误率超过阈值即打开；用默认结果短路。 |
| STRATUS | 「事故响应三件套」 | 检测 + 诊断 + 验证智能体。缓解成功率 1.5 倍。 |
| Memory poisoning | 「幻觉传播」 | 共享内存事实被污染；下游智能体在被投毒的事实上推理。 |

## Further Reading · 延伸阅读

- [Cemri et al. — Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) — MAST 分类法，NeurIPS 2025
- [Groupthink failures in multi-agent LLMs](https://arxiv.org/abs/2508.05687) — 单一化、从众与五族分类法
- [STRATUS — specialized agents for MAS incident response](https://neurips.cc/) — NeurIPS 2025 论文集条目（检测 + 诊断 + 验证）
- [Release It! — stability patterns (Nygard)](https://pragprog.com/titles/mnee2/release-it-second-edition/) — 熔断器的权威参考
- [Anthropic — Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) — 生产失败模式笔记
