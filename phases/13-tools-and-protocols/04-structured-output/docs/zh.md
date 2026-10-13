# Structured Output · 结构化输出——JSON Schema、Pydantic、Zod、受限解码

> "Ask the model nicely to return JSON" fails 5 to 15 percent of the time, even on frontier models. Structured outputs close that gap with constrained decoding: the model is literally prevented from emitting a token that would violate the schema. OpenAI's strict mode, Anthropic's schema-typed tool use, Gemini's `responseSchema`, Pydantic AI's `output_type`, and Zod's `.parse` are five surface forms of the same idea. This lesson builds the schema validator and the strict-mode contract learners will use for every production extraction pipeline.

**Type:** Build
**Languages:** Python（仅标准库，JSON Schema 2020-12 子集）
**Prerequisites:** Phase 13 · 02（函数调用深入）
**Time:** 约 75 分钟

## Learning Objectives · 学习目标

- 用正确的约束（enum、min/max、required、pattern）为一个抽取目标写出 JSON Schema 2020-12。
- 解释为什么严格模式（strict mode）和受限解码（constrained decoding）给出的保证不同于「生成之后再校验」。
- 区分三种失败模式：解析错误、schema 违规、模型拒绝。
- 交付一条带类型化修复与类型化拒绝处理的抽取流水线。

> Write a JSON Schema 2020-12 for an extraction target using the right constraints (enum, min/max, required, pattern).
> Explain why strict mode and constrained decoding give different guarantees from "validate after generation".
> Distinguish the three failure modes: parse error, schema violation, model refusal.
> Ship an extraction pipeline with typed repair and typed refusal handling.

## The Problem · 问题在哪

一个阅读采购订单邮件的 agent，需要把自由文本变成 `{customer, line_items, total_usd}`。三种做法。

**做法一：用提示词要 JSON。** 「用 JSON 回复，字段为 customer、line_items、total_usd。」在前沿模型上 85% 到 95% 的情况可行。失败方式有六种：缺花括号、尾随逗号、类型错误、幻觉字段、在 token 上限处截断、漏出「Here is your JSON:」之类的散文。

**做法二：生成后校验。** 自由生成、解析、按 schema 校验、失败就重试。可靠但昂贵——每次重试都要花钱，截断类 bug 每次发生多花一轮。

**做法三：受限解码（constrained decoding）。** 供应商在解码时强制执行 schema。非法 token 在采样分布里被屏蔽掉。输出保证可解析、保证通过校验。失败收敛为一种模式：拒绝（refusal，模型判断输入装不进这个 schema）。

2026 年的每家前沿供应商都提供了做法三的某个形态。

- **OpenAI。** `response_format: {type: "json_schema", strict: true}`；若模型婉拒，响应里有 `refusal`。
- **Anthropic。** 对 `tool_use` 输入强制 schema；`stop_reason: "refusal"` 并不存在，但没有工具调用的 `end_turn` 就是信号。
- **Gemini。** 请求级的 `responseSchema`；2026 年起 Gemini 为部分类型提供 token 级文法约束。
- **Pydantic AI。** `output_type=InvoiceModel` 输出类型化为 `InvoiceModel` 的结构化 `RunResult`。
- **Zod（TypeScript）。** 运行时解析器，用 Zod schema 校验供应商输出；与 OpenAI 的 `beta.chat.completions.parse` 配对。

共同的主线：schema 声明一次，端到端强制执行。

> **Approach three: constrained decoding.** The provider enforces the schema at decode time. Invalid tokens are masked out of the sampling distribution. The output is guaranteed to parse and guaranteed to validate. Failure collapses to one mode: refusal ... Every 2026 frontier provider ships some form of approach three. ... The common thread: declare the schema once, enforce it end to end.

## The Concept · 概念

### JSON Schema 2020-12 — the lingua franca · JSON Schema 2020-12：通用语

每家供应商都接受 JSON Schema 2020-12。你最常用的构件：

- `type`：`object`、`array`、`string`、`number`、`integer`、`boolean`、`null` 之一。
- `properties`：字段名到子 schema 的映射。
- `required`：必须出现的字段名列表。
- `enum`：允许值的封闭集合。
- `minimum` / `maximum`（数字），`minLength` / `maxLength` / `pattern`（字符串）。
- `items`：作用于每个数组元素的子 schema。
- `additionalProperties`：`false` 禁止多余字段（默认值随模式而变）。

OpenAI 严格模式追加三条要求：每个属性都必须列进 `required`、处处 `additionalProperties: false`、不能有未解析的 `$ref`。违反任何一条，API 在请求时直接返回 400。

> Every provider accepts JSON Schema 2020-12. ... OpenAI strict mode adds three requirements: every property must be listed in `required`, `additionalProperties: false` everywhere, and no unresolved `$ref`. If you break these, the API returns 400 at request time.

