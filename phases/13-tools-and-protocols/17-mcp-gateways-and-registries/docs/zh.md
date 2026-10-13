# Stateless MCP Gateways and Registry Admission · 无状态 MCP 网关与注册表准入

> 网关应当让每一条路由都显式可见。2026-07-28 版协议让它在没有传输会话的情况下，也能划定方法、名称、版本、能力、身份、缓存与追踪的边界。
>
> A gateway should make every route explicit. The 2026-07-28 protocol gives it method, name, version, capability, identity, cache, and trace boundaries without a transport session.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 13 · 15 (security), Phase 13 · 16 (authorization)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 把多个 MCP 服务器聚合到一个 2026-07-28 端点之后，而不依赖会话亲和性（session affinity）
- 在执行策略或转发之前，先校验每个请求的元数据与路由头
- 用稳定命名空间（namespace）、确定性顺序、描述符固定（descriptor pin）、RBAC 与私有缓存来合并工具
- 把注册表（registry）记录当作发现证据——它仍然需要准入策略（admission policy）把关
- 正确路由请求级 SSE、`subscriptions/listen`、MRTR 重试与 Tasks 扩展调用
- 把旧式握手与会话支持从现代路径中隔离出去

> Aggregate several MCP servers behind one 2026-07-28 endpoint without session affinity.
> Validate per-request metadata and routing headers before policy or forwarding.
> Merge tools with stable namespaces, deterministic order, descriptor pins, RBAC, and private caching.
> Treat registry records as discovery evidence that still requires admission policy.
> Route request-scoped SSE, `subscriptions/listen`, MRTR retries, and Tasks extension calls correctly.
> Isolate legacy handshake and session support from the modern path.

## The Problem · 问题在哪

把一个客户端直连一个服务器很简单。更大规模的部署需要对一些更难的问题给出一致的答案：

- 哪些服务器被允许接入？
- 哪个主体（principal）能看到并调用每个工具？
- 两个后端暴露了相同的名称时怎么办？
- 描述符（descriptor）的变更如何评审？
- 速率限制和审计事件在哪里生效？
- 下一个请求能否由任意实例来处理？

网关（gateway）位于客户端与后端 MCP 服务器之间。它对外呈现一个 MCP 端点，施加横切策略（cross-cutting policy），并转发获批准的请求。

较老的网关设计常常把一个客户端会话多路复用（multiplex）成多个后端会话，并改写 `Mcp-Session-Id`。那是遗留兼容性设计。2026-07-28 核心协议里已经没有协议会话。

> A gateway sits between clients and backend MCP servers. It presents one MCP endpoint, applies cross-cutting policy, and forwards approved requests.
> Older gateway designs often multiplexed one client session into several backend sessions and rewrote `Mcp-Session-Id`. That is a legacy compatibility design. The 2026-07-28 core has no protocol sessions.

## The Concept · 概念

### The modern gateway path · 现代网关路径

对每个请求：

1. 从传输层授权认证主体（principal）。
2. 校验 `MCP-Protocol-Version`、`Mcp-Method`、`Mcp-Name` 与 `params._meta`。
3. 对主体、资源、方法、工具与参数做授权。
4. 应用描述符、注册表、速率与数据策略。
5. 为选定的后端创建一个全新的自包含请求。
6. 校验后端结果并返回网关结果。
7. 在不记录机密信息的前提下记录审计事件。

没有任何一步需要隐藏的协议会话。应用状态仍然可以存在于数据库、显式句柄、Tasks 或受完整性保护的 MRTR 状态中。

> No step needs a hidden protocol session. Application state can still exist in databases, explicit handles, Tasks, or integrity-protected MRTR state.

### Runtime policy is the primary gateway decision · 运行时策略才是网关的首要决策

准入（admission）决定哪个后端版本可以进入网关；它并不授权一次实时调用。对每个请求，网关都会基于已认证的主体、签发者（issuer）与资源、租户（tenant）、匹配的方法与名称、归一化后的参数、已准入的描述符固定值、当前后端健康状况、能力交集、数据分级、速率状态，以及任何绑定到操作的审批，重新计算策略。

