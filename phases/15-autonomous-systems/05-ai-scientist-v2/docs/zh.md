# AI Scientist v2 — Workshop-Level Autonomous Research · AI Scientist v2——研讨会级别的自主研究

> Sakana 的 AI Scientist v2（Yamada 等，arXiv:2504.08066）跑通了完整的研究循环：假设、代码、实验、图表、写作、投稿。它是第一个「生成的论文通过 ICLR 2025 研讨会同行评审」的系统。独立评估（Beel 等）发现 42% 的实验因编码错误而失败，而且文献综述经常把已有概念错标为新颖。Sakana 自己的文档警告说这个代码库会执行 LLM 写的代码，并建议用 Docker 隔离。这幅图景的两半都是重点。

> Sakana's AI Scientist v2 (Yamada et al., arXiv:2504.08066) runs the full research loop: hypothesis, code, experiments, figures, writeup, submission. It is the first system to have a generated paper pass peer review at an ICLR 2025 workshop. Independent evaluation (Beel et al.) found 42% of experiments failed from coding errors and literature review frequently mislabeled established concepts as novel. Sakana's own docs warn that the codebase executes LLM-written code and recommend Docker isolation. Both halves of that picture are the point.

**类型：** Learn（学习）
**语言：** Python（仅 stdlib，research-loop 状态机玩具实现）
**先修：** Phase 15 · 03（AlphaEvolve）、Phase 15 · 04（DGM）
**时间：** ~60 分钟

## The Problem · 问题在哪

研究是一个开放式任务。不像 AlphaEvolve 的算法搜索，也不像 DGM 被基准框住的自我修改，一个研究结果并没有机器可判定的正确性标准。论文由审稿人评判，而不是单元测试。这让循环更难闭合——而一旦闭合也更有价值，因为研究正是复利式进步所在的地方。

AI Scientist v1（Sakana，2024）通过从人类撰写的模板出发来闭合循环。LLM 在固定的脚手架内填充实验。AI Scientist v2（Yamada 等，2025）用带视觉-语言模型（VLM）点评循环的 agentic 树搜索，移除了模板要求。系统生成想法、实现实验、产出图表、撰写论文，并根据审稿反馈迭代。

同行评审的判定：一篇 v2 生成的论文被 ICLR 2025 研讨会接收（做了披露）。独立评估的判定：这个系统远谈不上可靠。两者都是真的。

> Research is an open-ended task. Unlike AlphaEvolve's algorithmic search or DGM's benchmark-bounded self-modification, a research result does not have a machine-checkable correctness criterion. A paper is judged by reviewers, not unit tests. That makes the loop harder to close — and more valuable if closed, because research is where compounding progress lives.
> AI Scientist v1 (Sakana, 2024) closed the loop by starting from human-authored templates. The LLM filled in experiments within a fixed scaffolding. AI Scientist v2 (Yamada et al., 2025) removes the template requirement by using agentic tree search with a vision-language model critique loop. The system generates ideas, implements experiments, produces figures, writes a paper, and iterates on reviewer feedback.
> Peer review verdict: one v2-generated paper was accepted at an ICLR 2025 workshop (with disclosure). Independent evaluation verdict: the system is far from reliable. Both are true.

## The Concept · 概念

### The architecture · 架构

1. **想法生成。** LLM 在一个主题和已有文献的条件下提出研究想法。v1 用模板；v2 在假设空间上做 agentic 搜索。
2. **新颖性检查。** 文献检索步骤检查这个想法是否已被发表。Beel 等的评估正是在这一步发现了错标——已有方法经常被归为新颖。
3. **实验计划。** 智能体起草实验协议并编写代码。
4. **执行。** 代码在沙箱里运行。失败被回馈进重试循环。在 Beel 等的测量中，42% 的实验在这一阶段因编码错误而失败。
5. **图表生成。** 一个视觉-语言模型读取生成的图表，并改写它们以提升清晰度。这是 v2 的关键技术增量。
6. **写作。** LLM 起草论文，与一个内部审稿人迭代。
7. **可选：投稿。** 论文被投到一个会议。

