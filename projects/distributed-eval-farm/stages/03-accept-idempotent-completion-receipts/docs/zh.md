# Accept idempotent completion receipts · 接受幂等的完成回执

> 来自错误租约的正确结果，仍然是过期结果。
>
> Correct results from the wrong lease are still stale results.

**Type:** Build
**Languages:** Go
**Prerequisites:** 完成阶段 1 到 2；理解它们导出的类型与失败契约。
**Stage:** 3 of 4
**Time:** ~2 hours

## What you build · 你要构建什么

一个租约只接受一个结果。在你初始化好的工作区里实现 `stage3.go`。配套的 CLI 调用的是你的实现；它不会 import 参考答案。

> Accept one result for one lease. Implement `stage3.go` in your initialized workspace. The supplied CLI calls your implementation; it does not import the reference solution.

## Work through the mechanism · 剖析机制

一个结果绑定 shard、owner 和 version 三者。假设 old/v1 算出了正确答案，但 new/v2 已经完成了该 shard。提交 old/v1 必须在比较结果文本之前就失败。worker 再聪明，也不会因此获得当前的写权限。

完成之前：要求 now < Until，且结果非空、至多 1 MiB。完成之后：同样的 owner、version 和完全相同的结果可以再次成功投递，即使租约时间已过——这是对既有回执的确认（acknowledge），不是重新打开评估。改动结果的任何一个字节都会冲突。

CLI 先把录制的响应和期望文本都转小写、折叠空白，再进行评估。`GET` 和 ` get ` 匹配；`no` 和 `yes` 不匹配。每个 shard 回执保存有序的 case ID、正确性标志以及真实的 worker PID。coordinator 先核验回执的覆盖与计数，然后才把它写入持久化的 Lease.Result。

这是一个窄口径的精确匹配评估器。它评不了改写（paraphrase）、引用支撑或模型推理。只有先定义稳定的评分版本、并把该版本纳入运行身份（run identity）之后，才能更换评估器。

```figure
pj-distributed-eval-farm-3
```

> A result is tied to shard, owner and version. ... Submitting old/v1 must fail before comparing result text. The worker's intelligence does not give it current write authority.
> Before completion, require now < Until and a nonempty result of at most 1 MiB. After completion, the same owner, version and exact result can be delivered again successfully, even after the lease time has passed. ... Changing any result byte conflicts.
> Each shard receipt stores ordered case IDs, correctness flags and the actual worker PID. The coordinator verifies the receipt's coverage and counts before writing it into the persisted Lease.Result.
> This is a narrow exact-match evaluator. It cannot grade paraphrases, citation support or model reasoning.

## Your contract · 你的契约

```go
func Submit(l *Lease, worker string, version int, now int64, result string) error
```

公开签名和错误类型保持在 `types.go` 里。被拒绝的调用必须保留调用方此前的状态。最终产物的文件与进程边界参见[项目 API](../../../API.md)。

> Keep the public signature and errors in `types.go`. Rejected calls must preserve the caller's prior state. Read [the project API](../../../API.md) for the final artifact's file and process boundaries.

## Implementation hint · 实现提示

先检查 owner 和 version。再处理「已完成」的情形。过期条件只作用于首次完成；正是这个顺序让相同回执的重复投递成为可能。

> Check owner and version first. Then handle an already completed result. Apply the expiry condition only to a first completion; this ordering permits identical receipt redelivery.

## Verify your work · 验证你的实现

在仓库根目录：

```bash
python3 scripts/project_test.py distributed-eval-farm --stage 3 --path /tmp/distributed-eval-farm-work --strict
```

评分器会操练你选定的工作区，包括更早的阶段。它的 reference 模式是单独的教师检查，不计为学习者的完成。

> From the repository root:
> The grader exercises your selected workspace, including the earlier stages. Its reference mode is a separate instructor check and does not earn learner completion.

## Investigate a failure · 探查一个失败

在 109 完成，在 200 用完全相同的数据重复投递，然后改动结果的一个字节。预测这三种结局。再用相同数据试一个旧 owner，并解释它为什么仍然失败。

> Complete at 109, redeliver at 200 with identical data, then change one result byte. Predict all three outcomes. Try an old owner with identical data and explain why it still fails.

## Sources and limits · 资料与边界

按需研读标准库的 [os package](https://pkg.go.dev/os)、[context](https://pkg.go.dev/context) 和 [Go pipelines 指南](https://go.dev/blog/pipelines)。这些练习和样例都是原创。进程恢复只在单机上演示；README 说明了改造该产物时必须保留的文件系统与评估限制。

> Study the standard-library [os package](https://pkg.go.dev/os), [context](https://pkg.go.dev/context) and [Go pipelines guide](https://go.dev/blog/pipelines) as needed. These exercises and samples are original. Process recovery is demonstrated on one host; the README names the filesystem and evaluation limits you must preserve when adapting the artifact.
