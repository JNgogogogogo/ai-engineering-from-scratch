# Numerical Stability · 数值稳定性

> 浮点数是一个有漏洞的抽象。它会在训练中咬你一口，而你不会看到它从哪里袭来。
>
> Floating point is a leaky abstraction. It will bite you during training, and you will not see it coming.

**Type:** 构建（Build）
**Language:** Python
**Prerequisites:** Phase 1, Lessons 01-04
**Time:** 约 120 分钟

## Learning Objectives · 学习目标

- 使用减最大值技巧（max-subtraction trick）实现数值稳定的 softmax 和 log-sum-exp
- 识别浮点计算中的上溢（overflow）、下溢（underflow）与灾难性抵消（catastrophic cancellation）
- 用中心有限差分（centered finite differences）对照数值梯度来验证解析梯度
- 解释为什么训练时 bfloat16 优于 float16，以及损失缩放（loss scaling）如何防止梯度下溢

> Implement numerically stable softmax and log-sum-exp using the max-subtraction trick
> Identify overflow, underflow, and catastrophic cancellation in floating-point computations
> Verify analytical gradients against numerical gradients using centered finite differences
> Explain why bfloat16 is preferred over float16 for training and how loss scaling prevents gradient underflow

## The Problem · 问题在哪

你的模型训练了三个小时，然后 loss 变成了 NaN。你加了一行打印语句。第 9000 步时 logits 还是好的。第 9001 步它们变成了 `inf`。到第 9002 步，每个梯度都是 `nan`，训练宣告死亡。

或者：你的模型完整训练到了终点，但精度比论文声称的低 2%。你把一切都查了一遍。架构一致，超参数一致，数据一致。问题在于论文用的是 float32，而你用了 float16 却没做正确的缩放。32 位里日积月累的舍入误差悄悄吃掉了你的精度。

或者：你从零实现交叉熵损失（cross-entropy loss）。它在小的 logits 上工作正常。当 logits 超过 100 时，它返回 `inf`。softmax 上溢了，因为 `exp(100)` 超出了 float32 能表示的范围。每个 ML 框架都用一个两行的技巧处理了这件事，而你不知道这个技巧的存在。

数值稳定性（numerical stability）不是理论上的担忧。它是「一次成功的训练」和「一次悄无声息失败的训练」之间的分界线。你将来要调试的每一个严重的 ML bug，追根究底都是浮点数问题。

> Your model trains for three hours, then the loss becomes NaN. ... Or: your model trains to completion but accuracy is 2% worse than the paper claims. ... Numerical stability is not a theoretical concern. It is the difference between a training run that succeeds and one that silently fails. Every serious ML bug you will debug eventually comes down to floating point.

## The Concept · 概念

### IEEE 754: How Computers Store Real Numbers · IEEE 754：计算机如何存储实数

计算机按照 IEEE 754 标准把实数存储为浮点值。一个浮点数由三部分组成：符号位（sign bit）、指数（exponent）和尾数（mantissa，又称有效数字 significand）。

```
Float32 layout (32 bits total):
[1 sign] [8 exponent] [23 mantissa]

Value = (-1)^sign * 2^(exponent - 127) * 1.mantissa
```

尾数决定精度（有多少位有效数字），指数决定范围（一个数能有多大或多小）。

```
Format     Bits   Exponent  Mantissa  Decimal digits  Range (approx)
float64    64     11        52        ~15-16          +/- 1.8e308
float32    32     8         23        ~7-8            +/- 3.4e38
float16    16     5         10        ~3-4            +/- 65,504
bfloat16   16     8         7         ~2-3            +/- 3.4e38
```

float32 给你大约 7 位十进制精度。这意味着它能区分 1.0000001 和 1.0000002，却分不清 1.00000001 和 1.00000002。第 7 位之后，一切都是舍入噪声。

float16 给你大约 3 位精度。它能表示的最大数是 65,504。在 ML 里这个数小得令人不安——logits、梯度和激活值动不动就超过它。

bfloat16 是 Google 对 float16 范围问题的回答。它拥有与 float32 相同的 8 位指数（同样的范围，最高 3.4e38），但只有 7 位尾数（精度低于 float16）。对训练神经网络而言，范围比精度更重要，所以 bfloat16 通常胜出。

