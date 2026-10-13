# MCP Resources and Prompts: Addressable Context for Stateless Servers · MCP 资源与提示词：无状态服务器的可寻址上下文

> Tools perform operations. Resources expose addressable content. Prompts package user-selected message templates. A good MCP server keeps those contracts separate and predictable.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 13, Lesson 07 (Building an MCP Server), Phase 13, Lesson 09 (MCP Transports)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 依据消费者的意图，在 tool、resource、prompt 三者之间做出选择。
- 通过强制的 `server/discover` 公布 resources 与 prompts 接口。
- 构建确定性的 `resources/list` 与 `prompts/list` 结果。
- 正确使用 `ttlMs` 与 `cacheScope`，不泄露用户专属数据。
- 对无效或未知的资源 URI 返回 JSON-RPC 错误 `-32602`。
- 打开 `subscriptions/listen` 的 POST 响应流，并用订阅 ID 关联每一个事件。
- 把资源内容和提示词模板当作不可信的服务器输出。

> Choose among tools, resources, and prompts from the consumer's intent.
> Advertise the resource and prompt surface through mandatory `server/discover`.
> Build deterministic `resources/list` and `prompts/list` results.
> Apply `ttlMs` and `cacheScope` without leaking user-specific data.
> Return JSON-RPC error `-32602` for an invalid or unknown resource URI.
> Open a `subscriptions/listen` POST-response stream and correlate every event by subscription ID.
> Treat resource content and prompt templates as untrusted server output.

## Start With the Consumer · 从消费者出发

误用 MCP 最容易的方式就是从实现代码开始。一个数据库查询被做成了 tool（工具），因为函数大家都熟悉；一个可复用的工作流被做成了 resource（资源），因为它恰好存在文件里；一个 prompt（提示词）被做成了隐藏策略，因为宿主可以悄悄把它注入进去。

先想清楚两个问题：谁来选择，以及他们期望得到什么。

| Primitive | 主要意图 | 选择由谁做 | 典型结果 |
|---|---|---|---|
| Tool | 执行一个操作 | 模型或应用 | 结构化的操作结果 |
| Resource | 读取某个 URI 上的内容 | 宿主、应用或用户 | 文本或二进制内容 |
| Prompt | 启动一个可复用的消息工作流 | 用户（通过宿主 UI） | 一条或多条提示消息 |

`notes://note-1` 是一个 resource，因为它是可寻址的内容。`delete_note` 是一个 tool，因为它会改变状态。`review_note` 是一个 prompt，因为用户主动选择了一个准备好的评审工作流。

不要为了让接口显得完整，就把同一个操作同时暴露成这三种原语。每多一个接口，就多一份发现、授权、缓存、错误处理、测试和文档的负担。

> The easiest way to misuse MCP is to begin with implementation code. A database query becomes a tool because functions are familiar. A reusable workflow becomes a resource because it is stored in a file. A prompt becomes hidden policy because the host can inject it.
> Begin with who chooses and what they expect.
> A note at `notes://note-1` is a resource because it is addressable content. `delete_note` is a tool because it changes state. `review_note` is a prompt because a user chooses a prepared review workflow.
> Do not expose one operation as all three merely to look complete. Each extra surface needs discovery, authorization, caching, error handling, tests, and documentation.

## The 2026-07-28 Stateless Envelope · 2026-07-28 无状态信封

