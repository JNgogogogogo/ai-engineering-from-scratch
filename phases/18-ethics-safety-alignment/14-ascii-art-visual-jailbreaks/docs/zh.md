# ASCII Art and Visual Jailbreaks · ASCII 艺术与视觉越狱

> Jiang, Xu, Niu, Xiang, Ramasubramanian, Li, Poovendran,「ArtPrompt: ASCII Art-based Jailbreak Attacks against Aligned LLMs」(ACL 2024, arXiv:2402.11753)。把有害请求中的安全相关词先掩码,再用同样的字母画成 ASCII 艺术字替换进去,发送这个"斗篷化"后的提示词。GPT-3.5、GPT-4、Gemini、Claude、Llama-2 都无法稳定识别 ASCII 艺术字词元。该攻击能绕过 PPL(困惑度过滤器)、Paraphrase(改写)防御和 Retokenization(重分词)。相关:ViTC 基准衡量模型对非语义视觉提示的识别能力;StructuralSleight 把这一思路推广到「罕见文本编码结构」(树、图、嵌套 JSON)这一整族编码攻击。

**Type:** Build
**Languages:** Python (stdlib, ArtPrompt token-masking harness)
**Prerequisites:** Phase 18 · 12 (PAIR), Phase 18 · 13 (MSJ)
**Time:** ~60 minutes

## Learning Objectives · 学习目标

- 描述 ArtPrompt 攻击:词识别步骤、ASCII 艺术替换、最终"斗篷化"提示词
- 解释为什么标准防御(PPL、Paraphrase、Retokenization)对 ArtPrompt 失效
- 定义 ViTC 并说明它度量什么
- 描述 StructuralSleight 作为对任意「罕见文本编码结构」的推广

> Describe the ArtPrompt attack: word-identification step, ASCII-art substitution, final cloaked prompt. / Explain why standard defenses (PPL, Paraphrase, Retokenization) fail on ArtPrompt. / Define ViTC and describe what it measures. / Describe StructuralSleight as a generalization to arbitrary Uncommon Text-Encoded Structures.

## The Problem · 问题在哪

第 12 课的改写与角色扮演攻击、第 13 课的长上下文攻击都作用在**文本模式层**。ArtPrompt 作用在**识别层**:模型解析不了那个被禁词元——它解析的是一副用字符画出来的"图"。安全过滤器看到的是无害的标点;模型看到的却是一个词。

> Attacks via paraphrase and roleplay (Lesson 12) and via long context (Lesson 13) operate on the text-level pattern. ArtPrompt operates at the recognition level: the model does not parse the forbidden token. It parses an image rendered in characters. The safety filter sees harmless punctuation. The model sees a word.

## The Concept · 概念

### ArtPrompt, two steps · ArtPrompt 的两步

第一步:**词识别(Word Identification)**。给定一个有害请求,攻击者用 LLM 找出其中安全相关的词(比如 "how to make a bomb" 里的 "bomb")。

第二步:**斗篷化提示词生成(Cloaked Prompt Generation)**。把每个被识别的词替换成它的 ASCII 艺术字渲染(一个 7x5 或 7x7 的字符块,拼出字母形状)。模型收到的是一堆标点和空格组成的网格——足够强的模型能把它识别成那个词;而安全过滤器看到的只是网格。

结果:GPT-4、Gemini、Claude、Llama-2、GPT-3.5 全部失守。在其基准子集上攻击成功率超过 75%。

> Step 1. Word Identification. Given a harmful request, the attacker uses an LLM to identify the safety-relevant words... Step 2. Cloaked Prompt Generation. Replace each identified word with its ASCII-art rendering... Result: GPT-4, Gemini, Claude, Llama-2, GPT-3.5 all fail. Attack success rate above 75% on their benchmark subset.

### Why the standard defenses fail · 为什么标准防御会失败

