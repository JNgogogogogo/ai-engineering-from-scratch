# 向量、矩阵与运算（Vectors, Matrices & Operations）

> 中文讲义（双语对照）。正文为中文，每段下方 `>` 引用块保留英文原文；代码块、命令、术语名不译。

> Every neural network is just matrix multiplication with extra steps.

**类型 (Type):** Build
**语言 (Languages):** Python, Julia
**前置课程 (Prerequisites):** Phase 1, Lesson 01 (Linear Algebra Intuition)
**时间 (Time):** ~60 分钟

## 学习目标（Learning Objectives）

- 构建一个 Matrix 类，支持逐元素运算、矩阵乘法、转置、行列式、逆
- 区分逐元素乘法与矩阵乘法，并说清各自适用的场景
- 只用这个从零写的 Matrix 类，实现一个稠密神经网络层（`relu(W @ x + b)`）
- 解释广播（broadcasting）规则，以及神经网络框架里 bias 相加是怎么工作的

> - Build a Matrix class with element-wise operations, matrix multiplication, transpose, determinant, and inverse
> - Distinguish element-wise multiplication from matrix multiplication and explain when each applies
> - Implement a single dense neural network layer (`relu(W @ x + b)`) using only the from-scratch Matrix class
> - Explain broadcasting rules and how bias addition works in neural network frameworks

## 问题（The Problem）

你想造一个神经网络。你读代码，看到这一行：

```
output = activation(weights @ input + bias)
```

那个 `@` 是矩阵乘法。`weights` 是矩阵，`input` 是向量。不懂这些运算，这行就是魔法；懂了，它就是**一层的前向传播，三个运算**。

模型处理的每张图都是一个像素值矩阵；每个词向量都是一个向量；每一层神经网络都是一个矩阵变换。**不懂矩阵运算就没法造 AI 系统，正如不懂变量就没法写代码。**

本课从零开始把这个"流利度"建起来。

> You want to build a neural network. You read the code and see this:
>
> ```
> output = activation(weights @ input + bias)
> ```
>
> That `@` is matrix multiplication. The `weights` are a matrix. The `input` is a vector. If you do not know what those operations do, this line is magic. If you do know, it is the entire forward pass of a layer in three operations.
>
> Every image your model processes is a matrix of pixel values. Every word embedding is a vector. Every layer of every neural network is a matrix transformation. You cannot build AI systems without being fluent in matrix operations the same way you cannot write code without understanding variables.
>
> This lesson builds that fluency from scratch.

## 核心概念（The Concept）

### 向量：有序的数字列表

向量是一个带方向与模长的数字列表。在 AI 里，向量表示数据点、特征或参数。

```
v = [3, 4]        -- a 2D vector
w = [1, 0, -2]    -- a 3D vector
```

2D 向量 `[3, 4]` 指向平面上的坐标 (3, 4)，其长度（模长）是 5（3-4-5 直角三角形）。

> A vector is a list of numbers with a direction and magnitude. In AI, vectors represent data points, features, or parameters.
>
> ```
> v = [3, 4]        -- a 2D vector
> w = [1, 0, -2]    -- a 3D vector
> ```
>
> A 2D vector `[3, 4]` points to coordinates (3, 4) on a plane. Its length (magnitude) is 5 (the 3-4-5 triangle).

### 矩阵：数字的网格

矩阵是一个二维网格，有行有列。m x n 矩阵有 m 行 n 列。

```
A = | 1  2  3 |     -- 2x3 matrix (2 rows, 3 columns)
    | 4  5  6 |
```

在神经网络里，权重矩阵把输入向量变换成输出向量。一个 784 输入、128 输出的层用 128x784 的权重矩阵。

> A matrix is a 2D grid. Rows and columns. An m x n matrix has m rows and n columns.
>
> ```
> A = | 1  2  3 |     -- 2x3 matrix (2 rows, 3 columns)
>     | 4  5  6 |
> ```
>
> In neural networks, weight matrices transform input vectors into output vectors. A layer with 784 inputs and 128 outputs uses a 128x784 weight matrix.

