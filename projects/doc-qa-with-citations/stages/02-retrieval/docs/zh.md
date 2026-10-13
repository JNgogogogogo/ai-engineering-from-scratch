# Rank chunks with an inspectable keyword score · 用可检查的关键词分数给 chunk 排序

第 2 阶段（共 4 阶段）。开始之前先阅读[项目前置要求](../../../README.md)；本阶段建立在此前各阶段契约之上。

> Stage 2 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

词频（term frequency）经过对数达到饱和，文档频率（document frequency）则压低常见词的权重。返回带分数的完整 chunk 契约，而不只是文本，因为下一个阶段需要源 offset。这个词法基线抓不到同义词；在引入 embedding 服务之前，先量化它的短板。

> Term frequency saturates through a logarithm, and document frequency reduces the weight of common words. Return the whole chunk contract with its score, not just the text, because the next stage needs source offsets. This lexical baseline will miss synonyms; measure it before adding an embedding service.

## Work through one concrete case · 过一个具体例子

查询 cache 时，cache policy 文档应排在 request deadline 文档之前。重复出现 cache 会让词频按对数增长；出现在很多 chunk 里的词，贡献小于稀有词。

```figure
pj-doc-qa-with-citations-2
```

改一改 lab 输入，先自己算出结果再去看图中的指标。图形会根据这些输入实时计算；下方的实现测试仍是完成判定的依据。

> A query cache should rank the cache policy above the request deadline document. Repeating cache raises term frequency logarithmically; a term seen in many chunks contributes less than a rare term.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

实现 `retrieval.py`：`retrieve`。本产物是 Document QA With Citations and LangChain 的第 2 阶段。它消费显式输入，返回下一个阶段可以直接使用的、可检查的结果。

使用[公开 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示留给配套的 driver。

两侧用一致的方式 tokenize 和 case-fold。只有正分数进入结果；未知查询必须返回空候选列表，好让第 3 阶段能够弃答（abstain）。

> Implement `retrieval.py`: `retrieve`. This artifact is stage 2 of Document QA With Citations and LangChain. It consumes explicit inputs and returns an inspectable result that the next stage can use.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Tokenize and case-fold both sides consistently. Only positive scores enter the result; an unknown query must return an empty candidate list so stage 3 can abstain.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py doc-qa-with-citations --init learning-artifacts/doc-qa-with-citations` 做一次初始化。然后按阶段累计评分：

```bash
python3 scripts/project_test.py doc-qa-with-citations --stage 2 --path learning-artifacts/doc-qa-with-citations --strict
```

全新的工作区在你实现契约之前应当失败。每个阶段完成后，用配套样例运行你真实的产物：

```bash
cd learning-artifacts/doc-qa-with-citations
python3 cli.py samples/docs "When does cache expire?" --output answer.json --html answer.html
```

> From the repository root, initialize once with `python3 scripts/project_test.py doc-qa-with-citations --init learning-artifacts/doc-qa-with-citations`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

加一篇重复堆砌无关词的文档。确认仅凭长度并不会让它变得相关。

> Add a document containing many repetitions of an irrelevant word. Confirm that its length alone does not make it relevant.

## References · 参考资料

[参考资料 1](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter)
