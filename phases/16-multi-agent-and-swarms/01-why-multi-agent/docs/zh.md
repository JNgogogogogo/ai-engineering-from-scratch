# Why Multi-Agent? · 为什么要多智能体

> One agent hits a wall. The smart move is not a bigger agent - it is more agents.

**Type:** Learn
**Languages:** TypeScript
**Prerequisites:** Phase 14 (Agent Engineering)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 识别单智能体的天花板（上下文溢出、专长混杂、串行瓶颈），并解释什么时候拆分成多个智能体才是正确选择
- 比较各编排模式（流水线、并行扇出、supervisor、层级式），并针对给定的任务结构选对模式
- 设计一个角色边界清晰、共享状态明确、通信契约完备的多智能体系统
- 分析多智能体的复杂度（延迟、成本、调试难度）与单智能体简单性之间的权衡

> Identify the single-agent ceiling (context overflow, mixed expertise, sequential bottleneck) and explain when splitting into multiple agents is the right move
> Compare orchestration patterns (pipeline, parallel fan-out, supervisor, hierarchical) and select the right one for a given task structure
> Design a multi-agent system with clear role boundaries, shared state, and a communication contract
> Analyze the tradeoffs of multi-agent complexity (latency, cost, debugging difficulty) versus single-agent simplicity

## The Problem · 问题在哪

你在 Phase 14 造过一个单智能体，它能用：可以读文件、跑命令、调 API、对结果做推理。然后你把它指向一个真实的代码库：200 个文件、三种语言、依赖基础设施才能跑的测试，外加一条要求——写代码之前先调研外部 API。

这个智能体噎住了。不是 LLM 笨，而是任务超出了单个智能体循环能承受的范围。上下文窗口被文件内容塞满。它忘了 40 次工具调用之前读过什么。它想同时当好调研员、程序员和评审员，结果三样都做得很平庸。

这就是单智能体天花板（single-agent ceiling）。每当任务出现下面这些需求，你就会撞上它：

- **上下文多到一个窗口装不下** —— 读 50 个文件就会突破 200k token
- **不同阶段需要不同的专长** —— 调研需要的提示词与代码生成完全不同
- **工作可以并行** —— 能同时读三个文件，为什么要串着读？

> You built a single agent in Phase 14. It works. It can read files, run commands, call APIs, and reason about results. Then you point it at a real codebase: 200 files, three languages, tests that depend on infrastructure, and a requirement to research external APIs before writing code.
> The agent chokes. Not because the LLM is dumb, but because the task exceeds what one agent loop can handle. The context window fills up with file contents. The agent forgets what it read 40 tool calls ago. It tries to be a researcher, a coder, and a reviewer all at once, and does all three poorly.
> This is the single-agent ceiling. You hit it every time a task requires:
> - **More context than fits in one window** - reading 50 files blows past 200k tokens
> - **Different expertise at different stages** - research requires different prompting than code generation
> - **Work that can happen in parallel** - why read three files sequentially when you can read them simultaneously?

## The Concept · 概念

### The Single-Agent Ceiling · 单智能体天花板

单智能体就是一个循环、一个上下文窗口、一份系统提示词。想象一下：

```
┌─────────────────────────────────────────┐
│            SINGLE AGENT                 │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │         Context Window            │  │
│  │                                   │  │
│  │  research notes                   │  │
│  │  + code files                     │  │
│  │  + test output                    │  │
│  │  + review feedback                │  │
│  │  + API docs                       │  │
│  │  + ...                            │  │
│  │                                   │  │
│  │  ██████████████████████ FULL ███  │  │
│  └───────────────────────────────────┘  │
│                                         │
│  One system prompt tries to cover       │
│  research + coding + review + testing   │
│                                         │
│  Result: mediocre at everything         │
└─────────────────────────────────────────┘
```

会坏掉三件事：

1. **上下文饱和（context saturation）** —— 工具结果不断堆积。到第 30 轮，智能体已经吃掉 150k token 的文件内容、命令输出和此前的推理，第 5 轮的关键细节早就丢了。

