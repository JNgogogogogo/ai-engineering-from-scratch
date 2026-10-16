# ============================================================
# 线性回归 —— 从零实现 + scikit-learn 对照
# 课程文档: phases/02-ml-fundamentals/02-linear-regression/docs/en.md
# 内容: 单变量梯度下降、正规方程闭式解、多元回归、
#       多项式回归、岭回归(L2 正则化)、训练/测试集划分、sklearn 对比
# 运行: python3 linear_regression.py （零第三方依赖即可跑通）
# ============================================================
import random
import math


# ------------------------------------------------------------
# 1. 生成模拟数据
#    真实关系: y = 3x + 7，再叠加标准差为 2.0 的高斯噪声
# ------------------------------------------------------------
TRUE_W = 3.0     # 真实斜率（权重 w）
TRUE_B = 7.0     # 真实截距（偏置 b）
N_SAMPLES = 100  # 样本数量

random.seed(42)  # 固定随机种子，保证每次运行结果完全可复现
X = [random.uniform(0, 10) for _ in range(N_SAMPLES)]        # 特征: 0~10 之间的均匀分布
y = [TRUE_W * x + TRUE_B + random.gauss(0, 2.0) for x in X]  # 标签: 真值 + 高斯噪声 N(0, 2)

print(f"Generated {N_SAMPLES} samples（已生成 {N_SAMPLES} 个样本）")
print(f"True relationship: y = {TRUE_W}x + {TRUE_B} (+ noise)（真实关系: y = {TRUE_W}x + {TRUE_B} + 噪声）")
print(f"First 5 points: {[(round(X[i], 2), round(y[i], 2)) for i in range(5)]}"
      f"（前 5 个样本点: {[(round(X[i], 2), round(y[i], 2)) for i in range(5)]}）")


# ------------------------------------------------------------
# 2. 单变量线性回归 —— 批量梯度下降（Batch Gradient Descent）
#    模型:   ŷ = w·x + b
#    损失:   MSE = (1/n)·Σ(ŷᵢ - yᵢ)²
#    梯度:   ∂MSE/∂w = (2/n)·Σ(ŷᵢ - yᵢ)·xᵢ
#            ∂MSE/∂b = (2/n)·Σ(ŷᵢ - yᵢ)
#    更新:   w ← w - lr·∂MSE/∂w ，  b ← b - lr·∂MSE/∂b
# ------------------------------------------------------------
class LinearRegression:
    """单变量线性回归，用批量梯度下降最小化均方误差（MSE）。"""

    def __init__(self, learning_rate=0.01):
        self.w = 0.0              # 斜率，初始化为 0（也可随机初始化）
        self.b = 0.0              # 截距
        self.lr = learning_rate   # 学习率：每步沿负梯度方向前进的步长
        self.cost_history = []    # 记录每轮损失，便于观察收敛过程

    def predict(self, X):
        # 对每个样本计算 ŷ = w·x + b（纯 Python 用列表推导模拟向量化）
        return [self.w * x + self.b for x in X]

    def compute_cost(self, X, y):
        """均方误差 MSE = (1/n)·Σ(预测值 - 真实值)²"""
        predictions = self.predict(X)
        n = len(y)
        cost = sum((pred - actual) ** 2 for pred, actual in zip(predictions, y)) / n
        return cost

    def compute_gradients(self, X, y):
        """对 MSE 分别求 w、b 的偏导数（链式法则展开后的闭式结果）。"""
        predictions = self.predict(X)
        n = len(y)
        # ∂L/∂w = (2/n)·Σ(ŷᵢ - yᵢ)·xᵢ —— 每个误差乘以对应的特征值
        dw = (2 / n) * sum((pred - actual) * x for pred, actual, x in zip(predictions, y, X))
        # ∂L/∂b = (2/n)·Σ(ŷᵢ - yᵢ) —— 只需要对误差求平均
        db = (2 / n) * sum(pred - actual for pred, actual in zip(predictions, y))
        return dw, db

    def fit(self, X, y, epochs=1000, print_every=200):
        """训练主循环：反复执行「计算梯度 → 沿负梯度更新参数」。"""
        for epoch in range(epochs):
            dw, db = self.compute_gradients(X, y)  # ① 计算当前梯度
            self.w -= self.lr * dw                 # ② 梯度下降更新 w
            self.b -= self.lr * db                 # ③ 梯度下降更新 b
            cost = self.compute_cost(X, y)         # ④ 记录当前损失
            self.cost_history.append(cost)
            if epoch % print_every == 0:           # 每隔 print_every 轮打印一次进度
                print(f"  Epoch {epoch:4d} | Cost: {cost:.4f} | w: {self.w:.4f} | b: {self.b:.4f}"
                      f"（第 {epoch:4d} 轮 | 损失: {cost:.4f}）")
        return self  # 返回 self，支持链式调用

    def r_squared(self, X, y):
        """决定系数 R² = 1 - SS_res/SS_tot，越接近 1 拟合越好。"""
        predictions = self.predict(X)
        y_mean = sum(y) / len(y)
        ss_res = sum((actual - pred) ** 2 for actual, pred in zip(y, predictions))  # 残差平方和
        ss_tot = sum((actual - y_mean) ** 2 for actual in y)                        # 总平方和
        return 1 - (ss_res / ss_tot)


