# MCP Fundamentals: Stateless Requests and JSON-RPC · MCP 基础：无状态请求与 JSON-RPC

> Modern MCP has no handshake and no protocol session. Each request must carry enough metadata to be understood, authorized, routed, and retried on its own.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 13, Lessons 01 through 05
**Time:** ~55 minutes

## Learning Objectives · 学习目标

- 区分 MCP 的服务端原语（server primitives）与客户端侧特性。
- 为 MCP `2026-07-28` 构造合法的 JSON-RPC 2.0 请求与响应。
- 在每个请求上附带协议版本、客户端能力（client capabilities）与客户端身份（client identity）。
- 无需握手即可使用 `server/discover` 并处理 `UnsupportedProtocolVersionError`。
- 追踪一个独立请求从校验到完整结果的全过程。

> Distinguish MCP's server primitives from its client-side features.
> Build valid JSON-RPC 2.0 requests and responses for MCP `2026-07-28`.
> Attach protocol version, client capabilities, and client identity to every request.
> Use `server/discover` and handle `UnsupportedProtocolVersionError` without a handshake.
> Trace one independent request from validation through a complete result.

## The Problem · 问题所在

同一个进程或 HTTP worker 可能先后收到来自不同客户端、携带不同能力的两个请求。如果服务器记住了上一个请求声明的内容，就可能应用错误的权限，或返回错误的线上格式（wire shape）。

MCP `2026-07-28` 消除了这种歧义。协议核心是无状态的（stateless）。服务器必须依据当前请求本身来决定如何处理它，而不是依据连接历史。

这改变了心智模型。旧流程是：先建连接，再握手，然后才是操作。现代流程更简单：

1. 客户端发送一个自描述（self-describing）的请求。
2. 服务器校验该请求的版本与能力。
3. 服务器处理该方法。
4. 服务器返回一个带类型的结果或一个 JSON-RPC 错误。

下一个请求从头重复同样的流程。

> An MCP server can receive two consecutive requests from different clients, with different capabilities, on the same process or HTTP worker. If the server remembers what the previous request declared, it can apply the wrong permissions or return the wrong wire shape.
> MCP `2026-07-28` removes that ambiguity. The protocol core is stateless. A server must decide how to handle the current request from the current request, not from connection history.
> This changes the mental model. The old sequence was connection first, handshake second, operations third. The modern sequence is simpler:
> 1. The client sends a self-describing request.
> 2. The server validates that request's version and capabilities.
> 3. The server handles the method.
> 4. The server returns a typed result or a JSON-RPC error.
> The next request repeats the same process from scratch.

## The Concept · 核心概念

### Server primitives · 服务端原语

MCP 服务器对外暴露三类主要原语：

1. **Tools（工具）** 是由模型控制的活动，用 `tools/list` 发现，用 `tools/call` 调用。
2. **Resources（资源）** 是以 URI 寻址的数据，用 `resources/list` 发现，用 `resources/read` 读取。
3. **Prompts（提示模板）** 是可复用的模板，用 `prompts/list` 发现，用 `prompts/get` 渲染。

Roots、sampling 和 logging 出于兼容性仍保留在 `2026-07-28` schema 中，但已被弃用（deprecated）。新的实现应当：roots 改用显式的工具或资源输入，sampling 直接调用模型提供商的 API，logging 改用 stderr 或 OpenTelemetry。Elicitation（信息征集）仍可通过多轮往返请求（Multi Round-Trip Requests）实现：服务器返回一个输入请求，客户端补齐后重试原操作。现代服务器绝不会主动发起独立的 JSON-RPC 请求。

> MCP servers expose three primary primitives:
> 1. **Tools** are model-controlled actions, discovered with `tools/list` and invoked with `tools/call`.
> 2. **Resources** are URI-addressed data, discovered with `resources/list` and retrieved with `resources/read`.
> 3. **Prompts** are reusable templates, discovered with `prompts/list` and rendered with `prompts/get`.
> Roots, sampling, and logging remain in the `2026-07-28` schema for compatibility, but they are deprecated. ... Elicitation remains available through Multi Round-Trip Requests, where a server returns an input request and the client retries the original operation. A modern server never starts an independent JSON-RPC request.

