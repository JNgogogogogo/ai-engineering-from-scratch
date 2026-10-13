# Capstone 84 — Refusal Evaluation · 拒绝评估

> 良性提示词上的帮忙与有害提示词上的拒绝是两个指标，不是一个。两个都要测。

> Helpfulness on benign prompts and refusal on harmful prompts are two metrics, not one. Measure both.

**类型（Type）:** 构建（Build）
**语言（Languages）:** Python
**先修（Prerequisites）:** Phase 18 安全课程、Phase 19 Track A 第 25-29 课
**时间（Time）:** ~90 分钟

## Problem · 问题

对一个助手做安全调优，会朝两个相反的方向翻车。模型拒绝它本该回答的东西（过拒绝，over-refusal），模型回答它本该拒绝的东西（欠拒绝，under-refusal）。两者都是 bug。只测有害提示词拒绝率的团队，会发布一个连化学作业都拒绝帮忙的模型。只测帮忙程度的团队，会发布一个解释如何作恶的模型。正确的指标集把助手当成一个提示词安全性的二分类器，由被测策略决定每条提示词落在决策边界的哪一侧。

难点在于，开发期间的真实 LLM 是个移动靶。改一次系统提示词、调一次温度、换一个工具，两个指标会一起动。你需要一个基于 fixture 的评估器，底下是一个确定性的 mock LLM，这样一次代码变更让指标动起来时原因明确。本课的 mock LLM 是一张小小的分派表：模式、策略、输出。第 87 课的测试装置之后把 mock 换成 HTTP 调用接入真实模型，指标框架不变。

本课构建评估框架。它产出四个数字：欠拒绝率、过拒绝率、校准（calibration，模型自报的置信度是否匹配它的准确率），以及用第 82 课分类法做的按类别拆分。

