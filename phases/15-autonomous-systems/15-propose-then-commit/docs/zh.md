# Human-in-the-Loop: Propose-Then-Commit · 人在回路：先提议后提交（Propose-Then-Commit）

> The 2026 consensus on HITL is specific. It is not "the agent asks, the user clicks Approve." It is propose-then-commit: the proposed action is persisted to a durable store with an idempotency key; surfaced to a reviewer with intent, data lineage, permissions touched, blast radius, and a rollback plan; committed only after positive acknowledgement; verified after execution to confirm the side effect actually happened. LangGraph's `interrupt()` plus PostgreSQL checkpointing, Microsoft Agent Framework's `RequestInfoEvent`, and Cloudflare's `waitForApproval()` all implement the same shape. The canonical failure mode is the rubber-stamp approval: "Approve?" is clicked without review. The documented mitigation is challenge-and-response with an explicit checklist.

**类型:** Learn（学习）
**语言:** Python（仅标准库；带幂等性的 propose-then-commit 状态机）
**前置课程:** Phase 15 · 12（Durable execution）、Phase 15 · 14（Tripwires）
**时间:** ~60 分钟

---

## The Problem · 问题在哪

agent 采取一个动作。用户必须做决定：批准还是不批。如果决定是瞬间的，它多半不是一次审查。如果决定是有结构的，它慢但可信。工程上的问题是：**如何让有结构的审查成为阻力最小的路径。**

2023 年代的 HITL 模式是一个同步提示：「agent 想给 X 发邮件，正文是 Y——批准吗？」用户点击 Approve。所有人都觉得系统是安全的。实践中这个界面被大量「橡皮图章化」：用户批得飞快，批准记录几乎预测不了什么，而当 agent 出错时，审计轨迹里是一长串用户自己都记不起来的批准历史。

2026 年的模式——propose-then-commit——把 HITL 搬到持久化基底上，附加结构化元数据，并要求显式的正向提交。每个托管 agent SDK 都带一个版本：LangGraph `interrupt()`、Microsoft Agent Framework `RequestInfoEvent`、Cloudflare `waitForApproval()`。API 名字不同；形状是一样的。

> An agent takes an action. The user has to decide: approve or not. If the decision is instant, it is probably not a review. If the decision is structured, it is slow but trustworthy. The engineering question is how to make a structured review the path of least resistance.
> The 2023-era HITL pattern was a synchronous prompt: "Agent wants to send email to X with body Y — approve?" The user clicks Approve. Everyone feels the system is safe. In practice this surface is heavily rubber-stamped: users approve fast, approvals predict little, and when the agent goes wrong, the audit trail shows a long history of approvals the user cannot recall.
> The 2026 pattern — propose-then-commit — moves HITL onto a durable substrate, attaches structured metadata, and requires positive commit. Every managed agent SDK ships a version: LangGraph `interrupt()`, Microsoft Agent Framework `RequestInfoEvent`, Cloudflare `waitForApproval()`. The API names differ; the shape does not.

---

## The Concept · 概念

### The propose-then-commit state machine · propose-then-commit 状态机

1. **提议（Propose）。** agent 产出一个提议动作。持久化到一个持久化存储（PostgreSQL、Redis、Durable Object）。内容包括：
   - 意图（intent，agent 为什么要做这件事）
   - 数据谱系（data lineage，什么来源内容导致了这个提议）
   - 触及的权限（permissions touched，哪些作用域 / 文件 / 端点）
   - 爆炸半径（blast radius，最坏情况是什么）
   - 回滚计划（rollback plan，如果提交了，我们怎么撤销）
   - 幂等键（idempotency key，每个提议唯一；重复提交返回同一条记录）
2. **呈报（Surface）。** 审查者看到带全部元数据的提议。审查者是人（不是 agent 自己审自己）。
3. **提交（Commit）。** 显式的正向确认。动作执行。
4. **验证（Verify）。** 执行之后，把副作用读回来并确认。如果验证步骤失败，系统处于一个已知的坏状态，告警启动。

> 1. **Propose.** Agent produces a proposed action. Persisted to a durable store (PostgreSQL, Redis, Durable Object). Includes:
>    - intent (why is the agent doing this)
>    - data lineage (what source led to this proposal)
>    - permissions touched (which scopes / files / endpoints)
>    - blast radius (what is the worst case)
>    - rollback plan (if committed, how do we undo it)
>    - idempotency key (unique per proposal; resubmission returns the same record)
> 2. **Surface.** Reviewer sees the proposal with all metadata. The reviewer is a person (not the agent reviewing itself).
> 3. **Commit.** Positive acknowledgement. The action executes.
> 4. **Verify.** After execution, the side effect is read back and confirmed. If the verify step fails, the system is in a known bad state and alerting engages.

### The idempotency key · 幂等键

