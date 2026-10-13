# POS Tagging and Syntactic Parsing · 词性标注与句法分析

> Grammar was unfashionable for a while. Then every LLM pipeline needed to validate structured extraction, and it came back.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 01 (Text Processing), Phase 2 · 14 (Naive Bayes)
**Time:** ~45 minutes

## The Problem · 问题在哪

第 01 课说过：词形还原（lemmatization）需要词性标签。不知道 `running` 是动词，词形还原器就无法把它还原成 `run`；不知道 `better` 是形容词，就无法还原成 `good`。

那句话背后藏着一整个子领域。词性标注（POS tagging）给词分配语法类别；句法分析（syntactic parsing）还原句子的树结构：哪个词修饰哪个词，哪个动词支配哪些论元。经典 NLP 花了二十年打磨这两件事。然后深度学习把它们压缩成预训练 Transformer 之上的一个 token 分类任务，研究社区就翻篇了。

应用社区没有翻篇。每一条结构化抽取流水线，底层仍在用 POS 和依存树。LLM 生成的 JSON 要对照语法约束做校验。问答系统用依存分析来分解查询。机器翻译质量评估要检查句法树的对齐。

值得掌握。本课介绍标注集、基线方法，以及那个临界点——从哪里开始你该停止自己实现、直接调 spaCy。

> Lesson 01 promised that lemmatization needs a part-of-speech tag. Without knowing `running` is a verb, a lemmatizer cannot reduce it to `run`. Without knowing `better` is an adjective, it cannot reduce to `good`. ... Part-of-speech tagging assigns grammatical categories. Syntactic parsing recovers the sentence's tree structure: which word modifies which, which verb governs which arguments. ... Every structured-extraction pipeline still uses POS and dependency trees under the hood. ... This lesson introduces the tagsets, the baselines, and the point where you stop implementing from scratch and call spaCy.

## The Concept · 概念

**词性标注（POS tagging）** 给每个 token 打一个语法类别标签。**Penn Treebank（PTB）标注集**是英语的默认选择：36 个标签，细分到普通读者觉得琐碎的程度——`NN` 单数名词、`NNS` 复数名词、`NNP` 单数专有名词、`VBD` 动词过去式、`VBZ` 动词第三人称单数现在时，等等。**Universal Dependencies（UD）标注集**更粗（17 个标签）且与具体语言无关，成了跨语言工作的默认标准。

```
The/DET cats/NOUN were/AUX running/VERB at/ADP 3pm/NOUN ./PUNCT
```

**句法分析（syntactic parsing）** 产出一棵树。两大流派：

- **成分句法分析（constituency parsing）。** 名词短语、动词短语、介词短语彼此嵌套。输出是一棵非终结符类别（NP、VP、PP）的树，词是叶子。
- **依存句法分析（dependency parsing）。** 每个词有一个它所依赖的中心词（head），边上带一个语法关系标签。输出是一棵树，每条边都是一个（head，dependent，relation）三元组。

依存分析在 2010 年代胜出，因为它能干净地跨语言泛化，对自由语序语言尤其如此。

```
running is ROOT
cats is nsubj of running
were is aux of running
at is prep of running
3pm is pobj of at
```

```figure
pos-tagger
```

```figure
dependency-arcs
```

> **POS tagging** labels each token with a grammatical category. The **Penn Treebank (PTB)** tagset is the English default. 36 tags with distinctions the casual reader finds fussy ... The **Universal Dependencies (UD)** tagset is coarser (17 tags) and language-agnostic; it became the default for cross-lingual work.
> **Constituency parsing.** Noun phrases, verb phrases, prepositional phrases nest inside each other. ... **Dependency parsing.** Each word has a single head word it depends on, labeled with a grammatical relation. ... Dependency parsing won in the 2010s because it generalizes cleanly across languages, especially free-word-order ones.

## Build It · 动手造

### Step 1: most-frequent-tag baseline · 最高频标签基线

能用的最笨 POS 标注器：对每个词，预测它在训练数据里最常被标成的那个标签。

```python
from collections import Counter, defaultdict


def train_mft(train_examples):
    word_tag_counts = defaultdict(Counter)
    all_tags = Counter()
    for tokens, tags in train_examples:
        for token, tag in zip(tokens, tags):
            word_tag_counts[token.lower()][tag] += 1
            all_tags[tag] += 1
    word_best = {w: c.most_common(1)[0][0] for w, c in word_tag_counts.items()}
    default_tag = all_tags.most_common(1)[0][0]
    return word_best, default_tag


def predict_mft(tokens, word_best, default_tag):
    return [word_best.get(t.lower(), default_tag) for t in tokens]
```

