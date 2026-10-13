# Render an inspectable timeline · 渲染可检查的时间线

第 4 阶段（共 4 阶段）。开始前请先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 4 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

生成一个独立的 HTML 时间线：每个 span 一行，条形按比例缩放，错误带颜色标记。span 名称在插入标记之前必须先转义。内容包含自身时间（own time）、总时间（total time）、墙上时间（wall time）、token 数和错误数。空 trace 也要产出一个可读的 artifact。输出是一份本地静态报告，不加载任何第三方脚本。

本阶段的边界是 `render`。保持此前各阶段的行为不变：最终评分器会在同一个工作区上运行所有阶段。

> Generate a standalone HTML timeline with one row per span, scaled bars and error coloring. Escape span names before inserting them into markup. Include own time, total time, wall time, tokens and error count. Empty traces still produce a readable artifact. The output is a local static report and does not load third-party scripts.
> The boundary for this stage is `render`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 走一遍具体案例

附带的 baseline 与变更后的 trace 墙上时间都是 100 ms。变更后的 model span 额外花费了 200 个 token 并且失败了。只看总延迟会掩盖这次回归。

```figure
pj-agent-trace-debugger-4
```

修改实验输入，先自己算出结果再看它的指标。图形会根据这些输入计算；下方的实现测试仍然是完成与否的判定依据。

> The supplied baseline and changed trace both have 100 ms wall time. The changed model span spends 200 additional tokens and fails. Looking only at total latency would conceal that regression.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的工作区 `main.ts` 中实现 `render`。先尝试自己实现契约，之后再去读参考中的导出类型。保留 starter 的公开命名，这样测试才能调用你的实现。核心函数返回结构化的值，不要在核心函数内部打印；打印最终结果是 CLI 的职责。

使用[公开 API 契约](../../../API.md)和带类型的起始签名。核心函数只返回值，把文件输入、参数解析和展示交给附带的驱动代码。

CLI 对每个输入独立分析，然后相减对应的聚合指标。span 名称在嵌入 HTML 之前先转义，并保留 JSON 回执（receipt）供自动化对比使用。

> Implement `render` in your workspace `main.ts`. Read the exported types in the reference only after attempting the contract. Preserve the starter's public names so tests can call your implementation. Return structured values instead of printing inside the core function; the CLI prints the final result.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> The CLI analyzes each input independently, then subtracts matching aggregate metrics. Escape span names before embedding them in HTML, and keep the JSON receipt for automated comparisons.

## Verify and inspect · 验证与检查

在仓库根目录下，先用 `python3 scripts/project_test.py agent-trace-debugger --init learning-artifacts/agent-trace-debugger` 初始化一次。然后按阶段累进式评分：

```bash
python3 scripts/project_test.py agent-trace-debugger --stage 4 --path learning-artifacts/agent-trace-debugger --strict
```

全新的工作区在你实现契约之前应当是失败的。所有阶段都完成后，用附带的样例运行你真实的 artifact：

```bash
cd learning-artifacts/agent-trace-debugger
node cli.ts --input samples/trace.jsonl --baseline samples/before.jsonl --output trace.html --json trace.json
```

> From the repository root, initialize once with `python3 scripts/project_test.py agent-trace-debugger --init learning-artifacts/agent-trace-debugger`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

添加一个名为 <script>alert(1)</script> 的 span。它必须以文本形式可见，同时 token/错误的差值保持为数字。

输入是有文档说明的 JSONL Span 契约，不是原生 OTLP 导出。token 必须是每个 span 的独占用量。跨机器的时钟必须在导入前归一化。

> Add a span named <script>alert(1)</script>. It must be visible as text while the token/error delta remains numeric.
> Input is the documented JSONL Span contract, not a native OTLP export. Tokens must be exclusive per-span usage. Cross-machine clocks must be normalized before import.

## References · 参考资料

[OpenTelemetry traces concepts](https://opentelemetry.io/docs/concepts/signals/traces/)
[Node test runner](https://nodejs.org/api/test.html)

> [OpenTelemetry traces concepts](https://opentelemetry.io/docs/concepts/signals/traces/)
> [Node test runner](https://nodejs.org/api/test.html)
