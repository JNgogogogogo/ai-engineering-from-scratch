# Skill Invocation and Routing · 技能调用与路由

> Invocation is an authority decision followed by a relevance decision. A good description helps the model choose; a good policy decides whether that choice is allowed.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 13 · 24 (Skill Discovery and Progressive Disclosure)
**Time:** ~105 minutes

## Learning Objectives · 学习目标

- 区分显式用户调用、隐式模型调用、应用调用和技能对技能（skill-to-skill）调用。
- 把人类可见性与模型可选性建模为相互独立的策略维度。
- 编写带正向触发器和近似命中（near-miss）边界的路由描述。
- 在追踪和测试中把资格（eligibility）、选择（selection）、激活（activation）、参数绑定（argument binding）与执行分开。
- 适配特定运行时的调用字段，而不把它们伪装成可移植的 frontmatter。

> Distinguish explicit user invocation, implicit model invocation, application invocation, and skill-to-skill invocation.
> Model human visibility and model eligibility as independent policy dimensions.
> Write routing descriptions with positive triggers and near-miss boundaries.
> Separate eligibility, selection, activation, argument binding, and execution in traces and tests.
> Adapt runtime-specific invocation fields without presenting them as portable frontmatter.

## The Problem · 问题在哪

你安装了一个 `database-migration` 技能。用户可以按名字运行它，但模型也会看到它的描述，并且在有人问一个一般性数据库问题时就选中它。这个技能随后为一个只需要解释的任务提出了 schema 变更。

你加上 `user-invocable: false`，指望阻止人们手动运行它。在另一个运行时里，这个字段被忽略。你加上 `disable-model-invocation: true`，指望技能彻底消失。在理解它的那个运行时里，用户仍然可以显式调用它。

字段名没有错，错的是模型的心智图景。「用户能看到它」「模型能选中它」「应用能预加载它」「它里面的工具能执行」是四个相互独立的事实。一个叫 `invocable` 的布尔值表达不了它们。

路由还有第二种失败模式。如果描述含糊，多个技能都显得合理；如果描述堆满关键词，无关任务也会触发它们。目录是一个概率式接口：足够紧凑以装得下，足够具体以完成路由。

> You install a `database-migration` skill. The user can run it by name, but the model also sees its description and selects it when someone asks a general database question. The skill then proposes a schema change for a task that only needed an explanation.
> Routing has a second failure mode. If descriptions are vague, several skills become plausible. If descriptions are stuffed with keywords, unrelated tasks trigger them. The catalog is a probabilistic interface: compact enough to fit, specific enough to route.

## The Concept · 概念

### Five channels can start the lifecycle · 五种通道都能启动生命周期

| 行为者 | 调用形态 | 典型用途 | 主要风险 |
|---|---|---|---|
| 人类用户 | 在 UI 或提示中点名一个技能 | 有意的工作流选择 | 用户期待宿主并未授予的可用性或权限 |
| 模型或自主 agent | 从任务上下文中选中一个目录条目 | 自动化的专家规程 | 误报路由（false-positive routing） |
| 应用 | 通过运行时代码激活或预加载技能 | 固定的产品工作流 | 与单一宿主的隐藏耦合 |
| 另一个技能或子 agent | 把某个技能当作工作流依赖来请求 | 组合 | 循环、依赖缺失或上下文渗漏 |
| 评测框架（harness） | 在固定场景下激活指定的技能 | 可重复的测量 | 测了技能本身，却意外绕过了正在研究的生产策略 |

可移植的 Agent Skills 规范定义的是包。它不标准化任何通用的斜杠命令 UI、隐式路由标志、应用 API 或子 agent 生命周期。

> The portable Agent Skills specification defines the package. It does not standardize one universal slash-command UI, implicit-routing flag, application API, or subagent lifecycle.

### The five invocation stages · 五个调用阶段

```figure
skill-invocation-stages
```

精确地使用这些词：

