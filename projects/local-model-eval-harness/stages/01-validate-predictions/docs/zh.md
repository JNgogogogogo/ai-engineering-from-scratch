# Validate prediction records · 校验预测记录

Stage 1 of 4。开始之前，先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 1 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

预测记录就是证据：id、answer、confidence 和实测延迟。要求 id 唯一、数值必须是有限数。否则 NaN 能溜过各种比较，把一次失败变成一份看似有效的报告。

harness 消费的是 recording，所以每个指标测试都不需要模型在场。要评估一个真实的本地模型，请按同一份契约录制它的响应，并把执行环境信息保存在生成的 JSON 旁边。

> A prediction record is evidence: id, answer, confidence, and measured latency. Require unique ids and finite numbers. NaN can otherwise slip past comparisons and turn a failure into an apparently valid report.
> The harness consumes recordings so every metric test runs without a model. To evaluate a real local model, record its responses in the same contract and keep the execution environment beside the resulting JSON.

## Work through one concrete case · 走一个具体例子

两条 id 为 `case-a` 的记录会让与标签的连接产生歧义，所以即使两者的答案一致，校验也会拒绝它们。confidence 必须是有限数且落在 0..1 之内；NaN 必须在任何比较或求平均之前就失败。

```figure
pj-local-model-eval-harness-1
```

修改实验输入，先自己算出结果，再去读它的指标。figure 会根据这些输入计算；下面的实现测试仍然是完成证据的来源。

> Two records with idcase-a make joining to labels ambiguous, so validation rejects them even if their answers agree. Confidence must be finite and within 0..1; NaN must fail before any comparisons or averages.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

针对上述契约实现 `validate`。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只返回值；文件输入、参数解析和展示交给提供的 driver。

在 Python 里 boolean 是 integer 的子类，但它不是一个延迟测量值。把 answer、confidence、latency 和 id 作为一个整体保存，让后续指标不会意外地按数组位置对齐。

> Implement `validate` against the stated contract.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> A boolean is an integer subclass in Python but is not a latency measurement. Preserve answer, confidence, latency and id together so later metrics cannot accidentally align by array position.

## Verify and inspect · 验证与检查

在仓库根目录用 `python3 scripts/project_test.py local-model-eval-harness --init learning-artifacts/local-model-eval-harness` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py local-model-eval-harness --stage 1 --path learning-artifacts/local-model-eval-harness --strict
```

全新工作区在你实现契约之前应该保持失败。每个阶段完成后，用提供的样例运行你真实的 artifact：

```bash
cd learning-artifacts/local-model-eval-harness
python3 cli.py samples/input.json --output scorecard.json --html reliability.html
```

> From the repository root, initialize once with `python3 scripts/project_test.py local-model-eval-harness --init learning-artifacts/local-model-eval-harness`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

打乱预测行的顺序，证明分数保持不变。然后复制一个 id，确认运行会失败，而不是把它数两次。

> Reorder prediction rows and prove the score stays the same. Then duplicate one id and confirm that the run fails instead of double-counting it.

## References · 参考资料

[主要技术参考](https://docs.python.org/3/library/statistics.html)

> [Primary technical reference](https://docs.python.org/3/library/statistics.html)
