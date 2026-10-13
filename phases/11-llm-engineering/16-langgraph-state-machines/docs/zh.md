# Agent State Machines — Graphs, Nodes, Checkpoints · 智能体状态机：图、节点与检查点

> 手写的 ReAct 循环就是一个 `while True`。同一个循环写成一张显式的图，就变成可以被检查点（checkpoint）、中断（interrupt）、分支（branch）、时间旅行（time-travel）的东西。智能体没有变，变的是包在它外面的执行框架（harness）。
>
> A ReAct loop written by hand is a `while True`. The same loop written as an explicit graph is something you can checkpoint, interrupt, branch, and time-travel through. The agent hasn't changed. The harness around it has.

**类型：** Build
**语言：** Python
**先修：** Phase 11 · 09（函数调用）、Phase 11 · 14（模型上下文协议）
**时间：** 约 75 分钟

## The Problem · 问题在哪

你上线了一个函数调用（function calling）智能体。它顺利跑了三轮，然后出了岔子：模型试了一个返回 500 的工具，用户中途改变主意，或者智能体在没有任何人签字的情况下决定给订单退款。`while True:` 循环没有任何钩子（hook）。你不能暂停它，不能倒回它，也不能分叉出「如果模型当时选了另一个工具会怎样」的分支。一旦超出 demo 的范围上线，这个智能体就变成一个黑盒：要么成功，要么失败，仅此而已。

下一步一旦你看见它，就再明显不过。智能体本来就是一个状态机（state machine）——系统提示，加消息历史，加待执行的工具调用，加下一个动作。把这个状态机显式化：用节点表示「模型思考」「工具运行」「人类审批」，用边表示它们之间的条件转移。图一旦显式，执行框架就免费得到四件事：检查点（在步骤之间保存状态）、中断（暂停等人）、流式（流式输出 token 与中间事件）、时间旅行（回退到先前状态、尝试另一条分支）。

这个抽象的参考实现是 LangGraph。它不是 LangChain 意义上的智能体框架（「这是 AgentExecutor，祝你好运」）。它是一个图运行时（graph runtime），拥有一流的状态、一流的持久化、一流的中断。智能体循环是你画出来的，不是你手写出来的。

> You ship a function-calling agent. It works for three turns, then something goes wrong: the model tries a tool that returns 500, the user changes their mind mid-task, or the agent decides to refund an order without a human signing off. The `while True:` loop has no hooks. You can't pause it, you can't rewind it, and you can't branch off into "what if the model had picked the other tool." The moment you ship this past a demo, the agent becomes a black box that either worked or didn't.
> The next step is obvious once you see it. The agent is already a state machine — system prompt plus message history plus pending tool calls plus the next action. Make the state machine explicit: nodes for "the model thinks," "a tool runs," "a human approves," and edges for the conditional transitions between them. Once the graph is explicit, the harness gets four things for free: checkpointing (save state between steps), interrupts (pause for a human), streaming (stream tokens and intermediate events), and time-travel (rewind to a prior state and try a different branch).
> The reference implementation of this abstraction is LangGraph. It is not an agent framework in the LangChain sense ("here is an AgentExecutor, good luck"). It is a graph runtime with first-class state, first-class persistence, and first-class interrupts. The agent loop is something you draw, not something you hand-write.

## The Concept · 概念

![LangGraph StateGraph：节点、边与检查点器](../assets/langgraph-stategraph.svg)

一张 `StateGraph` 有三样东西。

1. **State（状态）。** 一个在图里流动的类型化字典（TypedDict 或 Pydantic 模型）。每个节点收到完整状态并返回一个部分更新，LangGraph 按字段用 *reducer* 合并——需要累积的列表用 `operator.add`，默认是覆盖。
2. **Nodes（节点）。** Python 函数 `state -> partial_state`。每个节点是一个离散步骤：「调用模型」「运行工具」「做总结」。
3. **Edges（边）。** 节点之间的转移。静态边只去一个地方。条件边接收一个路由函数 `state -> next_node_name`，让图能根据模型输出分支。

你编译（compile）这张图。compile 绑定拓扑、附加一个检查点器（checkpointer，可选但对生产至关重要），并返回一个可运行对象。你用一个初始状态和一个 `thread_id` 来调用它。执行的每一步都会持久化一个以 `(thread_id, checkpoint_id)` 为键的检查点。

> A `StateGraph` has three things. State: a typed dict that flows through the graph, merged with a reducer per field. Nodes: Python functions `state -> partial_state`. Edges: transitions, static or conditional.
> You compile the graph. Compile binds the topology, attaches a checkpointer (optional but essential for production), and returns a runnable. You invoke it with an initial state and a `thread_id`. Every step of execution persists a checkpoint keyed on `(thread_id, checkpoint_id)`.

