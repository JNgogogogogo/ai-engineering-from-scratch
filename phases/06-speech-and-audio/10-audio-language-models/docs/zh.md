# Audio-Language Models — Qwen2.5-Omni, Audio Flamingo, GPT-4o Audio · 音频语言模型——Qwen2.5-Omni、Audio Flamingo、GPT-4o Audio

> 2026 audio-language models reason over speech + environmental sound + music. Qwen2.5-Omni-7B matches GPT-4o Audio on MMAU-Pro. Audio Flamingo Next beats Gemini 2.5 Pro on LongAudioBench. The gap between open and closed is essentially closed — except on multi-audio tasks, where everyone is near random.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 6 · 04 (ASR), Phase 12 · 03 (Vision-Language Models), Phase 7 · 10 (Audio Transformers)
**Time:** ~45 minutes

---

## The Problem · 问题在哪

你有 5 秒音频：狗叫、有人喊 "stop!"、然后一片安静。有用的问题横跨多个维度：

- **转写。** "What was said?"（说了什么？）—— ASR 的地盘。
- **语义推理。** "这个人有危险吗？" —— 需要联合理解狗叫 + 喊叫 + 安静。
- **音乐推理。** "旋律是由哪些乐器演奏的？"
- **长音频检索。** "这节 90 分钟的课里，老师在哪儿讲了梯度下降？"

一个能用同一条提示回答以上所有问题的模型，就是**音频语言模型（audio-language model，LALM / ALM）**。它与纯 ASR 是两回事：LALM 产出自由格式的自然语言回答，而不只是转写。

> You have 5 seconds of audio: dog barks, someone yells "stop!", then silence. Useful questions span multiple axes:
> A single model that answers all of these with one prompt is an **audio-language model** (LALM / ALM). Separate from pure ASR: LALMs produce free-form natural-language answers, not just transcripts.

---

## The Concept · 概念

![音频语言模型：音频编码器 + 投影器 + LLM 解码器](../assets/alm-architecture.svg)

### The three-component template · 三组件模板

2026 年的每个 LALM 都是同一副骨架：

1. **音频编码器。** Whisper encoder · BEATs · CLAP · WavLM · 或模型自带的定制编码器。
2. **投影器（projector）。** 线性层或 MLP，把音频编码器特征桥接进 LLM 的 token 嵌入空间。
3. **LLM。** Llama / Qwen / Gemma 系解码器。接收交错的文本 + 音频 token；生成文本。

训练：

- **阶段 1。** 冻结编码器 + LLM；只在 ASR / 描述（captioning）数据上训练投影器。
- **阶段 2。** 在指令跟随类音频任务（问答、推理、音乐理解）上做全量 / LoRA 微调。
- **阶段 3（可选）。** 语音进 / 语音出需要再加一个语音解码器。Qwen2.5-Omni 和 AF3-Chat 就这么做。

> Every 2026 LALM has the same skeleton:
> **Stage 1.** Freeze encoder + LLM; train projector only on ASR / captioning data.
> **Stage 2.** Full / LoRA fine-tune on instruction-following audio tasks (QA, reasoning, music understanding).
> **Stage 3 (optional).** Voice-in / voice-out adds a speech decoder. Qwen2.5-Omni and AF3-Chat do this.

---

### The 2026 model map · 2026 年模型地图

| 模型 | 骨干 | 音频编码器 | 输出模态 | 获取方式 |
|-------|----------|---------------|-----------------|--------|
| Qwen2.5-Omni-7B | Qwen2.5-7B | 自研 + Whisper | 文本 + 语音 | Apache-2.0 |
| Qwen3-Omni | Qwen3 | 自研 | 文本 + 语音 | Apache-2.0 |
| Audio Flamingo 3 | Qwen2 | AF-CLAP | 文本 | NVIDIA 非商业 |
| Audio Flamingo Next | Qwen2 | AF-CLAP v2 | 文本 | NVIDIA 非商业 |
| SALMONN | Vicuna | Whisper + BEATs | 文本 | Apache-2.0 |
| LTU / LTU-AS | Llama | CAV-MAE | 文本 | Apache-2.0 |
| GAMA | Llama | AST + Q-Former | 文本 | Apache-2.0 |
| Gemini 2.5 Flash/Pro（闭源） | Gemini | 专有 | 文本 + 语音 | API |
| GPT-4o Audio（闭源） | GPT-4o | 专有 | 文本 + 语音 | API |

---

### Benchmark reality check (2026) · 基准实测（2026）

**MMAU-Pro。** 1800 道问答，覆盖语音 / 环境声 / 音乐 / 混合。含多音频（multi-audio）子集。

| 模型 | 总分 | 语音 | 环境声 | 音乐 | 多音频 |
|-------|---------|--------|-------|-------|-------------|
| Gemini 2.5 Pro | ~60% | 73.4% | 51.9% | 64.9% | ~22% |
| Gemini 2.5 Flash | ~57% | 73.4% | 50.5% | 64.9% | 21.2% |
| GPT-4o Audio | 52.5% | — | — | — | 26.5% |
| Qwen2.5-Omni-7B | 52.2% | 57.4% | 47.6% | 61.5% | ~20% |
| Audio Flamingo 3 | ~54% | — | — | — | — |
| Audio Flamingo Next | LongAudioBench 上的 SOTA | — | — | — | — |

