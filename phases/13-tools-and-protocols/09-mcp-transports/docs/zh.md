# MCP Transports: stdio and Stateless Streamable HTTP · MCP 传输层：stdio 与无状态 Streamable HTTP

> Transport carries MCP messages. It does not supply missing protocol state. In `2026-07-28`, local stdio and remote Streamable HTTP both carry self-describing requests.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 13, Lessons 07 and 08
**Time:** ~65 minutes

## Learning Objectives · 学习目标

- 本地子进程选 stdio，网络服务选 Streamable HTTP。
- 实现现代的单端点、仅 POST 的 Streamable HTTP 契约。
- 把 MCP 版本、方法和名称头部与 JSON-RPC 请求体相互镜像并校验。
- 正确投递请求作用域的 SSE 和长驻的 `subscriptions/listen` 流。
- 迁移基于会话的以及旧版 HTTP+SSE 部署，且不把旧版行为伪装成现代行为。

> Choose stdio for local child processes and Streamable HTTP for network services.
> Implement the modern single-endpoint, POST-only Streamable HTTP contract.
> Mirror and validate MCP version, method, and name headers against the JSON-RPC body.
> Deliver request-scoped SSE and long-lived `subscriptions/listen` streams correctly.
> Migrate session-based and legacy HTTP+SSE deployments without presenting legacy behavior as modern.

## The Problem · 问题所在

更早的 Streamable HTTP 修订版把协议协商与连接、会话行为混在一起。服务器可以铸造 `Mcp-Session-Id`、暴露独立的 GET 流、接受 DELETE 来终止会话，并用 `Last-Event-ID` 恢复 SSE。

MCP `2026-07-28` 把这些机制从现代线上协议中移除了。每个请求都可以落在任意健康的 worker 上，因为它的协议版本与客户端能力就随请求体一起传输。HTTP 头部镜像部分选定字段用于路由与策略，但服务器会在执行前用请求体校验这些头部。

结果就是：更容易扩展，也更容易推理。这也意味着，一台把 2025 版传输当作现行版本来教的服务器，教的是错误的失败模型和安全模型。

> Earlier Streamable HTTP revisions combined protocol negotiation with connection and session behavior. A server could mint `Mcp-Session-Id`, expose a standalone GET stream, accept DELETE for session termination, and resume SSE with `Last-Event-ID`.
> MCP `2026-07-28` removes those mechanisms from the modern wire. Every request can land on any healthy worker because its protocol version and client capabilities travel in the request body. HTTP headers mirror selected fields for routing and policy, but the server validates those headers against the body before execution.
> The result is easier to scale and easier to reason about. It also means that a server teaching the 2025 transport as current is teaching the wrong failure and security model.

## The Concept · 核心概念

### stdio · stdio

stdio 绑定用于客户端启动的子进程：

- 客户端向 stdin 每行写一条 UTF-8 JSON-RPC 消息。
- 服务器向 stdout 每行写一条 UTF-8 JSON-RPC 消息。
- 服务器把诊断信息写到 stderr。
- 服务器在 stdin EOF 时立即退出。
- 每个现代请求都在 `params._meta` 中携带版本与客户端能力。

进程可以活过多次调用，但它不是现代协议会话。如果它意外退出，在途请求就会丢失。重启进程、重新发现、重新列表、重新打开订阅，并用新的请求 id 重试安全操作。

> The stdio binding is for a client-launched subprocess:
> - Client writes one UTF-8 JSON-RPC message per line to stdin.
> - Server writes one UTF-8 JSON-RPC message per line to stdout.
> - Server writes diagnostics to stderr.
> - Server exits promptly on stdin EOF.
> - Every modern request carries version and client capabilities in `params._meta`.
> The process may live for many calls, but it is not a modern protocol session. If it exits unexpectedly, in-flight requests are lost. Restart the process, rediscover, relist, reopen subscriptions, and retry safe operations with new request ids.

### Streamable HTTP in 2026-07-28 · 2026-07-28 中的 Streamable HTTP

现代服务器暴露一个接受 POST 的 MCP 端点，例如 `/mcp`。

每个 JSON-RPC 请求或通知都是一次新的 HTTP POST。请求体包含一条 JSON-RPC 消息。客户端不向服务器发送 JSON-RPC 响应。

对于一个请求，服务器返回二者之一：

