# Edge Inference — Apple Neural Engine, Qualcomm Hexagon, WebGPU/WebLLM, Jetson · 边缘推理——Apple Neural Engine、Qualcomm Hexagon、WebGPU/WebLLM、Jetson

边缘的核心约束是内存带宽，不是算力。手机 DRAM 只有 50-90 GB/s；数据中心 HBM3 超过 2-3 TB/s——30-50 倍的差距。Decode 受带宽约束，所以这个差距是决定性的。2026 年的格局分成四路。Apple M4/A18 Neural Engine 峰值 38 TOPS，配统一内存（无需 CPU↔NPU 拷贝）。Qualcomm Snapdragon X Elite / 8 Gen 4 的 Hexagon 达到 45 TOPS。WebGPU + WebLLM 在 M3 Max 上以约 41 tok/s 运行 Llama 3.1 8B（Q4）（约为原生的 70-80%）；17.6k GitHub stars、OpenAI 兼容 API、约 70-75% 移动端覆盖率。NVIDIA Jetson Orin Nano Super（8GB）装得下 Llama 3.2 3B / Phi-3；AGX Orin 通过 vLLM 以约 40 tok/s 运行 gpt-oss-20b；Jetson T4000（JetPack 7.1）是 AGX Orin 的 2 倍。TensorRT Edge-LLM 支持 EAGLE-3、NVFP4、chunked prefill——Bosch、ThunderSoft、MediaTek 在 CES 2026 上做过展示。

> The core edge constraint is memory bandwidth, not compute. Mobile DRAM sits at 50-90 GB/s; datacenter HBM3 clears 2-3 TB/s — a 30-50x gap. Decode is memory-bound so the gap is decisive. In 2026 the landscape splits four ways. Apple M4/A18 Neural Engine peaks at 38 TOPS with unified memory (no CPU↔NPU copy). Qualcomm Snapdragon X Elite / 8 Gen 4 Hexagon hits 45 TOPS. WebGPU + WebLLM runs Llama 3.1 8B (Q4) at ~41 tok/s on M3 Max (roughly 70-80% of native); 17.6k GitHub stars, OpenAI-compatible API, ~70-75% mobile coverage. NVIDIA Jetson Orin Nano Super (8GB) fits Llama 3.2 3B / Phi-3; AGX Orin runs gpt-oss-20b via vLLM at ~40 tok/s; Jetson T4000 (JetPack 7.1) is 2x AGX Orin. TensorRT Edge-LLM supports EAGLE-3, NVFP4, chunked prefill — shown at CES 2026 by Bosch, ThunderSoft, MediaTek.

**Type:** Learn
**Languages:** Python（仅标准库；玩具级带宽受限解码模拟器）
**Prerequisites:** Phase 17 · 04（Serving Engine Internals）、Phase 17 · 09（Production Quantization）
**Time:** ~60 分钟

## Learning Objectives · 学习目标

- 解释为什么移动端 LLM 推理受内存带宽约束、算力是次要的。
- 列出四个边缘目标（Apple ANE、Qualcomm Hexagon、WebGPU/WebLLM、NVIDIA Jetson），并为每个匹配一个用例。
- 说出 2026 年 WebGPU 的覆盖缺口（Firefox Android 仍在追赶）和 Safari iOS 26 的落地。
- 按目标选择量化格式（ANE 用 Core ML INT4 + FP16，Hexagon 用 QNN INT8/INT4，浏览器用 WebGPU Q4，Jetson Thor 用 NVFP4）。

> Explain why mobile LLM inference is memory-bandwidth-bound and compute is secondary.
> Enumerate the four edge targets (Apple ANE, Qualcomm Hexagon, WebGPU/WebLLM, NVIDIA Jetson) and match each to a use case.
> Name the 2026 WebGPU coverage gap (Firefox Android catching up) and the Safari iOS 26 landing.
> Pick a quantization format per target (Core ML INT4 + FP16 for ANE, QNN INT8/INT4 for Hexagon, WebGPU Q4 for browser, NVFP4 for Jetson Thor).

## The Problem · 问题在哪

一个客户想要端侧聊天机器人：语音优先、默认保护隐私、离线可用。在 MacBook Pro M3 Max 上，Llama 3.1 8B Q4 跑约 55 tok/s——没问题。在 iPhone 16 Pro 上，同一个模型只有 3 tok/s——不行。Snapdragon 8 Gen 3 的中端 Android 上是 7 tok/s。在 Chrome Android v121+ 上经 WebGPU 跑浏览器版，4-8 tok/s，看设备。

