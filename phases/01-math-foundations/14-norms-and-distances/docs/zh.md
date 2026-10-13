# Norms and Distances · 范数与距离

> 你的距离函数定义了什么算「相似」。选错了，下游的一切都会崩塌。
>
> Your distance function defines what "similar" means. Choose wrong and everything downstream breaks.

**Type:** 构建（Build）
**Language:** Python
**Prerequisites:** Phase 1, Lessons 01 (Linear Algebra Intuition), 02 (Vectors, Matrices & Operations)
**Time:** 约 90 分钟

## Learning Objectives · 学习目标

- 从零实现 L1、L2、余弦（cosine）、马氏（Mahalanobis）、Jaccard 和编辑距离（edit distance）函数
- 为给定的 ML 任务选择合适的距离度量，并解释其他选择为何失败
- 把 L1、L2 范数与 LASSO、Ridge 正则化及其几何约束区域联系起来
- 演示同一数据集在不同度量下如何产生不同的最近邻

> Implement L1, L2, cosine, Mahalanobis, Jaccard, and edit distance functions from scratch
> Select the appropriate distance metric for a given ML task and explain why alternatives fail
> Connect L1 and L2 norms to LASSO and Ridge regularization and their geometric constraint regions
> Demonstrate how the same dataset produces different nearest neighbors under different metrics

## The Problem · 问题在哪

你有两个向量。也许它们是词嵌入（word embeddings），也许是用户画像，也许是像素数组。你需要知道：它们有多接近？

答案完全取决于你选了哪个距离函数。两个数据点在一种度量下是最近邻，在另一种度量下却相距甚远。你的 KNN 分类器、你的推荐引擎、你的向量数据库、你的聚类算法、你的损失函数——全都依赖这个选择。选错了，你的模型就在为错误的目标做优化。

没有普适的最佳距离。L2 适合空间数据。余弦相似度统治 NLP。Jaccard 处理集合。编辑距离处理字符串。马氏距离考虑相关性。Wasserstein 搬运概率质量。每一种都编码了关于「相似意味着什么」的不同假设。

本课从零构建每一个主流距离函数，告诉你每个函数何时是正确的工具，并演示同样的数据在不同度量下如何产生完全不同的最近邻。

> You have two vectors. Maybe they are word embeddings. Maybe they are user profiles. Maybe they are pixel arrays. You need to know: how close are they? ... The answer depends entirely on which distance function you pick. Two data points can be nearest neighbors under one metric and far apart under another. ... There is no universal best distance. ... This lesson builds every major distance function from scratch, shows you when each one is the right tool, and demonstrates how the same data produces completely different nearest neighbors depending on which metric you use.

## The Concept · 概念

### Norms: measuring vector magnitude · 范数：度量向量的大小

范数（norm）度量一个向量的「大小」。两个向量之间的任何距离函数都可以写成它们之差的范数：d(a, b) = ||a - b||。所以理解范数就是理解距离。

> A norm measures the "size" of a vector. Every distance function between two vectors can be written as the norm of their difference: d(a, b) = ||a - b||. So understanding norms is understanding distances.

### L1 Norm (Manhattan distance) · L1 范数（曼哈顿距离）

L1 范数把所有分量的绝对值求和。

```
||x||_1 = |x_1| + |x_2| + ... + |x_n|
```

它叫曼哈顿距离，因为度量的是你在城市街区里只能沿轴向走时的步行距离。不能走对角线。

```
Point A = (1, 1)
Point B = (4, 5)

L1 distance = |4-1| + |5-1| = 3 + 4 = 7

On a grid, you walk 3 blocks east and 4 blocks north.
```

何时用 L1：

- 高维稀疏数据（文本特征、one-hot 编码）
- 想要对离群点稳健时（单个巨大的差不会主导结果）
- 特征选择问题（L1 正则化促进稀疏性）

与 L1 正则化（Lasso）的联系：在损失函数里加上 ||w||_1 会惩罚权重的绝对值之和。这会把小权重推向恰好为零，实现自动特征选择。L1 惩罚在权重空间里形成菱形约束区域，而菱形的角正好落在某些权重为零的坐标轴上。

与损失函数的联系：平均绝对误差（MAE）就是预测与目标之间的平均 L1 距离。它对所有误差做线性惩罚，因此比 MSE 对离群点更稳健。

