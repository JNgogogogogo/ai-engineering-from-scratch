# Capstone 16 — GitHub Issue-to-PR Autonomous Agent · 毕业项目 16 —— GitHub Issue 转 PR 自主智能体

> 打一个标签，得到一个 PR——这就是 2026 年自主编码 agent 的产品形态：在云端沙箱里跑一个 agent，验证测试通过，然后发出一个带理由说明、可直接评审的 PR。AWS Remote SWE Agents、Cursor Background Agents、OpenAI Codex cloud 和 Google Jules 都已上线此形态。难点在于：自动复现仓库的构建环境、防止凭据泄漏、执行按仓库的预算，以及确保 agent 无法 force-push。本次毕业项目构建自托管版本，并在成本和通过率上与托管方案对比。

> Label an issue, get a PR — the 2026 product shape for autonomous coding agents: run an agent in a cloud sandbox, verify tests pass, and post a review-ready PR with rationale. AWS Remote SWE Agents, Cursor Background Agents, OpenAI Codex cloud, and Google Jules all ship it. The hard parts are reproducing the repo's build environment automatically, preventing credential leakage, enforcing per-repo budgets, and making sure the agent cannot force-push. This capstone builds the self-hosted version and compares it on cost and pass rate to the hosted alternatives.

**Type:** Capstone
**Languages:** Python (agent), TypeScript (GitHub App), YAML (Actions)
**Prerequisites:** Phase 11 (LLM engineering), Phase 13 (tools), Phase 14 (agents), Phase 15 (autonomous), Phase 17 (infrastructure)
**Phases exercised:** P11 · P13 · P14 · P15 · P17
**Time:** 30 hours

## Problem · 问题

异步云端编码 agent 是独立于交互式编码 agent（毕业项目 01）的一个产品类别。UX 就是一个 GitHub 标签。你给一个 issue 打上 `@agent fix this`，一个 worker 在云端沙箱里启动：克隆仓库、跑测试、改文件、验证，然后开一个 PR，正文里写明 agent 的理由。没有交互循环，没有终端。AWS Remote SWE Agents、Cursor Background Agents、OpenAI Codex cloud、Google Jules 和 Factory Droids 都收敛到这个形态。

工程挑战非常具体：环境复现（agent 必须在没有缓存开发镜像的条件下从零构建仓库）、不稳定测试（必须重跑或隔离）、凭据范围控制（一个带最小细粒度权限的 GitHub App）、按仓库按天的预算执行，以及禁止 force-push 政策。本次毕业项目度量通过率、成本和安全性，与托管方案对比。

> The async cloud coding agent is a separate product category from interactive coding agents (capstone 01). The UX is a GitHub label. You label an issue `@agent fix this`, a worker spins up in a cloud sandbox, clones the repo, runs tests, edits files, verifies, and opens a PR with the agent's rationale in the body. No interactive loop, no terminal. AWS Remote SWE Agents, Cursor Background Agents, OpenAI Codex cloud, Google Jules, and Factory Droids all converge on this.
> The engineering challenges are concrete: environment reproduction (the agent has to build the repo from scratch without a cached dev image), flaky tests (must be re-run or isolated), credential scoping (a GitHub App with minimal fine-grained permissions), budget enforcement per repo per day, and no-force-push policy. The capstone measures pass rate, cost, and safety vs the hosted alternatives.

## Concept · 概念

触发器是一个 GitHub webhook（issue 标签或 PR 评论）。分发器把工作排进 ECS Fargate 或 Lambda。worker 把仓库拉进一个 Daytona 或 E2B 沙箱，Dockerfile 由仓库（语言、框架）自动推断出的通用模板生成。agent 用 mini-swe-agent 或 SWE-agent v2 循环，底层是 Claude Opus 4.7 或 GPT-5.4-Codex。它迭代：读代码、提出修复、应用补丁、跑测试。

验证是把关步骤。PR 打开之前，完整 CI 必须在沙箱里通过。同时计算覆盖率差值；若负得超过阈值，PR 照常打开，但会打上 `needs-review` 标签。agent 把理由写成 PR 描述，外加一个 `@agent` 线程，评审者可以随时 @ 它追问。

安全通过两个不同的 GitHub 面来界定范围：App 提供短期安装令牌，只有 `workflows: read` 和狭窄的仓库内容/PR scope；分支保护（而不是 App 权限）强制执行「禁止直接写 `main`」和「禁止 force-push」——这个 App 绝不加入绕过名单。GitHub App 没有「按路径只读访问 `.github/workflows`」这种原生原语，所以 agent 的文件编辑允许清单必须在 worker 侧强制这条规则。按仓库按天的预算上限在分发器执行（例如每仓库每天最多 5 个 PR、每个 PR 20 美元）。

