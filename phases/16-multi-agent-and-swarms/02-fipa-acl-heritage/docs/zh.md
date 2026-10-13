# Heritage of FIPA-ACL and Speech Acts · FIPA-ACL 与言语行为的遗产

> Before MCP, before A2A, there was FIPA-ACL. In 2000 the IEEE Foundation for Intelligent Physical Agents ratified an agent communication language with twenty performatives, two content languages, and a set of interaction protocols — contract net, subscribe/notify, request-when. It faded from industry because the ontology overhead was too heavy for the web, but the LLM revival of multi-agent systems is quietly reimplementing the same ideas without the formal semantics: JSON contracts stand in for performatives, natural language stands in for ontologies. This lesson reads FIPA-ACL seriously so you can see which 2026 protocol decisions are reinvention, which are novelty, and where the current wave is going to rediscover problems the 2000s already solved.

**Type:** Learn
**Languages:** Python (stdlib)
**Prerequisites:** Phase 16 · 01 (Why Multi-Agent)
**Time:** ~60 minutes

## Problem · 问题

2026 年的智能体协议圈非常热闹：MCP 管工具，A2A 管智能体，ACP 管企业审计，ANP 管去中心化信任，NLIP 管自然语言内容，再加上 CA-MCP 和二十多个研究提案。每一份规范都宣称自己是奠基性的。

诚实的读法是：它们中的大多数正在重新发现一棵非常具体的、二十年前的决策树。Austin（1962）和 Searle（1969）的言语行为理论（speech-act theory）告诉我们「话语即行动」。KQML（1993）把它变成了线上协议（wire protocol）。FIPA-ACL（2000 年批准）给出了参照级的标准化：二十个言语行为原语（performative）、内容语言 SL0/SL1、合同网（contract-net）与订阅-通知（subscribe-notify）交互协议。JADE 和 JACK 是 Java 参考平台。这股努力在 2010 年前后淡出，因为本体（ontology）开销太重，而 Web 正在赢。

当你看着 MCP 的 `tools/call`、A2A 的任务生命周期或 CA-MCP 的共享上下文存储时，你看到的是 FIPA 决策的更柔软、JSON 原生的翻版。知道这段传承告诉你两件事：哪些新「创新」其实是重新发明，以及新规范会重新踩中哪些旧失败模式。

> The 2026 agent-protocol landscape is busy: MCP for tools, A2A for agents, ACP for enterprise audit, ANP for decentralized trust, NLIP for natural-language content, plus CA-MCP and two dozen research proposals. Each spec announces itself as foundational.
> The honest read is that most of them are rediscovering a very specific twenty-year-old decision tree. Speech-act theory from Austin (1962) and Searle (1969) gave us "utterances are actions." KQML (1993) turned that into a wire protocol. FIPA-ACL (ratified 2000) produced the reference standardization: twenty performatives, content languages SL0/SL1, interaction protocols for contract-net and subscribe-notify. JADE and JACK were the Java reference platforms. The effort faded around 2010 because the ontology overhead was too heavy and the web was winning.
> When you look at MCP's `tools/call`, A2A's task lifecycle, or CA-MCP's shared context store, you are looking at a softer, JSON-native rehash of FIPA decisions. Knowing the heritage tells you two things: which new "innovations" are actually reinventions, and which old failure modes the new specs will rediscover.

## Concept · 概念

### Speech acts, in one paragraph · 言语行为，一段话讲完

Austin 注意到有些句子并不描述世界——它们改变世界。「我承诺。」「我请求。」「我宣布。」他把这些叫做施为话语（performative utterances）。Searle 把它们形式化为五个范畴：断言（assertive）、指令（directive）、承诺（commissive）、表达（expressive）、宣告（declarative）。KQML（Finin et al., 1993）让这对软件智能体变得可操作：一条消息 = 一个 performative（动作）+ content（动作所针对的内容）。FIPA-ACL 修补了 KQML 的漏洞，围绕二十个 performative 完成了标准化。

> Austin noticed that some sentences do not describe the world — they change it. "I promise." "I request." "I declare." He called these performative utterances. Searle formalized five categories: assertive, directive, commissive, expressive, declarative. KQML (Finin et al., 1993) made this operational for software agents: a message is a performative (the action) plus content (what the action is about). FIPA-ACL cleaned up KQML's gaps and standardized around twenty performatives.

### The twenty FIPA performatives (partial list) · 二十个 FIPA performative（节选）

