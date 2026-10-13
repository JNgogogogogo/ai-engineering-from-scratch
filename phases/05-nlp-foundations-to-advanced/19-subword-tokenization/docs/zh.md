# Subword Tokenization — BPE, WordPiece, Unigram, SentencePiece · 子词分词 —— BPE、WordPiece、Unigram、SentencePiece

> 词级分词器在没见过的词上呛死。字符级分词器把序列长度炸上天。子词分词器取中间路线。每一台现代 LLM 出厂都带一个。
>
> Word tokenizers choke on unseen words. Character tokenizers blow up sequence length. Subword tokenizers split the difference. Every modern LLM ships on one.

**类型:** Learn（学习）
**语言:** Python
**前置课程:** Phase 5 · 01（文本处理）、Phase 5 · 04（GloVe / FastText / 子词）
**时间:** ~60 分钟

## The Problem · 问题

你的词表有 5 万个词。用户输入了 "untokenizable"。你的分词器返回 `[UNK]`。模型从此对这个词没有任何信号。更糟的是：语料里第 90 百分位的文档含有 40 个生僻词，这意味着每个文档丢掉 40 bit 的信息。

子词分词（subword tokenization）解决这个问题。常见词保持单个 token。生僻词分解成有意义的碎片：`untokenizable` → `un`、`token`、`izable`。训练数据覆盖一切，因为任何字符串归根到底都是字节序列。

2026 年的每一个前沿 LLM 出厂都带着三个算法之一（BPE、Unigram、WordPiece），包在三个库之一里（tiktoken、SentencePiece、HF Tokenizers）。不选一个，你没法交付语言模型。

> Your vocabulary has 50,000 words. A user types "untokenizable". Your tokenizer returns `[UNK]`. The model now has no signal about the word. ... Subword tokenization solves this. Common words stay single tokens. Rare words decompose into meaningful pieces ...
> Every frontier LLM in 2026 ships on one of three algorithms (BPE, Unigram, WordPiece), wrapped in one of three libraries (tiktoken, SentencePiece, HF Tokenizers). You cannot ship a language model without picking one.

## The Concept · 概念

![BPE vs Unigram vs WordPiece，逐字符对比](../assets/subword-tokenization.svg)

**BPE（Byte-Pair Encoding，字节对编码）。** 从字符级词表开始。统计每一对相邻符号。把最高频的一对合并成新 token。重复直到达到目标词表大小。统治级的算法：GPT-2/3/4、Llama、Gemma、Qwen2、Mistral。

**字节级 BPE（Byte-level BPE）。** 同一个算法，但作用在原始字节（256 个基础 token）而不是 Unicode 字符上。保证零 `[UNK]`——任何字节序列都能编码。GPT-2 用 50,257 个 token（256 字节 + 50,000 次合并 + 1 个特殊符号）。

**Unigram。** 从一个巨大的词表开始。给每个 token 分配一元概率。迭代剪枝那些「删掉后对语料对数似然伤害最小」的 token。推理时是概率性的：可以对分词结果采样（配合子词正则化 subword regularization 做数据增强很有用）。T5、mBART、ALBERT、XLNet、Gemma 使用它。

**WordPiece。** 合并能让训练语料似然最大化的词对，而不是只看原始频率。BERT、DistilBERT、ELECTRA 使用它。

**SentencePiece vs tiktoken。** SentencePiece 是直接在原始 Unicode 文本上*训练*词表（BPE 或 Unigram）的库，它把空白编码成 `▁`。tiktoken 是 OpenAI 的高速*编码器*，面向预建词表；它不做训练。

经验法则：

- **训练新词表：** SentencePiece（多语言、无需预分词）或 HF Tokenizers。
- **对 GPT 词表做快速推理：** tiktoken（cl100k_base、o200k_base）。
- **两者都要：** HF Tokenizers——一个库，训练 + 服务。

```figure
bpe-merge
```

> **BPE (Byte-Pair Encoding).** Start with a character-level vocabulary. Count every adjacent pair. Merge the most frequent pair into a new token. Repeat until you hit the target vocabulary size. Dominant algorithm: GPT-2/3/4, Llama, Gemma, Qwen2, Mistral.
> **Byte-level BPE.** ... Guarantees zero `[UNK]` tokens — any byte sequence encodes.
> **Unigram.** ... Probabilistic at inference: can sample tokenizations (useful for data augmentation via subword regularization).
> **WordPiece.** Merge pairs that maximize likelihood of the training corpus rather than raw frequency.
> **SentencePiece vs tiktoken.** SentencePiece is the library that *trains* vocabularies (BPE or Unigram) directly on raw Unicode text, encoding whitespace as `▁`. tiktoken is OpenAI's fast *encoder* against pre-built vocabularies; it does not train.

