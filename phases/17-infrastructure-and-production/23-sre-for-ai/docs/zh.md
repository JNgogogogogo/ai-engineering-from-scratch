# SRE for AI — Multi-Agent Incident Response, Runbooks, Predictive Detection · AI SRE——多智能体事件响应、Runbook 与预测性检测

> AI SRE 通过 RAG 把 LLM 锚定在基础设施数据（日志、runbook、服务拓扑）上，用来自动化调查、记录和协调这几个阶段。2026 年的架构模式是多智能体编排（multi-agent orchestration）——由 supervisor 协调各专职智能体（日志、指标、runbook）；AI 提出假设和查询，人类审批判断类决策。Datadog Bits AI 和 Azure SRE Agent 已经以托管产品的形式交付这套能力。Runbook 也在演化：NeuBird Hawkeye 使用对抗式评估（adversarial evaluation，两个模型分析同一起事件；结论一致 = 有信心，不一致 = 有不确定性）；运维记忆（operational memory）在团队人员变动中得以留存。自动修复（auto-remediation）保持谨慎：AI 建议，人类批准。完全自主的动作范围很窄（重启 pod、回滚特定部署），并配严格护栏——任何兜售「一劳永逸」（set it and forget it）的人都是在过度承诺。新兴前沿：事前预测（pre-incident prediction）。MIT 的研究报告称，一个用历史日志 + GPU 温度 + API 错误模式训练的 LLM 提前 10-15 分钟预测到了 89% 的故障。预测：到 2026 年底，95% 的企业级 LLM 将具备自动故障转移。

> AI SRE uses LLMs grounded in infrastructure data (logs, runbooks, service topology) via RAG to automate investigation, documentation, and coordination phases. The 2026 architecture pattern is multi-agent orchestration — specialized agents (logs, metrics, runbooks) coordinated by a supervisor; AI proposes hypotheses and queries, humans approve judgment calls. Datadog Bits AI and Azure SRE Agent ship this as managed products. Runbooks are evolving: NeuBird Hawkeye uses adversarial evaluation (two models analyze the same incident; agreement = confidence, disagreement = uncertainty); operational memory persists across team changes. Auto-remediation stays cautious: AI suggests, humans approve. Fully autonomous action is narrow (restart pod, rollback specific deploy) with tight guardrails — anyone selling "set it and forget it" is overselling. Emerging frontier: pre-incident prediction. MIT research reports an LLM trained on historical logs + GPU temps + API error patterns predicted 89% of outages 10-15 min early. Projection: 95% of enterprise LLMs have automated failover by end-2026.

**Type:** Learn
**Languages:** Python (stdlib, toy multi-agent incident triage simulator)
**Prerequisites:** Phase 17 · 13 (Observability), Phase 17 · 24 (Chaos Engineering)
**Time:** ~60 minutes

---

## Learning Objectives · 学习目标

- 画出多智能体 AI SRE 的架构图：supervisor + 专职智能体（日志、指标、runbook）+ 人工审批关卡
- 解释为什么自动修复（auto-remediation）的范围是窄的（重启 pod、回滚部署）而不是宽的（重构服务架构）
- 说出对抗式评估模式（NeuBird Hawkeye）：两个模型一致 = 有信心；不一致 = 升级给人
- 引用 MIT 89% 早期检测的结果，以及那条运维约束：不能落地执行的预测只是仪表盘

> Diagram the multi-agent AI SRE architecture: supervisor + specialized agents (logs, metrics, runbooks) + human approval gate.
> Explain why auto-remediation is narrow (restart pod, revert deploy) rather than broad (re-architect service).
> Name the adversarial evaluation pattern (NeuBird Hawkeye): two models agree = confidence; disagree = escalate.
> Cite the MIT 89% early-detection result and the operational constraint: predictions without actuation are just dashboards.

---

## The Problem · 问题在哪

一名值班工程师凌晨 3 点被呼。「checkout 服务错误率飙高。」他查了 Datadog、Loki、三份 runbook、部署日志。30 分钟后才发现根因是 KV cache 突增导致 vLLM OOM。重启 pod，错误消失。

在 2026 年，这类调查的前 20 分钟已经可以自动化。按服务聚合日志、关联到最近的部署、与 runbook 匹配——全都是 RAG + 工具调用。在人类打开 Datadog 之前，一个受监督的智能体就能完成第一轮分诊（triage）并给出假设。

