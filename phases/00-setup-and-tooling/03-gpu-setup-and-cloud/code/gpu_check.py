"""GPU availability check and CPU vs GPU matrix-multiply benchmark.

Lesson: phases/00-setup-and-tooling/03-gpu-setup-and-cloud/docs/en.md
Adapted for Apple Silicon: falls back to the MPS backend when CUDA is absent.
"""
import os  # 标准库：读取环境与系统信息
import subprocess  # 标准库：macOS 上通过 sysctl 命令读取物理内存大小
import time  # 标准库计时模块：基准测试用它测量墙钟时间


def check_gpu():
    # 主函数：检测可用的计算后端（CUDA / MPS / 无），然后跑 CPU vs GPU 基准
    try:
        import torch  # 延迟导入：没装 PyTorch 时给出友好提示而不是崩溃
    except ImportError:
        print("PyTorch not installed. Run: pip install torch")  # 明确的修复指引
        return  # 直接返回，跳过后续所有检测

    print("=== GPU Check ===\n")  # 标题：后端可用性检查
    print(f"PyTorch version: {torch.__version__}")  # 版本号 ≠ 可用性，只是环境信息
    print(f"CUDA available: {torch.cuda.is_available()}")  # NVIDIA 专属后端是否可用
    print(f"MPS available:  {torch.backends.mps.is_available()}")  # Apple Silicon 的 Metal 后端

    # 选择最优后端，并取与之配套的同步函数（两个后端的同步 API 不同）
    if torch.cuda.is_available():  # 情况 1：有 NVIDIA GPU → 用 CUDA
        device = "cuda"  # 张量搬运目标设备字符串
        sync = torch.cuda.synchronize  # CUDA 流同步函数：阻塞直到 GPU 全部算完
        print(f"\nCUDA version: {torch.version.cuda}")  # 驱动层 CUDA 运行时版本
        print(f"GPU: {torch.cuda.get_device_name(0)}")  # GPU 型号名（0 号卡）
        vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9  # 显存总量（字节转 GB）
        print(f"Memory: {vram_gb:.1f} GB")  # 打印显存
    elif torch.backends.mps.is_available():  # 情况 2：Apple Silicon → 用 MPS
        device = "mps"  # PyTorch 的 Metal Performance Shaders 后端
        sync = torch.mps.synchronize  # MPS 命令队列同步函数，语义同 CUDA 版
        # Apple Silicon 是统一内存架构：GPU 与 CPU 共享同一份物理内存，
        # 所以严格说没有独立 VRAM，这里用物理内存总量做 fp16 估算的上界。
        # 注意：hw.memsize 是 sysctl 名，os.sysconf 不认，必须走 sysctl 命令
        try:
            vram_gb = int(
                subprocess.run(
                    ["sysctl", "-n", "hw.memsize"],  # -n 只输出值，单位字节
                    capture_output=True,  # 捕获 stdout/stderr
                    text=True,  # 输出按文本而非 bytes 处理
                    check=True,  # 非 0 退出码时抛异常
                ).stdout.strip()
            ) / 1e9
        except Exception:
            vram_gb = None  # 读不到就不估，后面跳过 fp16 估算
        if vram_gb is not None:
            print(f"\nDevice: Apple Silicon GPU (MPS, unified memory ~{vram_gb:.1f} GB)")
        else:
            print("\nDevice: Apple Silicon GPU (MPS)")
    else:  # 情况 3：两种 GPU 后端都没有
        print("\nNo GPU detected. That's fine for most lessons.")  # 不是失败，Phase 1-3 CPU 够用
        print("For GPU-heavy lessons, use Google Colab (free).")  # 指路：免费云端 T4
        return  # 没有 GPU 就无法做对比基准，提前结束

    print("\n=== CPU vs GPU Benchmark ===\n")  # 标题：矩阵乘基准测试
    size = 4000  # 方阵边长：4000×4000 足够大，能体现 GPU 优势又不至于爆内存

    a = torch.randn(size, size)  # CPU 上生成随机矩阵 A（默认 float32）
    b = torch.randn(size, size)  # CPU 上生成随机矩阵 B

    start = time.time()  # CPU 计时开始
    _ = a @ b  # CPU 矩阵乘（结果丢弃，只测时间；CPU 调用是同步的，无需 sync）
    cpu_time = time.time() - start  # CPU 耗时
    print(f"CPU matrix multiply ({size}x{size}): {cpu_time:.3f}s")

    a_gpu = a.to(device)  # 把 A 从 CPU 内存搬运到 GPU 设备
    b_gpu = b.to(device)  # 把 B 搬运过去（后续计算不再经过 CPU）

    # 热身一次：Metal/CUDA 的 kernel 是懒编译的，首次调用包含编译开销，
    # 不把它从计时中剔除会严重低估 GPU 真实速度
    _ = a_gpu @ b_gpu
    sync()  # 等热身计算真正结束，再进入正式计时

    start = time.time()  # GPU 计时开始
    _ = a_gpu @ b_gpu  # GPU 矩阵乘：这一行只是「发出指令」，立即返回
    sync()  # 关键：阻塞等 GPU 真正算完，否则测到的是「发射耗时」而非「计算耗时」
    gpu_time = time.time() - start  # GPU 耗时
    print(f"GPU ({device}) matrix multiply ({size}x{size}): {gpu_time:.3f}s")
    print(f"Speedup: {cpu_time / gpu_time:.0f}x")  # 加速比 = CPU 时间 ÷ GPU 时间

    # fp16 经验法则：每个参数约 2 字节 → 可容纳参数量 ≈ 显存字节数 ÷ 2
    # 注意 Apple Silicon 上这是上界：统一内存里还要装操作系统和 CPU 侧数据
    if vram_gb is not None:
        params_billions = vram_gb * 1e9 / 2 / 1e9
        print(f"\nEstimated max model size (fp16): ~{params_billions:.0f}B parameters")
    else:
        print("\nEstimated max model size (fp16): unknown (could not read memory size)")


if __name__ == "__main__":
    # 直接运行本文件时执行检查；被 import 时不会自动跑基准
    check_gpu()
