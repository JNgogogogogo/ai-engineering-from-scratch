# Action Budgets, Iteration Caps, and Cost Governors · 动作预算、迭代上限与成本治理器

> A mid-sized e-commerce agent's monthly LLM cost jumped from $1,200 to $4,800 after its team enabled the "order-tracking" skill. That is not a pricing bug. That is an agent that found a new loop and kept spending inside it. Microsoft's Agent Governance Toolkit (April 2, 2026) codifies the defense against this class: per-request `max_tokens`, per-task token and dollar budgets, per-day/month caps, iteration caps, tiered model routing, prompt caching, context windowing, HITL checkpoints on expensive actions, kill switches on budget breach. Anthropic's Claude Code Agent SDK ships the same primitives under different names. Financial velocity limits — e.g. cut access on >$50 in 10 minutes — catch loops faster than monthly caps.

**类型:** Learn（学习）
**语言:** Python（仅标准库；分层成本治理器模拟器）
**前置课程:** Phase 15 · 10（Permission modes）、Phase 15 · 12（Durable execution）
**时间:** ~60 分钟

---

## The Problem · 问题在哪

自主 agent 每一轮都在花真金白银。聊天机器人的坏输出是一句糟糕的回答；agent 的坏循环是一张账单。业界对这种失败模式的通用叫法是「Denial of Wallet」（拒绝服务式烧钱）——agent 不停地推理、不停地调工具、不停地计费，而没有任何东西叫停它，因为设计里就没有任何东西负责叫停。

解法不是一个数字，而是**一叠不同时间尺度、不同粒度的限制**：每请求、每任务、每小时、每天、每月。设计良好的一叠限制能在几分钟内抓住失控循环，几小时内抓住缓慢泄漏，一天内抓住糟糕的发布。当 agent 是长程且自主的时候，也正是这一叠限制守住了预算。

这是一堂工程课：数学不难得，难的是纪律——团队栽跟头的都是纪律。下面的限制清单里的每一项，都能在 Microsoft Agent Governance Toolkit 或 Anthropic Claude Code Agent SDK 文档里找到出处。

> Autonomous agents spend real money on every turn. A chatbot's bad output is a bad reply; an agent's bad loop is a bill. The industry-documented term for the failure mode is "Denial of Wallet" — the agent keeps reasoning, keeps tool-calling, keeps billing, and nothing stops it because nothing was designed to.
> The fix is not one number. It is a stack of limits at different time scales and granularities: per-request, per-task, per-hour, per-day, per-month. A well-designed stack catches a runaway loop within minutes, a slow leak within hours, and a bad release within a day. The same stack keeps a budget at all when the agent is long-horizon and autonomous.
> This is an engineering lesson: the math is trivial, the discipline is where teams fail. The list of limits below is all named either in the Microsoft Agent Governance Toolkit or the Anthropic Claude Code Agent SDK docs.

---

## The Concept · 概念

### The cost-governor stack · 成本治理器栈

1. **每请求 `max_tokens`。** 简单。防止任何一次调用吐出无界长度的补全。
2. **每任务 token 预算。** 整个运行期间不超过 N 个 token。到达上限即硬停。
3. **每任务美元预算。** 同 token 预算，但以货币计。Claude Code 里的 `max_budget_usd`。
4. **每工具调用上限。** `WebFetch` 不超过 N 次、`shell_exec` 不超过 N 次等。
5. **迭代上限（`max_turns`）。** agent 循环的总迭代次数；防止无限推理循环。
6. **每分钟 / 每小时 / 每天 / 每月上限。** 滚动窗口。在不同时间尺度上抓住泄漏。
7. **金融速率限制（velocity limit）。** 例如「10 分钟内花费超过 $50 就切断访问」。比月度上限更快抓住基于循环的烧钱。
8. **分层模型路由。** 默认用较小的模型；只有当分类器判断任务配得上时才升级到更大的模型。
9. **提示缓存（prompt caching）。** 系统提示和稳定上下文存进提供商缓存；重发的 token 成本接近零。
10. **上下文开窗（context windowing）。** 用压缩 / 摘要让活跃上下文保持在阈值以下；直接降低 token 成本。
11. **昂贵动作上的 HITL 检查点。** 在已知昂贵的动作之前（长工具调用、大下载、昂贵的模型升级），要求一次人工点击。
12. **预算击穿时的 kill switch。** 任一上限触发即中止会话。触发被记录在案；重新启用要走单独的通道。