> The L1 norm sums the absolute values of all components. ... It is called Manhattan distance because it measures how far you walk on a city grid where you can only move along axes. No diagonals. ... Connection to L1 regularization (Lasso): adding ||w||_1 to your loss function penalizes the sum of absolute weight values. ... Connection to loss functions: Mean Absolute Error (MAE) is the average L1 distance between predictions and targets. It penalizes all errors linearly, making it robust to outliers compared to MSE.

### L2 Norm (Euclidean distance) · L2 范数（欧几里得距离）

L2 范数是直线距离。分量平方和的平方根。

```
||x||_2 = sqrt(x_1^2 + x_2^2 + ... + x_n^2)
```

这是你在几何课上学过的距离。n 维空间里的毕达哥拉斯定理。

```
Point A = (1, 1)
Point B = (4, 5)

L2 distance = sqrt((4-1)^2 + (5-1)^2) = sqrt(9 + 16) = sqrt(25) = 5.0

The straight line, cutting diagonally through the grid.
```

何时用 L2：

- 低到中维的连续数据
- 特征尺度相近时
- 物理距离（空间数据、传感器读数）
- 像素级的图像相似度

与 L2 正则化（Ridge）的联系：在损失函数里加上 ||w||_2^2 会惩罚大权重。与 L1 不同，它不把权重推向零，而是成比例地把所有权重向零收缩。L2 惩罚形成圆形约束区域，轴上没有角点。权重会变小，但很少恰好为零。

与损失函数的联系：均方误差（MSE）是 L2 距离平方的平均。平方运算让大误差受到的惩罚远重于小误差。

```
MAE (L1 loss):  |y - y_hat|         Linear penalty. Robust to outliers.
MSE (L2 loss):  (y - y_hat)^2       Quadratic penalty. Sensitive to outliers.
```

> The L2 norm is the straight-line distance. Square root of the sum of squared components. ... This is the distance you learned in geometry class. Pythagoras in n dimensions. ... Connection to L2 regularization (Ridge): adding ||w||_2^2 to your loss function penalizes large weights. ... Connection to loss functions: Mean Squared Error (MSE) is the average of L2 distances squared. Squaring penalizes large errors more heavily than small ones.

### Lp Norms: the general family · Lp 范数：一般化家族

L1 和 L2 都是 Lp 范数的特例：

```
||x||_p = (|x_1|^p + |x_2|^p + ... + |x_n|^p)^(1/p)
```

不同的 p 值产生不同形状的「单位球」（到原点距离为 1 的所有点构成的集合）：

```
p=1:    Diamond shape      (corners on axes)
p=2:    Circle/sphere      (the usual round ball)
p=3:    Superellipse       (rounded square)
p=inf:  Square/hypercube   (flat sides along axes)
```

> L1 and L2 are special cases of the Lp norm. ... Different values of p produce different shaped "unit balls" (the set of all points at distance 1 from the origin).

### L-infinity Norm (Chebyshev distance) · L-infinity 范数（切比雪夫距离）

当 p 趋于无穷，Lp 范数收敛到分量的最大绝对值。

```
||x||_inf = max(|x_1|, |x_2|, ..., |x_n|)
```

两点之间的距离由它们差异最大的那一个维度决定。其他所有维度都被忽略。

```
Point A = (1, 1)
Point B = (4, 5)

L-inf distance = max(|4-1|, |5-1|) = max(3, 4) = 4
```

何时用 L-infinity：

- 当任意单个维度上的最坏偏差很重要时
- 棋盘游戏（国际象棋里的王走的是 L-infinity 距离：任意方向一步都算 1）
- 制造公差（每个维度都必须在规格之内）

> As p approaches infinity, the Lp norm converges to the maximum absolute component. ... The distance between two points is determined by the single dimension where they differ the most. All other dimensions are ignored.

### Cosine Similarity and Cosine Distance · 余弦相似度与余弦距离

余弦相似度（cosine similarity）度量两个向量之间的夹角，忽略它们的大小。

```
cos_sim(a, b) = (a . b) / (||a||_2 * ||b||_2)
```

取值范围从 -1（方向相反）到 +1（方向相同）。垂直向量的余弦相似度为 0。

余弦距离把它转成距离：cosine_distance = 1 - cosine_similarity。范围从 0（方向相同）到 2（方向相反）。

