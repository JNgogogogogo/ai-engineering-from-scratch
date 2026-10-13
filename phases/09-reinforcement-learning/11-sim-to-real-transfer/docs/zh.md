# Sim-to-Real Transfer · 从仿真到现实的迁移

在仿真器里训练、一上硬件就失败的策略，是一个把仿真器背下来的策略。域随机化（domain randomization）、域自适应（domain adaptation）和系统辨识（system identification）是让学到的控制器跨过「现实差距」（reality gap）的三件工具。

> A policy trained in a simulator that fails on hardware is a policy that memorized the simulator. Domain randomization, domain adaptation, and system identification are the three tools to make learned controllers cross the reality gap.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 9 · 08 (PPO), Phase 2 · 10 (Bias/Variance)
**Time:** ~45 minutes

## The Problem · 问题在哪

训练真机器人慢、危险、贵。双足机器人学会走路要几百万个训练 episode；而真实双足哪怕只摔一次都可能损坏硬件。仿真给你无限次重置、确定性的可复现、并行环境，以及零物理损耗。

但仿真器是错的。轴承的摩擦比 MuJoCo 模型大。相机有仿真器不包含的镜头畸变。电机有延迟、回差和饱和，99% 的仿真模型都把这些略过了。风、灰尘和变化的光照会摧毁一个在「无菌渲染」上训练出来的策略。**现实差距（reality gap）**——仿真分布与真实分布之间的系统性差异——是机器人 RL 部署的核心问题。

你需要一个对 sim-to-real 分布偏移*鲁棒*的策略。三条历史路线：随机化仿真器（域随机化）、用少量真实数据适配策略（域自适应 / 微调）、或者辨识真实系统的参数并让仿真与之匹配（系统辨识）。2026 年的主流配方是把三者与大规模并行仿真（Isaac Sim、Isaac Lab、GPU 上的 Mujoco MJX）结合起来。

> Training a real robot is slow, dangerous, and expensive. ... But simulators are wrong. ... The **reality gap** — systematic difference between sim distribution and real distribution — is the central problem of deployed RL for robotics. ... You need a policy that is *robust to sim-to-real distribution shift*.

## The Concept · 概念

![Three sim-to-real regimes: domain randomization, adaptation, system identification](../assets/sim-to-real.svg)

**域随机化（Domain Randomization, DR）。** Tobin et al. 2017、Peng et al. 2018。训练时，把每一个可能在真机上不一样的仿真参数都随机化：质量、摩擦系数、电机 PD 增益、传感器噪声、相机位姿、光照、纹理、接触模型。策略学到一个「今天在哪个仿真里」的条件分布，从而在整个参数范围内泛化。只要真实机器人落在训练包络之内，策略就能用。

- **好处：** 不需要真实数据。一套配方，多种机器人。
- **坏处：** 过度随机化的训练会产出一个「万能」但过于保守的策略。噪声太多 ≈ 正则化太强。

**系统辨识（System Identification, SI）。** 训练之前，先把仿真器参数拟合到真实世界的数据上。如果你能在真机上量出机械臂关节的摩擦，就把它填进仿真器，然后训练一个按这些数值工作的策略。需要接触真实系统，但能直接缩小现实差距。

- **好处：** 精确、低噪声的训练目标。
- **坏处：** 残余的模型误差对策略不可见；没被辨识出来的小效应（比如电机死区）仍会让部署翻车。

**域自适应（Domain Adaptation）。** 在仿真中训练，再用少量真实数据微调。两种流派：

- **Real2Sim2Real：** 用真实 rollout 学一个残差仿真器 `f(s, a, z) - f_sim(s, a)`，在修正后的仿真里训练。不用太多真实数据就能缩小差距。
- **观测自适应：** 训练一个策略，通过学习到的特征提取器（比如 GAN 像素到像素）把真实观测映射成类仿真观测。控制器仍然留在仿真里。

**特权学习 / 师生（teacher-student）。** Miki et al. 2022（ANYmal 四足机器人）。在仿真里训练一个能接触特权信息（真实摩擦、地形高度、IMU 漂移）的*教师*。再蒸馏出一个只看真实传感器观测的*学生*。学生学会从历史观测推断特权特征，在物理参数变化下依然鲁棒。

**大规模并行仿真。** 2024–2026。Isaac Lab、Mujoco MJX、Brax 都能在单张 GPU 上跑数千个并行机器人。带 4,096 个并行 humanoids 的 PPO 几小时就能攒出数年的经验。训练分布一宽，「现实差距」就缩小；当那 4,096 个环境各自带不同的随机化参数时，DR 几乎免费。

**2026 年真实世界配方（四足行走为例）：**

1. 大规模并行仿真，域随机化重力、摩擦、电机增益、负载。
2. 用特权信息（地形图、本体速度真值）训练教师策略。
3. 从教师蒸馏学生策略，学生只用本体感知（腿关节编码器）。
4. 可选：用真实 IMU 上的自编码器做观测自适应。
5. 部署。在 10+ 个环境中零样本工作。如果失败，用带安全约束的 PPO 做几分钟真实微调。

