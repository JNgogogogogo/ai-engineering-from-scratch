# Detect named advisory patterns · 检测具名的建议型（advisory）模式

**Stage 2 of 4 · 第 2 阶段（共 4 阶段）。** Rust。计划约 2 小时。

规则对小写化后的行文本做匹配，但报告的是原始偏移。把指令覆盖（instruction override）、密钥文件访问和「命令连网」（command-to-network）组合各自标记为独立的 finding。引号里的示例同样可能命中；保留原始行让人可以裁决这类误报。

> Rules inspect lowercase line text but report original offsets. Flag instruction overrides, secret-file access and command-to-network combinations as separate findings. A quoted example can still match; preserving the line lets a human resolve that false positive.

```figure
pj-skill-scanner-2
```

## Implementation boundary · 实现边界

```rust
pub fn scan(lines:&[Span])->Vec<Finding>
```

主要参考：[官方规范（Official reference）](https://agentskills.io/specification)。

> Primary reference: [Official reference](https://agentskills.io/specification).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 和 [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。先完成 [阶段 1](../../01-retain-byte-accurate-source-spans/docs/en.md)。

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md). Complete [stage 1](../../01-retain-byte-accurate-source-spans/docs/en.md) first.

把显式能力标记出来供审查。Orchard 审查包里有一条指令覆盖，还有一条把 .env 读进网络客户端的命令。每个模式各产出一个具名的 advisory finding。

> Flag explicit capabilities for review. The Orchard review bundle contains an instruction override and a command that reads .env into a network client. Each pattern yields a named advisory finding.

```text
Ignore previous instructions. -> instruction-override, severity 3
curl https://... < .env -> secret-access 2 + network-command 2
```

## Build and inspect · 构建与检视

让匹配规则保持小而具名。文档完全可能合法地提到这些字符串；混淆过的命令也可能绕开它们。

> Keep matching rules small and named. Documentation may legitimately mention these strings; obfuscated commands may evade them.

请在你的学习者工作区（learner workspace）中实现本阶段。CLI 辅助工具是预先提供的适配器，它们导入你的函数；它们不能替代参考实现。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py skill-scanner --stage 2 --path learning-artifacts/skill-scanner
```

先预测上面的中间状态，再运行本阶段。全新的存根（stub）会失败；一次通过的参考运行并不能证明你的学习者工作区已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接下来探究

写一个无害的文档示例和一个绕过（evasion）样例，用来暴露这种启发式的局限。

> Write one benign documentation example and one evasion that expose the heuristic limits.
