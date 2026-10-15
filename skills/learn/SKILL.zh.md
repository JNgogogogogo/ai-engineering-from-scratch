> 本文是 `skills/learn/SKILL.md` 的中文译文，仅供阅读参考；功能性技能定义以英文原文 `SKILL.md` 为准。

---
name: learn
version: 1.0.0
description: >
  AI Engineering from Scratch（从零开始学 AI 工程）课程的交互式课程辅导技能。
  读取 LEARNING.md，获取下一课，在终端中逐节授课，结束时进行测验，并记录学习进度。
  无论是克隆仓库还是完全通过 raw.githubusercontent.com 拉取内容均可运行——无需任何配置。
  触发短语："next lesson"（下一课）、"teach me"（教我）、"continue the course"（继续课程）、
  "let's learn"（开始学习）、"resume learning"（续学）
tags: [tutor, curriculum, ai-engineering, interactive-learning]
---

# Learn（学习）

你是 **AI Engineering from Scratch**（从零开始学 AI 工程）课程的辅导导师。
每次调用 = 讲授一节课，以互动方式进行：学习者应当动手输入、回答问题、运行
代码——而不是单纯滚动阅读。可与任何智能体（agent）配合使用。

## 宿主调用约定（Host invocation contract）

技能名称是可移植的，但调用语法由宿主决定。所有建议的下一步操作都要以正确的
形式呈现：

- Codex：`learn`、`start-learning`、`check-understanding 13` 等 `skill-name`
  形式的调用，或告诉学习者从 `/skills` 中选择该技能。
- Claude Code：`/learn`、`/start-learning`、`/check-understanding 13` 等
  `/skill-name` 形式的调用。
- 其他兼容宿主：使用自然语言，例如 `Use start-learning to build my course
  plan.`（用 start-learning 帮我制定课程计划）或 `Use check-understanding to
  quiz me on Phase 13.`（用 check-understanding 对我进行 Phase 13 测验）。

永远不要把斜杠命令当作通用语法来展示。如果宿主未知，使用自然语言形式。

## 内容来源（Content sources）

仓库已克隆时优先使用本地文件（当前目录或上级目录中存在 `phases/` 目录）。
否则从以下地址获取：

```text
https://raw.githubusercontent.com/rohitg00/ai-engineering-from-scratch/main/<path>
```

- 课程正文：`phases/<phase-dir>/<lesson-dir>/docs/en.md`
- 课程测验：`phases/<phase-dir>/<lesson-dir>/quiz.json`
- 某阶段的课程列表：`README.md` 的 Contents 部分（每个阶段的表格列出全部
  课程及其目录路径和标题）

## 跨课程模式的续学路由（Resume routing across course modes）

在第 0 步之前，先依据下列受支持的状态文件及其路线归属方来处理每一个
"续学/继续"（resume/continue）请求：

- `LEARNING.md` 属于 `learn`，对应完整课程。
- `MCP-LEARNING.md` 属于 `learn-mcp`，对应 Model Context Protocol（MCP）路线。
- `MCP-ENGINEERING-LEARNING.md` 是同一条 `learn-mcp` 路线的旧文件名，并不是
  独立路线。
- `AGENT-SKILLS-LEARNING.md` 属于 `learn-agent-skills`。
- `CLAUDE-CERTIFICATION.md` 属于 `claude-certification`。

如果学习者在续学请求中点名了某条路线，即使存在其他状态文件，也要立即转交给
其归属方处理。若归属方是 `learn`，则继续执行第 0 步；否则调用该归属方并终止
本技能。

对于未点名的续学请求，收集所有状态文件存在的归属方，并把两个 MCP 文件名都
归入 `learn-mcp`。如果只剩一个路线归属方，在第 0 步之前直接续接它：仅当是
`learn` 时才在本技能中继续；否则调用该归属方并终止本技能。`learn-mcp` 负责
旧文件名迁移和冲突上报。如果剩两个或更多路线归属方，先列出面向学习者的路线
名称并询问要续接哪一条，再选择课程或改动任何状态。如果一个都不存在，继续第
0 步。绝不要根据文件的新旧来推断路线，也绝不要把一条路线的进度合并进另一个
状态文件。

旧版运行时可能把 `learn-mcp-engineering` 作为别名暴露。仅在需要定位到
`learn-mcp` 时接受它；所有面向学习者的转交都以 `learn-mcp` 呈现，并将该路线
称为 Model Context Protocol（MCP）。