2. **角色混乱（role confusion）** —— 一份写着「你是调研员、程序员、评审员兼测试员」的系统提示词，只会造出一个调研做一半、代码写一半、评审永远做不完的智能体。

3. **串行瓶颈（sequential bottleneck）** —— 智能体先读文件 A，再读 B，再读 C。三次串行 LLM 调用、三次串行工具执行，毫无并行。

> A single agent is one loop, one context window, one system prompt. Picture it:
> Three things break:
> 1. **Context saturation** - tool results pile up. By turn 30, the agent has consumed 150k tokens of file contents, command outputs, and prior reasoning. Critical details from turn 5 get lost.
> 2. **Role confusion** - a system prompt that says "you are a researcher, coder, reviewer, and tester" produces an agent that half-researches, half-codes, and never finishes reviewing.
> 3. **Sequential bottleneck** - the agent reads file A, then file B, then file C. Three serial LLM calls. Three serial tool executions. No parallelism.

### The Multi-Agent Solution · 多智能体解法

把工作拆开。给每个智能体一份工作、一个上下文窗口、一份为这份工作量身调校的系统提示词：

```
┌──────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                          │
│                                                          │
│  "Build a REST API for user management"                  │
│                                                          │
│         ┌──────────┬──────────┬──────────┐               │
│         │          │          │          │               │
│         ▼          ▼          ▼          ▼               │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│   │RESEARCHER│ │  CODER   │ │ REVIEWER │ │  TESTER  │  │
│   │          │ │          │ │          │ │          │  │
│   │ Reads    │ │ Writes   │ │ Checks   │ │ Runs     │  │
│   │ docs,    │ │ code     │ │ code     │ │ tests,   │  │
│   │ finds    │ │ based on │ │ quality, │ │ reports  │  │
│   │ patterns │ │ research │ │ finds    │ │ results  │  │
│   │          │ │ + spec   │ │ bugs     │ │          │  │
│   └─────┬────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
│         │           │            │             │         │
│         └───────────┴────────────┴─────────────┘         │
│                          │                               │
│                     Merge results                        │
└──────────────────────────────────────────────────────────┘
```

每个智能体拥有：

- 一份聚焦的系统提示词（「你是一名代码评审员，你唯一的职责就是找 bug。」）
- 自己的上下文窗口（不被其他智能体的工作污染）
- 一份清晰的输入/输出契约（接收调研笔记，产出代码）

