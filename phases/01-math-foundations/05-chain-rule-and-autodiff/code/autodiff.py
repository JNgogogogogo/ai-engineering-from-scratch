"""反向模式自动微分引擎（标量版）。

配套讲义：phases/01-math-foundations/05-chain-rule-and-autodiff/docs/en.md
核心思想：用 Value 节点记录计算图，前向算数值，反向按拓扑逆序传播梯度（链式法则）。
不依赖任何第三方库，纯 Python 实现，便于对照 torch.autograd 的行为验证正确性。
"""

import random


class Value:
    """计算图中的一个标量节点。

    属性：
      data    —— 当前节点的数值（前向传播结果）。
      grad    —— 目标输出对该节点的导数 ∂y/∂node（反向传播结果）。
                  默认 0.0；同一个节点被多条路径使用时，各路径贡献会累加（多元链式法则）。
      _backward —— 闭包，执行“本节点到其直接输入”的一步反向传播（局部梯度 × 上游梯度）。
      _prev   —— 直接父节点集合，用于构建计算图与拓扑排序。
      _op     —— 产生本节点的算子名，仅用于调试/打印。
    """

    def __init__(self, data, children=(), op=''):
        self.data = float(data)
        self.grad = 0.0
        self._backward = lambda: None   # 叶节点（输入/参数）无上游，反向为空操作
        self._prev = set(children)
        self._op = op

    def __repr__(self):
        return f"Value(data={self.data:.4f}, grad={self.grad:.4f})"

    def __add__(self, other):
        # 支持 Value + 标量：把标量包装成常量节点，便于统一建图
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data + other.data, (self, other), '+')
        def _backward():
            # z = a + b  ⇒  ∂z/∂a = 1, ∂z/∂b = 1
            # 链式法则：∂L/∂a += ∂L/∂z * 1，即把上游梯度原样传给两个输入
            self.grad += out.grad
            other.grad += out.grad
        out._backward = _backward
        return out

    def __radd__(self, other):
        # 标量 + Value 走这里（Python 交换律回退）
        return self.__add__(other)

    def __mul__(self, other):
        # z = a * b  ⇒  ∂z/∂a = b, ∂z/∂b = a（互为对方数值）
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data * other.data, (self, other), '*')
        def _backward():
            # 注意用的是前向时的数值（other.data / self.data），不是梯度
            self.grad += other.data * out.grad
            other.grad += self.data * out.grad
        out._backward = _backward
        return out

    def __rmul__(self, other):
        # 标量 * Value 走这里
        return self.__mul__(other)

    def __neg__(self):
        # -a 等价于 a * (-1)，复用乘法的反向规则
        return self * -1

    def __sub__(self, other):
        # a - b = a + (-b)，复用加法与取负
        return self + (-other)

    def __rsub__(self, other):
        # 标量 - Value
        return other + (-self)

    def __pow__(self, n):
        # z = a^n  ⇒  ∂z/∂a = n * a^(n-1)（幂函数求导公式）
        # n 在此实现中为常量指数，不参与求导
        out = Value(self.data ** n, (self,), f'**{n}')
        def _backward():
            self.grad += n * (self.data ** (n - 1)) * out.grad
        out._backward = _backward
        return out

    def __truediv__(self, other):
        # a / b = a * b^(-1)，把除法归约到乘法 + 幂，无需单独写反向
        return self * (other ** -1) if isinstance(other, Value) else self * (Value(other) ** -1)

    def relu(self):
        # z = max(0, a)  ⇒  ∂z/∂a = 1 (a > 0) 或 0 (a <= 0)
        # a = 0 处不可导，此处按惯例取 0；用输出 out.data > 0 判断激活区域
        out = Value(max(0, self.data), (self,), 'relu')
        def _backward():
            self.grad += (1.0 if out.data > 0 else 0.0) * out.grad
        out._backward = _backward
        return out

    def tanh(self):
        import math
        t = math.tanh(self.data)
        # z = tanh(a)  ⇒  ∂z/∂a = 1 - tanh²(a) = 1 - t²
        # 前向时缓存 t，反向直接复用，避免重复计算
        out = Value(t, (self,), 'tanh')
        def _backward():
            self.grad += (1 - t ** 2) * out.grad
        out._backward = _backward
        return out

    def exp(self):
        import math
        e = math.exp(self.data)
        # z = e^a  ⇒  ∂z/∂a = e^a（导数等于自身），前向缓存 e 供反向使用
        out = Value(e, (self,), 'exp')
        def _backward():
            self.grad += e * out.grad
        out._backward = _backward
        return out

    def log(self):
        import math
        # z = ln(a)  ⇒  ∂z/∂a = 1/a（要求 a > 0）
        out = Value(math.log(self.data), (self,), 'log')
        def _backward():
            self.grad += (1.0 / self.data) * out.grad
        out._backward = _backward
        return out

    def backward(self):
        """反向传播：从本节点（通常是最终 loss）出发，计算图中所有节点的梯度。

        步骤：
          1. 深度优先构建拓扑排序 topo —— 保证每个节点排在其所有使用者之前，
             这样逆序遍历时，上游梯度一定已经累加完毕。
          2. 种子梯度：输出对自身的导数为 1（∂y/∂y = 1）。
          3. 逆拓扑序依次调用每个节点的 _backward()，沿链式法则把梯度传给输入。
        """
        topo = []
        visited = set()
        def build_topo(v):
            # 后序遍历：先处理完所有子节点，再把当前节点追加进 topo
            if v not in visited:
                visited.add(v)
                for child in v._prev:
                    build_topo(child)
                topo.append(v)
        build_topo(self)

        self.grad = 1.0
        for v in reversed(topo):
            v._backward()


