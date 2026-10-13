# RL for Games — AlphaZero, MuZero, and the LLM-Reasoning Era · 游戏强化学习——AlphaZero、MuZero 与 LLM 推理时代

1992：TD-Gammon 用纯 TD 方法击败西洋双陆棋人类冠军。2016：AlphaGo 战胜李世石。2017：AlphaZero 从零开始横扫国际象棋、将棋和围棋。2024：DeepSeek-R1 证明了同一套配方——把 PPO 换成 GRPO——在推理任务上同样有效。游戏是驱动本阶段每一次突破的基准。

> 1992: TD-Gammon beat human champions at backgammon with pure TD. 2016: AlphaGo beat Lee Sedol. 2017: AlphaZero dominated chess, shogi, and Go from scratch. 2024: DeepSeek-R1 proved the same recipe, with GRPO replacing PPO, works on reasoning. Games are the benchmark that drives every breakthrough in this phase.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 9 · 05 (DQN), Phase 9 · 08 (PPO), Phase 9 · 09 (RLHF), Phase 9 · 10 (MARL)
**Time:** ~120 minutes

## The Problem · 问题在哪

游戏具备 RL 想要的一切。干净的奖励（胜 / 负）。无限的 episode（自博弈随时重开）。完美的仿真（游戏*就是*仿真器）。离散或小型连续动作空间。迫使策略具备对抗鲁棒性的多智能体结构。

而且每个重大 RL 突破都是拿游戏来验证的。TD-Gammon（西洋双陆棋，1992）。Atari-DQN（2013）。AlphaGo（2016）。AlphaZero（2017）。OpenAI Five（Dota 2，2019）。AlphaStar（StarCraft II，2019）。MuZero（学习模型，2019）。AlphaTensor（矩阵乘法，2022）。AlphaDev（排序算法，2023）。DeepSeek-R1（数学推理，2025）——游戏 RL 技术能迁移到文本上的最新证明。

本课顶点项目用一个统一的视角审视三个里程碑架构——AlphaZero、MuZero 和 GRPO：**自博弈 + 搜索 + 策略改进**。每一个都是对前一个的推广；GRPO 尤其是把 AlphaZero 配方用到了 LLM 推理上——token 当动作，数学验证当胜利信号。

> Games have everything RL wants. Clean reward (win/loss). Infinite episodes (self-play resets). Perfect simulation (the game *is* the simulator). ... And games are how every major RL breakthrough was tested. ... This capstone surveys the three landmark architectures — AlphaZero, MuZero, and GRPO — through a single unifying lens: **self-play + search + policy improvement**.

## The Concept · 概念

![AlphaZero ↔ MuZero ↔ GRPO: same loop, different environments](../assets/rl-games.svg)

**统一循环。**

```
while True:
    trajectory = self_play(current_policy, search)     # play game against self
    policy_target = search.improved_policy(trajectory) # search improves raw policy
    policy_net.update(policy_target, value_target)     # supervised on search output
```

**AlphaZero（2017）。** Silver et al. 给定一个规则已知的游戏（国际象棋、将棋、围棋）：

- 策略-价值网络：一个塔 `f_θ(s) → (p, v)`。`p` 是合法着法上的先验。`v` 是预期对局结果。
- 蒙特卡洛树搜索（Monte Carlo Tree Search, MCTS）：每步着法都展开一棵可能后续的树。用 `(p, v)` 作先验 + 自举（bootstrap）。用 UCB（PUCT）选节点：`a* = argmax Q(s, a) + c · p(a|s) · √N(s) / (1 + N(s, a))`。
- 自博弈：智能体对自己下棋。第 `t` 步时，MCTS 的访问分布 `π_t` 成为策略训练目标。
- 损失：`L = (v - z)² - π · log p + c · ||θ||²`。`z` 是对局结果（+1 / 0 / -1）。

零人类知识。零手工启发式。一套配方，各自经过几千万盘自博弈，就精通了国际象棋、将棋和围棋。

**MuZero（2019）。** Schrittwieser et al. 去掉了「规则已知」这个前提。

