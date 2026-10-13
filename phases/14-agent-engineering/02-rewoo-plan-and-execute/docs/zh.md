# ReWOO and Plan-and-Execute: Decoupled Planning · ReWOO 与 Plan-and-Execute：解耦式规划

> ReAct 把思考和行动交织在同一条流里。ReWOO 把它们分开：先做一份完整的大计划，再执行。token 省 5 倍，HotpotQA 准确率 +4%，而且你可以把 planner 蒸馏进一个 7B 模型。Plan-and-Execute 把它泛化；Plan-and-Act 把它扩展到网页导航。

> ReAct interleaves thought and action in one stream. ReWOO separates them: one big plan up front, then execute. 5x fewer tokens, +4% accuracy on HotpotQA, and you can distill the planner into a 7B model. Plan-and-Execute generalized it; Plan-and-Act scaled it to web navigation.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop)
**Time:** ~60 minutes

---

## Learning Objectives · 学习目标

- 解释 ReWOO 的 Planner / Worker / Solver 三分法为什么比 ReAct 的交织循环更省 token、更稳健。
- 实现一个计划 DAG、一个按依赖顺序执行的执行器，以及一个组合 worker 输出的 solver——全部用标准库。
- 用 2026 年的「五种 workflow 模式」框架（Anthropic），判断一个任务该跑 plan-then-execute 还是交织式 ReAct。
- 识别什么时候需要 Plan-and-Act 的合成计划数据来支撑长程网页或移动任务。

> Explain why ReWOO's Planner / Worker / Solver split saves tokens and improves robustness over ReAct's interleaved loop.
> Implement a plan DAG, a dependency-ordered executor, and a solver that composes worker outputs — all stdlib.
> Decide when a task should run as plan-then-execute vs interleaved ReAct, using the 2026 "five workflow patterns" framing (Anthropic).
> Recognize when Plan-and-Act's synthetic plan data is needed for long-horizon web or mobile tasks.

---

## The Problem · 问题在哪

ReAct 的思考-行动-观察交织循环简单而灵活，但每次工具调用都必须携带完整的先前上下文——包括之前的每一条思考。token 用量随深度呈平方级增长。更糟的是：当某个工具在循环中途失败，模型必须从错误观察出发重新推导整个计划。

ReWOO（Xu et al., arXiv:2305.18323，2023 年 5 月）注意到了这一点，并下了一个注：提前规划整件事，并行获取证据，最后组合出答案。一次 LLM 调用做规划，N 次工具调用拿证据（可以并行），一次 LLM 调用求解。这笔交易是用灵活性（计划是静态的）换大幅更好的 token 效率和更清晰的失败模式。

> ReAct's interleaved thought-action-observation loop is simple and flexible, but each tool call has to carry the full prior context — including every previous thought. Token usage grows quadratically with depth. Worse: when a tool fails mid-loop, the model has to re-derive the whole plan from the error observation.
> ReWOO (Xu et al., arXiv:2305.18323, May 2023) noticed this and made a bet: plan the whole thing up front, fetch evidence in parallel, compose the answer at the end. One LLM call to plan, N tool calls for evidence (can be parallel), one LLM call to solve. The trade is less flexibility (the plan is static) for much better token efficiency and clearer failure modes.

---

## The Concept · 概念

### The three roles · 三个角色

```
Planner:  user_question -> [plan_dag]
Workers:  [plan_dag]     -> [evidence]        (tool calls, possibly parallel)
Solver:   user_question, plan_dag, evidence -> final_answer
```

Planner 产出一个 DAG。每个节点写明一个工具、它的参数，以及它依赖哪些更早的节点（形如 `#E1`、`#E2` 的引用）。Worker 按拓扑序执行节点。Solver 把一切缝合起来。

> Planner produces a DAG. Each node names a tool, its arguments, and which earlier nodes it depends on (references like `#E1`, `#E2`). Workers execute nodes in topological order. Solver stitches everything together.

---

