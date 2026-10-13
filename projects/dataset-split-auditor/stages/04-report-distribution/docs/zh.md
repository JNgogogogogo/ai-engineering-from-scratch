# Report split size and leakage together · 把划分规模与泄漏放进同一份报告

Stage 4 of 4 · 第 4 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

## What changes · 变化在哪

当几乎所有记录都落进训练集时，一次「干净」的划分仍然可能毫无用处。要把行数、组数和泄漏情况放进同一份工件。把这些数字放在一起，能防止「无泄漏」的结论掩盖一个空的测试集。

> A clean split can still be useless when nearly all records land in training. Report row counts, group counts, and leakage in one artifact. Keeping these numbers together prevents a clean-leakage claim from hiding an empty test set.

这个 checker 不为统计代表性背书。时间相关的任务往往需要按时间顺序划分，本项目刻意把它留作后续扩展。

> The checker does not certify statistical representativeness. Time-dependent tasks often need a chronological split, which this project deliberately leaves as a later extension.

## Work through one concrete case · 走通一个具体案例

一份零泄漏但 test_rows=0 的报告是不可用的。提供的脏 fixture 两个分区都有，但仍然失败，因为内容和分组证据还在。这是同一个 gate 结果背后的两类不同原因。

> A report with zero leaks and test_rows=0 is unusable. The supplied dirty fixture has both partitions but still fails because content and group evidence remain. These are distinct reasons for the same gate outcome.

```figure
pj-dataset-split-auditor-4
```

先修改实验输入、自己算出结果，再去读它的指标。图中的数值由这些输入计算得出；下方的实现测试仍然是完成与否的判定依据。

> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

按照所述契约实现 `summarize`。

> Implement `summarize` against the stated contract.

使用[公开 API 契约](../../../API.md)和带类型标注的起始签名。核心函数只返回值；文件输入、参数解析和展示一律交给配套的 driver。

> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.

CLI 把 summarize 与溯源索引组合起来，并可选地返回 exit 2。CI 任务即使在 gate 失败时也应保留 JSON 工件，这样审查者才能定位问题。

> The CLI composes summarize with provenance indexes and optionally returns exit 2. A CI job should retain the JSON artifact even when the gate fails so a reviewer can locate the problem.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py dataset-split-auditor --init learning-artifacts/dataset-split-auditor` 初始化一次，然后按阶段累加评分：

> From the repository root, initialize once with `python3 scripts/project_test.py dataset-split-auditor --init learning-artifacts/dataset-split-auditor`. Then grade cumulatively:

```bash
python3 scripts/project_test.py dataset-split-auditor --stage 4 --path learning-artifacts/dataset-split-auditor --strict
```

全新的工作区在你实现契约之前应当是失败的。所有阶段完成后，用提供的样例运行你自己的工件：

> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

```bash
cd learning-artifacts/dataset-split-auditor
python3 cli.py samples/input.json --output split-audit.json --html split-audit.html
```

## Investigate the failure boundary · 探查失败边界

构造一对确认干净的记录，运行 --check 并确认 exit 0。再用一个新 id 加入一份规范化后的副本，确认 exit 2 且工件里同时包含两个原始 id。

> Create an authored clean pair, run --check and confirm exit 0. Add a normalized copy under a new id and confirm exit 2 with both original ids in the artifact.

规范化找到的是规范化后完全一致的副本，而不是改写。稳定的组哈希不保证类别均衡，也不保证时间感知的评估。导出的分区里仍然包含源文本。

> Normalization finds exact normalized copies, not paraphrases. Stable group hashing does not guarantee balanced classes or time-aware evaluation. Source text remains present in exported partitions.

## References · 参考资料

[主要技术参考](https://scikit-learn.org/stable/common_pitfalls.html)
