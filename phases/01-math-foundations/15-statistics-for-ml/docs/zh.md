# Statistics for Machine Learning · 机器学习统计

> 统计学就是你判断一个模型是真的有效，还是只是运气好。
>
> Statistics is how you know if your model actually works or just got lucky.

**Type:** Build
**Language:** Python
**Prerequisites:** Phase 1, Lessons 06 (Probability and Distributions), 07 (Bayes' Theorem)
**Time:** ~120 minutes

## Learning Objectives · 学习目标

- 从零实现描述性统计、Pearson/Spearman 相关系数和协方差矩阵
- 执行假设检验（t 检验、卡方检验），并正确解读 p 值和置信区间
- 用 bootstrap 重采样为任意指标构建置信区间，不需要任何分布假设
- 用效应量（effect size）区分统计显著性与实际显著性

> Compute descriptive statistics, Pearson/Spearman correlation, and covariance matrices from scratch
> Perform hypothesis tests (t-test, chi-squared) and interpret p-values and confidence intervals correctly
> Use bootstrap resampling to construct confidence intervals for any metric without distributional assumptions
> Distinguish statistical significance from practical significance using effect size measures

## The Problem · 问题在哪

你训练了两个模型。模型 A 在你的测试集上得 0.87，模型 B 得 0.89。你上线了模型 B。三周之后，生产指标比之前更差了。发生了什么？

模型 B 其实并没有跑赢模型 A。那 0.02 的差距是噪声。你的测试集太小，或者方差太高，或者两者兼有。你把伪装成提升的随机性发布上线了。

这种事一直在发生。Kaggle 排行榜上的名次洗牌、无法复现的论文、仅凭几百个样本就宣布获胜者的 A/B 测试。根本原因从来都是同一个：有人跳过了统计学。

统计学给你一套区分信号与噪声的工具。它告诉你一个差异什么时候是真的、你应该有多确信、以及需要多少数据才能相信一个结论。每一条 ML 流水线、每一次模型对比、每一个实验都需要统计学。没有它，你就是在瞎猜。

> You trained two models. Model A scores 0.87 on your test set. Model B scores 0.89. You deploy Model B. Three weeks later, production metrics are worse than before. What happened?
> Model B did not actually outperform Model A. The 0.02 difference was noise. Your test set was too small, or the variance too high, or both. You shipped randomness dressed up as improvement.
> This happens constantly. Kaggle leaderboard shakeups. Papers that fail to reproduce. A/B tests that declare winners based on a few hundred samples. The root cause is always the same: someone skipped the statistics.
> Statistics gives you the tools to distinguish signal from noise. It tells you when a difference is real, how confident you should be, and how much data you need before you can trust a result. ... Without it, you are guessing.

## The Concept · 概念

### Descriptive Statistics: Summarizing Your Data · 描述性统计：概括你的数据

在建模任何东西之前，你需要知道你的数据长什么样。描述性统计把数据集压缩成少数几个能刻画其形态的数字。

**集中趋势（central tendency）** 回答「中间在哪？」

```
Mean:   sum of all values / count
        mu = (1/n) * sum(x_i)

Median: middle value when sorted
        Robust to outliers. If you have [1, 2, 3, 4, 1000], the mean is 202
        but the median is 3.

Mode:   most frequent value
        Useful for categorical data. For continuous data, rarely informative.
```

均值是平衡点，中位数是中点标记。当两者背离时，说明你的分布是有偏的。收入分布的均值 >> 中位数（亿万富翁造成的右偏）。训练过程中的 loss 分布常常均值 << 中位数（简单样本造成的左偏）。

**离散程度（spread）** 回答「数据有多分散？」

```
Variance:   average squared deviation from the mean
            sigma^2 = (1/n) * sum((x_i - mu)^2)

Standard deviation:  square root of variance
                     sigma = sqrt(sigma^2)
                     Same units as the data, so more interpretable.

Range:      max - min
            Sensitive to outliers. Almost never useful alone.

IQR:        Q3 - Q1 (interquartile range)
            The range of the middle 50% of the data.
            Robust to outliers. Used for box plots and outlier detection.
```

**百分位数（percentile）** 把排序后的数据分成 100 等份。第 25 百分位数（Q1）表示有 25% 的值落在这个点以下。第 50 百分位数就是中位数。第 75 百分位数是 Q3。

```
For latency monitoring:
  P50 = median latency        (typical user experience)
  P95 = 95th percentile       (bad but not worst case)
  P99 = 99th percentile       (tail latency, often 10x the median)
```

在 ML 里，你在推理延迟、预测置信度分布以及理解误差分布时会关心百分位数。一个平均误差很低但 P99 误差很糟糕的模型，对安全攸关的应用来说可能毫无用处。

**样本统计 vs 总体统计。** 从样本计算方差时要除以 (n-1) 而不是 n。这就是 Bessel 修正（Bessel's correction）。它补偿的事实是：你的样本均值并不等于真实的总体均值。分母用 n 会系统性地低估真实方差；用 (n-1) 得到的估计才是无偏的。

```
Population variance: sigma^2 = (1/N) * sum((x_i - mu)^2)
Sample variance:     s^2     = (1/(n-1)) * sum((x_i - x_bar)^2)
```

实践中的判断：如果 n 很大（几千个样本），差异可以忽略。如果 n 很小（几十个样本），它就有影响。

> Before you model anything, you need to know what your data looks like. Descriptive statistics compress a dataset into a few numbers that capture its shape.
> The mean is the balance point. The median is the halfway mark. When they diverge, your distribution is skewed.
> When computing variance from a sample, divide by (n-1) instead of n. This is Bessel's correction. ... With n in the denominator, you systematically underestimate the true variance. With (n-1), the estimate is unbiased.
> In practice: if n is large (thousands of samples), the difference is negligible. If n is small (dozens of samples), it matters.

### Correlation: How Variables Move Together · 相关性：变量如何联动

相关性衡量两个变量之间线性关系的强度和方向。

**Pearson 相关系数（Pearson correlation coefficient）** 衡量线性关联：

```
r = sum((x_i - x_bar)(y_i - y_bar)) / (n * s_x * s_y)

r = +1:  perfect positive linear relationship
r = -1:  perfect negative linear relationship
r =  0:  no linear relationship (but there might be a nonlinear one!)

Range: [-1, 1]
```

Pearson 假设关系是线性的，且两个变量都近似服从正态分布。它对异常值敏感。单单一个极端点就能把 r 从 0.1 拖到 0.9。

**Spearman 秩相关（Spearman rank correlation）** 衡量单调关联：

```
1. Replace each value with its rank (1, 2, 3, ...)
2. Compute Pearson correlation on the ranks

Spearman catches any monotonic relationship, not just linear.
If y = x^3, Pearson gives r < 1 but Spearman gives rho = 1.
```

**各自该什么时候用：**

```
Pearson:    Both variables are continuous and roughly normal.
            You care about the linear relationship specifically.
            No extreme outliers.

Spearman:   Ordinal data (rankings, ratings).
            Data is not normally distributed.
            You suspect a monotonic but not linear relationship.
            Outliers are present.
```

**黄金法则：** 相关不等于因果（correlation does not imply causation）。冰淇淋销量和溺水死亡人数是相关的，因为两者都在夏天上升。你模型的准确率和参数数量是相关的，但增加参数并不会自动提升准确率（参见：过拟合）。

> Correlation measures the strength and direction of a linear relationship between two variables.
> Pearson assumes the relationship is linear and both variables are roughly normally distributed. It is sensitive to outliers. A single extreme point can drag r from 0.1 to 0.9.
> Spearman rank correlation measures monotonic association.
> The golden rule: correlation does not imply causation. Ice cream sales and drowning deaths are correlated because both increase in summer. ... Your model's accuracy and the number of parameters are correlated, but adding parameters does not automatically improve accuracy (see: overfitting).

### Covariance Matrix · 协方差矩阵

两个变量之间的协方差衡量它们如何共同变化：

```
Cov(X, Y) = (1/n) * sum((x_i - x_bar)(y_i - y_bar))

Cov(X, Y) > 0:  X and Y tend to increase together
Cov(X, Y) < 0:  when X increases, Y tends to decrease
Cov(X, Y) = 0:  no linear co-movement
```

对 d 个特征，协方差矩阵 C 是一个 d x d 矩阵，其中 C[i][j] = Cov(feature_i, feature_j)。对角线元素 C[i][i] 是每个特征的方差。

```
C = | Var(x1)      Cov(x1,x2)  Cov(x1,x3) |
    | Cov(x2,x1)  Var(x2)      Cov(x2,x3) |
    | Cov(x3,x1)  Cov(x3,x2)  Var(x3)     |

Properties:
  - Symmetric: C[i][j] = C[j][i]
  - Positive semi-definite: all eigenvalues >= 0
  - Diagonal = variances
  - Off-diagonal = covariances
```

**与 PCA 的联系。** PCA 对协方差矩阵做特征分解。特征向量就是主成分（方差最大的方向），特征值告诉你每个成分捕获了多少方差。这正是第 10 课讲过的内容，但现在你能看清为什么协方差矩阵才是该被分解的东西：它编码了你数据中所有两两之间的线性关系。

**与相关性的联系。** 相关矩阵就是标准化变量（各自除以自己的标准差）的协方差矩阵。相关性把协方差归一化，使所有值都落在 [-1, 1]。

> The covariance between two variables measures how they vary together:
> For d features, the covariance matrix C is a d x d matrix where C[i][j] = Cov(feature_i, feature_j). The diagonal entries C[i][i] are the variances of each feature.
> PCA eigendecomposes the covariance matrix. ... This is exactly what Lesson 10 covered, but now you see why the covariance matrix is the right thing to decompose: it encodes all pairwise linear relationships in your data.
> The correlation matrix is the covariance matrix of standardized variables (each divided by its standard deviation). Correlation normalizes covariance so all values fall in [-1, 1].

### Hypothesis Testing · 假设检验

假设检验是一套在不确定性下做决策的框架。你从一个断言出发，收集数据，然后判断数据与该断言是否一致。

**基本设定：**

```
Null hypothesis (H0):        the default assumption, usually "no effect"
Alternative hypothesis (H1): what you are trying to show

Example:
  H0: Model A and Model B have the same accuracy
  H1: Model B has higher accuracy than Model A
```

**p 值（p-value）** 是在假设 H0 为真的前提下，看到与你观察到的数据一样极端的数据的概率。它不是「H0 为真的概率」。这是统计学里最常见的一种误解，没有之一。

```
p-value = P(data this extreme | H0 is true)

If p-value < alpha (typically 0.05):
    Reject H0. The result is "statistically significant."
If p-value >= alpha:
    Fail to reject H0. You do not have enough evidence.
    This does NOT mean H0 is true.
```

**置信区间（confidence interval）** 给出参数的一个合理取值范围：

```
95% confidence interval for the mean:
    x_bar +/- z * (s / sqrt(n))

where z = 1.96 for 95% confidence

Interpretation: if you repeated this experiment many times, 95% of the
computed intervals would contain the true mean. It does NOT mean there
is a 95% probability the true mean is in this specific interval.
```

置信区间的宽度告诉你估计的精度。宽区间意味着高不确定性。窄区间意味着你的估计是精确的（但如果数据本身有偏，未必是准确的）。

> Hypothesis testing is a framework for making decisions under uncertainty. You start with a claim, collect data, and determine if the data is consistent with the claim.
> The p-value is the probability of seeing data as extreme as what you observed, assuming H0 is true. It is NOT the probability that H0 is true. This is the single most common misunderstanding in statistics.
> Confidence intervals give a range of plausible values for a parameter.
> The width of the confidence interval tells you about precision. Wide intervals mean high uncertainty. Narrow intervals mean your estimate is precise (but not necessarily accurate, if your data is biased).

### The t-test · t 检验

t 检验比较均值。它有几种变体。

**单样本 t 检验（one-sample t-test）：** 总体均值是否不同于某个假设值？

```
t = (x_bar - mu_0) / (s / sqrt(n))

degrees of freedom = n - 1
```

**双样本 t 检验（独立样本）：** 两组的均值是否不同？

```
t = (x_bar_1 - x_bar_2) / sqrt(s1^2/n1 + s2^2/n2)

This is Welch's t-test, which does not assume equal variances.
Always use Welch's unless you have a specific reason for equal variances.
```

**配对 t 检验（paired t-test）：** 当测量成对出现时（同一个模型在相同的数据划分上评估）：

```
Compute d_i = x_i - y_i for each pair
Then run a one-sample t-test on the d_i values against mu_0 = 0
```

在 ML 里，配对 t 检验很常见：你让两个模型跑相同的 10 个交叉验证折，然后逐对比较它们的分数。

> The t-test compares means. There are several flavors.
> In ML, the paired t-test is common: you run both models on the same 10 cross-validation folds and compare their scores pairwise.

### Chi-squared Test · 卡方检验

卡方检验检查观察频数是否匹配期望频数。对分类数据很有用。

```
chi^2 = sum((observed - expected)^2 / expected)

Example: does a language model's output distribution match the
training distribution across categories?

Category    Observed   Expected
Positive       120        100
Negative        80        100
chi^2 = (120-100)^2/100 + (80-100)^2/100 = 4 + 4 = 8

With 1 degree of freedom, chi^2 = 8 gives p < 0.005.
The difference is significant.
```

> The chi-squared test checks if observed frequencies match expected frequencies. Useful for categorical data.

### A/B Testing for ML Models · ML 模型的 A/B 测试

ML 里的 A/B 测试不同于网页 A/B 测试。模型对比有一系列特有的挑战：

```
1. Same test set:    Both models must be evaluated on identical data.
                     Different test sets make comparison meaningless.

2. Multiple metrics: Accuracy alone is not enough. You need precision,
                     recall, F1, latency, and fairness metrics.

3. Variance:         Use cross-validation or bootstrap to estimate
                     the variance of each metric, not just point estimates.

4. Data leakage:     If the test set was used during model selection,
                     your comparison is biased. Hold out a final test set.
```

**操作流程：**

```
1. Define your metric and significance level (alpha = 0.05)
2. Run both models on the same k-fold cross-validation splits
3. Collect paired scores: [(a1, b1), (a2, b2), ..., (ak, bk)]
4. Compute differences: d_i = b_i - a_i
5. Run a paired t-test on the differences
6. Check: is the mean difference significantly different from 0?
7. Compute a confidence interval for the mean difference
8. Compute effect size (Cohen's d) to judge practical significance
```

> A/B testing in ML is not the same as web A/B testing. Model comparison has specific challenges.

### Statistical Significance vs Practical Significance · 统计显著 vs 实际显著

一个结果可以统计显著但实际毫无意义。只要数据足够多，再微不足道的差异也会变得统计显著。

```
Example:
  Model A accuracy: 0.9234
  Model B accuracy: 0.9237
  n = 1,000,000 test samples
  p-value = 0.001

Statistically significant? Yes.
Practically significant? A 0.03% improvement is not worth the
engineering cost of deploying a new model.
```

**效应量（effect size）** 在不受样本量影响的前提下量化差异有多大：

```
Cohen's d = (mean_1 - mean_2) / pooled_std

d = 0.2:  small effect
d = 0.5:  medium effect
d = 0.8:  large effect
```

永远同时报告 p 值和效应量。p 值告诉你差异是否真实存在，效应量告诉你这个差异重不重要。

> A result can be statistically significant but practically meaningless. With enough data, even a trivial difference becomes statistically significant.
> Effect size quantifies how big the difference is, independent of sample size.
> Always report both the p-value and the effect size. The p-value tells you if the difference is real. The effect size tells you if it matters.

### Multiple Comparison Problem · 多重比较问题

当你检验很多个假设时，总有一些会「碰巧」显著。如果你在 alpha = 0.05 下检验 20 件事，即使什么都不是真的，你也会预期得到 1 个假阳性（false positive）。

```
P(at least one false positive) = 1 - (1 - alpha)^m

m = 20 tests, alpha = 0.05:
P(false positive) = 1 - 0.95^20 = 0.64

You have a 64% chance of at least one false positive.
```

**Bonferroni 修正（Bonferroni correction）：** 把 alpha 除以检验次数。

```
Adjusted alpha = alpha / m = 0.05 / 20 = 0.0025

Only reject H0 if p-value < 0.0025.
Conservative but simple. Works when tests are independent.
```

在 ML 里，当你跨多个指标比较一个模型、测试大量超参数配置、或在多个数据集上做评估时，这个问题就会浮现。

> When you test many hypotheses, some will be "significant" by chance. If you test 20 things at alpha = 0.05, you expect 1 false positive even when nothing is real.
> Bonferroni correction: divide alpha by the number of tests.
> In ML, this matters when you compare a model across multiple metrics, test many hyperparameter configurations, or evaluate on multiple datasets.

### Bootstrap Methods · Bootstrap 方法

Bootstrapping 通过对你的数据有放回地重采样来估计一个统计量（statistic）的抽样分布。不需要对底层分布做任何假设。

**算法：**

```
1. You have n data points
2. Draw n samples WITH replacement (some points appear multiple times,
   some not at all)
3. Compute your statistic on this bootstrap sample
4. Repeat B times (typically B = 1000 to 10000)
5. The distribution of bootstrap statistics approximates the
   sampling distribution
```

**Bootstrap 置信区间（百分位法）：**

```
Sort the B bootstrap statistics
95% CI = [2.5th percentile, 97.5th percentile]
```

**Bootstrap 为什么对 ML 重要：**

```
- Test set accuracy is a point estimate. Bootstrap gives you
  confidence intervals.
- You cannot assume metric distributions are normal (especially
  for AUC, F1, precision at k).
- Bootstrap works for ANY statistic: median, ratio of two means,
  difference in AUC between two models.
- No closed-form formula needed.
```

**用于模型比较的 bootstrap：**

```
1. You have predictions from Model A and Model B on the same test set
2. For each bootstrap iteration:
   a. Resample test indices with replacement
   b. Compute metric_A and metric_B on the resampled set
   c. Store diff = metric_B - metric_A
3. 95% CI for the difference:
   [2.5th percentile of diffs, 97.5th percentile of diffs]
4. If the CI does not contain 0, the difference is significant
```

这比配对 t 检验更稳健，因为它不做任何分布假设。

> Bootstrapping estimates the sampling distribution of a statistic by resampling your data with replacement. No assumptions about the underlying distribution required.
> This is more robust than the paired t-test because it makes no distributional assumptions.

### Parametric vs Non-parametric Tests · 参数检验 vs 非参数检验

**参数检验（parametric tests）** 假设数据服从某个特定分布（通常是正态分布）：

```
t-test:         assumes normally distributed data (or large n by CLT)
ANOVA:          assumes normality and equal variances
Pearson r:      assumes bivariate normality
```

**非参数检验（non-parametric tests）** 不做任何分布假设：

```
Mann-Whitney U:     compares two groups (replaces independent t-test)
Wilcoxon signed-rank: compares paired data (replaces paired t-test)
Spearman rho:       correlation on ranks (replaces Pearson)
Kruskal-Wallis:     compares multiple groups (replaces ANOVA)
```

**什么时候用非参数检验：**

```
- Small sample size (n < 30) and data is clearly non-normal
- Ordinal data (ratings, rankings)
- Heavy outliers you cannot remove
- Skewed distributions
```

**什么时候用参数检验：**

```
- Large sample size (CLT makes the test statistic approximately normal)
- Data is roughly symmetric without extreme outliers
- More statistical power (better at detecting real differences)
```

在 ML 实验中，你的 n 通常很小（5 或 10 个交叉验证折），所以 Wilcoxon signed-rank 这类非参数检验往往比 t 检验更合适。

> Parametric tests assume a specific distribution (usually normal):
> Non-parametric tests make no distributional assumptions:
> In ML experiments, you typically have small n (5 or 10 cross-validation folds), so non-parametric tests like Wilcoxon signed-rank are often more appropriate than t-tests.

### Central Limit Theorem: Practical Implications · 中心极限定理：实际意义

中心极限定理（CLT，central limit theorem）说：随着 n 增大，样本均值的分布趋近正态分布，不管底层总体分布是什么。

```
If X_1, X_2, ..., X_n are iid with mean mu and variance sigma^2:

    X_bar ~ Normal(mu, sigma^2 / n)    as n -> infinity

Works for n >= 30 in most cases.
For highly skewed distributions, you might need n >= 100.
```

**这对 ML 为什么重要：**

```
1. Justifies confidence intervals and t-tests on aggregated metrics
2. Explains why averaging over cross-validation folds gives stable
   estimates even when individual folds vary wildly
3. Mini-batch gradient descent works because the average gradient
   over a batch approximates the true gradient (CLT in action)
4. Ensemble methods: averaging predictions from many models gives
   more stable output than any single model
```

**CLT 做不到的事：**

```
- Does NOT make your data normal. It makes the MEAN of samples normal.
- Does NOT work for heavy-tailed distributions with infinite variance
  (Cauchy distribution).
- Does NOT apply to dependent data (time series without correction).
```

> The CLT says the distribution of sample means approaches a normal distribution as n grows, regardless of the underlying population distribution.
> What CLT does NOT do:
> Does NOT make your data normal. It makes the MEAN of samples normal. Does NOT work for heavy-tailed distributions with infinite variance (Cauchy distribution). Does NOT apply to dependent data (time series without correction).

### Common Statistical Mistakes in ML Papers · ML 论文中常见的统计错误

1. **在训练集上测试。** 必然过拟合。永远保留一批模型在训练期间从未见过的数据。

2. **不给置信区间。** 只报告一个不带不确定性的准确率数字，会让结果既无法复现也无法验证。

3. **忽略多重比较。** 测试 50 个配置然后不加修正地报告最好的那个，会夸大假阳性率。

4. **混淆统计显著与实际显著。** 0.01% 的准确率提升配一个 0.001 的 p 值，并没有意义。

5. **在不平衡数据上用准确率。** 在一个 99% 都是负样本的数据集上拿到 99% 准确率，说明模型什么都没学到。请用 precision、recall、F1 或 AUC。

6. **挑好看的指标（cherry-picking）。** 只报告你的模型赢的那一个指标。诚实的评估会报告所有相关指标。

7. **在训练/测试划分之间泄漏信息。** 先归一化再划分，或者用未来的数据预测过去。

8. **测试集很小又不给方差估计。** 在 100 个样本上评估然后宣称 2% 的提升，那是噪声，不是信号。

9. **在数据不独立时假设它们独立。** 同一位病人的多张医学影像、同一篇文档里的多个句子。同一组内的观测是彼此相关的。

10. **p 值黑客（P-hacking）。** 不断尝试不同的检验、子集或排除标准，直到拿到 p < 0.05。这样得到的结果是搜索过程的产物，不是发现。

> Testing on the training set. Guarantees overfitting. Always hold out data the model never sees during training.
> No confidence intervals. Reporting a single accuracy number without uncertainty makes results unreproducible and unverifiable.
> Ignoring multiple comparisons. Testing 50 configurations and reporting the best one without correction inflates false positive rates.
> P-hacking. Trying different tests, subsets, or exclusion criteria until you get p < 0.05. The result is an artifact of the search.

## Building It · 动手实现

你将实现：

1. **从零实现描述性统计**（均值、中位数、众数、标准差、百分位数、IQR）
2. **相关函数**（Pearson 和 Spearman，以及协方差矩阵）
3. **假设检验**（单样本 t 检验、双样本 t 检验、卡方检验）
4. **Bootstrap 置信区间**（对任意统计量都适用，不需要任何假设）
5. **A/B 测试模拟器**（生成数据、做检验、检查第一类错误和第二类错误）
6. **统计显著 vs 实际显著演示**（展示大 n 如何让一切都变得「显著」）

全部从零实现，只用 `math` 和 `random`。不用 numpy，不用 scipy。

```figure
f3-bootstrap-resample
```

> You will implement:
> 1. Descriptive statistics from scratch (mean, median, mode, standard deviation, percentiles, IQR)
> 2. Correlation functions (Pearson and Spearman, with the covariance matrix)
> 3. Hypothesis tests (one-sample t-test, two-sample t-test, chi-squared test)
> 4. Bootstrap confidence intervals (for any statistic, no assumptions needed)
> 5. A/B test simulator (generate data, test, check for Type I and Type II errors)
> 6. Statistical vs practical significance demo (showing that large n makes everything "significant")
> All from scratch, using only `math` and `random`. No numpy, no scipy.

## Key Terms · 术语表

| 术语 | 定义 |
|---|---|
| 均值（Mean） | 所有值之和除以个数。对异常值敏感。 |
| 中位数（Median） | 排序后数据的中间值。对异常值稳健。 |
| 标准差（Standard deviation） | 方差的平方根。用原始单位衡量离散程度。 |
| 百分位数（Percentile） | 一定百分比的数据落在其下的那个值。 |
| IQR | 四分位距。Q3 减 Q1。中间 50% 数据的跨度。 |
| Pearson 相关（Pearson correlation） | 衡量两个变量之间的线性关联。范围 [-1, 1]。 |
| Spearman 相关（Spearman correlation） | 用秩衡量单调关联。 |
| 协方差矩阵（Covariance matrix） | 所有特征两两之间协方差构成的矩阵。 |
| 零假设（Null hypothesis） | 「无效应或无差异」的默认假设。 |
| p 值（p-value） | 在零假设为真的前提下，出现如此极端数据的概率。 |
| 置信区间（Confidence interval） | 在给定置信水平下，参数的合理取值范围。 |
| t 检验（t-test） | 检验均值是否显著不同。使用 t 分布。 |
| 卡方检验（Chi-squared test） | 检验观察频数是否偏离期望频数。 |
| 效应量（Effect size） | 差异的大小，与样本量无关。常用 Cohen's d。 |
| Bonferroni 修正（Bonferroni correction） | 把显著性阈值除以检验次数来控制假阳性。 |
| Bootstrap | 有放回地重采样以估计抽样分布。 |
| 第一类错误（Type I error） | 假阳性。H0 为真却拒绝了它。 |
| 第二类错误（Type II error） | 假阴性。H0 为假却未能拒绝它。 |
| 统计功效（Statistical power） | 正确拒绝一个错误的 H0 的概率。功效 = 1 减第二类错误率。 |
| 中心极限定理（Central limit theorem） | 随样本量增大，样本均值收敛于正态分布。 |
| 参数检验（Parametric test） | 假设数据服从某个特定分布（通常是正态分布）。 |
| 非参数检验（Non-parametric test） | 不做分布假设。基于秩或符号工作。 |
