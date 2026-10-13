# Parse an explicit frontmatter subset · 解析显式的 frontmatter 子集

**第 1 阶段（共 4 阶段）。** Rust。预计约 2 小时。

> **Stage 1 of 4.** Rust. Plan about 2 hours.

只切分位于开头的一个 --- 块。接受纯文本或 JSON 兼容的双引号单行键/值对（key/value pair）；保留值内部的冒号，拒绝重复的键，并且绝不解释 YAML 标签（tag）或别名（alias）。这个解析器有意只实现 YAML 的一个子集，而不是一个通用实现。

> Split only a leading --- block. Accept plain or JSON-compatible double-quoted single-line key/value pairs; preserve colons inside values, reject duplicate keys, and never interpret YAML tags or aliases. This parser is intentionally a subset of YAML rather than a general-purpose implementation.

```figure
pj-skill-validator-1
```

## Implementation boundary · 实现边界

```rust
pub fn parse(text: &str) -> Result<std::collections::BTreeMap<String,String>, Error>
```

主要参考：[官方参考](https://agentskills.io/specification)。

> Primary reference: [Official reference](https://agentskills.io/specification).

## Worked Orchard case · Orchard 实战案例

动手编码之前，先复习 [Rust 所有权与 Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 和 [数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

安装器（installer）会发出带引号的元数据。接受纯文本单行标量（scalar）和 JSON 兼容的双引号标量，包括转义引号和 Unicode；拒绝标签、别名和多行 YAML，而不是悄悄地把它们重新解释掉。

```text
description: "Check \"replicas\" first"
parsed description: Check "replicas" first
description: | -> unsupported syntax
```

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md).
> The installer emits quoted metadata. Accept plain single-line scalars and JSON-compatible double-quoted scalars, including escaped quotes and Unicode. Reject tags, aliases and multiline YAML rather than silently reinterpreting them.

## Build and inspect · 构建并检查

在第一个冒号处切分头部行。在元数据校验之前先解码带引号的值；重复的键视为冲突。

请在你的学习工作区（learner workspace）中实现该阶段。这些 CLI 辅助工具是预先提供的适配器（adapter），它们会导入你的函数；它们不能替代参考解法（reference solution）。

```bash
python3 scripts/project_test.py skill-validator --init learning-artifacts/skill-validator
python3 scripts/project_test.py skill-validator --stage 1 --path learning-artifacts/skill-validator
```

先预测上面的中间状态，然后运行该阶段。全新的存根（stub）会失败；参考解法跑通并不代表你的学习工作区已经完成。

> Split a header line at its first colon. Decode quoted values before metadata validation; duplicate keys are conflicts.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

为什么一个与标准兼容的子集需要对不支持语法给出显式错误？

> Why does a standards-compatible subset need an explicit unsupported-syntax error?
