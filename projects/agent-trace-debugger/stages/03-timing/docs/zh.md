# Separate work time from waiting time · 区分工作时间与等待时间

第 3 阶段（共 4 阶段）。开始前请先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 3 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

包含时长（inclusive duration）等于 end 减 start。独占时长（exclusive duration）要减去直接子区间的并集（union），而不是它们的和，因为并行的子 span 会重叠。根区间的并集给出跨运行的墙上时间（wall time）。token 是每个 span 局部的，只累加一次。最慢结果（slowest）命名的是独占时长最大的 span，从而避免选中一个大部分时间都在等待子节点的根。

本阶段的边界是 `unionDuration, analyze`。保持此前各阶段的行为不变：最终评分器会在同一个工作区上运行所有阶段。

> Inclusive duration is end minus start. Exclusive duration subtracts the union of immediate child intervals, not their sum, because parallel children overlap. Root interval union provides wall time across runs. Tokens are local per span and summed once. The slowest result names the span with greatest exclusive duration, avoiding a root that is mostly waiting on children.
> The boundary for this stage is `unionDuration, analyze`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 走一遍具体案例

childA 运行 10..60，childB 运行 40..90。它们的时长之和是 100，重叠是 20，并集是 80。因此这个 100 ms 的父节点自身拥有（own）20 ms，而不是 0。

```figure
pj-agent-trace-debugger-3
```

修改实验输入，先自己算出结果再看它的指标。图形会根据这些输入计算；下方的实现测试仍然是完成与否的判定依据。

> ChildA runs 10..60 and childB runs 40..90. Their summed duration is 100, their overlap is 20, and their union is 80. The 100 ms parent therefore owns 20 ms, not zero.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的工作区 `main.ts` 中实现 `unionDuration, analyze`。先尝试自己实现契约，之后再去读参考中的导出类型。保留 starter 的公开命名，这样测试才能调用你的实现。核心函数返回结构化的值，不要在核心函数内部打印；打印最终结果是 CLI 的职责。

使用[公开 API 契约](../../../API.md)和带类型的起始签名。核心函数只返回值，把文件输入、参数解析和展示交给附带的驱动代码。

按开始时间对区间排序；遇到重叠就延伸当前终点，只有当下一个区间在其之后开始时才提交（commit）当前区间。计算一个 span 的独占时长时使用直接子节点。

> Implement `unionDuration, analyze` in your workspace `main.ts`. Read the exported types in the reference only after attempting the contract. Preserve the starter's public names so tests can call your implementation. Return structured values instead of printing inside the core function; the CLI prints the final result.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Sort intervals by start; extend the current end on overlap and commit the interval only when the next interval starts after it. Use immediate children when computing a span's exclusive duration.

## Verify and inspect · 验证与检查

在仓库根目录下，先用 `python3 scripts/project_test.py agent-trace-debugger --init learning-artifacts/agent-trace-debugger` 初始化一次。然后按阶段累进式评分：

```bash
python3 scripts/project_test.py agent-trace-debugger --stage 3 --path learning-artifacts/agent-trace-debugger --strict
```

全新的工作区在你实现契约之前应当是失败的。所有阶段都完成后，用附带的样例运行你真实的 artifact：

```bash
cd learning-artifacts/agent-trace-debugger
node cli.ts --input samples/trace.jsonl --baseline samples/before.jsonl --output trace.html --json trace.json
```

> From the repository root, initialize once with `python3 scripts/project_test.py agent-trace-debugger --init learning-artifacts/agent-trace-debugger`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

在实验中把 B 的开始时间从 40 改成 70。在观察条形图之前，先预测并集为 70、父节点自身时间为 30。

> Move B start from 40 to 70 in the lab. Predict union 70 and parent own time 30 before observing the bars.

## References · 参考资料

[OpenTelemetry traces concepts](https://opentelemetry.io/docs/concepts/signals/traces/)
[Node test runner](https://nodejs.org/api/test.html)

> [OpenTelemetry traces concepts](https://opentelemetry.io/docs/concepts/signals/traces/)
> [Node test runner](https://nodejs.org/api/test.html)