这个顺序很重要。注册表记录可以保持活跃，而某个用户的角色已被吊销；描述符可以保持固定，而某个目的地参数已跨越租户边界；后端可以保持获批，而事件策略（incident policy）正在隔离所有改变状态的调用。因此，运行时策略才是首要的「允许/拒绝」决策，注册表与描述符证据只是它的输入。

不要把「允许」决策缓存在连接或已移除的会话标识符之下。策略不可用时，就按操作类别执行预先声明的失败策略（failure policy）。一个安全的默认做法是：对状态变更和敏感读取失败关闭（fail closed）；而经过明确审批的公共读取路径，仅当其风险模型允许时，才可使用短期的「最后已知策略」。记录下是哪个策略版本和哪条失败路径做出了决策，然后在返回之前校验后端结果。

> Admission decides which backend version may enter the gateway. It does not authorize a live call. ... Runtime policy is therefore the primary allow or deny decision, with Registry and descriptor evidence as inputs.
> Do not cache an allow decision under a connection or removed session identifier. ... Record which policy version and failure path made the decision, then validate the backend result before returning it.

### One POST endpoint · 单一 POST 端点

现代 Streamable HTTP 通过 POST 发送每条 JSON-RPC 消息：

```text
POST /mcp
Authorization: Bearer <gateway-token>
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: notes.search
Accept: application/json, text/event-stream
```

针对这个 POST，网关可以返回 JSON 或请求级 SSE（request-scoped SSE）。对现代请求，GET 和 DELETE 返回 405。`Mcp-Session-Id` 与 `Last-Event-ID` 不产生任何权限、亲和性或重放行为。

头与体中的值必须一致。在查找后端之前发现不一致，就以 `-32020` 拒绝。这让负载均衡器、网关和速率限制器无需解析完整请求体就能路由，同时保持端到端完整性。

按一个精确的顺序校验：先校验 JSON-RPC 与元数据类型，再校验头与体的等价性，然后是所匹配版本的支持情况。不匹配返回 HTTP 400 与 `-32020`。如果头与体一致地声明了一个不支持的版本，返回 HTTP 400 与 `-32022`，且 `data` 恰好为 `{"supported":["2026-07-28"],"requested":"<actual>"}`。未知方法返回 HTTP 404 与 `-32601`。

`ProtocolError` 可以携带可选的 `data`，网关会把它序列化进 JSON-RPC 错误对象。通知（notification）没有 `id`，因此永远不会收到 JSON-RPC 成功或错误响应。被接受的 HTTP 通知返回 202 和空响应体。

> Modern Streamable HTTP sends each JSON-RPC message through POST. ... The gateway can return JSON or request-scoped SSE for that POST. GET and DELETE return 405 for modern requests. `Mcp-Session-Id` and `Last-Event-ID` do not create authority, affinity, or replay behavior.
> Header and body values must agree. Reject mismatch with `-32020` before looking up a backend.
> Validate in one exact order: JSON-RPC and metadata types, header and body equality, then support for the matched version. ... A mismatch returns HTTP 400 with `-32020`. ... An unknown method returns HTTP 404 with `-32601`.
> `ProtocolError` carries optional `data`, and the gateway serializes it into the JSON-RPC error object. A notification has no `id`, so it never receives a JSON-RPC success or error. An accepted HTTP notification returns 202 with an empty body.

### Implement discovery at every layer · 每一层都实现发现

网关为客户端实现 `server/discover`。它也会对每个后端做发现，从而掌握协议版本、能力与扩展。

网关结果示例：

```json
{
  "resultType": "complete",
  "supportedVersions": ["2026-07-28"],
  "capabilities": {
    "tools": {"listChanged": true}
  },
  "ttlMs": 30000,
  "cacheScope": "private",
  "_meta": {
    "io.modelcontextprotocol/serverInfo": {
      "name": "enterprise-gateway",
      "version": "2.0.0"
    }
  }
}
```

只公告网关能够端到端兑现的能力交集。后端的某个特性并不自动意味着可以安全暴露；网关有、但后端没有路径支持的特性，公告出去也没有用。

