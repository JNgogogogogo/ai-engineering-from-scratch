# Exercise the real wire with a typed client · 用 typed client 走一遍真实的线路

Stage 5 of 5。开始之前，先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 5 of 5. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

父进程与子进程的内存是分开的。序列化请求、保留它们的 id，并在解析之后把响应关联起来。初始化通知有意不带 id，也收不到响应。期望「一行输入对应一行输出」的 client 会挂住。

同时限制已流逝时间和累计输出。服务器可能停摆或无限打印，所以只有响应超时并不够。检查退出码，并让 stderr 与 JSON 输出保持分离。在创建进程之前拒绝重复的出站 id。

> The parent and child have separate memory. Serialize requests, preserve their ids, and correlate replies after parsing. Initialization notifications intentionally have no id and receive no response. A client that expects one line per input line will hang.
> Bound both elapsed time and accumulated output. A server can stall or print forever, so a response timeout alone is insufficient. Check the exit code and keep stderr separate from JSON output. Reject duplicate outgoing ids before creating the process.

## Work through one concrete case · 走一个具体例子

typed client 启动一个独立的 Python 进程，在请求发完后关闭 stdin，并校验响应 id。组合出的 CLI 也可以为 stdio MCP client 持续 serve 你提供的 inventory。

```figure
pj-mcp-at-scale-5
```

修改实验输入，先自己算出结果，再去读它的指标。figure 会根据这些输入计算；下面的实现测试仍然是完成证据的来源。

> The typed client starts a separate Python process, closes stdin after its requests and validates response ids. The composed CLI can instead serve your supplied inventory continuously for a stdio MCP client.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

实现阶段测试和 API 契约中点名的公开接口。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只返回值；文件输入、参数解析和展示交给提供的 driver。

让 stderr 与协议 stdout 保持分离。限制时间和累计输出，在超时或响应畸形时杀掉子进程。typed 的 Response 注解在运行时并不能校验外部 JSON。

> Implement the public interfaces named in the stage tests and API contract.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Keep stderr separate from protocol stdout. Bound time and accumulated output, and kill the child on a timeout or malformed response. A typed Response annotation cannot validate external JSON at runtime.

## Verify and inspect · 验证与检查

在仓库根目录用 `python3 scripts/project_test.py mcp-at-scale --init learning-artifacts/mcp-at-scale` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py mcp-at-scale --stage 5 --path learning-artifacts/mcp-at-scale --strict
```

全新工作区在你实现契约之前应该保持失败。每个阶段完成后，用提供的样例运行你真实的 artifact：

```bash
cd learning-artifacts/mcp-at-scale
python3 cli.py samples/inventory.json --query "pods count" --max-chars 500
```

> From the repository root, initialize once with `python3 scripts/project_test.py mcp-at-scale --init learning-artifacts/mcp-at-scale`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

运行完整的 stdio 集成回归：initialize、notify、pods_count。然后在同一条边界上检查 catalog_search，并记录它精确的上下文字符数。

stdio transport 实现的是文档化的 2025-06-18 与 2025-11-25 initialization/tools 子集。这不是对当前完整 MCP 一致性的声明。inventory 读取的是本地录制；生成的工具数量并非 250 个不同的集成。

> Run the full stdio integration regression: initialize, notify, pods_count. Then inspect catalog_search over the same boundary and retain its exact context character count.
> The stdio transport implements the documented 2025-06-18 and 2025-11-25 initialization/tools subset. It is not a claim of full current MCP conformance. Inventory reads are local recordings; the generated tool count is not 250 distinct integrations.

## References · 参考资料

[MCP stdio 传输](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)

> [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)

## Optional standard MCP client verification · 可选：标准 MCP client 验证

可选路线使用 `mcp==2.1.1`（已安装的官方 Python client），针对本项目真实的 stdio 进程。它协商的是已声明的 2025-11-25 legacy tools 契约。这并不建立对每个更新协议特性的支持。

```bash
python3 -m venv .venv-mcp
.venv-mcp/bin/python -m pip install -r projects/mcp-at-scale/requirements-framework.txt
.venv-mcp/bin/python scripts/project_test.py mcp-at-scale --all --solution --optional --strict
```

使用 `--path learning-artifacts/mcp-at-scale` 可以让同一个 client 针对你的实现运行。默认路线保持只用标准库；缺少可选包会产生 SKIP，而 SKIP 会让 strict 可选评分失败。

> The optional track uses `mcp==2.1.1`, the installed official Python client, against this project's actual stdio process. It negotiates the declared 2025-11-25 legacy tools contract. This does not establish support for every newer protocol feature.
> Use `--path learning-artifacts/mcp-at-scale` to run the same client against your implementation. The default track stays standard-library-only; missing optional packages produce SKIP, which fails strict optional grading.
