# Publish a deterministic incident packet · 发布确定性的 incident packet

> validated claim + ordered evidence -> one complete packet

**Type:** Build
**Languages:** Go
**Stage:** 4 of 4
**Time:** ~2 hours

## Publish a packet that exposes unfinished review · 发布一个会暴露未完成评审的 packet

文本 packet、HTML 评审台和 JSON 回执描述的是同一份经过校验的输入。HTML 包含来源链接、物理行定位符、上报的影响、主张裁决以及归属到人的后续行动。待定（pending）的主张和未分配的工作保持可见，而不是从最终报告里消失。

> The text packet, HTML desk and JSON receipt describe the same validated input. The HTML includes source links, physical line locators, reported impact, claim decisions and owned follow-up actions. Pending claims and unassigned work remain visible rather than disappearing from the final report.

## Work through one case · 走通一个案例

运行 `go run . --events ../examples/events.jsonl --review ../examples/review.json --out /tmp/incident-packet`。打开 index.html，沿着 e2 追回它对应的精确日志行。要批准一条主张，把 packet.json 里的 SourceSHA256 复制到 review 文件中的 sourceSHA256，把 state 设为 approved，填上评审人标签，然后重新构建。

```figure
pj-postmortem-writer-4
```

> Run `go run . --events ../examples/events.jsonl --review ../examples/review.json --out /tmp/incident-packet`. Open index.html and follow e2 back to its exact log line. To approve a claim, copy SourceSHA256 from packet.json into sourceSHA256 in the review file, set state to approved and provide a reviewer label, then rebuild.

## Your task · 你的任务

```go
func Report(events []Event,claims []Claim,maxClaims int)(string,error)
```

在你的工作区里实现这些公开签名。把非法输入与预算上限、状态冲突分开处理。任何操作失败时，保持原始证据或输入记录不变。测试会直接加载你的工作区，所以在已提交（checked-in）的参考实现里另写一个不同的函数并不能推进你的阶段。

> Implement these public signatures in your workspace. Keep invalid input separate from a budget limit or state conflict. Preserve the original evidence or input record whenever an operation fails. Tests load your workspace directly, so implementing a different function in the checked-in solution does not advance your stage.

## Run the tests · 运行测试

```bash
python3 scripts/project_test.py postmortem-writer --stage 4 --path /tmp/postmortem-writer-work
```

本阶段检查 Packet、Limit、InvalidAtomic、Escaped、Deterministic。用失败的案例定位你违反的那条不变量（invariant）。只通过正常示例并不能确立边界行为。

> The stage checks Packet, Limit, InvalidAtomic, Escaped, Deterministic. Use the failing case to locate the invariant you violated. Passing the normal example alone does not establish the boundary behavior.

## Implementation hints · 实现提示

在产出输出之前对每一条 claim 调用 Verify，然后再排时间线。拒绝超过上限（cap）的 claim 数量。HTML 用 Go 模板渲染，所以包含 script 标签的消息仍保持为文本。批准身份是一个由外部提供的标签，不是经过认证的签名。

从一个合法记录开始，优化之前先补上拒绝场景。失败时保持源数据不变，调用方才能诊断发生了什么。用足以表达边界的最小函数；多加一层框架只会掩盖你正在学习的机制。

> Call Verify for every claim before producing output, then order the timeline. Reject claim counts above the cap. HTML uses Go templates so a message containing a script tag remains text. Approval identity is a supplied label, not an authenticated signature. ... Start with one valid record, then add the rejection case before optimizing. ... Use the smallest function that expresses the boundary; an extra framework would hide the mechanism you are learning.

## Check your understanding · 检查你的理解

在批准之后改动日志中的一个字节，确认构建因 source 冲突而失败。集成测试同样会拒绝编造的引用和缺失的时间戳。把日志导出器（log exporter）对接到 JSONL 可以作为扩展；要保住证据契约，而不是添加编造的因果解释。

先写下你的预测，再去跑测试。如果结果让你意外，就把输入沿着验证、状态构造、输出这条链路追踪一遍。通过测试的参考实现只是一个对比工具；你自己的工作区必须通过累积式评分器（cumulative grader）才能算完成。

> Change a log byte after approval and confirm the build fails with a source conflict. The integration tests also reject fabricated quotations and missing timestamps. Connect a log exporter to JSONL as an extension; preserve the evidence contract rather than adding invented causal explanations. ... A passing reference implementation is a comparison tool; your own workspace must pass the cumulative grader to establish completion.

## Use it with your own data · 用你自己的数据

`--events FILE --review FILE --out DIRECTORY` 会生成 index.html、packet.json 和 packet.txt。用 `--events ../examples/events.jsonl --review ../examples/review.json --out /tmp/incident-packet` 运行随附的示例文件。不带参数时，CLI 会打印一个小型的原始 fixture。证据检查确立的是来源出处（provenance）；因果判断和评审人身份仍然是人的责任。

> `--events FILE --review FILE --out DIRECTORY` produces index.html, packet.json and packet.txt. Run the supplied files with `--events ../examples/events.jsonl --review ../examples/review.json --out /tmp/incident-packet`. With no arguments, the CLI prints a small original fixture. Evidence checks establish source provenance; causal judgment and reviewer identity remain human responsibilities.

## Sources · 参考资料

[Google SRE postmortem practice](https://sre.google/workbook/postmortem-culture/).
