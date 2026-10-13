# Capstone 05 — Autonomous Research Agent (AI-Scientist Class) · 自主研究智能体（AI-Scientist 级）

> Sakana 的 AI-Scientist-v2 发表了完整论文。Agent Laboratory 跑了实验。Allen AI 公开了 trace。2026 年的形态是：在实验树上做「计划-执行-验证」树搜索、预算化成本、沙箱化代码执行、一个带视觉反馈的 LaTeX 写手，以及一个自动化的 NeurIPS 风格评审团。这个毕业项目（capstone）就是造一个，在每篇 $30 预算内端到端跑通，并且挺过 Sakana 记录在案的沙箱逃逸红队测试。

> Sakana's AI-Scientist-v2 published full papers. Agent Laboratory ran the experiments. Allen AI shared traces. The 2026 shape is plan-execute-verify tree search over experiments, budgeted cost, sandboxed code execution, a vision-feedback LaTeX writer, and an automated NeurIPS-style reviewer ensemble. The capstone is to build one, run it end to end within $30 per paper, and survive the sandbox-escape red team that Sakana documented.

**类型（Type）:** 毕业项目（Capstone）
**语言（Languages）:** Python（agent + 沙箱），LaTeX（输出）
**先修（Prerequisites）:** Phase 2（ML）、Phase 3（深度学习）、Phase 7（transformers）、Phase 10（从零造 LLM）、Phase 14（智能体 agent）、Phase 15（自治）、Phase 16（多智能体）、Phase 18（安全）
**实践阶段（Phases exercised）:** P0 · P2 · P3 · P7 · P10 · P14 · P15 · P16 · P18
**时间（Time）:** 40 小时

## Problem · 问题

自主研究智能体在 2026 年跨过了门槛。Sakana AI 的 AI-Scientist-v2 发表于 Nature，其生成的论文通过了 workshop 同行评审。ShinkaEvolve（ICLR 2026）把这条线扩展到演化假设。AMD 的 Agent Laboratory 交付了可复现 trace。这些智能体不是魔法 —— 它们是一个跑在候选实验树上的「计划-执行-验证」循环，配上成本上限、种子绑定的沙箱和自动化评审。手艺在循环、预算和安全故事里。

你通过在一个窄域里对着一个种子想法实现这个循环来学会它（比如，对一个 100M 参数 transformer 做注意力稀疏度消融）。价值不在第一次运行就发现新东西。价值在基础设施：树搜索、实验沙箱、写手-评审循环、红队报告。Sakana 团队记录了沙箱逃逸事故；你的智能体必须通过同一套红队（red team）。

> Autonomous research agents crossed a threshold in 2026. Sakana AI's AI-Scientist-v2 was published in Nature with generated papers that cleared workshop peer review. ... The agents are not magic — they are a plan-execute-verify loop running over a tree of candidate experiments, with cost caps, seed-bound sandboxes, and automated review. The craft is in the loop, the budget, and the safety story. ... The value is not in discovering something new on the first run. The value is in the infrastructure: the tree-search, the experiment sandbox, the writer-reviewer loop, the red-team report. The Sakana team documented sandbox-escape failures; your agent must pass the same red team.

## Concept · 概念

这个智能体是一棵最佳优先树搜索（best-first tree search）。节点是实验规约：(假设, 配置, 代码, 预期结果)。expand 步用小改动提出子节点（换优化器、移批大小、消融一个组件）。每个子节点在带硬性资源上限的全新沙箱里运行。结果回灌进一个按 (新颖度 × 质量 × 剩余预算) 给节点排序的打分函数。树长到预算耗尽，然后最好的分支被写出来。

写手是多模态的。它生成 LaTeX 草稿、编译、渲染图表，再把渲染出的 PDF 喂回 Claude Opus 4.7 的视觉模式，对排版、图表可读性和论断-证据一致性做批评。一个五评委 LLM 评审团给出 NeurIPS 风格分数（新颖性、严谨性、清晰度、可复现性、影响力）；若均分跌破阈值，论文带着批评意见回到写手。

