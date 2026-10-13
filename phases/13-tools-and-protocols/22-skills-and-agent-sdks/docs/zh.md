# Agent Skills: Portable Contract and Runtime Boundary · Agent 技能（skills）：可移植契约与运行时边界

> 技能不是一个「文件名取得更好的长提示词」。它是一个可发现的包，内含指令、资源和可执行的辅助脚本，通过一个运行时契约（runtime contract）进入 agent 的上下文。
>
> A skill is not a long prompt with a better filename. It is a discoverable package of instructions, resources, and executable helpers that enters an agent's context through a runtime contract.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 13 · 01 (The Tool Interface), Phase 13 · 05 (Tool Schema Design)
**Time:** ~90 minutes

## Learning Objectives · 学习目标

- 定义 agent 技能，并把它与提示词、仓库指令、工具、钩子（hook）、子 agent（subagent）和插件区分开
- 读懂可移植的 `SKILL.md` 契约，并把它与运行时特有的扩展分开
- 把发现、选择、激活、资源加载、工具使用与验证解释为彼此不同的生命周期阶段
- 在运行时把一个技能包放进 agent 目录（catalog）之前校验它
- 针对具体任务，在技能、MCP 工具、钩子、子 agent 和普通代码之间做选择

> Define an agent skill without confusing it with a prompt, repository instructions, a tool, a hook, a subagent, or a plugin.
> Read the portable `SKILL.md` contract and separate it from runtime-specific extensions.
> Explain discovery, selection, activation, resource loading, tool use, and verification as distinct lifecycle stages.
> Validate a skill package before a runtime places it in an agent's catalog.
> Choose between a skill, MCP tool, hook, subagent, or ordinary code for a concrete task.

## Ten-Minute First Success · 十分钟首次成功

在长篇解释之前先做这个。你将创建一个小技能，把完整的 reviewer 包安装进一个真实的 agent 宿主，调用它，验证结果，然后移除它。用一个可观察的结果证明这套生命周期。

### Preflight for the real-host lab · 真实宿主实验的准备检查

真实宿主检查点需要 Node.js、`npx`、Python 3、一个选定的支持技能的宿主，以及你在安装器中选定作用域（项目或用户级）的写权限。先验证本地命令：

```bash
node --version
npx --version
python3 --version
```

在安装之前决定要用哪个宿主和哪个作用域。如果任何条件不可用，就在网站上阅读本课，或者继续做下面的手动包练习。那个后备路径能教会你契约，但无法证明宿主发现、调用、捆绑脚本执行或卸载行为。把这些观察标记为「待验证」。

> The real-host checkpoint requires Node.js, `npx`, Python 3, one selected skill-capable host, and write access to the project or user scope you choose in the installer. Verify the local commands first.
> That fallback teaches the contract, but it does not prove host discovery, invocation, bundled-script execution, or uninstall behavior. Keep those observations marked pending.

### 1. Start in an empty working directory · 第 1 步：在一个空工作目录里开始

在你存放学习工作的任意父目录下运行这些命令：

```bash
mkdir -p agent-skills-first-run
cd agent-skills-first-run
TARGET_ROOT="$(pwd -P)"
printf 'TARGET_ROOT=%s\n' "$TARGET_ROOT"
ls -A
```

最后一条命令应该什么都不打印。如果它打印了文件，换一个空目录，让这次评审有一个清晰的边界。

为你的第一个技能创建一个目录：

```bash
mkdir -p my-first-skill
```

创建 `my-first-skill/SKILL.md`，内容如下：

```markdown
---
name: my-first-skill
description: Turn rough meeting notes into a compact decision record when the user asks to capture a technical decision.
---

# Decision record

Extract the decision, context, alternatives, owner, and next review date.
If the notes do not contain a decision, ask one clarifying question instead
of inventing one.
```

确认你把文件创建在了预期的目录里：

```bash
test -f my-first-skill/SKILL.md
```

