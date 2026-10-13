# Supervisor / Orchestrator-Worker Pattern · 监督者-编排者模式

> 一个主控智能体（lead agent）负责规划和分派；专业化的工作智能体（worker）在各自独立的上下文中并行执行，然后汇报结果。这就是 Anthropic Research 系统背后的模式（Claude Opus 4 担任主控，Sonnet 4 担任子智能体），在内部研究评测中比单智能体 Opus 4 高出 +90.2%。Anthropic 的工程博客指出，BrowseComp 上 80% 的方差仅由 token 用量就能解释——多智能体获胜的最大原因，是每个子智能体都拿到一个全新的上下文窗口。本课从基础原语出发构建监督者模式，并覆盖来自生产部署的 2026 年工程经验。

> One lead agent plans and delegates; specialized workers execute in parallel contexts and report back. This is the pattern behind Anthropic's Research system (Claude Opus 4 as lead, Sonnet 4 as subagents), measured at +90.2% over single-agent Opus 4 on internal research evals. Anthropic's engineering post reports that 80% of the variance on BrowseComp is explained by token usage alone — multi-agent wins largely because each subagent gets a fresh context window. This lesson builds the supervisor pattern from the primitives and covers the 2026 engineering lessons from production deployments.

**Type:** Learn + Build
**Languages:** Python (stdlib, `threading`)
**Prerequisites:** Phase 16 · 04 (Primitive Model)
**Time:** ~75 minutes

---

## Problem · 问题

研究是单智能体系统最容易失败的原型任务。你问「2023 到 2026 年间多智能体系统有什么变化？」一个单智能体按顺序读五篇论文，用一半的上下文装下论文原文，然后还要把它们放在一起推理。读到第五篇时它已经忘了第一篇。它也无法并行。

监督者模式解决了这个问题：一个主控智能体规划检索，把每个子问题分派给一个 worker，最后做综合。每个 worker 都有自己 200k token 的窗口，只处理一个狭窄的问题。主控永远不看论文原文——只看 worker 的摘要。

Anthropic 的生产级 Research 系统报告称，在内部研究评测上比单个 Opus 4 高出 +90.2%。同一篇文章指出，BrowseComp 方差的 80% 仅由 *token 用量* 就能解释。每个子智能体一个全新上下文，是主要的起效机制。

> Research is the prototypical task that single-agent systems fail. ... The supervisor pattern fixes this: one lead agent plans the search, delegates each sub-question to a worker, and synthesizes. Each worker gets its own 200k-token window for a narrow question. The lead never sees the raw papers — only the worker summaries. ... Fresh context per subagent is the main mechanism.

---

## Concept · 概念

### The pattern · 模式形态

```
                 ┌──────────────┐
                 │   Lead       │  plans, decomposes,
                 │  (Opus 4)    │  synthesizes
                 └──┬────┬───┬──┘
                    │    │   │
            ┌───────┘    │   └───────┐
            ▼            ▼           ▼
      ┌─────────┐  ┌─────────┐  ┌─────────┐
      │ Worker1 │  │ Worker2 │  │ Worker3 │
      │(Sonnet) │  │(Sonnet) │  │(Sonnet) │
      └─────────┘  └─────────┘  └─────────┘
         fresh       fresh        fresh
         context     context      context
```

主控永远不读原始材料。在主控做综合之前，worker 之间互相看不到彼此的工作。每条箭头都是一次带着窄产物（artifact）的交接（handoff）。

> The lead never reads the raw materials. The workers never see each other's work until the lead synthesizes. Each arrow is a handoff with a narrow artifact.

---

### Why it wins · 它为什么能赢

三种机制：

1. **每个子智能体一个全新上下文（fresh context）。** 一个探索「FIPA-ACL 渊源」的 worker 不会背着主控规划时花掉的 40k token。它为一个问题拿到完整的 200k 窗口。
2. **用提示词实现专业化。** 主控的提示词是「分解与综合」，不是「做研究」。每个 worker 的提示词都很窄：「找出 X 里发生了什么变化」。聚焦的提示词产出聚焦的结果。
3. **并行。** worker 并发运行。墙钟时间大约是 `max(worker_times) + plan + synthesis`，而不是 `sum(worker_times)`。

> Three mechanisms: ... **Fresh context per subagent.** A worker exploring "FIPA-ACL heritage" does not carry the 40k tokens the lead spent planning. It gets a 200k window for one question. ... **Specialization via prompt.** The lead's prompt is "decompose and synthesize," not "research." ... **Parallelism.** Workers run concurrently. Wall-clock time is roughly `max(worker_times) + plan + synthesis`, not `sum(worker_times)`.

---

### Engineering lessons (Anthropic 2025) · 工程经验（Anthropic 2025）

