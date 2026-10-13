# Propose rules from development errors only · 只从开发集错误中提案规则

**第 3 阶段（共 4 阶段）。** Python。预留约 2 小时。

只从开发集（development split）中的错误生成候选。一个词元（token）需要足够的重复支持和无歧义的标签；这防止一次性的名字和互相矛盾的样本立刻变成策略。候选生成永远接触不到留出集（holdout）案例。它提出的是一个变更，而不是发布一个变更。

```figure
pj-self-improving-skill-loop-3
```

> Generate candidates only from mistakes in the development split. A token needs repeated support and an unambiguous label; this stops one-off names and contradictory examples from immediately becoming policy.
> Candidate generation never receives holdout cases. It proposes a change rather than publishing one.

## Implementation boundary · 实现边界

```python
def propose(development,rules,min_support=2):
    raise NotImplementedError("Implement the stage contract")
```

主要参考：[参考 1](https://docs.python.org/3/library/hashlib.html)。

> Primary reference: [Reference 1](https://docs.python.org/3/library/hashlib.html).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html) 和 [模型评估](../../../../../phases/02-ml-fundamentals/09-model-evaluation/docs/en.md)。先完成 [阶段 2](../../02-skill/docs/en.md)。

只从开发集错误提案。invoice 出现在两个 billing 样例里，可以成为规则；一个同时被 billing 和 access 样例使用的词项是有歧义的。把留出集文本挡在这个函数之外。

```text
development: invoice wrong; invoice late -> billing
min_support=2 -> candidate terms=[invoice]
holdout: invoice missing -> used only after proposal
```

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Model evaluation](../../../../../phases/02-ml-fundamentals/09-model-evaluation/docs/en.md). Complete [stage 2](../../02-skill/docs/en.md) first.
> Propose from development errors only. Invoice appears in two billing examples and can become a rule; a term used by both billing and access examples is ambiguous. Keep the holdout text out of this function.

## Build and inspect · 构建并检查

每个案例中每个词项只计一次，并收集它关联的全部标签。提案之前，要求标签唯一且独立支持数足够。

在你的学习者工作区（learner workspace）中实现本阶段。CLI 辅助脚本是随仓库提供的适配器（adapter），它们导入你的函数；它们不能替代参考解法。

```bash
python3 scripts/project_test.py self-improving-skill-loop --stage 3 --path learning-artifacts/self-improving-skill-loop
```

先预测上方的中间状态，再运行本阶段。全新的桩（stub）会失败；参考实现跑通并不能证明你的学习者工作区已完成。

> Count each term once per case and collect all associated labels. Require a unique label and enough independent support before proposing it.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 下一步探究

如果不去重（deduplicate），同一条开发消息的多个重复副本会导致什么失败？

> What failure would repeated copies of one development message cause without deduplication?
