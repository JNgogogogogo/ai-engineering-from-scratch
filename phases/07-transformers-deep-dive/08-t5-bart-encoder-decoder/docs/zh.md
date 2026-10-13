# T5, BART — Encoder-Decoder Models · T5、BART——编码器-解码器模型

> Encoders understand. Decoders generate. Put them back together and you get a model built for input → output tasks: translate, summarize, rewrite, transcribe.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 7 · 05 (Full Transformer), Phase 7 · 06 (BERT), Phase 7 · 07 (GPT)
**Time:** ~45 minutes

## The Problem · 问题在哪

Decoder-only 的 GPT 和 encoder-only 的 BERT 各自为了不同的目标把 2017 年的架构做了裁剪。但很多任务天然就是输入到输出：

- 翻译：英语 → 法语。
- 摘要：5,000 token 的文章 → 200 token 的摘要。
- 语音识别：音频 token → 文本 token。
- 结构化抽取：散文 → JSON。

对这些任务，encoder-decoder 是最干净的契合。编码器产出源序列的稠密表示。解码器生成输出，每一步都交叉注意力到那个表示。训练在输出侧做错位一格（shift-by-one）。和 GPT 同一个损失，只是以编码器输出为条件。

两篇论文定义了现代打法：

1. **T5**（Raffel et al. 2019）。"Text-to-Text Transfer Transformer"。把每个 NLP 任务都重新表述为文本进、文本出。单一架构、单一词表、单一损失。在 masked span 预测上预训练（把输入里的片段弄坏，在输出里解码还原）。
2. **BART**（Lewis et al. 2019）。"Bidirectional and Auto-Regressive Transformer"。去噪自编码器：用多种方式弄坏输入（打乱、mask、删除、旋转），让解码器重建原文。

2026 年，encoder-decoder 形式活在输入结构重要的地方：

- Whisper（语音 → 文本）。
- Google 的翻译体系。
- 一些具有「上下文 + 编辑」独特结构的代码补全 / 修复模型。
- 用于结构化推理任务的 Flan-T5 及其变体。

Decoder-only 赢走了聚光灯，但 encoder-decoder 从未离场。

> Decoder-only GPT and encoder-only BERT each strip down the 2017 architecture for a different goal. But many tasks are naturally input-output:
> - Translation: English → French.
> - Summarization: 5,000-token article → 200-token summary.
> - Speech recognition: audio tokens → text tokens.
> - Structured extraction: prose → JSON.
> For these, encoder-decoder makes the cleanest fit. The encoder produces a dense representation of the source. The decoder generates the output, cross-attending to that representation at every step. Training is shift-by-one on the output side. Same loss as GPT, just conditioned on the encoder output.
> Two papers defined the modern playbook:
> 1. **T5** (Raffel et al. 2019). "Text-to-Text Transfer Transformer." Every NLP task reframed as text-in, text-out. Single architecture, single vocabulary, single loss. Pretrained on masked span prediction (corrupt spans in the input, decode them in the output).
> 2. **BART** (Lewis et al. 2019). "Bidirectional and Auto-Regressive Transformer." Denoising autoencoder: corrupt input in multiple ways (shuffle, mask, delete, rotate), ask the decoder to reconstruct the original.
> In 2026 the encoder-decoder format lives on where input structure matters:
> - Whisper (speech → text).
> - Google's translation stack.
> - Some code-completion / repair models that have distinct context-and-edit structures.
> - Flan-T5 and variants for structured reasoning tasks.
> Decoder-only won the spotlight, but encoder-decoder never went away.

## The Concept · 概念

![Encoder-decoder with cross-attention](../assets/encoder-decoder.svg)

### The forward loop · 前向循环

```
source tokens ─▶ encoder ─▶ (N_src, d_model)  ──┐
                                                 │
target tokens ─▶ decoder block                   │
                 ├─▶ masked self-attention       │
                 ├─▶ cross-attention ◀───────────┘
                 └─▶ FFN
                ↓
              next-token logits
```

关键点：编码器对每个输入只跑一次。解码器自回归地跑，但每一步都交叉注意力到*同一个*编码器输出。缓存编码器输出，对长输入是一笔免费的加速。

> Crucially, the encoder runs once per input. The decoder runs autoregressively but cross-attends to the *same* encoder output at every step. Caching the encoder output is a free speedup for long inputs.

### T5 pretraining — span corruption · T5 预训练——span corruption

从输入里随机挑片段（平均长度 3 个 token，总共 15%）。每个片段替换成一个唯一的哨兵 token：`<extra_id_0>`、`<extra_id_1>` 等。解码器只输出被弄坏的片段，带各自的哨兵前缀：

```
source: The quick <extra_id_0> fox jumps <extra_id_1> dog
target: <extra_id_0> brown <extra_id_1> over the lazy
```

比预测整个序列的信号便宜。在 T5 论文的消融实验里，与 MLM（BERT）和 prefix-LM（UniLM）不相上下。