**多音频那一列对所有人都是当头一棒。** 四选一乱猜 = 25%；大多数模型就考在这个水平附近。让 LALM 比较两段音频，它们仍然做不到。

> **MMAU-Pro.** 1800 QA pairs covering speech / sound / music / mixed. Multi-audio subset included.
> The **multi-audio column is damning for everyone.** Random chance on 4-option multiple choice = 25%; most models score around there. LALMs still struggle to compare two clips.

---

### Where LALMs are useful in 2026 · 2026 年 LALM 的用武之地

- **呼叫中心录音的合规审计。** "Did the agent mention the required disclosure?"（坐席有没有提到必须的披露条款？）
- **无障碍。** 给听障用户描述声音事件（而不只是转写）。
- **内容审核。** 检测暴力语言 + 威胁性语气 + 背景语境。
- **播客 / 会议自动分段。** 语义层面的摘要，而不只是说话人轮次。
- **音乐曲库分析。** "Find all tracks with a B-section key change."（找出所有在 B 段转调的曲目。）

> **Compliance audit of call-center recordings.** "Did the agent mention the required disclosure?"
> **Accessibility.** Describe sound events to deaf users (not just transcription).
> **Content moderation.** Detect violent language + threatening tone + background context.
> **Music catalog analysis.** "Find all tracks with a B-section key change."

---

### Where they are NOT (yet) useful · 它们（暂时）不行的场景

- 细粒度音乐理论（和弦级以下）。
- 长对话中的说话人归属推理（超过 10 分钟就退化）。
- 多音频比较（22-26% 只比乱猜高一点点）。
- 实时流式推理（大多数还只是离线批量推理）。

> Fine-grained music theory (below chord-level).
> Speaker-attributed reasoning over long conversations (degrades past 10 minutes).
> Multi-audio comparison (22-26% is barely above random).
> Real-time streaming reasoning (most are offline batch inference).

```figure
v4-alm-tokens
```

---

## Build It · 动手造

### Step 1: query Qwen2.5-Omni · 查询 Qwen2.5-Omni

```python
from transformers import AutoModelForCausalLM, AutoProcessor

processor = AutoProcessor.from_pretrained("Qwen/Qwen2.5-Omni-7B")
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-Omni-7B", torch_dtype="auto")

audio, sr = load_wav("clip.wav", sr=16000)
messages = [{
    "role": "user",
    "content": [
        {"type": "audio", "audio": audio},
        {"type": "text", "text": "What sounds do you hear, and what's happening?"},
    ],
}]
inputs = processor.apply_chat_template(messages, tokenize=True, return_tensors="pt")
output = model.generate(**inputs, max_new_tokens=200)
print(processor.decode(output[0], skip_special_tokens=True))
```

### Step 2: the projector pattern · 投影器模式

```python
import torch.nn as nn

class AudioProjector(nn.Module):
    def __init__(self, audio_dim=1280, llm_dim=4096):
        super().__init__()
        self.down = nn.Linear(audio_dim, llm_dim)
        self.act = nn.GELU()
        self.up = nn.Linear(llm_dim, llm_dim)

    def forward(self, audio_features):
        return self.up(self.act(self.down(audio_features)))
```

就这么简单。投影器通常就是 1-3 个线性层。在 ASR 配对数据（音频 → 转写）上训练它，就是阶段 1 的前置任务（pretext task）。

> That's it. The projector is usually 1-3 linear layers. Training it on ASR pairs (audio → transcript) is the Stage-1 pretext task.

### Step 3: benchmarking MMAU / LongAudioBench · 跑 MMAU / LongAudioBench 基准

```python
from datasets import load_dataset
mmau = load_dataset("gamma-lab-umd/MMAU-Pro", split="test")
mcq = mmau.filter(lambda item: len(item["choices"] or []) > 1)

correct = 0
for item in mcq:
    answer = call_model(item["audio_path"], item["question"], item["choices"])
    if answer == item["answer"]:
        correct += 1
print(f"Accuracy: {correct / len(mcq):.3f}")
```

