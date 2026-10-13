# Relation Extraction & Knowledge Graph Construction · 关系抽取与知识图谱构建

> NER 找出了实体，实体链接把它们锚定到知识库，关系抽取（relation extraction）负责找出实体之间的边。知识图谱（knowledge graph）就是节点、边以及它们来源（provenance）的总和。
>
> NER found the entities. Entity linking anchored them. Relation extraction finds the edges between them. A knowledge graph is the sum of nodes, edges, and their provenance.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 06 (NER), Phase 5 · 25 (Entity Linking)
**Time:** ~60 minutes

## The Problem · 问题在哪

一位分析师读到："Tim Cook 在 2011 年成为 Apple 的 CEO。" 这句话里藏着四个事实：

- `(Tim Cook, role, CEO)`
- `(Tim Cook, employer, Apple)`
- `(Tim Cook, start_date, 2011)`
- `(Apple, type, Organization)`

关系抽取（Relation Extraction，简称 RE）把自由文本变成结构化三元组（triple）`(subject, relation, object)`。在整个语料库上聚合，你就得到了一个知识图谱。聚合之后再查询，你就有了支撑 RAG、数据分析或合规审计的推理底座。

2026 年的麻烦在于：LLM 抽取关系非常起劲——起劲得过了头。它们会幻觉出源文本并不支持的三元组。没有来源追溯（provenance），你分不清真实的三元组和貌似合理的编造。2026 年的答案是 AEVS 式的「锚定-校验」流水线（anchor-and-verify pipeline）。

> An analyst reads: "Tim Cook became CEO of Apple in 2011." Four facts:
> Relation Extraction (RE) turns free text into structured triples `(subject, relation, object)`. Aggregate across a corpus and you have a knowledge graph. Aggregate and query and you have a reasoning substrate for RAG, analytics, or compliance audits.
> The 2026 problem: LLMs extract relations enthusiastically. Too enthusiastically. They hallucinate triples that the source text does not support. Without provenance, you cannot tell real triples from plausible fiction. The 2026 answer is AEVS-style anchor-and-verify pipelines.

## The Concept · 概念

![文本 → 三元组 → 知识图谱](../assets/relation-extraction.svg)

**三元组形式。** `(subject_entity, relation_type, object_entity)`。关系取自封闭本体（closed ontology，如 Wikidata 属性、FIBO、UMLS），或开放集合（OpenIE 式，什么都能当关系）。

**三种抽取路线。**

1. **规则 / 模式。** Hearst 模式："X such as Y" → `(Y, isA, X)`，再加上手工正则。脆弱、精确、可解释。
2. **监督分类器。** 给定句子中的一对实体提及（entity mention），从固定关系集合里预测关系。训练数据用 TACRED、ACE、KBP。2015–2022 年的标准做法。
3. **生成式 LLM。** 提示模型直接吐出三元组。开箱即用，但必须有来源校验，否则会幻觉出看起来像模像样的垃圾。

**AEVS（Anchor-Extraction-Verification-Supplement，2026）。** 当前的幻觉抑制框架：

- **锚定（Anchor）。** 用精确位置标出每个实体 span 和关系短语 span。
- **抽取（Extract）。** 生成挂接到锚定 span 的三元组。
- **校验（Verify）。** 把每个三元组元素回对到源文本；拒绝一切无支撑的内容。
- **补充（Supplement）。** 一轮覆盖性检查，确保锚定过的 span 没有遗漏。

幻觉大幅下降。算力开销更大，但可审计。

**开放 vs 封闭的取舍。**

- **封闭本体。** 固定的属性清单（比如 Wikidata 的 11,000+ 个属性）。可预测、可查询、难编造。
- **开放 IE（Open IE）。** 任何动词短语都能当关系。召回高、精度低、查询起来一团糟。

生产级知识图谱通常混着用：先开放 IE 做发现，再把关系规范化（canonicalize）到封闭本体上，最后才并进主图。

```figure
relation-triples
```

> **Triple form.** `(subject_entity, relation_type, object_entity)`. Relations come from a closed ontology (Wikidata properties, FIBO, UMLS) or an open set (OpenIE-style, anything goes). ... **Verify.** Match each triple element back to the source text; reject anything unsupported. ... Hallucinations drop sharply. Requires more compute but is auditable. ... Production KGs usually mix: open IE for discovery, then canonicalize relations onto a closed ontology before merging into the main graph.

## Build It · 动手造

### Step 1: pattern-based extraction · 第 1 步：基于模式的抽取

```python
PATTERNS = [
    (r"(?P<s>[A-Z]\w+) (?:is|was) (?:a|an|the) (?P<o>[A-Z]?\w+)", "isA"),
    (r"(?P<s>[A-Z]\w+) (?:is|was) born in (?P<o>\w+)", "bornIn"),
    (r"(?P<s>[A-Z]\w+) works? (?:at|for) (?P<o>[A-Z]\w+)", "worksAt"),
    (r"(?P<s>[A-Z]\w+) founded (?P<o>[A-Z]\w+)", "founded"),
]
```

