# Named Entity Recognition · 命名实体识别（NER）

> Pull the names out. Sounds easy until you deal with ambiguous boundaries, nested entities, and domain jargon.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 02 (BoW + TF-IDF), Phase 5 · 03 (Word Embeddings)
**Time:** ~75 minutes

## The Problem · 问题在哪

"Apple sued Google over its iPhone search deal in the US."（苹果就其 iPhone 搜索交易起诉谷歌。）这句话里有五个实体：Apple（ORG，机构）、Google（ORG）、iPhone（PRODUCT，产品）、search deal（搜索交易，也许算）、US（GPE，地缘政治实体）。好的 NER 系统能把它们全部按正确类型抽出来；差的系统会漏掉 iPhone、把水果 Apple 和公司 Apple 混为一谈，还会把 "US" 标成人名（PERSON）。

NER 是所有结构化抽取流水线底层的那匹役马：简历解析、合规日志扫描、病历匿名化、搜索查询理解、聊天机器人回答的接地（grounding）、法律合同抽取。你几乎从来看不到它，却始终依赖它。

本课沿着经典路线（规则方法、HMM、CRF）一路走到现代路线（BiLSTM-CRF，再到 Transformer）。每一步都解决前一步的某个具体局限。这个模式本身就是本课。

> "Apple sued Google over its iPhone search deal in the US." Five entities: Apple (ORG), Google (ORG), iPhone (PRODUCT), search deal (maybe), US (GPE). A good NER system extracts all of them with correct types. ... NER is the workhorse underneath every structured extraction pipeline. ... This lesson walks the classical path (rule-based, HMM, CRF) into the modern one (BiLSTM-CRF, then transformers). Each step solves a specific limitation of the one before it. The pattern is the lesson.

## The Concept · 概念

**BIO 标注**（或 BILOU）把实体抽取变成序列标注（sequence labeling）问题。给每个 token 打上 `B-TYPE`（实体开头）、`I-TYPE`（实体内部）或 `O`（任何实体之外）的标签。

```
Apple    B-ORG
sued     O
Google   B-ORG
over     O
its      O
iPhone   B-PRODUCT
search   O
deal     O
in       O
the      O
US       B-GPE
.        O
```

多 token 实体连成一串：`New B-GPE`、`York I-GPE`、`City I-GPE`。一个理解 BIO 的模型能抽取任意跨度（span）。

架构演进如下：

- **规则方法（Rule-based）。** 正则表达式 + 词典（gazetteer）查找。对已知实体精确率高，对新实体覆盖率为零。
- **HMM。** 隐马尔可夫模型（Hidden Markov Model）。token 在给定标签下的发射概率（emission probability），标签到标签的转移概率（transition probability）。用 Viterbi 解码。在标注数据上训练。
- **CRF。** 条件随机场（Conditional Random Field）。像 HMM 但属于判别式模型，所以可以混入任意特征（词形、大小写、相邻词）。到 2026 年，它在低资源部署场景里仍是经典的生产主力。
- **BiLSTM-CRF。** 用学出来的神经特征替代手工特征。LSTM 双向读句子，顶上的 CRF 层强制标签序列保持一致。
- **基于 Transformer。** 微调一个带 token 分类头的 BERT。精度最好，算力消耗也最大。

```figure
ner-bio-tagging
```

> **BIO tagging** (or BILOU) turns entity extraction into a sequence-labeling problem. Label each token with `B-TYPE` (beginning of entity), `I-TYPE` (inside entity), or `O` (outside any entity). ... Multi-token entities chain: `New B-GPE`, `York I-GPE`, `City I-GPE`. A model that understands BIO can extract arbitrary spans.
> **CRF.** Conditional Random Field. Like HMM but discriminative, so you can mix arbitrary features (word shape, capitalization, neighboring words). Still the classical production workhorse in 2026 for low-resource deployments.
> **BiLSTM-CRF.** Neural features instead of hand-crafted. LSTM reads the sentence both directions, CRF layer on top enforces consistent tag sequences.
> **Transformer-based.** Fine-tune BERT with a token-classification head. Best accuracy. Most compute.

## Build It · 动手造

