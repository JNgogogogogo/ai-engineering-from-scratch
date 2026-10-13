# Compute precision and recall at k · 计算 k 处的 precision 与 recall

**4 个阶段中的第 2 阶段。** Python。预计约 2 小时。

Precision 回答的是：展示出来的列表里有几成是有用的。Recall 回答的是：所有已知相关证据中有多少被检索了出来。这两个指标的分母来源不同。

> Precision answers how much of the displayed list was useful. Recall answers how much of all known relevant evidence was retrieved. These denominators are different.

即使系统返回的结果不足 k 条，也用 k 作为 precision 的分母。这样对「没填满」的结果列表施加的惩罚才保持一致。把无相关标注时的 recall 定义为 0，并同时报告判断（judgment）的数量。

> Use k as the precision denominator, even when a system returns fewer than k results. This penalizes underfilled result lists consistently. Define empty-relevance recall as zero and report the judgment count.

```figure
pj-retrieval-evaluation-lab-2
```

主要参考：[主要技术参考](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html)。

## Worked Orchard case · Orchard 实例演算

动手写代码前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html)和[检索增强生成（RAG）](../../../../../phases/11-llm-engineering/06-rag/docs/en.md)，并先完成[阶段 1](../../01-validate-rankings/docs/en.md)。

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Retrieval augmented generation](../../../../../phases/11-llm-engineering/06-rag/docs/en.md). Complete [stage 1](../../01-validate-rankings/docs/en.md) first.

在 k=2 时，检索到一篇相关笔记和一篇无关笔记，precision 为 1/2。如果标注里共有两篇相关笔记，recall 也是 1/2。但每个指标的分母来自不同的地方。

> At k=2, retrieving one relevant note and one irrelevant note gives precision 1/2. If the labels contain two relevant notes, recall is also 1/2. The denominator comes from a different place in each metric.

```text
ranking[:2]=[restore,cafe]
relevant labels={restore,release}
precision=1/2; recall=1/2
```

## Build and inspect · 构建与检查

把相关性为正的标注都算作相关，而不是只看 judgment 映射里是否存在这个键。即使返回的结果少于 cutoff，也保持给定的 cutoff 不变。

> Count positive relevance labels as relevant, not merely keys in the judgment map. Keep the supplied cutoff even when fewer results are returned.

在你的 learner workspace（学习者工作区）中实现该阶段。这些 CLI 辅助脚本是由项目提供的适配器，会导入你的函数；它们不能替代参考实现（reference solution）。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py retrieval-evaluation-lab --stage 2 --path learning-artifacts/retrieval-evaluation-lab
```

先预测上面的中间状态，再运行该阶段。全新的 stub 必然失败；参考实现跑通并不代表你的 learner workspace 已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

为什么增大 k 可能在提升 recall 的同时降低 precision？

> Why can increasing k improve recall while lowering precision?