### JSON-RPC envelopes · JSON-RPC 信封

MCP 使用 JSON-RPC 2.0：

- 请求（Request）：`{jsonrpc, id, method, params}`
- 响应（Response）：`{jsonrpc, id, result}` 或 `{jsonrpc, id, error}`
- 通知（Notification）：`{jsonrpc, method, params}`，没有 `id`

请求中的 `id` 用来关联一个响应。它并不创建协议会话。

> MCP uses JSON-RPC 2.0:
> - Request: `{jsonrpc, id, method, params}`
> - Response: `{jsonrpc, id, result}` or `{jsonrpc, id, error}`
> - Notification: `{jsonrpc, method, params}` with no `id`
> The request `id` correlates one response. It does not create a protocol session.

### Required request metadata · 必需的请求元数据

每个现代请求都在 `params` 里携带一个 `_meta` 对象：

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/list",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {},
      "io.modelcontextprotocol/clientInfo": {
        "name": "course-client",
        "version": "1.0.0"
      }
    }
  }
}
```

协议版本和客户端能力是必需的。客户端身份是推荐项。它是自报的展示与调试信息，不是安全凭证。

服务器不得从更早的请求、stdio 进程、HTTP 连接或单独的传输层头部推断这些值中的任何一个。

> Every modern request carries a `_meta` object inside `params`:
> The protocol version and client capabilities are required. Client identity is recommended. It is self-reported display and debugging data, not a security credential.
> The server must not infer any of these values from an earlier request, a stdio process, an HTTP connection, or a transport header alone.

### Complete results and server identity · 完整结果与服务器身份

每个成功的现代结果都包含 `resultType`。正常的最终结果使用 `"complete"`。服务器还应在结果元数据中标明自己的身份：

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {
    "resultType": "complete",
    "tools": [],
    "ttlMs": 30000,
    "cacheScope": "public",
    "_meta": {
      "io.modelcontextprotocol/serverInfo": {
        "name": "notes-server",
        "version": "1.0.0"
      }
    }
  }
}
```

`tools/list`、`resources/list`、`prompts/list`、`resources/templates/list`、`resources/read` 和 `server/discover` 是可缓存（cacheable）的结果，它们带有 `ttlMs` 和 `cacheScope`。安全的默认值是 `ttlMs: 0` 与 `cacheScope: "private"`。列表项应当具有确定性排序（deterministic ordering），这样等价的响应才能产生稳定的缓存键和稳定的模型上下文。

> Every successful modern result includes `resultType`. A normal final result uses `"complete"`. Servers should also identify themselves in result metadata:
> `tools/list`, `resources/list`, `prompts/list`, `resources/templates/list`, `resources/read`, and `server/discover` are cacheable results. They include `ttlMs` and `cacheScope`. A safe default is `ttlMs: 0` and `cacheScope: "private"`. List items should have deterministic ordering so equivalent responses produce stable cache keys and stable model context.

### Discovery without a handshake · 无需握手的发现

每个现代服务器都必须实现 `server/discover`。客户端可以在调用其他方法之前先调用它，以获取：

- `supportedVersions`
- 服务器的 `capabilities`（能力）
- 可选的使用说明 `instructions`
- 结果 `_meta` 中的服务器身份
- 缓存提示（cache hints）

发现（discovery）很有用，但它不是一道门。客户端可以直接先发 `tools/list`，因为这个请求本身已经携带了协议版本与能力。

如果请求的版本不受支持，服务器返回 JSON-RPC 错误码 `-32022`，并附带：

```json
{
  "requested": "2027-01-01",
  "supported": ["2026-07-28"]
}
```

客户端选择一个双方都支持的现代版本，并用一个新的 JSON-RPC 请求 id 重试。

> Every modern server must implement `server/discover`. The client may call it before another method to retrieve:
> - `supportedVersions`
> - server `capabilities`
> - optional usage `instructions`
> - server identity in result `_meta`
> - cache hints
> Discovery is useful, but it is not a gate. A client can send `tools/list` first because that request already carries its protocol version and capabilities.
> If the requested version is unsupported, the server returns JSON-RPC code `-32022` with:
> The client selects a mutually supported modern version and retries with a new JSON-RPC request id.

