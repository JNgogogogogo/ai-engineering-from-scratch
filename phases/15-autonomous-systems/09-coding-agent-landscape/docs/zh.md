# The Autonomous Coding Agent Landscape (2026) · 自主编程 Agent 全景（2026）

> SWE-bench Verified went from 4% to 80.9% in under three years. Same Claude Sonnet 4.5 scored 43.2% on SWE-agent v1 and 59.8% on Cline autonomous — the scaffolding around the model now matters as much as the model itself. OpenHands (formerly OpenDevin) is the most active MIT-licensed platform and its CodeAct loop executes Python actions directly in a sandbox instead of JSON tool calls. The headline numbers hide a methodological issue: 161 of 500 SWE-bench Verified tasks require only a 1–2 line change, and SWE-bench Pro (10+ line tasks) sits at 23–59% for the same frontier models.

**类型:** Learn（学习）
**语言:** Python（仅标准库；CodeAct 与 JSON tool-call 对比）
**前置课程:** Phase 14 · 07（Tool use）、Phase 15 · 01（Long-horizon agents）
**时间:** ~45 分钟

---

## The Problem · 问题在哪

「哪个编程 agent 最好」是个问错了的问题。正确的问题是：**在一个匹配我实际工作的任务分布上，用我在生产环境里真的会跑的那套脚手架（scaffolding），我能拿到怎样的端到端可靠性？**

2022 到 2026 年，这个领域学到的一课是：**脚手架是承重结构**——检索层、规划器（planner）、沙箱、编辑-验证循环、反馈格式，每一层都在承重。Claude Sonnet 4.5 在 SWE-agent v1 脚手架下的 SWE-bench Verified 得分是 43.2%；同一个模型放进 Cline 的 autonomous 脚手架得分 59.8%。绝对分差 16.6 个百分点，而权重完全相同。**基座模型只是一个组件；循环（loop）才是产品。**

伴随而来的问题是：**基准饱和会掩盖能力回退**。SWE-bench Verified 已接近饱和，而简单任务的尾部（500 道任务里有 161 道只需 ≤2 行改动）在把头部分数越推越高。真实世界的质量更适合用 SWE-bench Pro（10+ 行改动）这类分布来度量——同样的头部系统在这里也只有 23–59%。

> "Which coding agent is best" is the wrong question. The right question is: on a task distribution that matches my work, with the scaffolding I will run in production, what end-to-end reliability do I get?
> Between 2022 and 2026 the field learned that scaffolding — the retrieval layer, the planner, the sandbox, the edit-verify loop, the feedback format — is load-bearing. ... The base model is a component; the loop is the product.
> The companion problem is that benchmark saturation hides regressions. SWE-bench Verified is close to saturated, and the easy-task tail (161 of 500 tasks requiring ≤2 lines) pulls top scores up. Real-world quality is better measured on distributions like SWE-bench Pro (10+ line changes), where the same leaders still sit at 23–59%.

---

## The Concept · 概念

### SWE-bench, one paragraph · 一段话说清 SWE-bench

SWE-bench（Jimenez 等人）取真实的 GitHub issue（附带标准补丁 ground-truth patch），要求 agent 产出一个能让测试套件通过的补丁。SWE-bench Verified（OpenAI，2024）是人工筛选过的 500 题子集，去掉了含糊不清和本身有缺陷的任务。SWE-bench Pro 是更难的后续版本——任务需要 10+ 行改动，当前的前沿 agent 在这里只有 23–59%。

> SWE-bench (Jimenez et al.) takes real GitHub issues with ground-truth patches and asks an agent to produce a patch that makes the test suite pass. SWE-bench Verified (OpenAI, 2024) is a human-curated 500-task subset with the ambiguous and broken tasks removed. SWE-bench Pro is the harder successor — tasks requiring 10+ lines of change, where current frontier agents sit at 23–59%.

