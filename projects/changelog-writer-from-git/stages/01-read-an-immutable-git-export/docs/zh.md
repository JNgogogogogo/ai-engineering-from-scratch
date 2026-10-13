# Read an immutable Git export · 读取不可变的 Git 导出

> git log --format=%h%x09%s -> hash and subject

**Type:** Build
**Languages:** Go
**Stage:** 1 of 4
**Time:** ~2 hours

## Read records without losing the evidence · 读记录，不弄丢证据

一个 Git commit 有 hash、subject 和 body。第一个练习刻意从 hash-tab-subject 记录开始，让你先学会解析边界，之后随附的 Git 适配器才会去处理 NUL 分隔的 body。绝不要把完整的 commit body 按换行切开、把每一行假装成一条新 commit。

> A Git commit has a hash, a subject and a body. The first exercise deliberately starts with hash-tab-subject records so you can learn the parsing boundary before the provided Git adapter handles NUL-delimited bodies. Never split a full commit body on newlines and pretend each line is a new commit.

## Work through one case · 过一个案例

两条记录 `abc1234\tfeat: cache` 和 `abc1234\tfix: cache` 即使 subject 不同也互相冲突。建立一个已接受 hash 的集合。在追加第二条记录之前先检查它的 hash；返回冲突，不给出部分结果。

```figure
pj-changelog-writer-from-git-1
```

> The two records `abc1234\tfeat: cache` and `abc1234\tfix: cache` conflict even though their subjects differ. Build a set of accepted hashes. Check the second hash before appending its record; return a conflict with no partial result.

## Your task · 你的任务

```go
func ParseLog(text string)([]Commit,error)
```

在你的 workspace 里实现这些公开签名。把非法输入与预算上限、状态冲突区分开。操作失败时保留原始证据或输入记录。测试直接加载你的 workspace，所以在签入的参考解答里实现别的函数并不能让你的阶段前进。

> Implement these public signatures in your workspace. Keep invalid input separate from a budget limit or state conflict. Preserve the original evidence or input record whenever an operation fails. Tests load your workspace directly, so implementing a different function in the checked-in solution does not advance your stage.

## Run the tests · 运行测试

```bash
python3 scripts/project_test.py changelog-writer-from-git --stage 1 --path /tmp/changelog-writer-from-git-work
```

本阶段检查 Valid、Duplicate、BadHash、NoSubject、Empty。用失败的用例定位你违反的那条不变量。只通过正常示例并不能证明边界行为成立。

> The stage checks Valid, Duplicate, BadHash, NoSubject, Empty. Use the failing case to locate the invariant you violated. Passing the normal example alone does not establish the boundary behavior.

## Implementation hints · 实现提示

用 limit 为 2 的 SplitN，让第一个分隔符定义边界。校验 hash 的每一个字符，然后拒绝空 subject。集成适配器单独保留 body 文本，并把导出上限设在 4 MiB。

先从一条合法记录开始，在优化之前先把拒绝用例加上。失败时保持源数据不变，调用方才能诊断发生了什么。用能表达这个边界的最小函数；多余的一层框架只会遮住你正在学的机制。

> Use SplitN with a limit of two so the first separator defines the boundary. Validate every hash character, then reject an empty subject. The integration adapter retains body text separately and caps exports at 4 MiB.
> Start with one valid record, then add the rejection case before optimizing. Keep source data unchanged on failure so the caller can diagnose what happened. Use the smallest function that expresses the boundary; an extra framework would hide the mechanism you are learning.

## Check your understanding · 检查你的理解

为什么 commit body 可以包含换行，而 subject 导出不行？构造一个被截断的 NUL 导出，解释适配器为什么拒绝它。

在运行测试之前写下你的预测。如果结果让你意外，就沿着校验、状态构造、输出把输入走一遍。参考实现通过只是一个对照工具；你自己的 workspace 必须通过累积评分器才算完成。

> Why can a commit body contain a newline while a subject export cannot? Construct a truncated NUL export and explain why the adapter refuses it.
> Write your prediction before running the test. If the result surprises you, trace the input through validation, state construction and output. A passing reference implementation is a comparison tool; your own workspace must pass the cumulative grader to establish completion.

## Use it with your own data · 用你自己的数据

`--repo PATH --from REV --to REV` 读取一个不可变的 Git 区间。另外，`--input FILE` 接受 `git log --format=%H%x00%s%x00%b%x00 FROM..TO` 的输出。加上 `--output release.md --receipt release.json` 可以得到可复用的产物。不带参数则使用原创的双 commit fixture。受支持的仓库档案使用 SHA-1 commit ID；SHA-256 仓库需要扩展 hash 格式。

> `--repo PATH --from REV --to REV` reads an immutable Git range. Alternatively, `--input FILE` accepts `git log --format=%H%x00%s%x00%b%x00 FROM..TO` output. Add `--output release.md --receipt release.json` for reusable artifacts. No argument means an original two-commit fixture. The supported repository profile uses SHA-1 commit IDs; SHA-256 repositories require a hash-format extension.

## Sources · 来源

[Git pretty formats](https://git-scm.com/docs/pretty-formats).
