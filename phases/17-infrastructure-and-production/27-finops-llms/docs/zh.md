# FinOps for LLMs — Unit Economics and Multi-Tenant Attribution · LLM 的 FinOps——单位经济模型与多租户成本归因

> 传统 FinOps 在 LLM 开销上会失灵。成本是 token 交易，不是资源运行时长。标签（tag）对不上——一次 API 调用是一笔交易，不是一项资产。工程决策（提示词设计、上下文窗口、输出长度）就是财务决策。2026 年的打法是在第一天就埋好三个归因（attribution）维度：按用户（`user_id`，用于席位定价和扩张）、按任务（`task_id` + `route`，用于产品面成本和优先级排序）、按租户（`tenant_id`，用于单位经济模型和续约）。四层 token——提示词、工具、记忆、响应——混在一个桶里就会藏住开销。多租户产品的执行阶梯：按租户限流（预期峰值的 2-3 倍，返回清晰的 429 + retry-after）；每日消费上限（合同上限的 1.5-3 倍；触发限流收紧 + 告警）；消费 z-score > 4 时触发 kill switch（自动暂停 + 呼叫值班）。归因模式：tag-and-aggregate、telemetry-joiner（trace-ID → 账单；准确度最高）、sampling-and-extrapolation、model-based allocation、event-sourced、real-time streaming。单位指标：每解决一次查询的成本、每生成一个制品的成本——不是 $/M tokens。事后补标签必然漏；要在请求创建时就埋点。

> Traditional FinOps breaks on LLM spend. Costs are token-transactions, not resource-uptime. Tags don't map — an API call is a transaction, not an asset. Engineering decisions (prompt design, context window, output length) are financial decisions. The 2026 playbook has three attribution dimensions to instrument on day one: per-user (`user_id`) for seat pricing and expansion, per-task (`task_id` + `route`) for product surface cost and prioritization, per-tenant (`tenant_id`) for unit economics and renewal. Four token layers — prompt, tool, memory, response — one bucket hides spend. Enforcement ladder for multi-tenant products: rate limits per tenant (2-3x expected peak, clear 429 + retry-after); daily spend cap (1.5-3x contracted ceiling; triggers rate tightening + alert); kill switches on spend z-score > 4 (auto-pause + page on-call). Attribution patterns: tag-and-aggregate, telemetry-joiner (trace-ID → billing; highest accuracy), sampling-and-extrapolation, model-based allocation, event-sourced, real-time streaming. Unit metric: cost per resolved query, cost per generated artifact — not $/M tokens. Retroactive tagging always misses; instrument at request creation.

**Type:** Learn
**Languages:** Python (stdlib, toy cost-attribution simulator with kill switch)
**Prerequisites:** Phase 17 · 13 (Observability), Phase 17 · 14 (Caching)
**Time:** ~60 minutes

---

## Learning Objectives · 学习目标

- 解释为什么传统 FinOps（标签 + 分层）在 LLM 开销上失灵，并说出三个新的归因维度
- 列举四层 token（提示词、工具、记忆、响应），以及为什么单桶计费会藏住成本
- 为多租户产品设计执行阶梯（限流 → 消费上限 → kill switch）
- 选单位指标（每解决一次查询 / 每个制品的成本），而不是 $/M tokens

> Explain why traditional FinOps (tags + tiers) breaks on LLM spend and name the three new attribution dimensions.
> Enumerate the four token layers (prompt, tool, memory, response) and why single-bucket billing hides cost.
> Design an enforcement ladder (rate → spend cap → kill switch) for a multi-tenant product.
> Pick a unit metric (cost per resolved query / artifact) instead of $/M tokens.

---

## The Problem · 问题在哪

账单写着 $40,000。你不知道：
- 哪个租户花的。
- 哪个产品功能带动的。
- 有没有个别用户在滥用。
- 罪魁是提示词膨胀、工具调用，还是记忆放大。

供应商侧的 tag-and-aggregate 对云资源（EC2、S3）有效，因为标签会传导到账单行。LLM API 调用不会自动打标签——你必须在调用点打上 user/task/tenant 戳并一路携带。事后归因必然会漏掉边缘情况。

> Your bill says $40,000. You don't know:
> - Which tenant spent it.
> - Which product feature drove it.
> - Whether any individual user was abusive.
> - Whether prompt bloat, tool calls, or memory amplification was the culprit.
> Tag-and-aggregate on provider-side works for cloud resources (EC2, S3) where tags propagate to line items. LLM API calls do not auto-tag — you have to stamp user/task/tenant at the call site and carry through. Retroactive attribution always misses edge cases.

---

