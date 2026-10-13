# Export a brief a person can inspect · 导出人能亲自检查的简报

> Show exact added and removed statements beside the source and hashes.

**Type:** Build  
**Language:** Go  
**Stage:** 4 of 4  
**Time:** About 2 hours

## What you are building · 你在造什么

报告应该能回答「变了什么」，而不需要有人去读原始 HTML。列出精确的新增和移除的归一化语句、它们的出现次数，以及未变更块的数量。包含源 URL 和两个哈希，让另一个工具能把简报关联回已保存的快照。

```figure
pj-web-change-brief-4
```

> The report should answer what changed without requiring someone to read raw HTML. List the exact added and removed normalized statements, their occurrence counts and the number of unchanged blocks. Include the source URL and both hashes so another tool can relate the brief to saved snapshots.

## Work through an example · 走一遍例子

makerspace 夹具把维修开始时间从 14:00 改到 15:00，把志愿者可参与的名额从三处减到一处，并新增一条无台阶入口说明。导航计数和 footer 时间戳的变更不出现。报告保留 before 和 after 的原句，而不是发明一个意图摘要。

写代码之前，先为这个例子写下返回字段，以及一个应当失败的输入。把预期结果放在实现旁边，才能区分「契约变了」和「出了 bug」。

> The makerspace fixture changes the repair start from 14:00 to 15:00, reduces volunteer availability from three places to one, and adds a step-free entrance note. Changing the navigation count and footer timestamp does not appear. The report preserves the before and after statements instead of inventing a summary of their intent.
> Before coding, write down the returned fields for that example and one input that should fail. Keep the expected result beside your implementation so you can distinguish a contract change from a bug.

## Implement the contract · 实现契约

- `ExportBrief(brief Brief, directory string) error`
- `CLI flags: --before, --after, --url, --out, --fetch, --baseline, --accept, --ignore`

写出 changes.json 和 index.html。使用 html/template，让不可信的页面文本被转义、URL 上下文被安全处理。空的变更列表显示明确的「无变更」消息。CLI 还会把新快照写入输出目录；live 模式只在提供 --accept 时才覆盖已有基线。错误返回非零退出码。

保持此前阶段可用。在你的学习工作区（learner workspace）里实现这些函数，走例子的过程中让参考解法保持关闭。

> Write changes.json and index.html. Use html/template so untrusted page text is escaped and URL contexts are handled safely. Empty change lists display an explicit no-change message. The CLI also writes the new snapshot to the output directory; live mode overwrites an existing baseline only when --accept is supplied. Errors return a nonzero exit code.
> Keep earlier stages working. Implement these functions in your learner workspace, leaving the reference solution closed while you work through the example.

## Hints and failure cases · 提示与失败场景

构建一个带「看起来像脚本的文本块」的 Brief，验证 HTML 中文本被转义。解码 JSON 报告并检查出现次数。在不同的已存文件上运行真实 CLI，然后打开它的输出，而不是只凭模板源码判断页面。

> Build a Brief with a script-looking text block and verify the HTML contains escaped text. Decode the JSON report and inspect occurrence counts. Run the actual CLI on different saved files, then open its output rather than judging the page from the template source alone.

## Run your stage · 跑你的阶段

从仓库根目录初始化一次，然后运行累积测试：

```bash
python3 scripts/project_test.py web-change-brief --init my-web-change-brief
python3 scripts/project_test.py web-change-brief --stage 4 --path my-web-change-brief
```

启动代码（starter）故意抛出一个实现错误。之后再次初始化会保留你的源码而不是替换它。通过的结果要求每个被选中的测试都真正运行过；被跳过的测试不算完成证据。

> Initialize once from the repository root, then run the cumulative tests:
> The starter deliberately raises an implementation error. Later initialization preserves your source rather than replacing it. A passing result requires every selected test to run; a skipped test is not completion evidence.

## Check your reasoning · 检查你的推理

人能从这份报告直接确认什么，什么又需要原始 HTML 或渲染后的页面？为什么生成的叙述永远不该替代精确的变更证据？

> What can the person confirm directly from this report, and what would require the original HTML or rendered page? Why should a generated narrative never replace exact change evidence?

## Connect it to the finished artifact · 连接到完成品

一个独立的变更报告 changes.json，以及一个可复用的 baseline.json 快照。这个抽取器是一个刻意受限的可读块扫描器，不是 HTML5 DOM，也不是浏览器。它不执行 JavaScript、不求值 CSS 可见性，也不抓取链接资源。块顺序被忽略；重复文本的计数被保留。过滤短语可能藏掉有用的变更，所以对两个快照要用同一条显式过滤策略。

完成项目之后，用你自己的输入试试：

```bash
cd my-web-change-brief
go run . --before fixtures/before.html --after fixtures/after.html --url https://example.invalid/makerspace --out ./web-change-output
```

为团队交接添加一个审阅备注字段或 Markdown 导出。把自动外发通知保留为单独配置、自带测试的集成（integration）。

> A standalone change report, changes.json and a reusable baseline.json snapshot. The extractor is a deliberately limited readable-block scanner, not an HTML5 DOM or browser. It does not execute JavaScript, evaluate CSS visibility or fetch linked resources. Block order is ignored; repeated text counts are retained. Filtering phrases can hide useful changes, so use the same explicit filter policy for both snapshots.
> After completing the project, try your own inputs:
> Add a review note field or Markdown export for a team handoff. Keep automatic outbound notifications as a separately configured integration with its own tests.

## Primary reference · 主要参考

[Official API documentation](https://pkg.go.dev/net/http)（官方 API 文档）。实现、示例和夹具均为原创。参考文档解释底层 API；项目特有的策略已在上面写明。

> [Official API documentation](https://pkg.go.dev/net/http). The implementation, examples and fixtures are original. The reference explains the underlying API; the project-specific policies are stated above.
