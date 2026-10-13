# Self-Refine and CRITIC: Iterative Output Improvement · Self-Refine 与 CRITIC：迭代式输出改进

> Self-Refine（Madaan et al., 2023）让一个 LLM 扮演三个角色——生成、反馈、精修——循环往复。平均提升：7 个任务上绝对 +20。CRITIC（Gou et al., 2023）把验证步骤路由到外部工具，硬化了反馈环节。2026 年，这个模式以「evaluator-optimizer」（Anthropic）或 guardrail 循环（OpenAI Agents SDK）的形态进入每一个框架。

> Self-Refine (Madaan et al., 2023) uses one LLM in three roles — generate, feedback, refine — in a loop. Average gain: +20 absolute on 7 tasks. CRITIC (Gou et al., 2023) hardens the feedback step by routing verification through external tools. In 2026 this pattern ships in every framework as "evaluator-optimizer" (Anthropic) or a guardrail loop (OpenAI Agents SDK).

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 03 (Reflexion)
**Time:** ~60 minutes

---

## Learning Objectives · 学习目标

- 说出 Self-Refine 的三个提示词（generate、feedback、refine），并解释为什么 history 对 refine 提示词至关重要。
- 解释 CRITIC 的关键洞见：没有外部锚定时，LLM 的自我验证并不可靠。
- 用标准库实现一个带 history 的 Self-Refine 循环和一个可选的外部验证器。
- 把这个模式对应到 Anthropic 的「evaluator-optimizer」workflow 和 OpenAI Agents SDK 的输出 guardrails。

> State Self-Refine's three prompts (generate, feedback, refine) and explain why history matters for the refine prompt.
> Explain CRITIC's critical insight: LLMs are unreliable at self-verification without external grounding.
> Implement a stdlib Self-Refine loop with history and an optional external verifier.
> Map this pattern to Anthropic's "evaluator-optimizer" workflow and OpenAI Agents SDK's output guardrails.

---

## The Problem · 问题在哪

智能体产出了一个几乎正确的答案。也许一行代码有语法错误。也许一篇摘要太长。也许一个计划漏了一个边界情况。你想要的是：智能体批评自己的输出，然后把它修好。

Self-Refine 证明这件事用单个模型就能做到：无训练数据、无 RL。但有一个坑：LLM 在硬事实上的自我验证很糟糕。CRITIC 点名了修法——把验证步骤路由到外部工具（搜索、代码解释器、计算器、测试运行器）。

这两篇论文共同定义了 2026 年迭代改进的默认做法：生成、验证（尽可能外部）、精修、验证器通过即停。

> An agent produces an answer that is almost right. Maybe a line of code has a syntax error. Maybe a summary is too long. Maybe a plan misses an edge case. What you want is: the agent critiques its own output, then fixes it.
> Self-Refine shows this works with a single model, no training data, no RL. But there is a catch: LLMs are bad at self-verification on hard facts. CRITIC names the fix — route the verify step through external tools (search, code interpreter, calculator, test runner).
> Together these two papers define the 2026 default for iterative improvement: generate, verify (externally when possible), refine, stop when the verifier passes.

---

## The Concept · 概念

### Self-Refine (Madaan et al., NeurIPS 2023)

一个 LLM，三个角色：

```
generate(task)            -> output_0
feedback(task, output_0)  -> critique_0
refine(task, output_0, critique_0, history) -> output_1
feedback(task, output_1)  -> critique_1
refine(task, output_1, critique_1, history) -> output_2
...
stop when feedback says "no issues" or budget exhausted.
```

关键细节：`refine` 看得到完整历史——所有先前的输出和批评——所以它不会重复犯错。论文做了消融实验：去掉 history，质量骤降。

标题数字：7 个任务（数学、代码、缩写、对话）平均绝对提升 +20，包括 GPT-4。无训练、无外部工具、单模型。

