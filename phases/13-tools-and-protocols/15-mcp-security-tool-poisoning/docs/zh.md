# MCP Security: Poisoned Metadata, Routing, and MRTR State · MCP 安全：被投毒的元数据、路由与 MRTR 状态

> 无状态不等于无信任（trustless）。它意味着每个请求都暴露出服务器和网关独立校验这次调用所需的证据。

> Stateless does not mean trustless. It means every request exposes the evidence a server and gateway need to validate the call independently.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 13 · 07 (MCP server), Phase 13 · 08 (MCP client)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 把工具描述、注解（annotations）、客户端信息与服务器信息都当作不可信数据。
- 检测元数据投毒（metadata poisoning）、描述符变更与跨服务器名称冲突。
- 校验 2026-07-28 的请求元数据和 Streamable HTTP 路由头。
- 保护 MRTR `requestState` 免遭篡改，并把确认绑定到精确的参数。
- 把授权与限流应用到一个主体（principal）上，而不是一个已被移除的协议会话。

> Treat tool descriptions, annotations, client information, and server information as untrusted data.
> Detect metadata poisoning, descriptor changes, and cross-server name collisions.
> Validate the 2026-07-28 request metadata and Streamable HTTP routing headers.
> Protect MRTR `requestState` against tampering and bind confirmation to exact arguments.
> Apply authorization and rate limits to a principal, not a removed protocol session.

## The Problem · 问题在哪

模型阅读工具描述来决定调用什么。路由器阅读工具名称来决定把请求发到哪里。用户阅读标签来决定批准什么。一个恶意描述符可以同时瞄准这三者。

官方 MCP 安全指导很直接：描述与注解应被视为不可信，除非它们来自受信任的服务器。即便如此，部署信任也可能改变。一次服务器更新、一个被入侵的包、一次注册表失误或一次网关合并，都能改变模型看到的内容。

当前协议还改变了安全边界。在 2026-07-28 中没有核心握手，也没有传输会话。仅靠 `Mcp-Session-Id` 来键控审批、限流或审计历史的安全设计，已经不是当代的设计。

> A model reads tool descriptions to decide what to call. A router reads tool names to decide where to send a request. A user reads labels to decide what to approve. One malicious descriptor can target all three.
> The official MCP security guidance is direct: descriptions and annotations should be treated as untrusted unless they come from a trusted server.
> In 2026-07-28 there is no core handshake and no transport session. A security design that keys approval, rate limits, or audit history only by `Mcp-Session-Id` is not a current design.

## The Concept · 概念

### Seven attack surfaces worth checking · 七个值得检查的攻击面

用一个具体的清单，代替「要小心」这种模糊指示。

1. **元数据投毒（Metadata poisoning）。** 描述里含有与声明的工具行为无关的指令。
2. **描述符急拉（Descriptor rug pull）。** 一个先前被批准的名称、描述、schema 或注解发生了变化。
3. **跨服务器遮蔽（Cross-server shadowing）。** 两个后端暴露同一个不带限定符的工具名，路由静默地选择了其中一个。
4. **头与正文混淆。** `Mcp-Method` 或 `Mcp-Name` 与 JSON-RPC 请求不一致。
5. **能力升级（Capability escalation）。** 对端声称了某个扩展或客户端特性，而服务器把这个声明误当成授权。
6. **MRTR 状态篡改。** 客户端修改 `requestState`、回答另一个问题，或用不同的参数复用确认。
7. **供应链身份混淆。** 一个眼熟的显示名称被当成了发布者或服务器身份的证明。

这些面彼此重叠。哈希固定有助于应对描述符变更，但无法证明第一个描述符就是安全的。静态扫描能抓住明显的短语，却抓不住隐晦的指令。命名空间防止一类冲突，却防不住一个恶意的带命名空间服务器。要把控制手段叠起来用。

> Use a concrete list instead of the vague instruction to be careful.
> Metadata poisoning: a description contains instructions unrelated to the declared tool behavior... Hash pinning helps with descriptor changes but does not prove that the first descriptor was safe. Static scanning catches obvious phrases but not subtle instructions. Namespacing prevents one collision class but not a malicious namespaced server. Stack the controls.

### The current request envelope is evidence, not identity · 当前请求信封是证据，不是身份

每个 2026-07-28 请求都包含：

