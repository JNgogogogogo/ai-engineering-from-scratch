# Building an MCP Client: Discovery, Routing, and Dual-Era Fallback · 构建 MCP 客户端：发现、路由与双时代回退

> A modern MCP client repeats its contract on every request. Its hardest compatibility decision is knowing when an old server is truly old and when a modern server is reporting a correctable error.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 13, Lesson 07
**Time:** ~85 minutes

## Learning Objectives · 学习目标

- 让每个 MCP `2026-07-28` 请求都携带当前元数据来构造。
- 用 `server/discover` 探测 stdio 服务器，并选出一个双方都支持的版本。
- 只对显式列入允许名单的对端进行有界的旧版探测授权。
- 只有在校验了针对受支持修订版的正面 `initialize` 结果之后，才接受旧时代。
- 合并确定性工具列表，且不悄悄覆盖重名。
- 把调用路由到拥有该工具的对端，而不发明协议会话。

> Build every MCP `2026-07-28` request with current metadata.
> Probe stdio servers with `server/discover` and select a mutually supported version.
> Authorize a bounded legacy probe only for explicitly allowlisted peers.
> Accept a legacy era only after validating a positive `initialize` result for a supported revision.
> Merge deterministic tool lists without silently overwriting collisions.
> Route calls to the peer that owns each tool without inventing protocol sessions.

## The Problem · 问题所在

一个 agent 宿主通常要同时和多个 MCP 服务器对话。它必须发现每台服务器、合并工具目录、解决重名、路由调用，并从传输故障中恢复。

`2026-07-28` 修订版让稳态更简单，因为每个请求都是自包含的。兼容性则让启动过程更微妙。客户端可能遇到：

- 支持首选版本的现代服务器；
- 返回可识别的版本错误或头部错误的现代服务器；
- 从没听说过 `server/discover` 的旧版服务器；
- 在收到 `initialize` 之前保持沉默的旧版服务器。

把每个探测错误都当成旧版是危险的。一个畸形的现代请求、一台过载的服务器、一个已死的进程和一台真正的旧服务器，都可能产生同样的超时或连接关闭。这些信号是含糊的。在选择旧时代之前，客户端必须把显式的运维意图与正面的协议证据结合起来。

> An agent host usually talks to more than one MCP server. It must discover each server, merge tool catalogs, resolve duplicate names, route calls, and recover from transport failure.
> The `2026-07-28` revision makes the steady state simpler because each request is self-contained. Compatibility makes startup more subtle. A client may encounter:
> - a modern server that supports the preferred version;
> - a modern server that returns a recognized version or header error;
> - a legacy server that has never heard of `server/discover`;
> - a legacy server that stays silent until it receives `initialize`.
> Treating every probe error as legacy is dangerous. A malformed modern request, an overloaded server, a dead process, and an old server can all produce the same timeout or connection close. Those signals are ambiguous. The client must combine explicit operator intent with positive protocol evidence before it chooses the legacy era.

## The Concept · 核心概念

### A peer, not a protocol session · 记录对端，而非协议会话

为每个服务器进程或端点保留一条传输对端（peer）记录：

- 传输句柄或发送函数；
- 选定的协议时代与版本；
- 最近一次发现的服务器能力；
- 最近一次确定性工具列表；
- 用于关联的待决请求 id；
- 传输健康状况。

这是客户端的簿记，不是协议会话状态。在现代 MCP 上，服务器依然会在每个请求中收到当前的版本与能力。

> Keep one transport peer record for each server process or endpoint:
> - transport handle or send function;
> - selected protocol era and version;
> - last discovered server capabilities;
> - last deterministic tool list;
> - pending request ids for correlation;
> - transport health.
> This is client bookkeeping. It is not protocol session state. On modern MCP, the server still receives current version and capabilities on every request.

### Build every modern request from scratch · 每个现代请求都从头构造

```python
def modern_request(request_id, method, params, version, capabilities):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": {
            **params,
            "_meta": {
                "io.modelcontextprotocol/protocolVersion": version,
                "io.modelcontextprotocol/clientCapabilities": capabilities,
                "io.modelcontextprotocol/clientInfo": CLIENT_INFO,
            },
        },
    }
```

