# Machine Translation · 机器翻译

> 翻译这项任务养活了 NLP 研究三十年，至今仍在持续输血。
> Translation is the task that paid for NLP research for thirty years and keeps paying now.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 5 · 10 (Attention Mechanism), Phase 5 · 04 (GloVe, FastText, Subword)
**Time:** ~75 minutes

## The Problem · 问题在哪

模型读入一种语言的句子，产出另一种语言的句子。长度会变。词序会变。有的源语词要对应多个目标语词，反过来也一样。习语拒绝一词对一词的映射："I miss you" 在法语里是 "tu me manques" —— 字面意思是「你对我而言有所缺失」。任何词级对齐在这种句子面前都活不下来。

机器翻译（machine translation）就是那个逼着 NLP 发明出编码器-解码器、注意力机制、Transformer、乃至整个 LLM 范式的任务。每一步前进，都是因为翻译质量可度量，而人与机器之间的差距又顽固地存在。

本课跳过历史课，直接教 2026 年能干活的技术管线：预训练多语言编码器-解码器（NLLB-200 或 mBART）、子词分词（subword tokenization）、束搜索（beam search）、BLEU 与 chrF 评估，以及那几种至今仍会未被察觉地溜进生产的失败模式。

> A model reads a sentence in one language and produces a sentence in another. Length varies. Word order varies. Some source words map to multiple target words and vice versa. Idioms refuse one-to-one mapping. "I miss you" in French is "tu me manques" — literally "you are lacking to me." No word-level alignment survives that.
> Machine translation is the task that forced NLP to invent encoder-decoders, attention, transformers, and eventually the whole LLM paradigm. Every step forward arrived because translation quality was measurable and the gap between human and machine was stubborn.
> This lesson skips the history lesson and teaches the working pipeline of 2026: pretrained multilingual encoder-decoder (NLLB-200 or mBART), subword tokenization, beam search, BLEU and chrF evaluation, and the handful of failure modes that still ship to production uncaught.

## The Concept · 概念

![MT 管线：分词 → 编码 → 带注意力解码 → 反分词](../assets/mt-pipeline.svg)

现代 MT 是在平行文本（parallel text）上训练的 Transformer 编码器-解码器。编码器按源语言自己的分词方案读入源句。解码器通过交叉注意力（cross-attention，第 10 课）利用编码器的输出，一次一个子词地生成目标句。解码阶段用束搜索（beam search）避开贪心解码的陷阱。输出经过反分词（detokenization）、还原大小写（detruecase），再对照参考译文打分。

三个工程决策决定真实世界的 MT 质量。

- **分词器（Tokenizer）。** 在混合语言语料上训练的 SentencePiece BPE。跨语言共享词表，正是 NLLB 能支持零样本（zero-shot）语言对的原因。
- **模型规模。** NLLB-200 distilled 600M 能塞进笔记本。NLLB-200 3.3B 是公开的生产默认规格。54.5B 是研究上限。
- **解码。** 通用内容用 4-5 的束宽（beam width）。用长度惩罚（length penalty）避免过短的输出。需要术语一致性时用受限解码（constrained decoding）。

```figure
seq2seq-alignment
```

> Modern MT is a transformer encoder-decoder trained on parallel text. The encoder reads the source in its language's tokenization. The decoder generates the target, one subword at a time, using the encoder's output via cross-attention (lesson 10). Decoding uses beam search to avoid the greedy-decoding trap. The output is detokenized, detruecased, and scored against a reference.
> Three operational choices drive real-world MT quality.
> - **Tokenizer.** SentencePiece BPE trained on a mixed-language corpus. Shared vocabulary across languages is what enables zero-shot pairs in NLLB.
> - **Model size.** NLLB-200 distilled 600M fits on a laptop. NLLB-200 3.3B is the published production default. 54.5B is the research ceiling.
> - **Decoding.** Beam width 4-5 for general content. Length penalty to avoid too-short output. Constrained decoding when you need terminology consistency.

## Build It · 动手造

### Step 1: a pretrained MT call · 一次预训练 MT 调用

