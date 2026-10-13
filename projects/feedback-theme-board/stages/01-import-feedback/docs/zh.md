# Import feedback with stable identities · 用稳定身份导入反馈

**Type:** Build
**Language:** TypeScript
**Stage:** 第 1 / 4 阶段
**Time:** ~2 小时（完成所列前置内容后）
**Prerequisites:** [开发环境](../../../../../phases/00-setup-and-tooling/01-dev-environment/docs/en.md)、[数据管理](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

## What you build · 你要构建什么

本阶段属于 Feedback Theme Board（反馈主题看板）项目：用可检查的短语证据给产品反馈分组，统计去重后的来源数量，并导出本地的 issue 草稿。

你的公开契约是 `parseFeedback(text); validateThemes(value)`。配套提供的 CLI 和示例文件已在你的工作区里；请在 `main.ts` 中实现领域函数。保持它们的签名不变，这样其他应用才能调用同一个边界。

> This stage contributes to Feedback Theme Board: group product feedback with inspectable phrase evidence, count distinct sources, and export local issue drafts.
> Your public contract is `parseFeedback(text); validateThemes(value)`. The supplied CLI and sample files live in your workspace; implement the domain functions in `main.ts`. Keep their signatures so another application can call the same boundary.

## Work through the mechanism · 剖析机制

每条反馈记录需要 ID、原文和来源标签。ID 标识记录本身，来源标签标识用于计数的「声明来源」。二者不可互换：同一个来源可以提交多条记录。

逐物理行读取 JSONL，并为错误信息保留行号，即使空行会被跳过。单独校验主题（theme）配置。一个主题有稳定的 ID、一个显示标题和一小串词组短语。限制输入规模能让教学流程保持可预测。

| 记录 | 来源 | 含义 |
|---|---|---|
| f-1 | interview-a | 一条反馈记录 |
| f-3 | interview-a | 另一条记录，来源标签相同 |
| f-4 | interview-c | 来源标签不同 |

> Each feedback record needs an ID, original text and source label. The ID identifies the record, while the source label identifies the declared origin used for counting. They are not interchangeable: one source can submit multiple records.
> Read JSONL one physical line at a time and preserve the line number for errors, even when blank lines are skipped. Validate the theme configuration separately. A theme has a stable ID, a display title and a small list of word phrases. Bounded input sizes keep the teaching workflow predictable.

## Predict before running · 运行前先预测

在格式非法的 JSON 前插入一个空行，预测报告出的物理行号。然后复制一个 ID，解释它为什么必须失败。

```figure
pj-feedback-theme-board-1
```

修改 figure 的输入并核对计算出的值。把其中一个变化的结果对应到你实现中的某一行；figure 是一个解释性模型，不能替代真实程序。

> Insert a blank line before malformed JSON and predict the reported physical line. Then duplicate an ID and explain why it must fail.
> Change the figure input and check the computed values. Relate one changed result to a line in your implementation; the figure is an explanatory model, not a replacement for the real program.

## Build and verify · 构建并验证

在仓库根目录初始化一次。这一步会复制公开类型、函数存根、一个真实的命令封装和原创示例输入。全新的第一次运行应当失败，因为领域函数还没有实现。

```bash
python3 scripts/project_test.py feedback-theme-board --init my-feedback-theme-board
python3 scripts/project_test.py feedback-theme-board --stage 1 --path my-feedback-theme-board --strict
```

用标准库实现契约。先亲手推演那个完整示例。保持调用方的输入不变，并用可操作的错误信息拒绝畸形数据。测试导入的是你的工作区，绝不是参考实现。

> From the repository root, initialize once. This copies public types, function stubs, a real command wrapper and original sample input. A fresh first-stage run should fail because the domain functions are not implemented.
> Implement the contract with the standard library. Trace the worked example by hand first. Keep caller inputs unchanged and reject malformed data with an actionable error. Tests import your workspace, never the reference solution.

## Hint ladder · 提示阶梯

1. 在过滤空行之前，先统计行号。
2. 拒绝重复的记录 ID。
3. 在匹配任何反馈之前，先校验有界长度的短语。

> 1. Count lines before filtering blank ones.
> 2. Reject duplicate record IDs.
> 3. Validate bounded phrases before matching any feedback.

## What you should see · 你应看到什么

在这一阶段，评分器会报告第 1 至第 1 阶段的真实通过测试。完成全部四个阶段后，先在提供的示例上运行交付的工具，然后换成你自己的输入：

```bash
cd my-feedback-theme-board
node cli.ts sample.jsonl themes.json output
```

最终产物是一个可移植的证据看板、一份 JSON 摘要和若干未发送的 Markdown 调查草稿。打开 HTML 并检查配套的 JSON，不要只看退出码。改动一个输入，并准确解释哪个结果必须随之改变。

> At this stage the grader reports real passing tests for stages 1 through 1. After completing all four stages, run the shipped tool on the supplied sample, then substitute your own input:
> The final artifact is a portable evidence board, JSON summary and unsent Markdown investigation drafts. Open the HTML and inspect the companion JSON instead of trusting an exit code alone. Change one input and explain exactly which result must change.

## Extend it · 扩展练习

为一个导出的支持工单 CSV 编写加载器，让它产生与本契约完全一致的 JSONL。

范围说明：基线只匹配显式的词组短语，不涉及语义情感或真假。去重后的来源标签不是经过核实的真人，也不是市场规模。可选的模型建议会生成一份单独的 proposed 配置，必须经过评审才能使用；任何东西都不会发布到 issue 跟踪器。

主要参考：[JSON text interchange, RFC 8259](https://www.rfc-editor.org/rfc/rfc8259)。实现和练习数据都是原创教学示例。

> Create a loader for an exported support CSV that produces this exact JSONL contract.
> Scope: The baseline matches explicit word phrases, not semantic sentiment or truth. Distinct source labels are not verified people or market size. Optional model suggestions produce a separate proposed configuration that must be reviewed before use; nothing posts to an issue tracker.
> Primary reference: [JSON text interchange, RFC 8259](https://www.rfc-editor.org/rfc/rfc8259). The implementation and exercise data are original teaching examples.