> The trigger is a GitHub webhook (issue label or PR comment). A dispatcher enqueues work to ECS Fargate or Lambda. The worker pulls the repo into a Daytona or E2B sandbox with a generic Dockerfile inferred from the repo (language, framework). The agent runs a mini-swe-agent or SWE-agent v2 loop against Claude Opus 4.7 or GPT-5.4-Codex. It iterates: read code, propose fix, apply patch, run tests.
> Verification is the gating step. Full CI must pass in the sandbox before the PR opens. Coverage delta is computed; if negative beyond a threshold, the PR opens but gets labeled `needs-review`. The agent posts the rationale as the PR description plus an `@agent` thread the reviewer can ping for follow-ups.
> Safety is scoped through two different GitHub surfaces: the App provides a short-lived installation token with `workflows: read` and narrow repo contents/PR scopes; branch protection (not app permissions) enforces "no direct writes to `main`" and "no force-push" — the app is never added to the bypass list. Path-scoped read-only access to `.github/workflows` is not a real GitHub App primitive, so the agent's allow-list on file edits has to enforce that at the worker. Budget ceilings per repo per day are enforced at the dispatcher (e.g., max 5 PRs per repo per day, $20 per PR).

## Architecture · 架构

```
GitHub issue labeled `@agent fix` or PR comment
            |
            v
    GitHub App webhook -> AWS Lambda dispatcher
            |
            v
    ECS Fargate task (or GitHub Actions self-hosted runner)
       - pull repo
       - infer Dockerfile (language, package manager)
       - Daytona / E2B sandbox with target runtime
       - clone -> git worktree -> agent branch
            |
            v
    mini-swe-agent / SWE-agent v2 loop
       Claude Opus 4.7 or GPT-5.4-Codex
       tools: ripgrep, tree-sitter, read/edit, run_tests, git
            |
            v
    verify CI passes in-sandbox + coverage delta check
            |
            v (verified)
    git push + open PR via GitHub App
       PR body = rationale + diff summary + trace URL
       label: needs-review
            |
            v
    operator reviews; can @-mention agent for follow-ups
```

## Stack · 技术栈

- 触发：带细粒度令牌的 GitHub App；webhook 接收端用 Lambda 或 Fly.io
- Worker：ECS Fargate 任务（或 GitHub Actions 自托管 runner）
- 沙箱：每个任务一个 Daytona devcontainer 或 E2B 沙箱
- Agent 循环：mini-swe-agent 基线或 SWE-agent v2，底层 Claude Opus 4.7 / GPT-5.4-Codex
- 检索：tree-sitter 仓库地图 + ripgrep
- 验证：沙箱内完整 CI + 覆盖率差值闸门
- 可观测性：Langfuse，按 PR 归档 trace，从 PR 正文链接过去
- 预算：每仓库每天美元上限；每仓库每天最大 PR 数

```figure
cf-issue-to-pr
```

## Build It · 动手造

1. **GitHub App。** 细粒度安装令牌：issues 读+写、pull_requests 写、contents 读+写、workflows 读。分支保护（唯一能做到这件事的机制）强制「禁止直接推 `main`」和「禁止 force-push」；该 App 不在绕过名单里。worker 在建议 diff 上以允许清单检查的方式强制「禁止写 `.github/workflows` 下的任何文件」，因为 GitHub App 权限不按路径划分。

2. **Webhook 接收端。** Lambda 函数接受 issue 标签 / PR 评论 webhook。按标签 `@agent fix this` 过滤。入队 SQS。

3. **分发器。** 从 SQS 弹出任务。执行按仓库按天的预算。带仓库 URL、issue 正文和一个全新 Daytona 沙箱拉起一个 ECS Fargate 任务。

4. **环境推断。** 检测语言（Python、Node、Go、Rust）和包管理器（uv、pnpm、go mod、cargo）。不存在 Dockerfile 时现场生成一个。

5. **Agent 循环。** mini-swe-agent 或 SWE-agent v2，底层 Claude Opus 4.7。工具：ripgrep、tree-sitter 仓库地图、read_file、edit_file、run_tests、git。硬上限：20 美元成本、30 分钟墙钟、30 个 agent 轮次。

6. **验证。** 循环结束后，在沙箱内跑完整测试套件。用 jacoco / coverage.py 计算覆盖率差值。CI 红：停止，不开 PR。覆盖率下降超过 2%：开 PR 但打 `needs-review` 标签。

7. **PR 发布。** 推送 agent 分支。通过 GitHub API 开 PR，包含：标题、理由、diff 摘要、trace URL、成本、轮次。

8. **凭据卫生。** worker 用短效 GitHub App 安装令牌运行。日志在归档前做机密擦除。

9. **评估。** 30 个不同难度的种子内部 issue。度量通过率、PR 质量（diff 体积、风格、覆盖率）、成本、延迟。在同样的 issue 上与 Cursor Background Agents 和 AWS Remote SWE Agents 对比。

