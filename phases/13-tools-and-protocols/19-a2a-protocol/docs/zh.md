# A2A — Agent-to-Agent Protocol · A2A —— Agent 到 Agent 协议（A2A protocol）

> MCP 是 agent 对工具。A2A（Agent2Agent）是 agent 对 agent —— 一个开放协议，让构建在不同框架上、彼此不透明的 agent 能够协作。由 Google 于 2025 年 4 月发布，2025 年 6 月捐赠给 Linux Foundation，2026 年 4 月达到 v1.0，拥有包括 AWS、Cisco、Microsoft、Salesforce、SAP 和 ServiceNow 在内的 150 多个支持者。它吸收了 IBM 的 ACP，并加入了 AP2 支付扩展。本课讲解 Agent Card、Task 生命周期和三种协议绑定，使用 A2A 1.0.1 的线上名称（wire names）。
>
> MCP is agent-to-tool. A2A (Agent2Agent) is agent-to-agent — an open protocol for letting opaque agents built on different frameworks collaborate. Released by Google in April 2025, donated to the Linux Foundation in June 2025, reaching v1.0 in April 2026 with 150+ supporters including AWS, Cisco, Microsoft, Salesforce, SAP, and ServiceNow. It absorbed IBM's ACP and added the AP2 payments extension. This lesson walks the Agent Card, Task lifecycle, and the three protocol bindings, using the A2A 1.0.1 wire names.

**Type:** Build
**Languages:** Python (stdlib, Agent Card + Task harness)
**Prerequisites:** Phase 13 · 06 (MCP fundamentals), Phase 13 · 08 (MCP client)
**Time:** ~75 minutes

## Learning Objectives · 学习目标

- 区分 agent 对工具（MCP）与 agent 对 agent（A2A）这两类用例
- 在 `/.well-known/agent-card.json` 发布一个带技能（skills）与 `supportedInterfaces` 元数据的 Agent Card
- 走完 Task 生命周期：`TASK_STATE_SUBMITTED`、`TASK_STATE_WORKING`、`TASK_STATE_INPUT_REQUIRED`，以及终态 `TASK_STATE_COMPLETED`、`TASK_STATE_FAILED`、`TASK_STATE_CANCELED`、`TASK_STATE_REJECTED`
- 使用 Parts 各自持有 `text`、`raw`、`url` 或 `data` 之一的 Messages，并用 Artifacts 作为输出

> Distinguish agent-to-tool (MCP) from agent-to-agent (A2A) use cases.
> Publish an Agent Card at `/.well-known/agent-card.json` with skills and `supportedInterfaces` metadata.
> Walk the Task lifecycle: `TASK_STATE_SUBMITTED`, `TASK_STATE_WORKING`, `TASK_STATE_INPUT_REQUIRED`, and the terminal states `TASK_STATE_COMPLETED`, `TASK_STATE_FAILED`, `TASK_STATE_CANCELED`, `TASK_STATE_REJECTED`.
> Use Messages whose Parts each hold one of `text`, `raw`, `url`, or `data`, and Artifacts as outputs.

## The Problem · 问题在哪

一个客服 agent 需要把写报告委托给一个专门的写作 agent。A2A 出现之前的选项：

- 自定义 REST API。能用，但每一对组合都是一次性的。
- 共享代码库。要求两个 agent 运行在同一个框架上。
- MCP。不合适：MCP 是用来调用工具的，不是让两个 agent 在各自保持不透明内部推理的前提下协作的。

A2A 填补了这个空白。它把这次交互建模为一个 agent 向另一个 agent 发送一个 Task，附带生命周期、消息（message）和产物（artifact）。被调用 agent 的内部状态保持不透明——调用方只看到任务状态迁移和最终输出。

A2A 是「让跨框架的 agent 互相对话」的协议。它不取代 MCP；两者互补。

> A2A fills the gap. It models the interaction as one agent sending a Task to another, with a lifecycle, messages, and artifacts. The called agent's internal state stays opaque — the caller sees only task state transitions and eventual outputs.
> A2A is the "let agents across frameworks talk to each other" protocol. It does not replace MCP; the two are complementary.

