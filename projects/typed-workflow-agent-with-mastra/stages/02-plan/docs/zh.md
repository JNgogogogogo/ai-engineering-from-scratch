# Make the approval invariant explicit in the plan · 在计划中显式声明审批不变量

> 带 requiresApproval=false 的 update 动作会失败；只含查找（lookup-only）的计划配上 requiresApproval=true 同样违反所声明的表示。允许 1 到 10 个动作，且每个动作都有受支持的工具和非空的 query。

> An update action with requiresApproval=false fails. A lookup-only plan with requiresApproval=true also violates the stated representation. One through ten actions are allowed, and every action has a supported tool and nonempty query.

**Type:** Build
**Stage:** 2 of 4
**Time:** About 2 hours

## The useful boundary · 有用的边界

读取（read）分类产生 lookup；写入（write）分类产生 update。执行时还要对生成的计划再做一次校验，因为它可能已经被序列化或编辑过。requiresApproval 标志必须等于「是否存在 update 动作」。这能防止一个布尔值悄悄关掉一道闸门。

```figure
pj-typed-workflow-agent-with-mastra-2
```

> A read classification creates lookup; a write classification creates update. Validate the resulting plan again at execution because it may have been serialized or edited. The requiresApproval flag must equal whether any action is update. This prevents one boolean from silently disabling a gate.

## Work the example · 做一遍示例

带 requiresApproval=false 的 update 动作会失败；只含查找（lookup-only）的计划配上 requiresApproval=true 同样违反所声明的表示。允许 1 到 10 个动作，且每个动作都必须使用受支持的工具、携带非空的 query。

在写代码之前，先写下要返回的字段和预期的副作用（side-effect）次数。保留一个应当失败的第二个输入，这样成功的示例就无法变成硬编码的答案。

> An update action with requiresApproval=false fails. A lookup-only plan with requiresApproval=true also violates the stated representation. One through ten actions are allowed, and every action has a supported tool and nonempty query.
> Write the returned fields and the expected side-effect count before coding. Keep a second input that should fail so the successful example cannot become a hard-coded answer.

## Build the contract · 构建契约

在你的学习者工作区（learner workspace）里实现 `makePlan(classification), validatePlan(plan) in main.ts`。保留导出的名称，并继续复用此前阶段（stage）的成果，而不是把它们的策略再复制一遍。

这个 scratch 检查点只是本地 JSON，不是经过认证的授权。可选的框架会存储真实的计划，并把审批绑定到它的摘要（digest）和工单 ID 上。摘要能发现上下文不匹配；它不能识别是谁批准了这个操作。

> Implement `makePlan(classification), validatePlan(plan) in main.ts` in your learner workspace. Preserve the exported names and continue using earlier stages rather than duplicating their policies.
> The scratch checkpoint is local JSON, not authenticated authorization. The optional framework stores the actual plan and binds approval to its digest and ticket ID. A digest detects mismatched context; it does not identify who approved the operation.

## Hints · 提示

先测一个合法的计划，然后一次只修改一个字段。先检查动作列表，再去统计写工具的个数。保持 query 不变，这样恢复执行（resume）的工作流就无法悄悄执行一条被改写过的请求。

> Test a valid plan, then modify one field at a time. Check the action list before counting write tools. Keep the query unchanged so a resumed workflow cannot quietly execute a rewritten request.

## Verify your work · 验证你的成果

```bash
python3 scripts/project_test.py typed-workflow-agent-with-mastra --init my-typed-workflow-agent-with-mastra
python3 scripts/project_test.py typed-workflow-agent-with-mastra --stage 2 --path my-typed-workflow-agent-with-mastra --strict
```

只需初始化一次。累积测试（cumulative tests）会导入你的工作区并保留你早先的源码。运行参考实现（reference solution）验证的是教学实现，永远不会给学习者颁发证书。可选的 SDK 检查需要项目 README 中的依赖和命令。

> Initialize once. Cumulative tests import your workspace and preserve your earlier source. A reference-solution run verifies the teaching implementation and never grants a learner certificate. Optional SDK checks require the dependencies and commands in the project README.

## Inspect the result · 检查结果

一个公开的审批端点还需要哪些额外的身份与访问控制？为什么只有计划哈希（plan hash）是不够的？

完成整个项目后，你会得到一份 scratch 版的 HTML/JSON 工作流评审，以及一次真实的 Mastra 运行：结果存入 SQLite，并附带一份与计划绑定的审批文档（plan-bound approval document）。

```bash
cd projects/typed-workflow-agent-with-mastra/solution
node --experimental-strip-types cli.ts --ticket fixtures/ticket.json --out workflow-output
```

把这个 fixture 换成来自你自己工作流的一小段输入。把预期结果和观察到的证据放在一起保存，另外再留一组单独的用例用于评估。Provider 请求测试证明的是序列化和控制流，而不是模型质量。

> What additional identity and access controls would a public approval endpoint need? Why is a plan hash alone insufficient?
> The completed project produces a scratch HTML/JSON workflow review and a real Mastra run stored in SQLite with a plan-bound approval document.
> Replace the fixture with a small input from your own workflow. Keep expected outcomes and observed evidence together, then retain a separate set of cases for evaluation. Provider request tests establish serialization and control flow; they do not establish model quality.

## Primary reference · 主要参考

[官方 API 文档](https://mastra.ai/docs/workflows/suspend-and-resume)。实现、策略选择和示例均为原创。

> [Official API documentation](https://mastra.ai/docs/workflows/suspend-and-resume). The implementation, policy choices and examples are original.