### The four superpowers · 四大超能力

**Checkpointing（检查点）。** 每次节点转移都把新状态写进一个存储（测试用内存版，生产用 Postgres/Redis/SQLite）。用同一个 `thread_id` 再次调用图即可恢复，图会从它暂停的地方继续。

**Interrupts（中断）。** 给节点标 `interrupt_before=["human_review"]`，执行就在该节点运行之前停下。状态被持久化。你的 API 用「等待审批」回应用户。稍后对同一个 `thread_id` 发一个带 `Command(resume=...)` 的请求，即可恢复执行。

**Streaming（流式）。** `graph.stream(state, mode="updates")` 在状态增量发生时逐个产出。`mode="messages"` 流式输出模型节点内部的 LLM token。`mode="values"` 产出完整快照。你在 UI 里展示什么，由你挑。

**Time-travel（时间旅行）。** `graph.get_state_history(thread_id)` 返回完整的检查点日志。把任何一个先前的 `checkpoint_id` 传给 `graph.invoke`，你就从那个点分叉。调试利器（「如果模型当时选的是工具 B 呢？」），也是重放生产轨迹做回归测试的利器。

> **Checkpointing.** Every node transition writes the new state to a store (in-memory for tests, Postgres/Redis/SQLite for prod). Resume by calling the graph again with the same `thread_id`.
> **Interrupts.** Mark a node with `interrupt_before=["human_review"]` and execution stops before that node runs. The state persists.
> **Streaming.** `graph.stream(state, mode="updates")` yields state deltas as they happen. `mode="messages"` streams the LLM tokens inside model nodes. `mode="values"` yields full snapshots.
> **Time-travel.** `graph.get_state_history(thread_id)` returns the full checkpoint log. Pass any prior `checkpoint_id` to `graph.invoke` and you fork from that point.

### Reducers are the point · Reducer 才是重点

每个状态字段都有一个 reducer。大多数默认值够用——新值覆盖旧值。但消息列表需要 `operator.add`，让新消息追加而不是替换。并行边各自产生的更新也通过 reducer 合并。如果两个节点都更新 `messages`，而你忘了 `Annotated[list, add_messages]`，第二个会静默胜出，半轮对话就丢了。reducer 是这个库里唯一微妙的东西；把它搞对，其余部分自然组合。

> Every state field has a reducer. Most defaults are fine — a new value overwrites the old. But message lists need `operator.add` so new messages append instead of replacing. Parallel edges merge their updates through the reducer. If two nodes both update `messages` and you forgot the `Annotated[list, add_messages]`, the second wins silently and you lose half the turn. The reducer is the only subtle thing in the library; get it right and the rest composes.

### The ReAct graph in four nodes · 四节点的 ReAct 图

一个生产级 ReAct 智能体是四个节点加两条边：

1. `agent` —— 用当前消息历史调用 LLM。返回助手消息（其中可能带 tool_calls）。
2. `tools` —— 执行最后一条助手消息里的所有 tool_calls，把工具结果作为工具消息追加。
3. 一条从 `agent` 出发的条件边：最后一条消息有 tool_calls 就路由到 `tools`，否则到 `END`。
4. 一条从 `tools` 回到 `agent` 的静态边。

就这么多。用大约 40 行代码，你就得到了完整的 ReAct 循环（Thought → Action → Observation → Thought → …），还自带检查点、中断和流式。

> A production ReAct agent is four nodes and two edges: `agent` calls the LLM, `tools` executes tool_calls, a conditional edge routes from `agent` to `tools` or `END`, and a static edge returns from `tools` to `agent`.
> That is it. You get the full ReAct loop (Thought → Action → Observation → Thought → …) with checkpointing, interrupts, and streaming, in roughly 40 lines of code.

### StateGraph vs Send (fanout) · StateGraph 对比 Send（扇出）

`Send(node_name, state)` 让一个节点可以派发并行子图。例子：智能体决定同时查询三个检索器。每个 `Send` 生成目标节点的一个并行执行；它们的输出经状态 reducer 合并。LangGraph 就是这样在不借助线程原语的情况下表达 orchestrator-workers 模式的。

> `Send(node_name, state)` lets a node dispatch parallel subgraphs. Each `Send` spawns a parallel execution of the target node; their outputs merge through the state reducer. This is how LangGraph expresses the orchestrator-workers pattern without threading primitives.

### Subgraphs · 子图

