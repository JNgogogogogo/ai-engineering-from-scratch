# MCP Authorization: CIMD, Issuer Binding, PKCE, and Step-Up · MCP 授权：CIMD、签发者绑定、PKCE 与逐步提权

> 一次远程 MCP 请求是无状态的，但它的授权不是匿名的。把每份凭据绑定到创建它的签发者（issuer），把每个令牌绑定到接收它的资源。

> A remote MCP request is stateless, but its authorization is not anonymous. Bind every credential to the issuer that created it and every token to the resource that receives it.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 13 · 09 (transports), Phase 13 · 15 (security)
**Time:** ~90 minutes

## Learning Objectives · 学习目标

- 通过受保护资源元数据（protected-resource metadata）发现授权服务器。
- 优先使用客户端 ID 元数据文档（Client ID Metadata Documents，CIMD），而不是已弃用的动态客户端注册（Dynamic Client Registration，DCR）。
- 在 DCR 兼容路径不可避免时，声明正确的 `application_type`。
- 校验授权响应的 `iss`，并按签发者隔离凭据。
- 使用 PKCE、资源指示符（resource indicators）、受众（audience）校验与增量 scope。
- 在没有协议会话的情况下发送已授权的 MCP 2026-07-28 请求。

> Discover authorization servers through protected-resource metadata.
> Prefer Client ID Metadata Documents over deprecated Dynamic Client Registration.
> Declare the correct `application_type` when a DCR compatibility path is unavoidable.
> Validate authorization response `iss` and isolate credentials by issuer.
> Use PKCE, resource indicators, audience validation, and incremental scopes.
> Send authorized MCP 2026-07-28 requests without protocol sessions.

## The Problem · 问题在哪

一台远程 MCP 服务器可能读取私人记录、写入外部系统，或触发高成本的工作。认证告诉它「是谁出示了凭据」。授权还必须回答：

- 是哪个授权服务器签发了这份凭据？
- 这个令牌是给哪个 MCP 资源的？
- 是哪个客户端和重定向 URI 完成了这个流程？
- 用户批准了哪些操作？
- 这个确切的请求是否仍然落在那次批准的范围之内？

2026-07-28 授权画像（authorization profile）强化了客户端注册与签发者处理。它优先使用客户端 ID 元数据文档，弃用动态客户端注册，要求 DCR 使用正确的 `application_type`，校验 RFC 9207 的签发者响应，并禁止凭据跨签发者复用。

这些规则是对无状态核心的补充。它们不会恢复核心握手或 `Mcp-Session-Id`。

> A remote MCP server may read private records, write external systems, or trigger costly work. Authentication tells it who presented a credential. Authorization must also answer which authorization server issued the credential, which MCP resource the token is for, and whether this exact request still fits that approval.
> The 2026-07-28 authorization profile hardens client enrollment and issuer handling. It prefers Client ID Metadata Documents, deprecates Dynamic Client Registration, requires the right `application_type` on DCR, validates RFC 9207 issuer responses, and forbids credential reuse across issuers.
> These rules complement the stateless core. They do not restore a core handshake or `Mcp-Session-Id`.

## The Concept · 概念

### Know the three roles · 认识三个角色

- **MCP 客户端（MCP client）：** 代表资源所有者发送请求。
- **MCP 资源服务器（resource server）：** 接受访问令牌并服务 MCP 端点。
- **授权服务器（authorization server）：** 认证资源所有者、收集同意并签发令牌。

资源服务器与授权服务器可以由同一方运营，但要保持它们的标识符与校验职责相互独立。

> An MCP client sends requests on behalf of a resource owner; an MCP resource server accepts the access token and serves the MCP endpoint; an authorization server authenticates the resource owner, collects consent, and issues tokens.
> The resource server and authorization server can be operated together, but keep their identifiers and validation responsibilities separate.

### Authorization applies to HTTP · 授权适用于 HTTP

MCP 授权规范适用于基于 HTTP 的传输。本地 stdio 服务器运行在进程与操作系统的信任边界之内。不要仅仅为了对称而给 stdio 添加一个假的浏览器 OAuth 流程。

