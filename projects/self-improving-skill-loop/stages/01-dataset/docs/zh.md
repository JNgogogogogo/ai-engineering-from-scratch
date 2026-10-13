# Split labeled cases without identity leakage · 切分带标注案例且不泄露身份

**第 1 阶段（共 4 阶段）。** Python。预留约 2 小时。

对每个稳定的案例 id 做哈希（hash），选出与文件顺序无关的分区（partition）。重复的身份会在评估开始前被拒绝。这个切分是确定性的，但并不保证标签数量完美均衡；在提出规则之前，先检查两个分区并预留出评估分区。

```figure
pj-self-improving-skill-loop-1
```

> Hash each stable case id to choose a partition independent of file order. A duplicate identity is rejected before evaluation.
> The split is deterministic, but it does not promise perfectly balanced label counts; inspect both partitions and reserve the evaluation partition before proposing rules.

## Implementation boundary · 实现边界

```python
def split_cases(cases,holdout_fraction=.25):
    raise NotImplementedError("Implement the stage contract")
```

主要参考：[参考 1](https://docs.python.org/3/library/hashlib.html)。

> Primary reference: [Reference 1](https://docs.python.org/3/library/hashlib.html).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html) 和 [模型评估](../../../../../phases/02-ml-fundamentals/09-model-evaluation/docs/en.md)。

留出集（holdout）的分离必须依据内容和分组，不能只看 id。两张 id 不同的工单可能重复同一条客户消息。先把内容规范化（normalize）、把相关记录并成一个组（component），再把整个组分配到分区。

```text
id d1: "Invoice wrong"
id h1: "INVOICE   wrong"
fingerprint equal -> one partition, or reject explicit split
```

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Model evaluation](../../../../../phases/02-ml-fundamentals/09-model-evaluation/docs/en.md).
> Holdout separation must follow content and groups, not just ids. Two tickets with different ids can repeat the same customer message. Normalize content and union related records before assigning the component to a partition.

## Build and inspect · 构建并检查

在对一个组（component）做哈希之前，先把重复内容边和分组边都合并（union）进来。规范化后内容相同、但标签冲突的记录要拒绝。

在你的学习者工作区（learner workspace）中实现本阶段。CLI 辅助脚本是随仓库提供的适配器（adapter），它们导入你的函数；它们不能替代参考解法。

```bash
python3 scripts/project_test.py self-improving-skill-loop --init learning-artifacts/self-improving-skill-loop
python3 scripts/project_test.py self-improving-skill-loop --stage 1 --path learning-artifacts/self-improving-skill-loop
```

先预测上方的中间状态，再运行本阶段。全新的桩（stub）会失败；参考实现跑通并不能证明你的学习者工作区已完成。

> Union both duplicate-content edges and group edges before hashing a component. Reject conflicting labels for identical normalized content.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 下一步探究

同一条客户线程里的两条不同消息，能被安全地当作相互独立的样本吗？

> Can two distinct messages from one customer thread safely be treated as independent examples?
