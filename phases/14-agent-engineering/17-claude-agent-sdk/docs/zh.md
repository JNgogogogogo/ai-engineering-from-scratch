# The Harness as a Library — Subagents and Session Store · 把 Harness 做成库——子代理与会话存储

> 一个可以 import 的 harness：内置工具、用于上下文隔离的子代理、生命周期钩子、W3C 追踪传播、会话持久化。Claude Agent SDK 是参考范例——Claude Code harness 的库形态；Claude Managed Agents 则是面向长时异步任务的托管替代方案。
>
> A harness you can import: built-in tools, subagents for context isolation, hooks, W3C trace propagation, session persistence. The Claude Agent SDK is the reference example — the library form of the Claude Code harness — and Claude Managed Agents is the hosted alternative for long-running async work.

**Type:** Learn + Build
**Languages:** Python (stdlib)
**Prerequisites:** Phase 14 · 01 (Agent Loop), Phase 14 · 10 (Skill Libraries)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 解释 Anthropic Client SDK（裸 API）与 Claude Agent SDK（harness 形态）的区别。
- 描述子代理（subagent）——并行化与上下文隔离——以及什么时候该动用它。
- 说出 Python SDK 会话存储的接口面（`append`、`load`、`list_sessions`、`delete`、`list_subkeys`）以及 `--session-mirror` 的作用。
- 用纯标准库实现一个 harness：内置工具、带隔离上下文的子代理生成、生命周期钩子、会话存储。

> Explain the difference between the Anthropic Client SDK (raw API) and the Claude Agent SDK (harness shape).
> Describe subagents — parallelization and context isolation — and when to reach for them.
> Name the Python SDK's session store surface (`append`, `load`, `list_sessions`, `delete`, `list_subkeys`) and the role of `--session-mirror`.
> Implement a stdlib harness with built-in tools, subagent spawning with isolated context, lifecycle hooks, and a session store.

## The Problem · 问题在哪

裸的 LLM API 只给你一次往返。生产级 agent 需要工具执行、MCP 服务器、生命周期钩子、子代理生成、会话持久化、追踪传播。Claude Agent SDK 把这套形态打包成一个库——与 Claude Code 用的是同一个 harness，只是开放出来给自定义 agent 用。

> A raw LLM API gets you one round-trip. A production agent needs tool execution, MCP servers, lifecycle hooks, subagent spawning, session persistence, trace propagation. Claude Agent SDK ships this shape as a library — the same harness Claude Code uses, exposed for custom agents.

## The Concept · 概念

### Client SDK vs Agent SDK · Client SDK 与 Agent SDK

- **Client SDK（`anthropic`）。** 裸的 Messages API。循环、工具、状态全都由你自己负责。
- **Agent SDK（`claude-agent-sdk`）。** 内置工具执行、MCP 连接、钩子、子代理生成、会话存储。把 Claude Code 的循环做成了库。

> **Client SDK (`anthropic`).** Raw Messages API. You own the loop, the tools, the state.
> **Agent SDK (`claude-agent-sdk`).** Built-in tool execution, MCP connections, hooks, subagent spawning, session store. The Claude Code loop as a library.

### Built-in tools · 内置工具

SDK 开箱自带 10+ 个工具：文件读写、shell、grep、glob、网页抓取等等。自定义工具通过标准的 tool-schema 接口注册。

> The SDK ships 10+ tools out of the box: file read/write, shell, grep, glob, web fetch, more. Custom tools register via the standard tool-schema interface.

### Subagents · 子代理

Anthropic 文档写明的两个用途：

1. **并行化。** 把相互独立的工作并发跑。「给这 20 个模块分别找出对应的测试文件」就是 20 个并行的子代理任务。
2. **上下文隔离。** 子代理使用自己的上下文窗口；只有结果会返回给编排者（orchestrator）。编排者的预算得以保住。

Python SDK 近期新增：`list_subagents()` 和 `get_subagent_messages()`，用于读取子代理的完整记录。

