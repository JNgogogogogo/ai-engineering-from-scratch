# Chatbots — Rule-Based to Neural to LLM Agents · 聊天机器人 —— 从规则到神经再到 LLM 智能体

> ELIZA 用模式匹配来回答。DialogFlow 映射意图（intent）。GPT 从权重里生成回答。Claude 调用工具并验证结果。每一个时代都在解决上一个时代最糟的失败。
>
> ELIZA replied with pattern matches. DialogFlow mapped intents. GPT answered from weights. Claude runs tools and verifies. Each era solved the previous one's worst failure.

**类型:** Learn（学习）
**语言:** Python
**前置课程:** Phase 5 · 13（问答）、Phase 5 · 14（信息检索）
**时间:** ~75 分钟

## The Problem · 问题

用户说「我想改签航班」。系统必须弄清楚用户想要什么、缺什么信息、怎么拿到这些信息、以及怎么完成这个操作。然后用户说「等等，我还是取消吧」，系统又必须记住上下文、切换任务、保持状态。

对话对 ML 系统来说很难。输入是开放的，输出要在很多轮里保持连贯，系统可能还要对真实世界执行动作（改签航班、扣银行卡款）。每一步错误用户都看得见。

聊天机器人架构在四个范式之间轮转，每一个范式的出现都是因为上一个失败得太显眼。本课按顺序走一遍。2026 年的生产环境是后两者的混合体。

> A user says "I want to change my flight." The system has to figure out what they want, what information is missing, how to get it, and how to complete the action. ... Conversation is hard for an ML system. The input is open-ended. The output has to be coherent over many turns. The system may need to act on the world ... Every wrong step is visible to the user.
> Chatbot architectures have cycled through four paradigms, each introduced because the previous one failed too visibly. This lesson walks them in order. The 2026 production landscape is a hybrid of the last two.

## The Concept · 概念

![聊天机器人演进：规则型 → 检索型 → 神经型 → 智能体](../assets/chatbot.svg)

### The scripted half-century, 1950-2001 · 脚本的半个世纪（1950-2001）

第一个范式没有只活五年，它活了五十年。了解它的轨迹很重要，因为其中的每个系统都是同一台机器——匹配输入、吐出一句预备好的回答、更新一点状态——而往这台机器里加了五十年规则，从未产出通用情形。这个天花板就是范式二到范式四存在的原因。

**1950.** Turing 用一个可操作的替代方案绕开「机器能思考吗」：如果审讯者通过电传打字分辨不出机器和人，这个哲学问题就不成问题了。对话在这个领域还没名字的时候，就成了这个领域的基准。

**1956.** 名字来了——达特茅斯的一个暑期研讨会创造了「人工智能」一词，赌的是智能的每个特征都「原则上可以被精确描述到让一台机器去模拟它」。这份提案给实质性进展的预算是两个月。

**1966.** ELIZA 交付了你将在第 1 步亲手实现的反射戏法（reflection trick）：分解规则从输入里抽出片段，重组规则把它们作为问题回敬出去。总共约 200 个模式，零状态、零理解——用户却照样向它倾诉。Weizenbaum 余下的职业生涯都在为「这么少的机器就够人当真」而忧心。

**1972.** PARRY，斯坦福为了建模偏执（paranoia）而造，补上了 ELIZA 缺的那块：内部状态。恐惧、愤怒、不信任各有一个数值变量，每一轮都更新，并决定下一个触发哪个脚本，于是相同的输入会依据之前的对话产生不同的回答。在一个盲测转录实验里，精神病学家区分 PARRY 和人类患者的能力与抛硬币无异。它是人设条件化（persona conditioning）的直系祖先——一个用三个浮点数实现的 system prompt。同年，这两个机器人被接上 ARPANET 互相对话：一个治疗师脚本在采访一个偏执状态机，这是网络上第一次 bot 对 bot 的对话。

**1995.** ALICE 用 AIML（一种面向「模式-模板」对的 XML 方言）放大了 ELIZA 的配方。约 4 万条手写类别，三夺 Loebner 奖。它证明了规则型系统的扩展律：更多规则买到的是覆盖面，永远买不到通用性。每条规则都是一份要人维护的负债。