安全是承重墙。每个实验在无网络出站、墙钟受限、资源上限钉死的 E2B 或 Daytona 沙箱里运行。智能体的代码生成步骤经过一个策略层，拦截逃逸沙箱的系统调用。红队报告复现 Sakana 记录的攻击面（fork 炸弹、文件系统逃逸、LLM 写出的网络调用）。

> The agent is a best-first tree search. Nodes are experiment specifications: (hypothesis, config, code, expected outcome). An expand step proposes children with small edits (swap optimizer, shift batch size, ablate a component). Each child runs in a fresh sandbox with a hard resource cap. Results feed back into a scoring function that ranks nodes by (novelty × quality × remaining budget). ... The writer is multimodal. It generates a LaTeX draft, compiles it, renders figures, and feeds the rendered PDF back into Claude Opus 4.7's vision mode for critique on layout, figure legibility, and claim-evidence alignment. ... Safety is load-bearing. Every experiment runs in an E2B or Daytona sandbox with no network egress, bounded wall-clock, and pinned resource limits. The agent's code-generation step passes through a policy layer that blocks syscalls that escape the sandbox.

## Architecture · 架构

```
seed idea + domain
      |
      v
  literature search (Semantic Scholar + OpenAlex + FAISS cache)
      |
      v
  LangGraph plan-execute-verify tree
      |
      v
  +--- expand node ----+      per-node sandbox
  |                    |      (E2B / Daytona)
  v                    v      resource caps
  child_1           child_k   no network egress
  |                    |      deterministic seeds
  v                    v
  run experiment       run experiment
  |                    |
  v                    v
  score nodes by (novelty, quality, budget)
      |
      v
  best branch -> LaTeX writer
      |
      v
  compile + vision critique (Opus 4.7 vision)
      |
      v
  reviewer ensemble (5 LLM judges, NeurIPS rubric)
      |
      v
  paper.pdf + review.md + trace.json
```

## Stack · 技术栈

- 编排：LangGraph，带 checkpoint 与人工审批门
- 树搜索：自实现的实验节点最佳优先搜索（Sakana v2 的 AB-MCTS 风格）
- 沙箱：每个实验一个 E2B，Docker-in-Docker 兜底；cgroups 做资源上限
- 文献：Semantic Scholar Graph API + OpenAlex + 本地 FAISS 摘要缓存
- 写手：LaTeX 模板 + Claude Opus 4.7（视觉模式）做图表批评与排版
- 评审：5 评委评审团（Opus 4.7、GPT-5.4、Gemini 3 Pro、DeepSeek R1、Qwen3-Max），加权聚合
- 实验框架：物理实验用 PyTorch 2.5，W&B 做记录
- 可观测性：Langfuse 记智能体 trace，每篇论文 $30 硬预算

> - Orchestration: LangGraph with checkpointing and human-approval gates
> - Tree search: custom best-first over experiment nodes (AB-MCTS-style from Sakana v2)
> - Sandbox: E2B per experiment, Docker-in-Docker fallback; resource caps via cgroups
> - Literature: Semantic Scholar Graph API + OpenAlex + local FAISS cache of abstracts
> - Writer: LaTeX template + Claude Opus 4.7 (vision mode) for figure critique and layout
> - Reviewer: ensemble of 5 judges (Opus 4.7, GPT-5.4, Gemini 3 Pro, DeepSeek R1, Qwen3-Max) with weighted aggregation
> - Experiment framework: PyTorch 2.5 for the physical experiments, W&B for logging
> - Observability: Langfuse for agent traces, $30 hard budget per paper

```figure
ce-experiment-tree
```

## Build It · 动手造

1. **种子与领域收窄。** 取一个种子想法（如「研究 sub-1B transformer 注意力图的稀疏模式」）。定义搜索空间：模型、数据集、算力预算。

