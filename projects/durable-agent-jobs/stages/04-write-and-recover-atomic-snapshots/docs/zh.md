# Write and recover atomic snapshots · 写入并恢复原子快照

> 崩溃可能发生在输出已经存在之后、队列记录完成之前。让这个缺口可以复现。

> A crash can happen after an output exists but before the queue records completion. Make that gap reproducible.

**Type:** Build
**Languages:** Go
**Prerequisites:** 完成阶段 1 至 3；理解它们导出的类型与失败契约。
**Stage:** 第 4 / 4 阶段
**Time:** ~2 小时

## What you build · 你要构建什么

把效果（effect）和台账一起恢复。在你初始化好的工作区中实现 `stage4.go`。配套的 CLI 调用的是你的实现；它不会导入参考实现。

> Recover the effect and the ledger. Implement `stage4.go` in your initialized workspace. The supplied CLI calls your implementation; it does not import the reference solution.

## Work through the mechanism · 剖析机制

在打开临时快照之前，先校验每个任务并拒绝重复的标识符。在目标目录里写入，同步（sync）文件，关闭它，然后用 rename 覆盖 `jobs.json`。加载器把文件限制在 4 MiB 以内，并拒绝被截断的 JSON、未知字段和尾随文档。一次失败的校验必须保留上一个快照。

组合而成的 worker 先持久化自己的认领，读取不可变的输入，创建 `effects/<id>.json`，然后持久化完成状态。回执（receipt）包含输入的 SHA256、字节数和词数。临时回执先做同步，再通过 link 挂到最终名字上，且不覆盖已有文件。如果那份最终回执已经包含期望的值，恢复时直接复用它。

在你完成的工作区里运行 `go run . demo`。demo 会启动一个真实的 worker，它在写出第一个 effect 之后以退出码 86 退出。Status 显示 running v1 和一个回执。下一个 worker 使用逻辑时间 111，回收并认领 v3，观察到既有回执，然后以 `reused_effect: true` 完成 v4。第二个示例任务正常完成。

原子 rename 保护读者免受残缺 JSON 的伤害。它并不把输入、回执和台账变成一个事务。生产者崩溃可能留下一个未被引用的输入文件；一次完全相同的入队可以安全地收养它。只同步文件而不同步目录，不能作为断电持久性的证明。这些练习建立的是本地文件系统上的进程崩溃恢复。

```figure
pj-durable-agent-jobs-4
```

> Validate every job and reject duplicate identifiers before opening a temporary snapshot. Write in the destination directory, sync the file, close it, then rename it over `jobs.json`. The loader bounds the file at 4 MiB and rejects truncated JSON, unknown fields and trailing documents. A failed validation must preserve the previous snapshot.
> The receipt contains the input SHA256, byte count and word count. A temporary receipt is synced, then linked into its final name without replacement. If that final receipt already contains the expected values, recovery reuses it.
> Atomic rename protects readers from partial JSON. It does not turn the input, receipt and ledger into one transaction. ... File sync without directory sync is not a proof of power-loss durability. These exercises establish process-crash recovery on a local filesystem.

## Your contract · 你的契约

```go
func ValidateJobs(jobs []Job) error
func Save(file string, jobs []Job) error
func Load(file string) ([]Job, error)
```

保持 `types.go` 中的公开签名和错误不变。被拒绝的调用必须保持调用方此前的状态。最终产物的文件与进程边界，请阅读 [the project API](../../../API.md)。

> Keep the public signature and errors in `types.go`. Rejected calls must preserve the caller's prior state. Read [the project API](../../../API.md) for the final artifact's file and process boundaries.

## Implementation hint · 实现提示

在对临时文件的每一个操作都成功之前，保留旧快照。不要用 defer 把 Close 的错误吞掉。跟着 `runner.go` 看你的函数如何在一把锁之下组合起来。

> Keep the old snapshot until every operation on the temporary file succeeds. Do not defer away a Close error. Follow `runner.go` to see how your functions compose under one lock.

## Verify your work · 验证你的工作

在仓库根目录执行：

```bash
python3 scripts/project_test.py durable-agent-jobs --stage 4 --path /tmp/durable-agent-jobs-work --strict
```

评分器会测试你选定的工作区，包括更早的阶段。它的 reference 模式是单独的教师检查，不能算作学习者的完成凭证。

> From the repository root:
> The grader exercises your selected workspace, including the earlier stages. Its reference mode is a separate instructor check and does not earn learner completion.

## Investigate a failure · 排查一次失败

先运行 README 中「认领之后崩溃」的实验，再运行「写出 effect 之后崩溃」。在每次恢复前后数一数回执文件的数量。在纸面上把回执替换成一次 HTTP 支付调用：你会需要什么样的幂等键和持久化接收方契约？

> Run the crash-after-claim experiment from the README, then crash-after-effect. Count receipt files before and after each recovery. Replace the receipt with an HTTP payment call on paper: what idempotency key and durable receiver contract would you need?

## Sources and limits · 资料与边界

按需研读标准库的 [os package](https://pkg.go.dev/os)、[context](https://pkg.go.dev/context) 和 [Go pipelines guide](https://go.dev/blog/pipelines)。这些练习和示例都是原创。进程恢复只在单机上演示；README 列出了你在改造该产物时必须保留的文件系统与评测限制。

> Study the standard-library [os package](https://pkg.go.dev/os), [context](https://pkg.go.dev/context) and [Go pipelines guide](https://go.dev/blog/pipelines) as needed. These exercises and samples are original. Process recovery is demonstrated on one host; the README names the filesystem and evaluation limits you must preserve when adapting the artifact.
