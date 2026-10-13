# Browser Agents and Long-Horizon Web Tasks · 浏览器 Agent 与长程 Web 任务

> ChatGPT agent (July 2025) merged Operator and deep research into one browser/terminal agent and set BrowseComp SOTA at 68.9%. OpenAI shut Operator down August 31, 2025 — consolidation at the product layer. Anthropic's Vercept acquisition moved Claude Sonnet on OSWorld from under 15% to 72.5%. WebArena-Verified (ServiceNow, ICLR 2026) fixed 11.3 percentage points of false-negative rate in the original WebArena and shipped the 258-task Hard subset. The numbers are real. So is the attack surface: OpenAI's head of preparedness stated publicly that indirect prompt injection into browser agents "is not a bug that can be fully patched." Documented 2025–2026 attacks: Tainted Memories (Atlas CSRF), HashJack (Cato Networks), and one-click hijacks in Perplexity Comet.

**类型:** Learn（学习）
**语言:** Python（仅标准库；间接提示注入攻击面模型）
**前置课程:** Phase 15 · 10（Permission modes）、Phase 15 · 01（Long-horizon agents）
**时间:** ~45 分钟

---

## The Problem · 问题在哪

浏览器 agent 是一类长程 agent：它读取不受信任的内容，并采取有真实后果的动作。agent 访问的每个页面，都是用户没有写过的输入。每个页面上的每个表单，都是一条潜在的命令通道。2025–2026 的攻击语料表明这绝非假设：Tainted Memories 让攻击者通过一个精心构造的页面把恶意指令绑定进 agent 的记忆；HashJack 把命令藏在 agent 会访问的 URL fragment 里；Perplexity Comet 的劫持一次点击就能得手。

防御侧的图景令人不安。OpenAI 的 preparedness 负责人把那句最要命的话说响了：间接提示注入「不是一个能被完全修补的 bug」。原因在于，这类攻击栖身于 agent 的「读取 vs 行动」边界上，而这个边界在架构上是模糊的——模型读到的每一个 token，原则上都可能被当作指令来解读。

本课把攻击面逐一命名，把基准格局讲清楚（BrowseComp、OSWorld、WebArena-Verified），并建模一个最小的间接提示注入场景，让你能在第 14 课和第 18 课里推理真正的防御手段。

> A browser agent is a long-horizon agent that reads untrusted content and takes consequential actions. Every page the agent visits is an input the user did not write. Every form on every page is a potential command channel. The 2025–2026 attack corpus shows this is not hypothetical: Tainted Memories lets an attacker bind malicious instructions to the agent's memory via a crafted page; HashJack hides commands in URL fragments the agent visits; Perplexity Comet hijacks hit in a single click.
> The defensive picture is uncomfortable. OpenAI's head of preparedness said the quiet part loud: indirect prompt injection "is not a bug that can be fully patched." This is because the attack lives in the agent's reading-vs-acting boundary, which is architecturally fuzzy — every token the model reads could, in principle, be read as an instruction.
> This lesson names the attack surface, names the benchmark landscape (BrowseComp, OSWorld, WebArena-Verified), and models a minimal indirect-prompt-injection scenario so you can reason about real defenses in Lessons 14 and 18.

---

## The Concept · 概念

### The 2026 landscape, in one paragraph per system · 2026 格局：每个系统一段话

**ChatGPT agent（OpenAI）。** 2025 年 7 月发布。统一了 Operator（浏览）与 Deep Research（多小时研究）。2025 年 8 月 31 日关闭独立的 Operator。BrowseComp SOTA 68.9%；在 OSWorld 与 WebArena-Verified 上成绩同样强劲。

**Claude Sonnet + Vercept（Anthropic）。** Anthropic 收购 Vercept，聚焦 computer-use 能力。把 Claude Sonnet 在 OSWorld 上的成绩从 <15% 提升到 72.5%。Claude Computer Use 以工具 API 的形式交付。

**Gemini 3 Pro with Browser Use（DeepMind）。** Browser Use 集成带来 computer-use 控制能力；FSF v3（2026 年 4 月，第 20 课）专门追踪 ML R&D 领域的自主性。

