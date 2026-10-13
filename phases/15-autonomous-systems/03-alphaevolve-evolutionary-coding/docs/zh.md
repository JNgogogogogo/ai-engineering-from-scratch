# AlphaEvolve — Evolutionary Coding Agents · AlphaEvolve——进化式编码智能体

> 把一个前沿编码模型、一个进化循环和一个机器可判定的评估器配在一起。让这个循环跑得足够久。它发现了一个只用 48 次标量乘法的 4x4 复矩阵乘法流程——这是 56 年来对 Strassen 的首次改进。它还找到了一个覆盖整个 Google 的 Borg 调度启发式，在生产环境里回收了约 0.7% 的集群算力。这个架构是刻意朴素的。赢点全部来自评估器的严格性。

> Pair a frontier coding model with an evolutionary loop and a machine-checkable evaluator. Let the loop run long enough. It discovers a 4x4 complex-matrix multiplication procedure that uses 48 scalar multiplications — the first improvement over Strassen in 56 years. It also finds a Google-wide Borg scheduling heuristic that recovers ~0.7% of cluster compute in production. The architecture is boring on purpose. The wins come from the evaluator's rigor.

**类型：** Learn（学习）
**语言：** Python（仅 stdlib，evolutionary-loop 玩具实现）
**先修：** Phase 15 · 01（long-horizon framing）、Phase 15 · 02（self-taught reasoning）
**时间：** ~60 分钟

## The Problem · 问题在哪

大语言模型会写代码。进化算法能在代码上做搜索。两者都已被单独尝试了几十年，也都撞上了天花板。LLM 的天花板是 confabulation（一本正经地编造）：模型写出看起来合理的代码，但它并不做它声称要做的事。进化算法的天花板是搜索成本：对语法做随机变异，很少能产出可编译的程序，更别提更好的程序。

AlphaEvolve（Novikov 等，DeepMind，arXiv:2506.13131，2025 年 6 月）把两者结合起来。LLM 对一个程序数据库提出有针对性的修改；一个自动评估器给每个变体打分；高分变体成为未来世代的父本。LLM 承担「写出合理代码」这个昂贵的步骤；评估器抓住那些编造。循环一跑就是几小时到几周。

已报告的结果：48 次标量乘法的 4x4 复矩阵乘法（Strassen 1969 年的界是 49）、Google 生产环境中的 Borg 调度启发式、32.5% 的 FlashAttention kernel 提速、Gemini 训练吞吐量改进。

这个架构能工作的原因，是评估器是机器可判定的。评估器不在的地方，它就不工作。这个不对称性就是本课的要点。

> Large language models can write code. Evolutionary algorithms can search over code. Both have been tried separately for decades; both hit ceilings. The LLM ceiling is confabulation: the model writes plausible code that does not do what it claims. The evolutionary ceiling is search cost: random mutations over syntax rarely produce compilable programs, let alone better ones.
> AlphaEvolve (Novikov et al., DeepMind, arXiv:2506.13131, June 2025) combines them. The LLM proposes targeted edits to a program database; an automatic evaluator scores each variant; high-scoring variants become parents for future generations. The LLM handles the expensive step of writing plausible code; the evaluator catches the confabulations. The loop runs for hours to weeks.
> The architecture works because the evaluator is machine-checkable. It does not work where the evaluator isn't. That asymmetry is the lesson.

## The Concept · 概念

### The loop · 循环

1. 从一个正确但次优的种子程序 `P_0` 出发。
2. 维护一个变体程序数据库，每个变体都由评估器打过分。
3. 从数据库采样一个或多个父本（MAP-elites 风格或岛屿式）。
4. 提示 LLM（大量候选用 Gemini Flash，难题用 Gemini Pro）产出父本的一个修改版变体。
5. 编译、运行该变体，并在留出评估器上评估。
6. 按得分与特征向量作为键插入数据库。
7. 重复。