`serverInfo` 是自报告的展示与诊断数据。不要把它当作注册表或发布者的证明。

> The gateway implements `server/discover` for clients. It also discovers each backend so it knows protocol versions, capabilities, and extensions.
> Advertise only the capability intersection the gateway can honor end to end. A backend feature is not automatically safe to expose. A gateway feature with no backend path is not useful to advertise.
> `serverInfo` is self-reported display and diagnostic data. Do not use it as registry or publisher proof.

### Per-request client capabilities · 每个请求的客户端能力

每个被转发的请求都需要一个新鲜的 `_meta` 信封：

```json
{
  "io.modelcontextprotocol/protocolVersion": "2026-07-28",
  "io.modelcontextprotocol/clientCapabilities": {},
  "io.modelcontextprotocol/clientInfo": {
    "name": "enterprise-gateway",
    "version": "1.0.0"
  }
}
```

不要盲目地把外层客户端能力复制给后端。网关才是后端的客户端。只公告网关会正确中介的特性。

> Every forwarded request needs a current `_meta` envelope.
> Do not blindly copy the outer client capabilities to a backend. The gateway is the backend's client. Advertise only features the gateway will mediate correctly.

### Deterministic namespacing · 确定性命名空间

用稳定的公开名称合并后端工具：

```text
notes.search
notes.create
issues.list
issues.open
```

保留一张「公开名称 → 后端与原始工具名」的映射。绝不选第一个或最后一个冲突。公开名称是审批与审计契约的一部分，改动它就是一次迁移。

`tools/list` 必须是确定性的。当可见性因主体而异时，返回 `cacheScope: private`。有界的 `ttlMs` 可以减少后端发现负载，同时不让特定用户的列表泄漏到其他授权上下文。

每个暴露的工具描述符都包含稳定名称、描述和以对象为根的 `inputSchema`。命名空间化不能移除必需的描述符字段。完整的列表结果还包括 `resultType`、服务器身份元数据和缓存提示。

> Merge backend tools under stable public names.
> Keep a mapping from public name to backend and original tool name. Never choose the first or last collision. A public name is part of the approval and audit contract, so changing it is a migration.
> `tools/list` must be deterministic. When visibility differs by principal, return `cacheScope: private`. A bounded `ttlMs` reduces backend discovery load without allowing a user-specific list to leak across authorization contexts.
> Every exposed tool descriptor includes a stable name, description, and object-root `inputSchema`. Namespacing cannot remove required descriptor fields. The complete list result also includes `resultType`, server identity metadata, and cache hints.

### Pin approved descriptors · 固定已批准的描述符

在准入时，对完整描述符做规范化（canonicalize），并把它的摘要存储在限定的公开名称之下。在 list 和 call 时，把实时描述符与已批准的摘要做比较。

如果它变了：

- 从 `tools/list` 中移除。
- 拒绝直接调用。
- 发出审计事件。
- 在更新固定值之前，要求策略或人工重新审批。

网关是一个有用的中心化执行点，但它不能把一个首次见到的描述符变成安全的描述符。初始评审仍然必要。

> At admission time, canonicalize the complete descriptor and store its digest under the qualified public name. At list and call time, compare the live descriptor with the approved digest.
> A gateway is a useful central enforcement point, but it does not turn a first-seen descriptor into a safe one. Initial review remains necessary.

### Registries help discover, not decide · 注册表帮你发现，不帮你决策