在 Brown 语料库上，这个基线能到约 85% 的准确率。不算好，但它是任何正经模型都不该跌破的地板。

> The dumbest POS tagger that works. For each word, predict the tag it had most often in training. ... On the Brown corpus, this baseline hits ~85% accuracy. Not good, but the floor below which no serious model should fall.

### Step 2: bigram HMM tagger · bigram HMM 标注器

对序列的联合概率建模：

```
P(tags, words) = prod P(tag_i | tag_{i-1}) * P(word_i | tag_i)
```

两张表：转移概率（在前一个标签给定时当前标签的概率）、发射概率（在标签给定时词的概率）。两者都从计数里用拉普拉斯平滑（Laplace smoothing）估计。用 Viterbi（在标签格上做动态规划）解码。

```python
import math


def train_hmm(train_examples, alpha=0.01):
    transitions = defaultdict(Counter)
    emissions = defaultdict(Counter)
    tags = set()
    vocab = set()

    for tokens, ts in train_examples:
        prev = "<BOS>"
        for token, tag in zip(tokens, ts):
            transitions[prev][tag] += 1
            emissions[tag][token.lower()] += 1
            tags.add(tag)
            vocab.add(token.lower())
            prev = tag
        transitions[prev]["<EOS>"] += 1

    return transitions, emissions, tags, vocab


def log_prob(table, given, key, smooth_denom, alpha):
    return math.log((table[given].get(key, 0) + alpha) / smooth_denom)


def viterbi(tokens, transitions, emissions, tags, vocab, alpha=0.01):
    tags_list = list(tags)
    n = len(tokens)
    V = [[0.0] * len(tags_list) for _ in range(n)]
    back = [[0] * len(tags_list) for _ in range(n)]

    for j, tag in enumerate(tags_list):
        em_denom = sum(emissions[tag].values()) + alpha * (len(vocab) + 1)
        tr_denom = sum(transitions["<BOS>"].values()) + alpha * (len(tags_list) + 1)
        tr = log_prob(transitions, "<BOS>", tag, tr_denom, alpha)
        em = log_prob(emissions, tag, tokens[0].lower(), em_denom, alpha)
        V[0][j] = tr + em
        back[0][j] = 0

    for i in range(1, n):
        for j, tag in enumerate(tags_list):
            em_denom = sum(emissions[tag].values()) + alpha * (len(vocab) + 1)
            em = log_prob(emissions, tag, tokens[i].lower(), em_denom, alpha)
            best_prev = 0
            best_score = -1e30
            for k, prev_tag in enumerate(tags_list):
                tr_denom = sum(transitions[prev_tag].values()) + alpha * (len(tags_list) + 1)
                tr = log_prob(transitions, prev_tag, tag, tr_denom, alpha)
                score = V[i - 1][k] + tr + em
                if score > best_score:
                    best_score = score
                    best_prev = k
            V[i][j] = best_score
            back[i][j] = best_prev

    last_best = max(range(len(tags_list)), key=lambda j: V[n - 1][j])
    path = [last_best]
    for i in range(n - 1, 0, -1):
        path.append(back[i][path[-1]])
    return [tags_list[j] for j in reversed(path)]
```

Brown 语料库上的 bigram HMM 能到约 93% 的准确率。从 85% 到 93% 的跳跃主要来自转移概率——模型学到了 `DET NOUN` 很常见、`NOUN DET` 很罕见。

> Model the joint probability of the sequence ... Two tables: transition probabilities (tag given previous tag), emission probabilities (word given tag). Estimate both from counts with Laplace smoothing. Decode with Viterbi (dynamic programming over the tag lattice). ... Bigram HMM on Brown hits ~93% accuracy. The jump from 85% to 93% is mostly transition probabilities — the model learns `DET NOUN` is common and `NOUN DET` is rare.

### Step 3: why modern taggers beat this · 为什么现代标注器更强

转移概率 + 发射概率都是局部的。它们捕捉不到 "I bought a saw" 里的 `saw` 是名词而 "I saw the movie" 里是动词这件事。带任意特征（后缀、词形、前后词、词本身）的 CRF 能到约 97%。BiLSTM-CRF 或 Transformer 能到 98% 以上。

