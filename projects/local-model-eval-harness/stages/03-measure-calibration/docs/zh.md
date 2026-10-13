# Measure confidence calibration · 测量置信度校准

Stage 3 of 4。开始之前，先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 3 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

一个以 99% 置信度给出错误答案的模型，对自动化路由来说比一个承认不确定性的模型更危险。期望校准误差（expected calibration error）按置信度把预测分组，并比较平均置信度与实际正确率。

ECE 依赖于分箱选择和样本数量。报告每个非空 bin、它的大小和它的 gap。样本太小或 ECE 看起来很低，都不能证明概率在新任务上是校准的。

> A model that is wrong with 99 percent confidence is more dangerous to an automated router than a model that admits uncertainty. Expected calibration error groups predictions by confidence and compares average confidence with actual correctness.
> ECE depends on bin choice and sample count. Report every nonempty bin, its size, and its gap. A tiny sample or an apparently low ECE does not establish calibrated probabilities on new tasks.

## Work through one concrete case · 走一个具体例子

四个置信度 0.9 的预测里包含三个正确答案。它们的观测准确率是 0.75，单个 bin 的 gap 是 0.15。第二个 bin 里有一个自信的错误答案，必须按 1 个样本加权，而不是与那个 4 样本的 bin 平权。

```figure
pj-local-model-eval-harness-3
```

修改实验输入，先自己算出结果，再去读它的指标。figure 会根据这些输入计算；下面的实现测试仍然是完成证据的来源。

> Four predictions at confidence 0.9 contain three correct answers. Their observed accuracy is0.75 and their single-bin gap is0.15. A second bin with one confident wrong answer must be weighted by one sample, not equally with the four-sample bin.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

针对上述契约实现 `calibration`。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只返回值；文件输入、参数解析和展示交给提供的 driver。

用 min(index,bins-1) 把置信度 1.0 放进最后一个 bin。在 ECE 旁边报告非空 bin 的计数，让平均值无法掩盖证据过小的事实。

> Implement `calibration` against the stated contract.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Place confidence 1.0 in the final bin with min(index,bins-1). Report nonempty bin counts beside ECE so the average cannot conceal tiny evidence.

## Verify and inspect · 验证与检查

在仓库根目录用 `python3 scripts/project_test.py local-model-eval-harness --init learning-artifacts/local-model-eval-harness` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py local-model-eval-harness --stage 3 --path learning-artifacts/local-model-eval-harness --strict
```

全新工作区在你实现契约之前应该保持失败。每个阶段完成后，用提供的样例运行你真实的 artifact：

```bash
cd learning-artifacts/local-model-eval-harness
python3 cli.py samples/input.json --output scorecard.json --html reliability.html
```

> From the repository root, initialize once with `python3 scripts/project_test.py local-model-eval-harness --init learning-artifacts/local-model-eval-harness`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

把同样的记录分成 5 个 bin 和 10 个 bin。解释为什么模型答案没有变，ECE 却变了。

> Split the same records into five and ten bins. Explain why the ECE changes even though the model answers did not.

## References · 参考资料

[主要技术参考](https://docs.python.org/3/library/statistics.html)

> [Primary technical reference](https://docs.python.org/3/library/statistics.html)
