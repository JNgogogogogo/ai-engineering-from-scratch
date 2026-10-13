# Orchestration Patterns: Supervisor, Swarm, Hierarchical · 编排模式：Supervisor、Swarm、Hierarchical

四种编排模式（orchestration patterns）在 2026 年的框架里反复出现：supervisor-worker、swarm / 对等网络（peer-to-peer）、层级制（hierarchical）、辩论（debate）。Anthropic 的建议是：「关键是为你的需求构建合适的系统。」从简单开始；只有当单个智能体加五种工作流模式不够用时，才引入拓扑。

> Four orchestration patterns recur across 2026 frameworks: supervisor-worker, swarm / peer-to-peer, hierarchical, debate. Anthropic's guidance: "It's about building the right system for your needs." Start simple; add topology only when a single agent plus five workflow patterns is insufficient.

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 12 (Workflow Patterns), Phase 14 · 25 (Multi-Agent Debate)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 说出四种反复出现的编排模式，以及各自适用的场合。
- 描述 2026 年 LangChain 的建议：用直接的 tool call 做监督（supervision），而不是 supervisor 库。
- 解释 Anthropic 的「构建合适的系统」原则，以及它如何约束拓扑选择。
- 在同一个脚本化 LLM 上用 stdlib 实现全部四种模式。

> Name the four recurring orchestration patterns and when each fits.
> Describe the 2026 LangChain recommendation: tool-call-based supervision vs supervisor libraries.
> Explain Anthropic's "build the right system" rule and how it gates topology choice.
> Implement all four in stdlib against a common scripted LLM.

## The Problem · 问题在哪

团队在还没需要的时候就扑向「多智能体」。四种模式在各个框架里反复出现；一旦你能叫出它们的名字，你就能选对的那一个——或者干脆跳过拓扑。

> Teams reach for "multi-agent" before they need it. Four patterns recur across frameworks; once you can name them, you can pick the right one — or skip topology entirely.

## The Concept · 概念

### Supervisor-worker · 监督者-工作者

- 一个中央路由 LLM 向专家智能体（specialist）分派任务。
- 它决定：回到自己继续循环、交接给专家、还是终止。
- 专家之间互不通信；所有路由都经过 supervisor。

框架：LangGraph `create_supervisor`、Anthropic orchestrator-workers、CrewAI Hierarchical Process。

**2026 年 LangChain 的建议：** 通过直接的 tool call 做监督，而不是用 `create_supervisor`。这带来更细粒度的上下文工程控制——每个专家能看到什么，由你精确决定。

> A central routing LLM dispatches to specialist agents.
> Decides: loop back to self, hand off to specialist, terminate.
> Specialists do not talk to each other; all routing goes through the supervisor.
> 2026 LangChain recommendation: do supervision through direct tool calls rather than `create_supervisor`. Gives finer context engineering control — you decide exactly what each specialist sees.

### Swarm / peer-to-peer · 蜂群 / 对等网络

- 智能体通过共享的工具表面直接交接（handoff）。
- 没有中央路由器。
- 延迟比 supervisor 低（跳数更少）。
- 更难推理（没有单一控制点）。

框架：LangGraph swarm 拓扑、OpenAI Agents SDK handoffs（当所有智能体都能互相交接时）。

> Agents hand off directly via a shared tool surface.
> No central router.
> Lower latency than supervisor (fewer hops).
> Harder to reason about (no single point of control).

### Hierarchical · 层级制

- supervisor 管理子 supervisor，子 supervisor 管理工作者。
- 在 LangGraph 里实现为嵌套子图（nested subgraphs）；在 CrewAI 里是嵌套 crew。
- 以运维复杂性为代价，扩展到大规模智能体群体。

什么时候需要它：当单个 supervisor 的上下文预算装不下所有专家的描述时。

> Supervisors managing sub-supervisors managing workers.
> Implemented as nested subgraphs in LangGraph; nested crews in CrewAI.
> Scales to large agent populations at the cost of operational complexity.
> When you need it: when a single supervisor's context budget cannot hold descriptions of all specialists.

### Debate · 辩论

- 并行提案者 + 迭代交叉批评（第 25 课）。
- 严格说不是编排——更像验证——但它在框架里确实是一种拓扑选择。

> Parallel proposers + iterative cross-critique (Lesson 25).
> Not really orchestration — more verification — but shows up as a topology choice in frameworks.

### Autonomous crews vs deterministic flows · 自主团队 vs 确定性流

CrewAI 把部署模式形式化为两种：

- **Flow** 用于确定性的、事件驱动的自动化（生产环境的推荐起点）。
- **Crew** 用于自主的、基于角色的协作。

这与上面四种模式正交，但能映射到拓扑：Flow 通常是 supervisor 或 hierarchical；Crew 通常是带 LLM 路由器的 supervisor。

> CrewAI formalizes two deployment modes: Flow for deterministic event-driven automation (recommended starting point for production), Crew for autonomous role-based collaboration.
> Flow is typically supervisor or hierarchical; Crew is typically supervisor with an LLM router.

### Anthropic's guidance · Anthropic 的建议

「LLM 领域的成功，不在于构建最复杂的系统，而在于为你的需求构建合适的系统。」

决策顺序：