## The Concept · 概念

### Three attribution dimensions · 三个归因维度

**按用户（Per-user）**（`user_id`）：谁在花多少钱。驱动席位定价、扩张谈判，识别重度用户。

**按任务（Per-task）**（`task_id` + `route`）：哪个产品面在花多少钱。驱动功能优先级排序、砍掉昂贵功能的决策。

**按租户（Per-tenant）**（`tenant_id`）：哪个客户在赚钱。驱动单位经济模型、续约定价、套餐阈值。

第一天就在调用点把三个都埋上。事后补永远更糟。

> **Per-user** (`user_id`): who is costing what. Drives seat pricing, expansion conversations, identifies power users.
> **Per-task** (`task_id` + `route`): which product surface costs what. Drives feature prioritization, kill-expensive-features decisions.
> **Per-tenant** (`tenant_id`): which customer is profitable. Drives unit economics, renewal pricing, tier thresholds.
> Instrument all three at call site on day one. Retroactive is always worse.

### Four token layers · 四层 token

| 层 | 例子 | 占总量的典型比例 |
|-------|---------|---------------------|
| Prompt（提示词） | system + 用户输入 | 40-60% |
| Tool（工具） | 回喂的工具调用结果 | 20-40%（agent 工作负载） |
| Memory（记忆） | 历史对话 / 检索到的文档 | 10-30% |
| Response（响应） | 模型输出 | 10-30% |

四层混进一个桶，优化就成了盲人摸象。在归因 schema 里把它们拆开。

> Bucketing all four together makes optimization blind. Break them out in your attribution schema.

### Enforcement ladder · 执行阶梯

1. **限流（Rate limit）**：按租户。预期峰值的 2-3 倍。返回带 `Retry-After` 的 429。租户感到摩擦；账单不会爆雷。

2. **每日消费上限（Daily spend cap）**：按租户。合同上限的 1.5-3 倍。触发动作：收紧限流 + 告警客户成功团队。

3. **Kill switch**：消费相对租户基线的 z-score > 4 时触发。自动暂停租户；呼叫值班；升级到运营 + 客户成功。

> **Rate limit** per tenant. 2-3x expected peak. Return 429 with `Retry-After`. Tenant sees friction; no surprise bill. ... **Daily spend cap** per tenant. 1.5-3x contracted ceiling. Trigger: tighten rate limit + alert customer-success. ... **Kill switch** on spend z-score > 4 relative to tenant baseline. Auto-pause tenant; page on-call; escalate to ops + CS.

### Attribution patterns · 归因模式

- **Tag-and-aggregate（打标聚合）**：打上元数据头；之后聚合。简单；粗糙。
- **Telemetry joiner（遥测拼接）**：用 trace ID 把 trace 关联到账单。准确度最高。成熟团队的做法。
- **Sampling + extrapolation（采样外推）**：采样 5-10%，再乘回去。对粗略开销划算；会漏尾部。
- **Model-based allocation（模型分摊）**：用回归推断成本驱动因素。适用于没有标签的存量数据。
- **Event-sourced（事件溯源）**：成本作为事件进流（Kafka / Kinesis）。实时。
- **Real-time streaming（实时流）**：仪表盘亚秒级更新。

> **Tag-and-aggregate**: stamp metadata headers; aggregate later. Simple; rough. ... **Telemetry joiner**: join traces to billing via trace IDs. Highest accuracy. What mature teams do. ... **Sampling + extrapolation**: sample 5-10%, multiply. Cost-effective for rough spend; misses tails. ... **Real-time streaming**: dashboard updates sub-second.

### Cost per X is the unit metric · 「每 X 的成本」才是单位指标

$/M tokens 是供应商的话术。产品指标是：

- 每解决一张支持工单的成本。
- 每生成一篇文章的成本。
- 每个成功 agent 任务的成本。
- 每用户会话分钟的成本。

把成本绑到产品结果上。否则优化就没有锚点。

> $/M tokens is vendor speak. Product metrics:
> - Cost per resolved support ticket.
> - Cost per generated article.
> - Cost per successful agent task.
> - Cost per user-session-minute.
> Tie cost to a product outcome. Otherwise optimization is unanchored.

### Cost attribution trace shape · 成本归因 trace 的形状

```
trace_id: abc123
  user_id: u_42
  tenant_id: t_7
  task_id: task_classify_doc
  route: model_haiku
  layers:
    prompt_tokens: 1800
    tool_tokens: 600
    memory_tokens: 400
    response_tokens: 150
  cost_usd: 0.0135
  cached_input: true
  batch: false
```

