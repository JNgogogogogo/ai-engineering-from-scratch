# Question Answering Systems · 问答系统

> 三种系统塑造了现代 QA。抽取式找到答案片段。检索增强把它们锚定在文档上。生成式直接产出答案。每个现代 AI 助手都是三者的混合体。
> Three systems shaped modern QA. Extractive found spans. Retrieval-augmented grounded them in documents. Generative produced answers. Every modern AI assistant is a mix of the three.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 11 (Machine Translation), Phase 5 · 10 (Attention Mechanism)
**Time:** ~75 minutes

## The Problem · 问题在哪

用户输入 "When did the first iPhone launch?"，期望得到 "June 29, 2007。" 而不是 "Apple 的历史悠久而多姿多彩。"，也不是孤零零、没有任何句子支撑的 "2007"。要的是一个直接、有依据、正确的答案。

过去十年主导 QA 的三种架构：

- **抽取式 QA（Extractive QA）。** 给定一个问题和一段已知包含答案的段落，找出答案片段在段落中的起止下标。SQuAD 是公认基准。
- **开放域 QA（Open-domain QA）。** 段落不给。先检索相关段落，再从中抽取或生成答案。这是今天所有 RAG 管线的基石。
- **生成式 / 闭卷 QA（Generative / Closed-book QA）。** 大语言模型凭参数记忆作答。无检索。推理最快，事实最不可靠。

2026 年的趋势是混合式：检索出最好的几段，然后提示生成模型基于这些段落作答。这就是 RAG；第 14 课深入讲检索那一半，本课构建 QA 那一半。

> A user types "When did the first iPhone launch?" and expects "June 29, 2007." Not "Apple's history is long and varied." Not "2007" sitting in isolation with no sentence. A direct, grounded, correct answer. ... **Extractive QA.** Given a question and a passage that is known to contain the answer, find the start and end indices of the answer span in the passage. SQuAD is the canonical benchmark. ... **Open-domain QA.** The passage is not given. Retrieve the relevant passage first, then extract or generate an answer. This is the bedrock of every RAG pipeline today. ... The trend in 2026 is hybrid: retrieve the best few passages, then prompt a generative model to answer grounded in those passages.

## The Concept · 概念

![QA 架构：抽取式、检索增强、生成式](../assets/qa.svg)

**抽取式。** 用 Transformer（BERT 家族）把问题和段落一起编码。训练两个头，预测答案的起止 token 下标。损失是合法位置上的交叉熵。输出是段落中的一个片段。从构造上就不会幻觉，也从构造上就无法回答段落答不了的问题。

**检索增强（RAG）。** 两个阶段。第一，检索器（retriever）从语料中找出前 `k` 个段落。第二，阅读器（reader，抽取式或生成式）用这些段落产出答案。检索器-阅读器的拆分让两者可以独立训练、独立评估。现代 RAG 常在两者之间再加一个重排器（reranker）。

**生成式。** 仅解码器（decoder-only）LLM（GPT、Claude、Llama）凭学到的权重作答。没有检索步骤。常见知识上表现出色，罕见或新近的事实上灾难频出。幻觉率与事实在预训练数据中的出现频率呈负相关。

```figure
qa-span
```

> **Extractive.** Encode question and passage together with a transformer (BERT family). Train two heads that predict start and end token indices of the answer. Loss is cross-entropy over valid positions. Output is a span from the passage. Never hallucinates (by construction), never handles questions the passage cannot answer (by construction).
> **Retrieval-augmented (RAG).** Two stages. First, a retriever finds the top-`k` passages from a corpus. Second, a reader (extractive or generative) produces the answer using those passages. The retriever-reader split lets each be trained and evaluated independently. Modern RAG often adds a reranker between them.
> **Generative.** A decoder-only LLM (GPT, Claude, Llama) answers from learned weights. No retrieval step. Excellent on common knowledge, catastrophic on rare or recent facts. The hallucination rate is inversely correlated with fact frequency in the pretraining data.

## Build It · 动手造

### Step 1: extractive QA with a pretrained model · 用预训练模型做抽取式 QA

```python
from transformers import pipeline

qa = pipeline("question-answering", model="deepset/roberta-base-squad2")

passage = (
    "Apple Inc. released the first iPhone on June 29, 2007. "
    "The device was announced by Steve Jobs at Macworld in January 2007."
)
question = "When was the first iPhone released?"

answer = qa(question=question, context=passage)
print(answer)
```

```python
{'score': 0.98, 'start': 57, 'end': 70, 'answer': 'June 29, 2007'}
```

`deepset/roberta-base-squad2` 在 SQuAD 2.0 上训练，该数据集包含无法回答的问题。默认情况下，`question-answering` 管线返回得分最高的片段——即使模型的空答案分数（null score）胜出，它也*不会*自动返回空答案。要得到显式的「无答案」行为，给管线调用传 `handle_impossible_answer=True`：只有当空答案分数超过所有片段分数时，管线才会返回空答案。无论哪种方式，都要检查 `score` 字段。

