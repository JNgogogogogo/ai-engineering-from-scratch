# Publish accuracy and latency together · 把准确率和延迟一起发布

Stage 4 of 4。开始之前，先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 4 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

质量和延迟衡量的是不同的取舍。使用 nearest-rank 百分位数，让定义在小样本上也可复现。把 p50 和 p95 与 accuracy、coverage、calibration 以及被测预测的数量一起报告。

附带的 demo 使用的是明确合成的录制延迟，不是对任何本地模型的计时结论。在做性能决策之前，先用真实测量值替换它们。

> Quality and latency measure different tradeoffs. Use nearest-rank percentiles so the definition is reproducible on small samples. Report p50 and p95 alongside accuracy, coverage, calibration, and number of measured predictions.
> The included demo uses explicitly synthetic recorded latencies, not timing claims about any local model. Substitute real measurements before making a performance decision.

## Work through one concrete case · 走一个具体例子

延迟 [80,100,120,300,900] 的 nearest-rank p95 位于 ceil(.95*5)=5，所以 p95=900。recording manifest 把 model revision、prompt revision、硬件和 confidence 方法保存在这个数字旁边。

```figure
pj-local-model-eval-harness-4
```

修改实验输入，先自己算出结果，再去读它的指标。figure 会根据这些输入计算；下面的实现测试仍然是完成证据的来源。

> Latencies[80,100,120,300,900] have nearest-rank p95 at ceil(.95*5)=5, so p95=900. The recording manifest keeps model revision, prompt revision, hardware and confidence method beside this number.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

针对上述契约实现 `scorecard`。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只返回值；文件输入、参数解析和展示交给提供的 driver。

record.py 只把 prompt 发给模型端点；expected 标签留在本地。用单调时钟包住真实请求，并把产生的 recording 喂给 cli.py。

> Implement `scorecard` against the stated contract.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> record.py sends only the prompt to the model endpoint; expected labels remain local. Use a monotonic clock around the actual request and feed the resulting recording to cli.py.

## Verify and inspect · 验证与检查

在仓库根目录用 `python3 scripts/project_test.py local-model-eval-harness --init learning-artifacts/local-model-eval-harness` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py local-model-eval-harness --stage 4 --path learning-artifacts/local-model-eval-harness --strict
```

全新工作区在你实现契约之前应该保持失败。每个阶段完成后，用提供的样例运行你真实的 artifact：

```bash
cd learning-artifacts/local-model-eval-harness
python3 cli.py samples/input.json --output scorecard.json --html reliability.html
```

> From the repository root, initialize once with `python3 scripts/project_test.py local-model-eval-harness --init learning-artifacts/local-model-eval-harness`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

比较两份标签不同的 recording。即使两个数据集的用例数量相同，CLI 也必须拒绝这次比较。

报告的 confidence 是模型自报值，除非你的 adapter 定义了其他方法。ECE 随分箱和样本数变化。没有下载或启动任何模型，样例也不是硬件基准。

> Compare two recordings with different labels. The CLI must reject the comparison even when both datasets have the same number of cases.
> Reported confidence is model self-report unless your adapter defines another method. ECE varies with bins and sample count. No model is downloaded or started, and the sample is not a hardware benchmark.

## References · 参考资料

[主要技术参考](https://docs.python.org/3/library/statistics.html)

> [Primary technical reference](https://docs.python.org/3/library/statistics.html)