- 不再依赖固定环境，而是学一个*潜空间动力学模型*（latent dynamics model）`(h, g, f)`：
  - `h(s)`：把观测编码为潜状态。
  - `g(s_latent, a)`：预测下一个潜状态 + 奖励。
  - `f(s_latent)`：预测策略先验 + 价值。
- MCTS 在*学到的潜空间*里运行。同样的搜索，同样的训练循环。
- 在围棋、国际象棋、将棋*以及* Atari 上都有效——一个算法，不懂规则。

**Stochastic MuZero（2022）。** 加入随机动力学和机会节点；扩展到西洋双陆棋一类的游戏。

**Muesli、Gumbel MuZero（2022-2024）。** 在样本效率和确定性搜索上的改进。

**GRPO（2024-2025）。** DeepSeek-R1 配方。同样的 AlphaZero 形状循环，应用到语言模型推理上：

- 「游戏」：解答一道数学 / 代码 / 推理题。「赢」= 验证器（测试用例通过、数值答案匹配）返回 1。
- 策略：LLM。动作：token。状态：提示 + 已生成的回复。
- 没有 critic（PPO 式的 V_φ）。取而代之，对每个提示从策略采样 `G` 个补全，算出各自的奖励，用**组相对优势** `A_i = (r_i - mean_r) / std_r` 作为 REINFORCE 式更新的信号。
- 对参考策略加 KL 惩罚防止漂移（同 RLHF）。
- 完整损失：

  `L_GRPO(θ) = -E_{q, {o_i}} [ (1/G) Σ_i A_i · log π_θ(o_i | q) ] + β · KL(π_θ || π_ref)`

没有奖励模型，没有 critic，没有 MCTS。组相对基线把三者全部替代。在推理基准上以一小部分算力达到甚至超过 PPO-RLHF 的质量。

**完整的 R1 配方。** DeepSeek-R1（DeepSeek 2025）一篇论文里装了两个模型：

- **R1-Zero。** 从 DeepSeek-V3 基座出发。不做 SFT。直接上 GRPO，只用两个奖励成分：*准确性奖励*（基于规则——最终答案能否解析出正确的数 / 代码是否通过单元测试）和*格式奖励*（补全是否把思维链包在 `<think>…</think>` 标签里）。几千步之后，平均回复长度从 ~100 涨到 ~10,000 token，数学基准分数爬到接近 o1-preview 的水平。模型从零学会了推理。缺点：它的思维链常常难以卒读、中英混杂、缺乏文体修饰。
- **R1。** 用四阶段流水线修 R1-Zero 的可读性问题：
  1. **冷启动 SFT。** 收集几千条格式干净的长思维链（long-CoT）示范，在基座上做监督微调。这给了一个可读的起点。
  2. **面向推理的 GRPO。** 上 GRPO，用准确性 + 格式奖励，外加一个防止语码转换（code-switching）的*语言一致性*奖励。
  3. **拒绝采样 + 第二轮 SFT。** 从 RL 检查点采样约 60 万条推理轨迹，只保留最终答案正确且思维链可读的，再混入约 20 万条非推理 SFT 样本（写作、问答、自我认知）。重新微调基座。
  4. **全谱 GRPO。** 再来一轮 RL，同时覆盖推理（基于规则的奖励）和通用对齐（有用性 / 无害性的偏好奖励）。

结果以开放权重在 AIME 和 MATH-500 上追平 o1，而且小到可以蒸馏。同一篇论文还发布了六个蒸馏出的稠密模型（Qwen-1.5B 到 Llama-70B），做法是在 R1 的推理轨迹上做 SFT——学生侧没有任何 RL。在学生的规模上，蒸馏一个强 RL 教师始终胜过从零做 RL。

**推理任务为什么用 GRPO 而不是 PPO。** DeepSeekMath 论文（2024 年 2 月）给了三个理由：(1) 不用训练价值网络，显存省一半；(2) 组基线天然能处理推理任务产生的稀疏轨迹末端奖励；(3) 逐提示归一化让优势在难度天差地别的题目之间也可比，这是 PPO 的单一 critic 做不到的。