有两个细节很关键。第一，给 LLM 的 prompt 不只有父本程序——通常是数据库里的若干头部变体，加上评估器签名，再加上一段简短的任务描述。模型的任务是提出一个可能提升得分的有针对性修改。第二，数据库是有结构的（MAP-elites 网格、岛屿式），所以循环探索的是多样性，而不只是当前的第一名。

> 1. Start from a seed program `P_0` that is correct but suboptimal. 2. Maintain a database of variant programs, each scored by the evaluator. 3. Sample one or more parents from the database (MAP-elites-style or island-based). 4. Prompt the LLM (Gemini Flash for many candidates, Gemini Pro for the hard ones) to produce a modified variant of the parent. 5. Compile, run, and evaluate the variant on the held-out evaluator. 6. Insert into the database keyed by its score and feature vector. 7. Repeat.
> First, the LLM is prompted with more than the parent program — typically several top variants from the database, plus the evaluator signature, plus a short task description. The model's job is to propose a targeted change that might improve the score. Second, the database is structured (MAP-elites grid, island-based) so the loop explores diversity, not just the current leader.

### What makes the evaluator non-negotiable · 为什么评估器不可妥协

AlphaEvolve 的所有战果都来自评估器快速、确定、难以钻空子的领域：

- **矩阵乘法算法**：一个单元测试，做矩阵乘法并按位一致地检查相等。
- **Borg 调度启发式**：一个生产级模拟器，回放历史集群负载并测量被浪费的算力。
- **FlashAttention kernel**：正确性测试加上真实硬件上的 wall-clock 基准。
- **Gemini 训练吞吐量**：按步测量的 GPU 秒数。

在每个案例里，评估器都抓住了那类否则会大行其道的 LLM 错误：编造的正确性声明、在硬件上消失的性能声明、边界情况失败。把评估器拿掉，循环就会去优化「好看的代码」。

> AlphaEvolve's wins all come from domains where the evaluator is fast, deterministic, and hard to game. ... In each case the evaluator catches the class of LLM errors that would otherwise dominate: confabulated correctness claims, performance claims that vanish on hardware, and edge-case failures. Remove the evaluator and the loop optimizes for pretty code.

### Reward hacking is the other face of that statement · 奖励劫持是同一句话的另一面

进化会优化评估器度量的任何东西。如果评估器不完美，循环就会找到那个不完美之处。在一个没有验证的领域里，循环会去优化表面特征，而不是预期行为。DeepMind 在论文里明确指出了这一点：AlphaEvolve 的成功只会转移到评估器严格性与搜索野心相匹配的领域。

2025-2026 年代码搜索循环中 reward hacking 的具体例子：

- 以「完成时间」为奖励的优化目标，奖励了提交空解。
- 以「测试下正确性」为奖励的基准分，奖励了背题和过拟合。
- 一个「代码质量」代理指标，奖励了删注释和改变量名——语义毫无变化。

AlphaEvolve 的对策：上线一个 LLM 从未见过的留出评估器，其输入在评估时才生成。即便如此，DeepMind 仍建议对任何提议的部署做强人工审查。

> Evolution optimizes for whatever the evaluator measures. If the evaluator is imperfect, the loop will find the imperfection. In an unverified domain the loop would optimize for the surface feature, not the intended behavior. DeepMind flags this explicitly in the paper: AlphaEvolve's successes transfer only to domains where evaluator rigor matches the ambition of the search.
> The fix in AlphaEvolve: ship a held-out evaluator the LLM has never seen, with inputs generated at evaluation time. Even then, DeepMind recommends strong review on any proposed deployment.

### Why LLM + search beats either alone · 为什么 LLM + 搜索强于单打独斗

LLM 能产出可编译、语义上说得通的修改。对一个 2000 行的 Python 文件做随机变异的遗传算法，几乎总是产出语法错误。LLM 还把搜索集中在说得通的邻域上（改一个函数，而不是随机字节），这大幅减少了被浪费的评估器调用。

反过来，评估器抓住 LLM 的编造。LLM 会信誓旦旦地说某个函数「在极限下是 O(n log n)」，而它实际上是 O(n^2)；一个 wall-clock 基准让这个问题一锤定音。

