# Check evidence before averaging scores · 先核查证据，再平均分数

**第 2 阶段（共 4 阶段）。** Python。预计约 2 小时。

在计算重叠度之前，先把缺失证据当作一票否决的失败处理。数字与否定检查能抓住那些仅靠词面重叠反而会奖励矛盾论断的情况。重叠分数是一个可检查的启发式（heuristic）；它不是真值探测器，而且会误拒好的改写（paraphrase）。

```figure
pj-report-judge-2
```

> Treat missing evidence as a categorical failure before calculating overlap. Number and negation checks catch cases where word overlap would otherwise reward a contradictory claim. The overlap score is an inspectable heuristic; it is not a truth detector and can reject good paraphrases.

## Implementation boundary · 实现边界

```python
def support(claim, source):
    raise NotImplementedError("Implement the stage contract")
```

主要参考：[Reference 1](https://www.rfc-editor.org/rfc/rfc8259)。

> Primary reference: [Reference 1](https://www.rfc-editor.org/rfc/rfc8259).

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html)和[检索增强生成](../../../../../phases/11-llm-engineering/06-rag/docs/en.md)。先完成[阶段 1](../../01-claims/docs/en.md)。

词面重叠会漏掉关系。论断 "Bob defeated Alice" 与 "Alice defeated Bob" 共享全部单词，却颠倒了谁做了什么。把这种语序不匹配拒绝并转人工审核；不要把这个检查标榜为语义理解。

```text
source: Alice defeated Bob
claim: Bob defeated Alice
word overlap=1; order check=false
result: order_requires_review
```

> Word overlap misses relationships. The claim "Bob defeated Alice" shares every word with "Alice defeated Bob" but reverses who did what. Reject the ordering mismatch for human review; do not label this check semantic understanding.

## Build and inspect · 构建并检查

只有在否定与数字守卫（guard）之后，才比较有序的内容词。这条保守规则可能误拒有效的改写，所以要让拒绝原因保持可见。

在你的学习工作区（learner workspace）中实现该阶段。这些 CLI 辅助工具是给定的适配器，它们导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py report-judge --stage 2 --path learning-artifacts/report-judge
```

先预测上面的中间状态，再运行该阶段。全新的 stub 会失败；参考实现跑通并不代表你的学习工作区已经完成。

> Compare ordered content tokens only after the negation and numeric guards. This conservative rule can reject valid paraphrases, so keep the reason visible.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 下一步探究

写出一条真实的改写句子，让你的词面规则去拒绝它。一个人需要什么证据才能裁定它？

> Write one true paraphrase that your lexical rule rejects. What evidence would a human need to resolve it?
