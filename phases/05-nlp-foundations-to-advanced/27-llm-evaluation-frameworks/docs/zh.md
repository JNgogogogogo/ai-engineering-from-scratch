# LLM Evaluation — RAGAS, DeepEval, G-Eval · LLM 评估——RAGAS、DeepEval、G-Eval

> 精确匹配（exact match）和 F1 识别不了语义等价，人工评审又无法规模化。LLM 当裁判（LLM-as-judge）是生产环境的答案——前提是有足够的校准（calibration），让你敢信这个数字。
>
> Exact-match and F1 miss semantic equivalence. Human review does not scale. LLM-as-judge is the production answer — with enough calibration to trust the number.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 13 (Question Answering), Phase 5 · 14 (Information Retrieval)
**Time:** ~75 minutes

## The Problem · 问题在哪

你的 RAG 系统回答："June 29th, 2007."
标准答案是："June 29, 2007."
Exact Match 得 0 分，F1 大约 75%，人类会打 100%。

现在乘以 10,000 个测试用例。再乘以检索器、分块（chunking）、提示词或模型的每一次变更。你需要一个这样的评估器：懂语义、规模化之后依然便宜、不谎报回归（regression）、还能暴露正确的失败模式。

2026 年有三个框架主导这个问题。

- **RAGAS.** Retrieval-Augmented Generation ASsessment。四个 RAG 指标（忠实度 faithfulness、答案相关性 answer-relevance、上下文精度 context-precision、上下文召回 context-recall），后端是 NLI + LLM 裁判。有研究支撑、轻量。
- **DeepEval.** LLM 界的 pytest。G-Eval、任务完成度、幻觉、偏见指标。CI/CD 原生。
- **G-Eval.** 一种方法（也是 DeepEval 的一个指标）：LLM 裁判 + 思维链（chain-of-thought）+ 自定义标准 + 0-1 打分。

三者都依赖 LLM-as-judge。本课要建立的是对这种方法本身、以及围绕它的信任层的直觉。

> Your RAG system answers: "June 29th, 2007."
> The gold reference is: "June 29, 2007."
> Exact Match scores 0. F1 scores ~75%. A human would score 100%.
> Now multiply by 10,000 test cases. Multiply again by every change to the retriever, chunking, prompt, or model. You need an evaluator that understands meaning, runs cheaply at scale, does not lie about regressions, and surfaces the right failure modes.
> All three lean on LLM-as-judge. This lesson builds intuition for the method and the trust layer around it.

## The Concept · 概念

![四个评估维度，LLM-as-judge 架构](../assets/llm-evaluation.svg)

**LLM-as-judge。** 用一个按评分标准（rubric）给输出打分的 LLM，取代静态指标。给定 `(query, context, answer)`，提示一个裁判 LLM："按忠实度打 0-1 分。" 返回分数。

它为什么可行：LLM 用极低的成本逼近人类判断。GPT-4o-mini 打一个用例约 $0.003，1000 样本的回归评估跑下来不到 $5。

它为什么会悄悄失效：

1. **裁判偏见（judge bias）。** 裁判偏爱更长的答案、自家模型家族产出的答案、与提示风格匹配的答案。
2. **JSON 解析失败。** 坏 JSON → NaN 分数 → 被悄悄排除出聚合。RAGAS 用户都懂这种痛。用 try/except + 显式失败模式来把关。
3. **模型版本间的漂移。** 升级裁判等于改动了每一个指标。冻结裁判模型 + 版本。

**RAG 四指标。**

| 指标 | 回答的问题 | 后端 |
|--------|----------|---------|
| Faithfulness（忠实度） | 答案里的每条论断都来自检索到的上下文吗？ | 基于 NLI 的蕴含判断 |
| Answer relevance（答案相关性） | 答案回应了问题吗？ | 从答案生成假设性问题，再与真实问题比较 |
| Context precision（上下文精度） | 检索回来的 chunk 里，相关的占多少？ | LLM 裁判 |
| Context recall（上下文召回） | 检索把需要的东西都拿回来了吗？ | LLM 裁判对照标准答案 |

**G-Eval。** 定义一条自定义标准："答案有没有引用正确的来源？" 框架会自动把它展开成思维链评估步骤，然后打 0-1 分。适合 RAGAS 没覆盖的领域特定质量维度。

**校准（Calibration）。** 在拿到与人工标注的相关性之前，永远不要相信裁判的原始分数。跑 100 条人工标注样本，画出裁判分 vs 人工分，算 Spearman rho。如果 rho < 0.7，你的裁判评分标准需要返工。

```figure
n5-judge-gauge
```

> **LLM-as-judge.** Replace a static metric with an LLM that scores outputs given a rubric. ... **Judge bias.** Judges prefer longer answers, answers from their own model family, answers that match the prompt style. ... **Drift over model versions.** Upgrading the judge changes every metric. Freeze judge model + version. ... **Calibration.** Never trust the raw judge score until you have a correlation against human labels. Run 100 hand-labeled examples. Plot judge vs human. Compute Spearman rho. If rho < 0.7, your judge rubric needs work.

