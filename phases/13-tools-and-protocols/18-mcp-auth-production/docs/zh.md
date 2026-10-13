# MCP Auth in Production: Issuer-Bound Enrollment and Tokens · 生产环境的 MCP 认证：签发者绑定的注册与令牌

> 第 16 课搭好了 OAuth 2.1 状态机。本课为 MCP 2026-07-28 加固它的生产边界：客户端 ID 元数据文档（Client ID Metadata Document）优先，已废弃的动态注册（dynamic registration）仅作兼容保留，授权响应的签发者校验，按签发者键控的客户端凭证，JWKS 刷新，以及每个无状态请求上的受众固定（audience-pinned）令牌。
>
> Lesson 16 built the OAuth 2.1 state machine. This lesson hardens its production boundaries for MCP 2026-07-28: Client ID Metadata Documents first, deprecated dynamic registration only for compatibility, authorization-response issuer validation, issuer-keyed client credentials, JWKS refresh, and audience-pinned tokens on every stateless request.
>
> **Spec note (2026-07-28):** Dynamic Client Registration is deprecated in favor of Client ID Metadata Documents. DCR remains a compatibility mechanism. When it is used, the client declares the correct `application_type`. A client validates a present RFC 9207 `iss` value and never reuses credentials across authorization-server issuers.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 13 · 16 (OAuth 2.1 state machine), Phase 13 · 17 (gateways)
**Time:** ~90 minutes

## Learning Objectives · 学习目标

- 通过 RFC 8414 元数据发现授权服务器（authorization server），并验证该契约
- 通过客户端 ID 元数据文档（Client ID Metadata Document）完成注册，并把已废弃的 DCR 隔离为后备路径
- 校验 RFC 9207 `iss`，按授权服务器签发者键控注册，并按「签发者+资源」键控资源绑定令牌
- 按计划缓存并刷新 JWKS 密钥，让签名验证挺过密钥轮换（key roll-over）
- 用 RFC 8707 资源指示符（resource indicator）把令牌固定到单一 MCP 资源，拒绝「混淆代理」式复用（confused-deputy reuse）
- 在 JWT 校验与令牌内省（introspection）之间做选择，定义撤销新鲜度，并在身份依赖不可用时安全失败
- 分离授权服务器、资源服务器与客户端，让各自只强制执行属于自己的检查
- 按部署清单审计一个授权服务器，拒绝不安全的注册或令牌复用

> Discover an authorization server through RFC 8414 metadata and verify the contract.
> Enroll through a Client ID Metadata Document and isolate deprecated DCR as a fallback.
> Validate RFC 9207 `iss`, key registrations by authorization-server issuer, and key resource-bound tokens by issuer plus resource.
> Cache and refresh JWKS keys on a schedule so signature verification survives key roll-over.
> Pin tokens to a single MCP resource using RFC 8707 resource indicators and refuse confused-deputy reuse.
> Choose JWT validation or token introspection, define revocation freshness, and fail safely when identity dependencies are unavailable.
> Separate the authorization server, resource server, and client so each enforces only its own checks.
> Audit an authorization server against a deployment checklist and refuse unsafe enrollment or token reuse.

## The Problem · 问题在哪

第 16 课的模拟器在内存里运行 OAuth 2.1。生产环境有三个只在内存里跑的模拟器看不到的运维缺口。

第一个缺口是注册与凭证隔离。一个真实的组织可能运行数百个 MCP 服务器和数千个 MCP 客户端。2026-07-28 修订版倾向于**客户端 ID 元数据文档（Client ID Metadata Document）**：客户端用一个自己控制的、带路径的 HTTPS URL 作为标识符，授权服务器（authorization server）反过来拉取这份元数据。RFC 7591 动态注册（dynamic registration）只作为已废弃的兼容路径保留。当 DCR 不可避免时，请求要声明正确的 `application_type`。客户端把注册信息按授权服务器签发者（issuer）存储，把访问令牌按 `(issuer, resource)` 对存储。签发者变了就意味着要重新注册，资源不同就意味着要一个单独绑定受众的令牌。

第二个缺口是密钥轮换。JWT 校验依赖授权服务器的签名密钥，它们以 JSON Web 密钥集（JWKS）发布。授权服务器按计划轮换这些密钥（常常每小时一次，事件响应时可能更快）。一个只在启动时抓取一次 JWKS 的 MCP 服务器会一直校验正常，直到轮换窗口来临——然后每个请求都失败，直到重启。生产环境把 JWKS 接成一个带刷新任务的缓存值：刷新任务在上一次密钥过期前覆写缓存，另加一条缓存未命中时的回退抓取路径，用来处理「令牌由比缓存更新的密钥签名」的情况。

第三个缺口是受众绑定（audience binding）。第 16 课介绍了 RFC 8707 资源指示符。在生产环境里，这个指示符变成对每个请求的硬性声明检查。MCP 服务器把 `token.aud` 与自己的规范资源 URL 比较，不匹配就以 HTTP 401 拒绝。这是防御「上游 MCP 服务器（或持有本属于某服务器的令牌的恶意客户端）在同一信任网络内把令牌重放给另一个服务器」的唯一手段。

本课把每个缺口映射到接口层的一个具体部件。元数据文档是一个 HTTP 端点。JWKS 缓存刷新是一个定时任务加一个键值缓存。JWT 校验是资源服务器在分发任何工具之前运行的一个例程。把三种角色分开，每个角色只强制执行属于自己的检查：授权服务器签发并轮换密钥，资源服务器缓存并校验，客户端发现并注册。

> The first gap is enrollment and credential isolation. ... The client stores registrations under the authorization-server issuer and access tokens under the `(issuer, resource)` pair. A changed issuer means a new enrollment, and a different resource means a separately audience-bound token.
> The second gap is key rotation. ... An MCP server that fetches JWKS once at boot validates fine until the rotation window — then every request fails until restart.
> The third gap is audience binding. ... The MCP server compares `token.aud` against its own canonical resource URL and rejects mismatches with HTTP 401. This is the only defense against an upstream MCP server (or a malicious client holding a token meant for one server) replaying that token against another server in the same trust mesh.
> Keep the three roles separate and each one enforces only the checks it owns: the authorization server issues and rotates keys, the resource server caches and validates, the client discovers and enrolls.

## Scope: Production Enforcement After Lesson 16 · 范围：第 16 课之后的生产级强制执行

[Lesson 16: MCP Security with OAuth 2.1](../../16-mcp-security-oauth-2-1/docs/en.md) 负责授权码状态机、PKCE、受保护资源发现、资源指示符和作用域决策。本课不定义第二条 OAuth 流程。它从这些契约已经存在之后开始，追问一个已部署的资源服务器如何在密钥轮换、不透明令牌校验、撤销、依赖故障、发布与事件响应期间持续强制执行它们。

