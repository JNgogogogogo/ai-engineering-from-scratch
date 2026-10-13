# MCP Conformance Engineering: Versioning, Evidence, and Operations · MCP 一致性工程：版本化、证据与运维

> 一个服务器并不会因为它的快乐路径在某个 SDK 下跑通就叫一致（conformant）。一致性存在于线上字节、版本边界、中间设备之间，以及回滚期间。
>
> A server is not conformant because its happy path worked through one SDK. Conformance lives at the wire, at version boundaries, through intermediaries, and during rollback.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 13 · 09 (transports), Phase 13 · 17 (gateways), Phase 13 · 30 (registry admission)
**Time:** ~100 minutes

## Learning Objectives · 学习目标

- 把规范性（normative）的 MCP 规则变成黄金与反例的线上报文记录（transcript）
- 把严格的 `2026-07-28` 行为与有界的遗留（legacy）回退分开
- 区分增量式未知字段与无效的未知 `resultType`
- 把原始 JSON-RPC 证据与 SDK 归一化视图做对比
- 通过真实的代理边界证明头部与体的完整性
- 用脱敏的报文记录、健康与回滚证据为发布把关

> Turn normative MCP rules into golden and negative wire transcripts.
> Keep strict `2026-07-28` behavior separate from bounded legacy fallback.
> Distinguish additive unknown fields from an invalid unknown `resultType`.
> Compare raw JSON-RPC evidence with an SDK-normalized view.
> Prove header and body integrity through a real proxy boundary.
> Gate releases with redacted transcript, health, and rollback evidence.

## The Problem · 问题在哪

你的客户端通过一个 SDK 调 `tools/list`，拿到了工具。集成测试通过。

但这个结果留下一堆没回答的问题：

- 请求带上了现代的每请求协议元数据吗？
- `MCP-Protocol-Version`、`Mcp-Method` 和 `Mcp-Name` 与 JSON-RPC 体一致吗？
- 响应在网络上带有合法的 `resultType`，还是 SDK 自己合成（synthesize）了一个？
- 客户端会保留未来的增量字段吗？
- 一个可识别的现代错误会不会意外触发遗留握手？
- 代理保住了源站（origin）状态码与 JSON-RPC 错误吗？
- 通知序列化器有没有发出被禁止的响应？
- 运维能否在不存储秘密的前提下，证明一次发布为什么晋级（promote）或回滚？

一致性是一组可观察的不变量（invariant）。构建一个测试框架（harness），在生产流量不得不发现它们之前就把它们捕获。

```figure
mcp-conformance-operations
```

> Your client calls `tools/list` through an SDK and gets tools. The integration test passes. ... Did the response contain a valid `resultType` on the wire, or did the SDK synthesize one? ... Conformance is a set of observable invariants. Build a harness that captures those invariants before production traffic has to discover them.

## Start With Version Eras · 从版本时代说起

MCP `2026-07-28` 使用自包含的每请求元数据。现代请求携带 `params._meta.io.modelcontextprotocol/protocolVersion` 和 `params._meta.io.modelcontextprotocol/clientCapabilities`。确切的名字空间键很重要；裸的 `protocolVersion` 或 `clientCapabilities` 别名都是畸形的。当镜像路由头出现在 HTTP 边界时，它们的值必须与 JSON-RPC 体一致。现代成功结果携带 `resultType`。

直到 `2025-11-25` 的各版本使用更早的初始化时代。没有 `resultType` 的遗留结果，只有在客户端已经选择那个更早时代之后，才被解释为完成。

不要造一个同时接受两种形状的宽容校验器。使用两个分支：

| 分支 | 进入证据 | 缺失 `resultType` | 初始化 |
|---|---|---|---|
| 现代 | 成功的 `server/discover` 或可识别的现代响应 | 无效 | 不是默认路径 |
| 遗留 | 配置的允许清单，加上在现代探测（probe）不确定之后一个合法的遗留 `initialize` 结果 | 解释为完成 | 那个时代所要求的 |

这种分离防止一个畸形的现代对端反而获得更弱的校验。

