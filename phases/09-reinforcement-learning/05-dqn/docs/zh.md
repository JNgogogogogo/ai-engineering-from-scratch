# Deep Q-Networks (DQN) · 深度 Q 网络

> 2013 年，Mnih 在原始像素上训练了一个 Q-learning 网络，在七款 Atari 游戏上击败了所有经典 RL 智能体。2015 年扩展到 49 款游戏，发表于 Nature，点燃了深度强化学习时代。DQN 就是 Q-learning 加上三个让函数逼近（function approximation）稳定下来的技巧。

> 2013: Mnih trained one Q-learning network on raw pixels, beat every classical RL agent on seven Atari games. 2015: extended to 49 games, published in Nature, sparked the deep-RL era. DQN is Q-learning plus three tricks that make function approximation stable.

**类型：** Build
**语言：** Python
**前置课程：** Phase 3 · 03（反向传播）、Phase 9 · 04（Q-learning、SARSA）
**时间：** ~75 分钟

## The Problem · 问题在哪

表格型 Q-learning（tabular Q-learning）要为每一对（状态，动作）单独存一个 Q 值。国际象棋棋盘约有 10⁴³ 个状态。一帧 Atari 画面是 210×160×3 = 100,800 个特征。表格型 RL 在几千个状态时就撑不住，几十亿个状态更想都别想。

事后看，修法显而易见：用神经网络 `Q(s, a; θ)` 替换 Q 表。但这个「事后显而易见」花了几十年。朴素的函数逼近配上 Q-learning，会在「致命三要素」（deadly triad）——函数逼近 + 自举（bootstrapping）+ 异策略（off-policy）学习——的作用下发散。Mnih 等人（2013, 2015）找出了三个让学习稳定下来的工程技巧：

1. **经验回放（experience replay）**：消除转移样本之间的相关性。
2. **目标网络（target network）**：冻结自举目标。
3. **奖励裁剪（reward clipping）**：把梯度量级归一化。

DQN 打 Atari 是第一次：用单一架构、单一超参数组合，就从原始像素解掉几十个控制问题。此后一切「深度 RL」的产物——DDQN、Rainbow、Dueling、Distributional、R2D2、Agent57——都叠在这个三技巧基座之上。

> Tabular Q-learning needs a separate Q-value for every (state, action) pair. A chess board has ~10⁴³ states. An Atari frame is 210×160×3 = 100,800 features. Tabular RL dies at thousands of states, let alone billions.
> The fix is obvious in hindsight: replace the Q-table with a neural network, `Q(s, a; θ)`. But obvious-in-hindsight took decades. Naive function approximation with Q-learning diverges under the "deadly triad" — function approximation + bootstrapping + off-policy learning.
> DQN on Atari was the first time a single architecture with a single hyperparameter set solved dozens of control problems from raw pixels. Everything "deep-RL" built since — DDQN, Rainbow, Dueling, Distributional, R2D2, Agent57 — is stacked on top of this three-trick base.

## The Concept · 概念

![DQN 训练回路：环境、回放缓冲区、在线网络、目标网络、Bellman TD 损失](../assets/dqn.svg)

**目标函数。** DQN 在神经 Q 函数上最小化单步 TD 损失：

`L(θ) = E_{(s,a,r,s')~D} [ (r + γ max_{a'} Q(s', a'; θ^-) - Q(s, a; θ))² ]`

`θ` 是在线网络（online network），每一步都由梯度下降更新。`θ^-` 是目标网络（target network），周期性地从 `θ` 复制而来（约每 10,000 步）。`D` 是存放历史转移的回放缓冲区（replay buffer）。

**三个技巧，按重要性排序：**

**经验回放。** 一个容量约 `10⁶` 条转移的环形缓冲区。每个训练步从中均匀随机采样一个 minibatch。这打破了时间相关性（相邻帧几乎一模一样），让网络能把稀有的带奖励转移反复学多次，并让相邻的梯度更新互相去相关。没有它，神经网络版的 on-policy TD 在 Atari 上会发散。

**目标网络。** 在 Bellman 方程两边用同一个网络 `Q(·; θ)`，目标就会随每次更新而移动——「追着自己的尾巴跑」。修法：保留第二个权重冻结的网络 `Q(·; θ^-)`。每 `C` 步执行一次 `θ → θ^-` 复制。这让回归目标一次就能稳定几千个梯度步。软更新 `θ^- ← τ θ + (1-τ) θ^-`（DDPG、SAC 在用）是更平滑的变体。