Anthropic 的文章列出了若干至今在 2026 年仍然适用的生产经验：

- **按查询复杂度调整投入规模。** 简单查询：一个智能体、3-10 次工具调用。复杂查询：10 个以上智能体。必须由主控来估计这一点，而不是调用方。
- **先宽后窄。** 先分解成宽泛的子问题；如果答案需要更深的挖掘，再为每个子问题派生更多 worker。
- **彩虹部署（rainbow deployment）。** 智能体是长时运行且有状态的。传统的蓝绿部署行不通。Anthropic 用的是彩虹部署：新版本逐步放量，旧版本慢慢排干。
- **token 用量主导一切。** 多智能体的 token 大约是单智能体的 15 倍。只有任务价值配得上成本时才运行它。

> The Anthropic post lists several production lessons that are still 2026-relevant: ... **Scale effort to query complexity.** Simple queries: one agent, 3-10 tool calls. Complex queries: 10+ agents. The lead must estimate this, not the caller. ... **Rainbow deployments.** Agents are long-running and stateful. Traditional blue-green does not work. ... **Token usage dominates.** Multi-agent is ~15× the tokens of single-agent. Only run it when the task value justifies the cost.

---

### The graph-native turn · 图原生转向

LangGraph 最初发布了一个带高层 `create_supervisor` 辅助函数的 `langgraph-supervisor` 库。2025 年，LangChain 把推荐做法改为直接通过工具调用（tool-calling）实现监督者模式，因为工具调用能更好地控制 *监督者能看到什么*（上下文工程）。那个库仍然可用；官方文档现在推荐工具调用形式。

> LangGraph originally shipped a `langgraph-supervisor` library with a high-level `create_supervisor` helper. In 2025 LangChain moved the recommendation to implementing the supervisor pattern via tool-calling directly, because tool calls give more control over *what the supervisor sees* (context engineering). The library still works; the docs now recommend the tool-calling form.

---

### The failure modes · 失败模式

- **主控幻觉出计划。** 如果主控生成的子问题没有真正分解原始问题，worker 就会对着错误的目标做精确研究。
- **worker 过度探索。** 没有明确的范围边界时，worker 会漂移出被指派的子问题，污染综合步骤。
- **综合冲突。** 两个 worker 返回相互矛盾的事实。主控必须要么重问（加一轮），要么显式记录分歧。悄悄挑一边是最坏的失败：用户永远不知道发生过分歧。

> **Lead hallucinates the plan.** If the lead generates sub-questions that do not decompose the real question, workers do precise research on the wrong target. ... **Workers over-explore.** Without explicit scope boundaries, workers drift beyond their assigned sub-question and pollute the synthesis step. ... **Synthesis conflicts.** Two workers return contradictory facts. ... Silent picking of one side is the worst failure: the user never knows disagreement happened.

---

### When supervisor is wrong · 什么时候监督者是错误选择

- **顺序任务。** 如果第 2 步真的需要第 1 步的输出，并行毫无收益。用流水线（CrewAI Sequential、LangGraph 线性图）。
- **简单查询。** 单智能体更快更便宜。派生 worker 之前先做主控的「投入规模」检查。
- **严格确定性。** 监督者使用 LLM 选择的分派。当审计/重放比适应性更重要时，静态图更好。

> **Sequential tasks.** If step 2 literally needs step 1's output, parallelism buys nothing. Use a pipeline (CrewAI Sequential, LangGraph linear graph). ... **Simple queries.** Single-agent handles them faster and cheaper. ... **Strict determinism.** Supervisor uses LLM-selected delegation. Static graphs are better when audit/replay matter more than adaptability.

```figure
supervisor-hierarchy
```

---

## Build It · 动手造

`code/main.py` 用 `threading` 实现了一个由三个并行 worker 组成的监督者。主控把一个查询分解成子问题，worker 在每个子问题上并发运行，最后主控做综合。没有真实 LLM——worker 是脚本化的，用来模拟「抓取并摘要」。

关键结构：

- `Lead.plan(query)` 把查询拆成 3 个子问题。
- `Worker.run(sub_q)` 返回一个伪造的摘要（在生产中可以是任何会使用工具的智能体）。
- `Lead.run(query)` 用线程启动 worker，join，然后综合。

Run:

```
python3 code/main.py
```

输出展示计划、带起止时间戳的并行 worker 轨迹，以及最终的综合。你可以直观看到墙钟时间的收益：三个 0.3 秒的 worker 总共只花约 0.35 秒，而不是 0.9 秒。

