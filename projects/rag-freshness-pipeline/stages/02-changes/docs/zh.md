# Plan inserts updates deletions and refreshes · 规划插入、更新、删除与刷新

**4 个阶段中的第 2 个。** Python。预计约 2 小时。

在改动索引之前，先把整个计划完整算出来。缺失的 id 是删除（deletion），哈希变化是更新（update），内容未变而元数据变化是刷新（refresh）。重复 id 要当作错误处理，因为悄悄保留其中一个会让摄取（ingestion）结果取决于输入顺序。

```figure
pj-rag-freshness-pipeline-2
```

> Compute the whole plan before changing the index.
> A missing id is a deletion, a changed hash is an update, and unchanged content with new metadata is a refresh.
> Treat duplicate ids as an error because silently keeping one would make ingestion depend on input order.

## Implementation boundary · 实现边界

```python
def diff(previous,incoming):
    raise NotImplementedError("Implement the stage contract")
```

主要参考：[参考 1](https://docs.python.org/3/library/os.html#os.replace)。

## Worked Orchard case · Orchard 实战案例

在动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html) 和 [数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。先完成 [阶段 1](../../01-fingerprint/docs/en.md)。

摄取收到的是一份完整的语料快照。after fixture 换掉了一条已退役的备份笔记，并修改了 token 有效期。缺失的 id 必须删除，这样过期的证据就不会继续可搜。

```text
before ids: orchard-auth, retired-backup
after ids: orchard-auth, restore-runbook
update: orchard-auth; delete: retired-backup; insert: restore-runbook
```

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md). Complete [stage 1](../../01-fingerprint/docs/en.md) first.
> Ingestion receives a complete corpus snapshot.
> The after fixture replaces a retired backup note and edits the token lifetime.
> Missing ids must be deleted so obsolete evidence cannot remain searchable.

## Build and inspect · 构建与检查

在决定任何操作之前，先构建 incoming id 的映射。重复的 incoming id 是错误，而不是「后写者胜」（last-write-wins）。

在你的学习工作区（learner workspace）里实现该阶段。这些 CLI 助手是官方提供的适配器，负责导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py rag-freshness-pipeline --stage 2 --path learning-artifacts/rag-freshness-pipeline
```

先预测上面的中间状态，再运行该阶段。全新的 stub 会失败；参考实现能跑通，并不代表你的学习工作区已经完成。

> Build the incoming id map before deciding any operation.
> A duplicate incoming id is an error, not last-write-wins.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage.
> A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接下来探究

如果 importer 收到的只是一份部分变更流（change feed），这个契约要怎么改？

> How would the contract change if the importer received only a partial change feed?
