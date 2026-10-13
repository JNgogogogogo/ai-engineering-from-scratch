# Skill Libraries and Lifelong Learning (Voyager) · 技能库与终身学习（Voyager）

> Voyager (Wang et al., TMLR 2024) treats executable code as a skill. Skills are named, retrievable, composable, and refined by environment feedback. This is the reference architecture for Claude Agent SDK skills, skillkit, and the 2026 skill-library pattern.

**Type:** Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 07 (MemGPT), Phase 14 · 08 (Letta Blocks)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 说出 Voyager 的三个组件——自动课程（automatic curriculum）、技能库（skill library）、迭代提示机制（iterative prompting）——以及各自的角色
- 解释为什么 Voyager 把动作空间设为代码，而不是原语命令
- 用 stdlib 实现一个技能库：注册、检索、组合、失败驱动的打磨
- 把 Voyager 的模式对应到 2026 年的 Claude Agent SDK skills 和 skillkit 生态

> Name Voyager's three components — automatic curriculum, skill library, iterative prompting — and the role of each.
> Explain why Voyager makes the action space code, not primitive commands.
> Implement a stdlib skill library with registration, retrieval, composition, and failure-driven refinement.
> Map Voyager's pattern onto the 2026 Claude Agent SDK skills and the skillkit ecosystem.

## The Problem · 问题在哪

每个会话都从零重建全部能力的 agent 有三个毛病：

1. **浪费 token。** 每个任务都要重新引出同样的推理。
2. **丢掉进度。** 在会话 A 里学到的纠正传不到会话 B。
3. **搞不定长程组合。** 复杂任务需要能力层级；一次性 prompt 表达不了。

Voyager 的答案：把每个可复用的能力当作一段有名字的代码存进技能库，按相似度可检索、能与其他技能组合、并由执行反馈打磨。

> 1. **Waste tokens.** Every task re-elicits the same reasoning.
> 2. **Lose progress.** A correction learned in session A doesn't transfer to session B.
> 3. **Fail on long-horizon composition.** Complex tasks need capability hierarchies; one-shot prompts cannot express them.
> Voyager's answer: treat each reusable capability as a named chunk of code stored in a library, retrievable by similarity, composable with other skills, and refined by execution feedback.

## The Concept · 概念

### Three components · 三个组件

Voyager（arXiv:2305.16291）把 agent 组织成三部分：

1. **自动课程（automatic curriculum）。** 一个好奇心驱动的提议器，根据 agent 当前的技能集和环境状态挑选下一个任务。探索是自底向上的。
2. **技能库（skill library）。** 每个技能是一段可执行代码。任务成功时新增技能。技能按「查询与描述的相似度」检索。
3. **迭代提示机制（iterative prompting mechanism）。** 失败时，agent 拿到执行错误、环境反馈和自我验证输出，然后打磨这个技能。

Minecraft 评测（Wang et al., 2024）：对比基线，独特物品多 3.3 倍、石制工具快 8.5 倍、铁制工具快 6.4 倍、地图穿越远 2.3 倍。这些数字是 Minecraft 特定的，但模式可以迁移。

> **Skill library.** Each skill is executable code. New skills are added when a task succeeds. Skills are retrieved by query-to-description similarity.
> The Minecraft evaluation (Wang et al., 2024): 3.3x more unique items, 8.5x faster stone tools, 6.4x faster iron tools, 2.3x longer map traversal versus baselines. The numbers are Minecraft-specific, but the pattern transfers.

### Action space = code · 动作空间即代码

大多数 agent 发出的是原语命令。Voyager 发出的是 JavaScript 函数。一个技能长这样：

```
async function craftIronPickaxe(bot) {
  await mineIron(bot, 3);
  await mineStick(bot, 2);
  await placeCraftingTable(bot);
  await craft(bot, 'iron_pickaxe');
}
```

由子技能组合而成。以描述和 embedding 为键存储。作为程序检索，而不是作为 prompt。

这就是 2026 年的 Claude Agent SDK 技能：一段有名字、可检索的代码加说明，agent 按需加载。

