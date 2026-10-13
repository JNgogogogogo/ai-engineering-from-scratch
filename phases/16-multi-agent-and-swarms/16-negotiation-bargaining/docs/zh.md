# 谈判与讨价还价（Negotiation and Bargaining）

> Agent 之间要谈判资源、价格、任务分配和条款。2026 年的基准集合给出了清晰的结论：NegotiationArena（arXiv:2402.05863）显示 LLM 能通过人格操纵（「desperation」绝境人设）把收益提高约 20%；"Measuring Bargaining Abilities"（arXiv:2402.15813）显示买方比卖方更难、而且堆规模没有用——他们的 **OG-Narrator**（确定性报价生成器 + LLM 叙述者）把成交率从 26.67% 推到 88.88%；大规模自主谈判竞赛（Large-Scale Autonomous Negotiation Competition, arXiv:2503.06416）跑了约 18 万场谈判，发现**隐藏思维链（chain-of-thought-concealing）**的 agent 靠对对手隐藏推理而获胜；Bhattacharya et al. 2025 用哈佛谈判项目的指标排名：Llama-3 最有效、Claude-3 最强势、GPT-4 最公平。本课实现合同网协议（Contract Net Protocol，FIPA 的祖先，第 02 课），接上一个 LLM 风格的买方/卖方，运行一次 OG-Narrator 式的分解，并度量每个结构性选择对成交率的影响。

> Agents negotiate resources, prices, task allocations, and terms. The 2026 benchmark set is clear: NegotiationArena (arXiv:2402.05863) shows LLMs can improve payoffs ~20% via persona manipulation ("desperation"); "Measuring Bargaining Abilities" (arXiv:2402.15813) shows buyer is harder than seller and scale does not help — their **OG-Narrator** (deterministic offer generator + LLM narrator) pushed deal rate from 26.67% to 88.88%; the Large-Scale Autonomous Negotiation Competition (arXiv:2503.06416) ran ~180k negotiations and found that **chain-of-thought-concealing** agents win by hiding reasoning from counterparts; Bhattacharya et al. 2025 on Harvard Negotiation Project metrics ranked Llama-3 most-effective, Claude-3 aggressive, GPT-4 fairest. This lesson implements Contract Net Protocol (the FIPA ancestor, Lesson 02), wires an LLM-style buyer/seller, runs an OG-Narrator-style decomposition, and measures how deal rate changes with each structural choice.

**Type:** Learn + Build
**Languages:** Python（stdlib）
**Prerequisites:** Phase 16 · 02（FIPA-ACL Heritage）、Phase 16 · 09（Parallel Swarm Networks）
**Time:** ~75 分钟

## Problem · 问题

两个 agent 需要就一个价格达成一致。放任它们用纯语言提示词自由发挥时，2024-2026 年的 LLM 以低得惊人的比率成交（arXiv:2402.15813 中严格参数化的议价场景约 27%）。堆规模也修不好：GPT-4 在议价的结构层面并不比 GPT-3.5 更强，它只是更擅长议价的*语言*。

根因在于 LLM 把两件事混在一起了——决定报价和叙述报价。OG-Narrator 把它们分开：一个确定性的报价生成器计算数值动作；LLM 只负责叙述。成交率跳到约 89%。

这印证了多 agent 领域的一个经典发现：把机制与通信层解耦就能赢。合同网协议（Contract Net Protocol，FIPA 1996；Smith 1980）就是参照级的任务市场机制。把 LLM 插进叙述的槽位，你就得到一个现代的 LLM 驱动任务市场。

> Two agents need to agree on a price. Left to themselves with pure language prompts, 2024-2026 LLMs close deals at surprisingly low rates (~27% on tightly-parameterized bargains in arXiv:2402.15813). Scale does not fix it: GPT-4 is not structurally better at bargaining than GPT-3.5; it is better at the *language* of bargaining.
> The root issue is that LLMs conflate two jobs — deciding the offer and narrating the offer. OG-Narrator separated these: a deterministic offer generator computes numeric moves; the LLM only narrates. Deal rate jumps to ~89%.
> This mirrors a classical multi-agent finding: decoupling the mechanism from the communication layer wins. Contract Net Protocol (FIPA, 1996; Smith, 1980) is the reference task-market mechanism. Plug an LLM into the narration slot and you get a modern LLM-powered task market.

