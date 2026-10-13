# Verify screenshot pixels in Python · 用 Python 校验截图像素

Stage 3 of 4. 第 3 阶段（共 4 阶段）。开始前先读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 3 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

读取 PNG 签名、chunk 长度和 CRC，然后解压有大小上限的图像数据。逆变换 PNG 行滤波（row filter），统计绿色成功像素的数量。把这个视觉信号与 DOM 标志结合起来；单独任何一个都不足够。这是一个针对本 fixture 的窄域像素状态检测器，不是 OCR，也不是通用视觉。损坏、超大、隔行（interlaced）和不支持的色彩格式都会显式失败。

本阶段的边界是 `inspectPNG`。保持前面阶段的行为不变：最终评分器会用同一个 workspace 跑所有阶段。

> Read the PNG signature, chunk lengths and CRCs, then decompress a bounded image payload. Reverse PNG row filters and count green success pixels. Combine this visual signal with the DOM flag; neither alone is sufficient. This is a narrow pixel-state detector for the authored fixture, not OCR or general vision. Corrupt, oversized, interlaced and unsupported color formats fail explicitly.
> The boundary for this stage is `inspectPNG`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 过一遍具体案例

一张 4x4 的 RGB 截图包含 16 个像素。4 个绿色像素得到 0.25，0 个绿色像素得到 0.0。合法的 PNG 签名只是起点：改动 IHDR 的一个字节而不更新 CRC，必须失败。

```figure
pj-browser-agent-3
```

修改实验输入，先自己算出结果，再去看它的 metrics。figure 是根据这些输入计算的；下面的实现测试仍然是完成与否的判定依据。

> A4x4 RGB screenshot contains 16 pixels. Four green pixels produce 0.25, while zero green pixels produce 0.0. A valid PNG signature is only the beginning: changing an IHDR byte without changing CRC must fail.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的 workspace 的 `main.ts` 里实现 `inspectPNG`。先自己尝试实现契约，之后再去读参考实现导出的类型。保留 starter 的公开命名，测试才能调用你的实现。核心函数返回结构化值，不要在函数内部打印；最终结果由 CLI 打印。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只负责返回值，文件输入、参数解析和展示都交给随附的 driver。

对 filter 1：重建字节 = 存储字节 + 左侧重建字节，对 256 取模。对 filter 2：使用上一行。RGB 每像素 3 个字节，所以「左侧」是 index-3，不是 index-1。

> Implement `inspectPNG` in your workspace `main.ts`. Read the exported types in the reference only after attempting the contract. Preserve the starter's public names so tests can call your implementation. Return structured values instead of printing inside the core function; the CLI prints the final result.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> For filter 1, reconstructed byte = stored byte + reconstructed left byte modulo 256. For filter 2, use the previous row. RGB has three bytes per pixel, so left means index-3, not index-1.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py browser-agent --init learning-artifacts/browser-agent` 初始化一次。然后按阶段累积评分：

```bash
python3 scripts/project_test.py browser-agent --stage 3 --path learning-artifacts/browser-agent --strict
```

全新 workspace 在你实现契约之前应当失败。所有阶段都完成后，用随附样例运行你真正的产物：

```bash
cd learning-artifacts/browser-agent
node cli.ts --task samples/contact.json --output browser-run.json
```

> From the repository root, initialize once with `python3 scripts/project_test.py browser-agent --init learning-artifacts/browser-agent`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

构造一行，包含像素 (20,140,80) 和 (30,150,90)。对红色字节，filter 1 存储的是 20 然后 10；重建必须还原出 20 然后 30。一般化的颜色检测不在本 fixture 契约的范围内。

> Construct one row with pixels(20,140,80) and(30,150,90). For the red bytes, filter 1 stores 20 then 10; reconstruction must recover 20 then 30. General color detection remains outside this fixture contract.

## References · 参考资料

[Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
[PNG specification](https://www.w3.org/TR/png-3/)
[HTML form controls](https://html.spec.whatwg.org/multipage/forms.html)