```python
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

model_id = "facebook/nllb-200-distilled-600M"
tok = AutoTokenizer.from_pretrained(model_id, src_lang="eng_Latn")
model = AutoModelForSeq2SeqLM.from_pretrained(model_id)

src = "The cats are running."
inputs = tok(src, return_tensors="pt")

out = model.generate(
    **inputs,
    forced_bos_token_id=tok.convert_tokens_to_ids("fra_Latn"),
    num_beams=5,
    length_penalty=1.0,
    max_new_tokens=64,
)
print(tok.batch_decode(out, skip_special_tokens=True)[0])
```

```text
Les chats courent.
```

这里有三个要点。`src_lang` 告诉分词器套用哪种文字系统和切分方式。`forced_bos_token_id` 告诉解码器生成哪种语言。两者都是 NLLB 专属的用法；mBART 和 M2M-100 有各自的一套约定，不能互换。

> Three things matter here. `src_lang` tells the tokenizer which script and segmentation to apply. `forced_bos_token_id` tells the decoder which language to generate. Both are NLLB-specific tricks; mBART and M2M-100 use their own conventions and they are not interchangeable.

### Step 2: BLEU and chrF · BLEU 与 chrF

BLEU 度量输出与参考译文之间的 n-gram 重叠。四个参考 n-gram 阶数（1-4），各阶精度的几何平均，再加上对过短输出的简短惩罚（brevity penalty）。分数范围 [0, 100]。使用广泛。解读起来令人沮丧：30 BLEU 算「能用」，40 算「好」，50 算「出色」，小于 1 BLEU 的差异都是噪声。

chrF 度量字符级 F 分数。对形态丰富的语言更敏感——BLEU 在这些语言上会漏算匹配。通常与 BLEU 一起报告。

```python
import sacrebleu

hypotheses = ["Les chats courent."]
references = [["Les chats courent."]]

bleu = sacrebleu.corpus_bleu(hypotheses, references)
chrf = sacrebleu.corpus_chrf(hypotheses, references)
print(f"BLEU: {bleu.score:.1f}  chrF: {chrf.score:.1f}")
```

永远用 `sacrebleu`。它把分词归一化，让分数可以跨论文比较。自己手搓 BLEU 计算，正是误导性基准的来源。

> BLEU measures n-gram overlap between output and reference. Four reference n-gram sizes (1-4), geometric mean of precisions, brevity penalty for too-short output. The score is in [0, 100]. Commonly used. Frustrating to interpret: 30 BLEU is "usable"; 40 is "good"; 50 is "exceptional"; differences under 1 BLEU are noise.
> chrF measures character-level F-score. More sensitive to morphologically rich languages where BLEU undercounts matches. Often reported alongside BLEU.
> Always use `sacrebleu`. It normalizes tokenization so scores are comparable across papers. Rolling your own BLEU computation is how misleading benchmarks happen.

### The three-tier evaluation hierarchy (2026) · 三层评估体系（2026）

现代 MT 评估使用三个互补的指标家族。上线时至少带其中两个。

- **启发式（Heuristic）**（BLEU、chrF）。快、基于参考译文、可解释、对意译不敏感。用于历史对比和回归检测。
- **学习型（Learned）**（COMET、BLEURT、BERTScore）。在人类评判数据上训练的神经模型；比较译文与源文、参考译文之间的语义相似度。COMET 自 2023 年以来与 MT 研究的关联度最高，是 2026 年重视质量时的生产默认选择。
- **LLM 当裁判（LLM-as-judge）**（无参考）。提示一个大模型按流畅度、充分性、语气、文化得体性给译文打分。评分细则（rubric）设计得当时，GPT-4 裁判与人类的一致率约 80%。用于没有参考译文的开放式内容。

2026 年的实用组合：`sacrebleu` 算 BLEU 和 chrF，`unbabel-comet` 算 COMET，再加一个带提示词的 LLM 提供面向人的最终信号。在每个指标用于生产数据之前，先在 50-100 条人工标注样本上校准。

无参考指标（COMET-QE、BLEURT-QE、LLM-as-judge）让你在没有参考译文的情况下评估翻译——这对不存在参考译文的长尾语言对至关重要。

