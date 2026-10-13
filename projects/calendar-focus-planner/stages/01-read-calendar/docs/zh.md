# Read explicit calendar intervals · 读取显式的日历区间

**Type:** Build
**Language:** TypeScript
**Stage:** 1 of 4
**Time:** ~2 hours, after the linked prerequisites
**Prerequisites:** [development environment](../../../../../phases/00-setup-and-tooling/01-dev-environment/docs/en.md), [data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md).

## What you build · 你要构建什么

本阶段为 Calendar Focus Planner 出力：在日历里找到真正空闲的时间，放置按优先级排序的任务，并解释哪些任务放不进去。

你的公开契约是 `parseCalendar(text)`。随附的 CLI 和样例文件就在你的 workspace 里；在 `main.ts` 中实现领域函数。保持它们的签名不变，别的应用才能调用同一个边界。

> This stage contributes to Calendar Focus Planner: find real free time in a calendar, place prioritized tasks, and explain which tasks do not fit.
> Your public contract is `parseCalendar(text)`. The supplied CLI and sample files live in your workspace; implement the domain functions in `main.ts`. Keep their signatures so another application can call the same boundary.

## Work through the mechanism · 过一遍机制

日历文本是一个协议，不是散乱的日期列表。读取属性之前先展开折行（continuation line）。把每个事件的 identity、summary、开始和结束保持在一起。拒绝缺失或先后颠倒的端点，拒绝重复的 identity。已取消（cancelled）或透明（transparent）的事件不应占用专注时间。

这个有界解析器接受带显式 `DTSTART` 和 `DTEND` 的 UTC 时间戳和纯日期事件。全天事件 `20261014` 需要排他的 `DTEND;VALUE=DATE:20261015`；不要推断被省略的结束时间，也不要用 `DURATION` 代替。它拒绝重复规则（recurrence）和时区规则，因为把它们悄悄当成单个 UTC 事件会制造出虚假的空闲时间。事件使用半开区间（half-open interval）：它的结束时刻是第一个不再被占用的时间点。

| 事件 | 开始 | 结束 |
|---|---|---|
| 团队例会 | 09:30 | 10:15 |
| 办公时间 | 10:00 | 11:00 |
| 工作坊 | 13:00 | 14:30 |

> Calendar text is a protocol, not a loose list of dates. Unfold continuation lines before reading properties. Keep each event identity, summary, start and end together. Reject missing or reversed endpoints and duplicate identities. Cancelled or transparent events should not occupy focus time.
> This bounded parser accepts UTC timestamps and date-only events with explicit `DTSTART` and `DTEND`. An all-day `20261014` event needs exclusive `DTEND;VALUE=DATE:20261015`; do not infer an omitted end or substitute `DURATION`. It refuses recurrence and timezone rules because silently treating them as one UTC event would create false free time. An event uses a half-open interval: its end is the first instant no longer occupied.

## Predict before running · 运行前先预测

在不要求 buffer 的情况下，预测一个恰好在 11:00 开始的任务，是否与一个 11:00 结束的事件冲突。

```figure
pj-calendar-focus-planner-1
```

修改 figure 的输入并核对计算出的值。把某一个变化的结果对应到你实现中的某一行；figure 是解释性模型，不能代替真实程序。

> Predict whether a task beginning exactly at 11:00 conflicts with an event ending at 11:00 when no buffer is requested.
> Change the figure input and check the computed values. Relate one changed result to a line in your implementation; the figure is an explanatory model, not a replacement for the real program.

## Build and verify · 构建并验证

在仓库根目录初始化一次。这一步会复制公开类型、函数桩、一个真实的命令封装和原创的样例输入。全新的第一次运行应该失败，因为领域函数还没有实现。

```bash
python3 scripts/project_test.py calendar-focus-planner --init my-calendar-focus-planner
python3 scripts/project_test.py calendar-focus-planner --stage 1 --path my-calendar-focus-planner --strict
```

用标准库实现契约。先手工推演一遍示例。保持调用方的输入不被改动，对畸形数据给出可操作的错误并拒绝。测试导入的是你的 workspace，绝不是参考解答。

> From the repository root, initialize once. This copies public types, function stubs, a real command wrapper and original sample input. A fresh first-stage run should fail because the domain functions are not implemented.
> Implement the contract with the standard library. Trace the worked example by hand first. Keep caller inputs unchanged and reject malformed data with an actionable error. Tests import your workspace, never the reference solution.

## Hint ladder · 提示阶梯

1. 先展开折行，再切分属性。
2. 通过转换再回验（round trip）来校验时间戳。
3. 拒绝不支持的时间语义，而不是靠猜。

> 1. Unfold before splitting properties.
> 2. Validate timestamps by converting and checking the round trip.
> 3. Reject unsupported timing semantics rather than guessing.

## What you should see · 你应该看到什么

在这一阶段，评分器会报告阶段 1 到 1 的真实通过测试。四个阶段全部完成后，先用随附样例运行交付的工具，再换成你自己的输入：

```bash
cd my-calendar-focus-planner
node cli.ts sample.ics tasks.json 2026-10-14 output 10
```

最终产物是一份可检查的 HTML 计划、一份机器可读的日程表，以及供手工导入的可移植 ICS 提案。打开 HTML 并检查配套的 JSON，不要只信退出码。改动一个输入，并准确解释哪个结果必须跟着变。

> At this stage the grader reports real passing tests for stages 1 through 1. After completing all four stages, run the shipped tool on the supplied sample, then substitute your own input:
> The final artifact is an inspectable HTML plan, machine-readable schedule, and portable ICS proposals for manual import. Open the HTML and inspect the companion JSON instead of trusting an exit code alone. Change one input and explain exactly which result must change.

## Extend it · 扩展练习

导入一个全天事件，并解释为什么白天不再剩下任何空隙。

> Import an all-day event and explain why no daytime gap remains.

范围：解析器支持显式 UTC 事件和全天日期。重复规则（recurrence）和具名时区必须先由日历导出器展开，遇到时会被拒绝。CLI 规划的是 09:00–17:00 的 UTC 一天。它只创建本地提案，从不改动账户日历。

> Scope: The parser supports explicit UTC events and all-day dates. Recurrence and named time zones must be expanded by a calendar exporter first and are rejected when encountered. The CLI plans a 09:00–17:00 UTC day. It creates local proposals and never changes an account calendar.

主要参考：[iCalendar RFC 5545](https://www.rfc-editor.org/rfc/rfc5545)。实现与练习数据均为原创教学示例。

> Primary reference: [iCalendar RFC 5545](https://www.rfc-editor.org/rfc/rfc5545). The implementation and exercise data are original teaching examples.
