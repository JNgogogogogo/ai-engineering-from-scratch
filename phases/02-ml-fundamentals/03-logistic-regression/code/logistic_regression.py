# ============================================================
# 逻辑回归 —— 从零实现 + Softmax 多分类 + scikit-learn 对照
# 课程文档: phases/02-ml-fundamentals/03-logistic-regression/docs/en.md
# 内容: sigmoid 函数、二元交叉熵损失、梯度下降、分类指标
#       (混淆矩阵/精确率/召回率/F1)、决策边界、阈值调优、
#       Softmax 多分类、线性回归做分类为何不行、sklearn 对比
# 运行: python3 logistic_regression.py （零第三方依赖即可跑通）
# ============================================================
import random
import math


# ------------------------------------------------------------
# sigmoid 函数: 逻辑回归的核心构件
# 公式: σ(z) = 1 / (1 + e^(-z))
# 作用: 把任意实数 z 压缩到 (0, 1) 区间，可以当作"概率"来用
#   z → +∞ 时 σ → 1；z → -∞ 时 σ → 0；z = 0 时 σ = 0.5
# ------------------------------------------------------------
def sigmoid(z):
    # 数值保护: z 太大时 e^(-z) 会溢出（math.exp 上限约 709），
    # 先截断到 ±500，sigmoid 在这些位置的值已经和 0/1 几乎没有区别
    z = max(-500, min(500, z))
    return 1.0 / (1.0 + math.exp(-z))


# ------------------------------------------------------------
# 生成模拟数据: 二维平面上两团高斯分布的点
#   类别 0: 以 (2, 2) 为中心的高斯团 → 标签 0
#   类别 1: 以 (5, 5) 为中心的高斯团 → 标签 1
# 两团中心距离够远但略有重叠，适合学一条线性决策边界
# ------------------------------------------------------------
random.seed(42)  # 固定随机种子，保证结果可复现
N = 200
X = []
y = []

