# Sentiment Analysis · 情感分析

> NLP 的经典任务。经典文本分类的要点，大都在这里登场。
> The canonical NLP task. Most of what you need to know about classical text classification shows up here.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 02 (BoW + TF-IDF), Phase 2 · 14 (Naive Bayes)
**Time:** ~75 minutes

## The Problem · 问题在哪

"The food was not great."，正面还是负面？

情感分析听着简单：评论者说了喜欢还是不喜欢，给句子打个标签。它之所以成为 NLP 的经典任务，是因为每个看起来容易的案例背后都藏着一个难的。否定翻转语义，讽刺把语义反过来，"Not bad at all" 带着两个负面色彩词却整体是正面，emoji 比周围文字的信号还强，领域词汇举足轻重（乐评里的 `tight` 对比时尚评论里的 `tight`）。

情感分析是经典 NLP 的练功房。如果你理解每个朴素基线为什么各有特定的失败模式，你就理解每个更复杂的模型为什么被发明出来。本课从零构建一个朴素贝叶斯（Naive Bayes）基线，加上逻辑回归（logistic regression），并点名那些让生产级情感分析变成合规级问题的陷阱。

> "The food was not great." Positive or negative?
> Sentiment sounds simple. A reviewer said they liked or did not like something. Label the sentence. The reason it became the canonical NLP task is that every easy-looking case hides a hard one. Negation flips meaning. Sarcasm inverts it. "Not bad at all" is positive despite two negative-coded words. Emojis carry more signal than surrounding text. Domain vocabulary matters (`tight` in music review versus `tight` in fashion review).
> Sentiment is a working lab for classical NLP. If you understand why every naive baseline has a specific failure mode, you understand why every richer model was invented. This lesson builds a Naive Bayes baseline from scratch, adds logistic regression, and names the traps that make production sentiment a compliance-grade problem.

## The Concept · 概念

经典情感分析是两步配方。

1. **表示。** 把文本变成特征向量：BoW、TF-IDF 或 n-gram。
2. **分类。** 在标注样本上拟合一个线性模型（朴素贝叶斯、逻辑回归、SVM）。

朴素贝叶斯是「能用」里最蠢的模型。假设给定标签后每个特征相互独立，从计数估计 `P(word | positive)` 和 `P(word | negative)`，推理时把概率乘起来。「朴素」的独立假设错得离谱，结果却强得吓人。原因在于：特征稀疏、数据适中时，分类器在意的更多是每个词偏向哪一边，而不是偏多少。

逻辑回归修掉了独立假设。它为每个特征学一个权重，包括负权重。`not good` 作为一个 bigram 特征会拿到负权重。朴素贝叶斯对自己从没标注过的 bigram 做不到这一点。

```figure
sentiment-logits
```

> Classical sentiment is a two-step recipe.
> Naive Bayes is the dumbest model that works. Assume every feature is independent given the label. Estimate `P(word | positive)` and `P(word | negative)` from counts. At inference, multiply the probabilities. The "naive" independence assumption is laughably wrong and yet the results are shockingly strong. The reason: with sparse text features and moderate data, the classifier cares about which side each word leans toward more than how much.
> Logistic regression fixes the independence assumption. It learns a weight per feature, including negative weights. `not good` as a bigram feature gets a negative weight. Naive Bayes cannot do that for bigrams it has never labeled.

## Build It · 动手造

### Step 1: a real mini-dataset · 一个真实的迷你数据集

```python
POSITIVE = [
    "absolutely loved this movie",
    "beautiful cinematography and a great story",
    "one of the best films of the year",
    "brilliant acting from the lead",
    "heartwarming and funny",
]

NEGATIVE = [
    "boring and far too long",
    "not worth your time",
    "the plot made no sense",
    "terrible acting, awful script",
    "i want my two hours back",
]
```

规模小是故意的。真实工作用几万条样本（IMDb、SST-2、Yelp polarity），数学完全一样。

> Small on purpose. Real work uses tens of thousands of examples (IMDb, SST-2, Yelp polarity). The math is identical.

### Step 2: multinomial Naive Bayes from scratch · 从零实现多项式朴素贝叶斯

