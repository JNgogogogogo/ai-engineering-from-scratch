# Introduction to JAX · JAX 入门

> PyTorch mutates tensors. TensorFlow builds graphs. JAX compiles pure functions. That last one changes how you think about deep learning.

**Type:** Build
**Languages:** Python
**Prerequisites:** Phase 03 Lessons 01-10, basic NumPy
**Time:** ~90 minutes

## Learning Objectives · 学习目标

- 用 JAX 的函数式 API（jax.numpy、jax.grad、jax.jit、jax.vmap）写纯函数式的神经网络代码
- 解释 PyTorch 的即时求变（eager mutation）与 JAX 的函数式编译模型之间的关键设计差异
- 相对朴素的 Python，应用 jit 编译和 vmap 向量化来加速训练循环
- 在 JAX 里训练一个简单网络，并对比其显式状态管理与 PyTorch 面向对象方法的差异

> Write pure-function neural network code using JAX's functional API (jax.numpy, jax.grad, jax.jit, jax.vmap)
> Explain the key design difference between PyTorch's eager mutation and JAX's functional compilation model
> Apply jit compilation and vmap vectorization to accelerate training loops compared to naive Python
> Train a simple network in JAX and contrast the explicit state management with PyTorch's object-oriented approach

---

## The Problem · 问题在哪

你已经会用 PyTorch 构建神经网络：定义一个 `nn.Module`，调用 `.backward()`，让优化器走一步。它能用，几百万人都在用。

但 PyTorch 的 DNA 里刻着一个约束：它在 Python 里逐个、即时地追踪操作。每个 `tensor + tensor` 都是一次独立的内核启动。每个训练步都在重新解释同样的 Python 代码。这一直没问题——直到你要在 2,048 块 TPU 上训练一个 5400 亿参数的模型。那时这些开销会杀死你。

Google DeepMind 用 JAX 训练 Gemini。Anthropic 用 JAX 训练 Claude。这些都不是小打小闹——它们是地球上最大规模的神经网络训练。他们选 JAX，是因为 JAX 把你的训练循环当作一个可编译的程序，而不是一串 Python 调用。

JAX 就是带三种超能力的 NumPy：自动微分、到 XLA 的 JIT 编译、自动向量化。你写一个处理单个样本的函数，JAX 给你一个能处理整个 batch、能算梯度、能编译成机器码、能跨多设备运行的函数。全程不改原来的函数。

> But PyTorch has a constraint baked into its DNA: it traces operations eagerly, one at a time, in Python. Every `tensor + tensor` is a separate kernel launch. Every training step re-interprets the same Python code. This works fine until you need to train a 540-billion-parameter model across 2,048 TPUs. Then the overhead kills you.
> Google DeepMind trains Gemini on JAX. Anthropic trained Claude on JAX. These are not small operations -- they are the largest neural network training runs on Earth. They chose JAX because it treats your training loop as a compilable program, not a sequence of Python calls.
> JAX is NumPy with three superpowers: automatic differentiation, JIT compilation to XLA, and automatic vectorization. You write a function that processes one example. JAX gives you a function that processes a batch, computes gradients, compiles to machine code, and runs across multiple devices. All without changing the original function.

---

## The Concept · 概念

### The JAX Philosophy · JAX 的哲学

JAX 是一个函数式框架。没有类，没有可变状态，没有 `.backward()` 方法。取而代之：

| PyTorch | JAX |
|---------|-----|
| `nn.Module` class with state | Pure function: `f(params, x) -> y` |
| `loss.backward()` | `jax.grad(loss_fn)(params, x, y)` |
| Eager execution（即时执行） | 经 XLA 的 JIT 编译 |
| `for x in batch:` manual loop | `jax.vmap(f)` auto-vectorization |
| `DataParallel` / `FSDP` | `jax.pmap(f)` auto-parallelism |
| Mutable `model.parameters()` | Immutable pytree of arrays |

这不是风格偏好，而是编译器的约束。JIT 编译要求纯函数——同样的输入永远产生同样的输出，没有副作用。正是这条限制让 100 倍加速成为可能。

> JAX is a functional framework. No classes, no mutable state, no `.backward()` method.
> This is not a style preference. It is a compiler constraint. JIT compilation requires pure functions -- same inputs always produce same outputs, no side effects. That restriction is what makes 100x speedups possible.