生产边界更窄、更偏运维：

- JWT 路径在每个请求上校验固定的签发者、算法、签名密钥、受众、时间声明与作用域，同时安全地刷新 JWKS。
- 不透明令牌（opaque token）路径调用签发者经过认证的内省（introspection）端点，并校验返回的 active 状态、受众或资源、过期时间、主题与作用域。
- 撤销策略定义一个凭证必须多快停止生效，以及哪个缓存可以延迟这个事实。
- 失败策略决定当发现、JWKS、内省或撤销基础设施不可用时会发生什么。
- 证据记录是哪些签发者元数据、密钥集或内省响应、令牌声明、策略版本与拒绝原因驱动了结果，同时不存储令牌。

这个区分让课程可以组合。第 16 课证明流程本身。第 18 课证明令牌在到达真实的 MCP 请求路径之后仍然可信，或者被拒绝。

> This lesson does not define a second OAuth flow. It starts after those contracts exist and asks how a deployed resource server keeps enforcing them during key rotation, opaque-token validation, revocation, dependency failure, rollout, and incident response.
> This distinction keeps the lessons composable. Lesson 16 proves the flow. Lesson 18 proves that a token remains trustworthy, or is refused, after it reaches a real MCP request path.

## The Concept · 概念

### RFC 8414 — OAuth Authorization Server Metadata · RFC 8414 — OAuth 授权服务器元数据

`/.well-known/oauth-authorization-server` 处的文档描述了客户端需要的一切：

```json
{
  "issuer": "https://auth.example.com",
  "authorization_endpoint": "https://auth.example.com/authorize",
  "token_endpoint": "https://auth.example.com/token",
  "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
  "client_id_metadata_document_supported": true,
  "registration_endpoint": "https://auth.example.com/register",
  "authorization_response_iss_parameter_supported": true,
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "code_challenge_methods_supported": ["S256"],
  "scopes_supported": ["mcp:tools.read", "mcp:tools.invoke"],
  "token_endpoint_auth_methods_supported": ["none", "private_key_jwt"]
}
```

拿到一个 MCP 资源 URL 的客户端会链式发现（chained discovery）：RFC 9728 的 `oauth-protected-resource`（资源服务器的文档）指名签发者，然后 `oauth-authorization-server`（本 RFC）指名每个端点。客户端绝不硬编码授权 URL。

对带路径的资源标识符，要把 well-known 段插入到该路径之前。例如 `https://mcp.example.com/team/server` 的受保护资源元数据解析在 `https://mcp.example.com/.well-known/oauth-protected-resource/team/server`。把 `/.well-known/...` 追加在资源路径之后是错误的。

在信任一个 IdP 用于 MCP 之前，你要验证的契约：

- `code_challenge_methods_supported` 包含 `S256`（PKCE，RFC 7636）。规范是明确的：如果这个字段**缺席**，授权服务器不支持 PKCE，客户端**必须（MUST）**拒绝继续。
- `grant_types_supported` 包含 `authorization_code`，并拒绝 `password` 和 `implicit`。
- 至少有一条注册途径可用：`client_id_metadata_document_supported: true`（CIMD，首选）、一个预注册的客户端，或 `registration_endpoint`（已废弃的 RFC 7591 兼容路径）。
- 如果 `authorization_response_iss_parameter_supported` 为 true，客户端要求返回的 RFC 9207 `iss`，并把它与重定向前记录的签发者做精确比较。
- 对 OAuth 2.1 而言，`response_types_supported` 恰好是 `["code"]`。

如果 `S256` 缺失，MCP 服务器拒绝针对这个 IdP 部署——PKCE 没有降级模式。如果*两条*注册途径都没有公告，而你也没有预注册的 `client_id`，那你也无法注册；这是部署清单错了，不是代码错了。

