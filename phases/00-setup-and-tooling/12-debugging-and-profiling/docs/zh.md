# 调试与性能剖析（Debugging and Profiling）

> 中文讲义（双语对照）。正文为中文，每段下方 `>` 引用块保留英文原文；代码块、命令、术语名不译。

**类型 (Type):** Build
**语言 (Language):** Python
**前置课程 (Prerequisites):** Lesson 1 (Dev Environment), basic PyTorch familiarity
**时间 (Time):** ~60 分钟

> The worst AI bugs don't crash. They train silently on garbage and report a beautiful loss curve.

## 学习目标（Learning Objectives）

- 用条件 `breakpoint()` 和 `debug_print` 在训练中途检查 tensor 的 shape、dtype、NaN 值
- 用 `cProfile`、`line_profiler`、`tracemalloc` 给训练循环做性能剖析，找出瓶颈
- 检测常见 AI bug：shape 不匹配、NaN loss、数据泄漏、tensor 放错设备
- 搭起 TensorBoard，可视化 loss 曲线、权重直方图、梯度分布

> - Use conditional `breakpoint()` and `debug_print` to inspect tensor shapes, dtypes, and NaN values mid-training
> - Profile training loops with `cProfile`, `line_profiler`, and `tracemalloc` to find bottlenecks
> - Detect common AI bugs: shape mismatches, NaN loss, data leakage, and wrong-device tensors
> - Set up TensorBoard to visualize loss curves, weight histograms, and gradient distributions

## 问题（The Problem）

AI 代码的失败方式和普通代码不一样。Web 应用崩了会给你一个 stack trace；而一个配错的训练循环会跑上 8 小时、烧掉 200 美元 GPU 时间，最后产出一个只会预测「所有输入的均值」的模型——代码从头到尾没报过一次错。bug 可能只是某个 tensor 放错了设备、忘了 `.detach()`、或者标签泄漏进了特征。

你需要能**在这些静默故障烧掉你的时间和算力之前**抓住它们的调试工具。

> AI code fails differently than regular code. A web app crashes with a stack trace. A misconfigured training loop runs for 8 hours, burns $200 in GPU time, and produces a model that predicts the mean of every input. The code never errored. The bug was a tensor on the wrong device, a forgotten `.detach()`, or labels leaking into features.
>
> You need debugging tools that catch these silent failures before they waste your time and compute.

## 核心概念（The Concept）


AI 调试分三个层次：

1. **标准 Python 层**：断点、日志、性能剖析、内存
2. **Tensor 操作层**：shape、dtype、device、NaN/Inf 值
3. **训练动态层**：loss 曲线、梯度范数、激活值

大多数人一头扎进第 3 层（盯着 TensorBoard 看）。但 **80% 的 AI bug 都藏在第 1、2 层**。

> AI debugging operates at three levels: 3. Training Dynamics (Loss curves, gradient norms, activations) → 2. Tensor Operations (Shapes, dtypes, devices, NaN/Inf values) → 1. Standard Python (Breakpoints, logging, profiling, memory). Most people jump straight to level 3 (staring at TensorBoard). But 80% of AI bugs live at levels 1 and 2.
```figure
s0-flame-hot
```

## 动手构建（Build It）


### Part 1：Print 调试（是的，它管用）

Print 调试常被看不起，但对 tensor 代码不该如此：一句有针对性的 print 胜过在调试器里单步——因为你要**同时**看到 shape、dtype 和取值范围。

```python
def debug_print(name, tensor):
    print(f"{name}: shape={tensor.shape}, dtype={tensor.dtype}, "
          f"device={tensor.device}, "
          f"min={tensor.min().item():.4f}, max={tensor.max().item():.4f}, "
          f"mean={tensor.mean().item():.4f}, "
          f"has_nan={tensor.isnan().any().item()}")
```

在每个可疑操作后面调它。bug 找到就把 print 删掉，简单。

> Print debugging gets dismissed. It shouldn't. For tensor code, a targeted print statement beats stepping through a debugger because you need to see shapes, dtypes, and value ranges all at once. Call this after every suspicious operation. When the bug is found, remove the prints.

