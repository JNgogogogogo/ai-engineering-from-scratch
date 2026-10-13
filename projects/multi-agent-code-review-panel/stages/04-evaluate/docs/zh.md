# Measure panel precision and recall · 度量 panel 的 precision 与 recall

第 4 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 4 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

用去重后的 finding id 对着一个期望集合（expected set）做评估。precision 度量预测出的 finding 有多少落在期望集合里；recall 度量期望集合被找出来了多少。两个集合都去重，让重复的 reviewer 抬不动指标。零个预测时 precision 记为 0，而不是一个有误导性的满分。在调整 quorum 之前，先用 held-out 输入试一试。

本阶段的边界是 `evaluate`。保持之前阶段的行为不变：最终评分器会在同一个 workspace 上运行每一个阶段。

> Evaluate unique finding ids against an expected set. Precision measures how many predicted findings are expected; recall measures how much of the expected set was found. Deduplicate both sets so repeated reviewers cannot inflate the metric. Zero predictions produce precision zero rather than a misleading perfect score.

## Work through one concrete case · 走一遍具体案例

宽泛的本地 reviewer 预测了 3 个 finding，其中 2 个真阳性，所以 precision=2/3。quorum 恰好保住两个期望 finding：在这个样例上 precision=1、recall=1。budget 为 1 时无法形成共识，recall 为 0。

```figure
pj-multi-agent-code-review-panel-4
```

修改实验（lab）的输入，先自己算出结果，再去看它的指标。图中数字由这些输入计算而来；下面的实现测试仍然是完成与否的证据来源。

> The broad local reviewer predicts three findings with two true positives, so precision=2/3. Quorum retains the two expected findings: precision=1 and recall=1 on this sample. A budget of1 leaves no consensus and recall 0. ... Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的 workspace `main.ts` 里实现 `evaluate`。先自己尝试契约，之后再去读参考实现中导出的类型。保留起始代码的公开名称，测试才能调用你的实现。核心函数返回结构化值，不要在核心函数内部打印；最终结果由 CLI 打印。

使用[公开的 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示交给随附的 driver。

把单个 reviewer 的预测和组合预测对着同一个期望集合比较。两个集合都去重，并保留 source fingerprint；来自不同快照的指标不是可比的证据。

> Implement `evaluate` in your workspace `main.ts`. ... Compare individual and combined predictions against the same expected set. Deduplicate both sets and retain the source fingerprint; metrics from a different snapshot are not comparable evidence.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py multi-agent-code-review-panel --init learning-artifacts/multi-agent-code-review-panel` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py multi-agent-code-review-panel --stage 4 --path learning-artifacts/multi-agent-code-review-panel --strict
```

全新的 workspace 在你实现契约之前应当判为失败。每个阶段完成后，用随附的样例运行你的真实产物：

```bash
cd learning-artifacts/multi-agent-code-review-panel
node cli.ts --input samples/review.json --output panel.json --html panel.html
```

> From the repository root, initialize once with `python3 scripts/project_test.py multi-agent-code-review-panel --init learning-artifacts/multi-agent-code-review-panel`. Then grade cumulatively ... A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample.

## Investigate the failure boundary · 探查失败边界

留出一个只有一个 reviewer 发现的用例。在把「共识」当作改进来展示之前，先量一量 quorum 是否丢掉了那个真阳性。

本地 reviewer 是各不相同的静态启发式，不是相互独立的 LLM。共识度量的是支持度，不是真相。外部回调必须遵守 AbortSignal；timeout 撤销不了远端已经造成的副作用。

> Hold out a case found by only one reviewer. Measure whether quorum loses that true positive before presenting agreement as an improvement. ... Local reviewers are distinct static heuristics, not independent LLMs. Consensus measures support, not truth.

## References · 参考资料

[Node 中的 AbortController](https://nodejs.org/api/globals.html#class-abortcontroller)
[Node 测试运行器](https://nodejs.org/api/test.html)
