# Capstone 09 — Code Migration Agent (Repo-Level Language / Runtime Upgrade) · 毕业项目 09 —— 代码迁移智能体（仓库级语言 / 运行时升级）

> Amazon 的 MigrationBench（Java 8 升 17）和 Google 的 App Engine Py2 迁 Py3 迁移器设定了 2026 年的标杆。Moderne 的 OpenRewrite 在大规模场景下做确定性 AST 重写，Grit 用 codemod 风格的 DSL 瞄准同一个问题。生产级模式是两者结合：确定性地基负责安全重写，agent 层负责模糊场景，外加一个按分支构建的沙箱，以及一个在 PR 打开之前就把测试翻绿的测试基座（test harness）。本次毕业项目要迁移 50 个真实仓库，公开通过率，并给出一份失败分类法。

> Amazon's MigrationBench (Java 8 to 17) and Google's App Engine Py2-to-Py3 migrator set the 2026 bar. Moderne's OpenRewrite does deterministic AST rewrites at scale. Grit targets the same problem with codemod-style DSL. The production pattern combines both: a deterministic substrate for safe rewrites plus an agent layer for the ambiguous cases, a sandbox for per-branch builds, and a test harness that flips green before the PR opens. The capstone is to migrate 50 real repos and publish a pass rate with a failure taxonomy.

**Type:** Capstone
**Languages:** Python (agent), Java / Python (targets), TypeScript (dashboard)
**Prerequisites:** Phase 5 (NLP), Phase 7 (transformers), Phase 11 (LLM engineering), Phase 13 (tools), Phase 14 (agents), Phase 15 (autonomous), Phase 17 (infrastructure)
**Phases exercised:** P5 · P7 · P11 · P13 · P14 · P15 · P17
**Time:** 30 hours

## Problem · 问题

大规模代码迁移是 2026 年编码智能体（agent）最干净的生产级应用之一。真值标准一目了然（迁移之后测试套件能否通过？），回报是实打实的（一次 Java 8 机群迁移是按人头计算的工程量），基准也是公开的（MigrationBench 50 仓库子集）。Moderne 的 OpenRewrite 负责确定性的一面；agent 层负责 OpenRewrite recipe 处理不了的一切：含糊的重写、构建系统漂移、长尾语法、传递依赖破坏。

你要构建一个 agent：输入一个 Java 8（或 Python 2）仓库，产出一个 CI 全绿的迁移分支。你要度量通过率、测试覆盖率保持度、单仓库成本，并建立一套失败分类法（failure taxonomy）。与「纯确定性基线」的同台对比，会告诉你 agent 的价值到底落在哪里。

> Large-scale code migration is one of the cleanest production applications of 2026 coding agents. The ground truth is obvious (does the test suite pass after the migration?), the rewards are real (a Java-8 fleet migration is a headcount-scale project), and the benchmarks are public (MigrationBench 50-repo subset). Moderne's OpenRewrite handles the deterministic side. The agent layer handles everything OpenRewrite recipes cannot: ambiguous rewrites, build-system drift, long-tail syntax, transitive dependency breakage.
> You will build an agent that takes a Java 8 repo (or Python 2 repo) and produces a green-CI migrated branch. You will measure pass rate, test-coverage preservation, cost per repo, and build a failure taxonomy. The side-by-side against a deterministic-only baseline tells you where the agent's value actually lives.

## Concept · 概念

整条流水线分两层。**确定性地基**（Java 用 OpenRewrite，Python 用 libcst）安全地完成大部分机械重写：import、方法签名、null 安全修改、try-with-resources、废弃 API 替换。它速度快，而且产出可审计的 diff。**agent 层**（OpenAI Agents SDK 或 LangGraph，底层模型 Claude Opus 4.7 和 GPT-5.4-Codex）处理 recipe 覆盖不了的情形：构建文件升级（Maven/Gradle/pyproject）、传递依赖冲突、测试抖动（test flake）、自定义注解。

每个仓库分配一个预装了目标运行时的 Daytona 沙箱。agent 循环迭代：跑构建、归类失败、应用修复、重跑。硬性上限：每个仓库 30 分钟、8 美元、20 个 agent 轮次。如果全部测试通过且覆盖率差值不为负，该分支就开一个 PR；否则该仓库被归入某个失败类别，并附上证据。

失败分类法本身就是交付物。横跨 50 个仓库，到底是什么坏了？传递依赖？自定义注解？构建工具版本？与迁移无关的测试抖动？每个类别记录一个计数和一个示例 diff。未来的 recipe 作者可以瞄准排名前三的类别。