## Build It · 动手造

### Step 1: faithfulness with NLI (RAGAS-style) · 第 1 步：用 NLI 算忠实度（RAGAS 风格）

```python
from typing import Callable
from transformers import pipeline

nli = pipeline("text-classification",
               model="MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli",
               top_k=None)

# `llm` is any callable: prompt str -> generated str.
# Example: llm = lambda p: client.messages.create(model="claude-haiku-4-5", ...).content[0].text
LLM = Callable[[str], str]


def atomic_claims(answer: str, llm: LLM) -> list[str]:
    prompt = f"""Break this answer into simple factual claims (one per line):
{answer}
"""
    return llm(prompt).splitlines()


def faithfulness(answer: str, context: str, llm: LLM) -> float:
    claims = atomic_claims(answer, llm)
    if not claims:
        return 0.0
    supported = 0
    for claim in claims:
        result = nli({"text": context, "text_pair": claim})[0]
        entail = next((s for s in result if s["label"] == "entailment"), None)
        if entail and entail["score"] > 0.5:
            supported += 1
    return supported / len(claims)
```

把答案分解成原子论断（atomic claims），用 NLI 逐条对照检索到的上下文检查。忠实度 = 被支撑的比例。

> Decompose the answer into atomic claims. NLI-check each claim against the retrieved context. Faithfulness = fraction supported.

### Step 2: answer relevance · 第 2 步：答案相关性

```python
import numpy as np
from sentence_transformers import SentenceTransformer

# encoder: any model implementing .encode(texts, normalize_embeddings=True) -> ndarray
# e.g., encoder = SentenceTransformer("BAAI/bge-small-en-v1.5")

def answer_relevance(question: str, answer: str, encoder, llm: LLM, n: int = 3) -> float:
    prompt = f"Write {n} questions this answer could be the answer to:\n{answer}"
    generated = [line for line in llm(prompt).splitlines() if line.strip()][:n]
    if not generated:
        return 0.0
    q_emb = np.asarray(encoder.encode([question], normalize_embeddings=True)[0])
    g_embs = np.asarray(encoder.encode(generated, normalize_embeddings=True))
    sims = [float(q_emb @ g_emb) for g_emb in g_embs]
    return sum(sims) / len(sims)
```

如果答案隐含的问题和实际问的不是同一个，相关性就掉下去了。

> If the answer implies different questions than the one asked, relevance drops.

### Step 3: G-Eval custom metric · 第 3 步：G-Eval 自定义指标

```python
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams, LLMTestCase

metric = GEval(
    name="Correctness",
    criteria="The answer should be factually accurate and match the expected output.",
    evaluation_steps=[
        "Read the expected output.",
        "Read the actual output.",
        "List factual claims in the actual output.",
        "For each claim, mark supported or unsupported by the expected output.",
        "Return score = fraction supported.",
    ],
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
)

test = LLMTestCase(input="When was the first iPhone released?",
                   actual_output="June 29th, 2007.",
                   expected_output="June 29, 2007.")
metric.measure(test)
print(metric.score, metric.reason)
```

评估步骤就是评分标准（rubric）。显式写出的步骤比含糊的「打 0-1 分」提示更稳定。

> The evaluation steps are the rubric. Explicit steps are more stable than implicit "score 0-1" prompts.

### Step 4: CI gate · 第 4 步：CI 闸门

```python
import deepeval
from deepeval.metrics import FaithfulnessMetric, ContextualRelevancyMetric


def test_rag_system():
    cases = load_regression_cases()
    faith = FaithfulnessMetric(threshold=0.85)
    rel = ContextualRelevancyMetric(threshold=0.7)
    for case in cases:
        faith.measure(case)
        assert faith.score >= 0.85, f"faithfulness regression on {case.id}"
        rel.measure(case)
        assert rel.score >= 0.7, f"relevancy regression on {case.id}"
```

存成 pytest 文件。每个 PR 都跑。有回归就挡住合并。

> Ship as a pytest file. Run on every PR. Block merges on regressions.

### Step 5: toy eval from scratch · 第 5 步：从零造一个玩具评估器

见 `code/main.py`。只用标准库近似实现忠实度（答案论断与上下文的重叠）和相关性（答案词元与问题词元的重叠）。不是生产级，只是展示形状。

> See `code/main.py`. Stdlib-only approximations of faithfulness (overlap of answer claims with context) and relevance (overlap of answer tokens with question tokens). Not production. Shows the shape.

## Pitfalls · 常见的坑

- **不做校准。** 与人工标注相关性只有 0.3 的裁判就是噪声。上线前必须跑校准。
- **自我评估。** 用同一个 LLM 既生成又打分，分数会虚高 10-20%。裁判换一个模型家族。
- **成对评审中的位置偏见。** 裁判偏爱先出现的选项。永远随机化顺序，两个都跑。
- **只看聚合分数会藏住失败。** 平均 0.85 分常常藏着 5% 的灾难性失败。永远检查最差的分位。
- **金标数据集腐化。** 不做版本管理的评估集会随时间漂移，破坏纵向对比。每次变更都给数据集打标签。
- **LLM 成本。** 规模一大，裁判调用主导成本。用满足校准阈值的最便宜模型：GPT-4o-mini、Claude Haiku、Mistral-small。