## The Concept · 概念

### Agent Card · Agent Card（代理卡）

每个符合 A2A 的 agent 都在 `/.well-known/agent-card.json` 发布一张卡：

```json
{
  "name": "research-agent",
  "description": "Summarizes academic papers and drafts citations.",
  "version": "1.2.0",
  "supportedInterfaces": [
    {
      "url": "https://research.example.com/a2a",
      "protocolBinding": "JSONRPC",
      "protocolVersion": "1.0"
    }
  ],
  "capabilities": {"streaming": true, "pushNotifications": true},
  "securitySchemes": {
    "bearer": {"httpAuthSecurityScheme": {"scheme": "Bearer"}}
  },
  "securityRequirements": [{"schemes": {"bearer": {"list": []}}}],
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/markdown"],
  "skills": [
    {
      "id": "summarize_paper",
      "name": "Summarize a paper",
      "description": "Read a paper PDF and produce a 3-paragraph summary.",
      "tags": ["research", "summarization"],
      "inputModes": ["text/plain", "application/pdf"],
      "outputModes": ["text/markdown"]
    }
  ]
}
```

发现是基于 URL 的：抓取卡片，挑出第一个你的客户端说得通的 `protocolBinding` 对应的 `supportedInterfaces` 条目，然后枚举技能。输入与输出模式是媒体类型（media type）。

> Discovery is URL-based: fetch the card, pick the first `supportedInterfaces` entry whose `protocolBinding` your client speaks, and enumerate skills. Input and output modes are media types.

### Signed Agent Cards · 签名的 Agent Card

卡片可以携带一个 `signatures` 数组。每个条目是一个 JWS（RFC 7515），计算对象是卡片的 RFC 8785 规范化 JSON（canonical JSON），并把 `signatures` 字段排除在外。消费方用同样的方式规范化卡片并验证。这能防止冒充。

> A card can carry a `signatures` array. Each entry is a JWS (RFC 7515) computed over the card's RFC 8785 canonical JSON, with the `signatures` field left out. Consumers canonicalize the card the same way and verify. Prevents impersonation.

### Task lifecycle · Task 生命周期

```text
TASK_STATE_SUBMITTED
  -> TASK_STATE_WORKING
  -> TASK_STATE_COMPLETED | TASK_STATE_FAILED | TASK_STATE_CANCELED | TASK_STATE_REJECTED

TASK_STATE_WORKING
  -> TASK_STATE_INPUT_REQUIRED
  -> TASK_STATE_WORKING (the client sends a message with the same taskId)
```

客户端用 `SendMessage` 发起，服务器创建 Task。被调用的 agent 在状态间迁移；客户端用 `GetTask` 轮询，或用 `SendStreamingMessage` 和 `SubscribeToTask` 通过 SSE 流式获取。一个流携带 `statusUpdate` 和 `artifactUpdate` 事件，并在任务到达终态时关闭。没有 `final` 标志。

> Clients initiate with `SendMessage`, and the server creates the Task. The called agent transitions through states; clients poll with `GetTask` or stream over SSE with `SendStreamingMessage` and `SubscribeToTask`. A stream carries `statusUpdate` and `artifactUpdate` events and closes when the task reaches a terminal state. There is no `final` flag.

### Messages and Parts · 消息与部件（Parts）

一条消息有 `messageId`、`role`（`ROLE_USER` 或 `ROLE_AGENT`）和一个或多个 Part。每个 Part 恰好持有一个内容字段，该字段名就是类型。没有 `kind` 字段。

- `text`：纯文本内容。
- `raw`：文件字节，JSON 里是 base64，通常带 `filename` 和 `mediaType`。
- `url`：指向文件内容的链接。
- `data`：结构化 JSON 载荷（给被调用 agent 的结构化输入）。

示例：

