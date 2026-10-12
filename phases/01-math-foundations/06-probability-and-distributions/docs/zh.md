# 1/06 概率与分布 / Probability and Distributions

**一句话主题句：模型输出的每一个数字，本质上都是一个概率——看不懂概率，就读不懂 loss。**

**你将构建：从零写出 PMF/PDF、期望方差、采样、softmax、交叉熵、中心极限定理的完整实现——不用 NumPy、不用 SciPy。**

---

## 学习目标 / Learning Objectives

1. 区分离散变量的 **PMF（概率质量函数）** 与连续变量的 **PDF（概率密度函数）**
2. 用条件概率与独立性分析事件关系
3. 手算常见分布（伯努利、均匀、正态、泊松、类别）的期望与方差
4. 解释为什么**正态分布无处不在**（中心极限定理）
5. 说明为什么**语言模型用对数概率**而不是原始概率
6. 把 **softmax** 理解成"把分数变成合法概率分布"的工具
7. 用**交叉熵**衡量两个分布的差异

> **Learning Objectives**
>
> By the end of this lesson, you will be able to:
>
> - Distinguish between PMFs and PDFs
> - Use conditional probability and independence
> - Compute expected value and variance for common distributions
> - Explain why the normal distribution appears everywhere (CLT)
> - Explain why language models use log probabilities
> - Understand softmax as a probability distribution
> - Use cross-entropy to measure distribution differences

---

## 问题所在 / The Problem

训练模型时，你会看到这些数字刷屏：

```
epoch 3  loss = 0.4170   accuracy = 0.89
```

**`loss = 0.4170` 是什么意思？** 为什么不是 0.42？为什么好的模型 loss 会趋近 0 而不是趋近 1？

**答案全在概率里。** 这个数字是**负对数概率**：模型给正确答案分配的概率是 `e^(-0.417) ≈ 0.66`。loss 越小 = 模型对正确答案越自信。

**不懂概率，你就是在盲调超参数。** 这课把所有概率基础一次讲清。

> **The Problem**
>
> When you train a model, you see numbers like `loss = 0.4170`. What does that mean? Why does a good model's loss approach 0 and not 1?
>
> The answer is all in probability. This number is a negative log probability. Without probability literacy, you are tuning hyperparameters blind.

---

## 概念 / The Concept

### 事件、样本空间与概率 / Events, Sample Spaces, and Probability

**样本空间 S** = 所有可能结果的集合。**事件** = 样本空间的一个子集。**概率**把事件映射到 0 到 1 之间的数。

```
抛硬币：S = {H, T}，P(H) = 0.5,  P(T) = 0.5

掷骰子：S = {1, 2, 3, 4, 5, 6}
        P(偶数) = P({2,4,6}) = 3/6 = 0.5
```

**三条公理定义了全部概率论**：

1. 任何事件 `P(A) ≥ 0`
2. `P(S) = 1`（必然发生）
3. `A`、`B` 不能同时发生时，`P(A 或 B) = P(A) + P(B)`

**其余一切**（贝叶斯定理、期望、分布）**都是从这三条推出来的。**