> Most agents emit primitive commands. Voyager emits JavaScript functions.
> Composed from sub-skills. Stored keyed on description and embedding. Retrieved as a program, not a prompt.
> This is the 2026 Claude Agent SDK skill: a named, retrievable chunk of code plus instructions the agent loads on demand.

### Skill retrieval · 技能检索

新任务：「做一把钻石镐」。agent 的动作：

1. 把任务描述向量化。
2. 向技能库查询 top-k 相似技能。
3. 检索出 `craftIronPickaxe`、`mineDiamond`、`placeCraftingTable` 等。
4. 用检索到的原语 + 新逻辑组合出新技能。

这就是 MCP 资源（Phase 13）和 Agent SDK skills 实现的那个模式：在一个知识/代码面上做检索，范围限定在当前任务。

> New task "make a diamond pickaxe." Agent: 1. Embeds the task description. 2. Queries the skill library for top-k similar skills. 3. Retrieves `craftIronPickaxe`, `mineDiamond`, `placeCraftingTable` etc. 4. Composes the new skill from retrieved primitives + new logic.
> This is the pattern MCP resources (Phase 13) and Agent SDK skills implement: retrieval over a knowledge/code surface, scoped to the current task.

### Iterative refinement · 迭代打磨

Voyager 的反馈回路：

1. agent 写一个技能。
2. 技能对着环境运行。
3. 三种信号之一返回：`success`（成功）、`error`（错误，带堆栈）、`self-verification failure`（自我验证失败）。
4. agent 以该信号为上下文重写技能。
5. 循环，直到成功或达到最大轮数。

这就是 Self-Refine（Lesson 05）用到代码生成上、由环境锚定的验证。CRITIC（Lesson 05）是同一个模式，只是把验证器换成了外部工具。

> Voyager's feedback loop: 1. Agent writes a skill. 2. Skill runs against the environment. 3. One of three signals returns: `success`, `error` (with stack trace), `self-verification failure`. 4. Agent rewrites the skill using the signal as context. 5. Loop until success or max rounds.
> This is Self-Refine (Lesson 05) applied to code generation with environment-grounded verification. CRITIC (Lesson 05) is the same pattern with external tools as the verifier.

### Curriculum and exploration · 课程与探索

Voyager 的课程模块会根据 agent 已有什么、还没做什么，提出「在湖边造一个庇护所」这样的任务。提议器用环境状态 + 技能清单，挑一个刚好略高于当前能力的任务——探索的甜蜜点。

对生产 agent 来说，这翻译成一个「还缺什么」算子：给定当前技能库和某个领域，我们还没覆盖哪些技能？团队通常以课程评审（curriculum review）的形式手工实现它。

> The proposer uses the environment state + skill inventory to pick a task just above current capability — the exploration sweet spot.
> For production agents this translates to a "what's missing" operator: given the current skill library and a domain, what skills are we not yet covering? Teams typically implement this manually as curriculum review.

### Where this pattern goes wrong · 这个模式哪里会出错

- **技能库腐烂。** 同一个技能带着略有不同的描述被加了 10 次。写入时做去重；检索只返回一个。
- **组合技能漂移。** 父技能依赖的子技能后来被打磨过。给技能做版本管理；钉在 v1 的父技能不会神奇地自动升到 v3。
- **检索质量。** 技能库长到几百条之后，对技能描述做向量检索会退化。用标签过滤和硬约束来补充（「只要 `category=tooling` 的技能」）。

```figure
voyager-skills
```

> **Skill library rot.** Same skill added 10 times with slightly different descriptions. Add deduplication on write; retrieval returns only one.
> **Composed-skill drift.** Parent skill depends on a child that was refined. Version skills; a parent pinned to v1 doesn't magically pick up v3.
> **Retrieval quality.** Vector retrieval over skill descriptions degrades as the library grows past a few hundred. Supplement with tag filters and hard constraints ("only skills with `category=tooling`").

## Build It · 动手造

`code/main.py` 实现一个 stdlib 技能库：

