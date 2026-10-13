# MCP Registry Supply Chain: Admission, Drift, and Rollback · MCP 注册表供应链：准入、漂移与回滚

> 注册表条目告诉你发布者声明了什么。生产准入（admission）证明的是：你拉取了什么、观察到了什么、批准了什么，以及你能安全恢复到什么。
>
> A registry entry tells you what a publisher declared. Production admission proves what you fetched, what you observed, what you approved, and what you can safely restore.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 13 · 17 (gateways and registries), Phase 13 · 18 (production authentication)
**Time:** ~90 minutes

## Learning Objectives · 学习目标

- 把注册表发布（publication）、包来源（provenance）、运行时发现与本地审批区分开
- 不信任记录自带的名字，去验证 MCP 服务器的命名空间（namespace）
- 固定（pin）不可变的发布、执行来源、来源证明与在线描述符（descriptor）证据
- 在准入之后检测注册表状态变化与运行时漂移（drift）
- 不改写历史，把路由回滚（rollback）到先前已准入的版本
- 维护一个防篡改（tamper-evident）、能解释每个决策的准入账本（ledger）

> Separate Registry publication, package provenance, runtime discovery, and local approval.
> Verify an MCP server namespace without trusting the name inside its own record.
> Pin immutable publication, execution-source, provenance, and live descriptor evidence.
> Detect registry status changes and runtime drift after admission.
> Roll back routing to a previously admitted version without rewriting history.
> Maintain a tamper-evident admission ledger that explains every decision.

## The Problem · 问题在哪

你在注册表里发现了 `com.example/inventory`。它的描述看起来没问题。它的包存在。服务器对 `server/discover` 有响应。

这不是一个事实，而是一条来自不同权威的事实链：

1. 一个对命名空间完成过认证的发布者提交了这条记录。
2. 一个包注册表交付了一个具有特定身份与摘要（digest）的制品（artifact）。
3. 一个运行中的端点报告了协议版本、能力（capabilities）、工具和诊断性服务器信息。
4. 你的组织决定允许这一个确切的组合。

把这些事实压缩成「它在注册表里，所以信它」会制造供应链（supply chain）盲区。一次合法的发布仍然可能被弃用（deprecated）。如果你不固定摘要，包标签可能指向一个意料之外的制品。服务器可能在评审之后添加一个破坏性工具。一次回滚可能悄悄选中一个从未被准入的版本。

解法是一个在每条边界都拿证据说话的准入控制器。

> You find `com.example/inventory` in a registry. Its description looks right. Its package exists. The server answers `server/discover`. ... That is not one fact. It is a chain of facts from different authorities ... Collapsing those facts into “it is in the registry, so trust it” creates a supply chain blind spot. ... The fix is an admission controller with evidence at every boundary.

## The Registry Is an Index, Not Your Approval System · 注册表是索引，不是你的审批系统

官方 MCP Registry 存储服务器元数据。它的 `server.json` 记录命名一个服务器版本，并声明一个或多个包或远程端点。发布规则增加了命名空间认证、包所有权检查、受限注册表规则，以及一个狭窄的发布者元数据存放位置。

这些控制回答的是发布问题。你的生产策略仍然要回答部署问题：

| 边界 | 问题 | 证据所有者 |
|---|---|---|
| 命名空间 | 发布者被允许使用这个名字吗？ | 注册表认证加上你验证过的命名空间输入 |
| 记录 | 发布者为这个版本声明了什么？ | 不可变的 `server.json` 摘要 |
| 执行来源 | 将由哪个包或远程端点执行？ | 声明的来源字段、经验证的所有权结果、传输与可信摘要 |
| 运行时 | 端点现在暴露了什么？ | `server/discover` 与工具描述符 |
| 准入 | 你的策略批准的是不是正好这一组？ | 本地 pin 与账本条目 |
| 运维 | 它还安全吗？有什么能替换它？ | 漂移检查、状态同步、健康与回滚路线 |