**2001.** SmarterChild 把这套配方端到 3000 万即时通讯用户面前，并加入了后端查询——天气、股票、电影时刻——拼接进模板。眯起眼看，这就是穿着 2001 年戏服的工具调用（tool calling）：解析意图，调用服务，把结果渲染进回复。

五十年，一套机制，不断上涨的规则数。这个范式的终结不是因为谁证伪了它，而是因为手写状态机的维护成本随覆盖面线性增长，而用户期望随他们上周刚见过的东西增长。

```figure
chatbot-lineage
```

**规则型（ELIZA、AIML、DialogFlow）。** 手写的模式匹配用户输入并产出回答。意图分类器路由到预定义流程。槽填充（slot filling）状态机收集必要信息。在它设计好的窄范围里表现出色，出了范围立刻失效。仍然在不容忍幻觉的安全关键领域（银行身份验证、航空订票）上线。

**检索型。** FAQ 式系统。把每一对（话语，回答）都编码存好。运行时编码用户消息，检索最接近的已存回答。想想 Zendesk 经典的「相似文章」功能。比规则更能处理同义改写。没有生成，所以没有幻觉。

**神经型（seq2seq）。** 在对话日志上训练的编码器-解码器。从零生成回答。流畅但容易产出通用回答（「我不知道」）和事实漂移，从来无法稳定切题。这就是 Google、Facebook、Microsoft 在 2016-2019 年的聊天机器人都不尽人意的原因。

**LLM 智能体。** 包在一个循环里的语言模型：规划、调用工具、验证结果。不是一个带长 prompt 的聊天机器人，而是一个智能体循环：规划 → 调用工具 → 观察结果 → 决定下一步。检索优先的落地（RAG）让它不幻觉，工具调用让它真能做事。这就是 2026 年的架构。

这四个范式不是依次替换的关系。2026 年的生产聊天机器人四个都会经过：规则型管身份验证和破坏性操作，检索型管 FAQ，神经生成管自然的措辞，LLM 智能体管含糊的开放式提问。

> The first paradigm did not last five years. It lasted fifty. ... fifty years of adding rules to that machine never produced the general case. That ceiling is why paradigms two through four exist.
> **1950.** Turing sidesteps "can machines think?" by proposing an operational replacement ... Conversation becomes the field's benchmark before the field has a name.
> **1966.** ELIZA ships the reflection trick you build in Step 1 ... Around 200 patterns total, zero state, zero understanding — and users confided in it anyway.
> **1972.** PARRY ... adds the piece ELIZA lacked: internal state. ... It is the direct ancestor of persona conditioning — a system prompt implemented as three floats.
> **1995.** ALICE scales the ELIZA recipe with AIML ... It proved the scaling law of rule-based systems: more rules buy coverage, never generality.
> Fifty years, one mechanism, rising rule counts. The paradigm ended not because anyone disproved it but because the maintenance cost of hand-written state machines grows linearly with coverage while user expectations grow with whatever they saw last week.
> **Rule-based ...** Works brilliantly inside the narrow scope it was designed for. Fails immediately outside it. ... **Retrieval-based.** ... No generation, so no hallucination. **Neural (seq2seq).** ... Never reliably on topic. ... **LLM agents.** ... This is the 2026 architecture.
> The four paradigms are not sequential replacements. A 2026 production chatbot routes through all four.

## Build It · 动手造

### Step 1: rule-based pattern matching · 第 1 步：规则型模式匹配

```python
import re


class RulePattern:
    def __init__(self, pattern, response_template):
        self.regex = re.compile(pattern, re.IGNORECASE)
        self.template = response_template


PATTERNS = [
    RulePattern(r"my name is (\w+)", "Nice to meet you, {0}."),
    RulePattern(r"i (need|want) (.+)", "Why do you {0} {1}?"),
    RulePattern(r"i feel (.+)", "Why do you feel {0}?"),
    RulePattern(r"(.*)", "Tell me more about that."),
]


def rule_based_respond(user_input):
    for pattern in PATTERNS:
        m = pattern.regex.match(user_input.strip())
        if m:
            return pattern.template.format(*m.groups())
    return "I don't understand."
```

20 行的 ELIZA。反射戏法（「I feel sad」→「Why do you feel sad」）就是 Weizenbaum 1966 年那个经典的心理治疗师演示。至今仍有启发性。