```python
import math
from collections import Counter


def train_nb(docs_by_class, vocab, alpha=1.0):
    class_priors = {}
    class_word_probs = {}
    total_docs = sum(len(d) for d in docs_by_class.values())

    for cls, docs in docs_by_class.items():
        class_priors[cls] = len(docs) / total_docs
        counts = Counter()
        for doc in docs:
            for token in doc:
                counts[token] += 1
        total = sum(counts.values()) + alpha * len(vocab)
        class_word_probs[cls] = {
            w: (counts[w] + alpha) / total for w in vocab
        }
    return class_priors, class_word_probs


def predict_nb(doc, class_priors, class_word_probs):
    scores = {}
    for cls in class_priors:
        s = math.log(class_priors[cls])
        for token in doc:
            if token in class_word_probs[cls]:
                s += math.log(class_word_probs[cls][token])
        scores[cls] = s
    return max(scores, key=scores.get)
```

加性平滑（alpha=1.0）就是拉普拉斯平滑（Laplace smoothing）。没有它，某个类里没见过的词概率为零，对数直接爆炸。实践中常用 `alpha=0.01`；`alpha=1.0` 是教学默认。

> Additive smoothing (alpha=1.0) is Laplace smoothing. Without it, a word unseen in a class has probability zero and the log explodes. `alpha=0.01` is common in practice. `alpha=1.0` is the teaching default.

### Step 3: logistic regression from scratch · 从零实现逻辑回归

```python
import numpy as np


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -20, 20)))


def train_lr(X, y, epochs=500, lr=0.05, l2=0.01):
    n_features = X.shape[1]
    w = np.zeros(n_features)
    b = 0.0
    for _ in range(epochs):
        logits = X @ w + b
        preds = sigmoid(logits)
        err = preds - y
        grad_w = X.T @ err / len(y) + l2 * w
        grad_b = err.mean()
        w -= lr * grad_w
        b -= lr * grad_b
    return w, b


def predict_lr(X, w, b):
    return (sigmoid(X @ w + b) >= 0.5).astype(int)
```

L2 正则化在这里很重要。文本特征是稀疏的，没有 L2 模型就会背下训练样本。从 `0.01` 起步再调。

> L2 regularization matters here. Text features are sparse; without L2 the model memorizes training examples. Start at `0.01` and tune.

### Step 4: handling negation (the failure mode) · 处理否定（那个失败模式）

看 "not good" 和 "not bad"。BoW 分类器看到 `{not, good}` 和 `{not, bad}`，从训练集中出现更多的那个学。bigram 分类器看到 `not_good` 和 `not_bad`，把它们当作不同的特征来学。这通常就够用了。

没有 bigram 时，一个更糙但有效的修法：**否定作用域（negation scoping）**。把否定词之后、直到下一个标点之前的 token 都加上 `NOT_` 前缀。

```python
NEGATION_WORDS = {"not", "no", "never", "nor", "none", "nothing", "neither"}
NEGATION_TERMINATORS = {".", "!", "?", ",", ";"}


def apply_negation(tokens):
    out = []
    negate = False
    for token in tokens:
        if token in NEGATION_TERMINATORS:
            negate = False
            out.append(token)
            continue
        if token in NEGATION_WORDS:
            negate = True
            out.append(token)
            continue
        out.append(f"NOT_{token}" if negate else token)
    return out
```

```python
>>> apply_negation(["not", "good", "at", "all", ".", "but", "funny"])
['not', 'NOT_good', 'NOT_at', 'NOT_all', '.', 'but', 'funny']
```

现在 `good` 和 `NOT_good` 是不同的特征，分类器可以给它们相反的权重。三行预处理，换来情感基准上可测量的精度跃升。

> Consider "not good" and "not bad". A BoW classifier sees `{not, good}` and `{not, bad}` and learns from whichever showed up more in training. A bigram classifier sees `not_good` and `not_bad` and learns them as distinct features. That is usually enough.
> A cruder fix that works when you do not have bigrams: **negation scoping**. Prefix tokens following a negation word with `NOT_` up to the next punctuation.
> Now `good` and `NOT_good` are different features. The classifier can weight them opposite. Three lines of preprocessing, measurable accuracy jump on sentiment benchmarks.