一张编译好的图可以成为另一张图里的节点。外层图看到的是单个节点；内层图有自己的状态和自己的检查点。团队就是这样构建 supervisor-worker 智能体的：supervisor 图把用户意图路由给按领域划分的 worker 子图。

> A compiled graph can be a node in another graph. The outer graph sees a single node; the inner graph has its own state and its own checkpoints. This is how teams build supervisor-worker agents: the supervisor graph routes user intent to a per-domain worker subgraph.

```figure
l5-state-graph-ledger
```

## Build It · 动手造

### Step 1: state and nodes · 状态与节点

```python
from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

def agent_node(state: State) -> dict:
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: State) -> str:
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END

tool_node = ToolNode(tools=[search_web, read_file])

graph = StateGraph(State)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")

app = graph.compile(checkpointer=MemorySaver())
```

`add_messages` 就是让消息列表累积而不是覆盖的那个 reducer。忘了它是最常见的 LangGraph bug。

> `add_messages` is the reducer that makes the message list accumulate instead of overwrite. Forgetting it is the most common LangGraph bug.

### Step 2: run with a thread · 用线程跑起来

```python
config = {"configurable": {"thread_id": "user-42"}}
for event in app.stream(
    {"messages": [HumanMessage("find the Anthropic headquarters address")]},
    config,
    stream_mode="updates",
):
    print(event)
```

每个更新都是一个字典 `{node_name: state_delta}`。你的前端可以把它们流式推到 UI，让用户看到「智能体正在思考……正在调用 search_web……拿到结果……正在回答」。

> Every update is a dict `{node_name: state_delta}`. Your frontend can stream these to the UI so users see "agent is thinking… calling search_web… got result… answering."

### Step 3: add a human-in-the-loop interrupt · 加一个人在环中断

给节点打标记，让执行在它运行之前暂停。

```python
app = graph.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["tools"],  # pause before every tool call
)

state = app.invoke({"messages": [HumanMessage("delete the production database")]}, config)
# state["__interrupt__"] is set. Inspect proposed tool calls.
# If approved:
from langgraph.types import Command
app.invoke(Command(resume=True), config)
# If denied: write a rejection message and resume
app.update_state(config, {"messages": [AIMessage("Blocked by human reviewer.")]})
```

状态、检查点和线程都跨中断持久存在。除执行期间外，什么都不留在内存里。

> The state, the checkpoint, and the thread all persist across the interrupt. Nothing is in memory except during execution.

### Step 4: time-travel for debugging · 用时间旅行调试

```python
history = list(app.get_state_history(config))
for snapshot in history:
    print(snapshot.values["messages"][-1].content[:80], snapshot.config)

# Fork from a prior checkpoint
target = history[3].config  # three steps back
for event in app.stream(None, target, stream_mode="values"):
    pass  # replay from that point forward
```

输入传 `None` 表示从给定检查点重放；传一个值则表示先把它作为更新追加到该检查点的状态上，再继续往下走。这就是你在不重跑整段对话的前提下复现一次糟糕智能体运行的方法。

> Passing `None` as the input replays from the given checkpoint; passing a value appends it as an update to that checkpoint's state before resuming. This is how you reproduce a bad agent run without re-running the whole conversation.

### Step 5: swap the checkpointer for production · 把检查点器换成生产版

```python
from langgraph.checkpoint.postgres import PostgresSaver

with PostgresSaver.from_conn_string("postgresql://...") as checkpointer:
    checkpointer.setup()
    app = graph.compile(checkpointer=checkpointer)
```

SQLite、Redis 和 Postgres 都是官方自带的。`MemorySaver` 只用于测试。任何要跨重启存活的场景都需要真正的存储。

> SQLite, Redis, and Postgres are shipped. `MemorySaver` is for tests. Anything that persists across restarts wants a real store.

## The Skill · 技能

> 你把智能体构建为图，而不是 `while True` 循环。
>
> You build agents as graphs, not as `while True` loops.

伸手拿 LangGraph 之前，先做一次 60 秒设计：

1. **给节点起名。** 每个离散的决策或带副作用的动作都是一个节点。「智能体思考」「工具运行」「评审者批准」「响应流式输出」。如果你列不出来，这个任务还不具备智能体形态。
2. **声明状态。** 最小化的 TypedDict，每个列表字段都配 reducer。不要把所有东西都塞进 `messages`；把任务专属字段（工作用的 `plan`、`budget` 计数器、`retrieved_docs` 列表）提升到顶层。
3. **画出边。** 默认静态，除非下一步取决于模型输出。每条条件边都要有一个带命名分支的路由函数。
4. **一开始就选好检查点器。** 测试用 `MemorySaver`，其他一切用 Postgres/Redis/SQLite。没有它不要上线——没有检查点器，就没有恢复、没有中断、没有时间旅行。
5. **在工具运行之前决定中断，而不是之后。** 审批放在进入带副作用节点的边上，这样你能在伤害发生前取消；校验放在离开模型的边上，这样你能廉价地拒绝糟糕的调用。
6. **默认开流式。** UI 用 `mode="updates"`，模型节点内部的 token 级流式用 `mode="messages"`，eval 时的完整快照用 `mode="values"`。

