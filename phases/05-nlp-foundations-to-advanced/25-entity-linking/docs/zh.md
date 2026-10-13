# Entity Linking & Disambiguation · 实体链接与消歧

> NER 找到了「Paris」。实体链接（entity linking）要决定：法国巴黎？Paris Hilton？德州的 Paris？还是特洛伊王子帕里斯？不做链接，你的知识图谱就永远悬在歧义里。
>
> NER found "Paris." Entity linking decides: Paris, France? Paris Hilton? Paris, Texas? Paris (the Trojan prince)? Without linking, your knowledge graph stays ambiguous.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 06 (NER), Phase 5 · 24 (Coreference Resolution)
**Time:** ~60 minutes

## The Problem · 问题在哪

一个句子：「Jordan beat the press.」你的 NER 把「Jordan」标成 PERSON。很好。但是*哪个* Jordan？

- Michael Jordan（篮球运动员）？
- Michael B. Jordan（演员）？
- Michael I. Jordan（伯克利 ML 教授——没错，这个混淆在 ML 论文里真实存在）？
- Jordan（国家约旦）？
- Jordan（希伯来语名字）？

实体链接（Entity Linking, EL）把每个提及解析到知识库（knowledge base）里的唯一条目：Wikidata、Wikipedia、DBpedia，或你自己的领域 KB。两个子任务：

1. **候选生成（candidate generation）。** 给定「Jordan」，哪些 KB 条目是可能的？
2. **消歧（disambiguation）。** 结合上下文，哪个候选才是对的？

两步都可学习，都有基准。组合流水线十年稳定——变的是消歧器的质量。

> A sentence reads: "Jordan beat the press." Your NER tags "Jordan" as PERSON. Good. But *which* Jordan?... Entity linking (EL) resolves each mention to a unique entry in a knowledge base: Wikidata, Wikipedia, DBpedia, or your domain KB.... Both steps are learnable. Both are benchmarked. The combined pipeline has been stable for a decade — what changes is the quality of the disambiguator.

## The Concept · 概念

![实体链接流水线：提及 → 候选 → 消歧后的实体](../assets/entity-linking.svg)

**候选生成。** 给定提及的表层形式（「Jordan」），在别名索引（alias index）里查候选。Wikipedia 别名词典覆盖大部分命名实体：「JFK」→ John F. Kennedy、Jacqueline Kennedy、JFK 机场、JFK（电影）。典型索引每个提及返回 10-30 个候选。

**消歧：三条路线。**

1. **先验 + 上下文（Milne & Witten, 2008）。** `P(entity | mention) × context-similarity(entity, text)`。好用、快、无需训练。
2. **基于嵌入（ESS / REL / Blink）。** 编码提及 + 上下文。编码每个候选的描述。取余弦最大者。2020-2024 年的默认。
3. **生成式（GENRE, 2021；基于 LLM, 2023+）。** 逐 token 解码实体的规范名称。约束在合法实体名组成的 trie 上，保证输出一定是合法的 KB id。

**端到端 vs 流水线。** 现代模型（ELQ、BLINK、ExtEnD、GENRE）一趟跑完 NER + 候选生成 + 消歧。生产中流水线系统仍然占主流，因为你可以更换组件。

### The two measurements · 两个指标

- **提及召回率（mention recall，考候选生成）。** 正确 KB 条目出现在候选列表里的金标提及比例。整条流水线的下限。
- **消歧准确率 / F1。** 候选正确的前提下，top-1 猜中的频率。

两个都要报。99% 消歧 × 80% 候选召回的系统，是一条 80% 的流水线。

```figure
gx-entity-linking
```

> **Candidate generation.** Given the mention surface form ("Jordan"), look up candidates in an alias index. Wikipedia alias dictionaries cover most named entities... Typical index returns 10-30 candidates per mention.... **Generative (GENRE, 2021; LLM-based, 2023+).** Decode the entity's canonical name token-by-token. Constrained to a trie of valid entity names so output is guaranteed to be a valid KB id.

> **Mention recall (candidate gen).** Fraction of gold mentions where the correct KB entry appears in the candidate list. Floor for the whole pipeline.... Always report both. A system with 99% disambiguation on 80% candidate recall is an 80% pipeline.

## Build It · 动手造

### Step 1: build an alias index from Wikipedia redirects · 用 Wikipedia 重定向建别名索引

```python
alias_to_entities = {
    "jordan": ["Q41421 (Michael Jordan)", "Q810 (Jordan, country)", "Q254110 (Michael B. Jordan)"],
    "paris":  ["Q90 (Paris, France)", "Q663094 (Paris, Texas)", "Q55411 (Paris Hilton)"],
    "apple":  ["Q312 (Apple Inc.)", "Q89 (apple, fruit)"],
}
```

