# Validate an unambiguous call envelope · 校验无歧义的调用信封

**第 1 阶段（共 4 阶段）。** Rust。预计约 2 小时。

在这个本地练习里，解析一个有边界的四字段信封（envelope），使用竖线分隔符（pipe delimiter）。拒绝缺失身份（identity）、控制字符和超长输入。这套语法有意比 JSON 窄，绝不能被悄悄当成通用线上协议复用。

> Parse a bounded four-field envelope using a pipe delimiter for this local exercise. Reject missing identity, control characters and overlong input. This grammar is intentionally narrower than JSON and must not be quietly reused as a general wire protocol.

```figure
pj-tool-call-firewall-1
```

## Implementation boundary · 实现边界

```rust
pub fn call(line:&str,max_bytes:usize)->Result<Call,Error>
```

主要参考：[官方参考](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices)。

> Primary reference: [Official reference](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 与 [Tool schema design](../../../../../phases/13-tools-and-protocols/05-tool-schema-design/docs/en.md)。

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Tool schema design](../../../../../phases/13-tools-and-protocols/05-tool-schema-design/docs/en.md).

身份由调用方应用提供；模型只提供提议的操作。这个紧凑的 Rust 信封携带稳定的请求 id、角色、工具和相对路径参数，不含歧义分隔符或控制字符。

> The caller application supplies identity; the model supplies only a proposed operation. The compact Rust envelope carries a stable request id, role, tool and relative argument without ambiguous delimiters or controls.

```text
r1|reader|read|notes.md -> typed request
r1|reader|read|notes.md|extra -> reject
```

## Build and inspect · 构建并检查

在策略评估之前，先校验完整的有界信封。在 CLI 中，trusted-role 是操作员传入的参数，不是从模型文本里接受进来的字段。

> Validate the entire bounded envelope before policy evaluation. In the CLI, trusted-role is an operator argument, not a field accepted from model text.

请在你的学习者工作区（learner workspace）里实现这个阶段。CLI 辅助脚本是现成的适配器，会导入你的函数；它们不能替代参考实现。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py tool-call-firewall --init learning-artifacts/tool-call-firewall
python3 scripts/project_test.py tool-call-firewall --stage 1 --path learning-artifacts/tool-call-firewall
```

先预测上面的中间状态，然后运行本阶段。全新的桩（stub）会失败；参考实现跑通并不意味着你的学习者工作区已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

如果模型能把 reader 换成 editor，会破坏什么？

> What would break if a model could replace reader with editor?