> MCP `2026-07-28` uses self-contained per-request metadata. ... The exact namespaced keys matter; bare `protocolVersion` or `clientCapabilities` aliases are malformed. ... Do not create one permissive validator that accepts both shapes at once. Use two branches ... The separation prevents a malformed modern peer from being rewarded with weaker validation.

### Strict mode · 严格模式

严格模式要求现代行为的证明。一次成功的 `server/discover` 证明现代分支。一个可识别的现代 JSON-RPC 错误同样证明它。修正请求，或者停下。绝不要因为服务器返回了 `-32020`、`-32021` 或 `-32022` 就降级。

> Strict mode requires proof of modern behavior. A successful `server/discover` proves the modern branch. A recognized modern JSON-RPC error also proves it. Correct the request or stop. Never downgrade because the server returned `-32020`, `-32021`, or `-32022`.

### Fallback mode · 回退模式

回退模式执行一次有界的现代探测。超时、空回复、被关闭的连接或不可识别的响应都算不确定（inconclusive）——它不证明对端是遗留的。只有显式配置或列入允许清单、以兼容为目的的端点，才可以随后接受一次有界的遗留探测；客户端也只有在验证了该探测的 `initialize` 结果与协商出的遗留修订版之后，才选择遗留分支。

回退不是「任何错误之后都试遗留」。可识别的现代错误包含有用的纠正信息。在它之后降级，可能掩盖头部不匹配、缺失的能力声明或不支持的版本。

这防止攻击者、故障或过滤代理通过丢弃现代响应来强迫降级。把端点策略、不确定的现代观察、确切的阳性遗留证据与所选时代一起记录下来。

在每份报文记录旁边记录所选时代。缺了这个事实，同一个缺失字段可能在这一轮测试里看起来可接受、在另一轮里无效。

> Fallback mode performs one bounded modern probe. ... It does not prove that the peer is legacy. ... Fallback is not “try legacy after any error.” A recognized modern error contains useful correction information. Downgrading after it can hide a header mismatch, missing capability declaration, or unsupported version. ... This prevents an attacker, outage, or filtering proxy from forcing downgrade by dropping the modern response. ... Record the selected era beside every transcript. Without that fact, a missing field can look acceptable in one test run and invalid in another.

## Build a Transcript Corpus · 构建报文记录语料库

报文记录（transcript）夹具记录的是跨越边界的东西，而不只是 SDK 调用：

```json
{
  "name": "golden-modern-list",
  "era": "modern",
  "headers": {
    "MCP-Protocol-Version": "2026-07-28",
    "Mcp-Method": "tools/list"
  },
  "request": {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {
      "_meta": {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {}
      }
    }
  },
  "responseStatus": 200,
  "responseBody": {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
      "resultType": "complete",
      "tools": []
    }
  }
}
```

保留两类夹具。

> A transcript fixture records what crossed the boundary, not only the SDK call ... Keep two classes of fixtures.

### Golden transcripts · 黄金报文记录

黄金记录证明被接受的行为：

- 元数据与头部匹配的现代发现或方法请求
- 带必需字段的完整结果
- 方法可以请求更多输入时的 `input_required` 结果
- 只有在对应能力已通告之后的扩展结果
- 没有 `resultType` 的遗留结果，但只在所选的遗留时代
- 通知被处理且没有 JSON-RPC 响应

黄金记录追求精确，不追求大。把易变的 ID 和时间戳变成确定的，或在比较前归一化。

> Golden transcripts prove accepted behavior ... A golden transcript is precise, not large. Keep volatile IDs and timestamps deterministic or normalize them before comparison.

### Negative transcripts · 反例报文记录

反例记录证明拒绝行为：

- 头部与体不匹配
- 缺失每请求能力
- 匹配到的协议版本不受支持
- 缺失现代 `resultType`
- 未知或未通告的 `resultType`
- 响应 `jsonrpc` 不是 `2.0`，或 ID 的值或 JSON 类型不同
- 一个响应同时含 `result` 与 `error`，或两者皆无
- 错误缺整数 `code` 或字符串 `message`
- 已知协议错误映射到错误的 HTTP 状态
- 为通知发出了响应
- 畸形的 JSON-RPC 信封
- 代理把协议错误压扁