---

### jax.numpy: The Familiar Surface · jax.numpy：熟悉的那层皮

JAX 在加速器上重新实现了 NumPy API：

```python
import jax.numpy as jnp

a = jnp.array([1.0, 2.0, 3.0])
b = jnp.array([4.0, 5.0, 6.0])
c = jnp.dot(a, b)
```

同样的函数名、同样的广播规则、同样的切片语义。但数组活在 GPU/TPU 上，而且每个操作都能被编译器追踪。

一个关键区别：JAX 数组是不可变的。没有 `a[0] = 5`，取而代之是 `a = a.at[0].set(5)`。这会让你别扭一个星期，然后豁然开朗——不可变性正是 `grad`、`jit`、`vmap` 这些变换能够自由组合的原因。

> JAX reimplements the NumPy API on accelerators:
> Same function names. Same broadcasting rules. Same slicing semantics. But the arrays live on GPU/TPU, and every operation is traceable by the compiler.
> One critical difference: JAX arrays are immutable. No `a[0] = 5`. Instead: `a = a.at[0].set(5)`. This feels awkward for a week, then it clicks -- immutability is what makes transformations like `grad`, `jit`, and `vmap` composable.

---

### jax.grad: Functional Autodiff · jax.grad：函数式自动微分

PyTorch 把梯度挂在张量上（`.grad`）。JAX 把梯度挂在函数上。

```python
import jax

def f(x):
    return x ** 2

df = jax.grad(f)
df(3.0)
```

`jax.grad` 接收一个函数，返回一个计算梯度的新函数。没有 `.backward()` 调用，没有存在张量上的计算图。梯度只是另一个你可以调用、组合、JIT 编译的函数。

它可以任意组合：

```python
d2f = jax.grad(jax.grad(f))
d2f(3.0)
```

二阶导、三阶导、Jacobian、Hessian——全部靠组合 `grad` 得到。PyTorch 也能做（`torch.autograd.functional.hessian`），但那是外挂上去的。在 JAX 里，这是地基。

约束：`grad` 只对纯函数有效。函数里不能有 print 语句（它们在追踪期运行，不在执行期）。不能修改外部状态。没有显式 key 管理就不能生成随机数。

> PyTorch attaches gradients to tensors (`.grad`). JAX attaches gradients to functions.
> `jax.grad` takes a function and returns a new function that computes the gradient. No `.backward()` call. No computation graph stored on tensors. The gradient is just another function you can call, compose, or JIT-compile.
> This composes arbitrarily:
> Second derivatives. Third derivatives. Jacobians. Hessians. All by composing `grad`. PyTorch can do this too (`torch.autograd.functional.hessian`), but it is bolted on. In JAX, it is the foundation.
> The constraint: `grad` only works on pure functions. No print statements inside (they run during tracing, not execution). No mutation of external state. No random number generation without explicit key management.

---

### jit: Compile to XLA · jit：编译到 XLA

```python
@jax.jit
def train_step(params, x, y):
    loss = loss_fn(params, x, y)
    return loss

fast_step = jax.jit(train_step)
```

第一次调用时，JAX 追踪（trace）这个函数——它记录发生了哪些操作，而不真正执行。然后它把这份 trace 交给 XLA（Accelerated Linear Algebra），Google 面向 TPU 和 GPU 的编译器。XLA 融合操作、消除冗余内存拷贝、生成优化过的机器码。

后续调用完全跳过 Python。编译后的代码以 C++ 速度跑在加速器上。

JIT 有帮助的场景：
- 训练步（同样的计算重复几千次）
- 推理（同一个模型，不同输入）
- 任何会被形状相似的输入反复调用的函数

JIT 有害的场景：
- Python 控制流依赖具体值的函数（`if x > 0` 且 x 是被追踪的数组）
- 一次性计算（编译开销超过运行收益）
- 调试（tracing 会遮住真正的执行）

控制流的限制是真实的。`jax.lax.cond` 替代 `if/else`，`jax.lax.scan` 替代 `for` 循环。这些不是可选项——这是编译的代价。