## Concept · 概念

### Contract Net, in one paragraph · 一段话讲完合同网

Smith 1980 年的合同网协议（Contract Net Protocol）：一个 **manager（管理者）**广播一份 **call for proposals（cfp，征集提案）**；**bidders（投标者）**用包含各自报价的 **propose** 消息应答；manager 挑出赢家，向其发送 **accept-proposal**，向落选者发送 **reject-proposal**。赢家执行工作。可选消息：**refuse**（投标者拒绝提案）。FIPA 把它编为 `fipa-contract-net` 交互协议。

> Smith's 1980 Contract Net Protocol: a **manager** broadcasts a **call for proposals (cfp)**; **bidders** respond with **propose** messages containing their offers; the manager picks a winner and sends **accept-proposal** to the winner and **reject-proposal** to the losers. The winner performs the work. Optional message: **refuse** (bidder declines to propose). FIPA codified this as `fipa-contract-net` interaction protocol.

### Why OG-Narrator wins · OG-Narrator 为什么赢

"Measuring Bargaining Abilities of Language Models"（arXiv:2402.15813）观察到：

- LLM 常常破坏议价规则（报出荒谬的价格，无视对方的 ZOPA）。
- 它们的锚定很差（接受糟糕的首轮报价；还价用象征性而非策略性的幅度）。
- 单靠堆规模修不好这些。更大的模型说出更可信的话，但战略性错误不相上下。

OG-Narrator 的分解：

```
           ┌──────────────────┐        ┌──────────────────┐
  state  → │ offer generator  │ price → │  LLM narrator    │ → message
           │  (deterministic) │        │  (writes the     │
           │                  │        │   human-style    │
           └──────────────────┘        │   accompaniment) │
                                       └──────────────────┘
```

报价生成器是一个经典的谈判策略：Rubinstein 议价模型、Zeuthen 策略，或者价格上的简单 tit-for-tat。LLM 负责叙述。消息里同时包含确定性价格和自然语言的包装。

成交率跳升的原因：
- 价格留在议价区间内。
- 锚是策略性的，不是情绪化的。
- LLM 只做它擅长的事：写作。