> Computers store real numbers as floating point values following the IEEE 754 standard. A float has three parts: a sign bit, an exponent, and a mantissa (significand). ... The mantissa determines precision (how many significant digits). The exponent determines range (how large or small a number can be). ... float32 gives you about 7 decimal digits of precision. ... For training neural networks, range matters more than precision, so bfloat16 usually wins.

### Why 0.1 + 0.2 != 0.3 · 为什么 0.1 + 0.2 != 0.3

数 0.1 无法用二进制浮点精确表示。在二进制里它是一个无限循环小数：

```
0.1 in binary = 0.0001100110011001100110011... (repeating forever)
```

Float32 把它截断为 23 位尾数。存储下来的值约为 0.100000001490116。类似地，0.2 被存成约 0.200000002980232。它们的和是 0.300000004470348，而不是 0.3。

```
In Python:
>>> 0.1 + 0.2
0.30000000000000004

>>> 0.1 + 0.2 == 0.3
False
```

这对 ML 很重要，因为：

1. 像 `if loss < threshold` 这样的 loss 比较可能给出错误的答案
2. 累加大量小值（几千步里的梯度更新）会偏离真实的总和
3. 如果用 `==` 比较浮点数，校验和与可复现性测试会失败

解决办法：永远不要用 `==` 比较浮点数。用 `abs(a - b) < epsilon` 或 `math.isclose()`。

> The number 0.1 cannot be represented exactly in binary floating point. ... Float32 truncates this to 23 bits of mantissa. ... The fix: never compare floats with `==`. Use `abs(a - b) < epsilon` or `math.isclose()`.

### Catastrophic Cancellation · 灾难性抵消

当你把两个几乎相等的浮点数相减时，有效数字相互抵消，剩下的舍入噪声被推上了最高有效位。

```
a = 1.0000001    (stored as 1.00000011920929 in float32)
b = 1.0000000    (stored as 1.00000000000000 in float32)

True difference:  0.0000001
Computed:         0.00000011920929

Relative error: 19.2%
```

仅仅一次减法就带来 19% 的相对误差。在 ML 里，只要你做下面这些事它就会出现：

- 计算均值很大的数据的方差：当 E[x] 很大时算 `E[x^2] - E[x]^2`
- 相减几乎相等的对数概率
- 用太小的 epsilon 计算有限差分梯度

解决办法：重排公式，避免相减两个大而几乎相等的数。算方差时用 Welford 算法，或者先对数据做中心化。处理对数概率时，全程在对数空间（log-space）里工作。

> When you subtract two nearly equal floating point numbers, the significant digits cancel and you are left with rounding noise promoted to leading digits. ... That is a 19% relative error from a single subtraction. ... The fix: rearrange formulas to avoid subtracting large, nearly equal numbers. For variance, use the Welford algorithm or center the data first. For log-probabilities, work in log-space throughout.

### Overflow and Underflow · 上溢与下溢

上溢（overflow）发生在一个结果大到无法表示的时候。下溢（underflow）发生在结果太小的时候（比最小可表示的正数还要接近零）。

```
Float32 boundaries:
  Maximum:  3.4028235e+38
  Minimum positive (normal): 1.175e-38
  Minimum positive (denorm): 1.401e-45
  Overflow:  anything > 3.4e38 becomes inf
  Underflow: anything < 1.4e-45 becomes 0.0
```

`exp()` 函数是 ML 中上溢的主要来源：

```
exp(88.7)  = 3.40e+38   (barely fits in float32)
exp(89.0)  = inf         (overflow)
exp(-87.3) = 1.18e-38   (barely above underflow)
exp(-104)  = 0.0         (underflow to zero)
```

`log()` 函数则从另一个方向出事：

```
log(0.0)   = -inf
log(-1.0)  = nan
log(1e-45) = -103.3      (fine)
log(1e-46) = -inf        (input underflowed to 0, then log(0) = -inf)
```

在 ML 里，`exp()` 出现在 softmax、sigmoid 和概率计算中；`log()` 出现在交叉熵、对数似然和 KL 散度（KL divergence）中。没有正确的技巧，`log(exp(x))` 这种组合就是一片雷区。

> Overflow happens when a result is too large to represent. Underflow happens when it is too small (closer to zero than the smallest representable positive number). ... The `exp()` function is the primary source of overflow in ML. ... In ML, `exp()` appears in softmax, sigmoid, and probability computations. `log()` appears in cross-entropy, log-likelihoods, and KL divergence. The combination `log(exp(x))` is a minefield without the right tricks.

