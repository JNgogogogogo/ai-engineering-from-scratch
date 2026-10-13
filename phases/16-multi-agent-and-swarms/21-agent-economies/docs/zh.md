# Agent Economies, Token Incentives, Reputation · 智能体经济、代币激励与声誉

> Long-horizon autonomous agents (METR's 1-hour to 8-hour work-curve) need economic agency. The emerging **5-layer stack** is: **DePIN** (physical compute) → **Identity** (W3C DIDs + reputation capital) → **Cognition** (RAG + MCP) → **Settlement** (account abstraction) → **Governance** (Agentic DAOs). Production agent-incentive networks include **Bittensor** (TAO subnets reward task-specific models), **Fetch.ai / ASI Alliance** (ASI-1 Mini LLM + FET token), and **Gonka** (transformer-based PoW that reallocates compute to productive AI tasks). Academic work: AAMAS 2025's decentralized LaMAS uses **Shapley-value credit attribution** to fairly reward contributing agents; Google Research "Mechanism design for large language models" proposes **token auctions** with second-price payment under monotone aggregation. This lesson builds a minimal agent marketplace, applies Shapley-value credit attribution to a multi-agent pipeline, and runs a second-price token auction so the game-theory machinery lands concretely.

长时程自主智能体（METR 测得的 1 小时到 8 小时工作曲线）需要经济能动性。新兴的**五层栈**是：**DePIN**（物理算力）→ **身份**（W3C DID + 声誉资本）→ **认知**（RAG + MCP）→ **结算**（账户抽象）→ **治理**（Agentic DAO）。生产级的智能体激励网络包括 **Bittensor**（TAO 子网奖励面向特定任务的模型）、**Fetch.ai / ASI Alliance**（ASI-1 Mini LLM + FET 代币）和 **Gonka**（把算力重新分配给生产性 AI 任务的 transformer 工作量证明）。学术工作方面：AAMAS 2025 的去中心化 LaMAS 用 **Shapley 值信用分配**公平奖励有贡献的智能体；Google Research 的「Mechanism design for large language models」提出单调聚合下二价支付的**代币拍卖**。本课构建一个最小的智能体市场，把 Shapley 值信用分配应用到多智能体流水线上，并运行一场二价代币拍卖，让博弈论机制落到实处。

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** Phase 16 · 16 (Negotiation and Bargaining), Phase 16 · 09 (Parallel Swarm Networks)
**Time:** ~75 minutes

## Problem · 问题

当智能体共同创造价值、却需要被单独奖励时，多智能体系统就变复杂了。经典机制 —— 平均分配、最后贡献者通吃 —— 要么不公平，要么可以被操纵。基于联盟的 Shapley 值奖励在构造上公平，但计算昂贵。2025-2026 年的文献推进了实用的近似方法：Shapley 采样、单调聚合拍卖、以及从已确认贡献中累积的链上声誉。

在信用分配之外，这个领域已经转向真正的经济智能体：Bittensor 的 TAO 奖励为微调子网专用模型贡献算力的矿工；Fetch.ai/ASI 用 FET 代币奖励 ASI-1 Mini LLM 的使用；Gonka 把 transformer 工作量证明重新分配到生产性 AI 任务。能自主交易的智能体今天已经存在；问题是如何对齐激励。

本课把智能体经济当作一个具体的问题族来处理 —— 信用分配、机制设计、声誉 —— 并用最小的数学把每一个构建出来，让思想真正扎下根。

> Multi-agent systems get complicated when agents produce value jointly but need to be rewarded individually. Classical mechanisms — equal split, last-contributor-takes-all — are unfair or gameable. Coalition-based rewarding via Shapley values is fair by construction but expensive to compute. The 2025-2026 literature pushes useful approximations: Shapley sampling, monotone aggregation auctions, and on-chain reputation that accrues from confirmed contributions.
> Beyond credit attribution, the field has turned to actual economic agents: Bittensor TAO rewards mining compute to fine-tune subnet-specific models, Fetch.ai/ASI rewards ASI-1 Mini LLM usage with FET tokens, Gonka reallocates transformer proof-of-work toward productive AI tasks. Agents that transact autonomously exist today; the question is how to align incentives.
> This lesson treats agent economies as a specific problem family — credit attribution, mechanism design, and reputation — and builds each with the minimal math so the ideas stick.

## Concept · 概念

### The 5-layer agent-economy stack · 五层智能体经济栈

1. **DePIN（物理算力）。** 出租 GPU、存储、带宽的去中心化基础设施。Bittensor 子网、Render Network、Akash。不是智能体专属；智能体使用它。
2. **身份。** W3C 去中心化标识符（DID）给每个智能体一个独立于任何平台的持久 ID。声誉累积到 DID 上。Agent Network Protocol（ANP）用 DID 作为发现层。
3. **认知。** 智能体的推理循环：LLM + RAG + MCP。这是其他 Phase 构建的内容。
4. **结算。** 账户抽象（ERC-4337）让智能体能用自己的余额支付 gas，而无需持有 ETH。智能体可以购买服务、互相支付、或购买算力。
5. **治理。** Agentic DAO：人类*和*智能体一起对协议变更投票的治理结构，投票权与声誉绑定。

不是每个生产系统都五层用全。Bittensor 用了 1、2、部分 3、部分 4，没有 5。OpenAI 智能体除 3 之外都没用。这个栈是一张参考地图，不是强制要求。

> The 5-layer agent-economy stack: DePIN (physical compute), Identity (W3C DIDs + reputation capital), Cognition (RAG + MCP), Settlement (account abstraction), Governance (Agentic DAOs).
> Not every production system uses all five. Bittensor uses 1, 2, partially 3, partially 4, none of 5. OpenAI agents use none except 3. The stack is a reference map, not a requirement.

### Bittensor, Fetch.ai, Gonka — what runs · Bittensor、Fetch.ai、Gonka —— 实际在跑什么

**Bittensor（TAO）。** 子网是专门化任务（语言建模、图像生成、预测）。矿工提交模型输出。验证者做排名；按权益加权评分来分配 TAO 奖励。每个子网有自己的评估。经济学教训：为任务特定的输出质量付费，而不是为用掉的算力付费。

**Fetch.ai / ASI Alliance。** ASI-1 Mini LLM 跑在 Fetch.ai 网络上；用户用 FET 代币支付推理费用。这里「智能体即对等节点」的叙事更强：Fetch 上的智能体可以调用另一个智能体做任务，并用 FET 支付。

**Gonka。** Transformer 工作量证明：「工作」就是 transformer 的前向传播。矿工通过运行有已知正确输出（来自训练数据）的推理任务来赚取收益。用资源生产性的 PoW 取代基于哈希的 PoW。

截至 2026 年 4 月，三者都是生产级的。收益分配方式各不相同。Bittensor 按子网验证者衡量的质量奖励；Fetch 按付费用户衡量的实用性奖励；Gonka 奖励可验证的推理工作量。

> **Bittensor (TAO).** Subnets are specialized tasks (language modeling, image generation, forecasting). Miners submit model outputs. Validators rank them; stake-weighted scoring distributes the TAO rewards. Each subnet has its own evaluation. The economic lesson: pay for task-specific output quality, not compute used.
> **Fetch.ai / ASI Alliance.** ASI-1 Mini LLM runs on Fetch.ai's network; users pay FET tokens for inference. The agents-as-peers narrative is stronger here: an agent on Fetch can call another for a task and pay in FET.
> **Gonka.** Transformer proof-of-work: the "work" is forward passes of a transformer. Miners earn by running inference tasks that have known correct outputs (from training data). Resource-productive PoW instead of hash-based PoW.
> All three are production-grade as of April 2026. Payoff distribution differs. Bittensor rewards quality relative to subnet validators; Fetch rewards utility measured by paying users; Gonka rewards verifiable inference work.

### Shapley-value credit attribution · Shapley 值信用分配

三个智能体合作一个任务。输出得分 0.8。谁贡献了什么？

Shapley 值：唯一同时满足四条公理（效率、对称、线性、虚无）的信用分配。对智能体 `i`：

```
shapley(i) = (1/N!) * sum over all orderings O of (v(S_i_O ∪ {i}) - v(S_i_O))
```

其中 `S_i_O` 是排序 `O` 中排在 `i` 之前的智能体集合。实践中：枚举所有排列，记录每个智能体在每个排列中的边际贡献，再取平均。

N=3 个智能体时有 6 个排列。N=10 时有 360 万个 —— 所以实践中你是对排序采样，而不是枚举。

> Shapley value: the unique credit allocation satisfying four axioms (efficiency, symmetry, linearity, null).
> In practice: enumerate all permutations, record marginal contribution of each agent in each permutation, average.
> For N=3 agents, there are 6 permutations. For N=10, 3.6M — so in practice you sample orderings rather than enumerate.

### Second-price auction for aggregation · 用于聚合的二价拍卖

Google Research（「Mechanism design for large language models」）提出用二价代币拍卖来聚合 LLM 输出。设定：N 个智能体各提交一个补全；每个智能体对「被选中」有一个私有估值。拍卖者选择估值最高的提案，并支付*第二高*的价格。在单调聚合下（价值只取决于选了哪个提案，而不是投了多少标），这个机制是诚实的 —— 智能体会报出自己的真实估值。

这对 LLM 系统为什么重要：你可以把补全任务外包给多个定价不同的智能体；拍卖选出最好的并公平支付，而智能体没有误报的动机。

> Google Research ("Mechanism design for large language models") proposes second-price token auctions for aggregating LLM outputs. Setup: N agents each propose a completion; each has a private value for being selected. The auctioneer picks the highest-value proposal and pays the *second-highest* value. Under monotone aggregation (value depends on which proposal is chosen, not how many were bid), this is truthful — agents bid their true value.
> Why this matters for LLM systems: you can outsource completion tasks to multiple agents with different pricing; the auction picks the best + pays fairly, and agents have no incentive to misreport.

### Reputation capital · 声誉资本

绑定 DID 的声誉分数从已确认的贡献中累积。一条简单的更新规则：

```
rep(i, t+1) = alpha * rep(i, t) + (1 - alpha) * contribution_quality(i, t)
```

衰减因子 `alpha` 接近 1。声誉：

- 读取便宜，可用于路由决策（「难任务发给高声誉智能体」）。
- 伪造昂贵（随时间累积，绑定 DID）。
- 可以被罚没（slash）：未通过验证的贡献会扣减声誉。

> A DID-bound reputation score accumulates from confirmed contributions.
> Reputation: is cheap to read for routing decisions ("send hard tasks to high-rep agents"); is expensive to forge (accumulates over time, bound to DID); can be slashed: contributions that fail verification subtract.

### AAMAS 2025 decentralized LaMAS · AAMAS 2025 去中心化 LaMAS

LaMAS 提案（AAMAS 2025）组合了：DID 身份、Shapley 值信用分配、和一个简单的拍卖机制。核心主张：把信用分配这一步去中心化，系统就可审计、且对单点操纵免疫。

> The LaMAS proposal (AAMAS 2025) combines: DID identity, Shapley-value credit attribution, and a simple auction mechanism. The key claim: decentralizing the credit attribution step makes the system auditable and immune to single-point manipulation.

### Where the economics falls apart · 经济学在哪里崩塌

- **价格预言机操纵。** 如果信用函数能被钻空子，智能体就会去钻。每个机制都需要对抗测试。
- **女巫攻击（Sybil attack）。** 一个运营者伪造 N 个假智能体来抬高自己的贡献。DID 能拖慢但不能阻止；声誉的伪造成本才是缓解手段。
- **验证成本。** 信用分配有多公平取决于验证者。验证便宜（小 LLM）就能被操纵；验证昂贵（人工评审团）系统就无法扩展。
- **监管阴影。** 智能体经济与金融监管交叉。截至 2026 年，Bittensor、Fetch 和 Gonka 在部分司法辖区都处于法律灰色地带。

> Price oracle manipulation: if the credit function can be gamed, agents will game it. Every mechanism needs an adversarial test.
> Sybil attacks: one operator spins up N fake agents to inflate their own contribution. DIDs slow but do not stop this; reputation cost-to-forge is the mitigation.
> Verification cost: credit attribution is only as fair as the verifier. If verification is cheap (small LLM), it can be gamed; if expensive (human panel), the system does not scale.
> Regulatory overhang: agent economies intersect with financial regulation. Bittensor, Fetch, and Gonka all operate in legal gray areas in some jurisdictions as of 2026.

### When agent economies make sense · 智能体经济什么时候成立

- **有异构运营者的开放网络。** 没有单一团队控制所有智能体。
- **可验证的输出。** 没有验证，信用分配就只是猜。
- **长时程工作流。** 一次性任务享受不到声誉累积。
- **代币化支付在你的司法辖区合法可行。**

在封闭的企业系统里，经济学让位于更简单的分配方式（经理派活、指标内部化）。经济学文献主要适用于开放网络。

> When agent economies make sense: open networks with heterogeneous operators; verifiable outputs; long-horizon workflows; tokenized payments are legally viable in your jurisdiction.
> In closed corporate systems, economics gives way to simpler allocation (managers assign work, metrics are internal). The economics literature applies mostly to open networks.

```figure
swarm-auction
```

## Build It · 动手造

`code/main.py` 实现：

- `shapley(value_fn, agents)` —— 对小 N 用枚举做精确 Shapley 计算。
- `second_price_auction(bids)` —— 诚实机制；赢家支付第二高价。
- `Reputation` —— 绑定 DID 的声誉，带指数衰减和罚没。
- 演示 1：三个智能体合作，精确 Shapley 分配信用。
- 演示 2：五个智能体竞标一个任务槽；二价拍卖选出赢家 + 支付额。
- 演示 3：100 轮向声誉各异的智能体分派任务；声誉加权路由优于随机路由。

运行：

```
python3 code/main.py
```

预期输出：每个智能体的 Shapley 值；展示诚实出价均衡的拍卖结果；声誉加权路由在预热后比随机路由高 10-20% 的质量收益。

> Expected output: Shapley values for each agent; auction result showing truthful-bid equilibrium; rep-weighted routing showing 10-20% quality gain over random after warmup.

## Use It · 实战用法

`outputs/skill-economy-designer.md` 设计一个最小的智能体经济：身份层的选择、信用分配机制、支付机制、声誉规则。

> `outputs/skill-economy-designer.md` designs a minimal agent economy: choice of identity layer, credit attribution mechanism, payment mechanism, reputation rule.

## Ship It · 交付

在 2026 年运营一个智能体经济体：

- **从声誉开始，而不是代币。** 声誉实现便宜，且单独就有价值；代币会带来法律和经济上的复杂性。
- **先验证，后奖励。** 绝不在没有独立验证步骤的情况下分配信用。自报质量会累积女巫操纵的空间。
- **Shapley 采样，不是 Shapley 精确。** 采样 100-1000 个排序；精确枚举无法扩展。
- **给衰减因子设上限、给声誉设下限。** 无界衰减会抹掉合法贡献者；衰减太慢会奖励过气的高声誉智能体。
- **对抗式审计机制。** 开放网络之前先跑红队场景。每个机制都有一套对应的博弈论；你要自己找到漏洞，而不是等攻击者来找。

> Running an agent economy in 2026: start with reputation, not tokens; verify before you reward; Shapley-sample, not Shapley-exact; cap decay factor and floor reputation; audit mechanisms adversarially. Every mechanism has a game theory; you want to find the holes, not the attackers.

## Exercises · 练习

1. 运行 `code/main.py`。确认 Shapley 值之和等于总价值（效率公理）。改变价值函数；Shapley 分配是否朝预期方向变化？
2. 实现 Shapley *采样*（对 K 个排序做蒙特卡洛）。K 如何影响近似精度？与 N=4 的精确值做比较。
3. 在拍卖之前实现一个结盟步骤：智能体可以合并成团队并以单位出价。哪些联盟会形成？结果比个体出价 Pareto 更优吗？
4. 阅读 Google Research 的机制设计文章。找出一条假设，违反它诚实性就会被破坏。这个失败模式在 LLM 场景里长什么样？
5. 阅读 AAMAS 2025 去中心化 LaMAS 论文。在合成任务上对 10 个智能体实现他们的 Shapley 步骤。精确计算要花多久？100 次采样能有多接近？

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| DePIN | 「去中心化物理基础设施」 | 代币激励的算力/存储/带宽。Bittensor、Akash、Render。 |
| DID | 「去中心化标识符」 | W3C 的可移植 ID 规范。智能体声誉绑定到 DID，而不是绑定到某个平台。 |
| ERC-4337 | 「账户抽象」 | 可以赞助 gas 的合约账户，让智能体支付成为可能。 |
| Shapley value | 「公平的信用分配」 | 唯一同时满足效率、对称、线性、虚无公理的分配。 |
| Second-price auction | 「Vickrey 拍卖」 | 诚实机制：赢家支付第二高出价。与单调聚合兼容。 |
| Reputation capital | 「累积的质量分」 | 绑定 DID、来自已确认贡献的分数；随时间衰减。 |
| Agentic DAO | 「智能体 + 人类共同治理」 | 智能体投票者是一等公民的 DAO，投票权与声誉绑定。 |
| TAO / FET / GPU credits | 「代币面额」 | Bittensor 的 TAO、Fetch.ai 的 FET、各类 DePIN 代币。 |

## Further Reading · 延伸阅读

- [The Agent Economy](https://arxiv.org/abs/2602.14219) — 2026 年五层智能体经济栈综述
- [Google Research — Mechanism design for large language models](https://research.google/blog/mechanism-design-for-large-language-models/) — 单调聚合下的代币拍卖
- [AAMAS 2025 — decentralized LaMAS](https://www.ifaamas.org/Proceedings/aamas2025/pdfs/p2896.pdf) — Shapley 值信用分配
- [Bittensor TAO documentation](https://docs.bittensor.com/) — 子网结构与奖励分配
- [Fetch.ai / ASI Alliance](https://fetch.ai/) — ASI-1 Mini LLM 与 FET 代币
- [W3C Decentralized Identifiers (DIDs) spec](https://www.w3.org/TR/did-core/) — 身份层基础