对远程 Streamable HTTP，在每个请求的 `Authorization` 头里发送持有者令牌（bearer token）。绝不把它放进 URL。

> The MCP authorization specification applies to HTTP-based transports. A local stdio server runs under the process and operating-system trust boundary. Do not add a fake browser OAuth flow to stdio merely for symmetry.
> For remote Streamable HTTP, send the bearer token in the `Authorization` header on every request. Never place it in the URL.

### Start with protected-resource metadata · 从受保护资源元数据开始

资源服务器发布 RFC 9728 元数据：

```json
{
  "resource": "https://notes.example.com/mcp",
  "authorization_servers": ["https://auth.example.com"],
  "scopes_supported": ["notes:delete", "notes:read", "notes:write"]
}
```

客户端从 MCP 资源 URL 出发，抓取这个文档，选择一个被宣告的授权服务器，然后再抓取那台服务器的 OAuth 或 OpenID Connect 元数据。

构造 RFC 9728 的 well-known URL 时要保留资源路径。对资源 `https://notes.example.com/mcp`，本课使用 `https://notes.example.com/.well-known/oauth-protected-resource/mcp`。丢掉 `/mcp` 后缀可能选到同一源上另一个受保护资源的元数据。

不要从主机名猜测授权服务器。不要跟随从一份未校验的错误正文里发现的签发者。为「客户端愿意信任哪些签发者」保留一条策略。

> The client starts from the MCP resource URL, fetches this document, selects an advertised authorization server, and then fetches that server's OAuth or OpenID Connect metadata.
> Preserve the resource path when constructing the RFC 9728 well-known URL... Dropping the `/mcp` suffix can select metadata for a different protected resource on the same origin.
> Do not guess the authorization server from a hostname. Do not follow an issuer discovered from an unvalidated error body.

### Verify authorization server metadata · 校验授权服务器元数据

元数据应暴露端点与受支持的控制项：

```json
{
  "issuer": "https://auth.example.com",
  "authorization_endpoint": "https://auth.example.com/authorize",
  "token_endpoint": "https://auth.example.com/token",
  "code_challenge_methods_supported": ["S256"],
  "authorization_response_iss_parameter_supported": true,
  "client_id_metadata_document_supported": true
}
```

PKCE 要求 S256。记录确切的签发者字符串。这个确切值将成为注册与令牌存储的键。

> The metadata should expose endpoints and supported controls.
> Require S256 for PKCE. Record the exact issuer string. That exact value becomes the key for registration and token storage.

### Follow the registration priority · 遵循注册优先级

当客户端与所选签发者已有显式关系时，使用预注册的客户端信息。否则，当授权服务器宣告支持时，优先使用客户端 ID 元数据文档。仅在两者都不可用时，才把 DCR 当作已弃用的兼容回退，然后在其机制都不可用时提示输入客户端信息。

> Use pre-registered client information when the client already has an explicit relationship with the selected issuer. Otherwise prefer Client ID Metadata Documents when the authorization server advertises support. Use DCR only as the deprecated compatibility fallback, then prompt for client information if none of those mechanisms is available.

### Prefer Client ID Metadata Documents · 优先使用客户端 ID 元数据文档

客户端 ID 元数据文档（CIMD）给授权服务器一个 HTTPS URL，它既是客户端标识符，也是其元数据的位置：

```json
{
  "client_id": "https://client.example.com/oauth/metadata.json",
  "client_name": "Notes desktop client",
  "application_type": "native",
  "redirect_uris": ["http://127.0.0.1:8765/callback"],
  "grant_types": ["authorization_code"],
  "response_types": ["code"]
}
```

授权服务器抓取并校验该文档。`client_id` 必须是带路径的 HTTPS URL，且文档内的取值必须与该 URL 完全相等。必需的文档字段是 `client_id`、`client_name` 和 `redirect_uris`。`application_type` 出现在本例中，但不是 CIMD 的要求。它新出现的强制使用场景特指 DCR 路径。

