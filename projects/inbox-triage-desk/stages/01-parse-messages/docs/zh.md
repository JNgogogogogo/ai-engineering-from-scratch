# Read MIME without losing message identity · 读取 MIME 而不丢失消息身份

> Parse exported messages and preserve their exact plain-text evidence.

**Type:** Build  
**Language:** Python  
**Stage:** 1 of 4  
**Time:** About 2 hours

## What you are building · 你在构建什么

电子邮件是一条结构化消息，不是「在第一个空行处切开」得到的正文。MIME 可以包含多个候选版本（alternative）、附件和传输编码。使用带显式 policy 的 `BytesParser`，然后选出纯文本正文。把发件人、主题、消息 ID、引用 ID 和正文状态放在正文旁边。

```figure
pj-inbox-triage-desk-1
```

> An email is a structured message, not a body obtained by splitting at the first blank line. MIME can contain multiple alternatives, attachments and transfer encodings. Use BytesParser with an explicit policy, then select the plain-text body. Keep the sender, subject, message ID, reference IDs and body status beside the text.

## Work through an example · 走一个例子

一封 From: Ada <ada@example.invalid>、Message-ID: <a@example.invalid>、正文为 Please reserve a chair 的消息，会得到发件人 ada@example.invalid 和一字不差的正文文本。第二个 HTML 候选版本不得替换这段文本。如果缺少 Message-ID，就对原始字节取摘要，作为稳定的本地身份。

编码之前，先写下这个例子的返回字段，以及一个应该失败的输入。把期望结果放在实现旁边，这样你才能区分「契约变了」和「出了 bug」。

> A message with From: Ada <ada@example.invalid>, Message-ID: <a@example.invalid>, and the body Please reserve a chair produces sender ada@example.invalid and the exact body text. A second HTML alternative must not replace that text. If Message-ID is absent, a digest of the original bytes supplies stable local identity.
> Before coding, write down the returned fields for that example and one input that should fail. Keep the expected result beside your implementation so you can distinguish a contract change from a bug.

## Implement the contract · 实现契约

- `parse_message(raw: bytes) -> dict`

返回键 id、sender、subject、text、references 和 body_status。拒绝空输入、超过 1,000,000 字节的输入，以及缺少发件人地址的输入。折叠 subject 中的空白，但保留正文的换行。对引用 ID 去重。只有 HTML 的正文会得到空 text 和 no-plain-body 状态。

保持早前阶段可用。在学习者工作区里实现这些函数；做例子期间让参考实现保持关闭。

> Return keys id, sender, subject, text, references and body_status. Reject empty input, input larger than 1,000,000 bytes, and missing sender addresses. Collapse whitespace in the subject but preserve body line breaks. Deduplicate reference IDs. An HTML-only body becomes empty text with no-plain-body status.
> Keep earlier stages working. Implement these functions in your learner workspace, leaving the reference solution closed while you work through the example.

## Hints and failure cases · 提示与失败场景

从一封纯文本消息开始，然后构造 multipart/alternative。优先使用解析器的 get_body，而不要遍历每一个文本部分：附带（attach）的文本文件并不是邮件正文。把同样的字节解析两次，测试回退 ID。

> Start with one plain message, then construct multipart/alternative. Prefer the parser's get_body over traversing every text part: an attached text file is not the email body. Test fallback IDs by parsing the same bytes twice.

## Run your stage · 运行本阶段

从仓库根目录初始化一次，然后运行累积测试：

```bash
python3 scripts/project_test.py inbox-triage-desk --init my-inbox-triage-desk
python3 scripts/project_test.py inbox-triage-desk --stage 1 --path my-inbox-triage-desk
```

起步代码会故意抛出一个实现错误。之后的初始化会保留你的源码，而不是替换它。通过的条件是每个被选中的测试都运行了；被跳过的测试不算完成证据。

> Initialize once from the repository root, then run the cumulative tests:
> The starter deliberately raises an implementation error. Later initialization preserves your source rather than replacing it. A passing result requires every selected test to run; a skipped test is not completion evidence.

## Check your reasoning · 检查你的推理

为什么两封主题相同的消息仍必须保持各自的身份？如果把 HTML 静默转换成纯文本，会丢失什么信息？

> Why must two messages with the same subject still keep separate identities? What information would be lost if HTML were silently converted to plain text?

## Connect it to the finished artifact · 连接到最终成品

一个 HTML 审阅台、triage.json，以及可下载的未发送 .eml 草稿。默认分类器使用显式短语规则，而不是 LLM。它处理一个导出消息的文件夹，从不连接你的邮箱，也从不发送回复。日期、紧急程度和承诺的动作都不做推断。

项目完成后，用自己的输入试一试：

```bash
cd my-inbox-triage-desk
python3 main.py --input ./fixtures --out ./inbox-output
```

添加一个带名称和大小的本地附件清单。附件要与用于分诊（triage）的文本分开保存。

> An HTML review desk, triage.json, and downloadable unsent .eml drafts. The default classifier uses explicit phrase rules, not an LLM. It handles a folder of exported messages and never connects to your mailbox or sends replies. Dates, urgency and promised actions are not inferred.
> After completing the project, try your own inputs:
> Add a local attachment inventory with names and sizes. Keep attachments separate from text used for triage.

## Primary reference · 主要参考

[官方 API 文档](https://docs.python.org/3/library/email.parser.html)。实现、示例与 fixtures 均为原创。该参考解释底层 API；项目特有的策略已在上面写明。

> [Official API documentation](https://docs.python.org/3/library/email.parser.html). The implementation, examples and fixtures are original. The reference explains the underlying API; the project-specific policies are stated above.