完整的教学版抽取器见 `code/main.py`。Hearst 模式至今仍在很多领域流水线里服役，就因为它们可调试。

> See `code/main.py` for the full toy extractor. Hearst patterns still ship in domain-specific pipelines because they are debuggable.

### Step 2: supervised relation classification · 第 2 步：监督式关系分类

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification

tok = AutoTokenizer.from_pretrained("Babelscape/rebel-large")
model = AutoModelForSequenceClassification.from_pretrained("Babelscape/rebel-large")

text = "Tim Cook was born in Alabama. He later became CEO of Apple."
encoded = tok(text, return_tensors="pt", truncation=True)
output = model.generate(**encoded, max_length=200)
triples = tok.batch_decode(output, skip_special_tokens=False)
```

REBEL 是一个 seq2seq 关系抽取器：文本进、三元组出，而且直接就是 Wikidata 属性 id。它在远程监督（distant supervision）数据上微调过，是标准的开放权重基线。

> REBEL is a seq2seq relation extractor: text in, triples out, already in Wikidata property ids. Fine-tuned on distant-supervision data. Standard open-weights baseline.

### Step 3: LLM-prompted extraction with anchoring · 第 3 步：带锚定的 LLM 提示抽取

```python
prompt = f"""Extract (subject, relation, object) triples from the text.
For each triple, include the exact character span in the source text.

Text: {text}

Output JSON:
[{{"subject": {{"text": "...", "span": [start, end]}},
   "relation": "...",
   "object": {{"text": "...", "span": [start, end]}}}}, ...]

Only include triples fully supported by the text. No inference beyond what is stated.
"""
```

返回的每一个 span 都要对照源文本校验。凡是 `text[start:end] != triple_entity` 的一律拒绝。这就是 AEVS「校验」步骤的最小形态。

> Verify every returned span against the source. Reject anything where `text[start:end] != triple_entity`. This is the AEVS "verify" step in its minimal form.

### Step 4: canonicalize onto a closed ontology · 第 4 步：规范化到封闭本体

```python
RELATION_MAP = {
    "is the CEO of": "P169",       # "chief executive officer"
    "was born in":   "P19",         # "place of birth"
    "founded":        "P112",       # "founded by" (inverted subject/object)
    "works at":       "P108",       # "employer"
}


def canonicalize(relation):
    rel_low = relation.lower().strip()
    if rel_low in RELATION_MAP:
        return RELATION_MAP[rel_low]
    return None   # drop unmapped open relations or route to manual review
```

规范化（canonicalization）经常占掉整个工程量的 60-80%。给它留足预算。

> Canonicalization is often 60-80% of the engineering work. Budget for it.

### Step 5: build a small graph and query · 第 5 步：搭一个小图并查询

```python
triples = extract(text)
graph = {}
for s, r, o in triples:
    graph.setdefault(s, []).append((r, o))


def neighbors(node, relation=None):
    return [(r, o) for r, o in graph.get(node, []) if relation is None or r == relation]


print(neighbors("Tim Cook", relation="P108"))    # -> [(P108, Apple)]
```

这就是所有「在 KG 上做 RAG」系统的原子操作。要规模化，换成 RDF 三元组库（Blazegraph、Virtuoso）、属性图（Neo4j）或向量增强的图存储。

> This is the atom of every RAG-over-KG system. Scale it with RDF triple stores (Blazegraph, Virtuoso), property graphs (Neo4j), or vector-augmented graph stores.

## Pitfalls · 常见的坑

- **先共指，后关系抽取。** "He founded Apple" —— RE 得先知道 "he" 是谁。先跑共指消解（coreference，第 24 课）。
- **实体规范化。** "Apple Inc" 和 "Apple" 必须归并到同一个节点。先做实体链接（entity linking，第 25 课）。
- **幻觉三元组。** LLM 会吐出文本不支撑的三元组。强制执行 span 校验。
- **关系规范化漂移。** 开放 IE 的关系表述不一致（"was born in"、"came from"、"is a native of"）。要么归并到规范 id，要么这个图就没法查询。
- **时序错误。** "Tim Cook is CEO of Apple" —— 现在为真，2005 年为假。很多关系是有时间边界的。使用限定符（qualifier，Wikidata 的 `P580` 开始时间、`P582` 结束时间）。
- **领域不匹配。** REBEL 是在 Wikipedia 上训练的。法律、医疗、科学文本往往需要领域微调过的 RE 模型。

> **Coreference before RE.** "He founded Apple" — RE needs to know who "he" is. Run coref first (lesson 24). ... **Hallucinated triples.** LLMs emit triples the text does not support. Enforce span verification. ... **Temporal errors.** "Tim Cook is CEO of Apple" — true now, false in 2005. Many relations are time-bounded. Use qualifiers (`P580` start time, `P582` end time in Wikidata).

## Use It · 实战用法

2026 年的选型表：

| 场景 | 选择 |
|-----------|------|
| 快速上线、通用领域 | REBEL 或 LlamaPred + Wikidata 规范化 |
| 领域特定（生物医学、法律） | SciREX 式领域微调 + 自定义本体 |
| LLM 提示抽取、输出要审计 | AEVS 流水线：anchor → extract → verify → supplement |
| 高吞吐新闻信息抽取 | 模式 + 监督模型的混合 |
| 从零构建知识图谱 | 开放 IE + 一轮人工规范化 |
| 时序知识图谱 | 带限定符抽取（开始/结束时间、时间点） |

集成套路：NER → 共指消解 → 实体链接 → 关系抽取 → 本体映射 → 入图。每一级都是一个潜在的质量闸门。

> The integration pattern: NER → coref → entity linking → relation extraction → ontology mapping → graph load. Every stage is a potential quality gate.

## Ship It · 交付

保存为 `outputs/skill-re-designer.md`：

```markdown
---
name: re-designer
description: Design a relation extraction pipeline with provenance and canonicalization.
version: 1.0.0
phase: 5
lesson: 26
tags: [nlp, relation-extraction, knowledge-graph]
---

