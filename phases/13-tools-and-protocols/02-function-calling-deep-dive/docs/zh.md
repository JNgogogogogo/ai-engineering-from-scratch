# Function Calling Deep Dive · 函数调用深入——OpenAI、Anthropic、Gemini

> The three frontier providers converged on the same tool-call loop in 2024 and then diverged on everything else. OpenAI uses `tools` and `tool_calls`. Anthropic uses `tool_use` and `tool_result` blocks. Gemini uses `functionDeclarations` and unique-id correlation. This lesson diffs the three side by side so code that ships on one provider does not break when you port it.

**Type:** Build
**Languages:** Python（仅标准库，schema 转换器）
**Prerequisites:** Phase 13 · 01（工具接口）
**Time:** 约 75 分钟

## Learning Objectives · 学习目标

- 说出 OpenAI、Anthropic、Gemini 三家函数调用负载之间的三个形状差异（声明 declaration、调用 call、结果 result）。
- 把同一个工具声明在三种供应商格式之间来回翻译，并预测严格模式（strict mode）约束会在哪里不同。
- 在每家供应商中使用 `tool_choice` 来强制、禁止或自动选择工具调用。
- 了解各家供应商的硬限制（工具数量、schema 深度、参数长度），以及超限时各自发出的错误特征。

> State the three shape differences between OpenAI, Anthropic, and Gemini function-calling payloads (declaration, call, result).
> Translate one tool declaration across all three provider formats and predict where strict-mode constraints will differ.
> Use `tool_choice` in each provider to force, forbid, or auto-pick tool calls.
> Know the per-provider hard limits (tool count, schema depth, argument length) and the error signatures each one emits when limits are violated.

## The Problem · 问题在哪

函数调用请求的形状因供应商而异。三个来自 2026 生产栈的具体例子：

**OpenAI Chat Completions / Responses API。** 你传入 `tools: [{type: "function", function: {name, description, parameters, strict}}]`。模型的响应里包含 `choices[0].message.tool_calls: [{id, type: "function", function: {name, arguments}}]`，其中 `arguments` 是一个需要你自己解析的 JSON 字符串。严格模式（`strict: true`）通过受限解码强制 schema 合规。

**Anthropic Messages API。** 你传入 `tools: [{name, description, input_schema}]`。响应以 `content: [{type: "text"}, {type: "tool_use", id, name, input}]` 的形式返回。`input` 已经解析好了（是对象，不是字符串）。你用一条新的 `user` 消息回复，内含一个 `{type: "tool_result", tool_use_id, content}` 块。

**Google Gemini API。** 你传入 `tools: [{functionDeclarations: [{name, description, parameters}]}]`（嵌套在 `functionDeclarations` 之下）。响应以 `candidates[0].content.parts: [{functionCall: {name, args, id}}]` 的形式到达，其中 `id` 在 Gemini 3 及以上版本中唯一，用于并行调用关联。你用 `{functionResponse: {name, id, response}}` 回复。

同一个循环。不同的字段名、不同的嵌套、不同的字符串-vs-对象约定、不同的关联机制。一个在 OpenAI 上写好天气 agent 的团队，把它移植到 Anthropic 要花两天管道工程，再移植到 Gemini 还要一天。

本课构建一个转换器（translator），把三种格式统一成一份规范（canonical）工具声明，并在边缘做路由。Phase 13 · 17 会把同样的模式泛化成一个 LLM 网关。

> The shape of a function-calling request differs by provider. Three concrete examples from 2026 production stacks: ... Same loop. Different field names, different nesting, different string-vs-object conventions, different correlation mechanisms. ... This lesson builds a translator that unifies the three formats into one canonical tool declaration and routes at the edge.

## The Concept · 概念

### The common structure · 公共结构

每家供应商都需要五样东西：

1. **工具清单。** 每个工具的 name、description 和输入 schema。
2. **工具选择（tool choice）。** 强制某个特定工具、禁止工具，或让模型自己决定。
3. **调用输出（call emission）。** 指名工具与参数的结构化输出。
4. **调用 id。** 把响应关联到正确的调用（并行时很关键）。
5. **结果注入（result injection）。** 一条把结果系回调用的消息或块。

