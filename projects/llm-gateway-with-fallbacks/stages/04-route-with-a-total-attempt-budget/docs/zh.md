# Route with a total-attempt budget · 以总尝试预算做路由

> Route the caller body while keeping credentials private.

**Type:** Build
**Languages:** Go
**Stage:** 4 of 4
**Prerequisites:** Stage 1 到 3。在添加用量统计之前，先阅读 [Token Counter and Cost Meter](../../../../token-counter-and-cost-meter/README.md)。
**Time:** ~2 hours

## What you build · 你要构建什么

实现 `Route`：把已校验的端点只走一遍，在调用 `Attempt` 之前先记入 attempt，并记录状态码、耗时毫秒数和失败类别。遇到成功、terminal 状态、响应溢出、取消或调用次数上限就停止。即使没有调用方 deadline，也给整条路由一个五秒上限。

提供的 `RouteConfigured` 把你的 route 与更严格的操作者设置组合起来：1 到 5000 毫秒、响应上限以及具名 provider。它的 transport 用 `key_env` 生成 provider 专属的 Authorization 头，并可能改写 `model`。`GatewayHandler` 只复制 JSON body；调用方的请求头永远不会变成 provider 凭证。当提供的 transport 改写 model 时，Body、GetBody 和 ContentLength 必须描述同一份字节。Go 在复用连接上发生零字节写失败后可能重放请求；该重放必须保留已配置的 model。重定向保持禁用。

> Implement `Route` by walking validated endpoints once, charging attempts before calling `Attempt`, and recording status, elapsed milliseconds and failure kind. Stop on success, a terminal status, response overflow, cancellation or the call ceiling. Give the entire route a five-second maximum even without a caller deadline.
> Provided `RouteConfigured` composes your route with stricter operator settings: 1 through 5000 milliseconds, response ceiling and named providers. ... `GatewayHandler` copies the JSON body only; caller headers never become provider credentials. ... Redirects remain disabled.

## Worked example · 具体例子

primary 花了 35 ms 并返回 503。在 65 ms 的总 deadline 下，backup 大约只能得到 30 ms，而不是又一个 65 ms。当这个共享 context 到期时，返回 `State=cancelled`、到目前为止已完成的 attempts 以及 context 错误。

一次成功的代理请求，响应带有 `X-Gateway-Attempts: 2` 和 `X-Gateway-Provider: backup`。body 就是 backup 的真实响应。错误使用本地 502 响应，取消时用 504，并且不回显 provider 的错误 body。CLI 会输出更完整的 trace 供操作者检查。

```figure
pj-llm-gateway-with-fallbacks-4
```

> Primary takes 35 ms and returns 503. Under a 65 ms total deadline, backup receives roughly 30 ms, not another 65 ms. When that shared context expires, return `State=cancelled`, the attempts made so far and the context error.
> For a successful proxy request, the response carries `X-Gateway-Attempts: 2` and `X-Gateway-Provider: backup`. The body is the actual backup response. Errors use local 502 responses, or 504 for cancellation, without echoing provider error bodies. The CLI emits the fuller trace for operator inspection.

## Implement the contract · 实现契约

```go
func Route(ctx context.Context, client *http.Client, providers []string, payload string, maxAttempts int, maxBytes int64) (Outcome, error)
```

在任何一次 attempt 失败之后立即检查 `ctx.Err()`，包括最后一个 provider。否则一次超时可能被误标为普通的尝试耗尽。已配置的环境变量缺失时，应该在任何 provider 收到请求之前就失败。集成测试使用独立的本地服务器来观察两种凭证头。

> Check `ctx.Err()` immediately after a failed attempt, including the last provider. Otherwise a timeout may be mislabeled as ordinary exhaustion. Missing configured environment variables should fail before any provider receives a request. The integration tests use separate local servers to observe both credential headers.

## Run your work · 运行你的实现

在仓库根目录初始化一次；grader 会保留工作区中已有的文件：

```bash
python3 scripts/project_test.py llm-gateway-with-fallbacks --init /tmp/llm-gateway-with-fallbacks-work
python3 scripts/project_test.py llm-gateway-with-fallbacks --stage 4 --path /tmp/llm-gateway-with-fallbacks-work --strict
```

你的实现放在该工作区的 `stage4.go` 里。提供的适配器调用这些学习者函数；它们不会导入参考解法。各阶段的测试包含与 Orchard 演示相互独立的用例。

> From the repository root, initialize once; the grader preserves existing workspace files:
> Your implementation belongs in `stage4.go` in that workspace. Provided adapters call those learner functions; they do not import the reference solution. Stage tests include cases separate from the Orchard demonstration.

## Inspect and extend · 检查与扩展

在完成的工作区里运行 `go run .`：它会在临时 loopback 端口上启动 primary、backup 和代理，并在处理一个请求后关闭它们。要使用你自己的端点，复制 `fixtures/providers.example.json`，替换 model 名称，然后使用 `go run . --config /tmp/providers.json --request fixtures/request.json` 或 `--listen 127.0.0.1:8088`。这个服务器是本地的、非流式的、无鉴权的；它不是一个公开部署模板。

[Go standard-library reference](https://pkg.go.dev/context)。可运行核心只使用 Go 标准库。外部模型调用是可选的，在常规评分期间不会运行。

> Run `go run .` from the completed workspace: it starts a primary, backup and proxy on temporary loopback ports and closes them after one request. For your own endpoints, copy `fixtures/providers.example.json`, replace model names, then use `go run . --config /tmp/providers.json --request fixtures/request.json` or `--listen 127.0.0.1:8088`. The server is local, non-streaming and unauthenticated; it is not a public deployment template.
> [Go standard-library reference](https://pkg.go.dev/context). The runnable core uses only Go's standard library. External model calls are optional and do not run during ordinary grading.
