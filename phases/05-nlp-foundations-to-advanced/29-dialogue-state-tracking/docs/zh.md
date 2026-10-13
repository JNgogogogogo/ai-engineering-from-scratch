# Dialogue State Tracking · 对话状态跟踪（DST）

> 「我想要北边一家便宜的餐厅……还是改成中等价位吧……再加个意大利菜。」三轮对话，三次状态更新。DST 让槽位-值字典始终同步，预订才不会出错。
>
> "I want a cheap restaurant in the north... actually make it moderate... and add Italian." Three turns, three state updates. DST keeps the slot-value dict in sync so the booking works.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 17 (Chatbots), Phase 5 · 20 (Structured Outputs)
**Time:** ~75 minutes

## The Problem · 问题在哪

在任务型对话系统（task-oriented dialogue）里，用户目标被编码成一组槽位-值对（slot-value pair）：`{cuisine: italian, area: north, price: moderate}`。用户的每一轮都可能新增、修改或删除一个槽位。系统必须读完整个对话，并正确输出当前状态。

错一个槽位，系统就会订错餐厅、排错航班、扣错卡。DST 是「用户说了什么」和「后端执行什么」之间的铰链。

2026 年有了 LLM，它为什么依然重要：

- 合规敏感领域（银行、医疗、机票预订）要求确定性的槽位值，而不是自由生成。
- 工具调用 agent 在调 API 之前仍然要先做槽位解析（slot resolution）。
- 多轮纠错比看上去难："不对，改到周四。"

现代流水线：经典 DST 概念 + LLM 抽取器 + 结构化输出护栏（guardrails）。

> In a task-oriented dialogue system, the user's goal is encoded as a set of slot-value pairs: `{cuisine: italian, area: north, price: moderate}`. Every user turn can add, change, or remove a slot. The system must read the whole conversation and output the current state correctly.
> Get a single slot wrong and the system books the wrong restaurant, schedules the wrong flight, or charges the wrong card. DST is the hinge between what the user said and what the backend executes.
> The modern pipeline: classical DST concepts + LLM extractors + structured-output guardrails.

## The Concept · 概念

![DST：对话历史 → 槽位值状态](../assets/dst.svg)

**任务结构。** 一个模式（schema）定义领域（restaurant、hotel、taxi）及其槽位（cuisine、area、price、people）。每个槽位可以是空、从封闭集合取值（price: {cheap, moderate, expensive}），或自由文本值（name: "The Copper Kettle"）。

**两种 DST 形式化。**

- **分类。** 对每个 (slot, candidate_value) 对预测是/否。适合封闭词表的槽位。2020 年前的标准。
- **生成。** 给定对话，把槽位值当自由文本生成。适合开放词表的槽位。现代默认做法。

**指标。** Joint Goal Accuracy（JGA，联合目标准确率）——每一轮 *所有* 槽位全对才算对的轮数占比。全对或全错。MultiWOZ 2.4 榜单在 2026 年顶部约 83%。

**架构。**

1. **基于规则（槽位正则 + 关键词）。** 窄领域的强基线。可调试。
2. **TripPy / BERT-DST。** BERT 编码 + 基于复制的生成。LLM 之前的标准。
3. **LDST（LLaMA + LoRA）。** 指令微调的 LLM + 领域-槽位提示。在 MultiWOZ 2.4 上达到 ChatGPT 级质量。
4. **免本体（ontology-free，2024–26）。** 跳过模式，直接生成槽位名和值。能处理开放领域。
5. **提示 + 结构化输出（2024–26）。** LLM + Pydantic 模式 + 受约束解码。5 行代码，生产可用。

### The classic failure modes · 经典失败模式

- **跨轮共指。** 「就用第一个选项吧。」得解析出是哪个选项。
- **覆盖还是追加。** 用户说「加意大利菜」，你是替换 cuisine 还是追加？
- **隐式确认。** 「OK 可以」——这算接受了那个预订吗？
- **纠正。** 「还是改到晚上 7 点。」必须更新时间，且不清掉其他槽位。
- **对系统上一句话的共指。** 「对，就那个。」哪个「那个」？

```figure
n5-slot-tracker
```

> Joint Goal Accuracy (JGA) — the fraction of turns where *every* slot is correct. All-or-nothing. MultiWOZ 2.4 leaderboard tops around 83% in 2026. ... **Co-reference across turns.** "Let's stay with the first option." Needs to resolve which option. ... **Implicit confirmations.** "OK cool" — did that accept the offered booking? ... **Correction.** "Actually make it 7 pm." Must update time without clearing other slots.

## Build It · 动手造

### Step 1: rule-based slot extractor · 第 1 步：基于规则的槽位抽取器