- `Content-Type: application/json`，带一条 JSON-RPC 响应；或
- `Content-Type: text/event-stream`，先发与该请求相关的通知，最后发最终的 JSON-RPC 响应。

对一条被接受的通知，服务器返回不带正文的 `202 Accepted`。

客户端声明两种响应类型都接受：

```http
Accept: application/json, text/event-stream
```

> A modern server exposes one MCP endpoint, such as `/mcp`, that accepts POST.
> Every JSON-RPC request or notification is a new HTTP POST. The body contains one JSON-RPC message. Clients do not send JSON-RPC responses to the server.
> For a request, the server returns either:
> - `Content-Type: application/json` with one JSON-RPC response; or
> - `Content-Type: text/event-stream` with notifications related to that request, followed by the final JSON-RPC response.
> For an accepted notification, the server returns `202 Accepted` with no body.
> Clients advertise both response types:

### POST-only means POST-only · POST-only 就是真的只有 POST

现代 Streamable HTTP 没有独立的 GET 流，也没有 DELETE 会话端点。

- `GET /mcp` 返回 `405 Method Not Allowed`。
- `DELETE /mcp` 返回 `405 Method Not Allowed`。
- `Mcp-Session-Id` 被忽略，既不铸造也不回显。
- `Last-Event-ID` 被忽略，因为现代流不可恢复。

如果一条请求作用域的流在最终响应之前断掉，客户端就丢失了那个在途请求。重试安全时，它可以用新的 JSON-RPC id 发起新请求。它绝不能尝试恢复流。

> Modern Streamable HTTP has no standalone GET stream and no DELETE session endpoint.
> - `GET /mcp` returns `405 Method Not Allowed`.
> - `DELETE /mcp` returns `405 Method Not Allowed`.
> - `Mcp-Session-Id` is ignored and never minted or echoed.
> - `Last-Event-ID` is ignored because modern streams are not resumable.
> If a request-scoped stream breaks before its final response, the client has lost that in-flight request. It may issue a new request with a new JSON-RPC id when retry is safe. It must not attempt stream resumption.

### Origin validation · Origin 校验

服务器对进来的连接校验 `Origin`，以防 DNS 重绑定（DNS rebinding）。如果该头部存在且未被显式允许，返回 `403 Forbidden`。非浏览器客户端可以省略 `Origin`，官方传输规则允许这一点。

本地服务器应当绑定 `127.0.0.1`，而不是所有网卡。网络服务仍然要对每个请求做认证与授权。Origin 校验不是认证。

在规范化配置之后使用精确的 origin 匹配。像 `origin.startswith("https://trusted.example")` 这样的前缀检查是不安全的，因为它们可能接受攻击者控制的后缀。

> Servers validate `Origin` on incoming connections to prevent DNS rebinding. If the header is present and not explicitly allowed, return `403 Forbidden`. A non-browser client may omit `Origin`, which the official transport rules permit.
> Local servers should bind to `127.0.0.1`, not every interface. Network services still need authentication and authorization on every request. Origin validation is not authentication.
> Use exact origin matching after canonical configuration. Prefix checks such as `origin.startswith("https://trusted.example")` are unsafe because they can accept attacker-controlled suffixes.

### Required HTTP metadata headers · 必需的 HTTP 元数据头部

每个现代 POST 请求都包含：

```http
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: notes_search
```

头部规则：

- `MCP-Protocol-Version` 必需，且必须等于 `params._meta.io.modelcontextprotocol/protocolVersion`。
- `Mcp-Method` 必需，且必须等于 JSON-RPC 的 `method`。
- `tools/call`、`resources/read` 和 `prompts/get` 必须带 `Mcp-Name`。
- `Mcp-Name` 等于 `params.name`；`resources/read` 时等于 `params.uri`。
- 头部值区分大小写，即使头部名不区分大小写。

不安全或含非 ASCII 字符的 `Mcp-Name` 值使用这个精确的 UTF-8 Base64 哨兵格式：

```text
=?base64?{Base64EncodedValue}?=
```

服务器先解码该值，再与请求体比对。

镜像头部缺失、畸形或与请求体不一致，返回 HTTP `400` 与 JSON-RPC 错误码 `-32020`。如果头部与请求体一致地给出了服务器不支持的版本，返回 HTTP `400` 与 `-32022`，并附带精确的错误数据，例如 `{"supported":["2026-07-28"],"requested":"2027-01-01"}`。

