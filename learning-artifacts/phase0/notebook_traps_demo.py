"""Notebook 三大陷阱的真实 kernel 复现脚本。

Lesson: phases/00-setup-and-tooling/05-jupyter-notebooks/docs/en.md
Learner artifact: 用真实 Jupyter kernel 跑出乱序执行与幽灵状态的报错，
    亲眼看到"同一份代码因为点击顺序不同而结果不同"。

运行：
    uv run python learning-artifacts/phase0/notebook_traps_demo.py

每个场景跑在独立 subprocess 里。原因：jupyter_client 的 kernel channel
线程一旦start_channels 就不能在同一进程里安全地再启动一次（踩过
RuntimeError: threads can only be started once）。隔离进程比在进程内
重启 kernel 更贴近"我重启了 JupyterLab"的真实心智模型。
"""
import json
import subprocess
import sys
import textwrap
from pathlib import Path

# --- 四个 cell，内容照抄讲义里的示例 -------------------------------------

CELL_LOAD = (
    "import time; t0=time.time(); data=list(range(2_000_000)); "
    "time.sleep(1); print(f'CELL1 数据就绪 {len(data):,} 项, {time.time()-t0:.1f}s')"
)
CELL_THRESHOLD = "threshold=1_500_000; print(f'CELL3 看到 {len(data):,} 项, 阈值已设 {threshold:,}')"
CELL_COUNT = (
    "big=sum(1 for x in data if x>threshold); "
    "print(f'CELL4 结果 {big:,}')  # 严格大于 1_500_000 → 499,999"
)
CELL_ORPHAN = "print(f'CELL5 无依赖声明，纯粹靠 kernel 里的残留变量 {len(data)*2:,} 项')"

SCENARIOS = {
    "陷阱一 · 乱序执行（out-of-order）": [
        ("先跑 CELL4（要用 data 和 threshold）", CELL_COUNT),
        ("再跑 CELL3（也要用 data）", CELL_THRESHOLD),
        ("最后才跑 CELL1（定义 data）", CELL_LOAD),
    ],
    "陷阱二 · 幽灵状态（hidden state）": [
        ("跑 CELL1（定义 data）", CELL_LOAD),
        ("跑 CELL4（用 threshold）→ 报错", CELL_COUNT),
        ("跑 CELL3（定义 threshold）", CELL_THRESHOLD),
        ("再跑 CELL4→ 一行没改，成功了", CELL_COUNT),
        ("跑 CELL5（自己没有任何 import）", CELL_ORPHAN),
    ],
}

# --- 单个场景的执行器：启动真 kernel，逐条发代码，收 stream/error ----------

RUNNER = textwrap.dedent(
    '''
    import sys, json, queue
    from jupyter_client.manager import KernelManager

    km = KernelManager(kernel_name="python3")
    km.start_kernel()
    kc = km.client()
    kc.start_channels()
    try:
        kc.wait_for_ready(timeout=30)
        for label, code in json.loads(sys.argv[1]):
            msg_id = kc.execute(code)
            out = []
            while True:
                try:
                    msg = kc.get_iopub_msg(timeout=60)
                except queue.Empty:
                    break
                if msg["parent_header"].get("msg_id") != msg_id:
                    continue
                t = msg["msg_type"]
                if t == "stream":
                    out.append(msg["content"]["text"].rstrip())
                elif t == "error":
                    out.append(f"{msg['content']['ename']}: {msg['content']['evalue']}")
                elif t == "status" and msg["content"]["execution_state"] == "idle":
                    break
            print(f"  {label}\\n    -> {out[0] if out else '(无输出)'}")
    finally:
        kc.stop_channels()
        km.shutdown_kernel()
    '''
)


def main():
    runner = Path(__file__).with_name("_kernel_runner.py")
    runner.write_text(RUNNER)

    print("Notebook 陷阱复现 —— 全部来自真实 kernel，不是模拟\n")
    for title, steps in SCENARIOS.items():
        print(f"=== {title} ===")
        # 每次用干净的 cwd，避免 .ipynb_checkpoints 之类的干扰
        result = subprocess.run(
            [sys.executable, str(runner), json.dumps(steps)],
            capture_output=True,
            text=True,
            cwd=runner.parent,
        )
        print(result.stdout.rstrip() or result.stderr[-800:])
        print()

    runner.unlink(missing_ok=True)  # 临时文件，用完即清

    print("=" * 60)
    print("复现要点：")
    print("  1. 乱序执行里没有一行代码是错的，错的只是点击顺序")
    print("  2. 幽灵状态里 CELL4 一行未改，只因前面多跑了一个 cell 就从报错变成功")
    print("  3. CELL5 自己没有任何 import，照样能跑 —— 依赖藏在 kernel 里")
    print("  4. 499,999 是边界正确的答案（range 上界不含，差一个 1 就错）")
    print("\n唯一的解药：分享前 Kernel > Restart & Run All。")


if __name__ == "__main__":
    main()