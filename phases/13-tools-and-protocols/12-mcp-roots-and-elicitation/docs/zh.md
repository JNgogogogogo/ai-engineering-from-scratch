# Explicit Scope and Stateless Elicitation · 显式作用域与无状态 Elicitation

> Roots are deprecated in MCP 2026-07-28 and were never a security sandbox. Put scope in visible tool arguments or resource URIs, authorize it on the server, and use MRTR when a tool genuinely needs user input. The user sees the decision, the model sees the handle, and any server instance can process the retry.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 13 · 07 (MCP server), Phase 13 · 11 (stateless MRTR)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 用显式的工作区参数、资源 URI 或服务器配置取代已弃用的 Roots。
- 把作用域提示与授权、路径包含和操作系统沙箱区分开。
- 通过 MRTR 的 `input_required` 结果交付表单模式的 `elicitation/create`。
- 在每请求的客户端能力中公告 elicitation 支持，并拒绝不支持的模式。
- 把 `accept`、`decline` 和 `cancel` 当作三种不同的结果来处理。
- 把破坏性操作的确认绑定到已认证主体、原始参数、候选集合和过期时间。

> Replace deprecated Roots with explicit workspace parameters, resource URIs, or server configuration.
> Separate scope hints from authorization, path containment, and operating-system sandboxing.
> Deliver form-mode `elicitation/create` through an MRTR `input_required` result.
> Advertise elicitation support in per-request client capabilities and reject unsupported modes.
> Validate `accept`, `decline`, and `cancel` as distinct outcomes.
> Bind destructive confirmation to an authenticated principal, original arguments, candidate set, and expiry.

## Two Problems That Look Similar · 两个看起来相似的问题

一个笔记工具收到这样的请求：「删掉那份旧的 TPS 报告。」

服务器必须回答两个不同的问题。

1. 这次操作可以触碰哪个工作区？
2. 三个匹配的笔记里，用户指的是哪一条？

第一个是作用域与授权。第二个是交互式消歧。把两者混在一起会导致危险的设计，比如把客户端提供的文件夹当成「调用者可以删除其中一切内容」的证明。

> A notes tool receives this request: "Delete the old TPS report."
> The server must answer two different questions: Which workspace may this operation touch? Which of three matching notes did the user mean?
> The first is scope and authorization. The second is interactive disambiguation. Mixing them leads to dangerous designs, such as treating a client-provided folder as proof that the caller may delete everything inside it.

## Roots Are a Migration Surface · Roots 只是迁移入口

更早的 MCP 修订版允许客户端公告 Roots（根目录）并在列表变化时通知服务器。Roots 只是信息性的指引。它们不约束服务器进程能读什么，不授权调用者，也不构成操作系统沙箱。

MCP 2026-07-28 在新设计中弃用了 `roots/list` 和 `notifications/roots/list_changed`。优先选择下面这些显式替代品之一：

- 当作用域随调用变化时，用一个 `workspaceUri` 或 `directory` 工具参数。
- 当操作本来就指向某个资源时，用资源 URI。
- 当一个部署只拥有一个固定工作区时，用服务器配置。
- 当代码在技术上必须无法逃逸时，用进程沙箱或受限文件系统。

如果一个既有的 2026-07-28 集成在弃用窗口期内仍需要 `roots/list`，服务器会把它嵌入 MRTR 的 `inputRequests`。它不得发送活的反向请求。那是迁移适配器；新的处理器应当接受显式作用域。

显式的句柄，模型能看见、能复述。隐藏在传输会话里的作用域更难检查、重放、审计和路由。

> Earlier MCP revisions let a client advertise Roots and notify a server when the list changed. Roots were informational guidance. They did not constrain what the server process could read, did not authorize the caller, and did not create an operating-system sandbox.
> MCP 2026-07-28 deprecates `roots/list` and `notifications/roots/list_changed` for new designs. Prefer one of these explicit replacements.
> If an existing 2026-07-28 integration still needs `roots/list` during the deprecation window, the server embeds it in MRTR `inputRequests`. It must not send a live reverse request. That is a migration adapter; new handlers should accept explicit scope instead.
> The model can see and repeat an explicit handle. Hidden transport-session scope is harder to inspect, replay, audit, and route.

