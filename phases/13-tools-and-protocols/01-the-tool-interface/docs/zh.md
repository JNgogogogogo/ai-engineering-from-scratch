# The Tool Interface · 工具接口——为什么 Agent 需要结构化输入输出

> A language model produces tokens. A program takes actions. The gap between those two is the tool interface: a contract that lets the model request an action and the host execute it. Every 2026 stack — function calling on OpenAI, Anthropic, and Gemini; MCP's `tools/call`; A2A's task parts — is a different encoding of the same four-step loop. This lesson names the loop and shows the minimum machinery to run it.

**Type:** Learn
**Languages:** Python（仅标准库，不调用 LLM）
**Prerequisites:** Phase 11（LLM 补全 API）
**Time:** 约 45 分钟

## Learning Objectives · 学习目标

- 解释为什么一个只能生成文本的 LLM 无法凭自身对现实世界采取行动。
- 画出工具调用的四步循环（describe → decide → execute → observe，描述 → 决策 → 执行 → 观察），并说出每一步由谁负责。
- 把一个工具描述写成三个部分：名称、JSON Schema 输入，以及一个确定性的执行器（executor）函数。
- 区分纯工具（pure tool）与后果型工具（consequential tool），并说明这一区分对安全为什么重要。

> Explain why an LLM that can only generate text cannot, on its own, take actions against the real world.
> Draw the four-step tool-call loop (describe → decide → execute → observe) and name who owns each step.
> Write a tool description as three parts: name, JSON Schema input, and a deterministic executor function.
> Distinguish pure and side-effecting tools and state why the split matters for safety.

## The Problem · 问题在哪

一个 LLM 输出的是「下一个 token 的概率分布」。这就是它全部的输出面。你问一个聊天模型「现在班加罗尔的天气怎么样」，它能写出一个听起来合理的句子，但它没办法拨号接入天气 API。那句话可能碰巧正确，也可能是三天前的陈旧信息。

弥合这道鸿沟正是工具接口（tool interface）存在的目的。宿主程序（host）——你的 agent 运行时、Claude Desktop、ChatGPT、Cursor，或一个自定义脚本——向模型 advertise 出一份可调用工具的清单。模型在判断需要执行某个动作时，输出一个结构化负载（payload），指名工具及其参数。宿主解析该负载，真正地运行工具，再把结果回喂。循环持续进行，直到模型判断不再需要调用。

这套契约的第一个版本于 2023 年 6 月以 OpenAI 的 `functions` 参数问世。Anthropic 在 Claude 2.1 中跟进 `tool_use` 块。Gemini 几个月后加入 `functionDeclarations`。如今每家供应商暴露的都是同一个形状：进去一份 JSON Schema 类型化的工具清单，出来一个 JSON 负载的工具调用。模型上下文协议（Model Context Protocol，2024 年 11 月）把这个契约泛化，让一份工具注册表（registry）服务所有模型。A2A（2026 年 4 月，v1.0）把同一个原语叠加到 agent 对 agent 的委托上。

四步循环是这一切底下不变的东西。Phase 13 的其余一切，都是对它的展开。

> An LLM emits a probability distribution over the next token. That is the entire output surface. ... Closing that gap is the purpose of the tool interface. ... The four-step loop is the invariant underneath all of these. Everything else in Phase 13 is an elaboration.

## The Concept · 概念

### Step one: describe · 第一步：描述

宿主用三个字段声明每个工具。

- **Name（名称）。** 一个稳定、机器可读的标识符。用 `get_weather`，而不是 "weather thing"。
- **Description（描述）。** 一段自然语言简介。「当用户询问某个城市的实时状况时使用。不要用于历史数据。」
- **Input schema（输入模式）。** 一个 JSON Schema 对象（draft 2020-12），描述工具的参数。

模型收到这份清单。现代供应商会用各家特定的模板把这些声明序列化进 system prompt，所以作为调用方，你只需要面对结构化的形式。

> The host declares each tool with three fields. ... The model receives the list. Modern providers serialize these declarations into the system prompt using a provider-specific template, so you as the caller only deal with the structured form.

