# Keep extraction proposals separate from labels · 把模型抽取的提议与分类标签分开

> 调用可选的视觉端点（vision endpoint），并在建立索引之前强制人工复核。

> Call an optional vision endpoint and require review before indexing.

**Type:** Build  
**Language:** Python  
**Stage:** 3 of 4  
**Time:** About 2 hours

## What you are building · 你在构建什么

模型可以提议可见文本，也可以把一张图片分类为标牌或图表。这是两种不同的输出。分类标签（classification label）没有文本矩形，绝不能变成 OCR 证据。先校验传输和模式（schema），然后要求一个人对照图片逐条检查每个被提议的文本片段（text span）。

```figure
pj-visual-evidence-library-3
```

> A model can propose visible text and can also classify an image as a sign or diagram. These are different outputs. A classification label has no text rectangle and must never become OCR evidence. Validate the transport and schema first, then require a person to inspect each proposed text span against the image.

## Work through an example · 走一遍示例

当提供方返回 regions=[{text: Return tools, bbox: [40,120,200,40]}] 和 labels=[notice] 时，你会得到一个 reviewed=False 的模型提议区域。标签 notice 留在 classification_labels 里。如果一个提议的框越出了图片，就拒绝这个提议，而不是裁剪它来制造合法的假象。

在写代码之前，先为该示例写下要返回的字段，并写下一个应当失败的输入。把预期结果放在实现旁边，这样你就能区分「契约变了」和「出了 bug」。

> A provider returning regions=[{text: Return tools, bbox: [40,120,200,40]}] and labels=[notice] yields one model-proposed region with reviewed=False. The label notice stays in classification_labels. If a proposed box extends beyond the image, reject the proposal rather than clipping it into apparent validity.
> Before coding, write down the returned fields for that example and one input that should fail. Keep the expected result beside your implementation so you can distinguish a contract change from a bug.

## Implement the contract · 实现契约

- `validate_proposal(proposal: dict, width: int, height: int) -> dict`
- `request_vision(path, endpoint, model, width, height, api_key="") -> dict`

返回 regions、classification_labels、status=review-required 和一条清晰的警告。区域 ID 按确定性方式分配。拒绝畸形、为空或越界的区域，以及非字符串的标签。HTTP 适配器把真实的图片字节放进 data URL，发送到配置好的 chat-completions 端点，带超时和响应大小检查。只支持签名匹配的 PNG/JPEG 上传；SVG fixtures 保持离线。

保持此前阶段正常工作。在你的学习者工作区里实现这些函数；在走示例的过程中，让参考解（reference solution）保持封闭。

> Return regions, classification_labels, status=review-required and a clear warning. Region IDs are assigned deterministically. Reject malformed, empty or out-of-bounds regions and nonstring labels. The HTTP adapter sends actual image bytes in a data URL to the configured chat-completions endpoint, with a timeout and response-size check. Support only PNG/JPEG uploads with matching signatures; SVG fixtures remain offline.
> Keep earlier stages working. Implement these functions in your learner workspace, leaving the reference solution closed while you work through the example.

## Hints and failure cases · 提示与失败情形

把提供方 URL 做成显式配置。在测试里检查 JSON 请求，并返回一个带 choices[0].message.content 的受控信封（envelope）。mock 或本地线路测试通过，证明的是序列化和校验，不是真实模型读文本读得准。

> Make the provider URL explicit. In tests, inspect the JSON request and return a controlled envelope with choices[0].message.content. A passing mock or local-wire test proves serialization and validation, not that a real model reads text accurately.

## Run your stage · 运行你的阶段

从仓库根目录初始化一次，然后运行累积测试（cumulative tests）：

```bash
python3 scripts/project_test.py visual-evidence-library --init my-visual-evidence-library
python3 scripts/project_test.py visual-evidence-library --stage 3 --path my-visual-evidence-library
```

起始代码（starter）会刻意抛出一个实现错误。之后的初始化会保留你的源码而不是替换它。要通过，每一条被选中的测试都必须真正运行；被跳过的测试不构成完成证据。

> The starter deliberately raises an implementation error. Later initialization preserves your source rather than replacing it. A passing result requires every selected test to run; a skipped test is not completion evidence.

## Check your reasoning · 检查你的推理

收到合法 JSON 之后，还有什么没有被验证？为什么把 reviewed=True 设为代表人工断言，而不是代表某个模型置信度阈值？

> What remains unverified after valid JSON is received? Why does setting reviewed=True represent a human assertion rather than a model confidence threshold?

## Connect it to the finished artifact · 连接到最终成品

成品是一个可独立打开的 HTML 证据画廊（evidence gallery），带高亮矩形和可复用的 evidence.json。离线核心只对提供的 OCR 元数据建索引；它不读取像素，也不执行 OCR。附带的 SVG 标牌和元数据都是为本项目专门编写的。查询覆盖率（query coverage）是词法重叠（lexical overlap），而不是「图片确实说了某句话」的置信度。尺寸与提供的文本始终是人工断言。

完成项目后，用你自己的输入试一试：

```bash
cd my-visual-evidence-library
python3 main.py --manifest ./fixtures/manifest.json --query "return dry seeds" --out ./visual-output
```

把复核人姓名和复核时间存进一份单独的本地复核日志。在一个留出（held-out）的人工标注集合上评估字符错误和矩形重叠。

> A standalone HTML evidence gallery with highlighted rectangles and evidence.json for reuse. The offline core indexes provided OCR metadata; it does not read pixels or perform OCR. The included SVG signs and metadata were authored for this project. Query coverage is lexical overlap, not confidence that the image says something. Dimensions and supplied text remain human assertions.
> Store reviewer name and review time in a separate local review log. Evaluate character errors and rectangle overlap against a held-out human-labeled set.

## Primary reference · 主要参考

[官方 API 文档](https://docs.python.org/3/library/xml.etree.elementtree.html)。实现、示例和 fixtures 均为原创。该参考解释了底层 API；项目特定的策略已在上方说明。

> [Official API documentation](https://docs.python.org/3/library/xml.etree.elementtree.html). The implementation, examples and fixtures are original. The reference explains the underlying API; the project-specific policies are stated above.
