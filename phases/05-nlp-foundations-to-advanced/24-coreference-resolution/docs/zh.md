# Coreference Resolution · 指代消解

> "She called him. He did not answer. The doctor was at lunch." —— 三处指代，两个人，一个名字都没提。指代消解（coreference resolution）负责搞清楚谁是谁。
>
> "She called him. He did not answer. The doctor was at lunch." Three references to two people and nobody is named. Coreference resolution figures out who is who.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 5 · 06 (NER), Phase 5 · 07 (POS & Parsing)
**Time:** ~60 minutes

## The Problem · 问题在哪

从一篇 300 词的文章里抽出 Apple Inc. 的每一次提及。文章直接写「Apple」时很容易；写「the company」「they」「Cupertino's technology giant」「Jobs's firm」时就难了。不把这些提及归并到同一个实体，你的 NER 流水线会漏掉 60-80% 的提及。

指代消解把所有指向同一个现实世界实体的表达链进同一个簇（cluster）。它是表层 NLP（NER、句法分析）与下游语义（信息抽取、问答、摘要、知识图谱）之间的胶水。

2026 年它为什么重要：

- 摘要：「The CEO announced...」 vs 「Tim Cook announced...」——摘要里应该写出 CEO 的名字。
- 问答：「Who did she call?」需要先解析「she」。
- 信息抽取：知识图谱里把「PER1 founded Apple」和「Jobs founded Apple」记成两条是错的。
- 跨文档 IE：把同一事件的多篇文章里的提及合并起来，就是跨文档指代消解（cross-document coreference）。

> Extract every mention of Apple Inc. from a 300-word article. Easy when the article says "Apple." Hard when it says "the company," "they," "Cupertino's technology giant," or "Jobs's firm." Without resolving these mentions to the same entity, your NER pipeline misses 60-80% of the mentions.
> Coreference resolution links every expression that refers to the same real-world entity into one cluster. It is the glue between surface-level NLP (NER, parsing) and downstream semantics (IE, QA, summarization, KG).

## The Concept · 概念

![指代消解聚类：提及 → 实体](../assets/coref.svg)

**任务。** 输入：一篇文档。输出：提及（span）的一个聚类，每个簇对应一个实体。

**提及类型。**

- **命名实体（named entity）。**「Tim Cook」
- **名词短语（nominal）。**「the CEO」「the company」
- **代词（pronominal）。**「he」「she」「they」「it」
- **同位语（appositive）。**「Tim Cook, Apple's CEO,」

**架构。**

1. **规则式（Hobbs, 1978）。** 基于句法树、用语法规则做代词消解。很好的基线。在代词上出奇地难被打败。
2. **提及对分类器（mention-pair classifier）。** 对每一对提及 (m_i, m_j) 预测它们是否共指。用传递闭包成簇。2016 年之前的标准做法。
3. **提及排序（mention-ranking）。** 对每个提及，给候选先行词（antecedent，包括「无先行词」）排序，取第一名。
4. **基于 span 的端到端（Lee et al., 2017）。** Transformer 编码器。枚举长度上限以内的所有候选 span。预测提及分数。为每个 span 预测先行词概率。贪心成簇。现代默认方案。
5. **生成式（2024+）。** 提示 LLM：「列出文中每个代词及其先行词。」简单例子上效果很好，长文档和罕见指称对象上吃力。

**评估指标。** 五个标准指标（MUC、B³、CEAF、BLANC、LEA）——因为没有哪个单一指标能抓住聚类质量。前三个的平均值记作 CoNLL F1。2026 年 CoNLL-2012 上的 SOTA：约 83 F1。

**已知的难例。**

- 指向几页之前才引入的实体的确定性描述（definite description）。
- 桥接回指（bridging anaphora）（「the wheels」→ 之前提到的那辆车）。
- 中文、日语等语言中的零指代（zero anaphora）。
- 前指（cataphora，代词先于指称对象出现）：「When **she** walked in, Mary smiled.」

```figure
coref-links
```