- **Eligible（具备资格）**：策略允许该行为者请求这个技能。
- **Selected（被选中）**：用户点名了它，或路由器判定它相关。
- **Activated（已激活）**：它的指令进入了工作上下文。
- **Executing（执行中）**：agent 在这些指令下开始了模型或工具工作。
- **Completed（已完成）**：输出通过了独立的成功检查。

只记录 `skill_used=true` 的追踪会掩盖失败发生的边界。

> Use these words precisely:
> A trace that records only `skill_used=true` hides the boundary where a failure happened.

### Human and model invocation form a 2x2 matrix · 人类调用与模型调用构成 2x2 矩阵

| 人类可调用 | 模型可调用 | 模式 | 合适的例子 |
|:---:|:---:|---|---|
| 是 | 是 | 共享（Shared） | 代码讲解、测试规划、文档评审 |
| 是 | 否 | 仅人类（Human-only） | 发布准备、账单导出、破坏性清理计划 |
| 否 | 是 | 仅模型（Model-only） | 内部风格指南、领域参考、自动支持规程 |
| 否 | 否 | 禁用或仅应用（Disabled or application-only） | 灰度发布、弃用的包、程序化预加载 |

这个矩阵是策略模型，不是标准 YAML。

一个当前宿主用 `disable-model-invocation: true` 表达「仅人类」行，用 `user-invocable: false` 表达「仅模型」行，默认两者都允许。另一个宿主用 `agents/openai.yaml` 里的 `allow_implicit_invocation: false` 在保留显式调用的同时禁用隐式选择。这些是运行时适配器。未知宿主可能忽略它们。

一个容易混淆的细节很关键：`user-invocable: false` 不是「模型不能用这个」，它只是在定义它的宿主中移除用户的直接调用。`disable-model-invocation: true` 不是「技能被禁用」，它移除模型发起的选择，同时保留用户的显式访问。

> The matrix is a policy model, not standard YAML.
> The confusing detail matters: `user-invocable: false` does not mean "the model cannot use this." It removes direct user invocation in the host that defines it. `disable-model-invocation: true` does not mean "the skill is disabled." It removes model-initiated selection while keeping explicit user access.

### Explicit invocation is identity-first · 显式调用以身份为先

显式调用直接提供身份：

```text
/release-readiness v2.4.0
```

或者：

```text
release-readiness check v2.4.0 without publishing
```

当前 Codex 接口文档了用于选择的 `/skills`，以及在请求中用纯技能名做显式调用。Claude Code 文档了 `/skill-name` 和宿主特定的参数展开。确切的语法、菜单可见性、引号规则和变量展开都归属宿主。

显式请求仍然要通过策略。点名一个技能不应绕过缺失的权限、工作区约束、审批门禁或运行时隔离。

> Current Codex interfaces document `/skills` for selection and plain skill names in requests for explicit invocation. Claude Code documents `/skill-name` and host-specific argument expansion. The exact syntax, menu visibility, quoting rules, and variable expansion belong to the host.
> An explicit request still passes policy. Naming a skill should not bypass missing permissions, workspace constraints, approval gates, or runtime isolation.

### Implicit invocation is description-first · 隐式调用以描述为先

隐式路由时，模型最初看到的是目录元数据而不是完整正文。因此描述就是技能的路由接口。

弱：

```yaml
description: Helps with releases.
```

过宽：

```yaml
description: Use for release, version, package, build, deploy, publish, tag, changelog, GitHub, CI, or software tasks.
```

有界：

```yaml
description: Inspect an already prepared release candidate and produce a readiness report. Use when the user asks whether a version, tag, package, or image is ready to publish; do not use for ordinary build failures or feature development.
```

有界的版本包含：

1. **能力（Capability）**：检查一个已准备好的候选版本。
2. **输出（Output）**：就绪报告。
3. **正向边界**：询问某个发布工件是否就绪。
4. **负向边界**：普通构建和开发不在范围内。

当两个相邻技能共享词汇时，负向边界很有用。它们不能替代近似命中（near-miss）评测。