### Why 5x fewer tokens · 为什么 token 少 5 倍

ReAct 的提示词长度随步数线性增长。到第 10 步时，提示词里装着思考 1 加行动 1 加观察 1，再加思考 2 加行动 2 加观察 2，以此类推。每个中间步骤还冗余地重复包含原始提示词。

ReWOO 只付一次 planner 提示词（大）、N 个小的 worker 提示词（每个只含工具调用本身，没有链条），和一次 solver 提示词。论文测得在 HotpotQA 上约省 5 倍 token，同时绝对准确率 +4。

> ReAct grows prompt length linearly with step count. At step 10, the prompt contains thought 1 plus action 1 plus observation 1 plus thought 2 plus action 2 plus observation 2, and so on. Each intermediate step also redundantly includes the original prompt.
> ReWOO pays one planner prompt (large), N small worker prompts (each just the tool call, no chain), and one solver prompt. On HotpotQA the paper measures ~5x fewer tokens while scoring +4 absolute accuracy.

---

### Why it is more robust · 为什么更稳健

如果 ReAct 里 worker 3 失败了，循环必须在中途对着错误做推理。在 ReWOO 里，worker 3 返回一个错误字符串；solver 在上下文里连同原始计划一起看到它，可以优雅降级。失败定位是按节点的，不是按步骤的。

> If worker 3 fails in ReAct, the loop has to reason out of the error mid-stream. In ReWOO, worker 3 returns an error string; the solver sees it in context with the original plan and can degrade gracefully. Failure localization is per-node, not per-step.

---

### Planner distillation · Planner 蒸馏

论文的第二个结果：因为 planner 看不到观察，你可以在一个 175B teacher 的 planner 输出上微调一个 7B 模型。小模型负责规划；推理时不再需要大模型。这如今已是标准做法——许多 2026 年的生产智能体用小 planner 配大执行器，或者反过来。

> The paper's second result: because the planner does not see observations, you can fine-tune a 7B model on planner outputs from a 175B teacher. The small model handles planning; the big model is not needed at inference. This is now standard — many 2026 production agents use a small planner and a big executor or vice-versa.

---

### Plan-and-Execute (2023)

LangChain 团队 2023 年 8 月的文章把 ReWOO 泛化成一个模式名：Plan-and-Execute。前置 planner 输出一份步骤列表，executor 逐步执行，一个可选的 replanner 可以在观察结果之后进行修订。它比 ReWOO 更接近 ReAct（replanner 把观察带回了规划），但保留了 token 节省。

> The LangChain team's August 2023 post generalized ReWOO into a pattern name: Plan-and-Execute. Up-front planner emits a step list, executor runs each step, an optional replanner can revise after observing results. This is closer to ReAct than ReWOO (the replanner brings observations back into planning) but preserves the token savings.

---

### Plan-and-Act (Erdogan et al., arXiv:2503.09572, ICML 2025)

Plan-and-Act 把这个模式扩展到长程网页与移动智能体。关键贡献是合成计划数据：一个带标注的轨迹生成器产出计划显式存在的训练数据。用它微调出的 planner 模型能在 WebArena 类任务上稳定跑过 30–50 步——单条 ReAct 轨迹在那里会失去连贯性。

> Plan-and-Act scales the pattern to long-horizon web and mobile agents. The key contribution is synthetic plan data: a labeled trajectory generator produces training data where the plan is explicit. Used to fine-tune planner models that keep working past 30–50 steps on WebArena-like tasks where a single ReAct trajectory loses coherence.

---

### When to pick which · 怎么选

| 模式 | 何时用 |
|---------|------|
| ReAct | 短任务、环境未知、需要反应式异常处理 |
| ReWOO | 工具已知的结构化任务、对 token 敏感、证据可并行 |
| Plan-and-Execute | 类似 ReWOO，但允许部分执行后的重规划 |
| Plan-and-Act | 长程（>30 步）、web / 移动端 / computer-use |
| Tree of Thoughts | 搜索值得付出代价时（第 4 课） |

