# Fingerprint normalized records · 为规范化后的记录建立指纹

Stage 1 of 4 · 第 1 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

## What changes · 变化在哪

随机划分可能把同一个样本以不同的 id 同时放进 train 和 test。在哈希内容之前，先做 Unicode、空白和大小写的规范化。把 id 与内容指纹分开保存，这样即使记录改了名也仍然会撞车。

> A random split can place the same example in both train and test under different ids. Normalize Unicode, whitespace, and case before hashing the content. Keep ids separate from content fingerprints so renamed records still collide.

规范化是一项显式声明的策略。它检测的是规范化后完全相同的重复，而不是改写、图片或语义等价的代码。当输入空间可以被猜到时，哈希并不能让内容匿名。

> Normalization is an explicit policy. It detects exact normalized duplicates, not paraphrases, images, or semantically equivalent code. Hashing does not make content anonymous when the input space is guessable.

## Work through one concrete case · 走通一个具体案例

字符串 "Ｒetry  NOW" 和 "retry now" 在 NFKC、大小写折叠和空白折叠之后得到相同的文本。它们的记录 id 可以不同，但内容指纹必须一致。

> The strings "Ｒetry  NOW" and "retry now" normalize to the same text under NFKC, case folding and whitespace collapse. Their record ids may differ, but their content fingerprints must agree.

```figure
pj-dataset-split-auditor-1
```

先修改实验输入、自己算出结果，再去读它的指标。图中的数值由这些输入计算得出；下方的实现测试仍然是完成与否的判定依据。

> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

按照所述契约实现 `fingerprint`。

> Implement `fingerprint` against the stated contract.

使用[公开 API 契约](../../../API.md)和带类型标注的起始签名。核心函数只返回值；文件输入、参数解析和展示一律交给配套的 driver。

> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.

先做规范化，再做 UTF-8 编码和哈希。绝不要哈希字典表示——字典的键序和附带的元数据会独立于内容而变化。

> Apply normalization before UTF-8 encoding and hashing. Never hash a dictionary representation, whose ordering and incidental metadata change independently of content.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py dataset-split-auditor --init learning-artifacts/dataset-split-auditor` 初始化一次，然后按阶段累加评分：

> From the repository root, initialize once with `python3 scripts/project_test.py dataset-split-auditor --init learning-artifacts/dataset-split-auditor`. Then grade cumulatively:

```bash
python3 scripts/project_test.py dataset-split-auditor --stage 1 --path learning-artifacts/dataset-split-auditor --strict
```

全新的工作区在你实现契约之前应当是失败的。所有阶段完成后，用提供的样例运行你自己的工件：

> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

```bash
cd learning-artifacts/dataset-split-auditor
python3 cli.py samples/input.json --output split-audit.json --html split-audit.html
```

## Investigate the failure boundary · 探查失败边界

试试 "retry now!"。标点仍然是有意义的，所以本契约不应声称它与 "retry now" 匹配。

> Try "retry now!". Punctuation remains meaningful, so this contract should not claim that it matches "retry now".

## References · 参考资料

[主要技术参考](https://scikit-learn.org/stable/common_pitfalls.html)