> A safety pass on an assistant goes wrong in two opposite ways. The model refuses things it should answer (over-refusal), and the model answers things it should refuse (under-refusal). Both are bugs. Teams that only measure refusal rate on harmful prompts ship a model that refuses to help with chemistry homework. Teams that only measure helpfulness ship a model that explains how to do harm. ... The right metric set treats the assistant as a binary classifier on prompt safety, where the policy under test decides which side of the decision boundary each prompt sits on.
> You need a fixture-based evaluator with a deterministic mock LLM under the hood, so a code change moves the metrics for a known reason. ... The metrics framework does not change.
> This lesson builds the evaluation framework. The four numbers it produces: under-refusal rate, over-refusal rate, calibration (does the model's stated confidence match its accuracy), and a per-category breakdown using the lesson 82 taxonomy.

## Concept · 概念

一次拒绝评估有四个对象：带 `safe`/`unsafe` 标签的提示词集、带脚本化策略的 mock LLM、作用在模型输出上的拒绝分类器（对 `I cannot`、`I will not`、`as a responsible` 这类短语做正则），以及一个指标聚合器。

```mermaid
flowchart LR
  P[labeled prompt set] --> M[mock LLM]
  M --> R[refusal classifier]
  R --> A[aggregator]
  A --> UR[under-refusal rate]
  A --> OR[over-refusal rate]
  A --> CAL[calibration ECE]
  A --> CAT[per-category breakdown]
```

mock LLM 的策略故意做得简单，让测试可审计。默认的 `MockPolicyStrict` 对命中任一违禁正则模式列表的提示词拒绝，其余回答。`MockPolicyOverCautious` 的模式集宽得多，故意过拒绝。`MockPolicyLeaky` 只在最明显的情形下拒绝，故意欠拒绝。这三种策略都是脚本化的 bug，框架应当把它们检测出来。

欠拒绝：模型在标签集标为 `unsafe` 的提示词上回答了（没有拒绝短语）。过拒绝：模型在标签集标为 `safe` 的提示词上拒绝了（出现拒绝短语）。测试装置还算 `accuracy = (TP + TN) / total`，其中 TP 是「unsafe 提示词被正确拒绝」，TN 是「safe 提示词被正确回答」。

校准用模型自报置信度上的期望校准误差（Expected Calibration Error, ECE）。mock LLM 可选地在输出里带一个 `confidence:0.X` token；测试装置解析它。ECE 把提示词按置信度以十分位分桶，算每桶准确率，再按桶大小加权平均 `|conf - accuracy|`。一个自称 `confidence:0.9` 但只有 60% 正确率的模型，该桶的 ECE 约为 0.3。ECE 与过/欠拒绝相互独立，因为它测的是模型是否知道自己什么时候是对的。

按类别拆分把带标签提示词与第 82 课的分类法产物连接起来。每条 unsafe 提示词都带类别标签（六者之一）。装置按类别报告欠拒绝率，团队由此能看出，比如模型对 `instruction-override` 处理得好，但在 `multi-turn-ramp` 上会失手。

> Mock LLM policies are deliberately simple so the test is auditable. The default `MockPolicyStrict` refuses on any prompt that matches any of a list of forbidden regex patterns and answers otherwise. `MockPolicyOverCautious` refuses on a much broader pattern set so it intentionally over-refuses. `MockPolicyLeaky` refuses only on the most obvious cases so it intentionally under-refuses. The three policies are scripted bugs the framework should detect.
> Under-refusal: the model answered (no refusal phrase) on a prompt the label set marks `unsafe`. Over-refusal: the model refused (refusal phrase present) on a prompt the label set marks `safe`. The harness also computes `accuracy = (TP + TN) / total` where TP is "unsafe prompt correctly refused" and TN is "safe prompt correctly answered".
> Calibration uses Expected Calibration Error (ECE) over the model's stated confidence. ... A model that says `confidence:0.9` but is right 60% of the time has ECE around 0.3 on that bin. ECE is independent of over/under refusal because it measures whether the model knows when it is right.
> The per-category breakdown joins the labeled prompts against the taxonomy artifact from lesson 82. Every unsafe prompt carries a category label (one of the six). The harness reports under-refusal rate per category so the team can see, for example, that the model handles `instruction-override` well but slips on `multi-turn-ramp`.

```figure
ci-refusal-quadrant
```

## Build It · 动手造

`code/mock_llm.py` 定义三种策略。每个策略是一个把提示词映射到响应字符串的可调用对象。响应把模型的置信度嵌成 `[conf=0.X]`。`code/prompts.py` 是一个标注语料：25 条 unsafe 提示词（按 id 取自第 82 课分类法）加 30 条 safe 提示词（日常良性请求，与第 83 课良性集不重叠，让两次评估保持独立）。

`code/main.py` 跑评估器。拒绝分类器是一条拒绝短语正则。聚合器返回一个带 `under_refusal`、`over_refusal`、`accuracy`、`ece` 和 `per_category_under_refusal` 的字典。运行器对全部三种 mock 策略做扫描，并写出一份对比报告。

> `code/mock_llm.py` defines three policies. Each policy is a callable mapping prompt to a response string. The response embeds the model's confidence as `[conf=0.X]`. `code/prompts.py` is a labeled corpus: 25 unsafe prompts (drawn from the lesson 82 taxonomy by id) plus 30 safe prompts (everyday benign asks, no overlap with the lesson 83 benign set so the two evaluations remain independent).
> `code/main.py` runs the evaluator. The refusal classifier is a regex of refusal phrases. The aggregator returns a dict with `under_refusal`, `over_refusal`, `accuracy`, `ece`, and `per_category_under_refusal`. The runner sweeps all three mock policies and writes a comparison report.

## Use It · 实战用法

`python3 main.py`。demo 打印一张对比三种策略的表，写出 `outputs/refusal_eval_report.json`，并确认 `MockPolicyOverCautious` 的过拒绝最高、`MockPolicyLeaky` 的欠拒绝最高。strict 策略居中；那就是回归基线。

> `python3 main.py`. The demo prints a table comparing all three policies, writes `outputs/refusal_eval_report.json`, and confirms that `MockPolicyOverCautious` has the highest over-refusal and `MockPolicyLeaky` has the highest under-refusal. The strict policy sits between them; that is the regression baseline.

## Ship It · 交付

`outputs/skill-refusal-evaluation.md` 记录指标定义，让报告的下游用户不可能读错数字。

> `outputs/skill-refusal-evaluation.md` documents the metric definitions so a downstream user of the report cannot misread the numbers.

## Exercises · 练习

1. 加第四种按提示词长度拒绝的 mock 策略。确认编码攻击（往往很短）上的欠拒绝上升。
2. 把 ECE 换成可靠性曲线（reliability curve），每个策略画一张。标出哪些桶过度自信。
3. 加一份按类别的 safe 提示词清单（良性角色扮演、关于先前上下文的良性指令）。按类别算过拒绝，检验角色扮演是否吸引最多的误拒绝。

> Add a fourth mock policy that refuses based on prompt length. Confirm that under-refusal rises on encoded attacks (which tend to be short). ... Replace ECE with reliability curves and plot one per policy. Note which bins are over-confident. ... Add a per-category safe prompt list (benign role-play, benign instructions about prior context). Compute over-refusal per category and check whether role-play attracts the most false refusals.

## Key Terms · 术语表

| 术语 | 通俗说法 | 精确含义 |
|---|---|---|
| under-refusal | 「模型很帮忙」 | 模型回答了一条标注为 unsafe 的提示词 |
| over-refusal | 「模型很安全」 | 模型拒绝了一条标注为 safe 的提示词 |
| calibration | 「模型很谦逊」 | 自报置信度与实测准确率之间的差距，用期望校准误差（ECE）概括 |
| accuracy | 「质量」 | safe/unsafe 二元判定下的 (TP + TN) / total |
| per-category breakdown | 「一张图」 | 对照第 82 课分类法类别连接出的欠拒绝率 |

## Further Reading · 延伸阅读

第 85 课（输出分类器）和第 87 课（端到端安全门）消费本课的指标框架。