> 1. **Idea generation.** The LLM proposes research ideas conditioned on a topic and prior literature. v1 used templates; v2 uses agentic search over a space of hypotheses. 2. **Novelty check.** A literature retrieval step checks whether the idea has been published. This is the step where Beel et al.'s evaluation found mislabeling — established methods frequently classified as novel. 3. **Experiment plan.** The agent drafts an experimental protocol and writes code. 4. **Execution.** Code runs in a sandbox. Failures are fed back into a retry loop. In Beel et al.'s measurements, 42% of experiments failed from coding errors at this stage. 5. **Figure generation.** A vision-language model reads generated figures and rewrites them for clarity. This was v2's key technical addition. 6. **Writeup.** The LLM drafts a paper, iterates with an internal reviewer. 7. **Optional: submission.** The paper is submitted to a venue.

### What the workshop-acceptance result means · 研讨会接收这个结果意味着什么

一篇 v2 生成的论文通过了 ICLR 2025 研讨会的同行评审。作者向程序委员会披露了论文的来源。这个接收是一个数据点；它不是宣称「这个系统会做研究」的许可证。

重要的背景：研讨会论文的门槛低于主会论文。同行评审是有噪声的；任何时候都只有一小部分投稿被接收。一次成功是概念验证，不是可靠性声明。Nature 2026 论文记录了端到端循环，而且它本身是由人类研究者共同署名的；它并不是「系统写了一篇 Nature 论文」。

> One v2-generated paper passed peer review at an ICLR 2025 workshop. The authors disclosed the paper's origin to the program committee. The acceptance is a data point; it is not a license to claim the system "does research."
> Important context: workshop papers are a lower bar than main-conference papers. Peer review is noisy; a small fraction of submissions are accepted on any given day. One success is a proof of concept, not a reliability claim. The Nature 2026 paper documents the end-to-end loop and was itself co-authored by human researchers; it is not "the system wrote a Nature paper."

### What the independent evaluation found · 独立评估发现了什么

Beel 等（arXiv:2502.14297）做了一次外部评估。核心发现：

- **实验失败。** 42% 的实验因编码错误（坏的 import、形状不匹配、未定义变量）而失败。重试循环抓住了一部分，不是全部。
- **新颖性错标。** 文献检索步骤经常把已有概念标记为新颖。这是研究版的无中生有（幻觉）。
- **呈现质量落差。** VLM 图表点评产出了出版级的视觉效果，掩盖了底层的实验弱点。

最后一条发现对本阶段最重要。一个能产出令人信服的输出、却没有做令人信服的研究的系统，比一个明显失败的系统更危险，而不是更安全。评估必须触达底层主张，而不是停在图表上。

> Beel et al. (arXiv:2502.14297) ran an external evaluation. Headline findings: ... **Experiment failures.** 42% of experiments failed from coding errors (bad imports, shape mismatches, undefined variables). The retry loop caught some, not all. **Novelty mislabeling.** The literature-retrieval step frequently flagged established concepts as novel. This is the research equivalent of hallucination. **Presentation-quality gap.** The vision-language figure critique produced publication-grade visuals, masking underlying experimental weaknesses.
> The last finding is the important one for this phase. A system that produces convincing outputs without doing convincing research is more dangerous, not safer, than one that fails obviously. Evaluation must reach the underlying claims, not stop at the figure.

### The sandbox-escape concern · 沙箱逃逸之虞

Sakana 自己的仓库 README 警告（原文）：

> Due to the nature of this software, which executes LLM-generated code, we cannot guarantee safety. There are risks of dangerous packages, uncontrolled web access, and spawning of unintended processes. Use at your own risk and consider Docker isolation.