注册表（Registry）的 `server.json` 提供发布元数据。一个基于包（package-backed）的记录可能长这样：

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "com.example/notes",
  "description": "Example notes MCP server.",
  "version": "1.0.0",
  "packages": [
    {
      "registryType": "npm",
      "identifier": "@example/notes-mcp",
      "version": "1.0.0",
      "transport": {"type": "stdio"}
    }
  ]
}
```

发布元数据不承载网关的安全决策。把已验证的发布者与来源（provenance）证据保存在单独的准入状态里：

```json
{
  "registryName": "com.example/notes",
  "registryVersion": "1.0.0",
  "publisher": {"namespace": "com.example", "status": "verified"},
  "provenance": {
    "source": "registry.modelcontextprotocol.io",
    "recordId": "com.example/notes@1.0.0"
  },
  "admission": {"status": "approved", "reviewedBy": "gateway-policy"}
}
```

网关检查 `server.json` 的结构，并把它与那份外部状态联接（join）起来。网关仍然需要准入策略。

对每个已准入的后端，记录：

- 精确的注册表与记录标识符。
- 已验证的发布者命名空间或域名证据。
- 允许的传输方式与端点。
- 固定的版本或已批准的升级策略。
- 制品（artifact）或描述符摘要。
- 授权签发者与资源。
- 评审人、审批时间与过期时间。

不要因为某个服务器的显示名称像一个熟悉的产品就接受它。不要把「出现在注册表里」当作运营安全评审。私有服务器可以走同一套证据模式准入，即使它们从不出现在公共注册表中。

本课实现的是网关接缝（seam）：在后端变得可路由之前，把发布证据联接到本地准入。[Lesson 30: MCP Registry Supply Chain, Admission, Drift, and Rollback](../../30-mcp-registry-supply-chain-and-drift/docs/en.md) 构建完整的控制平面，覆盖精确的命名空间证明、制品来源、不可变固定值、实时描述符漂移、注册表状态对账、防篡改准入账本，以及有证据支撑的回滚。要把那条供应链状态与上面的每请求运行时决策分开保存。

> A Registry `server.json` provides publication metadata.
> Publication metadata does not carry the gateway's security decision. Keep verified publisher and provenance evidence in separate admission state.
> The gateway checks the `server.json` shape and joins it to that external state. The gateway still needs an admission policy.
> Do not accept a server because its display name resembles a familiar product. Do not treat registry presence as an operational security review. Private servers can be admitted through the same evidence schema even when they never appear in a public registry.
> This lesson implements the gateway seam: join publication evidence to local admission before a backend becomes routable.

### Credential mediation · 凭证中介

网关认证它的调用方，并单独向后端认证。后端凭证永远不会交给客户端。

保持这些绑定关系显式化：

```text
outer principal -> gateway role and policy
backend issuer + resource -> backend registration and token
```

绝不把外层网关令牌传给后端。绝不在不同的签发者或资源处复用后端令牌。如果某个工具代表终端用户行事，就用设计好的交换（exchange）或声明（claims）模型来保留这种委托关系，而不是用共享的服务凭证冒充该用户。

> The gateway authenticates its callers and separately authenticates to backends. Backend credentials never go to the client.
> Never pass the outer gateway token to a backend. Never reuse a backend token at a different issuer or resource. If a tool acts on behalf of an end user, preserve that delegation with a designed exchange or claims model rather than impersonating the user with a shared service credential.

### Rate limits without sessions · 无会话的速率限制

按已认证主体、签发者、资源、公开工具、成本类别和时间窗口来设定关键限制。会话 ID 是缺席的，而且即使存在也很容易被轮换。

在消耗昂贵的工作之前，先做廉价的校验。再决定被拒绝的调用是计入滥用限制、业务配额，还是两者都计入。

> Key limits by authenticated principal, issuer, resource, public tool, cost class, and time window. A session id is absent and would be easy to rotate even if it existed.
> Apply cheap validation before consuming expensive work. Decide whether rejected calls count against abuse limits, business quotas, or both.

### Audit the decision chain · 审计决策链

记录足以重构一次调用的信息：

- 请求与追踪标识符。
- 已认证主体与签发者。
- 公开工具与后端路由。
- 描述符固定版本。
- 策略决策与原因。
- 延迟与结果类别。
- 适用时的 MRTR 轮次或任务标识符。

对 bearer 令牌、授权码、刷新令牌、原始机密和不必要的敏感参数做脱敏（redact）。

> Record enough to reconstruct a call.
> Redact bearer tokens, authorization codes, refresh tokens, raw secrets, and unnecessary sensitive arguments.

### Request-scoped SSE · 请求级 SSE

当工作在单个请求期间流式进行时，普通的 POST 可以返回请求级 SSE。关闭响应流即取消该在途的现代 HTTP 请求。

不要另建 GET 流，也不要承诺 Last-Event-ID 重放。那些是旧传输时代的假设。

> A normal POST may return request-scoped SSE when work streams during that one request. Closing the response stream cancels that in-flight modern HTTP request.
> Do not create a separate GET stream and do not promise Last-Event-ID replay. Those are older transport assumptions.

### Long-lived change notifications · 长连接变更通知

对于列表与资源变更通知，现代客户端通过 POST 发送 `subscriptions/listen` 并接收 SSE 响应。通知过滤器使用精确的扁平字段 `toolsListChanged`、`promptsListChanged`、`resourcesListChanged` 和 `resourceSubscriptions`：

```json
{
  "jsonrpc": "2.0",
  "id": "listen-tools",
  "method": "subscriptions/listen",
  "params": {
    "notifications": {
      "toolsListChanged": true
    },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {}
    }
  }
}
```

第一个事件确认受支持的子集。它的订阅标识符就是打开该流的那个请求的 JSON-RPC id：

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/subscriptions/acknowledged",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/subscriptionId": "listen-tools"
    },
    "notifications": {
      "toolsListChanged": true
    }
  }
}
```