> Pick random spans of the input (average length 3 tokens, 15% total). Replace each span with a unique sentinel: `<extra_id_0>`, `<extra_id_1>`, etc. The decoder outputs only the corrupted spans with their sentinel prefix:
> Cheaper signal than predicting the whole sequence. Competitive with MLM (BERT) and prefix-LM (UniLM) in the T5 paper's ablation.

### BART pretraining — multi-noise denoising · BART 预训练——多噪声去噪

BART 尝试五种噪声函数：

1. Token 掩码。
2. Token 删除。
3. 文本填充（mask 掉一个片段，解码器补出正确长度的内容）。
4. 句子乱序。
5. 文档旋转。

文本填充 + 句子乱序的组合给出了最好的下游数字。解码器总是重建完整原文。BART 的输出是完整序列，不只是被弄坏的片段——所以预训练算力比 T5 高。

> BART tries five noising functions:
> 1. Token masking.
> 2. Token deletion.
> 3. Text infilling (mask a span, decoder inserts the right length).
> 4. Sentence permutation.
> 5. Document rotation.
> Combining text infilling + sentence permutation produced the best downstream numbers. The decoder always reconstructs the original. BART's output is the full sequence, not just the corrupted spans — so pretraining compute is higher than T5.

### Inference · 推理

和 GPT 一样的自回归生成。Greedy / beam / top-p 采样都适用。Beam search（宽度 4–5）是翻译和摘要的标准做法，因为它们的输出分布比聊天窄。

> Same autoregressive generation as GPT. Greedy / beam / top-p sampling apply. Beam search (width 4–5) is standard for translation and summarization because the output distribution is narrower than chat.

### When to pick each variant in 2026 · 2026 年怎么选架构

| 任务 | 用 encoder-decoder？ | 原因 |
|------|---------------------|------|
| 翻译 | 通常要 | 源序列清晰；输出分布固定；beam search 好使 |
| 语音转文字 | 要（Whisper） | 输入模态与输出不同；编码器塑造音频特征 |
| 聊天 / 推理 | 不要，decoder-only | 没有固定的「输入」——对话本身就是序列 |
| 代码补全 | 通常不要 | 长上下文 decoder-only 胜出；Qwen 2.5 Coder 这类代码模型都是 decoder-only |
| 摘要 | 都行 | BART、PEGASUS 打败过早期 decoder-only 基线；现代 decoder-only LLM 已追平 |
| 结构化抽取 | 都行 | T5 很干净，因为「文本 → 文本」能吸收任何输出格式 |

2022 年前后的趋势：decoder-only 接管了 encoder-decoder 曾经的地盘，因为 (a) 指令微调的 decoder-only LLM 靠 prompt 就能泛化到任何任务，(b) 一种架构比两种更好扩展，(c) RLHF 以解码器为前提。encoder-decoder 守住了输入模态不同（语音、图像）或 beam search 质量重要的地方。

```figure
encoder-decoder
```

> The trend since ~2022: decoder-only takes over tasks that encoder-decoder used to own because (a) instruction-tuned decoder-only LLMs generalize to anything via prompting, (b) one architecture scales easier than two, (c) RLHF assumes a decoder. Encoder-decoder holds on where input modality differs (speech, images) or where beam search quality matters.

## Build It · 动手造

见 `code/main.py`。我们为玩具语料实现 T5 式的 span corruption——本课最有用的单独一块，因为从那以后的每个 encoder-decoder 预训练配方里都有它。

> See `code/main.py`. We implement T5-style span corruption for a toy corpus — the most useful single piece of this lesson because it shows up in every encoder-decoder pretraining recipe since.

### Step 1: span corruption · 第 1 步：span corruption

```python
def corrupt_spans(tokens, mask_rate=0.15, mean_span=3.0, rng=None):
    """Pick spans summing to ~mask_rate of tokens. Return (corrupted_input, target)."""
    n = len(tokens)
    n_mask = max(1, int(n * mask_rate))
    n_spans = max(1, int(round(n_mask / mean_span)))
    ...
```

目标格式遵循 T5 约定：`<sent0> span0 <sent1> span1 ...`。弄坏的输入把未改动的 token 与片段位置上的哨兵 token 交错排列。

> The target format is the T5 convention: `<sent0> span0 <sent1> span1 ...`. The corrupted input interleaves unchanged tokens with the sentinel tokens at span locations.

### Step 2: verify round-trip · 第 2 步：验证往返还原

给定弄坏的输入和目标，重建原句。如果你的损坏是可逆的，前向计算就是良定义的。这是个 sanity check——真实训练从不这么做，但这个测试很便宜，能抓住片段记录里的 off-by-one bug。

> Given the corrupted input and target, reconstruct the original sentence. If your corruption is reversible, the forward pass is well-defined. This is a sanity check — real training never does this, but the test is cheap and catches off-by-one bugs in your span bookkeeping.