```
a = (1, 0)    b = (1, 1)

cos_sim = (1*1 + 0*1) / (1 * sqrt(2)) = 1/sqrt(2) = 0.707
cos_dist = 1 - 0.707 = 0.293
```

为什么余弦统治 NLP 和嵌入：在文本里，文档长度不应该影响相似度。一篇关于猫的文档即使是另一篇关于猫的文档的两倍长，它们也应该「相似」。余弦相似度忽略大小（长度），只关心方向。词分布相同但长度不同的两篇文档指向同一方向，余弦相似度为 1.0。

何时用余弦相似度：

- 文本相似度（TF-IDF 向量、词嵌入、句嵌入）
- 任何「大小是噪声、方向才是信号」的领域
- 推荐系统（用户偏好向量）
- 嵌入搜索（向量数据库几乎总用余弦或点积）

> Cosine similarity measures the angle between two vectors, ignoring their magnitudes. ... Why cosine dominates NLP and embeddings: in text, document length should not affect similarity. ... Cosine similarity ignores magnitude (length) and only cares about direction. Two documents with the same word distribution but different lengths point in the same direction and get cosine similarity 1.0.

### Dot Product Similarity vs Cosine Similarity · 点积相似度 vs 余弦相似度

两个向量的点积：

```
a . b = a_1*b_1 + a_2*b_2 + ... + a_n*b_n
      = ||a|| * ||b|| * cos(angle)
```

余弦相似度就是被两个大小归一化的点积。当两个向量都已经单位归一化（大小 = 1）时，点积与余弦相似度完全相同。

```
If ||a|| = 1 and ||b|| = 1:
    a . b = cos(angle between a and b)
```

它们何时不同：点积包含大小信息。大小更大的向量得到更高的点积分数。这在某些检索系统里很重要——你想让「热门」条目排得更靠前。此时大小扮演了隐式的质量或重要性信号。

```
a = (3, 0)    b = (1, 0)    c = (0, 1)

dot(a, b) = 3     dot(a, c) = 0
cos(a, b) = 1.0   cos(a, c) = 0.0

Both agree on direction, but dot product also reflects magnitude.
```

实践中：

- 想要纯方向相似度时用余弦相似度
- 大小携带有意义信息时用点积
- 许多向量数据库（Pinecone、Weaviate、Qdrant）让你在两者之间选择
- 如果你的嵌入已经做了 L2 归一化，选哪个都一样

> Cosine similarity is the dot product normalized by both magnitudes. When both vectors are already unit-normalized (magnitude = 1), dot product and cosine similarity are identical. ... When they differ: dot product includes magnitude information. A vector with larger magnitude gets a higher dot product score. ... Use cosine similarity when you want pure directional similarity. Use dot product when magnitudes carry meaningful information.

### Mahalanobis Distance · 马氏距离

欧几里得距离对所有维度一视同仁。但如果你的特征彼此相关或尺度不同，L2 会给出误导性的结果。

马氏距离（Mahalanobis distance）考虑了数据的协方差结构。

```
d_M(x, y) = sqrt((x - y)^T * S^(-1) * (x - y))
```

其中 S 是数据的协方差矩阵。

直观理解：马氏距离先把数据去相关并归一化（白化，whitening），再在变换后的空间里计算 L2 距离。如果 S 是单位矩阵（特征不相关、方差为 1），马氏距离就退化为欧几里得距离。

```
Example: height and weight are correlated.
Someone 6'2" and 180 lbs is not unusual.
Someone 5'0" and 180 lbs is unusual.

Euclidean distance might say they are equally far from the mean.
Mahalanobis distance correctly identifies the second as an outlier
because it accounts for the height-weight correlation.
```

何时用马氏距离：

- 离群点检测（离均值马氏距离大的点就是离群点）
- 特征尺度和相关性各不相同时的分类
- 有足够数据估计出可靠协方差矩阵时
- 制造业质量控制（多元过程监控）

> Mahalanobis distance accounts for the covariance structure of the data. ... Intuitively: Mahalanobis distance first decorrelates and normalizes the data (whitening), then computes L2 distance in that transformed space. If S is the identity matrix (uncorrelated, unit variance features), Mahalanobis distance reduces to Euclidean distance.

### Jaccard Similarity (for sets) · Jaccard 相似度（面向集合）

Jaccard 相似度度量两个集合的重叠程度。

```
J(A, B) = |A intersect B| / |A union B|
```

