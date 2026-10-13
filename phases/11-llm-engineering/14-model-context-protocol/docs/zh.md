# Model Context Protocol (MCP) · 模型上下文协议（MCP）

> MCP 为 AI 宿主（host）提供一个统一协议，用于发现和调用工具（tool）、资源（resource）与提示（prompt）。2026-07-28 修订版让这个协议变成无状态（stateless）：能力与版本上下文随每个请求携带，而不是放在绑定在连接上的握手（handshake）里。
>
> MCP gives an AI host one protocol for discovering and invoking tools, resources, and prompts. The 2026-07-28 revision makes that protocol stateless: capability and version context travels with every request, not in a connection-bound handshake.

**类型：** Build
**语言：** Python
**先修：** Phase 11 · 09（函数调用）、Phase 11 · 03（结构化输出）
**时间：** 约 75 分钟

## Learning Objectives · 学习目标

- 区分 MCP 的宿主（host）、客户端（client）、服务器（server）、传输（transport）与服务器原语（server primitive）。
- 构建带 MCP 2026-07-28 所需元数据的 JSON-RPC 请求。
- 使用 `server/discover` 检查版本、身份与能力。
- 从工具、资源与提示返回带类型、可缓存感知的结果。
- 解释现代无状态 MCP 如何与握手时代的服务器互操作。
- 为一台服务器选择安全的状态、传输与审批边界。

> Distinguish an MCP host, client, server, transport, and server primitive.
> Build a JSON-RPC request with the metadata required by MCP 2026-07-28.
> Use `server/discover` to inspect versions, identity, and capabilities.
> Return typed and cache-aware results from tools, resources, and prompts.
> Explain how modern stateless MCP interoperates with handshake-era servers.
> Choose safe state, transport, and approval boundaries for a server.

## The Problem · 问题在哪

你的应用需要一个数据库查询、一个日历操作和一个文件读取器。如果没有共享协议，每个 AI 宿主都得为同一批能力各自编写发现、调用、错误处理、传输与授权的胶水代码。

MCP 压缩了这张集成矩阵。服务器发布一个标准的 JSON-RPC 表面（surface）。一个合规的客户端可以发现这个表面、把它呈现给模型或用户、调用它并解释结果，而不需要任何针对特定服务器的适配器。

有一个重要边界很容易被忽略。MCP 标准化的是通信。它不决定模型该调用哪个工具，不会让不可信内容变安全，也不会把无状态请求变成持久的应用状态。这些决策仍然归你的宿主和服务器所有。

> Your application needs a database query, a calendar operation, and a file reader. Without a shared protocol, every AI host needs custom discovery, invocation, errors, transport, and authorization glue for those same capabilities.
> MCP reduces that integration matrix. A server publishes a standard JSON-RPC surface. A compliant client can discover the surface, present it to a model or user, invoke it, and interpret the result without a server-specific adapter.
> The important boundary is easy to miss. MCP standardizes communication. It does not decide which tool the model should call, make untrusted content safe, or turn a stateless request into durable application state. Your host and server still own those decisions.

## The Concept · 概念

![MCP 宿主、无状态请求与服务器原语](../assets/mcp-architecture.svg)

### The three server primitives · 三种服务器原语

1. **工具（Tools）** 是可调用的动作。每个工具都有名字、描述、JSON Schema 输入和一个处理函数（handler）。
2. **资源（Resources）** 是有名字、按 URI 寻址的内容，客户端可以读取。
3. **提示（Prompts）** 是可复用的模板，宿主可以把它们暴露给用户。

宿主是 AI 应用。宿主内的一个 MCP 客户端与一台服务器对话。传输层在两者之间搬运 JSON-RPC 消息。

> Tools are callable actions. Each tool has a name, description, JSON Schema input, and handler.
> Resources are named, URI-addressed content that a client can read.
> Prompts are reusable templates that a host can expose to a user.
> The host is the AI application. An MCP client inside that host speaks to one server. The transport carries JSON-RPC messages between them.

### Stateless requests replace the handshake · 无状态请求取代握手

