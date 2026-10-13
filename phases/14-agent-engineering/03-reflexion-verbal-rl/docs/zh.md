# Reflexion: Verbal Reinforcement Learning · Reflexion：言语强化学习

> 基于梯度的 RL 需要成千上万次试验和一整个 GPU 集群才能修掉一个失败模式。Reflexion（Shinn et al., NeurIPS 2023）用自然语言做到了这件事：每次失败的试验之后，智能体写一段反思，存进情景记忆，并让下一次试验以这段记忆为条件。这就是 Letta 的 sleep-time compute、Claude Code 的 CLAUDE.md learnings 和 pro-workflow 的 learn-rule 背后的模式。

> Gradient-based RL needs thousands of trials and a GPU cluster to fix a failure mode. Reflexion (Shinn et al., NeurIPS 2023) does it in natural language: after each failed trial, the agent writes a reflection, stores it in episodic memory, and conditions the next trial on that memory. This is the pattern behind Letta's sleep-time compute, Claude Code's CLAUDE.md learnings, and pro-workflow's learn-rule.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 02 (ReWOO)
**Time:** ~60 minutes

---

## Learning Objectives · 学习目标

- 说出 Reflexion 的三个组件（Actor、Evaluator、Self-Reflector）以及情景记忆的角色。
- 用标准库实现一条 Reflexion 循环：二值评估器、反思缓冲区、全新的重试。
- 针对给定任务，在标量、启发式、自我评估三种反馈来源之间做选择。
- 解释为什么言语强化能抓住那些基于梯度的 RL 要几千次试验才能修好的错误。

> Name the three components of Reflexion (Actor, Evaluator, Self-Reflector) and the role of episodic memory.
> Implement a stdlib Reflexion loop with binary evaluator, reflection buffer, and fresh re-attempts.
> Choose between scalar, heuristic, and self-evaluated feedback sources for a given task.
> Explain why verbal reinforcement catches errors that gradient-based RL would need thousands of trials to fix.

---

## The Problem · 问题在哪

一个智能体搞砸了一个任务。在标准 RL 里，你会再跑几千次试验、算梯度、更新权重。昂贵、缓慢，而且大多数生产智能体不可能为每一次失败都准备一份训练预算。

Reflexion（Shinn et al., arXiv:2303.11366）问了另一个问题：如果智能体只是想一想自己为什么失败，然后带着这个想法再试一次呢？不更新权重。没有梯度。只有存在两次试验之间的自然语言。

结果是：在 ALFWorld 上它击败 ReAct 和其他未微调基线。在 HotpotQA 上它优于 ReAct。在代码生成（HumanEval/MBPP）上它创下了当时的最先进水平。全程没有一个梯度步。

> An agent fails a task. In standard RL you would run thousands more trials, compute gradients, update weights. Expensive, slow, and most production agents do not have a training budget for every failure.
> Reflexion (Shinn et al., arXiv:2303.11366) asks a different question: what if the agent just thought about why it failed and tried again with that thought in its prompt? No weight updates. No gradient. Just natural language stored between trials.
> The result: on ALFWorld it beats ReAct and other non-fine-tuned baselines. On HotpotQA it improves over ReAct. On code generation (HumanEval/MBPP) it sets state of the art at the time. All without a single gradient step.

---

## The Concept · 概念

### The three components · 三个组件

```
Actor         : generates a trajectory (ReAct-style loop)
Evaluator     : scores the trajectory — binary, heuristic, or self-eval
Self-Reflector: writes a natural-language reflection on the failure
```

外加一个数据结构：

```
Episodic memory: list of prior reflections, prepended to the next trial's prompt
```

一次试验运行 Actor。Evaluator 打分。如果分数低，Self-Reflector 产出一段反思（「我选错了工具，因为我把问题误读成在问 X，而它其实在问 Y」）。反思进入情景记忆。下一次试验从零开始，但能看到那段反思。

> One trial runs the Actor. Evaluator scores it. If the score is low, Self-Reflector produces a reflection ("I picked the wrong tool because I misread the question as asking about X when it was asking about Y"). The reflection goes into episodic memory. Next trial starts fresh but sees the reflection.

---

### Three evaluator types · 三种评估器

1. **标量（Scalar）** —— 外部二值信号。ALFWorld 成功或失败。HumanEval 测试通过或失败。最简单，信号最强。
2. **启发式（Heuristic）** —— 预定义的失败特征。「如果智能体连续两次产生同一动作，标记为卡住。」「如果轨迹超过 50 步，标记为低效。」
3. **自我评估（Self-evaluated）** —— LLM 给自己的轨迹打分。在没有 ground truth 时需要它。信号较弱；与工具锚定的验证（第 5 课——CRITIC）搭配效果好。

2026 年的默认做法是混合使用：有标量就用标量，没有就用自我评估，启发式当安全护栏。