### The Log-Sum-Exp Trick · Log-Sum-Exp 技巧

直接计算 `log(sum(exp(x_i)))` 在数值上是危险的。只要某个 `x_i` 很大，`exp(x_i)` 就会上溢。如果所有 `x_i` 都非常负，每个 `exp(x_i)` 都会下溢成零，而 `log(0)` 等于 `-inf`。

技巧：在取指数之前先减去最大值。

```
log(sum(exp(x_i))) = max(x) + log(sum(exp(x_i - max(x))))
```

它为什么成立：减去 `max(x)` 之后，最大的指数是 `exp(0) = 1`，上溢不可能发生。求和项里至少有一项是 1，所以和至少是 1，而 `log(1) = 0`，下溢到 `-inf` 也不可能发生。

证明：

```
log(sum(exp(x_i)))
= log(sum(exp(x_i - c + c)))                    (add and subtract c)
= log(sum(exp(x_i - c) * exp(c)))               (exp(a+b) = exp(a)*exp(b))
= log(exp(c) * sum(exp(x_i - c)))               (factor out exp(c))
= c + log(sum(exp(x_i - c)))                    (log(a*b) = log(a) + log(b))
```

令 `c = max(x)`，上溢就被消除了。

这个技巧在 ML 里无处不在：

- Softmax 归一化
- 交叉熵损失计算
- 序列模型中的对数概率求和
- 高斯混合（mixture of Gaussians）
- 变分推断（variational inference）

> Computing `log(sum(exp(x_i)))` directly is numerically dangerous. If any `x_i` is large, `exp(x_i)` overflows. If all `x_i` are very negative, every `exp(x_i)` underflows to zero and `log(0)` is `-inf`. ... The trick: subtract the maximum value before exponentiating. ... Why this works: after subtracting `max(x)`, the largest exponent is `exp(0) = 1`. No overflow is possible. ... Set `c = max(x)` and overflow is eliminated. ... This trick appears everywhere in ML:

### Why Softmax Needs the Max-Subtraction Trick · 为什么 Softmax 需要减最大值技巧

Softmax 把 logits 转成概率：

```
softmax(x_i) = exp(x_i) / sum(exp(x_j))
```

没有这个技巧，[100, 101, 102] 这样的 logits 会引发上溢：

```
exp(100) = 2.69e43
exp(101) = 7.31e43
exp(102) = 1.99e44
sum      = 2.99e44

These overflow float32 (max ~3.4e38)? No, 2.69e43 < 3.4e38? Actually:
exp(88.7) is already at the float32 limit.
exp(100) = inf in float32.
```

用这个技巧，减去 max(x) = 102：

```
exp(100 - 102) = exp(-2) = 0.135
exp(101 - 102) = exp(-1) = 0.368
exp(102 - 102) = exp(0)  = 1.000
sum = 1.503

softmax = [0.090, 0.245, 0.665]
```

概率一模一样，计算却安全了。这不是一个优化，这是正确性的硬性要求。

> Softmax converts logits to probabilities. ... Without the trick, logits of [100, 101, 102] cause overflow. ... With the trick, subtract max(x) = 102. ... The probabilities are identical. The computation is safe. This is not an optimization. It is a requirement for correctness.

### NaN and Inf: Detection and Prevention · NaN 与 Inf：检测与预防

`nan`（Not a Number，非数）和 `inf`（无穷大）会在计算中像病毒一样传播。梯度更新里混进一个 `nan`，权重就变成 `nan`，随后每一个输出都变成 `nan`。训练一步之内就宣告死亡。

`inf` 如何出现：

- 对大的正数取 `exp()`
- 除以零：`1.0 / 0.0`
- 累加时 `float32` 上溢

`nan` 如何出现：

- `0.0 / 0.0`
- `inf - inf`
- `inf * 0`
- 对负数取 `sqrt()`
- 对负数取 `log()`
- 任何涉及已有 `nan` 的运算

检测：

```python
import math

math.isnan(x)       # True if x is nan
math.isinf(x)       # True if x is +inf or -inf
math.isfinite(x)    # True if x is neither nan nor inf
```

预防策略：

