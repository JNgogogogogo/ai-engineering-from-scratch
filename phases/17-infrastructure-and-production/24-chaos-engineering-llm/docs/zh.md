# Chaos Engineering for LLM Production · LLM 生产环境的混沌工程

> 2026 年，面向 LLM 的混沌工程已经是一门独立的学科。在生产上跑实验前的先决条件：定义好的 SLI/SLO、trace + 指标 + 日志的可观测性、自动回滚、runbook、值班机制。架构分为四个平面（planes）：控制平面（实验调度器）、目标平面（服务、基础设施、数据存储）、安全平面（护栏 + 中止 + 流量过滤器）、可观测性平面（指标 + trace + 日志），外加反馈环节（回灌到 SLO 调整）。护栏是强制性的：当日错误预算（error budget）消耗超过预期的 2 倍时，燃烧率告警（burn-rate alert）暂停实验；抑制窗口（suppression windows）+ trace-ID 关联用来给告警噪音去重。节奏：每周小规模金丝雀（canary）实验 + SLO 评审；每月游戏日（game day）+ 复盘；每季度跨团队韧性审计 + 依赖关系梳理。LLM 专属实验：内存过载、网络故障、供应商（provider）宕机、畸形提示词（malformed prompt）、KV cache 驱逐风暴。工具：Harness Chaos Engineering（LLM 生成的实验建议、爆炸半径降级、MCP 工具集成）；LitmusChaos（CNCF）；Chaos Mesh（CNCF，Kubernetes 原生）。

> Chaos engineering for LLMs is its own discipline in 2026. Prerequisites before running experiments in production: defined SLI/SLO, trace+metric+log observability, automated rollback, runbooks, on-call. Architecture has four planes: control (experiment scheduler), target (services, infra, data stores), safety (guards + abort + traffic filters), observability (metrics + traces + logs), feedback (into SLO adjustments). Guardrails are mandatory: burn-rate alerts pause experiments if daily error-budget burn > 2x expected; suppression windows + trace-ID correlation dedupe alert noise. Cadence: weekly small canary + SLO review; monthly game day + postmortem; quarterly cross-team resilience audit + dependency mapping. LLM-specific experiments: memory overload, network failures, provider outages, malformed prompts, KV cache eviction storms. Tooling: Harness Chaos Engineering (LLM-derived recommendations, blast-radius downscaling, MCP tool integration); LitmusChaos (CNCF); Chaos Mesh (CNCF Kubernetes-native).

**Type:** Learn
**Languages:** Python (stdlib, toy chaos experiment runner)
**Prerequisites:** Phase 17 · 23 (SRE for AI), Phase 17 · 13 (Observability)
**Time:** ~60 minutes

---

## Learning Objectives · 学习目标

- 说出混沌工程的五项先决条件（SLI/SLO、可观测性、回滚、runbook、值班），并解释为什么缺了任何一项都会让这门实践翻车
- 画出四个平面（控制、目标、安全、可观测性）以及回灌 SLO 的反馈环
- 列举五个 LLM 专属实验（内存过载、网络故障、供应商宕机、畸形提示词、KV 驱逐风暴）
- 给定技术栈，在 Harness、LitmusChaos、Chaos Mesh 中完成选型

> Name the five chaos engineering prerequisites (SLI/SLO, observability, rollback, runbooks, on-call) and explain why skipping any breaks the practice.
> Diagram the four planes (control, target, safety, observability) and the feedback loop into SLO.
> Enumerate five LLM-specific experiments (memory overload, network fail, provider outage, malformed prompt, KV eviction storm).
> Pick a tool — Harness, LitmusChaos, Chaos Mesh — given stack.

---

## The Problem · 问题在哪

传统技术栈的混沌测试已经很成熟。LLM 技术栈带来了新的故障模式。一条带毒字符的 4K token 提示词能让分词器卡住 12 秒。上游供应商返回 429；你的网关重试；你的服务在重试放大的并发下 OOM。突发负载下的 KV cache 驱逐风暴引发 re-prefill 级联，把算力打满。

这些问题在单元测试里一个都不会暴露。混沌工程就是你抢在用户之前发现它们的办法。

> Chaos testing in traditional stacks is established. LLM stacks add new failure modes. A 4K-token prompt with a poison character stalls the tokenizer for 12 seconds. An upstream provider 429s; your gateway retries; your service OOMs on retry-amplified concurrency. A KV cache eviction storm under burst load causes re-prefill cascades that saturate compute. ... None of these show up in unit tests. Chaos engineering is how you discover them before users do.

---

## The Concept · 概念

### Prerequisites · 先决条件

没有这些就别在生产上跑混沌：

