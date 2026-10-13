# Stream bounded JSON events through real stdin · 经真实 stdin 流式输出有界 JSON 事件

**4 个阶段中的第 4 阶段。** Rust。预计约 2 小时。

用 BufRead 增量读取输入，并在为无界字符串分配内存之前先给每一行设上限。EOF 时处理最后一行没有换行符结尾的内容，并接受 CRLF。JSON 输出中的控制字符要转义，每个事件之后都要 flush，让父 agent 立刻看到结果。demo 会编译真实的二进制文件，并用一段确定性脚本驱动同一个循环。交互模式会读取用户终端，直到 quit、EOF 或动作预算耗尽。

> Read input incrementally with BufRead and cap each line before allocating an unbounded string. Process the last unterminated line at EOF and accept CRLF. Escape control characters in JSON output and flush after each event so a parent agent sees results immediately. The demo compiles the actual binary and feeds the same loop a deterministic script. Interactive mode reads the user terminal until quit, EOF or the action budget.

```figure
pj-rust-agent-shell-4
```

## Worked Orchard case · Orchard 实例演算

动手写代码前，先复习 [Rust 所有权与 Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html)和[数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)，并先完成[阶段 3](../../03-session/docs/en.md)。

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md). Complete [stage 3](../../03-session/docs/en.md) first.

客户端一次读取一个 JSON 事件，并与适配器添加的请求 id 匹配。每一行都 flush，UI 就不必等进程退出就能显示观察结果。

> A client reads one JSON event at a time and matches it to the request id added by the adapter. Flushing every line allows a UI to display observations without waiting for the process to exit.

```text
request evidence -> {request_id:evidence, seq:2, kind:ok}
output: 2:Restore evidence: rehearsal completed at 09:20 UTC.
```

## Build and inspect · 构建与检查

在构造命令字符串之前，用 BufRead 的分块读取来限制内存分配。对工具输出做 JSON 转义，而不是直接拼接原始文件文本。

> Use BufRead chunks to bound allocation before constructing a command string. JSON-escape tool output rather than concatenating raw file text.

在你的 learner workspace（学习者工作区）中实现该阶段。这些 CLI 辅助脚本是由项目提供的适配器，会导入你的函数；它们不能替代参考实现（reference solution）。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py rust-agent-shell --stage 4 --path learning-artifacts/rust-agent-shell
```

所有累积阶段通过后，在仓库根目录用原始示例输入运行你的产物：

> After the cumulative stages pass, run your artifact on the original sample input from the repository root:

```bash
python3 learning-artifacts/rust-agent-shell/client.py projects/rust-agent-shell/examples/workspace projects/rust-agent-shell/examples/requests.jsonl --limit 8 --out observations.jsonl
```

JSONL 请求使用调用方 id 和显式的工具参数对象。适配器把它们翻译成有界的 Rust stdin 语法。--limit 控制动作数；原生文件读取仍以 16 KiB 为上限。应用层路径检查不提供 OS 级隔离，也无法关闭对抗性的替换竞争。

> JSONL requests use caller ids and explicit tool argument objects. The adapter translates them to the bounded Rust stdin grammar. --limit controls actions; native file reads remain capped at 16 KiB. Application path checks do not provide OS isolation or close adversarial replacement races.

自带的 Python 适配器为每个输入 id 写一条回执（receipt），并保留全部原生响应。在 quit、预算耗尽或进程终止之后仍没有响应的请求，会收到带停止原因的终态 `kind: "not-executed"` 回执。进程出错或超时会保存部分回执流，并以非零码退出。对于意外终止，未获应答的请求没有任何执行证据；重试之前先查看原因。空输入不产生任何事件。

> The supplied Python adapter writes one receipt per input id, retaining all native responses. Requests without a response after quit, budget exhaustion, or process termination receive terminal `kind: "not-executed"` receipts with the stopping reason. A process error or timeout saves the partial receipt stream and exits nonzero. For unexpected termination, an unanswered request has no execution evidence; inspect the reason before retrying. Empty input produces no events.

## Investigate next · 接着探究

如果一个文件里包含引号、制表符或换行符，会发生什么？

> What happens if a file contains quotes, tabs or a newline?
