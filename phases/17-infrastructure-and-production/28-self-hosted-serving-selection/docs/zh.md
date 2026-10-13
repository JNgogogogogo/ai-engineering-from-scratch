# Self-Hosted Serving Selection — Matching Engine to Hardware and Scale · 自托管推理引擎选型——让引擎匹配硬件与规模

> 引擎选型是硬件、规模和生态的函数——不是看一眼排行榜就完事。2026 年主导自托管推理的是四个引擎：llama.cpp、Ollama、vLLM、SGLang，TGI 掉队进入维护模式。**llama.cpp** 在 CPU 上最快——模型支持面最广，量化（quantization）和多线程完全可控。**Ollama** 是开发笔记本上的一条命令安装，比 llama.cpp 慢约 15-30%（Go + CGo + HTTP 序列化），生产级负载下吞吐差距达 3 倍。**TGI 已于 2025 年 12 月 11 日进入维护模式**——只修 bug，原始吞吐比 vLLM 慢约 10%，但历史上拥有顶级的可观测性和 HF 生态集成。这个维护状态让它成为有风险的长期赌注——新项目选 SGLang 或 vLLM 更稳妥。**vLLM** 是通用型生产默认——v0.15.1（2026 年 2 月）加入 PyTorch 2.10、RTX Blackwell SM120、H200 优化。**SGLang** 是 agentic 多轮 / 前缀密集场景的专家——生产部署在 40 万+ GPU 上（xAI、LinkedIn、Cursor、Oracle、GCP、Azure、AWS）。硬件约束：CPU 优先 → llama.cpp。AMD / 非 NVIDIA → vLLM 是支持最稳的路径（TRT-LLM 被 NVIDIA 锁死）。2026 年的流水线模式：dev = Ollama，staging = llama.cpp，prod = vLLM 或 SGLang。各引擎吃的权重格式不同——llama.cpp 家族用 GGUF，GPU 引擎用 HF safetensors——所以阶段之间可能要放一道格式转换。

> Engine selection is a function of hardware, scale, and ecosystem — not a leaderboard read. Four engines dominate self-hosted inference in 2026: llama.cpp, Ollama, vLLM, SGLang, with TGI trailing in maintenance mode. **llama.cpp** is fastest on CPU — widest model support, full control over quantization and threading. **Ollama** is the dev-laptop one-command install, ~15-30% slower than llama.cpp (Go + CGo + HTTP serialization), 3x throughput gap under prod-like load. **TGI entered maintenance mode December 11, 2025** — only bug fixes, ~10% slower raw throughput than vLLM but historically top observability and HF-ecosystem integration. That maintenance status makes it a risky long-term bet — SGLang or vLLM are safer defaults for new projects. **vLLM** is the general-purpose production default — v0.15.1 (February 2026) adds PyTorch 2.10, RTX Blackwell SM120, H200 optimization. **SGLang** is the agentic multi-turn / prefix-heavy specialist — 400,000+ GPUs in production (xAI, LinkedIn, Cursor, Oracle, GCP, Azure, AWS). Hardware constraints: CPU-first → llama.cpp. AMD / non-NVIDIA → vLLM is the strongest-supported path (TRT-LLM is NVIDIA-locked). 2026 pipeline pattern: dev = Ollama, staging = llama.cpp, prod = vLLM or SGLang. The engines take different weight formats — GGUF for the llama.cpp family, HF safetensors for the GPU engines — so a format conversion may sit between stages.

**Type:** Learn
**Languages:** Python (stdlib, engine-decision tree walker)
**Prerequisites:** All Phase 17 lessons covering engines (04, 06, 07, 09, 18)
**Time:** ~45 minutes

---

## Learning Objectives · 学习目标

