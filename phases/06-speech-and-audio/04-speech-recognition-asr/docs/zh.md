# Speech Recognition (ASR) — CTC, RNN-T, Attention · 语音识别（ASR）：CTC、RNN-T 与注意力

> 语音识别就是把音频分类做到每一个时间步，再用一个懂语言、也懂静音的序列模型把它们粘起来。CTC、RNN-T 和注意力是三条实现路径。选一条，并弄明白为什么。
>
> Speech recognition is audio classification at every timestep, glued together by a sequence model that knows English and silence. CTC, RNN-T, and attention are the three ways to do it. Pick one and understand why.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 6 · 02 (Spectrograms & Mel), Phase 5 · 08 (CNNs & RNNs for Text), Phase 5 · 10 (Attention)
**Time:** ~45 minutes

## The Problem · 问题在哪

你有一段 10 秒的 16 kHz 音频，想要一个字符串："turn on the kitchen lights"。难点是结构性的：音频帧和字符不是一对一对应的。"okay" 这个词可能占 200 ms，也可能占 1200 ms。静音穿插在语句中间，有的音素比别的长，输出 token 的数量事先并不知道。

三种建模方式解决这个问题：

1. **CTC（Connectionist Temporal Classification，联结主义时序分类）。** 输出每帧的 token 概率，其中包含一个特殊的 *blank*。解码时折叠重复、去掉 blank。非自回归，速度快。wav2vec 2.0、MMS 使用它。
2. **RNN-T（Recurrent Neural Network Transducer，循环神经网络转换器）。** 联合网络根据编码器帧和已生成的 token 预测下一个 token。可流式。Google 的端侧 ASR、NVIDIA Parakeet 使用它。
3. **注意力编码器-解码器。** 编码器把音频压缩成隐藏状态，解码器交叉注意力、自回归地生成 token。Whisper、SeamlessM4T 使用它。

2026 年，LibriSpeech test-clean 上的 SOTA WER 是 1.4%（Parakeet-TDT-1.1B，NVIDIA）和 1.58%（Whisper-Large-v3-turbo）。模型之间的差距微乎其微，部署方式的差距却天壤之别。

> You have a 10-second 16 kHz clip. You want a string: "turn on the kitchen lights". The challenge is structural: audio frames do not align one-to-one with characters. The word "okay" might take 200 ms or 1200 ms. Silence punctuates the utterance. Some phonemes are longer than others. The number of output tokens is not known in advance.
> **CTC (Connectionist Temporal Classification).** Emit per-frame token probabilities including a special *blank*. Collapse repeats and blanks at decode time. Non-autoregressive, fast. Used by wav2vec 2.0, MMS.
> **RNN-T (Recurrent Neural Network Transducer).** Joint network predicts next token given encoder frame and previous tokens. Streamable. Used by Google's on-device ASR, NVIDIA Parakeet.
> **Attention encoder-decoder.** Encoder compresses audio to hidden states, decoder cross-attends to generate tokens autoregressively. Used by Whisper, SeamlessM4T.
> In 2026, SOTA WER on LibriSpeech test-clean is 1.4% (Parakeet-TDT-1.1B, NVIDIA) and 1.58% (Whisper-Large-v3-turbo). The differences are tiny; the deployment differences are huge.

## The Concept · 概念

![三种 ASR 建模方式：CTC、RNN-T、注意力编码器-解码器](../assets/asr-formulations.svg)

**CTC 直觉**。让编码器对 `V+1` 个 token（V 个字符 + blank）输出 `T` 个帧级分布。对长度为 `U < T` 的目标串 `y`，任何折叠后等于 `y` 的帧对齐都算数。CTC 损失对所有这些对齐求和。推理：逐帧取 argmax，折叠重复，去掉 blank。

优点：非自回归、可流式、零前瞻。缺点：*条件独立假设*——每一帧的预测彼此独立，因此内部没有语言模型。补救办法是配合外部语言模型做 beam search 或浅融合（shallow fusion）。

**RNN-T 直觉**。增加一个*预测器（predictor）*网络来嵌入 token 历史，再加一个*联合器（joiner）*把预测器状态与编码器帧合并成 `V+1` 上的联合分布（`+1` 是一个空发射 / null）。它显式建模了 CTC 忽略的条件依赖。可流式，因为每一步只依赖过去的帧和过去的 token。

优点：可流式 + 内置语言模型。缺点：训练更复杂、更吃内存（3D 损失格）；RNN-T 损失内核自成一类库。

**注意力编码器-解码器**。编码器（6-32 层 transformer）作用于 log-mel 帧。解码器（6-32 层 transformer）对编码器输出做交叉注意力，自回归生成 token。没有对齐约束——注意力可以看音频的任何位置。除非限制注意力（分块的 Whisper-Streaming，2024），否则无法流式。

优点：离线 ASR 质量最高，用标准 seq2seq 工具就容易训练。缺点：自回归延迟与输出长度成正比；不做工程改造就无法流式。

