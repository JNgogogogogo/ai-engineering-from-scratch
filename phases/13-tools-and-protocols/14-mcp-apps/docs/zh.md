# MCP Apps on the Stateless Protocol · 无状态协议上的 MCP Apps

> 交互式结果仍然是一次 MCP 工具与资源的交换。2026-07-28 核心协议让这次交换自包含（self-contained），而 Apps 扩展在此基础上添加了沙箱化的浏览器表面。

> An interactive result is still an MCP tool and resource exchange. The 2026-07-28 core makes that exchange self-contained, while the Apps extension adds the sandboxed browser surface.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 13 · 07 (MCP server), Phase 13 · 10 (resources)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 通过 `server/discover` 和每请求扩展能力（per-request extension capabilities）宣告 MCP Apps。
- 在工具被调用之前，就在工具上声明一个 `ui://` 资源。
- 在 2026-07-28 无状态线路上返回完整的工具与资源结果。
- 把 Apps 的 `ui/initialize` 桥接消息与已移除的 MCP 核心握手区分开。
- 应用来源校验（origin validation）、沙箱、CSP 与最小权限（least-privilege）。

> Advertise MCP Apps through `server/discover` and per-request extension capabilities.
> Declare a `ui://` resource on a tool before the tool is called.
> Return complete tool and resource results on the 2026-07-28 stateless wire.
> Separate the Apps `ui/initialize` bridge message from the removed MCP core handshake.
> Apply origin validation, sandboxing, CSP, and least-privilege permissions.

## The Problem · 问题在哪

一个文本结果可以描述一条时间线。但它无法给用户一条可以筛选、检查或操作的时间线。

MCP Apps 用一个可选扩展解决这个呈现问题。工具定义指向一个 `ui://` 资源。宿主（host）可以在工具运行之前抓取并审查该资源，把它渲染在一个沙箱化的 iframe 里，并通过一个 JSON-RPC 桥接调解所有应用动作。

核心协议在 2026-07-28 发生了变化。不要把一个 App 包进旧的连接生命周期里：

- 没有核心的 `initialize` 请求，也没有 `notifications/initialized` 通知。
- 没有 `Mcp-Session-Id` 头。
- 每个请求都在 `params._meta` 里携带协议版本与客户端能力。
- 服务器实现 `server/discover`，让客户端可以检查版本、核心能力与扩展。
- 每个成功结果都有一个 `resultType` 判别字段。
- Streamable HTTP 每个请求只用一个 POST。现代的 GET 和 DELETE 入口返回 405。

Apps 桥接里仍然有一个叫 `ui/initialize` 的方法。它属于 iframe postMessage 方言。它不会重建一个核心 MCP 会话。

> A text result can describe a timeline. It cannot give the user a timeline they can filter, inspect, or act on.
> MCP Apps solves the presentation problem with an optional extension. A tool definition points to a `ui://` resource.
> The core protocol changed in 2026-07-28. Do not wrap an App in the old connection lifecycle.
> The Apps bridge still has a method named `ui/initialize`. It belongs to the iframe postMessage dialect. It does not recreate a core MCP session.

## The Concept · 概念

### Two protocols, one feature · 两套协议，一个功能

让各层保持显式：

1. MCP 核心承载 `server/discover`、`tools/list`、`tools/call`、`resources/list` 和 `resources/read`。
2. MCP Apps 扩展声明 UI，并定义 iframe 到宿主的桥接。
3. 浏览器沙箱规则限制 UI 能触达什么。