> Two purposes documented by Anthropic:
> 1. **Parallelization.** Run independent work concurrently. "Find the test file for each of these 20 modules" is 20 parallel subagent tasks.
> 2. **Context isolation.** Subagents use their own context window; only results return to the orchestrator. The orchestrator's budget is preserved.
> Python SDK recent additions: `list_subagents()`, `get_subagent_messages()` for reading subagent transcripts.

### Session store · 会话存储

与 TypeScript 版的协议对齐：

- `append(session_id, message)` —— 追加一轮对话。
- `load(session_id)` —— 恢复会话。
- `list_sessions()` —— 枚举所有会话。
- `delete(session_id)` —— 删除，并级联删除子代理会话。
- `list_subkeys(session_id)` —— 列出子代理的 key。

`--session-mirror`（CLI 标志）在流式传输的同时把会话记录镜像到外部文件，便于调试。

> Protocol parity with TypeScript:
> - `append(session_id, message)` — add a turn.
> - `load(session_id)` — restore conversation.
> - `list_sessions()` — enumerate.
> - `delete(session_id)` — with cascade to subagent sessions.
> - `list_subkeys(session_id)` — list subagent keys.
> `--session-mirror` (CLI flag) mirrors the transcript to an external file as it streams, for debugging.

### Hooks · 生命周期钩子

可以注册的生命周期钩子：

- `PreToolUse`、`PostToolUse` —— 对工具调用做门禁或审计。
- `SessionStart`、`SessionEnd` —— 建立与清理环境。
- `UserPromptSubmit` —— 在模型看到用户输入之前先行处理。
- `PreCompact` —— 在上下文压缩之前运行。
- `Stop` —— agent 退出时的清理。
- `Notification` —— 旁路告警。

钩子是 pro-workflow（Phase 14 课程参照）这类系统添加横切行为的手段。

> Lifecycle hooks you can register:
> - `PreToolUse`, `PostToolUse` — gate or audit tool calls.
> - `SessionStart`, `SessionEnd` — set up and tear down.
> - `UserPromptSubmit` — act on user input before the model sees it.
> - `PreCompact` — run before context compaction.
> - `Stop` — cleanup on agent exit.
> - `Notification` — side-channel alerts.
> Hooks are how pro-workflow (Phase 14 curriculum reference) and similar systems add cross-cutting behavior.

### W3C trace context · W3C 追踪上下文

调用方处于活跃状态的 OTel span 会通过 W3C trace context 头传播进 CLI 子进程。整条多进程追踪链在你的后端里呈现为同一条 trace。

> OTel spans active on the caller propagate into the CLI subprocess via W3C trace context headers. The whole multi-process trace shows up as one trace in your backend.

### Claude Managed Agents · Claude Managed Agents（托管代理）

托管的替代方案（beta header `managed-agents-2026-04-01`）。面向长时异步任务，内置 prompt 缓存、内置压缩。用可控性换取托管基础设施。

> The hosted alternative (beta header `managed-agents-2026-04-01`). Long-running async work, built-in prompt caching, built-in compaction. Trade control for managed infrastructure.

### Where this pattern goes wrong · 这个模式的常见坑

- **子代理滥开。** 100 个小任务开 100 个子代理。开销反客为主。应该批量合并。
- **钩子蔓延。** 每个团队都往里加钩子；启动时间暴涨。每季度评审一次钩子。
- **会话膨胀。** 会话不断累积；体积越滚越大。用 `list_sessions` 加过期策略来治理。

> **Subagent over-spawn.** Spawning 100 subagents for 100 tiny tasks. Overhead dominates. Batch instead.
> **Hook creep.** Every team adds hooks; startup time balloons. Review hooks quarterly.
> **Session bloat.** Sessions accumulate; size grows. Use `list_sessions` + expiry policy.

```figure
ae-subagent-isolation
```

## Build It · 动手造

`code/main.py` 用标准库实现了 SDK 的形态：