- **PPL(困惑度过滤器)**:ASCII 艺术的困惑度确实很高——但所有新颖输入的困惑度都高。能把 ArtPrompt 拦下来的阈值,同样会把合法的结构化输入拦下来。
- **Paraphrase(改写)**:改写提示词会破坏 ASCII 艺术。但实践中,改写用的 LLM 常常会把艺术字保留甚至重构出来。
- **Retokenization(重分词)**:换一种方式切分词元,改变不了"模型的视觉在识别字母形状"这个事实。

底层问题是:安全过滤器工作在词元层或语义层,而 ArtPrompt 工作在视觉识别层。

> **PPL (perplexity filter).** ASCII art has high perplexity — but so does all novel input... **Paraphrase.** Paraphrasing the prompt destroys the ASCII art. In practice, paraphrase LLMs often preserve or reconstruct the art. **Retokenization.** Splitting tokens differently does not change that the model's vision is recognizing letter shapes. / The underlying issue is that safety filters are token- or semantic-level; ArtPrompt operates at the visual recognition level.

### ViTC benchmark · ViTC 基准

度量对**非语义视觉提示**的识别:模型读 ASCII 艺术、wingdings 等非文本语义视觉内容的能力。ArtPrompt 的效果与 ViTC 准确率正相关——模型读视觉文本越强,ArtPrompt 对它越有效。这是一个**能力-安全权衡**。

> Recognition of non-semantic visual prompts. Measures the model's ability to read ASCII-art, wingdings, and other non-text-semantic visual content. ArtPrompt's effectiveness correlates with ViTC accuracy... This is a capability-safety tradeoff.

### StructuralSleight · 结构化推广

StructuralSleight 把 ArtPrompt 推广为:**罕见文本编码结构(UTES, Uncommon Text-Encoded Structures)**。树、图、嵌套 JSON、JSON 里嵌 CSV、diff 风格代码块……只要一个结构在安全训练数据里罕见、但模型又能解析,它就可能藏住有害内容。

防御启示:安全机制必须泛化到模型能解析的所有结构化表示——这个集合很大,而且还在增长。

> Generalizes ArtPrompt: Uncommon Text-Encoded Structures (UTES). Trees, graphs, nested JSON, CSV-in-JSON, diff-style code blocks. If a structure is rare in training safety data but parseable by the model, it can hide harmful content. / The defense implication: safety must generalize across the structured representations the model can parse. The set is large and growing.

### Image-modality analog · 图像模态类比

视觉大模型(GPT-5.2、Gemini 3 Pro、Claude Opus 4.5、Grok 4.1)扩大了攻击面。用真实图像做 ArtPrompt 式攻击,比 ASCII 艺术类比更强,因为图像编码器产生的信号更丰富。

> Visual LLMs (GPT-5.2, Gemini 3 Pro, Claude Opus 4.5, Grok 4.1) extend the attack surface. ArtPrompt-style attacks with actual images are stronger than ASCII-art analogs because image encoders produce richer signal.

### Where this fits in Phase 18 · 在 Phase 18 中的位置

第 12-14 课描述了三个正交的攻击向量:迭代精炼(PAIR)、上下文长度(MSJ)、编码(ArtPrompt/StructuralSleight)。第 15 课从模型中心攻击转向系统边界攻击(间接提示注入)。第 16 课讲防御工具的回应。

> Lessons 12-14 describe three orthogonal attack vectors: iterative refinement (PAIR), context length (MSJ), and encoding (ArtPrompt/StructuralSleight). Lesson 15 shifts from model-centric attacks to system-boundary attacks (indirect prompt injection). Lesson 16 describes the defensive tooling response.

```figure
al-ascii-cloak
```

## Use It · 实战用法

`code/main.py` 构建了一个玩具版 ArtPrompt。你可以把有害查询里的特定词用 ASCII 艺术字形"斗篷化",验证斗篷化后的字符串能通过关键词过滤器,并(可选)用简单的识别器把斗篷化字符串解码回原文。

> `code/main.py` builds a toy ArtPrompt. You can cloak specific words in a harmful query with ASCII-art glyphs, verify the cloaked string passes a keyword filter, and (optionally) decode the cloaked string back using a simple recognizer.

## Ship It · 交付

