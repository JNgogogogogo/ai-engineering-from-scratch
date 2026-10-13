# MCP Model Input: Sampling Migration and Stateless MRTR · MCP 模型输入：Sampling 迁移与无状态 MRTR

> MCP 2026-07-28 deprecates Sampling for new designs and removes the server-to-client request channel. If an existing workflow still needs the client's model, the server returns an `input_required` result and the client retries the original request with the model output. The reasoning loop becomes explicit, bounded, and stateless at the protocol layer.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 13 · 07 (MCP server), Phase 13 · 10 (resources and prompts)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 解释为什么 Sampling 在 MCP 2026-07-28 中被弃用，并为新服务器选择直连模型集成这一默认方案。
- 实现一个兼容工作流，让 `sampling/createMessage` 通过多轮往返请求（Multi Round-Trip Requests，MRTR）继续工作。
- 把协议修订版和客户端能力放进每个请求的 `_meta` 对象。
- 返回 `resultType: "input_required"`，并让客户端用一个全新的 JSON-RPC id 重试原始方法。
- 对 `requestState` 做完整性保护，并把它绑定到主体、方法、参数和过期时间。
- 用能力检查、审批、响应校验和轮数上限，约束模型参与的循环。

> Explain why Sampling is deprecated in MCP 2026-07-28 and choose the direct model integration default for new servers.
> Implement a compatibility workflow that carries `sampling/createMessage` through Multi Round-Trip Requests (MRTR).
> Put the protocol revision and client capabilities in every request `_meta` object.
> Return `resultType: "input_required"` and retry the original method with a fresh JSON-RPC id.
> Integrity-protect `requestState` and bind it to the principal, method, arguments, and expiry.
> Bound model-assisted loops with capability checks, approval, response validation, and a round limit.

## The Decision Before the Protocol · 协议之前要先做的决定

像 `summarize_repo` 这样的工具需要两种工作：

1. 确定性工作：列出文件、读取被允许的文件、校验路径、组装内容。
2. 模型工作：挑选有代表性的文件，并综合出摘要。

现在你有两种都成立的架构。

### New server: integrate with a model provider directly · 新服务器：直连模型提供商

这是当前的默认方案。服务器自己负责模型选择、凭据、预算、重试和可观测性，然后向 MCP 客户端返回一个普通的 `tools/call` 结果。

当服务器本身已经是一个托管服务，或者可预测的模型行为比使用宿主的模型更重要时，选这一种。

### Existing Sampling workflow: migrate it to MRTR · 既有 Sampling 工作流：迁移到 MRTR

Sampling 在弃用窗口期内仍然存在。面向 2026-07-28 的服务器不能把一个活的 `sampling/createMessage` 请求发回客户端，而是把这个请求嵌入到一个 `InputRequiredResult` 里。

只有当「使用客户端的模型和凭据」是真实的产品需求时，才选这条兼容路径。要记录一个移除计划，因为新的实现不应再采用已弃用的 Sampling。

> A tool such as `summarize_repo` needs two kinds of work: deterministic work and model work. You now have two valid architectures.
> This is the current default. The server owns model selection, credentials, budgets, retries, and observability. It returns one ordinary `tools/call` result to the MCP client. Choose this when the server is already a hosted service or when predictable model behavior matters more than using the host's model.
> A server targeting 2026-07-28 cannot send a live `sampling/createMessage` request back to the client. It instead embeds that request in an `InputRequiredResult`. Choose this compatibility path only when using the client's model and credentials is a real product requirement. Record a removal plan because new implementations should not adopt deprecated Sampling.

## The Stateless Contract · 无状态契约