不要把元数据一次性挂到连接对象上就假设它已经上了线。要在最终序列化的请求上打戳并检查它。

> Do not attach metadata once to a connection object and assume it reached the wire. Stamp and inspect the final serialized request.

### Modern discovery · 现代发现

`server/discover` 返回受支持的版本、服务器能力、说明、缓存提示以及推荐的服务器身份。客户端选择双方都支持的最高的现代版本。

对只支持现代版的客户端来说，发现是可选的，但在 stdio 上推荐使用。有些旧版服务器会在初始化之前就接受操作，因此先发 `tools/list` 可能得到一个含义模糊的成功。`server/discover` 划出了一条干净的时代边界。

> `server/discover` returns supported versions, server capabilities, instructions, cache hints, and recommended server identity. A client chooses the highest mutually supported modern version.
> Discovery is optional for a modern-only client, but it is recommended on stdio. Some legacy servers accept an operation before initialization, so sending `tools/list` first can produce an ambiguous success. `server/discover` creates a clean era boundary.

### The stdio compatibility probe · stdio 兼容性探测

双时代 stdio 客户端在发送任何其他请求之前，先带上自己首选的现代元数据发送 `server/discover`。结果有三类：

1. **DiscoverResult。** 服务器是现代的。选出一个双方都支持的版本，继续用逐请求元数据。
2. **可识别的现代错误。** 服务器是现代的。对 `-32022`，从 `data.supported` 中选择并用新的请求 id 重试；对头部或能力错误，修正请求。不要发送 `initialize`。
3. **含糊信号。** 无法识别的 JSON-RPC 错误、超时、连接关闭或空响应都不能判定时代。除非该确切对端被配置为旧版兼容，否则一律失败关闭（fail closed）。

可识别的现代协议错误包括：

- `-32020` HeaderMismatch
- `-32021` MissingRequiredClientCapability
- `-32022` UnsupportedProtocolVersion

即使对端在旧版允许名单上，可识别的现代错误仍然属于现代。一旦服务器证明它听得懂现代错误词汇，再发送 `initialize` 就是一次降级。

不要把 `-32601` 当作正面的旧版证据。它只是让一个被显式列入允许名单的对端有资格做一次旧版探测。同样的规则适用于超时、连接关闭或空响应。

> A dual-era stdio client sends `server/discover` with its preferred modern metadata before any other request. There are three outcome classes:
> 1. **DiscoverResult.** The server is modern. Select a mutually supported version and continue with per-request metadata.
> 2. **Recognized modern error.** The server is modern. For `-32022`, choose from `data.supported` and retry with a new request id. For header or capability errors, correct the request. Do not send `initialize`.
> 3. **Ambiguous signal.** An unrecognized JSON-RPC error, timeout, connection close, or empty response does not identify an era. Fail closed unless that exact peer is configured for legacy compatibility.
> Recognized modern errors remain modern even when the peer is on the legacy allowlist. Once a server proves that it understands the modern error vocabulary, sending `initialize` would be a downgrade.
> Do not treat `-32601` as positive legacy evidence. It only makes an explicitly allowlisted peer eligible for one legacy probe. The same rule applies to a timeout, connection close, or empty response.

### Allowlisting is operator intent, not evidence · 允许名单是运维意图，不是证据

旧版兼容必须是某一条固定（pinned）对端配置上的显式属性：

```python
client.add_server("archive", archive_transport, allow_legacy=True)
```

把这个选择绑定到所配置的命令或端点上。不要使用通配符，让任意服务器自行选择更弱的语义。没有 `allow_legacy=True` 的对端在含糊的发现结果之后直接失败，永远不会收到 `initialize`。

允许名单授予的是探测许可，它不选择时代。客户端在传输层强制的截止时间内发送一次 `initialize`，然后要求以下全部条件：

- 带匹配请求 id 的 JSON-RPC `2.0` 响应；
- 恰好一个 `result` 且没有 `error`；
- `protocolVersion` 在客户端配置的旧版修订集合内；
- 对象类型的 `capabilities` 字段；
- `serverInfo` 对象，其 `name` 与 `version` 字段为非空字符串。