对每个反例，断言拒绝边界与稳定的错误码。「调用失败了」太弱。代理生成的 500 和源站的 `-32020` 可以都表现为失败，却给运维讲完全不同的故事。

头部不匹配夹具必须包含服务器真实的 HTTP 400 JSON-RPC 响应，带匹配的请求 ID 和错误码 `-32020`。每当本地校验器观察到 `HeaderMismatch` 就自动强制这一点；不要把响应验证做成可选的夹具开关。一个 HTTP 500 且无 body 的用例，即使本地拒绝码正确也判失败。只验证到「自己的请求校验器抛了异常」就停下的测试框架，测的只是它自己，不是服务器的线上行为。

官方 MCP conformance 项目可以作为外部套件和带版本的参考。你自己的本地记录也要保留：它们捕获的是你的代理、SDK、认证、扩展和发布路径，这些通用套件不可能知道。

> For each negative case, assert the rejection boundary and stable error code. “The call failed” is too weak. A proxy-generated 500 and an origin `-32020` can both look like failure while telling operators completely different stories. ... The header-mismatch fixture must include the server's actual HTTP 400 JSON-RPC response with the matching request ID and error code `-32020`. Enforce that automatically whenever the local validator observes `HeaderMismatch`; do not make response verification an optional fixture flag. ... The official MCP conformance project is useful as an external suite and versioned reference. Keep your local transcripts too.

## Header Values Must Match the RPC Body · 头部值必须与 RPC 体一致

在现代 Streamable HTTP 中，中间设备（intermediary）可以使用镜像头做路由或执行策略。JSON-RPC 体仍然是协议的事实来源。不匹配是完整性故障，不是「挑一个值」的提示。

按这个顺序校验：

1. 解析并校验 JSON-RPC 信封与元数据类型。
2. 将 `MCP-Protocol-Version` 与 `params._meta.io.modelcontextprotocol/protocolVersion` 比较。
3. 将 `Mcp-Method` 与 `method` 比较。
4. 当方法带路由名时，将 `Mcp-Name` 与对应的体值比较。
5. 等式确立之后，再决定匹配到的版本与能力集是否受支持。

这个顺序把不匹配的 `-32020` 与不受支持版本的 `-32022` 区分开。它也防止网关按头部名字放行授权、而源站执行的是另一个体名字。

HTTP 字段名大小写不敏感，而字段值保持大小写敏感。查找前归一化头部名，并拒绝相互冲突的重复项。对不安全的、非 ASCII 的或首尾带空白的 `Mcp-Name`，先解码确切的 `=?base64?{Base64EncodedValue}?=` UTF-8 哨兵（sentinel）再与体比较。对不完整的哨兵、非法 Base64、非法 UTF-8 或裸的不安全值，用 `-32020` 拒绝。裸的首尾空白是无效的，即使体里含相同的字符——因为那个值在传输前本就必须经过哨兵编码。

中间设备可能在请求到达 MCP 服务器之前就拒绝畸形的 HTTP，所以它的失败可能是没有 JSON-RPC 的 HTTP 错误。记录拒绝来自中间设备还是源站。源站 MCP 服务器在处理了合法 JSON-RPC 请求时，应当使用协议错误契约。

> In modern Streamable HTTP, intermediaries can route or enforce policy using mirrored headers. The JSON-RPC body remains the protocol source of truth. A mismatch is an integrity failure, not a hint to choose one value. ... This order distinguishes mismatch `-32020` from unsupported version `-32022`. It also stops a gateway from authorizing the header name while the origin executes a different body name. ... HTTP field names are case-insensitive, while their values remain case-sensitive. ... An intermediary can reject malformed HTTP before a request reaches the MCP server, so its failure may be an HTTP error without JSON-RPC.

## Unknown Fields Are Not Unknown Results · 未知字段不是未知结果

前向兼容需要两条不同的规则。

### Additive unknown fields · 增量式未知字段

结果对象与 `_meta` 映射可以增加字段。校验器应按其角色保留或忽略一个增量字段，除非该字段违反保留契约。示例在证据里保留完整的原始结果，并接受已知结果旁边的 `futureHint`。