1. **SLI/SLO**——定义好的服务级指标（indicator）和目标（objective）。
2. **可观测性**——trace、指标、日志，都接好仪表盘。
3. **自动回滚**——Phase 17 · 20 的策略开关（policy-flag）回滚。
4. **Runbook**——结构化的，见 Phase 17 · 23。
5. **值班（on-call）**——得有人响应。

缺任何一项，混沌实验都会变成真实事故。

> Don't run chaos in production without:
> 1. **SLI/SLO** — defined service-level indicators and objectives.
> 2. **Observability** — traces, metrics, logs, wired to dashboards.
> 3. **Automated rollback** — Phase 17 · 20 policy-flag rollback.
> 4. **Runbooks** — structured, Phase 17 · 23.
> 5. **On-call** — someone to respond.
> Missing any means chaos becomes real incident.

### Four planes + feedback · 四个平面 + 反馈

**控制平面（Control plane）**——实验调度器（Litmus workflow、Chaos Mesh schedule、Harness UI）。

**目标平面（Target plane）**——服务、pod、节点、负载均衡器、数据存储。

**安全平面（Safety plane）**——kill switch、抑制窗口、爆炸半径（blast radius）限制、错误预算门禁。

**可观测性平面（Observability plane）**——常规指标 + trace-ID 关联，用来区分混沌引发的故障和自然发生的故障。

**反馈环（Feedback loop）**——发现回灌到 SLO 调整、runbook 更新、代码修复。

> **Control plane** — experiment scheduler (Litmus workflow, Chaos Mesh schedule, Harness UI). ... **Safety plane** — kill switch, suppression windows, blast-radius limits, error-budget gates. ... **Observability plane** — normal metrics + trace-ID correlation to distinguish chaos-induced from natural failures. ... **Feedback loop** — findings feed back into SLO adjustment, runbook updates, code fixes.

### Guardrails are mandatory · 护栏是强制性的

- **燃烧率告警（Burn-rate alert）**：当日错误预算消耗超过预期的 2 倍就暂停实验。
- **抑制窗口（Suppression windows）**：实验期间静默爆炸半径内的非实验告警。
- **Trace-ID 关联**：所有实验引发的错误都带标签，值班人员可以据此去重。

> **Burn-rate alert**: pause experiment if daily error-budget burn exceeds 2x expected.
> **Suppression windows**: silence non-experiment alerts in the blast radius during experiment.
> **Trace-ID correlation**: all experiment-induced errors carry a tag so on-call can dedupe.

### Five LLM-specific experiments · 五个 LLM 专属实验

1. **内存过载（Memory overload）**——用高并发长上下文请求强制造成 KV cache 抢占（preemption）风暴。观察：服务是优雅卸载（graceful shed）还是崩溃？

2. **网络故障（Network failure）**——切断推理网关与供应商之间的连接。观察：fallback 能否在 SLA 内生效？（Phase 17 · 19）

3. **供应商宕机模拟（Provider outage simulation）**——让 OpenAI 100% 返回 429。观察：路由能否 failover 到 Anthropic？（Phase 17 · 16, 19）

4. **畸形提示词（Malformed prompt）**——注入能让分词器卡死的载荷（例如深度嵌套的 unicode、超大 UTF-8 码点）。观察：一条请求能否锁死一个 worker？

5. **KV 驱逐风暴（KV eviction storm）**——用打满 vLLM block 预算的方式强制驱逐。观察：LMCache 能恢复还是服务劣化？

> **Memory overload** — force a KV cache preemption storm by sending long-context requests with high concurrency. Observe: does the service gracefully shed or crash? ... **Provider outage simulation** — 100% 429 from OpenAI. Observe: does routing failover to Anthropic? (Phase 17 · 16, 19) ... **Malformed prompt** — inject tokenizer-stalling payload (e.g., deeply nested unicode, huge UTF-8 codepoint). Observe: does a single request lock up a worker? ... **KV eviction storm** — force eviction by saturating vLLM block budget. Observe: does LMCache recover or does service degrade?

### Cadence · 节奏

- **每周**——在 staging 跑小规模金丝雀实验，偶尔在 prod 跑 5% 流量。
- **每月**——针对特定场景的定期游戏日；跨团队参加；事后复盘。
- **每季度**——跨团队韧性审计；更新依赖关系图。

> **Weekly** — small canary experiments in staging, maybe 5% prod. ... **Monthly** — scheduled game day on a specific scenario; cross-team attendance; postmortem. ... **Quarterly** — cross-team resilience audit; dependency map update.

### Tooling · 工具

