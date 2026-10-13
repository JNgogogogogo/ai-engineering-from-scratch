# Multilingual NLP · 多语言 NLP（multilingual NLP）

> 一个模型，100 多种语言，其中大多数语言零训练数据。跨语言迁移（cross-lingual transfer）是 2020 年代的实用奇迹。
>
> One model, 100+ languages, zero training data for most of them. Cross-lingual transfer is the practical miracle of the 2020s.

**类型:** Learn（学习）
**语言:** Python
**前置课程:** Phase 5 · 04（GloVe、FastText、子词）、Phase 5 · 11（机器翻译）
**时间:** ~45 分钟

## The Problem · 问题

英语有数十亿条标注样本。乌尔都语有几千条。迈蒂利语（Maithili）几乎没有。任何一个面向全球用户的实际 NLP 系统，都必须在缺乏任务专属训练数据的长尾语言上工作。

多语言模型的解法是在许多语言上同时训练一个模型。共享表示让模型把从高资源语言学到的技能迁移到低资源语言。在英语情感分析上微调模型，开箱就能在乌尔都语上给出出奇好的情感预测。这就是零样本跨语言迁移（zero-shot cross-lingual transfer），它改变了 NLP 面向世界交付的方式。

本课讲清楚这些权衡、那几个经典模型，以及让多语言新手团队栽跟头的那个决策：为迁移挑选源语言。

> English has billions of labeled examples. Urdu has thousands. Maithili has almost none. Any practical NLP system that serves a global audience has to work on the long tail of languages where task-specific training data does not exist.
> Multilingual models solve this by training one model on many languages simultaneously. ... That is zero-shot cross-lingual transfer, and it has reshaped how NLP ships to the world.
> This lesson names the tradeoffs, the canonical models, and the one decision that trips up teams new to multilingual work: picking a source language for transfer.

## The Concept · 概念

![通过共享多语言嵌入空间实现跨语言迁移](../assets/multilingual.svg)

**共享词表。** 多语言模型使用一个在所有目标语言文本上训练的 SentencePiece 或 WordPiece 分词器。词表是共享的：同一个子词（subword）单元在相关语言里表示同一个语素（morpheme）。英语和意大利语里的 `anti-` 拿到同一个 token。

**共享表示。** 一个在多种语言上以掩码语言建模（masked language modeling）预训练的 transformer 会学到：不同语言里语义相似的句子产生相似的隐藏状态。mBERT、XLM-R、NLLB 都表现出这一点。英语 "cat" 的向量与法语 "chat"、西班牙语 "gato" 聚在一起，整句向量也一样。

**零样本迁移。** 在一种语言（通常是英语）的标注数据上微调模型。推理时在模型支持的任何其他语言上直接运行。不需要目标语言的标注。对类型学上相近的语言效果强，对差异大的语言弱一些。

**少样本微调（few-shot fine-tuning）。** 给目标语言加 100-500 条标注样本。分类任务的准确率会跳到英语基线的 95-98%。这是多语言 NLP 里性价比最高的单一杠杆。

> **Shared vocabulary.** Multilingual models use a SentencePiece or WordPiece tokenizer trained on text from all target languages. ...
> **Shared representation.** A transformer pretrained on masked language modeling across many languages learns that semantically similar sentences in different languages produce similar hidden states. ...
> **Zero-shot transfer.** Fine-tune the model on labeled data in one language (usually English). ... No target-language labels needed.
> **Few-shot fine-tuning.** Add 100-500 labeled examples in the target language. Accuracy jumps to 95-98% of the English baseline on classification tasks. This is the single most cost-effective lever in multilingual NLP.

## The models · 模型

| 模型 | 年份 | 覆盖 | 备注 |
|-------|------|----------|-------|
| mBERT | 2018 | 104 种语言 | 在维基百科上训练。第一个实用的多语言 LM。低资源语言上偏弱。|
| XLM-R | 2019 | 100 种语言 | 在 CommonCrawl 上训练（比维基百科大得多）。跨语言基线的设定者。Base 270M，Large 550M。|
| XLM-V | 2023 | 100 种语言 | XLM-R 但词表为 100 万 token（对比 25 万）。低资源语言上更好。|
| mT5 | 2020 | 101 种语言 | T5 架构的多语言生成。|
| NLLB-200 | 2022 | 200 种语言 | Meta 的翻译模型；包含 55 种低资源语言。|
| BLOOM | 2022 | 46 种语言 + 13 种编程语言 | 开放权重的 176B LLM，多语言训练。|
| Aya-23 | 2024 | 23 种语言 | Cohere 的多语言 LLM。阿拉伯语、印地语、斯瓦希里语上很强。|