### 为什么形状（shape）重要

矩阵乘法有一条铁律：`(m x n) @ (n x p) = (m x p)`，**内侧维度必须相等**。

```
(128 x 784) @ (784 x 1) = (128 x 1)
  weights       input       output

Inner dimensions: 784 = 784  -- valid
```

在 PyTorch 里遇到 shape mismatch 报错，根因就是这里。

> Matrix multiplication has a strict rule: `(m x n) @ (n x p) = (m x p)`. The inner dimensions must match.
>
> ```
> (128 x 784) @ (784 x 1) = (128 x 1)
>   weights       input       output
>
> Inner dimensions: 784 = 784  -- valid
> ```
>
> If you get a shape mismatch error in PyTorch, this is why.

### 运算地图（The operations map）

| 运算 | 做什么 | 神经网络里的用途 |
|-----------|-------------|-------------------|
| 加法 Addition | 逐元素合并 | 给输出加 bias |
| 标量乘 Scalar multiply | 每个元素缩放 | 学习率 × 梯度 |
| 矩阵乘 Matrix multiply | 变换向量 | 层的前向传播 |
| 转置 Transpose | 行列互换 | 反向传播 |
| 行列式 Determinant | 用单个数概括矩阵 | 判断是否可逆 |
| 逆 Inverse | 撤销一个变换 | 解线性方程组 |
| 单位阵 Identity | 什么都不做的矩阵 | 初始化、残差连接 |

> | Operation | What it does | Neural network use |
> |-----------|-------------|-------------------|
> | Addition | Element-wise combine | Adding bias to output |
> | Scalar multiply | Scale every element | Learning rate * gradients |
> | Matrix multiply | Transform vectors | Layer forward pass |
> | Transpose | Flip rows and columns | Backpropagation |
> | Determinant | Single number summary | Checking invertibility |
> | Inverse | Undo a transformation | Solving linear systems |
> | Identity | Do-nothing matrix | Initialization, residual connections |

### 逐元素乘 vs 矩阵乘（初学者最容易混的地方）

逐元素乘（element-wise）：把**对应位置**相乘，两个矩阵形状必须相同。

```
| 1  2 |   | 5  6 |   | 5  12 |
| 3  4 | * | 7  8 | = | 21 32 |
```

矩阵乘（matrix multiplication）：**行与列做点积**，内侧维度必须相等。

```
| 1  2 |   | 5  6 |   | 1*5+2*7  1*6+2*8 |   | 19  22 |
| 3  4 | @ | 7  8 | = | 3*5+4*7  3*6+4*8 | = | 43  50 |
```

不同的运算、不同的结果、不同的规则。

> This distinction trips up beginners constantly.
>
> Element-wise: multiply matching positions. Both matrices must be the same shape.
>
> ```
> | 1  2 |   | 5  6 |   | 5  12 |
> | 3  4 | * | 7  8 | = | 21 32 |
> ```
>
> Matrix multiplication: dot products of rows and columns. Inner dimensions must match.
>
> ```
> | 1  2 |   | 5  6 |   | 1*5+2*7  1*6+2*8 |   | 19  22 |
> | 3  4 | @ | 7  8 | = | 3*5+4*7  3*6+4*8 | = | 43  50 |
> ```
>
> Different operations, different results, different rules.

### 广播（Broadcasting）

当你要给一个输出矩阵加一个 bias 向量时，形状对不上。广播会把小的那个数组"拉伸"到合适大小。

```
| 1  2  3 |   +   [10, 20, 30]
| 4  5  6 |

Broadcasting stretches the vector across rows:

| 1  2  3 |   | 10  20  30 |   | 11  22  33 |
| 4  5  6 | + | 10  20  30 | = | 14  25  36 |
```

每个现代框架都自动做这件事。理解它能让你在"形状看起来不对但代码能跑"时不困惑。

