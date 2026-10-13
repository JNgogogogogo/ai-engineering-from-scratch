# Handoffs and Routines — Stateless Orchestration · 交接与例程——无状态编排

> OpenAI 的 Swarm（2024 年 10 月）把多智能体编排提炼成两个原语：**例程（routine）**（作为系统提示词的指令 + 工具）和**交接（handoff）**（一个返回另一个 Agent 的工具）。没有状态机，没有分支 DSL——LLM 通过调用正确的交接工具来路由。OpenAI Agents SDK（2025 年 3 月）是生产级继任者。Swarm 本身仍然是最干净的概念参考——它的全部源码只有几百行。这个模式之所以病毒式流行，是因为它的 API 表面大致就是「智能体 = 提示词 + 工具；交接 = 返回智能体的函数」。局限：无状态，所以记忆是调用方的问题。

> OpenAI's Swarm (October 2024) distilled multi-agent orchestration to two primitives: **routines** (instructions + tools as a system prompt) and **handoffs** (a tool that returns another Agent). No state machine, no branching DSL — the LLM routes by calling the right handoff tool. The OpenAI Agents SDK (March 2025) is the production successor. Swarm itself remains the cleanest conceptual reference — its entire source fits in a few hundred lines. The pattern is viral because the API surface is roughly "agent = prompt + tools; handoff = function returning agent." Limitation: stateless, so memory is the caller's problem.

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 16 · 04 (Primitive Model)
**Time:** ~60 minutes

---

## Problem · 问题

每个多智能体框架都要你学它的 DSL：LangGraph 的节点和边，CrewAI 的 crew 和 task，AutoGen 的 GroupChat 和管理器。这些 DSL 是真实的抽象，但它们让这件事显得比实际更重。

Swarm 朝反方向用力：用模型本来就有的工具调用能力。交接变成工具调用。编排者就是当前持有会话的那个智能体。状态机隐含在智能体的系统提示词里。

> Every multi-agent framework wants you to learn its DSL: LangGraph nodes and edges, CrewAI crews and tasks, AutoGen GroupChat and managers. The DSLs are real abstractions, but they make the thing feel heavier than it needs to be. ... Swarm pushes in the opposite direction: use the tool-calling capability the model already has. Handoffs become tool calls. The orchestrator is whichever agent currently holds the conversation. The state machine is implicit in the agents' system prompts.

---

## Concept · 概念

### Two primitives · 两个原语

**例程（Routine）。** 定义一个智能体的角色和可用工具的系统提示词。把它想成一组限定范围的指令：「你是分诊智能体；如果用户问退款，就交接给退款智能体。」

**交接（Handoff）。** 智能体可以调用的一个工具，返回一个新的 Agent 对象。Swarm 运行时检测到 Agent 返回值，就在下一轮切换活动智能体。

这就是全部的抽象。

```
def transfer_to_refunds():
    return refund_agent  # Swarm sees Agent return → switch active agent

triage_agent = Agent(
    name="triage",
    instructions="Route the user to the right specialist.",
    functions=[transfer_to_refunds, transfer_to_sales, transfer_to_support],
)
```

分诊智能体的系统提示词让它根据用户消息选择正确的交接。LLM 的工具调用完成路由。

> **Routine.** A system prompt that defines an agent's role and available tools. Think of it like a scoped set of instructions: "you are a triage agent; if the user asks about refunds, hand off to the refund agent." ... **Handoff.** A tool the agent can call that returns a new Agent object. The Swarm runtime detects the Agent return value and switches the active agent for the next turn. ... That is the entire abstraction. ... The triage agent's system prompt makes it choose the right handoff based on the user message. The LLM's tool-calling does the routing.

---

### Why it is viral · 它为什么流行

- **API 小。** 只有两个要学的概念。
- **用模型本来就会的事。** 工具调用在各个提供方都已是生产级。
- **没有状态机负担。** 你不用描述图；智能体的提示词描述它们把活交给谁。

> **Small API.** Two concepts to learn. ... **Uses what the model already does.** Tool calling is already production-grade across providers. ... **No state-machine burden.** You do not describe the graph; the agents' prompts describe who they hand off to.

