# Compare exact text and preserve duplicates · 精确比较文本并保留重复

> Build stable snapshots and count added and removed text occurrences.

**Type:** Build  
**Language:** Go  
**Stage:** 2 of 4  
**Time:** About 2 hours

## What you are building · 你在造什么

集合（set）会丢掉重复文本。改用每个归一化块的计数（count），这样一条重复出现的通知消失，仍然算一次变更。比较刻意忽略块顺序：在本项目中，把一条未变更的通知挪到另一个 section 不算文本编辑。对输出行排序以获得稳定的报告。

```figure
pj-web-change-brief-2
```

> A set loses repeated text. Use counts per normalized block so one repeated notice disappearing is still a change. The comparison ignores block order deliberately: moving an unchanged notice between sections is not a text edit in this project. Sort output rows for stable reports.

## Work through an example · 走一遍例子

before 包含 A、A、B；after 包含 A、B、C。报告移除一个 A 的出现（occurrence），新增一个 C，并计出两个未变更块。仅打乱 A 和 B 的顺序，既不改变报告，也不改变内容哈希。

写代码之前，先为这个例子写下返回字段，以及一个应当失败的输入。把预期结果放在实现旁边，才能区分「契约变了」和「出了 bug」。

> Before contains A, A, B; after contains A, B, C. The report removes one occurrence of A, adds one C and counts two unchanged blocks. Reordering A and B alone changes neither the report nor the content hash.
> Before coding, write down the returned fields for that example and one input that should fail. Keep the expected result beside your implementation so you can distinguish a contract change from a bug.

## Implement the contract · 实现契约

- `CanonicalURL(raw string) (string, error)`
- `NewSnapshot(rawURL, input string, ignores []string) (Snapshot, error)`
- `Compare(before, after Snapshot) (Brief, error)`

规范化 HTTP(S) URL：拒绝凭据、主机名小写、丢弃 fragment、为空路径补 /。保留查询字符串。只比较规范化 URL 完全相同的快照。用 SHA-256 对排序后块的 JSON 序列化做哈希。added 和 removed 条目包含 text 和 count；unchanged 的计数保留了出现次数。

保持此前阶段可用。在你的学习工作区（learner workspace）里实现这些函数，走例子的过程中让参考解法保持关闭。

> Canonicalize HTTP(S) URLs by rejecting credentials, lowercasing the host, dropping fragments and supplying / for an empty path. Preserve query strings. Compare only snapshots with exactly the same canonical URL. Hash the JSON serialization of sorted blocks with SHA-256. Added and removed entries contain text and count; unchanged counts preserved occurrences.
> Keep earlier stages working. Implement these functions in your learner workspace, leaving the reference solution closed while you work through the example.

## Hints and failure cases · 提示与失败场景

构建两个块计数 map，然后用最小值得到未变更的出现次数，用正差值得到新增/移除。JSON 序列化避免了「单个含分隔符的块」和「多个块」之间的歧义。

> Build two maps of block counts, then use the minimum for unchanged occurrences and positive differences for additions/removals. JSON serialization avoids ambiguity between a single block containing separators and several blocks.

## Run your stage · 跑你的阶段

从仓库根目录初始化一次，然后运行累积测试：

```bash
python3 scripts/project_test.py web-change-brief --init my-web-change-brief
python3 scripts/project_test.py web-change-brief --stage 2 --path my-web-change-brief
```

启动代码（starter）故意抛出一个实现错误。之后再次初始化会保留你的源码而不是替换它。通过的结果要求每个被选中的测试都真正运行过；被跳过的测试不算完成证据。

> Initialize once from the repository root, then run the cumulative tests:
> The starter deliberately raises an implementation error. Later initialization preserves your source rather than replacing it. A passing result requires every selected test to run; a skipped test is not completion evidence.

## Check your reasoning · 检查你的推理

内容哈希为什么不能确立页面由谁发布、何时发布？忽略顺序时，哪些变更被有意地隐去了？

> Why does a content hash not establish who published the page or when? Which changes are intentionally invisible when order is ignored?

## Connect it to the finished artifact · 连接到完成品

一个独立的变更报告 changes.json，以及一个可复用的 baseline.json 快照。这个抽取器是一个刻意受限的可读块扫描器，不是 HTML5 DOM，也不是浏览器。它不执行 JavaScript、不求值 CSS 可见性，也不抓取链接资源。块顺序被忽略；重复文本的计数被保留。过滤短语可能藏掉有用的变更，所以对两个快照要用同一条显式过滤策略。

完成项目之后，用你自己的输入试试：

```bash
cd my-web-change-brief
go run . --before fixtures/before.html --after fixtures/after.html --url https://example.invalid/makerspace --out ./web-change-output
```

用序列算法（sequence algorithm）为顺序变更添加一份单独的报告。把文本新增单独区分开，让「移动了的段落」不会变成一个误导性的「删除 + 新增」。

> A standalone change report, changes.json and a reusable baseline.json snapshot. The extractor is a deliberately limited readable-block scanner, not an HTML5 DOM or browser. It does not execute JavaScript, evaluate CSS visibility or fetch linked resources. Block order is ignored; repeated text counts are retained. Filtering phrases can hide useful changes, so use the same explicit filter policy for both snapshots.
> After completing the project, try your own inputs:
> Add a separate order-change report using a sequence algorithm. Keep text additions distinct so a moved paragraph does not become a misleading deletion plus addition.

## Primary reference · 主要参考

[Official API documentation](https://pkg.go.dev/net/http)（官方 API 文档）。实现、示例和夹具均为原创。参考文档解释底层 API；项目特有的策略已在上面写明。

> [Official API documentation](https://pkg.go.dev/net/http). The implementation, examples and fixtures are original. The reference explains the underlying API; the project-specific policies are stated above.
