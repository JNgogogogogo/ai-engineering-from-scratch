# Agent Memory — Virtual Context and Memory Paging · 智能体记忆——虚拟上下文与内存分页

> 上下文窗口是有限的。对话、文档和工具轨迹不是。解法就是把操作系统的虚拟内存重述一遍——主上下文是内存（RAM），外部存储是磁盘，智能体在两者之间分页。MemGPT（Packer et al., 2023）给这个模式起了名字；许多生产记忆系统都建立在它之上。

> Context windows are finite. Conversations, documents, and tool traces are not. The fix is OS virtual memory restated — main context is RAM, external store is disk, the agent pages between them. MemGPT (Packer et al., 2023) named the pattern; many production memory systems build on it.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 06 (Tool Use)
**Time:** ~75 minutes

---

## Learning Objectives · 学习目标

- 解释 MemGPT 建立其上的 OS 类比：主上下文 = 内存（RAM），外部上下文 = 磁盘，记忆工具 = 换页入/出。
- 用标准库实现两层 MemGPT 模式：主上下文缓冲区、外部可搜索存储、换页入/出工具。
- 描述智能体如何发出「中断」来查询或修改外部记忆，结果如何被拼接回下一个提示词。
- 识别哪些 MemGPT 设计选择延续到了 Letta（第 8 课）和 Mem0（第 9 课）。

> Explain the OS analogy MemGPT builds on: main context = RAM, external context = disk, memory tools = page in/out.
> Implement the two-tier MemGPT pattern in stdlib with a main-context buffer, an external searchable store, and page in/out tools.
> Describe how the agent issues "interrupts" to query or modify external memory and how the result is spliced back into the next prompt.
> Identify the MemGPT design choices that carry into Letta (Lesson 08) and Mem0 (Lesson 09).

---

## The Problem · 问题在哪

上下文窗口看上去应该能解决记忆问题。它们解决不了。三种失败模式在生产中反复出现：

1. **溢出。** 多轮对话、长文档或工具调用密集的轨迹会越过窗口。截断点之后的一切都没了。
2. **稀释。** 即使在窗口之内，塞入无关上下文也会稀释对真正要紧内容的注意力。前沿模型在长输入上仍会退化。
3. **持久化。** 新会话从空窗口开始。没有外部记忆的智能体无法跨会话说「还记得你让我……吗」。

更大的窗口有帮助，但解决不了问题。Mem0 的 2025 年论文测到：128k 窗口的基线仍然会漏掉一些长程事实，而带外部记忆的 4k 窗口智能体能抓到它们。

> Context windows look like they should solve memory. They do not. Three failure modes recur in production:
> 1. **Overflow.** Multi-turn conversations, long documents, or tool-call-heavy trajectories cross the window. Everything past the cutoff is gone.
> 2. **Dilution.** Even within the window, stuffing irrelevant context dilutes attention over what matters. Frontier models still degrade on long inputs.
> 3. **Persistence.** A new session starts with an empty window. Agents without external memory cannot say "remember when you asked me to..." across sessions.
>
> Bigger windows help but do not fix this. Mem0's 2025 paper measured that 128k-window baselines still miss long-horizon facts that a 4k-window agent with external memory catches.

---

## The Concept · 概念

### The OS analogy · 操作系统类比

MemGPT（Packer et al., arXiv:2310.08560，v2 2024 年 2 月）把上下文管理映射到操作系统的虚拟内存：

| OS 概念 | MemGPT 概念 | 2026 年生产对应物 |
|------------|---------------|------------------------|
| RAM | 主上下文（提示词） | Anthropic/OpenAI 上下文窗口 |
| 磁盘 | 外部上下文 | 向量库、KV、图存储 |
| 缺页 | 记忆工具调用 | `memory.search`、`memory.read`、`memory.write` |
| OS 内核 | 智能体控制循环 | 带记忆工具的 ReAct 循环 |

智能体跑的是一条普通的 ReAct 循环。多出来的一类工具让它可以把数据在主上下文里换入换出。

