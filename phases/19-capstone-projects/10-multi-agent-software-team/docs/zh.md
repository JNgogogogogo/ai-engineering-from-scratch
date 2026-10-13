# Capstone 10 — Multi-Agent Software Engineering Team · 毕业项目 10 —— 多智能体软件工程团队

> 2026 年多智能体工程团队的形态已经收敛：一名架构师做规划，N 个编码者在并行 worktree 中工作，一名评审者把关，一名测试者验证。SWE-AF 的工厂架构、MetaGPT 的角色化提示、AutoGen 0.4 的类型化 actor 图、Cognition 的 Devin、Factory 的 Droids，都不约而同落在这个形态上。并行 worktree 把墙钟时间换成了吞吐量；共享状态和交接协议则成为失效面。本次毕业项目要把这支团队造出来，在 SWE-bench Pro 上评估，并报告哪些交接会断、断得多频繁。

> The 2026 shape of a multi-agent engineering team has converged: an architect plans, N coders work in parallel worktrees, a reviewer gates, a tester verifies. SWE-AF's factory architecture, MetaGPT's role-based prompting, AutoGen 0.4's typed actor graph, Cognition's Devin, and Factory's Droids all landed on it independently. Parallel worktrees convert wall-clock into throughput. Shared state and handoff protocols become the failure surface. The capstone is to build the team, evaluate on SWE-bench Pro, and report which handoffs break and how often.

**Type:** Capstone
**Languages:** Python / TypeScript (agents), Shell (worktree scripts)
**Prerequisites:** Phase 11 (LLM engineering), Phase 13 (tools), Phase 14 (agents), Phase 15 (autonomous), Phase 16 (multi-agent), Phase 17 (infrastructure)
**Phases exercised:** P11 · P13 · P14 · P15 · P16 · P17
**Time:** 40 hours

## Problem · 问题

单 agent 编码工具在大任务上会撞到天花板。不是因为单个 agent 不够强，而是因为一个 20 万 token 的上下文装不下「一份架构规划 + 四个并行的代码切片 + 评审意见 + 测试输出」。多智能体工厂把问题拆开：架构师拥有规划，编码者在并行 worktree 里拥有实现，评审者把关，测试者验证。SWE-AF 的「工厂」架构、MetaGPT 的角色、AutoGen 的类型化 actor 图——三种表述说的是同一个形态。

失效面就是交接（handoff）。架构师规划出编码者实现不了的东西；编码者产出互相冲突的 diff；评审者批准了一个幻觉修复；测试者与还在写代码的编码者赛跑。你要把这样一支团队建出来，在 50 个 SWE-bench Pro issue 上运行，追踪每一次交接，并发布复盘报告（post-mortem）。

> Single-agent coding harnesses hit a ceiling on large tasks. Not because any individual agent is weak, but because a 200k-token context cannot hold an architecture plan plus four parallel codebase slices plus reviewer commentary plus test output. Multi-agent factories split the problem: an architect owns the plan, coders own implementation in parallel worktrees, a reviewer gates, a tester verifies. SWE-AF's "factory" architecture, MetaGPT's roles, AutoGen's typed actor graph — all three framings describe the same shape.
> The failure surface is the handoff. Architect plans something the coders cannot implement. Coders produce conflicting diffs. Reviewer approves a hallucinated fix. Tester races a still-writing coder. You will build one of these teams, run it on 50 SWE-bench Pro issues, track every handoff, and publish the post-mortem.

## Concept · 概念

角色是类型化的 agent。**架构师**（Claude Opus 4.7）读 issue、写规划，并把规划拆成带显式接口的子任务。**编码者**（Claude Sonnet 4.7，N 个并行实例，每个在一个 `git worktree` + Daytona 沙箱里）独立实现子任务。**评审者**（GPT-5.4）读合并后的 diff，要么批准，要么要求具体修改。**测试者**（Gemini 2.5 Pro）在隔离环境跑测试套件，附带工件（artifact）报告通过/失败。

通信通过一块共享任务板（文件或 Redis 存储）进行。每个角色只消费它被允许处理的任务。交接是 A2A 协议类型化的消息。协调要关心三件事：合并冲突消解（协调者角色或自动三方合并）、共享状态同步（编码者开跑后规划即冻结；重新规划是独立事件）、评审者把关（评审者不能批准自己写的或自己提议的改动）。

token 放大是隐性成本。每跨一次角色边界，都要追加总结提示和交接上下文。单 agent 40 轮的运行，摊到四个角色身上就是 160 轮。评分标准特意给「token 效率 vs 单 agent 基线」赋权，因为问题从来不是「多智能体行不行」，而是「每一美元能不能赢」。