> **CTC intuition.** Let the encoder output `T` frame-level distributions over `V+1` tokens (V chars + blank). For a target string `y` of length `U < T`, any frame alignment that collapses to `y` counts. CTC loss sums over all such alignments. Inference: per-frame argmax, collapse repeats, remove blanks.
> Drawback: *conditional independence assumption* — each frame prediction is independent of the others, so there is no internal language model.
> **RNN-T intuition.** Adds a *predictor* network that embeds the token history and a *joiner* that combines predictor state with encoder frame into a joint distribution over `V+1` (the `+1` is a null / no-emit). Explicitly models the conditional dependence CTC ignored.
> **Attention encoder-decoder.** ... No alignment constraint — attention can look anywhere in the audio. Non-streamable unless you restrict attention (chunked Whisper-Streaming, 2024).

### WER: the one number · WER：唯一重要的数字

**词错误率（Word Error Rate）** = `(S + D + I) / N`，其中 S=替换数、D=删除数、I=插入数、N=参考词数。等价于词级别的 Levenshtein 编辑距离。越低越好。WER 高于 20% 基本不可用；低于 5% 在朗读语音上达到人类水平。2026 年标准基准上的数字：

| 模型 | LibriSpeech test-clean | LibriSpeech test-other | 规模 |
|-------|------------------------|------------------------|------|
| Parakeet-TDT-1.1B | 1.40% | 2.78% | 1.1B params |
| Whisper-Large-v3-turbo | 1.58% | 3.03% | 809M |
| Canary-1B Flash | 1.48% | 2.87% | 1B |
| Seamless M4T v2 | 1.7% | 3.5% | 2.3B |

这些全是编码器-解码器或 RNN-T 架构。纯 CTC 系统（wav2vec 2.0）在 test-clean 上徘徊在 1.8–2.1%。

> **Word Error Rate** = `(S + D + I) / N`, where S=substitutions, D=deletions, I=insertions, N=reference word count. Matches Levenshtein edit distance at the word level. Lower is better. A WER above 20% is generally unusable; below 5% is human-parity for read speech.
> All these are encoder-decoder or RNN-T based. Pure CTC systems (wav2vec 2.0) sit around 1.8–2.1% on test-clean.

```figure
ctc-collapse
```

## Build It · 动手造

### Step 1: greedy CTC decode · 贪心 CTC 解码

```python
def ctc_greedy(frame_logits, blank=0, vocab=None):
    # frame_logits: list of per-frame probability vectors
    preds = [max(range(len(p)), key=lambda i: p[i]) for p in frame_logits]
    out = []
    prev = -1
    for p in preds:
        if p != prev and p != blank:
            out.append(p)
        prev = p
    return "".join(vocab[i] for i in out) if vocab else out
```

两条规则：折叠连续重复，丢弃 blank。示例：`a a _ _ a b b _ c` → `a a b c`。

> Two rules: collapse consecutive repeats, drop blanks. Example: `a a _ _ a b b _ c` → `a a b c`.

### Step 2: beam-search CTC · beam search 版 CTC

```python
def ctc_beam(frame_logits, beam=8, blank=0):
    import math
    beams = [([], 0.0)]  # (tokens, log_prob)
    for p in frame_logits:
        log_p = [math.log(max(pi, 1e-10)) for pi in p]
        candidates = []
        for seq, lp in beams:
            for t, lpt in enumerate(log_p):
                new = seq[:] if t == blank else (seq + [t] if not seq or seq[-1] != t else seq)
                candidates.append((new, lp + lpt))
        candidates.sort(key=lambda x: -x[1])
        beams = candidates[:beam]
    return beams[0][0]
```

生产环境使用带语言模型融合的前缀树 beam search；这里只是概念骨架。

> Production uses prefix tree beam search with LM fusion; this is the conceptual skeleton.

### Step 3: WER · 词错误率

```python
def wer(ref, hyp):
    r, h = ref.split(), hyp.split()
    dp = [[0] * (len(h) + 1) for _ in range(len(r) + 1)]
    for i in range(len(r) + 1):
        dp[i][0] = i
    for j in range(len(h) + 1):
        dp[0][j] = j
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            cost = 0 if r[i - 1] == h[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )
    return dp[len(r)][len(h)] / max(1, len(r))
```

### Step 4: inference against Whisper · 用 Whisper 做推理

```python
import whisper
model = whisper.load_model("large-v3-turbo")
result = model.transcribe("clip.wav")
print(result["text"])
```

一行代码调用 2026 年最强的通用 ASR。在 24 GB GPU 上以约 20 倍实时速度运行。

> One-liner for the strongest general ASR in 2026. Runs on a 24 GB GPU at ~20× realtime.

### Step 5: streaming with Parakeet or wav2vec 2.0 · 用 Parakeet 或 wav2vec 2.0 做流式识别

```python
from transformers import pipeline
asr = pipeline("automatic-speech-recognition", model="nvidia/parakeet-tdt-1.1b")
for chunk in streaming_audio():
    print(asr(chunk, return_timestamps=True))
```

