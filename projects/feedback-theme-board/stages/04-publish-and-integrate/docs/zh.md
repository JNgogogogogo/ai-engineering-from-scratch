# Publish evidence and reviewable investigation drafts · 发布证据和可评审的调查草稿

**Type:** Build
**Language:** TypeScript
**Stage:** 第 4 / 4 阶段
**Time:** ~2 小时（完成所列前置内容后）
**Prerequisites:** 前一个阶段，以及[开发环境](../../../../../phases/00-setup-and-tooling/01-dev-environment/docs/en.md)、[数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

## What you build · 你要构建什么

本阶段属于 Feedback Theme Board（反馈主题看板）项目：用可检查的短语证据给产品反馈分组，统计去重后的来源数量，并导出本地的 issue 草稿。

你的公开契约是 `draftIssue(theme); renderBoard(board)`。配套提供的 CLI 和示例文件已在你的工作区里；请在 `main.ts` 中实现领域函数。保持它们的签名不变，这样其他应用才能调用同一个边界。

> This stage contributes to Feedback Theme Board: group product feedback with inspectable phrase evidence, count distinct sources, and export local issue drafts.
> Your public contract is `draftIssue(theme); renderBoard(board)`. The supplied CLI and sample files live in your workspace; implement the domain functions in `main.ts`. Keep their signatures so another application can call the same boundary.

## Work through the mechanism · 剖析机制

看板应当让「核对一条来源引文」比「看一个头条数字」更容易。把证据、来源标签和偏移量渲染在每个主题旁边；把未匹配记录和重复计数也放进去。对所有用户文本做转义，包括来源标签。

为每个主题导出一份本地的 Markdown 调查草稿。草稿提议的是如何复现所报告的摩擦；它不得把一次关键词命中变成一个已确认的缺陷。可选的模型可以通过 --suggest 建议主题规则，但其输出会被单独保存，并在有人采纳之前通过同样的 schema 校验。

| 产物 | 下一步动作 |
|---|---|
| board.html | 复核精确引文 |
| board.json | 在另一个工具中对比多次运行 |
| first-run.md | 在本地编辑一份调查草稿 |
| themes.proposed.json | 评审可选的模型建议 |

> The board should make a source quote easier to inspect than a headline count. Render evidence, source labels and offsets beside each theme; include unmatched records and duplicate counts. Escape all user text, including source labels.
> Export one local Markdown investigation draft per theme. A draft proposes reproducing the reported friction; it must not turn a keyword match into a confirmed defect. An optional model can suggest theme rules through --suggest, but its output is saved separately and passes the same schema validation before a person adopts it.

## Predict before running · 运行前先预测

查看 first-run 的计数和它旁边的两条引文。解释为什么草稿说的是「一个来源标签」，而不是「两个客户」。

```figure
pj-feedback-theme-board-4
```

修改 figure 的输入并核对计算出的值。把其中一个变化的结果对应到你实现中的某一行；figure 是一个解释性模型，不能替代真实程序。

> Inspect the first-run count beside its two quotes. Explain why the draft says one source label rather than two customers.
> Change the figure input and check the computed values. Relate one changed result to a line in your implementation; the figure is an explanatory model, not a replacement for the real program.

## Build and verify · 构建并验证

在仓库根目录初始化一次。这一步会复制公开类型、函数存根、一个真实的命令封装和原创示例输入。全新的第一次运行应当失败，因为领域函数还没有实现。

```bash
python3 scripts/project_test.py feedback-theme-board --init my-feedback-theme-board
python3 scripts/project_test.py feedback-theme-board --stage 4 --path my-feedback-theme-board --strict
```

用标准库实现契约。先亲手推演那个完整示例。保持调用方的输入不变，并用可操作的错误信息拒绝畸形数据。测试导入的是你的工作区，绝不是参考实现。

> From the repository root, initialize once. This copies public types, function stubs, a real command wrapper and original sample input. A fresh first-stage run should fail because the domain functions are not implemented.
> Implement the contract with the standard library. Trace the worked example by hand first. Keep caller inputs unchanged and reject malformed data with an actionable error. Tests import your workspace, never the reference solution.

## Hint ladder · 提示阶梯

1. 用你导出为 JSON 的同一个 board 对象来渲染。
2. 让 issue 的生成保持在本地且显式。
3. 把模型建议的配置与已接受的配置分开保存。

> 1. Render from the same board object you export as JSON.
> 2. Keep issue writing local and explicit.
> 3. Keep model-suggested configuration separate from accepted configuration.

## What you should see · 你应看到什么

在这一阶段，评分器会报告第 1 至第 4 阶段的真实通过测试。完成全部四个阶段后，先在提供的示例上运行交付的工具，然后换成你自己的输入：

```bash
cd my-feedback-theme-board
node cli.ts sample.jsonl themes.json output
```

最终产物是一个可移植的证据看板、一份 JSON 摘要和若干未发送的 Markdown 调查草稿。打开 HTML 并检查配套的 JSON，不要只看退出码。改动一个输入，并准确解释哪个结果必须随之改变。

> At this stage the grader reports real passing tests for stages 1 through 4. After completing all four stages, run the shipped tool on the supplied sample, then substitute your own input:
> The final artifact is a portable evidence board, JSON summary and unsent Markdown investigation drafts. Open the HTML and inspect the companion JSON instead of trusting an exit code alone. Change one input and explain exactly which result must change.

## Extend it · 扩展练习

把 board.json 喂给一个优先级排序工具，并要求它保留原始的证据链接。

范围说明：基线只匹配显式的词组短语，不涉及语义情感或真假。去重后的来源标签不是经过核实的真人，也不是市场规模。可选的模型建议会生成一份单独的 proposed 配置，必须经过评审才能使用；任何东西都不会发布到 issue 跟踪器。

主要参考：[JSON text interchange, RFC 8259](https://www.rfc-editor.org/rfc/rfc8259)。实现和练习数据都是原创教学示例。

> Feed board.json to a prioritization tool and require it to retain the original evidence links.
> Scope: The baseline matches explicit word phrases, not semantic sentiment or truth. Distinct source labels are not verified people or market size. Optional model suggestions produce a separate proposed configuration that must be reviewed before use; nothing posts to an issue tracker.
> Primary reference: [JSON text interchange, RFC 8259](https://www.rfc-editor.org/rfc/rfc8259). The implementation and exercise data are original teaching examples.