完全自主的修复是另一回事。重启 pod：安全。扩 GPU 池：策略允许就安全。重构服务架构：绝对不行。这门学科的核心就是画出这条窄线。

> An on-call engineer gets paged at 3 a.m. "High error rate in checkout." They check Datadog, Loki, three runbooks, the deploy log. 30 minutes later they realize the root cause is a vLLM OOM from a KV cache spike. They restart the pod; error clears. ... Fully autonomous remediation is a different problem. Restart pod: safe. Scale GPU pool: safe if policy allows. Re-architect the service: absolutely not. The discipline is drawing the narrow line.

---

## The Concept · 概念

### Multi-agent architecture · 多智能体架构

```
          Incident
             │
             ▼
        Supervisor
        /    |    \
       ▼     ▼     ▼
  Log agent  Metric agent  Runbook agent
       │     │     │
       └─────┴─────┘
             │
             ▼
        Hypothesis + evidence
             │
             ▼
        Human approval
             │
             ▼
        Action (narrow set)
```

Supervisor 把事件拆成子查询。专职智能体各自有工具权限（日志搜索、PromQL、文档检索）。Supervisor 负责综合，把假设 + 证据呈给人类。人类批准或改道。

> Supervisor breaks the incident into sub-queries. Specialized agents have tool access (log search, PromQL, doc retrieval). Supervisor synthesizes, presents hypothesis + evidence to human. Human approves or redirects.

### Auto-remediation scope · 自动修复的边界

**安全（窄）**：重启 pod、回滚特定部署、在预先批准的范围内扩缩资源池、开启预先批准的功能开关（feature flag）。

**不安全（宽）**：更改服务拓扑、修改资源限制、部署新代码、改 IAM、动数据库。

任何兜售「一劳永逸」的人都在过度承诺。安全集合会随着 AI SRE 成熟而扩大，但这条边界是真实存在的。

> **Safe (narrow)**: restart pod, revert specific deploy, scale pool within pre-approved bounds, enable pre-approved feature flag.
> **Not safe (broad)**: change service topology, modify resource limits, deploy new code, change IAM, alter databases.
> Anyone selling "set it and forget it" is overselling. The safe set grows as AI SRE matures, but the boundary is real.

### Adversarial evaluation (NeuBird Hawkeye) · 对抗式评估（NeuBird Hawkeye）

两个模型独立分析同一起事件。如果它们对根因的结论一致，信心就高。如果不一致，就把两个假设都摆出来升级给人。模式简单，却是过滤幻觉根因的有效手段。

> Two models independently analyze the same incident. If they agree on root cause, confidence is high. If they disagree, escalate to human with both hypotheses visible. Simple pattern, effective filter against hallucinated root causes.

### Operational memory · 运维记忆

人员流动是传统 SRE 的隐形杀手——部落知识（tribal knowledge）跟着人走。AI SRE 把 runbook + 复盘报告（post-mortem）存进向量数据库；每次新事件发生时智能体都会检索它们。新工程师入职时，AI 已经掌握了全部历史。

> Team turnover is the silent kill of traditional SRE — tribal knowledge leaves. AI SRE stores runbooks + post-mortems in a vector DB; agents retrieve on every new incident. When new engineers join, the AI has full history.

### Pre-incident prediction · 事前预测

MIT 2025 年的研究：在测试集上，一个用历史日志、GPU 温度、API 错误模式训练的 LLM 提前 10-15 分钟预测到了 89% 的故障。

现实检验：不能落地执行的预测只是仪表盘。运维真正要回答的问题是「预测到了之后做什么」？提前驱逐流量（pre-emptive drain）？拉响 pager？自动扩容？答案取决于具体策略。

> MIT 2025 research: LLM trained on historical logs, GPU temperatures, API error patterns predicted 89% of outages 10-15 minutes before they happened on the test set.
> Reality check: predictions without actuation are dashboards. The operational question is "when we predict, what do we do?" Pre-emptive drain? Pager? Auto-scale? The answer is policy-specific.

### Products in 2026 · 2026 年的产品

- **Datadog Bits AI**——Datadog 内置的托管 SRE 副驾驶（copilot）。
- **Azure SRE Agent**——Azure 原生。
- **NeuBird Hawkeye**——对抗式评估 + 运维记忆。
- **PagerDuty AIOps**——分诊 + 去重。
- **Incident.io Autopilot**——事件指挥官 + 协调。

