# Compare the same cases across revisions · 跨修订版本对比同一批用例

**4 个阶段中的第 3 个。** Python。预计约 2 小时。

平均值可能掩盖一次严重的回归（regression）。按 case id 把两个修订版本两两配对，并把每一对标记为 improved（改善）、regressed（回归）、stable pass（稳定通过）或 stable fail（稳定失败）。一个新的成功绝不能抵消一个丢失的必备行为。

两个修订版本要使用同一份用例列表。cassette 中多余的 key 会被忽略，缺失的 key 则判为失败。这样即使某一次录制任务不完整，你也能对比修订版本，而不必编造结果。

```figure
pj-prompt-regression-tester-3
```

主要参考：[主要技术参考](https://docs.python.org/3/library/difflib.html)。

> An average can hide a serious regression.
> Pair revisions by case id and label each as improved, regressed, stable pass, or stable fail.
> A new success must not cancel a lost required behavior.
> Use the same case list for both revisions.
> Extra cassette keys are ignored and missing keys fail.
> This lets you compare revisions even when one recording job was incomplete without fabricating a result.

## Worked Orchard case · Orchard 实战案例

在动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html) 和 [结构化输出](../../../../../phases/11-llm-engineering/03-structured-outputs/docs/en.md)。先完成 [阶段 2](../../02-score-recordings/docs/en.md)。

候选版本修好了来源归属（source attribution），却把机器可读的 JSON 换成了友好的散文。在计算平均值之前先按 case id 配对：一处改善修不好另一处坏掉的接口。

```text
format-json: pass -> fail = regressed
source-link: fail -> pass = improved
aggregate pass rate: unchanged
```

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Structured outputs](../../../../../phases/11-llm-engineering/03-structured-outputs/docs/en.md). Complete [stage 2](../../02-score-recordings/docs/en.md) first.
> The candidate fixes source attribution but replaces machine-readable JSON with friendly prose.
> Pair case ids before calculating the average: one improvement does not repair another broken interface.

## Build and inspect · 构建与检查

把 model、settings 和 case 哈希与响应保存在一起。除非你显式允许该实验，否则 CLI 会拒绝 model/settings 发生变化的对比。

在你的学习工作区（learner workspace）里实现该阶段。这些 CLI 助手是官方提供的适配器，负责导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py prompt-regression-tester --stage 3 --path learning-artifacts/prompt-regression-tester
```

先预测上面的中间状态，再运行该阶段。全新的 stub 会失败；参考实现能跑通，并不代表你的学习工作区已经完成。

> Keep model, settings and case hash alongside the responses.
> The CLI rejects changed model/settings unless you explicitly allow that experiment.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage.
> A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接下来探究

你会如何向 JSON 消费方（consumer）的负责人解释一条「持平的通过率」？

> How would you explain a flat pass rate to the owner of the JSON consumer?
