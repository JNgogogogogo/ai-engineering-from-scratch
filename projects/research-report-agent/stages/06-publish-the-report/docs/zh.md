# Publish the report · 发布报告

> 一份给人看的报告和一份机器可读的 trace，服务的是不同的读者。
> A readable report and a machine-readable trace serve different readers.

**Type:** Build
**Languages:** Python, TypeScript
**Stage:** 6 of 7 (core)
**Time:** ~2 hours

## What you build · 你要构建什么

Python 运行管道并序列化 `report.json` 和 `trace.json`。`viewer/render.ts` 消费这些 JSON，产出一个自包含的 `report.html`。这个 viewer 是货真价实的 TypeScript，带有针对小节、句子、片段、文档和 trace 的接口（interface）。使用 Node 22.18 或更新版本，配合内建的类型剥离（type stripping）；经过验证的本地运行时是 Node 25.6.1。

```figure
pj-rra-publish
```

一个 JSON 边界迫使发布契约在序列化之后依然成立。把 Python 对象直接传进模板不会测试到这个边界。TypeScript 的类型注解为契约做文档，而运行时校验负责拒绝格式损坏的文件，因为类型并不能校验 JSON。

> Python runs the pipeline and serializes `report.json` plus `trace.json`. `viewer/render.ts` consumes the JSON and produces a self-contained `report.html`. The viewer is actual TypeScript with interfaces for sections, sentences, snippets, documents and traces. Use Node 22.18 or newer with built-in type stripping; the verified local runtime was Node 25.6.1.
> A JSON boundary forces the publishing contract to survive serialization. Passing a Python object directly into a template would not test that boundary. TypeScript's type annotations document the contract, while runtime validation rejects malformed files because types do not validate JSON.

## Keep the evidence contract intact · 保持证据契约完好

```json
{
  "schema_version": 1,
  "question": "How does a secrets proxy protect credentials?",
  "sections": [],
  "snippets": {},
  "documents": [],
  "trace": null
}
```

每个被渲染的引用都必须解析到一个片段和一个文档。要核实原始文档切片与片段文本相等。Python 的偏移量按 Unicode 码点（code point）计数；JavaScript 的字符串切片按 UTF-16 单元计数。使用 `[...source.text].slice(start, end).join('')`，这样前导的 emoji 就不会移动证据区间。

脚注按首次出现的顺序编号。在两个句子里复用 `S4` 应该产生两个参考链接和一个脚注。即使脚注被复用，tooltip 的 id 也必须保持唯一。对问题文本、小节标题、来源标题、片段和 trace 细节做转义。来源链接只允许 HTTP 或 HTTPS；仅靠 HTML 转义不能中和一个 `javascript:` URL。

> Every rendered citation must resolve to a snippet and a document. Verify that the original document slice equals the snippet text. Python offsets count Unicode code points; JavaScript string slices count UTF-16 units. Use `[...source.text].slice(start, end).join('')` so a preceding emoji does not shift the evidence span.
> Number footnotes by first appearance. Reusing `S4` in two sentences should produce two reference links and one footnote. Tooltip ids must remain unique even when the footnote is reused. Escape question text, section headings, source titles, snippets and trace details. Restrict source links to HTTP or HTTPS; HTML escaping alone does not neutralize a `javascript:` URL.

## Make the artifact usable · 让工件可用

引用在悬停或键盘聚焦时揭示它确切的来源句子。点击它会跳到编号的注释。原生 `<details>` 无需客户端框架或 JavaScript 就能展示运行 trace。页面尊重浅色与深色配色偏好，并适配手机视口。

报告作为本地文件依然可用。它的交互只用 HTML 和 CSS，因此阅读它不需要任何网络服务或安装包。

> A citation reveals its exact source sentence on hover or keyboard focus. Clicking it jumps to the numbered note. Native `<details>` exposes the run trace without requiring a client framework or JavaScript. The page honors light and dark color preferences and fits a phone viewport.
> The report still works as a local file. Its interaction uses HTML and CSS, so there is no network service or package installation required to read it.

## Trace the pipeline · 追踪管道

按顺序运行并扣费这些步骤：`index`、`plan`、`gather`、`write`、`verify`。每条记录包含一个名称、经过的毫秒数和结构化的细节。在 trace 中保留 `run_id`、`question`、`started_at`、`counts`、`budget` 和 `terminal_state`。

预算耗尽会追加 `budget_exceeded`、产生 `failed` 状态，并渲染出截至目前收集到的证据。要区分一个有用的失败工件和一次渲染器崩溃。当一次运行无法收集到被支撑的论断时，空报告是合法的。

