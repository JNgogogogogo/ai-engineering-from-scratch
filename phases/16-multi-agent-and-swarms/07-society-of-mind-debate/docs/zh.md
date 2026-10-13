# Society of Mind and Multi-Agent Debate · 心智社会与多智能体辩论

> Minsky 1986 年的命题——智能是一个由专家组成的社会——每隔十年就被重新发现一次。2023 年，Du 等人把它变成了一个具体算法：多个 LLM 实例各自提出答案、互相阅读、批评、更新。经过 N 轮之后，它们收敛到一个共识，在六项推理与事实性任务上胜过 zero-shot CoT 和自我反思。有两个发现很关键：**多智能体**和**多轮次**各自独立地做出贡献。「社会」胜过单智能体的独白；多轮交锋胜过一次性投票。

> Minsky's 1986 premise — intelligence is a society of specialists — gets rediscovered every decade. In 2023 Du et al. turned it into a concrete algorithm: multiple LLM instances propose answers, read each other's answers, critique, and update. Over N rounds they converge on a consensus that beats zero-shot CoT and reflection on six reasoning and factuality tasks. Two findings matter: both **multiple agents** and **multiple rounds** contribute independently. The society beats a single-agent monologue; the multi-round exchange beats one-shot voting.

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 16 · 04 (Primitive Model)
**Time:** ~60 minutes

---

## Problem · 问题

self-consistency（自一致性）——同一个模型采样多次然后取多数答案——是你能给推理加装的最便宜的改进。它有用，但很快饱和。样本翻倍也未必再看到有意义的提升。

辩论打破了饱和。不再是来自同一个模型的 N 个独立样本，而是 N 个智能体阅读彼此的推理并修订。样本之间的相关性下降（它们不再 i.i.d.），而收敛点常常在 i.i.d. 投票自信地给出错误答案的地方反而是正确的。

> Self-consistency — sample one model many times and take the majority answer — is the cheapest reasoning improvement you can bolt on. It works, but it saturates fast. ... Debate breaks the saturation. Instead of N independent samples from one model, N agents read each other's reasoning and revise. The correlation between samples drops (they are no longer i.i.d.), and the convergence point is often correct where i.i.d. voting was confidently wrong.

---

## Concept · 概念

### The Du et al. 2023 algorithm · Du 等人 2023 的算法

来自 arXiv:2305.14325（ICML 2024）：

1. N 个智能体各自给出该问题的初始答案。
2. 对第 r = 2..R 轮：每个智能体看到其他智能体第 r-1 轮的答案，并被要求「考虑到这些，给出你的更新答案」。
3. R 轮之后，对最终答案做多数投票。

论文在 MMLU、GSM8K、传记、MATH 和事实性基准上测试。辩论稳定胜过 CoT 和 Self-Reflection。

> From arXiv:2305.14325 (ICML 2024): each of N agents produces an initial answer to the question; for round r = 2..R, each agent is shown the other agents' round r-1 answers and asked "considering these, give your updated answer"; after R rounds, majority-vote the final answers. ... The paper tests on MMLU, GSM8K, biographies, MATH, and factuality benchmarks. Debate consistently beats CoT and Self-Reflection.

---

### Two independent knobs · 两个独立的旋钮

同一篇论文的消融实验：

- **只有智能体数量**（1 轮，N 个答案多数投票）在多数任务上胜过单智能体，但会进入平台期。
- **只有轮数**（1 个智能体回看自己的先前推理）几乎没有帮助——这正是自我反思的已知弱点。
- **两者结合**才带来大幅跃升。多智能体之间的多轮交锋才是收益来源。

> Ablations from the same paper: ... **Agent count alone** (1 round, majority vote of N) beats single-agent on most tasks, but plateaus. ... **Round count alone** (1 agent seeing its own prior reasoning) barely helps — reflection's known weakness. ... **Both together** produces the big jumps. The multi-round exchange between multiple agents drives the gain.

---

### Why it works · 为什么有效

两个机制：

