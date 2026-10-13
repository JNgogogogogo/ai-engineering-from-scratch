# Require a separate gate before promotion · 晋升前先设一道独立关卡

**第 4 阶段（共 4 阶段）。** Python。预留约 2 小时。

在同一批预留案例上比较基线（baseline）与候选（candidate）。要求聚合增益达到最低门槛，并且在之前正确的案例上零退步，然后用摘要（digest）唯一确定这个候选。这道关卡（gate）评估的是一个产物（artifact）；它绝不改写用户的技能，也绝不部署它。反复在同一个留出集上调优会泄露信息，所以后续轮次要轮换使用真正全新的评估集。

```figure
pj-self-improving-skill-loop-4
```

> Compare baseline and candidate on the same reserved cases. Require a minimum aggregate gain and zero losses on previously correct cases, then identify the exact candidate with a digest.
> This gate evaluates an artifact; it never rewrites a user skill or deploys it. Repeatedly tuning on the same holdout leaks information, so rotate a genuinely new evaluation set for later rounds.

## Implementation boundary · 实现边界

```python
def gate(holdout,baseline,candidate,min_gain=.05):
    raise NotImplementedError("Implement the stage contract")
```

主要参考：[参考 1](https://docs.python.org/3/library/hashlib.html)。

> Primary reference: [Reference 1](https://docs.python.org/3/library/hashlib.html).

## Worked Orchard case · Orchard 实战案例

写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html) 和 [模型评估](../../../../../phases/02-ml-fundamentals/09-model-evaluation/docs/en.md)。先完成 [阶段 3](../../03-propose/docs/en.md)。

留出集关卡通过后，会产出一个候选摘要供人审阅。晋升（promotion）要求精确匹配这个摘要，写入带版本的规则文件，并保留上一个文件以便回滚（rollback）。已发布的样例工单只是示例，不是未见过的基准（benchmark）。

```text
baseline accuracy=0; candidate accuracy=1; no regression -> eligible
wrong digest -> no write
exact digest -> promote and retain .previous
```

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Model evaluation](../../../../../phases/02-ml-fundamentals/09-model-evaluation/docs/en.md). Complete [stage 3](../../03-propose/docs/en.md) first.
> A passing holdout gate produces a candidate digest for human review. Promotion requires that exact digest, writes a versioned rules file, and preserves the previous file for rollback. Published sample tickets are examples, not an unseen benchmark.

## Build and inspect · 构建并检查

把批准绑定到序列化后的规则内容上，并在写入之前重新计算摘要。绝不要凭一份好成绩推断出「已获批准」。

在你的学习者工作区（learner workspace）中实现本阶段。CLI 辅助脚本是随仓库提供的适配器（adapter），它们导入你的函数；它们不能替代参考解法。

```bash
python3 scripts/project_test.py self-improving-skill-loop --stage 4 --path learning-artifacts/self-improving-skill-loop
```

在前面各阶段累计通过之后，从仓库根目录用最初的样例输入运行你的产物：

```bash
python3 learning-artifacts/self-improving-skill-loop/cli.py projects/self-improving-skill-loop/examples/support-cases.json --out experiment.json
```

实验会从开发数据中提出确定性的路由规则。显式给出的开发/留出输入会接受内容与分组泄露审计。晋升需要 `--promote-to`，以及通过的关卡打印出的那个精确的 `--approve-digest`。上一个规则文件会保留在 `<destination>.previous`，便于手动回滚；这是一个单写者（single-writer）的文件工作流。

> Bind approval to serialized rule content and recompute the digest before writing. Never infer approval from a good score.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> After the cumulative stages pass, run your artifact on the original sample input from the repository root:
> The experiment proposes deterministic routing rules from development data. Explicit development/holdout input is audited for content and group leakage. Promotion needs --promote-to and the exact --approve-digest printed by the passing gate. The previous rules remain in <destination>.previous for manual rollback; this is a single-writer file workflow.

## Investigate next · 下一步探究

在再次编辑技能之前，你会怎样冻结下一个留出集？

> How would you freeze the next holdout before editing the skill again?

`--dataset-audit audit.json` 选项会读取数据集切分审计器带版本的 `partitions.train` 和 `partitions.test` 记录，保留标签与来源，并在本地复查泄露。`--export-skill orchard-routing` 会写入一份新的草稿 `SKILL.md` 加上 `references/rules.json`；它不会安装或激活候选。

> The `--dataset-audit audit.json` option consumes the dataset split auditor's versioned `partitions.train` and `partitions.test` records, preserving labels and sources and rechecking leakage locally. `--export-skill orchard-routing` writes a new draft `SKILL.md` plus `references/rules.json`; it does not install or activate the candidate.
