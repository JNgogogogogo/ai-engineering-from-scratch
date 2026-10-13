# Reuse the policy inside the real ADK path · 在真实 ADK 路径中复用同一套策略

> A login ticket chooses read_account and access-recovery guidance. The fixture specialist replies using that guidance, and the final handoff stores the reply. A request for read_invoice under the access route raises PermissionError before a graph is run. Optional tests inspect model requests to ensure raw email and example keys did not cross the boundary.

**Type:** Build
**Stage:** 4 of 4
**Time:** About 2 hours

## The useful boundary · 有用的边界

在导入或调用框架之前，先把前面几课的成果组合起来。一份已清洗、已路由的工单会拿到一个已授权的只读能力，以及带来源 ID 的人工编写的指引（guidance）。含糊的工单在任何模型调用之前就升级。模型给定的路由无法越过这道闸门。随后，ADK 通过一个真实的 Workflow（含两个 LlmAgent 实例）传递路由和回复。

```figure
pj-support-agent-with-google-adk-4
```

> Compose the earlier lessons before importing or calling the framework. A cleaned, routed ticket receives one authorized read capability and authored guidance with a source ID. Ambiguous tickets escalate before any model call. A supplied model route cannot override this gate. ADK then propagates route and response through a real Workflow with two LlmAgent instances.

## Work the example · 做通示例

一个 login 工单会选中 read_account 和 access-recovery 指引。fixture 专员基于这份指引作答，最终的交接保存这条回复。在 access 路由下请求 read_invoice，会在图运行之前就抛出 PermissionError。可选测试会检查模型请求，确保原始邮箱和示例密钥没有跨过边界。

先写下要返回的字段和预期的副作用次数，再开始写代码。保留一个应当失败的第二个输入，让这个成功示例无法变成硬编码的答案。

> A login ticket chooses read_account and access-recovery guidance. The fixture specialist replies using that guidance, and the final handoff stores the reply. A request for read_invoice under the access route raises PermissionError before a graph is run. Optional tests inspect model requests to ensure raw email and example keys did not cross the boundary.
> Write the returned fields and the expected side-effect count before coding. Keep a second input that should fail so the successful example cannot become a hard-coded answer.

## Build the contract · 构建契约

在你的学习者工作区实现 `prepare_support, support_ticket, export_support in support.py; collect_events, run_adk in adk_adapter.py`。保持导出的名称不变，并继续复用前面阶段的成果，而不是把它们的策略各写一遍。

默认的 ADK 模型是显式注入的确定性 fixture。传入 `--adk --model YOUR_MODEL` 会选用真实的 ADK 提供商，并需要它的凭据。即使是真实模型给出的回复，也仍然是一份需要人工审阅的草稿；一段提示词并不能证明回答有据可依（grounding）。本例中的能力是对本地人工编写知识的一次读取，并不是连接到真实的账务或账户服务。

启动代码提供了 `KNOWLEDGE`：一个以专员为键的原创三记录字典。每个值包含一个稳定的来源 ID 和指引文本：`billing-receipts`、`access-recovery` 或 `platform-status`。把它当作输入数据；你要在它周围实现校验、授权、组合和导出。

`prepare_support` 返回 `ticket`、`session`、`tool` 和 `evidence`。evidence 是 `{"source_id": id, "text": guidance}`。不被支持或打平的路由会得到一个已升级的 session，tool 和 evidence 为 null。显式传入不被允许的工具会抛出 `PermissionError`。`support_ticket` 会加上一个方法标签，并把选定的指引保存为确定性基线的 session 回复。`export_support` 把这个结果写入 support.json，并把转义后的审阅页面写入 index.html。

`collect_events` 接受带 `author`、`text` 和可选 `state_delta` 的字典。要求 author 非空，跳过空文本，返回带 `agent`、`text` 和复制过的 `state_delta` 的行。ADK 结果保留准备好的字段，并添加 `events`、`state`、`handoff_prompt`、`model_requests` 和 `method`。state 保存 route 和 response。对 billing 工单，解析出的专员提示以 `Use the route billing` 开头。记录本地 fixture 请求，让测试能检查确切的脱敏边界。升级会在导入或运行任何模型之前返回空的 events 和 requests。

> Default ADK models are explicitly injected deterministic fixtures. Passing --adk --model YOUR_MODEL selects an actual ADK provider and requires its credentials. Even a live reply remains a draft requiring review; a prompt is not a proof of grounding.
> `prepare_support` returns `ticket`, `session`, `tool` and `evidence`.
> An escalation returns empty events and requests before importing or running a model.

## Hints · 提示

把 events、最终的 session 状态和导出的草稿放在一起检查。与框架无关的测试验证组合逻辑；`--optional` 会运行真实的 ADK 2.10.0 测试。缺少 SDK 记为跳过（skip）；严格模式下的可选评分失败就是失败，不会被解读成「具备框架能力」。

> Inspect events, final session state and the exported draft together. Framework-independent tests validate composition; --optional runs actual ADK 2.10.0 tests. A missing SDK is a skip, and strict optional grading fails rather than implying framework proficiency.

## Verify your work · 验证你的工作

```bash
python3 scripts/project_test.py support-agent-with-google-adk --init my-support-agent-with-google-adk
python3 scripts/project_test.py support-agent-with-google-adk --stage 4 --path my-support-agent-with-google-adk --strict
```

只需初始化一次。累积测试会导入你的工作区，并保留你前面阶段的源码。参考解（reference solution）的一次运行只用于验证教学实现，永远不会授予学习者证书。可选的 SDK 检查需要项目 README 中列出的依赖和命令。

> Initialize once. Cumulative tests import your workspace and preserve your earlier source. A reference-solution run verifies the teaching implementation and never grants a learner certificate. Optional SDK checks require the dependencies and commands in the project README.

## Inspect the result · 检查结果

确定性基线和 ADK 之间共享了哪些数据？为什么必须阻止模型提出的路由悄悄扩大权限？

完成整个项目后会产出一个 HTML 审阅页面和 support.json，其中包含脱敏后的工单、选定的能力（capability）、来源指引、回复或升级（escalation），以及状态历史。

```bash
cd projects/support-agent-with-google-adk/solution
python3 main.py --ticket fixtures/ticket.json --out support-output
```

把 fixture 换成你自己工作流里的一个小输入。把预期结果和观测到的证据放在一起保存，再单独保留一组用例用于评估。提供商请求测试（provider request tests）只能证明序列化和控制流，不能证明模型质量。

> Which data is shared between the deterministic baseline and ADK? Why should a model-proposed route be prevented from silently expanding permissions?
> The completed project produces an HTML review page and support.json with the redacted ticket, selected capability, source guidance, reply or escalation and state history.
> Provider request tests establish serialization and control flow; they do not establish model quality.

## Primary reference · 主要参考

[官方 API 文档](https://google.github.io/adk-docs/)。本项目的实现、策略选择和示例均为原创。

> The implementation, policy choices and examples are original.