> Run and charge these steps in order: `index`, `plan`, `gather`, `write`, `verify`. Each record contains a name, elapsed milliseconds and structured details. Preserve `run_id`, `question`, `started_at`, `counts`, `budget` and `terminal_state` in the trace.
> A budget exhaustion appends `budget_exceeded`, produces state `failed`, and renders the evidence collected so far. Distinguish a useful failed artifact from a renderer crash. Empty reports are valid when a run could not collect supported claims.

## Your task · 你的任务

补全管道、Python 负载序列化器和进程适配器，外加带类型的渲染器。`run_pipeline` 返回 `(report, trace, html)`，并在提供了输出目录时写出全部三个文件。

```bash
python3 scripts/project_test.py research-report-agent --stage 6 --path my-report-agent
python3 projects/research-report-agent/solution/run_report.py \
  "How does a secrets proxy protect API keys from prompt injection?" \
  --code my-report-agent --out out
node my-report-agent/viewer/render.ts out/report.json out/report.html
open out/report.html
```

> Complete the pipeline, Python payload serializer and process adapter, plus the typed renderer. `run_pipeline` returns `(report, trace, html)` and writes all three files when an output directory is supplied.

## What you should see · 预期结果

参考命令产生 `completed` 状态、4 个小节和 10 个句子，0 个被丢弃。目录里有 `report.json`、`report.html` 和 `trace.json`。悬停或聚焦 `[1]` 看到一段精确引文，然后打开运行 trace 检查全部五个步骤。耗时和 run id 在各次执行之间不同。

第 6 阶段有 7 个 Node 测试和 7 个 Python 集成测试。它们检查 Unicode 偏移量、转义、不安全 URL、重复引用、悬空证据和小预算失败。

> The reference command produces state `completed`, 4 sections and 10 sentences with 0 dropped. The directory contains `report.json`, `report.html` and `trace.json`. Hover or focus `[1]` to see an exact quote, then open the run trace to inspect all five steps. Timings and run ids differ between executions.
> Stage 6 has 7 Node tests and 7 Python integration tests. They check Unicode offsets, escaping, unsafe URLs, duplicate citations, dangling evidence and a tiny-budget failure.

## Check yourself · 自检

为什么即使渲染器是带类型的，JSON 也必须经过运行时校验？为什么在 emoji 之后 Python 和 JavaScript 的偏移量会不一致？当一份报告没有任何小节时，工程师需要从 trace 里得到什么？

> Why must JSON receive runtime validation even when the renderer is typed? Why do the Python and JavaScript offsets disagree after an emoji? What would an engineer need from the trace when a report has no sections?

## Going further · 进阶

添加一个分页感知脚注的打印样式表，或者把被丢弃的论断渲染到一个独立的审核小节里。让不被支撑的论断与已发布的证据在视觉上明显区分。

> Add a print stylesheet with page-aware footnotes, or render dropped claims in a separate review section. Keep unsupported claims visibly distinct from published evidence.

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html)和[检索增强生成](../../../../../phases/11-llm-engineering/06-rag/docs/en.md)。先完成[阶段 5](../../05-verify-every-claim/docs/en.md)。

为 TypeScript viewer 和独立的 report judge 发布同一个带版本号的报告负载。Orchard 前后对比的走查会写出 changes.json，列出被移除的论断、新增的论断和变化的来源区间。

```text
report.json -> viewer + judge
60-minute sentence -> removed_claims
15-minute sentence -> added_claims
```

> Publish one versioned report payload for the TypeScript viewer and the separate report judge. The Orchard before/after walkthrough writes changes.json listing removed claims, added claims and changed source spans.

## Build and inspect · 构建并检查

在发布时再次校验来源切片。在 HTML 渲染之前转义文本；来源内容是数据，不是可执行标记。

在你的学习工作区（learner workspace）中实现该阶段。这些 CLI 辅助工具是给定的适配器，它们导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py research-report-agent --stage 6 --path learning-artifacts/research-report-agent
```

先预测上面的中间状态，再运行该阶段。全新的 stub 会失败；参考实现跑通并不代表你的学习工作区已经完成。

> Validate source slices again at publication. Escape text before HTML rendering; source content is data, not executable markup.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 下一步探究

审阅者如何区分「论断变了」和「措辞未变但支撑证据变了」？

> How can a reviewer distinguish a changed claim from unchanged wording supported by changed evidence?
