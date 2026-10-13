# Production Agent Runtimes — Fast Instantiation and Typed Workflows · 生产级 Agent 运行时——快速实例化与类型化工作流

> 生产级 agent 运行时优化的，是原型框架不屑一顾的东西：实例化成本、类型化的工作流接口、开箱即可上线服务的后端。2026 年的一对组合：Agno（Python）瞄准微秒级 agent 实例化和无状态 FastAPI 后端；Mastra 在 Vercel AI SDK 地基上提供 agents、工具、工作流、统一模型路由与组合式存储。
>
> A production agent runtime optimizes what prototyping frameworks ignore: instantiation cost, typed workflow surfaces, and a serving-ready backend. The 2026 pairing: Agno (Python) aims at microsecond agent instantiation and stateless FastAPI backends. Mastra ships agents, tools, workflows, unified model routing, and composite storage on the Vercel AI SDK substrate.

**Type:** Learn
**Languages:** Python, TypeScript
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 13 (LangGraph)
**Time:** ~45 minutes

## Learning Objectives · 学习目标

- 说出 Agno 的性能指标，以及它们什么时候才要紧。
- 说出 Mastra 的三个原语——Agents、Tools、Workflows——以及它支持的服务器适配器。
- 解释为什么「无状态、会话作用域的 FastAPI 后端」是 Agno 推荐的生产路径。
- 针对给定的技术栈（Python 优先 vs TypeScript 优先）在 Agno 与 Mastra 之间做选择。

> Identify Agno's performance targets and when they matter.
> Name Mastra's three primitives — Agents, Tools, Workflows — and the supported server adapters.
> Explain why a stateless session-scoped FastAPI backend is the recommended Agno production path.
> Pick Agno vs Mastra for a given stack (Python-first vs TypeScript-first).

## The Problem · 问题在哪

LangGraph、AutoGen、CrewAI 都是重框架。那些想要「就要那个 agent 循环，要快，要跑在我自己的运行时里」的团队，会转向 Agno（Python）或 Mastra（TypeScript）。两者都拿一部分「框架管到底的原语」，换来了原始速度和与周边技术栈更紧的贴合。

> LangGraph, AutoGen, CrewAI are framework-heavy. Teams that want "just the agent loop, fast, in my runtime" reach for Agno (Python) or Mastra (TypeScript). Both trade some of the framework-owned primitives for raw speed and a tighter fit to the surrounding stack.

## The Concept · 概念

### Agno · Agno

- Python 运行时，前身是 Phi-data。
- 「没有图、没有链、没有绕来绕去的模式——只有纯 Python。」
- 官方文档给出的性能指标：约 2μs 实例化一个 agent，每个 agent 约 3.75 KiB 内存，约 23 家模型提供商。
- 生产路径：无状态、会话作用域的 FastAPI 后端。每个请求启动一个全新 agent；会话状态存在数据库里。
- 原生多模态（文本、图像、音频、视频、文件）与 agentic RAG。

> - Python runtime, formerly Phi-data.
> - "No graphs, chains, or convoluted patterns — just pure python."
> - Performance targets from their docs: ~2μs agent instantiation, ~3.75 KiB memory per agent, ~23 model providers.
> - Production path: stateless session-scoped FastAPI backend. Each request starts a fresh agent; session state lives in a DB.
> - Native multimodal (text, image, audio, video, file) and agentic RAG.

当你每秒要跑成千上万个短命 agent（聊天扇入、评估流水线）时，这些速度指标才真正要紧。如果一个 agent 一跑就是 10 分钟，它们就不那么重要了。

> The speed targets matter when you have thousands of short-lived agents per second (chat fan-in, evaluation pipelines). They matter less when one agent runs for 10 minutes.

### Mastra · Mastra

- TypeScript，构建在 Vercel AI SDK 之上。
- 三个原语：**Agents**、**Tools**（Zod 类型化）、**Workflows**。
- 统一模型路由（Unified Model Router）——横跨 94 家提供商的 3300+ 个模型（2026 年 3 月）。
- 组合式存储：memory、workflows、observability 可以各自落到不同后端；大规模可观测性场景推荐 ClickHouse。
- Apache 2.0，但 `ee/` 目录采用 source-available 企业许可证。
- 服务器适配器覆盖 Express、Hono、Fastify、Koa；Next.js 和 Astro 有一等公民级集成。
- 自带 Mastra Studio（localhost:4111）用于调试。
- 1.0 发布时（2026 年 1 月）已有 22k+ GitHub stars，npm 周下载 30 万+。

> - TypeScript, built on Vercel AI SDK.
> - Three primitives: **Agents**, **Tools** (Zod-typed), **Workflows**.
> - Unified Model Router — 3,300+ models across 94 providers (March 2026).
> - Composite storage: memory, workflows, observability to different backends; ClickHouse recommended for observability at scale.
> - Apache 2.0 with `ee/` directories under source-available enterprise license.
> - Server adapters for Express, Hono, Fastify, Koa; first-class Next.js and Astro integration.
> - Ships Mastra Studio (localhost:4111) for debugging.
> - 22k+ GitHub stars, 300k+ weekly npm downloads at 1.0 (Jan 2026).

### Positioning · 定位

谁都没想成为 LangGraph。它们的竞争点在：

- **语言契合度。** Python 优先的团队选 Agno；TypeScript 优先的选 Mastra。
- **运行时人体工学。** Agno = 近零开销；Mastra = 与 Vercel 生态深度集成。
- **可观测性。** 两者都集成 Langfuse/Phoenix/Opik（第 24 课），但 Mastra Studio 是一方自带。

