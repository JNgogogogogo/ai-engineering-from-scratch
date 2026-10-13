# Partition stable case identities · 划分稳定的 case 身份

> 一次重启后的评估，应该在任何 worker 启动之前就知道每个 shard 里有哪些 case。
>
> A restarted evaluation should know which cases belong to each shard before any worker starts.

**Type:** Build
**Languages:** Go
**Prerequisites:** 会用 Go 的 struct、指针、error、JSON 文件和 shell；按顺序完成更早的阶段。
**Stage:** 1 of 4
**Time:** ~2 hours

## What you build · 你要构建什么

让数据集的放置（placement）可复现。在你初始化好的工作区里实现 `stage1.go`。配套的 CLI 调用的是你的实现；它不会 import 参考答案。

> Make dataset placement reproducible. Implement `stage1.go` in your initialized workspace. The supplied CLI calls your implementation; it does not import the reference solution.

## Work through the mechanism · 剖析机制

划分（partitioning）就是把标识符（identifier）分配进桶（bucket）。FNV-1a32 哈希从 2166136261 起始，对每个 UTF-8 字节做 XOR，再乘以 16777619，按 32 位回绕。哈希对 shard 数取模。Go 的 `hash/fnv` 已经实现了这个原语；学习点在于围绕它定义并测试「身份契约」。

4 个 shard 时，样例标识符的落位是 case-d 进 0、case-c 进 1、case-b 进 2、case-a 进 3。打乱输入顺序只会改变每个桶内部的局部顺序，绝不会改变某个标识符所在的桶。不要断言每个桶大小相等：确定性分配不是负载均衡保证。

拒绝空标识符、重复标识符，以及不在 1..1024 范围内的 shard 数。配套的持久化存储还会对有序的输入记录（包括 prompt、期望答案和录制的响应）做指纹。预测或 shard 数一变，就需要另一个存储。否则恢复运行时可能在保留同一个表面数据集名的同时，把两次实验的结果混在一起。

空分区不需要 lease，也不会出现在存储的活跃 shard 列表里。覆盖率仍然按真实的 case 计数。一条记录、四个桶的样例只有一个活跃 shard，而不是四个人造的已完成任务。

```figure
pj-distributed-eval-farm-1
```

> Partitioning assigns identifiers to buckets. Start the FNV-1a32 hash at 2166136261, XOR each UTF-8 byte and multiply by 16777619 with 32-bit wraparound. Take hash modulo shard count. Go's `hash/fnv` implements this primitive; the learning work is defining and testing the identity contract around it.
> With four shards, the sample identifiers land as case-d in 0, case-c in 1, case-b in 2 and case-a in 3. Reordering the input changes each bucket's local order but never an identifier's bucket. Do not assert that every bucket has equal size: deterministic assignment is not a load-balancing guarantee.
> Reject empty identifiers, duplicates and shard counts outside 1..1024. ... A changed prediction or shard count needs a different store.
> Empty partitions need no lease and are omitted from the stored active shard list. Coverage still counts every actual case.

## Your contract · 你的契约

```go
func Partition(ids []string, shards int) ([][]string, error)
```

公开签名和错误类型保持在 `types.go` 里。被拒绝的调用必须保留调用方此前的状态。最终产物的文件与进程边界参见[项目 API](../../../API.md)。

> Keep the public signature and errors in `types.go`. Rejected calls must preserve the caller's prior state. Read [the project API](../../../API.md) for the final artifact's file and process boundaries.

## Implementation hint · 实现提示

先把所有请求的桶分配出来，追踪已见过的标识符，对字节做哈希，并恰好追加进一个桶。保持 ID 原样；做归一化（normalization）会把不同的 case 合并掉。

> Allocate all requested buckets first, track seen identifiers, hash bytes and append to exactly one bucket. Keep IDs intact; normalization can merge distinct cases.

## Verify your work · 验证你的实现

在仓库根目录：

```bash
python3 scripts/project_test.py distributed-eval-farm --stage 1 --path /tmp/distributed-eval-farm-work --strict
```

评分器会操练你选定的工作区，包括更早的阶段。它的 reference 模式是单独的教师检查，不计为学习者的完成。

> From the repository root:
> The grader exercises your selected workspace, including the earlier stages. Its reference mode is a separate instructor check and does not earn learner completion.

## Investigate a failure · 探查一个失败

把样例分别划成 4 个和 3 个桶。哪些 case ID 移动了？解释为什么只改 prompt 也会改变运行指纹（run fingerprint），即使它的 shard 分配保持不变。

> Partition the sample into 4 and 3 buckets. Which case IDs move? Explain why changing only a prompt also changes the run fingerprint even though its shard assignment remains stable.

## Sources and limits · 资料与边界

按需研读标准库的 [os package](https://pkg.go.dev/os)、[context](https://pkg.go.dev/context) 和 [Go pipelines 指南](https://go.dev/blog/pipelines)。这些练习和样例都是原创。进程恢复只在单机上演示；README 说明了改造该产物时必须保留的文件系统与评估限制。

> Study the standard-library [os package](https://pkg.go.dev/os), [context](https://pkg.go.dev/context) and [Go pipelines guide](https://go.dev/blog/pipelines) as needed. These exercises and samples are original. Process recovery is demonstrated on one host; the README names the filesystem and evaluation limits you must preserve when adapting the artifact.
