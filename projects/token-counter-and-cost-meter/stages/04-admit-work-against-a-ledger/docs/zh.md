# Admit work against a ledger · 对照账本准入工作

**第 4 阶段（共 4 阶段）。** Rust。预计约 2 小时。

只有当已花费（spent）加报价（quote）落在配置限额之内时，才为这笔报价预留（reserve）额度。恰好压在边界上视为通过；被拒绝的预留绝不改动账本（ledger）。本示例是单进程内的记账，不声称具备并发的分布式保证。

> Reserve a quoted amount only if spent plus quote is within the configured limit. An exact boundary is accepted; a rejected reservation never mutates the ledger. This example is single-process accounting and does not claim concurrent distributed guarantees.

```figure
pj-token-counter-and-cost-meter-4
```

## Implementation boundary · 实现边界

```rust
pub fn reserve(spent:&mut u64,quote:u64,limit:u64)->Result<u64,Error>
```

主要参考：[官方参考](https://doc.rust-lang.org/std/primitive.u64.html#method.checked_mul)。

> Primary reference: [Official reference](https://doc.rust-lang.org/std/primitive.u64.html#method.checked_mul).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 与 [Tokenizers](../../../../../phases/10-llms-from-scratch/01-tokenizers/docs/en.md)。请先完成[阶段 3](../../03-price-with-checked-integers/docs/en.md)。

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Tokenizers](../../../../../phases/10-llms-from-scratch/01-tokenizers/docs/en.md). Complete [stage 3](../../03-price-with-checked-integers/docs/en.md) first.

对照记录的用量重放（replay）各笔预留。第一条 Orchard 请求预留 600、结算（settle）260，释放 340。随后一条需要 1,500 的请求，在只剩 430 时被拒绝。保存下来的 JSON 保留请求 id 和全部结算字段。

> Replay reservations against recorded usage. The first Orchard request reserves 600 and settles 260, releasing 340. A later request requiring 1,500 is blocked when only 430 remains. Saved JSON retains request ids and all settlement fields.

```text
limit=1000
request 1 reserved=600 actual=260 unused=340
request 2 actual=310 -> spent=570
remaining=430; larger reservation -> blocked
```

## Build and inspect · 构建并检查

即使实际用量超过估算，结算也必须记录真实用量。超支（overrun）要显式标记；不要靠给计费成本封顶来掩盖它。

> A settlement must record actual usage even when it exceeds the estimate. Mark an overrun explicitly; do not hide it by capping the billed cost.

请在你的学习者工作区（learner workspace）里实现这个阶段。CLI 辅助脚本是现成的适配器，会导入你的函数；它们不能替代参考实现。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py token-counter-and-cost-meter --stage 4 --path learning-artifacts/token-counter-and-cost-meter
```

在所有阶段累计通过后，从仓库根目录用原始样例输入运行你的工件（artifact）：

> After the cumulative stages pass, run your artifact on the original sample input from the repository root:

```bash
python3 learning-artifacts/token-counter-and-cost-meter/usage.py projects/token-counter-and-cost-meter/examples/usage.json --out usage-ledger.json
```

费率是显式的 fixture 输入（整数纳诺美元每 token），不是服务方当前价格。usage.py 负责把记录的用量 JSON 归一化，并把带溢出检查的算术委托给 Rust。它的账本是经 --out 保存的顺序重放；它不是实时计费服务，也不是并发预留存储。

> Rates are explicit fixture inputs in integer nano-dollars per token, not current provider prices. usage.py normalizes recorded usage JSON and delegates checked arithmetic to Rust. Its ledger is a sequential replay saved with --out; it is not a live billing service or concurrent reservation store.

## Investigate next · 接着探究

agent-budget-planner 可以复用哪些字段，而不会把报价误当成实际用量？

> Which fields can the agent-budget-planner reuse without confusing a quote with actual usage?
