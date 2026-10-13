# Theory of Mind and Emergent Coordination · 心智理论与涌现协调

> Li et al. (arXiv:2310.10701) showed that LLM agents in a cooperative text game exhibit **emergent high-order Theory of Mind** (ToM) — reasoning about what another agent believes about a third agent's beliefs — but fail on long-horizon planning due to context management and hallucination. Riedl (arXiv:2510.05174) measured higher-order synergy across a population and found that **only** the ToM-prompt condition produces identity-linked differentiation and goal-directed complementarity; lower-capacity LLMs show only spurious emergence. That is, coordination emergence is prompt-conditional and model-dependent, not free. This lesson implements a minimal ToM-aware agent, runs a cooperative task with and without ToM prompting, and measures the coordination delta against the Riedl 2025 protocol.

Li 等人（arXiv:2310.10701）发现：在合作式文字游戏中，LLM 智能体会表现出**涌现的高阶心智理论**（Theory of Mind，ToM）—— 能推理「另一个智能体对第三个智能体信念所持的信念」—— 但受制于上下文管理与幻觉，它们在长程规划上会失败。Riedl（arXiv:2510.05174）在群体层面测量了高阶协同（higher-order synergy），发现**只有** ToM 提示条件才能产生身份绑定的角色分化与目标导向的互补性；能力较低的 LLM 只会表现出虚假的涌现。也就是说，协调的涌现是有提示条件的、依赖具体模型的，不是白来的。本课实现一个最小的 ToM 感知智能体，在开启与关闭 ToM 提示两种条件下运行合作任务，并按照 Riedl 2025 的协议测量协调差值。

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 16 · 07 (Society of Mind and Debate), Phase 16 · 17 (Generative Agents)
**Time:** ~75 minutes

## Problem · 问题

多智能体协调常常看起来很神奇：智能体分工、互相预判、避免重复。但这种「涌现」通常只是提示工程的产物 —— 某个人在提示里告诉智能体要「协调」。去掉提示，协调就没了。

Riedl 2025 年的结论更严格：在受控条件下，只有当智能体被提示去推理**其他智能体的心智**（ToM）时，协调才会涌现。没有 ToM 提示时，即便是强模型，表现出的协调模式也经不起统计控制的检验。这对生产环境很重要：很多团队上线的「多智能体协调」功能其实是依赖提示的、脆弱的。

本课把 ToM 当作一种具体能力（关于「信念的信念」的推理）来对待，构建一个最小的 ToM 感知智能体，并测量：真实的协调长什么样，提示包装出来的协调又长什么样。

> Multi-agent coordination often looks magical: agents divide labor, anticipate each other, avoid redundancy. Usually this "emergence" is an artifact of prompt engineering — someone told the agents to "coordinate." Remove the prompt, remove the coordination.
> Riedl's 2025 finding is stricter: under controlled conditions, coordination only emerges when agents are prompted to reason about **other agents' minds** (ToM). Without the ToM prompt, even strong models show coordination patterns that do not survive statistical controls. This matters for production: teams ship "multi-agent coordination" features that are prompt-dependent and brittle.
> This lesson treats ToM as a specific capability (reasoning about beliefs about beliefs), builds a minimal ToM-aware agent, and measures what real coordination looks like vs. what prompt dressing looks like.

## Concept · 概念

### What ToM means · ToM 是什么意思

发展心理学：3 岁的孩子认为任何人的内心世界都和自己一样。5 岁的孩子能理解别人有不同的信念。7 岁的孩子能推理「信念的信念」（「她认为我认为球在杯子下面」）。这分别是零阶、一阶、二阶 ToM。

对 LLM 智能体来说，ToM 阶数对应于：

- **零阶：** 对他人没有建模。智能体只根据自己的观察行动。
- **一阶：** 智能体对每个其他智能体的信念有建模。「Alice 相信 X。」
- **二阶：** 智能体建模递归信念。「Alice 认为 Bob 相信 X。」

