# Apply exact patches with preconditions · 带前置条件的精确补丁

**第 2 阶段（共 4 阶段）。** Python。计划耗时约 2 小时。

补丁（patch）是对当前文件内容的一条断言，而不是一条盲目覆盖文件的指令。要求旧文本恰好出现一次。如果模型猜出的是过时代码或一段有歧义的片段，就拒绝这个补丁并保留原文件。

> A patch is an assertion about the current file, not a blind instruction to overwrite it. Require the old text to appear exactly once. If the model guessed stale code or an ambiguous snippet, reject the patch and preserve the file.

把替换内容写入同一目录下的一个临时文件，保留目标的权限位（permission bits），然后原子地替换（atomically replace）目标。这样即使进程在写入中途失败，也不会留下写了一半的源文件，同时可执行脚本保持可执行。

> Write the replacement to a temporary file in the same directory, preserve the target's permission bits, then atomically replace the target. This avoids leaving a half-written source file if the process fails while writing and keeps executable scripts executable.

```figure
pj-tiny-coding-agent-2
```

主要参考：[主要技术参考（Primary technical reference）](https://docs.python.org/3/library/subprocess.html)。

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html) 和 [智能体循环](../../../../../phases/14-agent-engineering/01-the-agent-loop/docs/en.md)。先完成 [阶段 1](../../01-confine-paths/docs/en.md)。

补丁精确声明它期望替换什么。坏掉的 basket 既不乘价格也不乘数量：它返回 price + quantity。只有当这个表达式恰好出现一次时才替换它。

```text
old: price + quantity
new: price * quantity
occurrences=1 -> write; occurrences=0 or 2 -> reject
```

> A patch states exactly what it expects to replace. The broken basket multiplies neither price nor quantity: it returns price + quantity. Replace that expression only when it appears once.

## Build and inspect · 构建与检查

在打开临时输出文件之前，先统计精确匹配的次数。替换原文件时保留其文件权限。写入之前先记下临时文件的路径，并在 `finally` 块中删除它——写入、关闭或替换失败时也不例外。替换成功之前，原文件保持不变。

在你的学习者工作区实现本阶段。CLI 辅助脚本是预先提供的适配器（adapter），它们导入你的函数；它们不能替代参考解（reference solution）。

```bash
python3 scripts/project_test.py tiny-coding-agent --stage 2 --path learning-artifacts/tiny-coding-agent
```

先预测上面的中间状态，再运行本阶段。全新的桩代码（stub）会失败；参考解跑通并不代表你的学习者工作区已经完成。

> Count exact matches before opening a temporary output file. Preserve file permissions when replacing the original. Capture the temporary path before writing and remove it in a `finally` block, including when writing, closing, or replacing fails. The original stays unchanged until replacement succeeds.
> The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

## Investigate next · 下一步探究

当规划器（planner）提出补丁之后，另一个编辑器却抢先修好了文件，这时应该发生什么？

> What should happen when another editor fixes the file after the planner proposes a patch?
