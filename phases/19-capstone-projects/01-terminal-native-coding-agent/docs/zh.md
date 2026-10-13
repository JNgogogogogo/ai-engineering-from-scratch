# Capstone 01 — Terminal-Native Coding Agent · 终端原生编码智能体

> 到 2026 年，编码智能体的形态已经定型。一个 TUI harness（驱动层）、一份有状态的计划、一个沙箱化的工具面、一个「计划-行动-观察-恢复」循环。Claude Code、Cursor 3 和 OpenCode 从 50 英尺外看全都一个样。这个毕业项目（capstone）要你端到端地造一个 —— CLI 进，pull request 出 —— 并在 SWE-bench Pro 上与 mini-swe-agent 和 Live-SWE-agent 对标测量。你会明白：难的不是模型调用，而是工具循环、沙箱，以及 50 轮运行的成本上限。

> By 2026 the shape of a coding agent is settled. A TUI harness, a stateful plan, a sandboxed tool surface, a loop that plans, acts, observes, recovers. Claude Code, Cursor 3, and OpenCode all look the same from 50 feet. This capstone asks you to build one end to end — CLI in, pull request out — and measure it against mini-swe-agent and Live-SWE-agent on SWE-bench Pro. You will learn why the hard part is not the model call but the tool loop, the sandbox, and the cost ceiling on a 50-turn run.

**类型（Type）:** 毕业项目（Capstone）
**语言（Languages）:** TypeScript / Bun（harness）、Python（评估脚本）
**先修（Prerequisites）:** Phase 11（LLM 工程）、Phase 13（工具与协议）、Phase 14（智能体 agent）、Phase 15（自治系统）、Phase 17（基础设施）
**实践阶段（Phases exercised）:** P0 · P5 · P7 · P10 · P11 · P13 · P14 · P15 · P17 · P18
**时间（Time）:** 35 小时

## Problem · 问题

2026 年，编码智能体成为占主导地位的 AI 应用品类。Claude Code（Anthropic）、带 Composer 2 与 Agent Tabs 的 Cursor 3（Cursor）、Amp（Sourcegraph）、OpenCode（112k stars）、Factory Droids、Google Jules，全都在交付同一套架构的变体：一个终端 harness、一个带权限控制的工具面、一个沙箱（sandbox），以及围绕前沿模型构建的「计划-行动-观察」循环。前沿很窄 —— Live-SWE-agent 用 Opus 4.5 在 SWE-bench Verified 上达到 79.2% —— 但工程工艺面很宽。大多数失败模式不是模型犯错，而是工具循环不稳定、上下文污染（context poisoning）、token 成本失控，以及破坏性的文件系统操作。

你没法从外面想明白这些智能体。你必须亲手造一个，看着循环在第 47 轮因为 ripgrep 返回 8MB 匹配结果而崩溃，然后把截断层重写一遍。这就是本毕业项目的意义所在。

> Coding agents became the dominant AI application category in 2026. ... Most failure modes are not model mistakes. They are tool-loop instability, context poisoning, runaway token cost, and destructive filesystem operations. ... You cannot reason about these agents from the outside. You have to build one, watch the loop crash on turn 47 when ripgrep returns 8MB of matches, and rebuild the truncation layer. That is the point of this capstone.

## Concept · 概念

harness 有四个面。**Plan（计划）** 维护一个 TodoWrite 风格的状态对象，模型每一轮重写它。**Act（行动）** 分发工具调用（read、edit、run、search、git）。**Observe（观察）** 捕获 stdout / stderr / 退出码，做截断，把摘要喂回去。**Recover（恢复）** 处理工具错误，既不撑爆上下文窗口，也不无限循环。2026 年的形态又多了一样东西：**hooks（钩子）**。`PreToolUse`、`PostToolUse`、`SessionStart`、`SessionEnd`、`UserPromptSubmit`、`Notification`、`Stop`、`PreCompact` —— 可配置的扩展点，运维者在这里注入策略、遥测与护栏。