本课产出 `outputs/skill-encoding-audit.md`。给定一份越狱防御报告,它会枚举已覆盖的编码攻击族(ASCII 艺术、base64、leet 变体、UTF-8 同形字、UTES)以及拦截每一族的防御层。

> This lesson produces `outputs/skill-encoding-audit.md`. Given a jailbreak-defense report, it enumerates the encoding attack families covered (ASCII art, base64, leet-speak, UTF-8 homoglyph, UTES) and the defense layer that catches each.

## Exercises · 练习

1. 运行 `code/main.py`。验证斗篷化字符串能通过一个简单的关键词过滤器,报告所需的字符级改动。

2. 实现第二种编码:对同一个目标词做 base64。对比它与 ArtPrompt 的过滤器绕过率以及恢复难度。

3. 读 Jiang et al. 2024 第 4.3 节(五个模型的结果)。提出一个理由,解释为什么在同一基准上 Claude 对 ArtPrompt 的抗性比 Gemini 高。

4. 设计一种生成前防御,检测提示词中 ASCII 艺术形状的区域。在合法代码、表格和数学记号上测量其误报率。

5. StructuralSleight 列出了 10 种编码结构。勾画一个能处理全部 10 种的通用防御,并估计每个被防御提示词的计算成本。

> 1. Run `code/main.py`. Verify the cloaked string passes a simple keyword filter. Report the character-level change required. / 2. Implement a second encoding: base64 for the same target word... / 3. Read Jiang et al. 2024 Section 4.3 (five-model results)... / 4. Design a pre-generation defense that detects ASCII-art-shaped regions in the prompt... / 5. StructuralSleight lists 10 encoding structures...

## Key Terms · 关键术语

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|------------------------|
| ArtPrompt | "ASCII 艺术攻击" | 用 ASCII 艺术渲染掩掉安全词的两步越狱 |
| Cloaking | "把词藏起来" | 把被禁词元替换成模型读得出、过滤器读不出的视觉表示 |
| UTES | "罕见结构" | Uncommon Text-Encoded Structure——树、图、嵌套 JSON 等,用来夹带内容 |
| ViTC | "视觉-文本能力" | 衡量模型阅读非语义视觉编码能力的基准 |
| Perplexity filter | "PPL 防御" | 拒绝高困惑度的提示词;会失败,因为合法结构化输入得分同样高 |
| Retokenization | "分词器切换防御" | 用另一个分词器预处理提示词;会失败,因为识别发生在视觉层 |
| Homoglyph | "长得一样的字符" | 看起来与拉丁字母相同的 Unicode 字符;可绕过子串检查 |

> | ArtPrompt | "the ASCII-art attack" | Two-step jailbreak that masks safety words with ASCII-art renderings |
> | Cloaking | "hide the word" | Replace a forbidden token with a visual representation the model reads but the filter does not |
> | UTES | "uncommon structure" | Uncommon Text-Encoded Structure — tree, graph, nested JSON, etc. used to smuggle content |
> | ViTC | "visual-text capability" | Benchmark for model's ability to read non-semantic visual encoding |
> | Perplexity filter | "PPL defense" | Reject prompts with high perplexity; fails because legitimate structured input also scores high |
> | Retokenization | "tokenizer shift defense" | Pre-process the prompt with a different tokenizer; fails because recognition is visual |
> | Homoglyph | "lookalike characters" | Unicode characters that look identical to Latin letters; bypass substring checks |

## Further Reading · 延伸阅读

- [Jiang et al. — ArtPrompt (ACL 2024, arXiv:2402.11753)](https://arxiv.org/abs/2402.11753) —— ASCII 艺术越狱论文
- [Li et al. — StructuralSleight (arXiv:2406.08754)](https://arxiv.org/abs/2406.08754) —— UTES 推广
- [Chao et al. — PAIR (Lesson 12, arXiv:2310.08419)](https://arxiv.org/abs/2310.08419) —— 互补的迭代式攻击
- [Anil et al. — Many-shot Jailbreaking (Lesson 13)](https://www.anthropic.com/research/many-shot-jailbreaking) —— 互补的长度攻击
