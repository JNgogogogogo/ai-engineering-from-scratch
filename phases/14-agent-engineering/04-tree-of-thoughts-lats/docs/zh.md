# Tree of Thoughts and LATS: Deliberate Search · Tree of Thoughts 与 LATS：深思熟虑的搜索

> 单条思维链轨迹没有回旋的余地。ToT（Yao et al., 2023）把推理变成一棵树，在每个节点上做自我评估。LATS（Zhou et al., 2024）用蒙特卡洛树搜索把 ToT、ReAct 和 Reflexion 统一了起来。Game of 24 从 4%（CoT）升到 74%（ToT）；LATS 在 HumanEval 上拿到 92.7% pass@1。

> A single chain-of-thought trajectory has no room to backtrack. ToT (Yao et al., 2023) turns reasoning into a tree with self-evaluation on each node. LATS (Zhou et al., 2024) unifies ToT with ReAct and Reflexion under Monte Carlo Tree Search. Game of 24 goes from 4% (CoT) to 74% (ToT); LATS hits 92.7% pass@1 on HumanEval.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 03 (Reflexion)
**Time:** ~75 minutes

---

## Learning Objectives · 学习目标

- 把推理框成搜索：节点是「想法」，边是「扩展」，值是「多有希望」。
- 用标准库实现一个 ToT 风格的 BFS 树搜索，带自我评估打分。
- 扩展到一个玩具 LATS MCTS 循环：select / expand / simulate / backpropagate。
- 判断什么时候搜索值得付出 token 乘数（Game of 24、代码生成），什么时候单条轨迹就够（简单问答）。

> Frame reasoning as search: nodes are "thoughts," edges are "expansions," value is "how promising."
> Implement a stdlib ToT-style BFS tree search with self-evaluation scoring.
> Extend to a toy LATS MCTS loop with select / expand / simulate / backpropagate.
> Decide when search is worth the token multiplier (Game of 24, code generation) and when a single trajectory is enough (simple Q&A).

---

## The Problem · 问题在哪

思维链是一次线性行走。如果第一步错了，后面每一步都建立在坏前提之上。在 Game of 24（用四个数字和 + − × ÷ 凑出 24）上，GPT-4 CoT 只有 4% 的准确率。模型早早选错了子表达式，并且无法恢复。

推理需要的能力是：提出多个候选、评估它们、挑出有希望的、在死路出现时回溯。这就是搜索。Tree of Thoughts 和 LATS 是它的两个规范表述。

> Chain-of-thought is a linear walk. If the first step is wrong, every subsequent step works on a bad premise. On Game of 24 (use four digits with + − × ÷ to make 24), GPT-4 CoT hits 4% accuracy. The model picks the wrong subexpression early and cannot recover.
> What reasoning needs is the ability to propose multiple candidates, evaluate them, pick the promising ones, and backtrack when dead ends appear. That is search. Tree of Thoughts and LATS are the two canonical formulations.

---

## The Concept · 概念

### Tree of Thoughts (Yao et al., NeurIPS 2023)

每个节点是一个连贯的中间步骤（「一个想法」）。每个节点可以扩展出 K 个子想法。LLM 用打分提示词对每个节点做自我评估。搜索遍历这棵树——BFS、DFS 或 beam。

```
                     (root: "find 24 from 4 6 4 1")
                    /               |            \
           ("6 - 4 = 2")    ("4 + 1 = 5")    ("4 * 6 = 24")  <- Score: HIGH
              /   \              |                  |
          ...    ...          ...                finish
```

自我评估是承重墙。论文给出了三种变体：`sure / likely / impossible` 分类、`1..10` 数值打分、候选间投票。三种在 Game of 24 上都大幅击败 CoT（GPT-4 从 4% → 74%）。

> Each node is a coherent intermediate step ("a thought"). Each node can expand to K child thoughts. The LLM self-evaluates each node with a scoring prompt. Search explores the tree — BFS, DFS, or beam.
> Self-evaluation is the load-bearing piece. The paper shows three variants: `sure / likely / impossible` classification, `1..10` numeric score, and vote among candidates. All three beat CoT substantially on Game of 24 (4% -> 74% with GPT-4).

---

### LATS (Zhou et al., ICML 2024)

LATS 在 MCTS 之下统一了 ToT、ReAct 和 Reflexion。LLM 扮演三个角色：

- **Policy（策略）**：提出候选的下一步动作（ReAct 式）。
- **Value function（价值函数）**：给部分轨迹打分（ToT 式自我评估）。
- **Self-reflector（自我反思器）**：失败时写一段自然语言反思（Reflexion 式），并用它为未来的 rollout 重新播种。

环境反馈（观察）混入 value function，因此搜索由真实工具结果而非模型的主观判断提供信息。论文当时的结果：GPT-4 在 HumanEval 上 pass@1 92.7%（SOTA），GPT-3.5 在 WebShop 上平均 75.9（逼近基于梯度的微调）。

