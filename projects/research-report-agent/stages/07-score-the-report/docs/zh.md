# Score the public fixtures · 给公开 fixture 打分

> 如果你无法用一个数字衡量它，你就无法判断下一次改动有没有帮助。
> If you cannot put a number on it, you cannot tell whether your next change helped.

**Type:** Build
**Languages:** Python
**Stage:** 7 of 7 (stretch)
**Time:** ~2 hours

## What you build · 你要构建什么

`report_agent/evaluate.py`：

- `citation_precision(report)`：已发布句子中通过词面引用支撑检查的比例。
- `source_recall(report, expected_docs)`：每个问题附带的预期文档中，被你引用的比例。
- `fact_coverage(report, key_facts)`：出现在某个句子里的关键事实比例。
- `evaluate(questions_path, corpus_dir)` 返回一个 `Scorecard`，`format_scorecard` 把它打印出来，带一个满分 100 的最终数字。

```text
id      precision   recall   facts  state
----------------------------------------------
h1           1.00     1.00    1.00  completed
h2           1.00     1.00    1.00  completed
h3           1.00     1.00    1.00  completed
h4           1.00     1.00    0.50  completed
h5           1.00     1.00    0.50  completed
h6           1.00     0.50    0.00  completed
----------------------------------------------
mean         1.00     0.92    0.67
score 87.5 / 100
```

> `citation_precision(report)`: share of published sentences that pass the lexical citation-support check.
> `source_recall(report, expected_docs)`: share of the expected documents supplied with each question that you cited.
> `fact_coverage(report, key_facts)`: share of key facts that appear in some sentence.
> `evaluate(questions_path, corpus_dir)` returns a `Scorecard`, and `format_scorecard` prints it with one final number out of 100.

## Why it matters · 为什么重要

只看 precision 很容易刷满：发布一句安全的话，每条引用就都是对的。只看 recall 和 coverage 也容易：把语料库里每个句子都抄下来。一份有用的报告需要三者兼备，这就是总分按 0.4、0.3 和 0.3 加权的原因。

这些指标问的是不同的问题。precision 检验已发布内容的支撑，recall 检验来源选取，fact coverage 检验有用的内容。把每个分量与加权总分一起报告，这样一处改进就无法掩盖别处的回归。

> Precision alone is easy to max out: publish one safe sentence and every citation is correct. Recall and coverage alone are easy too: copy every sentence in the corpus. A useful report needs all three, which is why the score weights them 0.4, 0.3 and 0.3.
> The metrics ask different questions. Precision tests published support, recall tests source selection, and fact coverage tests useful content. Report each component alongside the weighted score so one improvement cannot hide a regression elsewhere.

## Public fixtures make the baseline reproducible · 公开 fixture 让基线可复现

`heldout/questions.json` 包含六道签入的公开评估问题，每道都带预期文档和关键事实。文件夹名是历史遗留：这些问题对学习者可见，参考实现也是在它们可用的条件下开发的。secrets-proxy 演示正是问题 h4，所以这个分数不是盲测或未见过的评估。

在学习这些指标时，把这份文件和 `fixtures/questions.json` 都看一遍。比较改动时保持公开评估输入不变，记录全部三个指标，并把改进当作在这些样例上的回归证据。反复针对它们调优并不能确立泛化。

参考基线在这六道公开 fixture 上得 87.5 / 100。每个已发布句子都通过了词面 precision 检查，但有几道问题漏掉了预期事实。这个分数不能确立在任意语料库或模型生成的散文上的表现。

```figure
pj-rra-scorecard
```

> `heldout/questions.json` contains six checked-in public evaluation questions, each with expected documents and key facts. The folder name is historical: these questions are visible to learners and the reference implementation was developed with them available. The secrets-proxy demo is exactly question h4, so the score is not a blind or unseen evaluation.
> Inspect both this file and `fixtures/questions.json` while learning the metrics. Keep the public evaluation inputs fixed when comparing changes, record all three metrics, and treat improvements as regression evidence on these examples. Repeatedly tuning against them does not establish generalization.
> The reference baseline scores 87.5 / 100 on these six public fixtures. Every published sentence passes the lexical precision check, but several questions miss expected facts. This score does not establish performance on arbitrary corpora or model-written prose.

## Follow the mechanism · 理解机制

宏平均（macro average）给每个问题相等的权重。微平均（micro average）则偏向句子更多的问题。本项目使用前者，这样一份又长又简单的报告就不能淹没一道又短又难的问题。比较改动时保持评估问题固定不变。

> A macro average gives each question equal weight. A micro average would instead favor questions with more sentences. This project uses the former so a long easy report cannot drown out a short difficult question. Keep the evaluation questions fixed while comparing changes.

## Your task · 你的任务

```python
class Scorecard:
    def mean(self, metric) -> float: ...
    def score(self) -> float: ...
def citation_precision(report, threshold=0.8) -> float: ...
def source_recall(report, expected_docs) -> float: ...
def fact_coverage(report, key_facts) -> float: ...
def evaluate(questions_path, corpus_dir, model=None) -> Scorecard: ...
def format_scorecard(card) -> str: ...
```