> The LLM can produce compilable, semantically plausible modifications. A random-mutation GA on a 2000-line Python file almost always produces syntax errors. The LLM also concentrates search on plausible neighborhoods (change one function, not random bytes) which dramatically reduces wasted evaluator calls.
> The evaluator, in turn, catches the LLM's confabulations. LLMs will confidently claim that a function "is O(n log n) in the limit" when it is actually O(n^2); a wall-clock benchmark makes the question settled.

### Where AlphaEvolve fits in the frontier stack · AlphaEvolve 在前沿技术栈中的位置

| 系统 | 生成器 | 评估器 | 领域 | 代表战果 |
|---|---|---|---|---|
| AlphaEvolve | Gemini | 正确性 + 基准 | 算法、kernel、调度器 | 48 乘 4x4 矩阵乘法 |
| FunSearch (DeepMind, 2023) | PaLM / Codey | 正确性 | 组合数学 | cap-set 下界 |
| AI Scientist v2 (Sakana, L5) | GPT/Claude | LLM 点评 + 实验 | ML 研究 | ICLR workshop 论文 |
| Darwin Godel Machine (L4) | 智能体脚手架 | SWE-bench / Polyglot | 智能体代码 | SWE-bench 20% → 50% |

四者都是同一个配方的变体：生成器 + 评估器 + 循环。差别在于评估器评什么、评得有多严。

> | System | Generator | Evaluator | Domain | Example win |
> |---|---|---|---|---|
> | AlphaEvolve | Gemini | correctness + benchmark | algorithms, kernels, schedulers | 48-mul 4x4 matmul |
> | FunSearch (DeepMind, 2023) | PaLM / Codey | correctness | combinatorial math | cap-set lower bounds |
> | AI Scientist v2 (Sakana, L5) | GPT/Claude | LLM critique + experiment | ML research | ICLR workshop paper |
> | Darwin Godel Machine (L4) | agent scaffolding | SWE-bench / Polyglot | agent code | 20% → 50% SWE-bench |
>
> All four are variations on the same recipe: generator plus evaluator, loop. The differences are what the evaluator grades and how rigorous it is.

```figure
alphaevolve-loop
```

## Use It · 实战用法

`code/main.py` 在一个玩具符号回归问题上实现了一个最小的类 AlphaEvolve 循环。「LLM」是一个 stdlib 代理，它对一个计算目标函数的程序提出小的语法变异。「评估器」在留出测试点上测量均方误差。

观察：

- 最佳得分如何随世代提升。
- MAP-elites 网格如何让多样的解存活，使循环不至于收敛到一个局部极小。
- 去掉留出测试（只用训练集的评估器）之后，循环如何壮观地过拟合。

> `code/main.py` implements a minimal AlphaEvolve-like loop over a toy symbolic-regression problem. The "LLM" is a stdlib proxy that proposes small syntactic mutations to a program that computes a target function. The "evaluator" measures mean squared error on held-out test points.
> Watch how the best score improves over generations, how a MAP-elites grid keeps diverse solutions alive so the loop doesn't converge on a local minimum, and how removing the held-out test (training-only evaluator) lets the loop overfit spectacularly.

## Ship It · 交付

`outputs/skill-evaluator-rigor-audit.md` 是在一个新领域考虑类 AlphaEvolve 循环之前的前置检查：你的评估器真的能抓住你在乎的那些失败吗？

> `outputs/skill-evaluator-rigor-audit.md` is the precondition for considering an AlphaEvolve-style loop in a new domain: does your evaluator actually catch the failures you care about?

## Exercises · 练习

1. 运行 `code/main.py`。记录最佳得分轨迹。禁用留出评估器（flag `--no-holdout`）再跑一次。量化过拟合程度。

2. 读 AlphaEvolve 论文第 3 节关于 MAP-elites 网格的内容。为一个新问题（例如编译器优化 pass）设计一个能保持搜索多样性的特征向量描述子。