> `deepset/roberta-base-squad2` is trained on SQuAD 2.0, which includes unanswerable questions. By default, the `question-answering` pipeline returns the highest-scoring span even when the model's null score wins — it does *not* automatically return an empty answer. To get explicit "no answer" behavior, pass `handle_impossible_answer=True` to the pipeline call: the pipeline then returns an empty answer only when the null score exceeds every span score. Always check the `score` field either way.

### Step 2: a retrieval-augmented pipeline (sketch) · 检索增强管线（草图）

```python
from sentence_transformers import SentenceTransformer
import numpy as np

encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

corpus = [
    "Apple Inc. released the first iPhone on June 29, 2007.",
    "Macworld 2007 featured the iPhone announcement by Steve Jobs.",
    "Android launched in 2008 as Google's mobile operating system.",
    "The first iPod was released in 2001.",
]
corpus_embeddings = encoder.encode(corpus, normalize_embeddings=True)


def retrieve(question, top_k=2):
    q_emb = encoder.encode([question], normalize_embeddings=True)
    sims = (corpus_embeddings @ q_emb.T).squeeze()
    order = np.argsort(-sims)[:top_k]
    return [corpus[i] for i in order]


def answer(question):
    passages = retrieve(question, top_k=2)
    combined = " ".join(passages)
    return qa(question=question, context=combined)


print(answer("When was the first iPhone released?"))
```

两阶段管线。稠密检索器（Sentence-BERT）按语义相似度找出相关段落。抽取式阅读器（RoBERTa-SQuAD）从合并后的头部段落中抽出答案片段。小语料上能用。百万文档级的语料请用 FAISS 或向量数据库。

> Two-stage pipeline. Dense retriever (Sentence-BERT) finds relevant passages by semantic similarity. Extractive reader (RoBERTa-SQuAD) pulls the answer span from the combined top passages. Works on small corpora. For a million-document corpus, use FAISS or a vector database.

### Step 3: generative with RAG · 用 RAG 做生成式问答

```python
def rag_generate(question, llm):
    passages = retrieve(question, top_k=3)
    prompt = f"""Context:
{chr(10).join('- ' + p for p in passages)}

Question: {question}

Answer using only the context above. If the context does not contain the answer, say "I don't know."
"""
    return llm(prompt)
```

提示词的模式很重要。明确告诉模型「基于上下文作答，上下文不够就回答 I don't know」，与朴素提示相比能把幻觉率砍掉 40-60%。更精细的模式会加入引用、置信度分数和结构化抽取。

> The prompt pattern matters. Explicitly telling the model to ground in the context and return "I don't know" when the context is insufficient cuts hallucination rates by 40-60% compared to naive prompting. More elaborate patterns add citations, confidence scores, and structured extraction.

### Step 4: evaluation that reflects the real world · 反映真实世界的评估

SQuAD 使用 **Exact Match（EM，精确匹配）** 和 **token 级 F1**。EM 是归一化后（转小写、去标点、去冠词）的严格匹配——预测要么完全一致得满分，要么得 0。F1 按预测与参考之间的 token 重叠计算，给部分分。两者都低估意译："June 29, 2007" 对 "June 29th, 2007" 通常 EM 得 0（序数词破坏了归一化），但靠重叠 token 仍能拿到可观的 F1。

生产环境 QA 要看：

- **答案准确率**（LLM 评判或人工评判，因为自动指标捕捉不到语义等价）。
- **引用准确率。** 被引用的段落真的支撑答案吗？把生成的引用与检索到的段落做字符串匹配即可自动检查，几乎不费事。
- **拒答校准（Refusal calibration）。** 当检索到的段落里没有答案时，系统能否正确说「我不知道」？度量虚假自信率。
- **检索召回率。** 评估阅读器之前，先度量检索器是否把正确的段落送进了前 `k`。阅读器救不了缺失的段落。

> SQuAD uses **Exact Match (EM)** and **token-level F1**. EM is a strict match after normalization (lowercase, strip punctuation, remove articles) — either the prediction matches exactly or it scores 0. F1 is computed over token overlap between prediction and reference and gives partial credit. ... For production QA: ... **Citation accuracy.** Does the cited passage actually support the answer? Trivial to check automatically with string match between generated citations and retrieved passages. ... **Retrieval recall.** Before evaluating the reader, measure whether the retriever gets the right passage into the top-`k`. A reader cannot fix a missing passage.

### RAGAS: the 2026 production eval framework · RAGAS：2026 年的生产级评估框架

`RAGAS` 专为 RAG 系统打造，是 2026 年的上线默认。它无需金标准参考即可给四个维度打分：

- **忠实度（Faithfulness）。** 答案中的每个论断都来自检索到的上下文吗？用基于 NLI 的蕴含来度量。这是你的首要幻觉指标。
- **答案相关性（Answer relevance）。** 答案回应了问题吗？度量方法是：从答案生成假设性问题，再与真实问题比较。
- **上下文精确率（Context precision）。** 检索到的 chunk 里，真正相关的占多少？低精确率 = 提示词里有噪声。
- **上下文召回率（Context recall）。** 检索到的集合包含全部所需信息吗？低召回 = 阅读器无从成功。

