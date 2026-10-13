# Drive the real fixture and score the run · 驱动真实 fixture 并为运行打分

Stage 4 of 4. 第 4 阶段（共 4 阶段）。开始前先读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 4 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

通过 loopback 提供 fixture.html，并用 gstack browse 导航到它。GstackDriver 读取 DOM 观察、按 label 填写、点击观察到的按钮，并捕获真实截图。命令使用参数数组而不是 shell。用 --live 运行同一个有界策略，把它的 trace 与 fixture 后端的做比较。模拟运行与真实浏览器运行的完成得分分开保留。

本阶段的边界是 `GstackDriver, scoreRuns`。保持前面阶段的行为不变：最终评分器会用同一个 workspace 跑所有阶段。

> Serve fixture.html over loopback and navigate to it with gstack browse. GstackDriver reads DOM observations, fills labels, clicks the observed button and captures a real screenshot. Commands use argument arrays instead of a shell. Run the same bounded policy with --live and compare its trace with the fixture backend. Keep completion scores separate for simulated and real-browser runs.
> The boundary for this stage is `GstackDriver, scoreRuns`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 过一遍具体案例

真实适配器导航到配置好的 loopback URL，通过 JavaScript 读取 label，填写观察到的 id，并捕获 browser-result.png。它的截图来自 Chromium；fixture 模式则有意复用手工构造的像素。

```figure
pj-browser-agent-4
```

修改实验输入，先自己算出结果，再去看它的 metrics。figure 是根据这些输入计算的；下面的实现测试仍然是完成与否的判定依据。

> The real adapter navigates the configured loopback URL, reads labels through JavaScript, fills observed ids and captures browser-result.png. Its screenshot comes from Chromium; fixture mode deliberately reuses authored pixels.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的 workspace 的 `main.ts` 里实现 `GstackDriver, scoreRuns`。先自己尝试实现契约，之后再去读参考实现导出的类型。保留 starter 的公开命名，测试才能调用你的实现。核心函数返回结构化值，不要在函数内部打印；最终结果由 CLI 打印。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只负责返回值，文件输入、参数解析和展示都交给随附的 driver。

在 execFileSync 里把二进制与参数分开。包含引号的 task 值仍然是一个完整的 fill 参数。导航之前先提供允许的 origin，之后每次观察都重新检查它。

> Implement `GstackDriver, scoreRuns` in your workspace `main.ts`. Read the exported types in the reference only after attempting the contract. Preserve the starter's public names so tests can call your implementation. Return structured values instead of printing inside the core function; the CLI prints the final result.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Keep binary and arguments separate in execFileSync. A task value containing quotes remains one fill argument. Supply an allowed origin before navigation, then recheck it on every observation.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py browser-agent --init learning-artifacts/browser-agent` 初始化一次。然后按阶段累积评分：

```bash
python3 scripts/project_test.py browser-agent --stage 4 --path learning-artifacts/browser-agent --strict
```

全新 workspace 在你实现契约之前应当失败。所有阶段都完成后，用随附样例运行你真正的产物：

```bash
cd learning-artifacts/browser-agent
node cli.ts --task samples/contact.json --output browser-run.json
```

> From the repository root, initialize once with `python3 scripts/project_test.py browser-agent --init learning-artifacts/browser-agent`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

在 127.0.0.1:8877 上提供 fixture.html，设置 BROWSE_BIN，然后运行 cli.ts --task samples/contact.json --live。把 mode、动作数和截图一起记录下来。

离线模式锻炼的是 fixture 状态转移和记录下来的像素。像素偏绿是 fixture 特有的信号，不是通用视觉理解。live CLI 只能访问显式允许的 loopback 页面。

> Serve fixture.html at127.0.0.1:8877, set BROWSE_BIN, and run cli.ts --task samples/contact.json --live. Record the mode, action count and screenshot together.
> Offline mode exercises fixture transitions and recorded pixels. Pixel greenness is a fixture-specific signal, not general visual understanding. The live CLI is limited to explicitly allowed loopback pages.

## References · 参考资料

[Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
[PNG specification](https://www.w3.org/TR/png-3/)
[HTML form controls](https://html.spec.whatwg.org/multipage/forms.html)
