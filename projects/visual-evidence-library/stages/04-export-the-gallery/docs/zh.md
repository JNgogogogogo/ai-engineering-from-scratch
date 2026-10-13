# Export evidence you can point to · 导出你能指给人看的证据

> 渲染一个可移植（portable）的画廊，带精确的区域叠加层（overlay）和 JSON 结果。

> Render a portable gallery with exact region overlays and JSON results.

**Type:** Build  
**Language:** Python  
**Stage:** 4 of 4  
**Time:** About 2 hours

## What you are building · 你在构建什么

最终报告应该让人一眼就能检查一个结果。把图片内嵌进来，并在它上面画一个矩形。把像素坐标换算成百分比，这样当页面比源图窄时，叠加层依然保持对齐。在 JSON 里保留原始像素框，供下游工具使用。

```figure
pj-visual-evidence-library-4
```

> The final report should make a result inspectable in one glance. Embed the image and draw a rectangle above it. Convert pixel coordinates to percentages so the overlay remains aligned when the page is narrower than the source image. Keep the original pixel box in JSON for downstream tools.

## Work through an example · 走一遍示例

种子标牌宽 600 像素。起点为 x=45 的框，位于展示图片宽度的 7.5% 处；宽度 510 变成 85%。调整浏览器大小改变的是展示像素，而图片区域保持不变。

在写代码之前，先为该示例写下要返回的字段，并写下一个应当失败的输入。把预期结果放在实现旁边，这样你就能区分「契约变了」和「出了 bug」。

> The seed sign is 600 pixels wide. A box beginning at x=45 starts at 7.5% of the displayed image width; a width of 510 becomes 85%. Resizing the browser changes the displayed pixels while preserving the same image region.
> Before coding, write down the returned fields for that example and one input that should fail. Keep the expected result beside your implementation so you can distinguish a contract change from a bug.

## Implement the contract · 实现契约

- `image_data(asset: dict) -> str`
- `export_library(assets, query: str, out: Path) -> dict`

写出 index.html 和 evidence.json。包含 query、method、matches 和可移植的资产元数据，排除解析出来的文件系统路径。对所有文本字段做转义。内嵌图片数据，让 HTML 可以单独携带。对 SVG，只允许一个小型的、有文档说明的形状/文本子集，并剥离不支持的属性；拒绝不支持的元素，例如脚本或 foreignObject。不要把抽取出的文本当作 HTML 渲染。

保持此前阶段正常工作。在你的学习者工作区里实现这些函数；在走示例的过程中，让参考解（reference solution）保持封闭。

> Write index.html and evidence.json. Include query, method, matches and portable asset metadata, excluding resolved filesystem paths. Escape all textual fields. Embed image data so the HTML can travel alone. For SVG, allow only a small documented shape/text subset and strip unsupported attributes; reject unsupported elements such as scripts or foreignObject. Do not render extracted text as HTML.
> Keep earlier stages working. Implement these functions in your learner workspace, leaving the reference solution closed while you work through the example.

## Hints and failure cases · 提示与失败情形

用一个定位容器（positioned wrapper）包住 width:100% 的图片，再放一个绝对定位的叠加层。分别比较 left=x/width 和 top=y/height。测试里应该解码内嵌的 SVG，并验证事件处理属性（event-handler attributes）不存在。

> Use a positioned wrapper around an image with width:100% and an absolutely positioned overlay. Compare left=x/width and top=y/height separately. A test should decode the embedded SVG and verify event-handler attributes are absent.

## Run your stage · 运行你的阶段

从仓库根目录初始化一次，然后运行累积测试（cumulative tests）：

```bash
python3 scripts/project_test.py visual-evidence-library --init my-visual-evidence-library
python3 scripts/project_test.py visual-evidence-library --stage 4 --path my-visual-evidence-library
```

起始代码（starter）会刻意抛出一个实现错误。之后的初始化会保留你的源码而不是替换它。要通过，每一条被选中的测试都必须真正运行；被跳过的测试不构成完成证据。

> The starter deliberately raises an implementation error. Later initialization preserves your source rather than replacing it. A passing result requires every selected test to run; a skipped test is not completion evidence.

## Check your reasoning · 检查你的推理

报告里哪些信息读者可以自行验证？哪些仍然依赖输入清单（manifest）？如果一个矩形用的是屏幕坐标而不是源图坐标，会坏掉什么？

> Which information can a reader verify in the report, and which still depends on the input manifest? What breaks if a rectangle uses screen coordinates rather than source-image coordinates?

## Connect it to the finished artifact · 连接到最终成品

成品是一个可独立打开的 HTML 证据画廊（evidence gallery），带高亮矩形和可复用的 evidence.json。离线核心只对提供的 OCR 元数据建索引；它不读取像素，也不执行 OCR。附带的 SVG 标牌和元数据都是为本项目专门编写的。查询覆盖率（query coverage）是词法重叠（lexical overlap），而不是「图片确实说了某句话」的置信度。尺寸与提供的文本始终是人工断言。

完成项目后，用你自己的输入试一试：

```bash
cd my-visual-evidence-library
python3 main.py --manifest ./fixtures/manifest.json --query "return dry seeds" --out ./visual-output
```

添加一个在本地读取内嵌索引的查询表单。把模型抽取留在查看器之外，这样打开一份已保存的报告绝不会发起上传。

> A standalone HTML evidence gallery with highlighted rectangles and evidence.json for reuse. The offline core indexes provided OCR metadata; it does not read pixels or perform OCR. The included SVG signs and metadata were authored for this project. Query coverage is lexical overlap, not confidence that the image says something. Dimensions and supplied text remain human assertions.
> Add a query form that reads an embedded index locally. Keep model extraction outside the viewer so opening a saved report never initiates an upload.

## Primary reference · 主要参考

[官方 API 文档](https://docs.python.org/3/library/xml.etree.elementtree.html)。实现、示例和 fixtures 均为原创。该参考解释了底层 API；项目特定的策略已在上方说明。

> [Official API documentation](https://docs.python.org/3/library/xml.etree.elementtree.html). The implementation, examples and fixtures are original. The reference explains the underlying API; the project-specific policies are stated above.
