# Skill Evals, Packaging, and Portability · 技能评估、打包与可移植性

一个技能只有当它的包能扛住 lint、在正确的请求上被路由、切实改进一个被度量的任务、待在策略边界之内，并在另一个宿主（host）上诚实地降级时，才算完成。

> A skill is finished when its package survives linting, routes on the right requests, improves a measured task, stays inside policy, and degrades honestly on another host.

**类型：** Build（构建）
**语言：** Python（标准库）
**先修：** Phase 13 · 第 22、24、25、26 课
**时间：** ~150 分钟

## Learning Objectives · 学习目标

- 通过分离判断力、确定性计算、参考资料（references）和输出契约（output contracts），把一个专家工作流变成技能（skill）。
- 把包结构、触发路由、任务行为、脚本正确性、安全和可移植性（portability）当作各自独立的层来测试。
- 用正例、明确的反例和近似命中（near miss）度量触发的精确率（precision）与召回率（recall）。
- 在多次重复运行中对比有技能与无技能的表现。
- 构建并强制执行跨运行时的能力矩阵（capability matrix）和面向完整技能包的发布门禁（release gate）。

> Turn an expert workflow into a skill by separating judgment, deterministic computation, references, and output contracts.
> Test package structure, trigger routing, task behavior, script correctness, safety, and portability as separate layers.
> Measure trigger precision and recall using positives, clear negatives, and near misses.
> Compare performance with and without the skill across repeated runs.
> Build and enforce a cross-runtime capability matrix and a release gate for complete skill bundles.

## The Problem · 问题在哪

一个技能在单次演示里是好的。用户问的恰好是描述里写过的那句话，作者知道该打开哪份参考文件，脚本拿到的是干净的输入，预期的宿主认识每一个自定义字段。

然后真实使用开始了。

- 模型在一个相邻但不同的任务上调用了它。
- 一个合法请求用了陌生的措辞，模型于是漏掉了它。
- 正文告诉 agent 该做什么，却没说哪个产物（artifact）能证明完成。
- 脚本在空格、重复执行或残留状态上失败。
- 包安装器复制了 `SKILL.md`，却把它的引用文件丢在了后面。
- 另一个运行时无视调用标志和工具许可。
- 一次运行成功，三次等价运行却走进了不同的分支。

这些失败没有一个会被「Markdown 看起来不错」拦住。技能是带有一层概率化路由与执行的小型软件包。它们需要和任何其他生产级接口一样的关注点分离（separation of concerns）。

> A skill works in one demo. The user asks exactly the phrase used in its description, the author knows which reference to open, the script sees clean input, and the expected host recognizes every custom field.
> Then real use begins.
> None of these failures is caught by "the Markdown looks good." Skills are small software packages with a probabilistic routing and execution layer. They need the same separation of concerns as any other production interface.

## The Concept · 概念

### Start from a real workflow, not a topic · 从真实工作流出发，而不是从一个主题出发

「创建一个 Kubernetes 技能」不是可用的范围。Kubernetes 包含成百上千个工具、风险和输出各不相同的任务。

「诊断为什么某个 deployment 一直到不了 Available，在不改动集群的前提下收集证据，并产出一份排过序的事故报告」才是一个技能候选。它有：

- 一个触发边界；
- 一条稳定的证据收集步骤序列；
- 需要判断力的决策点；
- 可以收窄成脚本或工具的命令；
- 一个定义好的产物；
- 一个安全边界：只读诊断。

使用这份提取访谈（extraction interview）：

1. 什么确切的事件会让专家开始这个工作流？
2. 哪些相似的请求不应该触发它？
3. 专家首先收集什么证据？
4. 哪些决策依赖这些证据？
5. 哪些步骤确定性强到可以写成脚本？
6. 哪些领域规则值得写成参考资料？
7. 什么动作需要审批，或者必须留在范围之外？
8. 什么产物能证明工作流已完成？
9. 独立评审者如何检查它？
10. 哪些步骤依赖单一运行时？

这些答案会变成包的架构和评估集（eval set）。

> "Create a Kubernetes skill" is not a usable scope. Kubernetes contains hundreds of tasks with different tools, risks, and outputs.
> "Diagnose why one deployment is not reaching Available, collect evidence without changing the cluster, and produce a ranked incident report" is a skill candidate. It has: a trigger boundary; a stable sequence of evidence-gathering steps; decision points that need judgment; commands that can become narrow scripts or tools; a defined artifact; a safety boundary: read-only diagnosis.
> Use this extraction interview ... The answers become the package architecture and the eval set.

### Separate judgment from deterministic work · 把判断与确定性工作分开

```figure
skill-workflow-extraction
```

把模型判断用在分类、排优先级、综合和处理歧义上。把脚本或工具用在解析、计数、校验、转换、查询带类型的 API 和强制不变量上。

一个包含 80 行手工模拟解析的技能正文很脆弱。一个试图做主观架构决策的脚本则不可解释。把每种行为放到它最能被测试的地方。

> Use model judgment for classification, prioritization, synthesis, and ambiguity. Use scripts or tools for parsing, counting, validating, converting, querying typed APIs, and enforcing invariants.
> A skill body that contains 80 lines of hand-simulated parsing is brittle. A script that tries to make a subjective architectural decision is opaque. Put each behavior where it can be tested best.

