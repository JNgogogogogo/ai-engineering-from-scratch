# Permission Modes for Autonomous Agents · 自主 Agent 的权限模式

> A permission ladder — graduated levels of autonomy from review-every-action to approve-everything — is how a harness governs what an autonomous agent may do without asking. Claude Code, this lesson's worked example, exposes six such modes: "plan" asks before every action, "default" (labeled "Manual" in the UI) asks only for risky ones, "acceptEdits" auto-approves file writes but still confirms shell execution, and "bypassPermissions" approves everything. Auto Mode — the `auto` permission mode — replaces per-action approval with a separate classifier model that reviews each action before it runs and blocks anything that escalates beyond what the request asked for. Action budgets are enforced via `max_turns` and `max_budget_usd`. Availability of `auto` depends on plan, org enablement, model, and provider — and Anthropic is explicit that the classifier is not sufficient alone.

**类型:** Learn（学习）
**语言:** Python（仅标准库；两阶段分类器模拟器）
**前置课程:** Phase 15 · 01（Long-horizon agents）、Phase 15 · 09（Coding-agent landscape）
**时间:** ~45 分钟

---

## The Problem · 问题在哪

跑在你机器上的自主编程 agent 是一个截然不同的安全类别。攻击面就是这个 agent 能触达的一切——文件系统、网络、凭证、剪贴板、任意浏览器标签页、任意打开的终端。Bruce Schneier 等人已公开指出这一点：computer-use agent 不是聊天机器人的「功能更新」，而是一类带着全新风险画像的新工具。

Claude Code 的权限系统是 Anthropic 给出的答案。它不是一个「自主 / 不自主」的开关，而是一架由六个模式构成的能力阶梯：plan → default → acceptEdits → … → bypassPermissions。每个模式都是「速度」与「逐动作审查」之间的一种不同取舍。Auto Mode（2026 年 3 月）加入了一个独立的分类器模型，把审批从用户的关键路径上挪走：它在每个动作运行之前审查，拦下任何超出请求范围的升级动作。

工程上的问题是：**这套系统能抓住什么、会漏掉什么，以及一个给定的任务到底该用哪个模式？**

> An autonomous coding agent on your machine is a distinct security category. The attack surface is everything the agent can reach — file system, network, credentials, clipboard, any browser tab, any open terminal. Bruce Schneier and others have flagged this publicly: computer-use agents are not a "feature update" of chatbots, they are a new kind of tool with a new kind of risk profile.
> Claude Code's permission system is Anthropic's answer. Rather than one "autonomous / not autonomous" switch, there are six modes spanning a capability ladder: plan → default → acceptEdits → … → bypassPermissions. ... Auto Mode (March 2026) adds a separate classifier model that moves approval off the user's critical path: it reviews each action before it runs and blocks anything that escalates beyond the request.
> The engineering question: what does this system catch, what does it miss, and which mode does a given task actually warrant?

---

## The Concept · 概念

### The six permission modes · 六种权限模式

| 模式 | 行为 | 何时使用 |
|---|---|---|
| `plan` | agent 提出一份计划；用户批准整份计划；每个动作在执行前都会被审查 | 不熟悉的任务；邻近生产的代码；第一次在某个仓库上使用该 agent |
| `default` | UI 中标注为「Manual」。agent 运行动作；任何「有风险」的动作（shell 执行、破坏性操作、网络调用）都会提示用户 | 大多数交互式编程会话 |
| `acceptEdits` | 文件写入自动批准；shell 执行和网络调用仍会提示 | 跨多个文件的重构 |
| `auto` | 一个独立的分类器模型在每个动作运行前审查；拦下任何超出请求的升级动作 | 受限工作区中的长程无人值守运行 |
| `dontAsk` | 从不提示；未被权限规则预先批准的动作直接拒绝 | 临时沙箱、CI 任务、研究脚本 |
| `bypassPermissions` | 批准一切 | 官方文档写明「只放在你愿意随时丢弃的临时容器里」 |

（以上名称与公开的 Claude Code 文档一致；UI 将 `default` 标注为「Manual」。）

> (Names above match public Claude Code docs; the UI labels `default` as "Manual".)

### Auto Mode in one page · 一页看懂 Auto Mode

Auto Mode（2026 年 3 月 24 日发布）是第一个把逐动作审批委托给模型的权限模式。结构：

1. **一个独立的分类器模型。** 在每个提议的动作运行之前审查它，以「声明的任务 + 会话当前状态」为判断依据，拦下任何超出请求所需范围的升级动作。被拦下的动作回退给用户处理。
2. **受门控的可用性。** `auto` 是否提供，取决于套餐（plan）、组织开关、模型和提供商。

