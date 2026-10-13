# Role Specialization — Planner, Critic, Executor, Verifier · 角色专业化——规划者、批评者、执行者、验证者

> 2026 年最常见的多智能体分解：一个智能体规划，一个执行，一个批评或验证。MetaGPT（arXiv:2308.00352）把它形式化为编码进角色提示词的 SOP——产品经理、架构师、项目经理、工程师、QA 工程师——遵循 `Code = SOP(Team)`。ChatDev（arXiv:2307.07924）让设计者、程序员、评审、测试员通过一条「聊天链」协作，并使用「沟通式去幻觉」（智能体显式索要缺失的细节）。验证者是承重角色：Cemri 等人（MAST，arXiv:2503.13657）表明每一个多智能体失败都能追溯到缺失或失效的验证。PwC 报告靠 CrewAI 中的结构化验证循环拿到了 7 倍精度提升（10% → 70%）。

> The most common multi-agent decomposition in 2026: one agent plans, one executes, one critiques or verifies. MetaGPT (arXiv:2308.00352) formalizes this as SOPs encoded into role prompts — Product Manager, Architect, Project Manager, Engineer, QA Engineer — following `Code = SOP(Team)`. ChatDev (arXiv:2307.07924) chains designer, programmer, reviewer, tester through a "chat chain" with "communicative dehallucination" (agents explicitly request missing details). The verifier is load-bearing: Cemri et al. (MAST, arXiv:2503.13657) show every multi-agent failure can be traced to missing or broken verification. PwC reported 7× accuracy gain (10% → 70%) from structured validation loops in CrewAI.

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 16 · 04 (Primitive Model), Phase 16 · 05 (Supervisor)
**Time:** ~60 minutes

---

## Problem · 问题

通用的多智能体系统产出通用的结果。三个程序员在群聊里写出同一种平庸代码的三个变体。你可以加更多智能体、加更多轮次，仍然跨不过质量门槛。

解法不是更多智能体——而是 *不同的* 智能体。分配不同的角色。给批评者规划者没有的工具。给验证者一套客观的测试套件。这样系统才拥有「带着落地修正的内部分歧」，而不只是并行的瞎猜。

> Generic multi-agent systems produce generic output. Three coders in a group chat write three flavors of the same mediocre code. You can add more agents, add more rounds, and still not cross the quality threshold. ... The fix is not more agents — it is *different* agents. Assign distinct roles. Give the critic tools the planner does not have. Give the verifier an objective test suite. Now the system has internal disagreement with grounded correction, not just parallel guessing.

---

## Concept · 概念

### The four canonical roles · 四个经典角色

**规划者（Planner）。** 读取目标，产出步骤列表或规格说明。工具：知识检索、文档。输出：结构化计划。

**执行者（Executor）。** 一次读取一个计划步骤，产出工件。工具：真正干活的工具（代码编译器、shell、API 客户端）。输出：工件。

**批评者（Critic）。** 对照规划者的意图审读执行者的输出。工具：对工件的只读访问、静态分析。输出：带理由的接受/拒绝。

**验证者（Verifier）。** 读取工件并运行确定性检查。工具：测试运行器、类型检查器、schema 校验器。输出：带证据的通过/失败。

批评者是主观的、有态度的、通常基于 LLM。验证者是客观的、确定性的、通常基于代码。它们不是同一个角色。

> **Planner.** Reads the goal, produces a step list or a spec. Tools: knowledge retrieval, docs. Output: structured plan. ... **Executor.** Reads one plan step at a time, produces the artifact. ... **Critic.** Reads the executor's output against the planner's intent. ... **Verifier.** Reads the artifact and runs a deterministic check. ... Critic is subjective, opinionated, often LLM-based. Verifier is objective, deterministic, often code-based. They are not the same role.

---

### MetaGPT's SOP pattern · MetaGPT 的 SOP 模式

MetaGPT（arXiv:2308.00352）把软件工程 SOP 编码成角色提示词：

- **产品经理（Product Manager）** 写 PRD。
- **架构师（Architect）** 产出系统设计。
- **项目经理（Project Manager）** 拆分任务。
- **工程师（Engineer）** 做实现。
- **QA 工程师（QA Engineer）** 跑测试。

每个角色都有严格的输入/输出 schema。角色提示词说明这个角色 *是什么*、*必须产出什么*。`Code = SOP(Team)` 这个表述——确定性 SOP 把一群 LLM 变成一条可预测的流水线。

