# Rank matches and preserve the rectangle · 为匹配结果排序并保留矩形

> 用透明的词法查询覆盖率（lexical query coverage）搜索区域文本。

> Search region text with transparent lexical query coverage.

**Type:** Build  
**Language:** Python  
**Stage:** 2 of 4  
**Time:** About 2 hours

## What you are building · 你在构建什么

对每个区域的文本分别建立索引。一个查询可以匹配多张图片，也可以匹配同一张图片里的多个区域。保留区域身份（region identity）能防止「标题命中」被误看成来自它下面那段话。分数统计的是这一个区域里出现的去重查询词（unique query tokens）。

```figure
pj-visual-evidence-library-2
```

> Index the text of each region separately. A query can match several images or several regions inside one image. Keeping region identity prevents a title match from appearing as though it came from the paragraph below it. The score counts unique query tokens found in that one region.

## Work through an example · 走一遍示例

查询 return dry seeds 有三个去重词元（token）。写着 Return dry seeds in paper envelopes 的区域命中全部三个，得 1 分。另一块写着 Return tools to the blue shelf 的标牌只命中 return，得 1/3 分。seed 这个词不会自动匹配 seeds；这是一个清晰可见的词法基线（lexical baseline）。

在写代码之前，先为该示例写下要返回的字段，并写下一个应当失败的输入。把预期结果放在实现旁边，这样你就能区分「契约变了」和「出了 bug」。

> The query return dry seeds has three unique tokens. A region saying Return dry seeds in paper envelopes matches all three and scores 1. A different sign saying Return tools to the blue shelf matches only return and scores 1/3. The word seed does not automatically match seeds; this is a visible lexical baseline.
> Before coding, write down the returned fields for that example and one input that should fail. Keep the expected result beside your implementation so you can distinguish a contract change from a bug.

## Implement the contract · 实现契约

- `terms(text: str) -> set[str]`
- `search(assets, query: str, limit: int = 20) -> list[dict]`

对 Unicode 文本做大小写折叠（case-fold），并按词字符（word characters）切分。空查询返回零个匹配。limit 必须是 1 到 100 之间的整数。返回 asset_id、region_id、原始文本、bbox、matched_terms、score 和 origin。按分数降序排序，再按资产 ID 和区域 ID 排序。查询里重复出现的词不增大分母。

保持此前阶段正常工作。在你的学习者工作区里实现这些函数；在走示例的过程中，让参考解（reference solution）保持封闭。

> Case-fold Unicode text and tokenize word characters. Empty queries return no matches. Limit must be an integer from 1 to 100. Return asset_id, region_id, original text, bbox, matched_terms, score and origin. Sort by descending score, then asset ID and region ID. Repeated query words do not increase the denominator.
> Keep earlier stages working. Implement these functions in your learner workspace, leaving the reference solution closed while you work through the example.

## Hints and failure cases · 提示与失败情形

用集合（set）做覆盖率，但保留原始文本用于展示。测一个带变音符的词和一个分数并列的情况。分数在 JSON 里保持为数字，只在视图层格式化成百分比。

> Use sets for coverage but preserve the original text for display. Test an accented word and a score tie. Keep scores as numbers in JSON, formatting percentages only in the view.

## Run your stage · 运行你的阶段

从仓库根目录初始化一次，然后运行累积测试（cumulative tests）：

```bash
python3 scripts/project_test.py visual-evidence-library --init my-visual-evidence-library
python3 scripts/project_test.py visual-evidence-library --stage 2 --path my-visual-evidence-library
```

起始代码（starter）会刻意抛出一个实现错误。之后的初始化会保留你的源码而不是替换它。要通过，每一条被选中的测试都必须真正运行；被跳过的测试不构成完成证据。

> The starter deliberately raises an implementation error. Later initialization preserves your source rather than replacing it. A passing result requires every selected test to run; a skipped test is not completion evidence.

## Check your reasoning · 检查你的推理

为什么 100% 的查询分数不能作为「该区域包含答案」的证据？如果引入短语匹配（phrase matching），这份契约会如何改变？

> Why is a 100% query score not evidence that a region contains the answer to a question? How would phrase matching change the contract?

## Connect it to the finished artifact · 连接到最终成品

成品是一个可独立打开的 HTML 证据画廊（evidence gallery），带高亮矩形和可复用的 evidence.json。离线核心只对提供的 OCR 元数据建索引；它不读取像素，也不执行 OCR。附带的 SVG 标牌和元数据都是为本项目专门编写的。查询覆盖率（query coverage）是词法重叠（lexical overlap），而不是「图片确实说了某句话」的置信度。尺寸与提供的文本始终是人工断言。

完成项目后，用你自己的输入试一试：

```bash
cd my-visual-evidence-library
python3 main.py --manifest ./fixtures/manifest.json --query "return dry seeds" --out ./visual-output
```

添加一个独立可选的同义词表，并在人工标注的查询上测量精确率（precision）。展示展开后的词元，让用户能解释意料之外的匹配。

> A standalone HTML evidence gallery with highlighted rectangles and evidence.json for reuse. The offline core indexes provided OCR metadata; it does not read pixels or perform OCR. The included SVG signs and metadata were authored for this project. Query coverage is lexical overlap, not confidence that the image says something. Dimensions and supplied text remain human assertions.
> Add a separate optional synonym table and measure precision on manually labeled queries. Show expanded terms so a user can explain unexpected matches.

## Primary reference · 主要参考

[官方 API 文档](https://docs.python.org/3/library/xml.etree.elementtree.html)。实现、示例和 fixtures 均为原创。该参考解释了底层 API；项目特定的策略已在上方说明。

> [Official API documentation](https://docs.python.org/3/library/xml.etree.elementtree.html). The implementation, examples and fixtures are original. The reference explains the underlying API; the project-specific policies are stated above.
