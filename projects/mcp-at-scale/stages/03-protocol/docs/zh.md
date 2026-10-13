# Implement initialized JSON-RPC over stdio · 在 stdio 上实现带初始化生命周期的 JSON-RPC

Stage 3 of 5。开始之前，先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 3 of 5. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

协议有生命周期：先协商版本，接收 initialized 通知，然后才能 list 或 call 工具。通知没有响应。把传输错误与工具执行错误分开，保留 request id，并对目录分页，而不是一次性返回全部 250 个 schema。

> The protocol has a lifecycle: negotiate a version, receive the initialized notification, then list or call tools. Notifications have no response. Separate transport errors from tool execution errors, preserve the request id, and paginate the catalog instead of returning all 250 schemas at once.

## Work through one concrete case · 走一个具体例子

initialize id1 返回版本和 capabilities。notifications/initialized 没有 id，也不输出任何行。随后 tools/call id2 返回 id2，要么携带 content，要么携带协议错误。把输入行数当作期望响应数会让程序挂住。

```figure
pj-mcp-at-scale-3
```

修改实验输入，先自己算出结果，再去读它的指标。figure 会根据这些输入计算；下面的实现测试仍然是完成证据的来源。

> initialize id1 returns a version and capabilities. notifications/initialized has no id and emits no line. tools/call id2 then returns id2 with either content or a protocol error. Counting input lines as expected responses would hang.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

实现 `protocol.py`：`handle`、`serve`。这个 artifact 是 MCP Server With 250 Tools 的 stage 3。它消费显式输入，返回一个可检查的结果，供下一个 stage 使用。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只返回值；文件输入、参数解析和展示交给提供的 driver。

把「已协商」与「已初始化」两个状态分开维护。CLI 提供一个有作用域的目录来 serve；catalog_search 工具调用的就是 stage 2 测试过的那个 discover 函数。

> Implement `protocol.py`: `handle`, `serve`. This artifact is stage 3 of MCP Server With 250 Tools. It consumes explicit inputs and returns an inspectable result that the next stage can use.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Maintain negotiated and initialized state separately. The CLI supplies a scoped catalog to serve; the catalog_search tool calls the same discover function tested in stage 2.

## Verify and inspect · 验证与检查

在仓库根目录用 `python3 scripts/project_test.py mcp-at-scale --init learning-artifacts/mcp-at-scale` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py mcp-at-scale --stage 3 --path learning-artifacts/mcp-at-scale --strict
```

全新工作区在你实现契约之前应该保持失败。每个阶段完成后，用提供的样例运行你真实的 artifact：

```bash
cd learning-artifacts/mcp-at-scale
python3 cli.py samples/inventory.json --query "pods count" --max-chars 500
```

> From the repository root, initialize once with `python3 scripts/project_test.py mcp-at-scale --init learning-artifacts/mcp-at-scale`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

在初始化之前调用一个工具，然后走完生命周期，再对样例 inventory 调用 pods_count。比较协议错误 -32002 与成功的文本结果 "2"。

> Call a tool before initialization, then complete the lifecycle and call pods_count against the sample inventory. Compare protocol error -32002 with a successful text result "2".

## References · 参考资料

[参考 1](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
[参考 2](https://www.jsonrpc.org/specification)

> [Reference 1](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
> [Reference 2](https://www.jsonrpc.org/specification)
