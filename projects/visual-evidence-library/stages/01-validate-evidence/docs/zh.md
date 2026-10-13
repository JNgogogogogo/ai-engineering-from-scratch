# Validate image paths and text rectangles · 校验图片路径与文本矩形

> 在为一条文本断言建立索引之前，先保住它的来源。

> Preserve where a text assertion came from before indexing it.

**Type:** Build  
**Language:** Python  
**Stage:** 1 of 4  
**Time:** About 2 hours

## What you are building · 你在构建什么

搜索结果的可信度不会超过它的证据记录（evidence record）。一个资产（asset）有 ID、本地路径、宽度、高度和区域（regions）。一个区域有自己的 ID、文本、矩形 [x,y,width,height] 和来源（origin）。清单（manifest）是一组由人提供的断言，或是在模型抽取之后经过人工复核的断言。

```figure
pj-visual-evidence-library-1
```

> A search result can only be as trustworthy as its evidence record. An asset has an ID, local path, width, height and regions. A region has its own ID, text, a rectangle [x,y,width,height] and an origin. The manifest is a set of assertions supplied by a person or reviewed after model extraction.

## Work through an example · 走一遍示例

对一张 600×320 的标牌，[45,130,510,45] 的终点是 x=555、y=175，所以它在图片内部。[590,130,30,45] 越过了右边缘，必须失败。负数宽度不是表达镜像框的方式。

在写代码之前，先为该示例写下要返回的字段，并写下一个应当失败的输入。把预期结果放在实现旁边，这样你就能区分「契约变了」和「出了 bug」。

> For a 600 by 320 sign, [45,130,510,45] ends at x=555 and y=175, so it is inside the image. [590,130,30,45] crosses the right edge and must fail. A negative width is not a way to express a mirrored box.
> Before coding, write down the returned fields for that example and one input that should fail. Keep the expected result beside your implementation so you can distinguish a contract change from a bug.

## Implement the contract · 实现契约

- `validate_manifest(manifest: dict, root: Path) -> list[dict]`

要求资产 ID 唯一，且每个资产内部的区域 ID 唯一。尺寸必须是 1 到 20000 之间的整数。矩形包含四个有限的非布尔（nonboolean）数值，宽和高为正，且没有任何一条边越出图片。解析 root 下的每一个路径，包括符号链接（symlink）。要求是一张受支持的、真实存在且不超过 5 MB 的图片。模型提议的区域必须先有 reviewed=True 才能被索引。

保持此前阶段正常工作。在你的学习者工作区里实现这些函数；在走示例的过程中，让参考解（reference solution）保持封闭。

> Require unique asset IDs and unique region IDs within each asset. Dimensions are integers from 1 to 20000. Rectangles contain four finite nonboolean numbers, with positive width and height and no edge outside the image. Resolve every path under root, including symlinks. Require a supported existing image no larger than 5 MB. Model-proposed regions require reviewed=True before indexing.
> Keep earlier stages working. Implement these functions in your learner workspace, leaving the reference solution closed while you work through the example.

## Hints and failure cases · 提示与失败情形

先解析 root 和候选路径，再做包含关系检查。用声明的边界去比较 x+w 和 y+h。即便 Python 把 bool 当作整数，也要显式拒绝 bool。把解析后的路径作为内部字段保留，不要放进可移植的报告数据里。

> Resolve the root and candidate path before checking containment. Compare x+w and y+h with the declared bounds. Explicitly reject bool even though Python treats it as an integer. Keep the resolved path as an internal field, not portable report data.

## Run your stage · 运行你的阶段

从仓库根目录初始化一次，然后运行累积测试（cumulative tests）：

```bash
python3 scripts/project_test.py visual-evidence-library --init my-visual-evidence-library
python3 scripts/project_test.py visual-evidence-library --stage 1 --path my-visual-evidence-library
```

起始代码（starter）会刻意抛出一个实现错误。之后的初始化会保留你的源码而不是替换它。要通过，每一条被选中的测试都必须真正运行；被跳过的测试不构成完成证据。

> The starter deliberately raises an implementation error. Later initialization preserves your source rather than replacing it. A passing result requires every selected test to run; a skipped test is not completion evidence.

## Check your reasoning · 检查你的推理

哪些检查确立了结构上的有效性？哪些论断仍然需要查看真实图片才能成立？为什么几何上合法并不能证明文本是正确的？

> Which checks establish structural validity, and which claims still require looking at the actual image? Why does valid geometry not prove the text is correct?

## Connect it to the finished artifact · 连接到最终成品

成品是一个可独立打开的 HTML 证据画廊（evidence gallery），带高亮矩形和可复用的 evidence.json。离线核心只对提供的 OCR 元数据建索引；它不读取像素，也不执行 OCR。附带的 SVG 标牌和元数据都是为本项目专门编写的。查询覆盖率（query coverage）是词法重叠（lexical overlap），而不是「图片确实说了某句话」的置信度。尺寸与提供的文本始终是人工断言。

完成项目后，用你自己的输入试一试：

```bash
cd my-visual-evidence-library
python3 main.py --manifest ./fixtures/manifest.json --query "return dry seeds" --out ./visual-output
```

为某一种图片格式添加一个尺寸读取器，把真实尺寸与声明的尺寸做对比。不要替换「提供的文本」这一来源标签（provenance label）。

> A standalone HTML evidence gallery with highlighted rectangles and evidence.json for reuse. The offline core indexes provided OCR metadata; it does not read pixels or perform OCR. The included SVG signs and metadata were authored for this project. Query coverage is lexical overlap, not confidence that the image says something. Dimensions and supplied text remain human assertions.
> Add a dimension reader for a single image format and compare actual dimensions with the declaration. Do not replace the supplied-text provenance label.

## Primary reference · 主要参考

[官方 API 文档](https://docs.python.org/3/library/xml.etree.elementtree.html)。实现、示例和 fixtures 均为原创。该参考解释了底层 API；项目特定的策略已在上方说明。

> [Official API documentation](https://docs.python.org/3/library/xml.etree.elementtree.html). The implementation, examples and fixtures are original. The reference explains the underlying API; the project-specific policies are stated above.