> `code/main.py` implements a supervisor of three parallel workers using `threading`. The lead decomposes a query into sub-questions, workers run concurrently on each sub-question, and the lead synthesizes. No real LLMs — the workers are scripted to simulate fetch-and-summarize. ... Output shows the plan, the parallel worker traces with start/end timestamps, and the final synthesis. You can see the wall-clock wins: three 0.3-second workers run in ~0.35 seconds, not 0.9.

---

## Use It · 实战用法

`outputs/skill-supervisor-designer.md` 接收一个用户查询，产出一份监督者模式设计：主控系统提示词、worker 角色、子问题分解规则，以及综合模板。在构建新的研究型智能体系统之前先用它。

> `outputs/skill-supervisor-designer.md` takes a user query and produces a supervisor-pattern design: lead system prompt, worker roles, sub-question decomposition rules, and the synthesis template. Use this before building a new research-style agent system.

---

## Ship It · 交付

部署监督者模式前的检查清单：

- **模型配对。** 主控用推理档模型（Opus 级、`o3` 级）。worker 用更快更便宜的模型（Sonnet、`o4-mini`）。
- **worker 超时。** 任何超过中位运行时间 2 倍的 worker 都被杀掉；主控要么以更窄的范围重新派生，要么在没有它的情况下继续。
- **每个 worker 的 token 上限。** 硬上限（比如预期综合输入的 10 倍）防止失控的 worker 烧穿预算。
- **可观测性。** 追踪主控的计划、每个 worker 的工具调用，以及综合。这是一切事后调试的基础。
- **彩虹发布。** 有状态的长时运行智能体需要渐进式版本过渡，而不是热替换。

> Checklist before deploying a supervisor pattern: ... **Model pairing.** Lead on a reasoning-tier model (Opus class, `o3` class). Workers on a faster, cheaper model (Sonnet, `o4-mini`). ... **Worker timeout.** Any worker that exceeds 2× median runtime gets killed; the lead either re-spawns with narrower scope or proceeds without it. ... **Observability.** Trace the lead's plan, each worker's tool calls, and the synthesis. This is the basis for any post-hoc debugging. ... **Rainbow rollout.** Stateful long-running agents need gradual version transition, not hot swap.

---

## Exercises · 练习

1. 跑 `code/main.py`，然后把主控改成派生 5 个 worker 而不是 3 个。观察墙钟时间的变化。在这个演示里，worker 数到多少时派生开销会超过并行收益？
2. 实现 worker 超时：杀掉任何运行超过 0.5 秒的 worker，让主控综合剩下的结果。你需要什么可观测性才能知道某个 worker 被切掉了？
3. 给主控的综合加一个冲突检测步骤：如果两个 worker 返回矛盾的答案，主控记录分歧而不是挑一边。不调用 LLM 的前提下你怎么检测矛盾？
4. 读 Anthropic 的 Research 系统工程博客。列出这个玩具演示要上生产需要采纳的三条实践。
5. 比较 LangGraph 的 `create_supervisor`（遗留）与新的工具调用推荐。哪个能让你更好地控制监督者看到的内容？为什么 Anthropic 在综合时只显式传入子答案、而不传 worker 的原始上下文？

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Supervisor | 「主控智能体」 | 负责规划、分派和综合的编排者智能体。自己不干活。 |
| Worker | 「子智能体」 | 被监督者调用的聚焦智能体，范围窄，拥有自己的上下文窗口。 |
| Orchestrator-worker | 「监督者模式」 | 同一个东西，不同的名字。2026 年的文献两种都用。 |
| Fresh context | 「干净的窗口」 | worker 的上下文从它自己的系统提示词和被指派的问题开始，不带主控的历史。 |
| Rainbow deployment | 「渐进式发布」 | 长时运行的有状态智能体需要带版本的排干再替换，而不是蓝绿部署。 |
| Token dominance | 「上下文才是变量」 | 据 Anthropic，研究评测 80% 的方差来自总 token 用量，而不是模型选择。 |
| Scale effort | 「智能体数量匹配复杂度」 | 主控估计查询难度，据此派生 1 个或 10 个以上 worker。 |
| Synthesis conflict | 「worker 意见不合」 | 两个 worker 返回矛盾的事实；主控必须把分歧摆上台面，不能悄悄挑一边。 |

---

## Further Reading · 延伸阅读

- [Anthropic engineering — How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) —— 监督者模式的生产级参考
- [LangGraph workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) —— 工具调用式监督者是现在推荐的形式
- [LangGraph supervisor reference](https://reference.langchain.com/python/langgraph-supervisor) —— 遗留辅助函数，2026 年的生产中仍在使用
- [OpenAI cookbook — Orchestrating Agents: Routines and Handoffs](https://developers.openai.com/cookbook/examples/orchestrating_agents) —— 基于交接的监督者变体
