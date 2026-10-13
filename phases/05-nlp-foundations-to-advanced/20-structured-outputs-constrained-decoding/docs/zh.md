# Structured Outputs & Constrained Decoding · 结构化输出与受限解码（constrained decoding）

> 让 LLM 输出 JSON，大多数时候你确实得到 JSON。但在生产里，「大多数」就是问题所在。受限解码通过在采样前修改 logits，把「大多数」变成「总是」。
>
> Ask an LLM for JSON. Get JSON most of the time. In production, "most" is the problem. Constrained decoding turns "most" into "always" by editing the logits before sampling.

**类型:** Build（构建）
**语言:** Python
**前置课程:** Phase 5 · 17（聊天机器人）、Phase 5 · 19（子词分词）
**时间:** ~60 分钟

## The Problem · 问题

一个分类器让 LLM：「从 {positive, negative, neutral} 里返回一个。」模型返回「The sentiment is positive — this review is overwhelmingly favorable because the customer explicitly states that they ...」。你的解析器崩了。分类器的 F1 变成 0.0。

自由生成不是契约，只是建议。生产系统需要契约。

2026 年存在三层方案。

1. **提示词（Prompting）。** 好好请求。「只返回 JSON 对象。」在前沿模型上约 80% 有效，小模型上更低。
2. **原生结构化输出 API。** OpenAI `response_format`、Anthropic 工具调用、Gemini JSON 模式。在支持的 schema 上可靠。会被厂商锁定。
3. **受限解码（constrained decoding）。** 在每个生成步骤修改 logits，让模型*不可能*输出非法 token。构造上 100% 合法。对任何本地模型都可用。

本课为三者建立直觉，并说清楚什么时候该用哪一个。

> Free-form generation is not a contract. It is a suggestion. A production system needs a contract.
> Three layers exist in 2026.
> **Prompting.** ... Works ~80% on frontier models, less on smaller ones.
> **Native structured output APIs.** ... **Constrained decoding.** Modify the logits at every generation step so the model *cannot* emit invalid tokens. 100% valid by construction. Works on any local model.

## The Concept · 概念

![受限解码在每一步屏蔽非法 token](../assets/constrained-decoding.svg)

**受限解码怎么工作。** 在每个生成步骤，LLM 对整个词表（约 10 万 token）产出一个 logit 向量。一个 *logit 处理器*（logit processor）坐在模型和采样器之间。它根据目标文法——JSON Schema、正则、上下文无关文法——中的当前位置，算出哪些 token 是合法的，并把所有非法 token 的 logits 设为负无穷。剩下 logits 的 softmax 只把概率质量放在合法的续写上。

2026 年的实现：

- **Outlines。** 把 JSON Schema 或正则编译成有限状态机（FSM）。每个 token 的下一合法 token 查询是 O(1)。基于 FSM，所以递归 schema 需要先展平。
- **XGrammar / llguidance。** 上下文无关文法引擎。能处理递归 JSON Schema。解码开销近乎为零。OpenAI 在其 2025 年的结构化输出实现中致谢了 llguidance。
- **vLLM guided decoding。** 内置 `guided_json`、`guided_regex`、`guided_choice`、`guided_grammar`，后端可接 Outlines、XGrammar 或 lm-format-enforcer。
- **Instructor。** 架在任何 LLM 之上的 Pydantic 封装。校验失败会重试。跨厂商，但不修改 logits——它依赖重试加对结构化输出友好的提示词。

> **How constrained decoding works.** At each generation step, the LLM produces a logit vector over the full vocabulary (~100k tokens). A *logit processor* sits between the model and the sampler. ... The softmax over the remaining logits puts probability mass only on valid continuations.
> **Outlines.** Compiles JSON Schema or regex into a finite-state machine. ...
> **XGrammar / llguidance.** Context-free grammar engines. Handle recursive JSON Schema. Near-zero decoding overhead.
> **vLLM guided decoding.** ... **Instructor.** Pydantic-based wrapper over any LLM. Retries on validation failure. Cross-provider, but does not modify logits.

### The counterintuitive result · 反直觉的结论

受限解码常常*比*无约束生成更快。两个原因。第一，它缩小了下一 token 的搜索空间。第二，聪明的实现会对被强制的 token 完全跳过生成（像 `{"name": "` 这样的脚手架——每个字节都是确定的）。

> Constrained decoding is often *faster* than unconstrained generation. Two reasons. First, it shrinks the next-token search space. Second, clever implementations skip token generation entirely for forced tokens (scaffolding like `{"name": "` — every byte is determined).

### The pitfall that costs you · 让你付出代价的坑