---

### The stateless trade · 无状态的代价

Swarm 在两次运行之间显式无状态。框架在一次运行期间保留消息历史，但不持久化任何东西。记忆、连续性、长时任务——全是调用方的问题。

在生产里（OpenAI Agents SDK，2025 年 3 月）这正是主要改动之一：SDK 加入了内建的会话管理、护栏（guardrails）和追踪，同时保留交接原语。

> Swarm is explicitly stateless between runs. The framework keeps a message history during a run, but it does not persist anything. Memory, continuity, long-running tasks — all the caller's problem. ... In production (OpenAI Agents SDK, March 2025) this was one of the main things that changed: the SDK adds built-in session management, guardrails, and tracing while keeping the handoff primitive.

---

### When Swarm/handoffs fit · Swarm/交接什么时候合适

- **分诊模式。** 一线智能体把用户路由给专家。
- **按技能交接。** 「任务需要代码就叫程序员；需要研究就叫研究员。」
- **短小有界的对话。** 客服、FAQ 转工单、简单工作流。

> **Triage patterns.** Front-line agent routes user to a specialist. ... **Skill-based handoffs.** "If the task needs code, call the coder; if it needs research, call the researcher." ... **Short, bounded conversations.** Customer support, FAQ-to-ticket, simple workflows.

---

### When Swarm struggles · Swarm 什么时候吃力

- **带共享记忆的长会话。** 交接把会话状态重置为新智能体的提示词加历史。没有调用方管理的记忆，就没有跨智能体的持久状态。
- **并行执行。** 交接是一次一个——活动智能体切换。并行需要调用方自己编排多个 Swarm 运行。
- **审计与重放。** 无状态运行很难精确重放；LLM 的交接选择不是确定性的。

> **Long sessions with shared memory.** Handoffs reset the conversation state to the new agent's prompt plus history. No persistent state across agents without caller-managed memory. ... **Parallel execution.** Handoff is one-at-a-time — the active agent switches. Parallelism requires the caller orchestrating multiple Swarm runs. ... **Audit and replay.** Stateless runs are hard to replay exactly; the LLM's handoff choice is not deterministic.

---

### OpenAI Agents SDK (March 2025) · OpenAI Agents SDK（2025 年 3 月）

生产级继任者加了：

- **会话状态。** 跨运行持久的线程。
- **护栏。** 输入/输出校验钩子。
- **追踪。** 每次工具调用和交接都被记录。
- **交接过滤器。** 控制交接时传递什么上下文。

交接原语活了下来；生产级的人体工学围绕它加上。

> The production successor adds: **Session state.** Persistent thread across runs. ... **Guardrails.** Input/output validation hooks. ... **Tracing.** Every tool call and handoff is logged. ... **Handoff filters.** Control what context transfers on handoff. ... The handoff primitive survives; production ergonomics get added around it.

---

### Swarm vs GroupChat · Swarm vs GroupChat

都用 LLM 驱动的路由，但在 **谁来选下一个** 上不同：

- GroupChat：一个选择器（函数或 LLM）从外部挑选下一个发言者。
- Swarm：当前智能体通过调用交接工具挑选自己的继任者。

Swarm 是「智能体决定下一步」；GroupChat 是「管理器决定下一步」。Swarm 的决策活在活动智能体的工具调用里；GroupChat 的活在 `GroupChatManager` 里。

```figure
sw-handoff-routing
```

> Both use LLM-driven routing, but they differ on **who picks next**: GroupChat — a selector (function or LLM) picks the next speaker from outside. Swarm — the current agent picks its successor by calling a handoff tool. ... Swarm is "agent decides what's next"; GroupChat is "manager decides what's next." Swarm's decision lives in the active agent's tool call; GroupChat's lives in the `GroupChatManager`.

---

## Build It · 动手造

`code/main.py` 从零实现 Swarm：一个 Agent dataclass、一个交接机制（工具返回 Agent），以及一个检测智能体切换的运行循环。

演示：一个分诊智能体路由到退款、销售或支持专家。每个专家有自己的工具。运行循环打印每一次交接。

Run:

```
python3 code/main.py
```

