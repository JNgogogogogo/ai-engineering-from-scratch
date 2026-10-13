# MCP Tool Contracts and Content · MCP 工具契约与内容

只有当发现（discovery）、参数、结果、分页（pagination）与传输元数据都认同同一份契约时，一个工具自动化起来才是安全的。

> A tool is safe to automate only when discovery, arguments, results, pagination, and transport metadata agree on one contract.

**类型：** Build（构建）
**语言：** Python
**先修：** Phase 13 · 第 07、09、10 课
**时间：** ~120 分钟

## Learning Objectives · 学习目标

- 用 JSON Schema 2020-12 定义工具的输入与输出。
- 校验结构化结果，而不假设它们是 JSON 对象。
- 在文本、图像、音频、资源链接与内嵌资源之间做选择。
- 在工具到达模型之前，拒绝不安全的 `x-mcp-header` 定义。
- 对参数头（parameter-header）的值进行编码，并验证头部与正文完全一致（parity）。
- 遍历游标分页（cursor pagination），而不解释游标的值。
- 为 `completion/complete` 的建议设定边界并做授权。

> Define tool inputs and outputs with JSON Schema 2020-12.
> Validate structured results without assuming they are JSON objects.
> Choose between text, image, audio, resource links, and embedded resources.
> Reject unsafe `x-mcp-header` definitions before a tool reaches the model.
> Encode parameter-header values and verify exact header-to-body parity.
> Traverse cursor pagination without interpreting cursor values.
> Bound and authorize `completion/complete` suggestions.

## The Problem · 问题在哪

调用一个 Python 函数很容易。通过 AI 宿主调用一个远端能力，则是一个契约问题。

服务端发布描述符（descriptor）。客户端把这个描述符变成模型上下文和用户界面。模型生成参数。网关可能根据镜像的头部路由请求。服务端执行工具。然后客户端要判断结果是否足够安全、足够有效，可以返回给模型。

一个薄弱的边界会污染整条链。

想五个失败：

- 描述符说结果是一个对象，服务端却返回了数组。
- 客户端在 `nextCursor` 是空字符串时停止了分页。
- 一个 token 参数被镜像进 HTTP 头，对中间方（intermediaries）变得可见。
- 一个 Unicode 路由值被当作原始头发送，然后网关和源站解释出不同的字节。
- 一个补全端点向无权访问它的调用者建议了生产环境。

这些失败没有一个能靠更好的提示词修复。它们需要显式的协议与应用契约。

> Calling a Python function is easy. Calling a remote capability through an AI host is a contract problem.
> One weak boundary corrupts the whole chain.
> None of these failures is fixed by better prompting. They require explicit protocol and application contracts.

## The Contract Pipeline · 契约流水线

把每次工具调用当成五道门：

1. **发现（Discover）。** 读取一个确定性的、分页的工具列表。
2. **准入（Admit）。** 校验每个描述符并应用本地安全策略。
3. **调用（Invoke）。** 校验参数并构建传输元数据。
4. **执行（Execute）。** 运行处理器并正确分类失败。
5. **消费（Consume）。** 在模型使用之前校验内容块与结构化输出。

```figure
mcp-contract-pipeline
```

宿主拥有准入与消费这两道门。服务端无法强迫客户端信任它的注解、schema 或输出。

> Treat each tool call as five gates: Discover. Admit. Invoke. Execute. Consume.
> The host owns the admission and consumption gates. A server cannot force a client to trust its annotations, schemas, or outputs.

## JSON Schema Is a Runtime Boundary · JSON Schema 是运行时边界

在 MCP `2026-07-28` 中，`inputSchema` 与 `outputSchema` 使用 JSON Schema。当 `$schema` 缺省时，默认方言（dialect）是 2020-12。

输入 schema 必须是一个 schema 对象。一个没有参数的工具也应该精确说明它接受什么：

```json
{
  "type": "object",
  "additionalProperties": false
}
```

这比 `{ "type": "object" }` 更严格，后者接受任意属性。

输出 schema 是可选的。一旦服务端发布了一个，每个完整的工具结果都承诺返回符合契约的 `structuredContent`，包括 `isError: true` 的结果。错误标志分类的是执行结果；它不豁免已发布的输出契约。客户端应当校验结果，而不是信任描述符。

> In MCP `2026-07-28`, `inputSchema` and `outputSchema` use JSON Schema. When `$schema` is absent, the default dialect is 2020-12.
> Once a server publishes one, every complete tool result commits to returning conforming `structuredContent`, including results with `isError: true`. The error flag classifies execution outcome; it does not waive the published output contract. Clients should validate the result instead of trusting the descriptor.