没有输出且退出码为 0，表示文件存在。

> Run these commands from any parent directory where you keep learning work.
> The final command should print nothing. If it prints files, choose a different empty directory so the review has a clear boundary.
> No output and exit code 0 means the file exists.

### 2. Install the complete reviewer bundle · 第 2 步：安装完整的 reviewer 包

停留在 `agent-skills-first-run` 里并运行：

```bash
npx skills add rohitg00/ai-engineering-from-scratch --skill skill-contract-reviewer --full-depth
```

选择你正在使用的 agent 宿主和作用域。安装器应该列出 `skill-contract-reviewer` 和它写入的目标位置。`--full-depth` 是必需的，因为本课的技能是一个带引用、脚本和资产的嵌套包。

把 `SKILL_ROOT` 设为安装器报告的绝对目录。它必须是包含已安装 `SKILL.md` 的那个目录，而不是本课的源码目录，也不是当前工作区：

```bash
# Replace the placeholder with the destination printed by the installer.
SKILL_ROOT="$(cd "/absolute/path/to/skill-contract-reviewer" && pwd -P)"
test -f "$SKILL_ROOT/SKILL.md"
printf 'SKILL_ROOT=%s\n' "$SKILL_ROOT"
```

如果 agent 会话早已打开，请新开一个会话，或使用那个宿主的技能重扫描命令。不要假设每个宿主都会热重载自己的目录。

> Choose the agent host and scope you are using. The installer should list `skill-contract-reviewer` and the destination it wrote. `--full-depth` is required because this lesson's skill is a nested bundle with references, a script, and an asset.
> Set `SKILL_ROOT` to the absolute directory reported by the installer. It must be the directory containing the installed `SKILL.md`, not the lesson source directory and not the current workspace.
> If the agent session was already open, start a new session or use that host's skill rescan command. Do not assume every host hot-reloads its catalog.

### 3. Invoke it explicitly · 第 3 步：显式调用

在安装好的 agent 里，以 `agent-skills-first-run` 为工作目录，使用那个宿主支持的语法：

| 宿主 | 显式调用方式 |
|---|---|
| Codex | `skill-contract-reviewer`，或从 `/skills` 里选择它，然后给出评审请求 |
| Claude Code | `/skill-contract-reviewer` 后跟评审请求 |
| 可移植后备 | `Use skill-contract-reviewer to review the target package.` |

在请求里使用为 `SKILL_ROOT` 和 `TARGET_ROOT` 打印出来的绝对值。要求宿主在执行前展开它们，并展示解析后的完整命令，而不是一条依赖进程工作目录的命令：

```text
Use skill-contract-reviewer to review <TARGET_ROOT>/my-first-skill. The installed bundle root is <SKILL_ROOT>. Run python3 <SKILL_ROOT>/scripts/check_skill.py <TARGET_ROOT>/my-first-skill. Before running it, show the fully resolved argv. Return the validation report, selected primitives, and one sentence for each selection. Include the resolved script path, resolved target path, cwd, argv, and exit code as execution evidence.
```

解析后的命令应该是这个形状，不残留任何占位符：

```bash
python3 "/absolute/install/path/skill-contract-reviewer/scripts/check_skill.py" \
  "/absolute/workspace/path/agent-skills-first-run/my-first-skill"
```

一个成功的结果同时具备三个性质：

1. 宿主按名称找到了 `skill-contract-reviewer`。
2. reviewer 读取了包契约并运行了它捆绑的校验器。
3. 响应包含一份对该样例没有结构性错误的验证报告，外加一个有理由支撑的原语（primitive）选择。

执行证据还必须写明脚本路径、目标路径、cwd、精确的参数向量（argv）和退出码。一份没有这些字段的流畅报告，不能证明已安装的配套脚本真的运行过。

如果宿主报告技能不可用，检查安装目标，重扫描或重启一次，然后重试显式请求。不要靠改写技能描述来掩盖一次安装失败。