> **Datadog Bits AI** — managed SRE copilot inside Datadog. ... **Azure SRE Agent** — Azure-native. ... **NeuBird Hawkeye** — adversarial eval + operational memory. ... **PagerDuty AIOps** — triage + deduplication. ... **Incident.io Autopilot** — incident commander + coordination.

### Runbooks as code · Runbook 即代码

Runbook 正从 Confluence 页面演化成带结构化小节的版本化 markdown（症状、假设、验证、动作）。结构化的 runbook 能让 RAG 检索效果更好。任何 AI SRE 落地的第一步，都是把非结构化 runbook 变成结构化的。

> Runbooks evolve from Confluence pages to versioned markdown with structured sections (symptom, hypothesis, verify, act). Structured runbooks feed better RAG retrieval. Start any AI-SRE rollout by turning unstructured runbooks into structured.

### Numbers you should remember · 该记住的数字

- MIT 早期检测：89% 的故障，10-15 分钟提前量。
- 多智能体分诊：supervisor +（日志、指标、runbook）+ 人类。
- 安全自动修复集合：重启 pod、回滚部署、范围内扩缩容。
- 对抗式评估：两个模型独立分析；一致 = 有信心。

> MIT early-detection: 89% of outages, 10-15 min lead time.
> Multi-agent triage: supervisor + (logs, metrics, runbooks) + human.
> Safe auto-remediation set: restart pod, revert deploy, scale within bounds.
> Adversarial eval: two models independent; agreement = confidence.

```figure
i4-incident-agents
```

---

## Use It · 实战用法

`code/main.py` 模拟一次多智能体分诊：日志智能体找到错误，指标智能体找到 CPU 尖峰，runbook 智能体匹配到已知问题。Supervisor 对假设排序。

> `code/main.py` simulates a multi-agent triage: log agent finds error, metric agent finds CPU spike, runbook agent matches to known issue. Supervisor ranks hypotheses.

---

## Ship It · 交付

本课产出 `outputs/skill-ai-sre-plan.md`。输入当前值班安排、事件量和团队成熟度，它帮你设计 AI SRE 落地方案。

> This lesson produces `outputs/skill-ai-sre-plan.md`. Given current on-call, incident volume, team maturity, designs an AI SRE rollout.

---

## Exercises · 练习

1. 跑 `code/main.py`。如果日志智能体和指标智能体结论不一致怎么办？Supervisor 如何裁决？
2. 为你的服务定义三个「安全」的自动修复动作，并逐一给出理由。
3. 写一个结构化 runbook 模板：小节划分、必填字段、验证命令。
4. 预测性检测在提前 12 分钟时触发。你的策略是什么——拉 pager、提前驱逐流量，还是两者都要？
5. 论证一个 3 人团队在 2026 年应该采用 AI SRE 还是继续等待。要考虑成熟度、事件量和风险。

---

## Key Terms · 术语表

| 术语 | 人们口头说 | 实际含义 |
|------|----------------|------------------------|
| AI SRE | 「值班智能体」 | LLM 支撑的事件调查 + 协调 |
| Supervisor agent | 「编排者」 | 把事件拆成子查询的顶层智能体 |
| Specialized agent | 「领域智能体」 | 有工具权限的子智能体（日志、指标、runbook） |
| Auto-remediation | 「AI 自动修复」 | 窄的、预先批准的动作；绝不是大范围重构 |
| Operational memory | 「向量化的 runbook」 | 复盘 + runbook 存进向量数据库供 RAG 使用 |
| Adversarial eval | 「双模型校验」 | 独立分析；结论一致 = 有信心 |
| NeuBird Hawkeye | 「那个搞对抗式的」 | 采用对抗式评估 + 记忆模式的产品 |
| Bits AI | 「Datadog 的 SRE 智能体」 | Datadog 托管的 AI SRE |
| Pre-incident prediction | 「早期检测」 | 对故障提前 10-15 分钟预警 |

---

## Further Reading · 延伸阅读

- [incident.io — AI SRE Complete Guide 2026](https://incident.io/blog/what-is-ai-sre-complete-guide-2026)
- [InfoQ — Human-Centred AI for SRE](https://www.infoq.com/news/2026/01/opsworker-ai-sre/)
- [DZone — AI in SRE 2026](https://dzone.com/articles/ai-in-sre-whats-actually-coming-in-2026)
- [Datadog Bits AI](https://www.datadoghq.com/product/bits-ai/)
- [NeuBird Hawkeye](https://www.neubird.ai/)
- [awesome-ai-sre](https://github.com/agamm/awesome-ai-sre)
