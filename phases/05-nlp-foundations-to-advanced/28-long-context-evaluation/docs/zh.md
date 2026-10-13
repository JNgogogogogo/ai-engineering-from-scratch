# Long-Context Evaluation — NIAH, RULER, LongBench, MRCR · 长上下文评估——NIAH、RULER、LongBench、MRCR

> Gemini 3 Pro 宣称 1000 万 token 的上下文。而在 100 万 token 下，8 针 MRCR 掉到 26.3%。宣称的 ≠ 可用的。长上下文评估告诉你，你要托付的那个模型真实容量到底是多少。
>
> Gemini 3 Pro advertises 10M tokens of context. At 1M tokens, 8-needle MRCR drops to 26.3%. Advertised ≠ usable. Long-context evaluation tells you the actual capacity of the model you are shipping on.

**Type:** Learn
**Languages:** Python
**Prerequisites:** Phase 5 · 13 (Question Answering), Phase 5 · 23 (Chunking Strategies)
**Time:** ~60 minutes

## The Problem · 问题在哪

你手上有一份 200 页的合同。模型宣称 100 万 token 上下文。你把合同贴进去问："终止条款是什么？" 模型回答了——但答的是封面页的内容，因为终止条款埋在 12 万 token 深处，早就出了模型真正注意（attend）得到的范围。

这就是 2026 年的上下文容量鸿沟（context-capacity gap）。规格表写着 1M 或 10M，现实是有 60-70% 可用，而且「可用」取决于任务。

- **检索（大海捞针式单针）：** 旗舰模型在宣称上限之内接近满分。
- **多跳 / 聚合：** 大多数模型在约 128k 之后急剧退化。
- **对分散事实做推理：** 第一个倒下的任务。

长上下文评估度量的就是这些轴。本课点名各家用基准（benchmark），说明它们各自实际测什么，以及如何为你的领域造一个自定义「针」测试。

> This is the 2026 context-capacity gap. Spec sheets say 1M or 10M. Reality says 60-70% of that is usable, and "usable" depends on the task.
> Long-context evaluation measures these axes. This lesson names the benchmarks, what each actually measures, and how to build a custom needle test for your domain.

## The Concept · 概念

![NIAH 基线、RULER 多任务、LongBench 整体评估](../assets/long-context-eval.svg)

**Needle-in-a-Haystack（NIAH，2023，大海捞针）。** 在长上下文的可控深度处放一个事实（"the magic word is pineapple"），让模型把它检索出来。扫 depth × length。最早的长上下文基准。旗舰模型如今已经把它刷爆；它是必要但非充分的基线。

**RULER（Nvidia，2024）。** 4 大类 13 种任务：检索（单键 / 多键 / 多值）、多跳追踪（变量跟踪）、聚合（常见词频）、问答。上下文长度可配置（4k 到 128k+）。它能暴露那些刷爆 NIAH 却栽在多跳上的模型。2024 年发布时，17 个宣称支持 32k+ 上下文的模型里只有一半在 32k 保住了质量。

**LongBench v2（2024）。** 503 道多选题，8k-2M 词的上下文，六大任务类：单文档 QA、多文档 QA、长上下文学习（long in-context learning）、长对话、代码仓库、长结构化数据。真实世界长上下文行为的生产基准。

**MRCR（Multi-Round Coreference Resolution，多轮共指消解）。** 规模化的多轮共指。8 针、24 针、100 针变体。测的是模型在注意力退化之前能同时驾驭多少条事实。

**NoLiMa。** 「非词面针（non-lexical needle）」。针和问题之间没有任何字面重叠，检索需要一步语义推理。比 NIAH 难。

**HELMET。** 拼接许多文档，从其中任意一篇提问。测选择性注意。

**BABILong。** 把 bAbI 推理链埋进无关的填充文本里。测「草堆里的推理」，不只是检索。

### What to actually report · 实际要报告什么

- **宣称上下文窗口。** 规格表上的那个数字。
- **有效检索长度。** NIAH 在某个阈值（如 90%）以上通过的长度。
- **有效推理长度。** 多跳或聚合任务在该阈值上通过的长度。
- **退化曲线。** 准确率 vs 上下文长度，按任务类型分别画。

给你的规格表留两个数：检索有效（retrieval-effective）和推理有效（reasoning-effective）。通常推理有效只有宣称窗口的 25-50%。

```figure
gx-niah-decay
```

> Frontier models now saturate this; it is a necessary but not sufficient baseline. ... In the 2024 release, only half of 17 models claiming 32k+ context maintained quality at 32k. ... **Effective retrieval length.** NIAH pass at some threshold (e.g., 90%). ... Two numbers for your spec sheet: retrieval-effective and reasoning-effective. Usually the reasoning-effective is 25-50% of the advertised window.

