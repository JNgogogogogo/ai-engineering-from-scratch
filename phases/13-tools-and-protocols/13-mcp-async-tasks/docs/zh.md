# MCP Tasks Extension: Durable Work on a Stateless Core · MCP Tasks 扩展：无状态核心上的持久化工作

> 无状态 MCP 并不意味着每个操作都必须在一次请求内完成。官方 Tasks 扩展为长时运行的工作提供了显式的持久句柄（durable handle）：服务器可以在 `tools/call` 里返回这个句柄，任何实例都能应答 `tasks/get`，而客户端输入通过 `tasks/update` 到达，无需复活任何协议会话。

> Stateless MCP does not mean every operation must finish in one request. The official Tasks extension gives long-running work an explicit durable handle. A server can return that handle from `tools/call`, any instance can answer `tasks/get`, and client input arrives through `tasks/update` without reviving protocol sessions.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 13 · 09 (transports), Phase 13 · 11 (stateless MRTR), Phase 13 · 12 (elicitation)
**Time:** ~90 minutes

## Learning Objectives · 学习目标

- 区分无状态的协议传输与持久化的应用层任务状态。
- 在每请求能力（per-request capabilities）和 `server/discover` 中协商 `io.modelcontextprotocol/tasks` 扩展。
- 只有在持久化创建完成之后，才返回服务器主导（server-directed）的 `CreateTaskResult`（`resultType: "task"`）。
- 用 `tasks/get` 轮询，用 `tasks/update` 提交任务输入，用 `tasks/cancel` 请求协作式取消。
- 摒弃旧的 `tasks/status`、`tasks/result` 和 `tasks/list` 假设。
- 通过 POST 响应 SSE 流上的 `subscriptions/listen` 订阅可选的任务通知。
- 正确建模任务过期、重启恢复、输入键去重与执行错误。

> Distinguish stateless protocol transport from durable application task state.
> Negotiate the `io.modelcontextprotocol/tasks` extension in per-request capabilities and `server/discover`.
> Return a server-directed `CreateTaskResult` with `resultType: "task"` only after durable creation.
> Poll with `tasks/get`, fulfill task input with `tasks/update`, and request cooperative cancellation with `tasks/cancel`.
> Remove the older `tasks/status`, `tasks/result`, and `tasks/list` assumptions.
> Subscribe to optional task notifications through `subscriptions/listen` on a POST response SSE stream.
> Model task expiry, restart recovery, input-key deduplication, and execution errors correctly.

## Why Tasks Are an Extension · 为什么 Tasks 是一个扩展

Tasks 最早在 2025-11-25 作为实验性核心功能出现。2026 年 7 月的重新设计把它们移进了官方的 `io.modelcontextprotocol/tasks` 扩展，让客户端和服务器可以选择性启用（opt in）这套额外的生命周期，而不必为所有人扩张核心协议。

尽管扩展规范是 Tasks 当前官方的归宿，它仍是一份草案（draft）表面。请固定（pin）你的 SDK 所支持的扩展版本，运行一致性（conformance）场景，并把线上协议适配器与你的 worker 和存储领域隔离开。

当操作具备下面一条或多条性质时，才使用任务：

- 它的生命周期可能超过一次普通请求的超时。
- 执行本来就归 worker 队列或外部作业系统所有。
- 客户端需要在自己重启之后恢复。
- 操作在执行中途暂停，等待用户或模型输入。
- 取消与持久化结果读取是产品需求。

不要为一次廉价的确定性查询创建任务。句柄、持久化、轮询、过期和取消都是实打实的复杂度。

> Tasks first appeared as an experimental core feature in 2025-11-25. The July 2026 redesign moves them into the official `io.modelcontextprotocol/tasks` extension so clients and servers can opt into the extra lifecycle without expanding the core protocol for everyone.
> The extension specification remains a draft surface even though it is the current official home for Tasks.
> Use a task when the operation has one or more of these properties... Do not create a task for a cheap deterministic lookup. A handle, persistence, polling, expiry, and cancellation are real complexity.

