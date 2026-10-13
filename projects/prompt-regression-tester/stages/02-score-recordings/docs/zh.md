# Score recorded outputs without a model · 不调用模型，为录制输出评分

**4 个阶段中的第 2 个。** Python。预计约 2 小时。

「录制与回放」（record and replay）把评分器与模型可用性、采样随机性隔离开来。每条响应都要对照每条 check 评分；一个 case 只有在它的全部 check 都通过时才算通过。缺失的响应按失败处理。

字面子串检查（literal substring check）在设计上就是区分大小写的。规范化大小写或标点会改变断言本身，所以当确实需要这类转换时，应把它显式做成另一种 check 类型。

```figure
pj-prompt-regression-tester-2
```

主要参考：[主要技术参考](https://docs.python.org/3/library/difflib.html)。

> Record and replay isolates the evaluator from model availability and sampling variance.
> Each response is scored against each check; a case passes only when all its checks pass. Missing responses are failures.
> Literal substring checks are case-sensitive by design.
> Normalizing case or punctuation would change the assertion, so make such transformations explicit in a separate check type when needed.

## Worked Orchard case · Orchard 实战案例

在动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html) 和 [结构化输出](../../../../../phases/11-llm-engineering/03-structured-outputs/docs/en.md)。先完成 [阶段 1](../../01-validate-cases/docs/en.md)。

一个合法的 JSON 响应仍然可能漏掉它的 source。要对每一条断言都评分，并保留各自的结果，让维护者能看清是哪个承诺（promise）失败了。

```text
response: {"answer":"ready"}
json -> true
contains("source:") -> false
case passed -> false
```

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Structured outputs](../../../../../phases/11-llm-engineering/03-structured-outputs/docs/en.md). Complete [stage 1](../../01-validate-cases/docs/en.md) first.
> A valid JSON response can still omit its source.
> Score every assertion and retain the individual results so a maintainer can see which promise failed.

## Build and inspect · 构建与检查

先逐条评估 check 列表，然后应用 all()。缺失的响应绝不能变成一张「空的、全部通过」的清单。

在你的学习工作区（learner workspace）里实现该阶段。这些 CLI 助手是官方提供的适配器，负责导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py prompt-regression-tester --stage 2 --path learning-artifacts/prompt-regression-tester
```

先预测上面的中间状态，再运行该阶段。全新的 stub 会失败；参考实现能跑通，并不代表你的学习工作区已经完成。

> Evaluate the list of checks first, then apply all(). A missing response must not become an empty passing checklist.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> Predict the intermediate state above, then run the stage.
> A fresh stub fails; a passing reference run does not establish completion of your learner workspace.

## Investigate next · 接下来探究

在 excludes 检查之前先把响应转成小写，这会改变 API_KEY 的契约吗？

> Would lowercasing the response before an excludes check change the contract for API_KEY?
