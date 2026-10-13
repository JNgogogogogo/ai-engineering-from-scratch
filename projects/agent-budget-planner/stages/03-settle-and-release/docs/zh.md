# Settle actual usage and release unused budget · 结算实际用量并释放未用预算

第 3 阶段（共 4 阶段）。开始前请先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 3 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

预留是一个上限，不是账单。请求结束时，移除它的占位（hold）并把实际支出加上。取消时，释放占位且支出为零。

上报的实际成本超过预留额是一起记账违规。要保留旧账本并抛出错误，让调用方去对账（reconcile），而不是悄悄产生一个负余额。

> A reservation is a ceiling, not an invoice. When a request finishes, remove its hold and add actual spending. On cancellation, release the hold with zero spending.
> A reported actual cost above the reservation is an accounting violation. Preserve the old ledger and raise an error so the caller can reconcile rather than silently producing a negative balance.

## Work through one concrete case · 走一遍具体案例

一个 70 单位的占位，收到实际的 20 单位回执后，释放 50 并把 20 计入支出。回执缺失则保留 70 单位占位；上报 71 则触发对账，而不是悄悄增加预算。

```figure
pj-agent-budget-planner-3
```

修改实验输入，先自己算出结果再看它的指标。图形会根据这些输入计算；下方的实现测试仍然是完成与否的判定依据。

> A 70-unit hold with an actual 20-unit receipt releases 50 and moves 20 into spending. A missing receipt preserves the 70-unit hold; a reported 71 triggers reconciliation instead of silently increasing the budget.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

按照给定的契约实现 `settle`。

使用[公开 API 契约](../../../API.md)和带类型的起始签名。核心函数只返回值，把文件输入、参数解析和展示交给附带的驱动代码。

保存已关闭的请求 id，这样重复的回执就无法花费两次。在异常发生后读取旧状态，并证明它没有被改变。

> Implement `settle` against the stated contract.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Store closed request ids so a duplicate receipt cannot spend twice. Read the old state after an exception and prove that it is unchanged.

## Verify and inspect · 验证与检查

在仓库根目录下，先用 `python3 scripts/project_test.py agent-budget-planner --init learning-artifacts/agent-budget-planner` 初始化一次。然后按阶段累进式评分：

```bash
python3 scripts/project_test.py agent-budget-planner --stage 3 --path learning-artifacts/agent-budget-planner --strict
```

全新的工作区在你实现契约之前应当是失败的。所有阶段都完成后，用附带的样例运行你真实的 artifact：

```bash
cd learning-artifacts/agent-budget-planner
python3 cli.py samples/input.json --mode execute --output budget.json
```

> From the repository root, initialize once with `python3 scripts/project_test.py agent-budget-planner --init learning-artifacts/agent-budget-planner`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

集成回调在完成工作之后抛出异常。请解释为什么此时释放预留会掩盖一笔未知的负债。

> The integration callback throws after doing work. Explain why releasing the reservation would hide an unknown liability.

## References · 参考资料

[主要技术参考](https://docs.python.org/3/library/decimal.html)

> [Primary technical reference](https://docs.python.org/3/library/decimal.html)
