# Audit catalog coverage through protocol pages · 通过协议分页审计目录覆盖率

Stage 4 of 5。开始之前，先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 4 of 5. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

把分页当作客户端可见的契约。穿过 handler 遍历每一页，并跨页边界跟踪重复名称。有限页数保护能抓住意外的 cursor 循环。这个审计验证的是协议层的 inventory；最后的 typed client 则会去检验另一条独立的边界——操作系统进程边界。

> Treat pagination as a client-visible contract. Traverse every page through the handler and track duplicate names across page boundaries. A finite page guard catches accidental cursor loops. This audit validates the protocol inventory, while the final typed client will exercise the separate operating-system process boundary.

## Work through one concrete case · 走一个具体例子

250 个工具、页大小 32 需要八页：七个满页加一个 26 个工具的收尾页。跨页保留 seen 名称集合，这样「用新 cursor 重复第 1 页」就无法冒充覆盖率。

```figure
pj-mcp-at-scale-4
```

修改实验输入，先自己算出结果，再去读它的指标。figure 会根据这些输入计算；下面的实现测试仍然是完成证据的来源。

> A32-tool page size over 250 tools requires eight pages: seven full pages and a final 26. Keep seen names across pages so repeating page 1 with a new cursor cannot masquerade as coverage.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

实现 `audit.py`：`audit_catalog`。这个 artifact 是 MCP Server With 250 Tools 的 stage 4。它消费显式输入，返回一个可检查的结果，供下一个 stage 使用。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只返回值；文件输入、参数解析和展示交给提供的 driver。

通过 handle 驱动分页，而不是直接调用 catalog。审计内部数组发现不了传输层的 cursor bug。

> Implement `audit.py`: `audit_catalog`. This artifact is stage 4 of MCP Server With 250 Tools. It consumes explicit inputs and returns an inspectable result that the next stage can use.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Drive pagination through handle rather than calling catalog directly. An audit of internal arrays cannot detect a cursor bug in the transport layer.

## Verify and inspect · 验证与检查

在仓库根目录用 `python3 scripts/project_test.py mcp-at-scale --init learning-artifacts/mcp-at-scale` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py mcp-at-scale --stage 4 --path learning-artifacts/mcp-at-scale --strict
```

全新工作区在你实现契约之前应该保持失败。每个阶段完成后，用提供的样例运行你真实的 artifact：

```bash
cd learning-artifacts/mcp-at-scale
python3 cli.py samples/inventory.json --query "pods count" --max-chars 500
```

> From the repository root, initialize once with `python3 scripts/project_test.py mcp-at-scale --init learning-artifacts/mcp-at-scale`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

在一个 test double 里故意把同一个 cursor 返回两次。给页循环设上限，并把重复页暴露出来，而不是无限继续。

> Deliberately return the same cursor twice in a test double. Bound the page loop and surface the repeated page instead of continuing indefinitely.

## References · 参考资料

[参考 1](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
[参考 2](https://www.jsonrpc.org/specification)

> [Reference 1](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
> [Reference 2](https://www.jsonrpc.org/specification)
