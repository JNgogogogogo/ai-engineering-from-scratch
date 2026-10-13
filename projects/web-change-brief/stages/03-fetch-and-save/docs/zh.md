# Fetch one page without losing the baseline · 抓取一个页面，且不丢掉基线

> Bound live HTTP work and verify saved snapshot integrity.

**Type:** Build  
**Language:** Go  
**Stage:** 3 of 4  
**Time:** About 2 hours

## What you are building · 你在造什么

一次失败的抓取绝不能变成下一份基线。先抓取并校验；再计算并写出报告；只有通过显式动作才能替换旧基线。CLI 每次调用只做一次这件事。它不创建周期性的监控。

```figure
pj-web-change-brief-3
```

> A failed fetch must not become the next baseline. Fetch and validate first; compute and write the report; replace a prior baseline only through an explicit action. The CLI does this once per invocation. It does not create a recurring monitor.

## Work through an example · 走一遍例子

返回 HTTP 503 的页面在解析之前就失败。大于 2 MB 的成功 HTML 响应同样失败。重定向到不同主机需要一个新的显式 URL。有效的已存基线可以经 JSON 往返（round-trip）；改动块文本却不更新摘要（digest）会让 LoadSnapshot 失败。

写代码之前，先为这个例子写下返回字段，以及一个应当失败的输入。把预期结果放在实现旁边，才能区分「契约变了」和「出了 bug」。

> A page returning HTTP 503 fails before parsing. A successful HTML response larger than 2 MB also fails. A redirect to a different host requires a new explicit URL. A valid saved baseline round-trips through JSON, while changing its block text without updating the digest makes LoadSnapshot fail.
> Before coding, write down the returned fields for that example and one input that should fail. Keep the expected result beside your implementation so you can distinguish a contract change from a bug.

## Implement the contract · 实现契约

- `FetchHTML(ctx context.Context, rawURL string, client *http.Client) (string, error)`
- `SaveSnapshot(path string, snapshot Snapshot) error`
- `LoadSnapshot(path string) (Snapshot, error)`

只接受无凭据的 HTTP(S) URL、状态码 200，以及 text/html 或 application/xhtml+xml。按 MaxHTMLBytes+1 的上限读取以检测溢出。应用取消（cancellation）和默认 15 秒的客户端超时，最多三次请求且重定向限同主机（显式端口保持不变）。所选 URL 用 HTTPS 时，每个重定向都必须保持 HTTPS。显式选择的 HTTP URL 仍然受支持。通过同目录下的临时文件保存，随后 rename。Load 校验规范化 URL 和内容校验和。

保持此前阶段可用。在你的学习工作区（learner workspace）里实现这些函数，走例子的过程中让参考解法保持关闭。

> Accept only HTTP(S) URLs without credentials, status 200, and text/html or application/xhtml+xml. Read through a limit of MaxHTMLBytes+1 to detect overflow. Apply cancellation and a default 15-second client timeout, with at most three requests and same-host redirects (including an unchanged explicit port). When the selected URL uses HTTPS, every redirect must keep HTTPS. An explicitly selected HTTP URL remains supported. Save via a temporary file in the same directory followed by rename. Load validates the canonical URL and content checksum.
> Keep earlier stages working. Implement these functions in your learner workspace, leaving the reference solution closed while you work through the example.

## Hints and failure cases · 提示与失败场景

用 httptest.NewServer 在不联网的情况下测试真实响应。把超时/取消的测试与状态码处理分开。同目录临时文件让 rename 语义局限在一个文件系统内。即使出错也要删除临时文件。

> Use httptest.NewServer to test actual responses without the internet. Test timeout/cancellation separately from status handling. A same-directory temporary file keeps rename semantics local to one filesystem. Delete temporary files even on errors.

## Run your stage · 跑你的阶段

从仓库根目录初始化一次，然后运行累积测试：

```bash
python3 scripts/project_test.py web-change-brief --init my-web-change-brief
python3 scripts/project_test.py web-change-brief --stage 3 --path my-web-change-brief
```

启动代码（starter）故意抛出一个实现错误。之后再次初始化会保留你的源码而不是替换它。通过的结果要求每个被选中的测试都真正运行过；被跳过的测试不算完成证据。

> Initialize once from the repository root, then run the cumulative tests:
> The starter deliberately raises an implementation error. Later initialization preserves your source rather than replacing it. A passing result requires every selected test to run; a skipped test is not completion evidence.

## Check your reasoning · 检查你的推理

抓取成功就意味着你看到了客户端 JavaScript 生成的内容吗？哪些服务器或限流行为应该对运行这个工具的人保持可见？

> Does a successful fetch mean you saw content produced by client-side JavaScript? Which server or rate-limit behavior should remain visible to the person running this tool?

## Connect it to the finished artifact · 连接到完成品

一个独立的变更报告 changes.json，以及一个可复用的 baseline.json 快照。这个抽取器是一个刻意受限的可读块扫描器，不是 HTML5 DOM，也不是浏览器。它不执行 JavaScript、不求值 CSS 可见性，也不抓取链接资源。块顺序被忽略；重复文本的计数被保留。过滤短语可能藏掉有用的变更，所以对两个快照要用同一条显式过滤策略。

完成项目之后，用你自己的输入试试：

```bash
cd my-web-change-brief
go run . --before fixtures/before.html --after fixtures/after.html --url https://example.invalid/makerspace --out ./web-change-output
```

支持带 ETag 或 Last-Modified 的条件请求（conditional request），保留「内容未变」「请求失败」「空页面」三者之间的区别。把调度（scheduling）留在抓取函数之外。

> A standalone change report, changes.json and a reusable baseline.json snapshot. The extractor is a deliberately limited readable-block scanner, not an HTML5 DOM or browser. It does not execute JavaScript, evaluate CSS visibility or fetch linked resources. Block order is ignored; repeated text counts are retained. Filtering phrases can hide useful changes, so use the same explicit filter policy for both snapshots.
> After completing the project, try your own inputs:
> Support conditional requests with ETag or Last-Modified, preserving the distinction between unchanged content, a failed request and an empty page. Keep scheduling outside the fetch function.

## Primary reference · 主要参考

[Official API documentation](https://pkg.go.dev/net/http)（官方 API 文档）。实现、示例和夹具均为原创。参考文档解释底层 API；项目特有的策略已在上面写明。

> [Official API documentation](https://pkg.go.dev/net/http). The implementation, examples and fixtures are original. The reference explains the underlying API; the project-specific policies are stated above.
