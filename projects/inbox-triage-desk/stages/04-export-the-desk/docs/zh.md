# Export an auditable inbox desk · 导出可审计的收件台

> Write portable HTML, JSON and draft files from the same review records.

**Type:** Build  
**Language:** Python  
**Stage:** 4 of 4  
**Time:** About 2 hours

## What you are building · 你在构建什么

导出才是有用的最终产物。应当让不运行 Python 的人也能查看输入、类别、理由和精确命中的短语。条目先按优先级、再按消息 ID 排序，让重复导出易于对比。把 JSON 报告保留为对接另一个应用的集成边界。

```figure
pj-inbox-triage-desk-4
```

> The export is the useful end product. Someone should be able to inspect the input, category, reason and exact matched phrase without running Python. Sort entries by priority and then message ID so repeated exports are easy to compare. Keep the JSON report as the integration boundary for another app.

## Work through an example · 走一个例子

内置的 repair-event fixture 包含一条 action 消息、一条 information 回复和一条含义不清的便签。它变成两个线程、三条队列条目。打开 index.html 能看到每封完整正文和一份可下载的未发送草稿；triage.json 保留线程归属和证据偏移量。

编码之前，先写下这个例子的返回字段，以及一个应该失败的输入。把期望结果放在实现旁边，这样你才能区分「契约变了」和「出了 bug」。

> The authored repair-event fixture has one action message, one informational reply and one unclear note. It becomes two threads and three queue entries. Opening index.html shows each full body and a downloadable unsent draft; triage.json retains thread membership and evidence offsets.
> Before coding, write down the returned fields for that example and one input that should fail. Keep the expected result beside your implementation so you can distinguish a contract change from a bug.

## Implement the contract · 实现契约

- `export_desk(messages, out: Path, rules=None) -> dict`

写出 index.html 和 triage.json，并为每封唯一消息写一个以摘要命名的 .eml。绝不要把主题或发件人直接当作文件名。在 HTML 中转义所有消息文本和主题。包含 schema 版本、规则方法和需要人工审阅的状态。空输入也要导出一个合法的空 desk。

保持早前阶段可用。在学习者工作区里实现这些函数；做例子期间让参考实现保持关闭。

> Write index.html and triage.json plus one digest-named .eml per unique message. Never use a subject or sender directly as a filename. Escape all message text and subjects in HTML. Include a schema version, rule method and review-required status. Empty input still exports a valid empty desk.
> Keep earlier stages working. Implement these functions in your learner workspace, leaving the reference solution closed while you work through the example.

## Hints and failure cases · 提示与失败场景

让 JSON 和 HTML 渲染共用同一份报告结构，防止两边总数不一致。把一个长得像 HTML 的字符串放进测试主题里，验证它被转义了。验证草稿文件真实存在，而不只是测试它展示出来的链接。

> Use one report structure for JSON and HTML rendering to prevent divergent totals. Put an HTML-like string in a test subject and verify it is escaped. Verify a draft file actually exists rather than only testing its displayed link.

## Run your stage · 运行本阶段

从仓库根目录初始化一次，然后运行累积测试：

```bash
python3 scripts/project_test.py inbox-triage-desk --init my-inbox-triage-desk
python3 scripts/project_test.py inbox-triage-desk --stage 4 --path my-inbox-triage-desk
```

起步代码会故意抛出一个实现错误。之后的初始化会保留你的源码，而不是替换它。通过的条件是每个被选中的测试都运行了；被跳过的测试不算完成证据。

> Initialize once from the repository root, then run the cumulative tests:
> The starter deliberately raises an implementation error. Later initialization preserves your source rather than replacing it. A passing result requires every selected test to run; a skipped test is not completion evidence.

## Check your reasoning · 检查你的推理

把输出目录搬到另一台电脑之后，什么东西还能用？消费者在依赖你的 JSON 格式之前，还需要什么额外的约定？

> What survives if you move the output directory to another computer? What additional agreement would a consumer need before depending on your JSON format?

## Connect it to the finished artifact · 连接到最终成品

一个 HTML 审阅台、triage.json，以及可下载的未发送 .eml 草稿。默认分类器使用显式短语规则，而不是 LLM。它处理一个导出消息的文件夹，从不连接你的邮箱，也从不发送回复。日期、紧急程度和承诺的动作都不做推断。

项目完成后，用自己的输入试一试：

```bash
cd my-inbox-triage-desk
python3 main.py --input ./fixtures --out ./inbox-output
```

把 triage.json 导入一个本地 dashboard，或者添加一个以消息 ID 为键的人工复核决定文件。让编辑与原始证据明确区分开。

> An HTML review desk, triage.json, and downloadable unsent .eml drafts. The default classifier uses explicit phrase rules, not an LLM. It handles a folder of exported messages and never connects to your mailbox or sends replies. Dates, urgency and promised actions are not inferred.
> After completing the project, try your own inputs:
> Import triage.json into a local dashboard, or add a reviewed decision file keyed by message ID. Keep edits distinct from the original evidence.

## Primary reference · 主要参考

[官方 API 文档](https://docs.python.org/3/library/email.parser.html)。实现、示例与 fixtures 均为原创。该参考解释底层 API；项目特有的策略已在上面写明。

> [Official API documentation](https://docs.python.org/3/library/email.parser.html). The implementation, examples and fixtures are original. The reference explains the underlying API; the project-specific policies are stated above.