扩展标识符是 `io.modelcontextprotocol/ui`。双方都要选择启用（opt in）。客户端在每个请求的 capabilities 对象里带上扩展支持：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "server/discover",
  "params": {
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "extensions": {
          "io.modelcontextprotocol/ui": {}
        }
      },
      "io.modelcontextprotocol/clientInfo": {
        "name": "timeline-host",
        "version": "1.0.0"
      }
    }
  }
}
```

`clientInfo` 是推荐用于诊断的字段。它是自报数据，不是授权身份。

> Keep the layers explicit: the MCP core carries discovery, tools, and resources; the Apps extension declares the UI and defines the iframe-to-host bridge; browser sandbox rules limit what the UI can reach.
> The extension identifier is `io.modelcontextprotocol/ui`. Both peers opt in.
> `clientInfo` is recommended for diagnostics. It is self-reported data, not an authorization identity.

### Discover before rendering · 渲染之前先发现

服务器的发现结果宣告该扩展：

```json
{
  "resultType": "complete",
  "supportedVersions": ["2026-07-28"],
  "capabilities": {
    "tools": {},
    "resources": {},
    "extensions": {
      "io.modelcontextprotocol/ui": {}
    }
  },
  "ttlMs": 300000,
  "cacheScope": "public",
  "_meta": {
    "io.modelcontextprotocol/serverInfo": {
      "name": "timeline-app-server",
      "version": "2.0.0"
    }
  }
}
```

服务器必须支持发现。客户端并不被强迫在每次动作前都调用发现，因为每个动作都自带能力。

> The server's discovery result advertises the extension.
> The server must support discovery. A client is not forced to call discovery before every action because each action carries its own capabilities.

### Declare the UI on the tool definition · 在工具定义上声明 UI

现代的 Apps 契约在 `tools/list` 里把 UI 绑定到工具：

```json
{
  "name": "notes_timeline",
  "description": "Render a timeline of notes.",
  "inputSchema": {
    "type": "object",
    "properties": {}
  },
  "_meta": {
    "ui": {
      "resourceUri": "ui://notes/timeline.html"
    }
  }
}
```

这是刻意设计的调用前（pre-call）元数据。宿主可以在某个结果请求展示它之前，预加载、缓存并对 HTML 做安全审查。旧的扁平元数据键可能仍被兼容代码接受，但新服务器应该输出嵌套的 `_meta.ui.resourceUri` 形式。

在当前核心里 `tools/list` 是可缓存的。包含确定性的排序、`ttlMs` 和 `cacheScope`。当可见工具随用户或令牌变化时，用 `private`。

> The modern Apps contract binds a UI to the tool in `tools/list`.
> This is deliberately pre-call metadata. The host can preload, cache, and security-review the HTML before a result asks to display it.
> `tools/list` is cacheable in the current core. Include deterministic ordering, `ttlMs`, and `cacheScope`.

### Return data, then let the host bind the view · 返回数据，让宿主去绑定视图

工具调用返回普通内容加上结构化数据：

```json
{
  "resultType": "complete",
  "content": [
    {"type": "text", "text": "Timeline ready."}
  ],
  "structuredContent": {
    "notes": [
      {"id": "note-1", "title": "Discover", "created": "2026-07-28"}
    ]
  },
  "isError": false
}
```

宿主已经知道哪个视图属于这个工具。不要为了重复一遍 URI 而发明一个新的内容块。

> The tool call returns ordinary content plus structured data.
> The host already knows which view belongs to the tool. Avoid inventing a new content block just to repeat the URI.

### Serve the app as a resource · 把应用作为资源来提供

服务器在发现中宣告了 `resources`，所以它也实现强制的 `resources/list` 操作。它的确定性列表条目包含规范 URI、稳定名称、描述和 MIME 类型。列表结果包含 `resultType`、服务器身份元数据、`ttlMs` 和 `cacheScope`，与确定性的工具列表一样。

宿主发送 `resources/read`。在 Streamable HTTP 上，请求带有：

```text
POST /mcp
MCP-Protocol-Version: 2026-07-28
Mcp-Method: resources/read
Mcp-Name: ui://notes/timeline.html
```

头的取值与 JSON-RPC 正文必须一致。不一致是协议错误 `-32020`。

结果包含 HTML 资源和缓存提示：

```json
{
  "resultType": "complete",
  "contents": [
    {
      "uri": "ui://notes/timeline.html",
      "mimeType": "text/html;profile=mcp-app",
      "text": "<!doctype html>...",
      "_meta": {
        "ui": {
          "csp": {
            "connectDomains": [],
            "resourceDomains": [],
            "frameDomains": [],
            "baseUriDomains": []
          },
          "permissions": {}
        }
      }
    }
  ],
  "ttlMs": 60000,
  "cacheScope": "public"
}
```

> The server advertises `resources` in discovery, so it also implements the mandatory `resources/list` operation.
> The header values and JSON-RPC body must match. A mismatch is protocol error `-32020`.
> The result contains the HTML resource and cache hints.

### Cache UI resources as executable content · 把 UI 资源当作可执行内容来缓存

App 资源与普通散文不可互换。它的缓存条目可以执行桥接代码、渲染工具数据，并请求宿主调解的动作。用它规范化的 `ui://` URI、已接纳的服务器身份与版本、资源内容摘要，以及（当 `cacheScope` 为 private 时的）授权上下文作为键。绝不在不同主体（principal）之间复用一个私有的 App 资源，因为即使 URI 完全相同，HTML 或其策略元数据也可能不同。