> When you add a bias vector to a matrix of outputs, the shapes do not match. Broadcasting stretches the smaller array to fit.
>
> ```
> | 1  2  3 |   +   [10, 20, 30]
> | 4  5  6 |
>
> Broadcasting stretches the vector across rows:
>
> | 1  2  3 |   | 10  20  30 |   | 11  22  33 |
> | 4  5  6 | + | 10  20  30 | = | 14  25  36 |
> ```
>
> Every modern framework does this automatically. Understanding it prevents confusion when shapes seem wrong but the code runs.

```figure
vector-projection
```

## 动手构建（Build It）

### Step 1：Vector 类

```python
class Vector:
    def __init__(self, data):
        self.data = list(data)
        self.size = len(self.data)

    def __repr__(self):
        return f"Vector({self.data})"

    def __add__(self, other):
        return Vector([a + b for a, b in zip(self.data, other.data)])

    def __sub__(self, other):
        return Vector([a - b for a, b in zip(self.data, other.data)])

    def __mul__(self, scalar):
        return Vector([x * scalar for x in self.data])

    def dot(self, other):
        return sum(a * b for a, b in zip(self.data, other.data))

    def magnitude(self):
        return sum(x ** 2 for x in self.data) ** 0.5
```

### Step 2：带核心运算的 Matrix 类

```python
class Matrix:
    def __init__(self, data):
        self.data = [list(row) for row in data]
        self.rows = len(self.data)
        self.cols = len(self.data[0])
        self.shape = (self.rows, self.cols)

    def __repr__(self):
        rows_str = "\n  ".join(str(row) for row in self.data)
        return f"Matrix({self.shape}):\n  {rows_str}"

    def __add__(self, other):
        return Matrix([
            [self.data[i][j] + other.data[i][j] for j in range(self.cols)]
            for i in range(self.rows)
        ])

    def __sub__(self, other):
        return Matrix([
            [self.data[i][j] - other.data[i][j] for j in range(self.cols)]
            for i in range(self.rows)
        ])

    def scalar_multiply(self, scalar):
        return Matrix([
            [self.data[i][j] * scalar for j in range(self.cols)]
            for i in range(self.rows)
        ])

    def element_wise_multiply(self, other):
        return Matrix([
            [self.data[i][j] * other.data[i][j] for j in range(self.cols)]
            for i in range(self.rows)
        ])

    def matmul(self, other):
        return Matrix([
            [
                sum(self.data[i][k] * other.data[k][j] for k in range(self.cols))
                for j in range(other.cols)
            ]
            for i in range(self.rows)
        ])

    def transpose(self):
        return Matrix([
            [self.data[j][i] for j in range(self.rows)]
            for i in range(self.cols)
        ])

    def determinant(self):
        if self.shape == (1, 1):
            return self.data[0][0]
        if self.shape == (2, 2):
            return self.data[0][0] * self.data[1][1] - self.data[0][1] * self.data[1][0]
        det = 0
        for j in range(self.cols):
            minor = Matrix([
                [self.data[i][k] for k in range(self.cols) if k != j]
                for i in range(1, self.rows)
            ])
            det += ((-1) ** j) * self.data[0][j] * minor.determinant()
        return det

    def inverse_2x2(self):
        det = self.determinant()
        if det == 0:
            raise ValueError("Matrix is singular, no inverse exists")
        return Matrix([
            [self.data[1][1] / det, -self.data[0][1] / det],
            [-self.data[1][0] / det, self.data[0][0] / det]
        ])

    @staticmethod
    def identity(n):
        return Matrix([
            [1 if i == j else 0 for j in range(n)]
            for i in range(n)
        ])
```

### Step 3：看它跑起来

```python
A = Matrix([[1, 2], [3, 4]])
B = Matrix([[5, 6], [7, 8]])

print("A + B =", (A + B).data)
print("A @ B =", A.matmul(B).data)
print("A^T =", A.transpose().data)
print("det(A) =", A.determinant())
print("A^-1 =", A.inverse_2x2().data)

I = Matrix.identity(2)
print("A @ A^-1 =", A.matmul(A.inverse_2x2()).data)
```

