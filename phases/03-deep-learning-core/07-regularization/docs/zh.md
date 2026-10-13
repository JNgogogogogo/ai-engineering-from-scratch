# 正则化：Dropout、权重衰减、归一化

> 你的模型训练集 99%，测试集 60%。它记住了数据而不是学到了规律。正则化是你对复杂度征收的税，逼迫模型泛化。

**类型：** Build
**语言：** Python
**前置课程：** 03.06（优化器）
**时间：** 约 75 分钟

## 学习目标

- 从零实现 Dropout（inverted scaling）、L2 权重衰减、BatchNorm、LayerNorm、RMSNorm
- 测量 train-test 准确率差距，诊断过拟合
- 解释为什么 Transformer 用 LayerNorm 而非 BatchNorm，以及现代 LLM 为何偏爱 RMSNorm
- 根据过拟合严重程度选择正确的正则化组合

---

## 问题所在

一个参数够多的神经网络可以记住任何数据集。这不是假设——Zhang et al. (2017) 用标准网络在 ImageNet 上用随机标签训练证明了这一点。网络在完全随机的标签分配上达到了接近零的训练损失。它记住了一百万个随机输入输出对，没有任何模式可学。训练损失完美，测试准确率为零。

这就是过拟合问题，而且模型越大越严重。GPT-3 有 1750 亿参数，训练集约 5000 亿 token。没有正则化，它只会复述训练样本而不是学习可泛化的模式。

训练性能和测试性能之间的差距就是**过拟合差距**。本课的每种技术从不同角度攻击这个差距。

---

## 核心概念

### 过拟合光谱

每个模型都处于从欠拟合（太简单，抓不住模式）到过拟合（太复杂，抓了噪声）的光谱上。最佳点在中间，正则化从过拟合一侧把模型推向那里。

### Dropout

最简单的正则化技术，解释也最优雅。训练时，以概率 p 随机将每个神经元的输出置零。

**Inverted Dropout**（实际实现）：
```
训练时：output = activation(z) * mask / (1 - p)   # mask[i] ~ Bernoulli(1-p)
测试时：output = activation(z)                     # 什么都不用做
```

在训练时做缩放，测试代码就不需要知道 dropout 的存在。

**集成解释**：N 个神经元的网络，dropout 产生 2^N 个可能的子网络。训练 dropout 近似同时训练所有 2^N 个子网络。测试时用全部神经元，等价于对 2^N 个子网络取平均——单个模型就构成了一个巨大集成。

默认值：Transformer p=0.1，MLP p=0.5，CNN p=0.2-0.3。

### 权重衰减（L2 正则化）

在损失上加所有权重的平方和：
```
total_loss = task_loss + (λ/2) * Σ(w_i²)
```

梯度为 λ·w——每一步，每个权重按其大小比例向零收缩。大权重受罚更重。

λ 典型值：AdamW 训 Transformer 用 0.01，SGD 训 CNN 用 1e-4，严重过拟合用 0.1。

**重要**：在 SGD 中权重衰减等价于 L2 正则化，但在 Adam 中不等价。用 Adam 训练时始终用 AdamW（解耦权重衰减），这在 06 优化器一课中已讲过。

### Batch Normalization

在 mini-batch 维度上归一化每层的输出：
```
μ = (1/B) * Σ(x_i)                    # batch 均值
σ² = (1/B) * Σ((x_i - μ)²)           # batch 方差
x̂ = (x_i - μ) / √(σ² + ε)           # 归一化
y = γ * x̂ + β                         # 缩放和偏移
```

γ 和 β 是可学习参数，让网络在需要时可以撤销归一化。

**训练 vs 推理**：训练时 μ、σ 来自当前 mini-batch；推理时用训练中累积的运行均值和方差（指数移动平均，momentum=0.1，即 90% 旧 + 10% 新）。

**为什么 BatchNorm 有效**仍有争议。原论文声称它减少了"内部协变量偏移"。Santurkar et al. (2018) 证明这个解释是错的。真正原因：BatchNorm 使 loss landscape 更平滑，梯度更有预测性，优化器可以安全地用更大步长。这就是为什么 BatchNorm 允许用更高学习率、更快收敛。

**根本限制**：依赖 batch 统计。batch size=1 时均值方差无意义；batch < 32 时统计量噪声大、伤性能。

### Layer Normalization

跨特征维度（而非跨 batch）归一化：
```
μ = (1/D) * Σ(x_j)
σ² = (1/D) * Σ((x_j - μ)²)
x̂ = (x_j - μ) / √(σ² + ε)
y = γ * x̂ + β
```