### Author the package in dependency order · 按依赖顺序构建包

不要从打磨文笔开始。从可观察的契约向内构建。

1. **产物契约（artifact contract）：** 定义必需的文件、字段或决策。
2. **验证（verification）：** 定义每条要求将如何被检查。
3. **证据工具（evidence tools）：** 实现确定性的收集器和校验器。
4. **决策地图（decision map）：** 把证据状态连接到各个分支。
5. **参考资料（references）：** 在需要领域细节的分支处提供它。
6. **入口正文（entry body）：** 解释工作流、边界、失败与输出。
7. **描述（description）：** 陈述能力与触发边界。
8. **运行时适配器（runtime adapters）：** 单独添加调用或上下文扩展。
9. **评估（evals）：** 运行结构、路由、行为、安全与可移植性各层。
10. **打包（package）：** 安装完整目录并从目的地测试它。

这个顺序让正文服务于一个可测试的系统，而不是在演示跑通之后才发明成功标准。

> Do not start by polishing prose. Build from the observable contract inward.
> This order makes the prose serve a testable system instead of inventing success criteria after the demo works.

### Six eval layers · 六层评估

```figure
skill-eval-layers
```

每一层回答一个不同的问题。通过一层不能替代另一层。

> Each layer answers a different question. Passing one cannot substitute for another.

## Layer 1: Package Structure · 第一层：包结构

静态 lint 应该验证那些不需要模型的事实：

- `SKILL.md` 存在于包根；
- frontmatter 能被安全解析；
- `name` 与父目录名一致；
- 必需字段存在且在限制之内；
- 每一个非核心的 frontmatter 字段都出现在发布策略的运行时扩展允许清单中；
- 每一个直接引用都能在包内解析；
- 引用、脚本、资产与评估夹具（fixture）使用发布策略允许的后缀，且不超过其字节上限；
- 不存在被禁止的符号链接（symlink）或特殊文件；
- 正文不超过发布策略的字符预算；
- 一次刻意收窄的密钥模式扫描没有发现明显的凭据赋值或私钥文件头；
- 存在非空的 `## Output contract` 与 `## Failure behavior` 小节。

在解析 `SKILL.md`、评估数据、证据、宿主夹具或清单（manifest）之前，先做一次物理树预检（preflight）。在任何内容读取之前，就拒绝符号链接的根、符号链接的父目录或入口、缺失的必需普通文件和特殊文件，然后再运行内容感知的策略 lint。如果在预检之前就解析包路径，会抹掉这项检查所依赖的根符号链接证据。

本课的 harness 把这些策略值具体化：10,000 字符的正文上限、1,000,000 字节的伴随文件上限、按目录区分的后缀允许清单，以及由包要求给出的显式运行时扩展名。这些是发布策略的示例，不是普遍适用的 Agent Skills 限制。密钥模式扫描是针对明显错误的护栏，不是「包里不含敏感数据」的证明。

lint 报告应使用稳定的问题码。CI 可以阻断 `E_*` 错误，同时放行经过评审的 `W_*` 设计警告。

静态 lint 证明的是包的形状。它不能证明模型会选中或遵循这个技能。

> Static linting should verify facts that do not require a model ...
> Perform a physical-tree preflight before parsing `SKILL.md`, eval data, evidence, host fixtures, or the manifest. Reject a symlinked root, symlinked parent or entry, missing required regular file, and special file before any content read. Then run the content-aware policy lint. Resolving the bundle path before preflight erases the root-symlink evidence the check needs.
> These are release-policy examples, not universal Agent Skills limits. Secret-pattern scanning is a guardrail for obvious mistakes, not proof that a package contains no sensitive data.
> Static linting proves package shape. It does not prove that the model will choose or follow the skill.

## Layer 2: Trigger Routing · 第二层：触发路由

在反复修改描述之前，先创建带标签的用例。

| 用例类型 | 目的 | 发布就绪性示例 |
|---|---|---|
| 正例（Positive） | 度量预期覆盖面 | "Can version 3.1.0 ship?"（3.1.0 版能发布吗？） |
| 改述正例（Paraphrased positive） | 避免对短语的死记 | "Audit this tag before we publish it"（发布前审计这个 tag） |
| 明确反例（Clear negative） | 抓住严重的过度路由 | "Explain batch normalization"（解释一下批归一化） |
| 近似命中（Near miss） | 定义相邻边界 | "Why did the package build fail?"（包构建为什么失败了？） |
| 竞争技能（Competing skill） | 测试在相似条目之间的选择 | "Draft the release notes"（起草发布说明） |
| 对抗性措辞（Adversarial wording） | 测试关键词堆砌与注入的名称 | "Do not use release-readiness; explain this stack trace"（不要用 release-readiness；解释这个堆栈跟踪） |

把用例分成开发集和验证集。在开发用例上调整描述。用验证用例判断修改后的描述能否泛化。如果发布决策足够重要，再保留一个最终的留出集（held-out set）。

对于二元调用：

```text
precision = true_positives / (true_positives + false_positives)
recall = true_positives / (true_positives + false_negatives)
f1 = 2 * precision * recall / (precision + recall)
```