把抓取该文档视为对 SSRF 敏感的操作。解析并校验目的地，拒绝环回（loopback）、私有、链路本地（link-local）以及其他被禁止的地址，在重定向和 DNS 变化后重新检查，限制重定向次数、字节数与时间，要求 JSON，并且只按已校验的 HTTP 缓存控制来缓存。把 `client_name` 与其他显示字段当作不可信文本。

CIMD 移除了「为每一次初次接触铸造一个新动态标识符」的需要。它没有移除重定向 URI 校验、签发者策略或用户同意。

> A Client ID Metadata Document gives the authorization server an HTTPS URL that is both the client identifier and the location of its metadata.
> The `client_id` must be an HTTPS URL with a path, and the value inside the document must equal that URL exactly. The required document fields are `client_id`, `client_name`, and `redirect_uris`.
> Treat fetching the document as an SSRF-sensitive operation.
> CIMD removes the need to mint a fresh dynamic identifier for every first contact. It does not remove redirect URI validation, issuer policy, or user consent.

### DCR is a compatibility path · DCR 是一条兼容路径

动态客户端注册（DCR）对较旧的授权服务器仍然可用，但对新的 MCP 实现已弃用。

使用 DCR 时，声明 `application_type`：

```json
{
  "client_name": "Notes desktop client",
  "application_type": "native",
  "redirect_uris": ["http://127.0.0.1:8765/callback"],
  "grant_types": ["authorization_code"],
  "response_types": ["code"]
}
```

- 桌面、移动、命令行与环回客户端使用 `native`。
- 远程托管的浏览器应用使用 `web` 和远程 HTTPS 重定向。

省略该字段可能在 OpenID Connect 注册实现里默认成 `web`，让一次合法的环回重定向失败。

把 DCR 代码藏在一个显式的回退决策之后。不要在任意的 CIMD 校验失败后静默回退。那会把一次安全失败变成一条更弱的注册路径。

> Dynamic Client Registration remains available for older authorization servers, but it is deprecated for new MCP implementations.
> Desktop, mobile, command-line, and loopback clients use `native`. Remotely hosted browser applications use `web` and remote HTTPS redirects.
> Omitting the field can default to `web` in an OpenID Connect registration implementation and make a legitimate loopback redirect fail.
> Keep DCR code behind an explicit fallback decision. Do not silently fall back after an arbitrary CIMD validation failure.

### Bind credentials to the issuer · 把凭据绑定到签发者

把签发者铸造的注册材料存储在确切的签发者之下：

```text
issuer_credentials[issuer] = pre_registered_or_dcr_client
tokens[(issuer, resource)] = access_token
```

如果受保护资源发现从 `https://auth-one.example` 变成 `https://auth-two.example`，重新评估信任。绝不把第一个签发者的客户端密钥、DCR 客户端 id、注册访问令牌、刷新令牌或访问令牌发给第二个。预注册与 DCR 客户端必须使用为新签发者签发的凭据。

CIMD 客户端 id 则不同：它是一个自托管的 HTTPS URL，不是授权服务器铸造的凭据。同一个 CIMD URL 是可移植的：一个新的受信签发者可以抓取并校验该文档，而无需 DCR 重新注册。授权响应与令牌仍然要在新签发者之下校验并存储。

> Store issuer-minted enrollment material under the exact issuer.
> Never send the first issuer's client secret, DCR client id, registration access token, refresh token, or access token to the second.
> A CIMD client id is different because it is a self-hosted HTTPS URL, not a credential minted by an authorization server. The same CIMD URL is portable... Authorization responses and tokens are still validated and stored under the new issuer.

### Authorization code with PKCE · 授权码 + PKCE

交互式流程是：

1. 生成一个高熵的 `code_verifier`。
2. 派生出 S256 的 `code_challenge`。
3. 发送带精确 `client_id`、`redirect_uri`、`scope`、`code_challenge` 和 `resource` 的授权请求。
4. 接收一个包含 `code` 以及（如果提供）`iss` 的授权响应。
5. 在使用任何响应字段之前，对照记录的确切签发者校验 `iss`。
6. 用 `code_verifier`、同一个重定向 URI 和同一个 `resource` 兑换 code。
7. 把结果令牌存储在 `(issuer, resource)` 之下。

