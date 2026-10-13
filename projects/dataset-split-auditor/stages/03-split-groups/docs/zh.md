# Split groups with stable hashing · 用稳定哈希划分组

Stage 3 of 4 · 第 3 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

## What changes · 变化在哪

划分的对象是组，不是行。把 seed 和 group id 一起哈希成一个稳定的分数，再与要求的 test 占比比较。同一组内的每一行都遵循同一个决定，与输入顺序无关。

> Partition groups, not rows. Hash the seed and group id into a stable fraction and compare it with the requested test fraction. Every row in a group follows the same decision, regardless of input order.

哈希划分给出的是期望占比，而不是精确的行数。小数据集可能出现空分区。要如实报告这一点，而不是挪动一行去凑数、破坏组隔离。

> Hash partitioning gives an expected fraction rather than an exact row count. Small datasets may have an empty partition. Report that honestly instead of moving one row and breaking group isolation.

## Work through one concrete case · 走通一个具体案例

如果 incident-A 包含九条消息、incident-B 只有一条，50% 的组级划分可能得到九条训练行和一条测试行。为了平衡数量而挪动一条消息，就会重新引入事故泄漏。

> If incident-A contains nine messages and incident-B contains one, a50 percent group split can yield nine train rows and one test row. Moving one message to balance counts would reintroduce incident leakage.

```figure
pj-dataset-split-auditor-3
```

先修改实验输入、自己算出结果，再去读它的指标。图中的数值由这些输入计算得出；下方的实现测试仍然是完成与否的判定依据。

> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

按照所述契约实现 `split_groups`。

> Implement `split_groups` against the stated contract.

使用[公开 API 契约](../../../API.md)和带类型标注的起始签名。核心函数只返回值；文件输入、参数解析和展示一律交给配套的 driver。

> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.

划分决定只能由 seed 加 group 推导，绝不能来自输入行顺序。把输入列表反过来可以改变行序，但每个 id 的分区归属必须保持不变。

> Derive the partition decision from seed plus group, never input row order. Reversing the input list may change row order but must preserve each id's partition membership.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py dataset-split-auditor --init learning-artifacts/dataset-split-auditor` 初始化一次，然后按阶段累加评分：

> From the repository root, initialize once with `python3 scripts/project_test.py dataset-split-auditor --init learning-artifacts/dataset-split-auditor`. Then grade cumulatively:

```bash
python3 scripts/project_test.py dataset-split-auditor --stage 3 --path learning-artifacts/dataset-split-auditor --strict
```

全新的工作区在你实现契约之前应当是失败的。所有阶段完成后，用提供的样例运行你自己的工件：

> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

```bash
cd learning-artifacts/dataset-split-auditor
python3 cli.py samples/input.json --output split-audit.json --html split-audit.html
```

## Investigate the failure boundary · 探查失败边界

生成 20 个大小不同的组，更换 seed，分别比较组隔离性和行数均衡。

> Generate 20 groups with different sizes, change the seed and compare group isolation and row balance separately.

## References · 参考资料

[主要技术参考](https://scikit-learn.org/stable/common_pitfalls.html)