> One LLM, three roles.
> Key detail: `refine` sees the full history — all prior outputs and critiques — so it does not repeat mistakes. The paper ablates this: drop history and quality drops sharply.
> Headline: +20 absolute improvement averaged across 7 tasks (math, code, acronym, dialog) including GPT-4. No training, no external tools, single model.

---

### CRITIC (Gou et al., arXiv:2305.11738, v4 Feb 2024)

Self-Refine 的弱点：反馈步骤是一个 LLM 在给自己打分。对事实性声明来说这不可靠（一个幻觉往往对产生它的模型自己显得很有说服力）。CRITIC 把 `feedback(task, output)` 换成 `verify(task, output, tools)`，其中 `tools` 包括：

- 一个搜索引擎，用于事实性声明。
- 一个代码解释器，用于代码正确性。
- 一个计算器，用于算术。
- 领域专用验证器（单元测试、类型检查器、linter）。

验证器产出一份以工具结果为锚的结构化批评。精修器随后以这份批评为条件。

标题数字：CRITIC 在事实性任务上胜过 Self-Refine，因为批评是有锚的。在没有外部验证器的任务（创意写作、排版格式）上，CRITIC 退化为 Self-Refine。

> Self-Refine's weakness: the feedback step is an LLM scoring itself. For factual claims this is unreliable (a hallucination often looks convincing to the model that produced it). CRITIC replaces `feedback(task, output)` with `verify(task, output, tools)` where `tools` includes: a search engine for factual claims; a code interpreter for code correctness; a calculator for arithmetic; domain-specific verifiers (unit tests, type checkers, linters).
> The verifier produces a structured critique grounded in tool results. The refiner then conditions on this critique.
> Headline: CRITIC outperforms Self-Refine on factual tasks because the critique is grounded. On tasks without external verifiers (creative writing, formatting), CRITIC reduces to Self-Refine.

---

### The stop condition · 停止条件

两种常见形状：

1. **验证器通过。** 外部测试返回成功。可用时优先采用（单元测试、类型检查器、guardrail 断言）。
2. **没有反馈发出。** 模型说「输出没问题」。更便宜但不可靠；要配一个最大迭代次数上限。

2026 年的默认做法：两者结合。「验证器通过 OR（模型说没问题 AND 迭代次数 >= 2）OR 迭代次数 >= max_iterations 时停止。」

> Two common shapes:
> 1. **Verifier passes.** External test returns success. Preferred when available (unit tests, type checker, guardrail assertion).
> 2. **No feedback issued.** Model says "the output is fine." Cheaper but unreliable; pair with a max-iteration cap.
>
> 2026 default: combine them. "Stop if verifier passes OR model says fine AND iterations >= 2 OR iterations >= max_iterations."

---

### Evaluator-Optimizer (Anthropic, 2024)

Anthropic 2024 年 12 月的文章把它列为五种 workflow 模式之一。两个角色：

- Evaluator：给输出打分并产出批评。
- Optimizer：根据批评修订输出。

循环直到 evaluator 通过。这就是 Anthropic 视角下的 Self-Refine/CRITIC。Anthropic 加上的关键工程细节：evaluator 和 optimizer 的提示词应当在结构上显著不同，免得模型只是走过场盖章。

> Anthropic's Dec 2024 post names this as one of the five workflow patterns. Two roles: Evaluator scores the output and produces a critique; Optimizer revises the output given the critique.
> Loop until the evaluator passes. This is Self-Refine/CRITIC in Anthropic's framing. The critical engineering detail Anthropic adds: the evaluator and optimizer prompts should be substantially different so the model does not just rubber-stamp.

---

### OpenAI Agents SDK output guardrails · OpenAI Agents SDK 的输出 guardrail

OpenAI Agents SDK 以「output guardrails」的形态内置这个模式。guardrail 是一个跑在智能体最终输出上的验证器。如果 guardrail 触发（抛出 `OutputGuardrailTripwireTriggered`），输出被拒绝，智能体可以重试。guardrail 可以调用工具（CRITIC 式），也可以是纯函数（Self-Refine 式）。