RFC 8707 的 `resource` 参数同时出现在授权请求和令牌请求中。它标识规范化的 MCP 服务器 URI。

> Generate a high-entropy `code_verifier`. Derive the S256 `code_challenge`.
> Validate `iss` against the exact recorded issuer before using any response field.
> The `resource` parameter from RFC 8707 appears in both authorization and token requests. It identifies the canonical MCP server URI.

### Validate `iss` exactly · 严格校验 `iss`

RFC 9207 防止来自一个签发者的授权响应被混同于来自另一个签发者的响应。

当 `iss` 存在时，把它与记录的签发者比较，不做大小写折叠、不去尾部斜杠、不去默认端口、也不做百分号编码规范化。不匹配时，不要对该 code 采取任何行动，甚至不要显示来自该响应的、攻击者可控的错误细节。

包含 `iss` 的授权服务器会宣告 `authorization_response_iss_parameter_supported: true`。即使这个宣告缺失，当代客户端仍然校验存在的 `iss`。

> RFC 9207 prevents an authorization response from one issuer being confused with a response from another.
> When `iss` is present, compare it to the recorded issuer without case folding, trailing-slash changes, default-port removal, or percent-encoding normalization.
> Current clients still validate a present `iss` even when that advertisement is missing.

### Validate audience at the MCP server · 在 MCP 服务器校验受众

资源服务器只接受为它自己签发的令牌：

```text
token.issuer == configured_authorization_server
token.audience == canonical_mcp_resource
```

无效、过期、错误签发者或错误受众的令牌收到 401。MCP 服务器绝不能接受或转发一个本属于其他服务的令牌。

> The resource server accepts only tokens issued for itself.
> Invalid, expired, wrong-issuer, or wrong-audience tokens receive 401. The MCP server must not accept or transit a token meant for another service.

### Request the smallest current scope · 请求当前所需的最小 scope

从现在需要的 scope 开始。如果稍后的工具需要更多，服务器返回 403 和一个权威的 scope 质询：

```text
WWW-Authenticate: Bearer error="insufficient_scope",
  scope="notes:delete",
  resource_metadata="https://notes.example.com/.well-known/oauth-protected-resource/mcp"
```

客户端解释新权限，取得同意，用合并后的 scope 集合执行一次新的授权流程，然后用一个新的 JSON-RPC id 重试该 MCP 请求。

不要假设被质询的 scope 是 `scopes_supported` 的子集。对当前操作来说，质询才是权威。

> Start with the scope needed now. If a later tool requires more, the server returns 403 with an authoritative scope challenge.
> The client explains the new permission, obtains consent, performs a new authorization flow with the combined scope set, and retries the MCP request with a new JSON-RPC id.
> Do not assume the challenged scope is a subset of `scopes_supported`. The challenge is authoritative for the current operation.

### Authorization and the stateless MCP wire · 授权与无状态的 MCP 线路

一次已授权的工具调用仍然携带完整的当前请求信封：

```text
POST /mcp
Authorization: Bearer <access-token>
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: notes.delete
```

```json
{
  "jsonrpc": "2.0",
  "id": 12,
  "method": "tools/call",
  "params": {
    "name": "notes.delete",
    "arguments": {"id": "note-7"},
    "_meta": {
      "io.modelcontextprotocol/protocolVersion": "2026-07-28",
      "io.modelcontextprotocol/clientCapabilities": {},
      "io.modelcontextprotocol/clientInfo": {
        "name": "oauth-lesson-client",
        "version": "1.0.0"
      }
    }
  }
}
```

令牌授权主体。请求元数据协商协议行为。两者互不替代。

