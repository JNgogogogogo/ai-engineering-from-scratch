# Capstone 17 — Personal AI Tutor (Adaptive, Multimodal, with Memory) · 毕业项目 17 —— 个人 AI 导师（自适应、多模态、带记忆）

> Khanmigo（Khan Academy）、Duolingo Max、Google LearnLM / Gemini for Education、Quizlet Q-Chat 和 Synthesis Tutor 都在 2026 年大规模上线了自适应多模态辅导。共同形态是：苏格拉底式策略（绝不直接甩答案）、每次交互后都更新的学习者模型（贝叶斯知识追踪风格）、语音 + 文本 + 拍照解题输入、课程图谱检索、间隔重复调度，以及面向适龄内容的严格安全过滤。本次毕业项目要上线一个特定学科的导师（K-12 代数或 Python 入门），用 10 名学习者跑一个为期两周的效果研究（efficacy study），并通过内容安全审计。

> Khanmigo (Khan Academy), Duolingo Max, Google LearnLM / Gemini for Education, Quizlet Q-Chat, and Synthesis Tutor all shipped adaptive multimodal tutoring at scale in 2026. The common shape is a Socratic policy (never just dump the answer), a learner model that updates after every interaction (Bayesian knowledge tracing style), voice + text + photo-math input, curriculum graph retrieval, spaced-repetition scheduling, and hard safety filters for age-appropriate content. The capstone is to ship a subject-specific tutor (K-12 algebra or intro Python), run a two-week efficacy study with 10 learners, and pass a content-safety audit.

**Type:** Capstone
**Languages:** Python (backend, learner model), TypeScript (web app), SQL (curriculum graph via Postgres + Neo4j)
**Prerequisites:** Phase 5 (NLP), Phase 6 (speech), Phase 11 (LLM engineering), Phase 12 (multimodal), Phase 14 (agents), Phase 17 (infrastructure), Phase 18 (safety)
**Phases exercised:** P5 · P6 · P11 · P12 · P14 · P17 · P18
**Time:** 30 hours

## Problem · 问题

自适应辅导曾经是教育科技的研究角落。到 2026 年它已经是消费级产品。Khanmigo 部署在全美大多数学区。Duolingo Max 攻下了数千万 MAU。Google 的 LearnLM / Gemini for Education 在 Google Classroom 里驱动辅导。Quizlet Q-Chat 与抽认卡并肩而立。Synthesis Tutor 靠「给好奇孩子的导师」火出了圈。共同要素：多模态输入（打字、说话、拍下方程）、苏格拉底式教学法（先提问，后讲解）、每次交互后更新的学习者模型，以及严格的适龄安全。

你要为特定人群造一个这样的产品。度量门槛是一次真实的效果研究：10 名学习者、两周的前测与后测。语音回路必须自然（毕业项目 03 的子技术栈）。记忆必须尊重隐私。安全过滤器必须通过面向 K-12 的 COPPA 意识红队测试。

> Adaptive tutoring used to be an ed-tech research niche. By 2026 it is a consumer product. Khanmigo is deployed across most US school districts. Duolingo Max hit tens of millions of MAUs. Google's LearnLM / Gemini for Education powers tutoring in Google Classroom. Quizlet Q-Chat sits alongside flashcards. Synthesis Tutor hit virality with tutor-for-curious-kids. The common elements: multimodal input (type, speak, photograph equations), Socratic pedagogy (ask first, explain later), a learner model that updates after each interaction, and strict age-appropriate safety.
> You will build one of these for a specific cohort. The measurement bar is an actual efficacy study: pre-test and post-test scores over two weeks with 10 learners. The voice loop must feel natural (capstone 03 sub-stack). The memory must be privacy-respecting. The safety filter must pass COPPA-aware red-team for K-12.

## Concept · 概念

四个组件。**导师策略**是一个苏格拉底式循环：学习者要答案时，策略先抛出一个引导性问题；学习者答对时，策略推进到下一个概念；学习者卡住时，策略给出脚手架式提示。**学习者模型**是贝叶斯知识追踪（BKT，或其简单变体），在每次交互后更新每个课程节点的掌握概率。**课程图谱**是一个存概念和先修边的 Neo4j；策略沿图谱走，挑出下一个概念。**记忆**是一个情景 + 语义存储（agentmemory 风格），保存过去的交互、错误和偏好。

UX 是多模态的。文本输入用于打字作答。语音输入走 LiveKit + Whisper（复用毕业项目 03）。数学题拍照输入走 dots.ocr 或 PaliGemma 2。语音输出走 Cartesia Sonic-2。安全用 Llama Guard 4 加一个适龄过滤器（屏蔽成人内容、暴力、自残），外加一个具备 COPPA 意识的记忆保留政策。

效果研究就是交付物。10 名学习者，前测和后测，为期两周。报告学习增益差和置信区间。与非自适应基线（同样的内容线性推送、不带导师策略）对比。