> OpenAI Agents SDK ships this pattern as "output guardrails." A guardrail is a validator that runs on the final output of an agent. If the guardrail trips (raises `OutputGuardrailTripwireTriggered`), the output is rejected and the agent can retry. Guardrails can call tools (CRITIC-style) or be pure functions (Self-Refine-style).

---

### 2026 pitfalls · 2026 年的坑

- **盖章循环。** 同一个模型用同样的提示词风格做生成和批评，最终会收敛到「我觉得没问题」。用结构上不同的提示词，或者用一个更小更便宜的模型做批评。
- **过度精修。** 每一轮 refine 都增加延迟和 token。预算 1–3 轮；之后升级到人工复核。
- **在琐碎任务上用 CRITIC。** 如果没有外部验证器，CRITIC 就退化为 Self-Refine；别为一个摆设验证器付出延迟。

> **Rubber-stamp loops.** Same model doing generation and critique with the same prompt style converges on "looks good to me." Use structurally different prompts, or a smaller cheap model for critique.
> **Over-refinement.** Each refine pass adds latency and tokens. Budget 1-3 passes; after that, escalate to human review.
> **CRITIC on trivial tasks.** If there is no external verifier, CRITIC degenerates to Self-Refine; do not pay the latency for a stub verifier.

```figure
self-refine
```

---

## Build It · 动手造

`code/main.py` 在一个玩具任务上实现 Self-Refine 和 CRITIC：给定一个主题，产出一个短 bullet 列表。验证器检查格式（3 个 bullet，每个不超过 60 字符）。CRITIC 增加一个外部「事实验证器」，惩罚已知的幻觉。

组件：

- `generate` —— 脚本化生产者。
- `feedback` —— LLM 式自我批评。
- `verify_external` —— CRITIC 式有锚验证器。
- `refine` —— 结合历史重写输出。
- 停止条件 —— 验证器通过或最多 4 次迭代。

跑起来：

```
python3 code/main.py
```

对比 Self-Refine 与 CRITIC 两次运行。CRITIC 抓到了 Self-Refine 漏掉的一处事实错误，因为外部验证器拥有自我批评者所没有的锚。

> `code/main.py` implements Self-Refine and CRITIC on a toy task: produce a short bullet list given a topic. The verifier checks format (3 bullets, each under 60 chars). CRITIC adds an external "fact verifier" that penalizes known hallucinations.
> Compare the Self-Refine vs CRITIC runs. CRITIC catches a factual error Self-Refine missed because the external verifier has grounding the self-critic does not.

---

## Use It · 实战用法

Anthropic 的 evaluator-optimizer 就是用 Claude 友好语言表述的这个模式。OpenAI Agents SDK 的输出 guardrails 是 CRITIC 形状的（guardrail 可以调用工具）。LangGraph 内置了一个读起来像 Self-Refine 的 reflection 节点。Google 的 Gemini 2.5 Computer Use 加了一个每步安全评估器，是 CRITIC 的变体：每个动作在提交前都先被验证。

> Anthropic's evaluator-optimizer is this pattern in Claude-friendly language. OpenAI Agents SDK's output guardrails are CRITIC-shaped (guardrails can call tools). LangGraph ships a reflection node that reads like Self-Refine. Google's Gemini 2.5 Computer Use adds a per-step safety evaluator that is a CRITIC variant: every action is verified before commit.

---

## Ship It · 交付

`outputs/skill-refine-loop.md` 在给定任务形状、验证器可用性和迭代预算的前提下，配置一个 evaluator-optimizer 循环。它为生成器、评估器/验证器和优化器输出提示词，外加一条停止策略。

> `outputs/skill-refine-loop.md` configures an evaluator-optimizer loop given task shape, verifier availability, and iteration budget. Emits prompts for generator, evaluator/verifier, and optimizer, plus a stop policy.

---

## Exercises · 练习

