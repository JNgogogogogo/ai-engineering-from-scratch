# Extract candidates without losing their evidence · 抽取候选，不丢失证据

**Type:** Build
**Language:** Python
**Stage:** 第 2 / 4 阶段
**Time:** ~2 小时（完成所列前置内容后）
**Prerequisites:** 前一个阶段，以及[开发环境](../../../../../phases/00-setup-and-tooling/01-dev-environment/docs/en.md)、[数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

## What you build · 你要构建什么

本阶段属于 Document Extraction Review Desk（文档抽取评审台）项目：从文本文档中抽取结构化字段，检查精确的原文区间，并在导出前批准含糊的值。

你的公开契约是 `extract_candidates(text, schema)`。配套提供的 CLI 和示例文件已在你的工作区里；请在 `main.py` 中实现领域函数。保持它们的签名不变，这样其他应用才能调用同一个边界。

> This stage contributes to Document Extraction Review Desk: extract structured fields from a text document, inspect exact source spans, and approve ambiguous values before export.
> Your public contract is `extract_candidates(text, schema)`. The supplied CLI and sample files live in your workspace; implement the domain functions in `main.py`. Keep their signatures so another application can call the same boundary.

## Work through the mechanism · 剖析机制

把每条候选当作一个提案（proposal），而不是事实。重复出现的 Seats 标签会产生两条候选，而不是默默选取最后一次出现。每条提案都包含精确的引文和一个半开字符区间：`text[start:end]` 必须等于 quote。

偏移量指的是原文中的 Python Unicode 字符位置。不要先把整个文档规范化、再拿这些偏移量去套原文。修剪（trim）一条候选会同时改变它的 start 和 end，所以要在计入前导空白之后再计算偏移量。

| 源文本 | 候选状态 |
|---|---|
| Seats: 18 | 首个 seats 提案 |
| Seats: 24 | 第二个 seats 提案 |
| Delivery: 2026-10-14 | 一条带日期的提案 |

> Read a candidate as a proposal, not a fact. A repeated Seats label yields two candidates rather than silently choosing the last occurrence. Each proposal contains the exact quote and a half-open character interval: text[start:end] must equal quote.
> Offsets refer to Python Unicode character positions in the original text. Do not normalize the entire document and then use those offsets against the original. Trimming a candidate changes its start and end, so calculate the offset after accounting for leading whitespace.

## Predict before running · 运行前先预测

在 Seats 前面放一个非 ASCII 的名字，然后手动数一遍候选的区间。要验证的是切片行为，而不是按字节数做的算术。

```figure
pj-document-extraction-desk-2
```

修改 figure 的输入并核对计算出的值。把其中一个变化的结果对应到你实现中的某一行；figure 是一个解释性模型，不能替代真实程序。

> Place a non-ASCII name before Seats and manually count the candidate span. Verify slicing, not byte-count arithmetic.
> Change the figure input and check the computed values. Relate one changed result to a line in your implementation; the figure is an explanatory model, not a replacement for the real program.

## Build and verify · 构建并验证

在仓库根目录初始化一次。这一步会复制公开类型、函数存根、一个真实的命令封装和原创示例输入。全新的第一次运行应当失败，因为领域函数还没有实现。

```bash
python3 scripts/project_test.py document-extraction-desk --init my-document-extraction-desk
python3 scripts/project_test.py document-extraction-desk --stage 2 --path my-document-extraction-desk --strict
```

用标准库实现契约。先亲手推演那个完整示例。保持调用方的输入不变，并用可操作的错误信息拒绝畸形数据。测试导入的是你的工作区，绝不是参考实现。

> From the repository root, initialize once. This copies public types, function stubs, a real command wrapper and original sample input. A fresh first-stage run should fail because the domain functions are not implemented.
> Implement the contract with the standard library. Trace the worked example by hand first. Keep caller inputs unchanged and reject malformed data with an actionable error. Tests import your workspace, never the reference solution.

## Hint ladder · 提示阶梯

1. 对捕获到的值使用 match.start。
2. 保留每一个被识别出的出现位置。
3. 在任何批准之前，先把切片与引文比对一遍。

> 1. Use match.start for the captured value.
> 2. Preserve every recognized occurrence.
> 3. Compare the slice to the quote before any approval.

## What you should see · 你应看到什么

在这一阶段，评分器会报告第 1 至第 2 阶段的真实通过测试。完成全部四个阶段后，先在提供的示例上运行交付的工具，然后换成你自己的输入：

```bash
cd my-document-extraction-desk
python3 cli.py sample.txt --schema schema.json --output output/review.html
```

最终产物是一个本地 HTML 评审台，它能下载绑定原文的批准决定和一份已批准的 JSON 值映射。打开 HTML 并检查配套的 JSON，不要只看退出码。改动一个输入，并准确解释哪个结果必须随之改变。

> At this stage the grader reports real passing tests for stages 1 through 2. After completing all four stages, run the shipped tool on the supplied sample, then substitute your own input:
> The final artifact is a local HTML review desk that downloads source-bound approval decisions and an approved JSON value map. Open the HTML and inspect the companion JSON instead of trusting an exit code alone. Change one input and explain exactly which result must change.

## Extend it · 扩展练习

把外部抽取器给出的一条伪造引文喂进来，并要求看到一次可见的拒绝。

范围说明：核心只处理 UTF-8 文本和显式标注的字段；它不声称支持 OCR 或 PDF 解析。外部 OCR 或模型适配器可以通过 --proposals 提供提案，但每一条引文和偏移量都会被校验。只有正确的出处，并不能确立正确的字段语义。

主要参考：[Python regular expression match offsets](https://docs.python.org/3/library/re.html#match-objects)。实现和练习数据都是原创教学示例。

> Feed a fabricated quote from an external extractor and require a visible rejection.
> Scope: The core consumes UTF-8 text and explicitly labelled fields; it does not claim OCR or PDF parsing. External OCR or model adapters may supply proposals through --proposals, but every quote and offset is checked. Correct provenance alone does not establish correct field meaning.
> Primary reference: [Python regular expression match offsets](https://docs.python.org/3/library/re.html#match-objects). The implementation and exercise data are original teaching examples.