> For implicit routing, the model initially sees catalog metadata rather than the full body. The description is therefore the skill's routing interface.
> Negative boundaries are useful when two nearby skills share vocabulary. They are not a replacement for near-miss evals.

### Routing is classification with an abstain option · 路由是带弃权选项的分类

对技能 `s` 和请求 `x`，想象一个路由器分数：

```text
score(s, x) = capability_match + trigger_match + context_match - exclusion_match - ambiguity_penalty
```

具体的打分可以是一个 LLM 决策而不是算术。工程原则依然成立：选择应当超过一个阈值并且胜过竞争技能。证据不足时，弃权（abstain）。

```figure
skill-routing-abstention
```

对高影响技能，即便描述很强，隐式路由也可能不合适。当误报的代价超过自动选择带来的便利时，使用仅人类策略。

> The exact scoring may be an LLM decision rather than arithmetic. The engineering principle still holds: selection should beat a threshold and a competing skill. When evidence is weak, abstain.
> For high-impact skills, implicit routing may be inappropriate even with a strong description. Use human-only policy when the cost of a false positive exceeds the convenience of automatic selection.

### Eligibility must precede ranking · 资格判断必须先于排名

不要给每个已发现的技能打分、挑出最强匹配、然后才检查那一个的策略。一个被拦截的最高分匹配会错误地阻止一个有资格的低分候选被考虑。

隐式路由使用这个顺序：

1. 按请求行为者和活动宿主适配器过滤已发现的技能。
2. 只给有资格的候选打分。
3. 如果最强合格匹配超过阈值和歧义规则，选中它。
4. 当没有候选合格、或没有合格分数足够强时，弃权。

假设 `incident-triage` 得分 `0.80`，但它的宿主扩展禁用了模型调用；`incident-review` 得分 `0.55` 且允许模型调用。路由器应把 `incident-review` 当作最佳合格候选来评估，而不是选中 `incident-triage`、拒绝它、然后停手。

这个顺序还让策略变化不会改变相关性分数的含义。资格定义选择集，相关性给选择集排名。

> Do not score every discovered skill, choose the strongest match, and check that one skill's policy afterward. A blocked top match would incorrectly prevent an eligible lower-scored candidate from being considered.
> This ordering also keeps policy changes from altering the meaning of a relevance score. Eligibility defines the selection set. Relevance ranks that set.

### Routing evals need near misses · 路由评测需要近似命中

正向用例证明召回（recall）：

```json
{"prompt":"Is version 2.4.0 ready to publish?","expected":"release-readiness"}
```

清晰的负例证明基本精确率（precision）：

```json
{"prompt":"Explain rotary position embeddings.","expected":null}
```

近似命中暴露边界质量：

```json
{"prompt":"Why did today's package build fail?","expected":"build-diagnostics"}
```

这个近似命中与发布技能共享 `package` 和 `build`，但属于另一个工作流。一个只由明显正例和无关负例组成的路由评测集会高估质量。

> Near misses expose boundary quality:
> The near miss shares `package` and `build` with the release skill but belongs elsewhere. A routing set made only of obvious positives and unrelated negatives will overstate quality.

### Arguments have three representations · 参数有三种表示

一次调用的参数会跨越多个边界：

```figure
skill-argument-boundaries
```

在每个边界上保留意图，但不要把文本当代码。

- 宿主解析器决定命令语法和引号规则。
- 技能按宿主规则接收绑定的文本或变量。
- 指令校验必需值和默认值。
- 工具调用把值转换为类型化 schema 并重新校验。

不要把原始参数插值（interpolate）进 shell 命令。优先使用以参数向量调用的脚本或类型化的 MCP 工具。

> At each boundary, preserve intent without treating text as code.
> Do not interpolate raw arguments into shell commands. Prefer a script invoked with an argument vector or a typed MCP tool.

### Application invocation is explicit orchestration · 应用调用是显式编排

产品可以在其工作流已经知道任务类型时激活一个技能。例如，拉取请求评审服务可以在用户按下 Review 之后预加载 `pull-request-risk-review`。