字段顺序有所谓。把 `answer` 放在 `reasoning` 前面，模型会先敲定答案、再去思考。JSON 是合法的。答案是错的。没有任何校验能抓住它。

```json
// BAD
{"answer": "yes", "reasoning": "because ..."}

// GOOD
{"reasoning": "... therefore ...", "answer": "yes"}
```

Schema 的字段顺序是逻辑，不是排版。

```figure
constrained-decoder
```

> Field order matters. Put `answer` before `reasoning`, and the model commits to an answer before it thinks. JSON is valid. Answer is wrong. No validation catches it.
> Schema field order is logic, not formatting.

## Build It · 动手造

### Step 1: regex-constrained generation from scratch · 第 1 步：从零实现正则受限生成

完整的独立 FSM 实现见 `code/main.py`。核心思想 30 行：

```python
def mask_logits(logits, valid_token_ids):
    mask = [float("-inf")] * len(logits)
    for tid in valid_token_ids:
        mask[tid] = logits[tid]
    return mask


def generate_constrained(model, tokenizer, prompt, fsm):
    ids = tokenizer.encode(prompt)
    state = fsm.initial_state
    while not fsm.is_accept(state):
        logits = model.next_token_logits(ids)
        valid = fsm.valid_tokens(state, tokenizer)
        logits = mask_logits(logits, valid)
        tok = sample(logits)
        ids.append(tok)
        state = fsm.transition(state, tok)
    return tokenizer.decode(ids)
```

FSM 跟踪文法的哪些部分已经被满足。`valid_tokens(state, tokenizer)` 计算哪些词表 token 能推进 FSM 而不离开接受路径。

> The FSM tracks what parts of the grammar we have satisfied so far. `valid_tokens(state, tokenizer)` computes which vocabulary tokens can advance the FSM without leaving an accepting path.

### Step 2: Outlines for JSON Schema · 第 2 步：用 Outlines 处理 JSON Schema

```python
from pydantic import BaseModel
from typing import Literal
import outlines


class Review(BaseModel):
    sentiment: Literal["positive", "negative", "neutral"]
    confidence: float
    evidence_span: str


model = outlines.models.transformers("meta-llama/Llama-3.2-3B-Instruct")
generator = outlines.generate.json(model, Review)

result = generator("Classify: 'The wait staff was attentive and the food arrived hot.'")
print(result)
# Review(sentiment='positive', confidence=0.93, evidence_span='attentive ... hot')
```

零校验错误。永远。FSM 让非法输出不可达。

> Zero validation errors. Ever. The FSM makes invalid output unreachable.

### Step 3: Instructor for provider-agnostic Pydantic · 第 3 步：用 Instructor 做厂商无关的 Pydantic

```python
import instructor
from anthropic import Anthropic
from pydantic import BaseModel, Field


class Invoice(BaseModel):
    vendor: str
    total_usd: float = Field(ge=0)
    line_items: list[str]


client = instructor.from_anthropic(Anthropic())
invoice = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=1024,
    response_model=Invoice,
    messages=[{"role": "user", "content": "Extract from: 'Acme Corp $420. Widget, Gizmo.'"}],
)
```

另一种机制。Instructor 不碰 logits。它把 schema 格式化进提示词，解析输出，校验失败就重试（默认 3 次）。对任何厂商都可用。重试增加延迟和成本。跨厂商可移植性是它的卖点。

> Different mechanism. Instructor does not touch logits. It formats the schema into the prompt, parses the output, and retries on validation failure (default 3 times). Works with any provider. Retries add latency and cost. Cross-provider portability is the selling point.

### Step 4: native vendor APIs · 第 4 步：原生厂商 API

```python
from openai import OpenAI

client = OpenAI()
response = client.responses.create(
    model="gpt-5",
    input=[{"role": "user", "content": "Classify: 'The food was cold.'"}],
    text={"format": {"type": "json_schema", "name": "sentiment",
          "schema": {"type": "object", "required": ["sentiment"],
                     "properties": {"sentiment": {"type": "string",
                                                  "enum": ["positive", "negative", "neutral"]}}}}},
)
print(response.output_parsed)
```

服务端的受限解码。在支持的 schema 上与 Outlines 可靠性相当。不用管理本地模型。代价是你被锁进厂商生态。

> Server-side constrained decoding. Reliability parity with Outlines for supported schemas. No local model management. Locks you to the vendor.

## Pitfalls · 坑

