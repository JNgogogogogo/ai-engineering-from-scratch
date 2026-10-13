# Capstone 15 — Constitutional Safety Harness + Red-Team Range · 毕业项目 15 —— 宪法式安全护栏 + 红队靶场

> Anthropic 的 Constitutional Classifiers、Meta 的 Llama Guard 4、Google 的 ShieldGemma-2、NVIDIA 的 Nemotron 3 Content Safety，以及覆盖多语言的 X-Guard，共同定义了 2026 年的安全分类器栈。garak、PyRIT、NVIDIA Aegis 和 promptfoo 成了标准的对抗评估工具。NeMo Guardrails v0.12 把它们串进生产流水线。本次毕业项目把这一切接在一起：围绕一个目标应用的多层安全护栏、一个跑 6+ 攻击家族的自主红队 agent，以及一次产出可度量无害性增量（harmlessness delta）的宪法式自我批评运行。

> Anthropic's Constitutional Classifiers, Meta's Llama Guard 4, Google's ShieldGemma-2, NVIDIA's Nemotron 3 Content Safety, and X-Guard for multilingual coverage defined the 2026 safety-classifier stack. garak, PyRIT, NVIDIA Aegis, and promptfoo became the standard adversarial evaluation tools. NeMo Guardrails v0.12 ties them into a production pipeline. This capstone wires all of it together: a layered safety harness around a target app, an autonomous red-team agent running 6+ attack families, and a constitutional self-critique run that produces a measurable harmlessness delta.

**Type:** Capstone
**Languages:** Python (safety pipeline, red team), YAML (policy configs)
**Prerequisites:** Phase 10 (LLMs from scratch), Phase 11 (LLM engineering), Phase 13 (tools), Phase 14 (agents), Phase 18 (ethics, safety, alignment)
**Phases exercised:** P10 · P11 · P13 · P14 · P18
**Time:** 25 hours

## Problem · 问题

2026 年 LLM 安全的前沿，已经不是分类器管不管用（大致管用），而是如何把它们正确地组合在生产应用周围：既不过度拒绝，也不留下明摆着的洞。Llama Guard 4 处理英文政策违规。X-Guard（132 种语言）处理多语言越狱。ShieldGemma-2 抓基于图像的提示注入。NVIDIA Nemotron 3 Content Safety 覆盖企业类别。Anthropic 的 Constitutional Classifiers 是另一条路线，用于训练阶段而非服务阶段。

攻击的演化同样重要。PAIR 和 TAP 把越狱发现自动化。GCG 跑基于梯度的后缀攻击。多轮和语码转换（code-switch）攻击利用 agent 记忆。任何部署上线的 LLM 都需要一个红队靶场——garak 和 PyRIT 是公认的标准驱动器——外加成文的缓解措施和按 CVSS 评分的发现。

你要加固一个目标应用（一个 8B 指令微调模型，或其他毕业项目里的某个 RAG 聊天机器人），对它跑 6+ 个攻击家族，并产出一个加固前后的无害性度量。

> The frontier of LLM safety in 2026 is not whether classifiers work (they do, roughly) but how to compose them correctly around a production app without over-refusing or leaving obvious holes. Llama Guard 4 handles English policy violations. X-Guard (132 languages) handles multilingual jailbreak. ShieldGemma-2 catches image-based prompt injection. NVIDIA Nemotron 3 Content Safety covers enterprise categories. Anthropic's Constitutional Classifiers are a separate approach used during training rather than serving.
> Attack evolution matters too. PAIR and TAP automate jailbreak discovery. GCG runs gradient-based suffix attacks. Multi-turn and code-switch attacks exploit agent memory. Any deployed LLM needs a red-team range — garak and PyRIT are the canonical drivers — plus documented mitigations and CVSS-scored findings.
> You will harden a target application (either an 8B instruction-tuned model or one of the RAG chatbots from other capstones), run 6+ attack families against it, and produce a before/after harmlessness measurement.

## Concept · 概念

安全流水线有五层。**输入净化**：去零宽字符、解码 base64/rot13、Unicode 规范化。**政策层**：NeMo Guardrails v0.12 的 rails（偏离领域、毒性、PII 提取）。**分类器闸门**：输入过 Llama Guard 4，非英文过 X-Guard，图像输入过 ShieldGemma-2。**模型**：目标 LLM。**输出过滤**：输出过 Llama Guard 4、Presidio PII 清洗、适用时的引用强制。**HITL 层**：被标记为高风险的输出进入一个 Slack 队列。

红队靶场跑在调度器上。PAIR 和 TAP 自主发现越狱。GCG 跑基于梯度的后缀攻击。ASCII / base64 / rot13 编码攻击。多轮攻击（人设扮演、记忆利用）。语码转换攻击（英语混斯瓦希里语或泰语）。每次运行产出一个结构化的发现文件，带 CVSS 评分和披露时间线。