print("\n=== Training Linear Regression (Gradient Descent) ===（训练线性回归 · 梯度下降）")
model = LinearRegression(learning_rate=0.03)
model.fit(X, y, epochs=1000, print_every=200)
print(f"\nLearned: y = {model.w:.4f}x + {model.b:.4f}（学到的模型）")
print(f"True:    y = {TRUE_W}x + {TRUE_B}（真实模型）")
print(f"R-squared: {model.r_squared(X, y):.4f}（R² 决定系数）")


# ------------------------------------------------------------
# 3. 正规方程（Normal Equation，闭式解）—— 不用迭代，一步求出最优参数
#    对单变量: w = Σ(xᵢ-x̄)(yᵢ-ȳ) / Σ(xᵢ-x̄)²，b = ȳ - w·x̄
#    本质：把 MSE 的梯度置零后直接解方程（协方差 / 方差之比）
# ------------------------------------------------------------
class LinearRegressionNormal:
    """单变量线性回归，用正规方程（闭式解）直接求全局最优参数。"""

    def __init__(self):
        self.w = 0.0  # 斜率
        self.b = 0.0  # 截距

    def fit(self, X, y):
        """闭式解：一步算出全局最优的 w 和 b，无需任何迭代。"""
        n = len(X)
        x_mean = sum(X) / n  # x̄：特征均值
        y_mean = sum(y) / n  # ȳ：标签均值
        # 分子 = Σ(xᵢ-x̄)(yᵢ-ȳ)，即 x 与 y 的（未除 n 的）协方差
        numerator = sum((X[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        # 分母 = Σ(xᵢ-x̄)²，即 x 的（未除 n 的）方差
        denominator = sum((X[i] - x_mean) ** 2 for i in range(n))
        self.w = numerator / denominator   # 斜率 = 协方差 / 方差
        self.b = y_mean - self.w * x_mean  # 均值点 (x̄, ȳ) 必在回归直线上，由此反解截距
        return self

    def predict(self, X):
        return [self.w * x + self.b for x in X]

    def r_squared(self, X, y):
        """决定系数 R²，与梯度下降版本含义相同。"""
        predictions = self.predict(X)
        y_mean = sum(y) / len(y)
        ss_res = sum((actual - pred) ** 2 for actual, pred in zip(y, predictions))
        ss_tot = sum((actual - y_mean) ** 2 for actual in y)
        return 1 - (ss_res / ss_tot)


print("\n=== Normal Equation (Closed-Form) ===（正规方程 · 闭式解）")
model_normal = LinearRegressionNormal()
model_normal.fit(X, y)
print(f"Learned: y = {model_normal.w:.4f}x + {model_normal.b:.4f}（学到的模型）")
print(f"R-squared: {model_normal.r_squared(X, y):.4f}（R² 决定系数）")


# ------------------------------------------------------------
# 4. 多元线性回归 —— 多特征 + 梯度下降
#    模型: ŷ = w₁x₁ + w₂x₂ + ... + wⱼxⱼ + b
#    每个参数的梯度公式与单变量相同，只是要对每个特征各算一次
# ------------------------------------------------------------
class MultipleLinearRegression:
    """多元线性回归：特征为向量，对每个权重分别做梯度下降。"""

    def __init__(self, n_features, learning_rate=0.01):
        self.weights = [0.0] * n_features  # 权重向量 w，逐特征初始化为 0
        self.bias = 0.0                    # 偏置 b
        self.lr = learning_rate            # 学习率
        self.cost_history = []             # 每轮损失记录

    def predict_single(self, x):
        # 单个样本的预测 = 特征与权重的内积 + 偏置
        return sum(w * xi for w, xi in zip(self.weights, x)) + self.bias

    def predict(self, X):
        return [self.predict_single(x) for x in X]

    def compute_cost(self, X, y):
        """MSE，与单变量版本相同。"""
        predictions = self.predict(X)
        n = len(y)
        return sum((pred - actual) ** 2 for pred, actual in zip(predictions, y)) / n

    def fit(self, X, y, epochs=1000, print_every=200):
        """批量梯度下降：每轮同时更新所有权重和偏置。"""
        n = len(y)
        n_features = len(X[0])
        for epoch in range(epochs):
            predictions = self.predict(X)
            # 一次性算出所有误差 (ŷᵢ - yᵢ)，供所有梯度复用
            errors = [pred - actual for pred, actual in zip(predictions, y)]
            for j in range(n_features):
                # ∂L/∂wⱼ = (2/n)·Σ(误差ᵢ · xᵢⱼ) —— 误差与第 j 个特征的相关性
                grad = (2 / n) * sum(errors[i] * X[i][j] for i in range(n))
                self.weights[j] -= self.lr * grad
            # ∂L/∂b = (2/n)·Σ(误差ᵢ) —— 偏置梯度与特征无关
            grad_b = (2 / n) * sum(errors)
            self.bias -= self.lr * grad_b
            cost = self.compute_cost(X, y)
            self.cost_history.append(cost)
            if epoch % print_every == 0:
                print(f"  Epoch {epoch:4d} | Cost: {cost:.4f}（第 {epoch:4d} 轮 | 损失: {cost:.4f}）")
        return self

    def r_squared(self, X, y):
        """决定系数 R²。"""
        predictions = self.predict(X)
        y_mean = sum(y) / len(y)
        ss_res = sum((actual - pred) ** 2 for actual, pred in zip(y, predictions))
        ss_tot = sum((actual - y_mean) ** 2 for actual in y)
        return 1 - (ss_res / ss_tot)


# ------------------------------------------------------------
# 标准化（z-score）：把每列特征变换为均值 0、标准差 1
# 公式: x' = (x - μ) / σ
# 目的: 各特征量纲差异大时（如面积 500~3000、卧室数 1~5），
#       不标准化会让损失曲面呈狭长椭圆，梯度下降来回震荡、收敛极慢；
#       标准化后曲面更"圆"，各维度收敛速度一致
# ------------------------------------------------------------
def standardize(X):
    """按列标准化（z-score），返回 (标准化数据, 各列均值, 各列标准差)。"""
    n_features = len(X[0])
    n_samples = len(X)
    # 每列的均值 μⱼ
    means = [sum(X[i][j] for i in range(n_samples)) / n_samples for j in range(n_features)]
    stds = []
    for j in range(n_features):
        # 每列的总体方差 σ²（除以 n 而非 n-1，教学场景下差异可忽略）
        variance = sum((X[i][j] - means[j]) ** 2 for i in range(n_samples)) / n_samples
        stds.append(variance ** 0.5)
    X_scaled = []
    for i in range(n_samples):
        # z-score: (x - μ) / σ；标准差为 0 的常数列直接置 0，避免除零错误
        row = [(X[i][j] - means[j]) / stds[j] if stds[j] > 0 else 0 for j in range(n_features)]
        X_scaled.append(row)
    return X_scaled, means, stds


# ------------------------------------------------------------
# 生成房价模拟数据（3 个特征）
# 真实关系: 房价 = 50·面积 + 10000·卧室数 - 1000·房龄 + 50000 + 噪声
# ------------------------------------------------------------
random.seed(42)
N = 100
X_multi = []
y_multi = []
for _ in range(N):
    size = random.uniform(500, 3000)       # 特征 1: 面积 500~3000 平方单位
    bedrooms = random.randint(1, 5)        # 特征 2: 卧室数 1~5
    age = random.uniform(0, 50)            # 特征 3: 房龄 0~50 年
    price = 50 * size + 10000 * bedrooms - 1000 * age + 50000 + random.gauss(0, 20000)
    X_multi.append([size, bedrooms, age])
    y_multi.append(price)

# 目标 y 也做同样的 z-score 标准化：让损失值量级适中、训练更平稳
y_mean_val = sum(y_multi) / len(y_multi)
y_std_val = (sum((yi - y_mean_val) ** 2 for yi in y_multi) / len(y_multi)) ** 0.5
y_scaled = [(yi - y_mean_val) / y_std_val for yi in y_multi]

X_scaled, x_means, x_stds = standardize(X_multi)

print("\n=== Multiple Linear Regression (3 features) ===（多元线性回归 · 3 个特征）")
print("Features: house size, bedrooms, age（特征: 房屋面积、卧室数、房龄）")
multi_model = MultipleLinearRegression(n_features=3, learning_rate=0.01)
multi_model.fit(X_scaled, y_scaled, epochs=1000, print_every=200)
print(f"\nWeights (standardized): {[round(w, 4) for w in multi_model.weights]}（标准化后的权重）")
print(f"Bias (standardized): {multi_model.bias:.4f}（标准化后的偏置）")
print(f"R-squared: {multi_model.r_squared(X_scaled, y_scaled):.4f}（R² 决定系数）")


# ------------------------------------------------------------
# 5. 多项式回归 —— 把线性回归用在「构造出来的特征」上
#    核心技巧: 令 x₁ = x, x₂ = x², ..., x_d = x^d，
#    则 y = w₁x + w₂x² + ... + w_d·x^d + b 对参数来说仍然是线性的！
# ------------------------------------------------------------
class PolynomialRegression:
    """多项式回归：先把 x 扩展成 [x, x², ..., x^d]，再跑多元线性回归。"""

    def __init__(self, degree, learning_rate=0.01):
        self.degree = degree              # 多项式最高次数 d
        self.weights = [0.0] * degree     # 每个多项式项一个权重
        self.bias = 0.0                   # 偏置
        self.lr = learning_rate

    def make_features(self, X):
        # 特征构造: 把标量 x 扩展为特征行 [x, x², ..., x^d]
        return [[x ** (d + 1) for d in range(self.degree)] for x in X]

    def predict(self, X):
        features = self.make_features(X)
        return [sum(w * f for w, f in zip(self.weights, row)) + self.bias for row in features]

    def fit(self, X, y, epochs=1000, print_every=200):
        features = self.make_features(X)  # 特征只构造一次，循环里直接复用
        n = len(y)
        for epoch in range(epochs):
            predictions = [sum(w * f for w, f in zip(self.weights, row)) + self.bias for row in features]
            errors = [pred - actual for pred, actual in zip(predictions, y)]
            for j in range(self.degree):
                # 与多元回归完全相同的梯度公式，只是特征换成了多项式项
                grad = (2 / n) * sum(errors[i] * features[i][j] for i in range(n))
                self.weights[j] -= self.lr * grad
            grad_b = (2 / n) * sum(errors)
            self.bias -= self.lr * grad_b
            if epoch % print_every == 0:
                cost = sum(e ** 2 for e in errors) / n
                print(f"  Epoch {epoch:4d} | Cost: {cost:.6f}（第 {epoch:4d} 轮 | 损失: {cost:.6f}）")
        return self

    def r_squared(self, X, y):
        """决定系数 R²。"""
        predictions = self.predict(X)
        y_mean = sum(y) / len(y)
        ss_res = sum((actual - pred) ** 2 for actual, pred in zip(y, predictions))
        ss_tot = sum((actual - y_mean) ** 2 for actual in y)
        return 1 - (ss_res / ss_tot)


# ------------------------------------------------------------
# 生成非线性数据: y = 0.5x² - 2x + 3 + 噪声
# 注意缩放: 多项式特征数值增长极快（x^5 可达几千），
#           不缩放的话梯度会爆炸，训练直接发散
# ------------------------------------------------------------
random.seed(42)
X_poly = [x / 10.0 for x in range(0, 50)]  # x 取 0 ~ 4.9，步长 0.1
y_poly = [0.5 * x ** 2 - 2 * x + 3 + random.gauss(0, 1.0) for x in X_poly]

# x 除以最大绝对值做简单归一化；y 做 z-score 标准化
x_max = max(abs(x) for x in X_poly)
X_poly_norm = [x / x_max for x in X_poly]
y_poly_mean = sum(y_poly) / len(y_poly)
y_poly_std = (sum((yi - y_poly_mean) ** 2 for yi in y_poly) / len(y_poly)) ** 0.5
y_poly_norm = [(yi - y_poly_mean) / y_poly_std for yi in y_poly]

print("\n=== Polynomial Regression ===（多项式回归）")
print("True relationship: y = 0.5x^2 - 2x + 3（真实关系: y = 0.5x² - 2x + 3）")

print("\nDegree 2:（二次多项式 —— 与真实关系匹配）")
poly2 = PolynomialRegression(degree=2, learning_rate=0.1)
poly2.fit(X_poly_norm, y_poly_norm, epochs=2000, print_every=500)
print(f"  R-squared: {poly2.r_squared(X_poly_norm, y_poly_norm):.4f}（R² 决定系数）")

print("\nDegree 5:（五次多项式 —— 更灵活，容易过拟合）")
poly5 = PolynomialRegression(degree=5, learning_rate=0.1)
poly5.fit(X_poly_norm, y_poly_norm, epochs=2000, print_every=500)
print(f"  R-squared: {poly5.r_squared(X_poly_norm, y_poly_norm):.4f}（R² 决定系数）")


# ------------------------------------------------------------
# 6. 岭回归（Ridge / L2 正则化）
#    损失: L = MSE + α·Σwⱼ²   （正则项一般不惩罚偏置 b）
#    梯度: ∂L/∂wⱼ = (2/n)·Σ(误差ᵢ·xᵢⱼ) + 2α·wⱼ
#    效果: 惩罚大权重 → 权重整体被「压小」→ 模型更平滑、更抗过拟合
# ------------------------------------------------------------
class RidgeRegression:
    """岭回归：在 MSE 基础上叠加 L2 惩罚项 α·Σw²。"""

    def __init__(self, n_features, learning_rate=0.01, alpha=1.0):
        self.weights = [0.0] * n_features  # 权重向量
        self.bias = 0.0                    # 偏置（不受正则化约束）
        self.lr = learning_rate
        self.alpha = alpha                 # 正则化强度: α 越大，权重被压得越小

    def predict_single(self, x):
        return sum(w * xi for w, xi in zip(self.weights, x)) + self.bias

    def predict(self, X):
        return [self.predict_single(x) for x in X]

    def fit(self, X, y, epochs=1000, print_every=200):
        """梯度下降，在普通梯度上叠加 L2 惩罚项的梯度。"""
        n = len(y)
        n_features = len(X[0])
        for epoch in range(epochs):
            predictions = self.predict(X)
            errors = [pred - actual for pred, actual in zip(predictions, y)]
            # 数据拟合项: MSE
            mse = sum(e ** 2 for e in errors) / n
            # L2 惩罚项: α·Σw²（不包含偏置 b）
            reg_term = self.alpha * sum(w ** 2 for w in self.weights)
            cost = mse + reg_term
            for j in range(n_features):
                grad = (2 / n) * sum(errors[i] * X[i][j] for i in range(n))  # MSE 的梯度
                grad += 2 * self.alpha * self.weights[j]                     # L2 惩罚的梯度（权重衰减）
                self.weights[j] -= self.lr * grad
            grad_b = (2 / n) * sum(errors)  # 偏置梯度不含正则项
            self.bias -= self.lr * grad_b
            if epoch % print_every == 0:
                print(f"  Epoch {epoch:4d} | Cost: {cost:.4f} | L2 penalty: {reg_term:.4f}"
                      f"（第 {epoch:4d} 轮 | 损失: {cost:.4f} | L2 惩罚项: {reg_term:.4f}）")
        return self


print("\n=== Ridge Regression (L2 Regularization) ===（岭回归 · L2 正则化）")
print("Same data as multiple regression, alpha=0.1（与多元回归同一份数据，alpha=0.1）")
ridge = RidgeRegression(n_features=3, learning_rate=0.01, alpha=0.1)
ridge.fit(X_scaled, y_scaled, epochs=1000, print_every=200)
print(f"\nRidge weights: {[round(w, 4) for w in ridge.weights]}（岭回归权重）")
print(f"Plain weights: {[round(w, 4) for w in multi_model.weights]}（无正则化的权重）")
print("Ridge weights are smaller due to the L2 penalty.（由于 L2 惩罚，岭回归的权重更小）")


# ------------------------------------------------------------
# 7. 训练集 / 测试集划分 —— 检验泛化能力
#    用 80% 数据训练、20% 数据测试；
#    若测试集 R² 明显低于训练集 R²，说明模型过拟合（或数据太少）
# ------------------------------------------------------------
print("\n=== Train/Test Split Comparison ===（训练集 / 测试集对比）")
split_idx = int(0.8 * len(X))  # 前 80% 作训练集，后 20% 作测试集
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]

model_split = LinearRegression(learning_rate=0.005)
model_split.fit(X_train, y_train, epochs=1000, print_every=500)
print(f"\nTrain R-squared: {model_split.r_squared(X_train, y_train):.4f}（训练集 R²）")
print(f"Test R-squared:  {model_split.r_squared(X_test, y_test):.4f}（测试集 R²）")
print(f"Learned: y = {model_split.w:.4f}x + {model_split.b:.4f}（学到的模型）")
print(f"True:    y = {TRUE_W}x + {TRUE_B}（真实模型）")


# ------------------------------------------------------------
# 8. scikit-learn 对照 —— "Build It / Use It"
#    前面都是手写实现（Build），这里用生产级库完成同样的任务（Use），
#    验证手写结果与工业实现一致，理解库到底帮你封装了什么
# ------------------------------------------------------------
print("\n=== Scikit-learn Comparison ===（scikit-learn 对照）")
try:
    # sklearn 是可选依赖：未安装时优雅降级，前面的手写部分照常运行
    from sklearn.linear_model import LinearRegression as SklearnLR
    from sklearn.linear_model import Ridge as SklearnRidge
    from sklearn.preprocessing import PolynomialFeatures, StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, r2_score
    import numpy as np

    # 用 NumPy 重建同样分布的数据: y = 3x + 7 + N(0, 2)
    np.random.seed(42)
    X_sk = np.random.uniform(0, 10, (100, 1))
    y_sk = 3.0 * X_sk.squeeze() + 7.0 + np.random.normal(0, 2.0, 100)

    # 80/20 划分（sklearn 版会先随机打乱再划分）
    X_tr, X_te, y_tr, y_te = train_test_split(X_sk, y_sk, test_size=0.2, random_state=42)

    # 线性回归：底层是与正规方程等价的闭式解（基于最小二乘 OLS）
    lr = SklearnLR()
    lr.fit(X_tr, y_tr)
    y_pred = lr.predict(X_te)

    print(f"Coefficient (w): {lr.coef_[0]:.4f}（系数 w）")
    print(f"Intercept (b): {lr.intercept_:.4f}（截距 b）")
    print(f"R-squared (test): {r2_score(y_te, y_pred):.4f}（测试集 R²）")
    print(f"MSE (test): {mean_squared_error(y_te, y_pred):.4f}（测试集均方误差）")

    # 二阶多项式特征：等价于前面的 PolynomialRegression(degree=2)
    poly = PolynomialFeatures(degree=2, include_bias=False)
    X_poly_sk = poly.fit_transform(X_tr)
    X_poly_test = poly.transform(X_te)
    lr_poly = SklearnLR()
    lr_poly.fit(X_poly_sk, y_tr)
    print(f"\nPolynomial degree 2 R-squared: {r2_score(y_te, lr_poly.predict(X_poly_test)):.4f}"
          f"（二阶多项式 R²）")

    # 标准化 + 岭回归：对应手写的 standardize() + RidgeRegression
    scaler = StandardScaler()
    X_tr_sc = scaler.fit_transform(X_tr)
    X_te_sc = scaler.transform(X_te)
    ridge_sk = SklearnRidge(alpha=1.0)
    ridge_sk.fit(X_tr_sc, y_tr)
    print(f"Ridge R-squared: {r2_score(y_te, ridge_sk.predict(X_te_sc)):.4f}（岭回归 R²）")

except ImportError:
    # 环境里没有 scikit-learn 时不报错，保证脚本可独立运行
    print("scikit-learn not installed. Install with: pip install scikit-learn"
          "（未安装 scikit-learn，可用 pip install scikit-learn 安装）")
    print("The from-scratch implementations above work without any dependencies."
          "（上面的手写实现无需任何第三方依赖即可运行）")
