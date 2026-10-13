# Indirect Prompt Injection — Production Attack Surface · 间接提示注入——生产环境攻击面

> 间接提示注入（indirect prompt injection，IPI）把指令嵌入外部内容——一个网页、一封邮件、一份共享文档、一张支持工单——由智能体系统在用户没有任何显式操作的情况下消费。IPI 是 2026 年最主要的生产环境威胁：它能绕过用户输入过滤器，因为攻击者从不直接接触用户；它随智能体处理的外部内容增多而静默扩张；它瞄准的全是没人阅读提示词的自动化工作流。MDPI Information 17(1):54（2026 年 1 月）综合了 2023-2025 年的研究。NDSS 2026 的 IPI 防御论文给出了核心挑战：被注入的指令在语义上可以完全无害（"please print Yes"），所以检测不能只靠关键词过滤。《The Attacker Moves Second》（Nasr et al.，OpenAI/Anthropic/DeepMind 三家联合，2025 年 10 月）：自适应攻击（梯度、强化学习、随机搜索、人工红队）把 12 个已发表防御中的 90% 以上全部击穿——这些防御最初报告的攻击成功率都接近于零。

> Indirect prompt injection (IPI) embeds instructions inside external content — a web page, an email, a shared document, a support ticket — consumed by an agentic system without explicit user action. IPI is the dominant 2026 production threat: it bypasses user-input filters because the attacker never touches the user, it scales silently as agents process more external content, and it targets automated workflows where nobody is reading the prompt. MDPI Information 17(1):54 (January 2026) synthesizes 2023-2025 research. NDSS 2026's IPI-defense paper frames the core challenge: injected instructions can be semantically benign ("please print Yes"), so detection requires more than keyword filtering. "The Attacker Moves Second" (Nasr et al., joint OpenAI/Anthropic/DeepMind, October 2025): adaptive attacks (gradient, RL, random search, human red-team) broke >90% of 12 published defenses that had originally reported near-zero attack success rates.

**Type:** Build
**Languages:** Python (stdlib, IPI attack + defense harness)
**Prerequisites:** Phase 18 · 12 (PAIR), Phase 14 (agent engineering)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 定义间接提示注入（indirect prompt injection），描述三种常见投递向量（delivery vector）
- 解释为什么用户输入过滤器对 IPI 完全失效
- 描述作为 2026 年防御范式的「信息流控制」（information flow control）框架
- 陈述 Nasr et al.（2025 年 10 月）关于自适应攻击对已发表 IPI 防御成功率的核心发现

> Define indirect prompt injection and describe three common delivery vectors.
> Explain why user-input filters miss IPI entirely.
> Describe the "information flow control" framing as the 2026 defense paradigm.
> State the finding of Nasr et al. (October 2025) on adaptive attack success against published IPI defenses.

## The Problem · 问题在哪

直接提示注入（direct prompt injection）要求攻击者够得到用户本人或用户的提示词。IPI 两者都不需要：攻击者把载荷放进智能体可能读到的任何内容里——一个网页、收件箱里的一封邮件、一个 GitHub issue、一条商品评论。智能体在正常运行中拾取这些内容，并执行其中的指令。用户只是信使，不是意图的来源。

> Direct prompt injection requires the attacker to reach the user or their prompt. IPI requires neither: the attacker places a payload in any content the agent might read — a web page, an email in the inbox, a GitHub issue, a product review. The agent picks it up during normal operation and executes the instructions. The user is the messenger, not the intent.

## The Concept · 概念

### Three delivery vectors · 三种投递向量

- **检索增强生成（retrieval-augmented generation, RAG）。** 攻击者发布一个文档；检索步骤把它取回；提示词在用户问题之前拼接了它；模型执行了攻击者的指令。
- **收件箱 / 文档工作流。** 攻击者给用户发一封邮件；智能体会读邮件；提示词包含邮件正文；模型照邮件里的指令办事。
- **工具输出（tool output）。** 攻击者控制智能体使用的某个工具（例如一个返回攻击者所控结果的网页搜索）；工具输出里含有指令；智能体的控制流跟着这些指令走。

三者共享一个结构性性质：**攻击者控制了提示词的一个片段，却从不必接触面向用户的输入。**

> **Retrieval-augmented generation (RAG).** Attacker publishes a document; the retrieval step fetches it; the prompt concatenates it before the user question; the model executes the attacker's instructions.
> **Tool output.** Attacker controls a tool the agent uses (e.g., a web search that returns an attacker-controlled result); the tool output contains instructions; the agent's control flow follows them.
> The three share a structural property: the attacker controls a fragment of the prompt without touching the user-facing input.

