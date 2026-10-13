# Compare systems query by query · 逐查询对比系统

**4 个阶段中的第 4 阶段。** Python。预计约 2 小时。

宏平均（macro averaging）给每个查询相同的权重，防止一个拥有数百条判断的查询主导整个基准。在均值之外保留逐查询（per-query）指标，让回归（regression）始终可见。

> Macro averaging gives each query equal weight, preventing a query with hundreds of judgments from dominating the benchmark. Retain per-query metrics alongside the mean so regressions remain visible.

要求所有被判定过的查询都出现在每个系统中，检索失败时也要显式地给出空排序。悄悄丢掉难查询会让平均值变好，却没有让检索变好。

> Require all judged queries to appear in every system, including an explicit empty ranking when retrieval fails. Silently dropping hard queries would improve the average without improving retrieval.

```figure
pj-retrieval-evaluation-lab-4
```

主要参考：[主要技术参考](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html)。

## Worked Orchard case · Orchard 实例演算

动手写代码前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html)和[检索增强生成（RAG）](../../../../../phases/11-llm-engineering/06-rag/docs/en.md)，并先完成[阶段 3](../../03-rank-sensitive-metrics/docs/en.md)。

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Retrieval augmented generation](../../../../../phases/11-llm-engineering/06-rag/docs/en.md). Complete [stage 3](../../03-rank-sensitive-metrics/docs/en.md) first.

自带的这个三查询 fixture 中，release 和 café 的检索变好了，但 restore 的检索变差了。对查询级的 delta 排序，让丢失的恢复证据出现在聚合数字之前。

> The supplied three-query fixture improves release and café retrieval while making restore retrieval worse. Sort query-level deltas so the lost recovery evidence appears before the aggregate.

```text
release: improved
cafe: improved
restore: regressed
--fail-on-regression -> exit 1
```

## Build and inspect · 构建与检查

以判断（judgment）的查询 id 为准对齐各个系统。每个 delta 都要保存 before/after 的排序 id；光有一个数字认不出被移动的是哪个来源。

> Align systems on the judgment query ids. Save before/after ranked ids with each delta; a number alone does not identify the moved source.

在你的 learner workspace（学习者工作区）中实现该阶段。这些 CLI 辅助脚本是由项目提供的适配器，会导入你的函数；它们不能替代参考实现（reference solution）。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py retrieval-evaluation-lab --stage 4 --path learning-artifacts/retrieval-evaluation-lab
```

所有累积阶段通过后，在仓库根目录用原始示例输入运行你的产物：

> After the cumulative stages pass, run your artifact on the original sample input from the repository root:

```bash
python3 learning-artifacts/retrieval-evaluation-lab/cli.py projects/retrieval-evaluation-lab/examples/baseline.json projects/retrieval-evaluation-lab/examples/candidate.json projects/retrieval-evaluation-lab/examples/judgments.json --out retrieval-diff.json
```

指标只作用于提供的标注。未判定的文档 gain 记为 0，并且继续按未判定统计。使用 --fail-on-regression，任何查询只要 NDCG 更低就返回 exit 1。

> Metrics apply to supplied labels. Unjudged documents receive zero gain and remain counted as unjudged. Use --fail-on-regression to return exit 1 for any query with lower NDCG.

## Investigate next · 接着探究

如果平均 NDCG 上升了，哪个查询最值得先复查？

> Which query deserves review first if average NDCG rises?