> A client given an MCP resource URL chains discovery: `oauth-protected-resource` from RFC 9728 (the resource server's document) names the issuer, then `oauth-authorization-server` (this RFC) names every endpoint. The client never hard-codes an authorization URL.
> `code_challenge_methods_supported` includes `S256` (PKCE per RFC 7636). The spec is explicit: if this field is **absent**, the authorization server does not support PKCE and the client **MUST** refuse to proceed.
> If `S256` is missing, the MCP server refuses to deploy against this IdP — there is no degraded mode for PKCE.

### RFC 9728 (recap) — Protected Resource Metadata · RFC 9728（回顾）— 受保护资源元数据

第 16 课讲过 RFC 9728。生产环境中的增量是：这份文档是客户端寻找「*这个* MCP 服务器信任哪些授权服务器」的唯一地方。一个 MCP 服务器可以接受来自多个 IdP 的令牌（一个给员工，一个给合作伙伴）。RFC 9728 声明这个集合；RFC 8414 文档化每个 IdP 支持什么。

```json
{
  "resource": "https://notes.example.com",
  "authorization_servers": ["https://auth.example.com", "https://partners.example.com"],
  "scopes_supported": ["mcp:tools.invoke"],
  "bearer_methods_supported": ["header"],
  "resource_documentation": "https://notes.example.com/docs"
}
```

> The delta in production: this document is the only place a client looks to find the authorization servers trusted by *this* MCP server. A single MCP server may accept tokens from multiple IdPs (one for staff, one for partners). RFC 9728 declares that set; RFC 8414 documents what each IdP supports.

### Client ID Metadata Documents (the recommended default) · 客户端 ID 元数据文档（推荐的默认方式）

CIMD 把注册从*推送*反转为*拉取*。客户端不再请求授权服务器铸造一个 `client_id`，而是用一个自己控制的 HTTPS URL **作为**它的 `client_id`。这个 URL 解析为一份 JSON 元数据文档；授权服务器在 OAuth 流程中按需抓取它。信任扎根在 DNS 上：如果服务器运营者信任 `app.example.com`，它就信任由 `https://app.example.com/client.json` 提供的客户端。没有注册往返，没有会耗尽的 `client_id` 命名空间，也没有需要保持同步的每服务器状态。

客户端托管的元数据文档：

```json
{
  "client_id": "https://app.example.com/oauth/client.json",
  "client_name": "Example MCP Client",
  "client_uri": "https://app.example.com",
  "application_type": "native",
  "redirect_uris": ["http://127.0.0.1:7333/callback", "http://localhost:7333/callback"],
  "grant_types": ["authorization_code", "refresh_token"],
  "response_types": ["code"],
  "token_endpoint_auth_method": "none"
}
```

文档中的 `client_id` 值**必须（MUST）**等于提供它的那个 URL（授权服务器会验证这一点；不匹配即拒绝）。授权服务器在自己的 RFC 8414 元数据里用 `client_id_metadata_document_supported: true` 公告支持。

对当前的 CIMD 契约而言，`client_id`、`client_name` 和一个非空的 `redirect_uris` 数组是必需的。客户端标识符是带路径的绝对 HTTPS URL。`application_type` 可以包含，但它不是 CIMD 的必填字段。不要把 DCR 对 `application_type` 的要求复制到首选的 CIMD 路径上。

规范直言不讳的两个安全事实：

- **SSRF。** 授权服务器要抓取一个攻击者提供的 URL。它必须防御服务器端请求伪造（不允许抓取内部/管理端点）。
- **localhost 冒充。** 单靠 CIMD 无法阻止本地攻击者认领一个合法客户端的元数据 URL 并绑定任意 `localhost` 重定向。授权服务器**必须（MUST）**在同意页清晰展示重定向 URI 的主机名，并且**应该（SHOULD）**对仅有 `localhost` 的重定向发出警告。

因为 CIMD 不需要服务器端状态，所以不存在 DCR 那种需要搭建的注册机构。客户端一侧是只读的：从一个静态 HTTPS 端点提供你的元数据文档，让授权服务器来拉取。

如果授权服务器运营者已经预置了客户端标识符，先使用那个按签发者作用域的注册，再考虑自动注册。否则首选 CIMD。只有当签发者既不能用预注册也不能用 CIMD 时，才使用已废弃的 DCR。

> CIMD inverts registration from *push* to *pull*. ... Trust is rooted in DNS: if the server operator trusts `app.example.com`, it trusts the client served from `https://app.example.com/client.json`. No registration round-trip, no `client_id` namespace to exhaust, no per-server state to keep in sync.
> The `client_id` value in the document **MUST** equal the URL it is served from (the authorization server verifies this; mismatches are rejected).
> **SSRF.** The authorization server fetches an attacker-supplied URL. It must defend against server-side request forgery (no fetches to internal/admin endpoints).
> **localhost impersonation.** CIMD alone cannot stop a local attacker from claiming a legitimate client's metadata URL and binding any `localhost` redirect. The authorization server **MUST** clearly display the redirect URI hostname during consent and **SHOULD** warn on `localhost`-only redirects.

### RFC 7591: deprecated compatibility enrollment · RFC 7591：已废弃的兼容性注册

DCR 在 2026-07-28 修订版中已废弃。只给那些无法消费 CIMD、且预注册不切实际的授权服务器保留它。一个兼容性客户端发送：

```json
POST /register
Content-Type: application/json

{
  "application_type": "native",
  "redirect_uris": ["http://127.0.0.1:7333/callback"],
  "grant_types": ["authorization_code", "refresh_token"],
  "response_types": ["code"],
  "token_endpoint_auth_method": "none",
  "scope": "mcp:tools.invoke",
  "client_name": "Cursor",
  "software_id": "com.cursor.cursor",
  "software_version": "0.42.0"
}
```

服务器以 `client_id` 和一个用于后续更新的 `registration_access_token` 响应：

```json
{
  "client_id": "c_3e7f1a",
  "client_id_issued_at": 1769472000,
  "redirect_uris": ["http://127.0.0.1:7333/callback"],
  "grant_types": ["authorization_code", "refresh_token"],
  "registration_access_token": "regt_b2...",
  "registration_client_uri": "https://auth.example.com/register/c_3e7f1a"
}
```

`application_type` 不是装饰。回环（loopback）桌面客户端声明 `native`；服务器托管的客户端声明 `web` 并使用 HTTPS 重定向 URI。`token_endpoint_auth_method: none` 是公共原生客户端的正确默认值。它只拿到一个 `client_id`，由 PKCE 提供持有证明（proof-of-possession）。

三个生产陷阱：

- 注册端点必须按来源 IP 限速。没有这一条，敌意行为者可以脚本化地伪造数百万个注册，耗尽 `client_id` 命名空间。在注册机构处理请求之前先跑限速检查。
- `software_statement`（一个为客户端作证的签名 JWT）被一些企业 IdP 要求。本课的 mock 跳过它；生产环境要接一个验证步骤，拒绝来自非 localhost 重定向 URI 的未签名注册。
- `registration_access_token` 必须以哈希存储，不能存明文。这个令牌被窃意味着攻击者可以改写客户端的重定向 URI。

> DCR is deprecated in the 2026-07-28 revision. Keep it only for authorization servers that cannot consume CIMD and where pre-registration is impractical.
> `application_type` is not decorative. A loopback desktop client declares `native`; a server-hosted client declares `web` and uses HTTPS redirect URIs. `token_endpoint_auth_method: none` is the right default for a public native client. It gets a `client_id` only, with PKCE providing the proof-of-possession.
> The registration endpoint must rate-limit by source IP. Without that, a hostile actor scripts millions of fake registrations and exhausts the `client_id` namespace.
> The `registration_access_token` must be stored as a hash, not plaintext. Theft of this token means the attacker can rewrite the client's redirect URIs.

### RFC 8707 (recap) — Resource Indicators · RFC 8707（回顾）— 资源指示符

第 16 课建立了形状。生产规则：每个令牌请求都带 `resource=<canonical-mcp-url>`，且 MCP 服务器在每次调用时校验 `token.aud` 与自己的资源 URL 匹配。规范 URI 是该服务器*最具体*的标识符：它使用小写的 scheme 和 host，不带 fragment，并且按惯例不带结尾斜杠。路径组件**不是**按规则一律剥离——规范在需要识别单个 MCP 服务器时会保留它。`https://mcp.example.com`、`https://mcp.example.com/mcp`、`https://mcp.example.com:8443` 和 `https://mcp.example.com/server/mcp` 都可以是有效的规范 URI。每个服务器选定一个，并把 `aud` 精确固定到它。（本课的 mock 出于简洁使用裸主机受众，例如 `https://notes.example.com`；在同一个源下共驻多个 MCP 服务器的部署则用路径区分它们。）

> The production rule: every token request includes `resource=<canonical-mcp-url>`, and the MCP server verifies `token.aud` matches its own resource URL on every call. The canonical URI is the *most specific* identifier for the server: it uses lowercase scheme and host, no fragment, and conventionally no trailing slash. The path component is **not** stripped by rule — the spec keeps it when it is needed to identify an individual MCP server.

### RFC 7636 (recap) — PKCE · RFC 7636（回顾）— PKCE

PKCE 在 OAuth 2.1 中是强制的。本课的授权码流程总是携带 `code_challenge` 和 `code_verifier`。服务器拒绝任何没有 verifier 的令牌请求，或 verifier 无法哈希到已存储 challenge 的请求。

> PKCE is mandatory in OAuth 2.1. The lesson's authorization-code flow always carries `code_challenge` and `code_verifier`. The server rejects any token request without a verifier or with a verifier that does not hash to the stored challenge.

### MCP 2026-07-28 authorization profile · MCP 2026-07-28 授权配置（profile）

当前的 MCP 修订版保留了 OAuth 资源服务器边界，同时让 MCP 传输无状态化。没有可以缓存身份决策的协议会话。因此，授权层独立校验每个请求：

- 实现 RFC 9728 受保护资源元数据，并通过 401 上的 `WWW-Authenticate: Bearer resource_metadata="..."` 头**或** well-known URI `/.well-known/oauth-protected-resource` 提供其位置（SEP-985 让该头变为可选，以 well-known 为回退）。元数据的 `authorization_servers` 字段**必须（MUST）**至少指名一个服务器。
- 只通过**每个**请求上的 `Authorization: Bearer ...` 接受令牌——绝不放在查询字符串里，绝不在会话开始时只校验一次。
- 按请求校验 `aud`、`iss`、`exp` 和所需作用域。服务器**必须（MUST）**校验令牌是专门为它签发的（受众）；缺失或不匹配的 `aud` 一律拒绝，绝不当作通配符。
- 在 401/403 上，返回携带 `error=...` 的 `WWW-Authenticate: Bearer`、`resource_metadata="<PRM-URL>"` 参数（元数据文档的 URL，*不是*裸资源），并在 `insufficient_scope`（403）时带 `scope="..."`。注意：参数名是 `resource_metadata`，一个发现指针——challenge 里没有 `resource` 参数。
- 授权服务器发现接受 RFC 8414 OAuth 元数据**或** OpenID Connect Discovery 1.0 中的任意一种；客户端必须按优先级顺序尝试两个 well-known 后缀。
- 防御**混合攻击（mix-up attack）**的是客户端（而非服务器）：它在重定向前记录期望的 `issuer`，并在兑换码之前校验实际授权响应中返回的 `iss` 值（RFC 9207）。仅靠 PKCE 不能阻止 mix-up，因为客户端会把它的 `code_verifier` 交给它被引导到的任何令牌端点。
- 一个客户端凭证属于一个授权服务器签发者。如果发现解析到了另一个签发者，客户端重新注册，而不是提交旧的 `client_id`、注册令牌或访问令牌。
- CIMD 是首选的注册机制。DCR 已废弃；兼容性的 DCR 请求仍要声明正确的 `application_type`。

OAuth 2.1 草案是基底；RFC 8414/7591/8707/9728/9207 + RFC 7636 + CIMD 是接口；MCP 规范是它们之上的配置（profile）。

> The current MCP revision keeps the OAuth resource-server boundary while making MCP transport stateless. There is no protocol session on which to cache an identity decision. The authorization layer therefore validates each request independently.
> Accept tokens only via `Authorization: Bearer ...` on **every** request — never in a query string, never validated only at session start.
> Validate `aud`, `iss`, `exp`, and required scopes per request. The server **MUST** validate that the token was issued specifically for it (audience); a missing or mismatched `aud` is rejected, never treated as wildcard.
> The OAuth 2.1 draft is the substrate; RFC 8414/7591/8707/9728/9207 + RFC 7636 + CIMD are the surface; the MCP spec is the profile.

### Deployment capability checklist · 部署能力清单

厂商的功能对照表很快就会过时。去检查你实际要部署的那个授权服务器返回的元数据。这道闸门是机械性的：

| 检查项 | 要求的决策 |
|---|---|
| 发现的签发者 | 与策略期望的精确 HTTPS 签发者一致 |
| PKCE | 已公告 `S256`；否则停止 |
| 注册途径 | CIMD 首选，接受预注册，DCR 仅作已废弃的兼容路径 |
| 授权响应 | 在存在或已公告时校验 RFC 9207 `iss` |
| 资源绑定 | 令牌请求携带 `resource`；资源服务器要求匹配的 `aud` |
| 凭证存储 | 客户端 ID 与注册凭证按签发者键控；访问令牌按「签发者+资源」键控 |
| DCR 兼容 | 声明 `native` 或 `web`；拒绝不符合所声明应用类型的重定向 URI |

不要从产品名称或定价档位推断支持情况。把发现的文档留存在部署证据里，并在必填字段缺席时失败关闭（fail closed）。

> Vendor feature tables become stale quickly. Inspect the metadata returned by the authorization server you will actually deploy instead. The gate is mechanical.
> Do not infer support from a product name or pricing tier. Capture the discovered document in deployment evidence and fail closed when a mandatory field is absent.

### JWKS refresh pattern (rotate at the AS, refresh at the resource server) · JWKS 刷新模式（AS 负责轮换，资源服务器负责刷新）

把两个动词分开，因为把它们混为一谈是一个真实的生产 bug：

- **轮换（Rotate）**是*授权服务器*做的事：铸造一个新的签名密钥，发布到 JWKS，稍后退役旧的。资源服务器在其中没有任何角色，也做不到——它不持有 IdP 的私钥。
- **刷新（Refresh）**是*资源服务器*做的事：重新 `GET` 已发布的 JWKS 到自己的缓存。这是资源服务器唯一会做的 JWKS 动作。

生产环境的故障模式是过期缓存。用一个定时刷新任务加一个键值缓存来解决它。资源服务器运行一个任务（cron、timer，你的运行时提供什么都行），按固定间隔抓取 `<issuer>/.well-known/jwks.json` 并覆写 `cache[issuer] = {keys, fetched_at}`。校验器从这份缓存读取。当某个令牌的 `kid` 在缓存中缺失时，触发**一次**同步刷新作为回退，然后重新检查。这同时处理两种情况：定时刷新，以及「由全新密钥签名的令牌在下一次定时刷新之前到达」的密钥重叠窗口。

回退**必须是重新抓取，绝不是轮换**。如果你把缓存未命中路径接成 rotate-and-mint，两件事会坏掉：(1) 铸造一把新密钥产生的 `kid` *仍然*与令牌不匹配，查找照样失败；(2) 一个用随机 `kid` 值扫射令牌的攻击者会逼迫出无上限的密钥创建——一种自己造成的 DoS。重新抓取是幂等的，所以一个伪造的 `kid` 最多浪费一次抓取。

缓存的形状：

```json
{
  "https://auth.example.com": {
    "keys": [
      {"kid": "k_2026_03", "kty": "RSA", "n": "...", "e": "AQAB", "alg": "RS256", "use": "sig"},
      {"kid": "k_2026_04", "kty": "RSA", "n": "...", "e": "AQAB", "alg": "RS256", "use": "sig"}
    ],
    "fetched_at": 1772668800
  }
}
```

同时存在两把密钥是稳态。授权服务器通过先引入下一把密钥（`k_2026_04`）、再退役上一把（`k_2026_03`）来轮换，这样旧密钥下签发的令牌在过期前保持有效。缓存持有并集；校验器按 `kid` 选取。

> **Rotate** is what the *authorization server* does: mint a new signing key, publish it in the JWKS, retire the old one later. ... **Refresh** is what the *resource server* does: re-`GET` the published JWKS into its cache. That is the only JWKS action a resource server ever performs.
> The fall-back **must be a re-fetch, never a rotate**. If you wire the cache-miss path to a rotate-and-mint, two things break: (1) minting a fresh key produces a `kid` that *still* does not match the token, so the lookup fails anyway; and (2) an attacker who sprays tokens with random `kid` values forces an unbounded series of key creations — a self-inflicted DoS. A re-fetch is idempotent, so a bogus `kid` costs at most one wasted fetch.
> Two keys at once is the steady state. Authorization servers rotate by introducing the next key (`k_2026_04`) before retiring the previous (`k_2026_03`), so tokens issued under the old key remain valid until they expire. The cache holds the union; the validator picks by `kid`.

### The validation routine · 校验例程

MCP 服务器在分发任何工具之前运行校验。`code/main.py` 使用的形状：

```python
result = server.validate(bearer_token, required_scope="mcp:tools.invoke")
if not result["valid"]:
    return {"status": result["status"], "WWW-Authenticate": result["www_authenticate"]}
```

`validate` 解码 JWT，从 JWKS 缓存解析签名密钥（未命中时刷新一次），验证签名，然后检查 `iss` 是否在允许列表内、`aud` 是否等于本服务器的规范资源、`exp`，以及所需作用域——在第一次失败时返回 `WWW-Authenticate` challenge。让它保持为资源服务器上的单一例程，意味着每个入口点（每次工具调用、每种传输）都走同一套检查；不存在绕过校验就触达工具的路径。

> The MCP server runs validation before dispatching any tool.
> `validate` decodes the JWT, resolves the signing key from the JWKS cache (refreshing once on a miss), verifies the signature, then checks `iss` against the allow-list, `aud` against this server's canonical resource, `exp`, and the required scope — returning a `WWW-Authenticate` challenge on the first failure. Keeping it a single routine on the resource server means every entry point (every tool call, every transport) goes through the same checks; there is no path that reaches a tool without validating first.

### Opaque tokens use introspection, not guesswork · 不透明令牌靠内省，不靠猜测

并非每个访问令牌都是 JWT。如果签发者声明的是不透明令牌（opaque token），资源服务器无法把它解码成可信的声明。它通过经过认证的后端信道把令牌发给签发者的 RFC 7662 内省（introspection）端点，并要求 `active: true`、期望的签发者上下文、确切的 MCP 受众或资源、未过期的时间声明，以及具体工具所需的作用域。

按签发者、令牌的单向摘要和 MCP 资源来缓存内省结果。绝不用明文令牌当日志或缓存标签。正向缓存条目的有效期取令牌过期时间、签发者缓存指引与部署的撤销新鲜度目标三者中最早者。负向缓存要足够短，让新签发的令牌不会一直被误判为 inactive。一个资源的结果不能授权另一个资源，即使不透明令牌字符串完全相同。

不要从攻击者可控的令牌内容里选择校验模式。把「JWT 还是内省」固定到经过校验的签发者元数据和部署配置上。在 JWT 路径上，固定接受的算法和受信任的 `jwks_uri`；绝不跟随仅由令牌头选出的密钥 URL 或算法。

> If the issuer documents an opaque token, the resource server cannot decode it into trustworthy claims. It sends the token to the issuer's RFC 7662 introspection endpoint over an authenticated backchannel and requires `active: true`, the expected issuer context, the exact MCP audience or resource, unexpired time claims, and the scopes required by the concrete tool.
> Cache introspection by issuer, a one-way token digest, and MCP resource. Never use the clear token as a log or cache label.
> Do not choose validation mode from attacker-controlled token contents. Pin JWT versus introspection behavior to validated issuer metadata and deployment configuration. On the JWT path, pin accepted algorithms and trusted `jwks_uri`; never follow a key URL or algorithm selected only by the token header.

### Revocation is a freshness contract · 撤销是一个新鲜度契约

RFC 7009 让客户端可以请求授权服务器撤销一个令牌。但那个请求不会抹掉已经缓存在每个资源服务器里的副本。定义可接受的最大撤销延迟，并让每个缓存都遵守它。

不透明令牌部署可以通过在每次高风险调用时内省、或使用很短的正向缓存，实现更紧的撤销。自包含 JWT 部署通常组合使用：短的访问令牌生命周期加上刷新令牌撤销、针对签发者级事件的密钥退役，以及一个可选的主题、会话或令牌 ID 拒绝列表（denylist）用于紧急的本地拒绝。一个签名 JWT 在过期之前在密码学上始终有效，除非资源服务器拿到了最新的外部撤销证据。

登出、账号禁用、同意撤回和事件响应是不同的触发器，但必须收敛为一个可度量的陈述：至多在声明的撤销窗口之后，每个副本都拒绝该凭证。要通过负载均衡器来测试这个陈述，而不是只对一个热身进程测。

> RFC 7009 lets a client ask an authorization server to revoke a token. That request does not erase copies already cached by every resource server. Define the maximum acceptable revocation delay and make every cache honor it.
> Logout, account disablement, consent withdrawal, and incident response are different triggers but must converge on one measurable statement: after at most the declared revocation window, every replica refuses the credential. Test that statement through the load balancer, not only against one warm process.

### Dependency failure needs a declared decision · 依赖故障需要预先声明的决策

绝不在异常处理器里即兴发挥可用性策略。

| 故障 | 安全的生产行为 |
|---|---|
| 计划内的 JWKS 刷新失败，但已知 `kid` 仍在仍然有效且有界的缓存中 | 只在声明的 stale-on-error 窗口内继续，并发出降级健康证据 |
| 令牌的 `kid` 未知，且唯一允许的一次刷新失败 | 拒绝；绝不接受无法验证的签名 |
| 内省不可用 | 对受保护调用失败关闭；不要把网络故障转换成 `active: true` |
| 受保护资源或签发者元数据意外变化 | 停止新的注册与令牌获取；只保留显式固定、未过期、且处于有界事件策略下的配置 |
| 撤销端点不可用 | 把登出或撤销报告为未完成；尽可能在本地把凭证保留为不可用状态；不要声称全局撤销成功 |
| 时钟源或声明类型无效 | 直接拒绝，而不是放宽时钟偏移直到令牌通过 |

把故障与无效凭证分开归类。依赖中断是带健康与重试策略的运维错误；坏签名、坏签发者、坏受众、坏过期时间或坏作用域是授权拒绝。两者都不该触达工具处理器，也都不该把令牌内容泄漏进审计证据。

> Never improvise availability policy inside an exception handler.
> Classify failures separately from invalid credentials. A dependency outage is an operational error with health and retry policy. A bad signature, issuer, audience, expiry, or scope is an authorization refusal. Neither reaches the tool handler, and neither should leak token contents into audit evidence.

### Audience-replay walkthrough (access-token privilege restriction) · 受众重放演练（访问令牌权限限制）

服务器 A（`notes.example.com`）和服务器 B（`tasks.example.com`）都注册在同一个授权服务器上。服务器 A 被攻陷。攻击者拿走一个用户的 notes 令牌，重放给服务器 B。

服务器 B 的校验器：

1. 解码 JWT，按 `kid` 抓取 JWKS，验证签名。
2. 对照其受保护资源元数据的 `authorization_servers` 检查 `iss`。（通过——同一个 IdP。）
3. 检查 `aud == "https://tasks.example.com"`。（失败——令牌的 `aud` 是 `https://notes.example.com`。）
4. 返回 401，附 `WWW-Authenticate: Bearer error="invalid_token", error_description="audience mismatch", resource_metadata="https://tasks.example.com/.well-known/oauth-protected-resource"`。

受众声明是这个攻击在协议层唯一的防御。为了性能跳过它是最常见的生产错误；校验器必须在每个请求上运行，而不是只在会话开始时。规范把这称为**访问令牌权限限制（access-token privilege restriction）**：MCP 服务器**必须（MUST）**拒绝任何没有在受众中指名它的令牌。

> **命名说明。** 规范把术语*混淆代理（confused deputy）*保留给一个相关但不同的问题：一个作为 OAuth **代理**访问第三方 API 的 MCP 服务器，使用静态客户端 ID，在没有获得每客户端用户同意的情况下转发令牌。受众绑定修的是上面的重放；混淆代理的修法是每客户端同意**加上**绝不把入站令牌透传给上游 API（MCP 服务器**必须（MUST）**获取它自己单独的上游令牌）。

> Server B's validator: ... Check `aud == "https://tasks.example.com"`. (Fail — token's `aud` is `https://notes.example.com`.)
> The audience claim is the only defense against this attack at the protocol layer. Skipping it for performance is the most common production mistake; the validator must run on every request, not just at session start. The spec calls this **access-token privilege restriction**: an MCP server `MUST` reject any token that does not name it in the audience.
> **Naming note.** The spec reserves the term *confused deputy* for a related-but-distinct problem: an MCP server acting as an OAuth **proxy** to a third-party API, using a static client ID, that forwards a token without obtaining per-client user consent. Audience binding fixes the replay above; the confused-deputy fix is per-client consent **plus** never passing the inbound token through to upstream APIs (the MCP server `MUST` get its own separate upstream token).

