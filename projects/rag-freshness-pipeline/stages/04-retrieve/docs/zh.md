# Exclude expired evidence at query time · 在查询时排除过期证据

**4 个阶段中的第 4 个。** Python。预计约 2 小时。

新鲜度（freshness）既是查询时的契约，也是摄取环节要关心的事。后台任务可能失败，所以每个候选都必须在排序（ranking）之前满足时限要求。测试中要注入时钟（inject the clock），而不是直接调用系统时钟；对未来时间戳要拒绝，而不是把它们当成「格外新鲜」。

```figure
pj-rag-freshness-pipeline-4
```

> Freshness is a query-time contract as well as an ingestion concern.
> A background job can fail, so every candidate must satisfy the age limit before ranking.
> Inject the clock instead of calling the system clock inside tests, and reject future timestamps rather than treating them as extra fresh.

## Implementation boundary · 实现边界

```python
def retrieve(documents,query,now,max_age=3600,k=3):
    raise NotImplementedError("Implement the stage contract")
```

主要参考：[参考 1](https://docs.python.org/3/library/os.html#os.replace)。

## Worked Orchard case · Orchard 实战案例

在动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html) 和 [数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。先完成 [阶段 3](../../03-snapshot/docs/en.md)。

这次编辑之后，查询必须返回 15 分钟那条策略，而绝不返回已退役的 60 分钟文本。新鲜度是在回答问题时强制执行的，哪怕自上一份快照以来没有任何摄取任务运行过。

```text
updated=200; now=210; max_age=60 -> age 10, eligible
updated=200; now=500; max_age=60 -> age 300, excluded
```

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md). Complete [stage 3](../../03-snapshot/docs/en.md) first.
> After the edit, a query must return the 15-minute policy and never the retired 60-minute text.
> Freshness is enforced when answering, even if no ingestion job has run since the last snapshot.

## Build and inspect · 构建与检查

为这次查询读取一份已提交的快照。每一条命中都返回它的 version 和 source hash，让调用方能察觉过期的引用（stale citation）。

在你的学习工作区（learner workspace）里实现该阶段。这些 CLI 助手是官方提供的适配器，负责导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py rag-freshness-pipeline --stage 4 --path learning-artifacts/rag-freshness-pipeline
```

在各阶段累计通过之后，从仓库根目录用原始示例输入运行你的产物：

```bash
python3 learning-artifacts/rag-freshness-pipeline/cli.py ingest orchard-index.json projects/rag-freshness-pipeline/examples/before.json
python3 learning-artifacts/rag-freshness-pipeline/cli.py ingest orchard-index.json projects/rag-freshness-pipeline/examples/after.json
python3 learning-artifacts/rag-freshness-pipeline/cli.py query orchard-index.json tokens --now 210 --max-age 60
```

importer 期望的是完整语料，而不是部分变更流。POSIX flock 协调的是本地写者；它不是分布式数据库锁。检索是词法（lexical）的，source 时间戳由调用方提供。

> Read one committed snapshot for the query.
> Return its version and the source hash with each hit so callers can detect stale citations.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage.
> A fresh stub fails; a passing reference run does not establish completion of your learner workspace.
> After the cumulative stages pass, run your artifact on the original sample input from the repository root:
> The importer expects the complete corpus, not a partial change feed.
> POSIX flock coordinates local writers; it is not a distributed database lock.
> Retrieval is lexical and source timestamps are caller supplied.

## Investigate next · 接下来探究

一份日期标在未来（future-dated）的文档，应该得到负的 age 并成为最佳结果吗？

> Should a future-dated document receive a negative age and become the best result?