一个未知的现代方法返回 HTTP `404` 与 JSON-RPC `-32601`。JSON-RPC 请求体很重要，因为双时代客户端要靠它来区分现代错误与旧版端点未命中。

> Every modern POST request includes:
> Header rules:
> - `MCP-Protocol-Version` is required and must equal `params._meta.io.modelcontextprotocol/protocolVersion`.
> - `Mcp-Method` is required and must equal the JSON-RPC `method`.
> - `Mcp-Name` is required for `tools/call`, `resources/read`, and `prompts/get`.
> - `Mcp-Name` equals `params.name`, or `params.uri` for `resources/read`.
> - Header values are case-sensitive even though header names are case-insensitive.
> Unsafe or non-ASCII `Mcp-Name` values use the exact UTF-8 Base64 sentinel:
> The server decodes that value before comparing it with the body.
> Missing, malformed, or mismatched mirrored headers return HTTP `400` with JSON-RPC code `-32020`. If header and body agree on a version the server does not support, return HTTP `400` with `-32022` and exact error data such as `{"supported":["2026-07-28"],"requested":"2027-01-01"}`.
> An unknown modern method returns HTTP `404` with JSON-RPC `-32601`. The JSON-RPC body is important because a dual-era client uses it to distinguish a modern error from a legacy endpoint miss.

### Request-scoped SSE · 请求作用域的 SSE

对一个长时间运行的请求，服务器可以选择 SSE：

```text
POST tools/call id=41
  <- notifications/progress related to id=41
  <- notifications/progress related to id=41
  <- JSON-RPC response id=41
stream closes
```

服务器不得在这条流上发送独立的 JSON-RPC 请求。sampling、elicitation 和 roots 交互使用多轮往返请求（Multi Round-Trip Request）结果。关闭响应流会取消该请求。

不要为重放添加 SSE 事件 id。`Last-Event-ID` 恢复不属于现代修订版。

> A server may choose SSE for one long-running request:
> The server must not send independent JSON-RPC requests on this stream. Sampling, elicitation, and roots interactions use Multi Round-Trip Request results. Closing the response stream cancels that request.
> Do not add SSE event ids for replay. `Last-Event-ID` resumption is not part of the modern revision.

### Long-lived changes use subscriptions/listen · 长期变更用 subscriptions/listen

变更通知使用一个客户端打开的请求，而不是独立的 GET：

