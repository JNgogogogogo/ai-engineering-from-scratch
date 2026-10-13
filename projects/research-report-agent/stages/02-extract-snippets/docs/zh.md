# Extract snippets you can cite · 提取可引用的片段

> 指向整篇文档的引用什么都证明不了。要指向确切的那个句子。
> A citation that points at a whole document proves nothing. Point at the exact sentence.

**Type:** Build
**Languages:** Python
**Stage:** 2 of 7 (starter)
**Time:** ~2 hours

## What you build · 你要构建什么

`report_agent/snippets.py`：

- `split_sentences(text)` 返回每个句子的 `(start, end)` 区间（span）。
- `score_sentence(sentence, query_tokens, idf)` 用一个查询给一个句子打分。
- `extract_snippets(query, index, ...)` 在排名靠前的文档中返回最好的 `Snippet` 对象。

一个 `Snippet` 持有 `id`、`doc_id`、`start`、`end`、`text` 和 `score`，并且永远满足：

```python
document.text[snippet.start:snippet.end] == snippet.text
```

> `split_sentences(text)` returns `(start, end)` spans for each sentence.
> `score_sentence(sentence, query_tokens, idf)` scores one sentence against a query.
> `extract_snippets(query, index, ...)` returns the best `Snippet` objects across the top documents.
> A `Snippet` holds `id`, `doc_id`, `start`, `end`, `text` and `score`, and always satisfies:

## Why it matters · 为什么重要

一个引用有两个相互独立的属性：它的标记能解析到某个来源，并且那个来源支撑该论断。一个合法的链接仍可能指向一个在说别的事情的句子。精确的证据区间（span）让这个区别变得可测试。

你没法低成本地拿一个论断去核对整个网页，读者也不会这么做。偏移量（offset）让每个引用都能一次查找就完成核对：打开文档、切出 `[start:end]`、读那个句子。第 5 阶段的 critic 和第 6 阶段的脚注都依赖这一点。

> A citation has two separate properties: its marker resolves to a source, and that source supports the claim. A valid link can still point to a sentence that says something else. Exact evidence spans make this distinction testable.
> You cannot check a claim against a whole web page cheaply, and a reader will not either. Offsets make every citation checkable in one lookup: open the document, slice `[start:end]`, read the sentence. The critic in stage 5 and the footnotes in stage 6 both depend on this.

## Sentence spans · 句子区间

在 `.`、`!` 或 `?` 处切分，条件是空白之后的下一个字符开始一个新句子，或者已经到达文本末尾。在这个语料库中有两个细节很重要：

```text
The socket is at /var/run/container.sock. Any process can write.
                            ^ not a boundary      ^ boundary
It is slower. user-space kernel is still useful.
             ^ boundary, even though user-space kernel starts lowercase
```

让区间不带前后空白，这样 `text[start:end]` 是干净的。

> Split at `.`, `!` or `?` when the next character after whitespace starts a new sentence, or at the end of the text. Two details matter in this corpus:
> Keep spans free of surrounding whitespace so `text[start:end]` is clean.

## Scoring sentences · 给句子打分

复用第 1 阶段的 IDF 表：

```python
score = sum(idf[t] for t in set(query_tokens) if t in tokenize(sentence))
```

然后应用两条让片段能独立成意的规则：

| 规则 | 原因 |
|---|---|
| 少于 `min_words`（6）个词的句子得 0 分 | "The tradeoff is overhead." 脱离上下文什么也没说 |
| 句子以 It、This、These、They 等开头则分数减半 | "It uses a limited set of calls" 没说 "it" 指什么 |

真实系统用去上下文化（decontextualization）解决第二个问题：改写句子，使它能独立成立。这个惩罚是廉价版本。

```figure
pj-rra-snippet-offsets
```

> Real systems solve the second problem with decontextualization: rewriting a sentence so it stands alone. The penalty is the cheap version.

## Follow the mechanism · 理解机制

偏移量是「去除空白后的文档正文」中的位置，不是完整 markdown 文件中的位置。永远不要在选出的句子上调用 `.strip()` 却不相应调整它的 start 和 end。如果来源变了，旧偏移量可能仍能解析出文本，但不再解析出同一个论断；第 6 阶段会再次检查这个等式。

