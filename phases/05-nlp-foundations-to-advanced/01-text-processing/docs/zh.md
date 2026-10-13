# Text Processing — Tokenization, Stemming, Lemmatization · 文本处理：分词、词干提取与词形还原

> 语言是连续的，模型是离散的，预处理就是两者之间的那座桥。
> Language is continuous. Models are discrete. Preprocessing is the bridge.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 2 · 14 (Naive Bayes)
**Time:** ~45 minutes

## The Problem · 问题在哪

模型读不了 "The cats were running."，它只读整数。

每个 NLP 系统开篇都要回答同样三个问题：一个词从哪里开始？一个词的词根是什么？什么时候该把 "run"、"running"、"ran" 当成同一个东西（这样有帮助），什么时候该当成不同的东西？

分词（tokenization）做错，模型就在垃圾上学习。如果你的分词器把 `don't` 切成一个 token，却把 `do n't` 切成两个，训练分布就分裂了。如果你的词干提取器（stemmer）把 `organization` 和 `organ` 归并到同一个词干，主题建模就完了。如果你的词形还原器（lemmatizer）需要词性上下文而你没传，动词就会被当成名词处理。

本课从零构建这三个预处理步骤，再展示 NLTK 和 spaCy 如何做同样的工作，让你看清各自的取舍。

> A model cannot read "The cats were running." It reads integers.
> Every NLP system opens with the same three questions. Where does a word start. What is the root of the word. How do we treat "run", "running", "ran" as the same thing when it helps, and as different things when it doesn't.
> Get tokenization wrong and the model learns from garbage. If your tokenizer treats `don't` as one token but `do n't` as two, the training distribution splits. If your stemmer collapses `organization` and `organ` to the same stem, topic modeling dies. If your lemmatizer needs part-of-speech context but you don't pass it, verbs get treated as nouns.
> This lesson builds the three preprocessing steps from scratch, then shows how NLTK and spaCy do the same work so you can see the tradeoffs.

## The Concept · 概念

三个操作。每个都有它的任务，也都有它的失败方式。

**分词（Tokenization）** 把字符串切成 token。"Token" 一词刻意保持模糊，因为合适的粒度取决于任务：经典 NLP 用词级，transformer 用子词（subword），没有空格的语言用字符级。

**词干提取（Stemming）** 按规则砍后缀。快、激进、糙。`running -> run`，`organization -> organ`。第二个例子就是它的失败方式。

**词形还原（Lemmatization）** 借助语法知识把词还原成词典形式。慢、准确，需要查找表或形态分析器。`ran -> run`（需要知道 "ran" 是 "run" 的过去式）。`better -> good`（需要知道比较级形式）。

经验法则：速度重要、能容忍噪声时用词干提取（搜索索引、粗糙分类）；语义重要时用词形还原（问答、语义搜索、任何用户会读到的文本）。

```figure
edit-distance
```

> Three operations. Each has a job and a failure mode.
> Tokenization splits a string into tokens. "Token" is deliberately vague because the right granularity depends on the task. Word-level for classical NLP. Subword for transformers. Character for languages without whitespace.
> Stemming chops suffixes with rules. Fast, aggressive, dumb. `running -> run`. `organization -> organ`. That second one is the failure mode.
> Lemmatization reduces a word to its dictionary form using grammar knowledge. Slower, accurate, needs a lookup table or morphological analyzer.
> Rule of thumb. Stem when speed matters and you can tolerate noise (search indexing, rough classification). Lemmatize when meaning matters (question answering, semantic search, anything the user will read).

## Build It · 动手造

### Step 1: a regex word tokenizer · 一个正则表达式词分词器

最简单可用的分词器：在非字母数字字符处切分，同时把标点保留为独立 token。不完美，也不是最终方案，但它一行就能跑起来。

```python
import re

def tokenize(text):
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?|[0-9]+|[^\sA-Za-z0-9]", text)
```

三个模式按优先级排列：带内部撇号的词（`don't`、`it's`）；纯数字；任何单个非空白、非字母数字字符作为独立 token（标点）。

```python
>>> tokenize("The cats weren't running at 3pm.")
['The', 'cats', "weren't", 'running', 'at', '3', 'pm', '.']
```

