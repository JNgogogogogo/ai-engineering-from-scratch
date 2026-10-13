# Validate reviewer evidence · 校验审查者的证据

第 1 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 1 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

要求：文件必须存在于给定的快照（snapshot）中；行号是从 1 开始（one-based）的正整数；quote 是精确匹配且非空的原文；rule id 保持稳定；severity 取 1 到 3。证据校验由所有 reviewer 共享。它保护聚合边界免遭伪造位置的攻击，但「达成一致 + 有引文」仍然不能证明一个 finding 是正确的。

本阶段的边界是 `validateFinding`。保持之前阶段的行为不变：最终评分器会在同一个 workspace 上运行每一个阶段。

> Require a file present in the supplied snapshot, a positive one-based line, an exact nonempty quote, a stable rule id and a severity from one through three. Evidence validation is shared across all reviewers. It protects the aggregation boundary against fabricated locations, but agreement and quoted text still do not prove a finding is correct.

## Work through one concrete case · 走一遍具体案例

一个 reviewer 声称 `run.ts` 第 99 行含有 `eval(input)`，但给定的快照只有三行。要在统计支持票之前就拒绝它，哪怕第二个 reviewer 重复了同一个伪造位置。

```figure
pj-multi-agent-code-review-panel-1
```

修改实验（lab）的输入，先自己算出结果，再去看它的指标。图中数字由这些输入计算而来；下面的实现测试仍然是完成与否的证据来源。

> A reviewer claims run.ts line 99 contains eval(input), but the supplied snapshot has three lines. Reject it before counting support, even if a second reviewer repeats the same fabricated location. ... Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的 workspace `main.ts` 里实现 `validateFinding`。先自己尝试契约，之后再去读参考实现中导出的类型。保留起始代码的公开名称，测试才能调用你的实现。核心函数返回结构化值，不要在核心函数内部打印；最终结果由 CLI 打印。

使用[公开的 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示交给随附的 driver。

用自有属性（own-property）查找文件，并把行号按一基（one-based）转换。精确且非空的 quote 只佐证位置；它证明不了 severity，也证明不了因果断言。

> Implement `validateFinding` in your workspace `main.ts`. ... Use an own-property file lookup and one-based line conversion. An exact nonempty quote supports location only; it does not prove the severity or causal claim.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py multi-agent-code-review-panel --init learning-artifacts/multi-agent-code-review-panel` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py multi-agent-code-review-panel --stage 1 --path learning-artifacts/multi-agent-code-review-panel --strict
```

全新的 workspace 在你实现契约之前应当判为失败。每个阶段完成后，用随附的样例运行你的真实产物：

```bash
cd learning-artifacts/multi-agent-code-review-panel
node cli.ts --input samples/review.json --output panel.json --html panel.html
```

> From the repository root, initialize once with `python3 scripts/project_test.py multi-agent-code-review-panel --init learning-artifacts/multi-agent-code-review-panel`. Then grade cumulatively ... A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample.

## Investigate the failure boundary · 探查失败边界

把一条录制好的外部 finding 通过 CLI 喂给一份已变更的源快照。它必须和本地 reviewer 一样栽在同一个 quote 门禁上。

> Feed a recorded external finding through the CLI against a changed source snapshot. It must fail the same quote gate as local reviewers.

## References · 参考资料

[Node 中的 AbortController](https://nodejs.org/api/globals.html#class-abortcontroller)
[Node 测试运行器](https://nodejs.org/api/test.html)
