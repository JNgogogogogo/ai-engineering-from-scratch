# Finish or reclaim expired work · 完成或回收过期的工作

> 一个缓慢的 worker 可能在另一个 worker 已经完成其任务之后才醒来。它的旧回执不得改写台账。

> A slow worker can wake after another worker has already completed its job. Its old receipt must not rewrite the ledger.

**Type:** Build
**Languages:** Go
**Prerequisites:** 完成阶段 1 至 2；理解它们导出的类型与失败契约。
**Stage:** 第 3 / 4 阶段
**Time:** ~2 小时

## What you build · 你要构建什么

把「完成」与「许可」分开。在你初始化好的工作区中实现 `stage3.go`。配套的 CLI 调用的是你的实现；它不会导入参考实现。

> Separate completion from permission. Implement `stage3.go` in your initialized workspace. The supplied CLI calls your implementation; it does not import the reference solution.

## Work through the mechanism · 剖析机制

Worker A 持有 version 1 直到 110。在 110 时刻，用 version 1 去完成会失败。Reclaim 把 running v1 变成 queued v2 并清掉租约，同时保留 attempts 1。Worker B 认领 queued v2，得到 running v3、attempts 2。A 迟到的完成请求仍然带着版本 1，所以即使它的时钟显示 105，也会失败。版本检查防住的是对时间的过期视角。

Worker B 在过期之前完成，得到 completed v4。完成是一次新的状态转换；它的版本不是认领时的版本。对 `Finish` 的重复调用会失败，因为任务已不再是 running。这与「幂等的输出回执」刻意不同：台账转换和业务副作用各有各的契约。

CLI 的 `--now-ms` 只用于可重复的实验。正常的 worker 在认领和完成时调用当前墙上时钟。注入的固定时钟能证明版本隔离（version fencing），但它无法模拟计算期间真实时钟的前进。多台机器、各自独立的时钟，需要一个由协调者掌控的时间权威。

```figure
pj-durable-agent-jobs-3
```

> Worker A owns version 1 until 110. At 110, finishing version 1 fails. Reclaim changes running v1 to queued v2 and clears the lease, while keeping attempts 1. Worker B claims queued v2 and receives running v3 with attempts 2. A late completion from A still carries 1, so it fails even if its clock says 105. The version check protects against a stale view of time.
> Completion is a new state transition; its version is not the claim version. Duplicate calls to `Finish` fail because the job is no longer running. This differs deliberately from an idempotent output receipt: ledger transitions and business effects have separate contracts.
> Use the CLI's `--now-ms` only for repeatable experiments. ... An injected fixed clock proves version fencing but does not model a real clock moving during computation. Multiple machines with independent clocks need a coordinator-owned time authority.

## Your contract · 你的契约

```go
func Finish(j *Job, expected int, now int64) error
func Reclaim(j *Job, now int64) bool
```

保持 `types.go` 中的公开签名和错误不变。被拒绝的调用必须保持调用方此前的状态。最终产物的文件与进程边界，请阅读 [the project API](../../../API.md)。

> Keep the public signature and errors in `types.go`. Rejected calls must preserve the caller's prior state. Read [the project API](../../../API.md) for the final artifact's file and process boundaries.

## Implementation hint · 实现提示

Reclaim 必须同时检查 running 状态和过期时间。queued 或 completed 的记录必须保持逐字节不变。Finish 既要检查当前版本，也要检查租约。

> Reclaim must test both running state and expiry. A queued or completed record should remain byte-for-byte unchanged. Finish must check the current version as well as the lease.

## Verify your work · 验证你的工作

在仓库根目录执行：

```bash
python3 scripts/project_test.py durable-agent-jobs --stage 3 --path /tmp/durable-agent-jobs-work --strict
```

评分器会测试你选定的工作区，包括更早的阶段。它的 reference 模式是单独的教师检查，不能算作学习者的完成凭证。

> From the repository root:
> The grader exercises your selected workspace, including the earlier stages. Its reference mode is a separate instructor check and does not earn learner completion.

## Investigate a failure · 排查一次失败

针对租约 110 分别测试 109 和 110。然后允许 A 在 B 已认领 v3 之后完成。说明为什么延长 A 的超时无法恢复 A 的权限。

> Test 109 and 110 against lease 110. Then allow A to finish after B has claimed v3. Describe why extending A's timeout cannot restore A's authority.

## Sources and limits · 资料与边界

按需研读标准库的 [os package](https://pkg.go.dev/os)、[context](https://pkg.go.dev/context) 和 [Go pipelines guide](https://go.dev/blog/pipelines)。这些练习和示例都是原创。进程恢复只在单机上演示；README 列出了你在改造该产物时必须保留的文件系统与评测限制。

> Study the standard-library [os package](https://pkg.go.dev/os), [context](https://pkg.go.dev/context) and [Go pipelines guide](https://go.dev/blog/pipelines) as needed. These exercises and samples are original. Process recovery is demonstrated on one host; the README names the filesystem and evaluation limits you must preserve when adapting the artifact.
