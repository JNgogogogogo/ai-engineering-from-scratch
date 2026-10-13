# Whisper — Architecture & Fine-Tuning · Whisper：架构与微调

> Whisper 是一个 30 秒窗口的 transformer 编码器-解码器，在 68 万小时多语言弱监督音频-文本对上训练。一套架构，多种任务，在 99 种语言上都鲁棒。它是 2026 年的参考 ASR。
>
> Whisper is a 30-second-window transformer encoder-decoder, trained on 680k hours of multilingual weakly-supervised audio-text pairs. One architecture, multiple tasks, robust across 99 languages. The 2026 reference ASR.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 6 · 04 (ASR), Phase 5 · 10 (Attention), Phase 7 · 05 (Full Transformer)
**Time:** ~75 minutes

## The Problem · 问题在哪

Whisper 由 OpenAI 于 2022 年 9 月发布，是第一个作为「商品」交付的 ASR 模型：贴入音频、得到文本，99 种语言，抗噪，笔记本电脑就能跑。到 2024 年，OpenAI 已推出 Large-v3 和 Turbo 变体；到 2026 年，从播客转写、语音助手到 YouTube 字幕，Whisper 都是一切任务的默认基线。

但 Whisper 不是一条你可以永远当黑盒对待的流水线。域偏移会杀死它——技术行话、说话人口音、专有名词、短片段、静音。你需要知道：

1. 它内部到底是什么。
2. 如何正确地喂给它分块的、流式的或长时长的音频。
3. 什么时候微调，以及怎么微调。

> Whisper, released by OpenAI in September 2022, was the first ASR model to ship as a commodity: paste audio, get text, 99 languages, robust to noise, runs on a laptop. By 2024 OpenAI had shipped Large-v3 and Turbo variants; by 2026, Whisper is the default baseline for everything from podcast transcription to voice assistants to YouTube subtitles.
> But Whisper is not a pipeline you can treat as a black box forever. Domain shift kills it — technical jargon, speaker accents, proper nouns, short clips, silence.

## The Concept · 概念

![Whisper 编码器-解码器、任务、分块推理、微调](../assets/whisper.svg)

**架构**。标准的 transformer 编码器-解码器。

- 输入：30 秒 log-mel 频谱图，80 维梅尔，10 ms 帧移 → 3000 帧。短于此的片段补零，长于此的分块。
- 编码器：卷积下采样（stride 2）+ `N` 个 transformer 块。Large-v3：32 层、1280 维、20 头。
- 解码器：`N` 个 transformer 块，带因果自注意力 + 对编码器输出的交叉注意力。规模与编码器相同。
- 输出：5 万余 token 词表上的 BPE token。

Large-v3 有 1.55B 参数。Turbo 用 4 层解码器（原本 32 层），把延迟降到 1/8，WER 代价不足 1%。

**提示词格式（prompt format）**。Whisper 是一个多任务模型，由解码器提示中的特殊 token 控制：

```
<|startoftranscript|><|en|><|transcribe|><|notimestamps|> Hello world.<|endoftext|>
```

- `<|en|>` —— 语言标签；决定任务走向翻译还是转写。
- `<|transcribe|>` 或 `<|translate|>` —— 把任意语言输入翻成英文输出，或逐字转写。
- `<|notimestamps|>` —— 跳过词级时间戳（更快）。

提示词正是让一个模型干多种活的关键。把 `<|en|>` 换成 `<|fr|>`，它就转写法语。

**30 秒窗口**。一切都钉死在 30 秒上。更长的音频要分块；更短的要补齐。窗口本身不支持原生流式——这正是 WhisperX、Whisper-Streaming 和 faster-whisper 存在的原因。

**log-mel 归一化**。`(log_mel - mean) / std`，统计量来自 Whisper 自己的训练语料。你*必须*使用 Whisper 的预处理（`whisper.audio.log_mel_spectrogram`），而不是 `librosa.feature.melspectrogram`。

> **Architecture.** Standard transformer encoder-decoder. Input: 30-second log-mel spectrogram, 80 mels, 10 ms hop → 3000 frames. Clips shorter are zero-padded, clips longer are chunked.
> Large-v3 has 1.55B params. Turbo uses a 4-layer decoder (from 32), cutting latency 8× with a <1% WER hit.
> **The prompt format.** Whisper is a multitask model steered by special tokens in the decoder prompt. The prompt is what lets one model do many tasks. Change `<|en|>` to `<|fr|>` and it transcribes French.
> **30-second window.** Everything is pinned to 30 seconds. Longer clips need chunking; shorter clips are padded. Windows are not streamed natively — this is why WhisperX, Whisper-Streaming, and faster-whisper exist.
> **Log-mel normalization.** `(log_mel - mean) / std` where the stats come from Whisper's own training corpus. You *must* use Whisper's preprocessing (`whisper.audio.log_mel_spectrogram`), not `librosa.feature.melspectrogram`.

### Variants in 2026 · 2026 年的各变体