def demo_basic():
    print("=== Basic: y = relu(x1 * x2 + 1) ===")
    x1 = Value(2.0)
    x2 = Value(3.0)
    a = x1 * x2
    b = a + Value(1.0)
    y = b.relu()
    y.backward()
    # 手工推导：y = x1*x2 + 1（relu 处于激活区），故 dy/dx1 = x2 = 3, dy/dx2 = x1 = 2

    print(f"  x1 = 2.0, x2 = 3.0")
    print(f"  y  = {y.data}")
    print(f"  dy/dx1 = {x1.grad}  (expected 3.0 = x2)")
    print(f"  dy/dx2 = {x2.grad}  (expected 2.0 = x1)")
    assert abs(x1.grad - 3.0) < 1e-6
    assert abs(x2.grad - 2.0) < 1e-6
    print("  PASSED\n")


def demo_power():
    print("=== Power: y = x^3, dy/dx at x=2 ===")
    x = Value(2.0)
    y = x ** 3
    y.backward()
    # dy/dx = 3x²，x=2 时为 12

    print(f"  x = 2.0")
    print(f"  y = {y.data}  (expected 8.0)")
    print(f"  dy/dx = {x.grad}  (expected 12.0 = 3*x^2)")
    assert abs(x.grad - 12.0) < 1e-6
    print("  PASSED\n")


def demo_complex():
    print("=== Complex: f = relu(a*b + c) ===")
    a = Value(2.0)
    b = Value(-3.0)
    c = Value(10.0)
    f = (a * b + c).relu()
    f.backward()
    # 前向：a*b+c = -6+10 = 4 > 0，relu 激活
    # df/da = b = -3，df/db = a = 2，df/dc = 1（加法原样传递）

    print(f"  a=2, b=-3, c=10")
    print(f"  f = {f.data}  (expected 4.0)")
    print(f"  df/da = {a.grad}  (expected -3.0 = b)")
    print(f"  df/db = {b.grad}  (expected 2.0 = a)")
    print(f"  df/dc = {c.grad}  (expected 1.0)")
    assert abs(a.grad - (-3.0)) < 1e-6
    assert abs(b.grad - 2.0) < 1e-6
    assert abs(c.grad - 1.0) < 1e-6
    print("  PASSED\n")