如果你是透明代理，保留未知字段通常比剥掉更安全。如果你是应用客户端，忽略它也可以是对的。你的差分测试仍应揭示 SDK 丢弃了它，从而证明这个行为是有意为之。

> Result objects and `_meta` maps can gain fields. A validator should preserve or ignore an additive field according to its role, unless the field violates a reserved contract. ... If you are a transparent proxy, preserving an unknown field is usually safer than stripping it. If you are an application client, ignoring it can be valid. Your differential test should still reveal that the SDK omitted it so the behavior is deliberate.

### Unknown `resultType` · 未知的 `resultType`

`resultType` 是判别符（discriminator）。核心现代结果使用 `complete` 或 `input_required`。扩展只有在能力被通告之后才能增加另一个值。例如 Tasks 扩展可以在协商的能力上下文中增加 `task`。

未知或未通告的判别符不能被安全地当作完成。客户端不知道它将丢弃的是什么生命周期。拒绝它。

因此，同一条原始响应可以同时含一个可接受的未知字段和一个不可接受的未知结果类型。两个用例都要测。

判别符只是第一层。在它之后校验方法特定的载荷。完整的 `tools/list` 结果需要 `tools` 数组，其描述符要有唯一的非空名字、有用的描述和对象根的 `inputSchema` 值。`task` 结果只对带 Tasks 能力的合格 `tools/call` 有效，并要求 `taskId`、已知状态、创建与更新时间戳和 `ttlMs`，外加合法的可选轮询间隔。完整的 `completion/complete` 结果需要 `completion` 对象，其中字符串值不超过 100 个、可选的非负整数 `total` 不小于返回的值数、可选的布尔 `hasMore`。一个拼写正确的 `resultType` 救不了畸形的载荷。

> `resultType` is a discriminator. Core modern results use `complete` or `input_required`. ... An unknown or unadvertised discriminator cannot be safely treated as complete. The client does not know the lifecycle it would be discarding. Reject it. ... The discriminator is only the first layer. Validate the method-specific payload after it. ... A well-spelled `resultType` cannot make a malformed payload conformant.

## The Notification Invariant · 通知不变量

JSON-RPC 通知没有 `id`。接收方不得发送 JSON-RPC 成功或错误响应。

对被接受的 HTTP 通知形状，测试框架期待 HTTP `202` 加空体。MCP `2026-07-28` 在 Streamable HTTP 上没有定义任何核心的客户端到服务器通知。示例使用一个带命名空间的课程扩展通知，只为测试单向序列化器不变量。不要把它当作新的核心方法来呈现。

测序列化器，而不只是处理器。处理器可能返回 `None`，而中间件把它包进一个 JSON 成功对象。捕获最终出口（egress）字节。

> A JSON-RPC notification has no `id`. The receiver must not send a JSON-RPC success or error response. ... Test the serializer, not only the handler. A handler may return `None` while middleware wraps it in a JSON success object. Capture the final egress bytes.

## Add an SDK Differential · 加一层 SDK 差分

SDK 常把网络对象变成方便的语言类型。这有用，但归一化后的对象证明不了收到的是什么。

对每个高风险夹具，捕获：

1. SDK 解码前的原始状态、头部与响应体。
2. SDK 归一化后的返回值或异常。
3. 所选时代的预期语义投影。
4. 被 SDK 提取、合成、剥离或改动的字段。

示例在比较应用载荷时，允许 SDK 独有地移除已知的网络簿记字段，如 `resultType`、`_meta`、`ttlMs` 和 `cacheScope`。它报告被丢弃的 `futureHint`，因为那个未知语义字段消失了。

不要假设每个差异都是 SDK bug。要点是让转换可见。决定你的组件是应用端点（可以忽略增量字段），还是透明中间设备（应当保留它）。

对你发布的每个 SDK 与版本都跑差分。如果两个 SDK 对同一份记录归一化得不一样，发布策略应当说明哪个行为可接受，而不是事后挑最方便的输出。