### The three-layer rule · 三层规则

一个显式 URI 仍然不能为自己授权。三层都要强制执行：

1. **Authorization（授权）：** 这个已认证的主体被允许使用这个工作区吗？
2. **Containment（包含）：** 归一化之后的目标 URI 是否仍留在授权的工作区边界之内？
3. **Sandbox（沙箱）：** 操作系统能否在服务器被攻破时依然阻止它逃逸？

可运行的服务器维护一个已授权工作区 URI 的允许清单，归一化百分号编码的路径，检查真实的路径组件边界，并在删除前一刻重新检查包含关系。

朴素的字符串前缀检查是错的：

```text
allowed:   file:///work/notes
attacker:  file:///work/notes-evil/secret.md
traversal: file:///work/notes/%2e%2e/private.md
```

两条恶意路径都以一段误导性的字符串开头。先归一化，再比较路径组件。生产级文件系统服务器还必须防御符号链接竞争和平台特定的路径语义。

> An explicit URI still does not authorize itself. Enforce all three layers: **Authorization**, **Containment**, and **Sandbox**.
> The runnable server keeps an allowlist of authorized workspace URIs, normalizes percent-encoded paths, checks a real path-component boundary, and re-checks containment immediately before deletion.
> Naive string-prefix checks are wrong: ... Both hostile paths start with a misleading string. Normalize first, then compare path components. A production filesystem server must also defend against symbolic-link races and platform-specific path semantics.

## Elicitation Still Exists, but Delivery Changed · Elicitation 仍然存在，但交付方式变了

Elicitation（用户输入引导）是当前的客户端特性，用于在 `tools/call`、`prompts/get` 或 `resources/read` 期间收集用户输入。方法名仍然是 `elicitation/create`。改变的是线上流的方向。

2026-07-28 服务器不发送反向 JSON-RPC 请求。它返回一个 `InputRequiredResult`：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "input_required",
    "inputRequests": {
      "delete_choice": {
        "method": "elicitation/create",
        "params": {
          "mode": "form",
          "message": "Choose one matching note and confirm deletion.",
          "requestedSchema": {
            "type": "object",
            "properties": {
              "note_id": {
                "type": "string",
                "enum": ["note-3", "note-7", "note-14"]
              },
              "confirm": {"type": "boolean"}
            },
            "required": ["note_id", "confirm"]
          }
        }
      }
    },
    "requestState": "integrity-protected-delete-state"
  }
}
```

宿主渲染表单。用户可以接受、明确拒绝，或者直接关掉它。然后客户端用一个全新的 id 重试原始的 `tools/call`：

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "notes_delete",
    "arguments": {
      "workspaceUri": "file:///Users/alice/Documents/Notes",
      "title": "TPS report"
    },
    "inputResponses": {
      "delete_choice": {
        "action": "accept",
        "content": {"note_id": "note-14", "confirm": true}
      }
    },
    "requestState": "integrity-protected-delete-state",
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "elicitation": {"form": {}}
      }
    }
  }
}
```

两次调用之间不存在协议会话。服务器校验回显的状态，按预期 schema 校验响应，确认所选笔记在签过名的候选集合里，重新授权工作区，重新检查包含关系，然后才执行删除。

> Elicitation is the current client feature for collecting user input during `tools/call`, `prompts/get`, or `resources/read`. The method name remains `elicitation/create`. What changed is the direction of the wire flow.
> A 2026-07-28 server does not send a reverse JSON-RPC request. It returns an `InputRequiredResult`.
> The host renders the form. The user can accept, explicitly decline, or dismiss it. The client then retries the original `tools/call` with a fresh id.
> There is no protocol session between the two calls. The server verifies the echoed state, validates the response against the expected schema, checks that the selected note was in the signed candidate set, re-authorizes the workspace, re-checks containment, and then deletes.

