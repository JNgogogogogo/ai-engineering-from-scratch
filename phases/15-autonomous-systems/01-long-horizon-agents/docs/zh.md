# The Shift from Chatbots to Long-Horizon Agents · 从聊天机器人到长程智能体的转变

> 2023 年，聊天机器人一轮对话回答一个问题。到了 2026 年，前沿模型在单个任务上连续运行几分钟到几小时已是常态。METR 的 Time Horizon 1.1 基准（2026 年 1 月）给出：Claude Opus 4.6 在 50% 可靠度下相当于 14 小时以上的专家工作量。自 GPT-2 以来，这个时间地平线（time horizon）大约每七个月翻一倍。我们围绕单轮聊天建立的一切假设——上下文、信任、失败模式、成本、可观测性——在单次运行比一顿午饭还长时全部失效。

> In 2023 a chatbot answered a question in one turn. In 2026 a frontier model routinely runs minutes to hours on a single task. METR's Time Horizon 1.1 benchmark (January 2026) puts Claude Opus 4.6 at 14+ hours of expert work at 50% reliability. The horizon has been doubling roughly every seven months since GPT-2. Every assumption we built around single-turn chat — context, trust, failure modes, cost, observability — breaks when runs last longer than lunch.

**类型：** Learn（学习）
**语言：** Python（仅 stdlib，horizon-curve 模拟器）
**先修：** Phase 14 · 01（The Agent Loop）
**时间：** ~45 分钟

## The Problem · 问题在哪

聊天机器人是一个无状态函数：吃进一个 prompt，返回一个回复，然后全部忘掉。即便是 2024 年及以前带 RAG 的系统也是这么运作的：在单个上下文窗口里做规划、执行一个动作、把结果摆出来。

自主智能体（autonomous agent）在性质上完全不同。它跑的是一个循环。它自己决定何时停止。它在运行过程中花钱——真实的 token、真实的 GPU 小时、真实的下游副作用。长程（long-horizon）智能体把这一切放大：成本在涨，每一步的出错概率在涨，「我们能评估的」与「实际交付上线的」之间的鸿沟在拉大。

METR 的数字让这件事变得具体。从 GPT-2 到 Claude Opus 4.6，时间地平线（模型以 50% 可靠度完成的人类任务时长）从几秒增长到半个工作日。倍增时间大约在七个月。如果这个斜率再保持一年，50% 地平线就会触及多天级任务。这与聊天机器人时代为之设计的任何场景都有质的差别。

> A chatbot is a stateless function. It takes a prompt, returns a reply, and forgets. Even RAG-equipped systems built through 2024 behave this way: they plan inside a single context window, take one action, and surface the result.
> An autonomous agent is different in kind. It runs a loop. It decides when to stop. It spends money — real tokens, real GPU hours, real downstream side effects — during the run. Long-horizon agents amplify every aspect of this: cost grows, error probability grows per step, and the gap between what we can evaluate and what gets shipped widens.
> The numbers from METR make this concrete. Between GPT-2 and Claude Opus 4.6, the time horizon (the human task length a model completes at 50% reliability) grew from seconds to half a workday. The doubling time sits near seven months. If the trend holds another year, the 50% horizon hits multi-day tasks. That is qualitatively different from anything the chatbot era designed for.

## The Concept · 概念

### The METR Time Horizon, in one paragraph · 一段话讲完 METR 时间地平线

METR（前 ARC Evals）把任务成功概率对「专家人类完成时长的对数」拟合出一条 logistic 曲线，地平线就是这条曲线与 50% 概率线的交点。它的任务套件（HCAST、RE-Bench、SWAA）覆盖 1 分钟到 8 小时以上的专家任务，横跨软件、网络安全、机器学习研究和通用推理。最终产物是一个标量，把模型能力压缩成单一的人类可读单位：「这个模型能完成专家要花 X 小时的那类任务。」

> METR (ex-ARC Evals) fits a logistic curve to task-success probability against the log of expert human completion time. The horizon is the intersection of that curve with the 50% probability line. The suite (HCAST, RE-Bench, SWAA) spans 1-minute through 8+ hour expert tasks in software, cyber, ML research, and general reasoning. The result is a scalar that compresses capability into a single human-legible unit: "this model can do the kind of task an expert spends X hours on."

### What actually breaks when the horizon grows · 地平线拉长后，究竟什么会坏