```json
{
  "_meta": {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientCapabilities": {
      "elicitation": {"form": {}}
    },
    "io.modelcontextprotocol/clientInfo": {
      "name": "security-lab",
      "version": "1.0.0"
    }
  }
}
```

在每个请求上校验版本与能力的形状。用能力来选择一个兼容的响应形状。不要把 `clientInfo` 当作已认证的主体（authenticated principal）。它是自报的。

同样的警告适用于结果元数据里的 `io.modelcontextprotocol/serverInfo`。它对日志和调试有用。它不是证书、注册表证明或授权决定。

> Validate the version and capability shape on every request. Use capabilities to choose a compatible response shape.
> Do not use `clientInfo` as an authenticated principal. It is self-reported.
> The same warning applies to `io.modelcontextprotocol/serverInfo` in result metadata. It is useful for logs and debugging. It is not a certificate, registry proof, or authorization decision.

### Validate routing before policy · 先校验路由，再谈策略

对 `tools/call`，Streamable HTTP 包含：

```text
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: notes.export
```

头里的方法必须等于正文里的方法。头里的名称必须等于 `params.name`。在选择后端、应用 RBAC 或消耗一个限流令牌之前，就用 `-32020` 拒绝不一致。

这个顺序堵住一个常见的歧义：一个组件按正文授权，另一个组件按头路由。

线路校验遵循一个确切的序列。校验 JSON-RPC 与元数据类型，比较头的取值与正文，然后检查匹配到的版本是否受支持。不匹配的头返回 HTTP 400 加 `-32020`。如果头与正文一致但版本不受支持，返回 HTTP 400 加 `-32022`，且 `data` 恰为 `{"supported":["2026-07-28"],"requested":"<actual>"}`。未知方法返回 HTTP 404 加 `-32601`。

每个错误对象在契约需要结构化恢复信息时包含可选的 `data`。通知没有 `id`，所以它永远不会收到 JSON-RPC 成功或错误响应。一条被接受的 HTTP 通知返回 202 加空正文。

> The header method must equal the body method. The header name must equal `params.name`. Reject disagreement with `-32020` before selecting a backend, applying RBAC, or consuming a rate-limit token.
> This ordering closes a common ambiguity: one component authorizes the body while another routes by the header.
> A notification has no `id`, so it never receives a JSON-RPC success or error response. An accepted HTTP notification returns 202 with an empty body.

### Pin the whole descriptor · 固定整个描述符

只用描述哈希会漏掉 schema 和注解的变更。把用户批准过的描述符字段规范化（canonicalize）并哈希：

```python
normalized = json.dumps(tool, sort_keys=True, separators=(",", ":"))
digest = hashlib.sha256(normalized.encode()).hexdigest()
```

把摘要存储在一个带限定符的键（如 `notes.export`）之下，同时在生产环境中（本玩具示例之外）连同发布者证据与批准时间一起保存。

每次刷新时：

- 未知键：隔离（quarantine），直到审查完成。
- 同键、不同摘要：作为 rug pull 隔离，直到重新批准。
- 重复的无限定名称：要求确定性的命名空间。
- 扫描器命中：阻止并审查完整描述符。

哈希相等证明的是稳定，不是安全。一个被投毒的描述符，即便被完美地固定，也仍然是投毒的。

> A description hash alone misses schema and annotation changes. Canonicalize and hash the descriptor fields the user approved.
> Hash equality proves stability, not safety. A poisoned descriptor stays poisoned when perfectly pinned.

### Static scanning is a tripwire · 静态扫描是一道绊线

简单的模式可以标记角色标签、指令覆盖、隐瞒、秘密访问和被混淆的网络目的地。它们足够便宜，可以用于安装时和 CI。

它们不是语义证明。一条安全的描述可能在一段正当的警告里包含被标记的短语。一条恶意的描述可以避开所有短语。把扫描器输出当作审查证据，而不是自动的无罪评分。

> Simple patterns can flag role tags, instruction overrides, concealment, secret access, and obscured network destinations. They are cheap enough for install time and CI.
> They are not a semantic proof... Treat scanner output as review evidence, not an automatic innocence score.

### Namespace before merging · 合并之前先命名空间

假设两台服务器都暴露 `search`。绝不让发现顺序决定谁赢。

```text
notes.search
issues.search
```