> Neither is trying to be LangGraph. They compete on:
> - **Language fit.** Agno for Python-first teams; Mastra for TypeScript-first.
> - **Runtime ergonomics.** Agno = near-zero overhead; Mastra = integrated with the Vercel ecosystem.
> - **Observability.** Both integrate with Langfuse/Phoenix/Opik (Lesson 24) but Mastra Studio is first-party.

### When to pick each · 什么时候选谁

- **Agno** —— Python 后端、大量短命 agent、强性能要求、FastAPI 技术栈。
- **Mastra** —— TypeScript 后端、Next.js / Vercel 部署、统一的多提供商模型路由、Zod 类型化工具。
- **LangGraph**（第 13 课）—— 当持久化状态和显式的图推理比原始速度更重要时。
- **OpenAI / Claude Agent SDK** —— 当你想要提供商自家产品化的形态（第 16–17 课）。

> - **Agno** — Python backend, many short-lived agents, strong perf requirements, FastAPI shop.
> - **Mastra** — TypeScript backend, Next.js / Vercel deploy, unified multi-provider model routing, Zod-typed tools.
> - **LangGraph** (Lesson 13) — when durable state and explicit graph reasoning matter more than raw speed.
> - **OpenAI / Claude Agent SDK** — when you want the provider's productized shape (Lessons 16–17).

### Where this pattern goes wrong · 这个模式的常见坑

- **为性能而性能。** 明明负载是「每请求一次慢吞吞的 agent 调用」，却因为「2μs」听着带感就选 Agno。开销根本不是瓶颈。
- **生态锁定。** Mastra 的 Vercel 风味集成在 Vercel 上是加分项，换个地方就是减分项。
- **企业许可证混淆。** Mastra 的 `ee/` 目录是 source-available，不是 Apache 2.0。打算 fork 的话先把许可证读清楚。

> - **Perf-for-perf's-sake.** Picking Agno because "2μs" sounds good when the workload is one slow agent call per request. Overhead is not the bottleneck.
> - **Ecosystem lock-in.** Mastra's Vercel-flavored integration is a plus on Vercel, a minus elsewhere.
> - **Enterprise license confusion.** Mastra's `ee/` directories are source-available, not Apache 2.0. Read the licenses if you're planning to fork.

```figure
wb-runtime-spawn
```

## Build It · 动手造

本课以对比为主——单独一个代码工件没法同时讲清楚两个框架。`code/main.py` 给出了一个并排的玩具实现：把「跑一个 agent、流式输出、持久化会话」的最小流程实现了两遍（一遍 Agno 形态，一遍 Mastra 形态）。

运行：

```
python3 code/main.py
```

> This lesson is primarily comparative — no single code artifact would do both frameworks justice. See `code/main.py` for a side-by-side toy: a minimal "run an agent, stream the output, persist session" flow implemented twice (once Agno-shaped, once Mastra-shaped).

两份结构不同但功能等价的追踪输出。

> Two structurally different but functionally equivalent traces.

## Use It · 实战用法

- **Agno** —— 需要速度和 FastAPI 形态的 Python 后端。
- **Mastra** —— 多提供商、需要工作流原语的 TypeScript 后端。
- 两者都自带一方的可观测性钩子。两者都集成 Langfuse。

> - **Agno** — Python backend that needs speed and FastAPI shape.
> - **Mastra** — TypeScript backend with many providers and workflow primitives.
> - Both ship first-party observability hooks. Both integrate with Langfuse.

## Ship It · 交付

`outputs/skill-runtime-picker.md` 依据技术栈、延迟预算和运维形态，在 Agno、Mastra、LangGraph 或某个提供商 SDK 之间做选择。

> `outputs/skill-runtime-picker.md` picks Agno, Mastra, LangGraph, or a provider SDK based on stack, latency budget, and operational shape.

## Exercises · 练习

1. 读 Agno 的文档。把纯标准库的 ReAct 循环（第 01 课）移植到 Agno。什么消失了？什么还在？
2. 读 Mastra 的文档。把同一个循环移植到 Mastra。工具类型上有什么变化（Zod vs 什么都没有）？
3. 做个基准：在你的技术栈上实测 agent 实例化延迟。Agno 的 2μs 对你的负载要紧吗？
4. 设计一次迁移：如果你一直在 Python 里跑 CrewAI，迁到 Agno 会破坏什么？
5. 读 Mastra 的 `ee/` 许可证条款。哪些限制会影响开源 fork？

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| Agno | 「快的 Python agent」 | 无状态、会话作用域的 agent 运行时 |
| Mastra | 「Vercel AI SDK 上的 TypeScript agent」 | Agents + Tools + Workflows + Model Router |
| Unified Model Router | 「多提供商接入」 | 一个客户端覆盖 94 家提供商的 3300+ 个模型 |
| Composite storage | 「多后端」 | memory/workflows/observability 各自落到不同存储 |
| Mastra Studio | 「本地调试器」 | localhost:4111 上内省 agent 的 UI |
| Source-available | 「不是开源」 | 许可证允许阅读源码，但限制商用 |

## Further Reading · 延伸阅读

- [Agno Agent Framework docs](https://www.agno.com/agent-framework) —— 性能指标、FastAPI 集成
- [Mastra docs](https://mastra.ai/docs) —— 原语、服务器适配器、Model Router
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) —— 有状态图的替代方案
- [Comet Opik](https://www.comet.com/site/products/opik/) —— Mastra 集成文档引用的可观测性对比
