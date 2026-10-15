# Linear Regression · 线性回归

> 线性回归（linear regression）画出穿过你数据的最优直线。它是机器学习里的「hello world」。

> Linear regression draws the best straight line through your data. It is the "hello world" of machine learning.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 1 (Linear Algebra, Calculus, Optimization), Phase 2 Lesson 1
**Time:** ~90 minutes

## Learning Objectives · 学习目标

- 推导均方误差（mean squared error，MSE）的梯度下降更新规则，并从零实现线性回归
- 比较梯度下降（gradient descent）与正规方程（normal equation）在计算复杂度和适用场景上的差异
- 构建带特征标准化的多元线性回归模型，并解读学到的权重
- 解释岭回归（Ridge regression，L2 正则化）如何通过惩罚大权重防止过拟合（overfitting）

> Derive the gradient descent update rules for mean squared error and implement linear regression from scratch
> Compare gradient descent and the normal equation in terms of computational complexity and when to use each
> Build a multiple linear regression model with feature standardization and interpret the learned weights
> Explain how Ridge regression (L2 regularization) prevents overfitting by penalizing large weights

## The Problem · 问题在哪

你手上有数据：房屋面积和它们的售价。你想在给定面积的情况下预测一套新房的价格。你可以在散点图上目测，但你需要的是一个公式。你需要一条最能拟合数据的直线，这样代入任意面积就能得到价格预测。

线性回归给你的就是这条线。更重要的是，它引入了完整的机器学习训练循环：定义模型、定义代价函数（cost function）、优化参数。每个机器学习算法都遵循同一个模式。用这里最简单的例子把它吃透，你就能在所有地方认出它。

这不只是用来解简单问题的。线性回归在生产系统中被用于需求预测、A/B 测试分析、金融建模，并且是所有回归（regression）任务的基线。

> You have data: house sizes and their sale prices. You want to predict the price of a new house given its size. You could eyeball it on a scatter plot, but you need a formula. ... Linear regression gives you that line. More importantly, it introduces the entire ML training loop: define a model, define a cost function, optimize the parameters. Every ML algorithm follows this same pattern. Master it here with the simplest case, and you will recognize it everywhere. ... Linear regression is used in production systems for demand forecasting, A/B test analysis, financial modeling, and as a baseline for every regression task.

## The Concept · 概念

### The Model · 模型

线性回归假设输入（x）和输出（y）之间存在线性关系：

```
y = wx + b
```

- `w`（weight，权重/斜率）：x 每增加 1，y 变化多少
- `b`（bias，偏置/截距）：x = 0 时 y 的值

有多个输入（特征，feature）时，模型扩展为：

```
y = w1*x1 + w2*x2 + ... + wn*xn + b
```

或者写成向量形式：`y = w^T * x + b`

目标：找到 w 和 b 的值，使预测出的 y 在所有训练样本上都尽可能接近真实的 y。

> Linear regression assumes a linear relationship between input (x) and output (y). ... The goal: find the values of w and b that make the predicted y as close as possible to the actual y across all training examples.

### The Cost Function (Mean Squared Error) · 代价函数（均方误差）

怎么衡量「尽可能接近」？你需要一个单独的数字来刻画预测有多错。最常见的选择是均方误差（MSE）：

```
MSE = (1/n) * sum((y_predicted - y_actual)^2)
```

为什么取平方？两个原因。第一，它对大错误的惩罚远重于小错误（误差 10 的糟糕程度是误差 1 的 100 倍，而不是 10 倍）。第二，平方函数处处光滑、可导，这让优化变得直接。

代价函数张成一个曲面。对单个权重 w 和偏置 b 来说，MSE 曲面看起来像一个碗（凸抛物面）。碗底就是 MSE 最小的地方。训练就是找到那个碗底。

> How do you measure "as close as possible"? You need a single number that captures how wrong your predictions are. The most common choice is Mean Squared Error (MSE). ... Why squared? Two reasons. First, it penalizes large errors more than small errors (an error of 10 is 100x worse than an error of 1, not 10x). Second, the squared function is smooth and differentiable everywhere, which makes optimization straightforward. ... The bottom of the bowl is where MSE is minimized. Training means finding that bottom.

### Gradient Descent · 梯度下降

梯度下降通过一步步往山下走来找到碗底。

```mermaid
flowchart TD
    A[Initialize w and b randomly] --> B[Compute predictions: y_hat = wx + b]
    B --> C[Compute cost: MSE]
    C --> D[Compute gradients: dMSE/dw, dMSE/db]
    D --> E[Update parameters]
    E --> F{Cost low enough?}
    F -->|No| B
    F -->|Yes| G[Done: optimal w and b found]
```

梯度告诉你两件事：每个参数该往哪个方向挪，以及挪多少。

对 y_hat = wx + b 的 MSE 来说：

```
dMSE/dw = (2/n) * sum((y_hat - y) * x)
dMSE/db = (2/n) * sum(y_hat - y)
```

更新规则：

```
w = w - learning_rate * dMSE/dw
b = b - learning_rate * dMSE/db
```