Registry 的 schema 版本与 MCP 协议版本相互独立。一条记录可以使用已发布的 `2025-12-11` server schema，而在线服务器支持 MCP `2026-07-28`。绝不要从一个推断另一个。

```figure
mcp-registry-admission
```

> The official MCP Registry stores server metadata. Its `server.json` record names a server version and declares one or more packages or remote endpoints. ... Those controls answer publication questions. Your production policy still answers deployment questions ... The Registry schema version and the MCP protocol version are independent. ... Never infer one from the other.

## Seven Controls in One Admission Decision · 一次准入决策中的七项控制

### 1. Namespace verification · 1. 命名空间验证

官方 Registry 的名字使用经过认证的命名空间。一个已验证的域名可以映射出一个反域名前缀。例如，控制 `example.com` 可以确立 `com.example/*`。

不要接受字符串前缀检查：

```python
server_name.startswith("com.example")
```

那样也会接受 `com.exampleevil/tool`。在 `/` 处拆开名字，要求 slug 非空，并精确比较命名空间段。更重要的是：把验证过的命名空间从认证结果传入准入。不要从不可信的记录里推导信任。

基于 GitHub 的命名空间与基于域名的命名空间走不同的认证路径。无论哪条路径，都归一成一个准入输入：精确的已验证命名空间字符串。

> Official Registry names use authenticated namespaces. A verified domain can map to a reversed domain prefix. ... Do not accept a string prefix check ... That also accepts `com.exampleevil/tool`. Split the name at `/`, require a non-empty slug, and compare the namespace segment exactly. More importantly, pass the verified namespace into admission from the authentication result. Do not derive trust from the untrusted record.

### 2. Provenance join · 2. 来源拼接

对包记录来说，声明与拉取到的制品必须在显式字段上拼接（join）：

- 包注册表类型
- 包标识符
- 包版本
- 已验证的所有权结果
- 下载制品的摘要

还要验证声明的包传输方式。只有远程端点、没有包的记录是合法的，不能因为它缺包而拒绝。对远程来源，把声明的 URL 与传输类型，拼接到你独立验证的端点所有权以及可信连接或部署证据的摘要上。

本课代码同时支持两种来源类型，并把选中的来源与 Registry 来源、服务器名、Registry 版本、记录摘要和证据摘要一起哈希。得到的来源摘要（provenance digest）是指向完整证据集的紧凑指针。它不能替代保留证据本身。

绝不要接受只由你正试图验证的那个制品提供的摘要。要么在可信的拉取边界计算它，要么从一个包服务接收它——并且你要验证那个服务的校验结果。

> For a package record, the declaration and fetched artifact must join on explicit fields ... Never accept a digest supplied only by the artifact you are trying to verify. Calculate it at a trusted fetch boundary, or receive it from a package service whose verification result you validate.

### 3. Pin the decision, not only the version · 3. 固定的是决策，不只是版本

Registry 版本是唯一的发布标识符。已发布的元数据不可变。改动记录就需要新版本。推荐语义化版本（semantic versioning），但 Registry 既不强制，也不接受版本范围。

这意味着 `^1.4` 不是准入 pin。「latest」也不是。有用的 pin 包含：

```json
{
  "server": "com.example/inventory",
  "version": "1.0.0",
  "recordDigest": "...",
  "source": {"kind": "package", "registryType": "pypi"},
  "sourceDigest": "...",
  "toolsetDigest": "...",
  "provenanceDigest": "...",
  "registryStatus": "active"
}
```

固定多层让你能定位是哪条边界变了。同一 Registry 版本下记录摘要变了 → Registry 完整性故障。同一包坐标或远程部署下来源摘要变了 → 执行来源完整性故障。工具集摘要变了 → 运行时漂移。

