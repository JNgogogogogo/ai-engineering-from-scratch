# Walk a schema recursively · 递归遍历 schema

第 2 阶段（共 4 阶段）。开始之前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 2 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

实现 object、array 和 primitive 校验。必填属性用「自身属性」（own-property）语义检查；继承来的属性不满足契约。把 integer 当作 number 的特化（refinement），拒绝非有限数（non-finite），并为每一次失败保留路径。递归下降的深度限制在 32，防止 schema 和值联手把栈耗尽。

本阶段的边界是 `validate`。保持早前阶段的行为不变：最终评分器会在同一个工作区上运行每个阶段。

> Implement object, array and primitive validation. Required properties are checked with own-property semantics. An inherited property does not satisfy the contract. Treat integer as a refinement of number, reject non-finite numbers, and preserve a path for every failure. Bound recursive descent at depth 32 so a schema and value cannot consume the stack indefinitely.
> The boundary for this stage is `validate`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 走一个具体例子

对 schema 的 properties.results.items.type=integer，值 {results:[1,"2"]} 会在 $/results/1 产生一个 issue。文本 "2" 不会仅仅因为「可以强转」就变成数字。

```figure
pj-json-schema-output-guard-2
```

先修改 lab 输入并自己算出结果，再去读它的指标。figure 会根据这些输入进行计算；下面的实现测试仍然是完成证据的来源。

> For schema properties.results.items.type=integer, the value {results:[1,"2"]} produces an issue at $/results/1. The text "2" does not become a number simply because coercion would be possible.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的工作区 `main.ts` 里实现 `validate`。先自己尝试实现契约，然后再去读参考中的导出类型。保留起步代码的公开名称，让测试能够调用你的实现。核心函数返回结构化值，不要在核心函数里打印；最终结果由 CLI 打印。

使用[公开 API 契约](../../../API.md)和带类型的起步签名。核心函数只返回值；文件输入、参数解析和展示交给提供的 driver。

把属性路径沿着递归一路携带下去，而不是失败之后再重建。必填字段用 own-property 检查；即使可选的值缺席，也要拒绝 schema 子树。

> Implement `validate` in your workspace `main.ts`. Read the exported types in the reference only after attempting the contract. Preserve the starter's public names so tests can call your implementation. Return structured values instead of printing inside the core function; the CLI prints the final result.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Carry the property path down recursion rather than rebuilding it after failure. Use own-property checks for required fields, and reject a schema subtree even when its optional value is absent.

## Verify and inspect · 验证与检查

从仓库根目录用 `python3 scripts/project_test.py json-schema-output-guard --init learning-artifacts/json-schema-output-guard` 初始化一次。然后按累积方式评分：

```bash
python3 scripts/project_test.py json-schema-output-guard --stage 2 --path learning-artifacts/json-schema-output-guard --strict
```

全新工作区在你实现契约之前应当失败。每个阶段都完成后，用提供的样例运行你的真实产物：

```bash
cd learning-artifacts/json-schema-output-guard
node cli.ts --schema samples/schema.json --attempts samples/attempts.json --output guard.json --html guard.html
```

> From the repository root, initialize once with `python3 scripts/project_test.py json-schema-output-guard --init learning-artifacts/json-schema-output-guard`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

在 properties.unused 下添加一个不支持的关键字并校验 {}。schema 预检（preflight）必须在宣布空对象合法之前拒绝该配置。

> Add an unsupported keyword under properties.unused and validate {}. Schema preflight must reject the configuration before declaring the empty object valid.

## References · 参考文献

[JSON Schema validation vocabulary](https://json-schema.org/draft/2020-12/json-schema-validation)
[Node TypeScript execution](https://nodejs.org/api/typescript.html)
