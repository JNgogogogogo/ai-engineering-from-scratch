# Export a reviewable calendar proposal · 导出可供评审的日历提案

**Type:** Build
**Language:** TypeScript
**Stage:** 4 of 4
**Time:** ~2 hours, after the linked prerequisites
**Prerequisites:** The previous stage and [development environment](../../../../../phases/00-setup-and-tooling/01-dev-environment/docs/en.md), [data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md).

## What you build · 你要构建什么

本阶段为 Calendar Focus Planner 出力：在日历里找到真正空闲的时间，放置按优先级排序的任务，并解释哪些任务放不进去。

你的公开契约是 `exportCalendar(plan, createdAt); renderPlan(plan)`。随附的 CLI 和样例文件就在你的 workspace 里；在 `main.ts` 中实现领域函数。保持它们的签名不变，别的应用才能调用同一个边界。

> This stage contributes to Calendar Focus Planner: find real free time in a calendar, place prioritized tasks, and explain which tasks do not fit.
> Your public contract is `exportCalendar(plan, createdAt); renderPlan(plan)`. The supplied CLI and sample files live in your workspace; implement the domain functions in `main.ts`. Keep their signatures so another application can call the same boundary.

## Work through the mechanism · 过一遍机制

导出的专注时间块是一个提案（proposal）。给它一个由任务身份和排定开始时间共同派生的稳定 identity，给出显式的 UTC 端点，以及由调用方提供的创建时间戳。转义文本属性，并折叠长行，且不能把一个 UTF-8 字符切成两半。

HTML 用人类视角解释同一份日程，包括没排上的工作。JSON 让另一个程序能检查这些决策。手工导入 ICS 把对日历的最终修改权留在学习者手里，也让这个项目完全不需要账户凭据。

| 输出 | 用途 |
|---|---|
| focus.ics | 可移植的提议事件 |
| plan.json | 可检查的排程结果 |
| plan.html | 人工评审与被拒绝的任务 |

> An exported focus block is a proposal. Give it a stable identity derived from task identity and scheduled start, explicit UTC endpoints, and a creation timestamp supplied by the caller. Escape text properties and fold long lines without splitting a UTF-8 character.
> The HTML explains the same schedule in human terms, including unscheduled work. The JSON lets another program inspect the decision. Manual ICS import keeps the final calendar edit under the learner's control and avoids account credentials in this project.

## Predict before running · 运行前先预测

用一个同时包含逗号和换行的任务标题。导出之后再解析一遍，验证标题和区间都原样保留。

```figure
pj-calendar-focus-planner-4
```

修改 figure 的输入并核对计算出的值。把某一个变化的结果对应到你实现中的某一行；figure 是解释性模型，不能代替真实程序。

> Use a task title containing a comma and a newline. Export, parse again, and verify the title and interval survive.
> Change the figure input and check the computed values. Relate one changed result to a line in your implementation; the figure is an explanatory model, not a replacement for the real program.

## Build and verify · 构建并验证

在仓库根目录初始化一次。这一步会复制公开类型、函数桩、一个真实的命令封装和原创的样例输入。全新的第一次运行应该失败，因为领域函数还没有实现。

```bash
python3 scripts/project_test.py calendar-focus-planner --init my-calendar-focus-planner
python3 scripts/project_test.py calendar-focus-planner --stage 4 --path my-calendar-focus-planner --strict
```

用标准库实现契约。先手工推演一遍示例。保持调用方的输入不被改动，对畸形数据给出可操作的错误并拒绝。测试导入的是你的 workspace，绝不是参考解答。

> From the repository root, initialize once. This copies public types, function stubs, a real command wrapper and original sample input. A fresh first-stage run should fail because the domain functions are not implemented.
> Implement the contract with the standard library. Trace the worked example by hand first. Keep caller inputs unchanged and reject malformed data with an actionable error. Tests import your workspace, never the reference solution.

## Hint ladder · 提示阶梯

1. 先转义值，再折叠行。
2. 折行时按 UTF-8 字节数计算，而不是 JavaScript 字符串长度。
3. 测试里使用固定的创建时间戳。

> 1. Escape values before line folding.
> 2. Count UTF-8 bytes rather than JavaScript string length for folding.
> 3. Use a fixed creation timestamp in tests.

## What you should see · 你应该看到什么

在这一阶段，评分器会报告阶段 1 到 4 的真实通过测试。四个阶段全部完成后，先用随附样例运行交付的工具，再换成你自己的输入：

```bash
cd my-calendar-focus-planner
node cli.ts sample.ics tasks.json 2026-10-14 output 10
```

最终产物是一份可检查的 HTML 计划、一份机器可读的日程表，以及供手工导入的可移植 ICS 提案。打开 HTML 并检查配套的 JSON，不要只信退出码。改动一个输入，并准确解释哪个结果必须跟着变。

> At this stage the grader reports real passing tests for stages 1 through 4. After completing all four stages, run the shipped tool on the supplied sample, then substitute your own input:
> The final artifact is an inspectable HTML plan, machine-readable schedule, and portable ICS proposals for manual import. Open the HTML and inspect the companion JSON instead of trusting an exit code alone. Change one input and explain exactly which result must change.

## Extend it · 扩展练习

另写一个独立适配器，把外部规划器的提案转换成经过校验的 Task 记录，让本调度器继续作为确定性的边界。

> Build a separate adapter that converts an external planner's proposals into validated Task records, keeping this scheduler as the deterministic boundary.

范围：解析器支持显式 UTC 事件和全天日期。重复规则（recurrence）和具名时区必须先由日历导出器展开，遇到时会被拒绝。CLI 规划的是 09:00–17:00 的 UTC 一天。它只创建本地提案，从不改动账户日历。

> Scope: The parser supports explicit UTC events and all-day dates. Recurrence and named time zones must be expanded by a calendar exporter first and are rejected when encountered. The CLI plans a 09:00–17:00 UTC day. It creates local proposals and never changes an account calendar.

主要参考：[iCalendar RFC 5545](https://www.rfc-editor.org/rfc/rfc5545)。实现与练习数据均为原创教学示例。

> Primary reference: [iCalendar RFC 5545](https://www.rfc-editor.org/rfc/rfc5545). The implementation and exercise data are original teaching examples.