**WebArena-Verified（ServiceNow，ICLR 2026）。** 修复了一个有据可查的问题：原始 WebArena 有约 11.3% 的假阴性率（实际已解出却被判失败的任务）。Verified 版本用人工筛选的成功标准重新判分，并新增 258 题的 Hard 子集（ICLR 2026 论文，openreview.net/forum?id=94tlGxmqkN）。

> **ChatGPT agent (OpenAI).** Launched July 2025. Unifies Operator (browsing) and Deep Research (multi-hour research). Shut down the standalone Operator August 31, 2025. SOTA on BrowseComp at 68.9%; strong numbers on OSWorld and WebArena-Verified.
> **Claude Sonnet + Vercept (Anthropic).** Anthropic's Vercept acquisition focused on computer-use capabilities. Moved Claude Sonnet on OSWorld from <15% to 72.5%. Claude Computer Use ships as a tool API.
> **Gemini 3 Pro with Browser Use (DeepMind).** Browser Use integration ships computer-use controls; FSF v3 (April 2026, Lesson 20) tracks autonomy in the ML R&D domain specifically.
> **WebArena-Verified (ServiceNow, ICLR 2026).** Fixes a well-documented problem: the original WebArena had ~11.3% false-negative rate (tasks marked failed that were actually solved). The Verified release re-grades with human-curated success criteria and adds a 258-task Hard subset (ICLR 2026 paper, openreview.net/forum?id=94tlGxmqkN).

### BrowseComp vs OSWorld vs WebArena · 三大基准对比

| 基准 | 测量什么 | 时间跨度 |
|---|---|---|
| BrowseComp | 在时间压力下从开放网络中找到特定事实 | 分钟级 |
| OSWorld | agent 操作一整个桌面（鼠标、键盘、shell） | 数十分钟 |
| WebArena-Verified | 模拟站点中的事务型 Web 任务 | 分钟级 |
| Hard subset | 带多页面状态转换的 WebArena-Verified 任务 | 数十分钟 |

轴不同。高的 BrowseComp 分数说明 agent 会找事实；它不能说明 agent 会订机票。OSWorld 分数更接近「它在我的桌面上好不好使」。WebArena-Verified 更接近「它能不能跑完一个流程」。**任何生产决策，都需要那个与任务分布相匹配的基准。**

> Different axes. A high BrowseComp score says the agent finds facts; it does not say the agent can book a flight. The OSWorld score is closer to "does it work on my desktop." WebArena-Verified is closer to "can it finish a flow." Any production decision needs the benchmark that matches the task distribution.

### The attack surface, named · 给攻击面一一命名

1. **间接提示注入（Indirect prompt injection）。** 不受信任的页面内容里含有指令。agent 读了。agent 执行了。公开案例：2024 年 Kai Greshake 等人，2025 年 Tainted Memories 论文，2026 年 HashJack（Cato Networks）。
2. **URL fragment / 查询串注入。** 被爬取 URL 的 `#fragment` 或查询串里藏着命令。从不被显式渲染；但仍在 agent 的上下文里。
3. **记忆绑定攻击（Memory-binding attacks）。** 页面指示 agent 写入一条持久记忆（第 12 课讲持久状态）。下个会话，这条记忆在没有可见触发的情况下引爆载荷。
4. **针对已登录会话的 CSRF 形攻击。** Tainted Memories 一类：agent 在某处处于登录态；攻击者的页面发出改状态的请求，agent 带着用户的 cookie 去执行。
5. **一键劫持（One-click hijack）。** 一个视觉上无害的按钮，搭载着 agent 会跟随执行的载荷。Comet 一类。
6. **agent 宿主面上的 Content-Security-Policy 漏洞。** 渲染层和工具层本身就能成为攻击向量；「浏览器里的浏览器 agent」这条技术栈很宽。