这消除了路由不确定性，但制造了对运行时 API 的依赖。把这个适配器放在可移植正文之外：

```figure
skill-host-adapter
```

换一个合规客户端打开时，技能本身仍应可理解。

> This removes routing uncertainty but creates a dependency on the runtime API. Keep that adapter outside the portable body:
> The skill should remain intelligible when opened by a different compliant client.

### Skill-to-skill invocation is a tool-like edge · 技能对技能调用是一条类工具边

假设 `release-readiness` 在依赖文件变化时请求 `security-change-review`。

调用方应提供：

- 目标技能身份；
- 有界的任务与工件路径；
- 预期的响应契约；
- 调用原因；
- 不可用时的回退；
- 最大深度或循环规则。

```json
{
  "target_skill": "security-change-review",
  "task": "Review dependency changes in the candidate diff",
  "inputs": ["artifacts/release.diff"],
  "expected": "risk-report.json",
  "max_depth": 2
}
```

第二个技能不是被盲目粘贴进第一个的。由宿主决定如何激活它，以及它是共享上下文、在分支（fork）中运行，还是通过工具结果返回。

> The second skill is not pasted blindly into the first. The host decides how to activate it and whether it shares context, runs in a fork, or returns through a tool result.

### Context lifecycle is host-specific · 上下文生命周期是宿主特定的

激活之后，技能正文可能留在对话中、在压缩（compaction）期间被摘要，或在受托上下文中运行。工具许可可能只持续一轮，而指令存留更久。子 agent 可能拿到技能，却没有父级的完整历史。

不要编写依赖某个不可见生命周期假设的技能。把持久输出写进文件或类型化状态，保证重入安全，并说明中断后必须重新加载什么。

```markdown
On resume, read `artifacts/release-readiness.json` if it exists.
Revalidate the candidate commit before continuing.
Do not repeat an external write whose idempotency key is already recorded.
```

> After activation, the skill body may remain in the conversation, be summarized during compaction, or run in a delegated context. Tool allowances may last one turn while instructions persist longer. A subagent may receive the skill without the parent's entire history.
> Do not write a skill that depends on an invisible lifetime assumption. Put durable outputs in files or typed state, make re-entry safe, and state what must be reloaded after interruption.

## Build It · 动手造

`code/main.py` 把策略与路由实现为相互独立的适配器。

模型包括：

- `Actor`：人类、模型、自主 agent、应用、技能和 harness 调用方；
- `SkillMetadata`：路由身份；
- `InvocationPolicy`：人类/模型矩阵；
- `InvocationRequest` 与 `InvocationDecision`：可追踪的输入与结果；
- `CorePolicyAdapter`：没有宿主扩展的可移植行为；
- `ExtensionPolicyAdapter`：识别特定运行时字段；
- `build_invocation_matrix(policy)`：2x2 视图；
- `route_request(skills, request, adapter)`：在相关性排名、选择和拒绝之前先做资格过滤。

运行它：

```bash
cd phases/13-tools-and-protocols/25-skill-invocation-and-routing
python3 code/main.py
python3 -m unittest discover -s code/tests -v
```

演示会为一个矩阵，以及显式人类、隐式模型、自主 agent、应用、技能组合和 harness 通道打印决策。它的扩展适配器结果显示：一个被拦截的最高词汇匹配会在合格备选被排名之前被移除。它还包含精确名字白名单。不需要任何模型 API。这个确定性路由器的存在是为了让策略边界可检视，而不是声称词汇匹配能复现生产模型路由。

> `code/main.py` implements policy and routing as separate adapters.
> The deterministic router exists to make policy boundaries inspectable, not to claim that lexical matching reproduces production model routing.

### Why core and extension adapters are separate · 为什么核心与扩展适配器分开

如果一个解析器给每个观察到的 frontmatter 字段都赋含义，它就把运行时约定悄悄提升成了伪标准。分开的适配器迫使调用方说出当前生效的是哪个宿主语义。

`CorePolicyAdapter` 只使用应用提供的策略。`ExtensionPolicyAdapter` 识别一组显式的宿主字段，并记录是哪个字段改变了决策。