> Registry versions are unique publication identifiers. Published metadata is immutable. A changed record requires a new version. Semantic versioning is recommended, but the Registry does not require it and does not accept version ranges. ... This means `^1.4` is not an admission pin. Neither is “latest.” ... Pinning several layers lets you identify which boundary changed. A record digest change under the same Registry version is a Registry integrity failure.

### 4. Live drift detection · 4. 在线漂移检测

准入应当观察那个真正会接流量的服务器。调用 `server/discover`，通过你的可信路径列出或以其他方式获得暴露的工具描述符，并验证：

- `2026-07-28` 在 `supportedVersions` 里
- 本地要求的全部能力都在
- 每个工具描述符都有要求的身份与 schema 表面
- 后续检查时，归一化的描述符摘要与已准入的 pin 一致

可选结果 `_meta["io.modelcontextprotocol/serverInfo"]` 的值是自报的展示、日志与调试上下文。把它记录为诊断证据，但绝不要用它去确立命名空间、包所有权、端点所有权、准入或任何其他安全决策。`_meta` 之外的直接 `serverInfo` 别名不是契约字段，也不应被提升为诊断证据。

只归一化那些顺序无意义的字段。示例在哈希前按稳定名字排序工具列表，所以无害的列表顺序变化不会触发漂移。它不丢弃描述符字段。新工具、schema 变化、描述变化或新注解都会改变 pin。

示例把畸形描述符和任何描述符摘要变化都当作漂移处理：隔离（quarantine）该 pin、摘掉它的活跃路由，并把该版本挡在回滚目标之外。生产策略可以允许编辑性修改，但只能通过一次新的评审，因为描述会影响模型的工具选择。「装饰性」元数据能改变智能体行为。

> Admission should observe the server that will actually receive traffic. ... The optional result `_meta["io.modelcontextprotocol/serverInfo"]` value is self-reported display, log, and debugging context. Record it as diagnostic evidence, but never use it to establish namespace, package ownership, endpoint ownership, admission, or any other security decision. ... Normalize only fields whose order has no meaning. ... A production policy may allow an editorial change only through a new review, because descriptions influence model tool selection. “Cosmetic” metadata can alter agent behavior.

### 5. Registry status is live state · 5. 注册表状态是实时状态

Registry API 在每条服务器记录旁边附加一个响应级 `_meta` 对象。Registry 管理的字段位于 `_meta["io.modelcontextprotocol.registry/official"]` 之下。把响应的 `_meta` 对象传入准入，并读取 `_meta["io.modelcontextprotocol.registry/official"].status`。直接的 `_meta.status` 值不是官方线上形状。不要把响应元数据与发布记录自己的 `_meta` 混为一谈。状态可以是：

- `active`：默认返回，有资格进入本地准入
- `deprecated`：仍可发现但带警告，不再是安全的自动选择
- `deleted`：默认隐藏，其历史记录仍可通过 deleted 或增量视图获得

准入之后要同步状态。如果一个活跃版本变成 deprecated 或 deleted，隔离它的 pin，停止把新工作路由过去。保留证据。从默认列表里删除，不是授权你抹掉审计轨迹。

发布者提供的自定义元数据只属于发布记录里的 `_meta.io.modelcontextprotocol.registry/publisher-provided`。Registry 管理的响应元数据是另一回事。不要让发布者设定自己的官方状态。

> The Registry API attaches a response-level `_meta` object beside each server record. Registry-managed fields live under `_meta["io.modelcontextprotocol.registry/official"]`. ... Sync status after admission. If an active version becomes deprecated or deleted, quarantine its pin and stop routing new work to it. Keep the evidence. Deletion from the default listing is not permission to erase your audit trail. ... Do not let a publisher set its own official status.

### 6. Rollback means route restoration · 6. 回滚意味着恢复路由

回滚不编辑不可变的发布。回滚选中一个先前已准入、当前仍合格的 pin，然后切换活跃路由。

安全目标必须：