本课面向 MCP 协议修订版 `2026-07-28`。在这个 profile 里没有初始化握手，也没有协议会话。每个请求都通过保留的 `_meta` 键携带自己的协议版本和客户端能力。

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "resources/list",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientInfo": {
        "name": "course-client",
        "version": "1.0.0"
      },
      "io.modelcontextprotocol/clientCapabilities": {}
    }
  }
}
```

服务器必须实现 `server/discover`。它的结果会公布支持的版本、resources 与 prompts 能力、实现身份以及缓存提示。客户端可以直接调用其他方法，但发现调用能在它构建 UI 之前给它一份稳定的快照。

```json
{
  "resultType": "complete",
  "supportedVersions": ["2026-07-28"],
  "capabilities": {
    "resources": {"listChanged": true, "subscribe": true},
    "prompts": {"listChanged": true}
  },
  "ttlMs": 3600000,
  "cacheScope": "public"
}
```

一个正常的结果会声明 `"resultType": "complete"`。响应中的 `_meta` 通过 `io.modelcontextprotocol/serverInfo` 标识提供服务的实现。这些信息对诊断有用，但它不是认证身份。携带不受支持修订版本的请求会返回 `-32022`，并同时给出所请求的修订版本和服务器支持的修订版本。

无状态契约会改变你的设计直觉。列表不能再依赖同一条连接上的上一次调用。授权可以改变可见集合——因为凭据是请求的输入——但连接历史绝不能。

> This lesson targets MCP protocol revision `2026-07-28`. There is no initialization handshake or protocol session in this profile. Every request carries its protocol version and client capabilities in reserved `_meta` keys.
> A server must implement `server/discover`. Its result advertises supported versions, resource and prompt capabilities, implementation identity, and cache hints.
> A normal result declares `"resultType": "complete"`. ... This information is useful for diagnostics. It is not an authentication identity. A request carrying an unsupported revision returns `-32022` with both the requested revision and the server's supported revisions.
> The stateless contract changes your design instincts. A list cannot depend on a prior call on one connection. Authorization may change the visible set because credentials are request input, but connection history must not.

## Resources Are Stable URI Contracts · 资源是稳定的 URI 契约

resource 就是由 URI 标识的内容。先设计 URI，再写处理器。

好的 URI 应具备的性质：

- 稳定到可以收藏，或可以在请求之间传递。
- 按服务器的领域做了命名空间隔离。
- 不依赖进程 ID 或连接。
- 在访问存储之前先做校验。
- 每次读取都做授权。

`notes://note-1` 比 `note-1` 更好，因为它的命名空间是显式的。文件服务器可以使用 `file://` URI，但在解析符号链接和相对路径段之后，仍必须检查配置好的目录边界。

`resources/list` 返回当前对调用者可见的资源。按稳定的键（例如 URI）排序。确定性的顺序可以避免嘈杂的缓存未命中、不断变化的快照，以及宿主 UI 在两次刷新之间来回跳动。

```json
{
  "resultType": "complete",
  "resources": [
    {
      "uri": "notes://note-1",
      "name": "Architecture decision",
      "description": "Why the service uses a stateless boundary",
      "mimeType": "text/markdown"
    }
  ],
  "ttlMs": 300000,
  "cacheScope": "public",
  "_meta": {
    "io.modelcontextprotocol/serverInfo": {
      "name": "notes-server",
      "version": "2.0.0"
    }
  }
}
```

`resources/read` 返回一个或多个内容项。未知的 URI 不是一次成功的空读取。现行的 Resources 规范把无效或未知的资源 URI 归入 JSON-RPC 的无效参数，错误码 `-32602`。

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "error": {
    "code": -32602,
    "message": "Unknown or invalid resource URI",
    "data": {
      "uri": "notes://missing"
    }
  }
}
```

这个区分让客户端能把「不存在」和「一个合法的空文档」分开。它也防止了意外回退到更大范围的查找。

> A resource is content identified by a URI. Design the URI before the handler.
> `resources/list` returns the resources currently visible to the caller. Sort by a stable key such as URI. Deterministic order prevents noisy cache misses, changing snapshots, and host UIs that jump between refreshes.
> `resources/read` returns one or more content items. An unknown URI is not a successful empty read. The current Resources specification assigns invalid or unknown resource URIs to JSON-RPC invalid parameters, code `-32602`.
> That distinction lets a client separate absence from a valid empty document. It also prevents accidental fallback to a broader lookup.

### Resource templates · 资源模板

资源模板（resource template）描述的是一个参数化 URI 的家族。当逐个列出所有具体条目的代价太高或根本无界时，就使用它。例如，`notes://projects/{project}/decisions/{decision}` 告诉客户端如何构造一个合法地址，而不必返回每一条决策。

模板不会削弱校验。解析变量、执行授权、强制长度和字符限制，并用带类型的参数构造存储查询。绝不把任意的 URI 尾部拼接进文件系统路径或数据库语句。

> A resource template describes a family of parameterized URIs. Use one when listing every concrete item would be expensive or unbounded.
> A template does not weaken validation. Parse variables, apply authorization, enforce length and character limits, and construct storage queries with typed parameters. Never concatenate an arbitrary URI tail into a filesystem path or database statement.

### Content is not trusted instruction · 内容不是可信指令

资源文本里可能藏着提示词注入、机密、误导性命令或格式错误的标记。宿主应当保留来源信息，并把资源内容当作数据对待。服务器应当限制内容大小、返回准确的 MIME 类型、对调用者无权访问的字段做脱敏，并避免返回无关记录。

> Resource text may contain prompt injection, secrets, misleading commands, or malformed markup. The host should preserve provenance and treat resource content as data. The server should limit content size, return an accurate MIME type, redact fields the caller cannot access, and avoid returning unrelated records.

## Prompts Are User-Controlled Templates · 提示词是用户控制的模板

