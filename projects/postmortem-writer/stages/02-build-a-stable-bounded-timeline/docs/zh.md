# Build a stable bounded timeline · 构建稳定有界的时间线

> event b at 5, event a at 1 -> a then b

**Type:** Build
**Languages:** Go
**Stage:** 2 of 4
**Time:** ~2 hours

## Separate ingestion order from timeline order · 区分摄入顺序与时间线顺序

日志可能乱序到达。时间线（timeline）给观察到的事件排出一个顺序，但并不声称时间顺序能证明因果。复制一份输入，让其他消费方仍能检查到达顺序。两个事件落在同一秒时，用事件 ID 作为平局裁决（tie-breaker）。

> Logs can arrive out of order. A timeline orders the observed events without claiming that time order proves causality. Copy the input so another consumer can still inspect arrival order. Use event ID as the tie-breaker when two events share a second.

## Work through one case · 走通一个案例

假设 b 在第 35 秒到达，a 在第 0 秒，c 在第 35 秒。排序结果是 a、b、c。当视野上限（horizon）为 30 时，操作直接失败，而不是丢掉 b 和 c。被丢掉的事件可能恰恰是能推翻草稿解释的那条观察。

```figure
pj-postmortem-writer-2
```

> Suppose b arrives at second 35, a at second 0 and c at second 35. Sorting yields a, b, c. With a horizon of 30, the operation fails instead of dropping b and c. A dropped event could be the observation that contradicts the draft explanation.

## Your task · 你的任务

```go
func Timeline(events []Event,horizon int)([]Event,error)
```

在你的工作区里实现这些公开签名。把非法输入与预算上限、状态冲突分开处理。任何操作失败时，保持原始证据或输入记录不变。测试会直接加载你的工作区，所以在已提交（checked-in）的参考实现里另写一个不同的函数并不能推进你的阶段。

> Implement these public signatures in your workspace. Keep invalid input separate from a budget limit or state conflict. Preserve the original evidence or input record whenever an operation fails. Tests load your workspace directly, so implementing a different function in the checked-in solution does not advance your stage.

## Run the tests · 运行测试

```bash
python3 scripts/project_test.py postmortem-writer --stage 2 --path /tmp/postmortem-writer-work
```

本阶段检查 Ordered、Tied、NoMutation、Bound、Empty。用失败的案例定位你违反的那条不变量（invariant）。只通过正常示例并不能确立边界行为。

> The stage checks Ordered, Tied, NoMutation, Bound, Empty. Use the failing case to locate the invariant you violated. Passing the normal example alone does not establish the boundary behavior.

## Implementation hints · 实现提示

先校验 horizon 和每个事件的时间。复制切片，然后以秒为主键、ID 为次键排序。在你的测试里同时检查输出顺序和未变的输入。

从一个合法记录开始，优化之前先补上拒绝场景。失败时保持源数据不变，调用方才能诊断发生了什么。用足以表达边界的最小函数；多加一层框架只会掩盖你正在学习的机制。

> Validate the horizon and every event time first. Copy the slice, then sort with second as the primary key and ID as the secondary key. Check both the output order and the unchanged input in your tests. ... Start with one valid record, then add the rejection case before optimizing. ... Use the smallest function that expresses the boundary; an extra framework would hide the mechanism you are learning.

## Check your understanding · 检查你的理解

同样的三条记录，horizon 恰好为 35 时会发生什么？在一个不同的到达位置加入一个相同的时间戳，并证明最终 packet 完全一致。

先写下你的预测，再去跑测试。如果结果让你意外，就把输入沿着验证、状态构造、输出这条链路追踪一遍。通过测试的参考实现只是一个对比工具；你自己的工作区必须通过累积式评分器（cumulative grader）才能算完成。

> What happens to the same three records with a horizon of exactly 35? Add a tied timestamp in a different arrival position and prove that the final packet is identical. ... A passing reference implementation is a comparison tool; your own workspace must pass the cumulative grader to establish completion.

## Use it with your own data · 用你自己的数据

`--events FILE --review FILE --out DIRECTORY` 会生成 index.html、packet.json 和 packet.txt。用 `--events ../examples/events.jsonl --review ../examples/review.json --out /tmp/incident-packet` 运行随附的示例文件。不带参数时，CLI 会打印一个小型的原始 fixture。证据检查确立的是来源出处（provenance）；因果判断和评审人身份仍然是人的责任。

> `--events FILE --review FILE --out DIRECTORY` produces index.html, packet.json and packet.txt. Run the supplied files with `--events ../examples/events.jsonl --review ../examples/review.json --out /tmp/incident-packet`. With no arguments, the CLI prints a small original fixture. Evidence checks establish source provenance; causal judgment and reviewer identity remain human responsibilities.

## Sources · 参考资料

[Google SRE postmortem practice](https://sre.google/workbook/postmortem-culture/).
