# Schedule priorities without pretending everything fits · 按优先级排程，不假装什么都放得下

**Type:** Build
**Language:** TypeScript
**Stage:** 3 of 4
**Time:** ~2 hours, after the linked prerequisites
**Prerequisites:** The previous stage and [development environment](../../../../../phases/00-setup-and-tooling/01-dev-environment/docs/en.md), [data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md).

## What you build · 你要构建什么

本阶段为 Calendar Focus Planner 出力：在日历里找到真正空闲的时间，放置按优先级排序的任务，并解释哪些任务放不进去。

你的公开契约是 `schedule(tasks, events, window, bufferMinutes=0)`。随附的 CLI 和样例文件就在你的 workspace 里；在 `main.ts` 中实现领域函数。保持它们的签名不变，别的应用才能调用同一个边界。

> This stage contributes to Calendar Focus Planner: find real free time in a calendar, place prioritized tasks, and explain which tasks do not fit.
> Your public contract is `schedule(tasks, events, window, bufferMinutes=0)`. The supplied CLI and sample files live in your workspace; implement the domain functions in `main.ts`. Keep their signatures so another application can call the same boundary.

## Work through the mechanism · 过一遍机制

按优先级从高到低给任务排序，优先级相同时用稳定的 ID 决出先后。把每个任务放进第一个足够长、放得下的空隙，然后把该空隙的起点向前推。任务保持连续；把任务拆开是另一种策略，需要一份显式契约才成立。

这个策略是一个确定性的启发式（heuristic），不是最优调度器。一个大的低优先级任务可能始终排不上，即使几个小碎片加起来等于它的时长。要用原因把这一结果报告出来，而不是凭空造出空闲时间，或者偷偷缩短任务。

| 任务 | 分钟 | 样例中的结果 |
|---|---|---|
| 课程示例 | 75 | 11:10–12:25 |
| 评审提交 | 45 | 14:40–15:25 |
| 录制走查 | 90 | 15:25–16:55 |
| 评估设计 | 120 | 没有连续空隙 |

> Sort tasks by descending priority with a stable ID tie-breaker. Place each task into the earliest gap that is long enough, then move that gap start forward. Keep tasks contiguous; splitting a task would be a different policy requiring an explicit contract.
> The policy is a deterministic heuristic, not an optimal scheduler. A large low-priority task may remain unscheduled even when several small fragments sum to its duration. Report that outcome with a reason instead of inventing free time or shortening the task.

## Predict before running · 运行前先预测

把那个 120 分钟任务的优先级提到五，预测哪些其他工作会因此排不上。

```figure
pj-calendar-focus-planner-3
```

修改 figure 的输入并核对计算出的值。把某一个变化的结果对应到你实现中的某一行；figure 是解释性模型，不能代替真实程序。

> Raise the 120-minute task to priority five and predict which other work becomes unscheduled.
> Change the figure input and check the computed values. Relate one changed result to a line in your implementation; the figure is an explanatory model, not a replacement for the real program.

## Build and verify · 构建并验证

在仓库根目录初始化一次。这一步会复制公开类型、函数桩、一个真实的命令封装和原创的样例输入。全新的第一次运行应该失败，因为领域函数还没有实现。

```bash
python3 scripts/project_test.py calendar-focus-planner --init my-calendar-focus-planner
python3 scripts/project_test.py calendar-focus-planner --stage 3 --path my-calendar-focus-planner --strict
```

用标准库实现契约。先手工推演一遍示例。保持调用方的输入不被改动，对畸形数据给出可操作的错误并拒绝。测试导入的是你的 workspace，绝不是参考解答。

> From the repository root, initialize once. This copies public types, function stubs, a real command wrapper and original sample input. A fresh first-stage run should fail because the domain functions are not implemented.
> Implement the contract with the standard library. Trace the worked example by hand first. Keep caller inputs unchanged and reject malformed data with an actionable error. Tests import your workspace, never the reference solution.

## Hint ladder · 提示阶梯

1. 排序之前先复制任务。
2. 要求一个空隙装得下完整时长。
3. 保留每一个被拒绝的任务及其原始请求时长。

> 1. Copy tasks before sorting.
> 2. Require one gap to fit the full duration.
> 3. Retain every rejected task with its original requested duration.

## What you should see · 你应该看到什么

在这一阶段，评分器会报告阶段 1 到 3 的真实通过测试。四个阶段全部完成后，先用随附样例运行交付的工具，再换成你自己的输入：

```bash
cd my-calendar-focus-planner
node cli.ts sample.ics tasks.json 2026-10-14 output 10
```

最终产物是一份可检查的 HTML 计划、一份机器可读的日程表，以及供手工导入的可移植 ICS 提案。打开 HTML 并检查配套的 JSON，不要只信退出码。改动一个输入，并准确解释哪个结果必须跟着变。

> At this stage the grader reports real passing tests for stages 1 through 3. After completing all four stages, run the shipped tool on the supplied sample, then substitute your own input:
> The final artifact is an inspectable HTML plan, machine-readable schedule, and portable ICS proposals for manual import. Open the HTML and inspect the companion JSON instead of trusting an exit code alone. Change one input and explain exactly which result must change.

## Extend it · 扩展练习

在一份原创任务集上比较「最早放入」（earliest-fit）与「最短任务优先」（shortest-task-first），并解释两者的取舍。

> Compare earliest-fit with shortest-task-first on an original task set and explain the tradeoff.

范围：解析器支持显式 UTC 事件和全天日期。重复规则（recurrence）和具名时区必须先由日历导出器展开，遇到时会被拒绝。CLI 规划的是 09:00–17:00 的 UTC 一天。它只创建本地提案，从不改动账户日历。

> Scope: The parser supports explicit UTC events and all-day dates. Recurrence and named time zones must be expanded by a calendar exporter first and are rejected when encountered. The CLI plans a 09:00–17:00 UTC day. It creates local proposals and never changes an account calendar.

主要参考：[iCalendar RFC 5545](https://www.rfc-editor.org/rfc/rfc5545)。实现与练习数据均为原创教学示例。

> Primary reference: [iCalendar RFC 5545](https://www.rfc-editor.org/rfc/rfc5545). The implementation and exercise data are original teaching examples.
