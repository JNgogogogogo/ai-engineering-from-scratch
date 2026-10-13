# Price with checked integers · 用带溢出检查的整数定价

**第 3 阶段（共 4 阶段）。** Rust。预计约 2 小时。

fixture 费率表（rate card）以每 token 纳诺美元（nano-dollars）计价。未缓存输入、缓存输入和输出分别按各自的费率计费。每一次乘法和加法都做溢出检查（checked），浮点舍入不可能悄悄改动账单。

> The fixture rate card uses nano-dollars per token. Charge uncached input, cached input and output at separate rates. Every multiplication and sum is checked for overflow, and no floating-point rounding can silently change the bill.

```figure
pj-token-counter-and-cost-meter-3
```

## Implementation boundary · 实现边界

```rust
pub fn cost(usage:&Usage,rates:&Rates)->Result<u64,Error>
```

主要参考：[官方参考](https://doc.rust-lang.org/std/primitive.u64.html#method.checked_mul)。

> Primary reference: [Official reference](https://doc.rust-lang.org/std/primitive.u64.html#method.checked_mul).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 与 [Tokenizers](../../../../../phases/10-llms-from-scratch/01-tokenizers/docs/en.md)。请先完成[阶段 2](../../02-validate-recorded-usage/docs/en.md)。

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Tokenizers](../../../../../phases/10-llms-from-scratch/01-tokenizers/docs/en.md). Complete [stage 2](../../02-validate-recorded-usage/docs/en.md) first.

使用给定的整数费率表（单位为每 token 纳诺美元）。当 input=2、output=5、cached=1 时，这条被记录的请求花费 260 纳诺美元。这些 fixture 费率不是服务方当前的真实价格。

> Use supplied integer rate cards in nano-dollars per token. With input=2, output=5 and cached=1, the recorded request costs 260 nano-dollars. These fixture rates are not current provider prices.

```text
60 uncached * 2 = 120
40 cached * 1 = 40
20 output * 5 = 100
total=260 nano_dollars
```

## Build and inspect · 构建并检查

乘法与加法都使用带溢出检查的 u64 运算。不要把每个组成部分先换算成浮点美元再取整。

> Multiply and add with checked u64 operations. Do not round each component through floating-point dollars.

请在你的学习者工作区（learner workspace）里实现这个阶段。CLI 辅助脚本是现成的适配器，会导入你的函数；它们不能替代参考实现。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py token-counter-and-cost-meter --stage 3 --path learning-artifacts/token-counter-and-cost-meter
```

先预测上面的中间状态，然后运行本阶段。全新的桩（stub）会失败；参考实现跑通并不意味着你的学习者工作区已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

如果算术悄悄回绕（wrap），溢出会如何影响预算准入？

> How would an overflow affect budget admission if arithmetic wrapped silently?
