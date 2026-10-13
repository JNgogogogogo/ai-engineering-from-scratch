# Benchmarks: SWE-bench, GAIA, AgentBench · 基准测试：SWE-bench、GAIA、AgentBench

> 三个基准锚定了 2026 年的 agent 评估。SWE-bench 测代码修补。GAIA 测通用工具使用。AgentBench 测多环境推理。你要了解它们的构成、它们的数据污染（contamination）故事，以及它们没在测什么。
>
> Three benchmarks anchor agent evaluation in 2026. SWE-bench tests code patching. GAIA tests generalist tool use. AgentBench tests multi-environment reasoning. Know their composition, their contamination story, and what they do not measure.

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 06 (Tool Use)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 说出 SWE-bench 的测试机制（FAIL_TO_PASS）并解释它为什么用单元测试做门禁。
- 解释 SWE-bench Verified（OpenAI，500 个任务）为什么存在、它剔除了什么。
- 描述 GAIA 的设计理念：对人简单、对 AI 难；三个难度级别。
- 说出 AgentBench 的八个环境，以及开源 LLM 落后的主因。
- 总结 SWE-bench+ 的数据污染发现及其影响。

> Name SWE-bench's test harness (FAIL_TO_PASS) and explain why it gates on unit tests.
> Explain why SWE-bench Verified (OpenAI, 500 tasks) exists and what it removes.
> Describe GAIA's design: simple for humans, hard for AI; three difficulty levels.
> Name AgentBench's eight environments and its primary blocker for open-source LLMs.
> Summarize the SWE-bench+ contamination finding and its implications.

## The Problem · 问题在哪

排行榜只能告诉你在某一个基准上哪个模型赢。它不能告诉你：

- 这个基准是否已被污染（解法进了训练数据、测试泄漏）。
- 这个基准量的是不是你在乎的东西（代码 vs 浏览器 vs 通用能力）。
- 评估器是否稳健（AST 匹配、状态检查、人工评审）。

在引用任何数字之前，先了解这三个锚点基准和它们的失效模式。

> Leaderboards tell you which model wins on one benchmark. They do not tell you:
> - Whether the benchmark is contaminated (solutions in training data, test leakage).
> - Whether the benchmark measures what you care about (code vs browsing vs generalist).
> - Whether the evaluator is robust (AST matching, state checks, human review).
> Know the three anchoring benchmarks and their failure modes before you quote a number.

## The Concept · 概念

### SWE-bench (Jimenez et al., ICLR 2024 oral) · SWE-bench

- 来自 12 个热门 Python 仓库的 2,294 个真实 GitHub issue。
- Agent 拿到：修复前那个 commit 时刻的代码库 + 自然语言 issue 描述。
- Agent 产出：一个补丁（patch）。
- 评估器：应用补丁，跑该仓库的测试套件。补丁必须让 FAIL_TO_PASS 测试（之前失败、现在要通过）翻绿，同时不能打破 PASS_TO_PASS 测试。

> - 2,294 real GitHub issues from 12 popular Python repos.
> - Agent gets: the codebase at the pre-fix commit + natural-language issue description.
> - Agent produces: a patch.
> - Evaluator: apply patch, run the repo's test suite. The patch must flip FAIL_TO_PASS tests (previously failing, now passing) without breaking PASS_TO_PASS tests.

SWE-agent（Yang et al., 2024）发布时拿到 12.5%，靠的是强调 agent-计算机接口（模型看得懂的文件编辑命令、搜索语法）。

> SWE-agent (Yang et al., 2024) hit 12.5% at release by emphasizing agent-computer interfaces (file editor commands, search syntax the model understands).

### SWE-bench Verified · SWE-bench Verified

OpenAI，2024 年 8 月。人工精选的 500 个任务子集。剔除了含混的 issue、不可靠的测试、以及修复方式不明确的任务。它是「你的 agent 能不能交付真实补丁」的首要基准。