**免搜索 vs 基于搜索。** 游戏阵营已经分叉：

- *长时程的完全信息游戏*（围棋、国际象棋）：仍然基于搜索。AlphaZero / MuZero 统治。
- *LLM 推理*：生产中还没有 MCTS；GRPO 跑完整 rollout，推理算力靠 best-of-N。过程奖励模型（PRM）暗示步级搜索可能被加回来。

```figure
f3-selfplay-ladder
```

> Zero human knowledge. Zero handcrafted heuristics. A single recipe that mastered chess, shogi, and Go after a few tens of millions of self-play games each. ... MCTS runs in the *learned latent space*. Same search, same training loop. ... No reward model, no critic, no MCTS. Group-relative baseline replaces all three. ... The model learns to reason from scratch. ... Distillation of a strong RL teacher consistently beats RL from scratch at the student's scale.

## Build It · 动手造

`code/main.py` 里的代码实现的是**微缩版 GRPO**——一个带多组采样的老虎机（bandit）。算法和在 LLM 上完全一样，只是策略和环境更简单。它教的是*损失*和*组相对优势*（group-relative advantage）——2025 年的创新点。

> The code in `code/main.py` implements **GRPO in miniature** — a bandit with multiple groups of samples. The algorithm is the same as on an LLM; only the policy and environment are simpler. It teaches the *loss* and the *group-relative advantage*, which is the 2025 innovation.

### Step 1: a tiny verifier environment · 一个微型验证器环境

```python
QUESTIONS = [
    {"prompt": "q1", "correct": 3},
    {"prompt": "q2", "correct": 1},
]

def verify(prompt_idx, answer_token):
    return 1.0 if answer_token == QUESTIONS[prompt_idx]["correct"] else 0.0
```

真实 GRPO 中，验证器跑单元测试或检查数学等式。

> In real GRPO the verifier runs unit tests or checks math equality.

### Step 2: policy: softmax over K answer tokens per prompt · 策略：对每个提示的 K 个答案 token 做 softmax

```python
def policy_probs(theta, p_idx):
    return softmax(theta[p_idx])
```

等价于 LLM 在给定提示时最后一层的输出。

> Equivalent to the final-layer output of an LLM conditioned on a prompt.

### Step 3: group sampling and group-relative advantage · 组采样与组相对优势

```python
def grpo_step(theta, p_idx, G=8, beta=0.01, lr=0.1, rng=None):
    probs = policy_probs(theta, p_idx)
    samples = [sample(probs, rng) for _ in range(G)]
    rewards = [verify(p_idx, s) for s in samples]
    mean_r = sum(rewards) / G
    std_r = stddev(rewards) + 1e-8
    advs = [(r - mean_r) / std_r for r in rewards]

    for a, A in zip(samples, advs):
        grad = onehot(a) - probs
        for i in range(len(probs)):
            theta[p_idx][i] += lr * A * grad[i]
    # KL penalty: pull theta toward reference
    for i in range(len(probs)):
        theta[p_idx][i] -= beta * (theta[p_idx][i] - reference[p_idx][i])
```

组相对优势是 DeepSeek 2024 年的技巧。不需要 critic。「基线」就是组内均值，归一化用组内标准差。

> The group-relative advantage is the 2024 DeepSeek trick. No critic needed. The "baseline" is the group mean, and normalization uses group std.

### Step 4: compare to REINFORCE baseline (value-free) · 与 REINFORCE 基线对比（无价值函数）

同样的设置、同样的算力，换成朴素 REINFORCE。GRPO 收敛更快、更稳。

> Same setup, same compute, plain REINFORCE. GRPO converges faster and more stably.

### Step 5: observe entropy and KL · 观察熵和 KL

和 RLHF 相同的诊断指标：对参考模型的平均 KL、策略熵、奖励随时间曲线。这些一旦稳定，训练就完成了。

