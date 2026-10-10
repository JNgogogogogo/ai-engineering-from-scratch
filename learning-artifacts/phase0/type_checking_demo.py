"""类型检查器能抓什么、不能抓什么 —— 0/08 Editor Setup 配套实测。

Lesson: phases/00-setup-and-tooling/08-editor-setup/docs/en.md
Learner artifact: 验证 `python.analysis.typeCheckingMode: basic` 的实际价值边界。
核心结论：类型检查抓「类型错」，抓不到「语义错」，而 AI 工程里语义错更致命。

运行：
    uv run python learning-artifacts/phase0/type_checking_demo.py
"""
import torch
from torch import nn

SEP = "=" * 70


def main():
    torch.manual_seed(0)
    x = torch.randn(32, 100)
    model = nn.Linear(100, 1)

    print(SEP)
    print(f"torch {torch.__version__} | 输入 x.shape = {tuple(x.shape)}")
    print(SEP)

    # ---- 错误 1：shape 混淆（类型完全合法）--------------------------
    print("\n[错误 1] batch 维与特征维混淆 —— 类型检查器抓不到")
    out = x.reshape(x.size(1), x.size(0))
    expected = x.reshape(x.size(1), x.size(0))
    print(f"  x.reshape(x.size(1), x.size(0)) -> {tuple(out.shape)}")
    print(f"  没有任何报错。类型签名 Tensor -> Tensor 完全合法")
    print(f"  但作者想写的其实是转置：")
    real_transpose = x.T.contiguous()
    print(f"    x.T.contiguous()            -> {tuple(real_transpose.shape)}")
    print(f"    两者元素相同吗: {torch.equal(out, real_transpose)}")
    print("  → 类型系统认为这是一次合法调用。只有你自己知道写错了。")

    # ---- 错误 2：把整个预测当 loss ---------------------------------
    print("\n[错误 2] 把 pred 当 loss 传给 backward —— 危险")
    pred = model(x)
    print(f"  pred.shape = {tuple(pred.shape)}  ← 不是标量")
    try:
        pred.backward()
        print("  backward() 竟然成功了 ← 这是最糟的情况：")
        print("     梯度算出来了，训练能跑，但优化目标完全错了")
        print("     你会以为模型在收敛，实际上它在往错误方向走")
    except RuntimeError as e:
        print(f"  RuntimeError: {str(e)[:70]}")

    # ---- 错误 3：拼错的参数名 ---------------------------------------
    print("\n[错误 3] 拼错的关键字参数名 —— 取决于库是否宽容")
    try:
        opt = torch.optim.SGD(model.parameters(), learning_rate=0.01)
        lrs = [g["lr"] for g in opt.param_groups]
        print(f"  SGD(learning_rate=...) 被接受，lr = {lrs}")
        print("  → torch 2.x 有这个别名，静默成功。改库名就炸。")
    except TypeError as e:
        print(f"  TypeError: {str(e)[:70]}")
        print("  → Pylance 会在你按 S 键之前就标红")

    # ---- 对照：正确写法 ---------------------------------------------
    print("\n[对照] 正确写法")
    loss = model(x).sum()
    loss.backward()
    print(f"  loss = model(x).sum()  shape={tuple(loss.shape)}  value={loss.item():.4f}")
    print("     .sum() 把张量降成标量，backward() 才语义正确")
    torch.optim.SGD(model.parameters(), lr=0.01)
    print("  SGD(lr=...) 正常")

    # ---- 结论 ------------------------------------------------------
    print("\n" + SEP)
    print("类型检查的实际价值边界")
    print(SEP)
    rows = [
        ("拼错的关键字参数名", "抓得到", "有类型签名的参数", "TypeError"),
        ("参数类型传错", "抓得到", "int传成 str 之类", "类型不匹配"),
        ("返回值类型不符声明", "抓得到", "声明 Tensor 返回 None", "返回值校验"),
        ("import 路径写错", "抓得到", "模块不存在", "ImportError"),
        ("用 .sum() 而非 .mean()", "抓不到", "类型完全合法", "静默算错"),
        ("batch 维与特征维混淆", "抓不到", "类型完全合法", "静默算错"),
        ("把 tensor 当 numpy 用", "抓不到", "鸭子类型兼容", "静默算错"),
        ("GPU 显存不够就 train", "抓不到", "运行期问题", "OOM"),
    ]
    print(f"{'错误类型':<24s}{'检查器':<10s}{'为什么':<26s}表现")
    print("-" * 78)
    for name, caught, why, symptom in rows:
        print(f"{name:<24s}{caught:<10s}{why:<26s}{symptom}")
    print("-" * 78)
    print("""
结论
  basic 模式的实际作用：抓「接口用错」—— 参数名、类型、路径。
  它抓不到「意图错」—— 维度搞反、少了个 .sum()、该 mean 的地方用了 sum。

  对 AI 工程来说第二类更致命，因为它们静默产生错误数值。
  所以要配一个最小测试：跑一遍，断言关键张量的 shape 和 loss 的量级。
  类型检查 + 一个 smoke test，才是「跑之前发现问题」的完整防线。
""")


if __name__ == "__main__":
    main()