> `code/main.py` implements Swarm from scratch: an Agent dataclass, a handoff mechanism (tool returns Agent), and a run loop that detects agent switches. ... Demo: a triage agent routes to refund, sales, or support specialists. Each specialist has its own tools. The run loop prints each handoff.

---

## Use It · 实战用法

`outputs/skill-handoff-designer.md` 为给定任务设计一份交接拓扑：存在哪些智能体、它们能调用哪些交接、传递什么上下文。

> `outputs/skill-handoff-designer.md` designs a handoff topology for a given task: which agents exist, which handoffs they can call, what context transfers.

---

## Ship It · 交付

检查清单：

- **交接日志。** 每次交接写一条 trace 事件：来自哪个智能体、到哪个智能体、上下文快照。
- **上下文传递规则。** 决定交接时什么跟着走：完整历史（贵）、最近 N 条消息，或一份摘要。
- **交接护栏。** 交接给拥有不同工具权限的专家必须做认证——否则提示注入可以强制不想要的交接。
- **循环检测。** 两个智能体来回互相交接是常见失败；用一个简单的 last-K 环形检查来检测。
- **回退智能体。** 如果交接目标不存在，回退到一个安全的默认。

> Checklist: ... **Handoff logging.** Every handoff writes a trace event with from-agent, to-agent, context snapshot. ... **Context transfer rules.** Decide what moves on handoff: full history (expensive), last N messages, or a summary. ... **Guardrail on handoff.** A handoff to a specialist with different tool permissions must be authenticated — otherwise prompt injection can force unwanted handoffs. ... **Loop detection.** Two agents handing back and forth is a common failure; detect with a simple last-K ring check. ... **Fallback agent.** If a handoff target does not exist, fall back to a safe default.

---

## Exercises · 练习

1. 跑 `code/main.py`，分诊到退款智能体。确认第二轮的活动智能体是退款。
2. 加一条循环检测规则：如果同样两个智能体连续交接 3 次，强制退出。设计好回退方案。
3. 读 OpenAI Agents SDK 关于交接过滤器的文档。实现一个「交接时摘要」版本：outgoing 智能体在 incoming 智能体接手之前，把上下文压缩成一份要点摘要。
4. 比较 Swarm 交接与 GroupChatManager 选择器。哪种模式让提示注入更糟，为什么？
5. 读 Swarm cookbook（https://developers.openai.com/cookbook/examples/orchestrating_agents）。指出 Swarm 做出的一个明确设计决策，以及 OpenAI Agents SDK 改掉了它还是保留了它。

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Routine | 「智能体提示词」 | 系统提示词 + 工具列表。定义角色和可用交接。 |
| Handoff | 「转给另一个智能体」 | 活动智能体可调用的工具，返回一个新的 Agent。运行时切换活动智能体。 |
| Stateless | 「运行之间无记忆」 | Swarm 不持久化任何东西；记忆是调用方的责任。 |
| Active agent | 「现在谁在说话」 | 当前持有会话的智能体。交接会改变它。 |
| Context transfer | 「交接时什么跟着走」 | 规定 incoming 智能体看到什么历史的策略：全部、最近 N 条或摘要。 |
| Handoff loop | 「智能体打乒乓球」 | 两个智能体不断互相交接的失败模式。 |
| OpenAI Agents SDK | 「生产级 Swarm」 | 2025 年 3 月的继任者；在交接原语之上加会话、护栏、追踪。 |
| Handoff filter | 「交接处的闸门」 | SDK 特性：在交接边界检查和修改上下文。 |

---

## Further Reading · 延伸阅读

- [OpenAI cookbook — Orchestrating Agents: Routines and Handoffs](https://developers.openai.com/cookbook/examples/orchestrating_agents) —— 参考表述
- [OpenAI Swarm repo](https://github.com/openai/swarm) —— 原始实现，保留为概念参考
- [OpenAI Agents SDK docs](https://openai.github.io/openai-agents-python/) —— 带会话和追踪的生产级继任者
- [Anthropic handoff-in-Claude notes](https://docs.anthropic.com/en/docs/claude-code) —— Claude Code 子智能体如何通过 `Task` 使用类似交接的模式