> The pipeline has two layers. The **deterministic substrate** (OpenRewrite for Java, libcst for Python) runs the bulk of mechanical rewrites safely: imports, method signatures, null-safety edits, try-with-resources, deprecated API replacements. It is fast and produces auditable diffs. The **agent layer** (OpenAI Agents SDK or LangGraph over Claude Opus 4.7 and GPT-5.4-Codex) handles cases the recipes cannot: build-file upgrades (Maven/Gradle/pyproject), transitive dependency conflicts, test flakes, custom annotations.
> Each repo gets a Daytona sandbox with the target runtime preinstalled. The agent iterates: run build, classify failures, apply fix, rerun. Hard limits: 30 minutes per repo, $8 per repo, 20 agent turns. If all tests pass and the coverage delta is not negative, the branch opens a PR. If not, the repo gets filed under a failure class with evidence.
> The failure taxonomy is the deliverable. Across 50 repos, what broke? Transitive deps? Custom annotations? Build tool version? Test flakes unrelated to migration? Each class gets a count and an exemplar diff. Future recipe authors can target the top three.

## Architecture · 架构

```
target repo
      |
      v
OpenRewrite / libcst deterministic recipes
   (safe, fast, auditable, ~70-80% of fixes)
      |
      v
Daytona sandbox per branch
      |
      v
agent loop (Claude Opus 4.7 / GPT-5.4-Codex):
   - run build -> capture failures
   - classify failures (build, test, lint)
   - apply fix (patch or retry recipe)
   - rerun
   - budget: 30 min, $8, 20 turns
      |
      v
test + coverage delta gate
      |
      v (passed)
open PR
      |
      v (failed)
file under failure class + attach repro
```

## Stack · 技术栈

- 确定性地基：OpenRewrite（Java）或 libcst（Python）
- Agent：OpenAI Agents SDK 或 LangGraph，底层模型 Claude Opus 4.7 + GPT-5.4-Codex
- 沙箱：每个分支一个 Daytona devcontainer，预装目标运行时（Java 17 / Python 3.12）
- 构建系统：Maven、Gradle、uv（Python）
- 基准：Amazon MigrationBench 50 仓库子集（Java 8 升 17）、Google App Engine Py2 迁 Py3 仓库
- 测试基座：并行执行器，覆盖率用 Jacoco（Java）或 coverage.py（Python）
- 可观测性：Langfuse + 每个仓库一份包含所有 diff 块的 trace bundle
- 仪表盘：失败分类法仪表盘，展示各类别计数与示例 diff

```figure
ce-migration-funnel
```

## Build It · 动手造

1. **Recipe pass（recipe 轮）。** 先跑 OpenRewrite（Java）或 libcst（Python）recipe，把 70-80% 机械性的迁移先吃掉，作为一个 "recipe" commit 提交。

2. **构建试跑。** Daytona 沙箱：安装目标运行时，跑构建。绿了就跳到测试；红了就交给 agent。

3. **Agent 循环。** LangGraph 挂上工具：`run_build`、`read_file`、`edit_file`、`run_test`、`git_diff`。agent 给失败归类（依赖、语法、测试、构建工具）并应用针对性修复，然后重跑。

4. **预算上限。** 每个仓库 30 分钟墙钟时间、8 美元成本、20 个 agent 轮次。任何一项越界都立即停止，并以 "budget_exhausted" 归档当前 diff。

5. **测试 + 覆盖率闸门。** 构建变绿之后跑测试套件，与基线仓库比较覆盖率。覆盖率下降超过 2%，按 "coverage_regression" 归档。

6. **开 PR。** 成功则推送分支、打开 PR，附上 diff，并写明应用了哪些 recipe、哪些 commit 由 agent 完成。

7. **失败分类法。** 每个失败的仓库打上一个类别标签：`dep_upgrade_required`、`build_tool_drift`、`custom_annotation`、`test_flake`、`syntax_edge_case`、`budget_exhausted`。据此建一个仪表盘。

8. **50 仓库运行。** 在 MigrationBench 子集上执行。报告各类别通过率、单仓库成本、覆盖率保持度，以及与「纯确定性」基线的对比。

> 2. **Build trial.** Daytona sandbox: install target runtime, run the build. If green, skip to tests. If red, hand off to agent.
> 4. **Budget caps.** 30 minutes wall-clock per repo, $8 cost, 20 agent turns. Any breach halts and files under "budget_exhausted" with the current diff.
> 5. **Test + coverage gate.** After the build goes green, run the test suite. Compare coverage to the base repo. If coverage dropped more than 2%, file under "coverage_regression".
> 7. **Failure taxonomy.** For each failed repo, tag with a class: `dep_upgrade_required`, `build_tool_drift`, `custom_annotation`, `test_flake`, `syntax_edge_case`, `budget_exhausted`. Build a dashboard.

