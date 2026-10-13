# Load local documents with stable provenance · 加载本地文档并保留稳定溯源

第 1 阶段（共 4 阶段）。开始之前先阅读[项目前置要求](../../../README.md)；本阶段建立在此前各阶段契约之上。

> Stage 1 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

在检索任何东西之前，先保留来源身份（source identity）、内容哈希和精确 offset。字符窗口（character window）是一个刻意简单的基线：重叠（overlap）保住了边界附近的上下文，但不会制造新证据。加载器拒绝逃出其根目录的 symlink，因此文档扫描不会悄悄读到另一个目录。

> Keep source identity, content hash and exact offsets before retrieving anything. Character windows are an intentionally simple baseline: overlap preserves context near boundaries but does not create new evidence. The loader refuses symlinks that escape its root, so a document scan cannot silently read another directory.

## Work through one concrete case · 过一个具体例子

对文本 abcdef，size 4、overlap 1 先产出 [0,4)="abcd"，再产出 [3,6)="def"。offset 以 Unicode 字符计，而不是 UTF-8 字节；文件的 SHA-256 标识确切的来源版本。

```figure
pj-doc-qa-with-citations-1
```

改一改 lab 输入，先自己算出结果再去看图中的指标。图形会根据这些输入实时计算；下方的实现测试仍是完成判定的依据。

> For text abcdef, size 4 and overlap 1 produce [0,4)="abcd" then [3,6)="def". The offset is in Unicode characters, not UTF-8 bytes, and the file's SHA-256 identifies the exact source version.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

实现 `documents.py`：`load_documents`、`chunk_document`。本产物是 Document QA With Citations and LangChain 的第 1 阶段。它消费显式输入，返回下一个阶段可以直接使用的、可检查的结果。

使用[公开 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示留给配套的 driver。

chunk 一旦到达源文本末尾就立即停止。否则一个很短的尾部 chunk 会再生成一个冗余窗口。对每个路径做解析（resolve），拒绝逃出根目录的 symlink。

> Implement `documents.py`: `load_documents`, `chunk_document`. This artifact is stage 1 of Document QA With Citations and LangChain. It consumes explicit inputs and returns an inspectable result that the next stage can use.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Stop immediately when a chunk reaches the source end. Otherwise a short trailing chunk can generate another redundant window. Resolve each path and reject symlinks escaping the root.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py doc-qa-with-citations --init learning-artifacts/doc-qa-with-citations` 做一次初始化。然后按阶段累计评分：

```bash
python3 scripts/project_test.py doc-qa-with-citations --stage 1 --path learning-artifacts/doc-qa-with-citations --strict
```

全新的工作区在你实现契约之前应当失败。每个阶段完成后，用配套样例运行你真实的产物：

```bash
cd learning-artifacts/doc-qa-with-citations
python3 cli.py samples/docs "When does cache expire?" --output answer.json --html answer.html
```

> From the repository root, initialize once with `python3 scripts/project_test.py doc-qa-with-citations --init learning-artifacts/doc-qa-with-citations`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

在引用片段之前放一个多字节字符。验证 Python 字符串切片、返回的 offset 和渲染器用的都是同一个单位。

> Place a multibyte character before a quoted span. Verify that Python string slicing, returned offsets and the renderer all use the same unit.

## References · 参考资料

[参考资料 1](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter)