```figure
f3-reality-gap
```

> If the real robot falls within the training envelope, the policy works. ... Over-randomized training produces a "universal" but overly cautious policy. Too much noise ≈ too much regularization. ... Train a *teacher* in simulation that has access to privileged information. Distill a *student* that only sees real-sensor observations. ... The "reality gap" shrinks as training distribution widens; DR becomes almost free when each of those 4,096 envs has different randomized parameters.

## Build It · 动手造

本课代码是在带*噪声*转移的 GridWorld 上做域随机化的微型演示。我们训练一个在「仿真」中经历随机打滑概率的策略，然后在「真实」环境里用训练时从未见过的打滑水平评估它。这个形状直接对应 MuJoCo 到硬件的迁移。

> This lesson's code is a tiny demonstration of domain randomization on a GridWorld with *noisy* transitions. We train a policy that experiences randomized slip probabilities in "sim" and evaluate on "real" with a slip level it never saw during training. The shape maps directly to MuJoCo-to-hardware transfer.

### Step 1: parameterized sim · 参数化的仿真器

```python
def step(state, action, slip):
    if rng.random() < slip:
        action = random_perpendicular(action)
    ...
```

`slip` 是仿真器暴露的一个参数。在真实机器人上，它可以是摩擦、质量、电机增益——任何会在仿真与现实之间发生偏移的量。

> `slip` is a parameter the simulator exposes. In real robotics it could be friction, mass, motor gain — anything that shifts between sim and real.

### Step 2: train with DR · 用 DR 训练

每个 episode 开始时采样 `slip ~ Uniform[0.0, 0.4]`。用 PPO / Q-learning / 随便什么都行来训练。重复很多 episode。

> At the start of each episode, sample `slip ~ Uniform[0.0, 0.4]`. Train PPO / Q-learning / anything. Do this for many episodes.

### Step 3: evaluate zero-shot on "real" slips · 在「真实」打滑水平上零样本评估

在 `slip ∈ {0.0, 0.1, 0.2, 0.3, 0.5, 0.7}` 上评估。前四个在训练支撑集之内；`0.5` 和 `0.7` 在外。DR 训练的策略应在支撑集内保持接近最优，在支撑集外平缓退化。固定打滑训练的策略在超出训练打滑水平时会变脆。

> Evaluate on `slip ∈ {0.0, 0.1, 0.2, 0.3, 0.5, 0.7}`. The first four are within training support; `0.5` and `0.7` are outside. A DR-trained policy should stay near-optimal inside support and degrade gracefully outside. A fixed-slip-trained policy will be brittle outside its training slip.

### Step 4: compare to narrow training · 与窄分布训练对比

再只用 `slip = 0.0` 训练第二个策略。在同样的 `slip` 扫描上评估。你会看到真实打滑一旦 > 0 就出现灾难性下跌。

> Train a second policy with `slip = 0.0` only. Evaluate on the same `slip` sweep. You should see a catastrophic drop as soon as real slip > 0.

## Pitfalls · 常见陷阱

- **随机化过头。** 在 `slip ∈ [0, 0.9]` 上训练，策略会保守到永远不试最优路径。随机化范围要匹配*预期的*真实世界分布，而不是「什么都有可能发生」。
- **随机化不足。** 只在很窄的切片上训练，策略完全无法泛化。用自适应课程（Automatic Domain Randomization）：策略变强就把分布加宽。
- **辨识错参数空间。** 随机化错了地方（真实现实差距是电机延迟，你却随机化相机色调），DR 就帮不上忙。先给真机做画像（profile）。
- **特权信息泄漏。** 用全局状态（而不只是观测）来产动作的教师，可能蒸馏出一个追不上的学生。确保教师的策略在学生可用的观测历史下是可实现的。
- **sim-to-sim 迁移失败。** 如果策略对一个更难的仿真变体都不鲁棒，那对真实世界也不会鲁棒。部署前一定先在留出的仿真变体上测。
- **没有真实世界的安全包络。** 一个在仿真里能跑、在现实里「似乎能跑」的策略，没有底层安全护盾照样可能损坏硬件。在非学习的控制器里加限速、力矩限制、关节限制。

> Too much randomization. ... Match the *expected* real-world distribution, not "anything could happen." ... Randomize the wrong thing ... and DR does not help. Profile the real robot first. ... If your policy is not robust to a harder sim variant, it will not be robust to the real world either.

## Use It · 实战用法

2026 年的 sim-to-real 技术栈：

| 领域 | 技术栈 |
|--------|-------|
| 足式运动（ANYmal、Spot、人形） | Isaac Lab + DR + privileged teacher / student |
| 操作（灵巧手、抓放） | Isaac Lab + DR + DR-GAN for vision |
| 自动驾驶 | CARLA / NVIDIA DRIVE Sim + DR + real fine-tune |
| 无人机竞速 | RotorS / Flightmare + DR + online adaptation |
| 手指 / 手内操作 | OpenAI Dactyl（空前规模的 DR） |
| 工业机械臂 | MuJoCo-Warp + SI + small real fine-tune |

