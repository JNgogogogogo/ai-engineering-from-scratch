# Tool Use and Function Calling · 工具使用与函数调用

> Toolformer（Schick et al., 2023）开启了自监督工具标注。Berkeley Function Calling Leaderboard V4（Patil et al., 2025）立起了 2026 年的标尺：40% agentic、30% 多轮、10% live、10% non-live、10% 幻觉。单轮已经解决。记忆、动态决策和长程工具链还没有。

> Toolformer (Schick et al., 2023) started self-supervised tool annotation. Berkeley Function Calling Leaderboard V4 (Patil et al., 2025) sets the 2026 bar: 40% agentic, 30% multi-turn, 10% live, 10% non-live, 10% hallucination. Single-turn is solved. Memory, dynamic decision-making, and long-horizon tool chains are not.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 13 · 01 (Function Calling Deep Dive)
**Time:** ~60 minutes

---

## Learning Objectives · 学习目标

- 解释 Toolformer 的自监督训练信号：只有当执行能降低下一 token 的损失时，才保留工具标注。
- 说出 BFCL V4 的五个评测类别以及各自测量什么。
- 实现一个带 schema 校验、参数强制转换和执行沙箱的标准库工具注册表。
- 诊断 2026 年的三个开放问题：长程工具链、动态决策和记忆。

> Explain Toolformer's self-supervised training signal: keep tool annotations only when execution reduces next-token loss.
> Name BFCL V4's five evaluation categories and what each measures.
> Implement a stdlib tool registry with schema validation, argument coercion, and execution sandboxing.
> Diagnose the three 2026 open problems: long-horizon tool chaining, dynamic decision-making, and memory.

---

## The Problem · 问题在哪

早期的工具使用问的是：模型能不能预测出一个正确的函数调用？现代的工具使用问的是：模型能不能跨 40 步链式调用工具——带着记忆、带着部分可观测性、带着从工具失败中恢复的能力——而且不幻觉出不存在的工具？

Toolformer 确立了基线：模型可以靠自监督学会何时调用工具。BFCL V4 定义了 2026 年的评测目标。两者之间的空隙就是生产智能体的生存空间。

> Early tool use asked: can the model predict a correct function call? Modern tool use asks: can the model chain tools across 40 steps, with memory, with partial observability, with recovery from tool failures, without hallucinating tools that do not exist?
> Toolformer established the baseline: models can learn when to call tools with self-supervision. BFCL V4 defines the 2026 evaluation target. The gap between them is the space production agents live in.

---

## The Concept · 概念

### Toolformer (Schick et al., NeurIPS 2023)

想法：让模型给自己预训练语料标注候选 API 调用。对每个候选项，实际执行它。只有当把工具结果包含进来能降低下一 token 的损失时，才保留该标注。然后在过滤后的语料上微调。

覆盖的工具：计算器、QA 系统、搜索引擎、翻译器、日历。自监督信号纯粹关于工具是否有助于预测文本——没有任何人工标注。

规模结果：工具使用随规模涌现。小模型被工具标注拖累；大模型从中获益。这就是为什么 2026 年的前沿模型出厂就自带强工具使用，而大多数 7B 模型需要显式的工具使用微调才可靠。

> Idea: let the model annotate its own pretraining corpus with candidate API calls. For each candidate, execute it. Keep the annotation only if including the tool result reduces loss on the next token. Fine-tune on the filtered corpus.
> Tools covered: calculator, QA system, search engines, translator, calendar. The self-supervision signal is purely about whether the tool helps predict text — no human labels.
> Scale result: tool use emerges at scale. Smaller models hurt from tool annotations; larger models gain. This is why 2026 frontier models have strong tool use baked in while most 7B models need explicit tool-use fine-tuning to be reliable.

---

### Berkeley Function Calling Leaderboard V4 (Patil et al., ICML 2025)

BFCL 是 2026 年事实上的评测标准。V4 构成：

- **Agentic（40%）** —— 完整智能体轨迹：记忆、多轮、动态决策。
- **Multi-Turn（30%）** —— 带工具链的交互式对话。
- **Live（10%）** —— 用户提交的真实提示词（分布更难）。
- **Non-Live（10%）** —— 合成测试用例。
- **Hallucination（10%）** —— 检测什么时候不该调用任何工具。

V3 引入了基于状态的评估：在一段工具序列之后，检查 API 的实际状态（例如「文件创建了吗？」），而不是匹配工具调用的 AST。V4 增加了网页搜索、记忆和格式敏感性类别。

2026 年的关键发现：单轮函数调用接近解决。失败集中在记忆（跨轮携带上下文）、动态决策（根据先前结果选择工具）、长程链条（20+ 步后漂移）和幻觉检测（没有合适工具时拒绝调用）。