for _ in range(N // 2):
    X.append([random.gauss(2, 1), random.gauss(2, 1)])  # 特征: 两个维度都以 2 为中心、标准差 1
    y.append(0)

for _ in range(N // 2):
    X.append([random.gauss(5, 1), random.gauss(5, 1)])  # 特征: 两个维度都以 5 为中心、标准差 1
    y.append(1)

# 打乱顺序: 前面生成时 0 全在前面、1 全在后面，
# 不打乱的话 train/test 划分会一边全是 0 一边全是 1
combined = list(zip(X, y))
random.shuffle(combined)
X, y = zip(*combined)  # 解包回两个列表
X = list(X)
y = list(y)

print(f"Generated {N} samples (2 classes, 2 features)（已生成 {N} 个样本: 2 个类别, 2 个特征）")
print(f"Class 0 center: (2, 2), Class 1 center: (5, 5)（类别 0 中心: (2, 2), 类别 1 中心: (5, 5)）")
print(f"First 5 samples:（前 5 个样本:）")
for i in range(5):
    print(f"  Features: [{X[i][0]:.2f}, {X[i][1]:.2f}], Label: {y[i]}"
          f"（特征: [{X[i][0]:.2f}, {X[i][1]:.2f}], 标签: {y[i]}）")


# ------------------------------------------------------------
# 逻辑回归（二分类）
#   模型:   z = w·x + b          （先做一次线性计算，和线性回归一样）
#           p = sigmoid(z)       （再压到 0~1，作为"属于类别 1 的概率"）
#   损失:   二元交叉熵
#           L = -(1/n)·Σ[ yᵢ·log(pᵢ) + (1-yᵢ)·log(1-pᵢ) ]
#   梯度:   ∂L/∂wⱼ = (1/n)·Σ(pᵢ - yᵢ)·xᵢⱼ
#           ∂L/∂b  = (1/n)·Σ(pᵢ - yᵢ)
#           —— 和线性回归形式完全一样！因为 sigmoid 的导数恰好是 p(1-p)，
#              链式法则相乘后抵消掉了，只剩 (p - y)
# ------------------------------------------------------------
class LogisticRegression:
    """二分类逻辑回归: sigmoid + 二元交叉熵 + 批量梯度下降。"""

    def __init__(self, n_features, learning_rate=0.01):
        self.weights = [0.0] * n_features  # 权重 w，逐特征初始化为 0
        self.bias = 0.0                    # 偏置 b
        self.lr = learning_rate            # 学习率
        self.loss_history = []             # 每轮损失记录，便于观察收敛

    def predict_proba(self, x):
        """返回属于类别 1 的概率 p = σ(w·x + b)，取值 (0, 1)。"""
        z = sum(w * xi for w, xi in zip(self.weights, x)) + self.bias
        return sigmoid(z)

    def predict(self, x, threshold=0.5):
        """输出最终类别: 概率 ≥ 阈值判 1，否则判 0（默认阈值 0.5）。"""
        return 1 if self.predict_proba(x) >= threshold else 0

    def compute_loss(self, X, y):
        """二元交叉熵: 标签为 1 时惩罚 -log(p)，标签为 0 时惩罚 -log(1-p)。
        预测越自信越准 → 损失接近 0；自信但错了 → 损失趋于无穷大。"""
        n = len(y)
        total = 0.0
        for i in range(n):
            p = self.predict_proba(X[i])
            # 裁剪到 [1e-15, 1-1e-15]: 避免 p=0 或 p=1 时 log(0) 报错/得 inf
            p = max(1e-15, min(1 - 1e-15, p))
            # y=1 时只剩第一项，y=0 时只剩第二项（乘 0 消掉了另一项）
            total += y[i] * math.log(p) + (1 - y[i]) * math.log(1 - p)
        return -total / n

    def fit(self, X, y, epochs=1000, print_every=200):
        """批量梯度下降: 每轮遍历全部样本累加梯度，再统一更新参数。"""
        n = len(y)
        n_features = len(X[0])
        for epoch in range(epochs):
            dw = [0.0] * n_features  # 各权重的梯度累加器
            db = 0.0                 # 偏置的梯度累加器
            for i in range(n):
                p = self.predict_proba(X[i])
                # 核心公式: 梯度里的"误差"就是 (预测概率 - 真实标签)
                # 预测 0.9 而真实 1 → 误差 -0.1，小惩罚
                # 预测 0.1 而真实 1 → 误差 -0.9，大惩罚
                error = p - y[i]
                for j in range(n_features):
                    dw[j] += error * X[i][j]  # ∂L/∂wⱼ 累加 (p-y)·xⱼ
                db += error                    # ∂L/∂b 累加 (p-y)
            # 取平均后沿负梯度方向更新
            for j in range(n_features):
                self.weights[j] -= self.lr * (dw[j] / n)
            self.bias -= self.lr * (db / n)
            loss = self.compute_loss(X, y)
            self.loss_history.append(loss)
            if epoch % print_every == 0:
                print(f"  Epoch {epoch:4d} | Loss: {loss:.4f} | w: [{self.weights[0]:.3f}, {self.weights[1]:.3f}] | b: {self.bias:.3f}"
                      f"（第 {epoch:4d} 轮 | 损失: {loss:.4f}）")
        return self

    def accuracy(self, X, y):
        """准确率 = 预测正确的样本数 / 总样本数。"""
        correct = sum(1 for i in range(len(y)) if self.predict(X[i]) == y[i])
        return correct / len(y)


# 80/20 划分: 前 80% 训练，后 20% 测试（数据已打乱，直接切即可）
split = int(0.8 * N)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

print("\n=== Training Logistic Regression ===（训练逻辑回归）")
model = LogisticRegression(n_features=2, learning_rate=0.1)
model.fit(X_train, y_train, epochs=1000, print_every=200)

print(f"\nTrain accuracy: {model.accuracy(X_train, y_train):.4f}（训练集准确率）")
print(f"Test accuracy:  {model.accuracy(X_test, y_test):.4f}（测试集准确率）")
print(f"Weights: [{model.weights[0]:.4f}, {model.weights[1]:.4f}]（权重）")
print(f"Bias: {model.bias:.4f}（偏置）")


# ------------------------------------------------------------
# 分类指标（不止看准确率）
#   混淆矩阵四个格子（二分类）:
#     TP (真正例): 真实 1，预测 1  → 抓对了
#     TN (真负例): 真实 0，预测 0  → 放对了
#     FP (假正例): 真实 0，预测 1  → 误报（宁错杀）
#     FN (假负例): 真实 1，预测 0  → 漏报（漏掉了）
#   准确率 accuracy   = (TP+TN) / 全部          —— 整体判对比例
#   精确率 precision  = TP / (TP+FP)            —— 我说"是"的里面，多少真对？
#   召回率 recall     = TP / (TP+FN)            —— 真"是"的里面，我抓到多少？
#   F1                = 精确率与召回率的调和平均  —— 两者的平衡分
# 精确率和召回率天然此消彼长，癌症筛查等场景宁愿误报也不能漏报
# ------------------------------------------------------------
class ClassificationMetrics:
    """基于混淆矩阵的分类评估: accuracy / precision / recall / F1。"""

    def __init__(self, y_true, y_pred):
        # 逐对比较真实标签和预测标签，统计四个格子
        self.tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
        self.tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
        self.fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
        self.fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)

    def accuracy(self):
        total = self.tp + self.tn + self.fp + self.fn
        return (self.tp + self.tn) / total if total > 0 else 0

    def precision(self):
        denom = self.tp + self.fp  # 所有预测为 1 的样本
        return self.tp / denom if denom > 0 else 0

    def recall(self):
        denom = self.tp + self.fn  # 所有真实为 1 的样本
        return self.tp / denom if denom > 0 else 0

    def f1(self):
        # 调和平均: 惩罚精确率和召回率中明显偏低的那一个
        p = self.precision()
        r = self.recall()
        return 2 * p * r / (p + r) if (p + r) > 0 else 0

    def print_confusion_matrix(self):
        """按 Predicted/Actual 排布打印 2x2 混淆矩阵。"""
        print(f"\n  Confusion Matrix:（混淆矩阵）")
        print(f"                  Predicted")
        print(f"                  Pos   Neg")
        print(f"  Actual Pos     {self.tp:4d}  {self.fn:4d}")
        print(f"  Actual Neg     {self.fp:4d}  {self.tn:4d}")
        print(f"  （行 = 真实 Actual, 列 = 预测 Predicted; Pos = 正例, Neg = 负例）")

    def print_report(self):
        self.print_confusion_matrix()
        print(f"\n  Accuracy:  {self.accuracy():.4f}（准确率）")
        print(f"  Precision: {self.precision():.4f}（精确率）")
        print(f"  Recall:    {self.recall():.4f}（召回率）")
        print(f"  F1 Score:  {self.f1():.4f}（F1 分数）")


y_pred_test = [model.predict(x) for x in X_test]
print("\n=== Classification Report (Test Set) ===（分类报告 · 测试集）")
metrics = ClassificationMetrics(y_test, y_pred_test)
metrics.print_report()


# ------------------------------------------------------------
# 决策边界
#   p = 0.5 恰好对应 z = 0（sigmoid(0) = 0.5），
#   所以边界方程就是一条直线: w₁x₁ + w₂x₂ + b = 0
#   直线一侧 p > 0.5 判 1，另一侧 p < 0.5 判 0
#   这就是"逻辑回归名字里有回归、干的却是分类"的原因:
#   它先用回归的方式拟合直线，再用 sigmoid 做概率判决
# ------------------------------------------------------------
print("\n=== Decision Boundary ===（决策边界）")
w1, w2 = model.weights
b = model.bias
print(f"Decision boundary: {w1:.4f}*x1 + {w2:.4f}*x2 + {b:.4f} = 0（决策边界方程）")
if abs(w2) > 1e-10:
    print(f"Solved for x2:     x2 = {-w1/w2:.4f}*x1 + {-b/w2:.4f}（解出 x2 的直线形式）")

print("\nSample predictions near the boundary:（边界附近的样本预测:）")
test_points = [
    [3.0, 3.0],
    [3.5, 3.5],
    [4.0, 4.0],
    [2.5, 2.5],
    [5.0, 5.0],
]
for point in test_points:
    prob = model.predict_proba(point)
    pred = model.predict(point)
    print(f"  [{point[0]}, {point[1]}] -> prob={prob:.4f}, class={pred}"
          f"（点 [{point[0]}, {point[1]}] -> 概率 = {prob:.4f}, 类别 = {pred}）")


# ------------------------------------------------------------
# Softmax 回归: 逻辑回归的多分类推广（2 类 → K 类）
#   每个类别配一组权重，算出 K 个分数 scoreₖ
#   softmax 把 K 个分数变成和为 1 的概率分布:
#     pₖ = e^(scoreₖ) / Σⱼ e^(scoreⱼ)
#   损失: 多类交叉熵，只惩罚真实类别对应的 -log(p_真实)
# ------------------------------------------------------------
class SoftmaxRegression:
    """多分类 Softmax 回归（也叫多项逻辑回归）。"""

    def __init__(self, n_features, n_classes, learning_rate=0.01):
        self.n_features = n_features
        self.n_classes = n_classes
        self.lr = learning_rate
        # 权重变成"每个类别一行"的矩阵: weights[类别][特征]
        self.weights = [[0.0] * n_features for _ in range(n_classes)]
        self.biases = [0.0] * n_classes  # 每个类别一个偏置

    def softmax(self, scores):
        # 数值稳定技巧: 先减去最大分数再取 e^x，
        # 防止大分数导致 e^x 溢出（减常数不改变 softmax 结果）
        max_score = max(scores)
        exp_scores = [math.exp(s - max_score) for s in scores]
        total = sum(exp_scores)
        return [e / total for e in exp_scores]  # 归一化，和恰好为 1

    def predict_proba(self, x):
        # 对每个类别各算一个线性分数，再整体过 softmax
        scores = [
            sum(self.weights[k][j] * x[j] for j in range(self.n_features)) + self.biases[k]
            for k in range(self.n_classes)
        ]
        return self.softmax(scores)

    def predict(self, x):
        probs = self.predict_proba(x)
        return probs.index(max(probs))  # 概率最大的类别就是预测结果

    def fit(self, X, y, epochs=1000, print_every=200):
        """多类交叉熵 + 批量梯度下降，误差形式仍是 (pₖ - 真实值)。"""
        n = len(y)
        for epoch in range(epochs):
            grad_w = [[0.0] * self.n_features for _ in range(self.n_classes)]
            grad_b = [0.0] * self.n_classes
            total_loss = 0.0
            for i in range(n):
                probs = self.predict_proba(X[i])
                for k in range(self.n_classes):
                    # one-hot 目标: 真实类别为 1，其余为 0
                    target = 1.0 if y[i] == k else 0.0
                    error = probs[k] - target  # 与二分类同形的梯度误差项
                    for j in range(self.n_features):
                        grad_w[k][j] += error * X[i][j]
                    grad_b[k] += error
                # 损失只看真实类别被分到的概率: -log(p_真实)
                true_prob = max(probs[y[i]], 1e-15)  # 防止 log(0)
                total_loss -= math.log(true_prob)
            for k in range(self.n_classes):
                for j in range(self.n_features):
                    self.weights[k][j] -= self.lr * (grad_w[k][j] / n)
                self.biases[k] -= self.lr * (grad_b[k] / n)
            if epoch % print_every == 0:
                print(f"  Epoch {epoch:4d} | Loss: {total_loss / n:.4f}（第 {epoch:4d} 轮 | 损失: {total_loss / n:.4f}）")
        return self

    def accuracy(self, X, y):
        correct = sum(1 for i in range(len(y)) if self.predict(X[i]) == y[i])
        return correct / len(y)


# ------------------------------------------------------------
# 三分类数据: 平面上三个高斯团
#   类别 0 中心 (1,1)、类别 1 中心 (5,1)、类别 2 中心 (3,5)
# Softmax 会学出三条决策边界，把平面切成三个区域
# ------------------------------------------------------------
random.seed(42)
X_3class = []
y_3class = []

centers = [(1, 1), (5, 1), (3, 5)]
for label, (cx, cy) in enumerate(centers):
    for _ in range(50):
        X_3class.append([random.gauss(cx, 0.8), random.gauss(cy, 0.8)])
        y_3class.append(label)

combined = list(zip(X_3class, y_3class))
random.shuffle(combined)
X_3class, y_3class = zip(*combined)
X_3class = list(X_3class)
y_3class = list(y_3class)

split_3 = int(0.8 * len(X_3class))
X_train_3 = X_3class[:split_3]
y_train_3 = y_3class[:split_3]
X_test_3 = X_3class[split_3:]
y_test_3 = y_3class[split_3:]

print("\n=== Multi-class Softmax Regression (3 classes) ===（Softmax 多分类回归 · 3 个类别）")
softmax_model = SoftmaxRegression(n_features=2, n_classes=3, learning_rate=0.1)
softmax_model.fit(X_train_3, y_train_3, epochs=1000, print_every=200)
print(f"\nTrain accuracy: {softmax_model.accuracy(X_train_3, y_train_3):.4f}（训练集准确率）")
print(f"Test accuracy:  {softmax_model.accuracy(X_test_3, y_test_3):.4f}（测试集准确率）")

# 看概率分布: 三个概率加起来等于 1，模型对每个类别的"信心"一目了然
print("\nSample predictions:（样本预测:）")
for i in range(5):
    probs = softmax_model.predict_proba(X_test_3[i])
    pred = softmax_model.predict(X_test_3[i])
    print(f"  True: {y_test_3[i]}, Predicted: {pred}, Probs: [{', '.join(f'{p:.3f}' for p in probs)}]"
          f"（真实: {y_test_3[i]}, 预测: {pred}, 概率: [{', '.join(f'{p:.3f}' for p in probs)}]）")


# ------------------------------------------------------------
# 阈值调优: 0.5 不是铁律
#   降低阈值 → 更容易判 1 → 召回率↑ 精确率↓（宁可错杀不可放过）
#   提高阈值 → 更难判 1   → 精确率↑ 召回率↓（拿不准就放行）
#   适用场景举例: 癌症筛查用低阈值（漏诊代价大），
#                 垃圾邮件用高阈值（误删正常邮件代价大）
# ------------------------------------------------------------
print("\n=== Threshold Tuning ===（阈值调优）")
print("Default threshold: 0.5. Adjusting trades precision for recall.\n"
      "（默认阈值 0.5。调整阈值就是在精确率与召回率之间做权衡。）\n")

thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
# {:>10} 表示右对齐、宽度 10，把表格列对齐
print(f"{'Threshold':>10} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F1':>10}")
print("-" * 52)
print("（从左到右: 阈值 | 准确率 | 精确率 | 召回率 | F1 分数）")

for t in thresholds:
    y_pred_t = [1 if model.predict_proba(x) >= t else 0 for x in X_test]
    m = ClassificationMetrics(y_test, y_pred_t)
    print(f"{t:>10.1f} {m.accuracy():>10.4f} {m.precision():>10.4f} {m.recall():>10.4f} {m.f1():>10.4f}")


# ------------------------------------------------------------
# 反面教材: 为什么不能拿线性回归直接做分类
#   标签只有 0 和 1，线性回归的输出却可以小于 0 或大于 1，
#   "概率为 -0.3 或 1.7" 没有意义
#   下面用"学习时长 → 是否及格"的例子直观对比
# ------------------------------------------------------------
print("\n=== Why Linear Regression Fails for Classification ===（为什么线性回归做不了分类）")
print("Fitting linear regression to binary labels:（用线性回归拟合 0/1 二分类标签:）")
x_hours = list(range(1, 11))                    # 学习 1~10 小时
y_pass = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1]        # 4 小时以下不及格，5 小时起及格

