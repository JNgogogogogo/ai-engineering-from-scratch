# Lesson: phases/02-ml-fundamentals/01-what-is-machine-learning/docs/en.md
# 从零实现最近质心分类器（Nearest Centroid Classifier），
# 不依赖任何机器学习库，仅使用 numpy 做数值计算。
# 目的：理解"机器学习 = 从数据中学出决策规则"这一最基本形式。
# 参考：NearestCentroid 算法描述见 scikit-learn 文档
# https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.NearestCentroid.html

import numpy as np


class NearestCentroid:
    """最近质心分类器。

    核心思想：每一类样本在特征空间中有一个"中心"（质心），
    即该类所有样本在每个特征维度上的平均值。
    预测时，新样本离哪个类的质心最近，就归为哪一类。

    这是最简单的生成式思想之一：
      fit   —— 只做一件事：算出每个类的质心（这就是"学习"）。
      predict —— 只做一件事：比距离（这就是"推理"）。
    """

    def __init__(self):
        # classes: 训练数据中出现过的类别标签，如 array([0, 1])
        self.classes = None
        # centroids: 形状 (n_classes, n_features)，第 i 行是第 i 个类的质心
        self.centroids = None

    def fit(self, X, y):
        """训练：计算每个类别的质心。

        X: 形状 (n_samples, n_features) 的特征矩阵
        y: 形状 (n_samples,) 的标签向量
        """
        # np.unique 返回排序后的去重标签，同时确定了 classes 与 centroids 的对应顺序
        self.classes = np.unique(y)
        # 对每个类别 c：用布尔掩码 X[y == c] 取出该类所有样本，
        # 沿样本维度（axis=0）求均值，得到该类的质心向量
        self.centroids = np.array([
            X[y == c].mean(axis=0) for c in self.classes
        ])
        return self

    def predict(self, X):
        """预测：为每个样本找出距离最近的质心对应的类别。

        返回形状 (n_samples,) 的预测标签数组。
        """
        # distances 形状 (n_classes, n_samples)：
        # 第 i 行是所有样本到第 i 个类质心的欧氏距离。
        # 欧氏距离 = sqrt(sum((x - centroid)^2))，对特征维度（axis=1）求和
        distances = np.array([
            np.sqrt(((X - c) ** 2).sum(axis=1))
            for c in self.centroids
        ])
        # 对每个样本（axis=0 上取 argmin）找距离最小的类，再映射回类别标签
        return self.classes[distances.argmin(axis=0)]

    def score(self, X, y):
        """计算准确率：预测正确的样本占比（0 到 1 之间）。"""
        return np.mean(self.predict(X) == y)


def generate_classification_data(n_per_class=100, n_features=2, separation=2.0, seed=42):
    """生成二分类的合成高斯数据。

    两类样本都是从标准正态分布采样的点云，分别往相反方向平移
    separation/2，因此 separation 越大，两类分得越开、问题越简单。

    n_per_class: 每类样本数
    n_features:  特征维度
    separation:  两类中心之间的距离
    seed:        随机种子，保证结果可复现
    """
    rng = np.random.RandomState(seed)
    # 两类中心对称分布在原点两侧：类 0 在 +separation/2，类 1 在 -separation/2
    center_0 = np.ones(n_features) * (separation / 2)
    center_1 = np.ones(n_features) * (-separation / 2)
    # randn 生成标准正态噪声，加上中心即得到围绕中心散布的点云
    X_class0 = rng.randn(n_per_class, n_features) + center_0
    X_class1 = rng.randn(n_per_class, n_features) + center_1
    # 堆叠成完整数据集：前半是类 0，后半是类 1
    X = np.vstack([X_class0, X_class1])
    y = np.array([0] * n_per_class + [1] * n_per_class)
    # 随机打乱顺序，模拟真实数据中类别混杂的情况
    shuffle_idx = rng.permutation(len(y))
    return X[shuffle_idx], y[shuffle_idx]


