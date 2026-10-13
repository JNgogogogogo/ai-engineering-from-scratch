# Publish an escaped HTML checklist and summary · 发布经过转义的 HTML 清单与摘要

第 4 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 4 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

清单只有在解析器之外也可读、可审查时才真正有用。在把 owner、日期、任务和 source 行渲染进 HTML 之前，先校验 source line citation，并对每个被渲染的字段做转义（escape）。只有相对一个显式给定的日期，才能标记逾期（overdue）。

HTML 是一个静态的审查产物。它不发消息，也不在其他系统里创建任务。它的计数器把 ready、incomplete、overdue 三类 action 分开，让读者能安排审查的优先级。

> A checklist becomes useful when it is readable and reviewable outside the parser. Validate source line citations before rendering owners, dates, tasks, and source lines into HTML, escaping every rendered field. Mark overdue items only relative to an explicit supplied date. ... The HTML is a static review artifact. It sends no messages and creates no tasks in other systems.

## Work through one concrete case · 走一遍具体案例

第一次 inbox 运行导出 0 行，因为 ready 不等于 approved。在 HTML 上做出明确的选择、下载一个 JSON 决策文件之后，下一次 CLI 运行只把 approved 且完整的行导出为 CSV。

```figure
pj-meeting-notes-to-actions-4
```

修改实验（lab）的输入，先自己算出结果，再去看它的指标。图中数字由这些输入计算而来；下面的实现测试仍然是完成与否的证据来源。

> The first inbox run exports zero rows because ready is not approved. The HTML selects explicit decisions, downloads a JSON decision file and the next CLI run exports only approved complete rows to CSV. ... Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

按照上述契约实现 `publish`。

使用[公开的 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示交给随附的 driver。

稳定的 id 把审查选择绑定到 owner、due、task 和 source lines。随附的 driver 在校验决策之前给每条当前记录分配 id，然后在写出输出之前拒绝任何未知或过期的 id。来自已变更源行的决策文件必须重新审查。下载决策时，选择器保留当前 approved 与 rejected 的选择。对每个导入字段做转义；HTML 里唯一可执行的脚本是作者编写的决策文件下载器。

> Implement `publish` against the stated contract. ... Stable ids bind review choices to owner, due, task and source lines. A decision file from changed source lines must be reviewed again. Escape every imported field; the only executable script in the HTML is the authored decision-file downloader.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py meeting-notes-to-actions --init learning-artifacts/meeting-notes-to-actions` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py meeting-notes-to-actions --stage 4 --path learning-artifacts/meeting-notes-to-actions --strict
```

全新的 workspace 在你实现契约之前应当判为失败。每个阶段完成后，用随附的样例运行你的真实产物：

```bash
cd learning-artifacts/meeting-notes-to-actions
python3 cli.py samples/notes.txt --today 2026-09-29 --output actions.json --html actions.html --csv approved.csv
```

> From the repository root, initialize once with `python3 scripts/project_test.py meeting-notes-to-actions --init learning-artifacts/meeting-notes-to-actions`. Then grade cumulatively ... A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample.

## Investigate the failure boundary · 探查失败边界

往一个 task 里粘贴一个 script 标签。它必须按源文本渲染，而且下载决策文件时只能包含 action id 和允许的决策值。

`ACTION` 行是权威候选；`NAME will TASK by YYYY-MM-DD` 是一套保守的 proposal 语法。这两种语法之外的非结构化建议保持未分配。HTML 审查不发任务、不发消息。

> Paste a script tag into a task. It must render as source text, and downloading decisions must contain only action ids and allowed decision values. ... ACTION lines are authoritative candidates; NAME will TASK by YYYY-MM-DD is a conservative proposal grammar. HTML review does not post tasks or send messages.

## References · 参考资料

[主要技术参考](https://docs.python.org/3/library/datetime.html)
