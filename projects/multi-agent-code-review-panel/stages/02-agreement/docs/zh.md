# Aggregate independent support · 聚合独立支持

第 2 阶段（共 4 阶段）。开始前先阅读[项目前置要求](../../../README.md)；本阶段建立在前面各阶段契约的基础上。

> Stage 2 of 4. Read the [project prerequisites](../../../README.md) before starting; this stage builds on the preceding contracts.

## What changes · 变化在哪

把有效的 finding 按 file、line、rule 分组。每组里每个 reviewer 计一票，拒绝重复的 reviewer 身份，并保留每一条 severity 投票。达到法定人数（quorum）才算共识；孤证（singleton）仍以 needs-review 的形式可见。disagreement 标记在共识达成后依然保留，让用户能检查相互冲突的 severity 判断。

本阶段的边界是 `aggregate`。保持之前阶段的行为不变：最终评分器会在同一个 workspace 上运行每一个阶段。

> Group valid findings by file, line and rule. Count one vote per reviewer per group, reject duplicate reviewer identities, and retain every severity vote. A quorum produces consensus; a singleton remains visible as needs-review. A disagreement flag survives consensus so the user can inspect conflicting severity judgments.

## Work through one concrete case · 走一遍具体案例

一个 reviewer 把同一条 finding 重复了五次，第二个 reviewer 报了一次。支持数是两个不同的 reviewer id，不是六份报告。`Severities[3,2]` 形成共识，且 `disagreement=true`。

```figure
pj-multi-agent-code-review-panel-2
```

修改实验（lab）的输入，先自己算出结果，再去看它的指标。图中数字由这些输入计算而来；下面的实现测试仍然是完成与否的证据来源。

> One reviewer repeats a finding five times and a second reviewer reports it once. Support is two distinct reviewer ids, not six reports. Severities[3,2] produce consensus with disagreement=true. ... Change the lab inputs and calculate the result before reading its metrics. The figure computes from those inputs; the implementation tests below remain the source of completion evidence.

## Implement the contract · 实现契约

在你的 workspace `main.ts` 里实现 `aggregate`。先自己尝试契约，之后再去读参考实现中导出的类型。保留起始代码的公开名称，测试才能调用你的实现。核心函数返回结构化值，不要在核心函数内部打印；最终结果由 CLI 打印。

使用[公开的 API 契约](../../../API.md)和带类型的起始签名。核心函数只负责返回值，把文件输入、参数解析和展示交给随附的 driver。

按稳定的 `tuple(file,line,rule)` 分组。输出里保留 severity 投票和支持者 id，而不是把决策塌缩成一个布尔值。

> Implement `aggregate` in your workspace `main.ts`. ... Group by the stable tuple(file,line,rule). Keep severity votes and supporter ids in the output rather than collapsing the decision into one boolean.

## Verify and inspect · 验证与检查

在仓库根目录，先用 `python3 scripts/project_test.py multi-agent-code-review-panel --init learning-artifacts/multi-agent-code-review-panel` 初始化一次。然后按阶段累计评分：

```bash
python3 scripts/project_test.py multi-agent-code-review-panel --stage 2 --path learning-artifacts/multi-agent-code-review-panel --strict
```

全新的 workspace 在你实现契约之前应当判为失败。每个阶段完成后，用随附的样例运行你的真实产物：

```bash
cd learning-artifacts/multi-agent-code-review-panel
node cli.ts --input samples/review.json --output panel.json --html panel.html
```

> From the repository root, initialize once with `python3 scripts/project_test.py multi-agent-code-review-panel --init learning-artifacts/multi-agent-code-review-panel`. Then grade cumulatively ... A fresh workspace should fail until you implement the contract. After every stage is complete, run your actual artifact from the supplied sample.

## Investigate the failure boundary · 探查失败边界

在样例上把 quorum 从 2 提到 3。找出哪个真 finding 变成了 needs-review，以及哪个假阳性本来就是孤证。

> Raise quorum from 2 to3 on the sample. Identify which true finding becomes needs-review and which false positive was already a singleton.

## References · 参考资料

[Node 中的 AbortController](https://nodejs.org/api/globals.html#class-abortcontroller)
[Node 测试运行器](https://nodejs.org/api/test.html)