- **Harness Chaos Engineering**——商业产品；AI 生成的实验建议；爆炸半径降级；MCP 工具集成。
- **LitmusChaos**——CNCF 毕业项目；基于 Kubernetes workflow。
- **Chaos Mesh**——CNCF 沙箱项目；Kubernetes 原生 CRD 风格。
- **Gremlin**——商业产品；支持面广。
- **AWS FIS** / **Azure Chaos Studio**——托管云服务。

> **Harness Chaos Engineering** — commercial; AI-derived experiment recommendations; blast-radius downscaling; MCP tool integration. ... **LitmusChaos** — CNCF graduated; Kubernetes workflow-based. ... **Chaos Mesh** — CNCF sandbox; Kubernetes-native CRD style. ... **Gremlin** — commercial; broad support. ... **AWS FIS** / **Azure Chaos Studio** — managed cloud offerings.

### Starting small · 从小处起步

第一个实验：在稳定流量下 pod-kill 掉一个解码副本。观察重路由和恢复。如果一切正常且看起来安全，再升级到网络混沌。

第一个 LLM 专属实验：注入一次持续 5 分钟的供应商 429。观察 fallback。大多数团队会发现他们的 fallback 根本没被完整测过。

> First experiment: pod-kill one decode replica under steady traffic. Observe rerouting and recovery. If this works and looks safe, graduate to network chaos. ... First LLM-specific experiment: inject one provider 429 for 5 minutes. Observe fallback. Most teams discover their fallback wasn't fully tested.

### Numbers you should remember · 该记住的数字

- 四个平面：控制、目标、安全、可观测性。
- 燃烧率暂停阈值：当日预算消耗达到预期的 2 倍。
- 节奏：每周金丝雀、每月游戏日、每季度审计。
- 五个 LLM 实验：内存、网络、供应商、畸形提示词、KV 风暴。

> Four planes: control, target, safety, observability.
> Burn-rate pause: 2x expected daily budget burn.
> Cadence: weekly canary, monthly game day, quarterly audit.
> Five LLM experiments: memory, network, provider, malformed prompt, KV storm.

```figure
i4-chaos-guard
```

---

## Use It · 实战用法

`code/main.py` 在安全平面门禁下模拟三个混沌实验，并报告哪些实验会触发燃烧率中止（abort）。

> `code/main.py` simulates three chaos experiments with safety plane gates. Reports which experiments would trip the burn-rate abort.

---

## Ship It · 交付

本课产出 `outputs/skill-chaos-plan.md`。输入技术栈和成熟度，它选出前三个实验和配套工具。

> This lesson produces `outputs/skill-chaos-plan.md`. Given stack and maturity, picks first three experiments and the tooling.

---

## Exercises · 练习

1. 跑 `code/main.py`。哪个实验触发了燃烧率门禁？为什么？
2. 为一个基于 vLLM 的 RAG 服务设计前五个混沌实验，并写明成功标准。
3. 你的燃烧率告警暂停了一个实验。如何判定根因——混沌还是自然故障？
4. 论证混沌应该跑在生产环境还是只在 staging。什么时候生产才是正确答案？
5. 说出三个通用网络混沌无法复现的 LLM 专属故障模式。

---

## Key Terms · 术语表

| 术语 | 人们口头说 | 实际含义 |
|------|----------------|------------------------|
| SLI / SLO | 「服务目标」 | 指标 + 目标；必备先决条件 |
| Blast radius | 「影响范围」 | 实验会波及的服务 / 用户集合 |
| Burn-rate alert | 「预算门禁」 | 错误预算燃烧率超过预期 2 倍时触发 |
| Game day | 「月度演练」 | 定期的跨团队混沌演习 |
| LitmusChaos | 「CNCF workflow」 | CNCF 毕业的 Kubernetes 混沌工具 |
| Chaos Mesh | 「CNCF CRD」 | CNCF 沙箱的 Kubernetes 原生混沌 |
| Harness CE | 「商业 AI 辅助」 | 带 AI 实验建议的 Harness 混沌 |
| Malformed prompt | 「分词器炸弹」 | 会让分词卡死的输入 |
| KV eviction storm | 「抢占级联」 | 大规模驱逐触发 re-prefill |

---

## Further Reading · 延伸阅读

- [DevSecOps School — Chaos Engineering 2026 Guide](https://devsecopsschool.com/blog/chaos-engineering/)
- [Ankush Sharma — Observability for LLMs (book)](https://www.amazon.com/Observability-Large-Language-Models-Engineering-ebook/dp/B0DJSR65TR)
- [LitmusChaos (CNCF)](https://litmuschaos.io/)
- [Chaos Mesh (CNCF)](https://chaos-mesh.org/)
- [Harness Chaos Engineering](https://www.harness.io/products/chaos-engineering)
- [AWS FIS](https://aws.amazon.com/fis/)