按固定顺序校验线路：JSON-RPC 与元数据类型、头与正文相等性，然后是协议支持。路由或版本头不匹配返回 HTTP 400 加 `-32020`。如果头与正文一致但版本不受支持，返回 HTTP 400 加 `-32022`，且 `data` 恰为 `{"supported":["2026-07-28"],"requested":"<actual>"}`。未知方法返回 HTTP 404 加 `-32601`。

每个请求错误——包括 401 无效令牌与 403 scope 不足——都是一个带原始请求 `id` 的 JSON-RPC 错误信封。结构化恢复信息属于可选的错误 `data`；`WWW-Authenticate` 仍然是 HTTP 响应头。通知没有 `id`，所以它收不到 JSON-RPC 正文。一条被接受的 HTTP 通知返回 202 加空正文。

服务器实现 `server/discover` 并宣告工具，所以它也实现强制的 `tools/list` 方法。它的工具描述符有稳定的名称、描述和对象根的 `inputSchema` 取值。列表是确定性的，返回 `resultType`、服务器身份元数据、有界的 `ttlMs` 和 `cacheScope`。发现与一个用户无关的工具列表可以在授权之前就可用。当其中任何一项随主体变化时，应用常规策略与私有缓存。

> The token authorizes the principal. The request metadata negotiates protocol behavior. Neither substitutes for the other.
> Validate the wire in a fixed order: JSON-RPC and metadata types, header and body equality, then protocol support.
> Every request error, including 401 invalid token and 403 insufficient scope, is a JSON-RPC error envelope with the original request `id`.
> Discovery and a user-independent tool list can be available before authorization. Apply normal policy and private caching if either varies by principal.

### No token passthrough · 不做令牌透传

MCP 服务器绝不能把客户端的 MCP 访问令牌转发给下游 API。为下游获取一个带正确受众的独立令牌，或使用一个显式的令牌交换（token exchange）设计。只有当各服务都拒绝为别人铸造的令牌时，受众校验才成立。

> An MCP server must not forward the client's MCP access token to a downstream API. Obtain a separate downstream token with the right audience or use an explicit token-exchange design.
> Audience validation only works when services refuse tokens minted for someone else.

### Refresh tokens · 刷新令牌

刷新令牌是可选的。签发时，要保密存储并按签发者与资源作键。不要假设它们存在。当授权服务器支持轮换时进行轮换，并检测已失效值的复用。

> Refresh tokens are optional. When issued, store them confidentially and key them by issuer and resource. Do not assume they exist.
> Rotate them when the authorization server supports rotation and detect reuse of invalidated values.

```figure
t3-scope-stepup
```

## Build It · 动手造

`code/main.py` 是一个进程内的协议与授权模拟器。它实现受保护资源发现、授权服务器元数据、CIMD 注册、按版本门控的 DCR 回退、application type 检查、PKCE、签发者校验、资源绑定令牌、scope 逐步提权（step-up）、`server/discover`、`tools/list`，以及一次无状态工具请求。

这个模型接收已解析的请求正文与路由头。它不是一个完整的 HTTP 适配器，也不解析 `Content-Type` 或 `Accept`。把它接到第 09 课的 Streamable HTTP 适配器上，后者要求 `Content-Type: application/json` 以及同时包含 `application/json` 和 `text/event-stream` 的 `Accept` 值。

运行它：

```bash
cd phases/13-tools-and-protocols/16-mcp-security-oauth-2-1
python3 code/main.py
python3 -m unittest discover code/tests -v
```

输出依次展示发现、CIMD 注册、一次普通读取、两次独立的 scope 逐步提权，以及按签发者作键的凭据存储。

> `code/main.py` is an in-process protocol and authorization simulator. It implements protected-resource discovery, authorization server metadata, CIMD enrollment, version-gated DCR fallback, application type checks, PKCE, issuer validation, resource-bound tokens, scope step-up, `server/discover`, `tools/list`, and a stateless tool request.
> The output shows discovery first, CIMD enrollment, an ordinary read, two separate scope step-ups, and issuer-keyed credential storage.

## Use It · 实战用法

把模拟器对象映射到生产组件：

