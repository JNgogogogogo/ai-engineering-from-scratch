# Reward Modeling & RLHF · 奖励建模与 RLHF

人类没法为「好的助手回答」手写一个奖励函数，但他们可以比较两个回答、挑出更好的那个。用这些两两比较拟合出一个奖励模型（reward model），再用强化学习让语言模型对着它优化。Christiano 2017、InstructGPT 2022——把 GPT-3 变成 ChatGPT 的正是这套配方。到 2026 年它大多已被 DPO 取代——但心智模型依然成立。

> Humans cannot write a reward function for "good assistant response," but they can compare two responses and pick the better one. Fit a reward model to those comparisons, then RL the language model against it. Christiano 2017. InstructGPT 2022. The recipe that turned GPT-3 into ChatGPT. In 2026 it is mostly being replaced by DPO — but the mental model stays.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 05 (Sentiment), Phase 9 · 08 (PPO)
**Time:** ~45 minutes

## The Problem · 问题在哪

你用「下一词预测」目标训练了一个语言模型。它能写出合乎语法的英文，但也会撒谎、东拉西扯、该拒绝时不拒绝。靠更多预训练修不好这个问题——网络文本是病根，不是药。

你想要一个*标量奖励*来表达「对指令 X，回答 A 比回答 B 更好」。手工写这个奖励函数是不可能的：「有用性」不是关于 token 的闭式表达式。但人类可以比较两个输出并标出偏好——这种数据收集成本低，还能规模化。

人类反馈强化学习（RLHF，Christiano et al. 2017；Ouyang et al. 2022）把偏好变成一个奖励模型，再用 PPO 对着这个奖励优化语言模型。三步走：SFT → RM → PPO。2023–2025 年上线的 ChatGPT、Claude、Gemini 以及所有对齐 LLM，用的都是这套配方。

到 2026 年，PPO 这一步大多已被 DPO（Phase 10 · 08）取代——更便宜，对齐微调的效果也几乎一样好。但*奖励模型*这一块仍然支撑着每一个 Best-of-N 采样器、每一条从可验证奖励做 RL 的流水线、以及每个使用过程奖励模型（process reward model）的推理模型。懂了 RLHF，你就懂了整个对齐技术栈。

> You trained a language model on the next-token-prediction objective. It writes grammatical English. It also lies, rambles, and refuses to refuse. You cannot fix this with more pretraining — web text is the problem, not the cure. ... RLHF (Christiano et al. 2017; Ouyang et al. 2022) converts preferences into a reward model, then optimizes the LM via PPO against that reward. In three steps: SFT → RM → PPO. ... Understand RLHF and you understand the entire alignment stack.

## The Concept · 概念

![Three-stage RLHF: SFT, RM training on pairwise prefs, PPO with KL penalty](../assets/rlhf.svg)

**阶段 1：监督微调（Supervised Fine-Tuning, SFT）。** 从预训练基座模型出发。在人类撰写的目标行为示范（遵循指令的回答、有帮助的回复等）上微调。结果：得到一个模型 `π_SFT`，它*偏向良好行为*，但动作空间仍然无界。

**阶段 2：奖励模型（Reward Model）训练。**

- 针对提示 `x` 收集回复对 `(y_+, y_-)`，由人类标注「y_+ 优于 y_-」。
- 训练奖励模型 `R_φ(x, y)`，让它给 `y_+` 打更高的分。
- 损失：**Bradley-Terry 成对 logistic 损失**：

  `L(φ) = -E[ log σ(R_φ(x, y_+) - R_φ(x, y_-)) ]`

  σ 是 sigmoid 函数。奖励的差值决定偏好的对数几率（log-odds）。Bradley-Terry 自 1952 年起就是标准方法（Bradley-Terry），也是现代 RLHF 的主流选择。

- `R_φ` 通常从 SFT 模型初始化，顶上加一个标量输出头：同一个 transformer 骨干，一个线性层输出奖励。

**阶段 3：对着 RM 跑 PPO，外加 KL 惩罚。**