- 给定硬件（CPU / AMD / NVIDIA Hopper / Blackwell）、规模（1 用户 / 100 / 10,000）和工作负载（通用聊天 / agent / 长上下文），选出一个引擎
- 说出 TGI 2026 年的维护模式状态（2025 年 12 月 11 日），以及为什么它让新项目偏向 vLLM 或 SGLang
- 描述 dev/staging/prod 流水线，包括 GGUF 转 safetensors 的格式转换位于哪两个阶段之间
- 解释为什么「CPU 优先」指向 llama.cpp，而「AMD」排除 TRT-LLM

> Pick an engine given hardware (CPU / AMD / NVIDIA Hopper / Blackwell), scale (1 user / 100 / 10,000), and workload (general chat / agent / long-context).
> Name the 2026 TGI maintenance-mode status (December 11, 2025) and why it biases new projects toward vLLM or SGLang.
> Describe the dev/staging/prod pipeline, including where a GGUF-to-safetensors format conversion sits between stages.
> Explain why "CPU-first" points to llama.cpp and "AMD" excludes TRT-LLM.

---

## The Problem · 问题在哪

你的团队要启动一个新的自托管 LLM 项目。一个工程师说 Ollama，另一个说 vLLM，第三个问「TGI 不是开箱即用吗」。三个人在各自的场景下都对，但没有一个适用于所有场景。

2026 年，选择树很重要：先看硬件，再看规模，最后看工作负载。而 2025 年的一个具体事件——TGI 于 12 月 11 日进入维护模式——改变了新项目的默认选择。

> Your team starts a new self-hosted LLM project. One engineer says Ollama, another says vLLM, a third says "doesn't TGI just work out of the box?" All three are right for different contexts. None is right for all. ... In 2026 the choice tree matters: hardware first, scale second, workload third. And one specific 2025 event — TGI entering maintenance mode December 11 — changes the default for new projects.

---

## The Concept · 概念

### The five engines · 五个引擎

| 引擎 | 最适合 | 备注 |
|--------|----------|-------|
| **llama.cpp** | CPU / 边缘 / 最小依赖 / 模型支持面最广 | CPU 上最快，控制力完整 |
| **Ollama** | 开发笔记本、单用户、一条命令安装 | 比 llama.cpp 慢 15-30%；生产吞吐差距 3 倍 |
| **TGI** | HF 生态、受监管行业 | **2025 年 12 月 11 日起维护模式** |
| **vLLM** | 通用生产、100+ 用户 | 广泛的生产默认；v0.15.1（2026 年 2 月） |
| **SGLang** | agentic 多轮、前缀密集工作负载 | 生产部署 40 万+ GPU |

### Hardware-first decision · 硬件优先决策

**CPU 优先** → llama.cpp。Ollama 也能跑但更慢。CPU 上没有别的引擎有竞争力。

**AMD GPU** → vLLM 是支持最稳的路径（AMD ROCm 支持）。SGLang 也能用。TRT-LLM 被 NVIDIA 锁死，出局。

**NVIDIA Hopper（H100 / H200）** → vLLM 或 SGLang 或 TRT-LLM。三家都是顶级。

**NVIDIA Blackwell（B200 / GB200）** → TRT-LLM 是吞吐冠军（Phase 17 · 07）。vLLM 和 SGLang 紧随其后。

**Apple Silicon（M 系列）** → llama.cpp（Metal）。Ollama 是它的包装。

> **CPU-first** → llama.cpp. Ollama works too but is slower. No other engine is competitive on CPU. ... **AMD GPU** → vLLM is the strongest-supported path (AMD ROCm support). SGLang also works. TRT-LLM is NVIDIA-locked, so it's out. ... **NVIDIA Blackwell (B200 / GB200)** → TRT-LLM is the throughput leader (Phase 17 · 07). vLLM and SGLang follow close. ... **Apple Silicon (M-series)** → llama.cpp (Metal). Ollama wraps this.

### Scale-second decision · 规模次之决策

**1 用户 / 本地开发** → Ollama。一条命令，秒级出首 token。

**10-100 用户 / 小团队** → vLLM 单 GPU。