> On the first call, JAX traces the function -- it records which operations happen, without executing them. Then it hands that trace to XLA (Accelerated Linear Algebra), Google's compiler for TPUs and GPUs. XLA fuses operations, eliminates redundant memory copies, and generates optimized machine code.
> Subsequent calls skip Python entirely. The compiled code runs on the accelerator at C++ speed.
> The control flow restriction is real. `jax.lax.cond` replaces `if/else`. `jax.lax.scan` replaces `for` loops. These are not optional -- they are the price of compilation.

---

### vmap: Automatic Vectorization · vmap：自动向量化

你写一个处理单个样本的函数：

```python
def predict(params, x):
    return jnp.dot(params['w'], x) + params['b']
```

`vmap` 把它抬升为处理一个 batch：

```python
batch_predict = jax.vmap(predict, in_axes=(None, 0))
```

`in_axes=(None, 0)` 的意思是：不对 `params` 分批（共享），对 `x` 的第 0 轴分批。没有手写 `for` 循环，没有 reshape，没有 batch 维度穿线。JAX 自己搞清楚 batch 维度，并把整个计算向量化。

这不是语法糖。`vmap` 生成融合的向量化代码，比 Python 循环快 10-100 倍。而且它能与 `jit` 和 `grad` 组合：

```python
per_example_grads = jax.vmap(jax.grad(loss_fn), in_axes=(None, 0, 0))
```

逐样本梯度，一行搞定。在 PyTorch 里不用 hack 几乎做不到。

> `in_axes=(None, 0)` means: do not batch over `params` (shared), batch over axis 0 of `x`. No manual `for` loop. No reshaping. No batch dimension threading. JAX figures out the batch dimension and vectorizes the entire computation.
> This is not syntactic sugar. `vmap` generates fused vectorized code that runs 10-100x faster than a Python loop. And it composes with `jit` and `grad`:
> Per-example gradients. One line. This is nearly impossible in PyTorch without hacks.

---

### pmap: Data Parallelism Across Devices · pmap：跨设备数据并行

```python
parallel_step = jax.pmap(train_step, axis_name='devices')
```

`pmap` 把函数复制到所有可用设备（GPU/TPU）上，并切分 batch。函数内部用 `jax.lax.pmean` 和 `jax.lax.psum` 跨设备同步梯度。

Google 用 `pmap`（以及它的后继 `shard_map`）在数千块 TPU v5e 芯片上训练 Gemini。编程模型是：写单设备版本，套上 `pmap`，完事。

> `pmap` replicates the function across all available devices (GPUs/TPUs) and splits the batch. Inside the function, `jax.lax.pmean` and `jax.lax.psum` synchronize gradients across devices.
> Google trains Gemini across thousands of TPU v5e chips using `pmap` (and its successor `shard_map`). The programming model: write the single-device version, wrap with `pmap`, done.

---

### Pytrees: The Universal Data Structure · Pytrees：通用数据结构

JAX 操作的是「pytree」——列表、元组、字典和数组的嵌套组合。你的模型参数就是一个 pytree：

```python
params = {
    'layer1': {'w': jnp.zeros((784, 256)), 'b': jnp.zeros(256)},
    'layer2': {'w': jnp.zeros((256, 128)), 'b': jnp.zeros(128)},
    'layer3': {'w': jnp.zeros((128, 10)),  'b': jnp.zeros(10)},
}
```

每个 JAX 变换——`grad`、`jit`、`vmap`——都知道怎么遍历 pytree。`jax.tree.map(f, tree)` 把 `f` 应用到每个叶子。优化器就是这样一次性更新所有参数的：

```python
params = jax.tree.map(lambda p, g: p - lr * g, params, grads)
```

没有 `.parameters()` 方法，没有参数注册。树结构本身就是模型。

> JAX operates on "pytrees" -- nested combinations of lists, tuples, dicts, and arrays. Your model parameters are a pytree.
> Every JAX transformation -- `grad`, `jit`, `vmap` -- knows how to traverse pytrees. `jax.tree.map(f, tree)` applies `f` to every leaf. This is how optimizers update all parameters at once:
> No `.parameters()` method. No parameter registration. The tree structure is the model.

---

### Functional vs Object-Oriented · 函数式 vs 面向对象

PyTorch 把状态存在对象里：

```python
class Model(nn.Module):
    def __init__(self):
        self.linear = nn.Linear(784, 10)

    def forward(self, x):
        return self.linear(x)
```