- 从 `π_SFT` 初始化可训练策略 `π_θ`；另存一份冻结的*参考*模型 `π_ref = π_SFT`。
- 回复 `y` 结束时拿到的奖励：

  `r_total(x, y) = R_φ(x, y) - β · KL(π_θ(·|x) || π_ref(·|x))`

  KL 惩罚防止 `π_θ` 任意漂离 `π_SFT`——它是*正则化器*，不是硬性信任域。`β` 典型取 `0.01`-`0.05`。
- 用这个奖励跑 PPO（第 08 课）。优势在 token 级轨迹上计算，但 RM 只对完整回复打一次分。

**为什么要 KL？** 没有 KL，PPO 会乐呵呵地找到「奖励黑客」（reward hacking）策略——RM 只在分布内补全上训练过，一个分布外的回复可能比任何人类写的得分都高。KL 把 `π_θ` 摁在 RM 训练时所处的流形附近。它是 RLHF 里最重要的单一旋钮。

**2026 年现状：**

- **DPO**（Rafailov 2023）：用闭式代数把阶段 2+3 折叠成一个针对偏好数据的监督损失。没有 RM，没有 PPO。在对齐基准上用一小部分算力达到同等质量。见 Phase 10 · 08。
- **GRPO**（DeepSeek 2024–2025）：PPO 去掉 critic、换上组相对基线（group-relative baseline），奖励来自*验证器*（代码跑得通 / 数学答案对得上）而不是人类训练的 RM。推理模型的主流选择。见 Phase 9 · 12。
- **过程奖励模型（process reward models, PRMs）：** 给部分解答（每一步推理）打分，在 RLHF 和 GRPO 的推理变体里都有使用。
- **Constitutional AI / RLAIF：** 用一个对齐过的 LLM 代替人类来生成偏好，把偏好预算规模化。

```figure
reward-model
```

> Start from a pretrained base model. Fine-tune on human-written demonstrations of the target behavior. ... The KL penalty prevents `π_θ` from drifting arbitrarily from `π_SFT` — it is a *regularizer*, not a hard trust region. ... Without it, PPO will happily find reward-hacking strategies — the RM was only trained on in-distribution completions. ... The KL keeps `π_θ` near the manifold where the RM was trained. It is the single most important knob in RLHF.

## Build It · 动手造

本课用字符串表示的微型合成「提示」（prompt）和「回复」（response）。RM 是词袋（bag-of-tokens）表示上的线性打分器。没有真实 LLM——要紧的是流水线的*形状*，不是规模。见 `code/main.py`。

> This lesson uses tiny synthetic "prompts" and "responses" represented as strings. The RM is a linear scorer over a bag-of-tokens representation. No real LLM — the *shape* of the pipeline matters, not the scale. See `code/main.py`.

### Step 1: synthetic preference data · 合成偏好数据

```python
PROMPTS = ["help me", "answer me", "explain this"]
GOOD_WORDS = {"clear", "specific", "kind", "thorough"}
BAD_WORDS = {"vague", "rude", "wrong", "short"}

def make_pair(rng):
    x = rng.choice(PROMPTS)
    y_good = rng.choice(list(GOOD_WORDS)) + " " + rng.choice(list(GOOD_WORDS))
    y_bad = rng.choice(list(BAD_WORDS)) + " " + rng.choice(list(BAD_WORDS))
    return (x, y_good, y_bad)
```

真实 RLHF 里这一步由人类标注员完成。数据形状——`(prompt, preferred_response, rejected_response)`——完全一致。

> In real RLHF this is replaced by human labelers. The shape — `(prompt, preferred_response, rejected_response)` — is identical.

### Step 2: Bradley-Terry reward model · Bradley-Terry 奖励模型

线性打分：`R(x, y) = w · bag(y)`。训练目标是最小化 BT 成对 log 损失：

```python
def rm_train_step(w, x, y_pos, y_neg, lr):
    r_pos = dot(w, bag(y_pos))
    r_neg = dot(w, bag(y_neg))
    p = sigmoid(r_pos - r_neg)
    for tok, cnt in bag(y_pos).items():
        w[tok] += lr * (1 - p) * cnt
    for tok, cnt in bag(y_neg).items():
        w[tok] -= lr * (1 - p) * cnt
```

