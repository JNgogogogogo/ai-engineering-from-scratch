# Reserve costs and enforce deadlines · 预留成本并强制截止时间

第 3 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 3 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

在启动每个 reviewer 之前先预留它的成本。放不进剩余预算的工作直接跳过，并把这个决策记录下来。让每个 reviewer 与 deadline 赛跑，时间一到就 abort 它的信号。失败仍留在 trace 里，已完成的审查照常参与聚合。adapter 必须遵守 AbortSignal 才能停掉外部工作；runner 无法强迫远端服务取消。

本阶段的边界是 `runPanel`。保持之前阶段的行为不变：最终评分器会在同一个 workspace 上运行每一个阶段。

> Reserve each reviewer cost before launching it. Skip work that cannot fit the remaining budget and record the decision. Race each reviewer against a deadline and abort its signal when time expires. ... Adapters must honor AbortSignal to stop external work; the runner cannot force a remote service to cancel.

## Work through one concrete case · 走一遍具体案例

三个 reviewer 各花 1 个单位成本，budget 2 只放行前两个。它们的工作并发启动，同时一个 1000 ms 的 deadline 把慢的 reviewer 标记为 timeout，并 abort 它们的信号。

```figure
pj-multi-agent-code-review-panel-3
```

修改实验（lab）的输入，先自己算出结果，再去看它的指标。图中数字由这些输入计算而来；下面的实现测试仍然是完成与否的证据来源。

> Three reviewers cost one unit each and budget 2 admits only the first two. Their work starts concurrently, while a1000 ms deadline marks slow reviewers timeout and aborts their signals. ... Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的 workspace `main.ts` 里实现 `runPanel`。先自己尝试契约，之后再去读参考实现中导出的类型。保留起始代码的公开名称，测试才能调用你的实现。核心函数返回结构化值，不要在核心函数内部打印；最终结果由 CLI 打印。

使用[公开的 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示交给随附的 driver。

在启动每个 promise 之前先预留它的成本。聚合已完成的审查时，把 timeout 和 failure 事件留在 trace 里；否则一个看似便宜的残缺 panel 会把被跳过的工作藏起来。

> Implement `runPanel` in your workspace `main.ts`. ... Reserve each cost before starting its promise. Keep timeout and failure events in the trace while aggregating completed reviews; otherwise a cheap-looking partial panel hides skipped work.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py multi-agent-code-review-panel --init learning-artifacts/multi-agent-code-review-panel` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py multi-agent-code-review-panel --stage 3 --path learning-artifacts/multi-agent-code-review-panel --strict
```

全新的 workspace 在你实现契约之前应当判为失败。每个阶段完成后，用随附的样例运行你的真实产物：

```bash
cd learning-artifacts/multi-agent-code-review-panel
node cli.ts --input samples/review.json --output panel.json --html panel.html
```

> From the repository root, initialize once with `python3 scripts/project_test.py multi-agent-code-review-panel --init learning-artifacts/multi-agent-code-review-panel`. Then grade cumulatively ... A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample.

## Investigate the failure boundary · 探查失败边界

实现一个无视 AbortSignal 的 reviewer。展示 runner 可以停止等待，但无法保证外部工作真的停了。

> Implement a reviewer that ignores AbortSignal. Show that the runner can stop waiting but cannot guarantee the external work stopped.

## References · 参考资料

[Node 中的 AbortController](https://nodejs.org/api/globals.html#class-abortcontroller)
[Node 测试运行器](https://nodejs.org/api/test.html)
