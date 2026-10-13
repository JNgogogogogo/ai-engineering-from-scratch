# GPU Setup & Cloud · GPU 设置与云端

> Training on CPU is fine for learning. Training for real needs a GPU.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 0, Lesson 01
**Time:** ~45 minutes

## Learning Objectives · 学习目标

- 用 `nvidia-smi` 和 PyTorch 的 CUDA API 确认本地 GPU 是否可用
- 给 Google Colab 配上 T4 GPU，做免费的云端实验
- 在 CPU 与 GPU 上分别做矩阵乘法基准测试，量化加速比
- 用 fp16 经验法则估算你的显存（VRAM）能装下多大的模型

> Verify local GPU availability using `nvidia-smi` and PyTorch's CUDA API
> Configure Google Colab with a T4 GPU for free cloud-based experiments
> Benchmark matrix multiplication on CPU vs GPU and measure the speedup
> Estimate the largest model that fits in your VRAM using the fp16 rule of thumb

## The Problem · 问题在哪

Phase 1-3 的大多数课程在 CPU 上就能顺利跑完。但一旦你开始训练 CNN、transformer 或 LLM（Phase 4 起），你就需要 GPU 加速：CPU 上要跑 8 小时的训练，GPU 上 10 分钟就能搞定。

你有三个选择：本地 GPU、云 GPU，或 Google Colab（免费）。

> Most lessons in phases 1-3 run fine on CPU. But once you start training CNNs,
> transformers, or LLMs (phases 4+), you need GPU acceleration. A training run
> that takes 8 hours on CPU takes 10 minutes on GPU.
> You have three options: local GPU, cloud GPU, or Google Colab (free).

## The Concept · 概念

```
Your options:

1. Local NVIDIA GPU
   Cost: $0 (you already have it)
   Setup: Install CUDA + cuDNN
   Best for: Regular use, large datasets

2. Google Colab (free tier)
   Cost: $0
   Setup: None
   Best for: Quick experiments, no GPU at home

3. Cloud GPU (Lambda, RunPod, Vast.ai)
   Cost: $0.20-2.00/hr
   Setup: SSH + install
   Best for: Serious training, large models
```

```figure
s0-gpu-dispatch
```

## Build It · 动手造

### Option 1: Local NVIDIA GPU · 方案 1：本地 NVIDIA GPU

看看你有没有一块：

```bash
nvidia-smi
```

安装带 CUDA 的 PyTorch：

```python
import torch

print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
```

> Check if you have one:
> Install PyTorch with CUDA:

### Option 2: Google Colab · 方案 2：Google Colab

1. 打开 [colab.research.google.com](https://colab.research.google.com)
2. 菜单里选 Runtime > Change runtime type > T4 GPU
3. 运行 `!nvidia-smi` 验证

本课程的 notebook 可以直接上传到 Colab。

> Go to [colab.research.google.com](https://colab.research.google.com)
> Runtime > Change runtime type > T4 GPU
> Run `!nvidia-smi` to verify
> Upload notebooks from this course directly to Colab.

### Option 3: Cloud GPU · 方案 3：云 GPU

在 Lambda Labs、RunPod 或 Vast.ai 上：

```bash
ssh user@your-gpu-instance

pip install torch torchvision torchaudio
python -c "import torch; print(torch.cuda.get_device_name(0))"
```

> For Lambda Labs, RunPod, or Vast.ai:

### No GPU? No problem. · 没有 GPU？没问题。

大多数课程在 CPU 上就能跑。需要 GPU 的课程会明确说明，并附上 Colab 链接。

```python
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using: {device}")
```

> Most lessons work on CPU. The ones that need GPU will say so and include Colab links.

## Build It: GPU vs CPU benchmark · 动手造：GPU vs CPU 基准测试

```python
import torch
import time

size = 5000

a_cpu = torch.randn(size, size)
b_cpu = torch.randn(size, size)

start = time.time()
c_cpu = a_cpu @ b_cpu
cpu_time = time.time() - start
print(f"CPU: {cpu_time:.3f}s")

if torch.cuda.is_available():
    a_gpu = a_cpu.to("cuda")
    b_gpu = b_cpu.to("cuda")

    torch.cuda.synchronize()
    start = time.time()
    c_gpu = a_gpu @ b_gpu
    torch.cuda.synchronize()
    gpu_time = time.time() - start
    print(f"GPU: {gpu_time:.3f}s")
    print(f"Speedup: {cpu_time / gpu_time:.0f}x")
```

## Exercises · 练习

1. 跑上面的基准测试，对比 CPU 和 GPU 的耗时
2. 如果你没有 GPU，就到 Google Colab 上跑一遍再对比
3. 查一下你有多少 GPU 显存，估算能装下的最大模型（经验法则：fp16 下每个参数 2 字节）

> 1. Run the benchmark above and compare CPU vs GPU times
> 2. If you don't have a GPU, run it on Google Colab and compare
> 3. Check how much GPU memory you have and estimate the largest model you can fit (rule of thumb: 2 bytes per parameter for fp16)

## Key Terms · 术语表

| Term 术语 | What people say 人们常说 | What it actually means 实际含义 |
|------|----------------|----------------------|
| CUDA | 「GPU 编程」 | NVIDIA 的并行计算平台，让你可以在 GPU 上运行代码 |
| VRAM | 「GPU 内存」 | GPU 上的显存，与系统内存相互独立。它决定了模型大小的上限。 |
| fp16 | 「半精度」 | 16 位浮点数，内存占用只有 fp32 的一半，精度损失极小 |
| Tensor Core | 「快速矩阵硬件」 | 专为矩阵乘法设计的 GPU 核心，比普通核心快 4-8 倍 |