1. 单智能体 + 工作流模式（第 12 课）——从这里开始。
2. Supervisor-worker——当你有 2-4 个专家时。
3. Swarm——当延迟比推理清晰度更重要时。
4. Hierarchical——只在 supervisor 的上下文预算撑不住时。
5. Debate——当准确率比成本更重要时。

> "Success in the LLM space isn't about building the most sophisticated system. It's about building the right system for your needs."
> Single agent + workflow patterns (Lesson 12) — start here.
> Supervisor-worker — when you have 2-4 specialists.
> Swarm — when latency matters more than reasoning clarity.
> Hierarchical — only when supervisor context budget fails.

### Where this pattern goes wrong · 这个模式哪里会出问题

- **拓扑优先思维。** 还没弄清多智能体解决什么问题，就先说「我们需要多智能体」。
- **Swarm 里交接来回弹。** A -> B -> A -> B。用跳数计数器来防。
- **假层级。** 因为「企业级」所以三层，实际只有两个团队。压扁它。

> Topology-first thinking. "We need multi-agent" before identifying what problem multi-agent solves.
> Bouncing handoffs in swarm. A -> B -> A -> B. Use hop counters.
> Fake hierarchy. Three layers because "enterprise"; two actual teams. Collapse.

```figure
orchestration-pattern
```

## Build It · 动手造

`code/main.py` 在一个脚本化 LLM 上用 stdlib 实现全部四种模式：

- `Supervisor`——中央路由器。
- `Swarm`——直接交接的对等网络。
- `Hierarchical`——supervisor 的 supervisor。
- `Debate`——并行提案者 + 批评。

每种模式处理同一个三意图任务（退款 / bug / 销售）。轨迹形状各不相同。

运行：

```
python3 code/main.py
```

输出：每个模式的轨迹 + 操作数。Supervisor 最干净；swarm 最短；hierarchical 最深；debate 最贵。

> Each pattern handles the same three-intent task (refund / bug / sales). Trace shapes differ.
> Output: per-pattern trace + op count. Supervisor is cleanest; swarm is shortest; hierarchical is deepest; debate is most expensive.

## Use It · 实战用法

- **LangGraph** 用于 supervisor 和 hierarchical（嵌套子图）。
- **OpenAI Agents SDK** 用于把交接当工具（supervisor 形态）。
- **CrewAI Flow** 用于生产级的确定性流。
- **自研** 用于辩论，或当你想要完全掌控时。

> LangGraph for supervisor and hierarchical (nested subgraphs).
> OpenAI Agents SDK for handoffs-as-tools (supervisor-shaped).
> CrewAI Flow for production deterministic.
> Custom for debate or when you want exact control.

## Ship It · 交付

`outputs/skill-orchestration-picker.md` 会选出一个拓扑并把它实现出来。

> `outputs/skill-orchestration-picker.md` picks a topology and implements it.

## Exercises · 练习

1. 把一个 supervisor-worker 改造成 swarm：删掉路由器。什么会坏？什么会变好？
2. 给 swarm 加一个跳数计数器：3 次交接后拒绝。它能抓住 A->B->A 的来回弹吗？
3. 为一个 12 专家的领域构建两级层级系统。不嵌套的话，上下文预算会在哪里撑不住？
4. 在一个生产形态的工作负载上对四种模式做性能剖析。哪个指标（延迟、成本、准确率、可调试性）上谁赢？
5. 阅读 Anthropic 的「Building Effective Agents」一文。把你每条生产流程映射到四种模式之一。有映射不顺的吗？

> Convert a supervisor-worker to a swarm by removing the router. What breaks? What improves?
> Add a hop counter to the swarm: refuse after 3 handoffs. Does it catch A->B->A bouncing?
> Read Anthropic's "Building Effective Agents" post. Map each of your production flows to one of the four. Any that don't map cleanly?

## Key Terms · 术语表

| Term 术语 | What people say 大家怎么说 | What it actually means 实际含义 |
|------|------------------------|------------------------|
| Supervisor-worker（监督者-工作者） | 「路由器 + 专家」 | 中央 LLM 向专家分派；专家之间互不通信 |
| Swarm（蜂群） | 「对等网络」 | 通过共享工具直接交接；没有中央路由器 |
| Hierarchical（层级制） | 「supervisor 的 supervisor」 | 用嵌套子图支撑大规模群体 |
| Debate（辩论） | 「提案者 + 批评」 | 并行提案者、交叉批评（第 25 课） |
| Tool-call-based supervision（基于 tool call 的监督） | 「不用库的 supervisor」 | 把 supervisor 实现为直接 tool call，换取上下文控制 |
| Crew（自主团队） | 「自主团队」 | CrewAI 的基于角色的协作模式 |
| Flow（确定性流） | 「确定性工作流」 | CrewAI 的事件驱动生产模式 |

## Further Reading · 延伸阅读

- [Anthropic, Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) —— 五种模式 + 智能体 vs 工作流
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) —— supervisor、swarm、hierarchical
- [CrewAI docs](https://docs.crewai.com/en/introduction) —— Crew vs Flow
- [Du et al., Society of Minds (arXiv:2305.14325)](https://arxiv.org/abs/2305.14325) —— 辩论模式