流式 ASR 需要分块的编码器注意力和跨块状态；请使用支持它的库（Parakeet 用 NeMo，或带 `chunk_length_s` 的 `transformers` pipeline）。

> Streaming ASR needs chunked encoder attention and carryover state; use a library that supports it (NeMo for Parakeet, `transformers` pipeline with `chunk_length_s`).

## Use It · 实战用法

2026 年的技术栈：

| 场景 | 选择 |
|-----------|------|
| 英语、离线、最高质量 | Whisper-large-v3-turbo |
| 多语言、鲁棒 | SeamlessM4T v2 |
| 流式、低延迟 | Parakeet-TDT-1.1B 或 Riva |
| 边缘、移动端、<500 ms 延迟 | Whisper-Tiny 量化版或 Moonshine (2024) |
| 长音频 | Whisper + 基于 VAD 的分块（WhisperX） |
| 领域特定（医疗、法律） | 微调 wav2vec 2.0 + 领域语言模型融合 |

> English, offline, max quality → Whisper-large-v3-turbo. Multilingual, robust → SeamlessM4T v2. Streaming, low latency → Parakeet-TDT-1.1B or Riva. Edge, mobile, <500 ms latency → Whisper-Tiny quantized or Moonshine (2024). Long-form → Whisper with VAD-based chunking (WhisperX). Domain-specific (medical, legal) → Fine-tune wav2vec 2.0 + domain LM fusion.

## Pitfalls that still ship in 2026 · 2026 年仍在发生的坑

- **不用 VAD。** 对静音跑 Whisper 会产生幻觉（"Thanks for watching!"）。务必先用 VAD 门控。
- **字符级 vs 词级 vs 子词级 WER。** 在归一化（转小写、去标点）*之后*报告词级 WER。
- **语言识别漂移。** Whisper 的自动 LID 会把噪声片段误判成日语或威尔士语；当你知道语言时，强制 `language="en"`。
- **长音频不分块。** Whisper 只有 30 秒窗口。更长的音频用 `chunk_length_s=30, stride=5`。

> **No VAD.** Running Whisper on silence produces hallucinations ("Thanks for watching!"). Always gate with VAD.
> **Character vs word vs subword WER.** Report word-level WER *after* normalization (lowercase, punctuation stripped).
> **Language ID drift.** Whisper's auto LID mis-routes noisy clips to Japanese or Welsh; force `language="en"` when you know.
> **Long clips without chunking.** Whisper has a 30-second window. Use `chunk_length_s=30, stride=5` for anything longer.

## Ship It · 交付

保存为 `outputs/skill-asr-picker.md`。为给定的部署目标挑选模型、解码策略、分块方案和语言模型融合。

> Save as `outputs/skill-asr-picker.md`. Pick model, decoding strategy, chunking, and LM fusion for a given deployment target.

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。它对手工构造的 CTC 输出做贪心解码，并对照参考文本计算 WER。
2. **中等。** 把第 2 步的前缀树 beam search 实现完整（要处理 blank 的合并规则）。在一个 10 例合成数据集上与贪心解码对比。
3. **困难。** 用 `whisper-large-v3-turbo` 跑 [LibriSpeech test-clean](https://www.openslr.org/12)。在前 100 条语句上计算 WER，与已发表的数字对比。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 它实际上是什么意思 |
|------|-----------------|-----------------------|
| CTC | blank token 损失 | 对所有帧到 token 对齐求边际；非自回归。 |
| RNN-T | 流式损失 | CTC + 下一 token 预测器；能处理词序。 |
| Attention enc-dec | Whisper 那一类 | 编码器 + 交叉注意力解码器；离线质量最佳。 |
| WER | 你要上报的那个数 | 词级别的 `(S+D+I)/N`。 |
| Blank | 「空」 | CTC 里的特殊 token，表示「本帧不发射」。 |
| LM fusion | 外部语言模型 | 在 beam search 中加权加入语言模型的对数概率。 |
| VAD | 静音门 | 语音活动检测器；裁掉非语音段。 |

## Further Reading · 延伸阅读

- [Graves et al. (2006). Connectionist Temporal Classification](https://www.cs.toronto.edu/~graves/icml_2006.pdf) —— CTC 原始论文。
- [Graves (2012). Sequence Transduction with RNNs](https://arxiv.org/abs/1211.3711) —— RNN-T 原始论文。
- [Radford et al. / OpenAI (2022). Whisper: Robust Speech Recognition via Large-Scale Weak Supervision](https://arxiv.org/abs/2212.04356) —— 2022 年的权威论文；v3-turbo 是 2024 年的扩展。
- [NVIDIA NeMo — Parakeet-TDT card](https://huggingface.co/nvidia/parakeet-tdt-1.1b) —— 2026 年 Open ASR Leaderboard 榜首。
- [Hugging Face — Open ASR Leaderboard](https://huggingface.co/spaces/hf-audio/open_asr_leaderboard) —— 覆盖 25+ 模型的实时基准。