Given a corpus (domain, language, volume) and downstream use (KG-RAG, analytics, compliance), output:

1. Extractor. Pattern-based / supervised / LLM / AEVS hybrid. Reason tied to precision vs recall target.
2. Ontology. Closed property list (Wikidata / domain) or open IE with canonicalization pass.
3. Provenance. Every triple carries source char-span + doc id. Non-negotiable for audit.
4. Merge strategy. Canonical entity id + relation id + temporal qualifiers; dedup policy.
5. Evaluation. Precision / recall on 200 hand-labelled triples + hallucination-rate on LLM-extracted sample.

Refuse any LLM-based RE pipeline without span verification (source provenance). Refuse open-IE output flowing into a production graph without canonicalization. Flag pipelines with no temporal qualifier on time-bounded relations (employer, spouse, position).
```

> Save as `outputs/skill-re-designer.md`:

## Exercises · 练习

1. **简单。** 用 `code/main.py` 的模式抽取器跑 5 条新闻句子，人工核对精度。
2. **中等。** 在同样的句子上用 REBEL（或一个小 LLM），对比三元组：哪个抽取器精度更高？召回更高？
3. **困难。** 搭出 AEVS 流水线：LLM 抽取 + 对照源文本校验 span。在 50 条 Wikipedia 风格的句子上测校验前后的幻觉率。

> 1. **Easy.** Run the pattern extractor in `code/main.py` on 5 news-article sentences. Hand-check precision.
> 2. **Medium.** Use REBEL (or a small LLM) on the same sentences. Compare triples. Which extractor has higher precision? Higher recall?
> 3. **Hard.** Build the AEVS pipeline: extract with LLM + verify spans against source. Measure hallucination rate before vs after the verify step on 50 Wikipedia-style sentences.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Triple（三元组） | 主语-关系-宾语 | `(s, r, o)` 元组，知识图谱的原子单元。 |
| Open IE（开放信息抽取） | 什么都能抽 | 开放词表的关系短语；召回高、精度低。 |
| Closed ontology（封闭本体） | 固定模式 | 有界的关系类型集合（Wikidata、UMLS、FIBO）。 |
| Canonicalization（规范化） | 一切归一 | 把表层名称 / 关系映射到规范 id。 |
| AEVS | 有据可查的抽取 | Anchor-Extraction-Verification-Supplement 流水线（2026）。 |
| Provenance（来源追溯） | 事实来源链接 | 每个三元组都带 doc id + 字符 span 指向它的出处。 |
| Distant supervision（远程监督） | 便宜的标签 | 用现有 KG 对齐文本来制造训练数据。 |

## Further Reading · 延伸阅读

- [Mintz et al. (2009). Distant supervision for relation extraction without labeled data](https://www.aclweb.org/anthology/P09-1113.pdf) —— 远程监督的开山论文。
- [Huguet Cabot, Navigli (2021). REBEL: Relation Extraction By End-to-end Language generation](https://aclanthology.org/2021.findings-emnlp.204.pdf) —— seq2seq 关系抽取的主力模型。
- [Wadden et al. (2019). Entity, Relation, and Event Extraction with Contextualized Span Representations (DyGIE++)](https://arxiv.org/abs/1909.03546) —— 联合信息抽取。
- [AEVS — Anchor-Extraction-Verification-Supplement framework](https://www.mdpi.com/2073-431X/15/3/178) —— 2026 年的幻觉抑制设计。
- [Wikidata SPARQL tutorial](https://www.wikidata.org/wiki/Wikidata:SPARQL_tutorial) —— 规范的图查询入门。
