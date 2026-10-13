# Parallel Tool Calls and Streaming with Tools · 并行工具调用与工具流式传输

> Three independent weather lookups serialized is three round trips. Run them in parallel and total time collapses to the slowest single call. Every frontier provider now emits multiple tool calls in a single turn. The payoff is real; the plumbing is subtle. This lesson walks both halves: the parallel fan-out and the streamed-argument reassembly, with emphasis on the id-correlation trap.

**Type:** Build
**Languages:** Python（仅标准库，线程池 + 流式测试支架）
**Prerequisites:** Phase 13 · 02（函数调用深入）
**Time:** 约 75 分钟

## Learning Objectives · 学习目标

- 解释 `parallel_tool_calls: true` 为什么存在，以及什么时候该关掉它。
- 在并行扇出（fan-out）期间，把流式参数块关联到正确的工具调用 id。
- 把不完整的 `arguments` 字符串重新拼装成完整 JSON，而不是过早解析。
- 跑一个三城市天气基准，直观对比顺序与并行的延迟。

> Explain why `parallel_tool_calls: true` exists and when to disable it.
> Correlate streamed argument chunks to the right tool-call id during parallel fan-out.
> Reassemble partial `arguments` strings into complete JSON without parsing early.
> Run a three-city weather benchmark that demonstrates sequential vs parallel latency.

## The Problem · 问题在哪

没有并行调用时，一个回答「班加罗尔、东京、苏黎世天气如何」的 agent 是这样做的：

```
user -> LLM
LLM -> call get_weather(Bengaluru)
host -> run executor, reply with result
LLM -> call get_weather(Tokyo)
host -> run executor, reply with result
LLM -> call get_weather(Zurich)
host -> run executor, reply with result
LLM -> final text answer
```

三次 LLM 往返，每一次还要额外支付执行器延迟。大约是理想墙钟时间的 4 倍。

用并行调用：

```
user -> LLM
LLM -> call get_weather(Bengaluru); call get_weather(Tokyo); call get_weather(Zurich)
host -> run all three executors concurrently, reply with three results
LLM -> final text answer
```

一次 LLM 往返。执行器时间是三者的最大值，不是总和。在 OpenAI、Anthropic、Gemini 上的生产基准显示，扇出型负载的墙钟时间减少 60% 到 70%。

代价是关联复杂度。当三个调用乱序完成时，你的结果必须带上匹配的 `tool_call_id`，模型才能把它们对上号。当结果流式传输时，你必须在执行之前把部分参数碎片拼装成完整 JSON。Gemini 3 加入唯一 id，部分就是为了解决一个真实世界的问题：对同一工具的两个并行调用此前无法区分。

> Three independent weather lookups serialized is three round trips. Run them in parallel and total time collapses to the slowest single call. ... The price is correlation complexity. When the three calls complete out of order, your results must carry the matching `tool_call_id` so the model can line them up. ... Gemini 3 added unique ids in part to solve a real-world issue where two parallel calls to the same tool were indistinguishable.

## The Concept · 概念

### Enabling parallel · 开启并行

- **OpenAI。** `parallel_tool_calls: true` 默认开启。设为 `false` 强制串行。
- **Anthropic。** 通过 `disable_parallel_tool_use: false` 并行（Claude 3.5 及以上默认）。设为 `true` 走串行。
- **Gemini。** 始终具备并行能力；`tool_config.function_calling_config.mode = "AUTO"` 让模型自己决定。

当工具之间有顺序依赖（先 `create_file` 再 `write_file`）、当一个调用的输出决定另一个调用的输入、或当限流器扛不住扇出时，要关掉并行。

> **OpenAI.** `parallel_tool_calls: true` on by default. Set `false` to force serial. ... Disable parallel when tools have ordering dependencies (`create_file` then `write_file`), when one call's output informs another's input, or when the rate limiter cannot handle fan-out.

### Id correlation · id 关联

模型输出的每个调用都有 `id`。宿主返回的每个结果必须带相同的 id。没有它，结果就有歧义。

- **OpenAI。** 每条 tool 角色消息上的 `tool_call_id`。
- **Anthropic。** 每个 `tool_result` 块上的 `tool_use_id`。
- **Gemini。** 每个 `functionResponse` 上的 `id`（Gemini 3 及以上；Gemini 2 按名称匹配，同名并行调用会出问题）。

> Every call the model emits has an `id`. Every result the host returns must include the same id. Without this, results are ambiguous. ... **Gemini.** `id` on each `functionResponse` (Gemini 3 and up; Gemini 2 matched by name which broke for same-name parallel calls).

### Running calls concurrently · 并发运行调用

宿主把每个调用的执行器放到自己的线程、协程或远程工作节点上跑。最简单的测试支架用线程池；生产用 asyncio 加 `asyncio.gather` 或结构化并发。完成顺序不可预测——id 才是身份标识。

