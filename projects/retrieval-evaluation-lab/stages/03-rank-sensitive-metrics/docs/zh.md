# Reward useful evidence near the top · 奖励排在靠前位置的有用证据

**4 个阶段中的第 3 阶段。** Python。预计约 2 小时。

Reciprocal rank（倒数排名）只使用第一条相关结果。Normalized discounted cumulative gain（NDCG，归一化折扣累计增益）则会用到每一条带等级的命中：gain 取 2^grade-1，折扣取 log2(rank+1)。把一条强结果向后换位时，即使 recall 不变，NDCG 也应当下降。

> Reciprocal rank uses only the first relevant result. Normalized discounted cumulative gain uses every graded hit, with gain 2^grade-1 and discount log2(rank+1). Swapping a strong result downward should lower NDCG even when recall is unchanged.

理想排序（ideal ranking）由全部判断按等级排序、再截断到 k 得到。理想 gain 为 0 时，NDCG 直接取 0，而不是发生除以零。

> The ideal ranking comes from all judgments sorted by grade, truncated to k. A zero ideal gain yields NDCG zero rather than division by zero.

```figure
pj-retrieval-evaluation-lab-3
```

主要参考：[主要技术参考](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html)。

## Worked Orchard case · Orchard 实例演算

动手写代码前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html)和[检索增强生成（RAG）](../../../../../phases/11-llm-engineering/06-rag/docs/en.md)，并先完成[阶段 2](../../02-precision-and-recall/docs/en.md)。

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Retrieval augmented generation](../../../../../phases/11-llm-engineering/06-rag/docs/en.md). Complete [stage 2](../../02-precision-and-recall/docs/en.md) first.

把更强的证据放在更靠前的位置。当 gain 分别为 3 和 1 时，把较弱的来源排在前面的 discounted gain 更低，即使检索到的文档集合完全没变。

> Place stronger evidence earlier. With gains 3 and 1, ranking the weaker source first reduces discounted gain even though the retrieved document set is unchanged.

```text
ranking [release,restore]: DCG=1 + 7/log2(3)=5.4165
ideal [restore,release]: DCG=7 + 1/log2(3)=7.6309
NDCG=0.7098
```

## Build and inspect · 构建与检查

gain 使用 2^relevance-1，折扣使用 log2(rank+1)。在相同 cutoff 下，用标注所能构成的最好排序来归一化。

> Use gain 2^relevance-1 and discount log2(rank+1). Normalize against the best labeled ordering at the same cutoff.

在你的 learner workspace（学习者工作区）中实现该阶段。这些 CLI 辅助脚本是由项目提供的适配器，会导入你的函数；它们不能替代参考实现（reference solution）。

> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.

```bash
python3 scripts/project_test.py retrieval-evaluation-lab --stage 3 --path learning-artifacts/retrieval-evaluation-lab
```

先预测上面的中间状态，再运行该阶段。全新的 stub 必然失败；参考实现跑通并不代表你的 learner workspace 已经完成。

> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

如果所有已标注的 gain 都是 0，NDCG 应该返回什么？

> What should NDCG return if every labeled gain is zero?