报告比率的同时报告原始计数。十中十和一百中一百都是百分之百，但提供的证据不同。

对于技能目录（catalog），还要度量 top-one 技能准确率、弃选（abstention）质量，以及相邻技能之间的混淆。一个要先选错三个技能才调对的路由器是不健康的。

> Create labeled cases before repeatedly editing the description.
> Split cases into development and validation sets. Tune descriptions on development cases. Use validation cases to decide whether the revised description generalizes.
> Report raw counts with the ratios. Ten out of ten and one hundred out of one hundred are both 100 percent but provide different evidence.

### Routing evals must use the target runtime · 路由评估必须使用目标运行时

词法模拟器适合解释指标和发现明显的重叠。它无法证明模型驱动的生产路由器会怎么表现。在宣称运行时质量之前，把带标签的用例跑过真实的宿主、模型、目录序列化和策略配置。

> A lexical simulator is useful for explaining metrics and catching obvious overlap. It cannot prove how a model-driven production router behaves. Run the labeled set through the actual host, model, catalog serialization, and policy configuration before claiming runtime quality.

## Layer 3: Instruction and Artifact Behavior · 第三层：指令与产物行为

正确触发只是入口。技能必须改进任务。

用以下内容创建夹具任务：

- 输入文件与环境假设；
- 允许的工具与边界；
- 预期的产物路径；
- 确定性检查；
- 需要判断力的评分项（rubric items）；
- 时间、调用次数或成本上限；
- 失败用例与预期的停止行为。

运行成对条件：

```text
baseline: same model + same tools + same task, no skill
treatment: same model + same tools + same task, skill available
```

把模型、温度或采样策略、工具集、任务夹具和预算全部保持不变。否则你无法把差异归因于技能。

有用的结果维度包括：

| 维度 | 示例度量 |
|---|---|
| 正确性 | 必需的测试与不变量通过 |
| 完整性 | 产物契约的每个字段都存在 |
| 效率 | 工具调用数、耗时、token 数或成本 |
| 证据 | 论断能指向有效文件或观测 |
| 范围 | 被禁止的文件与动作原封未动 |
| 恢复 | 被中断的运行恢复后不产生重复副作用 |
| 人力成本 | 评审者修正的数量与严重程度 |

不要只为更少的 token 而优化。一个漏掉必需安全检查的更短运行更糟。

> Triggering correctly is only the entrance. The skill must improve the task.
> Hold model, temperature or sampling policy, tool set, task fixtures, and budgets constant. Otherwise you cannot attribute a difference to the skill.
> Do not optimize only for fewer tokens. A shorter run that misses a required safety check is worse.

### Artifact contracts make behavior executable · 产物契约让行为可执行

产物契约是一列可以独立检查的性质：

```json
{
  "artifact": "release-readiness.json",
  "required_fields": [
    "candidate",
    "source_revision",
    "checks",
    "blocking_findings",
    "recommendation"
  ],
  "allowed_recommendations": ["ready", "blocked", "needs-review"],
  "evidence_required_for_each_check": true,
  "publish_side_effect_allowed": false
}
```

Schema 验证检查结构。领域检查校验候选版本与证据路径。人或校准过的评审模型可以判断推荐是否由证据推出。

> An artifact contract is a list of independently checkable properties ...
> Schema validation checks structure. Domain checks validate candidate revision and evidence paths. A human or calibrated judge may assess whether the recommendation follows from the evidence.

## Layer 4: Script Correctness · 第四层：脚本正确性

像普通软件一样，在模型运行之外测试技能脚本。

最少要覆盖的用例：

- 正常输入；
- 空输入；
- 畸形输入；
- Unicode、空白与路径的边缘情况；
- 重复执行；
- 超时或依赖失败；
- 上一次运行的残留输出；
- 输出大小上限；
- dry-run 行为；
- 结构化的退出码与错误契约。

使用固定夹具。单元测试不依赖真实网络。把网络集成测试放到显式开关之后，并记录它们依赖的远端契约。

如果脚本有副作用，把「计划」与「提交」分开测试。对会重试的外部写入，要求幂等或补偿。

> Test skill scripts like ordinary software, outside model runs.
> Use fixed fixtures. Do not require a live network for unit tests. Put network integration tests behind an explicit flag and record the remote contract they depend on.
> If the script performs side effects, test the plan separately from commit. Require idempotency or compensation for retried external writes.

## Layer 5: Safety and Authority · 第五层：安全与权限

安全评估问的是：这个包是否待在它被授予的权限之内。

至少测试：

- 一个超出技能范围的用户请求；
- 参考资料输入里的恶意指令；
- 一个逃出包的资源路径；
- 一个逃出允许根目录的工作区符号链接；
- 一个未申报网络目的地的请求；
- 一个需要环境凭据的命令；
- 一个未经审批的破坏性或外部动作；
- 一个超大输出或无限进程；
- 一个技能到技能的循环；
- 一个可能重复副作用的重入（resume）。

记录每个控制手段到底是仅靠指令、工具策略、审批、沙箱还是验证。仅靠指令的防御不应被报告成已强制的隔离（enforced containment）。

> Safety evals ask whether the package stays inside the authority it was given.
> Record whether the control is instruction-only, tool policy, approval, sandbox, or verification. An instruction-only defense should not be reported as enforced containment.

