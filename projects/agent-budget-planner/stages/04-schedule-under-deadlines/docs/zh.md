# Schedule within cost and time limits · 在成本与时间限制内调度

第 4 阶段（共 4 阶段）。开始前请先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 4 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

一个有界的 agent 需要的不只是一个记钱器。在每个顺序作业之前应用截止时间（deadline）和成本上限，然后追加一个明确的 completed 或 rejected 事件。测试时使用确定性的时长，而不是真的 sleep。

这是一个针对准入决策的模拟器，与执行明确分离。JSON 轨迹让你能检查每个作业是被哪个约束拒绝的。它不是模型延迟的基准测试。

> A bounded agent needs more than a money counter. Apply a deadline and a cost limit before each sequential job, then append an explicit completed or rejected event. Test deterministic durations rather than sleeping.
> This is a simulator for admission decisions, clearly separated from execution. The JSON trace lets you inspect which constraint rejected each job. It is not a benchmark of model latency.

## Work through one concrete case · 走一遍具体案例

两个作业在 limit 100 下各预留 70。执行模式下，第一个结算 20；于是第二个放得下并结算 20。而在成本为 70 和 70 的保守回放中，只有第一个放得下。不同的轨迹遵循不同的证据。

```figure
pj-agent-budget-planner-4
```

修改实验输入，先自己算出结果再看它的指标。图形会根据这些输入计算；下方的实现测试仍然是完成与否的判定依据。

> Two jobs each reserve 70 against limit 100. In execution mode, the first settles 20; the second now fits and settles 20. In conservative replay with costs 70 and 70, only the first fits. The different traces follow different evidence.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

按照给定的契约实现 `schedule`。把每个结果写入 `events[].status`：被准入的作业为 `completed`，被拒绝的作业为 `rejected` 并附上截止时间或预算原因。执行驱动使用同一个 status 字段，并对不确定的回执追加 `needs_reconciliation`。

使用[公开 API 契约](../../../API.md)和带类型的起始签名。核心函数只返回值，把文件输入、参数解析和展示交给附带的驱动代码。

保持 schedule 是确定性的准入回放。附带的 execute_jobs 驱动会围绕一个真实回调调用你的 reserve 和 settle 函数；不要用预测时长替代回调实际经过的时钟。

> Implement `schedule` against the stated contract. Emit each outcome in `events[].status`: `completed` for an admitted job, or `rejected` with its deadline or budget reason. The execution driver uses the same status field and adds `needs_reconciliation` for uncertain receipts.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Keep schedule as a deterministic admission replay. The supplied execute_jobs driver calls your reserve and settle functions around an actual callback; do not substitute predicted duration for the callback's elapsed clock.

## Verify and inspect · 验证与检查

在仓库根目录下，先用 `python3 scripts/project_test.py agent-budget-planner --init learning-artifacts/agent-budget-planner` 初始化一次。然后按阶段累进式评分：

```bash
python3 scripts/project_test.py agent-budget-planner --stage 4 --path learning-artifacts/agent-budget-planner --strict
```

全新的工作区在你实现契约之前应当是失败的。所有阶段都完成后，用附带的样例运行你真实的 artifact：

```bash
cd learning-artifacts/agent-budget-planner
python3 cli.py samples/input.json --mode execute --output budget.json
```

> From the repository root, initialize once with `python3 scripts/project_test.py agent-budget-planner --init learning-artifacts/agent-budget-planner`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

添加一个会睡过截止时间的调用。下一次派发必须停止，但这个同步实现无法打断已经在运行的回调。

成本是由调用方提供的整数回执。单调的截止时间能拦截派发，但无法打断一个同步回调。账本是单进程、内存中的。

> Add an invocation that sleeps past the deadline. The next dispatch must stop, but this synchronous implementation cannot interrupt the already-running callback.
> Costs are caller-supplied integer receipts. A monotonic deadline gates dispatch but cannot interrupt a synchronous callback. The ledger is single-process and in-memory.

## References · 参考资料

[主要技术参考](https://docs.python.org/3/library/decimal.html)

> [Primary technical reference](https://docs.python.org/3/library/decimal.html)