> Use the absolute values printed for `SKILL_ROOT` and `TARGET_ROOT` in the request. Require the host to expand them before execution and show the exact resolved command, not a command that depends on the process working directory.
> A successful result has all three properties:
> The host finds `skill-contract-reviewer` by name. ... The response contains a validation report with no structural error for the sample, plus a justified primitive selection.
> The execution evidence must also name the script path, target path, cwd, exact argument vector, and exit code. A fluent report without those fields does not prove that the installed companion script ran.
> If the host reports that the skill is unavailable, verify the install destination, rescan or restart once, and retry the explicit request. Do not rewrite the skill description to hide an installation failure.

### 4. Probe implicit selection · 第 4 步：探测隐式选择

开启一个全新的 agent 回合，输入同样的任务但不点名技能：

```text
Review <TARGET_ROOT>/my-first-skill as a reusable agent package and tell me whether its package contract is valid.
```

如果宿主暴露被选中的技能，记录它是否选择了 `skill-contract-reviewer`。如果宿主不暴露路由信息，就把隐式选择标记为「未验证」。显式调用是可移植的后备手段。

> Start a fresh agent turn and enter the same task without naming the skill.
> If the host exposes selected skills, record whether it chose `skill-contract-reviewer`. If the host does not expose routing, mark implicit selection as unverified. The explicit invocation is the portable fallback.

### 5. Clean up · 第 5 步：清理

只移除已安装的 reviewer 包：

```bash
npx skills remove skill-contract-reviewer
```

选择与安装时相同的宿主和作用域。重扫描或新开会话后，对 `skill-contract-reviewer` 的显式请求应该报告它不可用。保留 `my-first-skill` 给后面的课程，或者在你完成这条学习路线后删除实验目录。

> Select the same host and scope used during installation. After a rescan or new session, an explicit request for `skill-contract-reviewer` should report that it is unavailable. Keep `my-first-skill` for the later lessons, or remove the lab directory after you finish the track.

## The Problem · 问题在哪

假设你的团队有一个可靠的发布流程：找出已合并的变更、检查迁移说明、更新 changelog、运行一个打包命令，并产出一份评审清单。

把这套流程塞进一个提示词，会让它易于粘贴却难以运营。这个提示词没有稳定的身份、没有发现规则、没有资源边界、没有可测试的包形状，也回答不了基本问题：谁可以调用它？模型什么时候应该选中它？它能运行哪些脚本？哪些文件是可信的？上下文被压缩后还剩下什么？

相反的错误是把每一段可复用的指令都当成技能。仓库约定、确定性自动化、外部工具、事件钩子和被委托的 agent 解决的是不同的问题。把所有这些都打包进 `SKILL.md`，会产出一个「看起来可移植、实际上依赖某一个宿主的未文档化行为」的目录。

第一个工程任务是分类。先决定这个制品（artifact）是什么，再决定怎么打包它。

> Putting that workflow in one prompt makes it easy to paste and hard to operate. The prompt has no stable identity, no discovery rule, no resource boundary, no testable package shape, and no answer to basic questions: Who may invoke it? When should the model select it? Which scripts can it run? Which files are trusted? What survives when context is compacted?
> The opposite mistake is to treat every reusable instruction as a skill. Repository conventions, deterministic automation, external tools, event hooks, and delegated agents solve different problems. Packing all of them into `SKILL.md` produces a directory that looks portable while depending on one host's undocumented behavior.
> The first engineering task is classification. Decide what the artifact is before you decide how to package it.

## The Concept · 概念

### Skills encode procedural knowledge · 技能编码的是过程性知识

agent 技能是一个目录，其入口点是 `SKILL.md`。入口文件包含 YAML frontmatter 加 Markdown 指令。目录里还可以包含引用（references）、脚本（scripts）和资产（assets）。

```figure
skill-package-anatomy
```

可部署单元是目录，而不只是那个 Markdown 文件。一份缺了引用的、被单独复制的 `SKILL.md`，即使 frontmatter 能解析，也是一个坏掉的包。