| Performative | 意图 |
|---|---|
| `inform` | 「我告诉你 P 为真」 |
| `request` | 「我请你做 X」 |
| `query-if` | 「P 为真吗？」 |
| `query-ref` | 「X 的值是什么？」 |
| `propose` | 「我提议我们做 X」 |
| `accept-proposal` | 「我接受这个提案」 |
| `reject-proposal` | 「我拒绝这个提案」 |
| `agree` | 「我同意做 X」 |
| `refuse` | 「我不肯做 X」 |
| `confirm` | 「我确认 P 为真」 |
| `disconfirm` | 「我否认 P」 |
| `not-understood` | 「你的消息没解析明白」 |
| `cfp` | 「征求关于 X 的提案」 |
| `subscribe` | 「X 变化时通知我」 |
| `cancel` | 「取消进行中的 X」 |
| `failure` | 「我试了 X，失败了」 |

完整清单见 `fipa00037.pdf`（FIPA ACL Message Structure）。重点不是背下来——重点是：这里面每一条，都对应一个 LLM 协议迟早会重新加回来的原语。

> The full list is in `fipa00037.pdf` (FIPA ACL Message Structure). The point is not to memorize it — the point is that every one of these corresponds to a primitive an LLM protocol eventually re-adds.

### Canonical FIPA-ACL message · 规范形态的 FIPA-ACL 消息

```
(inform
  :sender       agent1@platform
  :receiver     agent2@platform
  :content      "((price IBM 83))"
  :language     SL0
  :ontology     finance
  :protocol     fipa-request
  :conversation-id   conv-42
  :reply-with   msg-17
)
```

七个字段承载协议信封；一个字段（`content`）承载载荷。其余字段，恰恰是你每次给 JSON 协议 bolt 上重试、线程和本体时重新发明出来的东西。

> Seven fields carry the protocol envelope; one field (`content`) carries the payload. The rest of the fields are exactly what you reinvent every time you bolt retries, threading, and ontology onto a JSON protocol.

### The two legacy platforms · 两个老牌平台

**JADE**（Java Agent DEvelopment framework，1999–2020 年代）是使用最广的 FIPA 兼容运行时。智能体继承一个基类、交换 ACL 消息、跑在容器（container）里，用「行为（behavior）」协调。它自带的交互协议库包含 contract-net、subscribe-notify、request-when 和 propose-accept。

**JACK**（Agent Oriented Software，商业产品）强调在 FIPA 消息之上做 BDI（Belief-Desire-Intention，信念-愿望-意图）推理。更形式化，采用率更低。

两者都在 Web 技术栈吃掉多智能体用例之后走向衰落。MCP 和 A2A 就是 2026 年的运行时「容器」。

> **JADE** (Java Agent DEvelopment framework, 1999–2020s) was the most-used FIPA-compliant runtime. Agents extended a base class, exchanged ACL messages, ran inside containers, and coordinated using "behaviors." The interaction-protocol library shipped with contract-net, subscribe-notify, request-when, and propose-accept.
> **JACK** (Agent Oriented Software, commercial) emphasized BDI (Belief-Desire-Intention) reasoning on top of FIPA messages. More formal, less adopted.
> Both declined once the web stack ate multi-agent use cases. MCP and A2A are the runtime "containers" of 2026.

### Why FIPA faded · FIPA 为什么淡出

- **本体开销。** FIPA 要求有共享本体才能解析 `content`。就本体达成一致是以年为单位的标准化过程。Web 直接用了 HTTP + JSON。
- **没人用的形式语义。** SL（Semantic Language）给出了严格的真值条件，但多数生产系统用自由格式内容，无视这套形式化。
- **工具链锁定。** JADE 只支持 Java；JACK 是商业产品。多语言团队绕开了两者。
- **互联网赢了技术栈。** REST、然后 JSON-RPC、然后 gRPC 取代了 ACL 的传输层。

> - **Ontology overhead.** FIPA required a shared ontology to parse `content`. Agreeing on ontologies is a years-long standards process. The web just used HTTP + JSON.
> - **Formal semantics nobody used.** SL (Semantic Language) gave rigorous truth conditions, but most production systems used free-form content and ignored the formalism.
> - **Tooling lock-in.** JADE was Java-only; JACK was commercial. Polyglot teams routed around both.
> - **The internet won the stack.** REST, then JSON-RPC, then gRPC replaced ACL's transport.