> 1. **Scalar** — an external binary signal. ALFWorld succeeds or fails. HumanEval tests pass or fail. Simplest, highest-signal.
> 2. **Heuristic** — predefined failure signatures. "If the agent produced the same action twice in a row, mark as stuck." "If the trajectory exceeds 50 steps, mark as inefficient."
> 3. **Self-evaluated** — the LLM scores its own trajectory. Needed when no ground truth is available. Weaker signal; pairs well with tool-grounded verification (Lesson 05 — CRITIC).
>
> The 2026 default is a mix: scalar when available, self-eval when not, heuristics as safety rails.

---

### Why this generalizes · 为什么它能推广

Reflexion 与其说是一个新算法，不如说是一个被命名的模式。几乎所有生产级「自愈」智能体都在跑它的某种变体：

- Letta 的 sleep-time compute（第 8 课）：一个独立的智能体反思过去的对话并写入记忆块。
- Claude Code 的 `CLAUDE.md` /「save memory」模式：反思被捕获为 learnings，前置到未来的会话。
- pro-workflow 的 `/learn-rule` 命令：纠正被捕获为显式规则。
- LangGraph 的 reflection 节点：一个给输出打分、并在需要时路由到 refine 的节点。

全都源自同一个洞见：自然语言是一种足够丰富的媒介，可以在多次运行之间承载「我从这次失败中学到了什么」。

> Reflexion is not a new algorithm so much as a named pattern. Almost every production "self-healing" agent runs some variant:
> - Letta's sleep-time compute (Lesson 08): a separate agent reflects on past conversations and writes to memory blocks.
> - Claude Code's `CLAUDE.md` / "save memory" pattern: reflections captured as learnings, prepended to future sessions.
> - pro-workflow's `/learn-rule` command: corrections captured as explicit rules.
> - LangGraph's reflection nodes: a node that scores output and routes to refine if needed.
>
> All derive from the same insight: natural language is a rich-enough medium to carry "what I learned from failure" between runs.

---

### When it works and when it does not · 什么时候有效，什么时候无效

Reflexion 在以下情况有效：

- 有清晰的失败信号（测试失败、工具错误、答案错误）。
- 任务类别可复现（同一类问题可以再问一次）。
- 反思有空间在轨迹之上做出改进（足够的行动预算）。

Reflexion 在以下情况没有帮助：

- 智能体第一次尝试就成功了。
- 失败是外部的（网络断了、工具坏了）——对「网络断了」的反思帮不到未来的运行。
- 反思变成迷信——存下一段关于某次偶发抽风的叙事。

2026 年的坑：记忆腐烂（memory rot）。反思不断累积；有些已经过时或错误；随着情景缓冲区变大，重跑越来越慢。缓解办法：周期性压缩（第 6 课）、给反思设 TTL，或者一个独立的 sleep-time 清理智能体（Letta）。

> Reflexion works when: there is a clear failure signal (test failure, tool error, wrong answer); the task class is reproducible (the same type of question can be asked again); the reflection has room to improve on the trajectory (enough action budget).
> Reflexion does not help when: the agent already succeeds on the first try; the failure is external (network down, tool broken) — reflection on "the network was down" does not help future runs; the reflection turns into superstition — storing a narrative about a one-off flaky run.
> 2026 pitfall: memory rot. Reflections accumulate; some are obsolete or wrong; re-runs get slower as the episodic buffer grows. Mitigation: periodic compaction (Lesson 06), TTL on reflections, or a separate sleep-time cleanup agent (Letta).

```figure
react-trace
```

---

## Build It · 动手造

`code/main.py` 在一个玩具谜题上实现 Reflexion：产出一个三个元素的列表，使其和等于目标值。Actor 发出候选列表；Evaluator 检查和；Self-Reflector 写一行关于哪里出了问题的诊断。反思进入情景记忆，供下一次试验使用。

组件：

- `Actor` —— 一个脚本化策略，看到反思后会改进。
- `Evaluator.binary()` —— 对目标 sum 做通过/失败判定。
- `SelfReflector` —— 为失败生成一行诊断。
- `EpisodicMemory` —— 带 TTL 语义的有界列表。

跑起来：

```
python3 code/main.py
```

轨迹展示了三次试验。第 1 次失败，一段反思被存储，第 2 次看到反思并有所改进但仍失败，第 3 次成功。与基线运行（无反思）对比——它一直卡死在第 1 次试验的答案上。

> `code/main.py` implements Reflexion on a toy puzzle: produce a 3-element list that sums to a target. The Actor emits candidate lists; the Evaluator checks the sum; the Self-Reflector writes a line about what went wrong. The reflection goes into episodic memory for the next trial.
> The trace shows three trials. Trial 1 fails, a reflection is stored, trial 2 sees the reflection and improves but still fails, trial 3 succeeds. Compare with a baseline run (no reflection) — it stays stuck at trial 1's answer.

---

## Use It · 实战用法

LangGraph 以节点模式内置 reflection。Claude Code 的 `/memory` 命令和 pro-workflow 的 `/learn-rule` 把情景缓冲区外化成一个 markdown 文件。Letta 的 sleep-time compute 在空闲期运行 Self-Reflector，让主智能体保持低延迟。OpenAI Agents SDK 不直接提供 Reflexion；你要用一个按分数拒绝轨迹的自定义 Guardrail，外加一个跨运行存活的记忆 `Session` 来搭建它。