每个样本独立归一化——不依赖 batch size。这就是 Transformer 用 LayerNorm 而非 BatchNorm 的原因：序列长度可变，batch 常常很小（生成时甚至为 1），训练和推理计算完全相同。

### RMSNorm

去掉均值减除的 LayerNorm（Zhang & Sennrich, 2019）：
```
rms = √((1/D) * Σ(x_j²))
y = γ * x / rms
```

就这么简单。没有均值计算，没有 β 参数。观察发现：LayerNorm 中的重新中心化（减均值）对性能贡献很小，但消耗计算。去掉它，精度不变，开销减少约 10%。

LLaMA、LLaMA 2、LLaMA 3、Mistral 以及大多数现代 LLM 都用 RMSNorm。

### 三种归一化对比

| | BatchNorm | LayerNorm | RMSNorm |
|---|---|---|---|
| 归一化维度 | 跨 batch，逐特征 | 跨特征，逐样本 | 跨特征，逐样本（无均值） |
| batch 依赖 | 需要 batch > 32 | 不依赖 | 不依赖 |
| 训练/推理 | 不同（running stats） | 相同 | 相同 |
| 典型用途 | CNN | Transformer | 现代 LLM |
| 额外参数 | γ, β | γ, β | 仅 γ |

### 数据增强作为正则化

不是修改模型，而是修改数据。变换训练输入同时保持标签不变：
- 图像：随机裁剪、翻转、旋转、颜色抖动、cutout
- 文本：同义词替换、回译、随机删除
- 音频：时间拉伸、音高偏移、噪声添加

效果等同正则化：增加有效训练集大小，迫使模型学习不变结构。

### 早停

最简单的正则化器：验证损失开始上升时停止训练。实践中，每 epoch 追踪验证损失，保存最佳模型，在"patience"窗口（通常 5-20 epoch）内继续训练。如果窗口内没有改善，停止并加载最佳模型。

### 何时用什么

- train-test gap > 10%：重正则化（Dropout 0.3-0.5，权重衰减 0.01-0.1，激进数据增强，早停）
- gap 5-10%：中等正则化（Dropout 0.1-0.2，权重衰减 0.001-0.01，BatchNorm/LayerNorm）
- gap < 5%：轻正则化（Dropout 0.05-0.1，权重衰减 1e-4）

---

## 动手构建

课程提供了纯 Python 零依赖实现（`code/main.py`，347 行），逐步演示六个步骤：

### Step 1：Dropout（训练与评估模式）

实现 inverted dropout：训练时随机置零并除以 (1-p) 缩放，评估时原样输出。

实测输出（p=0.5）：三次训练 pass 分别保留 4/8、3/8、4/8 个神经元，均值 ~4.5（缩放后）；eval pass 全部保留，均值 4.5。验证了 inverted scaling 使训练/测试期望一致。

### Step 2：L2 权重衰减

`l2_regularization(weights, λ)` 计算 (λ/2)·Σw²，`l2_gradient(weights, λ)` 返回逐元素 λ·w。

实测：权重 [0.5, -1.2, 3.0, 0.1, -2.5]，λ=0.01，惩罚=0.08475。最大权重 3.0 获得最大梯度 0.03——大权重受罚更重，这正是设计意图。

### Step 3：BatchNorm / LayerNorm / RMSNorm

同一输入 [4.71, 4.65, 4.78, 6.40] 三种归一化：
- BatchNorm：[-1.13, 0.22, -0.40, 0.89]（跨 batch 归一化）
- LayerNorm：[-0.58, -0.66, -0.49, 1.73]（mean=0, std=1）
- RMSNorm：[0.91, 0.90, 0.92, 1.23]（mean=0.99, rms=1.0）

**关键区别**：LayerNorm 强制 mean=0；RMSNorm 只管 scale 不管 centering（mean 不为零）。

### Step 4：BatchNorm 训练 vs 评估模式

训练 10 个 batch 后，running mean ≈ [2.32, 2.25, 2.31, 2.35]，running var ≈ [0.92, 0.99, 0.99, 0.91]。切换 eval 模式后，输入 [5,5,5,5] 输出 [2.80, 2.76, 2.71, 2.78]——用的是运行统计而非当前 batch 统计。

### Step 5：有无正则化的训练对比

200 个样本的 circle 数据集，hidden=16，lr=0.05，训练 300 epoch：

