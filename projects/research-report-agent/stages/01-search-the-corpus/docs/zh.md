# Search the corpus · 检索语料库

> 检索决定了系统其余部分能用到哪些证据。
> Retrieval decides which evidence the rest of the system can use.

**Type:** Build
**Languages:** Rust, Python
**Stage:** 1 of 7 (starter)
**Time:** ~5 hours

## What you build · 你要构建什么

实现 `search/main.rs`：一个只用标准库的 Rust 引擎，加载 markdown 文档、构建 BM25 索引，并逐行处理一个 JSON 请求。Python 的 `report_agent/search.py` 负责编译并调用该引擎；它不实现第二套排序算法。

```figure
pj-rra-bm25
```

Rust 适合做索引工作，因为所有权（ownership）让索引的生命周期显式化，原生循环处理词频计数也很高效。Python 仍然只是一个薄薄的编排层。只有当双方都有清晰的契约、并且有测试驱动真实进程时，语言边界才有价值。

> Implement `search/main.rs`: a standard-library-only Rust engine that loads markdown documents, builds a BM25 index and handles one JSON request per line. Python's `report_agent/search.py` compiles and invokes that engine; it does not implement a second ranking algorithm.
> Rust fits the indexing work because ownership makes the index lifetime explicit and native loops handle term counts efficiently. Python remains a small orchestration layer. A language boundary is useful only when both sides have a clear contract and tests that exercise the real process.

## Parse the corpus · 解析语料库

每份文档以三行头部、一个空行和原始说明文字开头：

```text
title: A user-space kernel intercepts system calls
source_url: https://www.kernel.org/doc/html/latest/userspace-api/seccomp_filter.html
published: 2026-09-28

A user-space kernel implements an application kernel between a sandboxed process and the host.
```

fixture 语料库包含 12 篇关于隔离概念的原创笔记。来源链接指向作为支撑的官方规范或文档；这些笔记是教学用的 fixture，不是照抄的产品文档。缺失头部字段是错误。把正文与元数据分开保存，并在加载前对文件路径排序，这样测试就不依赖目录枚举顺序。

> Each document starts with three header lines, a blank line and original explanatory text:
> The fixture corpus contains 12 original notes on isolation concepts. Source links identify supporting official specifications or documentation; these notes are teaching fixtures, not copied product documentation. Missing header fields are errors. Keep the body separate from metadata, and sort file paths before loading them so tests do not depend on directory enumeration order.

## Build the index · 构建索引

对标题和正文做分词（tokenize），ASCII 字母转小写，保留数字，去掉给定的停用词（stopwords）。统计每个词在每个文档中出现了多少次，以及它出现在多少个文档中。文档频率（document frequency）数的是文档数，不是出现次数。

```text
idf(t) = log(1 + (N - df(t) + 0.5) / (df(t) + 0.5))
score(t,d) = idf(t) * tf(t,d) * (k1+1)
             / (tf(t,d) + k1 * (1-b + b*len(d)/avglen))
```

`k1=1.5` 时，一个词反复出现带来的增益随其词频增长而递减。`b=0.75` 时，长文档会得到长度修正。像 `interceptor` 这样的稀有词贡献比 `kernel` 大。把查询词的贡献求和，按分数降序、文档 id 升序排序。空查询或未知词返回空结果。

> Tokenize the title and body, lowercase ASCII letters, keep digits, and remove the provided stopwords. Count how often each term occurs in each document and in how many documents it occurs. Document frequency counts documents, not occurrences.
> With `k1=1.5`, repeating a word helps less as its frequency grows. With `b=0.75`, long documents receive a length correction. A rare term such as `interceptor` contributes more than `kernel`. Sum the contribution of query terms and sort by descending score, then ascending document id. An empty query or an unknown word returns no results.

## Define the process contract · 定义进程契约

一个请求包含一个操作和带类型的字段。引擎对每行响应都做 flush，并在 stdin 到达 EOF 时退出。诊断信息写到 stderr，这样 stdout 保持可解析的 JSON。

```json
{"query":"daemon socket","k":3}
```

```json
{"cmd":"tokenize","text":"The kernel, VM!"}
```

第二个请求精确返回 `{"tokens":["kernel","vm"]}`。该协议还支持 `idf`、`docs`、`doc` 和 `score`。非法 JSON 或字段类型错误返回一个 `error` 对象。给定的 codec 按 [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259) 处理字符串与转义，包括 Unicode 代理对（surrogate pairs）。带小数的结果条数是非法的；零是合法的「空结果」请求。

实现 `engine_binary()`，让它返回一个指向名为 `search` 的已编译可执行文件的 `pathlib.Path`。每个进程在全新的私有临时目录中编译一次，目录前缀为 `rra-private-build-`、权限模式 `0700`；在进程内复用该路径，并在退出时注册清理。永远不要信任可预测的共享可执行文件缓存。

每个索引把它的输入文档写进一个私有临时目录。使用 `subprocess.run` 的参数列表形式、超时和显式的返回码检查。永远不要把问题拼进 shell 命令。