宪法式自我批评运行是一次训练期干预。取 1k 条有害企图 prompt，让模型起草回答，对照一部成文宪法（「不伤害」规则）做批评，再在批评循环上重训。在留出评估集上度量加固前后的无害性增量。

> The safety pipeline is five layers. **Input sanitize**: strip zero-width chars, decode base64/rot13, normalize Unicode. **Policy layer**: NeMo Guardrails v0.12 rails (off-domain, toxicity, PII extraction). **Classifier gate**: Llama Guard 4 on input, X-Guard on non-English, ShieldGemma-2 on image inputs. **Model**: the target LLM. **Output filter**: Llama Guard 4 on output, Presidio PII scrub, citation enforcement where applicable. **HITL tier**: outputs flagged high-risk go to a Slack queue.
> The red-team range runs on a scheduler. PAIR and TAP autonomously discover jailbreaks. GCG runs gradient-based suffix attacks. ASCII / base64 / rot13 encoding attacks. Multi-turn attacks (persona adoption, memory exploitation). Code-switch attacks (mix English with Swahili or Thai). Each run produces a structured findings file with CVSS scoring and disclosure timeline.
> The constitutional-self-critique run is a training-time intervention. Take 1k harmful-attempt prompts, have the model draft a response, critique it against a written constitution (do-not-harm rules), and retrain on the critique loop. Measure the before/after harmlessness delta on a held-out eval.

## Architecture · 架构

```
request (text / image / multilingual)
      |
      v
input sanitize (strip zero-width, decode, normalize)
      |
      v
NeMo Guardrails v0.12 rails (off-domain, policy)
      |
      v
classifier gate:
  Llama Guard 4 (English)
  X-Guard (multilingual, 132 langs)
  ShieldGemma-2 (image prompts)
  Nemotron 3 Content Safety (enterprise)
      |
      v (allowed)
target LLM
      |
      v
output filter: Llama Guard 4 + Presidio PII + citation check
      |
      v
HITL tier for flagged outputs

parallel:
  red-team scheduler
    -> garak (classic attacks)
    -> PyRIT (orchestrated red team)
    -> autonomous jailbreak agent (PAIR + TAP)
    -> GCG suffix attacks
    -> multilingual / code-switch
    -> multi-turn persona adoption

output: CVSS-scored findings + disclosure timeline + before/after harmlessness delta
```

## Stack · 技术栈

- 安全分类器：Llama Guard 4、ShieldGemma-2、NVIDIA Nemotron 3 Content Safety、X-Guard
- 护栏框架：NeMo Guardrails v0.12 + OPA
- 红队驱动器：garak（NVIDIA）、PyRIT（Microsoft Azure）、NVIDIA Aegis、promptfoo
- 越狱 agent：PAIR（Chao et al., 2023）、Tree-of-Attacks（TAP）、GCG 后缀
- 宪法式训练：Anthropic 风格的自我批评循环 + 在批评上做 SFT
- PII 清洗：Presidio
- 目标：一个 8B 指令微调模型，或其他毕业项目的某个 RAG 聊天机器人

```figure
cf-safety-stack
```

## Build It · 动手造

1. **目标搭建。** 在 vLLM 上起一个 8B 指令微调模型（或复用其他毕业项目的 RAG 聊天机器人）。这就是受测应用。

2. **安全流水线包裹。** 把五层流水线接到目标四周。验证每一层都可单独观测（Langfuse 里每层一个 span）。

3. **分类器覆盖。** 加载 Llama Guard 4、X-Guard（多语言）、ShieldGemma-2（图像）。各自跑一个小标注集建立基线。

4. **红队调度器。** 调度 garak、PyRIT、一个 PAIR agent、一个 TAP agent、一个 GCG 运行器、一个多轮攻击者、一个语码转换攻击者。各自跑在独立队列上。

5. **攻击套件。** 六个攻击家族：(1) PAIR 自动越狱、(2) TAP 攻击树、(3) GCG 梯度后缀、(4) ASCII / base64 / rot13 编码、(5) 多轮人设、(6) 多语言语码转换。报告每个家族的成功率。

6. **宪法式自我批评。** 精选 1k 条有害企图 prompt。每一条都由目标起草回答。一个批评 LLM 对照成文宪法（「不伤害」「引用证据」「拒绝非法请求」）打分。被批评者反对的 prompt 得到改写；目标在批评改进后的语对上微调。在留出评估上度量前后的无害性。

7. **过度拒绝度量。** 在一个良性 prompt 套件（如 XSTest）上跟踪假阳性率。目标必须在良性问题上保持有用。

8. **CVSS 评分。** 每次成功的越狱都按 CVSS 4.0 评分（攻击向量、复杂度、影响）。产出一份披露时间线和缓解计划。

9. **靶场自动化。** 以上全部跑在 cron 上；发现写入队列；过度拒绝回归告警发到 Slack。