没有幂等键，一次瞬时故障后的重试可能把一个已批准的动作执行两遍。具体例子：用户批准「从 A 向 B 转账 $100」。网络抖动。工作流重试。用户只批准过一次，但转账执行了两次。幂等键把批准绑定到一个单一、唯一的副作用上；第二次执行是空操作（no-op）。

这与 Stripe 和 AWS API 用的幂等模式是同一个。把它复用于 agent 批准，在 Microsoft Agent Framework 文档里有明确说明。

> Without an idempotency key, a retry after a transient failure can double-execute an approved action. Concrete example: user approves "transfer $100 from A to B." Network blips. Workflow retries. The user has approved once but the transfer executes twice. The idempotency key ties the approval to a single, unique side effect; the second execution is a no-op.
> This is the same idempotency pattern Stripe and AWS APIs use. Reusing it for agent approvals is explicit in the Microsoft Agent Framework docs.

### Durability: why approvals outlast processes · 持久化：为什么批准能活得比进程久

批准的「候诊室」是一块 agent 不拥有的状态。工作流处于暂停态（第 12 课）。当批准到达时，工作流从恰好那个点恢复。这就是为什么 LangGraph 让 `interrupt()` 与 PostgreSQL 检查点搭配，而不只是内存状态——两天后才来的批准，依然能找到完好无损的工作流。

> The approval waiting room is a piece of state the agent does not own. The workflow is paused (Lesson 12). When the approval arrives, the workflow resumes from exactly that point. This is why LangGraph pairs `interrupt()` with PostgreSQL checkpointing and not just in-memory state — an approval two days later still finds the workflow intact.

### Rubber-stamp approvals and the challenge-and-response mitigation · 橡皮图章批准与「挑战-应答」缓解

HITL 的默认 UI（「Approve」/「Reject」按钮）产出的是没有真实审查的快速批准。有据可查的缓解办法：一张「挑战-应答」清单（challenge-and-response），要求对具体问题给出正向回答之后，Approve 按钮才被启用。具体形状：

- 「你理解这触及的是什么资源吗？[ ]」
- 「你验证过爆炸半径可以接受吗？[ ]」
- 「如果失败，你有回滚计划吗？[ ]」

这不是为官僚而官僚——这是一个强制函数（forcing function）。打不了勾的审查者要么去追问细节（升级），要么拒绝（安全默认）。Anthropic 的 agent 安全研究明确把清单驱动的 HITL 列为橡皮图章批准模式的缓解手段。

> The default UI for HITL ("Approve" / "Reject" buttons) produces fast approvals with no genuine review. Documented mitigation: a challenge-and-response checklist that requires positive answers to specific questions before the Approve button is enabled. Concrete shape:
> - "Do you understand what resource this touches? [ ]"
> - "Have you verified the blast radius is acceptable? [ ]"
> - "Do you have a rollback plan if this fails? [ ]"
> Not bureaucracy for its own sake — a forcing function. The reviewer who cannot tick the boxes either asks for clarification (escalation) or declines (safe default). The Anthropic agent-safety research explicitly cites checklist-driven HITL as a mitigation for rubber-stamp approval patterns.

### What counts as consequential · 什么算「有后果」

不是每个动作都需要 propose-then-commit。2026 年的指引：

- **有后果的动作**（必须 HITL）：不可逆写入、金融交易、对外通信、生产数据库变更、破坏性文件系统操作。
- **可逆动作**（偶尔 HITL）：本地文件编辑、staging 环境变更、有清晰回滚的可逆写入。
- **读取与检查**（永远不 HITL）：读文件、列资源、调用只读 API。

> Not every action needs propose-then-commit. The 2026 guidance:
> - **Consequential actions** (always HITL): irreversible writes, financial transactions, outbound communication, production database changes, destructive file-system operations.
> - **Reversible actions** (sometimes HITL): edits to local files, staging-env changes, reversible writes with clear rollback.
> - **Reads and inspections** (never HITL): reading a file, listing resources, calling a read-only API.

### Post-action verification · 动作后验证

「提交跑过了」不等于「副作用发生了」。网络分区和竞态条件可能产出一个自认为成功、而后端其实没持久化的工作流。验证步骤在提交之后重新读取目标资源来确认。这与数据库事务里带 `RETURNING` 子句、或 AWS 在 `PutObject` 之后 `GetObject` 的模式是同一个。

> "The commit ran" is not the same as "the side effect happened." Network-partition and race conditions can produce a workflow that thinks it succeeded while the backend did not persist. The verify step re-reads the target resource after commit to confirm. This is the same pattern as database transactions with `RETURNING` clauses or AWS `GetObject` after `PutObject`.

### EU AI Act Article 14 · EU AI Act 第 14 条

