"""虚拟环境隔离机制现场验证 —— 0/06 Python Environments 配套脚本。

Lesson: phases/00-setup-and-tooling/06-python-environments/docs/en.md
Learner artifact: 把「虚拟环境是个目录约定」「activate 只改 PATH」「隔离靠什么」
这三条从概念变成可观测的数字。不需要预装任何包，纯标准库。

运行：
    uv run python learning-artifacts/phase0/venv_isolation_lab.py
    #或
    python3 learning-artifacts/phase0/venv_isolation_lab.py

本脚本只做「只读诊断」：它检查你当前的解释器环境，打印关键路径和版本。
它不会修改任何环境，不会装包，不会删除东西。唯一写操作是在临时目录里
建两个对照环境（用完即删），可用 --no-lab 跳过。
"""

import argparse
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

SEP = "=" * 68


def show(label, value, note=""):
    print(f"  {label:<28s}{value}")
    if note:
        print(f"  {'':<28s}└ {note}")


def section(title):
    print(f"\n{SEP}\n{title}\n{SEP}")


# ---------------------------------------------------------------- 1. 现状

def probe_current_env():
    section("1. 你当前所在的环境")

    print(f"  {sys.executable}")
    print(f"  {sys.version.split()[0]}")

    in_venv = sys.prefix != sys.base_prefix
    print(f"\n  sys.prefix      = {sys.prefix}")
    print(f"  sys.base_prefix = {sys.base_prefix}")

    if in_venv:
        print("\n  ✅ 你在虚拟环境里（prefix != base_prefix）")
        print("     装的包只影响这个目录，删掉目录就彻底没了。")
    else:
        print("\n  ⚠️  你在系统 Python 里（prefix == base_prefix）")
        print("     现在 pip install 会污染系统环境。")
        print("     修复：source <项目>/.venv/bin/activate")

    # site-packages 的位置——隔离的物理体现
    purelib = sysconfig.get_paths().get("purelib")
    print(f"\n  site-packages   = {purelib}")

    # 虚拟环境的判定标志文件
    markers = {
        "VIRTUAL_ENV环境变量": os.environ.get("VIRTUAL_ENV"),
        "pyvenv.cfg": str(Path(sys.prefix) / "pyvenv.cfg")
        if (Path(sys.prefix) / "pyvenv.cfg").exists()
        else None,
    }
    print("\n  虚拟环境标志物：")
    for k, v in markers.items():
        show(k, v or"<无>", None if v else "没找到 → 大概率不在 venv 里")

    # 体积
    sp = Path(purelib)
    if sp.exists():
        try:
            n = sum(1 for _ in sp.glob("*.dist-info"))
            size = sum(f.stat().st_size for f in sp.rglob("*") if f.is_file())
            print(f"\n  已装包数         {n}")
            print(f"  site-packages 体积 {size/1e6:.1f} MB")
            print(f"  （这就是不能提交 .venv 的原因——对比 pyproject.toml 的几百字节）")
        except OSError:
            pass

    # pip 在不在
    has_pip = importlib_available("pip")
    print(f"\n  pip 可用         {has_pip}")
    if not has_pip:
        print("     ⚠️  这个环境没有 pip。若它由 uv 创建（uv venv），")
        print("         请改用 `uv pip install <包>`，而不是 `python -m pip`。")
        print("         典型症状：No module named pip")
    return in_venv


def importlib_available(name):
    import importlib.util

    return importlib.util.find_spec(name) is not None


# ------------------------------------------------------- 2. PATH 优先级

def probe_path():
    section("2. PATH 优先级：环境是怎么被'选中'的")

    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    exe_dir = str(Path(sys.executable).parent)

    if exe_dir in path_dirs:
        idx = path_dirs.index(exe_dir)
        head = path_dirs[: idx + 1]
        print(f"  你的解释器目录   {exe_dir}")
        print(f"  它在 PATH 中排第 {idx + 1} 位")
        if idx == 0:
            print("\n  ✅ 排在第1 位 —— 裸敲 `python` 命中的就是它")
        else:
            print(f"\n  ⚠️  排第 {idx + 1} 位。前面这些目录里若也有 python，")
            print("     裸敲 `python` 命中的就不是当前环境。")
        print("\n  PATH 在你之前的部分：")
        for d in head[:-1]:
            print(f"    {d}")
    else:
        print(f"  解释器目录不在 PATH 里：{exe_dir}")
        print("  （常见于直接调`./.venv/bin/python` 或用了绝对路径）")