### Structured content is any JSON value · 结构化内容可以是任意 JSON 值

不要把 `structuredContent` 硬编码成字典。它可以是：

- 一个对象；
- 一个数组；
- 一个字符串；
- 一个数字；
- 一个布尔值；
- `null`。

这个工具返回一个数组：

```json
{
  "name": "tag_catalog",
  "inputSchema": {
    "type": "object",
    "additionalProperties": false
  },
  "outputSchema": {
    "type": "array",
    "items": {"type": "string"}
  }
}
```

它的成功结果是合法的：

```json
{
  "resultType": "complete",
  "content": [
    {
      "type": "text",
      "text": "[\"contracts\", \"mcp\", \"stateless\"]"
    }
  ],
  "structuredContent": ["contracts", "mcp", "stateless"],
  "isError": false
}
```

为了兼容性，结构化结果还应在文本块里包含序列化后的 JSON。文本不是校验来源。`structuredContent` 才是。

> Do not hard-code `structuredContent` as a dictionary. It can be: an object; an array; a string; a number; a boolean; `null`.
> For compatibility, structured results should also include serialized JSON in a text block. The text is not the validation source. `structuredContent` is.

### A small validator still teaches the boundary · 一个小验证器也能讲清边界

本课刻意使用一个 JSON Schema 子集，因为它留在了 Python 标准库之内。它检查示例工具用到的机制：

- object、array、string、integer、number、boolean 与 null 类型；
- 必需属性；
- `additionalProperties: false`；
- 数组元素；
- 枚举值；
- 最小字符串长度。

这不是生产级完整验证器的替代品。可复用的教训是校验发生的位置：发现之后校验描述符，执行之前校验参数，消费之前校验结构化结果。

> The lesson uses a deliberate JSON Schema subset because it stays inside the Python standard library.
> This is not a replacement for a complete production validator. The reusable lesson is where validation happens: after discovery for descriptors, before execution for arguments, and before consumption for structured results.

## Content Blocks Carry Different Costs · 内容块的成本各不相同

`content` 数组可以组合多种内容类型。

| 类型 | 用它来做什么 | 主要边界 |
|------|------------|---------------|
| `text` | 面向人和模型的可读摘要 | 把文本当作不可信输出 |
| `image` | 以 base64 编码的视觉证据 | 校验媒体类型与大小 |
| `audio` | 以 base64 编码的语音或录音输出 | 校验媒体类型与时长上限 |
| `resource_link` | 客户端之后可能抓取的一个 URI | 对之后的资源读取重新授权 |
| `resource` | 直接内嵌在结果里的数据 | 现在就执行载荷与内容限制 |

资源链接不能证明该资源出现在 `resources/list` 里。它是这一次工具调用返回的引用。客户端在跟随这个 URI 时，仍然要应用自己的资源策略。

内嵌资源省掉一次往返，但会增大当前响应的体积。对大型或独立变化的产物用链接。对必须随结果原子传输的小证据用内嵌资源。

本课的 `evidence_bundle` 结果包含全部五种类型。客户端在接受结果之前逐块校验。

> A resource link is not proof that the resource appears in `resources/list`. It is a reference returned by this tool call. The client still applies its resource policy when it follows the URI.
> An embedded resource avoids another round trip but increases the current response size. Use links for large or independently changing artifacts. Use embedded resources for small evidence that must travel atomically with the result.

## `x-mcp-header` Is Routing Metadata · `x-mcp-header` 是路由元数据

`inputSchema` 里的一个属性可以声明 `x-mcp-header`。在 Streamable HTTP 之上，客户端把这个参数镜像成 `Mcp-Param-{name}`。

```json
{
  "region": {
    "type": "string",
    "x-mcp-header": "Region"
  }
}
```

当 `region: "eu-west"` 时，传输层可以发出：

```http
Mcp-Param-Region: eu-west
```

这个注解的存在，是为了让负载均衡器、网关或策略引擎不用解析 JSON 正文就能路由。它不是放凭据的地方。

协议对注解的约束：

- 头名称非空，且符合 HTTP 字段名 token 语法；
- 头名称在不区分大小写的前提下唯一；
- 属性类型是 string、integer 或 boolean；
- 不允许 `number`；
- 注解只出现在 `inputSchema.properties` 的直接成员上；
- 整数值保持在 `-9007199254740991` 到 `9007199254740991` 之间。