### Part 2：Python 调试器（pdb 与 breakpoint）

内置调试器在 AI 工作里被低估了。把 `breakpoint()` 丢进训练循环，交互式检查 tensor。


```python
def training_step(model, batch, criterion, optimizer):
    inputs, labels = batch
    outputs = model(inputs)
    loss = criterion(outputs, labels)

    if loss.item() > 100 or torch.isnan(loss):
        breakpoint()

    loss.backward()
    optimizer.step()
```


进调试器后有用的命令：`p outputs.shape` 看 shape、`p loss.item()` 看 loss 值、`p torch.isnan(outputs).sum()` 数 NaN 个数、`p model.fc1.weight.grad` 查梯度、`c` 继续、`q` 退出。

这叫**条件断点**：只在看起来不对劲时才停。对 10,000 步的训练，这很关键。

> The built-in debugger is underrated for AI work. Drop `breakpoint()` into your training loop and inspect tensors interactively. This is conditional debugging. You only stop when something looks wrong. For a 10,000-step training run, that matters.

### Part 3：Python Logging

调试超出「快速看一眼」的范围时，把 print 换成 logging：带时间戳、严重级别、同时输出到文件和终端（见下方代码块）。

训练在凌晨 3 点挂掉时，你要的是一个日志文件，而不是已经滚出屏幕的终端输出。

> Replace print statements with logging when your debugging goes beyond a quick check. Logging gives you timestamps, severity levels, and file output. When a training run fails at 3 AM, you want a log file, not terminal output that scrolled off screen.


```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("training.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("Starting training: lr=%.4f, batch_size=%d", lr, batch_size)
logger.warning("Loss spike detected: %.4f at step %d", loss.item(), step)
logger.error("NaN loss at step %d, stopping", step)
```

### Part 4：给代码段计时

知道时间花在哪，是优化的第一步。用 `time.perf_counter()` 做上下文管理器计时（见下方代码块）。

**常见发现：数据加载占训练时间的 60%。修法是给 DataLoader 设 `num_workers > 0`，不是换更快的 GPU。**

> Knowing where time goes is the first step to optimization. Common finding: data loading takes 60% of training time. The fix is `num_workers > 0` in your DataLoader, not a faster GPU.


```python
import time

class Timer:
    def __init__(self, name=""):
        self.name = name

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        elapsed = time.perf_counter() - self.start
        print(f"[{self.name}] {elapsed:.4f}s")

with Timer("data loading"):
    batch = next(dataloader_iter)

with Timer("forward pass"):
    outputs = model(batch)

with Timer("backward pass"):
    loss.backward()
```

### Part 5：cProfile 与 line_profiler

手动计时不够用时：`python -m cProfile -s cumtime train.py` 列出每个函数按累计耗时排序。逐行剖析用 `line_profiler`（装法见代码块），`kernprof -l -v train.py` 跑。

> When you need more than manual timers: `python -m cProfile -s cumtime train.py` shows every function call sorted by cumulative time. For line-by-line profiling: `pip install line_profiler`, then `kernprof -l -v train.py`.


```bash
python -m cProfile -s cumtime train.py
pip install line_profiler
```

```python
@profile
def train_step(model, data, target):
    output = model(data)
    loss = F.cross_entropy(output, target)
    loss.backward()
    return loss

# Run with: kernprof -l -v train.py
```

### Part 6：内存剖析

**CPU 内存（tracemalloc）**：`tracemalloc.start()` → 你的代码 → `take_snapshot().statistics("lineno")` 打印前 10 大分配点。

**CPU 内存（memory_profiler）**：`@profile` 装饰函数，`python -m memory_profiler your_script.py` 看逐行内存占用。

**GPU 内存（PyTorch）**：`torch.cuda.memory_summary()`、`torch.cuda.memory_allocated()`、`torch.cuda.memory_reserved()`。

**撞 OOM（Out of Memory）时的处理顺序**：

