# Memory Blocks and Sleep-Time Compute · 记忆块与睡眠期计算

> 离散的、功能化的记忆块，模型可以直接编辑它们；再配一个 sleep-time 智能体，在主智能体空闲时异步整合记忆。这两个想法就是你把记忆扩展到单场对话之外的方法。

> Discrete functional memory blocks the model can edit directly, and a sleep-time agent that consolidates memory asynchronously while the primary agent is idle. These two ideas are how you scale memory beyond one conversation.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 07 (MemGPT)
**Time:** ~75 minutes

---

## Learning Objectives · 学习目标

- 说出 Letta 使用的三层记忆（core、recall、archival）及各自的角色。
- 解释记忆块模式：Human block、Persona block 以及作为一等类型化对象的用户自定义块。
- 描述 sleep-time compute 是什么、为什么它在关键路径之外、以及为什么它可以跑一个比主智能体更强的模型。
- 实现一个脚本化的双智能体循环：主智能体负责应答，sleep-time 智能体在轮次之间整合块。

> Name the three memory tiers Letta uses (core, recall, archival) and the role of each.
> Explain the memory-block pattern: Human block, Persona block, and user-defined blocks as first-class typed objects.
> Describe what sleep-time compute is, why it sits off the critical path, and why it can run a stronger model than the primary agent.
> Implement a scripted two-agent loop where a primary agent serves responses and a sleep-time agent consolidates blocks between turns.

---

## The Problem · 问题在哪

MemGPT（第 7 课）解决了虚拟内存的控制流。三个生产问题随之浮现：

1. **延迟。** 每次记忆操作都压在关键路径上。如果智能体必须在用户等待时修剪、总结或调和记忆，尾延迟就会爆掉。
2. **记忆腐烂。** 写入不断累积。被推翻的事实留着不走。检索被过时内容淹没。
3. **结构丢失。** 一个扁平的 archival 存储无法表达「Human block 永远在提示词里；Persona block 永远在提示词里；Task block 每个会话换一个」。

Letta（letta.com）是原 MemGPT 项目 2024 年起采用的平台名——论文里的模式仍叫 MemGPT——而 2026 年的 Letta V1 重写是更晚的另一独立步骤。记忆块让结构显式；sleep-time compute 把整合移出关键路径。

> MemGPT (Lesson 07) solved the virtual-memory control flow. Three production problems emerged:
> 1. **Latency.** Every memory operation sits on the critical path. If the agent has to prune, summarize, or reconcile while the user waits, tail latency blows up.
> 2. **Memory rot.** Writes accumulate. Contradicted facts stay. Retrieval drowns in stale content.
> 3. **Structure loss.** A flat archival store cannot express "the Human block is always in the prompt; the Persona block is always in the prompt; the Task block swaps per session."
>
> Letta (letta.com) is the platform name the original MemGPT project adopted in 2024 — the paper's pattern keeps the MemGPT name — and the 2026 Letta V1 rewrite is a later, separate step. Memory blocks make structure explicit; sleep-time compute moves consolidation off the critical path.

---

## The Concept · 概念

### Three tiers · 三层结构

| 层 | 范围 | 存放位置 | 写入者 |
|------|-------|----------------|------------|
| Core | 始终可见 | 主提示词内部 | 智能体工具调用 + sleep-time 重写 |
| Recall | 对话历史 | 可检索 | 自动的轮次日志记录 |
| Archival | 任意事实 | 向量 + KV + 图 | 智能体工具调用 + sleep-time 摄取 |

Core 就是 MemGPT 的 core。Recall 是带上被驱逐尾部的对话缓冲区。Archival 是外部存储。这个拆分清理了 MemGPT 两层结构里的职责过载。

> | Tier | Scope | Where it lives | Written by |
> |------|-------|----------------|------------|
> | Core | Always visible | Inside the main prompt | Agent tool call + sleep-time rewrites |
> | Recall | Conversation history | Retrievable | Automatic turn logging |
> | Archival | Arbitrary facts | Vector + KV + graph | Agent tool call + sleep-time ingest |
>
> Core is the MemGPT core. Recall is the conversation buffer with its evicted tail. Archival is the external store. The split cleans up MemGPT's two-tier overloading.

---

### Memory blocks · 记忆块

块是 core 层中一个类型化、持久、可编辑的 section。原 MemGPT 论文定义了两个：

- **Human block** —— 关于用户的事实（姓名、角色、偏好、目标）。
- **Persona block** —— 智能体的自我概念（身份、语气、约束）。

Letta 推广到任意的用户自定义块：装当前目标的 `Task` 块、装代码库事实的 `Project` 块、装硬约束的 `Safety` 块。每个块有 `id`、`label`、`value`、`limit`（字符上限）、`description`（让模型知道什么时候该编辑它）。

块通过工具面编辑：

- `block_append(label, text)`
- `block_replace(label, old, new)`
- `block_read(label)`
- `block_summarize(label)` —— 压缩一个接近上限的块。

