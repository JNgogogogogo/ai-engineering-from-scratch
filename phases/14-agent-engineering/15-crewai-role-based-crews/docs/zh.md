# Role-Based Agent Teams — Roles, Tasks, Processes · 角色制 agent 团队——角色、任务、流程

> Four primitives: Agent, Task, Crew, Process. Two top-level shapes: Crews (autonomous, role-based collaboration) and Flows (event-driven, deterministic). CrewAI is the 2026 reference implementation, and its docs are blunt: "for any production-ready application, start with a Flow."

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 12 (Workflow Patterns), Phase 14 · 14 (Actor Model)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 说出 CrewAI 的四个原语（Agent、Task、Crew、Process）以及各自掌管什么
- 区分 Sequential、Hierarchical 和计划中的 Consensus 流程；按工作负载选一个
- 区分 Crew（自主、角色制）与 Flow（事件驱动、确定性），并解释文档里的生产建议
- 用 `@tool` 装饰器和 `BaseTool` 子类接工具；想清楚结构化输出与自由文本的取舍
- 说出 CrewAI 的四种记忆类型，以及各自何时划算
- 实现一个产出简报的 stdlib 三 agent crew（researcher、writer、editor）
- 识别 CrewAI 的三种失败模式：prompt 膨胀、manager-LLM 税、脆弱的交接

> Name CrewAI's four primitives (Agent, Task, Crew, Process) and what each owns.
> Distinguish Sequential, Hierarchical, and the planned Consensus process; pick one per workload.
> Distinguish Crews (autonomous role-based) from Flows (event-driven deterministic), and explain the docs' production recommendation.
> Wire tools with the `@tool` decorator and `BaseTool` subclass; reason about structured outputs vs free text.
> Name the four CrewAI memory types and when each pays off.
> Implement a stdlib three-agent crew (researcher, writer, editor) that produces a brief.
> Spot the three CrewAI failure modes: prompt-bloat, manager-LLM tax, brittle handoffs.

## The Problem · 问题在哪

采用多 agent 框架的团队都会撞上同一堵墙。「自主协作」在 demo 里听着很美。然后客户提了一个 bug，你需要确定性的重放。或者财务来问：一个由 LLM 做路由的 crew 每次运行要花多少钱。或者 on-call 需要知道凌晨 3 点是哪个 agent 卡住了。

自由形态的 LLM 路由 crew 一个都答不利索。纯 DAG 全都答得上，却丢掉了头脑风暴 agent 需要的那种探索形状。

CrewAI 的拆分对这个取舍很诚实。Crew 给协作式、角色制、探索性的工作。Flow 给事件驱动、代码掌管、可审计的生产。同一个框架，两种形状，按面选。

> Free-form LLM-routed crews answer none of those cleanly. Pure DAGs answer them all but lose the exploratory shape a brainstorming agent needs.
> CrewAI's split is honest about the trade. Crews for collaborative, role-based, exploratory work. Flows for event-driven, code-owned, auditable production. Same framework, two shapes, pick per surface.

## The Concept · 概念

### Four primitives · 四个原语

CrewAI 的表面很小。记住这些，其余都是配置。

- **Agent。** `role + goal + backstory + tools + (可选) llm`。backstory 是承重墙。它塑造语气、判断、以及 agent 什么时候收手。工具是 agent 可以调用的函数（下文详述）。
- **Task。** `description + expected_output + agent + (可选) context + (可选) output_pydantic`。一个可复用的工作单元。`expected_output` 是契约。`context` 列出其输出会被传进来的上游任务。`output_pydantic` 强制结构化形状。
- **Crew。** 容器。持有 `agents` 列表、`tasks` 列表、`process`，以及可选的 `memory` + `verbose` + `manager_llm` 设置。
- **Process。** 执行策略。Sequential、Hierarchical、Consensus（计划中）。决定运行的形状。

agent 之间不直接看见彼此。任务引用 agent。Crew 给任务排顺序。Process 决定谁来挑下一个任务。这就是全部的心智模型。

