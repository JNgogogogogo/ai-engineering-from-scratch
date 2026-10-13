# Run real tests through one allowed command · 只经由一条放行的命令运行真实测试

**第 3 阶段（共 4 阶段）。** Python。计划耗时约 2 小时。

测试工具完全拥有自己的 argv。模型文本永远不会变成 shell 命令。用当前 Python 解释器运行 unittest 测试发现（discovery），禁用交互式 stdin，捕获输出，并强制超时。

> The test tool owns its argv. Model text never becomes a shell command. Run the current Python interpreter with unittest discovery, disable interactive stdin, capture output, and enforce a timeout.

一次零测试的运行或包含被跳过（skipped）测试的套件就是失败，哪怕 unittest 以零退出。要从 stderr 读取最终的 unittest 摘要；fixture 打印到 stdout 的文本不是运行器的证据。这个工具执行的是可信 Python，所以仅有路径限制并不构成操作系统级的安全边界。

> A zero-test run or a suite with skipped tests is a failure even when unittest exits zero. Read the final unittest summary from stderr; text printed by a fixture to stdout is not runner evidence. The tool executes trusted Python, so path confinement alone is not an OS security boundary.

```figure
pj-tiny-coding-agent-3
```

主要参考：[主要技术参考（Primary technical reference）](https://docs.python.org/3/library/subprocess.html)。

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html) 和 [智能体循环](../../../../../phases/14-agent-engineering/01-the-agent-loop/docs/en.md)。先完成 [阶段 2](../../02-apply-exact-patches/docs/en.md)。

在宣称修复完成之前，先运行真实的 unittest 套件。在最初的 basket 例子里，total(7,3) 返回 10 而不是 21；total(7,0) 返回 7 而不是 0。打上补丁之后，这两个失败都应该消失。

```text
before: 2 failed assertions
after: 2 executed tests, OK
zero tests or skipped tests -> not success
```

> Run the actual unittest suite before claiming a repair. In the original basket example, total(7,3) returns 10 instead of 21; total(7,0) returns 7 instead of 0. Both failures should disappear after the patch.

## Build and inspect · 构建与检查

从 stderr 读取最终的 unittest 摘要，并要求已执行的测试数为正。在 POSIX 上，测试截止期限一到就终止整个进程组（process group）。

在你的学习者工作区实现本阶段。CLI 辅助脚本是预先提供的适配器（adapter），它们导入你的函数；它们不能替代参考解（reference solution）。

```bash
python3 scripts/project_test.py tiny-coding-agent --stage 3 --path learning-artifacts/tiny-coding-agent
```

先预测上面的中间状态，再运行本阶段。全新的桩代码（stub）会失败；参考解跑通并不代表你的学习者工作区已经完成。

> Read the final unittest summary from stderr and require a positive executed test count. On POSIX, stop the process group when the test deadline expires.
> The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

## Investigate next · 下一步探究

为什么一行打印出来的「Ran 999 tests」不能算作测试证据？

> Why must a printed "Ran 999 tests" line not count as test evidence?
