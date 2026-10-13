# Generate narrow review candidates · 生成狭窄的评审候选

第 2 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在之前各阶段的契约之上。

## What changes · 变化在哪

为动态 eval、shell exec、被禁用的 TLS 校验和空的 catch 处理器构建显式的静态检测器。只检查新增行。这些模式产出的是评审候选（review candidates），而不是可利用行为的证明。保持 rule id 稳定，后面的模型评审者报出相同问题时才有可能去重。

本阶段的边界是 `inspect`。保持之前各阶段的行为不变：最终评分器会对同一个工作区运行每一个阶段。

> Build explicit static detectors for dynamic eval, shell exec, disabled TLS validation and empty catch handlers. Inspect only added lines. These patterns produce review candidates rather than proof of exploitable behavior. Keeping rule ids stable makes deduplication possible when a later model reviewer reports the same concern.

> The boundary for this stage is `inspect`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 走通一个具体案例

这个 patch 新增了 eval(input) 和一条写着 // eval(input) is dangerous 的注释。看起来可执行的那一行会产出 dynamic-eval 候选；行首注释则被抑制。

```figure
pj-pr-review-reporter-2
```

先改动实验输入，在读它的指标之前自己算出结果。figure 是从这些输入计算出来的；下面的实现测试仍然是判定完成与否的依据。

> The patch adds eval(input) and a comment saying // eval(input) is dangerous. The executable-looking line emits a dynamic-eval candidate; the leading comment is suppressed.

> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的工作区 `main.ts` 里实现 `inspect`。先自己尝试实现契约，之后再去读参考中导出的类型。保留 starter 的公开命名，测试才能调用你的实现。核心函数返回结构化值，不要在核心函数里打印；打印最终结果由 CLI 负责。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只管返回值，把文件输入、参数解析和展示交给随附的 driver。

稳定的 rule id 让另一位评审者能报告同一个问题而不产生重复的发现。这些正则仍然缺少 AST，会误读字符串或多行构造；在每一份报告里都要写明这个局限。

> Implement `inspect` in your workspace `main.ts`. Read the exported types in the reference only after attempting the contract. Preserve the starter's public names so tests can call your implementation. Return structured values instead of printing inside the core function; the CLI prints the final result.

> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.

> Stable rule ids let another reviewer report the same concern without creating duplicate findings. These regexes still lack an AST and can misread strings or multiline constructs; name that limitation in every report.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py pr-review-reporter --init learning-artifacts/pr-review-reporter` 初始化一次。然后累积式评分：

```bash
python3 scripts/project_test.py pr-review-reporter --stage 2 --path learning-artifacts/pr-review-reporter --strict
```

全新工作区在你实现契约之前应当失败。每个阶段都完成后，用随附的样例运行你真正的产物：

```bash
cd learning-artifacts/pr-review-reporter
node cli.ts --diff samples/change.diff --output review.json --html review.html --sarif review.sarif
```

> From the repository root, initialize once with `python3 scripts/project_test.py pr-review-reporter --init learning-artifacts/pr-review-reporter`. Then grade cumulatively:

> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

试一个包含 eval( 的字符串字面量。决定是增加词法状态解析，还是把它留作一个有记录在案、需要人工评审的候选。

> Try a string literal containing eval(. Decide whether to add lexical-state parsing or leave it as a documented candidate requiring review.

## References · 参考资料

[Git diff format](https://git-scm.com/docs/diff-format)
[Python subprocess and JSON](https://docs.python.org/3/library/json.html)