> **The task.** Input: a document. Output: a clustering of mentions (spans) where each cluster refers to one entity.... **Span-based end-to-end (Lee et al., 2017).** Transformer encoder. Enumerate all candidate spans up to a length cap. Predict mention scores. Predict antecedent-probability for each span. Cluster greedily. The modern default.... Five standard metrics (MUC, B³, CEAF, BLANC, LEA) because no single metric captures clustering quality. Report the average of the first three as CoNLL F1. State-of-the-art in 2026 on CoNLL-2012: ~83 F1.

## Build It · 动手造

### Step 1: pretrained neural coreference (AllenNLP / spaCy-experimental) · 预训练神经指代消解（AllenNLP / spaCy 实验版）

```python
import spacy
nlp = spacy.load("en_coreference_web_trf")   # experimental model
doc = nlp("Apple announced new products. The company said they would ship soon.")
for cluster in doc._.coref_clusters:
    print(cluster, "->", [m.text for m in cluster])
```

在更长的文档上，你会得到类似这样的结果：

- 簇 1：[Apple, The company, they]
- 簇 2：[new products]

> On a longer document, you get something like:
> - Cluster 1: [Apple, The company, they]
> - Cluster 2: [new products]

### Step 2: rule-based pronoun resolver (teaching) · 规则式代词消解器（教学版）

见 `code/main.py` 的纯标准库实现：

1. 抽取提及：命名实体（首字母大写的 span）、代词（查表）、确定性描述（「the X」）。
2. 对每个代词，看前面 K 个提及并按以下维度打分：
   - 性别/单复数一致（启发式）
   - 近因（越近越好）
   - 句法角色（主语优先）
3. 链接得分最高的先行词。

打不过神经模型。但它展示了搜索空间，以及一个端到端模型必须做出的那些决策。

> See `code/main.py` for a stdlib-only implementation:
> 1. Extract mentions: named entities (capitalized spans), pronouns (dict lookup), definite descriptions ("the X").
> 2. For each pronoun, look at the previous K mentions and score them by: gender/number agreement (heuristic), recency (closer wins), syntactic role (subjects preferred).
> 3. Link the highest-scoring antecedent.
> Not competitive with neural models. But it shows the search space and the decisions an end-to-end model must make.

### Step 3: using LLMs for coreference · 用 LLM 做指代消解

```python
prompt = f"""Text: {text}

List every pronoun and noun phrase that refers to a person or company.
Cluster them by what they refer to. Output JSON:
[{{"entity": "Apple", "mentions": ["Apple", "the company", "it"]}}, ...]
"""
```

要盯住两种失败模式。第一，LLM 会过度合并（把指两个不同人的「him」和「her」并成一簇）。第二，LLM 在长文档里会悄悄丢掉提及。永远用 span 偏移检查来验证。

> Two failure modes to watch. First, LLMs over-merge ("him" and "her" referring to two distinct people). Second, LLMs silently drop mentions in long documents. Always verify with span-offset checks.

### Step 4: evaluation · 评估

标准的 conll-2012 脚本会计算 MUC、B³、CEAF-φ4 并报告平均值。做内部评估时，先在你的标注测试集上算 span 级精确率和召回率，再加上提及链接 F1。

> The standard conll-2012 script computes MUC, B³, CEAF-φ4 and reports the average. For an in-house eval, start with span-level precision and recall on your annotated test set, then add mention-linking F1.

## Pitfalls · 常见的坑

- **单例爆炸（singleton explosion）。** 有些系统把每个提及都报成独立一簇。B³ 对此宽容，MUC 会惩罚它。三个指标都要看。
- **长上下文中的代词。** 文档超过 2,000 tokens 后，性能掉约 15 F1。分块要小心。
- **性别假设。** 写死的性别规则在非二元指称对象、组织、动物身上会崩。用学习到的模型或中性打分。
- **LLM 在长文档上漂移。** 单次 API 调用没法可靠地横跨 50+ 个段落做聚类。用滑窗 + 合并。

> Some systems report every mention as its own cluster. B³ is lenient. MUC punishes this. Always check all three metrics.... Performance drops ~15 F1 on documents over 2,000 tokens. Chunk carefully.... Hard-coded gender rules break on non-binary referents, organizations, animals.... A single API call cannot reliably cluster mentions across 50+ paragraphs. Use sliding-window + merge.

