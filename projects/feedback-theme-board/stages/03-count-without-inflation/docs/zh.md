# Count evidence without inflating source support · 统计证据而不夸大来源支持

**Type:** Build
**Language:** TypeScript
**Stage:** 第 3 / 4 阶段
**Time:** ~2 小时（完成所列前置内容后）
**Prerequisites:** 前一个阶段，以及[开发环境](../../../../../phases/00-setup-and-tooling/01-dev-environment/docs/en.md)、[数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

## What you build · 你要构建什么

本阶段属于 Feedback Theme Board（反馈主题看板）项目：用可检查的短语证据给产品反馈分组，统计去重后的来源数量，并导出本地的 issue 草稿。

你的公开契约是 `buildBoard(rows, themes)`。配套提供的 CLI 和示例文件已在你的工作区里；请在 `main.ts` 中实现领域函数。保持它们的签名不变，这样其他应用才能调用同一个边界。

> This stage contributes to Feedback Theme Board: group product feedback with inspectable phrase evidence, count distinct sources, and export local issue drafts.
> Your public contract is `buildBoard(rows, themes)`. The supplied CLI and sample files live in your workspace; implement the domain functions in `main.ts`. Keep their signatures so another application can call the same boundary.

## Work through the mechanism · 剖析机制

重复的记录和重复的来源会造成不同的计数错误。先把「同一来源 + 相同规范化文本」去重，同时保留重复关系以备检查。然后在每个主题内统计去重后的来源标签。来自 interview-a 的两条不同记录，仍然只提供一个去重后的来源标签。

一条记录可以命中多个主题。因此各主题的计数之和不必等于输入记录的数量。把未匹配的反馈留在可见的队列里；把它丢掉会让看板偏向你本来就预期找到的那些类别。

| 示例主题 | 匹配的记录数 | 去重后的来源标签数 |
|---|---|---|
| First useful run | 2 | 1 |
| Stale search | 2 | 2 |
| Search latency | 1 | 1 |

> Repeated records and repeated sources cause different counting errors. Deduplicate the same normalized text from the same source, retaining the duplicate relationship for inspection. Then count unique source labels within each theme. Two distinct records from interview-a still provide one distinct source label.
> A record can match multiple themes. Therefore theme totals need not add to the number of input records. Keep unmatched feedback in a visible queue; dropping it would bias the board toward the categories you already expected to find.

## Predict before running · 运行前先预测

在相同来源下用一个新 ID 复制 f-1，然后再在另一个来源下复制一次。解释两个计数器各自应该如何变化。

```figure
pj-feedback-theme-board-3
```

修改 figure 的输入并核对计算出的值。把其中一个变化的结果对应到你实现中的某一行；figure 是一个解释性模型，不能替代真实程序。

> Copy f-1 under a new ID with the same source, then under a different source. Explain how both counters should change.
> Change the figure input and check the computed values. Relate one changed result to a line in your implementation; the figure is an explanatory model, not a replacement for the real program.

## Build and verify · 构建并验证

在仓库根目录初始化一次。这一步会复制公开类型、函数存根、一个真实的命令封装和原创示例输入。全新的第一次运行应当失败，因为领域函数还没有实现。

```bash
python3 scripts/project_test.py feedback-theme-board --init my-feedback-theme-board
python3 scripts/project_test.py feedback-theme-board --stage 3 --path my-feedback-theme-board --strict
```

用标准库实现契约。先亲手推演那个完整示例。保持调用方的输入不变，并用可操作的错误信息拒绝畸形数据。测试导入的是你的工作区，绝不是参考实现。

> From the repository root, initialize once. This copies public types, function stubs, a real command wrapper and original sample input. A fresh first-stage run should fail because the domain functions are not implemented.
> Implement the contract with the standard library. Trace the worked example by hand first. Keep caller inputs unchanged and reject malformed data with an actionable error. Tests import your workspace, never the reference solution.

## Hint ladder · 提示阶梯

1. 用「来源 + 规范化文本」的指纹做重复检测。
2. 为每个主题使用来源标签的集合。
3. 在结果中保留未匹配和重复的记录。

> 1. Use a fingerprint of source plus normalized text for duplicate detection.
> 2. Use a set of source labels for each theme.
> 3. Preserve unmatched and duplicate records in the result.

## What you should see · 你应看到什么

在这一阶段，评分器会报告第 1 至第 3 阶段的真实通过测试。完成全部四个阶段后，先在提供的示例上运行交付的工具，然后换成你自己的输入：

```bash
cd my-feedback-theme-board
node cli.ts sample.jsonl themes.json output
```

最终产物是一个可移植的证据看板、一份 JSON 摘要和若干未发送的 Markdown 调查草稿。打开 HTML 并检查配套的 JSON，不要只看退出码。改动一个输入，并准确解释哪个结果必须随之改变。

> At this stage the grader reports real passing tests for stages 1 through 3. After completing all four stages, run the shipped tool on the supplied sample, then substitute your own input:
> The final artifact is a portable evidence board, JSON summary and unsent Markdown investigation drafts. Open the HTML and inspect the companion JSON instead of trusting an exit code alone. Change one input and explain exactly which result must change.

## Extend it · 扩展练习

比较两份主题配置，并报告哪些记录改变了所属主题。

范围说明：基线只匹配显式的词组短语，不涉及语义情感或真假。去重后的来源标签不是经过核实的真人，也不是市场规模。可选的模型建议会生成一份单独的 proposed 配置，必须经过评审才能使用；任何东西都不会发布到 issue 跟踪器。

主要参考：[JSON text interchange, RFC 8259](https://www.rfc-editor.org/rfc/rfc8259)。实现和练习数据都是原创教学示例。

> Compare two theme configurations and report which records changed membership.
> Scope: The baseline matches explicit word phrases, not semantic sentiment or truth. Distinct source labels are not verified people or market size. Optional model suggestions produce a separate proposed configuration that must be reviewed before use; nothing posts to an issue tracker.
> Primary reference: [JSON text interchange, RFC 8259](https://www.rfc-editor.org/rfc/rfc8259). The implementation and exercise data are original teaching examples.
