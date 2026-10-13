# Normalize notes without losing identity · 不丢失身份地规范化笔记

**第 1 阶段（共 4 阶段）。** Python。预计约 2 小时。

搜索索引（search index）是你今天写下的笔记与将来输入的查询之间的一份契约。对 Unicode 单词分词并做大小写折叠（case folding），但保留每个原始的文档 id。重复出现的词条携带词频信息；如果换成集合（set），这份信息就毁了。

用一张小而显式的同义词映射表（synonym map）把 deploy 和 release 映射到同一个规范词（canonical term）。这展示的是受控的语义扩展（controlled semantic expansion）。它不是嵌入模型（embedding model），推断不出任意的改述（paraphrase）。

```figure
pj-semantic-notes-search-1
```

主要参考资料：[Primary technical reference](https://nlp.stanford.edu/IR-book/html/htmledition/the-vector-space-model-for-scoring-1.html)。

> A search index is a contract between the note you wrote and the query you will type later. Tokenize Unicode words with case folding, but keep each original document id. Repeated terms carry frequency information; a set would destroy it.
> Use a small explicit synonym map to map deploy and release to the same canonical term. This demonstrates controlled semantic expansion. It is not an embedding model and cannot infer arbitrary paraphrases.
> Primary reference: [Primary technical reference](https://nlp.stanford.edu/IR-book/html/htmledition/the-vector-space-model-for-scoring-1.html).

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) 和 [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md)。

Orchard 的操作员会用不同的 Unicode 编码输入 café。对文本和别名键（alias key）同时应用大小写折叠与 NFC 规范化（NFC normalization），让等价的写法共享同一批词条。一个别名就是一次显式的词汇替换。

```text
"CAFE\u0301" -> ["café"]
alias release -> deploy
"release café" -> ["deploy","café"]
```

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Data management](../../../../../phases/00-setup-and-tooling/09-data-management/docs/en.md).
> Orchard operators type café with different Unicode encodings. Apply case folding and NFC normalization to both text and alias keys so equivalent spellings share tokens. An alias is one explicit lexical substitution.

## Build and inspect · 构建与检查

要在 Unicode 单词正则（regex）之前做规范化；否则组合附加符（combining mark）可能消失。不要把别名递归展开成环。

请在你的学习者工作区（learner workspace）里实现本阶段。CLI 辅助工具只是随附的适配器（adapter），它们导入你的函数；不能替代参考解答。

```bash
python3 scripts/project_test.py semantic-notes-search --init learning-artifacts/semantic-notes-search
python3 scripts/project_test.py semantic-notes-search --stage 1 --path learning-artifacts/semantic-notes-search
```

先预测上面的中间状态，再运行本阶段。全新的桩代码（stub）会失败；参考解答能跑通，并不代表你的学习者工作区已经完成。

> Normalize before the Unicode word regex; otherwise a combining mark can disappear. Do not recursively expand aliases into cycles.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage. A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接着探究

把 release 映射到 deploy，什么时候会损害检索而不是帮到检索？

> When would mapping release to deploy harm retrieval rather than help it?
