# Confine file tools to a bounded root · 把文件工具约束在有界根目录内

**4 个阶段中的第 2 阶段。** Rust。预计约 2 小时。

对 workspace 根目录和请求的目标做规范化（canonicalize），拒绝绝对路径和含父目录穿越的路径，并验证 symlink 仍落在根目录之内。文本读取限制在 16 KiB，目录结果限制在 100 条，搜索限制在 50 行匹配。这些是面向受信任本地 workspace 的应用层约束；要对抗恶意的并发 symlink 替换，需要更强的 OS 原语或隔离手段。

> Canonicalize the workspace root and requested targets, reject absolute and parent-traversing paths, and verify that symlinks remain inside the root. Limit text reads to 16 KiB, directory results to 100 entries and searches to 50 matching lines. These are application-level constraints for a trusted local workspace; hostile concurrent symlink replacement requires stronger OS primitives or isolation.

```figure
pj-rust-agent-shell-2
```

## Worked Orchard case · Orchard 实例演算

动手写代码前，先复习 [Rust 所有权与 Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html)和[数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)，并先完成[阶段 1](../../01-grammar/docs/en.md)。

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md). Complete [stage 1](../../01-grammar/docs/en.md) first.

读取 release.md 之前，先把它解析（resolve）到 workspace 根目录之下。一个词法上看起来无害的路径，其 symlink 可能指向 workspace 之外的文件。得到的是应用层约束（containment），不是进程沙箱。

> Resolve release.md under the workspace root before reading it. A lexical path can look harmless while a symlink targets a file outside the workspace. The result is application-level containment, not a process sandbox.

```text
workspace=/work/orchard
release.md -> /work/orchard/release.md -> allowed
link.md -> /outside/credentials -> rejected
```

## Build and inspect · 构建与检查

先规范化根目录和目标，再逐级比较路径组件。既要限制初始 metadata 的长度，也要限制实际读到的字节数。

> Canonicalize the root and target, then compare path components. Bound the bytes read as well as the initial metadata length.

在你的 learner workspace（学习者工作区）中实现该阶段。这些 CLI 辅助脚本是由项目提供的适配器，会导入你的函数；它们不能替代参考实现（reference solution）。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py rust-agent-shell --stage 2 --path learning-artifacts/rust-agent-shell
```

先预测上面的中间状态，再运行该阶段。全新的 stub 必然失败；参考实现跑通并不代表你的 learner workspace 已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

如果另一个进程在规范化之后替换了某个路径，还剩下哪种竞争条件（race）？

> Which race remains if another process replaces a path after canonicalization?