### Step 5: evaluation metrics that matter · 真正要紧的评估指标

类别不平衡时，只看准确率会误导。真实的情感语料通常是 70-80% 正面或 70-80% 负面；一个永远输出多数类的分类器能拿 80% 准确率，却毫无价值。以下每一项都要报告：

- **每类精确率与召回率。** 每类一对。对它们做宏平均（macro-average），得到一个尊重类别平衡的单值。
- **Macro-F1（不平衡数据的首要指标）。** 每类 F1 的等权平均。类别不平衡时用它替代准确率。
- **Weighted-F1（备选）。** 同宏平均，但按类别频率加权。当不平衡本身有业务含义时，与 macro-F1 一起报告。
- **混淆矩阵。** 原始计数。信任任何标量指标之前必看；它会暴露模型把哪一对类搞混。
- **每类错误样本。** 每类抽 5 条错预测，去读它们。没有任何东西能替代阅读真实的错误。

严重不平衡的数据（> 95-5 的比例），改报 **AUROC** 和 **AUPRC**，别报准确率。AUPRC 对少数类更敏感，而那通常正是你关心的（垃圾、欺诈、稀有情感）。

**要避开的常见 bug。** 在不平衡数据上报 micro-F1 而不是 macro-F1，得到的数字看着很高，因为它被多数类主导。Macro-F1 逼你直视少数类的表现。

```python
def evaluate(y_true, y_pred):
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "precision": precision, "recall": recall, "f1": f1}
```

> Accuracy alone is misleading if classes are imbalanced. Real sentiment corpora are usually 70-80% positive or 70-80% negative; a constant-majority classifier gets 80% accuracy and is worthless. Report every one of the following:
> **Macro-F1 (primary metric for imbalanced data).** Mean of per-class F1 scores, equally weighted. Use this instead of accuracy when classes are imbalanced.
> For severely imbalanced data (> 95-5 ratio), report **AUROC** and **AUPRC** instead of accuracy. AUPRC is more sensitive to the minority class, which is what you usually care about (spam, fraud, rare sentiment).
> **Common bug to avoid.** Reporting micro-F1 instead of macro-F1 on imbalanced data gives a number that looks high because it is dominated by the majority class. Macro-F1 forces you to see the minority-class performance.

## Use It · 实战用法

scikit-learn 六行搞定，而且是对的。

> scikit-learn does it in six lines, correctly.

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

pipe = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, stop_words=None)),
    ("clf", LogisticRegression(C=1.0, max_iter=1000)),
])
pipe.fit(X_train, y_train)
print(pipe.score(X_test, y_test))
```

三个要注意的点。`stop_words=None` 保留否定词；`ngram_range=(1, 2)` 引入 bigram，`not_good` 成为一个特征；`sublinear_tf=True` 抑制重复词。这三个开关，就是在 SST-2 上 75% 准确率基线和 85% 准确率基线的差别。

> Three things to notice. `stop_words=None` keeps negations. `ngram_range=(1, 2)` adds bigrams so `not_good` becomes a feature. `sublinear_tf=True` dampens repeated words. These three flags are the difference between a 75%-accurate baseline and an 85%-accurate baseline on SST-2.

### When to reach for a transformer · 什么时候该上 transformer

- 讽刺检测。经典模型在这里全军覆没，没有例外。
- 情感会在文档中途转向的长评论。
- 方面级情感（aspect-based sentiment）。"Camera was great but battery was terrible." 你要把情感归属到具体的方面上。只有 transformer 或结构化输出模型能做。
- 非英语、低资源语言。多语言 BERT 免费送你一个零样本基线。

只要命中上面任何一条，直接跳到 phase 7（transformer 深潜）。否则，TF-IDF 加 bigram 加否定处理之上跑朴素贝叶斯或逻辑回归，就是你 2026 年的生产基线。

> Sarcasm detection. Classical models fail here. Period.
> Long reviews where sentiment shifts mid-document.
> Aspect-based sentiment. "Camera was great but battery was terrible." You need to attribute sentiment to aspects. Transformers or structured output models only.
> Non-English, low-resource languages. Multilingual BERT gives you a zero-shot baseline for free.
> If you need any of the above, skip ahead to phase 7 (transformers deep dive). Otherwise, Naive Bayes or logistic regression on TF-IDF plus bigrams plus negation handling is your 2026 production baseline.

### The reproducibility trap (again) · 可复现性陷阱（又来了）

重训情感模型是家常便饭，重新评估却不是。论文里报告的精度数字，用的是特定的切分、特定的预处理、特定的分词器。如果你不用一模一样的流水线就把新模型和基线比较，得到的 delta 会误导你。永远在你的流水线上重新生成基线，而不是引用论文的数字。

> Retraining sentiment models is routine. Re-evaluating them is not. Accuracy numbers reported in papers use specific splits, specific preprocessing, specific tokenizers. If you compare your new model to a baseline without using the identical pipeline, you will get misleading deltas. Always regenerate the baseline on your pipeline, not the paper's number.

## Ship It · 交付

保存为 `outputs/prompt-sentiment-baseline.md`：

```markdown
---
name: sentiment-baseline
description: Design a sentiment analysis baseline for a new dataset.
phase: 5
lesson: 05
---