> SDKs often turn wire objects into convenient language types. That is useful, but a normalized object cannot prove what was received. ... Do not assume every difference is an SDK bug. The point is to make the transformation visible. ... Run the differential against every SDK and version you ship. If two SDKs normalize the same transcript differently, release policy should say which behavior is acceptable rather than choosing the most convenient output after the fact.

## Capture Proxy Evidence · 捕获代理证据

大多数生产 MCP 故障发生在不止一个进程之间。记录三个视图：

| 视图 | 最少证据 |
|---|---|
| 入口（Ingress） | 请求头、JSON-RPC 体、内容类型、认证后的路由、接收时间 |
| 源站（Origin） | 转发的头与体摘要、源站状态码、响应头与体 |
| 出口（Egress） | 客户端可见的状态码、头、体与发送时间 |

示例检测两种常见转换：

- 源站 HTTP 400 或 404 的 JSON-RPC 错误变成代理的通用 500
- 出口 JSON-RPC 体与源站体不同

为内容类型、`Accept`、压缩、请求作用域 SSE、缓存头与追踪关联加上部署特定的断言。策略允许时，捕获 TLS 终止的两侧。绝不要为了证明路径而记录凭据。

> Most production MCP failures occur across more than one process. Record three views ... an origin HTTP 400 or 404 JSON-RPC error becomes a generic proxy 500 ... Never log credentials just to prove the path.

## Redact Before Evidence Leaves Memory · 证据离开内存之前先脱敏

脱敏（redaction）是一致性运维的一部分，不是事后的清理工作。在序列化、哈希、日志、测试工件或故障上传之前应用它。

示例先把键名做大小写折叠、去掉分隔符再匹配，然后递归替换这些键下的值：`Authorization`、`Cookie`、`Set-Cookie`、`X-Api-Key`、`accessToken`、`clientSecret`、`registrationAccessToken`、`token`、`password`、`secret`、`api_key`。规范化与拒绝清单必须用同一形式，这样 camelCase、连字符、下划线与点分变体就无法绕开彼此的策略。生产采集器还应加上方法特定的参数策略，因为像 `query` 这样看似无害的键也可能包含个人或受监管数据。

对脱敏后的证据包做哈希。只有在特定调查需要时，才把原始捕获保存在经批准的短生命周期系统里。摘要证明是哪个脱敏包驱动了决策；它不揭示被移除的值。

> Redaction is part of conformance operations, not a later cleanup job. Apply it before serialization, hashing, logs, test artifacts, or failure uploads. ... Canonicalization and the denylist must use the same form so camelCase, hyphenated, underscored, and dotted variants cannot bypass one another's policy. ... A digest proves which redacted bundle drove the decision; it does not reveal the removed value.

## Make Health and Rollback Part of the Gate · 把健康与回滚纳入发布门禁

协议一致性是发布的必要条件，不是充分条件。一个一致的候选仍可能超时、泄漏内存或压垮依赖。

在发布前定义健康窗口：

- 最小样本数
- 最大错误率
- 最大延迟百分位
- 饱和度或资源上限
- 观察时长
- 与已准入基线的对比

也要在发布前定义回滚证据：

- 确切的上一个版本
- 准入证据摘要
- SHA-256 制品与描述符 pin
- 当前 Registry 状态
- 当前健康结果
- 路由恢复流程
- 由可信发布控制器身份对以上确切字段做的证明（attestation）

要求回滚目标在晋级之前就被验证且健康，而不是等候选失败之后。没有可用恢复路径的成功发布不算生产就绪。

如果候选失败而回滚目标缺这些证据，扣住流量，不要猜。「回滚到当时在那儿的东西」不是运营控制。

不要把就绪判断降级为真值检查，比如非空版本、`healthy: "yes"` 或任意的证据字符串。示例要求确切类型、active 状态、三个 SHA-256 摘要、可信签名者，以及对完整回滚载荷的合法 HMAC-SHA-256 证明。它的确定性演示密钥是非秘密夹具。生产中在发布边界注入受保护的密钥、KMS 验证结果或公钥证明验证器。

发布门禁还拒绝空的报文记录、SDK 差分或代理证据。每个来源都必须携带有效的证据摘要。绿色的健康窗口补不上一条从未被观察过的边界。