## Capability Negotiation Is Per Request · 能力协商按请求进行

支持表单模式 elicitation 的客户端会声明：

```json
{
  "io.modelcontextprotocol/clientCapabilities": {
    "elicitation": {"form": {}}
  }
}
```

空的 elicitation 能力，即 `"elicitation": {}`，出于兼容性考虑仍等价于仅表单支持。显式的 `"elicitation": {"form": {}}` 也支持表单模式。而仅 URL 的声明，`"elicitation": {"url": {}}`，不支持。服务器不得嵌入当前请求能力中不存在的模式，即使更早的请求公告过它。

每个请求还携带 `io.modelcontextprotocol/protocolVersion`。缺失或非字符串的版本返回 `-32602`。不支持的字符串返回 `-32022`，附带精确的 `supported` 和 `requested` 数据。缺失 elicitation 支持或仅有 URL 支持时返回 `-32021`，并把 `data.requiredCapabilities` 设为 `{"elicitation":{"form":{}}}`。

没有 JSON-RPC `id` 的信封是通知。处理它，但不发出 JSON-RPC 成功或错误响应。在 Streamable HTTP 上，已接受的通知收到 `202 Accepted`，无响应体。

`clientInfo` 应当包含在内用于诊断，但它是自报的，不能用于识别用户做授权。

服务器实现 `server/discover`，返回 `supportedVersions`、能力、`ttlMs` 和 `cacheScope`，并带 `resultType: "complete"`。在这个现代设计中它不公告 Roots。因为它公告了 tools，它也实现强制的 `tools/list`。该结果返回确定性的 `notes_delete` 描述符、一个合法的对象 `inputSchema`、服务器身份元数据和公开缓存提示。

> A client that supports form-mode elicitation declares the `elicitation` capability.
> An empty elicitation capability, `"elicitation": {}`, remains equivalent to form-only support for compatibility. Explicit `"elicitation": {"form": {}}` also supports form mode. A URL-only declaration, `"elicitation": {"url": {}}`, does not. The server must not embed a mode absent from the current request's capabilities, even if an earlier request advertised it.
> Every request also carries `io.modelcontextprotocol/protocolVersion`. A missing or non-string version returns `-32602`. An unsupported string returns `-32022` with exact `supported` and `requested` data. Missing or URL-only elicitation support returns `-32021` with `data.requiredCapabilities` set to `{"elicitation":{"form":{}}}`.
> `clientInfo` should be included for diagnostics, but it is self-reported and cannot identify the user for authorization.

## Form Mode · 表单模式

表单模式使用一种受限的 JSON Schema，专为可用的对话框设计。根必须是对象，其属性是扁平的原始类型字段或受支持的枚举数组。深层嵌套的对象和通用文档 schema 不该出现在确认对话框里。

表单模式适用于：

- 从多个候选中选一个；
- 确认一个破坏性操作；
- 收集非敏感的偏好设置；
- 收集少量必须由用户（而非模型）决定的值。

不要用表单模式收集密码、API 密钥、访问令牌或支付凭据。这些机密会经过 MCP 客户端，可能进入日志或模型上下文。

服务器会对返回的内容再次校验。客户端侧的表单校验改善体验，但不创造信任。

> Form mode uses a restricted JSON Schema designed for usable dialogs. The root is an object and its properties are flat primitive fields or supported enum arrays. Deeply nested objects and general-purpose document schemas do not belong in a confirmation dialog.
> Do not use form mode for passwords, API keys, access tokens, or payment credentials. Those secrets would pass through the MCP client and could reach logs or model context.
> The server validates the returned content again. Client-side form validation improves UX but does not create trust.

## URL Mode · URL 模式

URL 模式发送一个安全的 Web URL，用于带外交互：

