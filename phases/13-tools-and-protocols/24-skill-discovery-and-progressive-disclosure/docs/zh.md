# Skill Discovery and Progressive Disclosure · 技能发现与渐进式披露

> A skill becomes useful before its body is loaded. Its name and description earn a place in the catalog; its deeper files earn context only when the task reaches them.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 13 · 22 (Agent Skills: Portable Contract and Runtime Boundary)
**Time:** ~105 minutes

## Learning Objectives · 学习目标

- 构建一条文件系统发现流水线，把范围（scope）、校验、冲突策略和目录发布分离开。
- 解释三个披露层级：目录元数据、激活后的指令，以及任务特定的资源。
- 设计引用（reference），让 agent 能直接抵达所需细节，而不必加载整个包。
- 让目录预算与激活技能的上下文预算各自独立核算。
- 当技能读取自身资源时，拒绝路径穿越（path traversal）和符号链接逃逸（symlink escape）。

> Build a filesystem discovery pipeline that separates scope, validation, collision policy, and catalog publication.
> Explain the three disclosure levels: catalog metadata, active instructions, and task-specific resources.
> Design references so an agent can reach required detail directly without loading the entire package.
> Budget catalog space independently from active-skill context.
> Reject path traversal and symlink escape when a skill reads its own resources.

## The Problem · 问题在哪

你的 agent 装了 200 个技能。如果在会话开始时加载每个 `SKILL.md`、引用文件、脚本和模板，当前任务就会被无关规程淹没；如果什么都不加载，用户就得自己记住确切的文件系统路径。

常见的折中是目录（catalog）：向模型展示每个合格技能的紧凑身份与路由描述，选中之后才加载完整正文。这带来两个新的工程问题。

其一，发现不只是递归搜索文件。技能可能存在于项目、用户、管理员、插件或内置 scope。两个包可能重名。一个符号链接可能指向可信根之外。一个畸形的包可能吞掉目录空间，或者根本无法调用。

其二，渐进式披露（progressive disclosure）可能变成渐进式困惑。如果 `SKILL.md` 说「去读相关的指南」，而包里有十二份指南，模型只能靠猜。如果每份指南又指向另外三个文件，加载就变成一场无界的图遍历。

好的运行时让发现是确定性的，让披露是有意为之的。

> Your agent has 200 installed skills. Loading every `SKILL.md`, reference file, script, and template at session start would bury the current task in unrelated procedure. Loading nothing would force the user to remember exact filesystem paths.
> A good runtime makes discovery deterministic and disclosure intentional.

## The Concept · 概念

### Discovery is a compiler pipeline · 发现是一条编译器流水线

把文件系统当作源输入。不要把原始路径直接发布给模型。

```figure
skill-discovery-pipeline
```

每个阶段都应产出结构化数据和结构化失败。一份发现日志应能回答：

- 搜索了哪些根目录？
- 发现了哪些候选？
- 哪些候选被拒绝，为什么？
- 冲突中哪个包胜出？
- 哪些目录条目因预算被截短或省略？

没有这些证据，「模型没用我的技能」几乎无法诊断。

> Treat the filesystem as source input. Do not publish raw paths directly to the model.
> Each stage should produce structured data and structured failures. ... Without that evidence, "the model did not use my skill" is almost impossible to diagnose.

### Scope is runtime policy · Scope 是运行时策略

可移植的规范定义的是技能包，而不是某个通用的安装路径或优先级顺序。由宿主决定去哪里搜索。

一个通用运行时可能使用这些 scope：

| Scope | 示例根目录 | 归属 |
|---|---|---|
| Workspace | `<repo>/.agents/skills/` | 项目维护者 |
| User | `<user-data>/skills/` | 单个开发者 |
| Administrator | `<system>/skills/` | 机器或组织策略 |
| Plugin | 签名的插件捆绑包 | 插件发布者与安装器 |
| Built-in | 运行时包 | 运行时厂商 |