## Stateless Core, Stateful Application · 无状态核心，有状态应用

MCP 2026-07-28 移除了 `initialize`、`notifications/initialized`、协议会话和 `Mcp-Session-Id`。这并不禁止有状态的产品。

任务 id 是显式的应用状态：

- 服务器在返回它之前先持久化它。
- 客户端可以把它存下来，在重启之后继续轮询。
- 这个 id 可以路由到由同一个持久存储支撑的任何副本。
- 每个任务方法上都会检查授权。
- 过期与删除由任务字段定义，而不是由传输层的寿命定义。

这在运维上与挂在连接上的隐藏状态完全不同。

把四种寿命分开保管：

| 状态 | 寿命 | 归属 |
|---|---|---|
| 协议元数据（protocol metadata） | 单次请求 | `params._meta`，每次调用都重新验证 |
| 传输层工作（transport work） | 一个 stdio 请求或 HTTP 响应 | 有截止期限的进行中协调器（in-flight coordinator） |
| MRTR 续传（continuation） | 一个重试序列 | 完整性保护的 `requestState`，必要时加上重放控制 |
| 持久任务（durable task） | 跨请求、副本、重启与重连 | 由经授权的 `taskId` 索引的共享应用存储 |

把任务记录挪进进程内存并不能让 MCP 变成有状态——只会让应用变得不可靠。协议保持无状态，但一个路由到另一个副本的后续 `tasks/get` 无法找回这条记录。先持久化再返回句柄，然后让每个任务方法都在租户（tenant）与主体（principal）检查下解析同一条共享记录。

> MCP 2026-07-28 removes `initialize`, `notifications/initialized`, protocol sessions, and `Mcp-Session-Id`. That does not prohibit stateful products.
> A task id is explicit application state: the server persists it before returning it... Persist before returning the handle, then make every task method resolve the same shared record under tenant and principal checks.
> Moving a task record into process memory does not make MCP stateful. It makes the application unreliable.

## Capability Negotiation · 能力协商

客户端在每个符合条件的请求上声明支持：

```json
{
  "_meta": {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientCapabilities": {
      "extensions": {
        "io.modelcontextprotocol/tasks": {}
      }
    },
    "io.modelcontextprotocol/clientInfo": {
      "name": "lesson-client",
      "version": "1.0.0"
    }
  }
}
```

服务器通过 `server/discover` 返回精确的 `supportedVersions`、能力、`ttlMs` 和 `cacheScope`，并在 capabilities 里带上同一个扩展。因为它声明了 tools，所以它也实现强制的 `tools/list`。该结果返回一个确定性的 `generate_report` 描述符、合法的对象 `inputSchema`、`resultType: "complete"`、服务器身份元数据和公开的缓存提示。

来自未声明该扩展的客户端的任务方法会返回 `-32021`（Missing Required Client Capability），并带上 `data.requiredCapabilities` = `{"extensions":{"io.modelcontextprotocol/tasks":{}}}`。不支持的协议字符串返回 `-32022`，数据里带精确的 `supported` 与 `requested`；缺失或非字符串的版本返回 `-32602`。

没有 JSON-RPC `id` 的信封是一条通知（notification）。接收方可以处理它，但不会发出任何 JSON-RPC 结果或错误。Streamable HTTP 适配器对已接受的通知返回不带正文的 `202 Accepted`。

目前只有 `tools/call` 支持任务增强执行。设计内部抽象时，要让未来的请求类型不需要重写存储。

> The server returns exact `supportedVersions`, capabilities, `ttlMs`, and `cacheScope` from `server/discover`, with the same extension under capabilities.
> A task method from a client that did not declare the extension returns `-32021`, Missing Required Client Capability... An envelope without a JSON-RPC `id` is a notification. The receiver may process it, but it emits no JSON-RPC result or error.
> At present, only `tools/call` supports task-augmented execution.

## Server-Directed Task Creation · 服务器主导的任务创建

