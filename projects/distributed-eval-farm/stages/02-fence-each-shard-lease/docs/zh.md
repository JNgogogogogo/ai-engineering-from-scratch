# Fence each shard lease · 为每个 shard 租约加上围栏

> 租约（lease）必须比获取它的进程活得更久。下一个进程必须推进同一个 version。
>
> A lease must survive the process that acquired it. The next process must advance the same version.

**Type:** Build
**Languages:** Go
**Prerequisites:** 完成阶段 1；理解其导出的类型与失败契约。
**Stage:** 2 of 4
**Time:** ~2 hours

## What you build · 你要构建什么

让另一个进程能安全接管。在你初始化好的工作区里实现 `stage2.go`。配套的 CLI 调用的是你的实现；它不会 import 参考答案。

> Let another process take over safely. Implement `stage2.go` in your initialized workspace. The supplied CLI calls your implementation; it does not import the reference solution.

## Work through the mechanism · 剖析机制

第一个 worker 在 100 ms 以 10 ms 的租约认领 shard-0。存储的记录是 owner old、version 1、until 110。第二个 worker 在 109 时无法获取它；到 110 时可以成为 owner new、version 2。已完成的 shard 无论时间如何都保持关闭。

`Acquire` 只修改内存里的一个 Lease。`ClaimShard` 在 `ledger.lock` 之下把它和整次运行的快照组合起来：持锁期间重新加载、选出一个可认领的 shard、调用 Acquire、保存，然后才把 case 交给 worker。如果认领还没持久化就开始评估，崩溃后将不存在可恢复的 owner。

初始化之后运行 `farm worker --crash-after-claim`。这会启动一个真实进程，在 rename 之后以退出码 86 退出，把它的 lease 留在磁盘上。在到期边界上的接替进程可以恢复该 shard。观察这个失败不需要网络、模型服务或合成的回调。

所有参与者都必须在本地 Linux 或 macOS 文件系统上使用这个带锁的包装。直接裸调 Acquire 不具备跨进程协调能力。网络文件系统或远程数据库需要自己的事务与时钟契约。

```figure
pj-distributed-eval-farm-2
```

> The first worker claims shard-0 at 100 ms with a 10 ms lease. Its stored record has owner old, version 1 and until 110. A second worker at 109 cannot acquire it. At 110 it can become owner new with version 2. Completed shards stay closed regardless of time.
> `ClaimShard` composes it with a whole-run snapshot under `ledger.lock`. ... Starting an evaluation before the claim is durable would leave no recoverable owner after a crash.
> A replacement process at the expiry boundary can recover the shard. No network, model service or synthetic callback is needed to observe that failure.
> All participants must use the locking wrapper on a local Linux or macOS filesystem. A raw call to Acquire does not coordinate processes.

## Your contract · 你的契约

```go
func Acquire(l *Lease, worker string, now, ttl int64) error
```

公开签名和错误类型保持在 `types.go` 里。被拒绝的调用必须保留调用方此前的状态。最终产物的文件与进程边界参见[项目 API](../../../API.md)。

> Keep the public signature and errors in `types.go`. Rejected calls must preserve the caller's prior state. Read [the project API](../../../API.md) for the final artifact's file and process boundaries.

## Implementation hint · 实现提示

变更之前先检查 Done 和「当前被持有且未过期」的租约。校验时钟运算。owner、version 与过期的修改要保持成组完成。

> Check Done and a currently owned unexpired lease before mutation. Validate clock arithmetic. Keep owner, version and expiry changes together.

## Verify your work · 验证你的实现

在仓库根目录：

```bash
python3 scripts/project_test.py distributed-eval-farm --stage 2 --path /tmp/distributed-eval-farm-work --strict
```

评分器会操练你选定的工作区，包括更早的阶段。它的 reference 模式是单独的教师检查，不计为学习者的完成。

> From the repository root:
> The grader exercises your selected workspace, including the earlier stages. Its reference mode is a separate instructor check and does not earn learner completion.

## Investigate a failure · 探查一个失败

让一个 worker 认领之后暂停，再在同一逻辑时刻运行另一个。确认结果是上报了待办工作，而不是被抢走。在 110 恢复运行并检查持久化的 version。

> Pause a worker after it claims, then run another at the same logical time. Confirm that pending work is reported instead of stolen. Resume at 110 and inspect the persisted version.

## Sources and limits · 资料与边界

按需研读标准库的 [os package](https://pkg.go.dev/os)、[context](https://pkg.go.dev/context) 和 [Go pipelines 指南](https://go.dev/blog/pipelines)。这些练习和样例都是原创。进程恢复只在单机上演示；README 说明了改造该产物时必须保留的文件系统与评估限制。

> Study the standard-library [os package](https://pkg.go.dev/os), [context](https://pkg.go.dev/context) and [Go pipelines guide](https://go.dev/blog/pipelines) as needed. These exercises and samples are original. Process recovery is demonstrated on one host; the README names the filesystem and evaluation limits you must preserve when adapting the artifact.