### What the 2022 → 2026 curve actually shows · 2022 → 2026 的曲线到底说明了什么

- **2022**：研究模型在原始 SWE-bench 上约 4%。
- **2024**：GPT-4 + Devin 式脚手架约 14%；SWE-agent 约 12%。
- **2025**：Claude 3.5/3.7 Sonnet 在 Aider 和 SWE-agent 中推进到 40–55% 区间。
- **2026**：Claude Sonnet 4.5 与前沿竞品在 SWE-bench Verified 上达到 70–80%+。Epoch AI 的排行榜在实时追踪这条曲线。

斜率来自三个叠加的来源：更好的基座模型、更好的脚手架（CodeAct、反思 reflection、验证器循环）、更好的基准（Verified 去掉了噪声）。

> - **2022**: research models at ~4% on raw SWE-bench.
> - **2024**: GPT-4 + Devin-style scaffolding at ~14%; SWE-agent at ~12%.
> - **2025**: Claude 3.5/3.7 Sonnet inside Aider and SWE-agent push into the 40–55% range.
> - **2026**: Claude Sonnet 4.5 and frontier competitors at 70–80%+ on SWE-bench Verified. Epoch AI's leaderboard tracks this live.
> The slope came from three compounding sources: better base models, better scaffolding (CodeAct, reflection, verifier loops), and better benchmarks (Verified removing noise).

### CodeAct vs JSON tool calls · CodeAct 与 JSON 工具调用

OpenHands（All-Hands-AI，arXiv:2407.16741，前身为 OpenDevin）下了一个非常具体的架构赌注：不是让模型输出 JSON 工具调用、再由宿主解码执行，而是让模型直接输出 Python 代码，由一个 Jupyter 风格的内核在沙箱里运行。agent 可以在**一个动作里**循环遍历文件、串联工具、捕获自己的异常。

权衡如下：

- **JSON 工具调用**：每个动作就是一轮；容易审计；组合性有限；默认更安全，因为每次调用都要过一道显式验证器。
- **CodeAct**：一个动作可以是一整段程序；可组合；需要一个加固过的沙箱（OpenHands 用 Docker 隔离）；失败模式包括沙箱运行时允许的一切。

两种架构都在生产中使用。CodeAct 在开放平台占主导（OpenHands、smolagents）。JSON 工具调用在托管服务中仍占主导（Anthropic Managed Agents、OpenAI Assistants）——那里由提供商控制执行器。

> OpenHands (All-Hands-AI, arXiv:2407.16741, formerly OpenDevin) took a specific architectural bet: instead of the model emitting JSON tool calls that a host decodes and executes, the model emits Python code and a Jupyter-style kernel runs it in a sandbox. The agent can loop over files, chain tools, and catch its own exceptions inside one action.
> The trade-off:
> - **JSON tool calls**: every action is one turn; easy to audit; limited compositionality; safe by default because each call goes through an explicit validator.
> - **CodeAct**: one action can be a whole program; compositional; requires a hardened sandbox (OpenHands uses Docker isolation); failure modes include anything the sandbox runtime allows.
> Both architectures are in production. CodeAct is dominant in open platforms (OpenHands, smolagents). JSON tool calls remain dominant in managed services (Anthropic Managed Agents, OpenAI Assistants) where the provider controls the executor.

### Scaffolds in the 2026 landscape · 2026 全景中的脚手架

| 脚手架 | 许可证 | 执行模型 | 显著特性 |
|---|---|---|---|
| OpenHands (OpenDevin) | MIT | Docker 中的 CodeAct | 最活跃的开放平台；事件流可回放 |
| SWE-agent | MIT | Agent-Computer Interface（ACI） | 第一个端到端的 SWE-bench 脚手架 |
| Aider | Apache-2 | 本地仓库中的 diff 编辑 | 极简脚手架，回归稳定性强 |
| Cline | Apache-2 | 带工具策略的 VS Code agent | Sonnet 4.5 上得分最高的开放脚手架 |
| Devin (Cognition) | 专有 | 托管 VM + 规划器 | 开创「AI 软件工程师」产品品类 |
| Claude Code | 专有 | Permission modes + routines | 第 10 课将详细拆解这个 agent 循环 |

