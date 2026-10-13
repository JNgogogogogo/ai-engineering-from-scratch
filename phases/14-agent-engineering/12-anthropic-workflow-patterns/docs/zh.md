# Anthropic's Workflow Patterns: Simple Over Complex · Anthropic 工作流模式：简单优先

> Schluntz and Zhang (Anthropic, Dec 2024) distinguish workflows (predefined paths) from agents (dynamic tool-use). Five workflow patterns cover most cases. Start with direct API calls. Add agents only when steps cannot be predicted.

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 说出 Anthropic 的五种工作流模式：prompt 链（prompt chaining）、路由（routing）、并行化（parallelization）、编排者-工作者（orchestrator-workers）、评估者-优化者（evaluator-optimizer）
- 解释 agent 与工作流的区分，以及各自的工程成本
- 判断什么时候该选工作流而不是 agent（以及反过来）
- 面对一个脚本化 LLM，用 stdlib 实现全部五种模式

> Name Anthropic's five workflow patterns: prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer.
> Explain the agent-vs-workflow distinction and the engineering cost of each.
> Identify when to pick a workflow over an agent (and vice versa).
> Implement all five patterns in stdlib against a scripted LLM.

## The Problem · 问题在哪

很多团队为一个其实只需要一次函数调用的问题上马了多 agent 框架。代价是真实的：框架加上一层又一层的包装，遮住 prompt、藏起控制流、招来过早的复杂性。Schluntz 和 Zhang 2024 年 12 月的那篇文章是被引用最多的行业反弹：从简单开始，只有当复杂性挣得回自己的成本时才加。

> Teams reach for multi-agent frameworks for problems that want a single function call. The cost is real: frameworks add layers that obscure prompts, hide control flow, and invite premature complexity. Schluntz and Zhang's Dec 2024 post is the most-cited industry pushback: start simple, add complexity only when it earns its cost.

## The Concept · 概念

### Workflows vs agents · 工作流对 agent

- **工作流（Workflow）。** LLM 和工具通过预定义的代码路径编排。图归工程师所有。
- **Agent。** LLM 动态指挥自己的工具、走自己的步子。图归模型所有。

两者各有位置。工作流更便宜、更快、更好调试。agent 解锁开放式问题，但让失败模式更难推理。

> - **Workflow.** LLMs and tools orchestrated through predefined code paths. Engineers own the graph.
> - **Agent.** LLMs dynamically direct their own tools and take their own steps. The model owns the graph.
> Both have their place. Workflows are cheaper, faster, and easier to debug. Agents unlock open-ended problems but make failure modes harder to reason about.

### The augmented LLM · 增强型 LLM

全部五种模式的地基：一个接好三种能力的 LLM——搜索（检索）、工具（动作）、记忆（持久化）。任何 API 调用都可以用上这些。

> Foundation for all five patterns: one LLM with three capabilities wired in — search (retrieval), tools (actions), memory (persistence). Any API call can use these.

### The five patterns · 五种模式

1. **Prompt 链（prompt chaining）。** 调用 1 的输出是调用 2 的输入。适用于任务有干净的线性分解时。步骤之间可以放可选的程序化关卡（gate）。

2. **路由（routing）。** 一个分类 LLM 挑选下游调用哪个 LLM 或工具。适用于类别不同的输入需要不同处理时（一线支持 vs 退款 vs bug vs 销售）。

3. **并行化（parallelization）。** 并发跑 N 个 LLM 调用，聚合结果。两种形态：切分（sectioning，处理不同的块）和投票（voting，同一个 prompt 跑 N 次，多数决/综合）。

4. **编排者-工作者（orchestrator-workers）。** 一个编排 LLM 动态决定要跑哪些工作者（也是 LLM），并综合它们的输出。类似 agent 回路，但编排者不会无限循环。

5. **评估者-优化者（evaluator-optimizer）。** 一个 LLM 提出答案，另一个 LLM 评估它。迭代，直到评估者放行。这就是 Self-Refine（Lesson 05）的推广版。

> **Prompt chaining.** Output of call 1 is input to call 2. Use when a task has a clean linear decomposition. Optional programmatic gates between steps.
> **Routing.** A classifier LLM picks which downstream LLM or tool to invoke. Use when categorically different inputs need different handling (tier-1 support vs refund vs bug vs sales).
> **Parallelization.** Run N LLM calls concurrently, aggregate results. Two shapes: sectioning (different chunks) and voting (same prompt, N runs, majority/synthesis).
> **Orchestrator-workers.** An orchestrator LLM dynamically decides which workers (also LLMs) to run and synthesizes their output. Similar to agent loops but the orchestrator does not loop indefinitely.
> **Evaluator-optimizer.** One LLM proposes an answer, another LLM evaluates it. Iterate until the evaluator passes. This is Self-Refine (Lesson 05) generalized.

### Where workflows beat agents · 工作流赢过 agent 的地方

- **可预测的任务。** 如果你能枚举出步骤，你就该枚举。
- **有成本上限的任务。** 工作流的步数有界；agent 会打转。
- **受合规约束的任务。** 审计员想读图，而不是从运行轨迹里推断图。