### Pydantic, the Python binding · Pydantic：Python 侧绑定

Pydantic v2 通过 `model_json_schema()` 从 dataclass 风格的模型生成 JSON Schema。Pydantic AI 把它包了一层，于是你写：

```python
class Invoice(BaseModel):
    customer: str
    line_items: list[LineItem]
    total_usd: Decimal
```

agent 框架在边缘把这份 schema 翻译成 OpenAI 严格模式、Anthropic `input_schema` 或 Gemini `responseSchema`。模型的输出以类型化的 `Invoice` 实例返回。校验错误抛出带类型化错误路径的 `ValidationError`。

> Pydantic v2 generates JSON Schema from dataclass-shaped models via `model_json_schema()`. ... The model's output comes back as a typed `Invoice` instance. Validation errors raise `ValidationError` with typed error paths.

### Zod, the TypeScript binding · Zod：TypeScript 侧绑定

Zod（`z.object({customer: z.string(), ...})`）是 TS 侧的等价物。OpenAI 的 Node SDK 暴露 `zodResponseFormat(Invoice)`，把它翻译成 API 的 JSON Schema 负载。

> Zod (`z.object({customer: z.string(), ...})`) is the TS equivalent. OpenAI's Node SDK exposes `zodResponseFormat(Invoice)` which translates to the API's JSON Schema payload.

### Refusals · 拒绝

严格模式没法强迫模型回答。如果输入装不进 schema（「那封邮件是一首诗，不是发票」），模型会输出一个带原因的 `refusal` 字段。你的代码必须把它当一等结果来处理，而不是失败。拒绝还可以当安全信号用：让模型从受保护内容的邮件里抽信用卡号，它会返回附带安全原因的拒绝。

> Strict mode cannot force the model to answer. If the input cannot fit the schema ("the email was a poem, not an invoice"), the model emits a `refusal` field containing the reason. Your code must handle this as a first-class outcome, not a failure. ... The refusal is also useful as a safety signal: a model asked to extract a credit card number from a protected-content email returns a refusal with the safety reason attached.

### Constrained decoding in the open · 开源世界的受限解码

开放权重的实现用三种技术。

1. **基于文法的解码**（`outlines`、`guidance`、`lm-format-enforcer`）：从 schema 构建确定性有限自动机；每一步屏蔽掉会违反 FSM 的那些 token 的 logits。
2. **用 JSON 解析器做 logit 屏蔽**：让流式 JSON 解析器与模型同步运行；每一步算出合法的下一 token 集合。
3. **带校验器的投机解码**：便宜的草稿模型提议 token，校验器强制 schema。

商业供应商在幕后三选一。2026 年的技术水平：对短的结构化输出比普通生成更快，对长的速度大致相同。

> Open-weights implementations use three techniques. ... **Grammar-based decoding** (`outlines`, `guidance`, `lm-format-enforcer`): build a deterministic finite automaton from the schema; at every step, mask the logits of tokens that would violate the FSM. ... The 2026 state of the art is faster than plain generation for short structured outputs and roughly the same speed for long ones.

### The three failure modes · 三种失败模式

1. **解析错误。** 输出不是合法 JSON。严格模式下不可能发生。非严格供应商上仍会发生。
2. **Schema 违规。** 输出可解析但违反 schema。严格模式下不可能发生。它之外很常见。
3. **拒绝。** 模型婉拒。必须作为类型化结果处理。

> **Parse error.** The output is not valid JSON. Cannot happen under strict mode. Can still happen on non-strict providers. ... **Refusal.** The model declines. Must be handled as a typed outcome.

### Retry strategy · 重试策略

当你在严格模式之外（Anthropic 工具使用、非严格 OpenAI、旧版 Gemini），恢复模式是：

```
generate -> parse -> validate -> if fail, inject error and retry, max 3x
```

一次重试通常就够。三次重试能兜住弱模型的偶发抖动。超过三次说明 schema 有问题：对某些输入模型怎么也满足不了，该修的是提示词或 schema。

> When you are outside strict mode (Anthropic tool use, non-strict OpenAI, older Gemini), the recovery pattern is ... One retry is usually enough. Three retries catches weak-model flakes. Beyond three is a sign of a bad schema: the model cannot satisfy it for some inputs, and the prompt or the schema needs fixing.

### Small-model support · 小模型支持

受限解码在小模型上也有效。一个带文法强制的 3B 参数开源模型，在结构化任务上胜过靠裸提示的 70B 模型。这是结构化输出对生产如此重要的主因：它把可靠性与模型规模解耦。

> Constrained decoding works on small models. A 3B-parameter open model with grammar enforcement out-performs a 70B-parameter model with raw prompting on structured tasks. This is the main reason structured outputs matter for production: it decouples reliability from model size.