这个任务的天花板由标注员分歧决定。人工标注员在 Penn Treebank 上的一致率约 97%。超过 98% 的模型多半是在过拟合测试集。

> Transition + emission probabilities are local. They cannot capture that `saw` is a noun in "I bought a saw" but a verb in "I saw the movie." A CRF with arbitrary features (suffix, word shape, word before and after, word itself) hits ~97%. A BiLSTM-CRF or transformer hits ~98%+.
> The ceiling on this task is set by annotator disagreement. Human annotators agree about 97% of the time on Penn Treebank. Models past 98% are probably overfitting the test set.

### Step 4: dependency parsing sketch · 依存分析概貌

从零写完整的依存分析器超出本课范围；教科书式的标准讲解在 Jurafsky 和 Martin 的书里。要认识两大经典流派：

- **基于转移的（transition-based）** 分析器（arc-eager、arc-standard）：工作方式像移进-归约分析器，读入 token、压进栈，再执行建立依存弧的归约动作。贪心解码很快。经典实现是 MaltParser。现代神经版本是 Chen 和 Manning 的转移式分析器。
- **基于图的（graph-based）** 分析器（Eisner 算法、Dozat-Manning 双仿射 biaffine）：给每个可能的中心词-依存词边打分，选最大生成树。更慢但更准。

对大多数应用工作，直接调 spaCy：

```python
import spacy

nlp = spacy.load("en_core_web_sm")
doc = nlp("The cats were running at 3pm.")
for token in doc:
    print(f"{token.text:10s} tag={token.tag_:5s} pos={token.pos_:6s} dep={token.dep_:10s} head={token.head.text}")
```

```
The        tag=DT    pos=DET    dep=det        head=cats
cats       tag=NNS   pos=NOUN   dep=nsubj      head=running
were       tag=VBD   pos=AUX    dep=aux        head=running
running    tag=VBG   pos=VERB   dep=ROOT       head=running
at         tag=IN    pos=ADP    dep=prep       head=running
3pm        tag=NN    pos=NOUN   dep=pobj       head=at
.          tag=.     pos=PUNCT  dep=punct      head=running
```

把 `dep` 那一列从下往上读，句子的语法结构就自己浮现出来。

