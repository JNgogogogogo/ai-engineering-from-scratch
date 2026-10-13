# Define exactly what a correct answer means · 精确定义什么是「正确答案」

> Define the answer contract before seeing the scores.

**Type:** Build
**Languages:** Go
**Stage:** 2 of 4
**Prerequisites:** 阶段 1 与字符串处理。评分器刻意使用「精确答案」契约。
**Time:** ~2 hours

## What you build · 你要构建什么

实现 `Correct(actual, expected)`：先转小写、再折叠连续空白，最后做相等比较。空的期望答案永远不能通过。保留数字、单位和标点：过期 15 分钟和过期 150 分钟在运维上的后果完全不同。

这个指标适用于提示词要求时长、状态或明确拒答（explicit abstention）的场景。它不衡量自由格式文章的事实质量。

> Implement `Correct(actual, expected)` as lowercase plus collapsed whitespace, followed by equality. Empty expected answers never pass. Keep numbers, units and punctuation: an expiry of 15 minutes and 150 minutes have different operational consequences.
> This metric is appropriate when prompts request a duration, state or explicit abstention. It does not measure the factual quality of free-form essays.

## Worked example · 示例走查

对 `actual = " 15   MINUTES\n"`：先把文本拆成 `["15", "MINUTES"]`，再拼成 `15 MINUTES`，然后转小写得到 `15 minutes`。归一化后的期望答案同样是 `15 minutes`，因此该用例得 1 分。

`15 min` 对 `15 minutes` 会判失败。这是已经声明过的指标局限，不是模型出错的证据。如果你的应用需要更多可接受的变体，请通过单独规定的契约来添加；不要在看完成绩之后才放宽相等判断。

```figure
pj-harness-bench-2
```

> For `actual = " 15   MINUTES\n"`, split the text into `["15", "MINUTES"]`, join it as `15 MINUTES`, then lowercase it to `15 minutes`. The normalized expected answer is also `15 minutes`, so the case earns one point.
> `15 min` fails against `15 minutes`. That is a declared metric limitation, not evidence that the model is wrong. Add accepted variants through a separately specified contract if your application needs them; do not loosen equality after inspecting the winners.

## Implement the contract · 实现契约

```go
func Correct(actual, expected string) bool
```

`strings.Fields` 负责处理连续空白。`strings.ToLower` 处理 Unicode 大小写，但不会组合规范等价的附加符号（accents）。请把这个边界如实记录下来，而不要声称做了语义或完整的 Unicode 归一化。

> `strings.Fields` handles runs of whitespace. `strings.ToLower` handles Unicode case, but does not compose canonically equivalent accents. Record that boundary rather than claiming semantic or full Unicode normalization.

## Run your work · 运行你的实现

从仓库根目录初始化一次；评分器会保留已有的工作区文件：

```bash
python3 scripts/project_test.py harness-bench --init /tmp/harness-bench-work
python3 scripts/project_test.py harness-bench --stage 2 --path /tmp/harness-bench-work --strict
```

你的实现放在该工作区的 `stage2.go` 里。提供的适配器会调用这些学习者函数；它们不会导入参考实现。阶段测试包含与 Orchard 演示相互独立的用例。

> Your implementation belongs in `stage2.go` in that workspace. Provided adapters call those learner functions; they do not import the reference solution. Stage tests include cases separate from the Orchard demonstration.

## Inspect and extend · 检查与扩展

拿 `10 ms` 对 `100 ms`，以及 `ready!` 对 `ready` 做测试。在这个契约下哪些应该通过？先写下答案，再运行评分器。对开放式答案，请改用带来源证据的 [Report Judge](../../../../report-judge/README.md)，而不是这个指标。

[Go 标准库参考](https://pkg.go.dev/encoding/json)。可运行的核心只使用 Go 标准库。外部模型调用是可选的，在常规评分期间不会运行。

> Test `10 ms` against `100 ms`, and `ready!` against `ready`. Which should pass under this contract? Write the answer before running the scorer. For open-ended answers, use the [Report Judge](../../../../report-judge/README.md) with source evidence instead of this metric.
> [Go standard-library reference](https://pkg.go.dev/encoding/json). The runnable core uses only Go's standard library. External model calls are optional and do not run during ordinary grading.