> 1. **`max_tokens` per request.** Simple. Prevents any one call from emitting an unbounded completion.
> 2. **Per-task token budget.** Across the whole run, do not exceed N tokens. Hard stop at the cap.
> 3. **Per-task dollar budget.** Same as tokens but in currency. `max_budget_usd` in Claude Code.
> 4. **Per-tool call cap.** No more than N `WebFetch` calls, N `shell_exec` calls, etc.
> 5. **Iteration cap (`max_turns`).** Total agent loop iterations; prevents infinite reasoning loops.
> 6. **Per-minute / per-hour / per-day / per-month cap.** Rolling windows. Catches leaks at different time scales.
> 7. **Financial velocity limit.** E.g., "if spend exceeds $50 in 10 minutes, cut access." Catches loop-based burn before monthly caps fire.
> 8. **Tiered model routing.** Default to a smaller model; escalate to a larger one only when a classifier judges the task warrants it.
> 9. **Prompt caching.** System prompt and stable context stored in provider cache; token cost of re-sending is near zero.
> 10. **Context windowing.** Compaction / summarization to keep the active context below a threshold; direct token-cost reduction.
> 11. **HITL checkpoints on expensive actions.** Before an action known to be expensive (long tool call, large download, a costly model upgrade), require a human tap.
> 12. **Kill switch on budget breach.** Session aborts when any cap fires. Cap is recorded; requires a separate re-enable path.

### Why the stack, not one cap · 为什么是一叠限制而不是单个上限

单个月度上限，只有等钱包烧完才能抓住失控的 agent。单个每请求上限，在会话层面什么都抓不住。不同的失败模式需要不同的时间尺度：

- **失控循环**（agent 卡在 5 秒一次的重试里）：被速率限制抓住。
- **缓慢泄漏**（agent 每个任务做的功约是预期的 2 倍）：被每日上限抓住。
- **糟糕的发布**（新版本用了 5 倍 token）：被每周 / 每月上限抓住。
- **合理激增**（真实需求，不是 bug）：被小时 / 天上限抓住，且日志清晰。

> A single monthly cap catches a runaway agent only after the wallet is gone. A single per-request cap catches nothing at the session level. Different failure modes require different time scales:
> - **Runaway loop** (agent stuck in a 5-second retry): caught by velocity limit.
> - **Slow leak** (agent doing ~2x expected work per task): caught by daily cap.
> - **Bad release** (new version uses 5x tokens): caught by weekly / monthly cap.
> - **Legitimate surge** (real demand, not a bug): caught by hour / day cap with clear log.

### A harness budget surface · 一个 harness 的预算接口

Claude Code Agent SDK 暴露（公开文档）：

- `max_turns` — 迭代上限。
- `max_budget_usd` — 美元上限；击穿即中止会话。
- `allowed_tools` / `disallowed_tools` — 工具允许清单与拒绝清单。
- 工具使用之前的 hook 点，用于自定义成本核算。

与权限模式阶梯（第 10 课）组合使用。一个没有 `max_budget_usd` 的 `autoMode` 会话，就是不受治理的自主。Anthropic 明确将 Auto Mode 定位为必须配合预算控制；分类器与成本是正交的。

> The Claude Code Agent SDK exposes (public docs):
> - `max_turns` — iteration cap.
> - `max_budget_usd` — dollar cap; session aborts on breach.
> - `allowed_tools` / `disallowed_tools` — tool allowlist and denylist.
> - Hook points before tool use for custom cost-accounting.
> Combine with the permission-mode ladder (Lesson 10). An `autoMode` session without `max_budget_usd` is ungoverned autonomy. Anthropic explicitly frames Auto Mode as requiring budget controls; the classifier is orthogonal to cost.

### EU AI Act, OWASP Agentic Top 10 · EU AI Act 与 OWASP Agentic Top 10

Microsoft 的 Agent Governance Toolkit 覆盖 OWASP Agentic Top 10 和 EU AI Act 第 14 条（人类监督）的要求。在欧盟做生产部署，日志和上限执行不是可选项。

> Microsoft's Agent Governance Toolkit covers the OWASP Agentic Top 10 and the EU AI Act Article 14 (human oversight) requirements. For production in the EU, logging and cap enforcement are not optional.

### The observed $1,200 → $4,800 case · 实测的 $1,200 → $4,800 案例

Microsoft 文档里的真实案例：一个电商 agent，在新增一个工具后月成本翻了两番。这个工具允许 agent 在每次会话里轮询订单状态。没有循环检测。没有每工具上限。没有对环比增长的告警。修复是一个每工具上限加一个日增长告警。**这就是一个模板：每一个新的工具面都是一个新的潜在循环；每一个新工具都需要它自己的上限和它自己的告警。**

