# BERT — Masked Language Modeling · BERT——掩码语言建模

> GPT predicts the next word. BERT predicts a missing word. One sentence of difference — and half a decade of everything embedding-shaped.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 7 · 05 (Full Transformer), Phase 5 · 02 (Text Representation)
**Time:** ~45 minutes

## The Problem · 问题在哪

2018 年，每个 NLP 任务——情感分析、NER、问答、蕴含——都在各自的标注数据上从零训练各自的模型。没有一个预训练好的「懂英语」checkpoint 供你微调。ELMo（2018）证明了可以用双向 LSTM 预训练上下文相关的 embedding；有帮助，但没有形成通用范式。

BERT（Devlin et al. 2018）问的是：如果拿一个 transformer 编码器，用全网的所有句子训练它，逼它从两侧的上下文预测缺失的词，会怎样？然后你只需在下游任务上微调一个头。参数效率的解放令人震撼。

结果：18 个月内，BERT 及其变体（RoBERTa、ALBERT、ELECTRA）横扫了当时存在的所有 NLP 榜单。到 2020 年，地球上每个搜索引擎、内容审核管道和语义检索系统里都住着一个 BERT。

2026 年，encoder-only 模型仍然是分类、检索和结构化抽取的正确工具——每 token 速度比解码器快 5–10×，它们的 embedding 是每个现代检索栈的骨干。ModernBERT（2024 年 12 月）用 Flash Attention + RoPE + GeGLU 把这个架构推到了 8K 上下文。

> In 2018 every NLP task — sentiment, NER, QA, entailment — trained its own model from scratch on its own labeled data. There was no pre-trained "understand English" checkpoint you could fine-tune. ELMo (2018) showed you could pre-train contextual embeddings with a bidirectional LSTM; it helped but did not generalize.
> BERT (Devlin et al. 2018) asked: what if we took a transformer encoder, trained it on every sentence on the internet, and forced it to predict missing words from context on both sides? Then you fine-tune one head on your downstream task. Parameter efficiency was a revelation.
> The result: within 18 months BERT and its variants (RoBERTa, ALBERT, ELECTRA) dominated every NLP leaderboard that existed. By 2020 every search engine, content moderation pipeline, and semantic-search system on earth had a BERT inside.
> In 2026 encoder-only models are still the right tool for classification, retrieval, and structured extraction — they run 5–10× faster per token than decoders and their embeddings are the backbone of every modern retrieval stack. ModernBERT (Dec 2024) pushed the architecture to 8K context with Flash Attention + RoPE + GeGLU.

## The Concept · 概念

![Masked language modeling: pick tokens, mask them, predict originals](../assets/bert-mlm.svg)

### The training signal · 训练信号

拿一个句子：`the quick brown fox jumps over the lazy dog`。

随机 mask 掉 15% 的 token：

```
input:  the [MASK] brown fox jumps [MASK] the lazy dog
target: the  quick brown fox jumps  over  the lazy dog
```

训练模型在被 mask 的位置预测原始 token。因为编码器是双向的，预测位置 1 的 `[MASK]` 可以用上位置 2 之后的 `brown fox jumps`。这正是 GPT 做不到的事。

> Take a sentence: `the quick brown fox jumps over the lazy dog`.
> Mask 15% of tokens randomly:
> Train the model to predict the original tokens at masked positions. Because the encoder is bidirectional, predicting `[MASK]` at position 1 can use `brown fox jumps` at positions 2+. That is the thing GPT cannot do.

### The BERT mask rules · BERT 的 mask 规则

在被选中做预测的 15% token 里：

- 80% 替换成 `[MASK]`。
- 10% 替换成随机 token。
- 10% 保持不变。

为什么不全部用 `[MASK]`？因为推理时根本不会出现 `[MASK]`。如果训练时让模型预期 100% 的被 mask 位置都是 `[MASK]`，会在预训练和微调之间制造分布偏移。10% 随机 + 10% 不变让模型保持诚实。

> Of the 15% of tokens selected for prediction:
> - 80% are replaced with `[MASK]`.
> - 10% are replaced with a random token.
> - 10% are left unchanged.
> Why not always `[MASK]`? Because `[MASK]` never appears at inference time. Training the model to expect `[MASK]` at 100% of masked positions would create a distribution shift between pretraining and fine-tuning. The 10% random + 10% unchanged keeps the model honest.

### Next Sentence Prediction (NSP) — and why it was dropped · NSP——以及它为什么被砍掉

原版 BERT 还训练 NSP：给两个句子 A 和 B，预测 B 是否紧跟在 A 后面。RoBERTa（2019）做了消融实验，证明 NSP 是帮倒忙。现代编码器直接跳过它。