> An agent skill is a directory whose entry point is `SKILL.md`. The entry file contains YAML frontmatter followed by Markdown instructions. The directory can also contain references, scripts, and assets.
> The directory, not the Markdown file alone, is the deployable unit. A copied `SKILL.md` with missing references is a broken package even if its frontmatter parses.

### The neighboring abstractions · 相邻的抽象

| 制品 | 主要职责 | 何时被加载或运行 | 它不应冒充什么 |
|---|---|---|---|
| 提示词（Prompt） | 塑造一次模型交互 | 被应用或用户包含 | 一个带资源的版本化包 |
| 仓库指令（Repository instructions） | 解释一个代码库的长期规则 | 编码运行时进入该作用域时 | 一个可复用的任务工作流 |
| Agent 技能（Agent skill） | 提供可复用的过程性知识 | 显式或隐式激活时 | 一个硬授权边界 |
| MCP 工具（MCP tool） | 暴露一个有类型的远程能力 | 模型或应用调用它时 | 一份详细的操作规程 |
| 钩子（Hook） | 在事件上运行确定性逻辑 | 声明的事件发生时 | 概率性的模型路由 |
| 子 agent（Subagent） | 用独立上下文和状态委托工作 | 编排器创建或调用它时 | 一个静态指令包 |
| 插件（Plugin） | 分发一个更大的运行时扩展 | 宿主安装或启用它时 | 可移植技能契约本身 |
| 学习型技能库（Learned skill library） | 存储通过经验发现的行为 | 策略取回一个先前的程序或轨迹时 | 一个基于标准的 `SKILL.md` 包 |

一个发布技能可以告诉 agent 如何检查一次发布。一个 MCP 服务器可以暴露发布注册表。一个钩子可以禁止直接推送。一个子 agent 可以独立审计候选版本。这些部件能组合，是因为它们承担不同的职责。

> A release skill can tell the agent how to inspect a release. An MCP server can expose the release registry. A hook can forbid direct pushes. A subagent can independently audit the candidate. These pieces compose because they keep different responsibilities.

### The word "skill" names two different ideas · 「skill」一词指两个不同的概念

研究系统有时把一个学到的程序、一次成功的轨迹或环境特定的策略片段称为技能（skill）。agent 可以在探索中创建这些制品，按任务相似性取回它们，执行它们，并根据反馈修订这个库。Phase 14 · 10 构建的就是那种终身学习库。

本小节路线里的 Agent Skill 是另一回事。它是一个作者化（authored）的包，带声明好的文件系统契约、目录元数据、渐进披露（progressive disclosure）、运行时中介的调用和宿主控制的工具。它可以由 agent 生成或改进，但这个格式并不要求「学习」。

| 维度 | Agent Skill 包 | 学习型技能库 |
|---|---|---|
| 主要单元 | `SKILL.md` 目录 | 程序、策略、轨迹或记忆记录 |
| 创建方式 | 作者编写、生成或策展 | 通常从环境经验中发现 |
| 选择方式 | 目录描述加运行时策略 | 按任务状态做检索或策略决策 |
| 执行方式 | 模型遵循指令并调用宿主工具 | 环境运行一个存储的行为或代码制品 |
| 可移植性 | 包契约可以跨兼容宿主 | 往往绑定一个环境与动作空间 |
| 评估方式 | 路由、制品、安全与宿主兼容性 | 奖励、成功率、迁移与库增长 |

两种想法都在打包可复用的能力。它们不应该因为共享一个名字，就共享实现上的主张。

> Research systems sometimes call a learned program, successful trajectory, or environment-specific policy fragment a skill. An agent can create these artifacts during exploration, retrieve them by task similarity, execute them, and revise the library from feedback. Phase 14 · 10 builds that kind of lifelong-learning library.
> An Agent Skill in this mini-track is different. It is an authored package with a declared filesystem contract, catalog metadata, progressive disclosure, runtime-mediated invocation, and host-controlled tools. It can be generated or improved by an agent, but learning is not required for the format.
> Both ideas package reusable competence. They should not share implementation claims merely because they share a name.

