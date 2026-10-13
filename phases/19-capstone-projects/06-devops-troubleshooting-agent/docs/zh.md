# Capstone 06 — DevOps Troubleshooting Agent for Kubernetes · Kubernetes DevOps 排障智能体

> AWS 的 DevOps Agent 正式商用（GA），Resolve AI 公开了它的 K8s playbook，NeuBird 演示了语义监控，Metoro 把 AI SRE 绑到每服务 SLO 上。生产形态已定型：告警 webhook 触发，智能体（agent）读遥测，遍历一张 K8s 对象图，给根因（root-cause）假设排序，往 Slack 发一条带审批按钮的简报。默认只读。每个修复动作都由人把关。这个毕业项目（capstone）就是那个智能体，在 20 个合成事件上评估，并在三个共享案例上与 AWS 的 Agent 对比。

> AWS's DevOps Agent went GA, Resolve AI published its K8s playbooks, NeuBird demoed semantic monitoring, and Metoro tied AI SRE to per-service SLOs. The production shape is settled: an alert webhook fires, an agent reads telemetry, walks a graph of K8s objects, ranks root-cause hypotheses, and posts a Slack brief with approval buttons. Read-only by default. Every remediation gated by a human. This capstone is that agent, evaluated on 20 synthetic incidents and compared against AWS's Agent on three shared cases.

**类型（Type）:** 毕业项目（Capstone）
**语言（Languages）:** Python（智能体），TypeScript（Slack 集成）
**先修（Prerequisites）:** Phase 11（LLM 工程）、Phase 13（工具与 MCP）、Phase 14（智能体）、Phase 15（自治）、Phase 17（基础设施）、Phase 18（安全）
**实践阶段（Phases exercised）:** P11 · P13 · P14 · P15 · P17 · P18
**时间（Time）:** 30 小时

## Problem · 问题

2025-2026 年的 SRE 叙事变成了：「AI 智能体分诊事件，人类批准修复。」AWS DevOps Agent、Resolve AI、NeuBird、Metoro、PagerDuty AIOps 都在生产环境交付这个形态。智能体读 Prometheus 指标、Loki 日志、Tempo trace、kube-state-metrics，以及一张 K8s 对象知识图谱。它在五分钟内产出带遥测引用的根因假设排序。它绝不在没有 Slack 明确人工批准的情况下执行破坏性命令。

大部分难点在范围圈定与安全，不在推理。智能体需要默认只读的 RBAC 面、一个加固的 MCP 工具服务器、以及记录「每条被考虑过的命令 vs 被执行的命令」的审计日志。它需要知道自己何时超出了能力边界并升级上报。它还得跑得足够便宜，免得一场 OOM-kill 级联生成一张 $5k 的智能体账单。

> The 2025-2026 SRE narrative became: "AI agents triage incidents, humans approve remediations." AWS DevOps Agent, Resolve AI, NeuBird, Metoro, PagerDuty AIOps all ship this shape in production. ... It produces a ranked root-cause hypothesis with telemetry citations in under five minutes. It never executes destructive commands without explicit human approval through Slack. ... Most of the hard work is scoping and safety, not reasoning. The agent needs a read-only-by-default RBAC surface, a hardened MCP tool server, and audit logs of every command considered vs executed. It needs to know when it is outside its depth and escalate.

## Concept · 概念

智能体在一张知识图谱上运作。节点是 K8s 对象（Pod、Deployment、Service、Node、HPA、PVC）加遥测源（Prometheus 序列、Loki 流、Tempo trace）。边编码归属（Pod -> ReplicaSet -> Deployment）、调度（Pod -> Node）和观测（Pod -> Prometheus 序列）。图由 kube-state-metrics 同步保持新鲜，并在每次告警时重采样。

告警触发时，智能体从受影响对象开始根因定位。它沿边遍历，拉取相关遥测切片（最近 15 分钟），起草假设。假设按证据排序：有多少遥测引用支持它、多新、多具体。top-3 假设连同图路径可视化和修复动作审批按钮一起进 Slack。

