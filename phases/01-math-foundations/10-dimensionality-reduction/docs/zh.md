# 降维（Dimensionality Reduction）

> 高维数据自带结构。从正确的角度看过去，你就能找到它。

**类型：** Build
**语言：** Python
**前置：** Phase 1，第 01 课（线性代数直觉）、02（向量矩阵运算）、03（特征值与特征向量）、06（概率与分布）
**时间：** ~90 分钟

> High-dimensional data has structure. You find it by looking from the right angle.

## 学习目标

- 从零实现 PCA：中心化 → 协方差矩阵 → 特征分解 → 投影
- 用 explained variance ratio（解释方差比）和 elbow method（肘部法）选择主成分个数
- 对比 PCA、t-SNE、UMAP 在二维可视化上的取舍
- 用 RBF kernel PCA 分开线性 PCA 分不开的非线性结构

> Implement PCA from scratch... / Use explained variance ratio and the elbow method... / Compare PCA, t-SNE, and UMAP... / Apply kernel PCA with an RBF kernel...

## 问题：784 维没法看

每个样本 784 个特征（比如手写数字的像素），画不了、想不了。但这些特征大都是冗余的——一个"7"不需要 784 个独立数字来描述，只需要几笔的角度、横杠长度、倾斜度。降维就是找到那个更小的面：把 784 维压到 2/10/50 维，同时保住要紧的结构。

> You cannot visualize 784 dimensions... The actual information lives on a much smaller surface... Dimensionality reduction finds that smaller surface.

## 核心概念

### 维度灾难（curse of dimensionality）

维度升高时三件事会坏掉：

1. **距离失去意义**：随机两点的距离趋于同一个值（课文数据：2 维时 max/min 比约 5.0，1000 维只剩约 1.02）——最近邻搜索失效。
2. **体积挤到角落**：d 维单位超立方体有 2^d 个角，100 维时几乎全部体积都在角落里，数据点散在边缘。
3. **数据量指数不够用**：从 2 维到 20 维要保持同样密度需要 10^18 倍数据。降维是把数据密度拉回可用的范围。

> Distance becomes meaningless... Volume concentrates in corners... You need exponentially more data.

### PCA：找"方差最大"的方向

PCA 旋转坐标系，让第一根轴对准数据散得最开的方向（PC1），第二根对准次开的方向（PC2），依此类推。算法五步：中心化 → 协方差矩阵 → 特征分解 → 按特征值排序 → 投影到前 k 个特征向量。

为什么是特征分解？协方差矩阵是对称半正定矩阵，特征向量是一组正交方向，特征值 = 该方向捕获的方差。**最大特征值的特征向量 = 最大方差方向**。这一步直接接上第 03 课：特征值 A@v=λv 在这里有了第一份"工资"。

> PCA finds the axes along which your data varies the most... The eigenvector with the largest eigenvalue points along the direction of maximum variance.

### 解释方差比与选 k

每个主成分捕获总方差的一部分：explained_ratio_k = λ_k / Σλ。累计到 0.95 就说明前若干个成分拿走了 95% 的信息，剩下多半是噪声。选 k 的三种策略：阈值法（90–95%）、肘部法（看陡降拐点）、下游任务法（扫 k 看模型准确率在哪里平台期）。

> When the cumulative explained variance reaches 0.95, you know that many components capture 95% of the information.

### t-SNE 与 UMAP：保邻域的可视化

- **t-SNE**：在高维空间按距离算一个"邻居概率分布"，然后在 2D 里找同样的分布——高维的邻居在 2D 还是邻居。非线性、随机性（每次跑结果不同）、perplexity 控制有效邻居数（典型 5–50）、**簇间距离没有意义**（只有簇本身有意义）、O(n²) 慢。
- **UMAP**：用近似最近邻图，更快（能上百万样本），全局结构更好。n_neighbors 类似 perplexity（越大越保全局），min_dist 控制点挤多紧。

> t-SNE is designed for visualization... Distances between clusters in the output are not meaningful. / UMAP... Faster... Better global structure.

### 方法选择表

| 方法 | 场景 | 保什么 | 速度 |
|---|---|---|---|
| PCA | 训练前预处理 / 压缩 | 全局方差 | 快，百万样本可用 |
| t-SNE | 出版级 2D 图 | 局部邻域 | 慢（<1 万样本） |
| UMAP | 大规模 2D 可视化 | 局部 + 部分全局 | 中 |
| Kernel PCA | 非线性流形 | 核空间主方向 | n×n 核矩阵，内存受限 |

经验法则：**预处理和压缩用 PCA，2D 看结构用 t-SNE / UMAP**。

> Rule of thumb: use PCA for preprocessing and data compression. Use t-SNE or UMAP when you need to visualize structure in 2D.

### Kernel PCA 与核技巧

标准 PCA 只会切线性子空间：二维的同心圆环怎么旋转都分不开。Kernel PCA 用核函数（如 RBF：exp(-gamma·‖x−y‖²)）隐式把数据抬进高维特征空间，在那里做 PCA——这就是核技巧（SVM 同款思想）。代价：核矩阵 n×n，内存受限；成分失去直接的特征解释；逆变换要近似。

