# Validate provider endpoints · 校验 provider 端点

> Treat the provider list as trusted configuration.

**Type:** Build
**Languages:** Go
**Stage:** 1 of 4
**Prerequisites:** Go 的 structs、slices、errors 和基础 HTTP 请求。阅读 [structured outputs](../../../../../phases/11-llm-engineering/03-structured-outputs/docs/en.md) 了解严格的 JSON 契约。
**Time:** ~2 hours

## What you build · 你要构建什么

在打开任何连接之前先实现 `Endpoints(values)`。允许 HTTPS，外加仅允许 `localhost`、`127.0.0.1` 或 `::1` 上的 HTTP（面向本地服务）。拒绝 userinfo、fragment、query、换行符、缺失 host 以及其他 scheme。在保持 provider 顺序的前提下去除完全相同的重复项。

CLI 配置包含 provider 名称、URL、可选的 model 覆盖项和凭证环境变量的名字。它从不接受凭证值本身。拒绝 query 字符串能把 bearer key 挡在端点 URL 和 trace 之外；这个小网关不支持基于 query 的 API 版本。

> Implement `Endpoints(values)` before opening a connection. Allow HTTPS, plus HTTP on exactly `localhost`, `127.0.0.1` or `::1` for local services. Reject userinfo, fragments, queries, line breaks, missing hosts and other schemes. Remove exact duplicates while preserving provider order.
> The CLI configuration contains provider names, URLs, optional model overrides and credential environment-variable names. It never accepts a credential value. Rejecting query strings keeps bearer keys out of endpoint URLs and traces; this small gateway does not support query-based API versions.

## Worked example · 具体例子

输入顺序是 primary `https://primary.example/v1/chat/completions`、再来一次 primary，然后是 `http://127.0.0.1:11434/v1/chat/completions`。校验后的列表按此顺序保留两个条目。因此 primary 失败后可以落到本地 fallback。

把最后一个 host 改成 `local-model.example` 并保持 HTTP：拒绝整个列表。主机名里出现 “local” 这个词并不能证明它是一条 loopback 连接。包含 `user:password@host` 的 URL 会在请求发出之前被拒绝。

```figure
pj-llm-gateway-with-fallbacks-1
```

> Input order is primary `https://primary.example/v1/chat/completions`, primary again, then `http://127.0.0.1:11434/v1/chat/completions`. The validated list has two entries in that order. A primary failure can therefore reach the local fallback.
> Change the final host to `local-model.example` while keeping HTTP. Reject the entire list. The word “local” in a hostname does not prove a loopback connection. A URL containing `user:password@host` is rejected before a request can be sent.

## Implement the contract · 实现契约

```go
func Endpoints(values []string) ([]string, error)
```

用 `net/url` 解析，检查 `Hostname`，并维护一个单独的 seen 集合。不要对端点排序：顺序本身就是 fallback 策略。服务端只接受来自操作者（operator）的配置，绝不接受来自传入 JSON 请求字段的配置。

> Parse with `net/url`, inspect `Hostname`, and maintain a separate seen set. Do not sort endpoints: order is the fallback policy. The server accepts configuration from the operator, never from incoming JSON request fields.

## Run your work · 运行你的实现

在仓库根目录初始化一次；grader 会保留工作区中已有的文件：

```bash
python3 scripts/project_test.py llm-gateway-with-fallbacks --init /tmp/llm-gateway-with-fallbacks-work
python3 scripts/project_test.py llm-gateway-with-fallbacks --stage 1 --path /tmp/llm-gateway-with-fallbacks-work --strict
```

你的实现放在该工作区的 `stage1.go` 里。提供的适配器调用这些学习者函数；它们不会导入参考解法。各阶段的测试包含与 Orchard 演示相互独立的用例。

> From the repository root, initialize once; the grader preserves existing workspace files:
> Your implementation belongs in `stage1.go` in that workspace. Provided adapters call those learner functions; they do not import the reference solution. Stage tests include cases separate from the Orchard demonstration.

## Inspect and extend · 检查与扩展

用控件添加一个重复项或修改一个 URL scheme。为什么 `https://a.example?api_key=...` 必须失败？端点校验并不能证明一个已配置的 HTTPS 服务是可信的；这个选择由操作者负责。

[Go standard-library reference](https://pkg.go.dev/context)。可运行核心只使用 Go 标准库。外部模型调用是可选的，在常规评分期间不会运行。

> Use the controls to add a duplicate or change a URL scheme. Why must `https://a.example?api_key=...` fail? Endpoint validation does not establish that a configured HTTPS service is trustworthy; the operator owns that selection.
> [Go standard-library reference](https://pkg.go.dev/context). The runnable core uses only Go's standard library. External model calls are optional and do not run during ordinary grading.