按用例挑。分类任务用 XLM-R-base 当合理默认。生成任务看是翻译还是开放生成，选 mT5 或 NLLB。LLM 式的工作配 Aya-23 或 Claude，并使用显式的多语言提示。

> Pick by use case. Classification works well with XLM-R-base as the sane default. Generation tasks call for mT5 or NLLB depending on translation vs open generation. LLM-style work pairs with Aya-23 or Claude using explicit multilingual prompting.

## The source-language decision (2026 research) · 源语言决策（2026 研究）

大多数团队默认用英语做微调的源语言。2026 年的近期研究表明这经常是错的。

语言相似度对迁移质量的预测力强于原始语料规模。对斯拉夫语目标，德语或俄语常常胜过英语。对印度语系目标，印地语常常胜过英语。**qWALS** 相似度指标（2026，基于 World Atlas of Language Structures 特征）把这一点量化了。**LANGRANK**（Lin et al., ACL 2019）是另一个更早的独立方法，它从语言学相似度、语料规模和谱系亲缘的组合出发给候选源语言排序。

实用规则：如果你的目标语言有一个类型学上接近的高资源亲属语言，先试在那个语言上微调，再与英语微调比较。

```figure
n5-crosslingual-bridge
```

> Most teams default to English as the fine-tuning source. Recent research (2026) shows this is often wrong.
> Language similarity predicts transfer quality better than raw corpus size. ... Practical rule: if your target language has a typologically close high-resource relative, try fine-tuning on that one first, then compare to English fine-tune.

## Build It · 动手造

### Step 1: zero-shot cross-lingual classification · 第 1 步：零样本跨语言分类

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

tok = AutoTokenizer.from_pretrained("joeddav/xlm-roberta-large-xnli")
model = AutoModelForSequenceClassification.from_pretrained("joeddav/xlm-roberta-large-xnli")


def classify(text, candidate_labels, hypothesis_template="This text is about {}."):
    scores = {}
    for label in candidate_labels:
        hypothesis = hypothesis_template.format(label)
        inputs = tok(text, hypothesis, return_tensors="pt", truncation=True)
        with torch.no_grad():
            logits = model(**inputs).logits[0]
        entail_score = torch.softmax(logits, dim=-1)[2].item()
        scores[label] = entail_score
    return dict(sorted(scores.items(), key=lambda x: -x[1]))


print(classify("I love this product!", ["positive", "negative", "neutral"]))
print(classify("मुझे यह उत्पाद पसंद है!", ["positive", "negative", "neutral"]))
print(classify("J'adore ce produit !", ["positive", "negative", "neutral"]))
```

一个模型，三种语言，同一套 API。在 NLI 数据上训练过的 XLM-R 通过蕴含把戏（entailment trick）能很好地迁移到分类任务。

> One model, three languages, same API. XLM-R trained on NLI data transfers well to classification via the entailment trick.

### Step 2: multilingual embedding space · 第 2 步：多语言嵌入空间

```python
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

pairs = [
    ("The cat is sleeping.", "Le chat dort."),
    ("The cat is sleeping.", "El gato está durmiendo."),
    ("The cat is sleeping.", "Die Katze schläft."),
    ("The cat is sleeping.", "The dog is barking."),
]

for eng, other in pairs:
    emb_eng = model.encode([eng], normalize_embeddings=True)[0]
    emb_other = model.encode([other], normalize_embeddings=True)[0]
    sim = float(np.dot(emb_eng, emb_other))
    print(f"  {eng!r} <-> {other!r}: cos={sim:.3f}")
```

翻译对在嵌入空间里落得很近。另一个英语句子则落得更远。这就是跨语言检索、聚类和相似度能够成立的原因。

> Translations land close in embedding space. A different English sentence lands further. This is what makes cross-lingual retrieval, clustering, and similarity work.

### Step 3: few-shot fine-tuning strategy · 第 3 步：少样本微调策略

```python
from transformers import TrainingArguments, Trainer
from datasets import Dataset