- `ResourceServer.protected_resource_metadata` 变成 RFC 9728 端点。
- `AuthorizationServer.metadata` 变成 RFC 8414 或 OpenID Connect 发现。
- `Client.enroll` 变成 CIMD 解析外加一个显式的 DCR 兼容分支。
- 签发者铸造的客户端凭据与 `tokens_by_issuer_resource` 变成加密记录。CIMD URL 可以保持可移植，而其授权结果保持按签发者绑定。
- `ResourceServer.handle` 变成中间件：在分发前校验当前 MCP 头、令牌与工具 scope，同时把每个请求错误放进匹配的 JSON-RPC 信封。

> Map the simulator objects to production components: `ResourceServer.protected_resource_metadata` becomes the RFC 9728 endpoint; `AuthorizationServer.metadata` becomes RFC 8414 or OpenID Connect discovery; `Client.enroll` becomes CIMD resolution plus an explicit DCR compatibility branch.
> `ResourceServer.handle` becomes middleware that validates current MCP headers, token, and tool scope before dispatch while keeping every request error in a matching JSON-RPC envelope.

## Ship It · 交付

本课交付 `outputs/skill-oauth-scope-planner.md`。它现在可以设计注册优先级、按签发者绑定的凭据存储、application type、PKCE、资源指示符、scope 质询，以及现行的无状态请求边界。

> This lesson ships `outputs/skill-oauth-scope-planner.md`. It now designs enrollment priority, issuer-bound credential storage, application type, PKCE, resource indicators, scope challenges, and the current stateless request boundary.

## Exercises · 练习

1. 添加刷新令牌轮换，并拒绝复用上一次的刷新令牌。
2. 添加一个签发者允许列表。当签发者变化时，只复用可移植的 CIMD URL；拒绝此前所有由签发者铸造的凭据与令牌。
3. 给授权码添加过期时间，并确认一次迟到的兑换会失败。
4. 构建一个使用远程 HTTPS 重定向的 web 客户端变体，并把它的 DCR 元数据与 native 客户端做比较。
5. 在同一个签发者下添加第二个资源。确认它的访问令牌不能用在第一个资源上。

## Key Terms · 术语表

| 术语 | 含义 |
|------|---------|
| Protected-resource metadata（受保护资源元数据） | 标识资源与授权服务器的 RFC 9728 文档 |
| CIMD | 一种 HTTPS 元数据文档，其 URL 就是 OAuth 客户端标识符 |
| DCR | 为兼容性保留、但已弃用的动态客户端注册 |
| `application_type` | `native` 或 `web`，用于校验重定向 URI 规则 |
| PKCE | 保护被截获授权码的 verifier 与 S256 challenge |
| `iss` | RFC 9207 授权响应中的签发者标识符 |
| Resource indicator（资源指示符） | RFC 8707 参数，把令牌请求绑定到一个 MCP 资源 |
| Audience（受众） | 令牌对其有效的资源 |
| Step-up（逐步提权） | 为当前操作所需的额外 scope 做新的同意与令牌签发 |
| Issuer-bound credentials（按签发者绑定的凭据） | 按确切授权服务器签发者隔离的注册与令牌记录 |

## Further Reading · 延伸阅读

- [MCP 2026-07-28 authorization specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) —— MCP 2026-07-28 授权规范
- [RFC 9728: OAuth 2.0 Protected Resource Metadata](https://www.rfc-editor.org/rfc/rfc9728) —— OAuth 2.0 受保护资源元数据
- [RFC 8707: Resource Indicators for OAuth 2.0](https://www.rfc-editor.org/rfc/rfc8707) —— OAuth 2.0 资源指示符
- [RFC 9207: OAuth 2.0 Authorization Server Issuer Identification](https://www.rfc-editor.org/rfc/rfc9207) —— OAuth 2.0 授权服务器签发者标识
- [OAuth Client ID Metadata Document draft](https://datatracker.ietf.org/doc/draft-ietf-oauth-client-id-metadata-document/) —— OAuth 客户端 ID 元数据文档草案