## Use It · 实战用法

2026 年的选型：

| 场景 | 选择 |
|-----------|------|
| 英文、单文档 | `en_coreference_web_trf`（spaCy 实验版）或 AllenNLP 神经 coref |
| 多语言 | 在 OntoNotes 或 Multilingual CoNLL 上训练的 SpanBERT / XLM-R |
| 跨文档事件共指 | 专用端到端模型（2025–26 SOTA） |
| 快速 LLM 基线 | GPT-4o / Claude + 结构化输出的 coref 提示 |
| 生产级对话系统 | 规则式兜底 + 神经主模型 + 关键槽位人工复核 |

2026 年落地的集成模式：先跑 NER，再跑 coref，把 coref 簇合并进 NER 实体。下游任务看到的是每簇一个实体，而不是每提及一个实体。

> The integration pattern that ships in 2026: run NER first, run coref, merge coref clusters into NER entities. Downstream tasks see one entity per cluster, not one entity per mention.

## Ship It · 交付

保存为 `outputs/skill-coref-picker.md`：

```markdown
---
name: coref-picker
description: Pick a coreference approach, evaluation plan, and integration strategy.
version: 1.0.0
phase: 5
lesson: 24
tags: [nlp, coref, information-extraction]
---

Given a use case (single-doc / multi-doc, domain, language), output:

1. Approach. Rule-based / neural span-based / LLM-prompted / hybrid. One-sentence reason.
2. Model. Named checkpoint if neural.
3. Integration. Order of operations: tokenize → NER → coref → downstream task.
4. Evaluation. CoNLL F1 (MUC + B³ + CEAF-φ4 average) on held-out set + manual cluster review on 20 documents.

Refuse LLM-only coref for documents over 2,000 tokens without sliding-window merge. Refuse any pipeline that runs coref without a mention-level precision-recall report. Flag gender-heuristic systems deployed in demographically diverse text.
```

> Save as `outputs/skill-coref-picker.md`.

## Exercises · 练习

1. **简单。** 把 `code/main.py` 里的规则式消解器跑在 5 段手工构造的段落上。对照金标准测提及链接准确率。
2. **中等。** 在一篇新闻文章上用预训练神经 coref 模型。把它的簇跟你自己的手工标注对比。它在哪里出错了？
3. **困难。** 搭一个 coref 增强的 NER 流水线：先 NER，再用 coref 簇合并。在 100 篇文章上测相对纯 NER 的实体覆盖率提升。

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|-----------------------|
| Mention（提及） | 「一次指称」 | 指向某个实体的一段文本（名字、代词、名词短语）。 |
| Antecedent（先行词） | 「it 指的那个东西」 | 被后面的提及共指的那次更早的提及。 |
| Cluster（簇） | 「实体的所有提及」 | 全部指向同一个现实世界实体的提及集合。 |
| Anaphora（回指） | 「向后指称」 | 后面的提及指向前面（「he」→「John」）。 |
| Cataphora（前指） | 「向前指称」 | 前面的提及指向后面（「When he arrived, John...」）。 |
| Bridging（桥接） | 「隐式指称」 | 「I bought a car. The wheels were bad.」（是那辆车的轮子。） |
| CoNLL F1 | 「榜单上的那个数」 | MUC、B³、CEAF-φ4 三个 F1 的平均。 |

## Further Reading · 延伸阅读

- [Jurafsky & Martin, SLP3 Ch. 26 — Coreference Resolution and Entity Linking](https://web.stanford.edu/~jurafsky/slp3/26.pdf) —— 权威教材章节。
- [Lee et al. (2017). End-to-end Neural Coreference Resolution](https://arxiv.org/abs/1707.07045) —— 基于 span 的端到端方法。
- [Joshi et al. (2020). SpanBERT](https://arxiv.org/abs/1907.10529) —— 提升 coref 的预训练。
- [Pradhan et al. (2012). CoNLL-2012 Shared Task](https://aclanthology.org/W12-4501/) —— 那个基准。
- [Hobbs (1978). Resolving Pronoun References](https://www.sciencedirect.com/science/article/pii/0024384178900064) —— 规则式经典。
