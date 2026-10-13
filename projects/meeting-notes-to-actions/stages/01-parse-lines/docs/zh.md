# Parse explicit action records with line provenance · 解析带行级出处的显式 ACTION 记录

第 1 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 1 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

会议自然语言里混杂着建议、决定和承诺。先从显式格式入手：`ACTION owner | YYYY-MM-DD | task`。这个保守的解析器不会从附近出现的名字里凭空捏造 owner。

每条解析出来的记录都保留原始行号和原文。后续的审查者必须能把一条 action 追溯到某人写下的确切内容。非 action 的行不进入输出。

> Natural meeting prose contains suggestions, decisions, and commitments. Start with an explicit format: ACTION owner | YYYY-MM-DD | task. This conservative parser avoids inventing an owner from nearby names. ... Keep the original line number and text on every parsed record. A later reviewer must be able to trace an action to exactly what someone wrote.

## Work through one concrete case · 走一遍具体案例

第 1 行是一个决定，第 2 行是 `ACTION Mira |2026-10-01|Update guide`，第 3 行写着 Maybe ask Ravi。只有第 2 行成为显式候选。另一套独立的 proposal 语法可以在空格被正常补上之后识别出 `Priya will test login by2026-10-02`。

```figure
pj-meeting-notes-to-actions-1
```

修改实验（lab）的输入，先自己算出结果，再去看它的指标。图中数字由这些输入计算而来；下面的实现测试仍然是完成与否的证据来源。

> Line 1 is a decision, line 2 is ACTION Mira |2026-10-01|Update guide, and line 3 says Maybe ask Ravi. Only line 2 becomes an explicit candidate. ... Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

按照上述契约实现 `parse_notes`。

使用[公开的 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示交给随附的 driver。

先枚举原始行，再做过滤。`ACTION` 只按前两个分隔符切分，这样 task 正文里可以再出现一个竖线，而不会让 owner 和 date 错位。

> Implement `parse_notes` against the stated contract. ... Enumerate original lines before filtering. Split ACTION on only the first two separators so the task body can contain another vertical bar without shifting owner and date.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py meeting-notes-to-actions --init learning-artifacts/meeting-notes-to-actions` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py meeting-notes-to-actions --stage 1 --path learning-artifacts/meeting-notes-to-actions --strict
```

全新的 workspace 在你实现契约之前应当判为失败。每个阶段完成后，用随附的样例运行你的真实产物：

```bash
cd learning-artifacts/meeting-notes-to-actions
python3 cli.py samples/notes.txt --today 2026-09-29 --output actions.json --html actions.html --csv approved.csv
```

> From the repository root, initialize once with `python3 scripts/project_test.py meeting-notes-to-actions --init learning-artifacts/meeting-notes-to-actions`. Then grade cumulatively ... A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample.

## Investigate the failure boundary · 探查失败边界

把一条 action 往下移两行再重跑。存储的 citation（源行引用）必须跟着移动，而无关的散文（prose）仍然保持未分配。

> Move an action down two lines and rerun. The stored citation must move too, while unrelated prose remains unassigned.

## References · 参考资料

[主要技术参考](https://docs.python.org/3/library/datetime.html)