## Build It · 动手造

### Step 1: a custom NIAH for your domain · 第 1 步：为你的领域定制 NIAH

见 `code/main.py`。骨架：

```python
def build_haystack(filler_text, needle, depth_ratio, total_tokens):
    if not (0.0 <= depth_ratio <= 1.0):
        raise ValueError(f"depth_ratio must be in [0, 1], got {depth_ratio}")
    if total_tokens <= 0:
        raise ValueError(f"total_tokens must be positive, got {total_tokens}")

    filler_tokens = tokenize(filler_text)
    needle_tokens = tokenize(needle)
    if not filler_tokens:
        raise ValueError("filler_text produced no tokens")

    # Repeat filler until long enough to fill the haystack body.
    body_len = max(total_tokens - len(needle_tokens), 0)
    while len(filler_tokens) < body_len:
        filler_tokens = filler_tokens + filler_tokens
    filler_tokens = filler_tokens[:body_len]

    insert_at = min(int(body_len * depth_ratio), body_len)
    haystack = filler_tokens[:insert_at] + needle_tokens + filler_tokens[insert_at:]
    return " ".join(haystack)


def score_niah(model, haystack, question, expected):
    answer = model.complete(f"Context: {haystack}\nQ: {question}\nA:", max_tokens=50)
    return 1 if expected.lower() in answer.lower() else 0
```

扫 `depth_ratio` ∈ {0, 0.25, 0.5, 0.75, 1.0} × `total_tokens` ∈ {1k, 4k, 16k, 64k}，画出热力图。这就是你的目标模型的 NIAH 卡片。

> Sweep `depth_ratio` ∈ {0, 0.25, 0.5, 0.75, 1.0} × `total_tokens` ∈ {1k, 4k, 16k, 64k}. Plot the heatmap. That is the NIAH card for your target model.

### Step 2: a multi-needle variant · 第 2 步：多针变体

```python
def build_multi_needle(filler, needles, total_tokens):
    depths = [0.1, 0.4, 0.7]
    chunks = [filler[:int(total_tokens * 0.1)]]
    for depth, needle in zip(depths, needles):
        chunks.append(needle)
        next_chunk = filler[int(total_tokens * depth): int(total_tokens * (depth + 0.3))]
        chunks.append(next_chunk)
    return " ".join(chunks)
```

像「三个魔法词分别是什么？」这样的问题，要求把三根针全部捞出来。单针成功预测不了多针成功。

> Questions like "What are the three magic words?" require retrieving all three. Single-needle success does not predict multi-needle success.

### Step 3: multi-hop variable tracing (RULER-style) · 第 3 步：多跳变量追踪（RULER 风格）

```python
haystack = """X1 = 42. ... (filler) ... X2 = X1 + 10. ... (filler) ... X3 = X2 * 2."""
question = "What is X3?"
```

答案要把三次赋值串起来。旗舰模型在 128k 时这里常常掉到 50-70% 准确率。

> The answer requires chaining three assignments. Frontier models at 128k often drop to 50-70% accuracy here.

### Step 4: LongBench v2 on your stack · 第 4 步：在你的技术栈上跑 LongBench v2

```python
from datasets import load_dataset
longbench = load_dataset("THUDM/LongBench-v2")

def eval_model_on_longbench(model, subset="single-doc-qa"):
    tasks = [x for x in longbench["test"] if x["task"] == subset]
    correct = 0
    for x in tasks:
        answer = model.complete(x["context"] + "\n\nQ: " + x["question"], max_tokens=20)
        if normalize(answer) == normalize(x["answer"]):
            correct += 1
    return correct / len(tasks)
```

按类别分别报告准确率。聚合分数会藏住任务级的巨大差异。

> Report per-category accuracy. Aggregate scores hide big task-level differences.

## Pitfalls · 常见的坑

- **只跑 NIAH。** 1M token 下 NIAH 通过，说明不了任何多跳能力。永远加跑 RULER 或自定义多跳测试。
- **均匀深度采样。** 很多实现只测 depth=0.5。要测 0、0.25、0.5、0.75、1.0——「lost in the middle」效应是真实存在的。
- **针与填充文本词面重叠。** 针要是和填充文本共享关键词，检索就变成送分题。用 NoLiMa 式无重叠的针。
- **忽视延迟。** 1M token 的提示词，预填充（prefill）要 30-120 秒。测准确率的同时测首 token 时间（time-to-first-token）。
- **厂商自报数字。** OpenAI、Google、Anthropic 都自己发榜。永远在你的用例上独立重跑。