> LATS unifies ToT, ReAct, and Reflexion under MCTS. The LLM plays three roles: **Policy**: propose candidate next actions (ReAct-style); **Value function**: score a partial trajectory (ToT-style self-eval); **Self-reflector**: on failure, write a natural-language reflection (Reflexion-style) and use it to reseed future rollouts.
> Environment feedback (observations) mixes into the value function so the search is informed by real tool results, not just model opinions. Results at paper time: HumanEval pass@1 92.7% with GPT-4 (SOTA), WebShop average 75.9 with GPT-3.5 (approaching gradient-based fine-tuning).

---

### MCTS, minimally · MCTS 最小版

每次迭代四个阶段：

1. **Select（选择）** —— 用 UCT（树的置信上界）从根走到叶。
2. **Expand（扩展）** —— 用 policy 生成 K 个子节点。
3. **Simulate（模拟）** —— 从一个子节点用 policy 做 rollout，用 value function（或环境奖励）给叶打分。
4. **Backpropagate（回传）** —— 沿路径向上更新访问计数和价值估计。

UCT 公式：`Q(s, a) + c * sqrt(ln N(s) / N(s, a))`。第一项是利用；第二项是探索。按任务调 `c`。

> 1. **Select** — walk from root to a leaf using UCT (upper confidence bound for trees).
> 2. **Expand** — generate K children via the policy.
> 3. **Simulate** — rollout from a child using the policy, score the leaf with the value function (or environment reward).
> 4. **Backpropagate** — update visit counts and value estimates up the path.
>
> UCT formula: `Q(s, a) + c * sqrt(ln N(s) / N(s, a))`. First term is exploitation; second is exploration. Tune `c` per task.

---

### The cost reality · 成本的现实

搜索会引爆 token。ToT 在 Game of 24 上用的 token 是 CoT 的 100–1000 倍。LATS 类似。这并不免费；把搜索留给：

- 单条轨迹被证明不够用的任务（Game of 24、复杂代码）。
- 墙钟时间不如正确性重要的任务。
- 有便宜且可靠 value function 的任务（代码用单元测试，数学用显式目标）。

如果你的任务只有一个正确答案而评估器噪声很大，搜索常常让事情更糟——它会找到一个「打分好看」的错误答案。

> Search explodes tokens. ToT on Game of 24 uses 100–1000x the tokens of CoT. LATS is similar. This is not free; reserve search for: tasks where a single trajectory is demonstrably insufficient; tasks where wall-clock is less important than correctness; tasks with a cheap, reliable value function.
> If your task has a single right answer and a noisy evaluator, search often makes things worse — it finds a "good-scoring" wrong answer.

---

### 2026 positioning · 2026 年的定位

大多数生产智能体并不跑 LATS。他们跑的是带工具锚定验证的 ReAct（CRITIC，第 5 课）。搜索出现在专门的小生境里：

- 把测试当作 value function 的编码智能体（HumanEval 式）。
- 探索多条查询路径的 deep-research 智能体。
- LangGraph 子图内部的规划密集型 workflow。

AlphaEvolve（第 11 课）是 2025 年的极端案例：对代码做进化搜索，适应度机器可验证，拿到前沿成果（56 年来第一个 4x4 矩阵乘法改进）。

> Most production agents do not run LATS. They run ReAct with tool-grounded verification (CRITIC, Lesson 05). Search shows up in specialized niches: coding agents that run tests as the value function; deep-research agents that explore multiple query paths; planning-heavy workflows inside LangGraph subgraphs.
> AlphaEvolve (Lesson 11) is the 2025 extreme: evolutionary search over code, machine-checkable fitness, frontier gains (first 4x4 matmul improvement in 56 years).

```figure
tree-of-thoughts
```

---

## Build It · 动手造

`code/main.py` 实现：

- 一个在一个风格化的「挑选算术运算」任务上的微型 ToT BFS。
- 同一任务上的玩具 LATS MCTS 循环（Select / Expand / Simulate / Backpropagate），带 UCT 选择。
- 一个由符号分数加自我评估分数组合而成的 value function。

跑起来：

```
python3 code/main.py
```

轨迹展示 ToT 用 BFS 在每个节点扩展三个候选，与 LATS 通过 MCTS 收敛到最佳 rollout 形成对比。两者都打印 token 计数。

> `code/main.py` implements: a tiny ToT BFS on a stylized "pick arithmetic ops" task; a toy LATS MCTS loop on the same task (Select / Expand / Simulate / Backpropagate) with UCT selection; a value function that composes a symbolic score plus a self-eval score.
> The trace shows ToT expanding three candidates per node with BFS, compared to LATS converging on the best rollout via MCTS. Token counts printed for both.

---

## Use It · 实战用法

LangGraph 以子图模式提供 ToT 式探索；LangChain 团队 2024 年 5 月关于 LATS 的博客是参考教程。LlamaIndex 提供一个 `TreeOfThoughts` 智能体。对大多数 2026 年的生产智能体来说，这个模式活在一道 `if task_complexity > threshold: use_search()` 闸门后面——见第 5 课的 evaluator-optimizer 模式。