> A block is a typed, persistent, editable section of the core tier. The original MemGPT paper defined two: **Human block** — facts about the user (name, role, preferences, goals); **Persona block** — the agent's self-concept (identity, tone, constraints).
> Letta generalizes to arbitrary user-defined blocks: a `Task` block for the current goal, a `Project` block for codebase facts, a `Safety` block for hard constraints. Each block has an `id`, `label`, `value`, `limit` (character cap), `description` (so the model knows when to edit it).
> Blocks are editable via the tool surface: `block_append(label, text)`; `block_replace(label, old, new)`; `block_read(label)`; `block_summarize(label)` — condense a block that is near its limit.

---

### Sleep-time compute · 睡眠期计算

Letta 在 2025 年加入的内容：在后台、关键路径之外跑第二个智能体。Sleep-time 智能体处理对话记录和代码库上下文，把 `learned_context` 写进共享块，并整合或失效 archival 记录。

随之而来的性质：

- **零延迟成本。** 主响应不用等记忆操作。
- **可以用更强的模型。** Sleep-time 智能体可以是更贵、更慢的模型，因为它不受延迟约束。
- **天然的整合窗口。** 趁用户不在等的时候去重、总结、失效被推翻的事实。

这个形状和人类的工作方式吻合：你先做任务，睡一觉，长期记忆在夜里沉淀下来。

> The 2025 Letta addition: run a second agent in background, off the critical path. Sleep-time agents process conversation transcripts and codebase context, write `learned_context` into shared blocks, and consolidate or invalidate archival records.
> Properties that fall out: **No latency cost.** Primary responses do not wait for memory ops; **Stronger model allowed.** The sleep-time agent can be a more expensive, slower model because it is not latency-constrained; **Natural consolidation window.** Dedup, summarize, invalidate contradicted facts when the user is not waiting.
> The shape matches how humans work: you do the task, you sleep on it, the long-term memory settles overnight.

---

### Native reasoning · 原生推理

Letta V1（`letta_v1_agent`，2026）废弃了 `send_message`/heartbeat 和内联 `Thought:` token，改用原生推理。Responses API（OpenAI）和带 extended thinking 的 Messages API（Anthropic）都在独立通道上输出推理，跨轮次透传（生产环境中跨提供商加密）。控制循环仍是 ReAct。思考轨迹是结构性的，不是提示词形状的。

> Letta V1 (`letta_v1_agent`, 2026) deprecates `send_message`/heartbeat and inline `Thought:` tokens in favor of native reasoning. The Responses API (OpenAI) and the Messages API with extended thinking (Anthropic) emit reasoning on a separate channel, passed through turns (encrypted across providers in production). The control loop is still ReAct. The thought trace is structural, not prompt-shaped.

---

### Where this pattern goes wrong · 这个模式哪里会出问题

- **块膨胀。** 无限的 `block_append` 很快撞上上限。在会把块顶破的那次写入之前，接一个块摘要器。
- **静默漂移。** Sleep-time 智能体重写了块，主智能体毫无察觉。给块做版本化，并在 trace 里暴露 diff。
- **被投毒的整合。** Sleep-time 智能体把攻击者可达的内容处理进 core。第 27 课同样适用于 sleep-time 面。

> **Block bloat.** Infinite `block_append` hits the limit fast. Wire a block summarizer before the write that pushes over the cap.
> **Silent drift.** Sleep-time agent rewrites a block and the primary agent never notices. Version blocks and surface diffs in the trace.
> **Poisoned consolidation.** Sleep-time agent processes attacker-reachable content into core. Lesson 27 applies to the sleep-time surface too.

```figure
memory-blocks
```

---

## Build It · 动手造

`code/main.py` 实现：

- `Block` —— id、label、value、limit、description。
- `BlockStore` —— CRUD + `near_limit(label)` 辅助函数。
- 两个脚本化智能体 —— `PrimaryAgent` 应答一轮，`SleepTimeAgent` 在轮次之间做整合。
- 一条展示三轮对话（含块写入）的 trace，外加一次 sleep-time 处理：总结一个块并失效一条过时事实。

跑起来：

```
python3 code/main.py
```

记录展示了这种分工：主轮次速度快、产出原始写入；sleep 处理负责压缩和清理。

> `code/main.py` implements: `Block` — id, label, value, limit, description; `BlockStore` — CRUD + `near_limit(label)` helper; two scripted agents — `PrimaryAgent` serves a turn, `SleepTimeAgent` consolidates between turns; a trace that shows a three-turn conversation with block writes, plus a sleep-time pass that summarizes a block and invalidates a stale fact.
> The transcript shows the split: primary turns are fast and produce raw writes; the sleep pass compacts and cleans up.

---

## Use It · 实战用法

- **Letta**（letta.com）作为参考实现。自托管或托管云。
- **Claude Agent SDK skills** 作为块形知识——一个 skill 就是一个命名的、带版本的、可检索的指令块，智能体按需加载。
- **自建** 给想掌控存储后端的团队。沿用 Letta API 契约，以便日后迁移。

