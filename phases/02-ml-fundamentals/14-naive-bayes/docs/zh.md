# Naive Bayes · 朴素贝叶斯

> 「朴素」假设是错的，但它照样管用——这正是它的美妙之处。
>
> The "naive" assumption is wrong, and it works anyway. That's the beauty of it.

**Type:** Build
**Language:** Python
**Prerequisites:** Phase 2, Lessons 01-07 (classification, Bayes' theorem)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 从零实现带拉普拉斯平滑（Laplace smoothing）的多项式朴素贝叶斯（Multinomial Naive Bayes），用于文本分类
- 解释为什么朴素的独立性假设在数学上是错的，但在实践中仍能给出正确的类别排序
- 比较多项式（Multinomial）、伯努利（Bernoulli）、高斯（Gaussian）三种朴素贝叶斯变体，并针对给定特征类型选出合适的一种
- 在高维稀疏数据上把朴素贝叶斯与逻辑回归（logistic regression）对比，并解释其中起作用的偏差-方差权衡（bias-variance tradeoff）

> Implement Multinomial Naive Bayes from scratch with Laplace smoothing for text classification
> Explain why the naive independence assumption is mathematically wrong but produces correct class rankings in practice
> Compare Multinomial, Bernoulli, and Gaussian Naive Bayes variants and select the right one for a given feature type
> Evaluate Naive Bayes against logistic regression on high-dimensional sparse data and explain the bias-variance tradeoff at work

## The Problem · 问题在哪

你需要给文本分类：邮件分成垃圾/非垃圾，用户评论分成正面/负面，支持工单分成类别。你有几千个特征（每个词一个），而训练数据有限。

大多数分类器在这里会呛水。逻辑回归需要足够多的样本才能可靠地估计几千个权重。决策树一次只按一个词切分，过拟合得厉害。KNN 在 10,000 维里毫无意义，因为每个点和其他任何点的距离都差不多。

朴素贝叶斯（Naive Bayes）能搞定这件事。它做了一个数学上错误的假设（给定类别后，每个特征与其他任何特征都独立），却仍在文本分类上胜过那些「更聪明」的模型——训练集很小的时候尤其明显。它对数据只做一遍扫描即可完成训练，能扩展到数百万个特征，还能给出概率估计（尽管由于独立性假设，校准往往很差）。

理解「错误的假设为何能带来好的预测」，会让你领悟机器学习中一条根本道理：最好的模型不是最正确的那一个，而是针对你的数据偏差-方差权衡最好的那一个。

> You need to classify text. Emails into spam or not-spam. Customer reviews into positive or negative. Support tickets into categories. You have thousands of features (one per word) and limited training data.
> Most classifiers choke here. Logistic regression needs enough samples to estimate thousands of weights reliably. Decision trees split on one word at a time and overfit wildly. KNN in 10,000 dimensions is meaningless because every point is equally far from every other point.
> Naive Bayes handles this. It makes a mathematically wrong assumption (that every feature is independent of every other feature given the class), and it still outperforms "smarter" models on text classification, especially with small training sets. It trains in a single pass through the data. It scales to millions of features. It produces probability estimates (though often poorly calibrated due to the independence assumption).
> Understanding why a wrong assumption leads to good predictions teaches you something fundamental about machine learning: the best model is not the most correct one, it is the one with the best bias-variance tradeoff for your data.

## The Concept · 概念

### Bayes' Theorem (Quick Review) · 贝叶斯定理（快速回顾）

贝叶斯定理翻转条件概率：

```
P(class | features) = P(features | class) * P(class) / P(features)
```

我们想要的是 `P(class | features)`——给定文档中的词，它属于某个类别的概率。它可以由下面几项算出：
- `P(features | class)`——在这类文档中看到这些词的似然（likelihood）
- `P(class)`——类别的先验概率（垃圾邮件总体上有多常见？）
- `P(features)`——证据（evidence），对所有类别都相同，比较时可以忽略

`P(class | features)` 最大的那个类别胜出。

> Bayes' theorem flips conditional probabilities.
> We want `P(class | features)` -- the probability that a document belongs to a class given the words in it. We can compute this from: `P(features | class)` -- the likelihood of seeing these words in documents of this class; `P(class)` -- the prior probability of the class (how common is spam in general?); `P(features)` -- the evidence, same for all classes, so we can ignore it when comparing.
> The class with the highest `P(class | features)` wins.

### The Naive Independence Assumption · 朴素的独立性假设

要精确计算 `P(features | class)`，需要估计所有特征合在一起的联合概率。词表有 10,000 个词时，你得估计一个覆盖 2^10,000 种可能组合的分布。不可能。

朴素假设：给定类别后，每个特征条件独立。

```
P(w1, w2, ..., wn | class) = P(w1 | class) * P(w2 | class) * ... * P(wn | class)
```

于是不必估计一个不可能的联合分布，而是估计 n 个简单的逐特征分布。每一个只需要数个数。

这个假设显然是错的。"machine" 和 "learning" 在任何文档里都不独立。但分类器需要的不是正确的概率估计，而是正确的排序——哪个类别的概率最高。独立性假设引入系统性误差，但这些误差对所有类别的影响是相似的，所以排序依然正确。

> Computing `P(features | class)` exactly requires estimating the joint probability of all features together. With a vocabulary of 10,000 words, you would need to estimate a distribution over 2^10,000 possible combinations. Impossible.
> The naive assumption: every feature is conditionally independent given the class.
> Instead of one impossible joint distribution, you estimate n simple per-feature distributions. Each one needs only a count.
> This assumption is obviously wrong. The words "machine" and "learning" are not independent in any document. But the classifier does not need correct probability estimates. It needs correct rankings -- which class has the highest probability. The independence assumption introduces systematic errors, but those errors affect all classes similarly, so the ranking stays correct.

### Why It Still Works · 它为什么依然有效

三个原因：

1. **要排序，不要校准。** 分类只要求排第一的类别是对的。即使真实概率是 0.7 而模型给出 P(spam) = 0.99999，分类器仍然正确地选中 spam。我们不需要正确的概率，只需要正确的赢家。

2. **高偏差、低方差。** 独立性假设是一个很强的先验。它对模型施加了重约束，从而防止过拟合。训练数据有限时，「稍有偏差但稳定」的模型胜过「理论上正确但剧烈不稳定」的模型。这正是偏差-方差权衡在起作用。

3. **特征冗余会相互抵消。** 相关特征提供的是冗余证据。分类器把这份证据数了两遍，但它对正确的类别也同样数了两遍。如果 "machine" 和 "learning" 总是一起出现，它们都在为 "tech" 类别作证。NB 把它们算了两遍，但是为正确的类别算了两遍。

还有第四个很实际的原因：朴素贝叶斯极快。训练就是对数据做一遍词频计数，预测就是一次矩阵乘法。你可以在几秒内用一百万篇文档完成训练。这个速度意味着你可以迭代更快、尝试更多特征集、跑更多实验——比慢模型多得多。

> Three reasons:
> 1. **Ranking over calibration.** Classification only needs the top-ranked class to be correct. Even if P(spam) = 0.99999 when the true probability is 0.7, the classifier still picks spam correctly. We do not need correct probabilities. We need the correct winner.
> 2. **High bias, low variance.** The independence assumption is a strong prior. It constrains the model heavily, which prevents overfitting. With limited training data, a model that is slightly wrong but stable beats a model that is theoretically right but wildly unstable. This is the bias-variance tradeoff in action.
> 3. **Feature redundancy cancels out.** Correlated features provide redundant evidence. The classifier double-counts this evidence, but it double-counts it for the correct class too.
> A fourth, practical reason: Naive Bayes is extremely fast. Training is a single pass through the data counting frequencies. Prediction is a matrix multiplication.

### The Math Step by Step · 一步一步算一遍

我们走一个具体例子。两个类别：spam 和 not-spam。词表里有三个词："free"、"money"、"meeting"。

训练数据：
- 垃圾邮件提到 "free" 80 次、"money" 60 次、"meeting" 10 次（共 150 词）
- 非垃圾邮件提到 "free" 5 次、"money" 10 次、"meeting" 100 次（共 115 词）
- 40% 的邮件是垃圾，60% 不是

使用拉普拉斯平滑（alpha=1）：

```
P(free | spam)    = (80 + 1) / (150 + 3) = 81/153 = 0.529
P(money | spam)   = (60 + 1) / (150 + 3) = 61/153 = 0.399
P(meeting | spam) = (10 + 1) / (150 + 3) = 11/153 = 0.072

P(free | not-spam)    = (5 + 1) / (115 + 3) = 6/118 = 0.051
P(money | not-spam)   = (10 + 1) / (115 + 3) = 11/118 = 0.093
P(meeting | not-spam) = (100 + 1) / (115 + 3) = 101/118 = 0.856
```

新邮件包含："free"（2 次）、"money"（1 次）、"meeting"（0 次）。

```
log P(spam | email) = log(0.4) + 2*log(0.529) + 1*log(0.399) + 0*log(0.072)
                    = -0.916 + 2*(-0.637) + (-0.919) + 0
                    = -3.109

log P(not-spam | email) = log(0.6) + 2*log(0.051) + 1*log(0.093) + 0*log(0.856)
                        = -0.511 + 2*(-2.976) + (-2.375) + 0
                        = -8.838
```

spam 大幅胜出。"free" 出现两次是垃圾邮件的有力证据。注意 "meeting" 没出现对两边的对数和贡献都是零（0 * log(P)）——在多项式 NB 里，缺席的词不起作用。明确对「词缺席」建模的是伯努利 NB。

> Let us trace through a concrete example. Suppose we have two classes: spam and not-spam. Our vocabulary has three words: "free", "money", "meeting".
> Spam emails mention "free" 80 times, "money" 60 times, "meeting" 10 times (150 total words). Not-spam emails mention "free" 5 times, "money" 10 times, "meeting" 100 times (115 total words). 40% of emails are spam, 60% are not-spam.
> New email contains: "free" (2 times), "money" (1 time), "meeting" (0 times).
> Spam wins by a large margin. The word "free" appearing twice is strong evidence for spam. Note that "meeting" not appearing contributes zero to both log sums (0 * log(P)) -- in Multinomial NB, absent words have no effect. It is Bernoulli NB that explicitly models word absence.

### Three Variants · 三种变体

朴素贝叶斯有三种口味，各自用不同方式建模 `P(feature | class)`。

> Naive Bayes comes in three flavors. Each models `P(feature | class)` differently.

#### Multinomial Naive Bayes · 多项式朴素贝叶斯

把每个特征建模为计数。最适合特征是词频或 TF-IDF 值的文本数据。

```
P(word_i | class) = (count of word_i in class + alpha) / (total words in class + alpha * vocab_size)
```

`alpha` 是拉普拉斯平滑（下面细讲）。这个变体是文本分类的主力。

> Models each feature as a count. Best for text data where features are word frequencies or TF-IDF values.
> The `alpha` is Laplace smoothing (explained below). This variant is the workhorse for text classification.

#### Gaussian Naive Bayes · 高斯朴素贝叶斯

把每个特征建模为正态分布。最适合连续特征。

```
P(x_i | class) = (1 / sqrt(2 * pi * var)) * exp(-(x_i - mean)^2 / (2 * var))
```

每个类别对每个特征各有自己的均值和方差。当特征在每个类别内确实近似钟形分布时，效果很好。

> Models each feature as a normal distribution. Best for continuous features.
> Each class gets its own mean and variance per feature. This works well when features genuinely follow a bell curve within each class.

#### Bernoulli Naive Bayes · 伯努利朴素贝叶斯

把每个特征建模为二值（出现或不出现）。最适合短文本或二值特征向量。

```
P(word_i | class) = (docs in class containing word_i + alpha) / (total docs in class + 2 * alpha)
```

与多项式不同，伯努利会显式惩罚词的缺席。如果 "free" 通常出现在垃圾邮件里，而这封邮件里没有，伯努利会把这当作反对 spam 的证据。

> Models each feature as binary (present or absent). Best for short text or binary feature vectors.
> Unlike Multinomial, Bernoulli explicitly penalizes the absence of a word. If "free" typically appears in spam but is absent from this email, Bernoulli counts that as evidence against spam.

### When to Use Each Variant · 何时用哪种变体

| 变体 | 特征类型 | 最适合 | 例子 |
|------|---------|--------|------|
| Multinomial | 计数或词频 | 文本分类、词袋（bag-of-words） | 垃圾邮件过滤、主题分类 |
| Gaussian | 连续值 | 特征近似正态的表格数据 | 鸢尾花分类、传感器数据 |
| Bernoulli | 二值（0/1） | 短文本、二值特征向量 | 短信垃圾过滤、出现/缺席特征 |

> Multinomial | Counts or frequencies | Text classification, bag-of-words | Email spam, topic classification
> Gaussian | Continuous values | Tabular data with normal-ish features | Iris classification, sensor data

### Laplace Smoothing · 拉普拉斯平滑

如果某个词出现在测试数据里，却从未在某个类别的训练数据中出现过，会怎样？

不平滑的话：`P(word | class) = 0/N = 0`。一个零乘进整个连乘积，`P(class | features) = 0`，其他证据再多也没用。一个没见过的词就能毁掉整条预测，无论其他证据多么支持它。

拉普拉斯平滑给每个特征计数加上一个小的 `alpha`（通常取 1）：

```
P(word_i | class) = (count(word_i, class) + alpha) / (total_words_in_class + alpha * vocab_size)
```

alpha=1 时，每个词至少分到一个极小的概率。测试邮件里冒出个 "discombobulate" 不会再杀死 spam 概率。平滑还有一个贝叶斯解释：它等价于给词分布放置一个均匀的 Dirichlet 先验。

alpha 越大，平滑越强（分布越均匀）。alpha 越小，模型越信任数据。alpha 是一个要调的超参数。

alpha 的效果：

| Alpha | 效果 | 何时使用 |
|-------|------|---------|
| 0.001 | 几乎不平滑，信任数据 | 训练集非常大，预计不会出现未见特征 |
| 0.1 | 轻度平滑 | 训练集较大 |
| 1.0 | 标准拉普拉斯平滑 | 默认起点 |
| 10.0 | 强平滑，把分布压平 | 训练集非常小，预计会出现很多未见特征 |

> What happens when a word appears in the test data but never appeared in the training data for a particular class?
> Without smoothing: `P(word | class) = 0/N = 0`. One zero multiplied through the entire product makes `P(class | features) = 0`, regardless of all other evidence. A single unseen word destroys the entire prediction, no matter how much other evidence supports it.
> Laplace smoothing adds a small count `alpha` (usually 1) to every feature count.
> With alpha=1, every word gets at least a tiny probability. The word "discombobulate" appearing in a test email no longer kills the spam probability. The smoothing has a Bayesian interpretation: it is equivalent to placing a uniform Dirichlet prior on the word distributions.
> Higher alpha means stronger smoothing (more uniform distributions). Lower alpha means the model trusts the data more. Alpha is a hyperparameter you tune.

### Log-Space Computation · 对数空间计算

把几百个小于 1 的概率连乘会导致浮点下溢（underflow）：真实值明明是一个很小的正数，浮点里却变成零。

解决办法：在对数空间里工作。不乘概率，改加对数：

```
log P(class | x1, x2, ..., xn) = log P(class) + sum_i log P(xi | class)
```

这让预测变成一次点积：

```
log_scores = X @ log_feature_probs.T + log_class_priors
prediction = argmax(log_scores)
```

矩阵乘法。这就是朴素贝叶斯预测这么快的原因——它和单层线性模型做的是同一种运算。

> Multiplying hundreds of probabilities (each less than 1) causes floating-point underflow. The product becomes zero in floating point even though the true value is a very small positive number.
> The solution: work in log space. Instead of multiplying probabilities, add their logarithms.
> This turns the prediction into a dot product.
> Matrix multiplication. That is why Naive Bayes prediction is so fast -- it is the same operation as a single-layer linear model.

### Naive Bayes vs Logistic Regression · 朴素贝叶斯 vs 逻辑回归

两者都是文本上的线性分类器，差别在于建模的对象。

| 维度 | 朴素贝叶斯 | 逻辑回归 |
|------|-----------|---------|
| 类型 | 生成式（建模 P(X\|Y)） | 判别式（建模 P(Y\|X)） |
| 训练 | 数频率 | 优化损失函数 |
| 小数据 | 更好（强先验帮忙） | 更差（样本不足以估计权重） |
| 大数据 | 更差（错误假设拖后腿） | 更好（决策边界更灵活） |
| 特征 | 假设独立 | 能处理相关性 |
| 速度 | 一遍扫完，非常快 | 迭代优化 |
| 概率校准 | 概率不准 | 概率更可靠 |

经验法则：先上朴素贝叶斯。如果你数据够多而 NB 进入平台期，再换逻辑回归。

> Both are linear classifiers for text. The difference is in what they model.
> Type: Naive Bayes is generative (models P(X\|Y)); logistic regression is discriminative (models P(Y\|X)).
> Small data: NB is better (strong prior helps). Large data: logistic regression is better (flexible boundary).
> Rule of thumb: start with Naive Bayes. If you have enough data and NB plateaus, switch to logistic regression.

### Classification Pipeline · 分类管道

```mermaid
flowchart LR
    A[Raw Text] --> B[Tokenize]
    B --> C[Build Vocabulary]
    C --> D[Count Word Frequencies]
    D --> E[Apply Smoothing]
    E --> F[Compute Log Probabilities]
    F --> G[Predict: argmax P class given words]

    style A fill:#f9f,stroke:#333
    style G fill:#9f9,stroke:#333
```

实践中我们在对数空间里工作，以避免浮点下溢：不把许多小概率连乘，而是把它们的对数相加：

```
log P(class | features) = log P(class) + sum_i log P(feature_i | class)
```

```figure
naive-bayes
```

> In practice, we work in log space to avoid floating-point underflow. Instead of multiplying many small probabilities, we add their logarithms.

## Build It · 动手造

`code/naive_bayes.py` 从零实现了 MultinomialNB 和 GaussianNB 两者。

> The code in `code/naive_bayes.py` implements both MultinomialNB and GaussianNB from scratch.

### MultinomialNB

从零开始的实现：

1. **fit(X, y)**：对每个类别，统计每个特征的频率，加上拉普拉斯平滑，计算对数概率，并保存类别先验（类别频率的对数）。

2. **predict_log_proba(X)**：对每个样本，为所有类别计算 log P(class) + 各特征 log P(feature_i | class) 之和。这是一次矩阵乘法：X @ log_probs.T + log_priors。

3. **predict(X)**：返回对数概率最高的类别。

```python
class MultinomialNB:
    def __init__(self, alpha=1.0):
        self.alpha = alpha

    def fit(self, X, y):
        classes = np.unique(y)
        n_classes = len(classes)
        n_features = X.shape[1]

        self.classes_ = classes
        self.class_log_prior_ = np.zeros(n_classes)
        self.feature_log_prob_ = np.zeros((n_classes, n_features))

        for i, c in enumerate(classes):
            X_c = X[y == c]
            self.class_log_prior_[i] = np.log(X_c.shape[0] / X.shape[0])
            counts = X_c.sum(axis=0) + self.alpha
            self.feature_log_prob_[i] = np.log(counts / counts.sum())

        return self
```

关键洞察：拟合完成之后，预测只是矩阵乘法加一个偏置。这就是朴素贝叶斯快的原因。

> 1. **fit(X, y)**: For each class, count the frequency of each feature. Add Laplace smoothing. Compute log probabilities. Store class priors (log of class frequencies).
> 2. **predict_log_proba(X)**: For each sample, compute log P(class) + sum of log P(feature_i | class) for all classes. This is a matrix multiplication: X @ log_probs.T + log_priors.
> 3. **predict(X)**: Return the class with highest log probability.
> The key insight: after fitting, prediction is just matrix multiplication plus a bias. This is why Naive Bayes is so fast.

### GaussianNB

对连续特征，我们为每个类别、每个特征估计均值和方差：

```python
class GaussianNB:
    def __init__(self):
        pass

    def fit(self, X, y):
        classes = np.unique(y)
        self.classes_ = classes
        self.means_ = np.zeros((len(classes), X.shape[1]))
        self.vars_ = np.zeros((len(classes), X.shape[1]))
        self.priors_ = np.zeros(len(classes))

        for i, c in enumerate(classes):
            X_c = X[y == c]
            self.means_[i] = X_c.mean(axis=0)
            self.vars_[i] = X_c.var(axis=0) + 1e-9
            self.priors_[i] = X_c.shape[0] / X.shape[0]

        return self
```

预测时对每个特征使用高斯概率密度函数（PDF），再跨特征相乘（在对数空间里相加）。

> For continuous features, we estimate mean and variance per class per feature.
> Prediction uses the Gaussian PDF per feature, multiplied across features (added in log space).

### Demo: Text Classification · 演示：文本分类

代码生成合成的词袋（bag-of-words）数据，模拟两个类别（科技文章 vs 体育文章），每个类别有不同的词频分布。MultinomialNB 用词计数对它们分类。

合成数据是这样构造的：创建 200 个「词」（特征列）。词 0-39 在科技文章中高频、在体育文章中低频；词 80-119 在体育文章中高频、在科技文章中低频；词 40-79 在两边都是中频。这样就造出了一个现实的场景：有些词是强的类别指示器，有些词是噪声。

> The code generates synthetic bag-of-words data simulating two classes (tech articles vs sports articles). Each class has a different word frequency distribution. MultinomialNB classifies them using word counts.
> The synthetic data works like this: we create 200 "words" (feature columns). Words 0-39 have high frequency in tech articles and low in sports. Words 80-119 have high frequency in sports and low in tech. Words 40-79 are medium frequency in both. This creates a realistic scenario where some words are strong class indicators and others are noise.

### Demo: Continuous Features · 演示：连续特征

代码生成类似鸢尾花（Iris）的数据（3 个类别、4 个特征、高斯簇）。GaussianNB 用逐类别的均值和方差分类。每个类别有不同的中心（均值向量）和不同的散布（方差），模拟真实世界中不同类别度量系统性不同的数据。

代码还演示了：
- **平滑对比：** 用不同 alpha 训练 MultinomialNB，展示平滑强度对准确率的影响。
- **训练规模实验：** 训练数据从 20 增长到 1600 个样本时 NB 准确率如何提升。样本非常少时 NB 就能达到不错的准确率——这是它的主要优势。
- **混淆矩阵：** 每个类别的精确率、召回率和 F1 分数，展示 NB 在哪里犯错。

> The code generates Iris-like data (3 classes, 4 features, Gaussian clusters). GaussianNB classifies using per-class mean and variance. Each class has a different center (mean vector) and different spread (variance), mimicking real-world data where measurements differ systematically between categories.
> The code also demonstrates: **Smoothing comparison:** training MultinomialNB with different alpha values to show the effect of smoothing strength on accuracy. **Training size experiment:** how NB accuracy improves as training data grows from 20 to 1600 samples -- NB reaches decent accuracy even with very few samples, which is its main advantage. **Confusion matrix:** per-class precision, recall, and F1 score to show where NB makes mistakes.

### Prediction Speed · 预测速度

朴素贝叶斯的预测就是一次矩阵乘法。对 n 个样本、d 个特征、k 个类别：
- MultinomialNB：一次矩阵乘法 (n x d) @ (d x k) = O(n * d * k)
- GaussianNB：n * k 次高斯 PDF 计算，每次遍历 d 个特征 = O(n * d * k)

两者在每个维度上都是线性的。对比 KNN（要对所有训练点计算距离）或带 RBF 核的 SVM（要对所有支持向量计算核函数），NB 在预测时快上若干个数量级。

> Naive Bayes prediction is a matrix multiplication. For n samples with d features and k classes:
> - MultinomialNB: one matrix multiply (n x d) @ (d x k) = O(n * d * k)
> - GaussianNB: n * k Gaussian PDF evaluations, each over d features = O(n * d * k)
> Both are linear in every dimension. Compare this to KNN (which requires distance computation to all training points) or SVM with RBF kernel (which requires kernel evaluation against all support vectors). NB is faster by orders of magnitude at prediction time.

## Use It · 实战用法

用 sklearn 的话，两个变体都是一行的事：

```python
from sklearn.naive_bayes import GaussianNB, MultinomialNB

gnb = GaussianNB()
gnb.fit(X_train, y_train)
print(f"GaussianNB accuracy: {gnb.score(X_test, y_test):.3f}")

mnb = MultinomialNB(alpha=1.0)
mnb.fit(X_train_counts, y_train)
print(f"MultinomialNB accuracy: {mnb.score(X_test_counts, y_test):.3f}")
```

用 sklearn 做文本分类：

```python
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

text_clf = Pipeline([
    ("vectorizer", CountVectorizer()),
    ("classifier", MultinomialNB(alpha=1.0)),
])

text_clf.fit(train_texts, train_labels)
accuracy = text_clf.score(test_texts, test_labels)
```

`naive_bayes.py` 中的代码会在同一份数据上把从零实现与 sklearn 对比，以验证正确性。

> With sklearn, both variants are one-liners.
> For text classification with sklearn:
> The code in `naive_bayes.py` compares from-scratch implementations against sklearn on the same data to verify correctness.

### TF-IDF with Naive Bayes · TF-IDF 配朴素贝叶斯

原始词计数让每个词的每次出现权重相同。但 "the"、"is" 这类常见词在每个类别里都高频——它们不携带信息。TF-IDF（Term Frequency - Inverse Document Frequency，词频-逆文档频率）压低常见词的权重，抬高稀少而有区分力的词。

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

text_clf = Pipeline([
    ("tfidf", TfidfVectorizer()),
    ("classifier", MultinomialNB(alpha=0.1)),
])
```

TF-IDF 值非负，所以能配合 MultinomialNB 使用。TF-IDF + MultinomialNB 是文本分类最强的基线之一，在训练样本少于 10,000 的数据集上经常击败更复杂的模型。

> Raw word counts give every word equal weight per occurrence. But common words like "the" and "is" appear frequently in every class -- they carry no information. TF-IDF (Term Frequency - Inverse Document Frequency) downweights common words and upweights rare, discriminative words.
> TF-IDF values are non-negative, so they work with MultinomialNB. The combination of TF-IDF + MultinomialNB is one of the strongest baselines for text classification. It frequently beats more complex models on datasets with fewer than 10,000 training samples.

### BernoulliNB for Short Text · 短文本用 BernoulliNB

对短文本（推文、短信、聊天消息），BernoulliNB 可能胜过 MultinomialNB。短文本的词数少，MultinomialNB 依赖的频率信息噪声很大。BernoulliNB 只关心词出现与否，这在短文本上更可靠。

```python
from sklearn.naive_bayes import BernoulliNB
from sklearn.feature_extraction.text import CountVectorizer

text_clf = Pipeline([
    ("vectorizer", CountVectorizer(binary=True)),
    ("classifier", BernoulliNB(alpha=1.0)),
])
```

CountVectorizer 的 `binary=True` 把所有计数变成 0/1。不加这个 flag，BernoulliNB 也能跑，但它看到的计数并不是它设计时所针对的东西。

> For short text (tweets, SMS, chat messages), BernoulliNB can outperform MultinomialNB. Short texts have low word counts, so the frequency information that MultinomialNB relies on is noisy. BernoulliNB only cares about presence or absence, which is more reliable with short text.
> The `binary=True` flag in CountVectorizer converts all counts to 0/1. Without it, BernoulliNB still works but is seeing counts that it was not designed for.

### Calibrating NB Probabilities · 校准 NB 概率

NB 的概率校准很差。当 NB 说 P(spam) = 0.95 时，真实概率可能是 0.7。如果你需要可靠的概率估计（比如设置阈值，或与其他模型组合），用 sklearn 的 CalibratedClassifierCV：

```python
from sklearn.calibration import CalibratedClassifierCV

calibrated_nb = CalibratedClassifierCV(MultinomialNB(), cv=5, method="sigmoid")
calibrated_nb.fit(X_train, y_train)
proba = calibrated_nb.predict_proba(X_test)
```

它在 NB 的原始分数之上，用交叉验证拟合一个逻辑回归。得到的概率会接近真实的类别频率。

> NB probabilities are poorly calibrated. When NB says P(spam) = 0.95, the true probability might be 0.7. If you need reliable probability estimates (for example, to set a threshold or to combine with other models), use sklearn's CalibratedClassifierCV.
> This fits a logistic regression on top of NB's raw scores using cross-validation. The resulting probabilities are much closer to the true class frequencies.

### Common Gotchas · 常见坑

1. **特征出现负值。** MultinomialNB 要求特征非负。如果有负值（比如某些设置下的 TF-IDF 或标准化后的特征），改用 GaussianNB，或者把特征平移成正值。

2. **零方差特征。** GaussianNB 要除以方差。如果某特征在某类别内方差为零（所有值相同），概率计算会崩。代码给所有方差加了一个小的平滑项（1e-9）来防止这一点。

3. **类别不平衡。** 如果 99% 的邮件不是垃圾，先验 P(not-spam) = 0.99 强到会压过似然证据。可以手动设置类别先验，或使用 sklearn 的 class_prior 参数。

4. **特征缩放。** MultinomialNB 不需要缩放（它处理的就是计数）。GaussianNB 也不需要（它自己估计逐特征统计量）。这是相对逻辑回归和 SVM 的一个优势——那两者对特征尺度敏感。

> 1. **Negative feature values.** MultinomialNB requires non-negative features. If you have negative values (like TF-IDF with certain settings or standardized features), use GaussianNB instead, or shift the features to be positive.
> 2. **Zero variance features.** GaussianNB divides by variance. If a feature has zero variance for a class (all values identical), the probability computation breaks. The code adds a small smoothing term (1e-9) to all variances to prevent this.
> 3. **Class imbalance.** If 99% of emails are not-spam, the prior P(not-spam) = 0.99 is so strong that it overwhelms the likelihood evidence. You can set class priors manually or use class_prior parameter in sklearn.
> 4. **Feature scaling.** MultinomialNB does not need scaling (it works on counts). GaussianNB does not need scaling either (it estimates per-feature statistics). This is an advantage over logistic regression and SVM, which are sensitive to feature scales.

## Ship It · 交付

本课产出：
- `outputs/skill-naive-bayes-chooser.md` —— 一个帮你选对 NB 变体的决策技能（skill）
- `code/naive_bayes.py` —— 从零实现的 MultinomialNB 与 GaussianNB，附 sklearn 对比

> This lesson produces:
> - `outputs/skill-naive-bayes-chooser.md` -- a decision skill for picking the right NB variant
> - `code/naive_bayes.py` -- MultinomialNB and GaussianNB from scratch, with sklearn comparison

### When Naive Bayes Fails · 朴素贝叶斯何时失效

当独立性假设导致排序错误（而不只是概率不准）时，NB 会失败。这发生在：

1. **强特征交互。** 如果类别取决于两个特征的组合而非任一单独特征（类似 XOR 的模式），NB 会完全漏掉。每个特征单独都不提供证据，而 NB 无法非线性地组合它们。

2. **高度相关且证据相反的特征。** 如果特征 A 说 "spam"，特征 B 说 "not-spam"，而 A 和 B 完全相关（现实中它们总是同进退），NB 会在本无冲突的地方看到冲突证据。

3. **训练集非常大。** 数据够多时，逻辑回归这类判别模型能学出真实决策边界并胜过 NB。小数据时帮了忙的独立性假设，这时开始拖后腿。

实践中，这些失败模式在文本分类里很少见。文本特征数量多、单个作用弱，独立性假设的误差往往会相互抵消。对特征少而强相关的表格数据，优先考虑逻辑回归或树模型。

> NB fails when the independence assumption causes incorrect rankings (not just incorrect probabilities). This happens when:
> 1. **Strong feature interactions.** If the class depends on the combination of two features but not either alone (XOR-like patterns), NB will miss it entirely. Each feature alone provides no evidence, and NB cannot combine them nonlinearly.
> ...
> 3. **Very large training sets.** With enough data, discriminative models like logistic regression learn the true decision boundary and outperform NB. The independence assumption that helped with small data now holds the model back.
> In practice, these failure modes are rare for text classification. For tabular data with few strongly correlated features, consider logistic regression or tree-based models first.

## Exercises · 练习

1. **平滑实验。** 在文本数据上用 alpha = 0.01、0.1、1.0、10.0、100.0 训练 MultinomialNB。画出准确率随 alpha 变化的曲线。性能在哪里到达峰值？为什么 alpha 特别大反而变差？

2. **特征独立性检验。** 拿一个真实文本数据集，挑两个明显相关的词（"machine" 和 "learning"）。计算 P(word1 | class) * P(word2 | class)，与 P(word1 AND word2 | class) 比较。独立性假设错得有多离谱？它影响分类准确率吗？

3. **实现 Bernoulli。** 给代码扩展一个 BernoulliNB 类。把词袋转成二值（出现/缺席），在文本数据上与 MultinomialNB 比较准确率。Bernoulli 什么时候赢？

4. **NB vs 逻辑回归。** 在文本数据上两个都训练。从 100 个训练样本起步，增加到 10,000。画出两者准确率随训练集大小变化的曲线。逻辑回归在哪个点反超朴素贝叶斯？

5. **垃圾邮件过滤器。** 做一个完整的垃圾邮件分类器：对原始邮件文本分词、建词表、构造词袋特征、训练 MultinomialNB、用精确率和召回率评估（而不只是准确率——为什么？）。

> **Smoothing experiment.** Train MultinomialNB on text data with alpha values of 0.01, 0.1, 1.0, 10.0, and 100.0. Plot accuracy vs alpha. Where does performance peak? Why does very high alpha hurt?
> ...
> **Spam filter.** Build a complete spam classifier: tokenize raw email text, build vocabulary, create bag-of-words features, train MultinomialNB, evaluate with precision and recall (not just accuracy -- why?).

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|---------|---------|
| Naive Bayes | "简单的概率分类器" | 应用贝叶斯定理、并假设特征在给定类别下条件独立的分类器 |
| Conditional independence | "特征互不影响" | P(A, B \| C) = P(A \| C) * P(B \| C)——知道 C 之后，再知道 B 对了解 A 不提供新信息 |
| Laplace smoothing | "加一平滑" | 给每个特征计数加一个小量，防止零概率主宰预测 |
| Prior | "看数据之前的信念" | P(class)——观察到任何特征之前每个类别的概率 |
| Likelihood | "数据和假设的吻合程度" | P(features \| class)——已知类别时观察到这些特征的概率 |
| Posterior | "看数据之后更新的信念" | P(class \| features)——观察到特征之后类别被更新的概率 |
| Generative model | "建模数据如何生成" | 先学 P(X \| Y) 和 P(Y)、再用贝叶斯定理得到 P(Y \| X) 的模型 |
| Discriminative model | "直接建模决策边界" | 不建模 X 如何生成、直接学习 P(Y \| X) 的模型 |
| Log probability | "避免下溢" | 用 log P 代替 P 计算，防止许多小数的乘积在浮点里变成零 |

> Naive Bayes | "Simple probabilistic classifier" | A classifier that applies Bayes' theorem with the assumption that features are conditionally independent given the class
> Laplace smoothing | "Add-one smoothing" | Adding a small count to every feature to prevent zero probabilities from dominating the prediction
> Generative model | "Models how data is generated" | A model that learns P(X \| Y) and P(Y), then uses Bayes' theorem to get P(Y \| X)

## Further Reading · 延伸阅读

- [scikit-learn Naive Bayes docs](https://scikit-learn.org/stable/modules/naive_bayes.html) —— 三种变体及其数学细节
- [McCallum and Nigam, A Comparison of Event Models for Naive Bayes Text Classification (1998)](https://www.cs.cmu.edu/~knigam/papers/multinomial-aaaiws98.pdf) —— Multinomial 与 Bernoulli 在文本上对比的经典文献
- [Rennie et al., Tackling the Poor Assumptions of Naive Bayes Text Classifiers (2003)](https://people.csail.mit.edu/jrennie/papers/icml03-nb.pdf) —— 针对文本场景改进 NB
- [Ng and Jordan, On Discriminative vs. Generative Classifiers (2001)](https://ai.stanford.edu/~ang/papers/nips01-discriminativegenerative.pdf) —— 证明数据较少时 NB 比 LR 收敛更快
