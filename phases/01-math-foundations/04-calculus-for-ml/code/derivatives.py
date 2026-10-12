"""
derivatives.py —— 《Calculus for Machine Learning》配套代码（详细中文注释版）
==========================================================================

本文件用纯 Python 标准库（只用 math / random，不需要 NumPy）演示机器学习微积分的
全部核心概念。运行方式：

    python3 derivatives.py

共 7 个演示（demo_*），按顺序执行：
  1. demo_numerical_vs_analytical()  数值导数 vs 解析导数（并暴露浮点舍入的真相）
  2. demo_gradient()                 梯度 = 所有偏导组成的向量
  3. demo_gradient_descent_1d()      一维梯度下降：精确的几何衰减
  4. demo_gradient_descent_2d()      二维梯度下降
  5. demo_hessian()                  Hessian 矩阵：鞍点 vs 最小值 vs 条件数坑
  6. demo_taylor()                   泰勒级数近似：阶数与有效半径
  7. demo_linear_regression()        线性回归：暴露"参数收敛速度不同"的真问题

核心口诀（对应讲义九节）：
  · 导数 = 变化率 = 切线斜率
  · 梯度 = 所有偏导组成的向量，指向"最陡上升"方向；训练时取负走下坡
  · w_new = w_old - lr * dL/dw  —— 这一行就是整个深度学习的更新规则
  · 一阶泰勒 = 梯度下降；二阶泰勒 = 牛顿法
  · 反向传播 = 链式法则从输出往输入反复应用
"""

import math
import random


# ==========================================================================
# 一、基础工具函数
# ==========================================================================

def numerical_derivative(f, x, h=1e-7):
    """数值导数（中心差分，central difference）。

    公式：  f'(x) ≈ ( f(x+h) - f(x-h) ) / (2h)

    为什么用中心差分而不是前向差分 (f(x+h)-f(x))/h ？
      · 中心差分的截断误差是 O(h^2)，前向差分只有 O(h)
      · 也就是说同样的 h，中心差分精度高一个数量级以上

    为什么 h 默认取 1e-7 而不是 1e-15？
      · 总误差 ≈ 截断误差 + 浮点舍入误差
      · 截断误差 ~ h^2（越小越好）
      · 舍入误差 ~ eps*|f(x)|/(2h)（越小越差！因为除以了一个极小的数）
      · 两者此消彼长，h 的最优值约在 1e-5 ~ 1e-7
      · 把 h 取到 1e-15 会让 f(x+h) 和 f(x-h) 在浮点里几乎相等，
        相减时有效数字被"灾难性抵消"吃光，结果变成噪声
    """
    # 注意这里除以的是 (2*h)，不是 h —— 中心差分的标志
    return (f(x + h) - f(x - h)) / (2 * h)


def numerical_gradient(f, point, h=1e-7):
    """数值梯度：对"每个维度"分别做一次中心差分，拼成一个向量。

    point 是一个列表 [x1, x2, ..., xn]，返回 [df/dx1, df/dx2, ..., df/dxn]。

    关键点：求 df/dxi 时，"只动第 i 个维度，其余全部按住不动"——
            这就是偏导数（partial derivative）的定义。
    """
    gradient = []
    for i in range(len(point)):        # 逐个维度求偏导
        # 复制两份，避免污染原始输入（list(point) 是浅拷贝，元素是标量所以安全）
        point_plus = list(point)
        point_minus = list(point)
        point_plus[i] += h             # 只把第 i 个分量往右推 h
        point_minus[i] -= h            # 只把第 i 个分量往左推 h
        # 其余分量在两份里完全相同，相减时被消掉 —— 这就是"按住不动"
        partial = (f(point_plus) - f(point_minus)) / (2 * h)
        gradient.append(partial)
    return gradient


def gradient_descent_1d(f, df, x0, lr=0.1, steps=20):
    """一维梯度下降：x = x - lr * df(x)，迭代 steps 次。

    返回最终的 x 以及完整历史 [(step, x, f(x)), ...]。
    这里的 df 是"解析导数"，也可以换成 numerical_derivative(f, x) —— 数值法。
    """
    x = x0
    history = []
    for step in range(steps):
        grad = df(x)                   # ① 算梯度（这里是斜率）
        x = x - lr * grad              # ② 沿负梯度方向走一步 —— 训练的全部
        history.append((step, x, f(x)))
    return x, history


