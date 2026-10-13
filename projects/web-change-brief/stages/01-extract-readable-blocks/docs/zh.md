# Extract text before comparing pages · 比较页面之前，先抽取文本

> Scan HTML into normalized readable blocks and exclude known noise regions.

**Type:** Build  
**Language:** Go  
**Stage:** 1 of 4  
**Time:** About 2 hours

## What you are building · 你在造什么

原始 HTML diff 会被时间戳、导航和标记淹没。先抽取一个可读文本块（readable text block）序列。本项目在扫描标签边界时尊重带引号的属性，丢弃注释，并忽略 head、script、style、nav、footer 和 noscript 区域。段落、标题、列表项和结构性容器构成块边界。

```figure
pj-web-change-brief-1
```

> A raw HTML diff is dominated by timestamps, navigation and markup. Extract a sequence of readable text blocks first. This project scans tag boundaries while respecting quoted attributes, drops comments, and ignores head, script, style, nav, footer and noscript regions. Paragraphs, headings, list items and structural containers form block boundaries.

## Work through an example · 走一遍例子

对于 <nav>Visits 12</nav><p>Bring a mug &amp; a spoon.</p>，返回一个块：Bring a mug & a spoon。改变访问次数不应改变结果。段落里的行内 strong 标签应保留相邻文本，而不产生另一个块。

写代码之前，先为这个例子写下返回字段，以及一个应当失败的输入。把预期结果放在实现旁边，才能区分「契约变了」和「出了 bug」。

> For <nav>Visits 12</nav><p>Bring a mug &amp; a spoon.</p>, return one block: Bring a mug & a spoon. Changing the visit count should not change the result. An inline strong tag inside a paragraph should preserve adjacent text without creating another block.
> Before coding, write down the returned fields for that example and one input that should fail. Keep the expected result beside your implementation so you can distinguish a contract change from a bug.

## Implement the contract · 实现契约

- `ExtractBlocks(input string, ignorePhrases []string) ([]string, error)`

归一化实体和空白。省略空块。可选的非空短语会以大小写不敏感的方式移除整个匹配的块。拒绝超过 2,000,000 字节的输入、未闭合的标签/注释/被忽略区域，以及超过 10,000 个块。让这个扫描器支持的子集保持显眼：它不是完整的浏览器解析器，也无法推断视觉上的可见性。

保持此前阶段可用。在你的学习工作区（learner workspace）里实现这些函数，走例子的过程中让参考解法保持关闭。

> Normalize entities and whitespace. Omit empty blocks. Optional nonempty phrases remove a whole matching block case-insensitively. Reject input beyond 2,000,000 bytes, unclosed tags/comments/ignored regions and more than 10,000 blocks. Keep this scanner's supported subset visible: it is not a full browser parser and cannot infer visual visibility.
> Keep earlier stages working. Implement these functions in your learner workspace, leaving the reference solution closed while you work through the example.

## Hints and failure cases · 提示与失败场景

寻找标签的闭合尖括号时，跟踪引号是否处于打开状态。只在块边界冲刷（flush）累积的文本。在追加文本之前先跳过被忽略区域。空标签必须产生错误或安全的无操作（no-op），绝不能产生索引 panic。

> Track whether a quote is open while finding a tag's closing angle bracket. Flush accumulated text only at block boundaries. Skip ignored regions before appending text. An empty tag must produce an error or safe no-op, never an index panic.

## Run your stage · 跑你的阶段

从仓库根目录初始化一次，然后运行累积测试：

```bash
python3 scripts/project_test.py web-change-brief --init my-web-change-brief
python3 scripts/project_test.py web-change-brief --stage 1 --path my-web-change-brief
```

启动代码（starter）故意抛出一个实现错误。之后再次初始化会保留你的源码而不是替换它。通过的结果要求每个被选中的测试都真正运行过；被跳过的测试不算完成证据。

> Initialize once from the repository root, then run the cumulative tests:
> The starter deliberately raises an implementation error. Later initialization preserves your source rather than replacing it. A passing result requires every selected test to run; a skipped test is not completion evidence.

## Check your reasoning · 检查你的推理

页面作者会把什么有用的文本放进 footer？为什么移除整个匹配短语的块需要一条显式策略？

> What useful text could a page author place in a footer? Why does removing a whole phrase-matching block need an explicit policy?

## Connect it to the finished artifact · 连接到完成品

一个独立的变更报告 changes.json，以及一个可复用的 baseline.json 快照。这个抽取器是一个刻意受限的可读块扫描器，不是 HTML5 DOM，也不是浏览器。它不执行 JavaScript、不求值 CSS 可见性，也不抓取链接资源。块顺序被忽略；重复文本的计数被保留。过滤短语可能藏掉有用的变更，所以对两个快照要用同一条显式过滤策略。

完成项目之后，用你自己的输入试试：

```bash
cd my-web-change-brief
go run . --before fixtures/before.html --after fixtures/after.html --url https://example.invalid/makerspace --out ./web-change-output
```

为你要监控的真实 HTML 添加一条有文档说明的按站点抽取规则和一个夹具（fixture）。让解析失败保持可见，而不是返回一个空的成功快照。

> A standalone change report, changes.json and a reusable baseline.json snapshot. The extractor is a deliberately limited readable-block scanner, not an HTML5 DOM or browser. It does not execute JavaScript, evaluate CSS visibility or fetch linked resources. Block order is ignored; repeated text counts are retained. Filtering phrases can hide useful changes, so use the same explicit filter policy for both snapshots.
> After completing the project, try your own inputs:
> Add a documented per-site extraction rule and a fixture for the real HTML you want to monitor. Keep a parser failure visible rather than returning an empty successful snapshot.

## Primary reference · 主要参考

[Official API documentation](https://pkg.go.dev/net/http)（官方 API 文档）。实现、示例和夹具均为原创。参考文档解释底层 API；项目特有的策略已在上面写明。

> [Official API documentation](https://pkg.go.dev/net/http). The implementation, examples and fixtures are original. The reference explains the underlying API; the project-specific policies are stated above.