**奖励裁剪。** Atari 奖励的量级从 1 到 1000+ 不等。裁剪到 `{-1, 0, +1}` 让任何单个游戏都无法独占梯度。在奖励量级本身重要时这样做是错的；对只看符号的 Atari 没问题。

**Double DQN。** Hasselt（2016）修复最大化偏差：用在线网络*选择*动作，用目标网络*评估*动作。

`target = r + γ Q(s', argmax_{a'} Q(s', a'; θ); θ^-)`

即插即用的替换，一致地更好。默认就用它。

**其他改进（Rainbow，2017）：** 优先级回放（prioritized replay，多采样高 TD 误差的转移）、dueling 架构（把 `V(s)` 和优势拆成两个头）、noisy networks（把探索变成可学习的）、n-step 回报、分布式 Q（distributional Q，C51/QR-DQN）、多步自举。每项各加几个百分点；收益大致可以叠加。

```figure
f3-dqn-stability
```

> **The objective.** DQN minimizes the one-step TD loss on a neural Q-function... Experience replay: A ring buffer of `~10⁶` transitions. Each training step samples a minibatch uniformly at random. Without it, on-policy TD with a neural net diverges on Atari.
> **Target network.** The fix: keep a second network `Q(·; θ^-)` with frozen weights. Every `C` steps, copy `θ → θ^-`. This stabilizes the regression target for thousands of gradient steps at a time.
> **Reward clipping.** Clipping to `{-1, 0, +1}` stops any single game from dominating the gradient.
> **Double DQN.** Hasselt (2016) fixes maximization bias: use the online net to *select* the action, the target net to *evaluate* it. Drop-in replacement, consistently better. Use it by default.

## Build It · 动手造

这里的代码只用标准库、不依赖 numpy——我们在一个迷你连续 GridWorld 上手搓一个单隐层 MLP，每个训练步只需几微秒。算法与大规模的 Atari DQN 完全一致。

> The code here is stdlib-only numpy-free — we use a hand-rolled single-hidden-layer MLP on a tiny continuous GridWorld, so every training step runs in microseconds. The algorithm is identical to Atari DQN at scale.

### Step 1: replay buffer · 回放缓冲区

```python
class ReplayBuffer:
    def __init__(self, capacity):
        self.buf = []
        self.capacity = capacity
    def push(self, s, a, r, s_next, done):
        if len(self.buf) == self.capacity:
            self.buf.pop(0)
        self.buf.append((s, a, r, s_next, done))
    def sample(self, batch, rng):
        return rng.sample(self.buf, batch)
```

Atari 用约 50,000 的容量；我们的玩具环境 5,000 就够。

> ~50,000 capacity for Atari; 5,000 suffices for our toy env.

### Step 2: a tiny Q-network (manual MLP) · 迷你 Q 网络（手写 MLP）

```python
class QNet:
    def __init__(self, n_in, n_hidden, n_actions, rng):
        self.W1 = [[rng.gauss(0, 0.3) for _ in range(n_in)] for _ in range(n_hidden)]
        self.b1 = [0.0] * n_hidden
        self.W2 = [[rng.gauss(0, 0.3) for _ in range(n_hidden)] for _ in range(n_actions)]
        self.b2 = [0.0] * n_actions
    def forward(self, x):
        h = [max(0.0, sum(w * xi for w, xi in zip(row, x)) + b) for row, b in zip(self.W1, self.b1)]
        q = [sum(w * hi for w, hi in zip(row, h)) + b for row, b in zip(self.W2, self.b2)]
        return q, h
```

前向传播：linear → ReLU → linear。整个网络就这些。

> Forward pass: linear → ReLU → linear. That is the entire net.

### Step 3: the DQN update · DQN 更新

```python
def train_step(online, target, batch, gamma, lr):
    grads = zeros_like(online)
    for s, a, r, s_next, done in batch:
        q, h = online.forward(s)
        if done:
            y = r
        else:
            q_next, _ = target.forward(s_next)
            y = r + gamma * max(q_next)
        td_error = q[a] - y
        accumulate_grads(grads, online, s, h, a, td_error)
    apply_sgd(online, grads, lr / len(batch))
```

骨架就是第 04 课的 Q-learning，只有两点不同：(a) 我们对一个可微的 `Q(·; θ)` 做反向传播，而不是查表；(b) 目标用的是 `Q(·; θ^-)`。

> The shape is Q-learning from Lesson 04 with two differences: (a) we backprop through a differentiable `Q(·; θ)` instead of indexing a table, (b) the target uses `Q(·; θ^-)`.