> 1. **GitHub App.** Fine-grained installation token: issues read+write, pull_requests write, contents read+write, workflows read. Branch protection (the only surface that can do this) enforces "no direct push to `main`" and "no force-push"; the app is not in the bypass list. The worker enforces "no writes under `.github/workflows`" as an allow-list check on the proposed diff, since GitHub App permissions are not path-scoped.
> 6. **Verification.** After the loop concludes, run the full test suite in-sandbox. Compute coverage delta via jacoco / coverage.py. If CI red: halt, do not open PR. If coverage drops more than 2%: open PR with `needs-review` label.
> 8. **Credential hygiene.** Worker runs with a short-lived GitHub App installation token. Logs are scrubbed for secrets before archival.
> 9. **Eval.** 30 seeded internal issues of varying difficulty. Measure pass rate, PR quality (diff size, style, coverage), cost, latency.

## Use It · 实战用法

```
# on github.com
  - user labels issue #842 with `@agent fix this`
  - PR #1903 appears 14 minutes later
  - body:
    > Fixed NPE in widget.dedupe() caused by null comparator entry.
    > Added regression test widget_test.go::TestDedupeNullComparator.
    > Coverage delta: +0.12%
    > Turns: 7  Cost: $1.80  Trace: langfuse:...
    > Label: needs-review
```

## Ship It · 交付

`outputs/skill-issue-to-pr.md` 是交付物：一个 GitHub App + 异步云端 worker，把打了标签的 issue 变成可评审的 PR，成本有界、凭据受控。

| 权重 | 评分标准 | 度量方式 |
|:-:|---|---|
| 25 | 30 个 issue 上的通过率 | 端到端成功（CI 绿 + 覆盖率达标） |
| 20 | PR 质量 | diff 体积、覆盖率差值、风格一致性 |
| 20 | 每个已解决 issue 的成本与延迟 | 每 PR 的美元与墙钟时间 |
| 20 | 安全 | 令牌受控、按仓库预算、禁止 force-push、凭据卫生 |
| 15 | 操作者 UX | 理由说明、重试入口、@-mention 追问 |
| **100** | | |

> `outputs/skill-issue-to-pr.md` is the deliverable. A GitHub App + async cloud worker that turns labeled issues into review-ready PRs with bounded cost and scoped credentials.

## Exercises · 练习

1. 加一个「修复不稳定测试」模式：标签 `@agent stabilize-flake TestX` 让该测试在沙箱里跑 50 次，并提出让它稳定下来的最小改动。

2. 在三个共享 issue 上对比与 Cursor Background Agents 的成本。报告谁在哪里赢。

3. 实现一个预算仪表盘：按仓库按天的成本、按用户的成本。异常时告警。

4. 做一个「干跑」模式：不开 CI 就开一个草稿 PR，让评审者低成本地先审视计划。

5. 加一个保留策略：超过 7 天未合并的 PR 分支自动删除。

> 1. Add a "fix flaky test" mode: the label `@agent stabilize-flake TestX` runs the test 50 times in-sandbox and proposes a minimal change that stabilizes it.
> 4. Build a "dry-run" mode that opens a draft PR without running CI, so reviewers can examine the plan cheap.

## Key Terms · 术语表

| 术语 | 俗称 | 实际含义 |
|------|-----------------|------------------------|
| GitHub App | "受控范围的机器人身份" | 带细粒度权限 + 短效安装令牌的 App |
| Async cloud agent（异步云端 agent） | "后台 agent" | 在云端沙箱而非终端里运行的非交互式 worker |
| Environment inference（环境推断） | "Dockerfile 合成" | 检测语言 + 包管理器，缺失时生成 Dockerfile |
| Verification（验证） | "沙箱内 CI" | 开 PR 之前在 worker 内部跑完整测试套件 |
| Coverage delta（覆盖率差值） | "覆盖率保持" | 从基线到 agent 分支的测试覆盖率百分比变化 |
| Per-repo budget（按仓库预算） | "每日上限" | 在分发器强制执行的美元与 PR 数量上限 |
| Rationale（理由说明） | "PR 正文说明" | agent 对「改了什么、为什么」的总结；必须写进 PR 正文 |

## Further Reading · 延伸阅读

- [AWS Remote SWE Agents](https://github.com/aws-samples/remote-swe-agents) —— 异步云端 agent 的标杆参照
- [SWE-agent](https://github.com/SWE-agent/SWE-agent) —— CLI 参照
- [Cursor Background Agents](https://docs.cursor.com/background-agent) —— 商业替代
- [OpenAI Codex (cloud)](https://openai.com/codex) —— 托管竞争者
- [Google Jules](https://jules.google) —— Google 的托管版本
- [Factory Droids](https://www.factory.ai) —— 另一个商业参照
- [GitHub App documentation](https://docs.github.com/en/apps) —— 受控范围的机器人身份
- [Daytona cloud sandboxes](https://daytona.io) —— 参照沙箱
