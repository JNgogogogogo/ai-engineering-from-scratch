# Eval-Driven Agent Development · 评估驱动的智能体开发

Anthropic 的建议：「从简单的提示词开始，用全面的评估来优化它们，只在需要时才引入多步智能体系统。」评估不是最后一步。它是驱动 Phase 14 里所有其他选择的外层循环。

> Anthropic's guidance: "start with simple prompts, optimize them with comprehensive evaluation, and add multi-step agentic systems only when needed." Evaluation is not the last step. It's the outer loop that drives every other choice in Phase 14.

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** All of Phase 14.
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 说出三个评估层——静态基准（static benchmarks）、自定义离线评估（custom offline）、线上生产评估（online production）——以及各自用来做什么。
- 解释 evaluator-optimizer 紧密循环。
- 描述 2026 年的最佳实践：评估与代码同库存放、在 CI 里运行、为 PR 把关。
- 把 Phase 14 的每一课连接到它生成的评估用例。

> Name the three evaluation layers — static benchmarks, custom offline, online production — and what each is for.
> Explain the evaluator-optimizer tight loop.
> Describe the 2026 best practice: evals live next to code, run in CI, gate PRs.
> Connect every Phase 14 lesson to the eval case it generates.

## The Problem · 问题在哪

智能体在演示里无往不利，却在生产里以演示预测不到的方式失败。基准回答的是「这个模型泛化能力强吗？」而不是「这个智能体在为我的产品交付正确的补丁吗？」答案是：在三个层次上持续运行评估，让每条护栏、每条学到的规则都对应一个评估用例。

> Agents pass demos. They fail in production in ways demos cannot predict. Benchmarks answer "is this model broadly capable?" not "is this agent shipping the right patches for my product?" The answer: evaluation at three layers, running continuously, with every guardrail and learned rule mapped to an eval case.

## The Concept · 概念

### Three evaluation layers · 三个评估层

1. **静态基准（static benchmarks）**——代码用 SWE-bench Verified（第 19 课）、浏览/桌面用 WebArena/OSWorld（第 20 课）、通用智能用 GAIA（第 19 课）、工具使用用 BFCL V4（第 06 课）。用于跨模型比较和回归把关。数据污染是真实存在的：SWE-bench+ 发现了 32.67% 的解法泄露。永远报告 Verified / 经过审计的分数。

2. **自定义离线评估（custom offline evals）**——贴合你产品的形态：
   - LLM-as-judge（Langfuse、Phoenix、Opik——第 24 课）。
   - 执行型（跑补丁、查测试）。
   - 轨迹型（把动作序列与黄金轨迹对比；OSWorld-Human 显示顶级智能体是黄金轨迹的 1.4-2.7 倍步数）。

3. **线上评估（online evals）**——生产环境：
   - 会话回放（Langfuse）。
   - 护栏触发的告警（第 16、21 课）。
   - 逐步成本 / 延迟追踪（第 23 课 OTel span）。

> Static benchmarks — SWE-bench Verified for code (Lesson 19), WebArena/OSWorld for browsing / desktop (Lesson 20), GAIA for generalist (Lesson 19), BFCL V4 for tool use (Lesson 06). Use for cross-model comparison and regression gating.
> Contamination is real: SWE-bench+ found 32.67% solution leakage. Always report Verified / +-audited scores.
> Custom offline evals — your product's shape: LLM-as-judge... Execution-based... Trajectory-based...
> Online evals — production: session replays, guardrail-triggered alerts, per-step cost / latency tracking.

### Evaluator-optimizer (Anthropic) · 评估器-优化器

这个紧密循环：

1. 提案者（proposer）生成输出。
2. 评估器（evaluator）评判。
3. 精炼直到评估器通过。

这是 Self-Refine（第 05 课）的推广。你在乎的任何智能体流程，都可以包一层 evaluator-optimizer 来提高可靠性。

> Proposer generates output.
> Evaluator judges.
> Refine until evaluator passes.
> This is Self-Refine (Lesson 05) generalized. Any agent flow you care about can wrap in evaluator-optimizer for reliability.

### 2026 best practice · 2026 年的最佳实践

- 评估与代码同库存放。
- 每个 PR 都在 CI 里运行。
- 用评估分数为合并把关（例如「相对 main 回归不超过 5%」）。
- 每条护栏都对应一个评估用例。
- 每条学到的规则（Reflexion、pro-workflow 的 learn-rule）都对应一个失败用例。

> Evals live next to code.
> Run in CI on every PR.
> Gate merge on eval scores (e.g. "no regression > 5% vs main").
> Every guardrail maps to an eval case.
> Every learned rule (Reflexion, pro-workflow learn-rule) maps to a failure case.

### Tying Phase 14 together · 把 Phase 14 串起来

Phase 14 的每一课都会生成评估用例：