def few_shot_finetune(base_model, base_tokenizer, examples):
    ds = Dataset.from_list(examples)

    def tokenize_fn(ex):
        out = base_tokenizer(ex["text"], truncation=True, max_length=128)
        out["labels"] = ex["label"]
        return out

    ds = ds.map(tokenize_fn)
    args = TrainingArguments(
        output_dir="out",
        per_device_train_batch_size=8,
        num_train_epochs=5,
        learning_rate=2e-5,
        save_strategy="no",
    )
    trainer = Trainer(model=base_model, args=args, train_dataset=ds)
    trainer.train()
    return base_model
```

对 100-500 条目标语言样本，`num_train_epochs=5` 和 `learning_rate=2e-5` 是安全默认值。更高的学习率会让多语言对齐（alignment）崩塌，你会得到一个只剩英语的模型。

> For 100-500 target-language examples, `num_train_epochs=5` and `learning_rate=2e-5` are the safe defaults. Higher learning rates cause the multilingual alignment to collapse and you get an English-only model.

## Evaluation that actually works · 真正有效的评估

- **在留出集上按语言报告准确率。** 不要只看聚合值。聚合会藏住长尾。
- **与单语基线对比。** 对数据够多的语言，从头训练的单语模型有时会击败多语言模型。测了才知道。
- **实体级测试。** 用目标语言的命名实体测。多语言模型在远离拉丁字母的文字系统上分词往往很弱。
- **跨语言一致性。** 同一个意思的两种语言应该产生同一个预测。把差距量出来。

> **Per-language accuracy on held-out sets.** Not aggregated. The aggregate hides the long tail.
> **Benchmark against monolingual baseline.** ... **Entity-level tests.** ... **Cross-lingual consistency.** Same meaning in two languages should produce the same prediction. Measure the gap.

## Use It · 实战用法

2026 年的技术栈：

| 任务 | 推荐 |
|-----|-------------|
| 100 种语言的分类 | 微调过的 XLM-R-base（约 270M）|
| 零样本文本分类 | `joeddav/xlm-roberta-large-xnli` |
| 多语言句子向量 | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| 200 种语言的翻译 | `facebook/nllb-200-distilled-600M`（见第 11 课）|
| 生成式多语言 | Claude、GPT-4、Aya-23、mT5-XXL |
| 低资源语言 NLP | XLM-V，或在相近高资源语言上做领域微调 |

如果性能重要，永远要为目标语言的微调留预算。零样本只是起点，不是最终答案。

> Always budget for fine-tuning in the target language if performance matters. Zero-shot is a starting point, not a final answer.

### The tokenization tax (what goes wrong for low-resource languages) · 分词税（低资源语言到底哪里出问题）

多语言模型在所有语言间共享一个分词器。这个词表是在英语、法语、西班牙语、中文、德语占主导的语料上训练的。对主导集合之外的任何语言，三重税会悄悄叠加：

- **生育率税（fertility tax）。** 低资源语言的文本每个词切出的 token 远多于英语。一句印地语可能需要同等英语句子 3-5 倍的 token。这 3-5 倍会吃掉你的上下文窗口、训练效率和延迟。
- **变体恢复税（variant recovery tax）。** 每个错拼、变音符差异、Unicode 规范化不匹配或大小写变化，都会在嵌入空间里变成一段冷启动的无关序列。母语者视为理所当然的正字法对应关系，模型学不到。
- **容量外溢税（capacity spillover tax）。** 前两项税消耗上下文位置、层深度和嵌入维度。留给真正推理的容量，系统性地小于高资源语言从同一个模型里拿到的。

实际症状是：你的模型在印地语上正常训练，loss 曲线看着没问题，评估困惑度也合理，生产输出却有微妙的错误。句中形态学崩塌。罕见的屈折变化再也无法恢复。**分词器坏了，靠堆数据是救不回来的。**

缓解：选一个对你目标语言覆盖良好的分词器（XLM-V 的 100 万 token 词表就是直接解法）；训练前先在留出的目标文本上核查分词生育率；对真正的长尾文字使用字节级兜底（SentencePiece 的 `byte_fallback=True`、GPT-2 式字节级 BPE），保证任何输入都不会 OOV。

> For any language outside the dominant set, three taxes compound silently:
> **Fertility tax.** ... That 3-5x eats your context window, training efficiency, and latency.
> **Variant recovery tax.** ... **Capacity spillover tax.** ...
> The practical symptom: your model trains normally on Hindi, the loss curve looks right, eval perplexity looks reasonable, and production outputs are subtly wrong. ... **You cannot data-scale your way out of a broken tokenizer.**

## Ship It · 交付

保存为 `outputs/skill-multilingual-picker.md`：

```markdown
---
name: multilingual-picker
description: Pick source language, target model, and evaluation plan for a multilingual NLP task.
version: 1.0.0
phase: 5
lesson: 18
tags: [nlp, multilingual, cross-lingual]
---