这个吞吐差异不是移植问题。它是带宽差距 × 量化格式 × NPU 能否从用户态访问三者的乘积。2026 年的边缘推理是四个不同的问题，配四种不同的解法。

> A customer wants an on-device chatbot: voice-first, private-by-default, works offline. On a MacBook Pro M3 Max, Llama 3.1 8B Q4 runs at ~55 tok/s — fine. On an iPhone 16 Pro, the same model runs at 3 tok/s — not fine. On a mid-range Android with Snapdragon 8 Gen 3, 7 tok/s. In the browser via WebGPU on Chrome Android v121+, 4-8 tok/s depending on the device.
> The throughput variance is not a porting issue. It is the bandwidth gap times the quantization format times whether the NPU is accessible from user-space. Edge inference in 2026 is four different problems with four different solutions.

## The Concept · 概念

### Bandwidth is the real ceiling · 带宽才是真正的天花板

Decode 每个 token 都要把全部权重读一遍。Q4 的 7B 模型是 3.5 GB。以 50 GB/s 读 3.5 GB 需要 70 ms——理论上限约 14 tok/s。到 90 GB/s（高端手机 DRAM），上限移到约 25 tok/s。算力再多也突破不了这个数。

数据中心 HBM3 以 3 TB/s 读同样的 3.5 GB 只要 1.2 ms——上限是 830 tok/s。同一个模型、同一份权重，不同的内存子系统。

> Decode reads the full set of weights for every token. One 7B model in Q4 is 3.5 GB. Reading 3.5 GB at 50 GB/s takes 70 ms — a theoretical ceiling of ~14 tok/s. At 90 GB/s (high-end mobile DRAM) the ceiling moves to ~25 tok/s. No amount of compute helps below this number.
> Datacenter HBM3 at 3 TB/s clears the same 3.5 GB in 1.2 ms — ceiling is 830 tok/s. Same model, same weights. Different memory subsystem.

### Apple Neural Engine (M4 / A18) · Apple 神经引擎（M4 / A18）

- 最高 38 TOPS。统一内存（CPU 和 ANE 共享同一个池）——没有拷贝开销。
- 通过 Core ML + 编译好的 `.mlmodel` 模型访问，或经 PyTorch 走 Metal Performance Shaders（MPS）。
- Llama.cpp 的 Metal 后端用的是 MPS，不是直接用 ANE；原生 ANE 需要转成 Core ML。
- 2026 年 iOS 应用的最佳实践路径：Core ML 配 INT4 权重 + FP16 激活值。

> - Up to 38 TOPS. Unified memory (CPU and ANE share the same pool) — no copy overhead.
> - Access via Core ML + `.mlmodel` compiled models, or via Metal Performance Shaders (MPS) through PyTorch.
> - Llama.cpp Metal backend uses MPS, not ANE directly; native ANE requires Core ML conversion.
> - Best practical path for iOS apps in 2026: Core ML with INT4 weights + FP16 activations.

### Qualcomm Hexagon (Snapdragon X Elite / 8 Gen 4) · Qualcomm Hexagon（Snapdragon X Elite / 8 Gen 4）

- 最高 45 TOPS。与 CPU、GPU 集成在同一 SoC 上，但内存域独立。
- QNN（Qualcomm Neural Network）SDK 和 AI Hub 提供从 PyTorch/ONNX 的转换。
- Chat template、Llama 3.2、Phi-3 都作为一等公民制品在 AI Hub 上提供。

> - Up to 45 TOPS. Integrated with CPU and GPU in the SoC but separate memory domain.
> - QNN (Qualcomm Neural Network) SDK and AI Hub provide conversion from PyTorch/ONNX.
> - Chat templates, Llama 3.2, Phi-3 all ship as first-class artifacts on AI Hub.

### Intel / AMD NPUs (Lunar Lake, Ryzen AI 300) · Intel / AMD NPU（Lunar Lake、Ryzen AI 300）

- 40-50 TOPS。软件生态落后于 Apple/Qualcomm；OpenVINO 在改进但仍小众。
- 最适合 Windows ARM copilot 类应用；在 AMD/Intel 桌面上做 local-first 的原生选择。

> - 40-50 TOPS. Software lags behind Apple/Qualcomm; OpenVINO is improving but niche.
> - Best for Windows ARM copilot apps; native on AMD/Intel desktops for local-first.

