# Score distinct evidence without inflation · 只给去重后的证据打分，不许注水

**Stage 3 of 4 · 第 3 阶段（共 4 阶段）。** Rust。计划约 2 小时。

即使收集器（collector）重复给出同一个 finding，每条规则在每一源码行上也只计一次。用 checked 算术求 severity 总和。拒绝越界的 severity 和不可能的偏移，让畸形的扫描数据无法伪装成一个低分。

> Count each rule once per source line even if a collector repeats a finding. Sum severity with checked arithmetic. Reject out-of-range severities and impossible offsets so malformed scanner data cannot masquerade as a low score.

```figure
pj-skill-scanner-3
```

## Implementation boundary · 实现边界

```rust
pub fn risk_score(findings:&[Finding])->Result<u32,Error>
```

主要参考：[官方规范（Official reference）](https://agentskills.io/specification)。

> Primary reference: [Official reference](https://agentskills.io/specification).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 和 [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。先完成 [阶段 2](../../02-detect-named-advisory-patterns/docs/en.md)。

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md). Complete [stage 2](../../02-detect-named-advisory-patterns/docs/en.md) first.

每个 finding 按规则与源码行只挣一次 severity。重复同一检测不得推高风险值，而同一行上两个不同的能力仍是彼此独立的证据。

> A finding earns its severity once per rule and source line. Duplicating the same detection must not increase risk, while two distinct capabilities on one line remain separate evidence.

```text
line 7 secret-access severity 2, repeated twice -> 2
line 7 network-command severity 2 -> total 4
```

## Build and inspect · 构建与检视

先校验范围与 severity，再按规则和行去重。总和用 checked 加法。

> Deduplicate by rule and line after validating ranges and severity. Use checked addition for the total.

请在你的学习者工作区（learner workspace）中实现本阶段。CLI 辅助工具是预先提供的适配器，它们导入你的函数；它们不能替代参考实现。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py skill-scanner --stage 3 --path learning-artifacts/skill-scanner
```

先预测上面的中间状态，再运行本阶段。全新的存根（stub）会失败；一次通过的参考运行并不能证明你的学习者工作区已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接下来探究

只按行去重，为什么会掩盖第二种能力？

> Why would deduplicating only by line hide a second capability?