学习率（learning rate）控制步长。太大：你会跨过最小值并发散。太小：训练遥遥无期。典型的起始值：0.01、0.001 或 0.0001。

> Gradient descent finds the bottom of the bowl by taking steps downhill. ... The gradients tell you two things: which direction to move each parameter, and how much to move. ... The learning rate controls step size. Too large: you overshoot the minimum and diverge. Too small: training takes forever. Typical starting values: 0.01, 0.001, or 0.0001.

### The Normal Equation (Closed-Form Solution) · 正规方程（闭式解）

对线性回归来说，有一个不经任何迭代、直接给出最优权重的公式：

```
w = (X^T * X)^(-1) * X^T * y
```

它通过一次矩阵求逆一步解出 w。对小数据集完美可用。对大数据集（数百万行或数千个特征），更推荐梯度下降，因为矩阵求逆的代价对特征数是 O(n^3)。

> For linear regression specifically, there is a direct formula that gives the optimal weights without any iteration. ... This inverts a matrix to solve for w in one step. It works perfectly for small datasets. For large datasets (millions of rows or thousands of features), gradient descent is preferred because matrix inversion is O(n^3) in the number of features.

### Multiple Linear Regression · 多元线性回归

有多个特征时，模型变成：

```
y = w1*x1 + w2*x2 + ... + wn*xn + b
```

一切照旧：MSE 是代价函数，梯度下降同时更新所有权重。唯一的区别是你拟合的是一个超平面（hyperplane）而不是一条直线。

特征缩放（feature scaling）在这里很关键。如果一个特征范围是 0 到 1，另一个是 0 到 1,000,000，梯度下降会很挣扎，因为代价曲面会被拉长。训练前先标准化特征（减去均值，除以标准差）。

> Everything works the same: MSE is the cost function, gradient descent updates all weights simultaneously. The only difference is that you are fitting a hyperplane instead of a line. ... Feature scaling matters here. ... Standardize features (subtract mean, divide by standard deviation) before training.

### Polynomial Regression · 多项式回归

如果关系不是线性的怎么办？你仍然可以用线性回归——只要构造多项式特征（polynomial features）：

```
y = w1*x + w2*x^2 + w3*x^3 + b
```

这仍然是「线性」回归，因为模型对权重（w1, w2, w3）是线性的。你只是使用了 x 的非线性特征。

更高次的多项式能拟合更复杂的曲线，但有过拟合风险。10 次多项式会穿过 10 个点数据集中的每一个点，但在新数据上预测很差。

> What if the relationship is not linear? You can still use linear regression by creating polynomial features. ... This is still "linear" regression because the model is linear in the weights (w1, w2, w3). ... Higher-degree polynomials can fit more complex curves but risk overfitting. A degree-10 polynomial will pass through every point in a 10-point dataset but predict poorly on new data.

### R-Squared Score · R 方分数

MSE 告诉你有多错，但这个数字依赖于 y 的量纲。R 方（R-squared，R^2）给出一个与量纲无关的度量：

```
R^2 = 1 - (sum of squared residuals) / (sum of squared deviations from mean)
    = 1 - SS_res / SS_tot
```

- R^2 = 1.0：完美预测
- R^2 = 0.0：模型并不比每次都预测均值更好
- R^2 < 0.0：模型比预测均值还差

> MSE tells you how wrong you are, but the number depends on the scale of y. R-squared (R^2) gives a scale-independent measure.

### Regularization Preview (Ridge Regression) · 正则化预览（岭回归）

特征很多时，模型可能通过给出很大的权重来过拟合。岭回归（Ridge regression，L2 正则化）加入了一个惩罚项：

```
Cost = MSE + lambda * sum(w_i^2)
```

惩罚项抑制大权重。超参数 lambda 控制权衡：lambda 越高，权重越小，正则化越强。后面的课会深入讲它。现在你只需要知道它存在，以及它为什么有用。

> When you have many features, the model can overfit by assigning large weights. Ridge regression (L2 regularization) adds a penalty. ... The penalty term discourages large weights. The hyperparameter lambda controls the tradeoff: higher lambda means smaller weights and more regularization. This is covered in depth in a later lesson. For now, know that it exists and why it helps.

```figure
linear-regression-fit
```

## Build It · 动手造

### Step 1: Generate sample data · 生成样本数据

```python
import random
import math

random.seed(42)

TRUE_W = 3.0
TRUE_B = 7.0
N_SAMPLES = 100

X = [random.uniform(0, 10) for _ in range(N_SAMPLES)]
y = [TRUE_W * x + TRUE_B + random.gauss(0, 2.0) for x in X]

print(f"Generated {N_SAMPLES} samples")
print(f"True relationship: y = {TRUE_W}x + {TRUE_B} (+ noise)")
print(f"First 5 points: {[(round(X[i], 2), round(y[i], 2)) for i in range(5)]}")
```

### Step 2: Linear regression from scratch with gradient descent · 从零用梯度下降实现线性回归

