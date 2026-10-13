# Show evidence and export reviewed values · 展示证据并导出已评审的值

**Type:** Build
**Language:** Python
**Stage:** 第 4 / 4 阶段
**Time:** ~2 小时（完成所列前置内容后）
**Prerequisites:** 前一个阶段，以及[开发环境](../../../../../phases/00-setup-and-tooling/01-dev-environment/docs/en.md)、[数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

## What you build · 你要构建什么

本阶段属于 Document Extraction Review Desk（文档抽取评审台）项目：从文本文档中抽取结构化字段，检查精确的原文区间，并在导出前批准含糊的值。

你的公开契约是 `render_review(report)`。配套提供的 CLI 和示例文件已在你的工作区里；请在 `main.py` 中实现领域函数。保持它们的签名不变，这样其他应用才能调用同一个边界。

> This stage contributes to Document Extraction Review Desk: extract structured fields from a text document, inspect exact source spans, and approve ambiguous values before export.
> Your public contract is `render_review(report)`. The supplied CLI and sample files live in your workspace; implement the domain functions in `main.py`. Keep their signatures so another application can call the same boundary.

## Work through the mechanism · 剖析机制

把界面围绕那个尚未解决的选择来搭建。选中一条候选时，高亮它在原文中的精确区间，同时原文始终显示在字段旁边。下载决定会在本地生成一个 JSON 文件；它不会把值提交到任何地方。用 --approve 再次运行 CLI，即可重新校验并导出已批准的值。

把已批准的候选保留为每个字段中的 `selected` start/end 对。重新打开一份已批准的报告时，该候选的单选框应以选中状态渲染。在没有编辑的情况下再次下载，必须保留原有决定。

使用安全的 DOM 文本操作和转义后的 HTML。文档里可能包含必须当作普通文本处理的标记。把源文档指纹保留在决定文件里，这样即使评审页面一直开着，CLI 也能拒绝过期的选择。

| 产物 | 消费方 |
|---|---|
| review.html | 人类阅读原文并做出选择 |
| approvals.json | CLI 校验选定的区间 |
| review.json approvedValues | 其他应用导入已评审的字段 |

> Build the interface around the unresolved choice. Selecting a candidate highlights its exact source span, while the source remains visible beside the fields. Downloading decisions creates a local JSON file; it does not submit values anywhere. Run the CLI again with --approve to revalidate and export approved values.
> Retain the approved candidate as a `selected` start/end pair in each field. Render that candidate with its radio input checked when reopening an approved report. Downloading again without edits must preserve the decision.
> Use safe DOM text operations and escaped HTML. The document may contain markup that must remain ordinary text. Keep the source fingerprint in the decision file so the CLI can reject stale choices even if the review page was left open.

## Predict before running · 运行前先预测

在浏览器中选中一条 Seats 候选，并验证高亮的文本与它完全一致。先下载并检查决定 JSON，然后再应用它。

```figure
pj-document-extraction-desk-4
```

修改 figure 的输入并核对计算出的值。把其中一个变化的结果对应到你实现中的某一行；figure 是一个解释性模型，不能替代真实程序。

> Select a Seats candidate in the browser and verify the highlighted text exactly matches it. Download and inspect the decision JSON before applying it.
> Change the figure input and check the computed values. Relate one changed result to a line in your implementation; the figure is an explanatory model, not a replacement for the real program.

## Build and verify · 构建并验证

在仓库根目录初始化一次。这一步会复制公开类型、函数存根、一个真实的命令封装和原创示例输入。全新的第一次运行应当失败，因为领域函数还没有实现。

```bash
python3 scripts/project_test.py document-extraction-desk --init my-document-extraction-desk
python3 scripts/project_test.py document-extraction-desk --stage 4 --path my-document-extraction-desk --strict
```

用标准库实现契约。先亲手推演那个完整示例。保持调用方的输入不变，并用可操作的错误信息拒绝畸形数据。测试导入的是你的工作区，绝不是参考实现。

> From the repository root, initialize once. This copies public types, function stubs, a real command wrapper and original sample input. A fresh first-stage run should fail because the domain functions are not implemented.
> Implement the contract with the standard library. Trace the worked example by hand first. Keep caller inputs unchanged and reject malformed data with an actionable error. Tests import your workspace, never the reference solution.

## Hint ladder · 提示阶梯

1. 把控件绑定到偏移量上，而不是复制来的标签上。
2. 对文档内容和序列化后的脚本数据都要转义。
3. 让缺失的字段保持可见，而不是把它们藏起来。

> 1. Bind controls to offsets rather than copied labels.
> 2. Escape both document content and serialized script data.
> 3. Leave missing fields visible instead of hiding them.

## What you should see · 你应看到什么

在这一阶段，评分器会报告第 1 至第 4 阶段的真实通过测试。完成全部四个阶段后，先在提供的示例上运行交付的工具，然后换成你自己的输入：

```bash
cd my-document-extraction-desk
python3 cli.py sample.txt --schema schema.json --output output/review.html
```

最终产物是一个本地 HTML 评审台，它能下载绑定原文的批准决定和一份已批准的 JSON 值映射。打开 HTML 并检查配套的 JSON，不要只看退出码。改动一个输入，并准确解释哪个结果必须随之改变。

> At this stage the grader reports real passing tests for stages 1 through 4. After completing all four stages, run the shipped tool on the supplied sample, then substitute your own input:
> The final artifact is a local HTML review desk that downloads source-bound approval decisions and an approved JSON value map. Open the HTML and inspect the companion JSON instead of trusting an exit code alone. Change one input and explain exactly which result must change.

## Extend it · 扩展练习

编写一个小的消费方，拒绝 status 为 needs_review 的报告。

范围说明：核心只处理 UTF-8 文本和显式标注的字段；它不声称支持 OCR 或 PDF 解析。外部 OCR 或模型适配器可以通过 --proposals 提供提案，但每一条引文和偏移量都会被校验。只有正确的出处，并不能确立正确的字段语义。

主要参考：[Python regular expression match offsets](https://docs.python.org/3/library/re.html#match-objects)。实现和练习数据都是原创教学示例。

> Write a small consumer that refuses reports with status needs_review.
> Scope: The core consumes UTF-8 text and explicitly labelled fields; it does not claim OCR or PDF parsing. External OCR or model adapters may supply proposals through --proposals, but every quote and offset is checked. Correct provenance alone does not establish correct field meaning.
> Primary reference: [Python regular expression match offsets](https://docs.python.org/3/library/re.html#match-objects). The implementation and exercise data are original teaching examples.