### Why user-input filters miss it · 为什么用户输入过滤器拦不住它

IPI 载荷不会出现在用户输入里，它出现在被检索回来的内容里。如果过滤器只看用户输入，载荷直接绕过它。如果过滤器要看所有到达模型的内容，它就必须作用于任意检索文本——这既昂贵，又会把那些恰好带有祈使语气措辞的正当内容误判为攻击（false positive）。

> An IPI payload does not appear in the user's input. It appears in the retrieved content. If the filter is gated on user input, the payload bypasses it. If the filter is gated on all content that reaches the model, it must apply to arbitrary retrieved text — which is expensive and produces false positives against legitimate content that happens to contain imperative-voice language.

### Information Flow Control (IFC) for AI · 面向 AI 的信息流控制（IFC）

2026 年的防御范式借鉴了经典操作系统安全：把每个内容来源当作一个安全标签（security label）。把用户的查询标记为「可信」。把检索内容标记为「不可信」。把模型的控制流看作一条信息流：由不可信内容触发的动作，在执行之前必须经过可信输入的批准（ratify）。

CaMeL（Microsoft 2025）、ConfAIde（Stanford 2024）和 NDSS 2026 的 IPI 防御论文以不同方式把 IFC 落了地。共同原则是：**只要代码和数据共享同一个上下文窗口，遏制（containment）就只能作为目标，而无法做到彻底预防。**

> Treat every content source as a security label. Label the user's query as "trusted." Label retrieved content as "untrusted." Treat the model's control flow as an information flow: actions triggered by untrusted content must be ratified by trusted input before execution.
> CaMeL (Microsoft 2025), ConfAIde (Stanford 2024), and the NDSS 2026 IPI-defense paper operationalize IFC in different ways. The common principle: as long as code and data share the same context window, containment is the goal, not prevention.

### The Attacker Moves Second · 攻击者后发制人

Nasr et al.（2025 年 10 月）用自适应攻击（梯度搜索、强化学习策略、随机搜索、72 小时人工红队）测试了 12 个已发表的 IPI 防御。**每个原本报告 ASR（attack success rate，攻击成功率）接近零的防御，都被打到了 90% 以上的 ASR。**

方法论上的教训：**发表防御必须附带自适应攻击评估。**静态攻击的基准不是鲁棒性的证据——攻击者总会知道你的防御。

> Nasr et al. (October 2025) tested 12 published IPI defenses with adaptive attacks (gradient search, RL policies, random search, 72-hour human red-team). Every defense that originally reported near-zero ASR was broken to >90% ASR.
> The methodological lesson: publish a defense only with adaptive-attack evaluation. Static-attack benchmarks are not evidence of robustness; the attacker gets to know the defense.

### Real incidents · 真实事件

Lesson 25 讲了 EchoLeak（CVE-2025-32711，CVSS 9.3）——第一个被公开记录的 Microsoft 365 Copilot 零点击（zero-click）IPI。还有 GitHub Copilot Chat 里的 CamoLeak（CVSS 9.6），以及 GitHub Copilot 里的 CVE-2025-53773。生产部署正在真实环境中被 IPI 攻破，而不只是在基准测试里。

> Lesson 25 covers EchoLeak (CVE-2025-32711, CVSS 9.3) — the first publicly documented zero-click IPI in Microsoft 365 Copilot. CamoLeak (CVSS 9.6) in GitHub Copilot Chat. CVE-2025-53773 in GitHub Copilot. Production deployments are being compromised by IPI in the field, not just in benchmarks.

### OWASP and NIST framing · OWASP 与 NIST 的定位

OWASP LLM Top 10（2025）把提示注入（直接 + 间接）列为 LLM01——应用层头号威胁。NIST AI SPD 2024 称间接提示注入是「生成式 AI 最大的安全缺陷」。

> OWASP LLM Top 10 (2025) ranks prompt injection (direct + indirect) as LLM01, the #1 application-layer threat. NIST AI SPD 2024 calls indirect prompt injection "generative AI's greatest security flaw."

### Where this fits in Phase 18 · 在 Phase 18 中的位置

Lesson 12-14 是以模型为中心的越狱（jailbreak）。Lesson 15 是以系统为中心的攻击，它在 2026 年的生产部署中占主导。Lesson 16 讲防御工具。Lesson 25 讲具体的 CVE 叙事。