范围从 0（没有重叠）到 1（集合完全相同）。Jaccard 距离 = 1 - Jaccard 相似度。

```
A = {cat, dog, fish}
B = {cat, bird, fish, snake}

Intersection = {cat, fish}         size = 2
Union = {cat, dog, fish, bird, snake}  size = 5

Jaccard similarity = 2/5 = 0.4
Jaccard distance = 0.6
```

何时用 Jaccard：

- 比较标签、类别或特征的集合
- 基于词是否出现（而非词频）的文档相似度
- 近重复检测（MinHash 是 Jaccard 的近似）
- 比较二值特征向量（出现/不出现数据）
- 评估分割模型（Intersection over Union 就是 Jaccard）

> Jaccard similarity measures overlap between two sets. ... It ranges from 0 (no overlap) to 1 (identical sets). Jaccard distance = 1 - Jaccard similarity.

### Edit Distance (Levenshtein Distance) · 编辑距离（Levenshtein 距离）

编辑距离（edit distance）统计把一个字符串变成另一个所需的最少单字符操作数。操作有三种：插入、删除、替换。

```
"kitten" -> "sitting"

kitten -> sitten  (substitute k -> s)
sitten -> sittin  (substitute e -> i)
sittin -> sitting (insert g)

Edit distance = 3
```

用动态规划计算。填一个矩阵，其中条目 (i, j) 是字符串 A 的前 i 个字符与字符串 B 的前 j 个字符之间的编辑距离。

```
        ""  s  i  t  t  i  n  g
    ""   0  1  2  3  4  5  6  7
    k    1  1  2  3  4  5  6  7
    i    2  2  1  2  3  4  5  6
    t    3  3  2  1  2  3  4  5
    t    4  4  3  2  1  2  3  4
    e    5  5  4  3  2  2  3  4
    n    6  6  5  4  3  3  2  3
```

何时用编辑距离：

- 拼写检查与纠错
- DNA 序列比对（带权操作）
- 模糊字符串匹配
- 脏文本数据去重

> Edit distance counts the minimum number of single-character operations needed to transform one string into another. The operations are: insert, delete, or substitute. ... Computed using dynamic programming. Fill a matrix where entry (i, j) is the edit distance between the first i characters of string A and the first j characters of string B.

### KL Divergence (not a distance, but used like one) · KL 散度（不是距离，却常被当距离用）

KL 散度（KL divergence）度量一个概率分布与另一个的差异。它已在第 09 课讲过，但这里必须提它，因为人们把它当「距离」用，尽管它并不是。

```
D_KL(P || Q) = sum(p(x) * log(p(x) / q(x)))
```

关键性质：KL 散度不对称。

```
D_KL(P || Q) != D_KL(Q || P)
```

这意味着它不满足距离度量的基本要求。它也不满足三角不等式。它是散度（divergence），不是距离。

前向 KL（D_KL(P || Q)）是「均值寻求」（mean-seeking）：Q 试图覆盖 P 的所有模态。
反向 KL（D_KL(Q || P)）是「模态寻求」（mode-seeking）：Q 聚焦于 P 的单个模态。

你会在哪里见到 KL 散度：

- VAE（ELBO 里的 KL 项把潜在分布拉向先验）
- 知识蒸馏（学生试图匹配老师的分布）
- RLHF（KL 惩罚让微调后的模型不偏离基座模型）
- 策略梯度方法（约束策略更新）

> KL divergence measures how one probability distribution differs from another. ... Critical property: KL divergence is NOT symmetric. ... This means it fails the basic requirement of a distance metric. It also does not satisfy the triangle inequality. It is a divergence, not a distance. ... Forward KL (D_KL(P || Q)) is "mean-seeking": Q tries to cover all modes of P. Reverse KL (D_KL(Q || P)) is "mode-seeking": Q focuses on a single mode of P.

### Wasserstein Distance (Earth Mover's Distance) · Wasserstein 距离（推土机距离）

Wasserstein 距离度量把一个概率分布变换成另一个所需的最小「功」。这样想：如果一个分布是一堆土，另一个是坑，你要搬多少土、搬多远？

```
W(P, Q) = inf over all transport plans gamma of E[d(x, y)]
```

对一维分布，它简化为累积分布函数之差的绝对值的积分：

```
W_1(P, Q) = integral |CDF_P(x) - CDF_Q(x)| dx
```

为什么 Wasserstein 重要：