Wikipedia 别名数据：约 1,800 万对（alias, entity）。从 Wikidata dumps 下载。存成倒排索引。

> Wikipedia alias data: ~18M (alias, entity) pairs. Download from Wikidata dumps. Store as inverted index.

### Step 2: context-based disambiguation · 基于上下文的消歧

```python
def disambiguate(mention, context, alias_index, entity_desc):
    candidates = alias_index.get(mention.lower(), [])
    if not candidates:
        return None, 0.0
    context_words = set(tokenize(context))
    best, best_score = None, -1
    for entity_id in candidates:
        desc_words = set(tokenize(entity_desc[entity_id]))
        union = len(context_words | desc_words)
        score = len(context_words & desc_words) / union if union else 0.0
        if score > best_score:
            best, best_score = entity_id, score
    return best, best_score
```

Jaccard 重叠是个玩具。换成嵌入余弦相似度（Transformer 版本见 `code/main.py` 的 step-2）。

> The Jaccard overlap is a toy. Replace with cosine similarity on embeddings (see `code/main.py` step-2 for the transformer version).

### Step 3: embedding-based (BLINK-style) · 基于嵌入（BLINK 风格）

```python
from sentence_transformers import SentenceTransformer
encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def embed_mention(text, mention_span):
    start, end = mention_span
    marked = f"{text[:start]} [MENTION] {text[start:end]} [/MENTION] {text[end:]}"
    return encoder.encode([marked], normalize_embeddings=True)[0]

def embed_entity(entity_id, description):
    return encoder.encode([f"{entity_id}: {description}"], normalize_embeddings=True)[0]
```

索引时，把每个 KB 实体嵌入一次。查询时，把提及 + 上下文嵌入一次，对候选池做点积，取最大。

> At index time, embed every KB entity once. At query time, embed the mention + context once, dot-product against the candidate pool, pick max.

### Step 4: generative entity linking (concept) · 生成式实体链接（概念）

GENRE 逐字符解码实体的 Wikipedia 标题。约束解码（见第 20 课）保证只能输出合法标题。与 KB 支撑的 trie 紧密集成。现代后继者是 REL-GEN 和带结构化输出的 LLM 提示 EL。

```python
prompt = f"""Text: {text}
Mention: {mention}
List the best Wikipedia title for this mention.
Respond with JSON: {{"title": "..."}}"""
```

再结合一个白名单（Outlines 的 `choice`），这就是 2026 年最容易落地的 EL 流水线。

> GENRE decodes the entity's Wikipedia title character-by-character. Constrained decoding (see lesson 20) ensures only valid titles can be output. Tight integration with a KB-backed trie. The modern descendant is REL-GEN and LLM-prompted EL with structured output.
> Combined with a whitelist (Outlines `choice`), this is the simplest EL pipeline to ship in 2026.

### Step 5: evaluate on AIDA-CoNLL · 在 AIDA-CoNLL 上评估

AIDA-CoNLL 是标准 EL 基准：1,393 篇 Reuters 文章、3.4 万个提及、Wikipedia 实体。报告 in-KB 准确率（`P@1`）和 out-of-KB 的 NIL 检出率。

> AIDA-CoNLL is the standard EL benchmark: 1,393 Reuters articles, 34k mentions, Wikipedia entities. Report in-KB accuracy (`P@1`) and out-of-KB NIL-detection rate.

## Pitfalls · 常见的坑

- **NIL 处理。** 有些提及不在 KB 里（新出现的实体、冷门人物）。系统必须预测 NIL，而不是瞎猜一个实体。单独计量。
- **提及边界错误。** 上游 NER 漏了部分 span（「Bank of America」只标出「Bank」）。EL 召回率随之下跌。
- **流行度偏差（popularity bias）。** 训练出的系统过度预测高频实体。ML 论文里提到「Michael I. Jordan」，常常被链到打篮球的那个 Jordan。
- **跨语言 EL。** 把中文文本里的提及映射到英文 Wikipedia 实体。需要多语言编码器或一个翻译步骤。
- **KB 过期。** 新公司、新事件、新人物不在去年的 Wikipedia dump 里。生产流水线需要刷新机制。

> Some mentions are not in the KB (emerging entities, obscure people). Systems must predict NIL instead of guessing the wrong entity. Measured separately.... Trained systems over-predict frequent entities. A mention of "Michael I. Jordan" on an ML paper often links to basketball Jordan.... New companies, events, people are not in last year's Wikipedia dump. Production pipelines need a refresh loop.

## Use It · 实战用法

2026 年的选型：