JAX 用带显式状态的纯函数：

```python
def predict(params, x):
    return jnp.dot(x, params['w']) + params['b']
```

params 被传进来。什么都不存储，什么都不修改。这让每个函数都可测试、可组合、可编译。代价是你要自己管理 params——或者用 Flax、Equinox 这样的库。

> PyTorch stores state inside objects:
> JAX uses pure functions with explicit state:
> The params are passed in. Nothing is stored. Nothing is mutated. This makes every function testable, composable, and compilable. It also means you manage the params yourself -- or use a library like Flax or Equinox.

---

### The JAX Ecosystem · JAX 生态

JAX 给你原语，库给你人体工学：

| 库 | 角色 | 风格 |
|---------|------|-------|
| **Flax** (Google) | 神经网络层 | 带显式状态的 `nn.Module` |
| **Equinox** (Patrick Kidger) | 神经网络层 | 基于 pytree，Pythonic |
| **Optax** (DeepMind) | 优化器 + 学习率调度 | 可组合的梯度变换 |
| **Orbax** (Google) | 检查点 | 保存/恢复 pytree |
| **CLU** (Google) | 指标 + 日志 | 训练循环工具集 |

Optax 是标准的优化器库。它把梯度变换（Adam、SGD、裁剪）与参数更新分开，组合起来毫不费力：

```python
optimizer = optax.chain(
    optax.clip_by_global_norm(1.0),
    optax.adam(learning_rate=1e-3),
)
```

> JAX gives you primitives. Libraries give you ergonomics:
> Optax is the standard optimizer library. It separates the gradient transformation (Adam, SGD, clipping) from the parameter update, making it trivial to compose:

---

### When to Use JAX vs PyTorch · 何时用 JAX，何时用 PyTorch

| 因素 | JAX | PyTorch |
|--------|-----|---------|
| TPU 支持 | 一等公民（Google 两者皆造） | 社区维护（torch_xla） |
| GPU 支持 | 良好（经 XLA 的 CUDA） | 最佳（原生 CUDA） |
| 调试 | 难（tracing + 编译） | 容易（eager，逐行） |
| 生态 | 偏研究（Flax、Equinox） | 庞大（HuggingFace、torchvision 等） |
| 招聘 | 小众（Google/DeepMind/Anthropic） | 主流（到处都要） |
| 大规模训练 | 更强（XLA、pmap、mesh） | 良好（FSDP、DeepSpeed） |
| 原型速度 | 较慢（函数式的额外负担） | 较快（改了就跑） |
| 生产推理 | TensorFlow Serving、Vertex AI | TorchServe、Triton、ONNX |
| 谁在用 | DeepMind（Gemini）、Anthropic（Claude） | Meta（Llama）、OpenAI（GPT）、Stability AI |

诚实的答案：除非你有明确理由要用 JAX，否则用 PyTorch。那些理由是——能用 TPU、需要逐样本梯度、超大规模多设备训练，或者在 Google/DeepMind/Anthropic 工作。

> The honest answer: use PyTorch unless you have a specific reason to use JAX. Those reasons are -- TPU access, need for per-example gradients, multi-device training at massive scale, or working at Google/DeepMind/Anthropic.

---

### Random Numbers in JAX · JAX 里的随机数

JAX 没有全局随机状态。每个随机操作都需要显式的 PRNG key：

```python
key = jax.random.PRNGKey(42)
key1, key2 = jax.random.split(key)
w = jax.random.normal(key1, shape=(784, 256))
```

一开始很烦。但它保证了跨设备、跨编译的可复现性——这是 PyTorch 的 `torch.manual_seed` 在多 GPU 环境下给不了的保证。

> JAX does not have a global random state. Every random operation requires an explicit PRNG key:
> This is annoying at first. But it guarantees reproducibility across devices and compilations -- a property that PyTorch's `torch.manual_seed` cannot guarantee in multi-GPU settings.

```figure
batchnorm-effect
```

---

## Build It · 动手造

### Step 1: Setup and Data · 步骤 1：环境与数据

我们将用 JAX 和 Optax 在 MNIST 上训练一个 3 层 MLP。784 个输入，两个隐层分别有 256 和 128 个神经元，10 个输出类别。