Li 等人 2023 年发现：在合作游戏中，LLM 智能体能涌现出一阶和二阶 ToM，但随着时间跨度变长和通信变得不可靠，它们会退化。

> Developmental psychology: a 3-year-old thinks anyone's inner world matches theirs. A 5-year-old understands others have different beliefs. A 7-year-old reasons about beliefs about beliefs ("she thinks that I think the ball is under the cup"). These are zeroth, first, and second-order ToM.
> Li et al. 2023 found that first- and second-order ToM emerge in LLM agents in cooperative games but degrade with long horizon and unreliable communication.

### The Sally-Anne test, in brief · Sally-Anne 测试简介

一个 1985 年的错误信念测试（false-belief test）：Sally 把一颗弹珠放进篮子 A，然后离开。Anne 把它移到了篮子 B。Sally 回来后会在哪里找？具有一阶 ToM 的孩子会说篮子 A（Sally 的信念与现实不同）。没有的孩子会说篮子 B。

GPT-4 时代的 LLM 在直白表述的 Sally-Anne 式测试上能够通过。但当叙事变长、场景多次变化、或问题表述很间接时，它们会失败。这就是 2026 年生产级 LLM 在 ToM 上的实际水平。

> A 1985 false-belief test: Sally puts a marble in basket A, leaves. Anne moves it to basket B. Where will Sally look when she returns? A child with first-order ToM says basket A (Sally's belief differs from reality). A child without says basket B.
> GPT-4-era LLMs pass Sally-Anne-style tests when posed plainly. They fail when the narrative is long, the scene changes several times, or the question is phrased indirectly. That is the practical 2026 state of ToM in production LLMs.

### Riedl's coordination measurement · Riedl 的协调测量

Riedl（arXiv:2510.05174）构建了一个群体规模的测试：N 个智能体、一个合作目标、可变的提示条件。测量：

1. **身份绑定的角色分化（identity-linked differentiation）。** 智能体是否会随时间形成稳定的角色区分？
2. **目标导向的互补性（goal-directed complementarity）。** 智能体的动作是互补（不同子任务）还是重复？
3. **高阶协同（higher-order synergy）。** 一个统计量，衡量群体是否达成了任何子集都无法达成的结果。

结果：只有在 ToM 提示条件下，这三个指标才会产生高于基线的信号。没有 ToM 提示时，中等能力模型的指标在随机水平附近徘徊。大模型在无显式 ToM 提示下会表现出一些协调，但效果比显式提示时小。

> Riedl (arXiv:2510.05174) built a population-scale test: N agents, a cooperative objective, variable prompt conditions. Measure: identity-linked differentiation, goal-directed complementarity, higher-order synergy.
> Result: only under the ToM prompt condition do all three metrics produce signal above baseline. Without ToM prompting, metrics hover near chance for moderate-capacity models. Large models show some coordination without explicit ToM prompting but the effect is smaller than with explicit prompting.

### The coordination illusion · 协调错觉

没有统计控制时，演示里的「涌现协调」往往反映的是：

- 把协调烘焙进提示的提示工程（系统提示里写着「要合作」）。
- 观察者偏差（我们看到自己期待的模式）。
- 事后挑选成功的运行。

宣传「涌现协调」却拿不出可测量信号的生产系统，应当当作营销话术。先测量，再宣称。

> Without statistical controls, "emergent coordination" in demos often reflects: prompt engineering that bakes in coordination (system prompts that say "work together"); observer bias (we see patterns we expect); post-hoc selection of successful runs.
> Production systems that market "emergent coordination" without measurable signal should be treated as marketing. Measure before claiming.

### A minimal ToM-aware agent · 最小的 ToM 感知智能体

结构：

```
agent state:
  own_beliefs:    {facts the agent believes}
  other_models:   {other_agent_id -> {beliefs_the_agent_attributes_to_them}}
  actions_last_N: [history of others' actions]

observation update:
  - update own_beliefs from direct observation
  - update other_models[agent_id] from their action + prior beliefs

action selection:
  - enumerate candidate actions
  - for each, predict what each other agent will do next given their modeled beliefs
  - pick action that maximizes joint outcome under those predictions
```

`other_models` 属性就是 ToM 状态。一阶 ToM 只保留一层。二阶再加上 `other_models[i][other_models_of_j]` —— 我认为智能体 i 认为智能体 j 所相信的东西。

> The `other_models` attribute is the ToM state. First-order ToM keeps just one level. Second-order adds `other_models[i][other_models_of_j]` — what I think agent i thinks agent j believes.

### Why long-horizon hurts · 为什么长程会退化

Li 等人记录到：上下文限制导致智能体忘记哪条信念属于谁。幻觉会把虚假信念加进其他智能体的模型。两者都会产生「我以为他认为 X」这类错误，并随时间复利式累积。

论文以及 2024-2026 年后续工作记录的缓解手段：

- **在提示里放显式 ToM 状态。** 结构化格式：`{agent_id: belief_list}`。强制检索保持「身份-信念」绑定。
- **更短的推理链。** 每轮更少的 ToM 更新，减少幻觉的复利累积。
- **外部 ToM 存储。** 把模型维护在 LLM 上下文之外；每轮只注入相关部分。

> Li et al. document: context limits cause agents to forget which belief belongs to whom. Hallucination adds false beliefs to other-agent models. Both produce "I thought he thought X" errors that compound over time.
> Mitigations documented in the paper and in 2024-2026 follow-ups: explicit ToM state in the prompt (structured format: `{agent_id: belief_list}`); shorter reasoning chains; an external ToM store injected per turn.

### Where ToM fails in production · ToM 在生产中的失灵场景

- **对抗环境。** ToM 好的智能体更容易被操纵（你可以建模它对你的建模，然后加以利用）。
- **异构团队。** 模型不同时，对某个对手有效的 ToM 模型无法泛化。
- **依赖事实真值的任务。** ToM 关乎信念；如果正确性取决于事实，ToM 反而是一种干扰。

> Adversarial settings: agents with good ToM are easier to manipulate (you can model what they model of you, then exploit). Heterogeneous teams: when models are different, the ToM model that works for one opponent does not generalize. Ground-truth-dependent tasks: ToM is about beliefs; if correctness depends on facts, ToM can be a distraction.

### The coordination you can actually measure · 真正可测量的协调

三个实用信号，用来判断一个团队的协调是真实的而非提示包装的：

1. **随时间的互补性。** 在多轮任务中，智能体的动作是否覆盖互不重叠的子任务？
2. **预判。** 智能体 A 在第 T+1 轮的动作，是否依赖于一个对「B 在第 T+2 轮动作」的预测，而这个预测后来被证实是对的？
3. **纠正。** 当 A 在第 T 轮误读 B 的信念时，A 会在第 T+2 轮之前纠正吗？

这些在带日志的多智能体系统里都是可测量的。它们是「协调」叙事的实质版本。

> Three practical signals a team's coordination is real rather than prompt-dressed: complementarity over time, anticipation, and correction. These are measurable in a logged multi-agent system. They are the substantive version of the "coordination" narrative.

```figure
sw-theory-of-mind
```

## Build It · 动手造

`code/main.py` 实现：

- `ToMAgent` —— 跟踪自身信念以及每个其他智能体的信念模型。
- 一个合作任务：三个智能体要从三个盒子里收集三个代币；每个盒子只能放一个代币。智能体之间无法通信，只能从彼此的动作推断意图。
- 两种配置：`zeroth_order`（无 ToM）和 `first_order`（带一层信念模型的 ToM）。
- 200 次随机试验上的测量：完成率、重复率（两个智能体盯上同一个盒子）、平均完成轮数。

运行：

```
python3 code/main.py
```

预期输出：零阶智能体以约 35% 的比率重复劳动，10 轮内完成约 60% 的试验。一阶 ToM 智能体重复率约 5%，完成率约 95%。这个差值就是可测量的协调效应。

> Expected output: zeroth-order agents duplicate effort at ~35% rate and complete ~60% of trials in 10 turns. First-order ToM agents duplicate at ~5% and complete ~95%. The delta is the measurable coordination effect.

## Use It · 实战用法

`outputs/skill-tom-auditor.md` 是一个审计多智能体系统「涌现协调」声明的技能。检查提示包装、相对于对照的统计显著性、以及实测的互补性。

> `outputs/skill-tom-auditor.md` is a skill that audits a multi-agent system's claim of "emergent coordination." Checks for prompt dressing, statistical significance against a control, and measured complementarity.

## Ship It · 交付

协调声明检查清单：

- **对照条件。** 一个去掉协调提示的系统版本。两者都测量。
- **统计检验。** 系统与对照在你的指标上的差异是否在 `p < 0.05` 上显著？
- **互补性度量。** 随时间的动作不重叠度，而不只是最终成功。
- **失败案例日志。** 智能体协调失败时，ToM 状态长什么样？
- **模型能力披露。** 如果效果在更小的模型上消失，要明说。

> Coordination claims checklist: control condition, statistical test, complementarity measure, failure-case log, and model-capacity disclosure. If the effect vanishes on smaller models, say so.

## Exercises · 练习

1. 运行 `code/main.py`。确认一阶 ToM 把重复率降低约 7 倍。扩展到 5 个智能体和 5 个盒子时，差距还在吗？
2. 实现二阶 ToM（智能体 A 建模 B 对 C 的看法）。它比一阶有提升吗？在什么任务上？
3. 向 ToM 状态注入**幻觉**：每轮随机翻转一条信念。一阶性能退化多少？
4. 阅读 Li 等人（arXiv:2310.10701）。复现「长程退化」发现：当轮数从 10 增长到 30 时，你的一阶 ToM 性能如何变化？
5. 阅读 Riedl 2025（arXiv:2510.05174）。在你的仿真日志上实现高阶协同统计量。无 ToM 提示条件下这个效应还存在吗？

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Theory of Mind | 「理解他人的心智」 | 对另一个智能体的信念建模的能力。按阶数分级（0、1、2+）。 |
| Sally-Anne test | 「错误信念测试」 | 1985 年发展心理学实验；LLM 能通过直白版本，复杂版本会失败。 |
| First-order ToM | 「A 相信 X」 | 对一个他人的事实信念建模。 |
| Second-order ToM | 「A 认为 B 相信 X」 | 递归建模再深一层。 |
| Identity-linked differentiation | 「角色随时间保持稳定」 | Riedl 的指标：角色是持久的，不是随机的。 |
| Goal-directed complementarity | 「动作互不重叠」 | 智能体瞄准不同的子任务，而不是同一个。 |
| Higher-order synergy | 「群体超过任何子集」 | Riedl 用于判定真实协调的统计量。 |
| Coordination illusion | 「看起来很协调」 | 没有可测量信号、由提示包装出来的协调表象。 |

## Further Reading · 延伸阅读

- [Li et al. — Theory of Mind for Multi-Agent Collaboration via Large Language Models](https://arxiv.org/abs/2310.10701) — 合作游戏中的涌现 ToM；长程失败模式
- [Riedl — Emergent Coordination in Multi-Agent Language Models](https://arxiv.org/abs/2510.05174) — 群体规模测量；ToM 提示是承重条件
- [Premack & Woodruff — Does the chimpanzee have a theory of mind?](https://www.cambridge.org/core/journals/behavioral-and-brain-sciences/article/does-the-chimpanzee-have-a-theory-of-mind/1E96B02CD9850E69AF20F81FA7EB3595) — ToM 概念的 1978 年起源
- [Baron-Cohen, Leslie, Frith — Does the autistic child have a theory of mind?](https://doi.org/10.1016/0010-0277(85)90022-8) — Sally-Anne 论文（1985）