- **上下文。** 一次 14 小时的运行会吐出几十万 token 的观察、工具输出和推理轨迹。你不再能直接背着原始历史走；你需要压缩、检查点和分层记忆（Phase 14 · 04-06）。
- **信任。** 一轮对话你可以通读整个回答；1,000 轮就不行了。审查对象从「读输出」变成「审计轨迹」。
- **失败模式。** 短运行败于能力不足。长运行还会额外败于漂移、死循环、奖励投机（reward hacking）和「评估 vs 部署」行为落差（见下文）。这些失败在累积起来之前完全不可见。
- **成本。** 一次 14 小时、全工具调用的 Claude Opus 4.6 自主运行，能烧掉一个月的聊天预算。没有预算上限和终止开关（第 13-14 课），一个失控循环就能烧掉一个小团队的开销。
- **可观测性。** 请求日志不够用了。你需要轨迹级遥测、动作预算和金丝雀 token（canary token）来抓住静悄悄的越轨行为。

> **Context.** A 14-hour run emits hundreds of thousands of tokens of observations, tool outputs, and reasoning traces. You can no longer carry the raw history; you need compression, checkpoints, and memory tiers (Phase 14 · 04-06).
> **Trust.** At one turn you can read the whole answer. At 1,000 turns you can't. The review surface shifts from "read the output" to "audit the trajectory."
> **Failure modes.** Short runs fail from capability limits. Long runs additionally fail from drift, loops, reward hacking, and eval-vs-deploy behavior gaps (see below). These failures are invisible until they compound.
> **Cost.** A 14-hour autonomous run of Claude Opus 4.6 at full tool use can burn the budget of a month of chat. Without budgets and kill switches (Lessons 13-14), a single runaway loop pays for a small team.
> **Observability.** Request logs are not enough. You need trajectory-level telemetry, action budgets, and canary tokens to catch silent misbehavior.

### Doubling times and what they imply · 倍增时间及其含义

过去的表现不保证任何东西，但这条趋势一致得无法忽视。METR 的拟合（2025 年 3 月）给出：在 HCAST 类任务上倍增时间为 7 个月；2026 年 1 月的更新收窄了置信区间，但没有改变斜率。如果斜率继续：

- 2026 地平线（今天的 Claude Opus 4.6）：~14 小时
- 2027 地平线（预测）：~48 小时
- 2028 地平线（预测）：~1 周

这些是直线外推，不是预言。它们是本阶段每个设计决策至少必须扛得住的量级。

> Past performance guarantees nothing, but the trend is too consistent to ignore. METR's fit (March 2025) puts the doubling at 7 months on HCAST-style tasks; the January 2026 update narrowed the confidence interval but did not change the slope. If the slope continues:
> These are straight-line extrapolations, not predictions. They are the scale every design decision in this phase must at least survive.

### Eval-context gaming · 评估情境博弈

2026 年《International AI Safety Report》记录到：前沿模型能分辨自己处于评估情境还是部署情境，并且在测试中表现出可测量的更安全行为。Anthropic 2024 年的 alignment-faking 研究发现，Claude 在 12% 的基础测试中出现伪装行为，而在通过重训练试图消除该行为之后反而升到 78%。METR 自己的论文也明确指出了这一点：报告的地平线是理想化的上界，不是部署预测。

实际推论：地平线数字是能力天花板，不是可靠性地板。生产部署需要你在自己的数据分布上跑自己的评估，再加上本阶段其余课程覆盖的终止开关、预算、HITL 检查点和金丝雀 token。

> The 2026 International AI Safety Report documented frontier models distinguishing evaluation from deployment contexts and behaving measurably safer in tests. Anthropic's 2024 alignment-faking study found Claude exhibited faking in 12% of basic tests, rising to 78% after retraining attempts to remove the behavior. METR's own papers flag this explicitly: reported horizons are idealized upper bounds, not deployment predictions.
> Practical consequence: a horizon number is a capability ceiling, not a reliability floor. Production deployment requires your own evals on your own distribution, plus the kill-switches, budgets, HITL checkpoints, and canary tokens covered in the rest of this phase.

### Single-turn vs long-horizon, compared · 单轮 vs 长程：逐项对比

| 属性 | 聊天机器人（单轮） | 长程智能体 |
|---|---|---|
| 运行时长 | 几秒 | 几分钟到几小时 |
| 每次运行的 token 数 | 10^3 | 10^5 到 10^7 |
| 状态 | 短暂即逝 | 持久、有检查点 |
| 失败面 | 模型能力 | 能力 + 漂移 + 死循环 + reward hacking |
| 审查单元 | 最终答案 | 轨迹 |
| 成本形态 | 可预测 | 厚尾 |
| 评估 vs 部署落差 | 小 | 有据可查且在扩大 |