**100-10k 用户 / 生产** → vLLM production-stack（Phase 17 · 18）或 SGLang。

**10k+ 用户 / 企业级** → vLLM production-stack + 分离式部署（disaggregated，Phase 17 · 17）+ LMCache（Phase 17 · 18）。

> **1 user / local dev** → Ollama. One command, first-token in seconds. ... **100-10k users / production** → vLLM production-stack (Phase 17 · 18) or SGLang. ... **10k+ users / enterprise** → vLLM production-stack + disaggregated (Phase 17 · 17) + LMCache (Phase 17 · 18).

### Workload-third decision · 工作负载第三决策

**通用聊天 / 问答** → vLLM 赢在通用默认。

**Agentic 多轮（工具、规划、记忆）** → SGLang 的 RadixAttention（Phase 17 · 06）称霸。

**前缀重用密集的 RAG** → SGLang。

**代码生成** → vLLM 足够；SGLang 在缓存上略优。

**长上下文（128K+）** → vLLM + chunked prefill；SGLang + 分层 KV（tiered KV）。

> **General chat / Q&A** → vLLM wins on broad default. ... **Agentic multi-turn (tools, planning, memory)** → SGLang's RadixAttention (Phase 17 · 06) dominates. ... **RAG with heavy prefix reuse** → SGLang. ... **Long context (128K+)** → vLLM + chunked prefill; SGLang + tiered KV.

### The TGI maintenance trap · TGI 维护模式陷阱

Hugging Face TGI 于 2025 年 12 月 11 日进入维护模式——此后只修 bug。历史上：可观测性顶级，HF 生态集成一流（模型卡、安全工具），原始吞吐略落后于 vLLM。

对 2026 年的新项目：默认避开 TGI。已部署的 TGI 可以继续用，但最终应该迁移。SGLang 和 vLLM 是更稳妥的默认。

> Hugging Face TGI entered maintenance mode December 11, 2025 — only bug fixes going forward. Historically: top-tier observability, best-in-class HF-ecosystem integration (model cards, safety tools), slightly behind vLLM on raw throughput. ... For new projects in 2026: default away from TGI. Existing TGI deployments can continue but should migrate eventually. SGLang and vLLM are the safer defaults.

### The pipeline pattern · 流水线模式

Dev（Ollama）→ staging（llama.cpp）→ prod（vLLM）。各引擎吃的权重格式不同——llama.cpp 家族用 GGUF，GPU 引擎用 HF safetensors——所以阶段之间可能要放一道格式转换。工程师在笔记本上快速迭代；staging 镜像生产的量化方案；prod 是最终的服务目标。

> Dev (Ollama) → staging (llama.cpp) → prod (vLLM). The engines take different weight formats — GGUF for the llama.cpp family, HF safetensors for the GPU engines — so a format conversion may sit between stages. Engineers iterate quickly on laptops; staging mirrors production quantization; prod is the serving target.

### Ollama caveat · Ollama 的注意事项

Ollama 在开发场景很棒。但它不适合共享生产环境：Go HTTP 序列化有额外开销，并发管理比 vLLM 简单，OpenTelemetry 支持滞后。在 Ollama 的闪光点用它——一个用户、一条命令——共享场景换 vLLM。

> Ollama is great for dev. It is not great for shared production: Go HTTP serialization adds overhead, concurrency management is simpler than vLLM, OpenTelemetry support lags. Use Ollama where it shines — one user, one command — and switch to vLLM for shared.

### Self-hosted vs managed is a separate decision · 自托管 vs 托管是另一个决策

Phase 17 · 01（托管超大规模平台）、· 02（推理平台）讲的是托管。本课假设你已经决定自托管。自托管的理由：数据驻留（data residency）、定制微调（fine-tune）、规模化下的总拥有成本、托管平台上没有的领域模型。

> Phase 17 · 01 (managed hyperscalers), · 02 (inference platforms) cover managed. This lesson assumes you've already decided to self-host. Reasons to self-host: data residency, custom fine-tune, total cost ownership at scale, domain model not available on hosted.