- **递归 schema。** Outlines 把递归展平到固定深度。树形输出（嵌套评论、AST）需要 XGrammar 或 llguidance（基于 CFG）。
- **巨型枚举。** 一万个选项的 enum 编译很慢或直接超时。改用检索器：先预测 top-k 候选，再约束到这些候选。
- **文法太严。** 强制 `date: "YYYY-MM-DD"` 正则，模型就没法对缺失日期输出 `"unknown"`。模型会用编造日期来补偿。允许 `null` 或哨兵值。
- **过早承诺。** 见上面的字段顺序坑。永远把推理字段放在前面。
- **无 schema 的厂商 JSON 模式。** 纯 JSON 模式只保证 JSON 语法合法，不保证*对你的用例*合法。永远提供完整 schema。

> **Recursive schemas.** Outlines flattens recursion to a fixed depth. ...
> **Huge enums.** ... **Grammar too strict.** Force `date: "YYYY-MM-DD"` regex and the model cannot output `"unknown"` for missing dates. Model compensates by inventing a date. Allow `null` or a sentinel.
> **Premature commitment.** ... **Vendor JSON mode without schema.** Pure JSON mode only guarantees valid JSON, not valid *for your use case*. Always provide a full schema.

## Use It · 实战用法

2026 年的技术栈：

| 情形 | 选择 |
|-----------|------|
| OpenAI/Anthropic/Google 模型，schema 简单 | 原生厂商结构化输出 |
| 任意厂商、Pydantic 工作流、可容忍重试 | Instructor |
| 本地模型、需要 100% 合法、扁平 schema | Outlines（FSM）|
| 本地模型、递归 schema | XGrammar 或 llguidance |
| 自托管推理服务器 | vLLM guided decoding |
| 批处理且重试可接受 | Instructor + 最便宜的模型 |

## Ship It · 交付

保存为 `outputs/skill-structured-output-picker.md`：

```markdown
---
name: structured-output-picker
description: Choose a structured output approach, schema design, and validation plan.
version: 1.0.0
phase: 5
lesson: 20
tags: [nlp, llm, structured-output]
---

Given a use case (provider, latency budget, schema complexity, failure tolerance), output:

1. Mechanism. Native vendor structured output, Instructor retries, Outlines FSM, or XGrammar CFG. One-sentence reason.
2. Schema design. Field order (reasoning first, answer last), nullable fields for "unknown", enum vs regex, required fields.
3. Failure strategy. Max retries, fallback model, graceful `null` handling, out-of-distribution refusal.
4. Validation plan. Schema compliance rate (target 100%), semantic validity (LLM-judge), field-coverage rate, latency p50/p99.

Refuse any design that puts `answer` or `decision` before reasoning fields. Refuse to use bare JSON mode without a schema. Flag recursive schemas behind an FSM-only library.
```

> Save as `outputs/skill-structured-output-picker.md`.

## Exercises · 练习

1. **简单。** 不用受限解码，让一个小型开放权重模型（比如 Llama-3.2-3B）输出 `Review(sentiment, confidence, evidence_span)`。在 100 条评论上测能解析为合法 JSON 的比例。
2. **中等。** 同一语料换 Outlines JSON 模式再跑。比较合规率、延迟和语义准确率。
3. **困难。** 从零实现一个电话号码（`\d{3}-\d{3}-\d{4}`）的正则受限解码器。在 1000 个样本上验证 0 个非法输出。

## Key Terms · 关键术语

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Constrained decoding | 强制输出合法 | 在每个生成步骤屏蔽非法 token 的 logits。|
| Logit processor | 施加约束的那个东西 | 函数：`(logits, state) -> masked_logits`。|
| FSM | 有限状态机 | 编译后的文法表示；下一合法 token 查询为 O(1)。|
| CFG | 上下文无关文法 | 能处理递归的文法；比 FSM 慢但更有表达力。|
| Schema field order | 有所谓吗？ | 有——第一个字段先定调；永远把推理放在答案之前。|
| Guided decoding | vLLM 对它的叫法 | 同一概念，集成进推理服务器。|
| JSON mode | OpenAI 的早期版本 | 只保证 JSON 语法；不保证 schema 匹配。|

## Further Reading · 延伸阅读

- [Willard, Louf (2023). Efficient Guided Generation for LLMs](https://arxiv.org/abs/2307.09702) —— Outlines 论文。
- [XGrammar paper (2024)](https://arxiv.org/abs/2411.15100) —— 快速的基于 CFG 的受限解码。
- [vLLM — Structured Outputs](https://docs.vllm.ai/en/latest/features/structured_outputs.html) —— 推理服务器集成。
- [OpenAI — Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs) —— API 参考 + 各种坑。
- [Instructor library](https://python.useinstructor.com/) —— 跨厂商的 Pydantic + 重试。
- [JSONSchemaBench (2025)](https://arxiv.org/abs/2501.10868) —— 对 6 个受限解码框架做基准测试。
