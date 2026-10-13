# Write only from evidence · 只从证据写作

> 写作器（writer）不被允许知道任何事。它只能排列搜索找到的东西。
> The writer is not allowed to know anything. It may only arrange what search found.

**Type:** Build
**Languages:** Python
**Stage:** 4 of 7 (core)
**Time:** ~2 hours

## What you build · 你要构建什么

- `report_agent/citations.py`：读取引用标记、切分报告句子，并校验每个句子都引用了一个存在的片段（snippet）。
- `report_agent/writer.py`：为每个 facet 收集片段、据此写出小节，并渲染 markdown。

一个完成的句子长这样：

```text
Each microVM runs its own guest kernel [S4].
```

> `report_agent/citations.py`: read citation markers, split report sentences, and validate that every sentence cites a snippet that exists.
> `report_agent/writer.py`: gather snippets for every facet, write sections from them, and render markdown.
> A finished sentence looks like this:

## Why it matters · 为什么重要

生成报告中最常见的失败，是一句流畅却没有来源的句子，或者一个来源被挂到了它并不支撑的句子上。修复方法是结构性的，而不是更好的提示词：定义一种引用格式，然后拒绝任何破坏它的输出。强大的报告系统在代码里强制接地（grounding），比如让写作器只从抽取出的、编号过的证据中取材。弱的系统则客客气气地请求模型，然后祈祷。

本阶段构建一个抽取式（extractive）写作器：每个句子都是一个片段，原样复制，带上它的 id。它刻意无趣。它给你一份「由构造保证正确」的报告，以及一个在你换成能写真正散文的模型之后仍会保留的校验器。

> The most common failure in generated reports is a fluent sentence with no source, or a source attached to a sentence it does not support. The fix is structural, not a better prompt: define a citation format, then reject any output that breaks it. Strong report systems enforce grounding in code, for example by making the writer work only from extracted, numbered evidence. Weak ones ask the model nicely and hope.
> This stage builds an extractive writer: every sentence is a snippet, copied, with its id. It is boring on purpose. It gives you a report that is correct by construction, and a validator you will keep when you swap in a model that writes real prose.

## The citation contract · 引用契约

| 规则 | 反例 |
|---|---|
| 每个句子以一个或多个标记结尾，然后是句号 | `Containers share a kernel.` |
| 每个标记指向一个已知的片段 | `Containers share a kernel [S99].` |
| 标题不是句子 | `## Overview` is skipped |

`validate_citations(markdown, snippet_ids)` 返回一个 `CitationError(sentence, reason)` 列表，reason 为 `uncited` 或 `dangling:S99`。空列表表示合法。

一个微妙的切分点：`user-space kernel` 是小写开头，所以 "... workloads [S1]. user-space kernel is ..." 也必须在 `[S1].` 之后切分。把「收尾标记 + 句号」当作边界，无论后面跟什么。

> `validate_citations(markdown, snippet_ids)` returns a list of `CitationError(sentence, reason)` with reasons `uncited` or `dangling:S99`. An empty list means valid.
> One subtle split: `user-space kernel` starts lowercase, so "... workloads [S1]. user-space kernel is ..." must still split after `[S1].`. Treat a closing marker plus period as a boundary no matter what comes next.

## Gathering snippets per facet · 为每个 facet 收集片段

```python
top_docs = [doc_id for doc_id, _ in index.search(plan.question, k=k_docs)]
for facet in plan.facets:
    candidates = extract_snippets(plan.question + " " + facet.query(), index,
                                  per_doc=per_doc, doc_ids=top_docs)
    # skip spans already used, stop below relative_floor * best score,
    # keep per_facet, renumber S1, S2, ... across the whole report
```

对整个问题只做一次搜索，能让每个小节都切题。facet 只改变在这些文档里哪些句子胜出。跨 facet 重新编号意味着 `S3` 在整份报告里只有一个含义。

```figure
pj-rra-cited-writer
```

> Searching the whole question once keeps every section on topic. The facet only changes which sentences win inside those documents. Renumbering across facets means `S3` means one thing in the whole report.

## Follow the mechanism · 理解机制

片段注册表是一张主键表。写作器把 id 当外键使用，校验器检查引用完整性。在跨 facet 分配 id 之前，先按 `(doc_id, start, end)` 去重，因为分别编号的重复项看起来像独立证据，而实际不是。

