# Confine file tools to a workspace · 把文件工具限制在工作区内

**第 1 阶段（共 4 阶段）。** Python。计划耗时约 2 小时。

智能体（agent）的文件工具必须先把路径解释成相对于工作区（workspace）的路径，然后在检查包含关系之前解析符号链接（symlink）。只比较字符串前缀是不够的：/tmp/work-other 以 /tmp/work 开头，却是另一个目录。

> An agent file tool must interpret paths relative to the workspace, then resolve symlinks before checking containment. String prefixes are insufficient: /tmp/work-other starts with /tmp/work but is a different directory.

本项目保护的是可信本地教学工作区中的文件工具路径。它不会对 Python 测试做沙箱隔离（sandbox），不能防止并发的符号链接竞态（symlink race），也不能隔离敌意代码。请只在本项目中运行可信的 fixture。

> This protects file-tool paths in a trusted local teaching workspace. It does not sandbox Python tests, prevent a concurrent symlink race, or isolate hostile code. Only run trusted fixtures in this project.

```figure
pj-tiny-coding-agent-1
```

主要参考：[主要技术参考（Primary technical reference）](https://docs.python.org/3/library/subprocess.html)。

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html) 和 [智能体循环](../../../../../phases/14-agent-engineering/01-the-agent-loop/docs/en.md)。

Orchard 的购物篮（basket）修复运行在一个可信 Python 工作区的一次性副本里。在打开每个被请求的文件之前，都要先把它解析（resolve）到该根目录之下。一个路径可能看起来是本地的，但符号链接会把它重定向到工作区之外。

```text
basket.py -> contained existing file
../basket.py -> reject
symlink to external file -> reject
```

> The Orchard basket repair runs in a disposable copy of a trusted Python workspace. Resolve every requested file under that root before opening it. A path may look local while a symlink redirects it outside the workspace.

## Build and inspect · 构建与检查

比较解析后的路径组件（path components），而不是字符串前缀。工作区由调用方选择；模型的一次响应绝不能自己选定新的根目录。

在你的学习者工作区实现本阶段。CLI 辅助脚本是预先提供的适配器（adapter），它们导入你的函数；它们不能替代参考解（reference solution）。

```bash
python3 scripts/project_test.py tiny-coding-agent --init learning-artifacts/tiny-coding-agent
python3 scripts/project_test.py tiny-coding-agent --stage 1 --path learning-artifacts/tiny-coding-agent
```

先预测上面的中间状态，再运行本阶段。全新的桩代码（stub）会失败；参考解跑通并不代表你的学习者工作区已经完成。

> Compare resolved path components, not string prefixes. The caller chooses the workspace; a model response must not choose a new root.
> The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

## Investigate next · 下一步探究

为什么复制一个可信仓库，并不能让它里面的测试变成被沙箱隔离的代码？

> Why does copying a trusted repository not turn its tests into sandboxed code?
