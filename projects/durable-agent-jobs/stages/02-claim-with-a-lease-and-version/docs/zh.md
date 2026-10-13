# Claim with a lease and version · 用租约和版本进行认领

> 认领（claim）是 worker 获得行动许可的那一刻。在开始工作之前，先把它持久化。

> The claim is the moment a worker acquires permission to act. Persist it before starting the work.

**Type:** Build
**Languages:** Go
**Prerequisites:** 完成阶段 1；理解其导出的类型与失败契约。
**Stage:** 第 2 / 4 阶段
**Time:** ~2 小时

## What you build · 你要构建什么

预留一个执行窗口。在你初始化好的工作区中实现 `stage2.go`。配套的 CLI 调用的是你的实现；它不会导入参考实现。

> Reserve an execution window. Implement `stage2.go` in your initialized workspace. The supplied CLI calls your implementation; it does not import the reference solution.

## Work through the mechanism · 剖析机制

从 queued、version 0、attempts 0 出发。在 100 ms 发起、租约 10 ms、期望版本为 0 的认领，会变成 running、version 1、attempts 1、lease 110。租约区间是 [100,110)：右端点被排除在外。

两个 worker 可能都读到 version 0。只有第一次成功的认领可以继续。如果先修改记录、之后才检查期望版本，就丢掉了拒绝第二个 worker 所需的证据。要在给任何字段赋值之前，先校验状态、期望版本、尝试上限、时钟和溢出。

`ClaimJob` 是一个纯内存转换。配套的 `ClaimNext` 封装在加载、转换和 Save 期间持有一个操作系统级的文件锁。多个进程打开同一个 `ledger.lock`；进程崩溃时内核锁会随之释放。`jobs.json` 会被整体替换，而这个稳定的锁文件保持原位。如果给被改名的快照本身加锁，不同进程就会锁住不同的文件对象。

尝试计数器在恢复之后依然保留。一个崩溃过三次的任务，在上限为 3 时应当仍然以 queued、attempts 3 的状态可见；悄悄清零计数器会制造一个无限重试循环。

```figure
pj-durable-agent-jobs-2
```

> Start with queued version 0, attempts 0. A claim at 100 ms for 10 ms with expected version 0 becomes running version 1, attempts 1, lease 110. The lease interval is [100,110): its right endpoint is excluded.
> Only the first successful claim may proceed. ... Validate state, expected version, attempt cap, clock and overflow before assigning any field.
> `ClaimJob` is a pure in-memory transition. ... Locking the renamed snapshot itself would let processes lock different file objects.
> The attempt counter survives recovery. A job that crashes three times should remain visible as queued with attempts 3 when the cap is 3; silently clearing the counter would create an unlimited retry loop.

## Your contract · 你的契约

```go
func ClaimJob(j *Job, expected int, now, ttl int64, maxAttempts int) error
```

保持 `types.go` 中的公开签名和错误不变。被拒绝的调用必须保持调用方此前的状态。最终产物的文件与进程边界，请阅读 [the project API](../../../API.md)。

> Keep the public signature and errors in `types.go`. Rejected calls must preserve the caller's prior state. Read [the project API](../../../API.md) for the final artifact's file and process boundaries.

## Implementation hint · 实现提示

把每一次拒绝都写成提前返回。先检查 `now > MaxInt64-ttl`，再做加法。只有在那之后，才赋值 lease、version、尝试计数和状态。

> Write every rejection as an early return. Check `now > MaxInt64-ttl` before addition. Only then assign lease, version, attempt count and state.

## Verify your work · 验证你的工作

在仓库根目录执行：

```bash
python3 scripts/project_test.py durable-agent-jobs --stage 2 --path /tmp/durable-agent-jobs-work --strict
```

评分器会测试你选定的工作区，包括更早的阶段。它的 reference 模式是单独的教师检查，不能算作学习者的完成凭证。

> From the repository root:
> The grader exercises your selected workspace, including the earlier stages. Its reference mode is a separate instructor check and does not earn learner completion.

## Investigate a failure · 排查一次失败

预测两个调用方都传入 expected 0 之后的快照。然后把 maxAttempts 设为 1，并重新认领第一次尝试。为什么尽管状态是 queued，下一次认领仍会失败？

> Predict the snapshot after two callers both supply expected 0. Then set maxAttempts 1 and reclaim the first attempt. Why does the next claim fail even though the state is queued?

## Sources and limits · 资料与边界

按需研读标准库的 [os package](https://pkg.go.dev/os)、[context](https://pkg.go.dev/context) 和 [Go pipelines guide](https://go.dev/blog/pipelines)。这些练习和示例都是原创。进程恢复只在单机上演示；README 列出了你在改造该产物时必须保留的文件系统与评测限制。

> Study the standard-library [os package](https://pkg.go.dev/os), [context](https://pkg.go.dev/context) and [Go pipelines guide](https://go.dev/blog/pipelines) as needed. These exercises and samples are original. Process recovery is demonstrated on one host; the README names the filesystem and evaluation limits you must preserve when adapting the artifact.
