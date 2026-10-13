# Verify and merge findings · 校验并合并发现

第 3 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在之前各阶段的契约之上。

## What changes · 变化在哪

要求每个候选都有一个存在的新增行位置，以及一段非空的精确源码子串。拒绝编造的文件、删除行位置、空引用和非法的 severity 值。按 file、line、rule 合并发现；评审者意见不一致时保留更强的 severity。引用门（quote gate）确立的是位置支撑，而不是安全断言本身的真伪——后者仍然需要评审。

本阶段的边界是 `verify, merge`。保持之前各阶段的行为不变：最终评分器会对同一个工作区运行每一个阶段。

> Require an existing added-line location and a nonempty exact source substring for every candidate. Reject fabricated files, deleted-line locations, empty quotes and invalid severity values. Merge findings by file, line and rule; keep the stronger severity when reviewers disagree. The quote gate establishes location support, not the truth of a security claim, which still needs review.

> The boundary for this stage is `verify, merge`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 走通一个具体案例

一条模型建议引用了正确的文件，但引用的却是一行已删除的行。那段文本在新增行证据中不存在，必须拒绝。两条都有支撑的报告针对同一个 (file,line,rule) 时，按更强的 severity 合并。

```figure
pj-pr-review-reporter-3
```

先改动实验输入，在读它的指标之前自己算出结果。figure 是从这些输入计算出来的；下面的实现测试仍然是判定完成与否的依据。

> A model suggestion cites the right file but quotes a deleted line. That text is absent from the added-line evidence and must be rejected. Two supported reports for the same(file,line,rule) merge using the stronger severity.

> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的工作区 `main.ts` 里实现 `verify, merge`。先自己尝试实现契约，之后再去读参考中导出的类型。保留 starter 的公开命名，测试才能调用你的实现。核心函数返回结构化值，不要在核心函数里打印；打印最终结果由 CLI 负责。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只管返回值，把文件输入、参数解析和展示交给随附的 driver。

把接受与拒绝分成两个集合，这样调试一次评审不需要信任每一条建议。把提供的 JSON 当作未知数据：先要求外层数组，然后在访问字段之前拒绝 null、数组和非对象条目。要求 file、quote、rule、message 为字符串字段，line 为正整数，severity 在支持范围内，且 trim 后的 quote、rule、message 非空。畸形条目保留在 `rejected` 里；合法的相邻条目必须仍然能进入渲染和 SARIF 导出。

> Implement `verify, merge` in your workspace `main.ts`. Read the exported types in the reference only after attempting the contract. Preserve the starter's public names so tests can call your implementation. Return structured values instead of printing inside the core function; the CLI prints the final result.

> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.

> Separate accepted and rejected collections so debugging a review does not require trusting every suggestion. Treat supplied JSON as unknown data: require an outer array, then reject nulls, arrays and non-object entries before accessing fields. Require string file, quote, rule and message fields, a positive integer line, a supported severity, and nonempty trimmed quote, rule and message. Preserve malformed entries in `rejected`; valid neighbors must still reach rendering and SARIF export.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py pr-review-reporter --init learning-artifacts/pr-review-reporter` 初始化一次。然后累积式评分：

```bash
python3 scripts/project_test.py pr-review-reporter --stage 3 --path learning-artifacts/pr-review-reporter --strict
```

全新工作区在你实现契约之前应当失败。每个阶段都完成后，用随附的样例运行你真正的产物：

```bash
cd learning-artifacts/pr-review-reporter
node cli.ts --diff samples/change.diff --output review.json --html review.html --sarif review.sarif
```

> From the repository root, initialize once with `python3 scripts/project_test.py pr-review-reporter --init learning-artifacts/pr-review-reporter`. Then grade cumulatively:

> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

只改动一个合法候选的行号。确认别处出现的相同引用不会让这条发现悄悄挪位。

> Change only the line number in a valid candidate. Confirm that an identical quote elsewhere does not silently move the finding.

## References · 参考资料

[Git diff format](https://git-scm.com/docs/diff-format)
[Python subprocess and JSON](https://docs.python.org/3/library/json.html)