截至 2026 年 8 月，Codex 文档化的项目发现从 `$CWD/.agents/skills` 沿祖先目录向上直到仓库根，外加用户、管理员和内置位置。它支持符号链接的技能目录。重名可以同时出现而不是被合并。这些是 Codex 的行为，不是 `SKILL.md` 的要求；编写适配器时请核对当前的 [Codex skill documentation](https://learn.chatgpt.com/docs/build-skills)。

永远不要从目录名里发明优先级。把它声明成策略并测试它。本课实验为每个 `Scope` 使用显式的整数排名，让同一候选集总是以同样的方式裁决。

> The portable specification defines a skill package, not one universal installation path or precedence order. The host decides where it searches.
> Never invent precedence from directory names. Declare it as policy and test it. The lesson lab uses an explicit integer rank for each `Scope` so the same candidate set always resolves the same way.

### Collisions need identity beyond `name` · 冲突需要 `name` 之外的身份

两个都叫 `release-readiness` 的包可以是合法的：一个是工作区覆盖，一个是用户默认。因此目录条目至少需要：

```json
{
  "name": "release-readiness",
  "description": "Inspect a release candidate for this repository.",
  "scope": "workspace",
  "source": "/repo/.agents/skills/release-readiness",
  "selected": true
}
```

常见的冲突策略包括：

| 策略 | 好处 | 风险 |
|---|---|---|
| 保留每个候选 | 没有东西被隐藏 | 模型会看到有歧义的名字 |
| 最高优先级 scope 胜出 | 调用简单 | 本地包可能遮蔽可信包 |
| 拒绝重复 | 没有静默遮蔽 | 合法的覆盖会失效 |
| 按来源限定名字 | 身份明确 | 用户可见的名字变长 |

为宿主选定一种策略。即便被拒绝或被遮蔽的候选不出现在模型目录中，也要把它们保留在诊断信息里。

> Two packages named `release-readiness` can be legitimate. One may be a workspace override and one a user default.
> Choose one policy for the host. Preserve the rejected or shadowed candidates in diagnostics even when they are absent from the model catalog.

### Three disclosure levels · 三个披露层级

Agent Skills 规范描述的是分阶段加载。关键在于每一层都有不同的目的。

```figure
skill-disclosure-levels
```

#### Level 1: catalog metadata · 层级 1：目录元数据

模型需要足够的信息把该技能与邻居区分开。规范估计每个目录条目约 100 个 token，但实际的序列化与分词由宿主决定。

一份有用的描述包含两个分句：

```yaml
description: Validate a release candidate and produce a readiness report. Use when the user asks whether a version, tag, or package is ready to publish.
```

第一个分句陈述能力。第二个陈述触发边界。第 25 课会用正向提示和近似命中（near-miss）提示来评估这个边界。

> The model needs enough information to distinguish the skill from neighbors. The specification estimates roughly 100 tokens per catalog entry, but actual serialization and tokenization belong to the host.
> The first clause states the capability. The second states the trigger boundary. Lesson 25 evaluates this boundary with positive and near-miss prompts.

#### Level 2: active instructions · 层级 2：激活后的指令

激活之后，正文应当既是一张地图，也是一份规程。规范建议把 `SKILL.md` 保持在 500 行以内。这是一个设计信号，不是要填满的目标。

正文应包含：

- 任务边界；
- 默认工作流；
- 分支条件；
- 指向更深文件的直接引用；
- 工具和脚本契约；
- 失败与停止行为；
- 预期输出及其验证。

不要为了让入口文件变短就把核心工作流搬进引用文件。激活必须给模型足够的上下文，让它能正确地开始。

> After activation, the body should function as a map and a procedure. The specification recommends keeping `SKILL.md` under 500 lines. That is a design signal, not a target to fill.
> Do not move the central workflow into a reference merely to make the entry file short. Activation must give the model enough context to begin correctly.

#### Level 3: supporting resources · 层级 3：支撑资源

引用（references）提供散文或数据。脚本（scripts）提供确定性计算。资产（assets）会被复制、填充或转换成交付物，而不是被当作指令。

| 目录 | 模型会读它吗？ | 模型会执行它吗？ | 典型内容 |
|---|:---:|:---:|---|
| `references/` | 会，按需 | 不会 | schema、策略、领域指南 |
| `scripts/` | 可能检查它 | 通过被许可的工具 | 校验器、转换器、收集器 |
| `assets/` | 只在有用时 | 不会 | 模板、夹具、图片、起始文件 |

这些名字只是约定，不是魔法能力。宿主仍然需要文件访问权限和一个执行工具。

> References supply prose or data. Scripts provide deterministic computation. Assets are copied, filled, or transformed into deliverables rather than treated as instructions.
> These names are conventions, not magic capabilities. The host still needs file access and an execution tool.

### Branch-specific references beat topic dumps · 按分支给引用，胜过主题大杂烩

把入口文件写成一张决策地图：

```markdown
## Choose the path

- For a Python package, read `references/python-release.md`.
- For a container image, read `references/container-release.md`.
- For a documentation-only release, read `references/docs-release.md`.
- If the release combines artifact types, read only the guides for those artifacts.
```

这样每份引用都有一个可观察的加载条件。「想了解更多就读 `references/`」则没有。

保持引用图浅一些。官方指南建议从 `SKILL.md` 直接链接并避免深层链。一跳就让可达性变得可测试，也降低了某个必要约束永远进不了上下文的概率。

```figure
skill-reference-map
```

> This gives every reference an observable load condition. "Read `references/` for more" does not.
> Keep the reference graph shallow. The official guidance recommends direct links from `SKILL.md` and avoiding deep chains. One hop makes reachability testable and reduces the chance that a needed constraint never enters context.

### Catalog budget and active context are different budgets · 目录预算和活动上下文是两笔不同的预算

设 `c_i` 为技能 `i` 的序列化目录成本，`B_c` 为目录预算，`b_j` 为活动正文成本，`r_k` 为实际加载的资源。

```text
catalog_cost = sum(c_i for every published skill)
active_cost = sum(b_j for every activated skill) + sum(r_k for every disclosed resource)
```

降低一笔预算不会自动降低另一笔。更短的描述可以省目录空间，而一个被激活的 900 行正文仍会淹没任务。把正文拆进引用文件只有在运行时和指令确实避免加载无关分支时，才能真正降低活动成本。

Codex 目前在上下文窗口大小已知时，把初始技能列表预算定为上下文窗口的 2%。8,000 字符这个值只是大小未知时的回退，并不是与 2% 规则叠加的第二个上限。当目录超出适用的预算时，描述可能被截短或省略。把这些数字当作当前的 Codex 策略，而不是 Agent Skills 标准的属性。

> Reducing one budget does not automatically reduce the other. Short descriptions can save catalog space while an activated 900-line body still overwhelms the task. Splitting the body into references can reduce active cost only when the runtime and instructions actually avoid loading irrelevant branches.
> Codex currently budgets the initial skill list at 2 percent of the context window when the context-window size is known. ... Treat those figures as current Codex policy, not a property of the Agent Skills standard.

### Resource paths are a trust boundary · 资源路径是一条信任边界

技能应当只读自己包内的文件。字面字符串前缀检查是不够的：

```text
references/../../../../.ssh/config
references/external-link -> /private/company-secrets
```

用文件系统语义解析包根与候选路径，拒绝绝对路径输入，并验证解析后的候选仍位于解析后的根之下。在发现之前就决定是否允许符号链接。如果允许，每次都要检查解析后的目标。

```figure
skill-resource-containment
```

路径包含（path containment）并不建立内容信任。一个包内合法的引用仍可能包含恶意指令。第 26 课处理那个威胁。

> A skill should read only files inside its package. Literal string-prefix checks are not enough:
> Resolve the package root and candidate with filesystem semantics, reject absolute inputs, and verify that the resolved candidate remains under the resolved root. Decide whether symlinks are allowed before discovery. If allowed, check the resolved target every time.
> Path containment does not establish content trust. A valid in-package reference can still contain malicious instructions. Lesson 26 handles that threat.

### Loading must be observable · 加载必须可观察

在不记录机密的前提下记录披露事件：

```json
{
  "event": "skill.resource.loaded",
  "skill": "release-readiness",
  "resource": "references/python-release.md",
  "reason": "candidate contains pyproject.toml",
  "bytes": 2840
}
```

reason 字段把一次上下文选择变成可审查的证据。它还有助于识别那些让 agent「以防万一」加载每个文件的指令。

> Record disclosure events without logging secrets:
> The reason turns a context choice into reviewable evidence. It also helps identify instructions that cause the agent to load every file "just in case."

## Build It · 动手造

`code/main.py` 构建一个确定性的发现与披露引擎。

发现面（discovery surface）包括：

- `Scope`：来源与优先级元数据；
- `SkillCandidate`：未经校验的文件系统候选；
- `discover_scope(scope)`：枚举直接的技能目录；
- `resolve_collisions(candidates, precedence)`：应用一种已声明的策略；
- `CatalogEntry` 与 `build_catalog(...)`：发布有界的元数据；
- `CatalogBudget`：为序列化条目记账，而不假装字符就是通用 token。

披露面（disclosure surface）包括：

- `load_skill_body(entry, ...)`：层级 2 激活；
- `validate_reference(skill_dir, reference)`：路径包含；
- `load_reference(...)`：有界的层级 3 读取。

运行实验：

```bash
cd "$(git rev-parse --show-toplevel)"
cd phases/13-tools-and-protocols/24-skill-discovery-and-progressive-disclosure
python3 code/main.py
python3 -m unittest discover -s code/tests -v
```

这段命令需要本地克隆，并能从该克隆内的任意工作目录解析出仓库根。

演示会创建临时的项目与用户 scope，插入一个冲突，在故意调小的预算下构建目录，激活一个技能，然后尝试一次合法的引用读取和一次穿越逃逸。不安装任何永久文件。

> `code/main.py` builds a deterministic discovery and disclosure engine.
> The demo creates temporary project and user scopes, inserts a collision, builds a catalog under a deliberately small budget, activates one skill, and attempts both a valid reference read and a traversal escape. No permanent files are installed.

### Why discovery is shallow · 为什么发现是浅层的

`discover_scope` 只检查直接子目录中的 `SKILL.md`，不会把每个嵌套的 `SKILL.md` 递归地当作独立包。这保住了包边界，避免把已安装技能内部的示例或夹具意外发布出去。

> `discover_scope` checks immediate child directories for `SKILL.md`. It does not recursively treat every nested `SKILL.md` as a separate package. This preserves the package boundary and avoids accidentally publishing examples or fixtures inside an installed skill.

### Why the lab does not parse arbitrary YAML · 为什么实验不解析任意 YAML

实验只支持其目录所需的标量 frontmatter。生产运行时应使用带显式 schema、大小限制并禁用自定义对象构造的安全 YAML 解析器。「仅用标准库」是教学约束，不是默许你悄悄发明一门残缺 YAML 方言的许可证。

> The lab supports the scalar frontmatter needed for its catalog. A production runtime should use a safe YAML parser with an explicit schema, size limits, and disabled custom object construction. "Stdlib-only" is a teaching constraint, not permission to invent a partial YAML dialect silently.

## Use It · 实战用法

把这份清单应用到任何发现适配器上：

1. 列出每个已配置的根目录，以及谁有权写入它。
2. 声明是否允许符号链接的包。
3. 校验包名、目录名、必需元数据和入口正文大小。
4. 在内部身份中保留来源与 scope。
5. 声明并测试重名行为。
6. 精确测量发送给模型的序列化目录。
7. 记录正文或资源为何被加载。
8. 把资源读取限制在解析后的包根之内。
9. 引用文件缺失时清晰地失败。
10. 安装或策略变化时重建目录。

> Apply this checklist to any discovery adapter:

## Ship It · 交付

本课产出 `skill-catalog-builder` 捆绑包。它扫描显式排序的根目录，拒绝符号链接的入口文件和名字与目录不匹配的包，裁决跨 scope 冲突，拒绝同优先级的重复，并把选中的元数据装进已声明的条目、描述和序列化字符预算内。

它的 JSON 报告包含选中条目、被遮蔽候选、被省略条目、校验错误、优先级和预算使用情况。正文与引用加载仍是独立的运行时操作，因此目录构建器不执行脚本，也不把整个包放进上下文。

> This lesson produces the `skill-catalog-builder` bundle. It scans explicitly ordered roots, rejects symlinked entry files and name-directory mismatches, resolves cross-scope collisions, rejects equal-precedence duplicates, and fits selected metadata into declared entry, description, and serialized-character budgets.
> Its JSON report contains selected entries, shadowed candidates, omitted entries, validation errors, precedence, and budget use. Body and reference loading remain separate runtime operations, so the catalog builder does not execute scripts or admit the whole package into context.

## Exercises · 练习

1. 添加一个插件 scope，把它的优先级放在用户与内置之间。用测试证明冲突裁决结果。
2. 把冲突策略从最高优先级改为限定名字。在目录中保留两个条目。
3. 给 `load_reference` 加字节大小上限。分别测试恰好等于上限和超出一字节的文件。
4. 写两份听起来几乎一样的描述。重写它们，让触发边界互不重叠。
5. 添加一份包含每个引用和脚本哈希的清单（manifest）。在加载资源之前检测出被篡改的资源。
6. 给演示加插桩，分别报告层级 1、层级 2、层级 3 的字节数。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|---|---|---|
| Skill discovery（技能发现） | "Find every SKILL.md"（找到每个 SKILL.md） | 搜索已配置的 scope，校验包，附加来源信息，并应用策略 |
| Skill catalog（技能目录） | "The list of installed skills"（已安装技能的列表） | 面向模型的路由元数据，为合格包提供紧凑展示 |
| Collision policy（冲突策略） | "Which duplicate wins"（哪个重复者胜出） | 一条针对来自不同来源的同名候选的已声明规则 |
| Progressive disclosure（渐进式披露） | "Lazy loading"（懒加载） | 从目录到正文再到分支特定资源的分阶段上下文准入 |
| Reference graph（引用图） | "Files linked by the skill"（技能链接的文件） | 可达的资源结构及其加载条件 |
| Path containment（路径包含） | "Stay in the folder"（待在文件夹里） | 验证解析后的资源目标仍位于解析后的包根之内 |

## Further Reading · 延伸阅读

- [Agent Skills specification](https://agentskills.io/specification) —— 包形状与渐进式披露层级。
- [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) —— 目录路由元数据。
- [Agent Skills best practices](https://agentskills.io/skill-creation/best-practices) —— 直接引用与入口文件大小。
- [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills) —— 当前 Codex 的发现 scope 与目录限制。