def demo_neuron():
    print("=== Single neuron: y = relu(w1*x1 + w2*x2 + b) ===")
    w1 = Value(0.5)
    w2 = Value(-1.5)
    x1 = Value(3.0)
    x2 = Value(2.0)
    b = Value(0.1)

    y = (w1 * x1 + w2 * x2 + b).relu()
    y.backward()
    # 激活时：dy/dw1 = x1, dy/dw2 = x2, dy/dx1 = w1, dy/dx2 = w2, dy/db = 1
    # 未激活（pre <= 0）时：relu 导数为 0，所有梯度归零

    print(f"  w1=0.5, w2=-1.5, x1=3.0, x2=2.0, b=0.1")
    print(f"  pre_act = {w1.data*x1.data + w2.data*x2.data + b.data}")
    print(f"  y = {y.data}")
    print(f"  dy/dw1 = {w1.grad}")
    print(f"  dy/dw2 = {w2.grad}")
    print(f"  dy/dx1 = {x1.grad}")
    print(f"  dy/dx2 = {x2.grad}")
    print(f"  dy/db  = {b.grad}")

    pre = w1.data * x1.data + w2.data * x2.data + b.data
    if pre > 0:
        assert abs(w1.grad - x1.data) < 1e-6
        assert abs(w2.grad - x2.data) < 1e-6
        assert abs(x1.grad - w1.data) < 1e-6
        assert abs(x2.grad - w2.data) < 1e-6
        assert abs(b.grad - 1.0) < 1e-6
        print("  PASSED (relu active)\n")
    else:
        assert abs(w1.grad) < 1e-6
        assert abs(w2.grad) < 1e-6
        print("  PASSED (relu inactive, all grads zero)\n")


class Neuron:
    """单个神经元：act = tanh(w·x + b)。"""

    def __init__(self, n_inputs):
        # 权重随机初始化到 [-1, 1]，偏置初始为 0
        self.w = [Value(random.uniform(-1, 1)) for _ in range(n_inputs)]
        self.b = Value(0.0)

    def __call__(self, x):
        # sum(generator, self.b) 以偏置为初值累加 w_i * x_i，即仿射变换
        act = sum((wi * xi for wi, xi in zip(self.w, x)), self.b)
        return act.tanh()

    def parameters(self):
        return self.w + [self.b]


class Layer:
    """一层：n_outputs 个独立神经元，输入相同、输出为列表。"""

    def __init__(self, n_inputs, n_outputs):
        self.neurons = [Neuron(n_inputs) for _ in range(n_outputs)]

    def __call__(self, x):
        out = [n(x) for n in self.neurons]
        return out

    def parameters(self):
        # 展平本层所有神经元的参数，供统一优化
        return [p for n in self.neurons for p in n.parameters()]


class MLP:
    """多层感知机：按 sizes 逐层堆叠，如 [2, 4, 1] 表示 2 输入、4 隐单元、1 输出。"""

    def __init__(self, sizes):
        self.layers = [Layer(sizes[i], sizes[i + 1]) for i in range(len(sizes) - 1)]

    def __call__(self, x):
        for layer in self.layers:
            x = layer(x)
        # 单输出时去掉列表包装，方便直接与标量目标比较
        return x[0] if len(x) == 1 else x

    def parameters(self):
        return [p for layer in self.layers for p in layer.parameters()]


def gradient_check(build_expr, x_val, h=1e-7):
    """数值微分 vs 自动微分的梯度校验。

    中心差分公式：f'(x) ≈ (f(x+h) - f(x-h)) / (2h)，精度 O(h²)。
    返回 (自动微分梯度, 数值梯度, 绝对误差)，用于验证反向传播实现的正确性。
    """
    x = Value(x_val)
    y = build_expr(x)
    y.backward()
    autodiff_grad = x.grad

    y_plus = build_expr(Value(x_val + h)).data
    y_minus = build_expr(Value(x_val - h)).data
    numerical_grad = (y_plus - y_minus) / (2 * h)

    diff = abs(autodiff_grad - numerical_grad)
    return autodiff_grad, numerical_grad, diff


def demo_mlp_training():
    print("=== Mini MLP Training on XOR ===")
    random.seed(42)                 # 固定随机种子，训练过程可复现
    model = MLP([2, 4, 1])

    # XOR 是线性不可分问题，需要至少一个隐层才能学会
    xs = [[Value(0), Value(0)], [Value(0), Value(1)],
          [Value(1), Value(0)], [Value(1), Value(1)]]
    ys = [-1.0, 1.0, 1.0, -1.0]

    for step in range(100):
        preds = [model(x) for x in xs]
        # 均方误差 loss = Σ (pred - target)²；Value(-y) 借 radd/加法构造常量
        loss = sum((p + Value(-y)) ** 2 for p, y in zip(preds, ys))

        # 每轮先清零梯度（backward 是累加语义，否则梯度会跨步叠加）
        for p in model.parameters():
            p.grad = 0.0
        loss.backward()

        lr = 0.05                    # 学习率
        for p in model.parameters():
            p.data -= lr * p.grad    # 手写梯度下降：θ ← θ - lr * ∂loss/∂θ

        if step % 20 == 0 or step == 99:
            print(f"  step {step:3d}  loss = {loss.data:.4f}")

    print("\n  Predictions after training:")
    for x, y in zip(xs, ys):
        pred = model(x)
        sign = "+" if pred.data > 0 else "-"
        print(f"    input=[{x[0].data:.0f},{x[1].data:.0f}]  target={y:+.0f}  pred={pred.data:+.3f} ({sign})")
    print("  DONE\n")