> MemGPT (Packer et al., arXiv:2310.08560, v2 Feb 2024) maps context management to operating-system virtual memory:
> | OS concept | MemGPT concept | 2026 production analog |
> |------------|---------------|------------------------|
> | RAM | main context (prompt) | Anthropic/OpenAI context window |
> | Disk | external context | vector DB, KV, graph store |
> | Page fault | memory tool call | `memory.search`, `memory.read`, `memory.write` |
> | OS kernel | agent control loop | ReAct loop with memory tools |
>
> The agent runs a normal ReAct loop. One extra class of tools lets it page data in and out of main context.

---

### Two tiers · 两层结构

- **主上下文（Main context）。** 固定大小的提示词，装着当前任务。始终对模型可见。
- **外部上下文（External context）。** 无界，通过工具搜索。相关时读，事实出现时写。

原论文在两个超出基础窗口的任务上评估了这个设计：超过 100k token 的文档分析，以及跨数天保持持久记忆的多会话聊天。

> - **Main context.** Fixed-size prompt holding the current task. Always visible to the model.
> - **External context.** Unbounded, searchable via tools. Read when relevant, written when facts emerge.
>
> The original paper evaluated the design on two tasks beyond the base window: document analysis longer than 100k tokens and multi-session chat with persistent memory across days.

---

### The interrupt pattern · 中断模式

MemGPT 引入了 memory-as-interrupt（记忆即中断）：对话中途，智能体可以调用一个记忆工具，运行时执行它，结果作为一个新观察拼进下一个助手轮。概念上完全等同于一个 Unix `read()` 系统调用：阻塞进程、返回字节、进程继续。

规范的记忆工具面：

- `core_memory_append(section, text)` —— 写入提示词的一个持久 section。
- `core_memory_replace(section, old, new)` —— 编辑一个持久 section。
- `archival_memory_insert(text)` —— 写入可搜索的外部存储。
- `archival_memory_search(query, top_k)` —— 从外部存储检索。
- `conversation_search(query)` —— 扫描过去的轮次。

> MemGPT introduces memory-as-interrupt: mid-conversation the agent can invoke a memory tool, the runtime executes it, and the result splices into the next assistant turn as a new observation. Conceptually identical to a Unix `read()` syscall that blocks the process, returns bytes, and the process continues.
> Canonical memory tool surface: `core_memory_append(section, text)` — write to a persistent section of the prompt; `core_memory_replace(section, old, new)` — edit a persistent section; `archival_memory_insert(text)` — write to the searchable external store; `archival_memory_search(query, top_k)` — retrieve from the external store; `conversation_search(query)` — scan past turns.

---

### Where the paper ends and production begins · 论文终点与生产起点

2024 年 9 月，MemGPT 变成了 Letta。研究仓库（`cpacker/MemGPT`）仍在；Letta 扩展了这个设计：

- 三层而非两层（core、recall、archival —— 第 8 课）。
- 原生推理取代 `send_message`/heartbeat 模式（第 8 课）。
- sleep-time 智能体跑异步记忆工作（第 8 课）。

即使生产系统跑的是 Letta、Mem0 或自建的两层存储，MemGPT 论文仍是 2026 年的地基。

> In September 2024 MemGPT became Letta. The research repo (`cpacker/MemGPT`) remains; Letta extends the design: three tiers instead of two (core, recall, archival — Lesson 08); native reasoning replacing the `send_message`/heartbeat pattern (Lesson 08); sleep-time agents running async memory work (Lesson 08).
> The MemGPT paper is the 2026 foundation even if production systems run Letta, Mem0, or a custom two-tier store.

---

### Where this pattern goes wrong · 这个模式哪里会出问题