## Use It · 实战用法

```
$ migrate legacy-java-service --target java17
[recipe]   27 rewrites applied (JUnit 4->5, HashMap initializer, try-with-resources)
[build]    FAIL: cannot find symbol sun.misc.BASE64Encoder
[agent]    turn 1 classify: removed_jdk_api
[agent]    turn 2 apply: sun.misc.BASE64Encoder -> java.util.Base64
[build]    OK
[tests]    412/412 passing; coverage 84.1% -> 84.3%
[pr]       opened #1841  cost=$3.20  turns=4
```

## Ship It · 交付

`outputs/skill-migration-agent.md` 是交付物。给定一个仓库，它先执行确定性 recipe，再跑 agent 循环，最终产出一个迁移后全绿的分支；做不到就把仓库归入某个分类类别。

| 权重 | 评分标准 | 度量方式 |
|:-:|---|---|
| 25 | MigrationBench 通过率 | 50 仓库子集 pass@1 |
| 20 | 测试覆盖率保持 | 相对基线的平均覆盖率差值 |
| 20 | 单个迁移仓库的成本 | 通过运行中的 $/repo |
| 20 | Agent / 确定性工具分工 | OpenRewrite 处理的修复占比 vs agent 完成的占比 |
| 15 | 失败分析报告 | 分类法完整度，附示例 |
| **100** | | |

> `outputs/skill-migration-agent.md` is the deliverable. Given a repo, it executes deterministic recipes then an agent loop to produce a green migrated branch, or files the repo under a taxonomy class.

## Exercises · 练习

1. 只用 OpenRewrite（不挂 agent）跑迁移流水线，与完整流水线比较通过率。找出「只有 agent 才能搞定」的那些案例。

2. 实现一个 "lint-clean" 检查：迁移之后跑风格 linter（Java 用 spotless，Python 用 ruff）。出现新的 lint 错误就让 PR 失败，并度量「覆盖率保住但风格退化」的比例。

3. 加一个 "minimal-diff" 优化器：agent 分支通过测试后，再做一轮精简，去掉不必要的改动。报告 diff 体积的缩减。

4. 扩展到第三种迁移：Node 18 升 Node 22。复用沙箱封装，把 recipe 层换成自定义 codemod。

5. 把首次构建变绿时间（TTFGB, time-to-first-green-build）当作 UX 指标来度量。目标：p50 低于 10 分钟。

> 1. Run the migrate pipeline with OpenRewrite only (no agent). Compare pass rate to the full pipeline. Identify the cases where the agent alone is the difference.
> 5. Measure time-to-first-green-build (TTFGB) as a UX metric. Target: p50 under 10 minutes.

## Key Terms · 术语表

| 术语 | 俗称 | 实际含义 |
|------|-----------------|------------------------|
| Deterministic substrate（确定性地基） | "Recipe 引擎" | OpenRewrite / libcst：带安全保证的声明式 AST 重写 |
| Codemod | "改代码的程序" | 一条机械化修改源代码的重写规则 |
| Build drift（构建漂移） | "工具版本错位" | Maven / Gradle / uv 在大版本之间的细微行为差异 |
| Failure class（失败类别） | "分类桶" | 仓库迁移失败的一个标注原因：依赖、语法、测试、构建工具、预算 |
| Coverage delta（覆盖率差值） | "覆盖率保持" | 从基线到迁移分支的测试覆盖率百分比变化 |
| Agent turn（agent 轮次） | "一轮工具调用" | agent 循环中一次「计划 → 行动 → 观察」周期 |
| Budget exhaustion（预算耗尽） | "撞到天花板" | 仓库耗尽 30 分钟 / $8 / 20 轮上限仍未通过 |

## Further Reading · 延伸阅读

- [Amazon MigrationBench](https://aws.amazon.com/blogs/devops/amazon-introduces-two-benchmark-datasets-for-evaluating-ai-agents-ability-on-code-migration/) —— 2026 年的标杆基准
- [Moderne.io OpenRewrite platform](https://www.moderne.io) —— 确定性地基的参考实现
- [OpenRewrite documentation](https://docs.openrewrite.org) —— recipe 编写
- [Grit.io](https://www.grit.io) —— 另一个 codemod DSL
- [OpenAI sandboxed migration cookbook](https://developers.openai.com/cookbook/examples/agents_sdk/sandboxed-code-migration/sandboxed_code_migration_agent) —— Agents SDK 参考
- [Google App Engine Py2 to Py3 migrator](https://cloud.google.com/appengine) —— 另一个迁移基准
- [libcst](https://github.com/Instagram/LibCST) —— Python 确定性地基
- [Daytona sandboxes](https://daytona.io) —— 按分支沙箱的参考实现