当条目的 `ttlMs` 过期、工具的 `_meta.ui.resourceUri` 绑定改变、服务器版本或已接纳的描述符固定（pin）改变，或一条已确认的资源变更订阅点名该 URI 时，使其失效。在重新挂载之前，重新抓取并重新执行 CSP 与权限审查。一个陈旧的 iframe 绝不能仅仅因为新资源版本尚未加载就保留更宽的权限。

> An App resource is not interchangeable with ordinary prose. Its cache entry can execute bridge code, render tool data, and request host-mediated actions.
> Never reuse a private App resource across principals because the HTML or its policy metadata may differ even when the URI is identical.
> Refetch and reapply CSP and permission review before remounting. A stale iframe must not keep broader permissions merely because a new resource version has not loaded yet.

### Reject wire ambiguity before feature policy · 先拒绝线路歧义，再做功能策略

校验有一个刻意的顺序。先校验 JSON-RPC 形状，要求字符串协议元数据加对象型客户端能力映射。接着把路由头与正文做比较。只有在这之后才决定匹配到的协议版本是否受支持。这个顺序防止代理与服务器解释出两个不同的请求。

| 条件 | HTTP | JSON-RPC 错误 |
|-----------|------|----------------|
| 头与正文的版本、方法或名称不一致 | 400 | `-32020` |
| 头与正文一致但版本不受支持 | 400 | `-32022`，`data` 恰为 `{"supported":["2026-07-28"],"requested":"<actual>"}` |
| `resources/read` 缺少 Apps 扩展能力 | 400 | `-32021`，带 `data.requiredCapabilities.extensions.io.modelcontextprotocol/ui` |
| 方法未知 | 404 | `-32601` |

JSON-RPC 通知没有 `id`，所以服务器永远不会为它发出 JSON-RPC 响应。一条被接受的 HTTP 通知返回 202 加空正文。错误可以改变 HTTP 状态码，但它仍然不能为通知创建 JSON-RPC 错误正文。

> Validation has a deliberate order. First validate the JSON-RPC shape... Next compare routing headers with the body. Only then decide whether the matched protocol version is supported. This order prevents a proxy and server from interpreting different requests.
> A JSON-RPC notification has no `id`, so the server never emits a JSON-RPC response for it. An accepted HTTP notification returns 202 with an empty body.

### The sandbox is a boundary, not a trust verdict · 沙箱是边界，不是信任判决

宿主控制 iframe。App 无法直接读取宿主的 cookie、本地存储或页面 DOM。所有特权工作都必须经过桥接。

使用这些默认值：

- 让所有 CSP 域列表为空，然后只添加 App 需要的来源。`connectDomains` 用于 fetch、XHR 和 WebSocket；`resourceDomains` 用于脚本、样式、图片和字体。
- 在可行时把代码与数据打包在一起。
- 除非有可见功能需要，否则不请求摄像头、麦克风或位置权限。
- 把 `postMessage` 固定到确切的对端来源（peer origin），拒绝来自所有其他来源的事件。
- 把工具参数、工具结果、资源文本和桥接消息都当作不可信输入。
- 把用户同意保留在宿主里。iframe 不能批准它自己的重大动作。

不要把教程里固定的 `sandbox` 属性复制进每个宿主。宿主必须基于 App 的来源模型和它自己的隔离设计来选择标志。

一个被允许的域仍然是一条外泄路径。`connectDomains: ["https://api.example.com"]` 意味着任何在 App 内执行的脚本都可以把被允许的数据发到那里。精确的来源匹配防止目的地混淆，但它不决定载荷是否恰当。默认保持 connect 访问为空，避免把持有者令牌（bearer tokens）放进 iframe，可行时通过宿主代理窄操作，限制响应与请求的大小，并审计每次出站请求是由哪个用户动作触发的。把 `resourceDomains` 与 `connectDomains` 分开对待；加载一个字体或脚本的权限不应授予任意数据上传。

> A host controls the iframe. The App cannot directly read host cookies, local storage, or page DOM. All privileged work must cross the bridge.
> Leave all CSP domain lists empty, then add only the origins the App needs.
> Do not copy a fixed `sandbox` attribute from a tutorial into every host. The host must choose flags based on the App's origin model and its own isolation design.
> An allowed domain is still an exfiltration path... Exact origin matching prevents destination confusion, but it does not decide whether the payload is appropriate.