`audio_path` 指向数据集仓库里的 `data.zip`（约 47 GB），打分前要先下载并解压。这个精确匹配循环只是个健全性检查，不是正式的基准评分器，它的数字与已发表的 MMAU-Pro 结果不可比。官方评测器用嵌入相似度（NV-Embed-v2）匹配多选题答案，用 LLM 评审给开放式答案打分，并用正则规则检查指令跟随类答案：把预测写进 `model_output` 列，然后运行 [MMAU-Pro 仓库](https://github.com/sonalkum/MMAUPro)里的 `evaluate_mmau_pro_comprehensive.py`。每个 `category`（speech、sound、music、multi 及其余）分开报告。聚合数字会掩盖模型在哪里失败。

> `audio_path` points into the dataset repo's `data.zip` (about 47 GB), so download and unzip it before scoring. ... The official evaluator matches multiple-choice answers by embedding similarity (NV-Embed-v2), grades open-ended answers with an LLM judge, and checks instruction-following answers with regex rules: write predictions to a `model_output` column and run `evaluate_mmau_pro_comprehensive.py` from the [MMAU-Pro repo](https://github.com/sonalkum/MMAUPro). ... Aggregate numbers hide where the model fails.

---

## Use It · 实战用法

| 任务 | 2026 年之选 |
|------|-----------|
| 自由格式音频问答（开源） | Qwen2.5-Omni-7B |
| 开源长音频最佳 | Audio Flamingo Next |
| 闭源最佳 | Gemini 2.5 Pro |
| 语音进 / 语音出智能体 | Qwen2.5-Omni 或 GPT-4o Audio |
| 音乐推理 | Audio Flamingo 3 或 2（音乐专精的 AF-CLAP） |
| 呼叫中心审计 | 经 API 用 Gemini 2.5 Pro，并在你的制度文档上做 RAG |

---

## Pitfalls · 常见的坑

- **对多音频过度信任。** 如果你的任务是「哪段音频里有 X」，乱猜水平的性能是真实存在的。
- **长音频退化。** 超过 10 分钟，大多数模型的说话人归属就崩了。先做说话人分离（diarization，第 6 课），再做摘要。
- **静音上的幻觉。** Whisper 的老毛病，被用 Whisper 编码器的 LALM 原样继承。加 VAD 门控。
- **基准挑选性引用。** 厂商博客只晒最好的类别。自己跑一遍 MMAU-Pro 的多音频子集。

> **Over-trust on multi-audio.** If your task needs "which clip has X," random-chance-level performance is real.
> **Long-audio degradation.** Past 10 minutes, most models' speaker attribution breaks. Diarize first (Lesson 6), then summarize.
> **Hallucinations on silence.** Same Whisper-style issue inherited by LALMs that use Whisper encoder. VAD-gate.
> **Benchmark cherry-picking.** Vendor blog posts highlight best-case categories. Run MMAU-Pro multi-audio subset yourself.

---

## Ship It · 交付

保存为 `outputs/skill-alm-picker.md`：针对给定的音频理解任务，选定 LALM + 基准子集 + 输出模态（文本 vs 语音）。

> Save as `outputs/skill-alm-picker.md`. Pick LALM + benchmark subset + output-modality (text vs speech) for a given audio-understanding task.

---

## Exercises · 练习

1. **简单。** 运行 `code/main.py`，看一个玩具投影器模式 + 假 LALM 对（音频嵌入，文本 token）→ 输出 token 的路由。
2. **中等。** 在 100 条 MMAU-Pro 语音题上给 Qwen2.5-Omni-7B 打分，与论文报告值对比。
3. **困难。** 搭一个最小的音频描述基线：BEATs 编码器 + 2 层投影器 + 冻结的 Llama-3.2-1B。只在 AudioCaps 上微调投影器，在 Clotho-AQA 上与 SALMONN 对比。

> 1. **Easy.** Run `code/main.py` to see a toy projector pattern + fake LALM routing of (audio-embedding, text-tokens) → output tokens.
> 2. **Medium.** Score Qwen2.5-Omni-7B on 100 MMAU-Pro speech items. Compare to the paper's reported number.
> 3. **Hard.** Build a minimal audio-captioning baseline: BEATs encoder + 2-layer projector + frozen Llama-3.2-1B. Fine-tune only the projector on AudioCaps. Compare to SALMONN on Clotho-AQA.

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| LALM | 音频版 ChatGPT | 音频编码器 + 投影器 + LLM 解码器。 |
| Projector（投影器） | 适配器 | 把音频特征映射进 LLM 嵌入空间的小 MLP。 |
| MMAU | 那个基准 | 覆盖语音、环境声、音乐的 1 万条音频问答对。 |
| MMAU-Pro | 更难的 MMAU | 1800 道多音频 / 重推理题。 |
| LongAudioBench | 长音频评测 | 多分钟长片段 + 语义查询。 |
| Voice-in / voice-out | 语音原生 | 模型直接吃语音、吐语音，不绕道文本。 |

---

## Further Reading · 延伸阅读

- [Chu et al. (2024). Qwen2-Audio](https://arxiv.org/abs/2407.10759) —— 参考架构。
- [Alibaba (2025). Qwen2.5-Omni](https://huggingface.co/Qwen/Qwen2.5-Omni-7B) —— 语音进语音出。
- [NVIDIA (2025). Audio Flamingo 3](https://arxiv.org/abs/2507.08128) —— 开源长音频领头羊。
- [NVIDIA (2026). Audio Flamingo Next](https://arxiv.org/abs/2604.10905) —— LongAudioBench SOTA。
- [Tang et al. (2023). SALMONN](https://arxiv.org/abs/2310.13289) —— 双编码器先驱。
- [MMAU-Pro leaderboard](https://sonalkum.github.io/mmau-pro/) —— 2026 年实时排行。