### The LLM revival is FIPA-lite · LLM 复兴是 FIPA 精简版

把 FIPA 的 `request` 和 MCP 的 `tools/call` 摆在一起对比：

```
(request                                {
  :sender  agent1                         "jsonrpc": "2.0",
  :receiver tool-server                   "method":  "tools/call",
  :content "(lookup stock IBM)"           "params":  {"name":"lookup_stock",
  :ontology finance                                   "arguments":{"symbol":"IBM"}},
  :conversation-id c42                    "id": 42
)                                        }
```

同样的信封，不同的语法。两者都携带：谁、发给谁、意图、载荷、关联 id。谁也不是对另一方的革命——它们是同一个设计上的不同取舍。

> Compare a FIPA `request` to an MCP `tools/call`:
> Same envelope, different syntax. Both carry: who, whom, intent, payload, correlation id. Neither is a revolution over the other — they are different trade-offs on the same design.

Liu 等人 2025 年的综述（"A Survey of Agent Interoperability Protocols: MCP, ACP, A2A, ANP"，arXiv:2505.02279）把这条传承讲得非常明白：MCP 对应工具使用的言语行为，A2A 对应智能体对等的言语行为，ACP 对应审计留痕的言语行为，ANP 对应去中心化身份扩展。新规范就是 JSON 语法、语义更松的 ACL 后裔。

> The 2025 survey by Liu et al. ("A Survey of Agent Interoperability Protocols: MCP, ACP, A2A, ANP", arXiv:2505.02279) makes this lineage explicit: MCP corresponds to tool-use speech acts, A2A to agent-peer speech acts, ACP to audit-trail speech acts, ANP to decentralized-identity extensions. The new specs are ACL descendants with JSON syntax and looser semantics.

### The trade-off, stated plainly · 把取舍说透

**FIPA 给了你、而现代规范丢掉的：**

- 形式语义——你可以证明 `inform` 蕴含「发送者相信其内容」。
- 一份规范的 performative 目录——你不必重新争论「我们要不要一个 `cancel`？」。
- 几十年积累的交互协议模式——contract-net、subscribe-notify、propose-accept——附带已知正确性性质。

**现代规范给了你、而 FIPA 没有的：**

- 与所有现代工具兼容的 JSON 原生载荷。
- LLM 无需手工本体就能理解的自然语言内容。
- Web 技术栈的传输（HTTP、SSE、WebSocket）。
- 通过在线的 MCP `server/discover` 和 A2A Agent Card 做能力发现。

意图语义更松，换来实现更容易。这就是这笔交易的全部。

> **What FIPA gave you and modern specs drop:**
> - Formal semantics — you can prove `inform` implies the sender believes the content.
> - A canonical catalog of performatives — you do not have to re-argue "should we have a `cancel`?".
> - Decades of interaction-protocol patterns — contract-net, subscribe-notify, propose-accept — with known correctness properties.
> **What modern specs give you and FIPA did not:**
> - JSON-native payloads compatible with every modern tool.
> - Natural-language content that LLMs can interpret without a hand-coded ontology.
> - Web-stack transport (HTTP, SSE, WebSocket).
> - Capability discovery via live MCP `server/discover` and A2A Agent Cards.
> Looser intent semantics for easier implementation. That is the exact trade.

### Interaction protocols worth porting · 值得移植的交互协议

FIPA 交付了约 15 个交互协议。其中三个值得带进 LLM 多智能体系统：

1. **合同网协议（Contract Net Protocol, CNP）。** 管理者发出 `cfp`（call for proposals，征求提案）；投标者用 `propose` 响应；管理者接受／拒绝。这就是经典的任务市场模式（Phase 16 · 16 Negotiation）。
2. **订阅／通知（Subscribe/Notify）。** 订阅者发 `subscribe`；每当主题变化，发布者发 `inform`。这就是 2026 年的每一个事件总线（event-bus）。
3. **Request-When。** 「当条件 Y 成立时做 X。」带前置条件的延迟动作。它 2026 年的对应物是持久化工作流引擎里的延迟任务（Phase 16 · 22 Production Scaling）。

每一个都能干净地映射到现代消息队列、HTTP + 轮询或 SSE 流。

