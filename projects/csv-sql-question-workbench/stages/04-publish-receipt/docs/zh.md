# Publish an answer another developer can reproduce · 发布一个别的开发者能复现的答案

**Type:** Build
**Language:** Python
**Stage:** 4 of 4
**Time:** ~2 小时（在学习所列前置内容之后）
**Prerequisites:** 上一阶段，以及[开发环境](../../../../../phases/00-setup-and-tooling/01-dev-environment/docs/en.md)、[数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

## What you build · 你要构建什么

本阶段是 CSV Question Workbench 的一部分：向一个 CSV 提问、检查实际执行的 SQL，并保留一份可复现的只读答案回执。

> This stage contributes to CSV Question Workbench: ask a CSV a question, inspect the executed SQL, and keep a reproducible read-only answer receipt.

你的公开契约是 `render_report(report)`。配套的 CLI 和样例文件放在你的工作区里；领域函数在 `main.py` 中实现。保持它们的签名不变，这样别的应用才能调用同一个边界。

> Your public contract is `render_report(report)`. The supplied CLI and sample files live in your workspace; implement the domain functions in `main.py`. Keep their signatures so another application can call the same boundary.

## Work through the mechanism · 走通机制

一个有用的数据答案要带上它的查询和输入身份。把实际执行的 SQL 渲染在表格上方，并把机器可读的回执保留在 HTML 旁边。报告必须披露截断情况和溯源的适用范围。一个数据库结果是「这条查询之下、这个文件」的证据，而不是「这个文件是准确的」的证据。

> A useful data answer carries its query and input identity. Render the executed SQL above the table and preserve the machine-readable receipt beside the HTML. The report must disclose truncation and the scope of provenance. A database result is evidence about this file under this query, not evidence that the file is accurate.

生成 HTML 时，把每个单元格和列标题都当作不可信文本来对待。浏览器应当显示一个包含 script 标签的单元格，而不是执行它。同一份 JSON 回执让 notebook、CI 检查或另一个 agent 可以直接消费答案，而不必去刮取可视化报告。

> Treat every cell and column heading as untrusted text when producing HTML. The browser should display a cell containing a script tag, never execute it. The same JSON receipt lets a notebook, CI check or another agent consume the answer without scraping the visual report.

| Region | SUM(units) |
|---|---|
| East | 10 |
| South | 9 |
| West | 21 |

## Predict before running · 运行前先预测

把 West 的一个输入从 4 改成 6。预测会变化的聚合值和指纹，然后对比两份回执。

> Change one West input from 4 to 6. Predict the changed aggregate and fingerprint, then compare both receipts.

```figure
pj-csv-sql-question-workbench-4
```

修改图中的输入并核对计算出的值。把其中一处变化对应到你实现中的某一行；这张图只是解释性模型，不能替代真实程序。

> Change the figure input and check the computed values. Relate one changed result to a line in your implementation; the figure is an explanatory model, not a replacement for the real program.

## Build and verify · 构建与验证

在仓库根目录初始化一次。这一步会复制公开类型、函数桩、一个真实的命令行包装器和原始样例输入。全新状态下第一阶段的运行应该失败，因为领域函数还没有实现。

> From the repository root, initialize once. This copies public types, function stubs, a real command wrapper and original sample input. A fresh first-stage run should fail because the domain functions are not implemented.

```bash
python3 scripts/project_test.py csv-sql-question-workbench --init my-csv-sql-question-workbench
python3 scripts/project_test.py csv-sql-question-workbench --stage 4 --path my-csv-sql-question-workbench --strict
```

用标准库实现契约。先手工推演示例。保持调用方的输入不被改动，并用可操作的错误信息拒绝畸形数据。测试导入的是你的工作区，绝不是参考答案。

> Implement the contract with the standard library. Trace the worked example by hand first. Keep caller inputs unchanged and reject malformed data with an actionable error. Tests import your workspace, never the reference solution.

## Hint ladder · 提示阶梯

1. 对插入标记的数据使用 html.escape。
2. 展示真正执行过的 SQL，而不只是原始问题。
3. 让 JSON 和 HTML 派生自同一个 report 对象。

> 1. Use html.escape for data inserted into markup.
> 2. Show the SQL that actually ran, not the original question alone.
> 3. Keep JSON and HTML derived from the same report object.

## What you should see · 你应该看到什么

在这个阶段，评分器会报告阶段 1 到阶段 4 的真实通过测试。四个阶段全部完成后，用提供的样例运行成品工具，再换成你自己的输入：

> At this stage the grader reports real passing tests for stages 1 through 4. After completing all four stages, run the shipped tool on the supplied sample, then substitute your own input:

```bash
cd my-csv-sql-question-workbench
python3 cli.py sample.csv --question "sum units by region" --output output/report.html
```

最终工件是一个自包含的 HTML 结果表和一份 JSON 回执，其中包含确切的 SQL 和源文件指纹。要打开 HTML 并检查配套的 JSON，而不是只相信退出码。改动一个输入，并准确解释哪个结果必须随之改变。

> The final artifact is a self-contained HTML result table and JSON receipt containing the exact SQL and source fingerprint. Open the HTML and inspect the companion JSON instead of trusting an exit code alone. Change one input and explain exactly which result must change.

## Extend it · 扩展练习

把 JSON 回接进一个简单的回归检查，与一个已知聚合值做比较。

> Integrate the JSON receipt into a simple regression check comparing a known aggregate.

Scope：离线 planner 接受一个小而明确的问题语法。可选的真实模型提出 SQL，但只会拿到 schema 和问题本身。执行仍然由 SQLite authorization 控制。源级溯源并不意味着能推断出逐结果行的谱系。

> Scope: The offline planner accepts a small explicit question grammar. The optional real model proposes SQL but receives only schema and question. SQLite authorization still controls execution. Source-level provenance does not imply inferred per-result-row lineage.

主要参考：[SQLite authorization callbacks](https://www.sqlite.org/c3ref/set_authorizer.html)。实现与练习数据均为原创教学示例。

> Primary reference: [SQLite authorization callbacks](https://www.sqlite.org/c3ref/set_authorizer.html). The implementation and exercise data are original teaching examples.