> Same diagnostics as RLHF: mean KL to reference, policy entropy, reward-over-time. Once these stabilize, training is done.

## Pitfalls · 常见陷阱

- **通过钻验证器空子进行奖励黑客。** GRPO 继承了 RLHF 的风险：验证器有错或可被利用，LLM 就会找到那个漏洞。鲁棒的验证器（多个测试用例、形式化证明）很重要。
- **组太小。** 组基线的方差按 `1/√G` 增长。低于 `G = 4` 时优势信号噪声大；标准选择是 `G = 8` 到 `64`。
- **长度偏差。** 不同长度的 LLM 补全有不同的对数概率。按 token 数归一化，或用序列级对数概率，或截断到最大长度。
- **纯自博弈循环。** AlphaZero 式训练在一般和博弈上可能卡进支配循环。用多样化对手池缓解（联盟赛，第 10 课）。
- **搜索-策略失配。** AlphaZero 训练策略去模仿搜索的输出。如果策略网太小、表达不了搜索的分布，训练就停滞。
- **算力下限。** MuZero / AlphaZero 需要海量算力。单次消融实验常常就是几百 GPU 小时。有供学习的微缩演示（比如 Connect Four 上的 AlphaZero）。
- **验证器覆盖度。** 单元测试放过一个有 bug 的解，就会强化这个 bug。设计能抓住边界情况的验证器。

> If the verifier is wrong or exploitable, the LLM will find the exploit. ... Variance of the group baseline goes like `1/√G`. ... Unit tests that pass for a buggy solution reinforce the bug. Design verifiers that catch edge cases.

## Use It · 实战用法

2026 年的游戏 RL 版图，按领域划分：

| 领域 | 主流方法 |
|--------|-----------------|
| 双人零和棋类（围棋、国际象棋、将棋） | AlphaZero / MuZero / KataGo |
| 不完全信息牌类（扑克） | CFR + 深度学习（DeepStack、Libratus、Pluribus） |
| Atari / 像素游戏 | Muesli / MuZero / IMPALA-PPO |
| 大型多人策略游戏（Dota、StarCraft） | PPO + 自博弈 + 联盟（OpenAI Five、AlphaStar） |
| LLM 数学 / 代码推理 | GRPO（DeepSeek-R1、Qwen-RL、开源复现） |
| LLM 对齐 | DPO / RLHF-PPO（不是 GRPO；验证器是偏好而非可验证的） |
| 机器人 | PPO + DR（不算游戏 RL，但用的是同一套策略梯度工具） |
| 组合问题 | AlphaZero 变体（AlphaTensor、AlphaDev） |

这套*配方*——自博弈、搜索增强的改进、策略蒸馏——横跨文本、像素和物理控制。GRPO 是其中最年轻的实例；还会有更多。

> The *recipe* — self-play, search-augmented improvement, policy distillation — spans text, pixels, and physical control. GRPO is the youngest instance; more are coming.

## Ship It · 交付

保存为 `outputs/skill-game-rl-designer.md`：

```markdown
---
name: game-rl-designer
description: Design a game-RL or reasoning-RL training pipeline (AlphaZero / MuZero / GRPO) for a given domain.
version: 1.0.0
phase: 9
lesson: 12
tags: [rl, alphazero, muzero, grpo, self-play]
---

Given a target (perfect-info game / imperfect-info / Atari / LLM reasoning / combinatorial), output:

1. Environment fit. Known rules? Markov? Stochastic? Multi-agent? Informs AlphaZero vs MuZero vs GRPO.
2. Search strategy. MCTS (PUCT with learned prior), Gumbel-sampled, best-of-N, or none.
3. Self-play plan. Symmetric self-play / league / offline data / verifier-generated.
4. Target signal. Game outcome / verifier reward / preference / learned model. Include robustness plan.
5. Diagnostics. Win rate vs baseline, ELO curve, verifier pass rate, KL to reference.

Refuse AlphaZero on imperfect-info games (route to CFR). Refuse GRPO without a trusted verifier. Refuse any game-RL pipeline without a fixed baseline opponent set (self-play ELO is uncalibrated otherwise).
```

