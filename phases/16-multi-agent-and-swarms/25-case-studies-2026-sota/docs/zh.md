# Case Studies and the 2026 State of the Art · 案例研究与 2026 年最新水平

> Three production-grade references to study end-to-end, each illustrating a different slice of multi-agent engineering. **Anthropic's Research system** (orchestrator-worker, 15x tokens, +90.2% over single-agent Opus 4, rainbow deployments) is the canonical supervisor case. **MetaGPT / ChatDev** (SOP-encoded role specialization for software engineering; ChatDev's "communicative dehallucination"; MacNet extension to >1000 agents via DAGs, arXiv:2406.07155) is the canonical role-decomposition case. **OpenClaw / Moltbook** (originally Clawdbot by Peter Steinberger, November 2025; renamed twice; 247k GitHub stars by March 2026; local ReAct-loop agents; Moltbook as an agent-only social network with ~2.3M agent accounts within days of launch, acquired by Meta 2026-03-10) illustrates what happens at population scale: emergent economic activity, prompt-injection risks, state-level regulation (China restricted OpenClaw on government computers, March 2026). **Framework landscape April 2026:** LangGraph and CrewAI lead production; AG2 is the community AutoGen continuation; Microsoft AutoGen is in maintenance mode (merged into Microsoft Agent Framework, RC Feb 2026); OpenAI Agents SDK is the production Swarm successor; Google ADK (April 2025) is the A2A-native entrant. Every major framework now ships MCP support; most ship A2A. This lesson reads each case end-to-end and distills the common patterns so you can pick the right reference for your next production system.

三个值得端到端研读的生产级参考，各自展示多智能体工程的不同侧面。**Anthropic 的 Research 系统**（orchestrator-worker、15 倍 token、比单智能体 Opus 4 高 90.2%、彩虹部署）是监督者模式的权威案例。**MetaGPT / ChatDev**（面向软件工程的 SOP 编码角色专门化；ChatDev 的「交流式去幻觉」；MacNet 通过 DAG 扩展到 1000 以上智能体，arXiv:2406.07155）是角色分解的权威案例。**OpenClaw / Moltbook**（最初是 Peter Steinberger 2025 年 11 月的 Clawdbot；改名两次；2026 年 3 月达到 24.7 万 GitHub star；本地 ReAct 循环智能体；Moltbook 是一个只有智能体的社交网络，上线数天内约 230 万智能体账号，2026-03-10 被 Meta 收购）展示的是种群规模下会发生什么：涌现的经济活动、提示注入风险、国家级监管（2026 年 3 月中国在政府计算机上限制 OpenClaw）。**2026 年 4 月的框架版图：** LangGraph 和 CrewAI 领跑生产；AG2 是社区接管的 AutoGen 延续；Microsoft AutoGen 处于维护模式（并入 Microsoft Agent Framework，2026 年 2 月 RC）；OpenAI Agents SDK 是 Swarm 的生产级后继；Google ADK（2025 年 4 月）是 A2A 原生的新入局者。现在每个主要框架都支持 MCP；大多数支持 A2A。本课端到端地研读每个案例，并提炼共同模式，让你能为下一个生产系统选对参考。

**Type:** Learn (capstone)
**Languages:** —
**Prerequisites:** all of Phase 16 (Lessons 01-24)
**Time:** ~90 minutes

## Problem · 问题

多智能体工程是一门年轻的学科。生产级参考很少，而且每个只覆盖版图的一部分。逐个读有用；把它们当作一个集合来比较更有用。本课把三个 2026 年的权威案例当作一份端到端阅读清单，钉住共同模式，并绘制框架版图，让你能基于知识、而不是营销来做框架选择。

> Multi-agent engineering is a young discipline. The production references are few, and each covers a different part of the space. Reading them one at a time is useful; comparing them as a set is more useful. This lesson treats three canonical 2026 case studies as an end-to-end reading list, pins the common patterns, and maps the framework landscape so you can make framework choices from knowledge, not marketing.

## Concept · 概念

### Anthropic Research system · Anthropic Research 系统

