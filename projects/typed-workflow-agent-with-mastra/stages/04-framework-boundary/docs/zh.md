# Persist real Mastra approval state and resume it · 持久化真实的 Mastra 审批状态并恢复它

> 启动编写好的 workshop update，观察 status=suspended 且零次工具调用。关闭本地 LibSQL 存储，在同一个 SQLite 文件上创建一个全新的工作流，并通过 runId 恢复。在恢复测试中，匹配的审批产生 success 且恰好一次被观察到的本地工具调用；错误的哈希则以零次调用失败。

> Start the authored workshop update and observe status=suspended with zero tool calls. Close the local LibSQL store, create a fresh workflow over the same SQLite file and resume by runId. Matching approval produces success and exactly one observed local tool call in the recovery test; a wrong hash fails with zero calls.

**Type:** Build
**Stage:** 4 of 4
**Time:** About 2 hours

## The useful boundary · 有用的边界

用 Zod 契约组合三个真实的 Mastra 步骤（step）：classify、plan、execute。当 update 缺少审批时，执行步骤会调用 Mastra 的 suspend，并带上 ticketId、planHash、plan 和 reason。恢复（resume）时，它先对照存储的计划校验 approved、ticketId 和 planHash，然后再调用共享的 scratch 执行器。

```figure
pj-typed-workflow-agent-with-mastra-4
```

> Compose three real Mastra steps with Zod contracts: classify, plan and execute. The execution step calls Mastra suspend with ticketId, planHash, plan and reason when an update lacks approval. On resume, it validates approved, ticketId and planHash against the stored plan before calling the shared scratch executor.

## Work the example · 做一遍示例

启动编写好的 workshop update，观察 status=suspended 且零次工具调用。关闭本地 LibSQL 存储，在同一个 SQLite 文件上创建一个全新的工作流，并通过 runId 恢复。在恢复测试中，匹配的审批产生 success 且恰好一次被观察到的本地工具调用；错误的哈希则以零次调用失败。

在写代码之前，先写下要返回的字段和预期的副作用（side-effect）次数。保留一个应当失败的第二个输入，这样成功的示例就无法变成硬编码的答案。

> Start the authored workshop update and observe status=suspended with zero tool calls. Close the local LibSQL store, create a fresh workflow over the same SQLite file and resume by runId. Matching approval produces success and exactly one observed local tool call in the recovery test; a wrong hash fails with zero calls.
> Write the returned fields and the expected side-effect count before coding. Keep a second input that should fail so the successful example cannot become a hard-coded answer.

## Build the contract · 构建契约

在你的学习者工作区（learner workspace）里实现 `createTicketWorkflow, planHash, persistentWorkflow in optional-mastra/adapter.ts`。保留导出的名称，并继续复用此前阶段（stage）的成果，而不是把它们的策略再复制一遍。

默认工厂使用 InMemoryStore 便于轻量测试。persistentWorkflow 需要显式的 file: URL，且要求 @mastra/libsql 1.23.3 搭配 @mastra/core 1.71.0 与 Zod 4.3.6。CLI 会写出 approved=false 的 approval.json。查看存储的计划，显式地编辑审批内容，然后运行单独的恢复命令。一个 false 的决定会保持 suspended。

> Implement `createTicketWorkflow, planHash, persistentWorkflow in optional-mastra/adapter.ts` in your learner workspace. Preserve the exported names and continue using earlier stages rather than duplicating their policies.
> The default factory uses InMemoryStore for lightweight tests. persistentWorkflow requires an explicit file: URL and @mastra/libsql 1.23.3 alongside @mastra/core 1.71.0 and Zod 4.3.6. The CLI writes approval.json with approved=false. Inspect the stored plan, explicitly edit approval and run the separate resume command. A false decision remains suspended.

## Hints · 提示

通过 `project_test.py --optional --strict` 运行教师所有的可选测试。适配器触发的是真实的 SDK 挂起与恢复；不要仅仅因为 scratch 策略本会暂停就抛出异常。使用返回的 run ID，绝不要用一个新的输入去冒充恢复。

> Run instructor-owned optional tests through project_test.py --optional --strict. The adapter invokes actual SDK suspension and resume; do not throw merely because the scratch policy would pause. Use the returned run ID, never start a new input to imitate a resume.

## Verify your work · 验证你的成果

```bash
python3 scripts/project_test.py typed-workflow-agent-with-mastra --init my-typed-workflow-agent-with-mastra
python3 scripts/project_test.py typed-workflow-agent-with-mastra --stage 4 --path my-typed-workflow-agent-with-mastra --strict
```

只需初始化一次。累积测试（cumulative tests）会导入你的工作区并保留你早先的源码。运行参考实现（reference solution）验证的是教学实现，永远不会给学习者颁发证书。可选的 SDK 检查需要项目 README 中的依赖和命令。

> Initialize once. Cumulative tests import your workspace and preserve your earlier source. A reference-solution run verifies the teaching implementation and never grants a learner certificate. Optional SDK checks require the dependencies and commands in the project README.

## Inspect the result · 检查结果

哪些状态能在进程重启后存活？哪些外部副作用仍然需要幂等性？你会如何接入一个经过身份认证的评审 UI，而不信任模型去批准它自己的计划？

完成整个项目后，你会得到一份 scratch 版的 HTML/JSON 工作流评审，以及一次真实的 Mastra 运行：结果存入 SQLite，并附带一份与计划绑定的审批文档（plan-bound approval document）。

```bash
cd projects/typed-workflow-agent-with-mastra/solution
node --experimental-strip-types cli.ts --ticket fixtures/ticket.json --out workflow-output
```

把这个 fixture 换成来自你自己工作流的一小段输入。把预期结果和观察到的证据放在一起保存，另外再留一组单独的用例用于评估。Provider 请求测试证明的是序列化和控制流，而不是模型质量。

> Which state survives a process restart and which external effects still need idempotency? How would you connect an authenticated review UI without trusting a model to approve its own plan?
> The completed project produces a scratch HTML/JSON workflow review and a real Mastra run stored in SQLite with a plan-bound approval document.
> Replace the fixture with a small input from your own workflow. Keep expected outcomes and observed evidence together, then retain a separate set of cases for evaluation. Provider request tests establish serialization and control flow; they do not establish model quality.

## Primary reference · 主要参考

[官方 API 文档](https://mastra.ai/docs/workflows/suspend-and-resume)。实现、策略选择和示例均为原创。

> [Official API documentation](https://mastra.ai/docs/workflows/suspend-and-resume). The implementation, policy choices and examples are original.