超时、连接关闭、错误响应、畸形结果、id 不匹配或不受支持的修订，一律失败关闭。只有结构上合法的正面结果才能选中旧时代。代码把 `legacy_probe_timeout_ms` 传给传输适配器；真正的 stdio 或 HTTP 适配器必须强制执行这个截止时间，而不是仅仅记录它。

把选中的时代缓存到该传输对端上。不要在每次调用前重新探测。

> Legacy compatibility must be an explicit property of one pinned peer configuration:
> Bind that choice to the configured command or endpoint. Do not use a wildcard that lets an arbitrary server opt itself into weaker semantics. A peer without `allow_legacy=True` fails after an ambiguous discovery outcome and never receives `initialize`.
> The allowlist grants permission to probe. It does not select the era. The client sends one `initialize` under a transport-enforced deadline, then requires all of the following:
> - a JSON-RPC `2.0` response with the matching request id;
> - exactly one `result` and no `error`;
> - a `protocolVersion` in the client's configured legacy revision set;
> - an object-valued `capabilities` field;
> - a `serverInfo` object with non-empty string `name` and `version` fields.
> A timeout, connection close, error response, malformed result, mismatched id, or unsupported revision fails closed. Only a structurally valid positive result selects the legacy era. The code passes `legacy_probe_timeout_ms` to the transport adapter; a real stdio or HTTP adapter must enforce that deadline rather than merely record it.
> Cache the selected era for the transport peer. Do not probe again before every call.

### Legacy is a compatibility branch · 旧版只是一条兼容分支

一旦有界探测返回了合法的正面旧版证据，客户端就严格按照该修订的定义使用选中的旧版版本：

1. 校验响应信封和关联 id。
2. 校验协商出的修订在配置的旧版集合内。
3. 记录通过校验的能力与服务器身份。
4. 只有全部检查通过后才发送 `notifications/initialized`。
5. 在该传输生命周期内使用旧版请求形状。

这条分支只为与已知对端互操作而存在。它不是新服务器或新请求的默认设计。如果传输重启或端点变化，丢弃对端时代缓存并重新协商。

> Once the bounded probe returns valid positive legacy evidence, the client uses the selected legacy version exactly as defined by that revision:
> This branch exists for interoperability with known peers. It is not the default design for new servers or new requests. If the transport restarts or its endpoint changes, discard the peer-era cache and negotiate again.

### Discovering and caching tools · 发现并缓存工具

对每个活跃对端调用 `tools/list`。现代结果包含 `resultType`、`ttlMs` 与 `cacheScope`。在正确的授权上下文内遵守新鲜度提示；过期之后或收到订阅的列表变更事件时重新拉取。

对来自旧版服务器、缺失 `resultType` 的响应，客户端必须视为 `"complete"`。不要对更早时代协商出的响应要求现代缓存字段。

服务器应当返回确定性排序。客户端在合并前也应自行排序，这样本地注册表的顺序就不依赖进程启动的时序。

> For each active peer, call `tools/list`. A modern result includes `resultType`, `ttlMs`, and `cacheScope`. Honor the freshness hint within the correct authorization context. Re-fetch after expiry or a subscribed list-change event.
> Clients must treat a missing `resultType` from a legacy server as `"complete"`. Do not require modern cache fields on a response from an earlier negotiated era.
> The server should return deterministic ordering. The client should also sort before merging so local registry order does not depend on process startup timing.

### Collision-safe namespace merge · 防冲突的命名空间合并

两台服务器可能都暴露 `search`。要选一个明确声明的策略：

1. **冲突时加前缀。** 保留第一个规范名，把后续冲突以 `<server>/<tool>` 暴露。
2. **冲突时拒绝。** 不加载重复项，并给出清晰的配置错误。
3. **静默覆盖。** 绝不要用。它会掩盖模型选择的动作到底发给了哪台服务器。

同时保存规范名和本地名。模型看到规范名。发出的 `tools/call` 使用属主服务器声明的本地名。

