# Natural Language Inference — Textual Entailment · 自然语言推理——文本蕴含

> 「t 蕴含 h」的意思是：一个人类读者读到 t，会得出「h 为真」的结论。NLI（自然语言推理）的任务是预测蕴含 / 矛盾 / 中立三分类。表面上无聊，生产中却是承重墙。
>
> "t entails h" means a human reading t would conclude h is true. NLI is the task of predicting entailment / contradiction / neutral. Boring on the surface, load-bearing in production.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 5 · 05 (Sentiment Analysis), Phase 5 · 13 (Question Answering)
**Time:** ~60 minutes

## The Problem · 问题在哪

你写了一个摘要器，它产出了一份摘要。你怎么知道摘要里没有幻觉（hallucination）？

你写了一个聊天机器人，它回答了「是」。你怎么知道这个答案确实被检索到的段落支撑？

你要把 10,000 篇新闻文章按主题分类，但手上没有任何训练标注。能复用现成模型吗？

这三个问题都归结为自然语言推理（Natural Language Inference, NLI）。NLI 问的是：给定前提（premise）`t` 和假设（hypothesis）`h`，`h` 是被 `t` 蕴含（entailment）、被矛盾（contradiction），还是中立（neutral，无关）？

- **幻觉检查：** `t` = 原始文档，`h` = 摘要中的论断。不是蕴含 = 幻觉。
- **有据问答（grounded QA）：** `t` = 检索到的段落，`h` = 生成的答案。不是蕴含 = 编造。
- **零样本分类（zero-shot classification）：** `t` = 文档，`h` = 用自然语言说出来的标签（「这篇文章是关于体育的」）。蕴含 = 预测出的标签。

一个任务，三种生产用途。这就是为什么每个 RAG 评估框架底层都内置了一个 NLI 模型。

> You built a summarizer. It produced a summary. How do you know the summary does not contain a hallucination?
> You built a chatbot. It answered "yes." How do you know the answer is supported by the retrieved passage?
> You need to classify 10,000 news articles by topic. You have no training labels. Can you reuse a model?
> All three problems reduce to Natural Language Inference. NLI asks: given a premise `t` and a hypothesis `h`, is `h` entailed by `t`, contradicted, or neutral (unrelated)?

## The Concept · 概念

![NLI：三分类——前提 vs 假设](../assets/nli.svg)

**三个标签。**

- **蕴含（Entailment）。** `t` → `h`。「The cat is on the mat」蕴含「There is a cat」。
- **矛盾（Contradiction）。** `t` → ¬`h`。「The cat is on the mat」与「There is no cat」矛盾。
- **中立（Neutral）。** 两个方向都推不出。「The cat is on the mat」对「The cat is hungry」是中立的。

**不是逻辑蕴含。** NLI 是*自然*语言推理——一个典型人类读者会推出的结论，而不是严格逻辑。「John walked his dog」在 NLI 里蕴含「John has a dog」，但严格的一阶逻辑只有在你把「拥有」公理化之后才会承认这条推理。

**数据集。**

- **SNLI**（2015）。57 万条人工标注句对，图像描述作前提。领域较窄。
- **MultiNLI**（2017）。跨 10 种体裁的 43.3 万句对。2026 年的标准训练语料。
- **ANLI**（2019）。对抗性 NLI。人类专门编写用来击溃现有模型的样本。更难。
- **DocNLI、ConTRoL**（2020–21）。文档级前提。考验多跳（multi-hop）和长程推理。

**架构。** 一个 Transformer 编码器（BERT、RoBERTa、DeBERTa）读入 `[CLS] premise [SEP] hypothesis [SEP]`。`[CLS]` 表示接入一个三分类 softmax。在 MNLI 上训练，在留出基准上评估，同分布（in-distribution）句对能拿到 90%+ 的准确率。

**借 NLI 做零样本。** 给定一篇文档和候选标签，把每个标签改写成假设（「This text is about sports」）。算出每个假设的蕴含概率，取最大值。这就是 Hugging Face `zero-shot-classification` pipeline 背后的机制。

```figure
nli-router
```

> **The three labels.** Entailment. `t` → `h`. "The cat is on the mat" entails "There is a cat."... NLI is *natural* language inference — what a typical human reader would infer, not strict logic.... A transformer encoder (BERT, RoBERTa, DeBERTa) reads `[CLS] premise [SEP] hypothesis [SEP]`. The `[CLS]` representation feeds a 3-way softmax. Train on MNLI, evaluate on held-out benchmarks, get 90%+ accuracy on in-distribution pairs.... Given a document and candidate labels, turn each label into a hypothesis ("This text is about sports"). Compute entailment probability for each. Pick the max. This is the mechanism behind Hugging Face's `zero-shot-classification` pipeline.

