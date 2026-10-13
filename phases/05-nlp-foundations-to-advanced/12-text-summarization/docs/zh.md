# Text Summarization · 文本摘要

> 抽取式系统告诉你文档说了什么。生成式系统告诉你作者想说什么。不同的任务，不同的坑。
> Extractive systems tell you what the document said. Abstractive systems tell you what the author meant. Different tasks, different pitfalls.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 02 (BoW + TF-IDF), Phase 5 · 11 (Machine Translation)
**Time:** ~75 minutes

## The Problem · 问题在哪

一篇 2,000 词的新闻稿进入你的信息流。你需要 120 词把它抓住。你可以从文章里挑出最重要的三句话（抽取式，extractive），也可以用自己的话把内容重写一遍（生成式，abstractive）。两者都叫摘要。它们是完全不同的问题。

抽取式摘要是一个排序问题。给每个句子打分，返回前 `k` 句。输出永远合乎语法，因为它是原封不动搬过来的。风险是漏掉分散在全文各处的内容。

生成式摘要是一个生成问题。Transformer 以输入为条件生成新文本。输出流畅、压缩度高，但可能幻觉出源文里没有的事实。风险是自信的编造。

本课把两者都造出来，连同各自特有的那种失败模式。

> A 2,000-word news article lands in your feed. You need 120 words that capture it. You can either pick the three most important sentences from the article (extractive) or rewrite the content in your own words (abstractive). Both are called summarization. They are completely different problems.
> Extractive summarization is a ranking problem. Score every sentence, return the top-`k`. The output is always grammatical because it is lifted verbatim. The risk is missing content that is distributed across the article. ... Abstractive summarization is a generation problem. A transformer produces new text conditioned on the input. The output is fluent and compressive but may hallucinate facts that were not in the source. The risk is confident fabrication. ... This lesson builds both, with the failure mode each one owns.

## The Concept · 概念

![抽取式 TextRank vs 生成式 Transformer](../assets/summarization.svg)

**抽取式。** 把文章看成一张图：节点是句子，边是相似度。在图上跑 PageRank（或类似算法），按句子与全图其他部分的连接程度打分。得分最高的句子组成摘要。公认实现是 **TextRank**（Mihalcea 和 Tarau，2004）。

**生成式。** 在「文档-摘要」配对数据上微调 Transformer 编码器-解码器（BART、T5、Pegasus）。推理时，模型读入文档，通过交叉注意力逐 token 生成摘要。Pegasus 尤其使用了「间隔句子」（gap-sentence）预训练目标，使它不用太多微调就擅长摘要。

评估用 **ROUGE**（Recall-Oriented Understudy for Gisting Evaluation）。ROUGE-1 和 ROUGE-2 度量一元和二元词重叠。ROUGE-L 度量最长公共子序列（LCS）。越高越好，但 40 ROUGE-L 算「好」，50 算「出色」。每篇论文都会报告全部三项。用 `rouge-score` 包。

```figure
summarize-collapse
```

> **Extractive.** Treat the article as a graph where nodes are sentences and edges are similarities. Run PageRank (or something like it) over the graph to score sentences by how connected they are to everything else. Highest-scoring sentences are the summary. The canonical implementation is **TextRank** (Mihalcea and Tarau, 2004).
> **Abstractive.** Fine-tune a transformer encoder-decoder (BART, T5, Pegasus) on document-summary pairs. At inference, the model reads the document and generates the summary token-by-token via cross-attention. ... Evaluation with **ROUGE** (Recall-Oriented Understudy for Gisting Evaluation). ROUGE-1 and ROUGE-2 score unigram and bigram overlap. ROUGE-L scores longest common subsequence. Higher is better but 40 ROUGE-L is "good" and 50 is "exceptional." Every paper reports all three. Use the `rouge-score` package.

## Build It · 动手造

### Step 1: TextRank (extractive) · TextRank（抽取式）

```python
import math
import re
from collections import Counter


def sentence_split(text):
    return re.split(r"(?<=[.!?])\s+", text.strip())


def similarity(s1, s2):
    w1 = Counter(s1.lower().split())
    w2 = Counter(s2.lower().split())
    intersection = sum((w1 & w2).values())
    denom = math.log(len(w1) + 1) + math.log(len(w2) + 1)
    if denom == 0:
        return 0.0
    return intersection / denom


def textrank(text, top_k=3, damping=0.85, iterations=50, epsilon=1e-4):
    sentences = sentence_split(text)
    n = len(sentences)
    if n <= top_k:
        return sentences

    sim = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                sim[i][j] = similarity(sentences[i], sentences[j])

    scores = [1.0] * n
    for _ in range(iterations):
        new_scores = [1 - damping] * n
        for i in range(n):
            total_out = sum(sim[i]) or 1e-9
            for j in range(n):
                if sim[i][j] > 0:
                    new_scores[j] += damping * sim[i][j] / total_out * scores[i]
        if max(abs(s - ns) for s, ns in zip(scores, new_scores)) < epsilon:
            scores = new_scores
            break
        scores = new_scores

    ranked = sorted(range(n), key=lambda k: scores[k], reverse=True)[:top_k]
    ranked.sort()
    return [sentences[i] for i in ranked]
```