> - **Letta** (letta.com) for the reference implementation. Self-host or managed cloud.
> - **Claude Agent SDK skills** as block-shaped knowledge — a skill is a named, versioned, retrievable block of instructions the agent loads on demand.
> - **Custom builds** for teams that want control over the storage backend. Use the Letta API contract so you can migrate later.

---

## Ship It · 交付

`outputs/skill-memory-blocks.md` 为任意运行时生成一套 Letta 形状的块系统，带 sleep-time 钩子，包括安全规则和引用接线。

> `outputs/skill-memory-blocks.md` generates a Letta-shaped block system with sleep-time hooks for any runtime, including safety rules and citation wiring.

---

## Exercises · 练习

1. 加一个 `block_summarize` 工具：当 `near_limit` 返回 true 时，用一个模型生成的摘要替换块值。哪个触发阈值能让摘要调用次数和块溢出都最小？
2. 在 archival 上实现 sleep-time 去重：文本 token 重叠 >90% 的两条记录合并为一条。只在 sleep 处理里做，永远不要放在关键路径上。
3. 给块做版本化。每次写入都记录旧值和一个 diff。暴露 `block_history(label)`，让运维能调试「智能体为什么忘了 X」。
4. 把 sleep-time 智能体当作不可信的写入者。当它们要动 Persona 或 Safety 块时，要求先经过第二个智能体复核再提交。
5. 把示例移植到 Letta API（`letta_v1_agent`）。块 schema 有什么变化，原生推理又如何改变 trace 的形状？

> 1. Add a `block_summarize` tool that replaces the block value with a model-generated summary when `near_limit` returns true. Which trigger threshold minimizes both summarization calls and block overflow?
> 2. Implement sleep-time dedup over archival: two records whose text has >90% token overlap collapse to one. Do it only in the sleep pass, never on the critical path.
> 3. Version blocks. On every write record the old value and a diff. Expose `block_history(label)` so operators can debug "why did the agent forget X."
> 4. Treat sleep-time agents as untrusted writers. When they touch the Persona or Safety block, require a second-agent review before committing.
> 5. Port the example to use the Letta API (`letta_v1_agent`). What changes in the block schema, and how does native reasoning alter the trace shape?

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Memory block | 「可编辑的提示词 section」 | core 记忆中类型化、持久、可被 LLM 编辑的段落 |
| Human block | 「用户记忆」 | 关于用户的事实，钉在 core 里 |
| Persona block | 「智能体身份」 | 自我概念、语气、约束，钉在 core 里 |
| Sleep-time compute | 「异步记忆工作」 | 第二个智能体在关键路径之外做整合 |
| Core / Recall / Archival | 「层」 | 三层记忆拆分：始终可见 / 对话 / 外部 |
| Block limit | 「上限」 | 每块的字符上限；强制触发摘要 |
| Native reasoning | 「思考通道」 | provider 级的推理输出，而不是提示词级的 `Thought:` |
| Learned context | 「sleep 输出」 | Sleep-time 智能体写进共享块的事实 |

> | Term | What people say | What it actually means |
> |------|----------------|------------------------|
> | Memory block | "Editable prompt section" | Typed, persistent, LLM-editable segment of core memory |
> | Human block | "User memory" | Facts about the user, pinned in core |
> | Persona block | "Agent identity" | Self-concept, tone, constraints, pinned in core |
> | Sleep-time compute | "Async memory work" | Second agent doing consolidation off the critical path |
> | Core / Recall / Archival | "Tiers" | Three-layer memory split: always-visible / conversation / external |
> | Block limit | "Cap" | Character limit per block; forces summarization |
> | Native reasoning | "Thinking channel" | Provider-level reasoning output, not prompt-level `Thought:` |
> | Learned context | "Sleep output" | Facts the sleep-time agent writes into shared blocks |

---

## Further Reading · 延伸阅读

- [Letta, Memory Blocks blog](https://www.letta.com/blog/memory-blocks) —— 块模式
- [Letta, Sleep-time Compute blog](https://www.letta.com/blog/sleep-time-compute) —— 异步整合
- [Letta, Rearchitecting the Agent Loop](https://www.letta.com/blog/letta-v1-agent) —— 原生推理重写
- [Packer et al., MemGPT (arXiv:2310.08560)](https://arxiv.org/abs/2310.08560) —— 起源

> - [Letta, Memory Blocks blog](https://www.letta.com/blog/memory-blocks) — the block pattern
> - [Letta, Sleep-time Compute blog](https://www.letta.com/blog/sleep-time-compute) — async consolidation
> - [Letta, Rearchitecting the Agent Loop](https://www.letta.com/blog/letta-v1-agent) — native reasoning rewrite
> - [Packer et al., MemGPT (arXiv:2310.08560)](https://arxiv.org/abs/2310.08560) — the origin
