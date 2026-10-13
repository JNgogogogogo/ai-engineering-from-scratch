# Parse the untrusted boundary · 解析不受信任的边界

第 1 阶段（共 4 阶段）。开始之前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 1 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

模型响应是一个字节串。把整个字符串按 JSON 解析，拒绝 markdown 包裹和尾部多余文本，并在解析之前限制它的 UTF-8 字节大小。JSON 原始值（primitive）和对象都要接受：决定一个 primitive 是否有用的是 schema，而不是解析器。不要「删文本删到恰好能解析为止」，那样会掩盖真正的输出契约。

本阶段的边界是 `parseJSON`。保持早前阶段的行为不变：最终评分器会在同一个工作区上运行每个阶段。

> A model response is a byte string. Parse the entire string as JSON, reject markdown wrappers and trailing text, and cap its UTF-8 byte size before parsing. Accept JSON primitives as well as objects: the schema, not the parser, determines whether a primitive is useful. Do not remove text until it happens to parse because that hides the actual output contract.
> The boundary for this stage is `parseJSON`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 走一个具体例子

字符串 `{"answer":"yes"}` 是合法 JSON。在它后面追加一句尾随文字，整个响应就变成无效。为了让解析成功而删掉那句话，会掩盖一次供应商契约违约。

```figure
pj-json-schema-output-guard-1
```

先修改 lab 输入并自己算出结果，再去读它的指标。figure 会根据这些输入进行计算；下面的实现测试仍然是完成证据的来源。

> The string `{"answer":"yes"}` is valid JSON. Adding a trailing sentence makes the entire response invalid. Removing that sentence until parsing succeeds would hide a provider contract violation.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的工作区 `main.ts` 里实现 `parseJSON`。先自己尝试实现契约，然后再去读参考中的导出类型。保留起步代码的公开名称，让测试能够调用你的实现。核心函数返回结构化值，不要在核心函数里打印；最终结果由 CLI 打印。

使用[公开 API 契约](../../../API.md)和带类型的起步签名。核心函数只返回值；文件输入、参数解析和展示交给提供的 driver。

在 JSON.parse 之前先统计 UTF-8 字节数。一千个非 ASCII 字符未必占一千个字节。保持 JSON null 与「属性缺失」互相区分。

> Implement `parseJSON` in your workspace `main.ts`. Read the exported types in the reference only after attempting the contract. Preserve the starter's public names so tests can call your implementation. Return structured values instead of printing inside the core function; the CLI prints the final result.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Count UTF-8 bytes before JSON.parse. A thousand non-ASCII characters need not occupy a thousand bytes. Keep JSON null distinct from an absent property.

## Verify and inspect · 验证与检查

从仓库根目录用 `python3 scripts/project_test.py json-schema-output-guard --init learning-artifacts/json-schema-output-guard` 初始化一次。然后按累积方式评分：

```bash
python3 scripts/project_test.py json-schema-output-guard --stage 1 --path learning-artifacts/json-schema-output-guard --strict
```

全新工作区在你实现契约之前应当失败。每个阶段都完成后，用提供的样例运行你的真实产物：

```bash
cd learning-artifacts/json-schema-output-guard
node cli.ts --schema samples/schema.json --attempts samples/attempts.json --output guard.json --html guard.html
```

> From the repository root, initialize once with `python3 scripts/project_test.py json-schema-output-guard --init learning-artifacts/json-schema-output-guard`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

试一个 markdown 代码围栏（code fence）和一个合法的 JSON primitive。围栏在解析阶段失败；primitive 则等待 schema 阶段来决定它是否可用。

> Try a markdown code fence and a valid JSON primitive. The fence fails at parsing; the primitive waits for the schema stage to decide its suitability.

## References · 参考文献

[JSON Schema validation vocabulary](https://json-schema.org/draft/2020-12/json-schema-validation)
[Node TypeScript execution](https://nodejs.org/api/typescript.html)
