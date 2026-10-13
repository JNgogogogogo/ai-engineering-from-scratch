# Select the least costly sufficient profile · 选出成本最低的充分配置档

**第 3 阶段（共 4 阶段）。** Rust。预留约 2 小时。

先过滤掉不充分的配置档，再比较成本。遵守配置好的成本上限（cost ceiling），按名字打破平局（tie），并在没有合适配置档时返回一个明确的错误。绝不因为预算太小，就把一项必需的隔离控制悄悄降级。

```figure
pj-sandbox-ladder-3
```

> Filter insufficient profiles before comparing cost. Respect the configured cost ceiling, break ties by name, and return an explicit no-suitable-profile error.
> Never downgrade a required isolation control merely because the budget is too small.

## Implementation boundary · 实现边界

```rust
pub fn select(n:&Needs,candidates:&[Profile],budget:u32)->Result<Profile,Error>
```

主要参考：[官方参考](https://docs.docker.com/engine/security/)。

> Primary reference: [Official reference](https://docs.docker.com/engine/security/).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Rust 所有权与 Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 和 [面向 AI 的 Docker](../../../../../phases/00-setup-and-tooling/07-docker-for-ai/docs/en.md)。先完成 [阶段 2](../../02-define-modeled-control-profiles/docs/en.md)。

成本最低的充分配置档也可能超出允许的预算。当要求内核隔离时，预算 4 不能悄悄降级到成本为 3 的容器。

```text
kernel separation required; candidates costs 1,2,3,5
budget 4 -> no sufficient profile
budget 5 -> microvm-fixture
```

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Docker for AI](../../../../../phases/00-setup-and-tooling/07-docker-for-ai/docs/en.md). Complete [stage 2](../../02-define-modeled-control-profiles/docs/en.md) first.
> The cheapest sufficient profile may exceed the allowed budget. When kernel separation is required, budget 4 cannot silently downgrade to a container costing 3.

## Build and inspect · 构建并检查

先按能力过滤，再按成本，最后按稳定的名字顺序。如果剩下的集合为空，返回一个限额（limit）错误。

在你的学习者工作区（learner workspace）中实现本阶段。CLI 辅助脚本是随仓库提供的适配器（adapter），它们导入你的函数；它们不能替代参考解法。

```bash
python3 scripts/project_test.py sandbox-ladder --stage 3 --path learning-artifacts/sandbox-ladder
```

先预测上方的中间状态，再运行本阶段。全新的桩（stub）会失败；参考实现跑通并不能证明你的学习者工作区已完成。

> Filter by capabilities first, then cost, then stable name ordering. Return a limit error if the remaining set is empty.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 下一步探究

当两个充分配置档的建模成本相同时，应该改变什么？

> What should change when two sufficient profiles have the same modeled cost?
