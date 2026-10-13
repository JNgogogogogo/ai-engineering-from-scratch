# Group commits with stable ordering · 用稳定排序给 commit 分组

> feat! appears under Breaking changes, not Features

**Type:** Build
**Languages:** Go
**Stage:** 3 of 4
**Time:** ~2 hours

## Make release groups reproducible · 让发布分组可复现

分组是一个有序的决策。破坏性行为（breaking）优先于 feature 或 fix。组内排序让输出与记录到达程序的顺序无关。源 commit 仍然可以在单独的 JSON receipt 里查到。

> Grouping is an ordered decision. Breaking behavior takes precedence over feature or fix. Sorting inside each group makes the output independent of the order in which records reached your program. The source commit remains available in a separate JSON receipt.

## Work through one case · 过一个案例

输入 hash 为 bbbbbbb 的一个 fix 和 aaaaaaa 的一个 fix，输出变成 aaaaaaa 在前、bbbbbbb 在后。再加入带 `feat!: new wire format` 的 ccccccc；它只属于 Breaking changes。直接对原始输入切片排序会让其他调用方感到意外，所以要把值分类进新建的分组切片。

```figure
pj-changelog-writer-from-git-3
```

> Input hashes bbbbbbb for a fix and aaaaaaa for a fix become aaaaaaa then bbbbbbb. Add ccccccc with `feat!: new wire format`; it belongs only to Breaking changes. Sorting the original input slice would surprise another caller, so classify values into new group slices.

## Your task · 你的任务

```go
func Group(commits []Commit)(map[string][]Commit,error)
```

在你的 workspace 里实现这些公开签名。把非法输入与预算上限、状态冲突区分开。操作失败时保留原始证据或输入记录。测试直接加载你的 workspace，所以在签入的参考解答里实现别的函数并不能让你的阶段前进。

> Implement these public signatures in your workspace. Keep invalid input separate from a budget limit or state conflict. Preserve the original evidence or input record whenever an operation fails. Tests load your workspace directly, so implementing a different function in the checked-in solution does not advance your stage.

## Run the tests · 运行测试

```bash
python3 scripts/project_test.py changelog-writer-from-git --stage 3 --path /tmp/changelog-writer-from-git-work
```

本阶段检查 Features、BreakingFirst、Stable、Unknown、Empty。用失败的用例定位你违反的那条不变量。只通过正常示例并不能证明边界行为成立。

> The stage checks Features, BreakingFirst, Stable, Unknown, Empty. Use the failing case to locate the invariant you violated. Passing the normal example alone does not establish the boundary behavior.

## Implementation hints · 实现提示

先建好分组 map，一次分类一条记录，再把每个结果切片按 hash 排序。不要通过遍历 map 来输出小节，因为 map 的迭代顺序给不出稳定的展示顺序。

先从一条合法记录开始，在优化之前先把拒绝用例加上。失败时保持源数据不变，调用方才能诊断发生了什么。用能表达这个边界的最小函数；多余的一层框架只会遮住你正在学的机制。

> Create the group map, classify one record at a time, then sort each resulting slice by hash. Do not emit sections by ranging over the map because map iteration does not establish a stable presentation order.
> Start with one valid record, then add the rejection case before optimizing. Keep source data unchanged on failure so the caller can diagnose what happened. Use the smallest function that expresses the boundary; an extra framework would hide the mechanism you are learning.

## Check your understanding · 检查你的理解

反复打乱同一份 commit 列表，比较渲染出来的字节。revert 必须和它的目标一起保持可见；解释为什么悄悄把两者同时减掉，可能掩盖之后的一次跟进修改。

在运行测试之前写下你的预测。如果结果让你意外，就沿着校验、状态构造、输出把输入走一遍。参考实现通过只是一个对照工具；你自己的 workspace 必须通过累积评分器才算完成。

> Shuffle the same commit list repeatedly and compare the rendered bytes. A revert must remain visible alongside its target; explain why silently subtracting both commits could hide a later follow-up change.
> Write your prediction before running the test. If the result surprises you, trace the input through validation, state construction and output. A passing reference implementation is a comparison tool; your own workspace must pass the cumulative grader to establish completion.

## Use it with your own data · 用你自己的数据

`--repo PATH --from REV --to REV` 读取一个不可变的 Git 区间。另外，`--input FILE` 接受 `git log --format=%H%x00%s%x00%b%x00 FROM..TO` 的输出。加上 `--output release.md --receipt release.json` 可以得到可复用的产物。不带参数则使用原创的双 commit fixture。受支持的仓库档案使用 SHA-1 commit ID；SHA-256 仓库需要扩展 hash 格式。

> `--repo PATH --from REV --to REV` reads an immutable Git range. Alternatively, `--input FILE` accepts `git log --format=%H%x00%s%x00%b%x00 FROM..TO` output. Add `--output release.md --receipt release.json` for reusable artifacts. No argument means an original two-commit fixture. The supported repository profile uses SHA-1 commit IDs; SHA-256 repositories require a hash-format extension.

## Sources · 来源

[Git pretty formats](https://git-scm.com/docs/pretty-formats).
