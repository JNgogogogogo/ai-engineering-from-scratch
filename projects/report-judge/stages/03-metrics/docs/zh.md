# Report precision coverage and source recall · 报告精度、覆盖率与来源召回

**第 3 阶段（共 4 阶段）。** Python。预计约 2 小时。

在合并之前先把各指标分开。precision（精度）衡量已发布内容的支撑情况，source recall（来源召回）衡量预期证据的选取情况，fact coverage（事实覆盖）衡量关键短语是否出现。空报告的 precision 为零，从而防止「弃权」看起来完美无缺。

```figure
pj-report-judge-3
```

> Keep metrics separate before combining them. Precision measures published support, source recall measures expected evidence selection, and fact coverage measures whether key phrases appear. An empty report has zero precision, preventing abstention from looking perfectly accurate.

## Implementation boundary · 实现边界

```python
def score_report(text,evidence,expected_sources=(),facts=()):
    raise NotImplementedError("Implement the stage contract")
```

主要参考：[Reference 1](https://www.rfc-editor.org/rfc/rfc8259)。

> Primary reference: [Reference 1](https://www.rfc-editor.org/rfc/rfc8259).

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html)和[检索增强生成](../../../../../phases/11-llm-engineering/06-rag/docs/en.md)。先完成[阶段 2](../../02-support/docs/en.md)。

空报告没有证据，得分为零。recall 和 fact coverage 需要标注（label）；没有标注时它们是「不可用」，而不是自动满分。只有被支撑的论断才计入 source recall 或 coverage。

```text
empty claims -> score 0, state no_evidence
3 lexical matches, no reference labels -> recall null, coverage null
score is computed only from available metrics
```

> An empty report has no evidence and scores zero. Recall and fact coverage require labels; without labels they are unavailable, rather than automatically perfect. Only supported claims earn source recall or coverage.

## Build and inspect · 构建并检查

只跟踪一次被支撑的论断，然后从这一个集合推导所有与「被支撑证据」相关的指标。不要让悬空引用（dangling citation）抬高 source recall。

在你的学习工作区（learner workspace）中实现该阶段。这些 CLI 辅助工具是给定的适配器，它们导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py report-judge --stage 3 --path learning-artifacts/report-judge
```

先预测上面的中间状态，再运行该阶段。全新的 stub 会失败；参考实现跑通并不代表你的学习工作区已经完成。

> Track supported claims once and derive all supported-evidence metrics from that collection. Do not let a dangling citation inflate source recall.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 下一步探究

为什么词面匹配拿到 100 分的同时，recall 还可以不可用？

> Why can a 100 lexical-match score coexist with unavailable recall?