2. **文献扫描。** 查询 Semantic Scholar + OpenAlex 拿到被引最多的 50 篇相关论文；摘要本地缓存；生成一页领域摘要。

3. **树脚手架。** 用种子假设初始化根节点。实现 `expand(node) -> children`，提案都是小改动（每个子节点只改一处配置）。实现 `score(node)` 为加权的新颖度 × 质量 × 预算项。

4. **沙箱包装。** 每个实验跑 `docker run --network=none --memory=8g --cpus=2 --pids-limit=256 --read-only`（或等价的 E2B 策略）。种子写进沙箱；输出以只读方式挂载回来。

5. **计划-执行-验证循环。** `plan` 提出子节点。`execute` 跑沙箱，抓取日志与指标。`verify` 对指标跑单元检查（loss 降了吗？消融隔离出效应了吗？）。失败节点在树上记录失败原因。

6. **写手。** 预算用完后选最佳分支。用 matplotlib 渲染图表。带着分支 trace 调用 Claude Opus 4.7 生成 LaTeX 草稿。编译。把编译出的 PDF 喂回 Opus 4.7 视觉模式做批评。迭代。

7. **评审团。** 五个评委按（新颖性、严谨性、清晰度、可复现性、影响力）以 NeurIPS 风格 rubric 打分。均分 < 4.0/5 就带着批评回到写手。重写 3 次后硬停。

8. **红队。** 构建或集成一组针对沙箱的对抗任务：fork 炸弹、网络外传尝试、文件系统逃逸、LLM 写出的 shell 元字符。确认全部被拦截。写下发现。

9. **可复现性。** 每篇论文附带树搜索 trace JSON、种子、W&B run 链接、沙箱配置，以及一个端到端复现的 README。

> **Seed and domain scoping.** Take a seed idea (e.g., "investigate sparsity patterns in attention maps of sub-1B transformers"). Define the search space: models, datasets, compute budget. ... **Tree scaffolding.** Initialize the root with the seed hypothesis. Implement `expand(node) -> children` with small-edit proposals (one config change per child). Implement `score(node)` as a weighted novelty × quality × budget term. ... **Sandbox wrapping.** Every experiment runs `docker run --network=none --memory=8g --cpus=2 --pids-limit=256 --read-only` (or the equivalent E2B policy). ... **Plan-execute-verify loop.** `plan` proposes children. `execute` runs the sandbox, captures logs and metrics. `verify` runs unit checks on metrics (did the loss decrease? did the ablation isolate the effect?). ... **Red team.** Build or integrate a set of adversarial tasks targeting the sandbox: fork bombs, network exfiltration attempts, filesystem escapes, LLM-written shell metacharacters. Confirm all are blocked.

## Use It · 实战用法

```
$ ai-scientist run --seed "attention sparsity in sub-1B transformers" --budget 30
[lit]    50 papers, digest in 12s
[tree]   expanded 8 nodes, budget 12/30
[exec]   node #3 sparsity=top-8, loss=2.83 (best so far)
[exec]   node #6 sparsity=top-4, loss=3.12 (worse)
[exec]   ...
[tree]   chose branch rooted at node #3 (novelty 0.62, quality 0.81)
[write]  LaTeX draft v1 complete
[vision] critique: figure 2 legend too small, claim-evidence ok
[write]  draft v2 after 3 edits
[review] mean 4.2/5 (novelty 3.9, rigor 4.3, clarity 4.1, repro 4.5, impact 4.2)
[done]   paper.pdf + review.md + trace.json     $28.40 spent
```

## Ship It · 交付

`outputs/skill-ai-scientist.md` 是交付物。给定种子想法 + 领域 + $30 预算，它跑完整条管线，产出一篇可评审的论文和一个可复现包。

