# Checkpoints and Rollback · 检查点与回滚

> Every graph-state transition persists. When a worker crashes, its lease expires and another worker picks up at the latest checkpoint. Cloudflare Durable Objects hold state across hours or weeks. Propose-then-commit (Lesson 15) defines a rollback plan per action. Post-action verification closes the loop. EU AI Act Article 14 makes effective human oversight mandatory for high-risk systems — in practice this means checkpoints must be queryable, rollbacks must be rehearsed, and the audit trail must survive a deploy. The sharp failure mode: without idempotency keys and precondition checks, a retry after a transient failure can double-execute an already-approved action. Post-action verification is what catches it.

**类型:** Learn（学习）
**语言:** Python（仅标准库；检查点与回滚状态机）
**前置课程:** Phase 15 · 12（Durable execution）、Phase 15 · 15（Propose-then-commit）
**时间:** ~60 分钟

---

## The Problem · 问题在哪

持久化执行（第 12 课）让崩溃的 agent 可以恢复。Propose-then-commit（第 15 课）让被批准的动作可审计。本课把两者接起来：当一个已批准的动作执行到一半、崩溃、然后恢复时，会发生什么？回滚在什么时候运行？针对什么状态运行？

真实系统的接线方式各不相同：

- **LangGraph** 把每一次图状态转移检查点到 PostgreSQL。worker 崩溃时，租约（lease）释放，另一个 worker 从最新检查点恢复。工作流在 `interrupt()` 上暂停，而这个暂停本身也是持久的。
- **Cloudflare Durable Objects** 以键为单位把状态保存数小时到数周。把计算与存储同址放置，服务于已批准的动作。
- **Microsoft Agent Framework** 在工作流 API 里暴露 `Checkpoint` 原语；重放加幂等性覆盖了重试。

在所有这些情况里，真正管用的组合是：**幂等键（防止重复执行）+ 前置条件检查（状态仍然是我们批准时依据的状态）+ 动作后验证（副作用确实发生了）+ 验证失败时的回滚**。

> Durable execution (Lesson 12) makes a crashed agent resumable. Propose-then-commit (Lesson 15) makes an approved action auditable. This lesson joins them: what happens when an approved action executes partially, crashes, and resumes? When does the rollback run, and against what state?
> Real systems wire this up differently:
> - **LangGraph** checkpoints every graph-state transition to PostgreSQL. On worker crash, the lease releases and another worker resumes at the latest checkpoint. Workflows pause on `interrupt()`, which itself persists.
> - **Cloudflare Durable Objects** hold per-key state across hours or weeks. Co-locate the computation with the storage for the approved action.
> - **Microsoft Agent Framework** exposes `Checkpoint` primitives in the workflow API; replay plus idempotency covers retries.
> In every case, the combination that actually works is: idempotency key (prevents double-execute) + precondition check (state is still what we approved against) + post-action verify (the side effect actually happened) + rollback on verify-fail.

---

## The Concept · 概念

### Every transition persists · 每一次转移都持久化

图状态转移是任何把工作流从一个命名状态移到另一个命名状态的步骤。朴素的实现只在特定的提交点持久化；生产实现持久化每一次转移。代价（多几次写入）相对于可靠性收益（重放可以落在任何位置、租约恢复是精确的）是很小的。

> A graph-state transition is any step that moves the workflow from one named state to another. Naive implementations persist only at specific commit points; production implementations persist every transition. The cost (a few extra writes) is small relative to the reliability gain (replay lands anywhere, lease recovery is precise).

### Lease recovery · 租约恢复

worker 崩溃时，工作流并没有丢；租约（一份「这个 worker 正在执行这次运行」的短时效声明）只是过期了。另一个 worker 拾起最新检查点并恢复。租约机制正是生产系统能在滚动部署中存活而不丢失在途工作的原因。

> When a worker crashes, the workflow is not lost; the lease (a short-lived claim that this worker is executing this run) simply expires. Another worker picks up the latest checkpoint and resumes. The lease mechanism is what lets production systems survive rolling deploys without losing in-flight work.

### Idempotency plus preconditions · 幂等性加前置条件

只有幂等性是不够的。设想：一个工作流被批准「当余额 > $1000 时，从 A 向 B 转账 $100」。工作流被提交，执行中途崩溃，然后恢复。如果只检查幂等键，执行恢复后转账只跑一次（正确）。但设想在崩溃与恢复之间，A 的余额因为另一个工作流降到了 $500。幂等检查依然通过；前置条件不再通过。**没有前置条件检查，我们就交付了一张透支。**