1. 对 `exp()` 的输入做截断（clamp）：`exp(clamp(x, -80, 80))`
2. 给分母加 epsilon：`x / (y + 1e-8)`
3. 在 `log()` 里加 epsilon：`log(x + 1e-8)`
4. 使用稳定实现（log-sum-exp、稳定 softmax）
5. 用梯度裁剪（gradient clipping）防止权重爆炸
6. 调试期间每次前向传播之后检查 `nan`/`inf`

> `nan` (Not a Number) and `inf` (infinity) propagate virally through computation. One `nan` in a gradient update makes the weight `nan`, which makes every subsequent output `nan`. Training is dead within one step.

### Numerical Gradient Checking · 数值梯度检查

解析梯度（来自反向传播）可能藏着 bug。数值梯度检查（numerical gradient checking）用有限差分计算梯度来验证它们。

中心差分公式：

```
df/dx ~= (f(x + h) - f(x - h)) / (2h)
```

它的精度是 O(h^2)，远好于精度只有 O(h) 的前向差分 `(f(x+h) - f(x)) / h`。

h 的选择：太大，近似不准；太小，灾难性抵消会毁掉答案。典型取值是 `h = 1e-5` 到 `1e-7`。

检查方法：计算解析梯度与数值梯度之间的相对差。

```
relative_error = |grad_analytical - grad_numerical| / max(|grad_analytical|, |grad_numerical|, 1e-8)
```

经验法则：

- relative_error < 1e-7：完美，梯度正确
- relative_error < 1e-5：可接受，大概率正确
- relative_error > 1e-3：有问题
- relative_error > 1：梯度完全错了

实现新的层或新的损失函数时，永远要检查梯度。PyTorch 为此提供了 `torch.autograd.gradcheck()`。

> Analytical gradients (from backpropagation) can have bugs. Numerical gradient checking verifies them by computing gradients with finite differences. ... This is O(h^2) accurate, much better than the forward difference `(f(x+h) - f(x)) / h` which is only O(h). ... Choosing h: too large and the approximation is wrong. Too small and catastrophic cancellation destroys the answer. ... Always check gradients when implementing a new layer or loss function. PyTorch provides `torch.autograd.gradcheck()` for this.

### Mixed Precision Training · 混合精度训练

现代 GPU 有专用硬件（Tensor Cores），计算 float16 矩阵乘法比 float32 快 2-8 倍。混合精度训练（mixed precision training）利用的正是这一点：

```
1. Maintain float32 master copy of weights
2. Forward pass in float16 (fast)
3. Compute loss in float32 (prevents overflow)
4. Backward pass in float16 (fast)
5. Scale gradients to float32
6. Update float32 master weights
```

纯 float16 训练的问题：梯度通常非常小（1e-8 或更小）。Float16 会把低于 ~6e-8 的一切下溢成零。你的模型停止学习，因为所有梯度更新都是零。

解决办法是损失缩放（loss scaling）：

```
1. Multiply loss by a large scale factor (e.g., 1024)
2. Backward pass computes gradients of (loss * 1024)
3. All gradients are 1024x larger (pushed above float16 underflow)
4. Divide gradients by 1024 before updating weights
5. Net effect: same update, but no underflow
```

动态损失缩放（dynamic loss scaling）自动调整缩放因子。从一个大值开始（65536）。如果梯度上溢成 `inf`，就把它减半。如果连续 N 步都没有上溢，就把它翻倍。

> Modern GPUs have specialized hardware (Tensor Cores) that compute float16 matrix multiplications 2-8x faster than float32. Mixed precision training exploits this. ... The problem with pure float16 training: gradients are often very small (1e-8 or smaller). Float16 underflows anything below ~6e-8 to zero. ... The fix is loss scaling. ... Dynamic loss scaling adjusts the scale factor automatically. Start with a large value (65536). If gradients overflow to `inf`, halve it. If N steps pass without overflow, double it.

### bfloat16 vs float16: Why bfloat16 Wins for Training · bfloat16 对 float16：训练时为什么 bfloat16 胜出

```
float16:   [1 sign] [5 exponent]  [10 mantissa]
bfloat16:  [1 sign] [8 exponent]  [7 mantissa]
```

float16 精度更高（10 位尾数对 7 位），但范围有限（最大约 65,504）。bfloat16 精度更低，但范围与 float32 相同（最大约 3.4e38）。

对训练神经网络来说：