> Roles are typed agents. **Architect** (Claude Opus 4.7) reads the issue, writes a plan, and breaks it into subtasks with explicit interfaces. **Coders** (Claude Sonnet 4.7, N parallel instances, each in a `git worktree` + Daytona sandbox) implement subtasks independently. **Reviewer** (GPT-5.4) reads the merged diff and either approves or requests specific changes. **Tester** (Gemini 2.5 Pro) runs the test suite in isolation and reports pass/fail with artifacts.
> Communication is through a shared task board (file-backed or Redis). Each role consumes tasks it is permitted to handle. Handoffs are A2A-protocol-typed messages. Coordination concerns: merge-conflict resolution (coordinator role or automatic three-way merge), shared-state synchronization (the plan is frozen once coders start; replans are separate events), and reviewer gatekeeping (the reviewer cannot approve its own changes or changes it proposed).
> Token amplification is the hidden cost. Every role boundary adds summary prompts and handoff context. A 40-turn single-agent run becomes 160 total turns across four roles. The rubric specifically weighs token efficiency vs single-agent baseline because the question is not "does multi-agent work" but "does it win per dollar."

## Architecture · 架构

```
GitHub issue URL
      |
      v
Architect (Opus 4.7)
   reads issue, produces plan with subtasks + interfaces
      |
      v
Task board (file / Redis)
      |
   +-- subtask 1 ---+-- subtask 2 ---+-- subtask 3 ---+-- subtask 4 ---+
   v                v                v                v                v
Coder A          Coder B          Coder C          Coder D          (4 parallel)
 (Sonnet)         (Sonnet)         (Sonnet)         (Sonnet)
 worktree A       worktree B       worktree C       worktree D
 Daytona          Daytona          Daytona          Daytona
      |                |                |                |
      +--------+-------+-------+--------+
               v
           merge coordinator  (three-way merge + conflict resolution)
               |
               v
           Reviewer (GPT-5.4)
               |
               v
           Tester  (Gemini 2.5 Pro)  -> passes? -> open PR
                                     -> fails?  -> route back to coder
```

## Stack · 技术栈

- 编排：LangGraph + 共享状态 + 每个 agent 独立子图
- 消息：A2A 协议（Google 2025）承载类型化的 agent 间消息
- 模型：Opus 4.7（架构师）、Sonnet 4.7（编码者）、GPT-5.4（评审者）、Gemini 2.5 Pro（测试者）
- Worktree 隔离：每个编码者一个 `git worktree add` + Daytona 沙箱
- 合并协调器：自定义三方合并 + LLM 居中调解冲突
- 评估：SWE-bench Pro（50 个 issue）、SWE-AF 场景、HumanEval++ 单元测试
- 可观测性：Langfuse 带角色标签的 span，按 agent 做 token 计量
- 部署：K8s，每个角色一个独立 Deployment，按积压量（backlog）做 HPA

```figure
ce-team-handoff
```

## Build It · 动手造

1. **任务板。** 基于文件的 JSONL，消息带类型：`plan_request`、`subtask`、`diff_ready`、`review_needed`、`test_needed`、`approved`、`rejected`、`replan_needed`。agent 按标签订阅。

2. **架构师。** 读 GitHub issue，用 Opus 4.7 配合一份规划模板运行，模板要求子任务接口显式（触及哪些文件、公开函数、测试影响）。产出一条带子任务 DAG 的 `plan_request`。

3. **编码者。** N 个并行 worker，各自从任务板认领一个子任务。每个 worker 新开一个 `git worktree add` 分支加一个 Daytona 沙箱。实现子任务后，产出带补丁和测试增量的 `diff_ready`。

4. **合并协调器。** 全部编码者完成后，把 N 个分支三方合并进一个 staging 分支。只有存在文件级重叠时才让 LLM 居中调解冲突。

5. **评审者。** GPT-5.4 读合并后的 diff。不能批准自己写的 diff。产出 `approved`（无操作）或带具体修改要求的 `review_feedback`，并路由回相应的编码者。

6. **测试者。** Gemini 2.5 Pro 在干净沙箱里跑测试套件，收集工件，产出 `test_passed` 或带堆栈的 `test_failed`。失败的测试回流到拥有该失败子任务的编码者。

7. **交接记账。** 每条跨越角色边界的消息都在 Langfuse 里记一个 span，附载荷大小和所用模型。计算每个子任务的 token 放大率（coder_tokens + reviewer_tokens + tester_tokens + architect_share / coder_tokens）。

8. **评估。** 在 50 个 SWE-bench Pro issue 上运行。与单 agent 基线（一个 Sonnet 4.7 在单个 worktree 里）比较 pass@1 和每个已解决 issue 的成本。

9. **复盘。** 对每个失败的 issue，定位断掉的交接（规划太模糊、合并冲突、评审者误批准、测试抖动）。产出一张交接失败直方图。

