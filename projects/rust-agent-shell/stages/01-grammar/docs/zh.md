# Parse a deliberately small action language · 解析一门刻意精简的动作语言

**4 个阶段中的第 1 阶段。** Rust。预计约 2 小时。

定义一个动作 enum，覆盖 help、pwd、list、read、字面量 search 和 quit。未知命令一律拒绝，类 shell 的指令也不例外。search 用制表符分隔 pattern 和 path，因此两个参数内部都可以包含空格。解析从不调用子进程，输入上限为 4096 字节。这是一个模型无关（model-agnostic）的工具循环，不是自然语言模型，也不是操作系统 shell。

> Define an action enum for help, pwd, list, read, literal search and quit. Unknown commands are rejected, including shell-like instructions. Search separates its pattern and path with a tab so spaces remain valid inside either argument. Parsing never invokes a subprocess and has a 4096-byte input limit. This is a model-agnostic tool loop, not a natural-language model or an operating-system shell.

```figure
pj-rust-agent-shell-1
```

## Worked Orchard case · Orchard 实例演算

动手写代码前，先复习 [Rust 所有权与 Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html)和[数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md).

这个 Rust 进程只接受一门刻意精简的工具语言。它的 Python 适配器接受带调用方 id 和工具参数的 JSONL，然后只翻译已知命令。任何参数都不会变成操作系统 shell 命令。

> The Rust process accepts a deliberately small tool language. Its Python adapter accepts JSONL with caller ids and tool arguments, then translates only known commands. No argument becomes an operating-system shell command.

```text
{"id":"evidence","tool":"search","arguments":{"pattern":"Restore","path":"release.md"}}
wire: search Restore<TAB>release.md
```

## Build and inspect · 构建与检查

拒绝适配器参数中的控制字符，让路径无法注入第二条命令。把「解析被拒」（parse rejection）和「执行失败」（execution failure）区分开。

> Reject control characters in adapter arguments so a path cannot inject a second command. Distinguish parse rejection from execution failure.

在你的 learner workspace（学习者工作区）中实现该阶段。这些 CLI 辅助脚本是由项目提供的适配器，会导入你的函数；它们不能替代参考实现（reference solution）。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py rust-agent-shell --init learning-artifacts/rust-agent-shell
python3 scripts/project_test.py rust-agent-shell --stage 1 --path learning-artifacts/rust-agent-shell
```

先预测上面的中间状态，再运行该阶段。全新的 stub 必然失败；参考实现跑通并不代表你的 learner workspace 已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

为什么调用方路径中的字面换行符必须在 stdin 序列化之前就被拒绝？

> Why must a literal newline in a caller path be rejected before stdin serialization?