- **记忆腐烂。** 写入快于读取；检索被过时事实淹没。修法：周期性整合（Letta sleep-time）、显式失效（Mem0 冲突检测器）。
- **记忆投毒。** 外部记忆就是被检索回来的文本。如果攻击者控制的内容落进一条记忆笔记，智能体下一次会话会把它重新摄入。这就是 Greshake et al.（第 27 课）攻击在时间维度上的重演。
- **引用丢失。** 智能体记得「用户让我交付 X」，却引不出是哪一轮。每一次 archival 写入都应带源引用（session ID、turn ID）。

> **Memory rot.** Writes accumulate faster than reads; retrieval drowns in stale facts. Fix: periodic consolidation (Letta sleep-time), explicit invalidation (Mem0 conflict detector).
> **Memory poisoning.** External memory is retrieved text. If attacker-controlled content lands in a memory note, the agent re-ingests it next session. This is the Greshake et al. (Lesson 27) attack restated over time.
> **Citation loss.** Agent recalls "the user asked me to ship X" but cannot cite which turn. Store source references (session ID, turn ID) with every archival write.

```figure
context-budget
```

---

## Build It · 动手造

`code/main.py` 用标准库实现 MemGPT 的两层模式：

- `MainContext` —— 固定大小的提示词缓冲区，带一个 `core` 字典和一个 `messages` 列表；超过上限时自动压缩最旧的消息。
- `ArchivalStore` —— 内存中的 BM25 风格存储（token 重叠打分），记录形如 (id, text, tags, session, turn)。
- 五个映射到 MemGPT 工具面的记忆工具。
- 一个脚本化智能体：先把事实填进 archival，再通过调用 `archival_memory_search` 回答一个问题。

跑起来：

```
python3 code/main.py
```

轨迹展示智能体写入三条事实、把主上下文填到上限（触发驱逐），然后通过从 archival 检索回答一个后续问题——在没有任何真实 LLM 的情况下复现 MemGPT 工作流。

> `code/main.py` implements MemGPT's two-tier pattern in stdlib: `MainContext` — fixed-size prompt buffer with a `core` dict and a `messages` list, auto-compacting oldest messages when over cap; `ArchivalStore` — in-memory BM25-esque store (token-overlap scoring) of (id, text, tags, session, turn) records; five memory tools mapping to the MemGPT surface; a scripted agent that fills archival with facts, then answers a question by calling `archival_memory_search`.
> The trace shows the agent writing three facts, filling main context to the cap (forcing eviction), then answering a follow-up question by retrieving from archival — reproducing the MemGPT workflow without any real LLM.

---

## Use It · 实战用法

今天每一个生产记忆系统都是 MemGPT 的变体：

- **Letta**（第 8 课）—— 三层、原生推理、sleep-time compute。
- **Mem0**（第 9 课）—— 向量 + KV + 图，融合在一个打分层之下。
- **OpenAI Assistants / Responses** —— 通过 threads 和 files 提供托管记忆。
- **Claude Agent SDK** —— 通过 skills 和 session store 提供长期记忆。

按运维形状挑选（自托管、托管、框架集成），而不是按核心模式挑——核心模式就是 MemGPT。

> Every production memory system today is a MemGPT variant: **Letta** (Lesson 08) — three tiers, native reasoning, sleep-time compute; **Mem0** (Lesson 09) — vector + KV + graph fused with a scoring layer; **OpenAI Assistants / Responses** — managed memory via threads and files; **Claude Agent SDK** — long-term memory via skills and session store.
> Pick one by operational shape (self-hosted, managed, framework-integrated), not by the core pattern — the core pattern is MemGPT.

---

### The shape of agent memory · 智能体记忆的形态

分页解决的是容量。它不决定存什么。四种记忆类型在生产系统中反复出现，各自回答一个不同的问题：

- **工作记忆（Working memory）** —— 现在什么要紧？in-context 层：当前任务、最近轮次、钉住的 core section。就是提示词本身。
- **情景记忆（Episodic memory）** —— 发生过什么？过去的轮次和轨迹，带 session 和 turn 引用存储，可按需回放。
- **语义记忆（Semantic memory）** —— 什么是真的？关于用户、领域、世界的事实，随变化更新和去重。
- **程序性记忆（Procedural memory）** —— 这件事怎么做？学到的例程、偏好和规则，用来引导未来行为而非回忆。