这就是无验证领域中自主性的运行形态。LLM 写代码；代码运行；代码能做这个进程被允许做的任何事。没有一个硬性限制文件系统、网络和进程动作的沙箱，任何自主导向的研究智能体都可以窃取数据、烧掉算力，或者改写它自己。

AlphaEvolve 的沙箱故事更容易讲，因为它的评估器很紧。AI Scientist v2 的循环以开放的目标运行开放的代码。这就是为什么它需要更强的隔离（Docker 是底线；首选 seccomp / gVisor），以及在每份投稿离开系统之前的人工审查。

> This is the operational shape of autonomy in an unverified domain. The LLM writes code; the code runs; the code can do anything the process is allowed to do. Without a sandbox that hard-limits filesystem, network, and process actions, any self-directed research agent can exfiltrate data, burn compute, or rewrite itself.
> AlphaEvolve's sandbox story is easier because its evaluator is tight. AI Scientist v2's loop runs open-ended code with open-ended goals. That is why it needs stronger isolation (Docker minimum; seccomp / gVisor preferred) and a manual review of every submission before it leaves the system.

### Where v2 sits in the frontier stack · v2 在前沿技术栈中的位置

| 系统 | 目标 | 输出形态 | 评估器 | 已知失败 |
|---|---|---|---|---|
| AlphaEvolve | 算法 | 代码 | 单元测试 + 基准 | 受评估器严格性约束 |
| DGM | 智能体脚手架 | 代码 | SWE-bench | reward hacking |
| AI Scientist v2 | 研究论文 | 文本 + 代码 + 图表 | 同行评审（弱） | 实验失败、错标、包装掩盖弱点 |

v2 拥有三者中最弱的自动评估器、最宽的输出面，以及通往公开产物的最短路径。运营性控制手段（沙箱、审查、披露）承担了大部分安全工作。

> | System | Target | Output kind | Evaluator | Known failure |
> |---|---|---|---|---|
> | AlphaEvolve | algorithms | code | unit + benchmark | bounded by evaluator rigor |
> | DGM | agent scaffolding | code | SWE-bench | reward hacking |
> | AI Scientist v2 | research papers | text + code + figures | peer review (weak) | experiment failures, mislabeling, polish masking weakness |
>
> v2 has the weakest automatic evaluator of the three, the widest output surface, and the shortest path to public artifacts. The operational controls (sandbox, review, disclosure) are doing most of the safety work.

```figure
mx-research-loop
```

## Use It · 实战用法

`code/main.py` 把 v2 循环模拟成一个状态机：想法 → 新颖性检查 → 实验 → 图表 → 写作 → 评审 → 接收或迭代。每个状态都有一个取自 Beel 等发现的可配置失败概率。把模拟器跑 N 轮并统计：

- 多少想法走到了投稿。
- 多少投稿带有「被漂亮图表掩盖的严重实验缺陷」。
- 重试预算如何在质量与产量之间权衡。

> `code/main.py` simulates the v2 loop as a state machine: idea → novelty check → experiment → figure → writeup → review → accept-or-iterate. Each state has a configurable failure probability pulled from the Beel et al. findings. Run the simulator for N loops and count how many ideas reach submission, how many submissions would have a critical experimental flaw the polished paper hides, and how retry budgets trade off quality vs yield.

## Ship It · 交付

`outputs/skill-ai-scientist-sandbox-review.md` 是一份两道闸门的审查清单，用于任何由研究循环智能体产出的东西在离开沙箱之前的把关。

> `outputs/skill-ai-scientist-sandbox-review.md` is a two-gate review checklist for anything produced by a research-loop agent before it leaves the sandbox.

## Exercises · 练习

1. 用默认参数运行 `code/main.py`。多大比例的循环运行产出「干净」的论文？多大比例产出的论文带有被图表点评粉饰过去的实验失败缺陷？