几百次更新之后，`w` 会给好词 token 分配正权重、给坏词分配负权重。

> Linear score: `R(x, y) = w · bag(y)`. Train to minimize the BT pairwise log-loss. ... After a few hundred updates, `w` assigns positive weights to good-word tokens and negative to bad.

### Step 3: PPO-like policy on top of RM · 架在 RM 上的类 PPO 策略

我们的玩具策略从词表中产出一个 token。我们用 RM 给这个 token 打分，计算 `log π_θ(token | prompt)`，加上对参考模型的 KL 惩罚，再应用带裁剪的 PPO 代理目标。

```python
def rlhf_step(theta, ref, w, prompt, rng, eps=0.2, beta=0.1, lr=0.05):
    logits_theta = policy_logits(theta, prompt)
    probs = softmax(logits_theta)
    token = sample(probs, rng)
    logits_ref = policy_logits(ref, prompt)
    probs_ref = softmax(logits_ref)
    reward = dot(w, bag([token])) - beta * kl(probs, probs_ref)
    # ppo-style update on theta, treating reward as the return
    ...
```

> Our toy policy produces a single token from a vocabulary. We score the token under the RM, compute `log π_θ(token | prompt)`, add a KL-to-reference penalty, and apply the clipped PPO surrogate.

### Step 4: monitor the KL · 监控 KL

每次更新都跟踪平均 `KL(π_θ || π_ref)`。如果它悄悄爬过 `~5-10`，说明策略已经漂离 `π_SFT` 很远——要么 `β` 调得太低、漂移在加剧，要么奖励黑客已经开场。这是真实 RLHF 中的头号诊断指标。

> Track mean `KL(π_θ || π_ref)` every update. If it creeps past `~5-10` the policy has drifted far from `π_SFT` — lower `β` is rising or reward hacking is starting. This is the top diagnostic in real RLHF.

### Step 5: the production recipe with TRL · 用 TRL 写出生产级配方