MCP 的 prompts 是为用户的显式选择设计的。宿主可以把它们渲染成斜杠命令、菜单项或工作流按钮。协议不规定具体的 UI 形式。

对同样的请求授权，`prompts/list` 应当是确定性的。每个 prompt 都需要一个稳定的名称、一段有用的描述，以及能让宿主在 `prompts/get` 之前收集输入的参数声明。

```json
{
  "resultType": "complete",
  "prompts": [
    {
      "name": "review_note",
      "title": "Review a note",
      "description": "Review one note for a named concern",
      "arguments": [
        {
          "name": "uri",
          "description": "The note resource URI",
          "required": true
        }
      ]
    }
  ],
  "ttlMs": 600000,
  "cacheScope": "public"
}
```

`prompts/get` 把参数解析成消息。它不取代宿主的系统指令。由宿主决定返回的消息如何进入模型上下文，并让自己的可信策略保持更高的优先级。

在服务器边界校验 prompt 参数。一个 prompt URI 应当通过与直接资源读取相同的授权检查。不要把 prompt 变成绕过资源访问的侧信道。

> MCP prompts are designed for explicit user selection. A host may render them as slash commands, menu items, or workflow buttons. The protocol does not require one UI.
> `prompts/list` should be deterministic for the same request authorization. Each prompt needs a stable name, a useful description, and argument declarations that let the host collect input before `prompts/get`.
> `prompts/get` resolves arguments into messages. It does not replace the host's system instructions. The host decides how returned messages enter model context and keeps its own trusted policy at higher priority.
> Validate prompt arguments at the server boundary. A prompt URI should pass the same authorization check as a direct resource read. Do not make a prompt a side channel around resource access.

## Cache Hints Are Part of Correctness · 缓存提示是正确性的一部分

`ttlMs` 告诉客户端一个结果可以复用多久。`cacheScope` 描述谁可以共享这个缓存值。

| Scope | 含义 | 典型用途 |
|---|---|---|
| `public` | 在授权允许时可以跨用户复用 | 公开的 prompt 目录 |
| `private` | 绑定到发起请求的用户或凭据上下文 | 用户私有的笔记内容 |

TTL 要根据数据的变化速率和过期的危害来选。五分钟可能适合公开的 prompt 目录。私有的笔记读取可能只用一分钟。

MCP 只定义了 `public` 和 `private` 两种 `cacheScope` 取值。对含有机密或快速变化的结果，返回 `cacheScope: "private"` 且 `ttlMs: 0`，然后在宿主的缓存策略里应用更严格的 no-store 规则。`no-store` 本身并不是 MCP 的 `cacheScope` 取值。

缓存提示永远不能取代授权。缓存键必须包含每一个会改变可见性的请求维度，包括租户、用户、scope、locale 和分页游标。如果共享缓存无法安全地表达这些维度，就使用 `private` 加零 TTL，并在宿主层应用 no-store 策略。

> `ttlMs` tells a client how long a result may be reused. `cacheScope` describes who may share that cached value.
> Choose a TTL from the data's change rate and the damage of staleness. Five minutes may suit a public prompt catalog. A private note read may use one minute.
> MCP defines only `public` and `private` as `cacheScope` values. ... `no-store` itself is not an MCP `cacheScope` value.
> Cache hints never replace authorization. A cache key must include every request dimension that changes visibility, including tenant, user, scope, locale, and pagination cursor. If a shared cache cannot express those dimensions safely, use `private` with a zero TTL and a host-level no-store policy.

## Subscriptions Use a Client-Opened Response Stream · 订阅使用客户端打开的响应流

现代订阅模式取代了过去的 `resources/subscribe` RPC 和旧的 HTTP GET 事件端点。

客户端把 `subscriptions/listen` 作为普通的 JSON-RPC 请求发送。在 Streamable HTTP 上，这是一个 POST，其响应保持打开，作为一个 SSE 流。`notifications` 对象是一个允许清单。服务器不得投递任何未被请求的通知类型。

```json
{
  "jsonrpc": "2.0",
  "id": 17,
  "method": "subscriptions/listen",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {},
      "io.modelcontextprotocol/clientInfo": {
        "name": "course-client",
        "version": "1.0.0"
      }
    },
    "notifications": {
      "resourcesListChanged": true,
      "promptsListChanged": true,
      "resourceSubscriptions": [
        "notes://note-1"
      ]
    }
  }
}
```

