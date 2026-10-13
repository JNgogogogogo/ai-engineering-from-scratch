# Group Chat and Speaker Selection · 群聊与发言者选择

> 共享会话式编排把 N 个智能体放进同一个会话；由一个选择器函数（LLM、轮转或自定义）决定下一个发言者。这是涌现式多智能体会话的原型——智能体并不知道自己在静态图里的角色，它们只是对共享消息池做出反应。AutoGen GroupChat 和 AG2 GroupChat 是参考实现：AutoGen v0.2 的 GroupChat 语义在 AG2 fork 中得到保留；AutoGen v0.4 把它重写为事件驱动的 actor 模型。微软于 2026 年 2 月把 AutoGen 转入维护模式，并与 Semantic Kernel 合并进 Microsoft Agent Framework（2026 年 2 月 RC）。GroupChat 原语在 AG2 和 Microsoft Agent Framework 里都活着——学一次，到处可用。

> Shared-conversation orchestration puts N agents in one conversation; a selector function (LLM, round-robin, or custom) picks who speaks next. This is the archetype of emergent multi-agent conversation — agents do not know their role in a static graph, they just react to the shared pool. AutoGen GroupChat and AG2 GroupChat are the reference implementations: AutoGen v0.2's GroupChat semantics were preserved in the AG2 fork; AutoGen v0.4 rewrote it as an event-driven actor model. Microsoft put AutoGen into maintenance mode in February 2026 and merged it with Semantic Kernel into Microsoft Agent Framework (RC February 2026). The GroupChat primitive survives in both AG2 and Microsoft Agent Framework — learn it once, use it everywhere.

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 16 · 04 (Primitive Model)
**Time:** ~60 minutes

---

## Problem · 问题

静态图（LangGraph）在工作流已知时很好用。真实对话不是静态的：有时是程序员问评审，有时是研究员，有时是作者。把每一种可能的交接都硬编码会产生边爆炸。你想要的是 *智能体对共享池做出反应*，由某个函数决定谁下一个发言。

这正是 AutoGen GroupChat 做的事。

> Static graphs (LangGraph) are great when the workflow is known. Real conversations are not static: sometimes the coder asks the reviewer, sometimes the researcher, sometimes the writer. Hardcoding every possible handoff produces an edge explosion. You want *agents reacting to a shared pool*, with some function deciding who talks next. ... That is exactly what AutoGen GroupChat does.

---

## Concept · 概念

### The shape · 形态

```
              ┌─── shared pool ────┐
              │   m1  m2  m3  ...  │
              └─────────┬──────────┘
                        │ (everyone reads all)
      ┌───────┬─────────┼─────────┬───────┐
      ▼       ▼         ▼         ▼       ▼
    Agent A  Agent B  Agent C  Agent D  Selector
                                           │
                                           ▼
                                  "next speaker = C"
```

每个智能体看得到每一条消息。每一轮都会调用一个选择器函数，由它决定下一个发言者。

> Every agent sees every message. A selector function is invoked at each turn to pick who speaks next.

---

### The three selector flavors · 选择器的三种风味

**轮转（round-robin）。** 固定循环。确定性。随 N 线性扩展但无视上下文——话题是法律评审时程序员也会拿到发言权。

**LLM 选择。** 调用一次 LLM，读取最近的池并返回最佳的下一个发言者。上下文感知但慢：每一轮多一次 LLM 调用。这是 AutoGen 的默认。

**自定义。** 一个想写什么逻辑就写什么逻辑的 Python 函数。典型形态：LLM 选择加回退规则（例如「编码者发言之后，总是把发言权给验证者」）。

> **Round-robin.** Fixed cycle. Deterministic. Scales linearly in N but ignores context — a coder gets the turn even when the topic is legal review. ... **LLM-selected.** A call to an LLM that reads the recent pool and returns the best next speaker. Context-aware but slow: every turn adds an LLM call. AutoGen's default. ... **Custom.** A Python function with whatever logic you want. Typical: LLM-selected with fallback rules (e.g., "always give the verifier the turn after the coder").

---

### The ConversableAgent API · ConversableAgent API

```
agent = ConversableAgent(
    name="coder",
    system_message="You write Python.",
    llm_config={...},
)
chat = GroupChat(agents=[coder, reviewer, tester], messages=[])
manager = GroupChatManager(groupchat=chat, llm_config={...})
```

