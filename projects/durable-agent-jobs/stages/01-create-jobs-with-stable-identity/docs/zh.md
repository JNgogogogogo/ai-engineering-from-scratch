# Create jobs with stable identity · 用稳定身份创建任务

> 生产者丢失了自己的确认，于是同一个报表请求到达了两次。两次投递应当指向同一个任务。

> A report request arrives twice because the producer lost its acknowledgement. Two deliveries should refer to one job.

**Type:** Build
**Languages:** Go
**Prerequisites:** Go 结构体、指针、错误处理、JSON 文件与 shell；请按顺序完成更早的阶段。
**Stage:** 第 1 / 4 阶段
**Time:** ~2 小时

## What you build · 你要构建什么

为重试赋予同一个身份。在你初始化好的工作区中实现 `stage1.go`。配套的 CLI 调用的是你的实现；它不会导入参考实现。

> Give retries one identity. Implement `stage1.go` in your initialized workspace. The supplied CLI calls your implementation; it does not import the reference solution.

## Work through the mechanism · 剖析机制

任务（job）是一份意图的持久记录。你的函数创建这条记录，但不去执行这个意图。让 `ID`、`State`、`Version`、`LeaseUntil` 和 `Attempts` 保持可见，而不是把它们压缩成一个布尔值。布尔值无法告诉你当前是否有另一个 worker 正持有这份工作。

对 `report-1`，返回 queued、version 0、attempts 0、lease 0。拒绝 `../report`、空字符串、大写开头、带空格以及超过 64 个字符的标识符。被接受的形态是：一个小写字母开头，后面跟小写字母、数字或连字符。不要把一个非法的标识符修剪成另一个合法的身份。

配套的 CLI 稍后会把 `{id,text}` 与任务状态分开存储。用相同标识符加相同文本再次入队是一次空操作（no-op）；在既有标识符下改变文本则是一次冲突。这样，生产者就可以安全地重试，而不会意外覆盖已经执行过的工作。

```figure
pj-durable-agent-jobs-1
```

> A job is the durable record of an intention. Your function creates that record without executing the intention. Keep `ID`, `State`, `Version`, `LeaseUntil` and `Attempts` visible instead of compressing them into a boolean. A boolean cannot tell you whether another worker currently owns the work.
> The accepted form is a lowercase letter followed by lowercase letters, digits or hyphens. Do not trim an invalid identifier into a different valid identity.
> Enqueueing the same identifier and identical text is a no-op; changing the text under an existing identifier is a conflict. This is how a producer can retry without accidentally replacing work that already ran.

## Your contract · 你的契约

```go
func NewJob(id string) (Job, error)
```

保持 `types.go` 中的公开签名和错误不变。被拒绝的调用必须保持调用方此前的状态。最终产物的文件与进程边界，请阅读 [the project API](../../../API.md)。

> Keep the public signature and errors in `types.go`. Rejected calls must preserve the caller's prior state. Read [the project API](../../../API.md) for the final artifact's file and process boundaries.

## Implementation hint · 实现提示

在构造 Job 之前，先检查完整的标识符。零值的 Job 状态为空，所以只在成功时才返回显式的 queued 状态。

> Check the whole identifier before constructing a Job. A zero-value Job has an empty state, so return the explicit queued state only on success.

## Verify your work · 验证你的工作

在仓库根目录执行：

```bash
python3 scripts/project_test.py durable-agent-jobs --stage 1 --path /tmp/durable-agent-jobs-work --strict
```

评分器会测试你选定的工作区，包括更早的阶段。它的 reference 模式是单独的教师检查，不能算作学习者的完成凭证。

> From the repository root:
> The grader exercises your selected workspace, including the earlier stages. Its reference mode is a separate instructor check and does not earn learner completion.

## Investigate a failure · 排查一次失败

先创建 `a`，再依次尝试 `a ` 和 `a/`。解释为什么修剪或路径清洗会让一次重试变得有歧义。只有先想清楚「格式变化是否需要新的标识符」，再给 payload 增加一个报表格式字段。

> Create `a`, then try `a ` and `a/`. Explain why trimming or path cleaning would make a retry ambiguous. Extend the payload with a report format only after deciding whether format changes require a new identifier.

## Sources and limits · 资料与边界

按需研读标准库的 [os package](https://pkg.go.dev/os)、[context](https://pkg.go.dev/context) 和 [Go pipelines guide](https://go.dev/blog/pipelines)。这些练习和示例都是原创。进程恢复只在单机上演示；README 列出了你在改造该产物时必须保留的文件系统与评测限制。

> Study the standard-library [os package](https://pkg.go.dev/os), [context](https://pkg.go.dev/context) and [Go pipelines guide](https://go.dev/blog/pipelines) as needed. These exercises and samples are original. Process recovery is demonstrated on one host; the README names the filesystem and evaluation limits you must preserve when adapting the artifact.