### WebGPU + WebLLM

- 通过 WebGPU compute shader 在浏览器里跑模型；无需安装。
- Llama 3.1 8B Q4 在 M3 Max 上约 41 tok/s——同一后端下约为原生的 70-80%。
- WebLLM 有 17.6k GitHub stars；OpenAI 兼容 JS API；Apache 2.0。
- 2026 年覆盖率：Chrome Android v121+、Safari iOS 26 GA，Firefox Android 仍在追赶。总体约 70-75% 移动端覆盖。

> - Run models in the browser via WebGPU compute shaders; no install.
> - Llama 3.1 8B Q4 at ~41 tok/s on M3 Max — roughly 70-80% of native via same backend.
> - 17.6k GitHub stars on WebLLM; OpenAI-compatible JS API; Apache 2.0.
> - 2026 coverage: Chrome Android v121+, Safari iOS 26 GA, Firefox Android still catching up. Overall ~70-75% mobile coverage.

### NVIDIA Jetson family · NVIDIA Jetson 家族

- Orin Nano Super（8GB）：装得下 Llama 3.2 3B、Phi-3，tok/s 不错。
- AGX Orin：通过 vLLM 以约 40 tok/s 运行 gpt-oss-20b。
- Thor / T4000（JetPack 7.1）：2 倍于 AGX Orin 的性能，支持 EAGLE-3 和 NVFP4。
- TensorRT Edge-LLM（2026）支持 EAGLE-3 投机解码、NVFP4 权重、chunked prefill——数据中心优化移植到边缘。

> - Orin Nano Super (8GB): fits Llama 3.2 3B, Phi-3 at good tok/s.
> - AGX Orin: runs gpt-oss-20b via vLLM at ~40 tok/s.
> - Thor / T4000 (JetPack 7.1): 2x AGX Orin performance, EAGLE-3 and NVFP4 supported.
> - TensorRT Edge-LLM (2026) supports EAGLE-3 speculative decoding, NVFP4 weights, chunked prefill — the datacenter optimizations ported to edge.

### Quantization choice per target · 按目标选择量化格式

| 目标 | 格式 | 说明 |
|--------|--------|-------|
| Apple ANE | INT4 权重 + FP16 激活值 | Core ML 转换路径 |
| Qualcomm Hexagon | QNN INT8 / INT4 | AI Hub 转换器 |
| WebGPU / WebLLM | Q4 MLC (q4f16_1) | 使用 `mlc_llm convert_weight` + 编译好的 `.wasm`；不支持 GGUF |
| Jetson Orin Nano | Q4 GGUF 或 TRT-LLM INT4 | 受内存限制 |
| Jetson AGX / Thor | NVFP4 + FP8 KV | Edge-LLM 路径 |

### The long-context trap on edge · 边缘上的长上下文陷阱

Llama 3.1 的 128K 上下文是数据中心特性。在一台 8 GB 内存的手机上：4 GB 模型 + 32K token 的 2 GB KV cache + OS 开销 = OOM。边缘部署把上下文保持在 4K-8K，除非接受激进的 KV 量化（Q4 KV）。

> Llama 3.1's 128K context is a datacenter feature. On a phone with 8 GB RAM, 4 GB model + 2 GB KV cache for 32K tokens + OS overhead = OOM. Edge deployments keep context at 4K-8K unless aggressive KV quantization (Q4 KV) is accepted.

### Voice is the killer app · 语音才是杀手级应用

语音 agent 对延迟敏感（首 token < 500 ms）。本地推理彻底消灭网络延迟。再配上语音转文字（Whisper Turbo 变体可在端上运行），边缘推理就成了生产级的语音闭环。

> Voice agents are latency-sensitive (first token < 500 ms). Local inference eliminates network latency entirely. Combine with speech-to-text (Whisper Turbo variants run on edge) and edge inference becomes the production-quality voice loop.

### Numbers you should remember · 该记住的数字

- Apple M4 / A18 ANE：38 TOPS。
- Qualcomm Hexagon SD X Elite：45 TOPS。
- WebLLM M3 Max：Llama 3.1 8B Q4 约 41 tok/s。
- AGX Orin：经 vLLM 跑 gpt-oss-20b 约 40 tok/s。
- 数据中心-边缘带宽差距：30-50 倍。
- WebGPU 移动端覆盖率：约 70-75%（Firefox Android 落后）。