修复是门控的。允许的默认动作是只读。破坏性动作（缩容、回滚、删 Pod）需要 Slack 审批；ArgoCD 回滚 hook 需要一个智能体永远不持有的 auth token。审计日志记录智能体*考虑过*的每条命令 —— 不只是执行过的 —— 让复盘能抓住未遂事件（near-miss）。

> The agent operates on a knowledge graph. Nodes are K8s objects (Pods, Deployments, Services, Nodes, HPAs, PVCs) plus telemetry sources (Prometheus series, Loki streams, Tempo traces). Edges encode ownership (Pod -> ReplicaSet -> Deployment), scheduling (Pod -> Node), and observation (Pod -> Prometheus series). ... When an alert fires, the agent root-causes from the affected object. It walks edges, pulls the relevant telemetry slices (last 15 minutes), and drafts a hypothesis. The hypothesis is ranked by evidence: how many telemetry citations support it, how recent, how specific. ... Remediation is gated. Allowed default actions are read-only. Destructive actions (scaling down, rolling back, deleting Pods) require Slack approval; ArgoCD rollback hooks require an auth token the agent never holds. The audit log records every command the agent *considered* — not just executed — so the review process catches near-misses.

## Architecture · 架构

```
PagerDuty / Alertmanager webhook
           |
           v
     FastAPI receiver
           |
           v
   LangGraph root-cause agent
           |
           +---- read-only MCP tools ----+
           |                             |
           v                             v
   K8s knowledge graph              telemetry slices
     (Neo4j / kuzu)              Prometheus, Loki, Tempo
   ownership + scheduling          last 15m, scoped
           |
           v
   hypothesis ranking (evidence weight)
           |
           v
   Slack brief + approval buttons
           |
           v (approved)
   ArgoCD rollback hook / PagerDuty escalate
           |
           v
   audit log: considered vs executed, every command
```

## Stack · 技术栈

- 可观测源：Prometheus、Loki、Tempo、kube-state-metrics
- 知识图谱：K8s 对象 + 遥测边的 Neo4j（托管）或 kuzu（嵌入式）
- 智能体：LangGraph，逐工具 allow-list，默认只读
- 工具传输：FastMCP over StreamableHTTP；破坏性工具单独一台服务器，置于审批门后
- 模型：根因推理用 Claude Sonnet 4.7，日志摘要用 Gemini 2.5 Flash
- 修复：ArgoCD 回滚 webhook、PagerDuty 升级、Slack 审批卡片
- 审计：append-only 结构化日志（considered、executed、approved、outcome）
- 部署：K8s deployment 配自己的窄 RBAC 角色；独立 namespace

> - Observability sources: Prometheus, Loki, Tempo, kube-state-metrics
> - Knowledge graph: Neo4j (managed) or kuzu (embedded) of K8s objects + telemetry edges
> - Agent: LangGraph with per-tool allow-list, read-only by default
> - Tool transport: FastMCP over StreamableHTTP; separate server for destructive tools behind approval gate
> - Models: Claude Sonnet 4.7 for root-cause reasoning, Gemini 2.5 Flash for log summarization
> - Remediation: ArgoCD rollback webhook, PagerDuty escalate, Slack approval card
> - Audit: append-only structured log (considered, executed, approved, outcome)
> - Deployment: K8s deployment with its own narrow RBAC role; separate namespace

```figure
ce-rootcause-walk
```

## Build It · 动手造

1. **图摄取。** 每 30 秒把 kube-state-metrics 同步进 Neo4j/kuzu。节点：Pod、Deployment、Node、Service、PVC、HPA。边：OWNED_BY、SCHEDULED_ON、EXPOSES、MOUNTS、SCALES。遥测叠加边：OBSERVED_BY（一个 Pod 被一条 Prometheus 序列观测）。