```json
{
  "method": "elicitation/create",
  "params": {
    "mode": "url",
    "message": "Connect the report service to continue.",
    "url": "https://mcp.example.com/connect/report-service"
  }
}
```

当敏感信息必须直接进入服务器控制的 Web 流程（例如第三方授权）时使用它。客户端在打开之前展示完整的目的地并取得同意。它不得预取该 URL。

`accept` 响应表示用户同意打开该 URL。它不能证明外部流程已经完成。重试时，服务器检查自己的状态，然后要么完成操作，要么再返回一个 `input_required` 结果。

URL elicitation 不是 MCP 客户端与 MCP 服务器之间授权的替代品。它服务于 MCP 服务器需要代表用户执行的外部交互。服务器必须把浏览器用户绑定到发起 MCP 操作的同一个已认证主体上。

> URL mode sends a secure web URL for an out-of-band interaction.
> Use it when sensitive information must go directly to a server-controlled web flow, such as third-party authorization. The client shows the full destination and obtains consent before opening it. It must not prefetch the URL.
> An `accept` response means the user agreed to open the URL. It does not prove the external flow completed.
> URL elicitation is not a replacement for authorization between the MCP client and MCP server. ... The server must bind the browser user to the same authenticated principal that began the MCP operation.

## Response Branches · 响应分支

把这三种动作当作产品决策，而不是同义词：

| Action | 含义 | 服务器的安全行为 |
|--------|---------|----------------------|
| `accept` | 用户提交了这次交互 | 校验内容并继续 |
| `decline` | 用户明确拒绝 | 返回一个完整的、非错误的拒绝结果 |
| `cancel` | 用户关闭或未能完成 | 安全停止，允许稍后重试 |

绝不要把缺失的内容解读为同意。绝不要把 decline 变成反复弹出的提示循环。

> Treat the actions as product decisions, not aliases:
> | Action | Meaning | Safe server behavior |
> |--------|---------|----------------------|
> | `accept` | User submitted the interaction | Validate content and continue |
> | `decline` | User explicitly refused | Return a complete, non-error refusal outcome |
> | `cancel` | User dismissed or could not finish | Stop safely and allow a later retry |
> Never interpret missing content as consent. Never convert decline into a repeated prompt loop.

## Protecting Destructive MRTR State · 保护破坏性的 MRTR 状态

候选列表不能只活在一个提示词或未签名的 Base64 值里。客户端发回的一切都由它控制。

本课对一个状态载荷签名，其中包含：

- 已认证主体；
- 发起的方法；
- `workspaceUri` 和 `title` 的摘要；
- 表单里展示过的允许笔记 id；
- 操作阶段；
- 短过期时间。

在变更之前，服务器还要检查活着的笔记记录。这能捕获删除竞争，以及表单展示后目标被移出工作区的情况。

对一次性的金融或不可逆操作，仅靠 HMAC 无法阻止一个合法状态在过期窗口内被重放。要在所有处理器实例共享的重放存储中存储并恰好消费一次 nonce。本课注入了一个有界、按 TTL 修剪的存储，并在执行内存中的删除时持有它的原子认领。生产数据库应当把 nonce 认领和变更耦合在同一个事务或等价的条件写边界里。

在认领 nonce 之前先校验交互。格式错误的响应或 `cancel` 不执行任何变更，状态保持可重试直到过期。显式的 `decline` 是终结性的，所以本课会消费 nonce 但不删除任何东西。

```figure
t3-roots-boundary
```

> The candidate list cannot live only in a prompt or unsigned Base64 value. A client controls everything it sends back.
> The lesson signs a state payload containing: authenticated principal; originating method; digest of `workspaceUri` and `title`; allowed note ids shown in the form; operation phase; short expiry.
> Before mutation, the server also checks the live note record. This catches deletion races and a target moved outside the workspace after the form was shown.
> For a one-time financial or irreversible action, HMAC alone does not prevent a valid state from being replayed within its expiry. Store and consume a nonce exactly once in a replay store shared by every handler instance.
> Validate the interaction before claiming the nonce. A malformed response or `cancel` performs no mutation and leaves the state retryable until expiry. An explicit `decline` is terminal, so the lesson consumes the nonce without deleting anything.