1. 有已完成的准入记录。
2. 在你的策略下 Registry 状态仍是 active。
3. 未被运行时或安全证据隔离。
4. 仍能解析到固定的包与在线描述符集。
5. 通过当前健康检查。

示例聚焦前三个条件。真正的调和器（reconciler）应当在激活前重新拉取包并重新检查在线端点。

> An immutable publication is not edited during rollback. Rollback selects a previously admitted, currently eligible pin and changes the active route. ... The sample focuses on the first three conditions. A real reconciler should re-fetch the package and re-check the live endpoint before activation.

### 7. Append an admission ledger · 7. 追加准入账本

准入数据库说明什么在活跃。账本解释为什么。

示例的每个条目包含序号、时间、事件、服务器、版本、结果、原因、证据、前一条目的哈希以及它自己的哈希。改动一个较旧的结果，会破坏该条目以及其后每个链环的验证。

这是防篡改（tamper-evident），不是魔法般的防篡改（tamper-proof）。把周期性的账本头（ledger head）锚定在一个单独的信任域，例如签名的发布元数据或一次性写入存储。限制谁能追加。把授权令牌、包凭据、工具参数和私有端点数据挡在证据之外。

> An admission database says what is active. A ledger explains why. ... Changing an older outcome breaks verification of that entry and every later link. ... This is tamper-evident, not magically tamper-proof. Anchor periodic ledger heads in a separate trust domain, such as signed release metadata or write-once storage. ... Keep authorization tokens, package credentials, tool arguments, and private endpoint data out of evidence.

## Build It · 动手造

可运行的控制器在 `code/main.py`。它只用 Python 标准库。

先跑有限的演示：

```bash
cd phases/13-tools-and-protocols/30-mcp-registry-supply-chain-and-drift
python3 code/main.py
```

演示执行五个操作：

1. 在命名空间、包来源、协议、能力和工具全部匹配的情况下准入 `1.0.0`。
2. 准入 `1.1.0` 并把它设为活跃。
3. 在运行时观察到一个意料之外的 delete 工具。
4. 观察到 `1.1.0` 的 Registry 状态变成 `deprecated`。
5. 把路由恢复到仍然有效准入的 `1.0.0` pin。

预期形状：

```json
{
  "admitted": [true, true],
  "driftAllowed": false,
  "rollbackAllowed": true,
  "activeVersion": "1.0.0",
  "ledgerValid": true
}
```

按这个顺序读实现：

1. `namespace_for_domain()` 和 `namespace_matches()` 确立精确的命名权威。
2. `digest()` 和 `normalized_tools()` 产出确定性证据。
3. `RegistryAdmissionController.admit()` 把发布、来源、运行时和策略拼接起来。
4. `check_live()` 把一次新观察与 pin 对比。
5. `observe_registry_status()` 隔离 Registry 状态发生变化的版本。
6. `rollback()` 只激活先前准入过的合格目标。
7. `AdmissionLedger.verify()` 检测对已记录历史的改动。

> The runnable controller is in `code/main.py`. It uses only the Python standard library. ... The demonstration performs five operations ... Read the implementation in this order ... `AdmissionLedger.verify()` detects changes to recorded history.

## Use It · 实战用法

把控制器放在发现与路由之间：

```text
Registry sync -> artifact verifier -> live discovery -> admission controller -> route table
                                               |                 |
                                               v                 v
                                          evidence store    admission ledger
```

这些职能使用相互独立的身份。Registry 同步 worker 需要元数据读权限。制品验证器需要包拉取权限。路由调和器需要激活已批准 pin 的权限。谁也不需要全部凭据。

把发布状态显式化。「Approved（已批准）」指证据通过了策略。「Active（活跃）」指路由当前选中它。「Quarantined（已隔离）」指它不能接收新工作。「Superseded（已被取代）」指另一个已准入版本在活跃。不要把这四种含义编码进一个布尔值。

