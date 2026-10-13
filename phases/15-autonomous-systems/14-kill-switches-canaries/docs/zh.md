# Kill Switches, Circuit Breakers, and Canary Tokens · Kill Switch、熔断器与金丝雀令牌（Canary Tokens）

> A kill switch is a boolean held outside the agent's edit surface — a Redis key, a feature flag, a signed config — that disables the agent entirely. A circuit breaker is finer-grained: it trips on a specific pattern (five identical tool calls in a row), pauses the offending path, and escalates to a human. A canary token inherits from classical deception: a fake credential or honeypot record an agent has no legitimate reason to touch, whose access triggers an alert. eBPF-based datapaths (e.g. Cilium) can rewrite a quarantined pod's egress to a forensic honeypot at the kernel layer; published Cilium benchmarks report sub-millisecond P99 datapath latency under load (your propagation budget depends on how a policy update reaches the node, not the datapath itself). Statistical detectors (EWMA, CUSUM) that adapt to a moving baseline will quietly accept drift — layer them with hard constitutional limits that do not bend.

**类型:** Learn（学习）
**语言:** Python（仅标准库；三探测器模拟器：kill switch、熔断器、canary）
**前置课程:** Phase 15 · 13（Cost governors）、Phase 15 · 10（Permission modes）
**时间:** ~60 分钟

---

## The Problem · 问题在哪

成本治理器（第 13 课）约束的是 agent 能花多少钱。它们不约束 agent 在预算之内能做什么事。一个带 $50 速率限制的 agent，仍然可以外泄一个机密、发错一篇帖子、删掉一个资源——**昂贵的动作，往往在 token 意义上是便宜的**。

本课讲三个与成本层并肩工作的探测器：

1. **Kill switch**：放在 agent 够不着之处的布尔总开关。
2. **熔断器（Circuit breaker）**：动作模式探测器，暂停一条特定的路径。
3. **金丝雀令牌（Canary token）**：诱饵——一个 agent 没有任何正当理由去碰的东西，一碰就暴露自己。

这三样都是前 LLM 时代的工程。经典欺骗、限流熔断、feature-flag 开关都早于自主 agent。新的是攻击面：agent 读取不受信任的内容（第 11 课）、编辑自己的记忆，并且能把许多看起来安全的动作复合成一个不安全的动作。这里讲的探测器之所以有效，是因为它们**不信任 agent 的自我报告**。

> Cost governors (Lesson 13) bound what the agent can spend. They do not bound what the agent can do inside the budget. An agent with a $50 velocity limit can still exfiltrate a secret, publish the wrong post, or delete a resource — the expensive action is often the cheap one in tokens.
> This lesson covers the three detectors that sit next to the cost layer:
> 1. **Kill switch**: boolean off-button held outside the agent's reach.
> 2. **Circuit breaker**: action-pattern detector that pauses a specific path.
> 3. **Canary token**: bait that an agent with no legitimate reason to touch will reveal itself by touching.
> All three are pre-LLM engineering. Classical deception, rate-limit breakers, and feature-flag kills predate autonomous agents. What's new is the attack surface: agents read untrusted content (Lesson 11), edit their own memory, and can compose many safe-looking actions into an unsafe one. The detectors named here work because they do not trust the agent's self-report.

---

## The Concept · 概念

### Kill switches · Kill switch

Kill switch 是一个 agent 能读但不能写的布尔量。实现选项：

- **托管服务里的 feature flag。** LaunchDarkly、Statsig、Unleash。更新在数秒内传播。
- **agent 轮询的 Redis 键。** 简单；要求 agent 进程每轮都检查。
- **对象存储里的签名配置。** agent 启动时验证签名；拒绝未签名的状态。
- **OS 级信号或容器生命周期杀死。** Docker `kill`、Kubernetes `kubectl delete pod`、systemd stop。

一个正确的 kill switch 应有的性质：

