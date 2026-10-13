# Building an MCP Server: Stateless Python and TypeScript · 构建 MCP 服务器：无状态的 Python 与 TypeScript

> A modern MCP server does not remember a handshake. It validates the metadata on every request, runs one handler, and returns one typed result.

**Type:** Build
**Languages:** Python, TypeScript
**Prerequisites:** Phase 13, Lesson 06
**Time:** ~85 minutes

## Learning Objectives · 学习目标

- 为 MCP `2026-07-28` 实现必需的 `server/discover`。
- 在每个请求上校验协议版本与客户端能力。
- 以确定性的列表顺序暴露 tools、resources 和 prompts。
- 在正确的结果上返回 `resultType`、服务器身份和缓存提示。
- 用 Python 和 TypeScript 通过按换行分隔的 stdio 提供同一个无状态契约。

> Implement mandatory `server/discover` for MCP `2026-07-28`.
> Validate protocol version and client capabilities on every request.
> Expose tools, resources, and prompts with deterministic list ordering.
> Return `resultType`, server identity, and cache hints on the correct results.
> Serve the same stateless contract over newline-delimited stdio in Python and TypeScript.

## The Problem · 问题所在

一台在第一条消息之后就存下客户端能力的服务器，好写却难运维。同一个进程可能先后服务多个客户端；一个远程请求可能落在另一个 worker 上；一份过期的能力声明可能把行为泄漏过授权边界。

MCP `2026-07-28` 通过让每个请求自描述，解决了这个问题中属于协议的部分。你的应用仍然可以保存持久的笔记、任务或显式的状态句柄；不能保存的是那种会改变后续请求解码方式的隐藏协议状态。

本课把一个笔记服务器写了两遍。Python 版和 TypeScript 版的协议核心只使用各自的标准库。二者暴露相同的方法，并执行相同的线上契约。

> A server that stores client capabilities after the first message is easy to build and hard to operate. The same process may serve sequential clients. A remote request may land on a different worker. A stale capability declaration can leak behavior across authorization boundaries.
> MCP `2026-07-28` solves the protocol part of that problem by making every request self-describing. Your application can still keep durable notes, jobs, or explicit state handles. What it cannot keep is hidden protocol state that changes how a later request is decoded.
> This lesson builds a notes server twice. The Python and TypeScript versions use only their standard libraries for the protocol core. Both expose the same methods and enforce the same wire contract.

## The Concept · 核心概念

### The modern dispatch loop · 现代分发循环

```text
read one JSON-RPC line
parse the envelope
if it is a notification, do not respond
validate params._meta for this request
route by method
wrap success with resultType and serverInfo
write one JSON-RPC response line
forget request-scoped metadata
```

三条 stdio 规则依然重要：

- stdout 只写 JSON-RPC 消息，诊断信息发到 stderr。
- 消息用换行符分隔，每条响应都要 flush。
- stdin 到达 EOF 时立即退出。

进程的生命周期是传输层生命周期。它不是现代 MCP 会话。

> Three stdio rules still matter:
> - Write only JSON-RPC messages to stdout. Send diagnostics to stderr.
> - Delimit messages with a newline and flush each response.
> - Exit promptly when stdin reaches EOF.
> The process lifetime is a transport lifetime. It is not a modern MCP session.

### Request validation · 请求校验

每个请求必须带有：

```json
{
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {},
      "io.modelcontextprotocol/clientInfo": {
        "name": "notes-client",
        "version": "1.0.0"
      }
    }
  }
}
```

前两个字段是必需的。`clientInfo` 是推荐项。如果身份字段存在，要校验其形状，但不要把它当作认证。

如果版本不受支持，返回错误码 `-32022` 并附带 `requested` 与 `supported`。缺少请求元数据属于无效参数，错误码 `-32602`。绝不要用上一次调用的数据填补缺失字段。

> Every request must have:
> The first two fields are required. `clientInfo` is recommended. Validate a present identity shape, but do not treat it as authentication.
> If the version is unsupported, return code `-32022` with `requested` and `supported`. Missing request metadata is invalid params, code `-32602`. Never fill missing fields from a previous call.

### Mandatory discovery · 必需的发现方法

现代服务器必须实现 `server/discover`。一个完整的发现结果包含：受支持的现代版本、能力、可选的说明、缓存提示，以及结果 `_meta` 中的服务器身份：

```json
{
  "resultType": "complete",
  "supportedVersions": ["2026-07-28"],
  "capabilities": {
    "tools": {"listChanged": false},
    "resources": {"listChanged": false, "subscribe": false},
    "prompts": {"listChanged": false}
  },
  "ttlMs": 3600000,
  "cacheScope": "public",
  "_meta": {
    "io.modelcontextprotocol/serverInfo": {
      "name": "notes-server",
      "version": "2.0.0"
    }
  }
}
```