### Why scaffolding dominates · 为什么脚手架决定成败

一次编程运行是一条长程轨迹（long-horizon trajectory，见第 1 课）。可靠性会跨步骤复合。脚手架能在三个地方买到分数：

1. **检索（Retrieval）**：找到该读的文件是隐形的瓶颈。SWE-agent 的 ACI、OpenHands 的文件索引、Aider 的 repo-map 攻的都是这一点。
2. **验证器循环（Verifier loop）**：跑测试、读堆栈跟踪、再重试——在 SWE-bench 上能带来 10+ 个百分点的差异。
3. **失败遏制（Failure containment）**：出错时能回滚的沙箱可以阻止损害复合。同一个模型，带和不带验证器循环，看起来像两个不同的产品。

> A coding run is a long-horizon trajectory (Lesson 1). Reliability compounds across steps. Three places where scaffolding buys points:
> 1. **Retrieval**: finding the right files to read is the silent bottleneck. SWE-agent's ACI, OpenHands' file-index, and Aider's repo-map all attack this.
> 2. **Verifier loop**: running tests, reading stack traces, and re-attempting is a 10+ point delta on SWE-bench.
> 3. **Failure containment**: a sandbox that rolls back on error prevents compounding damage. The same model with and without a verifier loop looks like two different products.

### Benchmark saturation and the real distribution · 基准饱和与真实任务分布

OpenHands 的作者和 Epoch AI 都指出：SWE-bench Verified 存在一条简单尾部——500 题里有 161 题只需 1–2 行改动。高分有相当一部分是被这条尾部抬起来的。SWE-bench Pro 只保留 10+ 行改动的任务，即使是前沿系统，得分也回到 23–59% 区间。**你的生产任务分布几乎肯定更接近 Pro，而不是 Verified。**

对 agent 选型的启示：从自己的 bug 积压（backlog）里抽一个「Pro 风格」的子集来跑分。**真正重要的分数，是在能代表你实际交付内容的任务上的分数。**

```figure
a5-scaffold-delta
```

> The OpenHands authors and Epoch AI both flag that SWE-bench Verified has an easy tail: 161 of 500 tasks need only 1–2 lines of change. High scores are driven partly by this tail. SWE-bench Pro restricts to 10+ line changes and returns scores in the 23–59% range even for frontier systems. Your production distribution is almost certainly closer to Pro than to Verified.
> Implication for choosing an agent: run a Pro-like subset of your own bug backlog. The score that matters is the score on tasks representative of what you ship.

---

## Use It · 实战用法

`code/main.py` 在一个固定的小型任务分布上比较两个玩具 agent 脚手架：

1. 一个 **JSON tool-call** 脚手架：每轮只能做一个动作。
2. 一个 **CodeAct** 脚手架：每个动作可以输出一小段 Python 代码。

两者都使用桩「模型」（确定性规则），因此这个对比能把脚手架的影响与模型质量隔离开。输出显示：CodeAct 脚手架用更少的轮数解出更多任务，代价是单个动作的爆炸半径（blast radius）更大。

> `code/main.py` compares two toy agent scaffolds on a fixed mini-task distribution:
> 1. A **JSON tool-call** scaffold that takes one action per turn.
> 2. A **CodeAct** scaffold that can emit a small Python snippet per action.
> Both use a stub "model" (deterministic rules) so the comparison isolates the scaffold from model quality. The output shows the CodeAct scaffold solves more tasks in fewer turns at the cost of a larger per-action blast radius.

---

## Ship It · 交付