> Original BERT also trained on NSP: given two sentences A and B, predict if B follows A. RoBERTa (2019) ablated it and showed NSP hurt, not helped. Modern encoders skip it.

### What changed in 2026: ModernBERT · 2026 年的变化：ModernBERT

2024 年的 ModernBERT 论文用 2026 年的原语重造了块：

| 部件 | 初代 BERT（2018） | ModernBERT（2024） |
|------|------------------|--------------------|
| 位置编码 | 可学习的绝对位置 | RoPE |
| 激活函数 | GELU | GeGLU |
| 归一化 | LayerNorm | Pre-norm RMSNorm |
| 注意力 | 全量稠密 | 局部（128）与全局交替 |
| 上下文长度 | 512 | 8192 |
| 分词器 | WordPiece | BPE |

而且和 2018 年那套不同，它原生支持 Flash Attention。序列长度 8K 时，推理比 DeBERTa-v3 快 2–3×，GLUE 分数还更高。

> The 2024 ModernBERT paper rebuilt the block with 2026 primitives:
> And unlike the 2018 stack, it is Flash-Attention-native. Inference is 2–3× faster at sequence length 8K than DeBERTa-v3 with better GLUE scores.

### Use cases that still pick an encoder in 2026 · 2026 年仍选编码器的场景

| 任务 | 编码器为什么胜过解码器 |
|------|-----------------------|
| 检索 / 语义搜索 embedding | 双向上下文 = 每 token 更好的 embedding 质量 |
| 分类（情感、意图、毒性） | 一次前向；没有生成开销 |
| NER / token 标注 | 逐位置输出，天然双向 |
| 零样本蕴含（NLI） | 编码器之上接一个分类头 |
| RAG 重排器 | 交叉编码器打分，比 LLM 重排快 10 倍 |

```figure
transformer-residual
```

## Build It · 动手造

### Step 1: masking logic · 第 1 步：mask 逻辑

见 `code/main.py`。函数 `create_mlm_batch` 接收 token ID 列表、词表大小和 mask 概率。返回输入 ID（已应用 mask）和标签（只在被 mask 的位置有值，其余为 -100——PyTorch 的忽略索引约定）。

```python
def create_mlm_batch(tokens, vocab_size, mask_prob=0.15, rng=None):
    input_ids = list(tokens)
    labels = [-100] * len(tokens)
    for i, t in enumerate(tokens):
        if rng.random() < mask_prob:
            labels[i] = t
            r = rng.random()
            if r < 0.8:
                input_ids[i] = MASK_ID
            elif r < 0.9:
                input_ids[i] = rng.randrange(vocab_size)
            # else: keep original
    return input_ids, labels
```

