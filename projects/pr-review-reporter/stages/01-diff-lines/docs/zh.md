# Recover new-file line numbers · 恢复新文件的行号

第 1 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在之前各阶段的契约之上。

## What changes · 变化在哪

把 hunk 头解析成旧、新两个计数器。上下文行（context）同时消耗两个计数器，删除行（deletion）只消耗旧计数器，新增行（addition）消耗新计数器并产出一个可评审的位置。拒绝被截断的 hunk 和向上穿越父目录的路径。这个解析器刻意只处理文本 unified diff；二进制 patch 和 combined merge diff 都在契约之外。用 execFileSync 和 stdin 把 Python 接入 TypeScript，绝不使用拼接出来的 shell 命令。

本阶段的边界是 `parseDiff`。保持之前各阶段的行为不变：最终评分器会对同一个工作区运行每一个阶段。

> Parse hunk headers into old and new counters. Context consumes both counters, deletions consume only the old counter, and additions consume the new counter while producing a reviewable location. Reject truncated hunks and parent-traversing paths. The parser is deliberately for text unified diffs; binary patches and combined merge diffs are outside the contract. Wire Python into TypeScript using execFileSync and stdin, never an interpolated shell command.

> The boundary for this stage is `parseDiff`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 走通一个具体案例

一个 hunk 从新行 10 开始，包含两行 context，删除三行旧行，并新增一行 eval(input)。这行新增属于新行 12：删除永远不会推进新文件计数器。

```figure
pj-pr-review-reporter-1
```

先改动实验输入，在读它的指标之前自己算出结果。figure 是从这些输入计算出来的；下面的实现测试仍然是判定完成与否的依据。

> A hunk starts at new line 10, includes two context rows, deletes three old rows and adds eval(input). The addition belongs to new line 12: deletions never advance the new-file counter.

> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的工作区 `main.ts` 里实现 `parseDiff`。先自己尝试实现契约，之后再去读参考中导出的类型。保留 starter 的公开命名，测试才能调用你的实现。核心函数返回结构化值，不要在核心函数里打印；打印最终结果由 CLI 负责。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只管返回值，把文件输入、参数解析和展示交给随附的 driver。

只要 hunk 还有剩余行，以 +++ 开头的行就仍然是新增内容，而不是新的文件名头。先解码 Git 带引号的路径，再校验目录穿越。

> Implement `parseDiff` in your workspace `main.ts`. Read the exported types in the reference only after attempting the contract. Preserve the starter's public names so tests can call your implementation. Return structured values instead of printing inside the core function; the CLI prints the final result.

> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.

> While a hunk has remaining rows, a line beginning +++ is still added content, not a new filename header. Decode Git quoted paths before validating traversal.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py pr-review-reporter --init learning-artifacts/pr-review-reporter` 初始化一次。然后累积式评分：

```bash
python3 scripts/project_test.py pr-review-reporter --stage 1 --path learning-artifacts/pr-review-reporter --strict
```

全新工作区在你实现契约之前应当失败。每个阶段都完成后，用随附的样例运行你真正的产物：

```bash
cd learning-artifacts/pr-review-reporter
node cli.ts --diff samples/change.diff --output review.json --html review.html --sarif review.sarif
```

> From the repository root, initialize once with `python3 scripts/project_test.py pr-review-reporter --init learning-artifacts/pr-review-reporter`. Then grade cumulatively:

> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

用一个包含空格的文件名，以及一行源码以 ++ 开头的新增行来测试。两者都必须精确保留原始证据，不能让解析器的状态发生混淆。

> Use a filename containing a space and an added line whose source starts with ++. Both must retain their exact evidence without confusing parser states.

## References · 参考资料

[Git diff format](https://git-scm.com/docs/diff-format)
[Python subprocess and JSON](https://docs.python.org/3/library/json.html)
