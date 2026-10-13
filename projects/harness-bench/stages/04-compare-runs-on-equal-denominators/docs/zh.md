# Compare runs on equal denominators · 在相同分母上比较多次运行

> Prove the runs are comparable before ranking them.

**Type:** Build
**Languages:** Go
**Stage:** 4 of 4
**Prerequisites:** 阶段 1 到阶段 3。阅读 [Prompt Regression Tester](../../../../prompt-regression-tester/README.md) 了解成对的输出比较。
**Time:** ~2 hours

## What you build · 你要构建什么

实现 `Leaderboard`，让它在排序之前先校验结果。要求总数相等、评测器（harness）名称唯一。带回执（receipt）的结果必须拥有相同的有序数据集 SHA-256、模型配置 SHA-256 和调用预算。把缺失回执的结果混进带回执的比较中，必须予以拒绝。

`Fingerprint` 先序列化带类型的值，再做哈希。数据集的键顺序和空白会消失，但用例顺序、提示词、期望答案和证据仍然是回执的一部分。模型回执包含适配器、模型 ID、生成参数、在线时的 endpoint，以及回放时的完整录制摘要。

> Implement `Leaderboard` so it validates results before sorting. Require equal totals and unique harness names. Receipt-bearing results must have the same ordered dataset SHA-256, model-configuration SHA-256 and call budget. Reject missing receipts mixed into a receipt-bearing comparison.
> `Fingerprint` serializes typed values before hashing. Dataset key order and whitespace disappear, but case order, prompts, expected answers and evidence remain part of the receipt. The model receipt includes adapter, model ID, generation settings, endpoint when live, and the full recording digest when replaying.

## Worked example · 示例走查

内置的 Orchard 录制给出的成绩是：baseline `1/3`（三次调用）、retry `2/3`（四次）、evidence `3/3`（三次）。这些响应是为了演示机制而刻意构造的；它们并不给真实模型排名。

现在替换过期问题但保留三个用例。相同分母仍然给出 `3`，但数据集摘要不同了。要用 `ErrConflict` 拒绝这种比较。把 `max_tokens` 从 128 改成 256 同样必须拒绝混合比较，即使模型名没有变。

```figure
pj-harness-bench-4
```

> The authored Orchard recording yields baseline `1/3` with three calls, retry `2/3` with four, and evidence `3/3` with three. Those are deliberately constructed responses that demonstrate the mechanism; they do not rank real models.
> Now replace the expiry question but keep three cases. Equal denominators still say `3`, while dataset digests differ. Reject that comparison with `ErrConflict`. Changing `max_tokens` from 128 to 256 must also reject a mixed comparison, even if the model name is unchanged.

## Implement the contract · 实现契约

```go
func Leaderboard(results []Result) (string, error)
```

在排序副本之前先校验计数器：`Correct + Errors <= Attempted <= Total`；带回执的 run 还必须满足 `Attempted <= Calls <= CallBudget`。排名依据：先按正确数，再按更少的最终错误数，再按名称。没有任何回执的旧式手工构造结果保留原有的「仅计数器」API；录制或在线的比较请使用 `EvaluatePolicy`。

> Validate counters before sorting a copy: `Correct + Errors <= Attempted <= Total`, and receipt-bearing runs must satisfy `Attempted <= Calls <= CallBudget`. Rank by correct answers, then fewer final errors, then name. Legacy manually constructed results without any receipts retain the original counter-only API; use `EvaluatePolicy` for recorded or live comparisons.

## Run your work · 运行你的实现

从仓库根目录初始化一次；评分器会保留已有的工作区文件：

```bash
python3 scripts/project_test.py harness-bench --init /tmp/harness-bench-work
python3 scripts/project_test.py harness-bench --stage 4 --path /tmp/harness-bench-work --strict
```

你的实现放在该工作区的 `stage4.go` 里。提供的适配器会调用这些学习者函数；它们不会导入参考实现。阶段测试包含与 Orchard 演示相互独立的用例。

> Your implementation belongs in `stage4.go` in that workspace. Provided adapters call those learner functions; they do not import the reference solution. Stage tests include cases separate from the Orchard demonstration.

## Inspect and extend · 检查与扩展

在完成的工作区里运行 `go run . --cases fixtures/orchard-cases.json --recording fixtures/orchard-recording.json --out /tmp/orchard-runs.json`。检查每条策略各一条 trace。HTTP 适配器接受完整的 chat-completions endpoint 以及 `--model`、`--key-env`、`--temperature` 和 `--max-tokens`；命令见 README。要估计方差需要多次在线运行，而且这些未签名的回执并不能证明远端模型保持不变。

[Go 标准库参考](https://pkg.go.dev/encoding/json)。可运行的核心只使用 Go 标准库。外部模型调用是可选的，在常规评分期间不会运行。

> Run `go run . --cases fixtures/orchard-cases.json --recording fixtures/orchard-recording.json --out /tmp/orchard-runs.json` in your completed workspace. Inspect one trace from each policy. The HTTP adapter accepts a full chat-completions endpoint, `--model`, `--key-env`, `--temperature` and `--max-tokens`; the README has the command. Repeated live runs are needed to estimate variance, and these unsigned receipts do not attest that a remote model stayed fixed.
> [Go standard-library reference](https://pkg.go.dev/encoding/json). The runnable core uses only Go's standard library. External model calls are optional and do not run during ordinary grading.
