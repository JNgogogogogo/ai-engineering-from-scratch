# Resolve dependencies before execution · 在执行前解析依赖

**Stage 3 of 4 · 第 3 阶段（共 4 阶段）。** TypeScript。计划约 2 小时。

使用深度优先遍历（depth-first traversal），并分别维护 active 与 visited 两个集合。出现在 active 里说明发现了环（cycle）；出现在 visited 里则避免菱形依赖（diamond）导致的重复执行。既要对所选技能校验权限要求，也要对其每个依赖校验权限要求。先输出依赖、再输出依赖它们的消费者；遇到未知的依赖 id 要直接拒绝，而不是悄悄跳过这些工作。

> Use depth-first traversal with separate active and visited sets. Active membership catches a cycle; visited membership avoids duplicate execution through a diamond. Validate permission requirements on dependencies as well as the selected skill. Emit dependencies before their consumers and reject unknown dependency ids instead of silently skipping work.

本阶段的实现边界是 `plan`。保持此前阶段的行为不变：最终评分器（grader）会在同一个工作区上运行每一个阶段。

> The boundary for this stage is `plan`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

```figure
pj-skill-router-3
```

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [TypeScript object types](https://www.typescriptlang.org/docs/handbook/2/objects.html) 和 [Tool schema design](../../../../../phases/13-tools-and-protocols/05-tool-schema-design/docs/en.md)。先完成 [阶段 2](../../02-score/docs/en.md)。

> Before coding, review [TypeScript object types](https://www.typescriptlang.org/docs/handbook/2/objects.html) and [Tool schema design](../../../../../phases/13-tools-and-protocols/05-tool-schema-design/docs/en.md). Complete [stage 2](../../02-score/docs/en.md) first.

先选中 release-review 就必须带上 check-tests。深度优先遍历会先输出依赖、再输出所选技能，并在整张依赖图上校验权限。任何一个依赖被拒绝，整个计划都会被拦下。

> Selecting release-review first requires check-tests. A depth-first traversal emits dependencies before the selected skill and validates permissions throughout the graph. A denied dependency blocks the whole plan.

```text
release-review requires check-tests
allowed=[read]
plan=[check-tests,release-review]
```

## Build and inspect · 构建与检视

分别跟踪 active 与 visited 两个集合：active 用来发现环，visited 用来防止重复执行。不要在依赖之前先追加父节点。

> Track active and visited sets separately: active finds cycles, visited prevents repeated execution. Do not append a parent before its dependencies.

请在你的学习者工作区（learner workspace）中实现本阶段。CLI 辅助工具是预先提供的适配器，它们导入你的函数；它们不能替代参考实现。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py skill-router --stage 3 --path learning-artifacts/skill-router
```

先预测上面的中间状态，再运行本阶段。全新的存根（stub）会失败；一次通过的参考运行并不能证明你的学习者工作区已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接下来探究

如果 check-tests 偷偷要求一个网络权限，会发生什么？

> What would happen if check-tests secretly required a network permission?