1. 减 batch size（永远是第一个动作）
2. `torch.cuda.empty_cache()` 释放缓存
3. 大中间变量 `del tensor` 再 `empty_cache()`
4. 混合精度 `torch.cuda.amp`，内存减半
5. 深模型用 gradient checkpointing

> When you hit OOM: 1. Reduce batch size (first thing to try, always) 2. `torch.cuda.empty_cache()` 3. `del tensor` + `empty_cache()` for large intermediates 4. Mixed precision (`torch.cuda.amp`) to halve memory 5. Gradient checkpointing for very deep models.


#### CPU 内存（tracemalloc）

```python
import tracemalloc

tracemalloc.start()

# your code here
model = build_model()
data = load_dataset()

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics("lineno")
for stat in top_stats[:10]:
    print(stat)
```

#### CPU 内存（memory_profiler）

```bash
pip install memory_profiler
```

```python
from memory_profiler import profile

@profile
def load_data():
    raw = read_csv("data.csv")       # watch memory jump here
    processed = preprocess(raw)       # and here
    return processed
```

（`python -m memory_profiler your_script.py` 运行，看逐行内存占用。）

#### GPU 内存（PyTorch）

```python
import torch

if torch.cuda.is_available():
    print(torch.cuda.memory_summary())

    print(f"Allocated: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print(f"Cached: {torch.cuda.memory_reserved() / 1e9:.2f} GB")
```

### Part 7：常见 AI bug 及抓法

#### Shape 不匹配（最常见）

tensor 是 `[batch, features]`，模型却要 `[batch, channels, height, width]`。用 `register_forward_hook` 打印每个模块的输入→输出 shape，跑一遍就把整个模型的 shape 变换地图画出来（代码见下方）。

#### NaN Loss

NaN loss = 某处爆炸了。常见原因：学习率太高、自定义 loss 里除零、log(0) 或 log(负数)、RNN 梯度爆炸。`detect_nan()` 在 loss 为 NaN 时逐参数检查梯度有没有 NaN/Inf（见代码块）。

#### 数据泄漏（Data Leakage）

测试集 99% 准确率？听起来很棒，其实是 bug：测试样本混进了训练集。用 id 集合求交集检查（`check_data_leakage`）。还要查**时间泄漏**——用未来数据预测过去：切分前先按时间戳排序。

#### 放错设备（Wrong Device）

tensor 分处 CPU/GPU 会报运行时错误；但有时某个 tensor 静默地留在 CPU 上、其他都在 GPU——训练照跑，只是慢得要死。`check_devices()` 逐个对比 tensor 与模型的 device（见代码块）。

> Shape Mismatch — the most frequent bug. NaN loss means something exploded (lr too high, division by zero, log of zero, exploding gradients). Data Leakage — your model gets 99% accuracy on the test set. Sounds great. It's a bug. Also check for temporal leakage: using future data to predict the past. Wrong Device — sometimes a tensor silently stays on CPU while everything else is on GPU, and training just runs slowly.


#### Shape 不匹配（最常见）

tensor 是 `[batch, features]`，模型却要 `[batch, channels, height, width]`。

```python
def check_shapes(model, sample_input):
    print(f"Input: {sample_input.shape}")
    hooks = []

    def make_hook(name):
        def hook(module, inp, out):
            in_shape = inp[0].shape if isinstance(inp, tuple) else inp.shape
            out_shape = out.shape if hasattr(out, "shape") else type(out)
            print(f"  {name}: {in_shape} -> {out_shape}")
        return hook

    for name, module in model.named_modules():
        hooks.append(module.register_forward_hook(make_hook(name)))

    with torch.no_grad():
        model(sample_input)

    for h in hooks:
        h.remove()
```

跑一遍就画出整个模型的 shape 变换地图。

#### NaN Loss

```python
def detect_nan(model, loss, step):
    if torch.isnan(loss):
        print(f"NaN loss at step {step}")
        for name, param in model.named_parameters():
            if param.grad is not None:
                if torch.isnan(param.grad).any():
                    print(f"  NaN gradient in {name}")
                if torch.isinf(param.grad).any():
                    print(f"  Inf gradient in {name}")
        return True
    return False
```