各尺度的控制任务，工作流是一致的：尽量把仿真拟合好，拟合不了的就随机化，训练巨大的策略，蒸馏，带着安全护盾部署。

> For control at all scales, the workflow is consistent: fit the sim as best you can, randomize what you can't fit, train enormous policies, distill, deploy with a safety shield.

## Ship It · 交付

保存为 `outputs/skill-sim2real-planner.md`：

```markdown
---
name: sim2real-planner
description: Plan a sim-to-real transfer pipeline for a given robot + task, covering DR, SI, and safety.
version: 1.0.0
phase: 9
lesson: 11
tags: [rl, sim2real, robotics, domain-randomization]
---

Given a robot platform, a task, and access to real hardware time, output:

1. Reality gap inventory. Suspected sources ranked by expected impact (contact, sensing, actuation delay, vision).
2. DR parameters. Exact list, ranges, distribution. Justify each range against real measurements.
3. SI steps. Which parameters to measure; measurement method.
4. Teacher/student split. What privileged info the teacher uses; what obs the student uses.
5. Safety envelope. Low-level limits, emergency stops, backup controller.

Refuse to deploy without (a) a zero-shot sim-variant test, (b) a safety shield, (c) a rollback plan. Flag any DR range wider than 3× measured real variability as likely over-randomized.
```

> Save as `outputs/skill-sim2real-planner.md`:

## Exercises · 练习

1. **简单。** 在固定打滑的 GridWorld（slip=0.0）上训练 Q-learning 智能体。在 slip ∈ {0.0, 0.1, 0.3, 0.5} 上评估。画出「回报 vs slip」曲线。
2. **中等。** 训练一个采样 `slip ~ Uniform[0, 0.3]` 的 DR Q-learning 智能体。在同样的扫描上评估。在 slip=0.5（分布外）处 DR 能带来多少提升？
3. **困难。** 实现一个课程：从 slip=0.0 开始，每当策略达到最优的 90% 就加宽 DR 范围。测量零样本达到 slip=0.3 所需的总环境步数，与固定 DR 基线对比。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Reality gap | 「sim-to-real 差异」 | 训练物理 / 传感与部署物理 / 传感之间的分布偏移。 |
| Domain randomization (DR) | 「在随机仿真里训练」 | 训练时随机化仿真参数，让策略泛化。 |
| System identification (SI) | 「测真机、拟合仿真」 | 估计真实物理参数；把仿真设成一致。 |
| Domain adaptation | 「在真实数据上微调」 | 仿真训练后用少量真实数据微调；可适配观测或动力学。 |
| Privileged info | 「给教师的真值」 | 只有仿真才有的信息；学生必须从观测历史里推断。 |
| Teacher/student | 「蒸馏特权 -> 可观测」 | 教师靠捷径训练；学生学会不用捷径也能模仿。 |
| ADR | 「Automatic Domain Randomization」 | 策略变强就加宽 DR 范围的课程。 |
| Real2Sim | 「用真实数据缩差距」 | 学一个残差，让仿真模仿真实 rollout。 |

## Further Reading · 延伸阅读

- [Tobin et al. (2017). Domain Randomization for Transferring Deep Neural Networks from Simulation to the Real World](https://arxiv.org/abs/1703.06907) —— DR 的开山论文（机器人视觉）。
- [Peng et al. (2018). Sim-to-Real Transfer of Robotic Control with Dynamics Randomization](https://arxiv.org/abs/1710.06537) —— 面向动力学的 DR，四足运动。
- [OpenAI et al. (2019). Solving Rubik's Cube with a Robot Hand](https://arxiv.org/abs/1910.07113) —— Dactyl，大规模 ADR。
- [Miki et al. (2022). Learning robust perceptive locomotion for quadrupedal robots in the wild](https://www.science.org/doi/10.1126/scirobotics.abk2822) —— ANYmal 的师生方案。
- [Makoviychuk et al. (2021). Isaac Gym: High Performance GPU Based Physics Simulation for Robot Learning](https://arxiv.org/abs/2108.10470) —— 支撑 2025–2026 年部署的大规模并行仿真。
- [Akkaya et al. (2019). Automatic Domain Randomization](https://arxiv.org/abs/1910.07113) —— ADR 课程方法。
- [Sutton & Barto (2018). Ch. 8 — Planning and Learning with Tabular Methods](http://incompleteideas.net/book/RLbook2020.pdf) —— Dyna 框架（用模型做规划 + rollout），现代 sim-to-real 流水线的源头。
- [Zhao, Queralta & Westerlund (2020). Sim-to-Real Transfer in Deep Reinforcement Learning for Robotics: a Survey](https://arxiv.org/abs/2009.13303) —— sim-to-real 方法的分类学，附基准结果。