在把服务器暴露进 `tools/list` 之前先跑准入。否则客户端可能在发布与策略评估之间的空档里发现一个工具。

> Put the controller between discovery and routing ... Use separate identities for these jobs. ... Make rollout state explicit. ... Do not encode all four meanings in one Boolean. ... Run admission before exposing a server in `tools/list`. Otherwise a client can discover a tool during the gap between publication and policy evaluation.

## Interactive Lab · 交互实验

你将一次观察一条边界失效。

### Lab A: namespace collision · 实验 A：命名空间碰撞

从 code 目录打开一个 Python shell：

```bash
cd phases/13-tools-and-protocols/30-mcp-registry-supply-chain-and-drift/code
python3 -q
```

然后运行：

```python
from main import namespace_matches
namespace_matches("com.example/inventory", "com.example")
namespace_matches("com.exampleevil/inventory", "com.example")
```

第一个结果是 `True`；第二个是 `False`。在本地把精确比较换成 `startswith`，观察为什么第二个名字越过了边界。继续之前恢复精确比较。

> The first result is `True`; the second is `False`. Replace the exact comparison with `startswith` locally and observe why the second name crosses the boundary. Restore the exact comparison before continuing.

### Lab B: descriptor drift · 实验 B：描述符漂移

```python
from main import *
times = iter(f"2026-08-21T12:00:{n:02d}+00:00" for n in range(10))
c = RegistryAdmissionController(clock=lambda: next(times))
meta = {OFFICIAL_META_KEY: {"status": "active"}}
c.admit(sample_record("1.0.0"), meta, "com.example", evidence_for("1.0.0"), sample_live("1.0.0"))
c.check_live("com.example/inventory", "1.0.0", sample_live("1.0.0", True))
```

检查 reasons 与路由状态。包和 Registry 记录都没变。运行时工具表面变了，于是控制器隔离并停用了该 pin。这就是为什么供应链控制必须在安装之后继续。

> Inspect the reasons and route state. The package and Registry record did not change. The runtime tool surface did, so the controller quarantined and deactivated the pin. This is why supply chain control must continue after installation.

### Lab C: status and rollback · 实验 C：状态与回滚

准入 `1.1.0`，把它标记为 deprecated，然后尝试两个回滚目标：

```python
c.admit(sample_record("1.1.0"), meta, "com.example", evidence_for("1.1.0"), sample_live("1.1.0"))
c.observe_registry_status("com.example/inventory", "1.1.0", "deprecated")
c.rollback("com.example/inventory", "1.1.0", "unsafe retry")
c.rollback("com.example/inventory", "1.0.0", "restore known release")
c.ledger.verify()
```

被隔离的目标被拒绝。更早的活跃 pin 被接受。账本保持有效。

> Admit `1.1.0`, mark it deprecated, and try both rollback targets ... The quarantined target is rejected. The earlier active pin is accepted. The ledger remains valid.

## Practice Lab · 练习实验

给控制器加一道双人审批闸门。

要求：

- 把审批存成签名的证据引用（evidence reference），不是 pin 里可被改动的名字。
- 对包含 `destructiveHint: true` 工具的工具集，要求两个不同的评审者身份。
- 拒绝重复的评审者身份。
- 审批未完成时，把原始准入尝试保留在账本里。
- 为零个、一个、重复、两个不同审批各加测试。
- 不要记录签名、凭据或完整的私有工具参数。

成功的含义：直到两个身份都批准了确切的记录、包和工具集摘要，破坏性工具才能变活跃。

> Extend the controller with a two-person approval gate. ... Success means a destructive tool cannot become active until both identities approved the exact record, package, and toolset digests.

## Shipped Artifact · 交付物

本课交付 `outputs/skill-mcp-registry-admission.md`。在评审一个新 Registry 版本或调查漂移时，把它当作扁平、可复用的操作手册（runbook）。它定义了输入、拒绝规则、证据包、状态调和与回滚证明，不依赖示例类名。