### Mix-up attacks (a client-side defense the server cannot provide) · 混合攻击（服务器替你做不了的客户端防御）

一个客户端一生要和许多授权服务器打交道。一个恶意 AS 可以试图让客户端在攻击者的令牌端点兑换一个诚实 AS 的授权码。受众绑定在这里帮不上忙——攻击发生在任何令牌存在之前。防御住在客户端里（RFC 9207）：

1. 重定向前，客户端从经过校验的 AS 元数据里记录期望的 `issuer`。
2. 收到授权响应时，客户端在把 code 发给任何地方之前，把返回的 `iss` 参数与记录的签发者比较（简单字符串比较，不做归一化）。
3. 不匹配（或 AS 公告了 `authorization_response_iss_parameter_supported` 但 `iss` 缺席）→ 拒绝，甚至不展示 `error` 字段。

仅靠 PKCE 不能阻止 mix-up，因为客户端会把它的 `code_verifier` 交给它被引导到的任何令牌端点。这就是规范把签发者与 PKCE verifier 和 `state` 一起按请求记录的原因。

> A malicious AS can try to make the client redeem an honest AS's authorization code at the attacker's token endpoint. Audience binding does not help here — the attack happens before any token exists. The defense lives in the client (RFC 9207).
> PKCE alone does not stop mix-up, because the client hands its `code_verifier` to whatever token endpoint it was steered to. This is why the spec records the issuer per-request alongside the PKCE verifier and `state`.