> Protocol conformance is necessary but not sufficient for release. ... Require that rollback target to be verified and healthy before promotion, not only after the candidate fails. A successful release without a usable recovery path is not production-ready. ... “Roll back to whatever was there” is not an operational control. ... The release gate also refuses empty transcript, SDK differential, or proxy evidence. Each source must carry valid evidence digests. A green health window cannot fill in a boundary that was never observed.

## Build It · 动手造

运行标准库测试框架：

```bash
cd phases/13-tools-and-protocols/31-mcp-conformance-versioning-and-operations
python3 code/main.py
```

演示恰好运行十五份黄金与反例记录——包括合法与畸形的补全（completion）结果——把一个原始结果与 SDK 视图对比，检查一个压扁了源站错误的代理，评估健康，认证回滚证据，并选中该目标。

预期形状：

```json
{
  "transcriptsPassed": 15,
  "transcriptsTotal": 15,
  "sdkDroppedFields": ["futureHint"],
  "proxyIssues": [
    "proxy collapsed a protocol error into HTTP 500",
    "proxy changed the origin JSON-RPC body"
  ],
  "releaseAction": "rollback",
  "evidenceDigest": "..."
}
```

按这个顺序读 `code/main.py`：

1. `validate_request()` 强制时代特定的请求与头部规则。
2. `validate_result()` 区分缺失的遗留判别符、合法的现代值、扩展与未知值。
3. `select_era()` 实现严格与有界回退策略。
4. `run_transcript()` 评估黄金与反例夹具。
5. `compare_sdk_view()` 暴露归一化差异。
6. `inspect_proxy()` 对比入口、源站与出口证据。
7. `redact()` 在证据哈希前移除明显秘密。
8. `rollback_evidence_ready()` 校验确切的 pin 字段与可信发布证明。
9. `ReleaseGate.evaluate()` 拼接非空的一致性、SDK、代理、健康与回滚证据。

> The demo runs exactly fifteen golden and negative transcripts, including valid and malformed completion results, compares a raw result with an SDK view, inspects a proxy that collapsed an origin error, evaluates health, authenticates the rollback evidence, and selects that target. ... Read `code/main.py` in this order ... `ReleaseGate.evaluate()` joins non-empty conformance, SDK, proxy, health, and rollback evidence.

## Use It · 实战用法

在四个点运行测试框架：

1. 每次实现变更时，用进程内测试适配器。
2. 对构建出的客户端与服务器二进制，走真实传输。
3. 在预发（staging）环境穿过已部署的代理或网关。
4. 金丝雀（canary）发布期间，带实时健康与回滚证据。

跨层保持同样的稳定用例名。`negative-header-body-mismatch` 在单元、端到端、代理和金丝雀报告里应当指同一个不变量。证据摘要会不同，因为边界变了；要求不该变。

夹具 schema 存进版本控制。脱敏后的运行证据存进你的发布系统。短生命周期的原始捕获只在事故访问控制之下保存。

> Run the harness at four points ... Keep the same stable case names across layers. `negative-header-body-mismatch` should mean the same invariant in unit, end-to-end, proxy, and canary reports. The evidence digest will differ because the boundary changed; the requirement should not. ... Store fixture schemas in version control. Store redacted run evidence in your release system. Store short-lived raw captures only under incident access controls.

## Interactive Lab · 交互实验

### Lab A: prove the era boundary · 实验 A：证明时代边界

从 `code` 目录打开 Python：

```bash
cd phases/13-tools-and-protocols/31-mcp-conformance-versioning-and-operations/code
python3 -q
```

运行：

```python
from main import *
validate_result({"tools": []}, "legacy")
validate_result({"tools": []}, "modern")
```

遗留调用推断出 `complete`。现代调用抛出 `ProtocolViolation`。现在测回退：

```python
select_era({"kind": "timeout"}, "fallback")
select_era(
    {"kind": "timeout"},
    "fallback",
    legacy_allowed=True,
    legacy_evidence={"kind": "initialize_success", "protocolVersion": LEGACY_VERSION},
)
select_era({"kind": "jsonrpc_error", "code": -32021}, "fallback")
```