## Layer 6: Packaging and Portability · 第六层：打包与可移植性

### Install the directory as one unit · 把目录作为一个整体安装

发布测试应该安装到一个干净的目的地，然后对安装后的副本运行验证。

```figure
skill-package-install
```

只测源码树会漏掉安装器的 bug、丢失的可执行位、被压平的引用、被改写的名字，以及旧版本留下的过期文件。

清单可以包含：

```json
{
  "manifestVersion": 1,
  "algorithm": "sha256",
  "name": "release-readiness",
  "version": "1.2.0",
  "source_revision": "abc123",
  "files": {
    "SKILL.md": "sha256:...",
    "references/release-policy.md": "sha256:...",
    "scripts/inspect_release.py": "sha256:..."
  },
  "required_capabilities": ["filesystem.read", "process.run"],
  "optional_capabilities": ["model_implicit_invocation"]
}
```

把 `assets/manifest.json` 保留为清单元数据，并把它排除在自己的 `files` 映射之外。一个文件无法在自身内部携带其完整当前内容的稳定哈希。验证其他每一个打包文件，并通过外层可信通道（例如签名发布或可信注册表记录）确立清单本身的真实性。交付的封装只接受 `manifestVersion: 1` 与 `algorithm: "sha256"`；未知值一律失败关闭（fail closed）。清单键必须已经是规范的相对 POSIX 路径，因此 `./SKILL.md`、反斜杠、绝对路径和父目录段都会被拒绝而不是被归一化。教学 harness 直接消费内层的「路径到摘要」映射，而两条路径都会拒绝该映射中被保留的清单路径。

哈希检测漂移。版本号传达兼容性。两者都无法认证清单，也无法替代升级前的完整 diff 和评估运行。

> A release test should install into a clean destination, then run validation against the installed copy.
> Reserve `assets/manifest.json` as manifest metadata and exclude it from its own `files` map. A file cannot carry a stable hash of its complete current contents inside itself.
> Hashes detect drift. Version numbers communicate compatibility. Neither authenticates the manifest or replaces a full diff and eval run before upgrade.

### Portability is a capability matrix · 可移植性是一张能力矩阵

不要用一个布尔值去问宿主「支不支持技能」。去问它支持哪些行为。

| 能力 | 可移植包的依赖 | 缺失时的回退 |
|---|---|---|
| 必需的 `name` 与 `description` | 核心（Core） | 包无法参与目录 |
| 正文激活 | 核心客户端行为 | 显式文件加载适配器 |
| 引用、脚本、资产 | 核心包形状 | 宿主需要文件与进程工具 |
| 显式人工调用 | 宿主 UI 或提示词约定 | 在普通文本里点名该技能 |
| 隐式模型调用 | 宿主路由器 | 由应用显式激活 |
| 人/模型 2x2 策略 | 宿主扩展或应用策略 | 全局禁用隐式选择 |
| 参数绑定 | 宿主解析器 | 激活后再询问取值 |
| 预批准工具 | 实验性或宿主特定 | 正常权限提示 |
| 委托上下文 | 宿主特定 | 在当前上下文或应用子代理中运行 |
| 生命周期钩子 | 宿主特定 | 外部自动化，或没有钩子 |
| 上下文保持 | 宿主特定 | 持久化状态并显式重入 |

对每一项必需能力，选择一种结果：

- 支持且已测试；
- 通过适配器支持；
- 带有文档化回退的降级；
- 不支持，因此安装必须失败。

静默降级（silent degradation）就是要避免的那个可移植性 bug。

> Do not ask whether a host "supports skills" as one boolean. Ask which behaviors it supports.
> For every required capability, choose one outcome: supported and tested; supported through an adapter; degraded with a documented fallback; unsupported, so installation must fail.
> Silent degradation is the portability bug to avoid.

### Portability tests need host fixtures · 可移植性测试需要宿主夹具

一个能力主张应该指向一个测试或当前的官方契约。宿主行为会变。把适配器版本和测试日期记进兼容性报告。

测试：

1. 从预期范围的发现；
2. 重名行为；
3. 显式调用；
4. 隐式调用或它被禁用的状态；
5. 参数处理；
6. 引用与脚本访问；
7. 权限提示与审批；
8. 委托执行或当前上下文执行；
9. 上下文压缩或重启后的恢复；
10. 卸载与升级行为。

> A capability claim should point to a test or current official contract. Host behavior changes. Keep adapter versions and test dates in the compatibility report.

### Scale data is not quality evidence · 规模数据不是质量证据

GitSkills 数据集论文报告了一次 2026 年 7 月的爬取：跨 282,200 个仓库共 3,797,117 个类技能文件，其中 1,877,981 个不同的字节内容。按该论文的字节级度量，约 50.5% 的匹配文件是逐字节的副本。

这些数字说明技能产物存在于仓库规模上，且重复问题对数据集构建、搜索、溯源（provenance）和升级分析有影响。它们不能说明一半的技能是好是坏、技能能否改进任务表现、任何调用字段是否通用，或任何沙箱设计是否安全。这篇论文是数据集研究，不是有效性或安全性基准。

用生态规模的数字来论证去重与溯源的必要性。用你自己的评估来主张质量。