```python
import jax
import jax.numpy as jnp
from jax import random
import optax

def get_mnist_data():
    from sklearn.datasets import fetch_openml
    mnist = fetch_openml('mnist_784', version=1, as_frame=False, parser='auto')
    X = mnist.data.astype('float32') / 255.0
    y = mnist.target.astype('int')
    X_train, X_test = X[:60000], X[60000:]
    y_train, y_test = y[:60000], y[60000:]
    return X_train, y_train, X_test, y_test
```

> We will train a 3-layer MLP on MNIST using JAX and Optax. 784 inputs, two hidden layers of 256 and 128 neurons, 10 output classes.

### Step 2: Initialize Parameters · 步骤 2：初始化参数

没有类。只有一个返回 pytree 的函数：

```python
def init_params(key):
    k1, k2, k3 = random.split(key, 3)
    scale1 = jnp.sqrt(2.0 / 784)
    scale2 = jnp.sqrt(2.0 / 256)
    scale3 = jnp.sqrt(2.0 / 128)
    params = {
        'layer1': {
            'w': scale1 * random.normal(k1, (784, 256)),
            'b': jnp.zeros(256),
        },
        'layer2': {
            'w': scale2 * random.normal(k2, (256, 128)),
            'b': jnp.zeros(128),
        },
        'layer3': {
            'w': scale3 * random.normal(k3, (128, 10)),
            'b': jnp.zeros(10),
        },
    }
    return params
```

He 初始化，手动完成。三个 PRNG key 从一个种子分裂而来。每个权重都是嵌套字典里一个不可变数组。

> No class. Just a function that returns a pytree:
> He-initialization, done manually. Three PRNG keys split from one seed. Every weight is an immutable array in a nested dict.

### Step 3: Forward Pass · 步骤 3：前向传播

```python
def forward(params, x):
    x = jnp.dot(x, params['layer1']['w']) + params['layer1']['b']
    x = jax.nn.relu(x)
    x = jnp.dot(x, params['layer2']['w']) + params['layer2']['b']
    x = jax.nn.relu(x)
    x = jnp.dot(x, params['layer3']['w']) + params['layer3']['b']
    return x

def loss_fn(params, x, y):
    logits = forward(params, x)
    one_hot = jax.nn.one_hot(y, 10)
    return -jnp.mean(jnp.sum(jax.nn.log_softmax(logits) * one_hot, axis=-1))
```

纯函数。params 进，预测出。没有 `self`，没有存储的状态。`loss_fn` 从零计算交叉熵——softmax、取 log、负均值。

> Pure functions. Params in, prediction out. No `self`, no stored state. `loss_fn` computes cross-entropy from scratch -- softmax, log, negative mean.

### Step 4: JIT-Compiled Training Step · 步骤 4：JIT 编译的训练步

```python
@jax.jit
def train_step(params, opt_state, x, y):
    loss, grads = jax.value_and_grad(loss_fn)(params, x, y)
    updates, opt_state = optimizer.update(grads, opt_state, params)
    params = optax.apply_updates(params, updates)
    return params, opt_state, loss

@jax.jit
def accuracy(params, x, y):
    logits = forward(params, x)
    preds = jnp.argmax(logits, axis=-1)
    return jnp.mean(preds == y)
```

`jax.value_and_grad` 一次前向同时返回 loss 值和梯度。`@jax.jit` 装饰器把两个函数都编译到 XLA。第一次调用之后，每个训练步完全不经过 Python。

> `jax.value_and_grad` returns both the loss value and the gradients in one pass. The `@jax.jit` decorator compiles both functions to XLA. After the first call, each training step runs without touching Python.

### Step 5: Training Loop · 步骤 5：训练循环