> 1. **Indirect prompt injection.** Untrusted page content contains instructions. The agent reads them. The agent executes them. Public examples: 2024 Kai Greshake et al., 2025 Tainted Memories paper, 2026 HashJack (Cato Networks).
> 2. **URL fragment / query injection.** The `#fragment` or query string of a crawled URL contains commands. Never rendered visibly; still inside the agent's context.
> 3. **Memory-binding attacks.** Page instructs the agent to write a persistent memory (Lesson 12 covers durable state). Next session, the memory fires the payload with no visible trigger.
> 4. **CSRF-shaped attacks on authenticated sessions.** Tainted Memories class: agent is logged in somewhere; attacker's page issues state-changing requests the agent executes with the user's cookies.
> 5. **One-click hijack.** A visually innocuous button rides a payload the agent follows. Comet class.
> 6. **Content-Security-Policy holes in the agent's host surface.** The rendering and tool layers can themselves be attack vectors; the browser-in-a-browser-agent stack is wide.

### Why "not fully patchable" · 为什么「无法完全修补」

攻击与 agent 的能力是同构的。agent 必须读取不受信任的内容才能干活。agent 读到的任何内容都可能含有指令。agent 遵循的任何指令都可能与用户的真实请求错位。防御手段（信任边界、分类器、工具允许清单、对有后果动作的人工确认 HITL）能抬高攻击成本、缩小爆炸半径，但**关不掉这一整类攻击**。

这与 Lob 定理（第 8 课）是同一种推理模式：agent 无法证明下一个 token 是安全的；它只能搭建一个让不安全 token 更容易被发现的系统。

> The attack is isomorphic to the agent's capability. The agent must read untrusted content to do its job. Any content the agent reads could contain instructions. Any instructions the agent follows could be misaligned with the user's actual request. Defenses (trust boundaries, classifiers, tool allowlists, HITL on consequential actions) raise the cost of the attack and reduce its blast radius. They do not close the class.
> This is the same reasoning pattern as Lob's theorem (Lesson 8): the agent cannot prove the next token is safe; it can only set up a system where unsafe tokens are more detectable.

### Defense posture that actually ships · 真正能上线的防御姿态

- **读 / 写边界。** 读取永远不产生后果。写入（提交表单、发布内容、调用带副作用的工具）在发起内容来自信任边界之外时，需要重新取得人工批准。
- **每任务的工具允许清单。** agent 可以上网浏览；除非那个工具被显式地为该任务启用，否则它不能发起一笔电汇。第 13 课讲预算。
- **会话隔离。** 浏览器 agent 会话只携带作用域受限的凭证运行。不碰生产认证，不碰个人邮箱。保留每个 HTTP 请求的日志以供审计。
- **内容消毒器（sanitizer）。** 取回的 HTML 在拼进模型上下文之前，先剥离已知坏模式。（能减少低级攻击；挡不住精密载荷。）
- **对有后果动作的 HITL。** propose-then-commit 模式（第 15 课）。
- **记忆上的 canary token。** 某条记忆被触发时，用户能看得见（第 14 课）。

```figure
injection-boundary
```

> - **Read / write boundary.** Reading is never consequential. Writing (submitting a form, posting content, calling a tool with side effects) requires fresh human approval if the initiating content came from outside the trust boundary.
> - **Tool allowlist per task.** The agent can browse; it cannot initiate a wire transfer unless that tool was explicitly enabled for the task. Lesson 13 covers budgets.
> - **Session isolation.** Browser agent sessions run with scoped credentials only. No production auth, no personal email. Logs of every HTTP request retained for audit.
> - **Content sanitizer.** Fetched HTML is stripped of known-bad patterns before being concatenated into the model context. (Reduces the easy attacks; does not stop sophisticated payloads.)
> - **HITL on consequential actions.** Propose-then-commit pattern (Lesson 15).
> - **Canary tokens on memory.** If a memory entry fires, the user sees it (Lesson 14).

---

## Use It · 实战用法

`code/main.py` 对三个合成页面建模一次小型浏览器 agent 运行。一个页面良性；一个在可见文本里带直接的提示注入块；一个带 URL fragment 注入（不可见，但在 agent 的上下文里）。脚本展示 (a) 朴素 agent 会做什么，(b) 读/写边界能抓住什么，(c) 消毒器能抓住什么，(d) 两者都抓不住什么。