### Failure modes · 失败模式

- **JWKS 过期。** AS 轮换密钥后，校验器拒绝有效令牌。修法就是上面的 cron 刷新 + 缓存未命中重抓模式。绝不在没有刷新任务的情况下缓存 JWKS。
- **把轮换当回退。** 把缓存未命中路径接成 rotate-and-mint 而不是重新抓取，是一个真实的 bug：它永远产生不了缺失的 `kid`，还会把攻击者可控的 `kid` 值变成密钥创建 DoS。回退必须是幂等的 `refresh-jwks`。
- **`aud` 声明缺失。** 一些 IdP 在令牌请求中没有 `resource` 时默认省略 `aud`。校验器必须拒绝缺失 `aud` 的令牌，而不是把缺席当作通配符。
- **缺少 `iss` 检查导致的 mix-up。** 一个不把 RFC 9207 `iss` 授权响应参数与重定向前记录的签发者做校验的客户端，可能被引导到攻击者的令牌端点去兑换诚实 AS 的 code。这是客户端侧的失败；资源服务器无法补偿它。
- **作用域升级竞态。** 同一用户的两个并发的 step-up 流程可以同时成功，产生两个作用域不同的访问令牌。校验器必须使用请求上呈现的那个令牌，而不是去查「该用户当前的作用域」——那会制造一个 TOCTOU 窗口。
- **注册令牌被窃。** 泄漏的 `registration_access_token` 让攻击者改写重定向 URI。静态存储时做哈希；要求客户端在每次更新时出示明文；一旦怀疑就轮换。
- **`iss` 未固定。** 接受任意 `iss` 的校验器会让攻击者架起自己的授权服务器，为目标受众注册一个客户端并签发令牌。受保护资源元数据的 `authorization_servers` 列表就是允许列表；强制执行它。
- **凭证或令牌缓存冲突。** 只按资源键控注册的客户端，可能把一个授权服务器的身份提交给另一个。只按签发者键控访问令牌的客户端，可能在错误的受众处重放令牌。按经过校验的签发者键控注册，按 `(issuer, resource)` 键控访问令牌，并且签发者一变就重新注册。

