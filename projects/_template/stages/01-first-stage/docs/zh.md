# Parse a bounded task label · 解析有界任务标签

队列要先有稳定的标识符（identifier），才能可靠地对工作去重。

> A queue needs stable identifiers before it can reliably deduplicate work.

**Type:** Build
**Languages:** Python
**Stage:** 第 1 阶段 / 共 4 阶段（starter 起步模板；在此草稿上扩展）
**Time:** ~1 小时

> **Stage:** 1 of 4 (starter; extend this draft)

---

## What you build · 你要构建什么

在 `your_package/first.py` 中实现 `first_function(argument: str) -> str`。它返回一个规范化后的标识符，或抛出一个能区分「输入类型错了」还是「语法错了」的错误。

> Implement `first_function(argument: str) -> str` in `your_package/first.py`. It returns a normalized identifier or raises an error that identifies whether the input type or grammar is wrong.

---

## Why it matters · 为什么重要

一个把 `Ship-Report` 和 `ship-report` 当成两个不同任务的 worker，可能会重复投递同一件事。解析器的作用是在任务进入持久化存储之前，先建立单一的表示形式。

> A worker that treats `Ship-Report` and `ship-report` as different tasks can duplicate a delivery. A parser establishes a single representation before the task reaches persistent storage.

---

## The concept · 概念

先去掉首尾空白并把标签转为小写，再对整个结果做校验。例如 `  Ship-Report2  ` 会变成 `ship-report2`。内部空白仍然是非法的。不要把坏字符一路删到字符串碰巧通过为止：`ship/report` 和 `ship-report` 可能指代不同的任务。

在把这个项目标记为 ready 之前，添加一个原创且已注册的 `figure` 机制，展示输入、规范化、长度检查、语法检查，以及接受或拒绝的终态。

> Normalize surrounding whitespace and lowercase the label, then validate the entire result. For example, `  Ship-Report2  ` becomes `ship-report2`. Internal whitespace remains invalid. Do not remove bad characters until the string happens to pass: `ship/report` and `ship-report` might refer to different tasks.
> Add an original, registered `figure` mechanism before marking this project ready. Show the input, normalization, length check, grammar check, and accepted or rejected terminal state.

---

## Your task · 你的任务

```python
def first_function(argument: str) -> str: ...
```

非字符串输入用 `TypeError` 拒绝。规范化后的标签必须为 1 到 32 个字符，以一个 ASCII 字母开头，只含小写 ASCII 字母、数字，以及非空段之间的单个连字符。非法字符串抛 `ValueError`。该函数不得有任何文件系统或网络副作用。

> Reject non-string inputs with `TypeError`. A normalized label must have 1 to 32 characters, begin with an ASCII letter, and contain lowercase ASCII letters, digits or single hyphens between nonempty segments. Invalid strings raise `ValueError`. The function has no filesystem or network effects.

---

## Run the tests · 跑测试

```bash
python3 scripts/project_test.py your-project-id --stage 1 --path /tmp/my-project-work
```

测试会区分类型错误与畸形文本，并检查规范化、边界、歧义分隔符以及类似路径穿越的字符串。在查看解答之前，先往自己的测试里加一个没出现过的例子。

> The tests distinguish type errors from malformed text and check normalization, boundaries, ambiguous separators and traversal-like strings. Add an unseen example to your own tests before you inspect the solution.

---

## Check yourself · 自查

1. 为什么拒绝斜杠比把它替换成连字符更安全？
2. 只测试一个正常标签会漏掉哪个边界？

> 1. Why is rejecting a slash safer than replacing it with a hyphen?
> 2. Which boundary would be missed by testing only a normal label?

---

## Going further · 进阶

把通过校验的标签当作第二阶段的任务键（task key），然后加入显式的重复处理和一个有界重试状态机。把这个脚手架扩展成四个完整阶段，并录制一次真实的 artifact 演示。

> Use the accepted label as a task key in stage two, then add explicit duplicate handling and a bounded retry state machine. Extend this scaffold to four complete stages and record a real artifact demonstration.
