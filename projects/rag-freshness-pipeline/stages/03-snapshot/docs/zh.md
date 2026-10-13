# Persist an index with atomic replacement · 用原子替换持久化索引

**4 个阶段中的第 3 个。** Python。预计约 2 小时。

在目标文件旁边写出完整的下一份快照，把它 flush（刷盘），然后原子地替换目标文件。版本前置条件（version precondition）会拒绝过期的写者（stale writer）。持久化的兄弟锁（sibling lock）用 POSIX flock 把多个本地写进程在「版本检查与替换」这一段上串行化。原子替换保护的是读者不读到半截文件，而不是防住所有分布式竞态。

```figure
pj-rag-freshness-pipeline-3
```

> Write the complete next snapshot beside the destination, flush it, then replace the destination atomically.
> A version precondition rejects stale writers.
> The persistent sibling lock uses POSIX flock to serialize local writer processes around the version check and replacement.
> Atomic replacement protects readers from partial files, not from every distributed race.

## Implementation boundary · 实现边界

```python
def read_snapshot(path):
    raise NotImplementedError("Implement the stage contract")
```

主要参考：[参考 1](https://docs.python.org/3/library/os.html#os.replace)。

## Worked Orchard case · Orchard 实战案例

在动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html) 和 [数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。先完成 [阶段 2](../../02-changes/docs/en.md)。

两个摄取进程可能同时读到 version 1。一个持久的兄弟锁把它们的版本检查和替换写串行化。恰好只有一个能以 expected_version=1 提交；下一个写者必须重新读取。

```text
writer A expects 1 -> commits version 2
writer B expects 1 -> stale index version
index.json.lock remains as the stable lock inode
```

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md). Complete [stage 2](../../02-changes/docs/en.md) first.
> Two ingestion processes can read version 1 simultaneously.
> A persistent sibling lock serializes their version checks and replacement writes.
> Exactly one may commit with expected_version=1; the next writer must reread.

## Build and inspect · 构建与检查

在 POSIX 上，从 read、compare、fsync 到 rename 全程持有 flock。释放之后绝不要 unlink 这个锁文件：否则等待中的进程可能会锁住不同的文件。

在你的学习工作区（learner workspace）里实现该阶段。这些 CLI 助手是官方提供的适配器，负责导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py rag-freshness-pipeline --stage 3 --path learning-artifacts/rag-freshness-pipeline
```

先预测上面的中间状态，再运行该阶段。全新的 stub 会失败；参考实现能跑通，并不代表你的学习工作区已经完成。

> On POSIX, hold flock across read, compare, fsync and rename.
> Never unlink the lock after release: waiting processes could then lock different files.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage.
> A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接下来探究

如果一个进程写完临时文件、却在 rename 之前退出，会发生什么？

> What happens if a process exits after writing the temporary file but before rename?