沙箱用 E2B 或 Daytona。每个任务在一个全新 devcontainer 里运行，挂载一个可读写的 git worktree（工作树）。harness 绝不触碰宿主文件系统。无论成功或失败，worktree 都会被拆除。成本控制在三层强制执行：单轮 token 上限、单会话美元预算、硬性轮次上限（通常 50 轮）。可观测层是带 GenAI 语义约定（semantic conventions）的 OpenTelemetry span，送往自托管的 Langfuse。

> The harness has four surfaces. **Plan** maintains a TodoWrite-style state object that the model rewrites each turn. **Act** dispatches tool calls (read, edit, run, search, git). **Observe** captures stdout / stderr / exit codes, truncates, and feeds the summary back. **Recover** handles tool errors without blowing the context window or looping forever. ... The sandbox is E2B or Daytona. Each task runs in a fresh devcontainer with a git worktree mounted read-write. ... Cost control is enforced at three layers: a per-turn token ceiling, a per-session dollar budget, and a hard turn limit (typically 50). The observability layer is OpenTelemetry spans with GenAI semantic conventions, shipped to a self-hosted Langfuse.

## Architecture · 架构

```
  user CLI  ->  harness (Bun + Ink TUI)
                  |
                  v
           plan / act / observe loop  <--->  Claude Sonnet 4.7 / GPT-5.4-Codex / Gemini 3 Pro
                  |                          (via OpenRouter, model-agnostic)
                  v
           tool dispatcher (MCP StreamableHTTP client)
                  |
     +------------+------------+----------+
     v            v            v          v
  read/edit    ripgrep     tree-sitter   git/run
     |            |            |          |
     +------------+------------+----------+
                  |
                  v
           E2B / Daytona sandbox  (worktree isolated)
                  |
                  v
           hooks: Pre/Post, Session, Prompt, Compact
                  |
                  v
           OpenTelemetry -> Langfuse (spans, tokens, $)
                  |
                  v
           PR via GitHub app
```

## Stack · 技术栈

- Harness 运行时：Bun 1.2 + Ink 5（终端里的 React）
- 模型访问：OpenRouter 统一 API，覆盖 Claude Sonnet 4.7、GPT-5.4-Codex、Gemini 3 Pro、Opus 4.5（用于最难的任务）
- 工具传输：Model Context Protocol StreamableHTTP（MCP 2026 修订版）
- 沙箱：E2B sandboxes（JS SDK）或 Daytona devcontainers
- 代码搜索：ripgrep 子进程，17 种语言的 tree-sitter 解析器（预编译）
- 隔离：每个任务 `git worktree add`，成功 / 失败后清理
- 评估 harness：SWE-bench Pro（verified 子集）+ Terminal-Bench 2.0 + 你自己的 30 任务 holdout
- 可观测性：带 `gen_ai.*` 语义约定的 OpenTelemetry SDK → 自托管 Langfuse
- PR 发布：GitHub App 配细粒度 token，权限范围仅限目标仓库

> - Harness runtime: Bun 1.2 + Ink 5 (React-in-terminal)
> - Model access: OpenRouter unified API with Claude Sonnet 4.7, GPT-5.4-Codex, Gemini 3 Pro, Opus 4.5 (for hardest tasks)
> - Tool transport: Model Context Protocol StreamableHTTP (MCP 2026 revision)
> - Sandbox: E2B sandboxes (JS SDK) or Daytona devcontainers
> - Code search: ripgrep subprocess, tree-sitter parsers for 17 languages (pre-compiled)
> - Isolation: `git worktree add` per task, cleanup on success / failure
> - Eval harness: SWE-bench Pro (verified subset) + Terminal-Bench 2.0 + your own 30-task holdout
> - Observability: OpenTelemetry SDK with `gen_ai.*` semconv → self-hosted Langfuse
> - PR posting: GitHub App with fine-grained token, scope limited to the target repo

```figure
ce-agent-loop
```

## Build It · 动手造

1. **TUI 与命令循环。** 用 Ink 脚手架一个 Bun 项目。接受 `agent run <repo> "<task>"`。打印一个分栏视图：计划面板（上）、工具调用流（中）、token 预算（下）。Ctrl-C 取消时先触发 `SessionEnd` hook 再退出。