def gradient_descent_nd(f, x0, lr=0.1, steps=100):
    """n 维梯度下降：每个分量各自减去 lr * 该分量的偏导。

    和 1D 版唯一区别：梯度是"一个向量"，更新要逐分量进行。
    """
    point = list(x0)
    history = []
    for step in range(steps):
        grad = numerical_gradient(f, point)   # 梯度向量 [df/dx1, df/dx2, ...]
        # zip 把 point 和 grad 的分量一一配对，逐个做 x - lr*g
        point = [p - lr * g for p, g in zip(point, grad)]
        history.append((step, list(point), f(point)))
    return point, history


# ==========================================================================
# 二、演示 1：数值导数 vs 解析导数
# ==========================================================================

def demo_numerical_vs_analytical():
    print("=" * 55)
    print("数值导数 vs 解析导数")
    print("=" * 55)

    # (名字, 原函数, 它的解析导数) —— 前两个是 lambda，后三个用 math
    test_cases = [
        ("x^2",    lambda x: x**2,        lambda x: 2*x),            # MSE 损失的基础
        ("x^3",    lambda x: x**3,        lambda x: 3*x**2),
        ("sin(x)", lambda x: math.sin(x), lambda x: math.cos(x)),
        ("e^x",    lambda x: math.exp(x), lambda x: math.exp(x)),    # softmax / attention
        ("1/x",    lambda x: 1/x,         lambda x: -1/x**2),        # 交叉熵里的 log
    ]

    x = 2.0
    print(f"\n在 x = {x} 处：")
    print(f"{'函数':<12} {'数值导数':>12} {'解析导数':>12} {'误差':>12}")
    print("-" * 50)
    for name, f, df in test_cases:
        num = numerical_derivative(f, x)   # 数值法（有微小误差）
        ana = df(x)                        # 解析法（精确）
        err = abs(num - ana)
        # 实测：误差约 1e-9 量级，不是 1e-14 —— 因为"浮点舍入误差"主导了，
        # 详见讲义"实测纠正 1"。这也是工业界最终用自动微分而非数值微分的原因。
        print(f"{name:<12} {num:12.6f} {ana:12.6f} {err:12.2e}")


# ==========================================================================
# 三、演示 2：梯度（所有偏导组成的向量）
# ==========================================================================

def demo_gradient():
    print("\n" + "=" * 55)
    print("梯度（所有偏导组成的向量）")
    print("=" * 55)

    def f(point):
        x, y = point
        return x**2 + 3*x*y + y**2

    point = [1.0, 2.0]
    grad = numerical_gradient(f, point)
    # 解析梯度：df/dx = 2x + 3y，df/dy = 3x + 2y
    analytical = [2*point[0] + 3*point[1], 3*point[0] + 2*point[1]]

    print(f"\nf(x,y) = x^2 + 3xy + y^2")
    print(f"在点 ({point[0]}, {point[1]}) 处：")
    # 实测：[8.0000, 7.0000] 对 [8.0, 7.0] —— 数值法在两位小数上完全一致。
    # 这就是"反向传播写完后用数值梯度做 gradient check"的原理。
    print(f"  数值梯度:   [{grad[0]:.4f}, {grad[1]:.4f}]")
    print(f"  解析梯度:   [{analytical[0]:.1f}, {analytical[1]:.1f}]")


# ==========================================================================
# 四、演示 3：一维梯度下降 f(x) = x^2
# ==========================================================================

def demo_gradient_descent_1d():
    print("\n" + "=" * 55)
    print("梯度下降: f(x) = x^2")
    print("=" * 55)

    x = 5.0
    lr = 0.1
    print(f"\n起点: x={x}, lr={lr}")
    for step in range(20):
        grad = 2 * x                   # f(x)=x^2 的导数是 2x
        x = x - lr * grad              # 更新规则
        if step % 4 == 0 or step == 19:
            print(f"  第 {step:2d} 步  x={x:8.4f}  f(x)={x**2:10.6f}")

    # 【实测宝藏】把更新式代入化简：
    #     x_new = x - lr*(2x) = (1 - 2*lr) * x
    # lr=0.1 时每步系数是 0.8，于是 x 是"精确的几何衰减"：
    #     x_20 = 5 * 0.8^20 = 0.057646  （与上面实测打印完全吻合）
    # 由此直接读出收敛条件 |1-2*lr| < 1，即 0 < lr < 1：
    #     lr=0.5 -> 系数 0   一步到位
    #     lr=1.0 -> 系数 -1  永久震荡不收敛
    #     lr=1.1 -> 系数 -1.2 发散
    # 一般函数上，学习率的上限由"曲率（二阶导）"决定。
    print(f"找到最小值于 x={x:.6f}（真实最小值: x=0）")