Given requirements (target languages, task type, available labeled data per language), output:

1. Source language for fine-tuning. Default English; check LANGRANK or qWALS if target language has a typologically close high-resource language.
2. Base model. XLM-R (classification), mT5 (generation), NLLB (translation), Aya-23 (generative LLM).
3. Few-shot budget. Start with 100-500 target-language examples if available. Zero-shot only if labeling is infeasible.
4. Evaluation plan. Per-language accuracy (not aggregate), cross-lingual consistency, entity-level F1 on non-Latin scripts.

Refuse to ship a multilingual model without per-language evaluation — aggregate metrics hide long-tail failures. Flag scripts with low tokenization coverage (Amharic, Tigrinya, many African languages) as needing a model with byte-fallback (SentencePiece with byte_fallback=True, or byte-level tokenizer like GPT-2).
```

> Save as `outputs/skill-multilingual-picker.md`.

## Exercises · 练习

1. **简单。** 在英语、法语、印地语、阿拉伯语上各跑 10 句零样本分类管线，分别报告准确率。你应该会看到法语很强、印地语还行、阿拉伯语不稳定。
2. **中等。** 用 `paraphrase-multilingual-MiniLM-L12-v2` 在一个小型混合语言语料上搭一个跨语言检索器：用英语查询，检索任何语言的文档。测 recall@5。
3. **困难。** 为一个印地语分类任务比较英语源与印地语源的微调：两种设定下都用 500 条目标语言样本做少样本微调。报告哪个源带来更好的印地语准确率、差距多大。这是 LANGRANK 论点的微缩版。

## Key Terms · 关键术语

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Multilingual model | 一个模型，多种语言 | 词表和参数在语言间共享。|
| Cross-lingual transfer | 在一种语言上训练，在另一种上运行 | 在源语言上微调，在目标语言上评估，不需要目标语言标注。|
| Zero-shot | 没有目标语言标注 | 不在目标语言上微调就直接迁移。|
| Few-shot | 少量目标语言标注 | 用 100-500 条目标语言样本做微调。|
| mBERT | 第一个多语言 LM | 在维基百科上预训练的 104 语言 BERT。|
| XLM-R | 标准跨语言基线 | 在 CommonCrawl 上预训练的 100 语言 RoBERTa。|
| NLLB | Meta 的 200 语言机器翻译 | No Language Left Behind。包含 55 种低资源语言。|

## Further Reading · 延伸阅读

- [Conneau et al. (2019). Unsupervised Cross-lingual Representation Learning at Scale](https://arxiv.org/abs/1911.02116) —— XLM-R 论文。
- [Pires, Schlinger, Garrette (2019). How Multilingual is Multilingual BERT?](https://arxiv.org/abs/1906.01502) —— 开创跨语言迁移这条研究线的分析论文。
- [Costa-jussà et al. (2022). No Language Left Behind](https://arxiv.org/abs/2207.04672) —— NLLB-200 论文。
- [Üstün et al. (2024). Aya Model: An Instruction Finetuned Open-Access Multilingual Language Model](https://arxiv.org/abs/2402.07827) —— Aya，Cohere 的多语言 LLM。
- [Language Similarity Predicts Cross-Lingual Transfer Learning Performance (2026)](https://www.mdpi.com/2504-4990/8/3/65) —— qWALS / LANGRANK 源语言论文。