旧的客户端标志 `params._meta.task.required` 已经移除。客户端声明扩展支持，然后由服务器决定某一次具体的 `tools/call` 是否变成任务。

请求（Request）：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "generate_report",
    "arguments": {"size": "large"},
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "extensions": {
          "io.modelcontextprotocol/tasks": {}
        }
      }
    }
  }
}
```

响应（Response）：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "task",
    "taskId": "tsk_786512e29e0d",
    "status": "working",
    "statusMessage": "Preparing report outline.",
    "createdAt": "2026-08-21T10:30:00Z",
    "lastUpdatedAt": "2026-08-21T10:30:00Z",
    "ttlMs": 900000,
    "pollIntervalMs": 1000
  }
}
```

在一个针对该 id 的 `tasks/get` 能够解析之前，服务器绝不能返回这个句柄。在最终一致（eventually consistent）的存储里，先等到读可见再应答。否则客户端可能拿到一个看起来合法的 id，然后立刻得到「not found」。

任务响应是「非请求性的（unsolicited）」：客户端并没有请求任务模式。但它不是未协商的：当前请求仍然必须声明该扩展。

> The old client flag `params._meta.task.required` is gone. The client declares extension support, then the server decides whether a particular `tools/call` becomes a task.
> The server must not return this handle until a `tasks/get` for the id can resolve.
> A task response is unsolicited in the sense that the client does not request task mode. It is not unnegotiated: the current request still must advertise the extension.

## The Task Shape · 任务的形状

每个任务携带：

- `taskId`：稳定的服务器生成的标识符；
- `status`：`working`、`input_required`、`completed`、`cancelled` 或 `failed`；
- `createdAt` 与 `lastUpdatedAt`：ISO 8601 时间戳；
- `ttlMs`：自创建起算的过期时长，`null` 表示没有声明的上限；
- 可选的 `pollIntervalMs`：服务器当前建议的最小轮询节奏；
- 可选的 `statusMessage`：面向用户或面向模型的上下文。

状态专属字段只在相关时出现：

- `input_required` 包含 `inputRequests`。
- `completed` 包含原始请求的 `result` 形状。
- `failed` 包含一个 JSON-RPC `error` 对象。

客户端应当遵守 `pollIntervalMs`。服务器可以对更激进的轮询限速，并可以在任务生命周期内改变这个间隔。

> Status-specific fields appear only when relevant: `input_required` includes `inputRequests`. `completed` includes the original request's `result` shape. `failed` includes a JSON-RPC `error` object.
> The client should honor `pollIntervalMs`. A server may rate-limit more aggressive polling and may change the interval over the task lifetime.

## Poll with `tasks/get` · 用 `tasks/get` 轮询

客户端请求当前快照：