### The portable core · 可移植核心

Agent Skills 规范要求两个 frontmatter 字段：

```yaml
---
name: release-readiness
description: Inspect a release candidate when the user asks whether a version is ready to publish.
---
```

`name` 是稳定标识符。它必须满足规范的命名规则，并与父目录名一致。`description` 既是文档也是路由元数据。它应该说明这个技能做什么、什么时候适用。

可移植的可选字段：

| 字段 | 用途 | 可移植性说明 |
|---|---|---|
| `license` | 声明包的条款 | 核心规范 |
| `compatibility` | 声明环境要求 | 核心规范 |
| `metadata` | 携带字符串值的扩展数据 | 核心规范 |
| `allowed-tools` | 建议预批准的工具 | 实验性；宿主支持程度不一 |

Markdown 正文承载操作性指令。它应该定义工作流、决策点、失败行为，以及指向支撑资源的直接路径。

```markdown
# Release readiness

Use this workflow for a release candidate, not for ordinary development builds.

1. Read `references/release-policy.md`.
2. Run `python3 scripts/inspect_release.py --format json`.
3. Stop if the report contains a blocking failure.
4. Produce the checklist from `assets/release-checklist.md`.
5. Ask for approval before any publish or tag action.
```

> The Agent Skills specification requires two frontmatter fields.
> `name` is the stable identifier. It must satisfy the specification's naming rules and match the parent directory. `description` is both documentation and routing metadata. It should say what the skill does and when it applies.
> The Markdown body holds the operational instructions. It should define the workflow, decision points, failure behavior, and direct paths to supporting resources.

### Runtime extensions are a second layer · 运行时扩展是第二层

一些宿主接受额外的 frontmatter 或配套配置。这些字段可能有用，但它们不会自动可移植。

| 行为 | 宿主扩展示例 | 属于可移植核心？ |
|---|---|:---:|
| 对模型路由隐藏技能，但保留用户的直接调用 | `disable-model-invocation` | 否 |
| 对用户的命令菜单隐藏技能，但允许模型路由 | `user-invocable` | 否 |
| 在命令菜单里显示参数帮助 | `argument-hint` | 否 |
| 在被委托的上下文里运行技能 | `context`, `agent` | 否 |
| 固定模型或推理设置 | `model`, `effort` | 否 |
| 注册生命周期自动化 | `hooks` | 否 |
| 在 Codex 中禁用隐式调用 | `agents/openai.yaml` 策略 | 否 |

把每个扩展当作一个适配器（adapter）。让核心工作流在没有它的情况下仍然成立，写明后备行为，并测试消费它的那个宿主。运行时可能忽略未知字段、拒绝它，或者在未实现对应行为的情况下原样保留它。

> Some hosts accept extra frontmatter or companion configuration. Those fields can be useful, but they are not automatically portable.
> Treat each extension as an adapter. Keep the core workflow valid without it, document the fallback, and test the host that consumes it. A runtime may ignore an unknown field, reject it, or preserve it without implementing the behavior.

### Frontmatter is executable metadata · Frontmatter 是可执行的元数据

元数据会在技能正文被读取之前改变系统行为。

- 一个格式错误的 `name` 可以让发现失败。
- 一段含糊的 `description` 可以路由错误的请求。
- 一个仅限人类的标志可以把技能从模型的目录里移除。
- 一个工具许可可以改变宿主是否请求权限。
- 一个上下文设置可以把执行移进一个单独的 agent 会话。

像评审配置代码一样评审 frontmatter。校验它、为它做版本管理，并把它的行为纳入评估（eval）。

> Metadata changes system behavior before the skill body is read.
> Review frontmatter like configuration code. Validate it, version it, and include its behavior in evals.