Given a dataset description (domain, language, size, label granularity, latency budget), you output:

1. Feature extraction recipe. Specify tokenizer, n-gram range, stopword policy (usually keep), negation handling (scoped prefix or bigrams).
2. Classifier. Naive Bayes for baseline, logistic regression for production, transformer only if the domain needs sarcasm / aspects / cross-lingual.
3. Evaluation plan. Report precision, recall, F1, confusion matrix, and per-class error samples (not just scalars).
4. One failure mode to monitor post-deployment. Domain drift and sarcasm are the top two.

Refuse to recommend dropping stopwords for sentiment tasks. Refuse to report accuracy as the sole metric when classes are imbalanced (e.g., 90% positive). Flag subword-rich languages as needing FastText or transformer embeddings over word-level TF-IDF.
```

> Save as `outputs/prompt-sentiment-baseline.md`:

## Exercises · 练习

1. **简单。** 把 `apply_negation` 作为预处理步骤加进 scikit-learn 流水线，在一个小情感数据集上测 F1 的变化。
2. **中等。** 实现类别加权逻辑回归（给 scikit-learn 传 `class_weight="balanced"`，或自己推梯度）。在一个 90-10 的合成类别不平衡上测效果。
3. **困难。** 在情感模型的残差上训练第二个分类器，构建一个讽刺检测器。记录你的实验设置。当你的准确率低于随机水平时警告读者（二分类讽刺任务的随机水平约 50%，多数初次尝试就停在那里）。

## Key Terms · 术语表

| 术语 | 人们的说法 | 实际含义 |
|------|-----------|---------|
| Polarity | 「正面还是负面」 | 二元标签；有时扩展为中性或细粒度（五星）。 |
| Aspect-based sentiment | 「按方面的情感」 | 把情感归属到文中提到的具体实体或属性。 |
| Negation scoping | 「翻转附近的 token」 | 给 "not" 之后、直到标点前的 token 加 `NOT_` 前缀。 |
| Laplace smoothing | 「计数加一」 | 防止朴素贝叶斯出现零概率特征。 |
| L2 regularization | 「收缩权重」 | 在损失里加 `lambda * sum(w^2)`。稀疏文本特征的必备品。 |

## Further Reading · 延伸阅读

- [Pang and Lee (2008). Opinion Mining and Sentiment Analysis](https://www.cs.cornell.edu/home/llee/opinion-mining-sentiment-analysis-survey.html) —— 奠基性综述。很长，但前四节覆盖了全部经典内容。
- [Wang and Manning (2012). Baselines and Bigrams: Simple, Good Sentiment and Topic Classification](https://aclanthology.org/P12-2018/) —— 证明 bigram + 朴素贝叶斯在短文本上难以击败的那篇论文。
- [scikit-learn text feature extraction docs](https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction) —— `CountVectorizer`、`TfidfVectorizer` 和你将要调的每个旋钮的参考。