一个常见 bug：按调用清单顺序而不是完成顺序回复结果。这通常能工作，因为模型只关心 `tool_call_id`，但一旦某个结果被丢弃或重复，乱序提交会让调试更难。建议按完成顺序、带显式 id 回复。

> The host runs each call's executor on its own thread, coroutine, or remote worker. ... Order of completion is unpredictable — the id is the identifier. ... Prefer to reply in completion order with explicit ids.

### Streaming tool calls · 流式工具调用

模型流式输出时，`arguments` 是分片到达的。三个并行调用的三股 chunk 流在线上交错。你需要每个 id 一个累积器（accumulator）。

各家形状：

- **OpenAI。** 每个 chunk 是 `choices[0].delta.tool_calls[i].function.arguments`（部分字符串）。chunk 带 `index`（调用清单中的位置）。你按 index 累积，在 `id` 首次出现时读它，在 `finish_reason = "tool_calls"` 时解析 JSON。
- **Anthropic。** 流事件是 `message_start`，随后每个块一条 `content_block_start`（类型 `tool_use`，含 id、name、空 input）。`content_block_delta` 事件携带 `input_json_delta` 块。`content_block_stop` 关闭每个块。
- **Gemini。** `streamFunctionCallArguments`（Gemini 3 及以上）输出带 `functionCallId` 的块，调用得以干净交错。Gemini 3 之前，流式一次只返回一个完整调用。

> When the model streams, `arguments` arrive in pieces. Three separate streams of chunks for three parallel calls interleave on the wire. You need one accumulator per id. ... **Anthropic.** Stream events are `message_start`, then one `content_block_start` per block with type `tool_use` (containing id, name, empty input). ...

### Partial JSON and the parse-early trap · 部分 JSON 与过早解析陷阱

`arguments` 没拼完之前不能解析。`{"city": "Beng` 这类部分 JSON 不合法，会直接抛异常。正确的闸门是供应商的调用结束信号：OpenAI 的 `finish_reason = "tool_calls"`、Anthropic 的 `content_block_stop`、或 Gemini 的流结束事件。只有到那时才尝试 `json.loads`。更稳健的做法是使用增量 JSON 解析器，随着结构完成逐步产出事件；OpenAI 的流式指南推荐用它实现「正在思考」的实时 UX 提示。花括号计数作为完整性测试并不可靠（引号字符串或转义内容里的花括号会造成误报），只能当非正式的调试启发式来用。

> You cannot parse `arguments` until it is complete. Partial JSON such as `{"city": "Beng` is not valid and will raise. The correct gate is the provider's end-of-call signal: OpenAI's `finish_reason = "tool_calls"`, Anthropic's `content_block_stop`, or Gemini's stream-end event. Only then attempt `json.loads`. ... Brace-counting is unreliable as a completeness test (braces inside quoted strings or escaped content cause false positives) and should only be used as an informal debug heuristic.

### Out-of-order completion · 乱序完成

```
call_A: fast API, returns first
call_B: slow API, returns second
call_C: median API, returns third
```

宿主的回复仍然必须引用这些 id：

```
[{role: "tool", tool_call_id: "call_A", content: ...},
 {role: "tool", tool_call_id: "call_B", content: ...},
 {role: "tool", tool_call_id: "call_C", content: ...}]
```

在 OpenAI 或 Anthropic 上，回复顺序不影响正确性。Gemini 只要 id 对得上，接受任何顺序。

> The host reply must still cite the ids ... Order in the reply does not matter for correctness on OpenAI or Anthropic. Gemini accepts any order so long as ids match.

### Benchmark: sequential vs parallel · 基准测试：顺序 vs 并行

`code/main.py` 里的测试支架用 400、600、800 毫秒延迟模拟三个执行器。顺序执行总共 1800 毫秒。并行执行 max(400, 600, 800) = 800 毫秒。差值是常数而非比例，所以工具越多省得越多。

现实世界的警告：并行调用会给下游 API 施压。对限流服务来一次 10 路扇出会直接失败。Phase 13 · 17 讲网关级背压（backpressure）；重试语义留待未来阶段。

> The harness in `code/main.py` simulates three executors with 400, 600, and 800 ms latency. Sequential runs it in 1800 ms total. Parallel runs it in max(400, 600, 800) = 800 ms. ... Real-world caveat: parallel calls stress downstream APIs. A 10-way fan-out to a rate-limited service will fail.

### Streaming fan-out wall-clock · 流式扇出的墙钟时间

如果模型本身在流式输出，那么只要某个调用的参数一拼装完成，你就可以立刻开始执行，不必等所有调用都定型。这是 OpenAI 文档化了的优化，但不是所有 SDK 都暴露出来。本课的测试支架就这么做：模拟流一旦产出完整的参数对象，宿主立即发起该调用。

> If the model itself streams, you can start executing as soon as one call's arguments are complete, rather than waiting for all calls to finalize. This is an optimization OpenAI documents but not all SDKs expose. ...

```figure
tp-parallel-fanout
```