位置规则是语法性的、失败关闭（fail-closed）的。要遍历整棵 schema 树，而不是只遍历你的验证器恰好理解的那部分。拒绝出现在嵌套对象的 `properties`、`oneOf` 分支、`items`、由 `$ref` 到达的定义或任何输出 schema 下的注解。解析一个引用，并不会把被引用的节点变成直接顶层属性。

本课加了一条部署策略：拒绝镜像 `password`、`secret`、`token`、`api_key`、`authorization` 这类名字的描述符。官方规范建议服务端作者不要镜像敏感参数。客户端可以把这条建议变成一条硬性的准入规则。

审计头名称，而不是头的值。示例代码记录 `Mcp-Param-Region`，同时把 `eu-west` 挡在审计事件之外。

> A property inside `inputSchema` may declare `x-mcp-header`. Over Streamable HTTP, the client mirrors that argument into `Mcp-Param-{name}`.
> The annotation exists so a load balancer, gateway, or policy engine can route without parsing the JSON body. It is not a place to put credentials.
> The location rule is syntactic and fail-closed. Walk the entire schema tree, not just the properties your validator happens to understand.
> Audit the header name, not its value. The sample code records `Mcp-Param-Region` while keeping `eu-west` out of the audit event.

### Encode values before building HTTP headers · 构建 HTTP 头之前先编码值

一个参数值只有当它是非空的、由 `!` 到 `~` 的可见 ASCII 字符组成的字符串、并且看起来不像编码哨兵（sentinel）时，才可以作为纯文本传输。其他一切值都使用这个精确形式：

```text
=?base64?{Base64UTF8}?=
```

`Base64UTF8` 是对精确 UTF-8 字节做的标准 base64。不要先修剪、归一化或替换值。对 Unicode、空字符串、空格、制表符、控制字符、CR 或 LF、前导或尾随空白，以及任何以 `=?base64?` 开头的值进行编码。把一个看起来像哨兵的值再编码一次，正是接收方能够还原字面原文、而不是把它当作传输语法解码的原因。

布尔值渲染为小写的 `true` 或 `false`。整数按十进制渲染，且必须保持在 JavaScript 安全整数范围内。范围之外的值会被拒绝，而不是被中间方四舍五入。

> A parameter value may travel as plain text only when it is a non-empty string of visible ASCII characters from `!` through `~` and does not resemble the encoding sentinel. Everything else uses this exact form ...
> `Base64UTF8` is standard base64 over the exact UTF-8 bytes. Do not trim, normalize, or replace the value first. Encode Unicode, empty strings, spaces, tabs, control characters, CR or LF, leading or trailing whitespace, and any value beginning with `=?base64?`.
> Booleans render as lowercase `true` or `false`. Integers render in base 10 and must stay inside the JavaScript safe integer range. Values outside that range are rejected instead of rounded by an intermediary.

### The server checks the mirrored copy · 服务端校验镜像副本

头的生成只是客户端这一半。在 Streamable HTTP 边界上，服务端必须：

1. 不区分头名称大小写地找出可识别的 `Mcp-Param-*` 名称；
2. 在存在时解码精确的 base64 哨兵形式；
3. 把解码后的文本与对应的 JSON 正文参数精确比较；
4. 在分发之前拒绝缺失、重复、意外、畸形或不匹配的可识别头。

拒绝是 HTTP `400` 加 JSON-RPC 错误码 `-32020`。正文值和它的编码头形式都不该进入审计记录。只记录可识别的头名称和拒绝类别。

`code/main.py` 直接建模了这个边界。[第 09 课](../../09-mcp-transports/)讲解了更宽的 Streamable HTTP 校验顺序，包括方法与协议版本的一致性。

> Header generation is only the client half. At the Streamable HTTP boundary, the server must: find recognized `Mcp-Param-*` names without regard to header-name case; decode the exact base64 sentinel form when present; compare the decoded text with the corresponding JSON body argument exactly; reject a missing, duplicated, unexpected, malformed, or mismatched recognized header before dispatch.
> The rejection is HTTP `400` with JSON-RPC error code `-32020`. Neither the body value nor its encoded header form belongs in the audit record. Record the recognized header name and the rejection category only.

## Pagination Cursors Are Opaque · 分页游标是不透明的

MCP 的列表操作使用游标分页。服务端决定页大小和游标格式。客户端只有一个决策：

```python
if result.get("nextCursor") is None:
    break
cursor = result["nextCursor"]
```

不要这样写：

