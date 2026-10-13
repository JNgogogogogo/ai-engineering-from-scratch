# Failure Modes: Why Agents Break · 失败模式：智能体为何失效

MASFT（伯克利，2025）把多智能体失败归纳为 3 大类 14 种模式。微软的分类学记录了既有 AI 失败在智能体场景下如何被放大。业界实地数据收敛到五种反复出现的模式：幻觉动作（hallucinated actions）、范围蔓延（scope creep）、级联错误（cascading errors）、上下文丢失（context loss）、工具误用（tool misuse）。

> MASFT (Berkeley, 2025) catalogs 14 multi-agent failure modes in 3 categories. Microsoft's Taxonomy documents how existing AI failures amplify in agentic settings. Industry field data converges on five recurring modes: hallucinated actions, scope creep, cascading errors, context loss, tool misuse.

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 05 (Self-Refine and CRITIC), Phase 14 · 24 (Observability)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 说出 MASFT 的三大失败类别，以及每类中至少四种具体模式。
- 解释为什么智能体化（agentic）会放大既有 AI 失败模式（偏见、幻觉）。
- 描述业界反复出现的五种模式及其缓解手段。
- 实现一个 stdlib 检测器，给智能体轨迹（trace）打上失败模式标签。

> Name MASFT's three failure categories and at least four specific modes in each.
> Explain why agentic failure amplifies existing AI failure modes (bias, hallucination).
> Describe the five industry-recurring modes and their mitigations.
> Implement a stdlib detector that tags agent traces with failure-mode labels.

## The Problem · 问题在哪

团队交付的智能体在 90% 的轨迹上正常工作。剩下 10% 的失败不是随机噪声——它们落在少数几个反复出现的类别里。一旦你能叫出它们的名字，你就能监控它们、修复它们。

> Teams ship agents that work on 90% of traces. The 10% failures are not random noise — they fall into a small number of recurring categories. Once you can name them, you can monitor for them and fix them.

## The Concept · 概念

### MASFT (Berkeley, arXiv:2503.13657) · MASFT 失败分类学

多智能体系统失败分类学（Multi-Agent System Failure Taxonomy）。14 种失败模式聚成 3 大类。标注者间 Cohen's Kappa 达 0.88——这些类别是可靠可分的。

核心论断：这些失败是多智能体系统的基本设计缺陷，而不是等着更强的底座模型来修的 LLM 局限。

> Multi-Agent System Failure Taxonomy. 14 failure modes clustered into 3 categories. Inter-annotator Cohen's Kappa 0.88 — the categories are reliably distinguishable.
> Central claim: failures are fundamental design flaws in multi-agent systems, not LLM limitations to be fixed with better base models.

### Microsoft Taxonomy of Failure Mode in Agentic AI Systems · 微软智能体 AI 失败模式分类

- 既有 AI 失败（偏见、幻觉、数据泄露）在智能体场景中被放大。
- 自主性带来新的失败：大规模的意外动作、工具误用、使命漂移（mission drift）。
- 这份白皮书就是智能体产品的风险登记册（risk register）。

> Existing AI failures (bias, hallucination, data leakage) amplify in agentic settings.
> New failures emerge from autonomy: unintended action at scale, tool misuse, mission drift.
> The whitepaper is the risk register for agentic products.

### Characterizing Faults in Agentic AI (arXiv:2603.06847) · 智能体故障的特征刻画

- 失败源自编排（orchestration）、内部状态演化和环境交互。
- 而不只是「代码写得差」或「模型输出差」。

> Failures arise from orchestration, internal state evolution, and environment interaction.
> Not just "bad code" or "bad model output."

### LLM Agent Hallucinations Survey (arXiv:2509.18970) · LLM 智能体幻觉综述

两种主要表现：

1. **指令遵循偏差（Instruction-following Deviation）**——智能体不遵循系统提示。
2. **长程上下文误用（Long-range Contextual Misuse）**——智能体遗忘或误用早前轮次的上下文。

子意图错误（sub-intention errors）：遗漏（omission，漏了步骤）、冗余（redundancy，重复步骤）、乱序（disorder，步骤顺序错乱）。

> Two primary manifestations: Instruction-following Deviation — agent doesn't follow the system prompt... Long-range Contextual Misuse — agent forgets or misapplies context from earlier turns.
> Sub-intention errors: Omission (missed step), Redundancy (repeated step), Disorder (out-of-order steps).

### The five industry-recurring modes · 业界反复出现的五种模式

Arize、Galileo、NimbleBrain 在 2024-2026 的实地分析收敛到：

1. **幻觉动作（hallucinated actions）。** 智能体调用不存在的工具，或编造参数。
2. **范围蔓延（scope creep）。** 智能体把任务扩大到用户要求之外（多建 PR、多发邮件）。
3. **级联错误（cascading errors）。** 一次错误调用触发下游连锁反应。一个幽灵 SKU 幻觉触发四个 API 调用——变成跨系统事故。
4. **上下文丢失（context loss）。** 长程任务忘记早前轮次的约束。
5. **工具误用（tool misuse）。** 用错误的参数调用正确的工具，或干脆调用了错误的工具。

级联错误是最致命的。智能体分不清「我失败了」和「任务不可能完成」，还经常在 400 错误上幻觉出一条成功消息来收尾。