> Full dependency parsing from scratch is out of scope; the canonical textbook treatment is in Jurafsky and Martin. Two classical families to know: ... **Transition-based** parsers (arc-eager, arc-standard) act like a shift-reduce parser ... **Graph-based** parsers (Eisner's algorithm, Dozat-Manning biaffine) score every possible head-dependent edge and pick the maximum spanning tree. Slower but more accurate. ... Read the `dep` column bottom to top and the sentence's grammatical structure falls out.

## Use It · 实战用法

每个生产级 NLP 库都把 POS 和依存分析器作为标准流水线的一部分交付。

- **spaCy**（`en_core_web_sm` / `md` / `lg` / `trf`）。快、准，和分词 + NER + 词形还原集成在一起。`token.tag_`（Penn）、`token.pos_`（UD）、`token.dep_`（依存关系）。
- **Stanford NLP (stanza)**。CoreNLP 的斯坦福继任者。在 60 多种语言上是当时最优水平。
- **trankit**。基于 Transformer，UD 精度好。
- **NLTK**。`pos_tag`。能用、慢、老。教学够用。

> Every production NLP library ships POS and dependency parsers as part of a standard pipeline.
> **spaCy** (`en_core_web_sm` / `md` / `lg` / `trf`). Fast, accurate, integrated with tokenization + NER + lemmatization. ... **Stanford NLP (stanza)**. Stanford's successor to CoreNLP. State-of-the-art on 60+ languages. ... **NLTK**. `pos_tag`. Usable, slow, older. Fine for teaching.

### Where this still matters in 2026 · 2026 年它还在哪起作用

- **词形还原。** 第 01 课要正确做词形还原就得有 POS。永远如此。
- **LLM 输出的结构化抽取。** 校验生成的句子是否遵守语法约束（比如主谓一致、必需的修饰成分）。
- **基于方面的情感分析（aspect-based sentiment）。** 依存分析告诉你哪个形容词修饰哪个名词。
- **查询理解。** "movies directed by Wes Anderson starring Bill Murray" 经句法分析分解成结构化约束。
- **跨语言迁移。** UD 标签和依存关系与具体语言无关，可以对新语言做零样本结构化分析。
- **低算力流水线。** 如果你部署不了 Transformer，POS + 依存分析 + 词典能带你走得出乎意料的远。

> **Lemmatization.** Lesson 01 needs POS to lemmatize correctly. Always.
> **Structured extraction from LLM outputs.** Validate that a generated sentence respects grammatical constraints (e.g., subject-verb agreement, required modifiers).
> **Cross-lingual transfer.** UD tags and dependency relations are language-agnostic, enabling zero-shot structured analysis of new languages.
> **Low-compute pipelines.** If you cannot ship a transformer, POS + dependency parse + gazetteer gets you surprisingly far.

## Ship It · 交付

保存为 `outputs/skill-grammar-pipeline.md`：

```markdown
---
name: grammar-pipeline
description: Design a classical POS + dependency pipeline for a downstream NLP task.
version: 1.0.0
phase: 5
lesson: 07
tags: [nlp, pos, parsing]
---

Given a downstream task (information extraction, rewrite validation, query decomposition, lemmatization), you output:

1. Tagset to use. Penn Treebank for English-only legacy pipelines, Universal Dependencies for multilingual or cross-lingual.
2. Library. spaCy for most production, stanza for academic-grade multilingual, trankit for highest UD accuracy. Name the specific model ID.
3. Integration pattern. Show the 3-5 lines that call the library and consume the needed attributes (`.pos_`, `.dep_`, `.head`).
4. Failure mode to test. Noun-verb ambiguity (`saw`, `book`, `can`) and PP-attachment ambiguity are the classical traps. Sample 20 outputs and eyeball.

Refuse to recommend rolling your own parser. Building parsers from scratch is a research project, not an application task. Flag any pipeline that consumes POS tags without handling lowercase/uppercase variants as fragile.
```

> Save as `outputs/skill-grammar-pipeline.md`.

## Exercises · 练习

1. **简单。** 在一个小的已标注语料（比如 NLTK 的 Brown 子集）上运行最高频标签基线，测量留出句上的准确率。验证约 85% 的结果。
2. **中等。** 训练上面的 bigram HMM，报告每个标签的精确率/召回率。HMM 最容易混淆哪些标签？
3. **困难。** 用 spaCy 的依存分析从 1000 句样本中抽取主语-动词-宾语三元组。在 50 个人工标注的三元组上评估。记录抽取失败的地方（常见于被动句、并列结构和省略主语）。

> **Easy.** Using the most-frequent-tag baseline on a small tagged corpus (e.g., NLTK's Brown subset), measure accuracy on held-out sentences. Verify the ~85% result.
> **Medium.** Train the bigram HMM above and report per-tag precision/recall. Which tags does the HMM confuse most?
> **Hard.** Use spaCy's dependency parse to extract subject-verb-object triples from a 1000-sentence sample. Evaluate on 50 manually labeled triples. Document where extraction fails (often passives, coordinations, and elided subjects).

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| POS tag | 词的类型 | 语法类别。PTB 有 36 个；UD 有 17 个。 |
| Penn Treebank | 标准标注集 | 英语专用。动词时态和名词单复数分得很细。 |
| Universal Dependencies | 多语言标注集 | 比 PTB 粗；语言中立；跨语言工作的默认选择。 |
| Dependency parse | 句子树 | 每个词有一个中心词，每条边有一个语法关系。 |
| Viterbi | 动态规划 | 在发射和转移概率给定的情况下，找出概率最高的标签序列。 |

## Further Reading · 延伸阅读

- [Jurafsky and Martin — Speech and Language Processing, chapters 8 and 18](https://web.stanford.edu/~jurafsky/slp3/) —— POS 与句法分析的教科书级标准讲解。
- [Universal Dependencies project](https://universaldependencies.org/) —— 每个多语言分析器都在用的跨语言标注集和树库合集。
- [spaCy linguistic features guide](https://spacy.io/usage/linguistic-features) —— `Token` 上所有属性的实用参考。
- [Chen and Manning (2014). A Fast and Accurate Dependency Parser using Neural Networks](https://nlp.stanford.edu/pubs/emnlp2014-depparser.pdf) —— 把神经分析器带入主流的那篇论文。
