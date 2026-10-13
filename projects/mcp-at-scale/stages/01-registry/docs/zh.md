# Build a catalog of 250 read-only tools · 构建 250 个只读工具的目录

Stage 1 of 5。开始之前，先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 1 of 5. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

为 50 种资源各创建五个窄作用域的只读操作。名称和 schema 是稳定的；执行时读取的是注入的 inventory，而不是去联系一个集群。tool schema 定义了被接受的确切键和值，因此未知参数永远不会意外抵达 handler。

> Create five narrowly scoped read operations for each of 50 resource kinds. The names and schemas are stable; execution reads an injected inventory rather than contacting a cluster. A tool schema defines the exact accepted keys and values, so an unknown argument never reaches a handler by accident.

## Work through one concrete case · 走一个具体例子

50 个资源族乘以 5 个操作得到 250 个教学工具，但它们全部共享同一个本地 inventory 机制。一份只包含 pods 的 inventory 暴露出五个有用的资源工具；组合后的 server 再加上 catalog_search 作为第六个。

```figure
pj-mcp-at-scale-1
```

修改实验输入，先自己算出结果，再去读它的指标。figure 会根据这些输入计算；下面的实现测试仍然是完成证据的来源。

> Fifty resource families times five operations produce 250 teaching tools, but all share one local inventory mechanism. A supplied inventory containing only pods exposes five useful resource tools; the composed server adds catalog_search as the sixth.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

实现 `registry.py`：`catalog`、`execute`。这个 artifact 是 MCP Server With 250 Tools 的 stage 1。它消费显式输入，返回一个可检查的结果，供下一个 stage 使用。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只返回值；文件输入、参数解析和展示交给提供的 driver。

把公开的 name、description 和 inputSchema 与内部的 resource/operation 元数据分开保管。在查询 inventory 之前先校验确切的参数键。

> Implement `registry.py`: `catalog`, `execute`. This artifact is stage 1 of MCP Server With 250 Tools. It consumes explicit inputs and returns an inspectable result that the next stage can use.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Keep public name, description and inputSchema separate from internal resource/operation metadata. Validate exact argument keys before consulting inventory.

## Verify and inspect · 验证与检查

在仓库根目录用 `python3 scripts/project_test.py mcp-at-scale --init learning-artifacts/mcp-at-scale` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py mcp-at-scale --stage 1 --path learning-artifacts/mcp-at-scale --strict
```

全新工作区在你实现契约之前应该保持失败。每个阶段完成后，用提供的样例运行你真实的 artifact：

```bash
cd learning-artifacts/mcp-at-scale
python3 cli.py samples/inventory.json --query "pods count" --max-chars 500
```

> From the repository root, initialize once with `python3 scripts/project_test.py mcp-at-scale --init learning-artifacts/mcp-at-scale`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

给 pods_search 传入 {query:"worker",extra:true}。它必须失败，而不是悄悄忽略一个未被认可的指令。

> Pass {query:"worker",extra:true} to pods_search. It must fail rather than quietly ignoring an unrecognized instruction.

## References · 参考资料

[参考 1](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
[参考 2](https://www.jsonrpc.org/specification)

> [Reference 1](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
> [Reference 2](https://www.jsonrpc.org/specification)
