# Classify failures without retrying everything · 给失败分类，而不是全都重试

> Separate a repairable outage from a broken request.

**Type:** Build
**Languages:** Go
**Stage:** 2 of 4
**Prerequisites:** Stage 1 和 HTTP 状态码分类。
**Time:** ~2 hours

## What you build · 你要构建什么

实现 `ClassifyStatus(status)`，产生三种结果。2xx 响应算成功；429 和 5xx 允许 fallback；其余所有合法状态码都是 terminal。100 到 599 之外的整数是非法的。

401 通常意味着已配置的凭证需要修复。把同一个请求发给多个 provider 会掩盖这个错误，所以本项目在此停止。503 表示 provider 现在无法服务这个请求，所以换一个已配置的 provider 可能有帮助。

> Implement `ClassifyStatus(status)` with three outcomes. A 2xx response succeeds; 429 and 5xx permit fallback; all other valid codes are terminal. Integers outside 100 through 599 are invalid.
> A 401 usually means the configured credential needs repair. Sending the same request to several providers can hide that mistake, so this project stops. A 503 indicates that a provider cannot serve the request right now, so another configured provider may help.

## Worked example · 具体例子

跟随状态序列 `[503, 200]`：第一个被分类为 `retry`，第二个为 `success`。跟随 `[401, 200]`：401 是 `terminal`，第二个 provider 永远不会被联系。307 同样是 terminal，因为请求层拒绝重定向。

这条路由策略对每个 provider 至多访问一次。它不会为 `Retry-After` 睡眠等待，不会重试同一个端点，也不会承诺一次超时的生成从未被计费。

```figure
pj-llm-gateway-with-fallbacks-2
```

> Follow statuses `[503, 200]`: classify the first as `retry`, then the second as `success`. Follow `[401, 200]`: the 401 is `terminal` and the second provider is never contacted. A 307 is also terminal because the request layer refuses redirects.
> This routing policy visits each provider at most once. It does not sleep for `Retry-After`, retry the same endpoint, or promise that a timed-out generation was never billed.

## Implement the contract · 实现契约

```go
func ClassifyStatus(status int) (string, error)
```

先校验数值范围，再判断 success，然后判断两个 retry 条件。不要把 `status >= 400` 当作 retry 规则：那会把畸形请求和认证失败也包含进去。

> Validate the numeric range first, then test success, then the two retry conditions. Do not use `status >= 400` as the retry rule: it would include malformed requests and authentication failures.

## Run your work · 运行你的实现

在仓库根目录初始化一次；grader 会保留工作区中已有的文件：

```bash
python3 scripts/project_test.py llm-gateway-with-fallbacks --init /tmp/llm-gateway-with-fallbacks-work
python3 scripts/project_test.py llm-gateway-with-fallbacks --stage 2 --path /tmp/llm-gateway-with-fallbacks-work --strict
```

你的实现放在该工作区的 `stage2.go` 里。提供的适配器调用这些学习者函数；它们不会导入参考解法。各阶段的测试包含与 Orchard 演示相互独立的用例。

> From the repository root, initialize once; the grader preserves existing workspace files:
> Your implementation belongs in `stage2.go` in that workspace. Provided adapters call those learner functions; they do not import the reference solution. Stage tests include cases separate from the Orchard demonstration.

## Inspect and extend · 检查与扩展

预测 204、301、408、429、500 和 600 的分类结果。在这条策略里，408 是 terminal。如果你决定在未来的扩展中重试它，先写下新契约和副作用假设，再去修改实现。

[Go standard-library reference](https://pkg.go.dev/context)。可运行核心只使用 Go 标准库。外部模型调用是可选的，在常规评分期间不会运行。

> Predict the outcomes for 204, 301, 408, 429, 500 and 600. In this policy, 408 is terminal. If you choose to retry it in a future extension, write the new contract and side-effect assumptions before changing the implementation.
> [Go standard-library reference](https://pkg.go.dev/context). The runnable core uses only Go's standard library. External model calls are optional and do not run during ordinary grading.