- 训练尖峰期间，激活值和 logits 经常超过 65,504。float16 会上溢；bfloat16 能处理。
- float16 需要损失缩放，bfloat16 通常不需要，因为它的范围覆盖了梯度幅度的整个区间。
- bfloat16 就是对 float32 的简单截断：砍掉尾数的低 16 位。转换毫不费力，且指数部分无损。

float16 更适合推理（inference），那里数值有界、精度更重要；bfloat16 更适合训练，那里范围更重要。这就是为什么 TPU 和现代 NVIDIA GPU（A100、H100）都有原生的 bfloat16 支持。

> float16 has more precision (10 mantissa bits vs 7) but limited range (max ~65,504). bfloat16 has less precision but the same range as float32 (max ~3.4e38). ... bfloat16 is a simple truncation of float32: drop the bottom 16 bits of the mantissa. ... float16 is preferred for inference where values are bounded and precision matters more. bfloat16 is preferred for training where range matters more. This is why TPUs and modern NVIDIA GPUs (A100, H100) have native bfloat16 support.

### Gradient Clipping · 梯度裁剪

梯度爆炸（exploding gradients）指梯度穿过很多层时呈指数增长（在 RNN、深网络和 Transformer 中很常见）。一个过大的梯度就能在一步之内污染所有权重。

两种裁剪方式：

**按值裁剪（clip by value）：**独立截断每一个梯度元素。

```
grad = clamp(grad, -max_val, max_val)
```

简单，但可能改变梯度向量的方向。

**按范数裁剪（clip by norm）：**缩放整个梯度向量，让它的范数不超过阈值。

```
if ||grad|| > max_norm:
    grad = grad * (max_norm / ||grad||)
```

保留了梯度的方向。这就是 `torch.nn.utils.clip_grad_norm_()` 做的事，也是标准选择。

典型值：Transformer 用 `max_norm=1.0`，RL 用 `max_norm=0.5`，更简单的网络用 `max_norm=5.0`。

梯度裁剪不是 hack，它是安全机制。没有它，一个离群的 batch 就能产生足以毁掉数周训练的大梯度。

> Exploding gradients happen when gradients grow exponentially through many layers (common in RNNs, deep networks, and transformers). A single large gradient can corrupt all weights in one step. ... **Clip by norm:** scale the entire gradient vector so its norm does not exceed a threshold. ... Preserves the direction of the gradient. This is what `torch.nn.utils.clip_grad_norm_()` does. It is the standard choice. ... Gradient clipping is not a hack. It is a safety mechanism. Without it, a single outlier batch can produce a gradient large enough to ruin weeks of training.

### Normalization Layers as Numerical Stabilizers · 归一化层：数值稳定器

Batch normalization、layer normalization 和 RMS normalization 通常被介绍成帮助训练收敛的正则化手段。它们同时也是数值稳定器。

没有归一化时，激活值会逐层指数式地变大或变小：

```
Layer 1: values in [0, 1]
Layer 5: values in [0, 100]
Layer 10: values in [0, 10,000]
Layer 50: values in [0, inf]
```

归一化在每一层对激活值重新中心化、重新缩放：

```
LayerNorm(x) = (x - mean(x)) / (std(x) + epsilon) * gamma + beta
```

`epsilon`（典型值 1e-5）在所有激活值完全相同时防止除以零。可学习参数 `gamma` 和 `beta` 让网络能恢复它需要的任何尺度。

这让数值在整个网络中保持在安全范围，同时防止前向传播的上溢和反向传播的梯度爆炸。

> Batch normalization, layer normalization, and RMS normalization are usually presented as regularizers that help training converge. They are also numerical stabilizers. ... Normalization recenters and rescales activations at every layer. ... This keeps values in a numerically safe range throughout the network, preventing both overflow in the forward pass and gradient explosion in the backward pass.

### Common ML Numerical Bugs · 常见 ML 数值 Bug

**Bug：训练几个 epoch 后 loss 变成 NaN。**
原因：logits 长得太大，softmax 上溢了。或者学习率太高，权重发散了。
修复：使用稳定 softmax（减最大值）、降低学习率、加梯度裁剪。

**Bug：loss 卡在 log(num_classes) 不动。**
原因：模型输出接近均匀分布的概率。通常意味着梯度在消失，或模型根本没在学习。
修复：检查数据标签是否正确，验证损失函数，检查死 ReLU（dead ReLU）。