### Step 1: BIO tagging helpers · BIO 标注辅助函数

```python
def spans_to_bio(tokens, spans):
    labels = ["O"] * len(tokens)
    for start, end, label in spans:
        labels[start] = f"B-{label}"
        for i in range(start + 1, end):
            labels[i] = f"I-{label}"
    return labels


def bio_to_spans(tokens, labels):
    spans = []
    current = None
    for i, label in enumerate(labels):
        if label.startswith("B-"):
            if current:
                spans.append(current)
            current = (i, i + 1, label[2:])
        elif label.startswith("I-") and current and current[2] == label[2:]:
            current = (current[0], i + 1, current[2])
        else:
            if current:
                spans.append(current)
                current = None
    if current:
        spans.append(current)
    return spans
```

```python
>>> tokens = ["Apple", "sued", "Google", "over", "iPhone", "sales", "."]
>>> labels = ["B-ORG", "O", "B-ORG", "O", "B-PRODUCT", "O", "O"]
>>> bio_to_spans(tokens, labels)
[(0, 1, 'ORG'), (2, 3, 'ORG'), (4, 5, 'PRODUCT')]
```

### Step 2: hand-crafted features · 手工特征

对经典（非神经）NER 来说，特征就是整场游戏。好用的特征有：

```python
def token_features(token, prev_token, next_token):
    return {
        "lower": token.lower(),
        "is_upper": token.isupper(),
        "is_title": token.istitle(),
        "has_digit": any(c.isdigit() for c in token),
        "suffix_3": token[-3:].lower(),
        "shape": word_shape(token),
        "prev_lower": prev_token.lower() if prev_token else "<BOS>",
        "next_lower": next_token.lower() if next_token else "<EOS>",
    }


def word_shape(word):
    out = []
    for c in word:
        if c.isupper():
            out.append("X")
        elif c.islower():
            out.append("x")
        elif c.isdigit():
            out.append("d")
        else:
            out.append(c)
    return "".join(out)
```

`word_shape("iPhone")` 返回 `xXxxxx`，`word_shape("USA-2024")` 返回 `XXX-dddd`。大小写模式对专有名词是强信号。

> For classical (non-neural) NER, features are the game. Useful ones: ... `word_shape("iPhone")` returns `xXxxxx`. `word_shape("USA-2024")` returns `XXX-dddd`. Capitalization patterns are high-signal for proper nouns.

### Step 3: a simple rule-based + dictionary baseline · 规则 + 词典基线

```python
ORG_GAZETTEER = {"Apple", "Google", "Microsoft", "OpenAI", "Meta", "Amazon", "Netflix"}
GPE_GAZETTEER = {"US", "USA", "UK", "India", "Germany", "France"}
PRODUCT_GAZETTEER = {"iPhone", "Android", "Windows", "ChatGPT", "Claude"}


def rule_based_ner(tokens):
    labels = []
    for token in tokens:
        if token in ORG_GAZETTEER:
            labels.append("B-ORG")
        elif token in GPE_GAZETTEER:
            labels.append("B-GPE")
        elif token in PRODUCT_GAZETTEER:
            labels.append("B-PRODUCT")
        else:
            labels.append("O")
    return labels
```

生产级词典（gazetteer）有数百万条从 Wikipedia 和 DBpedia 抓来的词条。覆盖率不错，但消歧（disambiguation）很糟糕——公司的 `Apple` 还是水果的 `Apple` 分不清。这就是统计模型最终胜出的原因。

> Production gazetteers have millions of entries scraped from Wikipedia and DBpedia. Coverage is good. Disambiguation (`Apple` the company vs the fruit) is terrible. That is why statistical models won.

### Step 4: the CRF step (sketch, not full impl) · CRF 这一步（草图，非完整实现）

在没有概率论基础的前提下，用 50 行从零写完整 CRF 并不会带来多少洞见。改用 `sklearn-crfsuite`：

