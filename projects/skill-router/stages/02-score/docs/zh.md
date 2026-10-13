# Score words and repository paths · 给关键词与仓库路径打分

**Stage 2 of 4 · 第 2 阶段（共 4 阶段）。** TypeScript。计划约 2 小时。

每个匹配到的关键词记 2 分，每个匹配到的文件路径记 3 分，并把打分理由（score reasons）连同得分一起返回。支持单个路径段内的 `*` 与跨段的 `**`，转义正则表达式标点，并拒绝绝对路径或带父目录穿越（parent traversal）的文件路径。`**/` 匹配零个或多个完整目录：`**/*.ts` 能匹配 `main.ts`，`src/**/*.ts` 既能匹配 `src/main.ts` 也能匹配 `src/lib/main.ts`。把反斜杠规范化，并同时拒绝 Windows 盘符绝对路径与以斜杠开头的根路径。平分时先按 priority、再按 id 决出名次，保证排序可复现。

> Award two points for each matched keyword and three for each matched file path. Return score reasons alongside the score. Support star within one path segment and double-star across segments, escape regular expression punctuation, and reject absolute or parent-traversing file paths. `**/` matches zero or more complete directories: `**/*.ts` matches `main.ts`, and `src/**/*.ts` matches both `src/main.ts` and `src/lib/main.ts`. Resolve tied scores by priority and then id so ranking is reproducible.

本阶段的实现边界是 `matchPath, rank`。保持此前阶段的行为不变：最终评分器（grader）会在同一个工作区上运行每一个阶段。

> The boundary for this stage is `matchPath, rank`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

```figure
pj-skill-router-2
```

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [TypeScript object types](https://www.typescriptlang.org/docs/handbook/2/objects.html) 和 [Tool schema design](../../../../../phases/13-tools-and-protocols/05-tool-schema-design/docs/en.md)。先完成 [阶段 1](../../01-catalog/docs/en.md)。

> Before coding, review [TypeScript object types](https://www.typescriptlang.org/docs/handbook/2/objects.html) and [Tool schema design](../../../../../phases/13-tools-and-protocols/05-tool-schema-design/docs/en.md). Complete [stage 1](../../01-catalog/docs/en.md) first.

重复的证据不得抬高匹配得分。Orchard 请求把同一个变更路径重复了两遍，但它只应获得一次路径贡献分。关键词每处记 2 分，去重后的匹配路径每条记 3 分。

> Repeated evidence must not inflate a match. The Orchard request repeats the same changed path, but it should earn its path contribution only once. Keywords contribute two points and distinct matched paths contribute three.

```text
keywords release,replicas -> 4 points
files deploy/orchard.yaml repeated twice -> 3 points
score=7, not 10
```

## Build and inspect · 构建与检视

先规范化分隔符并去重，然后再打分。让理由与实际计入的证据严格对应。

> Canonicalize separators and deduplicate before scoring. Keep reasons aligned with the exact evidence counted.

请在你的学习者工作区（learner workspace）中实现本阶段。CLI 辅助工具是预先提供的适配器，它们导入你的函数；它们不能替代参考实现。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py skill-router --stage 2 --path learning-artifacts/skill-router
```

先预测上面的中间状态，再运行本阶段。全新的存根（stub）会失败；一次通过的参考运行并不能证明你的学习者工作区已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接下来探究

两条不同的路径规则匹配到同一个文件，应该算作两次独立的观察吗？

> Should two different path rules matching one file count as two independent observations?