每一个有后果的动作都需要两者：

- **幂等键**：防止重复执行。
- **前置条件检查**：确认状态仍然与被批准的内容一致。

> Idempotency alone is not enough. Consider: a workflow is approved to "transfer $100 from A to B when balance > $1000." The workflow is committed, crashes mid-execution, and resumes. If only the idempotency key is checked, and the execution resumes, the transfer runs once (correct). But consider that between crash and resume, A's balance drops to $500 via a different workflow. The idempotency check still passes; the precondition does not. Without a precondition check, we ship an overdraft.
> Every consequential action needs both:
> - **Idempotency key**: prevents double-execute.
> - **Precondition check**: confirms the state is still consistent with what was approved.

### Post-action verification · 动作后验证

「工具返回了 200」不是验证。真正的验证会重新读取目标状态，确认副作用确实发生了。模式：

- 数据库更新：`UPDATE ... RETURNING *`，然后断言返回的行匹配预期状态。
- 邮件发送：提交后检查已发送文件夹里的消息 ID。
- 文件写入：把文件读回来做哈希。
- API 调用：对目标资源做一次后续 `GET`。

如果验证失败，工作流处于一个已知坏状态。回滚启动。

> "The tool returned 200" is not verification. Real verification re-reads the target state and confirms the side effect actually happened. Patterns:
> - Database update: `UPDATE ... RETURNING *` then assert the returned row matches intended state.
> - Email send: check sent-folder for the message ID after submission.
> - File write: read the file back and hash it.
> - API call: follow-up `GET` on the target resource.
> If verify fails, the workflow is in a known-bad state. Rollback engages.

### Rollback plans · 回滚计划

propose-then-commit（第 15 课）里的每一个有后果的动作都携带一个回滚计划。类型：

- **带内回滚（In-band rollback）**：直接逆转副作用（`INSERT` 之后 `DELETE`，发送之后发「更正邮件」）。
- **补偿事务（Compensating transaction）**：一个抵消原动作的新动作（标准 SAGA 模式）。
- **带外回滚（Out-of-band rollback）**：告警一个人、暂停工作流、把坏状态留给调查。

空操作回滚（「我们无法撤销这个」）必须在提议里被明确写出。没有回滚的动作在提交时需要更强的 HITL（第 15 课的挑战-应答）。

> Every consequential action in propose-then-commit (Lesson 15) carries a rollback plan. Types:
> - **In-band rollback**: reverse the side effect directly (`DELETE` after `INSERT`, `Send-correction-email` after send).
> - **Compensating transaction**: a new action that neutralizes the original (standard SAGA pattern).
> - **Out-of-band rollback**: alert a human, pause the workflow, leave the bad state for investigation.
> No-op rollback ("we cannot undo this") must be named in the proposal. Actions with no rollback require stronger HITL at commit time (Lesson 15 challenge-and-response).

### EU AI Act Article 14 operational reading · EU AI Act 第 14 条的运营化解读

第 14 条要求高风险系统具备「有效的人类监督」。在运营层面，实现者把它读作：

- 检查点可被审计者查询。
- 回滚被演练过（至少端到端测试过一次）。
- 审计轨迹能挺过一次部署（检查点后端不是易失的）。
- 失败的验证会触发告警，而不是被悄悄记进日志。

一个在提交中途崩溃、恢复、并且在没有验证 + 回滚通路的情况下完成副作用的工作流，过不了第 14 条的检验。

> Article 14 requires "effective human oversight" for high-risk systems. In operational terms, implementers read it as:
> - Checkpoints are queryable by an auditor.
> - Rollbacks are rehearsed (tested end-to-end at least once).
> - The audit trail survives a deploy (checkpoint backend is not ephemeral).
> - Failed verifications are alerted on, not silently logged.
> A workflow that crashes mid-commit, resumes, and completes the side effect without a verify + rollback pathway does not survive the Article 14 test.

### The sharp failure mode: the double-execute · 最锋利的失败模式：重复执行

这个领域最常见的生产事故：

1. 动作已批准，幂等键为 k。
2. 提交开始，执行，返回 200。
3. 工作流在持久化「已提交」状态之前崩溃。
4. 工作流恢复；看到「已批准但未提交」；重新执行。
5. 副作用触发两次。

缓解：在执行之前持久化一个「进行中（in-flight）」意图，带幂等键执行，然后只在动作后验证成功之后才标记「已提交」。如果动作触发而状态写入失败，你知道要去验证、并且（必要时）重新触发。如果状态写入成功而动作失败，你通过恢复路径验证并恰好触发一次。