> Four components. **Tutor policy** is a Socratic loop: when the learner asks for the answer, the policy asks a leading question; when they get it right, it moves to the next concept; when they are stuck, it offers a scaffolded hint. **Learner model** is Bayesian knowledge tracing (or a simple variant) that updates mastery probability per curriculum node after each interaction. **Curriculum graph** is a Neo4j of concepts with prerequisite edges; the policy walks the graph to pick the next concept. **Memory** is an episodic + semantic store (agentmemory-style) holding past interactions, mistakes, and preferences.
> The UX is multimodal. Text input for typed answers. Voice input via LiveKit + Whisper (reuse capstone 03). Photo input for math problems via dots.ocr or PaliGemma 2. Voice output via Cartesia Sonic-2. Safety uses Llama Guard 4 plus an age-appropriate filter (blocks adult content, violence, self-harm) and a COPPA-aware memory retention policy.
> The efficacy study is the deliverable. 10 learners, pre-test and post-test, two weeks. Report learning gain delta and confidence interval. Compare against a non-adaptive baseline (the same content delivered linearly without the tutor policy).

## Architecture · 架构

```
learner device
  |
  +-- text         -> web app
  +-- voice        -> LiveKit Agents (ASR + TTS)
  +-- photo math   -> dots.ocr / PaliGemma 2
       |
       v
  tutor policy (LangGraph)
       - Socratic decision head
       - next-concept chooser (curriculum graph walk)
       - hint scaffolder
       - mastery update
       |
       v
  learner model (BKT / item-response theory)
       - per-concept mastery probability
       - spaced-repetition scheduler (SM-2 or FSRS)
       |
       v
  memory (agentmemory-style)
       - episodic: every interaction
       - semantic: learned mistakes, preferences
       - retention policy: COPPA / GDPR aware
       |
       v
  curriculum graph (Neo4j)
       - prerequisite edges
       - OER content attached
       |
       v
  safety:
    Llama Guard 4 + age-appropriate filter
    memory access guarded by learner ID scope
```

## Stack · 技术栈

- 学科选择：K-12 代数或 Python 入门（选一个做深）
- 导师策略：LangGraph，底层 Claude Sonnet 4.7（带 prompt 缓存）
- 学习者模型：经典贝叶斯知识追踪，或用 FSRS 做间隔调度
- 课程图谱：概念的 Neo4j + 先修边 + OER 内容
- 记忆：agentmemory 风格的持久向量 + 情景 + 语义存储
- 语音：LiveKit Agents 1.0 + Cartesia Sonic-2（复用毕业项目 03 子技术栈）
- 拍照解题：dots.ocr 或 PaliGemma 2 做方程识别
- 安全：Llama Guard 4 + 自定义适龄过滤器
- 评估：Bloom 层级出题、前/后测基座、效果研究工具

```figure
cf-tutor-loop
```

## Build It · 动手造

1. **课程图谱。** 建一个含 50-150 个概念节点的 Neo4j（例如 K-12 代数，从「数轴」到「求根公式」），带先修边。每个节点挂上 OER 内容（Open Textbook、OpenStax）。

2. **学习者模型。** 用先验初始化贝叶斯知识追踪：guess、slip、learn-rate。每次交互后更新各概念的掌握度。按学习者持久化。

3. **导师策略。** LangGraph 节点：`read_signal`（学习者的答案是正确 / 部分正确 / 卡住了？）、`select_concept`（走课程图谱，挑优先级最高的概念）、`scaffold`（苏格拉底式提示）、`update_mastery`。

4. **记忆。** 每次交互写入情景存储。错误和偏好提升为语义记忆。具备 COPPA 意识的保留政策：1 年后自动删除，家长可访问。

5. **语音路径。** LiveKit Agents worker 挂到导师策略上。ASR 用 Whisper-v3-turbo。TTS 用 Cartesia Sonic-2。支持插话打断（复用毕业项目 03 的机制）。

6. **拍照解题路径。** 上传或拍摄图像；跑 dots.ocr 或 PaliGemma 2 识别方程；作为结构化输入交给导师。

7. **安全。** 每个模型输出都过 Llama Guard 4 + 适龄过滤器（屏蔽自残、成人内容、暴力）。记忆访问按学习者 ID 划定范围；提供家长访问入口用于删除。

8. **效果研究。** 10 名学习者，前测（标准化 30 题基线），两周导师交互（每周 3 次），后测。与 10 名学习者组成的非自适应基线组在同样内容上对比。

9. **每周进度报告。** 按学习者自动生成 PDF 摘要：探索过的主题、掌握轨迹、建议的下一步。

