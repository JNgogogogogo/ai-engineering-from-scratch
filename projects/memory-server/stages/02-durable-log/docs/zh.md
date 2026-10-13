# Serialize revisioned writes · 串行化带修订号的写入

第 2 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 2 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

加载带版本的事件日志，为每个 namespace/id 对重建最新记录。一次更新必须指明它期望的 revision。对写入做串行化，让两个同时从 revision 0 起跑的调用者不能都成功。先追加（append），再修改内存中的 map。这是一个单进程存储：追加完成不等于断电级别的持久性保证，多个服务器进程需要外部锁或数据库。

本阶段的边界是 `MemoryStore.put, MemoryStore.list`。保持之前阶段的行为不变：最终评分器会在同一个 workspace 上运行每一个阶段。

> Load a versioned event log and reconstruct the latest record for each namespace/id pair. An update must name its expected revision. Serialize writes so two callers racing from revision zero cannot both succeed. ... Append before mutating the in-memory map. This is a single-process store: append completion is not a power-loss durability guarantee, and multiple server processes require an external lock or database.

## Work through one concrete case · 走一遍具体案例

同一进程里的两个写入者都对同一个 id 提出 `expectedRevision0`。串行化的队列放行其中一个 create、拒绝另一个；重放 JSONL 日志会重建出 revision 1。

```figure
pj-memory-server-2
```

修改实验（lab）的输入，先自己算出结果，再去看它的指标。图中数字由这些输入计算而来；下面的实现测试仍然是完成与否的证据来源。

> Two writers in the same process both propose expectedRevision0 for the same id. The serialized queue admits one create and rejects the other; replaying the JSONL log reconstructs revision 1. ... Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的 workspace `main.ts` 里实现 `MemoryStore.put, MemoryStore.list`。先自己尝试契约，之后再去读参考实现中导出的类型。保留起始代码的公开名称，测试才能调用你的实现。核心函数返回结构化值，不要在核心函数内部打印；最终结果由 CLI 打印。

使用[公开的 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示交给随附的 driver。

先追加再修改 map。追加失败时，内存中的值不得假装持久化成功了。操作失败之后要保持 tail promise 仍然可用，让后续互不相关的写入得以继续。

> Implement `MemoryStore.put, MemoryStore.list` in your workspace `main.ts`. ... Append before mutating the map. On a failed append, the in-memory value must not pretend persistence succeeded. Keep the tail promise usable after a failed operation so later independent writes can proceed.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py memory-server --init learning-artifacts/memory-server` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py memory-server --stage 2 --path learning-artifacts/memory-server --strict
```

全新的 workspace 在你实现契约之前应当判为失败。每个阶段完成后，用随附的样例运行你的真实产物：

```bash
cd learning-artifacts/memory-server
node cli.ts --data-dir memory-data --put samples/memory.json
node cli.ts --data-dir memory-data --query "cache policy"
node cli.ts --data-dir memory-data --history cache-policy
```

> From the repository root, initialize once with `python3 scripts/project_test.py memory-server --init learning-artifacts/memory-server`. Then grade cumulatively ... A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample.

## Investigate the failure boundary · 探查失败边界

在两个独立进程里用 revision 0 各跑一次 `cli.ts --put`。第二次运行会失败。然后改用 revision 1，并用 `--history` 查看两条日志条目。

> Run cli.ts --put twice from separate processes with revision 0. The second run fails. Then use revision 1 and inspect both log entries with --history.

## References · 参考资料

[MCP tools 规范](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
[Rust 标准库](https://doc.rust-lang.org/std/)
[Node HTTP API](https://nodejs.org/api/http.html)