`outputs/skill-scaffold-audit.md` 帮你在采纳某个编程 agent 脚手架之前先做一轮审计：检索质量、验证器是否存在、沙箱隔离，以及「基准分数 ↔ 自家任务分布」的匹配度。

> `outputs/skill-scaffold-audit.md` helps you audit a proposed coding-agent scaffold before adoption: retrieval quality, verifier presence, sandbox isolation, and benchmark-to-distribution fit.

---

## Exercises · 练习

1. 运行 `code/main.py`。两个脚手架在同一批任务上各花多少轮？各自单动作的爆炸半径有多大？
2. 读 OpenHands 论文（arXiv:2407.16741）。论文主张 CodeAct 在复杂任务上胜过 JSON 工具调用。找出论文自己承认的一个失败模式，并用一句话说明该模式在什么生产场景下会占据主导。
3. 从你的 bug 积压中挑一个需要跨两个文件改 10+ 行的任务。估算前沿模型在 (a) JSON 工具调用 和 (b) CodeAct 下的端到端成功概率，并解释差距从何而来。
4. SWE-bench Verified 里有 161 道单文件、1–2 行改动的任务。构造一个把它们剔除后的分数。排行榜会发生怎样的洗牌？
5. 读「Introducing SWE-bench Verified」（OpenAI）。解释其剔除含糊任务的具体方法论，并指出这种人工筛选会漏掉的一类问题。

> 1. Run `code/main.py`. How many turns does each scaffold take on the same task set? What is the per-action blast radius of each?
> 2. Read the OpenHands paper (arXiv:2407.16741). The paper argues CodeAct beats JSON tool calls on complex tasks. Identify one failure mode the paper acknowledges and write one sentence on when that mode would dominate in production.
> 3. Pick one task from your bug backlog that would require 10+ lines of change across two files. Estimate the end-to-end success probability for a frontier model under (a) JSON tool calls and (b) CodeAct. Justify the gap.
> 4. SWE-bench Verified has 161 single-file, 1–2 line tasks. Construct a score that excludes them. How does the leaderboard shuffle?
> 5. Read "Introducing SWE-bench Verified" (OpenAI). Explain the specific methodology used to remove ambiguous tasks, and name one category the curation would miss.

---

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|---|---|---|
| SWE-bench | 「编程基准」 | 真实 GitHub issue + 标准补丁 + 测试套件 |
| SWE-bench Verified | 「清洗过的子集」 | 500 道人工筛选任务，仍带有较简单的尾部 |
| SWE-bench Pro | 「更难的子集」 | 10+ 行改动；前沿系统仅 23–59% |
| CodeAct | 「代码即动作」 | agent 输出 Python；Jupyter 风格内核在沙箱中执行 |
| JSON tool call | 「函数调用」 | 每个动作是一个结构化 JSON 载荷，执行前先验证 |
| Scaffold | 「agent 框架」 | 包在基座模型外面的检索 + 规划器 + 执行器 + 验证器循环 |
| ACI (Agent-Computer Interface) | 「SWE-agent 的格式」 | 为 LLM 易用性（而非人类 shell）设计的命令集 |
| Verifier loop | 「跑测试再重试」 | 跑测试、读输出、修订补丁；模型之外最大的可靠性增益 |

---

## Further Reading · 延伸阅读

- [Jimenez et al. — SWE-bench](https://www.swebench.com/) — 原始基准及其方法论。
- [OpenAI — Introducing SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/) — 人工筛选子集是如何构建的。
- [Wang et al. — OpenHands: An Open Platform for AI Software Developers](https://arxiv.org/abs/2407.16741) — CodeAct 架构与事件流设计。
- [Epoch AI — SWE-bench leaderboard](https://epoch.ai/benchmarks) — 实时追踪的分数。
- [Anthropic — Measuring agent autonomy](https://www.anthropic.com/research/measuring-agent-autonomy) — 长程编程 agent 可靠性的分析框架。
