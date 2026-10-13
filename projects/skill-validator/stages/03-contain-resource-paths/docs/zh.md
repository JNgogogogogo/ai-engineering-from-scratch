# Contain resource paths · 把资源路径限制在边界内

**第 3 阶段（共 4 阶段）。** Rust。预计约 2 小时。

> **Stage 3 of 4.** Rust. Plan about 2 hours.

相对技能根目录（skill root）解析资源名称。在拼接（join）之前就拒绝绝对路径、父目录组件（parent component）和 Windows 分隔符，然后对已存在的路径做规范化（canonicalize），让符号链接（symlink）无法逃逸。规范化检查的是当前的文件系统；生产级的对抗性加载器还需要基于文件描述符的打开方式（descriptor-relative opens）来关闭后续的替换竞态（race）。

> Resolve resource names relative to a skill root. Reject absolute paths, parent components and Windows separators before joining, then canonicalize existing paths so a symlink cannot escape. Canonicalization checks the current filesystem; a production adversarial loader needs descriptor-relative opens to close later replacement races.

```figure
pj-skill-validator-3
```

## Implementation boundary · 实现边界

```rust
pub fn reference_path(root: &std::path::Path, resource: &str) -> Result<std::path::PathBuf, Error>
```

主要参考：[官方参考](https://agentskills.io/specification)。

> Primary reference: [Official reference](https://agentskills.io/specification).

## Worked Orchard case · Orchard 实战案例

动手编码之前，先复习 [Rust 所有权与 Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 和 [数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。先完成 [阶段 2](../../02-validate-names-and-descriptions/docs/en.md)。

资源查找相对于技能文件夹进行。解析 references/restore.md 并验证它的规范化路径仍留在该文件夹内；在读取任何内容之前就拒绝父目录穿越（parent traversal）。

```text
resource references/restore.md -> contained file
resource ../private.md -> invalid component
symlink outside root -> escapes root
```

> Resource lookup is relative to the skill folder. Resolve references/restore.md and verify its canonical path stays within that folder; reject parent traversal before reading anything.

## Build and inspect · 构建并检查

在拼接之前先校验路径组件，然后再做规范化。这个教学用的加载器不会关闭对抗性的路径替换竞态。

请在你的学习工作区（learner workspace）中实现该阶段。这些 CLI 辅助工具是预先提供的适配器（adapter），它们会导入你的函数；它们不能替代参考解法（reference solution）。

```bash
python3 scripts/project_test.py skill-validator --stage 3 --path learning-artifacts/skill-validator
```

先预测上面的中间状态，然后运行该阶段。全新的存根（stub）会失败；参考解法跑通并不代表你的学习工作区已经完成。

> Validate path components before joining, then canonicalize. This educational loader does not close adversarial path-replacement races.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

为什么对原始路径文本做 starts_with 不足以保证包含关系（containment）？

> Why is starts_with on raw path text insufficient for containment?