预算控制与分类器并行：

- `max_turns` — 会话的总迭代次数。
- `max_budget_usd` — 触发会话中止的美元上限。
- 每个工具的动作次数上限（`WebFetch` 不得超过 N 次等）。

> Auto Mode (launched March 24, 2026) is the first permission mode to delegate per-action approval to a model. Structure:
> 1. **A separate classifier model.** Reviews every proposed action before it runs, judged against the declared task and the current state of the session, and blocks anything that escalates beyond what the request called for. Blocked actions fall back to the user.
> 2. **Gated availability.** Whether `auto` is offered at all depends on plan, organization enablement, model, and provider.
> Budget controls sit alongside the classifier:
> - `max_turns` — total iterations in a session.
> - `max_budget_usd` — dollar cap that aborts the session.
> - action-count limits per tool (no more than N `WebFetch` calls, etc.).

### What the system catches · 这套系统能抓住什么

- 直接写进工具输入的提示注入（prompt injection），且注入指令映射到已知的高风险动作形态。
- 重复的工具循环——分类器能看出动作 N+1 和动作 N 几乎相同，而且一连五次。
- 在一个本应只做文件编辑的会话里，出现明显越界的 shell 命令。

> - Straightforward prompt injection into tool inputs where the injected instruction maps to a known-risky action shape.
> - Repetitive tool loops — the classifier can see action N+1 is nearly identical to action N, five times in a row.
> - Clearly out-of-scope shell commands on an otherwise file-edit-only session.

### What the system can miss · 这套系统可能漏掉什么

- **隐蔽的提示注入**：不产生任何单个可被标记的动作，却能悄悄调制行为。间接提示注入（indirect prompt injection）不是一个能被完全修补的漏洞（OpenAI preparedness 负责人，2025，谈浏览器 agent——见第 11 课）。
- **语义层面的越轨。** 每个单独的动作看起来都安全，而复合起来的轨迹有害。分类器评判的是动作本身；它不会重新推导用户的意图。
- **经由合法通道的数据外泄（exfiltration）。** 把数据写进你拥有的文件，然后 `git push` 到一个公开仓库——每一步都是被允许的动作，问题出在组合上。

> - **Subtle prompt injection** that modulates behavior without producing a single flagged action. Indirect prompt injection is not a fully patchable vulnerability (OpenAI preparedness head, 2025, on browser agents — see Lesson 11).
> - **Semantic-level misbehavior.** Every individual action can look safe while the composed trajectory is harmful. The classifier judges the action; it does not re-derive the user's intent.
> - **Exfiltration through legitimate channels.** Writing data to a file you own, then `git push`ing to a public repo, is a sequence of allowed actions whose composition is the problem.

### Research preview framing · 「研究预览」的定位

Anthropic 以研究预览（research preview）的名义发布 Auto Mode。文档明确表示：分类器是一层防护，而不是一个解决方案——用户应当把 Auto Mode 与预算、允许清单（allowlist）、隔离工作区和轨迹审计结合使用（第 12–16 课）。「预览」这一定位也反映了有据可查的「评估 vs 部署」差距（第 1 课）：一个通过离线评估的分类器，在用户上下文含糊不清的真实会话里可能表现不同。

> Anthropic shipped Auto Mode as a research preview. The documentation is explicit that the classifier is a layer, not a solution: users are expected to combine Auto Mode with budgets, allowlists, isolated workspaces, and trajectory audits (Lessons 12–16). The preview framing also reflects the documented evaluation-vs-deployment gap (Lesson 1) — a classifier that passes offline evals can behave differently in a real session where the user's context is ambiguous.

### Where this ladder lives in your workflow · 这个阶梯如何嵌进你的工作流

- 不熟悉的任务：从 `plan` 开始。读一份计划，比回滚一次糟糕的运行便宜得多。
- 熟悉的重构：`acceptEdits` 能省掉大量确认点击。
- 无人值守的后台运行：`auto` 只在爆炸半径已被你测量过的工作区里使用（无凭证、无生产挂载、没有你未主动同意的对外连接）。
- 临时容器：当且仅当容器及其凭证都可抛弃时，`dontAsk` / `bypassPermissions` 才可接受。

```figure
autonomy-oversight
```

> - Unfamiliar task: start in `plan`. Reading the plan is cheaper than rolling back a bad run.
> - Known refactor: `acceptEdits` saves a lot of confirmation clicks.
> - Unattended background run: `auto` only inside a workspace whose blast radius you have measured (no credentials, no production mounts, no egress you did not opt into).
> - Ephemeral containers: `dontAsk` / `bypassPermissions` is acceptable if and only if the container and its credentials are disposable.