第一个超时选择失败关闭（fail closed），因为沉默不是遗留证据。第二个调用选中遗留，只因配置允许它、并且观察到了合法的遗留初始化结果。可识别的缺失能力错误证明现代分支。

> The legacy call infers `complete`. The modern call raises `ProtocolViolation`. Now test fallback ... The first timeout fails closed because silence is not legacy evidence. The second call selects legacy only because configuration allows it and a valid legacy initialization result was observed. The recognized missing-capability error proves the modern branch.

### Lab B: additive field versus discriminator · 实验 B：增量字段对判别符

```python
validate_result({"resultType": "complete", "tools": [], "futureHint": True}, "modern")
validate_result({"resultType": "future_mode", "tools": []}, "modern")
```

第一个结果保留 `futureHint`。第二个被拒绝，因为生命周期判别符未知。

> The first result preserves `futureHint`. The second is rejected because the lifecycle discriminator is unknown.

### Lab C: inspect an SDK transformation · 实验 C：检查一次 SDK 转换

```python
compare_sdk_view(
    {"resultType": "complete", "tools": [], "futureHint": {"mode": "new"}},
    {"tools": []},
)
```

决定你的组件可以忽略 `futureHint` 还是必须转发它。把这个选择写进发布策略。不要悄悄抹掉差分。

> Decide whether your component may ignore `futureHint` or must forward it. Write that choice into release policy. Do not silently erase the differential.

### Lab D: repair the proxy · 实验 D：修复代理

修改演示交换，让出口保留源站状态与体。再跑一次 `python3 main.py`。代理问题应当消失，但 SDK 差分仍会阻止晋级。然后把 `futureHint` 包含进 SDK 视图，观察当每个证据源都通过时，动作变成 `promote`。

> Modify the demo exchange so egress preserves the origin status and body. Run `python3 main.py` again. The proxy issues should disappear, but the SDK differential still blocks promotion. Then include `futureHint` in the SDK view and observe the action change to `promote` when every evidence source passes.

## Practice Lab · 练习实验

给测试框架加请求作用域的 SSE 记录。

要求：

- 捕获响应状态、内容类型、有序的 SSE 事件和流终止。
- 证明每个 JSON-RPC 事件都有合法的时代特定结果或错误。
- 加一个反例：代理先缓冲完整流再转发。
- 加一个反例：SSE 事件的 JSON-RPC id 与请求不同。
- 写证据之前对事件数据脱敏。
- 把流时长、首事件延迟和事件数纳入健康窗口。
- 让发布门禁在流失败时只选择有证据支撑的回滚目标。

成功的含义：同一个用例直连与过代理都能跑，且报告指明是哪条确切边界改变了行为。

> Add request-scoped SSE transcripts to the harness. ... Success means the same case runs directly and through the proxy, with a report that identifies the exact boundary that changed behavior.

## Shipped Artifact · 交付物

本课交付 `outputs/skill-mcp-conformance-release-gate.md`。用它把一次服务器、客户端、网关或 SDK 变更变成带版本的一致性矩阵与发布决策。该工件要求原始网络证据、反例、显式时代选择、SDK 差分、代理证明、脱敏、健康阈值与回滚证据。

> This lesson ships `outputs/skill-mcp-conformance-release-gate.md`. Use it to turn a server, client, gateway, or SDK change into a versioned conformance matrix and release decision. The artifact requires raw wire evidence, negative cases, explicit era selection, SDK differentials, proxy proof, redaction, health thresholds, and rollback evidence.

## Verify It · 验收

运行演示与确定性套件：

```bash
cd phases/13-tools-and-protocols/31-mcp-conformance-versioning-and-operations
python3 code/main.py
python3 -m unittest discover -s code/tests -v
```

验证应当证明：

