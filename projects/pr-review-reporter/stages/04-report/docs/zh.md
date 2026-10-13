# Publish a local escaped report · 发布本地转义安全的报告

第 4 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在之前各阶段的契约之上。

## What changes · 变化在哪

渲染一份自包含的报告，包含源码位置、引用的证据、severity 和消息。对源码文本的转义要和对正文一样小心：diff 里可能含有可执行的 HTML。对外发布保持在工具之外。CLI 在本地写出 review.html，并打印一份机器可读的摘要供自动化使用。

本阶段的边界是 `escapeHTML, render`。保持之前各阶段的行为不变：最终评分器会对同一个工作区运行每一个阶段。

> Render a self-contained report with source locations, quoted evidence, severity and message. Escape source text as carefully as prose: a diff can contain executable HTML. Keep external publication outside the tool. The CLI writes review.html locally and prints a machine-readable summary for automation.

> The boundary for this stage is `escapeHTML, render`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 走通一个具体案例

CLI 读入随附的 patch，校验候选，合并重复项，并把匹配的位置写入 review.json、review.html 和 review.sarif。diff 的 SHA-256 把报告绑定到精确的 patch 字节。

```figure
pj-pr-review-reporter-4
```

先改动实验输入，在读它的指标之前自己算出结果。figure 是从这些输入计算出来的；下面的实现测试仍然是判定完成与否的依据。

> The CLI reads a supplied patch, validates candidates, merges duplicates and writes matching locations into review.json, review.html and review.sarif. The diff SHA-256 binds the report to the exact patch bytes.

> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的工作区 `main.ts` 里实现 `escapeHTML, render`。先自己尝试实现契约，之后再去读参考中导出的类型。保留 starter 的公开命名，测试才能调用你的实现。核心函数返回结构化值，不要在核心函数里打印；打印最终结果由 CLI 负责。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只管返回值，把文件输入、参数解析和展示交给随附的 driver。

把源码片段当作不可信的 HTML 对待。Git 模式使用参数数组，所有输出保留在本地；评审产物应当先可被检查，然后才谈公开发布。

> Implement `escapeHTML, render` in your workspace `main.ts`. Read the exported types in the reference only after attempting the contract. Preserve the starter's public names so tests can call your implementation. Return structured values instead of printing inside the core function; the CLI prints the final result.

> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.

> Treat source snippets as untrusted HTML. Use an argument array for Git mode and keep all outputs local; a review artifact should be inspectable before any public posting.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py pr-review-reporter --init learning-artifacts/pr-review-reporter` 初始化一次。然后累积式评分：

```bash
python3 scripts/project_test.py pr-review-reporter --stage 4 --path learning-artifacts/pr-review-reporter --strict
```

全新工作区在你实现契约之前应当失败。每个阶段都完成后，用随附的样例运行你真正的产物：

```bash
cd learning-artifacts/pr-review-reporter
node cli.ts --diff samples/change.diff --output review.json --html review.html --sarif review.sarif
```

> From the repository root, initialize once with `python3 scripts/project_test.py pr-review-reporter --init learning-artifacts/pr-review-reporter`. Then grade cumulatively:

> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

构造一个独立的 held-out patch，包含带引号的文件名和被禁用的 TLS。对照 git diff 核实它的 SARIF region.startLine，然后修改 patch，观察指纹变化。

四个词法检测器给出的是狭窄的评审候选，不是可利用性判决。二进制 diff 和 combined diff 不在范围内。带引号的 Git 路径先解码，再校验目录穿越和锚定。不会向远程发布任何 PR 评论。

> Create an independent held-out patch with a quoted filename and disabled TLS. Verify its SARIF region.startLine against git diff, then change the patch and observe the fingerprint change.

> Four lexical detectors are narrow review candidates, not an exploit verdict. Binary and combined diffs are outside scope. Quoted Git paths are decoded before validating traversal and anchoring. No remote PR comment is posted.

## References · 参考资料

[Git diff format](https://git-scm.com/docs/diff-format)
[Python subprocess and JSON](https://docs.python.org/3/library/json.html)
