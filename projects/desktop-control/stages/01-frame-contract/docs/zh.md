# Validate frames and coordinate spaces · 校验 frame 与坐标空间

第 1 阶段（共 4 阶段）。开始之前先阅读[项目前置要求](../../../README.md)；本阶段建立在此前各阶段契约之上。

> Stage 1 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

截图（screenshot）有物理像素尺寸，而原生桌面点击使用的可能是逻辑坐标（logical coordinates）。先校验「尺寸为正且有界」「display scale 有限」，再用向下取整除法（floor division）转换，并拒绝落在 frame 之外的点。frame 的 generation（代数）标识了是哪一次观察（observation）支撑了某个动作。

> A screenshot has physical pixel dimensions while native desktop clicks may use logical coordinates. Validate positive bounded dimensions and a finite display scale, then reject points outside the frame before converting by floor division. The frame generation identifies which observation justified an action.

## Work through one concrete case · 过一个具体例子

一张截图是 640x400 物理像素，scale 为 2。Pixel(200,100) 映射到 logical(100,50)。Pixel(640,100) 已经在图像之外，绝不能让它通过除法变成一个看似合理的逻辑坐标。

```figure
pj-desktop-control-1
```

改一改 lab 输入，先自己算出结果再去看图中的指标。图形会根据这些输入实时计算；下方的实现测试仍是完成判定的依据。

> A screenshot is640x400 physical pixels at scale 2. Pixel(200,100) maps to logical(100,50). Pixel(640,100) is already outside the image and must not become a plausible logical coordinate through division.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的工作区 `main.rs` 中实现 `Frame.validate, Frame.logical_point`。保持前几个阶段的实现持续可用。先读函数签名和测试，再一次实现一个边界。fixture 是一个确定性的测试 backend，它的结果不能代表真实的操作系统行为。

使用[公开 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示留给配套的 driver。

先在物理坐标空间里校验边界；然后把每个坐标除以 scale 并向下取整。把浮点数转成无符号整数之前，先检查其有限性（finiteness）。

> Implement `Frame.validate, Frame.logical_point` in your workspace `main.rs`. Keep earlier stages working. Read the function signatures and tests first, then implement one boundary at a time. The fixture is a deterministic test backend, and its results do not establish native operating-system behavior.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Validate bounds in physical space first; then floor each coordinate divided by scale. Check finiteness before converting floats to unsigned integers.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py desktop-control --init learning-artifacts/desktop-control` 做一次初始化。然后按阶段累计评分：

```bash
python3 scripts/project_test.py desktop-control --stage 1 --path learning-artifacts/desktop-control --strict
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

试试 NaN、负坐标和 scale 0。每一个错误都必须发生在 Backend.click 被调用之前。

> Try NaN, negative coordinates and scale 0. Each error must occur before Backend.click is called.

## References · 参考资料

[Rust 进程命令](https://doc.rust-lang.org/std/process/struct.Command.html)
[AppleScript 语言指南](https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide/)
[PNG 规范](https://www.w3.org/TR/png-3/)
