# 共享内存与黑板模式（Shared Memory and Blackboard Patterns）

> 2026 年的多 agent 系统里共存着两种思路：**消息池**（message pool，所有人都能看到所有人的消息，如 AutoGen GroupChat 或 MetaGPT）和**带订阅的黑板**（blackboard with subscription，agent 订阅自己相关的事件，如 Context-Aware MCP 或 Matrix 框架）。两者都是多 agent 系统中唯一有状态的部分——这也就意味着两者都是有意思的 bug 藏身处。标志性的失效模式是**内存投毒**（memory poisoning）：一个 agent 幻觉出一个「事实」，其他 agent 把它当作已验证的结论，于是准确率逐渐衰减，这种方式比立刻崩溃难调试得多。本课用标准库把两种结构都造出来，注入一次投毒攻击，并展示在生产中真正有效的三种缓解手段。

> Two approaches coexist in 2026 multi-agent systems: the **message pool** (everyone sees everyone's messages, as in AutoGen GroupChat or MetaGPT) and the **blackboard with subscription** (agents subscribe to relevant events, as in Context-Aware MCP or the Matrix framework). Both are the only stateful part of a multi-agent system — which means both are where the interesting bugs live. The reference failure mode is **memory poisoning**: one agent hallucinates a "fact," other agents treat it as verified, and accuracy decays gradually in a way that is much harder to debug than an immediate crash. This lesson builds both structures from stdlib, injects a poisoning attack, and shows the three mitigations that actually work in production.

**Type:** Learn + Build
**Languages:** Python（stdlib、`threading`）
**Prerequisites:** Phase 16 · 04（Primitive Model）、Phase 16 · 09（Parallel Swarm Networks）
**Time:** ~75 分钟

## Problem · 问题

多 agent 系统需要一个让 agent 共享事实的地方。一个字面意义上的选项是「把一切都塞进消息里传递」——但那是在靠额外的拷贝重新发明共享状态。另一个是「给每个人一个全局日志」——但全局日志会无限增长而且容易被投毒。第三个是「为每个 agent 投影出一个视图」——可扩展但对 schema 要求很重。

当其中一个 agent 产生幻觉、并把幻觉写进共享状态时，每个读到该状态的下游 agent 都会把幻觉当成事实。等到人类察觉时，推理链已经深入五步，而根因是最早写入的第三条消息。调试多 agent 系统的准确率衰减，比调试一次崩溃难得多。

这就是内存投毒（memory poisoning）。它是 MAST 分类法（Cemri et al., arXiv:2503.13657）中记录第二多的失效家族，而且是结构性的：任何没有来源记录（provenance）、没有不可写验证器（unwritable verifier）的共享内存设计，最终都会表现出这种失效。

> Multi-agent systems need a place for agents to share facts. A literal option is "pass everything in messages" — but that reinvents shared state with extra copying. Another is "give everyone a global log" — but global logs grow unbounded and poison easily. A third is "project a view per agent" — scalable but schema-heavy.
> When one of the agents hallucinates and writes the hallucination to shared state, every downstream agent that reads that state adopts the hallucination as fact. By the time the human notices, the reasoning chain is five steps deep and the root cause is the third message ever written. Debugging multi-agent accuracy decay is harder than debugging a crash.
> This is memory poisoning. It is the second-most-documented failure family in the MAST taxonomy (Cemri et al., arXiv:2503.13657) and it is structural: any shared-memory design without provenance and an unwritable verifier will exhibit it eventually.

## Concept · 概念

### The two main topologies · 两种主要拓扑

**完整消息池（full message pool）。** 每个 agent 读每一条消息。AutoGen GroupChat 和 MetaGPT 用的就是它。简单、透明、可检查，但扩展不过约 10 个 agent，因为每个 agent 的上下文都被其他 agent 的工作塞满。

```
agent-A ──write──▶ ┌────────────────┐ ◀──read── agent-D
                   │ message pool   │
agent-B ──write──▶ │                │ ◀──read── agent-E
                   │ (global log)   │
agent-C ──write──▶ └────────────────┘ ◀──read── agent-F
```

**带订阅的黑板（blackboard with subscription）。** agent 声明自己感兴趣的主题；底座只路由相关消息。CA-MCP（arXiv:2601.11595）和 Matrix 去中心化框架（arXiv:2511.21686）用的是这个。能扩展得更远，但需要预先设计 schema 才能让订阅有意义。

```
                   ┌─ topic: prices ──┐
agent-A ──pub────▶ │                  │ ──▶ agent-D (subscribed)
                   ├─ topic: orders ──┤
agent-B ──pub────▶ │                  │ ──▶ agent-E (subscribed)
                   ├─ topic: alerts ──┤
agent-C ──pub────▶ │                  │ ──▶ agent-F (subscribed)
                   └──────────────────┘
```

> **Full message pool.** Every agent reads every message. AutoGen GroupChat and MetaGPT use this. Simple, transparent, inspectable, but does not scale past ~10 agents because each agent's context fills with other agents' work.
> **Blackboard with subscription.** Agents declare interest in topics; the substrate routes only relevant messages. CA-MCP (arXiv:2601.11595) and the Matrix decentralized framework (arXiv:2511.21686) use this. Scales further, but requires upfront schema design to make subscriptions meaningful.

### When each wins · 各自的适用场景

- **完整消息池**在 agent 数量少（< 10）、角色异构、会话短程时占优。当所有人都看得到所有内容时，推理「谁说了什么」毫不费力。
- **黑板**在 agent 数量多、角色同构但实例众多（swarm）、会话长时间运行时占优。路由节省 token 成本，也避免上下文污染。

生产系统经常混用：顶部一个小型完整消息池（规划层），下面是黑板（执行层）。

> - **Full pool** wins when agents are few (< 10), heterogeneous, and the conversation is short-horizon. Reasoning about who said what is trivial when everyone sees everything.
> - **Blackboard** wins when agents are many, homogeneous in role but numerous in instance (swarms), and the conversation is long-running. Routing saves token cost and context pollution.
> Production systems often mix: a small full pool at the top (planning layer), blackboards below (worker layer).

### Memory poisoning, in one scenario · 一个场景看懂内存投毒

三个 agent 做一个研究任务。Agent A 是检索 agent。Agent B 是摘要器。Agent C 是分析员。

1. A 抓取一个页面，往共享状态写一条消息：「该研究报告了 42% 的准确率提升。」
2. 被抓取的页面实际写的是「4.2% 提升」。A 幻觉了一个小数点。
3. B 读取共享状态，写道：「报告了 42% 的大幅准确率提升（来源：A）。」
4. C 读取共享状态，写道：「建议采纳——42% 的提升是变革性的。」
5. 最终报告引用了一个从未存在过的 42%。

没有 agent 崩溃。没有测试失败。系统「正常运行」。幻觉穿过共享状态，从一个 agent 的上下文进入了每个下游 agent 的推理。

> Three agents work on a research task. Agent A is a retrieval agent. Agent B is a summarizer. Agent C is an analyst.
> 1. A fetches a page and writes a message to shared state: "The study reports a 42% accuracy improvement."
> 2. The fetched page actually said "4.2% improvement." A hallucinated a decimal.
> 3. B, reading shared state, writes: "Large 42% accuracy gain reported (source: A)."
> 4. C, reading shared state, writes: "Recommend adoption — 42% lift is transformative."
> 5. The final report cites a 42% number that never existed.
> No agent crashed. No test failed. The system "worked." The hallucination crossed from one agent's context into every downstream agent's reasoning via shared state.

### Why this is structural · 为什么这是结构性问题

没有共享状态时，agent A 的幻觉只留在 A 的上下文里。下游 agent 会重新抓取或重新推导，可能发现错误。有了朴素的共享状态，A 的上下文变成了所有人的上下文，幻觉被「洗白」成事实。

问题不在共享状态本身——而在于共享状态**没有来源记录、也没有独立验证器**。三种缓解手段针对的正是这一点：

1. **每次写入都记录来源（provenance）。** 共享状态里的每一条都记录谁写的、什么时候写的、在什么提示词下写的，以及（如果适用）agent 引用了什么来源。下游 agent 读取时按来源决定怀疑程度。
2. **给写入做版本化；把它当作只追加（append-only）。** 更正是一条取代旧条目的新条目，而不是原地修改。审计轨迹得以保留。
3. **保留至少一个无法写入共享状态的 agent。** 一个只读的验证器 agent 抽样检查条目、重新抓取来源、标记不一致。因为它不能写入消息池，所以它不会被消息池投毒。

> Without shared state, agent A's hallucination stays in A's context. Downstream agents would re-fetch or re-derive and might catch the error. With naive shared state, A's context becomes everyone's context, and the hallucination is laundered into fact.
> The problem is not shared state per se — it is shared state **without provenance and without an independent verifier**. Three mitigations address this:
> 1. **Attribute provenance on every write.** Every entry in shared state records who wrote it, when, under what prompt, and (if applicable) what source the agent cited. Downstream agents read with skepticism keyed to provenance.
> 2. **Version writes; treat them as append-only.** A correction is a new entry that supersedes the old, not an in-place update. The audit trail is preserved.
> 3. **Keep at least one agent that cannot write to shared state.** A read-only verifier agent samples entries, re-fetches sources, and flags inconsistencies. Because it cannot write to the pool, it cannot be poisoned by the pool.

### Blackboard precedent (Hayes-Roth, 1985) · 黑板的先例（Hayes-Roth，1985）

黑板模式比 LLM agent 早了四十年。Hayes-Roth（1985，"A Blackboard Architecture for Control"）描述了专门的「知识源」（Knowledge Sources）：它们观察一块全局黑板，贡献部分解，并触发其他知识源。2026 年的黑板（CA-MCP、Matrix）是同一个模式，只不过知识源换成了 LLM agent，部分解换成了 JSON 数据块。老文献已经记录了关于写竞争、机会主义控制与一致性的解决方案，而现代系统正在重新发现它们。

> The blackboard pattern predates LLM agents by four decades. Hayes-Roth (1985, "A Blackboard Architecture for Control") described specialist Knowledge Sources that observe a global blackboard, contribute partial solutions, and trigger other sources. The 2026 blackboard (CA-MCP, Matrix) is the same pattern with LLM agents as Knowledge Sources and JSON blobs as partial solutions. The old literature has documented solutions to write contention, opportunistic control, and consistency that modern systems rediscover.

### Projection vs full view · 投影 vs 完整视图

纯黑板给每个订阅者同样的投影（按主题划定范围）。更激进的设计是**按 agent 投影（per-agent projection）**：每个 agent 拿到按其角色定制的视图。LangGraph 的 state reducer 是 2026 年的标杆实现——reducer 函数把全局状态折叠成角色专属的切片。

按 agent 投影扩展性更好，但需要一个 schema。没有它，你就要在每个 agent 的提示词里重建临时拼凑的投影逻辑。

> A pure blackboard gives every subscriber the same projection (topic-scoped). A more aggressive design is **per-agent projection**: each agent gets a view customized to its role. LangGraph's state reducers are the canonical 2026 implementation — the reducer function folds global state into a role-specific slice.
> Per-agent projection scales further but needs a schema. Without one, you rebuild ad-hoc projection in every agent's prompt.

### Write-contention patterns · 写竞争的处理模式

多个 agent 同时写入是一个并发问题，不只是 LLM 问题。三种模式可行：

- **顺序写入者（单一生产者）。** 所有写入都经过一个负责串行化的协调 agent。简单，但是瓶颈。
- **带版本化的乐观并发。** 每条有一个版本号；写入者遇到版本不匹配就失败并重试。经典的数据库技术。
- **主题分区。** 不同 agent 拥有不同的主题。没有跨主题竞争。需要设计好分区边界。

大多数 2026 年的框架默认用顺序写入者，因为 LLM 调用足够慢，竞争很罕见，瓶颈也就不痛。

> Multiple agents writing simultaneously is a concurrency problem, not just an LLM problem. Three patterns work:
> - **Sequential writer (single producer).** All writes go through one coordinator agent that serializes. Simple, but a bottleneck.
> - **Optimistic concurrency with versioning.** Each entry has a version; writers fail on version mismatch and retry. Classic database technique.
> - **Topic partitioning.** Different agents own different topics. No cross-topic contention. Requires designed partition boundaries.
> Most 2026 frameworks default to sequential writer because LLM calls are slow enough that contention is rare and the bottleneck does not hurt.

### The unwritable verifier · 不可写的验证器

最有分量的缓解手段是只读验证器。实现规则：

- 验证器与团队共享状态（读黑板或消息池）。
- 验证器没有共享状态的写句柄——只有一条独立的验证通道。
- 验证器独立抓取写入中引用的来源。对不一致之处打标记。
- 验证器自己的输出路由给人类或一个独立的决策 agent，绝不回灌进消息池。

没有这道隔离，验证器的输出就成了池里的新条目，这意味着被投毒的池会毒化验证器，进而毒化它做的所有验证。

> The most load-bearing mitigation is the read-only verifier. Implementation rules:
> - Verifier shares state with the team (reads the blackboard or pool).
> - Verifier has no write handle to shared state — only to a separate verification channel.
> - Verifier independently fetches sources cited in writes. Flags disagreement.
> - Verifier's own outputs are routed to a human or a separate decision agent, never fed back into the pool.
> Without this separation, the verifier's outputs become new entries in the pool, which means a poisoned pool poisons the verifier, which poisons its verifications.

```figure
swarm-blackboard
```

## Build It · 动手造

`code/main.py` 用标准库 Python 实现两种拓扑，外加一个玩具级投毒攻击和三种缓解手段。

- `MessagePool` —— 线程安全的只追加日志，支持完整读出。
- `Blackboard` —— 以主题为键的发布/订阅，支持按 agent 订阅。
- `ProvenanceEntry` —— 每次写入记录 (writer, timestamp, prompt_hash, source_uri)。
- `PoisoningScenario` —— 运行一个三 agent 研究任务，其中 agent A 幻觉出一个 decimal。打印最终报告。
- `Verifier` —— 一个只读 agent，重新抓取来源并标记不一致。在验证器在场的情况下运行同一场景。

运行：

```
python3 code/main.py
```

预期输出：
- 第 1 次（无验证器）：幻觉出的 42% 传播到最终报告。
- 第 2 次（有验证器）：验证器标记不一致，消息池被标记为 "flagged"，最终报告包含一份撤回声明。

> `code/main.py` implements both topologies in stdlib Python plus a toy poisoning attack and the three mitigations.
> - `MessagePool` — thread-safe append-only log with full read-out.
> - `Blackboard` — topic-keyed pub/sub with per-agent subscriptions.
> - `ProvenanceEntry` — every write records (writer, timestamp, prompt_hash, source_uri).
> - `PoisoningScenario` — runs a three-agent research task where agent A hallucinates a decimal. Prints final report.
> - `Verifier` — a read-only agent that re-fetches sources and flags inconsistencies. Runs the same scenario with the verifier present.
> Expected output:
> - Run 1 (no verifier): the hallucinated 42% propagates to the final report.
> - Run 2 (with verifier): the verifier flags the inconsistency, the pool is labeled "flagged", the final report includes a retraction.

## Use It · 实战用法

`outputs/skill-memory-auditor.md` 是一个技能，用于审计任何多 agent 系统的共享内存设计：来源记录、版本化、验证器隔离。在新的多 agent 架构上线前对它跑一遍。

> `outputs/skill-memory-auditor.md` is a skill that audits any multi-agent system's shared-memory design for provenance, versioning, and verifier separation. Run it on new multi-agent architectures before production.

## Ship It · 交付

对任何共享内存设计：

- 每次写入都记录来源：`(writer, timestamp, prompt_hash, tool_calls_cited, source_uri)`。
- 让日志只追加。更正是引用了被取代条目的新条目。
- 部署至少一个拥有独立来源访问能力的只读验证器 agent。
- 把验证器的输出路由到独立通道，而不是回灌共享池。
- 记录「取代型写入」的占比——这个比率上升是幻觉模式的早期证据。

> For any shared-memory design:
> - Record provenance on every write: `(writer, timestamp, prompt_hash, tool_calls_cited, source_uri)`.
> - Make the log append-only. Corrections are new entries that reference the superseded one.
> - Deploy at least one read-only verifier agent with independent source access.
> - Route verifier output to a separate channel, not back into the shared pool.
> - Log the ratio of writes that are supersessions — a rising ratio is early evidence of hallucination patterns.

## Exercises · 练习

1. 运行 `code/main.py`。确认第 1 次运行传播了幻觉，第 2 次运行抓住了它。
2. 加第二个幻觉：agent B 编造一个数据集大小。验证器应该在不针对两者做任何手工调参的情况下把两个都抓住。
3. 把完整消息池换成带主题分区（`prices`、`summaries`、`analyses`）的黑板。主题分区让哪些投毒场景更难得逞，又对哪些无济于事？
4. 阅读 Hayes-Roth（1985，"A Blackboard Architecture for Control"）。从论文中找出两种本课没有讨论、2026 年的系统会受益的控制模式。
5. 阅读 CA-MCP（arXiv:2601.11595）。把它的 Shared Context Store 映射到 `code/main.py` 里的 MessagePool 或 Blackboard 类。CA-MCP 在其之上增加了哪些原语？

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Message pool | "共享聊天历史" | 所有 agent 都读的只追加日志。完全透明，扩展性差。 |
| Blackboard | "共享工作台" | 以主题为键的发布/订阅。agent 订阅相关主题。扩展得更远。 |
| Provenance | "谁写了什么" | 每次写入的元数据：写入者、时间戳、提示词、来源。 |
| Memory poisoning | "幻觉扩散" | 一个 agent 的错误进入共享状态，下游 agent 把它当成事实。 |
| Append-only | "不原地更新" | 更正是取代旧条目的新条目。保留审计轨迹。 |
| Unwritable verifier | "独立审计员" | 只读 agent，重新抓取来源并标记不一致。 |
| Projection | "划定范围的视图" | 从全局状态计算出的按 agent 视图。LangGraph reducer 是标杆案例。 |
| Knowledge Source | "专家 agent" | Hayes-Roth 1985 年对黑板参与者的称呼。 |

## Further Reading · 延伸阅读

- [Cemri et al. — Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) —— MAST 分类法；内存投毒是协作失效的一个子家族
- [CA-MCP — Context-Aware Multi-Server MCP](https://arxiv.org/abs/2601.11595) —— 面向协作式 MCP 服务器的 Shared Context Store
- [Matrix — decentralized multi-agent framework](https://arxiv.org/abs/2511.21686) —— 基于消息队列、无中央编排器的黑板
- [LangGraph state and reducers](https://docs.langchain.com/oss/python/langgraph/workflows-agents) —— 生产中的按 agent 投影模式
- [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) —— 一次生产部署中的来源记录与验证笔记