## Build It · 动手造

### Step 1: run a pretrained NLI model · 运行预训练 NLI 模型

```python
from transformers import pipeline

nli = pipeline("text-classification",
               model="facebook/bart-large-mnli",
               top_k=None)  # return all labels; replaces deprecated return_all_scores=True

premise = "The cat is sleeping on the couch."
hypothesis = "There is a cat in the room."

result = nli({"text": premise, "text_pair": hypothesis})[0]
print(result)
# [{'label': 'entailment', 'score': 0.97},
#  {'label': 'neutral', 'score': 0.02},
#  {'label': 'contradiction', 'score': 0.01}]
```

做生产级 NLI，`facebook/bart-large-mnli` 和 `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli` 是开源默认之选。DeBERTa-v3 霸榜。

> For production NLI, `facebook/bart-large-mnli` and `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli` are the open defaults. DeBERTa-v3 tops leaderboards.

### Step 2: zero-shot classification · 零样本分类

```python
zs = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

text = "The stock market rallied after the central bank cut interest rates."
labels = ["finance", "sports", "politics", "technology"]

result = zs(text, candidate_labels=labels)
print(result)
# {'labels': ['finance', 'politics', 'technology', 'sports'],
#  'scores': [0.92, 0.05, 0.02, 0.01]}
```

模板默认是 "This example is about {label}."，可以用 `hypothesis_template` 自定义。不需要训练数据，不需要微调，开箱即用。

> The template is "This example is about {label}." by default. Customize with `hypothesis_template`. No training data required. No fine-tuning. Works out of the box.

### Step 3: faithfulness check for RAG · RAG 忠实度检查

```python
def is_faithful(answer, context, threshold=0.5):
    result = nli({"text": context, "text_pair": answer})[0]
    entail = next(s for s in result if s["label"] == "entailment")
    return entail["score"] > threshold
```

这正是 RAGAS 忠实度（faithfulness）指标的核心：把生成的答案拆成原子论断（atomic claims），逐条对照检索到的上下文做 NLI，报告能被蕴含的比例。

> This is the core of RAGAS faithfulness. Split the generated answer into atomic claims. Check each claim against the retrieved context. Report the fraction that entail.

### Step 4: hand-rolled NLI classifier (conceptual) · 手写 NLI 分类器（概念版）

见 `code/main.py`：一个只用标准库的玩具实现——前提和假设通过词汇重叠（lexical overlap）+ 否定检测来比较。打不过 Transformer 模型，但它展示了任务的形状：两段文本进，三分类标签出，损失 = 在 `{entail, contradict, neutral}` 上的交叉熵。

> See `code/main.py` for a stdlib-only toy: premise and hypothesis are compared via lexical overlap + negation detection. Not competitive with transformer models — but it shows the shape of the task: two texts in, 3-way label out, loss = cross-entropy over `{entail, contradict, neutral}`.

## Pitfalls · 常见的坑

- **只看假设的捷径（hypothesis-only shortcuts）。** 模型仅凭假设就能在 SNLI 上拿到约 60% 的准确率，因为「not」「nobody」「never」与矛盾标签强相关。这是检测标签泄露的强基线。
- **词汇重叠启发式。** 「每个子序列都蕴含」这条启发式能通过 SNLI，却在 HANS/ANLI 上翻车。要用对抗性基准来测。
- **文档长度退化。** 句子级 NLI 模型在文档级前提上会掉 20+ F1。长上下文要用 DocNLI 训练的模型。
- **零样本模板敏感。** 「This example is about {label}」 vs 「{label}」 vs 「The topic is {label}」能让准确率波动 10+ 个点。要调模板。
- **领域不匹配。** MNLI 用通用英文训练。法律、医疗、科学文本需要领域专用的 NLI 模型（如 SciNLI、MedNLI）。

> Models can predict the label from the hypothesis alone at ~60% on SNLI because "not", "nobody", "never" correlate with contradiction.... The subsequence heuristic ("every subsequence is entailed") passes SNLI but fails HANS/ANLI. Use adversarial benchmarks.... Single-sentence NLI models drop 20+ F1 on document-length premises. Use DocNLI-trained models for long context.... "This example is about {label}" vs "{label}" vs "The topic is {label}" can swing accuracy by 10+ points. Tune the template.... MNLI trains on general English. Legal, medical, and scientific text need domain-specific NLI models (e.g., SciNLI, MedNLI).