### Numbers you should remember · 该记住的数字

- TGI 维护模式：2025 年 12 月 11 日。
- vLLM v0.15.1：2026 年 2 月；PyTorch 2.10；Blackwell SM120 支持。
- SGLang 生产足迹：40 万+ GPU。
- Ollama 相对 llama.cpp 的吞吐差距：慢 15-30%；生产负载下 3 倍。

> TGI maintenance mode: December 11, 2025.
> vLLM v0.15.1: February 2026; PyTorch 2.10; Blackwell SM120 support.
> SGLang production footprint: 400,000+ GPUs.
> Ollama throughput gap vs llama.cpp: 15-30% slower; 3x under prod load.

```figure
data-parallel
```

---

## Use It · 实战用法

`code/main.py` 是一个决策树遍历器：输入硬件 + 规模 + 工作负载，选出一个引擎并解释原因。

> `code/main.py` is a decision-tree walker: given hardware + scale + workload, picks an engine and explains why.

---

## Ship It · 交付

本课产出 `outputs/skill-engine-picker.md`。输入约束条件，它选出一个引擎并写出迁移计划。

> This lesson produces `outputs/skill-engine-picker.md`. Given constraints, picks an engine and writes the migration plan.

---

## Exercises · 练习

1. 用你的硬件 / 规模 / 工作负载跑 `code/main.py`。输出和你的直觉一致吗？
2. 你的基础设施是 12 台 H100 加 8 台 MI300X AMD。选什么引擎？为什么 TRT-LLM 出局？
3. 一个团队 2026 年还想用 TGI，理由是「我们只熟悉这个」。论证迁移的必要性。
4. 从 Ollama dev 到 vLLM prod：量化、配置、可观测性各要改什么？
5. 一个 RAG 产品的 P99 前缀长度 8K 且租户间重用率高。选一个引擎，并叠上 Phase 17 · 11 + 18。

---

## Key Terms · 术语表

| 术语 | 人们口头说 | 实际含义 |
|------|----------------|------------------------|
| llama.cpp | 「CPU 那个」 | 模型支持面最广，CPU 上最快 |
| Ollama | 「笔记本那个」 | 一条命令安装，开发级吞吐 |
| TGI | 「HF 的服务」 | 2025 年 12 月起维护模式 |
| vLLM | 「默认那个」 | 2026 年广泛的生产基线 |
| SGLang | 「agentic 那个」 | 前缀密集，RadixAttention |
| TRT-LLM | 「NVIDIA 专属」 | Blackwell 吞吐冠军，仅限 NVIDIA |
| GGUF | 「llama.cpp 格式」 | 打包的 K-quant 变体 |
| Production-stack | 「vLLM K8s」 | Phase 17 · 18 参考部署 |
| Pipeline pattern | 「dev→stage→prod」 | Ollama → llama.cpp → vLLM；各引擎权重格式不同 |

---

## Further Reading · 延伸阅读

- [AI Made Tools — vLLM vs Ollama vs llama.cpp vs TGI 2026](https://www.aimadetools.com/blog/vllm-vs-ollama-vs-llamacpp-vs-tgi/)
- [Morph — llama.cpp vs Ollama 2026](https://www.morphllm.com/comparisons/llama-cpp-vs-ollama)
- [n1n.ai — Comprehensive LLM Inference Engine Comparison](https://explore.n1n.ai/blog/llm-inference-engine-comparison-vllm-tgi-tensorrt-sglang-2026-03-13)
- [PremAI — 10 Best vLLM Alternatives 2026](https://blog.premai.io/10-best-vllm-alternatives-for-llm-inference-in-production-2026/)
- [TGI maintenance announcement](https://github.com/huggingface/text-generation-inference) —— 发布说明
- [vLLM v0.15.1 release notes](https://github.com/vllm-project/vllm/releases)