`GroupChatManager` 持有选择器。当一个智能体完成一轮发言，管理器调用选择器，选择器返回下一个智能体。循环持续到终止条件满足为止。

> `GroupChatManager` holds the selector. When an agent completes a turn, the manager calls the selector, which returns the next agent. Loop continues until a termination condition.

---

### Termination · 终止

三种常见模式：

- **最大轮数。** 对总轮数的硬上限。
- **「TERMINATE」标记。** 智能体可以发出一个哨兵消息；管理器一看到就停止。
- **目标达成检查。** 一个轻量验证器每轮运行，完成后终止群聊。

> Three common patterns: **Max rounds.** Hard cap on total turns. ... **"TERMINATE" token.** Agents can emit a sentinel message; the manager stops when one appears. ... **Goal-reached check.** A lightweight verifier runs each turn and stops the chat when done.

---

### Lineage: forks and mergers · 谱系：分叉与合并

2025 年初，微软开始围绕事件驱动 actor 模型对 AutoGen（v0.4）进行大重写。社区把 AutoGen v0.2 的 GroupChat 语义 fork 成 AG2，保住了早期采用者已经集成的 API。

2026 年 2 月，微软宣布 AutoGen 将进入维护模式，事件驱动 actor 模型并入 **Microsoft Agent Framework**（2026 年 2 月 RC，已与 Semantic Kernel 合并）。GroupChat 概念在两条传承线上都活着；实现细节不同。对 v0.2 兼容代码来说，AG2 是首选上游。

> In early 2025, Microsoft began a major rewrite of AutoGen (v0.4) around an event-driven actor model. The community forked AutoGen v0.2's GroupChat semantics as AG2, preserving the API that early adopters had integrated. ... In February 2026, Microsoft announced AutoGen would go to maintenance mode, with the event-driven actor model merging into **Microsoft Agent Framework** (RC February 2026, now merged with Semantic Kernel). The GroupChat concept survives in both tracks; the implementation details differ. AG2 is the preferred upstream for v0.2-compatible code.

---

### When GroupChat fits · GroupChat 什么时候合适

- **涌现式对话。** 你不想预先接好每一种「下一个发言者」。
- **角色混合任务。** 程序员问研究员，研究员问档案员，档案员又问回程序员。流程不是 DAG。
- **探索式解题。** 想成「头脑风暴会议」，不要想成「流水线」。

> **Emergent conversations.** You do not want to pre-wire every possible next-speaker. ... **Role-mixing tasks.** Coder asks researcher, researcher asks archivist, archivist asks coder back. Flow is not a DAG. ... **Exploratory problem-solving.** Think "brainstorm meeting," not "assembly line."

---

### When it fails · 什么时候会失败

- **严格确定性。** LLM 选择器可能不稳定。同样的提示词，不同的运行，选出不同的下一个发言者。
- **谄媚级联。** 智能体顺从说得最自信的人。用提示词明确反制。
- **上下文膨胀。** 每个智能体读每条消息；10 轮之后上下文巨大。用投影（projection，第 15 课）来限定视野。
- **热点发言者。** 某个智能体因为选择器偏爱它的专长而主导对话。把发言者均衡作为选择器的一个特性引入。

> **Strict determinism.** The LLM selector can be inconsistent. Same prompt, different runs, different next speakers. ... **Sycophancy cascades.** Agents defer to whoever spoke most confidently. Counter-prompt explicitly. ... **Context bloat.** Every agent reads every message; after 10 turns the context is huge. Use projections (Lesson 15) to scope views. ... **Hot speakers.** One agent dominates the conversation because the selector favors its specialties. Introduce speaker balance as a selector feature.

---

### Group chat vs supervisor · 群聊 vs 监督者

同一批原语，不同的默认值：

- 监督者：一个智能体规划，其他智能体执行。选择器是「问规划者该做什么」。
- 群聊：所有智能体平权；选择器是共享池上的一个函数。

两者都用第 04 课的四个原语。群聊默认 LLM 选择的编排和全池共享状态。

```figure
swarm-speaker
```

> Same primitives, different defaults: Supervisor — one agent plans and others execute. Selector is "ask the planner what to do." Group chat — all agents are peers; selector is a function over the shared pool. ... Both use the four primitives from Lesson 04. Group chat defaults to LLM-selected orchestration and full-pool shared state.

