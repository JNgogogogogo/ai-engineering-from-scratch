# Use a framework splitter without losing offsets · 使用框架 splitter 而不丢失偏移量

第 4 阶段（共 4 阶段）。开始之前先阅读[项目前置要求](../../../README.md)；本阶段建立在此前各阶段契约之上。

> Stage 4 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

adapter 保留从零实现的检索和答案校验器。可选的 LangChain 路径贡献递归切分（recursive splitting）和一个假模型接口，然后把每个 chunk 转回精确的源 offset。如果 splitter 改写了文本，就拒绝它，而不是编造溯源（provenance）。对重复出现的重叠子串，搜索游标必须每次只前进一个位置，而不是一整个 chunk 长度。

> The adapter keeps the from-scratch retrieval and answer validator. The optional LangChain path contributes recursive splitting and a fake model interface, then converts every chunk back to exact source offsets. If a splitter rewrites text, reject it instead of inventing provenance. Repeated overlapping substrings must advance the search cursor by one position, not by the full chunk length.

## Work through one concrete case · 过一个具体例子

框架 splitter 对 "ababa" 返回两个重叠的 "aba"。它们的位置是 0 和 2；如果搜索游标一次前进一整个 chunk 长度，就会漏掉第二个合法出现。

```figure
pj-doc-qa-with-citations-4
```

改一改 lab 输入，先自己算出结果再去看图中的指标。图形会根据这些输入实时计算；下方的实现测试仍是完成判定的依据。

> A framework splitter returns two overlapping copies of "aba" from "ababa". Their positions are 0 and 2; advancing the search cursor by the full chunk length would miss the second valid occurrence.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

实现 `adapter.py`：`adapt_splits`、`framework_qa`。本产物是 Document QA With Citations and LangChain 的第 4 阶段。它消费显式输入，返回下一个阶段可以直接使用的、可检查的结果。

使用[公开 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示留给配套的 driver。

把游标移到上一个匹配之后一个字符的位置，并用原文验证每个返回的分片。把从零实现的检索和引用校验器继续包在可选 SDK 路径外面。

> Implement `adapter.py`: `adapt_splits`, `framework_qa`. This artifact is stage 4 of Document QA With Citations and LangChain. It consumes explicit inputs and returns an inspectable result that the next stage can use.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Move the cursor one character past the last match and verify every returned part against the original text. Keep the from-scratch retrieval and citation validator around the optional SDK path.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py doc-qa-with-citations --init learning-artifacts/doc-qa-with-citations` 做一次初始化。然后按阶段累计评分：

```bash
python3 scripts/project_test.py doc-qa-with-citations --stage 4 --path learning-artifacts/doc-qa-with-citations --strict
```

全新的工作区在你实现契约之前应当失败。每个阶段完成后，用配套样例运行你真实的产物：

```bash
cd learning-artifacts/doc-qa-with-citations
python3 cli.py samples/docs "When does cache expire?" --output answer.json --html answer.html
```

> From the repository root, initialize once with `python3 scripts/project_test.py doc-qa-with-citations --init learning-artifacts/doc-qa-with-citations`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

用你自己的两个文本文件跑 folder CLI。然后安装锁定版本的可选依赖，比较 chunk offset，而不只是 chunk 的数量。

默认的回答器是本地的、抽取式的。词面重叠建立不起语义蕴含（entailment）。一条有效的引用仍可能不相关或过时；内容哈希让读者能发现来源变更。

> Run the folder CLI with your own two text files. Then install the pinned optional dependencies and compare chunk offsets, not merely the number of chunks.
> The default answerer is local and extractive. Lexical overlap cannot establish semantic entailment. A valid citation can still be irrelevant or outdated; the content hash lets a reader detect source changes.

## Verify the actual framework · 验证真实框架

五个默认阶段测试不 import SDK 就能检查 adapter 契约。安装锁定版本的可选依赖，然后显式纳入五个真实 SDK 测试：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r projects/doc-qa-with-citations/requirements-framework.txt
.venv/bin/python scripts/project_test.py doc-qa-with-citations --solution --optional --strict
.venv/bin/python projects/doc-qa-with-citations/solution/framework_demo.py
```

用 `--path my-doc-qa-with-citations` 代替 `--solution` 来评你的实现。缺依赖时，optional 模式下是 skip，strict optional 模式下是失败。已验证的 SDK 版本是 `langchain-text-splitters==1.1.2`；所有模型回复都是本地 fixture。

> The five default stage tests check the adapter contract without importing the SDK. Install the pinned optional dependency, then include the five real-SDK tests explicitly:
> Use `--path my-doc-qa-with-citations` instead of `--solution` to grade your implementation. Missing dependencies produce a skip in optional mode and a failure in strict optional mode. The verified SDK version is `langchain-text-splitters==1.1.2`; all model replies are local fixtures.

## References · 参考资料

[参考资料 1](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter)