2. **计划状态。** 定义一个带类型的 TodoWrite schema（pending / in_progress / done 条目加 notes）。模型每轮以一次工具调用的形式重写完整状态 —— 不要让它增量式修改。把计划持久化到 `.agent/state.json`，崩溃后可恢复。

3. **工具面。** 定义六个工具：`read_file`、`edit_file`（带 diff 预览）、`ripgrep`、`tree_sitter_symbols`、`run_shell`（带超时）、`git`（status / diff / commit / push）。通过 MCP StreamableHTTP 暴露，让 harness 与传输方式解耦。每个工具返回截断后的输出（每次调用上限 4k token）。

4. **沙箱包装。** 每个任务启动一个 E2B 沙箱。用 `git worktree add -b agent/$TASK_ID` 建一条新分支。所有工具调用都在沙箱内执行。宿主文件系统不可达。

5. **Hooks。** 实现 2026 年全部八种 hook 类型。至少接四个用户自定义 hook：(a) `PreToolUse` 破坏性命令守卫，拦截 worktree 之外的 `rm -rf`；(b) `PostToolUse` token 记账；(c) `SessionStart` 预算初始化；(d) `Stop` 写出最终 trace 包。

6. **评估循环。** 克隆 SWE-bench Pro Python 的 30 个 issue 子集。用你的 harness 逐个跑。在 pass@1、每任务轮数、每任务美元成本上与 mini-swe-agent（极简基线）对比。结果写入 `eval/results.jsonl`。

7. **成本控制。** 硬性上限：50 轮、200k 上下文、每任务 $5。`PreCompact` hook 在 150k 位置把更早的轮次摘要成一个先验状态块，为新观察腾出空间且不丢计划。

8. **PR 发布。** 成功时，最后一步是 `git push` + 一次 GitHub API 调用，开一个 PR，正文带上计划和 diff 摘要。

> **TUI and command loop.** Scaffold a Bun project with Ink. Accept `agent run <repo> "<task>"`. Print a split view: plan pane (top), tool-call stream (middle), token budget (bottom). ... **Plan state.** Define a typed TodoWrite schema (pending / in_progress / done items with notes). Model rewrites the full state each turn as a tool call — do not let it mutate incrementally. ... **Tool surface.** Define six tools: `read_file`, `edit_file` (with diff preview), `ripgrep`, `tree_sitter_symbols`, `run_shell` (with timeout), `git` (status / diff / commit / push). Every tool returns truncated output (cap at 4k tokens per call). ... **Sandbox wrapping.** Each task spawns an E2B sandbox. All tool calls execute inside the sandbox. Host filesystem is unreachable. ... **Cost control.** Hard cutoffs: 50 turns, 200k context, $5 per task.

## Use It · 实战用法

```
$ agent run ./my-repo "Fix the race condition in worker.rs"
[plan]  1 locate worker.rs and enumerate mutex uses
        2 identify shared state under contention
        3 propose fix, verify tests
[tool]  ripgrep mutex.*lock -t rust           (44 matches, truncated)
[tool]  read_file src/worker.rs 120..180
[tool]  edit_file src/worker.rs (+8 -3)
[tool]  run_shell cargo test worker::          (passed)
[plan]  1 done · 2 done · 3 done
[done]  PR opened: #482   turns=9   tokens=38k   cost=$0.41
```

## Ship It · 交付

交付的 skill 在 `outputs/skill-terminal-coding-agent.md`。给定一个仓库路径和一个任务描述，它在沙箱里跑完整的「计划-行动-观察」循环，返回一个 PR URL 和一个 trace 包。本毕业项目的评分标准：