> **Events, Sample Spaces, and Probability**
>
> The sample space S is the set of all possible outcomes. An event is a subset of the sample space. Probability maps events to numbers between 0 and 1.
>
> Three axioms define all of probability:
> 1. P(A) >= 0 for any event A
> 2. P(S) = 1 (something always happens)
> 3. P(A or B) = P(A) + P(B) when A and B cannot both occur
>
> Everything else (Bayes' theorem, expectations, distributions) follows from these three rules.

---

### 条件概率与独立性 / Conditional Probability and Independence

`P(A|B)` = **已知 B 发生了**，A 发生的概率。

```
P(A|B) = P(A 且 B) / P(B)

例：一副牌
  P(King | Face card) = P(King 且 Face card) / P(Face card)
                      = (4/52) / (12/52) = 4/12 = 1/3
```

**实测验证**：`probability.py` 打印 `P(King | Face card) = 0.3333` ✅

**独立性**：知道一个对另一个毫无帮助

```
独立：P(A|B) = P(A)   ⇔   P(A 且 B) = P(A) · P(B)
```

抛硬币是独立的；**不放回抽牌不是**（抽走一张改变了剩下的牌堆）。

> **Conditional Probability and Independence**
>
> P(A|B) is the probability of A given that B happened. Two events are independent when knowing one tells you nothing about the other.

---

### PMF vs PDF（**本课最基础的一组区分**）

| | **PMF 概率质量函数** | **PDF 概率密度函数** |
|---|---|---|
| 变量 | **离散**（骰子、分类） | **连续**（实数、潜变量） |
| 单点含义 | **就是概率**，可以直接读 | **不是概率**，是密度（可以 >1） |
| 怎么得概率 | 直接 `P(X=k)` | **积分** `∫f(x)dx` |
| 归一化 | `Σ = 1` | `∫ = 1` |

**实测**（伯努利 p=0.7）：`P(X=0)=0.3000, P(X=1)=0.7000`，**和 = 1.0000** ✅

**实测**（正态 PDF）：`f(0) = 0.3989`——**注意这个数 >0 但它是密度不是概率**。**单点概率在连续变量里永远是 0**（一个点的宽度是 0）。

**⚠️ 纠正一个常见误解**：**PDF 的值可以大于 1**。比如均匀分布 `U(0, 0.5)`，密度是 `1/0.5 = 2`。**"概率"必须 ≤1，但"密度"不必。**

**在 ML 里的对应**：

- **分类输出是 PMF**（离散选择，softmax 就是造 PMF）
- **VAE 潜空间用 PDF**（连续潜变量）

> **PMF vs PDF**
>
> Discrete random variables have a probability mass function (PMF). Each outcome has a specific probability that you can read off directly.
>
> Continuous random variables have a probability density function (PDF). The density at a single point is not a probability. Probability comes from integrating the density over an interval.
>
> `f(x)` can be greater than 1 (density, not probability).

---

### 常见分布 / Common Distributions

| 分布 | 形态 | 用在哪 | 参数 |
|---|---|---|---|
| **伯努利 Bernoulli** | 一次试验、两种结果 | **二分类** | `p`，`E=p`，`Var=p(1-p)` |
| **类别 Categorical** | 一次试验、k 种结果 | **多分类（softmax 输出）** | `p_i`，`Σp_i = 1` |
| **均匀 Uniform** | 等可能 | **随机初始化** | `[a, b]`，`f = 1/(b-a)` |
| **正态 Normal** | 钟形曲线 | **初始化、CLT、噪声** | `μ, σ²` |
| **泊松 Poisson** | 稀有事件计数 | **事件发生率** | `λ`，`E = Var = λ` |

**正态分布的公式**：

```
f(x) = (1 / √(2πσ²)) · exp(-(x-μ)² / (2σ²))

标准正态 μ=0, σ=1：
  68% 的数据在 1σ 内
  95% 在 2σ 内
  99.7% 在 3σ 内     ← 这就是 "3-sigma 原则"
```

**实测**（正态 μ=0,σ=1）：

```
f(-3) = 0.0044
f(-2) = 0.0540
f(-1) = 0.2420
f(+0) = 0.3989    ← 峰值
f(+1) = 0.2420
f(+2) = 0.0540
f(+3) = 0.0044
```

**看这个对称性**：`f(-3) = f(+3)`、`f(-1) = f(+1)`。**正态分布关于 μ 完全对称**，且离 μ 越远越稀。

> **Common Distributions**
>
> **Bernoulli:** one trial, two outcomes. Models binary classification. **Categorical:** one trial, k outcomes. Models multi-class classification (softmax output). **Uniform:** all outcomes equally likely. Used for random initialization. **Normal (Gaussian):** the bell curve. **Poisson:** counts of rare events in a fixed interval.

---

### 期望与方差 / Expected Value and Variance

**期望** = 加权平均

```
离散：E[X] = Σ xᵢ · P(X=xᵢ)
连续：E[X] = ∫ x · f(x) dx
```

**方差** = 围绕均值的散布程度

```
Var(X) = E[(X - E[X])²] = E[X²] - (E[X])²
标准差 SD = √Var(X)
```

**实测**（公平骰子）：`E[X] = 3.5000, Var(X) = 2.9167, SD = 1.7078`

**手算验证**：`E = (1+2+3+4+5+6)/6 = 3.5` ✅；`Var = E[X²] - (E[X])² = 91/6 - 12.25 = 15.167 - 12.25 = 2.9167` ✅

**在 ML 里的对应**：

- **损失函数就是期望**（数据分布上的平均损失）
- **方差告诉你模型稳定性**：**梯度方差大 = 训练噪声大**

> **Expected Value and Variance**
>
> Expected value is the weighted average outcome. Variance measures spread around the mean. In ML, expected value appears as the loss function. Variance tells you about model stability. High variance in gradients means noisy training.

---

### 联合分布与边缘分布 / Joint and Marginal Distributions

**联合分布 `P(X,Y)`** 同时描述两个随机变量。**边缘分布**把另一个变量"加掉"。

| | Y=0 没伞 | Y=1 有伞 | **边缘 P(X)** |
|---|---|---|---|
| X=0 晴 | 0.40 | 0.10 | **0.50** |
| X=1 雨 | 0.05 | 0.45 | **0.50** |
| **边缘 P(Y)** | **0.45** | **0.55** | 1.00 |

**边缘 = 把行/列加起来。**

```
P(X=x) = Σ_y P(X=x, Y=y)
```

**实测验证**：`Marginal X = [0.5, 0.5]`，`Marginal Y = [0.45, 0.55]`，**独立？False** ✅

**为什么不独立**：`P(雨 且 有伞) = 0.45`，但 `P(雨)·P(有伞) = 0.5 × 0.55 = 0.275`。**0.45 ≠ 0.275** → 两者相关（下雨和带伞当然相关）。

> **Joint and Marginal Distributions**
>
> A joint distribution P(X, Y) describes two random variables together. The marginal distribution sums out the other variable.

---

### 正态分布为什么无处不在 / Why the Normal Distribution Shows Up Everywhere

**中心极限定理（CLT）**：很多独立随机变量的**和（或平均）收敛到正态分布**，**无论原始分布是什么**。

```
掷 1 个骰子：     均匀分布（平的）
2 个骰子的平均：  三角形（有个尖）
30 个骰子的平均： 几乎完美的钟形

对任何起始分布都成立。
```

**实测**（对 `U[0,1)` 求平均）：

```
n= 1: mean=0.4971, std=0.2866
n= 2: mean=0.4995, std=0.2044
n= 5: mean=0.5003, std=0.1287
n=30: mean=0.5005, std=0.0524
```

**看 std 列**：`0.2866 → 0.2044 → 0.1287 → 0.0524`。**n 越大越收窄，形状越像钟形。**

**⚠️ 一个精确表述的纠正**：CLT 说的是**平均值的分布趋于正态**，不是"所有数据都服从正态"。常见的错引是"所有数据都服从正态"——**那是错的**（B 选项就是这个陷阱）。

**这就是为什么**：

- 测量误差近似正态（很多小的独立来源）
- **神经网络权重初始化用正态分布**
- **SGD 的梯度噪声近似正态**（多样本梯度之和）
- **正态是给定均值方差下的最大熵分布**

> **Why the Normal Distribution Shows Up Everywhere**
>
> The Central Limit Theorem: the sum (or average) of many independent random variables converges to a normal distribution, regardless of the original distribution. This works for ANY starting distribution.

---

### 对数概率 / Log Probabilities

**原始概率会出数值问题**：把许多小概率乘起来，很快就下溢到 0。

```
P(句子) = P(词1) × P(词2) × ... × P(词n)
        = 0.01 × 0.003 × 0.02 × ...
        → 0.0（约 30 项后下溢）
```

**对数概率修复了它**：乘法变加法。

```
log P(句子) = log P(词1) + log P(词2) + ...
            = -4.6 + -5.8 + -3.9 + ...
            → 有限的数（不下溢）
```

**实测**（50 个词、每个概率 0.01）：

```
P(word)^50 = 0.01^50
Raw product: 1.00e-100（更多项就下溢）
Log sum:     -230.2585（稳定）
Recovered:   1.00e-100
```

**看这两个数的对比**：`1e-100`（原始积，接近下溢边缘）vs `-230.2585`（对数和，一个完全正常的数）。**再乘 100 个词，原始积直接变 0，对数和只是变成 -1230，永远不爆。**

**规则**：

- `log(a·b) = log(a) + log(b)`
- **对数概率永远 ≤ 0**（因为 `0 < P ≤ 1`）
- **越负 = 越不可能**
- **交叉熵损失 = 正确类的负对数概率**

> **Log Probabilities**
>
> Raw probabilities cause numerical problems. Multiplying many small probabilities together quickly underflows to zero. Log probabilities fix this. Multiplications become additions. Cross-entropy loss is the negative log probability of the correct class.

---

### Softmax 作为一个概率分布 / Softmax as a Probability Distribution

神经网络输出原始分数（**logits**）。**softmax 把它们变成合法的概率分布。**

```
softmax(zᵢ) = exp(zᵢ) / Σ exp(zⱼ)

性质：
  - 所有输出在 (0, 1)
  - 所有输出之和 = 1
  - 保持输入的相对顺序
  - exp() 放大 logits 之间的差异
```

**实测**：

```
Logits:  [2.0, 1.0, 0.1]
Softmax: [0.6590, 0.2424, 0.0986]
Sum:     1.0000   ✅
```

**softmax 技巧（softmax trick）**：**指数前先减掉最大值**，防溢出。

```
z = [100, 101, 102]
exp(102) = 溢出！

z_shifted = z - max(z) = [-2, -1, 0]
exp(0) = 1  安全

结果完全相同，但不溢出。
```

**实测验证**：

```
Logits:  [100, 101, 102]
Softmax: [0.0900, 0.2447, 0.6652]
(No overflow because we subtract max before exp)
```

**为什么减掉最大值不影响结果**：softmax 是**比值**，分子分母同乘 `exp(-max)` 后比值不变。**这是一个纯粹的数值技巧，不改变数学。**

**log-softmax** 把 softmax 和 log 结合起来，数值更稳。**PyTorch 内部的交叉熵损失就用它。**

> **Softmax as a Probability Distribution**
>
> Neural networks output raw scores (logits). Softmax converts them into a valid probability distribution. The softmax trick: subtract the max logit before exponentiating to prevent overflow. Log-softmax combines softmax and log for numerical stability. PyTorch uses this internally for cross-entropy loss.

---

### 采样 / Sampling

**采样** = 从分布里抽随机值。在 ML 里：

- **Dropout** 随机采样哪些神经元置零
- **数据增强**采样随机变换
- **语言模型**从预测分布里采样下一个词
- **扩散模型**采样噪声然后逐步去噪

从任意分布采样需要技巧：**逆变换采样、拒绝采样、重参数化技巧**（VAE 用的就是这个）。

**实测**：

```
Sampling: Bernoulli (p=0.3, n=20)
  Samples: [0, 1, 1, 1, 0, 0, 0, 1, ...]
  Empirical mean: 0.5000 (expected 0.3)      ← 20 个样本太少

Sampling: Categorical, 1000 samples
  Empirical: [0.088, 0.285, 0.415, 0.212]
  Expected:  [0.1, 0.3, 0.4, 0.2]             ← 1000 个样本接近

Sampling: Normal (Box-Muller), 10000 samples
  Sample mean: 0.0036 (expected 0)            ← 10000 个很准
  Sample var:  0.9819 (expected 1)
```

**⚠️ 这三组数据揭示了一个实践规律**：**样本量决定经验分布的可信度。**

| 样本量 | 误差 | 用途 |
|---|---|---|
| 20 | 均值 0.5 vs 真值 0.3（**差 67%**） | 只能看趋势 |
| 1,000 | 各类差 ±1.5% | 调参够用 |
| 10,000 | 均值差 0.004 | 科研级精度 |

**这就是为什么"训练集大小"是 ML 里最贵的资源。**

> **Sampling**
>
> Sampling means drawing random values from a distribution. In ML: Dropout randomly samples which neurons to zero out. Data augmentation samples random transformations. Language models sample the next token. Diffusion models sample noise and progressively denoise.

```figure
gaussian-pdf
```

---

## 动手构建 / Build It

### Step 1：概率基础

```python
import math
import random

def factorial(n):
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

def combinations(n, k):
    return factorial(n) // (factorial(k) * factorial(n - k))

def conditional_probability(p_a_and_b, p_b):
    return p_a_and_b / p_b

p_king_given_face = conditional_probability(4/52, 12/52)
print(f"P(King | Face card) = {p_king_given_face:.4f}")
```

**实测**：`P(King | Face card) = 0.3333` ✅

**`conditional_probability` 只有一行**：`P(A|B) = P(A 且 B) / P(B)`。**整个贝叶斯推断都建立在这一行上。**

### Step 2：从零写 PMF 和 PDF

```python
def bernoulli_pmf(k, p):
    return p if k == 1 else (1 - p)

def categorical_pmf(k, probs):
    return probs[k]

def poisson_pmf(k, lam):
    return (lam ** k) * math.exp(-lam) / factorial(k)

def uniform_pdf(x, a, b):
    if a <= x <= b:
        return 1.0 / (b - a)
    return 0.0

def normal_pdf(x, mu, sigma):
    coeff = 1.0 / (sigma * math.sqrt(2 * math.pi))
    exponent = -0.5 * ((x - mu) / sigma) ** 2
    return coeff * math.exp(exponent)
```

**注意 PMF 和 PDF 的实现长得完全不一样**：

- **PMF 直接返回一个数**（就是概率）
- **PDF 返回一个"密度"**（要用时得积分）

`normal_pdf` 那三行就是钟形曲线的公式：

```
coeff = 1/(σ√(2π))          ← 归一化因子，保证 ∫=1
exponent = -0.5·((x-μ)/σ)²   ← 高斯核，离 μ 越远越小
return coeff · exp(exponent)  ← 两者相乘
```

### Step 3：期望与方差

```python
def expected_value(values, probabilities):
    return sum(v * p for v, p in zip(values, probabilities))

def variance(values, probabilities):
    mu = expected_value(values, probabilities)
    return sum(p * (v - mu) ** 2 for v, p in zip(values, probabilities))

die_values = [1, 2, 3, 4, 5, 6]
die_probs = [1/6] * 6
mu = expected_value(die_values, die_probs)
var = variance(die_values, die_probs)
print(f"Die: E[X] = {mu:.4f}, Var(X) = {var:.4f}, SD = {var**0.5:.4f}")
```

**实测**：`E[X] = 3.5000, Var(X) = 2.9167, SD = 1.7078` ✅

**方差的实现用了定义式 `E[(X-μ)²]`**，而不是 `E[X²] - (E[X])²`。**数值上后者更快但容易因浮点误差变负**，定义式更稳。**生产代码里常用 Welford 在线算法**。

### Step 4：从分布采样

```python
def sample_bernoulli(p, n=1):
    return [1 if random.random() < p else 0 for _ in range(n)]

def sample_categorical(probs, n=1):
    cumulative = []
    total = 0
    for p in probs:
        total += p
        cumulative.append(total)
    samples = []
    for _ in range(n):
        r = random.random()
        for i, c in enumerate(cumulative):
            if r <= c:
                samples.append(i)
                break
    return samples

def sample_normal_box_muller(mu, sigma, n=1):
    samples = []
    for _ in range(n):
        u1 = random.random()
        u2 = random.random()
        z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
        samples.append(mu + sigma * z)
    return samples
```

**三个采样方法各代表一类技巧**：

| 方法 | 思路 | 用在哪 |
|---|---|---|
| `sample_bernoulli` | **直接比较随机数和 p** | 二分类 |
| `sample_categorical` | **累积分布 + 二分查找** | 多分类（softmax 输出采样） |
| `sample_normal_box_muller` | **Box-Muller 变换**：用两个均匀随机数造正态 | **任意正态采样** |

**Box-Muller 是本节最值得看的**：

```python
z = √(-2·log(u1)) · cos(2π·u2)
```

**两个 `U[0,1)` 变量，经 log 和 cos 一变换，就得到标准正态**。**这不是近似，是精确的数学变换**——概率论里最漂亮的技巧之一。**PyTorch 的 `torch.randn()` 内部用的也是它（或类似的 Ziggurat）。**

### Step 5：Softmax 与对数概率

```python
def softmax(logits):
    max_logit = max(logits)
    shifted = [z - max_logit for z in logits]
    exps = [math.exp(z) for z in shifted]
    total = sum(exps)
    return [e / total for e in exps]

def log_softmax(logits):
    max_logit = max(logits)
    shifted = [z - max_logit for z in logits]
    log_sum_exp = max_logit + math.log(sum(math.exp(z) for z in shifted))
    return [z - log_sum_exp for z in logits]

def cross_entropy_loss(logits, target_index):
    log_probs = log_softmax(logits)
    return -log_probs[target_index]
```

**三个函数的数学关系**：

```
softmax      把 logits 变成概率
log_softmax  把 logits 变成对数概率（数值更稳）
cross_entropy 取正确类的负对数概率 = 损失
```

**`log_softmax` 里的 `log_sum_exp` 是数值稳定版的 `log(Σexp(z))`**：

```
log(Σexp(z)) = max(z) + log(Σexp(z - max(z)))
                ↑ 技巧        ↑ 里面的值 ≤0，安全
```

**实测**：

```
Logits:      [2.0, 1.0, 0.1]
Log-softmax: [-0.4170, -1.4170, -2.3170]
Verify exp:  [0.6590, 0.2424, 0.0986]   ← 取 exp 后和 softmax 一致 ✅

Cross-Entropy Loss (target=0): 0.4170
```

**看这个数字的含义**：`-log_softmax[0] = -(-0.4170) = 0.4170`。**loss = 0.4170 意思是"模型给正确答案分配的概率是 e^(-0.417) = 0.66"** ——**你训练时看到的那个 loss 数字，它的含义就是这个。**

### Step 6：中心极限定理演示

```python
def demonstrate_clt(dist_fn, n_samples, n_averages):
    averages = []
    for _ in range(n_averages):
        samples = [dist_fn() for _ in range(n_samples)]
        averages.append(sum(samples) / len(samples))
    return averages
```

**实测**：

```
n= 1: mean=0.4971, std=0.2866
n= 2: mean=0.4995, std=0.2044
n= 5: mean=0.5003, std=0.1287
n=30: mean=0.5005, std=0.0524
```

**看 std 那一列**：`0.2866 → 0.2044 → 0.1287 → 0.0524`。**这就是 CLT 的两个效应**：

1. **均值趋于 `0.5`**（`U[0,1)` 的真实均值）
2. **标准差按 `1/√n` 收窄**（`0.2866/√2 = 0.2027 ≈ 0.2044` ✅）

**这就解释了为什么"大数据集"能让估计变准**——不是因为数据多本身，而是**平均的方差按 `1/n` 收窄**。

### Step 7：可视化

```python
import matplotlib.pyplot as plt

xs = [mu + sigma * (i - 500) / 100 for i in range(1001)]
ys = [normal_pdf(x, mu, sigma) for x, mu, sigma in ...]
plt.plot(xs, ys)
```

完整实现见 `code/probability.py`。

**本机实测**：`matplotlib not available, skipping visualization.` —— 本机没装 matplotlib，跳过了绘图，但**所有数值计算全部跑通**。

---

## 实际使用 / Use It

用 NumPy 和 SciPy，上面所有东西都是一行：

```python
import numpy as np
from scipy import stats

normal = stats.norm(loc=0, scale=1)
samples = normal.rvs(size=10000)
print(f"Mean: {np.mean(samples):.4f}, Std: {np.std(samples):.4f}")
print(f"P(X < 1.96) = {normal.cdf(1.96):.4f}")

logits = np.array([2.0, 1.0, 0.1])
from scipy.special import softmax, log_softmax
probs = softmax(logits)
log_probs = log_softmax(logits)
print(f"Softmax: {probs}")
print(f"Log-softmax: {log_probs}")
```

**你已经从零写过这些了。现在你知道库函数在做什么。**

> **Use It**
>
> With NumPy and SciPy, everything above is one-liners. You built these from scratch. Now you know what the library calls are doing.

---

## 练习 / Exercises

1. 为指数分布实现**逆变换采样**。采样 10,000 个值，把直方图和真实 PDF 对比。
2. 给两个"灌铅骰子"建联合分布表。算出边缘分布，判断两个骰子是否独立。
3. 一个 5 类分类器输出 logits `[2.0, 0.5, -1.0, 3.0, 0.1]`，正确类是 index 3。**算出交叉熵损失**，再用 PyTorch 的 `nn.CrossEntropyLoss` 验证。
4. 写一个函数，输入一串对数概率，返回最可能的序列、总对数概率、以及等价的原始概率。用一个 50 词、每词概率 0.01 的句子测试。

> **Exercises**
>
> 1. Implement inverse transform sampling for the exponential distribution.
> 2. Build a joint distribution table for two loaded dice. Compute the marginal distributions and check whether the dice are independent.
> 3. Compute the cross-entropy loss for a 5-class classifier that outputs logits `[2.0, 0.5, -1.0, 3.0, 0.1]` when the correct class is index 3.
> 4. Write a function that takes a list of log probabilities and returns the most likely sequence, the total log probability, and the equivalent raw probability.

---

## 关键术语 / Key Terms

| 术语 | 大家的说法 | 它真正的含义 |
|------|----------|------------|
| 样本空间 Sample space | "所有可能性" | 实验的每个可能结果的集合 S |
| PMF | "概率函数" | 给出每个离散结果的**确切概率**，总和为 1 |
| PDF | "概率曲线" | 连续变量的**密度**函数。**积分**才得概率 |
| 条件概率 Conditional probability | "给定某事的概率" | `P(A|B) = P(A且B)/P(B)`。贝叶斯思维的基础 |
| 独立性 Independence | "互不影响" | `P(A且B) = P(A)·P(B)`。知道一个对另一个毫无帮助 |
| 期望 Expected value | "平均值" | 所有结果的**概率加权**和。**损失函数就是期望** |
| 方差 Variance | "多分散" | 围绕均值的期望平方偏差。高方差 = 噪声大、估计不稳 |
| 正态分布 Normal distribution | "钟形曲线" | `f(x) = (1/√(2πσ²))·exp(-(x-μ)²/(2σ²))`。因 CLT 而无处不在 |
| 中心极限定理 CLT | "平均会变正态" | 多个独立样本的均值收敛到正态，**无论来源分布** |
| 联合分布 Joint distribution | "两个变量一起" | `P(X,Y)` 描述 X、Y 每种组合的概率 |
| 边缘分布 Marginal distribution | "把另一个加掉" | `P(X) = Σ_y P(X,Y)`。从联合恢复单变量分布 |
| 对数概率 Log probability | "概率的对数" | `log P(x)`。**乘积变求和**，防止长序列数值下溢 |
| Softmax | "把分数变概率" | `softmax(zᵢ) = exp(zᵢ)/Σexp(zⱼ)`。把 logits 映射成合法概率分布 |
| 交叉熵 Cross-entropy | "那个损失函数" | `-Σ(p_true · log(p_predicted))`。衡量两个分布的差异。越低越好 |
| Logits | "模型原始输出" | softmax 之前的**未归一化分数**。得名于 logistic 函数 |
| 采样 Sampling | "抽随机值" | 按概率分布生成数值。模型如何生成输出 |

> **Key Terms**
>
> | Term | What people say | What it actually means |
> |------|----------------|----------------------|
> | Sample space | "All the possibilities" | The set S of every possible outcome of an experiment |
> | PMF | "The probability function" | A function that gives the exact probability of each discrete outcome, summing to 1 |
> | PDF | "The probability curve" | A density function for continuous variables. Integrate it over an interval to get probability |
> | Conditional probability | "Probability given something" | P(A\|B) = P(A and B) / P(B) |
> | Expected value | "The average" | The probability-weighted sum of all outcomes. The loss function is an expected value |
> | Normal distribution | "The bell curve" | f(x) = (1/sqrt(2*pi*sigma^2)) * exp(-(x-mu)^2/(2*sigma^2)) |
> | Central Limit Theorem | "Averages become normal" | The mean of many independent samples converges to a normal distribution regardless of the source |
> | Log probability | "Log of the probability" | log P(x). Turns products into sums, preventing numerical underflow |
> | Softmax | "Turn scores into probabilities" | softmax(z_i) = exp(z_i) / sum(exp(z_j)) |
> | Cross-entropy | "The loss function" | -sum(p_true * log(p_predicted)). Measures how different two distributions are |

---

## 延伸阅读 / Further Reading

- [3Blue1Brown: But what is the Central Limit Theorem?](https://www.youtube.com/watch?v=zeJD6dqJ5lo) —— 平均为什么会变正态的可视化证明
- [Stanford CS229 Probability Review](https://cs229.stanford.edu/section/cs229-prob.pdf) —— 涵盖本课内容及更多的简明参考
- [The Log-Sum-Exp Trick](https://gregorygundersen.com/blog/2020/02/09/log-sum-exp/) —— 数值稳定性为何重要以及如何实现

> **Further Reading**
>
> - [3Blue1Brown: But what is the Central Limit Theorem?](https://www.youtube.com/watch?v=zeJD6dqJ5lo) - visual proof of why averages become normal
> - [Stanford CS229 Probability Review](https://cs229.stanford.edu/section/cs229-prob.pdf) - concise reference covering everything here and more
> - [The Log-Sum-Exp Trick](https://gregorygundersen.com/blog/2020/02/09/log-sum-exp/) - why numerical stability matters and how to achieve it

---

## 实测数据与纠正 / Measured Data & Corrections

**实测环境**：macOS（zsh），`python3 code/probability.py`（零依赖，除 Step 7 可视化因本机无 matplotlib 跳过外全部通过）。

### 实测一：条件概率

```
P(King | Face card) = 0.3333
```

**手算验证**：`(4/52) / (12/52) = 4/12 = 1/3 = 0.3333` ✅

**纠正一个常见错觉**：`P(King | Face card)` **不是 4/52**（那是 `P(King)`）。**条件概率会缩小分母**——已知是花牌，那就只在 12 张花牌里挑 4 张 King。

### 实测二：PMF 归一化验证

```
Bernoulli (p=0.7):  P(0)=0.3000, P(1)=0.7000     Σ = 1.0000 ✅
Categorical:        [0.1, 0.3, 0.4, 0.2]          Σ = 1.0000 ✅
Poisson (λ=3):      P(0)=0.0498 ... P(9)=0.0027
```

**泊松的总和只到 `P(9)`，Σ ≈ 0.9966** —— **不是 1！** 这是**截断误差**，因为泊松支持无穷多取值（k=0,1,2,...）。**算分布和时要一直加到尾部足够小，或直接用归一化公式。**

**这就是为什么生产库（SciPy）不会让你自己手写 PMF**——数值细节很多。

### 实测三：正态 PDF 的对称性

```
f(-3) = 0.0044     f(+3) = 0.0044
f(-2) = 0.0540     f(+2) = 0.0540
f(-1) = 0.2420     f(+1) = 0.2420
f(+0) = 0.3989              ← 峰值
```

**完全对称** ✅。**峰值 `f(0) = 0.3989 = 1/√(2π) ≈ 1/2.5066`** —— 这就是正态分布归一化常数的来源。

**⚠️ 一个关键认知**：**`f(0) = 0.3989 < 1`，但 PDF 可以 >1。** 比如 `U(0, 0.5)` 的密度是 `1/0.5 = 2`。**"概率 ≤1"只对 PMF 成立，PDF 是密度不必受此限制。**

### 实测四：公平骰子的期望与方差

```
Fair die: E[X] = 3.5000, Var(X) = 2.9167, SD = 1.7078
```

**手算**：`E = (1+2+3+4+5+6)/6 = 3.5` ✅
`E[X²] = (1+4+9+16+25+36)/6 = 91/6 = 15.1667`
`Var = 15.1667 - 3.5² = 15.1667 - 12.25 = 2.9167` ✅

**注意 `Var = 2.9167` 而不是 3** —— 因为骰子只有 6 面，取值有限。**方差 3 是 `U[0,6]` 连续均匀的方差**（`(6-0)²/12 = 3`），**离散骰子和连续均匀的方差不同**。

### 实测五：样本量决定精度（**本课最有实践价值的一组**）

```
Sampling: Bernoulli (p=0.3, n=20)   → Empirical mean: 0.5000 (expected 0.3)   ← 差 67%
Sampling: Categorical, n=1000        → [0.088, 0.285, 0.415, 0.212] vs [0.1, 0.3, 0.4, 0.2]   ← 各差 ±1.5%
Sampling: Normal, n=10000            → mean 0.0036 (expected 0), var 0.9819 (expected 1)  ← 很准
```

**这三组数据是"训练集大小是 ML 最贵资源"的直接证据**：

| 样本量 | 误差 | 用途 |
|---|---|---|
| 20 | **67%** | 只能看趋势，不能下结论 |
| 1,000 | 1.5% | 调参够用 |
| 10,000 | 0.4% | 科研级精度 |

**⚠️ 常见错误**：看到 `0.5` vs `0.3` 就以为采样函数写错了。**20 个样本就是这样**。**结论：评估任何"经验 vs 理论"对比时，先看样本量。**

### 实测六：Softmax 数值稳定技巧

```
Logits:  [2.0, 1.0, 0.1]
Softmax: [0.6590, 0.2424, 0.0986]
Sum:     1.0000 ✅

Logits:  [100, 101, 102]          ← 极端值
Softmax: [0.0900, 0.2447, 0.6652]
(No overflow because we subtract max before exp)
```

**如果不减最大值会怎样**：`exp(102) ≈ 2.7e44`，**接近 Python float 的上限 `1.8e308`**，再大就 `inf`。而 `exp(1000)` 直接 `OverflowError`。

**减最大值后的结果完全不变**，因为：

```
softmax(z)ᵢ = exp(zᵢ) / Σexp(zⱼ)
            = exp(zᵢ - m) / Σexp(zⱼ - m)      （分子分母同乘 exp(-m)）
```

**数学上等价，数值上安全。** 这是**softmax 技巧的全部内容**。

**⚠️ 一个常被忽视的细节**：**减最大值后，最大的那个变成 `exp(0) = 1`，其余都是 `exp(负数) < 1`**，所以分子分母都在 `(0, 1]` 之间，**永远不会溢出**。

### 实测七：对数概率的威力（**语言模型必须用它的原因**）

```
P(word)^50 = 0.01^50
Raw product: 1.00e-100    (underflows with more terms)
Log sum:     -230.2585    (stable)
Recovered:   1.00e-100    ✅
```

**这两个数字的对比就是本课的落点**：

| 表示 | 50 词时 | 100 词时 | 200 词时 |
|---|---|---|---|
| 原始积 | `1e-100` | `1e-200` | **`0.0`（下溢）** |
| 对数和 | `-230` | `-460` | `-920`（永远正常） |

**语言模型处理长句子、长文档，必须用对数概率。** **这就是为什么 PyTorch 的 `nn.CrossEntropyLoss` 内部用 log-softmax 而不是 softmax + log**（后者会在中间步骤下溢）。

### 实测八：联合分布与独立性

```
Joint (weather x umbrella):
  Sun,  no umbrella: 0.4
  Sun,  umbrella:    0.1
  Rain, no umbrella: 0.05
  Rain, umbrella:    0.45
Marginal X (weather):  [0.5, 0.5]
Marginal Y (umbrella): [0.45, 0.55]
Independent? False
```

**手算验证独立性**：

```
P(雨 且 有伞) = 0.45
P(雨) · P(有伞) = 0.5 × 0.55 = 0.275

0.45 ≠ 0.275  →  不独立 ✅
```

**为什么它们相关**：**下雨导致带伞**，是因果关系。**这就是"独立性"最直观的反例** —— 如果 X、Y 真的独立，`P(X,Y)` 必须等于 `P(X)·P(Y)`，任何偏离都说明它们有联系。

**⚠️ 纠正一个常见误解**：**"边缘分布的和 = 1"不等于"独立"**。本例的边缘 `[0.5, 0.5]` 和 `[0.45, 0.55]` 都正确加和为 1，但**它们明显相关**。**判独立要看联合是否等于边缘之积。**

### 实测九：中心极限定理的量化

```
n= 1: mean=0.4971, std=0.2866
n= 2: mean=0.4995, std=0.2044
n= 5: mean=0.5003, std=0.1287
n=30: mean=0.5005, std=0.0524
```

**验证 `1/√n` 缩放律**：

```
n=1  → std 0.2866
n=2  → 预测 0.2866/√2 = 0.2027，实测 0.2044  ✅ 差 0.8%
n=5  → 预测 0.2866/√5 = 0.1282，实测 0.1287  ✅ 差 0.4%
n=30 → 预测 0.2866/√30 = 0.0523，实测 0.0524  ✅ 差 0.2%
```

**完美吻合 `1/√n` 律。** **这就是"数据越多估计越准"的数学本质**——**不是数据多本身好，而是平均的方差按 `1/n` 收窄。**

**⚠️ 纠正 CLT 的常见错误表述**：CLT 说的是 **"平均值的分布趋于正态"**，**不是"所有数据都服从正态"**。本例中 `U[0,1)` 的**单个样本**依然均匀分布，**只有平均值才变正态**。

### 实测十：交叉熵的数值含义

```
Logits: [2.0, 1.0, 0.1], target: 0
Cross-entropy loss: 0.4170
```

**反推模型的信心**：

```
loss = -log P(正确类) = 0.4170
P(正确类) = e^(-0.4170) = 0.6590
```

**看这个对应关系**：softmax 输出的 `P(类0) = 0.6590`，而 loss 是 `0.4170`。**loss 的每一个数字都直接对应模型对正确答案的置信度。**

| loss | P(正确类) | 含义 |
|---|---|---|
| 0.1 | 0.90 | 很自信 |
| 0.4170 | 0.66 | 本例 |
| 1.0 | 0.37 | 不太确定 |
| 2.3 | 0.10 | 几乎乱猜 |
| 10 | 0.00005 | 完全错 |

**这就是"loss 越小越好"的量化解释。** **你训练时看到的每一个 loss 数字，都可以直接读出模型对正确答案的信心。**

### 实测纠正汇总（一句话版）

| # | 常见错误认知 | 实测纠正 |
|---|---|---|
| 1 | "条件概率 = 无条件概率" | `P(King\|Face) = 1/3`，**不是** `4/52` |
| 2 | "PDF 的值也必须 ≤1" | PDF 是**密度**，可以 >1（如 `U(0,0.5)` 密度=2） |
| 3 | "样本 20 个就够" | 20 个样本误差 **67%**，**结论不可信** |
| 4 | "softmax 减最大值会改结果" | **数学等价**，纯粹是数值技巧 |
| 5 | "CLT 说所有数据服从正态" | CLT 说**平均值**趋于正态，单个样本不变 |
| 6 | "边缘和=1 就独立" | 独立要 `P(X,Y) = P(X)·P(Y)`，**边缘正确不代表独立** |
| 7 | "loss 数字只是个分数" | `loss=0.417` 就是 `P(正确类)=0.66`，**直接读出置信度** |
| 8 | "泊松 P(0..9) 加起来应是 1" | 是**截断误差**，泊松支持无穷取值，尾部还在 |

---

## 本课产物 / Deliverables

- **讲义**：`docs/zh.md`（本文件，双语对照 + 实测纠正十节）
- **代码**：`code/probability.py`（零依赖实现：PMF/PDF/期望/方差/采样/softmax/CLT）
- **对照源**：`docs/en.md`（458 行，未改动）

**下一课 1/07 Bayes Theorem —— 用今天学的条件概率，推断"看到数据后该怎么更新信念"。**