| 场景 | 选择 |
|-----------|------|
| 通用英文 + Wikipedia | BLINK 或 REL |
| 跨语言、KB = Wikipedia | mGENRE |
| LLM 友好、每天提及量少 | 提示 Claude/GPT-4：候选列表 + 约束 JSON |
| 领域 KB（医疗、法律） | 定制 BERT + KB 感知检索 + 在领域 AIDA 风格数据集上微调 |
| 极低延迟 | 只用精确匹配先验（Milne-Witten 基线） |
| 研究 SOTA | GENRE / ExtEnD / 生成式 LLM-EL |

2026 年落地的生产模式：NER → coref → 对每个提及做 EL → 把簇收敛为每簇一个规范实体。输出：文档中每个实体一个 KB id，而不是每个提及一个。

> Production pattern that ships in 2026: NER → coref → EL on each mention → collapse clusters to one canonical entity per cluster. Output: one KB id per entity in the document, not one per mention.

## Ship It · 交付

保存为 `outputs/skill-entity-linker.md`：

```markdown
---
name: entity-linker
description: Design an entity linking pipeline — KB, candidate generator, disambiguator, evaluation.
version: 1.0.0
phase: 5
lesson: 25
tags: [nlp, entity-linking, knowledge-graph]
---

Given a use case (domain KB, language, volume, latency budget), output:

1. Knowledge base. Wikidata / Wikipedia / custom KB. Version date. Refresh cadence.
2. Candidate generator. Alias-index, embedding, or hybrid. Target mention recall @ K.
3. Disambiguator. Prior + context, embedding-based, generative, or LLM-prompted.
4. NIL strategy. Threshold on top score, classifier, or explicit NIL candidate.
5. Evaluation. Mention recall @ 30, top-1 accuracy, NIL-detection F1 on held-out set.

Refuse any EL pipeline without a mention-recall baseline (you cannot evaluate a disambiguator without knowing candidate gen surfaced the right entity). Refuse any pipeline using LLM-prompted EL without constrained output to valid KB ids. Flag systems where popularity bias affects minority entities (e.g. name-clashes) without domain fine-tuning.
```

> Save as `outputs/skill-entity-linker.md`.

## Exercises · 练习

1. **简单。** 在 `code/main.py` 里实现先验+上下文消歧器，跑在 10 个歧义提及上（Paris、Jordan、Apple）。手工标注正确实体。测准确率。
2. **中等。** 用一个句子级 Transformer 编码 50 个歧义提及。给每个候选的描述做嵌入。比较基于嵌入的消歧与 Jaccard 上下文重叠。
3. **困难。** 建一个 1k 实体的领域 KB（比如你公司的员工 + 产品）。端到端实现 NER + EL。在 100 句留出句子上测精确率和召回率。

## Key Terms · 术语表

| 术语 | 人们常说 | 实际含义 |
|------|-----------------|-----------------------|
| Entity linking（实体链接，EL） | 「链到 Wikipedia」 | 把一个提及映射到唯一的 KB 条目。 |
| Candidate generation（候选生成） | 「它可能是谁？」 | 为一个提及返回一小串可能的 KB 条目。 |
| Disambiguation（消歧） | 「挑出对的那个」 | 用上下文给候选打分，选出赢家。 |
| Alias index（别名索引） | 「查找表」 | 从表层形式 → 候选实体的映射。 |
| NIL | 「KB 里没有」 | 显式预测没有任何 KB 条目匹配。 |
| KB | 「知识库」 | Wikidata、Wikipedia、DBpedia，或你自己的领域 KB。 |
| AIDA-CoNLL | 「那个基准」 | 1,393 篇带金标实体链接的 Reuters 文章。 |

## Further Reading · 延伸阅读

- [Milne, Witten (2008). Learning to Link with Wikipedia](https://researchcommons.waikato.ac.nz/entities/publication/b9a0b520-abc5-47c5-a86a-da6c579893ab) —— 奠基性的先验+上下文方法。
- [Wu et al. (2020). Zero-shot Entity Linking with Dense Entity Retrieval (BLINK)](https://arxiv.org/abs/1911.03814) —— 基于嵌入的主力方案。
- [De Cao et al. (2021). Autoregressive Entity Retrieval (GENRE)](https://arxiv.org/abs/2010.00904) —— 带约束解码的生成式 EL。
- [Hoffart et al. (2011). Robust Disambiguation of Named Entities in Text (AIDA)](https://www.aclweb.org/anthology/D11-1072.pdf) —— 基准论文。
- [REL: An Entity Linker Standing on the Shoulders of Giants (2020)](https://arxiv.org/abs/2006.01969) —— 开源生产级方案。
