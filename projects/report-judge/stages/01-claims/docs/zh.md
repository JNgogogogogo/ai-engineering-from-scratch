# Parse claims and citation references · 解析论断与引用标记

**第 1 阶段（共 4 阶段）。** Python。预计约 2 小时。

引用解析器（citation parser）负责识别引用，但不判断它们是否为真。在每个句子内部对标记（marker）去重，保留论断（claim）文本，并忽略 markdown 标题。这套刻意收窄的文法按「一行一个段落」处理；它不会假装能解析任意 markdown 或缩写。

```figure
pj-report-judge-1
```

> A citation parser identifies references without deciding whether they are true. Deduplicate markers within each sentence, preserve the claim text, and ignore markdown headings. This deliberately narrow grammar handles one paragraph per line; it does not pretend to parse arbitrary markdown or abbreviations.

## Implementation boundary · 实现边界

```python
def parse_claims(text):
    raise NotImplementedError("Implement the stage contract")
```

主要参考：[Reference 1](https://www.rfc-editor.org/rfc/rfc8259)。

> Primary reference: [Reference 1](https://www.rfc-editor.org/rfc/rfc8259).

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html)和[检索增强生成](../../../../../phases/11-llm-engineering/06-rag/docs/en.md)。

逐条单独审计每个事实性句子。Orchard 有一个带来源的重试上限和一个无关的部署论断；一个有效标记不能让整段直接通过。

```text
Worker A invokes worker B [S1]. Retry limit is 99 [S2].
claim 1 -> cites [S1]
claim 2 -> cites [S2]
```

> Audit each factual sentence separately. Orchard has a sourced retry limit and an unrelated deployment claim; one valid marker must not make the whole paragraph pass.

## Build and inspect · 构建并检查

先把标记提取出来，再把它们从论断文本中移除。对重复的标记去重，但不丢掉句子身份。

在你的学习工作区（learner workspace）中实现该阶段。这些 CLI 辅助工具是给定的适配器，它们导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py report-judge --init learning-artifacts/report-judge
python3 scripts/project_test.py report-judge --stage 1 --path learning-artifacts/report-judge
```

先预测上面的中间状态，再运行该阶段。全新的 stub 会失败；参考实现跑通并不代表你的学习工作区已经完成。

> Extract markers before removing them from the claim text. Deduplicate repeated markers without discarding sentence identity.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 下一步探究

当 [S2] 不在证据映射（evidence map）里时，应该发生什么？

> What should happen when [S2] is absent from the evidence map?