请求 ID 就是订阅 ID。在任何被请求的事件之前，服务器会先发送 `notifications/subscriptions/acknowledged`。它的过滤器只包含服务器接受的子集。

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/subscriptions/acknowledged",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/subscriptionId": 17
    },
    "notifications": {
      "resourcesListChanged": true,
      "resourceSubscriptions": [
        "notes://note-1"
      ]
    }
  }
}
```

这条流上后续的每个事件都携带同样的元数据。

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/resources/updated",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/subscriptionId": 17
    },
    "uri": "notes://note-1"
  }
}
```

通知只是说资源变了。客户端要再次通过 `resources/read` 去读取它，并接受当时的授权约束。它不能假设事件里已经包含了新文档。

多个订阅可以共享一条 stdio 通道。订阅 ID 让客户端能把它们分开。在 HTTP 上，关闭响应流就会取消订阅。优雅结束流的服务器会返回一个最终响应，`resultType: "complete"`，并关联到最初的请求。

不要把订阅流当作协议会话。后续的读取仍然是一个完整的请求，可以被路由到任何一个健康的服务器实例。

```figure
t3-primitive-sort
```

> The modern subscription pattern replaces the former `resources/subscribe` RPC and the old HTTP GET event endpoint.
> The client sends `subscriptions/listen` as a normal JSON-RPC request. Over Streamable HTTP this is a POST whose response remains open as an SSE stream. The `notifications` object is an allowlist. A server must not deliver notification types that were not requested.
> The request ID is the subscription ID. Before any requested event, the server sends `notifications/subscriptions/acknowledged`.
> The notification says the resource changed. The client reads it again through `resources/read`, subject to current authorization. It does not assume the event contains the new document.
> Do not use a subscription stream as a protocol session. A later read is still a complete request that can reach any healthy server instance.

## Interactive Lab · 交互实验

用图示对一个项目跟踪器里的五项能力做分类：issue 详情、创建 issue、sprint 评审模板、项目策略、关闭 issue。然后判断哪些列表可以公开缓存，哪些读取必须保持私有，哪些资源值得发送更新通知。

每一种分类都要说出选择者是谁。如果模型执行一个动作，用 tool。如果宿主读取以 URI 寻址的内容，用 resource。如果用户启动一个准备好的消息工作流，用 prompt。

> Use the figure to classify five capabilities from a project tracker: issue details, create issue, sprint review template, project policy, and close issue. Then decide which lists can be cached publicly, which reads must remain private, and which resources deserve update notifications.
> For every classification, name the chooser. If the model performs an action, use a tool. If a host reads URI-addressed content, use a resource. If the user starts a prepared message workflow, use a prompt.

## Practice Lab · 实践实验

在仓库根目录运行模拟器：

```bash
cd phases/13-tools-and-protocols/10-mcp-resources-and-prompts/code
python3 main.py
python3 -m unittest discover tests -v
```

按下面的顺序检查输出记录：

1. 确认 `server/discover` 公布了当前修订版和两个能力。
2. 确认两个列表结果都是排序过的，并且使用 `resultType: "complete"`。
3. 确认列表和读取结果带有刻意设置的缓存提示。
4. 把读取的 URI 改成 `notes://missing`，观察 `-32602`。
5. 确认订阅确认事件先于资源事件。
6. 确认资源事件和优雅关闭都携带订阅 ID `5`。

这个 Python 模型不会打开真实的 HTTP 连接。它表示的是一个 SDK 必须放到请求作用域响应流上的消息。生产环境中请使用官方 SDK 处理成帧和传输。

> Run the simulator from the repository root: ... Inspect the transcript in this order:
> 1. Confirm `server/discover` advertises the current revision and both capabilities.
> 2. Confirm both list results are sorted and use `resultType: "complete"`.
> 3. Confirm the list and read results carry intentional cache hints.
> 4. Change the read URI to `notes://missing` and observe `-32602`.
> 5. Confirm the subscription acknowledgment precedes the resource event.
> 6. Confirm the event and graceful close both carry subscription ID `5`.
> The Python model does not open a real HTTP connection. It represents the messages an SDK must place on the request-scoped response stream. Use an official SDK for framing and transport in production.

## Shipped Artifact · 交付物

`outputs/skill-primitive-splitter.md` 是一份可复用的 MCP 原语选择设计评审。它现在会检查确定性发现、缓存范围、无效 URI 行为，以及现代订阅过滤器。

本课还附带 `assets/primitive-split.svg`，这是原语与订阅边界的静态版本，便于离线学习。

> `outputs/skill-primitive-splitter.md` is a reusable design review for MCP primitive selection. It now checks deterministic discovery, cache scope, invalid URI behavior, and modern subscription filters.
> The lesson also ships `assets/primitive-split.svg`, a static version of the primitive and subscription boundary for offline study.

