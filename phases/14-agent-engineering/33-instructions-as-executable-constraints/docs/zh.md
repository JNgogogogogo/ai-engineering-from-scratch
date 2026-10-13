# Agent Instructions as Executable Constraints · 作为可执行约束的智能体指令

写成散文的指令是愿望；写成约束的指令是测试。工作台把每条规则变成智能体能在运行时检查、评审者能在事后验证的东西。

> Instructions written as prose are wishes. Instructions written as constraints are tests. The workbench turns each rule into something an agent can check at runtime and a reviewer can verify after the fact.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 32 (Minimal Workbench)
**Time:** ~50 minutes

## Learning Objectives · 学习目标

- 把路由散文与操作规则分离开来。
- 把启动规则、禁止动作、完成的定义、不确定性处理和审批边界表达成机器可检查的约束。
- 实现一个规则检查器（rule checker），对一次运行对照规则集打分。
- 让规则集对 diff 友好，让评审能看清改了什么。

> Separate routing prose from operational rules.
> Express startup rules, forbidden actions, definition of done, uncertainty handling, and approval boundaries as machine-checkable constraints.
> Implement a rule checker that scores a run against the rule set.
> Make the rule set diff-friendly so review can see what changed.

## The Problem · 问题在哪

一份典型的 `AGENTS.md` 读起来像入职文档。它让智能体「小心一点」「把测试做充分」「不确定就问」。三天后，智能体交付了一个没有测试的改动，写进了被禁止的目录，而且从头到尾没问过——因为它根本不知道线画在哪里。

指令在可操作时才有力量，在表达愿望时就很弱。解法是写出工作台能解释、评审者能打分的规则。

> A typical `AGENTS.md` reads like onboarding documentation. It tells the agent to "be careful" and "test thoroughly" and "ask if unsure." Three days later, the agent ships a change with no tests, writes to a forbidden directory, and never asks because it never knew where the line was.
> Instructions are powerful when they are operational and weak when they are aspirational. The fix is to write rules the workbench can interpret and the reviewer can score.

## The Concept · 概念

规则放在 `docs/agent-rules.md` 里，与简短的根路由器分开。每条规则有名字、类别和一个检查项。

```mermaid
flowchart LR
  Router[AGENTS.md] --> Rules[docs/agent-rules.md]
  Rules --> Checker[rule_checker.py]
  Checker --> Report[rule_report.json]
  Report --> Reviewer[Reviewer]
```

> Rules belong in `docs/agent-rules.md`, away from the short root router. Each rule has a name, a category, and a check.

### Five categories that cover most rules · 覆盖大多数规则的五个类别

| 类别 | 规则回答的问题 | 示例 |
|----------|---------------------------|---------|
| 启动（Startup） | 工作开始前什么必须为真？ | 「state 文件存在且新鲜」 |
| 禁止（Forbidden） | 什么事情绝不能发生？ | 「不要编辑 `scripts/release.sh`」 |
| 完成的定义（Definition of done） | 什么能证明任务完成了？ | 「pytest 退出码为 0 且验收行通过」 |
| 不确定性（Uncertainty） | 智能体不确定时做什么？ | 「开一张问题便签，而不是瞎猜」 |
| 审批（Approval） | 什么需要人类批准？ | 「任何新依赖、任何生产环境写入」 |

不属于这五类之一的规则，通常想变成两条规则。强制拆分。

> A rule that does not fit one of these five usually wants to be two rules. Force the split.

### Rules are machine-readable · 规则是机器可读的

每条规则有一个 slug、一个类别、一行描述，以及一个 `check` 字段，指向 `rule_checker.py` 里的一个函数。加一条规则就是加一个检查项；检查器随工作台一起生长。

> Each rule has a slug, a category, a one-line description, and a `check` field that names a function in `rule_checker.py`. Adding a rule means adding a check; the checker grows with the workbench.

### Rules are diff-friendly · 规则对 diff 友好

规则住在单个 markdown 文件里，一条规则一个标题。重命名在 diff 里一目了然。新规则放在所属类别的顶部。过时的规则直接删除，而不是注释掉——因为工作台才是事实来源，而不是团队上季度情绪的聊天记录。

> Rules live one per heading in a single markdown file. Renames are visible in diffs. New rules sit at the top of their category. Stale rules get deleted, not commented out, because the workbench is the source of truth, not the chat log of how the team felt last quarter.

### Rules versus framework guardrails · 规则与框架护栏

框架护栏（OpenAI Agents SDK guardrails、LangGraph interrupts）在运行时层面执行规则。本课的规则集是这些护栏所实现的人类可读、可评审的契约。两者都需要：运行时在一轮对话里捕获违规，规则集证明运行时做的是对的事。

> Framework guardrails (OpenAI Agents SDK guardrails, LangGraph interrupts) enforce rules at the runtime level. The rule set in this lesson is the human-readable, reviewable contract that those guardrails implement. You need both: the runtime catches violations during a turn, the rule set proves the runtime is doing the right thing.

### Progressive disclosure: a map, not an encyclopedia · 渐进式披露：给地图，不给百科全书