### The Apps bridge has its own lifecycle · Apps 桥接有自己的生命周期

Apps 桥接是 `postMessage` 之上的一个 JSON-RPC 方言。它可以交换 `ui/initialize` 和 `ui/*` 通知，并可以代理看似核心的方法（如 `tools/call`）。

View 携带 `appInfo` 和一个 `appCapabilities` 对象发送 `ui/initialize`。宿主返回它的能力与宿主上下文。只有在那次响应之后，View 才发送 `ui/notifications/initialized`。宿主必须等待这条 Apps 通知，才能向 View 发送消息。

那个本地握手在「一个 iframe」与「一个宿主 frame」之间创建桥接。它不协商 MCP 协议版本、不创建服务器状态、也不铸造传输会话。注意确切的前缀：核心的 `notifications/initialized` 已被移除，而 Apps 的 `ui/notifications/initialized` 仍然存在。由桥接的工具调用生成的核心请求是一个新的自包含请求，带新的 JSON-RPC id 和完整的请求元数据。

> The Apps bridge is a JSON-RPC dialect over `postMessage`.
> Only after that response does the View send `ui/notifications/initialized`. The host must wait for this Apps notification before sending messages to the View.
> That local handshake creates a bridge between one iframe and one host frame. It does not negotiate the MCP protocol version, create server state, or mint a transport session.

### Host context, actions, and revocation · 宿主上下文、动作与撤销

桥接初始化之后，宿主仍然是权威。View 只能通过宿主宣告过的能力去请求工具动作、导航、剪贴板使用或其他特权效果。宿主校验带类型的请求、当前用户、目标与参数，应用审批策略，并可以拒绝。一次按钮点击和一条合法的桥接消息表达的只是意图；两者都不授予权力。

把主题、尺寸和无障碍视为会变化的宿主上下文，而不是一次性渲染输入：

- 应用宿主提供的颜色与排版 token，然后在主题或对比度偏好变化时做出反应。
- 让 View 上报期望的尺寸，但让宿主封顶并应用 iframe 尺寸，这样内容无法逃出它的布局或制造欺骗性覆盖层。
- 在 iframe 内保持键盘顺序、可见焦点、可访问名称、屏幕阅读器状态、足够的对比度、缩放和减弱动效（reduced-motion）行为。
- 在 resize 与重渲染之后，重新测试宿主控件与 View 控件之间的焦点转移。

App 打开期间能力可以被撤销：用户更换账号、策略变化、某个服务器被隔离，或宿主收窄同意。在动作时刻检查能力与授权，而不只在 `ui/initialize` 时。撤销时，拒绝未决的特权调用，停止不再符合策略的网络活动，清除敏感的已渲染状态，并在 UI 资源本身不再被接纳时重新挂载或回退到文本。View 必须把拒绝当作正常结果处理，而不是重试到宿主让步为止。

> The host remains the authority after bridge initialization. A View can request a tool action, navigation, clipboard use, or another privileged effect only through a capability the host advertised.
> A button click and a valid bridge message express intent; neither grants authority.
> Check capability and authorization at action time, not only during `ui/initialize`.
> A View must handle refusal as a normal result, not retry until the host gives in.

### Fallback is part of the contract · 回退是契约的一部分

一个支持 Apps 的服务器仍然可以服务未宣告 UI 扩展的宿主：

- 在 `tools/list` 里返回同一个工具，但不带 `_meta.ui`。
- 为 `tools/call` 保留有用的文本结果。
- 对 UI 的 `resources/read` 用 missing-capability 错误拒绝。
- 在判断工具是否完成时，绝不假设 iframe 存在。

```figure
t3-ui-sandbox
```

> An Apps-aware server can still serve hosts that do not advertise the UI extension: return the same tool without `_meta.ui`, keep a useful text result for `tools/call`, refuse `resources/read` for the UI with a missing-capability error.
> Never assume an iframe exists when deciding whether the tool completed.

## Build It · 动手造

`code/main.py` 在没有 SDK 的情况下构建一个小型进程内协议模型。它校验当前请求信封和 Streamable HTTP 路由取值，通过 `server/discover` 宣告 Apps，列出工具与资源，执行工具，并提供一个自包含的 HTML 资源。

