# Deduplicate exact commitments without losing citations · 去重完全相同的承诺，且不丢失 citation

第 3 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 3 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

重复的笔记可能把同一个任务复制出多份。按归一化后的 owner、due date 和归一化后的任务文本分组，然后合并所有 source 行号。同一条任务指派给两个人，仍然是两条承诺。

这是精确归一化（exact normalization），不是语义去重。不要自动合并改写（paraphrase），因为它们的期限或范围可能不同。由人来审查，比悄悄删掉一条真实存在的义务更安全。

> Repeated notes can duplicate a task. Group by normalized owner, due date, and normalized task text, then merge all source line numbers. Two people assigned the same task are still two commitments. ... This is exact normalization, not semantic deduplication. Human review is safer than quietly deleting a distinct obligation.

## Work through one concrete case · 走一遍具体案例

第 2 行和第 8 行上两条完全相同的承诺折叠成一行，citation 为 `citations[2,8]`。哪怕任务文本保持不变，只要改动 owner 或 due date 中的任何一个，就会产生第二条承诺。

```figure
pj-meeting-notes-to-actions-3
```

修改实验（lab）的输入，先自己算出结果，再去看它的指标。图中数字由这些输入计算而来；下面的实现测试仍然是完成与否的证据来源。

> Two identical commitments on lines 2 and 8 collapse to one row with citations[2,8]. Changing either the owner or the due date creates a second commitment even if the task text remains identical. ... Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

按照上述契约实现 `deduplicate`。

使用[公开的 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示交给随附的 driver。

用归一化后的 owner、due 和 task 构建键，同时保留用于展示的原文。citation 集合按排序后的顺序合并，让重复导入产生确定性的输出。

> Implement `deduplicate` against the stated contract. ... Build the key from normalized owner, due and task, while preserving the displayed text. Merge citation sets in sorted order so repeated imports produce deterministic output.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py meeting-notes-to-actions --init learning-artifacts/meeting-notes-to-actions` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py meeting-notes-to-actions --stage 3 --path learning-artifacts/meeting-notes-to-actions --strict
```

全新的 workspace 在你实现契约之前应当判为失败。每个阶段完成后，用随附的样例运行你的真实产物：

```bash
cd learning-artifacts/meeting-notes-to-actions
python3 cli.py samples/notes.txt --today 2026-09-29 --output actions.json --html actions.html --csv approved.csv
```

> From the repository root, initialize once with `python3 scripts/project_test.py meeting-notes-to-actions --init learning-artifacts/meeting-notes-to-actions`. Then grade cumulatively ... A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample.

## Investigate the failure boundary · 探查失败边界

写一条期限更晚的改写版本。解释为什么自动语义合并可能删掉一条真实存在的义务。

> Write a paraphrase with a later deadline. Explain why an automatic semantic merge could delete an actual obligation.

## References · 参考资料

[主要技术参考](https://docs.python.org/3/library/datetime.html)