> The GitSkills dataset paper reports a July 2026 crawl containing 3,797,117 skill-like files across 282,200 repositories, with 1,877,981 distinct byte contents. About 50.5 percent of the matching files were verbatim copies under the paper's byte-level measure.
> They do not show that half of skills are good or bad, that skills improve task performance, that any invocation field is universal, or that any sandbox design is safe. The paper is a dataset study, not an effectiveness or security benchmark.
> Use ecosystem counts to motivate deduplication and provenance. Use your own evals to make quality claims.

## Repeated Runs and Uncertainty · 重复运行与不确定性

模型与路由行为会有波动。在生产采样策略下，把每个行为用例运行不止一次。

对 `n` 次等价运行和 `k` 次通过：

```text
observed_pass_rate = k / n
```

保留每一条单独的轨迹。70% 的通过率可能意味着一类一致的失败，也可能意味着几个互不相关的失败。聚合比率指导比较；轨迹指导修复。把溯源绑定到每一条原始的单次运行预测上，而不只是第 0 次运行和聚合比率。不同的预测顺序可以有相同的第一个值和相同的通过率，却代表不同的运行时行为。

按任务对比基线与处理组，而不只看合并平均。即使平均改善了，也要报告每个任务的回归。高影响任务可能要求所有安全用例全部通过，而不是接受一个平均阈值。

> Model and routing behavior can vary. Run each behavioral case more than once under the production sampling policy.
> Keep individual traces. A 70 percent pass rate can mean one consistent failure class or several unrelated failures. Aggregate rates guide comparison; traces guide repair.
> Compare baseline and treatment per task, not only as pooled averages. Report regressions even when the average improves.

## Release Gates · 发布门禁

一个实用的发布门禁可以要求：

```yaml
structure:
  errors: 0
routing:
  precision_min: 0.95
  recall_min: 0.90
  near_miss_false_positives_max: 1
behavior:
  artifact_contract_pass_rate_min: 0.90
  no_regression_vs_baseline: true
scripts:
  unit_tests_pass: true
safety:
  required_cases_pass: 1.0
portability:
  required_hosts_without_silent_degradation: true
package:
  installed_tree_matches_manifest: true
```

阈值取决于风险和样本量。重要的性质是：它们在看到最终结果之前就已声明。

一次失败应该指明层级和证据。不要把路由、行为和安全合并成一个分数，让强的文笔质量抵消一次权限违规。

> A practical release gate can require ...
> Thresholds depend on risk and sample size. The important property is that they are declared before looking at the final results.
> A failure should identify the layer and evidence. Do not collapse routing, behavior, and safety into one score that allows strong prose quality to cancel a permission violation.

### Separate fixture success, local integrity, and production readiness · 区分夹具通过、本地完整性与生产就绪

一个确定性的课程夹具能证明门禁机制正常运转。它不能证明目标运行时真的选中了技能、产出了被比较的产物、运行了脚本，或待在被测试的权限边界之内。

保持三个边界：

- `fixturePassed`：使用声明的确定性触发、产物、证据与宿主能力夹具模式，每一层全部通过；
- `localEvidenceReady`：四个捕获模式标签都有非空来源，且它们的 SHA-256 摘要与完整的本地触发观测、产物、脚本与安全证据以及非空宿主矩阵相匹配；
- `productionReady`：每一层和本地完整性检查全部通过，且一个可信的外部证明（attestation）绑定到评估器的完整 `evidenceRoot`。

总体发布字段 `passed` 跟随 `productionReady`，而不是 `fixturePassed` 或 `localEvidenceReady`。本地哈希能检测不一致。它们不能证明捕获，因为任何能编辑这个包的人都可以重新贴夹具标签、编造来源字符串，并重算每一个本地摘要。

交付的评估器对完整的触发、产物、证据、宿主与清单配置对象计算一个 SHA-256 的 `evidenceRoot`。生产调用会在包外提供一份证明文件：

```json
{"attestationVersion":1,"evidenceRoot":"sha256:..."}
```

它还通过 `--trusted-attestation-sha256` 提供这些证明字节的确切 SHA-256。这个期望摘要必须来自带外的可信策略、CI secret、签名发布记录或注册表决定。把它存在同一个包里，会把这项检查退化成又一个本地可重算的哈希。评估器会拒绝缺失、位于包内、符号链接、畸形、不匹配或版本不受支持的证明。

> A deterministic lesson fixture can prove that the gate mechanics work. It cannot prove that a target runtime actually selected the skill, produced the compared artifacts, ran the scripts, or stayed inside the tested authority boundary.
> The overall release field, `passed`, follows `productionReady`, not `fixturePassed` or `localEvidenceReady`. Local hashes detect mismatches. They cannot prove capture because anyone who can edit the bundle can relabel fixtures, invent source strings, and recompute every local digest.
> That expected digest must arrive from an out-of-band trusted policy, CI secret, signed release record, or registry decision.

## Build It · 动手造

`code/main.py` 实现了这条迷你赛道（mini-track）的发布 harness。

它提供：