带限定符的名称就是公开的网关名称。把后端映射单独记录。稳定的名称让批准、审计、哈希固定和 `Mcp-Name` 路由都指向同一个对象。

> Suppose two servers both expose `search`. Never let discovery order decide which wins.
> The qualified name is the public gateway name. Record the backend mapping separately.
> Stable names make approval, audit, hash pins, and `Mcp-Name` routing refer to the same object.

### Capabilities are compatibility declarations · 能力是兼容性声明

每请求的 `clientCapabilities` 告诉服务器：客户端能处理哪些协议特性。它并不授予客户端对工具、数据或动作的访问。

授权仍然来自已认证的主体与资源策略。序列是：

1. 认证传输凭据。
2. 校验版本、头与请求形状。
3. 检查能力兼容性。
4. 对主体、工具、资源和参数做授权。
5. 执行或请求用户输入。

> Per-request `clientCapabilities` tells a server which protocol features the client can process. It does not grant the client access to tools, data, or actions.
> Authorization still comes from the authenticated principal and resource policy.

### Protect stateless MRTR confirmation · 保护无状态的 MRTR 确认

一个重大（consequential）工具可能需要用户确认。当前 MCP 使用多轮次请求（Multi Round-Trip Requests，MRTR）来代替服务器到客户端的回调。

第一个响应：

```json
{
  "resultType": "input_required",
  "inputRequests": {
    "confirm": {
      "method": "elicitation/create",
      "params": {
        "mode": "form",
        "message": "Export notes to archive?",
        "requestedSchema": {
          "type": "object",
          "properties": {
            "confirm": {"type": "boolean"}
          },
          "required": ["confirm"]
        }
      }
    }
  },
  "requestState": "opaque-integrity-protected-value"
}
```