## Use It · 实战用法

`code/main.py` 有两半。前一半用 `concurrent.futures.ThreadPoolExecutor` 把三个模拟天气调用按顺序和并行各跑一遍，打印墙钟时间。后一半重放一个假的流式响应——三个并行调用的 `arguments` 块在同一条流上交错——并用 `StreamAccumulator` 按 id 重新拼装。没有 LLM，没有网络，只有拼装逻辑。

值得关注的点：

- 顺序计时器停在 1.8 秒。同样的假延迟下，并行计时器停在 0.8 秒。
- 累积器靠按 id 缓冲、且只在每个调用的 JSON 完整时才解析，来处理乱序到达的块。
- 某个 id 的参数一定型，执行器立刻开工，而不是等所有流结束。

> `code/main.py` has two halves. The first runs three simulated weather calls sequentially and in parallel using `concurrent.futures.ThreadPoolExecutor` and prints wall-clock time. ... The accumulator handles chunks arriving out of order by buffering per-id and parsing only when each call's JSON is complete. ...

## Ship It · 交付

本课产出 `outputs/skill-parallel-call-safety-check.md`。给定一份工具注册表，这个技能（skill）会审计哪些工具可以安全并行、哪些有顺序依赖、哪些会压垮下游限流——并返回一份带每工具 `parallel_safe` 标志的修订版注册表。

> This lesson produces `outputs/skill-parallel-call-safety-check.md`. Given a tool registry, the skill audits which tools are safe to parallelize, which have ordering dependencies, and which would overwhelm downstream rate limits — returning a revised registry with per-tool `parallel_safe` flags.

## Exercises · 练习

1. 运行 `code/main.py` 并调整模拟延迟。确认并行/顺序之比接近 `max/sum`（真实运行会因线程调度、序列化和支架开销而略偏离理想值）。延迟分布到什么程度时，并行就不再重要？

2. 扩展累积器以处理「调用在流中途被取消」的情况：丢弃其缓冲并发出 `cancelled` 事件。哪家供应商显式记录了这个情况？查查 Anthropic `content_block_stop` 的语义和 OpenAI `finish_reason: "length"` 的行为。

3. 把线程池换成 `asyncio.gather`。两个都测一下。异步应有小幅胜出，因为上下文切换更便宜——但前提是执行器做真正的 I/O。

4. 挑两个不该并行的工具（比如先 `create_file` 再 `write_file`）。给注册表加一张 `ordering_dependency` 依赖图，让并行扇出过这道闸。这是依赖感知调度的最小机器，未来的 agent 工程阶段会把它形式化。

5. 读 OpenAI 的并行函数调用小节和 Anthropic 的 `disable_parallel_tool_use` 文档。找出 Anthropic 建议关闭并行的那一类真实工具。（提示：对同一资源的后果型修改。）

## Key Terms · 术语表

| 术语 | 人们怎么说 | 它实际是什么 |
|------|----------------|------------------------|
| Parallel tool calls（并行工具调用） | 「一轮内扇出」 | 模型在单条 assistant 消息里输出多个工具调用 |
| `parallel_tool_calls` | 「OpenAI 的开关」 | 启用或禁用多调用输出 |
| `disable_parallel_tool_use` | 「Anthropic 的反向开关」 | 选择退出标志；默认并行开启 |
| Tool call id（调用 id） | 「关联句柄」 | 结果消息必须回带的每调用标识符 |
| Accumulator（累积器） | 「流缓冲」 | 每个 id 一个的字符串缓冲，接不完整的 `arguments` 块 |
| Out-of-order completion（乱序完成） | 「快的先回」 | 并行调用以不可预测的顺序完成；id 是黏合剂 |
| Dependency graph（依赖图） | 「顺序约束」 | 输出会喂进其他工具输入的工具；不可并行 |
| Parse-early trap（过早解析陷阱） | 「JSON.parse 炸了」 | 试图解析不完整的 `arguments` 字符串 |
| `streamFunctionCallArguments` | 「Gemini 3 特性」 | 带每调用唯一 id 的流式参数块 |
| Completion-order reply（按完成顺序回复） | 「不等全部」 | 结果一到就按 id 键回复 |

## Further Reading · 延伸阅读

- [OpenAI — Parallel function calling](https://platform.openai.com/docs/guides/function-calling#parallel-function-calling) —— 默认行为与选择退出的开关
- [Anthropic — Parallel tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use) —— `disable_parallel_tool_use` 与结果批处理
- [Google — Gemini function calling parallel section](https://ai.google.dev/gemini-api/docs/function-calling) —— Gemini 3 起按 id 关联的并行调用
- [OpenAI — Streaming responses with tools](https://platform.openai.com/docs/api-reference/responses-streaming) —— OpenAI 流的分块参数重组
- [Anthropic — Streaming messages](https://docs.anthropic.com/en/api/messages-streaming) —— 带 `input_json_delta` 的 `content_block_delta`