**Bug：验证精度比预期低 1-3%。**
原因：用了混合精度却没有配好损失缩放。梯度下溢悄悄把小更新清成零。
修复：开启动态损失缩放，或者换成 bfloat16。

**Bug：某些层的梯度范数是 0.0。**
原因：死 ReLU 神经元（输入全为负），或 float16 下溢。
修复：改用 LeakyReLU 或 GELU，用梯度缩放，检查权重初始化。

**Bug：模型在一块 GPU 上正常，在另一块上结果不同。**
原因：非确定性的浮点累加顺序。GPU 的并行归约在不同硬件上以不同顺序求和，而浮点加法不满足结合律。
修复：接受微小差异（1e-6），或者设置 `torch.use_deterministic_algorithms(True)` 并接受速度损失。

**Bug：loss 计算中 `exp()` 返回 `inf`。**
原因：原始 logits 没做减最大值就直接进了 `exp()`。
修复：使用 `torch.nn.functional.log_softmax()`，它内部实现了 log-sum-exp。

**Bug：从 float32 换成 float16 后训练发散。**
原因：float16 无法表示低于 6e-8 的梯度幅度，也无法表示高于 65,504 的激活值。
修复：使用带损失缩放的混合精度（AMP），或者改用 bfloat16。

```figure
logsumexp-stability
```

> **Bug: Loss is NaN after a few epochs.** Cause: logits grew too large, softmax overflowed. ... **Bug: Validation accuracy is lower than expected by 1-3%.** Cause: mixed precision without proper loss scaling. Gradient underflow silently zeroes out small updates. ... **Bug: Model works on one GPU but gives different results on another.** Cause: non-deterministic floating point accumulation order.

## Build It · 动手造

### Step 1: Demonstrate floating point precision limits · 第 1 步：演示浮点精度极限

```python
print("=== Floating Point Precision ===")
print(f"0.1 + 0.2 = {0.1 + 0.2}")
print(f"0.1 + 0.2 == 0.3? {0.1 + 0.2 == 0.3}")
print(f"Difference: {(0.1 + 0.2) - 0.3:.2e}")
```

### Step 2: Implement naive vs stable softmax · 第 2 步：实现朴素版与稳定版 softmax

```python
import math

def softmax_naive(logits):
    exps = [math.exp(z) for z in logits]
    total = sum(exps)
    return [e / total for e in exps]

def softmax_stable(logits):
    max_logit = max(logits)
    exps = [math.exp(z - max_logit) for z in logits]
    total = sum(exps)
    return [e / total for e in exps]

safe_logits = [2.0, 1.0, 0.1]
print(f"Naive:  {softmax_naive(safe_logits)}")
print(f"Stable: {softmax_stable(safe_logits)}")

dangerous_logits = [100.0, 101.0, 102.0]
print(f"Stable: {softmax_stable(dangerous_logits)}")
# softmax_naive(dangerous_logits) would return [nan, nan, nan]
```

### Step 3: Implement stable log-sum-exp · 第 3 步：实现稳定的 log-sum-exp

```python
def logsumexp_naive(values):
    return math.log(sum(math.exp(v) for v in values))

def logsumexp_stable(values):
    c = max(values)
    return c + math.log(sum(math.exp(v - c) for v in values))

safe = [1.0, 2.0, 3.0]
print(f"Naive:  {logsumexp_naive(safe):.6f}")
print(f"Stable: {logsumexp_stable(safe):.6f}")

large = [500.0, 501.0, 502.0]
print(f"Stable: {logsumexp_stable(large):.6f}")
# logsumexp_naive(large) returns inf
```

### Step 4: Implement stable cross-entropy · 第 4 步：实现稳定的交叉熵

```python
def cross_entropy_naive(true_class, logits):
    probs = softmax_naive(logits)
    return -math.log(probs[true_class])

def cross_entropy_stable(true_class, logits):
    max_logit = max(logits)
    shifted = [z - max_logit for z in logits]
    log_sum_exp = math.log(sum(math.exp(s) for s in shifted))
    log_prob = shifted[true_class] - log_sum_exp
    return -log_prob

logits = [2.0, 5.0, 1.0]
true_class = 1
print(f"Naive:  {cross_entropy_naive(true_class, logits):.6f}")
print(f"Stable: {cross_entropy_stable(true_class, logits):.6f}")
```

### Step 5: Gradient checking · 第 5 步：梯度检查