> **Stale JWKS.** The validator rejects valid tokens after the AS rotates a key. The fix is the cron-refresh + cache-miss-refetch pattern above. Never cache JWKS without a refresh job.
> **Rotate-as-fall-back.** Wiring the cache-miss path to a rotate-and-mint instead of a re-fetch is a real bug: it never produces the missing `kid`, and it turns attacker-controlled `kid` values into a key-creation DoS. The fall-back must be the idempotent `refresh-jwks`.
> **Missing `aud` claim.** Some IdPs default to omitting `aud` unless `resource` is present in the token request. The validator must reject tokens with missing `aud`, not treat absence as wildcard.
> **`iss` not pinned.** A validator that accepts any `iss` lets an attacker stand up their own authorization server, register a client for the target audience, and issue tokens. The protected-resource metadata's `authorization_servers` list is the allow-list; enforce it.

```figure
t3-jwks-rotate
```

## Use It · 实战用法

`code/main.py` 用标准库 Python 和三个角色跑通完整的生产流程：`AuthorizationServer`、`ResourceServer` 和 `Client`。流程如下：

从仓库根目录运行：

```bash
cd phases/13-tools-and-protocols/18-mcp-auth-production
python3 code/main.py
python3 -m unittest discover -s code/tests -v
```

第一条命令打印按签发者绑定的注册与令牌校验记录。第二条命令报告 18 项通过的检查。两条命令都不会打开网络监听，也不会写凭证。