每次调用都发。存进数据湖。按维度聚合。Phase 17 · 13 的可观测性栈就是它的家。

> Emit on every call. Store in data lake. Aggregate per dimension. Phase 17 · 13 observability stack is where this lives.

### The compounded-savings stack · 复利式省钱栈

栈：cache + batch + route + gateway。四件套全开：
- Cache L2（Phase 17 · 14）：输入便宜约 10 倍。
- Batch（Phase 17 · 15）：五折。
- 路由到便宜模型（Phase 17 · 16）：成本降 60%。
- Gateway 效率（Phase 17 · 19）：冗余 + 重试。

最好情况的叠加效果：约是朴素基线的 5-10%。大多数团队用上 2-3 个杠杆；能把四个全叠起来的很少。

> Stack: cache + batch + route + gateway. With all four:
> - Cache L2 (Phase 17 · 14): ~10x cheaper input.
> - Batch (Phase 17 · 15): 50% off.
> - Route to cheap model (Phase 17 · 16): 60% cost reduction.
> - Gateway efficiency (Phase 17 · 19): redundancy + retries.
> Best-case stacked: ~5-10% of naive baseline. Most teams have 2-3 levers engaged; few stack all four.

### Numbers you should remember · 该记住的数字

- 归因维度：按用户、按任务、按租户。
- 四层 token：提示词、工具、记忆、响应。
- Kill switch：消费 z-score > 4。
- 单位指标：每解决一次查询的成本，不是 $/M tokens。
- 叠加优化：可以压到基线的约 5-10%。

> Attribution dimensions: per-user, per-task, per-tenant.
> Four token layers: prompt, tool, memory, response.
> Kill switch: spend z-score > 4.
> Unit metric: cost per resolved query, not $/M tokens.
> Stacked optimizations: ~5-10% of baseline possible.

```figure
i4-spend-ladder
```

---

## Use It · 实战用法

`code/main.py` 模拟一个带三级执行阶梯的多租户 LLM 服务。注入一个滥用租户并演示 kill switch 触发。

> `code/main.py` simulates a multi-tenant LLM service with the three-tier enforcement ladder. Injects an abusive tenant and demonstrates the kill switch firing.

---

## Ship It · 交付

本课产出 `outputs/skill-finops-plan.md`。输入产品和规模，它设计归因 schema 和执行阶梯。

> This lesson produces `outputs/skill-finops-plan.md`. Given product and scale, designs the attribution schema and enforcement ladder.

---

## Exercises · 练习

1. 跑 `code/main.py`。kill switch 在什么 z-score 触发？这个阈值你怎么选？
2. 设计一个按租户、按任务的成本仪表盘。你会最先建的 5 个视图是什么？
3. 你最大的租户单位经济模型是负的。按客户影响排序，提出三个干预手段。
4. 给一个客服产品计算每解决一张工单的成本：3M tokens/工单，约 800 工单/天，GPT-5 缓存价。
5. 论证事后补标签（retroactive tagging）是否可能行得通。什么时候可以接受？

---

## Key Terms · 术语表

| 术语 | 人们口头说 | 实际含义 |
|------|----------------|------------------------|
| Per-user attribution | 「用户级成本」 | 每次调用都打上 `user_id` |
| Per-task attribution | 「功能成本」 | `task_id` + `route` 标识产品面 |
| Per-tenant attribution | 「客户成本」 | `tenant_id`；驱动单位经济模型 |
| Four token layers | 「成本分层」 | prompt + tool + memory + response |
| Rate limit | 「429 守门」 | 网关处执行的按租户上限 |
| Daily spend cap | 「每日天花板」 | 租户级预算 + 告警 |
| Kill switch | 「自动暂停」 | 消费 z-score > 4 触发自动停用 |
| Cost per resolved | 「产品单位指标」 | 成本绑产品结果，而不是 token |
| Telemetry joiner | 「trace 关联账单」 | 准确度最高的归因模式 |
| Stacked optimization | 「cache+batch+route+gateway」 | 叠加省钱压到基线的约 5-10% |

---

## Further Reading · 延伸阅读

- [FinOps Foundation — FinOps for AI Overview](https://www.finops.org/wg/finops-for-ai-overview/)
- [FinOps School — Cost per Unit 2026 Guide](https://finopsschool.com/blog/cost-per-unit/)
- [Digital Applied — LLM Agent Cost Attribution 2026](https://www.digitalapplied.com/blog/llm-agent-cost-attribution-guide-production-2026)
- [PointFive — Managed LLMs in Azure OpenAI](https://www.pointfive.co/blog/finops-for-ai-economics-of-managed-llms-in-azure-open-ai)