> MetaGPT (arXiv:2308.00352) encodes software engineering SOPs as role prompts: **Product Manager** writes the PRD, **Architect** produces the system design, **Project Manager** splits tasks, **Engineer** implements, **QA Engineer** runs tests. ... Each role has a strict input/output schema. The role prompt says what the role *is* and what it *must produce*. The `Code = SOP(Team)` formulation — deterministic SOPs turn a team of LLMs into a predictable pipeline.

---

### ChatDev's communicative dehallucination · ChatDev 的沟通式去幻觉

ChatDev 加了一个关键动作：当执行者需要一个计划里没有的具体细节时，它显式地问设计者，然后再继续。这防止了 LLM 那个经典失败：一本正经地发明细节。

实现方式：角色提示词里写上「当你需要未被提供的具体信息时，先按名字问对应的角色，再产出输出」。

> ChatDev adds a key move: when an executor needs a specific detail that was not in the plan, it explicitly asks the designer before continuing. This prevents the classic LLM failure of plausibly inventing the detail. ... Implementation: the role prompt includes "when you need specific information you were not given, ask the relevant role by name before producing output."

---

### Why verifier matters most · 为什么验证者最重要

Cemri 等人（MAST）追踪了 1642 个多智能体执行失败。21.3% 是验证缺口——系统交付了一个没人检查过的答案。其余 79% 常常也能追溯到「有一个检查悄悄失败或从未运行」。验证是承重角色。

PwC 报告（CrewAI 部署，2025）加入结构化验证循环把精度从 10% 提到 70%。一个角色带来 7 倍收益。

> Cemri et al. (MAST) traced 1642 multi-agent execution failures. 21.3% were verification gaps — the system shipped an answer no one had checked. The remaining 79% often trace back to "there was a check that failed silently or was never run." Verification is the load-bearing role. ... PwC reported (CrewAI deployments, 2025) that adding a structured validation loop moved accuracy from 10% to 70%. 7× gain from one role.

---

### Critic vs verifier · 批评者 vs 验证者

- 批评者是审读工件质量的 LLM。主观。可能被貌似合理的行文骗过。
- 验证者是在工件上运行的确定性程序。客观。给出带证据的通过/失败。

两个都用。批评者抓住验证者说不出口的品味问题。验证者抓住批评者看不见的 bug，因为那些 bug 只在运行时暴露。

> A critic is an LLM reviewing an artifact for quality. Subjective. Can be fooled by plausible prose. ... A verifier is a deterministic program running on the artifact. Objective. Gives pass/fail with evidence. ... Use both. Critic catches taste issues the verifier cannot articulate. Verifier catches bugs the critic cannot see because they show up only at runtime.

---

### The anti-pattern · 反模式

你系统里的每个角色都是 LLM，每个角色的输出都是「我觉得没问题」。经典的 MAST 失败模式。至少加一个通过/失败由代码而非 LLM 决定的验证者。

> Every role in your system is an LLM and every role's output is "looks good to me." Classic MAST failure mode. Add at least one verifier whose pass/fail is decided by code, not by an LLM.

---

### Framework mappings · 框架映射

- **CrewAI** —— `Agent(role, goal, backstory)` 是教科书式的专业化接口。
- **LangGraph** —— 节点可以有专门的提示词；边负责强制流水线顺序。
- **AutoGen** —— GroupChat 里用单词命名的角色化 ConversableAgent。
- **OpenAI Agents SDK** —— 角色专门化 Agent 之间的交接（handoff）工具。

```figure
swarm-roles
```

> **CrewAI** — `Agent(role, goal, backstory)` is the textbook specialization surface. ... **LangGraph** — nodes can have specialized prompts; edges enforce the pipeline. ... **AutoGen** — role-specific ConversableAgents with one-word names in a GroupChat. ... **OpenAI Agents SDK** — handoff tools between role-specialized Agents.

---

## Build It · 动手造

`code/main.py` 实现一个构建简单 Python 函数的 4 角色流水线：

- **规划者** 产出规格说明。
- **执行者** 生成代码字符串。
- **批评者**（模拟 LLM）标记明显问题。
- **验证者** 在沙箱（`exec`）里对测试用例运行生成的代码。

演示跑两遍：一遍执行者产出正确的代码（批评者和验证者都通过），一遍执行者产出偏离规格的代码（批评者漏掉 bug 因为它看起来合理，验证者抓住它因为测试失败）。