```python
import sklearn_crfsuite

def to_features(tokens):
    out = []
    for i, tok in enumerate(tokens):
        prev = tokens[i - 1] if i > 0 else ""
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        out.append({
            "word.lower()": tok.lower(),
            "word.isupper()": tok.isupper(),
            "word.istitle()": tok.istitle(),
            "word.isdigit()": tok.isdigit(),
            "word.suffix3": tok[-3:].lower(),
            "word.shape": word_shape(tok),
            "prev.word.lower()": prev.lower(),
            "next.word.lower()": nxt.lower(),
            "BOS": i == 0,
            "EOS": i == len(tokens) - 1,
        })
    return out


crf = sklearn_crfsuite.CRF(algorithm="lbfgs", c1=0.1, c2=0.1, max_iterations=100, all_possible_transitions=True)
X_train = [to_features(s) for s in sentences_tokenized]
crf.fit(X_train, bio_labels_train)
```

`c1` 和 `c2` 是 L1 和 L2 正则化。`all_possible_transitions=True` 让模型自己学到非法序列（比如 `O` 后面跟 `I-ORG`）不太可能出现——这就是 CRF 在不让你手写约束的情况下保证 BIO 一致性的方式。

> Full CRF from scratch in 50 lines is not enlightening without the probability-theory foundations. Use `sklearn-crfsuite` instead: ... `c1` and `c2` are L1 and L2 regularization. `all_possible_transitions=True` lets the model learn illegal sequences (e.g., `I-ORG` after `O`) are unlikely, which is how a CRF enforces BIO consistency without you writing the constraint.

### Step 5: what a BiLSTM-CRF adds · BiLSTM-CRF 加了什么

特征变成学出来的。输入是 token 嵌入（embedding，GloVe 或 fastText）。LSTM 从左到右、从右到左各读一遍句子，拼接后的隐状态（hidden state）过一层 CRF 输出层。CRF 依旧负责标签序列的一致性；LSTM 用学到的特征取代了手工特征。

```python
import torch
import torch.nn as nn


class BiLSTM_CRF_Head(nn.Module):
    def __init__(self, vocab_size, embed_dim, hidden_dim, n_labels):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, embed_dim)
        self.lstm = nn.LSTM(embed_dim, hidden_dim, bidirectional=True, batch_first=True)
        self.fc = nn.Linear(hidden_dim * 2, n_labels)

    def forward(self, token_ids):
        e = self.embed(token_ids)
        h, _ = self.lstm(e)
        emissions = self.fc(h)
        return emissions
```

CRF 层用 `torchcrf.CRF`（pip install pytorch-crf）。相比手工特征的 CRF，提升是可测量的，但除非你有几万句标注数据，否则比你预期的要小。

> Features become learned. Inputs: token embeddings (GloVe or fastText). LSTM reads left-to-right and right-to-left. Concatenated hidden states go through a CRF output layer. The CRF still enforces tag-sequence consistency; the LSTM replaces hand-crafted features with learned ones. ... For the CRF layer, use `torchcrf.CRF` (pip install pytorch-crf). The gain over hand-crafted CRF is measurable but smaller than you expect unless you have tens of thousands of labeled sentences.

## Use It · 实战用法

spaCy 开箱即带生产级 NER。

```python
import spacy

nlp = spacy.load("en_core_web_sm")
doc = nlp("Apple sued Google over its iPhone search deal in the US.")
for ent in doc.ents:
    print(f"{ent.text:20s} {ent.label_}")
```

```
Apple                ORG
Google               ORG
iPhone               ORG
US                   GPE
```

注意 `iPhone` 被标成了 `ORG` 而不是 `PRODUCT`——spaCy 的小模型对产品类实体的覆盖较弱。大模型（`en_core_web_lg`）会更好，Transformer 模型（`en_core_web_trf`）还要更好。

用 Hugging Face 做基于 BERT 的 NER：

```python
from transformers import pipeline

ner = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")
print(ner("Apple sued Google over its iPhone in the US."))
```

```
[{'entity_group': 'ORG', 'word': 'Apple', ...},
 {'entity_group': 'ORG', 'word': 'Google', ...},
 {'entity_group': 'MISC', 'word': 'iPhone', ...},
 {'entity_group': 'LOC', 'word': 'US', ...}]
```

