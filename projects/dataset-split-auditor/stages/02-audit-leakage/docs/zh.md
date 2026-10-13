# Audit duplicate and group leakage · 审计重复与分组泄漏

Stage 2 of 4 · 第 2 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

## What changes · 变化在哪

内容泄漏和分组泄漏是两回事。来自同一次事故的两条不同的支持消息，即使文本不同也可能泄漏答案。要同时在各个分区之间跟踪规范化后的内容哈希和 group id。

> Content leakage and group leakage are different. Two distinct support messages from the same incident can leak the answer even when their text differs. Track both normalized content hashes and group ids across partitions.

要返回发生碰撞的哈希和组名，而不只是一个百分比。审查者需要能定位到具体记录。拒绝重复的记录 id，因为它们会让这份证据变得含糊。

> Return the colliding hashes and group names, not just a percentage. The reviewer needs to locate the records. Reject duplicate record ids because they make that evidence ambiguous.

## Work through one concrete case · 走通一个具体案例

train-a 和 test-a 在不同事故之间共享了规范化后的文本。train-a 和 test-b 文本不同，但共享 incident-1。报告保留两份相互独立的证据清单，并带上所涉记录的确切 id。

> train-a and test-a share normalized text across different incidents. train-a and test-b have different text but share incident-1. The report keeps two independent evidence lists with the exact record ids involved.

```figure
pj-dataset-split-auditor-2
```

先修改实验输入、自己算出结果，再去读它的指标。图中的数值由这些输入计算得出；下方的实现测试仍然是完成与否的判定依据。

> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

按照所述契约实现 `audit`。

> Implement `audit` against the stated contract.

使用[公开 API 契约](../../../API.md)和带类型标注的起始签名。核心函数只返回值；文件输入、参数解析和展示一律交给配套的 driver。

> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.

为两侧分别建立「值 → 记录 id」的索引，然后对键求交集。哈希本身只能证明碰撞，却不会告诉新手该去检查哪些源数据行。

> Build value-to-record-id indexes for both sides, then intersect keys. The hash alone proves a collision but does not tell a beginner which source rows to inspect.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py dataset-split-auditor --init learning-artifacts/dataset-split-auditor` 初始化一次，然后按阶段累加评分：

> From the repository root, initialize once with `python3 scripts/project_test.py dataset-split-auditor --init learning-artifacts/dataset-split-auditor`. Then grade cumulatively:

```bash
python3 scripts/project_test.py dataset-split-auditor --stage 2 --path learning-artifacts/dataset-split-auditor --strict
```

全新的工作区在你实现契约之前应当是失败的。所有阶段完成后，用提供的样例运行你自己的工件：

> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

```bash
cd learning-artifacts/dataset-split-auditor
python3 cli.py samples/input.json --output split-audit.json --html split-audit.html
```

## Investigate the failure boundary · 探查失败边界

让两条记录使用同一个 id。要在构造证据之前就拒绝，因为那样给出的定位将是含糊的。

> Give two records the same id. Reject before constructing evidence because the resulting location would be ambiguous.

## References · 参考资料

[主要技术参考](https://scikit-learn.org/stable/common_pitfalls.html)
