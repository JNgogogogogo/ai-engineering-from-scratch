# Sampling Methods · 采样方法

> 采样是 AI 探索可能性空间的方式。
>
> Sampling is how AI explores the space of possibilities.

**Type:** Build
**Language:** Python
**Prerequisites:** Phase 1, Lessons 06-07 (Probability, Bayes' Theorem)
**Time:** ~120 minutes

## Learning Objectives · 学习目标

- 只用均匀随机数，从零实现逆 CDF、拒绝采样和重要性采样（importance sampling）
- 为语言模型的 token 生成构建 temperature、top-k、top-p（nucleus）采样
- 解释重参数化技巧（reparameterization trick），以及它为什么让 VAE 中的采样可以反向传播
- 运行 Metropolis-Hastings MCMC，从一个未归一化的目标分布采样

> Implement inverse CDF, rejection, and importance sampling from scratch using only uniform random numbers
> Build temperature, top-k, and top-p (nucleus) sampling for language model token generation
> Explain the reparameterization trick and why it enables backpropagation through sampling in VAEs
> Run Metropolis-Hastings MCMC to sample from an unnormalized target distribution

## The Problem · 问题在哪

一个语言模型处理完你的提示词，产出一个 50,000 维的 logits 向量。词表里的每个 token 对应一维。现在它必须挑出一个。怎么挑？

如果它总是挑概率最高的 token，那么每个回复都一模一样：确定性、无聊。如果它均匀随机地挑，输出就是乱码。答案位于这两个极端之间的某处，而那个「某处」由采样控制。

采样不只限于文本生成。强化学习通过采样轨迹来估计策略梯度。VAE 通过从学到的分布中采样并对随机性做反向传播来学习潜在表示。扩散模型通过采样噪声并迭代去噪来生成图像。蒙特卡洛方法估计没有闭式解的积分。MCMC 算法探索根本无法枚举的高维后验分布。

每一个生成式 AI 系统都是一个采样系统。采样策略决定了输出的质量、多样性和可控性。本课从零构建每一个主流采样方法：从均匀随机数出发，一直讲到驱动现代 LLM 和生成模型的技术。

> A language model finishes processing your prompt and produces a vector of 50,000 logits. One for every token in its vocabulary. Now it has to pick one. How?
> If it always picks the highest-probability token, every response is identical. Deterministic. Boring. If it picks uniformly at random, the output is gibberish. The answer lives somewhere between these extremes, and that somewhere is controlled by sampling.
> Sampling is not limited to text generation. ... MCMC algorithms explore high-dimensional posterior distributions that are impossible to enumerate.
> Every generative AI system is a sampling system. The sampling strategy determines the quality, diversity, and controllability of the output. This lesson builds every major sampling method from scratch, starting from uniform random numbers and ending with the techniques that power modern LLMs and generative models.

## The Concept · 概念

### Why Sampling Matters · 采样为什么重要

采样在 AI 和机器学习中扮演四种基本角色：

**生成（Generation）。** 语言模型、扩散模型和 GAN 都通过采样产生输出。采样算法直接控制创造性、连贯性和多样性。Temperature、top-k 和 nucleus 采样是工程师每天拧的那几个旋钮。

**训练（Training）。** 随机梯度下降对 mini-batch 采样。Dropout 对要失活的神经元采样。数据增强对随机变换采样。重要性采样对样本重新加权，以降低强化学习（PPO、TRPO）中的梯度方差。

**估计（Estimation）。** ML 里的很多量都没有闭式解：数据分布上的期望损失、能量模型的配分函数（partition function）、贝叶斯推断中的证据（evidence）。蒙特卡洛估计通过对样本求平均来近似所有这些量。

**探索（Exploration）。** MCMC 算法探索贝叶斯推断中的后验分布。进化策略对参数扰动采样。Thompson sampling 在老虎机问题中平衡探索与利用。

核心挑战在于：你能直接采样的只有简单分布（均匀分布、正态分布）。对其他所有分布，你都需要一种方法把简单样本转换成目标分布的样本。

> Sampling appears in four fundamental roles across AI and machine learning:
> Generation. Language models, diffusion models, and GANs all produce output by sampling. ...
> The core challenge: you can only sample directly from simple distributions (uniform, normal). For everything else, you need a method to convert simple samples into samples from your target distribution.

### Uniform Random Sampling · 均匀随机采样

每一种采样方法都从这里出发。均匀随机数生成器产生 [0, 1) 区间内的值，其中任何等长的子区间都有相等的概率。

```
U ~ Uniform(0, 1)

P(a <= U <= b) = b - a    for 0 <= a <= b <= 1

Properties:
  E[U] = 0.5
  Var(U) = 1/12
```

要从 n 个离散条目里均匀采样，生成 U 然后返回 floor(n * U)。要从连续区间 [a, b] 采样，计算 a + (b - a) * U。

关键洞见：一个均匀随机数恰好含有「从任何分布产生一个样本」所需的正确数量的随机性。诀窍在于找到那个正确的变换。

> Every sampling method starts here. A uniform random number generator produces values in [0, 1) where every sub-interval of equal length has equal probability.
> To sample uniformly from a discrete set of n items, generate U and return floor(n * U). To sample from a continuous range [a, b], compute a + (b - a) * U.
> The key insight: a single uniform random number contains exactly the right amount of randomness to produce one sample from any distribution. The trick is finding the right transformation.

### Inverse CDF Method (Inverse Transform Sampling) · 逆 CDF 法（逆变换采样）

累积分布函数（CDF，cumulative distribution function）把值映射到概率：

```
F(x) = P(X <= x)

Properties:
  F is non-decreasing
  F(-inf) = 0
  F(+inf) = 1
  F maps the real line to [0, 1]
```

逆 CDF 把概率映射回值。如果 U ~ Uniform(0, 1)，那么 X = F_inverse(U) 就服从目标分布。

```
Algorithm:
  1. Generate u ~ Uniform(0, 1)
  2. Return F_inverse(u)

Why it works:
  P(X <= x) = P(F_inverse(U) <= x) = P(U <= F(x)) = F(x)
```

**指数分布的例子：**

```
PDF: f(x) = lambda * exp(-lambda * x),   x >= 0
CDF: F(x) = 1 - exp(-lambda * x)

Solve F(x) = u for x:
  u = 1 - exp(-lambda * x)
  exp(-lambda * x) = 1 - u
  x = -ln(1 - u) / lambda

Since (1 - U) and U have the same distribution:
  x = -ln(u) / lambda
```

当你能写出 F_inverse 的闭式表达式时，这个方法完美工作。对正态分布来说，逆 CDF 没有闭式解，所以我们要用别的方法（Box-Muller 变换，或数值近似）。

**离散版本：** 对离散分布，把 CDF 建成累积和，生成 U，然后找到累积和第一次超过 U 的那个下标。这就是第 06 课里 `sample_categorical` 的工作方式。

> The cumulative distribution function (CDF) maps values to probabilities:
> The inverse CDF maps probabilities back to values. If U ~ Uniform(0, 1), then X = F_inverse(U) follows the target distribution.
> This works perfectly when you can write down F_inverse in closed form. For the normal distribution, there is no closed-form inverse CDF, so we use other methods (Box-Muller, or numerical approximation).
> Discrete version: For discrete distributions, build the CDF as a cumulative sum, generate U, and find the first index where the cumulative sum exceeds U. This is how `sample_categorical` works in Lesson 06.

### Rejection Sampling · 拒绝采样

当你无法对 CDF 求逆、但能在相差一个常数的意义下求值目标 PDF 时，拒绝采样就能用。

```
Target distribution: p(x)  (can evaluate, possibly unnormalized)
Proposal distribution: q(x)  (can sample from)
Bound: M such that p(x) <= M * q(x) for all x

Algorithm:
  1. Sample x ~ q(x)
  2. Sample u ~ Uniform(0, 1)
  3. If u < p(x) / (M * q(x)), accept x
  4. Otherwise, reject and go to step 1

Acceptance rate = 1/M
```

界 M 越紧，接受率越高。在低维（1-3 维）下，拒绝采样工作得很好。在高维下，接受率指数级下降，因为提议体积的大部分都被拒绝了。这就是拒绝采样的维数灾难（curse of dimensionality）。

**例子：从截断正态分布采样。** 用截断范围上的均匀提议。包络 M 就是正态 PDF 在该范围内的最大值。

**例子：从半圆采样。** 在包围矩形内均匀提议。如果点落在半圆内就接受。蒙特卡洛就是这么算 pi 的：接受率等于面积比 pi/4。

> When you cannot invert the CDF but can evaluate the target PDF up to a constant, rejection sampling works.
> Acceptance rate = 1/M. The tighter the bound M, the higher the acceptance rate. In low dimensions (1-3), rejection sampling works well. In high dimensions, the acceptance rate drops exponentially because most of the proposal volume gets rejected. This is the curse of dimensionality for rejection sampling.

### Importance Sampling · 重要性采样

有时你并不需要目标分布 p(x) 本身的样本。你需要估计的是 p(x) 下的一个期望，而你手里是来自另一个分布 q(x) 的样本。

```
Goal: estimate E_p[f(x)] = integral of f(x) * p(x) dx

Rewrite:
  E_p[f(x)] = integral of f(x) * (p(x)/q(x)) * q(x) dx
            = E_q[f(x) * w(x)]

where w(x) = p(x) / q(x)  are the importance weights.

Estimator:
  E_p[f(x)] ~ (1/N) * sum(f(x_i) * w(x_i))    where x_i ~ q(x)
```

这在强化学习里至关重要。在 PPO（Proximal Policy Optimization）中，你用旧策略 pi_old 收集轨迹，但想优化新策略 pi_new。重要性权重就是 pi_new(a|s) / pi_old(a|s)。PPO 对这些权重做裁剪（clip），防止新策略偏离旧策略太远。

重要性采样估计量的方差取决于 q 与 p 有多相似。如果 q 与 p 差得很远，少数样本会拿到巨大的权重并主导整个估计。自归一化重要性采样（self-normalized importance sampling）通过除以权重之和来缓解这个问题：

```
E_p[f(x)] ~ sum(w_i * f(x_i)) / sum(w_i)
```

> Sometimes you do not need samples from the target distribution p(x). You need to estimate an expectation under p(x), and you have samples from a different distribution q(x).
> This is critical in reinforcement learning. In PPO (Proximal Policy Optimization), you collect trajectories under an old policy pi_old but want to optimize a new policy pi_new. The importance weight is pi_new(a|s) / pi_old(a|s). PPO clips these weights to prevent the new policy from diverging too far from the old one.
> The variance of the importance sampling estimator depends on how similar q is to p. ... Self-normalized importance sampling divides by the sum of weights to reduce this problem.

### Monte Carlo Estimation · 蒙特卡洛估计

蒙特卡洛估计通过对随机样本求平均来近似积分。大数定律保证了收敛。

```
Goal: estimate I = integral of g(x) dx over domain D

Method:
  1. Sample x_1, ..., x_N uniformly from D
  2. I ~ (Volume of D / N) * sum(g(x_i))

Error: O(1 / sqrt(N))   regardless of dimension
```

误差率与维度无关。这就是为什么在基于网格的积分无法进行的高维空间里，蒙特卡洛方法占据统治地位。

**估计 pi：**

```
Sample (x, y) uniformly from [-1, 1] x [-1, 1]
Count how many fall inside the unit circle: x^2 + y^2 <= 1
pi ~ 4 * (count inside) / (total count)
```

**估计期望：**

```
E[f(X)] ~ (1/N) * sum(f(x_i))    where x_i ~ p(x)

The sample mean converges to the true expectation.
Variance of the estimator = Var(f(X)) / N
```

> Monte Carlo estimation approximates integrals by averaging random samples. The law of large numbers guarantees convergence.
> The error rate is dimension-independent. This is why Monte Carlo methods dominate in high dimensions where grid-based integration is impossible.

### Markov Chain Monte Carlo (MCMC): Metropolis-Hastings · 马尔可夫链蒙特卡洛（MCMC）：Metropolis-Hastings

MCMC 构造一条马尔可夫链，其平稳分布（stationary distribution）就是目标分布 p(x)。经过足够多步之后，链产生的样本就（近似）是 p(x) 的样本。

```
Target: p(x)  (known up to a normalizing constant)
Proposal: q(x'|x)  (how to propose the next state given the current state)

Metropolis-Hastings algorithm:
  1. Start at some x_0
  2. For t = 1, 2, ..., T:
     a. Propose x' ~ q(x'|x_t)
     b. Compute acceptance ratio:
        alpha = [p(x') * q(x_t|x')] / [p(x_t) * q(x'|x_t)]
     c. Accept with probability min(1, alpha):
        - If u < alpha (u ~ Uniform(0,1)): x_{t+1} = x'
        - Otherwise: x_{t+1} = x_t
  3. Discard first B samples (burn-in)
  4. Return remaining samples
```

对于对称提议（q(x'|x) = q(x|x')），接受比率简化为 p(x')/p(x)。这就是最早的 Metropolis 算法。

**它为什么有效。** 接受规则保证了细致平衡（detailed balance）：处于 x 并移动到 x' 的概率等于处于 x' 并移动到 x 的概率。细致平衡意味着 p(x) 是这条链的平稳分布。

**实践要点：**
- Burn-in（预烧期）：丢弃链达到平稳之前的早期样本
- Thinning（稀疏化）：每隔 k 个样本保留一个，以降低自相关
- 提议尺度：太小则链移动缓慢（接受率高、探索慢）；太大则大多数提议被拒绝（接受率低、原地不动）
- 高维下高斯提议的最优接受率约为 0.234

> MCMC constructs a Markov chain whose stationary distribution is the target distribution p(x). After enough steps, samples from the chain are (approximately) samples from p(x).
> Why it works. The acceptance rule ensures detailed balance: the probability of being at x and moving to x' equals the probability of being at x' and moving to x. Detailed balance implies that p(x) is the stationary distribution of the chain.
> Practical considerations:
> Burn-in: discard early samples before the chain reaches equilibrium. Thinning: keep every k-th sample to reduce autocorrelation. Proposal scale: too small and the chain moves slowly (high acceptance, slow exploration); too large and most proposals are rejected (low acceptance, stuck in place). The optimal acceptance rate for a Gaussian proposal in high dimensions is approximately 0.234.

### Gibbs Sampling · Gibbs 采样

Gibbs 采样是 MCMC 在多元分布上的特例。它不是一次在所有维度上提议一步，而是每次从该变量的条件分布出发更新一个变量。

```
Target: p(x_1, x_2, ..., x_d)

Algorithm:
  For each iteration t:
    Sample x_1^{t+1} ~ p(x_1 | x_2^t, x_3^t, ..., x_d^t)
    Sample x_2^{t+1} ~ p(x_2 | x_1^{t+1}, x_3^t, ..., x_d^t)
    ...
    Sample x_d^{t+1} ~ p(x_d | x_1^{t+1}, x_2^{t+1}, ..., x_{d-1}^{t+1})
```

Gibbs 采样要求你能从每个条件分布 p(x_i | x_{-i}) 采样。对很多模型来说这很直接：
- 贝叶斯网络：条件分布直接由图结构给出
- 高斯混合：条件分布是高斯的
- Ising 模型：每个自旋的条件分布只依赖它的邻居

它的接受率永远是 1（每个提议都被接受），因为从精确条件分布采样自动满足细致平衡。

**局限。** 当变量高度相关时，Gibbs 采样混合得很慢，因为一次只更新一个变量，无法在分布中做大幅度的对角线移动。

> Gibbs sampling is a special case of MCMC for multivariate distributions. Instead of proposing a move in all dimensions at once, it updates one variable at a time from its conditional distribution.
> Gibbs sampling requires that you can sample from each conditional distribution p(x_i | x_{-i}).
> The acceptance rate is always 1 (every proposal is accepted) because sampling from the exact conditional automatically satisfies detailed balance.
> Limitation. When variables are highly correlated, Gibbs sampling mixes slowly because updating one variable at a time cannot make large diagonal moves through the distribution.

### Temperature Sampling (Used in LLMs) · 温度采样（LLM 中使用）

语言模型为词表中的每个 token 输出 logits z_1, ..., z_V。Softmax 把这些转换成概率。Temperature 在 softmax 之前对 logits 重新缩放：

```
p_i = exp(z_i / T) / sum(exp(z_j / T))

T = 1.0: standard softmax (original distribution)
T -> 0:  argmax (deterministic, always picks highest logit)
T -> inf: uniform (all tokens equally likely)
T < 1.0: sharpens the distribution (more confident, less diverse)
T > 1.0: flattens the distribution (less confident, more diverse)
```

**它为什么有效。** logits 除以小于 1 的 T 会放大 logits 之间的差异。如果 z_1 = 2、z_2 = 1，除以 T = 0.5 得到 z_1/T = 4 和 z_2/T = 2，差距变大了。经过 softmax 之后，logit 最高的 token 拿到大得多的份额。

**实践中：**
- T = 0.0：贪心解码（greedy decoding），最适合事实型问答
- T = 0.3-0.7：略带创造性，适合代码生成
- T = 0.7-1.0：平衡，适合一般对话
- T = 1.0-1.5：创意写作、头脑风暴
- T > 1.5：越来越随机，很少有用

Temperature 不会改变哪些 token 是可能的。它改变的是分配给每个 token 的概率质量。

> Language models output logits z_1, ..., z_V for each token in the vocabulary. Softmax converts these to probabilities. Temperature rescales the logits before softmax:
> Why it works. Dividing logits by T < 1 amplifies differences between logits. ... After softmax, the highest-logit token gets a much larger share.
> Temperature does not change which tokens are possible. It changes the probability mass allocated to each token.

### Top-k Sampling · Top-k 采样

Top-k 采样把候选集限制在概率最高的 k 个 token，然后重新归一化并从这个受限集合中采样。

```
Algorithm:
  1. Compute softmax probabilities for all V tokens
  2. Sort tokens by probability (descending)
  3. Keep only the top k tokens
  4. Renormalize: p_i' = p_i / sum(p_j for j in top-k)
  5. Sample from the renormalized distribution

k = 1:  greedy decoding
k = V:  no filtering (standard sampling)
k = 40: typical setting, removes long tail of unlikely tokens
```

Top-k 阻止模型选中那些存在于词表分布长尾中的极不可能 token（错字、无意义内容）。问题在于：k 是固定的，不管上下文如何。当模型很自信（某个 token 概率 95%）时，k = 40 仍然允许 39 个备选。当模型不确定（概率摊在 1000 个 token 上）时，k = 40 会把合理的选项切掉。

> Top-k sampling restricts the candidate set to the k tokens with the highest probabilities, then renormalizes and samples from that restricted set.
> Top-k prevents the model from selecting extremely unlikely tokens (typos, nonsense) that exist in the long tail of the vocabulary distribution. The problem: k is fixed regardless of context. ... When the model is uncertain (probability is spread across 1000 tokens), k = 40 cuts off plausible options.

### Top-p (Nucleus) Sampling · Top-p（Nucleus）采样

Top-p 采样动态调整候选集的大小。它不保留固定数量的 token，而是保留累积概率超过 p 的最小 token 集合。

```
Algorithm:
  1. Compute softmax probabilities for all V tokens
  2. Sort tokens by probability (descending)
  3. Find smallest k such that sum of top-k probabilities >= p
  4. Keep only those k tokens
  5. Renormalize and sample

p = 0.9:  keeps tokens covering 90% of probability mass
p = 1.0:  no filtering
p = 0.1:  very restrictive, nearly greedy
```

当模型自信时，nucleus 采样只保留少数 token（也许 2-3 个）。当模型不确定时，它保留很多（也许 200 个）。正是这种自适应行为让 nucleus 采样总体上产出比 top-k 更好的文本。

**常见组合：**
- Temperature 0.7 + top-p 0.9：不错的通用设置
- Temperature 0.0（贪心）：最适合确定性任务
- Temperature 1.0 + top-k 50：Fan 等人（2018）原始论文的设置

Top-k 和 top-p 可以组合使用。先施加 top-k，再在剩下的集合上施加 top-p。

> Top-p sampling dynamically adjusts the candidate set size. Instead of keeping a fixed number of tokens, it keeps the smallest set of tokens whose cumulative probability exceeds p.
> When the model is confident, nucleus sampling keeps few tokens (maybe 2-3). When the model is uncertain, it keeps many (maybe 200). This adaptive behavior is why nucleus sampling generally produces better text than top-k.
> Top-k and top-p can be combined. Apply top-k first, then top-p on the remaining set.

### Reparameterization Trick (Used in VAEs) · 重参数化技巧（VAE 中使用）

变分自编码器（VAE，variational autoencoder）的学习方式是：把输入编码成潜在空间中的一个分布，从这个分布采样，再把样本解码回去。问题在于：你无法穿过一个采样操作做反向传播。

```
Standard sampling (not differentiable):
  z ~ N(mu, sigma^2)

  The randomness blocks gradient flow.
  d/d_mu [sample from N(mu, sigma^2)] = ???
```

重参数化技巧（reparameterization trick）把随机性和参数分离开：

```
Reparameterized sampling:
  epsilon ~ N(0, 1)          (fixed random noise, no parameters)
  z = mu + sigma * epsilon   (deterministic function of parameters)

  Now z is a deterministic, differentiable function of mu and sigma.
  d(z)/d(mu) = 1
  d(z)/d(sigma) = epsilon

  Gradients flow through mu and sigma.
```

这之所以有效，是因为 N(mu, sigma^2) 与 mu + sigma * N(0, 1) 同分布。关键洞见：把随机性挪到一个无参数的源头（epsilon），然后把样本表达成参数的可微变换。

**在 VAE 训练循环中：**
1. 编码器为每个输入输出 mu 和 log(sigma^2)
2. 采样 epsilon ~ N(0, 1)
3. 计算 z = mu + sigma * epsilon
4. 解码 z 以重构输入
5. 穿过第 4、3、2、1 步反向传播（之所以可能，是因为第 3 步可微）

没有重参数化技巧，VAE 就无法用标准反向传播训练。这一个洞见让 VAE 变得实用。

> Variational autoencoders (VAEs) learn by encoding inputs into a distribution in latent space, sampling from that distribution, and decoding the sample back. The problem: you cannot backpropagate through a sampling operation.
> The reparameterization trick separates the randomness from the parameters.
> This works because N(mu, sigma^2) has the same distribution as mu + sigma * N(0, 1). The key insight: move the randomness to a parameter-free source (epsilon), then express the sample as a differentiable transformation of the parameters.
> Without the reparameterization trick, VAEs cannot be trained with standard backpropagation. This single insight made VAEs practical.

### Gumbel-Softmax (Differentiable Categorical Sampling) · Gumbel-Softmax（可微分类采样）

重参数化技巧适用于连续分布（高斯）。对离散的分类分布，我们需要另一种方法。Gumbel-Softmax 为分类采样提供了一个可微近似。

**Gumbel-Max 技巧（不可微）：**

```
To sample from a categorical distribution with log-probabilities log(p_1), ..., log(p_k):
  1. Sample g_i ~ Gumbel(0, 1) for each category
     (g = -log(-log(u)), where u ~ Uniform(0, 1))
  2. Return argmax(log(p_i) + g_i)

This produces exact categorical samples.
```

**Gumbel-Softmax（可微近似）：**

```
Replace the hard argmax with a soft softmax:
  y_i = exp((log(p_i) + g_i) / tau) / sum(exp((log(p_j) + g_j) / tau))

tau (temperature) controls the approximation:
  tau -> 0:  approaches a one-hot vector (hard categorical)
  tau -> inf: approaches uniform (1/k, 1/k, ..., 1/k)
  tau = 1.0: soft approximation
```

Gumbel-Softmax 产生离散样本的连续松弛。输出是一个概率向量（软 one-hot）而不是硬 one-hot。梯度穿过 softmax 流动。在训练的前向传播中，你可以使用「直通」（straight-through）估计器：前向传播用硬 argmax，反向传播用软 Gumbel-Softmax 梯度。

**应用：**
- VAE 中的离散潜变量
- 神经架构搜索（选择离散操作）
- 硬注意力机制
- 离散动作的强化学习

> The reparameterization trick works for continuous distributions (Gaussian). For discrete categorical distributions, we need a different approach. Gumbel-Softmax provides a differentiable approximation to categorical sampling.
> Gumbel-Softmax produces a continuous relaxation of a discrete sample. The output is a probability vector (soft one-hot) instead of a hard one-hot. Gradients flow through the softmax. During the forward pass in training, you can use the "straight-through" estimator: use the hard argmax for the forward pass but the soft Gumbel-Softmax gradients for the backward pass.

### Stratified Sampling · 分层采样

标准的蒙特卡洛采样可能碰巧在样本空间中留下空隙。分层采样（stratified sampling）通过把空间切成层（stratum）并在每一层中采样来强制均匀覆盖。

```
Standard Monte Carlo:
  Sample N points uniformly from [0, 1]
  Some regions may have clusters, others gaps

Stratified sampling:
  Divide [0, 1] into N equal strata: [0, 1/N), [1/N, 2/N), ..., [(N-1)/N, 1)
  Sample one point uniformly within each stratum
  x_i = (i + u_i) / N   where u_i ~ Uniform(0, 1),  i = 0, ..., N-1
```

与标准蒙特卡洛相比，分层采样的方差永远更低或相等：

```
Var(stratified) <= Var(standard Monte Carlo)

The improvement is largest when f(x) varies smoothly.
For piecewise-constant functions, stratified sampling is exact.
```

**应用：**
- 数值积分（quasi-Monte Carlo）
- 训练数据划分（保证每一折中的类别平衡）
- 带分层的 importance sampling（两种技术结合）
- NeRF（Neural Radiance Fields）沿相机光线使用分层采样

> Standard Monte Carlo sampling can leave gaps in the sample space by chance. Stratified sampling forces even coverage by dividing the space into strata and sampling from each.
> Stratified sampling always has lower or equal variance compared to standard Monte Carlo:
> Var(stratified) <= Var(standard Monte Carlo). The improvement is largest when f(x) varies smoothly. For piecewise-constant functions, stratified sampling is exact.

### Connection to Diffusion Models · 与扩散模型的联系

扩散模型通过一个采样过程生成图像。前向过程在 T 步内不断向图像添加高斯噪声，直到它变成纯噪声。反向过程学会去噪，一步一步恢复原始图像。

```
Forward process (known):
  x_t = sqrt(alpha_t) * x_{t-1} + sqrt(1 - alpha_t) * epsilon
  where epsilon ~ N(0, I)

  After T steps: x_T ~ N(0, I)  (pure noise)

Reverse process (learned):
  x_{t-1} = (1/sqrt(alpha_t)) * (x_t - (1 - alpha_t)/sqrt(1 - alpha_bar_t) * epsilon_theta(x_t, t)) + sigma_t * z
  where z ~ N(0, I)

  Each denoising step is a sampling step.
```

与本课方法的联系：
- 每个去噪步骤都在用重参数化技巧（采样噪声，施加确定性变换）
- 噪声调度 {alpha_t} 控制了一种形式的温度退火（temperature annealing）
- 训练用蒙特卡洛估计来近似 ELBO（证据下界，evidence lower bound）
- 扩散模型中的 ancestral sampling 是一条马尔可夫链（每一步只依赖当前状态）

整个图像生成过程就是迭代采样：从噪声出发，在每一步，以学到的去噪模型为条件，采样一个噪声略小的版本。

> Diffusion models generate images through a sampling process. The forward process adds Gaussian noise to an image over T steps until it becomes pure noise. The reverse process learns to denoise, recovering the original image step by step.
> The connection to the methods in this lesson:
> Each denoising step uses the reparameterization trick (sample noise, apply deterministic transform). The noise schedule {alpha_t} controls a form of temperature annealing. Training uses Monte Carlo estimation to approximate the ELBO (evidence lower bound). Ancestral sampling in diffusion models is a Markov chain (each step depends only on the current state).
> The entire image generation process is iterative sampling: start from noise, and at each step, sample a slightly less noisy version conditioned on the learned denoising model.

```figure
monte-carlo-pi
```

## Build It · 动手造

### Step 1: Uniform and inverse CDF sampling · 第 1 步：均匀采样与逆 CDF

```python
import math
import random

def sample_uniform(a, b):
    return a + (b - a) * random.random()

def sample_exponential_inverse_cdf(lam):
    u = random.random()
    return -math.log(u) / lam
```

生成 10,000 个指数分布样本，并验证均值等于 1/lambda。

> Generate 10,000 exponential samples and verify the mean is 1/lambda.

### Step 2: Rejection sampling · 第 2 步：拒绝采样

```python
def rejection_sample(target_pdf, proposal_sample, proposal_pdf, M):
    while True:
        x = proposal_sample()
        u = random.random()
        if u < target_pdf(x) / (M * proposal_pdf(x)):
            return x
```

用拒绝采样从一个截断正态分布中抽取样本。对样本做直方图来验证形状。

> Use rejection sampling to draw from a truncated normal distribution. Verify the shape by histogramming the samples.

### Step 3: Importance sampling · 第 3 步：重要性采样

```python
def importance_sampling_estimate(f, target_pdf, proposal_pdf, proposal_sample, n):
    total = 0
    for _ in range(n):
        x = proposal_sample()
        w = target_pdf(x) / proposal_pdf(x)
        total += f(x) * w
    return total / n
```

用均匀提议分布估计正态分布下的 E[X^2]。与已知答案（mu^2 + sigma^2）比较。

> Estimate E[X^2] under a normal distribution using a uniform proposal. Compare to the known answer (mu^2 + sigma^2).

### Step 4: Monte Carlo estimation of pi · 第 4 步：蒙特卡洛估算 pi

```python
def monte_carlo_pi(n):
    inside = 0
    for _ in range(n):
        x = random.uniform(-1, 1)
        y = random.uniform(-1, 1)
        if x*x + y*y <= 1:
            inside += 1
    return 4 * inside / n
```

### Step 5: Metropolis-Hastings MCMC · 第 5 步：Metropolis-Hastings MCMC

```python
def metropolis_hastings(target_log_pdf, proposal_sample, proposal_log_pdf, x0, n_samples, burn_in):
    samples = []
    x = x0
    for i in range(n_samples + burn_in):
        x_new = proposal_sample(x)
        log_alpha = (target_log_pdf(x_new) + proposal_log_pdf(x, x_new)
                     - target_log_pdf(x) - proposal_log_pdf(x_new, x))
        if math.log(random.random()) < log_alpha:
            x = x_new
        if i >= burn_in:
            samples.append(x)
    return samples
```

从一个双峰分布（两个高斯的混合）采样。可视化这条链的轨迹。

> Sample from a bimodal distribution (mixture of two Gaussians). Visualize the chain's trajectory.

### Step 6: Gibbs sampling · 第 6 步：Gibbs 采样

```python
def gibbs_sampling_2d(conditional_x_given_y, conditional_y_given_x, x0, y0, n_samples, burn_in):
    x, y = x0, y0
    samples = []
    for i in range(n_samples + burn_in):
        x = conditional_x_given_y(y)
        y = conditional_y_given_x(x)
        if i >= burn_in:
            samples.append((x, y))
    return samples
```

### Step 7: Temperature sampling · 第 7 步：温度采样

```python
def softmax(logits):
    max_l = max(logits)
    exps = [math.exp(z - max_l) for z in logits]
    total = sum(exps)
    return [e / total for e in exps]

def temperature_sample(logits, temperature):
    scaled = [z / temperature for z in logits]
    probs = softmax(scaled)
    return sample_from_probs(probs)
```

展示 temperature 如何改变一组 token logits 的输出分布。

> Show how temperature changes the output distribution for a set of token logits.

### Step 8: Top-k and top-p sampling · 第 8 步：Top-k 与 top-p 采样

```python
def top_k_sample(logits, k):
    indexed = sorted(enumerate(logits), key=lambda x: -x[1])
    top = indexed[:k]
    top_logits = [l for _, l in top]
    probs = softmax(top_logits)
    idx = sample_from_probs(probs)
    return top[idx][0]

def top_p_sample(logits, p):
    probs = softmax(logits)
    indexed = sorted(enumerate(probs), key=lambda x: -x[1])
    cumsum = 0
    selected = []
    for token_idx, prob in indexed:
        cumsum += prob
        selected.append((token_idx, prob))
        if cumsum >= p:
            break
    sel_probs = [pr for _, pr in selected]
    total = sum(sel_probs)
    sel_probs = [pr / total for pr in sel_probs]
    idx = sample_from_probs(sel_probs)
    return selected[idx][0]
```

### Step 9: Reparameterization trick · 第 9 步：重参数化技巧

```python
def reparam_sample(mu, sigma):
    epsilon = random.gauss(0, 1)
    return mu + sigma * epsilon

def reparam_gradient(mu, sigma, epsilon):
    dz_dmu = 1.0
    dz_dsigma = epsilon
    return dz_dmu, dz_dsigma
```

演示梯度能穿过重参数化采样流动，却穿不过直接采样。

> Demonstrate that gradients flow through the reparameterized sample but not through direct sampling.

### Step 10: Gumbel-Softmax · 第 10 步：Gumbel-Softmax

```python
def gumbel_sample():
    u = random.random()
    return -math.log(-math.log(u))

def gumbel_softmax(logits, temperature):
    gumbels = [math.log(p) + gumbel_sample() for p in logits]
    return softmax([g / temperature for g in gumbels])
```

展示降低 temperature 如何让输出逼近一个 one-hot 向量。

> Show how decreasing temperature makes the output approach a one-hot vector.

带全部可视化的完整实现见 `code/sampling.py`。

> Full implementations with all visualizations are in `code/sampling.py`.

## Use It · 实战用法

有了 NumPy 和 SciPy，生产级写法是这样的：

```python
import numpy as np

rng = np.random.default_rng(42)

exponential_samples = rng.exponential(scale=2.0, size=10000)
print(f"Exponential mean: {exponential_samples.mean():.4f} (expected 2.0)")

from scipy import stats
normal = stats.norm(loc=0, scale=1)
print(f"CDF at 1.96: {normal.cdf(1.96):.4f}")
print(f"Inverse CDF at 0.975: {normal.ppf(0.975):.4f}")

logits = np.array([2.0, 1.0, 0.5, 0.1, -1.0])
temperature = 0.7
scaled = logits / temperature
probs = np.exp(scaled - scaled.max()) / np.exp(scaled - scaled.max()).sum()
token = rng.choice(len(logits), p=probs)
print(f"Sampled token index: {token}")
```

大规模跑 MCMC 时，请用专门的库：
- PyMC：完整的贝叶斯建模，带 NUTS（自适应 HMC）
- emcee：集成（ensemble）MCMC 采样器
- NumPyro/JAX：GPU 加速的 MCMC

这些你都已经从零造过了。现在你知道那些库调用在背后到底做了什么。

> With NumPy and SciPy, the production versions:
> For MCMC at scale, use dedicated libraries:
> - PyMC: full Bayesian modeling with NUTS (adaptive HMC)
> - emcee: ensemble MCMC sampler
> - NumPyro/JAX: GPU-accelerated MCMC
> You built these from scratch. Now you know what the library calls are doing.

## Exercises · 练习

1. 为柯西分布（Cauchy distribution）实现逆 CDF 采样。它的 CDF 是 F(x) = 0.5 + arctan(x)/pi。生成 10,000 个样本，画出直方图并与真实 PDF 对比。注意那些重尾（远离中心的极端值）。

2. 用拒绝采样和 Uniform(0, 1) 提议从 Beta(2, 5) 分布生成样本。把被接受的样本与真实 Beta PDF 画在一起。理论接受率是多少？

3. 用蒙特卡洛方法以 1,000、10,000 和 100,000 个样本估计 sin(x) 在 0 到 pi 上的积分。比较每个规模下的误差。验证误差按 O(1/sqrt(N)) 缩放。

4. 实现 Metropolis-Hastings，从二维分布 p(x, y) 正比于 exp(-(x^2 * y^2 + x^2 + y^2 - 8*x - 8*y) / 2) 中采样。画出样本和链的轨迹。尝试不同的提议标准差。

5. 搭一个完整的文本生成演示：给定一个含 10 个词的词表及其 logits，分别用 (a) 贪心、(b) temperature=0.7、(c) top-k=3、(d) top-p=0.9 生成 20 个 token 的序列。对比 5 次运行输出的多样性。

> Implement inverse CDF sampling for the Cauchy distribution. The CDF is F(x) = 0.5 + arctan(x)/pi. Generate 10,000 samples and plot the histogram against the true PDF. Notice the heavy tails (extreme values far from center).
> Use rejection sampling to generate samples from a Beta(2, 5) distribution using a Uniform(0, 1) proposal. Plot the accepted samples against the true Beta PDF. What is the theoretical acceptance rate?
> Estimate the integral of sin(x) from 0 to pi using Monte Carlo with 1,000, 10,000, and 100,000 samples. Compare the error at each level. Verify that the error scales as O(1/sqrt(N)).
> Implement Metropolis-Hastings to sample from a 2D distribution p(x, y) proportional to exp(-(x^2 * y^2 + x^2 + y^2 - 8*x - 8*y) / 2). Plot the samples and the chain trajectory. Experiment with different proposal standard deviations.
> Build a complete text generation demo: given a vocabulary of 10 words with logits, generate sequences of 20 tokens using (a) greedy, (b) temperature=0.7, (c) top-k=3, (d) top-p=0.9. Compare the diversity of outputs across 5 runs.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|----------------------|
| 采样（Sampling） | 「随机取值」 | 按照概率分布生成值。一切生成式 AI 背后的机制 |
| 均匀分布（Uniform distribution） | 「全都等可能」 | [a, b] 中每个值的概率密度都是 1/(b-a)。一切采样方法的起点 |
| 逆 CDF（Inverse CDF） | 「概率变换」 | F_inverse(U) 把均匀样本转换成任何已知 CDF 分布的样本。精确且高效 |
| 拒绝采样（Rejection sampling） | 「提议后接受/拒绝」 | 从简单的提议分布生成，按目标/提议之比的概率接受。精确但浪费样本 |
| 重要性采样（Importance sampling） | 「给样本重新加权」 | 用来自 q(x) 的样本估计 p(x) 下的期望，每个样本按 p(x)/q(x) 加权。强化学习里 PPO 的核心 |
| 蒙特卡洛（Monte Carlo） | 「对随机样本求平均」 | 把积分近似成样本均值。误差 O(1/sqrt(N))，与维度无关 |
| MCMC | 「会收敛的随机游走」 | 构造一条平稳分布等于目标的马尔可夫链。Metropolis-Hastings 是奠基性算法 |
| Metropolis-Hastings | 「上坡必收，下坡偶收」 | 提议移动，按密度比决定接受与否。细致平衡保证收敛到目标分布 |
| Gibbs 采样（Gibbs sampling） | 「一次一个变量」 | 固定其他变量，从每个变量的条件分布更新它。接受率 100% |
| Temperature（温度） | 「自信度旋钮」 | 在 softmax 前把 logits 除以 T。T<1 变尖（更自信），T>1 变平（更多样） |
| Top-k 采样（Top-k sampling） | 「保留最好的 k 个」 | 把概率最高的 k 个 token 之外的全部置零，重新归一化，再采样。候选集大小固定 |
| Nucleus 采样（top-p） | 「保留概率大的」 | 保留累积概率超过 p 的最小 token 集合。候选集大小自适应 |
| 重参数化技巧（Reparameterization trick） | 「把随机性挪到外面」 | 写成 z = mu + sigma * epsilon，其中 epsilon ~ N(0,1)。让采样可微。VAE 训练的命脉 |
| Gumbel-Softmax | 「软分类采样」 | 用 Gumbel 噪声 + 带 temperature 的 softmax 得到分类采样的可微近似 |
| 分层采样（Stratified sampling） | 「强制覆盖」 | 把样本空间分成层，每层各采样。方差永远不高于朴素蒙特卡洛 |
| Burn-in | 「预热期」 | MCMC 链达到平稳分布之前被丢弃的初始样本 |
| 细致平衡（Detailed balance） | 「可逆性条件」 | p(x) * T(x->y) = p(y) * T(y->x)。p 成为马尔可夫链平稳分布的充分条件 |
| 扩散采样（Diffusion sampling） | 「迭代去噪」 | 从噪声出发，施加学到的去噪步骤来生成数据。每一步都是一次条件采样操作 |

## Further Reading · 延伸阅读

- [Holbrook (2023): The Metropolis-Hastings Algorithm](https://arxiv.org/abs/2304.07010) —— MCMC 基础的详细教程
- [Jang, Gu, Poole (2017): Categorical Reparameterization with Gumbel-Softmax](https://arxiv.org/abs/1611.01144) —— Gumbel-Softmax 原始论文
- [Holtzman et al. (2020): The Curious Case of Neural Text Degeneration](https://arxiv.org/abs/1904.09751) —— nucleus（top-p）采样论文
- [Kingma & Welling (2014): Auto-Encoding Variational Bayes](https://arxiv.org/abs/1312.6114) —— 引入重参数化技巧的 VAE 论文
- [Ho, Jain, Abbeel (2020): Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239) —— 把采样与图像生成连接起来的 DDPM
