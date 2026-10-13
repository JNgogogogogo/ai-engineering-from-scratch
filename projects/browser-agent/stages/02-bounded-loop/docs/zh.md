# Stop on completion, stalling or budget · 在完成、停滞或预算耗尽时停止

Stage 2 of 4. 第 2 阶段（共 4 阶段）。开始前先读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 2 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

每个动作之后都要重新观察。当状态重复、策略阻止某个动作、或步数预算耗尽时停止。完成判定需要 DOM 成功标志，外加一次独立的截图检查。每个被选中的动作在执行前都要记录 trace。fixture 后端明确是一个模拟器：它提供确定性的观察来测试这个循环，并不声称覆盖真实浏览器。

本阶段的边界是 `runAgent, FixtureDriver`。保持前面阶段的行为不变：最终评分器会用同一个 workspace 跑所有阶段。

> Observe after every action. Stop if the state repeats, if policy blocks an action, or if the step budget is consumed. Completion requires the DOM success flag and a separate screenshot check. Trace every selected action before execution. The fixture backend is explicitly a simulator; it supplies deterministic observations to test the loop and does not claim browser coverage.
> The boundary for this stage is `runAgent, FixtureDriver`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 过一遍具体案例

一个空的两字段表单需要四次观察：填 name、填 email、提交、验证。预算为 3 时可以执行提交，但无法确立完成状态，因此终止状态仍然是 budget-exhausted（预算耗尽）。

```figure
pj-browser-agent-2
```

修改实验输入，先自己算出结果，再去看它的 metrics。figure 是根据这些输入计算的；下面的实现测试仍然是完成与否的判定依据。

> An empty two-field form needs four observations: fill name, fill email, submit, verify. A budget of 3 can perform the submit but cannot establish completion, so the terminal state remains budget-exhausted.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的 workspace 的 `main.ts` 里实现 `runAgent, FixtureDriver`。先自己尝试实现契约，之后再去读参考实现导出的类型。保留 starter 的公开命名，测试才能调用你的实现。核心函数返回结构化值，不要在函数内部打印；最终结果由 CLI 打印。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只负责返回值，文件输入、参数解析和展示都交给随附的 driver。

每次改动之后都要观察。比较前后两次完整观察以检测 driver 停滞；在接受 done 之前先比较请求的值。如果截图的捕获或检查失败，返回 `status: "screenshot-error"`、trace、原因，以及截图路径（可用时给出；捕获失败时为 `null`）。没有检查过图像时就省略视觉指标。直接调用 `inspectPNG` 遇到无效图像时仍然抛错。

> Implement `runAgent, FixtureDriver` in your workspace `main.ts`. Read the exported types in the reference only after attempting the contract. Preserve the starter's public names so tests can call your implementation. Return structured values instead of printing inside the core function; the CLI prints the final result.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Observe after every mutation. Compare successive complete observations to detect a stalled driver; compare requested values before accepting done. If capturing or inspecting the screenshot fails, return `status: "screenshot-error"`, the trace, a reason, and the screenshot path when available (`null` if capture failed). Omit visual metrics when no image was inspected. Direct calls to `inspectPNG` still throw on invalid images.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py browser-agent --init learning-artifacts/browser-agent` 初始化一次。然后按阶段累积评分：

```bash
python3 scripts/project_test.py browser-agent --stage 2 --path learning-artifacts/browser-agent --strict
```

全新 workspace 在你实现契约之前应当失败。所有阶段都完成后，用随附样例运行你真正的产物：

```bash
cd learning-artifacts/browser-agent
node cli.ts --task samples/contact.json --output browser-run.json
```

> From the repository root, initialize once with `python3 scripts/project_test.py browser-agent --init learning-artifacts/browser-agent`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

使用 samples/accessibility.json，其中 name 一栏本来就是正确的。解释为什么在不改变策略的情况下，现在三次观察就足够了。

> Use samples/accessibility.json, where the name is already correct. Explain why three observations now suffice without changing the policy.

## References · 参考资料

[Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
[PNG specification](https://www.w3.org/TR/png-3/)
[HTML form controls](https://html.spec.whatwg.org/multipage/forms.html)