> FIPA shipped ~15 interaction protocols. Three are worth carrying forward into LLM multi-agent systems:
> 1. **Contract Net Protocol (CNP).** Manager issues `cfp` (call for proposals); bidders respond with `propose`; manager accepts/rejects. This is the canonical task-market pattern (Phase 16 · 16 Negotiation).
> 2. **Subscribe/Notify.** Subscriber sends `subscribe`; publisher sends `inform` whenever the topic changes. This is every event-bus in 2026.
> 3. **Request-When.** "Do X when condition Y holds." Delayed-action with pre-conditions. The 2026 analog is deferred tasks in durable workflow engines (Phase 16 · 22 Production Scaling).
> Each maps cleanly onto modern message queues, HTTP + polling, or SSE streaming.

### What breaks when you drop the ontology · 丢掉本体之后会坏什么

没有共享本体，智能体要从自然语言内容里猜意思。有据可查的 2026 年失败模式是**语义漂移（semantic drift）**：两个智能体用同一个词（`"customer"`）指代微妙不同的概念，接收方的智能体按错误的理解行动，没有任何 schema 校验器能抓住它。FIPA 的本体要求本可以在解析时就拒收这条消息。

不上全套本体的缓解手段：

- 在 `content` 上加 JSON Schema——在传输层就拒绝结构性错误。
- 类型化工件（A2A）——拒绝错误的模态。
- 信封里带显式 performative——即使内容是自然语言，意图也无歧义。

> Without a shared ontology, agents infer meaning from natural-language content. The documented 2026 failure mode is **semantic drift**: two agents use the same word (`"customer"`) for subtly different concepts, the receiver's agent acts on the wrong interpretation, no schema validator catches it. FIPA's ontology requirement would have rejected the message at parse time.
> Mitigations without going full ontology:
> - JSON Schema on `content` — rejects structural errors at the wire.
> - Typed artifacts (A2A) — rejects wrong modality.
> - Explicit performative in the envelope — makes intent unambiguous even when content is natural language.

### The 2026 specs, mapped to speech-act heritage · 2026 年规范与言语行为传承的对照

| 现代规范 | FIPA 对应物 | 保留了什么 | 丢掉了什么 |
|---|---|---|---|
| MCP `tools/call` | `request` | 显式意图、关联 id | 形式语义、本体 |
| MCP `resources/read` | `query-ref` | 显式意图、关联 id | 形式语义 |
| A2A Task 生命周期 | contract-net + request-when | 异步生命周期、状态迁移 | 形式完备性保证 |
| A2A 流式事件 | subscribe/notify | 异步推送 | 类型化谓词订阅 |
| CA-MCP 共享上下文 | blackboard（Hayes-Roth 1985） | 多写者共享内存 | 逻辑一致性模型 |
| NLIP | 自然语言内容 | LLM 原生 | schema |

从上往下读这张表，模式是：保留结构性原语，丢掉形式化，让 LLM 把歧义糊过去。

```figure
sw-contract-net
```

> Reading the table top to bottom, the pattern is: keep the structural primitive, drop the formalism, let LLMs paper over the ambiguity.

## Build It · 动手造

`code/main.py` 实现了一个纯 stdlib 的 FIPA-ACL 转译器。它对规范的 ACL 信封做编码和解码，并展示每一条 MCP / A2A 消息形态如何归约为同样的七个字段。演示内容：

- 把五条 MCP 风格与 A2A 风格的消息编码成 FIPA-ACL。
- 把 FIPA-ACL 解码回现代等价物。
- 在一个管理者和三个投标者之间跑一场玩具合同网（Contract Net）谈判，使用 `cfp`、`propose`、`accept-proposal`、`reject-proposal`。

运行：

```
python3 code/main.py
```

输出是一份并排轨迹：每条现代消息同时以 2026 年的 JSON 形态和 FIPA-ACL 形态出现，然后是一轮合同网投标的往返（round-trip）。同一批协议原语在往返中幸存；不同的只是语法。

> `code/main.py` implements a pure-stdlib FIPA-ACL translator. It encodes and decodes the canonical ACL envelope and shows how every MCP / A2A message shape reduces to the same seven fields. The demo:
> - Encodes five MCP-style and A2A-style messages as FIPA-ACL.
> - Decodes FIPA-ACL back to the modern equivalent.
> - Runs a toy Contract Net negotiation between one manager and three bidders using `cfp`, `propose`, `accept-proposal`, `reject-proposal`.
> The output is a side-by-side trace showing each modern message in both its 2026 JSON form and its FIPA-ACL form, then a round-trip of a contract-net bid. The same protocol primitives survive the round-trip; only the syntax differs.