MCP 2026-07-28 移除了 `initialize` 和 `notifications/initialized`，也移除了协议层会话。每个请求都在 `params._meta` 里携带解释它自身所需的上下文：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {},
      "io.modelcontextprotocol/clientInfo": {
        "name": "lesson-client",
        "version": "1.0.0"
      }
    }
  }
}
```

协议版本与客户端能力是必填项，客户端身份是推荐项。缺失 `_meta`、缺失必填字段、或必填字段类型错误都属于畸形请求，返回 Invalid Params（`-32602`）。版本字符串格式正确但服务器不支持时，返回 `UnsupportedProtocolVersionError`（`-32022`）。服务器处理一个有效请求时，不需要恢复任何先前的协商记录。

无状态并不意味着应用永远不能维护状态。它只是说状态不再藏在 MCP 连接或 `Mcp-Session-Id` 后面。如果某个工作流需要连续性，服务器铸造一个不透明句柄（opaque handle），客户端在后续调用里把它当作普通工具参数传入。每个请求上仍然必须检查授权。

> MCP 2026-07-28 removes `initialize` and `notifications/initialized`. It also removes protocol-level sessions. Every request carries the context needed to interpret it in `params._meta`.
> The protocol version and client capabilities are required. Client identity is recommended. A missing `_meta`, a missing required field, or a required field with the wrong type is malformed and returns Invalid Params (`-32602`). A well-formed version string that the server does not support returns `UnsupportedProtocolVersionError` (`-32022`).
> Stateless does not mean an application can never maintain state. It means that state is not hidden behind an MCP connection or `Mcp-Session-Id`. If a workflow needs continuity, the server mints an opaque handle and the client passes that handle as an ordinary tool argument on later calls. Authorization must still be checked on every request.

### Discovery and version selection · 发现与版本选择

每台现代服务器都实现 `server/discover`。结果会宣告支持的版本、能力与服务器身份：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "complete",
    "supportedVersions": ["2026-07-28"],
    "capabilities": {
      "tools": {},
      "resources": {},
      "prompts": {}
    },
    "ttlMs": 3600000,
    "cacheScope": "public",
    "_meta": {
      "io.modelcontextprotocol/serverInfo": {
        "name": "demo-server",
        "version": "1.0.0"
      }
    }
  }
}
```

客户端可以直接调用别的方法并处理版本错误，但发现（discovery）让能力展示与版本选择变得显式。不支持的版本返回 `UnsupportedProtocolVersionError`，错误码 `-32022`。它的数据里包含 `supported`（服务器修订版本数组）和 `requested`（被拒绝的修订版本）。

在 stdio 上，双时代客户端用 `server/discover` 探测。一个发现结果，或一个可识别的现代错误（例如 `UnsupportedProtocolVersionError`），即表明这是现代服务器。任何未被识别为现代错误的其他错误或超时，都允许回退到 2025-11-25 的 `initialize` 流程。遗留行为是兼容代码，不是现代默认路径。

> Every modern server implements `server/discover`. The result advertises supported versions, capabilities, and server identity.
> A client may call another method directly and handle a version error, but discovery makes capability display and version selection explicit. An unsupported version returns `UnsupportedProtocolVersionError` with code `-32022`. Its data contains `supported`, an array of server revisions, and `requested`, the rejected revision.
> On stdio, a dual-era client probes with `server/discover`. A discovery result or a recognized modern error such as `UnsupportedProtocolVersionError` identifies a modern server. Any error or timeout that is not recognized as modern permits fallback to the 2025-11-25 `initialize` flow. Legacy behavior is compatibility code, not the modern default.

### Results are explicit · 结果是显式的

2026-07-28 的每个核心结果都带 `resultType`：

- `complete` 表示操作已完成。
- `input_required` 表示服务器需要通过多轮请求（Multi Round-Trip Requests，MRTR）模式再走一趟。核心服务器只允许从 `tools/call`、`resources/read` 或 `prompts/get` 返回它。

客户端必须把省略了 `resultType` 的遗留结果当作 complete 处理。

服务器应该在每个结果的 `_meta` 里带上 `io.modelcontextprotocol/serverInfo`。这个身份是自我上报的，用于展示、日志和调试，不用于安全决策。

列举与读取结果还携带 `ttlMs` 和 `cacheScope`。确定性的 `tools/list` 顺序加上新鲜度提示，让客户端可以安全地缓存发现结果，并提升提示缓存（prompt cache）的稳定性。`cacheScope: public` 允许共享缓存；`private` 把重用限制在调用上下文内。