1. 授权服务器在 `/.well-known/oauth-authorization-server` 发布 RFC 8414 元数据。
2. MCP 客户端调用元数据端点，检查它的注册选项（CIMD 的 `client_id_metadata_document_supported`、DCR 的 `registration_endpoint`）和 `S256` PKCE 支持。
3. 客户端检查是否有按签发者作用域的预注册，否则用它的 HTTPS 客户端 ID 元数据文档注册。已废弃的 DCR 仍是一个可单独测试的兼容方法。
4. 客户端记录经过校验的签发者，创建 S256 challenge，收到一次性授权码和 `iss`，校验返回的签发者，然后用原始 verifier 和 RFC 8707 `resource` 指示符兑换 code。
5. MCP 客户端带着 `Authorization: Bearer ...` 调用 MCP 服务器上的一个工具。
6. MCP 服务器运行 `validate`，从 JWKS 缓存解析签名密钥。
7. IdP 轮换一把密钥；定时刷新把 JWKS 重新拉进缓存。
8. 下一次调用针对刷新后的密钥完成校验，无需重启，且旧令牌在重叠窗口内仍然通过校验。
9. 针对另一个 MCP 资源的受众重放尝试得到 401，附 `audience mismatch` 和 `resource_metadata` 指针。

这里的 JWT 用 HS256 和共享密钥（这样本课只用标准库就能跑）。生产环境用 RS256 或 EdDSA 配合上面的 JWKS 模式；除此之外校验逻辑完全相同。因为 IdP 和资源服务器在同一个进程里，`refresh_jwks` 直接读取授权服务器的密钥列表；跨网络时它是一次对 `jwks_uri` 的 HTTP `GET`。

> `code/main.py` walks the full production flow with stdlib Python and three roles: `AuthorizationServer`, `ResourceServer`, and `Client`.
> The first command prints the issuer-bound enrollment and token-validation transcript. The second reports eighteen passing checks. Neither command opens a network listener or writes credentials.
> An audience-replay attempt against a different MCP resource gets 401 with `audience mismatch` and a `resource_metadata` pointer.
> The JWT here uses HS256 with a shared secret (so the lesson runs on stdlib only). Production uses RS256 or EdDSA with the JWKS pattern above; the validation logic is otherwise identical.

## Ship It · 交付

本课产出 `outputs/skill-mcp-auth.md`。给定一个 MCP 服务器配置和一个 IdP 能力集，这个技能会输出需要搭建的认证接口——受保护资源元数据、要用的注册路径（CIMD、预注册或 DCR 回退）、JWKS 刷新计划、作用域映射，以及当 IdP 不支持完整 RFC 配置时要应用的拒绝规则。

> This lesson produces `outputs/skill-mcp-auth.md`. Given an MCP server config and an IdP capability set, the skill emits the auth surface to stand up — the protected-resource metadata, the enrollment path to use (CIMD, pre-registration, or DCR fallback), the JWKS refresh schedule, the scope mapping, and the refusal rules to apply when the IdP does not support the full RFC profile.

## Exercises · 练习

1. 运行 `code/main.py`。追踪整个流程。注意 IdP 如何在第 6 步轮换一把密钥，定时 `refresh_jwks` 如何重新拉取已发布的密钥集，以及旧令牌（重叠窗口）和新令牌如何都无需重启即通过校验。
2. 向受保护资源元数据的 `authorization_servers` 列表添加一个新 IdP。签发一个由新 IdP 签名的令牌，确认校验器接受它。再签发一个由未列入列表的 IdP 签名的令牌，确认校验器以 `WWW-Authenticate: Bearer error="invalid_token", error_description="iss not allowed"` 拒绝。
3. 给 `register_client` 加一个限速检查，在注册机构接受请求之前运行。用一个以 IP 为键的小字典，为每个来源 IP 保存一个令牌桶。
4. 阅读 RFC 7591，找出本课 `/register` 处理器没有校验的两个字段。把校验加上。（提示：`software_statement` 和 `redirect_uris` 的 URI scheme。）
5. 添加第二个授权服务器。确认客户端存储一份单独的、按签发者键控的注册，并拒绝复用第一个签发者的令牌或 `client_id`。
6. 证明 DoS 修复。给校验器发一个带随机 `kid` 的令牌，确认 `refresh_jwks` 至多运行一次，且授权服务器的密钥数量不增长。然后故意把回退改成 rotate-and-mint，观察每个伪造令牌让密钥数量攀升——之后恢复成重抓。
7. 用 `native` 和 `web` 两种客户端演练已废弃的 DCR。确认带 HTTP 重定向 URI 的 web 客户端、以及没有精确回环重定向的 native 客户端都被拒绝。