```json
{
  "messageId": "msg-001",
  "role": "ROLE_USER",
  "parts": [
    {"text": "Summarize this paper."},
    {"raw": "...", "filename": "paper.pdf", "mediaType": "application/pdf"},
    {"data": {"targetLength": "3 paragraphs"}, "mediaType": "application/json"}
  ]
}
```

> A message has a `messageId`, a `role` (`ROLE_USER` or `ROLE_AGENT`), and one or more Parts. Each Part holds exactly one content field, and that field name is the type. There is no `kind` field.

### Artifacts · 产物（Artifacts）

输出是 Artifact，不是原始字符串。Artifact 是一个命名的、有类型的输出：

```json
{
  "artifactId": "art-001",
  "name": "summary",
  "parts": [{"text": "...", "mediaType": "text/markdown"}]
}
```

Artifact 可以分块流式传输。每个 `artifactUpdate` 事件携带 artifact 外加 `append` 和 `lastChunk`。由调用方累积。

> Outputs are Artifacts, not raw strings. An Artifact is a named, typed output.
> Artifacts can be streamed as chunks. Each `artifactUpdate` event carries the artifact plus `append` and `lastChunk`. The caller accumulates.

### Three protocol bindings · 三种协议绑定

1. **JSON-RPC 2.0 over HTTP**（`JSONRPC`）。请求用 POST，流式用 SSE。方法是 PascalCase：`SendMessage`、`SendStreamingMessage`、`GetTask`、`ListTasks`、`CancelTask`、`SubscribeToTask`、`CreateTaskPushNotificationConfig`、`GetTaskPushNotificationConfig`、`ListTaskPushNotificationConfigs`、`DeleteTaskPushNotificationConfig` 和 `GetExtendedAgentCard`。
2. **gRPC**（`GRPC`）。面向 gRPC 原生的企业环境。方法名相同。
3. **HTTP+JSON/REST**（`HTTP+JSON`）。资源式 URL，例如 `POST /message:send` 和 `GET /tasks/{id}`。

三种绑定携带同一个数据模型。每个 `supportedInterfaces` 条目指名一种绑定及其 `protocolVersion`。客户端在每个请求上发送 `A2A-Version: 1.0` 头，因为服务器会把不带它的请求读作版本 0.3。

```http
POST /a2a HTTP/1.1
Host: research.example.com
Content-Type: application/json
A2A-Version: 1.0

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "SendMessage",
  "params": {
    "message": {
      "messageId": "msg-001",
      "role": "ROLE_USER",
      "parts": [{"text": "Summarize this paper."}]
    }
  }
}
```

> All three bindings carry the same data model. Each `supportedInterfaces` entry names one binding and its `protocolVersion`. Clients send the header `A2A-Version: 1.0` on every request, because a server reads a request without it as version 0.3.

### Opacity preservation · 不透明性的保持

一个关键设计原则：被调用 agent 的内部状态是不透明的。调用方看到任务状态和 artifact。被调用 agent 的思维链、它的工具调用、它的子 agent 委托——全都不可见。这与 MCP 不同，MCP 的工具调用是透明的。

理由：A2A 让竞争者在不暴露内部的前提下协作。A2A 可以做到「调用这个客服 agent」，而调用方无需了解该 agent 如何实现这个服务。

> A key design principle: the called agent's internal state is opaque. The caller sees task state and artifacts. The called agent's chain-of-thought, its tool calls, its sub-agent delegation — all invisible. This is different from MCP, where tool calls are transparent.
> Rationale: A2A enables competitors to collaborate without revealing internals. A2A can be "call this customer-service agent" without the caller learning how that agent implements the service.

### Timeline · 时间线

- **2025-04-09。** Google 宣布 A2A。
- **2025-06-23。** 捐赠给 Linux Foundation。
- **2025-08。** 吸收 IBM 的 ACP。
- **2025-09。** AP2 扩展（Agent Payments）发布。
- **2026-04。** v1.0 发布，150 多个支持组织。

> **2025-04-09.** Google announces A2A.
> **2025-06-23.** Donated to Linux Foundation.
> **2025-08.** Absorbs IBM's ACP.
> **2025-09.** AP2 extension (Agent Payments) ships.
> **2026-04.** v1.0 released with 150+ supporting organizations.