## Build It · 动手造

### Step 1: BPE from scratch · 第 1 步：从零实现 BPE

见 `code/main.py`。循环是：

```python
def train_bpe(corpus, num_merges):
    vocab = {tuple(word) + ("</w>",): count for word, count in corpus.items()}
    merges = []
    for _ in range(num_merges):
        pairs = Counter()
        for symbols, freq in vocab.items():
            for a, b in zip(symbols, symbols[1:]):
                pairs[(a, b)] += freq
        if not pairs:
            break
        best = pairs.most_common(1)[0][0]
        merges.append(best)
        vocab = apply_merge(vocab, best)
    return merges
```

这个算法编码了三件事。`</w>` 标记词尾，所以 "low"（作为后缀）和 "lower"（作为前缀）保持可区分。频率加权让高频词对在早期胜出。merge 列表是有序的——推理按训练顺序应用合并。

> Three facts the algorithm encodes. `</w>` marks word end so "low" (suffix) and "lower" (prefix) stay distinct. Frequency weighting makes high-frequency pairs win early. The merge list is ordered — inference applies merges in training order.

### Step 2: encode with the learned merges · 第 2 步：用学到的合并来编码

```python
def encode_bpe(word, merges):
    symbols = list(word) + ["</w>"]
    for a, b in merges:
        i = 0
        while i < len(symbols) - 1:
            if symbols[i] == a and symbols[i + 1] == b:
                symbols = symbols[:i] + [a + b] + symbols[i + 2:]
            else:
                i += 1
    return symbols
```

朴素的 O(n·|merges|)。生产级实现（tiktoken、HF Tokenizers）使用带优先队列的 merge-rank 查找，运行时间接近线性。

> Naive O(n·|merges|). Production implementations (tiktoken, HF Tokenizers) use merge-rank lookup with priority queues and run in near-linear time.

### Step 3: SentencePiece in practice · 第 3 步：实战中的 SentencePiece

```python
import sentencepiece as spm

spm.SentencePieceTrainer.train(
    input="corpus.txt",
    model_prefix="my_tokenizer",
    vocab_size=8000,
    model_type="bpe",          # or "unigram"
    character_coverage=0.9995, # lower for CJK (e.g. 0.9995 for English, 0.995 for Japanese)
    normalization_rule_name="nmt_nfkc",
)

sp = spm.SentencePieceProcessor(model_file="my_tokenizer.model")
print(sp.encode("untokenizable", out_type=str))
# ['▁un', 'token', 'izable']
```

注意：不需要预分词，空格被编码为 `▁`，`character_coverage` 控制生僻字符是被保留还是被映射到 `<unk>` 的激进程度。

> Notice: no pre-tokenization required, space encoded as `▁`, `character_coverage` controls how aggressively rare characters are preserved vs mapped to `<unk>`.

### Step 4: tiktoken for OpenAI-compatible vocabs · 第 4 步：用 tiktoken 对接 OpenAI 兼容词表

```python
import tiktoken
enc = tiktoken.get_encoding("o200k_base")
print(enc.encode("untokenizable"))        # [127340, 101028]
print(len(enc.encode("Hello, world!")))   # 4
```

只做编码。快（Rust 后端）。与 GPT-4/5 的分词完全一致，可用于字节计数、成本估算和上下文窗口预算。

> Encoding-only. Fast (Rust backend). Exact match with GPT-4/5 tokenization for byte-counting, cost estimation, context-window budgeting.

## Pitfalls that still ship in 2026 · 2026 年仍在上线的坑

- **分词器漂移（tokenizer drift）。** 用词表 A 训练，部署时对着词表 B。token ID 对不上，模型输出乱码。在 CI 里检查 `tokenizer.json` 的哈希。
- **空白歧义。** BPE 里 "hello" 和 " hello" 产生不同的 token。始终显式指定 `add_special_tokens` 和 `add_prefix_space`。
- **多语言训练不足。** 以英语为主的语料产出的词表，会把非拉丁文字切出 5-10 倍的 token。同样的 prompt 在 GPT-3.5 上日语/阿拉伯语要多花 5-10 倍。o200k_base 部分修复了这个问题。
- **emoji 切分。** 一个 emoji 可能占 5 个 token。预算上下文时注意 emoji 的处理。