> Hallucinated actions. Agent invokes a tool that doesn't exist or fabricates arguments.
> Cascading errors. One wrong call triggers downstream effects. A phantom SKU hallucination triggers four API calls — a multi-system incident.
> Cascading is the killer. Agents cannot distinguish "I failed" from "the task is impossible" and often hallucinate a success message on 400 errors to close the loop.

### Mitigation: gates at every step · 缓解：每一步都设验证门

在推理链的每一步部署自动验证门（verification gate），对照环境状态核查事实根据。具体做法：

- 每步安全分类器（第 21 课）。
- 工具调用参数校验（第 06 课）。
- 将检索内容与已知事实交叉核对（第 05 课，CRITIC）。
- 通过重新探测状态来检测成功幻觉（文件真的创建了吗？）。

> Automated verification gates at every step of a reasoning chain, checking factual grounding against environment state.
> Detect success hallucination by re-probing state (was the file actually created?).

### Where failure monitoring goes wrong · 失败监控哪里会出错

- **只给崩溃打标。** 大多数智能体失败产生的是看起来有效的输出。需要内容级检查。
- **没有基线（baseline）。** 漂移检测需要一个「最后已知良好」；没有它，你就说不出「情况正在变糟」。
- **告警过量。** 每个失败都发一次呼叫。做聚类和限频。

> Tagging only crashes. Most agent failures produce valid-looking output. Need content-level checks.
> No baseline. Drift detection needs a last-known-good; without it you cannot say "this is getting worse."
> Over-alerting. Every failure produces a page. Cluster and rate-limit.

```figure
failure-cascade
```

## Build It · 动手造

`code/main.py` 实现一个 stdlib 失败模式标注器：

- 一份覆盖五种模式的合成轨迹数据集。
- 每种模式一个检测函数（针对工具调用、输出、重复动作的特征模式）。
- 一个标注器：给每条轨迹打标签并报告模式分布。

运行：

```
python3 code/main.py
```

输出：每条轨迹的标签 + 聚合分布，是 Phoenix 轨迹聚类能力的一个低成本复刻。

> Detector functions per mode (signature patterns on tool calls, outputs, repeat actions).
> Output: per-trace labels + aggregate distribution, a cheap reproduction of what Phoenix's trace clustering surfaces.

## Use It · 实战用法

- **Phoenix** 用于生产漂移聚类（第 24 课）。
- **Langfuse** 用于会话回放 + 人工标注。
- **自研** 用于可观测性平台检测不到的领域特定特征。

> Phoenix for production drift clustering (Lesson 24).
> Langfuse for session replay + annotation.
> Custom for domain-specific signatures your observability platform can't detect.

## Ship It · 交付

`outputs/skill-failure-detector.md` 生成贴合你领域的失败模式检测器，并接入轨迹存储。

> `outputs/skill-failure-detector.md` generates failure-mode detectors tailored to your domain, wired to a trace store.

## Exercises · 练习

1. 加一个「成功幻觉」检测器：智能体返回成功，但目标状态没有变化。
2. 从你做过的产品里取 100 条真实轨迹打标。哪种模式占主导？修好它的成本是多少？
3. 实现一个「级联半径」指标：给定第 N 步的一个失败，它影响了多少下游步骤？
4. 阅读 MASFT 的 14 种失败模式。挑出适用于你产品的三种，为它们写检测器。
5. 把一个检测器接进 CI 任务：如果 ≥5% 的轨迹命中某种模式，就让构建失败。

> Add a detector for "success hallucination": agent returns success but the target state is unchanged.
> Implement a "cascade radius" metric: given a failure at step N, how many downstream steps did it affect?
> Wire one detector into a CI job: fail the build if >=5% of traces tag a mode.

## Key Terms · 术语表

| Term 术语 | What people say 大家怎么说 | What it actually means 实际含义 |
|------|------------------------|------------------------|
| MASFT | 「多智能体失败分类学」 | 伯克利的 14 模式分类法 |
| Cascading error（级联错误） | 「涟漪式失败」 | 早期的一个错误沿 N 步传播 |
| Context loss（上下文丢失） | 「忘了约束」 | 长程任务丢掉了早前轮次的事实 |
| Tool misuse（工具误用） | 「工具错 / 参数错」 | 调用合法，调用方式错误 |
| Success hallucination（成功幻觉） | 「伪造完成」 | 智能体对着 400 宣布成功；状态未变 |
| Scope creep（范围蔓延） | 「越界」 | 智能体做了超出要求的事 |
| Instruction-following deviation（指令遵循偏差） | 「不听话」 | 无视系统提示或用户约束 |
| Sub-intention errors（子意图错误） | 「计划 bug」 | 计划执行中的遗漏、冗余、乱序 |

## Further Reading · 延伸阅读

- [Cemri et al., MASFT (arXiv:2503.13657)](https://arxiv.org/abs/2503.13657) —— 14 种失败模式、3 大类别
- [Microsoft, Taxonomy of Failure Mode in Agentic AI Systems](https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Taxonomy-of-Failure-Mode-in-Agentic-AI-Systems-Whitepaper.pdf) —— 风险登记册
- [Arize Phoenix](https://docs.arize.com/phoenix) —— 漂移聚类的实战落地
- [Anthropic, Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) —— 更简单的模式如何让这些失败模式根本不出现