- 它是真正的度量（metric）：对称、满足三角不等式
- 即使分布不重叠它也能提供梯度（KL 散度会趋于无穷）
- 这个性质使它成为 Wasserstein GAN（WGAN）的核心，解决了原始 GAN 的训练不稳定问题

```
Distributions with no overlap:

P: [1, 0, 0, 0, 0]    Q: [0, 0, 0, 0, 1]

KL divergence: infinity (log of zero)
Wasserstein: 4 (move all mass 4 bins)

Wasserstein gives a meaningful gradient. KL does not.
```

何时用 Wasserstein：

- GAN 训练（WGAN、WGAN-GP）
- 比较可能不重叠的分布
- 最优传输（optimal transport）问题
- 图像检索（比较颜色直方图）

> Wasserstein distance measures the minimum "work" needed to transform one probability distribution into another. ... It is a true metric (symmetric, satisfies triangle inequality). ... It provides gradients even when distributions do not overlap (KL divergence goes to infinity). ... This property made it central to Wasserstein GANs (WGANs), which solved the training instability of original GANs.

### Why Different Tasks Need Different Distances · 为什么不同任务需要不同的距离

| 任务 | 最佳距离 | 原因 |
|------|--------------|-----|
| 文本相似度 | Cosine | 大小是噪声，方向才是含义 |
| 图像像素比较 | L2 | 空间关系重要，特征尺度相近 |
| 稀疏高维特征 | L1 | 稳健，不放大罕见的大差异 |
| 集合重叠（标签、类别） | Jaccard | 数据天然是集合而非向量 |
| 字符串匹配 | Edit distance | 操作映射到人类编辑的直觉 |
| 离群点检测 | Mahalanobis | 考虑特征相关性与尺度 |
| 比较分布 | KL divergence | 度量用 Q 代替 P 所损失的信息 |
| GAN 训练 | Wasserstein | 分布不重叠也能提供梯度 |
| 嵌入（向量数据库） | Cosine or dot product | 嵌入被训练成把含义编码在方向里 |
| 推荐系统 | Dot product | 大小可以编码热度或置信度 |
| DNA 序列 | Weighted edit distance | 替换代价随碱基对不同而变化 |
| 制造业 QC | L-infinity | 任意维度上的最坏偏差都重要 |

### Connection to Loss Functions · 与损失函数的联系

损失函数就是作用在「预测 vs 目标」上的距离函数。

```
Loss function       Distance it uses       Behavior
MSE                 L2 squared             Penalizes large errors heavily
MAE                 L1                     Penalizes all errors equally
Huber loss          L1 for large errors,   Best of both: robust to outliers,
                    L2 for small errors    smooth gradient near zero
Cross-entropy       KL divergence          Measures distribution mismatch
Hinge loss          max(0, margin - d)     Only penalizes below margin
Triplet loss        L2 (typically)         Pulls positives close, pushes
                                           negatives away
Contrastive loss    L2                     Similar pairs close, dissimilar
                                           pairs beyond margin
```

> Loss functions are distance functions applied to predictions vs targets.

### Connection to Regularization · 与正则化的联系

正则化在损失函数上加一个针对权重的范数惩罚。

```
L1 regularization (Lasso):   loss + lambda * ||w||_1
  -> Sparse weights. Some weights become exactly zero.
  -> Automatic feature selection.
  -> Solution has corners (non-differentiable at zero).

L2 regularization (Ridge):   loss + lambda * ||w||_2^2
  -> Small weights. All weights shrink toward zero.
  -> No feature selection (nothing goes to exactly zero).
  -> Smooth solution everywhere.

Elastic Net:                  loss + lambda_1 * ||w||_1 + lambda_2 * ||w||_2^2
  -> Combines sparsity of L1 with stability of L2.
  -> Groups of correlated features are kept or dropped together.
```

为什么 L1 产生稀疏性而 L2 不会：想象二维权重空间里的约束区域。L1 是菱形，L2 是圆。损失函数的等高线（椭圆）最有可能碰到菱形的角——那里某个权重恰好为零。它们碰到圆的位置是光滑点——那里两个权重都非零。

> Regularization adds a norm penalty on the weights to the loss function. ... Why L1 produces sparsity but L2 does not: picture the constraint region in 2D weight space. L1 is a diamond, L2 is a circle. ... The loss function's contours (ellipses) are most likely to touch the diamond at a corner, where one weight is zero. They touch the circle at a smooth point, where both weights are nonzero.