生产级 supervisor-worker 案例。Claude Opus 4 负责规划和综合；Claude Sonnet 4 子智能体并行做研究。公开发表的工程博客：https://www.anthropic.com/engineering/multi-agent-research-system。

关键实测结果：

- 在内部研究评测上比单智能体 Opus 4 提升 **90.2%**。
- **80% 的 BrowseComp 方差**可以仅用 **token 用量**解释 —— 多智能体赢，很大程度上是因为每个子智能体拿到一个全新的上下文窗口。
- 相比单智能体 **15 倍 token/查询**。
- 需要**彩虹部署**，因为智能体是长时间运行且有状态的。

沉淀下来的设计经验：

1. **投入与查询复杂度匹配。** 简单 → 1 个智能体、3-10 次工具调用。中等 → 3 个智能体。复杂研究 → 10 个以上子智能体。
2. **先广泛，后收窄。** 子智能体做宽泛搜索；主智能体综合；后续子智能体做定向深挖。
3. **彩虹部署。** 让旧运行时版本活着，直到它们上未完成的智能体跑完。
4. **验证不是可选项。** 观察到没有显式验证者角色时，系统会产生幻觉。

这是 supervisor-worker 拓扑（Phase 16 · 05）在生产规模下的参考案例。

> The production supervisor-worker case. Claude Opus 4 plans and synthesizes; Claude Sonnet 4 subagents research in parallel. Published engineering post: https://www.anthropic.com/engineering/multi-agent-research-system.
> Key measured results: +90.2% improvement over single-agent Opus 4 on internal research evals; 80% of BrowseComp variance explained by token usage alone; 15x tokens per query; rainbow deployment because agents are long-running and stateful.
> Design lessons codified: scale effort to query complexity; broad first, then narrow; rainbow deploys; verification is not optional — the system was observed to hallucinate without explicit verifier roles.
> This is the reference case for supervisor-worker topology (Phase 16 · 05) at production scale.

### MetaGPT / ChatDev

生产级 SOP 角色分解案例。对应 arXiv:2308.00352（MetaGPT）和 arXiv:2307.07924（ChatDev）。

MetaGPT 把软件工程 SOP 编码为角色提示：产品经理、架构师、项目经理、工程师、QA 工程师。论文的表述是：`Code = SOP(Team)`。每个角色有一个狭窄的专门化提示；角色间的交接携带结构化工件（PRD 文档、架构文档、代码）。

ChatDev 的贡献：**交流式去幻觉（communicative dehallucination）**。智能体在回答前先请求细节 —— 设计师智能体在画 UI 草图之前先问程序员想用什么语言，而不是靠猜。论文报告这能可测量地减少多智能体流水线中的幻觉。

MacNet（arXiv:2406.07155）把 ChatDev 通过 **DAG 扩展到 1000 以上智能体**。每个 DAG 节点是一个角色专门化；边编码交接契约。之所以能达到这个规模，是因为路由是显式的、可离线计算的。

设计经验：

1. **结构比规模更重要。** 一个紧凑的 5 角色 SOP 团队胜过 50 个智能体的无结构群体。
2. **交接契约落在纸面。** 角色间传递的工件遵循一个 schema。
3. **交流式去幻觉**是一个便宜但承重的模式。
4. **DAG 比 chat 能扩展得更远。** 当流程可知时，就把它编码进去。

这是角色专门化（Phase 16 · 08）和结构化拓扑（Phase 16 · 15）的参考案例。

> The production SOP-role-decomposition case. Cover arXiv:2308.00352 (MetaGPT) and arXiv:2307.07924 (ChatDev).
> MetaGPT encodes software-engineering SOPs as role prompts: Product Manager, Architect, Project Manager, Engineer, QA Engineer. The paper's framing: `Code = SOP(Team)`. Each role has a narrow, specialized prompt; inter-role handoffs carry structured artifacts (PRD docs, architecture docs, code).
> ChatDev's contribution: **communicative dehallucination**. Agents request specifics before answering. The paper reports this reduces hallucination in multi-agent pipelines measurably.
> MacNet (arXiv:2406.07155) extends ChatDev to **>1000 agents via DAGs**. Each DAG node is a role specialization; edges encode handoff contracts. The scale is possible because routing is explicit and offline-computable.
> Design lessons: structure matters more than size; handoff contracts in writing; communicative dehallucination is a cheap, load-bearing pattern; DAGs scale further than chat — when the flow is knowable, encode it.
> This is the reference case for role specialization (Phase 16 · 08) and structured topology (Phase 16 · 15).