> **Agent.** `role + goal + backstory + tools + (optional) llm`. The backstory is load-bearing. It shapes tone, judgment, when the agent stops.
> Agents do not see each other directly. Tasks reference agents. The Crew sequences tasks. The Process decides who picks the next task. That is the whole mental model.

> **Validated against（对照版本验证）** CrewAI 0.86 (2026-05)。更新的版本可能重命名或合并 process 类型；在依赖某个具体形状之前，请查看 [CrewAI Processes 文档](https://docs.crewai.com/concepts/processes)。

### Sequential vs Hierarchical vs Consensus · 顺序、分层与共识

- **Sequential（顺序）。** 任务按声明顺序运行。任务 N 的输出作为 `context` 供任务 N+1 使用。成本最低。最可预测。顺序固定时用它。
- **Hierarchical（分层）。** 一个 manager Agent（单独的 LLM 调用）在专家之间做路由。CrewAI 要么从你的 `manager_llm` 配置生成这个 manager，要么用默认值。manager 每轮挑选下一个任务，可以拒绝或改道。当你有四个以上专家、且顺序真的取决于先前的输出时用它。
- **Consensus（共识）。** 计划中，公有 API 目前未实现。文档为未来基于投票的流程预留了这个名字。今天别依赖它。

Hierarchical 在每一次专家调用之上，额外加一次每轮的 LLM 调用（manager）。一个五步运行的 token 成本可能翻三倍。只有在你需要那个路由时才付这笔钱。

> **Consensus.** Planned, not currently implemented in the public API. The docs reserve the name for a future voting-based process. Do not rely on it today.
> Hierarchical adds a per-round LLM call (the manager) on top of every specialist call. Token cost can triple on a five-step run. Pay for it only when you need the routing.

### Crews vs Flows · Crew 与 Flow

这是文档在 2026 年主打的框架。

- **Crew。** LLM 驱动的自主性。框架在运行时决定形状。适合：研究、头脑风暴、初稿，以及一切「路径本身就是答案的一部分」的场合。难以重放。难以测试。原型成本低。
- **Flow。** 你自己拥有的事件驱动图。`@start` 标记入口。`@listen(topic)` 标记「另一个步骤发出该 topic 时触发」的步骤。每一步都是普通 Python（内部可以调用 Crew）。适合：生产。可观测。可测试。确定性。

文档 2026 年的生产建议：从 Flow 开始。当自主性挣得回自己的成本时，在 Flow 步骤内部以 `Crew.kickoff()` 调用的方式把 Crew 卷进来。Flow 给你审计轨迹，Crew 给你探索。做组合题，不做选择题。

> **Crew.** LLM-driven autonomy. The framework picks the shape at runtime. Good for: research, brainstorming, first drafts, anywhere the path is part of the answer. Hard to replay. Hard to test. Cheap to prototype.
> **Flow.** Event-driven graph you own. `@start` marks the entry. `@listen(topic)` marks a step that fires when another step emits that topic. Each step is plain Python (can call a Crew internally). Good for: production. Observable. Testable. Deterministic.
> The docs' 2026 production recommendation: start with a Flow. Fold Crews in as `Crew.kickoff()` calls from inside Flow steps when autonomy earns its cost. The Flow gives you the audit trail, the Crew gives you the exploration. Compose, do not pick.

### Tool integration · 工具集成

给 Agent 配工具的三种方式。选最贴合需求的那一个。

1. **`@tool` 装饰器。** 纯函数变成工具。函数签名就是 schema；docstring 是 LLM 看到的描述。最适合一次性的辅助函数。

   ```python
   from crewai.tools import tool

   @tool("Search the web")
   def search(query: str) -> str:
       """Return top results for the query."""
       return run_search(query)
   ```

2. **`BaseTool` 子类。** 基于类的工具，带显式的 args schema、异步支持、重试。当工具有状态（一个 client、一个缓存）或需要结构化参数时用它。

   ```python
   from crewai.tools import BaseTool
   from pydantic import BaseModel

   class SearchArgs(BaseModel):
       query: str
       limit: int = 10

   class SearchTool(BaseTool):
       name = "web_search"
       description = "Search the web and return top results."
       args_schema = SearchArgs

       def _run(self, query: str, limit: int = 10) -> str:
           return self.client.search(query, limit=limit)
   ```

3. **内置工具箱。** CrewAI 自带第一方适配器：`SerperDevTool`、`FileReadTool`、`DirectoryReadTool`、`CodeInterpreterTool`、`RagTool`、`WebsiteSearchTool`。一次 import 就接好。

结构化输出用 Pydantic。在 Task 上传 `output_pydantic=MyModel`。CrewAI 对照模型校验 LLM 响应，要么矫正（coerce）要么重试。再配一个收紧的 `expected_output` 字符串。自由文本输出对草稿来说没问题；结构化输出才是下游 Flow 能消费的东西。

> Three ways to give an Agent a tool. Pick the simplest one that fits.
> **`@tool` decorator.** Pure functions become tools. Signature is the schema; docstring is the description the LLM sees. Best for one-off helpers.
> **`BaseTool` subclass.** Class-based tool with explicit args schema, async support, retries.
> Structured outputs use Pydantic. Pass `output_pydantic=MyModel` on the Task. CrewAI validates the LLM response against the model and either coerces or retries. Pair this with a tight `expected_output` string. Free-text outputs are fine for drafts; structured outputs are what downstream Flows can consume.

### Memory hooks · 记忆钩子

CrewAI 开箱自带四种记忆类型。它们可以组合：一个 Crew 可以同时开启全部四种。

> **Validated against** CrewAI 0.86 (2026-05)。近期的版本把一切都路由进一个统一的 `Memory` 系统，由它包裹这四个存储。下面的概念模型仍然成立，但在更新的版本里，公有类表面可能收拢成单一的 `Memory` 入口；当前 API 请查看 [CrewAI memory 文档](https://docs.crewai.com/concepts/memory)。

- **Short-term（短期）。** 单次运行内的对话缓冲。结束时清空。
- **Long-term（长期）。** 跨运行持久。存在向量库（vector DB）里（默认 Chroma，可换）。按与当前任务的相似度检索。
- **Entity（实体）。** 按实体存放的事实。「客户 X 在企业版套餐上。」按实体键控，不按相似度。跨运行存活。
- **Contextual（情境）。** 装配时检索。在 Agent 需要的那一刻拉取相关记忆，而不是预载。

在 Crew 上用 `memory=True` 或按类型配置来开启。由你配置的 embeddings 提供方支撑（默认 OpenAI，可换成本地）。在那些更薄的框架面前，记忆是 CrewAI 挣回票价的地方之一；纯 LangGraph 要求你把这几样里的每一个都自己接一遍。

> **Short-term.** Conversation buffer within a single run. Wiped at the end.
> **Long-term.** Persisted across runs. Stored in a vector DB (Chroma by default, swappable). Retrieved by similarity to the current task.
> **Entity.** Per-entity facts. "Customer X is on the enterprise plan." Keyed by entity, not by similarity. Survives across runs.
> **Contextual.** Assembly-time retrieval. Pulls relevant memory at the moment the Agent needs it, not preloaded.
> Enable on the Crew with `memory=True` or per-type config. Backed by an embeddings provider you configure (defaults to OpenAI, swappable to local). Memory is one of the places CrewAI earns its keep against thinner frameworks; pure LangGraph requires you to wire each of these yourself.

### When role-based teams fit · 角色制团队什么时候合适

- 三到六个有具名角色、走协作流程的 agent。起草、评审、规划、头脑风暴。
- LLM 对下一步的判断本身就是价值一部分的路由场景（Hierarchical）。
- 一切「团队更愿意读 `role + goal + backstory` 而不是图定义」的场合。

> Three to six agents with named roles and a collaborative workflow. Drafting, reviewing, planning, brainstorming.
> Routing where the LLM's judgment about the next step is part of the value (Hierarchical).
> Anywhere the team is happier reading `role + goal + backstory` than reading a graph definition.

### When they do not · 什么时候不合适

- 严格排序的确定性 DAG。用 LangGraph（Lesson 13）。图形状才是对的抽象；CrewAI 的角色框架是摩擦。
- 亚秒级延迟预算。Hierarchical 会加往返。连 Sequential 都会串行化那些包含 backstory 和先前输出的 prompt。
- 单 agent 回路。跳过框架；一个 agent 回路（Lesson 1）加一个工具注册表更短。

Lesson 17（Agent Framework Tradeoffs）用一张矩阵把这件事讲清楚。简版：CrewAI 坐在「协作式角色制」那个角落。

> Deterministic DAGs with strict ordering. Use LangGraph (Lesson 13). The graph shape is the right abstraction; CrewAI's role framing is friction.
> Sub-second latency budgets. Hierarchical adds round trips. Even Sequential serializes prompts that include backstories and prior outputs.
> Single-agent loops. Skip the framework; an agent loop (Lesson 1) plus a tool registry is shorter.

### Dependency shape · 依赖形状

不依赖 LangChain。Python 3.10 到 3.13。用 `uv`。Star 数：见 [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI)（截至 2026-05 的快照）。AWS Bedrock 集成有文档；厂商基准报告相对 LangGraph 在 QA 负载上有可观提速，但方法论（数据集、硬件、评测指标）没有公开，所以把框架厂商的数字当作方向性参考就好。

> Independent of LangChain. Python 3.10 to 3.13. Uses `uv`. AWS Bedrock integration is documented; vendor benchmarks report a substantial speedup vs LangGraph on QA workloads, but the methodology (dataset, hardware, evaluation metric) is not published, so treat framework-vendor numbers as directional only.

### Where this pattern goes wrong · 这个模式哪里会出错

- **backstory 导致 prompt 膨胀。** 每个 agent 2000 词的 backstory，加上五个 agent 的 crew，在第一次工具调用之前就把上下文预算烧光了。backstory 控制在 200 词以内。跨 agent 复用措辞；别把 house style 重复五遍。
- **manager-LLM token 税。** Hierarchical 流程在每一次专家调用之前加一次 manager LLM 调用。一个五个任务的 crew 是六次 LLM 调用而不是五次，而且 manager 调用还带着完整的任务列表加上先前输出。除非路由取决于输出，否则换回 Sequential。
- **脆弱的交接。** 任务 N 的 `expected_output` 是「一份大纲」。任务 N+1 把它当 `context` 读，并试图解析三个小节。LLM 却产出了四节。下游的 Agent 开始即兴发挥。修法是给任务 N 加 `output_pydantic`，让任务 N+1 读到类型化对象，而不是自由文本。
- **把 Crew 当生产。** 自由形态的 Crew 不加 Flow 包装就直接上生产。输出方差大；重放不可能；on-call 没法把一次坏运行和一次好运行做 diff。用 Flow 包一层。

```figure
ae-crew-vs-flow
```

> **Prompt-bloat from backstories.** A 2000-word backstory per agent and a five-agent crew burns the context budget before the first tool call. Keep backstories under 200 words.
> **Manager-LLM token tax.** Hierarchical process adds a manager LLM call before every specialist call. On a five-task crew that is six LLM calls instead of five, and the manager call carries the full task list plus prior outputs. Switch to Sequential unless routing depends on output.
> **Brittle handoffs.** Fix with `output_pydantic` on Task N so Task N+1 reads a typed object, not free text.
> **Crew-as-prod.** Free-form Crew shipped to production without a Flow wrapper. Output variability is high; replay is impossible; on-call cannot diff a bad run against a good one. Wrap with a Flow.

## Build It · 动手造

`code/main.py` 实现两种形状的 stdlib 版本，外加一个三 agent crew。

形状：

- `Agent`、`Task` dataclass，对齐 CrewAI 的表面。
- `SequentialCrew.kickoff(inputs)` 按声明顺序跑任务，把输出作为 `context` 一路传递。
- `HierarchicalCrew.kickoff(topic)` 加一个每轮挑选下一个专家的 manager Agent，遇到 "done" 停下。
- 带 `@start` 和 `@listen(topic)` 装饰器的 `Flow`，一个小事件循环，和一条轨迹。
- 镜像 CrewAI `@tool` 形状的 `tool(name)` 装饰器。
- 带 `short_term`、`long_term`、`entity` 存储的 `Memory`；模拟的相似度用 numpy。
- Mock 的 LLM 响应是按「角色 + 输入前缀」键控的硬编码字符串。无网络。确定性。

具体演示：researcher、writer、editor 的 crew 产出一份关于「agent engineering 2026」的简报。Researcher 拉（mock 的）资料。Writer 起草。Editor 收紧。同一个 crew 再走一遍 Flow，展示确定性的形状。

运行：

```bash
python3 code/main.py
```

轨迹覆盖：sequential crew 经 `context` 传递输出、带 manager 挑选的 hierarchical crew（researcher、writer、editor，然后 "done"）、以显式 topic（`researched`、`drafted`、`edited`）跑同样三步的 flow、经 `@tool` 路由的工具调用，以及跨两次 kickoff 存活的长期记忆。

Crew 的轨迹是流动的；manager 原则上可以重新排序。Flow 的轨迹是固定的。这个选择本身就是本课。

> Mock LLM responses are hardcoded strings keyed off role plus input prefix. No network. Deterministic.
> The Crew trace is fluid; the manager could in principle re-order. The Flow trace is fixed. That choice is the lesson.

## Use It · 实战用法

- **CrewAI Flow** 给生产。哪怕这个 Flow 只有一个步骤、内部调 `Crew.kickoff()`。Flow 给你审计边界。
- **CrewAI Crew（Sequential）** 给顺序清晰的协作工作，尤其是初稿和评审回路。
- **CrewAI Crew（Hierarchical）** 当路由取决于输出、且你有四个以上专家时。
- **LangGraph**（Lesson 13）给显式状态机、持久恢复、严格排序。
- **AutoGen v0.4**（Lesson 14）给 actor 模型并发和故障隔离。
- **OpenAI Agents SDK**（Lesson 16）给 OpenAI 优先、带 handoff 和护栏的产品。
- **Claude Agent SDK**（Lesson 17）给 Claude 优先、带子 agent 和会话存储的产品。

> **CrewAI Flow** for production. Even when the Flow is one step that calls `Crew.kickoff()`. The Flow gives the audit boundary.
> **CrewAI Crew (Sequential)** for clear-ordering collaborative work, especially first drafts and review loops.
> **CrewAI Crew (Hierarchical)** when routing depends on output and you have four or more specialists.
> **LangGraph** (Lesson 13) for explicit state machines, durable resume, strict ordering.

## Ship It · 交付

`outputs/skill-crew-or-flow.md` 为任务挑选 Crew 或 Flow，并搭出最小实现。硬性拒绝：没有 backstory 的 Crew、没有显式 topic 的 Flow、专家少于三个的 Hierarchical。

> `outputs/skill-crew-or-flow.md` picks Crew vs Flow for a task and scaffolds the minimal implementation. Hard rejects on Crew-without-backstory, Flow-without-explicit-topics, Hierarchical with under three specialists.

## Pitfalls · 坑

- **backstory 当调味料。** 它会塑造输出。每个 agent 测三个变体；方差是真实存在的。选一个，冻结它。
- **跳过 `expected_output`。** 每个任务没有契约，下游任务就接到 LLM 随便产出的东西。Crew 跑起来了；审计崩了。
- **记忆常开。** 长期记忆每次运行都写。向量库膨胀。检索变吵。把写入限定在事实确实持久的任务上。
- **manager prompt 漂移。** Hierarchical 的 manager prompt 是隐式的。当路由变得诡异时，开 verbose 模式把它倒出来读。
- **Crew 里的工具副作用。** 一个 Crew 调用某个工具的次数可能超出预期。POST、DELETE、支付属于 Flow 步骤，永远不要放进 Crew 工具。

> **Backstory as flavor.** It shapes outputs. Test three variants per agent; variance is real. Pick one, freeze it.
> **Skipping `expected_output`.** Without a contract per task, downstream tasks pick up whatever the LLM produced. Crew runs; audit fails.
> **Memory always-on.** Long-term writes every run. Vector DB grows. Retrieval gets noisy. Scope writes to tasks where the fact is persistent.
> **Tool side effects in Crews.** A Crew can call a tool more times than expected. POST, DELETE, payment belong in a Flow step, never a Crew tool.

## Exercises · 练习

1. 把 Sequential crew 改写成 Flow。数一数方差下降的触点。记下可读性在哪里下降了。
2. 给 crew 加实体记忆：关于某客户的事实跨 kickoff 存活。验证检索能拉到正确的实体。
3. 实现一个 Hierarchical 流程：在 writer 的输出至少有三段之前，manager 拒绝路由给 editor。把重试轨迹打出来。
4. 为（mock 的）网页搜索接一个 `BaseTool` 子类。对比轨迹形状与 `@tool` 装饰器版本。
5. 给 editor 任务加 `output_pydantic=Brief`，其中 `Brief` 含 `title`、`summary`、`sections`。让 writer 任务输出一次坏 JSON；在轨迹里验证 CrewAI 的重试行为。
6. 读 CrewAI 文档导论。把玩具移植到真正的 `crewai` API。stdlib 版本跳过了哪些保证？
7. 把 AgentOps 或 Langfuse（Lesson 24）接到一次真实运行上。stdlib 版本里你错过了哪些轨迹？

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| Agent | 「人设」 | Role + goal + backstory + tools |
| Task | 「工作单元」 | 描述 + 期望输出 + 承接者 + 可选的结构化输出 |
| Crew | 「agent 团队」 | Agents + Tasks + Process 的容器 |
| Process | 「执行策略」 | Sequential / Hierarchical / Consensus（计划中） |
| Flow | 「确定性工作流」 | 事件驱动、代码掌管、可测试 |
| Backstory | 「人设 prompt」 | Agent 的语气与判断塑造器 |
| `@tool` | 「函数工具」 | 把函数变成 Agent 可调用工具的装饰器 |
| `BaseTool` | 「类工具」 | 基于类的工具，带 args schema、重试、异步支持 |
| Entity memory（实体记忆） | 「按实体存的事实」 | 以客户 / 账户 / issue 为范围 |
| Long-term memory（长期记忆） | 「跨运行记忆」 | 向量库支撑、跨 kickoff 存活的记忆 |
| Contextual memory（情境记忆） | 「即时检索」 | 在 Agent 需要的那一刻拉取的记忆 |
| Manager LLM | 「路由 agent」 | Hierarchical 流程里挑选下一个任务的额外 LLM |
| `expected_output` | 「任务契约」 | 告诉 Agent（和审计）返回什么形状的字符串 |

## Further Reading · 延伸阅读

- [CrewAI docs introduction](https://docs.crewai.com/en/introduction)：概念与推荐的生产路径
- [CrewAI Flows guide](https://docs.crewai.com/en/concepts/flows)：事件驱动形状、`@start`、`@listen`
- [CrewAI tools reference](https://docs.crewai.com/en/concepts/tools)：`@tool`、`BaseTool`、内置工具箱
- [CrewAI memory](https://docs.crewai.com/en/concepts/memory)：短期、长期、实体、情境
- [Anthropic, Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)：多 agent 什么时候有帮助、什么时候没有
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)：状态机替代方案
