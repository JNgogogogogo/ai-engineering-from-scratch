# Build an explicit review gate · 构建显式的审查闸门

**Stage 4 of 4 · 第 4 阶段（共 4 阶段）。** Rust。计划约 2 小时。

越过阈值就请求人工审查；低于阈值只说明这些规则没有越过配置的阈值，别无其他含义。限制 finding 数量，校验所有源码切片，并输出带行号和原文引用的文本报告。这道闸门绝不执行技能指令。

> A threshold crossing requests review; below threshold means only that these rules did not cross the configured threshold. Limit finding count, validate all source slices, and emit a text report with line numbers and literal quotes. The gate never executes skill instructions.

```figure
pj-skill-scanner-4
```

## Implementation boundary · 实现边界

```rust
pub fn review(text:&str,findings:&[Finding],threshold:u32,max_findings:usize)->Result<String,Error>
```

主要参考：[官方规范（Official reference）](https://agentskills.io/specification)。

> Primary reference: [Official reference](https://agentskills.io/specification).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 和 [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。先完成 [阶段 3](../../03-score-distinct-evidence-without-inflation/docs/en.md)。

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md). Complete [stage 3](../../03-score-distinct-evidence-without-inflation/docs/en.md) first.

遍历调用方的 bundle，以带版本（versioned）的 JSON 输出文件路径、行号、字节偏移和引用的源码。阈值用于请求审查；低于阈值并不等于宣告某个技能是安全的。

> Traverse the caller bundle and emit file paths, line numbers, byte offsets and quoted source in versioned JSON. The threshold requests a review; falling below it is not a declaration that a skill is safe.

```text
benign bundle -> below-threshold
reviewable bundle -> review-required
findings retain path + exact source slice
```

## Build and inspect · 构建与检视

扫描之前先拒绝符号链接，并给文件数量与字节数设上限。让审查状态与安装器的完整性检查保持分离。

> Reject symlinks and bound file count and bytes before scanning. Keep review state separate from installer integrity checks.

请在你的学习者工作区（learner workspace）中实现本阶段。CLI 辅助工具是预先提供的适配器，它们导入你的函数；它们不能替代参考实现。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py skill-scanner --stage 4 --path learning-artifacts/skill-scanner
```

累计各阶段都通过之后，从仓库根目录用最初的示例输入运行你的产物：

> After the cumulative stages pass, run your artifact on the original sample input from the repository root:

```bash
rustc --edition=2021 learning-artifacts/skill-scanner/cli.rs -o learning-artifacts/skill-scanner/scanner
learning-artifacts/skill-scanner/scanner projects/skill-scanner/examples/reviewable 3
```

扫描器输出带版本的 JSON，包含文件路径、精确的 UTF-8 字节区间和 advisory 规则。显式模式可能漏掉混淆写法，也可能误伤无辜的文档。below-threshold 不等于安全；扫描状态永远不能替代安装完整性检查或人工审查。

> The scanner emits versioned JSON with file paths, exact UTF-8 byte spans and advisory rules. Explicit patterns can miss obfuscation and flag benign documentation. below-threshold does not mean safe; scan status never replaces installation integrity or human review.

## Investigate next · 接下来探究

在批准一次升级之前，你会先讨论哪一个新出现的 finding？

> Which newly introduced finding would you discuss before approving an upgrade?