`aggregation_strategy="simple"` 会把连续的 B-X、I-X token 合并成一个跨度。不加这个参数，你拿到的是 token 级标签，得自己合并。

> spaCy ships production-grade NER out of the box. ... Notice `iPhone` labeled `ORG` rather than `PRODUCT` — spaCy's small model has weak product-entity coverage. The large model (`en_core_web_lg`) does better. The transformer model (`en_core_web_trf`) does better still. ... `aggregation_strategy="simple"` merges contiguous B-X, I-X tokens into a span. Without it, you get token-level labels and have to merge yourself.

### LLM-based NER (the 2026 option) · 基于 LLM 的 NER（2026 年的选择）

零样本（zero-shot）和少样本（few-shot）的 LLM NER 如今在许多领域已能和微调模型打平，而在标注数据稀缺时更是大幅领先。

- **零样本提示（zero-shot prompting）。** 给 LLM 一份实体类型清单和一个示例 schema，要求输出 JSON。开箱能用；在陌生领域精度中等。
- **ZeroTuneBio 式提示。** 把任务分解为候选抽取 → 含义解释 → 判断 → 复查。多阶段提示（而非一次性提示）在生物医学 NER 上显著提升精度。同样的模式也适用于法律、金融和科学领域。
- **结合 RAG 的动态提示。** 每次推理调用都从一个小型标注种子集中检索最相似的标注样本，即时构建少样本提示。在 2026 年的基准中，这让 GPT-4 生物医学 NER 的 F1 比静态提示高出 11-12%。
- **按实体类型分解。** 对长文档，一次性抽取所有实体类型的单次调用会随长度增长损失召回率。为每种实体类型各跑一遍抽取。推理成本更高，精度显著更高。这是临床笔记和法律合同场景的标准模式。

截至 2026 年的生产建议：在收集训练数据之前，先用 LLM 零样本跑一个基线。常常 F1 已经够好，根本不需要微调。

> Zero-shot and few-shot LLM NER is now competitive with fine-tuned models on many domains, and dramatically better when labeled data is scarce.
> Zero-shot prompting. Give the LLM a list of entity types and an example schema. Ask for JSON output. Works out of the box; accuracy is moderate on novel domains. ... Dynamic prompting with RAG. Retrieve the most similar labeled examples from a small annotated seed set for every inference call; build the few-shot prompt on the fly. ... Per-entity-type decomposition. For long documents, a single call that extracts all entity types at once loses recall as length grows. ... This is the standard pattern for clinical notes and legal contracts.
> Production recommendation as of 2026: start with an LLM zero-shot baseline before you collect training data. Often the F1 is good enough that you never need to fine-tune.

### Where classical NER still wins · 经典 NER 仍然占优的地方

即便 LLM 随手可用，以下情况经典 NER 依然占优：

- 延迟预算低于 50ms。
- 你有几千条标注样本，而且需要 98%+ 的 F1。
- 领域本体（ontology）稳定，预训练 CRF 或 BiLSTM 能顺利迁移。
- 监管约束要求本地部署（on-prem）的非生成式模型。

> Even with LLMs available, classical NER wins when: Latency budget is under 50ms. ... You have thousands of labeled examples and need 98%+ F1. ... The domain has a stable ontology where a pretrained CRF or BiLSTM transfers well. ... Regulatory constraints require an on-prem, non-generative model.

### Where it falls apart · 它在哪里翻车

- **领域漂移（domain shift）。** 在 CoNLL 上训练的 NER 拿到法律合同上，表现比词典还差。要在你自己的领域上微调。
- **嵌套实体（nested entities）。** "Bank of America Tower" 同时是一个 ORG 和一个 FACILITY。标准 BIO 无法表示重叠的跨度。你需要嵌套 NER（多轮扫描或基于跨度的模型）。
- **长实体。** "United States Federal Deposit Insurance Corporation."。token 级模型有时会把它拆开。用 `aggregation_strategy` 或后处理解决。
- **稀疏类型。** 医学 NER 的标签如 DRUG_BRAND、ADVERSE_EVENT、DOSE，通用模型完全没概念。那个领域的起点是 Scispacy 和 BioBERT。