| 权重 | 标准 | 如何衡量 |
|:-:|---|---|
| 25 | 论文质量 | 对已发表 workshop 论文做盲评 rubric 评审 |
| 20 | 实验严谨性 | 基线、种子、消融；每条论断都有结果表中的格子支撑 |
| 20 | 成本与算力纪律 | $30/篇上限被强制执行，Langfuse 可溯源 |
| 20 | 安全性 | 沙箱红队通过；网络策略与 kill-switch 验证过 |
| 15 | 可复现性 | 相同种子一条命令重跑即复现论文 |
| **100** | | |

> `outputs/skill-ai-scientist.md` is the deliverable. Given a seed idea + a domain + a $30 budget, it runs the full pipeline and emits a reviewable paper plus a reproducibility bundle.

## Exercises · 练习

1. 在同一领域对三个不同种子想法跑管线。比较树搜索哪些部分重叠。找出重复浪费的算力。

2. 在实验执行前，给预估成本超过 $5 的节点加一个人工在环（human-in-the-loop）门。测总成本降多少。

3. 把评审团换成单一评委。在一组已知劣质论文的留出集上测误接受率。

4. 引入网络外传红队测试：智能体写出尝试 `curl` 外部地址的代码。确认 `--network=none` 策略拦截它。记录尝试。

5. 把你的树搜索与平坦随机基线对比（同预算，无扩展策略）。报告新颖度 × 质量增益。

> Run the pipeline against three different seed ideas in the same domain. Compare which parts of the tree-search overlap. Identify duplicated wasted compute. ... Add a human-in-the-loop gate before experiment execution for nodes estimated above $5. Measure how much total cost drops. ... Swap the reviewer ensemble for a single judge. Measure the false-accept rate on a held-out set of known-bad papers. ... Introduce a network-exfiltration red team test: agent writes code that tries to `curl` an external address. Confirm the `--network=none` policy blocks it. ... Compare your tree-search with a flat random baseline (same budget, no expansion strategy). Report the novelty × quality gain.

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|------------------------|
| Tree search（树搜索） | 「AB-MCTS 式扩展」 | 在实验节点上做最佳优先探索，打分为新颖度×质量×预算 |
| Sandbox（沙箱） | 「实验隔离」 | 无网络、CPU/内存受限、种子钉死、输入只读的容器 |
| Vision critique（视觉批评） | 「先渲染再读」 | 把论文编译成 PDF，喂回 VLM 做排版与论断-证据批评 |
| Reviewer ensemble（评审团） | 「自动同行评审」 | 多个 LLM 评委按 NeurIPS rubric 给论文打分；加权聚合门控管线 |
| Novelty score（新颖度分） | 「这新吗？」 | 惩罚与 50 篇文献缓存过近的启发式 |
| Cost ceiling（成本上限） | 「$ 预算」 | 每篇论文总花费的硬上限；Langfuse 计数器 + 预跑估算 |
| Red team（红队） | 「沙箱逃逸审计」 | 若策略有误就能逃出沙箱的对抗任务 |

## Further Reading · 延伸阅读

- [Sakana AI-Scientist-v2 repository](https://github.com/SakanaAI/AI-Scientist-v2) — 参考级生产研究智能体
- [Sakana AI-Scientist-v1 paper (arXiv:2408.06292)](https://arxiv.org/abs/2408.06292) — 原始方法论
- [ShinkaEvolve (Sakana ICLR 2026)](https://sakana.ai) — 演化式扩展
- [Agent Laboratory (AMD)](https://github.com/SamuelSchmidgall/AgentLaboratory) — 多角色研究实验室框架
- [LangGraph documentation](https://langchain-ai.github.io/langgraph/) — 参考编排层
- [Semantic Scholar Graph API](https://api.semanticscholar.org/) — 文献检索
- [E2B sandboxes](https://e2b.dev) — 参考实验隔离
- [NeurIPS reviewer guidelines](https://neurips.cc/Conferences/2026/ReviewerGuidelines) — 评审团所编码的 rubric