`AGENTS.md` 不断膨胀的原因是：每次事故都会加一条规则，而没有任何事故会删掉一条。一年之后，这个文件有两千行，智能体读完第一屏就用光了注意力预算，只按被告知内容的一小部分行事。巨型指令文件失败的原因，和四十页入职文档失败的原因一样：读者草草读一遍，再也不会回到真正重要的那部分。

解法不是一份更短的文件，而是一份分层的文件。根路由器保持小到每次会话都能读完，里面只有指针。深度放在主题文档里，智能体只在任务触及它们时才加载。给智能体一张地图，而不是整部百科全书，让它自己走到需要的那一页。

```
AGENTS.md                  # router, < 50 lines: what this repo is, where to look, the 5 hard rules
docs/
  agent-rules.md           # the full rule set (this lesson)
  architecture.md          # loaded when the task touches module boundaries
  testing.md               # loaded when the task writes or runs tests
  deploy.md                # loaded only for release work, gated behind an approval rule
feature_list.json          # the backlog (Phase 14 · 36)
```

| 层级 | 位置 | 何时读 | 大小预算 |
|------|----------|-----------|-------------|
| 路由器（Router） | `AGENTS.md` | 每次会话，必然 | 约 50 行以内 |
| 规则（Rules） | `docs/agent-rules.md` | 每次会话，启动时 | 每个类别一屏 |
| 主题文档（Topic docs） | `docs/<topic>.md` | 仅当任务触及该主题 | 需要多深就多深 |

两个测试保证分层不说谎。可达性测试：智能体从路由器出发最多两跳就该到达任何一条规则，所以路由器必须用路径链接每个主题文档，而不是用散文描述它。新鲜度测试：路由器足够短，短到评审者在每个 PR 上都会重读它——这是阻止它悄悄长回它所取代的那部百科全书的唯一机制。一个解析不了的指针比一条缺失的规则更糟，所以路由器里的坏链接本身就是一次启动检查违规。

> The reason `AGENTS.md` keeps growing is that every incident adds a rule and no incident removes one. A year in, the file is two thousand lines, and the agent reads the first screen, runs out of attention budget, and acts on a fraction of what it was told.
> The fix is not a shorter file. It is a layered one. The root router stays small enough to read every session and holds nothing but pointers. The depth lives in topic files the agent loads only when the task touches them.
> Two tests keep the layering honest. The reachability test: an agent should reach any rule in at most two hops from the router... The freshness test: the router is short enough that a reviewer rereads it on every PR, which is the only thing that stops it from silently growing back into the encyclopedia it replaced.

```figure
wb-rule-checkoff
```

## Build It · 动手造

`code/main.py` 包含：

- 把规则加载进 dataclass 的 `agent-rules.md` 解析器。
- `rule_checker.py` 风格的检查函数，每个 `check` 引用对应一个。
- 一次违反两条规则的演示运行，外加一轮把它们抓出来的检查。

运行：

```
python3 code/main.py
```

输出：解析后的规则集、运行轨迹、每条规则的通过/失败，以及保存在脚本旁边的 `rule_report.json`。

> `code/main.py` ships: an `agent-rules.md` parser that loads rules into a dataclass... `rule_checker.py` style checker functions, one per `check` reference... A demo agent run that violates two rules and a check pass that catches them.
> Output: parsed rule set, run trace, pass/fail per rule, and a `rule_report.json` saved next to the script.

## Production patterns in the wild · 野外生产模式

三个模式区分了能撑一个季度的规则集和一周就腐烂的规则集。

**写入时打严重性标签（severity tagging）。** 每条规则带有 `severity`：`block`、`warn` 或 `info`。检查器报告全部三种；运行时只对 `block` 拒绝。大多数团队早期高估严重性，然后在截止日期压力下悄悄调低；写入时打标签逼你提前完成校准。配合验证门（Phase 14 · 38）使用，它把任何对 `block` 规则的覆盖签入 `overrides.jsonl` 审计日志。

**规则过期作为倒逼机制（forcing function）。** 每条规则带有 `expires_at` 日期（默认为创建后 90 天）。当一条未过期规则连续 60 天零违规时，检查器发出警告；下一次季度评审要么给出保留它的理由，要么把它降级为 `info`，要么删掉它。Cloudflare 的生产级 AI Code Review 数据（2026 年 4 月，30 天内跨 5,169 个仓库的 131,246 次评审运行）显示：带显式过期的规则集保持在每仓库 30 条以内；不带的涨到 80 条以上，且大多数从未触发过。

**Markdown 做源文件，JSON 做缓存。** `agent-rules.md` 是人工编写的文件；`agent-rules.lock.json` 是检查器在热路径读取的缓存。锁文件由 pre-commit 钩子重新生成。Markdown 的 diff 可评审；JSON 解析不进入每一轮。与 `package.json` / `package-lock.json` 和 `Cargo.toml` / `Cargo.lock` 同一形状。

