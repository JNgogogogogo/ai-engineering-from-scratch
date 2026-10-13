# Execute and score a transparent routing skill · 执行并评分一个透明的路由技能

**第 2 阶段（共 4 阶段）。** Python。预留约 2 小时。

路由技能（routing skill）是一个由合取词项构成的有序列表：要求每个词都命中，这让多词规则比一堆独立关键词更精确；而「第一条匹配生效」的顺序本身就是契约的一部分。评估会把每个案例的预测标签和期望标签都存下来，这样聚合分数就无法掩盖谁退步了。

```figure
pj-self-improving-skill-loop-2
```

> A routing skill is an ordered list of conjunctions. Matching every term makes multiword rules more specific than a bag of independent keywords, and first-match order is part of the contract.
> Evaluation stores predicted and expected labels per case so an aggregate cannot hide who regressed.

## Implementation boundary · 实现边界

```python
def route(text,rules,default='unknown'):
    raise NotImplementedError("Implement the stage contract")
```

主要参考：[参考 1](https://docs.python.org/3/library/hashlib.html)。

> Primary reference: [Reference 1](https://docs.python.org/3/library/hashlib.html).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html) 和 [模型评估](../../../../../phases/02-ml-fundamentals/09-model-evaluation/docs/en.md)。先完成 [阶段 1](../../01-dataset/docs/en.md)。

路由技能是一份透明的有序列表。一条规则要求所有词项都出现，第一条匹配的规则获胜。在计算准确率之前，先记录每一对期望/预测，让错误能够驱动后续的提案。

```text
rule terms=[password,reset], label=access
"password reset expired" -> access
"password rejected" -> unknown
```

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Model evaluation](../../../../../phases/02-ml-fundamentals/09-model-evaluation/docs/en.md). Complete [stage 1](../../01-dataset/docs/en.md) first.
> The routing skill is a transparent ordered list. A rule requires every term, and the first matching rule wins. Record each expected/predicted pair before calculating accuracy so errors can drive a proposal.

## Build and inspect · 构建并检查

输入词只做一次规范化（normalize）。空的词项集合绝不能变成「匹配一切」的规则。

在你的学习者工作区（learner workspace）中实现本阶段。CLI 辅助脚本是随仓库提供的适配器（adapter），它们导入你的函数；它们不能替代参考解法。

```bash
python3 scripts/project_test.py self-improving-skill-loop --stage 2 --path learning-artifacts/self-improving-skill-loop
```

先预测上方的中间状态，再运行本阶段。全新的桩（stub）会失败；参考实现跑通并不能证明你的学习者工作区已完成。

> Normalize input words once. Empty term sets must never become match-everything rules.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 下一步探究

当一条宽泛的前置规则遮蔽（shadow）了后面更精确的规则时，会发生什么？

> What happens when a broad early rule shadows a more precise later rule?
