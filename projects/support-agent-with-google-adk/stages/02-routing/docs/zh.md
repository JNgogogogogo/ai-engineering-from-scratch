# Route and authorize as separate decisions · 路由与授权是两个独立决策

> invoice refund selects billing and can use read_invoice. invoice login ties billing and access, so it escalates. A billing route requesting read_account is rejected even though that tool is valid for another specialist.

**Type:** Build
**Stage:** 2 of 4
**Time:** About 2 hours

## The useful boundary · 有用的边界

对 billing、access、platform 三个领域分别统计互不重复的领域词个数。只有当某个领域拿到唯一的正分时才选定路由；未知主题和平局一律交给人工审核（human review）。然后用只读能力白名单（read-capability allowlist）检查选出来的专员（specialist）。一个领域标签永远不会自动授予对所有工具的访问权。

```figure
pj-support-agent-with-google-adk-2
```

> Count distinct domain words for billing, access and platform. Choose a route only when one domain has a unique positive score. Unknown topics and ties go to human review. Then check the selected specialist against a read-capability allowlist. A domain label never grants access to every tool.

## Work the example · 做通示例

invoice refund 选中 billing，可以使用 read_invoice。invoice login 在 billing 和 access 上打平，所以走升级（escalate）。一个 billing 路由去请求 read_account 会被拒绝，哪怕这个工具对另一个专员完全合法。

先写下要返回的字段和预期的副作用次数，再开始写代码。保留一个应当失败的第二个输入，让这个成功示例无法变成硬编码的答案。

> invoice refund selects billing and can use read_invoice. invoice login ties billing and access, so it escalates. A billing route requesting read_account is rejected even though that tool is valid for another specialist.
> Write the returned fields and the expected side-effect count before coding. Keep a second input that should fail so the successful example cannot become a hard-coded answer.

## Build the contract · 构建契约

在你的学习者工作区实现 `route(text), authorize(specialist, tool) in routing.py`。保持导出的名称不变，并继续复用前面阶段的成果，而不是把它们的策略各写一遍。

这个路由器是一个透明的关键词基线（keyword baseline），不是语义模型。能力检查是确定性的，与分类置信度无关。组合起来的工作流会在挑选支持证据或构建智能体图（agent graph）之前先调用它。

启动代码提供了下面这些原创的策略输入。把它们和打分算法分开保存，这样以后修改策略时不需要重写分类器。

| Specialist | Distinct lowercase words | Allowed capability |
| --- | --- | --- |
| billing | invoice, refund, payment | read_invoice |
| access | password, login, account | read_account |
| platform | outage, latency, error | read_status |

`route` 返回一个专员名称或 `human`。`authorize` 返回布尔值；未知的专员或能力一律返回 false。比较时按完整的单词 token 匹配，所以 `payment` 能匹配而 `repayment` 不能。

> The router is a transparent keyword baseline, not a semantic model. The capability check is deterministic and independent of classification confidence. `route` returns one specialist name or `human`. `authorize` returns a boolean; an unknown specialist or capability returns false. Compare whole word tokens, so `payment` matches but `repayment` does not.

## Hints · 提示

用集合（set）来保存单词，这样重复二十次 invoice 也不会主导打分。测试未知的工具名，以及把 human 当作专员的情形。让平局保持显式，而不是按字母顺序随手挑一个。

> Use a set of words so repeating invoice twenty times does not dominate the score. Test unknown tool names and human as a specialist. Keep ties explicit rather than choosing alphabetically.

## Verify your work · 验证你的工作

```bash
python3 scripts/project_test.py support-agent-with-google-adk --init my-support-agent-with-google-adk
python3 scripts/project_test.py support-agent-with-google-adk --stage 2 --path my-support-agent-with-google-adk --strict
```

只需初始化一次。累积测试会导入你的工作区，并保留你前面阶段的源码。参考解（reference solution）的一次运行只用于验证教学实现，永远不会授予学习者证书。可选的 SDK 检查需要项目 README 中列出的依赖和命令。

> Initialize once. Cumulative tests import your workspace and preserve your earlier source. A reference-solution run verifies the teaching implementation and never grants a learner certificate. Optional SDK checks require the dependencies and commands in the project README.

## Inspect the result · 检查结果

为什么即使用模型来给请求打标签，这个授权函数依然不可少？在添加一个写（write）能力之前，你需要先拿到什么样的证据？

完成整个项目后会产出一个 HTML 审阅页面和 support.json，其中包含脱敏后的工单、选定的能力（capability）、来源指引、回复或升级（escalation），以及状态历史。

```bash
cd projects/support-agent-with-google-adk/solution
python3 main.py --ticket fixtures/ticket.json --out support-output
```

把 fixture 换成你自己工作流里的一个小输入。把预期结果和观测到的证据放在一起保存，再单独保留一组用例用于评估。提供商请求测试（provider request tests）只能证明序列化和控制流，不能证明模型质量。

> Why would using a model to label a request still leave this authorization function necessary? What evidence would you need before adding a write capability?
> The completed project produces an HTML review page and support.json with the redacted ticket, selected capability, source guidance, reply or escalation and state history.
> Provider request tests establish serialization and control flow; they do not establish model quality.

## Primary reference · 主要参考

[官方 API 文档](https://google.github.io/adk-docs/)。本项目的实现、策略选择和示例均为原创。

> The implementation, policy choices and examples are original.
