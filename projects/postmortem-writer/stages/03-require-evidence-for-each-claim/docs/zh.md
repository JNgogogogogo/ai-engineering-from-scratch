# Require evidence for each claim · 每条主张都必须有证据

> claim cites e99 but ledger contains e1 -> invalid

**Type:** Build
**Languages:** Go
**Stage:** 3 of 4
**Time:** ~2 hours

## Distinguish a citation from a conclusion · 区分引用与结论

合法的引用（citation）指向一个明确的已知事件。这只证明来源存在，并不证明该事件在逻辑上能支撑一条因果主张。组合式的评审台（review desk）还会检查逐字引用（exact quotation），把主张保持在待定（pending）状态，并要求已批准（approved）的记录带有明确的评审人和匹配的 source hash。

> A valid citation points to a distinct known event. That proves the source exists. It does not prove that the event logically establishes a causal claim. The composed review desk also checks exact quotations, keeps claims pending and requires an explicit reviewer and matching source hash for approved records.

## Work through one case · 走通一个案例

主张「An alert followed deployment（告警出现在部署之后）」引用了 e1 和 e2。两个 ID 都存在，所以出处检查（provenance）通过。更强的主张「Deployment caused the outage（部署导致了故障）」可以引用同样两个 ID，但仍然需要调查。当来源只说 "latency high" 时，引用写作 "database failed" 的会被拒绝。

```figure
pj-postmortem-writer-3
```

> The claim "An alert followed deployment" cites e1 and e2. Both IDs exist, so provenance passes. The stronger claim "Deployment caused the outage" can cite the same two IDs and still require investigation. A quote saying "database failed" is rejected when the source only says "latency high".

## Your task · 你的任务

```go
func Verify(claim Claim,events []Event)error
```

在你的工作区里实现这些公开签名。把非法输入与预算上限、状态冲突分开处理。任何操作失败时，保持原始证据或输入记录不变。测试会直接加载你的工作区，所以在已提交（checked-in）的参考实现里另写一个不同的函数并不能推进你的阶段。

> Implement these public signatures in your workspace. Keep invalid input separate from a budget limit or state conflict. Preserve the original evidence or input record whenever an operation fails. Tests load your workspace directly, so implementing a different function in the checked-in solution does not advance your stage.

## Run the tests · 运行测试

```bash
python3 scripts/project_test.py postmortem-writer --stage 3 --path /tmp/postmortem-writer-work
```

本阶段检查 Supported、Dangling、NoEvidence、Duplicate、Blank。用失败的案例定位你违反的那条不变量（invariant）。只通过正常示例并不能确立边界行为。

> The stage checks Supported, Dangling, NoEvidence, Duplicate, Blank. Use the failing case to locate the invariant you violated. Passing the normal example alone does not establish the boundary behavior.

## Implementation hints · 实现提示

构建一个已知事件 ID 的集合，再为 claim 内部的 evidence ID 建另一个集合。拒绝空白的主张文本、缺失的证据、重复的引用和悬空引用（dangling reference）。绝不要用一个看似合理的替代品去填补缺失的来源。

从一个合法记录开始，优化之前先补上拒绝场景。失败时保持源数据不变，调用方才能诊断发生了什么。用足以表达边界的最小函数；多加一层框架只会掩盖你正在学习的机制。

> Build a set of known event IDs and a separate set for evidence IDs within the claim. Reject blank claim text, missing evidence, duplicate citations and dangling references. Never fill in a missing source with a plausible substitute. ... Start with one valid record, then add the rejection case before optimizing. ... Use the smallest function that expresses the boundary; an extra framework would hide the mechanism you are learning.

## Check your understanding · 检查你的理解

构造两条引用相同事件的不同主张。解释哪些检查是你的代码能做的，哪些判断仍要留给评审人。为什么底层日志一旦改变，已批准的决定就必须失效（stale）？

先写下你的预测，再去跑测试。如果结果让你意外，就把输入沿着验证、状态构造、输出这条链路追踪一遍。通过测试的参考实现只是一个对比工具；你自己的工作区必须通过累积式评分器（cumulative grader）才能算完成。

> Invent two different claims that cite the same events. Explain which checks your code can perform and which judgment remains with a reviewer. Why must an approved decision become stale when the underlying log changes? ... A passing reference implementation is a comparison tool; your own workspace must pass the cumulative grader to establish completion.

## Use it with your own data · 用你自己的数据

`--events FILE --review FILE --out DIRECTORY` 会生成 index.html、packet.json 和 packet.txt。用 `--events ../examples/events.jsonl --review ../examples/review.json --out /tmp/incident-packet` 运行随附的示例文件。不带参数时，CLI 会打印一个小型的原始 fixture。证据检查确立的是来源出处（provenance）；因果判断和评审人身份仍然是人的责任。

> `--events FILE --review FILE --out DIRECTORY` produces index.html, packet.json and packet.txt. Run the supplied files with `--events ../examples/events.jsonl --review ../examples/review.json --out /tmp/incident-packet`. With no arguments, the CLI prints a small original fixture. Evidence checks establish source provenance; causal judgment and reviewer identity remain human responsibilities.

## Sources · 参考资料

[Google SRE postmortem practice](https://sre.google/workbook/postmortem-culture/).