> LangGraph ships reflection as a node pattern. Claude Code's `/memory` command and pro-workflow's `/learn-rule` externalize the episodic buffer as a markdown file. Letta's sleep-time compute runs the Self-Reflector on downtime so the primary agent stays latency-bound. OpenAI Agents SDK does not ship Reflexion directly; you build it with a custom Guardrail that rejects trajectories by score and a memory `Session` that survives across runs.

---

## Ship It · 交付

`outputs/skill-reflexion-buffer.md` 创建并维护一个带反思捕获、TTL 和去重的情景缓冲区。给定任务类别和一次失败，它产出一段对下一次试验真正有帮助的反思（而不是一句泛泛的「下次小心点」）。

> `outputs/skill-reflexion-buffer.md` creates and maintains an episodic buffer with reflection capture, TTL, and deduplication. Given a task class and a failure, it emits a reflection that actually helps the next trial (not a generic "be more careful").

---

## Exercises · 练习

1. 把二值评估器换成返回距离度量（离目标还有多远）的标量评估器。收敛会更快吗？
2. 给反思加一个 10 次试验的 TTL。过了那个点之后，更老的反思是帮了忙还是帮了倒忙？
3. 实现启发式评估器：如果同一动作重复出现，就把该次试验标记为卡住。这会如何与 Self-Reflector 互动？
4. 用一个无视反思的对抗性 Actor 跑 Reflexion。要让 Actor 注意到反思，最少需要多少反思提示词工程？
5. 读 Reflexion 论文第 4 节关于 AlfWorld 的内容。在概念上复现 130% 的成功率提升：相对原味 ReAct 的关键差异是什么？

> 1. Switch from binary to scalar evaluator that returns a distance metric (how far from target). Does it converge faster?
> 2. Add a TTL of 10 trials to reflections. Do older reflections hurt or help after that point?
> 3. Implement heuristic evaluator: mark the trial as stuck if the same action repeats. How does this interact with Self-Reflector?
> 4. Run Reflexion with an adversarial Actor that ignores reflections. What is the minimum reflection prompt engineering that forces the Actor to notice them?
> 5. Read Section 4 of the Reflexion paper on AlfWorld. Reproduce the 130% success-rate improvement conceptually: what is the key delta vs vanilla ReAct?

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Reflexion | 「自我纠正」 | Shinn et al. 2023 —— Actor、Evaluator、Self-Reflector 外加情景记忆 |
| Verbal reinforcement | 「无梯度学习」 | 以自然语言写成的反思，前置到下一次试验的提示词 |
| Episodic memory | 「按任务存放的反思」 | 针对某一任务类的有界反思缓冲区 |
| Scalar evaluator | 「二值成功信号」 | 来自 ground truth 的通过/失败或数值打分 |
| Heuristic evaluator | 「基于模式的检测器」 | 预定义的失败特征（如卡死循环、步数过多） |
| Self-evaluator | 「LLM 当自己的裁判」 | 没有 ground truth 时的低信号兜底——应搭配工具锚定的验证 |
| Memory rot | 「过时的反思」 | 情景缓冲区被失效条目填满；用压缩/TTL 修复 |
| Sleep-time reflection | 「异步自我反思」 | 把 Self-Reflector 挪到热路径之外跑，主智能体保持快速 |

> | Term | What people say | What it actually means |
> |------|----------------|------------------------|
> | Reflexion | "Self-correction" | Shinn et al. 2023 — Actor, Evaluator, Self-Reflector plus episodic memory |
> | Verbal reinforcement | "Learning without gradients" | Natural-language reflection prepended to the next trial's prompt |
> | Episodic memory | "Per-task reflections" | Bounded buffer of prior reflections for one task class |
> | Scalar evaluator | "Binary success signal" | Pass/fail or numeric score from ground truth |
> | Heuristic evaluator | "Pattern-based detector" | Predefined failure signatures (e.g. stuck-loop, too-many-steps) |
> | Self-evaluator | "LLM-as-judge on own trace" | Lower-signal fallback when no ground truth — pair with tool-grounded verification |
> | Memory rot | "Stale reflections" | Episodic buffer fills with obsolete entries; fix with compaction/TTL |
> | Sleep-time reflection | "Async self-reflection" | Run Self-Reflector off the hot path so primary agent stays fast |

---

## Further Reading · 延伸阅读

- [Shinn et al., Reflexion: Language Agents with Verbal Reinforcement Learning (arXiv:2303.11366)](https://arxiv.org/abs/2303.11366) —— 规范论文
- [Letta, Sleep-time Compute](https://www.letta.com/blog/sleep-time-compute) —— 生产环境中的异步反思
- [Anthropic, Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) —— 把情景缓冲区当作上下文的一部分来管理
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) —— reflection 节点模式

> - [Shinn et al., Reflexion: Language Agents with Verbal Reinforcement Learning (arXiv:2303.11366)](https://arxiv.org/abs/2303.11366) — the canonical paper
> - [Letta, Sleep-time Compute](https://www.letta.com/blog/sleep-time-compute) — async reflection in production
> - [Anthropic, Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — managing the episodic buffer as part of context
> - [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) — reflection node pattern