def train_test_split(X, y, test_fraction=0.3, seed=42):
    """把数据随机划分为训练集和测试集。

    划分前先随机打乱索引，保证两个集合的类别分布大致一致。
    返回 (X_train, X_test, y_train, y_test)。
    """
    rng = np.random.RandomState(seed)
    n = len(y)
    idx = rng.permutation(n)
    # 前 (1 - test_fraction) 部分作训练集，其余作测试集
    split = int(n * (1 - test_fraction))
    return X[idx[:split]], X[idx[split:]], y[idx[:split]], y[idx[split:]]


def random_baseline(y_train, y_test, seed=42):
    """随机基线：按训练集中各类的出现频率随机猜标签。

    这是"瞎猜"的下限参照。任何真实模型都应该显著超过它，
    否则说明模型没有从数据学到任何东西。
    """
    rng = np.random.RandomState(seed)
    classes, counts = np.unique(y_train, return_counts=True)
    probs = counts / counts.sum()
    preds = rng.choice(classes, size=len(y_test), p=probs)
    return np.mean(preds == y_test)


def majority_baseline(y_train, y_test):
    """多数类基线：永远预测训练集中样本数最多的那个类。

    在类别不平衡时，这个基线可能相当高。如果模型打不过它，
    说明模型还不如"无脑猜大多数"。
    """
    values, counts = np.unique(y_train, return_counts=True)
    majority_class = values[np.argmax(counts)]
    preds = np.full(len(y_test), majority_class)
    return np.mean(preds == y_test)


def demo_nearest_centroid():
    """演示 1：标准二分类流程（生成数据 → 划分 → 训练 → 评估 → 对比基线）。"""
    print("=" * 60)
    print("从零实现的最近质心分类器")
    print("=" * 60)
    print()

    # 生成两类各 150 个样本、间距为 2.0 的二维数据
    X, y = generate_classification_data(n_per_class=150, separation=2.0)
    X_train, X_test, y_train, y_test = train_test_split(X, y)

    print(f"数据集：{len(y)} 个样本，{X.shape[1]} 个特征，2 个类别")
    print(f"训练集：{len(y_train)} 个样本，测试集：{len(y_test)} 个样本")
    print()

    # 训练：只需要算质心，瞬间完成
    clf = NearestCentroid()
    clf.fit(X_train, y_train)

    # 在训练集和测试集上分别评估：
    # 两者接近说明没有过拟合（这个模型简单到几乎不会过拟合）
    train_acc = clf.score(X_train, y_train)
    test_acc = clf.score(X_test, y_test)

    print(f"质心：")
    for i, c in enumerate(clf.classes):
        print(f"  类别 {c}: [{clf.centroids[i][0]:.3f}, {clf.centroids[i][1]:.3f}]")
    print()

    # 与两个基线对比，验证模型确实学到了东西
    print(f"{'方法':<25} {'训练集':>10} {'测试集':>10}")
    print("-" * 50)
    print(f"{'最近质心':<25} {train_acc:>10.3f} {test_acc:>10.3f}")

    rand_acc = random_baseline(y_train, y_test)
    print(f"{'随机基线':<25} {'--':>10} {rand_acc:>10.3f}")

    maj_acc = majority_baseline(y_train, y_test)
    print(f"{'多数类基线':<25} {'--':>10} {maj_acc:>10.3f}")

    print()
    improvement_over_random = (test_acc - rand_acc) / rand_acc * 100
    print(f"最近质心比随机基线高出 {improvement_over_random:.1f}%")