1. 用 max_iterations=1 跑这个玩具。CRITIC 还能帮上忙吗？
2. 把外部验证器换成一个带噪声的（随机 30% 误报）。循环会怎么表现？这就是 2026 年大多数 guardrail 技术栈的现实。
3. 实现一个「生成器与批评器用不同模型」的变体：大模型生成，小模型批评。它能打败同模型方案吗？
4. 读 CRITIC 第 3 节（arXiv:2305.11738 v4）。说出三类验证工具，并各举一个例子。
5. 把 OpenAI Agents SDK 的 `output_guardrails` 对应到 CRITIC 的验证器角色。SDK 哪里做错了，哪里做对了？

> 1. Run the toy with max_iterations=1. Does CRITIC still help?
> 2. Replace the external verifier with a noisy one (random 30% false positives). What does the loop do? This is the 2026 reality of most guardrail stacks.
> 3. Implement a "generator-critic on different models" variant: big model generates, small model critiques. Does it beat same-model?
> 4. Read CRITIC Section 3 (arXiv:2305.11738 v4). Name the three verification-tool categories and give an example for each.
> 5. Map OpenAI Agents SDK's `output_guardrails` to CRITIC's verifier role. What does the SDK get wrong, and what does it get right?

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Self-Refine | 「会自我修复的 LLM」 | 单模型内的 generate -> feedback -> refine 循环，带 history |
| CRITIC | 「工具锚定的验证」 | 用外部验证器（搜索、代码、计算器、测试）替换 feedback |
| Evaluator-Optimizer | 「Anthropic 的 workflow 模式」 | 两个角色——evaluator 打分、optimizer 修订——循环到收敛 |
| Output guardrail | 「事后检查」 | OpenAI Agents SDK 的验证器，在智能体产出输出之后运行 |
| Verify step | 「批评阶段」 | 承重的决策点：有锚验证还是自我评级 |
| Refine history | 「模型已经试过什么」 | 先前输出 + 批评前置到 refine 提示词；去掉它质量就崩 |
| Rubber-stamp loop | 「自我同意失败」 | 同款提示词的批评只会回「看起来不错」；用结构不同的提示词修复 |
| Stop condition | 「收敛测试」 | 验证器通过 OR 无反馈 AND 迭代上限；永远不要单条件 |

> | Term | What people say | What it actually means |
> |------|----------------|------------------------|
> | Self-Refine | "LLM that fixes itself" | Generate -> feedback -> refine loop in one model, with history |
> | CRITIC | "Tool-grounded verification" | Replace feedback with an external verifier (search, code, calc, tests) |
> | Evaluator-Optimizer | "Anthropic workflow pattern" | Two roles — evaluator scores, optimizer revises — looped to convergence |
> | Output guardrail | "Post-hoc check" | OpenAI Agents SDK validator that runs after an agent produces output |
> | Verify step | "Critique phase" | The load-bearing decision: grounded or self-rated |
> | Refine history | "What the model already tried" | Prior outputs + critiques prepended to refine prompt; drop and quality collapses |
> | Rubber-stamp loop | "Self-agreement failure" | Same-prompt critique returns "looks good"; fix with structurally different prompts |
> | Stop condition | "Convergence test" | Verifier passes OR no feedback AND iteration cap; never single-condition |

---

## Further Reading · 延伸阅读

- [Madaan et al., Self-Refine (arXiv:2303.17651)](https://arxiv.org/abs/2303.17651) —— 规范论文
- [Gou et al., CRITIC (arXiv:2305.11738)](https://arxiv.org/abs/2305.11738) —— 工具锚定的验证
- [Anthropic, Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) —— evaluator-optimizer workflow 模式
- [OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/) —— 作为 CRITIC 形状验证器的输出 guardrails

> - [Madaan et al., Self-Refine (arXiv:2303.17651)](https://arxiv.org/abs/2303.17651) — the canonical paper
> - [Gou et al., CRITIC (arXiv:2305.11738)](https://arxiv.org/abs/2305.11738) — tool-grounded verification
> - [Anthropic, Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) — evaluator-optimizer workflow pattern
> - [OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/) — output guardrails as CRITIC-shaped verifiers