## Use It · 实战用法

2026 年的选型：

| 使用场景 | 模型 |
|---------|-------|
| 通用 NLI | `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli` |
| 快速 / 边缘 | `cross-encoder/nli-deberta-v3-base` |
| 零样本分类（轻量） | `facebook/bart-large-mnli` |
| 文档级 NLI | `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli` |
| 多语言 | `MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli` |
| RAG 幻觉检测 | RAGAS / DeepEval 内置的 NLI 层 |

2026 年的元模式：NLI 是文本理解的「万能胶」。每当你需要问「A 支持 B 吗？」或「A 与 B 矛盾吗？」——先伸手拿 NLI，而不是再发一次 LLM 调用。

> The 2026 meta-pattern: NLI is the duct tape of text understanding. Whenever you need "does A support B?" or "does A contradict B?" — reach for NLI before you reach for another LLM call.

## Ship It · 交付

保存为 `outputs/skill-nli-picker.md`：

```markdown
---
name: nli-picker
description: Pick an NLI model, label template, and evaluation setup for a classification / faithfulness / zero-shot task.
version: 1.0.0
phase: 5
lesson: 21
tags: [nlp, nli, zero-shot]
---

Given a use case (faithfulness check, zero-shot classification, document-level inference), output:

1. Model. Named NLI checkpoint. Reason tied to domain, length, language.
2. Template (if zero-shot). Verbalization pattern. Example.
3. Threshold. Entailment cutoff for the decision rule. Reason based on calibration.
4. Evaluation. Accuracy on held-out labeled set, hypothesis-only baseline, adversarial subset.

Refuse to ship zero-shot classification without a 100-example labeled sanity check. Refuse to use a sentence-level NLI model on document-length premises. Flag any claim that NLI solves hallucination — it reduces it; it does not eliminate it.
```

> Save as `outputs/skill-nli-picker.md`.

## Exercises · 练习

1. **简单。** 用 `facebook/bart-large-mnli` 跑 20 条手工构造的（前提, 假设, 标签）三元组，覆盖全部三个类别。测准确率。再加上对抗性的「子序列启发式」陷阱（「I did not eat the cake」 vs 「I ate the cake」），看它会不会翻车。
2. **中等。** 在 100 条 AG News 标题上，把零样本模板 `"This text is about {label}"` 与 `"The topic is {label}"`、`"{label}"` 做对比。报告准确率波动幅度。
3. **困难。** 做一个 RAG 忠实度检查器：原子论断拆分 + 逐条 NLI。在 50 条带金标上下文的 RAG 生成答案上评估。对照人工标注，测假阳性率和假阴性率。

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|-----------------------|
| NLI | Natural Language Inference（自然语言推理） | 对「前提—假设」关系做三分类。 |
| RTE | Recognizing Textual Entailment（识别文本蕴含） | NLI 的旧名；同一个任务。 |
| Entailment（蕴含） | 「t 推出 h」 | 典型读者读到 t 会得出 h 为真。 |
| Contradiction（矛盾） | 「t 排除 h」 | 典型读者读到 t 会得出 h 为假。 |
| Neutral（中立） | 「悬而未决」 | 从 t 到 h 哪个方向都推不出。 |
| Zero-shot classification（零样本分类） | 把 NLI 当分类器用 | 把标签改写成假设，取蕴含概率最大者。 |
| Faithfulness（忠实度） | 「答案有依据吗？」 | 对（检索上下文, 生成答案）跑 NLI。 |

## Further Reading · 延伸阅读

- [Bowman et al. (2015). A large annotated corpus for learning natural language inference](https://arxiv.org/abs/1508.05326) —— SNLI。
- [Williams, Nangia, Bowman (2017). A Broad-Coverage Challenge Corpus for Sentence Understanding through Inference](https://arxiv.org/abs/1704.05426) —— MultiNLI。
- [Nie et al. (2019). Adversarial NLI](https://arxiv.org/abs/1910.14599) —— ANLI 基准。
- [Yin, Hay, Roth (2019). Benchmarking Zero-shot Text Classification](https://arxiv.org/abs/1909.00161) —— NLI 当分类器用。
- [He et al. (2021). DeBERTa: Decoding-enhanced BERT with Disentangled Attention](https://arxiv.org/abs/2006.03654) —— 2026 年 NLI 的主力模型。