def demo_varying_difficulty():
    """演示 2：类别间距（separation）越大，分类越容易。

    间距小 → 两类点云重叠 → 任何模型都难以分开；
    间距大 → 点云几乎不重叠 → 连最简单的模型也能接近 100%。
    这说明模型效果同时取决于"模型能力"和"数据本身的可分性"。
    """
    print()
    print("=" * 60)
    print("类别间距对准确率的影响")
    print("=" * 60)
    print()

    separations = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]

    print(f"{'间距':>12} {'训练集':>10} {'测试集':>10} {'随机':>10}")
    print("-" * 50)

    for sep in separations:
        # 每次用同一个 seed 生成数据，保证不同间距之间可比
        X, y = generate_classification_data(n_per_class=150, separation=sep)
        X_train, X_test, y_train, y_test = train_test_split(X, y)

        clf = NearestCentroid()
        clf.fit(X_train, y_train)

        train_acc = clf.score(X_train, y_train)
        test_acc = clf.score(X_test, y_test)
        rand_acc = random_baseline(y_train, y_test)

        print(f"{sep:>12.1f} {train_acc:>10.3f} {test_acc:>10.3f} {rand_acc:>10.3f}")

    print()
    print("间距小：两类严重重叠，准确率下降。")
    print("间距大：两类相距很远，连这个简单模型也能表现优异。")


def demo_higher_dimensions():
    """演示 3：特征维度对分类效果的影响。

    对于"信号均匀分布在每个维度"的高斯合成数据：
    维度越高，质心估计越准（每维噪声在求均值时被平均掉），
    两类质心在高维空间里分得越开，准确率越高。

    注意：这是合成数据的理想情形。真实数据中很多维度是噪声，
    维度增加反而会稀释信号 —— 即"维度灾难"（curse of dimensionality）。
    """
    print()
    print("=" * 60)
    print("高维空间中的最近质心")
    print("=" * 60)
    print()

    dimensions = [2, 5, 10, 20, 50]

    print(f"{'特征数':>10} {'测试集':>10}")
    print("-" * 25)

    for d in dimensions:
        # 保持 separation=2.0 不变，只增加维度，观察准确率变化
        X, y = generate_classification_data(n_per_class=200, n_features=d, separation=2.0)
        X_train, X_test, y_train, y_test = train_test_split(X, y)

        clf = NearestCentroid()
        clf.fit(X_train, y_train)
        test_acc = clf.score(X_test, y_test)

        print(f"{d:>10d} {test_acc:>10.3f}")

    print()
    print("对于间距固定的高斯合成数据，维度越高效果越好。")
    print("质心在高维空间中变得更易区分。")
    print("真实数据则不同——当大量特征只是噪声时，")
    print("维度灾难就会显现。")


def demo_multiclass():
    """演示 4：三分类问题。

    最近质心天然支持多分类：predict 里的 argmin 会在所有类的
    质心中选最近的，不需要"一对多"之类的技巧。
    """
    print()
    print("=" * 60)
    print("多分类最近质心（3 个类别）")
    print("=" * 60)
    print()

    rng = np.random.RandomState(42)
    n_per_class = 100
    # 三个类的中心大致呈三角形分布，标准差 0.8 保证有一定重叠
    centers = np.array([[2, 0], [-1, 1.7], [-1, -1.7]])
    X_parts = [rng.randn(n_per_class, 2) * 0.8 + c for c in centers]
    X = np.vstack(X_parts)
    y = np.array([0] * n_per_class + [1] * n_per_class + [2] * n_per_class)

    shuffle_idx = rng.permutation(len(y))
    X, y = X[shuffle_idx], y[shuffle_idx]

    X_train, X_test, y_train, y_test = train_test_split(X, y)

    clf = NearestCentroid()
    clf.fit(X_train, y_train)

    print(f"三分类问题：{len(y)} 个样本")
    print(f"质心：")
    for i, c in enumerate(clf.classes):
        print(f"  类别 {c}: [{clf.centroids[i][0]:.3f}, {clf.centroids[i][1]:.3f}]")
    print()
    print(f"测试集准确率: {clf.score(X_test, y_test):.3f}")
    # 三分类的随机基线约为 1/3
    print(f"随机基线（约 1/3）: {random_baseline(y_train, y_test):.3f}")


if __name__ == "__main__":
    # 依次运行四个演示：二分类主流程、难度梯度、维度影响、多分类
    demo_nearest_centroid()
    demo_varying_difficulty()
    demo_higher_dimensions()
    demo_multiclass()
    print()
    print("所有机器学习入门演示运行完毕。")
