# Validate rankings and graded judgments · 校验排序与分级相关性判断

**4 个阶段中的第 1 阶段。** Python。预计约 2 小时。

评估默认一篇文档在排序（ranking）中只出现一次。如果同一篇相关文档被重复列出，朴素的 precision 和 gain 会把它统计多次。在动手度量之前，先校验排序中的 id 和相关性等级（relevance grade）。

> Evaluation assumes a document appears once in a ranking. If the same relevant document is repeated, naive precision and gain can count it many times. Validate ranking ids and relevance grades before measuring anything.

等级使用 0 到 3 的整数。缺失的文档按未判定（unjudged）处理、gain 记为 0，但最终报告仍会统计它们的数量，让不完整的标注保持可见。

> Grades use integers from zero to three. Missing documents are treated as unjudged and receive zero gain, but the final report also counts them so incomplete labeling remains visible.

```figure
pj-retrieval-evaluation-lab-1
```

主要参考：[主要技术参考](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html)。

## Worked Orchard case · Orchard 实例演算

动手写代码前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html)和[检索增强生成（RAG）](../../../../../phases/11-llm-engineering/06-rag/docs/en.md)。

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Retrieval augmented generation](../../../../../phases/11-llm-engineering/06-rag/docs/en.md).

排序（ranking）是由唯一文档 id 组成的有序列表。Orchard 的 restore 查询带有分级证据：一份恢复流程文档，比 release notes 里一笔带过的提及有用得多。

> A ranking is an ordered list of unique document ids. The Orchard restore query has graded evidence: a recovery procedure is more useful than a passing mention in release notes.

```text
judgments: restore=3, release=1, cafe=0
ranking: [release, restore, restore] -> duplicate error
```

## Build and inspect · 构建与检查

打分之前先校验排序和相关性判断。让未判定（unjudged）的文档保持可见，而不是默认它们已被审阅过、只是碰巧无关。

> Validate rankings and judgments before scoring. Keep unjudged documents visible instead of assuming they were reviewed and found irrelevant.

在你的 learner workspace（学习者工作区）中实现该阶段。这些 CLI 辅助脚本是由项目提供的适配器，会导入你的函数；它们不能替代参考实现（reference solution）。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py retrieval-evaluation-lab --init learning-artifacts/retrieval-evaluation-lab
python3 scripts/project_test.py retrieval-evaluation-lab --stage 1 --path learning-artifacts/retrieval-evaluation-lab
```

先预测上面的中间状态，再运行该阶段。全新的 stub 必然失败；参考实现跑通并不代表你的 learner workspace 已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

当你的语料库刚新增一篇笔记时，一条「缺失的判断」意味着什么？

> What does a missing judgment mean when your corpus has just gained a new note?