```python
optimizer = optax.adam(learning_rate=1e-3)

X_train, y_train, X_test, y_test = get_mnist_data()
X_train, X_test = jnp.array(X_train), jnp.array(X_test)
y_train, y_test = jnp.array(y_train), jnp.array(y_test)

key = random.PRNGKey(0)
params = init_params(key)
opt_state = optimizer.init(params)

batch_size = 128
n_epochs = 10

for epoch in range(n_epochs):
    key, subkey = random.split(key)
    perm = random.permutation(subkey, len(X_train))
    X_shuffled = X_train[perm]
    y_shuffled = y_train[perm]

    epoch_loss = 0.0
    n_batches = len(X_train) // batch_size
    for i in range(n_batches):
        start = i * batch_size
        xb = X_shuffled[start:start + batch_size]
        yb = y_shuffled[start:start + batch_size]
        params, opt_state, loss = train_step(params, opt_state, xb, yb)
        epoch_loss += loss

    train_acc = accuracy(params, X_train[:5000], y_train[:5000])
    test_acc = accuracy(params, X_test, y_test)
    print(f"Epoch {epoch + 1:2d} | Loss: {epoch_loss / n_batches:.4f} | "
          f"Train Acc: {train_acc:.4f} | Test Acc: {test_acc:.4f}")
```

10 个 epoch，约 97% 测试准确率。第一个 epoch 慢（JIT 编译），第 2-10 个 epoch 很快。

注意少了什么：没有 `.zero_grad()`，没有 `.backward()`，没有 `.step()`。整个更新就是一次组合函数调用。梯度被计算、被 Adam 变换、被应用到参数——全部在 `train_step` 里完成。

> 10 epochs. ~97% test accuracy. The first epoch is slow (JIT compilation). Epochs 2-10 are fast.
> Notice what is missing: no `.zero_grad()`, no `.backward()`, no `.step()`. The entire update is one composed function call. Gradients are computed, transformed by Adam, and applied to parameters -- all inside `train_step`.

---

## Use It · 实战用法

### Flax: The Google Standard · Flax：Google 的标准

Flax 是最常用的 JAX 神经网络库。它把 `nn.Module` 加了回来，但状态是显式管理的：

```python
import flax.linen as nn

class MLP(nn.Module):
    @nn.compact
    def __call__(self, x):
        x = nn.Dense(256)(x)
        x = nn.relu(x)
        x = nn.Dense(128)(x)
        x = nn.relu(x)
        x = nn.Dense(10)(x)
        return x

model = MLP()
params = model.init(jax.random.PRNGKey(0), jnp.ones((1, 784)))
logits = model.apply(params, x_batch)
```

结构与 PyTorch 相同，但 `params` 与模型是分开的。`model.init()` 创建 params，`model.apply(params, x)` 执行前向传播。模型对象本身没有状态。

> Flax is the most common JAX neural network library. It adds `nn.Module` back, but with explicit state management:
> Same structure as PyTorch, but `params` is separate from the model. `model.init()` creates params. `model.apply(params, x)` runs the forward pass. The model object has no state.

### Equinox: The Pythonic Alternative · Equinox：更 Pythonic 的替代品

Equinox（Patrick Kidger 所作）把模型表示为 pytree：

```python
import equinox as eqx

model = eqx.nn.MLP(
    in_size=784, out_size=10, width_size=256, depth=2,
    activation=jax.nn.relu, key=jax.random.PRNGKey(0)
)
logits = model(x)
```

模型本身就是 pytree。不需要 `.apply()`。参数就是模型的叶子。这更接近 JAX 的思维方式。

> Equinox (by Patrick Kidger) represents models as pytrees:
> The model itself is a pytree. No `.apply()` needed. Parameters are just the model's leaves. This is closer to how JAX thinks.

### Optax: Composable Optimizers · Optax：可组合的优化器

Optax 把梯度变换与参数更新解耦：

```python
schedule = optax.warmup_cosine_decay_schedule(
    init_value=0.0, peak_value=1e-3,
    warmup_steps=1000, decay_steps=50000
)

optimizer = optax.chain(
    optax.clip_by_global_norm(1.0),
    optax.adamw(learning_rate=schedule, weight_decay=0.01),
)
```

梯度裁剪、学习率 warmup、weight decay——全部作为一串变换链组合起来。每个变换接收梯度、修改梯度、传给下一个。没有大而全的优化器类。

> Optax decouples the gradient transformation from the update:
> Gradient clipping, learning rate warmup, weight decay -- all composed as a chain of transforms. Each transform sees the gradients, modifies them, and passes them to the next. No monolithic optimizer class.

---

## Ship It · 交付

**安装：**

```bash
pip install jax jaxlib optax flax
```

GPU 支持：

```bash
pip install jax[cuda12]
```

TPU（Google Cloud）：

```bash
pip install jax[tpu] -f https://storage.googleapis.com/jax-releases/libtpu_releases.html
```

