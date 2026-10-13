# Load unseen benchmark cases · 加载未见的基准用例

> Freeze the cases before comparing policies.

**Type:** Build
**Languages:** Go
**Stage:** 1 of 4
**Prerequisites:** Go 结构体（struct）、切片（slice）与 JSON 解码。阅读[模型评估](../../../../../phases/02-ml-fundamentals/09-model-evaluation/docs/en.md)了解 held-out（保留）样本的作用。
**Time:** ~2 hours

## What you build · 你要构建什么

导出链接助手记着旧的 60 分钟过期时间，而你的 runbook 写的是 15 分钟。把问题、期望答案和允许使用的证据放进相互独立的字段，这样你才能看清每条策略（policy）各自拿到了什么。

`Cases(data, max)` 接受一个由 `Case{ID, Prompt, Expected, Evidence}` 组成的 JSON 数组。`Evidence` 是可选的字符串数组。拒绝未知字段、重复 ID、空白必填字段、尾部多余的 JSON，以及超过 `max` 条的用例。输入文件在解码前限制为 1 MiB。

> An export-link assistant remembers an old 60-minute expiry. Your runbook says 15 minutes. Keep the question, expected answer and permitted evidence in separate fields so you can see exactly what each policy receives.
> `Cases(data, max)` accepts a JSON array of `Case{ID, Prompt, Expected, Evidence}`. `Evidence` is an optional string array. Reject unknown fields, duplicate IDs, blank required fields, trailing JSON and more than `max` cases. The input file is limited to one MiB before decoding.

## Worked example · 示例走查

从 `fixtures/orchard-cases.json` 的第一条记录开始。它的 ID 是 `orchard-ttl`，期望答案是 `15 minutes`，证据只有一句 runbook 里的句子。解码完成后，你的状态里有一条带类型的记录，以及一个包含 `orchard-ttl` 的 seen-ID 集合。

再追加一条 ID 相同、问题不同的记录。此时返回 `ErrConflict`；不要静默替换第一条记录。当 `max=0` 时，连第一条记录都超出了声明的用例预算。空数组可以解析通过，但最终的 CLI 会拒绝一个没有任何用例的基准。

```figure
pj-harness-bench-1
```

> Start with the first record in `fixtures/orchard-cases.json`. Its ID is `orchard-ttl`, expected answer is `15 minutes`, and its evidence is one runbook sentence. After decoding, your state contains one typed record and a seen-ID set containing `orchard-ttl`.
> Append a second record with the same ID and a different question. Return `ErrConflict`; do not silently replace the first record. With `max=0`, even the first record exceeds the declared case budget. An empty array can parse, but the final CLI rejects a benchmark with no cases.

## Implement the contract · 实现契约

```go
func Cases(data []byte, max int) ([]Case, error)
```

使用 `json.Decoder.DisallowUnknownFields`，然后再做第二次解码并要求得到 `io.EOF`。把「清点记录」与「校验记录字段」分开进行。拼错的 `Expected` 键必须产生错误，而不是产生一个悄悄改变你得分的空答案。

> Use `json.Decoder.DisallowUnknownFields`, then perform a second decode and require `io.EOF`. Count records separately from validating their fields. A misspelled `Expected` key must produce an error instead of an empty answer that quietly changes your score.

## Run your work · 运行你的实现

从仓库根目录初始化一次；评分器（grader）会保留已有的工作区文件：

```bash
python3 scripts/project_test.py harness-bench --init /tmp/harness-bench-work
python3 scripts/project_test.py harness-bench --stage 1 --path /tmp/harness-bench-work --strict
```

你的实现放在该工作区的 `stage1.go` 里。提供的适配器（adapter）会调用这些学习者函数；它们不会导入参考实现。阶段测试包含与 Orchard 演示相互独立的用例。

> Your implementation belongs in `stage1.go` in that workspace. Provided adapters call those learner functions; they do not import the reference solution. Stage tests include cases separate from the Orchard demonstration.

## Inspect and extend · 检查与扩展

为什么 ID 冲突和「两个用例期望答案相同」是两回事？试着只改变 JSON 的空白而不改任何字段：最终的数据集回执（receipt）应保持一致。而改变用例顺序必须改变回执，因为受限预算是按顺序逐个访问用例的。

[Go 标准库参考](https://pkg.go.dev/encoding/json)。可运行的核心只使用 Go 标准库。外部模型调用是可选的，在常规评分期间不会运行。

> Why is an ID collision different from two cases with the same expected answer? Try changing JSON whitespace without changing any field: the final dataset receipt should remain identical. Changing case order must change the receipt because a limited budget visits cases in order.
> [Go standard-library reference](https://pkg.go.dev/encoding/json). The runnable core uses only Go's standard library. External model calls are optional and do not run during ordinary grading.