> Modern MT evaluation uses three complementary metric families. Ship with at least two. ... **Learned** (COMET, BLEURT, BERTScore). Neural models trained on human judgment; compare semantic similarity of translation to source and reference. COMET has the highest association with MT research since 2023 and is the 2026 production default where quality matters. ... Practical 2026 stack: `sacrebleu` for BLEU and chrF, `unbabel-comet` for COMET, and a prompted LLM for the final human-facing signal. Calibrate every metric against 50-100 human-labeled examples before trusting it on production data. ... Reference-free metrics (COMET-QE, BLEURT-QE, LLM-as-judge) let you evaluate translations without a reference, which matters for long-tail language pairs where reference translations do not exist.

### Step 3: what breaks in production · 生产环境里会坏掉什么

上面这条能跑通的管线，80% 的时候翻得流畅，剩下 20% 悄无声息地失败。有名有姓的失败模式如下：

- **幻觉（Hallucination）。** 模型编造源文里不存在的内容。在陌生的领域词汇上很常见。症状：输出流畅，却声称源文没有陈述过的事实。缓解：对领域术语用受限解码，受监管内容加人工审核，监控输出远长于输入的情况。
- **目标语言跑偏（Off-target generation）。** 模型翻成了错误的语言。NLLB 在稀有语言对上出奇地容易犯这个毛病。缓解：核对 `forced_bos_token_id`，并且始终在输出上跑一次语言识别（language-ID）模型检查。
- **术语漂移（Terminology drift）。** "Sign up" 在文档 1 里成了 "s'inscrire"，在文档 2 里成了 "créer un compte"。对 UI 文案和面向用户的字符串来说，一致性比原始质量更重要。缓解：术语表约束解码，或后编辑字典替换。
- **敬语错配（Formality mismatch）。** 法语的 "tu" 与 "vous"，日语的敬语层级。模型会挑训练数据里更常见的那一种形式。对面向客户的内容来说这通常是错的。缓解：如果模型支持，用带敬语标记的提示前缀；或者只在正式语料上微调一个小模型。
- **短输入的长度爆炸。** 非常短的输入句经常产出过长的译文，因为长度惩罚在源文约 5 个 token 以下会断崖式失效。缓解：按源文长度设定硬性最大长度上限。

> The working pipeline above will translate fluently 80% of the time and silently fail the remaining 20%. Named failure modes: ... **Hallucination.** Model invents content that was not in the source. Common in unfamiliar domain vocabulary. Symptom: output is fluent but claims facts the source did not state. ... **Off-target generation.** Model translates into the wrong language. NLLB is surprisingly prone to this on rare language pairs. ... **Terminology drift.** "Sign up" becomes "s'inscrire" in doc 1 and "créer un compte" in doc 2. For UI text and user-facing strings, consistency matters more than raw quality. ... **Length explosion on short input.** Very short input sentences often produce overlong translations because the length penalty falls off a cliff below ~5 source tokens.

### Step 4: fine-tuning for a domain · 面向领域的微调

预训练模型是通才。法律、医疗或游戏对话的翻译，在领域平行数据上微调后有可度量的收益。配方并不神秘：

```python
from transformers import Trainer, TrainingArguments
from datasets import Dataset

pairs = [
    {"src": "The defendant pleaded guilty.", "tgt": "L'accusé a plaidé coupable."},
]

ds = Dataset.from_list(pairs)


def preprocess(ex):
    return tok(
        ex["src"],
        text_target=ex["tgt"],
        truncation=True,
        max_length=128,
        padding="max_length",
    )


ds = ds.map(preprocess, remove_columns=["src", "tgt"])

args = TrainingArguments(output_dir="out", per_device_train_batch_size=4, num_train_epochs=3, learning_rate=3e-5)
Trainer(model=model, args=args, train_dataset=ds).train()
```

几千条高质量的平行样本，胜过几十万条嘈杂的网络抓取样本。训练数据的质量是生产环境里最大的单个杠杆。

> Pretrained models are generalists. Legal, medical, or game-dialog translation benefits measurably from fine-tuning on domain parallel data. The recipe is not exotic: ... A few thousand high-quality parallel examples beats a few hundred thousand noisy web-scraped ones. Quality of training data is the single largest production lever.

## Use It · 实战用法

2026 年的 MT 生产技术栈：