无参考评分让你能在真实生产流量上做评估，不需要人工整理的金标准答案。开放式问题上精确匹配指标失灵，可在其上再叠一层 LLM 当裁判。

`pip install ragas`。接上你的检索器 + 阅读器。每个查询拿到四个标量。对回归告警。

> `RAGAS` is purpose-built for RAG systems and is the shipping default in 2026. It scores four dimensions without requiring gold references: ... **Faithfulness.** Does each claim in the answer come from the retrieved context? Measured by NLI-based entailment. Your primary hallucination metric. ... Reference-free scoring lets you evaluate on live production traffic without curated gold answers. Layer LLM-as-judge on top for open-ended questions where exact-match metrics are useless.
> `pip install ragas`. Plug your retriever + reader. Get four scalars per query. Alert on regressions.

## Use It · 实战用法

2026 年的技术栈。

| 使用场景 | 推荐 |
|---------|-------------|
| 给定段落，找答案片段 | `deepset/roberta-base-squad2` |
| 固定语料之上、闭卷不可接受 | RAG：稠密检索器 + LLM 阅读器 |
| 文档库上的实时问答 | RAG + 混合检索（BM25 + 稠密）+ 重排器（第 14 课） |
| 会话式 QA（追问） | 带对话历史的 LLM + 每轮挂 RAG |
| 高事实性、受监管领域 | 在权威语料上做抽取式；绝不要只用生成式 |

抽取式 QA 在 2026 年显得不合时宜，因为带 LLM 的 RAG 能覆盖更多场景。但在要求逐字引用的场合，它仍然在上线：法律检索、监管合规、审计工具。

> Extractive QA is unfashionable in 2026 because RAG with LLMs handles more cases. It still ships in contexts where literal quotation is required: legal research, regulatory compliance, audit tools.

## Ship It · 交付

保存为 `outputs/skill-qa-architect.md`：

```markdown
---
name: qa-architect
description: Choose QA architecture, retrieval strategy, and evaluation plan.
version: 1.0.0
phase: 5
lesson: 13
tags: [nlp, qa, rag]
---

Given requirements (corpus size, question type, factuality constraint, latency budget), output:

1. Architecture. Extractive, RAG with extractive reader, RAG with generative reader, or closed-book LLM. One-sentence reason.
2. Retriever. None, BM25, dense (name the encoder), or hybrid.
3. Reader. SQuAD-tuned model, LLM by name, or "domain-fine-tuned DistilBERT."
4. Evaluation. EM + F1 for extractive benchmarks; answer accuracy + citation accuracy + refusal calibration for production. Name what you are measuring and how you are measuring it.

Refuse closed-book LLM answers for regulatory or compliance-sensitive questions. Refuse any QA system without a retrieval-recall baseline (you cannot evaluate the reader without knowing the retriever surfaced the right passage). Flag questions that require multi-hop reasoning as needing specialized multi-hop retrievers like HotpotQA-trained systems.
```

> Save as `outputs/skill-qa-architect.md`:

## Exercises · 练习

1. **简单。** 在 10 个 Wikipedia 段落上搭好上面的 SQuAD 抽取式管线。手工写 10 个问题。度量答案正确的频率。段落和问题都干净的话，你应该看到 7-9 个正确。
2. **中等。** 加一个拒答分类器。当最高检索分数低于某个阈值（比如 0.3 余弦）时，返回「我不知道」而不是调用阅读器。在留出集上调阈值。
3. **困难。** 在你自己选的 10,000 文档语料上搭一条 RAG 管线。实现混合检索（BM25 + 稠密）加 RRF 融合（见第 14 课）。度量开启与关闭混合步骤后的答案准确率。记录哪些类型的问题受益最大。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| Extractive QA（抽取式 QA） | 找答案片段 | 在给定段落内预测答案的起止下标。 |
| Open-domain QA（开放域 QA） | 在语料上问答 | 不给段落；必须先检索再作答。 |
| RAG | 先检索再生成 | 检索增强生成。检索器 + 阅读器管线。 |
| SQuAD | 公认基准 | Stanford Question Answering Dataset。EM + F1 指标。 |
| Hallucination（幻觉） | 编造的答案 | 检索到的上下文不支撑的阅读器输出。 |
| Refusal calibration（拒答校准） | 知道何时闭嘴 | 无法回答时系统正确说出「我不知道」。 |

## Further Reading · 延伸阅读

- [Rajpurkar et al. (2016). SQuAD: 100,000+ Questions for Machine Comprehension of Text](https://arxiv.org/abs/1606.05250) —— 基准论文。
- [Karpukhin et al. (2020). Dense Passage Retrieval for Open-Domain QA](https://arxiv.org/abs/2004.04906) —— DPR，QA 公认的稠密检索器。
- [Lewis et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401) —— 给 RAG 命名的那篇论文。
- [Gao et al. (2023). Retrieval-Augmented Generation for Large Language Models: A Survey](https://arxiv.org/abs/2312.10997) —— 全面的 RAG 综述。