> Every provider needs five things: ... **Tool choice.** Force a specific tool, forbid tools, or let the model decide. ... **Call id.** Correlate the response to the right call (matters for parallel). ... **Result injection.** A message or block that ties the result back to the call.

### Shape diffs, field by field · 形状差异，逐字段对比

| 对比维度 | OpenAI | Anthropic | Gemini |
|--------|--------|-----------|--------|
| 声明信封 | `{type: "function", function: {...}}` | `{name, description, input_schema}` | `{functionDeclarations: [{...}]}` |
| Schema 字段 | `parameters` | `input_schema` | `parameters` |
| 响应容器 | assistant 消息上的 `tool_calls[]` | 类型为 `tool_use` 的 `content[]` | 类型为 `functionCall` 的 `parts[]` |
| 参数类型 | 字符串化的 JSON | 已解析的对象 | 已解析的对象 |
| Id 格式 | `call_...`（OpenAI 生成） | `toolu_...`（Anthropic） | UUID（Gemini 3+） |
| 结果块 | role `tool`、`tool_call_id` | `user` 内含 `tool_result`、`tool_use_id` | 带匹配 `id` 的 `functionResponse` |
| 强制某工具 | `tool_choice: {type: "function", function: {name}}` | `tool_choice: {type: "tool", name}` | `tool_config: {function_calling_config: {mode: "ANY"}}` |
| 禁止工具 | `tool_choice: "none"` | `tool_choice: {type: "none"}` | `mode: "NONE"` |
| 严格 schema | `strict: true` | schema 即契约（始终强制） | 请求级的 `responseSchema` |

### Limits you will actually hit · 你真的会撞上的限制

- **OpenAI。** 每个请求 128 个工具。Schema 深度 5。参数字符串 <= 8192 字节。严格模式要求：不能有 `$ref`，不能有相互重叠的 `oneOf`/`anyOf`/`allOf`，每个属性都必须列进 `required`。
- **Anthropic。** 每个请求 64 个工具。Schema 深度实际上无上限，但实用上限是 10。没有严格模式开关；schema 就是契约，模型大体上会遵守。
- **Gemini。** 每个请求 64 个函数。Schema 类型是 OpenAPI 3.0 子集（与 JSON Schema 2020-12 有轻微分歧）。Gemini 3 起并行调用带唯一 id。

> **OpenAI.** 128 tools per request. Schema depth 5. Argument string <= 8192 bytes. Strict mode requires no `$ref`, no `oneOf`/`anyOf`/`allOf` with overlap, every property listed in `required`. ... **Gemini.** 64 functions per request. Schema types are OpenAPI 3.0 subset (slight divergence from JSON Schema 2020-12). Parallel calls unique-id since Gemini 3.

### `tool_choice` behavior · `tool_choice` 的行为

三家都支持的三种模式，名字各不相同。

- **Auto（自动）。** 模型自己挑：调工具还是回文本。默认。
- **Required / Any（必须调用）。** 模型必须至少调用一个工具。
- **None（禁止）。** 模型不得调用工具。

另加每家一个独有模式：

- **OpenAI。** 按名称强制某个特定工具。
- **Anthropic。** 按名称强制某个特定工具；`disable_parallel_tool_use` 标志区分单调用与多调用。
- **Gemini。** `mode: "VALIDATED"` 让每个响应都过一遍 schema 校验器，不管模型本意如何。

> Three modes everyone supports, named differently. ... Plus one mode unique to each provider: ... **Gemini.** `mode: "VALIDATED"` routes every response through a schema validator regardless of model intent.

### Parallel calls · 并行调用

OpenAI 的 `parallel_tool_calls: true`（默认）会在一条 assistant 消息里输出多个调用。你把它们全部运行，然后用一条批量的 tool 角色消息回复，内含每个 `tool_call_id` 一条记录。Anthropic 历史上只做单调用；`disable_parallel_tool_use: false`（Claude 3.5 起默认）开启多调用。Gemini 2 允许并行调用但不给稳定 id；Gemini 3 加入 UUID，让乱序返回的响应能干净地关联起来。