### Relationship to MCP · 与 MCP 的关系

| 维度 | MCP | A2A |
|-----------|-----|-----|
| 用例 | Agent 对工具 | Agent 对 agent |
| 不透明性 | 透明的工具调用 | 不透明的内部推理 |
| 典型调用方 | Agent 运行时 | 另一个 agent |
| 状态 | 工具调用结果 | 带生命周期的 Task |
| 授权 | OAuth 2.1（Phase 13 · 16） | Agent Card `securitySchemes` + `securityRequirements` |
| 传输 | Stdio / Streamable HTTP | JSON-RPC / gRPC / HTTP+JSON |

想调用一个具体的工具时，用 MCP。想把一整个任务委托给另一个 agent 时，用 A2A。很多生产系统两者都用：agent 用 MCP 作工具层，用 A2A 作协作层。

> Use MCP when you want to invoke a specific tool. Use A2A when you want to delegate a whole task to another agent. Many production systems use both: an agent uses MCP for its tool layer and A2A for its collaboration layer.

```figure
a2a-task-lifecycle
```

## Use It · 实战用法

`code/main.py` 实现了一个最小 A2A 演练台（harness）：写作 agent 发布自己的卡片，research agent 发送一个带 PDF 部件和文本指令的 `SendMessage` 请求，任务依次经过 `TASK_STATE_WORKING` → `TASK_STATE_INPUT_REQUIRED` → `TASK_STATE_WORKING` → `TASK_STATE_COMPLETED`，最后返回一个文本 artifact。全部标准库；使用内存传输以聚焦消息形状。

值得看的地方：

- Agent Card 的 JSON 形状。
- 服务器侧的任务 id 分配与状态迁移。
- 由「出现了哪个内容字段」决定类型的 Parts。
- 任务中段的 `TASK_STATE_INPUT_REQUIRED` 分支。
- 完成时返回的 Artifact。

> `code/main.py` implements a minimal A2A harness: the writer agent publishes its card, the research agent sends it a `SendMessage` request with a PDF part and a text instruction, and the task moves through `TASK_STATE_WORKING` → `TASK_STATE_INPUT_REQUIRED` → `TASK_STATE_WORKING` → `TASK_STATE_COMPLETED` before returning a text artifact. All stdlib; uses an in-memory transport to focus on message shapes.

## Ship It · 交付

本课产出 `outputs/skill-a2a-agent-spec.md`。给定一个希望被其他 agent 调用的新 agent，该技能产出 Agent Card JSON、技能模式（skills schema）和端点蓝图。

> This lesson produces `outputs/skill-a2a-agent-spec.md`. Given a new agent that should be callable by other agents, the skill produces the Agent Card JSON, skills schema, and endpoint blueprint.

## Exercises · 练习

1. 运行 `code/main.py`。追踪完整的 Task 生命周期，包括被调用 agent 请求澄清时的 `TASK_STATE_INPUT_REQUIRED` 暂停。
2. 添加一张签名的 Agent Card。在 `signatures` 里放一个 JWS 条目，`alg` 设为 `HS256`，对不含 `signatures` 字段的卡片规范化 JSON 签名。写一个验证器，并确认它在卡片被篡改时失败。
3. 用 `SendStreamingMessage` 实现任务流式传输：写作 agent 依次发出 `task`、三个 `artifactUpdate` 分块和一个带 `TASK_STATE_COMPLETED` 的 `statusUpdate`，然后关闭流。由调用方累积分块。
4. 设计一个包装 MCP 服务器的 A2A agent。把每个 MCP 工具映射成一个 A2A 技能。注意其中的取舍——丢失了哪些不透明性？
5. 阅读 A2A v1.0 发布公告，找出截至 2026 年 4 月还没有任何框架实现的那个特性。（提示：它与多跳任务委托有关。）

