# Select tools under an explicit context budget · 在显式上下文预算内选择工具

Stage 2 of 5。开始之前，先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 2 of 5. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

在把工具送进 context window 之前，先对元数据排序。数出每个被选 schema 实际的紧凑 JSON 字符数，到显式预算即停。这是字符预算，不是 model-token 估计；单位要诚实。按名称稳定地打破平局，让发现过程可复现。

> Rank metadata before sending tools into a context window. Count the actual compact JSON characters of each selected schema and stop at the explicit budget. This is a character budget, not a model-token estimate; keep the units honest. Stable name ties make discovery reproducible.

## Work through one concrete case · 走一个具体例子

紧凑长度分别为 200 和 220 的两个 schema，放进数组共占 423 个字符：200+220，再加两个方括号和一个逗号。把各自长度直接相加会低估，可能溢出 420 字符的预算。

```figure
pj-mcp-at-scale-2
```

修改实验输入，先自己算出结果，再去读它的指标。figure 会根据这些输入计算；下面的实现测试仍然是完成证据的来源。

> Two schemas of compact lengths 200 and 220 occupy 423 characters in an array:200+220, two brackets and one comma. Summing individual lengths would undercount and could overflow a420-character budget.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

实现 `discovery.py`：`discover`。这个 artifact 是 MCP Server With 250 Tools 的 stage 2。它消费显式输入，返回一个可检查的结果，供下一个 stage 使用。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只返回值；文件输入、参数解析和展示交给提供的 driver。

在接受下一个 schema 之前，先测量候选已选数组 JSON 序列化后的长度。排序和打包是两回事：一个排名很高但超大的 schema 可以被跳过，而更小的有用 schema 仍然装得下。

> Implement `discovery.py`: `discover`. This artifact is stage 2 of MCP Server With 250 Tools. It consumes explicit inputs and returns an inspectable result that the next stage can use.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Measure JSON serialization of the candidate selected array before accepting the next schema. Ranking and packing are distinct: a highly ranked oversized schema can be skipped while a smaller useful schema still fits.

## Verify and inspect · 验证与检查

在仓库根目录用 `python3 scripts/project_test.py mcp-at-scale --init learning-artifacts/mcp-at-scale` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py mcp-at-scale --stage 2 --path learning-artifacts/mcp-at-scale --strict
```

全新工作区在你实现契约之前应该保持失败。每个阶段完成后，用提供的样例运行你真实的 artifact：

```bash
cd learning-artifacts/mcp-at-scale
python3 cli.py samples/inventory.json --query "pods count" --max-chars 500
```

> From the repository root, initialize once with `python3 scripts/project_test.py mcp-at-scale --init learning-artifacts/mcp-at-scale`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

把 max_chars 设为恰好等于一个已选 schema 数组的大小，然后再设为少一个字符。在不估算 model token 的情况下验证这个边界。

> Set max_chars to exactly the size of one selected schema array, then one character less. Verify the boundary without estimating model tokens.

## References · 参考资料

[参考 1](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
[参考 2](https://www.jsonrpc.org/specification)

> [Reference 1](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
> [Reference 2](https://www.jsonrpc.org/specification)