> Three patterns separate a rule set that lasts a quarter from one that decays in a week.
> Severity tagging at write time. Every rule carries `severity`: `block`, `warn`, or `info`... Pair with the verification gate (Phase 14 · 38), which signs any override of a `block` rule into a `overrides.jsonl` audit log.
> Rule expiry as a forcing function... Cloudflare's production AI Code Review data (April 2026, 131,246 review runs across 5,169 repos in 30 days) showed that rule sets with explicit expiry stayed under 30 rules per repo; sets without grew to 80+ with most never firing.
> Markdown-as-source, JSON-as-cache. `agent-rules.md` is the authored file; `agent-rules.lock.json` is a cache the checker reads in the hot path.

## Use It · 实战用法

在生产中：

- Claude Code、Codex、Cursor 在会话开始时读规则，并在拒绝动作时引用它们。检查器在 CI 里重跑这些检查，捕捉无声漂移。
- OpenAI Agents SDK guardrails 把同样的检查注册为输入和输出护栏。Markdown 是文档面；SDK 是运行时面。
- LangGraph interrupts 在执行中的节点违反规则时触发。中断处理器读取规则、询问人类、然后恢复。

规则集能在这三者之间移植，因为它只是 markdown 加函数名。

> In production: Claude Code, Codex, Cursor read the rules at session start and quote them when refusing actions. The checker re-runs them in CI to catch silent drift.
> OpenAI Agents SDK guardrails register the same checks as input and output guardrails. The markdown is the docs surface; the SDK is the runtime surface.
> LangGraph interrupts fire when an in-flight node violates a rule. The interrupt handler reads the rule, asks the human, and resumes.
> The rule set is portable across all three because it is just markdown plus function names.

## Ship It · 交付

`outputs/skill-rule-set-builder.md` 访谈项目负责人，把他们现有的散文指令归类到五个类别，并产出一份带版本的 `agent-rules.md` 加一个检查器桩（stub）。

> `outputs/skill-rule-set-builder.md` interviews a project owner, classifies their existing prose instructions into the five categories, and emits a versioned `agent-rules.md` plus a checker stub.

## Exercises · 练习

1. 如果你的产品确实需要第六个类别，就加上它，并论证它为什么不能坍缩进这五类。
2. 扩展检查器，让规则可以携带严重性（`block`、`warn`、`info`），并让报告相应地聚合。
3. 把检查器接进 CI：如果 block 级规则在最近一次智能体运行上失败，就让构建失败。
4. 给每条规则加一个「过期」字段。90 天没有检查失败后，该规则进入复审。
5. 找一份真实的 `AGENTS.md`，把它重写成五类别规则。它的行里有多少是可操作的？多少是表达愿望的？

> Add a sixth category if your product genuinely needs it. Defend why it does not collapse into one of the five.
> Extend the checker so a rule can carry a severity (`block`, `warn`, `info`) and the report aggregates accordingly.
> Wire the checker into CI: fail the build if a block-severity rule fails on the latest agent run.
> Add an "expiry" field per rule. After 90 days without a check fail, the rule is up for review.
> Find a real `AGENTS.md` and rewrite it as five-category rules. How many of its lines were operational? How many were aspirational?

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Operational rule（可操作规则） | 「一条真正的指令」 | 工作台能在运行时检查的规则 |
| Aspirational rule（愿望式规则） | 「小心一点」 | 没有检查项的规则；要么删除，要么升级 |
| Definition of done（完成的定义） | 「验收」 | 任务完成的、客观的、以文件为载体的证明 |
| Block severity（block 级严重性） | 「硬规则」 | 违规即中止运行；没有操作员参与就无法静音 |
| Rule expiry（规则过期） | 「过时规则清扫」 | N 天没有失败记录的规则进入退役流程 |

## Further Reading · 延伸阅读

- [OpenAI Agents SDK guardrails](https://openai.github.io/openai-agents-python/guardrails/)
- [LangGraph interrupts](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/breakpoints/)
- [Anthropic, Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Rick Hightower, Agent RuleZ: A Deterministic Policy Engine](https://medium.com/@richardhightower/agent-rulez-a-deterministic-policy-engine-for-ai-coding-agents-9489e0561edf) —— 生产环境中的 block/warn/info 严重性
- [Cloudflare, Orchestrating AI Code Review at Scale](https://blog.cloudflare.com/ai-code-review/) —— 13.1 万次评审运行，规则组合的经验教训
- [microservices.io, GenAI development platform — part 1: guardrails](https://microservices.io/post/architecture/2026/03/09/genai-development-platform-part-1-development-guardrails.html) —— 规则与 CI 之间的纵深防御
- [Type-Checked Compliance: Deterministic Guardrails (arXiv 2604.01483)](https://arxiv.org/pdf/2604.01483) —— Lean 4 作为「规则即检查」的上限
- [logi-cmd/agent-guardrails](https://github.com/logi-cmd/agent-guardrails) —— 合并门实现：范围、变异测试、违规预算
- Phase 14 · 32 —— 本规则集所嵌入的最小工作台
- Phase 14 · 38 —— 消费规则报告的验证门
- Phase 14 · 39 —— 给规则合规性打分的评审智能体