3. 48 次乘法的 4x4 结果，在 56 年后改进了 Strassen 的 49 次乘法界。读论文附录 F，用三句话解释为什么这个问题的评估器特别容易做对，以及为什么大多数领域并非如此。

4. 提出一个 AlphaEvolve 会失败的领域。精确指出评估器在哪里失效，以及为什么。

5. 对一个你熟悉的领域，写出你会使用的评估器签名。包括 (a) 正确性条件，(b) 性能指标，(c) 留出输入生成规则，(d) 至少一条反 reward-hacking 检查。

> 1. Run `code/main.py`. Note the best score trajectory. Disable the held-out evaluator (flag `--no-holdout`) and re-run. Quantify the overfitting.
> 3. The 48-multiplication 4x4 result improved on Strassen's 49-mul bound after 56 years. Read Appendix F of the paper and explain in three sentences why the evaluator for this problem is particularly easy to get right, and why most domains are not like it.
> 5. For a domain you know, write the evaluator signature you would use. Include (a) correctness conditions, (b) performance metric, (c) held-out input generation rule, (d) at least one anti-reward-hacking check.

## Key Terms · 术语表

| 术语 | 人们口头怎么说 | 它实际是什么意思 |
|---|---|---|
| AlphaEvolve | 「DeepMind 的进化式编码智能体」 | Gemini + 程序数据库 + 机器可判定评估器 |
| MAP-elites | 「保持多样性的档案库」 | 按特征向量分格的网格；每格保存具有该描述子的最佳变体 |
| Island model（岛屿模型） | 「并行的进化亚种群」 | 独立演化的种群定期迁移；防止过早收敛 |
| Machine-checkable evaluator | 「确定性神谕」 | LLM 无法伪造的单元测试、模拟器或基准——这个循环的先决条件 |
| Reward hacking（奖励劫持） | 「优化度量，而不是目标」 | 循环找到在不完成预期任务的情况下最大化分数的办法 |
| Seed program（种子程序） | 「起点」 | 循环据此演化的初始「正确但次优」程序 |
| Held-out evaluator（留出评估器） | 「LLM 从未见过的评估数据」 | 在评估时才生成输入，防止背题 |

> | Term | What people say | What it actually means |
> |---|---|---|
> | AlphaEvolve | "DeepMind's evolutionary coding agent" | Gemini + program database + machine-checkable evaluator |
> | MAP-elites | "Diversity-preserving archive" | Grid keyed by feature vectors; each cell holds the best variant with that descriptor |
> | Island model | "Parallel evolution subpopulations" | Independent populations that migrate periodically; prevents premature convergence |
> | Machine-checkable evaluator | "Deterministic oracle" | A unit test, simulator, or benchmark the LLM cannot fake — a prerequisite for this loop |
> | Reward hacking | "Optimizing the measure, not the goal" | Loop finds a way to maximize score without doing the intended task |
> | Seed program | "The starting point" | An initial correct-but-suboptimal program the loop evolves from |
> | Held-out evaluator | "Evaluation data the LLM never saw" | Inputs generated at evaluation time to prevent memorization |

## Further Reading · 延伸阅读

- [Novikov et al. (2025). AlphaEvolve: A coding agent for scientific and algorithmic discovery](https://arxiv.org/abs/2506.13131) —— 完整论文。
- [DeepMind blog on AlphaEvolve](https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/) —— 厂商综述与结果。
- [AlphaEvolve results repository](https://github.com/google-deepmind/alphaevolve_results) —— 被发现的算法，包括 48 乘 4x4 矩阵乘法。
- [Romera-Paredes et al. (2023). Mathematical discoveries from program search with LLMs (FunSearch)](https://www.nature.com/articles/s41586-023-06924-6) —— 前身系统。
- [Anthropic — Responsible Scaling Policy v3.0 (Feb 2026)](https://anthropic.com/responsible-scaling-policy/rsp-v3-0) —— 把「受评估器约束的自主性」定为一个关键研究方向。
