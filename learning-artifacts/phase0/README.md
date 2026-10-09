# 0/05 Jupyter Notebook 实测台

本目录是`phases/00-setup-and-tooling/05-jupyter-notebooks`（Jupyter Notebooks）的配套产物。

## 文件

| 文件 | 用途 |
|------|------|
| `jupyter_test_runnable.ipynb` | **推荐从这个开始。** 33 cells，从头 `Restart & Run All` 不会报错 |
| `jupyter_test.ipynb` | 陷阱版。三个刻意不自洽的 cell，用来现场踩坑 |
| `jupyter_test_runnable.executed.ipynb` | 上面那个的「已执行」快照，直接看输出不用自己跑 |
| `notebook_traps_demo.py` | 用真实 kernel 复现乱序执行 + 幽灵状态，命令行可跑 |

## 打开方式

```bash
cd /Users/tangxun/Documents/WKS/agent/ai-engineering-from-scratch
.venv/bin/jupyter lab learning-artifacts/phase0/jupyter_test_runnable.ipynb
```

**必须用 `.venv/bin/jupyter`，不能直接 `jupyter`**——否则 kernel 会挂在系统 Python 上，
numpy / pandas / psutil 全都import 失败。

## 陷阱版的正确玩法

1. 打开 `jupyter_test.ipynb`
2. 找到标着 `⚠️ 陷阱 cell4` 的 cell，**第一个就 Run 它** → 会看到 `NameError`
3. 往下依次 Run `CELL 1` / `CELL 2` / `CELL 3`
4. 回到第2 步那个 cell，**再 Run 一次** → 这次成功了，而代码一个字都没改
5. 然后 Kernel > Restart & Run All → 第 2 步立刻重新报错

第 4 步和第 5 步的反差就是这一课的全部内容。

## 可跑通版覆盖的知识点

1. 环境自检（解释器路径 —— 确认 kernel 挂在 `.venv` 上）
2. `%timeit` vs `%%time`，以及单次计时为什么不可信（实测 7.6x噪声）
3. 列表推导 vs numpy：24.8x 加速 + 4.6x 内存差距
4. 富输出：`df` 裸写vs `print(df)`；`df.style`；DataFrame 自带绘图
5. matplotlib 中文字体（默认 DejaVu Sans 不含 CJK，597 个已注册字体里挑 `PingFang SC`）
6. 陷阱一：乱序执行
7. 陷阱二：幽灵状态
8. 陷阱三：内存泄漏（psutil 读真实 RSS，`del` 之后 RSS 不回落）
9. `%who` 查看 kernel 里到底有哪些变量
10. 边界条件：`range` 上界不含（499,999 不是 500,000）

## 已知实测数据（本机 M5 Pro / Python 3.12.15）

| 项 | 值 |
|---|---|
| `%timeit np.random.randn(1000)` | 7.94 μs ± 17.8 ns，100,000 loops |
| 单次计时 8 轮噪声比 | 6~7.6x |
| 列表推导 vs numpy（1e6） | 18.93 ms vs 0.76 ms → 24.8x |
| 内存：列表真实占用 vs numpy | 36.4 MB vs 8.0 MB → 4.6x |
| RSS 分配 160 MB 数组 | 215.9 MB → 368.5 MB，`del`+`gc` 后**几乎不降** |

> 内存那一项第一版写错了：用 `sys.getsizeof` 量列表得到 8.4 MB，
> 看起来和 numpy 的 8.0 MB 差不多。实际加上每个 int 对象的 28 字节
> 是 36.4 MB，差 4.6 倍。**`sys.getsizeof` 只量容器本身，不含元素对象。**
