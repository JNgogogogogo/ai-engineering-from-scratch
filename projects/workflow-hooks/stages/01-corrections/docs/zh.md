# Capture corrections with provenance · 带来源地捕获修正

**Stage 1 of 4.** Typescript. Plan about 2 hours.

要求一条修正（correction）必须带修正 id、session id、scope、rule 和源摘录（source excerpt）。归一化 scope，同时保留 rule 的大小写和源证据。拒绝过大的值和明显是凭据形状的内容。这个启发式不是完整的秘密扫描器：调用方必须在摄取（ingestion）之前先脱敏源数据。

本阶段的边界是 `normalize, ingest`。保持此前阶段行为不变：最终评分器（grader）会在同一个工作区上运行每个阶段。

> Require a correction id, session id, scope, rule and source excerpt. Normalize scope while preserving rule case and source evidence. Reject oversized values and obvious credential-shaped content. This heuristic is not a complete secret scanner: callers must redact source data before ingestion.
> The boundary for this stage is `normalize, ingest`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

```figure
pj-workflow-hooks-1
```

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [TypeScript 对象类型](https://www.typescriptlang.org/docs/handbook/2/objects.html) 和 [仓库记忆与状态](../../../../../phases/14-agent-engineering/34-repo-memory-and-state/docs/en.md)。

一条修正是来自特定 session 和源定位器（source locator）的证据。保留 rule 里 API_KEY 的精确大小写；大小写折叠会把一条有用的指令变成一条自相矛盾的指令。

```text
rule: Read API_KEY; never rename it to api_key.
scope: Orchard -> orchard
source locator: local:orchard/config.py:12
```

> A correction is evidence from a specific session and source locator. Preserve the exact case of API_KEY in the rule; case folding would turn a useful instruction into a contradictory one.

## Build and inspect · 构建并检查

为匹配而归一化 scope，但对 rule 只折叠空白。在明显是凭据形状的数据进入持久存储（durable store）之前就拒绝它。

在你的学习工作区（learner workspace）里实现本阶段。CLI 助手是提供的适配器（adapter），它们导入你的函数；它们不能替代参考解法。

```bash
python3 scripts/project_test.py workflow-hooks --init learning-artifacts/workflow-hooks
python3 scripts/project_test.py workflow-hooks --stage 1 --path learning-artifacts/workflow-hooks
```

先预测上面的中间状态，再运行本阶段。全新的桩（stub）会失败；参考解法跑通并不能证明你的学习工作区完成。

> Normalize scope for matching, but only collapse rule whitespace. Reject obvious credential-shaped data before it enters the durable store.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

在摄取之前，源摘录的哪些部分必须由调用方先行脱敏？

> Which parts of a source excerpt must the caller sanitize before ingestion?
