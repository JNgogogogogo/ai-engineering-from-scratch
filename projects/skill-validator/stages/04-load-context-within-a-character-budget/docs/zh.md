# Load context within a character budget · 在字符预算内加载上下文

**第 4 阶段（共 4 阶段）。** Rust。预计约 2 小时。

> **Stage 4 of 4.** Rust. Plan about 2 hours.

发现（discovery）返回 name 和 description。只有当请求的预算装得下完整文本时，激活（activation）才追加正文（body）。宁可拒绝不完整的指令，也不要在一条约束中间截断。预算按字符计，不是模型 token 估计值。

> Discovery returns name and description. Activation appends the body only when the requested budget can hold the complete text. Refuse partial instructions rather than truncating in the middle of a constraint. The budget is characters, not a model-token estimate.

```figure
pj-skill-validator-4
```

## Implementation boundary · 实现边界

```rust
pub fn disclose(skill: &Skill, activate: bool, budget: usize) -> Result<String, Error>
```

主要参考：[官方参考](https://agentskills.io/specification)。

> Primary reference: [Official reference](https://agentskills.io/specification).

## Worked Orchard case · Orchard 实战案例

动手编码之前，先复习 [Rust 所有权与 Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 和 [数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。先完成 [阶段 3](../../03-contain-resource-paths/docs/en.md)。

发现只加载元数据；激活才追加指令。此后如果完整上下文装得下，CLI 可以再追加一个显式引用（reference）。按字符计数，而不是按字节或模型 token 计数，并且绝不截断半条指令。

```text
metadata length=80; body=120; separators=2
activation needs 202 characters
budget 200 -> Limit
```

> Discovery loads metadata only; activation appends instructions. The CLI can then append one explicit reference if the complete context fits. Count characters, not bytes or model tokens, and never truncate half an instruction.

## Build and inspect · 构建并检查

先组装出完整上下文，再把它的字符数与预算比较。要把分隔符和被请求的资源文本都算进去。

请在你的学习工作区（learner workspace）中实现该阶段。这些 CLI 辅助工具是预先提供的适配器（adapter），它们会导入你的函数；它们不能替代参考解法（reference solution）。

```bash
python3 scripts/project_test.py skill-validator --stage 4 --path learning-artifacts/skill-validator
```

在各阶段累计通过之后，从仓库根目录用最初的示例输入运行你的产物：

```bash
rustc --edition=2021 learning-artifacts/skill-validator/cli.rs -o learning-artifacts/skill-validator/validator
learning-artifacts/skill-validator/validator projects/skill-validator/examples/orchard-release 2000 --activate references/restore.md
```

该解析器接受纯文本单行值和 JSON 兼容的带引号字符串。它有意拒绝多行 YAML、别名、标签和流式集合（flow collection）。发现与激活后的上下文使用字符预算，而不是模型 token。已存在的规范化路径必须仍位于所提供的技能目录之内。

> Assemble the complete context before comparing its character count with the budget. Include separators and requested resource text.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> After the cumulative stages pass, run your artifact on the original sample input from the repository root:
> The parser accepts plain single-line values and JSON-compatible quoted strings. It intentionally rejects multiline YAML, aliases, tags and flow collections. Discovery and activated context use character budgets, not model tokens. Existing canonical paths must remain within the supplied skill directory.

## Investigate next · 接着探究

你会如何暴露一个基于分词器（tokenizer）的预算，又不让它与这个字符上限混淆？

> How would you expose a tokenizer-based budget without confusing it with this character limit?
