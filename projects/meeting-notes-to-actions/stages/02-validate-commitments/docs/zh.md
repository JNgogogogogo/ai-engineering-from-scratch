# Validate owners and calendar dates · 校验 owner 与日历日期

第 2 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 2 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

action 列表是运维数据。要拒绝在日历上不可能存在的日期，而不是接受一个只是长得像日期的形状。缺失 owner 或日期不是解析器崩溃，而是一个待审标记（review flag）。

未知字段使用字面量 `?` 标记。这让不确定性在结构化输出里保持可见。日期解析使用 ISO 日历日期，不为全天（all-day）承诺虚构时区。

要求 source citation 是一个非空的、由正整数组成的列表。即便 Python 把布尔值当作整数，也要拒绝 `bool`。无效或缺失的 citation 不能在发布出来的清单里冒充可信证据。

> An action list is operational data. Reject impossible calendar dates rather than accepting a shape that merely resembles a date. ... Require source citations to be a nonempty list of positive integers. Reject booleans even though Python treats them as integers. Invalid or missing citations cannot become trustworthy evidence in the published checklist.

## Work through one concrete case · 走一遍具体案例

`2026-02-30` 的数字形态完全正确，但它不是一个真实存在的日历日期。标记 `?` 表示承诺字段缺失，会生成 `needs_date` 或 `needs_owner`，而不是猜一个值。

```figure
pj-meeting-notes-to-actions-2
```

修改实验（lab）的输入，先自己算出结果，再去看它的指标。图中数字由这些输入计算而来；下面的实现测试仍然是完成与否的证据来源。

> 2026-02-30 has the right digit pattern but is not a calendar date. The marker ? means a missing commitment field and creates needs_date or needs_owner instead of guessing a value. ... Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

按照上述契约实现 `validate_action`。

使用[公开的 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示交给随附的 driver。

先强制约定好的 ISO 形态，再用 `date.fromisoformat` 解析日期。把 source line 校验为正整数，并显式拒绝 `bool`、空列表和形似 HTML 的值。

> Implement `validate_action` against the stated contract. ... Parse dates with date.fromisoformat after enforcing the intended ISO shape. Validate source lines as positive integers and explicitly reject bool, empty lists and HTML-like values.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py meeting-notes-to-actions --init learning-artifacts/meeting-notes-to-actions` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py meeting-notes-to-actions --stage 2 --path learning-artifacts/meeting-notes-to-actions --strict
```

全新的 workspace 在你实现契约之前应当判为失败。每个阶段完成后，用随附的样例运行你的真实产物：

```bash
cd learning-artifacts/meeting-notes-to-actions
python3 cli.py samples/notes.txt --today 2026-09-29 --output actions.json --html actions.html --csv approved.csv
```

> From the repository root, initialize once with `python3 scripts/project_test.py meeting-notes-to-actions --init learning-artifacts/meeting-notes-to-actions`. Then grade cumulatively ... A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample.

## Investigate the failure boundary · 探查失败边界

试着批准一个 owner 为 `?` 的 action。inbox 必须拒绝这次批准，把这份不完整的承诺留给人工审查。

> Try approving an action whose owner is?. The inbox must reject approval, leaving the incomplete commitment for review.

## References · 参考资料

[主要技术参考](https://docs.python.org/3/library/datetime.html)