> This lesson ships `outputs/skill-mcp-registry-admission.md`. Use it as a flat, reusable runbook when reviewing a new Registry version or investigating drift. It defines the inputs, refusal rules, evidence bundle, status reconciliation, and rollback proof without depending on the sample class names.

## Verify It · 验收

运行演示与确定性测试套件：

```bash
cd phases/13-tools-and-protocols/30-mcp-registry-supply-chain-and-drift
python3 code/main.py
python3 -m unittest discover -s code/tests -v
```

验证应当证明：

- 精确的命名空间边界拒绝形似前缀
- 只有官方带命名空间的 Registry 状态能让一个版本合格
- 未验证或不匹配的包与远程证据被拒绝
- 发布者元数据不能冒充 Registry 管理的元数据
- 工具排序被归一化而不掩盖描述符变化
- 畸形的包与工具结构被安全拒绝
- `serverInfo` 始终只是诊断，绝不提供准入授权
- 描述符漂移触发隔离、停用，并阻止回滚到该 pin
- 状态变化隔离活跃 pin
- 回滚不能选中被隔离或未知的版本
- 账本篡改会被发现

> exact namespace boundaries reject lookalike prefixes ... unverified or mismatched package and remote evidence is rejected ... descriptor drift quarantines, deactivates, and blocks rollback to the pin ... rollback cannot select a quarantined or unknown version ... ledger tampering is detected

## Production Failure Modes · 生产故障模式

| 故障 | 为什么发生 | 必需的响应 |
|---|---|---|
| 名字看起来合法但命名空间从未被认证 | 策略相信了记录文本 | 在可信的命名空间验证器给出精确前缀之前拒绝 |
| 同一包坐标返回了新字节 | 上游可变或分发被攻破 | 停止激活，保留两个摘要，调查拉取边界 |
| 「latest」未经评审就变了 | 浮动选择逃出了 pin | 只解析确切已准入的版本与摘要 |
| 审批之后出现新工具 | 运行时漂移或另一个部署 | 隔离路由并捕获一份新的描述符观察 |
| 已弃用版本仍然活跃 | 状态同步缺失或延迟 | 按计划并在激活前调和状态 |
| 已删除记录从默认同步中消失 | 客户端只请求了活跃记录 | 使用增量或感知删除的调和，并保留本地历史 |
| 回滚目标从未被准入 | 路由控制与审批状态脱节 | 拒绝回滚，为该目标执行一次新的准入 |
| 攻击者改写全部条目后账本本地仍验证通过 | 哈希链没有外部锚 | 把签名账本头发布到单独的信任域 |
| 证据里包含 bearer 令牌或工具参数 | 日志整份复制了请求 | 采集时脱敏，只存最小证明 |

> Same package coordinate returns new bytes | Mutable upstream or compromised distribution | Stop activation, retain both digests, investigate the fetch boundary ... Rollback target was never admitted | Route control and approval state are disconnected | Refuse rollback and run a new admission for the target ... Ledger verifies locally after an attacker rewrites all entries | Hash chain has no external anchor | Publish signed ledger heads to a separate trust domain

## Operational Rule · 运营规则

发布回答的是「这个身份能发布这个名字吗？」。准入回答的是「我们会执行这个确切的制品、并暴露这个确切的行为吗？」。把这两个决策分开，固定每一条拼接，让回滚依据证据而不是记忆来选择。

> Publication answers “can this identity publish this name?”. Admission answers “will we execute this exact artifact and expose this exact behavior?”. Keep those decisions separate, pin every join, and make rollback choose evidence rather than memory.

## Further Reading · 延伸阅读

- [Official Registry server.json requirements](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/official-registry-requirements.md)
- [Official Registry OpenAPI contract](https://registry.modelcontextprotocol.io/openapi.yaml)
- [MCP 2026-07-28 server discovery](https://modelcontextprotocol.io/specification/2026-07-28/server/discover)
