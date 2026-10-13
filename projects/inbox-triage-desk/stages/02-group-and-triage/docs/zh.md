# Group references and explain the queue · 用引用分组并解释队列

> Use message references for threads and explicit phrases for triage.

**Type:** Build  
**Language:** Python  
**Stage:** 2 of 4  
**Time:** About 2 hours

## What you are building · 你在构建什么

主题（subject）不是可靠的线程键。两个互不相干的发件人可能使用同一个主题，线程也可能中途换主题。只有当 References 或 In-Reply-To 中的 ID 存在于已导入集合时才建立连接。已连接的消息组成一个线程，即使输入顺序变化也不受影响。

```figure
pj-inbox-triage-desk-2
```

> A subject is not a reliable thread key. Two unrelated senders can use the same subject, and a thread can change its subject. Build connections only when a References or In-Reply-To ID exists in the imported set. Connected messages form a thread even when input order changes.

## Work through an example · 走一个例子

三条消息：a；b 引用 a；c 引用 b —— 三者属于同一个线程。第四条消息主题相同但没有引用，保持独立。分诊方面：Please confirm 命中 action，For your information 命中 information。同时包含两者的正文是 uncertain，因为只挑一条获胜规则会掩盖冲突。

编码之前，先写下这个例子的返回字段，以及一个应该失败的输入。把期望结果放在实现旁边，这样你才能区分「契约变了」和「出了 bug」。

> Three messages a, b referencing a, and c referencing b belong to one thread. A fourth message with the same subject and no reference stays separate. For triage, Please confirm matches action. For your information matches information. A body containing both is uncertain, because choosing a single winning rule would hide the conflict.
> Before coding, write down the returned fields for that example and one input that should fail. Keep the expected result beside your implementation so you can distinguish a contract change from a bug.

## Implement the contract · 实现契约

- `group_threads(messages: list[dict]) -> list[dict]`
- `triage(message: dict, rules: dict | None = None) -> dict`

返回稳定的线程 ID 和按 ID 排序的消息。完全相同的重复项合并；同一 ID 却有冲突记录时抛出 ValueError。规则类别是 action 和 information；未命中或类别冲突的归为 uncertain。每个命中包含 category、quote、start 和 end，且 text[start:end] 等于 quote。优先级为 action=0、uncertain=1、information=2。

保持早前阶段可用。在学习者工作区里实现这些函数；做例子期间让参考实现保持关闭。

> Return stable thread IDs and messages sorted by ID. Identical duplicates collapse; conflicting records with the same ID raise ValueError. Rule categories are action and information; unmatched or conflicting categories become uncertain. Each hit contains category, quote, start and end, with text[start:end] equal to quote. Priorities are action=0, uncertain=1, information=2.
> Keep earlier stages working. Implement these functions in your learner workspace, leaving the reference solution closed while you work through the example.

## Hints and failure cases · 提示与失败场景

线程连接的表示要与显示顺序相互独立。检查短语边界，别让 please 匹配到 displeased。在原始正文上用大小写不敏感的匹配来定位 span，而不要在大小写折叠后的字符串上搜索——后者的偏移量可能改变。

> Represent thread connections independently from display order. Check phrase boundaries so please does not match displeased. Find spans in the original body with case-insensitive matching rather than searching a case-folded string whose offsets might change.

## Run your stage · 运行本阶段

从仓库根目录初始化一次，然后运行累积测试：

```bash
python3 scripts/project_test.py inbox-triage-desk --init my-inbox-triage-desk
python3 scripts/project_test.py inbox-triage-desk --stage 2 --path my-inbox-triage-desk
```

起步代码会故意抛出一个实现错误。之后的初始化会保留你的源码，而不是替换它。通过的条件是每个被选中的测试都运行了；被跳过的测试不算完成证据。

> Initialize once from the repository root, then run the cumulative tests:
> The starter deliberately raises an implementation error. Later initialization preserves your source rather than replacing it. A passing result requires every selected test to run; a skipped test is not completion evidence.

## Check your reasoning · 检查你的推理

一个短语命中就能证明请求是紧急或合法的吗？为什么 uncertain 项要排在 information 项之前？

> Does a matching phrase prove that a request is urgent or legitimate? Why should uncertain items appear before informational items?

## Connect it to the finished artifact · 连接到最终成品

一个 HTML 审阅台、triage.json，以及可下载的未发送 .eml 草稿。默认分类器使用显式短语规则，而不是 LLM。它处理一个导出消息的文件夹，从不连接你的邮箱，也从不发送回复。日期、紧急程度和承诺的动作都不做推断。

项目完成后，用自己的输入试一试：

```bash
cd my-inbox-triage-desk
python3 main.py --input ./fixtures --out ./inbox-output
```

添加由用户维护的发件人偏好，作为另一个显式排序信号。让命中的短语和规则方法保持可见。

> An HTML review desk, triage.json, and downloadable unsent .eml drafts. The default classifier uses explicit phrase rules, not an LLM. It handles a folder of exported messages and never connects to your mailbox or sends replies. Dates, urgency and promised actions are not inferred.
> After completing the project, try your own inputs:
> Add user-maintained sender preferences as a separate explicit ranking signal. Keep the matched phrase and rule method visible.

## Primary reference · 主要参考

[官方 API 文档](https://docs.python.org/3/library/email.parser.html)。实现、示例与 fixtures 均为原创。该参考解释底层 API；项目特有的策略已在上面写明。

> [Official API documentation](https://docs.python.org/3/library/email.parser.html). The implementation, examples and fixtures are original. The reference explains the underlying API; the project-specific policies are stated above.