```python
if not result.get("nextCursor"):
    break
```

空字符串是一个合法游标。真值判断会过早停止。

客户端不得解码游标、递增游标、为了排序把它与之前的游标比较，或推断页码。服务端可以给游标签名、把它绑定到某个目录版本，或把它映射到私有状态。那是服务端的实现细节。

示例服务端刻意在第一页之后返回 `""`。客户端必须在第二个请求里原样发回这个值。它的轨迹是：

```text
<first request with no cursor>
<second request with cursor "">
```

非法游标产生 JSON-RPC invalid params，错误码 `-32602`。

> MCP list operations use cursor pagination. The server selects page size and cursor format. The client gets one decision ...
> Clients must not decode a cursor, increment it, compare it with a prior cursor for ordering, or infer a page number. A server may sign a cursor, bind it to a catalog version, or map it to private state. That is the server's implementation detail.
> An empty string is a valid cursor. Truthiness would stop too early.

## Completion Is an Authorization Surface · 补全是授权面

`completion/complete` 为 prompt 参数和资源模板参数提供补全建议。它对交互式表单有用，但它可能泄露那些被普通列表方法保护起来的名字。

一个补全请求指名一个引用（reference）和正在被补全的参数：

```json
{
  "method": "completion/complete",
  "params": {
    "ref": {
      "type": "ref/prompt",
      "name": "deployment_review"
    },
    "argument": {
      "name": "environment",
      "value": "st"
    }
  }
}
```

结果最多返回 100 个值，并可以报告 `total` 与 `hasMore`。

应用被引用 prompt 或资源所使用的同一授权边界。示例中的分析师会收到 `development` 和 `staging`。只有操作员能收到 `production`。

生产级补全还需要：

- 输入校验；
- 感知调用者的过滤；
- 客户端的请求防抖（debouncing）；
- 服务端的速率限制；
- 有界的结果数量；
- 不泄露敏感建议值的日志。

补全是辅助，不是发现绕过。

> `completion/complete` provides suggestions for prompt arguments and resource-template arguments. It is useful for interactive forms, but it can leak names that ordinary list methods protect.
> Apply the same authorization boundary used by the referenced prompt or resource. An analyst in the sample receives `development` and `staging`. Only an operator can receive `production`.
> Completion is assistance, not discovery bypass.

## Two Error Layers · 两层错误

把协议错误与工具执行错误分开。

当 MCP 请求无法被正确分发时，使用 JSON-RPC 错误：

- 未知工具名；
- 畸形的请求形状；
- 缺失请求元数据；
- 非法游标。

当调用已到达工具、且工具报告了可操作的失败时，使用 `isError: true` 的完整工具结果：

- 一个报告源不可用；
- 一个日期超出支持范围；
- 一条业务规则拒绝了请求的操作。

模型通常能修复工具执行错误。它们修不了一个违反自身输出 schema 的服务端。

如果工具声明了输出 schema，就在该 schema 之内建模可操作的失败。示例 `route_report` 的失败会返回它被请求的 region，附带 `accepted: false`、人类可读的错误文本和 `isError: true`。

> Keep protocol errors separate from tool execution errors.
> Use a JSON-RPC error when the MCP request cannot be dispatched correctly ... Use a complete tool result with `isError: true` when the invocation reached the tool and the tool reports an actionable failure ...
> Models can often repair a tool execution error. They cannot repair a server that violated its own output schema.

## Build It · 动手造

`code/main.py` 用 Python 标准库构建了这个边界的两侧。

服务端实现：

- 按请求的 MCP 元数据校验；
- 带 tools 与 completions 能力的 `server/discover`；
- 确定性的 `tools/list` 分页；
- 四个工具描述符，其中一个必须被拒绝；
- 数组结构化输出；
- 当前的全部工具内容块类型；
- 一个 Streamable HTTP 一致性门，解码可识别的参数头，并在不匹配时返回 HTTP `400` 加 JSON-RPC `-32020`；
- 经过授权和限流的补全。

客户端实现：

- 描述符准入；
- 全树的 `x-mcp-header` 位置校验与敏感字段策略；
- 精确的「纯可见 ASCII 或 base64 UTF-8」值编码；
- 跟随空字符串的不透明游标循环；
- 参数与结果校验；
- 内容块校验；
- 只含名称、不含值的头审计事件。

那个刻意不安全的描述符是教学数据。它证明一个被拒绝的工具不会阻止有效工具加载。