## Build It · 动手造

`code/main.py` 演示了一个现代的 `notes_delete` 工具：

- `tools/list` 返回一个确定性、可缓存的描述符，带所需的 workspace 和 title schema。
- 作用域是一个显式的 `workspaceUri` 参数。
- 服务器配置为本课主体授权该工作区。
- URI 归一化拒绝前缀混淆和编码穿越。
- 每次破坏性删除都要求表单模式 elicitation。
- elicitation 在 `resultType: "input_required"` 内部传递。
- 签名的 `requestState` 绑定确切的候选列表和原始参数。
- 注入的重放存储在多个服务器实例之间拒绝同一个被接受或被拒绝的状态。
- 重试使用全新的请求 id，并返回 `resultType: "complete"`。

数据存储放在内存里，以便协议行为易于检查。换成数据库之后，安全规则不变。

> `code/main.py` demonstrates a modern `notes_delete` tool: `tools/list` returns a deterministic, cacheable descriptor with the required workspace and title schema; scope is an explicit `workspaceUri` argument; server configuration authorizes that workspace for the lesson principal; URI normalization rejects prefix confusion and encoded traversal; every destructive deletion requires form-mode elicitation; the elicitation travels inside `resultType: "input_required"`; signed `requestState` binds the exact candidate list and original arguments; an injected replay store rejects the same accepted or declined state across server instances; the retry uses a fresh request id and returns `resultType: "complete"`.
> The data store is in memory so the protocol behavior is easy to inspect. The security rules remain the same with a database.

## Use It · 实战用法

在仓库根目录：

```bash
cd phases/13-tools-and-protocols/12-mcp-roots-and-elicitation/code
python3 main.py
python3 -m unittest discover tests -v
```

预期检查点：

- 发现公告了 tools，但没有 Roots。
- 工具发现返回 `notes_delete`，带 `resultType`、服务器身份和缓存提示。
- 请求 id `1` 在 `inputRequests.delete_choice` 中返回表单。
- 请求 id `2` 回显签名状态并完成删除。
- 前缀路径和编码穿越路径都无法通过包含检查。
- 被修改的 title 无法复用原始确认状态。
- decline 使笔记保持不变。
- 共享笔记与重放状态的两个服务器对象不能都执行同一个确认。
- 空的与显式的表单声明都能工作，而仅 URL 支持返回精确的 `-32021` 表单要求。
- 不支持版本的失败使用精确的 `-32022` 数据形状。
- 无 id 的通知不产生任何 JSON-RPC 响应。

> From the repository root: ... Expected checkpoints: Discovery advertises tools without Roots. Tool discovery returns `notes_delete` with `resultType`, server identity, and cache hints. Request id `1` returns the form in `inputRequests.delete_choice`. Request id `2` echoes the signed state and completes the deletion. A prefix path and an encoded traversal path both fail containment. A changed title cannot reuse the original confirmation state. A decline leaves the note unchanged. Two server objects sharing note and replay state cannot both execute one confirmation. Empty and explicit form declarations work, while URL-only support returns exact `-32021` form requirements. Unsupported version failures use the exact `-32022` data shape. An id-less notification produces no JSON-RPC response.

## Ship It · 交付

`outputs/skill-elicitation-form-designer.md` 设计显式作用域、授权检查、MRTR 表单、响应分支和状态绑定。它拒绝把已弃用的 Roots 当作沙箱，也拒绝通过表单模式收集机密。

> `outputs/skill-elicitation-form-designer.md` designs the explicit scope, authorization checks, MRTR form, response branches, and state binding. It refuses to treat deprecated Roots as a sandbox or to collect secrets through form mode.

## Exercises · 练习