> Split the work. Give each agent one job, one context window, and one system prompt tuned for that job:
> Each agent has:
> - A focused system prompt ("You are a code reviewer. Your only job is finding bugs.")
> - Its own context window (not polluted by other agents' work)
> - A clear input/output contract (receives research notes, outputs code)

### Real Systems That Do This · 真实系统里的先例

**Claude Code 子智能体（subagents）** —— 当 Claude Code 用 `Task` 派生子智能体时，它会创建一个带着限定任务的子代理。父代理的上下文保持干净；子代理做聚焦的工作，然后返回一份摘要。

**Devin** —— 同时运行一个规划代理、一个编码代理和一个浏览器代理。规划者把工作拆成步骤，编码者写代码，浏览器调研文档。三者各自持有独立的上下文。

**多智能体编程团队（SWE-bench）** —— SWE-bench 上的顶尖系统都用一个调研员读代码库、一个规划者设计修复方案、一个编码者动手实现。单智能体系统得分更低。

**ChatGPT Deep Research** —— 并行派出多个搜索代理，各自探索不同的角度，然后综合结果。

> **Claude Code subagents** - when Claude Code spawns a subagent with `Task`, it creates a child agent with a scoped task. The parent keeps its context clean. The child does focused work and returns a summary.
> **Devin** - runs a planner agent, a coder agent, and a browser agent. The planner breaks work into steps. The coder writes code. The browser researches documentation. Each has separate context.
> **Multi-agent coding teams (SWE-bench)** - top-performing systems on SWE-bench use a researcher that reads the codebase, a planner that designs the fix, and a coder that implements it. Single-agent systems score lower.
> **ChatGPT Deep Research** - spawns multiple search agents in parallel, each exploring a different angle, then synthesizes results.

### The Spectrum · 光谱

多智能体不是非黑即白，它是一条光谱：

```
SIMPLE ──────────────────────────────────────────── COMPLEX

 Single        Sub-         Pipeline      Team         Swarm
 Agent         agents

 ┌───┐       ┌───┐        ┌───┐───┐    ┌───┐───┐    ┌─┐┌─┐┌─┐
 │ A │       │ A │        │ A │ B │    │ A │ B │    │ ││ ││ │
 └───┘       └─┬─┘        └───┘─┬─┘    └─┬─┘─┬─┘    └┬┘└┬┘└┬┘
               │                │        │   │       ┌┴──┴──┴┐
             ┌─┴─┐          ┌───┘───┐    │   │       │shared │
             │ a │          │ C │ D │  ┌─┴───┴─┐    │ state │
             └───┘          └───┘───┘  │  msg   │    └───────┘
                                       │  bus   │
 1 loop      Parent +      Stage by    │       │    N peers,
 1 context   child tasks   stage       └───────┘    emergent
                                       Explicit      behavior
                                       roles
```

**单智能体（Single agent）** —— 一个循环、一份提示词。适合简单任务。

**子智能体（Subagents）** —— 父代理为聚焦的子任务派生子代理。父代理维护计划，子代理汇报结果。Claude Code 就是这种。

**流水线（Pipeline）** —— 智能体按顺序执行，A 的输出就是 B 的输入。适合分阶段工作流：调研 -> 写码 -> 评审 -> 测试。

**团队（Team）** —— 智能体并行运行，共享一条消息总线，各有角色，由编排器（orchestrator）协调。适合需要多种技能同时出场的场合。

**蜂群（Swarm）** —— 大量相同或近似相同的智能体共享状态。没有固定编排器，智能体从队列里认领工作。适合高吞吐并行任务。

> **Single agent** - one loop, one prompt. Good for simple tasks.
> **Subagents** - a parent spawns children for focused subtasks. The parent maintains the plan. Children report back. This is what Claude Code does.
> **Pipeline** - agents run in sequence. Agent A's output becomes Agent B's input. Good for staged workflows: research -> code -> review -> test.
> **Team** - agents run in parallel with a shared message bus. Each has a role. An orchestrator coordinates. Good when different skills are needed simultaneously.
> **Swarm** - many identical or near-identical agents with shared state. No fixed orchestrator. Agents pick up work from a queue. Good for high-throughput parallel tasks.

### The Four Multi-Agent Patterns · 四种多智能体模式

#### Pattern 1: Pipeline · 模式一：流水线

```
Input ──▶ Agent A ──▶ Agent B ──▶ Agent C ──▶ Output
          (research)  (code)      (review)
```

每个智能体对数据做一次变换再向前传递。容易推理。任何一个阶段失败都会阻塞后续所有阶段。

> Each agent transforms the data and passes it forward. Simple to reason about. Failure in one stage blocks the rest.

#### Pattern 2: Fan-out / Fan-in · 模式二：扇出／扇入

```
                ┌──▶ Agent A ──┐
                │              │
Input ──▶ Split ├──▶ Agent B ──├──▶ Merge ──▶ Output
                │              │
                └──▶ Agent C ──┘
```

把工作拆给并行的智能体，再合并结果。适合能分解成相互独立子任务的工作。

> Split work across parallel agents, then merge results. Good for tasks that decompose into independent subtasks.

#### Pattern 3: Orchestrator-Worker · 模式三：编排器-工人

```
                    ┌──────────┐
                    │  Orch.   │
                    └──┬───┬───┘
                  task │   │ task
                 ┌─────┘   └─────┐
                 ▼               ▼
           ┌──────────┐   ┌──────────┐
           │ Worker A │   │ Worker B │
           └──────────┘   └──────────┘
```

一个聪明的编排器决定做什么，把任务委托给工人，再综合结果。编排器本身也是一个智能体，拥有派生工人用的工具。

> A smart orchestrator decides what to do, delegates to workers, and synthesizes results. The orchestrator is itself an agent with tools for spawning workers.

#### Pattern 4: Peer Swarm · 模式四：对等蜂群

```
         ┌───┐ ◄──── msg ────▶ ┌───┐
         │ A │                  │ B │
         └─┬─┘                  └─┬─┘
           │                      │
      msg  │    ┌───────────┐     │ msg
           └───▶│  Shared   │◄────┘
                │  State    │
           ┌───▶│  / Queue  │◄────┐
           │    └───────────┘     │
      msg  │                      │ msg
         ┌─┴─┐                  ┌─┴─┐
         │ C │ ◄──── msg ────▶ │ D │
         └───┘                  └───┘
```

没有中央编排器。智能体两两点对点通信，决策从交互中涌现。更难调试，但能扩展到大量智能体。

> No central orchestrator. Agents communicate peer-to-peer. Decisions emerge from interaction. Harder to debug, but scales to many agents.

### When NOT to Use Multi-Agent · 什么时候别用多智能体

多智能体引入复杂度。智能体之间的每一条消息都是潜在故障点。调试从「读一段对话」变成「跨五个代理追消息」。

**这些情况下保持单智能体：**

- 任务装得进一个上下文窗口（工作数据在 100k token 以内）
- 不同阶段不需要不同的系统提示词
- 串行执行已经够快
- 任务足够简单，拆分带来的开销超过收益

**复杂度的代价：**

- 每一个智能体边界都是一次有损压缩：A 的完整上下文要被摘要成发给 B 的一条消息
- 协调逻辑（谁、何时、按什么顺序做什么）本身就是 bug 来源
- 延迟上升：N 个智能体至少意味着 N 次串行 LLM 调用，需要来回沟通时还会更多
- 成本翻倍：每个智能体都在独立烧 token

经验法则：一个任务如果少于 20 次工具调用、装得进 100k token，就保持单智能体。

```figure
swarm-messages
```

> Multi-agent adds complexity. Every message between agents is a potential failure point. Debugging goes from "read one conversation" to "trace messages across five agents."
> **Stay single-agent when:**
> - The task fits in one context window (under ~100k tokens of working data)
> - You do not need different system prompts for different stages
> - Sequential execution is fast enough
> - The task is simple enough that splitting it adds more overhead than value
> **The complexity cost:**
> - Every agent boundary is a lossy compression step: agent A's full context gets summarized into a message for agent B
> - Coordination logic (who does what, when, in what order) is its own source of bugs
> - Latency increases: N agents means N serial LLM calls minimum, more if they need to talk back and forth
> - Cost multiplies: each agent burns tokens independently
> Rule of thumb: if a task takes fewer than 20 tool calls and fits in 100k tokens, keep it single-agent.

## Build It · 动手造

### Step 1: The Overloaded Single Agent · 第一步：不堪重负的单智能体

下面是一个试图包办一切的单智能体：一份巨大的系统提示词，一个同时装着调研、代码和评审的上下文窗口：

```typescript
type AgentResult = {
  content: string;
  tokensUsed: number;
  toolCalls: number;
};

async function singleAgentApproach(task: string): Promise<AgentResult> {
  const systemPrompt = `You are a full-stack developer. You must:
1. Research the requirements
2. Write the code
3. Review the code for bugs
4. Write tests
Do ALL of these in a single conversation.`;

  const contextWindow: string[] = [];
  let totalTokens = 0;
  let totalToolCalls = 0;

  const research = await fakeLLMCall(systemPrompt, `Research: ${task}`);
  contextWindow.push(research.output);
  totalTokens += research.tokens;
  totalToolCalls += research.calls;

  const code = await fakeLLMCall(
    systemPrompt,
    `Given this research:\n${contextWindow.join("\n")}\n\nNow write code for: ${task}`
  );
  contextWindow.push(code.output);
  totalTokens += code.tokens;
  totalToolCalls += code.calls;

  const review = await fakeLLMCall(
    systemPrompt,
    `Given all previous context:\n${contextWindow.join("\n")}\n\nReview the code.`
  );
  contextWindow.push(review.output);
  totalTokens += review.tokens;
  totalToolCalls += review.calls;

  return {
    content: contextWindow.join("\n---\n"),
    tokensUsed: totalTokens,
    toolCalls: totalToolCalls,
  };
}
```

这种做法的问题：

- 上下文窗口随每个阶段膨胀。到评审那一步，里面已经装着调研笔记、代码和此前的推理。
- 系统提示词是大锅饭，没法针对每个阶段单独调校。
- 没有任何东西是并行运行的。

> Here is a single agent trying to do everything. It has one massive system prompt and one context window holding research, code, and reviews:
> Problems with this approach:
> - The context window grows with every stage. By the review step, it contains research notes AND code AND prior reasoning.
> - The system prompt is generic. It cannot be tuned for each stage.
> - Nothing runs in parallel.

### Step 2: Specialist Agents · 第二步：专家智能体

现在把它拆开，每个智能体只干一件事：

```typescript
type SpecialistAgent = {
  name: string;
  systemPrompt: string;
  run: (input: string) => Promise<AgentResult>;
};

function createSpecialist(name: string, systemPrompt: string): SpecialistAgent {
  return {
    name,
    systemPrompt,
    run: async (input: string) => {
      const result = await fakeLLMCall(systemPrompt, input);
      return {
        content: result.output,
        tokensUsed: result.tokens,
        toolCalls: result.calls,
      };
    },
  };
}

const researcher = createSpecialist(
  "researcher",
  "You are a technical researcher. Read documentation, find patterns, and summarize findings. Output only the facts needed for implementation."
);

const coder = createSpecialist(
  "coder",
  "You are a senior TypeScript developer. Given requirements and research notes, write clean, tested code. Nothing else."
);

const reviewer = createSpecialist(
  "reviewer",
  "You are a code reviewer. Find bugs, security issues, and logic errors. Be specific. Cite line numbers."
);
```

每个专家都有一份聚焦的提示词；每个专家都拿到一个干净的上下文窗口，里面只有它需要的输入。

> Now split it. Each agent gets one job:
> Each specialist has a focused prompt. Each gets a clean context window with only the input it needs.

### Step 3: Coordinate Through Messages · 第三步：用消息协调

用显式的消息传递把专家们接线：

```typescript
type AgentMessage = {
  from: string;
  to: string;
  content: string;
  timestamp: number;
};

async function multiAgentApproach(task: string): Promise<AgentResult> {
  const messages: AgentMessage[] = [];
  let totalTokens = 0;
  let totalToolCalls = 0;

  const researchResult = await researcher.run(task);
  messages.push({
    from: "researcher",
    to: "coder",
    content: researchResult.content,
    timestamp: Date.now(),
  });
  totalTokens += researchResult.tokensUsed;
  totalToolCalls += researchResult.toolCalls;

  const coderInput = messages
    .filter((m) => m.to === "coder")
    .map((m) => `[From ${m.from}]: ${m.content}`)
    .join("\n");

  const codeResult = await coder.run(coderInput);
  messages.push({
    from: "coder",
    to: "reviewer",
    content: codeResult.content,
    timestamp: Date.now(),
  });
  totalTokens += codeResult.tokensUsed;
  totalToolCalls += codeResult.toolCalls;

  const reviewerInput = messages
    .filter((m) => m.to === "reviewer")
    .map((m) => `[From ${m.from}]: ${m.content}`)
    .join("\n");

  const reviewResult = await reviewer.run(reviewerInput);
  messages.push({
    from: "reviewer",
    to: "orchestrator",
    content: reviewResult.content,
    timestamp: Date.now(),
  });
  totalTokens += reviewResult.tokensUsed;
  totalToolCalls += reviewResult.toolCalls;

  return {
    content: messages.map((m) => `[${m.from} -> ${m.to}]: ${m.content}`).join("\n\n"),
    tokensUsed: totalTokens,
    toolCalls: totalToolCalls,
  };
}
```

每个智能体只收到发给自己的消息，没有上下文污染。调研员读掉的 50k token 文档，永远不会进入评审员的上下文。

> Wire the specialists together with explicit message passing:
> Each agent receives only the messages addressed to it. No context pollution. The researcher's 50k tokens of documentation reading never enter the reviewer's context.

### Step 4: Compare · 第四步：对比

```typescript
async function compare() {
  const task = "Build a rate limiter middleware for an Express.js API";

  console.log("=== Single Agent ===");
  const single = await singleAgentApproach(task);
  console.log(`Tokens: ${single.tokensUsed}`);
  console.log(`Tool calls: ${single.toolCalls}`);

  console.log("\n=== Multi-Agent ===");
  const multi = await multiAgentApproach(task);
  console.log(`Tokens: ${multi.tokensUsed}`);
  console.log(`Tool calls: ${multi.toolCalls}`);
}
```

多智能体版本的总 token 消耗更高（三个智能体、三次独立的 LLM 调用），但每个智能体的上下文保持干净。每个阶段的质量都更好，因为系统提示词是专职的。

> The multi-agent version uses more total tokens (three agents, three separate LLM calls) but each agent's context stays clean. The quality of each stage improves because the system prompt is specialized.

## Use It · 实战用法

本课产出一个可复用提示词，用来判断什么时候该转向多智能体。见 `outputs/prompt-multi-agent-decision.md`。

> This lesson produces a reusable prompt for deciding when to go multi-agent. See `outputs/prompt-multi-agent-decision.md`.

## Exercises · 练习

1. 加第四个专家：一个「测试员」智能体，接收编码者的代码和评审员的反馈，然后编写测试
2. 修改流水线，让评审员可以把反馈发回编码者，形成修订循环（最多 2 轮）
3. 把串行流水线改成扇出：让调研员和一个「需求分析员」智能体并行运行，合并两者输出后再交给编码者

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|----------------|----------------------|
| Swarm | 「AI 智能体的蜂群思维」 | 一组共享状态、没有固定领导者的对等智能体。行为从局部交互中涌现。 |
| Orchestrator | 「老板智能体」 | 把「派生并管理其他智能体」作为工具的智能体。它负责规划与委托，未必亲自干活。 |
| Coordinator | 「交通警察」 | 非智能体组件（通常只是代码而非 LLM），按规则在智能体之间路由消息。 |
| Consensus | 「智能体们达成一致」 | 一种要求多个智能体先达成一致才能继续的协议。用于需要裁决冲突输出的场合。 |
| Emergent behavior | 「智能体们自己想出来的」 | 从智能体交互中产生、但未被显式编程的系统级模式。可能有益，也可能有害。 |
| Fan-out / fan-in | 「智能体版 map-reduce」 | 把任务拆给并行智能体（fan-out），再合并它们的结果（fan-in）。 |
| Message passing | 「智能体互相通信」 | 智能体之间的通信机制：从一个智能体发给另一个的结构化数据，取代共享的上下文窗口。 |

## Further Reading · 延伸阅读

- [The Landscape of Emerging AI Agent Architectures](https://arxiv.org/abs/2409.02977) —— 多智能体模式综述
- [AutoGen: Enabling Next-Gen LLM Applications](https://arxiv.org/abs/2308.08155) —— 微软的多智能体对话框架
- [Claude Code subagents documentation](https://docs.anthropic.com/en/docs/claude-code) —— Claude Code 如何用 `Task` 做委托
- [CrewAI documentation](https://docs.crewai.com/) —— 基于角色的多智能体框架
