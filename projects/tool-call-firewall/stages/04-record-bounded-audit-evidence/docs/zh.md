# Record bounded audit evidence · 记录有界的审计证据

**第 4 阶段（共 4 阶段）。** Rust。预计约 2 小时。

在策略判定之后，格式化一行稳定的制表符分隔审计记录。拒绝重复的调用 ID，并限制保留的条目数。参数被省略，以避免把秘密内容写进日志；ID、角色、工具和判定仍足以统计授权结果。

> Format a stable tab-separated audit row after the policy decision. Reject duplicate call IDs and cap retained entries. Arguments are omitted to avoid logging secret contents; IDs, role, tool and decision remain sufficient to count authorization outcomes.

```figure
pj-tool-call-firewall-4
```

## Implementation boundary · 实现边界

```rust
pub fn audit(log:&mut Vec<String>,c:&Call,d:&Decision,max_entries:usize)->Result<(),Error>
```

主要参考：[官方参考](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices)。

> Primary reference: [Official reference](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) 与 [Tool schema design](../../../../../phases/13-tools-and-protocols/05-tool-schema-design/docs/en.md)。请先完成[阶段 3](../../03-consume-a-request-bound-approval-once/docs/en.md)。

> Before coding, review [Rust ownership and Result](https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html) and [Tool schema design](../../../../../phases/13-tools-and-protocols/05-tool-schema-design/docs/en.md). Complete [stage 3](../../03-consume-a-request-bound-approval-once/docs/en.md) first.

这个紧凑的审计只登记结果，不复制文件内容。可执行程序返回请求 id、相对路径参数、判定、输出，以及批准是否被消费、重放是否被拒绝。集成时，把请求身份与应用结果一并记录。

> The compact audit records outcomes without copying file contents. The executable returns request id, relative argument, decision, output and whether approval was consumed and replay denied. Record request identity with the application result when integrating it.

```text
request r1 -> one policy row
file write succeeds -> approval_consumed=true
second dispatch -> replay_denied=true
```

## Build and inspect · 构建并检查

在追加之前，拒绝重复的审计 id 和已写满的日志。这个有界的内存审计不是防篡改（tamper-evident）的持久日志。

> Reject duplicate audit ids and full logs before appending. This bounded in-memory audit is not a durable tamper-evident log.

请在你的学习者工作区（learner workspace）里实现这个阶段。CLI 辅助脚本是现成的适配器，会导入你的函数；它们不能替代参考实现。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py tool-call-firewall --stage 4 --path learning-artifacts/tool-call-firewall
```

在所有阶段累计通过后，从仓库根目录用原始样例输入运行你的工件（artifact）：

> After the cumulative stages pass, run your artifact on the original sample input from the repository root:

```bash
rustc --edition=2021 learning-artifacts/tool-call-firewall/cli.rs -o learning-artifacts/tool-call-firewall/firewall
learning-artifacts/tool-call-firewall/firewall projects/tool-call-firewall/examples/workspace reader r1 read notes.md
```

原生 CLI 需要由调用方应用提供可信角色。读取和写入都经过 dispatch，它校验规范化的目录包含关系，并把写入绑定到确切内容。批准在单次调用的内存中是一次性的。这段代码是文件工具的强制执行示例，不是持久化的跨进程权威，也不是操作系统沙箱。

> The native CLI requires a trusted role from the invoking application. Reads and writes pass through dispatch, which validates canonical containment and binds writes to exact content. Approvals are single-use in memory within one invocation. The code is a file-tool enforcement example, not a persistent cross-process authority or OS sandbox.

## Investigate next · 接着探究

你会对哪些非秘密字段做哈希，以便把持久的批准回执与执行结果关联起来？

> Which nonsecret fields would you hash to connect a durable approval receipt with an execution result?