### Step 4：连到神经网络

```python
import random

inputs = Matrix([[0.5], [0.8], [0.2]])
weights = Matrix([
    [random.uniform(-1, 1) for _ in range(3)]
    for _ in range(2)
])
bias = Matrix([[0.1], [0.1]])

def relu_matrix(m):
    return Matrix([[max(0, val) for val in row] for row in m.data])

pre_activation = weights.matmul(inputs) + bias
output = relu_matrix(pre_activation)

print(f"Input shape: {inputs.shape}")
print(f"Weight shape: {weights.shape}")
print(f"Output shape: {output.shape}")
print(f"Output: {output.data}")
```

**这就是一个稠密层**：`output = relu(W @ x + b)`。每一个神经网络里的每一个稠密层，做的都恰好是这个。

> This is a single dense layer: `output = relu(W @ x + b)`. Every dense layer in every neural network does exactly this.

## 学以致用（Use It）

NumPy 用更少的行数、快几个数量级地完成上面所有事。

```python
import numpy as np

A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])

print("A + B =\n", A + B)
print("A * B (element-wise) =\n", A * B)
print("A @ B (matrix multiply) =\n", A @ B)
print("A^T =\n", A.T)
print("det(A) =", np.linalg.det(A))
print("A^-1 =\n", np.linalg.inv(A))
print("I =\n", np.eye(2))

inputs = np.random.randn(3, 1)
weights = np.random.randn(2, 3)
bias = np.array([[0.1], [0.1]])
output = np.maximum(0, weights @ inputs + bias)

print(f"\nNeural network layer: {weights.shape} @ {inputs.shape} = {output.shape}")
print(f"Output:\n{output}")
```

Python 里的 `@` 运算符调用 `__matmul__`。NumPy 用 C/Fortran 写的优化 BLAS 例程实现它——**同样的数学，快 100 倍**。

NumPy 里的广播：

```python
matrix = np.array([[1, 2, 3], [4, 5, 6]])
bias = np.array([10, 20, 30])
print(matrix + bias)
```

NumPy 自动把 1D 的 bias 广播到两行上。每个神经网络框架里的 bias 相加都是这么做的。

> NumPy does everything above in fewer lines and orders of magnitude faster.
>
> [... code ...]
>
> The `@` operator in Python calls `__matmul__`. NumPy implements it with optimized BLAS routines written in C and Fortran. Same math, 100x faster.
>
> Broadcasting in NumPy: [... code ...]
>
> NumPy automatically broadcasts the 1D bias across both rows. This is how bias addition works in every neural network framework.

## 交付物（Ship It）

本课产出一个"用几何直觉教矩阵运算"的提示词，见 `outputs/prompt-matrix-operations.md`。

这里构建的 Matrix 类是 Phase 3、Lesson 10 里迷你神经网络框架的基础。

> This lesson produces a prompt for teaching matrix operations through geometric intuition. See `outputs/prompt-matrix-operations.md`.
>
> The Matrix class built here is the foundation for the mini neural network framework we build in Phase 3, Lesson 10.

## 练习（Exercises）

1. **验证逆矩阵。** 计算 `A @ A.inverse_2x2()` 并确认得到单位阵。换三个不同的 2x2 矩阵试。行列式为 0 时会发生什么？
2. **实现 3x3 逆。** 用伴随矩阵（adjugate）法把 Matrix 类扩展到 3x3 求逆，和 NumPy 的 `np.linalg.inv` 对比。
3. **搭一个两层网络。** 只用你的 Matrix 类（不用 NumPy）搭 input(3) → hidden(4) → output(2) 的两层网络。随机初始化权重，跑一次前向传播，验证所有形状正确。