网关随后只转发已确认的变更类型。该流上的每条通知都在 `params._meta` 里携带同一个 `io.modelcontextprotocol/subscriptionId`。没有自动重放，也没有自动重新监听。重连时，客户端重新打开订阅，并刷新它所依赖的列表。服务器发起的优雅关闭会返回一个最终的完整结果，并带上同一个订阅 id。

现代路径取代了 `resources/subscribe`、`resources/unsubscribe` 和主动推送式独立 GET 流。只把它们保留在按版本门控的旧路径里。

> For list and resource change notifications, a current client sends `subscriptions/listen` through POST and receives an SSE response.
> The first event acknowledges the supported subset. Its subscription identifier is the JSON-RPC id of the request that opened the stream.
> The gateway then forwards only the acknowledged change types. Every notification on that stream carries the same `io.modelcontextprotocol/subscriptionId` in `params._meta`. There is no automatic replay or automatic re-listen. On reconnect, the client reopens the subscription and refreshes the lists it relies on. A server-initiated graceful close returns a final complete result tagged with the same subscription id.
> The modern path replaces `resources/subscribe`, `resources/unsubscribe`, and unsolicited standalone GET streaming. Keep those only in a version-gated older path.

### MRTR through a gateway · 经网关的 MRTR

当后端返回 `resultType: input_required` 时，只有在外层客户端支持所需的输入请求时，网关才能转发该结果。除非网关有意终止并重新发起这次交互，否则必须逐字节保留 `requestState`。

客户端用全新的 JSON-RPC id 和 `inputResponses` 重试原始公开工具。网关对重试重新授权，检查同一条公开路由，然后转发一个全新的后端请求。它绝不能假设早先的某一轮授予了无限期的批准。

> When a backend returns `resultType: input_required`, the gateway can forward that result only if the outer client supports the needed input request. Preserve `requestState` byte for byte unless the gateway deliberately terminates and reissues the interaction.
> The client retries the original public tool with a fresh JSON-RPC id and `inputResponses`. The gateway re-authorizes the retry, checks the same public route, then forwards a fresh backend request. It must not assume an earlier round granted unlimited approval.

### Tasks extension routing · Tasks 扩展路由

Tasks 是由 `io.modelcontextprotocol/tasks` 标识的官方扩展。它们不是核心会话的替代品。

客户端在每请求客户端能力中声明该扩展；网关只有在能端到端保持其生命周期时，才在发现中公告它。对一个受支持的 `tools/call`，由后端独自决定返回普通结果还是 `resultType: task`。任务结果直接在结果里携带 `taskId`、`status`、时间戳、`ttlMs` 和可选的 `pollIntervalMs`。在该结果被发送之前，任务必须已经持久可读。