2. 默认参数已经使用了 Beel 等的 42% / 25%。用 `--experiment-failure 0.20 --novelty-mislabel 0.10` 重跑一次，再用 `--experiment-failure 0.60 --novelty-mislabel 0.40` 重跑一次。「看似漂亮但有缺陷」的份额在两次运行之间如何移动？

3. 读 Sakana 的 AI Scientist v2 仓库 README 中关于沙箱要求的部分。说出在一次多天自主运行中，你会额外施加的两种限制（Docker 之外）。

4. 读 Beel 等论文第 4 节关于呈现质量落差的内容。设计一个额外的评估器，用来抓住「看起来漂亮但实验上有缺陷」的论文。

5. 提出一个比「一个博士读每一篇论文」扩展性更好的人类审查协议，用于研究智能体的输出。找出瓶颈并围绕它做设计。

> 1. Run `code/main.py` with default parameters. What fraction of loop runs produce a "clean" paper? What fraction produce a paper with an experiment-failure flaw the figure critique polished over?
> 2. The defaults already use Beel et al.'s 42% / 25%. Re-run with `--experiment-failure 0.20 --novelty-mislabel 0.10` and then with `--experiment-failure 0.60 --novelty-mislabel 0.40`. How does the polished-but-flawed share shift between the two runs?
> 5. Propose a human-review protocol for research-agent outputs that scales better than "a PhD reads every paper." Identify the bottleneck and design around it.

## Key Terms · 术语表

| 术语 | 人们口头怎么说 | 它实际是什么意思 |
|---|---|---|
| AI Scientist v1 | 「Sakana 的模板化研究智能体」 | 把实验填充进一个固定脚手架 |
| AI Scientist v2 | 「无模板研究智能体」 | agentic 树搜索 + VLM 图表点评 |
| Agentic tree search | 「会分支的研究智能体」 | 并行展开多个实验计划；由内部评审剪枝 |
| Vision-language critique | 「图表上的 VLM 抛光」 | 多模态模型读取图表并改写以提升清晰度 |
| Literature retrieval | 「新颖性检查」 | 检索先前工作以确认想法的新颖性——有记录表明会错标 |
| Polish masking | 「论文漂亮，研究破碎」 | 呈现质量超过实验质量；掩盖弱点 |
| Sandbox escape | 「LLM 代码逃逸」 | 智能体执行的代码做了循环设计者没有打算让它做的事 |

> | Term | What people say | What it actually means |
> |---|---|---|
> | AI Scientist v1 | "Sakana's templated research agent" | Filled experiments into a fixed scaffold |
> | AI Scientist v2 | "Template-free research agent" | Agentic tree search with VLM figure critique |
> | Agentic tree search | "Branching research agent" | Expands multiple experiment plans in parallel; prunes by internal critic |
> | Vision-language critique | "VLM polish on figures" | Multimodal model reads figures and rewrites them for clarity |
> | Literature retrieval | "Novelty check" | Searches prior work to confirm idea novelty — documented to mislabel |
> | Polish masking | "Pretty paper, broken research" | Presentation quality exceeds experimental quality; hides weaknesses |
> | Sandbox escape | "LLM code breaks out" | Agent-executed code does things the loop designer did not intend |

## Further Reading · 延伸阅读

- [Yamada et al. (2025). The AI Scientist-v2](https://arxiv.org/abs/2504.08066) —— 论文。
- [Sakana blog on the Nature 2026 publication](https://sakana.ai/ai-scientist-nature/) —— 厂商摘要，含同行评审背景。
- [Beel et al. (2025). Independent evaluation of The AI Scientist](https://arxiv.org/abs/2502.14297) —— 外部评估数字。
- [Sakana AI Scientist v1 paper](https://arxiv.org/abs/2408.06292) —— 模板化的前身。
- [Anthropic — Measuring AI agent autonomy](https://www.anthropic.com/research/measuring-agent-autonomy) —— 对开放式研究智能体更宏观的框架表述。