两点值得点名。相似度函数用的是对数归一化的词重叠，这是 TextRank 原始论文的变体。TF-IDF 向量的余弦相似度也可以。阻尼系数 0.85 和迭代次数都是 PageRank 的默认值。

> Two things worth naming. The similarity function uses log-normalized word overlap, which is the original TextRank variant. Cosine of TF-IDF vectors works too. The damping factor 0.85 and iteration count are the PageRank defaults.

### Step 2: abstractive with BART · 用 BART 做生成式摘要

```python
from transformers import pipeline

summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

article = """(long news article text)"""

summary = summarizer(article, max_length=120, min_length=60, do_sample=False)
print(summary[0]["summary_text"])
```

BART-large-CNN 在 CNN/DailyMail 语料上微调过，开箱即产新闻风格摘要。其他领域（科研论文、对话、法律）请用对应的 Pegasus 检查点，或在你的目标数据上微调。

> BART-large-CNN is fine-tuned on the CNN/DailyMail corpus. It produces news-style summaries out of the box. For other domains (scientific papers, dialog, legal), use the corresponding Pegasus checkpoint or fine-tune on your target data.

### Step 3: ROUGE evaluation · ROUGE 评估

```python
from rouge_score import rouge_scorer

scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
scores = scorer.score(reference_summary, generated_summary)
print({k: round(v.fmeasure, 3) for k, v in scores.items()})
```

永远开启词干化（stemming）。不开的话，"running" 和 "run" 会被算成不同的词，ROUGE 会低估分数。

> Always use stemming. Without it, "running" and "run" count as different words and ROUGE undercounts.

### Beyond ROUGE (2026 summarization eval) · ROUGE 之外（2026 年的摘要评估）

ROUGE 已经主导摘要评估二十年，但在 2026 年，仅靠它已经不够。一项 NLG 论文的大规模元分析显示：

- **BERTScore**（上下文嵌入相似度）到 2023 年持续走强，如今多数摘要论文都会把它与 ROUGE 并列报告。
- **BARTScore** 把评估当作生成任务：按预训练 BART 在给定源文时给摘要分配的似然来打分。
- **MoverScore**（上下文嵌入上的 Earth Mover's Distance）在 2025 年的摘要基准上登顶，因为它比 ROUGE 更能捕捉语义重叠。
- **FactCC** 和**基于 QA 的忠实度**评估在 2021-2023 年常见，如今常被 **G-Eval** 取代（一条 GPT-4 提示链，用思维链推理给连贯性、一致性、流畅度、相关性打分）。
- **G-Eval** 及同类 LLM 裁判方法，在评分细则（rubric）设计得当时与人类判断的一致率约 80%。

生产建议：报告 ROUGE-L 做历史对比，BERTScore 度量语义重叠，G-Eval 度量连贯性与事实性。在 50-100 条人工标注摘要上校准。