| 变体 | 参数量 | 延迟 (A100) | WER (LibriSpeech-clean) |
|---------|--------|----------------|------------------------|
| Tiny | 39M | 1× 实时 | 5.4% |
| Base | 74M | 1× | 4.1% |
| Small | 244M | 1× | 3.0% |
| Medium | 769M | 1× | 2.7% |
| Large-v3 | 1.55B | 2× | 1.8% |
| Large-v3-turbo | 809M | 8× | 1.58% |
| Whisper-Streaming (2024) | 1.55B | 流式 | 2.0% |

### Fine-tuning · 微调

2026 年的标准工作流：

1. 收集 10–100 小时带对齐转写的目标领域音频。
2. 运行 `transformers.Seq2SeqTrainer`，配合 `generate_with_loss` 回调。
3. 参数高效路线：在注意力层的 `q_proj`、`k_proj`、`v_proj` 上加 LoRA，显存省 4 倍，WER 代价低于 0.3。
4. 数据少于 10 小时就冻结编码器，只调解码器。
5. 用 Whisper 自己的 tokenizer 和提示词格式；绝不更换 tokenizer。

社区结果：在 20 小时医疗听写数据上微调 Medium，医疗词汇的 WER 从 12% 降到 4.5%。在 4 小时冰岛语数据上微调 Turbo，WER 从 18% 降到 6%。

> Canonical workflow in 2026: Collect 10–100 hours of target-domain audio with aligned transcripts. Run `transformers.Seq2SeqTrainer` with `generate_with_loss` callback. Parameter-efficient: LoRA on `q_proj`, `k_proj`, `v_proj` of attention layers reduces GPU memory 4× with <0.3 WER cost. Freeze the encoder if you have <10 hours. Only tune the decoder. Use Whisper's own tokenizer and prompt format; never swap tokenizers.
> Community results: fine-tuning Medium on 20 hours of medical dictation drops WER from 12% to 4.5% on medical vocabulary. Fine-tuning Turbo on 4 hours of Icelandic drops WER from 18% to 6%.

```figure
sp-asr-attention
```

## Build It · 动手造

### Step 1: run Whisper out of the box · 开箱即用地跑 Whisper

```python
import whisper
model = whisper.load_model("large-v3-turbo")
result = model.transcribe(
    "clip.wav",
    language="en",
    task="transcribe",
    temperature=0.0,
    condition_on_previous_text=False,  # prevents runaway repetition
)
print(result["text"])
for seg in result["segments"]:
    print(f"[{seg['start']:.2f}–{seg['end']:.2f}] {seg['text']}")
```

你几乎总是应该显式覆盖的默认值：`temperature=0.0`（采样默认走 0.0 → 0.2 → 0.4 … 的回退链）、`condition_on_previous_text=False`（防止级联幻觉问题）、`no_speech_threshold=0.6`（静音检测）。

> Key defaults you should always override: `temperature=0.0` (sampling defaults to 0.0 → 0.2 → 0.4 … fallback chain), `condition_on_previous_text=False` (prevents the cascading hallucination problem), and `no_speech_threshold=0.6` (silence detection).

### Step 2: chunked long-form · 分块处理长音频

```python
# whisperx is the 2026 reference for long-form with word-level timestamps
import whisperx
model = whisperx.load_model("large-v3-turbo", device="cuda", compute_type="float16")
segments = model.transcribe("1hour.mp3", batch_size=16, chunk_size=30)
```

WhisperX 增加了 (1) Silero VAD 门控，(2) 基于 wav2vec 2.0 的词级对齐，(3) 基于 `pyannote.audio` 的说话人分离。这是 2026 年生产转写的主力工具。

> WhisperX adds (1) Silero VAD gating, (2) word-level alignment via wav2vec 2.0, (3) diarization via `pyannote.audio`. The 2026 workhorse for production transcription.

### Step 3: fine-tune with LoRA · 用 LoRA 微调

```python
from transformers import WhisperForConditionalGeneration, WhisperProcessor
from peft import LoraConfig, get_peft_model

model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-large-v3-turbo")
lora = LoraConfig(
    r=16, lora_alpha=32, target_modules=["q_proj", "v_proj"],
    lora_dropout=0.1, bias="none", task_type="SEQ_2_SEQ_LM",
)
model = get_peft_model(model, lora)
# model.print_trainable_parameters()  -> ~3M trainable / 809M total
```

然后就是标准的 Trainer 循环。每 1000 步存一次 checkpoint。在留出集上用 WER 评估。

> Then standard Trainer loop. Checkpoint every 1000 steps. Evaluate with WER on held-out.

### Step 4: inspect what each layer learns · 观察每一层学到了什么

```python
# Grab cross-attention weights during decode to see what the decoder attends to.
with torch.inference_mode():
    out = model.generate(
        input_features=features,
        return_dict_in_generate=True,
        output_attentions=True,
    )
# out.cross_attentions: layer × head × step × src_len
```

用热力图可视化——你会看到解码器逐帧扫过编码器时形成对角对齐。那条对角线就是 Whisper 对词级时间戳的表达。