> 1. Run `code/main.py`. Trace the flow. Note how the IdP rotates a key in step 6, the scheduled `refresh_jwks` re-pulls the published set, and both the old token (overlap window) and a fresh token validate without restart.
> 2. Add a new IdP to the protected-resource metadata's `authorization_servers` list. Issue a token signed by the new IdP and confirm the validator accepts it. Issue a token signed by an unlisted IdP and confirm the validator rejects with `WWW-Authenticate: Bearer error="invalid_token", error_description="iss not allowed"`.
> 3. Add a rate-limit check to `register_client` that runs before the registrar accepts a request. Use a token-bucket per source IP held in a small dict keyed by IP.
> 4. Read RFC 7591 and identify two fields the lesson's `/register` handler does not validate. Add the validation. (Hint: `software_statement` and `redirect_uris` URI scheme.)
> 5. Add a second authorization server. Confirm the client stores a separate issuer-keyed enrollment and refuses to reuse the first issuer's token or `client_id`.
> 6. Prove the DoS fix. Send the validator a token with a random `kid` and confirm `refresh_jwks` runs at most once and the authorization server's key count does not grow. Then deliberately re-wire the fall-back to a rotate-and-mint and watch the key count climb per bogus token — restore the re-fetch afterward.
> 7. Exercise deprecated DCR with both `native` and `web` clients. Confirm a web client with an HTTP redirect URI and a native client without an exact loopback redirect are rejected.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| ASM | 「OAuth 元数据文档」 | RFC 8414 `/.well-known/oauth-authorization-server` JSON |
| CIMD | 「客户端元数据 URL」 | 客户端 ID 元数据文档：一个用作 `client_id` 的 HTTPS URL；由 AS 拉取 JSON。MCP 2026-07-28 的首选注册方式 |
| DCR | 「自助客户端注册」 | RFC 7591 `POST /register`；对当前 MCP 已废弃，仅为兼容保留 |
| JWKS | 「用于 JWT 校验的公钥」 | JSON Web 密钥集，从 `jwks_uri` 抓取，按 `kid` 索引 |
| 轮换 vs 刷新（Rotate vs refresh） | 「更新密钥」 | *轮换* = AS 铸造/退役签名密钥；*刷新* = 资源服务器重新抓取已发布的密钥集。资源服务器只会刷新 |
| 资源指示符（Resource indicator） | 「受众参数」 | RFC 8707 `resource` 参数，把令牌固定到一个服务器 |
| `aud` 声明 | 「受众」 | 校验器与规范资源 URL 比较的 JWT 声明 |
| 受众重放（Audience replay） | 「令牌重放」 | 为服务器 A 签发的令牌被提交给服务器 B；由受众校验防御（规范称 access-token privilege restriction） |
| 混淆代理（Confused deputy） | 「代理令牌滥用」 | 带静态客户端 ID 的 MCP 代理在没有每客户端同意的情况下转发令牌；与受众重放不同 |
| 混合攻击（Mix-up attack） | 「错误的令牌端点」 | 客户端被引导到攻击者端点兑换诚实 AS 的 code；由客户端侧的 RFC 9207 `iss` 防御 |
| `iss` 允许列表 | 「可信授权服务器」 | 受保护资源元数据 `authorization_servers` 中指名的集合 |
| `resource_metadata` | 「去哪找 PRM 文档」 | 401/403 上 `WWW-Authenticate` 中指名 RFC 9728 元数据 URL 的参数 |
| 公共客户端（Public client） | 「原生或浏览器客户端」 | 没有 `client_secret` 的 OAuth 客户端；由 PKCE 补偿 |
| `WWW-Authenticate` | 「401/403 响应头」 | 携带驱动客户端恢复的 `Bearer error=...` 指令 |

> | Term | What people say | What it actually means |
> | ASM | "OAuth metadata document" | RFC 8414 `/.well-known/oauth-authorization-server` JSON |
> | CIMD | "Client metadata URL" | Client ID Metadata Document: an HTTPS URL used as the `client_id`; the AS pulls the JSON. Preferred enrollment in MCP 2026-07-28 |
> | DCR | "Self-service client registration" | RFC 7591 `POST /register`; deprecated for current MCP and retained only for compatibility |
> | JWKS | "Public keys for JWT validation" | JSON Web Key Set, fetched from `jwks_uri`, indexed by `kid` |
> | Rotate vs refresh | "Updating the keys" | *Rotate* = AS mints/retires signing keys; *refresh* = resource server re-fetches the published set. Resource servers only ever refresh |
> | Resource indicator | "Audience parameter" | RFC 8707 `resource` parameter pinning the token to one server |
> | `aud` claim | "Audience" | JWT claim the validator compares against the canonical resource URL |
> | Audience replay | "Token replay" | Token issued for Server A presented to Server B; defended by audience validation (spec: access-token privilege restriction) |
> | Confused deputy | "Proxy token misuse" | An MCP proxy with a static client ID forwarding a token without per-client consent; distinct from audience replay |
> | Mix-up attack | "Wrong token endpoint" | Client steered to redeem an honest AS's code at an attacker's endpoint; defended client-side via RFC 9207 `iss` |
> | `iss` allow-list | "Trusted authorization servers" | The set named in protected-resource metadata's `authorization_servers` |
> | `resource_metadata` | "Where to find the PRM doc" | `WWW-Authenticate` parameter naming the RFC 9728 metadata URL on a 401/403 |
> | Public client | "Native or browser client" | OAuth client with no `client_secret`; PKCE compensates |
> | `WWW-Authenticate` | "401/403 response header" | Carries `Bearer error=...` directives that drive client recovery |

## Further Reading · 延伸阅读

- [MCP authorization specification (2026-07-28)](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) —— 当前的 MCP 授权配置
- [MCP 2026-07-28 changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog) —— CIMD、签发者校验、DCR 废弃与按签发者键控凭证的变更
- [OAuth Client ID Metadata Document (draft-ietf-oauth-client-id-metadata-document-00)](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-client-id-metadata-document-00) —— CIMD
- [RFC 8414 — OAuth 2.0 Authorization Server Metadata](https://datatracker.ietf.org/doc/html/rfc8414) —— 发现契约
- [RFC 7591 — OAuth 2.0 Dynamic Client Registration Protocol](https://datatracker.ietf.org/doc/html/rfc7591) —— DCR（后备路径）
- [RFC 7636 — Proof Key for Code Exchange (PKCE)](https://datatracker.ietf.org/doc/html/rfc7636) —— 公共客户端的持有证明
- [RFC 8707 — Resource Indicators for OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc8707) —— 受众固定
- [RFC 9728 — OAuth 2.0 Protected Resource Metadata](https://datatracker.ietf.org/doc/html/rfc9728) —— 资源服务器发现
- [RFC 9207 — OAuth 2.0 Authorization Server Issuer Identification](https://datatracker.ietf.org/doc/html/rfc9207) —— 防御 mix-up 攻击的 `iss` 参数
- [RFC 7662: OAuth 2.0 Token Introspection](https://datatracker.ietf.org/doc/html/rfc7662) —— 令牌内省
- [RFC 7009: OAuth 2.0 Token Revocation](https://datatracker.ietf.org/doc/html/rfc7009) —— 令牌撤销
