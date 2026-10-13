# Parse the capability request · 解析能力请求

**第 1 阶段（共 4 阶段）。** Rust。预留约 2 小时。

把威胁模型（threat model）表示为四个显式的布尔值：不可信代码（untrusted code）、含密钥主机（secret-bearing host）、拒绝网络（denied network）以及必需的内核隔离（required kernel separation）。拒绝未知的键和含糊的布尔取值。策略求值器（policy evaluator）有多大用处，取决于它真正理解了那份请求。

```figure
pj-sandbox-ladder-1
```

> Represent the threat model as four explicit booleans: untrusted code, secret-bearing host, denied network and required kernel separation. Reject unknown keys and ambiguous boolean values.
> A policy evaluator is only as useful as the request it actually understood.

## Implementation boundary · 实现边界

```rust
pub fn needs(text:&str)->Result<Needs,Error>
```

主要参考：[官方参考](https://docs.docker.com/engine/security/)。

> Primary reference: [Official reference](https://docs.docker.com/engine/security/).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Rust 所有权与 Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 和 [面向 AI 的 Docker](../../../../../phases/00-setup-and-tooling/07-docker-for-ai/docs/en.md)。

在选择运行时（runtime）之前，先把威胁需求写成布尔值。这里 `network=true` 表示要求禁用网络，`host_kernel=true` 表示要求一个独立的内核。这两个名字本身都不授予任何访问权限。

```text
untrusted=true,secrets=true,network=true,host_kernel=false
required: filesystem boundary + denied network
```

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Docker for AI](../../../../../phases/00-setup-and-tooling/07-docker-for-ai/docs/en.md).
> Write the threat requirement as booleans before selecting a runtime. Here network=true means network denial is required, and host_kernel=true means a separate kernel is required. Neither name grants access.

## Build and inspect · 构建并检查

拒绝重复的键，也拒绝精确 `true`/`false` 之外的任何取值。不要去猜 `network=yes` 是什么意思。

在你的学习者工作区（learner workspace）中实现本阶段。CLI 辅助脚本是随仓库提供的适配器（adapter），它们导入你的函数；它们不能替代参考解法。

```bash
python3 scripts/project_test.py sandbox-ladder --init learning-artifacts/sandbox-ladder
python3 scripts/project_test.py sandbox-ladder --stage 1 --path learning-artifacts/sandbox-ladder
```

先预测上方的中间状态，再运行本阶段。全新的桩（stub）会失败；参考实现跑通并不能证明你的学习者工作区已完成。

> Reject duplicate keys and values other than exact true/false. Do not guess what network=yes means.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 下一步探究

哪一个额外的需求，会让共享内核（shared-kernel）的容器变得不够用？

> Which additional requirement would make a shared-kernel container insufficient?