Run:

```
python3 code/main.py
```

> `code/main.py` implements a 4-role pipeline building a simple Python function: **Planner** produces a spec, **Executor** generates a code string, **Critic** (LLM-simulated) flags obvious issues, **Verifier** runs the generated code in a sandbox (`exec`) against a test case. ... Demo runs twice: once where the executor produces correct code (critic + verifier both pass), once where the executor produces off-spec code (critic misses the bug because it looks plausible, verifier catches it because the test fails).

---

## Use It · 实战用法

`outputs/skill-role-designer.md` 接收一个任务，产出角色名册（3-5 个角色）、每个角色的输入/输出 schema，以及验证者检查。在把智能体接进框架之前先用它。

> `outputs/skill-role-designer.md` takes a task and produces the role roster (3-5 roles), the input/output schema per role, and the verifier check. Use this before wiring agents into a framework.

---

## Ship It · 交付

检查清单：

- **至少一个确定性验证者。** 永远不要全是 LLM。
- **每个角色显式 I/O schema。** 规划者返回规格，不是散文；执行者读取这个 schema。
- **沟通式去幻觉。** 信息缺失时执行者必须问规划者；永远不要自己编。
- **批评者/验证者顺序。** 先跑批评者（便宜，抓设计问题），再跑验证者（慢，抓 bug）。
- **循环预算。** 升级给人类之前，最多 2 轮批评者-执行者修订。

> Checklist: ... **At least one deterministic verifier.** Never all-LLM. ... **Explicit I/O schema per role.** The planner returns a spec, not prose; the executor reads that schema. ... **Communicative dehallucination.** Executor must ask the planner when info is missing; never invent it. ... **Critic/verifier ordering.** Run critic first (cheap, catches design issues), verifier second (slow, catches bugs). ... **Loop budget.** Max 2 critic-executor revision rounds before escalating to human.

---

## Exercises · 练习

1. 跑 `code/main.py`，观察验证者如何抓住批评者漏掉的 bug。加一个静态分析检查（统计 `return` 出现的次数）作为额外验证者。它能抓住运行时测试漏掉的什么？
2. 加第 5 个角色：「需求分析师」，把用户愿望翻译成规划者可用的规格。哪些沟通式去幻觉请求应该流向它？
3. 读 MetaGPT 第 3 节（「Agents」）。列出 MetaGPT 5 个角色各自的输入/输出 schema。
4. 读 ChatDev 的聊天链图（arXiv:2307.07924 图 3）。找出沟通式去幻觉在哪里打破了一个原本无限的循环。
5. PwC 的 7 倍精度提升来自验证循环。假设三种加了验证者也没帮助的任务——确定性正确性检查不可能或昂贵到不可行的场景。

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| Role specialization | 「不同智能体，不同工种」 | 为规划者/执行者/批评者/验证者角色分别调校的不同系统提示词。 |
| SOP pattern | 「编码好的标准操作流程」 | MetaGPT 的框架：每个角色严格的 I/O schema 把团队变成流水线。 |
| Communicative dehallucination | 「先问再编」 | ChatDev 模式：细节缺失时执行者问规划者，而不是自己编一个。 |
| Critic | 「LLM 评审」 | 主观、有态度的评审。抓品味问题。可能被貌似合理的行文骗过。 |
| Verifier | 「确定性检查」 | 基于代码的通过/失败。测试运行器、类型检查器、schema 校验器。骗不过。 |
| Verification gap | 「没人检查」 | MAST 失败的 21.3%。答案交付时缺一个本可抓住 bug 的检查。 |
| Revision loop | 「批评者打回去」 | 批评者拒绝触发执行者带反馈重跑。需要预算。 |
| All-LLM anti-pattern | 「我觉得没问题」 | 每个角色都是 LLM，没有确定性检查。经典 MAST 失败。 |

---

## Further Reading · 延伸阅读

- [Hong et al. — MetaGPT: Meta Programming for Multi-Agent Collaboration](https://arxiv.org/abs/2308.00352) —— 「SOP 即角色提示词」的参考论文
- [Qian et al. — Communicative Agents for Software Development (ChatDev)](https://arxiv.org/abs/2307.07924) —— 聊天链 + 沟通式去幻觉
- [Cemri et al. — Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) —— MAST 分类法；验证缺口占失败的 21.3%
- [CrewAI docs — Agent roles](https://docs.crewai.com/en/introduction) —— 生产级角色规格接口