### One request lifecycle · 单个请求的生命周期

按下面的顺序追踪一个现代请求：

1. 解析一个 JSON-RPC 信封。
2. 确认 `jsonrpc` 是 `"2.0"`、存在 `id`、`method` 是字符串、`params` 是对象。
3. 要求 `params._meta` 里有版本字符串和能力对象；元数据畸形或缺失即 `-32602`。
4. 在 HTTP 边界上，把版本、方法以及适用的名称头部与请求体比对。只要不一致就是 `-32020`，即使其中一个版本值本身不受支持。
5. 确认一致之后，对一致但不受支持的版本返回 `-32022`。
6. 检查所需能力，然后按 `method` 路由并校验该方法特有的参数。
7. 在处理器运行之前完成对该具体操作的认证与授权。
8. 返回带有服务器身份的完整结果。
9. 丢弃请求作用域的协议元数据。

这个顺序防止两个组件各自解释不同的调用。网关不能在授权 `Mcp-Name: notes.read` 的同时让源站执行 `params.name: notes.delete`。它还把畸形输入、头部不一致、版本协商、能力缺失、授权失败和处理器失败保持为彼此可区分的证据。

关闭 stdin 或 HTTP 响应只是结束传输层活动。它不会终止协议会话，因为现代 MCP 根本没有协议会话。

> Trace a modern request in this order:
> That order prevents two components from interpreting different calls. A gateway must not authorize `Mcp-Name: notes.read` while the origin executes `params.name: notes.delete`. It also keeps malformed input, header confusion, version negotiation, capability failure, authorization, and handler failure as distinct evidence.
> Closing stdin or an HTTP response ends transport activity. It does not terminate a protocol session because modern MCP has no protocol session.

### Explicit legacy compatibility · 显式的旧版兼容

`2025-11-25` 及更早的版本使用 `initialize`、`notifications/initialized`、连接作用域的能力，以及在早期 Streamable HTTP 上可选的协议会话。当双时代（dual-era）客户端与旧服务器通信时，这些行为仍然相关。

把两个时代分开。现代请求由必需的逐请求元数据标识；旧式连接只能通过文档规定的回退路径选择。不要把发送 `initialize` 当作面对 `2026-07-28` 服务器的默认行为。

因此，“无状态”具有时代特定的含义。在 `2026-07-28` 中，它是一条协议不变量：每个普通请求都可以被独立解释，且不存在 MCP 会话。在 `2025-11-25` 及更早版本中，初始化与协商的能力属于连接，因此兼容适配器可以保留那种旧式连接状态。双时代实现不是一台宽容的状态机，而是一个无状态的现代核心旁边放着一个隔离的旧版适配器，并在任何一个解析器运行之前做出显式的选择决策。

这两种含义都不禁止持久化的应用状态。工作流、任务或草稿可以放在共享存储里，由一个不透明句柄（opaque handle）指代。客户端把该句柄作为普通输入发送，每个副本都对其使用进行认证与授权。协议上下文不得泄漏进那个存储、充当被移除会话的替代品。

```figure
mcp-tool-call
```

> Versions through `2025-11-25` use `initialize`, `notifications/initialized`, connection-scoped capabilities, and, on earlier Streamable HTTP, optional protocol sessions. That behavior is still relevant when a dual-era client talks to an old server.
> Keep the eras separate. A modern request is identified by the required per-request metadata. A legacy connection is selected only through the documented fallback path. Do not send `initialize` as the default for a `2026-07-28` server.
> “Stateless” therefore has an era-specific meaning. In `2026-07-28`, it is a protocol invariant: every ordinary request is independently interpretable and no MCP session exists. ... A dual-era implementation is not one permissive state machine. It is a stateless modern core beside an isolated legacy adapter, with an explicit selection decision before either parser runs.
> Neither meaning forbids durable application state. A workflow, task, or draft can live behind an opaque handle in a shared store.

## Use It · 实战用法

`code/main.py` 在不借助任何框架的情况下构造、校验、追踪并分发现代 MCP 消息。运行：