发现并不会解锁服务器。客户端可以不调用发现就直接调用 `tools/list`，因为 `tools/list` 本身已经携带同样的请求元数据。

> Modern servers must implement `server/discover`. A complete discovery result includes supported modern versions, capabilities, optional instructions, cache hints, and server identity in result `_meta`:
> Discovery does not unlock the server. A client may call `tools/list` without calling discovery because `tools/list` already carries the same request metadata.

### Tools · 工具

`tools/list` 返回一个确定性的工具描述符列表。稳定的排序能改善响应缓存，并保持模型上下文稳定。该结果还要求 `ttlMs` 与 `cacheScope`。

`tools/call` 返回内容块和 `isError`。当协议信封或方法参数非法时，使用 JSON-RPC 错误；当一次合法的工具调用执行了但工具本身失败时，使用 `isError: true`。

工具注解（annotations）仍然是提示，不是强制约束：

- `readOnlyHint`
- `destructiveHint`
- `idempotentHint`
- `openWorldHint`

宿主（host）应当用它们做确认与展示。服务器仍然必须执行真正的授权。

> `tools/list` returns a deterministic list of tool descriptors. Stable ordering improves response caching and keeps model context stable. The result also requires `ttlMs` and `cacheScope`.
> `tools/call` returns content blocks and `isError`. Use a JSON-RPC error when the protocol envelope or method parameters are invalid. Use `isError: true` when a valid tool invocation runs but the tool itself fails.
> Tool annotations remain hints, not enforcement:
> - `readOnlyHint`
> - `destructiveHint`
> - `idempotentHint`
> - `openWorldHint`
> The host should use them for confirmation and presentation. The server must still enforce real authorization.

### Resources · 资源

`resources/list` 返回稳定的 URI 描述符。`resources/read` 返回带类型的内容。在 `2026-07-28` 中二者都可缓存，因此都要包含 `ttlMs` 与 `cacheScope`。

用户私有的笔记数据使用 `cacheScope: "private"`。共享缓存不得跨授权上下文复用 private 响应。

现代的变更投递不使用 `resources/subscribe`。客户端打开 `subscriptions/listen`，并请求 `resourceSubscriptions` 或列表变更类别。第 10 课会构建这个流程。

> `resources/list` returns stable URI descriptors. `resources/read` returns typed contents. Both are cacheable in `2026-07-28`, so both include `ttlMs` and `cacheScope`.
> Use `cacheScope: "private"` for user-specific note data. A shared cache must not reuse a private response across authorization contexts.
> Modern change delivery does not use `resources/subscribe`. A client opens `subscriptions/listen` and requests `resourceSubscriptions` or list-change categories. Lesson 10 builds that flow.

### Prompts · 提示模板

`prompts/list` 是可缓存且确定性的。`prompts/get` 用参数渲染一个具名提示模板。渲染出的提示结果是 complete 的，但它不属于那种要求缓存提示的可缓存 list 或 read 结果。

> `prompts/list` is cacheable and deterministic. `prompts/get` renders a named prompt with arguments. The rendered prompt result is complete, but it is not one of the cacheable list or read results that requires cache hints.

### Every successful result is typed · 每个成功结果都带类型

示例对所有成功结果使用同一个包装器：

```python
def complete(payload):
    return {
        "resultType": "complete",
        **payload,
        "_meta": {SERVER_INFO_KEY: SERVER_INFO},
    }
```

list、read 和 discovery 处理器再加上 `ttlMs` 与 `cacheScope`。把这个包装器集中到一处，可以防止某个处理器悄悄漏掉现代结果字段。

> The examples use one wrapper for every success:
> List, read, and discovery handlers add `ttlMs` plus `cacheScope`. Centralizing this wrapper prevents one handler from silently omitting modern result fields.

### No server-initiated requests · 服务器不主动发起请求

现代服务器可以发送与某个客户端请求相关的通知，或在客户端打开的 `subscriptions/listen` 流上发送通知；但它绝不能发送自己的 JSON-RPC 请求。

当处理器需要 sampling、elicitation 或 roots 输入时，它返回一个 `input_required` 结果。客户端完成内嵌的输入请求后，用新的请求 id 重试原方法。第 11 课会讲这种多轮往返请求（Multi Round-Trip Request）模式。

> A modern server may send notifications related to a client request, or notifications on a client-opened `subscriptions/listen` stream. It must not send its own JSON-RPC request.
> When a handler needs sampling, elicitation, or roots input, it returns an `input_required` result. The client fulfills the embedded input requests and retries the original method with a new request id. Lesson 11 covers that Multi Round-Trip Request pattern.

### Explicit legacy compatibility · 显式的旧版兼容

双时代（dual-era）服务器也可以在一个明显独立的旧版分支上实现 `2025-11-25` 握手：当必需的现代 `_meta` 字段存在时选择现代行为，收到 `initialize` 时选择旧版行为。