## Use It · 实战用法

`outputs/skill-fipa-mapper.md` 是一个技能（skill）：读任意智能体协议规范，产出 FIPA-ACL 映射。在采用新协议之前先用它回答一个问题：「这是真正的新东西，还是披着 JSON 语法的 `inform`？」

> `outputs/skill-fipa-mapper.md` is a skill that reads any agent-protocol spec and produces the FIPA-ACL mapping. Use it before adopting a new protocol to answer: "Is this genuinely new, or is it `inform` with JSON syntax?"

## Ship It · 交付

不要把 FIPA-ACL 搬回来。把它的检查清单带回来：

- 每条消息的意图原语（performative）是什么？
- 请求-响应和取消有没有关联 id？
- 有没有显式的内容语言（JSON-RPC、纯文本、结构化类型化工件）？
- 交互协议是不是一等公民，还是你在从零重新实现 contract-net？
- 两个智能体对内容含义有分歧时（语义漂移）会发生什么？

任何新协议在上生产之前，先把这五个问题写成文档。

> Do not bring FIPA-ACL back. Bring back its checklist:
> - What is the intent primitive (performative) of each message?
> - Is there a correlation id for request-response and cancellation?
> - Is there an explicit content language (JSON-RPC, plain text, structured typed artifact)?
> - Are interaction protocols first-class, or are you re-implementing contract-net from scratch?
> - What happens when two agents disagree about content meaning (semantic drift)?
> Document these five questions for any new protocol before you ship it into production.

## Exercises · 练习

1. 运行 `code/main.py`。观察往返编码。找出与 `tools/call`、`resources/read` 和 A2A 任务创建分别对应的 FIPA performative。
2. 给合同网演示扩展一个 `cancel` performative，让管理者能在投标中途撤回任务。`cancel` 解决了哪个单靠重试解决不了的失败场景？
3. 读 FIPA ACL Message Structure（http://www.fipa.org/specs/fipa00037/）的 4.1–4.3 节。挑一个本课没讲到的 performative，描述它的现代 JSON-RPC 对应物。
4. 读 Liu 等人，arXiv:2505.02279。对 MCP、A2A、ACP、ANP 各自列出它们保留和丢掉的 FIPA performative 家族。
5. 为你自己系统里 `request` performative 的 `content` 字段设计一个最小 JSON-Schema。这个 schema 给了你哪些纯自然语言给不了的东西？代价是什么？

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|------------------------|
| Speech act | 「一句话本身就是一个动作」 | Austin/Searle：话语即行动。ACL 的理论前身。 |
| FIPA | 「那个老的 XML 玩意」 | IEEE Foundation for Intelligent Physical Agents。2000 年标准化了 ACL。 |
| ACL | 「Agent Communication Language」 | FIPA 的信封格式：performative + content + 元数据。 |
| Performative | 「那个动词」 | 一条消息的意图类别：`inform`、`request`、`propose`、`cfp` 等。 |
| KQML | 「FIPA 的前身」 | Knowledge Query and Manipulation Language（1993）。更简单、更窄。 |
| Ontology | 「共享词表」 | 对内容语言所谈论概念的正式定义。 |
| SL0 / SL1 | 「FIPA 内容语言」 | Semantic Language 的 0 级和 1 级——形式化内容语言家族。 |
| Contract Net | 「任务市场」 | 管理者发 cfp；投标者提议；管理者接受。最经典的交互协议。 |
| Interaction protocol | 「消息的模式」 | 一串带已知正确性的 performative 序列：request-when、subscribe-notify 等。 |

## Further Reading · 延伸阅读

- [Liu et al. — A Survey of Agent Interoperability Protocols: MCP, ACP, A2A, ANP](https://arxiv.org/html/2505.02279v1) —— 把现代规范接到 FIPA 传承之上的 2025 年权威综述
- [FIPA ACL Message Structure Specification (fipa00037)](http://www.fipa.org/specs/fipa00037/) —— 2000 年批准的信封格式
- [FIPA Communicative Act Library Specification (fipa00037)](http://www.fipa.org/specs/fipa00037/) —— 完整的 performative 目录
- [MCP specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28) —— `request`／`query-ref` 的当今无状态工具使用等价物
- [A2A specification](https://a2a-protocol.org/latest/specification/) —— contract-net 与 subscribe-notify 的现代智能体对等等价物