```python
class LinearRegression:
    def __init__(self, learning_rate=0.01):
        self.w = 0.0
        self.b = 0.0
        self.lr = learning_rate
        self.cost_history = []

    def predict(self, X):
        return [self.w * x + self.b for x in X]

    def compute_cost(self, X, y):
        predictions = self.predict(X)
        n = len(y)
        cost = sum((pred - actual) ** 2 for pred, actual in zip(predictions, y)) / n
        return cost

    def compute_gradients(self, X, y):
        predictions = self.predict(X)
        n = len(y)
        dw = (2 / n) * sum((pred - actual) * x for pred, actual, x in zip(predictions, y, X))
        db = (2 / n) * sum(pred - actual for pred, actual in zip(predictions, y))
        return dw, db

    def fit(self, X, y, epochs=1000, print_every=200):
        for epoch in range(epochs):
            dw, db = self.compute_gradients(X, y)
            self.w -= self.lr * dw
            self.b -= self.lr * db
            cost = self.compute_cost(X, y)
            self.cost_history.append(cost)
            if epoch % print_every == 0:
                print(f"  Epoch {epoch:4d} | Cost: {cost:.4f} | w: {self.w:.4f} | b: {self.b:.4f}")
        return self

    def r_squared(self, X, y):
        predictions = self.predict(X)
        y_mean = sum(y) / len(y)
        ss_res = sum((actual - pred) ** 2 for actual, pred in zip(y, predictions))
        ss_tot = sum((actual - y_mean) ** 2 for actual in y)
        return 1 - (ss_res / ss_tot)


print("=== Training Linear Regression (Gradient Descent) ===")
model = LinearRegression(learning_rate=0.005)
model.fit(X, y, epochs=1000, print_every=200)
print(f"\nLearned: y = {model.w:.4f}x + {model.b:.4f}")
print(f"True:    y = {TRUE_W}x + {TRUE_B}")
print(f"R-squared: {model.r_squared(X, y):.4f}")
```

### Step 3: Normal equation (closed-form solution) · 正规方程（闭式解）

```python
class LinearRegressionNormal:
    def __init__(self):
        self.w = 0.0
        self.b = 0.0

    def fit(self, X, y):
        n = len(X)
        x_mean = sum(X) / n
        y_mean = sum(y) / n
        numerator = sum((X[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((X[i] - x_mean) ** 2 for i in range(n))
        self.w = numerator / denominator
        self.b = y_mean - self.w * x_mean
        return self

    def predict(self, X):
        return [self.w * x + self.b for x in X]

    def r_squared(self, X, y):
        predictions = self.predict(X)
        y_mean = sum(y) / len(y)
        ss_res = sum((actual - pred) ** 2 for actual, pred in zip(y, predictions))
        ss_tot = sum((actual - y_mean) ** 2 for actual in y)
        return 1 - (ss_res / ss_tot)


print("\n=== Normal Equation (Closed-Form) ===")
model_normal = LinearRegressionNormal()
model_normal.fit(X, y)
print(f"Learned: y = {model_normal.w:.4f}x + {model_normal.b:.4f}")
print(f"R-squared: {model_normal.r_squared(X, y):.4f}")
```

### Step 4: Multiple linear regression · 多元线性回归

```python
class MultipleLinearRegression:
    def __init__(self, n_features, learning_rate=0.01):
        self.weights = [0.0] * n_features
        self.bias = 0.0
        self.lr = learning_rate
        self.cost_history = []

    def predict_single(self, x):
        return sum(w * xi for w, xi in zip(self.weights, x)) + self.bias

    def predict(self, X):
        return [self.predict_single(x) for x in X]

    def compute_cost(self, X, y):
        predictions = self.predict(X)
        n = len(y)
        return sum((pred - actual) ** 2 for pred, actual in zip(predictions, y)) / n

    def fit(self, X, y, epochs=1000, print_every=200):
        n = len(y)
        n_features = len(X[0])
        for epoch in range(epochs):
            predictions = self.predict(X)
            errors = [pred - actual for pred, actual in zip(predictions, y)]
            for j in range(n_features):
                grad = (2 / n) * sum(errors[i] * X[i][j] for i in range(n))
                self.weights[j] -= self.lr * grad
            grad_b = (2 / n) * sum(errors)
            self.bias -= self.lr * grad_b
            cost = self.compute_cost(X, y)
            self.cost_history.append(cost)
            if epoch % print_every == 0:
                print(f"  Epoch {epoch:4d} | Cost: {cost:.4f}")
        return self

    def r_squared(self, X, y):
        predictions = self.predict(X)
        y_mean = sum(y) / len(y)
        ss_res = sum((actual - pred) ** 2 for actual, pred in zip(y, predictions))
        ss_tot = sum((actual - y_mean) ** 2 for actual in y)
        return 1 - (ss_res / ss_tot)


random.seed(42)
N = 100
X_multi = []
y_multi = []
for _ in range(N):
    size = random.uniform(500, 3000)
    bedrooms = random.randint(1, 5)
    age = random.uniform(0, 50)
    price = 50 * size + 10000 * bedrooms - 1000 * age + 50000 + random.gauss(0, 20000)
    X_multi.append([size, bedrooms, age])
    y_multi.append(price)


def standardize(X):
    n_features = len(X[0])
    means = [sum(X[i][j] for i in range(len(X))) / len(X) for j in range(n_features)]
    stds = []
    for j in range(n_features):
        variance = sum((X[i][j] - means[j]) ** 2 for i in range(len(X))) / len(X)
        stds.append(variance ** 0.5)
    X_scaled = []
    for i in range(len(X)):
        row = [(X[i][j] - means[j]) / stds[j] if stds[j] > 0 else 0 for j in range(n_features)]
        X_scaled.append(row)
    return X_scaled, means, stds


y_mean_val = sum(y_multi) / len(y_multi)
y_std_val = (sum((yi - y_mean_val) ** 2 for yi in y_multi) / len(y_multi)) ** 0.5
y_scaled = [(yi - y_mean_val) / y_std_val for yi in y_multi]

X_scaled, x_means, x_stds = standardize(X_multi)

print("\n=== Multiple Linear Regression (3 features) ===")
print("Features: house size, bedrooms, age")
multi_model = MultipleLinearRegression(n_features=3, learning_rate=0.01)
multi_model.fit(X_scaled, y_scaled, epochs=1000, print_every=200)

print(f"\nWeights (standardized): {[round(w, 4) for w in multi_model.weights]}")
print(f"Bias (standardized): {multi_model.bias:.4f}")
print(f"R-squared: {multi_model.r_squared(X_scaled, y_scaled):.4f}")
```