---

## Use It · 实战用法

`code/main.py` 把一个动作审查分类器模拟为两阶段流水线——这是教学上的简化；真实的 `auto` 模式背后是一个独立的分类器模型，而不是一份文档化的两阶段契约。阶段 1 是对提议动作的廉价关键词规则；阶段 2 是更慢的多规则审查器。驱动脚本喂入一段简短的合成轨迹（安全动作、一次提示注入尝试、一个重复循环），展示分类器在哪里抓住、在哪里漏掉。

> `code/main.py` simulates an action-review classifier as a two-stage pipeline — a teaching simplification; the real `auto` mode is backed by a separate classifier model, not a documented two-stage contract. Stage 1 is a cheap keyword rule over proposed actions; Stage 2 is a slower multi-rule reviewer. The driver feeds in a short synthetic trajectory (safe actions, a prompt-injection attempt, a repetitive loop) and shows where the classifier catches and where it misses.

---

## Ship It · 交付

`outputs/skill-permission-mode-picker.md` 把任务描述匹配到合适的权限模式、预算上限和所需的隔离措施。

> `outputs/skill-permission-mode-picker.md` matches a task description to the right permission mode, budget caps, and required isolation.

---

## Exercises · 练习

1. 运行 `code/main.py`。哪类合成动作从未被阶段 1 标记、却总能被阶段 2 抓住？哪类两边都抓不住？
2. 扩展阶段 1 的规则集，抓住一个具体的已知坏形态（例如 `curl $ATTACKER/exfil`）。在良性动作样本上测量误报率。
3. 读 Anthropic 的「How the agent loop works」文档。列出 agent 在 `default` 模式下默认触达的每一种外部状态。在无人值守运行 `auto` 之前，其中哪些需要单独设门？
4. 设计一个 24 小时无人值守运行的预算：`max_turns`、`max_budget_usd`、每工具上限、允许清单。为每个数字给出理由。
5. 描述这样一条轨迹：每个单独的动作都被分类器批准，但复合起来的行为是错位的。（第 14 课讲 kill switch 和 canary token 如何应对这个问题。）

> 1. Run `code/main.py`. Which synthetic action type is never flagged by Stage 1 but always caught by Stage 2? Which is caught by neither?
> 2. Extend the Stage 1 rule set to catch a specific known-bad shape (e.g., `curl $ATTACKER/exfil`). Measure the false-positive rate on the benign-action sample.
> 3. Read Anthropic's "How the agent loop works" doc. List every external state the agent touches by default in `default` mode. Which would you need to gate separately before running `auto` unattended?
> 4. Design a 24-hour unattended run budget: `max_turns`, `max_budget_usd`, per-tool caps, allowlists. Justify each number.
> 5. Describe one trajectory where every individual action is approved by the classifier, yet the composed behavior is misaligned. (Lesson 14 covers how kill switches and canary tokens address this.)

---

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|---|---|---|
| Permission mode | 「agent 能做多少事」 | 六种命名策略之一，控制逐动作审批 |
| plan mode | 「做任何事之前先问」 | agent 写出计划；用户批准后才执行 |
| acceptEdits | 「让它写文件」 | 文件写入自动批准；shell 执行仍会提示 |
| auto | 「自动批准」 | 独立分类器模型审查每个动作；拦下超出请求的升级 |
| bypassPermissions | 「完全放飞（Full YOLO）」 | 批准一切；面向临时容器 |
| Stage 1 (simulator) | 「快速关键词检查」 | `code/main.py` 中对提议动作的廉价规则 |
| Stage 2 (simulator) | 「深度审查」 | `code/main.py` 中针对被标记动作的较慢多规则审查器 |
| Research preview | 「未正式发布（Not GA）」 | Anthropic 对失败模式仍在摸底的功能的定位 |

---

## Further Reading · 延伸阅读

- [Anthropic — How the agent loop works](https://code.claude.com/docs/en/agent-sdk/agent-loop) — 权限模式、预算、动作格式。
- [Anthropic — Claude Managed Agents overview](https://platform.claude.com/docs/en/managed-agents/overview) — 托管服务的执行模型。
- [Anthropic — Claude Code product page](https://www.anthropic.com/product/claude-code) — 功能面与 Auto Mode 发布公告。
- [Anthropic — Claude's Constitution (January 2026)](https://www.anthropic.com/news/claudes-constitution) — 塑造分类器判断的「基于理由」层。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 关于长程权限设计的内部视角。
