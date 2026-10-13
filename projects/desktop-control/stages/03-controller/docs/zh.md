# Reject stale observations and exhausted budgets · 拒绝过期观察与耗尽的预算

第 3 阶段（共 4 阶段）。开始之前先阅读[项目前置要求](../../../README.md)；本阶段建立在此前各阶段契约之上。

> Stage 3 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

在 backend 外面套一层 Controller。每次调用 backend 之前先预留动作 budget（预算），点击之前要求先有一帧已捕获的 frame，而任何一次变更（mutation）之后都要让这帧 frame 失效。过期的 generation 必须在点击之前就失败。保留成功动作的 trace，并且即使 backend 返回错误，也要把尝试过的 backend 调用计入。

> Place a Controller around the backend. Reserve action budget before each backend call, require a captured frame before clicks, and invalidate that frame after a mutation. A stale generation must fail before clicking. Keep a trace of successful actions and count attempted backend calls even when the backend returns an error.

## Work through one concrete case · 过一个具体例子

捕获 generation 0，点击一次，然后再用 generation 0 尝试一次点击。controller 在第一次变更之后就让自己保存的 frame 失效，所以第二次点击需要一次新的捕获。

```figure
pj-desktop-control-3
```

改一改 lab 输入，先自己算出结果再去看图中的指标。图形会根据这些输入实时计算；下方的实现测试仍是完成判定的依据。

> Capture generation 0, click once, then try another click with generation 0. The controller invalidates its saved frame after the first mutation, so the second click requires a new capture.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的工作区 `main.rs` 中实现 `Controller.capture, Controller.click, Controller.type_text`。保持前几个阶段的实现持续可用。先读函数签名和测试，再一次实现一个边界。fixture 是一个确定性的测试 backend，它的结果不能代表真实的操作系统行为。

使用[公开 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示留给配套的 driver。

在调用可能失败的 backend 方法之前，先预留调用 budget。backend 失败同样消耗掉一次已尝试的调用。在变更之前清掉缓存的 frame，这样出错后就不会留下仍可被不安全复用的缓存。

> Implement `Controller.capture, Controller.click, Controller.type_text` in your workspace `main.rs`. Keep earlier stages working. Read the function signatures and tests first, then implement one boundary at a time. The fixture is a deterministic test backend, and its results do not establish native operating-system behavior.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Reserve the call budget before invoking a fallible backend method. A backend failure still consumed an attempted call. Clear the cached frame before mutation so an error cannot leave unsafe reuse available.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py desktop-control --init learning-artifacts/desktop-control` 做一次初始化。然后按阶段累计评分：

```bash
python3 scripts/project_test.py desktop-control --stage 3 --path learning-artifacts/desktop-control --strict
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

用配套 TSV 跑出 33 次 capture。32 次调用的 budget 必须让执行停下来，并报告动作文件里的物理行号。

> Run the supplied TSV with 33 captures. The 32-call budget must stop execution and report the physical action-file line.

## References · 参考资料

[Rust 进程命令](https://doc.rust-lang.org/std/process/struct.Command.html)
[AppleScript 语言指南](https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide/)
[PNG 规范](https://www.w3.org/TR/png-3/)