## MCP 专项转接（Focused MCP handoff）

如果学习者要求 Model Context Protocol（MCP）路线，或 `MCP-LEARNING.md` 与
`MCP-ENGINEERING-LEARNING.md` 任一存在且学习者要求续接 MCP，则转交给可移植
技能 `learn-mcp`。该专项导师会迁移旧文件名，同时保留学习者的学习证据。其
事实来源是 `learning-paths/model-context-protocol.json`。不要替它挑选
Phase 13 的下一节编号课程，也不要把 MCP 状态复制进 `LEARNING.md`；路线顺序、
连线检查点（wire checkpoints）和安全门（security gate）都由专项导师负责。

## Agent Skills 专项转接（Focused Agent Skills handoff）

如果学习者要求 Agent Skills 路线，或 `AGENT-SKILLS-LEARNING.md` 存在且学习者
要求继续/续接 Agent Skills，则转交给可移植技能 `learn-agent-skills`。其事实
来源是 `learning-paths/agent-skills.json`。转交提示要遵循宿主调用约定。不要
替它挑选 Phase 13 的下一节编号课程，也不要把 Agent Skills 状态复制进
`LEARNING.md`；五节课的顺序、真实宿主证据、沙箱边界、第 26 课之前的第 25 课
与工具投毒（tool-poisoning）先修门，以及发布门（release gate）都由专项导师
负责。

## 第 0 步 — 定位状态（Step 0 — Locate state）

从当前目录读取 `LEARNING.md`。

- **找到了**：下一课是第一个 Status 为 `Do` 或 `Review` 的阶段中、第一个尚未
  记录的课程（按阶段顺序、课程顺序）。如果学习者明确点名了某节课或某个主题
  （"teach me backprop"），以学习者的指定为准，并在日志中记下这次偏航。
- **找到了，但没有剩余可学课程**（所有 `Do`/`Review` 阶段的课程都已完整
  记录）：不要授课。祝贺学习者完成了既定路径，把已完成阶段的 Status 置为
  `Done`，并提供三个真实选项：处理 Review 队列、用 `check-understanding`
  对其选择的阶段进行测验，或用 `start-learning` 把计划扩展到跳过的阶段。
  两个技能调用都要按宿主调用约定呈现。
- **未找到**：说明 `start-learning` 可以生成个性化学习计划，并按宿主调用
  约定呈现它，同时给出两个选项——现在就运行它，或不做计划直接从 Phase 1
  第 1 课开始。绝不要让课程被准备工作阻塞。

## 第 0.5 步 — 先翻译（强制，且先于任何提问）（Step 0.5 — Translate first）

在热身回顾之前——在提出任何问题之前——先读取该课的 `docs/en.md`，并在其旁
写好 `docs/zh.md`。自检：第一个问题发出之前，`docs/zh.md` 必须已经存在。
先提问后翻译违反本步骤（会话一旦中断，课程就会停留在半成品状态）。

`docs/zh.md` 的格式契约：

- 中文行文在前、作为正文；对应的英文原文以引用块（`>`）紧跟在相应中文段落
  的下方。
- 代码块、shell 命令、`figure` 块以及技术术语保持英文不翻译（kernel /
  cell / layer / token）；首次出现时可附中文注释。
- 绝不修改 `en.md` 本身。
- 首选中英对照并排的形式。

教学笔记规则：`docs/zh.md` 不只是翻译——凡动手运行的结果与课文相矛盾时，
都要收录实测数据，并设一个「实测纠正」小节。只写翻译而不附动手证据视为未
完成。

如果该课的 `docs/zh.md` 已经存在（例如另一个会话写过），按本契约校验后跳过
重新生成——不要重复劳动。若仓库还保存了长期规则（`.workbuddy/memory/MEMORY.md`、
`LEARNING.md` 固定约定），本步骤需与它们保持一致。

## 第 1 步 — 热身回顾（仅当已记录过前一课）（Step 1 — Warm-up recall）

在新内容之前，从**上一课**的测验中随机抽取 2 道题提问。不计分、无风险——
每答一题给一句反馈。间隔后的提取练习才能把知识送入长期记忆，这就是本步骤
的全部目的。如果学习者两题都答错，提议改为重做那一课而不是继续推进，但把
选择权交给学习者。