> Domain shift. CoNLL-trained NER on legal contracts performs worse than a gazetteer. Fine-tune on your domain. ... Nested entities. "Bank of America Tower" is simultaneously an ORG and a FACILITY. Standard BIO cannot represent overlapping spans. You need nested NER (multi-pass or span-based models). ... Long entities. "United States Federal Deposit Insurance Corporation." Token-level models sometimes split this. ... Sparse types. Medical NER labels like DRUG_BRAND, ADVERSE_EVENT, DOSE. General-purpose models have no idea. Scispacy and BioBERT are the starting points there.

## Ship It · 交付

保存为 `outputs/skill-ner-picker.md`：

```markdown
---
name: ner-picker
description: Pick the right NER approach for a given extraction task.
version: 1.0.0
phase: 5
lesson: 06
tags: [nlp, ner, extraction]
---

Given a task description (domain, label set, language, latency, data volume), output:

1. Approach. Rule-based + gazetteer, CRF, BiLSTM-CRF, or transformer fine-tune.
2. Starting model. Name it (spaCy model ID, Hugging Face checkpoint ID, or "custom, trained from scratch").
3. Labeling strategy. BIO, BILOU, or span-based. Justify in one sentence.
4. Evaluation. Use `seqeval`. Always report entity-level F1 (not token-level).

Refuse to recommend fine-tuning a transformer for under 500 labeled examples unless the user already has a pretrained domain model. Flag nested entities as needing span-based or multi-pass models. Require a gazetteer audit if the user mentions "production scale" and labels are unchanged from CoNLL-2003.
```

> Save as `outputs/skill-ner-picker.md`.

## Exercises · 练习

1. **简单。** 实现 `bio_to_spans`（`spans_to_bio` 的逆函数），在 10 个句子上验证往返一致性。
2. **中等。** 用上面的 sklearn-crfsuite CRF 在 CoNLL-2003 英语 NER 数据集上训练。用 `seqeval` 报告每个实体类型的 F1。典型结果：约 84 F1。
3. **困难。** 在一个领域专用 NER 数据集（医学、法律或金融）上微调 `distilbert-base-cased`，与 spaCy 小模型比较。记录数据泄漏检查，并写下让你意外的东西。

> **Easy.** Implement `bio_to_spans` (the inverse of `spans_to_bio`) and verify round-trip consistency on 10 sentences.
> **Medium.** Train the sklearn-crfsuite CRF above on the CoNLL-2003 English NER dataset. Report per-entity F1 using `seqeval`. Typical result: ~84 F1.
> **Hard.** Fine-tune `distilbert-base-cased` on a domain-specific NER dataset (medical, legal, or financial). Compare against the spaCy small model. Document data leakage checks and write up what surprised you.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| NER | 抽名字 | 给 token 跨度打上类型标签（PERSON、ORG、GPE、DATE……）。 |
| BIO | 标注方案 | `B-X` 开始，`I-X` 延续，`O` 在实体外。 |
| BILOU | 更细的 BIO | 增加 `L-X`（last，末位）、`U-X`（unit，单体），边界更干净。 |
| CRF | 结构化分类器 | 对标签之间的转移建模，而不只看发射。强制序列合法。 |
| Nested NER | 嵌套实体 | 一个跨度的子跨度是另一个实体。BIO 表达不了这种情况。 |
| Entity-level F1 | 正确的 NER 指标 | 预测跨度必须与真实跨度完全一致。token 级 F1 会高估精度。 |

## Further Reading · 延伸阅读

- [Lample et al. (2016). Neural Architectures for Named Entity Recognition](https://arxiv.org/abs/1603.01360) —— BiLSTM-CRF 论文。经典必读。
- [Devlin et al. (2018). BERT: Pre-training of Deep Bidirectional Transformers](https://arxiv.org/abs/1810.04805) —— 提出了后来成为标准的 token 分类模式。
- [spaCy linguistic features — named entities](https://spacy.io/usage/linguistic-features#named-entities) —— `Doc.ents` 与 `Span` 上所有属性的实用参考。
- [seqeval](https://github.com/chakki-works/seqeval) —— 正确的指标库。永远用它。