> **Predictable tasks.** If you can enumerate the steps, you should.
> **Cost-bound tasks.** Workflows have bounded step counts; agents can spiral.
> **Compliance-bound tasks.** Auditors want to read the graph, not infer it from trajectories.

### Where agents beat workflows · agent 赢过工作流的地方

- **开放式研究。** 下一步取决于上一步返回了什么。
- **长度不定的任务。** 几分钟到几小时的工作，步数未知。
- **全新领域。** 你还不知道正确的工作流长什么样——先探索，再固化。

> **Open-ended research.** When the next step depends on what the last step returned.
> **Variable-length tasks.** Minutes to hours of work where step count is unknown.
> **Novel domains.** When you don't yet know the right workflow — exploration first, codify later.

### The context-engineering companion · 姊妹篇：上下文工程

「Effective context engineering for AI agents」（Anthropic 2025）把相邻的这门学科形式化了：200k 窗口是预算，不是容器。装什么、什么时候压缩、什么时候放任上下文生长。细节在本课程 Phase 14 讲上下文压缩的那一课展开（重编号之前的 Phase 14 lesson 06）。

> "Effective context engineering for AI agents" (Anthropic 2025) formalizes the adjacent discipline: the 200k window is a budget, not a container. What to include, when to compact, when to let context grow. Covered in detail in Phase 14 lesson on context compression (Phase 14 earlier lesson 06 in this curriculum before the renumber).

```figure
workflow-chain
```

## Build It · 动手造

`code/main.py` 面对一个 `ScriptedLLM` 实现全部五种工作流模式：

- `prompt_chain(input, steps)` — 顺序执行。
- `route(input, classifier, handlers)` — 分类 + 分发。
- `parallel_vote(prompt, n, aggregator)` — N 次运行，聚合。
- `orchestrator_workers(task, workers)` — 编排者挑选工作者。
- `evaluator_optimizer(task, proposer, evaluator, max_iter)` — 循环直到通过。

运行：

```
python3 code/main.py
```

每个模式打印自己的轨迹。每个模式的代码量约 10-15 行；而一个框架的成本是按千行计的。

> Each pattern prints its trace. Total lines of code per pattern is ~10-15; the cost of a framework is measured in thousands.

## Use It · 实战用法

- 大多数任务，直接调 API。
- 只有当模式真的需要持久状态（LangGraph）、actor 模型并发（AutoGen v0.4）或角色模板化（CrewAI）时，才上框架。
- 想要 Claude Code 这种 harness 形状又不想自己重建时，用 Claude Agent SDK。

> Direct API calls for most tasks.
> Framework only when the pattern genuinely needs durable state (LangGraph), actor-model concurrency (AutoGen v0.4), or role templating (CrewAI).
> Reach for the Claude Agent SDK when you want the Claude Code harness shape without rebuilding it.

## Ship It · 交付

`outputs/skill-workflow-picker.md` 为给定的任务描述挑出正确的模式，附上决策理由，以及工作流不够用时升级到 agent 的重构路径。

> `outputs/skill-workflow-picker.md` picks the right pattern for a given task description, including the decision rationale and the refactor path to an agent if workflows fall short.

## Exercises · 练习

1. 实现带置信度阈值的路由。低于阈值 -> 升级给人工。一线支持场景下阈值会落在哪里？
2. 给 `parallel_vote` 加超时。当一个调用挂起时会发生什么？缺票时怎么聚合？
3. 把 `evaluator_optimizer` 变成 bandit：跨迭代保留 top-2 输出，免得晚出现的好结果被晚出现的坏结果覆盖。
4. 把 prompt 链和路由组合起来：路由器从三条链里挑一条。测一测 token 成本，对比单条大 prompt 的方案。
5. 挑一个你的生产功能。画出工作流图。数一数步数。这里换成 agent 真的会更好吗？

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| Workflow（工作流） | 「预定义流程」 | 工程师拥有的 LLM 与工具调用图 |
| Agent | 「自主 AI」 | 模型拥有的图；动态指挥工具 |
| Augmented LLM（增强型 LLM） | 「带工具的 LLM」 | LLM + 搜索 + 工具 + 记忆；原子单元 |
| Prompt chaining（prompt 链） | 「顺序调用」 | 调用 N 的输出是调用 N+1 的输入 |
| Routing（路由） | 「分类分发」 | 挑选哪条链/哪个模型来处理输入 |
| Parallelization（并行化） | 「扇出」 | N 个并发调用；按切分或投票聚合 |
| Orchestrator-workers | 「调度 agent」 | 编排 LLM 动态挑选专家 LLM |
| Evaluator-optimizer | 「提议者 + 裁判」 | 迭代直到评估者通过；Self-Refine 的推广 |

## Further Reading · 延伸阅读

- [Anthropic, Building Effective Agents (Dec 2024)](https://www.anthropic.com/research/building-effective-agents) —— 五种工作流模式
- [Anthropic, Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) —— 姊妹学科
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) —— 有状态图什么时候挣得回成本
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) —— 产品化的编排者-工作者模式