# ==========================================================================
# 五、演示 4：二维梯度下降 f(x,y) = x^2 + y^2
# ==========================================================================

def demo_gradient_descent_2d():
    print("\n" + "=" * 55)
    print("梯度下降: f(x,y) = x^2 + y^2")
    print("=" * 55)

    def f(point):
        x, y = point
        return x**2 + y**2

    point = [4.0, 3.0]
    lr = 0.1
    print(f"\n起点: ({point[0]}, {point[1]}), lr={lr}")
    for step in range(30):
        grad = numerical_gradient(f, point)          # 每次都用数值梯度
        # 逐分量更新：x 和 y 各自减去 lr * 自己的偏导
        point = [p - lr * g for p, g in zip(point, grad)]
        loss = f(point)
        if step % 5 == 0 or step == 29:
            print(f"  第 {step:2d} 步  ({point[0]:7.4f}, {point[1]:7.4f})  f={loss:.6f}")

    # 起点 (4,3) 到原点的距离是 5，f=x^2+y^2 两个方向"一样陡"，
    # 所以它本质上和 1D 那个 5*0.8^n 是同一件事：
    #     5 * 0.8^30 = 0.0062，实测模长 sqrt(0.0050^2+0.0037^2) = 0.0062 ✓
    # 但"各向异性"的坑（Rosenbrock）在演示 5 才会出现。
    print(f"找到最小值于 ({point[0]:.4f}, {point[1]:.4f})（真实: (0, 0)）")


# ==========================================================================
# 六、Hessian 相关工具
# ==========================================================================

def hessian_2d(f, x, y, h=1e-5):
    """用有限差分算二元函数在 (x,y) 处的 2x2 Hessian 矩阵。

    Hessian = 所有二阶偏导组成的矩阵：
        H = | d2f/dx2   d2f/dxdy |
            | d2f/dydx  d2f/dy2  |

    · fxx、fyy 用"二阶中心差分"：(f(x+h) - 2f(x) + f(x-h)) / h^2
    · fxy 是混合偏导，用四点交叉差分：
        (f(x+h,y+h) - f(x+h,y-h) - f(x-h,y+h) + f(x-h,y-h)) / (4h^2)
      这个公式最易手滑写错，注意四个角的符号是 + - - +，分母是 4h^2 不是 2h^2。
    · 混合偏导满足 fxy = fyx（Clairaut 定理），所以只需算一次，矩阵对称。
    """
    fxx = (f(x + h, y) - 2 * f(x, y) + f(x - h, y)) / (h ** 2)
    fyy = (f(x, y + h) - 2 * f(x, y) + f(x, y - h)) / (h ** 2)
    fxy = (f(x + h, y + h) - f(x + h, y - h) - f(x - h, y + h) + f(x - h, y - h)) / (4 * h ** 2)
    return [[fxx, fxy], [fxy, fyy]]


def taylor_approx(f, f_prime, f_double_prime, x0, h, order=2):
    """泰勒级数近似：在 x0 处展开，估算 f(x0+h)。

        f(x0+h) ≈ f(x0) + f'(x0)*h + (1/2)*f''(x0)*h^2 + ...

    order=0：只用常数项（随机搜索）
    order=1：加一次项（梯度下降的理论基础）
    order=2：加二次项（牛顿法的理论基础）

    【注意】这里最多展开到二阶；要更高阶得自己加项。
            用 sin 在 x0=0 演示时，二阶项恒为零（sin''(0) = -sin(0) = 0），
            所以 order=1 和 order=2 输出完全一样 —— 这不是 bug，是奇函数展开的必然。
    """
    result = f(x0)                        # 0 阶项：函数值
    if order >= 1:
        result += f_prime(x0) * h         # 1 阶项：斜率 × 位移
    if order >= 2:
        result += 0.5 * f_double_prime(x0) * h ** 2   # 2 阶项：(1/2)*曲率*h^2
    return result


def hessian_eigenvalues(H):
    """手算 2x2 实对称矩阵的特征值（不依赖 NumPy）。

    由特征方程 det(H - λI) = 0 展开：
        λ^2 - trace*λ + det = 0
    解得：
        λ = (trace ± sqrt(trace^2 - 4*det)) / 2

    其中 trace = a + d（对角线之和），det = ad - bc（行列式）。

    · 判别式 < 0 时特征值为复数（比如纯旋转矩阵），这里返回 (None, None)
      —— 说明该点没有实特征方向。
    · 【关键】特征值的"符号"决定临界点类型：
        全正 -> 局部最小；全负 -> 局部最大；符号混杂 -> 鞍点。
    """
    a, b = H[0][0], H[0][1]
    c, d = H[1][0], H[1][1]
    trace = a + d
    det = a * d - b * c
    discriminant = trace ** 2 - 4 * det
    if discriminant < 0:
        return None, None                  # 复数特征值（如旋转矩阵）
    sqrt_disc = discriminant ** 0.5
    return (trace + sqrt_disc) / 2, (trace - sqrt_disc) / 2


