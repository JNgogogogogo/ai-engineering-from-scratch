# Persist rules across sessions · 让 rule 跨 session 持久化

**Stage 4 of 4.** Typescript. Plan about 2 hours.

把带版本的 JSON 快照写入一个唯一的同级临时文件（权限仅限所有者），然后 rename 到目标位置。读者看到的要么是旧的完整文件，要么是新的完整文件。存储缺失意味着空集合，而格式错误的存储则是错误。这个快照存储支持单个写进程；跨进程合并和加锁是单独的扩展。

本阶段的边界是 `save, load`。保持此前阶段行为不变：最终评分器（grader）会在同一个工作区上运行每个阶段。

> Write a versioned JSON snapshot to a unique sibling temporary file with owner-only permissions, then rename it into place. Readers see the old or new complete file. Missing storage means an empty collection, while malformed storage is an error. This snapshot store supports one writer process; cross-process merge and locking are a separate extension.
> The boundary for this stage is `save, load`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

```figure
pj-workflow-hooks-4
```

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [TypeScript 对象类型](https://www.typescriptlang.org/docs/handbook/2/objects.html) 和 [仓库记忆与状态](../../../../../phases/14-agent-engineering/34-repo-memory-and-state/docs/en.md)。先完成 [阶段 3](../../03-policy/docs/en.md)。

CLI 捕获 JSONL 修正，保存一个带版本的存储，在另一个进程里重新加载它，并发出一个中立的 JSON hook 载荷（payload）。它保留证据，支持退役，并在重启之后精确保留 API_KEY。

```text
capture -> store.json
approve -> stored state approved
emit -> additional_context plus evidence locators
malformed store -> error, not empty success
```

> The CLI captures JSONL corrections, saves a versioned store, reloads it in another process and emits a neutral JSON hook payload. It retains evidence, supports retirement and preserves API_KEY exactly across restart.

## Build and inspect · 构建并检查

写一个唯一的同级临时文件然后 rename。这个存储是单写者（single-writer）契约；在使用并发的写者之前，先加锁。

在你的学习工作区（learner workspace）里实现本阶段。CLI 助手是提供的适配器（adapter），它们导入你的函数；它们不能替代参考解法。

```bash
python3 scripts/project_test.py workflow-hooks --stage 4 --path learning-artifacts/workflow-hooks
```

累积阶段全部通过之后，从仓库根目录用最初的示例输入运行你的产物：

```bash
node learning-artifacts/workflow-hooks/cli.ts capture orchard-rules.json projects/workflow-hooks/examples/corrections.jsonl
node learning-artifacts/workflow-hooks/cli.ts inspect orchard-rules.json
```

capture、inspect、approve、retire 和 emit 是基于文件的命令。emit 返回带 additional_context 和可解析证据的中立 JSON；agent 集成必须把这个字段映射到它自己文档化的 hook 接口。审批要求当前摘要。存储是带版本的、原子的、单写者的。

> Write a unique sibling temporary file and rename. This store has a single-writer contract; add locking before using simultaneous writers.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> After the cumulative stages pass, run your artifact on the original sample input from the repository root:
> capture, inspect, approve, retire and emit are file-based commands. emit returns neutral JSON with additional_context and resolvable evidence; an agent integration must map that field to its documented hook interface. Approval requires the current digest. Stores are versioned, atomic and single-writer.

## Investigate next · 接着探究

你的 agent 集成会怎么把 additional_context 映射进它文档化的 hook 传输格式（wire format）？

> How would your agent integration map additional_context into its documented hook wire format?