### Nearest Neighbor Search · 最近邻搜索

每个距离函数都隐含一个最近邻搜索问题：给定一个查询点，找出数据集中离它最近的点。

精确最近邻搜索在一个 n 个点、d 维的数据集上每次查询需要 O(n * d)。对大数据集来说太慢了。

近似最近邻（Approximate Nearest Neighbor，ANN）算法用少量精度换取巨大的速度提升：

```
Algorithm         Approach                      Used by
KD-trees          Axis-aligned space partition   scikit-learn (low-dim)
Ball trees        Nested hyperspheres            scikit-learn (medium-dim)
LSH               Random hash projections        Near-duplicate detection
HNSW              Hierarchical navigable         FAISS, Qdrant, Weaviate
                  small-world graph
IVF               Inverted file index with       FAISS (billion-scale)
                  cluster-based search
Product quant.    Compress vectors, search       FAISS (memory-constrained)
                  in compressed space
```

HNSW（Hierarchical Navigable Small World，分层可导航小世界）是现代向量数据库中的主导算法。它构建一个多层图，每个节点连接到它的近似最近邻。搜索从顶层开始（稀疏、长跳），逐层下降到底层（稠密、短跳）。

```figure
norm-unit-balls
```

> Every distance function implies a nearest neighbor search problem: given a query point, find the closest points in a dataset. ... Exact nearest neighbor search is O(n * d) per query in a dataset of n points with d dimensions. For large datasets, this is too slow. ... HNSW (Hierarchical Navigable Small World) is the dominant algorithm in modern vector databases. It builds a multi-layer graph where each node connects to its approximate nearest neighbors.

## Build It · 动手造

### Step 1: All norm and distance functions · 第 1 步：全部范数与距离函数

完整实现见 `code/distances.py`。每个函数都只用基础 Python 数学从零构建。

> See `code/distances.py` for the complete implementation. Every function is built from scratch using only basic Python math.

### Step 2: Same data, different distances, different neighbors · 第 2 步：同样的数据、不同的距离、不同的近邻

`distances.py` 里的演示会创建一个数据集、选一个查询点，并展示最近邻如何随距离度量而变化。L1 下「最近」的点在 L2 或余弦下未必最近。

> The demo in `distances.py` creates a dataset, picks a query point, and shows how the nearest neighbor changes depending on the distance metric. The point that is "closest" under L1 may not be closest under L2 or cosine.

### Step 3: Embedding similarity search · 第 3 步：嵌入相似度搜索

代码包含一个模拟的嵌入相似度搜索：用余弦相似度与 L2 距离分别找出与查询最相似的「文档」，并展示两种排序可以不同。

> The code includes a mock embedding similarity search that finds the most similar "documents" to a query using cosine similarity vs L2 distance, showing that the rankings can differ.

## Use It · 实战用法

最常见的实战用法：在向量数据库里找相似条目。

```python
import numpy as np

def cosine_similarity_matrix(X):
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    X_normalized = X / norms
    return X_normalized @ X_normalized.T

embeddings = np.random.randn(1000, 768)

sim_matrix = cosine_similarity_matrix(embeddings)

query_idx = 0
similarities = sim_matrix[query_idx]
top_k = np.argsort(similarities)[::-1][1:6]
print(f"Top 5 most similar to item 0: {top_k}")
print(f"Similarities: {similarities[top_k]}")
```

当你调用 `model.encode(text)` 然后去搜索向量数据库时，幕后发生的就是这些。嵌入模型把文本映射成向量；向量数据库计算你的查询向量与每个存储向量之间的余弦相似度（或点积），并使用 ANN 算法来避免逐个比对所有向量。

> The most common practical use: finding similar items in a vector database. ... When you call `model.encode(text)` and then search a vector database, this is what happens under the hood. The embedding model maps text to vectors. The vector database computes cosine similarity (or dot product) between your query vector and every stored vector, using ANN algorithms to avoid checking all of them.

## Exercises · 练习

1. 计算 (1, 2, 3) 和 (4, 0, 6) 之间的 L1、L2 和 L-infinity 距离。验证对任意点对都有 L-inf <= L2 <= L1 成立。证明为什么这个顺序是有保证的。

