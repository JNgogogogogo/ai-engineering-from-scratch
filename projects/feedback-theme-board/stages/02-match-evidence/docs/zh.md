# Match phrases while preserving original spans · 匹配短语并保留原文区间

**Type:** Build
**Language:** TypeScript
**Stage:** 第 2 / 4 阶段
**Time:** ~2 小时（完成所列前置内容后）
**Prerequisites:** 前一个阶段，以及[开发环境](../../../../../phases/00-setup-and-tooling/01-dev-environment/docs/en.md)、[数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

## What you build · 你要构建什么

本阶段属于 Feedback Theme Board（反馈主题看板）项目：用可检查的短语证据给产品反馈分组，统计去重后的来源数量，并导出本地的 issue 草稿。

你的公开契约是 `findEvidence(row, phrase)`。配套提供的 CLI 和示例文件已在你的工作区里；请在 `main.ts` 中实现领域函数。保持它们的签名不变，这样其他应用才能调用同一个边界。

> This stage contributes to Feedback Theme Board: group product feedback with inspectable phrase evidence, count distinct sources, and export local issue drafts.
> Your public contract is `findEvidence(row, phrase)`. The supplied CLI and sample files live in your workspace; implement the domain functions in `main.ts`. Keep their signatures so another application can call the same boundary.

## Work through the mechanism · 剖析机制

对原文分词（tokenize）时，保留每个 token 的 start 和 end。为匹配而规范化 token 的值，但引文要从原始字符串中截取。比较相邻的 token 可以避免子串层面的错误，例如不会把 slowdown 里的 slow 匹配进去。

本阶段说明的是「一条规则为什么命中」，它并不说明这条反馈在事实上正确、也不说明其情感是负面的。一个被否定的句子仍然可以包含该短语。这一局限应当保持可见，让后续用户去复查证据，而不是盲目信任一个分类标签。

| 文本 | 短语 | 结果 |
|---|---|---|
| Search results show old pages. | old pages | 与原文完全一致的引文 |
| The old homepage changed. | old pages | 无匹配 |
| No more old pages appear. | old pages | 匹配，但需要解读 |

> Tokenize the original text while retaining each token’s start and end. Normalize token values for matching, but derive the quote from the original string. Consecutive token comparison avoids substring mistakes such as matching slow inside slowdown.
> This stage establishes why a rule matched; it does not establish the feedback is factually correct or that its sentiment is negative. A negated sentence can still contain the phrase. That limitation should remain visible so later users can review evidence rather than trust a category label blindly.

## Predict before running · 运行前先预测

在匹配短语的前面加一个 emoji。验证 JavaScript 的 slice 仍然能用 UTF-16 偏移量复现出引文。

```figure
pj-feedback-theme-board-2
```

修改 figure 的输入并核对计算出的值。把其中一个变化的结果对应到你实现中的某一行；figure 是一个解释性模型，不能替代真实程序。

> Add an emoji before the matching phrase. Verify JavaScript slice still reproduces the quote using UTF-16 offsets.
> Change the figure input and check the computed values. Relate one changed result to a line in your implementation; the figure is an explanatory model, not a replacement for the real program.

## Build and verify · 构建并验证

在仓库根目录初始化一次。这一步会复制公开类型、函数存根、一个真实的命令封装和原创示例输入。全新的第一次运行应当失败，因为领域函数还没有实现。

```bash
python3 scripts/project_test.py feedback-theme-board --init my-feedback-theme-board
python3 scripts/project_test.py feedback-theme-board --stage 2 --path my-feedback-theme-board --strict
```

用标准库实现契约。先亲手推演那个完整示例。保持调用方的输入不变，并用可操作的错误信息拒绝畸形数据。测试导入的是你的工作区，绝不是参考实现。

> From the repository root, initialize once. This copies public types, function stubs, a real command wrapper and original sample input. A fresh first-stage run should fail because the domain functions are not implemented.
> Implement the contract with the standard library. Trace the worked example by hand first. Keep caller inputs unchanged and reject malformed data with an actionable error. Tests import your workspace, never the reference solution.

## Hint ladder · 提示阶梯

1. 为每个原始 token 保留 match.index。
2. 比较规范化后的 token 值，而不是规范化后的全文偏移量。
3. 返回最小的匹配区间。

> 1. Keep match.index for each original token.
> 2. Compare normalized token values, not normalized whole-text offsets.
> 3. Return the smallest matched span.

## What you should see · 你应看到什么

在这一阶段，评分器会报告第 1 至第 2 阶段的真实通过测试。完成全部四个阶段后，先在提供的示例上运行交付的工具，然后换成你自己的输入：

```bash
cd my-feedback-theme-board
node cli.ts sample.jsonl themes.json output
```

最终产物是一个可移植的证据看板、一份 JSON 摘要和若干未发送的 Markdown 调查草稿。打开 HTML 并检查配套的 JSON，不要只看退出码。改动一个输入，并准确解释哪个结果必须随之改变。

> At this stage the grader reports real passing tests for stages 1 through 2. After completing all four stages, run the shipped tool on the supplied sample, then substitute your own input:
> The final artifact is a portable evidence board, JSON summary and unsent Markdown investigation drafts. Open the HTML and inspect the companion JSON instead of trusting an exit code alone. Change one input and explain exactly which result must change.

## Extend it · 扩展练习

把「否定」作为一个独立的启发式，为它增加一个评审标志，并测量它的误报。

范围说明：基线只匹配显式的词组短语，不涉及语义情感或真假。去重后的来源标签不是经过核实的真人，也不是市场规模。可选的模型建议会生成一份单独的 proposed 配置，必须经过评审才能使用；任何东西都不会发布到 issue 跟踪器。

主要参考：[JSON text interchange, RFC 8259](https://www.rfc-editor.org/rfc/rfc8259)。实现和练习数据都是原创教学示例。

> Add a review flag for negation as a separate heuristic and measure its false positives.
> Scope: The baseline matches explicit word phrases, not semantic sentiment or truth. Distinct source labels are not verified people or market size. Optional model suggestions produce a separate proposed configuration that must be reviewed before use; nothing posts to an issue tracker.
> Primary reference: [JSON text interchange, RFC 8259](https://www.rfc-editor.org/rfc/rfc8259). The implementation and exercise data are original teaching examples.