> 1. **Verify the inverse.** Multiply `A @ A.inverse_2x2()` and confirm you get the identity matrix. Try it with three different 2x2 matrices. What happens when the determinant is zero?
>
> 2. **Implement 3x3 inverse.** Extend the Matrix class to compute inverses for 3x3 matrices using the adjugate method. Test it against NumPy's `np.linalg.inv`.
>
> 3. **Build a two-layer network.** Using only your Matrix class (no NumPy), create a two-layer neural network: input (3) -> hidden (4) -> output (2). Initialize random weights, run a forward pass, and verify all shapes are correct.

## 关键术语（Key Terms）

| 术语 | 人们的说法 | 它实际是什么 |
|------|----------------|----------------------|
| Vector | "一支箭头" | 有序数字列表。在 AI 里：高维空间中的一个点。 |
| Matrix | "一张数字表" | 一个线性变换，把向量从一个空间映射到另一个空间。 |
| Matrix multiply | "把数字乘一乘" | 第一个矩阵的每一行与第二个矩阵的每一列做点积。**顺序很重要（A@B ≠ B@A）。** |
| Transpose | "翻一下" | 行列互换，把 m x n 变成 n x m。反向传播里的关键操作。 |
| Determinant | "从矩阵算出的某个数" | 度量矩阵把面积（2D）或体积（3D）缩放了多少。为 0 意味着变换把某一维压扁了。 |
| Inverse | "撤销矩阵" | 逆转该变换的矩阵，仅在行列式不为 0 时存在。 |
| Identity matrix | "无聊的矩阵" | 矩阵版的"乘 1"。用于残差连接（ResNets）。 |
| Broadcasting | "神奇的形状修复" | 沿缺失维度重复，把小数组拉伸到大数组的形状。 |
| Element-wise | "普通乘法" | 对应位置相乘，两个数组形状必须相同（或可广播）。 |

> | Term | What people say | What it actually means |
> |------|----------------|----------------------|
> | Vector | "An arrow" | An ordered list of numbers. In AI: a point in high-dimensional space. |
> | Matrix | "A table of numbers" | A linear transformation. It maps vectors from one space to another. |
> | Matrix multiply | "Just multiply the numbers" | Dot products between every row of the first matrix and every column of the second. Order matters. |
> | Transpose | "Flip it" | Swap rows and columns. Turns an m x n matrix into n x m. Critical in backpropagation. |
> | Determinant | "Some number from the matrix" | Measures how much the matrix scales area (2D) or volume (3D). Zero means the transformation crushes a dimension. |
> | Inverse | "Undo the matrix" | The matrix that reverses the transformation. Only exists when the determinant is not zero. |
> | Identity matrix | "The boring matrix" | The matrix equivalent of multiplying by 1. Used in residual connections (ResNets). |
> | Broadcasting | "Magic shape fixing" | Stretching a smaller array to match a larger one by repeating along missing dimensions. |
> | Element-wise | "Regular multiplication" | Multiply matching positions. Both arrays must have the same shape (or be broadcastable). |

## 延伸阅读（Further Reading）