> Two servers may both expose `search`. Choose a declared policy:
> 1. **Prefix on collision.** Keep the first canonical name and expose later collisions as `<server>/<tool>`.
> 2. **Reject on collision.** Do not load the duplicate and surface a clear configuration error.
> 3. **Silent overwrite.** Never use this. It hides which server receives a model-selected action.
> Store both canonical and local names. The model sees the canonical name. The outgoing `tools/call` uses the local name the owning server declared.

### Routing a call · 路由一次调用

路由是一次纯粹的查表：

```text
canonical tool name
  -> peer name + local tool name
  -> new JSON-RPC request id
  -> modern request metadata or explicit legacy shape
  -> matching response id
```

当调用所属的传输不可用时，不要发送。重连或重启传输，然后重新运行发现和 `tools/list`。因传输断开而丢失的现代在途请求，在该操作的安全策略允许时，可以用新的 JSON-RPC id 重试。

> Routing is a pure lookup:
> Do not send a call when its owning transport is unavailable. Reconnect or restart the transport, then re-run discovery and `tools/list`. Modern in-flight requests lost on a broken transport can be retried with a new JSON-RPC id when the operation's safety policy permits it.

### Notifications and subscriptions · 通知与订阅

现代的列表与资源变更只会通过客户端打开的 `subscriptions/listen` 流到达。客户端发送通知过滤器，等待 `notifications/subscriptions/acknowledged`，并用通知元数据中的 listen 请求 id 关联事件。

断连后，打开一个新的 listen 请求并重新拉取相关的列表或资源。现代流不支持用 `Last-Event-ID` 恢复。

> Modern list and resource changes arrive only on a client-opened `subscriptions/listen` stream. The client sends the notification filter, waits for `notifications/subscriptions/acknowledged`, and correlates events with the listen request id in notification metadata.
> On disconnect, open a new listen request and refetch relevant lists or resources. Modern streams do not resume with `Last-Event-ID`.

### No server-initiated requests · 服务器不主动发起请求

现代服务器不会用独立的 JSON-RPC 请求反向调用客户端来获取 sampling、elicitation 或 roots。它们返回 `input_required`，客户端在完成内嵌输入请求后重试原请求。

在补齐输入时，不要阻塞该对端的响应读取器。保持关联，并为重试创建新的 JSON-RPC id。

```figure
tp-client-merge
```

> Modern servers do not call the client with independent JSON-RPC requests for sampling, elicitation, or roots. They return `input_required`, and the client retries the original request after fulfilling the embedded input requests.
> Do not block the peer's response reader while fulfilling input. Preserve correlation and create a new JSON-RPC id for the retry.

## Use It · 实战用法

`code/main.py` 使用进程内的对端函数，让协议决策保持可见。它连接两个现代对端和一个被有意列入允许名单的旧版对端，然后合并并路由它们的工具。传输可调用对象会收到一个超时预算，这样兼容分支就无法藏起一个无界的探测。

```bash
cd code
python3 main.py
python3 -m unittest discover tests -v
```

测试证明了普通演示覆盖不到的边界：

- 现代请求重复携带元数据；
- `-32022` 触发不初始化的现代发现重试；
- 可识别的现代错误绝不降级，即使对端在允许名单上；
- 没有允许名单时，超时、连接关闭、空响应和无法识别的错误都不会触发 `initialize`；
- 被列入名单的对端只有在收到合法且受支持的 `initialize` 结果后才进入旧版；
- 畸形和不受支持的旧版结果让对端保持不可用；
- 成功选中的时代会缓存整个传输生命周期。

> `code/main.py` uses in-process peer functions so the protocol decisions stay visible. It connects to two modern peers and one intentionally allowlisted legacy peer, then merges and routes their tools. The transport callable receives a timeout budget so the compatibility branch cannot hide an unbounded probe.
> The tests prove boundaries that normal demos miss:
> - modern requests repeat metadata;
> - `-32022` retries modern discovery without initialization;
> - recognized modern errors never downgrade, even for an allowlisted peer;
> - timeouts, connection closes, empty responses, and unrecognized errors do not trigger `initialize` without an allowlist;
> - an allowlisted peer becomes legacy only after a valid, supported `initialize` result;
> - malformed and unsupported legacy results leave the peer unavailable;
> - a successfully selected era is cached for the transport lifetime.

