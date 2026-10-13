# Run a harness under a call budget · 在调用预算下运行评测器

> Spend calls on a policy, not on answer leakage.

**Type:** Build
**Languages:** Go
**Stage:** 3 of 4
**Prerequisites:** 阶段 1 和阶段 2。在加入真实模型之前，先理解 Go 的回调（callback）与 context 取消（cancellation）。
**Time:** ~2 hours

## What you build · 你要构建什么

实现 `EvaluatePolicy` 与 `PolicyPrompt`；保留 `Evaluate` 作为基线便捷封装。三条策略拿到的是同一批有序用例和同一份模型配置。`baseline` 每个用例调用一次。`retry-errors` 在供应商错误之后允许一次额外调用。`evidence` 只把该用例声明的证据追加到提示词里。

每次调用之前先把 `Calls` 记上账。`Attempted` 统计用例数，`Errors` 统计最终调用失败的用例数，`Total` 永远包含每一个输入用例。把每次调用的提示词、答案、失败与正确性记录进 `Trace`。绝不要因为答案没通过评分器就重试。

> Implement `EvaluatePolicy` and `PolicyPrompt`; retain `Evaluate` as a baseline convenience wrapper. The three policies receive the same ordered cases and model configuration. `baseline` makes one call per case. `retry-errors` permits one extra call after a provider error. `evidence` appends only the case's declared evidence to its prompt.
> Charge `Calls` before every invocation. `Attempted` counts cases, `Errors` counts cases whose final call fails, and `Total` always includes every input case. Record each call's prompt, answer, failure and correctness in `Trace`. Never retry merely because an answer failed the scorer.

## Worked example · 示例走查

restore 问题录制的第一次响应是错误，第二次响应是 `ready`。基线在该用例上以 `Calls=1, Attempted=1, Errors=1` 结束。重试策略则得到 `Calls=2, Attempted=1, Errors=0, Correct=1`。

把预算降到 1。重试无法发生，于是该用例保持为错误，状态是 `budget-exhausted`。后面的用例仍留在分母里。在过期问题上，一个有效但错误的 `60 minutes` 答案永远不会触发「先知式重试」（oracle retry）。

```figure
pj-harness-bench-3
```

> The restore question's recorded first response is an error and its second response is `ready`. Baseline ends that case with `Calls=1, Attempted=1, Errors=1`. The retry policy uses `Calls=2, Attempted=1, Errors=0, Correct=1`.
> Reduce the budget to one. The retry cannot happen, so the case remains an error and the state is `budget-exhausted`. Later cases remain in the denominator. On the expiry question, a valid but wrong `60 minutes` answer never triggers an oracle retry.

## Implement the contract · 实现契约

```go
func PolicyPrompt(c Case, policy string) string
func EvaluatePolicy(ctx context.Context, name, policy string, cases []Case, model ContextModel, budget int, modelReceipt string) (Result, error)
func Evaluate(name string, cases []Case, model Model, budget int) (Result, error)
```

把每个用例的尝试次数与整个 run 的调用计数分开保管。只有模型提示词进入 `ContextModel`；`Expected` 留在评分一侧。为每条策略构造全新的录制适配器，让较早的策略不可能消耗较晚策略的第一条响应。录制耗尽时返回错误，而不是永远重复其最后一条答案。

> Keep per-case attempts separate from the run's call counter. Only the model prompt enters `ContextModel`; `Expected` stays on the scoring side. Construct a fresh recorded adapter for each policy so an earlier policy cannot consume a later policy's first response. Exhausted recordings return errors instead of repeating their final answer forever.

## Run your work · 运行你的实现

从仓库根目录初始化一次；评分器会保留已有的工作区文件：

```bash
python3 scripts/project_test.py harness-bench --init /tmp/harness-bench-work
python3 scripts/project_test.py harness-bench --stage 3 --path /tmp/harness-bench-work --strict
```

你的实现放在该工作区的 `stage3.go` 里。提供的适配器会调用这些学习者函数；它们不会导入参考实现。阶段测试包含与 Orchard 演示相互独立的用例。

> Your implementation belongs in `stage3.go` in that workspace. Provided adapters call those learner functions; they do not import the reference solution. Stage tests include cases separate from the Orchard demonstration.

## Inspect and extend · 检查与扩展

在完成的工作区里用 `go run . --budget 2 --out /tmp/orchard-budget.json` 运行成品。解释为什么把一次重试花在较早的用例上，可能导致较晚的用例根本没被尝试。提供的 HTTP 适配器受 context 截止时间（deadline）约束；任意的自定义回调必须自行配合取消（cancellation）。

[Go 标准库参考](https://pkg.go.dev/encoding/json)。可运行的核心只使用 Go 标准库。外部模型调用是可选的，在常规评分期间不会运行。

> Run the completed learner artifact with `go run . --budget 2 --out /tmp/orchard-budget.json` from its workspace. Explain why spending a retry on an early case can leave a later case unattempted. A context deadline bounds the provided HTTP adapter; an arbitrary custom callback must cooperate with cancellation.
> [Go standard-library reference](https://pkg.go.dev/encoding/json). The runnable core uses only Go's standard library. External model calls are optional and do not run during ordinary grading.