这个模型接收的是已经解析过的正文和路由头。它不是一个完整的 HTTP 适配器，也不解析 `Content-Type` 或 `Accept`。完整的 Streamable HTTP 适配器见第 09 课，它要求 `Content-Type: application/json` 以及同时包含 `application/json` 和 `text/event-stream` 的 `Accept` 值。

运行它：

```bash
cd phases/13-tools-and-protocols/14-mcp-apps
python3 code/main.py
python3 -m unittest discover code/tests -v
```

在输出中检查四件事：

1. 每次调用都相互独立。
2. 每个请求都带 `_meta` 能力。
3. `resources/list` 在任何资源读取之前返回稳定描述符。
4. 每个结果都有 `resultType` 和服务器身份元数据。
5. 不出现任何核心会话标识符。

> `code/main.py` builds a small in-process protocol model without an SDK. It validates the current request envelope and Streamable HTTP routing values, advertises Apps through `server/discover`, lists tools and resources, executes the tool, and serves a self-contained HTML resource.
> The model receives already parsed bodies and routing headers. It is not a complete HTTP adapter and does not parse `Content-Type` or `Accept`.

## Use It · 实战用法

从 `server/discover` 开始。确认 `io.modelcontextprotocol/ui` 出现在服务器扩展映射里。然后调用 `tools/list` 两次，一次带 Apps 能力，一次不带。第一个响应声明了资源。第二个仍然是一个可用的纯文本工具。

读取 `ui://notes/timeline.html`。在 HTML 里搜索 `hostOrigin` 和 `event.origin` 守卫。这两行是「桥接不使用通配符目标」的最小可见证明。

> Start with `server/discover`. Confirm `io.modelcontextprotocol/ui` appears in the server extension map.
> Search the HTML for `hostOrigin` and the `event.origin` guard. Those two lines are the minimum visible proof that the bridge does not use a wildcard target.

## Ship It · 交付

本课交付 `outputs/skill-mcp-apps-spec.md`。在编写框架代码之前，用它审查一份 App 契约。它迫使作者陈述当前核心信封、扩展协商、回退、UI 资源、缓存策略、CSP、权限、桥接方法和同意边界。

> This lesson ships `outputs/skill-mcp-apps-spec.md`. Use it to review an App contract before writing framework code. It forces the author to state the current core envelope, extension negotiation, fallback, UI resource, cache policy, CSP, permissions, bridge methods, and consent boundary.

## Exercises · 练习

1. 把客户端能力改成空的扩展映射。确认 `tools/list` 保留工具但移除 UI 绑定。
2. 发送 `Mcp-Name: ui://notes/other.html`，正文却读取 timeline。确认错误 `-32020`。
3. 把资源改成 `cacheScope: private`。描述什么样的用户相关条件可以证明这个选择。
4. 把脚本移到 `https://static.example.com/app.js`。把该来源加入 `resourceDomains` 并解释新的供应链风险。
5. 添加一个 `notes_open` 工具，并把按钮点击通过宿主路由。把用户批准保留在宿主里。

## Key Terms · 术语表

| 术语 | 含义 |
|------|---------|
| MCP Apps | 可选扩展，用于由 MCP 宿主渲染的交互式 HTML |
| `io.modelcontextprotocol/ui` | 由双方宣告的扩展标识符 |
| `ui://` | App 的 UI 模板所用的资源 scheme |
| `text/html;profile=mcp-app` | MCP App HTML 的 MIME 类型 |
| `server/discover` | 现行的协议与能力发现 RPC |
| `resources/list` | 服务器宣告资源时的强制资源列表方法 |
| `resultType` | 现代成功结果必需的判别字段 |
| `ui/initialize` | Apps 桥接的第一个请求，区别于已移除的核心初始化 |
| `ui/notifications/initialized` | 宿主响应之后由 Apps View 发送的就绪通知 |
| CSP | 限制脚本、样式、图片与网络来源的浏览器策略 |
| Text fallback（文本回退） | 为不支持 Apps 的宿主保留的工具行为 |

## Further Reading · 延伸阅读

- [MCP 2026-07-28 base protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic) —— MCP 2026-07-28 基础协议
- [MCP Apps overview](https://modelcontextprotocol.io/extensions/apps/overview) —— MCP Apps 概览
- [MCP Apps build guide](https://modelcontextprotocol.io/extensions/apps/build) —— MCP Apps 构建指南
- [Official extension support matrix](https://modelcontextprotocol.io/extensions/client-matrix) —— 官方扩展支持矩阵