1. 把内存重放存储换成 SQLite。用一个事务认领 nonce 并删除笔记，然后证明两个进程不能都提交成功。
2. 添加 `url` 能力协商和带外设置流程。把第三方凭据挡在 `inputResponses` 之外。
3. 把内存笔记映射换成一个临时 SQLite 数据库。在变更事务内部重新检查授权与包含关系。
4. 为真实文件系统实现添加符号链接策略。解释为什么仅靠 URI 词法包含无法阻止符号链接逃逸。
5. 设计一个 2025-11-25 适配器，把现代 MRTR 处理器的输出映射到遗留的服务器发起 elicitation。让它与当前处理器保持隔离。

> 1. Replace the in-memory replay store with SQLite. Use one transaction to claim the nonce and delete the note, then prove two processes cannot both commit.
> 2. Add `url` capability negotiation and an out-of-band setup flow. Keep third-party credentials out of `inputResponses`.
> 3. Replace the in-memory note map with a temporary SQLite database. Re-check authorization and containment inside the mutation transaction.
> 4. Add a symbolic-link policy for a real filesystem implementation. Explain why URI lexical containment alone cannot stop a symlink escape.
> 5. Design a 2025-11-25 adapter that maps modern MRTR handler output to legacy server-initiated elicitation. Keep it isolated from the current handler.

## Key Terms · 术语表

| Term | 在 2026-07-28 中的含义 |
|------|------------------------|
| Roots | 已弃用的信息性工作区提示，不是授权也不是沙箱 |
| Explicit scope（显式作用域） | 在请求参数中可见的工作区、目录或资源句柄 |
| Containment（包含） | 归一化的路径组件检查，确保目标留在边界之内 |
| Elicitation | 在 MCP 操作期间获取用户输入的客户端特性 |
| Form mode（表单模式） | 使用受限扁平 schema 的带内结构化用户输入 |
| URL mode（URL 模式） | 面向敏感或外部工作流的带外交互 |
| MRTR | 无状态的 input-required 结果，随后是一次全新的重试 |
| `requestState` | 不透明状态，由客户端逐字节回显并由服务器做完整性校验 |
| Decline | 用户的明确拒绝 |
| Cancel | 关闭或未完成的交互，没有批准 |

> | Term | Meaning in 2026-07-28 |
> |------|------------------------|
> | Roots | Deprecated informational workspace hints, not authorization or sandboxing |
> | Explicit scope | Workspace, directory, or resource handle visible in request arguments |
> | Containment | Normalized path-component check that keeps a target inside a boundary |
> | Elicitation | Client feature for obtaining user input during an MCP operation |
> | Form mode | In-band structured user input using a restricted flat schema |
> | URL mode | Out-of-band interaction for sensitive or external workflows |
> | MRTR | Stateless input-required result followed by a fresh retry |
> | `requestState` | Opaque state echoed exactly and integrity-checked by the server |
> | Decline | Explicit user refusal |
> | Cancel | Dismissal or incomplete interaction without approval |

## Legacy Compatibility · 遗留兼容性

对固定在 2025-11-25 的对端，`roots/list`、`notifications/roots/list_changed` 和活的服务器发起 `elicitation/create` 可能仍然存在。把那个适配器标注为 legacy。不要让遗留的 Roots 列表绕过服务器授权，也不要把协议会话假设带进现代处理器。

> For a peer pinned to 2025-11-25, `roots/list`, `notifications/roots/list_changed`, and live server-initiated `elicitation/create` may still exist. Label that adapter legacy. Do not allow a legacy Root list to bypass server authorization, and do not carry protocol-session assumptions into the modern handler.

## Further Reading · 延伸阅读

- [MCP 2026-07-28 Elicitation](https://modelcontextprotocol.io/specification/2026-07-28/client/elicitation)
- [MCP 2026-07-28 Multi Round-Trip Requests](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [MCP 2026-07-28 Roots deprecation](https://modelcontextprotocol.io/specification/2026-07-28/client/roots)
- [MCP 2026-07-28 server discovery](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
