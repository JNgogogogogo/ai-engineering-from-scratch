# Translate a small question into an inspectable plan · 把一个小问题翻译成可检查的计划

**Type:** Build
**Language:** Python
**Stage:** 2 of 4
**Time:** ~2 小时（在学习所列前置内容之后）
**Prerequisites:** 上一阶段，以及[开发环境](../../../../../phases/00-setup-and-tooling/01-dev-environment/docs/en.md)、[数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

## What you build · 你要构建什么

本阶段是 CSV Question Workbench 的一部分：向一个 CSV 提问、检查实际执行的 SQL，并保留一份可复现的只读答案回执。

> This stage contributes to CSV Question Workbench: ask a CSV a question, inspect the executed SQL, and keep a reproducible read-only answer receipt.

你的公开契约是 `plan_question(question, data)`。配套的 CLI 和样例文件放在你的工作区里；领域函数在 `main.py` 中实现。保持它们的签名不变，这样别的应用才能调用同一个边界。

> Your public contract is `plan_question(question, data)`. The supplied CLI and sample files live in your workspace; implement the domain functions in `main.py`. Keep their signatures so another application can call the same boundary.

## Work through the mechanism · 走通机制

问题规划器（planner）提出一个查询，但不执行它。这个基线刻意只理解 count rows、show rows 以及 sum units by region 这类分组聚合。不支持的问题会带着示例失败，而不是产出一个看似合理的编造答案。

> A question planner proposes a query. It does not execute one. The baseline intentionally understands count rows, show rows, and grouped aggregates such as sum units by region. An unsupported question fails with examples rather than producing a plausible invented answer.

用导入的 schema 解析字段名，并给解析出的标识符加引号。不要把任意用户子串直接插进 SQL。对于可选的真实模型，保持同样的提案/执行分离：在下一阶段授权之前，模型响应只是不可信文本。

> Resolve field names against the imported schema and quote the resolved identifiers. Do not insert an arbitrary user substring into SQL. For an optional model, make the same proposal/execution separation: a model response is untrusted text until the next stage authorizes it.

| 问题片段 | 解析出的含义 |
|---|---|
| sum | SQL 聚合 SUM |
| units | 已存在的数值列 |
| by region | 对已有的 region 列做 GROUP BY |

## Predict before running · 运行前先预测

预测 count by product 会生成什么 SQL。然后试一下 sum region by product，并在执行之前解释这个类型拒绝。

> Predict the SQL for count by product. Then try sum region by product and explain the type rejection before execution.

```figure
pj-csv-sql-question-workbench-2
```

修改图中的输入并核对计算出的值。把其中一处变化对应到你实现中的某一行；这张图只是解释性模型，不能替代真实程序。

> Change the figure input and check the computed values. Relate one changed result to a line in your implementation; the figure is an explanatory model, not a replacement for the real program.

## Build and verify · 构建与验证

在仓库根目录初始化一次。这一步会复制公开类型、函数桩、一个真实的命令行包装器和原始样例输入。全新状态下第一阶段的运行应该失败，因为领域函数还没有实现。

> From the repository root, initialize once. This copies public types, function stubs, a real command wrapper and original sample input. A fresh first-stage run should fail because the domain functions are not implemented.

```bash
python3 scripts/project_test.py csv-sql-question-workbench --init my-csv-sql-question-workbench
python3 scripts/project_test.py csv-sql-question-workbench --stage 2 --path my-csv-sql-question-workbench --strict
```

用标准库实现契约。先手工推演示例。保持调用方的输入不被改动，并用可操作的错误信息拒绝畸形数据。测试导入的是你的工作区，绝不是参考答案。

> Implement the contract with the standard library. Trace the worked example by hand first. Keep caller inputs unchanged and reject malformed data with an actionable error. Tests import your workspace, never the reference solution.

## Hint ladder · 提示阶梯

1. 只对问题语法做规范化。
2. 把被接受的字段词元映射回真实的列名。
3. 保持查询生成为纯函数，这样测试不需要数据库。

> 1. Normalize only the question grammar.
> 2. Map accepted field tokens back to actual column names.
> 3. Keep query generation pure so tests require no database.

## What you should see · 你应该看到什么

在这个阶段，评分器会报告阶段 1 到阶段 2 的真实通过测试。四个阶段全部完成后，用提供的样例运行成品工具，再换成你自己的输入：

> At this stage the grader reports real passing tests for stages 1 through 2. After completing all four stages, run the shipped tool on the supplied sample, then substitute your own input:

```bash
cd my-csv-sql-question-workbench
python3 cli.py sample.csv --question "sum units by region" --output output/report.html
```

最终工件是一个自包含的 HTML 结果表和一份 JSON 回执，其中包含确切的 SQL 和源文件指纹。要打开 HTML 并检查配套的 JSON，而不是只相信退出码。改动一个输入，并准确解释哪个结果必须随之改变。

> The final artifact is a self-contained HTML result table and JSON receipt containing the exact SQL and source fingerprint. Open the HTML and inspect the companion JSON instead of trusting an exit code alone. Change one input and explain exactly which result must change.

## Extend it · 扩展练习

新增一种问题形式，并配上一条显式的歧义规则和测试。

> Add one new question form with an explicit ambiguity rule and tests.

Scope：离线 planner 接受一个小而明确的问题语法。可选的真实模型提出 SQL，但只会拿到 schema 和问题本身。执行仍然由 SQLite authorization 控制。源级溯源并不意味着能推断出逐结果行的谱系。

> Scope: The offline planner accepts a small explicit question grammar. The optional real model proposes SQL but receives only schema and question. SQLite authorization still controls execution. Source-level provenance does not imply inferred per-result-row lineage.

主要参考：[SQLite authorization callbacks](https://www.sqlite.org/c3ref/set_authorizer.html)。实现与练习数据均为原创教学示例。

> Primary reference: [SQLite authorization callbacks](https://www.sqlite.org/c3ref/set_authorizer.html). The implementation and exercise data are original teaching examples.
