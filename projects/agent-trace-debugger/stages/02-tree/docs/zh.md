# Validate parent relationships · 校验父子关系

第 2 阶段（共 4 阶段）。开始前请先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 2 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

子 span 必须引用一个已存在的父 span，并且完全落在父区间之内。要检查每条祖先链是否存在环，并拒绝重复的 id。允许多个根，因为一条 trace 可以包含相互重叠的独立运行。校验发生在聚合之前，这样损坏的图就无法生成看似可信的图表。

本阶段的边界是 `validateTree`。保持此前各阶段的行为不变：最终评分器会在同一个工作区上运行所有阶段。

> A child span must reference an existing parent and fit inside the parent interval. Check every ancestor chain for cycles and reject duplicate ids. Multiple roots are allowed because a trace can contain overlapping independent runs. Validation happens before aggregation so corrupted graphs cannot produce convincing charts.
> The boundary for this stage is `validateTree`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 走一遍具体案例

root 运行 0..100，childA 运行 10..80。一个结束于 110 的 childB 违反了包含关系，即使每个单独区间的时长都非负。A->B->A 违反了祖先关系，即使所有时间都完全相同。

```figure
pj-agent-trace-debugger-2
```

修改实验输入，先自己算出结果再看它的指标。图形会根据这些输入计算；下方的实现测试仍然是完成与否的判定依据。

> The root runs 0..100 and childA runs 10..80. A childB ending 110 violates containment even though each individual interval has a nonnegative duration. A->B->A violates ancestry even if every time is identical.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的工作区 `main.ts` 中实现 `validateTree`。先尝试自己实现契约，之后再去读参考中的导出类型。保留 starter 的公开命名，这样测试才能调用你的实现。核心函数返回结构化的值，不要在核心函数内部打印；打印最终结果是 CLI 的职责。

使用[公开 API 契约](../../../API.md)和带类型的起始签名。核心函数只返回值，把文件输入、参数解析和展示交给附带的驱动代码。

在遍历祖先之前先建一个 id 映射。每个 span 使用一个全新的 visited 集合来捕捉环，这样就不会把「被两个合法子节点共享的祖先」误判成环。

> Implement `validateTree` in your workspace `main.ts`. Read the exported types in the reference only after attempting the contract. Preserve the starter's public names so tests can call your implementation. Return structured values instead of printing inside the core function; the CLI prints the final result.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Build an id map before walking ancestors. A fresh visited set per span catches cycles without confusing an ancestor shared by two valid children.

## Verify and inspect · 验证与检查

在仓库根目录下，先用 `python3 scripts/project_test.py agent-trace-debugger --init learning-artifacts/agent-trace-debugger` 初始化一次。然后按阶段累进式评分：

```bash
python3 scripts/project_test.py agent-trace-debugger --stage 2 --path learning-artifacts/agent-trace-debugger --strict
```

全新的工作区在你实现契约之前应当是失败的。所有阶段都完成后，用附带的样例运行你真实的 artifact：

```bash
cd learning-artifacts/agent-trace-debugger
node cli.ts --input samples/trace.jsonl --baseline samples/before.jsonl --output trace.html --json trace.json
```

> From the repository root, initialize once with `python3 scripts/project_test.py agent-trace-debugger --init learning-artifacts/agent-trace-debugger`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

创建两个相互重叠的独立根。它们是合法的；第 3 阶段必须合并它们的时间区间，而不是把墙上时间直接相加。

> Create two independent roots that overlap. They are valid; stage 3 must merge their time intervals instead of summing wall time.

## References · 参考资料

[OpenTelemetry traces concepts](https://opentelemetry.io/docs/concepts/signals/traces/)
[Node test runner](https://nodejs.org/api/test.html)

> [OpenTelemetry traces concepts](https://opentelemetry.io/docs/concepts/signals/traces/)
> [Node test runner](https://nodejs.org/api/test.html)
