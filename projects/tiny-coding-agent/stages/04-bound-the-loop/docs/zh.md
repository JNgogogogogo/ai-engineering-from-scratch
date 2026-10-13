# Stop the coding loop on evidence or budget · 以证据或预算终止编码循环

**第 4 阶段（共 4 阶段）。** Python。计划耗时约 2 小时。

编码智能体（coding agent）在「动作」与「观察」之间交替。本项目中，规划器（planner）是一份显式记录下来的工具调用列表，这让整个循环是确定的、便于检查的。这些工具执行真实的文件编辑和真实的测试运行。

> A coding agent alternates actions and observations. Here the planner is an explicit recorded list of tool calls, making the loop deterministic and easy to inspect. The tools perform real file edits and real test runs.

用步数预算（step budget）给每一个动作计数。测试通过、工具调用非法或预算耗尽时，立即停止。之后可以让生产级模型提供同样类型的动作，而不必改动工具的执行方式。

> Count every action against a step budget. Stop immediately when tests pass, when a tool call is invalid, or when the budget is exhausted. A production model can later supply the same typed actions without changing tool execution.

```figure
pj-tiny-coding-agent-4
```

主要参考：[主要技术参考（Primary technical reference）](https://docs.python.org/3/library/subprocess.html)。

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html) 和 [智能体循环](../../../../../phases/14-agent-engineering/01-the-agent-loop/docs/en.md)。先完成 [阶段 3](../../03-run-real-tests/docs/en.md)。

规划器现在会接收每一次观察。它先运行测试，只有当失败标记（failure marker）出现时才选用提供的精确修复，然后再测试一次。这个透明的规则规划器并不声称能凭模型凭空发明代码。

```text
test -> AssertionError
proposal marker matches -> patch
test -> OK -> completed
```

> The planner now receives each observation. It tests first, selects a supplied exact repair only when its failure marker appears, then tests again. This transparent rule planner does not claim to invent code from a model.

## Build and inspect · 构建与检查

每次拿到工具结果之后都再次调用规划器。把请求的动作与对应的观察一起保留，并在规划器弃权（abstention）或步数耗尽时停止。

在你的学习者工作区实现本阶段。CLI 辅助脚本是预先提供的适配器（adapter），它们导入你的函数；它们不能替代参考解（reference solution）。

```bash
python3 scripts/project_test.py tiny-coding-agent --stage 4 --path learning-artifacts/tiny-coding-agent
```

先预测上面的中间状态，再运行本阶段。全新的桩代码（stub）会失败；参考解跑通并不代表你的学习者工作区已经完成。

所有累积阶段通过之后，在仓库根目录用最初的示例输入运行你的产物：

```bash
python3 learning-artifacts/tiny-coding-agent/cli.py projects/tiny-coding-agent/examples/workspace projects/tiny-coding-agent/examples/proposals.json --copy-to basket-repair --out repair-trace.json
```

CLI 会把一个可信的 Python 工作区复制到新的目的地，然后把它的测试当作本地代码运行。提供的提议规划器（proposal planner）从观察到的失败中挑选预先写好的修复；它并不发明补丁。POSIX 进程组超时能终止后代进程，但内存与输出配额需要操作系统级的运行器。

> Call the planner again after every tool result. Retain the requested action with each observation and stop on abstention or exhausted steps.
> The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> After the cumulative stages pass, run your artifact on the original sample input from the repository root:
> The CLI copies a trusted Python workspace to a new destination, then runs its tests as local code. The supplied proposal planner selects prewritten repairs from observed failures; it does not invent patches. POSIX process-group timeout stops descendants, but memory and output quotas require an OS-level runner.

## Investigate next · 下一步探究

在保持同样的补丁前置条件和完成规则的前提下，你会如何把模型接入进来？

> How would you plug in a model while keeping the same patch preconditions and completion rule?