> ELIZA in 20 lines. The reflection trick ("I feel sad" → "Why do you feel sad") is the canonical psychotherapist demo from Weizenbaum 1966. Still instructive.

### Step 2: retrieval-based (FAQ) · 第 2 步：检索型（FAQ）

这个示意代码片段需要 `pip install sentence-transformers`（会连带安装 torch）。本课可运行的 `code/main.py` 改用标准库的 Jaccard 相似度，因此整课不需要任何外部依赖就能跑。

```python
from sentence_transformers import SentenceTransformer
import numpy as np


FAQ = [
    ("how do i reset my password", "Go to Settings > Security > Reset Password."),
    ("how do i cancel my order", "Go to Orders, find the order, click Cancel."),
    ("what is your return policy", "30-day returns on unused items, original packaging."),
]


encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
faq_questions = [q for q, _ in FAQ]
faq_embeddings = encoder.encode(faq_questions, normalize_embeddings=True)


def faq_respond(user_input, threshold=0.5):
    q_emb = encoder.encode([user_input], normalize_embeddings=True)[0]
    sims = faq_embeddings @ q_emb
    best = int(np.argmax(sims))
    if sims[best] < threshold:
        return None
    return FAQ[best][1]
```

基于阈值的拒答是关键设计决策。如果最佳匹配不够接近，就返回 `None`，让系统升级转人工。

> Threshold-based refusal is the key design choice. If the best match is not close enough, return `None` and let the system escalate.

### Step 3: neural generation (baseline) · 第 3 步：神经生成（基线）

用一个小型指令微调的编码器-解码器（FLAN-T5）或微调过的对话模型。2026 年单独用达不到生产标准（自相矛盾、跑题漂移、事实错误），但作为混合系统中负责自然措辞的部件在上线。DialoGPT 风格的 decoder-only 模型需要显式的轮次分隔符和 EOS 处理才能产出连贯回复；FLAN-T5 的 text2text 管线对教学例子开箱即用。

```python
from transformers import pipeline

chatbot = pipeline("text2text-generation", model="google/flan-t5-small")

response = chatbot("Respond politely to: Hi there!", max_new_tokens=40)
print(response[0]["generated_text"])
```

> Use a small instruction-tuned encoder-decoder (FLAN-T5) or a fine-tuned conversational model. Production-unusable on its own in 2026 (contradiction, off-topic drift, factual nonsense), but ships inside hybrid systems for natural phrasing. ... a FLAN-T5 text2text pipeline works out of the box for a teaching example.

### Step 4: LLM agent loop · 第 4 步：LLM 智能体循环

2026 年的生产形态：

```python
def agent_loop(user_message, tools, llm, max_steps=5):
    history = [{"role": "user", "content": user_message}]
    for _ in range(max_steps):
        response = llm(history, tools=tools)
        tool_call = response.get("tool_call")
        if tool_call:
            tool_name = tool_call.get("name")
            args = tool_call.get("arguments")
            if not isinstance(tool_name, str) or tool_name not in tools:
                history.append({"role": "assistant", "tool_call": tool_call})
                history.append({"role": "tool", "name": str(tool_name), "content": f"error: unknown tool {tool_name!r}"})
                continue
            if not isinstance(args, dict):
                history.append({"role": "assistant", "tool_call": tool_call})
                history.append({"role": "tool", "name": tool_name, "content": f"error: arguments must be a dict, got {type(args).__name__}"})
                continue
            fn = tools[tool_name]
            result = fn(**args)
            history.append({"role": "assistant", "tool_call": tool_call})
            history.append({"role": "tool", "name": tool_name, "content": result})
        else:
            return response["content"]
    return "I could not complete the task in the step budget."
```

三个要点。工具（tool）是 LLM 可以调用的函数。当 LLM 返回最终答案而不是工具调用时，循环终止。步数预算（step budget）防止在含糊任务上无限循环。

真实生产还要加上：检索优先的落地（在每次 LLM 调用前注入相关文档）、护栏（未经确认就拒绝破坏性操作）、可观测性（记录每一步）和评估（自动检查智能体行为不跑偏）。

> Three things to name. Tools are callable functions the LLM can invoke. The loop terminates when the LLM returns a final answer instead of a tool call. The step budget prevents infinite loops on ambiguous tasks.
> Real production adds: retrieval-first grounding ..., guardrails ..., observability ..., and evaluations ....