> 1. **Task board.** File-backed JSONL with typed messages: `plan_request`, `subtask`, `diff_ready`, `review_needed`, `test_needed`, `approved`, `rejected`, `replan_needed`. Agents subscribe to tags.
> 5. **Reviewer.** GPT-5.4 reads the merged diff. Cannot approve diffs it authored.
> 7. **Handoff accounting.** Every message crossing a role boundary gets a span in Langfuse with payload size and model used.
> 9. **Post-mortem.** For each failed issue, identify the handoff that broke (plan too vague, merge conflict, reviewer false-approve, tester flake). Produce a handoff-failure histogram.

## Use It · 实战用法

```
$ team run --issue https://github.com/acme/widget/issues/842
[architect] plan: 4 subtasks (parser, cache, api, migration)
[board]     dispatched to 4 coders in parallel worktrees
[coder-A]   subtask parser  -> 42 lines, tests pass locally
[coder-B]   subtask cache   -> 88 lines, tests pass locally
[coder-C]   subtask api     -> 31 lines, tests pass locally
[coder-D]   subtask migration -> 19 lines, tests pass locally
[merge]     3-way merge: 0 conflicts
[reviewer]  comments on cache (thread pool sizing); routed to coder-B
[coder-B]   revision: 92 lines; submits
[reviewer]  approved
[tester]    all 412 tests pass
[pr]        opened #3382   4 coders, 1 revision, $4.90, 18m
```

## Ship It · 交付

`outputs/skill-multi-agent-team.md` 是交付物。给定一个 issue URL 和并行度，团队产出一个可合并的 PR，并附按角色计量的 token 账目。

| 权重 | 评分标准 | 度量方式 |
|:-:|---|---|
| 25 | SWE-bench Pro pass@1 | 匹配的 50 issue 子集，pass@1 |
| 20 | 并行加速 | 墙钟时间 vs 单 agent 基线 |
| 20 | 评审质量 | 注入缺陷探针上的误批准率 |
| 20 | Token 效率 | 每解决一个 issue 的总 token vs 单 agent |
| 15 | 协调工程 | 合并冲突消解、交接失败直方图 |
| **100** | | |

> `outputs/skill-multi-agent-team.md` is the deliverable. Given an issue URL and parallelism level, the team produces a merge-ready PR with per-role token accounting.

## Exercises · 练习

1. 在运行中途往一个 diff 里注入一个明显的 bug（主体前面多一个 `return None`）。度量评审者的误批准率。调评审者提示词，直到误批准低于 5%。

2. 减到两个编码者（架构师 + 编码者 + 评审者 + 测试者，编码者按顺序做两个子任务）。比较墙钟时间和通过率。

3. 把合并协调器换成单写者约束（各子任务触及互不相交的文件集合）。度量这给架构师增加的规划负担。

4. 把评审者从 GPT-5.4 换成 Claude Opus 4.7。度量误批准率和 token 成本差。

5. 加第五个角色：文档员（Haiku 4.5）。评审通过后，它产出一个 changelog 条目。度量文档质量是否值这点额外的 token 开销。

> 1. Inject an obvious bug into a diff mid-run (extra `return None` before the main body). Measure the reviewer's false-approve rate. Tune the reviewer prompt until false-approval is under 5%.
> 5. Add a fifth role: documenter (Haiku 4.5). After review, it produces a changelog entry. Measure whether documentation quality justifies the extra token spend.

## Key Terms · 术语表

| 术语 | 俗称 | 实际含义 |
|------|-----------------|------------------------|
| Parallel worktree（并行工作树） | "隔离分支" | `git worktree add` 为每个编码者产出一个全新工作树 |
| Task board（任务板） | "共享消息总线" | 文件或 Redis 存储的类型化消息，agent 订阅消费 |
| Handoff（交接） | "角色边界" | 任何从一个角色上下文跨越到另一个角色上下文的消息 |
| Token amplification（token 放大） | "多智能体开销" | 各角色 token 总量 / 单 agent 完成同一任务的 token |
| A2A protocol | "agent 到 agent" | Google 2025 年的类型化 agent 间消息规范 |
| Merge coordinator（合并协调器） | "集成者" | 执行三方合并并调解冲突的组件 |
| False approval（误批准） | "评审者幻觉" | 评审者批准了带有已知缺陷的 diff |

## Further Reading · 延伸阅读

- [SWE-AF factory architecture](https://github.com/Agent-Field/SWE-AF) —— 2026 年多智能体工厂的参照实现
- [MetaGPT](https://github.com/FoundationAgents/MetaGPT) —— 基于角色的多智能体框架
- [AutoGen v0.4](https://github.com/microsoft/autogen) —— 微软的类型化 actor 框架
- [Cognition AI (Devin)](https://cognition.ai) —— 参照产品
- [Factory Droids](https://www.factory.ai) —— 另一个参照产品
- [Google A2A protocol](https://a2a-protocol.org/latest/) —— agent 间消息规范
- [git worktree documentation](https://git-scm.com/docs/git-worktree) —— 隔离的底层机制
- [SWE-bench Pro](https://www.swebench.com) —— 评估目标