#### 数据泄漏（Data Leakage）

```python
def check_data_leakage(train_set, test_set, id_column="id"):
    train_ids = set(train_set[id_column].tolist())
    test_ids = set(test_set[id_column].tolist())
    overlap = train_ids & test_ids
    if overlap:
        print(f"DATA LEAKAGE: {len(overlap)} samples in both train and test")
        return True
    return False
```

#### 放错设备（Wrong Device）

```python
def check_devices(model, *tensors):
    model_device = next(model.parameters()).device
    print(f"Model device: {model_device}")
    for i, t in enumerate(tensors):
        if t.device != model_device:
            print(f"  WARNING: tensor {i} on {t.device}, model on {model_device}")
```

### Part 8：TensorBoard 入门

TensorBoard 让你看到训练内部随时间的变化。`SummaryWriter` 记录标量（loss、lr）和直方图（权重、梯度），`tensorboard --logdir=runs` 启动。

**看图诊断口诀**：

- **Loss 不降**：学习率太低，或模型结构问题
- **Loss 剧烈震荡**：学习率太高
- **Loss 变 NaN**：数值不稳定（见 NaN 一节）
- **训练 loss 降、验证 loss 升**：过拟合
- **权重直方图塌缩到 0**：梯度消失
- **梯度直方图爆炸**：需要梯度裁剪（gradient clipping）

> What to look for: Loss not decreasing → lr too low or architecture issue. Loss oscillating wildly → lr too high. Loss goes to NaN → numerical instability. Train loss decreasing, val loss increasing → overfitting. Weight histograms collapsing to zero → vanishing gradients. Gradient histograms exploding → need gradient clipping.


```bash
pip install tensorboard
```

```python
from torch.utils.tensorboard import SummaryWriter

writer = SummaryWriter("runs/experiment_1")

for step in range(num_steps):
    loss = train_step(model, batch)

    writer.add_scalar("loss/train", loss.item(), step)
    writer.add_scalar("lr", optimizer.param_groups[0]["lr"], step)

    if step % 100 == 0:
        for name, param in model.named_parameters():
            writer.add_histogram(f"weights/{name}", param, step)
            if param.grad is not None:
                writer.add_histogram(f"grads/{name}", param.grad, step)

writer.close()
```

```bash
tensorboard --logdir=runs
```

### Part 9：VS Code 调试器

交互式调试时，配一个 `launch.json`（type 为 `debugpy`，`justMyCode: false` 才能步进第三方库）。点行号槽设断点，用 Variables 面板看 tensor 属性，Debug Console 里能中途执行任意 Python 表达式。

适合步进数据预处理流水线——看每一步变换做了什么。

> For interactive debugging, configure VS Code with a `launch.json`. Set breakpoints by clicking the gutter. Use the Variables pane to inspect tensor properties. The Debug Console lets you run arbitrary Python expressions mid-execution. Useful for stepping through data preprocessing pipelines.