- [3Blue1Brown: Essence of Linear Algebra](https://www.3blue1brown.com/topics/linear-algebra) - 本课每个运算的可视化直觉
- [NumPy 广播文档](https://numpy.org/doc/stable/user/basics.broadcasting.html) - NumPy 遵循的确切规则
- [Stanford CS229 Linear Algebra Review](http://cs229.stanford.edu/section/cs229-linalg.pdf) - 面向 ML 的线性代数简明参考

> - [3Blue1Brown: Essence of Linear Algebra](https://www.3blue1brown.com/topics/linear-algebra) - visual intuition for every operation covered here
> - [NumPy documentation on broadcasting](https://numpy.org/doc/stable/user/basics.broadcasting.html) - the exact rules NumPy follows
> - [Stanford CS229 Linear Algebra Review](http://cs229.stanford.edu/section/cs229-linalg.pdf) - concise reference for ML-specific linear algebra

## 实测数据与纠正（Measured Corrections）

以下为实机运行 `code/matrices.py` 的真实输出（macOS，Python 3.9.6），以及逐项核对结果：

```
=== 向量 ===
v = [3, 4],  w = [1, 2]
v + w = [4, 6] ; v - w = [2, 2] ; v * 2 = [6, 8]
v · w = 11        # 3*1 + 4*2 = 11
|v| = 5.0         # √(3²+4²) = 5（3-4-5 直角三角形，与课文一致）

=== 基本矩阵运算（A=[[1,2],[3,4]], B=[[5,6],[7,8]]）===
A + B  = [[6,8],[10,12]]
A * 3  = [[3,6],[9,12]]
A * B (逐元素) = [[5,12],[21,32]]     # 与课文示例逐位一致 ✓
A @ B (矩阵乘) = [[19,22],[43,50]]    # 与课文示例逐位一致 ✓
A^T = [[1,3],[2,4]]

=== 行列式与逆（A=[[4,7],[2,6]]）===
det(A) = 10                            # 4*6 − 7*2 = 24 − 14 = 10 ✓
A^-1 = [[0.6, -0.7], [-0.2, 0.4]]
A @ A^-1 = [[1.0000, 0.0000], [-0.0000, 1.0000]]   # 注意那个 -0.0000

=== 广播 ===
Output   = [[1,2,3],[4,5,6]] ; Bias = [[10,20,30]]
Out+Bias = [[11,22,33],[14,25,36]]     # 与课文示例逐位一致 ✓

=== 神经网络前向传播 ===
Input x: (3,1) ; W1: (4,3) ; W2: (2,4)
z1 = W1@x + b1 : (4,1)
h1 = ReLU(z1)  : (4,1)
z2 = W2@h1 + b2: (2,1)
Layer 1: (4x3) @ (3x1) + (4x1) -> (4x1) -> ReLU -> (4x1)
Layer 2: (2x4) @ (4x1) + (2x1) -> (2x1)
```

**实测纠正与易错点**：

1. **`-0.0000` 是负零，不是错误。** `A @ A^-1` 打印出 `-0.0000`——浮点运算里 `0.0` 可能有负号。**判等别用 `==`，用 `np.allclose(A @ inv, np.eye(n))`**，否则这个 `-0.0000` 会让相等判断失败。
2. **课文的形状链是"外加 bias"的完整版**：`(m×n)@(n×p) = (m×p)` 只管矩阵乘；加 bias 时 bias 必须是 `(m×1)`（或可广播成 `(m×p)`）。实测里 `W1: (4,3)`、`x: (3,1)` → `(4,1)`，bias 就是 `(4,1)`。
3. **ReLU 会把大量隐藏单元压成 0**：实测 4 个隐藏单元里 3 个输出 `0.0000`，只有 1 个非零。这是正常现象（随机初始化 + 小权重 → 一半左右神经元落在负区），也正是"dead ReLU"问题的雏形——训练时如果某个神经元长期输出 0、梯度也为 0，它就"死了"。
4. **逐元素乘与矩阵乘的案例值得背下来**：同一对矩阵，`A * B = [[5,12],[21,32]]`，`A @ B = [[19,22],[43,50]]`——数字完全不同。写 NumPy 时手滑把 `@` 打成 `*` 是最常见的静默 bug 之一（形状对得上，代码能跑，结果全错）。
5. **`det == 0` 时 `inverse_2x2` 抛错是设计而非缺陷**：代码里 `if det == 0: raise ValueError("Matrix is singular, no inverse exists")`。对浮点矩阵，更稳的判据是 `abs(det) < 1e-12`，因为理论上为 0 的行列式算出来可能是 `1e-17`。
6. **本机无 NumPy 依赖问题**：`matrices.py` 全部用纯 Python 实现，无需第三方包，直接 `python3` 可跑；课文 `Use It` 节的 NumPy 代码需自行 `uv pip install numpy`（注意用 `UV_CACHE_DIR=$PWD/.uv-cache`，默认缓存目录在沙箱里会被拒）。