Anthropic 2024 年 12 月的指南：从最简单的开始。如果任务是一次工具调用加一段总结，不要造 ReWOO。如果任务是一个 40 步的研究作业，不要只用 ReAct。

> | Pattern | When |
> |---------|------|
> | ReAct | Short tasks, unknown environment, need reactive exception handling |
> | ReWOO | Structured tasks with known tools, token-sensitive, parallelizable evidence |
> | Plan-and-Execute | Like ReWOO but with replanning after partial execution |
> | Plan-and-Act | Long-horizon (>30 steps), web/mobile/computer-use |
> | Tree of Thoughts | Search is worth paying for (Lesson 04) |
>
> Anthropic's Dec 2024 guidance: start with the simplest. If the task is one tool call plus a summary, do not build ReWOO. If the task is a 40-step research assignment, do not do ReAct alone.

```figure
rewoo-plan
```

---

## Build It · 动手造

`code/main.py` 实现了一个玩具 ReWOO：

- `Planner` —— 一个脚本化策略，从提示词产出计划 DAG。
- `Worker` —— 通过注册表分发每个节点的工具调用。
- `Solver` —— 脚本化组合，读取证据并产出最终答案。
- 依赖解析 —— 形如 `#E1` 的引用在分发时被替换成更早的 worker 输出。

这个 demo 回答「法国首都的人口，四舍五入到百万是多少？」，用的是两步计划：(1) 查首都，(2) 查人口，然后求解。

跑起来：

```
python3 code/main.py
```

轨迹先展示完整计划，然后是 worker 结果，最后是 solver 组合。把 token 计数（我们打印一个粗略的字符数）与 ReAct 式交织运行对比——在这类结构化任务上 ReWOO 赢。

> `code/main.py` implements a toy ReWOO: `Planner` — a scripted policy that emits a plan DAG from a prompt; `Worker` — dispatches each node's tool call via the registry; `Solver` — scripted composition that reads evidence and produces a final answer; dependency resolution — references like `#E1` are substituted with earlier worker outputs. ... The trace shows the full plan first, then worker results, then solver composition. Compare the token count (we print a rough character count) to a ReAct-style interleaved run — ReWOO wins on this kind of structured task.

---

## Use It · 实战用法

LangGraph 把 Plan-and-Execute 作为配方发布（ReAct 用 `create_react_agent`，plan-execute 用自定义图）。CrewAI 的 Flows 直接编码了这个模式：你预先定义任务，Flow DAG 负责执行。Plan-and-Act 的合成数据方法仍主要停留在研究阶段；其运行时模式（显式计划 DAG）通过 LangGraph 和 CrewAI Flows 进入生产。

> LangGraph ships Plan-and-Execute as a recipe (`create_react_agent` for ReAct, custom graphs for plan-execute). CrewAI's Flows encode the pattern directly: you define tasks up front and the Flow DAG executes them. Plan-and-Act's synthetic data approach is still mostly research; the runtime pattern (explicit plan DAG) ships in production through LangGraph and CrewAI Flows.

---

## Ship It · 交付

`outputs/skill-rewoo-planner.md` 在给定工具目录的前提下，从用户请求生成一份 ReWOO 计划 DAG。它在交给执行器之前校验计划（无环、每个引用可解析、每个工具存在）。

> `outputs/skill-rewoo-planner.md` generates a ReWOO plan DAG from a user request, given a tool catalog. It validates the plan (acyclic, every reference resolved, every tool exists) before handing off to an executor.

---

## Exercises · 练习

1. 为相互独立的计划节点实现并行 worker 执行。在一个有 2 个并行组的 6 节点 DAG 上，这能换来什么？
2. 加一个在任何 worker 返回错误时触发的 replanner 节点。让 ReWOO 变成 Plan-and-Execute 的最小改动是什么？
3. 把 `Planner` 换成小模型（7B 量级），`Solver` 仍用前沿模型。对比端到端质量——这种拆分在哪里失效？
4. 读 ReWOO 论文第 4 节关于 planner 蒸馏的内容。在概念上复现 175B → 7B 的结果：你需要什么训练数据，怎么给计划质量打分？
5. 把玩具移植成 Plan-and-Act 的轨迹形状：计划是序列而不是 DAG。哪些权衡随之改变？

