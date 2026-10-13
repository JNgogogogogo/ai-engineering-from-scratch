# Consume a request-bound approval once · 一次性消费与请求绑定的批准

**第 3 阶段（共 4 阶段）。** Rust。预计约 2 小时。

批准记录（approval）保存完整的类型化请求：ID、角色、工具和参数。只有在「需要批准」的判定下才会消费它。不匹配、已使用或被拒绝的请求都会失败，且不改动批准记录。参数变了却保留同一个展示用 ID，属于冲突（conflict）。应用只有在用户批准了那条确切的请求之后，才创建这条记录。

> An approval stores the complete typed request: ID, role, tool and argument. It is consumed only for an approval-required decision. A mismatched, used or denied request fails without mutating the approval. Changing arguments while retaining the same displayed ID is a conflict. The application creates this record only after the user approves that exact request.

```figure
pj-tool-call-firewall-3
```

## Implementation boundary · 实现边界

```rust
pub fn authorize(c:&Call,approval:Option<&mut Approval>)->Result<(),Error>
```

主要参考：[官方参考](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices)。

> Primary reference: [Official reference](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 与 [Tool schema design](../../../../../phases/13-tools-and-protocols/05-tool-schema-design/docs/en.md)。请先完成[阶段 2](../../02-evaluate-role-and-path-policy/docs/en.md)。

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Tool schema design](../../../../../phases/13-tools-and-protocols/05-tool-schema-design/docs/en.md). Complete [stage 2](../../02-evaluate-role-and-path-policy/docs/en.md) first.

真实的文件 dispatcher 把批准绑定到类型化请求和写入内容上，并在执行写入之前消费回执（receipt）。载荷（payload）被改动或重放（replay）都会失败，无法再次写入。

> The real file dispatcher binds approval to the typed request and write content. It consumes the receipt before executing the write. A changed payload or replay fails and cannot write again.

```text
approved content="approved after restore"
changed content -> Conflict, file unchanged
exact content -> write, used=true
replay -> Conflict
```

## Build and inspect · 构建并检查

在消费批准之前，先校验载荷大小和真实的目录包含关系。把单次使用的回执保存在与 dispatch 相同的可信应用边界内。

> Validate payload size and actual containment before consuming approval. Keep the single-use receipt in the same trusted application boundary as dispatch.

请在你的学习者工作区（learner workspace）里实现这个阶段。CLI 辅助脚本是现成的适配器，会导入你的函数；它们不能替代参考实现。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py tool-call-firewall --stage 3 --path learning-artifacts/tool-call-firewall
```

先预测上面的中间状态，然后运行本阶段。全新的桩（stub）会失败；参考实现跑通并不意味着你的学习者工作区已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

要允许批准跨进程重启后复用，你需要什么样的持久化回执存储？

> What persistent receipt store would you need before allowing approval reuse across process restarts?