2. **告警接收器。** 一个接受 PagerDuty 或 Alertmanager webhook 的 FastAPI 端点。抽取受影响对象和 SLO 违约。

3. **只读工具面。** 把 kubectl、Prometheus 查询、Loki logql、Tempo traceql 包进 FastMCP。每个工具只有窄 RBAC 动词（"get"、"list"、"describe"）。默认服务器里没有 "delete"、"exec"、"scale"。

4. **根因智能体。** LangGraph 三个节点：`sample` 拉最近 15 分钟遥测切片，`walk` 查图中相邻对象，`hypothesize` 起草带遥测引用的根因候选排序。

5. **证据打分。** 每个假设的分数 = 新近度 * 具体度 * 图路径长度倒数 * 引用数。返回 top-3。

6. **Slack 简报。** 发一条 attachment：假设、图路径可视化（服务端渲染的子图图像）、以及至多一个修复动作的审批按钮。

7. **修复门。** 破坏性工具（缩容、回滚、删除）放在第二台 MCP 服务器上，审批 token 后面。智能体只有在 Slack 卡片被人批准后才能调用它们。

8. **审计日志。** Append-only JSONL：对每条候选命令，记录它是否被考虑过、是否被执行过、谁批准。每天送到 S3。

9. **合成事件套件。** 建 20 个场景：OOMKill 级联、DNS 抖动、HPA 抖动、PVC 写满、吵闹邻居、故障 sidecar、坏 ConfigMap 发布、证书轮换、镜像拉取退避等。按根因准确率和出假设时间给智能体打分。

> **Graph ingestion.** Sync kube-state-metrics into Neo4j/kuzu every 30s. Nodes: Pod, Deployment, Node, Service, PVC, HPA. Edges: OWNED_BY, SCHEDULED_ON, EXPOSES, MOUNTS, SCALES. ... **Read-only tool surface.** Wrap kubectl, Prometheus query, Loki logql, Tempo traceql through FastMCP. Every tool has a narrow RBAC verb ("get", "list", "describe"). No "delete", "exec", "scale" in the default server. ... **Evidence scoring.** Each hypothesis has a score = recency * specificity * graph-path length inverse * citation count. Return top-3. ... **Remediation gate.** Destructive tools (scale down, roll back, delete) live on a second MCP server behind an approval token. The agent can call them only after the Slack card is approved by a human. ... **Synthetic incident suite.** Build 20 scenarios: OOMKill cascade, DNS flap, HPA thrash, PVC fill, noisy neighbor, faulty sidecar, bad ConfigMap rollout, certificate rotation, image-pull backoff, etc.

## Use It · 实战用法

```
webhook: alert.pagerduty.com -> checkout-api SLO breach, error rate 14%
[graph]   affected: Deployment checkout-api (3 Pods, Node ip-10-2-3-4)
[walk]    neighbors: ReplicaSet checkout-api-abc, Service checkout-api,
           recent rollout 14m ago
[sample]  prometheus error_rate 14%, up-trend; loki 500s on /api/v2/pay
[hypo]    #1 bad rollout: latest image checkout-api:v2.41 fails /healthz
          citations: deploy.yaml (rev 42), prometheus errorRate, loki 500 stack
[slack]   [ROLL BACK to v2.40]  [ESCALATE]  [IGNORE]
          (approval required; agent does not roll back unilaterally)
```

## Ship It · 交付

`outputs/skill-devops-agent.md` 是交付物。给定一个 K8s 集群和告警源，智能体产出根因假设排序和一条 Slack 门控的修复流程。

| 权重 | 标准 | 如何衡量 |
|:-:|---|---|
| 25 | 场景套件上的 RCA 准确率 | 20 个合成事件中 ≥80% 找对根因 |
| 20 | 安全性 | 审计日志中无一次未经 Slack 批准而触发的破坏性动作 |
| 20 | 出假设时间 | 从告警到 Slack 简报 p50 低于 5 分钟 |
| 20 | 可解释性 | 每个假设都有图路径和遥测引用 |
| 15 | 集成完整度 | PagerDuty、Slack、ArgoCD、Prometheus 端到端跑通 |
| **100** | | |