def show_activate_diff():
    section("3. activate 到底改了什么")

    activate = Path(sys.prefix) / "bin" / "activate"
    if not activate.exists():
        print(f"  没找到 {activate}")
        print("  （uv 创建的 venv 布局不同，或环境已失效）")
        print("\n  原理（不依赖具体实现）：activate 只做两件事——")
        print("    1) 把 <venv>/bin 插到 PATH 最前面")
        print("    2) 导出 VIRTUAL_ENV 环境变量")
        print("  deactivate 就是把 PATH 还原。没有卸载动作。")
        return

    lines = activate.read_text(errors="replace").splitlines()

    # 抓两类关键行：deactivate 里的 PATH 还原，和 activate 里的 PATH 插入
    restore = [ln.strip() for ln in lines
               if "_OLD_VIRTUAL_PATH" in ln and "=" in ln]
    prepend = [ln.strip() for ln in lines
               if "PATH=" in ln and "OLD_VIRTUAL_PATH" not in ln
               and ("export" in ln or ln.strip().startswith("PATH"))]

    print(f"  activate 脚本：{activate}")
    print(f"  行数：{len(lines)}（不同工具生成的版本行数不同，内容本质一样）\n")

    print("  ▸ deactivate 部分—— PATH 还原：")
    for h in restore[:4]:
        print(f"      {h}")
    if not restore:
        print("      （未匹配到，格式可能不同）")

    print("\n  ▸ activate 部分—— PATH 插入：")
    for h in prepend[:4]:
        print(f"      {h}")
    if not prepend:
        print("      （未匹配到，格式可能不同）")

    print("\n  把它当普通 shell 脚本读一遍，比任何解释都直观。")
    print("  原理：activate只做两件事——往PATH 最前面插 <venv>/bin，")
    print("  再导出 VIRTUAL_ENV。deactivate 把 PATH 字符串还原，")
    print("  没有「卸载」这一步。")


# ---------------------------------------------------- 3. 可选：对照实验

LAB_SCRIPT = r'''
import subprocess, sys, sysconfig, venv
from pathlib import Path

root = Path(sys.argv[1])
base_exe = sys.argv[2]          # 基础解释器，避免造出嵌套 venv
paths = {}
for name in ("env_a", "env_b"):
    vdir = root / name
    subprocess.run([base_exe, "-m", "venv", str(vdir)],
                   capture_output=True, text=True, check=True)
    py = vdir / "bin" / "python"
    out = subprocess.run([str(py), "-c",
        "import sys,json;print(json.dumps({"
        "'exe':sys.executable,'prefix':sys.prefix,"
        "'base':sys.base_prefix,'ver':sys.version.split()[0]}))"],
        capture_output=True, text=True)
    import json
    paths[name] = json.loads(out.stdout)

print(json.dumps(paths, indent=2, ensure_ascii=False))
'''


def build_lab(root: Path, install_pkgs: bool = True):
    """建两个环境并（可选）各装一个不同版本的 numpy。"""
    section("4. 对照实验：两个环境，同一个包，不同版本")

    # 先看基础信息（不装包，快）
    # 用「当前环境的基础解释器」而不是当前解释器去建，
    # 否则会造出嵌套 venv（base 指向自己），拿不到"Python 版本不同"的对比。
    base_py = sys.base_prefix
    base_exe = Path(base_py) / "bin" / (
        "python3" if sys.platform != "win32" else "python.exe")
    if not base_exe.exists():
        base_exe = Path(sysconfig.get_config_var("BINDIR")) / Path(sys.executable).name
    if not Path(base_exe).exists():
        print(f"  找不到基础解释器（试过 {base_exe}），跳过对照实验")
        return

    res = subprocess.run([sys.executable, "-c", LAB_SCRIPT, str(root), str(base_exe)],
                         capture_output=True, text=True)
    if res.returncode != 0:
        print("  建环境失败：")
        print("  " + res.stderr.strip()[-500:])
        return

    print(res.stdout)

    if not install_pkgs:
        print("  （跳过装包，加 --with-pkgs 才装；装包需要联网）")
        return

    import json

    paths = json.loads(res.stdout)
    versions = {"env_a": "numpy==1.26.4", "env_b": "numpy==2.2.6"}
    print("  装包中（可能需要几十秒）…")
    for name, spec in versions.items():
        py = str(root / name / "bin" / "pip")
        subprocess.run([py, "install", "-q", spec],
                       capture_output=True, text=True)
        v = subprocess.run([str(root / name / "bin" / "python"), "-c",
             "import numpy;print(numpy.__version__, numpy.__file__)"],
             capture_output=True, text=True)
        got = v.stdout.strip() or v.stderr.strip().splitlines()[-1]
        print(f"  {name}: 请求 {spec:<16s} 实得 {got}")

    print("\n  若两个版本不同且互不报错 → 隔离生效")
    print("  再检查你自己的环境有没有被动过（回到第 1 节看版本号是否变了）")
    print("\n  注意：两个环境的 base_prefix 相同是正常的 —— 它们由同一个")
    print("  基础解释器创建（本脚本不联网下载 Python）。要对比不同 Python")
    print("  版本，得先 `uv python install 3.14` 再用那个解释器建环境。")
    print("  隔离的关键不是 base 不同，而是 prefix 各不相同、")
    print("  site-packages 各装各的版本。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-lab", action="store_true",
                    help="跳过对照实验（不建临时环境）")
    ap.add_argument("--with-pkgs", action="store_true",
                    help="对照实验额外装 numpy（需要联网，约 30-60s）")
    args = ap.parse_args()

    print("虚拟环境隔离机制现场诊断")
    print(f"  Python {sys.version.split()[0]}  ({sys.executable})")

    probe_current_env()
    probe_path()
    show_activate_diff()

    if args.no_lab:
        print("\n（已跳过对照实验）")
        return

    tmp = Path(tempfile.mkdtemp(prefix="venv_lab_"))
    print(f"\n临时实验目录：{tmp}")
    try:
        build_lab(tmp, install_pkgs=args.with_pkgs)
    finally:
        print(f"\n清理 {tmp} …")
        shutil.rmtree(tmp, ignore_errors=True)
        print("  已删除。虚拟环境本来就是'删了就没'的东西。")


if __name__ == "__main__":
    main()