```figure
checkpoint-replay
```

> The most common production incident in this space:
> 1. Action approved, idempotency key k.
> 2. Commit starts, executes, returns 200.
> 3. Workflow crashes before persisting the "committed" status.
> 4. Workflow resumes; sees "approved but not committed"; re-executes.
> 5. Side effect fires twice.
> Mitigation: persist an "in-flight" intent before execution, execute with an idempotency key, then mark "committed" only after post-action verification succeeds. If the action fires and the status write fails, you know to verify and (if necessary) re-fire. If the status write succeeds and the action fails, you verify and fire exactly once via the recovery path.

---

## Use It · 实战用法

`code/main.py` 实现一个带幂等性、前置条件、验证和回滚的检查点工作流。驱动脚本模拟四个场景：干净运行、崩溃后重试（幂等性抓住）、前置条件失败（工作流中止而不触发动作）、验证失败（回滚触发）。

> `code/main.py` implements a checkpointed workflow with idempotency, preconditions, verify, and rollback. The driver simulates four scenarios: clean run, retry after crash (idempotency catches), precondition fail (workflow aborts without firing), verify fail (rollback fires).

---

## Ship It · 交付

`outputs/skill-rollback-rehearsal.md` 为一个拟议工作流设计回滚演练测试，并审计检查点后端的审计轨迹持久性。

> `outputs/skill-rollback-rehearsal.md` designs a rollback-rehearsal test for a proposed workflow and audits the checkpoint backend for audit-trail persistence.

---

## Exercises · 练习

1. 运行 `code/main.py`。验证四个场景。对于提交中途崩溃的情况，确认跨多次重试动作恰好触发一次。
2. 修改「先标记完成、再做事」的模式，让状态写入发生在动作之后。重跑崩溃场景。测量有多少重复动作被触发。
3. 为一个具体的生产动作设计回滚计划（例如「发帖到某个 Slack 频道」）。归类为带内、补偿或带外。为这个选择给出理由。
4. 取一个你熟悉的工作流。找出每一次状态转移。为每一次标注持久化要求（持久化 / 不持久化）。数一数你目前没有持久化的有多少个。
5. 回滚演练测试：设计一个端到端测试，运行一个真实工作流、让它崩溃、并确认回滚路径触发。这个测试断言什么？

> 1. Run `code/main.py`. Verify the four scenarios. For the crash-during-commit case, confirm the action fires exactly once across retries.
> 2. Modify the "mark as done first, then do it" pattern so the status write fires after the action. Rerun the crash scenario. Measure how many duplicate actions fire.
> 3. Design a rollback plan for a specific production action (e.g., "post to a Slack channel"). Classify as in-band, compensating, or out-of-band. Justify the choice.
> 4. Take one workflow you know. Identify every state transition. Mark each with a durability requirement (persist / do not persist). Count the ones you are currently not persisting.
> 5. Rehearsed-rollback test: design an end-to-end test that runs a real workflow, crashes it, and confirms the rollback path fires. What does the test assert?

---

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|---|---|---|
| Checkpoint | 「存档点」 | 每一次图状态转移都持久化到持久化存储 |
| Lease | 「worker 声明」 | 一份「worker 正在执行某次运行」的短时效声明；崩溃即过期 |
| Precondition | 「状态闸门」 | 断言状态仍然与已批准的动作一致 |
| Post-action verify | 「读回检查」 | 确认副作用确实在目标系统里发生了 |
| In-band rollback | 「直接撤销」 | 用逆操作逆转副作用 |
| Compensating transaction | 「SAGA 撤销」 | 一个抵消原动作的新动作 |
| Mark-as-done-first | 「状态写入顺序」 | 在从提交返回之前先持久化「已提交」状态 |
| Article 14 | 「EU AI Act 人类监督」 | 运营含义：可查询的检查点、演练过的回滚、可审计的轨迹 |

---

## Further Reading · 延伸阅读

- [Microsoft Agent Framework — Checkpointing and HITL](https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop) — 检查点原语与租约恢复。
- [Cloudflare Agents — Human in the loop](https://developers.cloudflare.com/agents/concepts/human-in-the-loop/) — 作为状态基底的 Durable Objects。
- [EU AI Act — Article 14: Human oversight](https://artificialintelligenceact.eu/article/14/) — 监管基线。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 长程工作流的可靠性框架。
- [Anthropic — Claude Code Agent SDK: agent loop](https://code.claude.com/docs/en/agent-sdk/agent-loop) — Claude Code Routines 的工作流形状。
