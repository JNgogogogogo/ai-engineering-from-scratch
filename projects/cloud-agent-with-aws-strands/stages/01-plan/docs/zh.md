# Validate a scoped cloud inspection plan · 校验带范围约束的云端巡检计划

Stage 1 of 4 · 第 1 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

## What changes · 变化在哪

模型只负责提出意图；由确定性的 validator（验证器）来授予权力。只接受调用方 scope 内显式点名的 read 操作和 resource id。拒绝未知的键和超大的计划，让模型额外生成的指令无法悄悄变成可执行的参数。

> The model proposes intent; a deterministic validator grants authority. Accept only explicitly named read operations and resource ids from the caller scope. Reject unknown keys and oversized plans so additional model-generated instructions cannot silently become executable parameters.

## Work through one concrete case · 走通一个具体案例

一份 checkout 事故计划包含 metrics.read checkout 和 logs.read checkout，两者都落在 scope={checkout} 之内。如果把 logs.read 换成 logs.delete，就必须在第一次 provider 调用之前拒绝整个提案。

> A checkout incident plan contains metrics.read checkout and logs.read checkout. Both fit scope={checkout}. Replacing logs.read with logs.delete must reject the complete proposal before the first provider call.

```figure
pj-cloud-agent-with-aws-strands-1
```

先修改实验输入、自己算出结果，再去读它的指标。图中的数值由这些输入计算得出；下方的实现测试仍然是完成与否的判定依据。

> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

实现 `plan.py` 中的 `validate_plan`。这个工件是 Cloud Agent With AWS Strands 的第 1 阶段产物：它消费显式输入，返回一个可供下一阶段使用的、可检查的结果。

> Implement `plan.py`: `validate_plan`. This artifact is stage 1 of Cloud Agent With AWS Strands. It consumes explicit inputs and returns an inspectable result that the next stage can use.

使用[公开 API 契约](../../../API.md)和带类型标注的起始签名。核心函数只返回值；文件输入、参数解析和展示一律交给配套的 driver。

> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.

只接受恰好 operation 和 resource 两个键。不能因为模型多给了一个 shell 或 region 属性，就让它升级成执行参数。

> Require exactly operation and resource keys. Do not let an extra shell or region property become an execution parameter because the model included it.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py cloud-agent-with-aws-strands --init learning-artifacts/cloud-agent-with-aws-strands` 初始化一次，然后按阶段累加评分：

> From the repository root, initialize once with `python3 scripts/project_test.py cloud-agent-with-aws-strands --init learning-artifacts/cloud-agent-with-aws-strands`. Then grade cumulatively:

```bash
python3 scripts/project_test.py cloud-agent-with-aws-strands --stage 1 --path learning-artifacts/cloud-agent-with-aws-strands --strict
```

全新的工作区在你实现契约之前应当是失败的。所有阶段完成后，用提供的样例运行你自己的工件：

> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

```bash
cd learning-artifacts/cloud-agent-with-aws-strands
python3 cli.py samples/input.json --output incident.json
```

## Investigate the failure boundary · 探查失败边界

把第二个资源 inventory-api 放到 scope 之外再加进来。校验失败之后，provider 调用 spy 应当保持为空。

> Add a second resource inventory-api outside scope. The provider-call spy should remain empty after validation fails.

## References · 参考资料

[Reference 1](https://strandsagents.com/docs/user-guide/concepts/model-providers/custom_model_provider/)