### Step two: decide · 第二步：决策

给定用户消息和可用工具，模型在三种行为中选择其一。

1. **直接以文本回答。** 不调用工具。
2. **调用一个或多个工具。** 输出结构化的调用对象。在 `parallel_tool_calls: true` 下（OpenAI 与 Gemini 默认开启，Anthropic 需选择加入），模型可以在一轮中输出多个调用。
3. **拒绝。** 严格模式（strict mode）的结构化输出可以产生一个类型化的 `refusal` 块，而不是一次调用。

工具调用负载有三个稳定字段：调用 `id`、工具 `name`，以及一个 JSON `arguments` 对象。id 的存在，是为了让宿主能把稍后的结果与具体的调用关联起来——当并行调用乱序返回时，这一点至关重要。

> Given the user's message and the available tools, the model chooses one of three behaviors. ... A tool call payload has three stable fields: a call `id`, a tool `name`, and a JSON `arguments` object. The id exists so the host can correlate the later result with the specific call, which matters when parallel calls come back out of order.

### Step three: execute · 第三步：执行

宿主收到调用，按声明的 schema 校验参数，然后运行执行器。参数非法意味着模型幻觉出了某个字段，或用错了类型——这在弱模型上是非常常见的失败模式。面对非法参数，生产级宿主三选一：快速失败并把错误暴露给模型；用受限解析器修复 JSON；或带着校验错误重新请求模型。

执行器本身就是普通代码。Python、TypeScript、一条 shell 命令、一次数据库查询。它产出一个结果，通常是字符串，但也可以是任何 JSON 值，或一个结构化内容块（在 MCP 中是文本、图像或资源引用）。结果必须可序列化。

> The host receives the call, validates arguments against the declared schema, and runs the executor. Invalid arguments mean the model hallucinated a field or used the wrong type — a very common failure mode on weak models. ... The executor itself is ordinary code. ... The result must be serializable.

### Step four: observe · 第四步：观察

宿主把工具结果追加进对话（作为一条带匹配 `id` 的 `tool` 角色消息），然后再次调用模型。模型此时在上下文中有了工具输出，可以给出最终答案，或请求更多调用。如此往复，直到模型不再输出调用，或宿主触及迭代次数的安全上限。

> The host appends the tool result to the conversation (as a `tool` role message with matching `id`) and re-invokes the model. The model now has the tool output in context and can produce a final answer or request more calls. ... This continues until the model stops emitting calls or the host hits a safety limit on iteration count.

### The trust split · 信任分界

从安全角度看，工具分两种口味。

- **纯工具（Pure）。** 只读、确定、无副作用。`get_weather`、`search_docs`、`get_current_time`。可以放心地试探性调用。
- **后果型工具（Consequential）。** 会修改状态、花钱、触碰用户数据。`send_email`、`delete_file`、`execute_trade`。必须有门禁（gate）。

Meta 2026 年的 agent 安全「Rule of Two」说：单轮之中，不可信输入、敏感数据、后果型动作三者最多同时出现两个。工具接口正是你执行这条规则的地方——靠拒绝调用、要求用户确认、或提升权限范围。完整的安全章节见 Phase 13 · 15，agent 级权限策略见 Phase 14 · 09。

> Tools come in two flavors that matter for safety. ... Meta's 2026 "Rule of Two" for agent security says a single turn may combine at most two of: untrusted input, sensitive data, consequential action. The tool interface is where you enforce that rule — by rejecting calls, requiring user confirmation, or escalating scopes. See Phase 13 · 15 for the full security chapter and Phase 14 · 09 for agent-level permission policies.

### Where the loop lives · 循环住在哪里

| 场景 | 谁描述 | 谁决策 | 谁执行 |
|---------|---------------|-------------|--------------|
| 单轮函数调用（function calling，OpenAI/Anthropic/Gemini） | 应用开发者 | LLM | 应用开发者 |
| MCP | MCP 服务器 | 经 MCP 客户端的 LLM | MCP 服务器 |
| A2A | Agent Card 发布者 | 发起调用的 agent | 被调用的 agent |
| 网页浏览器（函数调用 agent） | 浏览器扩展 / WebMCP | LLM | 浏览器运行时 |

