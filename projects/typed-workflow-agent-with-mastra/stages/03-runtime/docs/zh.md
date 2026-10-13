# Suspend before effects and count failed attempts · 在产生副作用之前挂起并统计失败次数

> 返回结果的 lookup 一次调用即完成；两次都返回空文本的工具在两次调用后失败。未获批准的写入返回一个检查点（checkpoint）且零次调用；用 approved=true 恢复该检查点时会执行原始 query。

> A lookup returning a result completes in one call. A tool returning empty text twice fails after two calls. A write without approval returns a checkpoint and zero calls; resuming that checkpoint with approved=true executes the original query.

**Type:** Build
**Stage:** 3 of 4
**Time:** About 2 hours

## The useful boundary · 有用的边界

在共享调用预算（shared call budget）和单动作重试上限（per-action retry bound）的双重约束下执行注入的工具。失败的调用同样消耗预算。未经批准的写入在任何工具调用发生之前就返回 suspended 状态，并附带一份分离的计划（detached plan）。空的工具输出按失败计，因为它提供不了任何可用的答案。

```figure
pj-typed-workflow-agent-with-mastra-3
```

> Execute an injected tool under both a shared call budget and a per-action retry bound. Failed calls consume the budget. Unapproved writes return suspended with a detached plan before any tool call. Empty tool output counts as failure because it provides no usable answer.

## Work the example · 做一遍示例

返回结果的 lookup 一次调用即完成。两次都返回空文本的工具在两次调用后失败。未获批准的写入返回一个检查点且零次调用；用 approved=true 恢复该检查点时会执行原始 query。

在写代码之前，先写下要返回的字段和预期的副作用（side-effect）次数。保留一个应当失败的第二个输入，这样成功的示例就无法变成硬编码的答案。

> A lookup returning a result completes in one call. A tool returning empty text twice fails after two calls. A write without approval returns a checkpoint and zero calls; resuming that checkpoint with approved=true executes the original query.
> Write the returned fields and the expected side-effect count before coding. Keep a second input that should fail so the successful example cannot become a hard-coded answer.

## Build the contract · 构建契约

在你的学习者工作区（learner workspace）里实现 `executePlan(plan, tool, options), runTicket(raw, tool, options) in main.ts`。保留导出的名称，并继续复用此前阶段（stage）的成果，而不是把它们的策略再复制一遍。

这个 scratch 运行时存在于内存中，在工具调用期间没有崩溃恢复。CLI 中使用的工具都是明确的本地模拟。真实的写操作需要幂等键（idempotency keys），因为网络故障可能发生在远端系统已经执行了动作之后、响应到达之前。

> Implement `executePlan(plan, tool, options), runTicket(raw, tool, options) in main.ts` in your learner workspace. Preserve the exported names and continue using earlier stages rather than duplicating their policies.
> The scratch runtime is in memory and has no crash recovery during a tool call. Tools used in the CLI are explicitly local simulations. Real writes need idempotency keys because a network failure can occur after a remote system applied the action but before the response arrived.

## Hints · 提示

注入一个会记录每次调用的工具。同时断言返回的状态和实际的调用列表。在进入循环之前先校验预算。让 suspended 与 failed 保持区别，这样评审队列可以恢复工作，而不是把一个错误再重试一遍。

> Inject a tool that records each invocation. Assert both the returned status and the actual call list. Validate budgets before entering loops. Keep suspended distinct from failed so a review queue can resume work rather than retrying an error.

## Verify your work · 验证你的成果

```bash
python3 scripts/project_test.py typed-workflow-agent-with-mastra --init my-typed-workflow-agent-with-mastra
python3 scripts/project_test.py typed-workflow-agent-with-mastra --stage 3 --path my-typed-workflow-agent-with-mastra --strict
```

只需初始化一次。累积测试（cumulative tests）会导入你的工作区并保留你早先的源码。运行参考实现（reference solution）验证的是教学实现，永远不会给学习者颁发证书。可选的 SDK 检查需要项目 README 中的依赖和命令。

> Initialize once. Cumulative tests import your workspace and preserve your earlier source. A reference-solution run verifies the teaching implementation and never grants a learner certificate. Optional SDK checks require the dependencies and commands in the project README.

## Inspect the result · 检查结果

为什么一次失败的调用必须计入预算？什么样的证据能把「挂起中的工作流」和「写入已完成但响应丢失」区分开？

完成整个项目后，你会得到一份 scratch 版的 HTML/JSON 工作流评审，以及一次真实的 Mastra 运行：结果存入 SQLite，并附带一份与计划绑定的审批文档（plan-bound approval document）。

```bash
cd projects/typed-workflow-agent-with-mastra/solution
node --experimental-strip-types cli.ts --ticket fixtures/ticket.json --out workflow-output
```

把这个 fixture 换成来自你自己工作流的一小段输入。把预期结果和观察到的证据放在一起保存，另外再留一组单独的用例用于评估。Provider 请求测试证明的是序列化和控制流，而不是模型质量。

> Why must a failed call count toward the budget? What evidence distinguishes a suspended workflow from a completed write whose response was lost?
> The completed project produces a scratch HTML/JSON workflow review and a real Mastra run stored in SQLite with a plan-bound approval document.
> Replace the fixture with a small input from your own workflow. Keep expected outcomes and observed evidence together, then retain a separate set of cases for evaluation. Provider request tests establish serialization and control flow; they do not establish model quality.

## Primary reference · 主要参考

[官方 API 文档](https://mastra.ai/docs/workflows/suspend-and-resume)。实现、策略选择和示例均为原创。

> [Official API documentation](https://mastra.ai/docs/workflows/suspend-and-resume). The implementation, policy choices and examples are original.