---

## Build It · 动手造

`code/main.py` 用标准库从零实现一个 GroupChat。包含三个智能体（coder、reviewer、manager）、轮转和 LLM 选择两种变体，以及基于 `TERMINATE` 标记的终止。

演示打印两个变体的会话记录和选择器的决策轨迹。

Run:

```
python3 code/main.py
```

> `code/main.py` implements a GroupChat from scratch in stdlib. Three agents (coder, reviewer, manager), round-robin and LLM-selected variants, and a termination on a `TERMINATE` token. ... The demo prints the conversation transcript plus the selector's decision trace for both variants.

---

## Use It · 实战用法

`outputs/skill-groupchat-selector.md` 为给定任务配置一个 GroupChat 选择器——轮转 vs LLM 选择 vs 自定义，以及选择器该用哪些输入（最近消息、智能体专长、轮次计数）。

> `outputs/skill-groupchat-selector.md` configures a GroupChat selector for a given task — round-robin vs LLM-selected vs custom, and what selector inputs (recent messages, agent specialties, turn counts) to use.

---

## Ship It · 交付

检查清单：

- **最大轮数上限。** 永远要有。典型任务 10-20。
- **发言者均衡指标。** 跟踪每个智能体的轮数；失衡超过阈值就告警。
- **终止标记。** `TERMINATE` 或一个专门的验证者智能体。
- **投影或限定记忆。** 大约 10 条消息之后，考虑只给每个智能体一个限定视野，防止上下文膨胀。
- **选择器日志。** 对 LLM 选择的变体，同时记录选择器的输入和它的选择。否则没法调试。

> Checklist: ... **Max rounds cap.** Always. 10-20 for typical tasks. ... **Speaker-balance metric.** Track turns per agent; alert when imbalance exceeds a threshold. ... **Termination token.** `TERMINATE` or a dedicated verifier agent. ... **Projection or scoped memory.** After ~10 messages, consider giving each agent only a scoped view to prevent context bloat. ... **Selector logging.** For LLM-selected variants, log both the selector's input and its choice. Otherwise debugging is impossible.

---

## Exercises · 练习

1. 跑 `code/main.py`。比较轮转与 LLM 选择下的对话。每种变体下哪个智能体占主导？
2. 在选择器里加一条「每智能体最大发言数」规则。它如何影响会话记录？
3. 实现目标达成终止：当 reviewer 返回「approved」就停止。它在轮数上限之前触发的频率如何？
4. 读 AutoGen 稳定版文档的 GroupChat 部分（https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/group-chat.html）。指出 `GroupChatManager` 使用的默认选择器。
5. 读 AG2 仓库（https://github.com/ag2ai/ag2），比较它的 v0.2 GroupChat 与 v0.4 事件驱动版本。v0.4 增加了什么具体属性（吞吐量、容错、可组合性）？

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| GroupChat | 「一个聊天室里的智能体」 | 共享消息池 + 选择器函数。AutoGen / AG2 的原语。 |
| Speaker selection | 「谁下一个发言」 | 挑选下一个智能体的函数。轮转、LLM 选择或自定义。 |
| GroupChatManager | 「会议主持人」 | 持有选择器并循环推进轮次的 AutoGen 组件。 |
| ConversableAgent | 「基类智能体」 | AutoGen 基类；能收发消息的智能体。 |
| Termination token | 「『停』这个词」 | 结束群聊的哨兵字符串（通常是 `TERMINATE`）。 |
| Hot speaker | 「一个智能体霸场」 | 选择器一直选同一个智能体的失败模式。 |
| Context bloat | 「池无限增长」 | 每个智能体读每条历史消息；上下文随轮数增长。 |
| Projection | 「限定视野」 | 共享池的角色专属视图，用来防止上下文膨胀。 |

---

## Further Reading · 延伸阅读

- [AutoGen group chat docs](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/group-chat.html) —— 参考实现
- [AG2 repo](https://github.com/ag2ai/ag2) —— 社区延续的 AutoGen v0.2
- [Microsoft Agent Framework docs](https://learn.microsoft.com/en-us/agent-framework/) —— 合并后的继任者，2026 年 2 月 RC
- [AutoGen v0.4 release notes](https://microsoft.github.io/autogen/stable/) —— 事件驱动 actor 模型重写细节