> `code/main.py` builds both sides of the boundary with the Python standard library.
> The deliberately unsafe descriptor is teaching data. It proves that one rejected tool does not prevent valid tools from loading.

## Use It · 实战用法

从仓库根开始：

```bash
cd phases/13-tools-and-protocols/28-mcp-tool-contracts-and-content/code
python3 main.py
python3 -m unittest discover tests -v
```

演示会打印：被准入的工具、被拒绝的描述符、两个分页请求、结构化数组内容、内容块类型、镜像的头名称、值是否需要编码、HTTP 一致性状态，以及按调用者过滤后的补全值。

> The demo prints admitted tools, the rejected descriptor, both pagination requests, structured array content, content-block types, mirrored header names, whether the value required encoding, the HTTP parity status, and caller-filtered completion values.

## Interactive Lab · 交互实验

打开 `code/main.py` 并定位 `TOOLS`。

1. 把 `tag_catalog.outputSchema.type` 从 `array` 改成 `object`。
2. 运行演示。客户端应拒绝返回的数组。
3. 恢复 schema。
4. 保持第一页的 `nextCursor` 为 `""`，然后让最后一页返回 `nextCursor: None` 而不是省略该字段。
5. 运行测试并比较游标轨迹。
6. 给一个 string 属性加上 `x-mcp-header: "Authorization"`。
7. 确认描述符准入在调用之前拒绝它。
8. 尝试包含 Unicode、换行符、首尾空格以及字面文本 `=?base64?SGVsbG8=?=` 的 `region` 值。解码每个发出的头，证明原始值被精确保留。
9. 把注解移到 `oneOf`、`items` 或某个 `$ref` 定义之下。确认每个描述符都被拒绝，即使演示从不使用那个分支。
10. 移除可识别的头或改动其解码后的值。确认 HTTP 边界返回状态 `400` 和 JSON-RPC 码 `-32020`。

重点不是背下一个 JSON 形状。而是观察每一道门在拥有它的那个边界上失败。

> The point is not to memorize a JSON shape. It is to watch each gate fail at the boundary that owns it.

## Practice Lab · 练习实验

用一个 `search_evidence` 工具扩展这个契约实验。

要求：

1. 它的输入 schema 接受 `query`、`limit` 和一个安全的 `region` 路由字段。
2. 它的输出 schema 是对象数组，每个对象有 `uri`、`title` 和 `score`。
3. 结果包含兼容性文本和每个条目一个资源链接。
4. 参数拒绝未知属性。
5. `limit` 由应用层校验设定边界。
6. 对某个 URI 无访问权的调用者，永远无法通过补全或工具输出看到那个 URI。
7. 测试包括一个不合规范（nonconforming）的 score、一个非法头注解和一个两页列表。
8. 头值测试覆盖可见 ASCII、Unicode、控制字符、空白、哨兵样文本，以及 JavaScript 安全整数的两个边界。
9. HTTP 夹具接受大小写不敏感的头名称，但对缺失或不匹配的可识别值返回状态 `400` 和码 `-32020`。

> Extend the contract lab with a `search_evidence` tool ...
> Header-value tests cover visible ASCII, Unicode, control characters, whitespace, sentinel-looking text, and both JavaScript-safe integer bounds.
> The HTTP fixture accepts case-insensitive header names but rejects missing or mismatched recognized values with status `400` and code `-32020`.

## Shipped Artifact · 交付产物

`outputs/skill-mcp-contract-reviewer.md` 是一个扁平、可复用的评审技能。给它一个工具描述符、示例结果、分页行为和补全策略，它会返回一份准入决定、结果校验计划、头策略和具体的失败测试。

> `outputs/skill-mcp-contract-reviewer.md` is a flat, reusable review skill. Give it a tool descriptor, sample results, pagination behavior, and completion policy. It returns an admission decision, result-validation plan, header policy, and concrete failure tests.

## Verify It · 验证

当下列陈述全部为真时，本课完成：

- `tools/list` 在重复调用时返回相同的逻辑顺序。
- 当 `nextCursor` 是 `""` 时，客户端会发起第二个请求。
- 不安全的敏感头描述符被排除，其他工具仍然可用。
- 一个数组通过它的数组输出 schema。
- 一个对象无法通过同一个数组 schema。
- 错误结果不能省略或违反已发布的输出 schema。
- 文本、图像、音频、资源链接和内嵌资源块都能通过校验。
- 头审计事件包含名称而不包含值。
- 纯可见 ASCII 保持纯文本；Unicode、控制字符、带填充、空值和哨兵样值都能通过精确的 base64 UTF-8 编码完整往返。
- 超出 JavaScript 安全范围的镜像整数被拒绝。
- `oneOf`、`items`、嵌套对象、`$ref` 定义或输出 schema 之下的注解在准入时被拒绝。
- 大小写不敏感的可识别头名称只在解码值与正文精确匹配时通过；缺失或不匹配的副本产生 HTTP `400` 和 JSON-RPC `-32020`。
- 分析师的补全永不返回 `production`。
- 工具失败使用 `isError: true`；畸形的协议调用使用 JSON-RPC `error`。