### Step 5: hybrid routing · 第 5 步：混合路由

```python
def hybrid_chat(user_input):
    if is_destructive_action(user_input):
        return structured_flow(user_input)

    faq_answer = faq_respond(user_input, threshold=0.6)
    if faq_answer:
        return faq_answer

    return agent_loop(user_input, tools, llm)


def is_destructive_action(text):
    danger_words = ["delete", "cancel", "charge", "refund", "transfer"]
    return any(w in text.lower() for w in danger_words)
```

模式是：破坏性的事交给确定性规则，固定 FAQ 交给检索，其余一切交给 LLM 智能体。这就是 2026 年客服系统真正上线的东西。

> The pattern: deterministic rules for anything destructive, retrieval for canned FAQs, LLM agents for everything else. This is what ships in 2026 customer-support systems.

## Use It · 实战用法

2026 年的技术栈：

| 用例 | 架构 |
|---------|---------------|
| 订票、支付、身份验证 | 规则型状态机 + 槽填充 |
| 客服 FAQ | 在精选答案上做检索 |
| 开放式帮助对话 | 带 RAG + 工具调用的 LLM 智能体 |
| 内部工具 / IDE 助手 | 带工具调用（搜索、读、写）的 LLM 智能体 |
| 陪伴 / 角色扮演聊天机器人 | 带人设 system prompt 的微调 LLM，知识走检索 |

生产环境始终用混合路由。没有任何单一架构能处理好每一种请求。路由层本身通常是一个小型意图分类器。

> The 2026 stack: ... Always use hybrid routing in production. No single architecture handles every request well. The routing layer itself is typically a small intent classifier.

## Failure modes that still ship · 至今还在上线的失败模式

- **自信的捏造。** LLM 智能体声称完成了它并没有完成的操作。缓解：验证结果、记录工具调用，绝不允许 LLM 在没有成功工具返回的情况下声称做过某事。
- **提示注入（prompt injection）。** 用户插入覆盖 system prompt 的文本。在 OWASP LLM 应用 Top 10（2025）里排名第一（LLM01）。两种形态：直接注入（粘贴进对话）和间接注入（藏在智能体会读到的文档、邮件或工具输出里）。

  各场景的攻击成功率不同。在通用工具使用与编码基准上，前沿模型的实测成功率约 0.5-8.5%。特定高危配置（针对 AI 编码智能体的自适应攻击、脆弱的编排）达到过约 84%。生产 CVE 包括 EchoLeak（CVE-2025-32711，CVSS 9.3）——Microsoft 365 Copilot 中由攻击者控制的邮件触发的零点击数据外泄漏洞。

  缓解手段：在整个循环里把用户输入当作不可信；工具调用前先净化；把工具输出与主 prompt 隔离；采用 Plan-Verify-Execute（PVE）模式——智能体先规划，执行前把每个动作对照计划校验（这能阻止工具结果注入计划外的新动作）；破坏性操作要求用户确认；对工具权限做最小授权。

  再多的提示工程也无法完全消除这个风险。必须要有外部的运行时防御层（LLM Guard、白名单校验、语义异常检测）。
- **范围蔓延（scope creep）。** 因为某次工具调用返回了沾边的信息，智能体偏离了任务。缓解：收窄工具契约；保持 system prompt 聚焦；为跑偏率增加评估。
- **无限循环。** 智能体反复调用同一个工具。缓解：步数预算、工具调用去重、用 LLM 裁判判断「我们有没有在推进」。
- **上下文窗口耗尽。** 长对话把最早的轮次挤出上下文。缓解：对更早的轮次做摘要、按相似度检索相关历史轮次，或换长上下文模型。

> **Confident fabrication.** LLM agent claims it completed an action it did not. Mitigation: verify outcomes, log tool calls, never let the LLM claim to have done something without a successful tool return.
> **Prompt injection.** User inserts text that overrides the system prompt. Ranked LLM01 in the OWASP Top 10 for LLM Applications 2025. ... No amount of prompt engineering fully eliminates this risk. External runtime defense layers (LLM Guard, allowlist validation, semantic anomaly detection) are required.
> **Scope creep.** ... **Infinite loops.** ... **Context window exhaustion.** Long conversations push the earliest turns out of context.

## Ship It · 交付

