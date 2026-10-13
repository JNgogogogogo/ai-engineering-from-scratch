# Validate cases before scoring · 评分之前先校验用例

**4 个阶段中的第 1 个。** Python。预计约 2 小时。

一个评估用例（evaluation case）需要一个稳定的 id、一个 prompt 和一小串断言（assertion）。当结果被装进字典时，重复的 id 会悄悄覆盖掉已有证据。在回放任何响应之前，先校验 id 和断言类型。

这里的断言指字面文本检查和 JSON 语法检查。它们能发现「契约漂移」（contract drift），但无法证明事实正确性或语气。要把这些局限与你发布门槛（gate）实际强制的内容区分开。

```figure
pj-prompt-regression-tester-1
```

主要参考：[主要技术参考](https://docs.python.org/3/library/difflib.html)。

> An evaluation case needs a stable id, a prompt, and a small set of assertions.
> Duplicate ids silently overwrite evidence when results become a dictionary. Validate ids and assertion types before replaying any responses.
> Assertions here are literal text checks and JSON syntax checks. They are useful for contract drift, but cannot prove factual correctness or tone.
> Separate those limitations from what your gate actually enforces.

## Worked Orchard case · Orchard 实战案例

在动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html) 和 [结构化输出](../../../../../phases/11-llm-engineering/03-structured-outputs/docs/en.md)。

Orchard 必须返回 JSON 并保留来源定位符（source locator）。把 `format-json` 和 `source-link` 保留为两个不同的 case id：它们是对调用方的两个独立承诺。cassette 在对比两次运行之前，会对整个用例列表（包括 prompt 和 check）做哈希。

```text
case ids: [format-json, source-link]
checks: json; contains("source:")
repeat format-json -> reject before replay
```

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Structured outputs](../../../../../phases/11-llm-engineering/03-structured-outputs/docs/en.md).
> Orchard must return JSON and preserve a source locator. Keep `format-json` and `source-link` as different case ids: they are separate promises to the caller.
> The cassette hashes the entire case list, including prompts and checks, before comparing runs.

## Build and inspect · 构建与检查

在校验过程中同步构建 id 集合。在查找某条已录制的响应之前，先校验每一种 check 类型。

在你的学习工作区（learner workspace）里实现该阶段。这些 CLI 助手是官方提供的适配器，负责导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py prompt-regression-tester --init learning-artifacts/prompt-regression-tester
python3 scripts/project_test.py prompt-regression-tester --stage 1 --path learning-artifacts/prompt-regression-tester
```

先预测上面的中间状态，再运行该阶段。全新的 stub 会失败；参考实现能跑通，并不代表你的学习工作区已经完成。

> Build a set of ids while validating. Validate each check kind before looking up a recorded response.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage.
> A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接下来探究

只改动 prompt 的措辞。为什么之前那个 case 的哈希必须不再匹配？

> Change only the prompt wording. Why must the previous case hash stop matching?