理解了玩具流水线之后，看看真实的库使用者怎么写同一个循环。Hugging Face 的 [TRL](https://huggingface.co/docs/trl) 是参考实现——阶段 2 用 `RewardTrainer`，阶段 3 用 `PPOTrainer`（内置对参考模型的 KL）。

```python
# Stage 2: reward model from pairwise preferences
from trl import RewardTrainer, RewardConfig
from transformers import AutoModelForSequenceClassification, AutoTokenizer

tok = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")
rm = AutoModelForSequenceClassification.from_pretrained(
    "meta-llama/Llama-3.1-8B-Instruct", num_labels=1
)

# dataset rows: {"prompt", "chosen", "rejected"} — Bradley-Terry format
trainer = RewardTrainer(
    model=rm,
    tokenizer=tok,
    train_dataset=preference_data,
    args=RewardConfig(output_dir="./rm", num_train_epochs=1, learning_rate=1e-5),
)
trainer.train()
```

```python
# Stage 3: PPO against the RM with KL penalty to the SFT reference
from trl import PPOTrainer, PPOConfig, AutoModelForCausalLMWithValueHead

policy = AutoModelForCausalLMWithValueHead.from_pretrained("./sft-checkpoint")
ref    = AutoModelForCausalLMWithValueHead.from_pretrained("./sft-checkpoint")  # frozen

ppo = PPOTrainer(
    config=PPOConfig(learning_rate=1.41e-5, batch_size=64, init_kl_coef=0.05,
                     target_kl=6.0, adap_kl_ctrl=True),
    model=policy, ref_model=ref, tokenizer=tok,
)

for batch in dataloader:
    responses = ppo.generate(batch["query_ids"], max_new_tokens=128)
    rewards   = rm(torch.cat([batch["query_ids"], responses], dim=-1)).logits[:, 0]
    stats     = ppo.step(batch["query_ids"], responses, rewards)
    # stats includes: mean_kl, clip_frac, value_loss — the three PPO diagnostics
```

库替你做了三件事。`adap_kl_ctrl=True` 实现自适应 β 调度：观测 KL 超过 `target_kl` 时 β 翻倍，低于其一半时 β 减半。参考模型按惯例是冻结的——你绝不能让它和 `policy` 意外共享参数。价值头与策略共用同一个骨干（`AutoModelForCausalLMWithValueHead` 会附加一个标量 MLP 头），这正是 TRL 把 `policy/kl` 和 `value/loss` 分开上报的原因。

> Three things the library does for you. `adap_kl_ctrl=True` implements the adaptive-β schedule: if observed KL exceeds `target_kl`, β doubles; if below half, β halves. The reference model is frozen by convention — you must not accidentally share parameters with `policy`. And the value head lives on the same backbone as the policy (`AutoModelForCausalLMWithValueHead` attaches a scalar MLP head), which is why TRL reports `policy/kl` and `value/loss` separately.

## Pitfalls · 常见陷阱

- **过度优化 / 奖励黑客。** RM 并不完美；`π_θ` 会找到得分很高但实际很差的对抗性补全。症状：奖励持续上涨，而人类评估分数持平甚至下降。对策：提前停止、调高 `β`、扩充 RM 训练数据。
- **长度黑客。** 在「有帮助的回答」上训练的 RM 往往隐式奖励长度，策略学会给回答灌水。补救：长度归一化的奖励，或者用带长度感知 RM 的 RLAIF。
- **RM 太小。** RM 至少要和策略一样大。太小的 RM 无法忠实地给策略的输出打分。
- **KL 调参。** `β` 太低 → 漂移和奖励黑客；`β` 太高 → 策略几乎不变。标准技巧是用*自适应* β，把每步 KL 锁定在目标值。
- **偏好数据噪声。** 人类标注里约 30% 是噪声或含糊的。用一致性过滤后的数据训练 RM 来校准，或者给 BT 加温度。
- **离策略问题。** 第一个 epoch 之后，PPO 数据就轻微离策略（off-policy）了。像第 08 课那样监控裁剪比例（clip fraction）。

> The RM is imperfect; `π_θ` finds adversarial completions that score high but are bad. Symptoms: reward climbs indefinitely while human eval score plateaus or drops. ... KL tuning. Too low β → drift and reward hacking. Too high β → policy barely changes. The standard trick is an *adaptive* β that targets a fixed KL per step.

## Use It · 实战用法

2026 年的 RLHF 是分层的：

| 层面 | 目标 | 方法 |
|-------|--------|--------|
| 指令遵循、有用性、无害性 | 对齐 | 首选 DPO（Phase 10 · 08），而非 RLHF-PPO。 |
| 推理正确性（数学、代码） | 能力 | 带验证器奖励的 GRPO（Phase 9 · 12）。 |
| 长时程多步任务 | 智能体 | PPO / GRPO 配合面向步骤的过程奖励模型。 |
| 安全 / 拒答行为 | 安全 | RLHF-PPO 配独立的安全 RM，或 Constitutional AI。 |
| 推理期 Best-of-N | 快速对齐 | 解码时直接用 RM；不需要训练策略。 |
| 奖励蒸馏 | 推理算力 | 在冻结 LM 之上训练一个小型「奖励头」。 |

RLHF 是 2022–2024 年间*那个*一统天下的方法。到 2026 年，生产对齐流水线以 DPO 为主，只有 RM 密集或安全关键的步骤才保留 PPO。

> RLHF was *the* method in 2022–2024. In 2026, production alignment pipelines are DPO-first, PPO-only for the RM-intensive or safety-critical steps.

## Ship It · 交付

保存为 `outputs/skill-rlhf-architect.md`：

```markdown
---
name: rlhf-architect
description: Design an RLHF / DPO / GRPO alignment pipeline for a language model, including RM, KL, and data strategy.
version: 1.0.0
phase: 9
lesson: 9
tags: [rl, rlhf, alignment, llm]
---

Given a base LM, a target behavior (alignment / reasoning / refusal / agent), and a preference or verifier budget, output:

1. Stage. SFT? RM? DPO? GRPO? With justification.
2. Preference or verifier source. Humans, AI feedback, rule-based, unit-test-pass, or reward distillation.
3. KL strategy. Fixed β, adaptive β, or DPO (implicit KL).
4. Diagnostics. Mean KL, reward stability, over-optimization guard (holdout human eval).
5. Safety gate. Red-team set, refusal rate, safety RM separate from helpfulness RM.

Refuse to ship RLHF-PPO without a KL monitor. Refuse to use an RM smaller than the target policy. Refuse length-only rewards. Flag any pipeline that does not hold back a blind human-eval set as lacking over-optimization protection.
```

> Save as `outputs/skill-rlhf-architect.md`:

## Exercises · 练习

1. **简单。** 用 500 个合成偏好对训练 `code/main.py` 里的 Bradley-Terry 奖励模型。在留出的 100 对上测量成对准确率，应超过 90%。
2. **中等。** 用 `β ∈ {0.0, 0.1, 1.0}` 跑玩具 PPO-RLHF 循环。对每个 β 画出「RM 分数 vs 对参考模型的 KL」随更新次数的变化。哪一组跑出了奖励黑客？
3. **困难。** 在同一份偏好数据上实现 DPO（闭式偏好似然损失），从消耗算力和最终 RM 分数两方面与 RLHF-PPO 流水线对比。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| RLHF | 「对齐 RL」 | 三阶段的 SFT + RM + PPO 流水线（Christiano 2017、Ouyang 2022）。 |
| Reward Model (RM) | 「打分网络」 | 用 Bradley-Terry 拟合两两偏好的学习型标量函数。 |
| Bradley-Terry | 「成对 logistic 损失」 | `P(y_+ ≻ y_-) = σ(R(y_+) - R(y_-))`；RM 的标准目标。 |
| KL penalty | 「待在参考模型附近」 | 奖励里的 `β · KL(π_θ \|\| π_ref)`；防奖励黑客的正则化器。 |
| Reward hacking | 「古德哈特定律」 | 策略利用 RM 的缺陷；症状：奖励涨、人类评估平。 |
| RLAIF | 「AI 标注的偏好」 | 标签来自另一个 LLM 而非人类的 RLHF。 |
| PRM | 「过程奖励模型」 | 给部分推理步骤打分；用于推理流水线。 |
| Constitutional AI | 「Anthropic 的方法」 | 由显式规则引导的 AI 生成偏好。 |

## Further Reading · 延伸阅读

- [Christiano et al. (2017). Deep Reinforcement Learning from Human Preferences](https://arxiv.org/abs/1706.03741) —— 开创 RLHF 的论文。
- [Ouyang et al. (2022). InstructGPT — Training language models to follow instructions with human feedback](https://arxiv.org/abs/2203.02155) —— ChatGPT 背后的配方。
- [Stiennon et al. (2020). Learning to summarize with human feedback](https://arxiv.org/abs/2009.01325) —— 更早期的摘要任务 RLHF。
- [Rafailov et al. (2023). Direct Preference Optimization](https://arxiv.org/abs/2305.18290) —— DPO；2026 年 RLHF 之后的新默认。
- [Bai et al. (2022). Constitutional AI: Harmlessness from AI Feedback](https://arxiv.org/abs/2212.08073) —— RLAIF 与自我批评循环。
- [Anthropic RLHF paper (Bai et al. 2022). Training a Helpful and Harmless Assistant](https://arxiv.org/abs/2204.05862) —— 那篇 HH 论文。
- [Hugging Face TRL library](https://huggingface.co/docs/trl) —— 生产级 `RewardTrainer` 与 `PPOTrainer`。自适应 KL 和价值头的细节去读 trainer 源码。
- [Hugging Face — Illustrating Reinforcement Learning from Human Feedback](https://huggingface.co/blog/rlhf)，作者 Lambert、Castricato、von Werra、Havrilla —— 带图解的三阶段流水线权威讲解。
- [von Werra et al. (2020). TRL: Transformer Reinforcement Learning](https://github.com/huggingface/trl) —— 这个库本身；`examples/` 里有面向 Llama、Mistral、Qwen 的端到端 RLHF 脚本。
- [Sutton & Barto (2018). Ch. 17.4 — Designing Reward Signals](http://incompleteideas.net/book/RLbook2020.pdf) —— 奖励假设的视角；思考奖励黑客前的必备前置阅读。