2026 年 7 月的协议没有 `initialize` 交换，没有 `notifications/initialized`，也没有 `Mcp-Session-Id`。每个请求都携带过去握手里才有的那些信息：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "summarize_repo",
    "arguments": {"audience": "developer"},
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {"sampling": {}},
      "io.modelcontextprotocol/clientInfo": {
        "name": "lesson-client",
        "version": "1.0.0"
      }
    }
  }
}
```

服务器对每个请求都校验修订版本。缺失或非字符串的版本是无效参数，返回 `-32602`。不支持的字符串返回 `-32022`，并附带精确的数据 `{"supported":["2026-07-28"],"requested":"<client version>"}`。缺少 Sampling 能力则返回 `-32021`，并把 `data.requiredCapabilities` 设为 `{"sampling":{}}`。

没有 JSON-RPC `id` 的信封是通知。接收方可以处理它，但既不发出成功响应也不发出错误响应。Streamable HTTP 适配器对已接受的通知返回 `202 Accepted`，无响应体。

服务器同样要实现 `server/discover`，使用精确的 `supportedVersions` 键、能力、`ttlMs` 和 `cacheScope`，让客户端在调用工具之前就能了解并缓存服务器的契约。因为发现结果公布了 `tools`，服务器也必须实现强制的 `tools/list`。它的确定性 `summarize_repo` 描述符包含一个合法的对象 `inputSchema`、`resultType: "complete"`、服务器身份元数据和公开缓存提示。

每个现代的成功结果都有一个判别字段：

- `resultType: "complete"` 表示操作已结束。
- `resultType: "input_required"` 表示客户端必须先完成嵌入的请求再重试。
- 扩展可以定义更多的结果类型。Tasks 扩展会在第 13 课加入 `"task"`。

> The July 2026 protocol has no `initialize` exchange, no `notifications/initialized`, and no `Mcp-Session-Id`. Every request carries the information that used to live in the handshake.
> The server validates the revision on every request. A missing or non-string version is invalid params, `-32602`. An unsupported string returns `-32022` with exact data `{"supported":["2026-07-28"],"requested":"<client version>"}`. A missing Sampling capability returns `-32021` with `data.requiredCapabilities` set to `{"sampling":{}}`.
> An envelope without a JSON-RPC `id` is a notification. The receiver may process it, but it emits neither a success response nor an error response.
> Every successful modern result has a discriminator: `resultType: "complete"` means the operation finished. `resultType: "input_required"` means the client must fulfill embedded requests and retry.

## One MRTR Round · 一轮 MRTR

服务器在处理请求时不能反过来调用客户端。它改为返回这样的结果：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "resultType": "input_required",
    "inputRequests": {
      "pick_files": {
        "method": "sampling/createMessage",
        "params": {
          "messages": [
            {
              "role": "user",
              "content": {
                "type": "text",
                "text": "Choose three representative files and return a JSON array."
              }
            }
          ],
          "systemPrompt": "Return only the requested value.",
          "modelPreferences": {
            "costPriority": 0.8,
            "intelligencePriority": 0.2
          },
          "maxTokens": 400
        }
      }
    },
    "requestState": "opaque-integrity-protected-value"
  }
}
```