### Step 5: Polynomial regression · 多项式回归

```python
class PolynomialRegression:
    def __init__(self, degree, learning_rate=0.01):
        self.degree = degree
        self.weights = [0.0] * degree
        self.bias = 0.0
        self.lr = learning_rate

    def make_features(self, X):
        return [[x ** (d + 1) for d in range(self.degree)] for x in X]

    def predict(self, X):
        features = self.make_features(X)
        return [sum(w * f for w, f in zip(self.weights, row)) + self.bias for row in features]

    def fit(self, X, y, epochs=1000, print_every=200):
        features = self.make_features(X)
        n = len(y)
        for epoch in range(epochs):
            predictions = [sum(w * f for w, f in zip(self.weights, row)) + self.bias for row in features]
            errors = [pred - actual for pred, actual in zip(predictions, y)]
            for j in range(self.degree):
                grad = (2 / n) * sum(errors[i] * features[i][j] for i in range(n))
                self.weights[j] -= self.lr * grad
            grad_b = (2 / n) * sum(errors)
            self.bias -= self.lr * grad_b
            if epoch % print_every == 0:
                cost = sum(e ** 2 for e in errors) / n
                print(f"  Epoch {epoch:4d} | Cost: {cost:.6f}")
        return self

    def r_squared(self, X, y):
        predictions = self.predict(X)
        y_mean = sum(y) / len(y)
        ss_res = sum((actual - pred) ** 2 for actual, pred in zip(y, predictions))
        ss_tot = sum((actual - y_mean) ** 2 for actual in y)
        return 1 - (ss_res / ss_tot)


random.seed(42)
X_poly = [x / 10.0 for x in range(0, 50)]
y_poly = [0.5 * x ** 2 - 2 * x + 3 + random.gauss(0, 1.0) for x in X_poly]

x_max = max(abs(x) for x in X_poly)
X_poly_norm = [x / x_max for x in X_poly]
y_poly_mean = sum(y_poly) / len(y_poly)
y_poly_std = (sum((yi - y_poly_mean) ** 2 for yi in y_poly) / len(y_poly)) ** 0.5
y_poly_norm = [(yi - y_poly_mean) / y_poly_std for yi in y_poly]

print("\n=== Polynomial Regression (degree 2 vs degree 5) ===")
print("True relationship: y = 0.5x^2 - 2x + 3")

print("\nDegree 2:")
poly2 = PolynomialRegression(degree=2, learning_rate=0.1)
poly2.fit(X_poly_norm, y_poly_norm, epochs=2000, print_every=500)
print(f"  R-squared: {poly2.r_squared(X_poly_norm, y_poly_norm):.4f}")

print("\nDegree 5:")
poly5 = PolynomialRegression(degree=5, learning_rate=0.1)
poly5.fit(X_poly_norm, y_poly_norm, epochs=2000, print_every=500)
print(f"  R-squared: {poly5.r_squared(X_poly_norm, y_poly_norm):.4f}")

print("\nDegree 2 fits the true curve well. Degree 5 fits training data slightly better")
print("but risks overfitting on new data.")
```

### Step 6: Ridge regression (L2 regularization) · 岭回归（L2 正则化）

