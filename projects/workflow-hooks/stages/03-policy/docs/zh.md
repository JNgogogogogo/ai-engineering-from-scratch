# Approve and select scoped rules · 审批并选出适配 scope 的 rule

**Stage 3 of 4.** Typescript. Plan about 2 hours.

在显式的审批转换（approval transition）之前，先要求有独立 session 的支持。已退役（retired）的 rule 不能被悄悄复活。hook 触发时，只包含匹配当前 scope 或全局 scope 的已批准 rule。把源 id 和注入的 rule 文本一起返回，让用户能追溯这些持久指引来自哪里。

本阶段的边界是 `transition, hook`。保持此前阶段行为不变：最终评分器（grader）会在同一个工作区上运行每个阶段。

> Require independent-session support before an explicit approval transition. Retired rules cannot be silently resurrected. At hook time, include only approved rules matching the current scope or global scope. Return source ids with injected rule text so the user can trace where persistent guidance came from.
> The boundary for this stage is `transition, hook`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

```figure
pj-workflow-hooks-3
```

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [TypeScript 对象类型](https://www.typescriptlang.org/docs/handbook/2/objects.html) 和 [仓库记忆与状态](../../../../../phases/14-agent-engineering/34-repo-memory-and-state/docs/en.md)。先完成 [阶段 2](../../02-consolidate/docs/en.md)。

审批针对的是精确的候选摘要（digest）。第二个来源可以改变这个摘要，并强制再次评审。退役一条 rule 会把它从发出的上下文中移除，同时保留它的证据以供检查。

```text
candidate -> inspect approval_digest
approve exact digest -> approved
emit orchard -> original rule + evidence
retire -> next emit omits rule
```

> Approval applies to an exact candidate digest. A second source can change that digest and force another review. Retiring a rule removes it from emitted context while keeping its evidence available for inspection.

## Build and inspect · 构建并检查

把状态过滤和 scope 过滤一起应用。绝不让全局的或频繁重复的候选绕过显式审批。

在你的学习工作区（learner workspace）里实现本阶段。CLI 助手是提供的适配器（adapter），它们导入你的函数；它们不能替代参考解法。

```bash
python3 scripts/project_test.py workflow-hooks --stage 3 --path learning-artifacts/workflow-hooks
```

先预测上面的中间状态，再运行本阶段。全新的桩（stub）会失败；参考解法跑通并不能证明你的学习工作区完成。

> Apply state and scope filtering together. Never let a global or frequently repeated candidate bypass explicit approval.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

当新证据已经到达、用户却提交了昨天的摘要时，CLI 应该怎么做？

> What should the CLI do when the user supplies yesterday's digest after new evidence arrived?