客户端确认自己支持 Sampling，应用自己的审批和模型策略，取得模型响应。然后它发送一个使用不同 JSON-RPC id 的新请求：

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "summarize_repo",
    "arguments": {"audience": "developer"},
    "inputResponses": {
      "pick_files": {
        "role": "assistant",
        "content": {
          "type": "text",
          "text": "[\"README.md\", \"server.py\", \"docs/intro.md\"]"
        },
        "model": "host-model",
        "stopReason": "endTurn"
      }
    },
    "requestState": "opaque-integrity-protected-value",
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {"sampling": {}}
    }
  }
}
```

这次重试不是协议会话的延续。它是一个新请求：重复原始的方法和参数，只加上本轮的 `inputResponses`，并逐字节回显 `requestState`。

MRTR 只允许出现在 `tools/call`、`prompts/get` 和 `resources/read` 上。服务器不得从不相关的方法返回 `input_required`。

> The server cannot call the client while handling the request. It returns this result instead.
> The client verifies that it supports Sampling, applies its approval and model policies, and obtains a model response. Then it sends a new request with a different JSON-RPC id.
> The retry is not a continuation of a protocol session. It is a new request that repeats the original method and arguments, adds only the current round's `inputResponses`, and echoes `requestState` byte for byte.
> MRTR is allowed only on `tools/call`, `prompts/get`, and `resources/read`. A server must not return `input_required` from unrelated methods.

## Multi-Round State · 多轮状态

本课需要两次模型调用：

1. `pick_files` 返回一个 JSON 数组。
2. `summary` 返回最终的文字摘要。

每次重试只携带本轮的响应。因此服务器要把阶段和已校验的中间数据放进下一个 `requestState`。

要把这个值当作攻击者可控的。只签名一个裸的阶段名是不够的。要把状态绑定到：

- 已认证的主体，而不是自报的 `clientInfo`；
- 发起的方法；
- 原始参数的摘要；
- 一个很短的过期时间；
- 当前阶段和已校验的中间值。

不需要保密时用 HMAC。当客户端不应读到状态内容时，使用认证加密。签名错误、已过期、主体改变或参数改变，一律以 `-32602` 拒绝。

客户端不得解析或修改 `requestState`。它唯一的职责就是在重试时原样回显这个字符串。

> Each retry carries only the responses for that round. The server therefore puts the phase and validated intermediate data into the next `requestState`.
> Treat that value as attacker-controlled. Signing a raw phase name is not enough. Bind the state to: the authenticated principal, not self-reported `clientInfo`; the originating method; a digest of the original arguments; a short expiry; the current phase and validated intermediate values.
> Use HMAC when confidentiality is not required. Use authenticated encryption when the client must not read the state. Reject a bad signature, expired value, changed principal, or changed arguments with `-32602`.
> The client must not parse or modify `requestState`. Its only job is to echo the exact string on the retry.

## Model Preferences Are Hints · 模型偏好只是提示

`costPriority`、`speedPriority` 和 `intelligencePriority` 是相互独立的偏好。它们不是概率分布，也不需要加和为一。客户端可以忽略它们，因为模型策略归客户端所有。

如果你在维护一条遗留的 Sampling 流程，把 `includeContext` 保持在 `"none"`。其他上下文模式会加大泄露风险，而且它们本身也已被弃用。在请求里显式传递最小限度的上下文。

> `costPriority`, `speedPriority`, and `intelligencePriority` are independent preferences. They are not a probability distribution and do not need to sum to one. The client may ignore them because the client owns model policy.
> Keep `includeContext` at `"none"` if you maintain a legacy Sampling flow. Other context modes increase leakage risk and are themselves deprecated. Pass the minimum explicit context in the request.

## Safety Invariants · 安全不变量

对嵌入的 Sampling 请求来说，客户端就是信任边界。

- 当策略要求审批时，向用户展示服务器要求模型做什么。
- 给 MRTR 轮数设上限。否则恶意服务器可以制造一个烧模型的循环。
- 在把每个 sampling 响应用作文件名、URL 或工具输入之前，先校验它。
- 限制每轮的字节数和 token 数。
- 拒绝当前客户端能力中未声明的输入请求。
- 不让模型输出参与授权决策。
- 记录发起方法和输入请求键，但不记录敏感的提示词内容。

`clientInfo` 和 `serverInfo` 是展示与诊断用的元数据。绝不要把任何一方当作已认证的身份。

> The client is the trust boundary for embedded Sampling requests.
> Show the user what the server is asking the model to do when policy requires approval.
> Cap MRTR rounds. A malicious server can otherwise create a model-spend loop.
> Validate every sampling response before using it as a filename, URL, or tool input.
> `clientInfo` and `serverInfo` are display and diagnostics metadata. Never use either as an authenticated identity.

```figure
t3-sampling-flip
```

## Build It · 动手造

`code/main.py` 在没有任何第三方包的情况下实现了完整的两轮流程：

- `server/discover` 返回 `supportedVersions`，公布工具支持，并返回缓存提示。
- `tools/list` 返回一个确定性、可缓存的 `summarize_repo` 描述符，带对象型输入 schema。
- `tools/call` 校验每个请求的元数据。
- 第一个结果嵌入用于文件选择的 `sampling/createMessage`。
- 第一次重试校验模型结果，并嵌入第二个请求。
- 受 HMAC 保护的 `requestState` 在相互独立的请求之间携带阶段信息。
- 最终结果使用 `resultType: "complete"`。

一个假宿主模型让示例保持确定性。接入真实宿主时，只需要替换 `fake_host_model`。服务器端的状态机应当保持确定性、可测试。

> `code/main.py` implements the full two-round flow with no third-party package: `server/discover` returns `supportedVersions`, advertises tool support, and returns cache hints; `tools/list` returns a deterministic, cacheable `summarize_repo` descriptor with an object input schema; `tools/call` validates per-request metadata; the first result embeds `sampling/createMessage` for file selection; the first retry validates the model result and embeds a second request; HMAC-protected `requestState` carries the phase between independent requests; the final result uses `resultType: "complete"`.
> The fake host model makes the example deterministic. Replace only `fake_host_model` when connecting a real host. The server-side state machine should stay deterministic and testable.

## Use It · 实战用法

在仓库根目录：

```bash
cd phases/13-tools-and-protocols/11-mcp-sampling/code
python3 main.py
python3 -m unittest discover tests -v
```

预期检查点：

- 发现返回带 `ttlMs` 和 `cacheScope` 的完整结果。
- 工具发现返回同样的排序描述符，带 `resultType`、服务器身份和缓存提示。
- 缺失能力和不支持的版本使用精确的 `-32021` 与 `-32022` 错误数据。
- 无 id 的通知不产生任何 JSON-RPC 响应。
- 请求 id 是 `[1, 2, 3]`，证明每一轮 MRTR 都相互独立。
- 前两个结果是 `input_required`。
- 最终结果是 `complete`，包含选中的文件和摘要。
- 在重试时修改原始参数会让请求状态检查失败。

> From the repository root: ... Expected checkpoints: Discovery returns a complete result with `ttlMs` and `cacheScope`. Tool discovery returns the same sorted descriptor with `resultType`, server identity, and cache hints. Missing capabilities and unsupported versions use exact `-32021` and `-32022` error data. An id-less notification produces no JSON-RPC response. Request ids are `[1, 2, 3]`, proving each MRTR round is independent. The first two results are `input_required`. The final result is `complete` and contains the selected files plus summary. Changing the original arguments on a retry fails the request-state check.

## Ship It · 交付

`outputs/skill-sampling-loop-designer.md` 现在是一份迁移规划器。它先决定是否应当移除 Sampling、改用直连模型集成。如果确需兼容，它就产出 MRTR 轮次、状态绑定、能力门控、预算、校验和移除计划。

> `outputs/skill-sampling-loop-designer.md` is now a migration planner. It first decides whether Sampling should be removed in favor of direct model integration. If compatibility is required, it produces the MRTR rounds, state binding, capability gate, budget, validation, and removal plan.

## Exercises · 练习

1. 把文件选择的响应改成无效 JSON。确认服务器返回 `-32602` 而不是信任模型输出。
2. 在第一次调用和重试之间修改 `audience`。解释为什么封印状态能阻止跨请求复用。
3. 加第三轮，让宿主点评摘要。把早先的摘要放进签名状态里携带，并把整个流程限制在三轮以内。
4. 移除 Sampling：把假宿主回调换成服务器自有的模型适配器。列出哪些审批、计费和可观测性职责随之转移到服务器。
5. 用一个超过截止时间一秒的状态值添加过期测试。

> 1. Change the file-selection response to invalid JSON. Confirm the server returns `-32602` instead of trusting model output.
> 2. Change `audience` between the first call and retry. Explain why the sealed state blocks cross-request reuse.
> 3. Add a third round that asks the host to critique the summary. Carry the earlier summary inside signed state and cap the entire flow at three rounds.
> 4. Remove Sampling by replacing the fake host callback with a server-owned model adapter. List which approval, billing, and observability responsibilities move to the server.
> 5. Add an expiry test using a state value that is one second past its deadline.

## Key Terms · 术语表

| Term | 在 2026-07-28 中的含义 |
|------|------------------------|
| Sampling | 已弃用的特性：向客户端的模型请求一次补全 |
| MRTR | 请求期间需要客户端输入时使用的无状态重试模式 |
| `InputRequiredResult` | 带 `resultType: "input_required"` 的结果 |
| `inputRequests` | 服务器分配的映射，内嵌 elicitation、sampling 或 roots 请求 |
| `inputResponses` | 当前轮的客户端结果，键与 `inputRequests` 对应 |
| `requestState` | 不透明的服务器状态，由客户端逐字节回显并由服务器校验 |
| `resultType` | 现代 MCP 结果必需的判别字段 |
| Direct model integration（直连模型集成） | 需要模型推理的新服务器应采用的推荐替代方案 |
| Capability gate（能力门控） | 防止发送客户端未公告的内嵌请求的规则 |
| Loop budget（循环预算） | 一次操作允许的最大轮数、token、字节、时间和花费 |

> | Term | Meaning in 2026-07-28 |
> |------|------------------------|
> | Sampling | Deprecated feature that asks the client's model for a completion |
> | MRTR | Stateless retry pattern for client input required during a request |
> | `InputRequiredResult` | Result with `resultType: "input_required"` |
> | `inputRequests` | Server-assigned map of embedded elicitation, sampling, or roots requests |
> | `inputResponses` | Current round's client results keyed like `inputRequests` |
> | `requestState` | Opaque server state echoed exactly by the client and verified by the server |
> | `resultType` | Required discriminator for modern MCP results |
> | Direct model integration | Recommended replacement for new servers that need model inference |
> | Capability gate | Rule that prevents sending an embedded request the client did not advertise |
> | Loop budget | Maximum rounds, tokens, bytes, time, and spend allowed for the operation |

## Legacy Compatibility · 遗留兼容性

固定在 2025-11-25 的客户端仍然可以在活连接上使用旧式的服务器发起 `sampling/createMessage` 流程。把这种行为只保留在版本专用适配器里。不要把这条会话式路径当成 2026-07-28 服务器的架构。

官方 SDK 可以为老旧对端翻译现代的 `input_required` 处理器。那个垫片是兼容性边界，不是添加新的会话依赖逻辑的许可。

> A client pinned to 2025-11-25 may still use the older server-initiated `sampling/createMessage` flow over a live connection. Keep that behavior in a version-specific adapter only. Do not make the sessionful path the architecture for a 2026-07-28 server.
> Official SDKs can translate modern `input_required` handlers for older peers. That shim is a compatibility boundary, not permission to add new session-dependent logic.

## Further Reading · 延伸阅读

- [MCP 2026-07-28 Multi Round-Trip Requests](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)
- [MCP 2026-07-28 changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
- [MCP Sampling deprecation](https://modelcontextprotocol.io/seps/2577-deprecate-roots-sampling-and-logging)
- [MCP 2026-07-28 server discovery](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
