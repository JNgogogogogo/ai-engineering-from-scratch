# Run a bounded local worker pool · 运行有界的本地 worker 池

> 当每个被派发的 worker 都走同一条持久化认领与回执路径时，并发才真正变得有用。
>
> Concurrency becomes useful when every dispatched worker uses the same durable claim and receipt path.

**Type:** Build
**Languages:** Go
**Prerequisites:** 完成阶段 1 到 3；理解它们导出的类型与失败契约。
**Stage:** 4 of 4
**Time:** ~2 hours

## What you build · 你要构建什么

让整个 farm 跨进程跑起来。在你初始化好的工作区里实现 `stage4.go`。配套的 CLI 调用的是你的实现；它不会 import 参考答案。

> Run the whole farm across processes. Implement `stage4.go` in your initialized workspace. The supplied CLI calls your implementation; it does not import the reference solution.

## Work through the mechanism · 剖析机制

围绕注入的回调实现一个有界的 goroutine 池。channel 承载唯一的 work ID；同时调用回调的数量至多是配置的 worker 数。收集成功的 Item 并按 ID 排序。如果某个回调失败，就把它的错误连同实际收集到的成功结果一起返回。取消（cancellation）会阻止新的有效工作，并被传入每一个回调。

最终的 `run` 命令用这个池来启动操作系统级的 worker 进程。每个回调都用 worker 命令执行同一个编译出的二进制。每个进程获取一个已持久化的 shard，评估其录制的预测，并通过当前 lease 提交。工作以有界的一波波（wave）推进，直到所有 shard 完成，或每个剩余 shard 都有未过期的 owner。

对四条 case 的样例、workers 2，两波会创建四个短命进程。上界 2 描述的是同时存在的进程数，不是进程总数。最终报告展示 4 题对 3、完整覆盖、数据集哈希、shard owner 以及真实的进程 ID。PID 每次运行都会不同；分数来自配套的响应。

最后阶段的测试会让一个延迟的旧 worker 和一个接替者同场运行。接替者提交之后，旧进程以 fencing 错误退出，持久化的快照保持不变。测试还会让 worker 崩溃、从磁盘重启、拒绝被改动过的数据集，并保留损坏的输入以供诊断。这是同主机协调，不是多机传输。

```figure
pj-distributed-eval-farm-4
```

> Implement a bounded goroutine pool around an injected callback. ... If one callback fails, return its error alongside the successes you actually collected. Cancellation stops new useful work and is passed into every callback.
> The final `run` command uses this pool to launch operating-system worker processes. ... Work runs in bounded waves until all shards finish or every remaining shard has an unexpired owner.
> The bound 2 describes simultaneous processes, not total process count.
> After the replacement commits, the old process exits with a fencing error and the persisted snapshot remains unchanged. ... This is same-host coordination, not a multi-machine transport.

## Your contract · 你的契约

```go
func Parallel(ctx context.Context, ids []string, workers int, run func(context.Context, string) (string, error)) ([]Item, error)
```

公开签名和错误类型保持在 `types.go` 里。被拒绝的调用必须保留调用方此前的状态。最终产物的文件与进程边界参见[项目 API](../../../API.md)。

> Keep the public signature and errors in `types.go`. Rejected calls must preserve the caller's prior state. Read [the project API](../../../API.md) for the final artifact's file and process boundaries.

## Implementation hint · 实现提示

只有派发 goroutine 才能关闭 jobs channel。等所有 worker 退出后再关闭 results。给结果收集足够的容量，或者在出错之后继续 drain，避免发送方被卡死。

> Only the dispatch goroutine closes the jobs channel. Close results after all workers exit. Give result collection enough capacity or keep draining it after an error to avoid stranding senders.

## Verify your work · 验证你的实现

在仓库根目录：

```bash
python3 scripts/project_test.py distributed-eval-farm --stage 4 --path /tmp/distributed-eval-farm-work --strict
```

评分器会操练你选定的工作区，包括更早的阶段。它的 reference 模式是单独的教师检查，不计为学习者的完成。

> From the repository root:
> The grader exercises your selected workspace, including the earlier stages. Its reference mode is a separate instructor check and does not earn learner completion.

## Investigate a failure · 探查一个失败

分别用 workers 1 和 2 跑样例，比较覆盖率和回执，而不是墙钟速度。试试 workers 0 和已取消的 context。解释为什么一个无视 context 的回调仍可能拖延池的关闭。

> Run the sample with workers 1 and 2 and compare coverage and receipts, not wall-clock speed. Try workers 0 and a canceled context. Explain why a callback that ignores context can still delay pool shutdown.

## Sources and limits · 资料与边界

按需研读标准库的 [os package](https://pkg.go.dev/os)、[context](https://pkg.go.dev/context) 和 [Go pipelines 指南](https://go.dev/blog/pipelines)。这些练习和样例都是原创。进程恢复只在单机上演示；README 说明了改造该产物时必须保留的文件系统与评估限制。

> Study the standard-library [os package](https://pkg.go.dev/os), [context](https://pkg.go.dev/context) and [Go pipelines guide](https://go.dev/blog/pipelines) as needed. These exercises and samples are original. Process recovery is demonstrated on one host; the README names the filesystem and evaluation limits you must preserve when adapting the artifact.
