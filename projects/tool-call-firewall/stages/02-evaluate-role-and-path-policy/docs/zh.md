# Evaluate role and path policy · 评估角色与路径策略

**第 2 阶段（共 4 阶段）。** Rust。预计约 2 小时。

只存在 reader 和 editor 两种角色。读取使用相对路径；写入要求 editor 角色并需要批准（approval）。拒绝父目录组件（parent components）、绝对路径、顶层隐藏路径和未知工具。这里检查的是词法（lexical）策略；真实的文件适配器还必须强制符号链接（symlink）安全的目录包含（containment）。

> Only reader and editor roles exist. Reads use relative paths; writes require the editor role and approval. Reject parent components, absolute paths, hidden top-level paths and unknown tools. This checks lexical policy; the actual file adapter must enforce symlink-safe containment.

```figure
pj-tool-call-firewall-2
```

## Implementation boundary · 实现边界

```rust
pub fn decide(c:&Call)->Decision
```

主要参考：[官方参考](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices)。

> Primary reference: [Official reference](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 与 [Tool schema design](../../../../../phases/13-tools-and-protocols/05-tool-schema-design/docs/en.md)。请先完成[阶段 1](../../01-validate-an-unambiguous-call-envelope/docs/en.md)。

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Tool schema design](../../../../../phases/13-tools-and-protocols/05-tool-schema-design/docs/en.md). Complete [stage 1](../../01-validate-an-unambiguous-call-envelope/docs/en.md) first.

策略拒绝未知角色、不支持的工具和不安全的路径组件。reader 可以读取被包含在内的笔记；editor 写入需要批准。词法层面放行（allow）之后，dispatch 仍会做真实的文件系统包含检查。

> Policy denies unknown roles, unsupported tools and unsafe path components. A reader may read a contained note; an editor write needs approval. A lexical allow is still followed by actual filesystem containment in dispatch.

```text
reader + read notes.md -> Allow
reader + write notes.md -> Deny
editor + write notes.md -> ApprovalRequired
```

## Build and inspect · 构建并检查

把 Deny 作为默认分支。在真实访问文件之前先检查规范化路径（canonical paths）；不要把策略判定误当成操作系统级隔离。

> Make Deny the default branch. Check canonical paths before real file access; do not mistake a policy verdict for OS isolation.

请在你的学习者工作区（learner workspace）里实现这个阶段。CLI 辅助脚本是现成的适配器，会导入你的函数；它们不能替代参考实现。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py tool-call-firewall --stage 2 --path learning-artifacts/tool-call-firewall
```

先预测上面的中间状态，然后运行本阶段。全新的桩（stub）会失败；参考实现跑通并不意味着你的学习者工作区已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

当符号链接的相对名字里根本不含父目录组件时，为什么它仍可能逃逸出去？

> Why can a symlink escape even when its relative name contains no parent component?
