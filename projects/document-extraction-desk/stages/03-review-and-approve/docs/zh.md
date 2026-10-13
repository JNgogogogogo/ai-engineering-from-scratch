# Bind approval to one document version · 把批准绑定到文档的某一个版本

**Type:** Build
**Language:** Python
**Stage:** 第 3 / 4 阶段
**Time:** ~2 小时（完成所列前置内容后）
**Prerequisites:** 前一个阶段，以及[开发环境](../../../../../phases/00-setup-and-tooling/01-dev-environment/docs/en.md)、[数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

## What you build · 你要构建什么

本阶段属于 Document Extraction Review Desk（文档抽取评审台）项目：从文本文档中抽取结构化字段，检查精确的原文区间，并在导出前批准含糊的值。

你的公开契约是 `typed_value(quote, kind); review_document(text, schema, candidates, decisions=None)`。配套提供的 CLI 和示例文件已在你的工作区里；请在 `main.py` 中实现领域函数。保持它们的签名不变，这样其他应用才能调用同一个边界。

> This stage contributes to Document Extraction Review Desk: extract structured fields from a text document, inspect exact source spans, and approve ambiguous values before export.
> Your public contract is `typed_value(quote, kind); review_document(text, schema, candidates, decisions=None)`. The supplied CLI and sample files live in your workspace; implement the domain functions in `main.py`. Keep their signatures so another application can call the same boundary.

## Work through the mechanism · 剖析机制

类型校验检查一条引文能否变成所请求的值：ISO 日期必须是真实存在的日历日期，数字必须是有限值。证据校验检查引文确实存在于声明的位置。至于这个值是否属于目标字段，仍然由人来决定。这是三个互相独立的判断。

对 `number`，接受 Python `float` 的文本语法，包括符号、小数部分、指数和数字之间的下划线：`-2.5`、`.5`、`1e3` 和 `1_000` 都是有效的。逗号和单位后缀（例如 `1,000` 或 `3.5 kg`）是无效的。拒绝非有限的结果，包括 `inf`、`NaN` 以及 `1e309` 这样的溢出。`integer` 类型仍然更严格：一个可选符号后跟数字。

批准（approval）里包含源文档的指纹（fingerprint）以及每个字段选定的 start/end 对。文档一旦改变，旧的批准就不能在原位置悄悄认可一个不同的值。missing、invalid、ambiguous、proposed、approved 这些状态让整个工作流保持可检查。

| 情形 | 状态 | 导出后果 |
|---|---|---|
| 一条有效引文，尚无决定 | proposed | 未获批准 |
| 两条 Seats 引文 | ambiguous | 由评审者选择 |
| 选定的区间且指纹匹配 | approved | 值可以导出 |

> Type validation checks whether a quote can become the requested value: an ISO date must be a real calendar date and a number must be finite. Evidence validation checks that the quote exists at the declared position. A human still decides whether that value belongs to the intended field. These are three separate judgments.
> For `number`, accept Python `float` text syntax, including signs, decimal fractions, exponents and underscores between digits: `-2.5`, `.5`, `1e3` and `1_000` are valid. Commas and unit suffixes such as `1,000` or `3.5 kg` are invalid. Reject nonfinite results, including `inf`, `NaN` and overflow such as `1e309`. The `integer` type remains stricter: an optional sign followed by digits.
> Approval contains the source fingerprint and the selected start/end pair for each field. If the document changes, the old decision cannot silently approve a different value at the same location. Missing, invalid, ambiguous, proposed and approved states keep the workflow inspectable.

## Predict before running · 运行前先预测

批准 18 个席位，然后在文档顶部插入一行，预测为什么旧的批准必须被拒绝。

```figure
pj-document-extraction-desk-3
```

修改 figure 的输入并核对计算出的值。把其中一个变化的结果对应到你实现中的某一行；figure 是一个解释性模型，不能替代真实程序。

> Approve 18 seats, insert a new line at the top, and predict why the old approval must be rejected.
> Change the figure input and check the computed values. Relate one changed result to a line in your implementation; the figure is an explanatory model, not a replacement for the real program.

## Build and verify · 构建并验证

在仓库根目录初始化一次。这一步会复制公开类型、函数存根、一个真实的命令封装和原创示例输入。全新的第一次运行应当失败，因为领域函数还没有实现。

```bash
python3 scripts/project_test.py document-extraction-desk --init my-document-extraction-desk
python3 scripts/project_test.py document-extraction-desk --stage 3 --path my-document-extraction-desk --strict
```

用标准库实现契约。先亲手推演那个完整示例。保持调用方的输入不变，并用可操作的错误信息拒绝畸形数据。测试导入的是你的工作区，绝不是参考实现。

> From the repository root, initialize once. This copies public types, function stubs, a real command wrapper and original sample input. A fresh first-stage run should fail because the domain functions are not implemented.
> Implement the contract with the standard library. Trace the worked example by hand first. Keep caller inputs unchanged and reject malformed data with an actionable error. Tests import your workspace, never the reference solution.

## Hint ladder · 提示阶梯

1. 在读取选择之前，先检查指纹。
2. 一次选择必须恰好指向一个合法的既有候选。
3. 就绪状态要基于全部必填字段来计算，而不是基于决定的数量。

> 1. Check the fingerprint before reading choices.
> 2. A choice must identify one valid existing candidate.
> 3. Compute readiness from all required fields, not the count of decisions.

## What you should see · 你应看到什么

在这一阶段，评分器会报告第 1 至第 3 阶段的真实通过测试。完成全部四个阶段后，先在提供的示例上运行交付的工具，然后换成你自己的输入：

```bash
cd my-document-extraction-desk
python3 cli.py sample.txt --schema schema.json --output output/review.html
```

最终产物是一个本地 HTML 评审台，它能下载绑定原文的批准决定和一份已批准的 JSON 值映射。打开 HTML 并检查配套的 JSON，不要只看退出码。改动一个输入，并准确解释哪个结果必须随之改变。

> At this stage the grader reports real passing tests for stages 1 through 3. After completing all four stages, run the shipped tool on the supplied sample, then substitute your own input:
> The final artifact is a local HTML review desk that downloads source-bound approval decisions and an approved JSON value map. Open the HTML and inspect the companion JSON instead of trusting an exit code alone. Change one input and explain exactly which result must change.

## Extend it · 扩展练习

增加一个单独的评审者身份和决定时间戳，但不要把其中任何一个当作密码学意义上的认证。

范围说明：核心只处理 UTF-8 文本和显式标注的字段；它不声称支持 OCR 或 PDF 解析。外部 OCR 或模型适配器可以通过 --proposals 提供提案，但每一条引文和偏移量都会被校验。只有正确的出处，并不能确立正确的字段语义。

主要参考：[Python regular expression match offsets](https://docs.python.org/3/library/re.html#match-objects)。实现和练习数据都是原创教学示例。

> Add a separate reviewer identity and decision timestamp without treating either as cryptographic authentication.
> Scope: The core consumes UTF-8 text and explicitly labelled fields; it does not claim OCR or PDF parsing. External OCR or model adapters may supply proposals through --proposals, but every quote and offset is checked. Correct provenance alone does not establish correct field meaning.
> Primary reference: [Python regular expression match offsets](https://docs.python.org/3/library/re.html#match-objects). The implementation and exercise data are original teaching examples.