```bash
python3 code/main.py
python3 -m unittest discover code/tests -v
```

在输出中留意三条不变量：

- 每个请求都重复携带自己的 `_meta` 字段。
- 每个成功结果都是 `resultType: "complete"` 并包含服务器身份。
- 列表结果是确定性排序的，并带有显式的缓存提示。

> `code/main.py` builds, validates, traces, and dispatches modern MCP messages without a framework. Run:
> Watch for three invariants in the output:
> - Every request repeats its `_meta` fields.
> - Every successful result is `resultType: "complete"` and includes server identity.
> - The list result is deterministically ordered and has explicit cache hints.

## Ship It · 交付

本课交付 `outputs/skill-mcp-handshake-tracer.md`。历史文件名保持不变，但这个产物现在是一个无状态请求追踪器（stateless request tracer）。它独立审计每条消息，只在确实出现旧版握手流量时才把它标注为旧版握手。

> This lesson ships `outputs/skill-mcp-handshake-tracer.md`. The historical filename remains stable, but the artifact is now a stateless request tracer. It audits each message independently and labels legacy handshake traffic only when it is genuinely present.

## Exercises · 练习

1. 把某个请求的协议版本改成 `2027-01-01`。确认错误码是 `-32022`，且错误数据中给出了受支持的版本。
2. 从第二个请求中删掉 `io.modelcontextprotocol/clientCapabilities`。确认服务器不会复用第一个请求的能力。
3. 把内存中的工具注册表反转。确认 `tools/list` 仍返回相同的确定性顺序。
4. 把 `cacheScope` 从 `public` 改成 `private`。解释两种取值下分别有哪些授权上下文可以复用该响应。
5. 增加一个 `clientInfo` 缺失的可选测试。请求应当仍然有效，因为客户端身份是推荐项而非必需项。

> 1. Change one request's protocol version to `2027-01-01`. Confirm the error code is `-32022` and the data advertises the supported version.
> 2. Remove `io.modelcontextprotocol/clientCapabilities` from the second request. Confirm the server does not reuse capabilities from the first request.
> 3. Reverse the in-memory tool registry. Confirm `tools/list` still returns the same deterministic order.
> 4. Change `cacheScope` from `public` to `private`. Explain which authorization contexts may reuse the response in each case.
> 5. Add an optional `clientInfo` omission test. The request should remain valid because client identity is recommended, not required.

## Key Terms · 术语表

| 术语 | 含义 |
|------|---------|
| 无状态协议（Stateless protocol） | 每个请求自带解释它所需的元数据 |
| 请求元数据（Request metadata） | `params._meta` 中的协议版本、客户端能力，以及推荐的客户端身份 |
| `server/discover` | 必需的服务器方法，用于获取版本、能力、说明与身份 |
| `resultType` | 每个成功的现代结果上的判别字段 |
| 可缓存结果（Cacheable result） | 带有所需 `ttlMs` 与 `cacheScope` 提示的结果 |
| 协议时代（Protocol era） | 现代的逐请求元数据，或旧版的连接作用域初始化 |
| 传输生命周期（Transport lifetime） | 进程、连接或响应流的生命周期，而非协议会话状态 |
| `-32022` | 不受支持的协议版本错误，附带 requested 与 supported 版本 |

> | Term | Meaning |
> |------|---------|
> | Stateless protocol | Every request supplies the metadata needed to interpret it |
> | Request metadata | Version, client capabilities, and recommended client identity in `params._meta` |
> | `server/discover` | Mandatory server method for versions, capabilities, instructions, and identity |
> | `resultType` | Discriminator on every successful modern result |
> | Cacheable result | Result that includes required `ttlMs` and `cacheScope` hints |
> | Protocol era | Modern per-request metadata or legacy connection-scoped initialization |
> | Transport lifetime | Process, connection, or response-stream lifetime, not protocol session state |
> | `-32022` | Unsupported protocol version error with requested and supported versions |

## Further Reading · 延伸阅读

- [MCP Architecture](https://modelcontextprotocol.io/specification/2026-07-28/architecture)
- [MCP Base Protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic)
- [MCP Server Discovery](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
- [MCP 2026-07-28 Changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
