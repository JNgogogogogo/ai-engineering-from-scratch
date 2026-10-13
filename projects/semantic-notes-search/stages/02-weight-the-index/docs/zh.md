# Weight terms by document rarity · 按文档稀有度给词条加权

**第 2 阶段（共 4 阶段）。** Python。预计约 2 小时。

在每条笔记里都出现的词几乎没有区分度。按 log((1+N)/(1+df))+1 计算平滑 IDF（smoothed IDF），乘以词频（term frequency），再把每个向量归一化到单位长度。

向量和 IDF 要一起存储。查询必须使用与索引完全相同的词汇表和权重；单独为查询拟合一套 IDF 会改变坐标系，让余弦比较失效。

```figure
pj-semantic-notes-search-2
```

主要参考资料：[Primary technical reference](https://nlp.stanford.edu/IR-book/html/htmledition/the-vector-space-model-for-scoring-1.html)。

> A word that appears in every note provides little discrimination. Compute smoothed IDF as log((1+N)/(1+df))+1, multiply by term frequency, then normalize each vector to unit length.
> Store vectors and IDF together. A query must use the exact vocabulary and weights from the index; fitting query-specific IDF changes the coordinate system and invalidates cosine comparisons.
> Primary reference: [Primary technical reference](https://nlp.stanford.edu/IR-book/html/htmledition/the-vector-space-model-for-scoring-1.html).

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) 和 [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)，并先完成[第 1 阶段](../../01-normalize-notes/docs/en.md)。

稀有的运维术语比常见的项目名更能把笔记区分开。每条笔记只统计一次文档频率（document frequency），把词频乘以平滑后的稀有度，再归一化每个稀疏向量。

```text
N=3; df(orchard)=3 -> idf=1
df(restore)=1 -> idf=log(4/2)+1=1.6931
```

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md). Complete [stage 1](../../01-normalize-notes/docs/en.md) first.
> Rare operational terms separate notes better than common project names. Count document frequency once per note, multiply frequency by smoothed rarity, then normalize each sparse vector.

## Build and inspect · 构建与检查

计算文档频率时，为每个文档构建一个单词集合（set）。同一条笔记里把 orchard 重复十次，并不等于它出现在十个文档里。

请在你的学习者工作区（learner workspace）里实现本阶段。CLI 辅助工具只是随附的适配器（adapter），它们导入你的函数；不能替代参考解答。

```bash
python3 scripts/project_test.py semantic-notes-search --stage 2 --path learning-artifacts/semantic-notes-search
```

先预测上面的中间状态，再运行本阶段。全新的桩代码（stub）会失败；参考解答能跑通，并不代表你的学习者工作区已经完成。

> Build a set of words per document for document frequency. Repeating orchard ten times in one note does not make it occur in ten documents.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

在比较一条短笔记和一篇长 runbook 之前，为什么要先把向量长度归一化？

> Why normalize vector length before comparing a short note with a long runbook?
