# Rank queries with a stable tie rule · 用稳定的平局规则为查询排序

**第 3 阶段（共 4 阶段）。** Python。预计约 2 小时。

余弦相似度（cosine similarity）度量的是向量方向，所以一篇长笔记不能只靠重复自己的全部词语就胜出。忽略语料库（corpus）里从未出现过的查询词，然后在同一个加权空间里归一化。

先按分数降序排序，分数相同再按文档 id 排序。这条平局规则（tie rule）让回归测试和演示录像可以复现。只返回正向匹配；一个空列表，也比一堆不相干的零分命中更诚实。

```figure
pj-semantic-notes-search-3
```

主要参考资料：[Primary technical reference](https://nlp.stanford.edu/IR-book/html/htmledition/the-vector-space-model-for-scoring-1.html)。

> Cosine similarity measures vector direction, so a long note does not win merely by repeating all its words. Ignore query terms that never appeared in the corpus, then normalize in the same weighted space.
> Sort by descending score and then document id. This tie rule makes regression tests and demo recordings reproducible. Return only positive matches; an empty list is more honest than unrelated zero-score hits.
> Primary reference: [Primary technical reference](https://nlp.stanford.edu/IR-book/html/htmledition/the-vector-space-model-for-scoring-1.html).

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) 和 [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)，并先完成[第 2 阶段](../../02-weight-the-index/docs/en.md)。

CLI 会针对你自己的 markdown 文件夹返回路径、预览和匹配到的词条。查询向量和笔记向量使用同一份别名映射（alias map）和同一张 IDF 表；未知词条不贡献任何权重。

```text
query=release replicas
alias release=deploy
matching note: release.md; matched terms: deploy
```

提供的笔记里是单数 `replica`，所以复数 `replicas` 匹配不上。这个词法分词器（lexical tokenizer）不做词干还原（stemming）。可编辑图形的起始状态是一篇更短的笔记，里面含字面短语 `deploy replicas`，所以它的两词匹配对应的是另一份输入。

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md). Complete [stage 2](../../02-weight-the-index/docs/en.md) first.
> The CLI returns paths, previews and matching tokens for your own markdown folder. Query and note vectors use the same alias map and IDF table; unknown terms contribute no weight.
> The supplied note contains singular `replica`, so plural `replicas` does not match. This lexical tokenizer does not stem words. The editable figure starts with a shorter note containing the literal phrase `deploy replicas`, so its two-term match is a different input.

## Build and inspect · 构建与检查

用索引的 IDF 计算查询向量，再对各笔记向量做点积（dot product）。分数相同时按文档 id 决出先后。

请在你的学习者工作区（learner workspace）里实现本阶段。CLI 辅助工具只是随附的适配器（adapter），它们导入你的函数；不能替代参考解答。

```bash
python3 scripts/project_test.py semantic-notes-search --stage 3 --path learning-artifacts/semantic-notes-search
```

先预测上面的中间状态，再运行本阶段。全新的桩代码（stub）会失败；参考解答能跑通，并不代表你的学习者工作区已经完成。

> Compute the query vector using index IDF, then dot products against note vectors. Break equal scores by document id.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

如果笔记用到的同义词不在别名映射表里，空结果意味着什么？

> What does an empty result mean if the note uses a synonym absent from the alias map?