**性能坑点：**

- 第一次 JIT 调用很慢（编译）。跑分之前先预热。
- 避免在 JIT 内用 Python 循环遍历 JAX 数组。用 `jax.lax.scan` 或 `jax.lax.fori_loop`。
- `jax.debug.print()` 在 JIT 内可用。普通 `print()` 不行。
- 用 `jax.profiler` 或 TensorBoard 做性能分析。XLA 编译会掩盖瓶颈。
- JAX 默认预分配 75% 的 GPU 内存。设 `XLA_PYTHON_CLIENT_PREALLOCATE=false` 可关闭。

**Checkpointing：**

```python
import orbax.checkpoint as ocp
checkpointer = ocp.PyTreeCheckpointer()
checkpointer.save('/tmp/model', params)
restored = checkpointer.restore('/tmp/model')
```

**本课产出：**
- `outputs/prompt-jax-optimizer.md` —— 选择正确 JAX 优化器配置的提示词
- `outputs/skill-jax-patterns.md` —— 覆盖 JAX 函数式模式的技能

---

## Exercises · 练习

1. 给 MLP 加 dropout。在 JAX 里 dropout 需要 PRNG key——把一个 key 穿过前向传播，并为每个 dropout 层分裂它。对比开与不开的测试准确率。

2. 用 `jax.vmap` 计算 32 张 MNIST 图片的逐样本梯度。算出每个样本的梯度范数。哪些样本梯度最大，为什么？

3. 把手写的 forward 函数换成通用的 `mlp_forward(params, x)`，能处理任意层数。用 `jax.tree.leaves` 自动判断深度。

4. 对比有与没有 `@jax.jit` 的训练步性能。各计时 100 步。你的硬件上加速比多大？第一次调用的编译开销是多少？

5. 用 `optax.chain(optax.clip_by_global_norm(1.0), optax.adam(1e-3))` 实现梯度裁剪。开与不开裁剪各训练一次。画出训练过程中的梯度范数，观察效果。

---

## Key Terms · 术语表

| 术语 | 大家怎么说 | 实际含义 |
|------|----------------|----------------------|
| XLA | 「让 JAX 变快的那个东西」 | Accelerated Linear Algebra——一个把操作融合、从计算图生成优化 GPU/TPU 内核的编译器 |
| JIT | 「即时编译」 | JAX 在首次调用时追踪函数、编译到 XLA，之后的调用直接运行编译版本 |
| Pure function | 「没有副作用」 | 输出只依赖输入的函数——没有全局状态、没有修改、没有显式 key 就没有随机性 |
| vmap | 「自动分批」 | 把处理单个样本的函数变成处理一个 batch 的函数，无需重写 |
| pmap | 「自动并行」 | 把函数复制到多个设备上并切分输入 batch |
| Pytree | 「嵌套的数组字典」 | 任何 JAX 能遍历和变换的列表、元组、字典、数组的嵌套结构 |
| Tracing | 「记录计算」 | JAX 用抽象值执行函数来构建计算图，不计算真实结果 |
| Functional autodiff | 「对函数求 grad」 | 通过变换函数来求导，而不是把梯度存储挂在张量上 |
| Optax | 「JAX 的优化器库」 | 一个可组合的梯度变换库——Adam、SGD、裁剪、调度——可以链在一起 |
| Flax | 「JAX 的 nn.Module」 | Google 的 JAX 神经网络库，在保持状态显式的前提下加入层抽象 |

---

## Further Reading · 延伸阅读

- JAX documentation: https://jax.readthedocs.io/ —— 官方文档，grad、jit、vmap 的教程非常出色
- "JAX: composable transformations of Python+NumPy programs" (Bradbury et al., 2018) —— 解释设计哲学的原始论文
- Flax documentation: https://flax.readthedocs.io/ —— Google 的 JAX 神经网络库
- Patrick Kidger, "Equinox: neural networks in JAX via callable PyTrees and filtered transformations" (2021) —— Flax 之外的 Pythonic 替代品
- DeepMind, "Optax: composable gradient transformation and optimisation" —— 标准优化器库
- "You Don't Know JAX" (Colin Raffel, 2020) —— 一位 T5 作者写的 JAX 坑点与模式实战指南