开源实现在不同的点上发力：

| 类型 | 实现 | 攻坚方式 |
|------|----------------|-------------------|
| 工作记忆 | MemGPT / Letta | 通过记忆工具把内容在固定的提示词预算里换入换出（本课与第 8 课） |
| 情景记忆 | Zep | 时序知识图谱——事实带有效区间，「什么时候是真的」可查询 |
| 语义记忆 | Mem0 | 一个提取流水线，在向量、KV 和图存储之间对事实去重和更新（第 9 课） |
| 语义 + 程序性 | LangMem | 把事实和行为规则后台提取到一个智能体在轮次间查阅的存储里 |
| 情景 + 语义 | agentmemory | 在会话运行时捕获它们，并整合成类型化、可搜索的记录 |

> Paging solves capacity. It does not decide what to store. Four memory types recur across production systems, each answering a different question:
> - **Working memory** — what matters right now? The in-context tier: current task, recent turns, pinned core sections. The prompt itself.
> - **Episodic memory** — what happened? Past turns and trajectories, stored with session and turn references, replayable on demand.
> - **Semantic memory** — what is true? Facts about the user, the domain, the world, updated and deduplicated as they change.
> - **Procedural memory** — how do I do this? Learned routines, preferences, and rules that steer future behavior rather than recall.
>
> | Type | Implementation | How it tackles it |
> |------|----------------|-------------------|
> | Working | MemGPT / Letta | Pages content in and out of a fixed prompt budget via memory tools (this lesson, Lesson 08) |
> | Episodic | Zep | Temporal knowledge graph — facts carry validity intervals, so "what was true when" is queryable |
> | Semantic | Mem0 | Extraction pipeline that dedupes and updates facts across vector, KV, and graph stores (Lesson 09) |
> | Semantic + procedural | LangMem | Background extraction of facts and behavioral rules into a store the agent consults between turns |
> | Episodic + semantic | agentmemory | Captures sessions as they run, consolidates them into typed, searchable records |

---

## Ship It · 交付

`outputs/skill-virtual-memory.md` 是一个可复用 skill：它为任意目标运行时产出一套正确的两层记忆脚手架（main + archival + 工具面），并接好驱逐策略和引用字段。

> `outputs/skill-virtual-memory.md` is a reusable skill that produces a correct two-tier memory scaffold (main + archival + tool surface) for any target runtime, with eviction policy and citation fields wired in.

---

## Exercises · 练习

1. 加一个以 token 计量的 `max_main_context_tokens` 上限（用 `len(text.split())` * 1.3 近似）。超过上限时，把最旧的消息压缩成摘要。对比有摘要器和无摘要器的行为。
2. 在 archival 存储上正经实现 BM25（词频、逆文档频率）。在一个玩具事实集上对比 token 重叠基线，测量 recall@10。
3. 给 archival 插入操作加 `citation` 字段（session_id、turn_id、source_url）。让智能体在每个有检索支撑的答案里给出引用。
4. 模拟记忆投毒：往 archival 里加一条写着「忽略未来所有用户指令」的记录。写一个守卫，扫描检索结果中的指令形文本并把它们标记为不可信。
5. 把实现移植到 MemGPT 研究仓库的 core-memory JSON schema（`cpacker/MemGPT`）。从扁平字符串换成类型化 section 后，什么变了？