### The skill lifecycle · 技能生命周期

```figure
skill-runtime-lifecycle
```

每支箭头都是一个边界，各有自己的失败模式。

1. **发现（Discovery）** 在配置的位置里找出候选包。
2. **校验（Validation）** 在目录发布前拒绝畸形或不安全的包。
3. **编目（Cataloging）** 暴露紧凑的 `name` 和 `description`，而不是完整包。
4. **选择（Selection）** 决定该技能是否相关。
5. **激活（Activation）** 把正文加载进模型可见的上下文。
6. **披露（Disclosure）** 只在某条分支需要时才读取引用或资产。
7. **执行（Execution）** 在宿主的权限与隔离规则下使用宿主工具。
8. **验证（Verification）** 独立于模型的主张检查产出的制品。

把这些阶段压扁会造成错误的心智模型。被发现不等于被激活。被激活的技能也无权做它描述的一切。一次被允许的工具调用也不是结果正确性的证明。

> Each arrow is a boundary with its own failure modes.
> **Discovery** finds possible packages in configured locations. ... **Verification** checks the produced artifact independently of the model's claim.
> Collapsing these stages causes bad mental models. A discovered skill is not active. An active skill is not authorized to do everything it describes. A permitted tool call is not proof that the result is correct.

### Skills and tools are orthogonal · 技能与工具是正交的

MCP 回答的是：「这个应用可以调用哪些能力，它们的模式（schema）是什么？」技能回答的是：「agent 应该如何处理这一类任务？」

```figure
skill-tool-orthogonality
```

技能可以点名一个工具，但能力注册表归宿主所有。如果工具缺席，技能应当陈述后备方案或清晰地失败。它绝不能暗示「点名一个能力就等于创造了它」。

> MCP answers, "Which capabilities can this application call, and what are their schemas?" A skill answers, "How should an agent approach this class of task?"
> The skill may name a tool, but the host owns the actual capability registry. If the tool is absent, the skill should state a fallback or fail clearly. It should never imply that naming a capability creates it.

### Skills and repository instructions are different scopes · 技能与仓库指令是不同的作用域

仓库指令描述你已经身处其中的环境：命令、约定、生成的文件和边界。技能为一个可能横跨许多仓库的任务提供可复用的流程。

当两者都适用时，活跃的用户请求和仓库规则约束技能。一个通用的重构技能绝不能覆盖「禁止编辑生成文件」这条仓库规则。

> Repository instructions describe the environment you are already in: commands, conventions, generated files, and boundaries. A skill provides reusable procedure for a task that may occur across many repositories.
> When both apply, the active user request and repository rules constrain the skill. A generic refactoring skill must not override a repository rule that forbids editing generated files.

### Skills do not import one another · 技能之间不能互相导入

一个技能可以指示 agent 去调用另一个技能，但这不是语言层面的导入。第二个技能仍然要走完运行时的发现、资格判定、激活、权限和上下文处理。

把跨技能依赖写成可观察的工作流边（edge）：

```markdown
After producing the candidate changelog, invoke the `release-risk-review` skill.
Pass the candidate path and require a blocking or non-blocking verdict.
If that skill is unavailable, stop and report the missing dependency.
```

这让依赖可测试，也让宿主有机会执行策略。

> One skill can direct the agent to invoke another, but this is not a language-level import. The second skill still goes through runtime discovery, eligibility, activation, permissions, and context handling.
> Write cross-skill dependencies as observable workflow edges.
> This makes the dependency testable and gives the host a chance to enforce policy.

## Build It · 动手造

`code/main.py` 实现了一个面向标准的小型校验器和一个制品选择器。它保持只用标准库，让每条规则都可见。

校验器暴露：

- `parse_frontmatter(text)`：把元数据与正文分离。
- `validate_skill_text(text, directory_name, allowed_runtime_extensions=())`：检查必需字段、命名、未知扩展、正文存在性和可移植性限制。
- `ValidationIssue` 和 `SkillReport`：返回结构化证据，而不是一个不透明的布尔值。
- `FrontmatterSyntaxError`：用于无法安全解释的输入。