第 14 条要求欧盟的高风险 AI 系统具备有效的人类监督。「有效」不是装饰性的。监管语言明确排除了橡皮图章模式。在 Microsoft Agent Governance Toolkit 的合规文档里，带「挑战-应答」的 propose-then-commit 就是能在第 14 条审查下站得住的形状。

```figure
mx-propose-then-commit
```

> Article 14 mandates effective human oversight for high-risk AI systems in the EU. "Effective" is not decorative. Regulatory language specifically excludes rubber-stamp patterns. Propose-then-commit with challenge-and-response is the shape that survives Article 14 scrutiny in the Microsoft Agent Governance Toolkit compliance docs.

---

## Use It · 实战用法

`code/main.py` 用标准库 Python 实现一个 propose-then-commit 状态机。持久化存储是一个 JSON 文件。幂等键是 (thread_id, action_signature) 的哈希。驱动脚本模拟三种情况：一次干净的批准流程、一次瞬时故障后的重试（绝不能重复执行），以及橡皮图章默认流程对比「挑战-应答」流程。

> `code/main.py` implements a propose-then-commit state machine in stdlib Python. Durable store is a JSON file. Idempotency key is a hash of (thread_id, action_signature). The driver simulates three cases: a clean approval flow, a retry after transient failure (which must not double-execute), and a rubber-stamp default versus a challenge-and-response flow.

---

## Ship It · 交付

`outputs/skill-hitl-design.md` 审查一个拟议的 HITL 工作流是否符合 propose-then-commit 形状，并标出缺失的元数据、幂等性、验证或「挑战-应答」层。

> `outputs/skill-hitl-design.md` reviews a proposed HITL workflow for propose-then-commit shape and flags missing metadata, idempotency, verification, or challenge-and-response layers.

---

## Exercises · 练习

1. 运行 `code/main.py`。确认对已批准提议的重试使用持久化记录、不会重复执行。然后把幂等键改成包含时间戳，展示重试导致重复执行。
2. 给提议记录加一个 `rollback` 字段。模拟一次验证步骤失败的执行。展示回滚自动触发。
3. 读 Microsoft Agent Framework 的 `RequestInfoEvent` 文档。找出 API 里有而玩具引擎缺失的一个元数据字段。把它加上，并解释它防的是什么。
4. 为一个具体动作设计「挑战-应答」清单（例如「发帖到公开的 Twitter 账号」）。审查者必须回答哪三个问题？为什么是这三个？
5. 挑出一个同步「批准吗？」提示就足够（不需要持久化存储）的场景。解释为什么，并说出你因此接受的风险类别。

> 1. Run `code/main.py`. Confirm that a retry of an approved proposal uses the durable record and does not re-execute. Now change the idempotency key to include a timestamp and show the retry double-executes.
> 2. Extend the proposal record with a `rollback` field. Simulate an execution whose verify step fails. Show the rollback firing automatically.
> 3. Read Microsoft Agent Framework's `RequestInfoEvent` docs. Identify one metadata field the API includes that the toy engine is missing. Add it and explain what it protects against.
> 4. Design a challenge-and-response checklist for a specific action (e.g., "post to a public Twitter account"). What three questions must the reviewer answer? Why those three?
> 5. Pick one case where a synchronous "Approve?" prompt would be sufficient (no durable store needed). Explain why, and name the risk class you are accepting.

---

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|---|---|---|
| Propose-then-commit | 「两阶段批准」 | 持久化提议 + 显式提交 + 验证 |
| Idempotency key | 「重试安全令牌」 | 每个提议唯一；第二次执行为空操作 |
| Data lineage | 「它从哪来」 | 导致这个提议的具体来源内容 |
| Blast radius | 「最坏情况」 | 动作出错时的影响范围 |
| Rubber-stamp | 「秒批」 | 没有真实审查就点下「Approve」 |
| Challenge-and-response | 「强制清单」 | 审查者必须对具体问题给出正向确认 |
| RequestInfoEvent | 「MS Agent Framework 原语」 | 带结构化元数据的持久化 HITL 请求 |
| `interrupt()` / `waitForApproval()` | 「框架原语」 | LangGraph / Cloudflare 的同形等价物 |

---

## Further Reading · 延伸阅读

- [Microsoft Agent Framework — Human in the loop](https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop) — `RequestInfoEvent`、持久化批准。
- [Cloudflare Agents — Human in the loop](https://developers.cloudflare.com/agents/concepts/human-in-the-loop/) — `waitForApproval()` 与 Durable Objects。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — HITL 作为长程风险的缓解手段。
- [EU AI Act — Article 14: Human oversight](https://artificialintelligenceact.eu/article/14/) — 高风险系统的监管基线。
- [Anthropic — Claude's Constitution (January 2026)](https://www.anthropic.com/news/claudes-constitution) — 围绕监督的宪法式框架。