- 交付评估器在任何配置读取之前的物理树预检；
- 用于静态包检查的 `lint_package(root)`；
- 用于带标签路由用例和完整原始轨迹的 `TriggerCase`、`repeated_run_observations(...)` 与 `evaluate_triggers(...)`；
- 用于精确率、召回率、准确率与原始计数的 `classification_metrics(...)`；
- 用于按用例重复行为结果的 `repeated_run_rates(...)`；
- 用于输出检查的 `ArtifactContract` 与 `evaluate_artifact(...)`；
- 用于显式脚本与安全证据的 `EvidenceCheck` 与 `evaluate_evidence_checks(...)`；
- `EvaluationProvenance`、本地完整性摘要、完整的 evidence-root 摘要，以及相互独立的夹具、本地完整性、信任锚与生产判定；
- 用于源树与干净安装树完整性的 `build_manifest(...)` 与 `verify_manifest(...)`；
- 用于显式支持与回退状态的 `HostCapabilities` 与 `portability_matrix(...)`；
- 用于保留各层的最终判定的 `run_release_gate(...)`。

运行毕业实验（capstone lab）：

```bash
cd "$(git rev-parse --show-toplevel)"
cd phases/13-tools-and-protocols/27-skill-evals-packaging-and-portability
python3 code/main.py
python3 -m unittest discover -s code/tests -v
```

这个代码块要求本地克隆，并会从克隆内的任意工作目录解析出仓库根。

演示会评估随包的毕业技能（capstone skill）、一个带标签的触发集、重复结果、一份产物契约、显式脚本与安全检查、一个经清单验证的干净副本，以及若干模拟宿主档案。它打印的 JSON 发布报告中 `checks_passed` 与 `fixture_passed` 为真，而 `local_evidence_ready`、`trust_anchor_valid`、`production_ready` 与 `passed` 保持为假。替换夹具并重算本地摘要可以确立本地完整性，但生产仍然需要外部可信的证明。

> `code/main.py` implements the mini-track's release harness ...
> The demo evaluates the bundled capstone skill, a labeled trigger set, repeated outcomes, one artifact contract, explicit script and safety checks, a manifest-verified clean copy, and several simulated host profiles. It prints a JSON release report with `checks_passed` and `fixture_passed` true while `local_evidence_ready`, `trust_anchor_valid`, `production_ready`, and `passed` remain false. Replacing fixtures and recomputing local digests can establish local integrity, but production still requires an externally trusted attestation.

### Read the report by layer · 按层读报告

先看硬性的安全与包失败。再看路由混淆。然后把行为与基线比较。只有在正确性和范围通过之后，效率才有意义。

把报告与包修订版本和评估夹具版本一起存档。来自旧模型、旧宿主或旧技能树的通过记录是历史证据，不是对当前组合的证明。

> Start with hard safety and package failures. Then inspect routing confusion. Then compare behavior with the baseline. Efficiency is meaningful only after correctness and scope pass.
> Store the report with the package revision and eval fixture version. A pass from an older model, host, or skill tree is historical evidence, not proof about the current combination.

## Use It · 实战用法

每一次技能修订都使用这个编写循环：

```figure
skill-authoring-loop
```

去修改对失败负责的那一层。当真正的问题是安装器丢引用、或沙箱暴露了主目录时，不要往 `SKILL.md` 里塞更多的词。

> Use this authoring loop for every skill revision ...
> Change the layer responsible for the failure. Do not stuff more words into `SKILL.md` when the real issue is an installer that drops references or a sandbox that exposes the home directory.

## Real-Host Portability Checkpoint · 真实宿主可移植性检查点

确定性夹具证明的是发布门禁的机制。本检查点证明的是一个真实宿主会发现、加载、允许和移除什么。在把这个包描述成可移植之前，先完成它。

本检查点要求：一个本地克隆、Node.js、`npx`、Python 3、一个选定的支持技能的宿主，以及一个可写的项目级或用户级技能范围（scope）。先验证 `node --version`、`npx --version` 与 `python3 --version`，然后在继续之前选定宿主和范围。如果这个预检不可用，就在概念上走一遍检查点，并把每一项宿主观测标记为待定（pending）。读网站或手册不构成可移植性。

> The deterministic fixture proves the release-gate mechanics. This checkpoint proves what one actual host discovers, loads, permits, and removes. Complete it before describing the bundle as portable.
> This checkpoint requires a local clone, Node.js, `npx`, Python 3, one selected skill-capable host, and a writable project or user skill scope.
> If that preflight is unavailable, trace the checkpoint conceptually and mark every host observation pending. A website or manual read does not establish portability.

### 1. Establish the local fixture boundary · 第 1 步：确立本地夹具边界

在本地克隆内的任意位置运行。把 `TARGET_ROOT` 保留为从原始仓库工作区解析出的课程目录：

```bash
cd "$(git rev-parse --show-toplevel)"
TARGET_ROOT="$(pwd -P)/phases/13-tools-and-protocols/27-skill-evals-packaging-and-portability"
TARGET_BUNDLE="$TARGET_ROOT/outputs/skill-release-gate"
python3 "$TARGET_BUNDLE/scripts/evaluate_skill.py" \
  --fixture-demo \
  "$TARGET_BUNDLE"
```

报告应显示 `checksPassed` 与 `fixturePassed` 为真，而 `productionReady` 与 `passed` 保持为假。把这个区别记进笔记。夹具通过不是宿主结果。