> OpenAI's `parallel_tool_calls: true` (default) emits multiple calls in one assistant message. You run them all and reply with a batched tool-role message containing one entry per `tool_call_id`. ... Gemini 2 allowed parallel calls but did not give stable ids; Gemini 3 adds UUIDs so out-of-order responses correlate cleanly.

### Streaming · 流式调用

三家都支持流式工具调用。线上格式不同：

- **OpenAI。** `tool_calls[i].function.arguments` 的增量 delta 块逐步到达。你持续累积，直到 `finish_reason: "tool_calls"`。
- **Anthropic。** block-start / block-delta / block-stop 事件。`input_json_delta` 块携带部分参数。
- **Gemini。** `streamFunctionCallArguments`（Gemini 3 新增）输出带 `functionCallId` 的块，多个并行调用得以交错。

> All three support streamed tool calls. The wire format differs: ... **Anthropic.** Block-start / block-delta / block-stop events. `input_json_delta` chunks carry partial arguments. ... **Gemini.** `streamFunctionCallArguments` (new in Gemini 3) emits chunks with a `functionCallId` so multiple parallel calls can interleave.

Phase 13 · 03 深入并行 + 流式重组。本课聚焦声明与单调用形状。

### Errors and repair · 错误与修复

参数非法的错误长得也不一样。

- **OpenAI（非严格）。** 模型返回 `arguments: "{bad json}"`，你的 JSON 解析失败，你注入一条错误消息再重新调用。
- **OpenAI（严格）。** 校验发生在解码期间；非法 JSON 不可能出现，但可能出现 `refusal`。
- **Anthropic。** `input` 里可能包含意料之外的字段；schema 只是建议性的。要在服务端自己校验。
- **Gemini。** OpenAPI 3.0 的怪癖：对象字段上的 `enum` 会被静默忽略；要自己校验。

> Invalid-argument errors look different too. ... **OpenAI (strict).** Validation happens during decoding; invalid JSON is impossible but `refusal` can appear. ... **Gemini.** OpenAPI 3.0 quirk: `enum` on object fields silently ignored; validate yourself.

### The translator pattern · 转换器模式

你的代码里，一份规范工具声明长这样（形状你自己挑）：

```python
Tool(
    name="get_weather",
    description="Use when ...",
    input_schema={"type": "object", "properties": {...}, "required": [...]},
    strict=True,
)
```

三个小函数把它翻译成三种供应商形状。`code/main.py` 里的测试支架做的正是这件事，然后把一个假的工具调用在每种供应商的响应形状里走一遍往返。不需要网络——本课教的是形状，不是 HTTP。

生产团队会把这个转换器包进 `AbstractToolset`（Pydantic AI）、`UniversalToolNode`（LangGraph）或 `BaseTool`（LlamaIndex）。Phase 13 · 17 交付一个网关，在三者任一之前暴露 OpenAI 形状的 API。

> Three tiny functions translate it to the three provider shapes. The harness in `code/main.py` does exactly this, then round-trips a fake tool call through each provider's response shape. No network required — this lesson teaches the shapes, not the HTTP. ... Production teams wrap this translator in `AbstractToolset` (Pydantic AI), `UniversalToolNode` (LangGraph), or `BaseTool` (LlamaIndex).

```figure
function-call-args
```

## Use It · 实战用法

`code/main.py` 定义一个规范的 `Tool` dataclass 和三个转换器，分别输出 OpenAI、Anthropic、Gemini 的声明 JSON。接着它把每种形状的手工构造供应商响应解析回同一个规范调用对象，证明皮肤之下的语义完全相同。跑一遍，把三份声明并排 diff 一下。

值得关注的点：