2. 构造两个向量，使余弦相似度高（> 0.9）但 L2 距离大（> 10）。从几何上解释发生了什么。再构造两个向量，使余弦相似度低（< 0.3）但 L2 距离小（< 0.5）。

3. 实现一个函数：输入一个数据集和一个查询点，分别按 L1、L2、余弦和马氏距离返回最近邻。找一个数据集，让四种度量对哪个点最近各执一词。

4. 用 CDF 方法手算 [0.5, 0.5, 0, 0] 和 [0, 0, 0.5, 0.5] 之间的 Wasserstein 距离。再算 [0.25, 0.25, 0.25, 0.25] 和 [0, 0, 0.5, 0.5] 之间的。哪个更大，为什么？

5. 实现近似 Jaccard 相似度的 MinHash。生成 100 个随机集合，计算所有集合对的精确 Jaccard，再与使用 50、100、200 个哈希函数的 MinHash 近似比较。画出近似误差。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|----------------------|
| Norm（范数） | 「向量的大小」 | 把向量映射为非负标量的函数，满足三角不等式、绝对齐次性，且仅零向量的范数为零 |
| L1 norm | 「曼哈顿距离」 | 分量绝对值之和。在优化中产生稀疏性。对离群点稳健 |
| L2 norm | 「欧几里得距离」 | 分量平方和的平方根。欧几里得空间里的直线距离 |
| Lp norm | 「广义范数」 | 分量 p 次幂绝对值之和的 p 次方根。L1 和 L2 是特例 |
| L-infinity norm | 「最大值范数」或「切比雪夫距离」 | 分量绝对值的最大值。p 趋于无穷时 Lp 的极限 |
| Cosine similarity（余弦相似度） | 「向量之间的夹角」 | 被两个大小归一化的点积。范围 -1 到 +1。忽略向量长度 |
| Cosine distance（余弦距离） | 「1 减余弦相似度」 | 把余弦相似度转成距离。范围 0 到 2 |
| Dot product（点积） | 「未归一化的余弦」 | 分量乘积之和。等于余弦相似度乘以两个大小 |
| Mahalanobis distance（马氏距离） | 「感知相关性的距离」 | 用数据协方差矩阵白化（去相关并归一化）后的空间里的 L2 距离 |
| Jaccard similarity | 「集合重叠」 | 交集大小除以并集大小。作用于集合，不是向量 |
| Edit distance（编辑距离） | 「Levenshtein 距离」 | 把一个字符串变成另一个所需的最少插入、删除和替换次数 |
| KL divergence（KL 散度） | 「分布之间的距离」 | 不是真正的距离（不对称）。度量用 Q 编码 P 多付出的比特数 |
| Wasserstein distance | 「推土机距离」 | 把质量从一个分布搬运到另一个的最小功。真正的度量 |
| Approximate nearest neighbor（近似最近邻） | 「ANN 搜索」 | 以远快于精确搜索的速度找出近似最近点的算法（HNSW、LSH、IVF） |
| HNSW | 「向量数据库的那个算法」 | 分层可导航小世界图（Hierarchical Navigable Small World）。用于快速近似最近邻搜索的多层图 |
| L1 regularization | 「Lasso」 | 在损失中加入权重的 L1 范数。把权重推向零（稀疏性） |
| L2 regularization | 「Ridge」或「权重衰减（weight decay）」 | 在损失中加入权重 L2 范数的平方。把权重向零收缩，但不产生稀疏性 |
| Elastic Net | 「L1 + L2」 | 结合 L1 与 L2 正则化。处理相关特征组比两者单独用都好 |

## Further Reading · 延伸阅读

- [FAISS: A Library for Efficient Similarity Search](https://github.com/facebookresearch/faiss) —— Meta 的十亿规模 ANN 搜索库
- [Wasserstein GAN (Arjovsky et al., 2017)](https://arxiv.org/abs/1701.07875) —— 把推土机距离引入 GAN 的论文
- [Locality-Sensitive Hashing (Indyk & Motwani, 1998)](https://dl.acm.org/doi/10.1145/276698.276876) —— 奠基性的 ANN 算法
- [Efficient Estimation of Word Representations (Mikolov et al., 2013)](https://arxiv.org/abs/1301.3781) —— Word2Vec，余弦相似度从这里成为嵌入的默认选择
- [sklearn.neighbors documentation](https://scikit-learn.org/stable/modules/neighbors.html) —— scikit-learn 中距离度量与近邻算法的实战指南