## Run the tests · 运行测试

```bash
python3 scripts/project_test.py research-report-agent --stage 7 --path my-report-agent
python3 projects/research-report-agent/solution/run_report.py \
  --eval projects/research-report-agent/heldout/questions.json --code my-report-agent
```

测试要求 precision 至少 0.9，source recall 至少 0.6，fact coverage 至少 0.4，总分至少 70。

> The tests require precision of at least 0.9, source recall of at least 0.6, fact coverage of at least 0.4, and a score of at least 70.

## What you should see · 预期结果

第 7 阶段通过 8 个 Python 测试，且此前所有阶段仍然通过。参考基线在签入的公开 fixture 上打印出上面展示的记分卡：precision 1.00、source recall 0.92、fact coverage 0.67，总分 87.5 / 100。这些是实测的 fixture 结果，不是对其他输入的保证。

> Stage 7 passes 8 Python tests, and all preceding stages still pass. The reference baseline on the checked-in public fixtures prints the scorecard shown above: precision 1.00, source recall 0.92, fact coverage 0.67, and score 87.5 / 100. These are measured fixture results, not guarantees for other inputs.

## Check yourself · 自检

1. 为什么这里的 precision 阈值（0.8）比 critic 的阈值（0.6）更严？
2. 一次改动后你的分数涨了 5 分。在相信它之前，你会检查什么？
3. 一份只说 "Containers are containers [S1]." 的报告会把哪个指标刷满？

> 1. Why is the precision threshold here (0.8) stricter than the critic threshold (0.6)?
> 2. Your score went up 5 points after a change. What would you check before believing it?
> 3. Which metric would a report that only says "Containers are containers [S1]." max out?

## Going further · 进阶

- 在不降低 precision 的前提下提高公开 fixture 分数，并记录哪些样例改进了、哪些回归了。
- 增加一个给可读性打分的模型 judge，并让它与接地指标分开报告。
- 要衡量泛化，请另找人为一个新语料库单独准备私有问题和标签。在评估它们之前冻结你的实现和阈值，然后在你查阅或针对这些结果调优时予以披露。

> - Improve the public fixture score without lowering precision, and document which examples improved and which regressed.
> - Add a model judge that scores readability, and report it separately from the grounded metrics.
> - To measure generalization, have someone else prepare separate private questions and labels for a new corpus. Freeze your implementation and thresholds before evaluating them, then disclose when you review or tune against those results.

## Worked Orchard case · Orchard 实战案例

动手写代码之前，先复习 [Python 数据结构](https://docs.python.org/3/tutorial/datastructures.html)和[检索增强生成](../../../../../phases/11-llm-engineering/06-rag/docs/en.md)。先完成[阶段 6](../../06-publish-the-report/docs/en.md)。

签入的问题是公开的回归 fixture。把它们的成绩与一次独立准备的语料库评估分开保存。新的 Orchard 场景在不改动公开隔离问题的前提下测试一次政策更新。

```text
same question + before corpus -> 60-minute claim
same question + after corpus -> 15-minute claim
comparison question mismatch -> reject
```

> The checked-in questions are public regression fixtures. Keep their score separate from an independently prepared corpus evaluation. The new Orchard scenario tests a policy update without changing the public isolation questions.

## Build and inspect · 构建并检查

在调优检索之前先冻结你的评估问题。把分量指标和问题级失败与汇总结果一起保存。

在你的学习工作区（learner workspace）中实现该阶段。这些 CLI 辅助工具是给定的适配器，它们导入你的函数；它们不能替代参考实现。

```bash
python3 scripts/project_test.py research-report-agent --stage 7 --path learning-artifacts/research-report-agent
```

在各阶段累计通过之后，从仓库根目录用最初的示例输入运行你的工件（artifact）：

```bash
python3 projects/research-report-agent/solution/run_report.py "How long do Orchard guest tokens last?" --code learning-artifacts/research-report-agent --corpus projects/research-report-agent/examples/orchard/before --out orchard-before
python3 projects/research-report-agent/solution/run_report.py "How long do Orchard guest tokens last?" --code learning-artifacts/research-report-agent --corpus projects/research-report-agent/examples/orchard/after --compare orchard-before/report.json --out orchard-after
```

默认使用确定性规划和抽取式写作。`--model replay` 需要 `--cassette`。`--model live` 使用 `RRA_LLM_BASE_URL`、`RRA_LLM_MODEL` 和可选的 `RRA_LLM_API_KEY`，且仅用于规划。线上服务的行为需要用调用者自己的凭据单独运行一次。公开 fixture 分数不能衡量对未见数据的泛化。

> The default uses deterministic planning and extractive writing. --model replay needs --cassette. --model live uses RRA_LLM_BASE_URL, RRA_LLM_MODEL and optional RRA_LLM_API_KEY for planning only. Live service behavior requires a separate run with caller credentials. Public fixture scores do not measure unseen generalization.

## Investigate next · 下一步探究

什么样的证据才能支撑「该 agent 能泛化到已发布 fixture 之外」的论断？

> What would justify a claim that the agent generalizes beyond the published fixtures?