### Step 4: the outer loop · 外层循环

每个 episode 里：基于 `Q(·; θ)` 按 ε-greedy 动作，把转移推进缓冲区，采一个 minibatch，走一步梯度，周期性同步 `θ^- ← θ`。模式如下：

```python
for episode in range(N):
    s = env.reset()
    while not done:
        a = epsilon_greedy(online, s, epsilon)
        s_next, r, done = env.step(s, a)
        buffer.push(s, a, r, s_next, done)
        if len(buffer) >= batch:
            train_step(online, target, buffer.sample(batch), gamma, lr)
        if steps % sync_every == 0:
            target = copy(online)
        s = s_next
```

在我们的迷你 GridWorld（16 维 one-hot 状态）上，智能体约 500 个 episode 就能学出接近最优的策略。在 Atari 上，把它放大到 2 亿帧，再加一个 CNN 特征提取器。

> For each episode, act ε-greedy on `Q(·; θ)`, push transitions into the buffer, sample a minibatch, take a gradient step, periodically sync `θ^- ← θ`.
> On our tiny GridWorld with a 16-dim one-hot state, the agent learns a near-optimal policy in ~500 episodes. On Atari, scale this to 200M frames and add a CNN feature extractor.

## Pitfalls · 常见的坑

- **致命三要素。** 函数逼近 + 异策略 + 自举可能发散。DQN 靠目标网络 + 回放来缓解；两个都别删。
- **探索。** ε 必须衰减，典型做法是在训练的前约 10% 里从 1.0 降到 0.01。早期探索不够，Q 网络会收敛进一个局部盆地。
- **高估。** 对带噪声的 Q 取 `max` 有向上的偏差。生产环境一律用 Double DQN。
- **奖励尺度。** 裁剪或归一化奖励；梯度量级与奖励量级成正比。
- **回放缓冲区冷启动。** 缓冲区攒到几千条转移之前别训练。在约 20 条样本上做早期梯度会过拟合。
- **目标网络同步频率。** 太频繁 ≈ 没有目标网络；太稀疏 ≈ 目标过时。Atari DQN 用 10,000 个环境步。经验法则：每约 1/100 训练时长同步一次。
- **观测预处理。** Atari DQN 堆叠 4 帧让状态满足马尔可夫性。任何带速度信息的环境都需要帧堆叠或循环状态。

> **Deadly triad.** Function approximation + off-policy + bootstrapping can diverge. DQN mitigates with target net + replay; do not remove either.
> **Exploration.** ε must decay, typically from 1.0 to 0.01 over the first ~10% of training. **Overestimation.** `max` over noisy Q is upward-biased. Always use Double DQN in production.
> **Target sync frequency.** Too frequent ≈ no target net; too infrequent ≈ stale targets. Atari DQN uses 10,000 env steps. Rule of thumb: sync every ~1/100 of training horizon.

## Use It · 实战用法

2026 年的今天，DQN 很少再是 state-of-the-art，但它仍是异策略（off-policy）算法的参照系：

| 任务 | 首选方法 | 为什么不用 DQN？ |
|------|------------------|--------------|
| 离散动作的 Atari 类任务 | Rainbow DQN 或 Muesli | 同一框架，技巧更多。 |
| 连续控制 | SAC / TD3（Phase 9 · 07） | DQN 没有策略网络。 |
| On-policy / 高吞吐 | PPO（Phase 9 · 08） | 没有回放缓冲区；更容易扩展。 |
| 离线 RL | CQL / IQL / Decision Transformer | 保守的 Q 目标，不会自举爆炸。 |
| 大离散动作空间（推荐系统） | 带动作嵌入的 DQN，或 IMPALA | 可行；表征很重要。 |
| LLM RL | PPO / GRPO | 序列级而非步级；损失函数不同。 |

这些思想仍然通用。回放和目标网络出现在 SAC、TD3、DDPG、SAC-X、AlphaZero 的自我对弈缓冲区以及所有离线 RL 方法里。奖励裁剪以优势归一化的形式活在 PPO 里。这套架构就是蓝图。

> In 2026, DQN is rarely state-of-the-art but remains the reference off-policy algorithm...
> The lessons still travel. Replay and target networks appear in SAC, TD3, DDPG, SAC-X, AlphaZero's self-play buffer, and every offline RL method. Reward clipping lives on as advantage normalization in PPO. The architecture is the blueprint.

## Ship It · 交付