客户端取得输入后，用一个新 JSON-RPC id 重试原始方法：

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "notes.export",
    "arguments": {"query": "private", "destination": "archive"},
    "requestState": "opaque-integrity-protected-value",
    "inputResponses": {
      "confirm": {
        "action": "accept",
        "content": {"confirm": true}
      }
    },
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {
        "elicitation": {"form": {}}
      }
    }
  }
}
```

每个 `inputRequests` 值都是一条带 `method` 和 `params` 的完整内嵌请求。它的键必须与 `inputResponses` 中对应的条目匹配。表单引导（form elicitation）使用对象根的 `requestedSchema`，而客户端必须在服务器请求它之前就已声明表单引导能力。

当前能力有两种合法的表单声明形式。`{"elicitation":{}}` 隐式支持表单引导，而 `{"elicitation":{"form":{}}}` 显式声明它。仅 URL 的声明（如 `{"elicitation":{"url":{}}}`）不支持表单请求。此时服务器返回 HTTP 400 加 `-32021`，且 `data.requiredCapabilities` 等于 `{"elicitation":{"form":{}}}`。

把 `requestState` 当作敌意输入。对它签名或加密，校验它，并在重放成为问题时把它绑定到方法、工具、精确参数、用途、过期时间、主体和一次性 nonce（number used once）。本课代码用 HMAC 和精确参数匹配让这条边界可见。

nonce 账本不能活在一个网关对象里。这个可运行模型注入了一个有界的、按 TTL 修剪的、可被多个网关实例共享的重放存储。它的原子认领（claim）就是执行边界：只有一次通过校验的接受或一次显式的终态拒绝会消耗状态。一个格式错误的响应或 `cancel` 不执行任何东西，并保持可重试直到过期。生产机队需要在共享持久存储里有同样的条件认领。

不要把隐藏的确认上下文存进协议会话。任何服务器实例都应能校验那次重试。

> Each `inputRequests` value is a complete embedded request with `method` and `params`. Its key must match the corresponding entry in `inputResponses`.
> Treat `requestState` as hostile input. Sign or encrypt it, validate it, and bind it to method, tool, exact arguments, purpose, expiry, principal, and a one-time nonce when replay matters.
> The nonce ledger must not live inside one gateway object... Its atomic claim is the execution boundary: only a validated acceptance or explicit terminal decline consumes state.
> Do not store hidden confirmation context in a protocol session. Any server instance should be able to validate the retry.

### Rule of two for high-risk calls · 高风险调用的「二取二」法则

沿三个轴对一个调用分类：

- 它消费不可信输入。
- 它能访问敏感数据。
- 它造成一个重大的外部动作。

一个单独的自动步骤不应同时集齐三者。拆开它、降低权限，或通过 MRTR 请求显式的用户输入。这是一个设计启发式，不是协议能力。

> Classify a call along three axes: it consumes untrusted input; it can access sensitive data; it causes a consequential external action.
> A single automatic step should not combine all three. Split it, reduce privilege, or request explicit user input through MRTR. This is a design heuristic, not a protocol capability.

### Reduce authority before execution · 在执行之前收敛权力

无状态本身不是安全。它移除的是隐藏的协议历史，但一个自包含请求仍然可以让一个权力过大的处理器泄露数据或做出不可逆的改变。安全来自在每个边界上收敛权力：

1. **带类型的动词（typed verb）。** 暴露一个有界的操作，如 `archive_note`，而不是一个能表达无关权力的泛型 `run` 或 `request` 工具。
2. **经过校验的参数。** 在可行时使用封闭 schema，拒绝未知字段，只规范化标识符一次，限制大小，并在策略评估之前校验目的地、租户与资源归属。
3. **现行的授权。** 把已认证主体绑定到确切的动词、资源、环境和规范化参数。工具注解与客户端能力不授予这种权力。
4. **绑定动作的审批（action-bound approval）。** 对一次重大调用，把审批绑定到「带类型动词 + 规范化参数」的摘要，外加主体、过期时间和一次性策略。任何字段改变都需要新的决定。
5. **一等公民式拒绝。** 把拒绝、过期审批、用户拒绝和不安全目的地建模为不执行任何副作用普通结果。不要把拒绝翻译成一个更弱的回退工具。
6. **脱敏的审计证据。** 记录谁发起请求、用了哪个已接纳的描述符与策略版本、哪个规范化目标被授权、决定为何允许或拒绝、以及执行是否开始。存储摘要或脱敏值，而不是秘密。

每一步都在收窄下一个组件能做的事。最终处理器应该收到的是一条已校验的领域命令，而不是原始模型文本加宽泛的凭据。在 MRTR 重试、任务更新或网关转发调用上，重复整条链。一次更早的审批不会把后续请求变成可信的会话流量。

> Statelessness alone is not safety. Safety comes from reducing authority at each boundary.
> Typed verb. Expose one bounded operation such as `archive_note`, not a generic `run` or `request` tool that can express unrelated powers.
> Action-bound approval... Any changed field requires a new decision.
> Repeat the entire chain on an MRTR retry, task update, or gateway-forwarded call. An earlier approval does not turn later requests into trusted session traffic.

### Current and legacy interaction paths · 现行与遗留的交互路径

Roots、Sampling 和 Logging 对新的 2026-07-28 实现已弃用。网关只能把旧的请求通道代码保留为按版本门控的兼容路径。

不要围绕「按会话的采样限流器」构建新防御。把配额应用到已认证主体、签发者、资源、工具和时间窗口上。对现行的交互式工作，检查 MRTR 输入请求与响应。

> Roots, Sampling, and Logging are deprecated for new 2026-07-28 implementations. A gateway may retain older request-channel code only as a version-gated compatibility path.
> Do not build a new defense around a per-session sampling limiter. Apply quotas to authenticated principal, issuer, resource, tool, and time window.

### Stateless transport checks · 无状态传输检查

- 在唯一的 POST 端点接受现代 MCP 消息。
- 对现代的 GET 和 DELETE 返回 405。
- 不铸造也不依赖 `Mcp-Session-Id`。
- 把遗留的会话与重放头忽略为权威输入。
- 对该 POST 返回 JSON 或请求范围的 SSE。
- 只对已选择启用（opted-in）的长生命变更通知使用 `subscriptions/listen`。

```figure
tp-tool-poisoning
```

> Accept modern MCP messages at the single POST endpoint. Return 405 for modern GET and DELETE.
> Do not mint or depend on `Mcp-Session-Id`. Ignore legacy session and replay headers as authority inputs.
> Use `subscriptions/listen` only for opted-in long-lived change notifications.

## Build It · 动手造

`code/main.py` 实现一个小型进程内安全网关模型。它规范化并固定完整的工具描述符，报告元数据投毒与遮蔽，校验现代请求信封与路由取值，并执行一次带签名 `requestState` 和注入共享重放存储的两轮确认导出。

这个模型在 HTTP 适配器解析完 JSON 正文与路由头之后启动。它不校验 `Content-Type` 或 `Accept`。把同一个分发器接到第 09 课完整的 Streamable HTTP 适配器上，后者要求 `Content-Type: application/json` 以及同时包含 `application/json` 和 `text/event-stream` 的 `Accept` 值。

运行它：

```bash
cd phases/13-tools-and-protocols/15-mcp-security-tool-poisoning
python3 code/main.py
python3 -m unittest discover code/tests -v
```

示例刻意修改了一个描述符。扫描器与摘要比较各自产生独立的发现。随后导出演示了 `input_required` 响应与无状态重试。

> `code/main.py` implements a small in-process security gateway model. It canonicalizes and pins full tool descriptors, reports metadata poisoning and shadowing, validates the modern request envelope and routing values, and performs a two-round confirmed export with signed `requestState` and an injected shared replay store.
> The sample intentionally mutates a descriptor. The scanner and digest comparison produce independent findings.

## Use It · 实战用法

把 `SAFE_TOOLS` 换成你自己已批准服务器的规范化快照。把凭据和秘密排除在快照之外。在更新一个描述符的摘要之前，审查每一个新增或变更的描述符。

在网关处，在发现时和分发前各运行同样的检查。缓存可以减少发现工作，但缓存的审批必须在描述符变化时过期或失效。

> Replace `SAFE_TOOLS` with a normalized snapshot from your own approved servers. Keep credentials and secrets out of the snapshot.
> Review every new or changed descriptor before updating its digest.
> At a gateway, run the same checks during discovery and again before dispatch.

## Ship It · 交付

本课交付 `outputs/skill-mcp-threat-model.md`。它产出一份覆盖元数据、路由、能力、授权、MRTR、缓存、注册表与兼容边界的现行协议威胁模型。

> This lesson ships `outputs/skill-mcp-threat-model.md`. It produces a current-protocol threat model across metadata, routing, capability, authorization, MRTR, caching, registry, and compatibility boundaries.

## Exercises · 练习

1. 把已认证主体与当前授权决定绑定到密封的 MRTR 状态里，然后拒绝来自不同主体的重试。
2. 把内存重放存储换成持久化的条件插入，证明两个进程不能同时认领同一个 nonce。
3. 在重放认领之后、模拟导出之前注入一个失败。定义并测试让恢复安全的交易或幂等规则。
4. 修改一个工具的 `inputSchema` 而不改它的描述。确认整描述符固定能抓住它。
5. 添加一条策略：当 `tools/list` 随主体不同而不同时，拒绝公开缓存。
6. 在网关后面建模一台更旧的服务器。把所有握手与会话行为放进一个显式的 `2025-11-25` 兼容分支。

## Key Terms · 术语表

| 术语 | 含义 |
|------|---------|
| Metadata poisoning（元数据投毒） | 嵌入工具描述符中的指令或欺骗性声明 |
| Rug pull（描述符急拉） | 对先前已批准描述符的更改 |
| Tool shadowing（工具遮蔽） | 由重复的无限定名称引起的歧义路由 |
| Header mismatch（头不匹配） | 路由头与 JSON-RPC 正文不一致，错误 `-32020` |
| Hash pin（哈希固定） | 完整已批准描述符的摘要 |
| MRTR | 服务器请求输入时使用的无状态响应与重试模式 |
| `requestState` | 不透明的往返值，必须当作不可信输入对待 |
| Capability declaration（能力声明） | 关于协议兼容性的陈述，不是授权 |
| Implicit form support（隐式表单支持） | 空的 `elicitation` 能力对象，等价于支持表单 |
| Qualified tool name（带限定符工具名） | 稳定的网关名称，如 `notes.search` |

## Further Reading · 延伸阅读

- [MCP security and trust guidance](https://modelcontextprotocol.io/specification/2026-07-28#security-and-trust--safety) —— MCP 安全与信任指导
- [Multi Round-Trip Requests](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr) —— 多轮次请求（MRTR）
- [Streamable HTTP transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) —— Streamable HTTP 传输
- [Deprecated features](https://modelcontextprotocol.io/specification/2026-07-28/deprecated) —— 已弃用特性