> **Tokenizer drift.** Training on vocab A, deploying against vocab B. Token IDs differ; model outputs garbage. Check `tokenizer.json` hash in CI.
> **Whitespace ambiguity.** ... **Multilingual undertraining.** ... **Emoji splits.** A single emoji can take 5 tokens.

## Use It · 实战用法

2026 年的技术栈：

| 情形 | 选择 |
|-----------|------|
| 从零训练单语模型 | HF Tokenizers（BPE）|
| 训练多语言模型 | SentencePiece（Unigram，`character_coverage=0.9995`）|
| 服务 OpenAI 兼容 API | tiktoken（GPT-4+ 用 `o200k_base`）|
| 领域专用词表（代码、数学、蛋白质）| 在领域语料上训练自定义 BPE，再与基础词表合并 |
| 边缘推理、小模型 | Unigram（更小的词表效果更好）|

词表大小是一个扩展性决策，不是常数。粗略启发：小于 1B 参数用 32k，1-10B 用 50-100k，多语言/前沿模型用 200k+。

> Vocabulary size is a scaling decision, not a constant. Rough heuristic: 32k for <1B params, 50-100k for 1-10B, 200k+ for multilingual/frontier.

## Ship It · 交付

保存为 `outputs/skill-bpe-vs-wordpiece.md`：

```markdown
---
name: tokenizer-picker
description: Pick tokenizer algorithm, vocab size, library for a given corpus and deployment target.
version: 1.0.0
phase: 5
lesson: 19
tags: [nlp, tokenization]
---

Given a corpus (size, languages, domain) and deployment target (training from scratch / fine-tuning / API-compatible inference), output:

1. Algorithm. BPE, Unigram, or WordPiece. One-sentence reason.
2. Library. SentencePiece, HF Tokenizers, or tiktoken. Reason.
3. Vocab size. Rounded to nearest 1k. Reason tied to model size and language coverage.
4. Coverage settings. `character_coverage`, `byte_fallback`, special-token list.
5. Validation plan. Average tokens-per-word on held-out set, OOV rate, compression ratio, round-trip decode equality.

Refuse to train a character-coverage <0.995 tokenizer on corpora with rare-script content. Refuse to ship a vocab without a frozen `tokenizer.json` hash check in CI. Flag any monolingual tokenizer under 16k vocab as likely under-spec.
```

> Save as `outputs/skill-bpe-vs-wordpiece.md`.

## Exercises · 练习

1. **简单。** 在 `code/main.py` 的小语料上训练一个 500 次合并的 BPE。编码三个留出词。多少个恰好得到 1 个 token、多少个超过 1 个 token？
2. **中等。** 在 100 句英语维基百科句子上比较 `cl100k_base`、`o200k_base` 和你自己训练的 vocab=32k SentencePiece BPE 的 token 数。报告各自的压缩率。
3. **困难。** 在同一语料上分别训练 BPE、Unigram 和 WordPiece。在一个小型情感分类器上测各自的下游准确率。这个选择能让 F1 动超过 1 个点吗？

## Key Terms · 关键术语

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| BPE | Byte-Pair Encoding | 对最高频字符对做贪心合并，直到达到目标词表大小。|
| Byte-level BPE | 永远没有未知 token | 在原始 256 字节上跑 BPE；GPT-2 / Llama 用的就是它。|
| Unigram | 概率型分词器 | 用对数似然从大候选集中剪枝；T5、Gemma 使用。|
| SentencePiece | 处理空格的那个 | 在原始文本上训练 BPE/Unigram 的库；空格编码为 `▁`。|
| tiktoken | 快的那个 | OpenAI 的 Rust 后端 BPE 编码器，面向预建词表。不训练。|
| Merge list | 那串魔法数字 | 有序的 `(a, b) → ab` 合并列表；推理按顺序应用。|
| Character coverage | 多稀有算太稀有？ | 分词器必须覆盖的训练语料字符比例；通常约 0.9995。|

## Further Reading · 延伸阅读

- [Sennrich, Haddow, Birch (2015). Neural Machine Translation of Rare Words with Subword Units](https://arxiv.org/abs/1508.07909) —— BPE 论文。
- [Kudo (2018). Subword Regularization with Unigram Language Model](https://arxiv.org/abs/1804.10959) —— Unigram 论文。
- [Kudo, Richardson (2018). SentencePiece: A simple and language independent subword tokenizer](https://arxiv.org/abs/1808.06226) —— 这个库的论文。
- [Hugging Face — Summary of the tokenizers](https://huggingface.co/docs/transformers/tokenizer_summary) —— 简明参考。
- [OpenAI tiktoken repo](https://github.com/openai/tiktoken) —— cookbook + 编码列表。