拒绝上线没有检查点器的 LangGraph 智能体。拒绝上线在副作用 *之后* 才中断的智能体。拒绝上线 `messages` 字段却没有以 `add_messages` 为 reducer 的智能体。

> Name the nodes. Declare the state. Draw the edges. Choose a checkpointer up front. Decide interrupts before tools run, not after. Stream by default.
> Refuse to ship a LangGraph agent that has no checkpointer. Refuse to ship one that interrupts *after* the side effect. Refuse to ship a `messages` field without `add_messages` as its reducer.

## Exercises · 练习

1. **简单。** 用一个计算器工具和一个网页搜索工具实现上面的四节点 ReAct 图。验证 `list(app.get_state_history(config))` 对一段两轮对话至少返回四个检查点。
2. **中等。** 加一个在 `agent` 之前运行的 `planner` 节点，把结构化的 `plan: list[str]` 写进状态。让 `agent` 把计划步骤标记为已完成。如果在检查点恢复后 `plan` 丢失（reducer 用错了），测试必须失败。
3. **困难。** 构建一个 supervisor 图，用 `Send` 在三个子图（`researcher`、`writer`、`reviewer`）之间路由。每个子图有自己的状态和检查点器。在外层图上加 `interrupt_before=["writer"]`，让人类可以审批研究简报。确认从先前检查点出发的时间旅行只重跑被分叉的分支。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| StateGraph | “LangGraph 的那张图” | 你在 compile 之前往里添加节点和边的构建器对象。 |
| Reducer | “字段怎么合并” | 当某个节点返回某字段的更新时应用的函数 `(old, new) -> merged`；默认是覆盖，`add_messages` 是追加。 |
| Thread（线程） | “一个对话 ID” | 一个 `thread_id` 字符串，为一个会话圈定所有检查点。 |
| Checkpoint（检查点） | “一个暂停的状态” | 节点转移之后全图状态的持久化快照，以 `(thread_id, checkpoint_id)` 为键。 |
| Interrupt（中断） | “暂停等人” | `interrupt_before` / `interrupt_after` 在节点边界停下执行；用 `Command(resume=...)` 恢复。 |
| Time-travel（时间旅行） | “从先前一步分叉” | `graph.invoke(None, config_with_old_checkpoint_id)` 从那个检查点向前重放。 |
| Send | “并行子图派发” | 一个节点可以返回的构造器，用于生成目标节点的 N 个并行执行。 |
| Subgraph（子图） | “作为节点的编译图” | 被当作另一张图里的节点使用的编译版 StateGraph；保留自己的状态作用域。 |

## Further Reading · 延伸阅读

- [LangGraph documentation](https://langchain-ai.github.io/langgraph/) —— StateGraph、reducer、检查点器与中断的权威参考。
- [LangGraph concepts: state, reducers, checkpointers](https://langchain-ai.github.io/langgraph/concepts/low_level/) —— 本课使用的心智模型，直接来自官方一手资料。

- [LangGraph Persistence and Checkpoints](https://langchain-ai.github.io/langgraph/concepts/persistence/) —— Postgres/SQLite/Redis 存储、检查点命名空间与 thread ID 的细节。
- [LangGraph Human-in-the-loop](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/) —— `interrupt_before`、`interrupt_after`、`Command(resume=...)` 与编辑状态模式。
- [Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models" (ICLR 2023)](https://arxiv.org/abs/2210.03629) —— 每个 LangGraph 智能体都在实现的那套模式；读它以理解推理轨迹的理由。
- [Anthropic — Building effective agents (Dec 2024)](https://www.anthropic.com/research/building-effective-agents) —— 该优先哪些图形态（链、路由、orchestrator-workers、evaluator-optimizer），以及何时优先。
- Phase 11 · 09（Function Calling / 函数调用）—— 每个 LangGraph 智能体节点都复用的工具调用原语。
- Phase 11 · 14（Model Context Protocol / 模型上下文协议）—— 经 MCP 适配器接入 LangGraph `ToolNode` 的外部工具发现。
- Phase 11 · 17（Agent framework tradeoffs / 智能体框架取舍）—— 何时选 LangGraph 而不是 CrewAI、AutoGen 或 Agno。