```figure
edge-bandwidth-pipe
```

> - Apple M4 / A18 ANE: 38 TOPS.
> - Qualcomm Hexagon SD X Elite: 45 TOPS.
> - WebLLM M3 Max: ~41 tok/s on Llama 3.1 8B Q4.
> - AGX Orin: ~40 tok/s on gpt-oss-20b via vLLM.
> - Datacenter-edge bandwidth gap: 30-50x.
> - WebGPU mobile coverage: ~70-75% (Firefox Android lagging).

## Use It · 实战用法

`code/main.py` 用带宽受限的数学计算各边缘目标的理论解码吞吐上限。与观测到的基准对比，并标出瓶颈到底是带宽而不是算力的地方。

> `code/main.py` computes theoretical decode throughput ceilings from bandwidth-bound math across edge targets. Compares to observed benchmarks and highlights where bandwidth, not compute, is the bottleneck.

## Ship It · 交付

本课产出 `outputs/skill-edge-target-picker.md`。给定平台（iOS/Android/浏览器/Jetson）、模型和延迟/显存预算，它会选出量化格式和转换流水线。

> This lesson produces `outputs/skill-edge-target-picker.md`. Given platform (iOS/Android/browser/Jetson), model, and latency/memory budget, picks a quantization format and conversion pipeline.

## Exercises · 练习

1. 运行 `code/main.py`。对 Snapdragon 8 Gen 3（约 77 GB/s 带宽）上的 Q4 7B 模型，计算解码上限。与观测到的 6-8 tok/s 对比——运行时效率高吗？
2. Android 上的 WebGPU 要求 Chrome v121+。为旧浏览器设计一个回退方案——经同一个 OpenAI 兼容 API 走服务端。
3. 你的 iOS 应用需要 4K 上下文流式输出。哪种模型/格式组合能让你在 iPhone 16 上保持 4 GB 活动内存以内？
4. Jetson AGX Orin 以 40 tok/s 跑 gpt-oss-20b，Jetson Nano 只装得下 3B。如果你的产品两类设备都要覆盖，怎么统一推理栈？
5. 论证「WebLLM 在 2026 年是否生产可用」。引用覆盖率、性能以及 Firefox Android 的缺口。

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|------------------------|
| ANE | 「Apple 神经引擎」 | M 系列与 A 系列芯片上的端侧 NPU；统一内存 |
| Hexagon | 「Qualcomm NPU」 | Snapdragon NPU；通过 QNN SDK 访问 |
| WebGPU | 「浏览器 GPU」 | W3C 标准化的浏览器 GPU API；2026 年的 Chrome/Safari |
| WebLLM | 「浏览器 LLM 运行时」 | MLC-LLM 项目；Apache 2.0；OpenAI 兼容 JS API |
| Jetson | 「NVIDIA 边缘」 | Orin Nano / AGX / Thor / T4000 家族 |
| TRT Edge-LLM | 「边缘 TensorRT」 | TensorRT-LLM 的 2026 边缘版；EAGLE-3 + NVFP4 |
| Unified memory | 「共享内存池」 | CPU 与 NPU 看到同一块内存；无拷贝开销 |
| Bandwidth-bound | 「受内存限制」 | decode 被每秒能读多少字节的权重卡住 |
| Core ML | 「Apple 转换」 | Apple 面向 ANE 原生模型的框架 |
| QNN | 「Qualcomm 技术栈」 | Qualcomm Neural Network SDK |

## Further Reading · 延伸阅读

- [On-Device LLMs State of the Union 2026](https://v-chandra.github.io/on-device-llms/) —— 格局与基准。
- [NVIDIA Jetson Edge AI](https://developer.nvidia.com/blog/getting-started-with-edge-ai-on-nvidia-jetson-llms-vlms-and-foundation-models-for-robotics/) —— Orin / AGX / Thor。
- [NVIDIA TensorRT Edge-LLM](https://developer.nvidia.com/blog/accelerating-llm-and-vlm-inference-for-automotive-and-robotics-with-nvidia-tensorrt-edge-llm/) —— 2026 边缘版发布公告。
- [WebLLM (arXiv:2412.15803)](https://arxiv.org/html/2412.15803v2) —— 设计与基准。
- [Apple Core ML](https://developer.apple.com/documentation/coreml) —— ANE 原生转换。
- [Qualcomm AI Hub](https://aihub.qualcomm.com/) —— 面向 Hexagon 的预转换模型。