```json
{
  "jsonrpc": "2.0",
  "id": "listen-1",
  "method": "subscriptions/listen",
  "params": {
    "notifications": {
      "toolsListChanged": true,
      "resourceSubscriptions": ["notes://note-1"]
    },
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

POST 的响应是一条长驻的 SSE 流。它的第一条协议消息是 `notifications/subscriptions/acknowledged`。确认消息、每条变更通知和最终结果都在 `_meta` 中携带 `io.modelcontextprotocol/subscriptionId`，等于该 listen 请求的 id。服务器可以发出 SSE 注释作为保活。当流断开时，客户端用新的请求 id 重发 `subscriptions/listen`，并重新拉取受影响的数据。

`resources/subscribe` 与 `resources/unsubscribe` 属于旧时代。不要在现代连接上使用它们。

> Change notifications use a client-opened request, not standalone GET:
> The POST response is a long-lived SSE stream. Its first protocol message is `notifications/subscriptions/acknowledged`. The acknowledgement, every change notification, and the final result carry `io.modelcontextprotocol/subscriptionId` in `_meta`, equal to the listen request id. The server may emit SSE comments as keepalives. When the stream drops, the client reissues `subscriptions/listen` with a new request id and refetches affected data.
> `resources/subscribe` and `resources/unsubscribe` belong to the legacy era. Do not use them on a modern connection.

### Explicit application state · 显式的应用状态

移除协议会话并不禁止带状态的工作流。服务器可以铸造一个不透明的状态句柄，并作为普通的工具结果返回。客户端在后续调用中把该句柄作为显式参数传入。

把句柄绑定到已认证的主体（principal），让它们不可猜测、会过期，并对每次使用做授权。这让状态在应用层可见，而不是藏在传输亲和性里。

隐藏的副本状态导致的失败是机械性的：

1. 请求 A 到达副本 1，在该进程的内存里创建了一个草稿。
2. 响应没有返回草稿句柄，因为实现假设连接本身就标识了草稿。
3. 请求 B 是一次全新的 POST，落到了副本 2。
4. 副本 2 拿着合法的协议元数据，却无法命名或加载那个草稿，于是工作流失败，或者读到了错误的本地对象。
5. 粘性路由看似修好了症状，直到一次重启、发布、重新调度或故障转移把下一个请求挪走。

正确的边界有两部分。协议上下文留在每个请求里。持久的应用状态放在共享存储中，由一个返回给客户端的服务器铸造的句柄指代。下一次调用带上该句柄，任何副本都能加载同一条记录，而授权把这条记录绑定到已认证的主体与租户。副本内存可以缓存一条记录，但它不能是正确性所依赖的唯一副本。

按生命周期选择状态机制。请求局部变量可以服务一次调用。一次短暂的 MRTR 续段可以用受完整性保护的 `requestState`。一份草稿或持久任务需要显式句柄，再加上共享持久化、过期、并发控制和幂等性。这些对象没有一个是 MCP 协议会话。

> Removing protocol sessions does not forbid workflows with state. The server may mint an opaque state handle and return it as a normal tool result. The client passes that handle as an explicit argument on later calls.
> Bind handles to the authenticated principal, make them unguessable, expire them, and authorize every use. This makes state visible at the application layer instead of hiding it in transport affinity.
> The failure caused by hidden replica state is mechanical:
> The correct boundary has two parts. Protocol context stays in each request. Durable application state lives in a shared store under a server-minted handle returned to the client. The next call supplies that handle, any replica loads the same record, and authorization binds the record to the authenticated principal and tenant. Replica memory may cache a record, but it cannot be the only copy required for correctness.
> Choose the state mechanism by lifetime. Request-local variables can serve one call. A short MRTR continuation can use integrity-protected `requestState`. A draft or durable task needs an explicit handle plus shared persistence, expiry, concurrency control, and idempotency. None of those objects is an MCP protocol session.

### HTTP dual-era compatibility · HTTP 双时代兼容

同时支持现代与旧版服务器的客户端先尝试一次现代 POST。如果收到 HTTP `400`、`404` 或 `405`，它检查响应体：

- 一个可识别的现代 JSON-RPC 错误证明服务器是现代的。修正请求，或重试其广告的版本。不要降级。
- 空响应体或无法识别的响应可能意味着旧版 HTTP+SSE 服务器。只有此时才尝试旧的 GET 端点，并期待它的旧版 `endpoint` 事件。

迁移期间，服务器可以同时支持两个时代：把现代元数据路由到现代的仅 POST 实现，并为旧客户端保留独立的旧版端点。绝不要把旧版的 GET、DELETE、会话 id 或重放行为描述成 `2026-07-28` 的一部分。

```figure
tp-transport-handshake
```

> A client that supports modern and legacy servers attempts a modern POST first. If it receives HTTP `400`, `404`, or `405`, it inspects the body:
> - A recognized modern JSON-RPC error proves the server is modern. Correct the request or retry an advertised version. Do not downgrade.
> - An empty body or an unrecognized response may indicate a legacy HTTP+SSE server. Only then try the old GET endpoint and expect its legacy `endpoint` event.
> A server can support both eras during migration by routing modern metadata to the modern POST-only implementation and retaining separate legacy endpoints for old clients. Never describe the legacy GET, DELETE, session id, or replay behavior as part of `2026-07-28`.

## Use It · 实战用法

`code/main.py` 用 Python 标准库实现了一个有限的现代 Streamable HTTP 服务器。它校验 Origin 与镜像头部、忽略被移除的会话头部、对普通调用返回 JSON，并演示一条有限的 `subscriptions/listen` SSE 流。

```bash
cd code
python3 main.py --probe
python3 -m unittest discover tests -v
```

探测脚本检查：

- 非法 Origin 被拒绝；
- 没有 session id 也能完成发现；
- `Mcp-Session-Id` 与 `Last-Event-ID` 被忽略；
- 头部不一致返回 `-32020`；
- 不受支持的版本返回 `-32022`，并带精确的 `supported` 与 `requested` 数据；
- 被接受的无 id 通知返回 HTTP `202` 且无正文；
- GET 与 DELETE 返回 `405`；
- `subscriptions/listen` 是一条 POST 响应流，其确认、通知和最终结果都携带它的订阅 id。

> `code/main.py` implements a finite, modern Streamable HTTP server with the Python standard library. It validates Origin and mirrored headers, ignores removed session headers, returns JSON for normal calls, and demonstrates a finite `subscriptions/listen` SSE stream.
> The probe checks:
> - invalid Origin is rejected;
> - discovery succeeds without a session id;
> - `Mcp-Session-Id` and `Last-Event-ID` are ignored;
> - header mismatch returns `-32020`;
> - unsupported version returns `-32022` with exact `supported` and `requested` data;
> - an accepted id-less notification returns HTTP `202` with no body;
> - GET and DELETE return `405`;
> - `subscriptions/listen` is a POST response stream whose acknowledgement, notifications, and final result carry its subscription id.

## Ship It · 交付

本课交付 `outputs/skill-mcp-transport-migrator.md`。它移除现代协议会话、增加头部与请求体的校验、用 `subscriptions/listen` 取代独立的 GET，并让任何旧版桥接保持清晰隔离。

> This lesson ships `outputs/skill-mcp-transport-migrator.md`. It removes modern protocol sessions, adds header-body validation, replaces standalone GET with `subscriptions/listen`, and keeps any legacy bridge visibly separate.

## Exercises · 练习

1. 从一个 POST 中去掉 `Mcp-Method`。确认返回 HTTP `400` 和错误 `-32020`。
2. 发送头部与请求体一致的版本 `2027-01-01`。确认返回 HTTP `400`、错误 `-32022`，以及精确数据 `{"supported":["2026-07-28"],"requested":"2027-01-01"}`。
3. 为一个非 ASCII 的资源 URI 发送 Base64 哨兵格式的 `Mcp-Name`。确认解码后的值会与 `params.uri` 比对。
4. 在最终响应之前弄断那条有限的 listen 流。用新的 JSON-RPC id 重发它并重新拉取工具。
5. 给 ping 工具加一个显式的工作流句柄。把它绑定到授权主体，而不使用连接亲和性。

> 1. Remove `Mcp-Method` from a POST. Confirm HTTP `400` and error `-32020`.
> 2. Send matching header and body version `2027-01-01`. Confirm HTTP `400`, error `-32022`, and exact data `{"supported":["2026-07-28"],"requested":"2027-01-01"}`.
> 3. Send a Base64 sentinel `Mcp-Name` for a non-ASCII resource URI. Confirm the decoded value is compared with `params.uri`.
> 4. Break the finite listen stream before its final response. Reissue it with a new JSON-RPC id and refetch tools.
> 5. Add an explicit workflow handle to the ping tool. Bind it to an authorization subject without using connection affinity.

## Key Terms · 术语表

| 术语 | 含义 |
|------|---------|
| stdio | 客户端启动的子进程上按换行分隔的 JSON-RPC |
| Streamable HTTP | 单一端点，每条现代消息都是一次新的 POST |
| 请求作用域 SSE（Request-scoped SSE） | POST 响应流，包含相关通知与最终响应 |
| `subscriptions/listen` | 用于显式订阅变更通知的长驻 POST 请求 |
| 头部不一致（Header mismatch） | 镜像头部与请求体不一致时返回 HTTP `400` 与 JSON-RPC `-32020` |
| Origin 校验（Origin validation） | 针对进连接的 DNS 重绑定防御，不是认证 |
| 显式状态句柄（Explicit state handle） | 作为普通参数传递的应用令牌，取代隐藏的会话状态 |
| 旧版桥接（Legacy bridge） | 仅为兼容性保留的、相互独立的更早时代行为 |

> | Term | Meaning |
> |------|---------|
> | stdio | Newline-delimited JSON-RPC over a client-launched subprocess |
> | Streamable HTTP | Single endpoint where each modern message is a new POST |
> | Request-scoped SSE | POST response stream containing related notifications and final response |
> | `subscriptions/listen` | Long-lived POST request for opted-in change notifications |
> | Header mismatch | HTTP `400` and JSON-RPC `-32020` when mirrored headers disagree with body |
> | Origin validation | DNS-rebinding defense for incoming connections, not authentication |
> | Explicit state handle | Application token passed as an ordinary argument instead of hidden session state |
> | Legacy bridge | Separate earlier-era behavior kept only for compatibility |

## Further Reading · 延伸阅读

- [MCP Transport Overview](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports)
- [MCP stdio Transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)
- [MCP Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [MCP Subscriptions](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/subscriptions)
- [MCP 2026-07-28 Changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