> The lesson is complete when these statements are true ...

## Production Failure Modes · 生产故障模式

| 故障 | 学习者看到什么 | 正确响应 |
|---------|-----------------------|------------------|
| 客户端假设对象输出 | 合法数组失败或被静默包装 | 对照已发布的 schema 校验，不使用只认对象的类型 |
| 空游标被当成 false | 最后几页消失 | 只要 `nextCursor` 存在且非 null 就继续 |
| 敏感值被镜像 | 秘密出现在代理、WAF 或追踪数据里 | 拒绝描述符，把秘密放在受保护的请求数据中 |
| 原始 Unicode 或空白被镜像 | 网关与源站不一致，或值被归一化 | 使用精确的 base64 UTF-8 哨兵编码，解码后再比较 |
| 注解藏在 schema 分支里 | 客户端在准入时漏掉路由元数据 | 遍历整棵 schema 树，只允许直接顶层属性 |
| 大整数被镜像 | JavaScript 中间方对路由值做舍入 | 拒绝 JavaScript 安全整数范围之外的值 |
| 头与正文不一致 | 网关路由到一个目标，而源站执行另一个 | 在分发之前拒绝，返回 HTTP `400` 和 JSON-RPC `-32020` |
| 输出 schema 被忽略 | 下游代码消费损坏的结构 | 在模型或应用使用之前校验 |
| 资源链接被自动信任 | 调用者跟随一个未授权的 URI | 对每一次资源读取重新授权 |
| 补全共享全局建议 | 隐藏的租户名泄露 | 按调用者、引用和授权过滤 |
| 工具注解被当成策略 | 破坏性操作绕过确认 | 在注解之外执行授权与审批 |
| 一个畸形工具破坏发现 | 整个服务端变得不可用 | 拒绝坏的描述符，独立准入有效工具 |

> Client assumes object output ... Validate against the published schema without object-only types.
> Header and body disagree ... Reject before dispatch with HTTP `400` and JSON-RPC `-32020`.
> One malformed tool breaks discovery ... Reject the bad descriptor and admit valid tools independently.

## Capstone Connection · 毕业项目关联

Phase 13 的毕业项目需要一个能合并多个服务端工具的网关。本课提供它的准入核心。

用这个产物给四份毕业证据打分：

- 确定且完整的分页发现；
- 模型暴露之前的描述符校验；
- 经过校验的结构化输出加上有界的内容块；
- 保有授权边界的补全与路由元数据。

不要只凭一次成功的 `tools/call` 就宣称网关兼容。捕获描述符、分页轨迹、被准入的工具集、被拒绝的工具集和一份经过校验的结果。

> The Phase 13 capstone needs a gateway that can merge tools from several servers. This lesson provides its admission core.
> Do not claim gateway compatibility from a successful `tools/call` alone. Capture the descriptor, page trace, admitted tool set, rejected tool set, and one validated result.

## Key Terms · 术语表

| 术语 | 含义 |
|------|---------|
| `inputSchema` | 定义工具可接受参数的 JSON Schema 对象 |
| `outputSchema` | 定义 `structuredContent` 的可选 JSON Schema |
| `structuredContent` | 工具结果产出的任意 JSON 值 |
| 内容块（Content block） | 有类型的 text、image、audio、资源链接或内嵌资源 |
| `x-mcp-header` | 把原始类型参数镜像进 Streamable HTTP 元数据的 schema 注解 |
| 不透明游标（Opaque cursor） | 服务端签发的分页令牌，客户端不解释其值 |
| 补全引用（Completion reference） | 其参数正在被补全的 prompt 名称或资源 URI/模板 |
| 准入（Admission） | 客户端对发现的描述符做出暴露或拒绝的决定 |

## Further Reading · 延伸阅读

- [MCP Tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [MCP Completion](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/completion)
- [MCP Pagination](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/pagination)
- [MCP Streamable HTTP Parameter Headers](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http#custom-headers-from-tool-parameters)
