# 生成式 agent 与涌现模拟（Generative Agents and Emergent Simulation）

> Park et al. 2023（UIST '23, arXiv:2304.03442）用三部分架构填充了 **Smallville**——一个 25 个 agent 的沙盒：**记忆流**（memory stream，自然语言日志）、**反思**（reflection，agent 对自己的记忆流生成的更高层综合）和**计划**（plan，先日级别行为，再子计划）。里程碑式的结果是情人节派对的涌现：一个被植入「想办一场情人节派对」的 agent，在没有进一步脚本的情况下，让邀请在人群中扩散、协调了日期，派对真的发生了——而其他 24 个 agent 起初对此一无所知。消融实验表明三个组件对可信度缺一不可。论文记录的失败是空间规范错误（走进打烊的店铺、共用单人卫生间）。这是 2026 年 agent 模拟与多 agent 社会评估的参照架构。

> Park et al. 2023 (UIST '23, arXiv:2304.03442) populated **Smallville**, a sandbox of 25 agents, with a three-part architecture: **memory stream** (natural-language log), **reflection** (higher-level syntheses the agent generates about its own stream), and **plan** (day-level behavior, then sub-plans). The landmark result was the Valentine's Day party emergence: one agent seeded with "wants to throw a Valentine's Day party," without further scripting, produced invitations spread through the population, coordinated dates, and the party happened — from 24 agents who started with no knowledge of it. Ablations show all three components are required for believability. The documented failures are spatial-norm errors (entering closed stores, sharing single-person bathrooms). This is the reference architecture for agent simulations and multi-agent social evaluation in 2026.

**Type:** Learn + Build
**Languages:** Python（stdlib）
**Prerequisites:** Phase 16 · 04（Primitive Model）、Phase 16 · 13（Shared Memory）
**Time:** ~75 分钟

## Problem · 问题

大多数多 agent 系统是编排严密的团队：planner 规划、coder 写码、reviewer 审查。这对定义良好的任务有效。但它捕捉不到当 agent 拥有记忆、优先级和开放世界时涌现出的、无脚本的行为。研究、社会模拟，以及越来越多的游戏 AI，需要的是第二种。

Smallville 架构就是它的标杆。在 Park 2023 之前，最好的 agent 模拟也只是浅层脚本跟随者；在那之后，这个模式成了开放世界中生成式 agent 的默认选择。如果你在 2026 年构建一个 agent 模拟，你要么在用 Smallville 的三个组件，要么在显式论证为什么不用。

> Most multi-agent systems are tightly-scripted teams: planner plans, coder codes, reviewer reviews. That works for well-defined tasks. It does not capture the emergent, unscripted behavior that arises when agents have memory, priorities, and an open world. Research, society simulation, and increasingly game AI need this second kind.
> The Smallville architecture is the benchmark for it. Until Park 2023, the best agent simulations were shallow script-followers; after it, the pattern is the default for generative agents in open worlds. If you build an agent simulation in 2026, you are either using Smallville's three components or explicitly justifying why you are not.

## Concept · 概念

### The three components · 三个组件

**记忆流（Memory stream）。** 一个只追加的日志，记录观察、行动、反思和计划。每条有时间戳、类型、描述（自然语言）和派生的元数据：**近因性（recency）**、**重要性（importance）**（由 agent 自评 1-10 分）、**相关性（relevance）**（与当前查询的余弦相似度）。

```
[2026-02-14 09:12:03] observation: Isabella Rodriguez asked me if I like jazz
[2026-02-14 09:14:22] reflection:   I enjoy long conversations about music
[2026-02-14 10:05:00] plan:         Attend Isabella's Valentine's Day party tonight
```

记忆检索把三个分数组合起来：`score = w_recency * e^(-decay * age) + w_importance * importance + w_relevance * cos_sim`。得分前 k 名的条目进入当前提示词。

> **Memory stream.** An append-only log of observations, actions, reflections, and plans. Each entry has a timestamp, a type, a description (natural language), and derived metadata: **recency**, **importance** (self-rated 1-10 by the agent), and **relevance** (cosine similarity to current query).
> Memory retrieval combines the three scores: `score = w_recency * e^(-decay * age) + w_importance * importance + w_relevance * cos_sim`. Top-k entries enter the current prompt.

**反思（Reflection）。** 周期性地（每 N 条记忆，或在重要事件上），agent 从近期记忆生成更高阶的综合。反思条目回到记忆流中，可以像任何其他记忆一样被检索。agent 就是这样建立起「理解」的——这是该架构对长期信念的等价物。

**计划（Plan）。** 自顶向下的分解。先是一份粗线条的日级计划（「去上班，和 Klaus 吃晚饭」）。然后是小时级计划。再是行动级计划。计划可修订：当观察与计划矛盾时，agent 重新规划受影响的部分。

> **Reflection.** Periodically (every N memories or on important events), the agent generates higher-order syntheses from recent memories. Reflection entries go back into the stream and are retrievable like any other memory. This is how agents build "understandings" — the architecture's equivalent of long-term beliefs.
> **Plan.** Top-down decomposition. First, a day-level plan in broad strokes ("go to work, have dinner with Klaus"). Then hour-level plans. Then action-level plans. Plans are revisable: when an observation contradicts a plan, the agent replans the affected segment.

### Why all three matter (ablation) · 为什么三者缺一不可（消融）

Park et al. 做了消融实验，分别去掉观察、反思和计划。每个消融都伤害可信度：

- 没有**观察**，agent 缺失上下文，按过时的信念行动。
- 没有**反思**，agent 无法形成更高阶的信念；互动停留在浅层。
- 没有**计划**，行为变成被动响应的噪声；目标消散。

人类评分者给出的可信度分数在三者齐备时最高；去掉任何一个都会产生可测量的退化。

> Park et al. ran ablations dropping each of observation, reflection, and plan. Each ablation hurts believability:
> - Without **observation** the agent misses context and acts on stale beliefs.
> - Without **reflection** the agent cannot form higher-order beliefs; interactions stay shallow.
> - Without **plan** behavior becomes reactive noise; goals dissipate.
> Believability scores from human raters are highest with all three; dropping any one produces a measurable regression.

### The Valentine's Day emergence · 情人节涌现

一个 agent，Isabella Rodriguez，被植入目标「想在 2 月 14 日下午 5 点在 Hobbs Cafe 办一场情人节派对」。其余 24 个 agent 没有得到任何这样的植入。在模拟的几天里：

1. Isabella 的计划包含邀请别人。
2. 每份邀请成为邻居记忆流里的一条观察。
3. 邻居的反思生成信念：「Isabella 要办派对。」
4. 邻居的计划纳入「2 月 14 日参加派对」。
5. 邻居告诉其他邻居。邀请在没有中央协调的情况下扩散。
6. 2 月 14 日下午 5 点，若干 agent 在 Hobbs Cafe 汇合。

这是技术意义上的涌现（emergence）：系统级行为（一场派对）从局部互动（两两邀请 + 各自规划）中产生，没有中央编排器。

> One agent, Isabella Rodriguez, is seeded with the goal "wants to throw a Valentine's Day party at Hobbs Cafe on Feb 14 at 5pm." The 24 other agents receive no such seed. Over simulated days:
> 1. Isabella's plan includes inviting people.
> 2. Each invitation becomes an observation in a neighbor's memory stream.
> 3. That neighbor's reflection generates beliefs: "Isabella is throwing a party."
> 4. The neighbor's plan incorporates "attend party on Feb 14."
> 5. Neighbors tell other neighbors. The invitation spreads without central coordination.
> 6. At 5pm on Feb 14, several agents converge at Hobbs Cafe.
> This is emergence in the technical sense: system-level behavior (a party) arose from local interactions (bilateral invitations + individual planning) without a central orchestrator.

### The documented failure modes · 已记录的失效模式

Park et al. 明确记录了：

- **空间规范错误。** Agent 走进打烊的店铺。Agent 们试图使用同一间单人卫生间。Agent 在不是用来吃饭的房间里吃饭。模型无法仅从环境推断社会-物理规范。
- **内存溢出。** 深度模拟运行导致记忆检索成本增长。实用的补救：周期性的记忆压缩（摘要-剪枝）以及对低重要性条目的衰减。
- **反思幻觉。** 反思可能编造记忆流中不存在的关系。缓解：在反思提示词里包含来源记忆 id，并在检索时校验。

这些是与生产相关的失效模式：任何 2026 年的 agent 模拟都会继承它们。

> Park et al. explicitly document:
> - **Spatial norm errors.** Agents walk into closed stores. Agents try to use the same single-person bathroom. Agents eat in rooms not intended for eating. The model does not infer social-physical norms from the environment alone.
> - **Memory overflow.** Deep simulation runs cause memory-retrieval cost to grow. Practical remedy: periodic memory compaction (summarize-and-prune) and decay on low-importance entries.
> - **Reflection hallucination.** Reflections can invent relationships that do not exist in the memory stream. Mitigation: include source memory ids in reflection prompts and verify at retrieval time.
> These are production-relevant failure modes: any 2026 agent simulation inherits them.

### Three-component implementation rules · 三组件的实现规则

1. **记忆只追加。** 永不原地修改记忆条目。更正就是新条目。
2. **重要性打分要便宜。** 在写入时调用 LLM 打 1-10 的重要性分。缓存这个分数。
3. **检索是排序的，不是过滤的。** 按组合得分取前 k；不要用硬过滤（那会丢上下文）。
4. **反思周期性运行。** 当未处理记忆的重要性之和超过阈值（比如 150）时触发。
5. **计划可修订。** 当新观察与计划矛盾时，只重新生成受影响的部分，而不是整个计划。

> 1. **Memory is append-only.** Never mutate a memory entry. Corrections are new entries.
> 2. **Importance scores are cheap.** Call the LLM to rate importance 1-10 at write time. Cache the score.
> 3. **Retrieval is ranked, not filtered.** Top-k by combined score; do not use hard filters (which lose context).
> 4. **Reflection runs periodically.** Trigger when the sum of importance of unprocessed memories exceeds a threshold (e.g., 150).
> 5. **Plans are revisable.** When a new observation contradicts a plan, regenerate the affected segment only, not the whole plan.

### Generative agents beyond Smallville · Smallville 之外的生成式 agent

2024-2026 年的后续文献扩展了该架构：

- **面向政策 / 市场研究的多 agent 社会模拟。** 类 Smallville 的人群模拟用户对功能的行为反应。比 A/B 测试快；准确性尚有争议。
- **游戏 NPC AI。** 用 Smallville agent 的 RPG 产生涌现的故事线，而不是脚本化的任务。
- **生成式 agent 评估基准。** 指标不再是任务准确率，而是长时间运行下行为的可信度 + 连贯性。

这个架构就是参照。扩展会替换组件（用向量存储做记忆、检索增强的反思、神经符号计划），但保留三部分结构。

> The 2024-2026 follow-up literature extends the architecture:
> - **Multi-agent social simulation for policy / market research.** Smallville-like populations simulate user behavior in response to features. Faster than A/B tests; accuracy is contested.
> - **NPC AI for games.** RPGs with Smallville agents produce emergent storylines instead of scripted quests.
> - **Generative-agent evaluation benchmarks.** Rather than task accuracy, the metric becomes believability + coherence of behavior over long runs.
> The architecture is the reference. Extensions swap components (vector store for memory, retrieval-augmented reflection, neurosymbolic plan) but keep the three-part structure.

### Why this matters for multi-agent engineering · 这对多 agent 工程为什么重要

Smallville 是概念证明：组件对了，多 agent 涌现是廉价的。该架构现已在开源模型上被复现（更小的 LLM 让可信度平滑下降，而不是断崖式下跌）。任何需要**涌现社会行为**的生产系统都使用这个形态。任何需要**严密任务执行**的系统则使用本阶段前面的 supervisor / 角色 / 原语模式。

> Smallville is the proof of concept that multi-agent emergence is cheap when the components are right. The architecture has now been replicated on open-source models (smaller LLMs lose believability gracefully, not sharply). Any production system that needs **emergent social behavior** uses this shape. Any system that needs **tight task execution** uses the supervisor / roles / primitives patterns from earlier in this phase.

```figure
a5-memory-reflection
```

## Build It · 动手造

`code/main.py` 用标准库 Python 实现三个组件，agent 策略为脚本化（没有真 LLM）。演示以微缩形式复现情人节派对涌现：

- `MemoryStream` —— 带近因/重要性/相关性检索的只追加日志。
- `reflect(stream)` —— 对近期高重要性记忆做脚本化反思。
- `plan(agent_state)` —— 基于当前信念的日级与小时级计划。
- 场景：5 个 agent。Agent 1 以「下午 5 点办派对」开场。随着模拟 tick 推进，邀请扩散，agent 们汇合。

运行：

```
python3 code/main.py
```

预期输出：逐 tick 的轨迹。到最后一个 tick，5 个 agent 中至少 3 个的计划里出现派对，并且他们向派对地点汇合。单一的种子在没有编排器的情况下产生了协同到场。

> `code/main.py` implements the three components in stdlib Python with scripted agent policies (no real LLM). The demo reproduces the Valentine's-party emergence in miniature:
> - `MemoryStream` — append-only log with recency/importance/relevance retrieval.
> - `reflect(stream)` — scripted reflection over recent high-importance memories.
> - `plan(agent_state)` — day-level and hour-level plans based on current beliefs.
> - Scenario: 5 agents. Agent 1 starts with "throw party at 5pm." Over simulated ticks, the invitation spreads and agents converge.
> Expected output: tick-by-tick trace. By the final tick, at least 3 of the 5 agents show the party in their plan, and they converge at the party location. The single seed produced the coordinated arrival without any orchestrator.

## Use It · 实战用法

`outputs/skill-simulation-designer.md` 设计一个生成式 agent 模拟：agent 数量、记忆 schema、反思节奏、计划时间跨度，以及评估指标。

> `outputs/skill-simulation-designer.md` designs a generative-agent simulation: number of agents, memory schema, reflection cadence, plan horizon, and evaluation metric.

## Ship It · 交付

生产级模拟的规则：

- **记忆就是数据库。** 上规模就选一个真正的存储（向量数据库、Postgres）。内存里的 stdlib 只属于原型。
- **记录检索轨迹。** 对每个动作，记录驱动它的前 k 条记忆。这是你的调试能力所在。
- **给每个 agent 做 token 预算。** 每个 agent 每 tick 的检索 + 反思 + 规划是 O(k) 次 LLM 调用。N 个 agent × T 个 tick × 每 tick 调用数可以轻松压垮你的预算。
- **周期性压缩记忆。** 对低重要性条目做摘要-剪枝。保留策略是一个设计决策，不是细节。
- **显式检测空间 / 社会规范违例。** 这个架构学不会它们。

> Rules for production simulations:
> - **Memory is the database.** Pick a real store (vector DB, Postgres) at scale. In-memory stdlib is for prototypes.
> - **Log the retrieval trace.** For every action, log the top-k memories that drove it. This is your debug ability.
> - **Budget per-agent tokens.** Each agent's retrieve + reflect + plan per tick is O(k) LLM calls. N agents × T ticks × calls-per-tick can dwarf your budget.
> - **Compact memory periodically.** Summarize-and-prune low-importance entries. Retention policy is a design decision, not a detail.
> - **Detect spatial / social norm violations** explicitly. The architecture does not learn them.

## Exercises · 练习

1. 运行 `code/main.py`。确认 3 个以上 agent 在派对上汇合。把 agent 增加到 10 个——涌现还会发生吗？
2. 去掉反思步骤。行为变成什么样？对应 Park 2023 的哪条消融发现？
3. 引入一个竞争性的植入目标（「Klaus 想在下午 5 点做一场研究演讲」）。agent 们会分裂吗，还是一个目标占主导？由什么决定？
4. 加上空间约束：Hobbs Cafe 最多容纳 4 个 agent。模拟是优雅地处理超员，还是踩中「单人卫生间」式的失效模式？
5. 阅读 Park et al.（arXiv:2304.03442）第 6 节（涌现行为实验）。找出一种在你的微缩版本中无法复现的行为。你需要增强架构的哪个组件？

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Memory stream | "agent 的日记" | 观察、行动、反思、计划的只追加日志。 |
| Recency | "记忆有多新" | 按年龄的指数衰减分数。 |
| Importance | "agent 有多在乎" | 写入时自评 1-10。缓存。 |
| Relevance | "与当前查询多相关" | 余弦相似度（基于 embedding）。 |
| Reflection | "更高阶的信念" | 从近期记忆生成的综合，作为新记忆再被摄入。 |
| Plan | "日/小时/行动分解" | 自顶向下的计划树。观察矛盾时可修订。 |
| Smallville | "Park 2023 的沙盒" | 产生情人节涌现的 25-agent 模拟。 |
| Believability | "质量指标" | 人类评分者对行为是否像一个可信 agent 的打分。 |

## Further Reading · 延伸阅读

- [Park et al. — Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442) —— 参照架构
- [UIST '23 paper page](https://dl.acm.org/doi/10.1145/3586183.3606763) —— 发表会议页面
- [Smallville code release](https://github.com/joonspk-research/generative_agents) —— 参考 Python 实现
- [Hayes-Roth 1985 — A Blackboard Architecture for Control](https://www.sciencedirect.com/science/article/abs/pii/0004370285900639) —— 结构化记忆 agent 的先例