```figure
cost-governor-stack
```

> The real case in the Microsoft docs: an e-commerce agent whose monthly cost tripled after a new tool was added. The tool allowed the agent to poll order status during every session. No loop detection. No per-tool cap. No alert on week-over-week growth. The fix was a per-tool cap plus a daily-growth alert. This is a template: every new tool surface is a new potential loop; every new tool needs its own cap and its own alert.

---

## Use It · 实战用法

`code/main.py` 模拟一次 agent 运行，分别在「有」和「没有」分层成本治理器栈的情况下。模拟 agent 在若干轮之后漂移进一个轮询循环；分层栈在速率窗口内就抓住了它，而单个月度上限要好几天之后才会触发。

> `code/main.py` simulates an agent run with and without a layered cost-governor stack. The simulated agent drifts into a polling loop after some turns; the layered stack catches it within the velocity window while a single monthly cap would not fire until days later.

---

## Ship It · 交付

`outputs/skill-agent-budget-audit.md` 审计一个拟议 agent 部署的成本治理器栈，并标出缺失的层。

> `outputs/skill-agent-budget-audit.md` audits a proposed agent deployment's cost-governor stack and flags missing layers.

---

## Exercises · 练习

1. 运行 `code/main.py`。确认在轮询循环轨迹上，速率限制比迭代上限先触发。然后禁用速率限制，测量在迭代上限抓住它之前 agent「花」掉了多少。
2. 为一个浏览器 agent（第 11 课）设计一组每工具上限。哪个工具需要最紧的上限？哪个工具可以无上界运行而没有风险？
3. 读 Microsoft Agent Governance Toolkit 文档。列出工具包点名的每一种上限类型。把每一种映射到一个失败模式（失控循环、缓慢泄漏、糟糕发布、合理激增）。
4. 给一次通宵无人值守运行定价（一个现实任务，例如「给仓库里的 50 个 issue 做分诊」）。把 `max_budget_usd` 设为你点估计的 2 倍。为这个 2 倍给出理由。
5. Claude Code 的 `max_budget_usd` 在会话聚合成本上触发。设计一个你会在外部强制执行的补充性速率限制。什么触发切断？重新启用长什么样？

> 1. Run `code/main.py`. Confirm the velocity limit fires before the iteration cap on a polling-loop trajectory. Now disable the velocity limit and measure how much the agent "spends" before the iteration cap catches it.
> 2. Design a per-tool cap set for a browser agent (Lesson 11). Which tool needs the tightest cap? Which tool can run unbounded without risk?
> 3. Read the Microsoft Agent Governance Toolkit docs. List every cap type the toolkit names. Map each to one of the failure modes (runaway loop, slow leak, bad release, surge).
> 4. Price an overnight unattended run for a realistic task (e.g., "triage 50 issues in a repo"). Set `max_budget_usd` at 2x your point estimate. Justify the 2x.
> 5. Claude Code's `max_budget_usd` fires on session aggregate cost. Design a complementary velocity limit you would enforce externally. What triggers the cut-off, and what does re-enable look like?

---

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|---|---|---|
| Denial of Wallet | 「失控账单」 | agent 循环不断产生花费，而没有任何上限叫停 |
| max_tokens | 「每请求上限」 | 单次补全大小的天花板 |
| max_turns | 「迭代上限」 | 会话内 agent 循环迭代次数的天花板 |
| max_budget_usd | 「美元 kill switch」 | 会话成本上限；击穿即中止 |
| Velocity limit | 「速率上限」 | 短时间窗内的花费限制（例如 $50 / 10 分钟） |
| Tiered routing | 「小模型先行」 | 默认廉价模型；仅当分类器判定值得时才升级 |
| Prompt caching | 「缓存的系统提示」 | 提供商侧缓存把重发 token 成本降到接近零 |
| HITL checkpoint | 「人工批准闸门」 | 昂贵动作之前要求一次人工点击 |

---

## Further Reading · 延伸阅读

- [Anthropic Claude Code Agent SDK — agent loop and budgets](https://code.claude.com/docs/en/agent-sdk/agent-loop) — `max_turns`、`max_budget_usd`、工具允许清单。
- [Microsoft Agent Framework — human-in-the-loop and governance](https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop) — 成本治理检查点。
- [Anthropic — Claude Managed Agents overview](https://platform.claude.com/docs/en/managed-agents/overview) — 提供商侧的成本控制。
- [Anthropic — Prompt caching (Claude API docs)](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) — 缓存机制。
- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 长程 agent 的成本画像。
