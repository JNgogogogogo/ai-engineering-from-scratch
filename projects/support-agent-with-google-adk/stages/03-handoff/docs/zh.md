# Retain the actual response in the handoff · 在交接中保留真实的回复

> begin followed by classify on invoice then respond with Check the invoice reference produces answered and retains response="Check the invoice reference". The history records classify and respond. Classifying invoice login followed by respond fails; escalate is the valid transition.

**Type:** Build
**Stage:** 3 of 4
**Time:** About 2 hours

## The useful boundary · 有用的边界

把工单建模为依次经过 received（已接收）、routed（已路由），最后到达 answered（已回答）或 escalated（已升级）。在分类之前就产生回复是非法的。路由到人工审核的会话不能自动变成 answered。要返回一个新状态并复制其历史（history），这样失败的操作就不会部分改写调用方已有的状态。

```figure
pj-support-agent-with-google-adk-3
```

> Model the ticket as received, routed, then answered or escalated. A response before classification is invalid. A human route cannot become answered automatically. Return a new state and copy its history so a failed operation does not partially mutate the caller's prior state.

## Work the example · 做通示例

begin 之后对 invoice 做 classify，再用 Check the invoice reference 做 respond，会得到 answered，并保留 response="Check the invoice reference"。历史里记录了 classify 和 respond。对 invoice login 做分类之后再 respond 会失败；escalate 才是合法的转换。

先写下要返回的字段和预期的副作用次数，再开始写代码。保留一个应当失败的第二个输入，让这个成功示例无法变成硬编码的答案。

> begin followed by classify on invoice then respond with Check the invoice reference produces answered and retains response="Check the invoice reference". The history records classify and respond. Classifying invoice login followed by respond fails; escalate is the valid transition.
> Write the returned fields and the expected side-effect count before coding. Keep a second input that should fail so the successful example cannot become a hard-coded answer.

## Build the contract · 构建契约

在你的学习者工作区实现 `begin(ticket), transition(session, event, payload=None) in handoff.py`。保持导出的名称不变，并继续复用前面阶段的成果，而不是把它们的策略各写一遍。

respond 要求文本非空，并把这段文本存入 response。升级会保存 escalation_reason。answered 和 escalated 是终态。导出的 response 必须来自这个状态，因此一次成功执行产出的是一份可用的草稿，而不只是一份转换日志。

`begin` 返回 `ticket_id`、`state="received"`、`route=None` 和一个空的 `history`。每次成功的转换都会把 `{"event": event, "state": next_state}` 追加到一份复制出来的历史里。分类复用阶段 2 来设置 `route`。respond 会去除首尾空白并存下 `response`；升级则存下给定的原因，未给定时存 `Human review required`。非法转换会抛出 `ValueError`，且不改动输入的会话。

> Respond requires nonempty text and stores that text in response. Answered and escalated are terminal states. `begin` returns `ticket_id`, `state="received"`, `route=None` and an empty `history`. Respond trims and stores `response`; escalation stores the supplied reason or `Human review required` when none is given. Invalid transitions raise `ValueError` without changing the input session.

## Hints · 提示

比较一次转换前后的原始状态。断言原状态没有被改动、返回的历史长度恰好加一。然后断言回复文本真的留存了下来，而不是只断言 `state` 等于 answered。

> Compare the original state before and after a transition. Assert that it is unchanged and the returned history grew by one. Then assert that the response text survived, not just that state equals answered.

## Verify your work · 验证你的工作

```bash
python3 scripts/project_test.py support-agent-with-google-adk --init my-support-agent-with-google-adk
python3 scripts/project_test.py support-agent-with-google-adk --stage 3 --path my-support-agent-with-google-adk --strict
```

只需初始化一次。累积测试会导入你的工作区，并保留你前面阶段的源码。参考解（reference solution）的一次运行只用于验证教学实现，永远不会授予学习者证书。可选的 SDK 检查需要项目 README 中列出的依赖和命令。

> Initialize once. Cumulative tests import your workspace and preserve your earlier source. A reference-solution run verifies the teaching implementation and never grants a learner certificate. Optional SDK checks require the dependencies and commands in the project README.

## Inspect the result · 检查结果

进程重启之后，你会保存什么数据来恢复这个状态？留存了一份回答，就能证明它是模型基于已授权的证据生成的吗？

完成整个项目后会产出一个 HTML 审阅页面和 support.json，其中包含脱敏后的工单、选定的能力（capability）、来源指引、回复或升级（escalation），以及状态历史。

```bash
cd projects/support-agent-with-google-adk/solution
python3 main.py --ticket fixtures/ticket.json --out support-output
```

把 fixture 换成你自己工作流里的一个小输入。把预期结果和观测到的证据放在一起保存，再单独保留一组用例用于评估。提供商请求测试（provider request tests）只能证明序列化和控制流，不能证明模型质量。

> What would you store to recover this state after a process restart? Does a retained answer prove that a model generated it from authorized evidence?
> The completed project produces an HTML review page and support.json with the redacted ticket, selected capability, source guidance, reply or escalation and state history.
> Provider request tests establish serialization and control flow; they do not establish model quality.

## Primary reference · 主要参考

[官方 API 文档](https://google.github.io/adk-docs/)。本项目的实现、策略选择和示例均为原创。

> The implementation, policy choices and examples are original.