> `outputs/skill-devops-agent.md` is the deliverable. Given a K8s cluster and alert source, the agent produces ranked root-cause hypotheses and a Slack-gated remediation flow.

## Exercises · 练习

1. 在 AWS DevOps Agent 被演示的同三个事件上跑你的智能体。发布并排对比。报告分歧点。

2. 加一个「未遂事件（near-miss）」审计：标记智能体*考虑过*的、若无审批即具破坏性的命令。测一周内的未遂率。

3. 把假设模型从 Claude Sonnet 4.7 换成自托管 Llama 3.3 70B。测 RCA 准确率差值和每事件美元成本。

4. 建一个因果过滤器：区分相关的遥测尖峰与真正的根因。用 20 场景标签训练一个小分类器。

5. 加回滚演练（dry-run）：用相同 manifest 对 staging 集群做 ArgoCD 回滚。在 Slack 审批按钮之前，于真实集群验证回滚计划。

> Run your agent on the same three incidents AWS's DevOps Agent is demo'd on. Publish the side-by-side. Report where the agent diverges. ... Add a "near-miss" audit that flags any command the agent *considered* that would have been destructive without approval. Measure the near-miss rate over one week. ... Swap the hypothesis model from Claude Sonnet 4.7 to a self-hosted Llama 3.3 70B. Measure RCA accuracy delta and dollar per incident. ... Build a causal filter: distinguish correlated telemetry spikes from a true root cause. Train a small classifier on the 20-scenario labels. ... Add a rollback dry-run: ArgoCD rollback against a staging cluster with the same manifest. Verify the rollback plan in a live cluster before the Slack approval button.

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|------------------------|
| K8s knowledge graph（K8s 知识图谱） | 「集群图」 | 节点 = K8s 对象 + 遥测序列；边 = 归属、调度、观测 |
| Read-only-by-default（默认只读） | 「收窄的 RBAC」 | 智能体服务账号只有 get/list/describe 动词；破坏性动词放在审批之后的独立服务器里 |
| Audit log（审计日志） | 「考虑过 vs 执行过」 | 每条候选命令的 append-only 记录：是否执行、谁批准 |
| Hypothesis ranking（假设排序） | 「证据分」 | 新近度 × 具体度 × 图路径长度倒数 × 引用数 |
| Slack approval card（Slack 审批卡） | 「HITL 门」 | 带修复按钮的交互式 Slack 消息；人点击之前智能体不得继续 |
| Telemetry citation（遥测引用） | 「证据指针」 | 支持某条论断的 Prometheus 查询、Loki 选择器或 Tempo trace URL |
| MTTR | 「恢复时长」 | 从告警触发到 SLO 恢复的墙钟时间 |

## Further Reading · 延伸阅读

- [AWS DevOps Agent GA](https://aws.amazon.com/blogs/aws/aws-devops-agent-helps-you-accelerate-incident-response-and-improve-system-reliability-preview/) — 2026 年的权威参考
- [Resolve AI K8s troubleshooting](https://resolve.ai/blog/kubernetes-troubleshooting-in-resolve-ai) — 竞品参考
- [NeuBird semantic monitoring](https://www.neubird.ai) — 语义图方案
- [Metoro AI SRE](https://metoro.io) — SLO 优先的生产视角
- [kube-state-metrics](https://github.com/kubernetes/kube-state-metrics) — 集群状态源
- [LangGraph](https://langchain-ai.github.io/langgraph/) — 参考智能体编排器
- [FastMCP](https://github.com/jlowin/fastmcp) — Python MCP 服务器框架
- [ArgoCD rollback](https://argo-cd.readthedocs.io/en/stable/user-guide/commands/argocd_app_rollback/) — 被门控的修复目标
