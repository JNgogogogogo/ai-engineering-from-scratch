# Render and manipulate a fixture scene · 渲染并操作 fixture 场景

第 2 阶段（共 4 阶段）。开始之前先阅读[项目前置要求](../../../README.md)；本阶段建立在此前各阶段契约之上。

> Stage 2 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

把 capture、click、type_text 三种操作都定义在同一个 Backend trait 之后。fixture 会根据自己的状态画出一幅真实的 PPM 图像：一个文本输入区、一个提交（submit）区域，以及一个「已完成」的绿色场景。点击输入区会改变焦点（focus），打字要求先有焦点，而点击 submit 只有在文本存在之后才会完成场景。这个 fixture 让状态迁移类 bug 在不操控用户真实桌面的情况下也能复现。

> Define capture, click and type_text behind one Backend trait. The fixture draws a real PPM image from its state: a text field, a submit region and a green completed scene. Clicking the field changes focus, typing requires focus, and clicking submit completes only after text exists. The fixture makes transition bugs reproducible without controlling the user desktop.

## Work through one concrete case · 过一个具体例子

fixture 初始处于未聚焦状态。点击(50,70) 让输入框获得焦点，输入 Mira 会保存文本，再点击(230,160) 场景即告完成。前后两次 capture 包含的是不同的真实 RGB 字节。

```figure
pj-desktop-control-2
```

改一改 lab 输入，先自己算出结果再去看图中的指标。图形会根据这些输入实时计算；下方的实现测试仍是完成判定的依据。

> The fixture starts unfocused. Clicking(50,70) focuses the input, typing Mira stores text, and clicking(230,160) completes the scene. Captures before and after contain different real RGB bytes.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的工作区 `main.rs` 中实现 `Backend, FixtureBackend`。保持前几个阶段的实现持续可用。先读函数签名和测试，再一次实现一个边界。fixture 是一个确定性的测试 backend，它的结果不能代表真实的操作系统行为。

使用[公开 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示留给配套的 driver。

PPM P6 以 ASCII 头 `P6`、宽/高和 255 开头，其后是 width*height*3 个字节。按行优先（row-major）遍历像素，从 backend 状态推导每个像素的颜色。

> Implement `Backend, FixtureBackend` in your workspace `main.rs`. Keep earlier stages working. Read the function signatures and tests first, then implement one boundary at a time. The fixture is a deterministic test backend, and its results do not establish native operating-system behavior.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> PPM P6 begins with ASCII header P6, width/height and 255, followed by width*height*3 bytes. Walk row-major pixels and derive each color from backend state.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py desktop-control --init learning-artifacts/desktop-control` 做一次初始化。然后按阶段累计评分：

```bash
python3 scripts/project_test.py desktop-control --stage 2 --path learning-artifacts/desktop-control --strict
```

全新的工作区在你实现契约之前应当失败。每个阶段完成后，用配套样例运行你真实的产物：

```bash
cd learning-artifacts/desktop-control
rustc --edition 2021 cli.rs -o desktop-cli
./desktop-cli samples/actions.tsv desktop-frames
```

> From the repository root, initialize once with `python3 scripts/project_test.py desktop-control --init learning-artifacts/desktop-control`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

先不打字就去点 submit，然后检查 complete=false。一个真实的 fixture 必须把失败迁移也建模出来，而不是任何点击之后一律涂绿。

> Submit before typing and inspect complete=false. A realistic fixture must model failure transitions, not just paint green after any click.

## References · 参考资料

[Rust 进程命令](https://doc.rust-lang.org/std/process/struct.Command.html)
[AppleScript 语言指南](https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide/)
[PNG 规范](https://www.w3.org/TR/png-3/)