# ==========================================================================
# 七、演示 5：Hessian —— 鞍点、碗、以及一个条件数 2500 的坑
# ==========================================================================

def demo_hessian():
    print("\n" + "=" * 55)
    print("Hessian 矩阵: 鞍点 vs 最小值")
    print("=" * 55)

    def saddle(x, y):
        # 鞍点函数：x 方向朝上弯，y 方向朝下弯
        return x ** 2 - y ** 2

    def bowl(x, y):
        # 碗函数：两个方向都朝上弯
        return x ** 2 + y ** 2

    print("\nf(x,y) = x^2 - y^2（鞍点函数）")
    H = hessian_2d(saddle, 0.0, 0.0)
    e1, e2 = hessian_eigenvalues(H)
    print("  在 (0,0) 处的 Hessian:")
    print(f"    [{H[0][0]:6.2f}  {H[0][1]:6.2f}]")
    print(f"    [{H[1][0]:6.2f}  {H[1][1]:6.2f}]")
    # 期望：[[2, 0], [0, -2]]，特征值 2 和 -2（一正一负）=> 鞍点
    print(f"  特征值: {e1:.2f}, {e2:.2f}")
    print("  符号混杂 --> 鞍点")

    print("\nf(x,y) = x^2 + y^2（碗函数）")
    H = hessian_2d(bowl, 0.0, 0.0)
    e1, e2 = hessian_eigenvalues(H)
    print("  在 (0,0) 处的 Hessian:")
    print(f"    [{H[0][0]:6.2f}  {H[0][1]:6.2f}]")
    print(f"    [{H[1][0]:6.2f}  {H[1][1]:6.2f}]")
    # 期望：[[2, 0], [0, 2]]，特征值 2 和 2（都是正的）=> 局部最小值
    print(f"  特征值: {e1:.2f}, {e2:.2f}")
    print("  全部为正 --> 局部最小值")

    def rosenbrock(x, y):
        # Rosenbrock"香蕉函数"：全局最小在 (1,1)，但那条山谷窄而长
        # 系数 100 是故意的 —— 让两个方向的曲率相差极大
        return (1 - x) ** 2 + 100 * (y - x ** 2) ** 2

    print("\nRosenbrock f(x,y) = (1-x)^2 + 100*(y-x^2)^2")
    H = hessian_2d(rosenbrock, 1.0, 1.0)
    e1, e2 = hessian_eigenvalues(H)
    print(f"  在最小值 (1,1) 处的 Hessian:")
    print(f"    [{H[0][0]:8.2f}  {H[0][1]:8.2f}]")
    print(f"    [{H[1][0]:8.2f}  {H[1][1]:8.2f}]")
    print(f"  特征值: {e1:.2f}, {e2:.2f}")
    # 【实测宝藏】H = [[802, -400], [-400, 200]]，λ = 1001.60 和 0.40
    #   条件数 = 1001.60 / 0.40 ≈ 2504 —— 两个方向曲率相差 2500 倍！
    #   后果：陡方向要求极小学习率（否则飞出山谷），平方向爬得极慢，
    #        而平方向恰恰是通往最小值的唯一通道。
    #   这正是 Adam / L-BFGS / 牛顿法存在的理由。
    print(f"  全部为正 --> 局部最小值（已确认）")


# ==========================================================================
# 八、演示 6：泰勒级数近似
# ==========================================================================