见 `code/main.py`。正则 + 同义词词典能覆盖窄领域里 70% 的规范说法：

```python
CUISINE_SYNONYMS = {
    "italian": ["italian", "pasta", "pizza", "italy"],
    "chinese": ["chinese", "chow mein", "noodles"],
}


def extract_cuisine(utterance):
    for canonical, synonyms in CUISINE_SYNONYMS.items():
        if any(syn in utterance.lower() for syn in synonyms):
            return canonical
    return None
```

出了规范词表就很脆。适合确定性的槽位确认场景。

> See `code/main.py`. Regex + synonym dictionaries cover 70% of canonical utterances in narrow domains:
> Brittle outside the canonical vocabulary. Works for deterministic slot confirmations.

### Step 2: state update loop · 第 2 步：状态更新循环

```python
def update_state(state, utterance):
    new_state = dict(state)
    for slot, extractor in SLOT_EXTRACTORS.items():
        value = extractor(utterance)
        if value is not None:
            new_state[slot] = value
    for slot in NEGATION_CLEARS:
        if is_negated(utterance, slot):
            new_state[slot] = None
    return new_state
```

三条不变式：

- 永远不要重置用户没碰过的槽位。
- 显式否定（「cuisine 算了」）必须清空。
- 用户纠正（「其实……」）必须覆盖，而不是追加。

> Three invariants:
> - Never reset a slot the user did not touch.
> - Explicit negation ("never mind the cuisine") must clear.
> - User correction ("actually...") must overwrite, not append.

### Step 3: LLM-driven DST with structured output · 第 3 步：结构化输出的 LLM DST

```python
from pydantic import BaseModel
from typing import Literal, Optional
import instructor

class RestaurantState(BaseModel):
    cuisine: Optional[Literal["italian", "chinese", "indian", "thai", "any"]] = None
    area: Optional[Literal["north", "south", "east", "west", "center"]] = None
    price: Optional[Literal["cheap", "moderate", "expensive"]] = None
    people: Optional[int] = None
    day: Optional[str] = None


def llm_dst(history, llm):
    prompt = f"""You track the slot values of a restaurant booking across turns.
Dialogue so far:
{render(history)}

Update the state based on the latest user turn. Output only the JSON state."""
    return llm(prompt, response_model=RestaurantState)
```

Instructor + Pydantic 保证拿到的是合法的状态对象。没有正则、没有模式不匹配、没有幻觉槽位。

> Instructor + Pydantic guarantees a valid state object. No regex, no schema mismatches, no hallucinated slots.

### Step 4: JGA evaluation · 第 4 步：JGA 评估

```python
def joint_goal_accuracy(predicted_states, gold_states):
    correct = sum(1 for p, g in zip(predicted_states, gold_states) if p == g)
    return correct / len(predicted_states)
```

校准一下：系统在多大比例的轮次上 *所有* 槽位全对？MultiWOZ 2.4 上 2026 年的头部系统是 80-83%。你的领域内系统在窄词表上应该超过它，否则不如直接用 LLM 基线。

> Calibrate: what fraction of turns does the system get ALL slots right? For MultiWOZ 2.4, top 2026 systems: 80-83%. Your in-domain system should exceed that on your narrow vocabulary or the LLM baseline beats you.

### Step 5: handling correction · 第 5 步：处理纠正

```python
CORRECTION_CUES = {"actually", "no wait", "on second thought", "change that to"}


def is_correction(utterance):
    return any(cue in utterance.lower() for cue in CORRECTION_CUES)
```

检测到纠正时，覆盖最近更新的槽位，而不是追加。没有 LLM 帮忙很难做对。现代模式：永远让 LLM 从历史重新生成整个状态，而不是增量更新——这样天然就能处理纠正。

> On a detected correction, overwrite the last-updated slot rather than appending. Hard to get right without LLM help. The modern pattern: always let the LLM regenerate the whole state from history rather than incrementally updating — this naturally handles corrections.

## Pitfalls · 常见的坑

- **全历史重生成的成本。** 让 LLM 每轮重新生成状态，总 token 消耗是 O(n²)。限制历史长度，或者把旧轮次做摘要。
- **模式漂移。** 事后新增槽位会破坏旧的训练数据。给模式做版本管理。
- **大小写敏感。** "Italian" vs "italian" vs "ITALIAN"——处处都要归一化。
- **隐式继承。** 用户之前说过「4 个人」，后来改时间不应该把人数清掉。永远传完整历史。
- **自由文本 vs 封闭集合。** 名字、时间、地址需要自由文本槽位；菜系和区域是封闭的。模式里两者都要有。

