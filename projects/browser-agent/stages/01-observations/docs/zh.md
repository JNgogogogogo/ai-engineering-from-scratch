# Turn DOM state into constrained actions · 把 DOM 状态变成受约束的动作

Stage 1 of 4. 第 1 阶段（共 4 阶段）。开始前先读[项目前置要求](../../../README.md)；本阶段建立在前面的契约之上。

> Stage 1 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

从一个小表单里读取 label、value、disabled 状态和稳定 id。校验 id 的唯一性和字段类型。一次只选一个动作：先填 name，再填 email，然后点击那个用唯一 id 标识的「Save request」按钮。页面上的文字永远不会被当作指令来解释。字段缺失、label 有歧义、危险按钮、意料之外的 origin，都会导致一个明确的 blocked 结果。

本阶段的边界是 `parseObservation, choose`。保持前面阶段的行为不变：最终评分器会用同一个 workspace 跑所有阶段。

> Read labels, values, disabled states and stable ids from a small form. Validate unique ids and field types. Choose one action at a time: fill the name, fill email, then click the uniquely identified Save request button. Page prose is never interpreted as instructions. Missing fields, ambiguous labels, dangerous buttons and unexpected origins cause an explicit blocked result.
> The boundary for this stage is `parseObservation, choose`. Keep earlier stage behavior intact: the final grader runs every stage against the same workspace.

## Work through one concrete case · 过一遍具体案例

页面上有两个字段：Full name 和 Full name confirmation。只有与请求的 label 完全一致才算匹配；选第一个模糊匹配可能把值填进错误的控件。如果两个字段共享同一个请求 label，就在改动页面之前直接 block。

```figure
pj-browser-agent-1
```

修改实验输入，先自己算出结果，再去看它的 metrics。figure 是根据这些输入计算的；下面的实现测试仍然是完成与否的判定依据。

> A page has fields Full name and Full name confirmation. Only exact requested labels may match; choosing the first fuzzy match can fill the wrong control. If two fields share the requested label, block before mutation.
> Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的 workspace 的 `main.ts` 里实现 `parseObservation, choose`。先自己尝试实现契约，之后再去读参考实现导出的类型。保留 starter 的公开命名，测试才能调用你的实现。核心函数返回结构化值，不要在函数内部打印；最终结果由 CLI 打印。

使用[公开 API 契约](../../../API.md)和带类型的 starter 签名。核心函数只负责返回值，文件输入、参数解析和展示都交给随附的 driver。

把 Task 当作调用方的权威，把 Observation 当作不可信的页面状态。fill 或 click 的值只能由观察到的 id 构造；页面文字永远不提供代码或命令。

> Implement `parseObservation, choose` in your workspace `main.ts`. Read the exported types in the reference only after attempting the contract. Preserve the starter's public names so tests can call your implementation. Return structured values instead of printing inside the core function; the CLI prints the final result.
> Use the [public API contract](../../../API.md) and the typed starter signatures. Return values from core functions and let the supplied driver own file input, argument parsing and presentation.
> Treat Task as caller authority and Observation as untrusted page state. Build one fill or click value from observed ids; page prose never supplies code or commands.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py browser-agent --init learning-artifacts/browser-agent` 初始化一次。然后按阶段累积评分：

```bash
python3 scripts/project_test.py browser-agent --stage 1 --path learning-artifacts/browser-agent --strict
```

全新 workspace 在你实现契约之前应当失败。所有阶段都完成后，用随附样例运行你真正的产物：

```bash
cd learning-artifacts/browser-agent
node cli.ts --task samples/contact.json --output browser-run.json
```

> From the repository root, initialize once with `python3 scripts/project_test.py browser-agent --init learning-artifacts/browser-agent`. Then grade cumulatively:
> A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample:

## Investigate the failure boundary · 探查失败边界

在 email 与任务要求不一致时把 done 设为 true。即使出现了绿色的成功横幅，完成判定也必须失败。

> Set done=true while the email differs from the task. Completion must fail even if a green banner is present.

## References · 参考资料

[Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
[PNG specification](https://www.w3.org/TR/png-3/)
[HTML form controls](https://html.spec.whatwg.org/multipage/forms.html)
