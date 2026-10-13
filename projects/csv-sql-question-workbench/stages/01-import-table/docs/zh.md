# Import a table without guessing away errors · 导入一张表，不把错误悄悄猜掉

**Type:** Build
**Language:** Python
**Stage:** 1 of 4
**Time:** ~2 小时（在学习所列前置内容之后）
**Prerequisites:** [开发环境](../../../../../phases/00-setup-and-tooling/01-dev-environment/docs/en.md)、[数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

## What you build · 你要构建什么

本阶段是 CSV Question Workbench 的一部分：向一个 CSV 提问、检查实际执行的 SQL，并保留一份可复现的只读答案回执。

> This stage contributes to CSV Question Workbench: ask a CSV a question, inspect the executed SQL, and keep a reproducible read-only answer receipt.

你的公开契约是 `load_csv(text, max_rows=10000)`。配套的 CLI 和样例文件放在你的工作区里；领域函数在 `main.py` 中实现。保持它们的签名不变，这样别的应用才能调用同一个边界。

> Your public contract is `load_csv(text, max_rows=10000)`. The supplied CLI and sample files live in your workspace; implement the domain functions in `main.py`. Keep their signatures so another application can call the same boundary.

## Work through the mechanism · 走通机制

从文件边界开始。CSV 读取器能处理引号内的逗号和换行；按逗号切分每一行的做法做不到。把原始字节的 fingerprint（指纹）与解析出的行分开保存，这样答案才能指认所提供的到底是哪个文件。

> Start with the file boundary. A CSV reader handles quoted commas and line breaks; splitting each line on commas cannot. Keep the original bytes fingerprint separate from parsed rows so the answer can identify the exact supplied file.

只有当一列的每个非空单元格都是有限十进制值、大小落在 binary64 的安全整数范围内、且不会下溢为 0 时，这一列才是 numeric。看起来像整数但带前导零的值按 TEXT 保留。超过 9007199254740991 的值同样保持 TEXT，这样不同的标识符才不会坍缩成同一个浮点数。REAL 列上的十进制运算仍然是近似的；如果要做扩展，请使用显式的精确数字 schema。空单元格稍后变成 SQL NULL。这条保守规则能把一个混杂的标识符列保留为文本。拒绝在大小写不敏感意义下重复的表头，因为 SQLite 认为这些名字等价。在创建数据库之前就拒绝参差不齐的记录。

> A column is numeric only when every nonempty cell is a finite decimal value within the safe integer magnitude of binary64, with no underflow to zero. Preserve integer-looking values with leading zeros as TEXT. Values above 9007199254740991 also stay TEXT so distinct identifiers cannot collapse into the same floating-point number. ... Reject duplicate case-insensitive headers because SQLite treats their names as equivalent. Reject ragged records before creating a database.

| 输入列 | 非空值 | 推断类型 |
|---|---|---|
| region | West, East | TEXT |
| units | 12, 7 | REAL |
| ticket | 001, 002 | TEXT |
| item_id | 9007199254740992, 9007199254740993 | TEXT |

## Predict before running · 运行前先预测

追踪一个包含逗号的带引号单元格。解释为什么改动源文件中的一个字符就会改变 fingerprint，即使下游的聚合值保持不变。

> Trace a quoted cell containing a comma. Explain why changing one source character changes the fingerprint even if a downstream aggregate stays equal.

```figure
pj-csv-sql-question-workbench-1
```

修改图中的输入并核对计算出的值。把其中一处变化对应到你实现中的某一行；这张图只是解释性模型，不能替代真实程序。

> Change the figure input and check the computed values. Relate one changed result to a line in your implementation; the figure is an explanatory model, not a replacement for the real program.

## Build and verify · 构建与验证

在仓库根目录初始化一次。这一步会复制公开类型、函数桩、一个真实的命令行包装器和原始样例输入。全新状态下第一阶段的运行应该失败，因为领域函数还没有实现。

> From the repository root, initialize once. This copies public types, function stubs, a real command wrapper and original sample input. A fresh first-stage run should fail because the domain functions are not implemented.

```bash
python3 scripts/project_test.py csv-sql-question-workbench --init my-csv-sql-question-workbench
python3 scripts/project_test.py csv-sql-question-workbench --stage 1 --path my-csv-sql-question-workbench --strict
```

用标准库实现契约。先手工推演示例。保持调用方的输入不被改动，并用可操作的错误信息拒绝畸形数据。测试导入的是你的工作区，绝不是参考答案。

> Implement the contract with the standard library. Trace the worked example by hand first. Keep caller inputs unchanged and reject malformed data with an actionable error. Tests import your workspace, never the reference solution.

## Hint ladder · 提示阶梯

1. 使用 csv.reader 进行严格解析。
2. 从全部非空值推断每一列的类型，而不是只看第一条记录。
3. 在任何变换之前先对输入文本做哈希。

> 1. Use csv.reader with strict parsing.
> 2. Infer each column from all nonempty values, not the first record.
> 3. Hash the input text before transformation.

## What you should see · 你应该看到什么

在这个阶段，评分器会报告阶段 1 到阶段 1 的真实通过测试。四个阶段全部完成后，用提供的样例运行成品工具，再换成你自己的输入：

> At this stage the grader reports real passing tests for stages 1 through 1. After completing all four stages, run the shipped tool on the supplied sample, then substitute your own input:

```bash
cd my-csv-sql-question-workbench
python3 cli.py sample.csv --question "sum units by region" --output output/report.html
```

最终工件是一个自包含的 HTML 结果表和一份 JSON 回执，其中包含确切的 SQL 和源文件指纹。要打开 HTML 并检查配套的 JSON，而不是只相信退出码。改动一个输入，并准确解释哪个结果必须随之改变。

> The final artifact is a self-contained HTML result table and JSON receipt containing the exact SQL and source fingerprint. Open the HTML and inspect the companion JSON instead of trusting an exit code alone. Change one input and explain exactly which result must change.

## Extend it · 扩展练习

增加一个数值/文本混合的列，并预测是否应该允许对它做 SUM。

> Add a mixed numeric/text column and predict whether SUM should be allowed.

Scope：离线 planner 接受一个小而明确的问题语法。可选的真实模型提出 SQL，但只会拿到 schema 和问题本身。执行仍然由 SQLite authorization 控制。源级溯源并不意味着能推断出逐结果行的谱系。

> Scope: The offline planner accepts a small explicit question grammar. The optional real model proposes SQL but receives only schema and question. SQLite authorization still controls execution. Source-level provenance does not imply inferred per-result-row lineage.

主要参考：[SQLite authorization callbacks](https://www.sqlite.org/c3ref/set_authorizer.html)。实现与练习数据均为原创教学示例。

> Primary reference: [SQLite authorization callbacks](https://www.sqlite.org/c3ref/set_authorizer.html). The implementation and exercise data are original teaching examples.