```http
POST /mcp HTTP/1.1
Content-Type: application/json
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tasks/get
Mcp-Name: tsk_786512e29e0d
```

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tasks/get",
  "params": {
    "taskId": "tsk_786512e29e0d",
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "extensions": {
          "io.modelcontextprotocol/tasks": {}
        }
      }
    }
  }
}
```

`tasks/get` 这个调用本身已经完成，所以它的 result 永远是 `resultType: "complete"`。被表示的那个任务仍可能处于 `status: "working"` 或 `status: "input_required"`。

这个区别防止一个常见的解析器 bug：

```text
result.resultType = complete    means the tasks/get RPC finished
result.status = working        means the represented job is still running
```

没有 `tasks/result` 这个调用。任务完成时，下一次 `tasks/get` 的响应会把原始的 `CallToolResult` 内联在 `result` 之下：

```json
{
  "resultType": "complete",
  "taskId": "tsk_786512e29e0d",
  "status": "completed",
  "createdAt": "2026-08-21T10:30:00Z",
  "lastUpdatedAt": "2026-08-21T10:34:12Z",
  "ttlMs": 900000,
  "result": {
    "resultType": "complete",
    "content": [
      {"type": "text", "text": "Generated large report with approved outline."}
    ],
    "structuredContent": {"size": "large", "approved": true},
    "isError": false,
    "_meta": {
      "io.modelcontextprotocol/serverInfo": {
        "name": "tasks-demo",
        "version": "1.0.0"
      }
    }
  },
  "_meta": {
    "io.modelcontextprotocol/serverInfo": {
      "name": "tasks-demo",
      "version": "1.0.0"
    }
  }
}
```

外层的 `resultType` 说明 `tasks/get` 这个 RPC 完成了。嵌套的 `result.resultType` 说明原始的工具调用完成了。这个嵌套判别字段是必需的。嵌套的 `CallToolResult` 还应当（SHOULD）携带它自己的 `io.modelcontextprotocol/serverInfo`；本课选择包含它，而不是存储一个无类型的载荷。

没有 `tasks/list`。无会话的服务器无法安全地推断哪些任务属于某个按连接划分的列表。需要历史记录的应用应该暴露一个经授权的领域工具，带上显式的过滤与归属规则。

> `tasks/get` itself completed, so its result always has `resultType: "complete"`. The nested task can still have `status: "working"` or `status: "input_required"`.
> There is no `tasks/result` call. When the task completes, the next `tasks/get` response inlines the original `CallToolResult` under `result`.
> The outer `resultType` says the `tasks/get` RPC completed. The nested `result.resultType` says the original tool call completed. That nested discriminator is required.
> There is no `tasks/list`. Sessionless servers cannot safely infer which tasks belong in a connection-scoped list.

## Input During Task Execution · 任务执行期间的输入

任务输入与核心 MRTR 看起来相似，但使用不同的续传（continuation）方式。

### Input needed before task creation · 任务创建之前需要的输入

从原始的 `tools/call` 返回核心的 `resultType: "input_required"`。客户端完成输入并重试那次原始调用。只有在这些同步的 MRTR 轮次结束之后才创建任务。

> Return core `resultType: "input_required"` from the original `tools/call`. The client fulfills it and retries that original call. Only create the task after those synchronous MRTR rounds finish.

### Input needed after task creation · 任务创建之后需要的输入

把任务置为 `input_required`。`tasks/get` 会暴露未完成的 `inputRequests`，客户端通过 `tasks/update` 发送响应。客户端不重试原始的 `tools/call`。

快照（Snapshot）：

```json
{
  "resultType": "complete",
  "taskId": "tsk_786512e29e0d",
  "status": "input_required",
  "createdAt": "2026-08-21T10:30:00Z",
  "lastUpdatedAt": "2026-08-21T10:31:00Z",
  "ttlMs": 900000,
  "inputRequests": {
    "approve_outline": {
      "method": "elicitation/create",
      "params": {
        "mode": "form",
        "message": "Approve the generated report outline?",
        "requestedSchema": {
          "type": "object",
          "properties": {"approved": {"type": "boolean"}},
          "required": ["approved"]
        }
      }
    }
  }
}
```

更新（Update）：

```http
POST /mcp HTTP/1.1
Content-Type: application/json
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tasks/update
Mcp-Name: tsk_786512e29e0d
```

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tasks/update",
  "params": {
    "taskId": "tsk_786512e29e0d",
    "inputResponses": {
      "approve_outline": {
        "action": "accept",
        "content": {"approved": true}
      }
    },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "extensions": {
          "io.modelcontextprotocol/tasks": {}
        }
      }
    }
  }
}
```

成功响应是一个空确认（acknowledgement）加上 `resultType: "complete"`。状态变更可能是最终一致的，所以客户端要继续轮询或监听。

每个 `inputRequests` 键在整个任务生命周期内必须唯一。重复的 `tasks/get` 快照可能显示同一个未完成键；客户端在 UI 上做去重，服务器忽略针对未知、已被取代或已满足键的响应。一次部分更新会让任务停留在 `input_required`，直到所有必需的键都被应答。

> Set the task to `input_required`. `tasks/get` exposes the outstanding `inputRequests`, and the client sends responses through `tasks/update`. The client does not retry the original `tools/call`.
> Each `inputRequests` key must be unique for the entire task lifetime... A partial update can leave the task in `input_required` until all required keys are answered.

