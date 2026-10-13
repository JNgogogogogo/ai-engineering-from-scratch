# Expose REST and MCP tools · 暴露 REST 与 MCP tools

第 4 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 4 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

绑定一个本地服务器，要求 bearer token，限制请求体大小，并实现 health、REST 写入/搜索，以及跑在 JSON-RPC POST 之上的 MCP initialization/tools 子集。工具执行失败用一个成功的 JSON-RPC 响应内部的 `isError` 表达；未知的协议方法才用 JSON-RPC error。这是一个教学子集：没有会话（session）、没有流式（streaming）、也不是生产级认证。要测试真实的 HTTP 字节，这样序列化才丢不掉 source 或 revision。

本阶段的边界是 `createMemoryServer`。保持之前阶段的行为不变：最终评分器会在同一个 workspace 上运行每一个阶段。

> Bind a local server, require a bearer token, bound request bodies, and implement health, REST writes/search and the MCP initialization/tools subset over JSON-RPC POST. Tool execution failures use isError inside a successful JSON-RPC response; unknown protocol methods use a JSON-RPC error. ... This is a teaching subset without sessions, streaming or production authentication. Test actual HTTP bytes so serialization cannot drop source or revision.

## Work through one concrete case · 走一遍具体案例

常驻 CLI 选一个保留数据的目录，并只绑定 127.0.0.1。一次 REST 写入和一次 MCP `tools/call memory_search` 用的是同一个 MemoryStore，所以 source 和 revision 必须在两条序列化路径上都活下来。

```figure
pj-memory-server-4
```

修改实验（lab）的输入，先自己算出结果，再去看它的指标。图中数字由这些输入计算而来；下面的实现测试仍然是完成与否的证据来源。

> The persistent CLI chooses a retained directory and binds only 127.0.0.1. A REST write and an MCP tools/call memory_search use the same MemoryStore, so source and revision must survive both serialization paths. ... Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的 workspace `main.ts` 里实现 `createMemoryServer`。先自己尝试契约，之后再去读参考实现中导出的类型。保留起始代码的公开名称，测试才能调用你的实现。核心函数返回结构化值，不要在核心函数内部打印；最终结果由 CLI 打印。

使用[公开的 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示交给随附的 driver。

以字节为单位收集 body 分块，等完整请求到达后再一次性做 UTF-8 解码，这样被网络分块劈开的码点也能保持完整。把入站 body 限制在 50,000 字节。超出限制就返回 HTTP 413，附上 `{"error":"body too large"}` 和 `Connection: close`；未完成的上传不能让连接一直开着。

通过 `MEMORY_TOKEN` 设置 bearer token，并且绝不打印它。用一个受支持的版本初始化，检查完整的 `memory_put` schema，然后发送畸形参数，确认收到的是工具级的 `isError` 响应。

> Implement `createMemoryServer` in your workspace `main.ts`. ... Collect body chunks as bytes and decode UTF-8 once after the complete request arrives, so a code point split between network chunks stays intact. Limit the incoming body to 50,000 bytes. ... Set the bearer token through MEMORY_TOKEN and never print it. Initialize with a supported version, inspect the complete memory_put schema, then send malformed arguments to confirm a tool-level isError response.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py memory-server --init learning-artifacts/memory-server` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py memory-server --stage 4 --path learning-artifacts/memory-server --strict
```

全新的 workspace 在你实现契约之前应当判为失败。每个阶段完成后，用随附的样例运行你的真实产物：

```bash
cd learning-artifacts/memory-server
node cli.ts --data-dir memory-data --put samples/memory.json
node cli.ts --data-dir memory-data --query "cache policy"
node cli.ts --data-dir memory-data --history cache-policy
```

> From the repository root, initialize once with `python3 scripts/project_test.py memory-server --init learning-artifacts/memory-server`. Then grade cumulatively ... A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample.

## Investigate the failure boundary · 探查失败边界

用同一个目录重启服务，再查询之前那条记录。把重启持久性（restart persistence）与多写者加锁、断电持久性区分开——后两者这套日志并不提供。

每个数据目录只用一个写者进程。追加式 JSONL 提供的是重启持久性，不是断电或多进程事务保证。哈希出来的词法向量不是语义 embedding。MCP HTTP 是有文档记载的 tools 子集，没有流式，也没有会话。

> Restart the service with the same directory and query the prior record. Distinguish restart persistence from multi-writer locking and power-loss durability, which this log does not provide. ... Use one writer process per data directory. Appended JSONL is restart persistence, not a power-loss or multi-process transaction guarantee.

## References · 参考资料

[MCP tools 规范](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
[Rust 标准库](https://doc.rust-lang.org/std/)
[Node HTTP API](https://nodejs.org/api/http.html)

## Optional standard MCP client verification · 可选：用标准 MCP 客户端验证

可选路线用 `mcp==2.1.1`（已安装的官方 Python 客户端）来打这个项目真实的 loopback HTTP 服务器。它协商的是声明中的 2025-11-25 legacy tools 契约。这并不代表支持每一个更新的协议特性。

```bash
python3 -m venv .venv-mcp
.venv-mcp/bin/python -m pip install -r projects/memory-server/requirements-framework.txt
.venv-mcp/bin/python scripts/project_test.py memory-server --all --solution --optional --strict
```

用 `--path learning-artifacts/memory-server` 让同一个客户端跑你的实现。默认路线保持纯标准库；缺少可选包会产出 SKIP，而 SKIP 会让 strict 的可选评分判为失败。

> The optional track uses `mcp==2.1.1`, the installed official Python client, against this project's actual loopback HTTP server. It negotiates the declared 2025-11-25 legacy tools contract. This does not establish support for every newer protocol feature. ... Use `--path learning-artifacts/memory-server` to run the same client against your implementation. The default track stays standard-library-only; missing optional packages produce SKIP, which fails strict optional grading.