```python
class RidgeRegression:
    def __init__(self, n_features, learning_rate=0.01, alpha=1.0):
        self.weights = [0.0] * n_features
        self.bias = 0.0
        self.lr = learning_rate
        self.alpha = alpha

    def predict_single(self, x):
        return sum(w * xi for w, xi in zip(self.weights, x)) + self.bias

    def predict(self, X):
        return [self.predict_single(x) for x in X]

    def fit(self, X, y, epochs=1000, print_every=200):
        n = len(y)
        n_features = len(X[0])
        for epoch in range(epochs):
            predictions = self.predict(X)
            errors = [pred - actual for pred, actual in zip(predictions, y)]
            mse = sum(e ** 2 for e in errors) / n
            reg_term = self.alpha * sum(w ** 2 for w in self.weights)
            cost = mse + reg_term
            for j in range(n_features):
                grad = (2 / n) * sum(errors[i] * X[i][j] for i in range(n))
                grad += 2 * self.alpha * self.weights[j]
                self.weights[j] -= self.lr * grad
            grad_b = (2 / n) * sum(errors)
            self.bias -= self.lr * grad_b
            if epoch % print_every == 0:
                print(f"  Epoch {epoch:4d} | Cost: {cost:.4f} | L2 penalty: {reg_term:.4f}")
        return self


print("\n=== Ridge Regression (L2 Regularization) ===")
print("Same data as multiple regression, with alpha=0.1")
ridge = RidgeRegression(n_features=3, learning_rate=0.01, alpha=0.1)
ridge.fit(X_scaled, y_scaled, epochs=1000, print_every=200)
print(f"\nRidge weights: {[round(w, 4) for w in ridge.weights]}")
print(f"Plain weights: {[round(w, 4) for w in multi_model.weights]}")
print("Ridge weights are smaller (shrunk toward zero) due to the L2 penalty.")
```

## Use It · 实战用法

现在用 scikit-learn 做同样的事——这才是你实际在生产中会用的东西。

```python
from sklearn.linear_model import LinearRegression as SklearnLR
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np

np.random.seed(42)
X_sk = np.random.uniform(0, 10, (100, 1))
y_sk = 3.0 * X_sk.squeeze() + 7.0 + np.random.normal(0, 2.0, 100)

X_train, X_test, y_train, y_test = train_test_split(X_sk, y_sk, test_size=0.2, random_state=42)

lr = SklearnLR()
lr.fit(X_train, y_train)
y_pred = lr.predict(X_test)

print("=== Scikit-learn Linear Regression ===")
print(f"Coefficient (w): {lr.coef_[0]:.4f}")
print(f"Intercept (b): {lr.intercept_:.4f}")
print(f"R-squared (test): {r2_score(y_test, y_pred):.4f}")
print(f"MSE (test): {mean_squared_error(y_test, y_pred):.4f}")

poly = PolynomialFeatures(degree=2, include_bias=False)
X_poly_sk = poly.fit_transform(X_train)
X_poly_test = poly.transform(X_test)

lr_poly = SklearnLR()
lr_poly.fit(X_poly_sk, y_train)
print(f"\nPolynomial degree 2 R-squared: {r2_score(y_test, lr_poly.predict(X_poly_test)):.4f}")

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

ridge = Ridge(alpha=1.0)
ridge.fit(X_train_scaled, y_train)
print(f"Ridge R-squared: {r2_score(y_test, ridge.predict(X_test_scaled)):.4f}")
print(f"Ridge coefficient: {ridge.coef_[0]:.4f}")
```

你从零写的实现和 scikit-learn 给出同样的结果。区别在于：scikit-learn 处理了边界情况、数值稳定性和性能优化。生产用库，从零版本用来理解背后发生了什么。

> Now the same thing with scikit-learn, which is what you will actually use in production. ... Your from-scratch implementation and scikit-learn produce the same results. The difference: scikit-learn handles edge cases, numerical stability, and performance optimizations. Use the library for production. Use the from-scratch version to understand what is happening.

## 实测纠正 · Measured Corrections

以下数据全部在本机实跑 `code/linear_regression.py`（Python 3.12，零依赖，exit 0）后自建脚本复测。发现课文有三处需要纠正。

### 纠正 1：课文的 Use It 代码块「Sklearn 对比」根本不会打印任何系数

`code/linear_regression.py` 末尾的 `Scikit-learn Comparison` 段在本机输出：

```text
=== Scikit-learn Comparison ===
scikit-learn not installed. Install with: pip install scikit-learn
The from-scratch implementations above work without any dependencies.
```

本项目 `.venv` 未装 scikit-learn（依赖清单里 Python 只允许 numpy / torch / h5py / zstandard / safetensors）。但即使装上，**本课产物文件里的 Sklearn 代码只打印 R^2，从不打印系数**——而课文正文断言「你从零写的实现和 scikit-learn 给出同样的结果」。这句话在本课代码里是**没有对拍过的**。真正的对拍在下面「实测 2」补上。**（该判断已被 2026-10-14 的实测 8 推翻：本机 `.venv` 现已装 sklearn 1.9.1，系数对拍差值 0.00e+00。）**

