# Estimate requests in integer microcredits · 以整数微积分单位（integer microcredits）估算请求

第 1 阶段（共 4 阶段）。开始前请先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 1 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

浮点金额会累积舍入误差。应当用一个有文档说明的单位，把费率和成本都表示成整数。一次请求估算会按各自独立的每 token 费率，对 prompt token 和一个输出上限（output ceiling）计费。

本 fixture 中的费率是任意的教学单位，不是真实供应商价格。输出上限按最坏情况成本预留，让调度器在调用模型之前就能做决策。实际用量稍后再结算（settle）。

> Floating point costs accumulate rounding errors. Represent rates and costs as integers in a documented unit. A request estimate charges prompt tokens and an output ceiling at separate per-token rates.
> Rates in this fixture are arbitrary teaching units, not provider prices. Output ceilings reserve worst-case cost so the scheduler can decide before invoking a model. Actual usage is settled later.

## Work through one concrete case · 走一遍具体案例

一个 prompt 有 120 个 token，允许 40 个输出 token。按整数费率 2 和 5 计算，它的上限是 120*2+40*5=440 单位。当 output_limit=0 时，上限仍然是 240。

```figure
pj-agent-budget-planner-1
```

修改实验输入，先自己算出结果再看它的指标。图形会根据这些输入计算；下方的实现测试仍然是完成与否的判定依据。

> A prompt has 120 tokens and allows 40 output tokens. At integer rates 2 and 5, its ceiling is 120*2+40*5=440 units. With output_limit=0 the ceiling is still 240.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

按照给定的契约实现 `estimate`。

使用[公开 API 契约](../../../API.md)和带类型的起始签名。核心函数只返回值，把文件输入、参数解析和展示交给附带的驱动代码。

在 Python 中要把布尔值和整数分开校验：True 不能变成 1 个 token。相乘之前检查每一个操作数，然后把调用者的单位与结果一并保留。

> Implement `estimate` against the stated contract.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Validate booleans separately from integers in Python: True must not become one token. Check every operand before multiplying, then retain the caller's unit beside the result.

## Verify and inspect · 验证与检查

在仓库根目录下，先用 `python3 scripts/project_test.py agent-budget-planner --init learning-artifacts/agent-budget-planner` 初始化一次。然后按阶段累进式评分：

```bash
python3 scripts/project_test.py agent-budget-planner --stage 1 --path learning-artifacts/agent-budget-planner --strict
```

全新的工作区在你实现契约之前应当是失败的。所有阶段都完成后，用附带的样例运行你真实的 artifact：

```bash
cd learning-artifacts/agent-budget-planner
python3 cli.py samples/input.json --mode execute --output budget.json
```

> From the repository root, initialize once with `python3 scripts/project_test.py agent-budget-planner --init learning-artifacts/agent-budget-planner`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

把输出上限从 40 改成 400。估算变为 2240 单位。实际输出 40 个 token 时，账单是 440，差距为 1800；实际输出为 0 个 token 时，账单是 240，达到最大差距 2000。请解释为什么「预留一个上限」与「结算一张回执」是两回事。

> Change the output ceiling from 40 to 400. The estimate becomes 2240 units. With 40 actual output tokens the invoice is 440, a gap of 1800; with zero actual output tokens the invoice is 240, the maximum gap of 2000. Explain why reserving a ceiling differs from settling a receipt.

## References · 参考资料

[主要技术参考](https://docs.python.org/3/library/decimal.html)

> [Primary technical reference](https://docs.python.org/3/library/decimal.html)