需要留意的失败模式：`3pm` 被切成 `['3', 'pm']`，因为我们在字母串和数字串之间做了交替。对多数任务够用了。URL、邮箱、hashtag 全都会挂。生产环境要在通用模式之前加上更具体的模式。

> The simplest useful tokenizer splits on non-alphanumeric characters while keeping punctuation as its own tokens. Not perfect, not final, but it runs in one line.
> Three patterns in order of precedence. Words with optional inner apostrophe (`don't`, `it's`). Pure numbers. Any single non-whitespace non-alphanumeric character as a standalone token (punctuation).
> Failure modes to notice. `3pm` splits to `['3', 'pm']` because we alternated between letter runs and digit runs. Good enough for most tasks. URLs, emails, hashtags all break. For production, add patterns before the general ones.

### Step 2: a Porter stemmer (step 1a only) · Porter 词干提取器（只做 step 1a）

完整的 Porter 算法有五个阶段的规则。仅 step 1a 就覆盖了最高频的英文后缀，也足以讲清这套套路。

```python
def stem_step_1a(word):
    if word.endswith("sses"):
        return word[:-2]
    if word.endswith("ies"):
        return word[:-2]
    if word.endswith("ss"):
        return word
    if word.endswith("s") and len(word) > 1:
        return word[:-1]
    return word
```

```python
>>> [stem_step_1a(w) for w in ["caresses", "ponies", "caress", "cats"]]
['caress', 'poni', 'caress', 'cat']
```

自上而下读规则。`ponies -> poni`（而不是 `pony`）正是 `ies -> i` 这条规则的结果。真正的 Porter 还有能修正它的 step 1b。规则之间相互竞争，先出现的规则赢——顺序比任何单条规则都重要。

> The full Porter algorithm has five phases of rules. Step 1a alone covers the most frequent English suffixes and teaches the pattern.
> Read the rules top-down. The `ies -> i` rule is why `ponies -> poni`, not `pony`. Real Porter has step 1b that would fix it. Rules compete. Earlier rules win. The order matters more than any single rule.

### Step 3: a lookup-based lemmatizer · 基于查找表的词形还原器

正宗的词形还原需要形态学。一个可操作的教学版本：一张小词元表，加一条兜底规则。

```python
LEMMA_TABLE = {
    ("running", "VERB"): "run",
    ("ran", "VERB"): "run",
    ("runs", "VERB"): "run",
    ("better", "ADJ"): "good",
    ("best", "ADJ"): "good",
    ("cats", "NOUN"): "cat",
    ("cat", "NOUN"): "cat",
    ("were", "VERB"): "be",
    ("was", "VERB"): "be",
    ("is", "VERB"): "be",
}

def lemmatize(word, pos):
    key = (word.lower(), pos)
    if key in LEMMA_TABLE:
        return LEMMA_TABLE[key]
    if pos == "VERB" and word.endswith("ing"):
        return word[:-3]
    if pos == "NOUN" and word.endswith("s"):
        return word[:-1]
    return word.lower()
```

```python
>>> lemmatize("running", "VERB")
'run'
>>> lemmatize("cats", "NOUN")
'cat'
>>> lemmatize("better", "ADJ")
'good'
>>> lemmatize("watched", "VERB")
'watched'
```

最后一个用例是关键的教学点：`watched` 不在我们的表里，而兜底规则只处理 `ing`。真正的词形还原要覆盖 `ed`、不规则动词、比较级形容词、带音变的复数（`children -> child`）。这正是生产系统使用 WordNet、spaCy 的 morphologizer 或完整形态分析器的原因。

> Lemmatization proper needs morphology. A tractable teaching version uses a small lemma table and a fallback.
> The last case is the key teaching moment. `watched` is not in our table and our fallback only handles `ing`. Real lemmatization covers `ed`, irregular verbs, comparative adjectives, plurals with sound changes (`children -> child`). This is why production systems use WordNet, spaCy's morphologizer, or a full morphological analyzer.

### Step 4: pipe them together · 串成一条流水线

