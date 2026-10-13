# Create an unsent draft with a source quote · 生成带来源引用的未发送草稿

> Generate reviewable email drafts without inventing commitments.

**Type:** Build  
**Language:** Python  
**Stage:** 3 of 4  
**Time:** About 2 hours

## What you are building · 你在构建什么

分类结果不会告诉你回复应该承诺什么。离线草稿会引用源文的第一行，然后留出一个标记清晰的位置给你的回复。使用 EmailMessage 来序列化消息头和换行。不要用字符串拼接手工组装原始消息头。

```figure
pj-inbox-triage-desk-3
```

> A classification does not tell you what the reply should promise. The offline draft quotes the first source line, then leaves a clearly marked place for your response. Use EmailMessage to serialize headers and line endings. Do not assemble raw headers by string concatenation.

## Work through an example · 走一个例子

发件人问 Could you lend two chairs? 时，草稿指向那句话，并包含 [Write and check your response here.]。它不会声称椅子有空。X-Unsent: 1 标识「草稿」工作流；本项目没有任何 SMTP 调用。

编码之前，先写下这个例子的返回字段，以及一个应该失败的输入。把期望结果放在实现旁边，这样你才能区分「契约变了」和「出了 bug」。

> For a sender asking Could you lend two chairs?, the draft points to that sentence and contains [Write and check your response here.]. It does not say that chairs are available. X-Unsent: 1 identifies the intended draft workflow; the project has no SMTP call.
> Before coding, write down the returned fields for that example and one input that should fail. Keep the expected result beside your implementation so you can distinguish a contract change from a bug.

## Implement the contract · 实现契约

- `build_draft(message: dict, decision: dict) -> dict`
- `provider_proposal(message, endpoint, model, api_key="") -> dict`

校验 decision 确实属于该消息，并且每个提供的证据 span 都能匹配上。返回 message_id、to、subject、body、eml、status=draft-only 和 source_quote。添加 In-Reply-To 和去重后的 References。可选的 HTTP 分类器必须拒绝不支持的类别、空引文，以及正文中不存在的引文。它返回 review_required=True。远程 endpoint 必须使用 HTTPS。仅当目标是 localhost 或显式的回环 IP 地址（IPv4 或 IPv6）、且主机名与端口有效时才允许 HTTP。拒绝 URL 凭据、片段（fragment）和空白。使用一个专用的 urllib opener，让它的 HTTPRedirectHandler.redirect_request 返回 None，使所有重定向在第二次请求转发凭据之前就失败。

保持早前阶段可用。在学习者工作区里实现这些函数；做例子期间让参考实现保持关闭。

> Check that the decision belongs to the message and every supplied evidence span matches. ... Return message_id, to, subject, body, eml, status=draft-only and source_quote. ... Add In-Reply-To and deduplicated References. ... The optional HTTP classifier must reject unsupported categories, empty quotes and quotes absent from the body. ... Require HTTPS for remote endpoints. ... Use a dedicated urllib opener whose HTTPRedirectHandler.redirect_request returns None, so all redirects fail before a second request can forward credentials.
> Keep earlier stages working. Implement these functions in your learner workspace, leaving the reference solution closed while you work through the example.

## Hints and failure cases · 提示与失败场景

用 BytesParser 把你生成的 .eml 再解析一遍，检查收件人和线程相关的消息头。对适配器，把序列化后的请求对着本地服务器或 mock 的 transport 来测试；离线测试并不能证明线上模型质量。

> Parse your generated .eml again with BytesParser and inspect the recipient and thread headers. For the adapter, test the serialized request against a local server or a mocked transport; an offline test does not establish live model quality.

## Run your stage · 运行本阶段

从仓库根目录初始化一次，然后运行累积测试：

```bash
python3 scripts/project_test.py inbox-triage-desk --init my-inbox-triage-desk
python3 scripts/project_test.py inbox-triage-desk --stage 3 --path my-inbox-triage-desk
```

起步代码会故意抛出一个实现错误。之后的初始化会保留你的源码，而不是替换它。通过的条件是每个被选中的测试都运行了；被跳过的测试不算完成证据。

> Initialize once from the repository root, then run the cumulative tests:
> The starter deliberately raises an implementation error. Later initialization preserves your source rather than replacing it. A passing result requires every selected test to run; a skipped test is not completion evidence.

## Check your reasoning · 检查你的推理

为什么一条有据可查的引文不足以验证模型选出的类别？如果要在保留人工审阅的同时起草更有用的回复，你会改动哪个组件？

> Why is a grounded quote insufficient to verify a model's chosen category? Which component would you change to draft more useful replies while preserving review?

## Connect it to the finished artifact · 连接到最终成品

一个 HTML 审阅台、triage.json，以及可下载的未发送 .eml 草稿。默认分类器使用显式短语规则，而不是 LLM。它处理一个导出消息的文件夹，从不连接你的邮箱，也从不发送回复。日期、紧急程度和承诺的动作都不做推断。

项目完成后，用自己的输入试一试：

```bash
cd my-inbox-triage-desk
python3 main.py --input ./fixtures --out ./inbox-output
```

在你自己标注的 held-out 集合上，把模型提案与你的短语基线做比较。报告不一致之处；不要把每个模型输出都称为改进。

> An HTML review desk, triage.json, and downloadable unsent .eml drafts. The default classifier uses explicit phrase rules, not an LLM. It handles a folder of exported messages and never connects to your mailbox or sends replies. Dates, urgency and promised actions are not inferred.
> After completing the project, try your own inputs:
> Compare model proposals with your phrase baseline on a held-out set you label yourself. Report disagreements; do not call every model output an improvement.

## Primary reference · 主要参考

[官方 API 文档](https://docs.python.org/3/library/email.parser.html)。实现、示例与 fixtures 均为原创。该参考解释底层 API；项目特有的策略已在上面写明。

> [Official API documentation](https://docs.python.org/3/library/email.parser.html). The implementation, examples and fixtures are original. The reference explains the underlying API; the project-specific policies are stated above.