> If one parser assigns meaning to every observed frontmatter field, it silently promotes runtime conventions into a fake standard. Separate adapters force the caller to name which host semantics are active.
> The `CorePolicyAdapter` uses only application-supplied policy. The `ExtensionPolicyAdapter` recognizes an explicit set of host fields and records which field changed the decision.

## Use It · 实战用法

在发布技能之前，先写一份调用契约：

```yaml
actors:
  human: allow
  model: deny
  application: allow
  skill: deny
explicit_name: release-readiness
arguments:
  candidate: required
  publish: fixed_false
ambiguity: ask_user
missing_dependency: stop
context:
  durable_state: artifacts/release-readiness.json
  max_composition_depth: 2
```

这份契约是给适配器和测试用的设计文档。除非某个标准明确采纳它，它不是可移植的 `SKILL.md` frontmatter。

> This contract is design documentation for adapters and tests. It is not portable `SKILL.md` frontmatter unless a standard explicitly adopts it.

## Ship It · 交付

本课产出 `skill-invocation-router` 捆绑包。它包含一份调用模型参考、一份示例宿主策略，以及一个非执行的 CLI：评估一次人类、模型、自主 agent、应用、技能组合或 harness 请求，并返回带通道、适配器、分数和理由的 JSON 决策。

这个单请求 CLI 是策略探针，不是完整的触发评测。请用第 27 课带标注的正例与近似命中设计来计算混淆计数、精确率、召回率和重复运行稳定性。

> This lesson produces the `skill-invocation-router` bundle. It includes an invocation-model reference, an example host policy, and a non-executing CLI that evaluates one human, model, autonomous-agent, application, skill-composition, or harness request and returns a JSON decision with channel, adapter, score, and reason.
> The one-request CLI is a policy probe, not a full trigger evaluation. Use the labeled positive and near-miss design in Lesson 27 to compute confusion counts, precision, recall, and repeated-run stability.

## Exercises · 练习

1. 创建人类/模型矩阵的全部四行，并为每一行写一个合法用例。
2. 给 `CorePolicyAdapter` 添加仅应用激活。证明人类和模型调用方仍被拒绝。
3. 为一个部署技能写十个近似命中。每个提示都必须与技能共享词汇，同时属于另一个工作流。
4. 在最高的两条路由分数之间加一个歧义裕度。裕度太小时返回 `ask`。
5. 给技能对技能请求加最大组合深度，并检测一个双技能循环。
6. 把同一组带标注的用例跑过核心与扩展适配器。解释每一个发生变化的决策。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|---|---|---|
| Explicit invocation（显式调用） | "Slash command"（斜杠命令） | 行为者直接提供技能身份，仍受策略约束 |
| Implicit invocation（隐式调用） | "The model chooses"（模型来选） | 路由器基于任务上下文从合格的目录元数据中选择 |
| User-invocable（用户可调用） | "Humans can use it"（人类能用它） | 宿主特定的菜单或直接调用属性，不是核心字段 |
| Model-invocable（模型可调用） | "The agent can use it"（agent 能用它） | 在宿主策略下进行隐式模型选择的资格 |
| Invocation adapter（调用适配器） | "Frontmatter parser"（frontmatter 解析器） | 把宿主的字段和 API 映射到已声明策略模型的代码 |
| Near miss（近似命中） | "Hard negative"（困难负例） | 形似技能预期输入、但并不触发它的请求 |
| Abstention（弃权） | "No skill selected"（不选技能） | 证据缺失或含糊时的一种有意的路由结果 |

## Further Reading · 延伸阅读

- [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) —— 正向触发器、具体性与评测。
- [Evaluating skills](https://agentskills.io/skill-creation/evaluating-skills) —— 触发与输出评测设计。
- [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills) —— 当前 Codex 的显式与隐式调用控制。
- [Claude Code skills](https://code.claude.com/docs/en/skills) —— 一个宿主的 `user-invocable`、`disable-model-invocation`、参数与受托上下文。