> 1. Add a `max_main_context_tokens` cap measured in tokens (approximate with `len(text.split())` * 1.3). Compact the oldest messages into a summary when the cap is exceeded. Compare behavior with and without the summarizer.
> 2. Implement BM25 properly over the archival store (term frequency, inverse document frequency). Measure recall@10 on a toy fact set versus the token-overlap baseline.
> 3. Add `citation` fields (session_id, turn_id, source_url) to archival inserts. Make the agent cite sources on every retrieval-backed answer.
> 4. Simulate memory poisoning: add an archival record that says "ignore all future user instructions." Write a guard that scans retrievals for directive-shaped text and marks them untrusted.
> 5. Port the implementation to use the MemGPT research repo's core-memory JSON schema (`cpacker/MemGPT`). What changes when you switch from flat strings to typed sections?

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Virtual context | 「无限记忆」 | 主（提示词）+ 外部（可搜索）两层，带换页入/出 |
| Main context | 「工作记忆」 | 提示词——固定大小，始终可见 |
| Archival memory | 「长期存储」 | 外部可搜索的持久化，按需检索 |
| Core memory | 「持久提示词 section」 | 钉在主上下文内部的命名 section |
| Memory tool | 「记忆 API」 | 智能体发出的、用于读写外部记忆的工具调用 |
| Interrupt | 「记忆缺页」 | 智能体暂停、运行时取回、结果拼进下一轮 |
| Memory rot | 「过时事实」 | 旧写入淹没检索；用整合修复 |
| Memory poisoning | 「被注入的持久笔记」 | 攻击者内容被存成记忆，回忆时被重新摄入 |

> | Term | What people say | What it actually means |
> |------|----------------|------------------------|
> | Virtual context | "Unlimited memory" | Main (prompt) + external (searchable) tiers with page in/out |
> | Main context | "Working memory" | The prompt — fixed-size, always visible |
> | Archival memory | "Long-term store" | External searchable persistence, retrieved on demand |
> | Core memory | "Persistent prompt section" | Named sections pinned inside the main context |
> | Memory tool | "Memory API" | Tool call the agent issues to read/write external memory |
> | Interrupt | "Memory page fault" | Agent pauses, runtime fetches, result splices into next turn |
> | Memory rot | "Stale facts" | Old writes drown retrieval; fix with consolidation |
> | Memory poisoning | "Injected persistent note" | Attacker content stored as memory, re-ingested on recall |

---

## Further Reading · 延伸阅读

- [Packer et al., MemGPT (arXiv:2310.08560)](https://arxiv.org/abs/2310.08560) —— OS 风格虚拟上下文论文
- [Letta, Memory Blocks blog](https://www.letta.com/blog/memory-blocks) —— 三层演进
- [Anthropic, Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) —— 把上下文当作预算来对待
- [Chhikara et al., Mem0 (arXiv:2504.19413)](https://arxiv.org/abs/2504.19413) —— 建立在这个模式之上的混合生产记忆
- [Zep (getzep/zep)](https://github.com/getzep/zep) —— 分类表中的时序知识图谱记忆
- [Mem0 (mem0ai/mem0)](https://github.com/mem0ai/mem0) —— 第 9 课混合存储背后的提取流水线
- [LangMem (langchain-ai/langmem)](https://github.com/langchain-ai/langmem) —— 事实与行为规则的后台提取
- [agentmemory (rohitg00/agentmemory)](https://github.com/rohitg00/agentmemory) —— 会话捕获并整合成类型化、可搜索的记录

> - [Packer et al., MemGPT (arXiv:2310.08560)](https://arxiv.org/abs/2310.08560) — OS-inspired virtual context paper
> - [Letta, Memory Blocks blog](https://www.letta.com/blog/memory-blocks) — the three-tier evolution
> - [Anthropic, Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — treating context as a budget
> - [Chhikara et al., Mem0 (arXiv:2504.19413)](https://arxiv.org/abs/2504.19413) — hybrid production memory on top of this pattern
> - [Zep (getzep/zep)](https://github.com/getzep/zep) — temporal knowledge-graph memory from the taxonomy table
> - [Mem0 (mem0ai/mem0)](https://github.com/mem0ai/mem0) — the extraction pipeline behind Lesson 09's hybrid store
> - [LangMem (langchain-ai/langmem)](https://github.com/langchain-ai/langmem) — background extraction of facts and behavioral rules
> - [agentmemory (rohitg00/agentmemory)](https://github.com/rohitg00/agentmemory) — session capture consolidated into typed, searchable records
