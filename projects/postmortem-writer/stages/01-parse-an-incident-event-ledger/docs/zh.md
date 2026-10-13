# Parse an incident event ledger · 解析事件台账

> e1 tab 12 tab alert tab latency high -> Event at t=12

**Type:** Build
**Languages:** Go
**Stage:** 1 of 4
**Time:** ~2 hours

## Ingest evidence with a stable locator · 用稳定的定位符摄入证据

从这份小小的 tab 分隔台账（ledger）开始：事件 ID、经过的秒数、种类（kind）和消息。后面每一条主张（claim）都依赖这些身份标识。随附的 JSONL 导入器把显式记录转换成这份契约，并记住原始物理行号——包括空行。

> Start with the small tab-separated ledger: event ID, elapsed second, kind and message. Every later claim depends on those identities. The provided JSONL importer converts explicit records to that contract and remembers the original physical line, including blank lines.

## Work through one case · 走通一个案例

第 12 秒的一条 alert 即使是提供的第一个事件，也是合法的。出现第二个相同 ID 的事件就是冲突。在 JSONL 里，缺失秒数的记录会被拒绝，而不是悄悄变成 0。当事件前面有一个空的第一行时，导入器保留的是第 2 行。

```figure
pj-postmortem-writer-1
```

> An alert at second 12 is valid even when it is the first event supplied. A second event with the same ID is a conflict. In JSONL, a missing second is rejected instead of silently becoming zero. The importer retains line 2 when a blank first line precedes the event.

## Your task · 你的任务

```go
func Parse(text string)([]Event,error)
```

在你的工作区里实现这些公开签名。把非法输入与预算上限、状态冲突分开处理。任何操作失败时，保持原始证据或输入记录不变。测试会直接加载你的工作区，所以在已提交（checked-in）的参考实现里另写一个不同的函数并不能推进你的阶段。

> Implement these public signatures in your workspace. Keep invalid input separate from a budget limit or state conflict. Preserve the original evidence or input record whenever an operation fails. Tests load your workspace directly, so implementing a different function in the checked-in solution does not advance your stage.

## Run the tests · 运行测试

```bash
python3 scripts/project_test.py postmortem-writer --stage 1 --path /tmp/postmortem-writer-work
```

本阶段检查 Valid、Negative、Duplicate、Missing、Empty。用失败的案例定位你违反的那条不变量（invariant）。只通过正常示例并不能确立边界行为。

> The stage checks Valid, Negative, Duplicate, Missing, Empty. Use the failing case to locate the invariant you violated. Passing the normal example alone does not establish the boundary behavior.

## Implementation hints · 实现提示

先把整数解析出来再追加。要求四个字段齐全、时间非负。维护一个 ID 集合，出现重复就拒绝整批输入。JSONL 配置会拒绝未知字段和内嵌的记录分隔符，这样转换过程无法伪造出台账行。

从一个合法记录开始，优化之前先补上拒绝场景。失败时保持源数据不变，调用方才能诊断发生了什么。用足以表达边界的最小函数；多加一层框架只会掩盖你正在学习的机制。

> Require all four fields and nonnegative time. Keep a set of IDs and reject the complete batch on duplicates. ... Start with one valid record, then add the rejection case before optimizing. ... Use the smallest function that expresses the boundary; an extra framework would hide the mechanism you are learning.

## Check your understanding · 检查你的理解

在三条合法记录之后试着喂一条畸形记录。调用方应该收到什么？解释为什么保留物理行号比只给通过解析的记录编号更有用。

先写下你的预测，再去跑测试。如果结果让你意外，就把输入沿着验证、状态构造、输出这条链路追踪一遍。通过测试的参考实现只是一个对比工具；你自己的工作区必须通过累积式评分器（cumulative grader）才能算完成。

> Try a malformed record after three valid records. What should the caller receive? Explain why preserving physical line numbers is more useful than numbering only the records that survived parsing. ... A passing reference implementation is a comparison tool; your own workspace must pass the cumulative grader to establish completion.

## Use it with your own data · 用你自己的数据

`--events FILE --review FILE --out DIRECTORY` 会生成 index.html、packet.json 和 packet.txt。用 `--events ../examples/events.jsonl --review ../examples/review.json --out /tmp/incident-packet` 运行随附的示例文件。不带参数时，CLI 会打印一个小型的原始 fixture。证据检查确立的是来源出处（provenance）；因果判断和评审人身份仍然是人的责任。

> `--events FILE --review FILE --out DIRECTORY` produces index.html, packet.json and packet.txt. Run the supplied files with `--events ../examples/events.jsonl --review ../examples/review.json --out /tmp/incident-packet`. With no arguments, the CLI prints a small original fixture. Evidence checks establish source provenance; causal judgment and reviewer identity remain human responsibilities.

## Sources · 参考资料

[Google SRE postmortem practice](https://sre.google/workbook/postmortem-culture/).