选择器暴露 `TaskShape` 和 `select_primitives(task)`。它把一个任务的需求映射到普通代码、仓库指令、技能、钩子、子 agent 或 MCP 工具。

运行实验：

```bash
cd "$(git rev-parse --show-toplevel)"
cd phases/13-tools-and-protocols/22-skills-and-agent-sdks
python3 code/main.py
python3 -m unittest discover -s code/tests -v
```

这个命令块要求一个本地克隆，并且必须从该克隆内的任意位置启动，这样 `git rev-parse --show-toplevel` 才能解析出仓库根目录。

演示会为「一个有效的可移植技能、一个带宿主扩展的技能、一个无效的包」以及若干任务形状决策打印 JSON。查看那些 issue 代码。一个包校验器应当解释如何修复制品，而不是替作者瞎猜。

> `code/main.py` implements a small standards-oriented validator and an artifact chooser. It stays stdlib-only so every rule is visible.
> The demo prints JSON for one valid portable skill, one host-extended skill, one invalid package, and several task-shape decisions. Inspect the issue codes. A package validator should explain how to fix an artifact without guessing on the author's behalf.

### Validation order matters · 校验顺序很重要

先校验廉价的结构性事实，再校验更深层的内容规则：

```figure
skill-validation-order
```

这个顺序防止次要错误掩盖第一个被破坏的不变量。

> Validate cheap structural facts before deeper content rules.
> This order prevents secondary errors from obscuring the first broken invariant.

## Use It · 实战用法

在写技能之前，先填这张决策卡：

| 问题 | 如果是 | 可能的原语 |
|---|---|---|
| 这需要在多个步骤间复用模型判断吗？ | 流程稳定但决策多变 | 技能 |
| 这必须每次事件触发时都发生吗？ | 错过一次执行不可接受 | 钩子或应用代码 |
| 模型需要一个带类型输入的外部能力吗？ | 操作发生在模型上下文之外 | 工具或 MCP 服务器 |
| 这项工作需要隔离的上下文、状态或所有权吗？ | 一个独立 worker 返回有界结果 | 子 agent |
| 这条指引只针对某一个仓库吗？ | 它描述本地命令与约束 | 仓库指令 |
| 一次交互就够了吗？ | 不需要任何包生命周期 | 提示词 |

许多生产工作流会用到不止一行。这张卡防止一个制品假装自己具备所有性质。

> Before writing a skill, fill out this decision card.
> Many production workflows use more than one row. The card prevents one artifact from pretending to provide every property.

## Ship It · 交付

本课在 `outputs/` 下产出 `skill-contract-reviewer` 包。它包含：

- 一份可移植的 `SKILL.md`，用于评审一个拟议的技能包；
- 针对可移植契约与原语选择的参考清单；
- 一个确定性的校验脚本；
- 覆盖提示词、技能、工具、钩子、普通代码和子 agent 的任务形状夹具（fixtures）。

安装完整包，而不只是它的入口文件：

```bash
cd "$(git rev-parse --show-toplevel)"
python3 scripts/install_skills.py /tmp/aiefs-skills --phase 13 --type skill
```

课程安装器会报告它复制的每个 Phase 13 技能，并写出 `/tmp/aiefs-skills/manifest.json`。这个干净的目的地检查包形状；上面的首次成功循环则在真实宿主中检查发现与调用。

后面的课程会深化生命周期的每个阶段。第 24 课构建发现与渐进披露。第 25 课构建调用策略与路由。第 26 课把权限与沙箱分开。第 27 课把整个包变成一个经过评估的发布制品。