1. **接触分歧。** 当一个智能体看到另一条推理链得出不同结论时，它必须要么为自己的结论辩护、要么更新。无论哪种，第 r+1 轮的上下文都比第 r 轮更丰富。
2. **降低误差相关性。** 在 self-consistency 里，所有样本来自同一个模型，误差是相关的——你平均出一个自信的错误答案。不同的模型或不同的种子可以去相关。不同的 *经过辩论的观点* 去相关得更彻底。

> Two mechanisms: ... **Exposure to disagreement.** When an agent sees another agent's reasoning chain with a different conclusion, it has to either justify or update. Either way, the context for round r+1 is richer than round r. ... **Correlated error reduction.** In self-consistency, all samples come from the same model, so the errors correlate — you average into a confidently wrong answer. Different models or different seeds decorrelate. Different *debated views* decorrelate further.

---

### Heterogeneous debate · 异构辩论

A-HMAD 和相关后续工作让不同的智能体使用 *不同的基座模型*。Llama + Claude + GPT 同场辩论能减少单一模型文化的集体崩塌（第 26 课），因为一个模型家族的相关性错误不会被其他家族共享。

缺点：一个弱模型参与辩论可能把共识拖向它的错误答案（见「Should we be going MAD?」，arXiv:2311.17371）。

> A-HMAD and related follow-ups use *different base models* for different agents. Llama + Claude + GPT debating reduces monoculture collapse (Lesson 26) because the correlated errors of one model family are not shared by the others. ... Downside: a weak model participating in a debate can drag the consensus toward its wrong answer (see "Should we be going MAD?", arXiv:2311.17371).

---

### NLSOM — the 129-agent extension · NLSOM——129 个智能体的扩展

Zhuge 等人（「Mindstorms in Natural Language-Based Societies of Mind,」arXiv:2305.17066）把这个想法放大到 129 个成员的社会。结果：专业化与自组织随规模涌现，系统在视觉问答等任务上胜过单智能体。

> Zhuge et al. ("Mindstorms in Natural Language-Based Societies of Mind," arXiv:2305.17066) scaled this idea to 129-member societies. The result: specialization and self-organization emerge with scale, and the system outperforms single-agent on tasks like visual question answering.

---

### Failure modes · 失败模式

- **谄媚级联（sycophancy cascade）。** 所有智能体都顺从听起来最自信的那个。辩论塌缩成嗓门最大的人。用提示词指定对抗角色（「某个智能体必须论证反方立场」）会有帮助。
- **话题漂移。** 多轮辩论会漂离原始问题。缓解：每轮重新注入问题。
- **计算爆炸。** N 个智能体 × R 轮 = N·R 次 LLM 调用，且每次调用的上下文都在增长。5 智能体 5 轮的辩论是 25 次上下文不断增长的调用。每个问题的成本可以超过单次 CoT 调用的 10 倍。

```figure
multi-agent-debate
```

> **Sycophancy cascade.** All agents defer to whichever agent sounds most confident. The debate collapses to the loudest voice. Prompting for adversarial roles ("one agent must argue the counter-position") helps. ... **Topic drift.** Debates over many rounds drift from the original question. Mitigation: re-inject the question every round. ... **Compute blowup.** N agents × R rounds = N·R LLM calls, each with a context that grows. A 5-agent, 5-round debate is 25 calls at growing context. Cost per question can exceed 10× a single CoT call.

---

## Build It · 动手造

`code/main.py` 在一道数学题上跑 3 智能体 × 3 轮的辩论，每个智能体的初始答案不同（可能有错）。智能体是脚本化的——每个「更新」都是按脚本化的置信度对邻居答案做加权平均。逐轮日志里可以清楚看到收敛。

演示展示两个关键效应：

- 一轮交锋就能让智能体更接近正确答案。
- 第 2 轮之后的额外轮次收益递减（与 Du 等人的平台期一致）。

Run:

```
python3 code/main.py
```

> `code/main.py` runs a 3-agent × 3-round debate on a math question where each agent starts with a different (possibly wrong) answer. Agents are scripted — each "updates" by averaging the neighbors' answers weighted by a scripted confidence. Convergence is visible in the round-by-round log. ... A single round of exchange moves agents closer to the correct answer. Extra rounds past round 2 show diminishing returns (matches Du et al.'s plateau).

