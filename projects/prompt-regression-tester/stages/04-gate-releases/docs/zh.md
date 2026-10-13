# Gate releases on explicit tolerances · 用显式容差为发布把关

**4 个阶段中的第 4 个。** Python。预计约 2 小时。

发布规则把测量值转化为一个决定。要求一个最低通过比例（minimum pass fraction）和一个最大回归数（maximum regressions）。先检查阈值的取值范围：NaN 和越界的值绝不能让门槛悄悄失效。

空的测试套件按「失败即关闭」（fail closed）处理。「零证据的发布决定」和「零失败的发布」不是一回事。输出会把各项测量值和决定放在一起，便于复查。

```figure
pj-prompt-regression-tester-4
```

主要参考：[主要技术参考](https://docs.python.org/3/library/difflib.html)。

> A release rule converts measurements into a decision.
> Require a minimum pass fraction and a maximum number of regressions.
> Check the threshold domain first: NaN and out-of-range values must not disable the gate.
> An empty suite fails closed.
> A release decision with zero evidence is not the same as a release with zero failures.
> The output keeps its measurements next to the decision for review.

## Worked Orchard case · Orchard 实战案例

在动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html) 和 [结构化输出](../../../../../phases/11-llm-engineering/03-structured-outputs/docs/en.md)。先完成 [阶段 3](../../03-pair-revisions/docs/en.md)。

你的发布门槛是一段可执行的策略。三个用例中出现一次回归，候选版本就会被拦截，哪怕它的其他响应都有改善。把 JSON 和 Markdown diff 保存为 CI 构件（artifact）。

```text
cases=3; candidate passes=2; regressions=1
minimum pass fraction=1; regression budget=0
decision=block; CLI exit=1
```

> Before coding, review [Python data structures](https://docs.python.org/3/tutorial/datastructures.html) and [Structured outputs](../../../../../phases/11-llm-engineering/03-structured-outputs/docs/en.md). Complete [stage 3](../../03-pair-revisions/docs/en.md) first.
> Your release gate is an executable policy.
> With three cases and one regression, a candidate is blocked even if its other responses improve.
> Save the JSON and Markdown diff as CI artifacts.

## Build and inspect · 构建与检查

在比较数字之前，先检查阈值都是有限值、且套件非空。退出状态码必须与报告的决定一致。

在你的学习工作区（learner workspace）里实现该阶段。这些 CLI 助手是官方提供的适配器，负责导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py prompt-regression-tester --stage 4 --path learning-artifacts/prompt-regression-tester
```

在各阶段累计通过之后，从仓库根目录用原始示例输入运行你的产物：

```bash
python3 learning-artifacts/prompt-regression-tester/cli.py projects/prompt-regression-tester/examples/cases.json projects/prompt-regression-tester/examples/baseline.json projects/prompt-regression-tester/examples/candidate.json --out prompt-diff.json --markdown prompt-diff.md
```

随附的录制内容是人工编写的 fixture。这个工具比较的是录制好的响应；它不会调用模型，也无法确立语义上的正确性。JSON 的 case 文件和响应文件就是公开接口。被拦截的门槛以退出码 1 结束。

> Check that thresholds are finite and the suite is nonempty before comparing numbers.
> Exit status must agree with the reported decision.
> Implement the stage in your learner workspace. The CLI helpers are provided adapters and import your functions; they do not substitute the reference solution.
> After the cumulative stages pass, run your artifact on the original sample input from the repository root:
> The supplied recordings are authored fixtures.
> The tool compares recorded responses; it does not call a model or establish semantic correctness.
> JSON case and response files are the public interface. A blocked gate exits 1.

## Investigate next · 接下来探究

在一次真实的支持事故之后，你会新增哪条断言？又要如何保住它的录制出处（provenance）？

> Which assertion would you add after a real support incident, and how would you keep its recording provenance?