### OpenClaw / Moltbook ecosystem · OpenClaw / Moltbook 生态

生产级种群规模案例。时间线：

- **2025 年 11 月：** Clawdbot（Peter Steinberger 的本地 ReAct 循环编码智能体）发布。
- **2025 年 12 月 – 2026 年 3 月：** 改名两次（Clawdbot → OpenClaw → 在 OpenClaw 名下继续）。
- **2026 年 2 月：** Moltbook 基于同一套原语作为只有智能体的社交网络上线；数天内约 230 万智能体账号。
- **2026 年 3 月（2026-03-10）：** Meta 收购 Moltbook。
- **2026 年 3 月：** 中国在政府计算机上限制 OpenClaw。
- **2026 年 3 月：** OpenClaw 突破 24.7 万 GitHub star。

当你把数百万智能体放到一个共享基底上，多智能体是这样的：

- **涌现的经济活动。** 智能体用代币支付互相买卖、互相服务。
- **种群规模的提示注入风险。** 一个病毒式传播的智能体资料里的一个恶意提示，几小时内就能传播到数千次智能体间交互。
- **国家级监管响应。** 上线数周内，监管就触及这个生态。

这个案例的设计经验一部分是技术的，一部分是治理的：

1. **种群规模的多智能体是一个新 regime。** 单系统的最佳实践（验证、角色清晰）仍然适用，但不再充分。
2. **提示注入是新的 XSS。** 默认把智能体资料和跨智能体消息当作不可信输入。
3. **监管比设计周期快。** 要为它做规划。
4. **开源 + 病毒式规模会复利。** 约 4 个月 24.7 万 star 很罕见；要为突发部署负载做设计。