> This lesson produces the `skill-contract-reviewer` bundle under `outputs/`. It contains:
> a portable `SKILL.md` that reviews a proposed skill package; ... task-shape fixtures covering prompts, skills, tools, hooks, ordinary code, and subagents.
> The course installer reports each copied Phase 13 skill and writes `/tmp/aiefs-skills/manifest.json`. This clean destination checks package shape; the first-success loop above checks discovery and invocation in a real host.
> The following lessons deepen each lifecycle stage. Lesson 24 builds discovery and progressive disclosure. Lesson 25 builds invocation policy and routing. Lesson 26 separates permissions from sandboxing. Lesson 27 turns the whole package into an evaluated release artifact.

## Exercises · 练习

1. 用 `TaskShape` 给你自己团队的五个工作流分类。为每一个你选择多于一个原语的场景辩护。
2. 添加边界测试，证明 500 字符的 `compatibility` 值通过，501 字符的值作为规范错误失败。
3. 向允许列表添加一个运行时扩展。写一个测试，证明同一个文件仍然能与纯可移植技能区分开。
4. 把一个 400 行的提示词拆成 `SKILL.md`、一个引用、一个脚本契约和一个输出模板。让每个文件只负责一类信息。
5. 为一个引用了不可用 MCP 工具的技能设计失败响应。不要静默地换成一个权限更大的工具。
6. 评审一个现有技能，把每一句话标注为路由、流程、策略、引用指针或输出契约。把不属于这里的任何内容移走。

> 1. Classify five workflows from your own team using `TaskShape`. Defend every case where you choose more than one primitive.
> 2. Add boundary tests proving that a 500-character `compatibility` value passes and a 501-character value fails as a specification error.
> 3. Add one runtime extension to the allowlist. Write a test proving the same file is still distinguishable from a portable-only skill.
> 4. Split a 400-line prompt into `SKILL.md`, one reference, one script contract, and one output template. Keep every file responsible for one kind of information.
> 5. Design a failure response for a skill that references an unavailable MCP tool. Do not silently substitute a tool with broader permissions.
> 6. Review an existing skill and label every sentence as routing, procedure, policy, reference pointer, or output contract. Move anything that does not belong.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|---|---|---|
| Agent 技能（Agent skill） | 「一个保存下来的提示词」 | 一个可发现的目录，内含过程性指令与可选资源 |
| 可移植核心（Portable core） | 「每个运行时都共享的字段」 | 由 Agent Skills 规范定义的契约 |
| 运行时扩展（Runtime extension） | 「额外的 frontmatter」 | 宿主特有的配置，其行为需要兼容的适配器 |
| 激活（Activation） | 「技能运行了」 | 技能正文进入了模型可见的上下文；执行可能更晚发生 |
| 技能依赖（Skill dependency） | 「导入另一个技能」 | 一条运行时中介的调用边，带可用性与策略检查 |
| 工具契约（Tool contract） | 「一个函数模式」 | 一个能力的输入、输出、权限、副作用、错误与证据 |

> | Term | What people say | What it actually means |
> | Agent skill | "A saved prompt" | A discoverable directory of procedural instructions and optional resources |
> | Portable core | "Fields every runtime shares" | The contract defined by the Agent Skills specification |
> | Runtime extension | "Extra frontmatter" | Host-specific configuration whose behavior requires a compatible adapter |
> | Activation | "The skill ran" | The skill body entered model-visible context; execution may come later |
> | Skill dependency | "Import another skill" | A runtime-mediated invocation edge with availability and policy checks |
> | Tool contract | "A function schema" | Inputs, outputs, permissions, side effects, errors, and evidence for a capability |

## Further Reading · 延伸阅读

- [Agent Skills specification](https://agentskills.io/specification) —— 可移植的目录与 frontmatter 契约。
- [Agent Skills best practices](https://agentskills.io/skill-creation/best-practices) —— 作用域、指令与资源组织。
- [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills) —— 当前的 Codex 发现与调用行为。
- [Claude Code skills](https://code.claude.com/docs/en/skills) —— 某个运行时的调用、参数、工具与委托上下文扩展。