保存为 `outputs/skill-chatbot-architect.md`：

```markdown
---
name: chatbot-architect
description: Design a chatbot stack for a given use case.
version: 1.0.0
phase: 5
lesson: 17
tags: [nlp, agents, chatbot]
---

Given a product context (user need, compliance constraints, available tools, data volume), output:

1. Architecture. Rule-based, retrieval, neural, LLM agent, or hybrid (specify which paths go where).
2. LLM choice if applicable. Name the model family (Claude, GPT-4, Llama-3.1, Mixtral). Match to tool-use quality and cost.
3. Grounding strategy. RAG sources, retrieval method (see lesson 14), tool contracts.
4. Evaluation plan. Task success rate, tool-call correctness, off-task rate, hallucination rate on held-out dialogs.

Refuse to recommend a pure-LLM agent for any destructive action (payments, account deletion, data modification) without a structured confirmation flow. Refuse to skip the prompt-injection audit if the agent has write access to anything.
```

> Save as `outputs/skill-chatbot-architect.md`.

## Exercises · 练习

1. **简单。** 用 10 个模式为咖啡店点单机器人实现上面的规则型回答。测试边界情况：重复下单、修改订单、取消、意图不清。
2. **中等。** 搭一个 FAQ + LLM 兜底的混合系统：50 条 SaaS 产品的固定 FAQ，LLM 兜底时对文档站做检索。在 100 个真实客服问题上测拒答率和准确率。
3. **困难。** 用三个工具（搜索、读用户数据、发邮件）实现上面的智能体循环。用 50 个测试场景（含提示注入尝试）跑一次评估。报告跑偏率、任务失败率和任何一次注入成功。

## Key Terms · 关键术语

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Intent | 用户想要什么 | 分类标签（book_flight、reset_password）。路由到对应的处理器。|
| Slot | 一条信息 | 机器人需要的参数（日期、目的地）。槽填充就是一连串追问。|
| RAG | 检索加生成 | 先检索相关文档，再让 LLM 的回答以它们为依据。|
| Tool call | 函数调用 | LLM 发出带名字 + 参数的结构化调用。运行时执行并返回结果。|
| Agent loop | 规划、行动、验证 | 让 LLM 调用与工具调用交替进行、直到任务完成的控制器。|
| Prompt injection | 用户攻击提示 | 试图覆盖 system prompt 的恶意输入。|

## Further Reading · 延伸阅读

- [Turing (1950). Computing Machinery and Intelligence](https://academic.oup.com/mind/article/LIX/236/433/986238) —— 让对话成为这个领域基准的那篇论文。
- [Weizenbaum (1966). ELIZA — A Computer Program For the Study of Natural Language Communication](https://web.stanford.edu/class/cs124/p36-weizenabaum.pdf) —— 规则型聊天机器人的开山论文。
- [Colby, Weber, Hilf (1971). Artificial Paranoia](https://doi.org/10.1016/0004-3702(71)90002-6) —— PARRY 的情感变量架构，第一个有状态的聊天机器人。
- [Thoppilan et al. (2022). LaMDA: Language Models for Dialog Applications](https://arxiv.org/abs/2201.08239) —— Google 后期的神经聊天机器人论文，恰好停在 LLM 智能体接管之前。
- [Yao et al. (2022). ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) —— 给智能体循环模式命名的论文。
- [Anthropic's guide on building effective agents](https://www.anthropic.com/research/building-effective-agents) —— 2024 年的生产指南，到 2026 年依然成立。
- [Greshake et al. (2023). Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection](https://arxiv.org/abs/2302.12173) —— 间接提示注入的那篇论文。
- [OWASP Top 10 for LLM Applications 2025 — LLM01 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) —— 让提示注入登顶安全头号问题的排名。
- [AWS — Securing Amazon Bedrock Agents against Indirect Prompt Injections](https://aws.amazon.com/blogs/machine-learning/securing-amazon-bedrock-agents-a-guide-to-safeguarding-against-indirect-prompt-injections/) —— 包含 Plan-Verify-Execute 与用户确认流程的编排层防御实践。
- [EchoLeak (CVE-2025-32711)](https://www.vectra.ai/topics/prompt-injection) —— 间接提示注入导致的零点击数据外泄标志性 CVE。为什么有写权限的智能体需要运行时防御的参考案例。