> Kernel PCA applies PCA in a high-dimensional feature space induced by a kernel function, without explicitly computing the coordinates in that space.

### 重建误差

压缩得怎么样？投到 k 维再投影回来算 MSE。PCA 有干净的关系式：**重建误差 = 没被保留的特征值之和**，丢失比例 = 丢掉的特征值和 / 全部特征值和。重建误差还能做异常检测：误差特别大的样本就是不在学到子空间里的离群点——生产系统里 PCA 异常检测的基础。

> Reconstruction error = sum of eigenvalues NOT included / You can use it for anomaly detection.

## Build It（从零构建）

PCA 类的骨架（完整代码在 \`code/dim_reduction.py\`）：

1. \`fit\`：记均值 → 中心化 → \`np.cov(rowvar=False)\` → \`np.linalg.eigh\`（对称矩阵专用）→ 按特征值降序排 → 取前 k 个特征向量为 \`components\` → \`explained_variance_ratio_ = λ_k / Σλ\`。
2. \`transform\`：中心化后 \`X_centered @ components.T\`——就是一次旋转投影。

> class PCA: ... def fit(self, X): ... eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix) ... def transform(self, X): return X_centered @ self.components.T

## Use It（用生产库）

sklearn 的 \`PCA\` 接口一致（fit/transform/explained_variance_ratio_），结果与手写版一致（符号可能翻转，|X| 相同）。把 PCA 当预处理接到 LogisticRegression 前面，扫 k=10/30/50/100/200：**准确率在远小于 784 维处就平台了，那个平台就是你的工作点**。

> Performance plateaus well before 784 dimensions. That plateau is your operating point.

## 实测纠正（本机实跑 \`code/dim_reduction.py\`，2026-10-12）

1. **MNIST 环节本机跑不了**：\`fetch_openml("mnist_784")\` 要写 \`~/scikit_learn_data\` 且需要联网下载，本次被沙箱/网络拦下（PermissionError）。课文里"50 个成分捕获约 xx%"的数字要用合成数据等价验证——不影响方法本身。
2. **合成 3D 数据（x3 = 0.5·x1 + 0.3·x2 + 噪声）实测**：两个主成分捕获 **99.93%** 方差（ratios = [0.590, 0.409]），重建 MSE = 0.0024——第三维基本是前两维的线性组合，PCA 正确识别了这一点。
3. **Kernel PCA 分同心圆实测**（每环 200 点）：线性 PCA 1 个成分上内环范围 [-1.13, 1.35]、外环 [-3.10, 3.24]，**完全重叠**；RBF 核（gamma=0.5）后内环 PC1 均值 -0.3585、外环 +0.3585，分离度 0.7170——**同一个数据，换一个核就分开了**。
4. **gamma 扫描实测**：0.1 → 分离度 0.0046（欠拟合，核太"宽"）；0.5 → **0.7170（最佳）**；1.0 → 0.2631；5.0 → 0.0619（过拟合，只看局部）。gamma 不是越大越好，是倒 U 形。
5. **"数据实际是 5 维"实验实测**（300 样本 × 20 特征、5 个有效）：累计解释方差 k=3 → 0.8150，**k=5 → 0.9986**，k=5 之后每个新成分只贡献 ~0.0001；重建 MSE 在 k=5 处从 1.007（k=3）跳水到 **0.0075**，之后几乎不动。**解释方差曲线 + 重建误差拐点都准确指认了"真实维度 = 5"**——课文 Exercise 3 的答案被实测坐实。
6. 本机 \`.venv\` 有 numpy + sklearn，但 umap 未装（课文 Step 5 走 ImportError 分支，符合预期）。

## 关键术语

| 术语 | 别人怎么说 | 实际意思 |
|---|---|---|
| Curse of dimensionality | "特征太多" | 距离、体积、数据密度在高维全部反直觉，模型需要指数级更多数据补偿 |
| PCA | "降维" | 旋转坐标系对准最大方差方向，砍掉低方差轴 |
| Principal component | "重要方向" | 协方差矩阵的特征向量 |
| Explained variance ratio | "这个成分有多少信息" | λ_k / Σλ；前 k 个求和看保留了多少 |
| t-SNE | "那张聚类图" | 非线性保邻域映射，只适合可视化 |
| UMAP | "更快的 t-SNE" | 拓扑近似最近邻，局部 + 部分全局，扩展性好 |
| Perplexity | "t-SNE 旋钮" | 每个点考虑的有效邻居数 |
| Manifold | "数据住的面" | 嵌在高维空间里的低维曲面 |

## 进一步阅读

- [A Tutorial on Principal Component Analysis](https://arxiv.org/abs/1404.1100)（Shlens）
- [How to Use t-SNE Effectively](https://distill.pub/2016/misread-tsne/)（Wattenberg et al.）
- [UMAP documentation](https://umap-learn.readthedocs.io/)