> "Measuring Bargaining Abilities of Language Models" (arXiv:2402.15813) observed that:
> - LLMs often break the bargaining rules (offer at nonsensical prices, ignore the other side's ZOPA).
> - They anchor poorly (accept bad first offers; counter-offer at symbolic rather than strategic amounts).
> - Scale alone does not fix these. Larger models make more-plausible language with similar strategic error.
> The offer generator is a classical negotiation strategy: a Rubinstein bargaining model, a Zeuthen strategy, or a simple tit-for-tat over price. The LLM narrates. The message contains the deterministic price and the natural-language framing.
> Deal rate jumps because:
> - Prices stay in the bargaining zone.
> - Anchors are strategic, not emotional.
> - The LLM does what it is good at: writing.

### NegotiationArena findings · NegotiationArena 的发现

arXiv:2402.05863 提供了标杆基准。头条发现：

- LLM 能通过采用人格（「我急着在周五之前把它卖掉」）把收益提高约 20% —— 人格操纵是真实有效的战术。
- 公平/合作的 agent 会被对抗性 agent 剥削；防御需要显式的反制姿态。
- 对称配对在基准中约 40% 的场景里收敛到不公平的结果。

这不是「LLM 是糟糕的谈判者」。而是「LLM 谈判得太像人类了，包括那些可被剥削的部分」。

> arXiv:2402.05863 provides the canonical benchmark. Headline findings:
> - LLMs can improve payoffs ~20% by adopting personas ("I am desperate to sell this by Friday") — persona manipulation is a real tactic.
> - Fair/cooperative agents are exploited by adversarial ones; defense requires explicit counter-posturing.
> - Symmetric pair-ups converge to inequitable outcomes on about 40% of the benchmark scenarios.
> This is not "LLMs are bad negotiators." It is "LLMs negotiate too much like humans, including the exploitable parts."

### Chain-of-thought concealment · 思维链隐藏

大规模自主谈判竞赛（arXiv:2503.06416）在众多 LLM 策略之间跑了约 18 万场谈判。赢家都对对手隐藏了自己的推理：

- 如果一个 agent 把「我最多只会出到 $75；我的保留价是 $70」打印进公开可见的 scratchpad，对手就会读到它。
- 赢家私下计算策略；输出通道只包含报价和最低限度的必要叙述。

这是经典博弈论在 2026 年的回声（Aumann 1976 论理性与信息）：暴露你的私人估值会损失收益。LLM 对此没有直觉，会高高兴兴地把保留价打进对手可见的推理轨迹里。

工程要点：把私有 scratchpad 的上下文与公开消息的上下文分开。这不是可选项。

> The Large-Scale Autonomous Negotiation Competition (arXiv:2503.06416) ran ~180k negotiations across many LLM strategies. Winners concealed their reasoning from counterparts:
> - If an agent prints "I will only go to $75; my reservation price is $70" into a publicly visible scratchpad, the opponent reads it.
> - Winners compute strategy privately; the output channel contains only the offer and minimum required narration.
> This is a 2026 echo of classical game theory (Aumann 1976 on rationality and information): revealing your private valuation costs payoff. LLMs do not intuit this and happily type their reservations in reasoning traces that become visible to the counterpart.
> Engineering takeaway: separate private-scratchpad context from public-message context. Not optional.

### Bhattacharya et al. 2025 — model rankings · 模型排名

按哈佛谈判项目指标（原则性谈判、BATNA 尊重、利益互惠）：

- **Llama-3** 在达成交易上最有效（成交率 + 收益）。
- **Claude-3** 是最强硬的谈判者（高锚点、晚让步）。
- **GPT-4** 是最公平的（各配对间收益方差最小）。

这是 2025 年的快照。重点不是哪个模型在 2026 年 4 月获胜——而是不同的基础模型有持久稳定的谈判风格。异构集成（第 15 课）可以把这一点当作一个多样性来源。

> On Harvard Negotiation Project metrics (principled negotiation, BATNA respect, interest reciprocity):
> - **Llama-3** was most-effective at striking bargains (deal rate + payoff).
> - **Claude-3** was the most-aggressive negotiator (high anchors, late concessions).
> - **GPT-4** was the fairest (smallest variance in payoff across pairings).
> This is a 2025 snapshot. The point is not which model wins in April 2026 — it is that different base models have persistent negotiation styles. Heterogeneous ensembles (Lesson 15) include this as a diversity source.

### Task allocation via Contract Net + LLM · 用合同网 + LLM 做任务分配

合同网在 LLM 多 agent 中的现代用法：

1. Manager agent 把任务分解成单元。
2. 向 worker agent 广播带任务描述的 `cfp`。
3. 每个 worker 返回一份报价：`(price, eta, confidence)`，其中 price 可以是 token、算力单元或美元。
4. Manager 挑出赢家（单个或多个，视任务而定）并授标。
5. 被拒绝的 worker 可以自由竞标其他任务。

它能轻松扩展到 100 个以上的 worker，因为协调是「广播-应答」式的，不是同步聊天。生产中的使用：Microsoft Agent Framework 的编排模式、一些 LangGraph 实现。

> The modern re-use of Contract Net for LLM multi-agent:
> 1. Manager agent decomposes a task into units.
> 2. Broadcasts `cfp` with task description to worker agents.
> 3. Each worker returns an offer: `(price, eta, confidence)` where price could be tokens, compute units, or dollars.
> 4. Manager picks winners (single or multiple, depending on task) and awards.
> 5. Rejected workers are free to bid on other tasks.
> This scales well past 100 workers because coordination is broadcast-and-respond, not synchronous chat. Used in production: Microsoft Agent Framework's orchestration patterns, some LangGraph implementations.

### LLM-Stakeholders Interactive Negotiation · LLM 利益相关者交互谈判

NeurIPS 2024（https://proceedings.neurips.cc/paper_files/paper/2024/file/984dd3db213db2d1454a163b65b84d08-Paper-Datasets_and_Benchmarks_Track.pdf）引入了带**秘密分数**和**最低接受阈值**的多方可计分博弈。每个利益相关者都有私有效用函数；LLM 必须从消息中推断它们。这是把两方议价推广到 N 方联盟形成。对拥有异构 worker 能力的生产级任务市场很有参考价值。

> NeurIPS 2024 (https://proceedings.neurips.cc/paper_files/paper/2024/file/984dd3db213db2d1454a163b65b84d08-Paper-Datasets_and_Benchmarks_Track.pdf) introduces multi-party scorable games with **secret scores** and **minimum-acceptance thresholds**. Each stakeholder has private utilities; the LLM must infer them from messages. This is the generalization of two-party bargaining to N-party coalition formation. Relevant for production task markets with heterogeneous worker capabilities.

### The narration-vs-mechanism rule · 叙述与机制的分工法则

纵观 2024-2026 年的所有谈判基准，一贯的工程法则是：

> 让 LLM 叙述。不要让 LLM 计算报价。

如果报价必须是一个数字（价格、ETA、数量），就从谈判状态确定性地产出它，让 LLM 生成包装话术。如果报价必须是一个提案结构（任务分解、角色分配），可以让 LLM 起草，但发送前要对照 schema 校验并做约束检查。

> Across all 2024-2026 negotiation benchmarks, the consistent engineering rule is:
> > Let the LLM narrate. Do not let the LLM compute the offer.
> If the offer needs to be a number (price, ETA, quantity), generate it deterministically from the negotiation state and have the LLM produce the framing. If the offer needs to be a proposal structure (task decomposition, role assignment), let the LLM draft it, but validate it against a schema and constraint-check before sending.

```figure
a5-og-narrator
```

## Build It · 动手造

`code/main.py` 实现：

- `ContractNetManager`、`ContractNetTask`、`Bid` —— manager + bidders，广播 cfp，收集提案，授标。
- `og_narrator_bargain(state, rng)` —— OG-Narrator 买方：朝中点做确定性的 Zeuthen 风格让步。
- `seller_response(state, rng)` —— 确定性的卖方还价策略（两种风格的共同结构性真值）。
- `naive_llm_bargain(state, rng)` —— 模拟一个全 LLM 议价者：以高方差选价格，经常跑出 ZOPA 之外。
- 测量：1000 次试验上的成交率，每次试验重新采样保留价。

运行：

```
python3 code/main.py
```

预期输出：naive-LLM 成交率约 65-75%；OG-Narrator 成交率约 85-95%；这 15-25 个点的差距就是把报价生成从叙述中分解出来的结构性优势。外加一个三投标者一任务的合同网任务市场分配示例。

> `code/main.py` implements:
> - `ContractNetManager`, `ContractNetTask`, `Bid` — manager + bidders, broadcast cfp, collect proposals, award.
> - `og_narrator_bargain(state, rng)` — OG-Narrator buyer: deterministic Zeuthen-style concession toward the midpoint.
> - `seller_response(state, rng)` — deterministic seller counter-offer policy (the structural ground truth for both styles).
> - `naive_llm_bargain(state, rng)` — simulates an all-LLM bargainer: picks prices with high variance, often outside the ZOPA.
> - Measurement: deal rate over 1000 trials with fresh reservation prices sampled per trial.
> Expected output: naive-LLM deal rate ~65-75%; OG-Narrator deal rate ~85-95%; the 15-25 point gap is the structural advantage of decomposing offer-generation from narration. Plus a Contract Net task-market allocation example with three bidders and one task.

## Use It · 实战用法

`outputs/skill-bargainer-designer.md` 设计一套议价协议：谁生成报价（确定性或 LLM）、谁叙述、私有 scratchpad 如何与公开消息隔离、以及如何监控成交率。

> `outputs/skill-bargainer-designer.md` designs a bargaining protocol: who generates offers (deterministic or LLM), who narrates, how private scratchpads separate from public messages, and how deal rate is monitored.

## Ship It · 交付

生产级议价检查清单：

- **隔离 scratchpad。** 私有状态绝不进入对手的上下文。这条没有商量余地。
- **确定性的报价生成。** 价格、数量、ETA：计算，不要提示。
- **对照 schema 校验所有传入报价。** 在协议边界拒绝 ZOPA 之外的报价。
- **限制轮次。** 最多 3-5 轮；死锁时升级给调解者。
- **持续测量成交率与收益方差。** 成交率下滑是一个症状——通常是提示词漂移或对手侧攻击。
- **记录所有被拒绝的提案**及确定性理由。对合同网 manager 而言，落选的投标者需要知道为什么。

> Production bargaining checklist:
> - **Separate scratchpad.** Private state never reaches the counterpart's context. This is non-negotiable.
> - **Deterministic offer generation.** Prices, quantities, ETAs: compute, do not prompt.
> - **Validate all incoming offers** against a schema. Reject out-of-ZOPA offers at the protocol boundary.
> - **Bound rounds.** 3-5 rounds maximum; escalate to mediator on deadlock.
> - **Measure deal rate and payoff variance** continuously. A falling deal rate is a symptom — often a prompt drift or a counterpart-side attack.
> - **Log all rejected proposals** with the deterministic rationale. For Contract Net managers, losing bidders need to understand why.

## Exercises · 练习

1. 运行 `code/main.py`。确认 OG-Narrator 在成交率上击败 naive-LLM。领先多少？
2. 实现**基于人格的收益提升**（arXiv:2402.05863）——买方只在叙述里采用「这周不买不行」的人设，报价生成器保持不变。成交率或收益变化了吗？
3. 实现思维链**隐藏**：维护一个不传给对手的私有 scratchpad 字符串。如果不小心泄漏了会发生什么（通过交换两个通道来模拟）？
4. 把合同网扩展成带保留价的 N 投标者拍卖。当所有报价都超过保留价时，manager 该如何在最低价与最高质量之间取舍？你选哪条授标规则，为什么？
5. 阅读 Bhattacharya et al. 2025 的哈佛谈判项目指标。实现两个不同风格的议价者（强势 vs 公平）。在对称与非对称配对下测量收益方差。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Contract Net | "任务市场" | Smith 1980，FIPA 1996。cfp + propose + accept/reject。标杆级任务市场。 |
| ZOPA | "可能达成一致的区域" | 买方上限与卖方下限的重叠区。区域外的报价无法成交。 |
| BATNA | "谈判破裂时的最佳替代方案" | 这笔交易失败时的退路。决定你的保留价。 |
| OG-Narrator | "报价生成器 + 叙述者" | 分解：确定性报价，LLM 叙述。 |
| Zeuthen strategy | "风险最小化的让步" | 经典报价生成器，按风险极限让步。 |
| Rubinstein bargaining | "轮流出价的均衡" | 带折现的无限期议价的博弈论模型。 |
| CoT concealment | "藏起你的推理" | arXiv:2503.06416 的赢家保留私有 scratchpad；公开通道只显示报价。 |
| Persona manipulation | "情绪化姿态" | arXiv:2402.05863：绝境/紧迫人设带来约 20% 的收益提升。 |

## Further Reading · 延伸阅读

- [NegotiationArena](https://arxiv.org/abs/2402.05863) —— 基准；人格操纵与剥削的发现
- [Measuring Bargaining Abilities of Language Models](https://arxiv.org/abs/2402.15813) —— OG-Narrator 与「买方比卖方难」的结论
- [Large-Scale Autonomous Negotiation Competition](https://arxiv.org/abs/2503.06416) —— 约 18 万场谈判；思维链隐藏获胜
- [LLM-Stakeholders Interactive Negotiation (NeurIPS 2024)](https://proceedings.neurips.cc/paper_files/paper/2024/file/984dd3db213db2d1454a163b65b84d08-Paper-Datasets_and_Benchmarks_Track.pdf) —— 带秘密效用的多方可计分博弈
- [Smith 1980 — The Contract Net Protocol](https://ieeexplore.ieee.org/document/1675516) —— 经典机制，IEEE Transactions on Computers