> The snippet registry is a primary-key table. The writer uses ids as foreign keys, and the validator checks referential integrity. Deduplicate by `(doc_id, start, end)` before assigning ids across facets, because separately numbered duplicates look like independent evidence when they are not.

## Your task · 你的任务

```python
# citations.py
def cites_of(sentence) -> list[str]: ...
def strip_cites(sentence) -> str: ...
def report_sentences(markdown) -> list[str]: ...
def validate_citations(markdown, snippet_ids) -> list[CitationError]: ...

# writer.py
class CitedSentence:
    def render(self) -> str: ...
def gather_snippets(plan, index, k_docs=4, per_doc=4, per_facet=3, relative_floor=0.4) -> dict: ...
def write_report(plan, snippets_by_facet, max_sentences=3) -> Report: ...
def to_markdown(report) -> str: ...
```

## Run the tests · 运行测试

```bash
python3 scripts/project_test.py research-report-agent --stage 4 --path my-report-agent
```

有一个测试检查写作器什么都没编造：每个句子必须等于其片段文本（空白折叠后）。

> One test checks that the writer invents nothing: every sentence must equal its snippet text with whitespace collapsed.

## What you should see · 预期结果

第 4 阶段通过 12 个 Python 测试，且此前所有阶段仍然通过。一份干净的抽取式报告没有任何引用错误。没有标记的句子得到 `uncited`；`[S99]` 得到 `dangling:S99`。空白规范化之后，每个报告句子都等于它的来源片段。

> Stage 4 passes 12 Python tests, and all preceding stages still pass. A clean extractive report yields no citation errors. A sentence without a marker yields `uncited`; `[S99]` yields `dangling:S99`. Every report sentence equals its source snippet after whitespace normalization.

## Check yourself · 自检

1. 为什么校验器放在独立的模块里，而不是塞进写作器？
2. 与会改写的模型相比，抽取式写作器损失了什么？
3. 如何在保持契约的前提下让模型改写句子？

> 1. Why does the validator live in its own module instead of inside the writer?
> 2. What does an extractive writer lose compared with a model that paraphrases?
> 3. How would you let a model rewrite sentences while keeping the contract?

## Going further · 进阶

- 增加一个模型驱动的写作器：它只拿到编号后的片段，并且必须以引用格式返回句子。对它的输出跑校验器，失败就重试一次。
- 把两个说了同一件事的片段合并成一个带两个标记的句子，`[S2][S5]`。

> - Add a model-backed writer that receives only the numbered snippets and must return sentences in the citation format. Run the validator on its output and retry once on failure.
> - Merge two snippets that say the same thing into one sentence with two markers, `[S2][S5]`.

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html)和[检索增强生成](../../../../../phases/11-llm-engineering/06-rag/docs/en.md)。先完成[阶段 3](../../03-plan-the-research/docs/en.md)。

报告中的句子必须携带存在于证据台账（evidence ledger）中的片段 id。写作器为每个 facet 选取证据；当只有 60 分钟的来源存在时，它不会编造一个新的 15 分钟政策。

```text
before corpus -> "tokens expire after 60 minutes" [S1]
after corpus -> "tokens expire after 15 minutes" [S1]
```

> A sentence in the report must carry snippet ids that exist in the evidence ledger. The writer selects evidence for each facet; it does not invent a new 15-minute policy when only the 60-minute source exists.

## Build and inspect · 构建并检查

用来源区间（span）跟踪引用 id，而不只是它们的显示编号。跨小节对重复句子去重，同时不丢证据。

在你的学习工作区（learner workspace）中实现该阶段。这些 CLI 辅助工具是给定的适配器，它们导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py research-report-agent --stage 4 --path learning-artifacts/research-report-agent
```

先预测上面的中间状态，再运行该阶段。全新的 stub 会失败；参考实现跑通并不代表你的学习工作区已经完成。

> Track citation ids with source spans, not just their display number. Deduplicate repeated sentences across sections without losing evidence.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 下一步探究

为什么同一个显示编号 S1 在两次独立运行中可以指向不同的证据？

> Why can the same display id S1 refer to different evidence in two separate runs?