处处都是同样的四步。变的只是列名；结构不变。

> Everywhere, the same four steps. The column names change; the structure does not.

### Why not just prompt the model to emit JSON? · 为什么不直接提示模型输出 JSON？

「让模型用 JSON 回复」是函数调用出现之前的模式。它在前沿模型上约有 5% 到 15% 的失败率，在小模型上高得多。失败形态包括缺花括号、尾随逗号、幻觉字段、类型错误。于是你需要一次 JSON 修复、一次重试，或一个受限解码器。

原生函数调用更好，理由有三。第一，供应商在训练时就用这个确切的调用形状对模型做了端到端训练，所以严格模式下合法 JSON 率能爬升到 98% 到 99%。第二，调用负载待在它自己的协议槽位里，而不是自由文本之内——工具调用因此绝不会泄漏进用户可见的回复。第三，供应商用受限解码（constrained decoding）强制 schema 合规（OpenAI 的 strict mode、Anthropic 的 `tool_use`、Gemini 的 `responseSchema`）。输出保证通过校验。

Phase 13 · 02 并排走读三家供应商的 API。Phase 13 · 04 深入结构化输出。

> "Ask the model to reply in JSON" was the pre-function-calling pattern. It fails ~5 to 15 percent of the time on frontier models and far more on smaller models. ... Native function calling is better for three reasons. ... The output is guaranteed to validate.

### Circuit breakers · 熔断器

当模型停止输出调用，或宿主达到最大轮数，循环就会终止。生产级宿主把这个上限设在 5 到 20 轮之间。超过之后，你几乎肯定陷入了模型自己走不出去的循环。Claude Code 默认 20 轮；OpenAI Assistants 默认 10 轮；Cursor 的 agent 模式默认 25 轮。

另一个选项——无界循环——每隔半年就会以「agent 一晚上烧掉 400 美元 API 费」的复盘帖形式冒出来。不要不做上限就上线。

Phase 14 · 12 深入讲解错误恢复与自愈；Phase 17 讲生产级限流。

> The loop terminates when the model stops emitting calls or the host hits a maximum turn count. Production hosts set this to between 5 and 20 turns. ... The alternative — unbounded loops — shows up every six months as "agent spent $400 in API calls overnight" post-mortems. Do not ship without a bound.

### Where Phase 13 goes from here · Phase 13 接下来去哪

- 第 02 到 05 课打磨供应商级的工具调用表面。
- 第 06 到 14 课把这个循环泛化为 MCP。
- 第 15 到 18 课防御这个循环，对抗恶意服务器、对抗性用户和未认证的远程认证面。
- 第 19 到 22 课把这个模式扩展到 agent 间协作、可观测性、路由与打包。
- 第 23 课用上全部原语，交付一个完整生态。

剩下的每一课都是这个四步循环的一次展开。把它作为不变量记在脑子里。

```figure
tp-tool-loop
```

> Lessons 02 through 05 polish the provider-level tool-call surface. ... Every remaining lesson is an elaboration of this four-step loop. Hold it in mind as the invariant.

## Use It · 实战用法

`code/main.py` 在没有 LLM 的情况下运行四步循环。一个假的「决策器」函数通过对用户消息做模式匹配来模拟模型；而执行器、schema 校验器和观察环节的测试支架都是真的。跑一遍，看看带可打印中间状态的完整请求/响应编排，然后在后续课程里把假决策器换成任何真实供应商。

值得关注的点：

- 工具注册表（registry）为每个工具保存三个字段：name、description、schema，外加一个执行器引用。
- 校验器是一个只用标准库实现的最小 JSON Schema 子集（types、required、enum、min/max）。Phase 13 · 04 会交付一个更完整的。
- 循环把迭代次数上限设为 5。生产级 agent 需要的恰恰是这种熔断器。

> `code/main.py` runs the four-step loop without an LLM. A fake "decider" function simulates the model by pattern-matching on the user message; the executor, schema validator, and observe-step harness are real. ... The loop bounds iteration count at five. Production agents need exactly this kind of circuit breaker.