## Ship It · 交付

本课交付 `outputs/skill-mcp-client-harness.md`。它搭出现代请求打戳、stdio 时代协商、确定性命名空间合并、路由，以及失败关闭的旧版兼容分支的脚手架。

> This lesson ships `outputs/skill-mcp-client-harness.md`. It scaffolds modern request stamping, stdio era negotiation, deterministic namespace merge, routing, and a fail-closed legacy compatibility branch.

## Exercises · 练习

1. 让一个假服务器返回没有共同支持版本的 `-32022`。确认客户端直接失败，而不是发送 `initialize`。
2. 把一个假旧版服务器列入允许名单，让它的有界 `initialize` 探测超时，并证明该对端保持 `unknown` 且不可用。
3. 为两个授权上下文分别添加 `cacheScope: "private"` 的工具列表。确认客户端绝不把一个上下文的缓存结果分享给另一个。
4. 把冲突策略改成拒绝，并让启动失败时报错中包含两个对端的名字。
5. 增加一个有限的 `subscriptions/listen` 模拟器。流断开后，用新的请求 id 重新 listen 并重新拉取工具。

> 1. Make a fake server return `-32022` with no mutually supported version. Confirm the client fails instead of sending `initialize`.
> 2. Allowlist a fake legacy server, make its bounded `initialize` probe time out, and prove the peer stays `unknown` and unavailable.
> 3. Add `cacheScope: "private"` tool lists for two authorization contexts. Confirm the client never shares one context's cached result with the other.
> 4. Change the collision policy to rejection and make startup fail with both peer names in the error.
> 5. Add a finite `subscriptions/listen` simulator. On stream loss, re-listen with a new request id and refetch tools.

## Key Terms · 术语表

| 术语 | 含义 |
|------|---------|
| 对端（Peer） | 客户端为一条服务器传输及其发现数据保存的记录 |
| 协议时代（Protocol era） | 现代的逐请求元数据，或旧版的初始化语义 |
| 发现探测（Discovery probe） | 用来识别 stdio 时代的首次 `server/discover` |
| 可识别的现代错误（Recognized modern error） | 证明对方是现代行为、禁止旧版回退的错误 |
| 旧版允许名单（Legacy allowlist） | 允许对某个固定对端做一次有界兼容探测的运维配置 |
| 正面旧版证据（Positive legacy evidence） | 针对显式受支持的旧版修订、合法且关联正确的 `initialize` 结果 |
| 合并命名空间（Merged namespace） | 跨所有活跃对端的规范工具名 |
| 冲突策略（Collision policy） | 对重复工具名的前缀或拒绝规则 |
| 时代缓存（Era cache） | 为一条传输对端保存的所选现代或旧行为 |
| 传输恢复（Transport recovery） | 重启或重连、重新发现、重新列表，并用新 id 安全重试 |

> | Term | Meaning |
> |------|---------|
> | Peer | Client-side record for one server transport and its discovered data |
> | Protocol era | Modern per-request metadata or legacy initialization semantics |
> | Discovery probe | Initial `server/discover` used to identify the stdio era |
> | Recognized modern error | Error that proves modern behavior and forbids legacy fallback |
> | Legacy allowlist | Operator configuration permitting one bounded compatibility probe for a pinned peer |
> | Positive legacy evidence | Valid, correlated `initialize` result for an explicitly supported legacy revision |
> | Merged namespace | Canonical tool names across all active peers |
> | Collision policy | Prefix or reject rule for duplicate tool names |
> | Era cache | Selected modern or legacy behavior stored for one transport peer |
> | Transport recovery | Restart or reconnect, rediscover, relist, and retry safely with a new id |

## Further Reading · 延伸阅读

- [MCP Specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/)
- [MCP Server Discovery](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
- [MCP stdio Transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)
- [MCP Versioning](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning)
- [MCP Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
