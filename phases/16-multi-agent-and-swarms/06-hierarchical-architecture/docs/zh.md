# Hierarchical Architecture and Its Failure Mode · 分层架构及其失败模式

> 分层架构就是套娃的监督者模式：经理智能体之下是子经理，子经理之下是 worker。CrewAI 的 `Process.hierarchical` 是教科书式实现：一个 `manager_llm` 动态分派任务并校验输出。LangGraph 里的等价物是 `create_supervisor(create_supervisor(...))`。当任务本身就是一张真实的组织架构图时，这是自然的选择。但它也是最容易塌缩成管理死循环的模式——经理智能体分派工作不当、误读子输出，或者无法达成共识。顺序流水线常常反而更好。

> Hierarchical is supervisor nested. Manager agents over sub-managers over workers. CrewAI `Process.hierarchical` is the textbook version: a `manager_llm` dynamically delegates tasks and validates outputs. The LangGraph equivalent is `create_supervisor(create_supervisor(...))`. It is the natural pattern when the task is a real org chart. It is also the pattern most likely to collapse into managerial looping — manager agents assign work poorly, misinterpret sub-outputs, or fail to reach consensus. Sequential often beats it.

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 16 · 05 (Supervisor Pattern)
**Time:** ~60 minutes

---

## Problem · 问题

一旦监督者模式想通了，自然的下一步就是问：「如果 worker 本身也是监督者呢？」团队下面有子团队；公司里有部门的部门。分层架构正是这种结构的镜像。

问题在于：LLM 经理和人类经理不是一回事。人类经理对「自己的下属知道什么」有稳定的先验。LLM 经理每一轮都根据上下文里的内容重新推理整个组织。上下文里一点微小的漂移，整棵树就会错误地分配工作。

> Once the supervisor pattern clicks, the natural next step is "what if the workers are themselves supervisors?" Teams have sub-teams; companies have departments of departments. Hierarchical architectures mirror that. ... The issue: LLM managers are not the same as human managers. A human manager has stable priors about what their reports know. An LLM manager re-reasons the org every turn from whatever is in its context. Tiny drift in that context, and the whole tree misallocates work.

---

## Concept · 概念

### The shape · 形态

```
                 Manager
                 ┌─────┐
                 └──┬──┘
           ┌────────┴────────┐
           ▼                 ▼
       Sub-Mgr A         Sub-Mgr B
       ┌─────┐           ┌─────┐
       └──┬──┘           └──┬──┘
         ┌┴──┬──┐          ┌┴──┐
         ▼   ▼  ▼          ▼   ▼
       W1  W2  W3         W4  W5
```

每个内部节点都负责规划、分派和综合。只有叶子节点真正干活。

> Every internal node plans, delegates, and synthesizes. Only leaves do work.

---

### Where it shines · 什么时候闪光

- **清晰的组织映射。** 如果真实任务本来就是按部门划分的（「法务审这份文档，财务审这份文档，工程审这份文档，然后给高管汇总」），层级结构是显式的。
- **局部摘要。** 每个子经理先综合自己团队的输出，顶层经理才看得到。顶层经理看到的是三份子经理摘要，而不是十五份 worker 输出。

> **Clear org mapping.** If the real task is departmental ("legal review the doc, finance review the doc, engineering review the doc, then summarize for exec"), the hierarchy is explicit. ... **Local summarization.** Each sub-manager synthesizes its team's output before the top manager sees it. Top manager sees three sub-manager summaries, not fifteen worker outputs.

---

### Where it breaks · 什么地方会断

2026 年的事后复盘反复发现的三种失败模式：

1. **任务分派错误。** 经理读取目标，幻觉出一个分解，把任务分派给错误的子经理。因为子经理会乖乖地干被指派的活，这个错误要到顶层综合时才暴露——离人类本可以抓住它的地方隔了一层。
2. **输出误读。** 子经理返回「无法验证断言 X」。顶层经理摘要成「断言 X 未确认」。含义在每一层都在漂移。
3. **共识死循环。** 两个子经理意见不合；顶层经理让他们调和；他们把任务重新往下分派；worker 重跑；子经理返回略有不同的答案；循环。CrewAI 的 `Process.hierarchical` 用步数上限防范这一点，但这个上限本身现在成了一个超参数。

> Three failure modes the 2026 post-mortems keep finding: ... **Task assignment error.** The manager reads the goal, hallucinates a decomposition, and delegates to the wrong sub-manager. ... **Output misinterpretation.** Sub-manager returns "unable to verify claim X." Top manager summarizes as "claim X not confirmed." Meaning drifts at every level. ... **Consensus loops.** Two sub-managers disagree; top manager asks them to reconcile; they re-delegate down; workers re-run; sub-managers return slightly different answers; loop. CrewAI's `Process.hierarchical` guards against this with step limits, but the limit itself is now a hyperparameter.

---

### The deciding question · 决定性问题

顺序（线性流水线）vs 分层：你的任务是真的拥有相互独立的子团队，还是一个假装成树的线性流程？如果是后者，用顺序。如果是前者，用分层，但要把显式的调和规则纳入预算。

> Sequential (linear pipeline) vs hierarchical: does your task actually have independent sub-teams, or is it one linear flow pretending to be a tree? If the latter, use sequential. If the former, use hierarchical but budget explicit reconciliation rules.

---

### Role-framework implementation · 角色型框架实现

CrewAI 的 `Process.hierarchical` 在专家小组（crew）之上接一个经理 LLM。经理：

- 接收顶层任务，
- 把子任务分派给各个 crew，
- 评估 crew 的输出，
- 决定接受、重新分派还是迭代。

文档：https://docs.crewai.com/en/introduction（在 Core Concepts 下找「Hierarchical Process」）。

