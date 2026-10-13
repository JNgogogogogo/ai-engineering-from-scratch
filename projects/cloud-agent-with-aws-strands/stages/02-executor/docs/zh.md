# Execute reads within step and response budgets · 在步数与响应预算内执行读取

Stage 2 of 4 · 第 2 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

## What changes · 变化在哪

在启动一个操作之前先计步，在保留序列化输出之前先计量。输出上限不能撤销一次调用已经花掉的开销，但能防止一个巨大的结果淹没后续上下文。保留部分结果和一个显式的终止状态，让预算触发的停止仍然可诊断。

> Charge steps before starting an operation and charge serialized output before retaining it. Output limits cannot undo the cost of a call, but they prevent a large result from flooding later context. Keep partial results and an explicit terminal state so a budget stop remains diagnosable.

## Work through one concrete case · 走通一个具体案例

在 max_steps=2 下，一个三步计划最多保留两个结果。在 max_chars=1 下，第一个 provider 仍然会运行，然后其结果才被发现过大；不保留任何输出。

> With max_steps=2, a three-action plan retains at most two results. With max_chars=1, the first provider can still run before its result is found too large; no output is retained.

```figure
pj-cloud-agent-with-aws-strands-2
```

先修改实验输入、自己算出结果，再去读它的指标。图中的数值由这些输入计算得出；下方的实现测试仍然是完成与否的判定依据。

> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

实现 `executor.py` 中的 `execute`。这个工件是 Cloud Agent With AWS Strands 的第 2 阶段产物：它消费显式输入，返回一个可供下一阶段使用的、可检查的结果。

> Implement `executor.py`: `execute`. This artifact is stage 2 of Cloud Agent With AWS Strands. It consumes explicit inputs and returns an inspectable result that the next stage can use.

使用[公开 API 契约](../../../API.md)和带类型标注的起始签名。核心函数只返回值；文件输入、参数解析和展示一律交给配套的 driver。

> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.

步数预算限制的是派发。序列化输出预算限制的是保留的上下文。在结果里把这两种不同的保证分别命名，并在预算耗尽时保留已经完成的行。

> A step budget limits dispatch. A serialized-output budget limits retained context. Name these different guarantees in the result and retain the already completed rows on exhaustion.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py cloud-agent-with-aws-strands --init learning-artifacts/cloud-agent-with-aws-strands` 初始化一次，然后按阶段累加评分：

> From the repository root, initialize once with `python3 scripts/project_test.py cloud-agent-with-aws-strands --init learning-artifacts/cloud-agent-with-aws-strands`. Then grade cumulatively:

```bash
python3 scripts/project_test.py cloud-agent-with-aws-strands --stage 2 --path learning-artifacts/cloud-agent-with-aws-strands --strict
```

全新的工作区在你实现契约之前应当是失败的。所有阶段完成后，用提供的样例运行你自己的工件：

> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

```bash
cd learning-artifacts/cloud-agent-with-aws-strands
python3 cli.py samples/input.json --output incident.json
```

## Investigate the failure boundary · 探查失败边界

让第一次 read 返回一个 1000 字符的字符串。说明为什么限制 provider 响应的字节数是 adapter 层的一项独立职责。

> Return a 1000-character string from the first read. Show why bounding provider response bytes is a separate adapter responsibility.

## References · 参考资料

[Reference 1](https://strandsagents.com/docs/user-guide/concepts/model-providers/custom_model_provider/)