> 2. **Learner model.** Initialize Bayesian knowledge tracing with priors: guess, slip, learn-rate. Update per-concept mastery after each interaction. Persist per learner.
> 4. **Memory.** Every interaction writes to an episodic store. Mistakes and preferences promote to semantic memory. COPPA-aware retention policy: auto-delete after 1 year, parent-accessible.
> 7. **Safety.** Every model output passes Llama Guard 4 + an age-appropriate filter (blocks self-harm, adult content, violence). Memory access scoped by learner ID; parental access surface for deletion.
> 8. **Efficacy study.** 10 learners, pre-test (standardized 30-question baseline), two weeks of tutor interaction (3 sessions/week), post-test.

## Use It · 实战用法

```
learner: "I don't understand why 3x + 6 = 12 means x = 2"
[signal]   stuck
[concept]  'isolating variables' (prerequisite: addition-subtraction-equality)
[scaffold] "what number would you subtract from both sides to start?"
learner: "6"
[signal]   correct
[mastery]  addition-subtraction-equality: 0.62 -> 0.77
[concept]  continue 'isolating variables'
[scaffold] "great. now what is 3x / 3 equal to?"
```

## Ship It · 交付

`outputs/skill-ai-tutor.md` 是交付物：一个特定学科的自适应导师，带多模态输入、学习者模型、记忆、安全和实测效果。

| 权重 | 评分标准 | 度量方式 |
|:-:|---|---|
| 25 | 学习增益差 | 10 名学习者两周研究中的前/后测差值 |
| 20 | 苏格拉底式保真度 | 转写样本上的量规评分 |
| 20 | 多模态 UX | 语音 + 拍照 + 文本端到端的一致性 |
| 20 | 安全 + 隐私姿态 | Llama Guard 4 通过率 + COPPA 意识保留政策 |
| 15 | 课程广度与图谱质量 | 概念覆盖 + 先修图一致性 |
| **100** | | |

> `outputs/skill-ai-tutor.md` is the deliverable. A subject-specific adaptive tutor with multimodal input, a learner model, memory, safety, and measured efficacy.

## Exercises · 练习

1. 跑效果研究：开自适应学习者模型和不开（随机概念顺序）各跑一次。报告差值。预期自适应赢，但赢多少才是有意思的数字。

2. 加一个多模态探针：同一个概念问题分别以文本、语音、照片呈现。度量学习者用自己偏好的模态时是否收敛更快。

3. 建一个家长仪表盘：练过的主题、掌握轨迹、即将学习的概念、安全事件（任何护栏命中）。符合 COPPA。

4. 加一个语言切换模式：导师接受西班牙语输入并用西班牙语授课。度量 X-Guard 覆盖。

5. 压测记忆隐私：验证学习者 A 无法看到学习者 B 的数据，即使通过语音片段重摄入攻击。记录这次访问企图并告警。

> 1. Run the efficacy study with and without the adaptive learner model (random concept order). Report the delta. Expect adaptive to win, but the size is the interesting number.
> 5. Stress the memory privacy: verify that learner A cannot see learner B's data even through a voice-clip re-ingest attack. Log the attempted access and alert.

## Key Terms · 术语表

| 术语 | 俗称 | 实际含义 |
|------|-----------------|------------------------|
| Socratic policy（苏格拉底式策略） | "提问，不甩答案" | 导师抛出引导性问题，而不是直接给答案 |
| Bayesian knowledge tracing | "BKT" | 经典的学习者模型方程，算每个概念的掌握概率 |
| FSRS | "开源间隔重复调度器" | 2024 年的间隔重复调度器，优于 SM-2 |
| Curriculum graph（课程图谱） | "概念 DAG" | 存概念与先修边的 Neo4j |
| Episodic memory（情景记忆） | "逐交互日志" | 每次交互都存储，供日后检索 |
| Semantic memory（语义记忆） | "习得模式库" | 从情景记忆压缩提升而来的错误与偏好 |
| COPPA | "儿童隐私法" | 限制收集 13 岁以下儿童数据的美国法律 |

## Further Reading · 延伸阅读

- [Khanmigo (Khan Academy)](https://www.khanmigo.ai) —— 消费级 K-12 导师参照
- [Duolingo Max](https://blog.duolingo.com/duolingo-max/) —— 语言学习导师参照
- [Google LearnLM / Gemini for Education](https://blog.google/products-and-platforms/products/education/google-learnlm-gemini-generative-ai/) —— 托管参照模型
- [Quizlet Q-Chat](https://quizlet.com) —— 另一个参照
- [Synthesis Tutor](https://www.synthesis.com) —— 创业公司参照
- [FSRS algorithm](https://github.com/open-spaced-repetition/fsrs4anki) —— 间隔重复调度器
- [Bayesian Knowledge Tracing](https://en.wikipedia.org/wiki/Bayesian_knowledge_tracing) —— 学习者模型经典
- [LiveKit Agents](https://github.com/livekit/agents) —— 语音技术栈