> 2. **Safety pipeline wrap.** Wire the five-layer pipeline around the target. Verify each layer is individually observable (span per layer in Langfuse).
> 5. **Attack suite.** Six attack families: (1) PAIR automated jailbreak, (2) TAP tree-of-attacks, (3) GCG gradient suffix, (4) ASCII / base64 / rot13 encoding, (5) multi-turn persona, (6) multilingual code-switch. Report success rate per family.
> 7. **Over-refusal measurement.** Track false-positive rate on a benign prompt suite (e.g., XSTest). The target must stay helpful on benign questions.
> 8. **CVSS scoring.** For each successful jailbreak, score on CVSS 4.0 (attack vector, complexity, impact). Produce a disclosure timeline and mitigation plan.

## Use It · 实战用法

```
$ safety probe --model=target --family=PAIR --budget=50
[attacker]   PAIR agent running on target
[attack]     attempt 1/50: disguise query as academic research ... blocked
[attack]     attempt 2/50: appeal to roleplay ... blocked
[attack]     attempt 3/50: chain-of-thought coax ... SUCCEEDED
[finding]    CVSS 4.8 medium: roleplay bypass on target
[range]      7 successes out of 50 (14% success rate)
```

## Ship It · 交付

`outputs/skill-safety-harness.md` 是交付物：一条生产级的多层安全流水线，外加一个可复现的红队靶场和前后无害性增量。

| 权重 | 评分标准 | 度量方式 |
|:-:|---|---|
| 25 | 攻击面覆盖 | 演练 6+ 攻击家族、2+ 语言 |
| 20 | 真阳 / 假阳权衡 | 攻击拦截率 vs XSTest 良性通过率 |
| 20 | 自我批评增量 | 留出评估上的前后无害性 |
| 20 | 文档与披露 | 按 CVSS 评分的发现，带时间线 |
| 15 | 自动化与可复现 | 全部跑在 cron 上并带告警 |
| **100** | | |

> `outputs/skill-safety-harness.md` is the deliverable. A production-grade layered safety pipeline plus a reproducible red-team range with before/after harmlessness deltas.

## Exercises · 练习

1. 在一个 RAG 聊天机器人上跑 garak 的提示注入插件，比较有和没有输出过滤层时的攻击成功率。

2. 加第七个攻击家族：经由检索文档的间接提示注入。度量需要追加的防御。

3. 实现「拒绝但给帮助」模式：护栏拦截时，目标给出一个更安全的相关答案，而不是干巴巴地拒绝。度量 XSTest 差值。

4. 多语言覆盖缺口：找一个 X-Guard 表现不佳的语言。提出一个针对它的微调数据集。

5. 在一个 30B 模型上跑宪法式自我批评，度量增量是否会随规模放大。

> 1. Run garak's plugin for prompt-injection on a RAG chatbot and compare attack success rate with and without the output-filter layer.
> 5. Run the constitutional self-critique on a 30B model and measure whether the delta scales.

## Key Terms · 术语表

| 术语 | 俗称 | 实际含义 |
|------|-----------------|------------------------|
| Layered safety（分层安全） | "纵深防御" | 在输入、闸门、输出、HITL 各处布置多重护栏 |
| Llama Guard 4 | "Meta 的安全分类器" | 2026 年的参照输入/输出内容分类器 |
| PAIR | "越狱 agent" | 关于 LLM 驱动越狱发现的论文（Chao et al.） |
| TAP | "攻击树" | PAIR 的树搜索变体 |
| GCG | "贪心坐标梯度" | 基于梯度的对抗后缀攻击 |
| Constitutional self-critique（宪法式自我批评） | "Anthropic 式训练" | 目标起草 → 批评者打分 → 改写 → 重训 |
| XSTest | "良性探针集" | 度量过度拒绝回归的基准 |
| CVSS 4.0 | "严重度评分" | 安全发现的标准漏洞评分 |

## Further Reading · 延伸阅读

- [Anthropic Constitutional Classifiers](https://www.anthropic.com/research/constitutional-classifiers) —— 训练期参照
- [Meta Llama Guard 4](https://www.llama.com/docs/model-cards-and-prompt-formats/llama-guard-4/) —— 2026 年的输入/输出分类器
- [Google ShieldGemma-2](https://huggingface.co/google/shieldgemma-2b) —— 图像 + 多模态安全
- [NVIDIA Nemotron 3 Content Safety](https://developer.nvidia.com/blog/building-nvidia-nemotron-3-agents-for-reasoning-multimodal-rag-voice-and-safety/) —— 企业参照
- [X-Guard (arXiv:2504.08848)](https://arxiv.org/abs/2504.08848) —— 132 语言多语言安全
- [garak](https://github.com/NVIDIA/garak) —— NVIDIA 红队工具箱
- [PyRIT](https://github.com/Azure/PyRIT) —— 微软红队框架
- [NeMo Guardrails v0.12](https://docs.nvidia.com/nemo-guardrails/) —— rails 框架
- [PAIR (arXiv:2310.08419)](https://arxiv.org/abs/2310.08419) —— 越狱 agent 论文
