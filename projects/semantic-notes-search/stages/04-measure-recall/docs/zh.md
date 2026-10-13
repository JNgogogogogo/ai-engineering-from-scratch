# Measure retrieval before adding embeddings · 在引入嵌入之前先度量检索

**第 4 阶段（共 4 阶段）。** Python。预计约 2 小时。

检索演示需要一个与任务挂钩的分数。对每个带标注的查询（labeled query），度量期望的文档是否出现在前 k 个结果里。对这些相互独立的命中取平均，就得到 recall@k（k 处召回率）。

这份带标注的小型测试集（fixture）是公开且确定性的。在这里拿满分并不能证明它对新笔记的质量。在判断同义词扩展是否够用之前，先单独保留一套你自己的改述（paraphrase）测试集。

```figure
pj-semantic-notes-search-4
```

主要参考资料：[Primary technical reference](https://nlp.stanford.edu/IR-book/html/htmledition/the-vector-space-model-for-scoring-1.html)。

> A retrieval demo needs a score tied to a task. For each labeled query, measure whether the expected document appears in the first k results. Average these independent hits for recall at k.
> This tiny labeled fixture is public and deterministic. A perfect score here cannot establish quality on new notes. Keep a separate set of your own paraphrases before deciding whether synonym expansion is sufficient.
> Primary reference: [Primary technical reference](https://nlp.stanford.edu/IR-book/html/htmledition/the-vector-space-model-for-scoring-1.html).

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) 和 [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)，并先完成[第 3 阶段](../../03-rank-queries/docs/en.md)。

在换上另一个检索后端（retrieval backend）之前，先度量目标笔记是否出现在靠前的位置。提供的笔记覆盖部署（deployment）、恢复（restore）和访客 Wi-Fi，所以一个别名可能帮了一个主题，却害了另一个。

```text
labels: restore -> backup.md; café -> café.md
hits=2,total=2,k=1 -> recall=1
add a misleading alias -> inspect changed hit ids
```

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md). Complete [stage 3](../../03-rank-queries/docs/en.md) first.
> Measure whether the intended note appears near the top before adding a different retrieval backend. The supplied notes span deployment, restore and guest Wi-Fi so an alias can help one topic while harming another.

## Build and inspect · 构建与检查

带标注的查询要与调参示例分开保管。评估时直接调用真正的搜索函数，而不是另外重造一个评分器（scorer）。

请在你的学习者工作区（learner workspace）里实现本阶段。CLI 辅助工具只是随附的适配器（adapter），它们导入你的函数；不能替代参考解答。

```bash
python3 scripts/project_test.py semantic-notes-search --stage 4 --path learning-artifacts/semantic-notes-search
```

所有累计阶段都通过后，从仓库根目录用原始示例输入运行你的产物（artifact）：

```bash
python3 learning-artifacts/semantic-notes-search/cli.py projects/semantic-notes-search/examples/notes "release replicas" --aliases projects/semantic-notes-search/examples/aliases.json --out matches.json
```

这是一个带显式别名、可解释的词法 TF-IDF 基线（baseline），不是训练出来的嵌入模型。标题保留了项目路线（project route）；每个匹配都会展示它的词法词条。文件夹读取器只接受有大小上限的 UTF-8 markdown，并拒绝符号链接（symlink）文件。

> Keep labeled queries outside the tuning examples. Call the actual search function inside evaluation instead of reconstructing a separate scorer.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> After the cumulative stages pass, run your artifact on the original sample input from the repository root:
> This is an explainable lexical TF-IDF baseline with explicit aliases, not a learned embedding model. The title preserves the project route; every match exposes its lexical terms. The folder reader accepts bounded UTF-8 markdown and rejects symlink files.

## Investigate next · 接着探究

在宣称初学者的检索体验有所改进之前，你会再收集多少条新标注？

> How many new labels would you collect before claiming improved retrieval for beginners?
