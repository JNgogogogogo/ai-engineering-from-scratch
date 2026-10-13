# Validate before starting a session · 会话开始前先校验

> For invoice for sam@example.invalid api_key=EXAMPLE_TOKEN, the usable ticket text becomes invoice for [email] api_key=[redacted]. An empty string fails before routing. The same cleaned text must reach both the baseline and ADK path.

**Type:** Build
**Stage:** 1 of 4
**Time:** About 2 hours

## The useful boundary · 有用的边界

支持请求（support request）是一种外部输入。在创建任何会话之前，先要求 ID 非空、文本长度在 1 到 10,000 个字符之间。把文档中定义的邮箱模式替换成 [email]，把 API 密钥的值替换成 [redacted]。保留工单 ID（ticket ID），这样后续事件可以引用它，而不必保留原始联系方式。

```figure
pj-support-agent-with-google-adk-1
```

> A support request is an external input. Require a nonempty ID and 1 to 10,000 characters of text before creating any session. Replace the documented email pattern with [email] and API-key values with [redacted]. Keep the ticket ID so later events can refer to it without retaining raw contact details.

## Work the example · 做通示例

对于 invoice for sam@example.invalid api_key=EXAMPLE_TOKEN 这样的输入，可用的工单文本会变成 invoice for [email] api_key=[redacted]。空字符串会在路由之前就直接失败。同一份清洗后的文本必须同时到达基线路径和 ADK 路径。

先写下要返回的字段和预期的副作用次数，再开始写代码。保留一个应当失败的第二个输入，让这个成功示例无法变成硬编码的答案。

> For invoice for sam@example.invalid api_key=EXAMPLE_TOKEN, the usable ticket text becomes invoice for [email] api_key=[redacted]. An empty string fails before routing. The same cleaned text must reach both the baseline and ADK path.
> Write the returned fields and the expected side-effect count before coding. Keep a second input that should fail so the successful example cannot become a hard-coded answer.

## Build the contract · 构建契约

在你的学习者工作区实现 `ticket(raw) in intake.py`。保持导出的名称不变，并继续复用前面阶段的成果，而不是把它们的策略各写一遍。

这些正则表达式只覆盖上面声明的模式。它们并不能证明任意的个人数据、密码或每一种凭据格式都已被移除。不要让原始文本进入模型请求和导出的报告，并在最终的集成边界上测试这些已知模式。

> Implement `ticket(raw) in intake.py` in your learner workspace. Preserve the exported names and continue using earlier stages rather than duplicating their policies.
> The regexes cover only the stated patterns. They do not establish that arbitrary personal data, passwords or every credential format has been removed. Keep raw text out of model requests and exported reports, and test the known patterns at the final integration boundary.

## Hints · 提示

沿着「原始输入 → 返回的字典」追踪值的流向。把邮箱和密钥放进同一个输入里一起测试，而不是只分开测。报告校验错误时不要记录原始输入。

> Trace the value from raw input through the returned dictionary. Test an email and key together, not only separately. Do not log raw input when reporting a validation error.

## Verify your work · 验证你的工作

```bash
python3 scripts/project_test.py support-agent-with-google-adk --init my-support-agent-with-google-adk
python3 scripts/project_test.py support-agent-with-google-adk --stage 1 --path my-support-agent-with-google-adk --strict
```

只需初始化一次。累积测试会导入你的工作区，并保留你前面阶段的源码。参考解（reference solution）的一次运行只用于验证教学实现，永远不会授予学习者证书。可选的 SDK 检查需要项目 README 中列出的依赖和命令。

> Initialize once. Cumulative tests import your workspace and preserve your earlier source. A reference-solution run verifies the teaching implementation and never grants a learner certificate. Optional SDK checks require the dependencies and commands in the project README.

## Inspect the result · 检查结果

经过这两次替换之后，一份真实工单里还有哪些部分是敏感的？生产级的数据最小化（data-minimization）策略应该放在哪里？

完成整个项目后会产出一个 HTML 审阅页面和 support.json，其中包含脱敏后的工单、选定的能力（capability）、来源指引、回复或升级（escalation），以及状态历史。

```bash
cd projects/support-agent-with-google-adk/solution
python3 main.py --ticket fixtures/ticket.json --out support-output
```

把 fixture 换成你自己工作流里的一个小输入。把预期结果和观测到的证据放在一起保存，再单独保留一组用例用于评估。提供商请求测试（provider request tests）只能证明序列化和控制流，不能证明模型质量。

> Which parts of a real ticket remain sensitive after these two substitutions? Where would a production data-minimization policy belong?
> The completed project produces an HTML review page and support.json with the redacted ticket, selected capability, source guidance, reply or escalation and state history.
> Provider request tests establish serialization and control flow; they do not establish model quality.

## Primary reference · 主要参考

[官方 API 文档](https://google.github.io/adk-docs/)。本项目的实现、策略选择和示例均为原创。

> The implementation, policy choices and examples are original.
