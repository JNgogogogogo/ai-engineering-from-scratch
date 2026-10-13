# Send one bounded HTTP request · 发送一个有界的 HTTP 请求

> Bound one request in both bytes and time.

**Type:** Build
**Languages:** Go
**Stage:** 3 of 4
**Prerequisites:** Stage 1 和 2。理解 Go 的 context 和 `io.Reader` 的所有权。
**Time:** ~2 hours

## What you build · 你要构建什么

实现 `Attempt(ctx, client, endpoint, payload, maxBytes)`。用调用方 HTTP client 的一份副本发送 JSON POST，禁用重定向，并且总是关闭响应 body。拒绝 nil client、超过 1 MiB 的请求体，以及不在 1 到 16 MiB 之间的响应上限。

即使调用方传入 `context.Background()`，也要加上五秒的 context deadline。调用方更早设置的 deadline 仍然优先。标准 HTTP transport 在建立连接和读取 body 期间都会响应取消。

> Implement `Attempt(ctx, client, endpoint, payload, maxBytes)`. Send a JSON POST using a copy of the caller's HTTP client, disable redirects, and always close the response body. Refuse nil clients, request bodies over one MiB and response limits outside 1 through 16 MiB.
> Add a five-second context deadline even when the caller passes `context.Background()`. An earlier caller deadline still wins. The standard HTTP transport observes cancellation while connecting and reading the body.

## Worked example · 具体例子

响应上限为 5、body 为 `0123456789` 时，最多读六个字节。读到第六个字节即可确认溢出，因此返回 `ErrLimit`，不保留完整响应。恰好五个字节时，返回 body 和状态码。

307 响应带有一个 `Location` 头。把这个响应交给 terminal 分类；不要向新 host 再发送请求。调用结束后，原 client 的 `CheckRedirect` 字段保持不变。

```figure
pj-llm-gateway-with-fallbacks-3
```

> With response limit 5 and body `0123456789`, read at most six bytes. Seeing six establishes overflow, so return `ErrLimit` without retaining the entire response. With exactly five bytes, return the body and status.
> A 307 response contains a `Location` header. Return that response for terminal classification; do not send another request to the new host. The original client's `CheckRedirect` field remains unchanged after the call.

## Implement the contract · 实现契约

```go
func Attempt(ctx context.Context, client *http.Client, endpoint, payload string, maxBytes int64) (Reply, error)
```

使用 `io.LimitReader(body, maxBytes+1)`，让「恰好装满」和「溢出」仍然可以区分。只给每个请求单独设超时对最终路由来说并不够：stage 4 还要让所有 attempt 共享同一个 deadline。自定义 `RoundTripper` 必须像标准 transport 一样响应 context 取消。

> Use `io.LimitReader(body, maxBytes+1)` so exact-fit and overflow remain distinguishable. A timeout on each request alone is insufficient for the final route: stage 4 also shares one deadline across all attempts. A custom `RoundTripper` must honor context cancellation just as the standard transport does.

## Run your work · 运行你的实现

在仓库根目录初始化一次；grader 会保留工作区中已有的文件：

```bash
python3 scripts/project_test.py llm-gateway-with-fallbacks --init /tmp/llm-gateway-with-fallbacks-work
python3 scripts/project_test.py llm-gateway-with-fallbacks --stage 3 --path /tmp/llm-gateway-with-fallbacks-work --strict
```

你的实现放在该工作区的 `stage3.go` 里。提供的适配器调用这些学习者函数；它们不会导入参考解法。各阶段的测试包含与 Orchard 演示相互独立的用例。

> From the repository root, initialize once; the grader preserves existing workspace files:
> Your implementation belongs in `stage3.go` in that workspace. Provided adapters call those learner functions; they do not import the reference solution. Stage tests include cases separate from the Orchard demonstration.

## Inspect and extend · 检查与扩展

测试一个恰好装满的 body、一个超出一字节的 body，以及一次重定向到另一台本地测试服务器。被重定向的服务器的请求计数必须保持为零。完成所有阶段之后，在你的工作区里用 `go run .` 运行真实的 loopback 演示。

[Go standard-library reference](https://pkg.go.dev/context)。可运行核心只使用 Go 标准库。外部模型调用是可选的，在常规评分期间不会运行。

> Test an exactly full body, a body one byte too large, and a redirect to another local test server. The redirected server's request count must remain zero. After implementing all stages, run the actual loopback demo with `go run .` in your workspace.
> [Go standard-library reference](https://pkg.go.dev/context). The runnable core uses only Go's standard library. External model calls are optional and do not run during ordinary grading.