```figure
constrained-decoding
```

## Use It · 实战用法

`code/main.py` 交付一个纯标准库实现的最小 JSON Schema 2020-12 校验器（types、required、enum、min/max、pattern、items、additionalProperties）。它包了一份 `Invoice` schema，把一份假 LLM 输出送过校验器，演示解析错误、schema 违规和拒绝三条路径。生产中把假输出换成任何供应商的真实响应即可。

值得关注的点：

- 校验器返回带路径和消息的类型化 `[ValidationError]` 列表。这正是你想在重试提示词里暴露的形状。
- 拒绝分支不重试。它记日志并返回类型化的拒绝。Phase 14 · 09 把拒绝当安全信号用。
- `additionalProperties: false` 检查会在对抗性测试输入上触发，展示严格模式为什么能把幻觉字段关在门外。

> `code/main.py` ships a minimal JSON Schema 2020-12 validator in stdlib (types, required, enum, min/max, pattern, items, additionalProperties). ... The validator returns a typed `[ValidationError]` list with path and message. That is the shape you want surfaced to the retry prompt. ...

## Ship It · 交付

本课产出 `outputs/skill-structured-output-designer.md`。给定一个自由文本抽取目标（发票、支持工单、简历等），这个技能（skill）会产出一份兼容严格模式的 JSON Schema 2020-12，以及一个与之对应的 Pydantic 模型，并预留类型化的拒绝与重试处理桩。

> This lesson produces `outputs/skill-structured-output-designer.md`. Given a free-text extraction target (invoices, support tickets, resumes, etc.), the skill produces a JSON Schema 2020-12 that is strict-mode-compatible and a Pydantic model that mirrors it, with typed refusal and retry handling stubbed in.

## Exercises · 练习

1. 运行 `code/main.py`。增加第四个测试用例，其 `total_usd` 是负数。确认校验器以 `minimum` 约束路径拒绝它。

2. 扩展校验器，支持带鉴别器的 `oneOf`。常见情形：`line_item` 要么是产品要么是服务，用 `kind` 标记。严格模式在这里有微妙的规则；查 OpenAI 的结构化输出指南。

3. 用 Pydantic BaseModel 写同一份 Invoice schema，比较 `model_json_schema()` 的输出与你手写的 schema。找出 Pydantic 默认设置、而手写版遗漏的那一个字段。

4. 测量拒绝率。构造十个本不该被抽取的输入（一段歌词、一个数学证明、一封空白邮件），用真实供应商的严格模式跑一遍。数一数拒绝与幻觉输出的比例。这是你做拒绝感知重试的 ground truth。

5. 从头到尾读 OpenAI 的结构化输出指南。找出它明确禁止、而普通 JSON Schema 允许的那一个构件。然后设计一个非本质地使用该禁用构件的 schema，再把它重构为严格模式兼容。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 它实际是什么 |
|------|----------------|------------------------|
| JSON Schema 2020-12 | 「那份 schema 规范」 | 每家现代供应商都在说的 IETF 草案 schema 方言 |
| Strict mode（严格模式） | 「保证 schema」 | OpenAI 的开关，通过受限解码强制 schema |
| Constrained decoding（受限解码） | 「logit 屏蔽」 | 解码时强制，屏蔽非法的下一 token |
| Refusal（拒绝） | 「模型婉拒」 | 输入装不进 schema 时的类型化结果 |
| Parse error（解析错误） | 「非法 JSON」 | 输出无法按 JSON 解析；严格模式下不可能 |
| Schema violation（schema 违规） | 「形状不对」 | 可解析但违反类型 / required / enum / 取值范围 |
| `additionalProperties: false` | 「不许有额外的」 | 禁止未知字段；OpenAI 严格模式必填 |
| Pydantic BaseModel | 「类型化输出」 | 生成并校验 JSON Schema 的 Python 类 |
| Zod schema | 「TypeScript 输出类型」 | 用于校验供应商输出的 TS 运行时 schema |
| Grammar enforcement（文法强制） | 「开源世界的受限解码」 | 基于 FSM 的 logit 屏蔽，如 outlines / guidance |

## Further Reading · 延伸阅读

- [OpenAI — Structured outputs](https://platform.openai.com/docs/guides/structured-outputs) —— 严格模式、拒绝与 schema 要求
- [OpenAI — Introducing structured outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/) —— 2024 年 8 月的发布文，解释解码保证
- [Pydantic AI — Output](https://ai.pydantic.dev/output/) —— 序列化到各家供应商的类型化 output_type 绑定
- [JSON Schema — 2020-12 release notes](https://json-schema.org/draft/2020-12/release-notes) —— 规范原文
- [Microsoft — Structured outputs in Azure OpenAI](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs) —— 企业部署注意事项与严格模式的坑