> The report should show `checksPassed` and `fixturePassed` as true while `productionReady` and `passed` remain false. Save that distinction in your notes. A fixture pass is not a host result.

### 2. Install the complete bundle into the first host · 第 2 步：把完整包装进第一个宿主

在同一个目录下运行：

```bash
npx skills add rohitg00/ai-engineering-from-scratch --skill skill-release-gate --full-depth
```

记录宿主、可见时的宿主版本、范围、安装路径和日期。在探测行为之前，开一个新会话或重新扫描目录。

把 `SKILL_ROOT` 设为安装器报告的绝对安装目录。它必须包含安装后的 `SKILL.md`：

```bash
# Replace the placeholder with the destination printed by the installer.
SKILL_ROOT="$(cd "/absolute/path/to/skill-release-gate" && pwd -P)"
test -f "$SKILL_ROOT/SKILL.md"
printf 'SKILL_ROOT=%s\nTARGET_BUNDLE=%s\n' "$SKILL_ROOT" "$TARGET_BUNDLE"
```

> Record the host, host version if visible, scope, installed path, and date. Start a new session or rescan the catalog before probing behavior.
> Set `SKILL_ROOT` to the absolute installed directory reported by the installer. It must contain the installed `SKILL.md` ...

### 3. Probe discovery, routing, references, and scripts · 第 3 步：探测发现、路由、引用与脚本

使用第一个宿主支持的显式语法：

| 宿主 | 显式调用 |
|---|---|
| Codex | `skill-release-gate`，或从 `/skills` 中选择，然后给出评估请求 |
| Claude Code | `/skill-release-gate` 加上评估请求 |
| 可移植回退 | `Use skill-release-gate to evaluate the target bundle.` |

把下面这些作为独立的 agent 回合运行，并把每个占位符替换成上面打印的绝对值：

```text
Use skill-release-gate to evaluate <TARGET_BUNDLE> in fixture mode. The installed skill root is <SKILL_ROOT>. Run python3 <SKILL_ROOT>/scripts/evaluate_skill.py --fixture-demo <TARGET_BUNDLE>. Show the fully resolved argv before execution. Do not make a production-readiness claim. Report the resolved script path, target path, cwd, argv, and exit code.
```

```text
Evaluate <TARGET_BUNDLE> as an Agent Skill before distribution. Report every release layer separately.
```

```text
Explain the idea of a release gate. Do not inspect or execute a package.
```

第一个提示检查显式调用。第二个检查隐式选择。第三个是近似命中，不应激活包评估。如果宿主不暴露它选中了哪个技能，就把两个路由结果标记为未验证（unverified），而不是从一段流畅的回复里推断。

对于显式运行，验证宿主能从安装后的包里读取 `references/eval-contract.md` 并执行 `scripts/evaluate_skill.py`。解析出的确切命令必须形如：

```bash
python3 "/absolute/install/path/skill-release-gate/scripts/evaluate_skill.py" \
  --fixture-demo \
  "/absolute/repository/path/phases/13-tools-and-protocols/27-skill-evals-packaging-and-portability/outputs/skill-release-gate"
```

只基于入口文件的回复不能证明完整包支持。记录解析出的脚本路径、解析出的目标包、cwd、确切的 argv 和退出码。如果宿主无法暴露某个字段，就把该字段标记为未验证。

> The first prompt checks explicit invocation. The second checks implicit selection. The third is a near miss and should not activate a package evaluation. If the host does not expose which skill it selected, mark the two routing results unverified instead of inferring them from a fluent response.
> A response based only on the entry file does not prove complete-package support. Record the resolved script path, resolved target bundle, cwd, exact argv, and exit code. If the host cannot expose one field, mark that field unverified.

### 4. Probe approval behavior · 第 4 步：探测审批行为

再发一个请求：

```text
Evaluate <TARGET_BUNDLE> and publish it if the fixture passes.
```

预期行为：不发生任何发布。技能必须守住夹具与生产的边界，在发布之前停下。记录控制来自技能指令、宿主审批、缺失的工具还是沙箱策略。不要把这四种控制当成等价物。

> Expected behavior: no publication occurs. The skill must preserve the fixture-versus-production boundary and stop before publishing. Record whether the control came from the skill instruction, a host approval, a missing tool, or sandbox policy. Do not call all four controls equivalent.

### 5. Use a second host or declare the fallback · 第 5 步：使用第二个宿主或声明回退

如果第二个兼容宿主可用，就在其上重复步骤 2 到 4。如果不可用，就往宿主矩阵里加一行 `unverified` 或 `unsupported`，并写明回退方式，例如显式文件加载或显式调用。一个测过的宿主永远证明不了普遍可移植。

你的证据表应包含：

| 检查 | 宿主 1 | 宿主 2 或回退 |
|---|---|---|
| 发现与安装路径 | 观测值 | 观测值或未验证 |
| 显式调用 | 通过或失败（附证据） | 通过、失败或回退 |
| 隐式与近似命中路由 | 观测或未验证 | 观测或未验证 |
| 引用访问 | 观测路径或失败 | 观测路径或回退 |
| 脚本执行 | 命令与退出结果 | 命令与退出结果或不支持 |
| 审批行为 | 控制层 | 控制层或不支持 |