不要让 `2026-07-28` 请求走进旧版握手路径；也不要把现代的 `resultType` 字段盖到旧版初始化结果上。本课代码刻意只支持现代版，这样它的不变量才保持可见。

```figure
t3-dispatch-loop
```

> A dual-era server may also implement the `2025-11-25` handshake on a clearly separate legacy branch. It chooses modern behavior when required modern `_meta` fields are present and legacy behavior when it receives `initialize`.
> Do not put a `2026-07-28` request through the legacy handshake path. Do not stamp modern `resultType` fields onto legacy initialization results. The code in this lesson is deliberately modern-only so its invariants stay visible.

## Use It · 实战用法

运行 Python 服务器的有限演示与测试：

```bash
cd code
python3 main.py --demo
python3 -m unittest discover tests -v
```

用 TypeScript 运行器跑 TypeScript 移植版：

```bash
npx tsx main.ts --demo
```

演示会发送 `server/discover`、列出每一类原语、调用工具，并展示一个版本不受支持的错误。每个现代请求都重复携带元数据。每个成功结果都包含服务器身份。

> Run the Python server's finite demo and tests:
> Run the TypeScript port with a TypeScript runner:
> The demo sends `server/discover`, lists each primitive, invokes tools, and shows an unsupported-version error. Every modern request repeats metadata. Every success includes server identity.

## Ship It · 交付

本课交付 `outputs/skill-mcp-server-scaffolder.md`。它生成一份现代服务器方案，包含发现契约、逐请求校验、确定性的可缓存列表，以及一个可选的隔离旧版适配器。

> This lesson ships `outputs/skill-mcp-server-scaffolder.md`. It produces a modern server plan with a discovery contract, per-request validation, deterministic cacheable lists, and an optional isolated legacy adapter.

## Exercises · 练习

1. 从某个请求中删掉能力，证明服务器不会复用上一个请求的声明。
2. 反转 `TOOLS`、`PROMPTS` 和笔记的插入顺序。确认所有列表结果保持稳定。
3. 增加一个破坏性的 `notes_delete` 工具，并要求在执行器内部做授权检查。`destructiveHint` 只作为 UX 提示。
4. 增加 `resources/templates/list`，带 `ttlMs`、`cacheScope` 和确定性排序。
5. 为 `2025-11-25` 构建一个独立的旧版适配器。加测试证明现代请求绝不会进入它。

> 1. Remove capabilities from one request and prove the server does not reuse the previous request's declaration.
> 2. Reverse the `TOOLS`, `PROMPTS`, and note insertion order. Confirm all list results remain stable.
> 3. Add a destructive `notes_delete` tool and require an authorization check inside the executor. Keep `destructiveHint` as a UX hint only.
> 4. Add `resources/templates/list` with `ttlMs`, `cacheScope`, and deterministic ordering.
> 5. Build a separate legacy adapter for `2025-11-25`. Add tests proving a modern request never enters it.

## Key Terms · 术语表

| 术语 | 含义 |
|------|---------|
| 无状态服务器（Stateless server） | 仅凭请求自身的元数据处理每个请求，没有协议会话记忆 |
| `server/discover` | 必需的现代方法，用于公布版本与能力 |
| 完整结果（Complete result） | 带 `resultType: "complete"` 的成功现代结果 |
| 可缓存结果（Cacheable result） | 带 `ttlMs` 与 `cacheScope` 的发现、列表或资源读取结果 |
| 确定性列表（Deterministic list） | 同一个逻辑注册表产生同样的条目顺序 |
| 服务器身份（Server identity） | 结果 `_meta` 中推荐的 `io.modelcontextprotocol/serverInfo` |
| 工具错误（Tool error） | 合法的工具调用返回带 `isError: true` 的内容 |
| 协议错误（Protocol error） | 非法的 JSON-RPC 或 MCP 请求，通过 `error` 返回 |

> | Term | Meaning |
> |------|---------|
> | Stateless server | Handles each request from its own metadata without protocol-session memory |
> | `server/discover` | Mandatory modern method that advertises versions and capabilities |
> | Complete result | Successful modern result with `resultType: "complete"` |
> | Cacheable result | Discovery, list, or resource-read result with `ttlMs` and `cacheScope` |
> | Deterministic list | Same logical registry produces the same item order |
> | Server identity | Recommended `io.modelcontextprotocol/serverInfo` in result `_meta` |
> | Tool error | Valid tool call that returns content with `isError: true` |
> | Protocol error | Invalid JSON-RPC or MCP request returned through `error` |

## Further Reading · 延伸阅读

- [MCP Specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/)
- [MCP Server Discovery](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
- [MCP Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [MCP Resources](https://modelcontextprotocol.io/specification/2026-07-28/server/resources)
- [MCP Prompts](https://modelcontextprotocol.io/specification/2026-07-28/server/prompts)
- [MCP stdio Transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)