def demo_taylor():
    print("\n" + "=" * 55)
    print("泰勒级数近似")
    print("=" * 55)

    x0 = 1.0
    print(f"\n在 x0 = {x0} 附近近似 f(x) = e^x")
    print(f"{'h':>8}  {'真值 f(x0+h)':>14}  {'0 阶':>10}  {'1 阶':>10}  {'2 阶':>10}")
    print("-" * 60)

    # e^x 的特点：各阶导数都是 e^x，所以 f、f'、f'' 传同一个函数
    for h in [0.1, 0.5, 1.0, 2.0]:
        true_val = math.exp(x0 + h)
        t0 = taylor_approx(math.exp, math.exp, math.exp, x0, h, order=0)
        t1 = taylor_approx(math.exp, math.exp, math.exp, x0, h, order=1)
        t2 = taylor_approx(math.exp, math.exp, math.exp, x0, h, order=2)
        # 实测：h=0.1 时二阶近似 3.003701 对真值 3.004166（误差 0.0005，极准）
        #      h=2.0 时二阶近似 13.59 对真值 20.09（低 32%，完全崩掉）
        print(f"{h:8.1f}  {true_val:14.6f}  {t0:10.6f}  {t1:10.6f}  {t2:10.6f}")

    print(f"\n在 x0 = 0 附近近似 f(x) = sin(x)")
    print(f"{'h':>8}  {'真值 sin(h)':>14}  {'0 阶':>10}  {'1 阶':>10}  {'2 阶':>10}")
    print("-" * 60)

    # sin 的各阶导数：f = sin, f' = cos, f'' = -sin
    for h in [0.1, 0.5, 1.0, 2.0]:
        true_val = math.sin(h)
        t0 = taylor_approx(math.sin, math.cos, lambda x: -math.sin(x), 0.0, h, order=0)
        t1 = taylor_approx(math.sin, math.cos, lambda x: -math.sin(x), 0.0, h, order=1)
        t2 = taylor_approx(math.sin, math.cos, lambda x: -math.sin(x), 0.0, h, order=2)
        # 【注意】order=1 与 order=2 的输出完全相同！
        #   因为 sin''(0) = -sin(0) = 0，二次项在 x0=0 处恒为零。
        #   想看到"加项更准"的效果，得用 e^x 或 cos(x)，或者跳到三阶 (x - x^3/6)。
        #   另外 h=2.0 时近似给出 2.0，真值 0.909 —— 差 2.2 倍，比直接猜 0 还离谱。
        print(f"{h:8.1f}  {true_val:14.6f}  {t0:10.6f}  {t1:10.6f}  {t2:10.6f}")

    print("\n关键洞察: 项数越多，在 x0 附近近似越准，")
    print("但所有泰勒近似在远离 x0 时都会发散。")


# ==========================================================================
# 九、演示 7：线性回归 —— 暴露"参数收敛速度不同"的真问题
# ==========================================================================

def demo_linear_regression():
    print("\n" + "=" * 55)
    print("梯度下降: 线性回归 y = 2x + 1")
    print("=" * 55)

    random.seed(42)                 # 固定随机种子，让结果可复现
    w = random.gauss(0, 1)          # 权重：标准正态随机初始化
    b = random.gauss(0, 1)          # 偏置：同样随机初始化
    lr = 0.01

    # 数据：故意选成 y = 2x + 1 的完美直线
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [3.0, 5.0, 7.0, 9.0, 11.0]

    for epoch in range(200):
        total_loss = 0
        dw = 0
        db = 0
        for x, y in zip(xs, ys):
            pred = w * x + b        # ① 前向：预测
            error = pred - y        #    残差
            total_loss += error ** 2   # ② MSE 损失
            # ③ 反向：MSE 对 w 和 b 的解析梯度
            #    L = (wx+b - y)^2  =>  dL/dw = 2*error*x ，dL/db = 2*error
            #    注意 dw 多乘了一个 x，db 没有 —— 这是下面"收敛速度差 3 倍"的根因！
            dw += 2 * error * x
            db += 2 * error
        # ④ 取平均（batch 梯度 = mini-batch 的均值）
        dw /= len(xs)
        db /= len(xs)
        total_loss /= len(xs)
        # ⑤ 更新权重 —— 这两行就是整个训练循环
        w -= lr * dw
        b -= lr * db
        if epoch % 40 == 0 or epoch == 199:
            print(f"  第 {epoch:3d} 轮  w={w:.4f}  b={b:.4f}  loss={total_loss:.6f}")

    # 【实测宝藏】w 在 40 epoch 就到 2.13（目标 2.0），b 到 200 epoch 才 0.73（目标 1.0）
    #   根因：xs 平均值是 3，所以 dw 的量级约是 db 的 3 倍
    #        => 同一个学习率不可能同时适合两个尺度差 3 倍的参数
    #   这解释了三个常见做法：特征归一化、Adam（每参数自适应学习率）、学习率预热/衰减
    #   也解释了"loss 曲线平了但模型没学对"的一种可观测来源。
    print(f"\n学到的: y = {w:.2f}x + {b:.2f}")
    print(f"真实的:  y = 2.00x + 1.00")


if __name__ == "__main__":
    demo_numerical_vs_analytical()
    demo_gradient()
    demo_gradient_descent_1d()
    demo_gradient_descent_2d()
    demo_hessian()
    demo_taylor()
    demo_linear_regression()