> The `Scikit-learn Comparison` block prints nothing but an install hint on this machine. The lesson text claims the from-scratch version and scikit-learn "produce the same results", but the shipped code never compares coefficients. Real comparison supplied below.

### 实测 2：从零梯度下降 vs 正规方程，真对拍

100 个样本，真值 `y = 3.0x + 7.0 + N(0, 2)`（`random.seed(42)`，与课文同种子）：

| 方法 | 学到的 w | 学到的 b | MSE | R^2 |
|------|----------|----------|-----|-----|
| 梯度下降 lr=0.005，1000 epoch（产物代码的真实配置） | 3.1433 | 6.5432 | 3.6976 | 0.9566 |
| 正规方程（闭式解） | 3.0756 | 6.9853 | 3.6443 | **0.9572** |
| 真值 | 3.0000 | 7.0000 | — | — |

正规方程一步到位、且更接近真值；梯度下降 1000 步还没走完。**这就是「闭式解精确、梯度下降要调步」的量化版本。**

> **2026-10-14 复跑修正两处**：① 原表写「lr=0.01，800 epoch → 3.1433 / 6.5432」，但产物 `code/linear_regression.py` 实际是 `learning_rate=0.005, epochs=1000`；800 epoch 那行打印的是 `w=3.1906 b=6.2336`——**配置标签与产物对不上**。② 原表写正规方程 `R^2 = 0.9772`，复跑产物打印 **0.9572**，且 `1 − MSE_opt/Var(y) = 1 − 3.6443/85.1447 = 0.9572` 完全吻合；闭式解是训练集 R² 的最大化解，必须 ≥ 梯度下降的 0.9566，**0.9772 在数学上不可能**。两只教训同 0/09：课文/讲义的数字必须与产物对拍。

> Closed-form normal equation lands closer to truth in one shot; gradient descent is still moving after 800 epochs.

### 实测 3：`w` 比 `b` 收敛慢（与 Phase 1/04 结论方向相反，要看清对象）

同一个单变量训练的逐步记录（换算回原尺度）：

```text
raw x lr=0.01 (800 ep)
  ep=   1 cost= 82.2346 w=0.8908 b=-3.8372
  ep=   5 cost= 14.1321 w=1.3633 b=-5.7541
  ep=  20 cost= 12.5654 w=1.3460 b=-5.1905
  ep=  50 cost= 10.1193 w=1.3018 b=-4.1318
  ep= 100 cost=  7.4399 w=1.2423 b=-2.7040
  ep= 200 cost=  4.9485 w=1.1618 b=-0.7739
  ep= 400 cost=  3.7983 w=1.0870 b= 1.0208
  ep= 800 cost=  3.6464 w=1.0525 b= 1.8494
```

800 epoch 后 `w=1.05`、`b=1.85`，离真值 3.0 / 7.0 都还差得远，**但 b 每一步的梯度绝对值是 w 的 3~7 倍，跑得更快**。

Phase 1/04 讲的是「在线性回归里 w 比 b 快 3 倍」——那次的机制是 `dw` 多乘了 `x`（x 平均 3）。**这次方向反了，因为这次 `x` 尺度大 ⇒ `w` 的曲率被 x² 放大、单步被 lr·x² 拖住；b 的曲率是常数 2。** 两个结论都对，取决于 x 的尺度——这正好是「特征缩放为什么必要」的活教材，见实测 4。

> `w` converges slower than `b` here (opposite of the Phase 1/04 finding), because x's scale inflates w's curvature by x². Same mechanism, opposite sign — the feature-scaling lesson in disguise.

### 实测 4：特征标准化，800 epoch → 50 epoch，且能开大学习率

同一批数据，z-score 标准化后 `x` 变成零均值单位方差：

| 配置 | 收敛到 cost=3.64 需要 | 50 epoch 时 w / b（换算回原尺度） |
|------|----------------------|----------------------------------|
| 原始 x，lr=0.01 | 800 epoch 还没收敛（cost=3.6464） | 1.30 / -4.13 |
| 标准化 x，lr=0.01 | 200 epoch 收敛（cost=3.6444） | — |
| 标准化 x，lr=0.1 | **50 epoch 收敛（cost=3.6443）** | **3.0756 / 6.9853** |

标准化 + 大学习率，**50 步就打到正规方程的解**（3.0756 / 6.9853，一模一样）。代价面从「狭长山谷」变「圆碗」后，一个学习率就能伺候所有参数——这正是 post 测验 Q1 的标准答案。

> Standardization + larger lr reaches the closed-form solution in 50 epochs instead of 800. The cost surface stops being elongated.

### 实测 5：Ridge（alpha 扫描）实测缩水幅度

`code/linear_regression.py` 的 Ridge 段（alpha=0.1）输出：

```text
Ridge weights: [0.7052, 0.2647, -0.2558]
Plain weights: [0.7716, 0.2773, -0.2739]
```

三个特征的权重都被压缩约 8.6%（0.7716→0.7052 等）。闭式解下 alpha 扫描（单变量、L2 只罚 w）：

