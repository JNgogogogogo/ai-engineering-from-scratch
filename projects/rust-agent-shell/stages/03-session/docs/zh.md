# Track budgets and terminal state · 跟踪预算与终态

**4 个阶段中的第 3 阶段。** Rust。预计约 2 小时。

把各个工具包进一个 session，由它持有根目录、请求计数和关闭状态。每个被解析的请求都要消耗一个动作槽位，被拒绝的命令也不例外。quit 是终态。超出预算的请求会产生一个终态错误。把「解析被拒」和「执行错误」区分开，调用方才能去修复命令本身，而不是把它误当成文件缺失。

> Wrap the tools in a session that owns its root, request count and closed state. Every parsed request, including rejected commands, consumes one action slot. Quit is terminal. A request beyond the budget emits a terminal error. Distinguish parsing rejection from an execution error so callers can repair a command without confusing it with a missing file.

```figure
pj-rust-agent-shell-3
```

## Worked Orchard case · Orchard 实例演算

动手写代码前，先复习 [Rust 所有权与 Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html)和[数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)，并先完成[阶段 2](../../02-filesystem/docs/en.md)。

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md). Complete [stage 2](../../02-filesystem/docs/en.md) first.

session 持有请求预算和终态。无效请求同样消耗一次尝试。通过可执行文件的参数和适配器的 --limit 暴露预算，让调用方能对「有界的工作量」进行推理。

> The session owns a request budget and terminal state. Invalid requests consume an attempt too. Expose the budget through the executable argument and adapter --limit so callers can reason about bounded work.

```text
limit=2
request 1: list -> step 1
request 2: rejected grammar -> step 2
request 3 -> terminal budget_exhausted
```

## Build and inspect · 构建与检查

在分发（dispatch）之前，每收到一个请求就把计数加一。一旦关闭，session 不得再读取任何文件。

> Increment once per received request, before dispatch. Once closed, the session must not read more files.

在你的 learner workspace（学习者工作区）中实现该阶段。这些 CLI 辅助脚本是由项目提供的适配器，会导入你的函数；它们不能替代参考实现（reference solution）。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py rust-agent-shell --stage 3 --path learning-artifacts/rust-agent-shell
```

先预测上面的中间状态，再运行该阶段。全新的 stub 必然失败；参考实现跑通并不代表你的 learner workspace 已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

如果输出在某个请求 id 收到事件之前就结束了，客户端应该如何处理？

> How should a client handle output ending before its request id receives an event?