> **NIAH-only evaluation.** Passing NIAH at 1M tokens says nothing about multi-hop. Always run RULER or a custom multi-hop test. ... **Uniform depth sampling.** Many implementations only test depth=0.5. Test depth=0, 0.25, 0.5, 0.75, 1.0 — the "lost in the middle" effect is real. ... **Vendor-self-reported numbers.** OpenAI, Google, Anthropic all publish their own scores. Always re-run independently on your use case.

## Use It · 实战用法

2026 年的选型表：

| 场景 | 基准 |
|-----------|-----------|
| 快速体检 | 自定义 NIAH，3 深度 × 3 长度 |
| 生产选型 | 在目标长度下跑 RULER（13 任务） |
| 真实世界 QA 质量 | LongBench v2 单文档 QA 子集 |
| 多跳推理 | BABILong 或自定义变量追踪 |
| 会话 / 对话 | 目标长度下 MRCR 8 针 |
| 模型升级回归 | 固定的内部 NIAH + RULER 治具，每个新模型都跑 |

生产经验法则：在你打算用的长度上跑过 NIAH + 1 个推理任务之前，别相信任何上下文窗口。

> Rule of thumb for production: never trust a context window until you have NIAH + 1 reasoning task at your intended length.

## Ship It · 交付

保存为 `outputs/skill-long-context-eval.md`：

```markdown
---
name: long-context-eval
description: Design a long-context evaluation battery for a given model and use case.
version: 1.0.0
phase: 5
lesson: 28
tags: [nlp, long-context, evaluation]
---

Given a target model, target context length, and use case, output:

1. Tests. NIAH depth × length grid; RULER multi-hop; custom domain task.
2. Sampling. Depths 0, 0.25, 0.5, 0.75, 1.0 at each length.
3. Metrics. Retrieval pass rate; reasoning pass rate; time-to-first-token; cost-per-query.
4. Cutoff. Effective retrieval length (90% pass) and effective reasoning length (70% pass). Report both.
5. Regression. Fixed harness, rerun on every model upgrade, surface deltas.

Refuse to trust a context window from the model card alone. Refuse NIAH-only evaluation for any multi-hop workload. Refuse vendor self-reported long-context scores as independent evidence.
```

> Save as `outputs/skill-long-context-eval.md`:

## Exercises · 练习

1. **简单。** 搭一个 3 深度（0.25、0.5、0.75）× 3 长度（1k、4k、16k）的 NIAH，随便找个模型跑，把通过率画成 3×3 热力图。
2. **中等。** 加一个 3 针变体，在每个长度下测三针全中的检索率，并与同长度下的单针通过率对比。
3. **困难。** 构造一个变量追踪任务（X1 → X2 → X3，3 跳），埋进 64k 填充文本，在 3 个旗舰模型上测准确率，报告每个模型的有效推理长度。

> 1. **Easy.** Build a NIAH with 3 depths (0.25, 0.5, 0.75) × 3 lengths (1k, 4k, 16k). Run on any model. Plot pass rate as a 3×3 heatmap.
> 2. **Medium.** Add a 3-needle variant. Measure retrieval of all 3 at each length. Compare to single-needle pass rate at the same length.
> 3. **Hard.** Construct a variable-tracing task (X1 → X2 → X3, with 3 hops) embedded in 64k of filler. Measure accuracy across 3 frontier models. Report effective reasoning length per model.

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|-----------------|-----------------------|
| NIAH | 草堆里的针 | 把一个事实埋进填充文本，让模型检索它。 |
| RULER | 加强版 NIAH | 横跨检索 / 多跳 / 聚合 / QA 的 13 种任务类型。 |
| Effective context | 真实容量 | 准确率仍能守住阈值之上的长度。 |
| Lost in the middle | 深度偏见 | 模型对长输入中部内容的注意不足。 |
| Multi-needle | 一次多条事实 | 多处埋针；测的是注意力的调配，不只是检索。 |
| MRCR | 多轮共指 | 8、24 或 100 针共指；暴露注意力饱和点。 |
| NoLiMa | 非词面针 | 针和问题不共享任何字面词元；需要推理。 |

## Further Reading · 延伸阅读

- [Kamradt (2023). Needle in a Haystack analysis](https://github.com/gkamradt/LLMTest_NeedleInAHaystack) —— NIAH 的原始仓库。
- [Hsieh et al. (2024). RULER: What's the Real Context Size of Your Long-Context LMs?](https://arxiv.org/abs/2404.06654) —— 多任务基准。
- [Bai et al. (2024). LongBench v2](https://arxiv.org/abs/2412.15204) —— 真实世界长上下文评估。
- [Modarressi et al. (2024). NoLiMa: Non-lexical needles](https://arxiv.org/abs/2404.06666) —— 更难的针。
- [Kuratov et al. (2024). BABILong](https://arxiv.org/abs/2406.10149) —— 草堆里的推理。
- [Liu et al. (2024). Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172) —— 深度偏见那篇论文。