网关为这个不透明的任务标识符记录已认证主体与后端路由。后续的 `tasks/get`、`tasks/update` 和 `tasks/cancel` 调用使用 `params.taskId` 作为 `Mcp-Name`，这给中间层提供了一个路由键。`tasks/get` 返回 `resultType: complete`，带有当前任务状态，并在终态中内联最终结果或协议错误。`tasks/update` 为未完成任务发送带键的 `inputResponses`，并返回一个空的 complete 确认。`tasks/cancel` 是一种协作式意图，返回空的 complete 确认，并不保证工作停止。

不要实现新的 `tasks/list` 或 `tasks/result` 方法。它们属于旧的实验模型。需要输入的任务通过 `tasks/get` 暴露完整的内嵌请求；客户端通过 `tasks/update` 回答它们，而不是重试原始工具调用。客户端仍按建议的间隔轮询；任务创建仍然由服务器主导。

持久的任务路由状态是以任务句柄为键的应用数据，不是协议会话。

> Tasks are an official extension identified by `io.modelcontextprotocol/tasks`. They are not a core session replacement.
> The client declares the extension inside per-request client capabilities, and the gateway advertises it in discovery only when it can preserve the lifecycle end to end. For a supported `tools/call`, the backend alone decides whether to return the ordinary result or `resultType: task`. A task result carries `taskId`, `status`, timestamps, `ttlMs`, and an optional `pollIntervalMs` directly in the result. The task must already be durably readable before that result is sent.
> The gateway records the authenticated principal and backend route for the opaque task identifier. Subsequent `tasks/get`, `tasks/update`, and `tasks/cancel` calls use `params.taskId` as `Mcp-Name`, which gives intermediaries a routing key.
> Do not implement new `tasks/list` or `tasks/result` methods. They belong to the older experimental model.
> Durable task route state is application data keyed by the task handle, not a protocol session.

### Compatibility boundary · 兼容性边界

如果网关必须服务较旧的客户端或后端：

- 显式检测其所处的年代。
- 把初始化、传输会话、GET 流、资源订阅和旧任务词汇都关进遗留适配器（legacy adapter）里。
- 绝不把遗留会话 id 泄漏进现代路由或授权。
- 用有界的发现探测和显式的回退策略，代替静默降级。

```figure
t3-gateway-funnel
```

> If the gateway must serve an older client or backend:
> Detect the era explicitly.
> Keep initialization, transport sessions, GET streams, resource subscriptions, and old task vocabulary inside a legacy adapter.
> Never leak a legacy session id into modern routing or authorization.
> Prefer a bounded discovery probe and explicit fallback policy over silent downgrade.

## Build It · 动手造

`code/main.py` 实现了一个进程内协议网关和两个后端服务器。每个后端收到的都是一次全新的当前协议请求。网关提供发现、按用户过滤的确定性 `tools/list`、命名空间路由、注册表 `server.json` 加外部准入状态、描述符固定、RBAC、按主体键控的速率限制、审计决策，以及一个建模的 `subscriptions/listen` SSE 确认。

模型接收解析好的请求体、路由头和已认证的 bearer 身份。它不是完整的 HTTP 适配器，不解析 `Content-Type` 或完整的 `Accept` 契约。把它接到第 09 课的 Streamable HTTP 适配器上，后者要求 `Content-Type: application/json`，且 `Accept` 值同时包含 `application/json` 和 `text/event-stream`。

运行它：

```bash
cd phases/13-tools-and-protocols/17-mcp-gateways-and-registries
python3 code/main.py
python3 -m unittest discover code/tests -v
```

演示会打印外层请求 id 和全新的后端请求 id，让无状态的一跳清晰可见。

> `code/main.py` implements an in-process protocol gateway and two backend servers. Each backend receives a fresh current-protocol request.
> The demo prints the outer request id and fresh backend request id so the stateless hop is visible.

## Use It · 实战用法

把进程内的后端对象换成真实的当前协议客户端。保持同样的接缝：