## Cancellation Is Cooperative · 取消是协作式的

`tasks/cancel` 表达意图并返回一个空的完成确认。这个确认不保证 worker 已经停止。工作可能先完成、忽略取消，或稍后再转换状态。

```http
POST /mcp HTTP/1.1
Content-Type: application/json
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tasks/cancel
Mcp-Name: tsk_786512e29e0d
```

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tasks/cancel",
  "params": {
    "taskId": "tsk_786512e29e0d",
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "extensions": {
          "io.modelcontextprotocol/tasks": {}
        }
      }
    }
  }
}
```

对全部三个任务方法来说，`Mcp-Name` 镜像 `params.taskId`。它不重复 JSON-RPC 方法名。`code/main.py` 把这条规则集中在 `make_http_request` 里。

本课的 worker 立即服从取消，让重复调用具有幂等性。生产客户端仍必须把取消视为协作式的，而不是从确认里推断任务的最终状态。

不要用 `notifications/cancelled` 去取消任务。那条通知属于请求取消（request cancellation），不属于持久化的 Tasks。

这个区别在路由边界处至关重要。请求取消针对的是一个进行中的 JSON-RPC 操作或它请求范围的 HTTP 响应。如果 `tools/call` 已经返回了 `resultType: "task"`，那个请求就已完成，关闭它的传输既无法指名、也无法停止那个持久作业。`tasks/cancel` 是一个新的经授权 RPC：它携带 `params.taskId`，在 `Mcp-Name` 里镜像这个 id，解析任务所属的后端，记录协作式取消意图，并返回一个不声称 worker 已停止的确认。

因此，网关必须把请求协调器和任务路由放在不同的表里。请求表可以在响应结束时消失；任务路由必须存活到终止状态与保留期（retention）过期为止。[Lesson 29: MCP Reliability, Cancellation, and Flow Control](../../29-mcp-reliability-cancellation-and-flow-control/docs/en.md) 为这两条路径构建了竞态、超时、幂等、背压与重试规则。

> `tasks/cancel` signals intent and returns an empty complete acknowledgement. That acknowledgement does not guarantee the worker stopped.
> Do not use `notifications/cancelled` to cancel a task. That notification belongs to request cancellation, not durable Tasks.
> A gateway must therefore keep request coordinators and task routes in different tables. The request table can disappear when the response finishes. The task route must survive until terminal state and retention expiry.

## Optional Notifications · 可选通知

轮询是基线。想要推送更新的客户端携带任务 id 发送 `subscriptions/listen`。对 Streamable HTTP 来说，这是一个响应为请求范围 SSE 流的 POST。没有独立的 GET 事件流，也没有需要保活的协议会话。

服务器用 `notifications/subscriptions/acknowledged` 确认已接受的 id，然后可以通过 `notifications/tasks` 发送完整快照。这条确认与每条任务通知都在 `_meta` 里携带 `io.modelcontextprotocol/subscriptionId`，等于 `subscriptions/listen` 请求的 id。除此之外，每条任务通知都等价于那一刻 `tasks/get` 会返回的内容。

客户端仍必须声明 Tasks 扩展。它们应当基于持久任务 id 重连并恢复，而不是依赖事件重放或 `Last-Event-ID`。

> Polling is the baseline. A client that wants push updates sends `subscriptions/listen` with task ids. For Streamable HTTP, this is a POST whose response is a request-scoped SSE stream. There is no standalone GET event stream and no protocol session to keep alive.
> The server acknowledges the accepted ids with `notifications/subscriptions/acknowledged` and can then send full snapshots through `notifications/tasks`.
> Clients must still declare the Tasks extension. They should reconnect and resume from durable task ids rather than depend on event replay or `Last-Event-ID`.

## Failure Semantics · 失败语义

正确使用这两个错误层。

### Protocol error · 协议错误

非法的方法参数或未知的任务 id 返回 JSON-RPC 错误，通常是 `-32602`。缺失扩展支持返回 `-32021` 并带上所需的能力对象。

> Invalid method parameters or an unknown task id return a JSON-RPC error, commonly `-32602`. Missing extension support returns `-32021` with the required capability object.

### Task execution outcome · 任务执行结果

- 带有 `isError: true` 的正常工具结果仍是一个 `completed` 任务，因为工具调用产出了它所定义的结果。
- 延迟执行期间出现的 JSON-RPC 错误使任务变为 `failed`，并把该 JSON-RPC 错误存储在 `error` 之下。
- 用户拒绝可能产生 `cancelled`、一个表示拒绝的 completed 结果，或其他领域特定的安全结果。把你的选择写进文档。

> A normal tool result with `isError: true` is still a `completed` task because the tool call produced its defined result.
> A JSON-RPC error during deferred execution makes the task `failed` and stores that JSON-RPC error under `error`.
> User refusal can produce `cancelled`, a completed refusal result, or another domain-specific safe outcome. Document the choice.

## Durability, Expiry, and Ownership · 持久性、过期与归属

至少要持久化：任务 id、状态、时间戳、ttl、轮询间隔、原始操作的归属、结果或错误、未完成的输入请求，以及所有已发出的输入键。

存储键必须包含或解析出一个权威的租户（tenant）与主体（principal）。知道一个任务 id 绝不等于获得访问权。在每次 `tasks/get`、`tasks/update`、`tasks/cancel` 和订阅上都检查归属。

`ttlMs` 从创建起算，并且可以改变。当任务已经停止产生可观察的更新时，客户端可以把它当作兜底。服务器可以让一个过期任务失败、随后删除它。不要把它描述成「任务完成后还要再保留这么多毫秒」的承诺。

使用原子写入或事务。本课写入一个临时文件然后原子重命名。多副本服务应当使用共享持久存储，外加 worker 租约（lease）或等价的并发控制。

```figure
tp-task-lifecycle
```

> Persist at least the task id, status, timestamps, ttl, poll interval, original operation ownership, result or error, outstanding input requests, and all issued input keys.
> The storage key must include or resolve an authoritative tenant and principal. Knowing a task id must not grant access.
> Use atomic writes or transactions. The lesson writes a temporary file and atomically renames it.

## Build It · 动手造

`code/main.py` 实现了一个确定性的任务服务：

- `server/discover` 返回 `supportedVersions`、缓存提示和 Tasks 扩展。
- `tools/list` 返回一个确定性的、可缓存的 `generate_report` 描述符，带合法的输入 schema。
- `tools/call` 在返回 `resultType: "task"` 之前创建并持久化任务。
- 一个新的服务实例会重新加载同一个任务，演示重启恢复。
- `tasks/get` 返回完整的任务快照。
- worker 从 `working` 推进到 `input_required`。
- `tasks/update` 接受表单响应并返回一个空的完成确认。
- worker 存储一个嵌套的 `CallToolResult`（带它自己的 `resultType` 和服务器身份），然后转换到 `completed`。
- `tasks/cancel` 在本实现中是幂等的。
- HTTP 构建器对 `tasks/get`、`tasks/update`、`tasks/cancel` 把 `Mcp-Name` 设为 `params.taskId`。
- 通知助手使用 `notifications/subscriptions/acknowledged` 和 `notifications/tasks`，都带上监听请求的 id。
- 无 id 的通知不产生 JSON-RPC 响应。

worker 显式推进状态，而不是在后台线程里睡眠。这让每一次状态转换都是确定性的，并让协议示例与队列机制保持分离。

> `code/main.py` implements a deterministic task service... The worker advances explicitly instead of sleeping in a background thread. That makes every state transition deterministic and keeps the protocol example separate from queue mechanics.

## Use It · 实战用法

从仓库根目录开始：

```bash
cd phases/13-tools-and-protocols/13-mcp-async-tasks/code
python3 main.py
python3 -m unittest discover tests -v
```

预期的结果序列：

```text
id=0 resultType=complete status=ack
id=1 resultType=task status=working
id=2 resultType=complete status=working
id=3 resultType=complete status=input_required
id=4 resultType=complete status=ack
id=5 resultType=complete status=completed
```

另外验证：`tasks/status`、`tasks/result` 和 `tasks/list` 在这个现代服务里返回 method-not-found。
验证 `tools/list` 是确定性的，并且当前每一个 HTTP 任务方法都通过 `Mcp-Name` 镜像其任务 id。

> Also verify that `tasks/status`, `tasks/result`, and `tasks/list` return method-not-found in the modern service.
> Verify that `tools/list` is deterministic and every current HTTP task method mirrors its task id through `Mcp-Name`.

## Ship It · 交付

`outputs/skill-task-store-designer.md` 现在产出一份扩展感知的设计：能力协商、先持久化再返回的创建、现行方法、输入更新流程、归属、过期、取消、订阅，以及从已被移除的实验性方法的迁移。

> `outputs/skill-task-store-designer.md` now produces an extension-aware design: capability negotiation, durable-before-return creation, current methods, input update flow, ownership, expiry, cancellation, subscription, and migration from the removed experimental methods.

## Exercises · 练习

1. 添加第二个未完成的输入键。发送一个部分 `tasks/update`，证明任务在两个键都被应答之前保持 `input_required`。
2. 给存储添加租户归属，并拒绝由错误的已认证主体出示的合法任务 id。
3. 添加一个带过期的 worker 租约。演示两个服务实例无法并发完成同一个任务。
4. 为 `subscriptions/listen` 实现一个 POST 响应 SSE 适配器。不要添加 GET、`Last-Event-ID` 或会话头。
5. 添加过期清理。把一个已过期的任务与一个格式错误的任务 id 区分开，且不泄露跨租户的存在性。

## Key Terms · 术语表

| 术语 | 在当前扩展中的含义 |
|------|----------------------------------|
| Tasks extension（Tasks 扩展） | 可选的 `io.modelcontextprotocol/tasks` 能力，用于持久化的异步工作 |
| `CreateTaskResult` | 对符合条件的请求返回的服务器主导的 `resultType: "task"` 响应 |
| `tasks/get` | 轮询一份完整的当前任务快照，包括终止结果或待处理输入 |
| `tasks/update` | 提交对任务未完成 `inputRequests` 的响应 |
| `tasks/cancel` | 确认协作式取消的意图 |
| `input_required` | 表示客户端输入尚未完成的状态 |
| `pollIntervalMs` | 服务器建议的、距下一次轮询的最小延迟 |
| `ttlMs` | 自任务创建起算的过期时长 |
| Durable-before-return（先持久化再返回） | 任务句柄发出之前，任务 id 必须已可解析的规则 |
| `notifications/tasks` | 在被订阅的 SSE 响应上递送的可选完整任务快照 |

## Legacy Compatibility · 旧版兼容

2025-11-25 的实验性表面使用客户端请求的任务增强、`tasks/status`、`tasks/result` 和可选的 `tasks/list`。这些名字只应保留在一个被固定的旧版适配器内部。当前的客户端使用扩展能力、接受服务器主导的句柄、轮询 `tasks/get`、用 `tasks/update` 提供输入，并从任务快照中读取最终结果。

> The 2025-11-25 experimental surface used client-requested task augmentation, `tasks/status`, `tasks/result`, and optional `tasks/list`. Keep those names only inside a pinned legacy adapter. A current client uses the extension capability, accepts server-directed handles, polls `tasks/get`, supplies input with `tasks/update`, and reads the final result from the task snapshot.

## Further Reading · 延伸阅读

- [Official MCP Tasks extension](https://tasks.extensions.modelcontextprotocol.io/specification/draft/tasks) —— 官方 MCP Tasks 扩展规范
- [MCP 2026-07-28 Multi Round-Trip Requests](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr) —— MCP 2026-07-28 多轮次请求（MRTR）
- [MCP 2026-07-28 Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) —— MCP 2026-07-28 Streamable HTTP 传输
