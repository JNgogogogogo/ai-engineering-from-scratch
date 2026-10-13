# Estimate text with a documented bound · 用有据可查的上界估算文本

**第 1 阶段（共 4 阶段）。** Rust。预计约 2 小时。

统计 Unicode 标量值（Unicode scalar values），并用一个可配置的每 token 字符数比率（characters-per-token ratio）做向上取整除法（ceiling division）。这个有意从简的估算器适合用作预检（preflight）告警。后续的精确准入会使用服务方记录的真实用量，而不是假装这里做的是 BPE 计数。

> Count Unicode scalar values and use a configurable characters-per-token ratio with ceiling division. This intentionally rough estimator is useful for a preflight warning. Exact admission later uses recorded provider usage rather than pretending this is BPE.

```figure
pj-token-counter-and-cost-meter-1
```

## Implementation boundary · 实现边界

```rust
pub fn estimate(text:&str, chars_per_token:u64)->Result<u64,Error>
```

主要参考：[官方参考](https://doc.rust-lang.org/std/primitive.u64.html#method.checked_mul)。

> Primary reference: [Official reference](https://doc.rust-lang.org/std/primitive.u64.html#method.checked_mul).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 与 [Tokenizers](../../../../../phases/10-llms-from-scratch/01-tokenizers/docs/en.md)。

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Tokenizers](../../../../../phases/10-llms-from-scratch/01-tokenizers/docs/en.md).

从一个看得见的近似开始：按每 token 4 个字符计，21 个 Unicode 标量值估算为 6 个 token。这只是预检规划的基线；服务方的真实计数会因语言、标点符号和分词器（tokenizer）而异。

> Start with a visible approximation. At four characters per token, 21 Unicode scalar values estimate six tokens. This is a baseline for preflight planning; actual provider counts can differ by language, punctuation and tokenizer.

```text
characters=21; ratio=4
ceil(21/4)=6 estimated tokens
```

## Build and inspect · 构建并检查

用「商加余数检查」的方式实现，避免先加 ratio-1 再除带来的溢出。永远不要把这个结果标榜成服务方分词器的计数。

> Use quotient plus a remainder check, avoiding overflow from adding ratio-1. Never label this result a provider tokenizer count.

请在你的学习者工作区（learner workspace）里实现这个阶段。CLI 辅助脚本是现成的适配器，会导入你的函数；它们不能替代参考实现。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py token-counter-and-cost-meter --init learning-artifacts/token-counter-and-cost-meter
python3 scripts/project_test.py token-counter-and-cost-meter --stage 1 --path learning-artifacts/token-counter-and-cost-meter
```

先预测上面的中间状态，然后运行本阶段。全新的桩（stub）会失败；参考实现跑通并不意味着你的学习者工作区已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

同样的字符数，为什么在两种语言里可能对应不同的 token 数？

> Why might the same number of characters cost different token counts in two languages?