> Visualize with a heatmap — you will see diagonal alignment as decoder steps scan through encoder frames. That diagonal is Whisper's notion of word timestamps.

## Use It · 实战用法

2026 年的技术栈：

| 场景 | 选择 |
|-----------|------|
| 通用英语、离线 | 通过 `whisperx` 用 Large-v3-turbo |
| 移动 / 边缘 | Whisper-Tiny 量化版（int8）或 Moonshine |
| 多语言长音频 | 通过 `whisperx` 用 Large-v3 + 说话人分离 |
| 低资源语言 | 用 LoRA 微调 Medium 或 Turbo |
| 流式（2 秒延迟） | Whisper-Streaming 或 Parakeet-TDT |
| 词级时间戳 | WhisperX（通过 wav2vec 2.0 强制对齐） |

`faster-whisper`（CTranslate2 后端）是 2026 年最快的 CPU+GPU 推理运行时——比原版快 4 倍，输出完全一致。

> `faster-whisper` (CTranslate2 backend) is the fastest CPU+GPU inference runtime in 2026 — 4× faster than vanilla with identical output.

## Pitfalls that still ship in 2026 · 2026 年仍在发生的坑

- **静音上产生幻觉文本。** Whisper 在字幕数据上训练，会吐出 "Thanks for watching!"、"Subscribe!"、歌词。调用前一定先用 VAD 门控。
- **`condition_on_previous_text` 级联。** 一处幻觉会污染后续所有窗口。除非你需要跨块的连贯性，否则设为 `False`。
- **短片段补齐。** 2 秒片段补到 30 秒，可能在末尾静音里产生幻觉。用 `pad=False` 或 VAD 门控。
- **梅尔统计量用错。** 用 librosa 的梅尔而不是 Whisper 的，会得到近乎随机的输出。用 `whisper.audio.log_mel_spectrogram`。

> **Hallucinated text on silence.** Whisper trained on captions includes "Thanks for watching!", "Subscribe!", song lyrics. Always VAD-gate before calling.
> **`condition_on_previous_text` cascade.** One hallucination pollutes subsequent windows. Set `False` unless you need fluency across chunks.
> **Short-clip padding.** A 2-second clip padded to 30 seconds can hallucinate in the trailing silence. Use `pad=False` or VAD-gate.
> **Wrong mel stats.** Using librosa's mels instead of Whisper's produces near-random output. Use `whisper.audio.log_mel_spectrogram`.

## Ship It · 交付

保存为 `outputs/skill-whisper-tuner.md`。为给定领域设计 Whisper 微调或推理流水线。

> Save as `outputs/skill-whisper-tuner.md`. Design a Whisper fine-tune or inference pipeline for a given domain.

## Exercises · 练习

1. **简单。** 运行 `code/main.py`。它对一个 Whisper 风格的提示词做分词，计算解码后的形状预算，并打印 10 分钟音频的分块调度。
2. **中等。** 安装 `faster-whisper`，转写一段 10 分钟的播客，对照人工转写计算 WER。试试 `language="auto"` 与强制 `language="en"` 的差别。
3. **困难。** 用 HF `datasets` 挑一种 Whisper 不擅长的语言（如乌尔都语），在 2 小时数据上用 LoRA 微调 Medium 两轮，报告 WER 变化。

## Key Terms · 术语表

| 术语 | 人们怎么说 | 它实际上是什么意思 |
|------|-----------------|-----------------------|
| 30 秒窗口（30-sec window） | Whisper 的限制 | 硬性输入上限；更长的音频要分块。 |
| SOT | 句首标记 | `<\|startoftranscript\|>` 开启解码器提示。 |
| 时间戳 token | 时间对齐 | 每 0.02 s 偏移都是 5.1 万词表里的一个特殊 token。 |
| Turbo | 快速变体 | 4 层解码器，快 8 倍，WER 回退不足 1%。 |
| WhisperX | 长音频封装 | VAD + Whisper + wav2vec 对齐 + 说话人分离。 |
| LoRA 微调 | 高效调参 | 在注意力上加低秩适配器；只训练约 0.3% 参数。 |
| 幻觉（Hallucination） | 静默失败 | Whisper 从噪声/静音里生成流畅英语。 |

## Further Reading · 延伸阅读

- [Radford et al. (2022). Whisper paper](https://arxiv.org/abs/2212.04356) —— 原始架构与训练配方。
- [OpenAI (2024). Whisper Large-v3-turbo release](https://github.com/openai/whisper/discussions/2363) —— 4 层解码器，8 倍加速。
- [Bain et al. (2023). WhisperX](https://arxiv.org/abs/2303.00747) —— 长音频、词对齐、说话人分离。
- [Systran — faster-whisper repo](https://github.com/SYSTRAN/faster-whisper) —— CTranslate2 加持，快 4 倍。
- [HuggingFace — Whisper fine-tune tutorial](https://huggingface.co/blog/fine-tune-whisper) —— 权威的 LoRA / 全量微调教程。
