# Reserve capacity before dispatch · 派发前预留容量

第 2 阶段（共 4 阶段）。开始前请先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 2 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

只检查可用预算而不预留它，会让多个排队的请求花掉同一份容量。预留（reservation）要与已结算支出（settled spending）分开存储。一个新请求必须在两项都计入之后仍然放得下。

这个单进程状态机用来教你这个不变量（invariant）。它并不声称具备分布式并发安全性。做成服务版本时，需要在这个确切的状态转换周围加上原子事务或锁。

> Checking available budget without reserving it allows multiple queued requests to spend the same capacity. Store reservations separately from settled spending. A new request must fit after both quantities are counted.
> This single-process state machine teaches the invariant. It does not claim distributed concurrency safety. A service version needs an atomic transaction or lock around this exact transition.

## Work through one concrete case · 走一遍具体案例

初始为 limit 100、已花费 20、holds={A:30}。可用容量是 50，因此预留 B:60 会失败，且不改变 A。用已有的 id A 再次预留也会失败，即使金额只有 1。

```figure
pj-agent-budget-planner-2
```

修改实验输入，先自己算出结果再看它的指标。图形会根据这些输入计算；下方的实现测试仍然是完成与否的判定依据。

> Start at limit 100, spent 20, holds={A:30}. Available capacity is 50, so reserving B:60 fails without changing A. A second reservation using id A also fails even if its amount is 1.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

按照给定的契约实现 `reserve`。

使用[公开 API 契约](../../../API.md)和带类型的起始签名。核心函数只返回值，把文件输入、参数解析和展示交给附带的驱动代码。

只有在校验完标识与金额之后，才构建新的 holds 字典。准入和预留必须是同一个状态转换；只靠先前的 available() 检查会允许双重花费。

> Implement `reserve` against the stated contract.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Build a new holds dictionary only after validating the identity and amount. Admission and reservation must be one state transition; an earlier available() check alone permits double spending.

## Verify and inspect · 验证与检查

在仓库根目录下，先用 `python3 scripts/project_test.py agent-budget-planner --init learning-artifacts/agent-budget-planner` 初始化一次。然后按阶段累进式评分：

```bash
python3 scripts/project_test.py agent-budget-planner --stage 2 --path learning-artifacts/agent-budget-planner --strict
```

全新的工作区在你实现契约之前应当是失败的。所有阶段都完成后，用附带的样例运行你真实的 artifact：

```bash
cd learning-artifacts/agent-budget-planner
python3 cli.py samples/input.json --mode execute --output budget.json
```

> From the repository root, initialize once with `python3 scripts/project_test.py agent-budget-planner --init learning-artifacts/agent-budget-planner`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

追踪两个都观察到 50 个空闲单位的调用方。说出一个服务在 reserve 周围需要什么样的锁或数据库事务。

> Trace two callers both observing 50 free units. Name the lock or database transaction a service needs around reserve.

## References · 参考资料

[主要技术参考](https://docs.python.org/3/library/decimal.html)

> [Primary technical reference](https://docs.python.org/3/library/decimal.html)