> A request has an operation and typed fields. The engine flushes each response line and exits when stdin reaches EOF. It writes diagnostics to stderr so stdout remains parseable JSON.
> The second request returns exactly `{"tokens":["kernel","vm"]}`. The protocol also supports `idf`, `docs`, `doc` and `score`. Invalid JSON or wrong field types return an `error` object. The supplied codec handles strings and escapes according to [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259), including Unicode surrogate pairs. A fractional result limit is invalid; zero is a valid empty result request.
> Implement `engine_binary()` to return a `pathlib.Path` to the compiled executable named `search`. Compile once per process in a fresh private temporary directory with the prefix `rra-private-build-` and mode `0700`; reuse that path within the process and register cleanup on exit. Never trust a predictable shared executable cache.
> Each index writes its input documents to a private temporary directory. Use an argument list with `subprocess.run`, a timeout, and explicit return-code checks. Never put a question into a shell command.

## Your task · 你的任务

starter 提供了 `wire.rs`，负责 JSON 解析/转义和 stdin 循环。你要实现语料库解析器、分词器、`Index` 和 `handle_line`。用现有的 `engine_binary`、`BM25Index`、`search`、`score` 和 `idf` API 补全 Python 语料库加载器和适配器。之后 Python 的句子打分会复用同一条分词规则，而文档排序留在 Rust。

```bash
python3 scripts/project_test.py research-report-agent --init my-report-agent
python3 scripts/project_test.py research-report-agent --stage 1 --path my-report-agent
rustc --edition 2021 -O my-report-agent/search/main.rs -o /tmp/rra-search
printf '%s\n' '{"query":"daemon socket","k":3}' | /tmp/rra-search projects/research-report-agent/fixtures/corpus
```

> The starter provides `wire.rs` for JSON parsing/escaping and the stdin loop. Implement the corpus parser, tokenizer, `Index` and `handle_line`. Complete the Python corpus loader and adapter with the existing `engine_binary`, `BM25Index`, `search`, `score` and `idf` API. Python sentence scoring later reuses the same tokenization rule, while document ranking stays in Rust.

## What you should see · 预期结果

全新工作区会以清晰的 stage 1 实现提示信息失败。完成后的工作区通过 7 个 Rust 测试和 12 个 Python 集成测试。该查询把 `03-daemon-socket-escape` 排在第一位，分数为正；确切分数取决于 fixture 文本。原生测试覆盖非法 JSON、Unicode 往返、稀有词加权和确定性的平局处理。

> The fresh workspace fails with a clear stage 1 implementation message. A completed workspace passes 7 Rust tests and 12 Python integration tests. The query ranks `03-daemon-socket-escape` first, with a positive score; the exact score depends on the fixture text. The native tests cover malformed JSON, Unicode round trips, rare-term weighting and deterministic ties.

## Check yourself · 自检

为什么文档频率对一篇文档里重复出现的词只计一次？如果 stdout 在 JSON 响应之前混入了构建日志，会发生什么？哪个查询会被关键词搜索漏掉，因为相关笔记用的是同义词？

> Why does document frequency count a repeated term once per document? What happens if stdout contains a build log before its JSON response? Which query will keyword search miss because the relevant note uses a synonym?

## Going further · 进阶

只有在这条基线被测量之后，才去添加向量（embedding）索引并融合排序。保持线上格式（wire format）不变，这样 planner 和 writer 就能使用任意一个后端。

> Add an embedding index and fuse rankings only after this baseline is measured. Keep the wire format unchanged so the planner and writer can use either backend.

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html)和[检索增强生成](../../../../../phases/11-llm-engineering/06-rag/docs/en.md)。

从检索开始，而不是把它当成一份 JSON 解析器作业。starter 提供了 wire.rs 和 stdin 管道。你实现语料库校验、分词、BM25 索引和 Python 进程适配器。Rust 编译进每个进程私有的目录。

```text
N=2, df(orchard)=2 -> idf=log(1.2)=0.1823
df(expiration)=1 -> idf=log(2)=0.6931
rare expiration term receives more weight
```

> Begin with retrieval, not a JSON parser assignment. The starter supplies wire.rs and stdin plumbing. You implement corpus validation, tokenization, BM25 indexing and the Python process adapter. Rust builds into a private per-process directory.

## Build and inspect · 构建并检查

分别跟踪一次词频计数和一次文档频率计数。除非你选择可选的 codec 扩展，否则传输代码留在 wire.rs。

在你的学习工作区（learner workspace）中实现该阶段。这些 CLI 辅助工具是给定的适配器，它们导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py research-report-agent --init learning-artifacts/research-report-agent
python3 scripts/project_test.py research-report-agent --stage 1 --path learning-artifacts/research-report-agent
```

先预测上面的中间状态，再运行该阶段。全新的 stub 会失败；参考实现跑通并不代表你的学习工作区已经完成。

> Trace one term count and one document-frequency count separately. Keep transport code in wire.rs unless you choose the optional codec extension.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 下一步探究

为什么一个重复出现的词会增大词频（term frequency），却不增大文档频率（document frequency）？

> Why does a repeated term increase term frequency but not document frequency?