| Lesson 课程 | 它生成的评估用例 Eval case it generates |
|--------|------------------------|
| 01 Agent Loop | 预算耗尽、死循环防护 |
| 02 ReWOO | 工具失败时 planner 正确重规划 |
| 03 Reflexion | 学到的反思在重试时生效 |
| 05 Self-Refine/CRITIC | judge 通过精炼后的输出 |
| 06 Tool Use | 参数纠偏生效；未知工具被拒绝 |
| 07-10 Memory | 检索引用与来源匹配；过期事实被判定失效 |
| 12 Workflow Patterns | 每种模式产出正确输出 |
| 13 LangGraph | 恢复后状态完全复现 |
| 14 AutoGen Actors | DLQ 接住崩溃的 handler |
| 16 OpenAI Agents SDK | 护栏在正确的输入上触发 |
| 17 Claude Agent SDK | 子智能体结果返回给编排器 |
| 19-20 Benchmarks | SWE-bench Verified 分数、WebArena 成功率、OSWorld 效率 |
| 21 Computer Use | 每步安全检查抓住被注入的 DOM |
| 23 OTel | span 携带必需的属性 |
| 26 Failure Modes | 检测器标记已知失败 |
| 27 Prompt Injection | PVE 拒绝被投毒的检索内容 |
| 28 Orchestration | supervisor 路由到正确的专家 |
| 29 Runtime Shapes | DLQ 承受 N% 失败 |

如果你的评估套件为每一种都有用例，你就覆盖了整个 Phase 14。

> Every lesson in Phase 14 generates eval cases.
> If your eval suite has cases for each, you have covered Phase 14.

### Where eval-driven development fails · 评估驱动开发哪里会失败

- **没有基线（baseline）。** 没有「最后已知良好」的评估结果无法解读。保存基线。
- **LLM judge 没有事实根据。** judge 自己也会幻觉。用 CRITIC 模式（第 05 课）——让 judge 锚定在外部工具上。
- **对评估过拟合。** 针对评估做优化，会偏离生产价值。轮换用例。
- **评估本身不稳定（flaky）。** 非确定性的用例制造假警报。固定随机种子，快照状态。

> No baseline. Evals without a last-known-good are unreadable. Store baselines.
> LLM-judge without grounding. Judges hallucinate too. CRITIC pattern (Lesson 05) — judge grounds on external tools.
> Over-fitting to evals. Optimizing for the eval diverges from production usefulness. Rotate cases.
> Flaky evals. Non-deterministic cases cause false alarms. Pin seeds, snapshot state.

```figure
ae-eval-three-layers
```

## Build It · 动手造

`code/main.py` 是一个 stdlib 评估 harness：

- 带类别（benchmark、custom、online）的用例注册表。
- 一个被测的脚本化智能体。
- Evaluator-optimizer 循环：提案、评判、精炼，直到通过或达到最大轮数。
- CI 门：聚合通过率 + 相对基线的回归。

运行：

```
python3 code/main.py
```

输出：每个用例的通过/失败、回归标志、CI 门裁决。

> Case registry with categories (benchmark, custom, online).
> Evaluator-optimizer loop: propose, judge, refine until pass or max rounds.
> Output: per-case pass/fail, regression flag, CI gate verdict.

## Use It · 实战用法

- 把评估用例写在智能体代码的同一个仓库里。
- 每个 PR 都通过 CI 运行它们。
- 出现回归就让构建失败。
- 长期追踪通过率。
- 把每一次生产失败都对应到一个新用例。

> Write eval cases in the same repo as your agent code.
> Run them on every PR via CI.
> Fail the build on regression.
> Track pass rate over time.
> Tie every production failure to a new case.

## Ship It · 交付

`outputs/skill-eval-suite.md` 为一个智能体产品搭建三层评估套件，带 CI 门和回归追踪。

> `outputs/skill-eval-suite.md` builds a three-layer eval suite for an agent product with CI gates and regression tracking.

## Exercises · 练习

1. 拿一次你的生产失败。写一个能复现它的评估用例。你的智能体现在能通过吗？
2. 为你的领域构建一个 LLM-judge 评分规则，含三个维度（事实性、语气、范围）。给 50 个会话打分。
3. 把评估套件接进 CI。回归 ≥5% 就让构建失败。
4. 加一个轨迹效率指标：智能体用了多少步，对比黄金轨迹？
5. 把 Phase 14 的每一课映射到你评估套件里的一个用例。有缺失吗？那就是要补上的缺口。

> Take one of your production failures. Write an eval case that reproduces it. Does your agent pass it now?
> Build an LLM-judge rubric for your domain with three dimensions (factual, tone, scope). Score 50 sessions.
> Wire the eval suite into CI. Fail the build on >=5% regression.

## Key Terms · 术语表

| Term 术语 | What people say 大家怎么说 | What it actually means 实际含义 |
|------|------------------------|------------------------|
| Static benchmark（静态基准） | 「现成的评估」 | SWE-bench、GAIA、AgentBench、WebArena、OSWorld |
| Custom offline eval（自定义离线评估） | 「领域评估」 | 在你的产品形态上做 LLM-as-judge / 执行 / 轨迹评估 |
| Online eval（线上评估） | 「生产评估」 | 会话回放、护栏告警、成本/延迟追踪 |
| Evaluator-optimizer（评估器-优化器） | 「提案-评判-精炼」 | 迭代直到 judge 通过 |
| CI gate（CI 门） | 「合并拦截器」 | 评估回归就让构建失败 |
| Baseline（基线） | 「最后已知良好」 | 用来检测回归的参考分数 |
| Trajectory efficiency（轨迹效率） | 「相对黄金轨迹的步数」 | 智能体步数除以人类专家的最小步数 |

## Further Reading · 延伸阅读

- [Anthropic, Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) —— 「从简单开始，用评估优化」
- [OpenAI, SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/) —— 精选过的基准
- [Berkeley Function Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html) —— 工具使用基准
- [Langfuse docs](https://langfuse.com/) —— 评估 + 会话回放的实战