> OpenAI, Aug 2024. Human-curated 500-task subset. Removes ambiguous issues, unreliable tests, and tasks where the fix was unclear. Primary benchmark for "does your agent ship real patches?"

### Contamination · 数据污染

- SWE-bench 超过 94% 的 issue 早于大多数模型的训练截止时间。
- **SWE-bench+** 发现：32.67% 的成功补丁在 issue 文本里泄漏了解法（模型在描述里就看到了修法），31.08% 因测试覆盖太弱而存疑。
- Verified 更干净，但并非零污染。

> - Over 94% of SWE-bench issues predate most model cutoffs.
> - **SWE-bench+** found 32.67% of successful patches leaked solutions in the issue text (model saw the fix in the description), and 31.08% were suspicious due to weak test coverage.
> - Verified is cleaner but not contamination-free.

现实含义：一个在 SWE-bench 上拿 50% 的模型，在 SWE-bench+ 上可能只有 35%。只要你宣称 SWE-bench 成绩，就应该两个都报。

> Practical implication: a model that scores 50% on SWE-bench may score 35% on SWE-bench+. Always report both if you claim SWE-bench performance.

### GAIA (Mialon et al., Nov 2023) · GAIA

- 466 道题；其中 300 道保留给 huggingface.co/gaia-benchmark 的私有排行榜。
- 设计哲学：「对人概念上简单（92%），对 AI 难（带插件的 GPT-4：15%）。」
- 考察推理、多模态、网页、工具使用。
- 三个难度级别；Level 3 需要跨模态的长工具链。

> - 466 questions; 300 retained for the private leaderboard at huggingface.co/gaia-benchmark.
> - Design philosophy: "conceptually simple for humans (92%) but hard for AI (GPT-4 with plugins: 15%)."
> - Tests reasoning, multi-modality, web, tool use.
> - Three difficulty levels; Level 3 requires long tool chains across modalities.

要量「通用能力」就跑 GAIA。别和代码专项基准搞混。

> GAIA is what you run to measure "generalist capability." Do not confuse with code-specific benchmarks.

### AgentBench (Liu et al., ICLR 2024) · AgentBench

- 8 个环境，覆盖代码（Bash、DB、KG）、游戏（Alfworld、LTP）、网页（WebShop、Mind2Web）和开放式生成。
- 多轮对话，每个 split 约 4k–13k 轮。
- 核心发现：长期推理、决策和指令遵循，是开源 LLM 追赶商业模型的拦路虎。

> - 8 environments across code (Bash, DB, KG), games (Alfworld, LTP), web (WebShop, Mind2Web), and open-ended generation.
> - Multi-turn, ~4k-13k turns per split.
> - Primary finding: long-term reasoning, decision-making, and instruction following are the blockers for OSS LLMs catching up to commercial.

### What these do not measure · 这些基准没在测什么

- 真实世界的运行成本（token、墙钟时间）。
- 对抗条件下的安全行为。
- 在你的业务领域上的表现（用你自己的评估，第 30 课）。
- 尾部失败（基准取平均；生产运维在乎的是最差的 1%）。

> - Real-world operational cost (tokens, wall-clock).
> - Safety behavior in adversarial conditions.
> - Performance on your domain (use your own evals, Lesson 30).
> - Tail failures (benchmarks average; production operators care about the worst 1%).

### Where benchmarking goes wrong · 基准测试的常见坑

- **单数字执念。** 「SWE-bench 50%」告诉你的东西，比不上 P50/P75/P95 成本 + 步数分布。
- **带污染的宣称。** 报 SWE-bench 却不提 Verified 或 SWE-bench+，就是误导。
- **把基准当开发目标。** 针对基准做优化，会偏离生产有用性。

> - **Single-number fixation.** SWE-bench 50% tells you less than the P50/P75/P95 cost + step distribution.
> - **Contaminated claims.** Reporting SWE-bench without mentioning Verified or SWE-bench+ is misleading.
> - **Benchmark-as-development-target.** Optimizing for the benchmark diverges from production usefulness.

```figure
ae-swebench-gate
```

