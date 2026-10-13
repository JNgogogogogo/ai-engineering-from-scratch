# Build an opt-in native boundary · 构建显式选择开启的原生边界

第 4 阶段（共 4 阶段）。开始之前先阅读[项目前置要求](../../../README.md)；本阶段建立在此前各阶段契约之上。

> Stage 4 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

不经 shell 地构造 macOS screencapture 和 AppleScript 的参数数组。把要输入的文本作为参数（argument）传递，绝不作为可执行的脚本内容。从原生截图的头部读 PNG 尺寸，并原样保留真实的图像负载。默认 demo 仍然是 fixture。原生 capture 需要显式的 --native-capture 标志、OS 权限，以及在显示器被缩放时由调用方提供的 DESKTOP_SCALE。原生点击和打字是库方法，不是自动执行的 demo 动作。

> Construct macOS screencapture and AppleScript argument arrays without a shell. Pass typed text as an argument, never as executable script content. Read PNG dimensions from native screenshot headers and preserve the actual image payload. ... Native capture requires an explicit --native-capture flag, OS permissions and a caller-supplied DESKTOP_SCALE when the display is scaled. Native click and typing are library methods, not automatic demo actions.

## Work through one concrete case · 过一个具体例子

文本负载 `Mira "quoted"` 应该放进 osascript 的一个 argv 元素里，绝不能拼进 AppleScript 程序字符串。这样参数边界就不依赖引号写法而保持完好。

```figure
pj-desktop-control-4
```

改一改 lab 输入，先自己算出结果再去看图中的指标。图形会根据这些输入实时计算；下方的实现测试仍是完成判定的依据。

> The text payload `Mira "quoted"` belongs in an osascript argv element. It must never be pasted into the AppleScript program string. This preserves argument boundaries independently of quoting.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的工作区 `main.rs` 中实现 `click_argv, text_argv, png_dimensions, MacBackend`。保持前几个阶段的实现持续可用。先读函数签名和测试，再一次实现一个边界。fixture 是一个确定性的测试 backend，它的结果不能代表真实的操作系统行为。

使用[公开 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示留给配套的 driver。

把原生 capture、点击和打字都留在 Backend 之后。TSV CLI 操练的是 fixture；可选的原生 adapter 需要单独的权限和一个可丢弃的目标应用。

> Implement `click_argv, text_argv, png_dimensions, MacBackend` in your workspace `main.rs`. Keep earlier stages working. Read the function signatures and tests first, then implement one boundary at a time. The fixture is a deterministic test backend, and its results do not establish native operating-system behavior.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Keep native capture, click and typing behind Backend. The TSV CLI exercises the fixture; the optional native adapter needs separate permissions and a disposable target application.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py desktop-control --init learning-artifacts/desktop-control` 做一次初始化。然后按阶段累计评分：

```bash
python3 scripts/project_test.py desktop-control --stage 4 --path learning-artifacts/desktop-control --strict
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

检查 cli.rs 产生的 frame-1.ppm、frame-4.ppm 和 frame-6.ppm。解释变化的像素证明了什么，以及为什么它们不能确立真实的 macOS 行为。

CLI 使用的是 fixture backend。原生 capture 是 main.rs 里单独的选择性开启（opt-in）命令；macOS 的点击/打字方法需要 OS 权限，在这里保持未验证状态。generation 失效检测的是本 controller 自己的变更，而不是桌面上任意的外部改动。

> Inspect frame-1.ppm, frame-4.ppm and frame-6.ppm from cli.rs. Explain what the changing pixels prove and why they cannot establish native macOS behavior.
> The CLI uses the fixture backend. Native capture is a separate opt-in main.rs command; macOS click/type methods require OS permission and remain unverified here. Generation invalidation detects this controller's mutations, not arbitrary external desktop changes.

## References · 参考资料

[Rust 进程命令](https://doc.rust-lang.org/std/process/struct.Command.html)
[AppleScript 语言指南](https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide/)
[PNG 规范](https://www.w3.org/TR/png-3/)