# 复用正规方程拟合一条直线（与上一课 LinearRegressionNormal 相同的公式）
n = len(x_hours)
x_mean = sum(x_hours) / n
y_mean = sum(y_pass) / n
numerator = sum((x_hours[i] - x_mean) * (y_pass[i] - y_mean) for i in range(n))
denominator = sum((x_hours[i] - x_mean) ** 2 for i in range(n))
w_lin = numerator / denominator
b_lin = y_mean - w_lin * x_mean

print(f"\nLinear fit: y = {w_lin:.4f}*x + {b_lin:.4f}（线性拟合结果）")
# 对比两列: Linear 在两端跑出 [0,1] 之外; Sigmoid 始终在 (0,1) 内
print(f"{'Hours':>6} {'Actual':>8} {'Linear':>8} {'Sigmoid':>8}")
print("（列: 学习时长 | 真实标签 | 线性回归输出 | sigmoid 输出）")
for h, actual in zip(x_hours, y_pass):
    lin_pred = w_lin * h + b_lin                # 线性回归输出: 可能越界
    sig_pred = sigmoid(3 * (h - 4.5))           # sigmoid 输出: 恒在 (0,1)，4.5 小时附近翻转
    print(f"{h:>6d} {actual:>8d} {lin_pred:>8.3f} {sig_pred:>8.3f}")