## Ship It · 交付

本课产出 `outputs/skill-tool-interface-reviewer.md`。给定一份工具定义草稿（name + description + schema + executor 概要），这个技能（skill）会从「循环适配度」角度审计它：name 是否机器稳定、description 是否是一份完整的用法简报、schema 是否正确使用 JSON Schema 2020-12，以及 pure 与 consequential 的分类是否显式。

> This lesson produces `outputs/skill-tool-interface-reviewer.md`. Given a draft tool definition (name + description + schema + executor outline), the skill audits it for loop fitness: is the name machine-stable, is the description a complete usage brief, does the schema use JSON Schema 2020-12 correctly, and is the pure-vs-consequential classification explicit.

## Exercises · 练习

1. 给 `code/main.py` 增加第四个工具 `get_stock_price(ticker)`。把它的描述写成 "Use when the user asks for a current stock price by ticker. Do not use for historical prices or market summaries."。运行测试支架，确认假决策器会把提到股票代码的查询路由到新工具。

2. 弄坏 schema 校验器。传入一个 `arguments` 对象缺失必填字段的调用，确认宿主在执行之前就拒绝它。然后传入一个带额外未知字段的调用。做判断：宿主应该拒绝还是忽略？用安全论证为你的选择辩护。

3. 把测试支架中的每个工具分类为 pure 或 consequential。给需要标记的注册表条目加上 `consequential: true` 标志，并修改循环：每当选中一个 consequential 工具，就打印一行「would confirm with user」（将向用户请求确认）。这就是每个生产级宿主都需要的确认门禁的雏形。

4. 在纸上画出四步循环，并按你最喜欢的客户端（Claude Desktop、Cursor、ChatGPT 或自建栈）填好上面的供应商表格。与 Phase 13 · 06 的 MCP 专属变体交叉对照。

5. 从头到尾读一遍 OpenAI 的函数调用指南。找出那个出现在请求里、却没有出现在本文四步循环中的字段。解释它增加了什么，以及为什么它是「便利」而非「必需」。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 它实际是什么 |
|------|----------------|------------------------|
| Tool（工具） | 「模型能调用的东西」 | 名称 + JSON Schema 类型化输入 + 执行器函数的三元组 |
| Function calling（函数调用） | 「原生工具使用」 | 供应商级 API 支持，让模型输出结构化工具调用而非散文 |
| Tool call（工具调用） | 「模型的行动请求」 | 模型输出的带 `id`、`name`、`arguments` 的 JSON 负载 |
| Tool result（工具结果） | 「工具返回的东西」 | 执行器的输出，包进一条带匹配 id 的 `tool` 角色消息 |
| Parallel tool calls（并行工具调用） | 「一次多个调用」 | 一轮模型消息中的多个调用对象，相互独立、可凭 id 排序 |
| Strict mode（严格模式） | 「保证 JSON」 | 受限解码，强制模型输出通过声明 schema 的校验 |
| Pure tool（纯工具） | 「只读工具」 | 无副作用；可安全重复运行 |
| Consequential tool（后果型工具） | 「动作工具」 | 修改外部状态；需要门禁、审计或用户确认 |
| Four-step loop（四步循环） | 「工具调用循环」 | describe → decide → execute → observe |
| Host（宿主） | 「agent 运行时」 | 持有工具注册表、调用模型、运行执行器的程序 |

## Further Reading · 延伸阅读

- [OpenAI — Function calling guide](https://platform.openai.com/docs/guides/function-calling) —— OpenAI 风格工具声明与调用形状的权威参考
- [Anthropic — Tool use overview](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview) —— Claude 的 `tool_use` / `tool_result` 块格式
- [Google — Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling) —— Gemini 中的 `functionDeclarations` 与并行调用语义
- [Model Context Protocol — Specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28) —— 工具接口当前的无状态、供应商无关泛化
- [JSON Schema — 2020-12 release notes](https://json-schema.org/draft/2020-12/release-notes) —— 每个现代工具 API 都在说的 schema 方言