---

## Use It · 实战用法

`outputs/skill-debate-configurator.md` 为新任务配置一场辩论：智能体数量、轮数、异构性（同模型 vs 混合）、角色分配（对称 vs 一个对抗角色）。它还会在你运行之前估算 token 成本。

> `outputs/skill-debate-configurator.md` configures a debate for a new task: number of agents, number of rounds, heterogeneity (same model vs mixed), role assignment (symmetric vs one-adversarial). It also estimates the token cost before you run.

---

## Ship It · 交付

如果你要上线辩论：

- **轮数封顶在 3。** Du 等人表明 3 轮就拿到大部分收益。更多只是成本，不是质量。
- **智能体数封顶在 5。** 超过 5 个，上下文膨胀和成本占主导。
- **默认异构。** 池里至少要有两个不同的基座模型。
- **对抗席位。** 固定一个智能体被提示为无论如何都要反对。打破谄媚。
- **记录每一轮。** 隐藏中间轮次的辩论系统既无法调试也无法审计。

> If you ship debate: ... **Cap rounds at 3.** Du et al. show 3 rounds capture most of the gain. More is cost, not quality. ... **Cap agents at 5.** Beyond 5, context bloat and cost dominate. ... **Heterogeneous by default.** At least two different base models in the pool. ... **Adversarial slot.** One agent prompted to disagree regardless. Breaks sycophancy. ... **Log every round.** Debate systems that hide intermediate rounds cannot be debugged or audited.

---

## Exercises · 练习

1. 跑 `code/main.py`，然后把轮数设成 5，观察收益递减。到第几轮额外收敛停止？
2. 加第四个对抗角色的智能体：永远反对当前多数。这会破坏还是改善收敛？
3. 绘制（打印）每轮的一致性得分（持多数答案的智能体比例）。它什么时候到 1.0？到 1.0 等价于「正确」吗？
4. 读 Du 等人第 4 节的消融实验。用这份代码复现「只有智能体」vs「只有轮数」vs「两者结合」的结果。
5. 读「Should we be going MAD?」（arXiv:2311.17371），列出循环轮转之外的两种辩论变体——例如裁判主持、辩论链、对抗式。

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Society of Mind | 「Minsky 的想法」 | 智能是相互作用的专家；1986 年的框架如今通过 LLM 辩论落地。 |
| Multi-agent debate | 「智能体互相争论」 | N 个智能体提案、互相批评、在 R 轮中修订、最后多数投票。 |
| Consensus | 「他们达成一致了」 | 不是认知意义上的真理——只是持多数答案的比例。可能自信地错。 |
| Rounds | 「交锋步」 | 一轮 = 每个智能体阅读其他智能体并更新一次。 |
| Heterogeneous debate | 「混用模型家族」 | 用不同的基座模型让误差去相关。 |
| Sycophancy cascade | 「所有人都同意嗓门大的」 | 辩论失败：智能体不顾对错顺从最自信的智能体。 |
| NLSOM | 「129 智能体社会」 | 自然语言心智社会；Zhuge 等人的放大版。 |
| Correlated error | 「同一个模型，同一个 bug」 | self-consistency 饱和的原因；跨不同观点的辩论可以去相关。 |

---

## Further Reading · 延伸阅读

- [Du et al. — Improving Factuality and Reasoning in Language Models through Multiagent Debate](https://arxiv.org/abs/2305.14325) —— 参考论文，ICML 2024
- [Zhuge et al. — Mindstorms in Natural Language-Based Societies of Mind](https://arxiv.org/abs/2305.17066) —— 129 智能体的 NLSOM
- [Should we be going MAD? A Look at Multi-Agent Debate Strategies for LLMs](https://arxiv.org/abs/2311.17371) —— 对各种辩论变体做基准测试
- [Debate project page](https://composable-models.github.io/llm_debate/) —— Du 等人的代码、演示与消融细节