> 1. Parallelize worker execution for independent plan nodes. What does it buy you on a 6-node DAG with 2 parallel groups?
> 2. Add a replanner node that fires if any worker returns an error. What is the smallest change to ReWOO that makes it Plan-and-Execute?
> 3. Replace `Planner` with a small model (7B class) and keep `Solver` on a frontier model. Compare end-to-end quality — where does the split fail?
> 4. Read Section 4 of the ReWOO paper on planner distillation. Reproduce the 175B -> 7B result conceptually: what training data do you need, and how do you score plan quality?
> 5. Port the toy to Plan-and-Act's trajectory shape: plan is a sequence, not a DAG. What tradeoffs change?

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| ReWOO | 「Reasoning without observations（无观察推理）」 | 先规划，再并行取证据，最后求解——规划提示词里不含任何观察 |
| Plan-and-Execute | 「LangChain 的 plan-execute 模式」 | ReWOO 加一个执行后可选的 replanner 节点 |
| Plan-and-Act | 「扩展版 plan-execute」 | 显式的 planner/executor 拆分，外加面向长程任务的合成计划训练数据 |
| Evidence reference | 「#E1, #E2, ...」 | 计划节点的占位符，在分发时被替换成先前的 worker 输出 |
| Planner distillation | 「小 planner，大执行器」 | 在大 teacher 的 planner 轨迹上微调一个小模型 |
| Token efficiency | 「更少的往返」 | 论文中 HotpotQA 上比 ReAct 少 5 倍 token |
| DAG executor | 「拓扑分发器」 | 按依赖顺序运行计划节点；每层内可并行 |

> | Term | What people say | What it actually means |
> |------|----------------|------------------------|
> | ReWOO | "Reasoning without observations" | Plan, then fetch evidence in parallel, then solve — no observations in the planning prompt |
> | Plan-and-Execute | "LangChain's plan-execute pattern" | ReWOO with an optional replanner node after execution |
> | Plan-and-Act | "Scaled plan-execute" | Explicit planner/executor split with synthetic plan training data for long-horizon tasks |
> | Evidence reference | "#E1, #E2, ..." | Plan-node placeholder substituted with prior worker output at dispatch time |
> | Planner distillation | "Small planner, big executor" | Fine-tune a small model on planner traces from a large teacher |
> | Token efficiency | "Fewer round trips" | 5x fewer tokens on HotpotQA vs ReAct in the paper |
> | DAG executor | "Topological dispatcher" | Runs plan nodes in dependency order; parallel at each level |

---

## Further Reading · 延伸阅读

- [Xu et al., ReWOO: Decoupling Reasoning from Observations (arXiv:2305.18323)](https://arxiv.org/abs/2305.18323) —— 规范论文
- [Erdogan et al., Plan-and-Act (arXiv:2503.09572)](https://arxiv.org/abs/2503.09572) —— 带合成计划的扩展版 planner-executor
- [LangGraph Plan-and-Execute tutorial](https://docs.langchain.com/oss/python/langgraph/overview) —— 框架配方
- [Anthropic, Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) —— 选能用的最简单模式

> - [Xu et al., ReWOO: Decoupling Reasoning from Observations (arXiv:2305.18323)](https://arxiv.org/abs/2305.18323) — the canonical paper
> - [Erdogan et al., Plan-and-Act (arXiv:2503.09572)](https://arxiv.org/abs/2503.09572) — scaled planner-executor with synthetic plans
> - [LangGraph Plan-and-Execute tutorial](https://docs.langchain.com/oss/python/langgraph/overview) — the framework recipe
> - [Anthropic, Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) — pick the simplest pattern that works