> **Full-history regeneration cost.** Letting the LLM regenerate state each turn costs O(n²) total tokens. Cap history or summarize older turns. ... **Implicit inheritance.** If the user has previously specified "for 4 people," a new request for a different time should not clear people. Always pass the full history. ... **Free-form vs closed-set.** Names, times, and addresses need free-form slots; cuisines and areas are closed. Mix both in the schema.

## Use It · 实战用法

2026 年的选型表：

| 场景 | 方案 |
|-----------|----------|
| 窄领域（一两个意图） | 规则 + 正则 |
| 宽领域、有标注数据 | LDST（LLaMA + LoRA，MultiWOZ 式数据） |
| 宽领域、无标注、要上生产 | LLM + Instructor + Pydantic 模式 |
| 语音输入 | ASR + 归一化器 + LLM-DST |
| 多领域预订流程 | 模式引导的 LLM，每个领域一个 Pydantic 模型 |
| 合规敏感 | 规则为主，LLM 兜底 + 确认流程 |

> The 2026 stack:

## Ship It · 交付

保存为 `outputs/skill-dst-designer.md`：

```markdown
---
name: dst-designer
description: Design a dialogue state tracker — schema, extractor, update policy, evaluation.
version: 1.0.0
phase: 5
lesson: 29
tags: [nlp, dialogue, task-oriented]
---

Given a use case (domain, languages, vocab openness, compliance needs), output:

1. Schema. Domain list, slots per domain, open vs closed vocabulary per slot.
2. Extractor. Rule-based / seq2seq / LLM-with-Pydantic. Reason.
3. Update policy. Regenerate-whole-state / incremental; correction handling; negation handling.
4. Evaluation. Joint Goal Accuracy on a held-out dialogue set, slot-level precision/recall, confusion on the hardest slot.
5. Confirmation flow. When to explicitly ask the user to confirm (destructive actions, low-confidence extractions).

Refuse LLM-only DST for compliance-sensitive slots without a rule-based secondary check. Refuse any DST that cannot roll back a slot on user correction. Flag schemas without version tags.
```

> Save as `outputs/skill-dst-designer.md`:

## Exercises · 练习

1. **简单。** 用 `code/main.py` 给 3 个槽位（cuisine、area、price）搭基于规则的状态跟踪器，在 10 段手工对话上测试，量出 JGA。
2. **中等。** 同一份数据换 Instructor + Pydantic + 一个小 LLM，对比 JGA，检查最难的那几轮。
3. **困难。** 两套都实现并做路由：规则为主，当规则以低置信度输出少于 2 个槽位时回退到 LLM。量出组合后的 JGA 和每轮推理成本。

> 1. **Easy.** Build the rule-based state tracker in `code/main.py` for 3 slots (cuisine, area, price). Test on 10 hand-crafted dialogues. Measure JGA.
> 2. **Medium.** Same dataset with Instructor + Pydantic + a small LLM. Compare JGA. Inspect the hardest turns.
> 3. **Hard.** Implement both and route: rule-based primary, LLM fallback when rule-based emits <2 slots with confidence. Measure the combined JGA and inference cost per turn.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| DST | 对话状态跟踪 | 跨对话轮次维护槽位-值字典。 |
| Slot（槽位） | 用户意图的单元 | 后端需要的具名参数（cuisine、date）。 |
| Domain（领域） | 任务范围 | restaurant、hotel、taxi——一组组槽位。 |
| JGA | Joint Goal Accuracy | 所有槽位全对的轮数占比。全对或全错。 |
| MultiWOZ | 那个基准 | 多领域 WOZ 数据集；DST 评估的标准。 |
| Ontology-free DST | 无模式 | 直接生成槽位名和值，没有固定清单。 |
| Correction（纠正） | 「其实……」 | 覆盖此前已填槽位的那一轮。 |

## Further Reading · 延伸阅读

- [Budzianowski et al. (2018). MultiWOZ — A Large-Scale Multi-Domain Wizard-of-Oz](https://arxiv.org/abs/1810.00278) —— 公认的基准数据集。
- [Feng et al. (2023). Towards LLM-driven Dialogue State Tracking (LDST)](https://arxiv.org/abs/2310.14970) —— LLaMA + LoRA 指令微调做 DST。
- [Heck et al. (2020). TripPy — A Triple Copy Strategy for Value Independent Neural Dialog State Tracking](https://arxiv.org/abs/2005.02877) —— 基于复制的 DST 主力模型。
- [King, Flanigan (2024). Unsupervised End-to-End Task-Oriented Dialogue with LLMs](https://arxiv.org/abs/2404.10753) —— 基于 EM 的无监督任务型对话。
- [MultiWOZ leaderboard](https://github.com/budzianowski/multiwoz) —— 公认的 DST 结果榜。