### Step 3: BART noising · 第 3 步：BART 加噪

五个函数：`token_mask`、`token_delete`、`text_infill`、`sentence_permute`、`document_rotate`。任选两个组合，展示结果。

> Five functions: `token_mask`, `token_delete`, `text_infill`, `sentence_permute`, `document_rotate`. Compose two of them and show the result.

## Use It · 实战用法

HuggingFace 参考：

```python
from transformers import T5ForConditionalGeneration, T5Tokenizer
tok = T5Tokenizer.from_pretrained("google/flan-t5-base")
model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-base")

inputs = tok("translate English to French: Attention is all you need.", return_tensors="pt")
out = model.generate(**inputs, max_new_tokens=32)
print(tok.decode(out[0], skip_special_tokens=True))
```

T5 的把戏：任务名写进输入文本。同一个模型处理几十个任务，因为每个任务都是文本进、文本出。2026 年这个模式已被指令微调的 decoder-only 模型泛化，但 T5 是第一个把它定型的。

> HuggingFace reference:
> The T5 trick: the task name goes into the input text. Same model handles dozens of tasks because each task is text-in, text-out. In 2026 this pattern has been generalized by instruction-tuned decoder-only models, but T5 codified it first.

## Ship It · 交付

见 `outputs/skill-seq2seq-picker.md`。这个 skill 依据输入-输出结构、延迟和质量目标，为新任务在 encoder-decoder 与 decoder-only 之间做选择。

> See `outputs/skill-seq2seq-picker.md`. The skill picks between encoder-decoder and decoder-only for a new task given input-output structure, latency, and quality targets.

## Exercises · 练习

1. **简单。** 跑 `code/main.py`，对一个 30-token 句子应用 span corruption，验证「非哨兵源 token + 解码出的目标片段」拼接后能还原原句。
2. **中等。** 实现 BART 的 `text_infill` 噪声：把随机片段替换成单个 `<mask>` token，解码器必须推断出正确的片段长度和内容。展示一个例子。
3. **困难。** 在一个微型的英语 → 儿童黑话（pig-Latin）语料（200 对）上微调 `flan-t5-small`。在留出的 50 对上测 BLEU。与在同样数据、同样算力下微调 `Llama-3.2-1B` 对比。

> 1. **Easy.** Run `code/main.py`, apply span corruption to a 30-token sentence, verify that concatenating the non-sentinel source tokens with the decoded target spans reproduces the original.
> 2. **Medium.** Implement BART's `text_infill` noise: replace random spans with a single `<mask>` token, and the decoder must infer the correct span length plus contents. Show one example.
> 3. **Hard.** Fine-tune `flan-t5-small` on a tiny English → pig-Latin corpus (200 pairs). Measure BLEU on a held-out 50-pair set. Compare against fine-tuning `Llama-3.2-1B` on the same data with the same compute.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------|---------|
| Encoder-decoder | 「Seq2seq transformer」 | 两个堆叠：输入用双向编码器，输出用带交叉注意力的因果解码器。 |
| Cross-attention（交叉注意力） | 「源和目标对话的地方」 | 解码器的 Q × 编码器的 K/V。编码器信息进入解码器的唯一通道。 |
| Span corruption | 「T5 的预训练把戏」 | 用哨兵 token 替换随机片段；解码器输出这些片段。 |
| Denoising objective（去噪目标） | 「BART 的玩法」 | 对输入施加噪声函数，训练解码器重建干净序列。 |
| Sentinel token（哨兵 token） | 「`<extra_id_N>` 占位符」 | 在源里标记被弄坏的片段、在目标里再标记一遍的特殊 token。 |
| Flan | 「指令微调的 T5」 | 在 >1,800 个任务上微调的 T5；让 encoder-decoder 在指令跟随上有竞争力。 |
| Beam search（束搜索） | 「解码策略」 | 每步保留 top-k 个部分序列；翻译 / 摘要的标准做法。 |
| Teacher forcing | 「训练期输入」 | 训练时喂给解码器真实的上一个输出 token，而不是采样出来的那个。 |

## Further Reading · 延伸阅读

- [Raffel et al. (2019). Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer](https://arxiv.org/abs/1910.10683) —— T5。
- [Lewis et al. (2019). BART: Denoising Sequence-to-Sequence Pre-training for Natural Language Generation, Translation, and Comprehension](https://arxiv.org/abs/1910.13461) —— BART。
- [Chung et al. (2022). Scaling Instruction-Finetuned Language Models](https://arxiv.org/abs/2210.11416) —— Flan-T5。
- [Radford et al. (2022). Robust Speech Recognition via Large-Scale Weak Supervision](https://arxiv.org/abs/2212.04356) —— Whisper，2026 年 encoder-decoder 的典范。
- [HuggingFace `modeling_t5.py`](https://github.com/huggingface/transformers/blob/main/src/transformers/models/t5/modeling_t5.py) —— 参考实现。