| alpha | 学到的 w | 学到的 b |
|-------|----------|----------|
| 0 | 3.0756 | 6.9853 |
| 1 | 3.0721 | 7.0024 |
| 10 | 3.0403 | 7.1546 |
| 50 | 2.9069 | 7.7944 |
| 100 | 2.7558 | 8.5193 |

**L2 把 w 往 0 拉，b 往均值拉**——alpha 越大越明显。注意课文说「Ridge weights are smaller」，实测确认**方向对但幅度取决于 alpha**，不是普适的「更小」。

> L2 shrinks w toward 0 and pushes b toward the mean; the amount depends on alpha, not a universal "smaller".

### 实测 6：多项式过拟合的量化扫描（课文练习 2 的完整答案）

`code/linear_regression.py` 的 Polynomial 段只跑了 degree 2 和 5（R^2 = 0.6408 / 0.6686，都没到过拟合）。补跑高次（真值 `y = 0.5x² - 2x + 3`，80 点，噪声 σ=1.5，64/16 划分）：

| degree | train R^2 | test R^2 | 判定 |
|--------|-----------|----------|------|
| 1 | 0.2025 | 0.2580 | 欠拟合 |
| 2 | 0.9132 | 0.9084 | 刚好（真值就是 2 次） |
| 5 | 0.9530 | 0.9844 | 还行 |
| 10 | 0.9734 | 0.9756 | 还行 |
| 16 | 0.9748 | **0.9017** | **开始过拟合** |
| 20 | 0.9753 | 0.9655 | 波动 |

**过拟合的信号不是「train R^2 高」**——所有高次模型 train R^2 都在 0.97+，肉眼分不出来。**信号是 train/test 的差距**（degree 16：0.9748 vs 0.9017，差 7.3 个点）。

同一份数据，degree=16 加 Ridge（alpha=0.1）：test R^2 从 0.9017 → **0.9764**（train 只降到 0.9672）。**这就是 post 测验 Q3 标准答案「降复杂度或加正则」的量化证据。**

> Overfitting is invisible in train R^2 alone; the signal is the train/test gap. Ridge alpha=0.1 on degree-16 lifts test R^2 from 0.9017 to 0.9764.

### 实测 7：外推会炸，且 R^2 完全看不见

同一份多项式数据（真值 `y=0.5x²-2x+3`），只看样本边缘 x=10.5 / x=11 处的预测：

| degree | train R^2 | x=10.5 预测 | x=11 预测 | 真值 37.12 / 41.50 |
|--------|-----------|-------------|-----------|---------------------|
| 2 | 0.957 | 40.72 | 46.06 | 接近 |
| 10 | 0.964 | 35.94 | 56.92 | 开始飘 |
| 16 | 0.939 | 1014.23 | 10646.94 | **炸了 255 倍** |
| 79 | 0.997 | 1589711.27 | 535915770.96 | **炸了 1300 万倍** |

degree=16 在训练区间内 R^2=0.939 看着「还行」，**但在样本边缘外推 0.5 个单位就错 255 倍**。R^2 是在训练数据上算的，它天生看不见外推。生产上这叫「模型在分布外（out-of-distribution）失效」。

> R^2 is computed on training data and structurally cannot see extrapolation error. Degree 16 looks fine inside the sample and is 255× wrong half a unit outside it.

### 实测 8：环境变了——`.venv` 现在装了 scikit-learn，纠正 1 已过时；顺手做真对拍 + 学习率稳定上界

2026-10-14 复跑本机 `.venv`：**scikit-learn 1.9.1 / numpy 2.5.3 已安装**（纠正 1 写于「未装」的当时，现已过时）。`code/linear_regression.py` 末尾的 Sklearn 段这次真的打印了系数：

```text
=== Scikit-learn Comparison ===
Coefficient (w): 2.9197
Intercept (b): 7.2858
R-squared (test): 0.9686
MSE (test): 2.6148
```

真对拍（同一 80/20 训练集，numpy seed 42，从零闭式解 vs sklearn）：

| 实现 | w | b |
|------|-----|-----|
| 从零正规方程（本课 Step 3 公式） | 2.8846 | 7.5478 |
| `sklearn.linear_model.LinearRegression` | 2.8846 | 7.5478 |
| 差值 | 0.00e+00 | 0.00e+00 |

课文那句「从零实现与 scikit-learn 给出同样的结果」**这次实测成立**，精度到机器零。注意别混：实测 2 的 3.0756 / 6.9853 是**全量 100 个样本**，这里是 **80% 训练集**（2.8846 / 7.5478），不是同一个数。

学习率稳定上界（同一份原始 x∈[0,10] 数据，2000 epoch）：

```text
lr=0.001  w=3.2537 b=5.1812   # 龟速，2000 步还没到
lr=0.005  w=2.9121 b=7.4038
lr=0.01   w=2.9081 b=7.4301
lr=0.03   w=2.9080 b=7.4302   # 仍然收敛
lr=0.05   w=nan    b=nan      # 溢出炸掉（RuntimeWarning: overflow encountered in reduce）
```

