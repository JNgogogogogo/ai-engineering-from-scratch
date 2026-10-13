# Read a JSONL trace · 读取 JSONL 轨迹

第 1 阶段（共 4 阶段）。开始前请先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 1 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

每个非空行解析一个 JSON 对象。要求有稳定的 id、名称、有限的开始与结束时间、非负的 token 数，以及一个明确的 ok 或 error 状态。一行畸形数据要带着行号停止处理。悄悄丢弃坏 span 会扭曲耗时和成本结论。时间是相对毫秒数，不是墙上时钟（wall-clock）时间戳。

本阶段的边界是 `parseTrace`。保持此前各阶段的行为不变：最终评分器会在同一个工作区上运行所有阶段。

> Parse one JSON object per nonempty line. Require stable ids, names, finite start and end times, nonnegative token counts and an explicit ok or error state. A malformed line stops processing with its line number. Silently dropping bad spans would distort timing and cost conclusions. Times are relative milliseconds, not wall-clock timestamps.
> The boundary for this stage is `parseTrace`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 走一遍具体案例

一个包含空行、有效 root 和畸形文本的文件，必须把畸形文本报告为第 3 行。如果在编号之前先过滤空行，就会错误地怪罪第 2 行。

```figure
pj-agent-trace-debugger-1
```

修改实验输入，先自己算出结果再看它的指标。图形会根据这些输入计算；下方的实现测试仍然是完成与否的判定依据。

> A file containing a blank line, a valid root and malformed text must report the malformed text as line 3. Filtering blank lines before numbering would incorrectly blame line 2.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的工作区 `main.ts` 中实现 `parseTrace`。先尝试自己实现契约，之后再去读参考中的导出类型。保留 starter 的公开命名，这样测试才能调用你的实现。核心函数返回结构化的值，不要在核心函数内部打印；打印最终结果是 CLI 的职责。

使用[公开 API 契约](../../../API.md)和带类型的起始签名。核心函数只返回值，把文件输入、参数解析和展示交给附带的驱动代码。

先枚举物理行，在该循环内忽略空行，并在 JSON 解析之后校验 start/end/tokens 是有限数值。保留零时长（zero-duration）的 span；它们是有效的观测。

> Implement `parseTrace` in your workspace `main.ts`. Read the exported types in the reference only after attempting the contract. Preserve the starter's public names so tests can call your implementation. Return structured values instead of printing inside the core function; the CLI prints the final result.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Enumerate physical lines first, ignore blanks inside that loop, and validate finite start/end/tokens after JSON parsing. Retain zero-duration spans; they are valid observations.

## Verify and inspect · 验证与检查

在仓库根目录下，先用 `python3 scripts/project_test.py agent-trace-debugger --init learning-artifacts/agent-trace-debugger` 初始化一次。然后按阶段累进式评分：

```bash
python3 scripts/project_test.py agent-trace-debugger --stage 1 --path learning-artifacts/agent-trace-debugger --strict
```

全新的工作区在你实现契约之前应当是失败的。所有阶段都完成后，用附带的样例运行你真实的 artifact：

```bash
cd learning-artifacts/agent-trace-debugger
node cli.ts --input samples/trace.jsonl --baseline samples/before.jsonl --output trace.html --json trace.json
```

> From the repository root, initialize once with `python3 scripts/project_test.py agent-trace-debugger --init learning-artifacts/agent-trace-debugger`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

用本地脚本录制一个嵌套的 span。时间保持相对毫秒，token 用量只记在恰好一个 span 上。

> Record one nested span from a local script. Keep times in relative milliseconds and account for token usage on exactly one span.

## References · 参考资料

[OpenTelemetry traces concepts](https://opentelemetry.io/docs/concepts/signals/traces/)
[Node test runner](https://nodejs.org/api/test.html)

> [OpenTelemetry traces concepts](https://opentelemetry.io/docs/concepts/signals/traces/)
> [Node test runner](https://nodejs.org/api/test.html)