> Save as `outputs/skill-game-rl-designer.md`:

## Exercises · 练习

1. **简单。** 实现 `code/main.py` 里的 GRPO 老虎机。在 2 个提示 × 每个提示 4 个答案 token 上训练。用 `G=8` 在 1,000 次更新内收敛。
2. **中等。** 接入 PPO（带裁剪）和朴素 REINFORCE。在同一个老虎机上比较它们与 GRPO 的样本效率和奖励方差。
3. **困难。** 扩展到长度为 2 的「推理链」：智能体输出两个 token，验证器对这一对给奖励。测量 GRPO 如何处理两步序列上的信用分配。（提示：按*完整序列*算组优势，再传播到两个 token 位置。）

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| MCTS | 「带学习网络的树搜索」 | 蒙特卡洛树搜索；用学到的 `(p, v)` 先验做 UCB1/PUCT 选择。 |
| AlphaZero | 「自博弈 + MCTS」 | 训练策略-价值网络去匹配 MCTS 的访问次数和对局结果。 |
| MuZero | 「学习模型的 AlphaZero」 | 同样的循环，但通过学到的动力学在潜空间里运行。 |
| GRPO | 「无 critic 的 PPO」 | Group Relative Policy Optimization；REINFORCE 加组均值基线 + KL。 |
| PUCT | 「AlphaZero 的 UCB」 | `Q + c · p · √N / (1 + N_a)` —— 在价值估计与先验之间平衡。 |
| Self-play | 「智能体打过去的自己」 | 零和博弈的标准做法；训练信号对称。 |
| League play | 「基于种群的自博弈」 | 过去 + 当前 + exploiter 都可作为采样对手。 |
| Verifier reward | 「可验证 RL」 | 奖励来自确定性检查器（测试通过、答案匹配）。 |
| Process reward | 「PRM」 | 给每个推理步骤打分，而不只是最终答案。 |

## Further Reading · 延伸阅读

- [Silver et al. (2017). Mastering the game of Go without human knowledge (AlphaGo Zero)](https://www.nature.com/articles/nature24270)。
- [Silver et al. (2018). A general reinforcement learning algorithm that masters chess, shogi, and Go through self-play (AlphaZero)](https://www.science.org/doi/10.1126/science.aar6404)。
- [Schrittwieser et al. (2020). Mastering Atari, Go, chess and shogi by planning with a learned model (MuZero)](https://www.nature.com/articles/s41586-020-03051-4)。
- [Vinyals et al. (2019). Grandmaster level in StarCraft II (AlphaStar)](https://www.nature.com/articles/s41586-019-1724-z)。
- [DeepSeek-AI (2024). DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models (GRPO)](https://arxiv.org/abs/2402.03300) —— 提出 GRPO 和组相对基线的论文。
- [DeepSeek-AI (2025). DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning](https://arxiv.org/abs/2501.12948) —— 完整的四阶段 R1 配方，外加 R1-Zero 消融。
- [Brown et al. (2019). Superhuman AI for multiplayer poker (Pluribus)](https://www.science.org/doi/10.1126/science.aay2400) —— 大规模 CFR + 深度学习。
- [Tesauro (1995). Temporal Difference Learning and TD-Gammon](https://dl.acm.org/doi/10.1145/203330.203343) —— 一切的起点。
- [Hugging Face TRL — GRPOTrainer](https://huggingface.co/docs/trl/main/en/grpo_trainer) —— 用自定义奖励函数上 GRPO 的生产级参考。
- [Qwen Team (2024). Qwen2.5-Math — GRPO replication](https://github.com/QwenLM/Qwen2.5-Math) —— R1 配方在多个规模上的开源复现。
- [Sutton & Barto (2018). Ch. 17 — Frontiers of Reinforcement Learning](http://incompleteideas.net/book/RLbook2020.pdf) —— 教科书对自博弈、搜索和「设计出来的奖励」的论述，R1 把它在 LLM 规模上变成了现实。