| 配置 | Train Acc | Test Acc | Gap |
|---|---|---|---|
| 无正则化 | 99.3% | 97.3% | 2.0% |
| Dropout p=0.3 | 96.0% | 98.0% | -2.0% |
| 权重衰减 0.01 | 96.7% | 94.0% | 2.7% |
| Dropout + 权重衰减 | 87.3% | 90.7% | -3.3% |

**关键洞察**：正则化降低了 train-test gap。Dropout + 权重衰减的组合泛化最好，即使训练准确率更低。

---

## 生产中使用

PyTorch 提供了所有这些作为模块：

```python
model = nn.Sequential(
    nn.Linear(784, 256),
    nn.BatchNorm1d(256),
    nn.ReLU(),
    nn.Dropout(0.3),
    nn.Linear(256, 128),
    nn.BatchNorm1d(128),
    nn.ReLU(),
    nn.Dropout(0.3),
    nn.Linear(128, 10),
)
model.train()  # 训练模式：dropout 开启，BatchNorm 用 batch 统计
model.eval()   # 推理模式：dropout 关闭，BatchNorm 用 running 统计
```

**`model.train()` / `model.eval()` 切换是深度学习最常见的 bug 来源之一。** 忘了 `model.eval()`，测试准确率会随机波动——因为 dropout 还在生效、BatchNorm 还在用 mini-batch 统计量。

Transformer 的模式不同：
- 用 LayerNorm 而非 BatchNorm
- Dropout p=0.1 而非 p=0.5
- Pre-LN（先归一化再进子层）比 Post-LN 更稳定

---

## 产出

`outputs/prompt-regularization-advisor.md` — 一个诊断过拟合并推荐正则化策略的 prompt。

---

## 实测纠正

本节记录实际运行中发现的与课程原文的差异或额外洞察：

1. **circle 数据集过拟合不严重**：课程描述的"99% 训练 60% 测试"场景在 200 样本 circle 数据上并未出现（无正则化时 test=97.3%），说明该数据集模式相对简单。要看到严重过拟合，需要更高维或更复杂的数据。
2. **Dropout + 权重衰减组合反而训练准确率更低**：87.3% train vs 90.7% test，gap 为负（-3.3%），说明两种正则化叠加过强，模型欠拟合了训练集。这印证了"何时用什么"的框架——不是正则化越多越好。
3. **RMSNorm 的 eps=1e-6 而非 1e-5**：代码实现中 RMSNorm 用 eps=1e-6（比 BatchNorm/LayerNorm 的 1e-5 更小），这是因为 RMSNorm 不减均值，数值稳定性更好，可以用更小的 ε。
4. **BatchNorm 的 momentum 含义**：代码中 momentum=0.1 表示 running_mean = 0.9 * old + 0.1 * new，即 10% 新数据。这与 PyTorch 默认的 momentum=0.1 一致（不是 0.9）。

---

## 关键术语

| 术语 | 通俗说法 | 实际含义 |
|---|---|---|
| Overfitting | "模型记住了数据" | 训练性能远超测试性能，说明学到了噪声而非信号 |
| Regularization | "防止过拟合" | 任何约束模型复杂度以改善泛化的技术 |
| Dropout | "随机删除神经元" | 训练时以概率 p 将神经元置零，强迫冗余表示 |
| Weight decay | "L2 惩罚" | 每步减去 λ·w，将权重向零收缩 |
| BatchNorm | "按 batch 归一化" | 跨 batch 维度用 batch 统计量归一化层输出 |
| LayerNorm | "按样本归一化" | 跨特征维度逐样本归一化，batch 无关 |
| RMSNorm | "去掉均值的 LayerNorm" | 只用 RMS 归一化，不减均值，快 10%，精度不变 |
| Early stopping | "在过拟合前停止" | 验证损失不再改善时停止训练 |
| Data augmentation | "用更少数据造更多" | 变换输入以增加有效数据集大小 |
| Generalization gap | "train-test 差距" | 训练与测试性能之差，正则化的目标是最小化它 |

---

## 参考文献

- Srivastava et al., "Dropout: A Simple Way to Prevent Neural Networks from Overfitting" (2014)
- Ioffe & Szegedy, "Batch Normalization: Accelerating Deep Network Training by Reducing Internal Covariate Shift" (2015)
- Zhang & Sennrich, "Root Mean Square Layer Normalization" (2019)
- Zhang et al., "Understanding Deep Learning Requires Rethinking Generalization" (2017)