> ROUGE has been the dominant summarization metric for twenty years and it is insufficient on its own in 2026. A large-scale meta-analysis of NLG papers showed: ... **MoverScore** (Earth Mover's Distance over contextual embeddings) reached the top spot in 2025 summarization benchmarks because it captures semantic overlap better than ROUGE. ... **G-Eval** and similar LLM-judge approaches match human judgment ~80% of the time when rubrics are well-designed. ... Production recommendation: report ROUGE-L for legacy comparison, BERTScore for semantic overlap, G-Eval for coherence and factuality. Calibrate against 50-100 human-labeled summaries.

### Step 4: the factuality problem · 事实性问题

生成式摘要容易幻觉。抽取式摘要的幻觉风险低得多，因为输出是从源文原样搬来的——不过，如果源句被断章取义、已经过时、或引用顺序错乱，它仍然会误导。这是生产系统在合规敏感内容上仍偏爱抽取式方法的最大单个原因。

需要点名的幻觉类型：

- **实体互换（Entity swap）。** 源文说 "John Smith"。摘要说 "John Brown"。
- **数字漂移（Number drift）。** 源文说 "25,000"。摘要说 "25 million"。
- **极性翻转（Polarity flip）。** 源文说 "rejected the offer"。摘要说 "accepted the offer"。
- **事实捏造（Fact invention）。** 源文没提 CEO。摘要说 CEO 批准了。

行得通的评估方法：

- **FactCC。** 在「源句与摘要句之间的蕴含关系」上训练的二元分类器。预测事实 / 非事实。
- **基于 QA 的事实性。** 向 QA 模型提那些答案就在源文里的问题。如果摘要支持不同的答案，就标记。
- **实体级 F1。** 对比源文与摘要中的命名实体。只出现在摘要里的实体是嫌疑对象。

对任何事实性重要的面向用户场景（新闻、医疗、法律、金融），抽取式是更安全的默认。生成式必须把事实性检查放进流程里。

> Abstractive summaries are prone to hallucination. Extractive summaries carry a much lower hallucination risk because the output is lifted verbatim from the source, though they can still mislead if source sentences are decontextualized, outdated, or quoted out of order. This is the single biggest reason production systems still prefer extractive methods for compliance-adjacent content. ... **Entity swap.** Source says "John Smith." Summary says "John Brown." ... For anything user-facing where factuality matters (news, medical, legal, financial), extractive is the safer default. Abstractive needs a factuality check in the loop.

## Use It · 实战用法

2026 年的技术栈：

| 使用场景 | 推荐 |
|---------|-------------|
| 新闻、3-5 句摘要、英语 | `facebook/bart-large-cnn` |
| 科研论文 | `google/pegasus-pubmed` 或调优过的 T5 |
| 多文档、长文 | 任意 32k+ 上下文的 LLM，用提示词 |
| 对话摘要 | `philschmid/bart-large-cnn-samsum` |
| 抽取式、构造上低幻觉风险 | TextRank 或 `sumy` 的 LSA / LexRank |

2026 年，当算力不是约束时，长上下文 LLM 常常打败专用模型。代价是成本与可复现性；专用模型的输出更一致。

> The 2026 stack: ... LLMs with long context often beat specialized models in 2026 when compute is not a constraint. The tradeoff is cost and reproducibility; specialized models give more consistent outputs.

## Ship It · 交付

保存为 `outputs/skill-summary-picker.md`：

```markdown
---
name: summary-picker
description: Pick extractive or abstractive, named library, factuality check.
version: 1.0.0
phase: 5
lesson: 12
tags: [nlp, summarization]
---

Given a task (document type, compliance requirement, length, compute budget), output:

1. Approach. Extractive or abstractive. Explain in one sentence why.
2. Starting model / library. Name it. `sumy.TextRankSummarizer`, `facebook/bart-large-cnn`, `google/pegasus-pubmed`, or an LLM prompt.
3. Evaluation plan. ROUGE-1, ROUGE-2, ROUGE-L (use rouge-score with stemming). Plus factuality check if abstractive.
4. One failure mode to probe. Entity swap is the most common in abstractive news summarization; flag samples where source entities do not appear in summary.

Refuse abstractive summarization for medical, legal, financial, or regulated content without a factuality gate. Flag input over the model's context window as needing chunked map-reduce summarization (not just truncation).
```

> Save as `outputs/skill-summary-picker.md`:

## Exercises · 练习

1. **简单。** 在 5 篇新闻文章上跑 TextRank。把前 3 句与参考摘要对比。度量 ROUGE-L。在 CNN/DailyMail 风格的文章上你应该看到 30-45 ROUGE-L。
2. **中等。** 实现实体级事实性检查：从源文与摘要中抽取命名实体（spaCy），计算源文实体在摘要中的召回率、摘要实体相对源文的精确率。高精确率 + 低召回 = 安全但简省；低精确率 = 出现了幻觉实体。
3. **困难。** 在 50 篇 CNN/DailyMail 文章上对比 BART-large-CNN 与一个 LLM（Claude 或 GPT-4）。报告 ROUGE-L、事实性（按实体 F1）和每条摘要的成本。记录各自在哪些地方赢。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Extractive（抽取式） | 挑句子 | 从源文原样返回句子。从不幻觉。 |
| Abstractive（生成式） | 重写 | 以源文为条件生成新文本。可能幻觉。 |
| ROUGE | 摘要指标 | 系统输出与参考之间的 n-gram / LCS 重叠。 |
| TextRank | 基于图的抽取式 | 在句子相似度图上跑 PageRank。 |
| Factuality（事实性） | 它对不对 | 摘要中的论断是否有源文支撑。 |
| Hallucination（幻觉） | 编造的内容 | 摘要中源文不支撑的内容。 |

## Further Reading · 延伸阅读

- [Mihalcea and Tarau (2004). TextRank: Bringing Order into Texts](https://aclanthology.org/W04-3252/) —— 抽取式的开山论文。
- [Lewis et al. (2019). BART: Denoising Sequence-to-Sequence Pre-training](https://arxiv.org/abs/1910.13461) —— BART 论文。
- [Zhang et al. (2019). PEGASUS: Pre-training with Extracted Gap-sentences](https://arxiv.org/abs/1912.08777) —— Pegasus 与间隔句子目标。
- [Lin (2004). ROUGE: A Package for Automatic Evaluation of Summaries](https://aclanthology.org/W04-1013/) —— ROUGE 论文。
- [Maynez et al. (2020). On Faithfulness and Factuality in Abstractive Summarization](https://arxiv.org/abs/2005.00661) —— 事实性全景那篇论文。
