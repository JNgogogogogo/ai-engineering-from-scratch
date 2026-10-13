# Normalize documents and fingerprint content · 规范化文档并为内容取指纹

**4 个阶段中的第 1 个。** Python。预计约 2 小时。

身份（identity）和内容是两种不同的键。保留调用方的 id，同时对规范化（normalized）后的 Unicode 内容做哈希，这样等价的编码就不会触发不必要的索引重建。时间戳仍然是元数据：修改时间戳绝不能伪装成文档内容发生了变化。

```figure
pj-rag-freshness-pipeline-1
```

> Identity and content are different keys.
> Preserve the caller id while hashing normalized Unicode content, so equivalent encodings do not trigger unnecessary indexing.
> Timestamps remain metadata: changing a timestamp must not pretend that the document content changed.

## Implementation boundary · 实现边界

```python
def normalize(doc):
    raise NotImplementedError("Implement the stage contract")
```

主要参考：[参考 1](https://docs.python.org/3/library/os.html#os.replace)。

## Worked Orchard case · Orchard 实战案例

在动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html) 和 [数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

Orchard 的策略是：超时时间变了，文档 id 保持不变。在哈希正文之前先规范化 Unicode 和换行符，并把更新时间单独保留。之后再观察到内容未变，算一次刷新（refresh），而不是重写（rewrite）。

```text
id=orchard-auth
text: tokens expire after 60 minutes
updated: 100 -> 200
content hash: unchanged
```

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md).
> The Orchard policy keeps the same document id when its timeout changes.
> Normalize Unicode and line endings before hashing the body, and retain updated time separately.
> A later observation of unchanged content is a refresh, not a rewrite.

## Build and inspect · 构建与检查

对规范化后的 UTF-8 字节做哈希。不要把时间戳哈希进内容身份里。

在你的学习工作区（learner workspace）里实现该阶段。这些 CLI 助手是官方提供的适配器，负责导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py rag-freshness-pipeline --init learning-artifacts/rag-freshness-pipeline
python3 scripts/project_test.py rag-freshness-pipeline --stage 1 --path learning-artifacts/rag-freshness-pipeline
```

先预测上面的中间状态，再运行该阶段。全新的 stub 会失败；参考实现能跑通，并不代表你的学习工作区已经完成。

> Hash normalized UTF-8 bytes. Do not hash the timestamp into content identity.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage.
> A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接下来探究

为什么 café 的两种不同编码版本应当产生同一个指纹？

> Why should two differently encoded versions of café produce the same fingerprint?