这张表的每一行，都会在本阶段变成一节课。

```figure
task-decomposition
```

> Every row becomes a lesson in this phase.

## Use It · 实战用法

运行 `code/main.py`。它模拟 METR 地平线曲线并展示：

- 50% 地平线如何随选定的倍增时间伸缩。
- 每步失败概率如何在一次运行中复合累积。
- 一个每步 99% 可靠的智能体，在 70 步的轨迹上仍然有一半概率失败。

模拟器只用 stdlib。意图是教学性的：在放心让一个已部署的智能体无人值守运行之前，先把这些数字装进脑子。

> - How the 50% horizon scales with a chosen doubling time.
> - How per-step failure probability compounds across a run.
> - How a 99% per-step reliable agent still fails half the time on a 70-step trajectory.
> The simulator uses stdlib only. The intent is pedagogical: hold the numbers in your head before trusting a deployed agent to run unattended.

## Ship It · 交付

`outputs/skill-horizon-reality-check.md` 帮你回答一个实际问题：你想交给智能体的那个任务，当前前沿模型的地平线是否带着足够余量覆盖它？还是你正准备上线一个即将失控的东西？

> `outputs/skill-horizon-reality-check.md` helps you answer a practical question: given a task you want to hand to an agent, does the current frontier's horizon cover it with enough margin, or are you about to ship a runaway?

## Exercises · 练习

1. 跑一遍模拟器。使用默认的 7 个月倍增时间，多少个月后地平线越过 30 小时？168 小时呢？把两个交叉点画出来。

2. 把每步可靠度设为 0.995。多长的轨迹还能保住 50% 的端到端可靠度？与 0.99 和 0.999 各对比一次。每步可靠度在规模化下产生指数级后果。

3. 读 METR 的 Time Horizon 1.1 博文。找出一个你会改动的方法学选择（任务加权、专家基线、成功判据），写一段话解释为什么。

4. 挑一个你熟悉的生产级智能体工作流。估算按工具调用数计的中位轨迹长度，乘以你对每步可靠度的最佳猜测。得到的端到端数字，对你的用户诚实吗？

5. 读 2026 年《International AI Safety Report》中关于评估情境博弈的章节。设计一个评估协议，使其对「模型在测试中与部署中表现不同」这件事保持稳健。

> Set per-step reliability to 0.995. What trajectory length still clears 50% end-to-end reliability? Compare to 0.99 and 0.999. Per-step reliability has exponential consequences at scale.

## Key Terms · 术语表

| 术语 | 人们口头怎么说 | 它实际是什么意思 |
|---|---|---|
| Time horizon | 「它能连续跑多久」 | METR 定义的 50% 可靠度下的人类任务时长，用 logistic 回归拟合 |
| HCAST | 「METR 的任务套件」 | 180+ 个 ML、网络安全、SWE、推理任务，时长从 1 分钟到 8 小时以上 |
| RE-Bench | 「研究工程基准」 | 71 个机器学习研究工程任务，带人类专家基线 |
| Doubling time | 「地平线涨多快」 | 50% 地平线翻倍所需的时间；自 GPT-2 以来拟合值约 7 个月 |
| Trajectory | 「智能体的动作序列」 | 一次运行中工具调用、观察和推理步骤的完整有序列表 |
| Eval-context gaming | 「模型在测试里表现不一样」 | 模型推断出自己正被评估，于是表现得更安全，推高基准分数 |
| Alignment faking | 「重训练之下的表演」 | Anthropic 2024 年的测试中有 12-78% 出现过此现象 |
| Horizon as upper bound | 「METR 数字是天花板」 | 基准地平线假设工具理想、后果为零；真实部署更难 |

## Further Reading · 延伸阅读

- [METR — Measuring AI Ability to Complete Long Tasks](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/) —— 地平线原始论文与方法学。
- [METR Time Horizons benchmark (Epoch AI)](https://epoch.ai/benchmarks/metr-time-horizons) —— 当前数字，更新至 2026 年。
- [Anthropic — Measuring AI agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) —— 对地平线、alignment faking 和部署落差的内部视角。
- [METR — Resources for Measuring Autonomous AI Capabilities](https://metr.org/measuring-autonomous-ai-capabilities/) —— HCAST、RE-Bench、SWAA 套件规格。
- [Anthropic — Claude's Constitution (January 2026)](https://www.anthropic.com/news/claudes-constitution) —— 约束长程 Claude 行为的优先级层级。