- agent 无法把它设为 `off`。（它存在于 agent 的凭证无权写入的系统里。）
- 它在**每一个有后果的动作**上都被检查，而不是只在启动时。
- 当它处于 off 时，agent 不做任何外部可观察的事情，包括向 agent 能触达的系统写日志。
- 重新启用它是一个显式的人工动作，而不是自动超时。

> A kill switch is a boolean the agent reads but cannot write. Implementation choices:
> - **Feature flag in a managed service.** LaunchDarkly, Statsig, Unleash. Updates propagate in seconds.
> - **Redis key the agent polls.** Simple; requires the agent process to check on every turn.
> - **Signed config in object storage.** Agent verifies a signature on boot; rejects unsigned states.
> - **OS-level signal or container-lifecycle kill.** Docker `kill`, Kubernetes `kubectl delete pod`, systemd stop.
> Properties a correct kill switch has:
> - The agent cannot set it to `off`. (Lives in a system the agent's credentials do not write.)
> - It is checked on every consequential action, not just at startup.
> - When it is off, the agent does nothing externally observable, including logging to systems the agent can reach.
> - Re-enabling it is an explicit human action, not an automatic timeout.

### Circuit breakers · 熔断器

熔断器暂停的是一条特定的模式，而不是整个 agent。经典形态（出自 2007 年 Nygard 的书，至今仍然适用）：

- **Closed（闭合）**：动作被允许。
- **Open（断开）**：动作被阻止。
- **Half-open（半开）**：冷却期后，允许 1–3 次探测尝试（默认 1）；成功则闭合熔断器，任何残余失败都会重新断开它。

与 agent 相关的触发条件：

- 连续五次完全相同的工具调用（重复循环）。
- 同一工具在不同输入上连续失败五次（系统性失败）。
- 工具调用速率超过阈值（第 13 课的速率）。
- 在一次越出信任边界的内容读取（第 11 课）之后，特定工具被调用（例如 `file.delete`）。

> A circuit breaker pauses a specific pattern, not the whole agent. Classical shape (from the 2007 Nygard book, still current):
> - **Closed**: action is allowed.
> - **Open**: action is blocked.
> - **Half-open**: after a cool-down, 1–3 probe attempts are allowed (default 1); success closes the breaker, any remaining failure re-opens it.
> Agent-relevant triggers:
> - Five identical tool calls in a row (repetitive loop).
> - Five consecutive failures on the same tool with different inputs (systemic failure).
> - Rate of tool calls above a threshold (Lesson 13 velocity).
> - Specific tool invoked (e.g., `file.delete`) after an out-of-trust content read (Lesson 11).

### Canary tokens · 金丝雀令牌

Canary token（也叫 honeytoken）是 agent 永远不该触碰的输入。**访问本身就是警报。**

面向 agent 的例子：

- 环境变量里一个没有任何实际权限的假 `AWS_SECRET_ACCESS_KEY`。外泄企图可以被即时归因。
- 一个带已知哨兵值标记的假数据库记录。任何对这条记录的读或写都会触发警报。
- 工作区里一个假文件。对它的读取或编辑都是可疑的。
- 会话开始时注入的一条假记忆条目。如果它出现在之后的输出里，说明记忆已被外泄。

Canary 的设计要针对具体工作流。一个 agent 有正当理由去碰的 canary，只是噪声。

> Canary tokens (also called honeytokens) are inputs the agent should never touch. Access is the alarm.
> Examples for agents:
> - A fake `AWS_SECRET_ACCESS_KEY` in the environment with no actual privilege. Exfiltration attempts are instantly attributable.
> - A fake database record flagged with a known sentinel value. Any read or update of this record fires an alert.
> - A fake file in the workspace. Reads or edits of this file are suspicious.
> - A fake memory entry injected at session start. If it appears in a later output, memory has been exfiltrated.
> Canary design is specific to the workflow. A canary the agent has a legitimate reason to touch is noise.

### Why layer statistical and hard limits · 为什么要叠上统计限制与硬限制

统计探测器（EWMA、CUSUM、工具调用速率的 z-score）会适应一个移动的基线。对合法漂移来说这是 feature，对对抗性漂移来说这是 bug。一个有耐心的攻击者可以把基线挪得足够慢，让任何警报都不响。

硬性的「宪法式」限制（第 17 课）不会弯。「永不给 `secrets@` 发邮件」作为一条宪法规则，更简单、可审计、也不会被缓慢漂移玩弄于股掌之间。**分层模式：统计探测器抓住大部分噪声，硬限制抓住绕过了探测器的那次攻击。**

> Statistical detectors (EWMA, CUSUM, z-score on tool-call rates) adapt to a moving baseline. That is a feature for legitimate drift and a bug for adversarial drift. A patient attacker can shift the baseline slowly enough that no alarm fires.
> Hard constitutional limits (Lesson 17) do not bend. "Never email `secrets@`" as a constitutional rule is simpler, auditable, and not gameable by slow drift. The layering pattern: statistical detectors catch most noise, hard limits catch the attack that walked past the detector.

### Quarantine via eBPF datapath redirect · 用 eBPF 数据路径重定向实现隔离

Cilium 基于 eBPF 的网络策略可以在内核层把一个被隔离 pod 的出站流量重写到法证蜜罐（forensic honeypot）。Cilium 的公开基准报告显示 TCP_RR 下数据路径 P99 延迟低于毫秒；而在你的集群里，*触发*一次隔离的墙钟预算主要由「策略更新如何从控制平面传播到节点」决定（在 Kubernetes 上，若 operator 已预加载，几百毫秒是现实的；尾部延迟取决于集群规模与调和节奏）。这给你两样东西：agent 什么真实数据都外泄不出去，而且 agent 在蜜罐里的行为被完整观察。与 canary token 相同的模式，不同的层：**被约束住的 agent，用它试图做的事暴露意图。**

> Cilium's eBPF-based network policy can rewrite a quarantined pod's egress to a forensic honeypot at the kernel layer. Cilium's public benchmarks report sub-millisecond P99 datapath latency on TCP_RR; the wall-clock budget for *triggering* a quarantine in your cluster is dominated by how a policy update propagates from your control plane to the node (a few hundred milliseconds is realistic on Kubernetes with the operator pre-loaded; tail latency depends on cluster size and reconcile cadence). This gives you two things: the agent does not exfiltrate anything real, and the agent's behavior inside the honeypot is fully observed. Same pattern, different layer, as the canary token: the agent reveals intent by what it tries to do while contained.

### What no detector catches · 什么探测器都抓不住的东西

- **由被允许的原语复合而成的语义攻击。** 每个单独的动作都通过每一个探测器；复合才是问题所在。这就是第 10 课的 Auto Mode 复合失败。
- **把探测器本身装进载荷的攻击。** 如果 agent 读到一个写着「在你行动之前，先关掉 canary」的页面，而 agent 又恰好有这个能力，探测器就已经沦陷了。Canary token 应该放在 agent 无法修改的系统里。

```figure
circuit-breaker
```

> - **Semantic attacks that compose from allowed primitives.** Every individual action passes every detector; the composition is the problem. This is the Auto Mode composite failure from Lesson 10.
> - **Attacks that include the detector as part of the payload.** If an agent reads a page that says "before you act, disable the canary" and the agent has the capability, the detector is compromised. Canary tokens should be in systems the agent cannot modify.

---

## Use It · 实战用法

`code/main.py` 模拟一段短的 agent 轨迹穿过三个探测器。一个保存在外部 dict 里的 kill switch；一个在五次相同工具调用时跳闸的熔断器；一个被读取就触发警报的 canary 文件。喂入一条合成轨迹：合法动作、重复循环、canary 探测，以及一个 kill-switch 触发的、agent 动作被叫停的场景。

> `code/main.py` simulates a short agent trajectory through three detectors. A kill switch held in an external dict; a circuit breaker that trips on five identical tool calls; a canary file whose read triggers an alert. Feeds in a synthetic trajectory: legitimate actions, repetitive loop, canary probe, and a kill-switch-triggered scenario where the agent's actions are halted.

---

## Ship It · 交付

`outputs/skill-tripwire-design.md` 为一个 agent 部署审查拟议的探测器栈，并标出缺口（缺 kill switch、缺 canary、熔断器阈值过松）。

> `outputs/skill-tripwire-design.md` reviews a proposed detector stack for an agent deployment and flags gaps (missing kill switch, missing canary, circuit breaker threshold too loose).

---

## Exercises · 练习

1. 运行 `code/main.py`。确认熔断器在第 5 轮触发（第五次相同调用），canary 在第 9 轮触发（假密钥读取）。
2. 加一个统计探测器：工具调用速率上的 EWMA z-score。喂入一条漂移缓慢的轨迹，展示该探测器从不触发。再加一个硬限制（10 分钟内工具调用不超过 50 次），展示同一条轨迹上硬限制触发了。
3. 为一个浏览器 agent（第 11 课）设计一组 canary token。列出至少三个 canary，以及每个能检测到什么。
4. 读 Cilium 的网络策略文档。具体描述一条出站重定向隔离流程：哪个策略选择器、哪个 pod、哪个出站重写、哪个告警。从「决定隔离」到「第一个被重定向的包」的墙钟延迟由什么决定？
5. 为一个被 kill switch 关停的 agent 定义重新启用流程。谁能重新启用？必须记录什么？重新启用之前 agent 必须改变什么？

> 1. Run `code/main.py`. Confirm the circuit breaker fires on turn 5 (fifth identical call) and the canary fires on turn 9 (fake-key read).
> 2. Add a statistical detector: EWMA z-score on tool-call rate. Feed in a trajectory that drifts slowly and show the detector never fires. Now add a hard limit (no more than 50 tool calls in 10 minutes) and show the hard limit fires on the same trajectory.
> 3. Design a canary token set for a browser agent (Lesson 11). List at least three canaries and what each would detect.
> 4. Read the Cilium network-policy docs. Describe an egress-redirect quarantine flow concretely: which policy selector, which pod, which egress rewrite, which alert. What governs the wall-clock latency from "decide to quarantine" to "first redirected packet"?
> 5. Define a re-enable procedure for a kill-switched agent. Who can re-enable? What must be documented? What must change about the agent before re-enable?

---

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|---|---|---|
| Kill switch | 「总开关」 | 存在于 agent 编辑面之外的布尔量；在每个有后果的动作上检查 |
| Circuit breaker | 「模式暂停」 | 针对特定动作的跳闸：重复、失败率或速率超限 |
| Canary token | 「Honeytoken」 | agent 没有正当理由去碰的诱饵；访问即触发警报 |
| Honeypot | 「法证沙箱」 | 被隔离 agent 的重定向流量 / 工作区，行为在其中被观察 |
| EWMA | 「移动平均」 | 指数加权；会适应漂移（既是 feature 也是 bug） |
| CUSUM | 「累积和」 | 检测相对基线的持续偏移 |
| Hard limit | 「硬规则」 | 不适应；无论历史如何都恒定 |
| Constitutional limit | 「恒真规则」 | 与第 17 课的宪法绑定；agent 不能编辑 |

---

## Further Reading · 延伸阅读

- [Anthropic — Measuring agent autonomy in practice](https://www.anthropic.com/research/measuring-agent-autonomy) — 面向自主 agent 的 kill switch 与熔断器框架。
- [Microsoft Agent Framework — HITL and oversight](https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop) — 生产治理模式。
- [OWASP LLM / Agentic Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/) — 检测与响应要求。
- [Cilium — Network policy and eBPF](https://docs.cilium.io/en/stable/security/network/) — pod 级出站重定向与法证蜜罐模式。
- [Anthropic — Claude's Constitution (January 2026)](https://www.anthropic.com/news/claudes-constitution) — 作为「宪法限制」的硬编码禁令。