> **No calibration.** A judge with 0.3 correlation to human labels is noise. Require a calibration run before shipping. ... **Self-evaluation.** Using the same LLM to generate and judge inflates scores by 10-20%. Use a different model family for the judge. ... **Raw aggregate hides failures.** Mean score 0.85 often hides 5% catastrophic failures. Always inspect the bottom quantile.

## Use It · 实战用法

2026 年的选型表：

| 用例 | 框架 |
|---------|-----------|
| RAG 质量监控 | RAGAS（4 指标） |
| CI/CD 回归闸门 | DeepEval + pytest |
| 自定义领域标准 | DeepEval 里的 G-Eval |
| 线上实时流量监控 | RAGAS 无参考（reference-free）模式 |
| 人工抽检 | LangSmith 或 Phoenix + 标注界面 |
| 红队 / 安全评估 | Promptfoo + DeepEval |

典型组合：RAGAS 做监控，DeepEval 做 CI，G-Eval 做新维度。三个都跑——它们的分歧本身就很有用。

> Typical stack: RAGAS for monitoring, DeepEval for CI, G-Eval for novel dimensions. Run all three; they disagree usefully.

## Ship It · 交付

保存为 `outputs/skill-eval-architect.md`：

```markdown
---
name: eval-architect
description: Design an LLM evaluation plan with calibrated judge and CI gates.
version: 1.0.0
phase: 5
lesson: 27
tags: [nlp, evaluation, rag]
---

Given a use case (RAG / agent / generative task), output:

1. Metrics. Faithfulness / relevance / context-precision / context-recall + any custom G-Eval metrics with criteria.
2. Judge model. Named model + version, rationale for cost vs accuracy.
3. Calibration. Hand-labeled set size, target Spearman rho vs human > 0.7.
4. Dataset versioning. Tag strategy, change log, stratification.
5. CI gate. Thresholds per metric, regression-window logic, bottom-quantile alert.

Refuse to rely on a judge untested against ≥50 human-labeled examples. Refuse self-evaluation (same model generates + judges). Refuse aggregate-only reporting without bottom-10% surfacing. Flag any pipeline where judge upgrade lands without parallel baseline eval.
```

> Save as `outputs/skill-eval-architect.md`:

## Exercises · 练习

1. **简单。** 在 10 个已知有幻觉的 RAG 样例上跑 RAGAS，验证忠实度指标能逐个抓住它们。
2. **中等。** 人工给 50 个 QA 答案按正确性打 0-1 分，再用 G-Eval 打分，算裁判与人类之间的 Spearman rho。
3. **困难。** 用 DeepEval 搭一个 pytest CI 闸门，故意把检索器改差，验证闸门会挂。再对最低的 10% 做阈值检查，实现最差分位告警。

> 1. **Easy.** Use RAGAS on 10 RAG examples with known hallucinations. Verify the faithfulness metric catches each one.
> 2. **Medium.** Hand-label 50 QA answers 0-1 for correctness. Score with G-Eval. Measure Spearman rho between judge and human.
> 3. **Hard.** Build a pytest CI gate with DeepEval. Intentionally regress the retriever. Verify the gate fails. Add bottom-quantile alerting via threshold check on the lowest 10%.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| LLM-as-judge | 用 LLM 打分 | 给裁判模型一个评分标准，让它把输出打成 0-1 分。 |
| RAGAS | RAG 指标库 | 开源评估框架，带 4 个无参考（reference-free）RAG 指标。 |
| Faithfulness | 答案有据可依吗？ | 答案论断中被检索上下文蕴含（entail）的比例。 |
| Context precision | 检索回来的 chunk 都相关吗？ | top-K chunk 里真正起作用的比例。 |
| Context recall | 检索找全了吗？ | 标准答案论断中被检索 chunk 支撑的比例。 |
| G-Eval | 自定义 LLM 裁判 | 评分标准 + 思维链评估步骤 + 0-1 分。 |
| Calibration | 信任但要先验证 | 裁判分与人工分之间的 Spearman 相关。 |

## Further Reading · 延伸阅读

- [Es et al. (2023). RAGAS: Automated Evaluation of Retrieval Augmented Generation](https://arxiv.org/abs/2309.15217) —— RAGAS 论文。
- [Liu et al. (2023). G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment](https://arxiv.org/abs/2303.16634) —— G-Eval 论文。
- [DeepEval docs](https://deepeval.com/docs/metrics-introduction) —— 开源生产级评估栈。
- [Zheng et al. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685) —— 偏见、校准与局限。
- [MLflow GenAI Scorer](https://mlflow.org/blog/third-party-scorers) —— 统一集成 RAGAS、DeepEval、Phoenix 的框架。