- 三份声明块只在信封和字段名上有差别。
- 三份响应块的差别在于调用住在哪里（顶层的 `tool_calls`、`content[]` 块、`parts[]` 条目）。
- 一个 `canonical_call()` 函数从全部三种响应形状中提取 `{id, name, args}`。

> `code/main.py` defines one canonical `Tool` dataclass and three translators that emit the OpenAI, Anthropic, and Gemini declaration JSON. ... Run it and diff the three declarations side by side. ... One `canonical_call()` function extracts `{id, name, args}` from all three response shapes.

## Ship It · 交付

本课产出 `outputs/skill-provider-portability-audit.md`。给定一个针对某家供应商的函数调用集成，这个技能（skill）会产出一份可移植性审计：它依赖了哪些供应商限制、哪些字段需要重命名、以及移植到其他每家供应商时会坏掉什么。

> This lesson produces `outputs/skill-provider-portability-audit.md`. Given a function-calling integration against one provider, the skill produces a portability audit: which provider limits it relies on, which fields need renaming, and what breaks when ported to each other provider.

## Exercises · 练习

1. 运行 `code/main.py`，验证三份供应商声明 JSON 序列化的都是同一个底层 `Tool` 对象。修改规范工具，加入一个 enum 参数，确认只有 Gemini 转换器需要处理 OpenAPI 怪癖。

2. 为每家供应商添加一个 `ListToolsResponse` 解析器，提取模型在 `list_tools` 或发现调用之后返回的工具清单。OpenAI 原生没有这个；记录这种不对称。

3. 实现 `tool_choice` 转换：把规范的 `ToolChoice(mode="force", tool_name="x")` 映射进三种供应商形状。然后映射 `mode="any"` 和 `mode="none"`。对照本课的差异表检查。

4. 三选一供应商，把它的函数调用指南从头读到尾。找出它的 schema 规范里另外两家不支持的一个字段。候选：OpenAI `strict`、Anthropic `disable_parallel_tool_use`、Gemini `function_calling_config.allowed_function_names`。

5. 写一个测试向量：一个参数违反声明 schema 的工具调用。把它送进每家供应商的校验器（用第 01 课的标准库实现当替身即可），记录哪些错误触发。写下生产上为了严格性你会选哪家供应商。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 它实际是什么 |
|------|----------------|------------------------|
| Function calling（函数调用） | 「工具使用」 | 供应商级的结构化工具调用输出 API |
| Tool declaration（工具声明） | 「工具规格」 | name + description + JSON Schema 输入负载 |
| `tool_choice` | 「强制 / 禁止」 | Auto / required / none / 指定名称等模式 |
| Strict mode（严格模式） | 「schema 强制」 | OpenAI 的开关，约束解码以匹配 schema |
| `tool_use` block | 「Anthropic 的调用形状」 | 带 id、name、input 的内联内容块 |
| `functionCall` part | 「Gemini 的调用形状」 | `parts[]` 中含 name、args、id 的条目 |
| Arguments-as-string（字符串化参数） | 「字符串化的 JSON」 | OpenAI 把参数作为 JSON 字符串而非对象返回 |
| Parallel tool calls（并行工具调用） | 「一轮内扇出」 | 一条 assistant 消息里的多个工具调用 |
| Refusal（拒绝） | 「模型婉拒」 | 仅严格模式下出现的 refusal 块，代替一次调用 |
| OpenAPI 3.0 subset（OpenAPI 3.0 子集） | 「Gemini 的 schema 怪癖」 | Gemini 使用一种类 JSON Schema 方言，略有差异 |

## Further Reading · 延伸阅读

- [OpenAI — Function calling guide](https://platform.openai.com/docs/guides/function-calling) —— 权威参考，含严格模式与并行调用
- [Anthropic — Tool use overview](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview) —— `tool_use` 与 `tool_result` 块语义
- [Google — Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling) —— 并行调用、唯一 id 与 OpenAPI 子集
- [Vertex AI — Function calling reference](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling) —— Gemini 的企业级入口
- [OpenAI — Structured outputs](https://platform.openai.com/docs/guides/structured-outputs) —— 严格模式 schema 强制的细节