```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Training",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

## 学以致用（Use It）

抓大多数 AI bug 的调试工作流：

1. **训练前**：用 `check_shapes` 跑一个样本 batch，确认输入输出维度符合预期
2. **前 10 步**：对 loss、输出、梯度用 `debug_print`，确认没有 NaN、数值在合理范围
3. **训练中**：记录 loss、学习率、梯度范数，用 TensorBoard 可视化
4. **出问题时**：在故障点丢 `breakpoint()`，交互式检查 tensor
5. **性能**：给数据加载/前向/反向分别计时；快 OOM 了就剖析内存

> Here's the debugging workflow that catches most AI bugs: 1. Before training: Run `check_shapes` with a sample batch. 2. First 10 steps: Use `debug_print` on loss, outputs, and gradients. 3. During training: Log loss, learning rate, and gradient norms. Use TensorBoard. 4. When something breaks: Drop `breakpoint()` at the failure point. 5. For performance: Time your data loading vs forward vs backward pass.

## 跑起来（Ship It）

跑调试工具箱脚本：


```bash
python phases/00-setup-and-tooling/12-debugging-and-profiling/code/debug_tools.py
```

`outputs/prompt-debug-ai-code.md` 里有一个帮你诊断 AI 专用 bug 的提示词模板。

> Run the debugging toolkit script. See `outputs/prompt-debug-ai-code.md` for a prompt that helps diagnose AI-specific bugs.

## 练习（Exercises）

1. 跑 `debug_tools.py`，通读每节输出。改一下 dummy 模型制造一个 NaN（提示：forward 里除零），看检测器抓住它。
2. 用 `cProfile` 剖析一个训练循环，找出最慢的函数。
3. 用 `tracemalloc` 找出数据加载流水线里哪一行分配内存最多。
4. 给一次简单训练搭 TensorBoard，判断模型是否过拟合。
5. 在训练循环里用 `breakpoint()`，练习从调试器提示符检查 tensor 的 shape、device、梯度值。

> 1. Run `debug_tools.py` and read through each section's output. Modify the dummy model to introduce a NaN (hint: divide by zero in the forward pass) and watch the detector catch it.
> 2. Profile a training loop with `cProfile` and identify the slowest function.
> 3. Use `tracemalloc` to find which line in your data loading pipeline allocates the most memory.
> 4. Set up TensorBoard for a simple training run and identify whether the model is overfitting.
> 5. Use `breakpoint()` inside a training loop. Practice inspecting tensor shapes, devices, and gradient values from the debugger prompt.

## 实测数据与纠正（Measured Corrections）

本节内容来自实机跑 `code/debug_tools.py` 的输出（macOS Darwin 24.3 / Python 3.9.6，本机无 torch）。

1. **实测结果**：`python3 phases/00-setup-and-tooling/12-debugging-and-profiling/code/debug_tools.py` 在本机跑通了**非 PyTorch** 部分：

   - **Structured Logging** 输出四行演示（真实 logging 格式）：`Training started: lr=0.001, batch_size=32, epochs=10` → `Step 100: loss=2.3026, accuracy=0.10` → `Loss spike detected: 15.7 at step 450`（WARNING 级）→ `Step 1000: loss=0.4512, accuracy=0.87` → `Training complete: best_loss=0.3201`。日志格式 `"%(asctime)s [%(levelname)s] %(message)s"`，可以看到时间戳+级别在排错时的作用。
   - **tracemalloc** 输出前 5 大分配点（演示数据）：`debug_tools.py:136: size=3913 KiB, count=201, average=19.5 KiB`、`debug_tools.py:137: size=3906 KiB, count=2, average=1953 KiB`——逐行定位内存大户，正是 Part 6 教的方法。

2. **实测纠正：本机没有 PyTorch**。跑 torch 相关 demo（`debug_print`、`check_shapes`、`detect_nan`、`check_devices`、GPU 内存）需要先装 torch：

   ```bash
   # 本机（macOS）：
   uv pip install torch        # 用 uv 装到当前 venv（注意 UV_CACHE_DIR=$PWD/.uv-cache）
   # 或在云 GPU 机器 / WSL2 Ubuntu 上：
   sudo apt install -y python3-venv && python3 -m venv .venv && source .venv/bin/activate
   pip install torch
   ```

   装好后 `debug_tools.py` 会自动进入 PyTorch 模式，跑全部 9 个 demo。

3. **`breakpoint()` 实测提醒**：`demo_conditional_breakpoint()` 会真的把交互式调试器停住（`pdb` 提示符 `(Pdb)`）。在非交互终端里跑会卡住或报错——练习 5 请在自己的终端里做，别在脚本管道里跑。

4. **Python 版本差异**：本机 Python 3.9.6，`debug_tools.py` 兼容 3.8+（`f-string`、`dataclasses` 未用到高版本特性）。云 GPU 机器上常见 3.10/3.11，行为一致。

5. **教训级提醒（对应 Part 7 数据泄漏）**：测试集 99% 准确率先怀疑泄漏，别先庆祝——`check_data_leakage()` 按 id 集合求交集是最快的一票否决；时序数据记得**切分前按时间戳排序**，否则就是用未来预测过去。