> CrewAI's `Process.hierarchical` wires a manager LLM over specialist crews. The manager: receives the top-level task, assigns subtasks to crews, evaluates crew outputs, decides whether to accept, re-delegate, or iterate.

---

### Graph-framework implementation · 图框架实现

LangGraph 用嵌套的 `create_supervisor` 调用。内层监督者有自己的图；外层监督者把内层图当作一个不透明的节点。这在调试上比 CrewAI 更干净（你可以单独单步调试每个图），但更难表达树的动态重构。

参考：https://reference.langchain.com/python/langgraph-supervisor。

```figure
swarm-hierarchy-token
```

> LangGraph uses nested `create_supervisor` calls. The inner supervisor has its own graph; the outer supervisor treats the inner graph as an opaque node. This is cleaner than CrewAI for debugging (you can step through each graph separately) but harder to express dynamic reshaping of the tree.

---

## Build It · 动手造

`code/main.py` 跑一个 3 层层级：

- 顶层经理：把任务拆成「工程」和「法务」两个分支，
- 工程子经理：拆成「前端」和「后端」两个 worker，
- 法务子经理：一个 worker。

演示把顺利路径（所有人达成一致）与一条 **扰动路径** 对比：顶层经理的分解把「法务」错标成「财务」，然后看着错误层层级联——子经理乖乖地干了财务的活，顶层综合器汇报财务结论，最初的法律问题无人回答。

Run:

```
python3 code/main.py
```

输出并排展示两条路径，清楚对照「被问的是什么」vs「交付的是什么」。

> `code/main.py` runs a 3-level hierarchy: top manager splits a task into "engineering" and "legal" branches, engineering sub-manager splits into "frontend" and "backend" workers, legal sub-manager has one worker. ... Demo contrasts happy path (everyone agrees) against a **perturbed path** where the top manager's decomposition mislabels "legal" as "finance" and watches the error cascade. ... Output shows both paths with a clear side-by-side of "what was asked" vs "what was delivered."

---

## Use It · 实战用法

`outputs/skill-hierarchy-fitness.md` 评估一个给定任务应该用分层、顺序还是扁平监督者。输入：任务描述、组织结构、调和预算。输出：模式推荐，以及要防范的具体失败模式。

> `outputs/skill-hierarchy-fitness.md` evaluates whether a given task should use hierarchical, sequential, or flat supervisor. Inputs: task description, org structure, reconciliation budget. Output: pattern recommendation with the specific failure modes to guard against.

---

## Ship It · 交付

如果你要上线分层架构：

- **树的深度封顶在 2。** 三层就已经把大部分错误藏到可观测性之外了。
- **显式的调和预算。** 设定顶层经理必须拍板之前的最大轮数。通常是 2。
- **每次综合都带溯源。** 每个节点的摘要必须注明它由哪些叶子输出产生。
- **对分解漂移告警。** 每一步都记录经理的分解；与用户查询做 diff。如果分解不再覆盖查询，触发告警。

> If you ship hierarchical: ... **Cap tree depth at 2.** Three levels already hides most errors from observability. ... **Explicit reconciliation budget.** Set max rounds before the top manager must commit. Usually 2. ... **Provenance on every synthesis.** Each node's summary must cite which leaf outputs produced it. ... **Alert on decomposition drift.** Log the manager's decomposition per step; diff against the user query. If the decomposition no longer covers the query, fire an alert.

---

## Exercises · 练习

1. 跑 `code/main.py` 并比较顺利路径与扰动路径。要经过多少层经理交接，顶层输出才会完全偏离用户的问题？
2. 加第三层（顶层 → 子 → 子子 → worker）。测量随着深度增长，扰动路径自我纠正与完全偏离的频率各是多少。
3. 在每个子经理处实现一个「金丝雀」worker，它总是被原封不动地问原始用户问题。用金丝雀的答案检测分解漂移。当金丝雀与综合答案不一致时，经理应该如何反应？
4. 读 CrewAI 的 `Process.hierarchical` 文档。找出 CrewAI 应用的一条具体护栏（步数上限、manager_llm 约束），并说明它针对哪种失败模式。
5. 比较嵌套的 LangGraph 监督者与 CrewAI 分层。哪种让调和循环更容易被发现？

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Hierarchical | 「组织架构图模式」 | 监督者之上再有监督者；只有叶子节点干活。 |
| Manager LLM | 「老板」 | 在内部节点做分解、分派和校验的 LLM。 |
| Decomposition drift | 「老板跑题了」 | 顶层经理的拆分不再覆盖原始问题。 |
| Reconciliation loop | 「开不完的会」 | 子经理意见不合；顶层重新分派；worker 重跑；循环直到预算耗尽。 |
| Depth-2 ceiling | 「别深过 2 层」 | 经验护栏：3 层以上可观测性就崩塌。 |
| Canary question | 「每层都有标准答案」 | 一个总被原封不动地问原始查询的 worker，用来检测漂移。 |
| Provenance chain | 「谁说了什么」 | 从每次综合回溯到产生它的叶子输出的轨迹。 |

---

## Further Reading · 延伸阅读

- [CrewAI introduction — Process.hierarchical](https://docs.crewai.com/en/introduction) —— 带经理 LLM 的教科书式分层架构
- [LangGraph supervisor reference](https://reference.langchain.com/python/langgraph-supervisor) —— 通过 `create_supervisor` 嵌套监督者
- [Anthropic engineering — Research system](https://www.anthropic.com/engineering/multi-agent-research-system) —— Anthropic 为什么刻意选扁平监督者而不是分层
- [Cemri et al. — Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) —— MAST 分类法；协调失败一节记录了分解漂移