- 连接之前，先有准入记录。
- 能力暴露之前，先有后端发现。
- 授权之前，先有限定的公开名称。
- list 或 call 之前，先有描述符固定。
- 转发之前，先有新鲜的每请求元数据。
- 返回之前，先有结果校验。

> Replace the in-process backend objects with real current-protocol clients. Keep the same seams:
> Admission record before connection.
> Backend discovery before capability exposure.
> Qualified public name before authorization.
> Descriptor pin before list or call.
> Fresh per-request metadata before forwarding.
> Result validation before returning.

## Ship It · 交付

本课交付 `outputs/skill-gateway-bootstrap.md`。它生成一份现代网关设计，覆盖入口（ingress）、发现、准入、命名空间、授权、缓存、流式传输、订阅、MRTR、Tasks、可观测性与遗留隔离。

> This lesson ships `outputs/skill-gateway-bootstrap.md`. It produces a modern gateway design covering ingress, discovery, admission, namespaces, authorization, caching, streaming, subscriptions, MRTR, Tasks, observability, and legacy isolation.

## Exercises · 练习

1. 给外层请求与转发请求的元数据加上追踪上下文，并把关联关系记录进审计事件。
2. 添加一个支持 Tasks 的后端，用 `Mcp-Name` 里的任务 id 来路由 `tasks/get`。
3. 修改某个后端描述符，并证明发现与直接调用都被阻止。
4. 添加一个主体特定的服务器能力，并解释为什么发现必须保持私有缓存。
5. 编写一个遗留适配器接口，且不给现代 `Gateway` 类添加任何遗留状态。

> 1. Add trace context to the outer and forwarded request metadata and record the correlation in the audit event.
> 2. Add a Tasks-capable backend and route `tasks/get` by task id in `Mcp-Name`.
> 3. Change one backend descriptor and prove both discovery and direct call are blocked.
> 4. Add a principal-specific server capability and explain why discovery must remain privately cached.
> 5. Write a legacy adapter interface without adding any legacy state to the modern `Gateway` class.

## Key Terms · 术语表

| 术语 | 含义 |
|------|---------|
| MCP 网关（MCP gateway） | 位于客户端与后端 MCP 服务器之间的策略与路由服务器 |
| 准入记录（Admission record） | 允许一个后端进入网关的证据与策略决策 |
| 限定工具名（Qualified tool name） | 稳定的公开路由，例如 `notes.search` |
| 描述符固定（Descriptor pin） | 在发现与分发时校验的已批准摘要 |
| 私有缓存范围（Private cache scope） | 限定在单个授权上下文内的缓存结果 |
| 请求级 SSE（Request-scoped SSE） | 附加到单个 POST 请求的流式响应 |
| `subscriptions/listen` | 客户端打开的 SSE 流，用于接收选定的长连接变更通知 |
| 任务路由（Task route） | 从不透明任务 id 到其后端的应用层映射 |
| 遗留适配器（Legacy adapter） | 面向旧握手与会话行为的、显式按版本门控的边界 |

> | Term | Meaning |
> | MCP gateway | Policy and routing server between clients and backend MCP servers |
> | Admission record | Evidence and policy decision allowing one backend into the gateway |
> | Qualified tool name | Stable public route such as `notes.search` |
> | Descriptor pin | Approved digest checked during discovery and dispatch |
> | Private cache scope | Cached result restricted to one authorization context |
> | Request-scoped SSE | Streaming response attached to one POST request |
> | `subscriptions/listen` | Client-opened SSE stream for selected long-lived change notifications |
> | Task route | Application mapping from an opaque task id to its backend |
> | Legacy adapter | Explicit version-gated boundary for old handshake and session behavior |

## Further Reading · 延伸阅读

- [Streamable HTTP transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) —— Streamable HTTP 传输规范
- [Server discovery](https://modelcontextprotocol.io/specification/2026-07-28/server/discover) —— 服务器发现规范
- [Official Registry server.json requirements](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/official-registry-requirements.md) —— 官方注册表的 server.json 要求
- [MCP Tasks extension](https://tasks.extensions.modelcontextprotocol.io/specification/draft/tasks) —— MCP Tasks 扩展规范