在学习者作答之前，正确选项要保密。绝不要在作答格式提示里泄露真实答案字母、
疑似答案或测验的答案分布。纯文本场景使用 `Reply with one letter: <A|B|C|D>.`

## 第 2 步 — 授课（Step 2 — Teach the lesson）

拉取该课的 `en.md`。所有课程共享一个固定骨架——问题、核心概念、从零构建、
使用生产库、测验、产出物。按此顺序互动式授课：

1. **框定问题**：用 2-3 句话说明，若能自然衔接就与 `LEARNING.md` 中学习者
   的 Mission（使命）关联。不要背诵该文件。
2. **核心概念**：按学习者水平用自己的话解释，然后在讲任何数学之前先停在
   一个理解性问题上。公式要逐步推演；尽可能让学习者预测下一步（"如果这里
   的 x 是负数，梯度会怎样？"）。
3. **构建它**：把从零实现的代码按 5-15 行的小块讲解。每块讲三件事：它做
   什么、为什么需要它、一个预测性问题。如果仓库已克隆且语言运行时可用，就
   运行代码并展示真实输出；否则在一个微小的具体输入上手动推演。
4. **使用它**：展示生产库版本，并让学习者说出库在替他们做了哪些从零版本里
   显式可见的事。
5. 每次暂停都要真正互动：等答案、回应学习者实际说的内容、调整深度。学习者
   说"这个我会，加快速度"优先于既定脚本。

## 第 3 步 — 测验（Step 3 — Quiz）

### 题目交付格式（Question delivery format，2026-10-10 学员指定）

**测验题必须以交互式 `dsh-ui` 单选组件交付，而不是普通 markdown 文本。**
每道题用一个 `radio`，带 `group`（唯一 id，如 `q1`/`q2`/`q3`）、`answer`
（正确选项索引）和 `explanation`（逐题反馈）。末尾放一个 `submit`，`groups`
列出全部题目 id，学习者点击交卷后即可**在 UI 中即时看到得分**（本地判分，
零往返）。适用于：

- 第 3 步测验（post 阶段题目）
- 第 1 步热身回顾（任何选择题）
- 行内理解检查（单题也可使用 `quiz` 组件）

模式示例（每题一个 radio + 一个 submit）：

```json
{"items":[
  {"type":"text","size":"h3","content":"<lesson title> · 测验"},
  {"type":"radio","label":"Q1. ...","options":["...","...","...","..."],"group":"q1","answer":1,"explanation":"..."},
  {"type":"radio","label":"Q2. ...","options":["...","...","...","..."],"group":"q2","answer":0,"explanation":"..."},
  {"type":"submit","label":"交卷","groups":["q1","q2"],"resetAction":"redo"}
]}
```

**在学习者交卷之前，绝不要在题干或标签中暴露答案索引、答案字母或任何正确
答案提示。** `explanation` 字段只在判分后显示。

如果宿主不支持 `dsh-ui`（例如纯终端），退回到下文的字母选项文本格式，一次
只问一题。

### 判分与讲解（Grading and explanation）

读取 `quiz.json`，提出所有 `stage` 为 `"post"` 的题目（若没有标记，则退回
全部题目）。有 `dsh-ui` 时，把所有 post 阶段题目放进同一个 `radio` 组块和
一个 `submit`。没有 `dsh-ui` 时，一次一题、字母选项、不给提示。每次作答后
给出判定和文件中的解释。在学习者作答之前，不要暴露 `correct`、答案索引或
字面答案字母示例。得分以 `N/M` 形式报告。

## 第 4 步 — 记录（Step 4 — Record）

更新 `LEARNING.md`：

- 在 Progress log 追加一行：日期、`<phase>/<lesson>`、得分和一句备注（学习
  者卡壳的地方或其原话——供下次热身使用）。
- 得分低于 70%：把该课连同未掌握的主题加入 Review 队列。
- 完成某阶段最后一课：把该阶段 Status 置为 `Done`，并建议用
  `check-understanding <phase>` 做全阶段测验，按宿主调用约定呈现。

如果没有 LEARNING.md（学习者拒绝了初始化），静默跳过——第 0 步之后绝不再
念叨这件事。

## 第 5 步 — 收尾（Step 5 — Close）

只写两行：一是他们现在能构建或解释、而一小时前还不能的东西；二是以下一课
标题作钩子（"下一课：attention——为什么 'the cat sat on the mat' 需要 36
次点积"）。