```python
def numerical_gradient(f, x, h=1e-5):
    grad = []
    for i in range(len(x)):
        x_plus = x[:]
        x_minus = x[:]
        x_plus[i] += h
        x_minus[i] -= h
        grad.append((f(x_plus) - f(x_minus)) / (2 * h))
    return grad

def check_gradient(analytical, numerical, tolerance=1e-5):
    for i, (a, n) in enumerate(zip(analytical, numerical)):
        denom = max(abs(a), abs(n), 1e-8)
        rel_error = abs(a - n) / denom
        status = "OK" if rel_error < tolerance else "FAIL"
        print(f"  param {i}: analytical={a:.8f} numerical={n:.8f} "
              f"rel_error={rel_error:.2e} [{status}]")

def f(params):
    x, y = params
    return x**2 + 3*x*y + y**3

def f_grad(params):
    x, y = params
    return [2*x + 3*y, 3*x + 3*y**2]

point = [2.0, 1.0]
analytical = f_grad(point)
numerical = numerical_gradient(f, point)
check_gradient(analytical, numerical)
```

## Use It · 实战用法

### Mixed precision simulation · 混合精度模拟

```python
import struct

def float32_to_float16_round(x):
    packed = struct.pack('f', x)
    f32 = struct.unpack('f', packed)[0]
    packed16 = struct.pack('e', f32)
    return struct.unpack('e', packed16)[0]

def simulate_bfloat16(x):
    packed = struct.pack('f', x)
    as_int = int.from_bytes(packed, 'little')
    truncated = as_int & 0xFFFF0000
    repacked = truncated.to_bytes(4, 'little')
    return struct.unpack('f', repacked)[0]
```

### Gradient clipping · 梯度裁剪

```python
def clip_by_norm(gradients, max_norm):
    total_norm = math.sqrt(sum(g**2 for g in gradients))
    if total_norm > max_norm:
        scale = max_norm / total_norm
        return [g * scale for g in gradients]
    return gradients

grads = [10.0, 20.0, 30.0]
clipped = clip_by_norm(grads, max_norm=5.0)
print(f"Original norm: {math.sqrt(sum(g**2 for g in grads)):.2f}")
print(f"Clipped norm:  {math.sqrt(sum(g**2 for g in clipped)):.2f}")
print(f"Direction preserved: {[c/clipped[0] for c in clipped]} == {[g/grads[0] for g in grads]}")
```

### NaN/Inf detection · NaN/Inf 检测

```python
def check_tensor(name, values):
    has_nan = any(math.isnan(v) for v in values)
    has_inf = any(math.isinf(v) for v in values)
    if has_nan or has_inf:
        print(f"WARNING {name}: nan={has_nan} inf={has_inf}")
        return False
    return True

check_tensor("good", [1.0, 2.0, 3.0])
check_tensor("bad",  [1.0, float('nan'), 3.0])
check_tensor("ugly", [1.0, float('inf'), 3.0])
```

完整实现（演示了所有边界情况）见 `code/numerical.py`。

> See `code/numerical.py` for complete implementations with all edge cases demonstrated.

## Ship It · 交付

本课产出：

- `code/numerical.py`：稳定 softmax、log-sum-exp、交叉熵、梯度检查和混合精度模拟
- `outputs/prompt-numerical-debugger.md`：用于诊断训练中 NaN/Inf 与数值问题的提示词

这些稳定实现会在 Phase 3 构建训练循环时、以及 Phase 4 实现 attention 机制时再次出现。

> This lesson produces:
> - `code/numerical.py` with stable softmax, log-sum-exp, cross-entropy, gradient checking, and mixed precision simulation
> - `outputs/prompt-numerical-debugger.md` for diagnosing NaN/Inf and numerical issues in training
>
> These stable implementations reappear in Phase 3 when building the training loop and in Phase 4 when implementing attention mechanisms.

## Exercises · 练习

1. **灾难性抵消。** 用朴素公式 `E[x^2] - E[x]^2` 在 float32 下计算 [1000000.0, 1000001.0, 1000002.0] 的方差。然后用 Welford 在线算法再算一遍。把两者的误差与真实方差（0.6667）做比较。

2. **精度狩猎。** 找出 Python 里满足 `1.0 + x == 1.0` 的最小正 float32 值 `x`。这就是机器精度（machine epsilon）。验证它与 `numpy.finfo(numpy.float32).eps` 相符。