```python
def preprocess(text, pos_tagger=None):
    tokens = tokenize(text)
    stems = [stem_step_1a(t.lower()) for t in tokens]
    tags = pos_tagger(tokens) if pos_tagger else [(t, "NOUN") for t in tokens]
    lemmas = [lemmatize(word, pos) for word, pos in tags]
    return {"tokens": tokens, "stems": stems, "lemmas": lemmas}
```

缺的那一环是词性标注器（POS tagger）。Phase 5 · 07（POS Tagging）会造一个。眼下先把所有词默认为 `NOUN`，并承认这个局限。

> The missing piece is a POS tagger. Phase 5 · 07 (POS Tagging) builds one. For now, default everything to `NOUN` and acknowledge the limitation.

## Use It · 实战用法

NLTK 和 spaCy 自带生产级实现，各自只需几行。

> NLTK and spaCy ship the production versions. A few lines each.

### NLTK

```python
import nltk
nltk.download("punkt_tab")
nltk.download("wordnet")
nltk.download("averaged_perceptron_tagger_eng")

from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer, WordNetLemmatizer
from nltk import pos_tag

text = "The cats were running."
tokens = word_tokenize(text)
stems = [PorterStemmer().stem(t) for t in tokens]
lemmatizer = WordNetLemmatizer()
tagged = pos_tag(tokens)


def nltk_pos_to_wordnet(tag):
    if tag.startswith("V"):
        return "v"
    if tag.startswith("J"):
        return "a"
    if tag.startswith("R"):
        return "r"
    return "n"


lemmas = [lemmatizer.lemmatize(t, nltk_pos_to_wordnet(tag)) for t, tag in tagged]
```

`word_tokenize` 能处理缩写、Unicode，以及你的正则会漏掉的各种边界情况。`PorterStemmer` 跑满全部五个阶段。`WordNetLemmatizer` 需要把词性标签从 NLTK 的 Penn Treebank 体系翻译成 WordNet 的缩写体系。上面这段翻译接线，正是大多数教程跳过的部分。

> `word_tokenize` handles contractions, Unicode, edge cases your regex misses. `PorterStemmer` runs all five phases. `WordNetLemmatizer` needs the POS tag translated from NLTK's Penn Treebank scheme to WordNet's abbreviation set. The translation wiring above is the bit most tutorials skip.

### spaCy

```python
import spacy

nlp = spacy.load("en_core_web_sm")
doc = nlp("The cats were running.")

for token in doc:
    print(token.text, token.lemma_, token.pos_)
```

```
The      the     DET
cats     cat     NOUN
were     be      AUX
running  run     VERB
.        .       PUNCT
```

spaCy 把整条流水线藏在 `nlp(text)` 一句话背后。分词、词性标注、词形还原一并执行。规模大时比 NLTK 快，开箱即得更准。代价是你无法轻易替换单个组件。

> spaCy hides the whole pipeline behind `nlp(text)`. Tokenization, POS tagging, and lemmatization all run. Faster than NLTK at scale. More accurate out of the box. The tradeoff is that you cannot easily swap individual components.

### When to pick which · 怎么选

| 场景 | 选择 |
|------|------|
| 教学、研究、需要替换组件 | NLTK |
| 生产环境、多语言、速度敏感 | spaCy |
| Transformer 流水线（反正你终究要用模型自带的分词器） | 用 `tokenizers` / `transformers`，跳过经典预处理 |

> Teaching, research, swapping components: NLTK. Production, multi-language, speed matters: spaCy.
> Transformer pipeline (you'll tokenize with the model's tokenizer anyway): use `tokenizers` / `transformers` and skip classical preprocessing.

### The two failure modes nobody warns you about · 没人提醒你的两种失败模式

多数教程讲完算法就停了。有两件事会咬到真实的预处理流水线，而它们几乎从没被讲过。

**可复现性漂移（reproducibility drift）。** NLTK 和 spaCy 在版本之间会改变分词和词形还原的行为。spaCy 2.x 里产出 `['do', "n't"]` 的输入，到 3.x 可能产出 `["don't"]`。你的模型在一个分布上训练，推理却跑在另一个分布上。精度悄悄劣化，没人知道为什么。把库版本钉死在 `requirements.txt` 里。写一个预处理回归测试，冻结 20 个样例句的预期分词结果，每次升级都跑一遍。

