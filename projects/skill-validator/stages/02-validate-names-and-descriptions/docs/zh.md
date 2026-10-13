# Validate names and descriptions · 校验名称与描述

**第 2 阶段（共 4 阶段）。** Rust。预计约 2 小时。

> **Stage 2 of 4.** Rust. Plan about 2 hours.

加载器只接受长度 1 到 64 字节的小写名称，名称内部只允许单个出现的连字符（hyphen）、不限制以数字开头，并要求一段最长 1024 字符的非空白（nonblank）描述。要把技能目录名与元数据做相互校验，这样发现（discovery）流程就无法悄悄地给一个包改名。

> The loader accepts only lowercase names of 1 to 64 bytes with single interior hyphens, no leading digit restriction, and a nonblank description up to 1024 characters. Validate the skill directory name against metadata so discovery cannot silently rename a package.

```figure
pj-skill-validator-2
```

## Implementation boundary · 实现边界

```rust
pub fn validate(fields: &std::collections::BTreeMap<String,String>, directory: &str) -> Result<Skill, Error>
```

主要参考：[官方参考](https://agentskills.io/specification)。

> Primary reference: [Official reference](https://agentskills.io/specification).

## Worked Orchard case · Orchard 实战案例

动手编码之前，先复习 [Rust 所有权与 Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 和 [数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。先完成 [阶段 1](../../01-parse-an-explicit-frontmatter-subset/docs/en.md)。

元数据标识一个包。带大写字母的 Orchard-release 无法通过可移植的小写文法；出现在名称不同目录里的 orchard-release 无法通过一致性校验。

```text
directory=orchard-release
name=orchard-release -> valid
name=orchard--release -> invalid name
```

> Metadata identifies a package. Orchard-release with an uppercase letter fails the portable lowercase grammar; orchard-release in a differently named directory fails identity validation.

## Build and inspect · 构建并检查

按照契约统计名称的字节数和描述的 Unicode 标量值（scalar value）。解析之后保留供人阅读的描述。

请在你的学习工作区（learner workspace）中实现该阶段。这些 CLI 辅助工具是预先提供的适配器（adapter），它们会导入你的函数；它们不能替代参考解法（reference solution）。

```bash
python3 scripts/project_test.py skill-validator --stage 2 --path learning-artifacts/skill-validator
```

先预测上面的中间状态，然后运行该阶段。全新的存根（stub）会失败；参考解法跑通并不代表你的学习工作区已经完成。

> Count name bytes and description Unicode scalar values according to the contract. Preserve the human description after parsing.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

为什么修改了目录名，就应该同样要求修改元数据？

> Why should changing a directory name require changing metadata too?