> Every core 2026-07-28 result has `resultType`: `complete` means the operation finished; `input_required` means the server needs another round trip through the Multi Round-Trip Requests pattern. Clients must treat a legacy result that omits `resultType` as complete.
> Servers should include `io.modelcontextprotocol/serverInfo` in every result's `_meta`. This identity is self-reported and is for display, logging, and debugging, not for security decisions.
> List and read results also carry `ttlMs` and `cacheScope`. A deterministic `tools/list` order plus a freshness hint lets clients cache discovery safely and improves prompt-cache stability. `cacheScope: public` permits shared caching; `private` confines reuse to the calling context.

### The wire format and transport · 线上格式与传输

MCP 在 stdio 或 Streamable HTTP 之上使用 JSON-RPC 2.0。

- 请求有 `jsonrpc`、`id`、`method` 和 `params`。
- 响应有匹配的 `id`，以及 `result` 或 `error` 之一。
- 通知（notification）没有 `id`，也不期待响应。

现代 Streamable HTTP 暴露一个接受 POST 的端点。每条 JSON-RPC 消息各用一次 POST。请求 POST 收到的要么是一个 JSON 对象，要么是一个请求级（request-scoped）的 Server-Sent Events 流，以最终响应结尾。被接受的通知 POST 返回 HTTP 202、无响应体；本核心修订版没有定义任何基于 Streamable HTTP 的客户端到服务器通知。

2026-07-28 里没有独立的 MCP GET 流、DELETE 会话端点、`Mcp-Session-Id`，也没有 `Last-Event-ID` 重放。长期存在的变更通知使用一个 `subscriptions/listen` POST，其响应保持打开为 SSE 流。

> MCP uses JSON-RPC 2.0 over stdio or Streamable HTTP. A request has `jsonrpc`, `id`, `method`, and `params`. A response has the matching `id` and either `result` or `error`. A notification has no `id` and expects no response.
> Modern Streamable HTTP exposes one endpoint that accepts POST. Each JSON-RPC message gets its own POST. A request POST receives either one JSON object or a request-scoped Server-Sent Events stream that ends with the final response.
> There is no standalone MCP GET stream, DELETE session endpoint, `Mcp-Session-Id`, or `Last-Event-ID` replay in 2026-07-28. Long-lived change notifications use a `subscriptions/listen` POST whose response remains open as an SSE stream.

### Client input without server-initiated requests · 无服务器发起请求时的客户端输入

更老的修订版允许服务器通过流发送 `sampling/createMessage`、`roots/list` 或 `elicitation/create` 之类的请求。当前协议改用多轮请求（MRTR）。一次符合条件的工具调用、资源读取或提示获取会返回 `resultType: input_required`，并带有 `inputRequests` 或 `requestState` 中的至少一个。客户端收集所有被请求的输入，用新的 JSON-RPC ID 和对应的 `inputResponses` 重试原始方法；如果之前提供了 `requestState`，就原样回显它。如果没有出现 `inputRequests`，重试时省略 `inputResponses`。

Roots、Sampling 与 Logging 仍然可用但已弃用（deprecated），新实现不应再采用。现有的 Roots 或 Sampling 请求被放进 MRTR 的 `inputRequests` 里，绝不再作为独立的服务器到客户端 JSON-RPC 请求出现。优先选择显式的文件或目录参数、资源 URI、服务器配置，以及直接的模型服务商集成。stdio 诊断写到 stderr，生产遥测用 OpenTelemetry。

```figure
mcp-nxm-collapse
```

> Older revisions let a server send requests such as `sampling/createMessage`, `roots/list`, or `elicitation/create` over a stream. The current protocol uses Multi Round-Trip Requests instead. An eligible tool call, resource read, or prompt get returns `resultType: input_required` with at least one of `inputRequests` or `requestState`.
> Roots, Sampling, and Logging remain functional but are deprecated, so new implementations should not adopt them. Existing Roots or Sampling requests travel inside MRTR `inputRequests`, never as independent server-to-client JSON-RPC requests.

## Build It · 动手造

### Step 1: register a server surface · 注册服务器表面

虽然请求契约变了，注册仍然保持简单：

```python
server = MCPServer("demo-server")

@server.tool(
    "add",
    "Add two integers.",
    {
        "type": "object",
        "properties": {
            "a": {"type": "integer"},
            "b": {"type": "integer"}
        },
        "required": ["a", "b"]
    }
)
def add(a: int, b: int) -> dict:
    return {"sum": a + b}
```