**训练 / 推理不一致（training / inference mismatch）。** 训练时用激进预处理（小写化、去停用词、词干提取），部署时吃原始用户输入，然后眼看性能崩盘。这是生产 NLP 最常见的失败，没有之一。训练时做了预处理，推理时就必须跑一模一样的函数。把预处理作为函数放进模型包一起交付，而不是留给服务团队重写的一个 notebook 单元格。

> Most tutorials teach the algorithms and stop. Two things will bite a real preprocessing pipeline, and they are almost never covered.
> **Reproducibility drift.** NLTK and spaCy change tokenization and lemmatizer behavior between versions. What produced `['do', "n't"]` in spaCy 2.x may produce `["don't"]` in 3.x. Your model was trained on one distribution. Inference now runs on a different one. Accuracy quietly degrades and nobody knows why. Pin library versions in `requirements.txt`. Write a preprocessing regression test that freezes expected tokenization of 20 sample sentences. Run it on every upgrade.
> **Training / inference mismatch.** Train with aggressive preprocessing (lowercase, stopword removal, stemming), deploy on raw user input, watch performance crater. This is the single most common production NLP failure. If you preprocess during training, you must run the identical function during inference. Ship preprocessing as a function inside the model package, not as a notebook cell the serving team rewrites.

## Ship It · 交付

一个可复用的提示词：帮工程师不必啃三本教材，就能选定预处理策略。

保存为 `outputs/prompt-preprocessing-advisor.md`：

```markdown
---
name: preprocessing-advisor
description: Recommends a tokenization, stemming, and lemmatization setup for an NLP task.
phase: 5
lesson: 01
---

You advise on classical NLP preprocessing. Given a task description, you output:

1. Tokenization choice (regex, NLTK word_tokenize, spaCy, or transformer tokenizer). Explain why.
2. Whether to stem, lemmatize, both, or neither. Explain why.
3. Specific library calls. Name the functions. Quote the POS-tag translation if NLTK is involved.
4. One failure mode the user should test for.

Refuse to recommend stemming for user-visible text. Refuse to recommend lemmatization without POS tags. Flag non-English input as needing a different pipeline.
```

> A reusable prompt that helps engineers pick a preprocessing strategy without reading three textbooks.
> Save as `outputs/prompt-preprocessing-advisor.md`:

## Exercises · 练习

1. **简单。** 扩展 `tokenize`，让 URL 保留为单个 token。测试：`tokenize("Visit https://example.com today.")` 应产出一个 URL token。
2. **中等。** 实现 Porter step 1b：如果一个词包含元音且以 `ed` 或 `ing` 结尾，删掉后缀。处理好双辅音规则（`hopping -> hop`，而不是 `hopp`）。
3. **困难。** 构建一个以 WordNet 为查找表的词形还原器，WordNet 没有条目时回退到你的 Porter 词干提取器。在带标注语料上测准确率，与纯 WordNet、纯 Porter 各自对比。

## Key Terms · 术语表

| 术语 | 人们的说法 | 实际含义 |
|------|-----------|---------|
| Token | 「一个词」 | 模型消费的任何单位。可以是词、子词、字符或字节。 |
| Stem | 「词根」 | 按规则剥后缀的结果。不一定是真实存在的词。 |
| Lemma | 「词典形式」 | 你会拿去查词典的那个形式。要算对需要语法上下文。 |
| POS tag | 「词性」 | NOUN、VERB、ADJ 这类类别。准确做词形还原必需。 |
| Morphology | 「构词规则」 | 词如何随时态、数、格改变形式。词形还原依赖它。 |

## Further Reading · 延伸阅读

- [Porter, M. F. (1980). An algorithm for suffix stripping](https://tartarus.org/martin/PorterStemmer/def.txt) —— 原始论文，五页，至今仍是最清晰的讲解。
- [spaCy 101 — linguistic features](https://spacy.io/usage/linguistic-features) —— 一条真实流水线是如何接起来的。
- [NLTK book, chapter 3](https://www.nltk.org/book/ch03.html) —— 你还没想到过的那些分词边界情况。