> `code/main.py` models a tiny browser-agent run against three synthetic pages. One page is benign, one has a direct prompt-injection blob in visible text, one has a URL-fragment injection (not visible but inside the agent's context). The script shows (a) what a naïve agent would do, (b) what a read/write boundary catches, (c) what a sanitizer catches, (d) what neither catches.

---

## Ship It · 交付

`outputs/skill-browser-agent-trust-boundary.md` 为一个拟议的浏览器 agent 部署划定范围：它触碰哪些信任区、它被授权写什么、以及首次运行前必须就位哪些防御。

> `outputs/skill-browser-agent-trust-boundary.md` scopes a proposed browser-agent deployment: which trust zones it touches, what it is authorized to write, and which defenses must be in place before the first run.

---

## Exercises · 练习

1. 运行 `code/main.py`。找出消毒器能抓住而读/写边界抓不住的那种攻击，以及只有读/写边界能抓住的那种攻击。
2. 扩展消毒器，检测一类 HashJack 风格的 URL fragment 注入。在带合法 fragment 的良性 URL 上测量误报率。
3. 挑一个你熟悉的真实浏览器 agent 工作流（例如「订机票」）。列出每一次读和每一次写。标出哪些写需要 HITL，以及为什么。
4. 读 WebArena-Verified 的 ICLR 2026 论文。找出原始 WebArena 判分不可靠的一类任务，并解释 Verified 子集如何解决它。
5. 为浏览器 agent 场景设计一个记忆 canary。你会存什么、存在哪里、什么触发警报？

> 1. Run `code/main.py`. Identify which attack the sanitizer catches but the read/write boundary does not, and which attack only the read/write boundary catches.
> 2. Extend the sanitizer to detect one class of HashJack-style URL-fragment injection. Measure the false-positive rate on benign URLs with legitimate fragments.
> 3. Pick one real browser-agent workflow you know (e.g., "book a flight"). List every read and every write. Mark which writes need HITL and why.
> 4. Read the WebArena-Verified ICLR 2026 paper. Identify one category of task where the original WebArena's scoring was unreliable and explain how the Verified subset resolves it.
> 5. Design a memory canary for a browser-agent setting. What would you store, where, and what triggers the alarm?

---

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|---|---|---|
| Indirect prompt injection | 「坏页面文本」 | agent 所读页面中的不受信内容，含有 agent 会执行的指令 |
| Tainted Memories | 「记忆攻击」 | agent 把攻击者提供的指令写进持久记忆；下个会话触发 |
| HashJack | 「URL fragment 攻击」 | 藏在 URL fragment / 查询串里的载荷在 agent 上下文中，但不被显式渲染 |
| One-click hijack | 「坏按钮」 | 可见的界面元素搭载着 agent 会执行的后续载荷 |
| BrowseComp | 「网页搜索基准」 | 在开放网络中找特定事实；分钟级时间跨度 |
| OSWorld | 「桌面基准」 | 完整操作系统控制；多步 GUI 任务 |
| WebArena-Verified | 「修复版 Web 任务基准」 | ServiceNow 重新判分的 WebArena，附 Hard 子集 |
| Read/write boundary | 「副作用闸门」 | 读取从不产生后果；内容越出信任边界时，写入需重新批准 |

---

## Further Reading · 延伸阅读

- [OpenAI — Introducing ChatGPT agent](https://openai.com/index/introducing-chatgpt-agent/) — Operator 与 deep research 合并；BrowseComp SOTA。
- [OpenAI — Computer-Using Agent](https://openai.com/index/computer-using-agent/) — Operator 的谱系，以及演化为 ChatGPT agent 的架构。
- [Zhou et al. — WebArena](https://webarena.dev/) — 原始基准。
- [WebArena-Verified (OpenReview)](https://openreview.net/forum?id=94tlGxmqkN) — ICLR 2026 修复子集论文。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 含 computer-use agent 的攻击面讨论。