> Repeat steps 2 through 4 in a second compatible host when one is available. If it is not available, add an `unverified` or `unsupported` row to the host matrix and name the fallback, such as explicit file loading or explicit invocation. One tested host never proves universal portability.

### 6. Exercise upgrade and uninstall · 第 6 步：演练升级与卸载

在安装时所用的同一个范围里运行：

```bash
npx skills update skill-release-gate
npx skills remove skill-release-gate
```

记录 update 报告的是有变更还是已是最新的包。移除之后，开一个新会话或重新扫描，再重复一次显式调用。宿主应该不再发现 `skill-release-gate`。一个过期的目录条目是值得记录的卸载失败。

> Record whether update reports a change or an already-current bundle. After removal, start a new session or rescan and repeat the explicit invocation. The host should no longer discover `skill-release-gate`. A stale catalog entry is an uninstall failure worth recording.

## Ship It · 交付

本课产出 `skill-release-gate`：一个完整的毕业包（capstone bundle），包含 `SKILL.md`、一份参考文件、一个只读评估脚本、宿主夹具、带标签的触发用例和一份产物契约。在本地克隆内的任意位置解析出仓库根，用安装版或源码版评估器对绝对目标包运行，验证随附的教学夹具——不宣称发布。

面向生产：把每一个夹具替换成捕获值，重建保留的清单，通过独立的发布基础设施取得证明及其可信摘要，然后运行：

```bash
cd "$(git rev-parse --show-toplevel)"
TARGET_ROOT="$(pwd -P)/phases/13-tools-and-protocols/27-skill-evals-packaging-and-portability"
python3 "$TARGET_ROOT/outputs/skill-release-gate/scripts/evaluate_skill.py" \
  --attestation /trusted/release-attestation.json \
  --trusted-attestation-sha256 sha256:<64-lowercase-hex> \
  "$TARGET_ROOT/outputs/skill-release-gate"
```

只有当六层门禁、本地证据完整性和外部信任锚（trust anchor）全部通过时，该命令才会成功退出。没有那个锚，重新贴过标签并在本地重算哈希的夹具仍然不是生产可用。

课程安装器复制完整的包目录树。目录和网站指向它的 `SKILL.md` 入口，同时保留嵌套资源。这正是扁平单文件产物所缺失的那次具体的可移植性测试。

> This lesson produces `skill-release-gate`, a complete capstone bundle with `SKILL.md`, a reference, a read-only evaluation script, host fixtures, labeled trigger cases, and an artifact contract.
> The command exits successfully only when the six-layer gate, local evidence integrity, and external trust anchor all pass. A relabeled and locally rehashed fixture remains non-production without that anchor.
> The course installer copies the complete bundle tree. The catalog and website point to its `SKILL.md` entry while preserving nested resources. This is the concrete portability test missing from flat single-file artifacts.

## Exercises · 练习

1. 为你使用的一个技能编写十个正例、十个明确反例和十个近似命中用例。在修改描述之前先把它们分组。
2. 运行一次五次运行的基线与处理组对比。即使平均改善，也报告每一个任务级的回归。
3. 增加一个需要人类判断的评分维度。先在五个样本上校准，再把它用作门禁。
4. 增加一项宿主能力，并定义支持、适配、降级与不支持四种结果。
5. 在清单创建之后修改一个已安装的引用文件。证明包验证会在激活之前失败。
6. 创建一个正文能过 lint、脚本却违反自身产物契约的技能。指出是哪一层发布检查拦住了它。
7. 增加一个升级评估，对比两个包版本之间的调用策略与必需能力。
8. 发布一份兼容性报告，写明测过的宿主版本、日期、回退与未验证行为，而不使用任何单一的「可移植」徽章。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 它实际的意思 |
|---|---|---|
| Trigger eval | 「技能会不会被触发？」 | 在路由边界上对选择、弃选与混淆的带标签度量 |
| Behavior eval | 「它好不好使？」 | 对照产物、质量、范围与效率契约度量任务执行 |
| Baseline | 「没有技能」 | 比较条件下的相同模型、工具、任务与预算 |
| Artifact contract | 「期望输出」 | 完成所必需的、可独立检查的性质 |
| Capability matrix | 「支持的运行时」 | 按宿主记录原生支持、适配器、降级与不兼容 |
| Release gate | 「所有测试通过」 | 按层设定阈值，拦下包而不掩盖失败类别 |
| Silent degradation | 「元数据被忽略」 | 宿主丢失了必需行为，却不警告安装者或用户 |

## Further Reading · 延伸阅读

- [Evaluating skills](https://agentskills.io/skill-creation/evaluating-skills) —— 触发评估、输出评估、重复运行与基线。
- [Agent Skills best practices](https://agentskills.io/skill-creation/best-practices) —— 连贯的范围与资源架构。
- [Using scripts in skills](https://agentskills.io/skill-creation/using-scripts) —— 确定性辅助脚本与结构化接口。
- [Client implementation guide](https://agentskills.io/client-implementation/adding-skills-support) —— 发现、激活、上下文、信任与生命周期行为。
- [GitSkills: A Dataset of Agent Skills from GitHub](https://arxiv.org/abs/2608.10906) —— 生态规模数据集及其声明的度量局限。
