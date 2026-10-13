# Reject ambiguous and unsupported contracts · 拒绝含糊与不受支持的契约

第 3 阶段（共 4 阶段）。开始之前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 3 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

增加数值边界、enum 成员、Unicode 最小字符串长度、数组边界和封闭对象（closed objects）。在属性路径里转义斜杠和波浪号。教育子集之外的关键字属于配置错误，而不是静默成功。本实现有意不声称完整符合 JSON Schema：引用（references）、格式（formats）和组合器（combinators）还需要额外的工作。

本阶段的边界是 `validate, guard`。保持早前阶段的行为不变：最终评分器会在同一个工作区上运行每个阶段。

> Add numeric bounds, enum membership, minimum Unicode string length, array bounds, and closed objects. Escape slash and tilde inside property paths. A keyword outside this educational subset is a configuration error, not silent success. This implementation intentionally does not claim complete JSON Schema conformance: references, formats and combinators require additional work.
> The boundary for this stage is `validate, guard`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 走一个具体例子

必需键 a/b~c 会被报告在 $/a~1b~0c。先转义 ~，再转义 /；顺序颠倒或漏掉转义会让诊断指到错误的字段。最小字符串长度按 Unicode 码点（code point）计数。

```figure
pj-json-schema-output-guard-3
```

先修改 lab 输入并自己算出结果，再去读它的指标。figure 会根据这些输入进行计算；下面的实现测试仍然是完成证据的来源。

> A required key a/b~c is reported at $/a~1b~0c. Escape ~ first, then /; reversing or skipping escapes makes the diagnostic point at the wrong field. A minimum string length counts Unicode code points.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的工作区 `main.ts` 里实现 `validate, guard`。先自己尝试实现契约，然后再去读参考中的导出类型。保留起步代码的公开名称，让测试能够调用你的实现。核心函数返回结构化值，不要在核心函数里打印；最终结果由 CLI 打印。

使用[公开 API 契约](../../../API.md)和带类型的起步签名。核心函数只返回值；文件输入、参数解析和展示交给提供的 driver。

把不受支持的词汇表（vocabulary）当作配置异常，普通的值不匹配则作为 Issue[] 结果返回。在查看模型数据之前，先校验所有 schema 形状，包括 minItems 和嵌套 properties。

> Treat unsupported vocabulary as a configuration exception and ordinary value mismatches as Issue[] results. Validate all schema shapes, including minItems and nested properties, before inspecting model data.

## Verify and inspect · 验证与检查

从仓库根目录用 `python3 scripts/project_test.py json-schema-output-guard --init learning-artifacts/json-schema-output-guard` 初始化一次。然后按累积方式评分：

```bash
python3 scripts/project_test.py json-schema-output-guard --stage 3 --path learning-artifacts/json-schema-output-guard --strict
```

全新工作区在你实现契约之前应当失败。每个阶段都完成后，用提供的样例运行你的真实产物：

```bash
cd learning-artifacts/json-schema-output-guard
node cli.ts --schema samples/schema.json --attempts samples/attempts.json --output guard.json --html guard.html
```

> From the repository root, initialize once with `python3 scripts/project_test.py json-schema-output-guard --init learning-artifacts/json-schema-output-guard`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

用一个 items 包含 $ref 的空数组。空输入不得绕过 schema 词汇校验。

> Use an empty array with items containing $ref. Empty input must not bypass schema-vocabulary validation.

## References · 参考文献

[JSON Schema validation vocabulary](https://json-schema.org/draft/2020-12/json-schema-validation)
[Node TypeScript execution](https://nodejs.org/api/typescript.html)
