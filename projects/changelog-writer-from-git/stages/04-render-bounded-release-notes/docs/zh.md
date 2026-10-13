# Render bounded release notes · 渲染有边界的发布说明

> commit `[x](bad)` -> escaped literal label in release notes

**Type:** Build
**Languages:** Go
**Stage:** 4 of 4
**Time:** ~2 hours

## Build a release artifact from an actual repository · 从真实仓库构建发布产物

CLI 接受你的仓库路径和两个 revision。它把两个名字都解析成不可变的 commit ID，读取 from 排他、to 包含的区间，产出 Markdown 和一个可选的 JSON receipt。它从不改动 checkout，也不发布 release。

> The CLI accepts your repository path and two revisions. It resolves both names to immutable commit IDs, reads the exclusive-from to inclusive-to range and produces Markdown plus an optional JSON receipt. It never changes the checkout or publishes a release.

## Work through one case · 过一个案例

运行 `go run . --repo /path/to/repo --from v1.0 --to HEAD --label v1.1 --output release.md --receipt release.json`。检查 receipt 里的 hash 和迁移小节。footer 标明的是作者说过必须改什么；它并不能证明那些说明是完整的。

```figure
pj-changelog-writer-from-git-4
```

> Run `go run . --repo /path/to/repo --from v1.0 --to HEAD --label v1.1 --output release.md --receipt release.json`. Inspect the receipt hash and the migration section. A footer identifies what an author said must change; it does not prove that those instructions are complete.

## Your task · 你的任务

```go
func Release(label string,commits []Commit,max int)(string,error)
```

在你的 workspace 里实现这些公开签名。把非法输入与预算上限、状态冲突区分开。操作失败时保留原始证据或输入记录。测试直接加载你的 workspace，所以在签入的参考解答里实现别的函数并不能让你的阶段前进。

> Implement these public signatures in your workspace. Keep invalid input separate from a budget limit or state conflict. Preserve the original evidence or input record whenever an operation fails. Tests load your workspace directly, so implementing a different function in the checked-in solution does not advance your stage.

## Run the tests · 运行测试

```bash
python3 scripts/project_test.py changelog-writer-from-git --stage 4 --path /tmp/changelog-writer-from-git-work
```

本阶段检查 Output、BadLabel、Limit、Escape、SectionOrder。用失败的用例定位你违反的那条不变量。只通过正常示例并不能证明边界行为成立。

> The stage checks Output, BadLabel, Limit, Escape, SectionOrder. Use the failing case to locate the invariant you violated. Passing the normal example alone does not establish the boundary behavior.

## Implementation hints · 实现提示

渲染之前先校验 label 和 commit 预算。把描述转义成字面 Markdown，使用固定的小节顺序，并包含每一个源 hash。随附的适配器使用参数数组、十秒时限和有界输出缓冲；没有任何 shell 会去解释 commit 文本。

先从一条合法记录开始，在优化之前先把拒绝用例加上。失败时保持源数据不变，调用方才能诊断发生了什么。用能表达这个边界的最小函数；多余的一层框架只会遮住你正在学的机制。

> Validate the label and commit budget before rendering. Escape the description as literal Markdown, use a fixed section order and include every source hash. The provided adapter uses argument arrays, a ten-second deadline and a bounded output buffer; no shell interprets commit text.
> Start with one valid record, then add the rejection case before optimizing. Keep source data unchanged on failure so the caller can diagnose what happened. Use the smallest function that expresses the boundary; an extra framework would hide the mechanism you are learning.

## Check your understanding · 检查你的理解

从一个很小的临时仓库生成 release，然后比较前后的 git status。在新分支里改动一个源 commit，展示导出指纹随之变化。手工发布之前，先审查显式的 revert 引用。

在运行测试之前写下你的预测。如果结果让你意外，就沿着校验、状态构造、输出把输入走一遍。参考实现通过只是一个对照工具；你自己的 workspace 必须通过累积评分器才算完成。

> Generate a release from a tiny temporary repository, then compare git status before and after. Change one source commit in a new branch and show that the export fingerprint changes. Review explicit revert references before publishing manually.
> Write your prediction before running the test. If the result surprises you, trace the input through validation, state construction and output. A passing reference implementation is a comparison tool; your own workspace must pass the cumulative grader to establish completion.

## Use it with your own data · 用你自己的数据

`--repo PATH --from REV --to REV` 读取一个不可变的 Git 区间。另外，`--input FILE` 接受 `git log --format=%H%x00%s%x00%b%x00 FROM..TO` 的输出。加上 `--output release.md --receipt release.json` 可以得到可复用的产物。不带参数则使用原创的双 commit fixture。受支持的仓库档案使用 SHA-1 commit ID；SHA-256 仓库需要扩展 hash 格式。

> `--repo PATH --from REV --to REV` reads an immutable Git range. Alternatively, `--input FILE` accepts `git log --format=%H%x00%s%x00%b%x00 FROM..TO` output. Add `--output release.md --receipt release.json` for reusable artifacts. No argument means an original two-commit fixture. The supported repository profile uses SHA-1 commit IDs; SHA-256 repositories require a hash-format extension.

## Sources · 来源

[Git pretty formats](https://git-scm.com/docs/pretty-formats).
