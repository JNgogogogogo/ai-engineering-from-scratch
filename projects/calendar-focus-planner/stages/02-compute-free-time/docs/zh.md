# Merge overlaps before finding gaps · 先合并重叠，再找空隙

**Type:** Build
**Language:** TypeScript
**Stage:** 2 of 4
**Time:** ~2 hours, after the linked prerequisites
**Prerequisites:** The previous stage and [development environment](../../../../../phases/00-setup-and-tooling/01-dev-environment/docs/en.md), [data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md).

## What you build · 你要构建什么

本阶段为 Calendar Focus Planner 出力：在日历里找到真正空闲的时间，放置按优先级排序的任务，并解释哪些任务放不进去。

你的公开契约是 `availableSlots(events, window, bufferMinutes=0)`。随附的 CLI 和样例文件就在你的 workspace 里；在 `main.ts` 中实现领域函数。保持它们的签名不变，别的应用才能调用同一个边界。

> This stage contributes to Calendar Focus Planner: find real free time in a calendar, place prioritized tasks, and explain which tasks do not fit.
> Your public contract is `availableSlots(events, window, bufferMinutes=0)`. The supplied CLI and sample files live in your workspace; implement the domain functions in `main.ts`. Keep their signatures so another application can call the same boundary.

## Work through the mechanism · 过一遍机制

两个重叠的会议消耗的时间并不是两者时长之和。把每个事件按所选 buffer 向外扩一圈，裁剪到工作时间窗内，按开始时间排序，再合并重叠或相邻的区间。这个并集的补集才是真正的空闲空隙。

用一个游标（cursor）从工作时间窗的起点开始。在每段忙碌区间之前，只有当该区间的开始晚于游标时才输出一段空隙。然后把游标移到忙碌结束处。最后一个事件之后，输出剩余的尾部。这个方法可解释，而且能处理嵌套会议而不重复计数。

| 输入（10 分钟 buffer） | 合并后的占用区间 |
|---|---|
| 09:20–10:25 与 09:50–11:10 | 09:20–11:10 |
| 12:50–14:40 | 12:50–14:40 |
| 工作时间窗 | 09:00–17:00 |

> Two overlapping meetings do not consume the sum of their durations. Expand each event by the chosen buffer, clip it to the work window, sort by start and merge overlapping or adjacent intervals. The complement of that union gives the actual free gaps.
> A cursor starts at the work-window beginning. Before each busy interval, emit a gap only if the interval starts after the cursor. Move the cursor to the busy end. After the final event, emit the remaining tail. This method is explainable and handles nested meetings without double counting.

## Predict before running · 运行前先预测

手工算出每一段空闲空隙。验证忙碌时长加空闲时长等于时间窗总时长。

```figure
pj-calendar-focus-planner-2
```

修改 figure 的输入并核对计算出的值。把某一个变化的结果对应到你实现中的某一行；figure 是解释性模型，不能代替真实程序。

> Calculate every free gap by hand. Verify busy duration plus free duration equals the window duration.
> Change the figure input and check the computed values. Relate one changed result to a line in your implementation; the figure is an explanatory model, not a replacement for the real program.

## Build and verify · 构建并验证

在仓库根目录初始化一次。这一步会复制公开类型、函数桩、一个真实的命令封装和原创的样例输入。全新的第一次运行应该失败，因为领域函数还没有实现。

```bash
python3 scripts/project_test.py calendar-focus-planner --init my-calendar-focus-planner
python3 scripts/project_test.py calendar-focus-planner --stage 2 --path my-calendar-focus-planner --strict
```

用标准库实现契约。先手工推演一遍示例。保持调用方的输入不被改动，对畸形数据给出可操作的错误并拒绝。测试导入的是你的 workspace，绝不是参考解答。

> From the repository root, initialize once. This copies public types, function stubs, a real command wrapper and original sample input. A fresh first-stage run should fail because the domain functions are not implemented.
> Implement the contract with the standard library. Trace the worked example by hand first. Keep caller inputs unchanged and reject malformed data with an actionable error. Tests import your workspace, never the reference solution.

## Hint ladder · 提示阶梯

1. 先裁剪到时间窗内，再丢弃窗外的区间。
2. 把每个开始时间与上一个合并后的结束时间比较。
3. 返回新对象，调用方的事件保持不变。

> 1. Clip before discarding intervals outside the window.
> 2. Compare each start with the last merged end.
> 3. Return new objects so caller events remain unchanged.

## What you should see · 你应该看到什么

在这一阶段，评分器会报告阶段 1 到 2 的真实通过测试。四个阶段全部完成后，先用随附样例运行交付的工具，再换成你自己的输入：

```bash
cd my-calendar-focus-planner
node cli.ts sample.ics tasks.json 2026-10-14 output 10
```

最终产物是一份可检查的 HTML 计划、一份机器可读的日程表，以及供手工导入的可移植 ICS 提案。打开 HTML 并检查配套的 JSON，不要只信退出码。改动一个输入，并准确解释哪个结果必须跟着变。

> At this stage the grader reports real passing tests for stages 1 through 2. After completing all four stages, run the shipped tool on the supplied sample, then substitute your own input:
> The final artifact is an inspectable HTML plan, machine-readable schedule, and portable ICS proposals for manual import. Open the HTML and inspect the companion JSON instead of trusting an exit code alone. Change one input and explain exactly which result must change.

## Extend it · 扩展练习

改变 buffer 的大小，找出一个 75 分钟的任务恰好放不进去的那个临界点。

> Vary the buffer and identify the exact point at which a 75-minute task no longer fits.

范围：解析器支持显式 UTC 事件和全天日期。重复规则（recurrence）和具名时区必须先由日历导出器展开，遇到时会被拒绝。CLI 规划的是 09:00–17:00 的 UTC 一天。它只创建本地提案，从不改动账户日历。

> Scope: The parser supports explicit UTC events and all-day dates. Recurrence and named time zones must be expanded by a calendar exporter first and are rejected when encountered. The CLI plans a 09:00–17:00 UTC day. It creates local proposals and never changes an account calendar.

主要参考：[iCalendar RFC 5545](https://www.rfc-editor.org/rfc/rfc5545)。实现与练习数据均为原创教学示例。

> Primary reference: [iCalendar RFC 5545](https://www.rfc-editor.org/rfc/rfc5545). The implementation and exercise data are original teaching examples.