> LangGraph ships ToT-style exploration as subgraph patterns; the LangChain team's blog on LATS (May 2024) is the reference tutorial. LlamaIndex ships a `TreeOfThoughts` agent. For most 2026 production agents this pattern lives behind an `if task_complexity > threshold: use_search()` gate — see the evaluator-optimizer pattern in Lesson 05.

---

## Ship It · 交付

`outputs/skill-search-policy.md` 在给定任务形状、预算和评估器保真度的前提下，在线性 ReAct、ToT、LATS 和进化搜索之间做选择。

> `outputs/skill-search-policy.md` selects between linear ReAct, ToT, LATS, and evolutionary search given task shape, budget, and evaluator fidelity.

---

## Exercises · 练习

1. 用 UCT c=0.1 和 c=2.0 分别跑玩具 LATS。轨迹里什么变了？
2. 把 value function 换成一个更吵的打分器（加随机抖动）。MCTS 还能找到最佳叶节点吗？它能容忍的最低信噪比是多少？
3. 实现 beam-search 版 ToT（每层保留 top-k）并与 BFS 对比。在紧张的 token 预算下哪个更好？
4. 读 LATS 第 5.1 节。复现 HumanEval 的轨迹数：要多少次 rollout 才能达到报告的 pass@1？
5. 读 LATS 论文中关于「LATS 什么时候帮助不大」的讨论。写一段话的决策规则，把任务形状映射到搜索策略。

> 1. Run the toy LATS with UCT c=0.1 vs c=2.0. What changes in the trace?
> 2. Swap the value function for a noisier scorer (add random jitter). Does MCTS still find the best leaf? What is the minimum signal-to-noise it tolerates?
> 3. Implement beam-search ToT (keep top-k at each level) and compare to BFS. Which is better on a tight token budget?
> 4. Read LATS Section 5.1. Reproduce the HumanEval trajectory count: how many rollouts does it take to hit the reported pass@1?
> 5. Read the LATS paper's discussion on "when LATS helps less." Write a one-paragraph decision rule mapping task shape to search strategy.

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Tree of Thoughts | 「会分叉的 CoT」 | Yao et al. —— 由想法节点组成的树，带自我评估 |
| LATS | 「给 LLM 用的 MCTS」 | Zhou et al. —— 在 MCTS 之下统一 ToT + ReAct + Reflexion |
| UCT | 「置信上界」 | 平衡利用（Q）与探索（ln N / n）的选择公式 |
| Value function | 「这个状态有多好」 | 提示词驱动的 LLM 打分或环境奖励；供 backprop 使用 |
| Policy | 「动作提议者」 | ReAct 式生成器；发出候选的下一步想法/动作 |
| Rollout | 「模拟轨迹」 | 从某节点用 policy 走到叶，再用 value 打分 |
| Backpropagate | 「更新祖先」 | 把叶节点的奖励沿路径上推，更新访问计数和 Q |
| Search cost | 「token 爆炸」 | Game of 24 上是 CoT 的 100-1000 倍；采用前先做预算 |

> | Term | What people say | What it actually means |
> |------|----------------|------------------------|
> | Tree of Thoughts | "Branching CoT" | Yao et al. — tree of thought nodes with self-evaluation |
> | LATS | "MCTS for LLMs" | Zhou et al. — unifies ToT + ReAct + Reflexion under MCTS |
> | UCT | "Upper confidence bound" | Select formula balancing exploitation (Q) and exploration (ln N / n) |
> | Value function | "How good is this state" | Prompted LLM score or environment reward; feeds backprop |
> | Policy | "Action proposer" | ReAct-style generator; emits candidate next thoughts/actions |
> | Rollout | "Simulated trajectory" | Walk from a node to a leaf using policy, score with value |
> | Backpropagate | "Update ancestors" | Push the leaf's reward up the path, updating visit counts and Q |
> | Search cost | "Token explosion" | 100-1000x CoT on Game of 24; budget before you adopt |

---

## Further Reading · 延伸阅读

- [Yao et al., Tree of Thoughts (arXiv:2305.10601)](https://arxiv.org/abs/2305.10601) —— 规范论文
- [Zhou et al., LATS (arXiv:2310.04406)](https://arxiv.org/abs/2310.04406) —— 带 Reflexion 反馈的 MCTS
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) —— 面向搜索的子图模式
- [AlphaEvolve (arXiv:2506.13131)](https://arxiv.org/abs/2506.13131) —— 带程序化评估器的进化搜索

> - [Yao et al., Tree of Thoughts (arXiv:2305.10601)](https://arxiv.org/abs/2305.10601) — the canonical paper
> - [Zhou et al., LATS (arXiv:2310.04406)](https://arxiv.org/abs/2310.04406) — MCTS with Reflexion feedback
> - [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) — subgraph patterns for search
> - [AlphaEvolve (arXiv:2506.13131)](https://arxiv.org/abs/2506.13131) — evolutionary search with programmatic evaluators