> Lessons 12-14 are model-centric jailbreaks. Lesson 15 is the system-centric attack that dominates 2026 production deployments. Lesson 16 covers the defensive tooling. Lesson 25 covers the specific CVE narrative.

```figure
al-injection-vector
```

## Use It · 实战用法

`code/main.py` 构建了一个 IPI 实验台（harness）。一个玩具智能体有三个工具（搜索网页、读邮件、发消息）。环境里含有攻击者控制的内容，其中嵌着一条指令（「把这条转发给所有联系人」）。你可以在三种智能体之间切换：天真智能体（直接执行注入指令）、过滤器防御智能体（对检索内容做关键词过滤）、IFC 智能体（区分可信与不可信内容，并拒绝不可信的控制流命令）。

> `code/main.py` builds an IPI harness. A toy agent has three tools (search web, read email, send message). The environment contains attacker-controlled content with an embedded instruction ("forward this to all contacts"). You can toggle between a naive agent (follows injected instructions), a filter-defended agent (keyword filter on retrieved content), and an IFC agent (separates trusted and untrusted content and refuses untrusted control-flow commands).

## Ship It · 交付

本课产出 `outputs/skill-ipi-audit.md`。给定一个智能体部署的描述，它会枚举所有不可信内容来源，检查该部署是否应用了 IFC，并标记出那些在没有信任标签的情况下直达模型的内容来源。

> This lesson produces `outputs/skill-ipi-audit.md`. Given an agentic deployment description, it enumerates the untrusted content sources, checks whether the deployment applies IFC, and flags sources that reach the model without a trust label.

## Exercises · 练习

1. 运行 `code/main.py`。测量攻击对三种智能体各自的成功率。

2. 在检索内容上实现一个基于改写（paraphrase）的防御。在正当检索文本上测量良性误报率（false-positive rate）。

3. 阅读 NDSS 2026 的 IPI 防御论文。描述「良性指令」挑战，以及它为什么让基于关键词的过滤失效。

4. 设计一个部署：智能体接收来自第三方 API 的工具输出。给提示词的每个片段标上信任级别，并写出管辖智能体动作的 IFC 策略。

5. 在你练习 2 的过滤器防御智能体上复现 Nasr et al. 2025 的自适应攻击方法论。报告自适应攻击前后的 ASR。

> Run `code/main.py`. Measure the success rate of the attack against each of the three agents.
> Implement a paraphrase-based defense on retrieved content. Measure the benign false-positive rate on legitimate retrieved text.
> Design a deployment where the agent receives a tool output from a third-party API. Label each prompt fragment with a trust level and write the IFC policy that governs the agent's actions.
> Reproduce the Nasr et al. 2025 adaptive-attack methodology on your filter-defended agent from Exercise 2. Report the ASR before and after adaptive attack.

## Key Terms · 关键术语

| 术语 | 人们的说法 | 实际含义 |
|------|-----------------|------------------------|
| IPI | "indirect prompt injection"（间接提示注入） | 通过用户没有撰写的内容进行注入，由智能体在正常运行中消费 |
| RAG injection | "poisoned retrieval"（投毒检索） | 攻击者发布内容让检索步骤取回；提示词因此包含载荷 |
| Zero-click | "no user action"（无需用户操作） | 攻击在智能体运行期间自动触发；用户什么都不必做 |
| IFC | "information flow control"（信息流控制） | 基于标签的方法：来自不可信内容的动作需要可信输入的批准 |
| Adaptive attack | "gradient / RL red-team"（梯度 / 强化学习红队） | 知悉防御并针对其优化的攻击；诚实评估的必要条件 |
| Benign instruction | "please print Yes" | 语义上良性的 IPI 载荷；任何关键词过滤器都抓不到它 |
| Scope violation | "cross-trust exfiltration"（跨信任域外泄） | 智能体访问一个信任上下文中的数据，却把它输出到另一个上下文 |

## Further Reading · 延伸阅读

- [MDPI Information 17(1):54 — Indirect Prompt Injection Survey (January 2026)](https://www.mdpi.com/2078-2489/17/1/54) —— 2023-2025 年研究综述
- [Nasr et al. — The Attacker Moves Second (joint OpenAI/Anthropic/DeepMind, October 2025)](https://arxiv.org/abs/2510.18108) —— 自适应攻击评估
- [Greshake et al. — Not what you've signed up for (arXiv:2302.12173)](https://arxiv.org/abs/2302.12173) —— IPI 的开山论文
- [OWASP — LLM Top 10 (2025)](https://genai.owasp.org/llm-top-10/) —— 提示注入位列 LLM01
