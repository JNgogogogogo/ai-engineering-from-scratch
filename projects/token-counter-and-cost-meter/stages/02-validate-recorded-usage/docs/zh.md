# Validate recorded usage · 校验已记录的用量

**第 2 阶段（共 4 阶段）。** Rust。预计约 2 小时。

缓存输入（cached input）是输入的子集，绝不是可以重复累加的额外 token 类别。服务方记录中 cached 大于总 input 的记录是无效的。三个计数器都必须从显式的逗号分隔 fixture 传输格式（wire format）中解析；出现正负号或缺失字段一律拒绝。

> Cached input is a subset of input, never an extra token category to add twice. A provider record with cached greater than total input is invalid. Parse all three counters from an explicit comma-separated fixture wire format; reject signs and missing fields.

```figure
pj-token-counter-and-cost-meter-2
```

## Implementation boundary · 实现边界

```rust
pub fn parse_usage(line:&str)->Result<Usage,Error>
```

主要参考：[官方参考](https://doc.rust-lang.org/std/primitive.u64.html#method.checked_mul)。

> Primary reference: [Official reference](https://doc.rust-lang.org/std/primitive.u64.html#method.checked_mul).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 与 [Tokenizers](../../../../../phases/10-llms-from-scratch/01-tokenizers/docs/en.md)。请先完成[阶段 1](../../01-estimate-text-with-a-documented-bound/docs/en.md)。

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Tokenizers](../../../../../phases/10-llms-from-scratch/01-tokenizers/docs/en.md). Complete [stage 1](../../01-estimate-text-with-a-documented-bound/docs/en.md) first.

JSON 适配器读取记录下来的 input/output 用量与缓存输入明细；Rust 校验对应的 input,output,cached 三元组。缓存 token 是输入 token 的子集，不是一笔额外的输入费用。

> The JSON adapter reads recorded input/output usage and cached input details. Rust validates the corresponding input,output,cached triplet. Cached tokens are a subset of input tokens, not an additional input charge.

```text
input_tokens=100; output_tokens=20; cached_tokens=40
wire=100,20,40
uncached input=60
```

## Build and inspect · 构建并检查

拒绝布尔值、负数，以及 cached 超过 input 的计数。把服务方响应的归一化（normalization）挡在算术核心之外。

> Reject booleans, negative values and cached counts above input. Keep provider response normalization outside the arithmetic core.

请在你的学习者工作区（learner workspace）里实现这个阶段。CLI 辅助脚本是现成的适配器，会导入你的函数；它们不能替代参考实现。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py token-counter-and-cost-meter --stage 2 --path learning-artifacts/token-counter-and-cost-meter
```

先预测上面的中间状态，然后运行本阶段。全新的桩（stub）会失败；参考实现跑通并不意味着你的学习者工作区已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

当服务方响应缺少必需的 input 用量时，应该发生什么？

> What should happen when a provider response omits required input usage?
