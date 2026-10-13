# Accept only answers grounded in retrieved spans · 只接受有检索片段支撑的答案

第 3 阶段（共 4 阶段）。开始之前先阅读[项目前置要求](../../../README.md)；本阶段建立在此前各阶段契约之上。

> Stage 3 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

让模型选出一条精确引用（exact quote）和一个 source id，然后对两者都做校验。被引用的子串给出一个可检查的 span；它并不保证来源内容为真。检索为空时，不调用模型、直接返回明确的弃答（abstention）。如果以后换成改写式（paraphrasing）的生成器，就需要另一道支撑闸门。

> Ask the model to select an exact quote and a source id, then validate both. A quoted substring gives a checkable span; it does not guarantee the source is true. Empty retrieval returns an explicit abstention without calling the model. A later paraphrasing writer would need a different support gate.

## Work through one concrete case · 过一个具体例子

源文本是 "Cache expires in sixty seconds. Bananas are yellow."，两句话都可被引用。对 cache 问题，香蕉那句能通过精确子串检查，但组装好的 CLI 会把它标为 `needs_review`，因为没有有意义的查询词重叠。

```figure
pj-doc-qa-with-citations-3
```

改一改 lab 输入，先自己算出结果再去看图中的指标。图形会根据这些输入实时计算；下方的实现测试仍是完成判定的依据。

> The source says "Cache expires in sixty seconds. Bananas are yellow." Both sentences are quotable. For a cache question, the banana sentence passes the exact-substring check but the composed CLI marks it needs_review because no meaningful query term overlaps.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

实现 `answer.py`：`answer`。本产物是 Document QA With Citations and LangChain 的第 3 阶段。它消费显式输入，返回下一个阶段可以直接使用的、可检查的结果。

使用[公开 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示留给配套的 driver。

先校验 source id 和精确引用，再从被引 chunk 中恢复 offset。把相关性留作一个独立的、显式受限的策略，而不是假装引用本身就证明了答案。

> Implement `answer.py`: `answer`. This artifact is stage 3 of Document QA With Citations and LangChain. It consumes explicit inputs and returns an inspectable result that the next stage can use.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> First validate source id and exact quote, then recover offsets from the cited chunk. Keep relevance as a separate, explicitly limited policy instead of pretending the citation proves the answer.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py doc-qa-with-citations --init learning-artifacts/doc-qa-with-citations` 做一次初始化。然后按阶段累计评分：

```bash
python3 scripts/project_test.py doc-qa-with-citations --stage 3 --path learning-artifacts/doc-qa-with-citations --strict
```

全新的工作区在你实现契约之前应当失败。每个阶段完成后，用配套样例运行你真实的产物：

```bash
cd learning-artifacts/doc-qa-with-citations
python3 cli.py samples/docs "When does cache expire?" --output answer.json --html answer.html
```

> From the repository root, initialize once with `python3 scripts/project_test.py doc-qa-with-citations --init learning-artifacts/doc-qa-with-citations`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

让返回的精确引用对应另一个 chunk id。答案闸门必须拒绝它，即使同样的文本在语料库的其他地方存在。

> Return an exact quote from a different chunk id. The answer gate must reject it even if the same text exists elsewhere in the corpus.

## References · 参考资料

[参考资料 1](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter)