- `Skill` — 名字、描述、代码（字符串形式）、版本、标签、依赖。
- `SkillLibrary` — 注册、搜索（词元重叠）、组合（依赖的拓扑排序）、打磨（更新时版本号递增）。
- 一个脚本化的 agent：注册三个原语技能、组合出第四个、撞上一次失败、然后打磨。

运行：

```
python3 code/main.py
```

轨迹展示了库写入、检索、组合、一次失败的执行和一个 v2 打磨——Voyager 回路端到端跑通。

> The trace shows library writes, retrieval, composition, a failed execution, and a v2 refinement — Voyager's loop end to end.

## Use It · 实战用法

- **Claude Agent SDK skills**（Anthropic）— 2026 年的参照物：每个技能有描述、代码和说明；在 agent 会话中按需加载。
- **skillkit**（npm: skillkit）— 面向 32+ 个 AI 编码 agent 的跨 agent 技能管理。
- **自建技能库** — 领域专用（数据 agent 的 SQL 技能、基础设施 agent 的 Terraform 技能）。Voyager 模式可以等比缩小。
- **OpenAI Agents SDK `tools`** — 低配版；每个工具就是一个轻量技能。

> **Claude Agent SDK skills** (Anthropic) — the 2026 reference: each skill has a description, code, and instructions; loaded on demand during an agent session.
> **skillkit** (npm: skillkit) — cross-agent skill management for 32+ AI coding agents.
> **Custom skill libraries** — domain-specific (SQL skills for data agents, Terraform skills for infra agents). The Voyager pattern scales down.
> **OpenAI Agents SDK `tools`** — at the low end; each tool is a lightweight skill.

## Ship It · 交付

`outputs/skill-skill-library.md` 生成一个 Voyager 形状的技能库，为任意目标运行时接好注册、检索、版本管理和打磨。

> `outputs/skill-skill-library.md` generates a Voyager-shaped skill library with registration, retrieval, versioning, and refinement wired in for any target runtime.

## Exercises · 练习

1. 给 `compose()` 加一个依赖环检测器。当技能 A 依赖 B、B 又依赖 A 时会发生什么？报错还是警告？
2. 实现按技能的版本钉扎（version pinning）。当父技能组合 `crafting@1` 时，对 `crafting@2` 的打磨不能悄悄升级父技能。
3. 把词元重叠检索换成 sentence-transformers embedding（或者 stdlib 实现的 BM25）。在一个 50 技能的玩具库上测 retrieval@5。
4. 加一个「课程」agent：给定当前技能库和一段领域描述，提出 5 个缺失的技能。每周调用一次。
5. 读 Anthropic 的 Claude Agent SDK 技能文档。把玩具库移植成 SDK 的技能 schema。可发现性会有什么变化？

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| Skill（技能） | 「可复用能力」 | 有名字的代码块 + 描述，可按相似度检索 |
| Skill library（技能库） | 「agent 的 know-how 记忆」 | 技能的持久存储，可搜索、可组合 |
| Curriculum（课程） | 「任务提议器」 | 由当前能力缺口驱动的自底向上目标生成器 |
| Composition（组合） | 「技能 DAG」 | 技能调用技能；执行时做拓扑排序 |
| Iterative refinement（迭代打磨） | 「自我修正回路」 | 环境反馈 + 错误 + 自我验证回卷进下一个版本 |
| Action-space-as-code | 「程序化动作」 | 对时间上延展的行为，发函数而不是原语命令 |
| Dedup on write（写入去重） | 「技能塌缩」 | 近重复的描述塌缩成一个规范技能 |

## Further Reading · 延伸阅读

- [Wang et al., Voyager (arXiv:2305.16291)](https://arxiv.org/abs/2305.16291) —— 技能库的开山论文
- [Claude Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview) —— 技能作为 2026 年的产品化形态
- [Anthropic, Building agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk) —— 技能与子 agent 实战
- [Madaan et al., Self-Refine (arXiv:2303.17651)](https://arxiv.org/abs/2303.17651) —— Voyager 底层的打磨回路