def demo_gradient_check():
    print("=== Gradient Checking ===")

    # 用 λ 表达式把每个表达式构造成“以 x 为唯一叶子”的计算图
    expressions = [
        ("x^3 + 2x + 1",       lambda x: x ** 3 + x * 2 + 1),
        ("tanh(x^2)",           lambda x: (x ** 2).tanh()),
        ("(x+1) / (x^2+1)",    lambda x: (x + 1) * ((x ** 2 + 1) ** -1)),
        ("exp(x) * x",         lambda x: x.exp() * x),
        ("log(x^2 + 1)",       lambda x: (x ** 2 + 1).log()),
    ]

    print(f"  {'Expression':<22} {'Autodiff':>12} {'Numerical':>12} {'Diff':>12}")
    print("  " + "-" * 60)

    all_passed = True
    for name, expr in expressions:
        ad, num, diff = gradient_check(expr, 0.5)
        status = "OK" if diff < 1e-5 else "FAIL"
        if diff >= 1e-5:
            all_passed = False
        print(f"  {name:<22} {ad:12.8f} {num:12.8f} {diff:12.2e}  {status}")

    if all_passed:
        print("  ALL CHECKS PASSED\n")
    else:
        print("  SOME CHECKS FAILED\n")


def demo_exp_log():
    print("=== Exp and Log operations ===")
    x = Value(2.0)
    y = x.exp()
    y.backward()
    import math
    # d/dx exp(x) = exp(x)，x=2 时梯度即 exp(2)
    print(f"  exp(2.0) = {y.data:.4f}  (expected {math.exp(2.0):.4f})")
    print(f"  d/dx exp(x) at x=2 = {x.grad:.4f}  (expected {math.exp(2.0):.4f})")
    assert abs(x.grad - math.exp(2.0)) < 1e-4
    print("  PASSED\n")

    x = Value(3.0)
    y = x.log()
    y.backward()
    # d/dx log(x) = 1/x，x=3 时梯度为 1/3
    print(f"  log(3.0) = {y.data:.4f}  (expected {math.log(3.0):.4f})")
    print(f"  d/dx log(x) at x=3 = {x.grad:.4f}  (expected {1/3:.4f})")
    assert abs(x.grad - 1.0 / 3.0) < 1e-4
    print("  PASSED\n")


def demo_verify_pytorch():
    print("=== Verify against PyTorch ===")
    try:
        import torch
    except ImportError:
        print("  PyTorch not installed, skipping verification.\n")
        return

    # 同一表达式分别用本引擎与 torch.autograd 计算梯度并逐项比对
    x1_v = Value(2.0)
    x2_v = Value(3.0)
    y_v = (x1_v * x2_v + 1.0).relu()
    y_v.backward()

    x1_t = torch.tensor(2.0, requires_grad=True)
    x2_t = torch.tensor(3.0, requires_grad=True)
    y_t = torch.relu(x1_t * x2_t + 1.0)
    y_t.backward()

    print(f"  Our engine: dy/dx1={x1_v.grad}, dy/dx2={x2_v.grad}")
    print(f"  PyTorch:    dy/dx1={x1_t.grad.item()}, dy/dx2={x2_t.grad.item()}")
    assert abs(x1_v.grad - x1_t.grad.item()) < 1e-6
    assert abs(x2_v.grad - x2_t.grad.item()) < 1e-6
    print("  MATCH\n")


if __name__ == "__main__":
    demo_basic()
    demo_power()
    demo_complex()
    demo_neuron()
    demo_exp_log()
    demo_gradient_check()
    demo_mlp_training()
    demo_verify_pytorch()
    print("All demos passed.")