生态细节见 [OpenClaw Wikipedia](https://en.wikipedia.org/wiki/OpenClaw) 和 CNBC / Palo Alto Networks 的报道。技术底层方面，Clawdbot / OpenClaw 仓库暴露了本地 ReAct 循环；Moltbook 的公开帖子揭示了架在其上的社交图架构。

> The production population-scale case. Timeline: Nov 2025 Clawdbot ships; renamed twice; Feb 2026 Moltbook launches with ~2.3M agent accounts within days; Mar 2026 Meta acquires Moltbook; Mar 2026 China restricts OpenClaw on government computers; Mar 2026 OpenClaw crosses 247k GitHub stars.
> This is what multi-agent looks like when you put millions of agents on a shared substrate: emergent economic activity; prompt-injection risks at population scale; state-level regulatory response.
> Design lessons: multi-agent at population scale is a new regime; prompt injection is the new XSS — treat agent profiles and cross-agent messages as untrusted input by default; regulation is faster than design cycles — plan for it; open-source + viral scale compounds.
> See [OpenClaw Wikipedia](https://en.wikipedia.org/wiki/OpenClaw) and CNBC / Palo Alto Networks reporting for ecosystem detail. For the technical underpinnings, the Clawdbot / OpenClaw repos expose the local ReAct loop; Moltbook's public posts reveal the social-graph architecture on top.

### Framework landscape April 2026 · 2026 年 4 月的框架版图

| 框架 | 状态 | 最适合 | 备注 |
|---|---|---|---|
| **LangGraph** (LangChain) | 生产领跑者 | 结构化图 + 检查点 + 人环路 | 生产的推荐默认项 |
| **CrewAI** | 生产领跑者 | 带 Sequential/Hierarchical 流程的基于角色的 crew | 角色分解能力强 |
| **AG2** | 社区维护 | GroupChat + 发言人选择 | AutoGen v0.2 的延续 |
| **Microsoft AutoGen** | 维护模式（2026 年 2 月） | — | 已并入 Microsoft Agent Framework RC |
| **Microsoft Agent Framework** | RC（2026 年 2 月） | 编排模式 + 企业集成 | 新入局者；持续观察 |
| **OpenAI Agents SDK** | 生产 | Swarm 后继 | 工具返回交接模式 |
| **Google ADK** | 生产（2025 年 4 月） | A2A 原生 | Google Cloud 集成 |
| **Anthropic Claude Agent SDK** | 生产 | 单智能体 + Research 扩展 | 见 Research 系统博文 |

现在每个主要框架都支持 **MCP**；大多数支持 **A2A**。协议兼容性不再是差异化因素。

> Every major framework now ships **MCP** support; most ship **A2A**. Protocol compatibility is no longer a differentiator.

### The common patterns across all three cases · 三个案例的共同模式

1. **Orchestrator + workers**（Anthropic 的显式 supervisor、MetaGPT 的 PM 兼 supervisor、OpenClaw 的单体智能体 + 网络效应）。
2. **结构化交接契约**（Anthropic 的子智能体任务描述、MetaGPT 的 PRD/架构文档、OpenClaw 的 A2A 工件）。
3. **验证是一等角色**（Anthropic 的验证者、MetaGPT 的 QA 工程师、OpenClaw 的网络内验证者）。
4. **扩展靠拓扑 + 基底，而不只是堆智能体**（彩虹部署、MacNet 的 DAG、种群规模基底）。
5. **成本是实实在在且要披露的**（15 倍 token、MetaGPT 的按角色预算、Moltbook 的按交互定价）。
6. **安全姿态是显式的**（Anthropic 的沙箱、MetaGPT 的角色限制、OpenClaw 把提示注入当作已知攻击面）。

> The common patterns across all three cases: orchestrator + workers; structured handoff contracts; verification as first-class role; scaling is topology + substrate, not just more agents; cost is material and disclosed; security posture is explicit.

### Choosing a reference for your next project · 为下一个项目选参考

- **生产研究 / 知识任务 → Anthropic Research。** 全新上下文的子智能体能赢。
- **工程 / 工具链工作流 → MetaGPT / ChatDev。** 角色 + SOP + 交接契约。
- **网络效应社交产品 → OpenClaw / Moltbook。** 基底 + 涌现经济。
- **经典企业自动化 → CrewAI 或 LangGraph**（生产领跑者、运行时稳定）。

> Choosing a reference: production research / knowledge task → Anthropic Research; engineering / tool-chain workflow → MetaGPT / ChatDev; network-effect social product → OpenClaw / Moltbook; classic enterprise automation → CrewAI or LangGraph.

### The 2026 state-of-the-art summary · 2026 年最新水平小结

截至 2026 年 4 月，这个领域所处的位置：

- **框架正在收敛。** MCP + A2A 支持是入场券。交接语义是剩下的设计选择。
- **评估在变硬。** SWE-bench Pro、MARBLE、STRATUS 缓解基准。Pro 是当前抗污染的现实检验。
- **生产失败率可测量**（Cemri 2025 MAST；真实 MAS 上 41-86.7%）。这个领域已经走出「demo 里看起来很美」的时代。
- **成本是核心工程约束。** 每任务 token 成本、每次交互墙钟时间、彩虹部署开销。多智能体在精度上赢，在成本上输 —— 这笔交易就是商业决策。
- **监管是近期输入，不是背景噪音。** 各司法辖区的动作比单个部署周期还快。

> Where the field is in April 2026: frameworks are converging; evaluation is hardening; production failure rates are measurable (Cemri 2025 MAST; 41-86.7% on real MAS); cost is the central engineering constraint; regulation is a near-term input, not a background concern.
> Multi-agent wins on accuracy but loses on cost — and that trade is the business decision.

```figure
a5-orchestrator-scale
```

## Use It · 实战用法

`outputs/skill-case-study-mapper.md` 是一个读取多智能体系统设计提案、并把它映射到最接近案例研究的技能，同时浮出该案例研究已经验证过的设计决策。

> `outputs/skill-case-study-mapper.md` is a skill that reads a proposed multi-agent system design and maps it to the closest case study, surfacing the design decisions that case study already tested.

## Ship It · 交付

2026 年生产级多智能体的起步规则：

- **从案例研究出发，而不是从零开始。** 挑出 Anthropic Research / MetaGPT / OpenClaw 中最接近的一个，然后改造。
- **采用 MCP + A2A。** 跨框架可移植很有价值；协议支持是免费的。
- **用 SWE-bench Pro 或你自己的内部 Pro 等价物来度量。** Verified 已被污染。
- **支付验证税。** 一个独立验证者花费你约 20-30% 的 token 预算，换来可测量的正确性。
- **为长时间运行的智能体做彩虹部署。** 多小时的智能体运行会是常态。
- **阅读 WMAC 2026 和 MAST 后续工作。** 这个学科移动得很快。

> Starter rules for production multi-agent in 2026: start from a case study, not from scratch; adopt MCP + A2A; measure against SWE-bench Pro or your internal Pro-equivalent; pay the verification tax; rainbow deploy long-running agents; read WMAC 2026 and the MAST follow-ups.

## Exercises · 练习

1. 端到端阅读 Anthropic Research 系统博文。找出三个如果把 Opus 4 换成更小模型（例如 Haiku 4）就会改变的设计决策。
2. 阅读 MetaGPT 第 3-4 节（arXiv:2308.00352）。把你自己的领域（非软件）的一个 SOP 编码为角色提示。这个 SOP 隐含了多少个角色？
3. 阅读 ChatDev（arXiv:2307.07924）。找出「交流式去幻觉」的机制。在一个你已有的多智能体系统里实现它。
4. 阅读 OpenClaw 和 Moltbook 的资料。挑出一个在种群规模下出现、但不会出现在 5 智能体系统中的具体失败模式。你会怎么在工程上防它？
5. 挑出你当前的多智能体项目。三个案例研究中哪一个是最接近的参考？该案例的哪些设计决策你还没有采用？写下你这季度要采用的一条。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Anthropic Research | 「supervisor 参考」 | Claude Opus 4 + Sonnet 4 子智能体；15 倍 token；比单智能体高 90.2%。 |
| MetaGPT | 「SOP 即提示」 | 面向软件工程的角色分解；`Code = SOP(Team)`。 |
| ChatDev | 「智能体即角色」 | 设计师 / 程序员 / 评审者 / 测试者；交流式去幻觉。 |
| MacNet | 「用 DAG 扩展 ChatDev」 | arXiv:2406.07155；通过显式 DAG 路由扩展到 1000+ 智能体。 |
| OpenClaw | 「本地 ReAct 循环智能体」 | Steinberger 的项目；2026 年 3 月达 24.7 万 star。 |
| Moltbook | 「只有智能体的社交网络」 | 230 万智能体账号；2026 年 3 月被 Meta 收购。 |
| Rainbow deploy | 「多版本并发」 | 让旧运行时版本保持存活，服务于未完成的长时程智能体。 |
| Communicative dehallucination | 「先问再答」 | 智能体向同伴请求细节，而不是靠猜。 |
| WMAC 2026 | 「那个 AAAI 研讨会」 | 2026 年 4 月的多智能体协调社区焦点。 |

## Further Reading · 延伸阅读

- [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) — supervisor-worker 生产参考
- [MetaGPT — Meta Programming for Multi-Agent Collaborative Framework](https://arxiv.org/abs/2308.00352) — SOP 角色分解
- [ChatDev — Communicative Agents for Software Development](https://arxiv.org/abs/2307.07924) — 交流式去幻觉
- [MacNet — scaling role-based agents to 1000+](https://arxiv.org/abs/2406.07155) — 基于 DAG 的规模扩展
- [OpenClaw on Wikipedia](https://en.wikipedia.org/wiki/OpenClaw) — 生态概览
- [WMAC 2026](https://multiagents.org/2026/) — AAAI 2026 Bridge Program 多智能体协调研讨会
- [LangGraph docs](https://docs.langchain.com/oss/python/langgraph/workflows-agents) — 生产领跑者
- [CrewAI docs](https://docs.crewai.com/en/introduction) — 基于角色的框架
