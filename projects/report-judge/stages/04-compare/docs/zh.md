# Compare paired revisions with bootstrap intervals · 用 bootstrap 区间比较成对修订

**第 4 阶段（共 4 阶段）。** Python。预计约 2 小时。

先按问题 id 把分数配对，再对差值做重采样（resample）。配对控制了「有些问题更难」这一因素。该区间只是对给定数据划分的一种描述；数据集很小，并不会因为你抽了很多次 bootstrap 样本就变得可靠。晋升（promotion）还会拒绝任何单题回归。

```figure
pj-report-judge-4
```

> Pair scores by question id, then resample the differences. Pairing controls for the fact that some questions are harder. The interval is descriptive for the supplied split; a tiny dataset does not become reliable because you draw many bootstrap samples. Promotion also rejects any per-question regression.

## Implementation boundary · 实现边界

```python
def compare(baseline,candidate,seed=7,samples=2000):
    raise NotImplementedError("Implement the stage contract")
```

主要参考：[Reference 1](https://www.rfc-editor.org/rfc/rfc8259)。

> Primary reference: [Reference 1](https://www.rfc-editor.org/rfc/rfc8259).

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html)和[检索增强生成](../../../../../phases/11-llm-engineering/06-rag/docs/en.md)。先完成[阶段 3](../../03-metrics/docs/en.md)。

比较报告改动前后相同的问题。简单题上的提升可能掩盖一个致命的回归；把每题的差值与 bootstrap 区间并排保留。

```text
baseline: q1=80,q2=70,q3=90
candidate: q1=85,q2=75,q3=60
deltas: +5,+5,-30; q3 remains a regression
```

> Compare the same questions before and after a report change. A gain on easy questions can hide one damaging regression; preserve per-question deltas beside the bootstrap interval.

## Build and inspect · 构建并检查

用一个确定的种子重采样成对差值。该区间描述的是这个已标注样本，而不是对未来每份报告的事实准确性。

在你的学习工作区（learner workspace）中实现该阶段。这些 CLI 辅助工具是给定的适配器，它们导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py report-judge --stage 4 --path learning-artifacts/report-judge
```

在各阶段累计通过之后，从仓库根目录用最初的示例输入运行你的工件（artifact）：

```bash
python3 learning-artifacts/report-judge/cli.py projects/report-judge/examples/claims.json --out evidence-audit.json --html evidence-audit.html
```

这个 judge 提供保守的词面证据检查。语序、数字和否定能暴露一部分假匹配；改写仍可能被误拒，其他假匹配也仍然存在。缺失的 recall/coverage 标注为 null。任何自动化分数都不能证明真值。

> Resample paired deltas with a deterministic seed. The interval describes this labeled sample, not factual accuracy on every future report.
> The judge provides conservative lexical evidence checks. Order, numbers and negation expose some false matches; paraphrases can still be rejected and other false matches remain. Missing recall/coverage labels are null. No automated score proves truth.

## Investigate next · 下一步探究

给 q1 添加一份第二副本，能制造出独立证据吗？

> Would adding a second copy of q1 create independent evidence?
