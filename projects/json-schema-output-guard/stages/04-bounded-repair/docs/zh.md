# Repair with a finite budget · 用有限预算修复

第 4 阶段（共 4 阶段）。开始之前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 4 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

只把结构化的校验反馈喂给生成回调。在解读一次输出之前先为这次调用计数。被接受后立即停止；最后一次被拒绝的尝试之后返回一个明确的「已耗尽」状态。供应商失败按原样传播，而不是被伪装成 schema 失败。trace 记录每一次尝试，所以第三次响应成功也不会掩盖前两次的契约违约。

本阶段的边界是 `repair`。保持早前阶段的行为不变：最终评分器会在同一个工作区上运行每个阶段。

> Feed only structured validation feedback into a generation callback. Count each call before interpreting its output. Stop immediately after acceptance and return an explicit exhausted state after the final rejected attempt. Provider failures propagate instead of being disguised as schema failures. The trace records each attempt so a successful third response does not conceal two earlier contract violations.
> The boundary for this stage is `repair`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 走一个具体例子

样例先记录 confidence 1.5，再记录 0.8。第一次响应产生一个超出上限（above-maximum）的 issue；回调在 attempt 2 之前收到该 issue。被接受后立即返回，不花费第三次调用。

```figure
pj-json-schema-output-guard-4
```

先修改 lab 输入并自己算出结果，再去读它的指标。figure 会根据这些输入进行计算；下面的实现测试仍然是完成证据的来源。

> The sample records confidence 1.5 then 0.8. The first response emits an above-maximum issue; the callback receives that issue before attempt 2. Acceptance returns immediately and does not spend a third call.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的工作区 `main.ts` 里实现 `repair`。先自己尝试实现契约，然后再去读参考中的导出类型。保留起步代码的公开名称，让测试能够调用你的实现。核心函数返回结构化值，不要在核心函数里打印；最终结果由 CLI 打印。

使用[公开 API 契约](../../../API.md)和带类型的起步签名。核心函数只返回值；文件输入、参数解析和展示交给提供的 driver。

在调用 generate 之前先调用 checkSchema，让坏掉的 schema 无法消耗供应商预算。供应商异常必须保持为供应商失败，而不是被转换成「永远重试」的邀请。

> Call checkSchema before invoking generate so a broken schema cannot consume provider budget. Provider exceptions must remain provider failures, not be converted into an invitation to retry forever.

## Verify and inspect · 验证与检查

从仓库根目录用 `python3 scripts/project_test.py json-schema-output-guard --init learning-artifacts/json-schema-output-guard` 初始化一次。然后按累积方式评分：

```bash
python3 scripts/project_test.py json-schema-output-guard --stage 4 --path learning-artifacts/json-schema-output-guard --strict
```

全新工作区在你实现契约之前应当失败。每个阶段都完成后，用提供的样例运行你的真实产物：

```bash
cd learning-artifacts/json-schema-output-guard
node cli.ts --schema samples/schema.json --attempts samples/attempts.json --output guard.json --html guard.html
```

> From the repository root, initialize once with `python3 scripts/project_test.py json-schema-output-guard --init learning-artifacts/json-schema-output-guard`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

提供两个无效响应，预算设为 2。断言结果为 exhausted 且 trace 恰好两行；然后只把第二个响应替换成合法对象，检查被接受的产物。

这是一个显式的 JSON Schema 子集。$ref、format 和组合器（combinator）都会被拒绝。schema 通过不代表答案在事实上正确。录制的修复不是在线模型调用。

> Supply two invalid responses with budget 2. Assert exhausted and exactly two trace rows; then replace only the second response with a valid object and inspect the accepted artifact.
> This is an explicit JSON Schema subset. $ref, format and combinators are rejected. Schema acceptance does not establish whether an answer is factually correct. Recorded repair is not a live model call.

## References · 参考文献

[JSON Schema validation vocabulary](https://json-schema.org/draft/2020-12/json-schema-validation)
[Node TypeScript execution](https://nodejs.org/api/typescript.html)