`code/main.py` 里随课发布的实现还注册了一个资源和一个提示。它刻意只用标准库，让你能看清每一个信封（envelope），而不是把协议委托给某个 SDK。

> Registration stays simple even though the request contract changed.
> The shipped implementation in `code/main.py` also registers a resource and prompt. It deliberately uses the standard library so you can see each envelope rather than delegating the protocol to an SDK.

### Step 2: attach metadata to every request · 给每个请求附加元数据

```python
def request(method, params=None):
    body_params = dict(params or {})
    body_params["_meta"] = {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {},
        "io.modelcontextprotocol/clientInfo": {
            "name": "demo-client",
            "version": "1.0.0"
        }
    }
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": body_params
    }
```

不要把这些元数据只缓存在某个连接对象里。服务器会在每个请求上校验它。

> Do not cache this metadata only in a connection object. The server validates it on each request.

### Step 3: optionally discover before listing · 列举前可选地先发现

先调用 `server/discover`，选一个支持的版本，然后调用 `tools/list`。如果你已经知道版本并能处理 `-32022`，直接 `tools/list` 也是合法的。

本课演示按名称顺序返回工具列表，并附带 `ttlMs`、`cacheScope`、`resultType` 和服务器身份。工具调用返回 complete 且不可缓存的结果，因为它的输出可能依赖当前状态。

> Call `server/discover`, choose a supported version, then call `tools/list`. A direct `tools/list` is also valid if you already know the version and can handle `-32022`.
> The demo returns tool lists in name order and attaches `ttlMs`, `cacheScope`, `resultType`, and server identity. A tool call returns a complete, non-cacheable result because its output can depend on current state.

### Step 4: map the same request to HTTP · 把同一请求映射到 HTTP

远程 `tools/call` 的 POST 带有与 JSON-RPC 体相镜像的头：

```http
POST /mcp HTTP/1.1
Content-Type: application/json
Accept: application/json, text/event-stream
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: add
```

`MCP-Protocol-Version` 头必须与 `_meta` 里的版本一致。`Mcp-Method` 在每个 JSON-RPC 请求上都必填，且必须与 `method` 一致。`Mcp-Name` 只在 `tools/call`、`resources/read` 和 `prompts/get` 上必填，必须分别与工具名、资源 URI 或提示名一致。缺失必填头或不匹配返回 HTTP 400，错误码 `HeaderMismatch`（`-32020`）。

> The `MCP-Protocol-Version` header must match the version in `_meta`. `Mcp-Method` is required on every JSON-RPC request and must match `method`. `Mcp-Name` is required only for `tools/call`, `resources/read`, and `prompts/get`, where it must match the tool name, resource URI, or prompt name. A missing required header or mismatch returns HTTP 400 with `HeaderMismatch` code `-32020`.

### Step 5: enforce safety outside protocol state · 在协议状态之外强制安全

- 在每个 HTTP 请求上校验授权（authorization）与受众（audience）。
- 把本地服务器绑定到 localhost，并在 Streamable HTTP 上校验 `Origin`。
- 给会改动状态的工具标 `destructiveHint: true`，并要求宿主审批。
- 显式传递目录与文件范围，而不是依赖已弃用的 Roots。
- 把资源和工具输出当作不可信数据。
- stdio 下把 stdout 保留给 JSON-RPC；诊断写到 stderr。

> Validate authorization and audience on every HTTP request.
> Bind local servers to localhost and validate `Origin` on Streamable HTTP.
> Mark mutating tools with `destructiveHint: true` and require host approval.
> Pass directory and file scope explicitly instead of depending on deprecated Roots.
> Treat resources and tool output as untrusted data.
> Keep stdout reserved for JSON-RPC under stdio; write diagnostics to stderr.

## Use It · 实战用法

在本课目录下运行：

```bash
python3 code/main.py
cd code
python3 -m unittest discover tests -v
```

第一行应该报告在协议 `2026-07-28` 上发现了 `demo-server`。然后查看 `MCPClient.request`：它为每次调用重建 `_meta`。从某个请求里删掉元数据，观察服务器拒绝它。

> The first line should report discovery of `demo-server` at protocol `2026-07-28`. Then inspect `MCPClient.request`: it reconstructs `_meta` for every call. Remove the metadata from one request and observe the server reject it.

## Ship It · 交付