## Verify It · 验证

```bash
cd phases/13-tools-and-protocols/10-mcp-resources-and-prompts/code
python3 main.py
python3 -m unittest discover tests -v
```

预期结果：主程序打印一份 JSON 记录，测试命令报告至少十二个通过。

> Expected result: the main program prints a JSON transcript and the test command reports at least twelve passing tests.

## Capstone Connection · 毕业项目关联

当你的毕业项目服务器在操作之外还要暴露可寻址的知识时，就使用这套契约。包含一份确定性的目录快照、一次经过授权的资源读取、一次 prompt 解析、一个无效 URI 用例，以及一份订阅记录。

你的证据应当表明：没有任何列表依赖连接历史，并且订阅事件绝不会授予对底层资源的访问权。

> Use this contract when your capstone server exposes addressable knowledge beside actions. Include one deterministic catalog snapshot, one authorized resource read, one prompt resolution, one invalid URI case, and one subscription transcript.
> Your evidence should show that no list depends on connection history and that a subscription event never grants access to the underlying resource.

## Exercises · 练习

1. 添加一个 `notes://projects/{project}/notes/{id}` 资源模板，并校验两个变量。
2. 给 `resources/list` 加分页，同时保持确定性顺序。
3. 把一个资源改成 `cacheScope: "private"` 且 `ttlMs: 0`，加上宿主层 no-store 策略，并解释是什么威胁证明这两层控制都是必要的。
4. 添加 prompt 列表变更订阅，并证明当过滤器省略 `promptsListChanged` 时不会发送任何事件。
5. 创建两个同时进行的订阅，并证明每个事件都携带正确的请求 ID。
6. 给读取处理器加上授权主体，并证明一个缓存条目不能跨主体使用。

> 1. Add a `notes://projects/{project}/notes/{id}` resource template and validate both variables.
> 2. Add pagination to `resources/list` while preserving deterministic order.
> 3. Change one resource to `cacheScope: "private"` with `ttlMs: 0`, add a host-level no-store policy, and explain the threat that justifies both controls.
> 4. Add a prompt-list change subscription and prove no event is sent when the filter omits `promptsListChanged`.
> 5. Create two simultaneous subscriptions and prove each event carries the correct request ID.
> 6. Add an authorization subject to the read handler and prove a cache entry cannot cross subjects.

## Key Terms · 术语表

- **Resource:** MCP 服务器暴露的、以 URI 寻址的内容。
- **Prompt:** MCP 服务器暴露的、由用户控制的消息模板。
- **Deterministic list（确定性列表）:** 对同样的请求输入，成员和顺序都稳定的发现结果。
- **`ttlMs`:** 缓存的新鲜时长，单位毫秒。
- **`cacheScope`:** 缓存结果的共享边界。
- **`subscriptions/listen`:** 一个长驻请求，其响应流投递显式过滤过的通知。
- **Subscription ID（订阅 ID）:** 最初的 listen 请求 ID，在通知元数据中重复出现。
- **Invalid parameters（无效参数）:** JSON-RPC 错误 `-32602`，用于无效或未知的资源 URI。
- **Unsupported protocol version（不支持的协议版本）:** JSON-RPC 错误 `-32022`，包含 `supported` 和 `requested` 修订版本。
- **`server/discover`:** 强制的服务器方法，返回支持的修订版本、能力、身份和可选的缓存提示。

> **Resource:** URI-addressed content exposed by an MCP server.
> **Prompt:** A user-controlled message template exposed by an MCP server.
> **Deterministic list:** A discovery result with stable membership and ordering for the same request inputs.
> **`ttlMs`:** Cache freshness duration in milliseconds.
> **`cacheScope`:** The sharing boundary for a cached result.
> **`subscriptions/listen`:** A long-lived request whose response stream delivers explicitly filtered notifications.
> **Subscription ID:** The original listen request ID, repeated in notification metadata.
> **Invalid parameters:** JSON-RPC error `-32602`, used for an invalid or unknown resource URI.
> **Unsupported protocol version:** JSON-RPC error `-32022`, including `supported` and `requested` revisions.
> **`server/discover`:** Mandatory server method that returns supported revisions, capabilities, identity, and optional cache hints.

## Further Reading · 延伸阅读

- [MCP 2026-07-28 Resources](https://modelcontextprotocol.io/specification/2026-07-28/server/resources)
- [MCP 2026-07-28 Prompts](https://modelcontextprotocol.io/specification/2026-07-28/server/prompts)
- [MCP 2026-07-28 Subscriptions](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/subscriptions)
- [MCP 2026-07-28 Caching](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/caching)