## Build It · 动手造

`code/main.py` 实现了一个玩具版 SWE-bench 式 harness：

- 合成的修 bug 任务（3 个任务）。
- 一个脚本化的「agent」，负责提出补丁。
- 一个测试运行器，检查 FAIL_TO_PASS（bug 已修复）和 PASS_TO_PASS（没弄坏别的）。
- 一个 GAIA 式的难度分类器，按问题分解深度打分。

运行：

```
python3 code/main.py
```

> `code/main.py` implements a toy SWE-bench-like harness:
> - Synthetic bug-fix tasks (3 tasks).
> - A scripted "agent" that proposes patches.
> - A test runner that checks FAIL_TO_PASS (bug now fixed) and PASS_TO_PASS (nothing broken).
> - A GAIA-style difficulty classifier based on question decomposition depth.

输出会展示每个任务、每个难度级别的解决率，并把评估器规则变得具体。

> The output shows resolution rate per task + per difficulty and makes the evaluator rules concrete.

## Use It · 实战用法

- **SWE-bench Verified** 用于代码 agent。永远报 Verified 分数。
- **GAIA** 用于通用 agent。使用私有排行榜的 split。
- **AgentBench** 用于跨环境对比。
- **自定义评估**（第 30 课）用于你产品真实的样子。

> - **SWE-bench Verified** for code agents. Always report Verified scores.
> - **GAIA** for generalist agents. Use the private leaderboard split.
> - **AgentBench** for multi-environment comparison.
> - **Custom evals** (Lesson 30) for your product's actual shape.

## Ship It · 交付

`outputs/skill-benchmark-harness.md` 为任一「代码库-任务」对搭建 SWE-bench 式 harness，带 FAIL_TO_PASS / PASS_TO_PASS 门禁。

> `outputs/skill-benchmark-harness.md` builds a SWE-bench-style harness for any codebase-task pair with FAIL_TO_PASS / PASS_TO_PASS gating.

## Exercises · 练习

1. 把玩具 harness 移植到一个真实仓库上（挑你自己的一个）。为已知 bug 写 3 个 FAIL_TO_PASS 测试。
2. 加一个步数指标。在你的 3 个任务上，每次解决需要多少 agent 步数？
3. 读 SWE-bench+ 论文。实现一个解法泄漏检查（把 issue 文本与 diff 做模式匹配）。
4. 从公开 split 下载一道 GAIA 题。推演一个 GPT-4 级 agent 会怎么做。它需要哪些工具？
5. 读 AgentBench 的分环境明细。哪个环境最像你的产品界面？在那里「SOTA」长什么样？

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| SWE-bench | 「代码 agent 基准」 | 2,294 个 GitHub issue；补丁必须让 FAIL_TO_PASS 测试翻绿 |
| SWE-bench Verified | 「干净的 SWE-bench」 | OpenAI 人工精选的 500 个任务 |
| FAIL_TO_PASS | 「修复门禁」 | 之前失败、补丁之后必须通过的测试 |
| PASS_TO_PASS | 「无回归门禁」 | 之前通过、之后必须仍然通过的测试 |
| GAIA | 「通用基准」 | 466 道「人易 / AI 难」的多工具问题 |
| AgentBench | 「多环境基准」 | 8 个环境；长程多轮 |
| Contamination | 「训练集泄漏」 | 基准任务出现在模型训练数据里 |
| SWE-bench+ | 「污染审计」 | 在 SWE-bench 成功补丁中发现 32.67% 的解法泄漏 |

## Further Reading · 延伸阅读

- [Jimenez et al., SWE-bench (arXiv:2310.06770)](https://arxiv.org/abs/2310.06770) —— 原始基准
- [OpenAI, SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/) —— 精选子集
- [Mialon et al., GAIA (arXiv:2311.12983)](https://arxiv.org/abs/2311.12983) —— 通用能力基准
- [Liu et al., AgentBench (arXiv:2308.03688)](https://arxiv.org/abs/2308.03688) —— 多环境套件