> BFCL is the 2026 de facto evaluation. V4 composition: **Agentic (40%)** — full agent trajectories: memory, multi-turn, dynamic decisions; **Multi-Turn (30%)** — interactive conversations with tool chains; **Live (10%)** — user-submitted real prompts (harder distribution); **Non-Live (10%)** — synthetic test cases; **Hallucination (10%)** — detect when no tool should be called.
> V3 introduced state-based evaluation: after a tool sequence, check the API's actual state (e.g. "is the file created?") rather than match the AST of the tool calls. V4 added web search, memory, and format sensitivity categories.
> Key 2026 finding: single-turn function calling is near-solved. Failures concentrate in memory (carrying context across turns), dynamic decision-making (choosing tools based on prior results), long-horizon chains (drift after 20+ steps), and hallucination detection (refusing to call when no tool fits).

---

### Tool schema · 工具 schema

每个 provider 都有自己的 schema。细节各异，形状相同：

```
name: string
description: string (what it does, when to use it)
input_schema: JSON Schema (properties, required, types, enums)
```

Anthropic 直接使用 `input_schema`。OpenAI 使用 `function.parameters`。两者都接受 JSON Schema。描述是承重的——模型靠读它们来挑对工具。糟糕的工具描述是「选错工具」类失败的头号根因。

> Every provider has a schema. They differ in details but share the same shape.
> Anthropic uses `input_schema` directly. OpenAI uses `function.parameters`. Both accept JSON Schema. Descriptions are load-bearing — the model reads them to pick the right tool. Bad tool descriptions are the #1 root cause of wrong-tool-picked failures.

---

### Argument validation · 参数校验

不要信任任何工具调用。校验：

1. **类型强制转换。** 模型可能返回字符串 "5"，而 schema 说 int。无歧义就转换；有歧义就拒绝。
2. **枚举校验。** 如果 schema 说 `status in {"open", "closed"}` 而模型发出 `"in_progress"`，带着描述性错误拒绝。
3. **必填字段。** 缺必填字段 → 立刻把错误观察还给模型，而不是崩溃。
4. **格式校验。** 日期、邮箱、URL——用具体的解析器校验，不要用正则。

每次校验失败都应该返回一个结构化观察，让模型能用正确的形状重试。

> Trust no tool call. Validate: type coercion (model may return a string "5" where the schema says int — coerce if unambiguous, reject if not); enum validation (if the schema says `status in {"open", "closed"}` and model emits `"in_progress"`, reject with a descriptive error); required fields (missing required field -> immediate error observation back to the model, not a crash); format validation (dates, emails, URLs — validate with concrete parsers, not regex).
> Every validation failure should return a structured observation so the model can retry with the correct shape.

---

### Parallel tool calls · 并行工具调用

现代 provider 支持在一个助手轮里并行调用工具。循环：

1. 模型发出 3 个带不同 `tool_use_id` 的工具调用。
2. 运行时执行它们（相互独立时并行执行）。
3. 每个结果作为一个 `tool_result` 块、按 `tool_use_id` 关联回传。

工程规则：把关联 ID 当承重件。换错了就会得到「错误工具的结果路由给错误调用」。

> Modern providers support parallel tool calls in one assistant turn. The loop: model emits 3 tool calls with distinct `tool_use_id`s; runtime executes them (in parallel if independent); each result goes back as a `tool_result` block correlated by `tool_use_id`.
> Engineering rule: treat correlation IDs as load-bearing. Swap them and you get wrong-tool-to-wrong-result routing.

---

### Sandboxing · 沙箱

工具执行就是沙箱边界。细节见第 9 课。简版：每个工具都应该声明读写面、网络访问、超时、内存上限。泛用的 `run_shell(cmd)` 是个危险信号；具体的 `git_status()` 更安全。

> Tool execution is the sandbox boundary. See Lesson 09 for detail. Short version: every tool should specify read/write surface, network access, timeout, memory cap. Generic `run_shell(cmd)` is a red flag; specific `git_status()` is safer.

```figure
tool-routing
```

---

## Build It · 动手造

`code/main.py` 实现一个生产形状的工具注册表：

- JSON Schema 子集校验器（仅标准库）。
- 工具注册：描述、输入 schema、超时和执行器。
- 参数强制转换与枚举校验。
- 带关联 ID 的并行工具分发。
- 作为结构化字符串的错误观察。

跑起来：

```
python3 code/main.py
```

轨迹展示一个迷你智能体在同一轮里调用三个工具，其中一个故意畸形的调用被拒绝，并返回一条模型可以据以行动的描述性错误。

> `code/main.py` implements a production-shape tool registry: JSON Schema subset validator (stdlib only); tool registration with description, input schema, timeout, and executor; argument coercion and enum validation; parallel tool dispatch with correlation IDs; error observations as structured strings.
> The trace shows a mini agent calling three tools in one turn, with one deliberately malformed call that is rejected with a descriptive error the model can act on.

---

## Use It · 实战用法

每个 provider 都有自己的工具 schema——Anthropic、OpenAI、Gemini、Bedrock。如果你需要多 provider，用一层转换层（OpenAI Agents SDK、Vercel AI SDK、LangChain tool adapter）。BFCL 是参考基准——如果工具使用是产品核心，发货前先拿它跑一遍你的智能体。