> 1. Run `code/main.py`. Trace the full Task lifecycle, including the `TASK_STATE_INPUT_REQUIRED` pause where the called agent asks for a clarification.
> 2. Add a signed Agent Card. Put one JWS entry in `signatures` with `alg` set to `HS256`, signing the card's canonical JSON without the `signatures` field. Write a verifier and confirm it fails on a mutated card.
> 3. Implement task streaming with `SendStreamingMessage`: the writer agent emits the `task`, three `artifactUpdate` chunks, and a `statusUpdate` with `TASK_STATE_COMPLETED`, then closes the stream. The caller accumulates the chunks.
> 4. Design an A2A agent that wraps an MCP server. Map each MCP tool to an A2A skill. Note the trade-offs — what opacity is lost?
> 5. Read the A2A v1.0 announcement and identify the one feature that is not yet implemented by any framework as of April 2026. (Hint: it relates to multi-hop task delegation.)

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| A2A | 「Agent 对 Agent 协议」 | 用于不透明 agent 协作的开放协议 |
| Agent Card | 「`/.well-known/agent-card.json`」 | 发布的元数据，描述一个 agent 的技能与 `supportedInterfaces` |
| Skill | 「一个可调用单元」 | agent 支持的一个命名操作（类比 MCP tool） |
| Task | 「委托单元」 | 带生命周期和最终 artifact 的工作项 |
| Message | 「任务输入」 | 携带 Parts（`text`、`raw`、`url`、`data`） |
| Part | 「有类型的分块」 | `text` / `raw` / `url` / `data` 之一，外加可选 `mediaType`；没有 `kind` 字段 |
| Artifact | 「任务输出」 | 完成时返回的、命名的、有类型的输出 |
| AP2 | 「Agent 支付协议」 | 建立在 A2A 之上的支付扩展；卡片签名是 A2A 核心（`signatures`） |
| Opacity | 「黑盒协作」 | 被调用 agent 的内部对调用方隐藏 |
| `TASK_STATE_INPUT_REQUIRED` | 「任务暂停」 | agent 需要更多信息时的中断状态 |

> | Term | What people say | What it actually means |
> | A2A | "Agent-to-Agent protocol" | Open protocol for opaque agent collaboration |
> | Agent Card | "`/.well-known/agent-card.json`" | Published metadata describing an agent's skills and `supportedInterfaces` |
> | Skill | "A callable unit" | A named operation the agent supports (analog to MCP tool) |
> | Task | "Unit of delegation" | A work item with a lifecycle and final artifact |
> | Message | "Task input" | Carries Parts (`text`, `raw`, `url`, `data`) |
> | Part | "Typed chunk" | Exactly one of `text` / `raw` / `url` / `data`, plus optional `mediaType`; no `kind` field |
> | Artifact | "Task output" | Named, typed output returned on completion |
> | AP2 | "Agent Payments Protocol" | Payments extension built on A2A; card signing is core A2A (`signatures`) |
> | Opacity | "Black-box collaboration" | Called agent's internals are hidden from caller |
> | `TASK_STATE_INPUT_REQUIRED` | "Task pause" | Interrupted state when the agent needs more info |

## Further Reading · 延伸阅读

- [a2a-protocol.org](https://a2a-protocol.org/latest/) —— A2A 规范的权威来源
- [a2aproject/A2A — GitHub](https://github.com/a2aproject/A2A) —— 参考实现与 SDK
- [A2A v1.0.1 release](https://github.com/a2aproject/A2A/tree/v1.0.1)：本课遵循的带标签的 `docs/specification.md` 与规范性的 `specification/a2a.proto`
- [Linux Foundation — A2A launch press release](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents) —— 2025 年 6 月的治理移交
- [Google Cloud — A2A protocol upgrade](https://cloud.google.com/blog/products/ai-machine-learning/agent2agent-protocol-is-getting-an-upgrade) —— 路线图与合作伙伴势头
- [Google Dev — A2A 1.0 milestone](https://discuss.google.dev/t/the-a2a-1-0-milestone-ensuring-and-testing-backward-compatibility/352258) —— v1.0 发布说明与向后兼容指引
