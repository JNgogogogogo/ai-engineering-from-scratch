# Define the fields before extracting values · 在抽取值之前先定义字段

**Type:** Build
**Language:** Python
**Stage:** 第 1 / 4 阶段
**Time:** ~2 小时（完成所列前置内容后）
**Prerequisites:** [开发环境](../../../../../phases/00-setup-and-tooling/01-dev-environment/docs/en.md)、[数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

## What you build · 你要构建什么

本阶段属于 Document Extraction Review Desk（文档抽取评审台）项目：从文本文档中抽取结构化字段，检查精确的原文区间，并在导出前批准含糊的值。

你的公开契约是 `validate_schema(schema)`。配套提供的 CLI 和示例文件已在你的工作区里；请在 `main.py` 中实现领域函数。保持它们的签名不变，这样其他应用才能调用同一个边界。

> This stage contributes to Document Extraction Review Desk: extract structured fields from a text document, inspect exact source spans, and approve ambiguous values before export.
> Your public contract is `validate_schema(schema)`. The supplied CLI and sample files live in your workspace; implement the domain functions in `main.py`. Keep their signatures so another application can call the same boundary.

## Work through the mechanism · 剖析机制

schema 是文档阅读方与消费应用之间的约定。每个字段都有一个稳定的机器名、可接受的行标签、一个类型和一个必填标志。一个标签只能属于一个字段；否则，还没轮到模型出场，同一行原文就会有两个互不相容的去处。

把 schema 校验和抽取分开。缺失必填值是文档的问题，而字段类型非法是编写 schema 的问题。这一区分带来的是有用的错误信息，而不是一个看似成功的空答案。

| 字段 | 标签 | 类型 | 必填 |
|---|---|---|---|
| requester | Requester, Requested by | text | yes |
| seats | Seats, Attendees | integer | yes |
| delivery | Delivery, Delivery date | date | yes |

> The schema is the agreement between the document reader and the consuming application. Each field has a stable machine name, accepted line labels, a type and a required flag. A label may belong to only one field; otherwise a source line would have two incompatible destinations before any model is involved.
> Keep schema validation separate from extraction. A missing required value is a document issue, while an invalid field type is an authoring issue. That distinction produces a useful error rather than an empty answer that looks successful.

## Predict before running · 运行前先预测

把标签 Seats 同时加到两个字段上，然后预测程序应当在哪里停下。不需要读任何源码就能发现这个冲突。

```figure
pj-document-extraction-desk-1
```

修改 figure 的输入并核对计算出的值。把其中一个变化的结果对应到你实现中的某一行；figure 是一个解释性模型，不能替代真实程序。

> Add the label Seats to two fields and predict where the program should stop. No source reading is needed to find this conflict.
> Change the figure input and check the computed values. Relate one changed result to a line in your implementation; the figure is an explanatory model, not a replacement for the real program.

## Build and verify · 构建并验证

在仓库根目录初始化一次。这一步会复制公开类型、函数存根、一个真实的命令封装和原创示例输入。全新的第一次运行应当失败，因为领域函数还没有实现。

```bash
python3 scripts/project_test.py document-extraction-desk --init my-document-extraction-desk
python3 scripts/project_test.py document-extraction-desk --stage 1 --path my-document-extraction-desk --strict
```

用标准库实现契约。先亲手推演那个完整示例。保持调用方的输入不变，并用可操作的错误信息拒绝畸形数据。测试导入的是你的工作区，绝不是参考实现。

> From the repository root, initialize once. This copies public types, function stubs, a real command wrapper and original sample input. A fresh first-stage run should fail because the domain functions are not implemented.
> Implement the contract with the standard library. Trace the worked example by hand first. Keep caller inputs unchanged and reject malformed data with an actionable error. Tests import your workspace, never the reference solution.

## Hint ladder · 提示阶梯

1. 在遍历标签之前，先校验字段的形状。
2. 把字段名和规范化后的标签身份分开跟踪。
3. 保留用于显示的标签，比较时使用大小写折叠后的形式。

> 1. Validate field shapes before iterating labels.
> 2. Track field names and normalized label identities separately.
> 3. Preserve display labels while comparing their case-folded form.

## What you should see · 你应看到什么

在这一阶段，评分器会报告第 1 至第 1 阶段的真实通过测试。完成全部四个阶段后，先在提供的示例上运行交付的工具，然后换成你自己的输入：

```bash
cd my-document-extraction-desk
python3 cli.py sample.txt --schema schema.json --output output/review.html
```

最终产物是一个本地 HTML 评审台，它能下载绑定原文的批准决定和一份已批准的 JSON 值映射。打开 HTML 并检查配套的 JSON，不要只看退出码。改动一个输入，并准确解释哪个结果必须随之改变。

> At this stage the grader reports real passing tests for stages 1 through 1. After completing all four stages, run the shipped tool on the supplied sample, then substitute your own input:
> The final artifact is a local HTML review desk that downloads source-bound approval decisions and an approved JSON value map. Open the HTML and inspect the companion JSON instead of trusting an exit code alone. Change one input and explain exactly which result must change.

## Extend it · 扩展练习

添加一个可选的 contact 字段，并说明为什么它的缺席不应阻碍必填字段的完成。

范围说明：核心只处理 UTF-8 文本和显式标注的字段；它不声称支持 OCR 或 PDF 解析。外部 OCR 或模型适配器可以通过 --proposals 提供提案，但每一条引文和偏移量都会被校验。只有正确的出处，并不能确立正确的字段语义。

主要参考：[Python regular expression match offsets](https://docs.python.org/3/library/re.html#match-objects)。实现和练习数据都是原创教学示例。

> Add an optional contact field and show why its absence must not block required-field completion.
> Scope: The core consumes UTF-8 text and explicitly labelled fields; it does not claim OCR or PDF parsing. External OCR or model adapters may supply proposals through --proposals, but every quote and offset is checked. Correct provenance alone does not establish correct field meaning.
> Primary reference: [Python regular expression match offsets](https://docs.python.org/3/library/re.html#match-objects). The implementation and exercise data are original teaching examples.
