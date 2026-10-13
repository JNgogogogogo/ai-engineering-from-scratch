# Retain byte-accurate source spans · 保留字节级精确的源码区间

**Stage 1 of 4 · 第 1 阶段（共 4 阶段）。** Rust。计划约 2 小时。

把 UTF-8 源码切成带行号的行，并保留指向原始缓冲区（buffer）的排他（exclusive）字节偏移。只剥掉行终止符。finding（发现项）必须引用精确的原始切片，而不是在规范化之后重新拼装证据。

> Split UTF-8 source into numbered lines and retain exclusive byte offsets into the original buffer. Strip only the line terminator. A finding must quote the exact slice rather than reconstructing evidence after normalization.

```figure
pj-skill-scanner-1
```

## Implementation boundary · 实现边界

```rust
pub fn spans(text:&str,max_bytes:usize)->Result<Vec<Span>,Error>
```

主要参考：[官方规范（Official reference）](https://agentskills.io/specification)。

> Primary reference: [Official reference](https://agentskills.io/specification).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 和 [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md).

源码证据使用字节偏移。包含 café 的那一行占用的 UTF-8 字节比可见字母更多，所以用字符索引去切 Rust 字符串并不安全。切分行时要保留起点和终点偏移。

> Source evidence uses byte offsets. A line containing café occupies more UTF-8 bytes than visible letters, so character indices cannot safely slice a Rust string. Preserve start and end offsets while splitting lines.

```text
text="café\n.env"
first line bytes [0,5)
second line bytes [6,10)
```

## Build and inspect · 构建与检视

让游标按原始行的字节数前进，包括换行符本身。只在展示的引用里剥掉 CRLF。

> Advance the cursor by the original line bytes, including the newline. Strip CRLF only from the displayed quote.

请在你的学习者工作区（learner workspace）中实现本阶段。CLI 辅助工具是预先提供的适配器，它们导入你的函数；它们不能替代参考实现。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py skill-scanner --init learning-artifacts/skill-scanner
python3 scripts/project_test.py skill-scanner --stage 1 --path learning-artifacts/skill-scanner
```

先预测上面的中间状态，再运行本阶段。全新的存根（stub）会失败；一次通过的参考运行并不能证明你的学习者工作区已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接下来探究

一个错误的偏移会怎样把一个本来正确的 finding 变成无效证据？

> How would a wrong offset turn an otherwise correct finding into invalid evidence?
