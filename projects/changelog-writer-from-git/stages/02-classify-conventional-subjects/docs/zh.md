# Classify conventional subjects · 分类 Conventional 提交主题

> feat(api)!: remove v1 -> type feat, scope api, breaking true

**Type:** Build
**Languages:** Go
**Stage:** 2 of 4
**Time:** ~2 hours

## Classify a subject without discarding migration risk · 分类 subject，不丢迁移风险

Conventional subject 是一门语法很小的实用语言：type、可选 scope、可选感叹号、冒号加空格、描述。真实仓库里还有 merge commit 和普通散文。把这些记录保留为 Other，发布说明的编辑者才能检查它们。

> Conventional subjects are a useful language with a small grammar: type, optional scope, optional exclamation mark, colon-space, description. Real repositories also have merge commits and ordinary prose. Preserve those records as Other so the release editor can inspect them.

## Work through one case · 过一个案例

`fix(api)!: rename timeout` 给出 kind fix、scope api、breaking true 和描述 rename timeout。一条单独的 `BREAKING CHANGE: Rename config.` footer 在本函数运行之前也会把 breaking 置为 true。你的分类器必须保留这个已有信号，而不是用「没有感叹号」把它覆盖掉。

```figure
pj-changelog-writer-from-git-2
```

> `fix(api)!: rename timeout` gives kind fix, scope api, breaking true and description rename timeout. A separate `BREAKING CHANGE: Rename config.` footer also sets breaking true before this function runs. Your classifier must preserve that existing signal instead of overwriting it with the absence of an exclamation mark.

## Your task · 你的任务

```go
func Classify(c Commit)(Commit,error)
```

在你的 workspace 里实现这些公开签名。把非法输入与预算上限、状态冲突区分开。操作失败时保留原始证据或输入记录。测试直接加载你的 workspace，所以在签入的参考解答里实现别的函数并不能让你的阶段前进。

> Implement these public signatures in your workspace. Keep invalid input separate from a budget limit or state conflict. Preserve the original evidence or input record whenever an operation fails. Tests load your workspace directly, so implementing a different function in the checked-in solution does not advance your stage.

## Run the tests · 运行测试

```bash
python3 scripts/project_test.py changelog-writer-from-git --stage 2 --path /tmp/changelog-writer-from-git-work
```

本阶段检查 Feature、Scope、Breaking、Other、Blank。用失败的用例定位你违反的那条不变量。只通过正常示例并不能证明边界行为成立。

> The stage checks Feature, Scope, Breaking, Other, Blank. Use the failing case to locate the invariant you violated. Passing the normal example alone does not establish the boundary behavior.

## Implementation hints · 实现提示

对 subject 语法只做一次匹配。无法识别的非空 subject 原样保留。把传入的 breaking 标志与标记用逻辑 OR 合并。空 subject 是非法输入，不是 Other 条目。

先从一条合法记录开始，在优化之前先把拒绝用例加上。失败时保持源数据不变，调用方才能诊断发生了什么。用能表达这个边界的最小函数；多余的一层框架只会遮住你正在学的机制。

> Match the subject grammar once. Keep an unrecognized nonblank subject intact. Combine the incoming breaking flag with the marker using logical OR. An empty subject is invalid, not an Other entry.
> Start with one valid record, then add the rejection case before optimizing. Keep source data unchanged on failure so the caller can diagnose what happened. Use the smallest function that expresses the boundary; an extra framework would hide the mechanism you are learning.

## Check your understanding · 检查你的理解

把同一个 subject 分别在传入 breaking 标志为 false 和 true 的情况下分类。哪些字段变了？为什么直接替换标志会丢掉迁移证据？

在运行测试之前写下你的预测。如果结果让你意外，就沿着校验、状态构造、输出把输入走一遍。参考实现通过只是一个对照工具；你自己的 workspace 必须通过累积评分器才算完成。

> Classify the same subject with the incoming breaking flag false and true. Which fields change, and why would replacing the flag lose migration evidence?
> Write your prediction before running the test. If the result surprises you, trace the input through validation, state construction and output. A passing reference implementation is a comparison tool; your own workspace must pass the cumulative grader to establish completion.

## Use it with your own data · 用你自己的数据

`--repo PATH --from REV --to REV` 读取一个不可变的 Git 区间。另外，`--input FILE` 接受 `git log --format=%H%x00%s%x00%b%x00 FROM..TO` 的输出。加上 `--output release.md --receipt release.json` 可以得到可复用的产物。不带参数则使用原创的双 commit fixture。受支持的仓库档案使用 SHA-1 commit ID；SHA-256 仓库需要扩展 hash 格式。

> `--repo PATH --from REV --to REV` reads an immutable Git range. Alternatively, `--input FILE` accepts `git log --format=%H%x00%s%x00%b%x00 FROM..TO` output. Add `--output release.md --receipt release.json` for reusable artifacts. No argument means an original two-commit fixture. The supported repository profile uses SHA-1 commit IDs; SHA-256 repositories require a hash-format extension.

## Sources · 来源

[Git pretty formats](https://git-scm.com/docs/pretty-formats).