`outputs/skill-mcp-server-designer.md` 把一个领域变成一份无状态 MCP 设计。它的验收门槛要求：一个发现结果、按请求的元数据策略、确定性且缓存友好的列表、显式的状态句柄、传输头、授权与审批规则。

> `outputs/skill-mcp-server-designer.md` turns a domain into a stateless MCP design. Its acceptance gate requires a discovery result, per-request metadata policy, deterministic cache-aware lists, explicit state handles, transport headers, authorization, and approval rules.

## Continue the MCP Deep Dive · 继续 MCP 深潜

本课给了你协议模型。Phase 13 把四个生产边界拆成独立的「构建并验证」课程：

1. [MCP Tool Contracts and Content](../../../13-tools-and-protocols/28-mcp-tool-contracts-and-content/docs/en.md) 讲封闭的输入 schema、结构化内容、路由元数据、不透明分页、完成授权，以及协议错误与工具域错误的区别。
2. [MCP Reliability, Cancellation, and Flow Control](../../../13-tools-and-protocols/29-mcp-reliability-cancellation-and-flow-control/docs/en.md) 讲请求取消、持久任务取消、截止时间、幂等性、背压、代理缓冲与重连行为。
3. [MCP Registry Supply Chain, Admission, Drift, and Rollback](../../../13-tools-and-protocols/30-mcp-registry-supply-chain-and-drift/docs/en.md) 讲命名空间证明、制品来源、不可变 pin、运行期漂移、Registry 状态、准入证据与回滚。
4. [MCP Conformance Engineering](../../../13-tools-and-protocols/31-mcp-conformance-versioning-and-operations/docs/en.md) 讲黄金与负向线上报文（wire transcript）、严格版本时代、SDK 差异、代理证据、脱敏、健康门与发布回滚。

当服务器要跨过团队或信任边界时，按顺序学它们。合在一起，它们把你从「方法能跑通」带到「契约在部署全程保持安全且可诊断」。

> This lesson gives you the protocol model. Phase 13 turns four production boundaries into separate build-and-verify lessons.
> Follow them in order when the server will cross a team or trust boundary. Together they move from “the method works” to “the contract remains safe and diagnosable through deployment.”

## Exercises · 练习

1. 加一个 `subtract` 工具，确认 `tools/list` 仍保持字母序。
2. 移除协议版本键，验证 Invalid Params（`-32602`）。然后发送格式正确但不被支持的版本 `2025-11-25`，验证 `-32022`，确认 `requested` 回显该版本，并从 `supported` 中选择。
3. 给一个创建操作加上服务器铸造的 `draftId`，然后把它设为更新操作的必填参数。解释为什么这是应用状态而不是协议会话。
4. 让一个需要用户确认的工具返回 `input_required`。用新 ID、一个 `inputResponses` 条目和原样的 `requestState` 重试原始调用，而不是发明一个服务器到客户端的 JSON-RPC 请求。
5. 画一个双时代 stdio 客户端的草图。把结果或可识别的现代错误视为现代服务器，只对未识别的错误或超时允许回退到 `initialize`。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|------------------------|
| MCP | “LLM 的工具协议” | 用于服务器发现、工具、资源、提示与扩展的 JSON-RPC 协议 |
| Host（宿主） | “那个 AI 应用” | 拥有模型与 UI，并挂载一个或多个 MCP 客户端 |
| Client（客户端） | “连接器” | 代表宿主与一台服务器说 MCP |
| Stateless MCP（无状态 MCP） | “没有会话” | 每个请求自带版本与能力；没有任何协议状态以连接为键 |
| `server/discover` | “能力探针” | 必需的服务器方法，宣告版本、能力与身份 |
| `resultType` | “结果状态” | 把结果标记为 `complete` 或 `input_required` |
| State handle（状态句柄） | “工作流 id” | 服务器铸造、作为普通参数传递的应用标识符 |
| Streamable HTTP | “远程传输” | 一个 POST 端点，返回 JSON 或请求级 SSE 响应 |
| MRTR | “先问再重试” | 嵌在结果里的输入请求，随后对原始操作做一次重试 |

## Further Reading · 延伸阅读

- [MCP 2026-07-28 key changes](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [MCP server discovery](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
- [MCP Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [MCP Multi Round-Trip Requests](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [MCP deprecated features](https://modelcontextprotocol.io/specification/2026-07-28/deprecated)