- `Tool` 与 `ToolRegistry`，内置 `read_file`、`write_file`、`list_dir`。
- `Subagent` —— 私有上下文、隔离运行、返回结果。
- `SessionStore` —— append、load、list、delete、list_subkeys。
- `Hooks` —— `pre_tool_use`、`post_tool_use`、`session_start`、`session_end`。
- 一个 demo：主 agent 并行生成 3 个子代理（各自隔离），聚合结果，持久化会话。

运行：

```
python3 code/main.py
```

追踪输出会展示子代理的上下文隔离（编排者的上下文大小保持有界）、钩子的执行以及会话持久化。

> `code/main.py` implements the SDK shape in stdlib:
> - `Tool`, `ToolRegistry` with built-in `read_file`, `write_file`, `list_dir`.
> - `Subagent` — private context, isolated run, results returned.
> - `SessionStore` — append, load, list, delete, list_subkeys.
> - `Hooks` — `pre_tool_use`, `post_tool_use`, `session_start`, `session_end`.
> - A demo: main agent spawns 3 subagents in parallel (each isolated), aggregates results, persists session.
> The trace shows subagent context isolation (orchestrator context size stays bounded), hook execution, and session persistence.

## Use It · 实战用法

- **Claude Agent SDK** —— 想要 Claude Code harness 形态的 Claude 优先产品。
- **Claude Managed Agents** —— 托管的长时异步任务。
- **OpenAI Agents SDK**（第 16 课）—— OpenAI 侧的对应物。
- **LangGraph + 自定义工具** —— 如果你想要的是图形态的状态机。

> - **Claude Agent SDK** for Claude-first products that want the Claude Code harness shape.
> - **Claude Managed Agents** for hosted long-running async work.
> - **OpenAI Agents SDK** (Lesson 16) for OpenAI-first counterparts.
> - **LangGraph + custom tools** if you want the graph-shaped state machine instead.

## Ship It · 交付

`outputs/skill-claude-agent-scaffold.md` 为 Claude Agent SDK 应用生成脚手架，涵盖子代理、钩子、会话存储、MCP 服务器挂载和 W3C 追踪传播。

> `outputs/skill-claude-agent-scaffold.md` scaffolds a Claude Agent SDK app with subagents, hooks, session store, MCP server attachment, and W3C trace propagation.

## Exercises · 练习

1. 给子代理生成器加批处理：把 20 个任务分成每组 5 个并行子代理。对比「分组并行」与「一任务一代理」两种方式下编排者的上下文大小。
2. 实现一个 `PreToolUse` 钩子，对 `write_file` 调用限速（每会话每分钟 5 次）。追踪其行为。
3. 用 `list_subkeys` 渲染一棵子代理树。深层嵌套会是什么样子？
4. 把这个玩具实现移植到真正的 `claude-agent-sdk` Python 包。工具注册会有什么变化？
5. 阅读 Claude Managed Agents 文档。什么时候你会从自托管切换到托管？

## Key Terms · 术语表

| Term | What people say | What it actually means |
|------|----------------|------------------------|
| Agent SDK | 「把 Claude Code 做成库」 | Harness 形态：工具、MCP、钩子、子代理、会话存储 |
| Subagent | 「子代理」 | 独立上下文、独立预算；结果向上冒泡 |
| Session store | 「对话数据库」 | 持久化、加载、枚举、删除对话轮次，并级联处理子代理会话 |
| Hook | 「生命周期回调」 | 工具前后、会话、用户输入提交、压缩、停止 |
| W3C trace context | 「跨进程追踪」 | 父 span 传播进 CLI 子进程 |
| Managed Agents | 「托管的 harness」 | Anthropic 托管的长时异步任务 |
| `--session-mirror` | 「记录镜像」 | 会话轮次在流式传输的同时写入外部文件 |
| MCP server | 「工具面板」 | 挂载到 agent 上的外部工具/资源来源 |

## Further Reading · 延伸阅读

- [Claude Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview) —— Claude Code 的库形态
- [Anthropic, Building agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk) —— 生产级模式
- [Claude Managed Agents overview](https://platform.claude.com/docs/en/managed-agents/overview) —— 托管替代方案
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) —— OpenAI 侧的对应物