3. **Log-sum-exp 边界情况。** 用这些输入测试你的 `logsumexp_stable` 函数：(a) 所有值相等，(b) 一个值远大于其余，(c) 所有值都非常负（-1000）。验证在朴素版本失败的地方它能给出正确结果。

4. **给神经网络层做梯度检查。** 实现单个线性层 `y = Wx + b` 及其解析反向传播。用 `numerical_gradient` 验证一个 3x2 权重矩阵的正确性。

5. **损失缩放实验。** 模拟 float16 训练：生成范围在 [1e-9, 1e-3] 的随机梯度，转成 float16，测量有多大比例变成零。然后施加损失缩放（乘以 1024），转成 float16，再缩放回去，再次测量零值比例。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|----------------------|
| IEEE 754 | 「浮点标准」 | 定义二进制浮点格式、舍入规则与特殊值（inf、nan）的国际标准。每个现代 CPU 和 GPU 都实现了它。 |
| Machine epsilon（机器精度） | 「精度极限」 | 在给定浮点格式下，使 1.0 + e != 1.0 成立的最小值 e。对 float32 约为 1.19e-7。 |
| Catastrophic cancellation（灾难性抵消） | 「减法导致的精度损失」 | 两个几乎相等的浮点数相减时，有效数字相互抵消，舍入噪声主导了结果。 |
| Overflow（上溢） | 「数太大」 | 结果超过最大可表示值，变成 inf。exp(89) 会让 float32 上溢。 |
| Underflow（下溢） | 「数太小」 | 结果比最小可表示正数更接近零，变成 0.0。exp(-104) 会让 float32 下溢。 |
| Log-sum-exp trick | 「先减最大值」 | 通过提出 exp(max(x)) 来计算 log(sum(exp(x)))，防止上溢与下溢。用于 softmax、交叉熵和对数概率运算。 |
| Stable softmax（稳定 softmax） | 「不会爆炸的 softmax」 | 在取指数前先减去 max(logits)。数值结果完全相同，但不可能上溢。 |
| Gradient checking（梯度检查） | 「验证你的反向传播」 | 把反向传播得到的解析梯度与有限差分得到的数值梯度做比较，抓出实现 bug。 |
| Mixed precision（混合精度） | 「float16 前向，float32 反向」 | 对速度关键的操作用低精度浮点，对数值敏感的操作用高精度浮点。典型加速 2-3 倍。 |
| Loss scaling（损失缩放） | 「防止梯度下溢」 | 反向传播前把损失乘以一个大常数，让梯度留在 float16 可表示范围内；权重更新前再除以同一个常数。 |
| bfloat16 | 「Brain floating point」 | Google 的 16 位格式：8 位指数（与 float32 同范围）加 7 位尾数（精度低于 float16）。训练首选。 |
| Gradient clipping（梯度裁剪） | 「限制梯度范数」 | 缩放梯度向量使其范数不超过阈值。防止梯度爆炸毁掉权重。 |
| NaN | 「Not a Number（非数）」 | 由未定义运算（0/0、inf-inf、sqrt(-1)）产生的特殊浮点值。会向后续所有算术传播。 |
| Inf | 「无穷大」 | 由上溢或除以零产生的特殊浮点值。可以组合出 NaN（inf - inf、inf * 0）。 |
| Numerical gradient（数值梯度） | 「暴力求导」 | 通过计算 f(x+h) 和 f(x-h) 再除以 2h 来近似导数。慢但可靠，适合验证。 |

## Further Reading · 延伸阅读

- [What Every Computer Scientist Should Know About Floating-Point Arithmetic (Goldberg 1991)](https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html) —— 权威参考，密度高但完整
- [Mixed Precision Training (Micikevicius et al., 2018)](https://arxiv.org/abs/1710.03740) —— NVIDIA 为 float16 训练引入损失缩放的论文
- [AMP: Automatic Mixed Precision (PyTorch docs)](https://pytorch.org/docs/stable/amp.html) —— PyTorch 混合精度实战指南
- [bfloat16 format (Google Cloud TPU docs)](https://cloud.google.com/tpu/docs/bfloat16) —— Google 为什么为 TPU 选择这个格式
- [Kahan Summation (Wikipedia)](https://en.wikipedia.org/wiki/Kahan_summation_algorithm) —— 降低浮点求和舍入误差的算法