> See `code/main.py`. The function `create_mlm_batch` takes a list of token IDs, a vocab size, and a mask probability. Returns input IDs (with masks applied) and labels (only at masked positions, -100 elsewhere — PyTorch's ignore index convention).

### Step 2: run MLM prediction on a tiny corpus · 第 2 步：在小语料上跑 MLM 预测

在 20 个词的词表、200 个句子上训练一个 2 层编码器 + MLM 头。不求梯度——只做前向 sanity check。完整训练需要 PyTorch。

> Train a 2-layer encoder + MLM head on a vocabulary of 20 words, 200 sentences. No gradient — we do forward-pass sanity checks. Full training needs PyTorch.

### Step 3: compare mask types · 第 3 步：对比 mask 类型

展示三选一规则如何让模型在没有 `[MASK]` 时依然可用。分别在未 mask 的句子和 mask 过的句子上做预测。两者都应产生合理的 token 分布，因为训练时模型两种模式都见过。

> Show how the three-way rule keeps the model usable without `[MASK]`. Predict on an unmasked sentence and on a masked sentence. Both should produce reasonable token distributions because the model saw both patterns in training.

### Step 4: fine-tune head · 第 4 步：微调头部

在玩具情感数据集上把 MLM 头换成分类头。只训练头；编码器冻结。每个 BERT 应用都遵循这个模式。

> Replace the MLM head with a classification head on a toy sentiment dataset. Only the head trains; the encoder is frozen. This is the pattern every BERT application follows.

## Use It · 实战用法

```python
from transformers import AutoModel, AutoTokenizer

tok = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-base")
model = AutoModel.from_pretrained("answerdotai/ModernBERT-base")

text = "Attention is all you need."
inputs = tok(text, return_tensors="pt")
out = model(**inputs).last_hidden_state   # (1, N, 768)
```

**Embedding 模型就是微调过的 BERT。** `sentence-transformers` 里像 `all-MiniLM-L6-v2` 这样的模型，就是用对比损失训练的 BERT。编码器没变，换的是损失。

**交叉编码器重排器也是微调过的 BERT。** 在 `[CLS] query [SEP] doc [SEP]` 上做 pair 分类。query 和 doc 之间的双向注意力，正是交叉编码器质量胜过双编码器（biencoder）的原因。

**2026 年什么时候不该选 BERT。** 一切生成式任务。编码器没有办法以合理方式自回归地产出 token。另外：参数量 1B 以下、小型解码器能以更高灵活性达到同等质量的场景（Phi-3-Mini、Qwen2-1.5B）。

> **Embedding models are fine-tuned BERT.** `sentence-transformers` models like `all-MiniLM-L6-v2` are BERTs trained with contrastive loss. The encoder is the same. The loss changed.
> **Cross-encoder rerankers are also fine-tuned BERT.** Pair-classification on `[CLS] query [SEP] doc [SEP]`. The bidirectional attention between query and doc is exactly what gives cross-encoders their quality edge over biencoders.
> **When not to pick BERT in 2026.** Anything generative. The encoder has no sensible way to autoregressively produce tokens. Also: anything under 1B params where a small decoder can match quality with more flexibility (Phi-3-Mini, Qwen2-1.5B).

## Ship It · 交付

见 `outputs/skill-bert-finetuner.md`。这个 skill 为新的分类或抽取任务规划一次 BERT 微调（骨干选择、头部规格、数据、评估、停止条件）。

> See `outputs/skill-bert-finetuner.md`. The skill scopes a BERT fine-tune (backbone choice, head spec, data, eval, stopping) for a new classification or extraction task.

## Exercises · 练习

1. **简单。** 跑 `code/main.py`，打印 10,000 个 token 上的 mask 分布。确认约 15% 被选中，其中约 80% 变成 `[MASK]`。
2. **中等。** 实现全词掩码（whole-word masking）：一个词被切成多个 subword 时，要么全部一起 mask，要么全不 mask。在 500 句语料上测量这是否提升 MLM 准确率。
3. **困难。** 用公开数据集的 10,000 个句子训练一个微型（2 层，d=64）BERT。微调 `[CLS]` token 做 SST-2 情感分类。与参数量对齐的 decoder-only 基线对比——谁赢？

> 1. **Easy.** Run `code/main.py` and print the mask distribution across 10,000 tokens. Confirm ~15% are selected, and of those ~80% become `[MASK]`.
> 2. **Medium.** Implement whole-word masking: if a word is tokenized into subwords, mask all subwords together or none. Measure whether this improves MLM accuracy on a 500-sentence corpus.
> 3. **Hard.** Train a tiny (2-layer, d=64) BERT on 10,000 sentences from a public dataset. Fine-tune the `[CLS]` token for SST-2 sentiment. Compare against a decoder-only baseline at matched params — which wins?

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------|---------|
| MLM | 「掩码语言建模」 | 训练信号：随机把 15% 的 token 换成 `[MASK]`，让模型预测原文。 |
| Bidirectional（双向） | 「两头都看」 | 编码器注意力没有因果 mask——每个位置看到所有其他位置。 |
| `[CLS]` | 「池化 token」 | 加在每个序列开头的特殊 token；它最终的 embedding 用作句子级表示。 |
| `[SEP]` | 「分段分隔符」 | 分隔成对的序列（如 query/doc、句子 A/B）。 |
| NSP | 「下一句预测」 | BERT 的第二个预训练任务；RoBERTa 证明它没用，2019 年后被抛弃。 |
| Fine-tuning（微调） | 「适配到任务」 | 编码器基本冻结；在顶上训练一个小头来做下游任务。 |
| Cross-encoder（交叉编码器） | 「重排器」 | 一个同时接收 query 和 doc 的 BERT，输出相关性分数。 |
| ModernBERT | 「2024 年翻新版」 | 用 RoPE、RMSNorm、GeGLU、局部/全局交替注意力、8K 上下文重造的编码器。 |

## Further Reading · 延伸阅读

- [Devlin et al. (2018). BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding](https://arxiv.org/abs/1810.04805) —— 原始论文。
- [Liu et al. (2019). RoBERTa: A Robustly Optimized BERT Pretraining Approach](https://arxiv.org/abs/1907.11692) —— 怎么把 BERT 训对；砍掉 NSP。
- [Clark et al. (2020). ELECTRA: Pre-training Text Encoders as Discriminators Rather Than Generators](https://arxiv.org/abs/2003.10555) —— 相同算力下，替换 token 检测胜过 MLM。
- [Warner et al. (2024). Smarter, Better, Faster, Longer: A Modern Bidirectional Encoder](https://arxiv.org/abs/2412.13663) —— ModernBERT 论文。
- [HuggingFace `modeling_bert.py`](https://github.com/huggingface/transformers/blob/main/src/transformers/models/bert/modeling_bert.py) —— 编码器的典范参考实现。