| 权重 | 标准 | 如何衡量 |
|:-:|---|---|
| 25 | SWE-bench Pro pass@1 对比基线 | 你的 harness 与 mini-swe-agent 在 30 个配对 Python 任务上对比 |
| 20 | 架构清晰度 | plan/act/observe 分离、hook 面、工具 schema —— 对照 Live-SWE-agent 布局评审 |
| 20 | 安全性 | 沙箱逃逸测试、权限提示、破坏性命令守卫通过红队（red team）测试 |
| 20 | 可观测性 | trace 完整性（100% 的工具调用有 span）、逐轮 token 记账 |
| 15 | 开发者 UX | 冷启动 < 2s、崩溃恢复可续接计划、Ctrl-C 在工具执行中干净取消 |
| **100** | | |

> The deliverable skill lives in `outputs/skill-terminal-coding-agent.md`. Given a repo path and a task description, it runs the full plan-act-observe loop in a sandbox and returns a PR URL plus a trace bundle.

## Exercises · 练习

1. 把背后的模型从 Claude Sonnet 4.7 换成 vLLM 上服务的 Qwen3-Coder-30B。对比 pass@1 和每任务美元成本。报告开源模型在哪些地方落后。

2. 加一个 `reviewer` 子智能体，在发 PR 前读 diff，并且可以要求进入修订循环。衡量误报评审会不会把 SWE-bench pass 率拖到单智能体基线之下（提示：通常会）。

3. 对沙箱做压力测试：写一个尝试 `curl` 外部 URL 的任务和一个写到 worktree 之外的任务。确认两者都被 PreToolUse hook 拦截。记录这些尝试。

4. 用一个更小的模型（Haiku 4.5）实现 `PreCompact` 摘要。衡量 3 倍压缩时会丢失多少计划保真度。

5. 把 MCP StreamableHTTP 传输换成 stdio。对冷启动和单次调用延迟做基准测试。为纯本地使用场景选出一个赢家。

> Swap the backing model from Claude Sonnet 4.7 to Qwen3-Coder-30B served on vLLM. Compare pass@1 and $-per-task. ... Add a `reviewer` sub-agent that reads the diff before PR posting and can request a revision loop. Measure whether false-positive reviews drop SWE-bench pass rate below the single-agent baseline. ... Stress-test the sandbox: write a task that tries to `curl` an external URL and a task that writes outside the worktree. Confirm both are blocked by the PreToolUse hook. ... Implement `PreCompact` summarization with a smaller model (Haiku 4.5). Measure how much plan fidelity is lost at 3x compaction. ... Swap MCP StreamableHTTP transport for stdio. Benchmark cold-start and per-call latency.

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|------------------------|
| Harness | 「智能体循环」 | 包裹模型的代码：分发工具、维护计划状态、执行预算 |
| Hook | 「智能体事件监听器」 | 由 harness 在八种生命周期事件之一上运行的用户脚本 |
| Worktree | 「Git 沙箱」 | 位于独立路径的关联 git 检出；可随意丢弃而不影响主克隆 |
| TodoWrite | 「计划状态」 | 一份带类型的 pending/in-progress/done 条目列表，模型每轮重写 |
| StreamableHTTP | 「MCP 传输」 | 2026 MCP 修订：带双向流的长连接 HTTP；取代 SSE |
| Token ceiling | 「上下文预算」 | 按轮或按会话的输入+输出 token 上限；触发压缩或终止 |
| pass@1 | 「单次尝试通过率」 | 首次运行即解决、不重试、不看测试集的 SWE-bench 任务比例 |

## Further Reading · 延伸阅读

- [Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code) — Anthropic 官方参考 harness
- [Cursor 3 changelog](https://cursor.com/changelog) — Agent Tabs 与 Composer 2 的产品说明
- [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) — SWE-bench harness 对比用的极简基线
- [Live-SWE-agent](https://github.com/OpenAutoCoder/live-swe-agent) — 用 Opus 4.5 达到 79.2% SWE-bench Verified
- [OpenCode](https://opencode.ai) — 开源 harness，112k stars
- [SWE-bench Pro leaderboard](https://www.swebench.com) — 本毕业项目瞄准的评估
- [Model Context Protocol 2026 roadmap](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/) — StreamableHTTP、能力元数据
- [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) — 工具调用与 token 用量的 span schema