> Offsets are positions in the stripped document body, not the full markdown file. Never call `.strip()` on a chosen sentence without adjusting its start and end. If the source changes, an old offset may still resolve to text but no longer resolve to the same claim; stage 6 checks that equality again.

## Your task · 你的任务

```python
def split_sentences(text: str) -> list[tuple[int, int]]: ...
def score_sentence(sentence, query_tokens, idf, min_words=6) -> float: ...
def extract_snippets(query, index, k_docs=4, per_doc=3, start_id=1,
                     min_score=0.0, doc_ids=None) -> list[Snippet]: ...
```

`extract_snippets` 在排名前 `k_docs` 的文档中搜索（给了 `doc_ids` 时只搜这些文档），每篇文档最多保留 `per_doc` 个句子，把所有候选按分数排序，并给它们编号 `S{start_id}`、`S{start_id + 1}` 依次类推。

> `extract_snippets` searches the top `k_docs` documents (or only `doc_ids` when given), keeps up to `per_doc` sentences per document, sorts all candidates by score, and numbers them `S{start_id}`, `S{start_id + 1}` and so on.

## Run the tests · 运行测试

```bash
python3 scripts/project_test.py research-report-agent --stage 2 --path my-report-agent
```

各阶段累计运行，所以第 1 阶段必须仍然通过。

> Stages run cumulatively, so stage 1 must still pass.

## What you should see · 预期结果

第 2 阶段通过 11 个 Python 测试，且此前所有阶段仍然通过。每个返回的片段都精确复现其来源切片，包括点分 socket 路径之后的文本。测试还覆盖小写开头的句子、连续 id 和每文档限额。

> Stage 2 passes 11 Python tests, and all preceding stages still pass. Every returned snippet reproduces its source slice exactly, including text after a dotted socket path. The tests also cover lowercase sentence starts, sequential ids and per-document limits.

## Check yourself · 自检

1. 为什么存偏移量，而不是只存句子文本？
2. `04-user-space-kernel.md` 里哪个句子丢了一半分数？如果把它丢掉，读者会错过什么？
3. 如果你的切分器把 `container.sock.` 当成两个句子，会破坏什么？

> 1. Why store offsets instead of just the sentence text?
> 2. Which sentence in `04-user-space-kernel.md` loses half its score, and would a reader miss anything if it were dropped?
> 3. What breaks if your splitter treats `container.sock.` as two sentences?

## Going further · 进阶

- 返回包含相邻句子的一小段窗口作为上下文，同时仍引用精确区间。
- 用一个小模型把句子改写到能独立成立，以此替换代词惩罚，并保存两个版本。

> - Return a window of the neighbouring sentence as context, while still citing the exact span.
> - Replace the pronoun penalty with a small model that rewrites the sentence to stand alone, and store both versions.

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html)和[检索增强生成](../../../../../phases/11-llm-engineering/06-rag/docs/en.md)。先完成[阶段 1](../../01-search-the-corpus/docs/en.md)。

Orchard 政策句只有在它存储的区间能复现精确文档文本时才是证据。偏移量属于规范化（normalized）后的文档正文，不属于文件头部或渲染后的 HTML。

```text
source: "Old rule. New rule."
second span=[10,19)
source[10:19]="New rule."
```

> The Orchard policy sentence is evidence only if its stored span reproduces the exact document text. Offsets belong to the normalized document body, not to the file header or rendered HTML.

## Build and inspect · 构建并检查

在原始字符串上找边界，通过移动偏移量来修剪。算出区间之后永远不要改写片段。

在你的学习工作区（learner workspace）中实现该阶段。这些 CLI 辅助工具是给定的适配器，它们导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py research-report-agent --stage 2 --path learning-artifacts/research-report-agent
```

先预测上面的中间状态，再运行该阶段。全新的 stub 会失败；参考实现跑通并不代表你的学习工作区已经完成。

> Find boundaries on the original string and trim by moving offsets. Never rewrite a snippet after computing its span.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 下一步探究

当来源文本在某个片段 start 偏移量之前被编辑过，这个旧片段会怎样？

> What happens to an old snippet when the source text is edited before its start offset?
