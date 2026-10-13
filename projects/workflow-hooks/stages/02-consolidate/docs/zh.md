# Count independent sessions · 数独立 session 的个数

**Stage 2 of 4.** Typescript. Plan about 2 hours.

按 scope 和「保留大小写、空白已归一化的 rule 文本」分组。对 event id 去重，并拒绝「同一个 id 带着不同内容」的复用。统计唯一 session 数而不是事件数，这样重复的 hook 投递就无法把一条 rule 晋升（promote）。把每个源 id 都挂在候选（candidate）上，并对最终输出排序，以获得可复现的文件。

本阶段的边界是 `consolidate`。保持此前阶段行为不变：最终评分器（grader）会在同一个工作区上运行每个阶段。

> Group by scope and case-preserving, whitespace-normalized rule text. Deduplicate event ids and reject a reused id with different content. Count unique sessions rather than event count, so repeated hook delivery cannot promote a rule. Keep every source id attached to the candidate and sort the final output for reproducible files.
> The boundary for this stage is `consolidate`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

```figure
pj-workflow-hooks-2
```

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [TypeScript 对象类型](https://www.typescriptlang.org/docs/handbook/2/objects.html) 和 [仓库记忆与状态](../../../../../phases/14-agent-engineering/34-repo-memory-and-state/docs/en.md)。先完成 [阶段 1](../../01-corrections/docs/en.md)。

重复投递不是独立证据。同一个 session 里的两条不同修正，仍然只贡献一个支持 session。把摘录和定位器留在候选上，这样它的源 id 之后仍可解析。

```text
events a1,a2 from session A -> sessions=[A]
event b1 from session B -> sessions=[A,B]
rule remains candidate until approval
```

> Repeated delivery is not independent evidence. Two distinct corrections in one session still contribute one supporting session. Keep excerpts and locators with the candidate so its source ids remain resolvable later.

## Build and inspect · 构建并检查

用完整且已校验的内容对 event id 去重。id 的冲突复用必须失败，而不是悄悄替换掉来源信息（provenance）。

在你的学习工作区（learner workspace）里实现本阶段。CLI 助手是提供的适配器（adapter），它们导入你的函数；它们不能替代参考解法。

```bash
python3 scripts/project_test.py workflow-hooks --stage 2 --path learning-artifacts/workflow-hooks
```

先预测上面的中间状态，再运行本阶段。全新的桩（stub）会失败；参考解法跑通并不能证明你的学习工作区完成。

> Deduplicate event ids using their full validated content. Conflicting reuse of an id must fail rather than silently replace provenance.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

为什么 API_KEY 和 api_key 两条 rule 要保持为两个独立的候选？

> Why should API_KEY and api_key rules remain separate candidates?