> Every provider has its own tool schema — Anthropic, OpenAI, Gemini, Bedrock. Use a translation layer (OpenAI Agents SDK, Vercel AI SDK, LangChain tool adapter) if you need multi-provider. BFCL is the reference benchmark — run it against your agent before shipping if tool use is central to the product.

---

## Ship It · 交付

`outputs/skill-tool-registry.md` 为给定任务域生成工具目录、schema 和注册表。包含描述质量检查（每个工具的描述有没有告诉模型什么时候该用它？）。

> `outputs/skill-tool-registry.md` generates a tool catalog, schema, and registry for a given task domain. Includes description-quality checks (does each tool's description tell the model when to use it?).

---

## Exercises · 练习

1. 加一个「no-op」工具，让模型可以显式拒绝使用其他任何工具。在一个 BFCL 式幻觉测试上测量效果。
2. 为 int-as-string 和 float-as-string 实现参数强制转换。从哪里开始，强制转换会开始掩盖真正的 bug？
3. 加一个每工具超时和一个熔断器（连续失败 3 次后拒绝该工具 60 秒）。这会如何改变模型的恢复方式？
4. 读 BFCL V4 描述。挑一个类别（例如「multi-turn」），把 10 个示例提示词跑过你的智能体。报告通过率。
5. 把这个标准库校验器移植到 Pydantic 或 Zod。Pydantic/Zod 抓到了哪些玩具实现漏掉的东西？

> 1. Add a "no-op" tool that lets the model explicitly refuse to use any other tool. Measure on a BFCL-like hallucination test.
> 2. Implement argument coercion for int-as-string and float-as-string. Where does coercion start to hide real bugs?
> 3. Add a per-tool timeout and a circuit breaker (refuse the tool for 60s after 3 consecutive failures). What does this change about how the model recovers?
> 4. Read BFCL V4 description. Pick one category (e.g. "multi-turn") and run 10 example prompts through your agent. Report pass rate.
> 5. Port the stdlib validator to Pydantic or Zod. What did Pydantic/Zod catch that the toy missed?

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Function calling | 「工具使用」 | 带校验 schema 的结构化输出工具调用 |
| Toolformer | 「自监督工具标注」 | Schick 2023 —— 只保留结果能降低下一 token 损失的工具调用 |
| BFCL | 「Berkeley Function Calling Leaderboard」 | 2026 年基准：40% agentic、30% 多轮、10% live、10% non-live、10% 幻觉 |
| Tool schema | 「给模型看的函数签名」 | name、description、参数的 JSON Schema |
| tool_use_id | 「关联 ID」 | 把工具调用和它的结果绑在一起；并行分发的关键 |
| Hallucination detection | 「知道何时不该调用」 | V4 类别：没有合适工具时拒绝调用 |
| Argument coercion | 「字符串转整数修补」 | 针对可预期 schema 不匹配的窄修复；有歧义就拒绝 |
| Sandboxing | 「工具执行边界」 | 每工具的读写面、网络、超时、内存上限 |

> | Term | What people say | What it actually means |
> |------|----------------|------------------------|
> | Function calling | "Tool use" | Structured-output tool invocation with validated schema |
> | Toolformer | "Self-supervised tool annotation" | Schick 2023 — keep tool calls whose results reduce next-token loss |
> | BFCL | "Berkeley Function Calling Leaderboard" | 2026 benchmark: 40% agentic, 30% multi-turn, 10% live, 10% non-live, 10% hallucination |
> | Tool schema | "Function signature for the model" | name, description, JSON Schema of arguments |
> | tool_use_id | "Correlation ID" | Ties a tool call to its result; essential for parallel dispatch |
> | Hallucination detection | "Know when not to call" | V4 category: refuse to call when no tool fits |
> | Argument coercion | "String-to-int repair" | Narrow fixes for predictable schema-mismatch; reject if ambiguous |
> | Sandboxing | "Tool execution boundary" | Per-tool read/write surface, network, timeout, memory cap |

---

## Further Reading · 延伸阅读

- [Schick et al., Toolformer (arXiv:2302.04761)](https://arxiv.org/abs/2302.04761) —— 自监督工具标注
- [Berkeley Function Calling Leaderboard (V4)](https://gorilla.cs.berkeley.edu/leaderboard.html) —— 2026 年评测基准
- [Anthropic, Tool use documentation](https://platform.claude.com/docs/en/agent-sdk/overview) —— Claude Agent SDK 里的生产级工具 schema
- [OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/) —— function tool 类型与 Guardrails

> - [Schick et al., Toolformer (arXiv:2302.04761)](https://arxiv.org/abs/2302.04761) — self-supervised tool annotation
> - [Berkeley Function Calling Leaderboard (V4)](https://gorilla.cs.berkeley.edu/leaderboard.html) — 2026 eval benchmark
> - [Anthropic, Tool use documentation](https://platform.claude.com/docs/en/agent-sdk/overview) — production tool schema in the Claude Agent SDK
> - [OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/) — function tool type and Guardrails
