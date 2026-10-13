# Measure normalized exact-answer accuracy · 测量归一化的精确答案准确率

Stage 2 of 4。开始之前，先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 2 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

精确答案匹配适合受约束的输出，例如标签和简短的参考答案。只归一化大小写和空白；不要为了让分数变高而删除事实或标点。

每个带标签的条目要求恰好一条预测，并拒绝未知 id。缺失的预测按错误计入分母。coverage 指标揭示数据集中实际被尝试的比例。

> Exact-answer matching is appropriate for constrained outputs such as labels and short reference answers. Normalize case and whitespace only; do not remove facts or punctuation to inflate a score.
> Require one prediction per labeled item and reject unknown ids. Missing predictions count as incorrect in the denominator. The coverage metric reveals how much of the dataset was actually attempted.

## Work through one concrete case · 走一个具体例子

十个标签、六个正确预测、两个错误预测、两个缺失预测时，accuracy 是 6/10，coverage 是 8/10。用八作分母会奖励一个回避难题的系统。

```figure
pj-local-model-eval-harness-2
```

修改实验输入，先自己算出结果，再去读它的指标。figure 会根据这些输入计算；下面的实现测试仍然是完成证据的来源。

> With ten labels, six correct predictions, two wrong predictions and two missing predictions, accuracy is6/10 and coverage is8/10. Dividing by eight would reward a system for avoiding difficult cases.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

针对上述契约实现 `accuracy`。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只返回值；文件输入、参数解析和展示交给提供的 driver。

这个任务只归一化大小写和重复空白。标点和事实保持原样。拒绝在预期标签映射里找不到的预测 id。

> Implement `accuracy` against the stated contract.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Normalize only case and repeated whitespace for this task. Keep punctuation and facts intact. Reject prediction ids absent from the expected label map.

## Verify and inspect · 验证与检查

在仓库根目录用 `python3 scripts/project_test.py local-model-eval-harness --init learning-artifacts/local-model-eval-harness` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py local-model-eval-harness --stage 2 --path learning-artifacts/local-model-eval-harness --strict
```

全新工作区在你实现契约之前应该保持失败。每个阶段完成后，用提供的样例运行你真实的 artifact：

```bash
cd learning-artifacts/local-model-eval-harness
python3 cli.py samples/input.json --output scorecard.json --html reliability.html
```

> From the repository root, initialize once with `python3 scripts/project_test.py local-model-eval-harness --init learning-artifacts/local-model-eval-harness`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

从一个十题的数据集里只记录一条简单的正确答案。在运行 scorer 之前，先预测 accuracy 是 0.1、coverage 是 0.1。

> Record only one easy correct answer from a ten-case dataset. Predict accuracy 0.1 and coverage 0.1 before running the scorer.

## References · 参考资料

[主要技术参考](https://docs.python.org/3/library/statistics.html)

> [Primary technical reference](https://docs.python.org/3/library/statistics.html)