保存为 `outputs/skill-dqn-trainer.md`：

```markdown
---
name: dqn-trainer
description: Produce a DQN training config (buffer, target sync, ε schedule, reward clipping) for a discrete-action RL task.
version: 1.0.0
phase: 9
lesson: 5
tags: [rl, dqn, deep-rl]
---

Given a discrete-action environment (observation shape, action count, horizon, reward scale), output:

1. Network. Architecture (MLP / CNN / Transformer), feature dim, depth.
2. Replay buffer. Capacity, minibatch size, warmup size.
3. Target network. Sync strategy (hard every C steps or soft τ).
4. Exploration. ε start / end / schedule length.
5. Loss. Huber vs MSE, gradient clip value, reward clipping rule.
6. Double DQN. On by default unless explicit reason to disable.

Refuse to ship a DQN with no target network, no replay buffer, or ε held at 1. Refuse continuous-action tasks (route to SAC / TD3). Flag any reward range > 10× per-step mean as needing clipping or scale normalization.
```

> Save as `outputs/skill-dqn-trainer.md`.

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。画出逐 episode 回报曲线。滑动平均要多少个 episode 才能超过 -10？
2. **中等。** 禁用目标网络（Bellman 目标两边都用在线网络）。测量训练的不稳定性——回报是震荡还是发散？
3. **困难。** 加上 Double DQN：用在线网络挑 `argmax a'`，用目标网络评估。在一个噪声奖励的 GridWorld 上，对比开与不开 Double DQN 时 1,000 个 episode 后 `Q(s_0, best_a)` 与真实 `V*(s_0)` 的偏差。

> **Easy.** Run `code/main.py`. Plot the per-episode return curve. How many episodes until the running mean exceeds -10?
> **Medium.** Disable the target network (use the online net for both sides of the Bellman target). Measure training instability — does return oscillate or diverge?
> **Hard.** Add Double DQN: use the online net to pick `argmax a'`, target net to evaluate. Compare bias of `Q(s_0, best_a)` vs true `V*(s_0)` after 1,000 episodes with vs without Double DQN on a noisy-reward GridWorld.

## Key Terms · 术语表

| Term | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| DQN | "深度 Q-learning" | 带神经 Q 函数、回放缓冲区和目标网络的 Q-learning。 |
| Experience replay | "打乱后的转移" | 环形缓冲区，每个梯度步均匀采样；让数据去相关。 |
| Target network | "冻结的自举" | 周期性复制的 Q，用在 Bellman 目标里；稳定训练。 |
| Deadly triad | "RL 为什么会发散" | 函数逼近 + 自举 + 异策略 = 没有收敛性保证。 |
| Double DQN | "修复最大化偏差" | 在线网络选动作，目标网络评估动作。 |
| Dueling DQN | "V 和 A 两个头" | 把 Q 分解为 V + A - mean(A)；输出相同，梯度流更好。 |
| Rainbow | "所有技巧一起上" | DDQN + PER + dueling + n-step + noisy + distributional 合体。 |
| PER | "优先级回放" | 按 TD 误差量级成比例地采样转移。 |

## Further Reading · 延伸阅读

- [Mnih et al. (2013). Playing Atari with Deep Reinforcement Learning](https://arxiv.org/abs/1312.5602) —— 开启深度 RL 的 2013 NeurIPS workshop 论文。
- [Mnih et al. (2015). Human-level control through deep reinforcement learning](https://www.nature.com/articles/nature14236) —— Nature 论文，49 游戏版 DQN。
- [Hasselt, Guez, Silver (2016). Deep Reinforcement Learning with Double Q-learning](https://arxiv.org/abs/1509.06461) —— DDQN。
- [Wang et al. (2016). Dueling Network Architectures](https://arxiv.org/abs/1511.06581) —— dueling DQN。
- [Hessel et al. (2018). Rainbow: Combining Improvements in Deep RL](https://arxiv.org/abs/1710.02298) —— 技巧叠加的那篇论文。
- [Sutton & Barto (2018). Ch. 9 — On-policy Prediction with Approximation](http://incompleteideas.net/book/RLbook2020.pdf) —— 教科书里对「致命三要素」（函数逼近 + 自举 + 异策略）的论述，DQN 的目标网络与回放缓冲区正是为驯服它而设计。
- [CleanRL DQN implementation](https://docs.cleanrl.dev/rl-algorithms/dqn/) —— 消融实验中使用的单文件参考 DQN；适合与本课的从零实现对照阅读。