| 使用场景 | 推荐起点 |
|---------|---------------------------|
| 任意语言互译、200 种语言 | `facebook/nllb-200-distilled-600M`（笔记本）或 `nllb-200-3.3B`（生产） |
| 以英语为中心、高质量、50 种语言 | `facebook/mbart-large-50-many-to-many-mmt` |
| 短任务、便宜推理、英法/德/西 | Helsinki-NLP / Marian 模型 |
| 延迟敏感的浏览器端 | ONNX 量化的 Marian（约 50 MB） |
| 追求最高质量、预算充足 | 带翻译提示词的 GPT-4 / Claude / Gemini |

截至 2026 年，LLM 在若干语言对上已经超过专用 MT 模型，尤其是在习语内容和长上下文上。代价是按 token 计费的成本和延迟。当上下文长度、风格一致性、或通过提示词做领域适配比吞吐量更重要时，选 LLM。

> The 2026 production stack for MT: ... LLMs now outperform specialized MT models on several language pairs as of 2026, particularly on idiomatic content and long context. The tradeoff is per-token cost and latency. Pick an LLM when context length, stylistic consistency, or domain adaptation via prompting matters more than throughput.

## Ship It · 交付

保存为 `outputs/skill-mt-evaluator.md`：

```markdown
---
name: mt-evaluator
description: Evaluate a machine translation output for shipping.
version: 1.0.0
phase: 5
lesson: 11
tags: [nlp, translation, evaluation]
---

Given a source text and a candidate translation, output:

1. Automatic score estimate. BLEU and chrF ranges you would expect. State whether a reference is available.
2. Five-point human-verifiable check list: (a) content preservation (no hallucinations), (b) correct language, (c) register / formality match, (d) terminology consistency with glossary if provided, (e) no truncation or length explosion.
3. One domain-specific issue to probe. E.g., for legal: named entities and statute citations. For medical: drug names and dosages. For UI: placeholder variables `{name}`.
4. Confidence flag. "Ship" / "Ship with review" / "Do not ship". Tie to the severity of issues found in step 2.

Refuse to ship a translation without a language-ID check on output. Refuse to evaluate without a reference unless the user explicitly opts in to reference-free scoring (COMET-QE, BLEURT-QE). Flag any content over 1000 tokens as likely needing chunked translation.
```

> Save as `outputs/skill-mt-evaluator.md`:

## Exercises · 练习

1. **简单。** 用 `nllb-200-distilled-600M` 把一段 5 句的英文段落翻成法语再翻回英语。度量往返结果与原文的接近程度。你应该会看到语义保留、用词漂移。
2. **中等。** 用 `fasttext lid.176` 或 `langdetect` 给翻译输出实现语言识别检查。把它接进 MT 调用，让目标语言跑偏的生成在返回之前就被拦下。
3. **困难。** 在你自己选的 5,000 对领域语料上微调 `nllb-200-distilled-600M`。在留出集上度量微调前后的 BLEU。报告哪些类型的句子变好了、哪些变差了。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| BLEU | 翻译分数 | 带 brevity penalty 的 n-gram 精度。范围 [0, 100]。 |
| chrF | 字符 F 分数 | 字符级 F 分数。对形态丰富的语言更敏感。 |
| NMT | 神经机器翻译 | 在平行文本上训练的 Transformer 编码器-解码器。2017 年以后的默认。 |
| NLLB | No Language Left Behind | Meta 的 200 语言 MT 模型家族。 |
| Constrained decoding（受限解码） | 受控输出 | 强制特定 token 或 n-gram 在输出中出现 / 不出现。 |
| Hallucination（幻觉） | 编造的内容 | 源文不支撑的模型输出。 |

## Further Reading · 延伸阅读

- [Costa-jussà et al. (2022). No Language Left Behind: Scaling Human-Centered Machine Translation](https://arxiv.org/abs/2207.04672) —— NLLB 论文。
- [Post (2018). A Call for Clarity in Reporting BLEU Scores](https://aclanthology.org/W18-6319/) —— 为什么 `sacrebleu` 是报告 BLEU 的唯一正确方式。
- [Popović (2015). chrF: character n-gram F-score for automatic MT evaluation](https://aclanthology.org/W15-3049/) —— chrF 论文。
- [Hugging Face MT guide](https://huggingface.co/docs/transformers/tasks/translation) —— 实用的微调 walkthrough。