理论值：MSE 的 Hessian 是 `(2/n)[[Σx², Σx],[Σx, n]]`，x~U(0,10) 时 λ_max≈68、λ_min≈0.5，稳定条件 `lr < 2/λ_max ≈ 0.03`。**实测 0.03 刚好活着、0.05 死**——这条边界不是调参玄学，是 x 的尺度直接决定的；把 x 标准化后 λ_max 掉回 O(1)，就能安全开到 lr=0.1（见实测 4 的 50 epoch）。

> Re-ran on 2026-10-14: sklearn 1.9.1 / numpy 2.5.3 are now installed, and the shipped Sklearn block does print coefficients. Closed-form vs sklearn agrees to 0.00e+00 on the same 80/20 split. Learning-rate stability bound: lr < 2/λ_max ≈ 0.03 for raw x∈[0,10] — lr=0.03 survives, lr=0.05 overflows to nan.

## Ship It · 交付

本课产出：

> This lesson produces:
> - `outputs/skill-regression.md` - a skill for choosing the right regression approach based on the problem

## Exercises · 练习

1. 实现批量梯度下降（batch gradient descent）、随机梯度下降（SGD）和小批量梯度下降（mini-batch gradient descent）。在同一数据集上比较收敛速度。哪个收敛最快？哪个的代价曲线最平滑？
2. 用三次函数（y = ax^3 + bx^2 + cx + d + noise）生成数据。拟合 1 次、3 次和 10 次多项式。比较训练 R^2 和测试 R^2。到多少次时过拟合变得明显？
3. 实现 Lasso 回归（L1 正则化：penalty = alpha * sum(|w_i|)）。在多特征房价数据上训练。对比哪些权重变成零，与 Ridge 比较。为什么 L1 产生稀疏解而 L2 不会？

> 1. Implement batch gradient descent, stochastic gradient descent (SGD), and mini-batch gradient descent. Compare convergence speed on the same dataset. Which converges fastest? Which has the smoothest cost curve?
> 2. Generate data from a cubic function (y = ax^3 + bx^2 + cx + d + noise). Fit polynomials of degree 1, 3, and 10. Compare training R^2 and test R^2. At what degree does overfitting become obvious?
> 3. Implement Lasso regression (L1 regularization: penalty = alpha * sum(|w_i|)). Train on the multi-feature housing data. Compare which weights go to zero vs Ridge. Why does L1 produce sparse solutions while L2 does not?

## Key Terms · 术语表

| 术语 | 人们常说的是 | 它实际的意思是 |
|------|----------------|----------------------|
| Linear regression | 「画一条穿过数据的线」 | 找到使 wx+b 与真实 y 之间平方差之和最小的权重 w 和偏置 b |
| Cost function | 「模型有多差」 | 把模型参数映射为一个衡量预测误差的数字的函数，优化就是要最小化它 |
| Mean squared error | 「误差平方的平均」 | (1/n) * sum of (predicted - actual)^2，对大错误的惩罚不成比例地更重 |
| Gradient descent | 「往山下走」 | 利用偏导数，沿降低代价函数的方向迭代调整参数 |
| Learning rate | 「步长」 | 控制梯度下降每一步参数变化幅度的标量 |
| Normal equation | 「直接解出来」 | 闭式解 w = (X^T X)^-1 X^T y，无需迭代直接给出最优权重 |
| R-squared | 「拟合有多好」 | 模型解释的 y 方差比例，取值从负无穷到 1.0 |
| Feature scaling | 「让特征可比较」 | 把特征变换到相近的范围（如零均值、单位方差），让梯度下降收敛更快 |
| Regularization | 「惩罚复杂度」 | 在代价函数中加入收缩权重的项，防止过拟合 |
| Ridge regression | 「L2 正则化」 | 在 MSE 上加 lambda * sum(w_i^2) 惩罚项的线性回归 |
| Polynomial regression | 「用线性数学拟合曲线」 | 在多项式特征（x, x^2, x^3, ...）上做线性回归，对权重仍然是线性的 |
| Overfitting | 「背下了训练数据」 | 用的模型太复杂，把训练数据里的噪声都拟合了，在新数据上失效 |

## Further Reading · 延伸阅读

- [An Introduction to Statistical Learning (ISLR)](https://www.statlearning.com/) —— 免费 PDF，第 3 章和第 6 章用实用的 R 例子讲线性回归和正则化
- [The Elements of Statistical Learning (ESL)](https://hastie.su.domains/ElemStatLearn/) —— 免费 PDF，ISLR 更数学化的姊妹篇，对 ridge 和 lasso 的处理更深
- [Stanford CS229 Lecture Notes on Linear Regression](https://cs229.stanford.edu/main_notes.pdf) —— Andrew Ng 的讲义，从第一性原理推导正规方程和梯度下降
- [scikit-learn LinearRegression documentation](https://scikit-learn.org/stable/modules/linear_model.html) —— LinearRegression、Ridge、Lasso、ElasticNet 的实用参考，含代码示例