print("\nLinear regression gives values outside [0, 1].（线性回归的输出会超出 [0, 1] 范围。）")
print("Logistic regression keeps everything in [0, 1] as probabilities.（逻辑回归的输出始终在 [0, 1] 内，可当作概率。）")


# ------------------------------------------------------------
# scikit-learn 对照 —— "Build It / Use It"
#   手写版（Build）结果应与生产库（Use）高度一致，
#   从而理解 sklearn 帮你封装了什么
#   注意: sklearn 的 LogisticRegression 默认带 L2 正则化并做了
#   特征标准化（此处显式用 StandardScaler），参数细节与手写版略有差异
# ------------------------------------------------------------
print("\n=== Scikit-learn Comparison ===（scikit-learn 对照）")
try:
    # sklearn 是可选依赖: 未安装时优雅降级，前面的手写部分照常运行
    from sklearn.linear_model import LogisticRegression as SklearnLR
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    from sklearn.metrics import confusion_matrix, classification_report
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    import numpy as np

    # 用 NumPy 重建同样分布的两团高斯数据（每类 100 个）
    np.random.seed(42)
    X_0 = np.random.randn(100, 2) + [2, 2]
    X_1 = np.random.randn(100, 2) + [5, 5]
    X_sk = np.vstack([X_0, X_1])
    y_sk = np.array([0] * 100 + [1] * 100)

    # 80/20 划分（sklearn 版会先随机打乱再划分）
    X_tr, X_te, y_tr, y_te = train_test_split(X_sk, y_sk, test_size=0.2, random_state=42)

    # 标准化: fit 在训练集上算 μ/σ，再同样变换测试集（防止数据泄漏）
    scaler = StandardScaler()
    X_tr_sc = scaler.fit_transform(X_tr)
    X_te_sc = scaler.transform(X_te)

    lr = SklearnLR()
    lr.fit(X_tr_sc, y_tr)
    y_pred_sk = lr.predict(X_te_sc)

    print(f"Accuracy:  {accuracy_score(y_te, y_pred_sk):.4f}（准确率）")
    print(f"Precision: {precision_score(y_te, y_pred_sk):.4f}（精确率）")
    print(f"Recall:    {recall_score(y_te, y_pred_sk):.4f}（召回率）")
    print(f"F1:        {f1_score(y_te, y_pred_sk):.4f}（F1 分数）")
    print(f"\nConfusion Matrix:（混淆矩阵）\n{confusion_matrix(y_te, y_pred_sk)}")
    print(f"\nClassification Report:（完整分类报告）\n{classification_report(y_te, y_pred_sk)}")

except ImportError:
    # 环境里没有 scikit-learn 时不报错，保证脚本可独立运行
    print("scikit-learn not installed. Install with: pip install scikit-learn"
          "（未安装 scikit-learn，可用 pip install scikit-learn 安装）")
    print("The from-scratch implementations above work without any dependencies."
          "（上面的手写实现无需任何第三方依赖即可运行）")