- 每一份内置黄金与反例记录都达到预期结果
- 现代请求要求确切的名字空间元数据键
- HTTP 头部名大小写不敏感匹配，编码的 `Mcp-Name` 值被精确解码
- 头体不匹配返回现代不匹配错误码
- 响应版本、ID、结果或错误互斥、错误形状与 HTTP 映射都被校验
- 方法特定的工具列表、任务与补全载荷要求被强制执行
- 每个观察到的 `HeaderMismatch` 都要求一个真实的 HTTP 400 JSON-RPC `-32020` 响应
- 裸 `Mcp-Name` 的空白被拒绝，而精确哨兵编码的空白可以往返
- 缺失 `resultType` 只在所选的遗留时代合法
- 增量字段在原始校验中存活，而未知结果类型失败
- 扩展结果类型要求其通告过的能力
- 可识别的现代错误绝不引发遗留回退
- 通知不产生 JSON-RPC 响应
- SDK 簿记移除与语义字段丢失被区分开
- 代理错误压扁被发现，凭据在 camelCase 与分隔符变体间递归脱敏
- 晋级要求非空的报文记录、SDK、代理与健康的运营证据
- 晋级与回滚都要求一个已认证、已固定、活跃且健康的回滚目标

> every included golden and negative transcript reaches its expected outcome ... every observed `HeaderMismatch` requires an actual HTTP 400 JSON-RPC `-32020` response ... notifications produce no JSON-RPC response ... promotion requires non-empty transcript, SDK, proxy, and healthy operational evidence ... promotion and rollback both require an authenticated, pinned, active, healthy rollback target

## Production Failure Modes · 生产故障模式

| 故障 | 弱测试报告什么 | 测试框架必须证明什么 |
|---|---|---|
| SDK 合成了缺失的判别符 | 「tools/list 通过了」 | 原始现代结果缺 `resultType`，无效 |
| 客户端在 `-32021` 后降级 | 「遗留重试成功了」 | 可识别的现代错误禁止回退 |
| 未知结果类型被当成完成 | 「响应解析成功」 | 未通告的生命周期判别符被拒绝 |
| 代理授权一个工具而源站执行另一个 | 「请求到达了服务器」 | 每一跳上 `Mcp-Name` 都等于体里的路由名 |
| 测试框架在读服务器响应前就抛异常 | 「头部不匹配测试通过」 | 捕获并验证 HTTP 400 与 JSON-RPC `-32020` 响应 |
| 代理把源站 400 变成通用 500 | 「上游错误」 | 源站与出口的状态码和 JSON-RPC 体被保留 |
| 通知中间件发出 `{result: null}` | 「处理器返回 None」 | 最终出口体为空且不存在 JSON-RPC 响应 |
| SDK 剥掉增量字段 | 「类型化对象匹配」 | 原始与归一化视图显示确切被丢的字段 |
| 故障工件泄漏 bearer 令牌 | 「调试包已上传」 | 在哈希、日志或上传之前完成脱敏 |
| 凭据键风格绕过脱敏 | 「拒绝清单里有 api_key」 | camelCase 与分隔符变体共用一个规范化拒绝清单形式 |
| 金丝雀没有样本却显得健康 | 「零错误」 | 强制最小样本数 |
| 回滚选中未知构建 | 「上一个部署已恢复」 | 目标版本、准入摘要、pin、状态与健康俱在 |

> SDK synthesizes a missing discriminator | “tools/list passed” | Raw modern result lacked `resultType` and is invalid ... Client downgrades after `-32021` | “legacy retry worked” | Recognized modern error forbids fallback ... Rollback selects an unknown build | “previous deployment restored” | Target version, admission digest, pins, status, and health are present

## Operational Rule · 运营规则

测试你发送的字节、每个中间设备转发的字节、每个 SDK 暴露的语义，以及运维在压力下会使用的证据。兼容性是一个显式分支。回滚是一个有证据支撑的发布动作。两者都不该是一个宽容解析器的意外副作用。

> Test the bytes you send, the bytes every intermediary forwards, the semantics each SDK exposes, and the evidence operations will use under pressure. Compatibility is an explicit branch. Rollback is an evidence-backed release action. Neither should be an accidental side effect of a permissive parser.

## Further Reading · 延伸阅读

- [MCP 2026-07-28 base protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic)
- [MCP version negotiation](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning)
- [MCP Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [Official MCP conformance project](https://github.com/modelcontextprotocol/conformance)
